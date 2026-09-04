"""Diffusers-style forward wrapper — framework-core glue for DiT-family models.

Purpose
-------

PHASE-3 glue extraction (``todo/PHASE-3-glue-layer-improvement.md`` §
"Example glue patterns"): centralise the **diffusers / SiT / DiT
forward-pass** wrapper that every DiT-family adapter
(:mod:`adaptive_reflow.adapters.self_flow`,
:mod:`adaptive_reflow.adapters.freqflow`,
:mod:`adaptive_reflow.adapters.mm_fm`,
:mod:`adaptive_reflow.adapters.kanzi`,
:mod:`adaptive_reflow.adapters.hidream_i1`,
…) was previously re-typing. The wrapper exposes:

* :class:`DiffusersForwardSignature` — a dataclass that captures
  the four-argument contract
  ``v_theta(x: Tensor, t: Tensor, y: Tensor, *, cfg_scale: float) -> Tensor``
  that every DiT-family model uses. The dataclass is the
  parameter envelope so adapters can re-export it without
  re-typing the tuple.
* :func:`diffusers_preprocess` — NumPy-to-torch conversion with
  dtype handling (``float32`` for SiT-XL/2 / FreqFlow / Kanzi
  encoder / MM-FM; ``bfloat16`` for HiDream-I1) and
  ``unsqueeze(0)`` batch-dim addition. Pure tensor-manipulation;
  no forward call.
* :func:`diffusers_postprocess` — inverse: torch tensor →
  NumPy ``float64`` array of the adapter's native shape, with
  the batch dim squeezed and the first ``out_channels`` slice
  taken when the upstream emits more channels than the input.
* :class:`DiffusersForwardWrapper` — full wrapper that handles
  the ``torch.no_grad()`` / ``eval()`` invocation, the optional
  classifier-free-guidance (CFG) duplicate-and-interpolate
  trick, and the postprocess return.
* :class:`DiffusersPipelineFactory` — small builder that
  resolves ``HiDreamImagePipeline`` / ``SiTTransformer2DModel``
  etc. via a try-import-and-fallback chain, so the adapters
  don't need to re-implement the upstream-vs-diffusers shim.

Constraints
-----------

* Stdlib + numpy only at module level. ``torch`` /
  ``diffusers`` / ``transformers`` are imported lazily inside
  the wrappers that need them so the framework never requires
  them at import time.
* All public surface is **pure data manipulation + lazy
  import dispatch**; no model side effects at module load.
* The forward wrapper is **deterministic for fixed inputs**:
  same ``x``, ``t``, ``y``, ``cfg_scale`` ⇒ same output
  (the upstream DiT is wrapped in ``torch.no_grad()`` /
  ``eval()`` to enforce inference-only determinism).

CFG semantics
-------------

The CFG duplicate-and-interpolate trick runs the upstream DiT
twice — once with the conditional ``y`` and once with an
unconditional ``y`` (zero tensor) — and combines::

    v = v_uncond + cfg_scale * (v_cond - v_uncond)

so ``cfg_scale = 1.0`` ⇒ identity (``v = v_cond``) and
``cfg_scale = 0.0`` ⇒ ``v = v_uncond``. ``cfg_scale <= 0.0``
disables CFG (single forward pass).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

ArrayF64 = NDArray[np.float64]

#: Supported dtype tags the wrappers accept.
#: ``"float32"`` — SiT-XL/2 / FreqFlow / Kanzi encoder / MM-FM.
#: ``"bfloat16"`` — HiDream-I1 / large FLUX-style DiTs.
DiffusersDType = Literal["float32", "bfloat16"]


@dataclass(frozen=True)
class DiffusersForwardSignature:
    """Parameter envelope for the canonical DiT-family forward call.

    Attributes
    ----------
    in_channels:
        Latent channels (4 for SD-VAE / DC-AE; 16 for FLUX-VAE).
    out_channels:
        Velocity-field channels. Usually equals ``in_channels``;
        some checkpoints (Self-Flow's dual-timestep head) emit
        ``2 * in_channels`` so post-processing slices the first
        ``in_channels``.
    patch_size:
        Tokenisation patch size (2 for SiT-XL/2, 1 for HiDream).
    sample_size:
        Spatial size after patch tokenisation
        (``H_patches = H_latent / patch_size``).
    dtype:
        ``"float32"`` / ``"bfloat16"``. Used by
        :func:`diffusers_preprocess` to set the torch dtype.
    use_cfg:
        Whether the model accepts classifier-free-guidance
        duplicate-forward calls. When ``True``, the wrapper
        runs the model twice (cond + uncond) and interpolates.
    """

    in_channels: int
    out_channels: int
    patch_size: int = 2
    sample_size: int = 16
    dtype: DiffusersDType = "float32"
    use_cfg: bool = True
    conditioning_dim: int = 1152  # adaLN class-embed / family-embed dim
    extra_kwargs: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if int(self.in_channels) <= 0:
            raise ValueError("in_channels_must_be_positive")
        if int(self.out_channels) <= 0:
            raise ValueError("out_channels_must_be_positive")
        if int(self.patch_size) <= 0:
            raise ValueError("patch_size_must_be_positive")
        if int(self.sample_size) <= 0:
            raise ValueError("sample_size_must_be_positive")
        if int(self.conditioning_dim) <= 0:
            raise ValueError("conditioning_dim_must_be_positive")


# ---------------------------------------------------------------------------
# Pure numpy / dtype helpers (torch-free)
# ---------------------------------------------------------------------------


def _torch_dtype_for(tag: DiffusersDType) -> Any:
    """Resolve a torch ``dtype`` object from the dtype tag.

    Imports torch lazily so the module is import-clean on
    CPU-only sandboxes.
    """
    try:
        import torch  # local import.
    except ImportError as exc:  # pragma: no cover — gated by caller.
        raise ImportError(
            "diffusers_preprocess requires torch; "
            "install torch>=2.1 or run the framework in synthetic mode"
        ) from exc
    if str(tag) == "bfloat16":
        return torch.bfloat16
    return torch.float32


def diffusers_preprocess(
    x: ArrayF64,
    *,
    signature: DiffusersForwardSignature,
    add_batch_dim: bool = True,
) -> Any:
    """Convert a NumPy latent to a torch tensor suitable for a DiT call.

    The output tensor has shape
    ``(1, in_channels, H, W)`` when ``add_batch_dim=True`` (the
    common case for SiT-XL/2 / FreqFlow / Kanzi / MM-FM / HiDream
    inference) and the dtype from ``signature.dtype``. The
    adapter never needs to touch torch APIs directly — this is
    the only conversion call site.
    """
    try:
        import torch  # local import.
    except ImportError as exc:  # pragma: no cover — gated by caller.
        raise ImportError(
            "diffusers_preprocess requires torch; "
            "install torch>=2.1 or run the framework in synthetic mode"
        ) from exc

    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError(
            f"diffusers_preprocess expects (C, H, W); got shape {tuple(arr.shape)!r}"
        )
    if arr.shape[0] != int(signature.in_channels):
        raise ValueError(
            f"diffusers_preprocess expected in_channels={int(signature.in_channels)}"
            f"; got {arr.shape[0]}"
        )
    t = torch.as_tensor(arr, dtype=_torch_dtype_for(signature.dtype))
    if add_batch_dim:
        t = t.unsqueeze(0)
    return t


def diffusers_postprocess(
    out: Any,
    *,
    signature: DiffusersForwardSignature,
    take_first_n_channels: int | None = None,
) -> ArrayF64:
    """Convert a torch DiT output to a NumPy float64 latent array.

    Squeezes the batch dim (assumed to be 1) and casts the
    result back to ``float64``. When the upstream DiT emits more
    channels than ``signature.in_channels`` (Self-Flow's
    dual-timestep head emits ``8`` channels for a 4-channel
    input), ``take_first_n_channels`` defaults to
    ``signature.in_channels`` so the velocity field shape
    matches the input latent shape.
    """
    try:
        import torch  # local import.
    except ImportError as exc:  # pragma: no cover — gated by caller.
        raise ImportError(
            "diffusers_postprocess requires torch"
        ) from exc

    if isinstance(out, torch.Tensor):
        v = out.detach()
        shape = tuple(v.shape)
        if len(shape) == 4 and shape[0] == 1:
            v = v.squeeze(0)
            shape = tuple(v.shape)
        keep = (
            int(take_first_n_channels)
            if take_first_n_channels is not None
            else int(signature.in_channels)
        )
        if shape[0] > keep:
            v = v[:keep]
        arr = np.asarray(v.cpu().numpy(), dtype=np.float64)
        return arr
    raise TypeError(
        "diffusers_postprocess expects a torch.Tensor; "
        f"got {type(out).__name__}"
    )


# ---------------------------------------------------------------------------
# Diffusers forward wrapper (lazy torch + diffusers)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiffusersForwardResult:
    """Structured output of :meth:`DiffusersForwardWrapper.__call__`.

    Attributes
    ----------
    velocity:
        NumPy ``float64`` velocity field, shape
        ``(in_channels, H, W)`` — matches the input latent.
    cfg_applied:
        ``True`` when CFG duplicate-and-interpolate fired
        (``cfg_scale > 0`` and ``signature.use_cfg``); ``False``
        when the single-cond pass ran.
    raw_cond:
        Raw conditional-pass output (torch Tensor or NumPy
        array) for diagnostic use. ``None`` when CFG was
        disabled.
    raw_uncond:
        Raw unconditional-pass output. ``None`` when CFG was
        disabled.
    """

    velocity: ArrayF64
    cfg_applied: bool
    raw_cond: Any = None
    raw_uncond: Any = None


class DiffusersForwardWrapper:
    """Wrap a DiT-family model behind the canonical forward contract.

    The wrapper hides three layers of boilerplate that every
    DiT-family adapter was previously re-typing:

    1. The NumPy → torch conversion + batch-dim add +
       dtype cast (:func:`diffusers_preprocess`).
    2. The ``torch.no_grad()`` / ``model.eval()`` invocation.
    3. The optional CFG duplicate-and-interpolate
       (``v_uncond + cfg_scale * (v_cond - v_uncond)``).
    4. The torch → NumPy conversion + postprocess channel slice
       (:func:`diffusers_postprocess`).

    Parameters
    ----------
    model:
        The DiT / SiT / Transformer2DModel instance. Must
        accept ``forward(x, t, y, **kwargs)`` (the diffusers
        convention).
    signature:
        The :class:`DiffusersForwardSignature` describing the
        model's input/output contract.
    """

    __slots__ = ("_model", "_signature", "_zero_y")

    def __init__(
        self,
        model: Any,
        *,
        signature: DiffusersForwardSignature,
    ) -> None:
        self._model = model
        self._signature = signature
        self._zero_y: Any = None  # cached zero-y tensor for CFG.

    @property
    def signature(self) -> DiffusersForwardSignature:
        return self._signature

    def _get_zero_y(self, *, dtype: Any, device: Any) -> Any:
        """Return a zero ``y`` tensor for the CFG unconditional pass."""
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError(
                "DiffusersForwardWrapper requires torch"
            ) from exc
        if self._zero_y is None or self._zero_y.dtype != dtype:
            self._zero_y = torch.zeros(
                1, int(self._signature.conditioning_dim), dtype=dtype, device=device,
            )
        return self._zero_y

    def __call__(
        self,
        x: ArrayF64,
        t: float,
        y: ArrayF64 | Any,
        *,
        cfg_scale: float = 1.0,
        forward_kwargs: Mapping[str, Any] | None = None,
    ) -> DiffusersForwardResult:
        """Run the canonical DiT forward call and return NumPy output.

        Parameters
        ----------
        x:
            NumPy latent of shape ``(in_channels, H, W)``.
        t:
            Flow-matching time in ``[0, 1]``.
        y:
            Conditioning vector. NumPy array of shape
            ``(conditioning_dim,)`` (any dtype) or an already-built
            torch tensor (passed through unchanged).
        cfg_scale:
            Classifier-free-guidance scale. ``<=0.0`` disables CFG
            (single conditional pass).
        forward_kwargs:
            Extra kwargs forwarded to the model's ``forward()``.
        """
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError(
                "DiffusersForwardWrapper requires torch"
            ) from exc

        sig = self._signature
        dtype = _torch_dtype_for(sig.dtype)

        x_t = diffusers_preprocess(x, signature=sig, add_batch_dim=True)
        x_t = x_t.to(dtype=dtype)

        if isinstance(y, torch.Tensor):
            y_t = y.to(dtype=dtype)
            if y_t.dim() == 1:
                y_t = y_t.unsqueeze(0)
        else:
            y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
            if y_arr.shape[0] != int(sig.conditioning_dim):
                raise ValueError(
                    f"expected y of dim {int(sig.conditioning_dim)}"
                    f"; got {y_arr.shape[0]}"
                )
            y_t = torch.as_tensor(y_arr, dtype=dtype).unsqueeze(0)
        y_t = y_t.to(device=x_t.device)

        t_t = torch.tensor([float(t)], dtype=dtype, device=x_t.device)

        fwd_kwargs = dict(forward_kwargs or {})
        fwd_kwargs.update(sig.extra_kwargs)

        with torch.no_grad():
            if hasattr(self._model, "eval"):
                self._model.eval()
            if float(cfg_scale) <= 0.0 or not bool(sig.use_cfg):
                v_cond = self._model(x_t, t_t, y_t, **fwd_kwargs)
                v_np = diffusers_postprocess(
                    v_cond, signature=sig, take_first_n_channels=int(sig.in_channels),
                )
                return DiffusersForwardResult(
                    velocity=v_np,
                    cfg_applied=False,
                    raw_cond=v_cond,
                    raw_uncond=None,
                )

            # CFG: run unconditional pass with zero ``y``.
            zero_y = self._get_zero_y(dtype=dtype, device=x_t.device)
            v_cond = self._model(x_t, t_t, y_t, **fwd_kwargs)
            v_uncond = self._model(x_t, t_t, zero_y, **fwd_kwargs)
            cfg = float(cfg_scale)
            v_cfg = v_uncond + cfg * (v_cond - v_uncond)
            v_np = diffusers_postprocess(
                v_cfg, signature=sig, take_first_n_channels=int(sig.in_channels),
            )
            return DiffusersForwardResult(
                velocity=v_np,
                cfg_applied=True,
                raw_cond=v_cond,
                raw_uncond=v_uncond,
            )


# ---------------------------------------------------------------------------
# Diffusers pipeline factory (try-import-and-fallback)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiffusersPipelineSpec:
    """Description of a diffusers pipeline the factory should build.

    The factory resolves ``transformer_cls`` / ``scheduler_cls`` /
    ``vae_cls`` lazily via :func:`_try_import`; the spec only
    names the symbols and the weights path.

    Attributes
    ----------
    name:
        Human-readable pipeline name (e.g. ``"HiDreamImagePipeline"``).
    transformer_symbol:
        ``"diffusers:HiDreamImageTransformer2DModel"`` — module +
        attribute pair, colon-separated.
    scheduler_symbol:
        ``"diffusers:FlowMatchEulerDiscreteScheduler"`` (or
        ``None`` to skip).
    vae_symbol:
        ``"diffusers:AutoencoderKL"`` (or ``None`` to skip).
    weights_path:
        Directory containing ``model_index.json`` and the
        per-component subdirectories.
    fallback_symbol:
        Optional upstream package symbol (e.g.
        ``"hi_diffusers.pipelines.hidream_image.pipeline_hidream_image:HiDreamImagePipeline"``).
        When provided the factory tries the upstream package first
        and falls back to the diffusers symbol.
    """

    name: str
    transformer_symbol: str | None = None
    scheduler_symbol: str | None = None
    vae_symbol: str | None = None
    weights_path: str | None = None
    fallback_symbol: str | None = None

    def __post_init__(self) -> None:
        if not str(self.name):
            raise ValueError("pipeline_name_must_be_non_empty")


def _try_import(symbol_path: str) -> Any | None:
    """Try to import ``"module:attribute"``; return ``None`` on failure.

    Mirrors the per-adapter try-import pattern in
    :mod:`adaptive_reflow.adapters._hidream_i1_upstream_shim`.
    """
    if ":" not in symbol_path:
        return None
    module_name, _, attr = symbol_path.partition(":")
    if not module_name or not attr:
        return None
    try:
        import importlib

        mod = importlib.import_module(str(module_name))
        return getattr(mod, str(attr), None)
    except Exception:
        return None


class DiffusersPipelineFactory:
    """Build a canonical diffusers pipeline from a :class:`DiffusersPipelineSpec`.

    The factory encapsulates the "try upstream package, fall back
    to diffusers" shim that HiDream / Lumina / Self-Flow / Kanzi /
    FreqFlow adapters all need. When the requested component
    class is missing, the factory returns ``None`` instead of
    raising — the caller can then fall back to the framework's
    synthetic-mode shim.
    """

    __slots__ = ("_spec",)

    def __init__(self, spec: DiffusersPipelineSpec) -> None:
        self._spec = spec

    @property
    def spec(self) -> DiffusersPipelineSpec:
        return self._spec

    def resolve_transformer_class(self) -> Any | None:
        """Resolve the DiT / Transformer class. Tries upstream first."""
        if self._spec.fallback_symbol:
            cls = _try_import(str(self._spec.fallback_symbol))
            if cls is not None:
                return cls
        if self._spec.transformer_symbol:
            return _try_import(str(self._spec.transformer_symbol))
        return None

    def resolve_scheduler_class(self) -> Any | None:
        if not self._spec.scheduler_symbol:
            return None
        return _try_import(str(self._spec.scheduler_symbol))

    def resolve_vae_class(self) -> Any | None:
        if not self._spec.vae_symbol:
            return None
        return _try_import(str(self._spec.vae_symbol))

    def build(
        self,
        *,
        text_encoder_constructors: Mapping[str, Callable[..., Any]] | None = None,
        dtype: Any = None,
    ) -> Any | None:
        """Construct the pipeline via ``from_pretrained`` calls.

        When torch is unavailable returns ``None``. The pipeline
        is built on CPU with the requested dtype (default
        ``torch.bfloat16`` for HiDream-style DiTs). The
        ``text_encoder_constructors`` mapping lets the caller
        substitute stub text encoders when the upstream checkpoint
        is missing a component (e.g. HiDream's 8B Llama branch).
        """
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError(
                "DiffusersPipelineFactory.build requires torch"
            ) from exc

        if dtype is None:
            dtype = torch.bfloat16

        if not self._spec.weights_path:
            return None
        from pathlib import Path as _Path

        wp = _Path(str(self._spec.weights_path))
        if not wp.exists():
            return None

        transformer_cls = self.resolve_transformer_class()
        scheduler_cls = self.resolve_scheduler_class()
        vae_cls = self.resolve_vae_class()
        if transformer_cls is None:
            return None

        kwargs: dict[str, Any] = {}
        if scheduler_cls is not None:
            try:
                kwargs["scheduler"] = scheduler_cls.from_pretrained(
                    str(wp / "scheduler"),
                )
            except Exception:
                pass
        if vae_cls is not None:
            try:
                kwargs["vae"] = vae_cls.from_pretrained(
                    str(wp / "vae"), dtype=dtype,
                )
            except Exception:
                pass
        try:
            kwargs["transformer"] = transformer_cls.from_pretrained(
                str(wp / "transformer"), dtype=dtype,
            )
        except Exception:
            return None

        for key, ctor in (text_encoder_constructors or {}).items():
            try:
                kwargs[key] = ctor(str(wp / key), dtype=dtype)
            except Exception:
                continue
        try:
            pipeline_cls = self.resolve_transformer_class()
            return pipeline_cls(**kwargs)
        except Exception:
            return None


__all__ = [
    "DiffusersDType",
    "DiffusersForwardResult",
    "DiffusersForwardSignature",
    "DiffusersForwardWrapper",
    "DiffusersPipelineFactory",
    "DiffusersPipelineSpec",
    "diffusers_postprocess",
    "diffusers_preprocess",
]
