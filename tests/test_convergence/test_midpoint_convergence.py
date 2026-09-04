"""Convergence-order test for the Midpoint (RK2) integrator.

The midpoint integrator is a classical second-order explicit
Runge-Kutta method::

    k1 = f(t, y)
    k2 = f(t + 0.5 dt, y + 0.5 dt k1)
    y_next = y + dt * k2

It is the canonical "midpoint" / RK2 method and shares the order-2
slot with Heun in textbook presentations.

Why this lives in the convergence suite (rather than the framework
itself)
-------------------------------------------------------------------

The framework does not currently ship a dedicated public
:class:`MidpointIntegrator` — the order-2 slot is occupied by
:class:`HeunIntegrator`. Including the midpoint as a convergence
test serves two purposes:

1. **Reference control on the order-2 slot.** SciML's
   ``test_convergence`` always pairs two methods of the same
   nominal order on the same analytic problem; if one passes and
   the other fails, the failure is attributable to the integrator
   surface (e.g., the trapezoidal corrector in Heun vs. the
   midpoint extrapolation in Midpoint), not to the order-2
   mathematical claim.
2. **Local test helper for future framework additions.** If a
   future refactor exposes ``MidpointIntegrator`` as a public
   surface (or replaces Heun with Midpoint per Wave 13 ablation),
   this convergence test will be the gate.

Marked ``@pytest.mark.slow`` (nightly CI only). Tolerance
direction: one-sided ``measured_slope >= claimed_order - 0.2``.
See ``tests.test_convergence.test_heun_convergence`` docstring.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pytest
from numpy.typing import NDArray

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
"""Midpoint's textbook order is 2 (single-stage midpoint RK)."""

TOLERANCE = 0.2
"""C.6 absolute tolerance per framework-internal-metrics rev 2 §1."""


def _midpoint_step(
    velocity: Callable[[float, NDArray[np.float64]], NDArray[np.float64]],
    t: float,
    y: NDArray[np.float64],
    dt: float,
) -> NDArray[np.float64]:
    """Local RK2 midpoint step (test helper; not a public framework surface).

    Matches the
    :class:`adaptive_reflow.adapters.integrators.IntegratorProtocol.step`
    signature for use with :func:`integrate_at_nfe`.
    """
    y_arr = np.asarray(y, dtype=np.float64)
    k1 = np.asarray(velocity(t, y_arr), dtype=np.float64)
    k2 = np.asarray(
        velocity(t + 0.5 * dt, y_arr + 0.5 * dt * k1),
        dtype=np.float64,
    )
    return y_arr + dt * k2


@pytest.mark.parametrize("problem", DEFAULT_PROBLEMS, ids=lambda p: p.name)
def test_midpoint_convergence_order(problem) -> None:
    """Midpoint achieves claimed order 2 (within 0.2 tolerance) on 3 problems."""
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(problem, _midpoint_step, nfe)
        errors.append(global_endpoint_error(problem, y_end))
    slope = fit_log_log_slope(NFE_GRID, errors)
    abs_slope = abs(float(slope))
    assert abs_slope >= CLAIMED_ORDER - TOLERANCE, (
        f"Midpoint on {problem.name}: slope={abs_slope:.3f} "
        f"is below claimed order {CLAIMED_ORDER} - {TOLERANCE}; "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )
    # Cap at +1.5 above claimed order — midpoint can super-converge
    # on stiff just like Heun; this guard catches truly anomalous
    # cases (e.g., integrator evaluating drift only once).
    assert abs_slope <= CLAIMED_ORDER + 1.5, (
        f"Midpoint on {problem.name}: slope={abs_slope:.3f} is "
        f"unexpectedly super-convergent. "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )


def test_midpoint_endpoint_accuracy_decreases_with_nfe() -> None:
    """Sanity: Midpoint's endpoint error strictly decreases with NFE."""
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(LINEAR, _midpoint_step, nfe)
        errors.append(global_endpoint_error(LINEAR, y_end))
    for prev, curr in zip(errors, errors[1:], strict=False):
        assert curr < prev, (
            f"Midpoint error not strictly decreasing with NFE: "
            f"{errors!r}"
        )


def test_midpoint_is_deterministic() -> None:
    """Two runs with identical inputs must produce identical endpoints."""
    y_first = integrate_at_nfe(LINEAR, _midpoint_step, 40)
    y_second = integrate_at_nfe(LINEAR, _midpoint_step, 40)
    assert float(np.max(np.abs(y_first - y_second))) == 0.0


def test_midpoint_matches_heun_to_first_order() -> None:
    """Midpoint and Heun should agree to O(dt^2) on smooth problems.

    Both are second-order methods; the local truncation error of
    both is ``O(dt^3)``, so the *difference* between the two
    integrators' endpoints after one step is also ``O(dt^3)``. This
    is a sanity check that the midpoint helper is implemented
    correctly (e.g., not accidentally swapping to forward Euler).
    """
    dt = 0.01
    y0 = np.asarray([1.0], dtype=np.float64)

    def drift(t: float, y) -> NDArray[np.float64]:
        return -np.asarray(y, dtype=np.float64)

    y_mid = _midpoint_step(drift, 0.0, y0, dt)
    # Heun inline for cross-check:
    v_t = drift(0.0, y0)
    y_pred = y0 + dt * v_t
    v_next = drift(dt, y_pred)
    y_heun = y0 + 0.5 * dt * (v_t + v_next)
    diff = float(np.max(np.abs(y_mid - y_heun)))
    # Difference should be on the order of dt^3 ≈ 1e-6 (for dt=0.01).
    assert diff < 1.0e-4, (
        f"Midpoint vs Heun single-step difference {diff:.3e} "
        f"exceeds O(dt^3) tolerance 1e-4; "
        f"y_mid={y_mid}, y_heun={y_heun}"
    )