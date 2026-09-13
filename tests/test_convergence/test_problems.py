"""Analytic ODE test problems for convergence-order verification (C.6).

Per framework-internal-metrics rev 2 §1 C.6, three analytic problems
cover the canonical integration scenarios:

* **Linear drift** ``dx/dt = -x`` with exact solution
  ``x(t) = x0 * exp(-t)``. Tests the basic first-order contract.
* **Nonlinear drift** ``dx/dt = -x^3`` with exact solution
  ``x(t) = x0 / sqrt(2 * x0^2 * t + 1)``. Tests that the integrator
  honours the Lipschitz / nonlinear contract (no spurious
  fixed-point drift).
* **Stiff drift** ``dx/dt = -100 * x`` with exact solution
  ``x(t) = x0 * exp(-100 * t)``. Tests stability under
  exponentially fast decay; explicit integrators above their
  stability region (e.g. Euler at large ``dt``) will diverge here.

For each problem we expose:

* ``<problem>_drift(t, y)`` — the right-hand side ``f(t, y)``.
* ``<problem>_exact(t, y0)`` — the closed-form solution at time
  ``t`` starting from ``y0``.
* :func:`integrate_at_nfe` — generic integrator driver.
* :func:`fit_log_log_slope` — least-squares ``log(error)`` vs
  ``log(NFE)`` slope fitter used by every convergence test.

All problems are 1-D scalar ODEs for two reasons: (a) the slope fit
is degenerate only when all error magnitudes collapse to noise, and
(b) it mirrors the SciML ``test_convergence`` canonical harness
which exercises 1-D ODEs so that the slope is uncontaminated by
multi-axis coupling.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Analytic problems
# ---------------------------------------------------------------------------


def linear_drift(
    t: float,
    y: NDArray[np.float64],
) -> NDArray[np.float64]:
    """``dx/dt = -x`` (linear decay).

    Parameters
    ----------
    t : float
        Current time. The drift is autonomous; ``t`` is unused.
    y : NDArray[np.float64]
        Current state (1-D, scalar or vector).

    Returns
    -------
    NDArray[np.float64]
        ``-y`` as an ndarray with the same shape as ``y``.
    """
    del t  # autonomous drift
    return -np.asarray(y, dtype=np.float64)


def linear_exact(
    t: float,
    y0: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Closed-form ``x(t) = x0 * exp(-t)`` for the linear problem.

    Parameters
    ----------
    t : float
        Evaluation time.
    y0 : NDArray[np.float64]
        Initial condition at ``t = 0``.

    Returns
    -------
    NDArray[np.float64]
        ``y0 * exp(-t)``.
    """
    return np.asarray(y0, dtype=np.float64) * np.exp(-float(t))


def nonlinear_drift(
    t: float,
    y: NDArray[np.float64],
) -> NDArray[np.float64]:
    """``dx/dt = -x^3`` (nonlinear decay).

    Parameters
    ----------
    t : float
        Current time. The drift is autonomous; ``t`` is unused.
    y : NDArray[np.float64]
        Current state (1-D, scalar or vector).

    Returns
    -------
    NDArray[np.float64]
        ``-y^3`` as an ndarray with the same shape as ``y``.
    """
    del t  # autonomous drift
    y_arr = np.asarray(y, dtype=np.float64)
    return -(y_arr ** 3)


def nonlinear_exact(
    t: float,
    y0: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Closed-form ``x(t) = x0 / sqrt(2 * x0^2 * t + 1)``.

    Derivation: separating variables on ``dx/dt = -x^3`` gives
    ``-dx / x^3 = dt``, integrating yields
    ``1 / x^2 = 2 * t + C`` with ``C = 1 / x0^2``, so
    ``x(t) = x0 / sqrt(2 * x0^2 * t + 1)``.

    Parameters
    ----------
    t : float
        Evaluation time.
    y0 : NDArray[np.float64]
        Initial condition at ``t = 0``.

    Returns
    -------
    NDArray[np.float64]
        ``y0 / sqrt(2 * y0^2 * t + 1)``.
    """
    y_arr = np.asarray(y0, dtype=np.float64)
    denom = np.sqrt(2.0 * y_arr ** 2 * float(t) + 1.0)
    return y_arr / denom


def stiff_drift(
    t: float,
    y: NDArray[np.float64],
) -> NDArray[np.float64]:
    """``dx/dt = -100 * x`` (stiff decay).

    The Lipschitz constant ``|df/dy| = 100`` is large enough that
    explicit integrators (Euler / Heun) at the largest NFE will
    still show stability-bound error, while adaptive integrators
    (DOPRI5) and high-order methods (RK4) recover the canonical
    order.

    Parameters
    ----------
    t : float
        Current time. The drift is autonomous; ``t`` is unused.
    y : NDArray[np.float64]
        Current state (1-D, scalar or vector).

    Returns
    -------
    NDArray[np.float64]
        ``-100 * y`` as an ndarray with the same shape as ``y``.
    """
    del t  # autonomous drift
    return -100.0 * np.asarray(y, dtype=np.float64)


def stiff_exact(
    t: float,
    y0: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Closed-form ``x(t) = x0 * exp(-100 * t)`` for the stiff problem.

    Parameters
    ----------
    t : float
        Evaluation time.
    y0 : NDArray[np.float64]
        Initial condition at ``t = 0``.

    Returns
    -------
    NDArray[np.float64]
        ``y0 * exp(-100 * t)``.
    """
    return np.asarray(y0, dtype=np.float64) * np.exp(-100.0 * float(t))


# ---------------------------------------------------------------------------
# Dataclass binding drift + exact solution + initial condition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalyticProblem:
    """Binding of drift, exact solution, initial condition, and horizon.

    Attributes
    ----------
    name : str
        Human-readable problem identifier (``"linear"``, ``"nonlinear"``,
        ``"stiff"``).
    drift : Callable[[float, NDArray[np.float64]], NDArray[np.float64]]
        The right-hand side ``f(t, y)``.
    exact : Callable[[float, NDArray[np.float64]], NDArray[np.float64]]
        Closed-form solution ``x(t; x0)``.
    y0 : NDArray[np.float64]
        Initial condition at ``t = 0``. Set to ``[1.0]`` for the
        canonical 1-D scalar sweep.
    horizon : float
        Final time ``T`` for the convergence sweep. Default ``1.0``
        for linear / nonlinear; stiff uses ``0.1`` to keep the
        exponential from collapsing below the noise floor before
        the integrator converges.
    """

    name: str
    drift: Callable[[float, NDArray[np.float64]], NDArray[np.float64]]
    exact: Callable[[float, NDArray[np.float64]], NDArray[np.float64]]
    y0: NDArray[np.float64]
    horizon: float


LINEAR: Final[AnalyticProblem] = AnalyticProblem(
    name="linear",
    drift=linear_drift,
    exact=linear_exact,
    y0=np.asarray([1.0], dtype=np.float64),
    horizon=1.0,
)
"""Linear drift problem ``dx/dt = -x``, horizon 1.0."""

NONLINEAR: Final[AnalyticProblem] = AnalyticProblem(
    name="nonlinear",
    drift=nonlinear_drift,
    exact=nonlinear_exact,
    y0=np.asarray([1.0], dtype=np.float64),
    horizon=1.0,
)
"""Nonlinear drift problem ``dx/dt = -x^3``, horizon 1.0."""

STIFF: Final[AnalyticProblem] = AnalyticProblem(
    name="stiff",
    drift=stiff_drift,
    exact=stiff_exact,
    y0=np.asarray([1.0], dtype=np.float64),
    horizon=0.1,
)
"""Stiff drift problem ``dx/dt = -100 x``, horizon 0.1.

The shorter horizon (``T = 0.1``) keeps the exact solution
``exp(-10) ≈ 4.5e-5`` above the float64 noise floor; if we used
``T = 1.0`` the exact endpoint would be ``exp(-100) ≈ 0`` and the
error fit would degenerate to noise.
"""

DEFAULT_PROBLEMS: Final[tuple[AnalyticProblem, ...]] = (LINEAR, NONLINEAR, STIFF)
"""Canonical 3-problem sweep tuple used by every convergence test."""


# ---------------------------------------------------------------------------
# Integration driver
# ---------------------------------------------------------------------------


def integrate_at_nfe(
    problem: AnalyticProblem,
    step_fn: Callable[
        [
            Callable[[float, NDArray[np.float64]], NDArray[np.float64]],
            float,
            NDArray[np.float64],
            float,
        ],
        NDArray[np.float64],
    ],
    nfe: int,
) -> NDArray[np.float64]:
    """Integrate ``problem`` on a uniform NFE grid with ``step_fn``.

    Parameters
    ----------
    problem : AnalyticProblem
        The analytic test problem (drift + initial condition + horizon).
    step_fn : Callable
        A function matching the
        :class:`adaptive_reflow.adapters.integrators.IntegratorProtocol`
        ``step(velocity, t, y, dt)`` signature: given the
        right-hand side ``velocity(t, y)`` and the current state
        ``(t, y, dt)``, return the next state ``y_{n+1}``.
    nfe : int
        Number of function-evaluations, i.e. number of sub-steps
        taken across ``[0, horizon]``. ``nfe >= 2`` is required.

    Returns
    -------
    NDArray[np.float64]
        The endpoint state ``y(T)``.
    """
    if int(nfe) < 2:
        raise ValueError(f"nfe must be >= 2, got {nfe!r}")
    t_grid = np.linspace(
        float(problem.horizon) / float(nfe),
        float(problem.horizon),
        int(nfe),
        dtype=np.float64,
    )
    t_full = np.concatenate(
        [np.asarray([0.0], dtype=np.float64), t_grid]
    )
    y_cur = np.asarray(problem.y0, dtype=np.float64).copy()
    for k in range(1, t_full.shape[0]):
        dt = float(t_full[k] - t_full[k - 1])
        y_cur = step_fn(problem.drift, float(t_full[k - 1]), y_cur, dt)
    return y_cur


def global_endpoint_error(
    problem: AnalyticProblem,
    y_end: NDArray[np.float64],
) -> float:
    """L-infinity endpoint error ``max(|y_end - y_exact(T)|)``.

    Parameters
    ----------
    problem : AnalyticProblem
        The analytic test problem.
    y_end : NDArray[np.float64]
        The integrator endpoint state.

    Returns
    -------
    float
        ``float(np.max(np.abs(y_end - problem.exact(T, problem.y0))))``.
    """
    y_ex = problem.exact(problem.horizon, problem.y0)
    return float(np.max(np.abs(np.asarray(y_end) - y_ex)))


# ---------------------------------------------------------------------------
# Convergence slope fitter
# ---------------------------------------------------------------------------


def fit_log_log_slope(
    nfe_grid: NDArray[np.int64] | tuple[int, ...],
    errors: NDArray[np.float64] | tuple[float, ...],
) -> float:
    """Fit ``log(error) = slope * log(NFE) + intercept`` via least squares.

    Errors are filtered to those strictly positive (zero error at
    infinite resolution collapses the log). If fewer than 2 valid
    points survive, return ``0.0`` (the test author should treat
    this as a degenerate case — usually a sign that the integrator
    has already converged to machine precision).

    Parameters
    ----------
    nfe_grid : array-like of int
        Sequence of NFE values, e.g. ``(10, 20, 40, 80, 160, 320)``.
    errors : array-like of float
        Endpoint L-infinity errors at each NFE.

    Returns
    -------
    float
        Least-squares slope. Order-1 methods yield slopes near 1.0,
        order-2 near 2.0, etc.
    """
    nfe_arr = np.asarray(nfe_grid, dtype=np.float64)
    err_arr = np.asarray(errors, dtype=np.float64)
    if nfe_arr.shape != err_arr.shape:
        raise ValueError(
            f"shape mismatch: nfe_grid {nfe_arr.shape!r} "
            f"vs errors {err_arr.shape!r}"
        )
    mask = err_arr > 0.0
    if int(np.sum(mask)) < 2:
        return 0.0
    log_nfe = np.log(nfe_arr[mask])
    log_err = np.log(err_arr[mask])
    # Least-squares fit log_err = slope * log_nfe + intercept.
    x_mean = float(np.mean(log_nfe))
    y_mean = float(np.mean(log_err))
    num = float(np.sum((log_nfe - x_mean) * (log_err - y_mean)))
    den = float(np.sum((log_nfe - x_mean) ** 2))
    if den <= 0.0:
        return 0.0
    return num / den


__all__ = (
    "AnalyticProblem",
    "DEFAULT_PROBLEMS",
    "LINEAR",
    "NONLINEAR",
    "STIFF",
    "fit_log_log_slope",
    "global_endpoint_error",
    "integrate_at_nfe",
    "linear_drift",
    "linear_exact",
    "nonlinear_drift",
    "nonlinear_exact",
    "stiff_drift",
    "stiff_exact",
)
