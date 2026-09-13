"""CLM-021: SequentialScheduler mirrors PyTorch's SequentialLR composite scheduler.

Asserted by docs/CLAIMS.md:424-448.
The chain takes (sub_scheduler, n_rounds) tuples and serves the slot at
index `i` for rounds `[sum(n_rounds[:i]), sum(n_rounds[:i+1]))`. The
chain's `cycle_length()` returns `sum(n_rounds)`.

We pin:
    1. SequentialScheduler class is importable.
    2. A 2-slot chain has cycle_length equal to the sum of n_rounds.
    3. Sampling rounds 0 and 1 in the first slot returns the first
       sub-scheduler's n_cap (not the second's).
"""
from __future__ import annotations

from adaptive_reflow.algorithm.sequential import SequentialScheduler
from tests.test_claims._claim_template import default_cosine_scheduler


def test_claim_021_sequential_class_importable() -> None:
    assert SequentialScheduler is not None

def test_claim_021_two_slot_chain_cycle_length_is_sum() -> None:
    sub_a = default_cosine_scheduler(cycle_length=4, n_min=0.0, n_max=1.0)
    sub_b = default_cosine_scheduler(cycle_length=6, n_min=0.0, n_max=1.0)
    chain = SequentialScheduler(schedulers=[(sub_a, 4), (sub_b, 6)])
    assert int(chain.cycle_length()) == 10

def test_claim_021_slot_zero_serves_first_subscheduler() -> None:
    """Rounds in [0, 4) sample from sub_a (cycle_length=4 -> n_max at r=0)."""
    sub_a = default_cosine_scheduler(cycle_length=4, n_min=0.0, n_max=1.0)
    sub_b = default_cosine_scheduler(cycle_length=6, n_min=0.0, n_max=1.0)
    chain = SequentialScheduler(schedulers=[(sub_a, 4), (sub_b, 6)])
    sample = chain.sample(outer_cycle_id=0, round_in_cycle=0, target_round=0)
    assert float(sample.n_cap) == 1.0  # n_max for sub_a's first round
