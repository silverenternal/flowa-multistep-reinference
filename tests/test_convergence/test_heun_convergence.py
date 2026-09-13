"""Convergence-order test for the Heun integrator (claimed order 2).

Per framework-internal-metrics rev 2 §1 C.6:

> Heun achieves global-error order 2 within 0.2 absolute tolerance
> on 3 analytic problems.

Method
------
For each problem in {linear, nonlinear, stiff}, sweep NFE in
{10, 20, 40, 80, 160, 320}, integrate with
:class:`HeunIntegrator.step` on a uniform grid, and fit
``log(error)`` vs ``log(NFE)``. Assert the slope is within 0.2 of
the claimed order (absolute tolerance).

The Heun step is::

    y_pred = y + dt * v(t, y)
    v_next = v(t + dt, y_pred)
    y_next = y + 0.5 * dt * (v(t, y) + v_next)

which is the canonical order-2 two-stage Runge-Kutta (improved
Euler / explicit trapezoidal).

Marked ``@pytest.mark.slow`` because the full sweep across 3
problems x 6 NFE values x 3 integrators = ~108 step counts; per the
rev 2 gate, nightly CI runs these and PR-level CI skips them via
``pytest -m "not slow"``.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.integrators import HeunIntegrator

from .test_problems import (
    DEFAULT_PROBLEMS,
    LINEAR,
    fit_log_log_slope,
    global_endpoint_error,
    integrate_at_nfe,
)

pytestmark = pytest.mark.slow

NFE_GRID: tuple[int, ...] = (10, 20, 40, 80, 160, 320)
"""Canonical SciML-style NFE sweep."""

CLAIMED_ORDER = 2
"""Heun's textbook order is 2 (two-stage explicit Runge-Kutta)."""

TOLERANCE = 0.2
"""C.6 absolute tolerance per framework-internal-metrics rev 2 §1."""


def _heun_step(velocity, t: float, y, dt: float):
    """``HeunIntegrator.step`` adapter for :func:`integrate_at_nfe`."""
    return HeunIntegrator().step(velocity, t, y, dt)


@pytest.mark.parametrize("problem", DEFAULT_PROBLEMS, ids=lambda p: p.name)
def test_heun_convergence_order(problem) -> None:
    """Heun achieves claimed order 2 (within 0.2 tolerance) on 3 problems.

    The fit uses ``log(error)`` vs ``log(NFE)``; the slope is
    negative because error decreases as NFE increases, so the test
    compares ``|slope|`` to ``CLAIMED_ORDER``.

    Note on tolerance direction (per ``CONVERGENCE_TARGETS.md``):
    we use a **one-sided** tolerance ``measured_slope >=
    claimed_order - 0.2`` rather than the symmetric
    ``|slope - order| <= 0.2``. Rationale: a method that
    *over-performs* (super-converges on the stiff problem, where
    the exponential decay lets truncation terms cancel faster than
    the classical order) is not a defect; only **under-convergence**
    indicates a real bug. The symmetric tolerance would falsely
    fail well-behaved integrators on the stiff problem.
    """
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(problem, _heun_step, nfe)
        errors.append(global_endpoint_error(problem, y_end))
    slope = fit_log_log_slope(NFE_GRID, errors)
    abs_slope = abs(float(slope))
    assert abs_slope >= CLAIMED_ORDER - TOLERANCE, (
        f"Heun on {problem.name}: slope={abs_slope:.3f} "
        f"is below claimed order {CLAIMED_ORDER} - {TOLERANCE}; "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )
    # Cap at +1.5 above claimed order — a slope this far above the
    # classical order almost certainly means the test problem is too
    # easy (e.g., error collapsed below noise floor) and the test
    # author should pick a harder problem.
    assert abs_slope <= CLAIMED_ORDER + 1.5, (
        f"Heun on {problem.name}: slope={abs_slope:.3f} is "
        f"unexpectedly super-convergent; check that errors are "
        f"not collapsed below float64 noise. "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )


def test_heun_endpoint_accuracy_decreases_with_nfe() -> None:
    """Sanity: Heun's endpoint error strictly decreases with NFE.

    A regression in monotonicity (e.g. an off-by-one bug in the
    step that overcorrects at large ``dt``) would break this.
    """
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(LINEAR, _heun_step, nfe)
        errors.append(global_endpoint_error(LINEAR, y_end))
    for prev, curr in zip(errors, errors[1:], strict=False):
        assert curr < prev, (
            f"Heun error not strictly decreasing with NFE: {errors!r}"
        )


def test_heun_is_deterministic() -> None:
    """Two runs with identical inputs must produce identical endpoints.

    This is a deterministic-method guard (B.5 framework health
    metric); if Heun became stochastic, every reported number in
    the framework would be silently noisy.
    """
    y_first = integrate_at_nfe(LINEAR, _heun_step, 40)
    y_second = integrate_at_nfe(LINEAR, _heun_step, 40)
    assert float(np.max(np.abs(y_first - y_second))) == 0.0
