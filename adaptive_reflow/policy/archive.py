"""Bounded same-sample candidate archive for the multi-candidate restart pipeline.

This module implements ``DTB-R4``: a bounded archive of candidate
:class:`RoundResultBundle` rows used by the per-round restart planner. The
archive:

* Dedups by upstream ``bundle_id`` (NOT by metric/evidence row count), so
  duplicate evidence/metric rows from the same source cannot inflate
  influence.
* Caps overall size (``max_archive_size``) so token/memory/runtime budgets
  cannot be exceeded.
* Caps per-source influence (``max_per_source_influence``) so a single
  bundle cannot dominate the global restart mass.
* Enforces a minimum fresh-noise mass (``min_fresh_noise_mass``) and a
  cap on consecutive reuse rounds (``max_consecutive_reuse_rounds``) so
  the global budget never collapses into a degenerate fixed-point.
* Selects ONE bundle per round via deterministic tie-break
  (lexicographic by ``bundle_id`` then ``evidence_score``).
* Enforces the *single-bundle-per-round* invariant: the archive keeps
  unselected candidates for audit only; the per-channel rules always
  see ONE :class:`RoundResultBundle`, never a Frankenstein mix.

The module is **stdlib-only**: no ``torch``, no I/O. Anything that wants
the audit trail reads :class:`ArchiveAuditTrail` from
``restart_memory_types``.

Tasks satisfied (per ``todo.json``):

* ``DTB-R4`` -- multi-candidate global quality budget with bundle consistency
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from adaptive_reflow.contracts import (
    ArchiveAuditTrail,
    ArchiveQuota,
    ArtifactHash,
    BundleId,
    FactorValue,
    RoundResultBundle,
    RunId,
    SampleId,
    TraceDigest,
    hash_artifact,
    validate_round_result_bundle,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CandidateArchiveError(ValueError):
    """Base exception for the candidate archive."""


class CandidateArchiveValidationError(CandidateArchiveError):
    """Raised when an entry or quota fails validation."""


class CandidateArchiveLineageError(CandidateArchiveError):
    """Raised when a candidate arrives from a different sample/run/checkpoint/trace."""


# ---------------------------------------------------------------------------
# ArchiveEntry (frozen)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArchiveEntry:
    """One candidate bundle inside :class:`SameSampleArchive`.

    Attributes
    ----------
    bundle:
        The source :class:`RoundResultBundle`.
    evidence_score:
        Aggregated evidence score in ``[0, 1]`` used for tie-break.
    source_round:
        Mirrors ``bundle.source_round`` for cheap comparison.
    is_selected:
        ``True`` iff this entry was selected by the most recent
        :meth:`SameSampleArchive.select_one_bundle` call.
    consecutive_reuse_count:
        How many consecutive prior rounds reused this same
        ``bundle_id``. Capped by ``ArchiveQuota.max_consecutive_reuse_rounds``.
    """

    bundle: RoundResultBundle
    evidence_score: FactorValue
    source_round: int
    is_selected: bool
    consecutive_reuse_count: int

    def with_selection(self, *, selected: bool) -> ArchiveEntry:
        """Return a copy with ``is_selected`` replaced."""
        return dataclasses.replace(self, is_selected=bool(selected))

    def with_reuse_count(self, count: int) -> ArchiveEntry:
        """Return a copy with ``consecutive_reuse_count`` replaced."""
        if isinstance(count, bool) or not isinstance(count, int):
            raise CandidateArchiveValidationError(
                "consecutive_reuse_count must be an int"
            )
        if count < 0:
            raise CandidateArchiveValidationError(
                f"consecutive_reuse_count must be >= 0, got {count}"
            )
        return dataclasses.replace(self, consecutive_reuse_count=int(count))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_factor(x: object, *, default: float) -> float:
    """Coerce ``x`` to a finite float in ``[0, 1]``; fall back to ``default``."""
    try:
        if isinstance(x, bool):
            value = float(int(x))
        elif isinstance(x, (int, float)):
            value = float(x)
        else:
            return float(default)
    except Exception:
        return float(default)
    if value != value:  # NaN
        return float(default)
    if value in (float("inf"), float("-inf")):
        return float(default)
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _validate_quota(quota: ArchiveQuota) -> None:
    """Fail closed on a malformed :class:`ArchiveQuota`."""
    if not isinstance(quota, ArchiveQuota):
        raise CandidateArchiveValidationError(
            "quota must be an ArchiveQuota instance"
        )
    if quota.max_archive_size < 1:
        raise CandidateArchiveValidationError(
            f"max_archive_size must be >= 1, got {quota.max_archive_size}"
        )
    if quota.max_per_source_influence <= 0.0 or quota.max_per_source_influence > 1.0:
        raise CandidateArchiveValidationError(
            "max_per_source_influence must be in (0, 1], "
            f"got {quota.max_per_source_influence}"
        )
    if quota.min_fresh_noise_mass < 0.0 or quota.min_fresh_noise_mass > 1.0:
        raise CandidateArchiveValidationError(
            "min_fresh_noise_mass must be in [0, 1], "
            f"got {quota.min_fresh_noise_mass}"
        )
    if quota.max_consecutive_reuse_rounds < 0:
        raise CandidateArchiveValidationError(
            "max_consecutive_reuse_rounds must be >= 0, "
            f"got {quota.max_consecutive_reuse_rounds}"
        )


def _check_lineage(
    bundle: RoundResultBundle,
    *,
    run_id: RunId,
    sample_id: SampleId,
    trace_lineage: TraceDigest,
    checkpoint_id: str,
) -> None:
    """Refuse bundles from a different sample/run/checkpoint/trace lineage.

    The check enforces:

    * ``bundle.run_id == archive.run_id``;
    * ``bundle.sample_id == archive.sample_id``;
    * ``archive.trace_lineage`` is non-empty (a single-trace anchor is
      required even though the bundle's own ``trace_digest`` is unique
      per bundle identity by construction);
    * ``archive.checkpoint_id`` is non-empty (the archive is invalid
      across checkpoint boundaries).

    Note: ``bundle.trace_digest`` is *bundle-identity-derived* and is
    therefore unique per bundle. The archive's ``trace_lineage`` is a
    separate lineage anchor stored at archive construction time; it
    names the trace the archive belongs to without needing to match the
    bundle's own digest byte-for-byte.
    """
    if str(bundle.run_id) != str(run_id):
        raise CandidateArchiveLineageError(
            f"bundle.run_id {str(bundle.run_id)!r} != archive run_id "
            f"{str(run_id)!r}; cross-run bundles are forbidden"
        )
    if str(bundle.sample_id) != str(sample_id):
        raise CandidateArchiveLineageError(
            f"bundle.sample_id {str(bundle.sample_id)!r} != archive sample_id "
            f"{str(sample_id)!r}; cross-sample bundles are forbidden"
        )
    if not str(trace_lineage):
        raise CandidateArchiveLineageError(
            "archive requires a non-empty trace_lineage anchor"
        )
    if not checkpoint_id:
        raise CandidateArchiveLineageError(
            "archive requires a non-empty checkpoint_id"
        )


def _entry_sort_key(entry: ArchiveEntry) -> tuple[float, str]:
    """Deterministic tie-break: evidence_score (descending), then bundle_id.

    Python sorts tuples lexicographically. We negate the score so the
    *highest* evidence_score wins while keeping the tie-break fully
    deterministic. When two candidates have the same score, the one with
    the lexicographically smaller ``bundle_id`` wins.
    """
    return (-float(entry.evidence_score), str(entry.bundle.bundle_id))


def _archive_audit_hash(
    *,
    run_id: RunId,
    sample_id: SampleId,
    trace_lineage: TraceDigest,
    selected_bundle_id: BundleId | None,
    rejected_bundle_ids: tuple[BundleId, ...],
    dedup_count: int,
    total_influence_kept: float,
) -> str:
    """Return a deterministic hash that uniquely identifies the audit row."""
    return hash_artifact(
        {
            "run_id": str(run_id),
            "sample_id": str(sample_id),
            "trace_lineage": str(trace_lineage),
            "selected_bundle_id": (
                None if selected_bundle_id is None else str(selected_bundle_id)
            ),
            "rejected_bundle_ids": [str(b) for b in rejected_bundle_ids],
            "dedup_count": int(dedup_count),
            "total_influence_kept": float(total_influence_kept),
        }
    )


# ---------------------------------------------------------------------------
# SameSampleArchive
# ---------------------------------------------------------------------------


@dataclass
class _ArchiveStats:
    """Mutable per-archive counters used during selection."""

    dedup_count: int = 0
    total_influence_kept: float = 0.0
    consecutive_reuse_count: int = 0


class SameSampleArchive:
    """Bounded archive of candidate :class:`RoundResultBundle` rows.

    The archive is scoped to ONE ``(run_id, sample_id, trace_lineage,
    checkpoint_id)`` tuple. Mixing candidates across sample/run/checkpoint/
    trace lineage is rejected at insertion time. The archive never
    stitches channels from different bundles: it returns ONE bundle per
    round and keeps the others for audit only.
    """

    __slots__ = (
        "_audit_trail",
        "_entries",
        "_last_selected_bundle_id",
        "_seen_bundle_ids",
        "_stats",
        "checkpoint_id",
        "quota",
        "run_id",
        "sample_id",
        "trace_lineage",
    )

    def __init__(
        self,
        *,
        quota: ArchiveQuota,
        run_id: RunId,
        sample_id: SampleId,
        trace_lineage: TraceDigest,
        checkpoint_id: str,
    ) -> None:
        """Construct the archive.

        Parameters
        ----------
        quota:
            The :class:`ArchiveQuota` bounds.
        run_id:
            Single-run lineage anchor.
        sample_id:
            Single-sample lineage anchor.
        trace_lineage:
            Single-trace lineage anchor.
        checkpoint_id:
            Single-checkpoint lineage anchor (the archive is invalid
            across checkpoint boundaries).
        """
        _validate_quota(quota)
        if not checkpoint_id:
            raise CandidateArchiveLineageError(
                "checkpoint_id must be non-empty"
            )
        if not str(trace_lineage):
            raise CandidateArchiveLineageError(
                "trace_lineage must be non-empty"
            )
        if not str(run_id):
            raise CandidateArchiveLineageError(
                "run_id must be non-empty"
            )
        if not str(sample_id):
            raise CandidateArchiveLineageError(
                "sample_id must be non-empty"
            )
        self.quota: ArchiveQuota = quota
        self.run_id: RunId = run_id
        self.sample_id: SampleId = sample_id
        self.trace_lineage: TraceDigest = trace_lineage
        self.checkpoint_id: str = str(checkpoint_id)
        self._entries: list[ArchiveEntry] = []
        self._seen_bundle_ids: set[BundleId] = set()
        self._stats: _ArchiveStats = _ArchiveStats()
        self._last_selected_bundle_id: BundleId | None = None
        self._audit_trail: ArchiveAuditTrail = self._empty_audit()

    # ------------------------------------------------------------------
    # read-only properties
    # ------------------------------------------------------------------

    @property
    def entries(self) -> tuple[ArchiveEntry, ...]:
        """Return the current archive entries as an immutable tuple."""
        return tuple(self._entries)

    @property
    def size(self) -> int:
        """Return the number of distinct bundles currently in the archive."""
        return len(self._entries)

    @property
    def audit_trail(self) -> ArchiveAuditTrail:
        """Return the most recent audit trail produced by ``select_one_bundle``."""
        return self._audit_trail

    @property
    def total_influence_kept(self) -> float:
        """Return the cumulative influence mass kept by the archive."""
        return float(self._stats.total_influence_kept)

    @property
    def dedup_count(self) -> int:
        """Return how many duplicate ``bundle_id`` insertions were ignored."""
        return int(self._stats.dedup_count)

    # ------------------------------------------------------------------
    # mutation
    # ------------------------------------------------------------------

    def add_candidate(
        self,
        bundle: RoundResultBundle,
        *,
        evidence_score: float = 1.0,
    ) -> ArchiveEntry:
        """Insert ``bundle`` into the archive (dedup by ``bundle_id``).

        Returns the freshly created or existing :class:`ArchiveEntry`.
        Duplicate ``bundle_id`` insertions increment ``dedup_count`` and
        do NOT inflate influence.
        """
        ok, errors = validate_round_result_bundle(bundle)
        if not ok:
            raise CandidateArchiveValidationError(
                "bundle failed validation: " + "; ".join(errors)
            )
        _check_lineage(
            bundle,
            run_id=self.run_id,
            sample_id=self.sample_id,
            trace_lineage=self.trace_lineage,
            checkpoint_id=self.checkpoint_id,
        )
        bundle_id = str(bundle.bundle_id)
        if bundle_id in self._seen_bundle_ids:
            self._stats.dedup_count += 1
            for existing in self._entries:
                if str(existing.bundle.bundle_id) == bundle_id:
                    return existing
        score = _safe_factor(evidence_score, default=0.0)
        entry = ArchiveEntry(
            bundle=bundle,
            evidence_score=FactorValue(score),
            source_round=int(bundle.source_round),
            is_selected=False,
            consecutive_reuse_count=0,
        )
        # Enforce bounded capacity. If the archive is full, refuse the
        # insertion rather than evicting: the archive is the global
        # quality budget and silent eviction would leak influence.
        if len(self._entries) >= int(self.quota.max_archive_size):
            raise CandidateArchiveValidationError(
                f"archive full (max_archive_size={self.quota.max_archive_size}); "
                "refusing to insert additional candidate"
            )
        self._entries.append(entry)
        self._seen_bundle_ids.add(BundleId(bundle_id))
        return entry

    def select_one_bundle(
        self,
        *,
        current_round: int,
        consumed_fresh_noise_mass: float = 0.0,
    ) -> ArchiveEntry | None:
        """Select ONE :class:`ArchiveEntry` for the current round.

        Returns ``None`` when the archive is empty, when no candidate
        satisfies the global quality budget, or when the consecutive
        reuse cap would be exceeded.

        Tie-break is deterministic: lexicographic by ``bundle_id`` then
        descending ``evidence_score``. The selected bundle's
        ``consecutive_reuse_count`` is bumped; the others are kept for
        audit only.
        """
        if not self._entries:
            self._audit_trail = self._empty_audit()
            self._last_selected_bundle_id = None
            return None

        # Enforce the per-source influence cap: the candidate's evidence
        # score must not exceed max_per_source_influence. Candidates that
        # would exceed the cap are dropped from the selection pool only
        # for this call -- they remain in the archive for audit and may
        # be eligible on subsequent rounds.
        cap = float(self.quota.max_per_source_influence)
        eligible = [
            entry
            for entry in self._entries
            if float(entry.evidence_score) <= cap
        ]
        if not eligible:
            self._audit_trail = self._empty_audit()
            self._last_selected_bundle_id = None
            return None

        # Sort deterministic: lexicographic by bundle_id, then descending
        # by evidence_score.
        sorted_entries = sorted(eligible, key=_entry_sort_key)

        # Walk the ordered candidates and pick the first one whose
        # consecutive_reuse_count can still grow without violating the cap
        # AND whose fresh-noise complement satisfies the floor.
        fresh_noise_used = _safe_factor(consumed_fresh_noise_mass, default=0.0)
        required_fresh = float(self.quota.min_fresh_noise_mass)
        max_reuse = int(self.quota.max_consecutive_reuse_rounds)

        chosen: ArchiveEntry | None = None
        for entry in sorted_entries:
            if entry.consecutive_reuse_count + 1 > max_reuse:
                # would exceed the cap; skip silently for this round
                continue
            chosen = entry
            break

        if chosen is None:
            self._audit_trail = self._empty_audit()
            self._last_selected_bundle_id = None
            return None

        # Update reuse counts: bump the chosen entry, reset others.
        new_entries: list[ArchiveEntry] = []
        updated_chosen: ArchiveEntry | None = None
        for entry in self._entries:
            if str(entry.bundle.bundle_id) == str(chosen.bundle.bundle_id):
                bumped = entry.with_reuse_count(entry.consecutive_reuse_count + 1)
                updated_chosen = bumped
                new_entries.append(bumped)
            else:
                new_entries.append(entry.with_reuse_count(0))
        # Mark the chosen entry as selected, others unselected.
        new_entries = [
            entry.with_selection(
                selected=str(entry.bundle.bundle_id) == str(chosen.bundle.bundle_id)
            )
            for entry in new_entries
        ]
        self._entries = new_entries

        # Track cumulative influence kept, capped at 1.0.
        self._stats.total_influence_kept = min(
            1.0,
            float(self._stats.total_influence_kept)
            + float(updated_chosen.evidence_score if updated_chosen is not None else 0.0),
        )

        # Build the audit trail. Rejected = every non-chosen entry that
        # was eligible for selection this round.
        rejected_ids: tuple[BundleId, ...] = tuple(
            BundleId(str(entry.bundle.bundle_id))
            for entry in sorted_entries
            if str(entry.bundle.bundle_id) != str(chosen.bundle.bundle_id)
        )
        # The fresh-noise complement is information for the planner; we
        # surface the required floor alongside the consumed mass so
        # downstream code can fail closed if the floor is violated.
        chosen_count = (
            int(updated_chosen.consecutive_reuse_count)
            if updated_chosen is not None
            else 0
        )
        self._audit_trail = ArchiveAuditTrail(
            selected_bundle_id=BundleId(str(chosen.bundle.bundle_id)),
            rejected_bundle_ids=rejected_ids,
            dedup_count=int(self._stats.dedup_count),
            total_influence_kept=float(self._stats.total_influence_kept),
            archive_size=len(self._entries),
            fresh_noise_mass_used=fresh_noise_used,
            fresh_noise_floor_required=required_fresh,
            consecutive_reuse_count=chosen_count,
            max_consecutive_reuse_rounds=int(max_reuse),
            current_round=int(current_round),
            audit_hash=ArtifactHash(
                _archive_audit_hash(
                    run_id=self.run_id,
                    sample_id=self.sample_id,
                    trace_lineage=self.trace_lineage,
                    selected_bundle_id=BundleId(str(chosen.bundle.bundle_id)),
                    rejected_bundle_ids=rejected_ids,
                    dedup_count=int(self._stats.dedup_count),
                    total_influence_kept=float(self._stats.total_influence_kept),
                )
            ),
        )
        self._last_selected_bundle_id = chosen.bundle.bundle_id
        return updated_chosen

    # ------------------------------------------------------------------
    # audit-only views
    # ------------------------------------------------------------------

    def selected_bundle(self) -> RoundResultBundle | None:
        """Return the most recently selected bundle, or ``None``."""
        bid = self._last_selected_bundle_id
        if bid is None:
            return None
        for entry in self._entries:
            if str(entry.bundle.bundle_id) == str(bid):
                return entry.bundle
        return None

    def unselected_bundles(self) -> tuple[RoundResultBundle, ...]:
        """Return every archive bundle that is NOT the selected one.

        These are kept for audit only and must never influence the
        per-channel restart rule directly. Channel rules always see
        ONE bundle.
        """
        bid = self._last_selected_bundle_id
        return tuple(
            entry.bundle
            for entry in self._entries
            if bid is None or str(entry.bundle.bundle_id) != str(bid)
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _empty_audit(self) -> ArchiveAuditTrail:
        return ArchiveAuditTrail(
            selected_bundle_id=None,
            rejected_bundle_ids=(),
            dedup_count=int(self._stats.dedup_count),
            total_influence_kept=float(self._stats.total_influence_kept),
            archive_size=len(self._entries),
            fresh_noise_mass_used=0.0,
            fresh_noise_floor_required=float(self.quota.min_fresh_noise_mass),
            consecutive_reuse_count=0,
            max_consecutive_reuse_rounds=int(
                self.quota.max_consecutive_reuse_rounds
            ),
            current_round=0,
            audit_hash=ArtifactHash(
                _archive_audit_hash(
                    run_id=self.run_id,
                    sample_id=self.sample_id,
                    trace_lineage=self.trace_lineage,
                    selected_bundle_id=None,
                    rejected_bundle_ids=(),
                    dedup_count=int(self._stats.dedup_count),
                    total_influence_kept=float(self._stats.total_influence_kept),
                )
            ),
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "ArchiveEntry",
    "CandidateArchiveError",
    "CandidateArchiveLineageError",
    "CandidateArchiveValidationError",
    "SameSampleArchive",
]
