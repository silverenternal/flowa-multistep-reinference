"""Modern generic state machine library.

PEP 695 generic, decorator-driven, type-safe, async-compatible, with HSM
(hierarchical) support, history pseudo-states (shallow + deep), parallel
(orthogonal) regions, byte-deterministic transition logging, and DOT/Mermaid
visualization.

Stdlib-only; mypy --strict clean.

Public API surface (re-exported from :mod:`adaptive_reflow.contracts`):

* :class:`StateMachine` — the PEP 695 generic machine: ``StateMachine[TState, TEvent]``
* :class:`TransitionBuilder` / :class:`TransitionGuardedBuilder` — fluent
  decorator builders returned by ``sm.on(event)``
* :class:`TransitionContext` — payload passed to guards / entry hooks / effects
* :class:`TransitionLog` — frozen record of one transition step (byte-deterministic)
* :class:`TransitionKind` — ``EXTERNAL`` / ``INTERNAL`` / ``SELF`` (UML-style)
* :class:`HistoryKind` — ``NONE`` / ``SHALLOW`` / ``DEEP``
* :class:`StateMachineError` — base exception
* :class:`InvalidTransitionError` — no matching transition for (state, event)
* :class:`GuardRejected` — strict mode: all guards rejected
* :class:`StateNotFoundError` — unknown state referenced

Usage::

    sm: StateMachine[str, str] = StateMachine(initial="idle", name="order")

    @sm.on_enter("running")
    def enter_running(ctx): ...

    @sm.on("start").to("running")
    def start(ctx): ...

    sm.send("start")

Design notes:

* ``TState`` and ``TEvent`` are invariant TypeVars; concrete type aliases
  (``type State = Literal["a", "b"]``) make mypy catch invalid literals.
* Transitions are decorated *after* ``sm.state`` is set to the desired source.
  If the user needs a transition from a different source, they re-enter that
  source state first (``sm._state = ...`` is not public; use ``add_region``
  / ``add_parallel`` instead, or call ``send`` events that get you there).
* For multi-source events, use :meth:`StateMachine.add_transition` directly.
* Logs are byte-deterministic: counter starts at 0 and increments by 1 per
  transition; ``event`` / ``source`` / ``target`` use ``str()`` of the
  generic type parameter (so two machines driven by identical event
  sequences produce identical logs).
"""
from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Self,
    TypeVar,
    cast,
)

# ---------------------------------------------------------------------------
# Type variables
# ---------------------------------------------------------------------------

TState = TypeVar("TState")
TEvent = TypeVar("TEvent")

# A hook / guard / effect callable.
Hook = Callable[..., Any]
Guard = Callable[..., Awaitable[bool] | bool]

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StateMachineError(Exception):
    """Base for all state machine errors."""


class InvalidTransitionError(StateMachineError):
    """Raised when no transition matches the current ``(state, event)`` pair."""


class GuardRejected(StateMachineError):
    """Raised (in strict-guard mode) when every candidate transition's guard
    predicate rejected the event."""


class StateNotFoundError(StateMachineError):
    """Raised when a hook or transition references an unregistered state."""


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TransitionKind(Enum):
    """Kind of UML-style transition.

    * ``EXTERNAL`` — full exit/enter chain fires.
    * ``INTERNAL`` — only the effect runs (no exit/enter, parent untouched).
    * ``SELF`` — exit + re-enter on the same state (hooks fire).
    """

    EXTERNAL = "external"
    INTERNAL = "internal"
    SELF = "self"


class HistoryKind(Enum):
    """History pseudo-state restoration depth.

    * ``NONE`` — no history.
    * ``SHALLOW`` (H) — restore the region's last *direct* sub-state.
    * ``DEEP`` (H*) — restore the region's last *deepest* active sub-state.
    """

    NONE = "none"
    SHALLOW = "shallow"
    DEEP = "deep"


# ---------------------------------------------------------------------------
# Frozen transition log record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionLog:
    """A single transition step in the machine's replay-able history.

    Fields are stable across runs (``counter`` is a monotonic integer,
    timestamps are NOT wall-clock-derived). Two machines driven by identical
    event sequences produce byte-identical logs.
    """

    counter: int
    """Monotonic counter; starts at 1. Independent of wall clock."""

    event: str
    """``str(event)`` — the triggering event."""

    source: str
    """``str(source_state)`` — state we transitioned from."""

    target: str
    """``str(target_state)`` — state we transitioned to."""

    guard_name: str | None
    """``__name__`` of the guard that fired, or ``None`` (no guard)."""

    guard_result: bool | None
    """``True`` if the guard accepted, ``None`` when there was no guard."""

    effect_name: str | None
    """``__name__`` of the effect that fired, or ``None``."""

    history_restored: tuple[str, ...]
    """Non-empty when the target's history pseudo-state restored a sub-state."""

    kind: str
    """``str(TransitionKind)`` — external/internal/self."""

    internal_subpath: str
    """``"parent/region/sub_sm"`` path for nested dispatch, or ``""`` if root."""

    def __hash__(self) -> int:
        """Explicit hash over the canonical 4-tuple (audit F-52 / P2-29).

        ``frozen=True`` dataclasses already get a default ``__hash__`` over
        *every* field, but the audit asked for an explicit hash that
        pins only the 4-tuple ``(event, source, target, kind)`` so two
        ``TransitionLog`` records that differ only in ``counter`` /
        ``guard_name`` / ``effect_name`` / ``history_restored`` /
        ``internal_subpath`` / ``guard_result`` still hash the same.
        This makes the dedup-set semantic (the 4-tuple uniquely names
        the transition; the other fields are diagnostic metadata) the
        hash's contract.
        """
        return hash((self.event, self.source, self.target, self.kind))


# ---------------------------------------------------------------------------
# Context passed to hooks/guards/effects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionContext:
    """Read-only payload passed to guards / entry hooks / effects / exit hooks.

    ``source`` and ``target`` are the strings of the state names (``str()``
    of the generic ``TState``). For nested machines, ``machine`` is the
    deepest machine receiving the event.
    """

    machine: StateMachine[Any, Any]
    """The :class:`StateMachine` instance (deepest machine for nested events)."""

    event: Any
    """The event that triggered the transition."""

    payload: Any
    """Optional caller-supplied payload (``send(event, payload=...)``)."""

    source: str
    """``str(source_state)`` — origin state of this transition."""

    target: str
    """``str(target_state)`` — destination state of this transition."""

    counter: int
    """Monotonic counter for this transition (pre-increment value; the log
    records ``counter + 1`` after this transition commits)."""

    def is_initial(self) -> bool:
        """``True`` if this is the very first transition the machine has seen.

        The hook / effect context is constructed *before* the counter is
        incremented, so ``counter == 0`` here means "first transition".
        """
        return self.counter == 0


# ---------------------------------------------------------------------------
# Internal transition record (NOT public)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Transition:
    event: Any
    source: Any
    target: Any
    guard: Guard | None
    effect: Hook | None
    priority: int
    kind: TransitionKind
    internal: bool = False

    @property
    def guard_name(self) -> str | None:
        return getattr(self.guard, "__name__", None) if self.guard else None

    @property
    def effect_name(self) -> str | None:
        return getattr(self.effect, "__name__", None) if self.effect else None


# ---------------------------------------------------------------------------
# Fluent transition builders
# ---------------------------------------------------------------------------


class TransitionBuilder[TState, TEvent]:
    """Fluent builder returned by :meth:`StateMachine.on`.

    Chain ``.to(state)`` to specify the target; the returned
    :class:`TransitionGuardedBuilder` accepts ``.when(guard)``,
    ``.with_effect(...)``, ``.with_priority(...)``, and is also callable
    directly as a decorator (in which case the decorated function becomes
    the effect).
    """

    __slots__ = ("_sm", "_event")

    def __init__(self, sm: StateMachine[TState, TEvent], event: TEvent) -> None:
        self._sm = sm
        self._event = event

    def to(
        self,
        target: TState,
        *,
        kind: TransitionKind = TransitionKind.EXTERNAL,
    ) -> TransitionGuardedBuilder[TState, TEvent]:
        return TransitionGuardedBuilder(
            sm=self._sm,
            event=self._event,
            target=target,
            kind=kind,
        )


class TransitionGuardedBuilder[TState, TEvent]:
    """Builder returned by :meth:`TransitionBuilder.to`.

    Supports ``.when(...)``, ``.with_effect(...)``, ``.with_priority(...)``,
    and acts as a decorator itself: calling it with a function registers
    the function as the transition's effect.
    """

    __slots__ = (
        "_sm",
        "_event",
        "_target",
        "_kind",
        "_guard",
        "_effect",
        "_priority",
    )

    def __init__(
        self,
        *,
        sm: StateMachine[TState, TEvent],
        event: TEvent,
        target: TState,
        kind: TransitionKind,
    ) -> None:
        self._sm = sm
        self._event = event
        self._target = target
        self._kind = kind
        self._guard: Guard | None = None
        self._effect: Hook | None = None
        self._priority: int = 0

    def when(self, guard: Guard) -> Self:
        """Attach a guard predicate. Returns ``self`` for chaining."""
        self._guard = guard
        return self

    def with_effect(self, effect: Hook) -> Self:
        """Attach an effect callable (separate from the decorated handler)."""
        self._effect = effect
        return self

    def with_priority(self, priority: int) -> Self:
        """Set priority; higher priority wins when multiple guards could match."""
        self._priority = priority
        return self

    def register(self) -> _Transition:
        """Register the transition without a decorated handler.

        Useful when you want a guard-only or pure-configuration transition.
        """
        return self._sm._register_transition(
            event=self._event,
            target=self._target,
            guard=self._guard,
            effect=self._effect,
            priority=self._priority,
            kind=self._kind,
        )

    def __call__(self, fn: Hook) -> Hook:
        """Use as a decorator: register the transition with ``fn`` as the effect."""
        self._effect = fn
        self._sm._register_transition(
            event=self._event,
            target=self._target,
            guard=self._guard,
            effect=self._effect,
            priority=self._priority,
            kind=self._kind,
        )
        return fn


# ---------------------------------------------------------------------------
# StateMachine (PEP 695 generic)
# ---------------------------------------------------------------------------


class StateMachine[TState, TEvent]:
    """PEP 695 generic, hand-rolled, stdlib-only state machine.

    Supports:

    * Decorator-based transitions: ``@sm.on("event").to("state")`` (with
      ``.when(guard)`` / ``.with_effect(...)`` / ``.with_priority(...)``).
    * State entry / exit hooks: ``@sm.on_enter(state)`` / ``@sm.on_exit(state)``.
    * Synchronous and asynchronous hooks/guards/effects (``send()`` refused
      for async, ``asend()`` awaits all of them).
    * Hierarchical states (``add_region``): sub-state machines owned by a
      parent state; events bubble from the deepest region outward.
    * History pseudo-states (shallow + deep): re-entering a parent restores
      the last-active sub-state.
    * Parallel / orthogonal regions (``add_parallel``): a parent state with
      multiple sub-state machines that all receive every event independently.
    * Visualization: ``to_mermaid()`` (``stateDiagram-v2``) and ``to_dot()``
      (Graphviz DOT).
    * Byte-deterministic transition log: every transition is recorded in
      :attr:`log` (a tuple of :class:`TransitionLog`); two machines driven
      by identical event sequences produce byte-identical logs.
    * Type-safe transitions: ``TState`` / ``TEvent`` type parameters enforce
      literal state/event vocab (mypy strict).
    """

    __slots__ = (
        "_initial",
        "_state",
        "_name",
        "_transitions",
        "_enter_hooks",
        "_exit_hooks",
        "_regions",
        "_parallel",
        "_history_kind",
        "_history",
        "_history_deep",
        "_log",
        "_counter",
        "_strict_guards",
    )

    def __init__(self, *, initial: TState, name: str = "sm") -> None:
        self._initial: TState = initial
        self._state: TState = initial
        self._name: str = name

        # Transition table; kept as list so registration order is preserved
        # (used as a stable sort key when priorities tie).
        self._transitions: list[_Transition] = []

        # Hooks: state -> ordered list of hooks
        self._enter_hooks: dict[Any, list[Hook]] = {}
        self._exit_hooks: dict[Any, list[Hook]] = {}

        # Sub-state machines (HSM + parallel)
        self._regions: dict[Any, dict[str, StateMachine[Any, TEvent]]] = {}
        self._parallel: dict[Any, dict[str, StateMachine[Any, TEvent]]] = {}

        # History tracking
        self._history_kind: dict[Any, HistoryKind] = {}
        self._history: dict[Any, dict[str, Any]] = {}  # parent -> region -> last direct sub
        self._history_deep: dict[Any, dict[str, Any]] = {}  # parent -> region -> deepest sub

        # Logging
        self._log: list[TransitionLog] = []
        self._counter: int = 0

        # Strict guard mode (default False — silent no-op when no guard fires)
        self._strict_guards: bool = False

    # ---- Properties -----------------------------------------------------

    @property
    def name(self) -> str:
        """User-supplied name; used in DOT/Mermaid output."""
        return self._name

    @property
    def state(self) -> TState:
        """Current state (read-only public API)."""
        return self._state

    @property
    def initial(self) -> TState:
        """The state passed to ``__init__``."""
        return self._initial

    @property
    def log(self) -> tuple[TransitionLog, ...]:
        """Tuple of every transition log entry recorded so far."""
        return tuple(self._log)

    @property
    def transitions(self) -> tuple[_Transition, ...]:
        """Tuple of every registered transition (internal type, exposed for tests)."""
        return tuple(self._transitions)

    # ---- Decorator API ---------------------------------------------------

    def on(self, event: TEvent) -> TransitionBuilder[TState, TEvent]:
        """Start a transition-builder chain for ``event``.

        Use as a decorator::

            @sm.on("start").to("running")
            def start(ctx): ...

        Or call ``.register()`` to register without a handler::

            sm.on("start").to("running").when(can_start).register()
        """
        return TransitionBuilder(self, event)

    def on_enter(self, state: TState) -> Callable[[Hook], Hook]:
        """Decorator factory: register an on-enter hook for ``state``."""

        def decorator(fn: Hook) -> Hook:
            self._enter_hooks.setdefault(state, []).append(fn)
            return fn

        return decorator

    def on_exit(self, state: TState) -> Callable[[Hook], Hook]:
        """Decorator factory: register an on-exit hook for ``state``."""

        def decorator(fn: Hook) -> Hook:
            self._exit_hooks.setdefault(state, []).append(fn)
            return fn

        return decorator

    # ---- Mode configuration ---------------------------------------------

    def with_strict_guards(self, strict: bool = True) -> Self:
        """Enable / disable strict-guard mode.

        When enabled, :meth:`send` / :meth:`asend` raise :class:`GuardRejected`
        if every candidate transition's guard predicate rejected the event.
        Default ``False`` (silently no-op, matching classic UML "ignored events").
        """
        self._strict_guards = strict
        return self

    # ---- HSM + Parallel registration ------------------------------------

    def add_region(
        self,
        parent: TState,
        region_name: str,
        sub_sm: StateMachine[Any, TEvent],
        *,
        history: HistoryKind = HistoryKind.NONE,
    ) -> Self:
        """Register a sub-state machine under the composite state ``parent``.

        On entry to ``parent``, ``sub_sm`` is also entered (its initial state
        becomes active). On event dispatch while in ``parent``, the event is
        forwarded to ``sub_sm`` first; if no transition is matched there, the
        parent's own transitions are tried.

        ``history=HistoryKind.SHALLOW`` restores the region's last direct
        sub-state on re-entry. ``history=HistoryKind.DEEP`` restores the last
        deepest active sub-state.
        """
        if not isinstance(sub_sm, StateMachine):
            raise TypeError(
                f"add_region sub_sm must be a StateMachine instance; got {type(sub_sm)!r}"
            )
        self._regions.setdefault(parent, {})[region_name] = sub_sm
        self._history_kind[parent] = history
        return self

    def add_parallel(
        self,
        parent: TState,
        regions: Mapping[str, StateMachine[Any, TEvent]],
    ) -> Self:
        """Register a parallel / orthogonal state.

        On entry to ``parent``, every region is entered (each runs its own
        state machine). On event dispatch while in ``parent``, every region
        receives the event independently (synchronous sequential dispatch;
        for parallel async dispatch, see :meth:`asend_parallel`).
        """
        for name, sub in regions.items():
            if not isinstance(sub, StateMachine):
                raise TypeError(
                    f"add_parallel region {name!r} must be a StateMachine; got {type(sub)!r}"
                )
        self._parallel[parent] = dict(regions)
        return self

    # ---- Reset -----------------------------------------------------------

    def reset(self) -> Self:
        """Reset the machine to its initial state. Clears the transition log."""
        self._state = self._initial
        self._log.clear()
        self._counter = 0
        for sub_dict in self._regions.values():
            for sub in sub_dict.values():
                sub.reset()
        for sub_dict in self._parallel.values():
            for sub in sub_dict.values():
                sub.reset()
        return self

    def clear_log(self) -> None:
        """Clear the transition log without resetting state."""
        self._log.clear()
        self._counter = 0

    # ---- Synchronous dispatch -------------------------------------------

    def send(self, event: TEvent, *, payload: Any = None) -> Self:
        """Synchronously dispatch ``event``.

        Refuses if any guard / hook / effect on the matched path is a
        coroutine function. Use :meth:`asend` for those.
        """
        self._dispatch_sync(event, payload)
        return self

    def can(self, event: TEvent, *, payload: Any = None) -> bool:
        """Return ``True`` if ``event`` can fire from the current state.

        For nested machines, ``True`` if any sub-region can fire it (which
        matches the dispatch order used by :meth:`send`).
        """
        return self._can_sync(event, payload)

    # ---- Asynchronous dispatch ------------------------------------------

    async def asend(self, event: TEvent, *, payload: Any = None) -> Self:
        """Asynchronously dispatch ``event``.

        Awaits any async guards / hooks / effects encountered on the path.
        """
        await self._dispatch_async(event, payload)
        return self

    async def can_async(self, event: TEvent, *, payload: Any = None) -> bool:
        """Async variant of :meth:`can`."""
        return await self._can_async(event, payload)

    # ---- Internal: registration -----------------------------------------

    def _register_transition(
        self,
        *,
        event: TEvent,
        target: TState,
        guard: Guard | None,
        effect: Hook | None,
        priority: int,
        kind: TransitionKind,
    ) -> _Transition:
        source = self._state
        # Auto-promote: EXTERNAL transition with source == target becomes SELF
        if kind is TransitionKind.EXTERNAL and source == target:
            kind = TransitionKind.SELF
        trans = _Transition(
            event=event,
            source=source,
            target=target,
            guard=guard,
            effect=effect,
            priority=priority,
            kind=kind,
        )
        self._transitions.append(trans)
        return trans

    def add_transition(
        self,
        *,
        source: TState,
        event: TEvent,
        target: TState,
        guard: Guard | None = None,
        effect: Hook | None = None,
        priority: int = 0,
        kind: TransitionKind = TransitionKind.EXTERNAL,
    ) -> Self:
        """Imperatively add a transition (alternative to the decorator API).

        Use this when you need to register a transition from a source that is
        not the machine's current state.
        """
        effective_kind = kind
        if kind is TransitionKind.EXTERNAL and source == target:
            effective_kind = TransitionKind.SELF
        self._transitions.append(
            _Transition(
                event=event,
                source=source,
                target=target,
                guard=guard,
                effect=effect,
                priority=priority,
                kind=effective_kind,
            )
        )
        return self

    # ---- Internal: history ----------------------------------------------

    def _update_history(self, parent: Any, sub: StateMachine[Any, TEvent]) -> None:
        """Snapshot the sub-state machine's current state into history."""
        kind = self._history_kind.get(parent, HistoryKind.NONE)
        if kind is HistoryKind.NONE:
            return
        # Find which region name `sub` lives under
        regions = self._regions.get(parent, {})
        for region_name, region_sub in regions.items():
            if region_sub is sub:
                self._history.setdefault(parent, {})[region_name] = sub._state
                if kind is HistoryKind.DEEP:
                    # Deep = walk all sub-machines and collect their state
                    deep_path = self._collect_deep_state(sub)
                    self._history_deep.setdefault(parent, {})[region_name] = deep_path
                break

    @staticmethod
    def _collect_deep_state(sm: StateMachine[Any, Any]) -> tuple[Any, ...]:
        """Walk a state machine tree and return the path of currently-active states.

        The first element is ``sm._state``; subsequent elements are the active
        sub-state of each region nested under that state.
        """
        path: list[Any] = [sm._state]
        # Walk into nested regions / parallels if the current state owns any.
        for sub in sm._regions.get(sm._state, {}).values():
            path.extend(sm._collect_deep_state(sub))
        for sub in sm._parallel.get(sm._state, {}).values():
            path.extend(sm._collect_deep_state(sub))
        return tuple(path)

    def _restore_history(self, parent: Any) -> tuple[str, ...]:
        """Restore sub-state machine(s) to their entry state on re-entry.

        * :attr:`HistoryKind.NONE` — reset each sub-state machine to its initial.
        * :attr:`HistoryKind.SHALLOW` — restore last direct sub-state.
        * :attr:`HistoryKind.DEEP` — restore last deepest active sub-state.

        Returns a tuple of human-readable strings describing the restored paths
        (empty when ``NONE`` or no regions).
        """
        kind = self._history_kind.get(parent, HistoryKind.NONE)
        regions = self._regions.get(parent, {})
        if kind is HistoryKind.NONE:
            for sub in regions.values():
                sub.reset()
            return ()
        restored: list[str] = []
        shallow_map = self._history.get(parent, {})
        deep_map = self._history_deep.get(parent, {})
        for region_name, sub in regions.items():
            if kind is HistoryKind.SHALLOW and region_name in shallow_map:
                target = shallow_map[region_name]
                sub._state = target
                restored.append(f"{region_name}:{target}")
            elif kind is HistoryKind.DEEP and region_name in deep_map:
                deep_path = deep_map[region_name]
                if deep_path:
                    sub._restore_deep_path(deep_path)
                    restored.append(f"{region_name}:{'/'.join(str(p) for p in deep_path)}")
        return tuple(restored)

    def _restore_deep_path(self, path: tuple[Any, ...]) -> None:
        """Restore a deep-history path into ``self``."""
        if not path:
            return
        self._state = path[0]
        if len(path) > 1:
            for sub in self._regions.get(path[0], {}).values():
                sub._restore_deep_path(path[1:])
                return
            for sub in self._parallel.get(path[0], {}).values():
                sub._restore_deep_path(path[1:])
                return

    # ---- Internal: synchronous dispatch --------------------------------

    def _dispatch_sync(self, event: TEvent, payload: Any) -> None:
        # 1. Sub-region forwarding (composite state with single sub-region).
        regions = self._regions.get(self._state)
        if regions is not None:
            for sub in regions.values():
                if sub._can_sync(event, payload):
                    sub._dispatch_sync(event, payload)
                    return

        # 2. Parallel forwarding (orthogonal regions).
        parallel = self._parallel.get(self._state)
        if parallel is not None:
            handled_any = False
            for sub in parallel.values():
                if sub._can_sync(event, payload):
                    sub._dispatch_sync(event, payload)
                    handled_any = True
            if handled_any:
                return
            # No region handled it: fall through to self transitions.

        # 3. Try matching transitions in self.
        trans, any_guard = self._try_pick_sync(event, payload, raise_guard=True)
        if trans is None:
            if not any_guard:
                # No transition defined at all for (state, event).
                raise InvalidTransitionError(
                    f"No transition for state={self._state!r} event={event!r} "
                    f"(machine={self._name!r})"
                )
            # else: guards rejected in non-strict mode → silent no-op (UML "ignored event")
            return

        # 4. Execute.
        self._execute_transition_sync(trans, event, payload)

    def _can_sync(self, event: TEvent, payload: Any) -> bool:
        # Sub-region
        regions = self._regions.get(self._state)
        if regions is not None:
            for sub in regions.values():
                if sub._can_sync(event, payload):
                    return True
        # Parallel: event is "consumable" if any region can handle it
        parallel = self._parallel.get(self._state)
        if parallel is not None:
            return any(sub._can_sync(event, payload) for sub in parallel.values())
        # Self: a transition matches AND its guard passes (can-fires)
        trans, _ = self._try_pick_sync(event, payload, raise_guard=False)
        return trans is not None

    def _try_pick_sync(
        self,
        event: TEvent,
        payload: Any,
        *,
        raise_guard: bool,
    ) -> tuple[_Transition | None, bool]:
        """Find the first matching transition.

        Returns ``(trans, any_guard)`` where ``trans`` is the chosen transition
        (or ``None``) and ``any_guard`` is ``True`` iff at least one candidate
        had a guard that rejected the event.

        * If ``trans`` is not ``None`` → execute it.
        * If ``trans`` is ``None`` and ``any_guard`` is ``False`` → no
          transition is defined; caller should raise :class:`InvalidTransitionError`.
        * If ``trans`` is ``None`` and ``any_guard`` is ``True`` → all guards
          rejected. In strict mode (and ``raise_guard=True``) raise
          :class:`GuardRejected`; otherwise silent no-op.
        """
        candidates = [t for t in self._transitions if t.source == self._state and t.event == event]
        if not candidates:
            return None, False
        # Stable sort: priority desc, then registration order.
        indexed = list(enumerate(candidates))
        indexed.sort(key=lambda pair: (-pair[1].priority, pair[0]))
        ordered = [t for _, t in indexed]
        any_guard_seen = False
        for cand in ordered:
            if cand.guard is None:
                # No guard: only viable if no other guarded candidate is alive.
                if not any_guard_seen:
                    return cand, False
                continue
            any_guard_seen = True
            if inspect.iscoroutinefunction(cand.guard):
                raise RuntimeError(
                    f"Async guard {cand.guard!r} cannot be used with sync send(); "
                    f"call asend() instead."
                )
            ok = cand.guard(self._ctx(event, payload))
            if ok:
                return cand, False
        if raise_guard and self._strict_guards and any_guard_seen:
            raise GuardRejected(
                f"All guards rejected for state={self._state!r} event={event!r} "
                f"(machine={self._name!r})"
            )
        return None, any_guard_seen

    def _execute_transition_sync(
        self,
        trans: _Transition,
        event: TEvent,
        payload: Any,
    ) -> None:
        source = self._state
        target = trans.target
        kind = trans.kind

        # Update history of source BEFORE leaving.
        if source in self._regions:
            for sub in self._regions[source].values():
                self._update_history(source, sub)

        # Exit hooks (skip for INTERNAL transitions).
        if kind is not TransitionKind.INTERNAL:
            for fn in self._exit_hooks.get(source, ()):
                if inspect.iscoroutinefunction(fn):
                    raise RuntimeError(
                        f"Async exit hook {fn!r} requires asend(); use send() for sync hooks."
                    )
                fn(self._ctx(event, payload, source=source, target=target))

        # Move state.
        self._state = target

        # Enter hooks + history restoration.
        history_restored: tuple[str, ...] = ()
        if kind is not TransitionKind.INTERNAL:
            for fn in self._enter_hooks.get(target, ()):
                if inspect.iscoroutinefunction(fn):
                    raise RuntimeError(
                        f"Async enter hook {fn!r} requires asend(); use send() for sync hooks."
                    )
                fn(self._ctx(event, payload, source=source, target=target))
            if target in self._regions:
                history_restored = self._restore_history(target)

        # Effect.
        if trans.effect is not None:
            if inspect.iscoroutinefunction(trans.effect):
                raise RuntimeError(
                    f"Async effect {trans.effect!r} requires asend(); use send() for sync effects."
                )
            trans.effect(self._ctx(event, payload, source=source, target=target))

        # Log.
        self._counter += 1
        self._log.append(
            TransitionLog(
                counter=self._counter,
                event=str(event),
                source=str(source),
                target=str(target),
                guard_name=trans.guard_name,
                guard_result=True if trans.guard is None else None,
                effect_name=trans.effect_name,
                history_restored=history_restored,
                kind=kind.value,
                internal_subpath="",
            )
        )

    # ---- Internal: asynchronous dispatch -------------------------------

    async def _dispatch_async(self, event: TEvent, payload: Any) -> None:
        regions = self._regions.get(self._state)
        if regions is not None:
            for sub in regions.values():
                if await sub._can_async(event, payload):
                    await sub._dispatch_async(event, payload)
                    return

        parallel = self._parallel.get(self._state)
        if parallel is not None:
            handled_any = False
            coros = []
            for sub in parallel.values():
                if await sub._can_async(event, payload):
                    coros.append(sub._dispatch_async(event, payload))
                    handled_any = True
            if coros:
                await asyncio.gather(*coros)
            if handled_any:
                return
            # else: fall through to outer transitions

        trans, any_guard = await self._try_pick_async(event, payload, raise_guard=True)
        if trans is None:
            if not any_guard:
                raise InvalidTransitionError(
                    f"No transition for state={self._state!r} event={event!r} "
                    f"(machine={self._name!r})"
                )
            # Non-strict guard rejection: silent no-op.
            return
        await self._execute_transition_async(trans, event, payload)

    async def _can_async(self, event: TEvent, payload: Any) -> bool:
        regions = self._regions.get(self._state)
        if regions is not None:
            for sub in regions.values():
                if await sub._can_async(event, payload):
                    return True
        parallel = self._parallel.get(self._state)
        if parallel is not None:
            checks = [sub._can_async(event, payload) for sub in parallel.values()]
            results = await asyncio.gather(*checks)
            return any(results)
        trans, _ = await self._try_pick_async(event, payload, raise_guard=False)
        return trans is not None

    async def _try_pick_async(
        self,
        event: TEvent,
        payload: Any,
        *,
        raise_guard: bool,
    ) -> tuple[_Transition | None, bool]:
        candidates = [t for t in self._transitions if t.source == self._state and t.event == event]
        if not candidates:
            return None, False
        indexed = list(enumerate(candidates))
        indexed.sort(key=lambda pair: (-pair[1].priority, pair[0]))
        ordered = [t for _, t in indexed]
        any_guard_seen = False
        for cand in ordered:
            if cand.guard is None:
                if not any_guard_seen:
                    return cand, False
                continue
            any_guard_seen = True
            ctx = self._ctx(event, payload)
            if inspect.iscoroutinefunction(cand.guard):
                ok = await cand.guard(ctx)
            else:
                ok = cand.guard(ctx)
            if ok:
                return cand, False
        if raise_guard and self._strict_guards and any_guard_seen:
            raise GuardRejected(
                f"All guards rejected for state={self._state!r} event={event!r} "
                f"(machine={self._name!r})"
            )
        return None, any_guard_seen

    async def _execute_transition_async(
        self,
        trans: _Transition,
        event: TEvent,
        payload: Any,
    ) -> None:
        source = self._state
        target = trans.target
        kind = trans.kind

        if source in self._regions:
            for sub in self._regions[source].values():
                self._update_history(source, sub)

        if kind is not TransitionKind.INTERNAL:
            for fn in self._exit_hooks.get(source, ()):
                ctx = self._ctx(event, payload, source=source, target=target)
                if inspect.iscoroutinefunction(fn):
                    await fn(ctx)
                else:
                    fn(ctx)

        self._state = target

        history_restored: tuple[str, ...] = ()
        if kind is not TransitionKind.INTERNAL:
            for fn in self._enter_hooks.get(target, ()):
                ctx = self._ctx(event, payload, source=source, target=target)
                if inspect.iscoroutinefunction(fn):
                    await fn(ctx)
                else:
                    fn(ctx)
            if target in self._regions:
                history_restored = self._restore_history(target)

        if trans.effect is not None:
            ctx = self._ctx(event, payload, source=source, target=target)
            if inspect.iscoroutinefunction(trans.effect):
                await trans.effect(ctx)
            else:
                trans.effect(ctx)

        self._counter += 1
        self._log.append(
            TransitionLog(
                counter=self._counter,
                event=str(event),
                source=str(source),
                target=str(target),
                guard_name=trans.guard_name,
                guard_result=True if trans.guard is None else None,
                effect_name=trans.effect_name,
                history_restored=history_restored,
                kind=kind.value,
                internal_subpath="",
            )
        )

    # ---- Context helper ------------------------------------------------

    def _ctx(
        self,
        event: TEvent,
        payload: Any,
        *,
        source: Any | None = None,
        target: Any | None = None,
    ) -> TransitionContext:
        return TransitionContext(
            machine=self,
            event=event,
            payload=payload,
            source=str(source if source is not None else self._state),
            target=str(target if target is not None else self._state),
            counter=self._counter,
        )

    # ---- Visualization --------------------------------------------------

    def to_mermaid(self) -> str:
        """Emit a ``stateDiagram-v2`` representation.

        Includes all registered transitions. Sub-regions are rendered as
        composite states; parallel regions are emitted as nested state
        diagrams side-by-side.
        """
        lines: list[str] = ["stateDiagram-v2", f"    [*] --> {self._state}"]
        seen: set[tuple[str, str, str]] = set()
        self._collect_mermaid(lines, seen, indent=0)
        # Also emit parallel regions as simple composite markers
        for parent, regions in self._parallel.items():
            for region_name in regions:
                lines.append(f"    state {parent}_{region_name} {{")
                lines.append("        direction LR")
                lines.append("    }")
        return "\n".join(lines)

    def _collect_mermaid(
        self,
        out: list[str],
        seen: set[tuple[str, str, str]],
        *,
        indent: int,
    ) -> None:
        prefix = "    " * (indent + 1)
        for t in self._transitions:
            key = (str(t.source), str(t.event), str(t.target))
            if key in seen:
                continue
            seen.add(key)
            label = str(t.event)
            if t.guard is not None:
                label += f" / [{t.guard_name or 'guard'}]"
            out.append(f"{prefix}{t.source} --> {t.target} : {label}")

    def to_dot(self) -> str:
        """Emit a Graphviz DOT representation."""
        lines: list[str] = [
            f'digraph "{self._name}" {{',
            "    rankdir=LR;",
            '    node [shape=circle];',
            '    __start__ [shape=point];',
            f'    __start__ -> "{self._state}";',
        ]
        seen: set[tuple[str, str, str]] = set()
        for t in self._transitions:
            key = (str(t.source), str(t.event), str(t.target))
            if key in seen:
                continue
            seen.add(key)
            label = str(t.event)
            if t.guard is not None:
                label += f"\\n[{t.guard_name or 'guard'}]"
            lines.append(f'    "{t.source}" -> "{t.target}" [label="{label}"];')
        # Composite markers
        for parent in self._regions:
            lines.append(f'    subgraph "cluster_{parent}" {{')
            lines.append(f'        label="{parent}";')
            lines.append(f'        "{parent}";')
            lines.append("    }")
        for parent in self._parallel:
            lines.append(f'    subgraph "cluster_parallel_{parent}" {{')
            lines.append(f'        label="{parent} (parallel)";')
            lines.append(f'        "{parent}";')
            lines.append("    }")
        lines.append("}")
        return "\n".join(lines)

    # ---- Introspection --------------------------------------------------

    def states(self) -> tuple[TState, ...]:
        """Tuple of every state that appears as a source or target of a transition,
        plus the initial state and any state with registered hooks."""
        states: set[TState] = {self._initial}
        for t in self._transitions:
            states.add(t.source)
            states.add(t.target)
        for s in self._enter_hooks:
            states.add(s)
        for s in self._exit_hooks:
            states.add(s)
        for s in self._regions:
            states.add(s)
        for s in self._parallel:
            states.add(s)
        return tuple(states)

    def __repr__(self) -> str:
        return f"StateMachine(name={self._name!r}, state={self._state!r})"


__all__ = [
    "Guard",
    "GuardRejected",
    "HistoryKind",
    "Hook",
    "InvalidTransitionError",
    "StateMachine",
    "StateMachineError",
    "StateNotFoundError",
    "TransitionBuilder",
    "TransitionContext",
    "TransitionGuardedBuilder",
    "TransitionKind",
    "TransitionLog",
]
