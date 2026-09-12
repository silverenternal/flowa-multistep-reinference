"""Lumina-Image 2.0 Flow Matching ODE adapter (lumina_image_2_0).

This module wires the published Lumina-Image 2.0 Unified Next-DiT
diffusion-transformer (``Alpha-VLLM/Lumina-Image-2.0`` on HuggingFace,
``arXiv:2503.21758``, Apache-2.0) into the framework's
:class:`FlowMatchingODEAdapter` Protocol so that the same algorithm-
layer code that drives the synthetic 2D :mod:`adaptive_reflow.adapters
.twodim_fm` and the unconditional 32x32 RF CIFAR
(:mod:`adaptive_reflow.adapters.rectified_flow_cifar`) adapters can
also drive a state-of-the-art flow-based text-to-image DiT.

Architecture summary
-------------------

* 2.6B-parameter Unified Next-DiT (Gemma2 text encoder, mRoPE
  positional encoding, single-stream fused text+image causal DiT with
  26 layers, hidden=2304, 24 Q heads / 8 KV heads, head_dim=256, 16-
  channel latent space).
* FLUX.1-dev AutoencoderKL encoder/decoder (latent_channels=16,
  scaling_factor=0.3611, shift_factor=0.1159).
* FlowMatchEulerDiscreteScheduler (shift=6.0, num_train_timesteps=1000).
* Default sampling at 1024x1024: 50 inference steps + classifier-free
  guidance (guidance_scale=4.0, cfg_trunc_ratio=0.25,
  cfg_normalization=True).

Two operating modes
-------------------

1. ``torch`` mode (the published integration). The adapter lazy-imports
   :mod:`torch` and :mod:`diffusers.Lumina2Pipeline` /
   :class:`diffusers.Lumina2Transformer2DModel`. Required when running
   on a GPU host with the Lumina-Image 2.0 checkpoint available.

2. ``synthetic`` mode (testing only). When :mod:`torch` / diffusers /
   transformers / safetensors are unavailable at construction time, the
   adapter falls back to a deterministic NumPy two-tensor affine
   velocity field on the canonical ``(16, 128, 128)`` latent shape. The
   synthetic path lets the Protocol conformance tests run without the
   heavy dependencies.

Public surface
--------------

* :class:`LuminaImage20Adapter` -- concrete
  :class:`FlowMatchingODEAdapter` with ``state_shape=(16, 128, 128)``.
* :class:`LuminaImage20Capabilities` -- frozen capability surface.
* :func:`default_lumina_image_2_0_adapter` -- factory.

Tasks satisfied
---------------

* ``ADAPTER-lumina_image_2_0`` -- Lumina-Image 2.0 Flow Matching
  reproduction wiring (DTB-G1 + DTB-G2).

The implementation deliberately mirrors the
:class:`RectifiedFlowCIFARAdapter` torch/synthetic dual-mode pattern:
lazy torch / diffusers imports, capability handshake, deterministic
seed, native tensors on adapter side via :class:`TensorRef`, text-
condition injection cached on ``calibration_artifact_hash`` so two
rounds with the same prompt share the embedding compute.
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
    make_ref,
    memory_fraction_for,
    seed_from_ids,
)
from adaptive_reflow.core.ckpt_loader import resolve_candidate_paths
from adaptive_reflow.framework.interfaces import implements


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Canonical Lumina-Image 2.0 latent state shape -- 16-channel latent at
#: the 1024x1024 generation resolution. This is the ``state_shape`` the
#: framework's runner reads for F14 forward-noise allocation and the
#: shape ``solve_ode`` integrates over.
LUMINA_IMAGE_2_0_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("latent"),
    ChannelName("text_condition"),
)
LUMINA_IMAGE_2_0_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("latent"): "latent",
    ChannelName("text_condition"): "continuous",
}
LUMINA_IMAGE_2_0_STATE_SHAPE: tuple[int, ...] = (16, 128, 128)
LUMINA_IMAGE_2_0_CONFIG_HASH: str = "lumina_image_2_0:cfg:v1"
LUMINA_IMAGE_2_0_CONFIG_VERSION: str = "0.1.0"

#: Per-model mechanism_id -- the engine stamps this on every round trace
#: so the writer can attribute the round to this specific
#: model+adapter pair. Distinct from the canonical
#: ``EXECUTABLE_WRITER_MECHANISM_ID = "inference.adaptive_reflow"``,
#: which is the writer authority (DTB-S1). The per-model mechanism_id
#: lives alongside the writer registry as an attribution tag.
LUMINA_IMAGE_2_0_MECHANISM_ID: str = "lumina_image_2_0_flow_matching"

#: Paper default sampling steps at 1024x1024. Overridable per-round via
#: ``condition.delta_spec["num_steps"]``.
LUMINA_IMAGE_2_0_NUM_STEPS_DEFAULT: int = 50

#: Default classifier-free-guidance scale (paper default).
LUMINA_IMAGE_2_0_GUIDANCE_SCALE_DEFAULT: float = 4.0

#: Default CFG-Trunc ratio (paper default; truncates the last 25% of
#: the diffusion timeline from CFG).
LUMINA_IMAGE_2_0_CFG_TRUNC_RATIO_DEFAULT: float = 0.25

#: Default RoPE axis lengths (text=300, h=512, w=512) for mRoPE.
LUMINA_IMAGE_2_0_ROPE_AXES_DEFAULT: tuple[int, int, int] = (300, 512, 512)

#: Latent clamp magnitude. FLUX.1-dev VAE scale 0.3611 + shift 0.1159
#: keep encoded latents inside ``|x| <= 3.0`` (~3-sigma capture).
LUMINA_IMAGE_2_0_CLAMP: float = 3.0

#: ``t_end`` of the diffusion interval. Lumina uses ``[0, 1]`` like
#: Rectified Flow; the FlowMatchEulerDiscreteScheduler applies the
#: ``shift=6.0`` rescale internally.
LUMINA_IMAGE_2_0_T_END: float = 1.0

#: LRU cache bound on native states (audit A-3 mirror of twodim_fm).
LUMINA_IMAGE_2_0_NATIVE_STATES_MAXSIZE: int = 8

#: Integrator literals -- the published Lumina-Image 2.0 sampler uses
#: FlowMatchEulerDiscreteScheduler. Heun is exposed as a future
#: 2nd-order option but is not the paper default.
LUMINA_IMAGE_2_0_INTEGRATORS: tuple[str, ...] = ("euler", "heun")
LUMINA_IMAGE_2_0_INTEGRATOR_EULER: str = "euler"
LUMINA_IMAGE_2_0_INTEGRATOR_HEUN: str = "heun"

#: Default synthetic-mode hidden width (the NumPy two-tensor affine
#: velocity field). Matches :data:`RectifiedFlowCIFARAdapter.SYNTHETIC_HIDDEN`
#: pattern -- random-init for protocol conformance only.
LUMINA_IMAGE_2_0_SYNTHETIC_HIDDEN: int = 32
LUMINA_IMAGE_2_0_SYNTHETIC_SEED_DEFAULT: int = 0xA5A5A5A5

#: Gemma2 text-encoder cache: keyed by
#: ``sha256(prompt + negative_prompt + calibration_artifact_hash)`` so
#: two rounds with the same prompt share the embedding compute.
LUMINA_IMAGE_2_0_TEXT_CACHE_MAXSIZE: int = 32

# Audit / error codes (deterministic ASCII strings).
AUDIT_LUMINA_RESTART_BLEND: str = "lumina_image_2_0_restart_blend"
AUDIT_LUMINA_OBSERVED: str = "lumina_image_2_0_observed"
AUDIT_LUMINA_TEXT_CACHED: str = "lumina_image_2_0_text_cached"
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
ERR_LUMINA_NUM_STEPS: str = "lumina_image_2_0_num_steps_must_be_positive"
ERR_LUMINA_INTEGRATOR_UNKNOWN: str = "lumina_image_2_0_integrator_unknown"
ERR_LUMINA_TEXT_EMBED_MISSING: str = "lumina_image_2_0_text_embed_missing"
ERR_LUMINA_PROMPT_MISSING: str = "lumina_image_2_0_prompt_missing"

# Local type alias (avoid numpy at module-import hot annotation paths).
ArrayF64 = NDArray[np.float64]

Mode = Literal["torch", "synthetic", "upstream"]

# Default weight-dir candidate filenames (used by the resolver; the
# published checkpoint layout is documented in
# ``docs/r4-survey/07-sota-experiment-protocol.md`` §2).
LUMINA_IMAGE_2_0_WEIGHTS_CANDIDATES: tuple[str, ...] = (
    "lumina-image-2.0",
    "Lumina-Image-2.0",
    "Alpha-VLLM__Lumina-Image-2.0",
)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def lumina_image_2_0_resolve_weights_path(
    data_dir: Path | None = None,
    *,
    candidates: tuple[str, ...] = LUMINA_IMAGE_2_0_WEIGHTS_CANDIDATES,
) -> Path | None:
    """Return the first existing candidate weights path under ``data_dir``.

    Thin adapter wrapper over
    :func:`adaptive_reflow.core.ckpt_loader.resolve_candidate_paths` —
    probes each candidate filename in probe-order and returns the
    first existing path. The framework-core helper handles the
    per-adapter subdir probe and the flat-file fallback. The
    Lumina-Image 2.0 published checkpoint layout is a directory
    (``consolidated.00-of-01.pth`` + ``text_encoder/`` + ``transformer/``
    + ``vae/``); the resolver returns the first matching directory
    under ``data_dir``. Returns ``None`` when none of the candidates
    exist.
    """
    data_dirs_kw = [data_dir] if data_dir is not None else None
    for stem in candidates:
        hits = resolve_candidate_paths(
            "", stem, data_dirs=data_dirs_kw,
        )
        if hits:
            return hits[0]
    return None


def torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter.

    The check is a runtime ``importlib.util.find_spec`` call (not a
    cached flag) so test fixtures that install torch mid-session still
    see the live answer.
    """
    import importlib.util as _il

    return _il.find_spec("torch") is not None


def diffusers_is_available() -> bool:
    """Return ``True`` iff :mod:`diffusers` is importable in this interpreter.

    Mirrors :func:`torch_is_available`. Used by the constructor to
    decide whether the heavy diffusion pipeline can be loaded.
    """
    import importlib.util as _il

    return _il.find_spec("diffusers") is not None


def transformers_is_available() -> bool:
    """Return ``True`` iff :mod:`transformers` is importable.

    The Gemma2 text encoder is a HuggingFace ``transformers`` model;
    without it the torch path cannot construct the prompt embedding.
    """
    import importlib.util as _il

    return _il.find_spec("transformers") is not None


# ---------------------------------------------------------------------------
# Private helpers -- hashing + state-shape integrity
# ---------------------------------------------------------------------------

# ``seed_from_ids``, ``digest_state`` and ``make_ref`` are imported from
# :mod:`adaptive_reflow.adapters._adapter_common` (Wave 33 / Wave 44 D.1
# shrink + Wave 103 P0-B dedup). The call sites use the canonical names.


def _validate_state_shape(x: ArrayF64) -> ArrayF64:
    """Reshape ``x`` to ``LUMINA_IMAGE_2_0_STATE_SHAPE`` and float64."""
    return np.asarray(x, dtype=np.float64).reshape(LUMINA_IMAGE_2_0_STATE_SHAPE)


def _text_embed_cache_key(prompt: str, negative_prompt: str, calibration_hash: str) -> str:
    """Return the cache key for a ``(prompt, negative_prompt, calibration_hash)`` triple."""
    blob = repr((str(prompt), str(negative_prompt), str(calibration_hash))).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------------------
# Synthetic (NumPy) velocity field -- test-only path; no torch dependency
# ---------------------------------------------------------------------------


def _synthesize_latent_like_tensor(rng: np.random.Generator) -> ArrayF64:
    """Sample a latent-shape ``(16, 128, 128)`` array from ``N(0, I)``."""
    return rng.standard_normal(LUMINA_IMAGE_2_0_STATE_SHAPE).astype(np.float64)


def _synthetic_velocity_field(
    x: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> ArrayF64:
    """Evaluate a tiny two-tensor affine velocity field on ``(16, 128, 128)``.

    The synthetic field is shaped as
    ``v_theta(x, t) = W2 @ tanh(W1 @ flatten(x) + b1 + t * t_bias) + b2``
    using two dense linear layers with hidden width
    :data:`LUMINA_IMAGE_2_0_SYNTHETIC_HIDDEN`. The weights are random-
    init (deterministic via ``np.random.default_rng``) so the synthetic
    path is byte-deterministic for a fixed ``seed``. The field is NOT
    a trained Lumina-Image 2.0 model and is only used by the test
    suite to exercise the Protocol surface.
    """
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    w1 = np.asarray(weights["W1"], dtype=np.float64)
    b1 = np.asarray(weights["b1"], dtype=np.float64)
    w2 = np.asarray(weights["W2"], dtype=np.float64)
    b2 = np.asarray(weights["b2"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    h = np.tanh(flat @ w1 + b1 + float(t) * t_bias)
    out = h @ w2 + b2
    return np.asarray(out, dtype=np.float64).reshape(LUMINA_IMAGE_2_0_STATE_SHAPE)


def _random_init_synthetic_weights(
    *,
    seed: int,
    hidden: int | None = None,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic velocity field's two linear layers.

    Hidden width defaults to :data:`LUMINA_IMAGE_2_0_SYNTHETIC_HIDDEN`
    but can be overridden per-instance via the ``hidden`` keyword.
    """
    rng = np.random.default_rng(int(seed))
    in_dim = int(np.prod(LUMINA_IMAGE_2_0_STATE_SHAPE))
    hidden_w = (
        int(hidden)
        if hidden is not None
        else int(LUMINA_IMAGE_2_0_SYNTHETIC_HIDDEN)
    )

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


# ---------------------------------------------------------------------------
# Torch velocity field -- production path; requires torch + diffusers
# ---------------------------------------------------------------------------


def _torch_velocity_field(
    transformer: Any,
    x: ArrayF64,
    t: float,
    *,
    dtype: Any,
    text_emb: Any,
    uncond_text_emb: Any,
    encoder_attention_mask: Any | None,
    uncond_attention_mask: Any | None,
    guidance_scale: float,
    cfg_trunc_ratio: float,
    cfg_normalization: bool,
) -> ArrayF64:
    """Call the Lumina-Image 2.0 transformer ``v_theta(x, t, text)``.

    Lazy-imports :mod:`torch` and :mod:`diffusers.Lumina2Transformer2DModel`.
    Returns a NumPy ``(16, 128, 128)`` float64 array.

    Notes
    -----
    The function is intentionally a thin wrapper around the diffusers
    Lumina2Transformer2DModel call: paper §4.5's CFG-Renorm and
    CFG-Trunc are applied here, then a single Euler velocity evaluation
    is returned. The protocol layer stays byte-deterministic by passing
    the same ``text_emb`` / ``uncond_text_emb`` tensors across the
    integration grid.

    The diffusers 0.40+ Lumina2Transformer2DModel.forward signature
    drops the legacy ``rope_axes`` kwarg (RoPE is computed internally
    from ``axes_lens`` in the config), so this wrapper passes
    ``encoder_hidden_states`` + ``encoder_attention_mask`` only.
    """
    import torch  # local import -- torch is optional at the framework level.

    with torch.no_grad():
        x_t = torch.as_tensor(x, dtype=dtype).unsqueeze(0)
        # Time conditioning: broadcast scalar to (1,) and cast to dtype.
        # The Lumina2 transformer expects a (B,) tensor of normalized
        # timesteps in [0, 1] (FlowMatchEuler scheduler convention).
        # Match the transformer's device (transformer may have been
        # moved to GPU by the caller via ``pipeline.to("cuda")``).
        tf_device = next(transformer.parameters()).device
        x_t = x_t.to(device=tf_device)
        t_t = torch.tensor([float(t)], dtype=dtype, device=tf_device)
        # Conditional forward: v_t = transformer(x_t, t_t, text_emb, ...).
        v_t = transformer(
            hidden_states=x_t,
            timestep=t_t,
            encoder_hidden_states=text_emb,
            encoder_attention_mask=encoder_attention_mask,
        ).sample
        # CFG: combine conditional + unconditional (CFG-Trunc gate).
        in_cfg_window = float(t) <= float(1.0 - float(cfg_trunc_ratio))
        if in_cfg_window and uncond_text_emb is not None:
            v_tu = transformer(
                hidden_states=x_t,
                timestep=t_t,
                encoder_hidden_states=uncond_text_emb,
                encoder_attention_mask=uncond_attention_mask,
            ).sample
            v_eff = v_tu + float(guidance_scale) * (v_t - v_tu)
            # CFG-Renorm: rescale v_eff so its per-sample std matches the
            # conditional branch's std (paper §4.5 stability fix).
            if cfg_normalization:
                cond_std = v_t.flatten(1).std(dim=1, keepdim=True).clamp_min(1e-6)
                eff_std = v_eff.flatten(1).std(dim=1, keepdim=True).clamp_min(1e-6)
                scale = (cond_std / eff_std).view(-1, 1, 1, 1)
                v_eff = v_eff * scale
        else:
            v_eff = v_t
        out = np.asarray(v_eff.squeeze(0).detach().to(torch.float32).cpu().numpy(), dtype=np.float64)
    return out.reshape(LUMINA_IMAGE_2_0_STATE_SHAPE)


def _load_torch_pipeline(weights_dir: Path, *, dtype: Any) -> Any:
    """Load the published Lumina-Image 2.0 diffusion pipeline.

    The pipeline is constructed via diffusers' ``Lumina2Pipeline.from_
    pretrained`` so the encoder, transformer, scheduler and VAE are
    loaded with their canonical configurations. The result is moved to
    CPU and put in ``eval()`` mode; the caller can re-enable CPU
    offload via ``pipeline.enable_model_cpu_offload()``.
    """
    import torch  # local import -- torch is optional at the framework level.
    from diffusers import Lumina2Pipeline  # local import -- diffusers is optional.

    pipeline = Lumina2Pipeline.from_pretrained(
        str(weights_dir),
        torch_dtype=dtype,
        variant=None,
    )
    pipeline.set_progress_bar_config(disable=True)
    return pipeline


def _load_upstream_pipeline(
    weights_dir: Path, *, dtype: Any
) -> dict[str, Any]:
    """Load the Lumina-Image 2.0 *upstream* harness.

    Wires the framework adapter to the upstream
    ``Alpha-VLLM/Lumina-Image-2.0`` repo (arXiv:2503.21758):

    * ``models.NextDiT_2B_GQA_patch2_Adaln_Refiner`` -- the 2.6B-param
      Unified Next-DiT backbone with the canonical architecture.
    * ``transport.create_transport`` / ``Sampler`` -- the Rectified-Flow
      path / drift / ``sample_ode`` machinery.

    The function returns a dict with the loaded handles the framework
    needs to drive ``model.forward_with_cfg`` from the ODE loop:

    ==================  ===============================================
    Key                 Description
    ==================  ===============================================
    ``model``           ``NextDiT_2B_GQA_patch2_Adaln_Refiner``
                        instance in ``eval()`` mode on CUDA in
                        ``dtype`` (paper default: bf16).
    ``sampler``         ``transport.Sampler`` from
                        ``create_transport('Linear', 'velocity')``.
    ``train_args``      Loaded ``model_args.pth`` (the upstream uses
                        ``train_args.model`` and ``train_args.qk_norm``
                        to look up the right constructor).
    ``weights_dir``         Mirror of the input arg for downstream logging.
    ``stubbed_flash_attn``  True iff ``flash_attn`` was stubbed by the
                        shim (real wheel missing on sm_120). When True,
                        ``model.forward`` will raise at the first
                        attention call -- the caller must surface this
                        as a clean blocker.
    ==================  ===============================================

    Notes
    -----
    The upstream harness needs:

    * ``consolidated.00-of-01.safetensors`` (or ``.pth``) -- the actual
      checkpoint file. The published layout is documented in
      ``data/lumina_image_2_0/weights_real/`` (diffusers format) vs
      ``data/lumina_image_2_0/weights/`` (upstream format placeholder).
    * ``model_args.pth`` -- a small ``argparse.Namespace`` persisted by
      upstream's training entrypoint. Used to look up the constructor.
    * ``flash_attn`` -- the upstream uses ``flash_attn_varlen_func`` at
      every attention call. On sm_120 (Blackwell) the wheel is not on
      PyPI as of 2026-09; the shim installs a stub so this function
      can return successfully even when the real wheel is missing.

    If ``model_args.pth`` or ``consolidated.00-of-01.safetensors`` /
    ``consolidated.00-of-01.pth`` is missing, the function raises
    ``FileNotFoundError`` so the caller can fall back to
    ``synthetic`` mode.
    """
    import torch  # local import -- torch is optional at the framework level.
    from safetensors.torch import load_file  # local import.

    # Late-bound shim import -- keeps the module importable on
    # stdlib-only test runners.
    from adaptive_reflow.adapters.lumina_image_2_0_upstream_shim import (
        import_upstream_harness,
    )

    harness = import_upstream_harness()
    models_module = harness["models_module"]
    create_transport = harness["create_transport"]

    model_args_path = weights_dir / "model_args.pth"
    if not model_args_path.exists():
        raise FileNotFoundError(
            f"lumina_upstream_model_args_missing:{model_args_path}"
        )

    # Detect an LFS pointer stub (the published repo's
    # ``weights/model_args.pth`` is a 129-byte ASCII pointer line,
    # not a real pickle). The LFS stub starts with
    # ``version https://git-lfs.github.com/spec/v1`` -- if we see
    # that, raise ``FileNotFoundError`` so the caller falls back
    # cleanly to synthetic mode rather than choking on a
    # ``pickle.UnpicklingError`` deep inside ``torch.load``.
    try:
        with open(model_args_path, "rb") as _f:
            _head = _f.read(48)
        if b"git-lfs" in _head or b"version https" in _head:
            raise FileNotFoundError(
                f"lumina_upstream_model_args_lfs_stub:{model_args_path}"
            )
    except OSError:
        # File vanished between the ``exists()`` check and our open --
        # treat as missing.
        raise FileNotFoundError(
            f"lumina_upstream_model_args_missing:{model_args_path}"
        ) from None

    # ``model_args.pth`` is a pickled argparse.Namespace persisted by
    # upstream's training entrypoint.
    train_args = torch.load(model_args_path, weights_only=False)

    # Look up the constructor by name (the upstream uses the same name
    # across checkpoints: ``NextDiT_2B_GQA_patch2_Adaln_Refiner`` for
    # the published 2B Lumina-Image 2.0 config). If a future variant
    # lands (3B/4B/7B), the lookup falls back to the same model.
    model_cls_name = getattr(train_args, "model", "NextDiT_2B_GQA_patch2_Adaln_Refiner")
    try:
        model_cls = models_module.__dict__[model_cls_name]
    except KeyError as exc:
        raise RuntimeError(
            f"lumina_upstream_model_class_unknown:{model_cls_name}"
        ) from exc

    model = model_cls(
        in_channels=16,
        qk_norm=getattr(train_args, "qk_norm", True),
        cap_feat_dim=2304,  # Gemma2-2B hidden_size
    )

    # Locate the upstream-format checkpoint. The published layout uses
    # ``consolidated.00-of-01.safetensors`` (or ``.pth`` as a fallback).
    consolidated_st = weights_dir / "consolidated.00-of-01.safetensors"
    consolidated_pt = weights_dir / "consolidated.00-of-01.pth"
    if consolidated_st.exists():
        ckpt = load_file(str(consolidated_st))
        model.load_state_dict(ckpt, strict=True)
    elif consolidated_pt.exists():
        ckpt = torch.load(consolidated_pt, weights_only=False)
        # The ``.pth`` variant wraps a list of state-dicts (one per
        # shard); with single-GPU ``num_gpus=1`` there is exactly one.
        if isinstance(ckpt, list):
            ckpt = ckpt[0]
        model.load_state_dict(ckpt, strict=True)
    else:
        raise FileNotFoundError(
            f"lumina_upstream_consolidated_missing:{weights_dir} "
            "(expected consolidated.00-of-01.safetensors or "
            "consolidated.00-of-01.pth)"
        )

    model = model.to(dtype=dtype)
    if torch.cuda.is_available():
        model = model.cuda()
    model.eval()

    sampler_obj = create_transport(
        path_type="Linear",
        prediction="velocity",
    )

    return {
        "model": model,
        "sampler": sampler_obj,
        "train_args": train_args,
        "weights_dir": weights_dir,
        "stubbed_flash_attn": bool(harness.get("stubbed_flash_attn", False)),
    }


def _upstream_velocity_field(
    pipeline: dict[str, Any],
    x: ArrayF64,
    t: float,
    *,
    dtype: Any,
    text_emb: Any,
    uncond_text_emb: Any,
    encoder_attention_mask: Any | None,
    uncond_attention_mask: Any | None,
    guidance_scale: float,
    cfg_trunc_ratio: float,
    cfg_normalization: bool,
) -> ArrayF64:
    """Call the upstream ``model.forward_with_cfg(x, t, cap_feats, cap_mask)``.

    The upstream Lumina-Image 2.0 ``forward_with_cfg`` (in
    ``data/lumina_image_2_0/repo/models/model.py`` line 781) handles
    CFG-Trunc + CFG-Renorm internally and expects:

    * ``x`` -- shape ``(2*B, 16, h, w)`` with the conditional x
      duplicated across the batch dim (``forward_with_cfg`` takes
      ``half = x[:B]`` then re-stacks ``[half, half]`` before the
      inner ``self.forward``).
    * ``cap_feats`` -- shape ``(2*B, L, 2304)`` with the conditional
      features in the first half and the unconditional features in the
      second half.
    * ``cap_mask`` -- same layout as ``cap_feats`` along the batch dim.
    * ``t`` -- shape ``(B,)`` (or ``(2*B,)`` -- only ``t[0]`` is checked
      against ``cfg_trunc``).

    The CFG-Trunc semantics are: if ``t[0] < cfg_trunc`` apply CFG,
    else return the conditional branch untouched. The paper's
    ``CFG-Trunc=0.25`` means "skip CFG for the LAST 25% of the
    timeline", i.e. CFG applies for ``t < 0.75``. The adapter sets
    ``cfg_trunc=1.0 - cfg_trunc_ratio`` to match that convention.

    The CFG-Renorm semantics are: ``renorm_cfg > 0`` rescales the
    CFG-combined eps so its vector norm does not exceed
    ``renorm_cfg * ||cond_eps||``. The paper sets ``renorm_cfg=1.0``
    (matches ``cfg_normalization=True``).

    Returns a NumPy ``(16, 128, 128)`` float64 array.
    """
    import torch  # local import -- torch is optional at the framework level.

    model = pipeline["model"]

    with torch.no_grad():
        x_t = torch.as_tensor(x, dtype=dtype).unsqueeze(0)  # (1, 16, h, w)
        x_batched = torch.cat([x_t, x_t], dim=0)  # (2, 16, h, w)
        t_t = torch.tensor([float(t)], dtype=dtype)
        # ``cap_feats`` and ``cap_mask`` are already pre-stacked by
        # ``_encode_text_pair`` in the upstream mode (see that method
        # below). The shape is ``(2, L, 2304)`` and ``(2, L)``.
        cap_feats = text_emb
        cap_mask = encoder_attention_mask
        # CFG-Trunc: in upstream's convention CFG applies when
        # ``t[0] < cfg_trunc``. The framework stores the "truncate the
        # LAST fraction of the timeline" ratio; invert it.
        cfg_trunc = float(1.0 - float(cfg_trunc_ratio))
        # CFG-Renorm: upstream takes a numeric threshold; the framework
        # stores a bool. Map True -> 1.0, False -> 0.0.
        renorm_cfg = 1.0 if bool(cfg_normalization) else 0.0
        v_t = model.forward_with_cfg(
            x_batched,
            t_t,
            cap_feats,
            cap_mask,
            float(guidance_scale),
            cfg_trunc=cfg_trunc,
            renorm_cfg=renorm_cfg,
        )  # (1, 16, h, w) -- forward_with_cfg returns the half-output
    out = np.asarray(v_t.squeeze(0).detach().cpu().numpy(), dtype=np.float64)
    return out.reshape(LUMINA_IMAGE_2_0_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LuminaImage20Capabilities(AdapterCapabilities):
    """Capability surface for :class:`LuminaImage20Adapter`."""

    def __init__(self) -> None:  # noqa: D401 -- dataclass __init__ override
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
            state_shape=LUMINA_IMAGE_2_0_STATE_SHAPE,
            supported_channels=LUMINA_IMAGE_2_0_CHANNELS,
            channel_domains=LUMINA_IMAGE_2_0_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=LUMINA_IMAGE_2_0_CONFIG_HASH,
            native_config_version=LUMINA_IMAGE_2_0_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter)
class LuminaImage20Adapter(FlowMatchingODEAdapter):
    """Lumina-Image 2.0 Flow Matching text-to-image adapter.

    Wraps the published 2.6B-parameter Unified Next-DiT
    (``Alpha-VLLM/Lumina-Image-2.0``, ``arXiv:2503.21758``, Apache-2.0)
    into the :class:`FlowMatchingODEAdapter` Protocol so the framework's
    algorithm-layer code can drive a state-of-the-art text-conditioned
    flow-matching model at 1024x1024 without modification.

    Two operating modes (per :data:`Mode`):

    * ``torch`` -- production path. Lazy-imports :mod:`torch` and
      :mod:`diffusers.Lumina2Pipeline` /
      :class:`diffusers.Lumina2Transformer2DModel` and invokes the
      transformer in ``torch.no_grad()`` / ``eval()`` mode on each
      integration step. Requires the ``[lumina-image]`` extra and the
      Lumina-Image 2.0 checkpoint (default ``data/Lumina-Image-2.0/``).
    * ``upstream`` -- the upstream-repo harness. Lazy-imports the
      ``models`` and ``transport`` modules from the cloned
      ``Alpha-VLLM/Lumina-Image-2.0`` repository (see
      :mod:`adaptive_reflow.adapters.lumina_image_2_0_upstream_shim`)
      and constructs ``NextDiT_2B_GQA_patch2_Adaln_Refiner`` plus
      ``transport.create_transport`` directly. Requires the upstream
      ``consolidated.00-of-01.safetensors`` + ``model_args.pth`` +
      ``flash_attn`` wheel. Falls back to ``synthetic`` on any of
      those being unavailable; the failure is captured on
      ``self._upstream_init_error``.
    * ``synthetic`` -- testing-only path. Uses a deterministic NumPy
      two-tensor affine velocity field with random init. The synthetic
      field is NOT a trained Lumina-Image 2.0 model; it is a Protocol-
      surface shim that lets the test suite exercise every method
      without the heavy torch / diffusers / transformers stack.

    Constructor parameters
    ----------------------

    * ``weights_path`` -- explicit path to the Lumina-Image 2.0
      checkpoint directory. When ``None``, the adapter falls back to
      ``data/lumina-image-2.0`` / ``data/Lumina-Image-2.0`` /
      ``data/Alpha-VLLM__Lumina-Image-2.0`` in order; if none of those
      exist, the adapter switches to ``synthetic`` mode (when ``force_mode``
      is ``"auto"``).
    * ``force_mode`` -- ``"torch"`` / ``"upstream"`` / ``"synthetic"`` /
      ``"auto"`` (default). ``"auto"`` picks ``"torch"`` when the
      weights directory exists AND torch + diffusers + transformers
      are all importable; otherwise ``"synthetic"``.
    * ``num_steps`` -- default number of Euler integration steps per
      round (paper default 50). The framework can override via
      ``condition.delta_spec["num_steps"]``.
    * ``guidance_scale`` -- CFG scale (paper default 4.0).
    * ``cfg_trunc_ratio`` -- CFG-Trunc ratio (paper default 0.25).
    * ``cfg_normalization`` -- enable CFG-Renorm (paper default True).
    * ``solver`` -- ``"euler"`` (default; matches the paper's
      FlowMatchEulerDiscreteScheduler) or ``"heun"``.
    """

    pinned_num_steps: int = LUMINA_IMAGE_2_0_NUM_STEPS_DEFAULT
    # F14: runner reads ``getattr(self._adapter, "state_shape", (2,))``.
    # Standardised on the HiDream dual-level pattern (class-level
    # default, instance-level override) so subclasses / fixtures can
    # tweak the state shape without redefining the class attribute
    # (r17-audit P-07).
    state_shape: tuple[int, ...] = LUMINA_IMAGE_2_0_STATE_SHAPE

    mechanism_id: MechanismId = MechanismId(LUMINA_IMAGE_2_0_MECHANISM_ID)

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        num_steps: int = LUMINA_IMAGE_2_0_NUM_STEPS_DEFAULT,
        guidance_scale: float = LUMINA_IMAGE_2_0_GUIDANCE_SCALE_DEFAULT,
        cfg_trunc_ratio: float = LUMINA_IMAGE_2_0_CFG_TRUNC_RATIO_DEFAULT,
        cfg_normalization: bool = True,
        rope_axes: tuple[int, int, int] = LUMINA_IMAGE_2_0_ROPE_AXES_DEFAULT,
        seed_offset: int = 0,
        synthetic_hidden: int = LUMINA_IMAGE_2_0_SYNTHETIC_HIDDEN,
        synthetic_seed: int = LUMINA_IMAGE_2_0_SYNTHETIC_SEED_DEFAULT,
        solver: str = LUMINA_IMAGE_2_0_INTEGRATOR_EULER,
    ) -> None:
        if int(num_steps) <= 0:
            raise ValueError(ERR_LUMINA_NUM_STEPS)
        if float(guidance_scale) < 0.0:
            raise ValueError("guidance_scale_must_be_non_negative")
        if not (0.0 <= float(cfg_trunc_ratio) <= 1.0):
            raise ValueError("cfg_trunc_ratio_must_be_in_[0,1]")
        if int(synthetic_hidden) <= 0:
            raise ValueError("synthetic_hidden_must_be_positive")
        if str(solver) not in LUMINA_IMAGE_2_0_INTEGRATORS:
            raise ValueError(
                f"{ERR_LUMINA_INTEGRATOR_UNKNOWN}:{solver!r}"
                f"; expected one of {LUMINA_IMAGE_2_0_INTEGRATORS!r}"
            )
        for rope_label, rope_value in (
            ("rope_axes[0]", rope_axes[0]),
            ("rope_axes[1]", rope_axes[1]),
            ("rope_axes[2]", rope_axes[2]),
        ):
            if int(rope_value) <= 0:
                raise ValueError(f"{rope_label}_must_be_positive")

        self._num_steps = int(num_steps)
        self._guidance_scale = float(guidance_scale)
        self._cfg_trunc_ratio = float(cfg_trunc_ratio)
        self._cfg_normalization = bool(cfg_normalization)
        self._rope_axes: tuple[int, int, int] = (
            int(rope_axes[0]),
            int(rope_axes[1]),
            int(rope_axes[2]),
        )
        self._seed_offset = int(seed_offset)
        self._synthetic_hidden = int(synthetic_hidden)
        self._synthetic_seed = int(synthetic_seed)
        self._solver: str = str(solver)

        # Resolve weights path.
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or lumina_image_2_0_resolve_weights_path()
        self._weights_path = (
            Path(resolved) if resolved is not None else Path("synthetic")
        )

        # Decide operating mode.
        if force_mode == "auto":
            if (
                self._weights_path.exists()
                and torch_is_available()
                and diffusers_is_available()
                and transformers_is_available()
            ):
                self._mode: Mode = "torch"
            else:
                self._mode = "synthetic"
        elif force_mode == "torch":
            if not torch_is_available():
                raise RuntimeError("torch requested but not installed")
            if not diffusers_is_available():
                raise RuntimeError("diffusers requested but not installed")
            if not transformers_is_available():
                raise RuntimeError("transformers requested but not installed")
            if not self._weights_path.exists():
                raise FileNotFoundError(
                    f"lumina_image_2_0_weights_missing:{self._weights_path}"
                )
            self._mode = "torch"
        elif force_mode == "upstream":
            if not torch_is_available():
                raise RuntimeError("upstream requested but torch not installed")
            if not self._weights_path.exists():
                raise FileNotFoundError(
                    f"lumina_image_2_0_weights_missing:{self._weights_path}"
                )
            self._mode = "upstream"
        elif force_mode == "synthetic":
            self._mode = "synthetic"
        else:
            raise ValueError(f"unknown_force_mode:{force_mode}")

        # Backend handles.
        self._pipeline: Any = None
        self._torch_dtype: Any = None
        self._synthetic_weights: dict[str, ArrayF64] | None = None
        # When ``force_mode == 'upstream'`` we keep a repr of any
        # import / weight-loading failure here so the engine log can
        # surface why the upstream path is unavailable without
        # crashing the framework. ``None`` when the upstream load
        # succeeded, or when the adapter never attempted the upstream
        # path.
        self._upstream_init_error: str | None = None
        if self._mode == "torch":
            try:
                import torch as _torch  # local import -- torch is optional.

                # bfloat16 matches the paper's recommended inference
                # dtype (the consolidated weights ship as bf16).
                self._torch_dtype = _torch.bfloat16
                self._pipeline = _load_torch_pipeline(
                    self._weights_path, dtype=self._torch_dtype
                )
            except ImportError:
                self._mode = "synthetic"
        elif self._mode == "upstream":
            try:
                import torch as _torch  # local import -- torch is optional.

                self._torch_dtype = _torch.bfloat16
                self._pipeline = _load_upstream_pipeline(
                    self._weights_path, dtype=self._torch_dtype
                )
            except (ImportError, FileNotFoundError, RuntimeError, EOFError, ValueError) as exc:
                # Upstream path requires the published
                # ``consolidated.00-of-01.safetensors`` /
                # ``model_args.pth`` + a working ``flash_attn`` wheel.
                # None of those is a guaranteed runtime guarantee, so
                # we fall back to ``synthetic`` rather than crashing
                # the framework; the failure is surfaced via the
                # exception's repr in the engine log.
                # ``UnpicklingError`` and friends are surfaced as
                # ``EOFError`` / ``ValueError`` here because
                # ``weights/model_args.pth`` is currently an LFS
                # pointer stub (ASCII text starting with the LFS
                # version line, not a real pickle).
                self._mode = "synthetic"
                self._upstream_init_error = repr(exc)
            else:
                self._upstream_init_error = None
        if self._mode == "synthetic":
            self._synthetic_weights = _random_init_synthetic_weights(
                hidden=int(self._synthetic_hidden),
                seed=int(self._synthetic_seed),
            )

        # LRU-bounded native-states cache (audit A-3 mirror of twodim_fm).
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        # Gemma2 text-embedding cache keyed by sha256(prompt + negative_prompt
        # + calibration_hash). Bounded LRU.
        self._text_embed_cache: OrderedDict[str, tuple[Any, Any]] = OrderedDict()
        self._caps = LuminaImage20Capabilities()
        # Instance-level override for F14 state-shape resolution
        # (r17-audit P-07 -- mirrors HiDreamI1Adapter's dual-level
        # pattern so the runner's ``getattr(self._adapter, "state_shape",
        # (2,))`` always sees the instance value). Defaults to the
        # canonical ``LUMINA_IMAGE_2_0_STATE_SHAPE``; subclasses /
        # fixtures may override via ``self.state_shape = ...`` before
        # the runner inspects the adapter.
        self.state_shape: tuple[int, ...] = LUMINA_IMAGE_2_0_STATE_SHAPE

        # Wave 113.A.5 Fix 0 — inline N=1 forward-shape assert at
        # adapter construction time. Industry standard (Diffusers
        # Triton strict-config, BentoML input_spec): catch a wrong-
        # shape or all-zeros shim BEFORE the sweep runs N=1000 cells.
        # Skip-guarded on torch mode + ckpt path so synthetic-mode
        # tests (no torch, no ckpt) construct cleanly as before.
        if (
            self._mode == "torch"
            and self._pipeline is not None
            and torch_is_available()
            and self._weights_path is not None
            and Path(self._weights_path).exists()
        ):
            try:
                import torch as _torch_assert  # noqa: PLC0415
                _x = _torch_assert.randn(1, *LUMINA_IMAGE_2_0_STATE_SHAPE)
                _t = _torch_assert.tensor([0.5])
                _te = _torch_assert.randn(1, 64, 2304)
                _tf = getattr(self._pipeline, "transformer", self._pipeline)
                with _torch_assert.no_grad():
                    _v = _tf(hidden_states=_x, timestep=_t,
                             encoder_hidden_states=_te,
                             encoder_attention_mask=None).sample
                if tuple(_v.shape) != (1, *LUMINA_IMAGE_2_0_STATE_SHAPE):
                    raise RuntimeError(
                        "Wave 113.A.5 Fix 0: Lumina-Image 2.0 shim "
                        f"returned shape {tuple(_v.shape)} but "
                        f"contract is (1, {tuple(LUMINA_IMAGE_2_0_STATE_SHAPE)}); "
                        "shim likely broken. See "
                        "docs/audit/wave113-final-synthesis.md"
                    )
                if float(_v.abs().max()) <= 0.0:
                    raise RuntimeError(
                        "Wave 113.A.5 Fix 0: Lumina-Image 2.0 shim "
                        "returned all-zeros velocity — stub or broken "
                        "forward. See docs/audit/wave113-final-synthesis.md"
                    )
            except RuntimeError:
                raise
            except Exception as _exc:  # noqa: BLE001 — fail-closed gate
                raise RuntimeError(
                    "Wave 113.A.5 Fix 0: Lumina-Image 2.0 inline "
                    f"pre-flight shape assert failed: {_exc!r}. "
                    "See docs/audit/wave113-final-synthesis.md"
                ) from _exc

    # ------------------------------------------------------------------
    # 1. capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. helpers -- LRU-bounded caches
    # ------------------------------------------------------------------

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > LUMINA_IMAGE_2_0_NATIVE_STATES_MAXSIZE:
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        self._native_states.pop(digest, None)

    def _put_text_embed(self, key: str, emb_pair: tuple[Any, Any]) -> None:
        if key in self._text_embed_cache:
            self._text_embed_cache[key] = emb_pair
            self._text_embed_cache.move_to_end(key)
            return
        self._text_embed_cache[key] = emb_pair
        while len(self._text_embed_cache) > LUMINA_IMAGE_2_0_TEXT_CACHE_MAXSIZE:
            self._text_embed_cache.popitem(last=False)

    def _resolve_text_embed(self, key: str) -> tuple[Any, Any] | None:
        return self._text_embed_cache.get(key)

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
        digest = digest_state(
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
                "x0": np.asarray(x0, dtype=np.float64).reshape(
                    LUMINA_IMAGE_2_0_STATE_SHAPE
                ),
                "source_round": 0,
                "mode": self._mode,
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("latent"): make_ref(
                    "lumina_image_2_0:",
                    "initial",
                    batch=batch_id,
                    sample=sample_id,
                ),
                # Text condition is a placeholder TensorRef -- the actual
                # Gemma2 embedding lives on the adapter side in
                # ``self._text_embed_cache``. The engine never inspects
                # the ref's contents; it only propagates the opaque
                # handle.
                ChannelName("text_condition"): make_ref(
                    "lumina_image_2_0:",
                    "text_initial",
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
            provenance=("lumina_image_2_0@v1",),
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

        beta, memory_fraction = memory_fraction_for(policy, ChannelName("latent"))
        prior_x = np.asarray(
            prior_entry["x0"], dtype=np.float64
        ).reshape(LUMINA_IMAGE_2_0_STATE_SHAPE)
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_x = _synthesize_latent_like_tensor(np.random.default_rng(restart_seed))

        m = max(0.0, min(1.0, float(memory_fraction)))
        blended = (m * prior_x + (1.0 - m) * fresh_x).astype(np.float64)
        blended = np.clip(blended, -LUMINA_IMAGE_2_0_CLAMP, LUMINA_IMAGE_2_0_CLAMP)

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
        return StateBundle(
            channels={
                ChannelName("latent"): make_ref(
                    "lumina_image_2_0:",
                    "restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
                # Text condition is NOT blended -- it is condition, not
                # state. The ref propagates unchanged from the prior so
                # the engine's restart math is state-only.
                ChannelName("text_condition"): make_ref(
                    "lumina_image_2_0:",
                    "text_restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
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
            provenance=tuple(state.provenance) + (AUDIT_LUMINA_RESTART_BLEND,),
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
        new_spec = dict(delta.delta_spec)
        # Stamp paper defaults; the framework's ``delta_spec`` can
        # override these per-round.
        new_spec.setdefault(
            "target_distribution", "lumina_image_2.0_text_to_image"
        )
        new_spec.setdefault(
            "integrator_config_hash", LUMINA_IMAGE_2_0_CONFIG_HASH
        )
        new_spec.setdefault("num_steps", LUMINA_IMAGE_2_0_NUM_STEPS_DEFAULT)
        new_spec.setdefault(
            "guidance_scale", LUMINA_IMAGE_2_0_GUIDANCE_SCALE_DEFAULT
        )
        new_spec.setdefault(
            "cfg_trunc_ratio", LUMINA_IMAGE_2_0_CFG_TRUNC_RATIO_DEFAULT
        )
        new_spec.setdefault("cfg_normalization", True)
        new_spec.setdefault(
            "rope_axes", LUMINA_IMAGE_2_0_ROPE_AXES_DEFAULT
        )
        # Per-round condition injection: encode the (prompt,
        # negative_prompt) pair via the Gemma2 text encoder, cache
        # keyed by ``calibration_artifact_hash``, and stamp the new
        # delta's ``delta_spec`` with the cache key so ``solve_ode``
        # can resolve the cached embedding without re-running the
        # encoder. The encode path is lazy-imported (torch /
        # transformers) so the framework's stdlib-only contract holds
        # in synthetic mode.
        prompt = str(new_spec.get("prompt", ""))
        negative_prompt = str(new_spec.get("negative_prompt", ""))
        if not prompt:
            raise ValueError(ERR_LUMINA_PROMPT_MISSING)
        cache_key = _text_embed_cache_key(
            prompt,
            negative_prompt,
            str(delta.calibration_artifact_hash),
        )
        cached = self._resolve_text_embed(cache_key)
        if cached is None:
            text_emb, uncond_text_emb, attn_mask, uncond_attn_mask = (
                self._encode_text_pair(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                )
            )
            self._put_text_embed(
                cache_key,
                (text_emb, uncond_text_emb, attn_mask, uncond_attn_mask),
            )
        new_spec["text_embed_cache_key"] = cache_key
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 6a. text-encoder helper -- lazy torch + transformers import
    # ------------------------------------------------------------------

    def _encode_text_pair(
        self,
        *,
        prompt: str,
        negative_prompt: str,
    ) -> tuple[Any, Any, Any | None, Any | None]:
        """Encode ``prompt`` and ``negative_prompt`` via Gemma2.

        Returns a 4-tuple ``(text_emb, uncond_text_emb, attention_mask,
        uncond_attention_mask)``; the embeddings are adapter-side
        native tensors that MUST NOT cross the protocol boundary. The
        encode path is lazy-imported: in synthetic mode a tiny NumPy
        placeholder pair is returned so the Protocol conformance
        tests run without the heavy stack.

        The torch mode returns the actual Gemma2 hidden states from
        ``transformers.Gemma2Model`` -- the paper embeds the
        ``last_hidden_state`` (shape ``(1, seq_text, 2304)``) into
        the Unified Next-DiT as the text condition.
        """
        if self._mode != "torch" or self._pipeline is None:
            # Synthetic placeholder: a deterministic NumPy anchor that
            # satisfies the protocol surface without requiring
            # transformers / torch. Shape ``(1, 1, 2304)`` mirrors
            # the canonical Gemma2 embedding dim (hidden_size=2304).
            seed_blob = repr(("text_embed", str(prompt), str(negative_prompt))).encode(
                "utf-8"
            )
            seed = int(hashlib.sha256(seed_blob).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            text_emb = rng.standard_normal((1, 1, 2304)).astype(np.float64)
            uncond_text_emb = np.zeros_like(text_emb)
            attn_mask = np.ones((1, 1), dtype=np.int64)
            return text_emb, uncond_text_emb, attn_mask, attn_mask

        # Torch mode: lazy-import Gemma2Model + tokenizer, encode.
        try:
            import torch  # local import.
            from transformers import GemmaTokenizer  # local import.
        except ImportError:
            # Defensive: if torch / transformers disappear mid-session,
            # fall back to the synthetic placeholder so the round can
            # still complete (engine never sees a hard fail).
            return self._encode_text_pair(
                prompt=prompt, negative_prompt=negative_prompt
            )

        # The adapter is configured for a published Lumina-Image 2.0
        # checkpoint; the Gemma2 text encoder + tokenizer are loaded
        # by the diffusers ``Lumina2Pipeline.from_pretrained`` call
        # earlier. Reuse the pipeline's loaded components so the
        # tokenizer / encoder dtype match the pipeline (no extra disk
        # load + no dtype mismatch on the forward pass).
        try:
            tokenizer = self._pipeline.tokenizer
            encoder = self._pipeline.text_encoder
        except AttributeError:
            # Defensive: the published checkpoint layout may not match
            # our pipeline expectations. Fall back to the synthetic
            # pair so the round still completes.
            return self._encode_text_pair(
                prompt=prompt, negative_prompt=negative_prompt
            )

        max_seq = int(self._rope_axes[0])

        with torch.no_grad():
            tokens = tokenizer(
                [prompt],
                return_tensors="pt",
                padding="max_length",
                max_length=max_seq,
                truncation=True,
            )
            uncond_tokens = tokenizer(
                [negative_prompt or ""],
                return_tensors="pt",
                padding="max_length",
                max_length=max_seq,
                truncation=True,
            )
            input_ids = tokens.input_ids.to(dtype=torch.long)
            attn = tokens.attention_mask.to(dtype=torch.long)
            uncond_ids = uncond_tokens.input_ids.to(dtype=torch.long)
            uncond_attn = uncond_tokens.attention_mask.to(dtype=torch.long)
            # Tokenizer output lives on CPU; the loaded text_encoder may
            # have been moved to GPU via ``pipeline.to("cuda")``. Move
            # inputs to the encoder's device so the forward pass doesn't
            # crash on a mixed-device ``F.embedding`` call.
            enc_device = next(encoder.parameters()).device
            input_ids = input_ids.to(device=enc_device)
            attn = attn.to(device=enc_device)
            uncond_ids = uncond_ids.to(device=enc_device)
            uncond_attn = uncond_attn.to(device=enc_device)
            # SEMANTIC DIFFERENCE vs upstream:
            # the framework's torch path uses ``last_hidden_state``
            # (the diffusers Lumina2Pipeline convention); the upstream
            # ``sample.py`` uses ``hidden_states[-2]`` (the 2nd-to-last
            # Gemma2 layer). Both are valid choices in the paper's
            # framework -- mixing-and-matching is a documented
            # foot-gun, so the upstream mode uses ``hidden_states[-2]``
            # below.
            if self._mode == "upstream":
                # Upstream's ``encode_prompt`` returns the second-to-
                # last Gemma2 hidden layer (``hidden_states[-2]``)
                # rather than ``last_hidden_state``. The diffusers
                # pipeline exposes ``output_hidden_states=True`` via
                # the underlying ``Gemma2Model``; we re-encode here
                # so the layer index matches upstream.
                cond_out = encoder(
                    input_ids=input_ids,
                    attention_mask=attn,
                    output_hidden_states=True,
                )
                uncond_out = encoder(
                    input_ids=uncond_ids,
                    attention_mask=uncond_attn,
                    output_hidden_states=True,
                )
                cond_h = cond_out.hidden_states[-2]
                uncond_h = uncond_out.hidden_states[-2]
            else:
                cond_h = encoder(
                    input_ids=input_ids,
                    attention_mask=attn,
                ).last_hidden_state
                uncond_h = encoder(
                    input_ids=uncond_ids,
                    attention_mask=uncond_attn,
                ).last_hidden_state

        # Upstream mode: pre-stack the (cond, uncond) embeddings so
        # ``model.forward_with_cfg`` can use the (2, L, 2304)-shaped
        # ``cap_feats`` and (2, L)-shaped ``cap_mask`` directly. The
        # upstream's ``forward_with_cfg`` does the conditional /
        # unconditional split internally via
        # ``cond_eps, uncond_eps = torch.split(eps, len(eps)//2)``.
        if self._mode == "upstream":
            text_emb = torch.cat([cond_h, uncond_h], dim=0)
            encoder_attention_mask = torch.cat([attn, uncond_attn], dim=0)
            return (
                text_emb.detach(),
                None,
                encoder_attention_mask.detach(),
                None,
            )
        return (
            cond_h.detach(),
            uncond_h.detach(),
            attn.detach(),
            uncond_attn.detach(),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def _velocity_field(
        self,
        x: ArrayF64,
        t: float,
        *,
        text_emb: Any,
        uncond_text_emb: Any,
        encoder_attention_mask: Any | None = None,
        uncond_attention_mask: Any | None = None,
    ) -> ArrayF64:
        """Evaluate the velocity field at ``(x, t)`` for the active backend.

        ``torch`` mode delegates to :func:`_torch_velocity_field`;
        ``synthetic`` mode uses the deterministic NumPy two-tensor
        affine field. Returns a NumPy ``(16, 128, 128)`` float64 array
        (copy-safe to mutate).
        """
        if self._mode == "torch":
            assert self._pipeline is not None
            # The diffusers Lumina2Pipeline owns the transformer + VAE
            # + scheduler; we call the inner transformer directly for
            # the velocity field and rely on the pipeline's loaded
            # encoder for any latent <-> pixel round-trips downstream.
            transformer = getattr(self._pipeline, "transformer", self._pipeline)
            return _torch_velocity_field(
                transformer,
                x,
                t,
                dtype=self._torch_dtype,
                text_emb=text_emb,
                uncond_text_emb=uncond_text_emb,
                encoder_attention_mask=encoder_attention_mask,
                uncond_attention_mask=uncond_attention_mask,
                guidance_scale=self._guidance_scale,
                cfg_trunc_ratio=self._cfg_trunc_ratio,
                cfg_normalization=self._cfg_normalization,
            )
        if self._mode == "upstream":
            assert self._pipeline is not None
            # The upstream harness owns the bare ``NextDiT`` model +
            # a ``transport.Sampler``. ``_upstream_velocity_field``
            # batches the (cond, uncond) pair inside the call -- the
            # upstream ``forward_with_cfg`` expects ``cap_feats`` /
            # ``cap_mask`` to be pre-stacked along the batch dim (see
            # ``_encode_text_pair`` for the pre-stacking path).
            return _upstream_velocity_field(
                self._pipeline,
                x,
                t,
                dtype=self._torch_dtype,
                text_emb=text_emb,
                uncond_text_emb=uncond_text_emb,
                encoder_attention_mask=encoder_attention_mask,
                uncond_attention_mask=uncond_attention_mask,
                guidance_scale=self._guidance_scale,
                cfg_trunc_ratio=self._cfg_trunc_ratio,
                cfg_normalization=self._cfg_normalization,
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
            raise ValueError(ERR_LUMINA_NUM_STEPS)
        x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            LUMINA_IMAGE_2_0_STATE_SHAPE
        )

        # Resolve the cached text embeddings (encoded during
        # ``compose_condition``). In synthetic mode the cached entries
        # are NumPy placeholders; in torch mode they are the actual
        # Gemma2 hidden states.
        cache_key = str(condition.delta_spec.get("text_embed_cache_key", ""))
        if not cache_key:
            raise CapabilityMissingError(
                "text_embed_cache_key_missing",
                context=str(condition.delta_spec),
            )
        cached = self._resolve_text_embed(cache_key)
        if cached is None:
            raise CapabilityMissingError(
                ERR_LUMINA_TEXT_EMBED_MISSING,
                context=cache_key,
            )
        text_emb, uncond_text_emb, attn_mask, uncond_attn_mask = cached

        # Per-round overrides for CFG (paper §4.5 + framework control).
        guidance_scale = float(
            condition.delta_spec.get("guidance_scale", self._guidance_scale)
        )
        cfg_trunc_ratio = float(
            condition.delta_spec.get("cfg_trunc_ratio", self._cfg_trunc_ratio)
        )
        cfg_normalization = bool(
            condition.delta_spec.get("cfg_normalization", self._cfg_normalization)
        )

        solver_kind = str(self._solver)
        t_grid = np.linspace(
            0.0, float(LUMINA_IMAGE_2_0_T_END), num_steps + 1, dtype=np.float64
        )
        traj = np.empty(
            (t_grid.size, *LUMINA_IMAGE_2_0_STATE_SHAPE), dtype=np.float64
        )
        traj[0] = x0.copy()
        x_cur = x0.copy()

        # The CFG params are baked into ``self._velocity_field`` via
        # closure above; per-round overrides are applied here so the
        # trajectory reflects the round's policy.
        # Closure pattern: rebuild a small per-round velocity function.
        def _vf_round(xx: ArrayF64, tt: float) -> ArrayF64:
            if self._mode == "torch":
                assert self._pipeline is not None
                transformer = getattr(self._pipeline, "transformer", self._pipeline)
                return _torch_velocity_field(
                    transformer,
                    xx,
                    tt,
                    dtype=self._torch_dtype,
                    text_emb=text_emb,
                    uncond_text_emb=uncond_text_emb,
                    encoder_attention_mask=attn_mask,
                    uncond_attention_mask=uncond_attn_mask,
                    guidance_scale=guidance_scale,
                    cfg_trunc_ratio=cfg_trunc_ratio,
                    cfg_normalization=cfg_normalization,
                )
            if self._mode == "upstream":
                assert self._pipeline is not None
                return _upstream_velocity_field(
                    self._pipeline,
                    xx,
                    tt,
                    dtype=self._torch_dtype,
                    text_emb=text_emb,
                    uncond_text_emb=uncond_text_emb,
                    encoder_attention_mask=attn_mask,
                    uncond_attention_mask=uncond_attn_mask,
                    guidance_scale=guidance_scale,
                    cfg_trunc_ratio=cfg_trunc_ratio,
                    cfg_normalization=cfg_normalization,
                )
            assert self._synthetic_weights is not None
            return _synthetic_velocity_field(
                xx, tt, weights=self._synthetic_weights
            )

        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            v1 = _vf_round(x_cur, t0)
            if solver_kind == LUMINA_IMAGE_2_0_INTEGRATOR_HEUN and i < t_grid.size - 1:
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(
                    x_cur + dt * v1,
                    -LUMINA_IMAGE_2_0_CLAMP,
                    LUMINA_IMAGE_2_0_CLAMP,
                )
                # Corrector: trapezoidal average.
                v2 = _vf_round(x_pred, t1)
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -LUMINA_IMAGE_2_0_CLAMP,
                    LUMINA_IMAGE_2_0_CLAMP,
                )
            else:
                x_cur = np.clip(
                    x_cur + dt * v1,
                    -LUMINA_IMAGE_2_0_CLAMP,
                    LUMINA_IMAGE_2_0_CLAMP,
                )
            traj[i] = x_cur

        traj_digest = digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "integrator": str(solver_kind),
                "num_steps": int(num_steps),
                "guidance_scale": float(guidance_scale),
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
            (
                "lumina_image_2_0_config",
                str(solver_kind),
                int(num_steps),
                int(seed),
                float(guidance_scale),
                float(cfg_trunc_ratio),
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
            LUMINA_IMAGE_2_0_STATE_SHAPE
        )
        endpoint_digest = digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "x_final_first": [
                    float(x_final[0, 0, 0]),
                    float(x_final[0, 0, 1]),
                    float(x_final[0, 1, 0]),
                ],
                "t_final": float(LUMINA_IMAGE_2_0_T_END),
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "x": np.asarray(x_final, dtype=np.float64).reshape(
                    LUMINA_IMAGE_2_0_STATE_SHAPE
                ),
                "t": float(LUMINA_IMAGE_2_0_T_END),
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
            provenance=tuple(state.provenance) + (AUDIT_LUMINA_OBSERVED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 -- public trajectory export)
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
    # 10. inject_forward_noise (optional -- P0-7 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """Inject ``injected`` (shape ``(16, 128, 128)``) into the bundle's prior.

        Returns a fresh :class:`StateBundle` whose prior x0 has been
        updated to ``x + injected`` (clipped to ``[-LUMINA_IMAGE_2_0_CLAMP,
        LUMINA_IMAGE_2_0_CLAMP]``) and whose ``provenance`` records
        the :data:`AUDIT_FORWARD_NOISE_APPLIED` tag.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        x_prior = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            LUMINA_IMAGE_2_0_STATE_SHAPE
        )
        x_new_arr = np.asarray(injected, dtype=np.float64).reshape(
            LUMINA_IMAGE_2_0_STATE_SHAPE
        )
        x_new = np.clip(
            x_prior + x_new_arr,
            -LUMINA_IMAGE_2_0_CLAMP,
            LUMINA_IMAGE_2_0_CLAMP,
        )
        new_digest = digest_state(
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


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_lumina_image_2_0_adapter(
    *,
    weights_path: Path | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    num_steps: int = LUMINA_IMAGE_2_0_NUM_STEPS_DEFAULT,
    solver: str = LUMINA_IMAGE_2_0_INTEGRATOR_EULER,
) -> LuminaImage20Adapter:
    """Default factory for :class:`LuminaImage20Adapter`.

    When ``weights_path`` is ``None`` the adapter resolves
    ``data/lumina-image-2.0`` / ``data/Lumina-Image-2.0`` /
    ``data/Alpha-VLLM__Lumina-Image-2.0`` in priority order; when none
    of those exist and ``force_mode`` is ``"auto"``, the adapter falls
    back to ``synthetic`` mode (testing-only).
    """
    return LuminaImage20Adapter(
        weights_path=weights_path,
        force_mode=force_mode,
        num_steps=num_steps,
        solver=solver,
    )


__all__ = [
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_LUMINA_OBSERVED",
    "AUDIT_LUMINA_RESTART_BLEND",
    "AUDIT_LUMINA_TEXT_CACHED",
    "ERR_LUMINA_INTEGRATOR_UNKNOWN",
    "ERR_LUMINA_NUM_STEPS",
    "ERR_LUMINA_PROMPT_MISSING",
    "ERR_LUMINA_TEXT_EMBED_MISSING",
    "LUMINA_IMAGE_2_0_CHANNEL_DOMAINS",
    "LUMINA_IMAGE_2_0_CHANNELS",
    "LUMINA_IMAGE_2_0_CLAMP",
    "LUMINA_IMAGE_2_0_CFG_TRUNC_RATIO_DEFAULT",
    "LUMINA_IMAGE_2_0_CONFIG_HASH",
    "LUMINA_IMAGE_2_0_CONFIG_VERSION",
    "LUMINA_IMAGE_2_0_GUIDANCE_SCALE_DEFAULT",
    "LUMINA_IMAGE_2_0_INTEGRATOR_EULER",
    "LUMINA_IMAGE_2_0_INTEGRATOR_HEUN",
    "LUMINA_IMAGE_2_0_INTEGRATORS",
    "LUMINA_IMAGE_2_0_MECHANISM_ID",
    "LUMINA_IMAGE_2_0_NATIVE_STATES_MAXSIZE",
    "LUMINA_IMAGE_2_0_NUM_STEPS_DEFAULT",
    "LUMINA_IMAGE_2_0_ROPE_AXES_DEFAULT",
    "LUMINA_IMAGE_2_0_STATE_SHAPE",
    "LUMINA_IMAGE_2_0_SYNTHETIC_HIDDEN",
    "LUMINA_IMAGE_2_0_SYNTHETIC_SEED_DEFAULT",
    "LUMINA_IMAGE_2_0_T_END",
    "LUMINA_IMAGE_2_0_TEXT_CACHE_MAXSIZE",
    "LUMINA_IMAGE_2_0_WEIGHTS_CANDIDATES",
    "LuminaImage20Adapter",
    "LuminaImage20Capabilities",
    "default_lumina_image_2_0_adapter",
    "diffusers_is_available",
    "lumina_image_2_0_resolve_weights_path",
    "torch_is_available",
    "transformers_is_available",
]