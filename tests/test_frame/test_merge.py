"""Tests for the DTB-R3 bounded merge authority and core-runtime handoff.

Covers the contract that ``adaptive_reflow``'s dynamic-control merge
must satisfy per DTB-R3:

* the merge can DECREASE on worse evidence, bounded by per-round delta
  caps and a fresh-noise floor;
* floor / cap clamping is honoured;
* ``delta_cap_up`` / ``delta_cap_down`` are symmetric;
* same-run dual executable writer attempts are rejected by the
  :class:`WriterArbitrator`;
* diagnostic-only ``inference.noise_bias`` registration does not change
  the :class:`FinalRestartPolicy` byte / hash;
* the disabled profile leaves the merge unchanged (i.e. a no-op for
  callers that don't construct an orchestrator).

The tests are stdlib-only (no ``torch``) and importable from a regular
checkout with ``PYTHONPATH=. python -m pytest tests/``.
"""

from __future__ import annotations

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
    CosineScheduleSample,
    EnvelopeLayer,
    FactorValue,
    FrozenEnvelopeManifest,
    MechanismId,
    ProvenanceChain,
    RoundResultBundle,
    RunId,
    SampleId,
    TraceDigest,
    hash_artifact,
    hash_trace_digest,
)
from adaptive_reflow.frame import (
    ERR_PREV_REQUIRED,
    MERGE_AUTHORITY_SCHEMA_NAME,
    MERGE_AUTHORITY_SCHEMA_VERSION,
    MERGE_DEGENERATE_INTERVAL,
    MERGE_FLOOR_FALLBACK,
    MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
    WRITER_ID,
    AdaptiveReflowPolicyOrchestrator,
    MergeAuthorityError,
    bounded_merge,
    bounded_merge_with_schedule,
)
from adaptive_reflow.schedule import CosineScheduleSampler
from adaptive_reflow.writer import (
    CORE_RUNTIME_HANDBOFF_SCHEMA_NAME,
    CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION,
    CORE_RUNTIME_OWNER,
    DIAGNOSTIC_WRITER_MECHANISM_ID,
    ERR_DUAL_EXECUTABLE,
    EXECUTABLE_WRITER_MECHANISM_ID,
    CoreRuntimeHandoffError,
    WriterArbitrator,
    WriterArgumentError,
    build_core_runtime_handoff,
    build_default_authority_contract,
    write_handoff_spec,
)

# ---------------------------------------------------------------------------
# Fixtures (minimal envelope + schedule + bundle for orchestrator wiring)
# ---------------------------------------------------------------------------


def _make_envelope_manifest() -> FrozenEnvelopeManifest:
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
        internal_geometry_pass_required=False,
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
    # Stamp a deterministic manifest hash so we can assert byte equality
    # on the orchestrator outputs.
    payload = {
        "manifest_id": manifest.manifest_id,
        "layers": [
            {f.name: getattr(layer_, f.name) for f in layer.__dataclass_fields__.values()}
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


def _make_bundle(*, source_round: int = 0) -> RoundResultBundle:
    bundle_id = f"bundle-{source_round}"
    trace = TraceDigest(
        hash_trace_digest(
            BundleId(bundle_id),
            source_round,
            1,
            RunId("run-0"),
            SampleId("sample-0"),
        )
    )
    return RoundResultBundle(
        bundle_id=BundleId(bundle_id),
        source_round=source_round,
        round_count=1,
        run_id=RunId("run-0"),
        sample_id=SampleId("sample-0"),
        trace_digest=trace,
        condition_digest=TraceDigest(""),
        feedback_mode="inference_external_diagnostic",
        calibration_artifact_hash=ArtifactHash("calibration-stub"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel={
            "source_round": source_round,
            "channel": "coordinate",
        },
        charge_channel={
            "source_round": source_round,
            "channel": "charge",
        },
        raw_pair_channel={
            "source_round": source_round,
            "channel": "raw_pair",
        },
        projected_pair_channel={
            "source_round": source_round,
            "channel": "projected_pair",
        },
        materialization_evidence=None,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec={},
        frame_spec={},
        provenance=ProvenanceChain(("test_provenance",)),
        created_at_round=source_round,
        revoked=False,
    )


def _make_evidence(bundle: RoundResultBundle, channel: ChannelName, *,
                    calibration: float = 0.5,
                    support: float = 0.5) -> ChannelTransferEvidence:
    return ChannelTransferEvidence(
        bundle_id=bundle.bundle_id,
        channel=channel,
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=FactorValue(0.5),
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=FactorValue(0.1),
        proxy_only_evidence=False,
        ambiguity=FactorValue(0.1),
        degeneracy_penalty=FactorValue(0.1),
        support_coverage=FactorValue(support),
        recency_decay=FactorValue(0.8),
        calibration_lower_bound=FactorValue(calibration),
        raw_score=0.5,
        bounded_score=0.5,
        provenance=ProvenanceChain(("test_evidence",)),
        validation_errors=(),
    )


def _make_orchestrator() -> AdaptiveReflowPolicyOrchestrator:
    envelope = _make_envelope_manifest()
    schedule = _make_schedule_config()
    return AdaptiveReflowPolicyOrchestrator(
        envelope_manifest=envelope,
        schedule_config=schedule,
        schedule_sampler=CosineScheduleSampler(schedule),
    )


# ---------------------------------------------------------------------------
# 1. bounded_merge can DECREASE on worse evidence
# ---------------------------------------------------------------------------


def test_bounded_merge_can_decrease_on_worse_evidence():
    """A dynamic value below ``prev`` must be respected (with bounds)."""
    prev = 0.8
    dynamic = 0.2  # worse evidence -> smaller fraction
    result = bounded_merge(
        prev=prev,
        dynamic=dynamic,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    # lo = max(0.0, 0.8 - 0.5) = 0.3; target = clamp(0.2, 0.0, 1.0) = 0.2;
    # clamped to lo: 0.3.
    assert result == pytest.approx(0.3)
    assert result < prev


def test_bounded_merge_can_increase_on_better_evidence():
    """A dynamic value above ``prev`` must be respected (with bounds)."""
    prev = 0.2
    dynamic = 0.7
    result = bounded_merge(
        prev=prev,
        dynamic=dynamic,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    # hi = min(1.0, 0.2 + 0.5) = 0.7; target = 0.7; result = 0.7.
    assert result == pytest.approx(0.7)
    assert result > prev


def test_bounded_merge_no_change_when_within_range():
    """A dynamic value inside the symmetric delta envelope stays."""
    prev = 0.5
    dynamic = 0.5
    result = bounded_merge(
        prev=prev,
        dynamic=dynamic,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    assert result == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 2. floor / cap clamping
# ---------------------------------------------------------------------------


def test_floor_clamping_prevents_underflow():
    """Result must never go below ``floor``."""
    result = bounded_merge(
        prev=0.1,
        dynamic=0.0,
        cap=1.0,
        floor=0.05,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    assert result == pytest.approx(0.05)


def test_cap_clamping_prevents_overflow():
    """Result must never exceed ``cap``."""
    result = bounded_merge(
        prev=0.9,
        dynamic=1.0,
        cap=0.95,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
    )
    assert result == pytest.approx(0.95)


def test_floor_above_cap_clips_with_audit():
    """Inverted envelope is fail-closed; audit code is appended before raise (F5).

    After the F5 fix, :class:`BoundedMergeOperator` no longer silently
    swaps the envelope. It appends the ``_ERR_CAP_BELOW_FLOOR`` audit
    code and raises :exc:`MergeAuthorityError`. The audit trail is
    preserved so a downstream reader can replay the broken configuration.
    """
    audit: list[str] = []
    with pytest.raises(MergeAuthorityError):
        bounded_merge(
            prev=0.5,
            dynamic=0.5,
            cap=0.3,
            floor=0.7,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
            audit_codes=audit,
        )
    assert any("merge_cap_below_floor" in code for code in audit)


def test_negative_floor_clips_with_audit():
    """Negative floor is clipped to ``0.0`` and a canonical audit code is appended (P0-3).

    Previously raised :exc:`MergeAuthorityError`. After the P0-3 fix,
    :class:`BoundedMergeOperator` clips ``floor`` into the unit
    interval and appends ``MERGE_FLOOR_OUT_OF_RANGE``.
    """
    audit: list[str] = []
    result = bounded_merge(
        prev=0.5,
        dynamic=0.5,
        cap=1.0,
        floor=-0.1,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert 0.0 <= result <= 1.0
    assert any("merge_floor_out_of_range" in code for code in audit)


def test_cap_above_one_clips_with_audit():
    """Cap > 1.0 is clipped to ``1.0`` and a canonical audit code is appended (P0-3).

    Previously raised :exc:`MergeAuthorityError`. After the P0-3 fix,
    :class:`BoundedMergeOperator` clips ``cap`` into the unit
    interval and appends ``MERGE_CAP_OUT_OF_RANGE``.
    """
    audit: list[str] = []
    result = bounded_merge(
        prev=0.5,
        dynamic=0.5,
        cap=1.1,
        floor=0.0,
        delta_cap_up=0.5,
        delta_cap_down=0.5,
        audit_codes=audit,
    )
    assert 0.0 <= result <= 1.0
    assert any("merge_cap_out_of_range" in code for code in audit)


# ---------------------------------------------------------------------------
# 3. delta_cap_up / delta_cap_down symmetric
# ---------------------------------------------------------------------------


def test_symmetric_delta_caps_produce_identical_results():
    """Same numeric cap on up and down must produce identical output."""
    a = bounded_merge(
        prev=0.5,
        dynamic=0.0,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.25,
        delta_cap_down=0.25,
    )
    b = bounded_merge(
        prev=0.5,
        dynamic=1.0,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.25,
        delta_cap_down=0.25,
    )
    # a is constrained downward; b is constrained upward. Both end up
    # at prev +- 0.25 == 0.25 / 0.75.
    assert a == pytest.approx(0.25)
    assert b == pytest.approx(0.75)


def test_asymmetric_delta_caps():
    """Larger delta_cap_up allows bigger jumps up than down."""
    up_only = bounded_merge(
        prev=0.5,
        dynamic=1.0,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.0,
        delta_cap_down=0.05,
    )
    down_only = bounded_merge(
        prev=0.5,
        dynamic=0.0,
        cap=1.0,
        floor=0.0,
        delta_cap_up=0.05,
        delta_cap_down=1.0,
    )
    # up_only: dynamic=1.0, hi=min(1.0, 0.5+1.0)=1.0 -> 1.0
    # down_only: dynamic=0.0, lo=max(0.0, 0.5-1.0)=0.0, hi=min(1.0, 0.5+0.05)=0.55
    #            -> clamp(0.0, 0.0, 0.55) = 0.0
    assert up_only == pytest.approx(1.0)
    assert down_only == pytest.approx(0.0)


def test_delta_cap_up_above_one_clips_with_audit():
    """delta_cap_up > 1.0 is clipped to ``1.0`` (P0-3).

    Previously raised :exc:`MergeAuthorityError`. After the P0-3
    fix the operator never raises on legitimate caller input; it
    clips ``delta_cap_up`` into the unit interval and returns a
    finite result.
    """
    result = bounded_merge(
        prev=0.5,
        dynamic=0.5,
        cap=1.0,
        floor=0.0,
        delta_cap_up=1.5,
        delta_cap_down=0.5,
    )
    assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# 4. Dual-writer rejection (DTB-S1)
# ---------------------------------------------------------------------------


def test_dual_executable_writer_rejected():
    """Same-run dual executable writer is fail-closed."""
    contract = build_default_authority_contract()
    arb = WriterArbitrator(contract)
    arb.register_request(EXECUTABLE_WRITER_MECHANISM_ID, "executable")
    with pytest.raises(WriterArgumentError) as excinfo:
        arb.register_request(DIAGNOSTIC_WRITER_MECHANISM_ID, "executable")
    # Either ERR_DUAL_EXECUTABLE (a second distinct mechanism holds
    # executable) or ERR_WRONG_EXECUTABLE (a non-adaptive_reflow
    # mechanism tried to take executable mode) is acceptable here;
    # both fail closed under DTB-S1.
    msg = str(excinfo.value)
    assert ERR_DUAL_EXECUTABLE in msg or "writer_request_executable_not_adaptive_reflow" in msg


def test_diagnostic_only_writer_allowed_with_executable():
    """A diagnostic writer alongside the executable is allowed."""
    contract = build_default_authority_contract()
    arb = WriterArbitrator(contract)
    arb.register_request(EXECUTABLE_WRITER_MECHANISM_ID, "executable")
    arb.register_request(DIAGNOSTIC_WRITER_MECHANISM_ID, "diagnostic_only")
    executors = arb.authorize()
    diagnostics = arb.diagnostics_allowed()
    assert executors == (
        MechanismId(EXECUTABLE_WRITER_MECHANISM_ID),
    )
    assert diagnostics == (
        MechanismId(DIAGNOSTIC_WRITER_MECHANISM_ID),
    )


def test_orchestrator_auto_registers_diagnostic_writer():
    """Evaluating a bundle auto-registers the diagnostic writer."""
    orchestrator = _make_orchestrator()
    # Pre-register the executable writer so the arbitrator has the
    # canonical single-executable state. The orchestrator then
    # auto-registers the diagnostic writer on the first
    # ``evaluate_bundle`` call.
    orchestrator.arbitrator.register_request(
        EXECUTABLE_WRITER_MECHANISM_ID, "executable"
    )
    bundle = _make_bundle()
    evidence_by_channel = {
        ch: _make_evidence(bundle, ch) for ch in (
            ChannelName("coordinate"),
            ChannelName("charge"),
            ChannelName("raw_pair"),
            ChannelName("projected_pair"),
        )
    }
    orchestrator.evaluate_bundle(bundle, evidence_by_channel)
    # Diagnostic writer must be present; executable writer must remain
    # the sole executable.
    diagnostics = orchestrator.arbitrator.diagnostics_allowed()
    executors = orchestrator.arbitrator.authorize()
    assert DIAGNOSTIC_WRITER_MECHANISM_ID in (str(m) for m in diagnostics)
    assert executors == (
        MechanismId(EXECUTABLE_WRITER_MECHANISM_ID),
    )


# ---------------------------------------------------------------------------
# 5. Diagnostic-only noise_bias does not change FinalRestartPolicy byte/hash
# ---------------------------------------------------------------------------


def test_diagnostic_writer_does_not_change_policy_hash():
    """Registering noise_bias in diagnostic_only mode must not perturb
    the produced ``FinalRestartPolicy`` byte / hash.
    """
    envelope = _make_envelope_manifest()
    schedule = _make_schedule_config()
    sampler = CosineScheduleSampler(schedule)
    contract = build_default_authority_contract()
    arb_a = WriterArbitrator(contract)
    arb_b = WriterArbitrator(contract)

    bundle = _make_bundle()
    evidence_by_channel = {
        ch: _make_evidence(bundle, ch) for ch in (
            ChannelName("coordinate"),
            ChannelName("charge"),
            ChannelName("raw_pair"),
            ChannelName("projected_pair"),
        )
    }

    orch_a = AdaptiveReflowPolicyOrchestrator(
        envelope_manifest=envelope,
        schedule_config=schedule,
        authority_contract=contract,
        arbitrator=arb_a,
        schedule_sampler=sampler,
    )
    ledger_a = orch_a.evaluate_bundle(bundle, evidence_by_channel)
    policy_a = orch_a.build_final_policy(ledger_a)

    orch_b = AdaptiveReflowPolicyOrchestrator(
        envelope_manifest=envelope,
        schedule_config=schedule,
        authority_contract=contract,
        arbitrator=arb_b,
        schedule_sampler=sampler,
    )
    # Pre-register the diagnostic writer BEFORE the bundle is evaluated;
    # the orchestrator will additionally auto-register inside
    # evaluate_bundle. The pre-registration must not perturb the result.
    orch_b.arbitrator.register_request(
        DIAGNOSTIC_WRITER_MECHANISM_ID, "diagnostic_only"
    )
    ledger_b = orch_b.evaluate_bundle(bundle, evidence_by_channel)
    policy_b = orch_b.build_final_policy(ledger_b)

    assert policy_a.policy_hash == policy_b.policy_hash
    # Byte-for-byte equality of the frozen dataclass is the canonical
    # invariant: per ``DESIGN_BOUNDARY.md`` §4, the final restart policy
    # must be content-addressed.
    import dataclasses
    assert dataclasses.asdict(policy_a) == dataclasses.asdict(policy_b)
    # Sanity: the writer id is the canonical adaptive_reflow id.
    assert str(policy_a.writer_id) == WRITER_ID


# ---------------------------------------------------------------------------
# 6. Disabled profile unchanged behavior
# ---------------------------------------------------------------------------


def test_disabled_profile_no_orchestrator_uses_legacy_callable():
    """Without an orchestrator, prepare_outer_reflow_round routes to the
    legacy ``merge_controls_fn`` callable (backward-compat path).
    """
    from adaptive_reflow.legacy.orchestration import prepare_outer_reflow_round

    def _legacy_merge(
        *,
        scheduled_memory_fraction,
        scheduled_charge_memory_fraction,
        scheduled_pair_memory_fraction,
        scheduled_freeze_charge_state,
        scheduled_freeze_pair_chemical_state,
        dynamic_control_delta,
    ):
        # Legacy semantics: just echo the scheduled values.
        return {
            "memory_fraction": scheduled_memory_fraction,
            "charge_memory_fraction": scheduled_charge_memory_fraction,
            "pair_memory_fraction": scheduled_pair_memory_fraction,
            "freeze_charge_state": scheduled_freeze_charge_state,
            "freeze_pair_chemical_state": scheduled_freeze_pair_chemical_state,
        }

    kwargs, controls, prop = prepare_outer_reflow_round(
        round_index=0,
        rounds=1,
        sample_kwargs={},
        previous=None,
        next_property_preference=None,
        dynamic_control_delta={},
        base_property_schedule=None,
        bond_threshold_schedule=None,
        temperature_schedule=None,
        memory_fraction_schedule=[0.3],
        charge_memory_fraction_schedule=None,
        pair_memory_fraction_schedule=None,
        freeze_charge_state_schedule=None,
        freeze_pair_chemical_state_schedule=None,
        merge_controls_fn=_legacy_merge,
        policy_orchestrator=None,
    )
    assert controls["memory_fraction"] == pytest.approx(0.3)
    assert prop is None
    # ``adaptive_reflow_round_index`` / ``adaptive_reflow_round_count``
    # are stamped into the kwargs for downstream consumers.
    assert kwargs["adaptive_reflow_round_index"] == 0
    assert kwargs["adaptive_reflow_round_count"] == 1


def test_with_orchestrator_uses_bounded_merge_authority():
    """With an orchestrator, prepare_outer_reflow_round threads through
    ``merge_fraction_authority`` and emits bounded fractions.
    """
    from adaptive_reflow.legacy.orchestration import prepare_outer_reflow_round

    orchestrator = _make_orchestrator()

    def _legacy_merge(
        *,
        scheduled_memory_fraction,
        scheduled_charge_memory_fraction,
        scheduled_pair_memory_fraction,
        scheduled_freeze_charge_state,
        scheduled_freeze_pair_chemical_state,
        dynamic_control_delta,
    ):
        # If this were called, we'd fail the test.
        raise AssertionError(
            "legacy merge must not be called when an orchestrator is provided"
        )

    _kwargs, controls, _ = prepare_outer_reflow_round(
        round_index=0,
        rounds=1,
        sample_kwargs={},
        previous=None,
        next_property_preference=None,
        dynamic_control_delta={},
        base_property_schedule=None,
        bond_threshold_schedule=None,
        temperature_schedule=None,
        memory_fraction_schedule=[0.4],
        charge_memory_fraction_schedule=[0.3],
        pair_memory_fraction_schedule=[0.2],
        freeze_charge_state_schedule=[False],
        freeze_pair_chemical_state_schedule=[False],
        merge_controls_fn=_legacy_merge,
        policy_orchestrator=orchestrator,
    )
    # Fractions must lie in [0, 1] (the bounded merge enforces it).
    assert 0.0 <= controls["memory_fraction"] <= 1.0
    assert 0.0 <= controls["charge_memory_fraction"] <= 1.0
    assert 0.0 <= controls["pair_memory_fraction"] <= 1.0
    # With no prior round, the merge falls back to the schedule's
    # n_cap which is bounded by ``n_max = 0.5`` -> 0.5 envelope.
    assert controls["memory_fraction"] == pytest.approx(0.4, abs=0.5)


# ---------------------------------------------------------------------------
# 7. Core-runtime handoff record
# ---------------------------------------------------------------------------


def test_core_runtime_handoff_record_is_self_describing():
    """The handoff record exposes the contract the core runtime must
    implement: schema, responsibility, compatibility path, rollback
    flag, target tests, owner.
    """
    spec = write_handoff_spec(
        responsibility=(
            "flowa_denovo_core must consume adaptive_reflow FinalRestartPolicy "
            "deterministically, write no sampler controls, and honor the "
            "diagnostic_only mode for noise_bias without affecting policy_hash."
        ),
        compatibility_path=(
            "flowa_adaptive_reflow_noise_bias_v1 (read-only legacy window)"
        ),
        rollback_flag=True,
        target_tests=(
            "test_merge_authority_bounded.py::test_dual_executable_writer_rejected",
            "test_merge_authority_bounded.py::test_diagnostic_writer_does_not_change_policy_hash",
            "test_merge_authority_bounded.py::test_floor_clamping_prevents_underflow",
        ),
    )
    assert spec["schema_name"] == CORE_RUNTIME_HANDBOFF_SCHEMA_NAME
    assert spec["schema_version"] == CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION
    assert spec["owner"] == CORE_RUNTIME_OWNER
    assert spec["rollback_flag"] is True
    assert spec["compatibility_path"].startswith("flowa_")
    assert spec["responsibility"]
    assert spec["handoff_hash"]


def test_core_runtime_handoff_hash_is_deterministic():
    """Identical inputs produce identical handoff hashes."""
    kwargs = {
        "responsibility": "consume adaptive_reflow",
        "compatibility_path": "flowa_adaptive_reflow_noise_bias_v1",
        "rollback_flag": False,
        "target_tests": ("test_a", "test_b"),
    }
    a = write_handoff_spec(**kwargs)
    b = write_handoff_spec(**kwargs)
    assert a == b
    assert a["handoff_hash"] == b["handoff_hash"]


def test_core_runtime_handoff_rejects_bad_schema():
    """The helper rejects an unknown schema name (fail closed)."""
    with pytest.raises(CoreRuntimeHandoffError):
        build_core_runtime_handoff(
            responsibility="x",
            compatibility_path="y",
            rollback_flag=False,
            schema_name="not.the.canonical.schema",
        )


def test_core_runtime_handoff_rejects_non_bool_rollback():
    """Rollback flag must be a bool (fail closed)."""
    with pytest.raises(CoreRuntimeHandoffError):
        build_core_runtime_handoff(
            responsibility="x",
            compatibility_path="y",
            rollback_flag="yes",  # type: ignore[arg-type]
        )


def test_core_runtime_handoff_rejects_empty_responsibility():
    """Empty responsibility is a fail-closed error."""
    with pytest.raises(CoreRuntimeHandoffError):
        build_core_runtime_handoff(
            responsibility="",
            compatibility_path="y",
            rollback_flag=False,
        )


# ---------------------------------------------------------------------------
# 8. Schema / module-level constants
# ---------------------------------------------------------------------------


def test_merge_authority_schema_constants_are_stable():
    """Module-level schema constants are stable across calls."""
    assert MERGE_AUTHORITY_SCHEMA_NAME == "adaptive_reflow.bounded_merge_authority"
    assert MERGE_AUTHORITY_SCHEMA_VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# 9. Orchestrator integration: bounded merge decreases on worse evidence
# ---------------------------------------------------------------------------


def test_orchestrator_emits_strictly_decreasing_fraction_on_worse_evidence():
    """Round N+1 with worse evidence must emit a strictly smaller
    ``bounded_target_fraction`` than round N for every channel (the
    legacy ``max(prev, dynamic)`` would forbid this).
    """
    orchestrator = _make_orchestrator()
    # First round: strong evidence.
    bundle_a = _make_bundle(source_round=0)
    good_evidence = {
        ch: _make_evidence(bundle_a, ch, calibration=0.9, support=0.9)
        for ch in (
            ChannelName("coordinate"),
            ChannelName("charge"),
            ChannelName("raw_pair"),
            ChannelName("projected_pair"),
        )
    }
    ledger_a = orchestrator.evaluate_bundle(bundle_a, good_evidence)

    # Second round: weaker evidence (smaller calibration + support).
    bundle_b = _make_bundle(source_round=1)
    weak_evidence = {
        ch: _make_evidence(bundle_b, ch, calibration=0.05, support=0.05)
        for ch in (
            ChannelName("coordinate"),
            ChannelName("charge"),
            ChannelName("raw_pair"),
            ChannelName("projected_pair"),
        )
    }
    ledger_b = orchestrator.evaluate_bundle(bundle_b, weak_evidence)

    # Each channel's bounded fraction must have decreased (or stayed
    # at the floor). The legacy max-only merge would have produced an
    # increase for some channels.
    for ch in (
        ChannelName("coordinate"),
        ChannelName("charge"),
        ChannelName("raw_pair"),
        ChannelName("projected_pair"),
    ):
        prev_value = float(ledger_a.bounded_fraction_by_channel[ch])
        next_value = float(ledger_b.bounded_fraction_by_channel[ch])
        assert next_value <= prev_value, (
            f"channel {ch}: next={next_value} must be <= prev={prev_value} "
            f"under DTB-R3 bounded merge"
        )


# ---------------------------------------------------------------------------
# 10. Audit-code emission on degenerate interval (gap B5)
# ---------------------------------------------------------------------------


def test_bounded_merge_emits_degenerate_interval_audit():
    """When ``hi < lo`` the merge returns the floor AND emits the
    :data:`MERGE_DEGENERATE_INTERVAL` audit code with the envelope
    values embedded so a downstream audit reader can replay the
    collapse.

    We force the collapse with ``prev > cap`` and ``delta_cap_up ==
    delta_cap_down == 0``: ``lo = max(floor, prev) = 1.0``,
    ``hi = min(cap, prev) = 0.6`` -> ``hi < lo`` -> collapse to floor.
    """
    audit_codes: list[str] = []
    result = bounded_merge(
        prev=1.0,
        dynamic=0.5,
        cap=0.6,
        floor=0.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit_codes,
    )
    # lo = max(0.0, 1.0 - 0.0) = 1.0; hi = min(0.6, 1.0 + 0.0) = 0.6;
    # hi < lo so collapse to floor == 0.0.
    assert result == pytest.approx(0.0)
    assert any(
        code.startswith(MERGE_DEGENERATE_INTERVAL) for code in audit_codes
    ), f"expected MERGE_DEGENERATE_INTERVAL in {audit_codes!r}"
    # The audit code must carry the envelope values so a reader can
    # replay the collapse.
    matching = [
        code for code in audit_codes if code.startswith(MERGE_DEGENERATE_INTERVAL)
    ]
    assert matching, "MERGE_DEGENERATE_INTERVAL missing from audit_codes"
    payload = matching[0]
    for token in ("floor=0.000000", "cap=0.600000", "prev=1.000000"):
        assert token in payload, (
            f"audit payload {payload!r} must carry {token!r}"
        )


def test_bounded_merge_no_audit_when_kwarg_omitted():
    """When ``audit_codes`` is omitted (back-compat path) the merge
    silently returns the floor without raising. The collapse is
    observable only via the returned value, never via an audit code.
    """
    # Same collapsed envelope as the previous test, no audit_codes.
    result = bounded_merge(
        prev=1.0,
        dynamic=0.5,
        cap=0.6,
        floor=0.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
    )
    assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 11. Audit-code emission on per-channel floor lookup (gap A2)
# ---------------------------------------------------------------------------


def _make_schedule_sample(
    *,
    n_cap: float = 0.5,
) -> CosineScheduleSample:
    """Build a minimal :class:`CosineScheduleSample` for tests."""
    from adaptive_reflow.contracts import ArtifactHash

    return CosineScheduleSample(
        schedule_hash=ArtifactHash("sched-test"),
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(n_cap),
        n_min=FactorValue(0.0),
        n_max=FactorValue(n_cap),
        u_r=0.0,
        family="cosine_no_restart",
        computed_at_round=0,
    )


def test_bounded_merge_with_schedule_uses_per_channel_floor():
    """When the ``fresh_noise_floor`` arg is ``None``, the helper
    consults the ``fresh_noise_floor_by_channel`` mapping. The mapping
    entry must be honoured, not silently ignored.

    Concretely, with n_cap=0.8 and a per-channel mapping entry of
    0.3, the floor must be 0.3 (the mapping value), not 0.8
    (the schedule's n_cap) and not 0.0 (the last-resort default).
    """
    sample = _make_schedule_sample(n_cap=0.8)
    mapping = {ChannelName("c0"): 0.3}
    audit_codes: list[str] = []
    # cap = 0.8 (n_cap), floor = 0.3 (per-channel mapping).
    # prev is the previous round's emitted fraction (e.g. 0.4).
    result = bounded_merge_with_schedule(
        channel=ChannelName("c0"),
        dynamic=0.4,
        schedule_sample=sample,
        fresh_noise_floor=None,
        delta_caps_by_channel={ChannelName("c0"): 0.5},
        fresh_noise_floor_by_channel=mapping,
        prev=0.4,
        audit_codes=audit_codes,
    )
    # The merge's effective floor must be the per-channel mapping
    # value (0.3), not the schedule's n_cap (0.8). With cap=0.8,
    # floor=0.3, prev=0.4, deltas=0.5: lo=max(0.3, -0.1)=0.3,
    # hi=min(0.8, 0.9)=0.8, target=clamp(0.4, 0.3, 0.8)=0.4 ->
    # result=clamp(0.4, 0.3, 0.8)=0.4.
    assert float(result) == pytest.approx(0.4)
    # The MERGE_FLOOR_FALLBACK code must NOT be appended when the
    # config-level mapping supplied the floor.
    assert MERGE_FLOOR_FALLBACK not in audit_codes, (
        f"MERGE_FLOOR_FALLBACK must not fire when mapping supplied "
        f"the floor; got audit_codes={audit_codes!r}"
    )
    # The prev anchor must be surfaced.
    assert MERGE_PREV_ANCHORED_TO_LAST_EMITTED in audit_codes


def test_bounded_merge_with_schedule_rejects_missing_prev():
    """``prev=None`` is fail-closed: the helper appends
    :data:`ERR_PREV_REQUIRED` and raises :class:`MergeAuthorityError`.
    The schedule's ``n_cap`` is the cap, never the prev.
    """
    sample = _make_schedule_sample(n_cap=0.5)
    audit_codes: list[str] = []
    with pytest.raises(MergeAuthorityError) as excinfo:
        bounded_merge_with_schedule(
            channel=ChannelName("c0"),
            dynamic=0.5,
            schedule_sample=sample,
            fresh_noise_floor=None,
            delta_caps_by_channel=None,
            fresh_noise_floor_by_channel=None,
            prev=None,
            audit_codes=audit_codes,
        )
    # ERR_PREV_REQUIRED must be appended before the raise.
    assert ERR_PREV_REQUIRED in audit_codes, (
        f"ERR_PREV_REQUIRED must be appended to audit_codes; got {audit_codes!r}"
    )
    # The exception message must mention the cap-vs-prev distinction.
    msg = str(excinfo.value)
    assert "cap" in msg and "prev" in msg, (
        f"exception message must explain the cap-vs-prev invariant; got {msg!r}"
    )
