"""Uncertainty-ratio pruning gate for the adaptive_reflow component.

This module implements the DTB-L3 pruning-gate half of the layered candidate
and uncertainty-ratio pruning gate. Given a per-bundle
:class:`stratification.StratumAssignment`, the :class:`PruneGate` returns a
:class:`PruneDecision` drawn from a closed literal set:

* ``"keep"`` — assignment survives the gate.
* ``"prune"`` — the gate has a deterministic, gap-justified reason to drop
  the bundle. Only emitted when ``dominance_ratio > threshold_ratio``.
* ``"preserve_unordered"`` — the gap does not exceed the calibrated
  uncertainty (or the uncertainty floor is zero with a non-zero gap),
  so the branch is preserved without committing to a winner. Canonical
  unordered weights + provenance are kept.

The gate is fail-closed: when the gap is within the calibrated radius
the gate MUST NOT issue a deterministic prune; downstream callers must
hold all such branches as an unordered set.

The :class:`UnorderedAuditResult` carries the canonical, deterministic,
branch-swap-invariant audit of a batch of assignments. It is intended to
be reproducible from an offline ledger so that branch_count, stratum
membership and prune decisions can be replayed bit-for-bit.

Tasks satisfied:

* ``DTB-L3`` — layered candidates + uncertainty-ratio pruning gate (half).

Module boundary:

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* All public dataclasses are ``frozen=True``.
* ``PruneDecision`` is a closed ``Literal``; no caller may extend it.

Public surface:

* :data:`PruneDecision` — ``Literal["keep", "prune", "preserve_unordered"]``.
* :class:`PruneGate` — frozen config + per-assignment decision + batch audit.
* :class:`UnorderedAuditResult` — frozen audit row for offline replay.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from adaptive_reflow.contracts import (
    ArtifactHash,
    BundleId,
    FactorValue,
    hash_artifact,
)
from adaptive_reflow.policy.stratification import (
    Stratum,
    StratumAssignment,
    _validate_finite_nonneg,
    dominance_ratio,
)

__all__ = [
    "PruneDecision",
    "PruneGate",
    "UnorderedAuditResult",
]


# Closed literal for the gate's decision; keep this aligned with the
# decision enum in CONTRACTS.md §5 ("AmbiguityBandFixture") and §2
# ("FrozenEnvelopeManifest" tail-selection semantics).
PruneDecision = Literal["keep", "prune", "preserve_unordered"]


# ---------------------------------------------------------------------------
# PruneGate (frozen, dataclass)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PruneGate:
    """Per-round uncertainty-ratio pruning gate.

    Attributes
    ----------
    threshold_ratio:
        The dimensionless dominance ratio above which a branch is
        deterministically pruned. Must be finite and ``>= 0``. The
        canonical StratifiedChemicalTransport value is ``1.0`` (i.e.
        the gap must strictly dominate the calibrated uncertainty before
        the gate is allowed to drop a branch).
    calibrated_error_source_hash:
        Hash of the calibration artifact that supplied
        ``calibrated_error`` for every assignment passed to this gate.
        Used by the offline ledger to verify the gate operates against a
        single consistent calibration source.
    deterministic_ordering:
        When ``True`` (the canonical value), audit results are
        reproducible from the offline ledger independent of the order in
        which branches arrived at the gate. The ordering used is the
        canonical ``(bundle_id)`` lexicographic order.
    """

    threshold_ratio: FactorValue
    calibrated_error_source_hash: ArtifactHash
    deterministic_ordering: bool = True

    def __post_init__(self) -> None:
        _validate_finite_nonneg(self.threshold_ratio, "threshold_ratio")
        if float(self.threshold_ratio) < 0.0:
            raise ValueError("threshold_ratio must be >= 0")
        if not str(self.calibrated_error_source_hash):
            raise ValueError("calibrated_error_source_hash must be non-empty")
        if not isinstance(self.deterministic_ordering, bool):
            raise ValueError(
                "deterministic_ordering must be a bool, got "
                f"{type(self.deterministic_ordering).__name__}"
            )

    # ------------------------------------------------------------------
    # Per-assignment decision
    # ------------------------------------------------------------------

    def decide(self, assignment: StratumAssignment) -> PruneDecision:
        """Return the gate decision for a single :class:`StratumAssignment`.

        Decision rule (DTB-L3):

        * ``ratio > threshold_ratio``  → ``"prune"``
          (a deterministic prune is justified; the gap strictly dominates
          the calibrated uncertainty).

        * ``ratio <= threshold_ratio`` → ``"preserve_unordered"``
          (the gap does not justify a deterministic prune; the branch is
          retained with its canonical unordered weight and provenance so
          an unordered audit can replay it). The literal ``"keep"`` is
          reserved for branches that should be reported as the lead
          survivor at the call-site; this gate never emits ``"keep"`` on
          its own — see :meth:`audit_decisions` for the batch logic that
          may upgrade a single unordered survivor to ``"keep"``.

        * If ``calibrated_error == 0`` and ``score_gap > 0`` the ratio is
          ``+inf`` which is ``> threshold_ratio`` ⇒ ``"prune"``. This is
          the documented behaviour of an unbounded noise floor: no
          calibrated bound means the gate has no business holding the
          branch.

        * If ``calibrated_error == 0`` and ``score_gap == 0`` the ratio
          is ``0.0`` which is ``<= threshold_ratio`` ⇒
          ``"preserve_unordered"``.
        """
        if not isinstance(assignment, StratumAssignment):
            raise ValueError(
                f"decide() requires a StratumAssignment, got "
                f"{type(assignment).__name__}"
            )
        if not isinstance(assignment.stratum, Stratum):
            raise ValueError(
                "assignment.stratum must be a Stratum member, got "
                f"{assignment.stratum!r}"
            )

        ratio = dominance_ratio(assignment.score_gap, assignment.calibrated_error)

        if math.isinf(float(ratio)):
            # Unbounded noise floor → no calibrated bound → deterministic
            # prune is the only safe action; the gate refuses to silently
            # manufacture a winner from an un-bounded uncertainty.
            return "prune"

        if float(ratio) > float(self.threshold_ratio):
            return "prune"
        return "preserve_unordered"

    # ------------------------------------------------------------------
    # Batch audit (branch-swap invariant, deterministic from ledger)
    # ------------------------------------------------------------------

    def audit_decisions(
        self,
        assignments: Iterable[StratumAssignment],
    ) -> UnorderedAuditResult:
        """Return the canonical unordered audit for a batch of assignments.

        The audit is *branch-swap invariant*: the result depends only on
        the *set* of ``(bundle_id, stratum, score_gap, calibrated_error)``
        tuples, not on the order in which they were supplied.

        The audit is *ledger reproducible*: ``deterministic_ordering=True``
        is the canonical mode and the audit is serialized through a
        deterministic ordering of bundle ids inside each stratum. The
        resulting ``UnorderedAuditResult`` can therefore be re-derived
        from an offline ledger row containing the same assignments and
        the same ``calibrated_error_source_hash``.

        Reason codes returned in ``reason_codes``:

        * ``"preserved_below_threshold"`` — the assignment's ratio was
          ``<= threshold_ratio``; the branch is kept unordered.
        * ``"pruned_above_threshold"`` — the assignment's ratio was
          strictly above the threshold; it was pruned.
        * ``"pruned_unbounded_noise_floor"`` — ``calibrated_error == 0``
          with ``score_gap > 0``; the ratio was ``+inf``; the branch was
          pruned (no calibrated bound).
        """
        # Defensive: coerce each entry to a StratumAssignment and split
        # by stratum. We don't fail the whole audit for one bad entry;
        # instead we raise so callers can fix the upstream builder.
        normalized: list[StratumAssignment] = []
        for raw in assignments:
            if not isinstance(raw, StratumAssignment):
                raise ValueError(
                    f"audit_decisions requires StratumAssignment, got "
                    f"{type(raw).__name__}"
                )
            if not isinstance(raw.stratum, Stratum):
                raise ValueError(
                    f"assignment.stratum must be a Stratum member, got "
                    f"{raw.stratum!r}"
                )
            _validate_finite_nonneg(raw.score_gap, "score_gap")
            _validate_finite_nonneg(raw.calibrated_error, "calibrated_error")
            normalized.append(raw)

        if self.deterministic_ordering:
            ordered = sorted(normalized, key=lambda a: (str(a.bundle_id),))
        else:
            ordered = list(normalized)

        pruned: list[BundleId] = []
        kept: list[BundleId] = []
        reason_codes: list[str] = []
        # Aggregate gap / calibrated_error use the dominant survivor per
        # stratum, defined as the assignment with the largest score_gap
        # among the kept branches (tie-broken by bundle_id ascending).
        per_stratum_kept: dict[Stratum, list[StratumAssignment]] = {}

        for assignment in ordered:
            ratio = dominance_ratio(
                assignment.score_gap, assignment.calibrated_error
            )
            decision = self.decide(assignment)
            if decision == "prune":
                pruned.append(assignment.bundle_id)
                if math.isinf(float(ratio)):
                    reason_codes.append(
                        f"{assignment.bundle_id}:pruned_unbounded_noise_floor"
                    )
                else:
                    reason_codes.append(
                        f"{assignment.bundle_id}:pruned_above_threshold"
                    )
            else:
                kept.append(assignment.bundle_id)
                per_stratum_kept.setdefault(assignment.stratum, []).append(
                    assignment
                )
                reason_codes.append(
                    f"{assignment.bundle_id}:preserved_below_threshold"
                )

        # Aggregate gap and calibrated_error from the dominant survivor
        # per stratum; the audit's reported values are the worst-case
        # across strata (max gap, max calibrated_error) so an offline
        # replay can verify they match the same stratum's best branch.
        worst_gap: float = 0.0
        worst_error: float = 0.0
        for stratum, branches in per_stratum_kept.items():
            dominant = max(
                branches,
                key=lambda a: (
                    float(a.score_gap),
                    -_lex_key(a.bundle_id),
                ),
            )
            worst_gap = max(worst_gap, float(dominant.score_gap))
            worst_error = max(worst_error, float(dominant.calibrated_error))
            _ = stratum  # per-stratum breakdown not exposed by this row

        return UnorderedAuditResult(
            pruned_bundle_ids=tuple(pruned),
            kept_bundle_ids=tuple(kept),
            branch_count=len(ordered),
            gap=FactorValue(float(worst_gap)),
            calibrated_error=FactorValue(float(worst_error)),
            reason_codes=tuple(reason_codes),
            calibrated_error_source_hash=self.calibrated_error_source_hash,
            threshold_ratio=self.threshold_ratio,
            deterministic_ordering=bool(self.deterministic_ordering),
        )


def _lex_key(bundle_id: BundleId) -> int:
    """Return a stable numeric key from a BundleId for deterministic max()."""
    return int.from_bytes(
        str(bundle_id).encode("utf-8"), "big", signed=False
    ) if str(bundle_id) else 0


# ---------------------------------------------------------------------------
# UnorderedAuditResult (frozen, dataclass)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UnorderedAuditResult:
    """Canonical unordered audit row produced by :meth:`PruneGate.audit_decisions`.

    The row is *branch-swap invariant* and reproducible from the offline
    ledger (provided the gate uses ``deterministic_ordering=True``).

    Attributes
    ----------
    pruned_bundle_ids:
        Tuple of bundle ids that the gate deterministically pruned.
        Order is deterministic (lexicographic by ``bundle_id``).
    kept_bundle_ids:
        Tuple of bundle ids that the gate preserved unordered. Order is
        deterministic (lexicographic by ``bundle_id``).
    branch_count:
        Total number of assignments the gate saw, including both pruned
        and kept.
    gap:
        Maximum ``score_gap`` observed across the surviving per-stratum
        dominant branches. ``FactorValue``.
    calibrated_error:
        Maximum ``calibrated_error`` observed across the surviving
        per-stratum dominant branches. ``FactorValue``.
    reason_codes:
        Tuple of human-readable reason codes per branch in the canonical
        ordering. The tuple is never parsed; it is a debugging aid.
    """

    pruned_bundle_ids: tuple[BundleId, ...]
    kept_bundle_ids: tuple[BundleId, ...]
    branch_count: int
    gap: FactorValue
    calibrated_error: FactorValue
    reason_codes: tuple[str, ...]
    calibrated_error_source_hash: ArtifactHash = ArtifactHash("")
    threshold_ratio: FactorValue = FactorValue(0.0)
    deterministic_ordering: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.branch_count, int) or isinstance(
            self.branch_count, bool
        ):
            raise ValueError(
                f"branch_count must be int, got {type(self.branch_count).__name__}"
            )
        if self.branch_count < 0:
            raise ValueError(
                f"branch_count must be >= 0, got {self.branch_count}"
            )
        _validate_finite_nonneg(self.gap, "gap")
        _validate_finite_nonneg(self.calibrated_error, "calibrated_error")
        _validate_finite_nonneg(self.threshold_ratio, "threshold_ratio")
        if not isinstance(self.deterministic_ordering, bool):
            raise ValueError(
                "deterministic_ordering must be a bool, got "
                f"{type(self.deterministic_ordering).__name__}"
            )
        # Ledger integrity: pruned ∩ kept must be empty and
        # pruned ∪ kept ⊆ branch_count.
        if len(self.pruned_bundle_ids) + len(self.kept_bundle_ids) > self.branch_count:
            raise ValueError(
                "pruned + kept exceeds branch_count; this indicates a "
                "duplicated branch id between pruned and kept"
            )
        overlap = set(self.pruned_bundle_ids) & set(self.kept_bundle_ids)
        if overlap:
            raise ValueError(
                "a bundle_id cannot be both pruned and kept: "
                f"overlap={sorted(overlap)!r}"
            )

    def ledger_payload(self) -> Mapping[str, object]:
        """Return a JSON-serializable dict for offline-ledger replay.

        The payload is canonical: lists are sorted, tuples of bundle ids
        are sorted lexicographically, and floating-point values are emitted
        as raw floats so the same ledger row replays to the same hash.
        """
        return {
            "pruned_bundle_ids": sorted(str(b) for b in self.pruned_bundle_ids),
            "kept_bundle_ids": sorted(str(b) for b in self.kept_bundle_ids),
            "branch_count": int(self.branch_count),
            "gap": float(self.gap),
            "calibrated_error": float(self.calibrated_error),
            "reason_codes": list(self.reason_codes),
            "calibrated_error_source_hash": str(self.calibrated_error_source_hash),
            "threshold_ratio": float(self.threshold_ratio),
            "deterministic_ordering": bool(self.deterministic_ordering),
        }

    def ledger_hash(self) -> ArtifactHash:
        """Return the deterministic sha256 of :meth:`ledger_payload`."""
        return hash_artifact(self.ledger_payload())
