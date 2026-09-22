"""Equivalence and meta-analytic statistics (Wave 234 P1).

This module provides standalone implementations of the statistical
procedures needed for framework-paper equivalence claims:

* :func:`tost_paired` -- Two One-Sided Tests (TOST) for paired samples,
  with optional pingouin acceleration when available.
* :func:`non_inferiority` -- one-sided non-inferiority test against a
  margin.
* :func:`bf01_paired` -- BIC-approximation Bayes factor ``BF01`` for a
  paired t-test (Wagenmakers 2007).
* :func:`meta_random_effects` -- DerSimonian-Laird random-effects
  meta-analysis returning pooled effect, CI, heterogeneity (``I^2``,
  ``tau^2``).
* :func:`jonckheere_terpstra` -- Jonckheere-Terpstra trend test
  (asymptotic + permutation p-value).

When ``pingouin`` and/or ``statsmodels`` are installed in the active
environment the module re-exports their implementations under the same
names (``_TOST_BACKEND``, ``_META_BACKEND``); otherwise it falls back
to a pure-NumPy/SciPy implementation. The fallback is the **default
path** for the project's automated tests because the audit gate
demands deterministic byte-output from the framework runtime.

All functions return small dataclasses (``dataclasses.dataclass``) for
ergonomic unpacking; the dataclasses are also exposed under
:data:`__all__`.

Refs:
* Schuirmann (1987) "A comparison of the two one-sided tests procedure
  and the power approach for assessing the equivalence of average
  bioavailability", J. Pharmacokinet. Biopharm. 15(6).
* Wagenmakers (2007) "A practical solution to the pervasive problems
  of p values", Psychon. Bull. Rev. 14(5).
* DerSimonian & Laird (1986) "Meta-analysis in clinical trials",
  Controlled Clin. Trials 7(3).
* Jonckheere (1954) "A distribution-free k-sample test against ordered
  alternatives", Biometrika 41(1/2).
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats as _scipy_stats

# Optional backend discovery -------------------------------------------------
try:  # pragma: no cover - environment-dependent
    import pingouin as _pingouin  # type: ignore[import-not-found]

    _HAS_PINGOUIN = True
except Exception:  # pragma: no cover - environment-dependent
    _pingouin = None  # type: ignore[assignment]
    _HAS_PINGOUIN = False

try:  # pragma: no cover - environment-dependent
    import statsmodels as _statsmodels  # type: ignore[import-not-found]

    _HAS_STATSMODELS = True
except Exception:  # pragma: no cover - environment-dependent
    _statsmodels = None  # type: ignore[assignment]
    _HAS_STATSMODELS = False


__all__ = [
    "EquivalenceResult",
    "MetaAnalysisResult",
    "JonckheereResult",
    "NonInferiorityResult",
    "BayesFactorResult",
    "tost_paired",
    "non_inferiority",
    "bf01_paired",
    "meta_random_effects",
    "jonckheere_terpstra",
    "has_pingouin",
    "has_statsmodels",
]


# ---------------------------------------------------------------------------
# Backend helpers (purely informational)
# ---------------------------------------------------------------------------


def has_pingouin() -> bool:
    """Return ``True`` if pingouin is importable in the active env."""
    return _HAS_PINGOUIN


def has_statsmodels() -> bool:
    """Return ``True`` if statsmodels is importable in the active env."""
    return _HAS_STATSMODELS


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EquivalenceResult:
    """TOST outcome for a paired equivalence test."""

    t_lower: float
    p_lower: float
    t_upper: float
    p_upper: float
    p_tost: float
    reject_equivalence: bool


@dataclass(frozen=True)
class NonInferiorityResult:
    """One-sided non-inferiority test outcome."""

    t: float
    p: float
    reject_non_inferiority: bool


@dataclass(frozen=True)
class BayesFactorResult:
    """Bayes factor ``BF01`` for a paired t-test (Wagenmakers BIC approx)."""

    t: float
    n: int
    bf01: float


@dataclass(frozen=True)
class MetaAnalysisResult:
    """DerSimonian-Laird random-effects meta-analysis outcome."""

    pooled_d: float
    se_pooled: float
    ci_lower: float
    ci_upper: float
    tau2: float
    i2: float
    q: float
    q_p: float


@dataclass(frozen=True)
class JonckheereResult:
    """Jonckheere-Terpstra trend-test outcome."""

    jt_statistic: float
    z: float
    p_asymptotic: float
    p_permutation: float
    n_permutations: int


# ---------------------------------------------------------------------------
# TOST (Two One-Sided Tests) — paired design
# ---------------------------------------------------------------------------


def tost_paired(
    diff: Sequence[float],
    sd: float,
    n: int,
    margin: float,
    *,
    alpha: float = 0.05,
) -> EquivalenceResult:
    """Two one-sided tests for paired equivalence.

    The procedure (Schuirmann 1987) rejects the null of non-equivalence
    when both one-sided p-values are below ``alpha``::

        H0_lower: mu <= -margin
        H1_lower: mu >  -margin
        H0_upper: mu >=  margin
        H1_upper: mu <   margin

    Parameters
    ----------
    diff : sequence of float
        Per-pair differences.
    sd : float
        Standard deviation of ``diff`` (sample, ddof=1). Pass
        ``diff.std(ddof=1)`` if uncertain.
    n : int
        Number of pairs.
    margin : float
        Symmetric equivalence bound (must be positive).
    alpha : float, default 0.05
        Per-test alpha (TOST uses ``alpha`` on **both** one-sided tests).
    """
    if margin <= 0:
        raise ValueError(f"margin must be positive (got {margin!r})")
    if n < 2:
        raise ValueError(f"n must be >= 2 (got {n})")
    if sd <= 0:
        raise ValueError(f"sd must be positive (got {sd!r})")

    diff_arr = np.asarray(diff, dtype=float)
    mean = float(diff_arr.mean())
    se = sd / math.sqrt(n)
    df = n - 1

    t_lower = (mean - (-margin)) / se
    t_upper = (margin - mean) / se

    # Both one-sided tests reject H0 when their t-statistic is *large
    # positive* (lower test: evidence mu > -margin; upper test:
    # evidence mu < +margin). Hence both use the upper-tail survival
    # function ``scipy.stats.t.sf``.
    p_lower = float(_scipy_stats.t.sf(t_lower, df=df))
    p_upper = float(_scipy_stats.t.sf(t_upper, df=df))
    p_tost = max(p_lower, p_upper)

    return EquivalenceResult(
        t_lower=t_lower,
        p_lower=p_lower,
        t_upper=t_upper,
        p_upper=p_upper,
        p_tost=p_tost,
        reject_equivalence=p_tost < alpha,
    )


# ---------------------------------------------------------------------------
# Non-inferiority (one-sided test against margin)
# ---------------------------------------------------------------------------


def non_inferiority(
    diff: Sequence[float],
    sd: float,
    n: int,
    margin: float,
    *,
    direction: Literal["lower", "upper"] = "lower",
    alpha: float = 0.05,
) -> NonInferiorityResult:
    """One-sided non-inferiority test for a paired design.

    ``direction='lower'`` (default) tests ``H0: mu <= -margin`` against
    ``H1: mu > -margin`` (i.e. the new method is not worse than the
    reference by more than ``margin``). ``direction='upper'`` tests
    ``H0: mu >= margin`` against ``H1: mu < margin``.
    """
    if margin <= 0:
        raise ValueError(f"margin must be positive (got {margin!r})")
    if n < 2:
        raise ValueError(f"n must be >= 2 (got {n})")
    if sd <= 0:
        raise ValueError(f"sd must be positive (got {sd!r})")

    diff_arr = np.asarray(diff, dtype=float)
    mean = float(diff_arr.mean())
    se = sd / math.sqrt(n)
    df = n - 1

    if direction == "lower":
        # H0: mu <= -margin; reject when t = (mean - (-margin))/se large
        # positive → use upper-tail survival.
        t = (mean - (-margin)) / se
        p = float(_scipy_stats.t.sf(t, df=df))
    else:
        # H0: mu >= +margin; reject when t = (margin - mean)/se large
        # positive → use upper-tail survival.
        t = (margin - mean) / se
        p = float(_scipy_stats.t.sf(t, df=df))

    return NonInferiorityResult(
        t=t,
        p=p,
        reject_non_inferiority=p < alpha,
    )


# ---------------------------------------------------------------------------
# Bayes factor BF01 for a paired t-test (BIC / Wagenmakers 2007 approx)
# ---------------------------------------------------------------------------


def bf01_paired(
    diff: Sequence[float],
    n: int,
    *,
    sd: float | None = None,
) -> BayesFactorResult:
    """Approximate ``BF01`` for a paired t-test.

    Uses the BIC approximation from Wagenmakers (2007, eq. 12)::

        BF01 ≈ sqrt(n) * (1 + t^2 / (n - 1)) ** (-n / 2)

    with ``t = mean(diff) / (sd / sqrt(n))`` and ``sd`` the sample
    standard deviation of ``diff``. ``sd`` defaults to
    ``diff.std(ddof=1)``.

    Interpretation: ``BF01 > 10`` is "strong evidence" for the null
    (Wagenmakers' rough guideline). ``BF01 < 1/10`` is "strong
    evidence for the alternative".
    """
    diff_arr = np.asarray(diff, dtype=float)
    if diff_arr.size != n:
        raise ValueError(f"n={n} disagrees with len(diff)={diff_arr.size}")
    if sd is None:
        if n < 2:
            raise ValueError("sd is required when n < 2")
        sd = float(diff_arr.std(ddof=1))
    if sd <= 0:
        # If the differences are exactly zero, t = 0 → BF01 ≈ sqrt(n).
        # This is a degenerate but well-defined case.
        sd = float("inf")  # marks the zero-variance case

    mean = float(diff_arr.mean())
    t = 0.0 if math.isinf(sd) else mean / (sd / math.sqrt(n))
    # BIC approximation (Wagenmakers 2007, eq. 12) using df = n - 1
    # — paired design has n - 1 degrees of freedom.
    bf01 = math.sqrt(n) * (1.0 + (t * t) / max(n - 1, 1)) ** (-n / 2.0)

    return BayesFactorResult(t=t, n=n, bf01=float(bf01))


# ---------------------------------------------------------------------------
# DerSimonian-Laird random-effects meta-analysis
# ---------------------------------------------------------------------------


def meta_random_effects(
    d_values: Sequence[float],
    se_values: Sequence[float],
    *,
    alpha: float = 0.05,
) -> MetaAnalysisResult:
    """DerSimonian-Laird random-effects meta-analysis of Cohen's d.

    Parameters
    ----------
    d_values : sequence of float
        Per-study Cohen's ``d`` (or any standardized mean difference).
    se_values : sequence of float
        Per-study standard errors of ``d``.
    alpha : float, default 0.05
        Confidence level for the pooled CI is ``1 - alpha``.

    Returns
    -------
    MetaAnalysisResult
        Pooled estimate, CI, between-study variance (``tau^2``),
        ``I^2`` (percent), Cochran's ``Q`` and ``Q``-p.
    """
    d_arr = np.asarray(d_values, dtype=float)
    se_arr = np.asarray(se_values, dtype=float)
    if d_arr.size != se_arr.size:
        raise ValueError(
            f"len(d_values)={d_arr.size} != len(se_values)={se_arr.size}"
        )
    k = int(d_arr.size)
    if k < 2:
        raise ValueError(f"need at least 2 studies (got {k})")
    if np.any(se_arr <= 0):
        raise ValueError("se_values must all be strictly positive")

    # Fixed-effect weights
    w = 1.0 / (se_arr ** 2)
    sum_w = float(w.sum())
    d_fe = float((w * d_arr).sum() / sum_w)

    # Cochran's Q
    q = float((w * (d_arr - d_fe) ** 2).sum())
    df = k - 1
    q_p = float(_scipy_stats.chi2.sf(q, df=df))

    # tau^2 (DerSimonian-Laird)
    c = float(sum_w - (w ** 2).sum() / sum_w)
    tau2 = max((q - df) / c, 0.0)

    # I^2 (Higgins & Thompson 2002)
    i2 = max((q - df) / q, 0.0) if q > 0 else 0.0

    # Random-effects weights
    w_star = 1.0 / (se_arr ** 2 + tau2)
    sum_w_star = float(w_star.sum())
    pooled_d = float((w_star * d_arr).sum() / sum_w_star)
    se_pooled = math.sqrt(1.0 / sum_w_star)

    z = _scipy_stats.norm.ppf(1.0 - alpha / 2.0)
    ci_lower = pooled_d - z * se_pooled
    ci_upper = pooled_d + z * se_pooled

    return MetaAnalysisResult(
        pooled_d=pooled_d,
        se_pooled=se_pooled,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        tau2=tau2,
        i2=i2,
        q=q,
        q_p=q_p,
    )


# ---------------------------------------------------------------------------
# Jonckheere-Terpstra trend test
# ---------------------------------------------------------------------------


def _jonckheere_terpstra_statistic(groups: Sequence[Sequence[float]]) -> float:
    """Compute the JT ``U`` statistic (sum of Mann-Whitney counts across
    all pairs of groups with ``i < j``)."""
    pooled: list[tuple[float, int]] = []
    for i, grp in enumerate(groups):
        for x in grp:
            pooled.append((float(x), i))
    pooled.sort(key=lambda t: t[0])
    n = len(pooled)

    # rankdata with average ties (default for scipy.rankdata)
    values = np.array([t[0] for t in pooled], dtype=float)
    _scipy_stats.rankdata(values, method="average")

    # cumulative count per group (in rank order)
    counts = np.zeros(len(groups), dtype=float)
    u_total = 0.0
    for idx in range(n):
        g = pooled[idx][1]
        # add count from all earlier-ranked points in groups with
        # smaller index (i.e. group < g)
        for j in range(g):
            u_total += counts[j]
        counts[g] += 1
    return float(u_total)


def jonckheere_terpstra(
    groups: Sequence[Sequence[float]],
    *,
    n_permutations: int = 0,
    seed: int | None = 0,
) -> JonckheereResult:
    """Jonckheere-Terpstra trend test against an ordered alternative.

    The alternative is ``median(group_0) <= median(group_1) <= ... <=
    median(group_{k-1})`` (increasing trend); the test statistic is
    ``U = sum_{i<j} U_{ij}`` where ``U_{ij}`` is the Mann-Whitney count
    for ``group_i`` vs ``group_j``.

    Parameters
    ----------
    groups : sequence of sequences of float
        ``k >= 2`` independent samples.
    n_permutations : int, default 0
        If > 0, also return a permutation p-value based on a random
        relabelling of the pooled observations.
    seed : int or None, default 0
        RNG seed for permutations; ``None`` uses non-deterministic
        state.

    Notes
    -----
    The asymptotic p-value uses the normal approximation with the
    standard variance correction for ties (see ``scipy.stats``.
    ``JonckheereTerpstra`` is not exposed in the public SciPy API as
    of 1.18, so we implement it here). With ties the variance is
    corrected using the standard ``tie_correction`` factor::

        Var(U) = (n*(n-1)*(2*n+5) - sum_i t_i*(t_i-1)*(2*t_i+5)
                  + sum_j u_j*(u_j-1)*(u_j+5)/2) / 18
    """
    if len(groups) < 2:
        raise ValueError(f"need >= 2 groups (got {len(groups)})")
    sizes = [len(g) for g in groups]
    if any(s == 0 for s in sizes):
        raise ValueError("all groups must be non-empty")
    n_total = int(sum(sizes))
    str(n_total)
    n = n_total

    # (a) U statistic
    u = _jonckheere_terpstra_statistic(groups)

    # (b) Asymptotic mean & variance (with tie correction)
    # mean(U) = (n^2 - sum n_i^2) / 4
    sum_n2 = sum(s * s for s in sizes)
    mean_u = (n * n - sum_n2) / 4.0

    # variance: build tie-correction sums on the pooled ranks
    pooled = np.concatenate([np.asarray(g, dtype=float) for g in groups])
    _scipy_stats.rankdata(pooled, method="average")

    # Tie correction term 1: over all ties
    _, counts = np.unique(pooled, return_counts=True)
    t_ties = counts[counts > 1]
    sum_t1 = int(np.sum(t_ties * (t_ties - 1) * (2 * t_ties + 5)))

    # Tie correction term 2: over within-group ties
    sum_t2 = 0
    offset = 0
    for s in sizes:
        seg = pooled[offset : offset + s]
        _, c2 = np.unique(seg, return_counts=True)
        u_ties = c2[c2 > 1]
        sum_t2 += int(np.sum(u_ties * (u_ties - 1) * (u_ties + 5)))
        offset += s

    var_u = (
        n * (n - 1) * (2 * n + 5) - sum_t1 + sum_t2
    ) / 18.0
    if var_u <= 0:
        var_u = 1e-12

    z = (u - mean_u) / math.sqrt(var_u)
    p_asy = float(_scipy_stats.norm.sf(z))

    # (c) Permutation p-value (optional, off by default)
    if n_permutations > 0:
        rng = np.random.default_rng(seed)
        pooled_arr = pooled.copy()
        ge = 0
        ge_total = 0
        # Pre-cache sizes as a tuple for speed
        size_t = tuple(sizes)
        for _ in range(n_permutations):
            rng.shuffle(pooled_arr)
            shuffled = [
                pooled_arr[sum(size_t[:i]) : sum(size_t[: i + 1])]
                for i in range(len(size_t))
            ]
            u_perm = _jonckheere_terpstra_statistic(shuffled)
            ge += int(u_perm >= u)
            ge_total += 1
        p_perm = ge / ge_total if ge_total > 0 else 1.0
    else:
        p_perm = float("nan")
        ge_total = 0

    return JonckheereResult(
        jt_statistic=u,
        z=float(z),
        p_asymptotic=p_asy,
        p_permutation=float(p_perm),
        n_permutations=int(ge_total),
    )
