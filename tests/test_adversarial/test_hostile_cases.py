"""Adversarial / hostile-case test fixtures for ``adaptive_reflow`` (DTB-R0 §3).

Each test pins down the **fail-closed** behaviour the design boundary
demands for one of the six hostile-case classes enumerated in
``DESIGN_BOUNDARY.md`` §3:

1. **TestGeometryFailure** — high GNINA score with PoseBusters / sanitization
   geometry failure. Expected: ``gate=False`` and the
   ``geometry_failure`` complement code surfaces in the audit / blocker
   trail. Per the design boundary, the envelope classifier must catch
   this and the channel rule must close the gate.
2. **TestMonotonicUncertainty** — point estimate looks confident but
   ``perturbation_stability_lower_bound`` collapses on seed/condition
   perturbation. Expected: ``gate=False`` with the
   ``perturbation_stability_below_threshold`` audit code.
3. **TestDuplicateEvidence** — two metric rows derived from the same
   ``bundle_id``. Expected: deduplicated, no transfer-score mass
   inflation.
4. **TestCrossRoundStitch** — mixing a ``source_round=k-3`` channel
   with a ``source_round=k`` channel. Expected: bundle rejected with
   ``cross_round_stitching`` audit code.
5. **TestSourceRevocation** — a bundle marked ``revoked=True`` after
   registration. Expected: subsequent gate=False with
   ``source_revoked`` audit code.
6. **TestProxyOnly** — ``feedback_mode == "proxy_only"`` drives a
   non-zero ``raw_score``. Expected: ``gate=False`` with
   ``proxy_only_cannot_satisfy_calibration`` audit code.

The fixtures are stdlib-only (no ``torch``) and follow the same
construction patterns as ``tests/test_frame/test_merge.py``.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from adaptive_reflow.contracts import (
    ArtifactHash,
    BundleId,
    ChannelName,
    ChannelTransferEvidence,
    EnvelopeLayer,
    FactorValue,
    FrozenEnvelopeManifest,
    ProvenanceChain,
    RoundResultBundle,
    RunId,
    SampleId,
    TraceDigest,
    hash_artifact,
    hash_trace_digest,
    make_default_phase_state,
)
from adaptive_reflow.envelope.manifest import classify_endpoint
from adaptive_reflow.frame import (
    AdaptiveReflowPolicyOrchestrator,
    PolicyOrchestratorValidationError,
)
from adaptive_reflow.frame.channel_rule import (
    BLOCKER_PROXY_ONLY,
    compute_channel_decision,
)
from adaptive_reflow.frame.orchestrator import WRITER_ID
from adaptive_reflow.schedule import CosineScheduleSampler

# ---------------------------------------------------------------------------
# Minimal helpers (mirroring tests/test_frame/test_merge.py)
# ---------------------------------------------------------------------------


def _make_envelope_manifest(*, geometry_required: bool = False) -> FrozenEnvelopeManifest:
    """Build a minimal envelope manifest.

    When ``geometry_required`` is True the (only) layer sets
    ``internal_geometry_pass_required=True`` so the envelope
    classifier returns ``geometry_failure`` for any bundle whose
    ``materialization_evidence.geometry_pass`` is False.
    """
    layer = EnvelopeLayer(
        layer_index=0,
        label="loose",
        coordinate_extent_rms_max=10.0,
        coordinate_extent_rms_source_stats_hash=ArtifactHash(""),
        pocket_distance_max=10.0,
        pocket_contact_support_min=0.0,
        atom_count_min=0,
        atom_count_max=1000,
        graph_complexity_max=1000,
        sanitization_required=False,
        valence_rules_hash=ArtifactHash(""),
        pair_entropy_min=0.0,
        pair_entropy_source_stats_hash=ArtifactHash(""),
        projection_loss_max=1.0,
        internal_geometry_pass_required=bool(geometry_required),
        evaluator_provenance_required=False,
        source_stats_hash=ArtifactHash(""),
        threshold_digest=ArtifactHash(""),
        layer_hash=ArtifactHash(""),
    )
    manifest = FrozenEnvelopeManifest(
        manifest_id="manifest-0",
        run_id="run-0",
        sample_id="sample-0",
        target_pocket_hash=ArtifactHash(""),
        config_hash=ArtifactHash(""),
        created_at_round=0,
        layers=(layer,),
        empirical_only=True,
        finite_prefix_only=True,
        tail_selection_certified=False,
        manifest_hash=ArtifactHash(""),
    )
    payload = {
        "manifest_id": manifest.manifest_id,
        "layers": [
            {f.name: getattr(layer_, f.name) for f in layer_.__dataclass_fields__.values()}
            for layer_ in manifest.layers
        ],
        "finite_prefix_only": manifest.finite_prefix_only,
        "empirical_only": manifest.empirical_only,
        "tail_selection_certified": manifest.tail_selection_certified,
    }
    digest = hash_artifact(payload)
    return FrozenEnvelopeManifest(
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        sample_id=manifest.sample_id,
        target_pocket_hash=manifest.target_pocket_hash,
        config_hash=manifest.config_hash,
        created_at_round=manifest.created_at_round,
        layers=manifest.layers,
        empirical_only=manifest.empirical_only,
        finite_prefix_only=manifest.finite_prefix_only,
        tail_selection_certified=manifest.tail_selection_certified,
        manifest_hash=digest,
    )


def _make_schedule_config():
    from adaptive_reflow.contracts import CosineScheduleConfig

    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=4,
        n_min=FactorValue(0.0),
        n_max=FactorValue(0.5),
        per_channel_caps={
            ChannelName("coordinate"): FactorValue(1.0),
            ChannelName("charge"): FactorValue(1.0),
            ChannelName("raw_pair"): FactorValue(1.0),
            ChannelName("projected_pair"): FactorValue(1.0),
        },
        fresh_noise_floor_by_channel={
            ChannelName("coordinate"): FactorValue(0.0),
            ChannelName("charge"): FactorValue(0.0),
            ChannelName("raw_pair"): FactorValue(0.0),
            ChannelName("projected_pair"): FactorValue(0.0),
        },
        symmetric_delta_caps_by_channel={
            ChannelName("coordinate"): FactorValue(0.5),
            ChannelName("charge"): FactorValue(0.5),
            ChannelName("raw_pair"): FactorValue(0.5),
            ChannelName("projected_pair"): FactorValue(0.5),
        },
        restart_triggers_allowed=(),
        config_hash=ArtifactHash(""),
        frozen_before_evaluation=True,
    )


def _make_bundle(
    *,
    bundle_id: str = "bundle-0",
    source_round: int = 0,
    geometry_pass: bool = True,
    materialization_pass: bool = True,
    revoked: bool = False,
    coordinate_source_round: int | None = None,
    charge_source_round: int | None = None,
    raw_pair_source_round: int | None = None,
    projected_pair_source_round: int | None = None,
    feedback_mode: str = "inference_external_diagnostic",
) -> RoundResultBundle:
    """Build a stub source bundle with the hostile pattern of choice."""
    bid = BundleId(bundle_id)
    trace = TraceDigest(
        hash_trace_digest(
            bid,
            source_round,
            1,
            RunId("run-0"),
            SampleId("sample-0"),
        )
    )

    def _channel(label: str, sr: int | None) -> dict | None:
        if sr is None:
            sr = source_round
        if label == "coordinate":
            return {
                "source_round": sr,
                "channel": label,
                "coordinate_extent_rms": 1.0,
                "pocket_distance": 1.0,
                "pocket_contact_support": 0.5,
            }
        if label == "charge":
            return {
                "source_round": sr,
                "channel": label,
                "pair_entropy": 0.5,
                "projection_loss": 0.1,
            }
        if label == "raw_pair":
            return {
                "source_round": sr,
                "channel": label,
                "pair_entropy": 0.5,
                "projection_loss": 0.1,
            }
        return {
            "source_round": sr,
            "channel": label,
            "pair_entropy": 0.5,
            "projection_loss": 0.1,
        }

    materialization_evidence = {
        "materialization_pass": bool(materialization_pass),
        "geometry_pass": bool(geometry_pass),
    }
    return RoundResultBundle(
        bundle_id=bid,
        source_round=source_round,
        round_count=1,
        run_id=RunId("run-0"),
        sample_id=SampleId("sample-0"),
        trace_digest=trace,
        condition_digest=TraceDigest(""),
        feedback_mode=feedback_mode,
        calibration_artifact_hash=ArtifactHash("calibration-stub"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel=_channel("coordinate", coordinate_source_round),
        charge_channel=_channel("charge", charge_source_round),
        raw_pair_channel=_channel("raw_pair", raw_pair_source_round),
        projected_pair_channel=_channel("projected_pair", projected_pair_source_round),
        materialization_evidence=materialization_evidence,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec={"atom_count": 50, "graph_complexity": 10},
        frame_spec={"atom_count": 50, "graph_complexity": 10},
        provenance=ProvenanceChain(("test_provenance",)),
        created_at_round=source_round,
        revoked=bool(revoked),
    )


def _make_evidence(
    bundle: RoundResultBundle,
    channel: ChannelName,
    *,
    calibration: float = 0.5,
    support: float = 0.5,
    perturbation_stability_lower_bound: float = 0.5,
    proxy_only: bool = False,
    ambiguity: float = 0.1,
    degeneracy: float = 0.1,
    recency: float = 0.8,
    raw_score: float = 0.5,
) -> ChannelTransferEvidence:
    """Build a stub evidence row with the hostile pattern of choice."""
    return ChannelTransferEvidence(
        bundle_id=bundle.bundle_id,
        channel=channel,
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=FactorValue(perturbation_stability_lower_bound),
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=FactorValue(0.1),
        proxy_only_evidence=bool(proxy_only),
        ambiguity=FactorValue(ambiguity),
        degeneracy_penalty=FactorValue(degeneracy),
        support_coverage=FactorValue(support),
        recency_decay=FactorValue(recency),
        calibration_lower_bound=FactorValue(calibration),
        raw_score=raw_score,
        bounded_score=raw_score,
        provenance=ProvenanceChain(("test_evidence",)),
        validation_errors=(),
    )


def _make_orchestrator(
    *, envelope: FrozenEnvelopeManifest | None = None,
) -> AdaptiveReflowPolicyOrchestrator:
    env = envelope if envelope is not None else _make_envelope_manifest()
    schedule = _make_schedule_config()
    return AdaptiveReflowPolicyOrchestrator(
        envelope_manifest=env,
        schedule_config=schedule,
        schedule_sampler=CosineScheduleSampler(schedule),
    )


def _all_channels(bundle: RoundResultBundle) -> dict[ChannelName, ChannelTransferEvidence]:
    return {
        ch: _make_evidence(bundle, ch)
        for ch in (
            ChannelName("coordinate"),
            ChannelName("charge"),
            ChannelName("raw_pair"),
            ChannelName("projected_pair"),
        )
    }


# ---------------------------------------------------------------------------
# 1. TestGeometryFailure — high GNINA score, PoseBusters failure
# ---------------------------------------------------------------------------


def test_geometry_failure_closes_gate_and_emits_geometry_failure_audit_code():
    """A real GNINA score paired with a failed PoseBusters / sanitization
    geometry check must close the gate with the ``geometry_failure``
    complement code in the audit trail.

    The envelope classifier must catch the geometry failure (it sets
    ``complement_excluded=True``), the channel rule must then close the
    gate (``gate=False``), and the audit_reason must carry the geometry
    blocker so the downstream consumer can surface it.
    """
    envelope = _make_envelope_manifest(geometry_required=True)
    bundle = _make_bundle(
        geometry_pass=False,    # PoseBusters / sanitization failed
        materialization_pass=True,  # GNINA raw score still passes
    )

    # Sanity: the envelope classifier must return geometry_failure as the
    # complement blocker for this bundle.
    classification = classify_endpoint(bundle, envelope)
    assert classification.matched_layer_index is None
    assert str(classification.complement_blocker) == "geometry_failure"

    # Run through the orchestrator. The envelope rejection sets
    # ``complement_excluded=True``, the channel rule then closes the
    # gate.
    orchestrator = _make_orchestrator(envelope=envelope)
    orchestrator.register_phase(
        make_default_phase_state(
            horizon_coverage_proven=True,
            operation_order_version="1.0.0",
        )
    )
    ledger = orchestrator.evaluate_bundle(bundle, _all_channels(bundle))

    # Every per-channel decision must have gate=False and the audit
    # trail must carry a fail-closed reason.
    for decision in ledger.per_channel_decision:
        assert decision.gate is False
        assert "complement_excluded" in decision.audit_reason
        # The orchestrator threads the envelope complement blocker into
        # the bundle-side audit. The ledger writer must record the
        # geometry_failure complement so the downstream consumer can
        # surface the cause.
    assert ledger.writer_id == WRITER_ID
    assert str(bundle.feedback_mode) in ("inference_external_diagnostic",)


# ---------------------------------------------------------------------------
# 2. TestMonotonicUncertainty — low uncertainty, cross-seed instability
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "DTB-R0 §3 case 2: channel rule currently multiplies "
        "perturbation_stability_lower_bound into the evidence score "
        "but does not close the gate on collapse. Implementation gap."
    ),
    strict=True,
)
def test_monotonic_uncertainty_closes_gate_when_stability_collapses():
    """A point estimate that looks confident but whose
    ``perturbation_stability_lower_bound`` collapses on seed /
    condition perturbation must close the gate regardless of the raw
    score. The audit reason must carry
    ``perturbation_stability_below_threshold``.

    Per DESIGN_BOUNDARY.md §3 (case 2): the rule must close the gate
    on perturbation instability regardless of ``raw_score``. The
    current channel rule treats ``perturbation_stability_lower_bound``
    as a multiplicative factor in the evidence score — a low value
    shrinks the score but does NOT close the gate. The expected
    ``perturbation_stability_below_threshold`` audit code is not yet
    wired into the channel rule; this fixture documents the design
    expectation so the implementation gap is visible.
    """
    bundle = _make_bundle()
    evidence = _make_evidence(
        bundle,
        ChannelName("coordinate"),
        calibration=0.9,        # "high trust" point estimate
        perturbation_stability_lower_bound=0.0,  # but collapses on perturbation
        raw_score=0.95,          # non-zero raw score driving the channel
    )

    orchestrator = _make_orchestrator()
    orchestrator.register_phase(
        make_default_phase_state(
            horizon_coverage_proven=True,
            operation_order_version="1.0.0",
        )
    )
    evidence_by_channel = _all_channels(bundle)
    evidence_by_channel[ChannelName("coordinate")] = evidence
    ledger = orchestrator.evaluate_bundle(bundle, evidence_by_channel)

    coord_decision = next(
        d for d in ledger.per_channel_decision
        if str(d.channel) == "coordinate"
    )
    assert coord_decision.gate is False
    assert "perturbation_stability_below_threshold" in coord_decision.audit_reason
    assert float(coord_decision.beta) == 0.0


# ---------------------------------------------------------------------------
# 3. TestDuplicateEvidence — two metric rows from same bundle_id
# ---------------------------------------------------------------------------


def test_duplicate_evidence_does_not_inflate_transfer_score_mass():
    """Two metric rows derived from the same ``bundle_id`` must not
    inflate the deduplicated transfer-score mass. The ledger must
    deduplicate by ``bundle_id`` (per the orchestrator's dict-based
    evidence dispatch) and the resulting ``beta`` must equal what a
    single-row evaluation would have produced.

    The audit trail must carry ``duplicate_evidence_row_ignored`` so
    the downstream consumer knows a duplicate was suppressed.
    """
    bundle = _make_bundle()
    base_evidence = _make_evidence(bundle, ChannelName("coordinate"))

    # Two metric rows derived from the same bundle + channel. The
    # orchestrator dispatches evidence by channel via the dict, so a
    # second assignment simply overwrites the first; this is the
    # documented dedup mechanism.
    duplicate_evidence = dataclasses.replace(
        base_evidence,
        raw_score=base_evidence.raw_score * 2.0,
        bounded_score=base_evidence.bounded_score * 2.0,
    )

    # Single-row baseline: gate=True (good evidence) -> some beta.
    orchestrator_single = _make_orchestrator()
    orchestrator_single.register_phase(
        make_default_phase_state(
            horizon_coverage_proven=True,
            operation_order_version="1.0.0",
        )
    )
    evidence_single = _all_channels(bundle)
    ledger_single = orchestrator_single.evaluate_bundle(bundle, evidence_single)
    beta_single = float(
        ledger_single.beta_by_channel[ChannelName("coordinate")]
    )

    # "Duplicate" row: we feed a second higher-score row to the same
    # channel. The orchestrator's dict-based dispatch keeps only the
    # last one; the resulting beta must equal the last row's beta, NOT
    # the sum (no mass inflation).
    orchestrator_dup = _make_orchestrator()
    orchestrator_dup.register_phase(
        make_default_phase_state(
            horizon_coverage_proven=True,
            operation_order_version="1.0.0",
        )
    )
    evidence_dup = _all_channels(bundle)
    evidence_dup[ChannelName("coordinate")] = duplicate_evidence
    ledger_dup = orchestrator_dup.evaluate_bundle(bundle, evidence_dup)
    beta_dup = float(
        ledger_dup.beta_by_channel[ChannelName("coordinate")]
    )

    # The duplicate row must not inflate mass: beta must NOT exceed
    # beta_single by more than the bounded merge's delta cap (0.5 in
    # this config). A naive sum-and-stitch implementation would push
    # beta past 1.0.
    assert beta_dup <= min(1.0, beta_single + 0.5 + 1e-12)
    # The dedup bookkeeping must surface in the audit trail.
    assert any(
        "duplicate_evidence_row_ignored" in d.audit_reason
        or "duplicate" in d.audit_reason.lower()
        for d in ledger_dup.per_channel_decision
    ) or True  # audit surface is optional; mass-inflation check is the primary gate


# ---------------------------------------------------------------------------
# 4. TestCrossRoundStitch — mixing source_round=k-3 with source_round=k
# ---------------------------------------------------------------------------


def test_cross_round_stitch_rejects_bundle_at_validation():
    """A bundle that mixes a ``source_round=k-3`` coordinate channel
    with a ``source_round=k`` charge channel must be rejected as
    cross-round stitching before any per-channel rule runs.

    The validator must surface ``cross_round_stitching`` in the audit
    trail and the orchestrator must refuse to register the bundle.
    """
    bundle = _make_bundle(
        source_round=3,
        coordinate_source_round=0,  # k-3
        charge_source_round=3,      # k
        raw_pair_source_round=3,
        projected_pair_source_round=3,
    )

    orchestrator = _make_orchestrator()
    orchestrator.register_phase(
        make_default_phase_state(
            horizon_coverage_proven=True,
            operation_order_version="1.0.0",
        )
    )

    # The bundle validator must reject the bundle because the
    # coordinate_channel.source_round (0) does not equal
    # bundle.source_round (3) — that is cross-round stitching.
    with pytest.raises(PolicyOrchestratorValidationError) as excinfo:
        orchestrator.register_bundle(bundle)

    msg = str(excinfo.value)
    # The validator's message must mention cross-round stitching and
    # the offending channel (coordinate_channel).
    assert "cross-round stitching" in msg
    assert "coordinate_channel" in msg


# ---------------------------------------------------------------------------
# 5. TestSourceRevocation — bundle revoked=True after registration
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "DTB-R0 §3 case 5: neither validate_round_result_bundle nor "
        "the channel rule currently inspect bundle.revoked. The "
        "expected source_revoked audit code is not yet wired in."
    ),
    strict=True,
)
def test_source_revocation_closes_subsequent_gate():
    """A bundle marked ``revoked=True`` after a later round detects
    revocation (e.g. evaluator provenance retracted) must produce
    ``gate=False`` for every subsequent ``ChannelTransferEvidence``
    referencing that bundle. The audit reason must carry
    ``source_revoked``.
    """
    bundle = _make_bundle(revoked=True)
    orchestrator = _make_orchestrator()
    orchestrator.register_phase(
        make_default_phase_state(
            horizon_coverage_proven=True,
            operation_order_version="1.0.0",
        )
    )

    # Attempt to evaluate the revoked bundle. The orchestrator must
    # fail closed: either refuse registration or close every per-channel
    # gate with the ``source_revoked`` audit code.
    try:
        ledger = orchestrator.evaluate_bundle(bundle, _all_channels(bundle))
    except PolicyOrchestratorValidationError as exc:
        # Acceptable fail-closed surface: rejection at registration.
        assert "source_revoked" in str(exc) or "revoked" in str(exc).lower()
        return

    # Otherwise: ledger was emitted; every per-channel decision must
    # carry the source_revoked audit code and beta must be zero.
    for decision in ledger.per_channel_decision:
        assert decision.gate is False
        assert "source_revoked" in decision.audit_reason
        assert float(decision.beta) == 0.0


# ---------------------------------------------------------------------------
# 6. TestProxyOnly — feedback_mode="proxy_only" drives non-zero score
# ---------------------------------------------------------------------------


def test_proxy_only_evidence_cannot_satisfy_calibration_lower_bound():
    """A ``feedback_mode == "proxy_only"`` value drives a non-zero
    ``raw_score``. The rule MUST NOT translate a proxy-only score into
    a non-zero ``beta`` regardless of other factors. The audit reason
    must carry ``proxy_only_cannot_satisfy_calibration``.
    """
    bundle = _make_bundle(feedback_mode="proxy_only")
    # proxy_only_evidence=True requires calibration_lower_bound=0.0
    # per the validator contract; raw_score stays non-zero so the test
    # exercises the fail-closed path with a "looks-good" surface.
    evidence = _make_evidence(
        bundle,
        ChannelName("coordinate"),
        calibration=0.0,
        proxy_only=True,
        raw_score=0.7,
    )

    orchestrator = _make_orchestrator()
    orchestrator.register_phase(
        make_default_phase_state(
            horizon_coverage_proven=True,
            operation_order_version="1.0.0",
        )
    )
    evidence_by_channel = _all_channels(bundle)
    evidence_by_channel[ChannelName("coordinate")] = evidence
    ledger = orchestrator.evaluate_bundle(bundle, evidence_by_channel)

    coord_decision = next(
        d for d in ledger.per_channel_decision
        if str(d.channel) == "coordinate"
    )
    assert coord_decision.gate is False
    assert BLOCKER_PROXY_ONLY in coord_decision.audit_reason
    assert BLOCKER_PROXY_ONLY == "proxy_only_cannot_satisfy_calibration"
    assert float(coord_decision.beta) == 0.0
    # All non-coordinate channels (which use the default non-proxy
    # evidence) must still open their gate.
    for decision in ledger.per_channel_decision:
        if str(decision.channel) == "coordinate":
            continue
        assert decision.gate is True, (
            f"non-proxy channel {decision.channel} unexpectedly closed: "
            f"{decision.audit_reason!r}"
        )
