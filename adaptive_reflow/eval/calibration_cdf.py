"""Exact binomial CDF + two-sided proportion intervals (P1 #24).

:mod:`adaptive_reflow.eval.calibration` already carries a numerically
careful, scipy-free implementation of the regularised incomplete beta
function (``_betacf`` / ``_betai`` / ``_inv_betai``) — but only exposes
it through two *one-sided lower bounds*
(:func:`~adaptive_reflow.eval.calibration.wilson_lower_bound` and
:func:`~adaptive_reflow.eval.calibration.beta_lower_bound`). Every caller
that wanted an upper bound, a two-sided interval, or a plain binomial
tail probability had to re-derive it.

This module exposes the missing surface, delegating to the existing
private helpers so there is exactly **one** incomplete-beta
implementation in the framework:

* :func:`binomial_cdf` / :func:`binomial_sf` — exact binomial tail
  probabilities via the beta identity
  ``P(X <= k) = I_{1-p}(n - k, k + 1)``.
* :func:`wilson_ci` — the two-sided Wilson score interval whose lower
  endpoint is bit-identical to
  :func:`~adaptive_reflow.eval.calibration.wilson_lower_bound`.
* :func:`clopper_pearson_ci` — the exact ("guaranteed coverage")
  interval, for the small-``n`` calibration buckets where Wilson's
  normal approximation under-covers.

Everything here is additive: no existing call site changes.

Quantitative target
-------------------

``wilson_ci(k, n, c).lower`` reproduces ``wilson_lower_bound(k, n, c)``
to within ``1e-12`` for every ``(k, n)`` in the calibration panel's
range, and :func:`clopper_pearson_ci` attains **at least** nominal
coverage on the exact binomial law (asserted directly in
``tests/test_eval/test_calibration_cdf.py``), where the Wilson interval
is allowed to under-cover.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from adaptive_reflow.eval.calibration import (
    _betai,
    _inv_betai,
    _norm_ppf,
    wilson_lower_bound,
)

__all__ = [
    "ProportionInterval",
    "binomial_cdf",
    "binomial_sf",
    "clopper_pearson_ci",
    "regularized_incomplete_beta",
    "wilson_ci",
]


@dataclass(frozen=True)
class ProportionInterval:
    """A two-sided confidence interval on a binomial proportion.

    Attributes
    ----------
    lower:
        Lower endpoint, clipped into ``[0, 1]``.
    upper:
        Upper endpoint, clipped into ``[0, 1]``. Always ``>= lower``.
    point:
        The observed proportion ``successes / trials`` (``0.0`` when
        ``trials == 0``).
    confidence:
        Nominal two-sided coverage the interval was constructed for.
    method:
        ``"wilson"`` or ``"clopper_pearson"``.
    """

    lower: float
    upper: float
    point: float
    confidence: float
    method: str

    @property
    def width(self) -> float:
        """Return ``upper - lower``."""
        return float(self.upper - self.lower)

    def contains(self, value: float) -> bool:
        """Return whether ``value`` lies inside the closed interval."""
        return bool(self.lower <= float(value) <= self.upper)


def _validate(successes: int, trials: int, confidence: float) -> None:
    """Raise :class:`ValueError` for any ill-formed ``(k, n, c)`` triple."""
    if isinstance(successes, bool) or not isinstance(successes, int):
        raise ValueError(f"successes must be int, got {type(successes).__name__}")
    if isinstance(trials, bool) or not isinstance(trials, int):
        raise ValueError(f"trials must be int, got {type(trials).__name__}")
    if successes < 0 or trials < 0 or successes > trials:
        raise ValueError(
            f"require 0 <= successes <= trials, got successes={successes}, "
            f"trials={trials}"
        )
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError(f"confidence must be a real number, got {confidence!r}")
    if not (0.0 < float(confidence) < 1.0):
        raise ValueError(f"confidence must be in (0, 1), got {confidence!r}")


def regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """Return the regularised incomplete beta ``I_x(a, b)``.

    A thin public alias for the module-private implementation in
    :mod:`adaptive_reflow.eval.calibration`, so callers that need the
    primitive (e.g. a bespoke tail probability) do not have to reach
    through a private name and the framework keeps a single source of
    truth for the continued-fraction expansion.
    """
    if not (a > 0.0 and b > 0.0):
        raise ValueError(f"a, b must be > 0, got a={a!r}, b={b!r}")
    if not (0.0 <= float(x) <= 1.0):
        raise ValueError(f"x must be in [0, 1], got {x!r}")
    return float(_betai(float(a), float(b), float(x)))


def binomial_cdf(k: int, n: int, p: float) -> float:
    """Return the exact ``P(X <= k)`` for ``X ~ Binomial(n, p)``.

    Uses the beta identity ``P(X <= k) = I_{1-p}(n - k, k + 1)`` rather
    than summing ``k + 1`` terms, so the cost is independent of ``n``
    and there is no catastrophic cancellation in the far tail.
    """
    if isinstance(k, bool) or not isinstance(k, int):
        raise ValueError(f"k must be int, got {type(k).__name__}")
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError(f"n must be int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n!r}")
    if not (0.0 <= float(p) <= 1.0):
        raise ValueError(f"p must be in [0, 1], got {p!r}")
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    pf = float(p)
    if pf <= 0.0:
        return 1.0
    if pf >= 1.0:
        return 0.0
    return float(min(1.0, max(0.0, _betai(float(n - k), float(k) + 1.0, 1.0 - pf))))


def binomial_sf(k: int, n: int, p: float) -> float:
    """Return the exact ``P(X > k)`` for ``X ~ Binomial(n, p)``."""
    return float(min(1.0, max(0.0, 1.0 - binomial_cdf(k, n, p))))


def wilson_ci(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> ProportionInterval:
    """Return the two-sided Wilson score interval.

    The lower endpoint is computed by delegating to
    :func:`~adaptive_reflow.eval.calibration.wilson_lower_bound`, so the
    two surfaces can never drift; the upper endpoint mirrors it with the
    radius added rather than subtracted.

    ``trials == 0`` returns the fail-closed degenerate interval
    ``[0, 1]`` with ``point = 0.0``, matching the empty-bucket
    convention the calibration panel already uses.
    """
    _validate(successes, trials, confidence)
    if trials == 0:
        return ProportionInterval(
            lower=0.0, upper=1.0, point=0.0,
            confidence=float(confidence), method="wilson",
        )
    z = _norm_ppf((1.0 + float(confidence)) / 2.0)
    z2 = z * z
    n = float(trials)
    p_hat = float(successes) / n
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denom
    radius = z * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n)) / denom
    lower = float(wilson_lower_bound(successes, trials, confidence))
    upper = min(1.0, max(0.0, center + radius))
    if upper < lower:
        upper = lower
    return ProportionInterval(
        lower=lower, upper=float(upper), point=float(p_hat),
        confidence=float(confidence), method="wilson",
    )


def clopper_pearson_ci(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> ProportionInterval:
    """Return the exact (Clopper-Pearson) two-sided interval.

    Inverts the exact binomial test:

        lower = InvBeta(alpha/2; k, n - k + 1)      (0 when k = 0)
        upper = InvBeta(1 - alpha/2; k + 1, n - k)  (1 when k = n)

    Unlike Wilson, coverage is *guaranteed* to be at least nominal for
    every ``(k, n, p)`` — which is what the small-``n`` calibration
    buckets need, at the cost of being conservative.
    """
    _validate(successes, trials, confidence)
    if trials == 0:
        return ProportionInterval(
            lower=0.0, upper=1.0, point=0.0,
            confidence=float(confidence), method="clopper_pearson",
        )
    alpha = 1.0 - float(confidence)
    k = int(successes)
    n = int(trials)
    lower = 0.0 if k == 0 else _inv_betai(float(k), float(n - k) + 1.0, alpha / 2.0)
    upper = (
        1.0
        if k == n
        else _inv_betai(float(k) + 1.0, float(n - k), 1.0 - alpha / 2.0)
    )
    lower = min(1.0, max(0.0, float(lower)))
    upper = min(1.0, max(0.0, float(upper)))
    if upper < lower:
        upper = lower
    return ProportionInterval(
        lower=lower, upper=upper, point=float(k) / float(n),
        confidence=float(confidence), method="clopper_pearson",
    )
