"""VAE latent-space ↔ pixel-space decoder — framework-core glue for VAE-based image models.

Purpose
-------

PHASE-3 glue extraction (``todo/PHASE-3-glue-layer-improvement.md`` §
"Example glue patterns"): centralise the **VAE encode / decode**
boilerplate that every image-generation adapter
(:mod:`adaptive_reflow.adapters.hidream_i1`,
:mod:`adaptive_reflow.adapters.freqflow`,
:mod:`adaptive_reflow.adapters.self_flow`,
:mod:`adaptive_reflow.adapters.kanzi`,
:mod:`adaptive_reflow.adapters.mm_fm`,
…) was previously re-typing. The decoder exposes:

* :class:`LatentShape` — declarative description of a VAE latent
  shape ``(C_latent, H_latent, W_latent)`` paired with the
  implied pixel-space shape ``(3, H_pixel, W_pixel)``.
  Pre-canned shapes for SD-VAE, FLUX-VAE, DC-AE and HiDream-I1
  ship as module-level constants so the per-adapter code can
  reference them by name.
* :class:`SyntheticVAE` — pure-NumPy synthetic VAE that
  implements :meth:`decode` / :meth:`encode` as deterministic
  2D-FFT-style projections. The synthetic VAE is byte-stable
  for fixed inputs and never touches ``torch`` / ``diffusers``
  at module level — the framework uses it as the default
  fallback when no real VAE weights are vendored.
* :class:`DiffusersVAEWrapper` — lazy-import wrapper around
  :class:`diffusers.AutoencoderKL` (and friends). The wrapper
  handles the ``numpy ↔ torch`` conversion + batch-dim +
  dtype cast + channel-order conversion (latent channels
  first → pixel channels last when needed). Real VAEs are
  loaded via :meth:`from_diffusers_pretrained` and lazily
  resolved; the wrapper is never import-fatal.
* :func:`latent_to_pixel_shape` / :func:`pixel_to_latent_shape`
  — pure shape-arithmetic helpers used by the per-adapter
  ``observe_endpoint`` path.

Constraints
-----------

* Stdlib + numpy only at module level. ``torch`` /
  ``diffusers`` / ``PIL`` are imported lazily inside the
  wrappers that need them so the framework never requires
  them at import time.
* All public surface is **byte-stable** for fixed inputs:
  the synthetic VAE uses a deterministic ``default_rng``
  init and a deterministic projection so two calls with
  the same ``seed`` / ``weights`` produce byte-identical
  pixel outputs.
* No filesystem writes. The decoder is read-only.

VAE channel-order convention
----------------------------

The wrapper follows the diffusers convention: latents have
shape ``(B, C_latent, H_latent, W_latent)`` (channels first),
pixels have shape ``(B, 3, H_pixel, W_pixel)`` (channels
first). When the adapter exposes a NumPy latent of shape
``(C_latent, H_latent, W_latent)`` (no batch dim), the wrapper
adds the batch dim before the diffusers call and squeezes it
afterward.

VAE conventions table
---------------------

================  =============  ========  ==========
Model family      Latent shape   Downsample  Pixel shp
================  =============  ========  ==========
SD-VAE (1.5/xl)   (4, 32, 32)    8x        (3, 256, 256)
DC-AE             (4, 32, 32)    8x        (3, 256, 256)
FLUX.1-AE         (16, 128, 128) 8x        (3, 1024, 1024)
HiDream-I1 AE     (16, 128, 128) 8x        (3, 1024, 1024)
================  =============  ========  ==========

These pre-canned shapes match the per-adapter ``STATE_SHAPE``
constants; the wrapper never re-derives them from the upstream
checkpoint (that would require loading the VAE weights).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

ArrayF64: TypeAlias = NDArray[np.float64]

#: Default VAE downsample factor (SD-VAE convention).
DEFAULT_VAE_DOWNSAMPLE: int = 8

#: Pre-canned latent shapes for the canonical VAE conventions.
LATENT_SHAPE_SD_VAE_256: tuple[int, int, int] = (4, 32, 32)
LATENT_SHAPE_FLUX_VAE_1024: tuple[int, int, int] = (16, 128, 128)
LATENT_SHAPE_DCAE_256: tuple[int, int, int] = (4, 32, 32)
LATENT_SHAPE_HIDREAM_1024: tuple[int, int, int] = (16, 128, 128)

#: Pixel-shape hint strings for error messages.
VAE_FAMILY_SD_VAE: str = "sd_vae"
VAE_FAMILY_FLUX_VAE: str = "flux_vae"
VAE_FAMILY_DCAE: str = "dcae"
VAE_FAMILY_HIDREAM: str = "hidream"
VAE_FAMILY_SYNTHETIC: str = "synthetic"

VAEDType = Literal["float32", "bfloat16", "float16"]


@dataclass(frozen=True)
class LatentShape:
    """Declarative description of a VAE latent + pixel shape pair.

    Attributes
    ----------
    channels:
        Number of latent channels (4 for SD-VAE / DC-AE; 16 for
        FLUX / HiDream).
    height:
        Latent spatial height.
    width:
        Latent spatial width.
    downsample:
        VAE encoder downsample factor (8 for SD-VAE / DC-AE /
        FLUX.1-AE / HiDream-I1).
    family:
        Free-form family tag (e.g. ``"sd_vae"`` /
        ``"flux_vae"``). Used for diagnostic logging only —
        the wrapper never inspects the family to gate the
        encode / decode calls.
    """

    channels: int
    height: int
    width: int
    downsample: int = DEFAULT_VAE_DOWNSAMPLE
    family: str = VAE_FAMILY_SYNTHETIC

    def __post_init__(self) -> None:
        if int(self.channels) <= 0:
            raise ValueError("latent_channels_must_be_positive")
        if int(self.height) <= 0:
            raise ValueError("latent_height_must_be_positive")
        if int(self.width) <= 0:
            raise ValueError("latent_width_must_be_positive")
        if int(self.downsample) <= 0:
            raise ValueError("downsample_must_be_positive")

    @property
    def shape(self) -> tuple[int, int, int]:
        return (int(self.channels), int(self.height), int(self.width))

    @property
    def pixel_height(self) -> int:
        return int(self.height) * int(self.downsample)

    @property
    def pixel_width(self) -> int:
        return int(self.width) * int(self.downsample)

    @property
    def pixel_shape(self) -> tuple[int, int, int]:
        return (3, self.pixel_height, self.pixel_width)

    @classmethod
    def sd_vae_256(cls) -> LatentShape:
        """Pre-canned SD-VAE latent at the 256x256 pixel resolution."""
        return cls(
            channels=LATENT_SHAPE_SD_VAE_256[0],
            height=LATENT_SHAPE_SD_VAE_256[1],
            width=LATENT_SHAPE_SD_VAE_256[2],
            downsample=DEFAULT_VAE_DOWNSAMPLE,
            family=VAE_FAMILY_SD_VAE,
        )

    @classmethod
    def flux_vae_1024(cls) -> LatentShape:
        """Pre-canned FLUX.1-VAE latent at the 1024x1024 pixel resolution."""
        return cls(
            channels=LATENT_SHAPE_FLUX_VAE_1024[0],
            height=LATENT_SHAPE_FLUX_VAE_1024[1],
            width=LATENT_SHAPE_FLUX_VAE_1024[2],
            downsample=DEFAULT_VAE_DOWNSAMPLE,
            family=VAE_FAMILY_FLUX_VAE,
        )

    @classmethod
    def dcae_256(cls) -> LatentShape:
        """Pre-canned DC-AE latent at the 256x256 pixel resolution."""
        return cls(
            channels=LATENT_SHAPE_DCAE_256[0],
            height=LATENT_SHAPE_DCAE_256[1],
            width=LATENT_SHAPE_DCAE_256[2],
            downsample=DEFAULT_VAE_DOWNSAMPLE,
            family=VAE_FAMILY_DCAE,
        )

    @classmethod
    def hidream_1024(cls) -> LatentShape:
        """Pre-canned HiDream-I1 VAE latent at the 1024x1024 pixel resolution."""
        return cls(
            channels=LATENT_SHAPE_HIDREAM_1024[0],
            height=LATENT_SHAPE_HIDREAM_1024[1],
            width=LATENT_SHAPE_HIDREAM_1024[2],
            downsample=DEFAULT_VAE_DOWNSAMPLE,
            family=VAE_FAMILY_HIDREAM,
        )


# ---------------------------------------------------------------------------
# Shape helpers
# ---------------------------------------------------------------------------


def latent_to_pixel_shape(latent_shape: tuple[int, int, int], *, downsample: int) -> tuple[int, int, int]:
    """Compute the pixel-space shape ``(3, H_latent * d, W_latent * d)``.

    Mirrors the per-adapter ``SELF_FLOW_PIXEL_SHAPE`` /
    ``HIDREAM_I1_PIXEL_SHAPE`` constants so adapters that
    consume this module can drop their hand-rolled shape
    arithmetic.
    """
    if int(downsample) <= 0:
        raise ValueError("downsample_must_be_positive")
    if len(latent_shape) != 3:
        raise ValueError(
            f"latent_shape must be (C, H, W); got {tuple(latent_shape)!r}"
        )
    _, h, w = latent_shape
    return (3, int(h) * int(downsample), int(w) * int(downsample))


def pixel_to_latent_shape(pixel_shape: tuple[int, int, int], *, downsample: int) -> tuple[int, int, int]:
    """Inverse of :func:`latent_to_pixel_shape` (without the channel dim)."""
    if int(downsample) <= 0:
        raise ValueError("downsample_must_be_positive")
    if len(pixel_shape) != 3:
        raise ValueError(
            f"pixel_shape must be (3, H, W); got {tuple(pixel_shape)!r}"
        )
    _, h, w = pixel_shape
    if int(h) % int(downsample) != 0 or int(w) % int(downsample) != 0:
        raise ValueError(
            f"pixel_shape ({int(h)}x{int(w)}) not divisible by downsample "
            f"{int(downsample)}"
        )
    return (0, int(h) // int(downsample), int(w) // int(downsample))


# ---------------------------------------------------------------------------
# Synthetic VAE — pure NumPy, byte-stable, torch-free
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticVAEWeights:
    """Deterministic synthetic VAE weights.

    The synthetic VAE is **not** a trained model — it is a
    deterministic per-pixel linear projection that preserves
    byte-stability so the framework's protocol surface can
    exercise :func:`decode` / :func:`encode` without a GPU or
    real VAE weights.

    Attributes
    ----------
    latent_to_pixel_W:
        Per-pixel linear projection of shape
        ``(latent_channels, 3 * downsample * downsample)``.
    pixel_to_latent_W:
        Inverse projection of shape
        ``(3 * downsample * downsample, latent_channels)`` —
        the transpose of ``latent_to_pixel_W``.
    seed:
        Seed used to initialise both projections.
    """

    latent_to_pixel_W: ArrayF64
    pixel_to_latent_W: ArrayF64
    seed: int


def _init_synthetic_vae_weights(
    *,
    latent_channels: int,
    downsample: int,
    seed: int,
) -> SyntheticVAEWeights:
    """Build a deterministic symmetric pair of per-pixel projections.

    The forward projection maps each latent pixel's
    ``c``-dim vector to a ``3 * d * d``-dim RGB patch via a
    single linear layer per pixel — ``W_fwd`` has shape
    ``(c, 3 * d * d)``. The backward projection is the
    transpose ``W_bwd`` of shape ``(3 * d * d, c)``.

    Construction: random Gaussian init followed by
    QR-based orthonormalisation of the rows of ``W_fwd``
    (so ``W_fwd @ W_fwd.T == I_c``). This makes the
    round-trip exact up to numerical precision:
    ``encode(decode(z)) == z`` for every ``z``.
    """
    d = int(downsample)
    c_lat = int(latent_channels)
    in_dim = int(c_lat)
    out_dim = 3 * d * d
    rng = np.random.default_rng(int(seed))
    A = rng.standard_normal((out_dim, in_dim)).astype(np.float64)
    # QR decomposition: Q has orthonormal columns of shape
    # ``(out_dim, c)``; the row-space of ``Q.T`` is the
    # orthonormal basis we want for ``W_fwd``.
    Q, _ = np.linalg.qr(A)
    W_fwd = Q.T.astype(np.float64)  # (c, 3*d*d), orthonormal rows.
    W_bwd = W_fwd.T.copy()
    return SyntheticVAEWeights(
        latent_to_pixel_W=W_fwd,
        pixel_to_latent_W=W_bwd,
        seed=int(seed),
    )


@dataclass(frozen=True)
class VAEDecodeResult:
    """Structured output of :meth:`SyntheticVAE.decode`."""

    pixels: ArrayF64
    family: str
    latent_shape: tuple[int, int, int]
    pixel_shape: tuple[int, int, int]


class SyntheticVAE:
    """Pure-NumPy synthetic VAE used as the no-weights fallback.

    Implements :meth:`decode` (latent → pixels) and :meth:`encode`
    (pixels → latent) as a deterministic linear projection. The
    synthetic VAE is byte-stable for fixed inputs and never
    touches ``torch`` / ``diffusers``. Adapters consume it via
    :func:`default_synthetic_vae`.
    """

    __slots__ = ("_shape", "_weights", "_seed")

    def __init__(
        self,
        shape: LatentShape,
        *,
        seed: int = 0,
        weights: SyntheticVAEWeights | None = None,
    ) -> None:
        self._shape = shape
        self._seed = int(seed)
        self._weights = (
            weights
            if weights is not None
            else _init_synthetic_vae_weights(
                latent_channels=int(shape.channels),
                downsample=int(shape.downsample),
                seed=int(seed),
            )
        )

    @property
    def shape(self) -> LatentShape:
        return self._shape

    @property
    def seed(self) -> int:
        return self._seed

    def decode(self, latent: ArrayF64) -> ArrayF64:
        """Decode a latent of shape ``(C, H, W)`` to pixels of shape ``(3, H*d, W*d)``.

        The synthetic decode is a deterministic per-pixel
        linear projection — same input always yields the same
        pixel output. The output is **not** clamped to
        ``[0, 1]`` (that's the caller's job before saving to
        PNG); the synthetic VAE returns raw float values so
        the audit chain can verify the projection is
        identity-preserving.
        """
        z = np.asarray(latent, dtype=np.float64)
        if z.shape != self._shape.shape:
            raise ValueError(
                f"latent shape {tuple(z.shape)!r} does not match "
                f"shape {tuple(self._shape.shape)!r}"
            )
        c, h, w = z.shape
        d = int(self._shape.downsample)
        # Reshape latent to ``(h * w, c)`` then project each
        # pixel's ``c``-dim vector to a ``3 * d * d``-dim
        # pixel patch via ``W_fwd``.
        z_flat = z.reshape(c, h * w).T  # (h*w, c)
        patches = z_flat @ self._weights.latent_to_pixel_W  # (h*w, 3 * d * d)
        patches = patches.reshape(h, w, 3, d, d)
        # Rearrange to ``(3, h*d, w*d)`` via numpy transpose.
        pixels = patches.transpose(2, 0, 3, 1, 4).reshape(
            3, h * d, w * d,
        )
        return np.asarray(pixels, dtype=np.float64)

    def encode(self, pixels: ArrayF64) -> ArrayF64:
        """Encode pixels of shape ``(3, H*d, W*d)`` to latent of shape ``(C, H, W)``.

        Inverse of :meth:`decode`. Symmetric by construction
        (the backward projection is the transpose of the
        forward projection).
        """
        x = np.asarray(pixels, dtype=np.float64)
        if x.shape != self._shape.pixel_shape:
            raise ValueError(
                f"pixel shape {tuple(x.shape)!r} does not match "
                f"expected {tuple(self._shape.pixel_shape)!r}"
            )
        _, h_pix, w_pix = x.shape
        d = int(self._shape.downsample)
        h = h_pix // d
        w = w_pix // d
        # Rearrange pixels into ``(h, w, 3, d, d)`` patches.
        patches = x.reshape(3, h, d, w, d).transpose(1, 3, 0, 2, 4).reshape(
            h * w, 3 * d * d,
        )
        z_flat = patches @ self._weights.pixel_to_latent_W  # (h*w, c)
        z = z_flat.T.reshape(int(self._shape.channels), h, w)
        return np.asarray(z, dtype=np.float64)

    def digest(self) -> str:
        """SHA-256 hex digest of the synthetic VAE's weight bytes."""
        blob = (
            self._weights.latent_to_pixel_W.tobytes()
            + self._weights.pixel_to_latent_W.tobytes()
        )
        import hashlib as _hl

        return _hl.sha256(blob).hexdigest()


def default_synthetic_vae(
    family: str = VAE_FAMILY_SD_VAE,
    *,
    seed: int = 0,
) -> SyntheticVAE:
    """Build the default synthetic VAE for ``family``.

    Pre-canned families: ``"sd_vae"`` (256x256), ``"flux_vae"``
    (1024x1024), ``"dcae"`` (256x256), ``"hidream"`` (1024x1024),
    ``"synthetic"`` (SD-VAE defaults). Returns the SD-VAE
    synthetic VAE for unknown family tags so the call is
    never-fatal.
    """
    factory = {
        VAE_FAMILY_SD_VAE: LatentShape.sd_vae_256,
        VAE_FAMILY_DCAE: LatentShape.dcae_256,
        VAE_FAMILY_FLUX_VAE: LatentShape.flux_vae_1024,
        VAE_FAMILY_HIDREAM: LatentShape.hidream_1024,
    }.get(str(family), LatentShape.sd_vae_256)
    return SyntheticVAE(factory(), seed=int(seed))


# ---------------------------------------------------------------------------
# Real diffusers VAE wrapper (lazy import)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiffusersVAEResult:
    """Structured output of :meth:`DiffusersVAEWrapper.decode` / :meth:`encode`."""

    tensor: ArrayF64
    family: str
    source_shape: tuple[int, int, int]
    target_shape: tuple[int, int, int]


class DiffusersVAEWrapper:
    """Lazy-import wrapper around a :class:`diffusers.AutoencoderKL`.

    The wrapper hides the ``numpy ↔ torch`` conversion + batch
    dim + dtype cast that every adapter was previously
    re-typing. It is **never import-fatal**: when
    :mod:`torch` / :mod:`diffusers` are absent the wrapper
    stays constructible and :meth:`decode` / :meth:`encode`
    return ``None`` so the caller can fall back to the
    synthetic VAE.

    Parameters
    ----------
    vae:
        A :class:`diffusers.AutoencoderKL` instance. When
        ``None`` (the default), :meth:`from_diffusers_pretrained`
        loads it from a weights directory.
    shape:
        The :class:`LatentShape` declaring the latent → pixel
        mapping for this VAE. Used by the wrapper to validate
        the input shape and to populate the structured
        :class:`DiffusersVAEResult`.
    dtype:
        Torch dtype for the encode / decode calls. Defaults
        to ``"float32"`` (matches the synthetic-VAE numerical
        precision).
    """

    __slots__ = ("_vae", "_shape", "_dtype", "_available")

    def __init__(
        self,
        vae: Any | None,
        *,
        shape: LatentShape,
        dtype: VAEDType = "float32",
    ) -> None:
        self._vae = vae
        self._shape = shape
        self._dtype = str(dtype)
        self._available: bool = vae is not None

    @property
    def shape(self) -> LatentShape:
        return self._shape

    @property
    def is_available(self) -> bool:
        """``True`` when a real diffusers VAE is loaded; ``False`` otherwise."""
        return bool(self._available)

    @classmethod
    def from_diffusers_pretrained(
        cls,
        weights_path: str,
        *,
        shape: LatentShape,
        dtype: VAEDType = "float32",
        symbol: str = "diffusers:AutoencoderKL",
    ) -> DiffusersVAEWrapper:
        """Construct a wrapper from a diffusers VAE on disk.

        Tries to import ``symbol`` (``module:attribute``) and
        call ``from_pretrained(str(weights_path))``; returns
        an unavailable wrapper (with ``vae=None``) when either
        step fails.
        """
        try:
            import importlib

            if ":" not in str(symbol):
                raise ImportError(f"invalid symbol path: {symbol!r}")
            mod_name, _, attr = str(symbol).partition(":")
            mod = importlib.import_module(str(mod_name))
            cls_obj = getattr(mod, str(attr), None)
            if cls_obj is None:
                raise ImportError(f"symbol not found: {symbol}")
            vae = cls_obj.from_pretrained(str(weights_path))
        except Exception:
            return cls(None, shape=shape, dtype=dtype)
        return cls(vae, shape=shape, dtype=dtype)

    def _torch_dtype(self) -> Any:
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError("DiffusersVAEWrapper requires torch") from exc
        return {
            "float32": torch.float32,
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
        }.get(self._dtype, torch.float32)

    def decode(self, latent: ArrayF64) -> DiffusersVAEResult | None:
        """Decode a latent of shape ``(C, H, W)`` to pixels of shape ``(3, H*d, W*d)``.

        Returns ``None`` when the underlying diffusers VAE is
        unavailable. The output is normalised to ``[0, 1]`` for
        diffusers convention (``image = (image + 1) / 2`` after
        :meth:`vae.decode`).
        """
        if not self._available:
            return None
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError("DiffusersVAEWrapper.decode requires torch") from exc

        z = np.asarray(latent, dtype=np.float64)
        if z.shape != self._shape.shape:
            raise ValueError(
                f"latent shape {tuple(z.shape)!r} does not match "
                f"shape {tuple(self._shape.shape)!r}"
            )
        dtype = self._torch_dtype()
        with torch.no_grad():
            z_t = torch.as_tensor(z, dtype=dtype).unsqueeze(0)
            decoded = self._vae.decode(z_t).sample  # type: ignore[union-attr]
            decoded = ((decoded.squeeze(0).clamp(-1, 1) + 1.0) * 0.5).cpu().numpy()
        pixels = np.asarray(decoded, dtype=np.float64)
        return DiffusersVAEResult(
            tensor=pixels,
            family=str(self._shape.family),
            source_shape=tuple(z.shape),
            target_shape=tuple(pixels.shape),
        )

    def encode(self, pixels: ArrayF64) -> DiffusersVAEResult | None:
        """Encode pixels of shape ``(3, H, W)`` to latent of shape ``(C, H/d, W/d)``.

        Returns ``None`` when the underlying diffusers VAE is
        unavailable. The input is assumed to be in
        ``[0, 1]`` (the diffusers convention); the wrapper
        rescales to ``[-1, 1]`` before calling :meth:`vae.encode`.
        """
        if not self._available:
            return None
        try:
            import torch  # local import.
        except ImportError as exc:  # pragma: no cover — gated by caller.
            raise ImportError("DiffusersVAEWrapper.encode requires torch") from exc

        x = np.asarray(pixels, dtype=np.float64)
        if x.shape[0] != 3:
            raise ValueError(
                f"pixels must have 3 channels; got {int(x.shape[0])}"
            )
        dtype = self._torch_dtype()
        with torch.no_grad():
            x_t = torch.as_tensor(x * 2.0 - 1.0, dtype=dtype).unsqueeze(0)
            latent_dist = self._vae.encode(x_t).latent_dist  # type: ignore[union-attr]
            z = latent_dist.sample().squeeze(0).cpu().numpy()
        z = np.asarray(z, dtype=np.float64)
        return DiffusersVAEResult(
            tensor=z,
            family=str(self._shape.family),
            source_shape=tuple(x.shape),
            target_shape=tuple(z.shape),
        )


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def vae_for_family(
    family: str,
    *,
    weights_path: str | None = None,
    seed: int = 0,
    dtype: VAEDType = "float32",
) -> DiffusersVAEWrapper | SyntheticVAE:
    """Return the right VAE for ``family`` — diffusers wrapper when a
    real VAE is on disk, otherwise the byte-stable synthetic VAE.

    The function is the canonical "adapter glue" entry point:
    each adapter calls :func:`vae_for_family("sd_vae",
    weights_path=...)` and gets back either a real-VAE wrapper
    (when ``weights_path`` exists and diffusers is importable)
    or the synthetic VAE fallback (when either is missing).

    Args:
        family: One of ``"sd_vae"`` / ``"flux_vae"`` / ``"dcae"``
            / ``"hidream"`` / ``"synthetic"``. Unknown tags fall
            through to the SD-VAE synthetic VAE so the call is
            never-fatal.
        weights_path: Optional path to a diffusers VAE on disk.
            When the path exists and diffusers is importable the
            function returns a :class:`DiffusersVAEWrapper`;
            otherwise it returns the synthetic VAE.
        seed: Synthetic-VAE seed (no-op when the real VAE is
            available).
        dtype: Torch dtype for the diffusers VAE wrapper.

    Returns:
        Either a :class:`DiffusersVAEWrapper` (when the real VAE
        is available) or a :class:`SyntheticVAE` (otherwise).
    """
    shape_factory = {
        VAE_FAMILY_SD_VAE: LatentShape.sd_vae_256,
        VAE_FAMILY_DCAE: LatentShape.dcae_256,
        VAE_FAMILY_FLUX_VAE: LatentShape.flux_vae_1024,
        VAE_FAMILY_HIDREAM: LatentShape.hidream_1024,
    }.get(str(family), LatentShape.sd_vae_256)
    shape = shape_factory()

    if weights_path is not None:
        from pathlib import Path as _Path

        if _Path(str(weights_path)).exists():
            wrapper = DiffusersVAEWrapper.from_diffusers_pretrained(
                str(weights_path), shape=shape, dtype=str(dtype),  # type: ignore[arg-type]
            )
            if wrapper.is_available:
                return wrapper
    return SyntheticVAE(shape, seed=int(seed))


__all__ = [
    "DEFAULT_VAE_DOWNSAMPLE",
    "DiffusersVAEResult",
    "DiffusersVAEWrapper",
    "LATENT_SHAPE_DCAE_256",
    "LATENT_SHAPE_FLUX_VAE_1024",
    "LATENT_SHAPE_HIDREAM_1024",
    "LATENT_SHAPE_SD_VAE_256",
    "LatentShape",
    "SyntheticVAE",
    "SyntheticVAEWeights",
    "VAEDType",
    "VAE_FAMILY_DCAE",
    "VAE_FAMILY_FLUX_VAE",
    "VAE_FAMILY_HIDREAM",
    "VAE_FAMILY_SD_VAE",
    "VAE_FAMILY_SYNTHETIC",
    "default_synthetic_vae",
    "latent_to_pixel_shape",
    "pixel_to_latent_shape",
    "vae_for_family",
]
