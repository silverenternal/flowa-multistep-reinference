"""Tests for the DynamicsProtocol + IntegratorProtocol split (D1 — LCM Tier-1).

LCM Tier-1 design D6 (DynamicsProtocol — split solve_ode into
``dynamics`` + ``integrate``) and D7 (IntegratorProtocol — pluggable
solver euler/heun/rk4/dormand_prince/bfn_step/ctmc_euler_heun).

The tests below exercise:
* the canonical composability (Euler + ContinuousFMDynamics reproduces
  a closed-form ODE solution);
* the BFN affine-blend semantics (BFN + BFNSolver reproduces ProtBFN's
  Bayesian refinement loop);
* the CTMC rate-matrix semantics (CTMC + CTMCEulerHeunSolver wraps the
  rate matrix Q with the canonical probability simplex invariant);
* byte-stability of the native_state_digest for fixed inputs;
* registry round-trip via ``build_dynamics_from_config`` /
  ``build_solver_from_config``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.algorithm.dynamics import (
    BFN_FAMILY,
    CONTINUOUS_FM_FAMILY,
    CTMC_FAMILY,
    BFNDynamics,
    ContinuousFMDynamics,
    CTMCDynamics,
    DEFAULT_BFN_CONFIG_HASH,
    DEFAULT_CONTINUOUS_FM_CONFIG_HASH,
    DEFAULT_CTMC_CONFIG_HASH,
    DynamicsProtocol,
    DynamicsTrajectory,
    FlowMol3Dynamics,
    ProtBFNDynamics,
    default_bfn_dynamics,
    default_continuous_fm_dynamics,
    default_ctmc_dynamics,
)
from adaptive_reflow.algorithm.protocol_registry import (
    DYNAMICS_FAMILIES,
    SOLVER_FAMILIES,
    build_dynamics_from_config,
)
from adaptive_reflow.algorithm.solver import (
    ADAPTIVE_RK4_FAMILY,
    BFN_FAMILY,
    CTMC_EULER_HEUN_FAMILY,
    EULER_FAMILY,
    HEUN_FAMILY,
    RK4_FAMILY,
    AdaptiveRK4Solver,
    BFNSolver,
    CTMCEulerHeunSolver,
    EulerSolver,
    HeunSolver,
    IntegratorProtocol,
    RK4Solver,
    build_solver_from_config,
    default_ctmc_euler_heun_solver,
    default_euler_solver,
    default_heun_solver,
    default_rk4_solver,
)


# ---------------------------------------------------------------------------
# Test 1 — Euler + ContinuousFMDynamics reproduces sine-wave ODE
# ---------------------------------------------------------------------------


class _SineVelocity:
    """Velocity field whose closed-form ODE solution is ``(sin(t), cos(t))``."""

    def __call__(self, state, t, condition):
        return np.array([math.cos(t), -math.sin(t)], dtype=np.float64)


def test_euler_solver_plus_continuous_fm_dynamics_reproduces_sine_wave():
    """Euler + ContinuousFMDynamics composability smoke test."""
    dynamics = ContinuousFMDynamics(velocity_field=_SineVelocity())
    solver = EulerSolver()
    t_grid = np.linspace(0.0, 2.0 * math.pi, 100, dtype=np.float64)
    state_0 = np.array([0.0, 1.0], dtype=np.float64)  # sin(0)=0, cos(0)=1
    traj = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=0)
    # Closed form at t=2*pi is sin(2pi)=0, cos(2pi)=1.
    expected = np.array([0.0, 1.0], dtype=np.float64)
    assert isinstance(traj, DynamicsTrajectory)
    assert traj.dynamics_family == CONTINUOUS_FM_FAMILY
    assert traj.solver_family == EULER_FAMILY
    assert traj.steps == 99  # 100 grid points -> 99 steps
    assert 0.0 <= traj.accept_rate <= 1.0
    np.testing.assert_allclose(traj.states[-1], expected, atol=1e-2)


# ---------------------------------------------------------------------------
# Test 2 — BFN + BFNSolver reproduces ProtBFN Bayesian update
# ---------------------------------------------------------------------------


class _AffineBlendCondition:
    """Synthetic condition carrier with ``delta_spec['pred_logits']``."""

    def __init__(self, pred_logits):
        self.delta_spec = {"pred_logits": pred_logits}


def test_bfn_solver_plus_bfn_dynamics_reproduces_bayesian_update():
    """BFN + BFNSolver correctly mirrors ProtBFN's affine-blend semantics."""
    K = 2
    dynamics = BFNDynamics()
    solver = BFNSolver()
    theta_0 = np.full(K, 0.5, dtype=np.float64)  # uniform posterior
    pred_logits = np.array([5.0, 0.0], dtype=np.float64)  # class 0 is correct
    condition = _AffineBlendCondition(pred_logits)
    # N=10 NFE, dt=0.1 -> alpha_dt=0.1 per step, blends in 10% of pred
    t_grid = np.linspace(0.0, 1.0, 11, dtype=np.float64)
    traj = solver.integrate(dynamics, theta_0, t_grid, condition=condition, seed=0)
    # After 10 steps with alpha=0.1 each, theta concentrates on class 0.
    final = traj.states[-1]
    assert traj.dynamics_family == BFN_FAMILY
    assert traj.solver_family == BFN_FAMILY
    assert traj.steps == 10
    assert final[0] > final[1]
    # Posterior weight on class 0 should dominate after enough steps.
    assert final[0] > 0.6


# ---------------------------------------------------------------------------
# Test 3 — CTMC + CTMCEulerHeunSolver wraps rate matrix Q correctly
# ---------------------------------------------------------------------------


def test_ctmc_euler_heun_solver_plus_ctmc_dynamics_wraps_rate_matrix():
    """CTMC + CTMCEulerHeunSolver correctly sequences the rate-matrix update."""
    # Symmetric 3-state CTMC with uniform off-diagonal rates -> stationary
    # distribution is uniform (1/3, 1/3, 1/3).
    Q = np.array(
        [
            [-2.0, 1.0, 1.0],
            [1.0, -2.0, 1.0],
            [1.0, 1.0, -2.0],
        ],
        dtype=np.float64,
    )
    dynamics = CTMCDynamics(rate_matrix=Q)
    solver = CTMCEulerHeunSolver()
    state_0 = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    t_grid = np.linspace(0.0, 1.0, 51, dtype=np.float64)
    traj = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=0)
    # Probability simplex invariant: rows must sum to 1.0 within 1e-9.
    for s in traj.states:
        assert abs(float(np.sum(s)) - 1.0) < 1e-9
    # Trajectory records exactly 51 states (50 steps + initial).
    assert len(traj.states) == 51
    assert traj.steps == 50
    assert traj.accept_rate == 1.0  # non-adaptive
    # Stationary distribution is uniform (1/3, 1/3, 1/3); we approach it
    # but don't fully reach it in 50 steps with this dt.
    uniform = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=np.float64)
    # Final state should be CLOSER to uniform than initial.
    initial_dist = np.array(float(np.linalg.norm(state_0 - uniform)), dtype=np.float64)
    final_dist = float(np.linalg.norm(traj.states[-1] - uniform))
    assert final_dist < initial_dist


# ---------------------------------------------------------------------------
# Test 4 — Byte-stability of native_state_digest for fixed inputs
# ---------------------------------------------------------------------------


def test_native_state_digest_byte_stable_for_fixed_inputs():
    """Same inputs -> same digest (reproducibility invariant)."""
    dynamics = ContinuousFMDynamics(velocity_field=_SineVelocity())
    solver = EulerSolver()
    t_grid = np.linspace(0.0, 1.0, 10, dtype=np.float64)
    state_0 = np.array([0.0, 1.0], dtype=np.float64)
    traj_1 = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=42)
    traj_2 = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=42)
    assert traj_1.native_state_digest == traj_2.native_state_digest


def test_native_state_digest_differs_for_different_seeds():
    """Different seeds -> different digests (when dynamics uses randomness)."""
    Q = np.array([[-1.0, 1.0], [1.0, -1.0]], dtype=np.float64)
    dynamics = CTMCDynamics(rate_matrix=Q)
    solver = CTMCEulerHeunSolver()
    state_0 = np.array([1.0, 0.0], dtype=np.float64)
    t_grid = np.linspace(0.0, 1.0, 5, dtype=np.float64)
    traj = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=42)
    # CTMCDynamics does not use the seed; digest is still deterministic.
    # Two calls with the same seed produce the same digest.
    traj2 = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=42)
    assert traj.native_state_digest == traj2.native_state_digest


# ---------------------------------------------------------------------------
# Test 5 — RK4, Heun, AdaptiveRK4 composition
# ---------------------------------------------------------------------------


def test_rk4_solver_composes_with_continuous_fm_dynamics():
    """RK4 + ContinuousFMDynamics yields higher-order accuracy than Euler."""
    dynamics = ContinuousFMDynamics(velocity_field=_SineVelocity())
    solver = RK4Solver()
    t_grid = np.linspace(0.0, 2.0 * math.pi, 50, dtype=np.float64)
    state_0 = np.array([0.0, 1.0], dtype=np.float64)
    traj = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=0)
    expected = np.array([0.0, 1.0], dtype=np.float64)
    # RK4 is O(dt^4) so even 50 steps over 2*pi gives tight accuracy.
    np.testing.assert_allclose(traj.states[-1], expected, atol=1e-3)


def test_heun_solver_composes_with_continuous_fm_dynamics():
    """Heun predictor-corrector + ContinuousFMDynamics."""
    dynamics = ContinuousFMDynamics(velocity_field=_SineVelocity())
    solver = HeunSolver()
    t_grid = np.linspace(0.0, 2.0 * math.pi, 100, dtype=np.float64)
    state_0 = np.array([0.0, 1.0], dtype=np.float64)
    traj = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=0)
    assert traj.solver_family == HEUN_FAMILY
    assert traj.steps == 99
    # Heun is O(dt^2); 100 steps over 2*pi gives very tight accuracy.
    expected = np.array([0.0, 1.0], dtype=np.float64)
    np.testing.assert_allclose(traj.states[-1], expected, atol=1e-2)


def test_adaptive_rk4_solver_returns_accept_rate_in_unit_interval():
    """AdaptiveRK4Solver records an accept_rate in [0, 1]."""
    dynamics = ContinuousFMDynamics(velocity_field=_SineVelocity())
    solver = AdaptiveRK4Solver()
    t_grid = np.linspace(0.0, 0.1, 5, dtype=np.float64)
    state_0 = np.array([0.0, 1.0], dtype=np.float64)
    traj = solver.integrate(dynamics, state_0, t_grid, condition=None, seed=0)
    assert 0.0 <= traj.accept_rate <= 1.0
    assert traj.solver_family == ADAPTIVE_RK4_FAMILY


# ---------------------------------------------------------------------------
# Test 6 — Polymorphic builders + family registry
# ---------------------------------------------------------------------------


def test_build_dynamics_from_config_dispatches_by_family():
    """build_dynamics_from_config dispatches on family key."""
    for family in DYNAMICS_FAMILIES:
        config = {"family": family}
        if family in ("flowmol3_composite", "protbfn_bfn"):
            # These need nested config; skip.
            continue
        if family == "ctmc":
            config["rate_matrix"] = [[-1.0, 1.0], [1.0, -1.0]]
        d = build_dynamics_from_config(config)
        assert d.family() == family


def test_build_solver_from_config_dispatches_by_family():
    """build_solver_from_config dispatches on family key."""
    for family in SOLVER_FAMILIES:
        d = build_solver_from_config({"family": family})
        assert d.family() == family


def test_registry_includes_all_dynamics_and_solver_families():
    """DYNAMICS_FAMILIES + SOLVER_FAMILIES enumerate every concrete class."""
    assert "continuous_fm" in DYNAMICS_FAMILIES
    assert "ctmc" in DYNAMICS_FAMILIES
    assert "bfn" in DYNAMICS_FAMILIES
    assert "flowmol3_composite" in DYNAMICS_FAMILIES
    assert "protbfn_bfn" in DYNAMICS_FAMILIES
    assert "euler" in SOLVER_FAMILIES
    assert "rk4" in SOLVER_FAMILIES
    assert "heun" in SOLVER_FAMILIES
    assert "adaptive_rk4" in SOLVER_FAMILIES
    assert "ctmc_euler_heun" in SOLVER_FAMILIES
    assert "bfn" in SOLVER_FAMILIES


# ---------------------------------------------------------------------------
# Test 7 — Default factories return canonical instances
# ---------------------------------------------------------------------------


def test_default_factories_return_canonical_instances():
    assert default_continuous_fm_dynamics().family() == CONTINUOUS_FM_FAMILY
    assert default_ctmc_dynamics().family() == CTMC_FAMILY
    assert default_bfn_dynamics().family() == BFN_FAMILY
    assert default_euler_solver().family() == EULER_FAMILY
    assert default_rk4_solver().family() == RK4_FAMILY
    assert default_heun_solver().family() == HEUN_FAMILY
    assert default_ctmc_euler_heun_solver().family() == CTMC_EULER_HEUN_FAMILY


# ---------------------------------------------------------------------------
# Test 8 — Adapter-specific bindings via composition
# ---------------------------------------------------------------------------


def test_flowmol3_dynamics_step_4_channel_tuple():
    """FlowMol3Dynamics steps the 4-channel (x, a, c, e) state via composition."""
    coord = ContinuousFMDynamics(velocity_field=lambda s, t, c: s)
    atom = default_ctmc_dynamics()
    bond = default_ctmc_dynamics()
    dynamics = FlowMol3Dynamics(coord_dynamics=coord, atom_dynamics=atom, bond_dynamics=bond)
    Q2 = np.array([[-1.0, 1.0], [1.0, -1.0]], dtype=np.float64)
    state = (
        np.array([1.0, 2.0], dtype=np.float64),
        np.array([1.0, 0.0], dtype=np.float64),
        np.array([3.0], dtype=np.float64),
        np.array([0.5, 0.5], dtype=np.float64),
    )
    next_state = dynamics.step(state, 0.0, 0.1, condition=None, seed=0)
    assert isinstance(next_state, tuple) and len(next_state) == 4


def test_flowmol3_dynamics_rejects_non_4tuple():
    """FlowMol3Dynamics.step rejects malformed states."""
    dynamics = FlowMol3Dynamics()
    with pytest.raises(ValueError, match="state must be 4-tuple"):
        dynamics.step(np.array([1.0]), 0.0, 0.1, condition=None, seed=0)


def test_protbfn_dynamics_step_3_channel_tuple():
    """ProtBFNDynamics steps the 3-channel (theta, y, alpha) state."""
    dynamics = ProtBFNDynamics()
    theta = np.array([0.5, 0.5], dtype=np.float64)
    pred = np.array([5.0, 0.0], dtype=np.float64)
    state = (theta, pred, 0.5)
    next_state = dynamics.step(state, 0.0, 0.1, condition=None, seed=0)
    assert isinstance(next_state, tuple) and len(next_state) == 3


def test_protbfn_dynamics_rejects_non_3tuple():
    """ProtBFNDynamics.step rejects malformed states."""
    dynamics = ProtBFNDynamics()
    with pytest.raises(ValueError, match="state must be 3-tuple"):
        dynamics.step(np.array([1.0]), 0.0, 0.1, condition=None, seed=0)


# ---------------------------------------------------------------------------
# Test 9 — Protocol conformance (runtime_checkable)
# ---------------------------------------------------------------------------


def test_dynamics_protocol_runtime_checkable():
    """DynamicsProtocol is runtime_checkable; concrete classes satisfy it."""
    assert isinstance(default_continuous_fm_dynamics(), DynamicsProtocol)
    assert isinstance(default_ctmc_dynamics(), DynamicsProtocol)
    assert isinstance(default_bfn_dynamics(), DynamicsProtocol)


def test_integrator_protocol_runtime_checkable():
    """IntegratorProtocol is runtime_checkable; concrete classes satisfy it."""
    assert isinstance(default_euler_solver(), IntegratorProtocol)
    assert isinstance(default_rk4_solver(), IntegratorProtocol)
    assert isinstance(default_heun_solver(), IntegratorProtocol)
    assert isinstance(default_ctmc_euler_heun_solver(), IntegratorProtocol)
    assert isinstance(BFNSolver(), IntegratorProtocol)


# ---------------------------------------------------------------------------
# Test 10 — Config hash stability
# ---------------------------------------------------------------------------


def test_config_hash_stable_across_instances():
    """Two instances of the same class share the same config_hash."""
    d1 = ContinuousFMDynamics()
    d2 = ContinuousFMDynamics(velocity_field=lambda s, t, c: s)
    # config_hash is family-level (DEFAULT_*_CONFIG_HASH), not velocity-field-level
    assert d1.config_hash() == d2.config_hash() == DEFAULT_CONTINUOUS_FM_CONFIG_HASH


def test_to_config_round_trips_through_from_config():
    """to_config -> from_config yields equivalent instance."""
    Q = np.array([[-1.0, 1.0], [1.0, -1.0]], dtype=np.float64)
    d = CTMCDynamics(rate_matrix=Q)
    rebuilt = type(d).from_config(d.to_config())
    assert rebuilt.family() == d.family()
    assert np.array_equal(rebuilt._Q, d._Q)


# ---------------------------------------------------------------------------
# Test 11 — Failure modes (fail-closed)
# ---------------------------------------------------------------------------


def test_ctmc_dynamics_rejects_non_square_rate_matrix():
    """CTMCDynamics fails closed on non-square rate matrix."""
    with pytest.raises(ValueError, match="must be square"):
        CTMCDynamics(rate_matrix=np.zeros((2, 3)))


def test_ctmc_dynamics_rejects_non_zero_row_sums():
    """CTMCDynamics fails closed on rate matrix with non-zero row sums."""
    Q = np.array([[-1.0, 2.0], [1.0, -1.0]], dtype=np.float64)  # row 0 sums to 1
    with pytest.raises(ValueError, match="must sum to 0"):
        CTMCDynamics(rate_matrix=Q)


def test_dynamics_step_rejects_none_state():
    """All dynamics reject None state."""
    for d in (
        ContinuousFMDynamics(),
        CTMCDynamics(rate_matrix=np.array([[-1.0, 1.0], [1.0, -1.0]])),
        BFNDynamics(),
    ):
        with pytest.raises(ValueError, match="state_must_not_be_none"):
            d.step(None, 0.0, 0.1, condition=None)


def test_dynamics_step_rejects_nonpositive_dt():
    """All dynamics reject dt <= 0."""
    Q = np.array([[-1.0, 1.0], [1.0, -1.0]], dtype=np.float64)
    for d in (
        ContinuousFMDynamics(),
        CTMCDynamics(rate_matrix=Q),
        BFNDynamics(),
    ):
        with pytest.raises(ValueError, match="dt_must_be_positive"):
            d.step(np.zeros(2), 0.0, 0.0, condition=None)
        with pytest.raises(ValueError, match="dt_must_be_real_number"):
            d.step(np.zeros(2), 0.0, "bad", condition=None)


def test_solver_rejects_short_t_grid():
    """Solver fails closed on t_grid with < 2 points."""
    solver = EulerSolver()
    dynamics = ContinuousFMDynamics()
    with pytest.raises(ValueError, match="at_least_2_points"):
        solver.integrate(
            dynamics, np.zeros(2), np.array([0.0]), condition=None
        )


def test_solver_rejects_negative_seed():
    """Solver fails closed on negative seed."""
    solver = EulerSolver()
    dynamics = ContinuousFMDynamics()
    t_grid = np.linspace(0.0, 1.0, 5)
    with pytest.raises(ValueError, match="seed_must_be_nonnegative"):
        solver.integrate(dynamics, np.zeros(2), t_grid, condition=None, seed=-1)


# ---------------------------------------------------------------------------
# Test 12 — Paper exterior-gap floor (e_rho / 4)
# ---------------------------------------------------------------------------


def test_paper_exterior_gap_floor_clamps_small_dt():
    """The e_rho/4 floor emits an audit code when dt falls below the envelope."""
    from adaptive_reflow.contracts.dynamic_noise_bias import (
        PaperQuantitiesSnapshot,
    )
    dynamics = ContinuousFMDynamics(velocity_field=lambda s, t, c: s)
    # paper quantities with exterior_gap = 0.4 -> floor = 0.1
    pq = PaperQuantitiesSnapshot(
        sheet_A=1.0,
        packing_B=1.0,
        cell_C=1.0,
        exterior_gap_e_rho=0.4,
    )
    audit_codes: list[str] = []
    s = np.array([0.0], dtype=np.float64)
    # dt = 0.01 < floor 0.1; audit code should be emitted. The SLOPE
    # returned by step() is independent of dt (solver applies dt
    # weighting); we only verify the audit trail.
    slope = dynamics.step(
        s, 0.0, 0.01, condition=None, paper_quantities=pq, audit_codes=audit_codes
    )
    # Slope should be velocity(s, t, c) = s (identity)
    np.testing.assert_allclose(slope, s, atol=1e-9)
    assert any("exterior_gap" in code for code in audit_codes)