"""Sweep-based monotonicity certification for the channel rule.

:func:`adaptive_reflow.frame.channel_rule.check_monotonicity_property`
answers a *single* question: "given this one baseline and this one
perturbation, did ``beta`` move the right way?" It returns a bare
``bool``. That is enough to catch a sign inversion, but it has two gaps
the framework actually cares about:

* **Coverage.** A monotonicity break that only shows up in part of the
  factor range (a clamp that saturates, a floor that lifts, a
  degeneracy branch that engages past a threshold) is invisible unless
  the one hand-picked pair happens to straddle it.
* **Localisation.** When the check fails, the caller learns *that* it
  failed and nothing else — not which factor, not at what value, not by
  how much. Debugging then means bisecting by hand.

:func:`certify_monotonicity` closes both gaps: it sweeps a factor across
a grid, checks the invariant on **every adjacent pair**, and returns a
report carrying the violation count, the worst violation magnitude, and
the exact factor values that produced it.

The module is additive — the existing single-pair checker is untouched
and still used by the engine's own invariant assertion. This is the
diagnostic layer on top of it.

Quantitative target
-------------------

Sweeping ``k`` grid points examines ``k - 1`` adjacent pairs versus the
single pair the legacy checker examines, so at the framework default
``k = 33`` the certifier has **32x** the monotonicity coverage. On the
canonical rule it certifies zero violations across every supported
family (no false positives); on a deliberately inverted rule it reports
the violating factor value. Asserted in
``tests/test_frame/test_channel_rule_diagnostics.py``.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from adaptive_reflow.contracts import ChannelRuleInputs, FactorValue
from adaptive_reflow.frame.channel_rule import compute_channel_decision

__all__ = [
    "DEFAULT_SWEEP_POINTS",
    "MONOTONE_FACTOR_DIRECTION",
    "MonotonicityReport",
    "MonotonicityViolation",
    "certify_all_factors",
    "certify_monotonicity",
    "sweep_grid",
]


DEFAULT_SWEEP_POINTS: int = 33
"""Default grid resolution. ``33`` points -> ``32`` adjacent pairs."""


MONOTONE_FACTOR_DIRECTION: dict[str, int] = {
    # Raising these factors must not lower ``beta``.
    "calibration_lower_bound": +1,
    "perturbation_stability_lower_bound": +1,
    "support_coverage": +1,
    "recency_decay": +1,
    # Raising these factors must not raise ``beta``.
    "ambiguity": -1,
    "degeneracy_penalty": -1,
}
"""Factor name -> required sign of ``d(beta) / d(factor)``.

Mirrors the four families
:func:`~adaptive_reflow.frame.channel_rule.check_monotonicity_property`
supports, re-expressed per *factor* (rather than per named family) so a
sweep can be driven directly from the factor name.
"""


@dataclass(frozen=True)
class MonotonicityViolation:
    """One adjacent-pair monotonicity break found during a sweep.

    Attributes
    ----------
    factor:
        Name of the swept factor.
    lower_value / upper_value:
        The two adjacent grid values that bracket the break.
    lower_beta / upper_beta:
        ``beta`` at those two values.
    magnitude:
        How far ``beta`` moved in the forbidden direction (always
        ``> 0``). This is the quantity to rank violations by — a
        ``1e-13`` break is roundoff, a ``0.3`` break is a real defect.
    """

    factor: str
    lower_value: float
    upper_value: float
    lower_beta: float
    upper_beta: float
    magnitude: float


@dataclass(frozen=True)
class MonotonicityReport:
    """Outcome of a monotonicity sweep.

    Attributes
    ----------
    factor:
        Name of the swept factor.
    direction:
        ``+1`` when raising the factor must not lower ``beta``, ``-1``
        for the opposite.
    n_points / n_pairs:
        Grid resolution and the number of adjacent pairs examined.
    violations:
        Every break found, in sweep order.
    betas:
        The full ``beta`` trace across the grid, so a caller can plot
        or hash the response curve.
    tolerance:
        Float tolerance below which a move is treated as roundoff.
    """

    factor: str
    direction: int
    n_points: int
    n_pairs: int
    violations: tuple[MonotonicityViolation, ...]
    betas: tuple[float, ...]
    tolerance: float

    @property
    def ok(self) -> bool:
        """Return whether the sweep found no violations."""
        return not self.violations

    @property
    def worst_magnitude(self) -> float:
        """Return the largest violation magnitude (``0.0`` when clean)."""
        if not self.violations:
            return 0.0
        return max(v.magnitude for v in self.violations)

    @property
    def coverage_ratio(self) -> float:
        """Return pairs examined relative to the single-pair legacy check.

        The measurable form of the coverage claim: ``n_pairs`` versus
        the one pair
        :func:`~adaptive_reflow.frame.channel_rule.check_monotonicity_property`
        inspects.
        """
        return float(self.n_pairs)


def sweep_grid(
    n_points: int = DEFAULT_SWEEP_POINTS,
    *,
    low: float = 0.0,
    high: float = 1.0,
) -> tuple[float, ...]:
    """Return ``n_points`` evenly spaced values in ``[low, high]``.

    Stdlib-only (no NumPy) so this module can be imported from the frame
    layer without pulling the optional numeric extra in.
    """
    if isinstance(n_points, bool) or not isinstance(n_points, int):
        raise ValueError(f"n_points must be int, got {n_points!r}")
    if int(n_points) < 2:
        raise ValueError(f"n_points must be >= 2, got {n_points!r}")
    lo = float(low)
    hi = float(high)
    if not (math.isfinite(lo) and math.isfinite(hi)):
        raise ValueError(f"low and high must be finite, got {low!r}, {high!r}")
    if hi <= lo:
        raise ValueError(f"high must exceed low, got low={lo!r}, high={hi!r}")
    step = (hi - lo) / float(int(n_points) - 1)
    return tuple(lo + step * float(i) for i in range(int(n_points)))


def certify_monotonicity(
    baseline: ChannelRuleInputs,
    factor: str,
    *,
    n_points: int = DEFAULT_SWEEP_POINTS,
    tolerance: float = 1e-12,
    rule: Callable[[ChannelRuleInputs], float] | None = None,
) -> MonotonicityReport:
    """Sweep ``factor`` across ``[0, 1]`` and certify the ``beta`` response.

    For each adjacent pair of grid values the required inequality is

        direction = +1:  beta(upper) >= beta(lower) - tolerance
        direction = -1:  beta(upper) <= beta(lower) + tolerance

    Every pair that breaks it is recorded with the bracketing values, so
    the caller gets the *location* of the defect rather than a bare
    ``False``.

    :param baseline: the inputs to perturb. Every field other than
        ``factor`` is held fixed, which is what makes the sweep a clean
        partial-derivative probe.
    :param factor: one of the keys of :data:`MONOTONE_FACTOR_DIRECTION`.
    :param n_points: grid resolution (``>= 2``).
    :param tolerance: float slack absorbing harmless roundoff.
    :param rule: optional override mapping inputs to ``beta``. Defaults
        to :func:`~adaptive_reflow.frame.channel_rule.compute_channel_decision`.
        Supplied by the tests to certify a deliberately-broken rule, and
        by callers who wrap the canonical rule.
    :raises ValueError: for an unknown ``factor`` or bad parameters.
    """
    if factor not in MONOTONE_FACTOR_DIRECTION:
        raise ValueError(
            f"unknown factor {factor!r}; expected one of "
            f"{sorted(MONOTONE_FACTOR_DIRECTION)!r}"
        )
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise ValueError(f"tolerance must be a real number, got {tolerance!r}")
    tol = float(tolerance)
    if not math.isfinite(tol) or tol < 0.0:
        raise ValueError(f"tolerance must be finite and >= 0, got {tolerance!r}")

    direction = int(MONOTONE_FACTOR_DIRECTION[factor])
    evaluate = rule if rule is not None else _canonical_beta
    grid = sweep_grid(n_points)

    betas: list[float] = []
    for value in grid:
        betas.append(float(evaluate(_with_factor(baseline, factor, value))))

    violations: list[MonotonicityViolation] = []
    for idx in range(len(grid) - 1):
        lo_beta = betas[idx]
        hi_beta = betas[idx + 1]
        delta = hi_beta - lo_beta
        # A violation is movement in the forbidden direction beyond the
        # tolerance. ``direction * delta`` is the signed move in the
        # *allowed* direction, so a negative value past -tol is a break.
        signed = float(direction) * delta
        if signed < -tol:
            violations.append(
                MonotonicityViolation(
                    factor=factor,
                    lower_value=float(grid[idx]),
                    upper_value=float(grid[idx + 1]),
                    lower_beta=lo_beta,
                    upper_beta=hi_beta,
                    magnitude=float(-signed),
                )
            )

    return MonotonicityReport(
        factor=factor,
        direction=direction,
        n_points=len(grid),
        n_pairs=len(grid) - 1,
        violations=tuple(violations),
        betas=tuple(betas),
        tolerance=tol,
    )


def certify_all_factors(
    baseline: ChannelRuleInputs,
    *,
    factors: Sequence[str] | None = None,
    n_points: int = DEFAULT_SWEEP_POINTS,
    tolerance: float = 1e-12,
    rule: Callable[[ChannelRuleInputs], float] | None = None,
) -> dict[str, MonotonicityReport]:
    """Run :func:`certify_monotonicity` for every monotone factor.

    Returns ``factor -> report``. ``factors`` defaults to every key of
    :data:`MONOTONE_FACTOR_DIRECTION`, so the default call is a full
    certification of the rule's monotone surface.
    """
    names = (
        tuple(factors)
        if factors is not None
        else tuple(sorted(MONOTONE_FACTOR_DIRECTION))
    )
    return {
        name: certify_monotonicity(
            baseline, name, n_points=n_points, tolerance=tolerance, rule=rule
        )
        for name in names
    }


def _with_factor(
    baseline: ChannelRuleInputs,
    factor: str,
    value: float,
) -> ChannelRuleInputs:
    """Return ``baseline`` with a single monotone factor replaced.

    Written as an explicit dispatch rather than ``replace(baseline,
    **{factor: ...})`` so the substitution is statically type-checked:
    ``ChannelRuleInputs`` mixes ``FactorValue`` fields with bundles,
    flags and hashes, and a ``**dict`` splat erases which one is being
    written.
    """
    fv = FactorValue(float(value))
    if factor == "calibration_lower_bound":
        return replace(baseline, calibration_lower_bound=fv)
    if factor == "perturbation_stability_lower_bound":
        return replace(baseline, perturbation_stability_lower_bound=fv)
    if factor == "support_coverage":
        return replace(baseline, support_coverage=fv)
    if factor == "recency_decay":
        return replace(baseline, recency_decay=fv)
    if factor == "ambiguity":
        return replace(baseline, ambiguity=fv)
    if factor == "degeneracy_penalty":
        return replace(baseline, degeneracy_penalty=fv)
    raise ValueError(f"unknown factor {factor!r}")


def _canonical_beta(inputs: ChannelRuleInputs) -> float:
    """Return the canonical rule's ``beta`` for ``inputs``."""
    return float(compute_channel_decision(inputs).decision.beta)
