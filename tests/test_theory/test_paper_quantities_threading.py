"""Wave 38 paper_quantities threading — regression tests (HIGH-1 + MEDIUM-6 + MEDIUM-8).

Per ``todo/algo-improvement-paper-quantities-threading.md`` (Wave 32 audit
gap): the ``paper_quantities`` payload produced by paper-aware
adapters / evaluators was being silently dropped at three sites in the
adaptive re-inference control loop:

* ``CodimensionSheetScheduler.record_round_feedback`` (HIGH-1) — the
  codimension scheduler never consumed the per-round paper-quantity
  dict, so the runner's ``scheduler.record_round_feedback(r,
  metrics, paper_quantities=...)`` call left the scheduler blind to
  sheet-vs-cell evidence (paper Lemma 2 / Lemma 3).
* ``SequentialScheduler.record_round_feedback`` (MEDIUM-6) — the chain
  forwarded ``metrics`` to every slot but dropped the new
  ``paper_quantities`` kwarg, so a ``PaperRatioAdaptiveScheduler`` in
  slot[1] saw a metrics-only payload.
* ``BatchedTrajectoryRunner.run`` (MEDIUM-8) — the runner is the
  single chokepoint for ``record_round_feedback`` and only forwarded
  ``{"W2": float(w2)}``, dropping the paper-quantity carrier even when
  the runner config carried a paper-quantity producer.

These three tests pin the Wave 38 fixes (the same class of bug
surfaced by F-1 / F-4 / F-5 in Wave 30, but for the
``paper_quantities`` protocol surface). Each test:

1. Constructs the smallest fixture that exercises the threading path.
2. Invokes the fixed surface with a non-``None`` ``paper_quantities``
   payload.
3. Asserts the carrier has been consumed (scheduler history grows,
   sub-scheduler PID shifts, runner forwards).

The tests are **byte-deterministic**: every input is a hand-picked
literal, no RNG, no network, no I/O. They belong in
``tests/test_theory/`` per the Wave 38 disjoint-scope convention
(the algorithm layer lives in ``adaptive_reflow/algorithm/``; the
regression coverage for *protocol-surface* fixes that depend on the
theory module's paper quantities lives in the theory test directory
so the wiring is audited from the theory package's perspective).
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import pytest

# Pre-warm the module graph so the partial-init circular import
# (``adaptive_reflow.framework`` ↔ ``adaptive_reflow.theory.checkers``)
# is resolved before our test bodies touch the scheduler subpackage.
# Importing these adapters (used in
# ``tests/test_algorithm/test_wave35_saturation_fixes.py``) resolves
# the cycle deterministically; without them, ``tests/test_theory/``
# collection alone triggers the partial-init failure.
import adaptive_reflow.adapters.twodim_fm  # noqa: F401 -- pre-warm module graph


def _paper_quantities_a(r: int) -> Mapping[str, float]:
    """Build a paper-quantities dict that drives the PID in a known direction.

    Returns a dict with strictly *increasing* ``sheet_A`` so two
    sequential feedback calls produce a non-zero shift on the
    :class:`PaperRatioAdaptiveScheduler`'s PID controller (which
    needs at least two samples before it moves ``_shift``).
    """
    return {"sheet_A": 0.30 + 0.01 * r, "cell_C": 0.20, "packing_B": 0.50}


# ---------------------------------------------------------------------------
# HIGH-1 — CodimensionSheetScheduler.record_round_feedback consumes
#          paper_quantities and grows `_shift_history`.
# ---------------------------------------------------------------------------


def test_codimension_scheduler_consumes_paper_quantities() -> None:
    """HIGH-1 fix: ``paper_quantities`` kwarg is consumed; ``_shift_history`` grows.

    Smallest possible fixture — a codimension scheduler with the
    canonical ``profile_residual_fn`` wired so the four paper
    quantities are cached at construction time, then a single
    ``record_round_feedback`` call carrying the sheet-vs-cell
    components. The ``_shift_history`` MUST grow by exactly one entry
    (one ratio per call) and the ratio MUST equal
    ``sheet_A / (cell_C * packing_B)`` to within ``1e-12``.
    """
    from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler

    scheduler = CodimensionSheetScheduler(
        profile_residual_fn=math.sin, cycle_length=5
    )
    assert scheduler._shift_history == []
    scheduler.record_round_feedback(
        0,
        {"W2": 1.0},
        paper_quantities={"sheet_A": 0.5, "cell_C": 0.3, "packing_B": 0.4},
    )
    assert len(scheduler._shift_history) == 1
    expected_ratio = 0.5 / (0.3 * 0.4)
    assert math.isclose(
        scheduler._shift_history[0], expected_ratio, rel_tol=1e-12
    )
    # The public property exposes the same value.
    assert scheduler.shift_history == (pytest.approx(expected_ratio),)


def test_codimension_scheduler_legacy_metrics_only_no_shift_history_growth() -> None:
    """HIGH-1 backward-compat: a metrics-only call does NOT touch ``_shift_history``.

    Callers that do not wire a ``paper_quantities`` payload (the legacy
    Wave 35 path) MUST continue to see ``_shift_history == ()`` so the
    pinned D.4 regression vectors stay valid.
    """
    from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler

    scheduler = CodimensionSheetScheduler(cycle_length=5)
    scheduler.record_round_feedback(0, {"W2": 0.5})
    scheduler.record_round_feedback(1, {"W2": 0.4})
    assert scheduler._shift_history == []


def test_codimension_scheduler_skips_incomplete_paper_quantities() -> None:
    """HIGH-1 robustness: missing / non-finite paper-quantity keys are skipped.

    A broken oracle that supplies ``sheet_A`` but forgets ``cell_C`` or
    ``packing_B`` MUST NOT corrupt ``_shift_history`` (the same
    missing-value tolerance the codimension scheduler already applies
    to ``_w2_history`` and ``_evidence_ratio_history``). Non-finite
    values (NaN / inf) and non-numeric types are likewise ignored.
    """
    from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler

    scheduler = CodimensionSheetScheduler(cycle_length=5)

    # Missing keys
    scheduler.record_round_feedback(
        0, {"W2": 0.5}, paper_quantities={"sheet_A": 0.5}
    )
    assert scheduler._shift_history == []

    # Non-finite sheet_A
    scheduler.record_round_feedback(
        0,
        {"W2": 0.5},
        paper_quantities={
            "sheet_A": float("nan"),
            "cell_C": 0.3,
            "packing_B": 0.4,
        },
    )
    assert scheduler._shift_history == []

    # All finite + complete — accepted
    scheduler.record_round_feedback(
        0,
        {"W2": 0.5},
        paper_quantities={"sheet_A": 0.5, "cell_C": 0.3, "packing_B": 0.4},
    )
    assert len(scheduler._shift_history) == 1


def test_codimension_scheduler_reset_clears_shift_history() -> None:
    """HIGH-1 ``reset()`` parity: ``_shift_history`` is cleared on reset.

    The other feedback histories (``_w2_history``,
    ``_evidence_ratio_history``) are reset by ``reset()``; the new
    ``_shift_history`` MUST follow the same convention so a replayed
    cycle starts from zero PID state.
    """
    from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler

    scheduler = CodimensionSheetScheduler(cycle_length=5)
    scheduler.record_round_feedback(
        0,
        {"W2": 0.5},
        paper_quantities={"sheet_A": 0.5, "cell_C": 0.3, "packing_B": 0.4},
    )
    assert len(scheduler._shift_history) == 1
    scheduler.reset()
    assert scheduler._shift_history == []


# ---------------------------------------------------------------------------
# MEDIUM-6 — SequentialScheduler.record_round_feedback forwards
#            ``paper_quantities`` to slots that accept the kwarg.
# ---------------------------------------------------------------------------


def test_sequential_scheduler_forwards_paper_quantities_to_paper_ratio_slot() -> None:
    """MEDIUM-6 fix: ``paper_quantities`` is forwarded to ``PaperRatioAdaptiveScheduler`` slot.

    The chain must thread the new ``paper_quantities`` kwarg through to
    the slot whose ``record_round_feedback`` accepts it. A two-call
    warm-up is required because ``PaperRatioAdaptiveScheduler`` only
    applies a shift update from the second sample onwards (mirroring
    the Wave 31 contract on EMA history length).
    """
    from adaptive_reflow.algorithm.scheduler import PaperRatioAdaptiveScheduler
    from adaptive_reflow.algorithm.scheduler._core import (
        default_cosine_scheduler,
    )
    from adaptive_reflow.algorithm.sequential import SequentialScheduler

    paper_ratio = PaperRatioAdaptiveScheduler()
    cosine = default_cosine_scheduler(cycle_length=4)
    seq = SequentialScheduler(schedulers=[(cosine, 4), (paper_ratio, 4)])

    seq.record_round_feedback(
        2,
        {"W2": 0.5},
        paper_quantities=_paper_quantities_a(2),
    )
    seq.record_round_feedback(
        3,
        {"W2": 0.5},
        paper_quantities=_paper_quantities_a(3),
    )
    # Two feedback calls with increasing sheet_A MUST shift the
    # PaperRatioAdaptiveScheduler's PID away from zero. The exact
    # direction follows the controller's
    # ``kp * (1 - sheet_ratio) - kd * sheet_delta`` formula.
    assert paper_ratio._shift != 0.0


def test_sequential_scheduler_legacy_slot_does_not_break_on_paper_quantities() -> None:
    """MEDIUM-6 backward-compat: legacy no-op slot stays no-op.

    A slot whose ``record_round_feedback`` predates Wave 38 (no
    ``paper_quantities`` kwarg) MUST still receive the legacy
    metrics-only call. The chain introspects the slot's signature
    once and caches the result on the sub-scheduler so the per-round
    cost is constant.
    """
    from adaptive_reflow.algorithm.scheduler import (
        ConstantScheduler,
        PaperRatioAdaptiveScheduler,
    )
    from adaptive_reflow.algorithm.sequential import SequentialScheduler

    cosine = ConstantScheduler(cycle_length=4, n_cap=0.5)
    paper_ratio = PaperRatioAdaptiveScheduler()
    seq = SequentialScheduler(schedulers=[(cosine, 4), (paper_ratio, 4)])

    # Should not raise even though the legacy slot ignores paper_quantities
    seq.record_round_feedback(
        2,
        {"W2": 0.5},
        paper_quantities={"sheet_A": 0.3, "cell_C": 0.2, "packing_B": 0.5},
    )
    seq.record_round_feedback(
        3,
        {"W2": 0.5},
        paper_quantities={"sheet_A": 0.4, "cell_C": 0.2, "packing_B": 0.5},
    )
    assert paper_ratio._shift != 0.0


# ---------------------------------------------------------------------------
# MEDIUM-8 — BatchedTrajectoryRunner.run forwards ``paper_quantities``
#            to the scheduler's ``record_round_feedback``.
# ---------------------------------------------------------------------------


def test_batched_runner_forwards_paper_quantities_to_scheduler() -> None:
    """MEDIUM-8 fix: ``BatchedTrajectoryRunner.run`` forwards ``paper_quantities``.

    Construct the minimal runner (cycle_length=3, trajectories_per_round=1,
    endpoints_per_trajectory=1) with a ``PaperRatioAdaptiveScheduler``
    and a callable ``paper_quantities_fn`` that returns an
    increasing-sheet_A payload. After ``run()`` the
    ``PaperRatioAdaptiveScheduler._shift`` MUST have moved off zero
    — the runner forwarded the carrier. We avoid exercising the
    trajectory generator by giving the runner a deterministic
    stub adapter so the loop executes three rounds deterministically.
    """
    import numpy as np

    from adaptive_reflow.algorithm.batched_runner import (
        BatchedRunnerConfig,
        BatchedTrajectoryRunner,
    )
    from adaptive_reflow.algorithm.scheduler import PaperRatioAdaptiveScheduler

    class StubAdapter:
        """Minimal deterministic stub satisfying ``_BatchedAdapterProtocol``."""

        target = "two_moons"

        def generate_trajectory(
            self,
            *,
            n_trajectories: int,
            endpoints_per_trajectory: int,
            n_gen: int,
            seed: int,
        ) -> np.ndarray:
            # Two moons: each trajectory carries ``endpoints_per_trajectory``
            # 2-D endpoints. The exact shape is what
            # ``_reshape_round_endpoints`` expects.
            return np.zeros(
                (n_trajectories, endpoints_per_trajectory, n_gen, 2),
                dtype=np.float64,
            )

    scheduler = PaperRatioAdaptiveScheduler()
    cfg = BatchedRunnerConfig(
        cycle_length=3,
        trajectories_per_round=1,
        endpoints_per_trajectory=1,
        scheduler=scheduler,
        seed=0,
    )
    runner = BatchedTrajectoryRunner(
        cfg,
        StubAdapter(),  # type: ignore[arg-type]
        paper_quantities_fn=lambda r: _paper_quantities_a(r),
    )
    runner.run()
    # Three feedback calls on the PaperRatioAdaptiveScheduler across
    # 3 rounds. The PID needs 2+ samples with paper_quantities to
    # move ``_shift`` off zero.
    assert scheduler._shift != 0.0


def test_batched_runner_without_paper_quantities_fn_is_legacy_compat() -> None:
    """MEDIUM-8 backward-compat: no ``paper_quantities_fn`` keeps legacy semantics.

    When the caller omits the ``paper_quantities_fn`` constructor
    argument (the legacy Wave 35 path), the runner MUST continue to
    forward only ``{"W2": float(w2)}`` to the scheduler so every
    pinned D.4 regression vector stays valid. The
    ``PaperRatioAdaptiveScheduler`` (whose ``record_round_feedback``
    signature accepts the kwarg but does not require it) MUST remain
    at zero shift in the no-paper-quantities path.
    """
    import numpy as np

    from adaptive_reflow.algorithm.batched_runner import (
        BatchedRunnerConfig,
        BatchedTrajectoryRunner,
    )
    from adaptive_reflow.algorithm.scheduler import PaperRatioAdaptiveScheduler

    class StubAdapter:
        target = "two_moons"

        def generate_trajectory(
            self,
            *,
            n_trajectories: int,
            endpoints_per_trajectory: int,
            n_gen: int,
            seed: int,
        ) -> np.ndarray:
            return np.zeros(
                (n_trajectories, endpoints_per_trajectory, n_gen, 2),
                dtype=np.float64,
            )

    scheduler = PaperRatioAdaptiveScheduler()
    cfg = BatchedRunnerConfig(
        cycle_length=3,
        trajectories_per_round=1,
        endpoints_per_trajectory=1,
        scheduler=scheduler,
        seed=0,
    )
    runner = BatchedTrajectoryRunner(cfg, StubAdapter())  # type: ignore[arg-type]
    runner.run()
    # No paper quantities forwarded — the PID's first call seeds the
    # EMA but never produces a non-zero shift (the controller needs
    # >= 2 samples AND a paper_quantities payload to move).
    assert scheduler._shift == 0.0
