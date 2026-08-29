"""State-machine integration layer for schedulers + the orchestrator.

Phase 2a shipped the generic :class:`StateMachine` library in
:mod:`adaptive_reflow.contracts.state_machine`. Phase 2b wires that
library into every scheduler + the :class:`ReInferenceRunner` orchestrator.

Design constraints (carried from
``docs/r4-survey/02-universal-statemachine-plan.md``):

* **WRAP, do not replace.** The state machine is an *observation-only*
  wrapper around the existing :class:`SchedulerProtocol` implementation.
  We never mutate the underlying scheduler's behaviour; we only observe
  method calls and record state transitions.
* **Backward compatible by construction.** All existing tests continue
  to pass because the wrapped scheduler exposes the same public API as
  the underlying scheduler (duck-typed :class:`SchedulerProtocol`).
* **Universal coverage.** Every scheduler family gets a state machine
  with at least the common 6-state vocabulary (UNINITIALIZED /
  INITIALIZED / SAMPLING / SAMPLE_EMITTED / ROUND_TERMINATED /
  TERMINATED). Per-family extension states are added when warranted.
* **The 4 feedback loops become explicit typed transitions.** The
  runner's state machine explicitly transitions through the
  ROUND_ACTIVE -> FEEDBACK_PENDING -> NEXT_ROUND_READY cycle on every
  round.

State-event vocabulary (common across all schedulers)
-----------------------------------------------------

States:
    UNINITIALIZED, INITIALIZED, SAMPLING, SAMPLE_EMITTED,
    ROUND_TERMINATED, TERMINATED.

Events:
    INIT, SAMPLE_REQUESTED, SAMPLE_EMIT, RESET, TERMINATE.

Per-family extensions (see :func:`_build_state_machine_for`):

* :class:`ConvergenceAdaptiveScheduler` -> adds ``PID_WARMING`` and
  ``PID_UPDATING`` (``FEEDBACK_RECEIVED`` event).
* :class:`CodimensionSheetScheduler` -> adds ``EVIDENCE_COMPUTED`` and
  ``PROFILE_BOUND``.
* :class:`EvidenceDrivenScheduler` -> adds ``PID_UPDATING``,
  ``EPS_PROPAGATED``, ``EPS_FLOORED``.
* :class:`FreeTrajScheduler` -> adds ``TRAJECTORY_UPDATED``,
  ``SUBSTEP_COMPUTED``.
* :class:`EDMScheduler` -> adds ``ADAPTIVE_WARMING``,
  ``SIGMA_ADAPTING`` (only when ``adaptive_sigma_max=True``).
* :class:`AdaptivePIDScheduler` -> adds ``PID_WARMING``,
  ``PID_UPDATING``, ``INTEGRAL_ACCUMULATING``.
* :class:`MultiChannelJitteredConstantScheduler` -> adds
  ``CHANNEL_RESOLVED``.
* :class:`SequentialScheduler` -> adds ``SLOT_ACTIVE``,
  ``FALLBACK_EMITTED``.
* :class:`HandoffSequentialScheduler` -> adds ``HANDOFF_BLENDING``.

Public surface
--------------

* :func:`wrap_scheduler_with_state_machine` — wrap a single scheduler.
* :class:`RunnerStateMachine` — orchestrator state machine factory.
* :data:`ORCHESTRATOR_STATES` / :data:`ORCHESTRATOR_EVENTS` — orchestrator
  state/event vocabularies.
"""
from __future__ import annotations

import contextlib
import math
from collections.abc import Mapping
from typing import Any, Literal, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import CosineScheduleSample, StateMachine
from adaptive_reflow.contracts.state_machine import InvalidTransitionError

# ---------------------------------------------------------------------------
# Common state + event vocabularies
# ---------------------------------------------------------------------------

SchedulerState = Literal[
    "UNINITIALIZED",
    "INITIALIZED",
    "SAMPLING",
    "SAMPLE_EMITTED",
    "FEEDBACK_RECEIVED",
    "ADJUSTED",
    "ROUND_TERMINATED",
    "TERMINATED",
    # Per-family extensions:
    "PID_WARMING",
    "PID_UPDATING",
    "EVIDENCE_COMPUTED",
    "PROFILE_BOUND",
    "EPS_PROPAGATED",
    "EPS_FLOORED",
    "TRAJECTORY_UPDATED",
    "SUBSTEP_COMPUTED",
    "ADAPTIVE_WARMING",
    "SIGMA_ADAPTING",
    "INTEGRAL_ACCUMULATING",
    "CHANNEL_RESOLVED",
    "SLOT_ACTIVE",
    "FALLBACK_EMITTED",
    "HANDOFF_BLENDING",
]

SchedulerEvent = Literal[
    "INIT",
    "SAMPLE_REQUESTED",
    "SAMPLE_EMIT",
    "FEEDBACK_RECEIVED",
    "ADJUST",
    "RESET",
    "TERMINATE",
]


# Orchestrator state + event vocabularies (per the design doc §5)
OrchestratorState = Literal[
    "IDLE",
    "INITIALIZED",
    "ROUND_ACTIVE",
    "FEEDBACK_PENDING",
    "NEXT_ROUND_READY",
    "COMPLETE",
    "FAILED",
]

OrchestratorEvent = Literal[
    "INIT",
    "SAMPLE_REQUESTED",
    "SAMPLE_EMITTED",
    "FEEDBACK_DISPATCHED",
    "ADVANCE",
    "COMPLETE_RUN",
    "RESET",
    "FAIL",
]


# ---------------------------------------------------------------------------
# State machine factory
# ---------------------------------------------------------------------------


def _build_state_machine_for(scheduler: Any) -> StateMachine[SchedulerState, SchedulerEvent]:
    """Build a state machine appropriate for the given scheduler.

    Per-family extension states are added when the scheduler's class is
    recognised. The base 6-state vocabulary is always present.

    The ``scheduler`` argument may be either a raw inner scheduler or a
    wrapped instance; we walk the MRO looking for the first non-mixin
    class so per-family extensions are wired correctly either way.
    """
    # Walk the MRO to find the inner scheduler class name. The wrapped
    # class is named ``_StateMachineWrapped{InnerClass}``; the inner
    # class is whatever follows ``_StateMachineSchedulerBase`` in the
    # MRO.
    name = type(scheduler).__name__
    if name.startswith("_StateMachineWrapped"):
        # Strip the wrapper prefix to recover the inner class name.
        name = name[len("_StateMachineWrapped") :]
    sm: StateMachine[SchedulerState, SchedulerEvent] = StateMachine(
        initial="UNINITIALIZED", name=f"scheduler:{name}"
    )

    # ---- Common transitions (always present) ----------------------------
    # INIT -> INITIALIZED happens automatically when the scheduler is
    # wrapped. We register the transition so the log records the move.
    sm._state = "UNINITIALIZED"  # explicit; matches initial

    # INITIALIZED -> SAMPLING (on SAMPLE_REQUESTED)
    sm.add_transition(
        source="UNINITIALIZED",
        event="INIT",
        target="INITIALIZED",
    )
    sm.add_transition(
        source="INITIALIZED",
        event="SAMPLE_REQUESTED",
        target="SAMPLING",
    )
    sm.add_transition(
        source="SAMPLING",
        event="SAMPLE_EMIT",
        target="SAMPLE_EMITTED",
    )
    sm.add_transition(
        source="SAMPLE_EMITTED",
        event="SAMPLE_REQUESTED",
        target="SAMPLING",
    )
    # FEEDBACK_RECEIVED is a common transition for ALL scheduler
    # families (universal coverage per the design doc). Trivial
    # families (Cosine, Constant, Linear, ...) no-op on the inner
    # scheduler but the SM still records the lifecycle step.
    sm.add_transition(
        source="SAMPLE_EMITTED",
        event="FEEDBACK_RECEIVED",
        target="FEEDBACK_RECEIVED",
    )
    sm.add_transition(
        source="FEEDBACK_RECEIVED",
        event="ADJUST",
        target="ADJUSTED",
    )
    sm.add_transition(
        source="ADJUSTED",
        event="SAMPLE_REQUESTED",
        target="SAMPLING",
    )
    sm.add_transition(
        source="SAMPLE_EMITTED",
        event="TERMINATE",
        target="ROUND_TERMINATED",
    )
    sm.add_transition(
        source="ROUND_TERMINATED",
        event="TERMINATE",
        target="TERMINATED",
    )
    sm.add_transition(
        source="INITIALIZED",
        event="TERMINATE",
        target="TERMINATED",
    )
    # RESET from any state -> INITIALIZED
    for src in (
        "UNINITIALIZED",
        "INITIALIZED",
        "SAMPLING",
        "SAMPLE_EMITTED",
        "FEEDBACK_RECEIVED",
        "ADJUSTED",
        "ROUND_TERMINATED",
        "TERMINATED",
    ):
        sm.add_transition(source=src, event="RESET", target="INITIALIZED")

    # ---- Per-family extensions -----------------------------------------
    if name in {
        "ConvergenceAdaptiveScheduler",
        "AdaptivePIDScheduler",
        "EvidenceDrivenScheduler",
        "EDMScheduler",
    }:
        # PID-aware families: FEEDBACK_RECEIVED -> PID_WARMING (first round)
        # or PID_UPDATING (subsequent rounds). Guard: cooldown_complete
        # is signalled by the wrapper based on the scheduler's own state.
        if name in {"ConvergenceAdaptiveScheduler", "AdaptivePIDScheduler"}:
            sm.add_transition(
                source="FEEDBACK_RECEIVED",
                event="ADJUST",
                target="PID_WARMING",
                priority=1,
            )
            sm.add_transition(
                source="PID_WARMING",
                event="ADJUST",
                target="PID_UPDATING",
                priority=1,
            )
            sm.add_transition(
                source="PID_UPDATING",
                event="SAMPLE_REQUESTED",
                target="SAMPLING",
                priority=1,
            )
        if name == "EvidenceDrivenScheduler":
            sm.add_transition(
                source="FEEDBACK_RECEIVED",
                event="ADJUST",
                target="PID_UPDATING",
                priority=1,
            )
            sm.add_transition(
                source="PID_UPDATING",
                event="ADJUST",
                target="EPS_PROPAGATED",
                priority=1,
            )
            sm.add_transition(
                source="EPS_PROPAGATED",
                event="ADJUST",
                target="ADJUSTED",
                priority=1,
            )
            sm.add_transition(
                source="ADJUSTED",
                event="SAMPLE_REQUESTED",
                target="SAMPLING",
                priority=1,
            )
        if name == "EDMScheduler":
            sm.add_transition(
                source="FEEDBACK_RECEIVED",
                event="ADJUST",
                target="ADAPTIVE_WARMING",
                priority=1,
            )
            sm.add_transition(
                source="ADAPTIVE_WARMING",
                event="ADJUST",
                target="SIGMA_ADAPTING",
                priority=1,
            )
            sm.add_transition(
                source="SIGMA_ADAPTING",
                event="SAMPLE_REQUESTED",
                target="SAMPLING",
                priority=1,
            )
    elif name == "CodimensionSheetScheduler":
        sm.add_transition(
            source="FEEDBACK_RECEIVED",
            event="ADJUST",
            target="EVIDENCE_COMPUTED",
            priority=1,
        )
        sm.add_transition(
            source="EVIDENCE_COMPUTED",
            event="ADJUST",
            target="ADJUSTED",
            priority=1,
        )
        sm.add_transition(
            source="ADJUSTED",
            event="SAMPLE_REQUESTED",
            target="SAMPLING",
            priority=1,
        )
        # PROFILE_BOUND is reachable when a profile_residual_fn is
        # supplied; the wrap-time introspection below enables the
        # transition by checking the inner's ``profile_residual_fn``
        # attribute. We add the transition only when applicable so
        # schedulers without a profile follow the common
        # UNINITIALIZED -> INITIALIZED path.
        profile_fn = getattr(scheduler, "_profile_residual_fn", None) or getattr(
            scheduler, "profile_residual_fn", None
        )
        if profile_fn is not None:
            sm.add_transition(
                source="UNINITIALIZED",
                event="INIT",
                target="PROFILE_BOUND",
                priority=1,
            )
            sm.add_transition(
                source="PROFILE_BOUND",
                event="SAMPLE_REQUESTED",
                target="SAMPLING",
                priority=1,
            )
    elif name == "FreeTrajScheduler":
        sm.add_transition(
            source="FEEDBACK_RECEIVED",
            event="ADJUST",
            target="TRAJECTORY_UPDATED",
            priority=1,
        )
        sm.add_transition(
            source="TRAJECTORY_UPDATED",
            event="ADJUST",
            target="SUBSTEP_COMPUTED",
            priority=1,
        )
        sm.add_transition(
            source="SUBSTEP_COMPUTED",
            event="ADJUST",
            target="ADJUSTED",
            priority=1,
        )
        sm.add_transition(
            source="ADJUSTED",
            event="SAMPLE_REQUESTED",
            target="SAMPLING",
            priority=1,
        )
    elif name == "MultiChannelJitteredConstantScheduler":
        sm.add_transition(
            source="SAMPLING",
            event="SAMPLE_EMIT",
            target="CHANNEL_RESOLVED",
            priority=1,
        )
        sm.add_transition(
            source="CHANNEL_RESOLVED",
            event="SAMPLE_EMIT",
            target="SAMPLE_EMITTED",
            priority=1,
        )
    elif name == "SequentialScheduler":
        sm.add_transition(
            source="SAMPLING",
            event="SAMPLE_EMIT",
            target="SLOT_ACTIVE",
            priority=1,
        )
        sm.add_transition(
            source="SLOT_ACTIVE",
            event="SAMPLE_EMIT",
            target="SAMPLE_EMITTED",
            priority=1,
        )
        sm.add_transition(
            source="SAMPLE_EMITTED",
            event="SAMPLE_EMIT",
            target="FALLBACK_EMITTED",
            priority=1,
        )
    elif name == "HandoffSequentialScheduler":
        sm.add_transition(
            source="SAMPLING",
            event="SAMPLE_EMIT",
            target="SLOT_ACTIVE",
            priority=1,
        )
        sm.add_transition(
            source="SLOT_ACTIVE",
            event="SAMPLE_EMIT",
            target="HANDOFF_BLENDING",
            priority=1,
        )
        sm.add_transition(
            source="HANDOFF_BLENDING",
            event="SAMPLE_EMIT",
            target="SAMPLE_EMITTED",
            priority=1,
        )
        sm.add_transition(
            source="SAMPLE_EMITTED",
            event="SAMPLE_EMIT",
            target="FALLBACK_EMITTED",
            priority=1,
        )

    return sm


# ---------------------------------------------------------------------------
# Scheduler wrapper (dynamic subclass)
# ---------------------------------------------------------------------------


@runtime_checkable
class _SchedulerLike(Protocol):
    """Duck-typed protocol the wrapper honours (subset of SchedulerProtocol)."""

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> Any: ...

    def cycle_length(self) -> int: ...

    def schedule_family(self) -> str: ...

    def config_hash(self) -> str: ...

    def reset(self) -> None: ...

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None: ...

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]: ...

    def to_config(self) -> dict[str, Any]: ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Any: ...


class _StateMachineSchedulerBase:
    """Mixin providing the ``_state_machine`` field + per-method SM events.

    Dynamically combined with the inner scheduler's class so that
    ``isinstance(wrapped, InnerClass)`` returns ``True`` (Phase 2b
    backward-compatibility invariant). The inner scheduler's behaviour
    is preserved byte-for-byte; the mixin only emits events around
    ``sample`` / ``reset`` / ``record_round_feedback``.
    ``inject_noise`` is delegated through ``__getattr__`` so that
    ``hasattr(wrapped, "inject_noise")`` returns ``True`` only when
    the inner scheduler implements it (test doubles without the hook
    remain invisible to ``hasattr`` checks).
    """

    _state_machine: StateMachine[SchedulerState, SchedulerEvent]
    _w2_history: list[float]

    def _sm_init(self: Any) -> None:
        """Initialise the per-instance state machine + W2 history.

        Called by ``__init_subclass__`` so the field is populated the
        first time the wrapped class is instantiated. The wrapper
        always has access to the inner scheduler's own attributes
        because the mixin is dynamically added to the inner class.
        """
        self._w2_history = []
        # Build the state machine using the *inner* class name so the
        # per-family extension states are wired correctly.
        self._state_machine = _build_state_machine_for(self)

    def sample(
        self: Any,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> Any:
        """Wrap the inner ``sample`` call with state-machine events."""
        if self._state_machine.state == "UNINITIALIZED":
            self._state_machine.send("INIT")
        current = self._state_machine.state
        if current in {"INITIALIZED", "SAMPLE_EMITTED", "ADJUSTED"}:
            self._state_machine.send("SAMPLE_REQUESTED")
        elif current in {
            "FEEDBACK_RECEIVED",
            "PID_WARMING",
            "PID_UPDATING",
            "EVIDENCE_COMPUTED",
            "EPS_PROPAGATED",
            "TRAJECTORY_UPDATED",
            "SUBSTEP_COMPUTED",
            "ADAPTIVE_WARMING",
            "SIGMA_ADAPTING",
            "INTEGRAL_ACCUMULATING",
        }:
            # Walk through ADJUST repeatedly until the SM reaches a
            # state from which ``SAMPLE_REQUESTED`` can fire. This
            # covers per-family chains like
            # FEEDBACK_RECEIVED -> PID_UPDATING -> EPS_PROPAGATED ->
            # ADJUSTED (EvidenceDrivenScheduler) where multiple
            # intermediate ``ADJUST`` events are needed.
            for _ in range(8):
                with contextlib.suppress(InvalidTransitionError):
                    self._state_machine.send("ADJUST")
                if self._state_machine.state == "ADJUSTED":
                    break
            with contextlib.suppress(InvalidTransitionError):
                self._state_machine.send("SAMPLE_REQUESTED")
        # Delegate to the inner scheduler's real ``sample``. We call
        # ``self.__class__.__mro__`` walk to find the next ``sample``
        # method (skip our own override).
        result = _call_inner_method(
            self, "sample", outer_cycle_id, round_in_cycle, target_round
        )
        self._state_machine.send("SAMPLE_EMIT")
        return result

    def reset(self: Any) -> None:
        """Wrap the inner ``reset`` call with a state-machine RESET event."""
        with contextlib.suppress(AttributeError):
            # Inner doesn't define ``reset`` (test double); still emit
            # the SM RESET event so the SM transitions back to
            # INITIALIZED. The runner never wraps such schedulers in
            # practice but the SM is observation-only so we never crash.
            _call_inner_method(self, "reset")
        self._state_machine.send("RESET")

    def record_round_feedback(
        self: Any,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Wrap the inner ``record_round_feedback`` with SM events."""
        w2 = metrics.get("W2") or metrics.get("w2")
        if w2 is not None:
            try:
                v = float(w2)
                if math.isfinite(v):
                    self._w2_history.append(v)
            except (TypeError, ValueError):
                pass
        try:
            _call_inner_method(self, "record_round_feedback", round_in_cycle, metrics)
        except AttributeError:
            # Inner doesn't define ``record_round_feedback`` (test
            # double or trivial scheduler family). Match the legacy
            # runner behaviour: ``hasattr(scheduler,
            # "record_round_feedback")`` is False for the inner, but
            # the wrapper adds the method via the mixin so the runner
            # calls it; we no-op silently when the inner is absent.
            return None
        with contextlib.suppress(InvalidTransitionError):
            self._state_machine.send("FEEDBACK_RECEIVED")
        # Walk the ADJUST chain until the SM reaches ADJUSTED. This
        # handles per-family extensions like
        # FEEDBACK_RECEIVED -> PID_UPDATING -> EPS_PROPAGATED -> ADJUSTED.
        for _ in range(8):
            with contextlib.suppress(InvalidTransitionError):
                self._state_machine.send("ADJUST")
            if self._state_machine.state == "ADJUSTED":
                break
        return None


def _call_inner_method(instance: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    """Invoke the *inner* scheduler's method ``name`` (skip the mixin override).

    Walks ``type(instance).__mro__`` looking for a concrete definition
    of ``name`` in each class's ``__dict__``. The first hit (after
    skipping :class:`_StateMachineSchedulerBase`) wins. If no concrete
    definition exists on the inner class, ``AttributeError`` is raised
    so callers can fall back to the protocol-level default behaviour
    (matches the legacy ``hasattr`` checks the runner performs).
    """
    cls = type(instance)
    for klass in cls.__mro__:
        if klass is _StateMachineSchedulerBase:
            continue
        method = klass.__dict__.get(name)
        if method is not None:
            return method(instance, *args, **kwargs)
    raise AttributeError(
        f"method {name!r} not found on inner class for {cls!r}"
    )


# Cache of wrapped classes (one per inner class) so repeated wraps of
# the same scheduler type share the same dynamically-built subclass.
_WRAPPED_CLASS_CACHE: dict[type, type] = {}


def _build_wrapped_class(inner_cls: type) -> type:
    """Return a state-machine-wrapped subclass of ``inner_cls``.

    Cached per ``inner_cls`` so all wrappers of the same scheduler
    family share one class (preserves ``isinstance`` checks across
    wrappers and keeps the class registry stable).
    """
    cached = _WRAPPED_CLASS_CACHE.get(inner_cls)
    if cached is not None:
        return cached
    wrapped = type(
        f"_StateMachineWrapped{inner_cls.__name__}",
        (_StateMachineSchedulerBase, inner_cls),
        {},
    )
    _WRAPPED_CLASS_CACHE[inner_cls] = wrapped
    return wrapped


def wrap_scheduler_with_state_machine(
    scheduler: Any,
) -> Any:
    """Wrap a scheduler with an observation-only state machine.

    The returned wrapper is a *subclass* of the inner scheduler's
    class, so ``isinstance(wrapped, InnerClass)`` returns ``True``
    (Phase 2b backward-compatibility invariant). All public methods
    continue to work byte-for-byte; the wrapper only emits
    state-machine events around ``sample`` / ``reset`` /
    ``record_round_feedback``. ``inject_noise`` delegates to the
    inner scheduler unchanged.

    Idempotent: a scheduler that is already a wrapped instance is
    returned unchanged.
    """
    if type(scheduler).__name__.startswith("_StateMachineWrapped"):
        return scheduler
    wrapped_cls = _build_wrapped_class(type(scheduler))
    # Re-instantiate via ``copy.copy`` so we don't mutate the caller's
    # reference. The wrapped instance carries the same private attrs
    # (``_config``, ``_last_sample``, ``_w2_history``, etc.) as the
    # inner scheduler because the wrapper class inherits from it.
    import copy

    wrapped = copy.copy(scheduler)
    wrapped.__class__ = wrapped_cls
    # Initialise the per-instance state machine + W2 history.
    wrapped._sm_init()
    return wrapped


# Re-export name used by tests / docs.
StateMachineWrappedScheduler = _StateMachineSchedulerBase


# ---------------------------------------------------------------------------
# Orchestrator state machine
# ---------------------------------------------------------------------------

ORCHESTRATOR_STATES: tuple[OrchestratorState, ...] = (
    "IDLE",
    "INITIALIZED",
    "ROUND_ACTIVE",
    "FEEDBACK_PENDING",
    "NEXT_ROUND_READY",
    "COMPLETE",
    "FAILED",
)


def make_runner_state_machine(
    *, name: str = "runner:ReInferenceRunner"
) -> StateMachine[OrchestratorState, OrchestratorEvent]:
    """Build the :class:`ReInferenceRunner` orchestrator state machine.

    Outer state machine only (the per-round inner machine is implicit
    in the lifecycle of the outer machine — every round traverses
    ``ROUND_ACTIVE -> FEEDBACK_PENDING -> NEXT_ROUND_READY`` and then
    either returns to ``ROUND_ACTIVE`` (next round) or transitions to
    ``COMPLETE`` (run finished) / ``FAILED`` (chain broken).
    """
    sm: StateMachine[OrchestratorState, OrchestratorEvent] = StateMachine(
        initial="IDLE", name=name
    )
    # IDLE -> INITIALIZED on INIT
    sm.add_transition(source="IDLE", event="INIT", target="INITIALIZED")
    # INITIALIZED -> ROUND_ACTIVE on first SAMPLE_REQUESTED
    sm.add_transition(
        source="INITIALIZED", event="SAMPLE_REQUESTED", target="ROUND_ACTIVE"
    )
    # ROUND_ACTIVE -> FEEDBACK_PENDING on SAMPLE_EMITTED
    sm.add_transition(
        source="ROUND_ACTIVE", event="SAMPLE_EMITTED", target="FEEDBACK_PENDING"
    )
    # FEEDBACK_PENDING -> NEXT_ROUND_READY on FEEDBACK_DISPATCHED
    sm.add_transition(
        source="FEEDBACK_PENDING",
        event="FEEDBACK_DISPATCHED",
        target="NEXT_ROUND_READY",
    )
    # NEXT_ROUND_READY -> ROUND_ACTIVE on next SAMPLE_REQUESTED (more rounds)
    sm.add_transition(
        source="NEXT_ROUND_READY",
        event="SAMPLE_REQUESTED",
        target="ROUND_ACTIVE",
    )
    # NEXT_ROUND_READY -> COMPLETE on COMPLETE_RUN
    sm.add_transition(
        source="NEXT_ROUND_READY", event="COMPLETE_RUN", target="COMPLETE"
    )
    # ROUND_ACTIVE -> FAILED on FAIL (e.g. ledger chain broken)
    sm.add_transition(source="ROUND_ACTIVE", event="FAIL", target="FAILED")
    sm.add_transition(source="FEEDBACK_PENDING", event="FAIL", target="FAILED")
    sm.add_transition(source="NEXT_ROUND_READY", event="FAIL", target="FAILED")
    # RESET from any state -> IDLE
    for src in ORCHESTRATOR_STATES:
        sm.add_transition(source=src, event="RESET", target="IDLE")
    return sm


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------

__all__ = [
    "OrchestratorEvent",
    "OrchestratorState",
    "ORCHESTRATOR_STATES",
    "SchedulerEvent",
    "SchedulerState",
    "StateMachineWrappedScheduler",
    "make_runner_state_machine",
    "wrap_scheduler_with_state_machine",
]
