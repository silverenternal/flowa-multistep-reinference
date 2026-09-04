"""Bounded-Lipschitz convergence diagnostic for the selection ratio."""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.eval.lipschitz_diagnostic import (
    PLANAR_BL_CONSTANT,
    LipschitzConvergenceReport,
    bounded_lipschitz_distance,
    bounded_lipschitz_distance_2d,
    evaluate_lipschitz_convergence,
    lipschitz_modulus,
    planar_bl_convergence_witness,
    sample_planar_limit,
    sample_planar_residual_posterior,
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


# ---------------------------------------------------------------------------
# Planar (R^2) BL distance — paper Theorem 1 (Wave 12 A1-high-3)
# ---------------------------------------------------------------------------


def _sin_profile(s: float) -> float:
    return math.sin(s)


def _quadratic_profile(s: float) -> float:
    return 0.5 * s * s


EPS_SCHEDULE = (0.5, 0.2, 0.1, 0.05, 0.01)


def test_planar_bl_distance_is_zero_on_identical_samples() -> None:
    pts = sample_planar_limit(_sin_profile, n_samples=64, seed=0)
    assert bounded_lipschitz_distance_2d(pts, pts) == pytest.approx(0.0, abs=1e-12)


def test_planar_bl_distance_is_symmetric_and_bounded() -> None:
    a = sample_planar_limit(_sin_profile, n_samples=64, seed=1)
    b = sample_planar_residual_posterior(_sin_profile, 0.3, n_samples=64, seed=2)
    ab = bounded_lipschitz_distance_2d(a, b, bound=2.0)
    ba = bounded_lipschitz_distance_2d(b, a, bound=2.0)
    assert ab == pytest.approx(ba, rel=1e-9, abs=1e-12)
    assert 0.0 <= ab <= 2.0


def test_planar_bl_distance_truncates_outliers() -> None:
    """A single escaped point cannot dominate: the cost is capped at B."""
    base = sample_planar_limit(_sin_profile, n_samples=64, seed=3)
    contaminated = base.copy()
    contaminated[0] = np.array([1e6, -1e6])
    value = bounded_lipschitz_distance_2d(base, contaminated, bound=2.0)
    assert value <= 2.0 / 64.0 + 1e-9


def test_planar_bl_distance_translation_scales_with_shift() -> None:
    """Below the truncation, BL of a rigid shift is at most the shift norm.

    Exactly the shift norm when re-matching cannot help (a measure
    concentrated at one point); at most that in general, since the
    identity coupling is one admissible transport plan.
    """
    atom = np.zeros((16, 2), dtype=float)
    assert bounded_lipschitz_distance_2d(
        atom + np.array([0.3, 0.0]), atom, bound=2.0
    ) == pytest.approx(0.3, rel=1e-9)

    base = sample_planar_limit(_sin_profile, n_samples=48, seed=4)
    shifted = base + np.array([0.3, 0.0])
    spread = bounded_lipschitz_distance_2d(shifted, base, bound=2.0)
    assert 0.0 < spread <= 0.3 + 1e-9


def test_planar_bl_distance_rejects_bad_shape_and_bound() -> None:
    pts = sample_planar_limit(_sin_profile, n_samples=8, seed=5)
    with pytest.raises(ValueError):
        bounded_lipschitz_distance_2d(pts, pts, bound=0.0)
    with pytest.raises(ValueError):
        bounded_lipschitz_distance_2d(np.zeros((4, 3)), np.zeros((4, 3)))


def test_planar_samplers_have_expected_geometry() -> None:
    """nu_g lies exactly on the sheet; mu_{g,eps} sits eps off it."""
    nu = sample_planar_limit(_quadratic_profile, n_samples=256, seed=6)
    residual_nu = nu[:, 1] - np.array([_quadratic_profile(x) for x in nu[:, 0]])
    assert np.allclose(residual_nu, 0.0, atol=1e-12)

    eps = 0.05
    mu = sample_planar_residual_posterior(
        _quadratic_profile, eps, n_samples=4096, seed=7
    )
    residual_mu = mu[:, 1] - np.array([_quadratic_profile(x) for x in mu[:, 0]])
    assert float(np.std(residual_mu)) == pytest.approx(eps, rel=0.1)
    # x-marginal is exactly N(0, 1) — mu_{g,eps} integrates y out to it.
    assert float(np.mean(mu[:, 0])) == pytest.approx(0.0, abs=0.1)
    assert float(np.std(mu[:, 0])) == pytest.approx(1.0, rel=0.1)


def test_planar_samplers_reject_bad_arguments() -> None:
    with pytest.raises(ValueError):
        sample_planar_residual_posterior(_sin_profile, 0.0, n_samples=16)
    with pytest.raises(ValueError):
        sample_planar_limit(_sin_profile, n_samples=1)


@pytest.mark.parametrize("profile", [_sin_profile, _quadratic_profile])
@pytest.mark.parametrize("seed", [0, 7, 13])
def test_theorem1_planar_bl_bound_holds(profile, seed: int) -> None:
    """Paper Theorem 1: ``BL(mu_{g,eps}, nu_g) <= C * eps`` on ``R^2``.

    The BL distance is the paper's own metric (Fortet-Mourier on the
    ambient plane), not the Gaussian-Frechet proxy on Inception
    features. ``C = sqrt(2 / pi)`` is the analytic constant of the
    synchronous coupling; the measured Monte-Carlo floor of the
    empirical estimator is added to the right-hand side.
    """
    report = planar_bl_convergence_witness(
        profile, EPS_SCHEDULE, n_samples=256, seed=seed
    )
    assert report.within_bound, report
    assert report.monotone, report
    slack = report.floor_tolerance * report.mc_floor
    for eps, bl in zip(report.eps_sequence, report.bl_distances, strict=True):
        assert bl <= PLANAR_BL_CONSTANT * eps + slack


def test_theorem1_planar_bl_detects_a_wrong_limit() -> None:
    """A displaced sheet violates the bound: the witness is not vacuous."""
    displaced = planar_bl_convergence_witness(
        lambda s: math.sin(s) + 1.0,
        EPS_SCHEDULE,
        n_samples=256,
        seed=0,
    )
    # BL is measured against nu_g of the *displaced* profile, so this
    # run must pass; the falsification is comparing mu of one profile
    # with nu of another.
    assert displaced.within_bound

    mu = sample_planar_residual_posterior(_sin_profile, 0.01, n_samples=256, seed=1)
    nu_wrong = sample_planar_limit(lambda s: math.sin(s) + 1.0, n_samples=256, seed=2)
    far = bounded_lipschitz_distance_2d(mu, nu_wrong, bound=2.0)
    assert far > PLANAR_BL_CONSTANT * 0.01 + 1.5 * displaced.mc_floor
    assert far == pytest.approx(1.0, abs=0.15)


def test_planar_bl_report_metrics_are_numeric() -> None:
    report = planar_bl_convergence_witness(
        _sin_profile, (0.2, 0.05), n_samples=128, seed=3
    )
    metrics = report.as_metrics()
    assert set(metrics) == {
        "planar_bl_min",
        "planar_bl_max",
        "planar_bl_mc_floor",
        "planar_bl_floor_tolerance",
        "planar_bl_constant",
        "planar_bl_within_bound",
        "planar_bl_monotone",
    }
    assert all(isinstance(v, float) and math.isfinite(v) for v in metrics.values())


def test_planar_bl_witness_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        planar_bl_convergence_witness(_sin_profile, ())
    with pytest.raises(ValueError):
        planar_bl_convergence_witness(_sin_profile, (0.1, -0.2))
    with pytest.raises(ValueError):
        planar_bl_convergence_witness(_sin_profile, (0.1,), floor_tolerance=0.5)
