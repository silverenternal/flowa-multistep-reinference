"""Adaptive reflow typed contracts — cosine restart budget (DTB-NA1).

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .types import (
    ArtifactHash,
    BundleId,
    ChannelName,
    FactorValue,
    ProvenanceChain,
    RestartTriggerCode,
    TriggerId,
)

# ---------------------------------------------------------------------------
# Cosine restart budget (CONTRACTS.md §4) — DTB-NA1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CosineScheduleConfig:
    """Frozen schedule configuration for the outer cycle."""

    schedule_family: Literal[
        "constant",
        "linear",
        "cosine_no_restart",
        "cosine_guarded_restart",
        "empirical_learned",
    ]
    cycle_length: int
    n_min: FactorValue
    n_max: FactorValue
    per_channel_caps: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    symmetric_delta_caps_by_channel: Mapping[ChannelName, FactorValue]
    restart_triggers_allowed: tuple[RestartTriggerCode, ...]
    config_hash: ArtifactHash
    frozen_before_evaluation: bool


@dataclass(frozen=True)
class CosineScheduleSample:
    """Sample of the schedule for a single round."""

    schedule_hash: ArtifactHash
    outer_cycle_id: int
    round_in_cycle: int
    cycle_length: int
    n_cap: FactorValue
    n_min: FactorValue
    n_max: FactorValue
    u_r: float
    family: str
    computed_at_round: int


@dataclass(frozen=True)
class FreshNoiseFloor:
    """Per-channel fresh-noise floor, with its provenance source."""

    channel: ChannelName
    floor_value: FactorValue
    source: Literal["schedule", "calibration", "manual_override"]
    config_hash: ArtifactHash


@dataclass(frozen=True)
class RestartTriggerEvent:
    """Record of one restart-trigger event (warm restart boundary)."""

    trigger_id: TriggerId
    outer_cycle_id_old: int
    outer_cycle_id_new: int
    trigger_code: RestartTriggerCode
    trigger_metric_snapshot: Mapping[str, float]
    discarded_source_bundle_ids: tuple[BundleId, ...]
    noise_capacity_before: FactorValue
    noise_capacity_after: FactorValue
    unresolved_metric_deficit: Mapping[str, float]
    provenance: ProvenanceChain
    recorded_at_round: int
