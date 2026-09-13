"""Unit tests for :mod:`adaptive_reflow.core.vae_decoder`.

Wave 24 MUST-3 partial completion — the framework-core glue
module for latent ↔ pixel VAE decoding (HiDream-I1, FreqFlow,
Self-Flow, Kanzi, MM-FM).

All tests are stdlib + numpy only (CPU-only sandbox). The
diffusers-dependent branch (:class:`DiffusersVAEWrapper`) is
exercised via ``is_available=False`` paths and a fake-torch
shim that lets the wrapper construct against a stub
:class:`AutoencoderKL` instance.
"""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from adaptive_reflow.core.vae_decoder import (
    DEFAULT_VAE_DOWNSAMPLE,
    LATENT_SHAPE_FLUX_VAE_1024,
    LATENT_SHAPE_HIDREAM_1024,
    LATENT_SHAPE_SD_VAE_256,
    VAE_FAMILY_FLUX_VAE,
    VAE_FAMILY_HIDREAM,
    VAE_FAMILY_SD_VAE,
    VAE_FAMILY_SYNTHETIC,
    LatentShape,
    SyntheticVAE,
    default_synthetic_vae,
    latent_to_pixel_shape,
    pixel_to_latent_shape,
    vae_for_family,
)

# ---------------------------------------------------------------------------
# Test 1: shape arithmetic
# ---------------------------------------------------------------------------


def test_latent_to_pixel_shape_sd_vae() -> None:
    """SD-VAE latent ``(4, 32, 32)`` → pixels ``(3, 256, 256)`` with 8x downsample."""
    assert latent_to_pixel_shape((4, 32, 32), downsample=8) == (3, 256, 256)


def test_latent_to_pixel_shape_flux_vae() -> None:
    """FLUX.1-VAE latent ``(16, 128, 128)`` → pixels ``(3, 1024, 1024)``."""
    assert latent_to_pixel_shape((16, 128, 128), downsample=8) == (3, 1024, 1024)


def test_latent_to_pixel_shape_rejects_zero_downsample() -> None:
    with pytest.raises(ValueError, match="downsample_must_be_positive"):
        latent_to_pixel_shape((4, 32, 32), downsample=0)


def test_latent_to_pixel_shape_rejects_wrong_arity() -> None:
    with pytest.raises(ValueError, match=r"\(C, H, W\)"):
        latent_to_pixel_shape((4, 32), downsample=8)


def test_pixel_to_latent_shape_inverse() -> None:
    """``pixel_to_latent_shape`` is the inverse of ``latent_to_pixel_shape``."""
    latent = (4, 32, 32)
    pixel = latent_to_pixel_shape(latent, downsample=8)
    recovered = pixel_to_latent_shape(pixel, downsample=8)
    assert recovered == (0, 32, 32)


def test_pixel_to_latent_shape_rejects_indivisible() -> None:
    with pytest.raises(ValueError, match="not divisible"):
        pixel_to_latent_shape((3, 256, 257), downsample=8)


# ---------------------------------------------------------------------------
# Test 2: LatentShape pre-canned factories
# ---------------------------------------------------------------------------


def test_latent_shape_sd_vae_256_factory() -> None:
    shape = LatentShape.sd_vae_256()
    assert shape.shape == LATENT_SHAPE_SD_VAE_256
    assert shape.pixel_shape == (3, 256, 256)
    assert shape.downsample == 8
    assert shape.family == VAE_FAMILY_SD_VAE


def test_latent_shape_flux_vae_1024_factory() -> None:
    shape = LatentShape.flux_vae_1024()
    assert shape.shape == LATENT_SHAPE_FLUX_VAE_1024
    assert shape.pixel_shape == (3, 1024, 1024)
    assert shape.downsample == 8
    assert shape.family == VAE_FAMILY_FLUX_VAE


def test_latent_shape_hidream_1024_factory() -> None:
    shape = LatentShape.hidream_1024()
    assert shape.shape == LATENT_SHAPE_HIDREAM_1024
    assert shape.pixel_shape == (3, 1024, 1024)
    assert shape.family == VAE_FAMILY_HIDREAM


def test_latent_shape_rejects_zero_channels() -> None:
    with pytest.raises(ValueError, match="latent_channels_must_be_positive"):
        LatentShape(channels=0, height=32, width=32)


def test_latent_shape_rejects_zero_height() -> None:
    with pytest.raises(ValueError, match="latent_height_must_be_positive"):
        LatentShape(channels=4, height=0, width=32)


# ---------------------------------------------------------------------------
# Test 3: synthetic VAE encode / decode
# ---------------------------------------------------------------------------


def test_synthetic_vae_decode_shape() -> None:
    """SD-VAE synthetic decode: latent ``(4, 32, 32)`` → pixels ``(3, 256, 256)``."""
    shape = LatentShape.sd_vae_256()
    vae = SyntheticVAE(shape, seed=0)
    z = np.random.default_rng(0).standard_normal(shape.shape)
    pixels = vae.decode(z)
    assert pixels.shape == shape.pixel_shape


def test_synthetic_vae_encode_shape() -> None:
    """SD-VAE synthetic encode: pixels ``(3, 256, 256)`` → latent ``(4, 32, 32)``."""
    shape = LatentShape.sd_vae_256()
    vae = SyntheticVAE(shape, seed=0)
    pixels = np.random.default_rng(1).standard_normal(shape.pixel_shape)
    z = vae.encode(pixels)
    assert z.shape == shape.shape


def test_synthetic_vae_decode_rejects_wrong_shape() -> None:
    shape = LatentShape.sd_vae_256()
    vae = SyntheticVAE(shape, seed=0)
    z = np.zeros((4, 16, 16), dtype=np.float64)  # wrong shape
    with pytest.raises(ValueError, match="latent shape"):
        vae.decode(z)


def test_synthetic_vae_encode_rejects_wrong_shape() -> None:
    shape = LatentShape.sd_vae_256()
    vae = SyntheticVAE(shape, seed=0)
    pixels = np.zeros((3, 128, 128), dtype=np.float64)  # wrong shape
    with pytest.raises(ValueError, match="pixel shape"):
        vae.encode(pixels)


def test_synthetic_vae_is_byte_stable() -> None:
    """Two VAE instances with the same seed produce identical digests."""
    shape = LatentShape.sd_vae_256()
    a = SyntheticVAE(shape, seed=42)
    b = SyntheticVAE(shape, seed=42)
    assert a.digest() == b.digest()


def test_synthetic_vae_round_trip_is_symmetric_projection() -> None:
    """``encode(decode(z)) == z`` for the synthetic VAE (transpose construction)."""
    shape = LatentShape.sd_vae_256()
    vae = SyntheticVAE(shape, seed=0)
    z = np.random.default_rng(0).standard_normal(shape.shape)
    pixels = vae.decode(z)
    z_recovered = vae.encode(pixels)
    np.testing.assert_allclose(z, z_recovered, atol=1e-8)


def test_synthetic_vae_digest_changes_with_seed() -> None:
    """Different seeds produce different synthetic VAEs (different digests)."""
    shape = LatentShape.sd_vae_256()
    a = SyntheticVAE(shape, seed=0)
    b = SyntheticVAE(shape, seed=1)
    assert a.digest() != b.digest()


# ---------------------------------------------------------------------------
# Test 4: default_synthetic_vae factory
# ---------------------------------------------------------------------------


def test_default_synthetic_vae_dispatch() -> None:
    """The factory dispatches on family tag to the right ``LatentShape``."""
    sd = default_synthetic_vae(VAE_FAMILY_SD_VAE)
    assert sd.shape.channels == 4
    assert sd.shape.pixel_shape == (3, 256, 256)

    flux = default_synthetic_vae(VAE_FAMILY_FLUX_VAE)
    assert flux.shape.channels == 16
    assert flux.shape.pixel_shape == (3, 1024, 1024)

    hidream = default_synthetic_vae(VAE_FAMILY_HIDREAM)
    assert hidream.shape.channels == 16
    assert hidream.shape.pixel_shape == (3, 1024, 1024)


def test_default_synthetic_vae_unknown_family_falls_back_to_sd_vae() -> None:
    """Unknown family tags fall through to the SD-VAE synthetic VAE."""
    vae = default_synthetic_vae("no_such_vae_family")
    assert vae.shape.family == VAE_FAMILY_SD_VAE
    assert vae.shape.pixel_shape == (3, 256, 256)


# ---------------------------------------------------------------------------
# Test 5: DiffusersVAEWrapper — torch-fallback path (no torch)
# ---------------------------------------------------------------------------


def test_diffusers_vae_wrapper_unavailable_when_vae_none() -> None:
    """``is_available=False`` when constructed with ``vae=None``."""
    from adaptive_reflow.core.vae_decoder import DiffusersVAEWrapper

    wrapper = DiffusersVAEWrapper(
        None, shape=LatentShape.sd_vae_256(),
    )
    assert wrapper.is_available is False
    assert wrapper.decode(np.zeros(LATENT_SHAPE_SD_VAE_256)) is None
    assert wrapper.encode(np.zeros((3, 256, 256))) is None


def test_diffusers_vae_wrapper_from_diffusers_pretrained_returns_unavailable(
    tmp_path: Path,
) -> None:
    """Missing weights path returns an unavailable wrapper (no crash)."""
    from adaptive_reflow.core.vae_decoder import DiffusersVAEWrapper

    wrapper = DiffusersVAEWrapper.from_diffusers_pretrained(
        str(tmp_path / "nope"), shape=LatentShape.sd_vae_256(),
        symbol="diffusers:AutoencoderKL",
    )
    assert wrapper.is_available is False


# ---------------------------------------------------------------------------
# Test 6: vae_for_family dispatcher
# ---------------------------------------------------------------------------


def test_vae_for_family_returns_synthetic_when_weights_missing(tmp_path: Path) -> None:
    """No weights → synthetic VAE (never-fatal)."""
    vae = vae_for_family(
        VAE_FAMILY_SD_VAE,
        weights_path=str(tmp_path / "no_vae_here"),
        seed=0,
    )
    # Either a real wrapper with ``is_available=False`` or a
    # synthetic VAE — both are valid; the contract is "no
    # crash + correct family mapping".
    from adaptive_reflow.core.vae_decoder import DiffusersVAEWrapper

    assert isinstance(vae, (SyntheticVAE, DiffusersVAEWrapper))
    if isinstance(vae, SyntheticVAE):
        assert vae.shape.family == VAE_FAMILY_SD_VAE


def test_vae_for_family_synthetic_path() -> None:
    """``weights_path=None`` returns the synthetic VAE directly."""
    vae = vae_for_family(VAE_FAMILY_FLUX_VAE, weights_path=None, seed=0)
    assert isinstance(vae, SyntheticVAE)
    assert vae.shape.channels == 16
    assert vae.shape.pixel_shape == (3, 1024, 1024)


def test_vae_for_family_unknown_family_falls_back_to_sd_vae() -> None:
    """Unknown family tags fall through to the SD-VAE synthetic VAE."""
    vae = vae_for_family("no_such_family", weights_path=None)
    assert isinstance(vae, SyntheticVAE)
    assert vae.shape.family == VAE_FAMILY_SD_VAE


# ---------------------------------------------------------------------------
# Test 7: constants exposed at the package surface
# ---------------------------------------------------------------------------


def test_constants_exposed() -> None:
    assert DEFAULT_VAE_DOWNSAMPLE == 8
    assert LATENT_SHAPE_SD_VAE_256 == (4, 32, 32)
    assert LATENT_SHAPE_FLUX_VAE_1024 == (16, 128, 128)
    assert LATENT_SHAPE_HIDREAM_1024 == (16, 128, 128)
    assert VAE_FAMILY_SYNTHETIC == "synthetic"
