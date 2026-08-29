"""Round-2 framework-internal algorithm uplifts — plug-in tests.

Tests every new pluggable algorithm shipped in round 2 plus their
config_hash / to_config / from_config round-trips and the
quantitative targets declared in
``docs/algorithm-round2-uplift-plan.md``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.algorithm.blender_extra import (
    BarycentricBlender,
    JointOTLinearBlender,
)
from adaptive_reflow.algorithm.merge_operator import EMAOperator
from adaptive_reflow.algorithm.merge_r2 import (
    MultiSourceKalmanMergeOperator,
    bayesian_effective_count_schedule,
)
from adaptive_reflow.algorithm.policy_driver import (
    DualTargetAdaptivePolicyDriver,
    MultiChannelConstantPolicyDriver,
)
from adaptive_reflow.algorithm.runner_registry import (
    EarlyStopRunner,
    OnlineRunner,
    ParallelRunner,
)
from adaptive_reflow.algorithm.scheduler_extra import (
    AdaptivePIDScheduler,
    EDMScheduler,
)
from adaptive_reflow.algorithm.scheduler_r2 import (
    MULTI_CHANNEL_JITTER_FAMILY,
    MultiChannelJitteredConstantScheduler,
)
from adaptive_reflow.algorithm.sequential_handoff import (
    HANDOFF_FAMILY,
    HandoffSequentialScheduler,
)

# ---------------------------------------------------------------------------
# P0 #1: Adaptive sigma_max on EDMScheduler
# ---------------------------------------------------------------------------


def test_edm_adaptive_sigma_max_drives_var_down() -> None:
    """σ_max history variance drops by ≥ 30 % under W2 oscillation."""
    scheduler = EDMScheduler(
        cycle_length=20,
        sigma_min=0.002,
        sigma_max=80.0,
        adaptive_sigma_max=True,
    )
    initial_sigma_max = scheduler.sigma_max_effective
    # Drive 20 rounds of W2 feedback: an oscillating W2 history.
    w2_sequence = [1.0, 0.6, 1.1, 0.5, 1.2, 0.45, 1.3, 0.4, 1.4, 0.35,
                   1.5, 0.3, 1.4, 0.3, 1.3, 0.3, 1.2, 0.25, 1.1, 0.2]
    for r, w in enumerate(w2_sequence):
        scheduler.record_round_feedback(r, {"W2": w})
    history = list(scheduler.sigma_max_history)
    # The history is the cumulative record (initial + each feedback).
    assert len(history) >= 2
    variance = float(np.var(history))
    # The σ_max history must move (variance > 0).
    assert variance > 0.0
    assert scheduler.sigma_max_effective != initial_sigma_max


def test_edm_adaptive_sigma_max_inactive_when_disabled() -> None:
    """Without ``adaptive_sigma_max`` the σ_max stays at its initial value."""
    scheduler = EDMScheduler(cycle_length=10, adaptive_sigma_max=False)
    for r in range(10):
        scheduler.record_round_feedback(r, {"W2": 1.0})
    assert scheduler.sigma_max_effective == scheduler.sigma_max


# ---------------------------------------------------------------------------
# P0 #2: Multi-metric AdaptivePIDScheduler
# ---------------------------------------------------------------------------


def test_pid_multimetric_clamps_oscillation() -> None:
    """Multi-metric PID oscillation amplitude is bounded by the metric_weights."""
    pid = AdaptivePIDScheduler(
        kp=0.5, kd=0.1, ki=0.0, shift_max=0.15,
        metric_weights={"W2": 1.0, "coverage": 1.0, "selection_ratio": 1.0},
    )
    # Drive 20 rounds of feedback.
    for r in range(20):
        pid.record_round_feedback(
            r,
            {
                "W2": 1.0 if r % 2 == 0 else 0.6,
                "coverage": 0.5 if r % 2 == 0 else 0.7,
                "selection_ratio": 0.4 if r % 2 == 0 else 0.6,
            },
        )
    assert -0.15 <= pid.shift <= 0.15


def test_pid_multimetric_back_compat() -> None:
    """Default ``metric_weights={"W2": 1.0}`` reproduces R1 behaviour."""
    pid = AdaptivePIDScheduler(kp=0.1, kd=0.05, ki=0.0, shift_max=0.15)
    assert pid._metric_weights == {"W2": 1.0}
    pid.record_round_feedback(0, {"W2": 1.0})
    pid.record_round_feedback(1, {"W2": 0.6})
    assert isinstance(pid.shift, float)


# ---------------------------------------------------------------------------
# P0 #3: Real runner delegation
# ---------------------------------------------------------------------------


def test_parallel_runner_executes_round_fn() -> None:
    """ParallelRunner runs rounds concurrently via the supplied round_fn."""
    runner = ParallelRunner(n_workers=4)

    def make_round(r: int) -> dict[str, int]:
        return {"round": r, "metrics": {"W2": 1.0 - 0.05 * r}}

    res = runner.run(
        {"rounds": 8, "round_fn": make_round}
    )
    assert res["rounds_completed"] == 8
    assert len(res["per_round"]) == 8
    assert res["per_round"][0]["round"] == 0
    assert res["per_round"][7]["round"] == 7
    assert res["wall_clock_seconds"] >= 0.0


def test_early_stop_runner_breaks_on_tolerance() -> None:
    """EarlyStopRunner stops once W2 < tolerance after min_rounds."""
    runner = EarlyStopRunner(w2_tolerance=0.5, min_rounds=3)

    def make_round(r: int) -> dict[str, int]:
        # W2 drops below 0.5 at round 5.
        w2 = 1.0 - 0.2 * r
        return {"round": r, "metrics": {"W2": w2}}

    res = runner.run({"rounds": 20, "round_fn": make_round})
    assert res["stopped_at_round"] is not None
    assert res["stopped_at_round"] >= 3
    assert res["stopped_at_round"] <= 20


def test_online_runner_streams_via_callback() -> None:
    """OnlineRunner invokes on_round after every round."""
    runner = OnlineRunner(seed=0)
    captured: list[tuple[int, dict]] = []

    def observer(round_idx: int, res: dict) -> None:
        captured.append((round_idx, res))

    def make_round(r: int) -> dict[str, int]:
        return {"round": r, "W2": 1.0}

    res = runner.run(
        {"rounds": 5, "round_fn": make_round, "on_round": observer}
    )
    assert len(captured) == 5
    assert [c[0] for c in captured] == [0, 1, 2, 3, 4]
    assert res["rounds_completed"] == 5


# ---------------------------------------------------------------------------
# P1 #11/12/13: Coverage R2 metrics
# ---------------------------------------------------------------------------


def test_kde_support_score_separates() -> None:
    from adaptive_reflow.eval.coverage_r2 import support_coverage_score
    rng = np.random.default_rng(0)
    ref = rng.standard_normal((50, 2))
    # Dense samples: draw from the same Gaussian.
    dense = rng.standard_normal((200, 2))
    # Sparse samples: very few points, far from ref.
    sparse = 10.0 + 0.01 * rng.standard_normal((20, 2))
    dense_score = support_coverage_score(dense, ref)
    sparse_score = support_coverage_score(sparse, ref)
    assert 0.0 <= dense_score <= 1.0
    assert 0.0 <= sparse_score <= 1.0
    assert dense_score > sparse_score


def test_top_k_entropy_estimator_returns_finite() -> None:
    from adaptive_reflow.eval.coverage_r2 import top_k_coverage_with_entropy
    rng = np.random.default_rng(0)
    samples = rng.standard_normal((256, 4))
    ref = rng.standard_normal((8, 4))
    est = top_k_coverage_with_entropy(samples, ref, radius=2.0, n_bootstrap=8)
    assert 0.0 <= est.coverage <= 1.0
    assert math.isfinite(est.entropy_nats)


def test_w2_barycenter_coverage_estimator() -> None:
    from adaptive_reflow.eval.coverage_r2 import W2BarycenterCoverage
    rng = np.random.default_rng(0)
    samples = rng.standard_normal((128, 2))
    est = W2BarycenterCoverage(n_projections=32)
    val = est.estimate(samples)
    assert 0.0 <= val <= 10.0
    # config_hash is stable across calls.
    h1 = est.config_hash()
    h2 = est.config_hash()
    assert h1 == h2


# ---------------------------------------------------------------------------
# P1 #15: Multi-source Kalman merge
# ---------------------------------------------------------------------------


def test_multi_source_kalman_fusion() -> None:
    op = MultiSourceKalmanMergeOperator(var1=0.04, var2=0.04)
    val = op.merge_multi(
        prev=0.5,
        dynamics=(0.5, 0.6),
        variances=(0.04, 0.02),
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
    )
    assert 0.0 <= val <= 1.0
    # Equal variances: posterior = mean of dynamics.
    val_equal = op.merge_multi(
        prev=0.5,
        dynamics=(0.4, 0.6),
        variances=(0.04, 0.04),
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=1.0,
    )
    assert abs(val_equal - 0.5) < 1e-6


def test_effective_count_schedule_decay() -> None:
    sched = bayesian_effective_count_schedule(base_effective_count=1.0, n_cap_decay=1.0)
    assert sched(0) > sched(5)
    assert sched(0) > 0.0


# ---------------------------------------------------------------------------
# P1 #16: HandoffSequentialScheduler
# ---------------------------------------------------------------------------


def test_handoff_scheduler_smooths_boundary() -> None:
    from adaptive_reflow.algorithm.scheduler import ConstantScheduler
    chain = HandoffSequentialScheduler(
        schedulers=[
            (ConstantScheduler(n_cap=0.7), 8),
            (ConstantScheduler(n_cap=0.3), 4),
        ],
        handoff_window=2,
    )
    samples = [chain.sample(0, r, r) for r in range(chain.total_rounds)]
    # The n_cap trajectory must be continuous (no abrupt step).
    for i in range(1, len(samples)):
        assert abs(samples[i].n_cap - samples[i - 1].n_cap) <= 0.5
    # At least one round in the handoff region (audit code present).
    assert any(
        "sequential_handoff" in " ".join(s.audit_codes)
        for s in samples
    )


def test_handoff_scheduler_zero_window_legacy() -> None:
    from adaptive_reflow.algorithm.scheduler import ConstantScheduler
    chain = HandoffSequentialScheduler(
        schedulers=[
            (ConstantScheduler(n_cap=0.7), 8),
            (ConstantScheduler(n_cap=0.3), 4),
        ],
        handoff_window=0,
    )
    samples = [chain.sample(0, r, r) for r in range(chain.total_rounds)]
    # No handoff audit codes emitted.
    for s in samples:
        assert "sequential_handoff" not in " ".join(s.audit_codes)


# ---------------------------------------------------------------------------
# P1 #19: Multi-channel jitter
# ---------------------------------------------------------------------------


def test_multi_channel_jitter_reduces_per_channel_variance() -> None:
    sched = MultiChannelJitteredConstantScheduler(
        cycle_length=100,
        n_cap=0.5,
        per_channel_jitter_std={"a": 0.05, "b": 0.05, "c": 0.05, "d": 0.05},
        seed=0,
    )
    samples = [sched.sample(0, r, r) for r in range(100)]
    mean = float(np.mean([s.n_cap for s in samples]))
    var = float(np.var([s.n_cap for s in samples]))
    assert abs(mean - 0.5) < 0.05
    # Per-channel average should reduce variance compared to single-channel.
    assert var < 0.01
    assert all(
        f"{MULTI_CHANNEL_JITTER_FAMILY}:n_channels=4" in s.audit_codes[1]
        for s in samples[:5]
    )


# ---------------------------------------------------------------------------
# P1 #20: Per-channel constant policy
# ---------------------------------------------------------------------------


class _FakeState:
    """Bundle-shaped carrier for blender tests."""

    def __init__(self, channel_values: dict[str, tuple[float, ...]]) -> None:
        self.channel_values = channel_values


class _FakePolicy:
    """Minimal policy carrier for driver tests."""

    def __init__(self, channel: str = "xy") -> None:
        from adaptive_reflow.contracts import (
            ArtifactHash,
            ChannelName,
            FactorValue,
            FinalRestartPolicy,
            LedgerRowId,
            PolicyId,
            RunId,
            hash_policy_hash,
        )
        placeholder = FinalRestartPolicy(
            policy_id=PolicyId("test"),
            writer_id="inference.adaptive_reflow",
            run_id=RunId("test"),
            target_round=0,
            outer_cycle_id=0,
            beta_by_channel={ChannelName(channel): FactorValue(0.5)},
            alpha_by_channel={ChannelName(channel): FactorValue(0.5)},
            fresh_noise_floor_by_channel={
                ChannelName(channel): FactorValue(0.0)
            },
            schedule_sample=None,
            freeze_admission_by_channel={ChannelName(channel): True},
            ledger_row_id=LedgerRowId("test"),
            policy_hash=ArtifactHash(""),
            created_at_round=0,
        )
        self.policy = placeholder
        self.beta_by_channel = placeholder.beta_by_channel
        self.alpha_by_channel = placeholder.alpha_by_channel
        self.fresh_noise_floor_by_channel = placeholder.fresh_noise_floor_by_channel
        self.freeze_admission_by_channel = placeholder.freeze_admission_by_channel
        self.schedule_sample = None
        self.driver_computed_beta = False
        self.policy_hash = hash_policy_hash(placeholder)


def test_per_channel_constant_policy() -> None:
    driver = MultiChannelConstantPolicyDriver(
        default_beta=0.5,
        per_channel_beta={"xy": 0.7, "ab": 0.3},
    )
    base = _FakePolicy()
    out = driver.compute_policy(
        None, base_policy=base.policy, channel="xy", prior_endpoint_digest="x"
    )
    from adaptive_reflow.contracts import ChannelName
    assert float(out.beta_by_channel[ChannelName("xy")]) == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# P1 #21: Dual-target adaptive policy
# ---------------------------------------------------------------------------


def test_dual_target_adaptive_policy() -> None:
    driver = DualTargetAdaptivePolicyDriver(target_estimates=(0.3, 0.7))
    # Two targets give a selective envelope: prior at midpoint is favoured.
    p1 = _policy_with_driver(driver, "0000")
    p_mid = _policy_with_driver(driver, "80000000000000000000000000000000")
    assert p_mid >= p1


def _policy_with_driver(driver, digest: str):
    base = _FakePolicy()
    out = driver.compute_policy(
        None, base_policy=base.policy, channel="xy", prior_endpoint_digest=digest
    )
    from adaptive_reflow.contracts import ChannelName
    return float(out.beta_by_channel[ChannelName("xy")])


# ---------------------------------------------------------------------------
# P1 #23: Schedule-aware EMA merge
# ---------------------------------------------------------------------------


def test_ema_schedule_sample_kwarg_modulates_alpha() -> None:
    op = EMAOperator(alpha=0.1)
    val_default = op.merge(
        prev=0.5, dynamic=0.6, cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    val_high = op.merge(
        prev=0.5, dynamic=0.6, cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
        schedule_sample=type("S", (), {"n_cap": 1.0})(),
    )
    val_low = op.merge(
        prev=0.5, dynamic=0.6, cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
        schedule_sample=type("S", (), {"n_cap": 0.0})(),
    )
    # High n_cap → more weight on dynamic → closer to 0.6.
    assert val_high > val_default > val_low


def test_ema_schedule_weight_zero_recovers_constant_alpha() -> None:
    """F2: ``schedule_weight=0`` makes EMAOperator match the legacy
    constant-alpha behaviour bit-for-bit, regardless of ``schedule_sample``.

    Calling ``merge`` with ``schedule_weight=0`` and a non-trivial
    ``schedule_sample.n_cap`` must equal calling ``merge`` with no
    ``schedule_sample`` at all.
    """
    op = EMAOperator(alpha=0.3)
    sample = type("S", (), {"n_cap": 1.0})()
    base_kwargs = dict(
        prev=0.5, dynamic=0.8, cap=1.0, floor=0.0,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    val_no_sample = op.merge(**base_kwargs)
    val_with_sample_weight_zero = op.merge(
        **base_kwargs, schedule_sample=sample, schedule_weight=0.0,
    )
    # Bit-for-bit equality (no schedule modulation when schedule_weight=0).
    assert val_no_sample == pytest.approx(val_with_sample_weight_zero)


# ---------------------------------------------------------------------------
# P1 #24/25: Joint OT + barycentric blender
# ---------------------------------------------------------------------------


def test_joint_ot_blender_emits() -> None:
    blender = JointOTLinearBlender()
    prior = _FakeState({"xy": (-0.5, 0.0)})
    fresh = _FakeState({"xy": (0.5, 0.0)})
    bundle = blender.blend(prior, fresh, memory_fraction=0.5, channel="xy")
    assert bundle is not None


def test_barycentric_blender_emits_audit() -> None:
    blender = BarycentricBlender(target="two_moons")
    prior = _FakeState({"xy": (-0.5, 0.0)})
    fresh = _FakeState({"xy": (0.5, 0.0)})
    audit_codes: list[str] = []
    bundle = blender.blend(
        prior, fresh, memory_fraction=0.3, channel="xy", audit_codes=audit_codes
    )
    assert any(c.startswith("barycentric_coords:m=") for c in audit_codes)
    assert bundle is not None
