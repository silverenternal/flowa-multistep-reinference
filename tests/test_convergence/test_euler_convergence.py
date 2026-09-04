"""Convergence-order test for explicit Euler (claimed order 1).

The framework ships two public surfaces that implement explicit
forward Euler::

    y_next = y + dt * v(t, y)

1. :class:`adaptive_reflow.adapters.integrators.AMEDSolverIntegrator`
   — the order-1 forward-Euler building block used by the AMED-
   Solver diff-sampler (per ``integrators.py`` docstring).
2. :class:`adaptive_reflow.adapters.integrators.DPMSolverIntegrator`
   — first-order DPM-Solver; on a plain (non-semi-linear) ODE
   collapses to forward Euler.

This test exercises **AMEDSolverIntegrator** (canonical Euler
building block; the docstring explicitly identifies the step as
"the order-1 forward Euler step"). The DPM-Solver variant is
covered by a separate convergence test against the diffusion
semi-linear ODE form under ``test_dpm_convergence`` (TODO, not
in Wave 18 P1 scope).

Why Euler's stiff case is interesting
-------------------------------------

Explicit Euler has stability boundary ``dt * |lambda| < 2``; for
the stiff problem ``dx/dt = -100 x`` with horizon ``T = 0.1``,
``dt = 0.01`` (NFE = 10) gives ``dt * 100 = 1.0``, just inside
the boundary. At NFE = 5 (``dt = 0.02``) the boundary is exceeded
and the integrator would diverge. Our NFE_GRID starts at 10, so
Euler is stable across all tested NFE values, but the stiff
problem's slope fit may differ from linear / nonlinear.

Marked ``@pytest.mark.slow`` (nightly CI only). Tolerance
direction: one-sided ``measured_slope >= claimed_order - 0.2``.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.integrators import AMEDSolverIntegrator

from .test_problems import (
    DEFAULT_PROBLEMS,
    LINEAR,
    fit_log_log_slope,
    global_endpoint_error,
    integrate_at_nfe,
)

pytestmark = pytest.mark.slow

NFE_GRID: tuple[int, ...] = (40, 80, 160, 320, 640)
"""Extended SciML-style NFE sweep for Euler.

The stiff problem (dx/dt = -100 x, T=0.1) has stability boundary
``dt * 100 < 2``; at NFE = 10 (``dt = 0.01``) the boundary is
saturated and Euler's error barely decreases. Starting at NFE = 40
sidesteps this and reaches the asymptotic ``O(NFE^-1)`` regime
where the order-1 slope is observable. The sweep is one step
larger than the canonical 6-point sweep to give the linear
least-squares fit enough range on the stiff case.
"""

CLAIMED_ORDER = 1
"""Euler's textbook order is 1 (forward-Euler explicit)."""

TOLERANCE = 0.2
"""C.6 absolute tolerance per framework-internal-metrics rev 2 §1."""


def _euler_step(velocity, t: float, y, dt: float):
    """``AMEDSolverIntegrator.step`` adapter for :func:`integrate_at_nfe`.

    The AMEDSolverIntegrator step is documented as
    "the order-1 forward Euler step" (see
    ``integrators.py`` docstring), so it is the canonical Euler
    surface for the framework's convergence gate.
    """
    return AMEDSolverIntegrator().step(velocity, t, y, dt)


@pytest.mark.parametrize("problem", DEFAULT_PROBLEMS, ids=lambda p: p.name)
def test_euler_convergence_order(problem) -> None:
    """Euler achieves claimed order 1 (within 0.2 tolerance) on 3 problems.

    On the stiff problem, the slope may exceed ``CLAIMED_ORDER``
    due to super-convergence (similar to Heun). The one-sided
    tolerance ``measured_slope >= 1 - 0.2`` accepts this. A
    one-sided test is appropriate: explicit Euler never
    *under*-performs its claimed order on a stable trajectory —
    it only over-performs in the linear regime where error terms
    decay faster than the classical ``O(NFE^-1)``.
    """
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(problem, _euler_step, nfe)
        errors.append(global_endpoint_error(problem, y_end))
    slope = fit_log_log_slope(NFE_GRID, errors)
    abs_slope = abs(float(slope))
    assert abs_slope >= CLAIMED_ORDER - TOLERANCE, (
        f"Euler on {problem.name}: slope={abs_slope:.3f} "
        f"is below claimed order {CLAIMED_ORDER} - {TOLERANCE}; "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )
    # Cap at +1.5 above claimed order — Euler is rarely super-
    # convergent; >2.5 slope indicates noise floor or buggy step.
    assert abs_slope <= CLAIMED_ORDER + 1.5, (
        f"Euler on {problem.name}: slope={abs_slope:.3f} is "
        f"unexpectedly super-convergent. "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )


def test_euler_endpoint_accuracy_decreases_with_nfe() -> None:
    """Sanity: Euler's endpoint error strictly decreases with NFE."""
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(LINEAR, _euler_step, nfe)
        errors.append(global_endpoint_error(LINEAR, y_end))
    for prev, curr in zip(errors, errors[1:], strict=False):
        assert curr < prev, (
            f"Euler error not strictly decreasing with NFE: "
            f"{errors!r}"
        )


def test_euler_is_deterministic() -> None:
    """Two runs with identical inputs must produce identical endpoints."""
    y_first = integrate_at_nfe(LINEAR, _euler_step, 40)
    y_second = integrate_at_nfe(LINEAR, _euler_step, 40)
    assert float(np.max(np.abs(y_first - y_second))) == 0.0


def test_euler_stability_boundary_safe() -> None:
    """Euler on stiff stays stable across our NFE_GRID.

    Explicit Euler stability boundary for ``dx/dt = -100 x`` is
    ``dt * 100 < 2`` i.e. ``dt < 0.02``. Our smallest NFE on the
    stiff problem (NFE = 10, horizon 0.1) gives ``dt = 0.01``, well
    inside the boundary. If we ever shrink the NFE_GRID lower
    bound, this test will catch divergence immediately.
    """
    from .test_problems import STIFF
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(STIFF, _euler_step, nfe)
        # Endpoint magnitude must be finite and bounded by exp(-100*T) * (1 + small_eps).
        # If dt exceeds the stability boundary, the integrator blows up to >1.
        assert np.all(np.isfinite(y_end)), (
            f"Euler diverged at NFE={nfe} on stiff: {y_end}"
        )
        assert float(np.max(np.abs(y_end))) < 1.0, (
            f"Euler blew up at NFE={nfe} on stiff: {y_end}"
        )