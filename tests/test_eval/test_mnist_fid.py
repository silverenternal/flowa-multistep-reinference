"""Smoke tests for :mod:`adaptive_reflow.eval.mnist_fid` (EXP-1).

The FID evaluator computes a Fréchet-style distance in a fixed
random-projection feature space; the absolute numbers are not
literature-comparable but the *relative* comparison across rounds
captures the empirical claim that the multi-round framework improves
sample quality.

Tests
-----

* ``test_evaluator_loads_and_has_reference_features`` -- the evaluator
  constructs against the canonical ``data/mnist_cache`` and exposes a
  10K-row reference feature matrix.
* ``test_score_population_returns_finite_for_real_digits`` -- scoring
  the actual MNIST test images against themselves returns ``0.0`` (or
  very small) FID since the means / covariances match.
* ``test_score_population_distinguishes_real_from_noise`` -- the FID
  of real MNIST images is strictly lower than the FID of matched
  Gaussian noise (the discriminator sanity check).
* ``test_random_projection_is_deterministic`` -- two evaluators with
  the same seed yield identical projection matrices.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def test_random_projection_is_deterministic() -> None:
    """Two evaluators constructed with the same seed produce identical projections."""
    from adaptive_reflow.eval.mnist_fid import MnistFidEvaluator

    cache = Path("data/mnist_cache")
    if not (cache / "MNIST" / "raw").exists():
        pytest.skip(f"MNIST cache not populated at {cache}")
    a = MnistFidEvaluator(cache_dir=cache, seed=42, feature_dim=64)
    b = MnistFidEvaluator(cache_dir=cache, seed=42, feature_dim=64)
    assert np.array_equal(a.projection, b.projection)
    assert a.feature_dim == 64


def test_evaluator_loads_and_has_reference_features() -> None:
    """Evaluator exposes a 10K-row reference feature matrix of shape ``(10000, feature_dim)``."""
    from adaptive_reflow.eval.mnist_fid import MnistFidEvaluator

    cache = Path("data/mnist_cache")
    if not (cache / "MNIST" / "raw").exists():
        pytest.skip(f"MNIST cache not populated at {cache}")
    ev = MnistFidEvaluator(cache_dir=cache, seed=42, feature_dim=64)
    feats = ev.ref_features
    assert feats.shape == (10_000, 64)
    assert np.all(np.isfinite(feats))


def test_score_population_returns_finite_for_real_digits() -> None:
    """Scoring the canonical MNIST test images returns a finite, small FID."""
    from adaptive_reflow.adapters.mnist_fm_train import _load_mnist
    from adaptive_reflow.eval.mnist_fid import MnistFidEvaluator

    cache = Path("data/mnist_cache")
    if not (cache / "MNIST" / "raw").exists():
        pytest.skip(f"MNIST cache not populated at {cache}")
    images = np.asarray(_load_mnist("test", cache_dir=cache), dtype=np.float64)
    ev = MnistFidEvaluator(cache_dir=cache, seed=42, feature_dim=64)
    result = ev.score_population(images)
    # The reference IS the test set, so the FID is small (not exactly 0
    # because the 10K samples are scored against the full 10K reference).
    assert np.isfinite(result["fid"])
    assert result["fid"] < 5.0, f"self-FID unexpectedly large: {result['fid']}"


def test_score_population_distinguishes_real_from_noise() -> None:
    """Real MNIST images score below Gaussian noise of equal shape."""
    from adaptive_reflow.adapters.mnist_fm_train import _load_mnist
    from adaptive_reflow.eval.mnist_fid import MnistFidEvaluator

    cache = Path("data/mnist_cache")
    if not (cache / "MNIST" / "raw").exists():
        pytest.skip(f"MNIST cache not populated at {cache}")
    images = np.asarray(_load_mnist("test", cache_dir=cache), dtype=np.float64)
    ev = MnistFidEvaluator(cache_dir=cache, seed=42, feature_dim=64)
    real = ev.score_population(images)
    # Build a Gaussian-noise population of identical shape.
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(images.shape).astype(np.float64)
    np.clip(noise, -1.0, 1.0, out=noise)
    noisy = ev.score_population(noise)
    assert real["fid"] < noisy["fid"], (
        f"real FID ({real['fid']:.3f}) is not below noise FID ({noisy['fid']:.3f}); "
        f"the discriminator sanity check failed"
    )
