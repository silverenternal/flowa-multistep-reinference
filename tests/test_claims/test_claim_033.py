"""CLM-033: Modern state machine library — generic + HSM + decorator.

Asserted by docs/CLAIMS.md:909-949.
The framework ships a stdlib-only state machine library that combines
a PEP-695 generic API (`class StateMachine[TState, TEvent]`), a
decorator-based transition DSL, hierarchical state machines with
shallow/deep history pseudo-states, parallel (orthogonal) regions,
byte-deterministic `TransitionLog` records, and DOT/Mermaid export.

We pin the public surface:
    1. `StateMachine` is generic over `[TState, TEvent]`.
    2. The decorator `on(event).to(state)` registers a transition.
    3. The `transitions` property yields the byte-deterministic log.
    4. `to_dot()` and `to_mermaid()` are exported.
"""
from __future__ import annotations

from adaptive_reflow.contracts.state_machine import (
    StateMachine,
    TransitionKind,
)


def test_claim_033_state_machine_class_is_generic() -> None:
    """StateMachine is generic over [TState, TEvent]."""
    assert hasattr(StateMachine, "__class_getitem__"), (
        "StateMachine must be generic (PEP 695 __class_getitem__)"
    )


def test_claim_033_state_machine_supports_decorator_dsl() -> None:
    """The decorator @on('event').to('state') registers a transition."""
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    @sm.on("start").to("running")
    def _on_start(_ctx):  # pragma: no cover -- transition handler
        return None

    assert "running" in sm.states(), "decorator-registered state missing"


def test_claim_033_transition_log_byte_deterministic() -> None:
    """Two identical transition sequences produce identical log."""
    sm: StateMachine[str, str] = StateMachine(initial="idle")

    @sm.on("go").to("running")
    def _h1(_ctx):  # pragma: no cover
        return None

    sm.send("go")
    log_a = list(sm.transitions)
    sm.reset()
    sm.send("go")
    log_b = list(sm.transitions)
    assert log_a == log_b, "transition log not byte-deterministic"


def test_claim_033_to_dot_and_to_mermaid_exported() -> None:
    """Both `to_dot` and `to_mermaid` are exported on StateMachine."""
    assert hasattr(StateMachine, "to_dot")
    assert hasattr(StateMachine, "to_mermaid")
    # TransitionKind Enum has the documented variants.
    assert TransitionKind.INTERNAL.value == "internal"
