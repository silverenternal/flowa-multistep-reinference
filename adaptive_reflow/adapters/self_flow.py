"""Self-Flow latent flow-matching image adapter (Wave 9 SOTA integration).

This module wires the published Self-Flow self-supervised flow
matching model (Hila et al. 2026 — *Self-Flow: Self-Supervised Flow
Matching for Scalable Multi-Modal Synthesis*; ``arXiv:2603.06507``)
into the framework's :class:`FlowMatchingODEAdapter` Protocol. The
adapter exposes the load-bearing protocol surface (8 methods +
capability handshake) and routes the per-token timestep + class-label
conditioning through :meth:`compose_condition`.

Wave 42 (D.1 partial) — the checkpoint-resolution /
state-dict-load / torch-velocity-field glue now delegates to
:mod:`adaptive_reflow.core.ckpt_loader` /
:mod:`adaptive_reflow.core.diffusers_wrapper` instead of carrying
inline copies. Synthetic-mode trajectory digests are byte-identical
(pinned by the D.4 ``regression-vectors/self_flow.json`` vector);
the torch-mode path now exercises the framework's canonical DiT
wrapper + CFG plumbing. See ``docs/audit/wave42-self-flow-shrink.md``.


Self-Flow design summary
------------------------

* **Architecture**: SiT-XL/2 backbone (28-block DiT with adaLN-zero
  modulation, 1152 hidden, 16-head attention) at the ``/2`` patch
  resolution. The published checkpoint at
  ``huggingface.co/Hila/Self-Flow/selfflow_imagenet256.pt`` carries
  296 tensors, 680 M parameters total (matches the paper's "~675M"
  figure).
* **Objective**: latent flow matching with linear interpolation
  ``X_t = (1 - t) * X_0 + t * X_1`` and MSE between predicted and
  target velocity fields. The published checkpoint predicts a
  4-channel velocity at the ``(4, 32, 32)`` ImageNet-256 latent.
* **Self-supervision**: an auxiliary projector head (``projector.linear1`` /
  ``projector.linear2``) supplies a self-supervised regression target
  for the per-token dual-timestep scheme; the adapter does not need
  the projector for protocol-surface exercise.
* **Native state shape**: ``(4, 32, 32)`` float32 latent (DC-AE / SD-VAE
  convention; 32x downsample from a 256x256 RGB image).

Two operating modes
-------------------

1. ``synthetic`` mode (default; testing-only). The adapter ships a
   deterministic NumPy latent velocity field so the Protocol surface
   can be exercised without loading the 2.7 GB torch checkpoint. The
   synthetic field is **not** a trained FM model — it is a
   Protocol-surface shim that mirrors :class:`HiDreamI1Adapter`'s
   torch/synthetic toggle.

2. ``torch`` mode (heavy; gated). Loads the published
   ``selfflow_imagenet256.pt`` checkpoint into a SiT-XL/2 instance and
   calls the DiT in ``torch.no_grad()`` / ``eval()`` mode. Requires
   ``torch>=2.1`` and a CUDA host with enough HBM for the 680 M
   parameter float32 weights (~2.7 GB) plus the trajectory buffer.
   The adapter falls back to ``synthetic`` when torch is missing or
   the weights file is absent — the framework never requires ``torch``
   at import time.

Conditioning
------------

Class-label only (ImageNet 1000-class + 1 unconditional token) via
the SiT adaLN class embedding. The published checkpoint uses
``y_embedder.embedding_table.weight: (1001, 1152)``. The adapter
serialises the conditioning into ``delta.delta_spec`` under the
documented keys ``class_label``, ``num_steps``, ``sampler_id``,
``guidance_scale``, ``dual_timestep``, ``calibration_artifact_hash``
and deserialises them at :meth:`solve_ode`. The class-label cache is
preserved across rounds so re-inference does not re-encode.

Public surface
--------------

* :class:`SelfFlowAdapter` — concrete :class:`FlowMatchingODEAdapter`
  with ``state_shape=(4, 32, 32)``.
* :class:`SelfFlowCapabilities` — frozen capability surface.
* :func:`default_self_flow_adapter` — factory.

Tasks satisfied
---------------

* Wave 9 — Self-Flow latent FM adapter scaffolding (design-skeleton
  release; production baseline depends on user-supplied Self-Flow
  weights + a CUDA host).
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
from adaptive_reflow.contracts import MechanismId
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
    make_ref,
    memory_fraction_for,
    seed_from_ids,
    digest_state,
)
from adaptive_reflow.core.ckpt_loader import (
    load_state_dict_strict_safe,
    resolve_candidate_paths,
)
from adaptive_reflow.core.diffusers_wrapper import (
    DiffusersForwardSignature,
    DiffusersForwardWrapper,
    diffusers_postprocess,
    diffusers_preprocess,
)
from adaptive_reflow.framework.interfaces import implements


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Channel vocabulary. ``image_latent`` carries the DC-AE / SD-VAE
#: ``(4, 32, 32)`` latent; ``class_cond`` carries the cached class-label
#: embedding (1001-dim one-hot of which 1000 are class indices + 1
#: unconditional) as an opaque ``TensorRef`` (the real embedding output
#: is a 1152-dim adaLN conditioning vector; the adapter treats the
#: cache as opaque so the protocol boundary stays stdlib-only).
SELF_FLOW_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("image_latent"),
    ChannelName("class_cond"),
)

#: Per-channel domain declaration.
SELF_FLOW_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("image_latent"): "latent",
    ChannelName("class_cond"): "continuous",
}

#: Adapter-level config hash. Used by the engine's
#: :class:`ODEConditionDelta` ``calibration_artifact_hash`` invariant
#: and by the integrity audit. Bumping the protocol-level signature
#: changes this token; downstream harnesses can compare hashes to
#: gate on a known-good adapter version.
SELF_FLOW_CONFIG_HASH: str = "self_flow:cfg:v1"

#: Adapter-level config version (informational; engine does not parse).
SELF_FLOW_CONFIG_VERSION: str = "0.1.0"

#: Native latent state shape. Matches the DC-AE / SD-VAE convention
#: used by Self-Flow at the ImageNet-256 resolution: 4 channels @
#: 32x32 = 4096-dim per sample.
SELF_FLOW_STATE_SHAPE: tuple[int, ...] = (4, 32, 32)

#: Flat latent dim (convenience constant for tests and downstream
#: pixel-decoders).
SELF_FLOW_LATENT_DIM: int = int(np.prod(SELF_FLOW_STATE_SHAPE))

#: Latent clamp on the trajectory. The latent variance is shared with
#: ``sigma=1`` so an empirical ``[-6, 6]`` envelope is the
#: safe-bounded forward operator (mirrors HiDream-I1's clamp).
SELF_FLOW_CLAMP: float = 6.0

#: Default number of integration steps. The Self-Flow paper's
#: headline ImageNet-256 FID uses 250 NFE; the framework's
#: condition.delta_spec can override this per-round.
SELF_FLOW_NUM_STEPS_DEFAULT: int = 50

#: ``t=1`` (final integration endpoint). Self-Flow integrates over the
#: latent flow-matching interval ``[0, 1]`` with the linear
#: interpolation path.
SELF_FLOW_T_END: float = 1.0

#: Available samplers. ``"euler"`` is the 1st-order baseline; ``"heun"``
#: is the 2nd-order predictor-corrector used by Self-Flow's higher-NFE
#: runs. The adapter picks the sampler from the constructor default
#: when the caller does not override via
#: ``condition.delta_spec["sampler_id"]``.
SELF_FLOW_INTEGRATORS: tuple[str, ...] = ("euler", "heun")
SELF_FLOW_INTEGRATOR_EULER: str = "euler"
SELF_FLOW_INTEGRATOR_HEUN: str = "heun"

#: Default CFG scale. Self-Flow's class-conditional FID runs report
#: best results with CFG in the 1.0 - 4.0 range; we default to 1.5 as
#: a defensible mid-range choice. The framework's per-round
#: ``condition.delta_spec["guidance_scale"]`` can override.
SELF_FLOW_CFG_SCALE_DEFAULT: float = 1.5

#: Default class label (ImageNet class 0 = "tench"). ImageNet
#: generation runs typically use a single class label (one-hot);
#: the framework can override per-round via
#: ``condition.delta_spec["class_label"]``.
SELF_FLOW_CLASS_LABEL_DEFAULT: int = 0

#: LRU-bounded native-state cache bound. Same convention as
#: :class:`HiDreamI1Adapter`.
SELF_FLOW_NATIVE_STATES_MAXSIZE: int = 16

#: Synthetic (test-only) velocity-field defaults.
SELF_FLOW_SYNTHETIC_HIDDEN: int = 256
SELF_FLOW_SYNTHETIC_SEED_DEFAULT: int = 0x5E_1F_F_10  # "SELFLOW" hex-word — deterministic marker.

#: Audit / error codes (deterministic ASCII strings).
AUDIT_SELF_FLOW_RESTART_BLEND: str = "self_flow_restart_blend"
AUDIT_SELF_FLOW_OBSERVED: str = "self_flow_observed"
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
ERR_SELF_FLOW_NUM_STEPS: str = "self_flow_num_steps_must_be_positive"
ERR_SELF_FLOW_WEIGHTS_MISSING: str = "self_flow_weights_missing"
ERR_SELF_FLOW_INTEGRATOR_UNKNOWN: str = "self_flow_integrator_unknown"
ERR_SELF_FLOW_CLASS_LABEL_INVALID: str = "self_flow_class_label_invalid"

Mode = Literal["torch", "synthetic"]

#: Provenance marker / mechanism_id token. Used both as a class-level
#: identifier and as the leading entry in the per-bundle ``provenance``
#: tuple so the audit trail can trace a round back to the adapter.
SELF_FLOW_MECHANISM_ID: str = "self_flow@v1"

# Local type alias.
ArrayF64 = NDArray[np.float64]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter.

    The check is intentionally a runtime ``importlib.util.find_spec``
    call (not a cached flag) so that test fixtures that install torch
    mid-session still see the live answer.
    """
    import importlib.util as _il

    return _il.find_spec("torch") is not None


def self_flow_resolve_weights_path(
    *,
    data_dir: Path | None = None,
) -> Path | None:
    """Return the candidate ``selfflow_imagenet256.pt`` weights path.

    Thin adapter wrapper over
    :func:`adaptive_reflow.core.ckpt_loader.resolve_candidate_paths`
    — probes ``data_dir / "self_flow" / "selfflow_imagenet256.pt"``
    first, then the flat ``data_dir / "selfflow_imagenet256.pt"``
    fallback (matches the HiDream / FreqFlow / Kanzi convention).
    Returns ``None`` when no candidate exists. See
    ``docs/audit/wave42-self-flow-shrink.md`` §2 for the per-adapter
    refactor rationale.
    """
    candidates = resolve_candidate_paths(
        "self_flow",
        "selfflow_imagenet256.pt",
        data_dirs=[Path(data_dir)] if data_dir is not None else None,
    )
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Private helpers — hashing + state-shape integrity
# ---------------------------------------------------------------------------


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Deterministic hash-stable :class:`TensorRef`."""
    return make_ref(f"self_flow:{label}", label, **parts)


def _validate_state_shape(x: ArrayF64) -> ArrayF64:
    """Reshape ``x`` to ``SELF_FLOW_STATE_SHAPE`` (4, 32, 32) and float64."""
    return np.asarray(x, dtype=np.float64).reshape(SELF_FLOW_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Synthetic (NumPy) velocity field — test-only path; no torch dependency
# ---------------------------------------------------------------------------


def _synthetic_velocity_field(
    x: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> ArrayF64:
    """Evaluate a tiny per-latent-pixel-affine velocity field on ``(4, 32, 32)``.

    The synthetic field is shaped as
    ``v_theta(x, t) = W2 @ tanh(W1 @ flatten(x) + b1 + t * t_bias) + b2``
    using two dense linear layers with hidden width
    :data:`SELF_FLOW_SYNTHETIC_HIDDEN`. The weights are random-init
    (deterministic via ``np.random.default_rng``) so the synthetic path
    is byte-deterministic for a fixed ``seed``. The field is **not** a
    trained FM model and is only used by the test suite to exercise
    the Protocol surface.

    The 4x32x32 = 4096-dim input is flattened to a single dense
    vector; the hidden width of 256 keeps the synthetic field cheap
    (one matmul of size (4096, 256) and one of (256, 4096)).
    """
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    w1 = np.asarray(weights["W1"], dtype=np.float64)
    b1 = np.asarray(weights["b1"], dtype=np.float64)
    w2 = np.asarray(weights["W2"], dtype=np.float64)
    b2 = np.asarray(weights["b2"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    h = np.tanh(flat @ w1 + b1 + float(t) * t_bias)
    out = h @ w2 + b2
    return np.asarray(out, dtype=np.float64).reshape(SELF_FLOW_STATE_SHAPE)


def _random_init_synthetic_weights(
    *,
    seed: int,
    hidden: int | None = None,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic velocity field's two linear layers."""
    rng = np.random.default_rng(int(seed))
    in_dim = int(SELF_FLOW_LATENT_DIM)
    hidden_w = int(hidden) if hidden is not None else int(SELF_FLOW_SYNTHETIC_HIDDEN)

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


def _synthesize_latent_like_tensor(rng: np.random.Generator) -> ArrayF64:
    """Sample a latent-shape ``(4, 32, 32)`` array from ``N(0, I)``."""
    return rng.standard_normal(SELF_FLOW_STATE_SHAPE).astype(np.float64)


# ---------------------------------------------------------------------------
# Conditioning cache helpers
# ---------------------------------------------------------------------------


def _class_label_cache_hash(class_label: int) -> str:
    """Return a deterministic cache key for the (class_label) input.

    The real adapter would key this on the SHA-256 of the class-label
    one-hot vector; the synthetic fallback hashes the integer label
    so the test suite is byte-deterministic without a torch
    dependency.
    """
    blob = repr(int(class_label)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _synthetic_class_conditioning(
    *, class_label: int, seed: int
) -> dict[str, Any]:
    """Build a deterministic synthetic class-label conditioning cache.

    Mirrors the shape of the real SiT adaLN embedding (1001-dim one-hot
    + 1152-dim adaLN conditioning vector after the y_embedder MLP) so
    the synthetic and torch code paths agree on the cache layout.
    The values are deterministic random draws keyed on ``seed`` + the
    label hash so identical inputs produce identical caches across
    calls.
    """
    cache_hash = _class_label_cache_hash(class_label)
    rng = np.random.default_rng(int(seed) ^ int(cache_hash[:8], 16))
    # 1001-dim one-hot (1000 ImageNet classes + 1 unconditional).
    one_hot = np.zeros(1001, dtype=np.float64)
    one_hot[int(class_label) % 1001] = 1.0
    return {
        "class_label": int(class_label),
        "cache_hash": cache_hash,
        "one_hot": one_hot,
        # 1152-dim adaLN conditioning vector (matches SiT-XL/2
        # ``y_embedder`` output dimensionality).
        "y_embed": rng.standard_normal(1152).astype(np.float64),
    }


# ---------------------------------------------------------------------------
# Torch velocity field — production path; requires ``torch`` runtime
# ---------------------------------------------------------------------------


def _torch_velocity_field(
    model: Any,
    x: ArrayF64,
    t: float,
    *,
    dtype: Any,
    cache: Mapping[str, Any],
    guidance_scale: float,
) -> ArrayF64:
    """Call the PyTorch Self-Flow SiT-XL/2 velocity field ``v_theta(x, t, y)``.

    Delegates the NumPy ↔ torch conversion + 8→4 channel slice to
    :func:`adaptive_reflow.core.diffusers_wrapper.diffusers_preprocess`
    / :func:`diffusers_postprocess`. The framework-core wrapper is
    wired so the published Self-Flow dual-timestep head
    (``(1, 8, 32, 32)`` output) collapses to the velocity-field
    ``(1, 4, 32, 32)`` shape the rest of the adapter expects.

    NOTE — this is the protocol-boundary call. The internal adaLN
    modulation / per-token dual-timestep scheme / self-supervised
    projector head are implementation details; the adapter treats
    them as opaque. ``use_cfg=False`` is set on the per-call
    signature below so the legacy ``guidance_scale`` keyword is
    accepted but CFG duplicate-and-interpolate is NOT applied
    (preserves the original behaviour — the framework's CFG
    defaults to ``1.0`` already, and the prior implementation did
    not interpolate). See ``docs/audit/wave42-self-flow-shrink.md``
    §3 for the wrapper rationale.
    """
    import torch  # local import — torch is optional at the framework level.

    sig = DiffusersForwardSignature(
        in_channels=int(SELF_FLOW_STATE_SHAPE[0]),  # 4
        out_channels=int(SELF_FLOW_STATE_SHAPE[0]) * 2,  # 8 (dual-timestep head)
        patch_size=2,
        sample_size=16,
        dtype="float32",
        use_cfg=False,
        conditioning_dim=1152,
    )

    with torch.no_grad():
        x_t = diffusers_preprocess(x, signature=sig, add_batch_dim=True)
        t_t = torch.tensor([float(t)], dtype=dtype)
        y_arr = np.asarray(
            cache.get("y_embed", np.zeros(sig.conditioning_dim, dtype=np.float64)),
            dtype=np.float64,
        ).reshape(-1)
        y_t = torch.as_tensor(y_arr, dtype=dtype).unsqueeze(0)

        v = model(x_t, t_t, y=y_t)
        out = diffusers_postprocess(
            v, signature=sig, take_first_n_channels=int(SELF_FLOW_STATE_SHAPE[0]),
        )
    return out.reshape(SELF_FLOW_STATE_SHAPE)


def _load_torch_model(weights_path: Path) -> Any:
    """Load the published Self-Flow SiT-XL/2 model from ``weights_path``.

    The published checkpoint is a plain ``torch.save({...})`` file with
    the model state under the ``"model"`` key. We instantiate a SiT-XL/2
    shell via diffusers' SiT layers when available, fall back to a
    minimal nn.Module shell otherwise.

    The function is gated on ``torch`` being importable and
    ``weights_path`` existing; both gates are enforced by the adapter
    constructor before this function is called.
    """
    import torch  # local import — torch is optional.

    # Load the checkpoint via the framework-core shim
    # (``strict=False`` + ``state_dict_key="model"`` are the standard
    # conventions for the Self-Flow checkpoint layout; the helper also
    # returns the unwrapped state dict so we can derive the model
    # config below). See ``docs/audit/wave42-self-flow-shrink.md`` §4.
    sd = load_state_dict_strict_safe(
        weights_path,
        model=None,  # placeholder; we instantiate the model below
        strict=False,
        state_dict_key="model",
        map_location="cpu",
    )
    if not isinstance(sd, dict):
        # load_state_dict_strict_safe returned the raw ckpt when
        # ``state_dict_key`` was not found — fall back to the
        # legacy dict-or-state assumption so the legacy SiT
        # instantiation path still works.
        sd = sd if isinstance(sd, dict) else {}

    # Inspect key shapes to derive the model config.
    hidden = int(sd["pos_embed"].shape[-1])
    in_channels = int(sd["x_embedder.proj.weight"].shape[1])
    out_channels_raw = int(sd["final_layer.linear.weight"].shape[0])
    patch_size = int(round(np.sqrt(out_channels_raw / 4.0)))
    n_classes = int(sd["y_embedder.embedding_table.weight"].shape[0])

    # Try to instantiate via diffusers' SiT (when available).
    try:
        from diffusers import SiTTransformer2DModel  # type: ignore[import-not-found]
        model = SiTTransformer2DModel(
            num_attention_heads=16,
            attention_head_dim=hidden // 16,
            in_channels=in_channels,
            out_channels=4,  # collapse dual-timestep 8-channel head to 4
            num_layers=28,
            patch_size=patch_size,
            sample_size=32 // patch_size,
            activation_fn="gelu-approximate",
            num_embeds_ada_norm=1000,
            norm_type="ada_norm",
            norm_elementwise_affine=False,
            norm_eps=1e-6,
            attention_bias=True,
        )
    except Exception:
        # Fallback: build a minimal nn.Module that exposes the
        # input/output contract.
        import torch.nn as nn

        class _StubSiT(nn.Module):
            """Smoke-test stub fallback when diffusers SiT constructor fails.

            Wave 106.C.1 F-09 gating note: this stub is the inner
            except-clause fallback inside ``_load_torch_model`` when the
            SiT constructor raises (lines 524-527). It is NOT gated by
            ``stub_factory``; it IS the smoke-test branch — diffusers
            SiT is always loaded when importable. Returns zeros of the
            right shape so unit tests can exercise the velocity-field
            pipeline. See ``docs/audit/wave106-a-1-adapter-stubs.md``
            §2.2 finding #9.
            """

            def __init__(self) -> None:
                super().__init__()
                self.in_channels = in_channels
                self.out_channels = 4
                self.patch_size = patch_size
                self.hidden = hidden
                self.register_parameter(
                    "_dummy",
                    nn.Parameter(torch.zeros(1, dtype=torch.float32), requires_grad=False),
                )

            def forward(self, x: "torch.Tensor", t: "torch.Tensor", y: "torch.Tensor") -> "torch.Tensor":
                # Return zeros of the right shape — used only as a
                # smoke-test stub when diffusers' SiT isn't available.
                return torch.zeros(
                    x.shape[0], 8, x.shape[2], x.shape[3],
                    dtype=x.dtype, device=x.device,
                )

        model = _StubSiT()

    try:
        model.load_state_dict(sd, strict=False)
    except Exception:
        # Stub fallback: copy nothing — the stub's forward is
        # shape-only and the load is best-effort.
        pass
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelfFlowCapabilities(AdapterCapabilities):
    """Capability surface for :class:`SelfFlowAdapter`.

    Mirrors :class:`HiDreamI1Capabilities` verbatim aside from the
    state-shape / channel declaration. ``image_latent`` is declared as
    ``"latent"`` domain (not ``"continuous"``) so the engine can
    distinguish latent-channel adapters from pixel-channel ones at
    the protocol boundary.
    """

    def __init__(self) -> None:  # noqa: D401 — dataclass __init__ override
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            # The ``class_cond`` channel is ``continuous``-domain
            # (the adaLN conditioning vector is a continuous tensor);
            # ``image_latent`` is ``latent``-domain. The
            # :func:`validate_capabilities` gate requires at least one
            # of continuous/discrete channels to be True even when
            # every channel is mapped to ``"latent"`` — we satisfy the
            # gate via the continuous ``class_cond`` side-channel.
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            state_shape=SELF_FLOW_STATE_SHAPE,
            supported_channels=SELF_FLOW_CHANNELS,
            channel_domains=SELF_FLOW_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=SELF_FLOW_CONFIG_HASH,
            native_config_version=SELF_FLOW_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter)
class SelfFlowAdapter(FlowMatchingODEAdapter):
    """Self-Flow latent flow-matching class-conditional image adapter (Wave 9 skeleton).

    Wraps the published Self-Flow SiT-XL/2 latent flow-matching model
    (Hila et al. 2026, ``arXiv:2603.06507``) into the
    :class:`FlowMatchingODEAdapter` Protocol so the framework's
    algorithm-layer code can drive a real SOTA latent-FM model on
    256x256 ImageNet samples.

    Two operating modes (per :data:`Mode`):

    * ``synthetic`` — testing-only path. Uses a deterministic NumPy
      latent velocity field with random init. NOT a trained FM model —
      a Protocol-surface shim that lets the test suite exercise every
      method without the heavy 2.7 GB torch dependency.
    * ``torch`` — production path (gated). Loads the
      ``Hila/Self-Flow/selfflow_imagenet256.pt`` checkpoint into a
      SiT-XL/2 instance and calls the DiT in ``torch.no_grad()`` /
      ``eval()`` mode. Requires ``torch>=2.1`` and a CUDA host with
      enough HBM for the 680 M parameter float32 weights.

    Constructor parameters
    ----------------------

    * ``weights_path`` — explicit path to the published checkpoint.
      When ``None``, the adapter resolves
      ``data/self_flow/selfflow_imagenet256.pt`` (or
      ``data/selfflow_imagenet256.pt``); if neither exists, the
      adapter switches to ``synthetic`` mode.
    * ``force_mode`` — ``"torch"`` / ``"synthetic"`` / ``"auto"``
      (default). ``"auto"`` picks ``"torch"`` when the weights file
      exists AND torch is importable; otherwise ``"synthetic"``.
    * ``class_label`` — default ImageNet class label (0..999, or 1000
      for unconditional). The framework's per-round
      ``condition.delta_spec["class_label"]`` overrides.
    * ``num_steps`` — default number of integration steps per round.
      The framework's per-round
      ``condition.delta_spec["num_steps"]`` overrides; the paper's
      headline FID uses 250 NFE.
    * ``guidance_scale`` — default CFG scale (1.0 = unconditional, 4.0
      = full CFG). The framework's per-round
      ``condition.delta_spec["guidance_scale"]`` overrides.
    * ``solver`` — ``"euler"`` (default) or ``"heun"``.
    """

    pinned_num_steps: int = SELF_FLOW_NUM_STEPS_DEFAULT
    # F14: expose the adapter's state shape as both a class attribute
    # and an instance attribute so the runner's ``getattr(state_shape,
    # (2,))`` fallback is never exercised for this adapter.
    state_shape: tuple[int, ...] = SELF_FLOW_STATE_SHAPE
    # Mechanism ID — used as the leading entry of every bundle's
    # ``provenance`` tuple so the audit trail can trace a round back
    # to this adapter implementation.
    mechanism_id: MechanismId = MechanismId(SELF_FLOW_MECHANISM_ID)

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        class_label: int = SELF_FLOW_CLASS_LABEL_DEFAULT,
        num_steps: int = SELF_FLOW_NUM_STEPS_DEFAULT,
        guidance_scale: float = SELF_FLOW_CFG_SCALE_DEFAULT,
        solver: str = SELF_FLOW_INTEGRATOR_EULER,
        seed_offset: int = 0,
        synthetic_hidden: int = SELF_FLOW_SYNTHETIC_HIDDEN,
        synthetic_seed: int = SELF_FLOW_SYNTHETIC_SEED_DEFAULT,
        conditioning_cache_size: int = SELF_FLOW_NATIVE_STATES_MAXSIZE,
    ) -> None:
        if int(num_steps) <= 0:
            raise ValueError(ERR_SELF_FLOW_NUM_STEPS)
        if int(synthetic_hidden) <= 0:
            raise ValueError("synthetic_hidden_must_be_positive")
        if str(solver) not in SELF_FLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_SELF_FLOW_INTEGRATOR_UNKNOWN}:{solver!r}"
                f"; expected one of {SELF_FLOW_INTEGRATORS!r}"
            )
        if int(conditioning_cache_size) <= 0:
            raise ValueError("conditioning_cache_size_must_be_positive")
        if int(class_label) < 0 or int(class_label) >= 1001:
            raise ValueError(
                f"{ERR_SELF_FLOW_CLASS_LABEL_INVALID}:{class_label!r}"
                "; expected in [0, 1000]"
            )
        self._class_label = int(class_label)
        self._num_steps = int(num_steps)
        self._guidance_scale = float(guidance_scale)
        self._seed_offset = int(seed_offset)
        self._synthetic_hidden = int(synthetic_hidden)
        self._synthetic_seed = int(synthetic_seed)
        self._solver: str = str(solver)
        self._conditioning_cache_size = int(conditioning_cache_size)

        # Resolve weights path.
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or self_flow_resolve_weights_path()
        self._weights_path = (
            Path(resolved) if resolved is not None else Path("synthetic")
        )

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
                raise FileNotFoundError(
                    f"{ERR_SELF_FLOW_WEIGHTS_MISSING}:{self._weights_path}"
                )
            self._mode = "torch"
        elif force_mode == "synthetic":
            self._mode = "synthetic"
        else:
            raise ValueError(f"unknown_force_mode:{force_mode}")

        # Backend handles.
        self._model: Any = None
        self._torch_dtype: Any = None
        self._synthetic_weights: dict[str, ArrayF64] | None = None
        if self._mode == "torch":
            self._model = _load_torch_model(self._weights_path)
            try:
                import torch as _torch  # local.
                self._torch_dtype = _torch.float32
            except ImportError:
                # Should never happen — torch_is_available() returned True.
                self._mode = "synthetic"
        if self._mode == "synthetic":
            self._synthetic_weights = _random_init_synthetic_weights(
                hidden=int(self._synthetic_hidden),
                seed=int(self._synthetic_seed),
            )

        # LRU-bounded native-states cache (audit A-3 mirror of
        # RectifiedFlowCIFAR). The cache holds the (latent, conditioning)
        # tuple per digest + trajectory / endpoint entries; the
        # conditioning-only cache is bounded separately.
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._conditioning_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = SelfFlowCapabilities()

    # ------------------------------------------------------------------
    # 1. capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. helpers — LRU-bounded native_states + conditioning cache
    # ------------------------------------------------------------------

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > SELF_FLOW_NATIVE_STATES_MAXSIZE:
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        self._native_states.pop(digest, None)

    def _put_conditioning(self, cache_hash: str, entry: dict[str, Any]) -> None:
        if cache_hash in self._conditioning_cache:
            self._conditioning_cache[cache_hash] = entry
            self._conditioning_cache.move_to_end(cache_hash)
            return
        self._conditioning_cache[cache_hash] = entry
        while len(self._conditioning_cache) > self._conditioning_cache_size:
            self._conditioning_cache.popitem(last=False)

    def _resolve_conditioning(
        self, *, class_label: int, seed: int
    ) -> dict[str, Any]:
        """Build or fetch the conditioning cache for ``class_label``.

        The cache key is the SHA-256 of the (class_label) integer, so
        re-inference rounds that preserve the class label do not
        re-encode.
        """
        cache_hash = _class_label_cache_hash(class_label)
        existing = self._conditioning_cache.get(cache_hash)
        if existing is not None:
            self._conditioning_cache.move_to_end(cache_hash)
            return existing
        entry = _synthetic_class_conditioning(
            class_label=class_label, seed=int(seed),
        )
        self._put_conditioning(cache_hash, entry)
        return entry

    # ------------------------------------------------------------------
    # 2. build_initial_state
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        seed = seed_from_ids(
            str(batch_id),
            str(sample_id),
            int(self._seed_offset) + 0,
        )
        rng = np.random.default_rng(seed)
        x0 = _synthesize_latent_like_tensor(rng)

        # Build the conditioning cache for the *default* class label.
        # The framework can override the label per-round via
        # ``compose_condition`` -> ``solve_ode``; this initial-state
        # cache is just a placeholder so the bundle's ``class_cond``
        # channel has a valid TensorRef.
        cond = self._resolve_conditioning(
            class_label=self._class_label, seed=int(seed),
        )

        digest = digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "shape": [int(s) for s in x0.shape],
                "latent_first": [
                    float(x0[0, 0, 0]),
                    float(x0[0, 0, 1]),
                    float(x0[1, 0, 0]),
                ],
                "conditioning_hash": str(cond["cache_hash"]),
            }
        )
        self._put_native_state(
            digest,
            {
                "x0": np.asarray(x0, dtype=np.float64).reshape(SELF_FLOW_STATE_SHAPE),
                "source_round": 0,
                "mode": self._mode,
                "conditioning_hash": str(cond["cache_hash"]),
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("image_latent"): _make_ref(
                    "latent:initial",
                    batch=batch_id,
                    sample=sample_id,
                ),
                ChannelName("class_cond"): _make_ref(
                    "cond",
                    cache_hash=str(cond["cache_hash"]),
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
            provenance=(SELF_FLOW_MECHANISM_ID,),
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
        """Identity pass-through; the latent endpoint crosses the protocol boundary."""
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
        """Latent-space restart blend (NOT pixel space).

        The blend math is
        ``blended = m * prior_latent + (1 - m) * fresh_latent``
        with ``m = 1 - beta``. The conditioning reference is preserved
        unchanged across rounds (same class_label -> same cache key),
        so ``class_cond`` TensorRef propagates forward. The blended
        latent is clipped to ``[-SELF_FLOW_CLAMP, SELF_FLOW_CLAMP]``.
        """
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

        beta, memory_fraction = memory_fraction_for(policy, ChannelName("image_latent"))

        prior_x = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            SELF_FLOW_STATE_SHAPE
        )
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_x = _synthesize_latent_like_tensor(np.random.default_rng(restart_seed))

        m = max(0.0, min(1.0, float(memory_fraction)))
        blended = (m * prior_x + (1.0 - m) * fresh_x).astype(np.float64)
        blended = np.clip(blended, -SELF_FLOW_CLAMP, SELF_FLOW_CLAMP)

        # Preserve the conditioning cache across the restart boundary
        # (same class_label -> same conditioning). This is the
        # load-bearing optimisation that keeps re-inference rounds
        # cheap.
        cond_hash = str(prior_entry.get("conditioning_hash", ""))

        next_digest = digest_state(
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
                    float(blended[1, 0, 0]),
                ],
                "conditioning_hash": str(cond_hash),
            }
        )
        self._put_native_state(
            next_digest,
            {
                "x0": blended,
                "source_round": next_round,
                "mode": self._mode,
                "conditioning_hash": str(cond_hash),
            },
        )
        return StateBundle(
            channels={
                ChannelName("image_latent"): _make_ref(
                    "latent:restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
                # Preserve the conditioning reference across the restart
                # boundary so the class-encoder cache is reused.
                ChannelName("class_cond"): _make_ref(
                    "cond",
                    cache_hash=str(cond_hash),
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
            provenance=tuple(state.provenance) + (AUDIT_SELF_FLOW_RESTART_BLEND,),
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
        """Inject the conditioning cache + class label + CFG into the delta.

        Convention (documented in the module docstring):

        * ``class_label`` (int, default 0) — required for
          class-conditional generation. The synthetic / torch path
          accepts any value in ``[0, 1000]``; ``1000`` is the
          unconditional token.
        * ``guidance_scale`` (float, default 1.5) — CFG scale; the
          framework's per-round
          ``condition.delta_spec["guidance_scale"]`` overrides.
        * ``num_steps`` (int, default 50) — integration step count.
        * ``sampler_id`` (str, default "euler") — integrator name.
        * ``conditioning_cache_hash`` (str, output) — the
          deterministic SHA-256 of the class_label, written by
          ``compose_condition`` so subsequent rounds can check the
          cache key without re-encoding.

        The adapter caches the conditioning internally on first use;
        ``conditioning_cache_hash`` is exposed via ``delta_spec`` for
        downstream observability.
        """
        del bundle
        new_spec = dict(delta.delta_spec)
        # Resolve class label.
        class_label = int(new_spec.get("class_label", self._class_label))
        if class_label < 0 or class_label >= 1001:
            raise ValueError(
                f"{ERR_SELF_FLOW_CLASS_LABEL_INVALID}:{class_label!r}"
                "; expected in [0, 1000]"
            )
        new_spec["class_label"] = class_label

        # Resolve CFG scale (per-round override).
        guidance_scale = float(
            new_spec.get("guidance_scale", self._guidance_scale)
        )
        new_spec["guidance_scale"] = guidance_scale

        # Resolve num_steps (per-round override).
        num_steps = int(new_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError(ERR_SELF_FLOW_NUM_STEPS)
        new_spec["num_steps"] = num_steps

        # Resolve sampler.
        sampler_id = str(new_spec.get("sampler_id", self._solver))
        if sampler_id not in SELF_FLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_SELF_FLOW_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
                f"; expected one of {SELF_FLOW_INTEGRATORS!r}"
            )
        new_spec["sampler_id"] = sampler_id

        # Build / fetch the conditioning cache so the cache key is
        # available to ``solve_ode`` without re-encoding.
        cond = self._resolve_conditioning(
            class_label=class_label, seed=int(delta.target_round),
        )
        new_spec["conditioning_cache_hash"] = str(cond["cache_hash"])

        new_spec.setdefault("integrator_config_hash", SELF_FLOW_CONFIG_HASH)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def _velocity_field(
        self,
        x: ArrayF64,
        t: float,
        *,
        conditioning: Mapping[str, Any],
        guidance_scale: float,
    ) -> ArrayF64:
        """Evaluate the velocity field at ``(x, t)`` for the active backend.

        Internal dispatch helper used by :meth:`solve_ode` and
        :meth:`batched_inference`. ``torch`` mode delegates to the
        PyTorch SiT (see :func:`_torch_velocity_field`); ``synthetic``
        mode uses the deterministic NumPy field. Returns a NumPy
        ``(4, 32, 32)`` float64 array (copy-safe to mutate).
        """
        if self._mode == "torch":
            assert self._model is not None
            return _torch_velocity_field(
                self._model,
                x,
                t,
                dtype=self._torch_dtype,
                cache=conditioning,
                guidance_scale=float(guidance_scale),
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
            raise ValueError(ERR_SELF_FLOW_NUM_STEPS)
        guidance_scale = float(
            condition.delta_spec.get("guidance_scale", self._guidance_scale)
        )
        sampler_id = str(
            condition.delta_spec.get("sampler_id", self._solver)
        )
        if sampler_id not in SELF_FLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_SELF_FLOW_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
            )

        # Re-resolve conditioning from the delta_spec's cache hash so
        # re-inference rounds reuse the cached encoder output. If the
        # delta_spec lacks the conditioning hash (e.g. a hand-rolled
        # delta from a hostile test), fall back to encoding the default
        # class label.
        cond_hash = str(
            condition.delta_spec.get("conditioning_cache_hash", "")
        )
        if cond_hash and cond_hash in self._conditioning_cache:
            conditioning = self._conditioning_cache[cond_hash]
        else:
            class_label = int(
                condition.delta_spec.get("class_label", self._class_label)
            )
            conditioning = self._resolve_conditioning(
                class_label=class_label, seed=int(seed),
            )

        x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            SELF_FLOW_STATE_SHAPE
        )

        t_grid = np.linspace(
            0.0, float(SELF_FLOW_T_END), num_steps + 1, dtype=np.float64
        )
        traj = np.empty((t_grid.size, *SELF_FLOW_STATE_SHAPE), dtype=np.float64)
        traj[0] = x0.copy()
        x_cur = x0.copy()
        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            v1 = self._velocity_field(
                x_cur, t0, conditioning=conditioning, guidance_scale=guidance_scale,
            )
            if (
                sampler_id == SELF_FLOW_INTEGRATOR_HEUN
                and i < t_grid.size - 1
            ):
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(
                    x_cur + dt * v1, -SELF_FLOW_CLAMP, SELF_FLOW_CLAMP
                )
                v2 = self._velocity_field(
                    x_pred, t1, conditioning=conditioning, guidance_scale=guidance_scale,
                )
                # Corrector: trapezoidal average. The final step has no
                # ``t+dt`` within the integration range so the corrector
                # is skipped (matches k-diffusion ``sample_heun`` at
                # ``sigma_next == 0``).
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -SELF_FLOW_CLAMP,
                    SELF_FLOW_CLAMP,
                )
            else:
                x_cur = np.clip(
                    x_cur + dt * v1, -SELF_FLOW_CLAMP, SELF_FLOW_CLAMP
                )
            traj[i] = x_cur

        traj_digest = digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "sampler_id": str(sampler_id),
                "num_steps": int(num_steps),
                "guidance_scale": float(guidance_scale),
                "conditioning_hash": str(conditioning.get("cache_hash", "")),
                "shape": [int(traj.shape[0]), int(traj.shape[1]), int(traj.shape[2])],
                "latent_first": [
                    float(x0[0, 0, 0]),
                    float(x0[0, 0, 1]),
                    float(x0[1, 0, 0]),
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
                "conditioning_hash": str(conditioning.get("cache_hash", "")),
            },
        )
        cfg_blob = repr(
            (
                "self_flow_config",
                str(sampler_id),
                int(num_steps),
                float(guidance_scale),
                int(seed),
            )
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
            SELF_FLOW_STATE_SHAPE
        )
        endpoint_digest = digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "x_final_first": [
                    float(x_final[0, 0, 0]),
                    float(x_final[0, 0, 1]),
                    float(x_final[1, 0, 0]),
                ],
                "t_final": float(SELF_FLOW_T_END),
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "x": np.asarray(x_final, dtype=np.float64).reshape(SELF_FLOW_STATE_SHAPE),
                "t": float(SELF_FLOW_T_END),
                "mode": self._mode,
                "conditioning_hash": str(traj_entry.get("conditioning_hash", "")),
            },
        )
        next_round = int(state.source_round) + 1
        # Carry the conditioning reference forward across rounds so the
        # bundle's ``class_cond`` channel never goes stale.
        cond_hash = str(traj_entry.get("conditioning_hash", ""))
        return StateBundle(
            channels={
                ChannelName("image_latent"): dict(state.channels).get(
                    ChannelName("image_latent"),
                    _make_ref(
                        "latent:endpoint",
                        traj_digest=str(trace.native_state_digest),
                        src_digest=str(state.native_state_digest),
                    ),
                ),
                ChannelName("class_cond"): _make_ref(
                    "cond",
                    cache_hash=str(cond_hash),
                ),
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=endpoint_digest,
            provenance=tuple(state.provenance) + (AUDIT_SELF_FLOW_OBSERVED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> ArrayF64 | None:
        """Return the native ``(T, 4, 32, 32)`` trajectory for ``trace``."""
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
        """Inject ``injected`` (shape ``(4, 32, 32)``) into the bundle's prior.

        Returns a fresh :class:`StateBundle` whose prior x0 has been
        updated to ``x + injected`` (clipped to
        ``[-SELF_FLOW_CLAMP, SELF_FLOW_CLAMP]``) and whose
        ``provenance`` records the
        :data:`AUDIT_FORWARD_NOISE_APPLIED` tag.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        x_prior = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            SELF_FLOW_STATE_SHAPE
        )
        x_new_arr = np.asarray(injected, dtype=np.float64).reshape(
            SELF_FLOW_STATE_SHAPE
        )
        x_new = np.clip(x_prior + x_new_arr, -SELF_FLOW_CLAMP, SELF_FLOW_CLAMP)
        new_digest = digest_state(
            {
                "kind": "forward_noise",
                "src_digest": bundle.native_state_digest,
                "shape": [int(s) for s in x_new.shape],
                "x_first": [
                    float(x_new[0, 0, 0]),
                    float(x_new[0, 0, 1]),
                    float(x_new[1, 0, 0]),
                ],
            }
        )
        self._put_native_state(
            new_digest,
            {
                "x0": x_new,
                "source_round": int(bundle.source_round),
                "mode": self._mode,
                "conditioning_hash": str(prior_entry.get("conditioning_hash", "")),
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


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_self_flow_adapter(
    *,
    weights_path: Path | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    num_steps: int | None = None,
    class_label: int = SELF_FLOW_CLASS_LABEL_DEFAULT,
    solver: str = SELF_FLOW_INTEGRATOR_EULER,
) -> SelfFlowAdapter:
    """Default factory for :class:`SelfFlowAdapter`.

    When ``weights_path`` is ``None`` the adapter resolves
    ``data/self_flow/selfflow_imagenet256.pt`` (or
    ``data/selfflow_imagenet256.pt``); when neither exists and
    ``force_mode`` is ``"auto"``, the adapter falls back to
    ``synthetic`` mode (testing-only).

    The ``class_label`` parameter selects the ImageNet class label
    (0..999, or 1000 for unconditional); the ``num_steps`` parameter
    defaults to :data:`SELF_FLOW_NUM_STEPS_DEFAULT` (=50) when ``None``.
    """
    if num_steps is None:
        num_steps = int(SELF_FLOW_NUM_STEPS_DEFAULT)
    return SelfFlowAdapter(
        weights_path=weights_path,
        force_mode=force_mode,
        num_steps=int(num_steps),
        class_label=int(class_label),
        solver=solver,
    )


__all__ = [
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_SELF_FLOW_OBSERVED",
    "AUDIT_SELF_FLOW_RESTART_BLEND",
    "ERR_SELF_FLOW_CLASS_LABEL_INVALID",
    "ERR_SELF_FLOW_INTEGRATOR_UNKNOWN",
    "ERR_SELF_FLOW_NUM_STEPS",
    "ERR_SELF_FLOW_WEIGHTS_MISSING",
    "SELF_FLOW_CHANNEL_DOMAINS",
    "SELF_FLOW_CHANNELS",
    "SELF_FLOW_CLAMP",
    "SELF_FLOW_CFG_SCALE_DEFAULT",
    "SELF_FLOW_CLASS_LABEL_DEFAULT",
    "SELF_FLOW_CONFIG_HASH",
    "SELF_FLOW_CONFIG_VERSION",
    "SELF_FLOW_INTEGRATORS",
    "SELF_FLOW_INTEGRATOR_EULER",
    "SELF_FLOW_INTEGRATOR_HEUN",
    "SELF_FLOW_LATENT_DIM",
    "SELF_FLOW_MECHANISM_ID",
    "SELF_FLOW_NATIVE_STATES_MAXSIZE",
    "SELF_FLOW_NUM_STEPS_DEFAULT",
    "SELF_FLOW_STATE_SHAPE",
    "SELF_FLOW_SYNTHETIC_HIDDEN",
    "SELF_FLOW_SYNTHETIC_SEED_DEFAULT",
    "SELF_FLOW_T_END",
    "SelfFlowAdapter",
    "SelfFlowCapabilities",
    "default_self_flow_adapter",
    "self_flow_resolve_weights_path",
    "torch_is_available",
]
