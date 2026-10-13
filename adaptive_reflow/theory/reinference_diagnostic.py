"""Re-inference diagnostics for Theorem 4 (conditional contraction) and
Theorem 5 (exact restart-blend error identity).

Motivation (GAP-09)
-------------------

Wave 372 replaced the retracted FID-sign "Theorem 5" with two conditional,
*measurable* statements (paper §6.5–§6.6):

* **Theorem 4** — the round map ``G_b(x) = Phi_T(B_m(x, b))`` with
  ``B_m(x, b) = m x + (1 - m) b`` is a ``q``-contraction when
  ``q := m K < 1``, where ``K`` is the Lipschitz constant of the frozen flow
  map ``Phi_T`` on the invariant envelope.
* **Theorem 5** — for the convex blend ``B_m = m X + (1 - m) Y`` the exact
  identity ``E||B_m - z||^2 = m E||X - z||^2 + (1 - m) E||Y - z||^2
  - m(1 - m) E||X - Y||^2`` holds, so the blend improves squared endpoint
  error over ``X`` exactly when
  ``E||Y - z||^2 - E||X - z||^2 < m E||X - Y||^2``.

Wave 372's "remaining evidence limits" state that *the contraction condition
has not been measured on the production adapters*. This module supplies the
missing, adapter-agnostic diagnostic: estimate ``K`` by finite differences of
the integrated flow map, form ``q = m K``, and — on a cell where a target is
available — evaluate the Theorem-5 improvement condition.

Everything here is pure and additive: no existing module changes. The
functions take a plain ``velocity_fn(x, t)`` so they work for any adapter's
field (synthetic MLP, torch UNet, …) without importing torch.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "BlendIdentityReport",
    "FlowMapLipschitzReport",
    "RoundMapContractionReport",
    "blend_identity_terms",
    "contraction_variable",
    "critical_memory",
    "critical_restart_ratio",
    "estimate_flow_map_lipschitz",
    "integrate_flow",
    "round_map_contraction",
]

VelocityFn = Callable[[NDArray[np.float64], float], NDArray[np.float64]]


def integrate_flow(
    velocity_fn: VelocityFn,
    x0: NDArray[np.float64],
    *,
    t_final: float = 1.0,
    n_steps: int = 20,
) -> NDArray[np.float64]:
    """Forward-Euler integration of ``dx/dt = v(x, t)`` from ``t=0`` to ``t_final``.

    Batched: ``x0`` has shape ``(n, d)`` and the velocity fn is applied
    row-wise, so ``Phi_T`` is evaluated for a whole batch at once.
    """
    x = np.asarray(x0, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError(f"x0 must be 2-D (n, d); got shape {x.shape}")
    n = int(n_steps)
    if n < 1:
        raise ValueError(f"n_steps must be >= 1, got {n_steps!r}")
    dt = float(t_final) / float(n)
    for k in range(n):
        t = (k / float(n)) * float(t_final)
        v = np.asarray(velocity_fn(x, t), dtype=np.float64)
        if v.shape != x.shape:
            raise ValueError(
                f"velocity_fn returned shape {v.shape}, expected {x.shape}"
            )
        x = x + dt * v
    return np.ascontiguousarray(x, dtype=np.float64)


def estimate_flow_map_lipschitz(
    velocity_fn: VelocityFn,
    x_batch: NDArray[np.float64],
    *,
    t_final: float = 1.0,
    n_steps: int = 20,
    eps: float = 1e-3,
    n_directions: int = 4,
    seed: int = 0,
) -> FlowMapLipschitzReport:
    """Estimate ``K = Lip(Phi_T)`` by finite differences of the flow map.

    For each point ``x`` and each random unit direction ``u``, form
    ``x + eps*u`` and compute ``||Phi_T(x + eps u) - Phi_T(x)|| / eps``.
    The sample-max over all (point, direction) pairs is the empirical
    upper envelope on ``K``; the mean is a central estimate. Both are
    reported because ``K`` enters ``q = mK`` and the sample-max is the
    conservative choice for testing ``q < 1``.

    The estimate is a *numerical surrogate* for the true Lipschitz
    constant: finite differences under random directions sample the
    operator norm from below, so the reported ``k_max`` is a lower bound on
    ``Lip(Phi_T)`` and ``q < 1`` using it is a necessary, not sufficient,
    condition. This is the honest reading and is surfaced in the report.
    """
    x = np.asarray(x_batch, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError(f"x_batch must be 2-D (n, d); got shape {x.shape}")
    if x.shape[0] < 1:
        raise ValueError("x_batch must be non-empty")
    e = float(eps)
    if not np.isfinite(e) or e <= 0.0:
        raise ValueError(f"eps must be finite and > 0, got {eps!r}")
    nd = int(n_directions)
    if nd < 1:
        raise ValueError(f"n_directions must be >= 1, got {n_directions!r}")

    rng = np.random.default_rng(int(seed))
    phi_x = integrate_flow(velocity_fn, x, t_final=t_final, n_steps=n_steps)

    ratios: list[float] = []
    for _ in range(nd):
        u = rng.standard_normal(x.shape).astype(np.float64)
        norms = np.linalg.norm(u, axis=1, keepdims=True)
        u = u / np.maximum(norms, 1e-12)
        phi_shift = integrate_flow(
            velocity_fn, x + e * u, t_final=t_final, n_steps=n_steps
        )
        num = np.linalg.norm(phi_shift - phi_x, axis=1)
        ratios.extend((num / e).tolist())

    arr = np.asarray(ratios, dtype=np.float64)
    return FlowMapLipschitzReport(
        k_mean=float(np.mean(arr)),
        k_max=float(np.max(arr)),
        k_p95=float(np.percentile(arr, 95)),
        n_points=int(x.shape[0]),
        n_directions=nd,
        n_estimates=int(arr.size),
        eps=e,
        t_final=float(t_final),
        n_steps=int(n_steps),
    )


@dataclass(frozen=True)
class FlowMapLipschitzReport:
    """Result of :func:`estimate_flow_map_lipschitz`."""

    k_mean: float
    k_max: float
    k_p95: float
    n_points: int
    n_directions: int
    n_estimates: int
    eps: float
    t_final: float
    n_steps: int

    def as_metrics(self) -> dict[str, float]:
        return {
            "flow_map_k_mean": float(self.k_mean),
            "flow_map_k_max": float(self.k_max),
            "flow_map_k_p95": float(self.k_p95),
        }


def contraction_variable(m: float, k: float) -> float:
    """Return ``q = m K`` — the Theorem-4 contraction variable."""
    mm = float(m)
    kk = float(k)
    if not np.isfinite(mm) or mm < 0.0 or mm > 1.0:
        raise ValueError(f"m (memory fraction) must be in [0, 1], got {m!r}")
    if not np.isfinite(kk) or kk < 0.0:
        raise ValueError(f"K must be finite and >= 0, got {k!r}")
    return mm * kk


def critical_restart_ratio(m: float) -> float:
    """Closed-form boundary of the Theorem-5 Eq. 7 improvement condition.

    For **independent isotropic Gaussian residuals** (``err_X = sigma_X^2``,
    ``err_Y = sigma_Y^2``, ``err_XY = sigma_X^2 + sigma_Y^2`` per dimension) the
    condition ``err_Y - err_X < m * err_XY`` is equivalent to

        ``sigma_Y / sigma_X < sqrt((1 + m) / (1 - m))``,

    so the blend improves the endpoint error exactly when the *restart-quality
    ratio* ``q = sigma_Y / sigma_X`` is below this critical value. The bound
    grows with ``m`` (more memory tolerates a worse fresh restart); ``q* <= 1``
    is impossible for ``m > 0``, i.e. a fresh restart at least as good as the
    preceding state always helps.

    This is the analytic form of the boundary the GAP-24 runner measures.
    """
    mm = float(m)
    if not np.isfinite(mm) or mm < 0.0 or mm >= 1.0:
        raise ValueError(f"m must be finite and in [0, 1), got {m!r}")
    return math.sqrt((1.0 + mm) / (1.0 - mm))


def critical_memory(q: float) -> float:
    """Inverse of :func:`critical_restart_ratio`.

    Returns the memory fraction ``m*(q) = (q^2 - 1) / (q^2 + 1)`` above which a
    restart-blend with restart-quality ratio ``q`` improves the endpoint error.
    ``m* <= 0`` for ``q <= 1`` (always improves).
    """
    qq = float(q)
    if not np.isfinite(qq) or qq < 0.0:
        raise ValueError(f"q must be finite and >= 0, got {q!r}")
    return (qq * qq - 1.0) / (qq * qq + 1.0)


def round_map_contraction(
    velocity_fn: VelocityFn,
    x0: NDArray[np.float64],
    fresh: NDArray[np.float64],
    *,
    m: float,
    t_final: float = 1.0,
    n_steps: int = 20,
    n_iter: int = 30,
    tol: float = 1e-10,
) -> RoundMapContractionReport:
    """Measure the empirical round-map contraction rate and compare to ``q = mK``.

    Iterates the round map ``G_b(x) = Phi_T(m x + (1 - m) b)`` for a *fixed*
    fresh input ``b`` from ``x0``, recording the per-step ratio
    ``||x_{k+1} - x*|| / ||x_k - x*||`` where ``x*`` is the converged
    fixed point. The geometric mean of the trailing ratios is the empirical
    contraction rate; Theorem 4 predicts it is ``<= q = m K``.

    Returns the empirical rate and, via
    :func:`estimate_flow_map_lipschitz`, the ``q`` it should track.
    """
    mm = float(m)
    x = np.asarray(x0, dtype=np.float64)
    b = np.asarray(fresh, dtype=np.float64)
    if x.shape != b.shape:
        raise ValueError(f"x0 {x.shape} and fresh {b.shape} must match")

    def _g(xx: NDArray[np.float64]) -> NDArray[np.float64]:
        blended = mm * xx + (1.0 - mm) * b
        return integrate_flow(velocity_fn, blended, t_final=t_final, n_steps=n_steps)

    traj = [x]
    cur = x
    for _ in range(int(n_iter)):
        nxt = _g(cur)
        traj.append(nxt)
        if float(np.max(np.linalg.norm(nxt - cur, axis=1))) < tol:
            cur = nxt
            break
        cur = nxt
    x_star = traj[-1]

    ratios: list[float] = []
    for k in range(len(traj) - 1):
        num = float(np.max(np.linalg.norm(traj[k + 1] - x_star, axis=1)))
        den = float(np.max(np.linalg.norm(traj[k] - x_star, axis=1)))
        if den > 1e-300:
            ratios.append(num / den)
    # Trailing geometric mean (drop the first few transients).
    tail = ratios[len(ratios) // 2 :] if len(ratios) >= 4 else ratios
    tail_arr = np.asarray(tail, dtype=np.float64)
    tail_arr = tail_arr[tail_arr > 0.0]
    geo = float(np.exp(np.mean(np.log(tail_arr)))) if tail_arr.size else float("nan")

    k_report = estimate_flow_map_lipschitz(
        velocity_fn, x, t_final=t_final, n_steps=n_steps, seed=0
    )
    q = contraction_variable(mm, k_report.k_max)
    return RoundMapContractionReport(
        m=mm,
        q_from_k_max=q,
        empirical_rate_geomean=geo,
        empirical_rate_max=float(np.max(tail_arr)) if tail_arr.size else float("nan"),
        converged=bool(len(traj) < int(n_iter) + 1),
        n_iterations=int(len(traj) - 1),
        k_max=k_report.k_max,
        k_mean=k_report.k_mean,
    )


@dataclass(frozen=True)
class RoundMapContractionReport:
    """Result of :func:`round_map_contraction`."""

    m: float
    q_from_k_max: float
    empirical_rate_geomean: float
    empirical_rate_max: float
    converged: bool
    n_iterations: int
    k_max: float
    k_mean: float

    @property
    def contraction_holds(self) -> bool:
        """``q = m K_max < 1`` — the Theorem-4 sufficient condition."""
        return bool(self.q_from_k_max < 1.0)

    @property
    def contracts_empirically(self) -> bool:
        """The measured round-map rate is ``< 1`` — the map contracts.

        This is the *direction* prediction Theorem 4 makes (a q-contraction
        with q<1 contracts); it is the check the GAP-09 acceptance refers to.
        """
        if not np.isfinite(self.empirical_rate_geomean):
            return False
        return bool(self.empirical_rate_geomean < 1.0)

    @property
    def rate_tracks_q(self) -> bool:
        """The empirical contraction rate is ``<= q`` (up to 20% slack).

        A *tighter* check than :attr:`contracts_empirically`: Theorem 4
        upper-bounds the round-map contraction by ``q``, so a measured rate
        materially above ``q`` would falsify the bound. The slack absorbs the
        short-transient noise that dominates when the round map converges in
        very few iterations (small ``m``).
        """
        if not np.isfinite(self.empirical_rate_geomean):
            return False
        return bool(self.empirical_rate_geomean <= self.q_from_k_max * 1.2)

    def as_metrics(self) -> dict[str, float]:
        return {
            "round_map_q": float(self.q_from_k_max),
            "round_map_empirical_rate": float(self.empirical_rate_geomean),
            "round_map_k_max": float(self.k_max),
            "round_map_converged": 1.0 if self.converged else 0.0,
            "round_map_contraction_holds": 1.0 if self.contraction_holds else 0.0,
            "round_map_contracts_empirically": (
                1.0 if self.contracts_empirically else 0.0
            ),
            "round_map_rate_tracks_q": 1.0 if self.rate_tracks_q else 0.0,
        }


def blend_identity_terms(
    x_prev: Sequence[float] | NDArray[np.float64],
    y_fresh: Sequence[float] | NDArray[np.float64],
    z_target: Sequence[float] | NDArray[np.float64],
    *,
    m: float,
) -> BlendIdentityReport:
    """Evaluate the Theorem-5 blend identity and the Eq. 7 improvement condition.

    ``X`` = preceding endpoint, ``Y`` = fresh state, ``z`` = target,
    ``B_m = m X + (1 - m) Y``. All inputs are batched ``(n, d)`` (or 1-D,
    promoted to a single row). The report carries the three squared-error
    terms, the exact identity residual (should be ~0), and the
    *predicted* vs *measured* sign of the blend's error change relative to
    ``X`` — the criterion's prediction and the measurement it must match.
    """
    X = np.atleast_2d(np.asarray(x_prev, dtype=np.float64))
    Y = np.atleast_2d(np.asarray(y_fresh, dtype=np.float64))
    Z = np.atleast_2d(np.asarray(z_target, dtype=np.float64))
    if not (X.shape == Y.shape == Z.shape):
        raise ValueError(
            f"X {X.shape}, Y {Y.shape}, Z {Z.shape} must have matching shape"
        )
    mm = float(m)
    if not np.isfinite(mm) or mm < 0.0 or mm > 1.0:
        raise ValueError(f"m must be in [0, 1], got {m!r}")

    def _mse(A: NDArray[np.float64]) -> float:
        return float(np.mean(np.sum((A - Z) ** 2, axis=1)))

    B = mm * X + (1.0 - mm) * Y
    err_x = _mse(X)
    err_y = _mse(Y)
    err_b = _mse(B)
    xy = float(np.mean(np.sum((X - Y) ** 2, axis=1)))

    # Theorem 5 identity: E||B-z||^2 = m E||X-z||^2 + (1-m) E||Y-z||^2
    #                     - m(1-m) E||X-Y||^2
    rhs = mm * err_x + (1.0 - mm) * err_y - mm * (1.0 - mm) * xy
    identity_residual = err_b - rhs

    # Eq. 7: blend improves over X iff  err_y - err_x < m * E||X-Y||^2
    condition_holds = bool((err_y - err_x) < mm * xy)
    measured_blend_better = bool(err_b < err_x)
    return BlendIdentityReport(
        m=mm,
        err_x=err_x,
        err_y=err_y,
        err_blend=err_b,
        e_xy_sq=xy,
        identity_residual=float(identity_residual),
        condition_holds=condition_holds,
        measured_blend_better=measured_blend_better,
        prediction_matches=bool(condition_holds == measured_blend_better),
        n_records=int(X.shape[0]),
    )


@dataclass(frozen=True)
class BlendIdentityReport:
    """Result of :func:`blend_identity_terms`."""

    m: float
    err_x: float
    err_y: float
    err_blend: float
    e_xy_sq: float
    identity_residual: float
    condition_holds: bool
    measured_blend_better: bool
    prediction_matches: bool
    n_records: int

    def as_metrics(self) -> dict[str, float]:
        return {
            "blend_err_x": float(self.err_x),
            "blend_err_y": float(self.err_y),
            "blend_err_blend": float(self.err_blend),
            "blend_e_xy_sq": float(self.e_xy_sq),
            "blend_identity_residual": float(self.identity_residual),
            "blend_condition_holds": 1.0 if self.condition_holds else 0.0,
            "blend_measured_better": 1.0 if self.measured_blend_better else 0.0,
            "blend_prediction_matches": 1.0 if self.prediction_matches else 0.0,
        }
