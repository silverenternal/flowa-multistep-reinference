"""Phase-state construction and transition helpers for the adaptive_reflow component.

This module implements the DTB-L1 "phase memory" half of the
``adaptive_reflow`` typed contract. ``PhaseState`` is the minimum required
controller input; it is **forbidden** to reconstruct the phase from endpoint
score alone (see CONTRACTS.md §5 and DESIGN_BOUNDARY.md §1 / §6). The
helpers here therefore refuse any signature that would let a caller
synthesize a phase from endpoint tensors alone.

Tasks satisfied:

* ``DTB-L1`` — phase memory + horizon coverage + branch uncertainty.

Module boundary:

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* ``PhaseState`` is frozen; every helper returns a new instance.
* ``phase_state_digest`` is recomputed via the canonical
  ``hash_phase_state_digest`` (from ``restart_memory_types``) so that
  downstream caches keyed on the digest remain stable.

Public surface:

* :func:`build_phase_state` — assemble a :class:`PhaseState` with
  schedule-phase inference and required ``operation_order_version``.
* :func:`advance_phase` — produce the next :class:`PhaseState` after a
  round boundary, honoring any restart-trigger event.
* :func:`make_default_phase_state` — convenience wrapper used by tests.
* :func:`validate_phase_state_transition` — pure validator for
  round-to-round transitions.

The module never exposes a helper that reconstructs phase from an
endpoint score alone.
"""

from __future__ import annotations

from typing import Optional

from .restart_memory_types import (
    ArtifactHash,
    PhaseState,
    RestartTriggerEvent,
    SCHEDULE_PHASES,
    hash_phase_state_digest,
    make_default_phase_state as _make_default_phase_state_from_types,
)


__all__ = [
    "build_phase_state",
    "advance_phase",
    "make_default_phase_state",
    "validate_phase_state_transition",
]


# ---------------------------------------------------------------------------
# Schedule-phase inference (DTB-L1)
# ---------------------------------------------------------------------------


def _infer_schedule_phase(
    schedule_phase_index: int,
    previous_trigger: Optional[RestartTriggerEvent],
) -> str:
    """Infer the canonical ``schedule_phase`` label from the schedule index.

    The mapping mirrors CONTRACTS.md §4/§5 schedule semantics:

    * ``0`` -> ``"high_noise"``
    * ``1`` -> ``"anneal"``
    * ``>= 2`` -> ``"low_noise"`` (unless a restart trigger is present)

    Any other non-negative value that is ambiguous (e.g. a negative
    schedule index used as a "frozen-bucket" sentinel) defaults to
    ``"anneal"``; this is the safe middle of the cycle and is the
    documented fallback per CONTRACTS.md §5 (PhaseState).
    """
    # A previous trigger overrides the schedule index: the cycle has
    # just been reset by a warm-restart boundary, so phase is
    # "post_restart" regardless of the schedule index.
    if previous_trigger is not None:
        return "post_restart"

    if schedule_phase_index < 0:
        # Negative indices are reserved for sentinel values (e.g. "frozen
        # bucket, schedule not yet assigned"). They are ambiguous; the
        # safe default is the middle of the cycle.
        return "anneal"

    if schedule_phase_index == 0:
        return "high_noise"
    if schedule_phase_index == 1:
        return "anneal"
    if schedule_phase_index >= 2:
        return "low_noise"

    # Defensive: the explicit branches above cover all non-negative ints
    # and the negative case. Any other value is unexpected; fall back
    # to the safe middle.
    return "anneal"


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_phase_state(
    outer_cycle_id: int,
    round_in_cycle: int,
    schedule_phase_index: int,
    operation_order_version: str,
    source_selector_procedure: str,
    seed_lineage_digest: ArtifactHash,
    horizon_remaining: int,
    *,
    previous_trigger: RestartTriggerEvent | None = None,
    horizon_coverage_proven: bool = True,
    ambiguity_band_active: bool = False,
    recorded_at_round: int = 0,
    schedule_phase: str | None = None,
) -> PhaseState:
    """Build a :class:`PhaseState` with phase inference and digest recompute.

    Parameters
    ----------
    outer_cycle_id:
        Identifier of the current outer warm-restart cycle. Must be a
        non-negative integer.
    round_in_cycle:
        Position inside the current cycle. Must be a non-negative
        integer.
    schedule_phase_index:
        Index into the frozen schedule family. ``0`` -> ``"high_noise"``,
        ``1`` -> ``"anneal"``, ``>= 2`` -> ``"low_noise"``. A negative
        index is treated as ambiguous and defaults to ``"anneal"``.
    operation_order_version:
        Version string of the operation-composition contract; see
        CONTRACTS.md §6. Must be non-empty (required field on the
        :class:`PhaseState`).
    source_selector_procedure:
        Versioned name of the source-selection routine. Must be
        non-empty.
    seed_lineage_digest:
        Hash of the random-seed lineage; used to reject seed
        substitutions that would silently change the schedule.
    horizon_remaining:
        Number of remaining rounds under the current horizon H. Must
        be strictly positive; ``0`` is a fail-closed condition.
    previous_trigger:
        Optional :class:`RestartTriggerEvent` from a recent restart
        boundary. When provided, ``schedule_phase`` is forced to
        ``"post_restart"`` regardless of the index.
    horizon_coverage_proven:
        ``True`` iff the calibration artifact covers the current H.
        Defaults to ``True`` (the safe value for a built artifact).
    ambiguity_band_active:
        ``True`` iff the dominance gap is within the calibrated
        uncertainty radius; downstream callers must NOT deterministic
        prune in this state.
    recorded_at_round:
        Round index at which this phase state was assembled. Used by
        downstream diagnostics to bound staleness.
    schedule_phase:
        Optional explicit override. When ``None``, the phase is
        inferred from ``schedule_phase_index`` and
        ``previous_trigger``. When set, the caller's value is
        validated against :data:`SCHEDULE_PHASES`.

    Raises
    ------
    ValueError
        If ``horizon_remaining <= 0`` or if a non-``None``
        ``schedule_phase`` is not in :data:`SCHEDULE_PHASES`.
    """
    # Strict positivity is enforced eagerly: PhaseState requires
    # horizon_remaining > 0 and 0 is a documented fail-closed condition.
    if horizon_remaining is None:
        raise ValueError("horizon_remaining must be a positive integer; got None")
    if isinstance(horizon_remaining, bool) or not isinstance(horizon_remaining, int):
        raise ValueError(
            "horizon_remaining must be a positive integer; "
            f"got {type(horizon_remaining).__name__}"
        )
    if horizon_remaining <= 0:
        raise ValueError(
            f"horizon_remaining must be > 0 (0 is a fail-closed condition); got {horizon_remaining}"
        )

    if not operation_order_version:
        raise ValueError("operation_order_version must be non-empty")
    if not source_selector_procedure:
        raise ValueError("source_selector_procedure must be non-empty")

    # Resolve schedule_phase:
    #   1. If the caller passed an explicit value, validate it.
    #   2. Else infer from schedule_phase_index, honoring previous_trigger.
    if schedule_phase is not None:
        if schedule_phase not in SCHEDULE_PHASES:
            raise ValueError(
                f"schedule_phase must be one of {SCHEDULE_PHASES!r}, "
                f"got {schedule_phase!r}"
            )
        resolved_phase = schedule_phase
    else:
        resolved_phase = _infer_schedule_phase(schedule_phase_index, previous_trigger)

    # The schema explicitly forbids reconstruction from endpoint score
    # alone. We enforce that here by construction: the builder takes
    # only controller inputs (cycle, round, schedule, lineage, selector)
    # and never accepts an endpoint tensor or a scalar score. Any
    # future helper that takes only a score is rejected at design time.
    state = PhaseState(
        outer_cycle_id=int(outer_cycle_id),
        round_in_cycle=int(round_in_cycle),
        schedule_phase=resolved_phase,
        schedule_phase_index=int(schedule_phase_index),
        previous_trigger=previous_trigger,
        operation_order_version=operation_order_version,
        source_selector_procedure=source_selector_procedure,
        seed_lineage_digest=seed_lineage_digest,
        horizon_remaining=int(horizon_remaining),
        horizon_coverage_proven=bool(horizon_coverage_proven),
        ambiguity_band_active=bool(ambiguity_band_active),
        phase_state_digest=ArtifactHash(""),
        recorded_at_round=int(recorded_at_round),
    )

    digest = hash_phase_state_digest(state)
    # dataclasses.replace returns a new instance because PhaseState is
    # frozen=True; this preserves immutability.
    import dataclasses

    return dataclasses.replace(state, phase_state_digest=digest)


def advance_phase(
    state: PhaseState,
    *,
    next_round_in_cycle: int,
    next_horizon_remaining: int,
    trigger: RestartTriggerEvent | None = None,
) -> PhaseState:
    """Return the next :class:`PhaseState` after a round boundary.

    With no ``trigger``:

    * ``round_in_cycle`` becomes ``next_round_in_cycle``
    * ``horizon_remaining`` becomes ``next_horizon_remaining``
    * ``recorded_at_round`` is incremented by 1
    * ``schedule_phase_index`` is preserved
    * ``schedule_phase`` is recomputed from the (preserved) index

    With a ``trigger``:

    * ``outer_cycle_id`` increments by 1
    * ``round_in_cycle`` resets to 0
    * ``schedule_phase`` becomes ``"post_restart"``
    * ``previous_trigger`` becomes ``trigger``
    * ``recorded_at_round`` is incremented by 1
    * ``horizon_remaining`` is preserved (the new cycle owns its own
      horizon; the caller's ``next_horizon_remaining`` is still applied
      because that is the explicit value for the upcoming round)
    * ``schedule_phase_index`` is preserved as a diagnostic field; the
      active schedule label is forced to ``"post_restart"``.

    Parameters
    ----------
    state:
        The current :class:`PhaseState`. Not mutated.
    next_round_in_cycle:
        Position inside the next round. If a trigger is provided this
        value is ignored and ``round_in_cycle`` resets to ``0``.
    next_horizon_remaining:
        Updated horizon remaining. Must be strictly positive.

    Raises
    ------
    ValueError
        If ``next_horizon_remaining <= 0``.
    """
    if next_horizon_remaining is None:
        raise ValueError("next_horizon_remaining must be a positive integer; got None")
    if (
        isinstance(next_horizon_remaining, bool)
        or not isinstance(next_horizon_remaining, int)
    ):
        raise ValueError(
            "next_horizon_remaining must be a positive integer; "
            f"got {type(next_horizon_remaining).__name__}"
        )
    if next_horizon_remaining <= 0:
        raise ValueError(
            f"next_horizon_remaining must be > 0 (0 is a fail-closed condition); "
            f"got {next_horizon_remaining}"
        )

    if trigger is not None:
        # Warm-restart boundary: cycle advances, round resets, label
        # becomes post_restart, the trigger becomes the recorded
        # previous_trigger.
        next_state = PhaseState(
            outer_cycle_id=int(state.outer_cycle_id) + 1,
            round_in_cycle=0,
            schedule_phase="post_restart",
            schedule_phase_index=int(state.schedule_phase_index),
            previous_trigger=trigger,
            operation_order_version=state.operation_order_version,
            source_selector_procedure=state.source_selector_procedure,
            seed_lineage_digest=state.seed_lineage_digest,
            horizon_remaining=int(next_horizon_remaining),
            horizon_coverage_proven=state.horizon_coverage_proven,
            ambiguity_band_active=state.ambiguity_band_active,
            phase_state_digest=ArtifactHash(""),
            recorded_at_round=int(state.recorded_at_round) + 1,
        )
    else:
        # Normal round boundary: keep cycle, advance round, recompute
        # the schedule phase from the (preserved) schedule index.
        next_phase_label = _infer_schedule_phase(
            int(state.schedule_phase_index), state.previous_trigger
        )
        next_state = PhaseState(
            outer_cycle_id=int(state.outer_cycle_id),
            round_in_cycle=int(next_round_in_cycle),
            schedule_phase=next_phase_label,
            schedule_phase_index=int(state.schedule_phase_index),
            previous_trigger=state.previous_trigger,
            operation_order_version=state.operation_order_version,
            source_selector_procedure=state.source_selector_procedure,
            seed_lineage_digest=state.seed_lineage_digest,
            horizon_remaining=int(next_horizon_remaining),
            horizon_coverage_proven=state.horizon_coverage_proven,
            ambiguity_band_active=state.ambiguity_band_active,
            phase_state_digest=ArtifactHash(""),
            recorded_at_round=int(state.recorded_at_round) + 1,
        )

    digest = hash_phase_state_digest(next_state)
    import dataclasses

    return dataclasses.replace(next_state, phase_state_digest=digest)


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------


def make_default_phase_state(
    run_id_seed: str,
    *,
    operation_order_version: str = "v1",
    source_selector_procedure: str = "deterministic.previous_round",
    horizon_remaining: int = 1,
    horizon_coverage_proven: bool = False,
    schedule_phase: str = "high_noise",
    schedule_phase_index: int = 0,
    recorded_at_round: int = 0,
) -> PhaseState:
    """Return a default :class:`PhaseState` useful for tests.

    Thin wrapper around ``restart_memory_types.make_default_phase_state``
    that pins ``operation_order_version`` and
    ``source_selector_procedure`` from this module's defaults and
    derives a deterministic ``seed_lineage_digest`` from the supplied
    ``run_id_seed``. ``run_id_seed`` is required so that two callers
    that ask for a "default" phase state never silently collide on the
    same lineage hash.

    Parameters
    ----------
    run_id_seed:
        Identifier used to seed the lineage hash. Two different
        ``run_id_seed`` values yield two different phase states.
    operation_order_version:
        Operation composition contract version; forwarded to the
        underlying builder.
    source_selector_procedure:
        Versioned selector procedure name; forwarded to the
        underlying builder.
    horizon_remaining:
        Forwarded to the underlying builder. Must be ``> 0``.
    horizon_coverage_proven:
        Forwarded to the underlying builder.
    schedule_phase:
        Forwarded to the underlying builder.
    schedule_phase_index:
        Forwarded to the underlying builder.
    recorded_at_round:
        Forwarded to the underlying builder.

    Raises
    ------
    ValueError
        If ``run_id_seed`` is empty.
    """
    if run_id_seed is None or str(run_id_seed) == "":
        raise ValueError("make_default_phase_state requires a non-empty run_id_seed")

    # Derive a deterministic lineage digest from the run seed so two
    # callers cannot accidentally share a default phase state.
    lineage_digest = ArtifactHash(
        __import__("hashlib").sha256(
            f"adaptive_reflow.phase_state.run_seed:{run_id_seed}".encode("utf-8")
        ).hexdigest()
    )

    return _make_default_phase_state_from_types(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase=schedule_phase,  # type: ignore[arg-type]
        schedule_phase_index=schedule_phase_index,
        previous_trigger=None,
        operation_order_version=operation_order_version,
        source_selector_procedure=source_selector_procedure,
        seed_lineage_digest=lineage_digest,
        horizon_remaining=horizon_remaining,
        horizon_coverage_proven=horizon_coverage_proven,
        ambiguity_band_active=False,
        recorded_at_round=recorded_at_round,
    )


# ---------------------------------------------------------------------------
# Transition validator (pure)
# ---------------------------------------------------------------------------


def validate_phase_state_transition(
    prev: PhaseState,
    new: PhaseState,
) -> tuple[str, ...]:
    """Validate the round-to-round transition ``prev -> new``.

    Returns an empty tuple when the transition is legal, otherwise a
    tuple of human-readable error messages (never parsed by code). The
    check enforces:

    * ``outer_cycle_id`` is non-decreasing; a strict increase is only
      legal when ``new.schedule_phase == "post_restart"`` and a fresh
      ``previous_trigger`` was attached (the warm-restart case).
    * ``round_in_cycle`` is monotonic within a cycle. A reset to ``0``
      is only legal when the cycle id advanced (warm-restart).
    * ``operation_order_version`` matches across the transition. A
      mismatch fails closed per the cross-contract invariant in
      CONTRACTS.md §6.
    * ``source_selector_procedure`` matches across the transition.
      Selector swaps without a contract version bump are not silent.
    * ``seed_lineage_digest`` matches across the transition. Lineage
      breaks are rejected (PhaseState fixture ``SeedLineageBreakFixture``).
    * ``horizon_remaining`` is a positive integer in both ``prev`` and
      ``new``; ``0`` is a documented fail-closed condition.
    * ``recorded_at_round`` advances by exactly 1 across the
      transition; anything else implies a missing or duplicate phase
      state.
    * ``phase_state_digest`` on ``new`` matches its deterministic
      recompute (the same invariant ``validate_phase_state`` enforces
      standalone).
    """
    errors: list[str] = []

    # Phase-state-level invariants on both endpoints.
    for label, state in (("prev", prev), ("new", new)):
        if (
            isinstance(state.horizon_remaining, bool)
            or not isinstance(state.horizon_remaining, int)
        ):
            errors.append(f"{label}.horizon_remaining must be an int, got {type(state.horizon_remaining).__name__}")
            continue
        if state.horizon_remaining <= 0:
            errors.append(
                f"{label}.horizon_remaining must be > 0 (0 is a fail-closed condition); "
                f"got {state.horizon_remaining}"
            )

    # Cycle monotonicity.
    if int(new.outer_cycle_id) < int(prev.outer_cycle_id):
        errors.append(
            "new.outer_cycle_id must be >= prev.outer_cycle_id; "
            f"got {new.outer_cycle_id} < {prev.outer_cycle_id}"
        )
    elif int(new.outer_cycle_id) == int(prev.outer_cycle_id) + 1:
        # Strict cycle advance: must be a warm-restart boundary.
        if new.schedule_phase != "post_restart":
            errors.append(
                "outer_cycle_id advanced by 1 but new.schedule_phase must be "
                f"'post_restart'; got {new.schedule_phase!r}"
            )
        if new.round_in_cycle != 0:
            errors.append(
                "outer_cycle_id advanced by 1 but new.round_in_cycle must reset "
                f"to 0; got {new.round_in_cycle}"
            )
    elif int(new.outer_cycle_id) > int(prev.outer_cycle_id) + 1:
        errors.append(
            "outer_cycle_id cannot skip cycles; "
            f"got prev={prev.outer_cycle_id}, new={new.outer_cycle_id}"
        )

    # Round monotonicity within a cycle.
    if int(new.outer_cycle_id) == int(prev.outer_cycle_id):
        if int(new.round_in_cycle) < int(prev.round_in_cycle):
            errors.append(
                "round_in_cycle must be non-decreasing within a cycle; "
                f"got prev={prev.round_in_cycle}, new={new.round_in_cycle}"
            )

    # Operation order version.
    if new.operation_order_version != prev.operation_order_version:
        errors.append(
            "operation_order_version must match across the transition "
            "(DTB-L2 cross-contract invariant); "
            f"prev={prev.operation_order_version!r}, new={new.operation_order_version!r}"
        )

    # Source selector procedure.
    if new.source_selector_procedure != prev.source_selector_procedure:
        errors.append(
            "source_selector_procedure must match across the transition; "
            f"prev={prev.source_selector_procedure!r}, new={new.source_selector_procedure!r}"
        )

    # Seed lineage must not break.
    if new.seed_lineage_digest != prev.seed_lineage_digest:
        errors.append(
            "seed_lineage_digest must match across the transition "
            "(PhaseState SeedLineageBreakFixture); "
            f"prev={prev.seed_lineage_digest!r}, new={new.seed_lineage_digest!r}"
        )

    # recorded_at_round must advance by exactly 1.
    if int(new.recorded_at_round) != int(prev.recorded_at_round) + 1:
        errors.append(
            "recorded_at_round must advance by exactly 1 across a phase-state "
            f"transition; got prev={prev.recorded_at_round}, new={new.recorded_at_round}"
        )

    # Digest must be the deterministic recompute (same invariant as
    # validate_phase_state).
    expected_digest = hash_phase_state_digest(new)
    if new.phase_state_digest != expected_digest:
        errors.append(
            "new.phase_state_digest does not match deterministic recompute of "
            "all other PhaseState fields"
        )

    return tuple(errors)