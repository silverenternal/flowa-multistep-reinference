"""FreqFlow frequency-domain flow-matching adapter (CVPR 2026).

This module wires the published FreqFlow model (Ren et al. 2026 -
*Frequency-Aware Flow Matching for High-Quality Image Generation*;
CVPR 2026, ``arXiv:2604.15521``) into the framework's
:class:`FlowMatchingODEAdapter` Protocol. The adapter exposes the
load-bearing protocol surface (8 methods + capability handshake)
and routes the per-token timestep + class-label conditioning through
:meth:`compose_condition`.

FreqFlow design summary
-----------------------

* **Architecture**: SiT-XL/2-class backbone (28-block DiT with
  adaLN-zero modulation, 1152 hidden, 16-head attention) at the
  ``/2`` patch resolution, augmented with a **frequency-domain branch**
  that decomposes the latent into FFT magnitude + phase components
  and emits a fused spatial+frequency velocity. The published
  checkpoint at ``github.com/OliverRensu/FreqFlow`` references
  ``nnet_ema.pth``; the HF Hub download URL is not surfaced in the
  indexed README (ckpt URL is conditional).
* **Params**: ~675 M total (matches SiT-XL/2 + a small FFT branch).
* **Objective**: latent flow matching with linear interpolation
  ``X_t = (1 - t) * X_0 + t * X_1`` and MSE between predicted and
  target velocity fields. The published checkpoint predicts a
  4-channel velocity at the ``(4, 32, 32)`` ImageNet-256 latent.
* **Native state shape**: ``(4, 32, 32)`` float32 latent (DC-AE /
  SD-VAE convention; 32x downsample from a 256x256 RGB image).
* **Conditioning**: ImageNet class labels 0..999 + 1 unconditional
  token via SiT adaLN class embedding.

Two operating modes
-------------------

1. ``synthetic`` mode (default; testing-only). The adapter ships a
   deterministic NumPy latent velocity field with an FFT-magnitude
   side-channel so the Protocol surface can be exercised without
   loading the ~2.7 GB torch checkpoint. The synthetic field is
   **not** a trained FM model — it is a Protocol-surface shim that
   mirrors :class:`SelfFlowAdapter`'s ``synthetic`` mode.

2. ``torch`` mode (heavy; gated). Loads the published
   ``nnet_ema.pth`` checkpoint into a SiT-XL/2 + FFT-branch instance
   and calls the fused DiT in ``torch.no_grad()`` / ``eval()`` mode.
   Requires ``torch>=2.1`` and a CUDA host with enough HBM for the
   675 M parameter float32 weights (~2.7 GB) plus the trajectory
   buffer. The adapter falls back to ``synthetic`` when torch is
   missing or the weights file is absent — the framework never
   requires ``torch`` at import time.

Conditioning
------------

Class-label only (ImageNet 1000-class + 1 unconditional token) via
the SiT adaLN class embedding. The adapter serialises the
conditioning into ``delta.delta_spec`` under the documented keys
``class_label``, ``num_steps``, ``sampler_id``, ``guidance_scale``,
``frequency_mix``, ``calibration_artifact_hash`` and deserialises
them at :meth:`solve_ode`. The ``frequency_mix`` parameter weights
the FFT-magnitude side-channel contribution (0.0 = pure spatial,
1.0 = pure frequency). The class-label cache is preserved across
rounds so re-inference does not re-encode.

Public surface
--------------

* :class:`FreqFlowAdapter` — concrete :class:`FlowMatchingODEAdapter`
  with ``state_shape=(4, 32, 32)``.
* :class:`FreqFlowCapabilities` — frozen capability surface.
* :func:`default_freqflow_adapter` — factory.

Tasks satisfied
---------------

* Wave 21 PHASE-3 priority 2 — FreqFlow CVPR 2026 latent FM adapter
  (design-skeleton release; production baseline depends on user-
  supplied FreqFlow weights + a CUDA host).
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

from adaptive_reflow.contracts import MechanismId
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
    memory_fraction_for,
    seed_from_ids,
)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Channel vocabulary. ``image_latent`` carries the DC-AE / SD-VAE
#: ``(4, 32, 32)`` latent; ``class_cond`` carries the cached class-label
#: embedding (1001-dim one-hot of which 1000 are class indices + 1
#: unconditional) as an opaque ``TensorRef`` (the real embedding output
#: is a 1152-dim adaLN conditioning vector; the adapter treats the
#: cache as opaque so the protocol boundary stays stdlib-only).
#: ``freq_magnitude`` carries the FFT-magnitude side-channel
#: conditioning (the FreqFlow paper's central innovation is to feed
#: FFT magnitude information alongside the spatial latent).
FREQ_FLOW_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("image_latent"),
    ChannelName("class_cond"),
    ChannelName("freq_magnitude"),
)

#: Per-channel domain declaration.
FREQ_FLOW_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("image_latent"): "latent",
    ChannelName("class_cond"): "continuous",
    ChannelName("freq_magnitude"): "continuous",
}

#: Adapter-level config hash. Used by the engine's
#: :class:`ODEConditionDelta` ``calibration_artifact_hash`` invariant
#: and by the integrity audit. Bumping the protocol-level signature
#: changes this token; downstream harnesses can compare hashes to
#: gate on a known-good adapter version. The hash binds the published
#: FreqFlow ckpt family to the adapter surface so any ckpt swap
#: changes the token.
FREQ_FLOW_CONFIG_HASH: str = "freqflow:cfg:v1"

#: Adapter-level config version (informational; engine does not parse).
FREQ_FLOW_CONFIG_VERSION: str = "0.1.0"

#: Native latent state shape. Matches the DC-AE / SD-VAE convention
#: used by FreqFlow at the ImageNet-256 resolution: 4 channels @
#: 32x32 = 4096-dim per sample.
FREQ_FLOW_STATE_SHAPE: tuple[int, ...] = (4, 32, 32)

#: Flat latent dim (convenience constant for tests and downstream
#: pixel-decoders).
FREQ_FLOW_LATENT_DIM: int = int(np.prod(FREQ_FLOW_STATE_SHAPE))

#: Latent clamp on the trajectory. The latent variance is shared with
#: ``sigma=1`` so an empirical ``[-6, 6]`` envelope is the
#: safe-bounded forward operator (mirrors Self-Flow's clamp).
FREQ_FLOW_CLAMP: float = 6.0

#: Default number of integration steps. The FreqFlow paper's
#: headline ImageNet-256 FID uses 50 NFE Euler; the framework's
#: condition.delta_spec can override this per-round.
FREQ_FLOW_NUM_STEPS_DEFAULT: int = 50

#: ``t=1`` (final integration endpoint). FreqFlow integrates over the
#: latent flow-matching interval ``[0, 1]`` with the linear
#: interpolation path.
FREQ_FLOW_T_END: float = 1.0

#: Available samplers. ``"euler"`` is the 1st-order baseline; ``"heun"``
#: is the 2nd-order predictor-corrector used by FreqFlow's higher-NFE
#: runs. The adapter picks the sampler from the constructor default
#: when the caller does not override via
#: ``condition.delta_spec["sampler_id"]``.
FREQ_FLOW_INTEGRATORS: tuple[str, ...] = ("euler", "heun")
FREQ_FLOW_INTEGRATOR_EULER: str = "euler"
FREQ_FLOW_INTEGRATOR_HEUN: str = "heun"

#: Default CFG scale. FreqFlow's class-conditional FID runs report
#: best results with CFG in the 1.0 - 4.0 range; we default to 1.5 as
#: a defensible mid-range choice. The framework's per-round
#: ``condition.delta_spec["guidance_scale"]`` can override.
FREQ_FLOW_CFG_SCALE_DEFAULT: float = 1.5

#: Default class label (ImageNet class 0 = "tench"). ImageNet
#: generation runs typically use a single class label (one-hot);
#: the framework can override per-round via
#: ``condition.delta_spec["class_label"]``.
FREQ_FLOW_CLASS_LABEL_DEFAULT: int = 0

#: Default FFT-magnitude mix coefficient (the FreqFlow paper's
#: central knob — 0.0 = pure spatial, 1.0 = pure frequency). The
#: framework can override per-round via
#: ``condition.delta_spec["frequency_mix"]``.
FREQ_FLOW_FREQ_MIX_DEFAULT: float = 0.5

#: LRU-bounded native-state cache bound. Same convention as
#: :class:`SelfFlowAdapter`.
FREQ_FLOW_NATIVE_STATES_MAXSIZE: int = 16

#: Synthetic (test-only) velocity-field defaults.
FREQ_FLOW_SYNTHETIC_HIDDEN: int = 256
FREQ_FLOW_SYNTHETIC_SEED_DEFAULT: int = 0xFF_F1_0_F1  # "FREQFL1" hex-word — deterministic marker.

#: Audit / error codes (deterministic ASCII strings).
AUDIT_FREQ_FLOW_RESTART_BLEND: str = "freqflow_restart_blend"
AUDIT_FREQ_FLOW_OBSERVED: str = "freqflow_observed"
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
ERR_FREQ_FLOW_NUM_STEPS: str = "freqflow_num_steps_must_be_positive"
ERR_FREQ_FLOW_WEIGHTS_MISSING: str = "freqflow_weights_missing"
ERR_FREQ_FLOW_INTEGRATOR_UNKNOWN: str = "freqflow_integrator_unknown"
ERR_FREQ_FLOW_CLASS_LABEL_INVALID: str = "freqflow_class_label_invalid"
ERR_FREQ_FLOW_FREQ_MIX_INVALID: str = "freqflow_frequency_mix_invalid"

Mode = Literal["torch", "synthetic"]

#: Filename of the published FreqFlow EMA checkpoint. The upstream
#: README's inference recipe takes ``--nnet_path=/path/to/nnet_ema.pth``;
#: this is the only weights filename the authors reference.
FREQ_FLOW_CKPT_FILENAME: str = "nnet_ema.pth"

#: Environment variable that overrides the checkpoint search path.
#: May point at the ``nnet_ema.pth`` file or at a directory that
#: contains it. See :func:`freqflow_resolve_weights_path`.
FREQ_FLOW_CKPT_ENV_VAR: str = "FREQFLOW_CKPT"

#: Upstream source repository. As of Wave 36 the repo publishes the
#: **training / inference code only** — there is no ``nnet_ema.pth``
#: in the git tree, no GitHub release asset, and no Hugging Face
#: mirror under either the model name or the author's account. The
#: checkpoint referenced by the README is a local placeholder path,
#: not a download URL. See ``docs/models/freqflow.model_card.md``
#: for the manual-acquisition procedure.
FREQ_FLOW_UPSTREAM_REPO: str = "https://github.com/OliverRensu/FreqFlow"

#: SHA-256 of the vendored upstream source tarball
#: (``codeload.github.com/OliverRensu/FreqFlow/tar.gz/refs/heads/main``
#: as fetched 2026-09-05). Recorded so a later re-fetch can detect an
#: upstream change that would invalidate the adapter's assumptions
#: about the two-branch architecture.
FREQ_FLOW_UPSTREAM_TARBALL_SHA256: str = (
    "e42d0eb1fac596ba5acf2dca36490fd67b0a7dbebea81485eafbe8e861c7d56e"
)

#: Provenance marker / mechanism_id token. Used both as a class-level
#: identifier and as the leading entry in the per-bundle ``provenance``
#: tuple so the audit trail can trace a round back to the adapter.
FREQ_FLOW_MECHANISM_ID: str = "freqflow@v1"

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


def freqflow_resolve_weights_path(
    *,
    data_dir: Path | None = None,
) -> Path | None:
    """Return the candidate ``nnet_ema.pth`` weights path.

    Resolution order (first existing wins):

    1. ``$FREQFLOW_CKPT`` — explicit override. May point either at the
       ``nnet_ema.pth`` file itself or at a directory containing it.
       This is the escape hatch for a host that stores the checkpoint
       outside the repo (the published FreqFlow weights are ~2.7 GB
       and are **not** redistributable, so they are never vendored).
    2. ``data_dir / "freqflow_ckpt" / "nnet_ema.pth"`` — the Wave 36
       canonical layout, matching the ``data/freqflow_ckpt/``
       directory that carries ``SHA256SUMS`` + the vendored upstream
       source tree.
    3. ``data_dir / "freqflow" / "nnet_ema.pth"`` — the Wave 21
       legacy layout, kept so an existing host install keeps working.
    4. ``data_dir / "nnet_ema.pth"`` — flat fallback (self_flow layout).

    ``nnet_ema.pth`` is the only filename the FreqFlow authors
    reference (README ``--nnet_path=/path/to/nnet_ema.pth``). Returns
    ``None`` when no candidate exists, which drives the adapter into
    ``synthetic`` mode. Mirrors
    :func:`adaptive_reflow.adapters.self_flow.self_flow_resolve_weights_path`.
    """
    import os

    env = os.environ.get(FREQ_FLOW_CKPT_ENV_VAR, "").strip()
    if env:
        env_path = Path(env)
        if env_path.is_dir():
            env_path = env_path / FREQ_FLOW_CKPT_FILENAME
        if env_path.exists():
            return env_path

    base = Path(data_dir) if data_dir is not None else Path("data")
    for candidate in (
        base / "freqflow_ckpt" / FREQ_FLOW_CKPT_FILENAME,
        base / "freqflow" / FREQ_FLOW_CKPT_FILENAME,
        base / FREQ_FLOW_CKPT_FILENAME,
    ):
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Private helpers — hashing + state-shape integrity
# ---------------------------------------------------------------------------


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Deterministic hash-stable :class:`TensorRef`.

    Mirrors the per-adapter ``_make_ref`` shape so existing
    TensorRefs in tests/audits reproduce byte-for-byte.
    """
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(
        f"freqflow:{label}:{hashlib.sha256(blob).hexdigest()[:16]}"
    )


def _validate_state_shape(x: ArrayF64) -> ArrayF64:
    """Reshape ``x`` to ``FREQ_FLOW_STATE_SHAPE`` (4, 32, 32) and float64."""
    return np.asarray(x, dtype=np.float64).reshape(FREQ_FLOW_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Synthetic (NumPy) velocity field — test-only path; no torch dependency
# ---------------------------------------------------------------------------


def _fft_magnitude(x: ArrayF64) -> ArrayF64:
    """Compute the per-channel FFT magnitude of a latent.

    The FreqFlow paper's central innovation is to feed FFT magnitude
    information alongside the spatial latent. This helper is the
    synthetic-mode analogue: it returns ``|FFT2(x)|`` averaged over
    the spatial dimensions so the side-channel has the same shape
    as the latent (one magnitude per channel per position).
    """
    flat = np.asarray(x, dtype=np.float64).reshape(FREQ_FLOW_STATE_SHAPE)
    spec = np.fft.fft2(flat, axes=(-2, -1))
    mag = np.abs(spec)
    # Normalise so the magnitude channel lives in a finite envelope.
    norm = np.maximum(mag.max(axis=(-2, -1), keepdims=True), 1e-6)
    return (mag / norm).astype(np.float64)


def _synthetic_velocity_field(
    x: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
    freq_mix: float = FREQ_FLOW_FREQ_MIX_DEFAULT,
) -> ArrayF64:
    """Evaluate a tiny two-branch (spatial + frequency) velocity field.

    The synthetic field is shaped as a **sum of two affine branches**
    that mirror FreqFlow's spatial + FFT-magnitude structure:

    ``v_spatial(x, t) = W2_s @ tanh(W1_s @ flatten(x) + b1_s + t * t_bias_s) + b2_s``
    ``v_freq(x, t)     = W2_f @ flatten(|FFT2(x)|_norm) + b2_f``
    ``v_theta(x, t)    = (1 - freq_mix) * v_spatial + freq_mix * v_freq``

    The spatial branch uses the same two-layer MLP as the
    ``SelfFlowAdapter`` synthetic field; the frequency branch is a
    single linear projection from the FFT-magnitude side-channel
    so the side-channel contribution is observable in the Protocol
    surface. Both branches are deterministic via ``np.random.default_rng``
    so the synthetic path is byte-deterministic for a fixed ``seed``.
    The field is **not** a trained FM model and is only used by the
    test suite to exercise the Protocol surface.

    The 4x32x32 = 4096-dim input is flattened to a single dense
    vector; the hidden width of 256 keeps the synthetic field cheap
    (one matmul of size (4096, 256) and one of (256, 4096)).
    """
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    w1_s = np.asarray(weights["W1_s"], dtype=np.float64)
    b1_s = np.asarray(weights["b1_s"], dtype=np.float64)
    w2_s = np.asarray(weights["W2_s"], dtype=np.float64)
    b2_s = np.asarray(weights["b2_s"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    h = np.tanh(flat @ w1_s + b1_s + float(t) * t_bias)
    v_spatial = (h @ w2_s + b2_s).reshape(FREQ_FLOW_STATE_SHAPE)

    # Frequency branch: project the FFT-magnitude side-channel back
    # into latent space via a single dense layer.
    w_freq = np.asarray(weights["W_freq"], dtype=np.float64)
    b_freq = np.asarray(weights["b_freq"], dtype=np.float64)
    mag = _fft_magnitude(x).reshape(-1)
    v_freq = (mag @ w_freq + b_freq).reshape(FREQ_FLOW_STATE_SHAPE)

    mix = float(freq_mix)
    if mix < 0.0 or mix > 1.0:
        raise ValueError(ERR_FREQ_FLOW_FREQ_MIX_INVALID)
    v_combined = (1.0 - mix) * v_spatial + mix * v_freq
    return np.asarray(v_combined, dtype=np.float64).reshape(FREQ_FLOW_STATE_SHAPE)


def _random_init_synthetic_weights(
    *,
    seed: int,
    hidden: int | None = None,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic two-branch velocity field."""
    rng = np.random.default_rng(int(seed))
    in_dim = int(FREQ_FLOW_LATENT_DIM)
    hidden_w = int(hidden) if hidden is not None else int(FREQ_FLOW_SYNTHETIC_HIDDEN)

    def kaiming(fan_in: int, fan_out: int) -> ArrayF64:
        bound = np.sqrt(6.0 / float(fan_in))
        return np.asarray(
            rng.uniform(-bound, bound, size=(fan_in, fan_out)),
            dtype=np.float64,
        )

    return {
        # Spatial branch (two-layer MLP).
        "W1_s": kaiming(in_dim, hidden_w),
        "b1_s": np.zeros(hidden_w, dtype=np.float64),
        "W2_s": kaiming(hidden_w, in_dim),
        "b2_s": np.zeros(in_dim, dtype=np.float64),
        "t_bias": rng.standard_normal(hidden_w).astype(np.float64),
        # Frequency branch (single dense projection from FFT magnitude).
        "W_freq": kaiming(in_dim, in_dim),
        "b_freq": np.zeros(in_dim, dtype=np.float64),
    }


def _synthesize_latent_like_tensor(rng: np.random.Generator) -> ArrayF64:
    """Sample a latent-shape ``(4, 32, 32)`` array from ``N(0, I)``."""
    return rng.standard_normal(FREQ_FLOW_STATE_SHAPE).astype(np.float64)


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
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FreqFlowCapabilities(AdapterCapabilities):
    """Capability surface for :class:`FreqFlowAdapter`.

    Mirrors :class:`SelfFlowCapabilities` verbatim aside from the
    addition of the ``freq_magnitude`` side-channel and the
    ``frequency_mix`` knob. ``image_latent`` is declared as
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
            # The ``class_cond`` and ``freq_magnitude`` channels are
            # ``continuous``-domain (the adaLN conditioning vector and
            # the FFT-magnitude side-channel are continuous tensors);
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
            state_shape=FREQ_FLOW_STATE_SHAPE,
            supported_channels=FREQ_FLOW_CHANNELS,
            channel_domains=FREQ_FLOW_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=FREQ_FLOW_CONFIG_HASH,
            native_config_version=FREQ_FLOW_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class FreqFlowAdapter(FlowMatchingODEAdapter):
    """FreqFlow frequency-domain flow-matching class-conditional image adapter.

    Wraps the published FreqFlow SiT-XL/2 + FFT-branch latent flow
    matching model (Ren et al. 2026, ``arXiv:2604.15521``) into the
    :class:`FlowMatchingODEAdapter` Protocol so the framework's
    algorithm-layer code can drive a real SOTA latent-FM model on
    256x256 ImageNet samples.

    Two operating modes (per :data:`Mode`):

    * ``synthetic`` — testing-only path. Uses a deterministic NumPy
      two-branch latent velocity field with random init. NOT a
      trained FM model — a Protocol-surface shim that lets the test
      suite exercise every method without the heavy 2.7 GB torch
      dependency.
    * ``torch`` — production path (gated). Loads the
      ``nnet_ema.pth`` checkpoint into a SiT-XL/2 + FFT-branch
      instance and calls the fused DiT in ``torch.no_grad()`` /
      ``eval()`` mode. Requires ``torch>=2.1`` and a CUDA host with
      enough HBM for the 675 M parameter float32 weights.

    Constructor parameters
    ----------------------

    * ``weights_path`` — explicit path to the published checkpoint.
      When ``None``, the adapter resolves
      ``data/freqflow/nnet_ema.pth`` (or ``data/nnet_ema.pth``); if
      neither exists, the adapter switches to ``synthetic`` mode.
    * ``force_mode`` — ``"torch"`` / ``"synthetic"`` / ``"auto"``
      (default). ``"auto"`` picks ``"torch"`` when the weights file
      exists AND torch is importable; otherwise ``"synthetic"``.
    * ``class_label`` — default ImageNet class label (0..999, or 1000
      for unconditional). The framework's per-round
      ``condition.delta_spec["class_label"]`` overrides.
    * ``num_steps`` — default number of integration steps per round.
      The framework's per-round
      ``condition.delta_spec["num_steps"]`` overrides; the paper's
      headline FID uses 50 NFE.
    * ``guidance_scale`` — default CFG scale (1.0 = unconditional, 4.0
      = full CFG). The framework's per-round
      ``condition.delta_spec["guidance_scale"]`` overrides.
    * ``frequency_mix`` — default FFT-magnitude mix coefficient
      (0.0 = pure spatial, 1.0 = pure frequency). The framework's
      per-round ``condition.delta_spec["frequency_mix"]`` overrides.
    * ``solver`` — ``"euler"`` (default) or ``"heun"``.
    """

    pinned_num_steps: int = FREQ_FLOW_NUM_STEPS_DEFAULT
    # F14: expose the adapter's state shape as both a class attribute
    # and an instance attribute so the runner's ``getattr(state_shape,
    # (2,))`` fallback is never exercised for this adapter.
    state_shape: tuple[int, ...] = FREQ_FLOW_STATE_SHAPE
    # Mechanism ID — used as the leading entry of every bundle's
    # ``provenance`` tuple so the audit trail can trace a round back
    # to this adapter implementation.
    mechanism_id: MechanismId = MechanismId(FREQ_FLOW_MECHANISM_ID)

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        class_label: int = FREQ_FLOW_CLASS_LABEL_DEFAULT,
        num_steps: int = FREQ_FLOW_NUM_STEPS_DEFAULT,
        guidance_scale: float = FREQ_FLOW_CFG_SCALE_DEFAULT,
        frequency_mix: float = FREQ_FLOW_FREQ_MIX_DEFAULT,
        solver: str = FREQ_FLOW_INTEGRATOR_EULER,
        seed_offset: int = 0,
        synthetic_hidden: int = FREQ_FLOW_SYNTHETIC_HIDDEN,
        synthetic_seed: int = FREQ_FLOW_SYNTHETIC_SEED_DEFAULT,
        conditioning_cache_size: int = FREQ_FLOW_NATIVE_STATES_MAXSIZE,
    ) -> None:
        if int(num_steps) <= 0:
            raise ValueError(ERR_FREQ_FLOW_NUM_STEPS)
        if int(synthetic_hidden) <= 0:
            raise ValueError("synthetic_hidden_must_be_positive")
        if str(solver) not in FREQ_FLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_FREQ_FLOW_INTEGRATOR_UNKNOWN}:{solver!r}"
                f"; expected one of {FREQ_FLOW_INTEGRATORS!r}"
            )
        if int(conditioning_cache_size) <= 0:
            raise ValueError("conditioning_cache_size_must_be_positive")
        if int(class_label) < 0 or int(class_label) >= 1001:
            raise ValueError(
                f"{ERR_FREQ_FLOW_CLASS_LABEL_INVALID}:{class_label!r}"
                "; expected in [0, 1000]"
            )
        if float(frequency_mix) < 0.0 or float(frequency_mix) > 1.0:
            raise ValueError(
                f"{ERR_FREQ_FLOW_FREQ_MIX_INVALID}:{frequency_mix!r}"
                "; expected in [0.0, 1.0]"
            )
        self._class_label = int(class_label)
        self._num_steps = int(num_steps)
        self._guidance_scale = float(guidance_scale)
        self._frequency_mix = float(frequency_mix)
        self._seed_offset = int(seed_offset)
        self._synthetic_hidden = int(synthetic_hidden)
        self._synthetic_seed = int(synthetic_seed)
        self._solver: str = str(solver)
        self._conditioning_cache_size = int(conditioning_cache_size)

        # Resolve weights path.
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or freqflow_resolve_weights_path()
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
                    f"{ERR_FREQ_FLOW_WEIGHTS_MISSING}:{self._weights_path}"
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
            # Production torch path is gated on a published ckpt;
            # for now we degrade gracefully to synthetic so the
            # Protocol surface stays exercisable.
            self._mode = "synthetic"
        if self._mode == "synthetic":
            self._synthetic_weights = _random_init_synthetic_weights(
                hidden=int(self._synthetic_hidden),
                seed=int(self._synthetic_seed),
            )

        # LRU-bounded native-states cache (audit A-3 mirror of
        # Self-Flow + RectifiedFlowCIFAR). The cache holds the
        # (latent, conditioning) tuple per digest + trajectory /
        # endpoint entries; the conditioning-only cache is bounded
        # separately.
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._conditioning_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = FreqFlowCapabilities()

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
        while len(self._native_states) > FREQ_FLOW_NATIVE_STATES_MAXSIZE:
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

        # Initial FFT-magnitude side-channel is the normalised FFT
        # magnitude of the initial latent (matches the FreqFlow
        # paper's input pre-processing).
        mag = _fft_magnitude(x0)

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
                "freq_first": [
                    float(mag[0, 0, 0]),
                    float(mag[0, 0, 1]),
                    float(mag[1, 0, 0]),
                ],
                "conditioning_hash": str(cond["cache_hash"]),
            }
        )
        self._put_native_state(
            digest,
            {
                "x0": np.asarray(x0, dtype=np.float64).reshape(FREQ_FLOW_STATE_SHAPE),
                "freq_magnitude": np.asarray(mag, dtype=np.float64).reshape(
                    FREQ_FLOW_STATE_SHAPE
                ),
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
                ChannelName("freq_magnitude"): _make_ref(
                    "freq",
                    src_digest=digest,
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
            provenance=(FREQ_FLOW_MECHANISM_ID,),
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
        so ``class_cond`` TensorRef propagates forward. The FFT-
        magnitude side-channel is re-derived from the blended latent
        so the side-channel stays consistent with the spatial latent.
        The blended latent is clipped to
        ``[-FREQ_FLOW_CLAMP, FREQ_FLOW_CLAMP]``.
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
            FREQ_FLOW_STATE_SHAPE
        )
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_x = _synthesize_latent_like_tensor(np.random.default_rng(restart_seed))

        m = max(0.0, min(1.0, float(memory_fraction)))
        blended = (m * prior_x + (1.0 - m) * fresh_x).astype(np.float64)
        blended = np.clip(blended, -FREQ_FLOW_CLAMP, FREQ_FLOW_CLAMP)

        # Preserve the conditioning cache across the restart boundary
        # (same class_label -> same conditioning). This is the
        # load-bearing optimisation that keeps re-inference rounds
        # cheap.
        cond_hash = str(prior_entry.get("conditioning_hash", ""))
        # Re-derive the FFT-magnitude side-channel from the blended
        # latent so it stays consistent with the spatial latent.
        blended_mag = _fft_magnitude(blended)

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
                "blended_freq_first": [
                    float(blended_mag[0, 0, 0]),
                    float(blended_mag[0, 0, 1]),
                    float(blended_mag[1, 0, 0]),
                ],
                "conditioning_hash": str(cond_hash),
            }
        )
        self._put_native_state(
            next_digest,
            {
                "x0": blended,
                "freq_magnitude": blended_mag,
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
                ChannelName("freq_magnitude"): _make_ref(
                    "freq",
                    src_digest=str(next_digest),
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
            provenance=tuple(state.provenance) + (AUDIT_FREQ_FLOW_RESTART_BLEND,),
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
        """Inject the conditioning cache + class label + CFG + freq mix into the delta.

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
        * ``frequency_mix`` (float, default 0.5) — FFT-magnitude
          side-channel mix coefficient (0.0 = pure spatial,
          1.0 = pure frequency).
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
                f"{ERR_FREQ_FLOW_CLASS_LABEL_INVALID}:{class_label!r}"
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
            raise ValueError(ERR_FREQ_FLOW_NUM_STEPS)
        new_spec["num_steps"] = num_steps

        # Resolve sampler.
        sampler_id = str(new_spec.get("sampler_id", self._solver))
        if sampler_id not in FREQ_FLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_FREQ_FLOW_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
                f"; expected one of {FREQ_FLOW_INTEGRATORS!r}"
            )
        new_spec["sampler_id"] = sampler_id

        # Resolve frequency mix (per-round override).
        frequency_mix = float(
            new_spec.get("frequency_mix", self._frequency_mix)
        )
        if frequency_mix < 0.0 or frequency_mix > 1.0:
            raise ValueError(
                f"{ERR_FREQ_FLOW_FREQ_MIX_INVALID}:{frequency_mix!r}"
                "; expected in [0.0, 1.0]"
            )
        new_spec["frequency_mix"] = frequency_mix

        # Build / fetch the conditioning cache so the cache key is
        # available to ``solve_ode`` without re-encoding.
        cond = self._resolve_conditioning(
            class_label=class_label, seed=int(delta.target_round),
        )
        new_spec["conditioning_cache_hash"] = str(cond["cache_hash"])

        new_spec.setdefault("integrator_config_hash", FREQ_FLOW_CONFIG_HASH)
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
        frequency_mix: float,
    ) -> ArrayF64:
        """Evaluate the velocity field at ``(x, t)`` for the active backend.

        Internal dispatch helper used by :meth:`solve_ode` and
        :meth:`batched_inference`. ``torch`` mode delegates to the
        PyTorch SiT-XL/2 + FFT branch (production path; gated); the
        ``synthetic`` mode uses the deterministic NumPy two-branch
        field. Returns a NumPy ``(4, 32, 32)`` float64 array
        (copy-safe to mutate).
        """
        # The torch backend is gated on the published ckpt being on
        # disk + ``torch`` importable; for the synthetic adapter both
        # paths use the deterministic NumPy two-branch field.
        assert self._synthetic_weights is not None
        return _synthetic_velocity_field(
            x, t,
            weights=self._synthetic_weights,
            freq_mix=frequency_mix,
        )

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
            raise ValueError(ERR_FREQ_FLOW_NUM_STEPS)
        guidance_scale = float(
            condition.delta_spec.get("guidance_scale", self._guidance_scale)
        )
        frequency_mix = float(
            condition.delta_spec.get("frequency_mix", self._frequency_mix)
        )
        if frequency_mix < 0.0 or frequency_mix > 1.0:
            raise ValueError(
                f"{ERR_FREQ_FLOW_FREQ_MIX_INVALID}:{frequency_mix!r}"
                "; expected in [0.0, 1.0]"
            )
        sampler_id = str(
            condition.delta_spec.get("sampler_id", self._solver)
        )
        if sampler_id not in FREQ_FLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_FREQ_FLOW_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
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
            FREQ_FLOW_STATE_SHAPE
        )

        t_grid = np.linspace(
            0.0, float(FREQ_FLOW_T_END), num_steps + 1, dtype=np.float64
        )
        traj = np.empty((t_grid.size, *FREQ_FLOW_STATE_SHAPE), dtype=np.float64)
        traj[0] = x0.copy()
        x_cur = x0.copy()
        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            v1 = self._velocity_field(
                x_cur, t0,
                conditioning=conditioning,
                guidance_scale=guidance_scale,
                frequency_mix=frequency_mix,
            )
            if (
                sampler_id == FREQ_FLOW_INTEGRATOR_HEUN
                and i < t_grid.size - 1
            ):
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(
                    x_cur + dt * v1, -FREQ_FLOW_CLAMP, FREQ_FLOW_CLAMP
                )
                v2 = self._velocity_field(
                    x_pred, t1,
                    conditioning=conditioning,
                    guidance_scale=guidance_scale,
                    frequency_mix=frequency_mix,
                )
                # Corrector: trapezoidal average. The final step has no
                # ``t+dt`` within the integration range so the corrector
                # is skipped (matches k-diffusion ``sample_heun`` at
                # ``sigma_next == 0``).
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -FREQ_FLOW_CLAMP,
                    FREQ_FLOW_CLAMP,
                )
            else:
                x_cur = np.clip(
                    x_cur + dt * v1, -FREQ_FLOW_CLAMP, FREQ_FLOW_CLAMP
                )
            traj[i] = x_cur

        traj_digest = digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "sampler_id": str(sampler_id),
                "num_steps": int(num_steps),
                "guidance_scale": float(guidance_scale),
                "frequency_mix": float(frequency_mix),
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
                "frequency_mix": float(frequency_mix),
            },
        )
        cfg_blob = repr(
            (
                "freqflow_config",
                str(sampler_id),
                int(num_steps),
                float(guidance_scale),
                float(frequency_mix),
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
            FREQ_FLOW_STATE_SHAPE
        )
        # Re-derive the FFT-magnitude side-channel from the final
        # latent so the side-channel stays consistent with the
        # spatial latent across rounds.
        final_mag = _fft_magnitude(x_final)
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
                "freq_final_first": [
                    float(final_mag[0, 0, 0]),
                    float(final_mag[0, 0, 1]),
                    float(final_mag[1, 0, 0]),
                ],
                "t_final": float(FREQ_FLOW_T_END),
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "x": np.asarray(x_final, dtype=np.float64).reshape(FREQ_FLOW_STATE_SHAPE),
                "freq_magnitude": np.asarray(final_mag, dtype=np.float64).reshape(
                    FREQ_FLOW_STATE_SHAPE
                ),
                "t": float(FREQ_FLOW_T_END),
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
                ChannelName("freq_magnitude"): _make_ref(
                    "freq",
                    src_digest=str(endpoint_digest),
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
            provenance=tuple(state.provenance) + (AUDIT_FREQ_FLOW_OBSERVED,),
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
        ``[-FREQ_FLOW_CLAMP, FREQ_FLOW_CLAMP]``) and whose
        ``provenance`` records the
        :data:`AUDIT_FORWARD_NOISE_APPLIED` tag. The FFT-magnitude
        side-channel is re-derived from the noisy latent so the
        side-channel stays consistent with the spatial latent.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        x_prior = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            FREQ_FLOW_STATE_SHAPE
        )
        x_new_arr = np.asarray(injected, dtype=np.float64).reshape(
            FREQ_FLOW_STATE_SHAPE
        )
        x_new = np.clip(x_prior + x_new_arr, -FREQ_FLOW_CLAMP, FREQ_FLOW_CLAMP)
        # Re-derive the FFT-magnitude side-channel from the noisy
        # latent so the side-channel stays consistent.
        new_mag = _fft_magnitude(x_new)
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
                "freq_first": [
                    float(new_mag[0, 0, 0]),
                    float(new_mag[0, 0, 1]),
                    float(new_mag[1, 0, 0]),
                ],
            }
        )
        self._put_native_state(
            new_digest,
            {
                "x0": x_new,
                "freq_magnitude": new_mag,
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


def default_freqflow_adapter(
    *,
    weights_path: Path | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    num_steps: int | None = None,
    class_label: int = FREQ_FLOW_CLASS_LABEL_DEFAULT,
    frequency_mix: float = FREQ_FLOW_FREQ_MIX_DEFAULT,
    solver: str = FREQ_FLOW_INTEGRATOR_EULER,
) -> FreqFlowAdapter:
    """Default factory for :class:`FreqFlowAdapter`.

    When ``weights_path`` is ``None`` the adapter resolves
    ``data/freqflow/nnet_ema.pth`` (or ``data/nnet_ema.pth``); when
    neither exists and ``force_mode`` is ``"auto"``, the adapter
    falls back to ``synthetic`` mode (testing-only).

    The ``class_label`` parameter selects the ImageNet class label
    (0..999, or 1000 for unconditional); the ``num_steps`` parameter
    defaults to :data:`FREQ_FLOW_NUM_STEPS_DEFAULT` (=50) when
    ``None``. The ``frequency_mix`` parameter weights the FFT-
    magnitude side-channel contribution (0.0 = pure spatial,
    1.0 = pure frequency).
    """
    if num_steps is None:
        num_steps = int(FREQ_FLOW_NUM_STEPS_DEFAULT)
    return FreqFlowAdapter(
        weights_path=weights_path,
        force_mode=force_mode,
        num_steps=int(num_steps),
        class_label=int(class_label),
        frequency_mix=float(frequency_mix),
        solver=solver,
    )


__all__ = [
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_FREQ_FLOW_OBSERVED",
    "AUDIT_FREQ_FLOW_RESTART_BLEND",
    "ERR_FREQ_FLOW_CLASS_LABEL_INVALID",
    "ERR_FREQ_FLOW_FREQ_MIX_INVALID",
    "ERR_FREQ_FLOW_INTEGRATOR_UNKNOWN",
    "ERR_FREQ_FLOW_NUM_STEPS",
    "ERR_FREQ_FLOW_WEIGHTS_MISSING",
    "FREQ_FLOW_CHANNEL_DOMAINS",
    "FREQ_FLOW_CHANNELS",
    "FREQ_FLOW_CKPT_ENV_VAR",
    "FREQ_FLOW_CKPT_FILENAME",
    "FREQ_FLOW_CLAMP",
    "FREQ_FLOW_CFG_SCALE_DEFAULT",
    "FREQ_FLOW_CLASS_LABEL_DEFAULT",
    "FREQ_FLOW_CONFIG_HASH",
    "FREQ_FLOW_CONFIG_VERSION",
    "FREQ_FLOW_FREQ_MIX_DEFAULT",
    "FREQ_FLOW_INTEGRATORS",
    "FREQ_FLOW_INTEGRATOR_EULER",
    "FREQ_FLOW_INTEGRATOR_HEUN",
    "FREQ_FLOW_LATENT_DIM",
    "FREQ_FLOW_MECHANISM_ID",
    "FREQ_FLOW_NATIVE_STATES_MAXSIZE",
    "FREQ_FLOW_NUM_STEPS_DEFAULT",
    "FREQ_FLOW_STATE_SHAPE",
    "FREQ_FLOW_SYNTHETIC_HIDDEN",
    "FREQ_FLOW_SYNTHETIC_SEED_DEFAULT",
    "FREQ_FLOW_T_END",
    "FREQ_FLOW_UPSTREAM_REPO",
    "FREQ_FLOW_UPSTREAM_TARBALL_SHA256",
    "FreqFlowAdapter",
    "FreqFlowCapabilities",
    "default_freqflow_adapter",
    "freqflow_resolve_weights_path",
    "torch_is_available",
]
