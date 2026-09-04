"""Lemma 2 sheet-tube rescaling witness (Wave 12 A1-high-2).

Paper Lemma 2 (line 100-104):

    ``eps^{-1} * int_T phi(x, y) * p_eps(x, y) dx dy
       -> (2*pi)^{-1/2} * int_R phi(s, 0) * e^{-s^2/2} / sqrt(1+g(s)^2) ds``

where ``T = {(x, y) : |y| <= 1/2}`` and

    ``p_eps(x, y) = (2*pi)^{-1} exp(-(x^2 + y^2)/2) *
                    exp(-|F_g(x, y)|^2 / (2 eps^2))``

with ``|F_g(x, y)|^2 = y^2 * (g(x)^2 + (y-1)^2)`` (paper line 142-144,
the literal residual geometry).

The framework previously implemented only the RHS (the limit object)
in ``adaptive_reflow.eval.fid_theorem_aligned._analytic_nu_g_gaussian``;
this module adds a *finite-eps* LHS evaluator so the Lemma 2
rescaling is witnessed end-to-end: the LHS Monte-Carlo is computed
via 2D-grid quadrature on a rectangle ``x in [-K_x, K_x]`` and
``y in [-1/2, 1/2]``, then divided by the paper RHS to yield a
ratio that converges to 1.0 as ``eps -> 0``.

:func:`sheet_tube_evidence` returns that ratio as a ``float``.

Stdlib-only.
"""
from __future__ import annotations

import math
from collections.abc import Callable

__all__ = ["sheet_tube_evidence"]


def sheet_tube_evidence(
    g: Callable[[float], float],
    eps: float,
    phi: Callable[[float, float], float],
    *,
    n_x: int = 256,
    n_y_per_unit_eps: int = 64,
    K_x: float = 8.0,
) -> float:
    """Return ``LHS / RHS`` for Lemma 2 at finite ``eps``.

    Evaluates the LHS Monte-Carlo

        LHS = (1/eps) * (2*pi)^{-1} *
              int_{x in [-K_x, K_x]} int_{y in [-1/2, 1/2]}
                  phi(x, y) * exp(-(x^2 + y^2)/2) *
                  exp(-y^2 (g(x)^2 + (y-1)^2) / (2 eps^2)) dy dx

    by 2D-grid trapezoidal quadrature on a uniform grid with ``n_x``
    points in x and ``n_y = max(64, ceil(n_y_per_unit_eps / eps))``
    points in y (so the y-resolution scales with the Gaussian peak
    width ``~ eps / sqrt(1 + g(x)^2)``).

    Evaluates the RHS

        RHS = (2*pi)^{-1/2} *
              int_R phi(s, 0) * exp(-s^2/2) / sqrt(1 + g(s)^2) ds

    by 1D trapezoidal quadrature on the same x-window ``[-K_x, K_x]``
    with ``n_x_rhs`` points.

    Returns ``LHS / RHS``. By Lemma 2 this ratio converges to 1.0 as
    ``eps -> 0`` for any bounded continuous ``phi`` (and any
    F-side-admissible ``g``).

    Parameters
    ----------
    g
        The profile ``R -> R``. Need not be uniformly separated; the
        Lemma 2 limit is a sheet-tube statement and does not require
        root-cell F-side conditions.
    eps
        The finite ``eps`` at which to evaluate Lemma 2.
    phi
        A bounded continuous test function ``R^2 -> R``.
    n_x
        Number of x-grid points (used for both LHS and RHS).
    n_y_per_unit_eps
        Density of y-grid points per unit ``1/eps``. Total
        ``n_y = max(64, ceil(n_y_per_unit_eps / eps))`` so the grid
        resolves the Gaussian peak at small ``eps``.
    K_x
        Half-width of the x-integration window. ``8.0`` truncates the
        Gaussian at ``8`` standard deviations, sub-1e-14 truncation
        error.

    Returns
    -------
    float
        ``LHS / RHS``. Converges to 1.0 as ``eps -> 0``.

    Raises
    ------
    ValueError
        If ``eps <= 0`` or grid sizes are non-positive.
    """
    if eps <= 0.0:
        raise ValueError(f"eps must be positive, got {eps!r}")
    if n_x < 4:
        raise ValueError(f"n_x must be >= 4, got {n_x!r}")
    if K_x <= 0.0:
        raise ValueError(f"K_x must be positive, got {K_x!r}")
    if n_y_per_unit_eps < 4:
        raise ValueError(
            f"n_y_per_unit_eps must be >= 4, got {n_y_per_unit_eps!r}"
        )

    n_y = max(64, int(math.ceil(n_y_per_unit_eps / float(eps))))
    hx = (2.0 * float(K_x)) / float(n_x)
    hy = 1.0 / float(n_y)  # y in [-1/2, 1/2]
    inv_2pi = 1.0 / (2.0 * math.pi)
    inv_2eps2 = 1.0 / (2.0 * float(eps) * float(eps))

    # ---- LHS: 2D trapezoidal over x in [-K_x, K_x], y in [-1/2, 1/2]
    lhs_total = 0.0
    for i in range(n_x + 1):
        x = -float(K_x) + i * hx
        wx = 0.5 if (i == 0 or i == n_x) else 1.0
        gx = float(g(x))
        gx2 = gx * gx
        for j in range(n_y + 1):
            y = -0.5 + j * hy
            wy = 0.5 if (j == 0 or j == n_y) else 1.0
            ym1 = y - 1.0
            # Paper residual: |F_g|^2 = y^2 * (g(x)^2 + (y-1)^2).
            F_g_sq = (y * y) * (gx2 + ym1 * ym1)
            log_p = -0.5 * (x * x + y * y) - F_g_sq * inv_2eps2
            if log_p < -50.0:
                # Negligible contribution; skip.
                continue
            p = inv_2pi * math.exp(log_p)
            lhs_total += wx * wy * float(phi(x, y)) * p
    lhs_total *= hx * hy
    lhs = lhs_total / float(eps)

    # ---- RHS: (2*pi)^{-1/2} * int_R phi(s, 0) e^{-s^2/2} / sqrt(1+g(s)^2) ds
    inv_sqrt_2pi = 1.0 / math.sqrt(2.0 * math.pi)
    rhs_total = 0.0
    for k in range(n_x + 1):
        s = -float(K_x) + k * hx
        ws = 0.5 if (k == 0 or k == n_x) else 1.0
        gx = float(g(s))
        denom = math.sqrt(1.0 + gx * gx)
        integrand = float(phi(s, 0.0)) * math.exp(-0.5 * s * s) / denom
        rhs_total += ws * integrand
    rhs_total *= hx
    rhs = inv_sqrt_2pi * rhs_total

    denom = max(abs(rhs), 1e-30)
    return float(lhs / rhs)