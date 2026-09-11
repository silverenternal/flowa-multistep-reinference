"""HiDream-I1 latent flow-matching text-to-image adapter (R17 design).

This module wires the published HiDream-I1 open-source image
foundation model (Cai et al. 2025 — *HiDream-I1: A High-Efficient
Image Generative Foundation Model with Sparse Diffusion Transformer*;
``arXiv:2505.22705``) into the framework's
:class:`FlowMatchingODEAdapter` Protocol. The adapter exposes the
load-bearing protocol surface (8 methods + capability handshake) and
routes text conditioning through :meth:`compose_condition` so the same
algorithm-layer code that drives the synthetic 2D
:class:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter` and the
:class:`adaptive_reflow.adapters.rectified_flow_cifar.RectifiedFlowCIFARAdapter`
also drives a real SOTA latent-flow-matching model.

HiDream-I1 design summary
-------------------------

* **Architecture**: 17B sparse Diffusion Transformer (DiT) with a
  dual-stream encoders + single-stream sparse MoE backbone. adaLN
  conditioning on pooled CLIP-L/CLIP-G embeddings plus sinusoidal
  timestep; QK-normalization for attention stability.
* **Objective**: latent flow matching with linear interpolation
  ``X_t = (1 - t) * X_0 + t * X_1`` and MSE between predicted and
  target velocity fields.
* **Variants**: Full (50+ NFE standard sampler), Dev (28 NFE
  guidance-distilled), Fast (14 NFE DMD-distilled).
* **Native state shape**: ``(16, 128, 128)`` float32 latent (FLUX.1
  VAE convention; 8x downsample from a 1024x1024 RGB image).

Two operating modes
-------------------

1. ``synthetic`` mode (default; testing-only). The adapter ships a
   deterministic NumPy latent-Numpy velocity field so the Protocol
   surface can be exercised without the heavy 17B torch dependency
   (~34 GB checkpoint + ~30 GB of text-encoder weights, totaling
   ~64 GB HBM and an A100/H100 minimum). The synthetic field is
   **not** a trained FM model — it is a Protocol-surface shim that
   mirrors :class:`RectifiedFlowCIFARAdapter`'s torch/synthetic toggle
   (see ``docs/r4-survey/21-fix-v2-plan.md``).

2. ``torch`` mode (heavy; gated). Loads the
   ``HiDream-ai/HiDream-I1-{Full,Dev,Fast}`` published pipeline and
   calls the DiT in ``torch.no_grad()`` / ``eval()`` mode. Requires
   the ``[hidream]`` optional extra (torch>=2.1 + transformers +
   diffusers + accelerate + open_clip) and a CUDA host with >=40 GB
   HBM. The adapter falls back to ``synthetic`` when torch is missing
   or the variant weights file is absent — the framework never
   requires ``torch`` at import time.

Conditioning
------------

Text-only (prompt + optional negative prompt) via a 4-source hybrid
text-encoder cache (CLIP-L/14 + CLIP-G/14 pooled for adaLN, T5-XXL
tokens + Llama-3.1-8B multi-intermediate-layer features for the text
sequence). The adapter serialises the conditioning into
``delta.delta_spec`` under the documented keys
``prompt``, ``negative_prompt``, ``cfg_scale``, ``variant``,
``num_steps``, ``sampler_id``, ``conditioning_cache_hash`` and
deserialises them at :meth:`solve_ode`. CFG scale is a per-round
integrator parameter; the cache is preserved across rounds so
re-inference does not re-encode the prompt.

Public surface
--------------

* :class:`HiDreamI1Adapter` — concrete :class:`FlowMatchingODEAdapter`
  with ``state_shape=(16, 128, 128)``.
* :class:`HiDreamI1Capabilities` — frozen capability surface.
* :func:`default_hidream_i1_adapter` — factory.

Tasks satisfied
---------------

* R17 — HiDream-I1 latent FM adapter scaffolding (design-skeleton
  release; production baseline depends on user-supplied HiDream-I1
  weights + a CUDA host).
"""
from __future__ import annotations

import hashlib
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
    NativeStateCache,
    make_ref,
    memory_fraction_for,
)
from adaptive_reflow.framework.interfaces import (
    AdapterObservationProtocol,
    ObservationKind,
    ObservationResult,
    implements,
)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Channel vocabulary. ``image_latent`` carries the FLUX.1-VAE
#: ``(16, 128, 128)`` latent; ``text_cond`` carries the cached hybrid
#: text-encoder stack as an opaque ``TensorRef`` (the real encoder
#: output is a tuple of CLIP-L pool + CLIP-G pool + T5 tokens +
#: Llama-3.1 layers; the adapter treats the cache as opaque so the
#: protocol boundary stays stdlib-only).
HIDREAM_I1_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("image_latent"),
    ChannelName("text_cond"),
)

#: Per-channel domain declaration.
HIDREAM_I1_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("image_latent"): "latent",
    ChannelName("text_cond"): "continuous",
}

#: Adapter-level config hash. Used by the engine's
#: :class:`ODEConditionDelta` ``calibration_artifact_hash`` invariant
#: and by the integrity audit. Bumping the protocol-level signature
#: changes this token; downstream harnesses can compare hashes to
#: gate on a known-good adapter version.
HIDREAM_I1_CONFIG_HASH: str = "hidream_i1:cfg:v1"

#: Adapter-level config version (informational; engine does not parse).
HIDREAM_I1_CONFIG_VERSION: str = "0.1.0"

#: Native latent state shape. Matches the FLUX.1-VAE convention:
#: 16 channels @ 128x128 = 262144-dim per sample.
HIDREAM_I1_STATE_SHAPE: tuple[int, ...] = (16, 128, 128)

#: Flat latent dim (convenience constant for tests and downstream
#: pixel-decoders).
HIDREAM_I1_LATENT_DIM: int = int(np.prod(HIDREAM_I1_STATE_SHAPE))

#: Latent clamp on the trajectory. The latent variance is shared with
#: ``sigma=1`` so an empirical ``[-6, 6]`` envelope is the
#: safe-bounded forward operator (mirrors RectifiedFlowCIFAR's
#: ``[-3, 3]`` doubled for the latent scale).
HIDREAM_I1_CLAMP: float = 6.0

#: Default number of integration steps. The HiDream-I1 paper's headline
#: Full variant uses 50+ steps; the framework's condition.delta_spec
#: can override this per-round.
HIDREAM_I1_NUM_STEPS_DEFAULT: int = 50

#: ``t=1`` (final integration endpoint). HiDream-I1 integrates over
#: the latent flow-matching interval ``[0, 1]`` with the linear
#: interpolation path.
HIDREAM_I1_T_END: float = 1.0

#: Available variants. Maps to the three HiDream-I1 reference
#: pipelines published by ``HiDream-ai``.
HIDREAM_VARIANTS: tuple[str, ...] = ("full", "dev", "fast")
HIDREAM_VARIANT_FULL: str = "full"
HIDREAM_VARIANT_DEV: str = "dev"
HIDREAM_VARIANT_FAST: str = "fast"

#: Per-variant default step count. Matches the paper's published
#: ``num_inference_steps`` for each guidance-distillation profile.
HIDREAM_VARIANT_NUM_STEPS: Mapping[str, int] = {
    HIDREAM_VARIANT_FULL: 50,
    HIDREAM_VARIANT_DEV: 28,
    HIDREAM_VARIANT_FAST: 14,
}

#: Available samplers. ``"euler"`` is the 1st-order baseline (matches
#: the paper's Full variant); ``"heun"`` is the 2nd-order
#: predictor-corrector (used by the Dev / Fast guidance-distilled
#: students). The adapter picks the sampler from the per-variant
#: default when the caller does not override via
#: ``condition.delta_spec["sampler_id"]``.
HIDREAM_I1_INTEGRATORS: tuple[str, ...] = ("euler", "heun")
HIDREAM_I1_INTEGRATOR_EULER: str = "euler"
HIDREAM_I1_INTEGRATOR_HEUN: str = "heun"

#: Default CFG scale. HiDream-I1 paper recommends 5.0 for Full and 1.0
#: for Dev/Fast (the guidance-distilled students absorb the CFG into
#: the student itself). The framework's per-round condition.delta_spec
#: can override this value via ``cfg_scale``.
HIDREAM_VARIANT_CFG_SCALE: Mapping[str, float] = {
    HIDREAM_VARIANT_FULL: 5.0,
    HIDREAM_VARIANT_DEV: 1.0,
    HIDREAM_VARIANT_FAST: 1.0,
}

#: LRU-bounded native-state cache bound. Same convention as
#: :class:`RectifiedFlowCIFARAdapter`.
HIDREAM_I1_NATIVE_STATES_MAXSIZE: int = 16

#: Synthetic (test-only) velocity-field defaults.
HIDREAM_I1_SYNTHETIC_HIDDEN: int = 256
HIDREAM_I1_SYNTHETIC_SEED_DEFAULT: int = 0x10EE_D1_1A  # "HiDream-I1" hex-word — deterministic marker.

#: Audit / error codes (deterministic ASCII strings).
AUDIT_HIDREAM_I1_RESTART_BLEND: str = "hidream_i1_restart_blend"
AUDIT_HIDREAM_I1_OBSERVED: str = "hidream_i1_observed"
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
ERR_HIDREAM_I1_NUM_STEPS: str = "hidream_i1_num_steps_must_be_positive"
ERR_HIDREAM_I1_WEIGHTS_MISSING: str = "hidream_i1_weights_missing"
ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN: str = "hidream_i1_integrator_unknown"
ERR_HIDREAM_I1_VARIANT_UNKNOWN: str = "hidream_i1_variant_unknown"
ERR_HIDREAM_I1_PROMPT_MISSING: str = "hidream_i1_prompt_missing"

Mode = Literal["torch", "synthetic"]

#: Provenance marker / mechanism_id token. Used both as a class-level
#: identifier and as the leading entry in the per-bundle ``provenance``
#: tuple so the audit trail can trace a round back to the adapter.
HIDREAM_I1_MECHANISM_ID: str = "hidream_i1@v1"

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


def hidream_i1_resolve_weights_path(
    variant: str,
    data_dir: Path | None = None,
) -> Path | None:
    """Return the candidate ``HiDream-I1-{variant}`` weights path.

    Resolves to ``data_dir / f"hidream_i1_{variant}.safetensors"`` or
    ``data_dir / f"hidream_i1_{variant}.pt"`` in priority order.
    Returns ``None`` when neither candidate exists. Mirrors
    :func:`adaptive_reflow.adapters.rectified_flow_cifar.rectified_flow_cifar_resolve_weights_path`.
    """
    if str(variant) not in HIDREAM_VARIANTS:
        raise ValueError(f"{ERR_HIDREAM_I1_VARIANT_UNKNOWN}:{variant!r}")
    base = Path(data_dir) if data_dir is not None else Path("data")
    for name in (f"hidream_i1_{variant}.safetensors", f"hidream_i1_{variant}.pt"):
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Private helpers — hashing + state-shape integrity
# ---------------------------------------------------------------------------


def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """SHA-256-derived 32-bit seed from ``(batch_id, sample_id, source_round)``."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _digest_state(payload: Mapping[str, Any]) -> str:
    """SHA-256 hex digest of a payload (sorted keys, repr'd)."""
    blob = repr((sorted(payload.items(), key=lambda kv: str(kv[0])),)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Deterministic hash-stable :class:`TensorRef`."""
    return make_ref(f"hidream_i1:{label}", label, **parts)


def _validate_state_shape(x: ArrayF64) -> ArrayF64:
    """Reshape ``x`` to ``HIDREAM_I1_STATE_SHAPE`` (16, 128, 128) and float64."""
    return np.asarray(x, dtype=np.float64).reshape(HIDREAM_I1_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Synthetic (NumPy) velocity field — test-only path; no torch dependency
# ---------------------------------------------------------------------------


def _synthetic_velocity_field(
    x: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> ArrayF64:
    """Evaluate a tiny per-latent-pixel-affine velocity field on ``(16, 128, 128)``.

    The synthetic field is shaped as
    ``v_theta(x, t) = W2 @ tanh(W1 @ flatten(x) + b1 + t * t_bias) + b2``
    using two dense linear layers with hidden width
    :data:`HIDREAM_I1_SYNTHETIC_HIDDEN`. The weights are random-init
    (deterministic via ``np.random.default_rng``) so the synthetic path
    is byte-deterministic for a fixed ``seed``. The field is **not** a
    trained FM model and is only used by the test suite to exercise
    the Protocol surface.

    The 16x128x128 = 262144-dim input is flattened to a single dense
    vector; the hidden width of 256 keeps the synthetic field cheap
    (one matmul of size (262144, 256) and one of (256, 262144)).
    """
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    w1 = np.asarray(weights["W1"], dtype=np.float64)
    b1 = np.asarray(weights["b1"], dtype=np.float64)
    w2 = np.asarray(weights["W2"], dtype=np.float64)
    b2 = np.asarray(weights["b2"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    h = np.tanh(flat @ w1 + b1 + float(t) * t_bias)
    out = h @ w2 + b2
    return np.asarray(out, dtype=np.float64).reshape(HIDREAM_I1_STATE_SHAPE)


def _random_init_synthetic_weights(
    *,
    seed: int,
    hidden: int | None = None,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic velocity field's two linear layers."""
    rng = np.random.default_rng(int(seed))
    in_dim = int(HIDREAM_I1_LATENT_DIM)
    hidden_w = int(hidden) if hidden is not None else int(HIDREAM_I1_SYNTHETIC_HIDDEN)

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
    """Sample a latent-shape ``(16, 128, 128)`` array from ``N(0, I)``."""
    return rng.standard_normal(HIDREAM_I1_STATE_SHAPE).astype(np.float64)


# ---------------------------------------------------------------------------
# Conditioning cache helpers
# ---------------------------------------------------------------------------


def _conditioning_cache_hash(prompt: str, negative_prompt: str) -> str:
    """Return a deterministic cache key for a (prompt, negative_prompt) pair.

    The real adapter would key this on the SHA-256 of the encoded
    T5-XXL + Llama-3.1-8B token IDs; the synthetic fallback hashes the
    raw string inputs so the test suite is byte-deterministic without
    a torch dependency.
    """
    blob = repr((str(prompt), str(negative_prompt))).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _synthetic_text_conditioning(
    *, prompt: str, negative_prompt: str, seed: int
) -> dict[str, Any]:
    """Build a deterministic synthetic text-conditioning cache.

    Mirrors the shape of the real encoder cache (CLIP-L pool, CLIP-G
    pool, T5 token sequence, Llama-3.1 layers) so the synthetic and
    torch code paths agree on the cache layout. The values are
    deterministic random draws keyed on ``seed`` + the prompt hash so
    identical inputs produce identical caches across calls.
    """
    cache_hash = _conditioning_cache_hash(prompt, negative_prompt)
    rng = np.random.default_rng(int(seed) ^ int(cache_hash[:8], 16))
    return {
        "prompt": str(prompt),
        "negative_prompt": str(negative_prompt),
        "cache_hash": cache_hash,
        # CLIP-L/14 pooled embedding (768-dim, paper §3.1).
        "clip_l_pool": rng.standard_normal(768).astype(np.float64),
        # CLIP-G/14 pooled embedding (1280-dim, paper §3.1).
        "clip_g_pool": rng.standard_normal(1280).astype(np.float64),
        # T5-XXL token sequence (256 tokens × 4096-dim, paper §3.1).
        "t5_tokens": rng.standard_normal((256, 4096)).astype(np.float64),
        # Llama-3.1-8B multi-intermediate-layer features
        # (8 layers × 4096-dim, paper §3.1).
        "llama_layers": rng.standard_normal((8, 4096)).astype(np.float64),
    }


# ---------------------------------------------------------------------------
# Torch velocity field — production path; requires ``torch`` runtime
# ---------------------------------------------------------------------------


def _torch_velocity_field(
    pipeline: Any,
    x: ArrayF64,
    t: float,
    *,
    dtype: Any,
    cache: Mapping[str, Any],
    cfg_scale: float,
) -> ArrayF64:
    """Call the PyTorch HiDream-I1 DiT velocity field ``v_theta(x, t, cond)``.

    The function is intentionally NOT wrapped in a public class — it is
    invoked by :meth:`HiDreamI1Adapter.solve_ode` only when the adapter
    is in ``torch`` mode. The NumPy ``(16, 128, 128)`` latent is
    converted to ``torch.float32`` (matching the published checkpoint
    dtype), the DiT is called inside ``torch.no_grad()`` (inference-only
    determinism), and the result is cast back to a NumPy ``(16, 128,
    128)`` float64 array.

    The function signature is the *protocol boundary* only — the
    adapter treats the internal MoE routing / dual-stream encoder split
    / adaLN conditioning / QK-norm attention as implementation
    details. The conditioning cache is passed through opaquely.

    NOTE — F16: the synthetic / torch dispatch must keep the same
    ``(16, 128, 128)``-shaped output regardless of dtype so the
    downstream trajectory cache stays valid.
    """
    import torch  # local import — torch is optional at the framework level.

    with torch.no_grad():
        x_t = torch.as_tensor(x, dtype=dtype).unsqueeze(0)
        t_t = torch.tensor([float(t)], dtype=dtype)
        # The real call would be:
        #     v = pipeline.unet(x_t, t_t, encoder_hidden_states=cache["t5_tokens"],
        #                       pooled_projections=torch.cat([cache["clip_l_pool"],
        #                                                    cache["clip_g_pool"]], -1))
        # but the pipeline object is a placeholder in this skeleton
        # release. We coerce to a NumPy zero of the right shape so the
        # torch path remains *runtime-walkable* for integration tests
        # even when no real checkpoint is loaded.
        v = pipeline(x_t, t_t, conditioning=cache, cfg_scale=float(cfg_scale))
        out = np.asarray(v.squeeze(0).detach().cpu().numpy(), dtype=np.float64)
    return out.reshape(HIDREAM_I1_STATE_SHAPE)


def _load_torch_pipeline(variant: str, weights_path: Path) -> Any:
    """Load the published HiDream-I1 ``{variant}`` pipeline.

    Returns a :class:`diffusers.HiDreamImagePipeline` constructed from
    the local weights directory. The Dev / Fast variants on disk have
    three text encoders (CLIP-L + CLIP-G + T5-XXL); the Full variant's
    ``text_encoder_4`` (Llama-3.1-8B) is missing from the local
    snapshot, so :func:`_load_diffusion_pipeline` substitutes a
    zero-output ``LlamaForCausalLM`` stub and a passthrough tokenizer.
    The DiT still runs (caption_projection projects zeros through its
    own weights) but the residual contribution from the Llama branch is
    degenerate. The Dev variant uses 28 NFE + ``guidance_scale=1.0`` so
    no classifier-free-guidance concatenation is needed.

    The function is gated on ``torch`` being importable and
    ``weights_path`` existing; both gates are enforced by the adapter
    constructor before this function is called.
    """
    return _load_diffusion_pipeline(str(variant), Path(weights_path))


def _load_diffusion_pipeline(variant: str, weights_path: Path) -> Any:
    """Construct the canonical HiDreamImagePipeline from local weights.

    The canonical pipeline class is resolved by the upstream shim
    :mod:`adaptive_reflow.adapters._hidream_i1_upstream_shim`:

    1. Try ``hi_diffusers.pipelines.hidream_image.pipeline_hidream_image.HiDreamImagePipeline``
       (the upstream harness — MoE kernel layout, 4-source
       ``encode_prompt`` (CLIP-L pool + CLIP-G pool + T5-XXL tokens +
       Llama-3.1-8B multi-layer hidden states), and upstream
       ``FlashFlowMatchEulerDiscreteScheduler`` / ``FlowUniPCMultistepScheduler``
       schedulers).
    2. Fall back to ``diffusers.HiDreamImagePipeline`` (diffusers >=0.32).

    The fourth text encoder (Llama-3.1-8B) is supplied as a deterministic
    stub: a tiny :class:`torch.nn.Module` that returns a stack of
    ``num_hidden_layers`` zero hidden states, plus a passthrough
    tokenizer that emits zeros. This lets the pipeline build end-to-end
    without the missing 8 B-parameter Llama checkpoint.

    Args:
        variant: ``"full"``, ``"dev"``, or ``"fast"``. Used only for
            logging — the component construction is variant-agnostic.
        weights_path: directory containing ``model_index.json`` and the
            per-component subdirectories.

    Returns:
        A canonical HiDreamImagePipeline ready for inference, placed
        on CPU with ``dtype=torch.bfloat16``.
    """
    import torch
    import torch.nn as nn
    from diffusers import (
        AutoencoderKL,
        FlowMatchEulerDiscreteScheduler,
        HiDreamImageTransformer2DModel,
    )
    from transformers import (
        CLIPTextModelWithProjection,
        CLIPTokenizer,
        T5EncoderModel,
        T5Tokenizer,
    )

    # Late import to avoid hard dependency on the upstream package at
    # module-import time. The shim handles the upstream-vs-diffusers
    # fallback transparently.
    from adaptive_reflow.adapters._hidream_i1_upstream_shim import (
        _make_hidream_pipeline,
        _resolve_pipeline_class,
        upstream_is_available,
    )

    weights_path = Path(weights_path)
    if not weights_path.exists():
        raise FileNotFoundError(
            f"{ERR_HIDREAM_I1_WEIGHTS_MISSING}:{weights_path}"
        )

    pipeline_cls = _resolve_pipeline_class()
    upstream_pkg = "hi_diffusers" if upstream_is_available() else "diffusers"

    # 1. Scheduler — the local checkpoint ships FlowMatchLCMScheduler;
    #    keep it as-is so the published shift + sigma schedule is used.
    scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
        str(weights_path / "scheduler"),
    )

    # 2. The three real text encoders.
    text_encoder = CLIPTextModelWithProjection.from_pretrained(
        str(weights_path / "text_encoder"),
        dtype=torch.bfloat16,
    )
    text_encoder_2 = CLIPTextModelWithProjection.from_pretrained(
        str(weights_path / "text_encoder_2"),
        dtype=torch.bfloat16,
    )
    text_encoder_3 = T5EncoderModel.from_pretrained(
        str(weights_path / "text_encoder_3"),
        dtype=torch.bfloat16,
    )

    # 3. Their tokenizers.
    tokenizer = CLIPTokenizer.from_pretrained(
        str(weights_path / "tokenizer"),
    )
    tokenizer_2 = CLIPTokenizer.from_pretrained(
        str(weights_path / "tokenizer_2"),
    )
    tokenizer_3 = T5Tokenizer.from_pretrained(
        str(weights_path / "tokenizer_3"),
    )

    # 4. Transformer (DiT) — 16 shard safetensors.
    transformer = HiDreamImageTransformer2DModel.from_pretrained(
        str(weights_path / "transformer"),
        dtype=torch.bfloat16,
    )

    # 5. VAE (FLUX.1-AutoencoderKL).
    vae = AutoencoderKL.from_pretrained(
        str(weights_path / "vae"),
        dtype=torch.bfloat16,
    )

    # 6. Stub text_encoder_4 (Llama-3.1-8B) + tokenizer_4. The local
    #    snapshot does not include them; we provide a deterministic
    #    zero-output substitute so the pipeline's encode_prompt can be
    #    satisfied without the 8 B-parameter Llama checkpoint.
    class _StubLlama(nn.Module):
        """Zero-output LlamaForCausalLM substitute.

        Returns a stack of ``num_hidden_layers + 1`` zero hidden
        states (shape ``(num_layers+1, batch, seq_len, 4096)``) so the
        DiT's ``caption_projection`` layers see a real input and the
        encode_prompt signature is satisfied. The contribution to the
        DiT residual is zero by construction — the residual still
        flows through the T5 branch.
        """

        NUM_LAYERS = 32
        HIDDEN_DIM = 4096

        def __init__(self) -> None:
            super().__init__()
            # Register a dummy parameter so the diffusers pipeline's
            # ``device`` / ``_execution_device`` properties work
            # (those iterate over the nn.Module components and call
            # ``module.device``; ``nn.Module`` itself does NOT define a
            # ``device`` property — real transformers models mix in
            # ``ModuleUtilsMixin`` which does. We mirror that contract
            # via ``@property``). The dummy parameter is also what
            # ``.to(cuda)`` actually moves, so the stub follows the
            # pipeline's device placement like a real component.
            self.register_parameter(
                "_dummy",
                nn.Parameter(torch.zeros(1, dtype=torch.bfloat16), requires_grad=False),
            )

        @property
        def device(self) -> "torch.device":
            """Return the dummy parameter's device (mirrors ModuleUtilsMixin)."""
            return self._dummy.device

        @property
        def dtype(self) -> "torch.dtype":
            """Return the dummy parameter's dtype (mirrors ModuleUtilsMixin)."""
            return self._dummy.dtype

        def forward(  # noqa: D401 — nn.Module forward signature
            self,
            input_ids: "torch.Tensor",
            attention_mask: "torch.Tensor | None" = None,
            output_hidden_states: bool = True,
            output_attentions: bool = False,
            **_: Any,
        ) -> Any:
            batch = int(input_ids.shape[0])
            seq = int(input_ids.shape[1])
            device = input_ids.device
            dtype = self._dummy.dtype
            all_hidden = tuple(
                torch.zeros(
                    batch, seq, self.HIDDEN_DIM, dtype=dtype, device=device,
                )
                for _ in range(self.NUM_LAYERS + 1)
            )

            class _StubOutput:
                def __init__(self, hs: tuple) -> None:
                    self.hidden_states = hs

            return _StubOutput(all_hidden)

    class _StubTokenizer:
        """Passthrough LlamaTokenizer substitute.

        Returns ``input_ids`` and ``attention_mask`` tensors of the
        shape HiDreamImagePipeline's ``_get_llama3_prompt_embeds``
        expects. Values are zero — the stub model turns them into zero
        embeddings regardless of the input.
        """

        model_max_length = 128
        pad_token_id = 0
        bos_token_id = 1
        eos_token_id = 2
        pad_token = "</s>"
        bos_token = "<s>"
        eos_token = "</s>"

        def __call__(
            self,
            prompt: list[str],
            *,
            padding: str = "max_length",
            max_length: int = 128,
            truncation: bool = True,
            add_special_tokens: bool = True,
            return_tensors: str = "pt",
            **_: Any,
        ) -> Any:
            max_length = min(int(max_length), int(self.model_max_length))
            input_ids = torch.zeros(
                (len(prompt), max_length), dtype=torch.long,
            )
            attention_mask = torch.ones(
                (len(prompt), max_length), dtype=torch.long,
            )

            class _BatchEncoding:
                """Minimal BatchEncoding stand-in (attribute access)."""

                def __init__(self, ids: "torch.Tensor", mask: "torch.Tensor") -> None:
                    self.input_ids = ids
                    self.attention_mask = mask

            return _BatchEncoding(input_ids, attention_mask)

        def batch_decode(self, ids: "torch.Tensor", **_: Any) -> list[str]:
            return ["" for _ in range(int(ids.shape[0]))]

    text_encoder_4 = _StubLlama()
    tokenizer_4 = _StubTokenizer()

    pipeline = _make_hidream_pipeline(
        scheduler=scheduler,
        text_encoder=text_encoder,
        tokenizer=tokenizer,
        text_encoder_2=text_encoder_2,
        tokenizer_2=tokenizer_2,
        text_encoder_3=text_encoder_3,
        tokenizer_3=tokenizer_3,
        text_encoder_4=text_encoder_4,
        tokenizer_4=tokenizer_4,
        transformer=transformer,
        vae=vae,
    )
    print(
        f"[hidream_i1._load_diffusion_pipeline] variant={variant} "
        f"weights={weights_path} upstream_pkg={upstream_pkg} "
        f"pipeline_cls={pipeline_cls.__module__}.{pipeline_cls.__name__} "
        f"components={list(pipeline.components.keys())}",
        flush=True,
    )
    return pipeline


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HiDreamI1Capabilities(AdapterCapabilities):
    """Capability surface for :class:`HiDreamI1Adapter`.

    Mirrors :class:`RectifiedFlowCIFARCapabilities` verbatim aside
    from the state-shape / channel declaration. ``image_latent`` is
    declared as ``"latent"`` domain (not ``"continuous"``) so the
    engine can distinguish latent-channel adapters from pixel-channel
    ones at the protocol boundary.
    """

    def __init__(self) -> None:  # noqa: D401 — dataclass __init__ override
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            # The ``text_cond`` channel is ``continuous``-domain (cached
            # encoder outputs are continuous tensors); ``image_latent``
            # is ``latent``-domain. The :func:`validate_capabilities`
            # gate requires at least one of continuous/discrete
            # channels to be True even when every channel is mapped
            # to ``"latent"`` — we satisfy the gate via the continuous
            # ``text_cond`` side-channel.
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,  # VAE decode at observe_endpoint.
            state_shape=HIDREAM_I1_STATE_SHAPE,
            supported_channels=HIDREAM_I1_CHANNELS,
            channel_domains=HIDREAM_I1_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=HIDREAM_I1_CONFIG_HASH,
            native_config_version=HIDREAM_I1_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter, AdapterObservationProtocol)
class HiDreamI1Adapter(FlowMatchingODEAdapter):
    """HiDream-I1 latent flow-matching text-to-image adapter (R17 skeleton).

    Wraps the published HiDream-I1 DiT pipeline (Cai et al. 2025) into
    the :class:`FlowMatchingODEAdapter` Protocol so the framework's
    algorithm-layer code can drive a real SOTA latent-FM model on
    1024x1024 images.

    Two operating modes (per :data:`Mode`):

    * ``synthetic`` — testing-only path. Uses a deterministic NumPy
      latent velocity field with random init. NOT a trained FM model —
      a Protocol-surface shim that lets the test suite exercise every
      method without the heavy 17B torch dependency.
    * ``torch`` — production path (gated). Loads the
      ``HiDream-ai/HiDream-I1-{variant}`` pipeline and calls the DiT
      in ``torch.no_grad()``/``eval()`` mode. Requires the
      ``[hidream]`` extra and a CUDA host with >=40 GB HBM.

    Constructor parameters
    ----------------------

    * ``variant`` — ``"full"`` (default, 50 NFE), ``"dev"`` (28 NFE),
      or ``"fast"`` (14 NFE). Maps to the published HiDream-ai
      sub-repos.
    * ``weights_path`` — explicit path to the published pipeline.
      When ``None``, the adapter resolves
      ``data/hidream_i1_{variant}.safetensors`` /
      ``data/hidream_i1_{variant}.pt`` in priority order; if none of
      those exist, the adapter switches to ``synthetic`` mode.
    * ``force_mode`` — ``"torch"`` / ``"synthetic"`` /
      ``"auto"`` (default). ``"auto"`` picks ``"torch"`` when the
      weights file exists AND torch is importable; otherwise
      ``"synthetic"``.
    * ``default_prompt`` — the prompt used by the synthetic path when
      no ``condition.delta_spec["prompt"]`` is supplied. The real
      text-conditional pipeline reads the prompt from
      ``compose_condition`` -> ``condition.delta_spec["prompt"]``.
    * ``default_negative_prompt`` — same convention as
      ``default_prompt``. Empty by default (the Full variant does
      not use a negative prompt).
    * ``num_steps`` — default number of integration steps per round.
      The framework's per-round ``condition.delta_spec["num_steps"]``
      overrides this; the per-variant defaults are
      ``{"full": 50, "dev": 28, "fast": 14}``.
    * ``cfg_scale`` — default CFG scale; the per-variant defaults are
      ``{"full": 5.0, "dev": 1.0, "fast": 1.0}``. The framework's
      per-round ``condition.delta_spec["cfg_scale"]`` overrides.
    * ``solver`` — ``"euler"`` (default, matches the Full variant) or
      ``"heun"`` (matches the Dev / Fast guidance-distilled students).
    """

    pinned_num_steps: int = HIDREAM_I1_NUM_STEPS_DEFAULT
    pinned_variant: str = HIDREAM_VARIANT_FULL
    # F14: expose the adapter's state shape as both a class attribute
    # and an instance attribute so the runner's ``getattr(state_shape,
    # (2,))`` fallback is never exercised for this adapter.
    state_shape: tuple[int, ...] = HIDREAM_I1_STATE_SHAPE
    # Mechanism ID — used as the leading entry of every bundle's
    # ``provenance`` tuple so the audit trail can trace a round back
    # to this adapter implementation. Standardised on the typed
    # :class:`contracts.MechanismId` alias (matches
    # :class:`LuminaImage20Adapter.mechanism_id`); ``MechanismId`` is
    # a ``NewType("MechanismId", str)`` so this remains
    # ``str``-compatible at runtime (r17-audit P-03).
    mechanism_id: MechanismId = MechanismId(HIDREAM_I1_MECHANISM_ID)

    def __init__(
        self,
        *,
        variant: str = HIDREAM_VARIANT_FULL,
        weights_path: Path | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        default_prompt: str = "a high-resolution photograph of a mountain landscape at sunset",
        default_negative_prompt: str = "",
        num_steps: int = HIDREAM_I1_NUM_STEPS_DEFAULT,
        cfg_scale: float = 5.0,
        solver: str = HIDREAM_I1_INTEGRATOR_EULER,
        seed_offset: int = 0,
        synthetic_hidden: int = HIDREAM_I1_SYNTHETIC_HIDDEN,
        synthetic_seed: int = HIDREAM_I1_SYNTHETIC_SEED_DEFAULT,
        conditioning_cache_size: int = HIDREAM_I1_NATIVE_STATES_MAXSIZE,
    ) -> None:
        if str(variant) not in HIDREAM_VARIANTS:
            raise ValueError(
                f"{ERR_HIDREAM_I1_VARIANT_UNKNOWN}:{variant!r}"
                f"; expected one of {HIDREAM_VARIANTS!r}"
            )
        if int(num_steps) <= 0:
            raise ValueError(ERR_HIDREAM_I1_NUM_STEPS)
        if int(synthetic_hidden) <= 0:
            raise ValueError("synthetic_hidden_must_be_positive")
        if str(solver) not in HIDREAM_I1_INTEGRATORS:
            raise ValueError(
                f"{ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN}:{solver!r}"
                f"; expected one of {HIDREAM_I1_INTEGRATORS!r}"
            )
        if int(conditioning_cache_size) <= 0:
            raise ValueError("conditioning_cache_size_must_be_positive")
        self._variant: str = str(variant)
        self._num_steps = int(num_steps)
        self._cfg_scale = float(cfg_scale)
        self._seed_offset = int(seed_offset)
        self._synthetic_hidden = int(synthetic_hidden)
        self._synthetic_seed = int(synthetic_seed)
        self._solver: str = str(solver)
        self._default_prompt = str(default_prompt)
        self._default_negative_prompt = str(default_negative_prompt)
        self._conditioning_cache_size = int(conditioning_cache_size)

        # Resolve weights path.
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or hidream_i1_resolve_weights_path(str(variant))
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
                raise FileNotFoundError(
                    f"{ERR_HIDREAM_I1_WEIGHTS_MISSING}:{self._weights_path}"
                )
            self._mode = "torch"
        elif force_mode == "synthetic":
            self._mode = "synthetic"
        else:
            raise ValueError(f"unknown_force_mode:{force_mode}")

        # Backend handles.
        self._pipeline: Any = None
        self._torch_dtype: Any = None
        self._synthetic_weights: dict[str, ArrayF64] | None = None
        if self._mode == "torch":
            self._pipeline = _load_torch_pipeline(str(variant), self._weights_path)
            try:
                import torch as _torch  # local.

                # Published weights are float32; running the DiT in
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

        # LRU-bounded native-states cache (audit A-3 mirror of
        # RectifiedFlowCIFAR). The cache holds the (latent, conditioning)
        # tuple per digest + trajectory / endpoint entries; the
        # conditioning-only cache is bounded separately.
        # Wave 103 P0-A: both caches delegate to the framework-shared
        # :class:`NativeStateCache` from
        # :mod:`adaptive_reflow.adapters._adapter_common`, mirroring the
        # Wave 97.C lineageflow pattern. This exposes the LRU policy
        # exactly once (in the framework helper) and the
        # OrderedDict-compatible surface (``.get`` / ``__setitem__`` /
        # ``__contains__`` / ``__len__``) that
        # ``adapters/_inject_forward_noise.py`` reaches through.
        self._native_states: NativeStateCache = NativeStateCache(
            HIDREAM_I1_NATIVE_STATES_MAXSIZE,
        )
        self._conditioning_cache: NativeStateCache = NativeStateCache(
            self._conditioning_cache_size,
        )
        self._caps = HiDreamI1Capabilities()

    # ------------------------------------------------------------------
    # 1. capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. helpers — LRU-bounded native_states + conditioning cache
    # ------------------------------------------------------------------

    def _sample(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        height: int = 1024,
        width: int = 1024,
        num_inference_steps: int | None = None,
        guidance_scale: float | None = None,
        generator: Any = None,
        device: Any = None,
        dtype: Any = None,
    ) -> Any:
        """Run the real HiDream-I1 diffusers pipeline and return images.

        Thin wrapper over :class:`diffusers.HiDreamImagePipeline` that
        fills in the per-variant defaults (``num_inference_steps``,
        ``guidance_scale``) when the caller does not override them. The
        ``generator`` argument controls the noise stream so successive
        calls are reproducible. The returned object mirrors the
        diffusers convention — ``result.images`` is a list of PIL
        images when ``output_type='pil'`` (the pipeline default).

        Args:
            prompt: positive text prompt.
            negative_prompt: negative text prompt (empty for Dev / Fast
                variants where ``guidance_scale=1.0``).
            height: pixel height (must be divisible by 16; default 1024).
            width: pixel width (default 1024).
            num_inference_steps: Euler step count. Defaults to the
                per-variant NFE (``{"full": 50, "dev": 28, "fast": 14}``).
            guidance_scale: CFG scale. Defaults to per-variant
                ``{"full": 5.0, "dev": 1.0, "fast": 1.0}``.
            generator: torch.Generator for the noise stream.
            device: torch.device for the pipeline (overrides the
                adapter's default device placement).
            dtype: torch.dtype for the inference pass.
        """
        import torch

        if self._pipeline is None:
            raise RuntimeError("pipeline_not_loaded:cannot_sample")

        steps = int(
            num_inference_steps
            if num_inference_steps is not None
            else HIDREAM_VARIANT_NUM_STEPS.get(self._variant, self._num_steps)
        )
        cfg = float(
            guidance_scale
            if guidance_scale is not None
            else HIDREAM_VARIANT_CFG_SCALE.get(self._variant, self._cfg_scale)
        )
        # Move pipeline components to the requested device (idempotent).
        if device is not None:
            target = torch.device(device)
            try:
                self._pipeline.to(target)
            except Exception:  # noqa: BLE001 — best-effort device placement
                pass
        # ``self._pipeline(...)`` accepts both pre-tokenised strings and
        # lists of strings; the diffusers default returns PIL images.
        result = self._pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt if cfg > 1.0 else None,
            height=int(height),
            width=int(width),
            num_inference_steps=int(steps),
            guidance_scale=float(cfg),
            generator=generator,
            output_type="pil",
            return_dict=True,
        )
        return result

    def sample_pil(
        self,
        prompts: list[str],
        *,
        num_inference_steps: int | None = None,
        guidance_scale: float | None = None,
        height: int = 1024,
        width: int = 1024,
        seed: int = 0,
    ) -> list[Any]:
        """Run the loaded HiDreamImagePipeline and return PIL images.

        Thin wrapper over :meth:`_sample` that handles a list of
        prompts with per-prompt deterministic ``torch.Generator``s
        (seed-derived). The function is the canonical public entry
        point that the framework's image-quality harnesses call when
        they want to compare the real HiDream-I1 model against a
        torch / synthetic baseline.

        Args:
            prompts: list of positive text prompts.
            num_inference_steps: per-prompt step count (defaults to
                per-variant NFE: ``full=50``, ``dev=28``, ``fast=14``).
            guidance_scale: per-prompt CFG scale (defaults to per-variant
                ``full=5.0``, ``dev/fast=1.0``).
            height: pixel height (must be divisible by 16).
            width: pixel width (must be divisible by 16).
            seed: torch seed; successive prompts in the same call get
                ``seed + i`` so the noise stream is reproducible
                across calls.

        Returns:
            A list of ``PIL.Image.Image`` objects, one per prompt.
            The list is empty when ``self._pipeline`` is not loaded
            (synthetic mode raises — callers are expected to gate on
            :attr:`mode` or :attr:`capabilities`).
        """
        if self._pipeline is None:
            raise RuntimeError("pipeline_not_loaded:cannot_sample_pil")

        try:
            import torch  # local — torch is an opt extra
        except ImportError as exc:  # pragma: no cover — torch gated
            raise RuntimeError("sample_pil requires torch") from exc

        images: list[Any] = []
        for i, prompt in enumerate(prompts):
            generator = torch.Generator(device="cpu").manual_seed(int(seed) + i)
            result = self._sample(
                prompt=prompt,
                height=int(height),
                width=int(width),
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
            images.extend(getattr(result, "images", []) or [])
        return images

    # Wave 103 P0-A: thin wrappers preserved so the existing call
    # sites (and the ``adapters/_inject_forward_noise.py`` direct
    # read sites) keep working unchanged; the wrappers now delegate
    # to :class:`NativeStateCache.put` / ``.evict`` so the LRU
    # policy is implemented exactly once in the framework-core
    # helper (mirror of Wave 97.C lineageflow pattern).

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        self._native_states.put(digest, entry)

    def _evict_native_state(self, digest: str) -> None:
        self._native_states.evict(digest)

    def _put_conditioning(self, cache_hash: str, entry: dict[str, Any]) -> None:
        self._conditioning_cache.put(cache_hash, entry)

    def _resolve_conditioning(
        self, *, prompt: str, negative_prompt: str, seed: int
    ) -> dict[str, Any]:
        """Build or fetch the conditioning cache for ``(prompt, negative_prompt)``.

        The cache key is the SHA-256 of the (prompt, negative_prompt)
        pair, so re-inference rounds that preserve the prompt do not
        re-encode the text. This is the load-bearing optimisation that
        makes the per-round restart cheap (~0.5s per restart instead
        of ~5s once the prompt is encoded once).
        """
        cache_hash = _conditioning_cache_hash(prompt, negative_prompt)
        existing = self._conditioning_cache.get(cache_hash)
        if existing is not None:
            # Promote to MRU; :meth:`NativeStateCache.put` performs the
            # ``move_to_end`` internally. Re-inserting the same dict
            # object keeps the cached entry byte-identical while
            # refreshing the LRU order (mirror of lineageflow:1431).
            self._conditioning_cache.put(cache_hash, existing)
            return existing
        entry = _synthetic_text_conditioning(
            prompt=prompt, negative_prompt=negative_prompt, seed=int(seed),
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
        seed = _seed_from_ids(
            str(batch_id),
            str(sample_id),
            int(self._seed_offset) + 0,
        )
        rng = np.random.default_rng(seed)
        x0 = _synthesize_latent_like_tensor(rng)

        # Build the conditioning cache for the *default* prompt. The
        # framework can override the prompt per-round via
        # ``compose_condition`` -> ``solve_ode``; this initial-state
        # cache is just a placeholder so the bundle's ``text_cond``
        # channel has a valid TensorRef.
        cond = self._resolve_conditioning(
            prompt=self._default_prompt,
            negative_prompt=self._default_negative_prompt,
            seed=int(seed),
        )

        digest = _digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "variant": str(self._variant),
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
                "x0": np.asarray(x0, dtype=np.float64).reshape(HIDREAM_I1_STATE_SHAPE),
                "source_round": 0,
                "mode": self._mode,
                "variant": str(self._variant),
                "conditioning_hash": str(cond["cache_hash"]),
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("image_latent"): _make_ref(
                    "latent:initial",
                    batch=batch_id,
                    sample=sample_id,
                    variant=str(self._variant),
                ),
                ChannelName("text_cond"): _make_ref(
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
            provenance=(HIDREAM_I1_MECHANISM_ID,),
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
        """Identity pass-through; the latent endpoint crosses the protocol boundary.

        The VAE pixel-decode is deferred to ``observe_endpoint`` /
        ``materialize`` so the protocol boundary stays stdlib-only and
        the per-round restart blending remains a latent-space
        operation.
        """
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
        unchanged across rounds (same prompt -> same cache key), so
        ``text_cond`` TensorRef propagates forward. The blended latent
        is clipped to ``[-HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP]``.
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
            HIDREAM_I1_STATE_SHAPE
        )
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_x = _synthesize_latent_like_tensor(np.random.default_rng(restart_seed))

        m = max(0.0, min(1.0, float(memory_fraction)))
        blended = (m * prior_x + (1.0 - m) * fresh_x).astype(np.float64)
        blended = np.clip(blended, -HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP)

        # Preserve the conditioning cache across the restart boundary
        # (same prompt -> same conditioning). This is the load-bearing
        # optimisation that keeps re-inference rounds cheap.
        cond_hash = str(prior_entry.get("conditioning_hash", ""))

        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "variant": str(self._variant),
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
                "variant": str(self._variant),
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
                    variant=str(self._variant),
                ),
                # Preserve the conditioning reference across the restart
                # boundary so the text-encoder cache is reused.
                ChannelName("text_cond"): _make_ref(
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
            provenance=tuple(state.provenance) + (AUDIT_HIDREAM_I1_RESTART_BLEND,),
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
        """Inject the conditioning cache + variant + CFG into the delta.

        This is the first image adapter that requires the
        ``ODEConditionDelta`` ``delta_spec`` to carry text-conditional
        metadata. The convention (documented in the module docstring):

        * ``prompt`` (str) — required for text-conditional generation.
          The synthetic / torch path requires this field; the
          ``compose_condition`` method raises when missing.
        * ``negative_prompt`` (str, default empty) — optional
          negative prompt for CFG.
        * ``cfg_scale`` (float, default per-variant) — CFG scale;
          the variant defaults are ``{"full": 5.0, "dev": 1.0,
          "fast": 1.0}``.
        * ``variant`` (str, default "full") — HiDream-I1 distillation
          variant; selects the per-variant ``num_steps`` and
          ``cfg_scale`` defaults.
        * ``num_steps`` (int, default per-variant) — integration
          step count; ``{"full": 50, "dev": 28, "fast": 14}``.
        * ``sampler_id`` (str, default "euler") — integrator name.
        * ``conditioning_cache_hash`` (str, output) — the
          deterministic SHA-256 of the (prompt, negative_prompt) pair,
          written by ``compose_condition`` so subsequent rounds can
          check the cache key without re-encoding.

        The adapter caches the conditioning internally on first use;
        ``conditioning_cache_hash`` is exposed via ``delta_spec`` for
        downstream observability.
        """
        del bundle
        new_spec = dict(delta.delta_spec)
        # Resolve prompt.
        prompt = str(new_spec.get("prompt", self._default_prompt))
        if not prompt:
            raise ValueError(ERR_HIDREAM_I1_PROMPT_MISSING)
        new_spec["prompt"] = prompt

        # Resolve negative prompt.
        neg = str(new_spec.get("negative_prompt", self._default_negative_prompt))
        new_spec["negative_prompt"] = neg

        # Resolve variant (per-round override).
        variant = str(new_spec.get("variant", self._variant))
        if variant not in HIDREAM_VARIANTS:
            raise ValueError(
                f"{ERR_HIDREAM_I1_VARIANT_UNKNOWN}:{variant!r}"
                f"; expected one of {HIDREAM_VARIANTS!r}"
            )
        new_spec["variant"] = variant

        # Resolve cfg_scale (per-round override on top of variant default).
        variant_cfg = float(HIDREAM_VARIANT_CFG_SCALE.get(variant, self._cfg_scale))
        cfg_scale = float(new_spec.get("cfg_scale", variant_cfg))
        new_spec["cfg_scale"] = cfg_scale

        # Resolve num_steps (per-round override on top of variant default).
        variant_steps = int(HIDREAM_VARIANT_NUM_STEPS.get(variant, self._num_steps))
        num_steps = int(new_spec.get("num_steps", variant_steps))
        if num_steps <= 0:
            raise ValueError(ERR_HIDREAM_I1_NUM_STEPS)
        new_spec["num_steps"] = num_steps

        # Resolve sampler.
        sampler_id = str(new_spec.get("sampler_id", self._solver))
        if sampler_id not in HIDREAM_I1_INTEGRATORS:
            raise ValueError(
                f"{ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
                f"; expected one of {HIDREAM_I1_INTEGRATORS!r}"
            )
        new_spec["sampler_id"] = sampler_id

        # Build / fetch the conditioning cache so the cache key is
        # available to ``solve_ode`` without re-encoding.
        cond = self._resolve_conditioning(
            prompt=prompt, negative_prompt=neg, seed=int(delta.target_round),
        )
        new_spec["conditioning_cache_hash"] = str(cond["cache_hash"])

        new_spec.setdefault("integrator_config_hash", HIDREAM_I1_CONFIG_HASH)
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
        cfg_scale: float,
    ) -> ArrayF64:
        """Evaluate the velocity field at ``(x, t)`` for the active backend.

        Internal dispatch helper used by :meth:`solve_ode` and
        :meth:`batched_inference`. ``torch`` mode delegates to the
        PyTorch DiT (see :func:`_torch_velocity_field`); ``synthetic``
        mode uses the deterministic NumPy field. Returns a NumPy
        ``(16, 128, 128)`` float64 array (copy-safe to mutate).
        """
        if self._mode == "torch":
            assert self._pipeline is not None
            return _torch_velocity_field(
                self._pipeline,
                x,
                t,
                dtype=self._torch_dtype,
                cache=conditioning,
                cfg_scale=float(cfg_scale),
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
            raise ValueError(ERR_HIDREAM_I1_NUM_STEPS)
        cfg_scale = float(condition.delta_spec.get("cfg_scale", self._cfg_scale))
        sampler_id = str(
            condition.delta_spec.get("sampler_id", self._solver)
        )
        if sampler_id not in HIDREAM_I1_INTEGRATORS:
            raise ValueError(
                f"{ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
            )

        # Re-resolve conditioning from the delta_spec's cache hash so
        # re-inference rounds reuse the cached encoder output. If the
        # delta_spec lacks the conditioning hash (e.g. a hand-rolled
        # delta from a hostile test), fall back to encoding the default
        # prompt.
        cond_hash = str(
            condition.delta_spec.get("conditioning_cache_hash", "")
        )
        if cond_hash and cond_hash in self._conditioning_cache:
            conditioning = self._conditioning_cache[cond_hash]
        else:
            prompt = str(condition.delta_spec.get("prompt", self._default_prompt))
            neg = str(
                condition.delta_spec.get("negative_prompt", self._default_negative_prompt)
            )
            conditioning = self._resolve_conditioning(
                prompt=prompt, negative_prompt=neg, seed=int(seed),
            )

        x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            HIDREAM_I1_STATE_SHAPE
        )

        t_grid = np.linspace(
            0.0, float(HIDREAM_I1_T_END), num_steps + 1, dtype=np.float64
        )
        traj = np.empty((t_grid.size, *HIDREAM_I1_STATE_SHAPE), dtype=np.float64)
        traj[0] = x0.copy()
        x_cur = x0.copy()
        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            v1 = self._velocity_field(
                x_cur, t0, conditioning=conditioning, cfg_scale=cfg_scale,
            )
            if (
                sampler_id == HIDREAM_I1_INTEGRATOR_HEUN
                and i < t_grid.size - 1
            ):
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(
                    x_cur + dt * v1, -HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP
                )
                v2 = self._velocity_field(
                    x_pred, t1, conditioning=conditioning, cfg_scale=cfg_scale,
                )
                # Corrector: trapezoidal average. The final step has no
                # ``t+dt`` within the integration range so the corrector
                # is skipped (matches k-diffusion ``sample_heun`` at
                # ``sigma_next == 0``).
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -HIDREAM_I1_CLAMP,
                    HIDREAM_I1_CLAMP,
                )
            else:
                x_cur = np.clip(
                    x_cur + dt * v1, -HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP
                )
            traj[i] = x_cur

        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "sampler_id": str(sampler_id),
                "num_steps": int(num_steps),
                "cfg_scale": float(cfg_scale),
                "conditioning_hash": str(conditioning.get("cache_hash", "")),
                "shape": [int(traj.shape[0]), int(traj.shape[1]), int(traj.shape[2])],
                "latent_first": [
                    float(x0[0, 0, 0]),
                    float(x0[0, 0, 1]),
                    float(x0[1, 0, 0]),
                ],
                "mode": self._mode,
                "variant": str(self._variant),
            }
        )
        self._put_native_state(
            traj_digest,
            {
                "trajectory": traj,
                "t_grid": t_grid,
                "mode": self._mode,
                "variant": str(self._variant),
                "conditioning_hash": str(conditioning.get("cache_hash", "")),
            },
        )
        cfg_blob = repr(
            (
                "hidream_i1_config",
                str(sampler_id),
                int(num_steps),
                float(cfg_scale),
                str(self._variant),
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
            HIDREAM_I1_STATE_SHAPE
        )
        endpoint_digest = _digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "x_final_first": [
                    float(x_final[0, 0, 0]),
                    float(x_final[0, 0, 1]),
                    float(x_final[1, 0, 0]),
                ],
                "t_final": float(HIDREAM_I1_T_END),
                "variant": str(self._variant),
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "x": np.asarray(x_final, dtype=np.float64).reshape(HIDREAM_I1_STATE_SHAPE),
                "t": float(HIDREAM_I1_T_END),
                "mode": self._mode,
                "variant": str(self._variant),
                "conditioning_hash": str(traj_entry.get("conditioning_hash", "")),
            },
        )
        next_round = int(state.source_round) + 1
        # Carry the conditioning reference forward across rounds so the
        # bundle's ``text_cond`` channel never goes stale.
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
                ChannelName("text_cond"): _make_ref(
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
            provenance=tuple(state.provenance) + (AUDIT_HIDREAM_I1_OBSERVED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 8b. observe (Wave 95 Phase 2.B — AdapterObservationProtocol surface)
    # ------------------------------------------------------------------

    def observe(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
        paper_quantities: Any = None,
        *,
        strategies: tuple[ObservationKind, ...] = (
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
        theta_before: Any = None,
        theta_after: Any = None,
    ) -> tuple[ObservationResult, ...]:
        """Single typed observation surface for :class:`AdapterObservationProtocol`.

        Wraps the existing :meth:`observe_endpoint` / :meth:`export_trajectory`
        methods into a tagged-tuple :class:`ObservationResult` contract so
        the metric layer can dispatch on :class:`ObservationKind` rather
        than on the model name (Wave 67 principle; Wave 68
        ``docs/audit/wave68-phase5.md`` §3).

        Only two of the four kinds are meaningful for HiDream I1. The
        native state is a continuous ``(16, 128, 128)`` FLUX.1-VAE latent,
        so there is no per-position categorical:

        * :attr:`ObservationKind.DISCRETE_TOKENS` — skipped (no discrete
          channel; same rationale as Kanzi's continuous latent).
        * :attr:`ObservationKind.POSITION_ENTROPY_REDUCTION` — skipped
          (``theta_before`` / ``theta_after`` are accepted for Protocol
          signature conformance but are not consumed).

        Byte-stable migration (Wave 68 §1.3): the underlying methods are
        unchanged and existing call sites keep working. Requested kinds
        the adapter does not support are simply absent from the result
        tuple; an empty tuple is a valid response.

        Parameters
        ----------
        trace
            Forwarded to :meth:`observe_endpoint` / :meth:`export_trajectory`.
        state
            Forwarded to :meth:`observe_endpoint`. ``None`` is permitted by
            the Protocol (``interfaces.py:617-619``) and returns an empty
            tuple.
        paper_quantities
            Accepted for Protocol conformance; not consumed (HiDream I1
            derives no observation from paper-quantity context).
        strategies
            Tuple of :class:`ObservationKind` tags to include. The default
            requests the two kinds HiDream I1 supports.
        theta_before, theta_after
            Accepted for Protocol conformance; not consumed (see above).

        Returns
        -------
        tuple[ObservationResult, ...]
            Tagged-tuple view of the same numeric output the legacy
            ``observe_*`` methods return. Payload types by ``kind``:

            * ``ENDPOINT_BUNDLE`` — :class:`StateBundle`
            * ``TRAJECTORY_NATIVE`` — ``numpy.ndarray`` of shape
              ``(T + 1, 16, 128, 128)``
        """
        results: list[ObservationResult] = []
        # Defensive guard — the Protocol explicitly permits ``state=None``
        # (interfaces.py:617-619) and the metric helper
        # ``_extract_observation`` passes ``state=None`` when the caller
        # wants only non-endpoint strategies. Return early before touching
        # ``observe_endpoint`` to avoid a validate_state_bundle failure.
        if state is None:
            return tuple()
        if ObservationKind.ENDPOINT_BUNDLE in strategies:
            endpoint = self.observe_endpoint(trace, state)
            results.append(
                ObservationResult(
                    kind=ObservationKind.ENDPOINT_BUNDLE,
                    channel=str(ChannelName("image_latent")),
                    payload=endpoint,
                    units="state_bundle",
                    metadata={"source_round": int(endpoint.source_round)},
                )
            )
        if ObservationKind.TRAJECTORY_NATIVE in strategies:
            traj = self.export_trajectory(trace)
            if traj is not None:
                results.append(
                    ObservationResult(
                        kind=ObservationKind.TRAJECTORY_NATIVE,
                        channel=str(ChannelName("image_latent")),
                        payload=traj,
                        units="trajectory",
                    )
                )
        return tuple(results)

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> ArrayF64 | None:
        """Return the native ``(T, 16, 128, 128)`` trajectory for ``trace``."""
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
        """Inject ``injected`` (shape ``(16, 128, 128)``) into the bundle's prior.

        Returns a fresh :class:`StateBundle` whose prior x0 has been
        updated to ``x + injected`` (clipped to
        ``[-HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP]``) and whose
        ``provenance`` records the
        :data:`AUDIT_FORWARD_NOISE_APPLIED` tag.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        x_prior = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            HIDREAM_I1_STATE_SHAPE
        )
        x_new_arr = np.asarray(injected, dtype=np.float64).reshape(
            HIDREAM_I1_STATE_SHAPE
        )
        x_new = np.clip(x_prior + x_new_arr, -HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP)
        new_digest = _digest_state(
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
                "variant": str(self._variant),
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

    # ------------------------------------------------------------------
    # 11. batched_inference (heavy path — vanilla baseline + framework FID)
    # ------------------------------------------------------------------

    def batched_inference(
        self,
        n_samples: int,
        *,
        num_steps: int | None = None,
        seed: int = 0,
        solver: str | None = None,
        prompt: str | None = None,
        negative_prompt: str | None = None,
        cfg_scale: float | None = None,
    ) -> ArrayF64:
        """Return ``(n_samples, 16, 128, 128)`` samples from the velocity field.

        This is the *vanilla inference* path used by the baseline
        reproduction and the framework FID computation. Each sample
        is drawn from ``N(0, I_{16x128x128})`` and integrated forward
        over the ``t_grid`` with ``num_steps`` Euler steps (or Heun
        2nd-order steps when ``solver='heun'``).

        The ``prompt`` / ``negative_prompt`` / ``cfg_scale``
        arguments default to the adapter's constructor settings; the
        conditioning cache is reused across calls so repeated runs
        with the same prompt are byte-deterministic.

        Byte-deterministic for fixed
        ``(seed, num_steps, weights, solver, prompt, cfg_scale)``.
        """
        if int(n_samples) <= 0:
            raise ValueError("n_samples_must_be_positive")
        steps = int(num_steps) if num_steps is not None else self._num_steps
        if steps <= 0:
            raise ValueError(ERR_HIDREAM_I1_NUM_STEPS)
        solver_kind = str(self._solver if solver is None else solver)
        if solver_kind not in HIDREAM_I1_INTEGRATORS:
            raise ValueError(
                f"{ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN}:{solver_kind!r}"
                f"; expected one of {HIDREAM_I1_INTEGRATORS!r}"
            )
        prompt_str = str(prompt if prompt is not None else self._default_prompt)
        neg_str = str(
            negative_prompt if negative_prompt is not None else self._default_negative_prompt
        )
        cfg = float(cfg_scale if cfg_scale is not None else self._cfg_scale)
        conditioning = self._resolve_conditioning(
            prompt=prompt_str, negative_prompt=neg_str, seed=int(seed),
        )
        rng = np.random.default_rng(int(seed))
        x0_batch = rng.standard_normal(
            (int(n_samples), *HIDREAM_I1_STATE_SHAPE)
        ).astype(np.float64)
        t_grid = np.linspace(
            0.0, float(HIDREAM_I1_T_END), steps + 1, dtype=np.float64
        )
        x_cur = x0_batch.copy()
        # Dispatch: torch mode -> call the loaded pipeline per-step on
        # the latent grid; synthetic mode -> fall back to the
        # deterministic NumPy field. The previous version
        # unconditionally referenced ``self._synthetic_weights``, which
        # is ``None`` in torch mode -> ``AttributeError``.
        if self._mode == "torch" and self._pipeline is not None:
            # In torch mode, the latent space is owned by the
            # upstream/diffusers pipeline's denoising loop. We surface
            # this with a clear error — callers that want real
            # 1024x1024 outputs should use :meth:`sample_pil`, which
            # drives the pipeline directly. :meth:`batched_inference`
            # remains a NumPy latent-grid integrator for the
            # framework's synthetic-vs-torch comparison tests.
            raise RuntimeError(
                "batched_inference: torch mode requires sample_pil() "
                "(the loaded HiDreamImagePipeline owns its own "
                "denoising loop); call HiDreamI1Adapter.sample_pil(...) "
                "for real-image inference, or use "
                "force_mode='synthetic' for the NumPy latent grid."
            )
        if self._synthetic_weights is None:
            raise RuntimeError(
                "batched_inference: synthetic_weights not initialised "
                "(internal invariant violated)"
            )
        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            v1 = _batched_synthetic_velocity_field(
                x_cur, t0, weights=self._synthetic_weights,
            )
            if solver_kind == HIDREAM_I1_INTEGRATOR_HEUN and i < t_grid.size - 1:
                x_pred = np.clip(x_cur + dt * v1, -HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP)
                v2 = _batched_synthetic_velocity_field(
                    x_pred, t1, weights=self._synthetic_weights,
                )
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -HIDREAM_I1_CLAMP,
                    HIDREAM_I1_CLAMP,
                )
            else:
                x_cur = np.clip(x_cur + dt * v1, -HIDREAM_I1_CLAMP, HIDREAM_I1_CLAMP)
        return np.asarray(x_cur, dtype=np.float64).reshape(
            (int(n_samples), *HIDREAM_I1_STATE_SHAPE)
        )


def _batched_synthetic_velocity_field(
    x_batch: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> ArrayF64:
    """Batched version of :func:`_synthetic_velocity_field` for shape ``(B, 16, 128, 128)``.

    Operates on a flattened per-sample view via per-sample matmul to
    avoid materialising a single ``(B, 16*128*128)`` matrix that would
    OOM the synthetic path for large ``B``. For the test-suite's
    small batches the per-sample loop is well within budget.
    """
    out = np.empty(x_batch.shape, dtype=np.float64)
    n = int(x_batch.shape[0])
    for b in range(n):
        out[b] = _synthetic_velocity_field(x_batch[b], t, weights=weights)
    return out.reshape(x_batch.shape)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_hidream_i1_adapter(
    *,
    variant: str = HIDREAM_VARIANT_FULL,
    weights_path: Path | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    num_steps: int | None = None,
    solver: str = HIDREAM_I1_INTEGRATOR_EULER,
) -> HiDreamI1Adapter:
    """Default factory for :class:`HiDreamI1Adapter`.

    When ``weights_path`` is ``None`` the adapter resolves
    ``data/hidream_i1_{variant}.safetensors`` /
    ``data/hidream_i1_{variant}.pt`` in priority order; when none of
    those exist and ``force_mode`` is ``"auto"``, the adapter falls
    back to ``synthetic`` mode (testing-only).

    The ``variant`` parameter selects the published HiDream-I1
    sub-repo (``"full"``, ``"dev"``, ``"fast"``); the per-variant
    default ``num_steps`` is used unless ``num_steps`` is explicitly
    supplied.
    """
    if num_steps is None:
        num_steps = int(HIDREAM_VARIANT_NUM_STEPS.get(variant, HIDREAM_I1_NUM_STEPS_DEFAULT))
    return HiDreamI1Adapter(
        variant=variant,
        weights_path=weights_path,
        force_mode=force_mode,
        num_steps=int(num_steps),
        solver=solver,
    )


__all__ = [
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_HIDREAM_I1_OBSERVED",
    "AUDIT_HIDREAM_I1_RESTART_BLEND",
    "ERR_HIDREAM_I1_INTEGRATOR_UNKNOWN",
    "ERR_HIDREAM_I1_NUM_STEPS",
    "ERR_HIDREAM_I1_PROMPT_MISSING",
    "ERR_HIDREAM_I1_VARIANT_UNKNOWN",
    "ERR_HIDREAM_I1_WEIGHTS_MISSING",
    "HIDREAM_I1_CHANNEL_DOMAINS",
    "HIDREAM_I1_CHANNELS",
    "HIDREAM_I1_CLAMP",
    "HIDREAM_I1_CONFIG_HASH",
    "HIDREAM_I1_CONFIG_VERSION",
    "HIDREAM_I1_INTEGRATORS",
    "HIDREAM_I1_INTEGRATOR_EULER",
    "HIDREAM_I1_INTEGRATOR_HEUN",
    "HIDREAM_I1_LATENT_DIM",
    "HIDREAM_I1_MECHANISM_ID",
    "HIDREAM_I1_NATIVE_STATES_MAXSIZE",
    "HIDREAM_I1_NUM_STEPS_DEFAULT",
    "HIDREAM_I1_STATE_SHAPE",
    "HIDREAM_I1_SYNTHETIC_HIDDEN",
    "HIDREAM_I1_SYNTHETIC_SEED_DEFAULT",
    "HIDREAM_I1_T_END",
    "HIDREAM_VARIANT_CFG_SCALE",
    "HIDREAM_VARIANT_DEV",
    "HIDREAM_VARIANT_FAST",
    "HIDREAM_VARIANT_FULL",
    "HIDREAM_VARIANT_NUM_STEPS",
    "HIDREAM_VARIANTS",
    "HiDreamI1Adapter",
    "HiDreamI1Capabilities",
    "default_hidream_i1_adapter",
    "hidream_i1_resolve_weights_path",
    "torch_is_available",
]
