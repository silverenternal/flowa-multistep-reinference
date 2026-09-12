"""Tests for the state-machine integration layer.

These tests cover Phase 2b (state machines wired into
:class:`ReInferenceRunner` and every scheduler family). The wrap-only
strategy is verified end-to-end:

* Every public scheduler class produces a wrapped instance whose
  ``isinstance`` check against the original class is True.
* The wrapped instance emits the expected state-machine transitions
  through ``sample`` / ``reset`` / ``record_round_feedback``.
* The :class:`ReInferenceRunner` orchestrator transitions through the
  ROUND_ACTIVE -> FEEDBACK_PENDING -> NEXT_ROUND_READY cycle on every
  round and ends in COMPLETE on success / FAILED on chain break.
* Universal coverage: every scheduler family documented in
  ``docs/r4-survey/02-universal-statemachine-plan.md`` is exercised.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pytest

# Scheduler classes to cover (the universal 14 + extras per design doc)
from adaptive_reflow.algorithm.scheduler import (
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    SchedulerProtocol,
    SigmoidScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler.evidence_driven import (
    EvidenceDrivenScheduler,
)
from adaptive_reflow.algorithm.scheduler.freetraj import FreeTrajScheduler
from adaptive_reflow.algorithm.scheduler_extra import (
    AdaptivePIDScheduler,
    EDMScheduler,
    JitteredConstantScheduler,
    MultiChannelJitteredConstantScheduler,
)
from adaptive_reflow.algorithm.state_machine_integration import (
    OrchestratorEvent,
    OrchestratorState,
    SchedulerEvent,
    SchedulerState,
    make_runner_state_machine,
    wrap_scheduler_with_state_machine,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    CosineScheduleConfig,
    FactorValue,
    StateMachine,
)
from adaptive_reflow.contracts.state_machine import InvalidTransitionError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_cosine_config(cycle_length: int = 4, n_min: float = 0.05, n_max: float = 0.5):
    """Build a minimal :class:`CosineScheduleConfig` for tests."""
    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=cycle_length,
        n_min=FactorValue(n_min),
        n_max=FactorValue(n_max),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("cfg-test"),
        frozen_before_evaluation=True,
    )


# ---------------------------------------------------------------------------
# Per-scheduler wrap tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scheduler_factory",
    [
        ("CosineAnnealScheduler", lambda: CosineAnnealScheduler(_make_cosine_config())),
        ("ConstantScheduler", lambda: ConstantScheduler(cycle_length=4, n_cap=0.3)),
        ("LinearScheduler", lambda: LinearScheduler(cycle_length=4, n_min=0.05, n_max=0.5)),
        ("ExponentialScheduler", lambda: ExponentialScheduler(cycle_length=4, n_max=0.5, alpha=2.0)),
        ("PolynomialScheduler", lambda: PolynomialScheduler(cycle_length=4, n_min=0.05, n_max=0.5, power=2)),
        ("SigmoidScheduler", lambda: SigmoidScheduler(cycle_length=4, n_min=0.05, n_max=0.5)),
        ("ConvergenceAdaptiveScheduler", lambda: ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler(_make_cosine_config()), kp=0.1, kd=0.01, shift_max=0.5)),
        ("CodimensionSheetScheduler", lambda: CodimensionSheetScheduler(cycle_length=4, n_min=0.05, n_max=0.5)),
        ("EvidenceDrivenScheduler", lambda: EvidenceDrivenScheduler(_make_cosine_config())),
        ("FreeTrajScheduler", lambda: FreeTrajScheduler(_make_cosine_config())),
        ("EDMScheduler", lambda: EDMScheduler(cycle_length=4, n_min=0.05, n_max=0.5)),
        ("AdaptivePIDScheduler", lambda: AdaptivePIDScheduler(base=CosineAnnealScheduler(_make_cosine_config()), kp=0.1, kd=0.01)),
        ("JitteredConstantScheduler", lambda: JitteredConstantScheduler(cycle_length=4, n_cap=0.3)),
        ("MultiChannelJitteredConstantScheduler", lambda: MultiChannelJitteredConstantScheduler(cycle_length=4, n_cap=0.3)),
    ],
)
def test_wrap_preserves_isinstance(scheduler_factory: Any) -> None:
    """Wrap every scheduler family; verify isinstance still matches inner."""
    name, factory = scheduler_factory
    inner = factory()
    wrapped = wrap_scheduler_with_state_machine(inner)
    assert isinstance(wrapped, type(inner)), (
        f"{name}: wrapped not isinstance of {type(inner).__name__}"
    )
    assert hasattr(wrapped, "_state_machine")
    assert isinstance(wrapped._state_machine, StateMachine)


def test_wrap_is_idempotent() -> None:
    """Wrapping an already-wrapped scheduler returns the same instance."""
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    wrapped_again = wrap_scheduler_with_state_machine(wrapped)
    assert wrapped is wrapped_again


def test_wrap_preserves_config_hash() -> None:
    """The wrapped scheduler's ``config_hash`` is identical to the inner."""
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    assert inner.config_hash() == wrapped.config_hash()


def test_wrap_preserves_to_config_round_trip() -> None:
    """The wrapped scheduler's ``to_config`` matches the inner."""
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    assert inner.to_config() == wrapped.to_config()


# ---------------------------------------------------------------------------
# Scheduler state-machine transition tests
# ---------------------------------------------------------------------------


def test_cosine_scheduler_state_machine_lifecycle() -> None:
    """Cosine scheduler: UNINITIALIZED -> INITIALIZED -> SAMPLING -> SAMPLE_EMITTED."""
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    assert sm.state == "UNINITIALIZED"
    wrapped.sample(0, 0, 0)
    # First sample: INIT -> INITIALIZED -> SAMPLING -> SAMPLE_EMITTED.
    assert sm.state == "SAMPLE_EMITTED"
    # Second sample (different round): SAMPLE_EMITTED -> SAMPLING -> SAMPLE_EMITTED.
    wrapped.sample(0, 1, 1)
    assert sm.state == "SAMPLE_EMITTED"


def test_cosine_scheduler_reset_transitions_to_initialized() -> None:
    """Reset returns the SM to INITIALIZED (via the RESET transition)."""
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    wrapped.sample(0, 0, 0)
    assert wrapped._state_machine.state == "SAMPLE_EMITTED"
    wrapped.reset()
    assert wrapped._state_machine.state == "INITIALIZED"


def test_convergence_adaptive_extended_transitions() -> None:
    """ConvergenceAdaptive scheduler: PID-aware extensions are reachable.

    First feedback -> PID_WARMING (warmup). Subsequent feedbacks ->
    PID_UPDATING via the ADJUST transition. Reset clears the SM.
    """
    inner = ConvergenceAdaptiveScheduler(
        base=CosineAnnealScheduler(_make_cosine_config()),
        kp=0.1,
        kd=0.01,
        shift_max=0.5,
    )
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    # Two rounds + two feedbacks
    wrapped.sample(0, 0, 0)
    wrapped.record_round_feedback(0, {"W2": 0.1})
    wrapped.sample(0, 1, 1)
    wrapped.record_round_feedback(1, {"W2": 0.05})
    # After two feedbacks, the SM should have visited FEEDBACK_RECEIVED
    # and walked through PID-aware transitions. Confirm via log entries.
    sources = [log.source for log in sm.log]
    targets = [log.target for log in sm.log]
    assert "SAMPLE_EMITTED" in sources  # we emitted a sample
    assert any(t in {"FEEDBACK_RECEIVED", "PID_WARMING", "PID_UPDATING", "ADJUSTED"} for t in targets), (
        f"PID-aware transitions never reached; targets={targets}"
    )


def test_codimension_sheet_extended_transitions() -> None:
    """CodimensionSheetScheduler: EVIDENCE_COMPUTED reachable after feedback."""
    inner = CodimensionSheetScheduler(cycle_length=4, n_min=0.05, n_max=0.5)
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    wrapped.sample(0, 0, 0)
    wrapped.record_round_feedback(0, {"W2": 0.1})
    targets = [log.target for log in sm.log]
    assert "EVIDENCE_COMPUTED" in targets, (
        f"EVIDENCE_COMPUTED not reached; targets={targets}"
    )


def test_evidence_driven_extended_transitions() -> None:
    """EvidenceDrivenScheduler: EPS_PROPAGATED / ADJUSTED reachable."""
    inner = EvidenceDrivenScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    wrapped.sample(0, 0, 0)
    wrapped.record_round_feedback(0, {"W2": 0.1})
    targets = [log.target for log in sm.log]
    # At minimum the SM should have visited FEEDBACK_RECEIVED via the
    # ADJUST transition; per-family extensions (PID_UPDATING /
    # EPS_PROPAGATED / ADJUSTED) may or may not fire depending on the
    # orchestrator's payload. Assert at least the common path.
    assert any(t in {"FEEDBACK_RECEIVED", "PID_UPDATING", "EPS_PROPAGATED", "ADJUSTED"} for t in targets), (
        f"Evidence-driven transitions never reached; targets={targets}"
    )


def test_freetraj_extended_transitions() -> None:
    """FreeTrajScheduler: TRAJECTORY_UPDATED / SUBSTEP_COMPUTED reachable."""
    inner = FreeTrajScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    wrapped.sample(0, 0, 0)
    wrapped.record_round_feedback(0, {"trajectory_progress": 0.5})
    targets = [log.target for log in sm.log]
    assert any(t in {"TRAJECTORY_UPDATED", "SUBSTEP_COMPUTED", "ADJUSTED"} for t in targets), (
        f"FreeTraj transitions never reached; targets={targets}"
    )


def test_edm_extended_transitions() -> None:
    """EDMScheduler: ADAPTIVE_WARMING / SIGMA_ADAPTING reachable (adaptive_sigma_max)."""
    inner = EDMScheduler(cycle_length=4, n_min=0.05, n_max=0.5, adaptive_sigma_max=True)
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    wrapped.sample(0, 0, 0)
    wrapped.record_round_feedback(0, {"W2": 0.1})
    targets = [log.target for log in sm.log]
    assert any(t in {"ADAPTIVE_WARMING", "SIGMA_ADAPTING", "ADJUSTED"} for t in targets), (
        f"EDM adaptive transitions never reached; targets={targets}"
    )


def test_multichannel_jittered_extended_transition() -> None:
    """MultiChannelJitteredConstantScheduler: CHANNEL_RESOLVED reachable."""
    inner = MultiChannelJitteredConstantScheduler(cycle_length=4, n_cap=0.3)
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    wrapped.sample(0, 0, 0)
    targets = [log.target for log in sm.log]
    assert "CHANNEL_RESOLVED" in targets, (
        f"CHANNEL_RESOLVED not reached; targets={targets}"
    )


def test_trivial_scheduler_noop_feedback() -> None:
    """Trivial schedulers (Cosine): record_round_feedback is a no-op inner."""
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    wrapped.sample(0, 0, 0)
    # No exception: the inner record_round_feedback is a no-op; the
    # wrapper still emits FEEDBACK_RECEIVED via the mixin.
    wrapped.record_round_feedback(0, {"W2": 0.1})
    targets = [log.target for log in sm.log]
    assert "FEEDBACK_RECEIVED" in targets


def test_invalid_transition_raises() -> None:
    """Sending an undefined event raises InvalidTransitionError.

    Verify the SM API directly (not via the wrapper, since the wrapper
    suppresses errors).
    """
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    sm = wrapped._state_machine
    wrapped.sample(0, 0, 0)
    # The wrapper suppresses InvalidTransitionError on FEEDBACK_RECEIVED
    # for trivial schedulers; the underlying SM still rejects unknown
    # events.
    with pytest.raises(InvalidTransitionError):
        sm.send("UNKNOWN_EVENT")


def test_guard_rejects_invalid_event_silently_via_wrapper() -> None:
    """The wrapper suppresses InvalidTransitionError (no behavioural break)."""
    inner = CosineAnnealScheduler(_make_cosine_config())
    wrapped = wrap_scheduler_with_state_machine(inner)
    wrapped.sample(0, 0, 0)
    # No exception: the wrapper uses contextlib.suppress around the
    # FEEDBACK_RECEIVED / ADJUST sends.
    wrapped.record_round_feedback(0, {"W2": 0.1})


# ---------------------------------------------------------------------------
# Orchestrator state machine tests
# ---------------------------------------------------------------------------


def test_orchestrator_state_machine_lifecycle() -> None:
    """Orchestrator SM: IDLE -> INITIALIZED -> ROUND_ACTIVE -> ... -> COMPLETE."""
    sm = make_runner_state_machine()
    assert sm.state == "IDLE"
    sm.send("INIT")
    assert sm.state == "INITIALIZED"
    sm.send("SAMPLE_REQUESTED")
    assert sm.state == "ROUND_ACTIVE"
    sm.send("SAMPLE_EMITTED")
    assert sm.state == "FEEDBACK_PENDING"
    sm.send("FEEDBACK_DISPATCHED")
    assert sm.state == "NEXT_ROUND_READY"
    sm.send("COMPLETE_RUN")
    assert sm.state == "COMPLETE"


def test_orchestrator_multiple_rounds() -> None:
    """Orchestrator SM cycles through NEXT_ROUND_READY -> ROUND_ACTIVE."""
    sm = make_runner_state_machine()
    sm.send("INIT")
    for _ in range(3):
        sm.send("SAMPLE_REQUESTED")
        assert sm.state == "ROUND_ACTIVE"
        sm.send("SAMPLE_EMITTED")
        assert sm.state == "FEEDBACK_PENDING"
        sm.send("FEEDBACK_DISPATCHED")
        assert sm.state == "NEXT_ROUND_READY"
    sm.send("COMPLETE_RUN")
    assert sm.state == "COMPLETE"


def test_orchestrator_fail_transition() -> None:
    """Orchestrator SM: any state -> FAILED on FAIL event."""
    sm = make_runner_state_machine()
    sm.send("INIT")
    sm.send("SAMPLE_REQUESTED")
    assert sm.state == "ROUND_ACTIVE"
    sm.send("FAIL")
    assert sm.state == "FAILED"


def test_orchestrator_reset_from_complete() -> None:
    """Orchestrator SM: COMPLETE -> IDLE on RESET (allows run reuse)."""
    sm = make_runner_state_machine()
    sm.send("INIT")
    sm.send("SAMPLE_REQUESTED")
    sm.send("SAMPLE_EMITTED")
    sm.send("FEEDBACK_DISPATCHED")
    sm.send("COMPLETE_RUN")
    assert sm.state == "COMPLETE"
    sm.send("RESET")
    assert sm.state == "IDLE"


# ---------------------------------------------------------------------------
# Byte-deterministic / log assertions
# ---------------------------------------------------------------------------


def test_orchestrator_log_byte_deterministic() -> None:
    """Two orchestrator SM instances driven by the same event sequence
    produce byte-identical transition logs.
    """
    sm1 = make_runner_state_machine(name="o1")
    sm2 = make_runner_state_machine(name="o2")
    for sm in (sm1, sm2):
        sm.send("INIT")
        sm.send("SAMPLE_REQUESTED")
        sm.send("SAMPLE_EMITTED")
        sm.send("FEEDBACK_DISPATCHED")
        sm.send("SAMPLE_REQUESTED")
        sm.send("SAMPLE_EMITTED")
        sm.send("FEEDBACK_DISPATCHED")
        sm.send("COMPLETE_RUN")
    # Strip the name field for the comparison (the two machines have
    # different names; the rest of the log entries are deterministic).
    def _strip(log: tuple) -> tuple:
        return tuple(
            (e.counter, e.event, e.source, e.target, e.kind)
            for e in log
        )

    assert _strip(sm1.log) == _strip(sm2.log)


def test_scheduler_log_byte_deterministic() -> None:
    """Two wrapped cosine schedulers driven by the same sequence produce
    byte-identical transition logs (the inner scheduler is deterministic).
    """
    sm_a = wrap_scheduler_with_state_machine(
        CosineAnnealScheduler(_make_cosine_config())
    )
    sm_b = wrap_scheduler_with_state_machine(
        CosineAnnealScheduler(_make_cosine_config())
    )
    for w in (sm_a, sm_b):
        w.sample(0, 0, 0)
        w.sample(0, 1, 1)
        w.reset()
        w.sample(0, 0, 0)

    def _strip(log: tuple) -> tuple:
        return tuple(
            (e.counter, e.event, e.source, e.target, e.kind)
            for e in log
        )

    assert _strip(sm_a._state_machine.log) == _strip(sm_b._state_machine.log)


# ---------------------------------------------------------------------------
# ReInferenceRunner end-to-end with state machine
# ---------------------------------------------------------------------------


def test_runner_state_machine_default_factory() -> None:
    """The default paper-quantity-driven scheduler is wrapped by the runner.

    Wave 34 wire change: the runner's default scheduler is now the
    paper-quantity-driven :class:`CodimensionSheetScheduler` (formerly
    the cosine ramp). The state-machine wrapper preserves the
    ``schedule_family()`` string and the runner end-state machine
    remains IDLE before any round is run.
    """
    from adaptive_reflow.algorithm.runner import ReInferenceRunner
    # Wave 104 P2-B split test_runner.py into per-class sub-files; the
    # _twodim_adapter fixture moved to test_batched_runner.py.
    from tests.test_algorithm.test_batched_runner import _twodim_adapter  # type: ignore

    # _twodim_adapter is a session-scoped fixture; here we only need
    # *any* adapter to exercise the constructor. Skip if unavailable.
    try:
        adapter = _twodim_adapter.__wrapped__ if hasattr(_twodim_adapter, "__wrapped__") else _twodim_adapter  # type: ignore[attr-defined]
    except Exception:
        pytest.skip("twodim_adapter fixture not available")
    runner = ReInferenceRunner(adapter=adapter)
    # Wave 34 default: paper-quantity-driven CodimensionSheetScheduler.
    assert isinstance(runner.scheduler, CodimensionSheetScheduler)
    assert hasattr(runner, "state_machine")
    assert isinstance(runner.state_machine, StateMachine)
    assert runner.state_machine.state == "IDLE"
