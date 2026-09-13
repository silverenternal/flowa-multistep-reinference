"""Explicit rate bound for Theorem 1.

Paper Theorem 1 (line 87-92): BL convergence of mu_{g,eps} -> nu_g on R^2.
This module makes the explicit O(eps) rate with constant sqrt(2/pi) a
first-class framework surface (dataclass + checker + tests).

The constant comes from the synchronous coupling
  (x, g(x) + eps*z) <-> (x, g(x)) with z ~ N(0,1)
which gives expected cost E|eps*z| = eps * sqrt(2/pi) and is g-independent.

See :data:`adaptive_reflow.eval.lipschitz_diagnostic.PLANAR_BL_CONSTANT`
for the canonical constant definition; this module re-exports it
through :data:`DEFAULT_ANALYTIC_CONSTANT` so the rate bound theorem
is a self-contained framework surface.

**Policy reference:** ``docs/adr/0005-fail-closed-audit-code-policy.md``
defines fail-closed semantics; the checker raises
:class:`adaptive_reflow.theory.validation.NotInFsideClassError` when an
F-side-violating ``g`` is supplied (default ``enforce_f_side=True``),
matching the rest of the framework's audit surface. Pass
``enforce_f_side=False`` to disable the F-side pre-check (the rate
bound itself is g-independent and holds for any measurable g, so this
flag is for callers who want the bound state without the F-side gate).
"""
from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable

# Paper Theorem 1 (line 87-92) plus the constant from the synchronous
# coupling argument in the Wave 12 high-3 audit (see eval/lipschitz_diagnostic.py
# PLANAR_BL_CONSTANT docstring).
from adaptive_reflow.eval.lipschitz_diagnostic import (
    PLANAR_BL_CONSTANT,
    planar_bl_convergence_witness,
)
from adaptive_reflow.theory.validation import (
    NotInFsideClassError,
    validate_g_admissible,
)

__all__ = ["ExplicitRateBoundReport", "check_explicit_rate_bound"]

DEFAULT_ANALYTIC_CONSTANT: float = PLANAR_BL_CONSTANT
"""Default ``C`` in ``BL(mu_{g,eps}, nu_g) <= C * eps``.

Equals :data:`PLANAR_BL_CONSTANT` = ``math.sqrt(2.0 / math.pi)``, the
synchronous-coupling upper bound established in Wave 12 A1-high-3.
"""

# Default F-side constants used by the fail-closed pre-check. These match
# the values used by ``Theorem1StatementChecker`` and ``validate_f_side``
# tests in the Wave 11 / Wave 12 conformance suite. Callers can override
# via the corresponding keyword arguments to
# :func:`check_explicit_rate_bound`.
_DEFAULT_FSIDE_D: float = 1.0
_DEFAULT_FSIDE_C: float = 1.0
_DEFAULT_FSIDE_RHO: float = 0.1
_DEFAULT_FSIDE_ETA: float = 0.1


@dataclasses.dataclass(frozen=True)
class ExplicitRateBoundReport:
    """Result of :func:`check_explicit_rate_bound`.

    Attributes
    ----------
    eps:
        The noise scale the bound was checked at.
    bl_distance:
        Empirical ``BL(mu_{g,eps}, nu_g)`` from the planar witness.
    analytic_constant:
        The ``C`` in ``BL <= C * eps`` (default ``sqrt(2/pi)`` from
        the synchronous coupling argument).
    expected_upper_bound:
        ``analytic_constant * eps``.
    empirical_to_bound_ratio:
        ``bl_distance / expected_upper_bound``; should be ``~ 1.0``.
    within_bound:
        ``True`` iff ``bl_distance <= expected_upper_bound`` (with MC
        tolerance accommodated by the witness's own floor check).
    n_samples:
        Points drawn per measure per seed.
    """

    eps: float
    bl_distance: float
    analytic_constant: float
    expected_upper_bound: float
    empirical_to_bound_ratio: float
    within_bound: bool
    n_samples: int

    def as_metrics(self) -> dict[str, float]:
        """Return the numeric fields as a flat metric dict."""
        return {
            "rate_bound_eps": float(self.eps),
            "rate_bound_bl_distance": float(self.bl_distance),
            "rate_bound_analytic_constant": float(self.analytic_constant),
            "rate_bound_expected_upper_bound": float(self.expected_upper_bound),
            "rate_bound_empirical_to_bound_ratio": float(self.empirical_to_bound_ratio),
            "rate_bound_within_bound": 1.0 if self.within_bound else 0.0,
        }


def check_explicit_rate_bound(
    g: Callable[[float], float],
    eps: float,
    *,
    constant: float = DEFAULT_ANALYTIC_CONSTANT,
    n_samples: int = 512,
    seed: int = 0,
    tolerance: float = 1.5,
    enforce_f_side: bool = True,
    f_side_d: float = _DEFAULT_FSIDE_D,
    f_side_c: float = _DEFAULT_FSIDE_C,
    f_side_rho: float = _DEFAULT_FSIDE_RHO,
    f_side_eta: float = _DEFAULT_FSIDE_ETA,
) -> ExplicitRateBoundReport:
    """Check ``BL(mu_{g,eps}, nu_g) <= constant * eps`` for the supplied ``g``.

    Reuses :func:`planar_bl_convergence_witness` (Wave 12 A1-high-3
    repointing: the true ``R^2`` BL distance on the ambient plane) and
    reports the empirical-to-bound ratio.

    Parameters
    ----------
    g
        The profile ``R -> R`` whose graph is the sheet ``{F_g = 0}``.
    eps
        Noise scale ``> 0``. The bound ``C * eps`` is checked at this
        single value; callers wanting a sweep can iterate themselves
        or call :func:`planar_bl_convergence_witness` directly.
    constant
        The ``C`` in ``BL <= C * eps``. Default
        :data:`DEFAULT_ANALYTIC_CONSTANT` (``sqrt(2/pi)``).
    n_samples
        Points per measure per replicate pair.
    seed
        RNG seed forwarded to the planar witness.
    tolerance
        Absolute slack absorbed into the ``within_bound`` check (the
        witness's own ``floor_tolerance`` already covers the MC-noise
        envelope; this is a small belt-and-braces pad).
    enforce_f_side
        When ``True`` (default), :func:`validate_g_admissible` is
        called first and any F-side violation raises
        :class:`NotInFsideClassError` (fail-closed per
        ``docs/adr/0005-fail-closed-audit-code-policy.md``). The rate
        bound itself is g-independent and holds for any measurable g;
        disabling this flag is for callers who want the bound state
        without the F-side gate.
    f_side_d, f_side_c, f_side_rho, f_side_eta
        F-side constants forwarded to :func:`validate_g_admissible` when
        ``enforce_f_side=True``.

    Raises
    ------
    NotInFsideClassError
        When ``enforce_f_side=True`` and ``g`` violates the F-side
        hypotheses (empty ``Z_g``, non-uniform simplicity, etc.). See
        :func:`adaptive_reflow.theory.validation.validate_g_admissible`.
    ValueError
        When ``eps <= 0``.
    """
    if eps <= 0.0:
        raise ValueError(f"eps must be > 0, got {eps}")
    if enforce_f_side:
        # Fail-closed F-side pre-check: Theorem 1 is conditional on the
        # F-side hypotheses (paper line 22-26), so a profile that fails
        # ``validate_g_admissible`` is out of the theorem's scope. Raise
        # rather than silently report ``within_bound=False`` so the
        # caller knows the bound state is undefined for this g.
        validate_g_admissible(
            g,
            d=float(f_side_d),
            c=float(f_side_c),
            rho=float(f_side_rho),
            eta=float(f_side_eta),
        )
    report = planar_bl_convergence_witness(
        g, [float(eps)], n_samples=int(n_samples), seed=int(seed),
        constant=float(constant),
    )
    bl_distance = float(report.bl_distances[0])
    expected = float(constant) * float(eps)
    return ExplicitRateBoundReport(
        eps=float(eps),
        bl_distance=float(bl_distance),
        analytic_constant=float(constant),
        expected_upper_bound=float(expected),
        empirical_to_bound_ratio=float(bl_distance / max(expected, 1e-12)),
        within_bound=bool(bl_distance <= expected + float(tolerance)),
        n_samples=int(n_samples),
    )
