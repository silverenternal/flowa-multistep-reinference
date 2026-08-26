"""Tests for the DTB-R4 same-sample candidate archive.

These tests cover:

* Dedup by ``bundle_id`` (NOT by metric/evidence row count).
* Cross-class Frankenstein rejection: best coordinate from round A +
  best charge from round B must never form a mixed restart state.
* Archive size cap (``max_archive_size``) enforced.
* Per-source influence cap (``max_per_source_influence``) enforced.
* Deterministic tie-break reproducible across calls.
* Archive only valid within single-sample/run/checkpoint/trace lineage.

NO torch. NO GPU. NO mutation of inputs.
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure the package root is importable when pytest is invoked from the
# repository root (which is how the brief specifies running tests).
_PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from adaptive_reflow.contracts import (
    ArchiveAuditTrail,
    ArchiveQuota,
    ArtifactHash,
    BundleId,
    ChargeChannelRef,
    ConditionDigest,
    CoordinateChannelRef,
    EvaluatorProvenanceRef,
    FactorValue,
    FeedbackEvidenceRef,
    FrameSpec,
    MaterializationEvidenceRef,
    ProjectedPairChannelRef,
    ProvenanceChain,
    RawPairChannelRef,
    RoundResultBundle,
    RunId,
    SampleId,
    ShapeSpec,
    TraceDigest,
    hash_trace_digest,
)
from adaptive_reflow.policy import (
    ArchiveEntry,
    CandidateArchiveLineageError,
    CandidateArchiveValidationError,
    SameSampleArchive,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_RUN_ID = RunId("run-DTB-R4")
_SAMPLE_ID = SampleId("sample-001")
_CHECKPOINT_ID = "ckpt-0"


def _trace_for(bundle_id: str, source_round: int) -> TraceDigest:
    return hash_trace_digest(
        BundleId(bundle_id),
        int(source_round),
        int(source_round) + 1,
        _RUN_ID,
        _SAMPLE_ID,
    )


def _make_bundle(
    *,
    bundle_id: str,
    source_round: int,
    coordinate_value: float = 0.5,
    charge_value: float = 0.5,
    raw_pair_value: float = 0.5,
    projected_pair_value: float = 0.5,
    run_id: RunId | None = None,
    sample_id: SampleId | None = None,
) -> RoundResultBundle:
    """Build a deterministic RoundResultBundle for tests.

    Each channel carries a ``source_round`` that matches the bundle's
    ``source_round`` so the round-result-bundle validator passes; that
    mirrors the real-world contract enforced by
    :func:`validate_round_result_bundle`.
    """
    rid = run_id if run_id is not None else _RUN_ID
    sid = sample_id if sample_id is not None else _SAMPLE_ID
    round_count = int(source_round) + 1
    bundle_id_typed = BundleId(bundle_id)
    # trace_digest is recomputed from the FINAL run_id / sample_id so
    # the bundle always validates.
    trace_digest = hash_trace_digest(
        bundle_id_typed,
        int(source_round),
        round_count,
        rid,
        sid,
    )
    channel_kwargs = {
        "coordinate_channel": CoordinateChannelRef(
            {
                "source_round": int(source_round),
                "value": float(coordinate_value),
            }
        ),
        "charge_channel": ChargeChannelRef(
            {
                "source_round": int(source_round),
                "value": float(charge_value),
            }
        ),
        "raw_pair_channel": RawPairChannelRef(
            {
                "source_round": int(source_round),
                "value": float(raw_pair_value),
            }
        ),
        "projected_pair_channel": ProjectedPairChannelRef(
            {
                "source_round": int(source_round),
                "value": float(projected_pair_value),
            }
        ),
    }
    return RoundResultBundle(
        bundle_id=bundle_id_typed,
        source_round=int(source_round),
        round_count=round_count,
        run_id=rid,
        sample_id=sid,
        trace_digest=trace_digest,
        condition_digest=ConditionDigest(
            "cd-" + bundle_id
        ),
        feedback_mode="proxy_only",
        calibration_artifact_hash=ArtifactHash("c" * 64),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        materialization_evidence=MaterializationEvidenceRef(
            {"ok": True}
        ),
        evaluator_provenance=EvaluatorProvenanceRef(
            {"ok": True}
        ),
        feedback_evidence=FeedbackEvidenceRef(
            {"ok": True}
        ),
        shape_spec=ShapeSpec({"shape": (1,)}),
        frame_spec=FrameSpec({"frame": "test"}),
        provenance=ProvenanceChain(("test.producer",)),
        created_at_round=int(source_round),
        revoked=False,
        **channel_kwargs,
    )


def _default_quota(**overrides) -> ArchiveQuota:
    defaults = {
        "max_archive_size": 4,
        "max_per_source_influence": 0.8,
        "min_fresh_noise_mass": 0.0,
        "max_consecutive_reuse_rounds": 3,
    }
    defaults.update(overrides)
    return ArchiveQuota(**defaults)


def _new_archive(**quota_overrides) -> SameSampleArchive:
    quota = _default_quota(**quota_overrides)
    trace = _trace_for("archive-trace-anchor", 0)
    return SameSampleArchive(
        quota=quota,
        run_id=_RUN_ID,
        sample_id=_SAMPLE_ID,
        trace_lineage=trace,
        checkpoint_id=_CHECKPOINT_ID,
    )


# ---------------------------------------------------------------------------
# 1. Dedup by upstream bundle_id (NOT metric/evidence row count)
# ---------------------------------------------------------------------------


class TestDedupByBundleId:
    def test_duplicate_bundle_id_does_not_inflate_archive(self):
        archive = _new_archive()
        bundle = _make_bundle(bundle_id="dup-bundle", source_round=2)
        first = archive.add_candidate(bundle, evidence_score=0.5)
        second = archive.add_candidate(bundle, evidence_score=0.5)
        third = archive.add_candidate(bundle, evidence_score=0.5)
        # The archive must hold exactly ONE entry for that bundle_id.
        assert archive.size == 1
        assert first.bundle.bundle_id == second.bundle.bundle_id == third.bundle.bundle_id
        # dedup_count counts the duplicate insertions that were ignored.
        assert archive.dedup_count == 2

    def test_metric_row_count_is_not_a_dedup_key(self):
        """Many duplicate metric rows -> still one archive entry."""
        archive = _new_archive()
        bundle = _make_bundle(bundle_id="metric-bundle", source_round=1)
        # 10 duplicate insertions with different evidence_score values
        # (the values are ignored on dedup because the bundle_id is
        # already present).
        for i in range(10):
            archive.add_candidate(bundle, evidence_score=0.1 * (i + 1))
        assert archive.size == 1
        assert archive.dedup_count == 9
        # The evidence_score is the FIRST one registered; later scores
        # do NOT override the entry.
        first_entry = archive.entries[0]
        assert float(first_entry.evidence_score) == pytest.approx(0.1)

    def test_dedup_count_in_audit_trail(self):
        archive = _new_archive()
        bundle = _make_bundle(bundle_id="audit-bundle", source_round=0)
        for _ in range(3):
            archive.add_candidate(bundle, evidence_score=0.4)
        archive.select_one_bundle(current_round=0)
        audit = archive.audit_trail
        assert isinstance(audit, ArchiveAuditTrail)
        assert audit.dedup_count == 2


# ---------------------------------------------------------------------------
# 2. Cross-class Frankenstein rejection
# ---------------------------------------------------------------------------


class TestCrossClassFrankensteinRejection:
    """The archive must NOT stitch best-coordinate from round A with
    best-charge from round B into a single restart state.
    """

    def test_two_bundles_only_one_is_selected(self):
        archive = _new_archive()
        a = _make_bundle(
            bundle_id="bundle-A",
            source_round=1,
            coordinate_value=0.99,
            charge_value=0.10,
        )
        b = _make_bundle(
            bundle_id="bundle-B",
            source_round=2,
            coordinate_value=0.10,
            charge_value=0.99,
        )
        # Scores below the per-source influence cap (0.8) so both are
        # eligible; selection then picks by deterministic tie-break.
        archive.add_candidate(a, evidence_score=0.5)
        archive.add_candidate(b, evidence_score=0.5)
        entry = archive.select_one_bundle(current_round=3)
        assert entry is not None
        selected = entry.bundle
        # The selected bundle must be ONE of the candidates -- never a
        # Frankenstein blend of A and B channels.
        assert selected.bundle_id in (BundleId("bundle-A"), BundleId("bundle-B"))
        # The selected bundle's coordinate and charge channels come from
        # the SAME source round.
        assert selected.coordinate_channel["source_round"] == selected.source_round
        assert selected.charge_channel["source_round"] == selected.source_round

    def test_unselected_bundle_never_directly_emitted(self):
        """The archive exposes the selected bundle only to callers."""
        archive = _new_archive()
        for bid, sr in (("bundle-A", 1), ("bundle-B", 2)):
            archive.add_candidate(
                _make_bundle(bundle_id=bid, source_round=sr),
                evidence_score=0.5,
            )
        archive.select_one_bundle(current_round=3)
        selected = archive.selected_bundle()
        unselected = archive.unselected_bundles()
        assert selected is not None
        assert selected.bundle_id in (BundleId("bundle-A"), BundleId("bundle-B"))
        # The unselected list contains exactly ONE bundle -- the one
        # that was NOT selected. Per-channel rules must never read from
        # this list.
        assert len(unselected) == 1
        assert unselected[0].bundle_id != selected.bundle_id


# ---------------------------------------------------------------------------
# 3. Archive size cap enforced
# ---------------------------------------------------------------------------


class TestArchiveSizeCap:
    def test_max_archive_size_enforced(self):
        archive = _new_archive(max_archive_size=2)
        archive.add_candidate(_make_bundle(bundle_id="b1", source_round=0))
        archive.add_candidate(_make_bundle(bundle_id="b2", source_round=0))
        assert archive.size == 2
        with pytest.raises(CandidateArchiveValidationError):
            archive.add_candidate(_make_bundle(bundle_id="b3", source_round=0))

    def test_quota_rejects_invalid_max_archive_size(self):
        with pytest.raises((CandidateArchiveValidationError, ValueError)):
            ArchiveQuota(
                max_archive_size=0,
                max_per_source_influence=0.5,
                min_fresh_noise_mass=0.0,
                max_consecutive_reuse_rounds=1,
            )


# ---------------------------------------------------------------------------
# 4. Per-source influence cap enforced
# ---------------------------------------------------------------------------


class TestPerSourceInfluenceCap:
    def test_candidate_over_cap_is_skipped_for_selection(self):
        # cap at 0.5; candidate A scores 0.9 (over cap) so it must be
        # skipped; candidate B scores 0.4 (under cap) so it must be
        # selected.
        archive = _new_archive(max_per_source_influence=0.5)
        archive.add_candidate(
            _make_bundle(bundle_id="A-over-cap", source_round=0),
            evidence_score=0.9,
        )
        archive.add_candidate(
            _make_bundle(bundle_id="B-under-cap", source_round=1),
            evidence_score=0.4,
        )
        entry = archive.select_one_bundle(current_round=0)
        assert entry is not None
        assert entry.bundle.bundle_id == BundleId("B-under-cap")
        # The total influence kept is the score of the chosen entry,
        # capped at 1.0.
        assert archive.total_influence_kept == pytest.approx(0.4)

    def test_quota_rejects_invalid_per_source_influence(self):
        with pytest.raises((CandidateArchiveValidationError, ValueError)):
            ArchiveQuota(
                max_archive_size=4,
                max_per_source_influence=0.0,
                min_fresh_noise_mass=0.0,
                max_consecutive_reuse_rounds=1,
            )
        with pytest.raises((CandidateArchiveValidationError, ValueError)):
            ArchiveQuota(
                max_archive_size=4,
                max_per_source_influence=1.5,
                min_fresh_noise_mass=0.0,
                max_consecutive_reuse_rounds=1,
            )


# ---------------------------------------------------------------------------
# 5. Deterministic tie-break reproducible
# ---------------------------------------------------------------------------


class TestDeterministicTieBreak:
    def test_tie_break_is_lexicographic_by_bundle_id(self):
        """Equal scores -> bundle_id wins (lowest first)."""
        archive_a = _new_archive()
        archive_b = _new_archive()
        for bid, sr in (("zebra", 0), ("alpha", 1), ("mike", 2)):
            archive_a.add_candidate(
                _make_bundle(bundle_id=bid, source_round=sr),
                evidence_score=0.5,
            )
            archive_b.add_candidate(
                _make_bundle(bundle_id=bid, source_round=sr),
                evidence_score=0.5,
            )
        entry_a = archive_a.select_one_bundle(current_round=3)
        entry_b = archive_b.select_one_bundle(current_round=3)
        assert entry_a is not None and entry_b is not None
        # All three have equal scores -> bundle_id lexicographic sort ->
        # "alpha" wins.
        assert entry_a.bundle.bundle_id == BundleId("alpha")
        assert entry_a.bundle.bundle_id == entry_b.bundle.bundle_id

    def test_tie_break_descending_by_evidence_score(self):
        """When scores differ, score wins; bundle_id is the secondary key."""
        archive = _new_archive()
        archive.add_candidate(
            _make_bundle(bundle_id="alpha", source_round=0),
            evidence_score=0.3,
        )
        archive.add_candidate(
            _make_bundle(bundle_id="zebra", source_round=1),
            evidence_score=0.7,
        )
        entry = archive.select_one_bundle(current_round=2)
        assert entry is not None
        # zebra has the higher score -> zebra wins.
        assert entry.bundle.bundle_id == BundleId("zebra")

    def test_selection_is_reproducible_across_two_calls(self):
        archive_a = _new_archive()
        archive_b = _new_archive()
        for bid, sr, score in (
            ("bundle-1", 0, 0.7),
            ("bundle-2", 1, 0.6),
            ("bundle-3", 2, 0.9),
        ):
            archive_a.add_candidate(
                _make_bundle(bundle_id=bid, source_round=sr),
                evidence_score=score,
            )
            archive_b.add_candidate(
                _make_bundle(bundle_id=bid, source_round=sr),
                evidence_score=score,
            )
        entry_a = archive_a.select_one_bundle(current_round=3)
        entry_b = archive_b.select_one_bundle(current_round=3)
        assert entry_a is not None and entry_b is not None
        assert entry_a.bundle.bundle_id == entry_b.bundle.bundle_id
        # The audit_hash is deterministic across identical inputs.
        assert archive_a.audit_trail.audit_hash == archive_b.audit_trail.audit_hash


# ---------------------------------------------------------------------------
# 6. Archive only valid within single-sample/run/checkpoint/trace lineage
# ---------------------------------------------------------------------------


class TestLineageRejection:
    def test_cross_run_id_rejected(self):
        archive = _new_archive()
        bundle = _make_bundle(
            bundle_id="bundle-cross-run",
            source_round=0,
            run_id=RunId("other-run"),
        )
        with pytest.raises(CandidateArchiveLineageError):
            archive.add_candidate(bundle, evidence_score=0.5)

    def test_cross_sample_id_rejected(self):
        archive = _new_archive()
        bundle = _make_bundle(
            bundle_id="bundle-cross-sample",
            source_round=0,
            sample_id=SampleId("other-sample"),
        )
        with pytest.raises(CandidateArchiveLineageError):
            archive.add_candidate(bundle, evidence_score=0.5)

    def test_cross_trace_lineage_rejected(self):
        """An archive built with an empty trace_lineage is rejected at
        construction. The check ensures the archive cannot be repurposed
        across trace lineages.
        """
        with pytest.raises(CandidateArchiveLineageError):
            SameSampleArchive(
                quota=_default_quota(),
                run_id=_RUN_ID,
                sample_id=_SAMPLE_ID,
                trace_lineage=TraceDigest(""),
                checkpoint_id=_CHECKPOINT_ID,
            )

    def test_empty_checkpoint_id_rejected(self):
        with pytest.raises(CandidateArchiveLineageError):
            SameSampleArchive(
                quota=_default_quota(),
                run_id=_RUN_ID,
                sample_id=_SAMPLE_ID,
                trace_lineage=_trace_for("archive", 0),
                checkpoint_id="",
            )


# ---------------------------------------------------------------------------
# 7. Consecutive reuse cap and audit trail shape
# ---------------------------------------------------------------------------


class TestConsecutiveReuse:
    def test_consecutive_reuse_cap_excludes_last_selected(self):
        """If the most recently selected bundle would exceed the cap,
        the archive must skip it and pick the next eligible candidate.
        """
        archive = _new_archive(max_consecutive_reuse_rounds=1)
        archive.add_candidate(
            _make_bundle(bundle_id="alpha", source_round=0),
            evidence_score=0.5,
        )
        archive.add_candidate(
            _make_bundle(bundle_id="zebra", source_round=1),
            evidence_score=0.5,
        )
        # Round 0: "alpha" selected (bundle_id < "zebra").
        entry0 = archive.select_one_bundle(current_round=0)
        assert entry0 is not None
        assert entry0.bundle.bundle_id == BundleId("alpha")
        assert entry0.consecutive_reuse_count == 1
        # Round 1: "alpha" would exceed max_consecutive_reuse_rounds=1
        # (count + 1 = 2 > 1). The archive must pick "zebra".
        entry1 = archive.select_one_bundle(current_round=1)
        assert entry1 is not None
        assert entry1.bundle.bundle_id == BundleId("zebra")

    def test_audit_trail_carries_required_fields(self):
        archive = _new_archive()
        archive.add_candidate(
            _make_bundle(bundle_id="only", source_round=0),
            evidence_score=0.7,
        )
        archive.select_one_bundle(current_round=0)
        audit = archive.audit_trail
        assert isinstance(audit, ArchiveAuditTrail)
        assert audit.selected_bundle_id == BundleId("only")
        assert audit.rejected_bundle_ids == ()
        assert audit.archive_size == 1
        assert audit.consecutive_reuse_count == 1
        assert audit.max_consecutive_reuse_rounds == 3
        assert audit.current_round == 0
        assert audit.audit_hash != ArtifactHash("")


# ---------------------------------------------------------------------------
# 8. ArchiveEntry shape + immutability
# ---------------------------------------------------------------------------


class TestArchiveEntry:
    def test_entry_is_frozen(self):
        bundle = _make_bundle(bundle_id="x", source_round=0)
        entry = ArchiveEntry(
            bundle=bundle,
            evidence_score=FactorValue(0.5),
            source_round=0,
            is_selected=False,
            consecutive_reuse_count=0,
        )
        import dataclasses as _dc
        with pytest.raises(_dc.FrozenInstanceError):
            entry.is_selected = True  # type: ignore[misc]

    def test_with_reuse_count_validates_negative(self):
        bundle = _make_bundle(bundle_id="x", source_round=0)
        entry = ArchiveEntry(
            bundle=bundle,
            evidence_score=FactorValue(0.5),
            source_round=0,
            is_selected=False,
            consecutive_reuse_count=0,
        )
        with pytest.raises(CandidateArchiveValidationError):
            entry.with_reuse_count(-1)


# ---------------------------------------------------------------------------
# 9. ArchiveQuota and ArchiveAuditTrail immutability
# ---------------------------------------------------------------------------


class TestArchiveTypes:
    def test_quota_is_frozen(self):
        import dataclasses as _dc
        quota = _default_quota()
        with pytest.raises(_dc.FrozenInstanceError):
            quota.max_archive_size = 99  # type: ignore[misc]

    def test_audit_trail_is_frozen(self):
        import dataclasses as _dc
        audit = ArchiveAuditTrail(
            selected_bundle_id=BundleId("b"),
            rejected_bundle_ids=(),
            dedup_count=0,
            total_influence_kept=0.0,
            archive_size=1,
        )
        with pytest.raises(_dc.FrozenInstanceError):
            audit.selected_bundle_id = None  # type: ignore[misc]
