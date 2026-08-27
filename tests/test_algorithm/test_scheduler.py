"""Tests for the abstract algorithm layer (SchedulerProtocol + cosine default)."""

from __future__ import annotations

import math
import warnings
from itertools import pairwise

import pytest

from adaptive_reflow.algorithm import (
    SCHEDULER_REGISTRY,
    ConstantScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    SchedulerProtocol,
    ScheduleSample,
    build_scheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.schedule.cosine import CosineScheduleSampler


def _legacy_sampler(config) -> CosineScheduleSampler:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return CosineScheduleSampler(config)


def test_scheduler_protocol_runtime_checkable() -> None:
    scheduler = default_cosine_scheduler()
    assert isinstance(scheduler, SchedulerProtocol)
    assert isinstance(scheduler, CosineAnnealScheduler)


def test_cosine_anneal_scheduler_matches_legacy() -> None:
    scheduler = default_cosine_scheduler(cycle_length=8, n_min=0.1, n_max=0.9)
    legacy = _legacy_sampler(scheduler.config)
    for r in range(8):
        new = scheduler.sample(0, r, r)
        old = legacy.sample(0, r, r)
        assert new.n_cap == pytest.approx(float(old.n_cap))
        assert new.u_r == pytest.approx(old.u_r)
        assert new.family == old.family
        assert new.cycle_length == old.cycle_length
        assert new.memory_fraction() == pytest.approx(1.0 - float(old.n_cap))


def test_scheduler_sample_is_pure() -> None:
    scheduler = default_cosine_scheduler(cycle_length=5)
    a = scheduler.sample(2, 3, 7)
    b = scheduler.sample(2, 3, 7)
    assert a == b
    assert isinstance(a, ScheduleSample)


def test_scheduler_config_hash_is_stable() -> None:
    a = default_cosine_scheduler(cycle_length=12, n_min=0.2, n_max=0.8)
    b = default_cosine_scheduler(cycle_length=12, n_min=0.2, n_max=0.8)
    assert a.config_hash() == b.config_hash()
    a.sample(0, 1, 1)
    assert a.config_hash() == b.config_hash()
    c = default_cosine_scheduler(cycle_length=13, n_min=0.2, n_max=0.8)
    assert c.config_hash() != a.config_hash()


def test_scheduler_reset_clears_state() -> None:
    scheduler = default_cosine_scheduler(cycle_length=4)
    assert scheduler.last_sample is None
    scheduler.sample(0, 1, 1)
    assert scheduler.last_sample is not None
    scheduler.reset()
    assert scheduler.last_sample is None


def test_scheduler_accessors() -> None:
    scheduler = default_cosine_scheduler(cycle_length=6)
    assert scheduler.cycle_length() == 6
    assert scheduler.schedule_family() == "cosine_no_restart"


def test_legacy_sampler_emits_deprecation_warning() -> None:
    config = default_cosine_scheduler().config
    with pytest.warns(DeprecationWarning):
        CosineScheduleSampler(config)


# ---------------------------------------------------------------------------
# ConstantScheduler
# ---------------------------------------------------------------------------


def test_constant_scheduler_n_cap_is_constant() -> None:
    """ConstantScheduler must emit the same n_cap for every round."""
    scheduler = ConstantScheduler(cycle_length=10, n_cap=0.5)
    samples = [scheduler.sample(0, r, r) for r in range(10)]
    n_caps = {s.n_cap for s in samples}
    assert n_caps == {0.5}
    assert scheduler.schedule_family() == "constant"
    assert scheduler.cycle_length() == 10
    assert all(s.family == "constant" for s in samples)
    assert all(s.u_r == 0.5 for s in samples)


# ---------------------------------------------------------------------------
# LinearScheduler
# ---------------------------------------------------------------------------


def test_linear_scheduler_n_cap_ramps_monotonically() -> None:
    """LinearScheduler must produce a monotonic (decreasing) ramp n_min -> n_max."""
    scheduler = LinearScheduler(cycle_length=10, n_min=0.0, n_max=1.0)
    samples = [scheduler.sample(0, r, r) for r in range(10)]
    n_caps = [s.n_cap for s in samples]
    # Closed form n_max - (n_max - n_min) * u_r with n_max > n_min
    # produces a strictly decreasing sequence.
    for prev, curr in pairwise(n_caps):
        assert curr < prev
    assert n_caps[0] == pytest.approx(1.0)  # round 0 -> n_max
    assert n_caps[-1] == pytest.approx(0.0)  # round L-1 -> n_min
    assert scheduler.schedule_family() == "linear"


# ---------------------------------------------------------------------------
# ExponentialScheduler
# ---------------------------------------------------------------------------


def test_exponential_scheduler_n_cap_decays() -> None:
    """ExponentialScheduler must produce a strictly non-increasing n_cap sequence."""
    scheduler = ExponentialScheduler(cycle_length=10, n_max=1.0, alpha=0.2)
    samples = [scheduler.sample(0, r, r) for r in range(10)]
    n_caps = [s.n_cap for s in samples]
    # Strictly decreasing for alpha > 0.
    for prev, curr in pairwise(n_caps):
        assert curr < prev
    # Closed form check at round 1: n_max * exp(-alpha * 1).
    assert n_caps[1] == pytest.approx(math.exp(-0.2))
    assert scheduler.schedule_family() == "exponential"


# ---------------------------------------------------------------------------
# Registry + factory
# ---------------------------------------------------------------------------


def test_build_scheduler_factory_dispatches_by_family() -> None:
    """build_scheduler must return the right class for each registered family."""
    assert isinstance(build_scheduler("cosine"), CosineAnnealScheduler)
    assert isinstance(build_scheduler("constant"), ConstantScheduler)
    assert isinstance(build_scheduler("linear"), LinearScheduler)
    assert isinstance(build_scheduler("exponential"), ExponentialScheduler)
    # Whitespace + case tolerance.
    assert isinstance(build_scheduler("  COSINE  "), CosineAnnealScheduler)
    # Unknown family -> KeyError.
    with pytest.raises(KeyError):
        build_scheduler("not_a_family")


# ---------------------------------------------------------------------------
# Protocol conformance for every registered scheduler
# ---------------------------------------------------------------------------


def test_all_schedulers_conform_to_protocol() -> None:
    """Every registered scheduler class must satisfy SchedulerProtocol structurally."""
    assert set(SCHEDULER_REGISTRY) == {
        "cosine",
        "constant",
        "linear",
        "exponential",
    }
    instances: list[SchedulerProtocol] = [
        default_cosine_scheduler(cycle_length=5),
        ConstantScheduler(cycle_length=5),
        LinearScheduler(cycle_length=5),
        ExponentialScheduler(cycle_length=5),
    ]
    for instance in instances:
        assert isinstance(instance, SchedulerProtocol)
        # Every Protocol method must be callable and return the right shape.
        sample = instance.sample(0, 0, 0)
        assert isinstance(sample, ScheduleSample)
        assert isinstance(instance.cycle_length(), int)
        assert isinstance(instance.schedule_family(), str)
        assert isinstance(instance.config_hash(), str)
        instance.reset()
