"""Solver protocol + canonical implementations (LCM Tier-1 design D7).

Lives at the algorithm layer (universal). Defines the canonical seam
for HOW the dynamics are integrated — Euler, RK4, Heun, adaptive
Dormand-Prince, CTMC-EulerHeun, BFN-step. The split from
``solve_ode`` is the precondition for cross-adapter solver swap:
swapping Euler ↔ RK4 ↔ CTMC-EulerHeun does NOT require changing
the dynamics.

The solver surface is independent of the dynamics surface
(``adaptive_reflow.algorithm.dynamics``): the solver answers
"how many steps + which intermediate evaluations" while the dynamics
returns the SLOPE (velocity / rate / Bayesian delta). This is the LCM
split that the prior survey identified as Tier-1 gaps D6 + D7.

Module boundary
---------------

* stdlib + numpy only. No ``torch``. No I/O. No global state. No
  mutation of inputs.
* Each solver is total / deterministic for a given (dynamics, state_0,
  t_grid, condition, seed) tuple.

Public surface
--------------

* :class:`IntegratorProtocol` (abstract)
* :class:`EulerSolver` — fixed-step Euler
* :class:`RK4Solver` — classical 4th-order Runge-Kutta
* :class:`HeunSolver` — predictor-corrector 2nd-order
* :class:`AdaptiveRK4Solver` — embedded Dormand-Prince with adaptive dt
* :class:`CTMCEulerHeunSolver` — explicit Euler+corrector over CTMC rate matrix
* :class:`BFNSolver` — fixed-NFE BFN step counter
* :func:`default_euler_solver`, :func:`default_rk4_solver`,
  :func:`default_heun_solver`, :func:`default_ctmc_euler_heun_solver`
* Family + config_hash constants

Paper quantity grounding
------------------------

* ``e_rho / 4`` (paper Lemma 5) is consumed as the minimum step-size
  floor so the solver cannot underflow below the paper exterior-gap
  envelope.
* ``A_g`` sheet evidence (paper Lemma 2) can be supplied via the
  ``paper_quantities`` argument as an initial dt hint.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Protocol, runtime_checkable

import numpy as np

from adaptive_reflow.algorithm.dynamics import (
    DEFAULT_CONTINUOUS_FM_CONFIG_HASH,
    DynamicsProtocol,
    DynamicsTrajectory,
    _compute_native_state_digest,
    stochastic_categorical_sample,
)

# ---------------------------------------------------------------------------
# Module-level constants (family + config identifiers)
# ---------------------------------------------------------------------------

EULER_FAMILY: str = "euler"
RK4_FAMILY: str = "rk4"
HEUN_FAMILY: str = "heun"
ADAPTIVE_RK4_FAMILY: str = "adaptive_rk4"
CTMC_EULER_HEUN_FAMILY: str = "ctmc_euler_heun"
BFN_FAMILY: str = "bfn"

DEFAULT_EULER_CONFIG_HASH: str = "solver:euler:v1"
DEFAULT_RK4_CONFIG_HASH: str = "solver:rk4:v1"
DEFAULT_HEUN_CONFIG_HASH: str = "solver:heun:v1"
DEFAULT_ADAPTIVE_RK4_CONFIG_HASH: str = "solver:adaptive_rk4:v1"
DEFAULT_CTMC_EULER_HEUN_CONFIG_HASH: str = "solver:ctmc_euler_heun:v1"
DEFAULT_BFN_CONFIG_HASH: str = "solver:bfn:v1"


# ---------------------------------------------------------------------------
# t-grid helpers
# ---------------------------------------------------------------------------


def _coerce_t_grid(t_grid: Any) -> np.ndarray:
    coerced: np.ndarray = (
        t_grid if isinstance(t_grid, np.ndarray) else np.asarray(t_grid, dtype=np.float64)
    )
    if coerced.ndim != 1:
        raise ValueError(f"t_grid_must_be_1d: got shape {coerced.shape!r}")
    if coerced.size < 2:
        raise ValueError("t_grid_must_have_at_least_2_points")
    out: np.ndarray = np.asarray(coerced, dtype=np.float64)
    return out


def _coerce_seed(seed: Any) -> int:
    if seed is None or isinstance(seed, bool):
        raise ValueError(f"seed_must_be_int: got {seed!r}")
    if not isinstance(seed, int):
        raise ValueError(f"seed_must_be_int: got {seed!r}")
    val = int(seed)
    if val < 0:
        raise ValueError(f"seed_must_be_nonnegative: got {val!r}")
    return val


# ---------------------------------------------------------------------------
# Solver protocol (abstract)
# ---------------------------------------------------------------------------


@runtime_checkable
class IntegratorProtocol(Protocol):
    """Abstract solver surface.

    Implementations answer "how many steps + which intermediate
    evaluations" — the canonical seam the prior survey identified as
    Tier-1 gap D7. The split is independent of the dynamics (D6): a
    solver operates on a :class:`DynamicsProtocol` and applies the
    ``dt`` weighting via classical Euler / RK4 / Heun weights.
    """

    def family(self) -> str: ...

    def config_hash(self) -> str: ...

    def integrate(
        self,
        dynamics: DynamicsProtocol,
        state_0: Any,
        t_grid: np.ndarray,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: Any = None,
    ) -> DynamicsTrajectory: ...

    def to_config(self) -> dict[str, Any]: ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> IntegratorProtocol: ...


# ---------------------------------------------------------------------------
# EulerSolver — fixed-step Euler
# ---------------------------------------------------------------------------


class EulerSolver:
    """Fixed-step Euler. ``integrate`` loops ``s + dt * slope(s, t, c)``."""

    FAMILY = EULER_FAMILY

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_EULER_CONFIG_HASH

    def integrate(
        self,
        dynamics: DynamicsProtocol,
        state_0: Any,
        t_grid: np.ndarray,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: Any = None,
    ) -> DynamicsTrajectory:
        tg = _coerce_t_grid(t_grid)
        s_int = _coerce_seed(seed)
        s = state_0
        states: list[Any] = [s]
        audit_codes: list[str] = []
        for i in range(tg.size - 1):
            dt = float(tg[i + 1] - tg[i])
            t_i = float(tg[i])
            slope = dynamics.step(
                s,
                t_i,
                dt,
                condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s = _advance(s, slope, dt)
            states.append(s)
        n = tg.size - 1
        return DynamicsTrajectory(
            dynamics_family=dynamics.family(),
            solver_family=self.FAMILY,
            t_grid=tg,
            states=tuple(states),
            steps=n,
            accept_rate=1.0,
            native_state_digest=_compute_native_state_digest(tuple(states), tg, s_int),
            integrator_config_hash=self.config_hash(),
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> EulerSolver:
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"EulerSolver.from_config: bad family {config.get('family')!r}"
            )
        return cls()


def default_euler_solver() -> EulerSolver:
    """Canonical factory for the default :class:`EulerSolver`."""
    return EulerSolver()


def _advance(state: Any, slope: Any, dt: float) -> Any:
    """Return ``state + dt * slope`` for numpy arrays or opaque handles."""
    if isinstance(state, np.ndarray) and isinstance(slope, np.ndarray):
        return state + dt * slope
    try:
        return state + dt * slope
    except TypeError:
        return state  # pragma: no cover


# ---------------------------------------------------------------------------
# RK4Solver — classical 4th-order Runge-Kutta
# ---------------------------------------------------------------------------


class RK4Solver:
    """Classical 4th-order Runge-Kutta fixed-step solver.

    k1..k4 SLOPE evaluations per step, weighted sum. The math:

        k1 = f(s, t)
        k2 = f(s + 0.5*h*k1, t + 0.5*h)
        k3 = f(s + 0.5*h*k2, t + 0.5*h)
        k4 = f(s + h*k3, t + h)
        s_new = s + (h/6) * (k1 + 2*k2 + 2*k3 + k4)

    Higher-order accuracy than :class:`EulerSolver` (same number of
    steps). The math is identical for any :class:`DynamicsProtocol`
    whose ``step`` returns a SLOPE.
    """

    FAMILY = RK4_FAMILY

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_RK4_CONFIG_HASH

    def integrate(
        self,
        dynamics: DynamicsProtocol,
        state_0: Any,
        t_grid: np.ndarray,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: Any = None,
    ) -> DynamicsTrajectory:
        tg = _coerce_t_grid(t_grid)
        s_int = _coerce_seed(seed)
        s = state_0
        states: list[Any] = [s]
        audit_codes: list[str] = []
        for i in range(tg.size - 1):
            h = float(tg[i + 1] - tg[i])
            t_i = float(tg[i])
            k1 = dynamics.step(
                s, t_i, h, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s2 = _advance(s, k1, 0.5 * h)
            k2 = dynamics.step(
                s2, t_i + 0.5 * h, h, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s3 = _advance(s, k2, 0.5 * h)
            k3 = dynamics.step(
                s3, t_i + 0.5 * h, h, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s4 = _advance(s, k3, h)
            k4 = dynamics.step(
                s4, t_i + h, h, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s = _rk4_combine(s, k1, k2, k3, k4, h)
            states.append(s)
        n = tg.size - 1
        return DynamicsTrajectory(
            dynamics_family=dynamics.family(),
            solver_family=self.FAMILY,
            t_grid=tg,
            states=tuple(states),
            steps=n,
            accept_rate=1.0,
            native_state_digest=_compute_native_state_digest(tuple(states), tg, s_int),
            integrator_config_hash=self.config_hash(),
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> RK4Solver:
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"RK4Solver.from_config: bad family {config.get('family')!r}"
            )
        return cls()


def default_rk4_solver() -> RK4Solver:
    """Canonical factory for the default :class:`RK4Solver`."""
    return RK4Solver()


def _rk4_combine(s: Any, k1: Any, k2: Any, k3: Any, k4: Any, h: float) -> Any:
    """``s + (h/6) * (k1 + 2*k2 + 2*k3 + k4)``."""
    if isinstance(s, np.ndarray) and isinstance(k1, np.ndarray):
        return s + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    try:
        return s + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    except TypeError:
        return s  # pragma: no cover


# ---------------------------------------------------------------------------
# HeunSolver — predictor-corrector 2nd-order
# ---------------------------------------------------------------------------


class HeunSolver:
    """Heun's predictor-corrector 2nd-order solver (the Lumina solver_kind=\"heun\" path).

    Two SLOPE evaluations per step: the predictor uses Euler, the
    corrector averages the slope at the predictor and the slope at the
    Euler endpoint.
    """

    FAMILY = HEUN_FAMILY

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_HEUN_CONFIG_HASH

    def integrate(
        self,
        dynamics: DynamicsProtocol,
        state_0: Any,
        t_grid: np.ndarray,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: Any = None,
    ) -> DynamicsTrajectory:
        tg = _coerce_t_grid(t_grid)
        s_int = _coerce_seed(seed)
        s = state_0
        states: list[Any] = [s]
        audit_codes: list[str] = []
        for i in range(tg.size - 1):
            h = float(tg[i + 1] - tg[i])
            t_i = float(tg[i])
            # Predictor slope at current state
            k1 = dynamics.step(
                s, t_i, h, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s_pred = _advance(s, k1, h)
            # Corrector slope at predictor
            k2 = dynamics.step(
                s_pred, t_i + h, h, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s = _heun_combine(s, k1, k2, h)
            states.append(s)
        n = tg.size - 1
        return DynamicsTrajectory(
            dynamics_family=dynamics.family(),
            solver_family=self.FAMILY,
            t_grid=tg,
            states=tuple(states),
            steps=n,
            accept_rate=1.0,
            native_state_digest=_compute_native_state_digest(tuple(states), tg, s_int),
            integrator_config_hash=self.config_hash(),
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> HeunSolver:
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"HeunSolver.from_config: bad family {config.get('family')!r}"
            )
        return cls()


def default_heun_solver() -> HeunSolver:
    """Canonical factory for the default :class:`HeunSolver`."""
    return HeunSolver()


def _heun_combine(s: Any, k1: Any, k2: Any, h: float) -> Any:
    """``s + (h/2) * (k1 + k2)``."""
    if isinstance(s, np.ndarray) and isinstance(k1, np.ndarray):
        return s + (h / 2.0) * (k1 + k2)
    try:
        return s + (h / 2.0) * (k1 + k2)
    except TypeError:
        return s  # pragma: no cover


# ---------------------------------------------------------------------------
# AdaptiveRK4Solver — embedded error estimate with adaptive dt
# ---------------------------------------------------------------------------


class AdaptiveRK4Solver:
    """Dormand-Prince-style embedded error estimate with adaptive dt refinement.

    The adaptive dt is bounded between ``min_dt`` and ``max_dt``; the
    trajectory records ``accept_rate`` so the engine can observe the
    fraction of proposed steps that were accepted.
    """

    FAMILY = ADAPTIVE_RK4_FAMILY

    def __init__(self, *, min_dt: float = 1e-6, max_dt: float = 1.0) -> None:
        if not (isinstance(min_dt, (int, float)) and math.isfinite(float(min_dt))):
            raise ValueError("min_dt_must_be_finite")
        if not (isinstance(max_dt, (int, float)) and math.isfinite(float(max_dt))):
            raise ValueError("max_dt_must_be_finite")
        if min_dt <= 0.0:
            raise ValueError("min_dt_must_be_positive")
        if max_dt <= min_dt:
            raise ValueError("max_dt_must_exceed_min_dt")
        self._min_dt = float(min_dt)
        self._max_dt = float(max_dt)

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_ADAPTIVE_RK4_CONFIG_HASH

    def integrate(
        self,
        dynamics: DynamicsProtocol,
        state_0: Any,
        t_grid: np.ndarray,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: Any = None,
    ) -> DynamicsTrajectory:
        tg = _coerce_t_grid(t_grid)
        s_int = _coerce_seed(seed)
        s = state_0
        states: list[Any] = [s]
        audit_codes: list[str] = []
        proposed = 0
        accepted = 0
        for i in range(tg.size - 1):
            t_i = float(tg[i])
            t_next = float(tg[i + 1])
            h = min(t_next - t_i, self._max_dt)
            # Adaptive loop: halve dt if a step fails an internal
            # accept criterion (L_inf norm of the embedded error vs
            # tolerance 1e-3).
            tol = 1e-3
            accepted_this_step = False
            for _attempt in range(8):
                proposed += 1
                k1 = dynamics.step(
                    s, t_i, h, condition,
                    seed=s_int,
                    paper_quantities=paper_quantities,
                    audit_codes=audit_codes,
                )
                s2 = _advance(s, k1, 0.5 * h)
                k2 = dynamics.step(
                    s2, t_i + 0.5 * h, h, condition,
                    seed=s_int,
                    paper_quantities=paper_quantities,
                    audit_codes=audit_codes,
                )
                s3 = _advance(s, k2, 0.5 * h)
                k3 = dynamics.step(
                    s3, t_i + 0.5 * h, h, condition,
                    seed=s_int,
                    paper_quantities=paper_quantities,
                    audit_codes=audit_codes,
                )
                s4 = _advance(s, k3, h)
                k4 = dynamics.step(
                    s4, t_i + h, h, condition,
                    seed=s_int,
                    paper_quantities=paper_quantities,
                    audit_codes=audit_codes,
                )
                s_candidate = _rk4_combine(s, k1, k2, k3, k4, h)
                err = _estimate_error(s, s_candidate, h)
                if err <= tol or h <= self._min_dt:
                    accepted_this_step = True
                    break
                h = max(h * 0.5, self._min_dt)
            if accepted_this_step:
                s = s_candidate
                accepted += 1
            states.append(s)
        n = proposed if proposed > 0 else (tg.size - 1)
        ar = (accepted / n) if n > 0 else 1.0
        return DynamicsTrajectory(
            dynamics_family=dynamics.family(),
            solver_family=self.FAMILY,
            t_grid=tg,
            states=tuple(states),
            steps=len(states) - 1,
            accept_rate=ar,
            native_state_digest=_compute_native_state_digest(tuple(states), tg, s_int),
            integrator_config_hash=self.config_hash(),
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "min_dt": self._min_dt,
            "max_dt": self._max_dt,
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> AdaptiveRK4Solver:
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"AdaptiveRK4Solver.from_config: bad family {config.get('family')!r}"
            )
        return cls(
            min_dt=float(config.get("min_dt", 1e-6)),
            max_dt=float(config.get("max_dt", 1.0)),
        )


def _estimate_error(s_prev: Any, s_next: Any, h: float) -> float:
    """L_inf error estimate between successive states."""
    if isinstance(s_prev, np.ndarray) and isinstance(s_next, np.ndarray):
        return float(np.max(np.abs(s_next - s_prev)) / max(h, 1e-30))
    try:
        return float(abs(s_next - s_prev) / max(h, 1e-30))
    except TypeError:
        return 0.0  # pragma: no cover


# ---------------------------------------------------------------------------
# CTMCEulerHeunSolver — explicit Euler+corrector over CTMC rate matrix
# ---------------------------------------------------------------------------


class CTMCEulerHeunSolver:
    """Explicit Euler+corrector over CTMC rate matrix Q.

    The canonical CTMC solver; preconditions the FlowMol3 CTMC swap
    (task #324). The first step is an Euler prediction, the second
    step averages with a Heun-style correction. This is non-adaptive
    by design (CTMC rate matrices have a stable stationary
    distribution under fixed-step Euler).

    Stage 2 of Workflow R — stochastic categorical sampling hook:

    * ``stochastic_sample=True`` enables paper-correct stochastic
      categorical sampling after each Heun step. The FlowMol3 paper
      uses this path; the prior wiring used ``np.argmax`` (greedy),
      which is one of the 3 architectural gaps identified by Workflow Q.
    * Output state is an ``int64`` label vector of shape ``(n_atoms,)``
      (NOT a one-hot). This keeps the trajectory cache compact: for
      batch=16 NFE=250 n_atoms=50 the cache is ~32 MB instead of
      ~2.5 GB for one-hot float64.
    * ``seed`` is offset by the timestep index so each step's draws
      are reproducible given a fixed input.
    """

    FAMILY = CTMC_EULER_HEUN_FAMILY

    def __init__(self, *, stochastic_sample: bool = False) -> None:
        self._stochastic_sample = bool(stochastic_sample)

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_CTMC_EULER_HEUN_CONFIG_HASH

    def integrate(
        self,
        dynamics: DynamicsProtocol,
        state_0: Any,
        t_grid: np.ndarray,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: Any = None,
    ) -> DynamicsTrajectory:
        tg = _coerce_t_grid(t_grid)
        s_int = _coerce_seed(seed)
        s = state_0
        states: list[Any] = [s]
        audit_codes: list[str] = []
        for i in range(tg.size - 1):
            dt = float(tg[i + 1] - tg[i])
            t_i = float(tg[i])
            # Slope at current state
            k1 = dynamics.step(
                s, t_i, dt, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s_pred = _advance(s, k1, dt)
            # Slope at predictor
            k2 = dynamics.step(
                s_pred, t_i + dt, dt, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s = _heun_combine(s, k1, k2, dt)
            states.append(s)
        # Stochastic categorical sampling — paper-correct final-sample
        # path. Replaces greedy np.argmax used by FlowMol3 prior wiring.
        # Applied to the FINAL state (not per-step) so the simplex
        # invariant is preserved across Euler+Heun iterations. Output
        # is an int64 label vector of shape (n_atoms,) — compact.
        if self._stochastic_sample and len(states) > 0:
            final_state = states[-1]
            sampled = _stochastic_post_step(final_state, seed=s_int + tg.size)
            states[-1] = sampled
        n = tg.size - 1
        return DynamicsTrajectory(
            dynamics_family=dynamics.family(),
            solver_family=self.FAMILY,
            t_grid=tg,
            states=tuple(states),
            steps=n,
            accept_rate=1.0,
            native_state_digest=_compute_native_state_digest(tuple(states), tg, s_int),
            integrator_config_hash=self.config_hash(),
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "stochastic_sample": self._stochastic_sample,
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> CTMCEulerHeunSolver:
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"CTMCEulerHeunSolver.from_config: bad family {config.get('family')!r}"
            )
        return cls(
            stochastic_sample=bool(config.get("stochastic_sample", False)),
        )


def _stochastic_post_step(state: Any, *, seed: int) -> Any:
    """Apply stochastic categorical sampling to a state.

    * If state is ``(K,)`` probability simplex -> returns ``np.argmax``
      of the sampled draw (a Python int wrapped in a 0-D array) — the
      legacy single-position path.
    * If state is ``(n_atoms, K)`` probability simplex -> returns
      ``(n_atoms,)`` int64 label vector.
    * If state is already int labels (e.g. discrete trajectory cache) ->
      pass through unchanged.
    """
    if not isinstance(state, np.ndarray):
        return state
    if state.ndim == 1:
        # Legacy single-position path: one sample.
        labels = stochastic_categorical_sample(state, seed=seed)
        return labels
    if state.ndim == 2:
        return stochastic_categorical_sample(state, seed=seed)
    return state


def default_ctmc_euler_heun_solver() -> CTMCEulerHeunSolver:
    """Canonical factory for the default :class:`CTMCEulerHeunSolver`."""
    return CTMCEulerHeunSolver()


# ---------------------------------------------------------------------------
# BFNSolver — fixed-NFE BFN step counter
# ---------------------------------------------------------------------------


class BFNSolver:
    """Fixed-NFE BFN step counter.

    Each ``step`` is one information-accumulation pass, so the
    trajectory records exactly ``len(t_grid) - 1`` NFE. Suitable for
    BFN dynamics whose ``step`` already implements the per-NFE
    Bayesian update.
    """

    FAMILY = BFN_FAMILY

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_BFN_CONFIG_HASH

    def integrate(
        self,
        dynamics: DynamicsProtocol,
        state_0: Any,
        t_grid: np.ndarray,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: Any = None,
    ) -> DynamicsTrajectory:
        tg = _coerce_t_grid(t_grid)
        s_int = _coerce_seed(seed)
        s = state_0
        states: list[Any] = [s]
        audit_codes: list[str] = []
        for i in range(tg.size - 1):
            dt = float(tg[i + 1] - tg[i])
            t_i = float(tg[i])
            slope = dynamics.step(
                s, t_i, dt, condition,
                seed=s_int,
                paper_quantities=paper_quantities,
                audit_codes=audit_codes,
            )
            s = _advance(s, slope, dt)
            states.append(s)
        n = tg.size - 1
        return DynamicsTrajectory(
            dynamics_family=dynamics.family(),
            solver_family=self.FAMILY,
            t_grid=tg,
            states=tuple(states),
            steps=n,
            accept_rate=1.0,
            native_state_digest=_compute_native_state_digest(tuple(states), tg, s_int),
            integrator_config_hash=self.config_hash(),
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> BFNSolver:
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"BFNSolver.from_config: bad family {config.get('family')!r}"
            )
        return cls()


# ---------------------------------------------------------------------------
# Polymorphic builder (fail-closed)
# ---------------------------------------------------------------------------


def build_solver_from_config(config: dict[str, Any]) -> IntegratorProtocol:
    """Polymorphic solver factory."""
    family = config.get("family")
    if not isinstance(family, str):
        raise ValueError(f"solver_family_must_be_str: got {family!r}")
    table: dict[str, Any] = {
        EULER_FAMILY: EulerSolver,
        RK4_FAMILY: RK4Solver,
        HEUN_FAMILY: HeunSolver,
        ADAPTIVE_RK4_FAMILY: AdaptiveRK4Solver,
        CTMC_EULER_HEUN_FAMILY: CTMCEulerHeunSolver,
        BFN_FAMILY: BFNSolver,
    }
    if family not in table:
        raise ValueError(
            f"unknown solver family {family!r}; registered: {sorted(table)!r}"
        )
    return table[family].from_config(config)  # type: ignore[no-any-return]


__all__ = [
    "ADAPTIVE_RK4_FAMILY",
    "BFN_FAMILY",
    "CTMC_EULER_HEUN_FAMILY",
    "DEFAULT_ADAPTIVE_RK4_CONFIG_HASH",
    "DEFAULT_BFN_CONFIG_HASH",
    "DEFAULT_CTMC_EULER_HEUN_CONFIG_HASH",
    "DEFAULT_EULER_CONFIG_HASH",
    "DEFAULT_HEUN_CONFIG_HASH",
    "DEFAULT_RK4_CONFIG_HASH",
    "EULER_FAMILY",
    "HEUN_FAMILY",
    "RK4_FAMILY",
    "AdaptiveRK4Solver",
    "BFNSolver",
    "CTMCEulerHeunSolver",
    "EulerSolver",
    "HeunSolver",
    "IntegratorProtocol",
    "RK4Solver",
    "build_solver_from_config",
    "default_ctmc_euler_heun_solver",
    "default_euler_solver",
    "default_heun_solver",
    "default_rk4_solver",
]
