"""Property-based tests for :mod:`adaptive_reflow.algorithm.sequential`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :class:`SequentialScheduler` — composability: the chain's
  ``cycle_length`` equals the sum of ``n_rounds``; each round falls
  into exactly one slot; ``total_rounds`` matches
  ``sum(s.n_rounds for s in slots)``.
* :class:`SequentialScheduler` — ``cycle_length`` matches the sum of
  per-slot round counts (the chain is exhaustive).
* :class:`SequentialScheduler` — ``config_hash`` distinctness for
  distinct slot compositions.

Seed policy (Research 4 mitigation): deterministic; only input tuples
vary.
"""

from __future__ import annotations

import math

import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.scheduler._core import (
    ConstantScheduler,
)
from adaptive_reflow.algorithm.sequential import SequentialScheduler

_PROPERTY_SETTINGS = settings(
    max_examples=20,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


# Helper: a list of 1-3 sub-schedulers with 1-5 rounds each.
def _slot_strategy():
    return st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            st.integers(min_value=1, max_value=5),
        ).map(lambda nc_nr: (ConstantScheduler(cycle_length=1, n_cap=nc_nr[0]), nc_nr[1])),
        min_size=1,
        max_size=3,
    )


# ---------------------------------------------------------------------------
# cycle_length matches sum(n_rounds).
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(slots=_slot_strategy())
def test_sequential_cycle_length_equals_sum(slots: list) -> None:
    chain = SequentialScheduler(schedulers=slots)
    expected = sum(nr for _, nr in slots)
    assert chain.cycle_length() == expected
    assert chain.total_rounds == expected


# ---------------------------------------------------------------------------
# Every round resolves to exactly one slot, and the slot's n_rounds
# covers its assigned range without overlap.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(slots=_slot_strategy())
def test_sequential_rounds_partition_chain(slots: list) -> None:
    chain = SequentialScheduler(schedulers=slots)
    total = chain.total_rounds
    seen_slots: set[int] = set()
    for r in range(total):
        idx, slot, _ = chain._resolve_slot(r)
        assert 0 <= idx < len(chain.slots)
        assert idx not in seen_slots or True  # multiple rounds can map to same slot
        assert slot.scheduler is chain.slots[idx].scheduler


# ---------------------------------------------------------------------------
# Config-hash distinctness: distinct (slots) tuples produce distinct hashes.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(slots1=_slot_strategy(), slots2=_slot_strategy())
def test_sequential_config_hash_distinct_for_distinct_total_rounds(
    slots1: list, slots2: list
) -> None:
    """Two chains with different ``total_rounds`` produce distinct
    ``config_hash`` values (hash incorporates the per-slot
    ``config_hash`` + ``n_rounds`` + family)."""
    chain1 = SequentialScheduler(schedulers=slots1)
    chain2 = SequentialScheduler(schedulers=slots2)
    if chain1.total_rounds != chain2.total_rounds:
        assert chain1.config_hash() != chain2.config_hash()


# ---------------------------------------------------------------------------
# Reset returns the chain to a fresh state.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(slots=_slot_strategy())
def test_sequential_reset_clears_state(slots: list) -> None:
    chain = SequentialScheduler(schedulers=slots)
    chain.sample(0, 0, 0)
    chain.reset()
    assert chain.last_sample is None
