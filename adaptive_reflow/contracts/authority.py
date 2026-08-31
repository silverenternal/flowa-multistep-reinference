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
    # ADR-0010 — cosine-driven memory fraction. When ``True`` (default)
    # the engine derives ``beta_by_channel`` from the schedule's
    # ``n_cap`` (``beta = n_cap`` so ``memory_fraction = 1 - n_cap``).
    # When ``False`` the caller-supplied ``beta_by_channel`` is preserved
    # verbatim (back-compat for callers that want to lock beta
    # independently of the schedule). The flag is read by
    # :meth:`adaptive_reflow.frame.engine.Engine.run_round` and is
    # included in the canonical ``policy_hash`` recompute so two
    # policies that differ only by this flag hash differently.
    beta_from_schedule: bool = True
    # Contract 1.2 — driver / engine dedup. When ``True`` the
    # :class:`adaptive_reflow.algorithm.PolicyDriverProtocol` has
    # already mutated ``beta_by_channel`` (e.g. a
    # :class:`ScheduleDerivedPolicyDriver` writing ``beta = n_cap``).
    # The engine reads this flag and SKIPS the inline
    # ``_policy_with_schedule_beta`` re-override so the per-round
    # ``beta`` is set by exactly one source of truth (the driver).
    # ``False`` (the default) preserves the legacy engine-driven
    # path for callers that opt out of the driver abstraction.
    driver_computed_beta: bool = False


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
    # P2-32 (F-56 / audit) — the four channel-keyed mappings must carry
    # the same :data:`ChannelName` set; otherwise the policy can silently
    # disagree with itself (e.g. ``beta_by_channel`` defines ``"image"``
    # but ``alpha_by_channel`` defines ``"label"``). Reject when the
    # channel-name key sets disagree. ``freeze_admission_by_channel`` is
    # allowed to be a strict subset of the other three (some callers
    # only freeze a subset of channels), but it must not introduce
    # *new* channel names that aren't already in ``beta_by_channel``.
    beta_keys = set(p.beta_by_channel)
    alpha_keys = set(p.alpha_by_channel)
    floor_keys = set(p.fresh_noise_floor_by_channel)
    freeze_keys = set(p.freeze_admission_by_channel)
    if alpha_keys != beta_keys:
        errors.append(
            "alpha_by_channel key set must equal beta_by_channel key set; "
            f"got alpha_keys={sorted(alpha_keys)!r} vs beta_keys={sorted(beta_keys)!r}"
        )
    if floor_keys != beta_keys:
        errors.append(
            "fresh_noise_floor_by_channel key set must equal beta_by_channel key set; "
            f"got floor_keys={sorted(floor_keys)!r} vs beta_keys={sorted(beta_keys)!r}"
        )
    if not freeze_keys.issubset(beta_keys):
        errors.append(
            "freeze_admission_by_channel key set must be a subset of "
            f"beta_by_channel; got freeze_keys={sorted(freeze_keys)!r} "
            f"vs beta_keys={sorted(beta_keys)!r}"
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
