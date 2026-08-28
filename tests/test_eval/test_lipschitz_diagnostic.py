"""Bounded-Lipschitz convergence diagnostic for the selection ratio."""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.eval.lipschitz_diagnostic import (
    LipschitzConvergenceReport,
    bounded_lipschitz_distance,
    evaluate_lipschitz_convergence,
    lipschitz_modulus,
)

N_ENDPOINTS = 128


def _converged_series(n: int = 20) -> list[float]:
    """A smooth, monotone approach to ~0.95 — the Theorem-1 shape."""
    return [0.5 + 0.45 * (1.0 - math.exp(-i / 3.0)) for i in range(n)]


def _oscillating_series(n: int = 21) -> list[float]:
    """Same terminal level, but the tail never settles."""
    return [0.95 + 0.06 * (-1.0) ** i for i in range(n)]


# ---------------------------------------------------------------------------
# lipschitz_modulus
# ---------------------------------------------------------------------------


def test_modulus_of_a_constant_series_is_zero() -> None:
    assert lipschitz_modulus([0.4] * 10) == pytest.approx(0.0)


def test_modulus_of_a_linear_ramp_equals_its_slope() -> None:
    """A ramp from 0 to 1 over ``u in [0, 1]`` has modulus 1."""
    n = 11
    series = [i / (n - 1) for i in range(n)]
    assert lipschitz_modulus(series) == pytest.approx(1.0)


def test_modulus_is_cycle_length_invariant() -> None:
    """Normalising by the round spacing makes cycles comparable."""
    short = [i / 4 for i in range(5)]
    long = [i / 40 for i in range(41)]
    assert lipschitz_modulus(short) == pytest.approx(lipschitz_modulus(long))


def test_modulus_of_a_single_point_is_zero() -> None:
    assert lipschitz_modulus([0.7]) == pytest.approx(0.0)


def test_modulus_rejects_empty_and_non_finite() -> None:
    with pytest.raises(ValueError):
        lipschitz_modulus([])
    with pytest.raises(ValueError):
        lipschitz_modulus([0.1, float("nan")])
    with pytest.raises(ValueError):
        lipschitz_modulus([0.1, 0.2], spacing=0.0)


# ---------------------------------------------------------------------------
# evaluate_lipschitz_convergence — the quantitative target
# ---------------------------------------------------------------------------


def test_converged_trajectory_meets_the_monte_carlo_rate() -> None:
    """Target: tail increment <= 1/sqrt(N) at N = 128 endpoints."""
    report = evaluate_lipschitz_convergence(
        _converged_series(), n_samples=N_ENDPOINTS
    )
    assert isinstance(report, LipschitzConvergenceReport)
    assert report.rate_bound == pytest.approx(1.0 / math.sqrt(N_ENDPOINTS))
    assert report.within_rate, (
        f"tail increment {report.tail_increment:.5f} exceeded the rate bound "
        f"{report.rate_bound:.5f}"
    )
    assert report.monotone_tail


def test_oscillating_trajectory_is_rejected_at_the_same_terminal_level() -> None:
    """The whole point: level alone must not certify convergence."""
    converged = evaluate_lipschitz_convergence(
        _converged_series(), n_samples=N_ENDPOINTS
    )
    oscillating = evaluate_lipschitz_convergence(
        _oscillating_series(), n_samples=N_ENDPOINTS
    )
    assert oscillating.terminal_value >= converged.terminal_value - 0.05
    assert not oscillating.within_rate
    assert not oscillating.monotone_tail
    assert oscillating.tail_modulus > converged.tail_modulus


def test_rate_bound_tightens_as_the_population_grows() -> None:
    small = evaluate_lipschitz_convergence(_converged_series(), n_samples=16)
    large = evaluate_lipschitz_convergence(_converged_series(), n_samples=1024)
    assert large.rate_bound < small.rate_bound


def test_tail_fraction_selects_the_asymptotic_window() -> None:
    """A trajectory that is rough early but smooth late passes on the tail."""
    series = [0.1, 0.9, 0.2, 0.95] + [0.95 + 0.0005 * i for i in range(16)]
    whole = evaluate_lipschitz_convergence(
        series, n_samples=N_ENDPOINTS, tail_fraction=1.0
    )
    tail_only = evaluate_lipschitz_convergence(
        series, n_samples=N_ENDPOINTS, tail_fraction=0.5
    )
    assert not whole.within_rate
    assert tail_only.within_rate


def test_as_metrics_is_flat_and_numeric() -> None:
    metrics = evaluate_lipschitz_convergence(
        _converged_series(), n_samples=N_ENDPOINTS
    ).as_metrics()
    assert set(metrics) == {
        "lipschitz_modulus",
        "lipschitz_tail_modulus",
        "lipschitz_tail_increment",
        "lipschitz_rate_bound",
        "lipschitz_within_rate",
        "lipschitz_terminal_value",
        "lipschitz_monotone_tail",
    }
    assert all(isinstance(v, float) for v in metrics.values())


def test_evaluate_rejects_bad_parameters() -> None:
    series = _converged_series()
    with pytest.raises(ValueError):
        evaluate_lipschitz_convergence(series, n_samples=0)
    with pytest.raises(ValueError):
        evaluate_lipschitz_convergence(series, n_samples=128, tail_fraction=0.0)
    with pytest.raises(ValueError):
        evaluate_lipschitz_convergence(series, n_samples=128, tail_fraction=1.5)
    with pytest.raises(ValueError):
        evaluate_lipschitz_convergence(series, n_samples=128, constant=0.0)


# ---------------------------------------------------------------------------
# bounded_lipschitz_distance
# ---------------------------------------------------------------------------


def test_bounded_lipschitz_distance_is_zero_for_identical_samples() -> None:
    rng = np.random.default_rng(0)
    sample = rng.normal(size=256)
    assert bounded_lipschitz_distance(sample, sample) == pytest.approx(0.0, abs=1e-12)


def test_bounded_lipschitz_distance_grows_with_separation() -> None:
    rng = np.random.default_rng(0)
    base = rng.normal(size=512)
    values = [bounded_lipschitz_distance(base, base + s) for s in (0.0, 0.25, 0.5, 1.0)]
    assert values == sorted(values)


def test_bounded_lipschitz_distance_caps_outlier_influence() -> None:
    """One escaped point must not dominate, unlike an unbounded W1."""
    rng = np.random.default_rng(1)
    base = rng.normal(size=256)
    contaminated = base.copy()
    contaminated[0] = 1e6
    distance = bounded_lipschitz_distance(base, contaminated, bound=2.0)
    assert distance <= 2.0


def test_bounded_lipschitz_distance_handles_unequal_sizes() -> None:
    rng = np.random.default_rng(2)
    small = rng.normal(size=37)
    large = rng.normal(size=311)
    value = bounded_lipschitz_distance(small, large)
    assert math.isfinite(value)
    assert value >= 0.0


def test_bounded_lipschitz_distance_rejects_bad_bound() -> None:
    with pytest.raises(ValueError):
        bounded_lipschitz_distance([0.0, 1.0], [0.0, 1.0], bound=0.0)
