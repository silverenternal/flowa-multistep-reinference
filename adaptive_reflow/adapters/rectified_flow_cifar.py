"""Rectified Flow (Liu 2022) CIFAR-10 adapter (R5 — SOTA FM reproduction).

This module wires the published Rectified Flow velocity-field UNet (Liu,
Q. 2022 — *Flow Straight and Fast: Learning to Generate and Transfer Data
with Rectified Flow*, NeurIPS 2022 Spotlight; ``arXiv:2210.02647``)
into the framework's :class:`FlowMatchingODEAdapter` Protocol so that
the same algorithm-layer code that drives the synthetic 2D
:mod:`adaptive_reflow.adapters.twodim_fm` adapter also drives a real
state-of-the-art FM model on CIFAR-10 32×32.

Two operating modes
-------------------

1. ``torch`` mode (the published integration; default when the weights
   file exists at construction). The adapter loads the pretrained UNet
   ``state_dict`` via :mod:`torch` and calls the network in
   ``torch.no_grad()`` / ``eval()`` mode on each integration step.
   This is the only torch import in the entire framework. It is gated
   on the :file:`pyproject.toml` ``[rf-cifar]`` optional extra.

2. ``synthetic`` mode (testing only). When ``weights_path`` is ``None``
   or the file is missing, the adapter falls back to a deterministic
   NumPy velocity field (``random_init=True``). The synthetic path is
   used by the test suite when torch is not installed in the test
   environment; it produces a well-formed but *non-SOTA* velocity field
   so the Protocol conformance tests can run without the heavy
   dependency. The synthetic mode is NOT a baseline reproduction of
   Liu 2022 — see ``tools/eval_rf_cifar.py`` for the load-bearing
   baseline.

Public surface
--------------

* :class:`RectifiedFlowCIFARAdapter` — concrete :class:`FlowMatchingODEAdapter`
  with ``state_shape=(3, 32, 32)``.
* :class:`RectifiedFlowCIFARCapabilities` — frozen capability surface.
* :func:`default_rectified_flow_cifar_adapter` — factory.
* :func:`rectified_flow_cifar_resolve_weights_path` — resolve a weights
  path from a list of candidate filenames.

Tasks satisfied
---------------

* R5 — SOTA Flow Matching reproduction on CIFAR-10 (CLM-040).
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    NoOpMixer,
)
from adaptive_reflow.universal.state import (
    
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

from adaptive_reflow.adapters._adapter_common import (
    digest_state,
    make_ref,
    seed_from_ids,
    memory_fraction_for,
)
from adaptive_reflow.framework.interfaces import implements


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

RF_CIFAR_CHANNELS: tuple[ChannelName, ...] = (ChannelName("image"),)
RF_CIFAR_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("image"): "continuous",
}
RF_CIFAR_CONFIG_HASH: str = "rf_cifar:cfg:v1"
RF_CIFAR_CONFIG_VERSION: str = "0.1.0"
RF_CIFAR_STATE_SHAPE: tuple[int, ...] = (3, 32, 32)
RF_CIFAR_CLAMP: float = 3.0
RF_CIFAR_NUM_STEPS_DEFAULT: int = 2
RF_CIFAR_T_END: float = 1.0
RF_CIFAR_NATIVE_STATES_MAXSIZE: int = 8

#: Available ODE integrators. ``"euler"`` is the 1st-order baseline
#: (single velocity evaluation per step). ``"heun"`` is the 2nd-order
#: predictor-corrector (two evaluations per step: Euler trial + trapezoidal
#: corrector). Heun at half the steps matches Euler at full steps
#: (trapezoidal rule halves the truncation error) but costs the same
#: wall-clock; at matched steps Heun is ~30-40% better FID.
#: See ``docs/r4-survey/21-fix-v2-plan.md`` §1.2 / §3.2.
RF_CIFAR_INTEGRATORS: tuple[str, ...] = ("euler", "heun")
RF_CIFAR_INTEGRATOR_EULER: str = "euler"
RF_CIFAR_INTEGRATOR_HEUN: str = "heun"

#: Max sub-batch fed to the torch UNet in one forward pass. The published
#: DDPM++ attention block materialises a ``(B, 16, 16, 16, 16)`` tensor,
#: so unbounded batches exhaust CPU memory.
RF_CIFAR_TORCH_CHUNK: int = 32

# Audit / error codes (deterministic ASCII strings).
AUDIT_RF_CIFAR_RESTART_BLEND: str = "rf_cifar_restart_blend"
AUDIT_RF_CIFAR_OBSERVED: str = "rf_cifar_observed"
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
ERR_RF_CIFAR_NUM_STEPS: str = "rf_cifar_num_steps_must_be_positive"
ERR_RF_CIFAR_WEIGHTS_MISSING: str = "rf_cifar_weights_missing"
ERR_RF_CIFAR_INTEGRATOR_UNKNOWN: str = "rf_cifar_integrator_unknown"

# Default weights filenames in priority order (the plan §1.2 fallbacks).
# ``cifar10_rf.pth`` is the clean EMA-only state-dict produced by the
# weights-acquisition phase (docs/r4-survey/13-weights-acquisition.md) and
# is preferred over the 990 MB raw training checkpoint.
RF_CIFAR_WEIGHTS_CANDIDATES: tuple[str, ...] = (
    "cifar10_rf.pth",
    "rectified_flow_cifar10.safetensors",
    "rectified_flow_cifar10.pth",
    "rectified_flow_cifar10.pt",
)

#: ``format`` marker written into the clean checkpoint by the acquisition
#: phase; selects the gnobitab Score-SDE DDPM++ topology.
RF_CIFAR_FORMAT_GNOBITAB: str = "gnobitab_1rf_cifar10"

#: Image-shape constants.
RF_CIFAR_CHANNELS_AXIS: int = 0
RF_CIFAR_HEIGHT: int = 32
RF_CIFAR_WIDTH: int = 32
RF_CIFAR_PIXEL_COUNT: int = RF_CIFAR_HEIGHT * RF_CIFAR_WIDTH

#: Synthetic (test-only) velocity-field defaults.
RF_CIFAR_SYNTHETIC_HIDDEN: int = 32
RF_CIFAR_SYNTHETIC_SEED_DEFAULT: int = 0x5F3759DF  # "fast inverse sqrt" — deterministic marker.

Mode = Literal["torch", "synthetic"]

# Local type alias (avoid numpy at module-import hot annotation paths).
ArrayF64 = NDArray[np.float64]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def rectified_flow_cifar_resolve_weights_path(
    data_dir: Path | None = None,
    *,
    candidates: tuple[str, ...] = RF_CIFAR_WEIGHTS_CANDIDATES,
) -> Path | None:
    """Return the first existing candidate weights path under ``data_dir``.

    Returns ``None`` when none of the candidates exist. Used by the
    adapter factory when the caller does not pass an explicit
    ``weights_path``. Mirrors :func:`adaptive_reflow.adapters.twodim_fm
    ._default_weights_path` (no torch dependency in this helper).
    """
    base = Path(data_dir) if data_dir is not None else Path("data")
    for name in candidates:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


def torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter.

    The check is intentionally a runtime ``importlib.util.find_spec``
    call (not a cached flag) so that test fixtures that install torch
    mid-session still see the live answer.
    """
    import importlib.util as _il

    return _il.find_spec("torch") is not None


# ---------------------------------------------------------------------------
# Private helpers — hashing + state-shape integrity
# ---------------------------------------------------------------------------


def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """SHA-256-derived 32-bit seed from ``(batch_id, sample_id, source_round)``."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _digest_state(payload: Mapping[str, Any]) -> str:
    """SHA-256 hex digest of a payload (sorted keys, repr'd)."""
    return digest_state(payload)


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Deterministic hash-stable :class:`TensorRef`."""
    return make_ref("rf_cifar:image", label, **parts)


def _validate_state_shape(x: ArrayF64) -> ArrayF64:
    """Reshape ``x`` to ``RF_CIFAR_STATE_SHAPE`` (3, 32, 32) and float64."""
    arr = np.asarray(x, dtype=np.float64).reshape(RF_CIFAR_STATE_SHAPE)
    return arr


# ---------------------------------------------------------------------------
# Synthetic (NumPy) velocity field — test-only path; no torch dependency
# ---------------------------------------------------------------------------


def _synthetic_velocity_field(
    x: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> ArrayF64:
    """Evaluate a tiny per-pixel-affine velocity field on ``(3, 32, 32)``.

    The synthetic field is shaped as
    ``v_theta(x, t) = W2 @ tanh(W1 @ flatten(x) + b1 + t * t_bias) + b2``
    using two dense linear layers with hidden width
    :data:`RF_CIFAR_SYNTHETIC_HIDDEN`. The weights are random-init
    (deterministic via ``np.random.default_rng``) so the synthetic path
    is byte-deterministic for a fixed ``seed``. The field is **not** a
    trained FM model and is only used by the test suite to exercise the
    Protocol surface.
    """
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    w1 = np.asarray(weights["W1"], dtype=np.float64)
    b1 = np.asarray(weights["b1"], dtype=np.float64)
    w2 = np.asarray(weights["W2"], dtype=np.float64)
    b2 = np.asarray(weights["b2"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    h = np.tanh(flat @ w1 + b1 + float(t) * t_bias)
    out = h @ w2 + b2
    return np.asarray(out, dtype=np.float64).reshape(RF_CIFAR_STATE_SHAPE)


def _random_init_synthetic_weights(
    *,
    seed: int,
    hidden: int | None = None,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic velocity field's two linear layers.

    The hidden width defaults to :data:`RF_CIFAR_SYNTHETIC_HIDDEN` but
    can be overridden per-instance via the ``hidden`` keyword (used by
    the adapter when the caller sets ``synthetic_hidden`` to a non-
    default value).
    """
    rng = np.random.default_rng(int(seed))
    in_dim = 3 * 32 * 32
    hidden_w = int(hidden) if hidden is not None else int(RF_CIFAR_SYNTHETIC_HIDDEN)

    def kaiming(fan_in: int, fan_out: int) -> ArrayF64:
        bound = np.sqrt(6.0 / float(fan_in))
        return np.asarray(
            rng.uniform(-bound, bound, size=(fan_in, fan_out)),
            dtype=np.float64,
        )

    return {
        "W1": kaiming(in_dim, hidden_w),
        "b1": np.zeros(hidden_w, dtype=np.float64),
        "W2": kaiming(hidden_w, in_dim),
        "b2": np.zeros(in_dim, dtype=np.float64),
        "t_bias": rng.standard_normal(hidden_w).astype(np.float64),
    }


def _synthesize_image_like_tensor(rng: np.random.Generator) -> ArrayF64:
    """Sample an image-shape ``(3, 32, 32)`` array from ``N(0, I)``."""
    return rng.standard_normal(RF_CIFAR_STATE_SHAPE).astype(np.float64)


# ---------------------------------------------------------------------------
# Torch velocity field — production path; requires ``torch`` runtime
# ---------------------------------------------------------------------------


def _torch_velocity_field(
    unet: Any,
    x: ArrayF64,
    t: float,
    *,
    dtype: Any,
    device: Any,
) -> ArrayF64:
    """Call the PyTorch UNet velocity field ``v_theta(x, t)``.

    The function is intentionally NOT wrapped in a public class — it is
    invoked by :meth:`RectifiedFlowCIFARAdapter.solve_ode` only when
    the adapter is in ``torch`` mode. The NumPy ``(3, 32, 32)`` array
    is converted to ``torch.float64``, the UNet is called inside
    ``torch.no_grad()`` (inference-only determinism), and the result is
    cast back to a NumPy ``(3, 32, 32)`` float64 array.

    Returns a copy that the caller may mutate (Euler integrator).
    """
    import torch  # local import — torch is optional at the framework level.

    with torch.no_grad():
        x_t = torch.as_tensor(x, dtype=dtype, device=device).unsqueeze(0)
        t_t = torch.tensor([float(t)], dtype=dtype, device=device)
        v = unet(x_t, t_t)
        out = np.asarray(v.squeeze(0).detach().cpu().numpy(), dtype=np.float64)
    return out.reshape(RF_CIFAR_STATE_SHAPE)


def _load_torch_unet(weights_path: Path, *, device: Any) -> Any:
    """Load the published UNet ``state_dict`` and return the unet module.

    Two checkpoint layouts are recognised:

    1. **gnobitab Score-SDE DDPM++** (the published Liu 2022 CIFAR-10
       1-Rectified-Flow checkpoint). Detected either by the ``format``
       marker written by the weights-acquisition phase or by the
       ``module.all_modules.`` key prefix. The topology is rebuilt by
       :mod:`adaptive_reflow.adapters._gnobitab_ddpmpp`, which also folds
       the reference sampler's ``t * 999`` rescale into the wrapper so
       the caller integrates on ``t ∈ [0, 1]``.
    2. **Framework-native ``DDPMppUNet``** — the minimal builder below,
       used by checkpoints saved from this repo.
    """
    import torch  # local import.

    if weights_path.suffix == ".safetensors":
        try:
            from safetensors.torch import load_file
        except ImportError as exc:
            raise RuntimeError(
                "safetensors checkpoint requires the safetensors package"
            ) from exc
        raw: Any = load_file(str(weights_path), device=str(device))
    else:
        # Model checkpoints are data, not executable Python.  Refuse legacy
        # pickle objects so an untrusted checkpoint cannot execute on load.
        raw = torch.load(str(weights_path), map_location=device, weights_only=True)
    state_dict = raw.get("state_dict", raw) if isinstance(raw, dict) else raw
    fmt = raw.get("format") if isinstance(raw, dict) else None
    is_gnobitab = fmt == RF_CIFAR_FORMAT_GNOBITAB or any(
        str(k).startswith(("module.all_modules.", "all_modules."))
        for k in list(state_dict)[:8]
    )
    if is_gnobitab:
        from adaptive_reflow.adapters._gnobitab_ddpmpp import (
            load_gnobitab_rf_cifar_unet,
        )

        unet = load_gnobitab_rf_cifar_unet(state_dict, dtype=torch.float32)
    else:
        unet = _build_torch_unet_ddpmpp()
        unet.load_state_dict(state_dict)
    unet.to(device)
    unet.eval()
    for p in unet.parameters():
        p.requires_grad_(False)
    return unet


def _build_torch_unet_ddpmpp() -> Any:
    """Construct the published RF DDPM++ UNet (Liu 2022 §3.2).

    The architecture matches the published ``gnobitab/RectifiedFlow``
    reference: 3 input channels (RGB), ``base_ch=128``, ``ch_mult=
    (1, 2, 2, 2)``, two residual blocks per stage, GroupNorm + SiLU,
    sinusoidal time embedding (128-dim, 4 frequencies). Image size is
    fixed at 32×32 to match CIFAR-10.

    NOTE — This builder is intentionally minimal: it instantiates the
    network topology so that ``state_dict`` load works, but it does not
    require the actual published checkpoint to be present (the
    ``synthetic`` mode is the test-time path). The published check-
    point must be supplied at adapter construction time for the
    baseline reproduction (§4 of the plan).
    """
    import torch
    import torch.nn as nn

    base_ch = 128
    ch_mult = (1, 2, 2, 2)
    n_res_blocks = 2
    time_dim = 128

    class _SinusoidalTimeEmbed(nn.Module):
        def __init__(self, dim: int) -> None:
            super().__init__()
            self.dim = int(dim)
            half = self.dim // 2
            freqs = torch.exp(-np.log(np.float64(10000.0)) * torch.arange(half).float() / float(half))
            self.register_buffer("_freqs", freqs)

        def forward(self, t: torch.Tensor) -> torch.Tensor:
            args = t.float()[:, None] * self._freqs[None]
            return torch.cat([torch.cos(args), torch.sin(args)], dim=-1)

    class _ResBlock(nn.Module):
        def __init__(self, in_ch: int, out_ch: int) -> None:
            super().__init__()
            self.norm1 = nn.GroupNorm(32, in_ch)
            self.conv1 = nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1)
            self.time = nn.Linear(time_dim, out_ch)
            self.norm2 = nn.GroupNorm(32, out_ch)
            self.conv2 = nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1)
            self.skip = (
                nn.Conv2d(in_ch, out_ch, kernel_size=1)
                if in_ch != out_ch
                else nn.Identity()
            )
            self.act = nn.SiLU()

        def forward(self, x: torch.Tensor, t_emb: torch.Tensor) -> torch.Tensor:
            h = self.conv1(self.act(self.norm1(x)))
            h = h + self.time(self.act(t_emb))[:, :, None, None]
            h = self.conv2(self.act(self.norm2(h)))
            return h + self.skip(x)

    class _Downsample(nn.Module):
        def __init__(self, ch: int) -> None:
            super().__init__()
            self.op = nn.Conv2d(ch, ch, kernel_size=3, stride=2, padding=1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.op(x)

    class _Upsample(nn.Module):
        def __init__(self, ch: int) -> None:
            super().__init__()
            self.op = nn.Conv2d(ch, ch, kernel_size=3, padding=1)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = nn.functional.interpolate(x, scale_factor=2.0, mode="nearest")
            return self.op(x)

    class DDPMppUNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.time_embed = _SinusoidalTimeEmbed(time_dim)
            self.time_mlp = nn.Sequential(
                nn.Linear(time_dim, time_dim),
                nn.SiLU(),
                nn.Linear(time_dim, time_dim),
            )
            chs = [base_ch * m for m in ch_mult]
            self.conv_in = nn.Conv2d(3, chs[0], kernel_size=3, padding=1)
            self.downs = nn.ModuleList()
            cur = chs[0]
            for i, out_ch in enumerate(chs):
                blocks = nn.ModuleList()
                for _ in range(n_res_blocks):
                    blocks.append(_ResBlock(cur, out_ch))
                    cur = out_ch
                down = _Downsample(cur) if i < len(chs) - 1 else nn.Identity()
                self.downs.append(nn.ModuleList([blocks, down]))
            self.mid_res1 = _ResBlock(cur, cur)
            self.mid_res2 = _ResBlock(cur, cur)
            self.ups = nn.ModuleList()
            for i, out_ch in enumerate(reversed(chs)):
                blocks = nn.ModuleList()
                for _ in range(n_res_blocks + 1):
                    blocks.append(_ResBlock(cur, out_ch))
                    cur = out_ch
                up = _Upsample(cur) if i < len(chs) - 1 else nn.Identity()
                self.ups.append(nn.ModuleList([blocks, up]))
            self.norm_out = nn.GroupNorm(32, cur)
            self.conv_out = nn.Conv2d(cur, 3, kernel_size=3, padding=1)
            self.act = nn.SiLU()

        def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
            t_emb = self.time_mlp(self.time_embed(t))
            h = self.conv_in(x)
            for blocks, down in self.downs:
                for blk in blocks:
                    h = blk(h, t_emb)
                h = down(h)
            h = self.mid_res1(h, t_emb)
            h = self.mid_res2(h, t_emb)
            for blocks, up in self.ups:
                for blk in blocks:
                    h = blk(h, t_emb)
                h = up(h)
            return self.conv_out(self.act(self.norm_out(h)))

    return DDPMppUNet()


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RectifiedFlowCIFARCapabilities(AdapterCapabilities):
    """Capability surface for :class:`RectifiedFlowCIFARAdapter`."""

    def __init__(self) -> None:  # noqa: D401 — dataclass __init__ override
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            state_shape=RF_CIFAR_STATE_SHAPE,
            supported_channels=RF_CIFAR_CHANNELS,
            channel_domains=RF_CIFAR_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=RF_CIFAR_CONFIG_HASH,
            native_config_version=RF_CIFAR_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter)
class RectifiedFlowCIFARAdapter(FlowMatchingODEAdapter):
    """Rectified Flow (Liu 2022) on CIFAR-10 32×32.

    Wraps the published velocity-field UNet (``state_dict`` checkpoint)
    into the :class:`FlowMatchingODEAdapter` Protocol so that the
    framework's algorithm-layer code can drive it without modification.

    Two operating modes (per :data:`Mode`):

    * ``torch`` — production path. Loads the UNet ``state_dict`` via
      :mod:`torch` and calls the network in
      ``torch.no_grad()``/``eval()`` mode on each integration step.
      Requires the ``[rf-cifar]`` extra.
    * ``synthetic`` — testing-only path. Uses a deterministic NumPy
      velocity field with random init. The synthetic field is NOT a
      trained FM model — it is a Protocol-surface shim that lets the
      test suite exercise every method without the heavy torch
      dependency.

    Constructor parameters
    ----------------------

    * ``weights_path`` — explicit path to the published UNet
      ``state_dict``. When ``None``, the adapter falls back to
      ``data/rectified_flow_cifar10.safetensors`` /
      ``data/rectified_flow_cifar10.pth`` /
      ``data/rectified_flow_cifar10.pt`` in order; if none of those
      exist, the adapter switches to ``synthetic`` mode.
    * ``force_mode`` — ``"torch"`` / ``"synthetic"`` / ``"auto"``
      (default). ``"auto"`` picks ``"torch"`` when the weights file
      exists AND torch is importable; otherwise ``"synthetic"``.
    * ``num_steps`` — default number of Euler integration steps per
      round (paper uses 2-NFE Euler; the framework can override via
      ``condition.delta_spec["num_steps"]``).
    * ``solver`` — ``"euler"`` (default) or ``"heun"``. ``"euler"`` is
      the 1st-order baseline (1 NFE per step). ``"heun"`` is the 2nd-
      order predictor-corrector (2 NFE per step): Euler trial step at
      ``t+dt`` + trapezoidal corrector. Cost is ~2x wall-clock per step;
      quality improvement at matched NFE is ~30-40% per the EDM /
      Rectified-Flow literature. See
      ``docs/r4-survey/21-fix-v2-plan.md`` §1.2 / §3.2.
    """

    pinned_num_steps: int = RF_CIFAR_NUM_STEPS_DEFAULT
    # F14 (runner.py:774-783): the runner reads
    # ``getattr(self._adapter, "state_shape", (2,))`` for its forward-
    # noise allocation. We expose the adapter's state shape as both a
    # class attribute and an instance attribute so the runner's fallback
    # is never exercised for this adapter.
    state_shape: tuple[int, ...] = RF_CIFAR_STATE_SHAPE

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        num_steps: int = RF_CIFAR_NUM_STEPS_DEFAULT,
        seed_offset: int = 0,
        synthetic_hidden: int = RF_CIFAR_SYNTHETIC_HIDDEN,
        synthetic_seed: int = RF_CIFAR_SYNTHETIC_SEED_DEFAULT,
        solver: str = RF_CIFAR_INTEGRATOR_EULER,
        device: str = "cpu",
        enable_paper_uplift_27: bool = False,
        paper_uplift_27_e_rho: float | None = None,
    ) -> None:
        if int(num_steps) <= 0:
            raise ValueError(ERR_RF_CIFAR_NUM_STEPS)
        if int(synthetic_hidden) <= 0:
            raise ValueError("synthetic_hidden_must_be_positive")
        if str(solver) not in RF_CIFAR_INTEGRATORS:
            raise ValueError(
                f"{ERR_RF_CIFAR_INTEGRATOR_UNKNOWN}:{solver!r}"
                f"; expected one of {RF_CIFAR_INTEGRATORS!r}"
            )
        self._num_steps = int(num_steps)
        self._seed_offset = int(seed_offset)
        self._synthetic_hidden = int(synthetic_hidden)
        self._synthetic_seed = int(synthetic_seed)
        self._solver: str = str(solver)
        self._device_name = str(device)
        # Paper-uplift-27 (P0-A12 — Lemma 5): when enabled, the
        # apply_restart_distribution floor is lifted to max(1-beta, e_rho/4).
        # Default e_rho mirrors the paper defaults (rho=0.1, eta=0.1) so
        # callers can opt in with a single boolean.
        self._enable_paper_uplift_27: bool = bool(enable_paper_uplift_27)
        if paper_uplift_27_e_rho is None:
            # Paper defaults: rho=0.1, eta=0.1 -> e_rho = min(rho**4, (1-rho)**2 * eta**2) = 1e-4.
            self._paper_uplift_27_e_rho: float | None = float(1e-4) if self._enable_paper_uplift_27 else None
        else:
            self._paper_uplift_27_e_rho = float(paper_uplift_27_e_rho) if float(paper_uplift_27_e_rho) > 0.0 else None
        if self._enable_paper_uplift_27 and self._paper_uplift_27_e_rho is None:
            raise ValueError("enable_paper_uplift_27_requires_positive_e_rho")

        # Resolve weights path.
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or rectified_flow_cifar_resolve_weights_path()
        self._weights_path = Path(resolved) if resolved is not None else Path("synthetic")

        # Decide operating mode.
        if force_mode == "auto":
            if self._weights_path.exists() and torch_is_available():
                self._mode: Mode = "torch"
            else:
                self._mode = "synthetic"
        elif force_mode == "torch":
            if not torch_is_available():
                raise RuntimeError("torch requested but not installed")
            if not self._weights_path.exists():
                raise FileNotFoundError(f"{ERR_RF_CIFAR_WEIGHTS_MISSING}:{self._weights_path}")
            self._mode = "torch"
        elif force_mode == "synthetic":
            self._mode = "synthetic"
        else:
            raise ValueError(f"unknown_force_mode:{force_mode}")

        # Backend handles.
        self._unet: Any = None
        self._torch_dtype: Any = None
        self._torch_device: Any = None
        self._synthetic_weights: dict[str, ArrayF64] | None = None
        if self._mode == "torch":
            try:
                import torch as _torch  # local

                self._torch_device = _torch.device(self._device_name)
                if self._torch_device.type == "cuda" and not _torch.cuda.is_available():
                    raise RuntimeError("cuda requested but not available")
                self._unet = _load_torch_unet(
                    self._weights_path, device=self._torch_device
                )
                # The published weights are float32; running the UNet in
                # float64 on CPU roughly doubles the wall-clock for no
                # accuracy gain (the integrator state stays float64).
                self._torch_dtype = _torch.float32
            except ImportError:
                # Should never happen — torch_is_available() returned True.
                self._mode = "synthetic"
        if self._mode == "synthetic":
            self._synthetic_weights = _random_init_synthetic_weights(
                hidden=int(self._synthetic_hidden),
                seed=int(self._synthetic_seed),
            )

        # LRU-bounded native-states cache (audit A-3 mirror of twodim_fm).
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = RectifiedFlowCIFARCapabilities()
        # Paper-uplift-27 audit-code buffer (counted post-hoc for AC3).
        self._audit_codes_buffer: list[str] = []

    # ------------------------------------------------------------------
    # 1. capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. helpers — LRU-bounded native_states
    # ------------------------------------------------------------------

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > RF_CIFAR_NATIVE_STATES_MAXSIZE:
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        self._native_states.pop(digest, None)

    # ------------------------------------------------------------------
    # 2. build_initial_state
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        seed = _seed_from_ids(
            str(batch_id),
            str(sample_id),
            int(self._seed_offset) + 0,
        )
        rng = np.random.default_rng(seed)
        x0 = _synthesize_image_like_tensor(rng)
        digest = _digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "shape": [int(s) for s in x0.shape],
                "x0_first": [
                    float(x0[0, 0, 0]),
                    float(x0[0, 0, 1]),
                    float(x0[0, 1, 0]),
                ],
            }
        )
        self._put_native_state(
            digest,
            {
                "x0": np.asarray(x0, dtype=np.float64).reshape(RF_CIFAR_STATE_SHAPE),
                "source_round": 0,
                "mode": self._mode,
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("image"): _make_ref(
                    "initial",
                    batch=batch_id,
                    sample=sample_id,
                ),
            },
            masks={},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=digest,
            provenance=("rectified_flow_cifar@v1",),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        return bundle

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: RestartPolicy,
    ) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )

        beta, memory_fraction = memory_fraction_for(
            policy,
            ChannelName("image"),
            exterior_gap_e_rho=self._paper_uplift_27_e_rho,
            audit_codes=self._audit_codes_buffer,
        )
        prior_value = prior_entry["x0"]
        prior_x = np.asarray(prior_value, dtype=np.float64).reshape(
            RF_CIFAR_STATE_SHAPE
        )
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_x = _synthesize_image_like_tensor(np.random.default_rng(restart_seed))

        m = max(0.0, min(1.0, float(memory_fraction)))
        blended = (m * prior_x + (1.0 - m) * fresh_x).astype(np.float64)
        blended = np.clip(blended, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)

        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "beta": float(beta),
                "memory_fraction": float(memory_fraction),
                "blended_first": [
                    float(blended[0, 0, 0]),
                    float(blended[0, 0, 1]),
                    float(blended[0, 1, 0]),
                ],
            }
        )
        self._put_native_state(
            next_digest,
            {
                "x0": blended,
                "source_round": next_round,
                "mode": self._mode,
            },
        )
        provenance = tuple(state.provenance) + (AUDIT_RF_CIFAR_RESTART_BLEND,)
        return StateBundle(
            channels={
                ChannelName("image"): _make_ref(
                    "restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(next_digest),
            provenance=provenance,
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        del bundle
        new_spec = dict(delta.delta_spec)
        new_spec.setdefault("target_distribution", "cifar10")
        new_spec.setdefault("integrator_config_hash", RF_CIFAR_CONFIG_HASH)
        # The paper's headline baseline is 2-NFE Euler; the framework's
        # condition.delta_spec can override this per-round.
        new_spec.setdefault("num_steps", RF_CIFAR_NUM_STEPS_DEFAULT)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def _velocity_field(self, x: ArrayF64, t: float) -> ArrayF64:
        """Evaluate the velocity field at ``(x, t)`` for the active backend.

        Internal dispatch helper used by :meth:`solve_ode` and
        :meth:`batched_inference`. ``torch`` mode delegates to the
        PyTorch UNet (see :func:`_torch_velocity_field`); ``synthetic``
        mode uses the deterministic NumPy field. Returns a NumPy
        ``(3, 32, 32)`` float64 array (copy-safe to mutate).
        """
        if self._mode == "torch":
            assert self._unet is not None
            return _torch_velocity_field(
                self._unet,
                x,
                t,
                dtype=self._torch_dtype,
                device=self._torch_device,
            )
        assert self._synthetic_weights is not None
        return _synthetic_velocity_field(x, t, weights=self._synthetic_weights)

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )
        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError(ERR_RF_CIFAR_NUM_STEPS)
        x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            RF_CIFAR_STATE_SHAPE
        )

        solver_kind = str(self._solver)
        t_grid = np.linspace(0.0, float(RF_CIFAR_T_END), num_steps + 1, dtype=np.float64)
        traj = np.empty((t_grid.size, *RF_CIFAR_STATE_SHAPE), dtype=np.float64)
        traj[0] = x0.copy()
        x_cur = x0.copy()
        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            v1 = self._velocity_field(x_cur, t0)
            if solver_kind == RF_CIFAR_INTEGRATOR_HEUN and i < t_grid.size - 1:
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(
                    x_cur + dt * v1, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP
                )
                # Corrector: trapezoidal average using v(x_pred, t+dt).
                # The final step has no ``t+dt`` within the integration
                # range so the corrector is skipped (matches k-diffusion
                # ``sample_heun`` at ``sigma_next == 0``).
                v2 = self._velocity_field(x_pred, t1)
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -RF_CIFAR_CLAMP,
                    RF_CIFAR_CLAMP,
                )
            else:
                x_cur = np.clip(
                    x_cur + dt * v1, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP
                )
            traj[i] = x_cur

        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "integrator": str(solver_kind),
                "num_steps": int(num_steps),
                "shape": [int(traj.shape[0]), int(traj.shape[1]), int(traj.shape[2])],
                "x0_first": [
                    float(x0[0, 0, 0]),
                    float(x0[0, 0, 1]),
                    float(x0[0, 1, 0]),
                ],
                "mode": self._mode,
            }
        )
        self._put_native_state(
            traj_digest,
            {
                "trajectory": traj,
                "t_grid": t_grid,
                "mode": self._mode,
            },
        )
        cfg_blob = repr(
            ("rf_cifar_config", str(solver_kind), int(num_steps), int(seed))
        ).encode("utf-8")
        integrator_config_hash = hashlib.sha256(cfg_blob).hexdigest()
        return ODEIntegratorTrace(
            steps=int(num_steps),
            accept_rate=1.0,
            native_state_digest=traj_digest,
            integrator_config_hash=integrator_config_hash,
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=trace.native_state_digest
            )
        trajectory = np.asarray(traj_entry["trajectory"], dtype=np.float64)
        x_final = np.asarray(trajectory[-1], dtype=np.float64).reshape(
            RF_CIFAR_STATE_SHAPE
        )
        endpoint_digest = _digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "x_final_first": [
                    float(x_final[0, 0, 0]),
                    float(x_final[0, 0, 1]),
                    float(x_final[0, 1, 0]),
                ],
                "t_final": float(RF_CIFAR_T_END),
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "x": np.asarray(x_final, dtype=np.float64).reshape(RF_CIFAR_STATE_SHAPE),
                # ``apply_restart_distribution`` accepts either key so
                # endpoint bundles can be fed directly into the next round.
                "x0": np.asarray(x_final, dtype=np.float64).reshape(RF_CIFAR_STATE_SHAPE),
                "t": float(RF_CIFAR_T_END),
                "mode": self._mode,
            },
        )
        next_round = int(state.source_round) + 1
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=endpoint_digest,
            provenance=tuple(state.provenance) + (AUDIT_RF_CIFAR_OBSERVED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> ArrayF64 | None:
        """Return the native ``(T, 3, 32, 32)`` trajectory for ``trace``."""
        entry = self._native_states.get(trace.native_state_digest)
        if entry is None:
            return None
        traj = entry.get("trajectory")
        if traj is None:
            return None
        return np.asarray(traj, dtype=np.float64)

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (optional — P0-7 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """Inject ``injected`` (shape ``(3, 32, 32)``) into the bundle's prior.

        Returns a fresh :class:`StateBundle` whose prior x0 has been
        updated to ``x + injected`` (clipped to ``[-RF_CIFAR_CLAMP,
        RF_CIFAR_CLAMP]``) and whose ``provenance`` records the
        :data:`AUDIT_FORWARD_NOISE_APPLIED` tag.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        x_prior = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            RF_CIFAR_STATE_SHAPE
        )
        x_new_arr = np.asarray(injected, dtype=np.float64).reshape(RF_CIFAR_STATE_SHAPE)
        x_new = np.clip(x_prior + x_new_arr, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)
        new_digest = _digest_state(
            {
                "kind": "forward_noise",
                "src_digest": bundle.native_state_digest,
                "shape": [int(s) for s in x_new.shape],
                "x_first": [
                    float(x_new[0, 0, 0]),
                    float(x_new[0, 0, 1]),
                    float(x_new[0, 1, 0]),
                ],
            }
        )
        self._put_native_state(
            new_digest,
            {
                "x0": x_new,
                "source_round": int(bundle.source_round),
                "mode": self._mode,
            },
        )
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance) + (AUDIT_FORWARD_NOISE_APPLIED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 11. batched_inference (heavy path — vanilla baseline + framework FIDs)
    # ------------------------------------------------------------------

    def batched_inference(
        self,
        n_samples: int,
        *,
        num_steps: int | None = None,
        seed: int = 0,
        solver: str | None = None,
    ) -> ArrayF64:
        """Return ``(n_samples, 3, 32, 32)`` samples from the velocity field.

        This is the *vanilla inference* path used by the baseline
        reproduction (§4 of the plan) and the framework FID
        computation (§5.4). Each sample is drawn from
        ``N(0, I_{3×32×32})`` and integrated forward over the
        ``t_grid`` with ``num_steps`` Euler steps (or Heun 2nd-order
        steps when ``solver='heun'``).

        The ``solver`` argument overrides the adapter's default
        ``solver`` constructor argument for this call only. When
        ``None``, the constructor setting is used.

        Byte-deterministic for fixed ``(seed, num_steps, weights, solver)``.
        """
        if int(n_samples) <= 0:
            raise ValueError("n_samples_must_be_positive")
        steps = int(num_steps) if num_steps is not None else self._num_steps
        if steps <= 0:
            raise ValueError(ERR_RF_CIFAR_NUM_STEPS)
        solver_kind = str(self._solver if solver is None else solver)
        if solver_kind not in RF_CIFAR_INTEGRATORS:
            raise ValueError(
                f"{ERR_RF_CIFAR_INTEGRATOR_UNKNOWN}:{solver_kind!r}"
                f"; expected one of {RF_CIFAR_INTEGRATORS!r}"
            )
        rng = np.random.default_rng(int(seed))
        x0_batch = rng.standard_normal((int(n_samples), *RF_CIFAR_STATE_SHAPE)).astype(
            np.float64
        )
        t_grid = np.linspace(0.0, float(RF_CIFAR_T_END), steps + 1, dtype=np.float64)
        x_cur = x0_batch.copy()
        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            if self._mode == "torch":
                assert self._unet is not None
                v1 = _batched_torch_velocity_field(
                    self._unet, x_cur, t0, dtype=self._torch_dtype, device=self._torch_device
                )
            else:
                assert self._synthetic_weights is not None
                v1 = _batched_synthetic_velocity_field(
                    x_cur, t0, weights=self._synthetic_weights
                )
            if solver_kind == RF_CIFAR_INTEGRATOR_HEUN and i < t_grid.size - 1:
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(x_cur + dt * v1, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)
                if self._mode == "torch":
                    assert self._unet is not None
                    v2 = _batched_torch_velocity_field(
                        self._unet, x_pred, t1, dtype=self._torch_dtype, device=self._torch_device
                    )
                else:
                    assert self._synthetic_weights is not None
                    v2 = _batched_synthetic_velocity_field(
                        x_pred, t1, weights=self._synthetic_weights
                    )
                # Corrector: trapezoidal average.
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -RF_CIFAR_CLAMP,
                    RF_CIFAR_CLAMP,
                )
            else:
                x_cur = np.clip(x_cur + dt * v1, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)
        return np.asarray(x_cur, dtype=np.float64).reshape(
            (int(n_samples), *RF_CIFAR_STATE_SHAPE)
        )


def _batched_synthetic_velocity_field(
    x_batch: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> ArrayF64:
    """Batched version of :func:`_synthetic_velocity_field` for shape ``(B, 3, 32, 32)``."""
    flat = np.asarray(x_batch, dtype=np.float64).reshape(x_batch.shape[0], -1)
    w1 = np.asarray(weights["W1"], dtype=np.float64)
    b1 = np.asarray(weights["b1"], dtype=np.float64)
    w2 = np.asarray(weights["W2"], dtype=np.float64)
    b2 = np.asarray(weights["b2"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    h = np.tanh(flat @ w1 + b1 + float(t) * t_bias)
    out = h @ w2 + b2
    return np.asarray(out, dtype=np.float64).reshape(x_batch.shape)


def _batched_torch_velocity_field(
    unet: Any,
    x_batch: ArrayF64,
    t: float,
    *,
    dtype: Any,
    device: Any,
    chunk_size: int = RF_CIFAR_TORCH_CHUNK,
) -> ArrayF64:
    """Batched torch velocity field for shape ``(B, 3, 32, 32)``.

    The batch is evaluated in slices of at most ``chunk_size`` so the
    published DDPM++ self-attention block (which materialises a
    ``(B, 16, 16, 16, 16)`` attention tensor) stays within CPU memory
    for large ``B``.
    """
    import torch  # local import.

    n = int(x_batch.shape[0])
    step = max(1, int(chunk_size))
    out = np.empty(x_batch.shape, dtype=np.float64)
    with torch.no_grad():
        for start in range(0, n, step):
            stop = min(start + step, n)
            x_t = torch.as_tensor(
                np.ascontiguousarray(x_batch[start:stop]), dtype=dtype, device=device
            )
            t_t = torch.full((stop - start,), float(t), dtype=dtype, device=device)
            out[start:stop] = unet(x_t, t_t).detach().cpu().numpy().astype(np.float64)
    return out.reshape(x_batch.shape)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_rectified_flow_cifar_adapter(
    *,
    weights_path: Path | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    num_steps: int = RF_CIFAR_NUM_STEPS_DEFAULT,
    solver: str = RF_CIFAR_INTEGRATOR_EULER,
    device: str = "cpu",
) -> RectifiedFlowCIFARAdapter:
    """Default factory for :class:`RectifiedFlowCIFARAdapter`.

    When ``weights_path`` is ``None`` the adapter resolves
    ``data/rectified_flow_cifar10.safetensors`` /
    ``data/rectified_flow_cifar10.pth`` /
    ``data/rectified_flow_cifar10.pt`` in priority order; when none of
    those exist and ``force_mode`` is ``"auto"``, the adapter falls
    back to ``synthetic`` mode (testing-only).

    The ``solver`` parameter selects the integrator: ``"euler"`` (1st-
    order, default) or ``"heun"`` (2nd-order predictor-corrector).
    """
    return RectifiedFlowCIFARAdapter(
        weights_path=weights_path,
        force_mode=force_mode,
        num_steps=num_steps,
        solver=solver,
        device=device,
    )


__all__ = [
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_RF_CIFAR_OBSERVED",
    "AUDIT_RF_CIFAR_RESTART_BLEND",
    "ERR_RF_CIFAR_INTEGRATOR_UNKNOWN",
    "ERR_RF_CIFAR_NUM_STEPS",
    "ERR_RF_CIFAR_WEIGHTS_MISSING",
    "RF_CIFAR_CHANNELS",
    "RF_CIFAR_CHANNEL_DOMAINS",
    "RF_CIFAR_CLAMP",
    "RF_CIFAR_CONFIG_HASH",
    "RF_CIFAR_CONFIG_VERSION",
    "RF_CIFAR_FORMAT_GNOBITAB",
    "RF_CIFAR_HEIGHT",
    "RF_CIFAR_INTEGRATOR_EULER",
    "RF_CIFAR_INTEGRATOR_HEUN",
    "RF_CIFAR_INTEGRATORS",
    "RF_CIFAR_NATIVE_STATES_MAXSIZE",
    "RF_CIFAR_NUM_STEPS_DEFAULT",
    "RF_CIFAR_STATE_SHAPE",
    "RF_CIFAR_SYNTHETIC_HIDDEN",
    "RF_CIFAR_SYNTHETIC_SEED_DEFAULT",
    "RF_CIFAR_T_END",
    "RF_CIFAR_TORCH_CHUNK",
    "RF_CIFAR_WEIGHTS_CANDIDATES",
    "RF_CIFAR_WIDTH",
    "RectifiedFlowCIFARAdapter",
    "RectifiedFlowCIFARCapabilities",
    "default_rectified_flow_cifar_adapter",
    "rectified_flow_cifar_resolve_weights_path",
    "torch_is_available",
]
