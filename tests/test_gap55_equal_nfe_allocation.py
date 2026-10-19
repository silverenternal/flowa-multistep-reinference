"""GAP-55 — R5c equal-total-NFE allocation.

The legacy R5c driver applies ``FRAMEWORK_MAX_NUM_STEPS`` as a *per-round
cap*, so the three framework arms run different totals (25 / 48 / 25) against
a 50-NFE baseline while the claim says "matched NFE=50". The new
``per_round_num_steps_equal_budget`` apportions exactly the baseline budget.

These tests pin both paths:
* the legacy path is unchanged (byte-stable for historical artifacts);
* the equal-budget path sums to the baseline budget for every arm.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.wave191_p3_mnist_sweep import (  # noqa: E402
    ARM_LABELS,
    BASELINE_NUM_STEPS,
    FRAMEWORK_MAX_NUM_STEPS,
    N_ROUNDS,
    per_round_num_steps,
    per_round_num_steps_equal_budget,
)


def test_legacy_allocation_is_unchanged() -> None:
    """The historical per-round-cap path must not move."""
    assert per_round_num_steps("cosine", N_ROUNDS, FRAMEWORK_MAX_NUM_STEPS) == [
        12, 9, 3, 1,
    ]
    assert per_round_num_steps(
        "codimension_sheet", N_ROUNDS, FRAMEWORK_MAX_NUM_STEPS,
    ) == [12, 12, 12, 12]
    assert per_round_num_steps(
        "evidence_driven", N_ROUNDS, FRAMEWORK_MAX_NUM_STEPS,
    ) == [12, 9, 3, 1]


def test_equal_budget_matches_the_baseline_total() -> None:
    for arm in ARM_LABELS:
        steps = per_round_num_steps_equal_budget(
            arm, N_ROUNDS, BASELINE_NUM_STEPS,
        )
        assert len(steps) == N_ROUNDS
        assert sum(steps) == BASELINE_NUM_STEPS, (arm, steps)
        assert all(s >= 1 for s in steps), (arm, steps)


def test_equal_budget_preserves_the_scheduler_ordering() -> None:
    """Cosine anneals down, so its early rounds must get more steps."""
    steps = per_round_num_steps_equal_budget("cosine", N_ROUNDS, BASELINE_NUM_STEPS)
    assert steps[0] > steps[1] > steps[2]
