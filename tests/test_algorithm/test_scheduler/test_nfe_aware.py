"""NFEAwareMemoryScheduler tests (Wave 61 Agent 2 — Wave 57 Agent D's B2).

Split out of the monolithic ``tests/test_algorithm/test_scheduler.py``
during Wave 104 P2-B. Pure file-system refactor — no behaviour change.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from adaptive_reflow.algorithm import (
    SCHEDULER_REGISTRY,
    NFEAwareMemoryScheduler,
    SchedulerProtocol,
    ScheduleSample,
    build_scheduler,
    build_scheduler_from_config,
)


def test_nfe_aware_scheduler_memory_fraction_at_canonical_strata() -> None:
    """At the Wave 57 grid (``n_rounds=3``) the ``memory_fraction`` matches
    the formula at every relevant NFE.

    * NFE=10 → ``nfe_per_round = 10/3 ≈ 3.33`` → ``m ≈ 0.5 * (0.333)² ≈ 0.056``.
    * NFE=50 → ``nfe_per_round ≈ 16.67`` → ``m = 0.5`` (saturated).
    * NFE=200 → ``nfe_per_round ≈ 66.67`` → ``m = 0.5`` (saturated).
    * NFE=500 → ``nfe_per_round ≈ 166.67`` → ``m = 0.5`` (saturated).
    """
    # NFE=10 (low NFE, no perturbation).
    s10 = NFEAwareMemoryScheduler(cycle_length=10, nfe_budget=10, n_rounds=3)
    expected_m10 = 0.5 * (10.0 / 3.0 / 10.0) ** 2
    assert s10.memory_fraction == pytest.approx(expected_m10, rel=1e-9)
    assert s10.memory_fraction < 0.1  # essentially no perturbation
    assert s10.n_cap == pytest.approx(1.0 - expected_m10)

    # NFE=50 (saturated regime).
    s50 = NFEAwareMemoryScheduler(cycle_length=10, nfe_budget=50, n_rounds=3)
    assert s50.memory_fraction == pytest.approx(0.5)
    assert s50.n_cap == pytest.approx(0.5)

    # NFE=200 (saturated).
    s200 = NFEAwareMemoryScheduler(cycle_length=10, nfe_budget=200, n_rounds=3)
    assert s200.memory_fraction == pytest.approx(0.5)
    assert s200.n_cap == pytest.approx(0.5)

    # NFE=500 (saturated).
    s500 = NFEAwareMemoryScheduler(cycle_length=10, nfe_budget=500, n_rounds=3)
    assert s500.memory_fraction == pytest.approx(0.5)


def test_nfe_aware_scheduler_constant_across_rounds() -> None:
    """``memory_fraction`` is the same for every round (the family is
    *constant* by design — only the ``nfe_budget`` parameter varies,
    not ``r``).
    """
    s = NFEAwareMemoryScheduler(cycle_length=12, nfe_budget=80, n_rounds=4)
    n_caps = [s.sample(0, r, r).n_cap for r in range(12)]
    assert n_caps[0] == pytest.approx(n_caps[5])
    assert n_caps[0] == pytest.approx(n_caps[11])
    # And equal to the constructor's cached value.
    assert n_caps[0] == pytest.approx(s.n_cap)


def test_nfe_aware_scheduler_conforms_to_protocol() -> None:
    """``NFEAwareMemoryScheduler`` satisfies ``SchedulerProtocol``."""
    s = NFEAwareMemoryScheduler(cycle_length=8, nfe_budget=50, n_rounds=3)
    assert isinstance(s, SchedulerProtocol)
    # Required methods / attributes.
    sample = s.sample(0, 0, 0)
    assert isinstance(sample, ScheduleSample)
    assert s.cycle_length() == 8
    assert s.schedule_family() == "nfe_aware_memory"
    assert isinstance(s.config_hash(), str)
    # to_config / from_config + reset + record_round_feedback + inject_noise
    cfg = s.to_config()
    assert cfg["family"] == "nfe_aware_memory"
    s2 = NFEAwareMemoryScheduler.from_config(cfg)
    assert s2.config_hash() == s.config_hash()
    s.reset()
    assert s.last_sample is None
    # record_round_feedback is a no-op (the family is non-adaptive).
    s.record_round_feedback(0, {"W2": 1.0})
    # inject_noise returns a fresh state of the same shape (P0-7).
    rng = np.random.default_rng(0)
    state = np.zeros((4, 4), dtype=np.float64)
    out = s.inject_noise(state, sample, generator=rng)
    assert out.shape == state.shape
    assert not np.shares_memory(out, state)


def test_nfe_aware_scheduler_config_round_trip_byte_stable() -> None:
    """``to_config`` / ``from_config`` round-trip is byte-stable."""
    s = NFEAwareMemoryScheduler(
        cycle_length=12,
        nfe_budget=100,
        n_rounds=5,
        threshold=15,
        max_memory_fraction=0.4,
        seed=42,
    )
    cfg = s.to_config()
    s2 = NFEAwareMemoryScheduler.from_config(cfg)
    # Same hash + same memory_fraction.
    assert s2.config_hash() == s.config_hash()
    assert s2.memory_fraction == s.memory_fraction
    assert s2.n_cap == s.n_cap
    # Same sample, byte-for-byte.
    sample_a = s.sample(0, 3, 3)
    sample_b = s2.sample(0, 3, 3)
    assert sample_a == sample_b


def test_nfe_aware_scheduler_audit_codes_tag_family() -> None:
    """Every sample carries the NFE-aware audit codes so the runner / engine
    can branch on the family without re-reading the scheduler.
    """
    s = NFEAwareMemoryScheduler(cycle_length=5, nfe_budget=50, n_rounds=3)
    sample = s.sample(0, 2, 2)
    assert "schedule_nfe_aware_memory" in sample.audit_codes
    # The constant-``m`` and per-round-NFE audit markers must be present.
    joined = "|".join(sample.audit_codes)
    assert "m=" in joined
    assert "nfe_per_round=" in joined
    assert sample.family == "nfe_aware_memory"


def test_nfe_aware_scheduler_threshold_zero_saturates() -> None:
    """``threshold=0`` is rejected because it would divide by zero.

    The closed form ``m = M * (NFE_per_round / threshold) ** 2`` cannot
    be evaluated at ``threshold = 0``. The constructor rejects it
    with a clear ``ValueError`` so a misconfigured caller surfaces
    the bug rather than producing NaN at sample time.
    """
    with pytest.raises(ValueError):
        NFEAwareMemoryScheduler(cycle_length=10, threshold=0)


def test_nfe_aware_scheduler_max_memory_fraction_bounds() -> None:
    """``max_memory_fraction`` must lie in ``[0, 1]``."""
    with pytest.raises(ValueError):
        NFEAwareMemoryScheduler(cycle_length=10, max_memory_fraction=-0.1)
    with pytest.raises(ValueError):
        NFEAwareMemoryScheduler(cycle_length=10, max_memory_fraction=1.5)


def test_nfe_aware_scheduler_nfe_budget_must_be_positive() -> None:
    """``nfe_budget`` and ``n_rounds`` must be ``>= 1``."""
    with pytest.raises(ValueError):
        NFEAwareMemoryScheduler(cycle_length=10, nfe_budget=0)
    with pytest.raises(ValueError):
        NFEAwareMemoryScheduler(cycle_length=10, n_rounds=0)


def test_nfe_aware_scheduler_registered_in_registry() -> None:
    """``nfe_aware_memory`` is registered in ``SCHEDULER_REGISTRY`` and
    reachable via ``build_scheduler`` / ``build_scheduler_from_config``.
    """
    assert "nfe_aware_memory" in SCHEDULER_REGISTRY
    s = build_scheduler(
        "nfe_aware_memory",
        cycle_length=10,
        nfe_budget=50,
        n_rounds=3,
    )
    assert isinstance(s, NFEAwareMemoryScheduler)
    assert s.schedule_family() == "nfe_aware_memory"

    cfg = s.to_config()
    s2 = build_scheduler_from_config(cfg)
    assert isinstance(s2, NFEAwareMemoryScheduler)
    assert s2.config_hash() == s.config_hash()


def test_nfe_aware_scheduler_inject_noise_is_deterministic() -> None:
    """P0-7: ``inject_noise`` is reproducible given the same ``generator``
    state. The new scheduler uses ``sqrt(n_cap)`` as the noise mass, so
    two calls with the same generator produce identical output.
    """
    s = NFEAwareMemoryScheduler(cycle_length=4, nfe_budget=50, n_rounds=3)
    sample = s.sample(0, 0, 0)
    state = np.zeros((3, 3), dtype=np.float64)
    rng_a = np.random.default_rng(42)
    rng_b = np.random.default_rng(42)
    out_a = s.inject_noise(state, sample, generator=rng_a)
    out_b = s.inject_noise(state, sample, generator=rng_b)
    np.testing.assert_array_equal(out_a, out_b)


def test_nfe_aware_scheduler_u_r_progress_monotonic() -> None:
    """``u_r`` still progresses linearly across rounds (the
    ``memory_fraction`` is constant, but ``u_r`` is round-derived for
    downstream consumers).
    """
    s = NFEAwareMemoryScheduler(cycle_length=11, nfe_budget=50, n_rounds=3)
    u_rs = [s.sample(0, r, r).u_r for r in range(11)]
    for prev, curr in pairwise(u_rs):
        assert curr > prev
    assert u_rs[0] == pytest.approx(0.0)
    assert u_rs[-1] == pytest.approx(1.0)
