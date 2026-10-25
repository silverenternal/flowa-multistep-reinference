"""GAP-84b — the round count follows the budget.

At total NFE = n_rounds the equal-budget allocator returns ``[1, 1, 1, 1]``
whatever the weights are (every round keeps at least one step). That is not a
restart, it is a stub of one: four one-step passes through re-noised states,
which is why the production frontier loses 27.7 % at NFE=4. These tests pin the
cap that fixes it and the default that keeps every older run byte-identical.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.wave191_p3_mnist_sweep import (  # noqa: E402
    effective_rounds,
    per_round_num_steps_equal_budget,
)


def test_default_is_the_legacy_round_count() -> None:
    for nfe in (1, 2, 4, 5, 10, 50, 200):
        assert effective_rounds(4, nfe, 1) == 4
    assert effective_rounds(3, 1, 1) == 3  # legacy nfe < n_rounds edge


def test_cap_keeps_every_round_usable() -> None:
    assert effective_rounds(4, 4, 2) == 2
    assert effective_rounds(4, 5, 2) == 2
    assert effective_rounds(4, 10, 2) == 4
    assert effective_rounds(4, 10, 3) == 3
    assert effective_rounds(4, 50, 3) == 4


def test_cap_degrades_to_the_single_pass_not_to_a_stub() -> None:
    # min_steps 4 at NFE 4 leaves exactly one round: the baseline itself.
    assert effective_rounds(4, 4, 4) == 1
    assert effective_rounds(4, 3, 4) == 1
    assert effective_rounds(4, 1, 4) == 1


def test_the_allocator_really_was_degenerate_at_nfe_eq_rounds() -> None:
    """The premise: with 4 rounds and 4 steps, every weight vector gives 1s."""
    for allocation in ("scheduler", "uniform"):
        got = per_round_num_steps_equal_budget(
            "cosine", 4, 4, allocation=allocation,
            interval_lengths=[1.0, 0.3, 0.3, 0.3],
        )
        assert got == [1, 1, 1, 1]
        assert sum(got) == 4


def test_two_steps_per_round_at_nfe_four_gives_two_two() -> None:
    r = effective_rounds(4, 4, 2)
    got = per_round_num_steps_equal_budget(
        "cosine", r, 4, allocation="scheduler",
        interval_lengths=[1.0, 0.3],
    )
    assert got == [2, 2]
    assert sum(got) == 4
