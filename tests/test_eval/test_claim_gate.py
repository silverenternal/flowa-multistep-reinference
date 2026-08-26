"""Tests for the DTB-R8 structural promotion / rollback / claim gate.

These tests exercise the structural half of DTB-R8 only. They do not
require R7 GPU data: numeric ``gain`` / ``cost`` fields are placeholders
and every :class:`ClaimGateDecision` is expected to be ``"defer"`` until
R7 evidence lands.

NO torch. NO I/O. NO mutation of inputs.
"""

from __future__ import annotations

import dataclasses
import math
import os
import sys

import pytest

# Ensure the package root is importable when pytest is invoked from the
# repository root (which is how the brief specifies running tests).
_PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

# The repository is a flat module layout (no ``__init__.py``). The
# modules therefore expose themselves as top-level packages when the
# repository root is on ``sys.path``. We import them via their dotted
# relative path so that the existing ``from .restart_memory_types``
# style imports inside each module continue to resolve.
from adaptive_reflow.contracts import (
    ArtifactHash,
    RunId,
)
from adaptive_reflow.eval import (
    DEFAULT_DISABLED_REASON,
    DEFERRED_COST,
    DEFERRED_GAIN,
    DEFERRED_R8_REASON,
    TIER_LABELS,
    ClaimGateArgumentError,
    ClaimGateEvaluation,
    LayeredMetricPanel,
    LayeredMetricPanelArgumentError,
    PolicyVersionHashRecorder,
    PromotionArgumentError,
    PromotionReport,
    RollbackArgumentError,
    RollbackAudit,
    RollbackFlag,
    apply_rollback,
    build_default_claim_gate_config,
    build_default_layered_metric_panel,
    build_deferred_promotion_report,
    build_disabled_rollback_flag,
    derive_policy_hash_from_version,
    enforce_separation,
    evaluate_claim_gate,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _enabled_config(
    *,
    required_contracts_passing=("contract_a", "contract_b"),
    required_paired_evidence_count=2,
    evaluation_window_rounds=1,
    minimum_confidence_interval_coverage=0.5,
):
    return build_default_claim_gate_config(
        required_contracts_passing=required_contracts_passing,
        required_paired_evidence_count=required_paired_evidence_count,
        gate_enabled=True,
        evaluation_window_rounds=evaluation_window_rounds,
        minimum_confidence_interval_coverage=minimum_confidence_interval_coverage,
    )


def _passing_evidence(extra: dict | None = None) -> dict:
    base = {
        "contract_a": {"passed": True, "summary": "ok"},
        "contract_b": {"passed": True, "summary": "ok"},
        "paired_evidence_count": 5,
        "confidence_interval_coverage": 0.9,
        "evaluation_window_rounds": 3,
    }
    if extra:
        base.update(extra)
    return base


# ---------------------------------------------------------------------------
# 1. Gate conditions: all-or-nothing; any failure -> defer/rollback
# ---------------------------------------------------------------------------


class TestClaimGateAllOrNothing:
    def test_all_conditions_passed_still_defers_structurally(self):
        """Every condition satisfied but structural evaluator defers.

        The structural evaluator never emits 'promote' or 'rollback'
        until R7 GPU data lands; we assert the literal decision is
        'defer' and that all expected conditions are in the passed
        tuple.
        """
        config = _enabled_config()
        evidence = _passing_evidence()
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=1
        )
        assert isinstance(evaluation, ClaimGateEvaluation)
        assert evaluation.decision == "defer"
        assert "contract:contract_a" in evaluation.gate_conditions_passed
        assert "contract:contract_b" in evaluation.gate_conditions_passed
        assert "paired_evidence_count" in evaluation.gate_conditions_passed
        assert (
            "confidence_interval_coverage"
            in evaluation.gate_conditions_passed
        )
        assert (
            "evaluation_window_rounds" in evaluation.gate_conditions_passed
        )
        assert evaluation.gate_conditions_failed == ()

    def test_missing_evidence_defers_with_marker(self):
        """``None``/empty evidence always defers with ``missing_evidence``."""
        config = _enabled_config()
        for empty in (None, {}):
            evaluation = evaluate_claim_gate(
                config, empty, evaluated_at_round=0
            )
            assert evaluation.decision == "defer"
            # With an enabled gate, empty evidence triggers an
            # explicit ``missing_evidence`` marker.
            assert "missing_evidence" in evaluation.gate_conditions_failed
            assert evaluation.gate_conditions_failed

    def test_single_contract_failure_defers(self):
        """A single failed contract -> ``defer``."""
        config = _enabled_config()
        evidence = _passing_evidence()
        evidence["contract_b"] = {"passed": False, "summary": "fail"}
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=2
        )
        assert evaluation.decision == "defer"
        assert "contract_failed:contract_b" in (
            evaluation.gate_conditions_failed
        )
        assert "contract:contract_a" in (
            evaluation.gate_conditions_passed
        )

    def test_insufficient_paired_evidence_defers(self):
        config = _enabled_config(required_paired_evidence_count=10)
        evidence = _passing_evidence()
        evidence["paired_evidence_count"] = 3
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=3
        )
        assert evaluation.decision == "defer"
        assert "paired_evidence_count:insufficient" in (
            evaluation.gate_conditions_failed
        )

    def test_insufficient_confidence_interval_defers(self):
        config = _enabled_config(minimum_confidence_interval_coverage=0.95)
        evidence = _passing_evidence()
        evidence["confidence_interval_coverage"] = 0.5
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=4
        )
        assert evaluation.decision == "defer"
        assert "confidence_interval_coverage:insufficient" in (
            evaluation.gate_conditions_failed
        )

    def test_insufficient_evaluation_window_defers(self):
        config = _enabled_config(evaluation_window_rounds=10)
        evidence = _passing_evidence()
        evidence["evaluation_window_rounds"] = 1
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=5
        )
        assert evaluation.decision == "defer"
        assert "evaluation_window_rounds:insufficient" in (
            evaluation.gate_conditions_failed
        )

    def test_missing_calibration_artifact_hash_defers(self):
        config = build_default_claim_gate_config(
            required_contracts_passing=("contract_a",),
            required_calibration_artifact_hash=ArtifactHash(
                "deadbeef" * 8
            ),
            gate_enabled=True,
        )
        evidence = {
            "contract_a": {"passed": True},
            # No calibration_artifact entry -> missing marker
        }
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=6
        )
        assert evaluation.decision == "defer"
        assert "calibration_artifact:missing" in (
            evaluation.gate_conditions_failed
        )

    def test_calibration_artifact_hash_mismatch_defers(self):
        config = build_default_claim_gate_config(
            required_contracts_passing=("contract_a",),
            required_calibration_artifact_hash=ArtifactHash(
                "deadbeef" * 8
            ),
            gate_enabled=True,
        )
        evidence = {
            "contract_a": {"passed": True},
            "calibration_artifact": {
                "hash": "f" * 64,  # different
            },
        }
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=7
        )
        assert evaluation.decision == "defer"
        assert "calibration_artifact:mismatch" in (
            evaluation.gate_conditions_failed
        )

    def test_calibration_artifact_hash_match_passes(self):
        expected = ArtifactHash("a" * 64)
        config = build_default_claim_gate_config(
            required_contracts_passing=("contract_a",),
            required_calibration_artifact_hash=expected,
            gate_enabled=True,
        )
        evidence = {
            "contract_a": {"passed": True},
            "calibration_artifact": {"hash": str(expected)},
        }
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=8
        )
        assert evaluation.decision == "defer"
        assert "calibration_artifact" in (
            evaluation.gate_conditions_passed
        )

    def test_gate_disabled_marks_disabled_and_defers(self):
        config = build_default_claim_gate_config(
            gate_enabled=False,
            required_contracts_passing=("contract_a",),
        )
        evidence = _passing_evidence()
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=9
        )
        assert evaluation.decision == "defer"
        assert "gate_disabled" in evaluation.gate_conditions_failed

    def test_decision_is_deferred_only_in_structural_module(self):
        """The structural evaluator never emits promote or rollback."""
        config = _enabled_config()
        evidence = _passing_evidence()
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=10
        )
        assert evaluation.decision in ("promote", "rollback", "defer")
        assert evaluation.decision == "defer"

    def test_evaluation_summary_contains_required_fields(self):
        config = _enabled_config()
        evidence = _passing_evidence()
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=11
        )
        for key in (
            "required_contracts_passing",
            "required_paired_evidence_count",
            "evaluation_window_rounds",
            "minimum_confidence_interval_coverage",
            "gate_enabled",
            "deferred_reason",
        ):
            assert key in evaluation.evidence_summary
        assert (
            evaluation.evidence_summary["deferred_reason"]
            == DEFERRED_R8_REASON
        )


class TestClaimGateConfigValidation:
    def test_negative_paired_evidence_rejected(self):
        with pytest.raises(ClaimGateArgumentError):
            build_default_claim_gate_config(
                required_paired_evidence_count=-1,
            )

    def test_negative_window_rejected(self):
        with pytest.raises(ClaimGateArgumentError):
            build_default_claim_gate_config(
                evaluation_window_rounds=-2,
            )

    def test_coverage_out_of_range_rejected(self):
        with pytest.raises(ClaimGateArgumentError):
            build_default_claim_gate_config(
                minimum_confidence_interval_coverage=1.5,
            )

    def test_coverage_not_finite_rejected(self):
        with pytest.raises(ClaimGateArgumentError):
            build_default_claim_gate_config(
                minimum_confidence_interval_coverage=float("inf"),
            )

    def test_negative_evaluated_at_round_rejected(self):
        config = _enabled_config()
        with pytest.raises(ClaimGateArgumentError):
            evaluate_claim_gate(
                config, _passing_evidence(), evaluated_at_round=-1
            )

    def test_config_is_frozen(self):
        config = _enabled_config()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.gate_enabled = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 2. Single disabled flag rollback (single_stateless=True enforced)
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    def test_default_flag_has_required_invariants(self):
        flag = build_disabled_rollback_flag(set_at_round=0)
        assert isinstance(flag, RollbackFlag)
        assert flag.disabled is True
        assert flag.single_stateless is True
        assert flag.set_at_round == 0
        assert flag.reason == DEFAULT_DISABLED_REASON

    def test_apply_rollback_returns_audit(self):
        flag = build_disabled_rollback_flag(set_at_round=3)
        audit = apply_rollback(
            flag,
            prior_state={"policy": "v1"},
            post_state={"policy": "v1"},
            applied_at_round=4,
        )
        assert isinstance(audit, RollbackAudit)
        assert audit.flag is flag
        assert audit.applied_at_round == 4
        assert audit.prior_state_digest != ""
        assert audit.post_state_digest != ""

    def test_apply_rollback_is_stateless(self):
        """Applier never migrates artifacts; digests are equal."""
        flag = build_disabled_rollback_flag(set_at_round=1)
        prior = {"policy": "v0", "calibration": "abc"}
        post = {"policy": "v0", "calibration": "abc"}  # no migration
        audit = apply_rollback(
            flag, prior_state=prior, post_state=post, applied_at_round=2
        )
        # Stateless applier -> identical state -> identical digest.
        assert audit.prior_state_digest == audit.post_state_digest

    def test_apply_rollback_rejects_non_disabled_flag(self):
        """A hand-rolled RollbackFlag with disabled=False is rejected."""
        bad_flag = RollbackFlag(
            disabled=False,
            set_at_round=0,
            reason="not disabled",
            single_stateless=True,
        )
        with pytest.raises(RollbackArgumentError):
            apply_rollback(
                bad_flag,
                prior_state={},
                post_state={},
                applied_at_round=0,
            )

    def test_apply_rollback_rejects_non_stateless_flag(self):
        bad_flag = RollbackFlag(
            disabled=True,
            set_at_round=0,
            reason="ok",
            single_stateless=False,
        )
        with pytest.raises(RollbackArgumentError):
            apply_rollback(
                bad_flag,
                prior_state={},
                post_state={},
                applied_at_round=0,
            )

    def test_apply_rollback_rejects_negative_round(self):
        flag = build_disabled_rollback_flag(set_at_round=0)
        with pytest.raises(RollbackArgumentError):
            apply_rollback(
                flag,
                prior_state={},
                post_state={},
                applied_at_round=-1,
            )

    def test_audit_and_flag_are_frozen(self):
        flag = build_disabled_rollback_flag(set_at_round=0)
        audit = apply_rollback(
            flag, prior_state={}, post_state={}, applied_at_round=0
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            flag.disabled = False  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            audit.applied_at_round = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3. Policy version / hash recorded per run
# ---------------------------------------------------------------------------


class TestPolicyVersionHashRecorder:
    def test_records_are_written_in_order(self):
        recorder = PolicyVersionHashRecorder()
        recorder.write_policy_version_hash(
            RunId("run-A"), "v0.1.0", ArtifactHash("a" * 64), at_round=0
        )
        recorder.write_policy_version_hash(
            RunId("run-A"), "v0.1.1", ArtifactHash("b" * 64), at_round=1
        )
        recorder.write_policy_version_hash(
            RunId("run-B"), "v0.2.0", ArtifactHash("c" * 64), at_round=0
        )
        run_a = recorder.get_records_for_run(RunId("run-A"))
        assert len(run_a) == 2
        assert run_a[0][1] == "v0.1.0"
        assert run_a[1][1] == "v0.1.1"
        assert recorder.total_records == 3

    def test_run_scoping_isolates_records(self):
        recorder = PolicyVersionHashRecorder()
        recorder.write_policy_version_hash(
            RunId("run-X"), "v1", ArtifactHash("d" * 64), at_round=0
        )
        recorder.write_policy_version_hash(
            RunId("run-Y"), "v1", ArtifactHash("e" * 64), at_round=0
        )
        run_x = recorder.get_records_for_run(RunId("run-X"))
        run_y = recorder.get_records_for_run(RunId("run-Y"))
        assert len(run_x) == 1
        assert len(run_y) == 1
        assert str(run_x[0][0]) == "run-X"
        assert str(run_y[0][0]) == "run-Y"

    def test_recorder_rejects_empty_run_id(self):
        recorder = PolicyVersionHashRecorder()
        with pytest.raises(PromotionArgumentError):
            recorder.write_policy_version_hash(
                RunId(""), "v1", ArtifactHash("a" * 64), at_round=0
            )

    def test_recorder_rejects_empty_policy_version(self):
        recorder = PolicyVersionHashRecorder()
        with pytest.raises(PromotionArgumentError):
            recorder.write_policy_version_hash(
                RunId("run-A"), "", ArtifactHash("a" * 64), at_round=0
            )

    def test_recorder_rejects_empty_policy_hash(self):
        recorder = PolicyVersionHashRecorder()
        with pytest.raises(PromotionArgumentError):
            recorder.write_policy_version_hash(
                RunId("run-A"), "v1", ArtifactHash(""), at_round=0
            )

    def test_recorder_rejects_negative_round(self):
        recorder = PolicyVersionHashRecorder()
        with pytest.raises(PromotionArgumentError):
            recorder.write_policy_version_hash(
                RunId("run-A"),
                "v1",
                ArtifactHash("a" * 64),
                at_round=-1,
            )

    def test_records_are_immutable_tuples(self):
        recorder = PolicyVersionHashRecorder()
        recorder.write_policy_version_hash(
            RunId("run-A"), "v1", ArtifactHash("a" * 64), at_round=0
        )
        run_a = recorder.get_records_for_run(RunId("run-A"))
        assert isinstance(run_a[0], tuple)
        with pytest.raises((TypeError, AttributeError)):
            run_a[0][1] = "tampered"  # type: ignore[index]

    def test_derive_policy_hash_from_version_is_deterministic(self):
        h1 = derive_policy_hash_from_version(
            RunId("run-A"), "v1", at_round=0
        )
        h2 = derive_policy_hash_from_version(
            RunId("run-A"), "v1", at_round=0
        )
        assert h1 == h2
        # ArtifactHash is a typing.NewType over str; at runtime it is a str.
        assert isinstance(h1, str)
        assert len(str(h1)) == 64


# ---------------------------------------------------------------------------
# 4. Promotion report contains all required fields
# ---------------------------------------------------------------------------


class TestPromotionReport:
    REQUIRED_FIELDS = (
        "policy_version",
        "policy_hash",
        "gain",
        "invalid_samples",
        "cost",
        "failure_modes",
        "calibration_drift",
        "disabled_baseline",
        "evaluation_rounds",
        "claim_gate_decision",
        "generated_at_round",
        "run_id",
    )

    def test_default_report_has_required_fields(self):
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=10,
        )
        assert isinstance(report, PromotionReport)
        for field in self.REQUIRED_FIELDS:
            assert hasattr(report, field), f"missing field: {field}"

    def test_report_gain_and_cost_are_deferred(self):
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=10,
        )
        assert math.isnan(report.gain)
        assert math.isnan(report.cost)
        assert math.isnan(report.gain) == math.isnan(DEFERRED_GAIN)
        assert math.isnan(report.cost) == math.isnan(DEFERRED_COST)

    def test_report_decision_is_defer(self):
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=10,
        )
        assert report.claim_gate_decision == "defer"

    def test_report_failure_modes_carries_deferred_reason(self):
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=10,
        )
        assert DEFERRED_R8_REASON in report.failure_modes

    def test_report_rejects_negative_invalid_samples(self):
        with pytest.raises(PromotionArgumentError):
            build_deferred_promotion_report(
                policy_version="v0.7.2",
                policy_hash=ArtifactHash("a" * 64),
                run_id=RunId("run-A"),
                generated_at_round=10,
                invalid_samples=-1,
            )

    def test_report_rejects_negative_evaluation_rounds(self):
        with pytest.raises(PromotionArgumentError):
            build_deferred_promotion_report(
                policy_version="v0.7.2",
                policy_hash=ArtifactHash("a" * 64),
                run_id=RunId("run-A"),
                generated_at_round=10,
                evaluation_rounds=-1,
            )

    def test_report_rejects_negative_generated_at_round(self):
        with pytest.raises(PromotionArgumentError):
            build_deferred_promotion_report(
                policy_version="v0.7.2",
                policy_hash=ArtifactHash("a" * 64),
                run_id=RunId("run-A"),
                generated_at_round=-1,
            )

    def test_report_rejects_calibration_drift_out_of_range(self):
        with pytest.raises(PromotionArgumentError):
            build_deferred_promotion_report(
                policy_version="v0.7.2",
                policy_hash=ArtifactHash("a" * 64),
                run_id=RunId("run-A"),
                generated_at_round=10,
                calibration_drift=1.5,
            )

    def test_failure_modes_are_deduplicated_and_sorted(self):
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=10,
            failure_modes=("zeta", "alpha", "alpha", "mu"),
        )
        # Deferred reason must be present.
        assert DEFERRED_R8_REASON in report.failure_modes
        # User-supplied entries are deduplicated and sorted.
        user_entries = tuple(
            e for e in report.failure_modes if e != DEFERRED_R8_REASON
        )
        assert list(user_entries) == sorted(set(user_entries))
        # Deferred reason is the first element when present (prepended).
        if DEFERRED_R8_REASON in report.failure_modes:
            assert report.failure_modes[0] == DEFERRED_R8_REASON

    def test_report_is_frozen(self):
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=10,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.policy_version = "v9.9.9"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 5. Rollback when gate not met -> never writes diagnostic proxy or local
#    case as performance conclusion
# ---------------------------------------------------------------------------


class TestRollbackGateNotMet:
    """When the claim gate is not satisfiable the orchestrator must:

    * rollback to the disabled baseline (``disabled=True`` flag), and
    * never write a diagnostic proxy or local case as a performance
      conclusion (the :class:`PromotionReport` carries
      ``claim_gate_decision == 'defer'`` and the deferred-reason
      marker in ``failure_modes``).
    """

    def test_gate_not_satisfied_yields_rollback_flag(self):
        config = _enabled_config(
            required_paired_evidence_count=100  # unattainable
        )
        evidence = _passing_evidence()
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=2
        )
        # Gate not satisfiable -> promotion report must defer and
        # rollback must be available.
        assert evaluation.decision == "defer"
        assert "paired_evidence_count:insufficient" in (
            evaluation.gate_conditions_failed
        )
        # Rollback path is the disabled flag, structurally
        # stateless, applied at the same round.
        flag = build_disabled_rollback_flag(set_at_round=2)
        audit = apply_rollback(
            flag,
            prior_state={"policy": "active", "evidence": evidence},
            post_state={"policy": "disabled", "evidence": evidence},
            applied_at_round=2,
        )
        assert audit.flag.disabled is True
        assert audit.flag.single_stateless is True
        # The promotion report never records diagnostic-proxy /
        # local-case values as performance numbers.
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=2,
        )
        assert math.isnan(report.gain)
        assert math.isnan(report.cost)
        assert report.claim_gate_decision == "defer"
        assert DEFERRED_R8_REASON in report.failure_modes

    def test_diagnostic_proxy_is_not_recorded_as_gain(self):
        """Diagnostic / proxy numbers must NEVER appear as ``gain``."""
        # We confirm that the only legal gain values are the deferred
        # NaN placeholder. Any attempt to assign a number bypasses
        # the frozen dataclass.
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=1,
        )
        assert math.isnan(report.gain)
        # Bypass attempt: the dataclass is frozen, so mutation fails.
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.gain = 0.42  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. Layered metric panel enforces tier separation (no overlapping keys)
# ---------------------------------------------------------------------------


class TestLayeredMetricPanel:
    def test_default_panel_constructs_with_no_overlap(self):
        panel = build_default_layered_metric_panel(
            raw_generation_metrics={"gnina": 0.1, "qed": 0.5},
            adaptive_reflow_metrics={"policy_fraction": 0.3},
            postprocess_assisted_metrics={"sanitized_score": 0.7},
        )
        assert isinstance(panel, LayeredMetricPanel)
        ok, overlapping = enforce_separation(panel)
        assert ok is True
        assert overlapping == ()

    def test_overlapping_keys_rejected_at_construction(self):
        with pytest.raises(LayeredMetricPanelArgumentError):
            build_default_layered_metric_panel(
                raw_generation_metrics={"gnina": 0.1, "qed": 0.5},
                adaptive_reflow_metrics={"gnina": 0.2},
                postprocess_assisted_metrics={"sanitized_score": 0.7},
            )

    def test_enforce_separation_reports_all_overlapping_keys(self):
        # Build a panel with overlapping keys by direct construction
        # then run the validator.
        panel = LayeredMetricPanel(
            raw_generation_metrics={"gnina": 0.1, "qed": 0.5},
            adaptive_reflow_metrics={"gnina": 0.2},
            postprocess_assisted_metrics={"qed": 0.7},
            separation_enforced=True,
        )
        ok, overlapping = enforce_separation(panel)
        assert ok is False
        assert overlapping == ("gnina", "qed")

    def test_separation_enforced_invariant(self):
        with pytest.raises(LayeredMetricPanelArgumentError):
            build_default_layered_metric_panel(
                raw_generation_metrics={"a": 1},
                adaptive_reflow_metrics={"b": 2},
                postprocess_assisted_metrics={"c": 3},
                separation_enforced=False,
            )

    def test_panel_is_frozen(self):
        panel = build_default_layered_metric_panel(
            raw_generation_metrics={"gnina": 0.1},
            adaptive_reflow_metrics={"policy_fraction": 0.3},
            postprocess_assisted_metrics={"sanitized_score": 0.7},
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            panel.raw_generation_metrics = {"x": 1}  # type: ignore[misc]

    def test_tier_labels_literal_set(self):
        assert TIER_LABELS == (
            "raw_generation",
            "adaptive_reflow",
            "postprocess_assisted",
        )
        # Literal alias is exposed and matches TIER_LABELS.
        assert set(TIER_LABELS) == {
            "raw_generation",
            "adaptive_reflow",
            "postprocess_assisted",
        }

    def test_missing_tier_mapping_rejected(self):
        with pytest.raises(LayeredMetricPanelArgumentError):
            build_default_layered_metric_panel(
                raw_generation_metrics=None,  # type: ignore[arg-type]
                adaptive_reflow_metrics={"a": 1},
                postprocess_assisted_metrics={"b": 2},
            )


# ---------------------------------------------------------------------------
# Smoke integration: gate -> rollback -> promotion report pipeline
# ---------------------------------------------------------------------------


class TestStructuralPipeline:
    def test_end_to_end_deferred_promotion_pipeline(self):
        # 1. Build an enabled gate config.
        config = _enabled_config(
            required_contracts_passing=("contract_a",),
            required_paired_evidence_count=1,
            evaluation_window_rounds=1,
            minimum_confidence_interval_coverage=0.5,
        )
        # 2. Evaluate the gate with passing evidence -> defer
        #    (structural, not promote).
        evidence = {
            "contract_a": {"passed": True},
            "paired_evidence_count": 1,
            "confidence_interval_coverage": 0.9,
            "evaluation_window_rounds": 1,
        }
        evaluation = evaluate_claim_gate(
            config, evidence, evaluated_at_round=7
        )
        assert evaluation.decision == "defer"

        # 3. Record the policy version / hash.
        recorder = PolicyVersionHashRecorder()
        recorder.write_policy_version_hash(
            RunId("run-A"),
            "v0.7.2",
            ArtifactHash("a" * 64),
            at_round=7,
        )
        assert recorder.total_records == 1

        # 4. Roll back to the disabled baseline (gate not yet
        #    satisfied at this round because R7 GPU data is missing).
        flag = build_disabled_rollback_flag(set_at_round=7)
        audit = apply_rollback(
            flag,
            prior_state={"active": True},
            post_state={"active": False},
            applied_at_round=7,
        )
        assert audit.flag.single_stateless is True

        # 5. Emit the deferred promotion report.
        report = build_deferred_promotion_report(
            policy_version="v0.7.2",
            policy_hash=ArtifactHash("a" * 64),
            run_id=RunId("run-A"),
            generated_at_round=7,
            invalid_samples=0,
            evaluation_rounds=1,
            disabled_baseline="baseline-v0",
        )
        assert report.claim_gate_decision == "defer"
        assert report.disabled_baseline == "baseline-v0"
        assert math.isnan(report.gain)
        assert math.isnan(report.cost)
        assert DEFERRED_R8_REASON in report.failure_modes
