"""Convergence-order verification for public deterministic FM integrators.

Implements the framework-internal-metrics rev 2 §1 C.6 gate:
> Empirical convergence-order verification: every deterministic FM
> integrator achieves its claimed global-error order within 0.2 absolute
> tolerance on 3 analytic problems (linear drift, nonlinear drift,
> stiff); stochastic integrators (SDE-style) instead verified under
> C.7 SBC; behind --runslow marker, nightly only, not per-PR.

Module layout
-------------

* :mod:`tests.test_convergence.test_problems` — analytic ODE test
  problems (linear / nonlinear / stiff) with exact closed-form
  solutions and per-problem :func:`integrate_at_nfe` helpers that
  integrate a callable velocity field with an arbitrary integrator
  on a uniform NFE grid.
* :mod:`tests.test_convergence.test_heun_convergence` — Heun
  integrator (claimed order 2).
* :mod:`tests.test_convergence.test_rk4_convergence` — RK4
  integrator (claimed order 4).
* :mod:`tests.test_convergence.test_midpoint_convergence` —
  Midpoint (RK2) integrator (claimed order 2). The midpoint
  integrator is a local test helper because the framework does not
  ship a dedicated public midpoint integrator; the convergence
  reference serves as a SciML-style control on the order-2 slot
  that Heun also occupies.
* :mod:`tests.test_convergence.test_euler_convergence` — explicit
  Euler integrator (claimed order 1). Euler is exercised through
  :class:`adaptive_reflow.adapters.integrators.AMEDSolverIntegrator`
  which is the order-1 forward-Euler building block used by the
  AMED-Solver diff-sampler (see ``integrators.py`` docstring).
* :mod:`tests.test_convergence.test_dopri5_convergence` —
  Dormand-Prince RK45 adaptive integrator (claimed order >= 5).
* :mod:`tests.test_convergence.CONVERGENCE_TARGETS` — per-integrator
  expected slopes + tolerances + exceptions for stochastic / non-
  classical integrators.

Method (per SciML's ``test_convergence`` pattern)
-------------------------------------------------

For each ``(integrator, problem)`` pair:

1. Sweep NFE in ``{10, 20, 40, 80, 160, 320}``.
2. Integrate from ``t=0`` to ``t=1`` (or ``t=0.1`` for the stiff
   problem to keep the exponential well-sampled) on a uniform grid
   of NFE points with the integrator's per-step callable.
3. Compute global error = ``max(|y_end - y_exact(end)|)`` (L-infinity
   at the endpoint; this is the standard SciML convention for
   scalar / 1-D ODE convergence sweeps and avoids the noise of
   intermediate-grid interpolation).
4. Fit ``log(error)`` vs ``log(NFE)`` via least-squares.
5. Assert ``|slope - claimed_order| <= 0.2`` per the rev 2 §1 C.6
   tolerance (relaxed from the stricter 0.05 used by SciML
   ``test_convergence`` per Wave 13 verification fix).

All tests are marked ``@pytest.mark.slow`` so nightly CI runs them
while the per-PR gate stays fast. The conftest-level ``--runslow``
marker pattern is documented in :mod:`tests.conftest`.

This file is the ``__init__`` for the convergence suite and
re-exports the analytic problems so external scripts (e.g.
``scripts/run_convergence_sweep.py`` for nightly run aggregation)
can import them in one place.
"""

from __future__ import annotations

from .test_problems import (
    AnalyticProblem,
    fit_log_log_slope,
    integrate_at_nfe,
    linear_drift,
    linear_exact,
    nonlinear_drift,
    nonlinear_exact,
    stiff_drift,
    stiff_exact,
)

__all__ = (
    "AnalyticProblem",
    "linear_drift",
    "nonlinear_drift",
    "stiff_drift",
    "linear_exact",
    "nonlinear_exact",
    "stiff_exact",
    "integrate_at_nfe",
    "fit_log_log_slope",
)
