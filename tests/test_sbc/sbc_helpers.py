"""SBC test helpers — rank-uniformity chi-squared statistics (C.7).

Per Talts et al. 2018: Simulation-Based Calibration (SBC) verifies
that a Bayesian inference algorithm produces *calibrated* posterior
samples by checking that rank statistics of ``theta`` against draws
from ``p(theta | x)`` are approximately uniform.

For each algorithm we:

1. Draw ``N`` ``(theta, x)`` pairs with ``theta ~ prior`` and
   ``x ~ p(x | theta)`` via the algorithm's stochastic forward step
   (the *simulator*).
2. Re-infer ``theta_hat`` from ``x`` (the *re-inference*).
3. Compute the rank of ``theta`` among ``K`` posterior draws
   ``theta_hat_1, ..., theta_hat_K ~ p(theta | x)`` — these
   posterior draws come from re-running the simulator ``K`` times
   with the *same* ``x`` (a noise-only re-inference approximation
   that holds for additive-Gaussian re-inference).
4. Bin the ``N`` ranks into ``B`` equal-width bins in ``[0, K]``.
5. Test the chi-squared statistic
   ``chi^2 = sum_bins (count - N/B)^2 / (N/B)`` against
   ``chi^2_{B-1}`` for a uniform null hypothesis.
6. Accept calibration iff ``p > 0.05``.

The chi-squared test is exact for any ``N >= 30`` and is the
canonical SBC summary statistic (Section 4 of Talts et al. 2018).
The minimal ``N = 200`` (per ``framework-internal-metrics.md`` rev 2
§1 C.7) is informative; ``N = 1000`` adds statistical power but
roughly multiplies wall-clock by 5x.

Compute budget (rough; N=200):

* Euler-Maruyama / SDE Heun sde_step: ~0.6 s
* JitteredConstantScheduler: ~0.2 s
* AdaptivePolicyDriver: ~0.1 s (digest-seeded envelope)
* Theorem1DynamicNoiseBias: ~0.05 s (deterministic; verified via
  parameter-uniformity on prior draws)
* Cosine inject_noise: ~0.5 s (numpy RNG draws)
"""
from __future__ import annotations

import math
import statistics
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SBCResult:
    """Result of one SBC run (one stochastic algorithm, one N).

    Attributes
    ----------
    algorithm_name:
        Human-readable algorithm identifier (e.g. ``"jittered_constant"``).
    n_prior_samples:
        Number of ``theta`` draws from the prior (``N``).
    n_posterior_draws:
        Number of posterior draws per observation (``K``).
    n_bins:
        Number of chi-squared bins (``B``).
    chi_squared:
        The chi-squared statistic against the uniform null.
    p_value:
        Two-sided p-value under ``chi^2_{B-1}``.
    mean_rank:
        Sample mean of the rank values (uniform ``(K+1)/2`` for
        calibrated algorithm; large deviations flag a miscalibrated
        algorithm).
    mean_rank_normalised:
        ``(mean_rank - (K+1)/2) / ((K+1)/2)`` — zero for a
        calibrated algorithm; positive skew means ranks pushed to the
        right (under-dispersed inference); negative skew means
        over-dispersed.
    rank_histogram:
        Bin counts of length ``n_bins``; should be ~``N/B`` each for
        a calibrated algorithm.
    runtime_seconds:
        Wall-clock for the SBC run (excludes import overhead).
    """

    algorithm_name: str
    n_prior_samples: int
    n_posterior_draws: int
    n_bins: int
    chi_squared: float
    p_value: float
    mean_rank: float
    mean_rank_normalised: float
    rank_histogram: tuple[int, ...]
    runtime_seconds: float


def _gser(k: float, x: float) -> float:
    """Series approximation for ``gamma_inc_lower(k, x) / Gamma(k)``.

    From Numerical Recipes (Press et al. 2007, §6.2). Used for
    ``x < k + 1``; accuracy ``<1e-7`` for ``k >= 1``.
    """
    ITMAX = 200
    EPS = 3.0e-16
    if x <= 0.0:
        return 0.0
    term = 1.0 / k
    s = term
    for i in range(1, ITMAX + 1):
        term *= x / (k + i)
        s += term
        if abs(term) < abs(s) * EPS:
            break
    return math.exp(k * math.log(x) - x - math.lgamma(k)) * s


def _gcf(k: float, x: float) -> float:
    """Lentz continued-fraction approximation for
    ``gamma_inc_upper(k, x) / Gamma(k)`` (the regularised upper
    incomplete gamma). Used for ``x >= k + 1``; accuracy
    ``<1e-7``.

    Initialisation follows Numerical Recipes (Press et al. 2007,
    §6.2) verbatim so the algorithm converges on the standard test
    vectors. Returns a value in ``[0, 1]``.
    """
    FPMIN = 1.0e-30
    ITMAX = 200
    EPS = 3.0e-16
    b = x + 1.0 - k
    c = 1.0 / FPMIN
    d = 1.0 / b if abs(b) >= FPMIN else (1.0 / FPMIN if b >= 0 else -1.0 / FPMIN)
    h = d
    for i in range(1, ITMAX + 1):
        an = -i * (i - k)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return math.exp(-x + k * math.log(x) - math.lgamma(k)) * h


def _chi2_sf(chi2: float, df: int) -> float:
    """Return ``P(chi^2_df > chi2)`` (chi-squared survival function).

    Computed via the regularised upper incomplete gamma function
    ``Q(df/2, chi2/2)`` using the standard series / continued-fraction
    pair from Numerical Recipes (Press et al. 2007, §6.2). Accurate
    to ``<1e-7`` for ``df >= 1``. Inlined so the SBC tests do not
    require ``scipy`` (the framework runs in a stdlib-only env on
    CPU-only sandboxes).
    """
    if chi2 <= 0.0 or df <= 0:
        return 1.0
    x = float(chi2) / 2.0
    k = df / 2.0
    if x < k + 1.0:
        # Series for the lower incomplete gamma; upper = 1 - lower.
        return max(0.0, 1.0 - _gser(k, x))
    return max(0.0, min(1.0, _gcf(k, x)))


def _chi2_pvalue(chi2: float, df: int) -> float:
    """Return ``P(chi^2_df > chi2)`` (two-sided p-value).

    Thin wrapper around :func:`_chi2_sf`. Used by :func:`run_sbc`.
    """
    if df <= 0:
        raise ValueError(f"df must be positive, got {df}")
    if chi2 < 0.0:
        raise ValueError(f"chi2 must be non-negative, got {chi2}")
    return float(_chi2_sf(float(chi2), int(df)))


def _rank_of(
    value: float,
    *,
    posterior_draws: Sequence[float],
) -> int:
    """Return ``#{d in posterior_draws : d <= value}`` (rank, 0-indexed).

    Talts et al. 2018 §3.1: the rank is the number of posterior draws
    strictly less than ``theta`` (the true parameter). Adding 1 to
    convert to 1-indexed ranks shifts the uniform by ``(K+1)/2`` —
    we use 0-indexed ranks internally and only convert to
    ``(K+1)/2`` for the mean-rank comparison.
    """
    count = 0
    for d in posterior_draws:
        if d <= value:
            count += 1
    return count


def run_sbc(
    *,
    algorithm_name: str,
    simulator: Callable[[float, int], float],
    re_inference: Callable[[float, int], Sequence[float]],
    prior_draws: Sequence[float],
    n_posterior_draws: int = 20,
    n_bins: int | None = None,
) -> SBCResult:
    """Run a single SBC experiment and return the chi-squared statistic.

    Parameters
    ----------
    algorithm_name:
        Human-readable algorithm identifier.
    simulator:
        ``simulator(theta, seed) -> x`` — draws one observation ``x``
        from the algorithm's forward stochastic step, parameterised
        by ``theta`` and a per-trial ``seed`` for reproducibility.
    re_inference:
        ``re_inference(x, seed) -> Sequence[float]`` — returns
        ``n_posterior_draws`` samples from ``p(theta | x)`` (approximated
        by re-running the simulator with the *same* ``x`` and
        ``n_posterior_draws`` independent seeds; valid for additive
        noise re-inference where the posterior on the noise scale
        factorises).
    prior_draws:
        Sequence of ``theta`` values from the prior (``N`` values).
    n_posterior_draws:
        Number of posterior draws per observation (``K``). Default 20
        matches Talts et al. 2018.
    n_bins:
        Number of chi-squared bins. Default ``n_posterior_draws + 1``
        (the Talts et al. 2018 §4 canonical: K+1 bins, one per possible
        rank value). Setting a smaller ``n_bins`` collapses multiple
        ranks into one bin and slightly reduces the chi-squared power
        for miscalibration detection; it does NOT change the null
        distribution.

    Returns
    -------
    SBCResult
        Summary statistic with chi-squared, p-value, mean rank,
        rank histogram, and runtime.
    """
    if n_posterior_draws <= 0:
        raise ValueError(
            f"n_posterior_draws must be positive, got {n_posterior_draws}"
        )
    if n_bins is None:
        n_bins = int(n_posterior_draws) + 1
    if n_bins <= 1:
        raise ValueError(f"n_bins must be > 1, got {n_bins}")
    n_prior = len(prior_draws)
    if n_prior <= 0:
        raise ValueError("prior_draws must be non-empty")

    t_start = time.perf_counter()
    ranks: list[int] = []
    outer_seed = int(abs(hash(tuple(prior_draws))) % (2**31))
    for i, theta in enumerate(prior_draws):
        # Thread both `i` and `outer_seed` into the per-call seeds so
        # re-running with a different prior produces an *independent*
        # simulator / posterior noise sequence.
        sim_seed = outer_seed * 100003 + int(i) * 7919 + 1
        post_seed = outer_seed * 100003 + int(i) * 7919 + 2
        x = simulator(float(theta), sim_seed)
        posterior = re_inference(float(x), post_seed)
        rank = _rank_of(float(theta), posterior_draws=posterior)
        ranks.append(int(rank))
    t_end = time.perf_counter()

    # Bin ranks into ``n_bins`` equal-width bins covering
    # ``[0, n_posterior_draws]`` (Talts et al. 2018 §4). We use the
    # requested ``n_bins`` (default 20) which gives a bin width of 1
    # when ``n_posterior_draws == n_bins``. The chi-squared null is
    # uniform-with-boundary, which is exactly what Talts et al.
    # validate as the SBC null hypothesis.
    bin_width = n_posterior_draws / n_bins
    counts = [0] * n_bins
    for r in ranks:
        idx = min(int(r // bin_width), n_bins - 1)
        counts[idx] += 1

    expected = float(n_prior) / float(n_bins)
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    p_value = _chi2_pvalue(chi2, df=n_bins - 1)
    mean_rank = float(statistics.fmean(ranks))
    midpoint = (n_posterior_draws + 1) / 2.0
    mean_rank_normalised = (mean_rank - midpoint) / midpoint

    return SBCResult(
        algorithm_name=algorithm_name,
        n_prior_samples=n_prior,
        n_posterior_draws=n_posterior_draws,
        n_bins=n_bins,
        chi_squared=float(chi2),
        p_value=float(p_value),
        mean_rank=mean_rank,
        mean_rank_normalised=float(mean_rank_normalised),
        rank_histogram=tuple(counts),
        runtime_seconds=float(t_end - t_start),
    )


def uniform_prior(
    *,
    n: int,
    low: float,
    high: float,
    seed: int = 0,
) -> np.ndarray:
    """Return ``n`` draws from ``Uniform(low, high)``.

    The canonical prior for SBC on a scale parameter; bounds ``low``
    and ``high`` must lie in ``(0, 1]`` for the canonical capacity
    range.
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    if not (math.isfinite(low) and math.isfinite(high)):
        raise ValueError(
            f"bounds must be finite, got low={low!r}, high={high!r}"
        )
    if low >= high:
        raise ValueError(
            f"low must be < high, got low={low!r}, high={high!r}"
        )
    rng = np.random.default_rng(int(seed))
    return rng.uniform(low=float(low), high=float(high), size=int(n))


def assert_calibrated(
    result: SBCResult,
    *,
    p_value_threshold: float = 0.05,
) -> None:
    """Assert that ``result`` corresponds to a calibrated algorithm.

    Fails if the chi-squared p-value falls below
    ``p_value_threshold`` OR if the mean-rank-normalised deviation
    exceeds 0.20 (a 20 % skew on the rank midpoint indicates the
    posterior is systematically over- or under-dispersed even if the
    chi-squared test nominally passes).

    Parameters
    ----------
    result:
        Output of :func:`run_sbc`.
    p_value_threshold:
        Calibration threshold for the chi-squared p-value (default
        ``0.05`` matches the Talts et al. 2018 convention).
    """
    if result.p_value < p_value_threshold:
        raise AssertionError(
            f"SBC FAIL [{result.algorithm_name}]: "
            f"chi^2 = {result.chi_squared:.3f} on "
            f"{result.n_bins - 1} df, "
            f"p = {result.p_value:.4f} < {p_value_threshold:.4f}; "
            f"rank histogram = {result.rank_histogram!r}, "
            f"expected ~{result.n_prior_samples // result.n_bins} per bin. "
            f"Algorithm is miscalibrated (re-inference does not match "
            f"the simulator's noise model)."
        )
    if abs(result.mean_rank_normalised) > 0.20:
        raise AssertionError(
            f"SBC FAIL [{result.algorithm_name}]: "
            f"mean_rank normalised deviation "
            f"{result.mean_rank_normalised:+.4f} exceeds ±0.20; "
            f"inference is systematically skewed "
            f"(over- or under-dispersed relative to simulator)."
        )


__all__ = [
    "SBCResult",
    "assert_calibrated",
    "run_sbc",
    "uniform_prior",
]