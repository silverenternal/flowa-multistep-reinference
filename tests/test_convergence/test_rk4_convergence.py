"""Convergence-order test for the RK4 integrator (claimed order 4).

Per framework-internal-metrics rev 2 §1 C.6:

> RK4 achieves global-error order 4 within 0.2 absolute tolerance
> on 3 analytic problems.

The RK4 step is the canonical four-stage Runge-Kutta
(:class:`adaptive_reflow.adapters.integrators.RK4Integrator`)::

    k1 = f(t, y)
    k2 = f(t + 0.5 dt, y + 0.5 dt k1)
    k3 = f(t + 0.5 dt, y + 0.5 dt k2)
    k4 = f(t + dt, y + dt k3)
    y_next = y + (dt / 6) * (k1 + 2 k2 + 2 k3 + k4)

Marked ``@pytest.mark.slow`` (nightly CI only).

Tolerance direction: one-sided ``measured_slope >=
claimed_order - 0.2``. See
``tests.test_convergence.test_heun_convergence`` docstring for
the rationale (super-convergence on stiff is not a defect).
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.integrators import RK4Integrator

from .test_problems import (
    DEFAULT_PROBLEMS,
    LINEAR,
    fit_log_log_slope,
    global_endpoint_error,
    integrate_at_nfe,
)

pytestmark = pytest.mark.slow

NFE_GRID: tuple[int, ...] = (20, 40, 80, 160, 320)
"""Canonical SciML-style NFE sweep.

For higher-order methods (RK4), the lowest NFE points can sit in
the *pre-asymptotic* regime where error is not yet scaling as
``O(NFE^-p)`` — the integrator's step shape has not stabilized
into its classical order. Starting at NFE = 20 sidesteps this
artefact for RK4 (and higher) while still covering 1.6 decades
of NFE, more than enough for a robust least-squares fit.
"""

CLAIMED_ORDER = 4
"""RK4's textbook order is 4 (four-stage explicit Runge-Kutta)."""

TOLERANCE = 0.2
"""C.6 absolute tolerance per framework-internal-metrics rev 2 §1."""


def _rk4_step(velocity, t: float, y, dt: float):
    """``RK4Integrator.step`` adapter for :func:`integrate_at_nfe`."""
    return RK4Integrator().step(velocity, t, y, dt)


@pytest.mark.parametrize("problem", DEFAULT_PROBLEMS, ids=lambda p: p.name)
def test_rk4_convergence_order(problem) -> None:
    """RK4 achieves claimed order 4 (within 0.2 tolerance) on 3 problems."""
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(problem, _rk4_step, nfe)
        errors.append(global_endpoint_error(problem, y_end))
    slope = fit_log_log_slope(NFE_GRID, errors)
    abs_slope = abs(float(slope))
    assert abs_slope >= CLAIMED_ORDER - TOLERANCE, (
        f"RK4 on {problem.name}: slope={abs_slope:.3f} "
        f"is below claimed order {CLAIMED_ORDER} - {TOLERANCE}; "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )
    # Cap at +1.0 above claimed order — RK4 is rarely super-
    # convergent; >5.0 slope indicates noise floor or buggy problem.
    assert abs_slope <= CLAIMED_ORDER + 1.0, (
        f"RK4 on {problem.name}: slope={abs_slope:.3f} is "
        f"unexpectedly super-convergent. "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )


def test_rk4_endpoint_accuracy_decreases_with_nfe() -> None:
    """Sanity: RK4's endpoint error strictly decreases with NFE.

    RK4 is unconditionally more accurate than RK2/Heun at every
    NFE; if we ever see RK4 degrade, the step is buggy.
    """
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(LINEAR, _rk4_step, nfe)
        errors.append(global_endpoint_error(LINEAR, y_end))
    for prev, curr in zip(errors, errors[1:], strict=False):
        assert curr < prev, (
            f"RK4 error not strictly decreasing with NFE: {errors!r}"
        )


def test_rk4_is_deterministic() -> None:
    """Two runs with identical inputs must produce identical endpoints."""
    y_first = integrate_at_nfe(LINEAR, _rk4_step, 40)
    y_second = integrate_at_nfe(LINEAR, _rk4_step, 40)
    assert float(np.max(np.abs(y_first - y_second))) == 0.0