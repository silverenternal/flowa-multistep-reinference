"""Exact binomial CDF + two-sided proportion intervals."""

from __future__ import annotations

import math
from itertools import product

import pytest

from adaptive_reflow.eval.calibration import wilson_lower_bound
from adaptive_reflow.eval.calibration_cdf import (
    ProportionInterval,
    binomial_cdf,
    binomial_sf,
    clopper_pearson_ci,
    regularized_incomplete_beta,
    wilson_ci,
)


def _exact_binomial_cdf(k: int, n: int, p: float) -> float:
    """Reference CDF by direct summation (independent of the beta identity)."""
    return sum(math.comb(n, i) * p**i * (1.0 - p) ** (n - i) for i in range(k + 1))


# ---------------------------------------------------------------------------
# binomial_cdf / binomial_sf
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 5, 20, 50])
@pytest.mark.parametrize("p", [0.05, 0.3, 0.5, 0.77, 0.99])
def test_binomial_cdf_matches_direct_summation(n: int, p: float) -> None:
    for k in range(n + 1):
        assert binomial_cdf(k, n, p) == pytest.approx(
            _exact_binomial_cdf(k, n, p), abs=1e-10
        )


def test_binomial_cdf_is_a_proper_cdf() -> None:
    values = [binomial_cdf(k, 12, 0.4) for k in range(13)]
    assert values == sorted(values)
    assert values[-1] == pytest.approx(1.0, abs=1e-12)
    assert binomial_cdf(-1, 12, 0.4) == pytest.approx(0.0)


def test_binomial_cdf_degenerate_probabilities() -> None:
    assert binomial_cdf(3, 10, 0.0) == pytest.approx(1.0)
    assert binomial_cdf(3, 10, 1.0) == pytest.approx(0.0)


def test_binomial_sf_complements_the_cdf() -> None:
    for k in range(11):
        assert binomial_cdf(k, 10, 0.35) + binomial_sf(k, 10, 0.35) == pytest.approx(
            1.0, abs=1e-12
        )


def test_binomial_cdf_rejects_bad_arguments() -> None:
    with pytest.raises(ValueError):
        binomial_cdf(1, -1, 0.5)
    with pytest.raises(ValueError):
        binomial_cdf(1, 10, 1.5)
    with pytest.raises(ValueError):
        binomial_cdf(True, 10, 0.5)  # type: ignore[arg-type]


def test_regularized_incomplete_beta_boundaries() -> None:
    assert regularized_incomplete_beta(2.0, 3.0, 0.0) == pytest.approx(0.0)
    assert regularized_incomplete_beta(2.0, 3.0, 1.0) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        regularized_incomplete_beta(0.0, 3.0, 0.5)
    with pytest.raises(ValueError):
        regularized_incomplete_beta(2.0, 3.0, 1.5)


# ---------------------------------------------------------------------------
# wilson_ci — must not drift from the existing lower bound
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 4, 17, 100])
def test_wilson_ci_lower_matches_the_existing_lower_bound(n: int) -> None:
    """Quantitative target: agreement to within 1e-12 across the panel range."""
    for k in range(n + 1):
        interval = wilson_ci(k, n, 0.95)
        assert interval.lower == pytest.approx(
            float(wilson_lower_bound(k, n, 0.95)), abs=1e-12
        )


def test_wilson_ci_brackets_the_observed_proportion() -> None:
    for n, k in product((5, 25, 90), range(0, 6)):
        if k > n:
            continue
        interval = wilson_ci(k, n, 0.95)
        assert isinstance(interval, ProportionInterval)
        assert interval.lower <= interval.point <= interval.upper
        assert 0.0 <= interval.lower <= interval.upper <= 1.0


def test_wilson_ci_narrows_as_n_grows() -> None:
    widths = [wilson_ci(n // 2, n, 0.95).width for n in (10, 40, 160, 640)]
    assert widths == sorted(widths, reverse=True)


def test_wilson_ci_empty_bucket_is_fail_closed() -> None:
    interval = wilson_ci(0, 0, 0.95)
    assert (interval.lower, interval.upper, interval.point) == (0.0, 1.0, 0.0)


# ---------------------------------------------------------------------------
# clopper_pearson_ci
# ---------------------------------------------------------------------------


def test_clopper_pearson_brackets_the_observed_proportion() -> None:
    for n in (3, 12, 40):
        for k in range(n + 1):
            interval = clopper_pearson_ci(k, n, 0.95)
            assert interval.lower <= interval.point <= interval.upper
            assert interval.method == "clopper_pearson"


def test_clopper_pearson_is_conservative_relative_to_wilson() -> None:
    """Exact coverage means a wider interval than the normal approximation."""
    for n in (5, 20, 60):
        for k in (1, n // 2, n - 1):
            exact = clopper_pearson_ci(k, n, 0.95)
            approx = wilson_ci(k, n, 0.95)
            assert exact.width >= approx.width - 1e-12


def test_clopper_pearson_attains_nominal_coverage() -> None:
    """The exact interval covers the truth with probability >= nominal.

    Coverage is computed exactly by summing the binomial pmf over the
    outcomes whose interval contains ``p`` — no simulation, so the
    assertion is deterministic.
    """
    n = 20
    confidence = 0.95
    for p in (0.1, 0.25, 0.5, 0.8):
        coverage = 0.0
        for k in range(n + 1):
            if clopper_pearson_ci(k, n, confidence).contains(p):
                coverage += math.comb(n, k) * p**k * (1.0 - p) ** (n - k)
        assert coverage >= confidence - 1e-9, f"coverage {coverage:.4f} at p={p}"


def test_clopper_pearson_boundary_cases() -> None:
    assert clopper_pearson_ci(0, 10, 0.95).lower == pytest.approx(0.0)
    assert clopper_pearson_ci(10, 10, 0.95).upper == pytest.approx(1.0)
    empty = clopper_pearson_ci(0, 0, 0.95)
    assert (empty.lower, empty.upper) == (0.0, 1.0)


def test_intervals_reject_bad_arguments() -> None:
    for factory in (wilson_ci, clopper_pearson_ci):
        with pytest.raises(ValueError):
            factory(5, 3, 0.95)
        with pytest.raises(ValueError):
            factory(-1, 3, 0.95)
        with pytest.raises(ValueError):
            factory(1, 3, 0.0)
        with pytest.raises(ValueError):
            factory(True, 3, 0.95)  # type: ignore[arg-type]
