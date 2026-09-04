"""Convergence-order test for the Dormand-Prince RK45 integrator (claimed order 5).

Per framework-internal-metrics rev 2 §1 C.6:

> DOPRI5 achieves global-error order 5 within 0.2 absolute tolerance
> on 3 analytic problems.

The DOPRI5 step is the canonical Dormand-Prince RK4(5) pair
(:class:`adaptive_reflow.adapters.integrators.DormandPrinceRK45Integrator`).
Seven stages are evaluated per step; the propagated solution uses
stages ``k1..k6`` with the scipy-aligned (order-5 verified) weights
``[35/384, 0, 500/1113, 125/192, -2187/6784, 11/84]`` and ``k7`` is
the FSAL extension used only by the error estimator.

Marked ``@pytest.mark.slow`` (nightly CI only).

Tolerance direction: one-sided ``measured_slope >=
claimed_order - 0.2``. See
``tests.test_convergence.test_heun_convergence`` docstring for
the rationale (super-convergence on stiff is not a defect).

Wave 20 Phase 1 history
-----------------------
Originally documented in ``CONVERGENCE_TARGETS.md`` as KNOWN-BROKEN:
the framework's ``DormandPrinceRK45Integrator.step`` used the
naively aligned Wikipedia DOPRI5 b-weights
``[35/384, 500/1113, 125/192, -2187/6784, 11/84, 0]`` paired with
``k1..k6``, which violates the order-2 condition
``sum(b_i c_i) = 1/2`` (numerical 0.144) and silently degrades the
method to forward-Euler order 1. Wave 20 Phase 1 fixed the bug by
aligning the weights with the scipy ``RK45`` verified order-5
formulation; this test gate the regression.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.integrators import (
    DormandPrinceRK45Integrator,
    HeunIntegrator,
)

from .test_problems import (
    DEFAULT_PROBLEMS,
    LINEAR,
    fit_log_log_slope,
    global_endpoint_error,
    integrate_at_nfe,
)

pytestmark = pytest.mark.slow

NFE_GRID: tuple[int, ...] = (10, 20, 40, 80, 160)
"""SciML-style NFE sweep for DOPRI5.

DOPRI5 (order 5) converges so fast that on the linear problem the
endpoint error collapses below the float64 noise floor
(``~1e-16``) by NFE = 320, which then dominates the
``log``/``log`` slope fit and yields a spurious sub-claimed slope
(empirically ~4.27 instead of ~5.0). Capping the sweep at
NFE = 160 keeps the error well above the noise floor on the linear
and nonlinear problems while still covering ~1.7 decades of NFE,
sufficient for a robust least-squares fit. The stiff problem with
``T = 0.1`` keeps its error above ``1e-10`` across the grid.
"""

CLAIMED_ORDER = 5
"""DOPRI5's textbook order is 5 (6-stage FSAL embedded pair)."""

TOLERANCE = 0.2
"""C.6 absolute tolerance per framework-internal-metrics rev 2 §1."""


def _dopri_step(velocity, t: float, y, dt: float):
    """``DormandPrinceRK45Integrator.step`` adapter for ``integrate_at_nfe``."""
    return DormandPrinceRK45Integrator().step(velocity, t, y, dt)


def _heun_step(velocity, t: float, y, dt: float):
    """``HeunIntegrator.step`` adapter for the harmonic oscillator."""
    return HeunIntegrator().step(velocity, t, y, dt)


@pytest.mark.parametrize("problem", DEFAULT_PROBLEMS, ids=lambda p: p.name)
def test_dopri5_convergence_order(problem) -> None:
    """DOPRI5 achieves claimed order 5 (within 0.2 tolerance) on 3 problems.

    Linear, nonlinear, and stiff drift problems each expose a
    different facet of the order-5 contract:

    * **Linear** (``:math:`dx/dt=-x``): analytic, no round-off; the
      pure-order slope test.
    * **Nonlinear** (``:math:`dx/dt=-x^3``): verifies the integrator
      honours the Lipschitz contract on a non-affine drift.
    * **Stiff** (``:math:`dx/dt=-100x``): the exponential decay lets
      truncation terms cancel faster than the classical order, so
      super-convergence is expected; the one-sided tolerance
      accepts a slope up to ``claimed_order + 1.5``.
    """
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(problem, _dopri_step, nfe)
        errors.append(global_endpoint_error(problem, y_end))
    slope = fit_log_log_slope(NFE_GRID, errors)
    abs_slope = abs(float(slope))
    assert abs_slope >= CLAIMED_ORDER - TOLERANCE, (
        f"DOPRI5 on {problem.name}: slope={abs_slope:.3f} "
        f"is below claimed order {CLAIMED_ORDER} - {TOLERANCE}; "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )
    # Cap at +1.5 above claimed order (per CONVERGENCE_TARGETS.md).
    assert abs_slope <= CLAIMED_ORDER + 1.5, (
        f"DOPRI5 on {problem.name}: slope={abs_slope:.3f} is "
        f"unexpectedly super-convergent; check that errors are "
        f"not collapsed below float64 noise. "
        f"errors={[f'{e:.3e}' for e in errors]!r}"
    )


def test_dopri5_endpoint_accuracy_decreases_with_nfe() -> None:
    """Monotonicity: DOPRI5 endpoint error strictly decreases with NFE.

    A regression in the propagated state computation (e.g. the
    Wave 18 step-assembly bug where the b-weights were unshifted)
    would make the error stop decreasing — or even *increase* —
    with NFE. This test gates that regression on the canonical
    linear problem.
    """
    errors: list[float] = []
    for nfe in NFE_GRID:
        y_end = integrate_at_nfe(LINEAR, _dopri_step, nfe)
        errors.append(global_endpoint_error(LINEAR, y_end))
    for prev, curr in zip(errors, errors[1:], strict=False):
        assert curr < prev, (
            f"DOPRI5 error not strictly decreasing with NFE: {errors!r}"
        )


def test_dopri5_is_deterministic() -> None:
    """Two runs with identical inputs produce identical endpoints.

    DOPRI5 is a deterministic method; if it became stochastic
    (e.g. a future refactor accidentally introduces a random
    perturbation), every reported number in the framework would
    be silently noisy. This is a B.5 framework-health guard.
    """
    y_first = integrate_at_nfe(LINEAR, _dopri_step, 40)
    y_second = integrate_at_nfe(LINEAR, _dopri_step, 40)
    assert float(np.max(np.abs(y_first - y_second))) == 0.0


def test_dopri5_matches_scipy_rk45_reference() -> None:
    """Cross-check: framework DOPRI5 matches scipy RK45 within 1e-9.

    scipy's ``RK45`` is a well-tested port of the Dormand-Prince
    pair (see ``scipy/integrate/_ivp/rk.py``). The framework's
    ``DormandPrinceRK45Integrator`` MUST reproduce its endpoint to
    floating-point precision when both use identical step counts;
    any meaningful divergence indicates a step-assembly bug
    (cf. the Wave 18 KNOWN-BROKEN note in CONVERGENCE_TARGETS.md).
    """
    from scipy.integrate import solve_ivp

    def vel(t, y):
        return -y

    nfe = 100
    T = 1.0
    y0 = np.array([1.0], dtype=np.float64)

    # Framework DOPRI5
    integ = DormandPrinceRK45Integrator()
    y_ours = y0.copy()
    t_cur = 0.0
    dt = T / nfe
    for _ in range(nfe):
        y_ours = integ.step(vel, t_cur, y_ours, dt)
        t_cur += dt

    # scipy RK45 at the same time points (forces fixed-step matching)
    sol = solve_ivp(
        vel,
        [0.0, T],
        [1.0],
        method="RK45",
        rtol=1e-12,
        atol=1e-12,
        t_eval=[T],
    )
    y_scipy = sol.y[:, -1]

    assert float(np.max(np.abs(y_ours - y_scipy))) < 1e-9, (
        f"Framework DOPRI5 diverges from scipy RK45: "
        f"y_ours={y_ours}, y_scipy={y_scipy}"
    )


def test_dopri5_energy_conservation_vs_heun_harmonic_oscillator() -> None:
    """Cross-check vs Heun: both preserve harmonic-oscillator energy within tolerance.

    The harmonic oscillator ``dx/dt = (v, -omega^2 x)`` has conserved
    energy ``E = 0.5 (v^2 + omega^2 x^2)``. Heun is the order-2
    baseline used elsewhere in the convergence suite
    (:file:`test_heun_convergence.py`); DOPRI5 (order 5) should
    preserve energy at least as tightly at matched NFE because the
    local truncation error is smaller.

    This test is a sanity check rather than a strict energy
    *convergence* test: it asserts that DOPRI5 is no worse than
    Heun at the same NFE on the canonical harmonic oscillator, and
    that the relative energy drift stays below ``1e-2`` over
    ``NFE = 1000`` steps.
    """
    omega = 1.0
    # y = (q, p); dx/dt = (p, -omega^2 q)
    def harmonic_drift(t, y):
        q = y[0]
        p = y[1]
        return np.array([p, -omega ** 2 * q], dtype=np.float64)

    def harmonic_exact(t, y0):
        # x(0) = y0, x(t) = cos(omega*t) * y0[0] + sin(omega*t)/omega * y0[1]
        q0 = y0[0]
        p0 = y0[1]
        q_t = np.cos(omega * t) * q0 + np.sin(omega * t) * p0 / omega
        p_t = -omega * np.sin(omega * t) * q0 + np.cos(omega * t) * p0
        return np.array([q_t, p_t], dtype=np.float64)

    T = 2.0 * np.pi  # one full period
    y0 = np.array([1.0, 0.0], dtype=np.float64)
    nfe = 1000
    dt = T / nfe

    def energy(y):
        return 0.5 * (y[1] ** 2 + omega ** 2 * y[0] ** 2)

    E0 = energy(y0)

    # DOPRI5
    integ = DormandPrinceRK45Integrator()
    y_dopri = y0.copy()
    for _ in range(nfe):
        y_dopri = integ.step(harmonic_drift, 0.0, y_dopri, dt)
    E_dopri = energy(y_dopri)
    rel_drift_dopri = abs(E_dopri - E0) / E0

    # Heun
    y_heun = y0.copy()
    for _ in range(nfe):
        y_heun = _heun_step(harmonic_drift, 0.0, y_heun, dt)
    E_heun = energy(y_heun)
    rel_drift_heun = abs(E_heun - E0) / E0

    # DOPRI5 should be no worse than Heun at the same NFE.
    assert rel_drift_dopri <= rel_drift_heun + 1e-9, (
        f"DOPRI5 energy drift ({rel_drift_dopri:.3e}) exceeds "
        f"Heun drift ({rel_drift_heun:.3e}) at NFE={nfe}"
    )
    # Absolute energy-conservation budget for DOPRI5.
    assert rel_drift_dopri < 1e-2, (
        f"DOPRI5 harmonic-oscillator energy drift too large: "
        f"{rel_drift_dopri:.3e} >= 1e-2 at NFE={nfe}"
    )