"""Adaptive reflow typed contracts — candidate archive (DTB-R4).

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .types import ArtifactHash, BundleId
from .validators import ValidationResult, _err, _ok

# ---------------------------------------------------------------------------
# Candidate archive quota + audit trail (CONTRACTS.md §8) — DTB-R4
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArchiveQuota:
    """Bounded global quality budget for the same-sample candidate archive.

    The archive uses these fields to cap:

    * overall size (``max_archive_size``) — keeps token/memory/runtime
      budgets bounded;
    * per-source influence (``max_per_source_influence``) — prevents any
      single bundle from dominating the global restart mass;
    * fresh-noise complement (``min_fresh_noise_mass``) — guarantees a
      floor of fresh-noise mass per round;
    * consecutive reuse (``max_consecutive_reuse_rounds``) — guarantees
      the archive cannot collapse into a fixed point.
    """

    max_archive_size: int
    max_per_source_influence: float
    min_fresh_noise_mass: float
    max_consecutive_reuse_rounds: int

    def __post_init__(self) -> None:
        # Field validation: max_archive_size must be a positive int,
        # per-source influence and fresh-noise mass must be in [0, 1]
        # (with per-source influence strictly positive), and
        # max_consecutive_reuse_rounds must be a non-negative int.
        ok, errors = validate_archive_quota(self)
        if not ok:
            raise ValueError("invalid ArchiveQuota: " + "; ".join(errors))


def validate_archive_quota(q: ArchiveQuota) -> ValidationResult:
    """Validate an :class:`ArchiveQuota` row.

    Rejects when ``max_archive_size < 1``,
    ``max_per_source_influence`` is not in ``(0, 1]``,
    ``min_fresh_noise_mass`` is not in ``[0, 1]``, or
    ``max_consecutive_reuse_rounds`` is negative.
    """
    errors: list[str] = []
    if (
        isinstance(q.max_archive_size, bool)
        or not isinstance(q.max_archive_size, int)
        or q.max_archive_size < 1
    ):
        errors.append(
            f"max_archive_size must be a positive int, got {q.max_archive_size!r}"
        )
    if (
        not isinstance(q.max_per_source_influence, (int, float))
        or isinstance(q.max_per_source_influence, bool)
    ):
        errors.append(
            "max_per_source_influence must be a real number, got "
            f"{type(q.max_per_source_influence).__name__}"
        )
    else:
        v = float(q.max_per_source_influence)
        if not math.isfinite(v):
            errors.append(
                f"max_per_source_influence must be finite, got {v!r}"
            )
        elif v <= 0.0 or v > 1.0:
            errors.append(
                "max_per_source_influence must be in (0, 1], got "
                f"{v!r}"
            )
    if (
        not isinstance(q.min_fresh_noise_mass, (int, float))
        or isinstance(q.min_fresh_noise_mass, bool)
    ):
        errors.append(
            "min_fresh_noise_mass must be a real number, got "
            f"{type(q.min_fresh_noise_mass).__name__}"
        )
    else:
        v = float(q.min_fresh_noise_mass)
        if not math.isfinite(v):
            errors.append(
                f"min_fresh_noise_mass must be finite, got {v!r}"
            )
        elif v < 0.0 or v > 1.0:
            errors.append(
                "min_fresh_noise_mass must be in [0, 1], got "
                f"{v!r}"
            )
    if (
        isinstance(q.max_consecutive_reuse_rounds, bool)
        or not isinstance(q.max_consecutive_reuse_rounds, int)
        or q.max_consecutive_reuse_rounds < 0
    ):
        errors.append(
            "max_consecutive_reuse_rounds must be a non-negative int, "
            f"got {q.max_consecutive_reuse_rounds!r}"
        )
    if errors:
        return _err(*errors)
    return _ok()


@dataclass(frozen=True)
class ArchiveAuditTrail:
    """Audit-only record emitted by ``SameSampleArchive.select_one_bundle``.

    The audit trail is informational: the per-channel rules always see
    ONE :class:`RoundResultBundle`; unselected candidates are kept here
    for audit only and never influence channel decisions directly.

    ``selected_bundle_id`` is ``None`` iff the archive was empty, every
    candidate was over the per-source influence cap, or the consecutive
    reuse cap was exceeded for every eligible candidate.
    """

    selected_bundle_id: BundleId | None
    rejected_bundle_ids: tuple[BundleId, ...]
    dedup_count: int
    total_influence_kept: float
    archive_size: int = 0
    fresh_noise_mass_used: float = 0.0
    fresh_noise_floor_required: float = 0.0
    consecutive_reuse_count: int = 0
    max_consecutive_reuse_rounds: int = 0
    current_round: int = 0
    audit_hash: ArtifactHash = field(default=ArtifactHash(""))
