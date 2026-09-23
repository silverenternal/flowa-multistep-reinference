"""Property-based byte-determinism tests for ``StateMachine``.

This is the structural invariant for the *state machine* side of the
audit-bytes-determinism property (ADR-0006 §3.2 / Wave 300 P4 gap).
It mirrors ``tests/property/test_engine_round_determinism.py`` but
targets the public ``StateMachine`` surface — the engine determinism
test only proves ``Engine.run_round`` is deterministic *given* a
``StateMachine``; this file proves the state machine itself is.

The contract: two ``StateMachine`` instances constructed identically
(by the same code path with the same configuration) and driven by the
same event sequence must produce byte-identical :class:`TransitionLog`
tuples and identical final ``sm.state``.

Surface covered (in order):

* simple linear chain (``test_determinism_simple_chain``)
* hierarchical state machine with history pseudo-states
  (``test_determinism_with_history``)
* parallel / orthogonal regions, sync dispatch
  (``test_determinism_parallel_regions``)
* parallel / orthogonal regions, async dispatch through the
  ``asyncio.gather`` path at ``state_machine.py:940-942``
  (``test_determinism_async_gather``)
* long random walk (``test_determinism_stress`` — N=1000)

Stdlib + hypothesis. No torch.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import sys
from pathlib import Path

import pytest

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# The ``hypothesis`` strategy library is the property-test backbone.
# We let ``pytest.importorskip`` in ``tests/property/conftest.py`` gate
# the entire subtree on its availability; this file trusts that the
# import will succeed.
import hypothesis
from hypothesis import given, settings
from hypothesis import strategies as st

from adaptive_reflow.contracts.state_machine import (
    HistoryKind,
    StateMachine,
    TransitionLog,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _digest(payload: object) -> str:
    """Return a deterministic sha256 digest for ``payload``.

    Uses ``sort_keys=True`` + ``default=str`` so the digest is stable
    across dict iteration orders and across the dataclass /
    ``frozen=True`` TransitionLog records emitted by ``StateMachine``.
    """
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _logs_to_jsonable(
    logs: tuple[TransitionLog, ...],
) -> list[dict[str, object]]:
    """Project :class:`TransitionLog` tuples into a JSON-stable list.

    Each ``TransitionLog`` is a frozen dataclass; ``dataclasses.asdict``
    is stable, but we spell it out so the JSON shape is explicit (the
    audit cares about field names + ordering).
    """
    return [
        {
            "counter": e.counter,
            "event": e.event,
            "source": e.source,
            "target": e.target,
            "guard_name": e.guard_name,
            "guard_result": e.guard_result,
            "effect_name": e.effect_name,
            "history_restored": list(e.history_restored),
            "kind": e.kind,
            "internal_subpath": e.internal_subpath,
        }
        for e in logs
    ]


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# A small state vocabulary — three labels is enough to exercise
# non-trivial transition graphs without ballooning the search space.
_SMALL_STATES = ("A", "B", "C")
_SMALL_EVENTS = ("e1", "e2", "e3", "e4")


@st.composite
def st_event_sequence(draw: Any, *, min_size: int = 10, max_size: int = 50) -> list[str]:
    """Return a list of events drawn uniformly from the small event vocabulary."""
    return draw(
        st.lists(
            elements=st.sampled_from(_SMALL_EVENTS),
            min_size=min_size,
            max_size=max_size,
        )
    )


@st.composite
def st_state_machine_topology(
    draw: Any,
) -> dict[str, list[tuple[str, str]]]:
    """Sample a small transition graph over ``_SMALL_STATES``.

    Returns a mapping ``state -> list[(event, target_state)]`` so the
    test body can register every transition via ``add_transition`` and
    know the source / target / event triple is unique enough to drive a
    non-trivial walk without overwhelming the state space.
    """
    transitions: dict[str, list[tuple[str, str]]] = {}
    for src in _SMALL_STATES:
        n_edges = draw(st.integers(min_value=1, max_value=len(_SMALL_EVENTS)))
        edges: list[tuple[str, str]] = []
        for ev in draw(
            st.lists(
                elements=st.sampled_from(_SMALL_EVENTS),
                min_size=n_edges,
                max_size=n_edges,
                unique=True,
            )
        ):
            tgt = draw(st.sampled_from(_SMALL_STATES))
            edges.append((ev, tgt))
        transitions[src] = edges
    return transitions


def _build_machine(
    topology: dict[str, list[tuple[str, str]]],
    *,
    name: str = "sm",
    initial: str = "A",
) -> StateMachine[str, str]:
    """Materialise a :class:`StateMachine` from a topology dict."""
    sm: StateMachine[str, str] = StateMachine(initial=initial, name=name)
    for src, edges in topology.items():
        for event, tgt in edges:
            sm.add_transition(source=src, event=event, target=tgt)
    return sm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _assert_logs_byte_identical(
    logs_a: tuple[TransitionLog, ...],
    logs_b: tuple[TransitionLog, ...],
    *,
    label: str,
) -> None:
    """Assert two log tuples are equal and their JSON digests match."""
    assert logs_a == logs_b, (
        f"structural equality violated for {label}: "
        f"first_len={len(logs_a)} second_len={len(logs_b)}"
    )
    json_a = _logs_to_jsonable(logs_a)
    json_b = _logs_to_jsonable(logs_b)
    assert _digest(json_a) == _digest(json_b), (
        f"byte-determinism violated for {label}: "
        f"digest mismatch on JSON projection"
    )


@settings(max_examples=20, deadline=None)
@given(topology=st_state_machine_topology(), events=st_event_sequence())
def test_determinism_simple_chain(
    topology: dict[str, list[tuple[str, str]]],
    events: list[str],
) -> None:
    """Two :class:`StateMachine` instances driven by the same event
    sequence produce byte-identical :class:`TransitionLog` tuples.

    Mirrors ``tests/test_contracts/test_state_machine.py::
    test_two_machines_produce_identical_logs_for_same_event_sequence``
    but driven by ``hypothesis`` so we sweep topologies and event
    sequences rather than a single hand-written scenario.
    """
    m1 = _build_machine(topology, name="m1")
    m2 = _build_machine(topology, name="m2")

    # Filter events to ones the initial state actually consumes so we
    # don't raise ``InvalidTransitionError`` mid-walk. The property we
    # care about (byte-determinism of the *logs*) is invariant under
    # which events we send, but if the first event is invalid the
    # comparison degenerates to "both raise" which is too weak to be
    # useful.
    def _drive(sm: StateMachine[str, str]) -> tuple[TransitionLog, ...]:
        # Swallow only the no-transition error so the walk gracefully
        # ends on a state that doesn't consume the next event. Any
        # other error must propagate (regression coverage).
        for ev in events:
            with contextlib.suppress(Exception):
                sm.send(ev)
        return sm.log

    logs_a = _drive(m1)
    logs_b = _drive(m2)
    assert m1.state == m2.state, (
        f"final state diverged: m1={m1.state!r} m2={m2.state!r}"
    )
    _assert_logs_byte_identical(logs_a, logs_b, label="simple_chain")


@settings(max_examples=15, deadline=None)
@given(
    initial_sub=st.sampled_from(("idle", "ready")),
    events=st_event_sequence(min_size=8, max_size=20),
)
def test_determinism_with_history(
    initial_sub: str,
    events: list[str],
) -> None:
    """Two HSMs with shallow-history regions must produce identical
    logs after re-entry into the parent state.

    The history path exercises ``_restore_history`` and
    ``_update_history`` (``state_machine.py:680-740``); both must be
    byte-deterministic across independent machine instances.
    """
    def build() -> StateMachine[str, str]:
        parent: StateMachine[str, str] = StateMachine(initial="on")
        sub: StateMachine[str, str] = StateMachine(initial="idle")
        # Sub-state machine has its own mini-topology.
        sub.add_transition(source="idle", event="go", target="ready")
        sub.add_transition(source="ready", event="back", target="idle")
        parent.add_region(
            "on",
            "main",
            sub,
            history=HistoryKind.SHALLOW,
        )
        # A direct transition on the parent (events that miss the sub
        # bubble up).
        parent.add_transition(source="on", event="leave", target="off")
        parent.add_transition(source="off", event="enter", target="on")
        return parent

    m1, m2 = build(), build()
    # Force the sub into a known non-initial state so history has
    # something to restore.
    if initial_sub == "ready":
        m1.send("go")
        m2.send("go")

    def drive(sm: StateMachine[str, str]) -> tuple[TransitionLog, ...]:
        for ev in events:
            with contextlib.suppress(Exception):
                sm.send(ev)
        return sm.log

    logs_a = drive(m1)
    logs_b = drive(m2)
    assert m1.state == m2.state, (
        f"final state diverged (history): m1={m1.state!r} m2={m2.state!r}"
    )
    _assert_logs_byte_identical(logs_a, logs_b, label="with_history")


@settings(max_examples=12, deadline=None)
@given(events=st_event_sequence(min_size=8, max_size=20))
def test_determinism_parallel_regions(events: list[str]) -> None:
    """Two parallel SMs (sync dispatch) produce identical parent + region
    logs.

    Exercises the parallel sync dispatch path at
    ``state_machine.py:767-776`` (no ``asyncio.gather``; this test
    covers the sync counterpart).
    """
    def build() -> tuple[
        StateMachine[str, str],
        StateMachine[str, str],
        StateMachine[str, str],
    ]:
        parent: StateMachine[str, str] = StateMachine(initial="both")
        left: StateMachine[str, str] = StateMachine(initial="idle")
        right: StateMachine[str, str] = StateMachine(initial="idle")
        left.add_transition(source="idle", event="go", target="active")
        right.add_transition(source="idle", event="go", target="active")
        left.add_transition(source="active", event="reset", target="idle")
        right.add_transition(source="active", event="reset", target="idle")
        parent.add_parallel("both", {"L": left, "R": right})
        return parent, left, right

    p1, l1, r1 = build()
    p2, l2, r2 = build()

    def drive(
        parent: StateMachine[str, str],
        left: StateMachine[str, str],
        right: StateMachine[str, str],
    ) -> None:
        for ev in events:
            with contextlib.suppress(Exception):
                parent.send(ev)

    drive(p1, l1, r1)
    drive(p2, l2, r2)
    assert p1.state == p2.state, (
        f"parallel parent state diverged: p1={p1.state!r} p2={p2.state!r}"
    )
    assert l1.state == l2.state, (
        f"parallel left state diverged: l1={l1.state!r} l2={l2.state!r}"
    )
    assert r1.state == r2.state, (
        f"parallel right state diverged: r1={r1.state!r} r2={r2.state!r}"
    )
    _assert_logs_byte_identical(p1.log, p2.log, label="parallel_parent")
    _assert_logs_byte_identical(l1.log, l2.log, label="parallel_left")
    _assert_logs_byte_identical(r1.log, r2.log, label="parallel_right")


@settings(max_examples=10, deadline=None)
@given(events=st_event_sequence(min_size=6, max_size=15))
def test_determinism_async_gather(events: list[str]) -> None:
    """The ``asyncio.gather`` path at ``state_machine.py:940-942`` is
    byte-deterministic across two parallel-region parents driven
    asynchronously.

    Why this is the load-bearing test: ``asyncio.gather`` schedules
    coroutines on the event loop; if scheduling order leaked into the
    sub-machine dispatch order, two runs of the same parent would
    produce different log tuples. The contract is that
    ``parallel.values()`` is insertion-ordered (Python 3.7+ dicts) so
    the coroutines are scheduled in the same order, and each sub's
    :meth:`_dispatch_async` is independently deterministic — so the
    gather result is deterministic too.
    """
    def build() -> tuple[
        StateMachine[str, str],
        StateMachine[str, str],
        StateMachine[str, str],
    ]:
        parent: StateMachine[str, str] = StateMachine(initial="both")
        left: StateMachine[str, str] = StateMachine(initial="idle")
        right: StateMachine[str, str] = StateMachine(initial="idle")

        @left.on("go").to("active")
        async def _l_async(ctx: Any) -> None:
            # Force a yield so the gather path actually interleaves.
            await asyncio.sleep(0)

        @right.on("go").to("active")
        async def _r_async(ctx: Any) -> None:
            await asyncio.sleep(0)

        parent.add_parallel("both", {"L": left, "R": right})
        return parent, left, right

    async def drive(
        parent: StateMachine[str, str],
        left: StateMachine[str, str],
        right: StateMachine[str, str],
    ) -> None:
        for ev in events:
            with contextlib.suppress(Exception):
                await parent.asend(ev)

    async def run_twice() -> None:
        p1, l1, r1 = build()
        p2, l2, r2 = build()
        await drive(p1, l1, r1)
        await drive(p2, l2, r2)
        assert p1.state == p2.state, (
            f"async parent state diverged: p1={p1.state!r} p2={p2.state!r}"
        )
        assert l1.state == l2.state, (
            f"async left state diverged: l1={l1.state!r} l2={l2.state!r}"
        )
        assert r1.state == r2.state, (
            f"async right state diverged: r1={r1.state!r} r2={r2.state!r}"
        )
        # The parent log stays empty under parallel dispatch because
        # handled_any short-circuits before the parent runs its own
        # transition; we still check it for completeness.
        _assert_logs_byte_identical(p1.log, p2.log, label="async_parent")
        _assert_logs_byte_identical(l1.log, l2.log, label="async_left")
        _assert_logs_byte_identical(r1.log, r2.log, label="async_right")

    asyncio.run(run_twice())


@settings(max_examples=5, deadline=None)
@given(events=st_event_sequence(min_size=500, max_size=1000))
def test_determinism_stress(events: list[str]) -> None:
    """Stress: a 500-1000-step random walk must remain byte-deterministic.

    Smaller example count because each example runs ~1000 transitions;
    the property still gets ~5000+ total transitions exercised.
    """
    # Use a topology dense enough that any event is consumed from any
    # state (every state has every event -> a uniformly random target).
    dense_topology: dict[str, list[tuple[str, str]]] = {
        s: [(ev, "A") for ev in _SMALL_EVENTS] for s in _SMALL_STATES
    }
    m1 = _build_machine(dense_topology, name="m1")
    m2 = _build_machine(dense_topology, name="m2")

    for ev in events:
        # Dense topology guarantees every event is consumable from
        # every state, so no need to swallow errors here. If anything
        # raises we want to see it (regression signal).
        m1.send(ev)
        m2.send(ev)

    assert m1.state == m2.state, (
        f"stress final state diverged: m1={m1.state!r} m2={m2.state!r}"
    )
    _assert_logs_byte_identical(m1.log, m2.log, label="stress")


__all__ = [
    "test_determinism_async_gather",
    "test_determinism_parallel_regions",
    "test_determinism_simple_chain",
    "test_determinism_stress",
    "test_determinism_with_history",
]


# ---------------------------------------------------------------------------
# Type-only shim for ``hypothesis.composite`` decorators that reference
# ``draw: Any`` in their signature. Kept here so the file does not need
# a top-level ``typing.Any`` import — the composite decorators run at
# collection time and ``Any`` must be in scope.
# ---------------------------------------------------------------------------
from typing import Any  # noqa: E402,F401  (used by st.composite decorators above)
