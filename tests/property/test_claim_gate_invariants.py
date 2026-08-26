"""Property-based invariants for the DTB-R8 claim gate evaluator.

Three hypothesis-driven templates covering the structural decisions of
:func:`adaptive_reflow.eval.claim_gate.evaluate_claim_gate`:

19. ``evidence=None`` -> decision is ``"defer"`` (no promotion path).
20. ``gate_enabled=False`` -> decision is ``"defer"`` (master switch off).
21. All-pass evidence with gate enabled -> decision is still ``"defer"``
    because R7 GPU data is unavailable; the structural promotion logic
    is deferred.

Stdlib-only.
"""
from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings

from adaptive_reflow.eval import (
    ClaimGateArgumentError,
    build_default_claim_gate_config,
    evaluate_claim_gate,
)

from . import st_claim_config, st_claim_evidence

# ---------------------------------------------------------------------------
# 19. evidence=None => decision="defer"
# ---------------------------------------------------------------------------


@given(
    config=st_claim_config(),
    round_value=pytest.mark.parametrize(
        "round_value", [0, 1, 5]
    ) if False else __import__("hypothesis").strategies.integers(min_value=0, max_value=10),
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_claim_gate_defer_when_evidence_is_none(config, round_value: int) -> None:
    """``evidence=None`` forces a ``"defer"`` decision (no promotion path)."""
    evaluation = evaluate_claim_gate(
        config=config,
        evidence=None,
        evaluated_at_round=int(round_value),
    )
    assert evaluation.decision == "defer"
    # The "missing_evidence" / "gate_disabled" marker must appear in the
    # failed conditions tuple so downstream consumers can distinguish
    # "no evidence supplied" from "a specific condition failed".
    assert "missing_evidence" in evaluation.gate_conditions_failed or (
        "gate_disabled" in evaluation.gate_conditions_failed
    )


# ---------------------------------------------------------------------------
# 20. gate_enabled=False => decision="defer"
# ---------------------------------------------------------------------------


@given(
    round_value=__import__("hypothesis").strategies.integers(min_value=0, max_value=10),
    evidence=st_claim_evidence(min_paired=0, max_paired=10),
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_claim_gate_defer_when_gate_disabled(round_value: int, evidence) -> None:
    """A disabled gate is a master switch; the decision is always ``"defer"``."""
    config = build_default_claim_gate_config(
        required_contracts_passing=(),
        required_calibration_artifact_hash=None,
        required_paired_evidence_count=0,
        gate_enabled=False,
        evaluation_window_rounds=0,
        minimum_confidence_interval_coverage=0.0,
    )
    evaluation = evaluate_claim_gate(
        config=config,
        evidence=evidence,
        evaluated_at_round=int(round_value),
    )
    assert evaluation.decision == "defer"
    # The ``"gate_disabled"`` marker must be present in the failed tuple
    # so callers can distinguish "the gate was off" from "evidence was
    # missing or a specific condition failed".
    assert "gate_disabled" in evaluation.gate_conditions_failed
    # Summary must also reflect the disabled master switch.
    assert evaluation.evidence_summary["gate_enabled"] is False


# ---------------------------------------------------------------------------
# 21. All-pass evidence with gate enabled => decision="defer" (until R7)
# ---------------------------------------------------------------------------


@given(round_value=__import__("hypothesis").strategies.integers(min_value=0, max_value=10))
@settings(max_examples=200, suppress_health_check=[HealthCheck.filter_too_much])
def test_claim_gate_all_pass_evidence_still_defers(round_value: int) -> None:
    """All conditions passing still yields ``"defer"`` until R7 GPU data lands.

    The structural evaluator never emits ``"promote"`` or ``"rollback"``
    without R7 evidence. Even when every required contract passes,
    paired evidence is sufficient, CI coverage is sufficient, the
    evaluation window is satisfied, and (when configured) the
    calibration artifact hash matches, the decision must remain
    ``"defer"`` per :data:`DEFERRED_R8_REASON`.
    """
    # We construct an explicit all-pass configuration rather than relying
    # on the property strategy, because the structural test must fix the
    # *passing* configuration precisely to exercise the R7-deferred
    # code path.
    required_contracts = ("contract_a", "contract_b")
    expected_calibration_hash = "deadbeef" * 8
    config = build_default_claim_gate_config(
        required_contracts_passing=required_contracts,
        required_calibration_artifact_hash=expected_calibration_hash,
        required_paired_evidence_count=2,
        gate_enabled=True,
        evaluation_window_rounds=1,
        minimum_confidence_interval_coverage=0.5,
    )
    evidence = {
        "contract_a": {"passed": True, "summary": "ok"},
        "contract_b": {"passed": True, "summary": "ok"},
        "calibration_artifact": {"hash": expected_calibration_hash},
        "paired_evidence_count": 5,
        "confidence_interval_coverage": 0.9,
        "evaluation_window_rounds": 3,
    }
    evaluation = evaluate_claim_gate(
        config=config,
        evidence=evidence,
        evaluated_at_round=int(round_value),
    )
    assert evaluation.decision == "defer"
    # Summary must reference the deferred reason so downstream
    # consumers can see *why* the structural decision is ``"defer"``.
    assert "deferred_reason" in evaluation.evidence_summary
    # And the all-pass surface is observable: every required condition
    # is present in the passed tuple.
    expected_pass_keys = {
        "contract:contract_a",
        "contract:contract_b",
        "calibration_artifact",
        "paired_evidence_count",
        "confidence_interval_coverage",
        "evaluation_window_rounds",
    }
    assert expected_pass_keys.issubset(set(evaluation.gate_conditions_passed))
    # No condition failed.
    assert evaluation.gate_conditions_failed == ()
