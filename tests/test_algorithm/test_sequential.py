"""Tests for :class:`adaptive_reflow.algorithm.sequential.SequentialScheduler` (P1-2)."""

from __future__ import annotations

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
