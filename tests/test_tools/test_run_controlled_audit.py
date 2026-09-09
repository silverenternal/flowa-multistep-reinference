"""Tests for ``tools.run_controlled_audit``.

Wave 95 Phase 1.B (E2): the audit tool's default NFE allocation was
flipped from ``"uniform"`` to ``"evidence"`` (inverse-to-eps) so the
framework arm of every grid cell reaches the theoretical bound at low
NFE without the user having to pass ``--nfe-allocation evidence``.

These tests pin:

* :data:`tools.run_controlled_audit.NFE_ALLOCATION` defaults to
  ``"evidence"`` (Wave 95 flip).
* :func:`_nfe_steps_per_round` with the new default allocates steps
  *inversely* to the codimension scheduler's per-round ``eps`` -- later
  refinement rounds get more steps than early high-noise rounds.
* The matched-NFE invariant (sum equals ``nfe`` exactly, every round
  ``>= 1``) is preserved.
* The legacy ``"uniform"`` path is still reachable via module-global
  flip (Wave 35 FIX-3 opt-in).
"""
from __future__ import annotations

import pytest

import tools.run_controlled_audit as audit


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT_AUDIT_TOOL = "tools/run_controlled_audit.py"


def test_nfe_allocation_default_is_evidence_w95() -> None:
    """Wave 95 E2: default allocation is ``"evidence"`` (inverse-to-eps).

    Line 101 of ``tools/run_controlled_audit.py`` declares the module
    global; this test pins the flip so a future regression to
    ``"uniform"`` fails loudly.
    """
    assert audit.NFE_ALLOCATION == "evidence"


def test_nfe_steps_evidence_default_allocates_inversely_to_eps() -> None:
    """Default evidence mode gives *more* steps to later rounds.

    The codimension scheduler's ``eps_per_round`` is a strictly
    decreasing sequence (small-eps refinement rounds come last), so
    inverse-to-eps allocation must produce a *non-decreasing* step
    vector: the small-eps refinement rounds absorb a larger share.

    The test pins both the matched-NFE invariant (sum equals ``nfe``
    exactly, every round ``>= 1``) and the monotone non-decreasing
    shape that distinguishes evidence mode from uniform mode.
    """
    nfe = 275
    n_rounds = 5

    steps = audit._nfe_steps_per_round(nfe, n_rounds)

    # Matched-NFE invariant.
    assert sum(steps) == nfe
    assert len(steps) == n_rounds
    assert all(s >= 1 for s in steps)

    # Inverse-to-eps -> non-decreasing (later rounds get more steps).
    assert steps == sorted(steps), (
        f"evidence mode must allocate non-decreasingly, got {steps}"
    )

    # Strictly different from the uniform split of the same budget.
    assert steps != [nfe // n_rounds] * n_rounds


def test_evidence_mode_smaller_budgets_inversely_to_eps() -> None:
    """Same invariant at the canonical 50-NFE / 4-round budget.

    Repeats the inverse-to-eps check at a smaller budget so the test
    is sensitive to allocation regressions on the Wave 17 50-NFE cell.
    """
    steps = audit._nfe_steps_per_round(50, 4)
    assert sum(steps) == 50
    assert len(steps) == 4
    assert all(s >= 1 for s in steps)
    # Non-decreasing in evidence mode.
    assert steps == sorted(steps)
    # Differs from uniform [13, 13, 12, 12].
    assert steps != [13, 13, 12, 12]


def test_uniform_mode_still_reachable_via_module_global(monkeypatch) -> None:
    """Wave 35 FIX-3 opt-in path: ``NFE_ALLOCATION = "uniform"`` still works.

    The flip in E2 changes the *default*; the legacy equal-split is
    preserved as a module-global override so previously published grid
    cells can be re-evaluated byte-for-byte.
    """
    monkeypatch.setattr(audit, "NFE_ALLOCATION", "uniform")
    assert audit._nfe_steps_per_round(275, 5) == [55] * 5
    assert audit._nfe_steps_per_round(50, 4) == [13, 13, 12, 12]
    assert audit._nfe_steps_per_round(11, 4) == [3, 3, 3, 2]


@pytest.mark.parametrize(
    "nfe,n_rounds",
    [(50, 4), (200, 4), (10, 5), (275, 5), (1000, 5)],
)
def test_evidence_mode_matched_nfe_invariant(nfe: int, n_rounds: int) -> None:
    """Matched-NFE invariant holds across the canonical budget grid."""
    steps = audit._nfe_steps_per_round(nfe, n_rounds)
    assert sum(steps) == nfe
    assert len(steps) == n_rounds
    assert all(s >= 1 for s in steps)
    # Evidence mode is non-decreasing.
    assert steps == sorted(steps)


# ---------------------------------------------------------------------------
# Wave 95 Phase 1.C (E3): LineageFlow framework-shape
# ---------------------------------------------------------------------------


def test_lineageflow_arm_uses_batched_runner_shape() -> None:
    """Wave 95 E3: LineageFlow framework arm is framework-shaped.

    The LineageFlow arm (line 432 of ``tools/run_controlled_audit.py``)
    does NOT advertise :class:`generate_trajectory` so it cannot drive
    the :class:`BatchedTrajectoryRunner` runner directly. The audit
    arm is therefore framework-shaped via three framework primitives:

    1. :class:`BatchedRunnerConfig` with ``early_termination=True`` and
       a ``BoundedMergeOperator`` wired into the merge slot.
    2. :func:`adaptive_reflow.algorithm.nfe_allocation.nfe_steps_for_evidence`
       (inverse-to-eps, Wave 35 FIX-3) for the per-round NFE
       allocation; the matched-NFE invariant holds.
    3. The per-round loop honours ``scheduler.should_terminate_round``
       when present.

    This test pins all three primitives so a future regression that
    drops the framework-shape (e.g. silently regresses to uniform
    allocation or removes early termination) fails loudly.
    """
    import inspect

    from adaptive_reflow.algorithm.batched_runner import BatchedRunnerConfig
    from adaptive_reflow.algorithm.merge_operator import (
        BoundedMergeOperator,
    )
    from adaptive_reflow.algorithm.nfe_allocation import (
        nfe_steps_for_evidence,
    )
    from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler

    # Pin (1): the LineageFlow arm constructs a BatchedRunnerConfig.
    src = inspect.getsource(audit._run_lineageflow)
    assert "BatchedRunnerConfig" in src, (
        "LineageFlow arm must construct BatchedRunnerConfig for "
        "framework-shape witness"
    )
    assert "early_termination=True" in src, (
        "LineageFlow arm must set BatchedRunnerConfig.early_termination=True"
    )
    assert "BoundedMergeOperator" in src or "default_bounded_merge_operator" in src, (
        "LineageFlow arm must thread a BoundedMergeOperator into the "
        "BatchedRunnerConfig merge slot"
    )

    # Pin (2): the per-round NFE allocation uses evidence mode.
    assert "nfe_steps_for_evidence" in src, (
        "LineageFlow arm must use nfe_steps_for_evidence for "
        "framework-shaped NFE allocation"
    )
    # Pin the matched-NFE invariant via the same helper the arm uses.
    scheduler = CodimensionSheetScheduler(cycle_length=5)
    eps_per_round = [
        float(scheduler.sample(0, r, r).eps_implicit) for r in range(5)
    ]
    steps = nfe_steps_for_evidence(50, eps_per_round)
    assert sum(steps) == 50
    assert len(steps) == 5
    assert all(s >= 1 for s in steps)
    assert steps == sorted(steps), (
        f"evidence mode must be non-decreasing, got {steps}"
    )

    # Pin (3): the per-round loop honours early termination.
    assert "should_terminate_round" in src, (
        "LineageFlow arm must check scheduler.should_terminate_round "
        "for framework-shape early termination"
    )

    # Pin the BoundedRunnerConfig / BoundedMergeOperator constructors
    # work as expected so a future dataclass drift fails loudly here
    # rather than at audit-run time.
    config = BatchedRunnerConfig(
        cycle_length=5,
        trajectories_per_round=8,
        endpoints_per_trajectory=1,
        scheduler=scheduler,
        merge_operator=BoundedMergeOperator(),
        seed=42,
        early_termination=True,
    )
    assert config.early_termination is True
    assert isinstance(config.merge_operator, BoundedMergeOperator)
    assert config.scheduler is scheduler
