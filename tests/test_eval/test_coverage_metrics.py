"""Weighted Voronoi coverage + bootstrapped energy distance."""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.eval.coverage import (
    EnergyDistanceEstimate,
    energy_distance_point,
    energy_distance_with_ci,
    weighted_coverage_score,
)
from adaptive_reflow.eval.twodim_fm_evaluator import coverage_score, voronoi_grid

MODE_CENTERS = np.asarray([[0.5, 0.0], [-0.5, 0.0]], dtype=np.float64)


def _grid() -> np.ndarray:
    return voronoi_grid("two_moons")


def _sparse_population() -> np.ndarray:
    """Two points, one per mode — touches every mode, fills nothing."""
    rng = np.random.default_rng(0)
    return MODE_CENTERS + rng.normal(0.0, 0.02, size=MODE_CENTERS.shape)


def _dense_population(n_per_mode: int = 200) -> np.ndarray:
    rng = np.random.default_rng(1)
    return np.concatenate(
        [
            MODE_CENTERS[i] + rng.normal(0.0, 0.35, size=(n_per_mode, 2))
            for i in range(MODE_CENTERS.shape[0])
        ]
    )


# ---------------------------------------------------------------------------
# Weighted coverage
# ---------------------------------------------------------------------------


def test_weighted_coverage_is_a_unit_interval_score() -> None:
    value = weighted_coverage_score(_dense_population(), _grid(), MODE_CENTERS)
    assert 0.0 <= value <= 1.0


def test_weighted_coverage_discriminates_where_binary_saturates() -> None:
    """Quantitative target: >= 0.2 separation where binary coverage is flat."""
    grid = _grid()
    sparse = _sparse_population()
    dense = _dense_population()

    binary_sparse = coverage_score(sparse, dense, grid, MODE_CENTERS)
    binary_dense = coverage_score(dense, dense, grid, MODE_CENTERS)
    assert binary_sparse == pytest.approx(binary_dense), (
        "precondition: the binary metric must be saturated for this pair"
    )

    weighted_sparse = weighted_coverage_score(sparse, grid, MODE_CENTERS)
    weighted_dense = weighted_coverage_score(dense, grid, MODE_CENTERS)
    separation = weighted_dense - weighted_sparse
    assert separation >= 0.20, (
        f"weighted coverage separated the sparse and dense populations by "
        f"only {separation:.4f} (sparse={weighted_sparse:.4f}, "
        f"dense={weighted_dense:.4f})"
    )


def test_weighted_coverage_is_monotone_in_population_size() -> None:
    grid = _grid()
    rng = np.random.default_rng(7)
    pool = np.concatenate(
        [MODE_CENTERS[i] + rng.normal(0.0, 0.3, size=(300, 2)) for i in range(2)]
    )
    scores = [
        weighted_coverage_score(pool[:n], grid, MODE_CENTERS)
        for n in (10, 50, 200, 600)
    ]
    assert scores == sorted(scores)


def test_weighted_coverage_zero_for_far_away_population() -> None:
    far = np.full((16, 2), 1e3, dtype=np.float64)
    assert weighted_coverage_score(far, _grid(), MODE_CENTERS) == pytest.approx(0.0)


def test_weighted_coverage_is_deterministic() -> None:
    grid = _grid()
    pop = _dense_population()
    assert weighted_coverage_score(pop, grid, MODE_CENTERS) == weighted_coverage_score(
        pop, grid, MODE_CENTERS
    )


def test_weighted_coverage_rejects_bad_inputs() -> None:
    grid = _grid()
    with pytest.raises(ValueError):
        weighted_coverage_score(np.zeros(4), grid, MODE_CENTERS)
    with pytest.raises(ValueError):
        weighted_coverage_score(np.zeros((4, 3)), grid, MODE_CENTERS)
    with pytest.raises(ValueError):
        weighted_coverage_score(np.zeros((4, 2)), grid, MODE_CENTERS, radius=0.0)


# ---------------------------------------------------------------------------
# Energy distance + bootstrap CI
# ---------------------------------------------------------------------------


def test_energy_distance_is_zero_for_identical_samples() -> None:
    rng = np.random.default_rng(0)
    pts = rng.normal(size=(64, 2))
    assert energy_distance_point(pts, pts) == pytest.approx(0.0, abs=1e-12)


def test_energy_distance_grows_with_separation() -> None:
    rng = np.random.default_rng(0)
    base = rng.normal(size=(128, 2))
    values = [
        energy_distance_point(base, base + shift) for shift in (0.0, 0.5, 1.0, 2.0)
    ]
    assert values == sorted(values)


def test_energy_distance_ci_brackets_the_point_estimate() -> None:
    rng = np.random.default_rng(5)
    x = rng.normal(0.0, 1.0, size=(128, 2))
    y = rng.normal(1.0, 1.0, size=(128, 2))
    est = energy_distance_with_ci(x, y, n_bootstrap=200, seed=3)
    assert isinstance(est, EnergyDistanceEstimate)
    assert est.lower <= est.point <= est.upper
    assert est.width >= 0.0


def test_energy_distance_ci_is_deterministic_in_seed() -> None:
    rng = np.random.default_rng(5)
    x = rng.normal(0.0, 1.0, size=(64, 2))
    y = rng.normal(0.8, 1.0, size=(64, 2))
    first = energy_distance_with_ci(x, y, n_bootstrap=100, seed=11)
    second = energy_distance_with_ci(x, y, n_bootstrap=100, seed=11)
    assert first == second


def test_energy_distance_ci_relative_width_target() -> None:
    """Quantitative target: <= 20 % relative CI width on the distance scale.

    Conditions: ``n = 256`` per side, ``1000`` resamples, separation of
    ``1.5`` standard deviations.
    """
    rng = np.random.default_rng(3)
    x = rng.normal(0.0, 1.0, size=(256, 2))
    y = rng.normal(1.5, 1.0, size=(256, 2))
    est = energy_distance_with_ci(x, y, n_bootstrap=1000, seed=1)
    assert est.relative_width_distance <= 0.20, (
        f"95% CI relative width {est.relative_width_distance:.4f} "
        f"exceeded the 0.20 target (distance={est.distance:.4f})"
    )


def test_energy_distance_ci_rejects_bad_parameters() -> None:
    x = np.zeros((4, 2))
    with pytest.raises(ValueError):
        energy_distance_with_ci(x, x, n_bootstrap=0)
    with pytest.raises(ValueError):
        energy_distance_with_ci(x, x, confidence=1.0)
    with pytest.raises(ValueError):
        energy_distance_with_ci(x, x, seed=1.5)  # type: ignore[arg-type]


def test_energy_distance_relative_width_fails_closed_on_zero_point() -> None:
    rng = np.random.default_rng(0)
    pts = rng.normal(size=(32, 2))
    est = energy_distance_with_ci(pts, pts, n_bootstrap=20, seed=0)
    assert est.relative_width == float("inf")
    assert est.relative_width_distance == float("inf")
