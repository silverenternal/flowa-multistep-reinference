"""Dynamics protocol + canonical implementations (LCM Tier-1 design D6).

Lives at the algorithm layer (universal). Defines the canonical seam
for how state evolves per unit time — velocity-field (continuous FM),
CTMC rate matrix, or Bayesian-update (BFN). The split from
``solve_ode`` is the precondition for cross-adapter reproducibility:
swapping :class:`ContinuousFMDynamics` ↔ :class:`CTMCDynamics` ↔
:class:`BFNDynamics` does NOT require rewriting the integration scheme.

The protocol surface is independent of the solver surface
(``adaptive_reflow.algorithm.solver``): a :class:`DynamicsProtocol`
answers "what changes per unit time" while the solver answers
"how many steps + which intermediate evaluations" and applies the
``dt`` weighting. This is the LCM split that the prior survey
identified as Tier-1 gaps D6 + D7.

Module boundary
---------------

* stdlib + numpy only. No ``torch``. No I/O. No global state. No
  mutation of inputs.
* ``step()`` returns the SLOPE (velocity / rate / Bayesian delta), NOT
  the next state. The solver applies ``s + dt * slope`` for Euler,
  classical RK4 weights, Heun predictor-corrector, etc.

Public surface
--------------

* :class:`DynamicsProtocol` (abstract)
* :class:`ContinuousFMDynamics` — velocity-field dynamics
* :class:`CTMCDynamics` — continuous-time Markov chain dynamics
* :class:`BFNDynamics` — Bayesian-update dynamics
* :class:`FlowMol3Dynamics` — FlowMol3-specific 4-channel binding
* :class:`ProtBFNDynamics` — ProtBFN-specific categorical binding
* :func:`default_continuous_fm_dynamics`,
  :func:`default_ctmc_dynamics`,
  :func:`default_bfn_dynamics` — canonical factories
* :class:`DynamicsTrajectory` (carrier)
* Family + config_hash constants

Paper quantity grounding
------------------------

* ``e_rho / 4`` (paper Lemma 5) is consumed as the minimum
  step-size floor so the solver cannot underflow below the paper
  exterior-gap envelope.
* BFN information schedule ``alpha_t`` (paper Theorem 1) is passed via
  the ``condition`` carrier so the posterior update uses the per-round
  schedule.
* CTMC rate matrix ``Q`` (paper TransitionKernels §3) is the canonical
  per-step Euler-Heun update target.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt

from adaptive_reflow.contracts.dynamic_noise_bias import (
    PaperQuantitiesSnapshot,
)

# ---------------------------------------------------------------------------
# Module-level constants (family + config identifiers)
# ---------------------------------------------------------------------------

CONTINUOUS_FM_FAMILY: str = "continuous_fm"
"""Dynamics family identifier for :class:`ContinuousFMDynamics`."""

CTMC_FAMILY: str = "ctmc"
"""Dynamics family identifier for :class:`CTMCDynamics`."""

BFN_FAMILY: str = "bfn"
"""Dynamics family identifier for :class:`BFNDynamics`."""

DEFAULT_CONTINUOUS_FM_CONFIG_HASH: str = "dynamics:continuous_fm:v1"
"""Stable config hash for the default :class:`ContinuousFMDynamics`."""

DEFAULT_CTMC_CONFIG_HASH: str = "dynamics:ctmc:v1"
"""Stable config hash for the default :class:`CTMCDynamics`."""

DEFAULT_BFN_CONFIG_HASH: str = "dynamics:bfn:v1"
"""Stable config hash for the default :class:`BFNDynamics`."""

EXTERIOR_GAP_FLOOR_FRACTION: float = 0.25
"""``e_rho / 4`` fraction for the step-size floor (paper Lemma 5)."""


# ---------------------------------------------------------------------------
# Coercion helpers (fail-closed)
# ---------------------------------------------------------------------------


def _coerce_dt(dt: Any) -> float:
    """Coerce ``dt`` to a finite float; raise on non-finite."""
    if dt is None or isinstance(dt, bool):
        raise ValueError(f"dt_must_be_real_number: got {dt!r}")
    if not isinstance(dt, (int, float)):
        raise ValueError(f"dt_must_be_real_number: got {dt!r}")
    val = float(dt)
    if not math.isfinite(val):
        raise ValueError(f"dt_must_be_finite: got {val!r}")
    if val <= 0.0:
        raise ValueError(f"dt_must_be_positive: got {val!r}")
    return val


def _coerce_seed(seed: Any) -> int:
    """Coerce ``seed`` to a non-negative int; raise on bad input."""
    if seed is None or isinstance(seed, bool):
        raise ValueError(f"seed_must_be_int: got {seed!r}")
    if not isinstance(seed, int):
        raise ValueError(f"seed_must_be_int: got {seed!r}")
    val = int(seed)
    if val < 0:
        raise ValueError(f"seed_must_be_nonnegative: got {val!r}")
    return val


def _validate_state_handle(state: Any, *, kind: str) -> Any:
    """Lightly validate that ``state`` is an opaque numeric handle."""
    if state is None:
        raise ValueError(f"{kind}_state_must_not_be_none")
    return state


def _floor_dt(
    dt: float,
    paper_quantities: PaperQuantitiesSnapshot | None,
) -> tuple[float, bool]:
    """Apply the ``e_rho / 4`` floor to ``dt``; return (dt, did_floor)."""
    if paper_quantities is None:
        return dt, False
    e_rho = float(paper_quantities.exterior_gap_e_rho)
    if not math.isfinite(e_rho) or e_rho <= 0.0:
        return dt, False
    floor = e_rho * EXTERIOR_GAP_FLOOR_FRACTION
    if dt < floor:
        return floor, True
    return dt, False


# ---------------------------------------------------------------------------
# Dynamics trajectory carrier
# ---------------------------------------------------------------------------


class DynamicsTrajectory:
    """Pure-data carrier for a dynamics integrate() result.

    Mirrors the structural invariants of
    :class:`adaptive_reflow.universal.state.ODEIntegratorTrace` so the
    engine can treat the new seam as a drop-in replacement.
    """

    def __init__(
        self,
        *,
        dynamics_family: str,
        solver_family: str,
        t_grid: np.ndarray,
        states: tuple[Any, ...],
        steps: int,
        accept_rate: float,
        native_state_digest: str,
        integrator_config_hash: str,
    ) -> None:
        if not isinstance(dynamics_family, str) or not dynamics_family:
            raise ValueError("dynamics_family_must_be_nonempty_str")
        if not isinstance(solver_family, str) or not solver_family:
            raise ValueError("solver_family_must_be_nonempty_str")
        if not isinstance(t_grid, np.ndarray):
            raise ValueError("t_grid_must_be_ndarray")
        if not isinstance(states, tuple):
            raise ValueError("states_must_be_tuple")
        if not isinstance(steps, int) or steps < 0:
            raise ValueError(f"steps_must_be_nonnegative_int: got {steps!r}")
        if not isinstance(accept_rate, (int, float)):
            raise ValueError("accept_rate_must_be_number")
        if not (0.0 <= float(accept_rate) <= 1.0):
            raise ValueError(
                f"accept_rate_must_be_in_[0,1]: got {accept_rate!r}"
            )
        if not isinstance(native_state_digest, str) or not native_state_digest:
            raise ValueError("native_state_digest_must_be_nonempty_str")
        if not isinstance(integrator_config_hash, str) or not integrator_config_hash:
            raise ValueError("integrator_config_hash_must_be_nonempty_str")
        self.dynamics_family = str(dynamics_family)
        self.solver_family = str(solver_family)
        self.t_grid = np.asarray(t_grid, dtype=np.float64)
        self.states = tuple(states)
        self.steps = int(steps)
        self.accept_rate = float(accept_rate)
        self.native_state_digest = str(native_state_digest)
        self.integrator_config_hash = str(integrator_config_hash)


def _compute_native_state_digest(
    states: tuple[Any, ...],
    t_grid: np.ndarray,
    seed: int,
) -> str:
    """Compute a stable hex digest over (states, t_grid, seed)."""
    h = hashlib.sha256()
    h.update(f"n={len(states)};seed={seed};".encode())
    h.update(np.ascontiguousarray(t_grid).tobytes())
    for i, s in enumerate(states):
        h.update(f"[{i}]".encode())
        if isinstance(s, np.ndarray):
            h.update(np.ascontiguousarray(s).tobytes())
        else:
            h.update(repr(s).encode())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Dynamics protocol (abstract)
# ---------------------------------------------------------------------------


@runtime_checkable
class DynamicsProtocol(Protocol):
    """Abstract dynamics surface.

    Implementations answer "what changes per unit time" — the canonical
    seam the prior survey identified as Tier-1 gap D6. The split is
    independent of the solver (D7): a dynamics returns the SLOPE; the
    solver applies ``dt * slope`` for Euler, classical RK4 weights for
    higher-order, etc.
    """

    def family(self) -> str: ...

    def config_hash(self) -> str: ...

    def step(
        self,
        state_t: Any,
        t: float,
        dt: float,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: PaperQuantitiesSnapshot | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Return the SLOPE (velocity / rate / Bayesian delta) at ``(state_t, t, condition)``.

        ``dt`` is passed for paper-quantity gating (e.g. ``e_rho / 4``
        step-size floor) but the returned slope itself does NOT depend
        on ``dt`` — the solver applies the ``dt`` weighting.
        """
        ...

    def to_config(self) -> dict[str, Any]: ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "DynamicsProtocol": ...


# ---------------------------------------------------------------------------
# ContinuousFMDynamics — velocity-field ODE
# ---------------------------------------------------------------------------


class ContinuousFMDynamics:
    """Velocity-field dynamics (continuous FM).

    ``step(s, t, dt, c) = velocity(s, t, c)``. The solver applies
    ``s + dt * slope`` for Euler; classical RK4 weights for higher-order.
    The velocity callable is supplied at construction time; it MUST
    accept ``(s, t, c)`` and return a same-shape handle.
    """

    FAMILY = CONTINUOUS_FM_FAMILY

    def __init__(self, *, velocity_field: Any = None) -> None:
        if velocity_field is None:
            self._velocity = _zero_velocity
        else:
            self._velocity = velocity_field

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_CONTINUOUS_FM_CONFIG_HASH

    def step(
        self,
        state_t: Any,
        t: float,
        dt: float,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: PaperQuantitiesSnapshot | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Return ``velocity(s, t, c)`` (the SLOPE)."""
        dt_f = _coerce_dt(dt)
        _coerce_seed(seed)
        _validate_state_handle(state_t, kind="continuous_fm")
        effective_dt, did_floor = _floor_dt(dt_f, paper_quantities)
        if did_floor and audit_codes is not None:
            audit_codes.append("dynamics_dt_floored_by_paper_exterior_gap")
        return self._velocity(state_t, float(t), condition)

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "ContinuousFMDynamics":
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"ContinuousFMDynamics.from_config: bad family {config.get('family')!r}"
            )
        return cls()


def _zero_velocity(state: Any, t: float, condition: Any) -> Any:
    """Default velocity field (zero). Useful for unit tests."""
    if isinstance(state, np.ndarray):
        return np.zeros_like(state)
    return 0.0


def default_continuous_fm_dynamics() -> ContinuousFMDynamics:
    """Canonical factory for the default :class:`ContinuousFMDynamics`."""
    return ContinuousFMDynamics()


# ---------------------------------------------------------------------------
# CTMCDynamics — continuous-time Markov chain rate matrix
# ---------------------------------------------------------------------------


class CTMCDynamics:
    """Continuous-time Markov chain rate-matrix dynamics.

    ``step(s, t, dt, c) = Q @ s`` — the rate of change of the
    probability simplex state. The solver applies ``s + dt * slope``
    (Euler-on-rate-matrix) or ``softmax(log s + dt * Q)`` (the
    "Euler-on-logits" path). The latter is the path FlowMol3 currently
    uses; both are supported.

    The rate matrix ``Q`` is supplied at construction time; rows MUST
    sum to ``0.0`` so the CTMC stays a probability distribution.
    """

    FAMILY = CTMC_FAMILY

    def __init__(self, *, rate_matrix: np.ndarray | None = None) -> None:
        if rate_matrix is None:
            raise ValueError("CTMCDynamics: rate_matrix required")
        Q = np.asarray(rate_matrix, dtype=np.float64)
        if Q.ndim != 2 or Q.shape[0] != Q.shape[1]:
            raise ValueError(
                f"CTMCDynamics: rate_matrix must be square, got shape {Q.shape!r}"
            )
        row_sums = Q.sum(axis=1)
        if not np.allclose(row_sums, 0.0, atol=1e-9):
            raise ValueError(
                f"CTMCDynamics: rate_matrix rows must sum to 0; got {row_sums!r}"
            )
        self._Q = Q

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_CTMC_CONFIG_HASH

    def step(
        self,
        state_t: Any,
        t: float,
        dt: float,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: PaperQuantitiesSnapshot | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Return the rate ``Q @ s`` (the SLOPE)."""
        dt_f = _coerce_dt(dt)
        _coerce_seed(seed)
        _validate_state_handle(state_t, kind="ctmc")
        if not isinstance(state_t, np.ndarray):
            raise ValueError(
                "CTMCDynamics.step: state must be np.ndarray simplex vector"
            )
        if state_t.ndim != 1 or state_t.shape[0] != self._Q.shape[0]:
            raise ValueError(
                f"CTMCDynamics.step: state shape {state_t.shape!r} does not "
                f"match rate matrix shape {self._Q.shape!r}"
            )
        effective_dt, did_floor = _floor_dt(dt_f, paper_quantities)
        if did_floor and audit_codes is not None:
            audit_codes.append("dynamics_dt_floored_by_paper_exterior_gap")
        return self._Q @ state_t

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "rate_matrix": self._Q.tolist(),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "CTMCDynamics":
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"CTMCDynamics.from_config: bad family {config.get('family')!r}"
            )
        rm = config.get("rate_matrix")
        if rm is None:
            raise ValueError("CTMCDynamics.from_config: rate_matrix required")
        return cls(rate_matrix=np.asarray(rm, dtype=np.float64))


def default_ctmc_dynamics() -> CTMCDynamics:
    """Canonical factory — yields a 2-state symmetric CTMC for smoke tests."""
    Q: npt.NDArray[np.float64] = np.asarray(
        [
            [-1.0, 1.0],
            [1.0, -1.0],
        ],
        dtype=np.float64,
    )
    return CTMCDynamics(rate_matrix=Q)


# ---------------------------------------------------------------------------
# BFNDynamics — Bayesian-update dynamics
# ---------------------------------------------------------------------------


class BFNDynamics:
    """Bayesian-update dynamics for discrete/structured outputs.

    Returns the per-NFE posterior delta (pred_logits - theta) as the
    SLOPE; the solver applies ``theta + alpha_dt * slope`` (the
    canonical affine blend). Mirrors the ProtBFN / AbBFN / GraphBFN
    semantics: each step is a Bayesian posterior update with an
    information schedule ``alpha_t``.
    """

    FAMILY = BFN_FAMILY

    def __init__(self) -> None:
        pass

    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return DEFAULT_BFN_CONFIG_HASH

    def step(
        self,
        state_t: Any,
        t: float,
        dt: float,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: PaperQuantitiesSnapshot | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Return the SLOPE = ``pred_logits - theta`` (the Bayesian delta)."""
        dt_f = _coerce_dt(dt)
        _coerce_seed(seed)
        _validate_state_handle(state_t, kind="bfn")
        if not isinstance(state_t, np.ndarray):
            raise ValueError(
                "BFNDynamics.step: state must be np.ndarray posterior vector"
            )
        if not (0.0 < dt_f <= 1.0):
            raise ValueError(
                f"BFNDynamics.step: dt must be in (0, 1]; got {dt_f!r}"
            )
        # Pred logits supplied via condition.delta_spec['pred_logits'].
        pred_logits = None
        if condition is not None:
            spec = getattr(condition, "delta_spec", None)
            if isinstance(spec, dict):
                pred_logits = spec.get("pred_logits")
            elif isinstance(spec, np.ndarray):
                pred_logits = spec
        if pred_logits is None:
            pred_logits = state_t  # identity fallback (no new info)
        if not isinstance(pred_logits, np.ndarray):
            pred_logits = np.asarray(pred_logits, dtype=np.float64)
        # Paper exterior-gap floor (eps_implicit clamp).
        if paper_quantities is not None:
            e_rho = float(paper_quantities.exterior_gap_e_rho)
            if math.isfinite(e_rho) and e_rho > 0.0:
                floor = e_rho * EXTERIOR_GAP_FLOOR_FRACTION
                if dt_f < floor:
                    if audit_codes is not None:
                        audit_codes.append(
                            "dynamics_alpha_floored_by_paper_exterior_gap"
                        )
        return pred_logits - state_t

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "BFNDynamics":
        if config.get("family") != cls.FAMILY:
            raise ValueError(
                f"BFNDynamics.from_config: bad family {config.get('family')!r}"
            )
        return cls()


def default_bfn_dynamics() -> BFNDynamics:
    """Canonical factory for the default :class:`BFNDynamics`."""
    return BFNDynamics()


# ---------------------------------------------------------------------------
# Adapter-specific bindings (composition; NOT inheritance)
# ---------------------------------------------------------------------------


class FlowMol3Dynamics:
    """Concrete FlowMol3 4-channel binding via composition.

    The FlowMol3 state is a 4-tuple ``(x, a, c, e)``. The composite
    dynamics delegates per-channel: continuous coordinates via
    :class:`ContinuousFMDynamics`, discrete atom/bond/charge via
    :class:`CTMCDynamics`. The split makes the (currently incorrect)
    Euler-on-logits swap to ``CTMCEulerHeunSolver`` explicit — the
    task #324 scope.

    Note: this binding does NOT call into ``flowmol3_v2_adapter`` to
    avoid the universal -> adapters import boundary. It is a pure
    typed seam; the concrete adapter chooses to opt in.
    """

    def __init__(
        self,
        *,
        coord_dynamics: DynamicsProtocol | None = None,
        atom_dynamics: DynamicsProtocol | None = None,
        bond_dynamics: DynamicsProtocol | None = None,
    ) -> None:
        self._coord = coord_dynamics if coord_dynamics is not None else ContinuousFMDynamics()
        self._atom = atom_dynamics if atom_dynamics is not None else default_ctmc_dynamics()
        self._bond = bond_dynamics if bond_dynamics is not None else default_ctmc_dynamics()

    def family(self) -> str:
        return "flowmol3_composite"

    def config_hash(self) -> str:
        return "dynamics:flowmol3_composite:v1"

    def step(
        self,
        state_t: Any,
        t: float,
        dt: float,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: PaperQuantitiesSnapshot | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Step the 4-channel state ``(x, a, c, e)`` returning 4-tuple of SLOPES."""
        if not isinstance(state_t, tuple) or len(state_t) != 4:
            raise ValueError(
                f"FlowMol3Dynamics.step: state must be 4-tuple (x,a,c,e); "
                f"got {type(state_t).__name__}"
            )
        x, a, c, e = state_t
        x_slope = self._coord.step(
            x, t, dt, condition,
            seed=seed, paper_quantities=paper_quantities, audit_codes=audit_codes,
        )
        a_slope = self._atom.step(
            a, t, dt, condition,
            seed=seed, paper_quantities=paper_quantities, audit_codes=audit_codes,
        )
        c_slope = self._coord.step(
            c, t, dt, condition,
            seed=seed, paper_quantities=paper_quantities, audit_codes=audit_codes,
        )
        e_slope = self._bond.step(
            e, t, dt, condition,
            seed=seed, paper_quantities=paper_quantities, audit_codes=audit_codes,
        )
        return (x_slope, a_slope, c_slope, e_slope)

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.family(),
            "coord_dynamics": self._coord.to_config(),
            "atom_dynamics": self._atom.to_config(),
            "bond_dynamics": self._bond.to_config(),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "FlowMol3Dynamics":
        coord = None
        atom = None
        bond = None
        cd = config.get("coord_dynamics")
        if isinstance(cd, dict):
            coord = _build_dynamics_from_config(cd)
        ad = config.get("atom_dynamics")
        if isinstance(ad, dict):
            atom = _build_dynamics_from_config(ad)
        bd = config.get("bond_dynamics")
        if isinstance(bd, dict):
            bond = _build_dynamics_from_config(bd)
        return cls(coord_dynamics=coord, atom_dynamics=atom, bond_dynamics=bond)


class ProtBFNDynamics:
    """Concrete ProtBFN categorical binding via composition.

    The ProtBFN state is a 3-tuple ``(theta, y, alpha)`` where
    ``theta`` is the per-position posterior, ``y`` is the model's
    prediction logits, and ``alpha`` is the information schedule.
    The composite dynamics delegates via :class:`BFNDynamics`; the
    ``alpha`` channel is propagated but unused by ``BFNDynamics.step``
    (the information schedule is read from ``dt`` itself).
    """

    def __init__(self, *, bfn: DynamicsProtocol | None = None) -> None:
        self._bfn = bfn if bfn is not None else BFNDynamics()

    def family(self) -> str:
        return "protbfn_bfn"

    def config_hash(self) -> str:
        return "dynamics:protbfn_bfn:v1"

    def step(
        self,
        state_t: Any,
        t: float,
        dt: float,
        condition: Any,
        *,
        seed: int = 0,
        paper_quantities: PaperQuantitiesSnapshot | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        if not isinstance(state_t, tuple) or len(state_t) != 3:
            raise ValueError(
                f"ProtBFNDynamics.step: state must be 3-tuple (theta,y,alpha); "
                f"got {type(state_t).__name__}"
            )
        theta, y, alpha = state_t
        theta_slope = self._bfn.step(
            theta, t, dt, condition,
            seed=seed, paper_quantities=paper_quantities, audit_codes=audit_codes,
        )
        # y and alpha are propagated unchanged (they're inputs).
        return (theta_slope, y, alpha)

    def to_config(self) -> dict[str, Any]:
        return {"family": self.family(), "bfn": self._bfn.to_config()}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "ProtBFNDynamics":
        bfn_cfg = config.get("bfn")
        if not isinstance(bfn_cfg, dict):
            raise ValueError("ProtBFNDynamics.from_config: bfn config required")
        bfn = _build_dynamics_from_config(bfn_cfg)
        return cls(bfn=bfn)


# ---------------------------------------------------------------------------
# Polymorphic builder (fail-closed)
# ---------------------------------------------------------------------------


def _build_dynamics_from_config(config: dict[str, Any]) -> DynamicsProtocol:
    """Polymorphic dynamics factory."""
    family = config.get("family")
    if not isinstance(family, str):
        raise ValueError(f"dynamics_family_must_be_str: got {family!r}")
    table: dict[str, Any] = {
        CONTINUOUS_FM_FAMILY: ContinuousFMDynamics,
        CTMC_FAMILY: CTMCDynamics,
        BFN_FAMILY: BFNDynamics,
        "flowmol3_composite": FlowMol3Dynamics,
        "protbfn_bfn": ProtBFNDynamics,
    }
    if family not in table:
        raise ValueError(
            f"unknown dynamics family {family!r}; registered: {sorted(table)!r}"
        )
    return table[family].from_config(config)  # type: ignore[no-any-return]


__all__ = [
    "BFN_FAMILY",
    "CONTINUOUS_FM_FAMILY",
    "CTMC_FAMILY",
    "DEFAULT_BFN_CONFIG_HASH",
    "DEFAULT_CONTINUOUS_FM_CONFIG_HASH",
    "DEFAULT_CTMC_CONFIG_HASH",
    "BFNDynamics",
    "ContinuousFMDynamics",
    "CTMCDynamics",
    "DynamicsProtocol",
    "DynamicsTrajectory",
    "EXTERIOR_GAP_FLOOR_FRACTION",
    "FlowMol3Dynamics",
    "ProtBFNDynamics",
    "default_bfn_dynamics",
    "default_continuous_fm_dynamics",
    "default_ctmc_dynamics",
]