"""Adaptive reflow typed contracts — phase state (DTB-L1).

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Literal

from .hashes import hash_artifact, hash_phase_state_digest
from .schedule import RestartTriggerEvent
from .types import ArtifactHash, ProvenanceChain
from .validators import ValidationResult, _ok, validate_positive_int

# ---------------------------------------------------------------------------
# Phase state (CONTRACTS.md §5) — DTB-L1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhaseState:
    """Required controller input; cannot be reconstructed from endpoint score alone."""

    outer_cycle_id: int
    round_in_cycle: int
    schedule_phase: Literal["high_noise", "anneal", "low_noise", "post_restart"]
    schedule_phase_index: int
    previous_trigger: RestartTriggerEvent | None
    operation_order_version: str
    source_selector_procedure: str
    seed_lineage_digest: ArtifactHash
    horizon_remaining: int
    horizon_coverage_proven: bool
    ambiguity_band_active: bool
    phase_state_digest: ArtifactHash
    recorded_at_round: int


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def empty_provenance() -> ProvenanceChain:
    """Return the canonical empty provenance chain.

    Callers must replace this with a non-empty producer list before validation.
    """
    return ProvenanceChain(())


def make_default_phase_state(
    *,
    outer_cycle_id: int = 0,
    round_in_cycle: int = 0,
    schedule_phase: Literal[
        "high_noise", "anneal", "low_noise", "post_restart"
    ] = "high_noise",
    schedule_phase_index: int = 0,
    previous_trigger: RestartTriggerEvent | None = None,
    operation_order_version: str = "v1",
    source_selector_procedure: str = "deterministic.previous_round",
    seed_lineage_digest: ArtifactHash = ArtifactHash(""),
    horizon_remaining: int = 1,
    horizon_coverage_proven: bool = False,
    ambiguity_band_active: bool = False,
    recorded_at_round: int = 0,
) -> PhaseState:
    """Build a :class:`PhaseState` with sensible defaults for tests."""
    seed_lineage_digest = ArtifactHash(seed_lineage_digest) if seed_lineage_digest else ArtifactHash(
        hash_artifact(
            {
                "selector": source_selector_procedure,
                "outer_cycle_id": outer_cycle_id,
                "round_in_cycle": round_in_cycle,
            }
        )
    )
    state = PhaseState(
        outer_cycle_id=outer_cycle_id,
        round_in_cycle=round_in_cycle,
        schedule_phase=schedule_phase,
        schedule_phase_index=schedule_phase_index,
        previous_trigger=previous_trigger,
        operation_order_version=operation_order_version,
        source_selector_procedure=source_selector_procedure,
        seed_lineage_digest=seed_lineage_digest,
        horizon_remaining=horizon_remaining,
        horizon_coverage_proven=horizon_coverage_proven,
        ambiguity_band_active=ambiguity_band_active,
        phase_state_digest=ArtifactHash(""),
        recorded_at_round=recorded_at_round,
    )
    digest = hash_phase_state_digest(state)
    return dataclasses.replace(state, phase_state_digest=digest)


def make_default_phase_state_digest(state: PhaseState) -> ArtifactHash:
    """Return the deterministic digest that ``state`` should carry."""
    return hash_phase_state_digest(state)


# ---------------------------------------------------------------------------
# Dataclass validators
# ---------------------------------------------------------------------------

from .types import SCHEDULE_PHASES


def validate_phase_state(p: PhaseState) -> ValidationResult:
    """Validate :class:`PhaseState`.

    Rejects when ``schedule_phase`` is not in the canonical literal set,
    ``operation_order_version`` is empty, ``horizon_remaining`` is not a
    positive integer, or ``phase_state_digest`` does not match the
    deterministic recompute.
    """
    errors: list[str] = []

    if p.schedule_phase not in SCHEDULE_PHASES:
        errors.append(
            f"schedule_phase must be one of {SCHEDULE_PHASES!r}, got {p.schedule_phase!r}"
        )

    if not p.operation_order_version:
        errors.append("operation_order_version must be non-empty")

    ok, sub_errors = validate_positive_int(p.horizon_remaining, "horizon_remaining")
    if not ok:
        errors.extend(sub_errors)

    expected_digest = hash_phase_state_digest(p)
    if p.phase_state_digest != expected_digest:
        errors.append(
            "phase_state_digest does not match deterministic recompute of "
            "all other PhaseState fields"
        )

    if errors:
        return (False, tuple(errors))
    return _ok()
