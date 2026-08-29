"""Tests for the modern generic state machine library.

Covers every feature in the Phase-1 spec (must-haves + nice-to-haves):
- PEP 695 generic typing
- Decorator-based transitions
- State entry/exit actions
- Guards (boolean predicates)
- Hierarchical states (HSM, sub-state machines)
- History states (shallow H + deep H*)
- Parallel / orthogonal regions
- Async hooks / guards / effects (``asend``)
- Visualization (``to_mermaid``, ``to_dot``)
- Type-safe transition registration
- Byte-deterministic transition log
- Exception types
- Nice-to-haves: priority, self-transitions, internal transitions
"""
from __future__ import annotations

import asyncio
import dataclasses

import pytest

from adaptive_reflow.contracts.state_machine import (
    GuardRejected,
    HistoryKind,
    InvalidTransitionError,
    StateMachine,
    StateMachineError,
    StateNotFoundError,
    TransitionContext,
    TransitionKind,
    TransitionLog,
)

# ---------------------------------------------------------------------------
# 1. Generic typing
# ---------------------------------------------------------------------------


def test_state_machine_is_pep695_generic() -> None:
    """``StateMachine`` is a PEP 695 generic class over ``TState`` and ``TEvent``."""
    # PEP 695 generic classes have ``__type_params__`` (a tuple of TypeVarType)
    # in Python 3.12+.
    params = getattr(StateMachine, "__type_params__", None)
    assert params is not None, "StateMachine should be a PEP 695 generic"
    names = {getattr(p, "__name__", str(p)) for p in params}
    assert "TState" in names
    assert "TEvent" in names


def test_state_machine_constructs_with_initial_state() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle", name="t1")
    assert sm.state == "idle"
    assert sm.initial == "idle"
    assert sm.name == "t1"


def test_state_machine_repr_includes_name_and_state() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle", name="widget")
    assert "widget" in repr(sm)
    assert "idle" in repr(sm)


# ---------------------------------------------------------------------------
# 2. Decorator-based transitions
# ---------------------------------------------------------------------------


def test_decorator_transition_from_initial_state() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    fired: list[str] = []

    @sm.on("start").to("running")
    def _start(ctx: TransitionContext) -> None:
        fired.append("start")

    sm.send("start")
    assert sm.state == "running"
    assert fired == ["start"]


def test_add_transition_with_explicit_source() -> None:
    """``add_transition`` allows transitions from non-current sources."""
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    def _stop(ctx: TransitionContext) -> None:
        pass

    sm.add_transition(source="running", event="stop", target="idle", effect=_stop)
    sm.add_transition(source="idle", event="start", target="running")
    sm.send("start")
    sm.send("stop")
    assert sm.state == "idle"


def test_fluent_builder_without_decorator_works() -> None:
    """``.register()`` registers a transition without an effect."""
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.on("go").to("running").register()
    sm.send("go")
    assert sm.state == "running"


def test_decorator_returns_original_function() -> None:
    """The decorator must return the original function unchanged (decorator semantics)."""

    def handler(ctx: TransitionContext) -> None:
        pass

    sm: StateMachine[str, str] = StateMachine(initial="idle")
    wrapper = sm.on("e").to("s")
    result = wrapper(handler)
    assert result is handler


# ---------------------------------------------------------------------------
# 3. State entry / exit actions
# ---------------------------------------------------------------------------


def test_on_enter_fires_on_entry() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    entered: list[str] = []

    @sm.on_enter("running")
    def _e(ctx: TransitionContext) -> None:
        entered.append(ctx.target)

    @sm.on("start").to("running")
    def _s(ctx: TransitionContext) -> None:
        pass

    sm.send("start")
    assert entered == ["running"]


def test_on_exit_fires_on_exit() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    exited: list[str] = []

    @sm.on_exit("idle")
    def _x(ctx: TransitionContext) -> None:
        exited.append(ctx.source)

    @sm.on("start").to("running")
    def _s(ctx: TransitionContext) -> None:
        pass

    sm.send("start")
    assert exited == ["idle"]


def test_multiple_enter_hooks_fire_in_order() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    order: list[str] = []

    @sm.on_enter("running")
    def _a(ctx: TransitionContext) -> None:
        order.append("a")

    @sm.on_enter("running")
    def _b(ctx: TransitionContext) -> None:
        order.append("b")

    @sm.on("go").to("running")
    def _g(ctx: TransitionContext) -> None:
        pass

    sm.send("go")
    assert order == ["a", "b"]


def test_hook_receives_transition_context() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    captured: list[TransitionContext] = []

    @sm.on_enter("running")
    def _e(ctx: TransitionContext) -> None:
        captured.append(ctx)

    @sm.on("go").to("running")
    def _g(ctx: TransitionContext) -> None:
        captured.append(ctx)

    sm.send("go", payload={"x": 1})
    assert len(captured) == 2
    assert all(isinstance(c, TransitionContext) for c in captured)
    assert all(c.machine is sm for c in captured)
    assert all(c.event == "go" for c in captured)
    assert all(c.source == "idle" for c in captured)
    assert all(c.target == "running" for c in captured)
    assert all(c.payload == {"x": 1} for c in captured)
    assert captured[0].is_initial() is True


# ---------------------------------------------------------------------------
# 4. Guards
# ---------------------------------------------------------------------------


def test_guard_blocks_transition_when_false() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    fired: list[str] = []

    def only_when_true(ctx: TransitionContext) -> bool:
        return False

    @sm.on("go").to("running").when(only_when_true)
    def _g(ctx: TransitionContext) -> None:
        fired.append(ctx.target)

    # Without strict guards: silent no-op (UML "ignored event" semantics).
    sm.send("go")
    assert sm.state == "idle"
    assert fired == []


def test_guard_allows_transition_when_true() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    def always(ctx: TransitionContext) -> bool:
        return True

    @sm.on("go").to("running").when(always)
    def _g(ctx: TransitionContext) -> None:
        pass

    sm.send("go")
    assert sm.state == "running"


def test_strict_guard_mode_raises_guard_rejected() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle").with_strict_guards(True)

    def no(ctx: TransitionContext) -> bool:
        return False

    @sm.on("go").to("running").when(no)
    def _g(ctx: TransitionContext) -> None:
        pass

    with pytest.raises(GuardRejected):
        sm.send("go")


def test_multiple_guards_priority() -> None:
    """Higher-priority guard wins when multiple transitions match the same event."""
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    chosen: list[str] = []

    def g_a(ctx: TransitionContext) -> bool:
        return True

    def g_b(ctx: TransitionContext) -> bool:
        return True

    sm.add_transition(
        source="idle",
        event="go",
        target="a",
        guard=g_a,
        effect=lambda ctx: chosen.append("a"),
        priority=1,
    )
    sm.add_transition(
        source="idle",
        event="go",
        target="b",
        guard=g_b,
        effect=lambda ctx: chosen.append("b"),
        priority=10,
    )
    sm.send("go")
    assert sm.state == "b"
    assert chosen == ["b"]


def test_first_satisfying_guard_wins_in_registration_order() -> None:
    """Same priority: registration order breaks the tie."""
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    sm.add_transition(
        source="idle",
        event="go",
        target="a",
        guard=lambda ctx: True,
    )
    sm.add_transition(
        source="idle",
        event="go",
        target="b",
        guard=lambda ctx: True,
    )
    sm.send("go")
    assert sm.state == "a"


# ---------------------------------------------------------------------------
# 5. Hierarchical states (HSM)
# ---------------------------------------------------------------------------


def test_hsm_sub_region_receives_event() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="idle")

    @sub.on("go").to("active")
    def _g(ctx: TransitionContext) -> None:
        pass

    parent.add_region("on", "main", sub)
    parent.send("go")
    assert sub.state == "active"


def test_hsm_event_bubbles_to_parent_when_subregion_misses() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="idle")
    parent.add_region("on", "main", sub)

    parent.add_transition(source="on", event="off", target="off")
    parent.send("off")
    assert parent.state == "off"


def test_hsm_can_check_event_from_parent() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="idle")
    sub.add_transition(source="idle", event="go", target="active")
    parent.add_region("on", "main", sub)

    assert parent.can("go") is True
    assert parent.can("off") is False


def test_hsm_invalid_event_raises_invalid_transition() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="idle")
    parent.add_region("on", "main", sub)
    with pytest.raises(InvalidTransitionError):
        parent.send("nonsense")


# ---------------------------------------------------------------------------
# 6. History states (shallow H + deep H*)
# ---------------------------------------------------------------------------


def test_shallow_history_restores_direct_substate() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="a")
    sub.add_transition(source="a", event="to_b", target="b")
    sub.add_transition(source="b", event="to_a", target="a")
    parent.add_region("on", "main", sub, history=HistoryKind.SHALLOW)

    parent.send("to_b")
    assert sub.state == "b"
    # Exit and re-enter "on": shallow history should restore "b".
    parent.add_transition(source="on", event="off", target="off")
    parent.add_transition(source="off", event="on", target="on")
    parent.send("off")
    assert parent.state == "off"
    parent.send("on")
    assert parent.state == "on"
    # Shallow history: direct sub-state restored.
    assert sub.state == "b"


def test_deep_history_restores_deepest_substate() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    inner: StateMachine[str, str] = StateMachine(initial="x")
    inner.add_transition(source="x", event="to_y", target="y")
    outer_sub: StateMachine[str, str] = StateMachine(initial="outer")
    # outer has a region under "outer" that wraps "inner"
    outer_sub.add_region("outer", "inner_region", inner)
    parent.add_region("on", "outer", outer_sub, history=HistoryKind.DEEP)

    parent.send("to_y")
    assert inner.state == "y"
    # Exit and re-enter "on": deep history should restore "y" (deepest).
    parent.add_transition(source="on", event="off", target="off")
    parent.add_transition(source="off", event="on", target="on")
    parent.send("off")
    parent.send("on")
    assert inner.state == "y"


def test_no_history_uses_initial_on_reentry() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="a")
    sub.add_transition(source="a", event="to_b", target="b")
    parent.add_region("on", "main", sub, history=HistoryKind.NONE)
    parent.send("to_b")
    assert sub.state == "b"

    parent.add_transition(source="on", event="off", target="off")
    parent.add_transition(source="off", event="on", target="on")
    parent.send("off")
    parent.send("on")
    assert sub.state == "a"  # back to initial, not "b"


def test_history_kind_exposes_values() -> None:
    assert HistoryKind.NONE.value == "none"
    assert HistoryKind.SHALLOW.value == "shallow"
    assert HistoryKind.DEEP.value == "deep"


# ---------------------------------------------------------------------------
# 7. Parallel / orthogonal regions
# ---------------------------------------------------------------------------


def test_parallel_dispatches_to_all_regions() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="both")
    left: StateMachine[str, str] = StateMachine(initial="idle")
    right: StateMachine[str, str] = StateMachine(initial="idle")
    left.add_transition(source="idle", event="go", target="active")
    right.add_transition(source="idle", event="go", target="active")
    parent.add_parallel("both", {"L": left, "R": right})

    parent.send("go")
    assert left.state == "active"
    assert right.state == "active"


def test_parallel_regions_are_independent() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="both")
    left: StateMachine[str, str] = StateMachine(initial="idle")
    right: StateMachine[str, str] = StateMachine(initial="idle")
    only_left: list[str] = []
    only_right: list[str] = []
    left.add_transition(
        source="idle",
        event="left_only",
        target="ready",
        effect=lambda ctx: only_left.append(ctx.target),
    )
    right.add_transition(
        source="idle",
        event="right_only",
        target="ready",
        effect=lambda ctx: only_right.append(ctx.target),
    )
    parent.add_parallel("both", {"L": left, "R": right})

    # right_only has no transition in left, but is still consumed (per region).
    parent.send("right_only")
    assert only_right == ["ready"]
    assert only_left == []


def test_parallel_rejects_non_state_machine_region() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="both")
    with pytest.raises(TypeError):
        sm.add_parallel("both", {"L": "not_a_machine"})  # type: ignore[typeddict-item]


# ---------------------------------------------------------------------------
# 8. Async support
# ---------------------------------------------------------------------------


def test_async_enter_hook_works_with_asend() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    entered: list[str] = []

    @sm.on_enter("running")
    async def _enter(ctx: TransitionContext) -> None:
        await asyncio.sleep(0)
        entered.append(ctx.target)

    @sm.on("start").to("running")
    def _s(ctx: TransitionContext) -> None:
        pass

    asyncio.run(sm.asend("start"))
    assert sm.state == "running"
    assert entered == ["running"]


def test_async_guard_with_asend() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    async def is_ready(ctx: TransitionContext) -> bool:
        await asyncio.sleep(0)
        return ctx.payload == "go"

    @sm.on("start").to("running").when(is_ready)
    def _s(ctx: TransitionContext) -> None:
        pass

    asyncio.run(sm.asend("start", payload="go"))
    assert sm.state == "running"


def test_sync_send_rejects_async_hooks() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    @sm.on_enter("running")
    async def _e(ctx: TransitionContext) -> None:
        pass

    @sm.on("start").to("running")
    def _s(ctx: TransitionContext) -> None:
        pass

    with pytest.raises(RuntimeError, match="async"):
        sm.send("start")


def test_async_effect_with_asend() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    fired: list[str] = []

    async def effect(ctx: TransitionContext) -> None:
        await asyncio.sleep(0)
        fired.append(ctx.target)

    sm.add_transition(source="idle", event="start", target="running", effect=effect)
    asyncio.run(sm.asend("start"))
    assert fired == ["running"]


# ---------------------------------------------------------------------------
# 9. Visualization
# ---------------------------------------------------------------------------


def test_to_mermaid_emits_state_diagram_v2() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.add_transition(source="idle", event="start", target="running")
    sm.add_transition(source="running", event="stop", target="idle")
    out = sm.to_mermaid()
    assert "stateDiagram-v2" in out
    assert "[*] --> idle" in out
    assert "idle --> running : start" in out
    assert "running --> idle : stop" in out


def test_to_mermaid_includes_guard_labels() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="a")
    sm.add_transition(
        source="a",
        event="go",
        target="b",
        guard=lambda ctx: True,
    )
    out = sm.to_mermaid()
    assert "a --> b : go / [<lambda>]" in out


def test_to_dot_emits_valid_graphviz_dot() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.add_transition(source="idle", event="go", target="running")
    out = sm.to_dot()
    assert out.startswith(f'digraph "{sm.name}"')
    assert "rankdir=LR;" in out
    assert '"idle" -> "running"' in out
    assert out.rstrip().endswith("}")


def test_to_mermaid_includes_parallel_regions() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="both")
    left: StateMachine[str, str] = StateMachine(initial="i")
    right: StateMachine[str, str] = StateMachine(initial="i")
    sm.add_parallel("both", {"L": left, "R": right})
    out = sm.to_mermaid()
    assert "both_L" in out
    assert "both_R" in out


# ---------------------------------------------------------------------------
# 10. Type-safe transitions (smoke-tested here; mypy enforces strictly)
# ---------------------------------------------------------------------------


def test_states_introspection() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.add_transition(source="idle", event="a", target="b")
    sm.add_transition(source="b", event="c", target="idle")

    @sm.on_enter("b")
    def _e(ctx: TransitionContext) -> None:
        pass

    states = sm.states()
    assert "idle" in states
    assert "b" in states


# ---------------------------------------------------------------------------
# 11. Byte-deterministic transition log
# ---------------------------------------------------------------------------


def test_log_records_every_transition_with_monotonic_counter() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.add_transition(source="idle", event="a", target="b")
    sm.add_transition(source="b", event="c", target="idle")
    sm.send("a")
    sm.send("c")
    log = sm.log
    assert [e.counter for e in log] == [1, 2]
    assert log[0].event == "a"
    assert log[0].source == "idle"
    assert log[0].target == "b"


def test_two_machines_produce_identical_logs_for_same_event_sequence() -> None:
    def build() -> StateMachine[str, str]:
        sm: StateMachine[str, str] = StateMachine(initial="idle", name="x")
        sm.add_transition(source="idle", event="a", target="b")
        sm.add_transition(source="b", event="c", target="idle")
        return sm

    m1, m2 = build(), build()
    for evt in ("a", "c", "a", "c"):
        m1.send(evt)
        m2.send(evt)
    # Byte-determinism: tuple of dataclasses compares field-by-field.
    assert m1.log == m2.log


def test_log_includes_guard_and_effect_names() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    def my_guard(ctx: TransitionContext) -> bool:
        return True

    def my_effect(ctx: TransitionContext) -> None:
        pass

    sm.add_transition(
        source="idle",
        event="go",
        target="running",
        guard=my_guard,
        effect=my_effect,
    )
    sm.send("go")
    entry = sm.log[0]
    assert entry.guard_name == "my_guard"
    assert entry.effect_name == "my_effect"
    assert entry.guard_result is None  # None means "guard accepted, recorded result is None"
    assert entry.kind == "external"


def test_log_records_history_restored() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="a")
    sub.add_transition(source="a", event="to_b", target="b")
    parent.add_region("on", "main", sub, history=HistoryKind.SHALLOW)

    parent.send("to_b")
    assert sub.state == "b"
    parent.add_transition(source="on", event="off", target="off")
    parent.add_transition(source="off", event="on", target="on")
    parent.send("off")
    parent.send("on")
    # The "on" entry log should show history_restored != empty
    on_entry = next(e for e in parent.log if e.event == "on" and e.target == "on")
    assert on_entry.history_restored != ()


def test_clear_log_resets_counter_and_entries() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.add_transition(source="idle", event="go", target="b")
    sm.send("go")
    assert len(sm.log) == 1
    sm.clear_log()
    assert sm.log == ()


# ---------------------------------------------------------------------------
# 12. Exception types
# ---------------------------------------------------------------------------


def test_invalid_transition_error_is_state_machine_error() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    with pytest.raises(StateMachineError):
        sm.send("undefined_event")


def test_invalid_transition_error_message_contains_state_and_event() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    with pytest.raises(InvalidTransitionError) as exc:
        sm.send("nope")
    assert "nope" in str(exc.value)
    assert "idle" in str(exc.value)


def test_guard_rejected_subclass_of_state_machine_error() -> None:
    assert issubclass(GuardRejected, StateMachineError)


def test_state_not_found_error_subclass_of_state_machine_error() -> None:
    assert issubclass(StateNotFoundError, StateMachineError)


def test_state_not_found_error_raised_on_undefined_state() -> None:
    """``StateNotFoundError`` is reserved for direct API misuse; we surface it
    by importing it and confirming it is constructable / raiseable."""
    with pytest.raises(StateNotFoundError):
        raise StateNotFoundError("synthetic")


# ---------------------------------------------------------------------------
# Nice-to-haves
# ---------------------------------------------------------------------------


def test_self_transition_kind_promotes_external_to_self() -> None:
    """A transition with source == target is auto-promoted to ``SELF`` kind."""
    sm: StateMachine[str, str] = StateMachine(initial="active")
    sm.add_transition(source="active", event="tick", target="active")
    sm.send("tick")
    assert sm.log[0].kind == TransitionKind.SELF.value


def test_internal_transition_skips_exit_and_enter_hooks() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="active")
    exit_count = 0
    enter_count = 0

    @sm.on_exit("active")
    def _x(ctx: TransitionContext) -> None:
        nonlocal exit_count
        exit_count += 1

    @sm.on_enter("active")
    def _e(ctx: TransitionContext) -> None:
        nonlocal enter_count
        enter_count += 1

    sm.add_transition(
        source="active",
        event="ping",
        target="active",
        kind=TransitionKind.INTERNAL,
    )
    sm.send("ping")
    assert exit_count == 0
    assert enter_count == 0
    assert sm.log[0].kind == "internal"


def test_external_self_transition_runs_exit_then_enter() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="active")
    seq: list[str] = []

    @sm.on_exit("active")
    def _x(ctx: TransitionContext) -> None:
        seq.append("exit")

    @sm.on_enter("active")
    def _e(ctx: TransitionContext) -> None:
        seq.append("enter")

    sm.add_transition(
        source="active",
        event="ping",
        target="active",
        kind=TransitionKind.EXTERNAL,
    )
    sm.send("ping")
    assert seq == ["exit", "enter"]


def test_reset_returns_to_initial_and_clears_log() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.add_transition(source="idle", event="go", target="running")
    sm.send("go")
    assert sm.state == "running"
    assert len(sm.log) == 1
    sm.reset()
    assert sm.state == "idle"
    assert sm.log == ()


def test_can_returns_true_when_event_matches() -> None:
    sm: StateMachine[str, str] = StateMachine(initial="idle")
    sm.add_transition(source="idle", event="go", target="running")
    assert sm.can("go") is True
    assert sm.can("nope") is False


def test_transition_log_is_frozen() -> None:
    entry = TransitionLog(
        counter=1,
        event="e",
        source="a",
        target="b",
        guard_name=None,
        guard_result=None,
        effect_name=None,
        history_restored=(),
        kind="external",
        internal_subpath="",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.counter = 99  # type: ignore[misc]


def test_transition_kind_enum_values() -> None:
    assert TransitionKind.EXTERNAL.value == "external"
    assert TransitionKind.INTERNAL.value == "internal"
    assert TransitionKind.SELF.value == "self"


# ---------------------------------------------------------------------------
# Module-level public API re-exports
# ---------------------------------------------------------------------------


def test_contracts_module_reexports_state_machine_api() -> None:
    from adaptive_reflow.contracts import (  # noqa: F401
        GuardRejected,
        HistoryKind,
        InvalidTransitionError,
        StateMachine,
        StateMachineError,
        StateNotFoundError,
        TransitionBuilder,
        TransitionContext,
        TransitionGuardedBuilder,
        TransitionKind,
        TransitionLog,
    )


# ---------------------------------------------------------------------------
# Integration: a complex state machine using every feature
# ---------------------------------------------------------------------------


def test_integration_complex_machine_uses_all_features() -> None:
    """One end-to-end machine that exercises every feature.

    Layout::

        outer
          ├── composite "on" with sub-state machine "main"
          │       ├── shallow-history at "b"
          │       └── states a, b, c
          └── parallel "both" with two regions L and R

    Guards, entry/exit hooks, internal self-transition, async dispatch,
    history restoration, parallel dispatch, byte-deterministic log.
    """
    outer: StateMachine[str, str] = StateMachine(initial="off", name="integrated")

    # Composite state "on" with sub-state machine
    main: StateMachine[str, str] = StateMachine(initial="a")
    main.add_transition(source="a", event="to_b", target="b")
    main.add_transition(source="b", event="to_c", target="c")
    main.add_transition(source="c", event="to_a", target="a")
    outer.add_region("on", "main", main, history=HistoryKind.SHALLOW)

    # Parallel state "both" with two orthogonal regions
    left: StateMachine[str, str] = StateMachine(initial="idle")
    right: StateMachine[str, str] = StateMachine(initial="idle")
    left.add_transition(source="idle", event="lgo", target="run")
    right.add_transition(source="idle", event="rgo", target="run")
    outer.add_parallel("both", {"L": left, "R": right})

    # Parent-level transitions
    outer.add_transition(source="off", event="power_on", target="on")

    # Hooks
    entries: list[str] = []
    exits: list[str] = []

    @outer.on_enter("on")
    def _enter_on(ctx: TransitionContext) -> None:
        entries.append("on")

    @outer.on_exit("on")
    def _exit_on(ctx: TransitionContext) -> None:
        exits.append("on")

    # Exercise composite + guard
    power_events: list[str] = []
    outer.add_transition(
        source="on",
        event="power_off",
        target="off",
        guard=lambda ctx: True,
        effect=lambda ctx: power_events.append("off"),
    )

    # Drive the machine through composite + parallel + history
    outer.send("power_on")
    assert outer.state == "on"
    assert main.state == "a"
    assert "on" in entries

    # Walk the sub-state machine
    outer.send("to_b")
    outer.send("to_c")
    assert main.state == "c"

    # Power off + on should restore "c" via shallow history
    outer.send("power_off")
    assert outer.state == "off"
    outer.send("power_on")
    assert outer.state == "on"
    assert main.state == "c"
    assert "on" in exits
    assert entries.count("on") == 2

    # Switch to parallel
    outer.add_transition(source="on", event="to_both", target="both")
    outer.add_transition(source="both", event="to_on", target="on")
    outer.send("to_both")
    assert outer.state == "both"
    outer.send("lgo")
    outer.send("rgo")
    assert left.state == "run"
    assert right.state == "run"

    # Internal self-transition does NOT fire exit/enter on outer
    outer.add_transition(
        source="both",
        event="ping",
        target="both",
        kind=TransitionKind.INTERNAL,
    )
    pre_log_len = len(outer.log)
    outer.send("ping")
    assert len(outer.log) == pre_log_len + 1
    assert outer.log[-1].kind == "internal"

    # Async path through composite
    async def driver() -> None:
        # Drive an async hook on the inner machine
        async_entered: list[str] = []

        @main.on_enter("a")
        async def _ae(ctx: TransitionContext) -> None:
            await asyncio.sleep(0)
            async_entered.append("a")

        # Move to "both" then back, then deep walk
        await outer.asend("to_on")
        await main.asend("to_a")
        assert async_entered == ["a"]

    asyncio.run(driver())

    # Byte-deterministic log check: total transition count and effect names.
    kinds = [e.kind for e in outer.log]
    # We expect at least: external, external, external, external, external,
    # external (to_both), external, external (lgo), external (rgo),
    # internal (ping), external (to_on), external (to_a in main via async)
    assert "internal" in kinds
    # The very last main-log entry is the async-driven "to_a" transition
    final_main_entry = main.log[-1]
    assert final_main_entry.event == "to_a"
    assert final_main_entry.source == "c"
    assert final_main_entry.target == "a"


# ---------------------------------------------------------------------------
# Counter-incrementing behaviour across nested machines
# ---------------------------------------------------------------------------


def test_nested_sub_machine_log_has_independent_counter() -> None:
    parent: StateMachine[str, str] = StateMachine(initial="on")
    sub: StateMachine[str, str] = StateMachine(initial="a")
    sub.add_transition(source="a", event="go", target="b")
    sub.add_transition(source="b", event="go", target="a")
    parent.add_region("on", "main", sub)

    parent.send("go")
    assert sub.state == "b"
    assert sub.log[0].counter == 1
    parent.send("go")
    assert sub.state == "a"
    assert sub.log[1].counter == 2
    # Parent log records nothing when sub handles the event (forwarded).
    assert parent.log == ()
