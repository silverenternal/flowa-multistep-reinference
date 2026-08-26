"""Adaptive reflow typed contracts — writer authority (DTB-S1).

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .hashes import hash_policy_hash
from .schedule import CosineScheduleSample
from .types import (
    ArtifactHash,
    ChannelName,
    FactorValue,
    LedgerRowId,
    MechanismId,
    PolicyId,
    RunId,
)
from .validators import ValidationResult, _ok

# ---------------------------------------------------------------------------
# Writer authority (CONTRACTS.md §7) — DTB-S1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RestartPolicyAuthorityContract:
    """Single-writer authority contract. ``adaptive_reflow`` is sole executable writer."""

    contract_version: str
    executable_writer_id: Literal["inference.adaptive_reflow"]
    diagnostic_writer_ids: tuple[MechanismId, ...]
    consumer_writer_id: Literal["flowa_core_runtime"]
    mode_flags: tuple[str, ...]
    legacy_compatibility_window: LegacyCompatibilityWindow
    contract_hash: ArtifactHash


@dataclass(frozen=True)
class LegacyCompatibilityWindow:
    """Bounded compatibility window for the legacy ``noise_bias`` standalone route."""

    enabled: bool
    legacy_mechanism_id: MechanismId
    legacy_mode: Literal["legacy_standalone"]
    exclusive_with: tuple[MechanismId, ...]
    schema_read_compatibility_version: str
    writes_sampler_controls: Literal[False]


@dataclass(frozen=True)
class FinalRestartPolicy:
    """Immutable final restart policy consumed by ``flowa_core_runtime``."""

    policy_id: PolicyId
    writer_id: MechanismId
    run_id: RunId
    target_round: int
    outer_cycle_id: int
    beta_by_channel: Mapping[ChannelName, FactorValue]
    alpha_by_channel: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    schedule_sample: CosineScheduleSample | None
    freeze_admission_by_channel: Mapping[ChannelName, bool]
    ledger_row_id: LedgerRowId
    policy_hash: ArtifactHash
    created_at_round: int


# ---------------------------------------------------------------------------
# Dataclass validators
# ---------------------------------------------------------------------------


def validate_final_restart_policy(p: FinalRestartPolicy) -> ValidationResult:
    """Validate :class:`FinalRestartPolicy`.

    Rejects when ``writer_id`` is not exactly ``"inference.adaptive_reflow"`` or
    ``policy_hash`` does not match the deterministic recompute of the canonical
    field tuple.
    """
    errors: list[str] = []
    if p.writer_id != "inference.adaptive_reflow":
        errors.append(
            f"writer_id must be 'inference.adaptive_reflow'; got {p.writer_id!r}"
        )
    expected_hash = hash_policy_hash(p)
    if p.policy_hash != expected_hash:
        errors.append(
            "policy_hash does not match deterministic recompute of "
            "(policy_id, writer_id, run_id, target_round, outer_cycle_id, "
            "beta_by_channel, alpha_by_channel, fresh_noise_floor_by_channel, "
            "freeze_admission_by_channel)"
        )
    if errors:
        return (False, tuple(errors))
    return _ok()
