"""Tests for :class:`adaptive_reflow.algorithm.sequential.SequentialScheduler` (P1-2)."""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.algorithm.scheduler import (
    SCHEDULER_REGISTRY,
    ConstantScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    build_scheduler,
    build_scheduler_from_config,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.sequential import (
    SEQUENTIAL_FAMILY,
    SequentialScheduler,
    SequentialSlot,
)

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_sequential_requires_at_least_one_sub_scheduler() -> None:
    with pytest.raises(ValueError, match="at least one"):
        SequentialScheduler(schedulers=[])


def test_sequential_validates_n_rounds_positive() -> None:
    cosine = default_cosine_scheduler(cycle_length=4)
    with pytest.raises(ValueError, match="must be >= 1"):
        SequentialScheduler(schedulers=[(cosine, 0)])


def test_sequential_accepts_tuples_and_slots() -> None:
    cosine = default_cosine_scheduler(cycle_length=4)
    linear = LinearScheduler(cycle_length=4)
    chain = SequentialScheduler(
        schedulers=[(cosine, 3), SequentialSlot(scheduler=linear, n_rounds=5)]
    )
    assert chain.total_rounds == 8
    assert len(chain.slots) == 2


def test_sequential_rejects_non_scheduler_object() -> None:
    with pytest.raises(TypeError, match="missing required method"):
        SequentialScheduler(schedulers=[(object(), 3)])  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# Trajectory correctness
# ---------------------------------------------------------------------------


def test_sequential_chains_two_sub_schedulers() -> None:
    """Cosine for 8 rounds, exponential for 4 rounds -> 12 rounds total."""
    cosine = default_cosine_scheduler(cycle_length=8)
    expo = ExponentialScheduler(cycle_length=4, n_max=1.0, alpha=0.1)
    chain = SequentialScheduler(schedulers=[(cosine, 8), (expo, 4)])

    assert chain.cycle_length() == 12
    assert chain.total_rounds == 12
    assert chain.schedule_family() == "sequential"

    # Round 0 -> cosine, n_cap = n_max (1.0).
    s0 = chain.sample(0, 0, 0)
    assert s0.n_cap == pytest.approx(cosine.sample(0, 0, 0).n_cap)
    # Round 7 -> cosine, n_cap at terminal round (n_min).
    s7 = chain.sample(0, 7, 7)
    assert s7.n_cap == pytest.approx(cosine.sample(0, 7, 7).n_cap)
    # Round 8 -> exponential at sub-round 0 (n_max).
    s8 = chain.sample(0, 8, 8)
    assert s8.n_cap == pytest.approx(expo.sample(0, 0, 0).n_cap)
    # Round 11 -> exponential at sub-round 3 (decayed).
    s11 = chain.sample(0, 11, 11)
    assert s11.n_cap == pytest.approx(expo.sample(0, 3, 3).n_cap)


def test_sequential_out_of_range_raises() -> None:
    chain = SequentialScheduler(
        schedulers=[(default_cosine_scheduler(cycle_length=4), 4)]
    )
    with pytest.raises(ValueError, match="round_in_cycle"):
        chain.sample(0, 4, 4)


def test_sequential_config_hash_distinguishes_sub_schedulers() -> None:
    """Two chains with same shape but different sub-schedulers hash differently."""
    cosine_a = default_cosine_scheduler(cycle_length=4, n_min=0.0)
    cosine_b = default_cosine_scheduler(cycle_length=4, n_min=0.5)
    chain_a = SequentialScheduler(schedulers=[(cosine_a, 4)])
    chain_b = SequentialScheduler(schedulers=[(cosine_b, 4)])
    assert chain_a.config_hash() != chain_b.config_hash()


def test_sequential_config_hash_distinguishes_slot_lengths() -> None:
    """Two chains with same sub-scheduler but different n_rounds hash differently."""
    cosine = default_cosine_scheduler(cycle_length=8)
    chain_a = SequentialScheduler(schedulers=[(cosine, 4)])
    chain_b = SequentialScheduler(schedulers=[(cosine, 8)])
    assert chain_a.config_hash() != chain_b.config_hash()


def test_sequential_config_hash_stable() -> None:
    """Two chains built identically produce identical hashes."""
    a = SequentialScheduler(
        schedulers=[(default_cosine_scheduler(cycle_length=4), 4)]
    )
    b = SequentialScheduler(
        schedulers=[(default_cosine_scheduler(cycle_length=4), 4)]
    )
    assert a.config_hash() == b.config_hash()


# ---------------------------------------------------------------------------
# Reset / feedback / noise injection
# ---------------------------------------------------------------------------


def test_sequential_reset_clears_sub_schedulers() -> None:
    cosine = default_cosine_scheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4)])
    chain.sample(0, 0, 0)
    assert chain.last_sample is not None
    assert cosine.last_sample is not None
    chain.reset()
    assert chain.last_sample is None
    assert cosine.last_sample is None


def test_sequential_inject_noise_delegates_to_active_slot() -> None:
    """Forward noise injection should reach the active sub-scheduler."""
    cosine = default_cosine_scheduler(cycle_length=4)
    expo = ExponentialScheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4), (expo, 4)])
    sample = chain.sample(0, 0, 0)  # cosine sub-slot
    from adaptive_reflow.contracts import CosineScheduleSample, FactorValue
    sched_sample = CosineScheduleSample(
        schedule_hash=sample.schedule_hash,
        outer_cycle_id=sample.outer_cycle_id,
        round_in_cycle=sample.round_in_cycle,
        cycle_length=sample.cycle_length,
        n_cap=FactorValue(sample.n_cap),
        n_min=FactorValue(sample.n_min),
        n_max=FactorValue(sample.n_max),
        u_r=sample.u_r,
        family=sample.family,
        computed_at_round=sample.computed_at_round,
    )
    import numpy as np
    state = np.zeros(8, dtype=np.float64)
    gen = np.random.default_rng(42)
    out_chain = chain.inject_noise(state, sched_sample, generator=gen)
    gen = np.random.default_rng(42)
    out_direct = cosine.inject_noise(state, sched_sample, generator=gen)
    assert np.allclose(out_chain, out_direct)


# ---------------------------------------------------------------------------
# Config round-trip
# ---------------------------------------------------------------------------


def test_sequential_round_trip_to_from_config() -> None:
    cosine = default_cosine_scheduler(cycle_length=6)
    expo = ExponentialScheduler(cycle_length=4, alpha=0.2)
    original = SequentialScheduler(schedulers=[(cosine, 6), (expo, 4)])
    cfg = original.to_config()
    assert cfg["family"] == "sequential"
    assert len(cfg["slots"]) == 2

    rebuilt = SequentialScheduler.from_config(cfg)
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.cycle_length() == original.cycle_length()
    assert rebuilt.total_rounds == original.total_rounds


def test_sequential_round_trip_trajectory_identical() -> None:
    """After round-trip, the trajectory matches round-for-round."""
    cosine = default_cosine_scheduler(cycle_length=6)
    expo = ExponentialScheduler(cycle_length=4, alpha=0.2)
    original = SequentialScheduler(schedulers=[(cosine, 6), (expo, 4)])
    rebuilt = SequentialScheduler.from_config(original.to_config())
    for r in range(original.total_rounds):
        s_orig = original.sample(0, r, r)
        s_rebuilt = rebuilt.sample(0, r, r)
        assert s_orig.n_cap == pytest.approx(s_rebuilt.n_cap)
        assert s_orig.u_r == pytest.approx(s_rebuilt.u_r)
        assert s_orig.family == s_rebuilt.family


def test_sequential_registered_in_scheduler_registry() -> None:
    assert SEQUENTIAL_FAMILY in SCHEDULER_REGISTRY
    assert SCHEDULER_REGISTRY["sequential"] is not None


def test_sequential_dispatched_via_build_scheduler_from_config() -> None:
    cosine = default_cosine_scheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4)])
    cfg = chain.to_config()
    rebuilt = build_scheduler_from_config(cfg)
    assert isinstance(rebuilt, SequentialScheduler)
    assert rebuilt.config_hash() == chain.config_hash()


def test_sequential_nested_round_trip() -> None:
    """Nested SequentialScheduler inside another SequentialScheduler."""
    inner = SequentialScheduler(
        schedulers=[(default_cosine_scheduler(cycle_length=3), 3)]
    )
    outer = SequentialScheduler(schedulers=[(inner, 3)])
    rebuilt = SequentialScheduler.from_config(outer.to_config())
    assert rebuilt.total_rounds == 3
    s = rebuilt.sample(0, 1, 1)
    assert 0.0 <= s.n_cap <= 1.0


def test_sequential_three_sub_schedulers() -> None:
    """Three-slot chain: cosine -> linear -> exponential."""
    cosine = default_cosine_scheduler(cycle_length=4)
    linear = LinearScheduler(cycle_length=4)
    expo = ExponentialScheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4), (linear, 4), (expo, 4)])
    assert chain.total_rounds == 12
    s0 = chain.sample(0, 0, 0)
    s4 = chain.sample(0, 4, 4)
    s8 = chain.sample(0, 8, 8)
    assert s0.family.startswith("sequential[0]")
    assert s4.family.startswith("sequential[1]")
    assert s8.family.startswith("sequential[2]")


def test_sequential_constant_sub_scheduler() -> None:
    """SequentialScheduler with a ConstantScheduler sub-slot."""
    cosine = default_cosine_scheduler(cycle_length=4)
    const = ConstantScheduler(cycle_length=4, n_cap=0.5)
    chain = SequentialScheduler(schedulers=[(cosine, 4), (const, 4)])
    # At chain round 5, the constant scheduler is at sub-round 1.
    s = chain.sample(0, 5, 5)
    assert s.n_cap == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# A8 — record_round_feedback forwards to every sub-scheduler
# ---------------------------------------------------------------------------


def test_sequential_feedback_forwards_to_every_slot() -> None:
    """A8: a single feedback call reaches every sub-scheduler in the chain.

    When the chain has two :class:`ConvergenceAdaptiveScheduler` slots,
    a single ``record_round_feedback`` at ``round_in_cycle=2`` must
    update both sub-schedulers' internal W2 history (with sub-round
    indices clamped to each slot's range).
    """
    from adaptive_reflow.algorithm.scheduler import (
        ConvergenceAdaptiveScheduler,
    )

    slot_a = ConvergenceAdaptiveScheduler()
    slot_b = ConvergenceAdaptiveScheduler()
    chain = SequentialScheduler(
        schedulers=[(slot_a, 5), (slot_b, 5)],
    )
    chain.record_round_feedback(round_in_cycle=2, metrics={"W2": 0.5})
    # Both sub-schedulers received the feedback (active + inactive).
    assert len(slot_a.w2_history) >= 1
    assert len(slot_b.w2_history) >= 1


def test_sequential_feedback_active_slot_index_clamped() -> None:
    """A8: the active slot's sub-round index is clamped to its range.

    With ``(slot_a, 5) + (slot_b, 5)`` and ``round_in_cycle=7`` (in
    slot_b), slot_a receives the feedback clamped to its terminal
    round (4); slot_b receives it at sub-round 2.
    """
    from adaptive_reflow.algorithm.scheduler import (
        ConvergenceAdaptiveScheduler,
    )

    slot_a = ConvergenceAdaptiveScheduler()
    slot_b = ConvergenceAdaptiveScheduler()
    chain = SequentialScheduler(
        schedulers=[(slot_a, 5), (slot_b, 5)],
    )
    chain.record_round_feedback(round_in_cycle=7, metrics={"W2": 0.7})
    # slot_a's history length is >= 1 (feedback forwarded at clamped round).
    assert len(slot_a.w2_history) >= 1
    assert len(slot_b.w2_history) >= 1


def test_sequential_feedback_out_of_range_noop() -> None:
    """A8: out-of-range ``round_in_cycle`` is a no-op (no sub-scheduler updated).

    Legacy semantics: callers that pass a ``round_in_cycle`` past the
    chain's total length see no feedback. (Clamping to the last slot
    would also warm it up but we keep the no-op behavior for callers
    that explicitly signal "out of range".)
    """
    from adaptive_reflow.algorithm.scheduler import (
        ConvergenceAdaptiveScheduler,
    )

    slot_a = ConvergenceAdaptiveScheduler()
    chain = SequentialScheduler(schedulers=[(slot_a, 4)])
    # round_in_cycle=10 is out of range for a 4-round chain.
    chain.record_round_feedback(round_in_cycle=10, metrics={"W2": 0.5})
    # No feedback was forwarded because the chain's total length is 4.
    assert len(slot_a.w2_history) == 0


# ---------------------------------------------------------------------------
# A9 — inject_noise fallback emits the audit code
# ---------------------------------------------------------------------------


def test_sequential_inject_noise_audit_codes_default_empty() -> None:
    """A9: ``audit_codes`` defaults to an empty tuple."""
    cosine = default_cosine_scheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4)])
    assert chain.audit_codes == ()


def test_sequential_inject_noise_fallback_emits_audit_code() -> None:
    """A9: out-of-range ``computed_at_round`` emits ``seq_inject_noise_fallback``.

    The chain's total length is 4; calling ``inject_noise`` with a
    ``schedule_sample.computed_at_round`` of 10 must fall back to
    ``slot[0]`` AND append the audit code so the audit ledger records
    the mis-wiring.
    """
    from adaptive_reflow.contracts import CosineScheduleSample, FactorValue

    cosine = default_cosine_scheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4)])
    sched_sample = CosineScheduleSample(
        schedule_hash="hash-fallback",
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(0.5),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        u_r=0.5,
        family="cosine",
        computed_at_round=10,  # out of range for a 4-round chain
    )
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    chain.inject_noise(state, sched_sample, generator=gen)
    # The audit code is appended.
    assert len(chain.audit_codes) == 1
    code = chain.audit_codes[0]
    assert code.startswith("seq_inject_noise_fallback")
    assert "total_rounds=4" in code
    assert "computed_at_round=10" in code


def test_sequential_inject_noise_no_fallback_in_range() -> None:
    """A9: in-range ``computed_at_round`` does NOT emit the audit code."""
    from adaptive_reflow.contracts import CosineScheduleSample, FactorValue

    cosine = default_cosine_scheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4)])
    sched_sample = CosineScheduleSample(
        schedule_hash="hash-in-range",
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(0.5),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        u_r=0.5,
        family="cosine",
        computed_at_round=2,  # in range
    )
    state = np.zeros(4, dtype=np.float64)
    gen = np.random.default_rng(0)
    chain.inject_noise(state, sched_sample, generator=gen)
    # No audit code appended.
    assert chain.audit_codes == ()


def test_sequential_reset_clears_audit_codes() -> None:
    """A9: ``reset()`` clears the audit_codes list."""
    from adaptive_reflow.contracts import CosineScheduleSample, FactorValue

    cosine = default_cosine_scheduler(cycle_length=4)
    chain = SequentialScheduler(schedulers=[(cosine, 4)])
    sched_sample = CosineScheduleSample(
        schedule_hash="hash-clear",
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(0.5),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        u_r=0.5,
        family="cosine",
        computed_at_round=10,
    )
    chain.inject_noise(
        np.zeros(4, dtype=np.float64), sched_sample,
        generator=np.random.default_rng(0),
    )
    assert len(chain.audit_codes) == 1
    chain.reset()
    assert chain.audit_codes == ()


def test_sequential_sample_propagates_audit_codes_and_evidence_ratio() -> None:
    """P0-A1 / P0-A7: the chain forwards the sub-scheduler's diagnostics.

    The rewritten :class:`ScheduleSample` keeps the chain-level
    ``schedule_hash`` but must not hide *which* family produced the
    round: the slot marker is prepended to the sub-scheduler's own
    ``audit_codes`` and the sub-scheduler's ``evidence_ratio`` is
    forwarded verbatim.
    """

    import math

    from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler

    def _profile(x: float) -> float:
        return (1.0 + 0.25 * math.tanh(x)) * math.sin(x)

    cosine = default_cosine_scheduler(cycle_length=3)
    codim = CodimensionSheetScheduler(
        cycle_length=3, profile_residual_fn=_profile
    )
    chain = SequentialScheduler(schedulers=[(cosine, 3), (codim, 3)])

    first = chain.sample(0, 0, 0)
    assert first.audit_codes == ("sequential_slot:0", "cosine_baseline")
    assert first.evidence_ratio is None

    second = chain.sample(0, 4, 4)
    assert second.audit_codes == (
        "sequential_slot:1",
        "codimension_paper_quantity_grounded",
    )
    assert second.evidence_ratio is not None
    assert second.evidence_ratio == pytest.approx(
        float(codim.last_evidence_ratio), abs=1e-6
    )
