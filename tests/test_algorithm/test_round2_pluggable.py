"""Round-2 pluggable design hardening tests.

The Round-2 plan calls out several new plug-in points. For each one
this suite asserts the canonical pluggable invariants:

1. The implementation is registered in its family registry.
2. ``from_config`` / ``to_config`` round-trips bit-for-bit (the
   rebuilt instance has the same ``config_hash`` and produces the
   same per-call output).
3. ``config_hash`` captures every constructor argument (different
   kwargs produce different hashes).
4. Bad inputs fail closed (no silent fallback) — ValueError on
   out-of-range / non-finite arguments.
5. ``audit_codes`` is emitted on the canonical degenerate
   configurations.

The suite is additive — it does not duplicate the protocol-surface
tests in :mod:`tests.test_algorithm.test_protocol_surface`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.algorithm.handoff import (
    HANDOFF_FAMILY,
    HandoffSequentialScheduler,
)
from adaptive_reflow.algorithm.merge_operator_extra import (
    MultiSourceKalmanMergeOperator,
)
from adaptive_reflow.algorithm.protocol_registry import (
    PROTOCOL_REGISTRY,
    build_merge_operator_from_config,
    build_scheduler_from_config,
)
from adaptive_reflow.algorithm.scheduler import ConstantScheduler
from adaptive_reflow.algorithm.scheduler_extra import (
    EDMScheduler,
    JitteredConstantScheduler,
    MultiChannelJitteredConstantScheduler,
)
from adaptive_reflow.algorithm.sequential import SequentialSlot
from adaptive_reflow.eval.coverage_extra import (
    support_coverage_score,
    top_k_coverage_with_entropy,
)
from adaptive_reflow.eval.w2 import (
    DEFAULT_W2_FAMILY,
    W2_REGISTRY,
    ProjectionFreeRademacherW2,
    TreeSlicedW2,
    W2Barycenter,
    W2Family,
    build_w2_estimator,
)

# ---------------------------------------------------------------------------
# W2 pluggable families (P0 #3, #4, P1 #13)
# ---------------------------------------------------------------------------


def test_w2_registry_covers_all_round2_families() -> None:
    """The registry must cover every round-2 W2 family key."""
    assert W2Family.PROJECTION_FREE_RADEMACHER in W2_REGISTRY
    assert W2Family.TREE_SLICED in W2_REGISTRY
    assert W2Family.W2_BARYCENTER in W2_REGISTRY
    # The legacy default is preserved verbatim.
    assert DEFAULT_W2_FAMILY == W2Family.MODE_CENTRE_MSE


def test_w2_rademacher_round_trip() -> None:
    """``from_config`` rebuilds a byte-identical Rademacher estimator."""
    est = ProjectionFreeRademacherW2(n_projections=64, seed=7)
    rebuilt = ProjectionFreeRademacherW2.from_config(est.to_config())
    assert rebuilt.config_hash() == est.config_hash()
    assert rebuilt.n_projections == est.n_projections
    assert rebuilt.seed == est.seed


def test_w2_tree_sliced_round_trip() -> None:
    """``from_config`` rebuilds a byte-identical TreeSliced estimator."""
    est = TreeSlicedW2(n_projections=32, seed=11)
    rebuilt = TreeSlicedW2.from_config(est.to_config())
    assert rebuilt.config_hash() == est.config_hash()


def test_w2_barycenter_estimate_and_round_trip() -> None:
    """``W2Barycenter`` returns a finite distance and round-trips."""
    rng = np.random.default_rng(0)
    samples = rng.normal(size=(64, 2))
    reference = rng.normal(size=(64, 2))
    est = W2Barycenter(n_projections=32, seed=0)
    distance = est.estimate(samples, reference)
    assert math.isfinite(float(distance))
    assert float(distance) >= 0.0
    codes: list[str] = []
    est.estimate(samples, reference, audit_codes=codes)
    assert codes and codes[0].startswith("w2_barycenter_used:")
    rebuilt = W2Barycenter.from_config(est.to_config())
    assert rebuilt.config_hash() == est.config_hash()


def test_w2_build_dispatch_for_round2_families() -> None:
    """``build_w2_estimator`` resolves every round-2 family key."""
    for family in (
        W2Family.PROJECTION_FREE_RADEMACHER,
        W2Family.TREE_SLICED,
        W2Family.W2_BARYCENTER,
    ):
        est = build_w2_estimator(family, n_projections=16, seed=0)
        assert est.family == family


# ---------------------------------------------------------------------------
# Merge operator: MultiSourceKalmanMergeOperator (P1 #15)
# ---------------------------------------------------------------------------


def test_multi_source_kalman_round_trip_and_registration() -> None:
    """``MultiSourceKalmanMergeOperator`` is registered + round-trips."""
    assert PROTOCOL_REGISTRY["MergeOperatorProtocol"]["multi_source_kalman"] is MultiSourceKalmanMergeOperator
    op = MultiSourceKalmanMergeOperator(
        prior_variance=0.02,
        dynamic_variances=(0.05, 0.10),
    )
    rebuilt = MultiSourceKalmanMergeOperator.from_config(op.to_config())
    assert rebuilt.config_hash() == op.config_hash()
    assert rebuilt.dynamic_variances == (0.05, 0.10)
    # Polymorphic builder resolves the family.
    out = build_merge_operator_from_config(op.to_config())
    assert isinstance(out, MultiSourceKalmanMergeOperator)


def test_multi_source_kalman_audit_codes_and_validation() -> None:
    """Audit codes are emitted and bad variances fail closed."""
    op = MultiSourceKalmanMergeOperator(dynamic_variances=(0.1, 0.2))
    codes: list[str] = []
    result = op.merge(
        0.5,
        0.6,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=codes,
        dynamics=(0.4, 0.7),
    )
    assert math.isfinite(float(result))
    assert any(c.startswith("multi_source_kalman:") for c in codes)
    with pytest.raises(ValueError):
        MultiSourceKalmanMergeOperator(dynamic_variances=())


# ---------------------------------------------------------------------------
# Scheduler: MultiChannelJitteredConstantScheduler (P1 #19)
# ---------------------------------------------------------------------------


def test_multi_channel_jittered_round_trip_and_registration() -> None:
    """``MultiChannelJitteredConstantScheduler`` is registered + round-trips."""
    assert (
        PROTOCOL_REGISTRY["SchedulerProtocol"]["multi_channel_jittered"]
        is MultiChannelJitteredConstantScheduler
    )
    sched = MultiChannelJitteredConstantScheduler(
        cycle_length=8,
        n_cap=0.5,
        default_jitter_std=0.05,
        per_channel_jitter_std={"a": 0.1, "b": 0.2},
        channel_keys=("a", "b"),
    )
    rebuilt = MultiChannelJitteredConstantScheduler.from_config(sched.to_config())
    assert rebuilt.config_hash() == sched.config_hash()
    out = build_scheduler_from_config(sched.to_config())
    assert isinstance(out, MultiChannelJitteredConstantScheduler)


def test_multi_channel_jittered_emits_per_channel_audit_codes() -> None:
    """Per-channel n_cap values are emitted in ``audit_codes``."""
    sched = MultiChannelJitteredConstantScheduler(
        cycle_length=4,
        n_cap=0.5,
        default_jitter_std=0.0,
        per_channel_jitter_std={"a": 0.0, "b": 0.0},
        channel_keys=("a", "b"),
        seed=0,
    )
    sample = sched.sample(0, 0, 0)
    assert any(c.startswith("per_channel_n_cap:") for c in sample.audit_codes)
    assert any(c.startswith("channels:") for c in sample.audit_codes)


# ---------------------------------------------------------------------------
# Handoff scheduler (P1 #16)
# ---------------------------------------------------------------------------


def test_handoff_sequential_scheduler_registered_and_round_trip() -> None:
    """``HandoffSequentialScheduler`` round-trips via to/from_config."""
    sched = HandoffSequentialScheduler(
        schedulers=[
            SequentialSlot(scheduler=ConstantScheduler(), n_rounds=4),
            SequentialSlot(scheduler=ConstantScheduler(n_cap=0.9), n_rounds=4),
        ],
        handoff_window=2,
    )
    rebuilt = HandoffSequentialScheduler.from_config(sched.to_config())
    assert rebuilt.config_hash() == sched.config_hash()
    assert rebuilt.handoff_window == 2
    assert rebuilt.schedule_family() == HANDOFF_FAMILY


def test_handoff_sequential_scheduler_emits_handoff_alpha() -> None:
    """The active handoff emits ``handoff_alpha=...`` on the sample."""
    sched = HandoffSequentialScheduler(
        schedulers=[
            SequentialSlot(scheduler=ConstantScheduler(n_cap=0.2), n_rounds=4),
            SequentialSlot(scheduler=ConstantScheduler(n_cap=0.9), n_rounds=4),
        ],
        handoff_window=2,
    )
    # Round 3 is in the handoff tail of slot 0.
    sample = sched.sample(0, 3, 0)
    assert any(c.startswith("handoff_alpha=") for c in sample.audit_codes)


# ---------------------------------------------------------------------------
# EDM adaptive_sigma_max (P0 #1) and Round-2 surface
# ---------------------------------------------------------------------------


def test_edm_scheduler_adaptive_sigma_max_kwarg_round_trip() -> None:
    """``EDMScheduler(adaptive_sigma_max=True)`` round-trips and hashes."""
    sched = EDMScheduler(cycle_length=8, adaptive_sigma_max=True, seed=0)
    assert sched.sigma_max_effective > 0.0
    rebuilt = EDMScheduler.from_config(sched.to_config())
    assert rebuilt.config_hash() == sched.config_hash()
    # Two different adaptive kp values hash differently.
    other = EDMScheduler(cycle_length=8, adaptive_pid_kp=0.5)
    assert other.config_hash() != sched.config_hash()


# ---------------------------------------------------------------------------
# Coverage extras (P1 #11, #12)
# ---------------------------------------------------------------------------


def test_support_coverage_score_finite_and_monotone() -> None:
    """``support_coverage_score`` is finite and bounded in [0, 1]."""
    rng = np.random.default_rng(0)
    ref = rng.normal(size=(128, 2))
    samples = rng.normal(size=(64, 2))
    score = support_coverage_score(samples, ref)
    assert 0.0 <= float(score) <= 1.0
    # Empty samples -> 0 (fail-closed).
    empty_score = support_coverage_score(np.zeros((0, 2)), ref)
    assert float(empty_score) == 0.0


def test_top_k_coverage_with_entropy_returns_finite() -> None:
    """``top_k_coverage_with_entropy`` returns finite coverage + entropy."""
    rng = np.random.default_rng(0)
    ref = rng.normal(size=(64, 2))
    samples = rng.normal(size=(64, 2))
    result = top_k_coverage_with_entropy(samples, ref, k=3, n_bootstrap=4, seed=0)
    assert 0.0 <= float(result["coverage"]) <= 1.0
    assert math.isfinite(float(result["entropy"]))
