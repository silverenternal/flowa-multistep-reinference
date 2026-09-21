"""Unit tests for :mod:`adaptive_reflow.stats.equivalence` (Wave 234 P1).

Each test exercises a known-answer check:

* TOST on a textbook equivalence case (paired t-test inside the
  symmetric ``[-margin, +margin]`` window → reject H0 of inequivalence).
* BF01 on a true-null paired sample (Wagenmakers BIC approx should
  produce ``BF01 > 10`` for moderate n).
* DerSimonian-Laird meta-analysis on a synthetic 5-study dataset
  with known pooled effect.
* Jonckheere-Terpstra on a strictly monotone dataset (asymptotic
  p-value should be very small).
* Non-inferiority one-sided test on a paired diff vs. margin.

All tests are stdlib + numpy + scipy only (they do not require
pingouin or statsmodels); the implementations themselves expose a
fallback path so this gate runs even without optional dependencies.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.stats.equivalence import (
    BayesFactorResult,
    EquivalenceResult,
    JonckheereResult,
    MetaAnalysisResult,
    NonInferiorityResult,
    bf01_paired,
    has_pingouin,
    has_statsmodels,
    jonckheere_terpstra,
    meta_random_effects,
    non_inferiority,
    tost_paired,
)


# ---------------------------------------------------------------------------
# TOST
# ---------------------------------------------------------------------------


def test_tost_paired_rejects_when_inside_equivalence_window() -> None:
    """Differences entirely inside ``[-margin, +margin]`` → equivalence."""
    # 8 paired differences centered on 0.01, sd ~ 0.05, margin 0.20
    diff = np.array([0.01, -0.02, 0.00, 0.03, -0.01, 0.02, -0.03, 0.01])
    sd = float(np.std(diff, ddof=1))
    n = len(diff)
    res = tost_paired(diff, sd=sd, n=n, margin=0.20)
    assert isinstance(res, EquivalenceResult)
    assert res.reject_equivalence is True
    assert res.p_tost < 0.05
    # lower test rejects H0:mu<=-margin (p small)
    assert res.p_lower < 0.05
    # upper test rejects H0:mu>=+margin (p small)
    assert res.p_upper < 0.05


def test_tost_paired_fails_when_outside_equivalence_window() -> None:
    """Strong shift outside the window → fails to reject inequivalence."""
    rng = np.random.default_rng(0)
    diff = rng.normal(loc=0.50, scale=0.10, size=20)
    sd = float(np.std(diff, ddof=1))
    res = tost_paired(diff, sd=sd, n=20, margin=0.20)
    assert res.reject_equivalence is False
    assert res.p_tost > 0.05


def test_tost_paired_rejects_invalid_margin() -> None:
    diff = np.array([0.0, 0.1, -0.1])
    with pytest.raises(ValueError):
        tost_paired(diff, sd=0.1, n=3, margin=-1.0)


# ---------------------------------------------------------------------------
# Bayes factor BF01 (paired t-test, BIC approx)
# ---------------------------------------------------------------------------


def test_bf01_paired_null_with_large_n_yields_large_bf01() -> None:
    """Under a true null, BIC-approx ``BF01`` should be > 10 for moderate n.

    With ``t`` close to 0 and large n, the BIC approx reduces to
    ``sqrt(n)``, so n = 200 ⇒ BF01 > 10 is a robust threshold that
    isolates the null-evidence property from the magnitude of ``t``.
    """
    rng = np.random.default_rng(42)
    # mean diff 0, small sd → strong evidence for H0 (no difference)
    diff = rng.normal(loc=0.0, scale=0.5, size=200)
    res = bf01_paired(diff, n=200)
    assert isinstance(res, BayesFactorResult)
    assert res.bf01 > 10.0
    # |t| should be small under the null
    assert abs(res.t) < 2.0


def test_bf01_paired_alt_with_large_t_yields_small_bf01() -> None:
    """A large t-statistic should drive ``BF01`` very small (< 1/10)."""
    rng = np.random.default_rng(1)
    diff = rng.normal(loc=1.5, scale=0.5, size=40)
    res = bf01_paired(diff, n=40)
    assert res.bf01 < 0.1
    assert res.t > 5.0


def test_bf01_paired_zero_variance_degenerate() -> None:
    """All-zero differences → ``t = 0``, ``BF01 = sqrt(n)``."""
    diff = np.zeros(9)
    res = bf01_paired(diff, n=9)
    assert res.t == 0.0
    assert math.isclose(res.bf01, math.sqrt(9), rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Meta-analysis (DerSimonian-Laird)
# ---------------------------------------------------------------------------


def test_meta_random_effects_recovers_pooled_on_uniform_dataset() -> None:
    """All studies report the same d → pooled ≈ d, tau^2 = 0, I^2 = 0."""
    d_values = [0.30, 0.30, 0.30, 0.30, 0.30]
    se_values = [0.10, 0.10, 0.10, 0.10, 0.10]
    res = meta_random_effects(d_values, se_values)
    assert isinstance(res, MetaAnalysisResult)
    assert math.isclose(res.pooled_d, 0.30, abs_tol=1e-9)
    assert math.isclose(res.tau2, 0.0, abs_tol=1e-12)
    assert math.isclose(res.i2, 0.0, abs_tol=1e-12)
    assert math.isclose(res.q, 0.0, abs_tol=1e-9)
    # CI should bracket 0.30
    assert res.ci_lower < 0.30 < res.ci_upper


def test_meta_random_effects_heterogeneity_signals_positive_tau2() -> None:
    """Studies with widely varying d → tau^2 > 0, I^2 > 0."""
    d_values = [0.10, 0.20, 0.40, 0.50, 0.80]
    se_values = [0.10, 0.10, 0.10, 0.10, 0.10]
    res = meta_random_effects(d_values, se_values)
    assert res.tau2 > 0.0
    assert res.i2 > 0.0
    assert res.q > 0.0
    assert res.q_p < 0.05  # very heterogeneous


def test_meta_random_effects_rejects_zero_se() -> None:
    with pytest.raises(ValueError):
        meta_random_effects([0.0, 0.1], [0.0, 0.1])


# ---------------------------------------------------------------------------
# Jonckheere-Terpstra
# ---------------------------------------------------------------------------


def test_jonckheere_terpstra_strictly_increasing_rejects_null() -> None:
    """Monotone increasing groups → reject null of no trend (p < 0.01)."""
    # 8 obs per group, means 1.0 / 2.0 / 3.0 / 4.0 → very strong trend
    groups = [
        [0.9, 1.0, 1.1, 0.95, 1.05, 0.85, 1.15, 1.0],
        [1.9, 2.0, 2.1, 1.95, 2.05, 1.85, 2.15, 2.0],
        [2.9, 3.0, 3.1, 2.95, 3.05, 2.85, 3.15, 3.0],
        [3.9, 4.0, 4.1, 3.95, 4.05, 3.85, 4.15, 4.0],
    ]
    res = jonckheere_terpstra(groups)
    assert isinstance(res, JonckheereResult)
    assert res.z > 0.0
    assert res.p_asymptotic < 0.01
    # jt_statistic positive (all pairs count)
    assert res.jt_statistic > 0.0


def test_jonckheere_terpstra_balanced_groups_shows_no_trend() -> None:
    """No trend → large p (cannot reject)."""
    groups = [
        [1.0, 2.0, 3.0],
        [1.5, 2.5, 3.5],
        [0.5, 1.5, 2.5],
    ]
    res = jonckheere_terpstra(groups, n_permutations=200, seed=123)
    assert res.p_asymptotic > 0.05
    # permutation p-value should also be large on average
    assert res.p_permutation > 0.05 or math.isnan(res.p_permutation)


def test_jonckheere_terpstra_requires_two_groups() -> None:
    with pytest.raises(ValueError):
        jonckheere_terpstra([[1.0, 2.0]])


# ---------------------------------------------------------------------------
# Non-inferiority (one-sided)
# ---------------------------------------------------------------------------


def test_non_inferiority_rejects_when_difference_well_above_margin() -> None:
    """Diff >> -margin → reject null of inferiority."""
    diff = np.array([0.10, 0.12, 0.08, 0.11, 0.09, 0.13, 0.07, 0.10])
    sd = float(np.std(diff, ddof=1))
    res = non_inferiority(diff, sd=sd, n=8, margin=0.50, direction="lower")
    assert isinstance(res, NonInferiorityResult)
    assert res.reject_non_inferiority is True
    assert res.p < 0.001


def test_non_inferiority_fails_when_difference_below_minus_margin() -> None:
    """Diff < -margin → cannot claim non-inferiority."""
    diff = np.array([-0.80, -0.75, -0.90, -0.70, -0.85])
    sd = float(np.std(diff, ddof=1))
    res = non_inferiority(diff, sd=sd, n=5, margin=0.20, direction="lower")
    assert res.reject_non_inferiority is False
    assert res.p > 0.5


def test_non_inferiority_upper_direction() -> None:
    """Upper-margin test: H0 says diff >= +margin; small diff rejects H0."""
    # 8 obs centered at -0.20 (clearly below the upper margin 0.50)
    diff = np.array([-0.20, -0.18, -0.22, -0.19, -0.21, -0.17, -0.23, -0.20])
    sd = float(np.std(diff, ddof=1))
    res = non_inferiority(diff, sd=sd, n=8, margin=0.50, direction="upper")
    assert isinstance(res, NonInferiorityResult)
    assert res.reject_non_inferiority is True
    assert res.p < 0.001


# ---------------------------------------------------------------------------
# Backend availability probes (informational only)
# ---------------------------------------------------------------------------


def test_pingouin_and_statsmodels_probes_return_bool() -> None:
    assert isinstance(has_pingouin(), bool)
    assert isinstance(has_statsmodels(), bool)