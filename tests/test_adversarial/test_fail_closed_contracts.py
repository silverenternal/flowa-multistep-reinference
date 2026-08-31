"""Phase 1 ADVERSARIAL test suite for adaptive_reflow contracts.

This module is the *additional* layer of hostile / boundary tests
sitting on top of ``test_hostile_cases.py`` (the six enumerated DTB-R0 §3
cases). Where ``test_hostile_cases`` pins the six enumerated hostility
classes, this module exhaustively probes the **structural** and
**boundary** behaviour of the typed contracts:

* ``TestEdgeCases`` — degenerate factor / mapping configurations
  (empty mappings, all-zero / all-one factor sets, contradictory
  cap-vs-floor configurations).
* ``TestBoundaryConditions`` — round-number / channel-name / digest
  boundary inputs (``source_round`` at zero, very large, mismatched
  channel names, empty digest strings).
* ``TestUnsupportedScenarios`` — inputs that are formally valid by
  the ``dataclass`` shape but that the design boundary treats as
  "unsupported" (non-canonical step names, unknown trigger codes,
  all-blocker classifications).

Every test asserts a *specific* fail-closed behaviour. The tests are
intentionally narrow so that a regression in any one blocker path
surfaces as a single failure rather than a cascade.

Stdlib + ``hypothesis`` (installed). No torch. No I/O.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

try:  # pragma: no cover - hypothesis is optional but available
    from hypothesis import HealthCheck, assume, given, settings
    from hypothesis import strategies as st
    HAS_HYPOTHESIS = True
except ImportError:  # pragma: no cover
    HAS_HYPOTHESIS = False

from adaptive_reflow.contracts import (
    COMPLEMENT_BLOCKER_CODES,
    OPERATION_STEPS,
    RESTART_TRIGGER_CODES,
    ArtifactHash,
    BundleId,
    ChannelName,
    ChannelRuleInputs,
    ChannelTransferEvidence,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    PolicyId,
    ProvenanceChain,
    RestartTriggerCode,
    RoundResultBundle,
    RunId,
    SampleId,
    TraceDigest,
    make_default_phase_state,
    validate_final_restart_policy,
    validate_unit_factor,
)
from adaptive_reflow.contracts.bundle import ChannelRuleOutputs
from adaptive_reflow.contracts.schedule import RestartTriggerEvent
from adaptive_reflow.frame.channel_rule import (
    BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL,
    BLOCKER_MISSING_FACTOR,
    BLOCKER_NAN_OR_INF,
    BLOCKER_NON_FINITE,
    BLOCKER_TAIL_INADMISSIBLE,
    ERR_INPUT_FACTOR_TYPE,
    compute_channel_decision,
    evaluate_channel_evidence_with_revocation,
    required_factors_in_unit_interval,
)
from adaptive_reflow.frame.merge import (
    MergeAuthorityError,
    bounded_merge,
    bounded_merge_with_schedule,
)
from adaptive_reflow.universal.adapter import AdapterCapabilities
from adaptive_reflow.universal.state import (
    REFERENCE_FRAMES,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_condition_delta,
    validate_integrator_trace,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Minimal builders (mirroring tests/test_adversarial/test_hostile_cases.py)
# ---------------------------------------------------------------------------


def _make_envelope_manifest() -> FrozenEnvelopeManifest:  # type: ignore[name-defined]
    from adaptive_reflow.contracts import (
        EnvelopeLayer,
        FrozenEnvelopeManifest,
        hash_artifact,
    )

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


def _make_bundle(**overrides) -> RoundResultBundle:
    """Build a minimal valid RoundResultBundle for adversarial probing."""
    from adaptive_reflow.contracts import hash_trace_digest

    bid = BundleId(overrides.pop("bundle_id", "bundle-0"))
    source_round = overrides.pop("source_round", 0)
    trace = TraceDigest(
        hash_trace_digest(bid, source_round, 1, RunId("run-0"), SampleId("sample-0"))
    )

    def _channel(label: str) -> dict:
        if label == "coordinate":
            return {
                "source_round": source_round,
                "channel": label,
                "coordinate_extent_rms": 1.0,
                "pocket_distance": 1.0,
                "pocket_contact_support": 0.5,
            }
        return {
            "source_round": source_round,
            "channel": label,
            "pair_entropy": 0.5,
            "projection_loss": 0.1,
        }

    return RoundResultBundle(
        bundle_id=bid,
        source_round=source_round,
        round_count=1,
        run_id=RunId("run-0"),
        sample_id=SampleId("sample-0"),
        trace_digest=trace,
        condition_digest=TraceDigest(""),
        feedback_mode=overrides.pop("feedback_mode", "inference_external_diagnostic"),
        calibration_artifact_hash=ArtifactHash("calibration-stub"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel=_channel("coordinate"),
        charge_channel=_channel("charge"),
        raw_pair_channel=_channel("raw_pair"),
        projected_pair_channel=_channel("projected_pair"),
        materialization_evidence={"materialization_pass": True, "geometry_pass": True},
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec={"atom_count": 50, "graph_complexity": 10},
        frame_spec={"atom_count": 50, "graph_complexity": 10},
        provenance=ProvenanceChain(("test_provenance",)),
        created_at_round=source_round,
        revoked=False,
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


def _make_channel_rule_inputs(
    *,
    bundle: RoundResultBundle,
    evidence: ChannelTransferEvidence,
    scheduled_cap: float = 0.5,
    mixing_cap: float = 0.5,
    fresh_noise_floor: float = 0.0,
    delta_cap_up: float = 0.5,
    delta_cap_down: float = 0.5,
    tail_admissibility: bool = True,
    complement_excluded: bool = False,
    finite_prefix_only: bool = True,
    frozen_envelope_manifest_hash: ArtifactHash | None = ArtifactHash("env-hash"),
    horizon_coverage_proven: bool = True,
    calibration: float = 0.5,
    perturbation_stability_lower_bound: float = 0.5,
    support_coverage: float = 0.5,
    ambiguity: float = 0.1,
    degeneracy_penalty: float = 0.1,
    recency_decay: float = 0.8,
) -> ChannelRuleInputs:
    """Build a :class:`ChannelRuleInputs` with overrides for every factor."""
    return ChannelRuleInputs(
        bundle=bundle,
        evidence=evidence,
        phase_state=make_default_phase_state(
            horizon_coverage_proven=horizon_coverage_proven,
            operation_order_version="v1",
        ),
        scheduled_cap=FactorValue(scheduled_cap),
        mixing_cap=FactorValue(mixing_cap),
        fresh_noise_floor=FactorValue(fresh_noise_floor),
        delta_cap_up=FactorValue(delta_cap_up),
        delta_cap_down=FactorValue(delta_cap_down),
        tail_admissibility=tail_admissibility,
        complement_excluded=complement_excluded,
        frozen_envelope_manifest_hash=frozen_envelope_manifest_hash,
        finite_prefix_only=finite_prefix_only,
        calibration_lower_bound=FactorValue(calibration),
        perturbation_stability_lower_bound=FactorValue(perturbation_stability_lower_bound),
        support_coverage=FactorValue(support_coverage),
        ambiguity=FactorValue(ambiguity),
        degeneracy_penalty=FactorValue(degeneracy_penalty),
        recency_decay=FactorValue(recency_decay),
        horizon_coverage_proven=horizon_coverage_proven,
        selected_bundle_id=bundle.bundle_id,
    )


def _make_capabilities(supported: tuple[str, ...]) -> AdapterCapabilities:
    """Build an ``AdapterCapabilities`` token supporting the named channels."""
    return AdapterCapabilities(
        has_ode_integration_surface=False,
        has_prior_export=False,
        has_state_export=False,
        has_condition_injection=False,
        has_restart_boundary=False,
        has_continuous_channels=False,
        has_discrete_channels=False,
        has_trajectory_digest=False,
        has_deterministic_seed=False,
        has_materialization_route=False,
        supported_channels=supported,
        channel_domains={},
    )


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """Degenerate factor / mapping configurations."""

    # -----------------------------------------------------------------------

    def test_empty_state_bundle_channels_fails_closed(self) -> None:
        """A :class:`StateBundle` with an empty ``channels`` mapping must
        fail closed at validation.

        Per DTB-G1, ``channels`` is required to be a non-empty mapping;
        a bundle that names no channels cannot be mapped to any adapter
        operation, so the validator must surface the
        ``channels_must_be_non_empty_mapping`` error code.
        """
        caps = _make_capabilities(("coordinate",))
        empty_bundle = StateBundle(
            channels={},  # degenerate: zero channels
            masks={},
            batch_id="b-0",
            sample_id="s-0",
            reference_frame="pocket_centered",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest="digest-stub",
            provenance=("p",),
            capability_token=caps,
        )

        ok, errors = validate_state_bundle(empty_bundle)
        assert ok is False
        assert "channels_must_be_non_empty_mapping" in errors

    # -----------------------------------------------------------------------

    def test_state_bundle_with_nan_string_digest_is_opaque_passthrough(self) -> None:
        """``native_state_digest`` is an opaque hash token. A non-empty
        literal ``"NaN"`` string is structurally valid (the validator
        only requires non-empty).

        This documents the design contract: the engine treats the digest
        as an opaque label and does not parse it as a float. A producer
        that mistakenly serializes ``float('nan')`` as the literal string
        ``"NaN"`` therefore passes structural validation; semantic
        integrity is the responsibility of the producer.
        """
        caps = _make_capabilities(("coordinate",))
        bundle = StateBundle(
            channels={ChannelName("coordinate"): TensorRef("tensor-0")},
            masks={},
            batch_id="b-0",
            sample_id="s-0",
            reference_frame="pocket_centered",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest="NaN",
            provenance=("p",),
            capability_token=caps,
        )
        ok, errors = validate_state_bundle(bundle)
        assert ok is True
        assert errors == ()

    # -----------------------------------------------------------------------

    def test_condition_delta_with_empty_delta_spec_fails_closed(self) -> None:
        """An :class:`ODEConditionDelta` with ``delta_spec={}`` must
        fail closed at validation.

        The adapter contract requires a non-empty ``delta_spec`` so the
        orchestrator knows what to feed into
        :meth:`FlowMatchingODEAdapter.compose_condition`. An empty
        mapping is not a valid declarative description of a delta.
        """
        delta = ODEConditionDelta(
            delta_spec={},  # degenerate: no delta description
            source="producer-x",
            target_round=0,
            calibration_artifact_hash="calib-stub",
        )
        ok, errors = validate_condition_delta(delta)
        assert ok is False
        assert "delta_spec_must_be_non_empty_mapping" in errors

    # -----------------------------------------------------------------------

    def test_final_restart_policy_with_empty_beta_by_channel_is_hash_consistent(self) -> None:
        """A :class:`FinalRestartPolicy` with an empty ``beta_by_channel``
        mapping is structurally admissible — the validator only checks
        ``writer_id`` and the deterministic ``policy_hash`` recompute.

        This test pins the fail-closed boundary: the policy is valid if
        and only if (a) ``writer_id`` is the canonical adaptive_reflow
        writer and (b) ``policy_hash`` matches the recompute of the
        canonical field tuple. An empty channel mapping simply produces
        a deterministic (empty-tuple) hash that the recompute matches.
        """
        empty_policy = FinalRestartPolicy(
            policy_id=PolicyId("policy-0"),
            writer_id="inference.adaptive_reflow",
            run_id=RunId("run-0"),
            target_round=0,
            outer_cycle_id=0,
            beta_by_channel={},
            alpha_by_channel={},
            fresh_noise_floor_by_channel={},
            schedule_sample=None,
            freeze_admission_by_channel={},
            ledger_row_id=LedgerRowId("ledger-0"),
            policy_hash=ArtifactHash(""),  # will be overridden below
            created_at_round=0,
        )
        # Recompute the deterministic hash and re-stamp the policy.
        from adaptive_reflow.contracts.hashes import hash_policy_hash

        expected_hash = hash_policy_hash(empty_policy)
        stamped = empty_policy.__class__(
            **{**empty_policy.__dict__, "policy_hash": expected_hash}
        )
        ok, errors = validate_final_restart_policy(stamped)
        assert ok is True, f"expected valid; got errors={errors!r}"

    # -----------------------------------------------------------------------

    def test_channel_rule_with_all_factors_zero_keeps_gate_open_but_zero_beta(self) -> None:
        """``ChannelRuleInputs`` with every evidence factor at 0 must
        keep the gate OPEN (factors are valid in ``[0, 1]``) and produce
        ``beta=0`` (the multiplicative product of zeros).

        This is the boundary between "closed because invalid" and "open
        but produces nothing". The audit reason must be ``"ok"`` and the
        blocker tuple must be empty.

        DTB-R0 §3 case 2 caveat: ``perturbation_stability_lower_bound``
        is anchored at :data:`PERTURBATION_STABILITY_FLOOR` rather than
        ``0.0`` here so this test still verifies the "all factors valid
        in [0,1] -> gate stays open" invariant without triggering the
        dedicated stability-collapse short-circuit. The dedicated
        collapse path is exercised in
        ``tests/test_adversarial/test_hostile_cases.py``.
        """
        from adaptive_reflow.frame.channel_rule import PERTURBATION_STABILITY_FLOOR

        bundle = _make_bundle()
        evidence = _make_evidence(
            bundle,
            ChannelName("coordinate"),
            calibration=0.0,
            support=0.0,
            perturbation_stability_lower_bound=float(PERTURBATION_STABILITY_FLOOR),
            ambiguity=0.0,
            degeneracy=0.0,
            recency=0.0,
            raw_score=0.0,
        )
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            calibration=0.0,
            support_coverage=0.0,
            perturbation_stability_lower_bound=float(PERTURBATION_STABILITY_FLOOR),
            ambiguity=0.0,
            degeneracy_penalty=0.0,
            recency_decay=0.0,
        )
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is True, (
            "all-zero factor set must remain gate=True; the gate is "
            "closed only on structural failures, not on a zero score"
        )
        assert float(outputs.decision.beta) == 0.0
        assert outputs.decision.blocker_codes == ()
        assert outputs.decision.audit_reason == "ok"
        assert outputs.validation_errors == ()

    # -----------------------------------------------------------------------

    def test_channel_rule_with_all_factors_one_yields_max_beta(self) -> None:
        """``ChannelRuleInputs`` with every factor at 1 must produce
        the maximum admissible beta (bounded by mixing_cap and the
        per-round delta-cap interval).

        For ``mixing_cap=1.0`` and ``delta_cap_up=delta_cap_down=1.0``
        the interval is ``[0, 1]`` so beta saturates at 1.0. The gate
        must be open and the audit reason ``"ok"``.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(
            bundle,
            ChannelName("coordinate"),
            calibration=1.0,
            support=1.0,
            perturbation_stability_lower_bound=1.0,
            ambiguity=0.0,
            degeneracy=0.0,
            recency=1.0,
            raw_score=1.0,
        )
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            calibration=1.0,
            support_coverage=1.0,
            perturbation_stability_lower_bound=1.0,
            ambiguity=0.0,
            degeneracy_penalty=0.0,
            recency_decay=1.0,
            mixing_cap=1.0,
            scheduled_cap=1.0,
            delta_cap_up=1.0,
            delta_cap_down=1.0,
        )
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is True
        assert outputs.decision.audit_reason == "ok"
        assert outputs.decision.blocker_codes == ()
        # At max evidence with full mixing / full cap, beta saturates at 1.0
        assert math.isclose(float(outputs.decision.beta), 1.0, abs_tol=1e-12)
        assert math.isclose(float(outputs.decision.alpha), 0.0, abs_tol=1e-12)

    # -----------------------------------------------------------------------

    def test_channel_rule_with_cap_below_floor_clamps_to_floor(self) -> None:
        """When the delta-cap interval collapses (cap effectively below
        floor) the bounded merge must NOT raise — it must return the
        documented fail-closed floor.

        For ``scheduled_cap=0.1``, ``delta_cap_up=0``,
        ``delta_cap_down=0`` the interval is the single point
        ``{prev=0.1}``. The result is finite, in ``[0, 1]``, and the
        gate stays open.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            scheduled_cap=0.1,
            mixing_cap=1.0,
            delta_cap_up=0.0,
            delta_cap_down=0.0,
        )
        outputs = compute_channel_decision(inputs)
        # Gate is open (factors are valid in [0,1]); the result must be finite.
        assert outputs.decision.gate is True
        beta = float(outputs.decision.beta)
        assert 0.0 <= beta <= 1.0
        assert math.isfinite(beta)
        # At prev=0.1, the only admissible bounded target is 0.1.
        assert math.isclose(beta, 0.1, abs_tol=1e-12)

    # -----------------------------------------------------------------------

    def test_bounded_merge_cap_below_floor_clips_with_audit(self) -> None:
        """P0-3 (F-18): when ``cap < floor``, the bounded_merge primitive
        fails closed — returns the ``floor`` value (no raise) AND emits
        the canonical ``merge_cap_below_floor`` audit code. The earlier
        F5 ``MergeAuthorityError`` raise contradicted the
        :data:`MergeOperatorProtocol` docstring ("implementations MUST
        NOT raise on legitimate caller input such as ``cap <
        floor``") and crashed the runner on legitimate envelopes. The
        audit trail is preserved so a downstream reader can replay the
        broken configuration.
        """
        audit: list[str] = []
        result = bounded_merge(
            prev=0.5,
            dynamic=0.5,
            cap=0.2,
            floor=0.7,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
            audit_codes=audit,
        )
        # Fail-closed: returns the floor value rather than raising.
        assert result == pytest.approx(0.7, abs=1e-12)
        joined = "|".join(audit)
        assert "merge_cap_below_floor" in joined, (
            f"merge_cap_below_floor must appear in audit_codes for "
            f"cap<floor; got {audit!r}"
        )

    # -----------------------------------------------------------------------

    def test_channel_rule_with_mixing_cap_above_scheduled_cap_clamps_to_one(self) -> None:
        """``mixing_cap > scheduled_cap`` (e.g. ``mixing_cap=1.0``,
        ``scheduled_cap=0.5``) must keep the gate open.

        The cap/floor fields must individually lie in ``[0, 1]``; the
        rule then bounds the raw target by ``mixing_cap * scheduled_cap``
        and clamps to ``[0, 1]``. The resulting beta must lie in
        ``[0, 1]`` and the audit reason must be ``"ok"``.

        Note: ``mixing_cap > 1.0`` is rejected by the unit-interval
        guard; that path is exercised separately in
        ``test_channel_rule_with_cap_floor_factor_out_of_unit_interval``.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            scheduled_cap=0.5,
            mixing_cap=1.0,  # legal max, above scheduled_cap
            delta_cap_up=1.0,
            delta_cap_down=1.0,
        )
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is True
        beta = float(outputs.decision.beta)
        assert 0.0 <= beta <= 1.0
        assert math.isfinite(beta)
        # With factors at 0.5 (calibration, support, stability), recency 0.8,
        # (1-ambiguity)=0.9, (1-degeneracy)=0.9, the evidence score is:
        # 0.5*0.5*0.5*0.9*0.9*0.8 = 0.081
        # raw_target = min(1, 1.0 * 0.5 * 0.081) = min(1, 0.0405) = 0.0405
        # bounded into [0, 1] (delta_cap interval is [0, 1.5] -> [0, 1])
        # so beta = 0.0405 (within tolerance)
        assert math.isclose(beta, 0.0405, abs_tol=1e-9)


# ===========================================================================
# TestBoundaryConditions
# ===========================================================================


class TestBoundaryConditions:
    """Boundary-value inputs for round / channel / digest fields."""

    # -----------------------------------------------------------------------

    def test_state_bundle_source_round_at_zero_is_valid(self) -> None:
        """``source_round=0`` is the lowest legal value (the run-start
        round). The validator must accept it.
        """
        caps = _make_capabilities(("coordinate",))
        bundle = StateBundle(
            channels={ChannelName("coordinate"): TensorRef("tensor-0")},
            masks={},
            batch_id="b-0",
            sample_id="s-0",
            reference_frame="pocket_centered",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest="digest-stub",
            provenance=("p",),
            capability_token=caps,
        )
        ok, errors = validate_state_bundle(bundle)
        assert ok is True
        assert errors == ()

    # -----------------------------------------------------------------------

    def test_state_bundle_source_round_very_large_is_valid(self) -> None:
        """``source_round=10**9`` is far outside any realistic run but
        must still validate. The validator only checks
        ``isinstance(int)`` and ``>= 0``.

        This documents that no implicit "round limit" is enforced at the
        state-bundle layer; the engine treats ``source_round`` as an
        opaque non-negative integer.
        """
        caps = _make_capabilities(("coordinate",))
        bundle = StateBundle(
            channels={ChannelName("coordinate"): TensorRef("tensor-0")},
            masks={},
            batch_id="b-0",
            sample_id="s-0",
            reference_frame="pocket_centered",
            normalization="none",
            source_round=10**9,
            detach_proof=True,
            native_state_digest="digest-stub",
            provenance=("p",),
            capability_token=caps,
        )
        ok, errors = validate_state_bundle(bundle)
        assert ok is True
        assert errors == ()

    # -----------------------------------------------------------------------

    def test_state_bundle_source_round_negative_fails_closed(self) -> None:
        """Negative ``source_round`` must fail closed.
        """
        caps = _make_capabilities(("coordinate",))
        bundle = StateBundle(
            channels={ChannelName("coordinate"): TensorRef("tensor-0")},
            masks={},
            batch_id="b-0",
            sample_id="s-0",
            reference_frame="pocket_centered",
            normalization="none",
            source_round=-1,
            detach_proof=True,
            native_state_digest="digest-stub",
            provenance=("p",),
            capability_token=caps,
        )
        ok, errors = validate_state_bundle(bundle)
        assert ok is False
        assert "source_round_must_be_non_negative" in errors

    # -----------------------------------------------------------------------

    def test_final_restart_policy_with_mismatched_channel_names_validates_by_hash(self) -> None:
        """A :class:`FinalRestartPolicy` whose ``beta_by_channel`` /
        ``alpha_by_channel`` use channel names that do not match the
        canonical molecule vocabulary still validates — the validator
        only enforces ``writer_id`` + ``policy_hash`` determinism.

        This pins the boundary: the typed contract does not currently
        enforce channel-name consistency between the per-channel
        mappings (it relies on the orchestrator to keep them in sync).
        The test asserts the **current** behaviour with a clear comment
        so future tightening of this contract is visible.
        """
        from adaptive_reflow.contracts.hashes import hash_policy_hash

        # Channel names that are NOT in the canonical molecule vocabulary.
        weird = ChannelName("non_canonical_channel_z")
        policy = FinalRestartPolicy(
            policy_id=PolicyId("policy-0"),
            writer_id="inference.adaptive_reflow",
            run_id=RunId("run-0"),
            target_round=0,
            outer_cycle_id=0,
            beta_by_channel={weird: FactorValue(0.25)},
            alpha_by_channel={weird: FactorValue(0.75)},
            fresh_noise_floor_by_channel={weird: FactorValue(0.0)},
            schedule_sample=None,
            freeze_admission_by_channel={weird: False},
            ledger_row_id=LedgerRowId("ledger-0"),
            policy_hash=ArtifactHash(""),
            created_at_round=0,
        )
        # Stamp the deterministic hash.
        expected_hash = hash_policy_hash(policy)
        # Reconstruct with the canonical hash.
        stamped_dict = dict(policy.__dict__)
        stamped_dict["policy_hash"] = expected_hash
        stamped = FinalRestartPolicy(**stamped_dict)

        ok, errors = validate_final_restart_policy(stamped)
        # Current contract: mismatched / unknown channel names do NOT
        # cause validation to fail. The validator only inspects
        # writer_id + policy_hash. Documenting this so future
        # tightening of the contract is a deliberate change.
        assert ok is True, (
            f"unknown channel name currently passes validation; "
            f"errors={errors!r}"
        )

    # -----------------------------------------------------------------------

    def test_final_restart_policy_with_wrong_writer_id_fails_closed(self) -> None:
        """A :class:`FinalRestartPolicy` whose ``writer_id`` is not the
        canonical ``"inference.adaptive_reflow"`` must fail closed.
        """
        from adaptive_reflow.contracts.hashes import hash_policy_hash

        policy = FinalRestartPolicy(
            policy_id=PolicyId("policy-0"),
            writer_id="inference.some_other_component",  # wrong writer
            run_id=RunId("run-0"),
            target_round=0,
            outer_cycle_id=0,
            beta_by_channel={},
            alpha_by_channel={},
            fresh_noise_floor_by_channel={},
            schedule_sample=None,
            freeze_admission_by_channel={},
            ledger_row_id=LedgerRowId("ledger-0"),
            policy_hash=ArtifactHash(""),
            created_at_round=0,
        )
        # Recompute the hash with the WRONG writer_id; the validator
        # must still reject because writer_id != "inference.adaptive_reflow".
        expected_hash = hash_policy_hash(policy)
        stamped_dict = dict(policy.__dict__)
        stamped_dict["policy_hash"] = expected_hash
        stamped = FinalRestartPolicy(**stamped_dict)
        ok, errors = validate_final_restart_policy(stamped)
        assert ok is False
        assert any("writer_id" in e for e in errors)

    # -----------------------------------------------------------------------

    def test_state_bundle_with_empty_native_state_digest_fails_closed(self) -> None:
        """``StateBundle.native_state_digest`` must be a non-empty
        string. An empty string must fail closed with the canonical
        error code.
        """
        caps = _make_capabilities(("coordinate",))
        bundle = StateBundle(
            channels={ChannelName("coordinate"): TensorRef("tensor-0")},
            masks={},
            batch_id="b-0",
            sample_id="s-0",
            reference_frame="pocket_centered",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest="",  # empty -> invalid
            provenance=("p",),
            capability_token=caps,
        )
        ok, errors = validate_state_bundle(bundle)
        assert ok is False
        assert "native_state_digest_must_be_non_empty" in errors

    # -----------------------------------------------------------------------

    def test_integrator_trace_with_empty_state_digest_fails_closed(self) -> None:
        """``ODEIntegratorTrace.native_state_digest`` must be non-empty.
        """
        trace = ODEIntegratorTrace(
            steps=10,
            accept_rate=0.5,
            native_state_digest="",
            integrator_config_hash="cfg-stub",
        )
        ok, errors = validate_integrator_trace(trace)
        assert ok is False
        assert "native_state_digest_must_be_non_empty" in errors


# ===========================================================================
# TestUnsupportedScenarios
# ===========================================================================


class TestUnsupportedScenarios:
    """Scenarios that are formally constructible but outside the design boundary."""

    # -----------------------------------------------------------------------

    def test_operation_step_with_non_canonical_name_is_constructible(self) -> None:
        """``OPERATION_STEPS`` is the canonical literal set. A
        non-canonical step name (e.g. ``"unsupported_step"``) is not in
        the set; the contract treats it as an unsupported operation.

        This test pins the boundary by asserting the literal set's
        contents (so an accidental widening is visible) and constructs
        a non-canonical ``operation_order`` to assert that the typed
        ``OperationCompositionContract`` does NOT silently accept it
        for semantic equality — the consumer is expected to compare
        against ``OPERATION_STEPS``.
        """
        from adaptive_reflow.contracts.operations import OperationCompositionContract

        # 1. Pin the canonical literal set: a step name like
        #    "unsupported_step" must NOT be present.
        assert "unsupported_step" not in OPERATION_STEPS
        assert "validate" in OPERATION_STEPS
        assert "native_ODE_solve" in OPERATION_STEPS

        # 2. The dataclass accepts any tuple[str, ...] at construction
        #    (the type system uses ``tuple[str, ...]``), but a consumer
        #    that compares against ``OPERATION_STEPS`` must reject the
        #    non-canonical order. Demonstrate by set difference:
        non_canonical = ("validate", "select", "unsupported_step")
        assert set(non_canonical) - set(OPERATION_STEPS) == {"unsupported_step"}

        # 3. The dataclass itself stores the value; the validator layer
        #    is responsible for semantic rejection.
        contract = OperationCompositionContract(
            version="v1",
            operation_order=non_canonical,
            commutator_residual_tolerance=0.0,
        )
        assert contract.operation_order == non_canonical
        # The semantic fail-closed comparison is the consumer's job:
        unsupported_in_order = [
            step for step in contract.operation_order
            if step not in OPERATION_STEPS
        ]
        assert unsupported_in_order == ["unsupported_step"]

    # -----------------------------------------------------------------------

    def test_restart_trigger_event_with_unknown_trigger_code_is_constructible(self) -> None:
        """``RestartTriggerEvent.trigger_code`` is typed as the
        ``RestartTriggerCode`` NewType, which is a string at runtime.
        An unknown code (e.g. ``"unknown_trigger"``) is not in
        ``RESTART_TRIGGER_CODES``; the contract is constructible but
        the orchestrator is expected to reject it.

        Pin the boundary: the literal set membership check is what
        makes an unknown code "unsupported".
        """
        unknown_code: RestartTriggerCode = RestartTriggerCode("unknown_trigger")
        assert unknown_code not in RESTART_TRIGGER_CODES
        # All canonical codes are present in the literal set:
        for code in (
            "tail_budget_violation",
            "complement_unclassified",
            "materialization_regression",
            "geometry_regression",
            "calibration_drift",
            "valid_evidence_no_progress",
        ):
            assert RestartTriggerCode(code) in RESTART_TRIGGER_CODES

        # The dataclass accepts any string at construction; semantic
        # rejection is the orchestrator's job.
        event = RestartTriggerEvent(
            trigger_id="trigger-0",
            outer_cycle_id_old=0,
            outer_cycle_id_new=1,
            trigger_code=unknown_code,
            trigger_metric_snapshot={"metric": 0.0},
            discarded_source_bundle_ids=(BundleId("bundle-0"),),
            noise_capacity_before=FactorValue(0.5),
            noise_capacity_after=FactorValue(0.5),
            unresolved_metric_deficit={},
            provenance=ProvenanceChain(("test",)),
            recorded_at_round=1,
        )
        assert str(event.trigger_code) == "unknown_trigger"
        assert event.trigger_code not in RESTART_TRIGGER_CODES

    # -----------------------------------------------------------------------

    def test_envelope_classification_with_all_blocker_codes(self) -> None:
        """``EnvelopeClassification.complement_blocker`` is typed as
        :data:`ComplementBlockerCode`. The canonical literal set
        (``COMPLEMENT_BLOCKER_CODES``) contains the six molecule
        blocker codes; a classification that names *every* blocker code
        is structurally admissible but semantically meaningless.

        Pin the literal set and assert that the dataclass carries
        arbitrary blocker strings without parsing them.
        """
        from adaptive_reflow.contracts import (
            ComplementBlockerCode,
            EnvelopeClassification,
        )

        # Pin the canonical set membership:
        expected_codes = {
            "out_of_envelope",
            "materialization_failure",
            "geometry_failure",
            "evaluator_provenance_missing",
            "lineage_invalid",
            "unclassified",
        }
        assert set(COMPLEMENT_BLOCKER_CODES) == expected_codes

        # A classification with a single blocker code (the documented
        # "first match" semantics) is the only meaningful configuration.
        classification = EnvelopeClassification(
            bundle_id=BundleId("bundle-0"),
            matched_layer_index=None,
            complement_blocker=ComplementBlockerCode("unclassified"),
            within_layer_thresholds=False,
            residual_extents={"coord": 0.5},
        )
        assert str(classification.complement_blocker) == "unclassified"
        assert classification.complement_blocker in COMPLEMENT_BLOCKER_CODES

        # The literal set is exactly six codes; a "all-blocker"
        # classification is not a documented configuration.
        assert len(COMPLEMENT_BLOCKER_CODES) == 6

    # -----------------------------------------------------------------------

    def test_channel_rule_with_cap_floor_factor_out_of_unit_interval(self) -> None:
        """A cap / floor / delta-cap field outside ``[0, 1]`` must
        produce the canonical ``BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL``
        code.

        Set ``mixing_cap=1.5`` (above unit interval). The rule must
        still gate=True but emit the precise blocker code so the
        consumer can surface the cause.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            mixing_cap=1.5,  # out of [0, 1]
        )
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is False
        # The blocker code must be the precise out-of-unit-interval one:
        assert any(
            code.startswith(BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL)
            for code in outputs.decision.blocker_codes
        )
        assert float(outputs.decision.beta) == 0.0

    # -----------------------------------------------------------------------

    def test_channel_rule_with_nan_cap_fails_closed(self) -> None:
        """A NaN cap value must close the gate with the canonical
        ``required_factor_not_finite`` blocker code.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            mixing_cap=float("nan"),  # NaN cap
        )
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is False
        assert any(
            BLOCKER_NAN_OR_INF in code
            for code in outputs.decision.blocker_codes
        )
        assert float(outputs.decision.beta) == 0.0

    # -----------------------------------------------------------------------

    def test_channel_rule_with_none_factor_marks_missing(self) -> None:
        """A :class:`ChannelRuleInputs` with ``calibration_lower_bound=None``
        must surface ``BLOCKER_MISSING_FACTOR:calibration_lower_bound``
        and close the gate.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
        )
        # dataclass(frozen=True) — use object.__setattr__ to inject None.
        object.__setattr__(inputs, "calibration_lower_bound", None)
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is False
        assert any(
            code == f"{BLOCKER_MISSING_FACTOR}:calibration_lower_bound"
            for code in outputs.decision.blocker_codes
        )

    # -----------------------------------------------------------------------

    def test_channel_rule_tail_inadmissibility_closes_gate(self) -> None:
        """``tail_admissibility=False`` must close the gate with the
        canonical ``BLOCKER_TAIL_INADMISSIBLE`` code (DTB-NC2).
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            tail_admissibility=False,
        )
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is False
        assert BLOCKER_TAIL_INADMISSIBLE in outputs.decision.blocker_codes
        assert float(outputs.decision.beta) == 0.0

    # -----------------------------------------------------------------------

    def test_required_factors_helper_reports_nan_inputs(self) -> None:
        """The ``required_factors_in_unit_interval`` helper must report
        NaN factors as failed. This pins the deterministic blocker-code
        suffix mapping.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            calibration=float("nan"),
        )
        failed = required_factors_in_unit_interval(inputs)
        assert "calibration_lower_bound" in failed

    # -----------------------------------------------------------------------

    def test_stability_collapse_handles_malformed_scheduled_cap(self) -> None:
        """Algorithmic gap A1 (fail-closed): ``_build_stability_collapse_outputs``
        must coerce a malformed ``scheduled_cap`` to ``0.0`` instead of
        propagating the underlying :exc:`TypeError`.

        With ``perturbation_stability_lower_bound`` below the
        :data:`PERTURBATION_STABILITY_FLOOR` the stability-collapse branch
        fires. Injecting ``scheduled_cap="not-a-float"`` (a non-numeric
        string) must NOT raise — the rule returns a
        :class:`ChannelRuleOutputs` with ``gate=False`` and surfaces the
        :data:`ERR_INPUT_FACTOR_TYPE` audit code so the consumer can
        recognise the malformed-field cause.
        """
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            # Below the floor -> the stability-collapse branch fires.
            perturbation_stability_lower_bound=0.1,
        )
        # dataclass(frozen=True) — bypass the type guard via
        # object.__setattr__ to inject a malformed value.
        object.__setattr__(inputs, "scheduled_cap", "not-a-float")

        # Must NOT raise; the helper coerces-or-zeroes.
        outputs = evaluate_channel_evidence_with_revocation(inputs)
        assert outputs.decision.gate is False
        # Audit trail must surface the canonical ERR_INPUT_FACTOR_TYPE
        # code with the field-name suffix so the consumer can pinpoint
        # the offending field.
        assert (
            f"{ERR_INPUT_FACTOR_TYPE}:scheduled_cap"
            in outputs.decision.audit_reason
        ) or any(
            code == f"{ERR_INPUT_FACTOR_TYPE}:scheduled_cap"
            for code in outputs.decision.blocker_codes
        )
        # The collapse-branch audit code stays present so the consumer
        # can still recognise the DTB-R0 §3 case 2 cause.
        assert outputs.decision.audit_reason.startswith(
            "perturbation_stability_below_threshold"
        )
        # scheduled_cap was coerced to 0.0; alpha=1, beta=0 by design.
        assert float(outputs.decision.scheduled_cap) == 0.0
        assert float(outputs.decision.beta) == 0.0
        assert float(outputs.decision.alpha) == 1.0

    # -----------------------------------------------------------------------

    def test_revocation_handles_malformed_fresh_noise_floor(self) -> None:
        """Algorithmic gap A1 (fail-closed): the dynamic-compute branch
        in :func:`evaluate_channel_evidence_with_revocation` must coerce
        a malformed ``fresh_noise_floor`` (``None``) to ``0.0`` instead
        of propagating the underlying :exc:`TypeError`.

        With ``bundle.revoked=True`` the dynamic-compute branch fires
        (before any gate evaluation). Injecting ``fresh_noise_floor=None``
        must NOT raise — the rule returns a :class:`ChannelRuleOutputs`
        with ``gate=False`` and surfaces the :data:`ERR_INPUT_FACTOR_TYPE`
        audit code so the consumer can recognise the malformed-field
        cause.
        """
        bundle = _make_bundle()
        # dataclass(frozen=True) — flip the revocation flag via
        # object.__setattr__ so the dynamic-compute branch fires.
        object.__setattr__(bundle, "revoked", True)
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
        )
        # dataclass(frozen=True) — bypass the type guard via
        # object.__setattr__ to inject a malformed value.
        object.__setattr__(inputs, "fresh_noise_floor", None)

        # Must NOT raise; the helper coerces-or-zeroes.
        outputs = evaluate_channel_evidence_with_revocation(inputs)
        assert outputs.decision.gate is False
        # Audit trail must surface the canonical ERR_INPUT_FACTOR_TYPE
        # code with the field-name suffix.
        assert (
            f"{ERR_INPUT_FACTOR_TYPE}:fresh_noise_floor"
            in outputs.decision.audit_reason
        ) or any(
            code == f"{ERR_INPUT_FACTOR_TYPE}:fresh_noise_floor"
            for code in outputs.decision.blocker_codes
        )
        # The revocation audit code stays present so the consumer can
        # still recognise the DTB-R0 §3 case 5 cause.
        assert "source_revoked" in outputs.decision.audit_reason
        # fresh_noise_floor was coerced to 0.0.
        assert float(outputs.decision.fresh_noise_floor) == 0.0
        assert float(outputs.decision.beta) == 0.0
        assert float(outputs.decision.alpha) == 1.0


# ===========================================================================
# Property-based tests (only run if hypothesis is installed)
# ===========================================================================


if HAS_HYPOTHESIS:

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(
        bad_factor=st.floats(
            min_value=1.0001, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25, suppress_health_check=[HealthCheck.too_slow])
    def test_property_out_of_unit_interval_factor_always_closes_gate(bad_factor: float) -> None:
        """Property: any single evidence factor strictly above 1.0 must
        close the gate. Sweeps a wide range of out-of-unit-interval
        values to catch accidental floating-point surprises (e.g. a
        wrong clamp that accidentally admits 1.0 + epsilon).
        """
        assume(bad_factor > 1.0)
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            calibration=bad_factor,
        )
        outputs = compute_channel_decision(inputs)
        assert outputs.decision.gate is False
        assert float(outputs.decision.beta) == 0.0
        assert any(
            BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL in code
            for code in outputs.decision.blocker_codes
        )

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(
        good_factor=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=25, suppress_health_check=[HealthCheck.too_slow])
    def test_property_unit_interval_factor_keeps_gate_open(good_factor: float) -> None:
        """Property: any single evidence factor in ``[0, 1]`` (the
        legal range) keeps the gate OPEN. Combined with the other
        factors at their default legal values, the rule produces a
        finite beta.
        """
        assume(0.0 <= good_factor <= 1.0)
        bundle = _make_bundle()
        evidence = _make_evidence(bundle, ChannelName("coordinate"))
        inputs = _make_channel_rule_inputs(
            bundle=bundle,
            evidence=evidence,
            calibration=good_factor,
        )
        outputs = compute_channel_decision(inputs)
        # With valid factors, the gate must be open and beta must be
        # finite and within [0, 1].
        assert outputs.decision.gate is True
        beta = float(outputs.decision.beta)
        assert math.isfinite(beta)
        assert 0.0 <= beta <= 1.0

    @pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
    @given(
        sr=st.integers(min_value=0, max_value=10**12),
    )
    @settings(max_examples=25, suppress_health_check=[HealthCheck.too_slow])
    def test_property_state_bundle_source_round_non_negative(sr: int) -> None:
        """Property: any non-negative integer ``source_round`` produces
        a structurally valid :class:`StateBundle`. Confirms the only
        structural check on ``source_round`` is the non-negative
        integer type guard.
        """
        assume(sr >= 0)
        caps = _make_capabilities(("coordinate",))
        bundle = StateBundle(
            channels={ChannelName("coordinate"): TensorRef("tensor-0")},
            masks={},
            batch_id="b-0",
            sample_id="s-0",
            reference_frame="pocket_centered",
            normalization="none",
            source_round=sr,
            detach_proof=True,
            native_state_digest="digest-stub",
            provenance=("p",),
            capability_token=caps,
        )
        ok, errors = validate_state_bundle(bundle)
        assert ok is True
        assert errors == ()
