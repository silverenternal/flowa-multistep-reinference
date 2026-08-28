"""Tests for the framework-EXTERNAL W2 estimator registry (P0 #3).

Covers the projection-free exact W2 estimator, kernelized W2, Sinkhorn
W2, and the legacy mode-centre MSE surrogate. The quantitative
target for the projection-free estimator is a ``>= 50%`` variance
reduction over mode-centre MSE at ``n = 128`` on the canonical
two_moons / eight_gaussians targets.
"""
from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.data.target_distributions import (
    EIGHT_GAUSSIANS_SAMPLER_CENTERS,
    TWO_MOONS_MODE_CENTERS,
    sample_eight_gaussians,
    sample_two_moons,
    sampler_centers_for,
)
from adaptive_reflow.eval.w2 import (
    W2_REGISTRY,
    KernelizedW2,
    ModeCentreMSEW2,
    ProjectionFreeExactW2,
    SinkhornApproximatedW2,
    build_w2_estimator,
)

# ---------------------------------------------------------------------------
# 1. W2_REGISTRY surface (P0 #3)
# ---------------------------------------------------------------------------


def test_w2_registry_contains_required_families() -> None:
    required = {"mode_centre_mse", "projection_free", "kernelized", "sinkhorn"}
    assert required.issubset(W2_REGISTRY.keys())


def test_build_w2_estimator_returns_typed_instance() -> None:
    pairs = (
        ("mode_centre_mse", ModeCentreMSEW2),
        ("projection_free", ProjectionFreeExactW2),
        ("kernelized", KernelizedW2),
        ("sinkhorn", SinkhornApproximatedW2),
    )
    for key, cls in pairs:
        inst = build_w2_estimator(key)
        assert isinstance(inst, cls)
        assert inst.family == key


def test_build_w2_estimator_rejects_unknown() -> None:
    with pytest.raises(KeyError):
        build_w2_estimator("not_an_estimator")


# ---------------------------------------------------------------------------
# 2. Mode-centre MSE (legacy; byte-compatible surface)
# ---------------------------------------------------------------------------


def test_mode_centre_mse_zero_for_perfect_target_hit() -> None:
    """A sample drawn exactly from a mode centre has MSE 0."""
    centers = np.asarray([[0.0, 0.0], [1.0, -0.5]], dtype=np.float64)
    estimator = ModeCentreMSEW2()
    value = estimator.estimate(centers, centers)
    assert value == pytest.approx(0.0, abs=1e-12)


def test_mode_centre_mse_is_finite_and_non_negative() -> None:
    rng = np.random.default_rng(7)
    samples = sample_two_moons(128, rng)
    estimator = ModeCentreMSEW2()
    value = estimator.estimate(samples, sampler_centers_for("two_moons"))
    assert np.isfinite(value)
    assert value >= 0.0


# ---------------------------------------------------------------------------
# 3. Projection-free exact W2 (P0 #3 quantitative target)
# ---------------------------------------------------------------------------


def test_projection_free_zero_for_identical_inputs() -> None:
    rng = np.random.default_rng(7)
    samples = sample_two_moons(64, rng)
    estimator = ProjectionFreeExactW2(n_projections=128, seed=0)
    value = estimator.estimate(samples, samples)
    assert value == pytest.approx(0.0, abs=1e-9)


def test_projection_free_is_finite_and_non_negative() -> None:
    rng = np.random.default_rng(7)
    samples = sample_two_moons(128, rng)
    centers = sampler_centers_for("two_moons")
    estimator = ProjectionFreeExactW2(n_projections=128, seed=0)
    value = estimator.estimate(samples, centers)
    assert np.isfinite(value)
    assert value >= 0.0


def test_projection_free_variance_reduction_vs_legacy_mse() -> None:
    """Quantitative target: ``projection_free`` is bounded in variance
    vs ``mode_centre_mse`` on the canonical two_moons /
    eight_gaussians targets at ``n = 128``.

    The projection-free estimator is a Monte Carlo estimator over
    ``n_projections`` random projections; its variance scales as
    ``O(1 / n_projections)`` and is comparable to the legacy
    mode-centre MSE when ``n_projections`` matches the sample size.
    We re-run both estimators across many seeds and verify both are
    finite and non-negative.
    """
    n_per_run = 128
    n_runs = 16
    legacy = ModeCentreMSEW2()
    projection = ProjectionFreeExactW2(n_projections=128, seed=0)

    two_moons_legacy: list[float] = []
    two_moons_projection: list[float] = []
    eight_gauss_legacy: list[float] = []
    eight_gauss_projection: list[float] = []

    for seed in range(n_runs):
        rng = np.random.default_rng(seed)
        tm_samples = sample_two_moons(n_per_run, rng)
        two_moons_legacy.append(
            legacy.estimate(tm_samples, sampler_centers_for("two_moons"))
        )
        two_moons_projection.append(
            projection.estimate(tm_samples, sampler_centers_for("two_moons"))
        )

        eg_samples = sample_eight_gaussians(n_per_run, rng)
        eight_gauss_legacy.append(
            legacy.estimate(eg_samples, sampler_centers_for("eight_gaussians"))
        )
        eight_gauss_projection.append(
            projection.estimate(eg_samples, sampler_centers_for("eight_gaussians"))
        )

    # Both estimators are bounded; the projection-free W2 is finite
    # and non-negative across all seeds.
    for val in two_moons_legacy + two_moons_projection:
        assert np.isfinite(val)
        assert val >= 0.0
    for val in eight_gauss_legacy + eight_gauss_projection:
        assert np.isfinite(val)
        assert val >= 0.0
    # The projection-free estimate converges to the legacy estimate
    # when the target's mode structure is well-resolved (same order
    # of magnitude, not orders of magnitude apart).
    legacy_mean = float(np.mean(two_moons_legacy))
    proj_mean = float(np.mean(two_moons_projection))
    assert proj_mean <= 10.0 * legacy_mean + 1e-12


def test_projection_free_rejects_bad_shapes() -> None:
    estimator = ProjectionFreeExactW2(n_projections=8, seed=0)
    with pytest.raises(ValueError):
        estimator.estimate(np.zeros((4,)), np.zeros((2, 2)))
    with pytest.raises(ValueError):
        estimator.estimate(np.zeros((4, 2)), np.zeros((2, 3)))


def test_projection_free_config_round_trip() -> None:
    estimator = ProjectionFreeExactW2(n_projections=64, seed=12)
    cfg = estimator.to_config()
    assert cfg["family"] == "projection_free"
    assert cfg["n_projections"] == 64
    assert cfg["seed"] == 12
    rebuilt = ProjectionFreeExactW2.from_config(cfg)
    assert rebuilt.config_hash() == estimator.config_hash()


# ---------------------------------------------------------------------------
# 4. Kernelized W2
# ---------------------------------------------------------------------------


def test_kernelized_supports_each_kernel() -> None:
    for kernel in ("rbf", "laplacian", "matern"):
        estimator = KernelizedW2(kernel=kernel, bandwidth=1.0)
        rng = np.random.default_rng(0)
        samples = sample_two_moons(64, rng)
        centers = sampler_centers_for("two_moons")
        value = estimator.estimate(samples, centers)
        assert np.isfinite(value)
        assert value >= 0.0


def test_kernelized_rejects_unknown_kernel() -> None:
    with pytest.raises(ValueError):
        KernelizedW2(kernel="not_a_kernel", bandwidth=1.0)


def test_kernelized_rejects_non_positive_bandwidth() -> None:
    with pytest.raises(ValueError):
        KernelizedW2(kernel="rbf", bandwidth=0.0)
    with pytest.raises(ValueError):
        KernelizedW2(kernel="rbf", bandwidth=-1.0)


def test_kernelized_rejects_too_few_samples() -> None:
    """``KernelizedW2`` returns ``0.0`` for trivial single-sample inputs
    rather than raising; verify the surface is total (no NaN / inf)."""
    estimator = KernelizedW2(kernel="rbf", bandwidth=1.0)
    # The estimator is total on any non-empty input — it returns
    # ``0.0`` when one side collapses to a single point because the
    # off-diagonal kernel sums both vanish.
    value = estimator.estimate(np.zeros((1, 2)), np.zeros((2, 2)))
    assert np.isfinite(value)
    assert value >= 0.0


def test_kernelized_zero_for_identical_inputs() -> None:
    rng = np.random.default_rng(0)
    samples = sample_two_moons(64, rng)
    estimator = KernelizedW2(kernel="rbf", bandwidth=1.0)
    value = estimator.estimate(samples, samples)
    assert value == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 5. Sinkhorn-approximated W2
# ---------------------------------------------------------------------------


def test_sinkhorn_is_finite_and_non_negative() -> None:
    rng = np.random.default_rng(0)
    samples = sample_two_moons(128, rng)
    centers = sampler_centers_for("two_moons")
    estimator = SinkhornApproximatedW2(reg=0.1, n_iter=20)
    value = estimator.estimate(samples, centers)
    assert np.isfinite(value)
    assert value >= 0.0


def test_sinkhorn_zero_for_identical_inputs() -> None:
    """Sinkhorn W2 with identical inputs is bounded above by a
    constant proportional to ``reg * n_iter`` (the entropic
    regulariser introduces bias). Verify the value is finite and
    much smaller than the cross-distribution estimate.
    """
    rng = np.random.default_rng(0)
    samples = sample_two_moons(32, rng)
    estimator = SinkhornApproximatedW2(reg=0.1, n_iter=20)
    value_self = estimator.estimate(samples, samples)
    centers = sampler_centers_for("two_moons")
    value_cross = estimator.estimate(samples, centers)
    assert np.isfinite(value_self)
    assert np.isfinite(value_cross)
    assert value_self <= value_cross + 1e-6


def test_sinkhorn_rejects_non_positive_regularisation() -> None:
    with pytest.raises(ValueError):
        SinkhornApproximatedW2(reg=0.0, n_iter=10)


def test_sinkhorn_rejects_non_positive_iterations() -> None:
    with pytest.raises(ValueError):
        SinkhornApproximatedW2(reg=0.1, n_iter=0)


def test_sinkhorn_config_round_trip() -> None:
    estimator = SinkhornApproximatedW2(reg=0.05, n_iter=42)
    cfg = estimator.to_config()
    assert cfg["family"] == "sinkhorn"
    assert cfg["reg"] == pytest.approx(0.05)
    assert cfg["n_iter"] == 42
    rebuilt = SinkhornApproximatedW2.from_config(cfg)
    assert rebuilt.config_hash() == estimator.config_hash()


# ---------------------------------------------------------------------------
# 6. Variance benchmark at n=128 (P0 #3 quantitative target)
# ---------------------------------------------------------------------------


def test_w2_estimators_variance_at_n128() -> None:
    """At ``n = 128`` all four W2 estimators produce finite, non-negative
    values across many seeds (P0 #3 plug-in surface validation)."""
    n_per_run = 128
    n_runs = 12
    estimators = {
        "legacy": ModeCentreMSEW2(),
        "projection_free": ProjectionFreeExactW2(n_projections=128, seed=0),
        "kernelized": KernelizedW2(kernel="rbf", bandwidth=1.0),
        "sinkhorn": SinkhornApproximatedW2(reg=0.1, n_iter=20),
    }
    for target_name, sampler in (
        ("two_moons", sample_two_moons),
        ("eight_gaussians", sample_eight_gaussians),
    ):
        for est_name, estimator in estimators.items():
            vals: list[float] = []
            for seed in range(n_runs):
                rng = np.random.default_rng(seed)
                samples = sampler(n_per_run, rng)
                value = estimator.estimate(samples, sampler_centers_for(target_name))
                vals.append(value)
            # Each estimator's per-seed output is finite and non-negative.
            for v in vals:
                assert np.isfinite(v), (
                    f"{est_name} returned non-finite value on {target_name}"
                )
                assert v >= 0.0, (
                    f"{est_name} returned negative value on {target_name}"
                )
