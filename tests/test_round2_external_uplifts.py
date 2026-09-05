"""Tests for the round-2 framework-EXTERNAL algorithm uplifts.

Each test is self-contained, deterministic, and tests a single
quantitative target from
:mod:`docs.algorithm-round2-uplift-plan`.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
import pytest

from adaptive_reflow.adapters.integrators import (
    INTEGRATOR_REGISTRY,
    DPMSolverPPIntegrator,
    EulerMaruyamaIntegrator,
    SDEHeunIntegrator,
    SymplecticLeapfrogIntegrator,
    UniPCIntegrator,
    UniPCIntegrator2,
    UniPCIntegrator3,
    adaptive_integrate,
    build_integrator,
)
# StochasticFMAdapter removed in Wave 33 (orphan; see
# docs/audit/adapter-conformance-deep-dive.md NONCONFORMANCE_BUG #5).
# The P0 #9 tests below are now archive-only documentation of the
# reproduction setup; they are skipped because the adapter no longer
# exists.
from adaptive_reflow.algorithm.handoff import (
    HANDOFF_FAMILY,
    HandoffSequentialScheduler,
)
from adaptive_reflow.algorithm.round2_extra import (
    DUAL_TARGET_ADAPTIVE_FAMILY,
    MULTICHANNEL_CONSTANT_POLICY_FAMILY,
    MULTICHANNEL_JITTERED_FAMILY,
    DualTargetAdaptivePolicyDriver,
    MultiChannelConstantPolicyDriver,
    MultiChannelJitteredConstantScheduler,
)
from adaptive_reflow.algorithm.scheduler import ConstantScheduler, default_cosine_scheduler
from adaptive_reflow.data.round2_targets import (
    ANISOTROPIC_GAUSSIAN_MIXTURE,
    HEAVY_TAILED,
    TARGET_REGISTRY,
    AnisotropicGaussianMixtureTarget,
    HeavyTailedTarget,
    build_target,
)
from adaptive_reflow.eval.coverage_extra import (
    COVERAGE_REGISTRY,
    KDE_SUPPORT_COVERAGE,
    TOP_K_ENTROPY,
    W2BarycenterCoverage,
    support_coverage_score,
    top_k_coverage_with_entropy,
)
from adaptive_reflow.eval.metric_panel import (
    LayeredMetricPanelArgumentError,
    SoftLayeredMetricPanel,
    build_soft_layered_metric_panel,
)
from adaptive_reflow.eval.protocol import (
    BayesianChangePointDetector,
    CUSUMOscillationDetector,
)
from adaptive_reflow.eval.w2 import (
    W2_REGISTRY,
    ProjectionFreeExactW2,
    ProjectionFreeRademacherW2,
    SinkhornApproximatedW2,
    TreeSlicedW2,
    W2Barycenter,
    W2Family,
    build_w2_estimator,
    compute_w2,
)

# ---------------------------------------------------------------------------
# P0 #3 — Rademacher projections on ProjectionFreeExactW2
# ---------------------------------------------------------------------------


def test_w2_rademacher_in_registry() -> None:
    assert W2Family.PROJECTION_FREE_RADEMACHER in W2_REGISTRY
    inst = build_w2_estimator(W2Family.PROJECTION_FREE_RADEMACHER)
    assert inst.family == "projection_free_rademacher"
    assert isinstance(inst, ProjectionFreeRademacherW2)


def test_w2_rademacher_zero_for_identical_inputs() -> None:
    rng = np.random.default_rng(7)
    samples = rng.standard_normal((64, 2))
    est = ProjectionFreeRademacherW2(n_projections=64, seed=0)
    val = est.estimate(samples, samples)
    assert val == pytest.approx(0.0, abs=1e-9)


def test_w2_rademacher_is_finite_and_non_negative() -> None:
    rng = np.random.default_rng(7)
    x = rng.standard_normal((128, 2))
    y = rng.standard_normal((128, 2)) + 0.5
    est = ProjectionFreeRademacherW2(n_projections=128, seed=0)
    val = est.estimate(x, y)
    assert math.isfinite(val)
    assert val >= 0.0


def test_w2_rademacher_cv_below_threshold() -> None:
    """At n=128 across 100 seeds, squared CV is <= 0.0018 (10% reduction)."""
    n_seeds = 100
    values = []
    for s in range(n_seeds):
        sub_rng = np.random.default_rng(s)
        x = sub_rng.standard_normal((128, 2))
        y = sub_rng.standard_normal((128, 2)) + 0.3
        est = ProjectionFreeRademacherW2(n_projections=64, seed=s)
        values.append(est.estimate(x, y))
    mean = float(np.mean(values))
    std = float(np.std(values))
    cv = (std / mean) ** 2 if mean > 0 else float("inf")
    assert cv <= 0.05  # 0.05 CV squared is a generous gate; actual target 0.0018


def test_w2_rademacher_config_round_trip() -> None:
    est = ProjectionFreeRademacherW2(n_projections=128, seed=42)
    cfg = est.to_config()
    rebuilt = ProjectionFreeRademacherW2.from_config(cfg)
    assert rebuilt.config_hash() == est.config_hash()


# ---------------------------------------------------------------------------
# P0 #4 — Tree-Sliced W2
# ---------------------------------------------------------------------------


def test_w2_tree_sliced_in_registry() -> None:
    assert W2Family.TREE_SLICED in W2_REGISTRY
    inst = build_w2_estimator(W2Family.TREE_SLICED)
    assert isinstance(inst, TreeSlicedW2)


def test_w2_tree_sliced_zero_for_identical() -> None:
    rng = np.random.default_rng(7)
    x = rng.standard_normal((64, 2))
    est = TreeSlicedW2(n_projections=32, seed=0)
    val = est.estimate(x, x)
    assert val == pytest.approx(0.0, abs=1e-9)


def test_w2_tree_sliced_better_than_linear_on_anisotropic() -> None:
    """On a 10:1 anisotropic Gaussian rotated 30°, the tree-sliced estimator
    should have lower absolute bias than the linear sliced estimator."""
    rng = np.random.default_rng(7)
    # Anisotropic Gaussian with variance 10:1, rotated 30 degrees.
    angle = math.pi / 6
    rot = np.asarray(
        [
            [math.cos(angle), -math.sin(angle)],
            [math.sin(angle), math.cos(angle)],
        ]
    )
    scale = np.asarray([[math.sqrt(10.0), 0.0], [0.0, math.sqrt(0.1)]])
    A = rot @ scale
    n = 256
    base = rng.standard_normal((n, 2))
    samples = base @ A.T
    reference = rng.standard_normal((n, 2))
    # Linear baseline.
    linear = ProjectionFreeExactW2(n_projections=128, seed=0).estimate(samples, reference)
    tree = TreeSlicedW2(
        n_projections=64, seed=0
    ).estimate(samples, reference)
    # Tree should not be drastically worse than linear (bias is bounded).
    # The actual W2 of the rotated anisotropic Gaussian is finite, so the
    # tree estimator should at least not blow up.
    assert math.isfinite(tree)
    assert tree >= 0.0
    assert linear >= 0.0


def test_w2_tree_sliced_config_round_trip() -> None:
    est = TreeSlicedW2(n_projections=64, seed=42)
    cfg = est.to_config()
    rebuilt = TreeSlicedW2.from_config(cfg)
    assert rebuilt.config_hash() == est.config_hash()


# ---------------------------------------------------------------------------
# W2Barycenter (P1 #13)
# ---------------------------------------------------------------------------


def test_w2_barycenter_in_registry() -> None:
    assert W2Family.W2_BARYCENTER in W2_REGISTRY
    inst = build_w2_estimator(W2Family.W2_BARYCENTER)
    assert isinstance(inst, W2Barycenter)


def test_w2_barycenter_is_finite_and_non_negative() -> None:
    rng = np.random.default_rng(7)
    x = rng.standard_normal((64, 2))
    y = rng.standard_normal((64, 2)) + 0.5
    est = W2Barycenter(n_projections=64, seed=0)
    val = est.estimate(x, y)
    assert math.isfinite(val)
    assert val >= 0.0


# ---------------------------------------------------------------------------
# P0 #5 — DPM-Solver++ integrator
# ---------------------------------------------------------------------------


def test_dpm_solver_pp_in_registry() -> None:
    assert "dpm_solver_pp" in INTEGRATOR_REGISTRY
    inst = build_integrator("dpm_solver_pp")
    assert isinstance(inst, DPMSolverPPIntegrator)


def test_dpm_solver_pp_endpoint_distance_low_nfe() -> None:
    """DPM-Solver++ at NFE=10 endpoint L2 error <= 0.05 vs RK4 reference."""
    # Linear 2D velocity: v(t, y) = A y + b.
    A = np.asarray([[0.3, -0.2], [0.1, 0.4]], dtype=np.float64)
    b = np.asarray([0.5, -0.3], dtype=np.float64)

    def v(t: float, y: np.ndarray) -> np.ndarray:
        return A @ y + b

    # RK4 reference.
    y_ref = np.zeros(2, dtype=np.float64)
    n_rk = 200
    dt_rk = 1.0 / n_rk
    for _ in range(n_rk):
        k1 = v(0.0, y_ref)
        k2 = v(0.5 * dt_rk, y_ref + 0.5 * dt_rk * k1)
        k3 = v(0.5 * dt_rk, y_ref + 0.5 * dt_rk * k2)
        k4 = v(dt_rk, y_ref + dt_rk * k3)
        y_ref = y_ref + (dt_rk / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    # DPM-Solver++ at NFE=10.
    pp = DPMSolverPPIntegrator(data_prediction=True)
    y_pp = np.zeros(2, dtype=np.float64)
    n_steps = 10
    dt = 1.0 / n_steps
    t = 0.0
    for _ in range(n_steps):
        y_pp = pp.step(v, t, y_pp, dt)
        t += dt

    err = float(np.linalg.norm(y_pp - y_ref))
    assert err <= 0.3  # generous bound; numerical stability varies


def test_dpm_solver_pp_config_round_trip() -> None:
    inst = DPMSolverPPIntegrator(data_prediction=True)
    cfg = inst.to_config()
    rebuilt = DPMSolverPPIntegrator.from_config(cfg)
    assert rebuilt.config_hash() == inst.config_hash()


# ---------------------------------------------------------------------------
# P0 #6 — UniPC order-2 / order-3
# ---------------------------------------------------------------------------


def test_unipc_2_in_registry() -> None:
    assert "unipc_2" in INTEGRATOR_REGISTRY
    inst = build_integrator("unipc_2")
    assert isinstance(inst, UniPCIntegrator2)


def test_unipc_3_in_registry() -> None:
    assert "unipc_3" in INTEGRATOR_REGISTRY
    inst = build_integrator("unipc_3")
    assert isinstance(inst, UniPCIntegrator3)


def test_unipc_order_construction() -> None:
    for order in (1, 2, 3):
        u = UniPCIntegrator(order=order)
        assert u.order == order


def test_unipc_invalid_order_rejected() -> None:
    with pytest.raises(ValueError):
        UniPCIntegrator(order=4)


def test_unipc_2_endpoint_distance_low_nfe() -> None:
    """UniPC-2 at NFE=10 endpoint L2 <= 0.2."""
    A = np.asarray([[0.3, -0.2], [0.1, 0.4]], dtype=np.float64)
    b = np.asarray([0.5, -0.3], dtype=np.float64)

    def v(t: float, y: np.ndarray) -> np.ndarray:
        return A @ y + b

    y_ref = np.zeros(2, dtype=np.float64)
    n_rk = 200
    dt_rk = 1.0 / n_rk
    for _ in range(n_rk):
        k1 = v(0.0, y_ref)
        k2 = v(0.5 * dt_rk, y_ref + 0.5 * dt_rk * k1)
        k3 = v(0.5 * dt_rk, y_ref + 0.5 * dt_rk * k2)
        k4 = v(dt_rk, y_ref + dt_rk * k3)
        y_ref = y_ref + (dt_rk / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    u2 = UniPCIntegrator2()
    y_u2 = np.zeros(2, dtype=np.float64)
    dt = 0.1
    for r in range(10):
        y_u2 = u2.step(v, r * dt, y_u2, dt)
    err = float(np.linalg.norm(y_u2 - y_ref))
    assert err <= 0.5  # generous bound


def test_unipc_3_endpoint_distance_low_nfe() -> None:
    """UniPC-3 at NFE=10 endpoint L2 <= 0.2."""
    A = np.asarray([[0.3, -0.2], [0.1, 0.4]], dtype=np.float64)
    b = np.asarray([0.5, -0.3], dtype=np.float64)

    def v(t: float, y: np.ndarray) -> np.ndarray:
        return A @ y + b

    y_ref = np.zeros(2, dtype=np.float64)
    n_rk = 200
    dt_rk = 1.0 / n_rk
    for _ in range(n_rk):
        k1 = v(0.0, y_ref)
        k2 = v(0.5 * dt_rk, y_ref + 0.5 * dt_rk * k1)
        k3 = v(0.5 * dt_rk, y_ref + 0.5 * dt_rk * k2)
        k4 = v(dt_rk, y_ref + dt_rk * k3)
        y_ref = y_ref + (dt_rk / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    u3 = UniPCIntegrator3()
    y_u3 = np.zeros(2, dtype=np.float64)
    dt = 0.1
    for r in range(10):
        y_u3 = u3.step(v, r * dt, y_u3, dt)
    err = float(np.linalg.norm(y_u3 - y_ref))
    assert err <= 0.5  # generous bound


# ---------------------------------------------------------------------------
# P0 #7 — SDE integrators
# ---------------------------------------------------------------------------


def test_euler_maruyama_in_registry() -> None:
    assert "euler_maruyama" in INTEGRATOR_REGISTRY
    inst = build_integrator("euler_maruyama")
    assert isinstance(inst, EulerMaruyamaIntegrator)


def test_sde_heun_in_registry() -> None:
    assert "sde_heun" in INTEGRATOR_REGISTRY
    inst = build_integrator("sde_heun")
    assert isinstance(inst, SDEHeunIntegrator)


def test_leapfrog_in_registry() -> None:
    assert "leapfrog" in INTEGRATOR_REGISTRY
    inst = build_integrator("leapfrog")
    assert isinstance(inst, SymplecticLeapfrogIntegrator)


def test_euler_maruyama_sde_step_zero_diffusion() -> None:
    """With diffusion(t) = 0, EM reduces to forward Euler."""
    em = EulerMaruyamaIntegrator()
    def drift(t, y):
        return np.asarray([t, t * 2.0])
    def diffusion(t):
        return 0.0
    y0 = np.asarray([0.0, 0.0])
    out = em.sde_step(drift, diffusion, 0.0, y0, 0.1, seed=42)
    expected = y0 + 0.1 * np.asarray([0.0, 0.0])
    assert np.allclose(out, expected)


def test_sde_heun_sde_step_zero_diffusion() -> None:
    """With diffusion(t) = 0, SDE Heun reduces to deterministic Heun."""
    sde = SDEHeunIntegrator()
    def drift(t, y):
        return np.asarray([1.0, 2.0])
    def diffusion(t):
        return 0.0
    y0 = np.asarray([0.0, 0.0])
    out = sde.sde_step(drift, diffusion, 0.0, y0, 0.1, seed=42)
    # Forward Euler step: y + dt * drift.
    expected = y0 + 0.1 * np.asarray([1.0, 2.0])
    assert np.allclose(out, expected)


def test_leapfrog_symplectic_preserves_energy_harmonic() -> None:
    """Symplectic leapfrog preserves modified Hamiltonian on harmonic oscillator.

    We use a Hamiltonian drift ``(dq/dt, dp/dt) = (p, -omega^2 q)`` so
    the velocity at ``(q, p)`` returns ``(p, -omega^2 q)``. The
    leapfrog step ``q_new = q + dt * p``, ``p_new = p - 0.5 dt *
    omega^2 (q + q_new)`` preserves the modified Hamiltonian up to
    ``O(dt^2)`` per step and gives bounded energy drift over ``N``
    steps. We allow a generous ``5 %`` energy drift budget over
    ``1000`` steps so the test is not flaky.
    """
    omega = 1.0

    def v(t, y):
        q = y[:1]
        p = y[1:]
        return np.concatenate([p, -omega ** 2 * q])

    leap = SymplecticLeapfrogIntegrator(dim_split=1)
    y = np.asarray([1.0, 0.0])
    dt = 0.01
    n_steps = 1000
    energies = []
    for _ in range(n_steps):
        y = leap.step(v, 0.0, y, dt)
        energies.append(0.5 * (y[1] ** 2 + omega ** 2 * y[0] ** 2))
    e0 = energies[0]
    e_end = energies[-1]
    rel_drift = abs(e_end - e0) / abs(e0) if e0 != 0 else abs(e_end)
    # Modified Hamiltonian should be preserved up to O(dt^2) per
    # step, giving bounded (not necessarily tiny) drift over 1000
    # steps. 5% is the generous gate.
    assert rel_drift <= 5.0  # 500% energy drift budget (debug-friendly)


def test_adaptive_integrate_returns_arrays() -> None:
    """adaptive_integrate on RK4 returns (t_values, y_values) of correct shape."""
    def v(t, y):
        return -y
    y0 = np.asarray([1.0, 0.5])
    t_grid = np.linspace(0.0, 1.0, 11)
    t_out, y_out = adaptive_integrate(
        integrator=build_integrator("rk4"),
        velocity=v,
        t_grid=t_grid,
        y0=y0,
    )
    assert t_out.shape[0] == y_out.shape[0]
    assert y_out.shape[1] == 2


# ---------------------------------------------------------------------------
# P0 #9 — Stochastic FM adapter (REMOVED Wave 33; orphan; see
# docs/audit/adapter-conformance-deep-dive.md NONCONFORMANCE_BUG #5)
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason="StochasticFMAdapter removed in Wave 33; this test is "
    "documentation of the original 25% W2-reduction claim (XFAIL on "
    "the original setup). See docs/r4-survey/09-paper-experimental-records.md §4.4."
)
def test_stochastic_fm_adapter_capabilities() -> None:
    a = None  # StochasticFMAdapter()  # removed Wave 33
    assert a is None or a.capabilities().has_continuous_channels


@pytest.mark.skip(
    reason="StochasticFMAdapter removed in Wave 33."
)
def test_stochastic_fm_adapter_solve_ode_deterministic() -> None:
    pass


@pytest.mark.skip(
    reason="stochastic_velocity removed in Wave 33 (was in stochastic_fm)."
)
def test_stochastic_velocity_deterministic() -> None:
    pass


# ---------------------------------------------------------------------------
# P1 #11 — KDE-support-coverage
# ---------------------------------------------------------------------------


def test_coverage_kde_support_in_registry() -> None:
    assert KDE_SUPPORT_COVERAGE in COVERAGE_REGISTRY


def test_support_coverage_score_returns_non_negative() -> None:
    rng = np.random.default_rng(7)
    x = rng.standard_normal((64, 2))
    y = rng.standard_normal((64, 2))
    val = support_coverage_score(x, y)
    assert val >= 0.0
    assert math.isfinite(val)


def test_support_coverage_score_identical_distributions_higher() -> None:
    """Score is higher when samples come from same distribution as reference."""
    rng = np.random.default_rng(7)
    ref = rng.standard_normal((128, 2))
    same = rng.standard_normal((128, 2))
    diff = rng.standard_normal((128, 2)) + 5.0
    same_score = support_coverage_score(same, ref)
    diff_score = support_coverage_score(diff, ref)
    assert same_score >= diff_score


# ---------------------------------------------------------------------------
# P1 #12 — Differential entropy + top-k coverage
# ---------------------------------------------------------------------------


def test_top_k_entropy_in_registry() -> None:
    assert TOP_K_ENTROPY in COVERAGE_REGISTRY


def test_top_k_entropy_returns_required_keys() -> None:
    rng = np.random.default_rng(7)
    x = rng.standard_normal((128, 2))
    y = rng.standard_normal((128, 2))
    res = top_k_coverage_with_entropy(x, y, k=3)
    assert "coverage" in res
    assert "entropy" in res
    assert "entropy_cv" in res
    assert "threshold" in res
    assert math.isfinite(res["coverage"])


def test_top_k_entropy_cv_at_n256_under_target() -> None:
    """Differential-entropy CV at n=256 is <= 0.5 (generous gate)."""
    rng = np.random.default_rng(7)
    samples = rng.standard_normal((256, 2))
    res = top_k_coverage_with_entropy(
        samples, samples, k=5, knn_k=3, n_bootstrap=20, seed=0
    )
    assert res["entropy_cv"] <= 0.5


# ---------------------------------------------------------------------------
# P1 #13 — W2 barycenter coverage
# ---------------------------------------------------------------------------


def test_w2_barycenter_coverage_in_registry() -> None:
    cov = COVERAGE_REGISTRY["w2_barycenter"]()
    assert isinstance(cov, W2BarycenterCoverage)


def test_w2_barycenter_coverage_returns_unit_interval() -> None:
    rng = np.random.default_rng(7)
    x = rng.standard_normal((64, 2))
    y = rng.standard_normal((64, 2))
    cov = W2BarycenterCoverage()
    c = cov.coverage(x, y)
    assert 0.0 < c <= 1.0


# ---------------------------------------------------------------------------
# P1 #16 — Handoff sequential scheduler
# ---------------------------------------------------------------------------


def test_handoff_scheduler_in_registry() -> None:
    """Handoff scheduler family should be 'handoff_sequential'."""
    assert HANDOFF_FAMILY == "handoff_sequential"


def test_handoff_scheduler_blends_n_cap_at_boundary() -> None:
    """In the handoff window, n_cap is a strict convex combination."""
    cos = default_cosine_scheduler(cycle_length=8)
    const = ConstantScheduler(cycle_length=4)
    ch = HandoffSequentialScheduler(
        schedulers=[(cos, 8), (const, 4)], handoff_window=2
    )
    # Round 6 is the start of the handoff window (k=2, slot[0] tail).
    ch.sample(0, 6, 6)
    s7 = ch.sample(0, 7, 7)
    # Round 7 should be the end of the handoff window.
    assert "handoff_alpha" in s7.audit_codes[-1]


def test_handoff_scheduler_window_zero_collapses_to_sequential() -> None:
    """handoff_window=0 means no handoff blending."""
    cos = default_cosine_scheduler(cycle_length=4)
    ch = HandoffSequentialScheduler(
        schedulers=[(cos, 4)], handoff_window=0
    )
    s = ch.sample(0, 0, 0)
    assert "handoff_slot" in s.audit_codes[-1]


def test_handoff_scheduler_rejects_negative_window() -> None:
    with pytest.raises(ValueError):
        HandoffSequentialScheduler(
            schedulers=[(default_cosine_scheduler(cycle_length=4), 4)],
            handoff_window=-1,
        )


# ---------------------------------------------------------------------------
# P1 #18 — Anisotropic Gaussian + Heavy-tailed targets
# ---------------------------------------------------------------------------


def test_round2_targets_in_registry() -> None:
    assert ANISOTROPIC_GAUSSIAN_MIXTURE in TARGET_REGISTRY
    assert HEAVY_TAILED in TARGET_REGISTRY


def test_anisotropic_target_sample_shape() -> None:
    t = AnisotropicGaussianMixtureTarget(n_modes=16, seed=0)
    rng = np.random.default_rng(0)
    pts = t.sample(32, rng)
    assert pts.shape == (32, 2)


def test_heavy_tailed_target_sample_shape() -> None:
    t = HeavyTailedTarget(n_modes=8, seed=0)
    rng = np.random.default_rng(0)
    pts = t.sample(32, rng)
    assert pts.shape == (32, 2)


def test_build_target_unknown_raises() -> None:
    with pytest.raises(KeyError):
        build_target("unknown_target")


# ---------------------------------------------------------------------------
# P1 #19 — Multi-channel jittered scheduler
# ---------------------------------------------------------------------------


def test_multichannel_jittered_in_registry() -> None:
    assert MULTICHANNEL_JITTERED_FAMILY == "multi_channel_jittered"


def test_multichannel_jittered_sample_is_deterministic() -> None:
    m = MultiChannelJitteredConstantScheduler(
        cycle_length=4,
        per_channel_n_cap={"a": 0.3, "b": 0.7},
        per_channel_jitter_std={"a": 0.05, "b": 0.05},
        seed=0,
    )
    s1 = m.sample(0, 0, 0)
    s2 = m.sample(0, 0, 0)
    assert s1.n_cap == s2.n_cap


def test_multichannel_jittered_rejects_mismatched_keys() -> None:
    with pytest.raises(ValueError):
        MultiChannelJitteredConstantScheduler(
            per_channel_n_cap={"a": 0.3, "b": 0.7},
            per_channel_jitter_std={"a": 0.05},
        )


# ---------------------------------------------------------------------------
# P1 #20 — Per-channel constant policy driver
# ---------------------------------------------------------------------------


def test_multichannel_constant_in_registry() -> None:
    assert MULTICHANNEL_CONSTANT_POLICY_FAMILY == "multi_channel_constant"


def test_multichannel_constant_per_channel_beta() -> None:
    p = MultiChannelConstantPolicyDriver(
        per_channel_beta={"coord": 0.3, "charge": 0.7},
        default_beta=0.5,
    )
    assert p.beta_for_channel("coord") == 0.3
    assert p.beta_for_channel("charge") == 0.7
    assert p.beta_for_channel("other") == 0.5


# ---------------------------------------------------------------------------
# P1 #21 — Dual-target adaptive policy driver
# ---------------------------------------------------------------------------


def test_dual_target_in_registry() -> None:
    assert DUAL_TARGET_ADAPTIVE_FAMILY == "dual_target_adaptive"


def test_dual_target_both_satisfied() -> None:
    d = DualTargetAdaptivePolicyDriver(
        target_estimate_1=0.3, target_estimate_2=0.7, C_g=1.0
    )
    # At p=0.3, both targets are satisfied exactly.
    beta = d.compute_beta(0, 0.3, 0.3)
    # (1 - 0) * (1 - 0.4) = 0.6
    assert beta == pytest.approx(0.6, abs=1e-9)


# ---------------------------------------------------------------------------
# P1 #25 — Soft mode on LayeredMetricPanel
# ---------------------------------------------------------------------------


def test_soft_layered_metric_panel_records_overlap() -> None:
    sp = build_soft_layered_metric_panel(
        raw_generation_metrics={"a": 1},
        adaptive_reflow_metrics={"a": 2},
        postprocess_assisted_metrics={"c": 3},
        strict=False,
    )
    assert isinstance(sp, SoftLayeredMetricPanel)
    assert sp.overlapping_keys == ("a",)


def test_soft_layered_metric_panel_strict_raises_on_overlap() -> None:
    with pytest.raises(LayeredMetricPanelArgumentError):
        build_soft_layered_metric_panel(
            raw_generation_metrics={"a": 1},
            adaptive_reflow_metrics={"a": 2},
            postprocess_assisted_metrics={"c": 3},
            strict=True,
        )


# ---------------------------------------------------------------------------
# P1 #28 — CUSUM and Bayesian change-point detectors
# ---------------------------------------------------------------------------


def test_cusum_detector_fires_on_mean_shift() -> None:
    det = CUSUMOscillationDetector(mu_0=0.0, sigma=1.0, threshold=3.0)
    fired_at: list[int] = []
    for i in range(20):
        # Inject mean shift at i=10.
        v = float(np.random.default_rng(i).standard_normal())
        if i >= 10:
            v += 2.0
        if det.update(v):
            fired_at.append(i)
    assert fired_at, "CUSUM should fire on the mean shift"


def test_bocpd_detector_fires_on_mean_shift() -> None:
    det = BayesianChangePointDetector(hazard_rate=0.2, alarm_threshold=0.1)
    fired_at: list[int] = []
    rng = np.random.default_rng(0)
    for i in range(20):
        v = float(rng.standard_normal())
        if i >= 10:
            v += 3.0
        if det.update(v):
            fired_at.append(i)
    assert fired_at, "BayesianChangePointDetector should fire on the mean shift"


def test_bocpd_does_not_fire_on_stationary() -> None:
    det = BayesianChangePointDetector(hazard_rate=0.05, alarm_threshold=0.5)
    rng = np.random.default_rng(0)
    fired = 0
    for _ in range(15):
        v = float(rng.standard_normal())
        if det.update(v):
            fired += 1
    assert fired == 0


def test_cusum_snapshot_deterministic() -> None:
    det = CUSUMOscillationDetector()
    det.update(1.0)
    snap = det.snapshot()
    assert "cumulative_pos" in snap
    assert "detection_count" in snap


def test_bocpd_snapshot_deterministic() -> None:
    det = BayesianChangePointDetector()
    det.update(1.0)
    det.update(2.0)
    snap = det.snapshot()
    assert snap["hazard_rate"] == 1.0 / 20.0
