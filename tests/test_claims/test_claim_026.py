"""CLM-026: ConvergenceAdaptiveScheduler PID consumes `_smoothed_w2`.

Asserted by docs/CLAIMS.md:593-620.
ConvergenceAdaptiveScheduler.record_round_feedback appends the
EMA-smoothed W2 (`self._smoothed_w2`) to `_w2_history` so the PID's
`prev = self._w2_history[-2]` reference reads the same signal the EMA
was supposed to expose.

We pin:
    1. After a single record_round_feedback call, _w2_history has
       length 1.
    2. The appended value equals `_smoothed_w2` (not the raw aggregated
       `metrics["W2"]`).
"""
from __future__ import annotations

from adaptive_reflow.algorithm.scheduler._core import (
    ConvergenceAdaptiveScheduler,
)


def _make_scheduler() -> ConvergenceAdaptiveScheduler:
    return ConvergenceAdaptiveScheduler(ema=0.5)


def test_claim_026_record_round_feedback_appends_smoothed_w2() -> None:
    """The single appended value equals _smoothed_w2 (EMA)."""
    sch = _make_scheduler()
    sch.record_round_feedback(
        round_in_cycle=0, metrics={"W2": 0.4},
    )
    assert len(sch.w2_history) == 1, f"expected len=1, got {len(sch.w2_history)}"
    assert sch._smoothed_w2 is not None
    assert float(sch.w2_history[-1]) == float(sch._smoothed_w2), (
        f"appended {float(sch.w2_history[-1])!r} != _smoothed_w2 "
        f"{float(sch._smoothed_w2)!r}"
    )


def test_claim_026_two_calls_yield_smoothed_history() -> None:
    """After two calls, both appended values follow the EMA recursion."""
    sch = _make_scheduler()
    sch.record_round_feedback(round_in_cycle=0, metrics={"W2": 0.4})
    sch.record_round_feedback(round_in_cycle=1, metrics={"W2": 0.2})
    assert len(sch.w2_history) == 2
    # EMA with ema=0.5: history[0]=0.4, history[1]=0.5*0.2+0.5*0.4=0.3
    assert abs(float(sch.w2_history[-1]) - 0.3) < 1e-12, (
        f"second EMA step = {float(sch.w2_history[-1])!r}, expected 0.3"
    )
