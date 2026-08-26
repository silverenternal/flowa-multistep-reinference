"""One-shot generator for the ``tests/golden`` JSON matrices.

This script imports the canonical implementations from
``adaptive_reflow`` and writes a curated set of test cases to
``tests/golden/<subject>/case_NNN.json`` for the following subjects:

* ``bounded_merge``        — :func:`adaptive_reflow.frame.bounded_merge`
* ``channel_rule``         — :func:`adaptive_reflow.frame.compute_channel_decision`
* ``claim_gate``           — :func:`adaptive_reflow.eval.evaluate_claim_gate`
* ``synthetic_evaluator``  — :class:`adaptive_reflow.eval.synthetic_oracle.SyntheticEvaluator`

The generated JSON files are the *source of truth* for property-test
replay (``tests/property/test_golden_replay.py``). They are
deliberately written as plain JSON so they can be diffed and reviewed
in isolation from the implementations.

Usage::

    PYTHONPATH=. python tools/generate_golden.py
    PYTHONPATH=. python tools/generate_golden.py --synthetic-evaluator
    PYTHONPATH=. python tools/generate_golden.py --only synthetic_evaluator

The ``--synthetic-evaluator`` flag (or the ``--only`` selector
``synthetic_evaluator``) restricts generation to the
``synthetic_evaluator`` subject so the closed-form CPU oracle can be
regenerated in isolation. The default invocation generates every
subject; the script is idempotent: re-running it overwrites all
selected golden files deterministically.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Canonical imports
# ---------------------------------------------------------------------------
#
# Import order matters: importing ``adaptive_reflow.molecular.bundle`` first
# fully populates ``sys.modules['adaptive_reflow.contracts'].RoundResultBundle``
# (via the lazy ``__getattr__`` in ``contracts/__init__.py``) before
# ``contracts/__init__.py`` itself runs the eager import chain that ends
# up triggering the ``contracts`` <-> ``molecular`` cycle. Doing the
# molecular import first breaks the cycle.

from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    BundleId,
    ChannelName,
    ChannelRuleInputs,
    ChannelTransferEvidence,
    ConditionDigest,
    FactorValue,
    FrameSpec,
    MechanismId,
    ProvenanceChain,
    RunId,
    SampleId,
    ShapeSpec,
    TraceDigest,
    empty_provenance,
    hash_artifact,
    make_default_phase_state,
)
from adaptive_reflow.eval import (  # noqa: E402
    ClaimGateEvaluation,
    build_default_claim_gate_config,
    evaluate_claim_gate,
)
from adaptive_reflow.eval.synthetic_oracle import (  # noqa: E402
    SYNTHETIC_AUDIT_REASON,
    SyntheticEvaluator,
)
from adaptive_reflow.frame import (  # noqa: E402
    bounded_merge,
    compute_channel_decision,
)
from adaptive_reflow.molecular.bundle import (  # noqa: E402
    RoundResultBundle,
)
from adaptive_reflow.universal.adapter import (  # noqa: E402
    AdapterCapabilities,
)
from adaptive_reflow.universal.state import (  # noqa: E402
    StateBundle,
    TensorRef,
)

GOLDEN_ROOT = _REPO_ROOT / "tests" / "golden"


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write ``payload`` to ``path`` deterministically (sorted keys, indent=2)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
    # Use a trailing newline so ``git diff`` stays clean.
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def _json_default(value: Any) -> Any:
    """Custom encoder hook: dataclasses -> dict, NaN/inf -> explicit strings.

    The replay test normalises NaN tokens back to ``float('nan')``; the
    golden JSON records them as the literal string ``"NaN"`` so the file
    round-trips through ``json.loads`` on a strict parser if needed.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _json_default(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_default(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_default(v) for v in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    # NewType aliases fall through to their underlying type. If the
    # underlying type is already JSON-friendly, ``json.dumps`` will
    # serialise it; otherwise we surface a clear error.
    return value


# ===========================================================================
# bounded_merge cases
# ===========================================================================


def _bm_cases() -> list[dict[str, Any]]:
    """Build the bounded_merge golden cases.

    Covers the canonical behaviour and the documented adversarial
    configurations: clamped up, clamped down, asymmetric delta caps,
    empty interval, exact-zero / exact-one envelope edges.
    """
    cases: list[dict[str, Any]] = []

    def add(name: str, *, prev, dynamic, cap, floor, up, down) -> None:
        cases.append(
            {
                "name": name,
                "inputs": {
                    "prev": prev,
                    "dynamic": dynamic,
                    "cap": cap,
                    "floor": floor,
                    "delta_cap_up": up,
                    "delta_cap_down": down,
                },
                "expected": bounded_merge(
                    prev=prev,
                    dynamic=dynamic,
                    cap=cap,
                    floor=floor,
                    delta_cap_up=up,
                    delta_cap_down=down,
                ),
            }
        )

    # ---- happy path: prev == dynamic, no clamp needed ----
    add("baseline_match_zero", prev=0.0, dynamic=0.0, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("baseline_match_mid", prev=0.5, dynamic=0.5, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("baseline_match_one", prev=1.0, dynamic=1.0, cap=1.0, floor=0.0, up=0.5, down=0.5)

    # ---- symmetric increase / decrease around the floor ----
    add("increase_within_delta_cap", prev=0.2, dynamic=0.7, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("decrease_within_delta_cap", prev=0.8, dynamic=0.2, cap=1.0, floor=0.0, up=0.5, down=0.5)

    # ---- delta caps hit on both sides ----
    add("increase_capped_at_up_delta", prev=0.0, dynamic=1.0, cap=1.0, floor=0.0, up=0.3, down=0.5)
    add("decrease_capped_at_down_delta", prev=1.0, dynamic=0.0, cap=1.0, floor=0.0, up=0.5, down=0.3)

    # ---- floor / cap clamping of the dynamic value ----
    add("dynamic_above_cap_clamps_to_cap", prev=0.5, dynamic=2.0, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("dynamic_below_floor_clamps_to_floor", prev=0.5, dynamic=-1.0, cap=1.0, floor=0.0, up=0.5, down=0.5)

    # ---- non-trivial floor ----
    add("floor_protects_decrease", prev=0.4, dynamic=0.0, cap=1.0, floor=0.25, up=0.5, down=0.5)
    add("floor_protects_dynamic_target", prev=0.5, dynamic=0.1, cap=1.0, floor=0.3, up=0.5, down=0.5)
    add("floor_exact_match", prev=0.4, dynamic=0.3, cap=1.0, floor=0.4, up=0.5, down=0.5)

    # ---- non-trivial cap ----
    add("cap_caps_increase", prev=0.5, dynamic=1.0, cap=0.6, floor=0.0, up=1.0, down=0.5)
    add("cap_exact_match", prev=0.6, dynamic=0.5, cap=0.6, floor=0.0, up=1.0, down=0.5)

    # ---- asymmetric delta caps ----
    add("asymmetric_up_tight", prev=0.5, dynamic=0.9, cap=1.0, floor=0.0, up=0.1, down=0.9)
    add("asymmetric_down_tight", prev=0.5, dynamic=0.1, cap=1.0, floor=0.0, up=0.9, down=0.1)

    # ---- zero delta caps ----
    add("zero_delta_up_freeze_increase", prev=0.5, dynamic=0.9, cap=1.0, floor=0.0, up=0.0, down=0.5)
    add("zero_delta_down_freeze_decrease", prev=0.5, dynamic=0.1, cap=1.0, floor=0.0, up=0.5, down=0.0)
    add("zero_delta_both_freeze", prev=0.5, dynamic=0.9, cap=1.0, floor=0.0, up=0.0, down=0.0)

    # ---- asymmetric prev / dynamic extremes ----
    add("prev_zero_dyn_full", prev=0.0, dynamic=1.0, cap=1.0, floor=0.0, up=1.0, down=0.5)
    add("prev_one_dyn_zero", prev=1.0, dynamic=0.0, cap=1.0, floor=0.0, up=0.5, down=1.0)
    add("prev_zero_dyn_zero", prev=0.0, dynamic=0.0, cap=1.0, floor=0.0, up=0.5, down=0.5)

    # ---- mid-range corners ----
    add("mid_to_high", prev=0.4, dynamic=0.7, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("high_to_mid", prev=0.7, dynamic=0.4, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("mid_to_low", prev=0.4, dynamic=0.1, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("low_to_mid", prev=0.1, dynamic=0.4, cap=1.0, floor=0.0, up=0.5, down=0.5)

    # ---- tight envelopes ----
    add("tight_envelope_increase", prev=0.0, dynamic=1.0, cap=0.2, floor=0.0, up=1.0, down=1.0)
    add("tight_envelope_decrease", prev=1.0, dynamic=0.0, cap=1.0, floor=0.8, up=1.0, down=1.0)

    # ---- floor == cap (degenerate envelope; only the single value is reachable) ----
    add("floor_eq_cap_dynamic_within", prev=0.5, dynamic=0.5, cap=0.3, floor=0.3, up=1.0, down=1.0)
    add("floor_eq_cap_dynamic_above", prev=0.5, dynamic=1.0, cap=0.3, floor=0.3, up=1.0, down=1.0)
    add("floor_eq_cap_dynamic_below", prev=0.5, dynamic=0.0, cap=0.3, floor=0.3, up=1.0, down=1.0)

    # ---- degenerate floor == cap (only the single value is reachable) ----
    add("floor_eq_cap_below_zero", prev=0.0, dynamic=0.0, cap=0.0, floor=0.0, up=1.0, down=1.0)
    add("floor_eq_cap_above_one", prev=1.0, dynamic=1.0, cap=1.0, floor=1.0, up=1.0, down=1.0)

    # ---- delta caps at exact boundaries (1.0) ----
    add("delta_caps_one_full_swing_up", prev=0.0, dynamic=1.0, cap=1.0, floor=0.0, up=1.0, down=1.0)
    add("delta_caps_one_full_swing_down", prev=1.0, dynamic=0.0, cap=1.0, floor=0.0, up=1.0, down=1.0)

    # ---- target == prev ----
    add("target_equals_prev", prev=0.4, dynamic=0.4, cap=1.0, floor=0.0, up=0.5, down=0.5)
    add("target_equals_prev_zero", prev=0.0, dynamic=0.0, cap=1.0, floor=0.0, up=0.5, down=0.5)

    # ---- asymmetric floor above zero ----
    add("floor_high_lower_bound", prev=0.6, dynamic=0.0, cap=1.0, floor=0.5, up=0.5, down=0.5)
    add("floor_high_increase_within", prev=0.6, dynamic=0.9, cap=1.0, floor=0.5, up=0.5, down=0.5)

    # ---- adversarial: float roundoff-like values ----
    add("tiny_dynamic_zero_floor", prev=0.0, dynamic=1e-12, cap=1.0, floor=0.0, up=1.0, down=1.0)
    add("near_one_dynamic", prev=0.0, dynamic=1.0 - 1e-12, cap=1.0, floor=0.0, up=1.0, down=1.0)

    return cases


# ===========================================================================
# channel_rule cases
# ===========================================================================


def _make_minimal_bundle(bundle_id: str = "b-1") -> RoundResultBundle:
    """Build a valid :class:`RoundResultBundle` for rule-input construction."""
    return RoundResultBundle(
        bundle_id=BundleId(bundle_id),
        source_round=1,
        round_count=2,
        run_id=RunId("run-1"),
        sample_id=SampleId("sample-1"),
        trace_digest=TraceDigest(hash_artifact({"selector": "unit-test", "n": 1})),
        condition_digest=ConditionDigest(hash_artifact({"condition": "test"})),
        feedback_mode="adaptive_reflow_executable",  # type: ignore[arg-type]
        calibration_artifact_hash=ArtifactHash(hash_artifact({"calib": bundle_id})),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel={"source_round": 1},
        charge_channel=None,
        raw_pair_channel=None,
        projected_pair_channel=None,
        materialization_evidence=None,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec=ShapeSpec({}),
        frame_spec=FrameSpec({}),
        provenance=ProvenanceChain((MechanismId("test.producer"),)),
        created_at_round=1,
        revoked=False,
    )


def _make_evidence(
    bundle_id: str,
    channel: ChannelName,
    *,
    calibration: float = 0.9,
    stability: float = 0.8,
    support: float = 0.7,
    ambiguity: float = 0.1,
    degeneracy: float = 0.1,
    recency: float = 0.95,
    proxy_only: bool = False,
) -> ChannelTransferEvidence:
    """Build a :class:`ChannelTransferEvidence` with the named factor values."""
    return ChannelTransferEvidence(
        bundle_id=BundleId(bundle_id),
        channel=channel,
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=FactorValue(stability),
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=None,
        proxy_only_evidence=proxy_only,
        ambiguity=FactorValue(ambiguity),
        degeneracy_penalty=FactorValue(degeneracy),
        support_coverage=FactorValue(support),
        recency_decay=FactorValue(recency),
        calibration_lower_bound=FactorValue(calibration),
        raw_score=0.5,
        bounded_score=0.5,
        provenance=ProvenanceChain((MechanismId("test.producer"),)),
        validation_errors=(),
    )


def _make_inputs(
    *,
    bundle_id: str = "b-1",
    channel: ChannelName = "coordinate",  # type: ignore[arg-type]
    tail_admissibility: bool = True,
    complement_excluded: bool = False,
    frozen_envelope_manifest_hash: ArtifactHash | None = ArtifactHash("env-hash"),
    finite_prefix_only: bool = True,
    calibration: float = 0.9,
    stability: float = 0.8,
    support: float = 0.7,
    ambiguity: float = 0.1,
    degeneracy: float = 0.1,
    recency: float = 0.95,
    horizon_coverage_proven: bool = True,
    scheduled_cap: float = 0.5,
    mixing_cap: float = 0.5,
    fresh_noise_floor: float = 0.0,
    delta_cap_up: float = 0.5,
    delta_cap_down: float = 0.5,
    proxy_only: bool = False,
) -> ChannelRuleInputs:
    """Build a :class:`ChannelRuleInputs` with the named overrides."""
    bundle = _make_minimal_bundle(bundle_id=bundle_id)
    evidence = _make_evidence(
        bundle_id=bundle_id,
        channel=channel,
        calibration=calibration,
        stability=stability,
        support=support,
        ambiguity=ambiguity,
        degeneracy=degeneracy,
        recency=recency,
        proxy_only=proxy_only,
    )
    phase = make_default_phase_state(
        outer_cycle_id=0,
        round_in_cycle=0,
        horizon_remaining=1,
        horizon_coverage_proven=horizon_coverage_proven,
    )
    return ChannelRuleInputs(
        bundle=bundle,
        evidence=evidence,
        phase_state=phase,
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
        perturbation_stability_lower_bound=FactorValue(stability),
        support_coverage=FactorValue(support),
        ambiguity=FactorValue(ambiguity),
        degeneracy_penalty=FactorValue(degeneracy),
        recency_decay=FactorValue(recency),
        horizon_coverage_proven=horizon_coverage_proven,
        selected_bundle_id=BundleId(bundle_id),
    )


def _channel_rule_cases() -> list[dict[str, Any]]:
    """Build the channel_rule golden cases."""
    cases: list[dict[str, Any]] = []

    def add(name: str, inputs: ChannelRuleInputs) -> None:
        outputs = compute_channel_decision(inputs)
        cases.append(
            {
                "name": name,
                "inputs": _serialise_inputs(inputs),
                "expected": _serialise_decision(outputs.decision),
            }
        )

    # ---- happy path: gate open, decision carries a non-zero beta ----
    add("happy_open_gate", _make_inputs())
    add("happy_open_gate_charge_channel", _make_inputs(channel="charge"))
    add(
        "happy_open_gate_high_evidence",
        _make_inputs(
            calibration=1.0,
            stability=1.0,
            support=1.0,
            ambiguity=0.0,
            degeneracy=0.0,
            recency=1.0,
        ),
    )
    add(
        "happy_open_gate_low_evidence",
        _make_inputs(
            calibration=0.5,
            stability=0.5,
            support=0.5,
            ambiguity=0.5,
            degeneracy=0.5,
            recency=0.5,
        ),
    )

    # ---- blockers fired individually ----
    add(
        "blocker_tail_inadmissible",
        _make_inputs(tail_admissibility=False),
    )
    add(
        "blocker_complement_excluded",
        _make_inputs(complement_excluded=True),
    )
    add(
        "blocker_proxy_only",
        _make_inputs(
            proxy_only=True,
            calibration=0.0,
            stability=0.0,
            support=0.0,
            ambiguity=0.0,
            degeneracy=0.0,
            recency=0.0,
        ),
    )
    add(
        "blocker_horizon_coverage_unproven",
        _make_inputs(horizon_coverage_proven=False),
    )
    add(
        "blocker_finite_prefix_false",
        _make_inputs(finite_prefix_only=False),
    )

    # ---- multiple blockers fired together ----
    add(
        "blocker_combination_all_modes",
        _make_inputs(
            tail_admissibility=False,
            complement_excluded=True,
            finite_prefix_only=False,
            horizon_coverage_proven=False,
        ),
    )

    # ---- envelope hash missing when finite_prefix_only ----
    add(
        "blocker_envelope_hash_missing",
        _make_inputs(frozen_envelope_manifest_hash=None),
    )

    # ---- individual evidence factor failures ----
    add(
        "blocker_factor_out_of_unit_calibration_high",
        _make_inputs(calibration=1.5),
    )
    add(
        "blocker_factor_out_of_unit_calibration_negative",
        _make_inputs(calibration=-0.1),
    )
    add(
        "blocker_factor_out_of_unit_stability_high",
        _make_inputs(stability=2.0),
    )
    add(
        "blocker_factor_out_of_unit_ambiguity_high",
        _make_inputs(ambiguity=1.5),
    )
    add(
        "blocker_factor_out_of_unit_degeneracy_high",
        _make_inputs(degeneracy=1.1),
    )
    add(
        "blocker_factor_out_of_unit_support_low",
        _make_inputs(support=-0.2),
    )
    add(
        "blocker_factor_out_of_unit_recency_high",
        _make_inputs(recency=1.5),
    )

    # ---- cap/floor field failures (still raise blockers, gate stays closed) ----
    add(
        "blocker_cap_field_out_of_unit",
        _make_inputs(scheduled_cap=1.5),
    )
    add(
        "blocker_floor_field_out_of_unit",
        _make_inputs(fresh_noise_floor=-0.1),
    )
    add(
        "blocker_delta_cap_up_field_out_of_unit",
        _make_inputs(delta_cap_up=2.0),
    )

    # ---- edge case: all evidence factors exactly 0.0 ----
    add(
        "open_gate_zero_evidence",
        _make_inputs(
            calibration=0.0,
            stability=0.0,
            support=0.0,
            ambiguity=0.0,
            degeneracy=0.0,
            recency=0.0,
        ),
    )

    # ---- edge case: high ambiguity and degeneracy collapse evidence ----
    add(
        "open_gate_high_ambiguity",
        _make_inputs(ambiguity=1.0),
    )
    add(
        "open_gate_high_degeneracy",
        _make_inputs(degeneracy=1.0),
    )

    # ---- scheduled_cap at extremes ----
    add(
        "open_gate_scheduled_cap_zero",
        _make_inputs(scheduled_cap=0.0),
    )
    add(
        "open_gate_scheduled_cap_one",
        _make_inputs(scheduled_cap=1.0),
    )

    # ---- tight delta caps: rule still admits but bounded_target_fraction clamps ----
    add(
        "open_gate_tight_delta_caps",
        _make_inputs(delta_cap_up=0.01, delta_cap_down=0.01),
    )

    # ---- asymmetric delta caps ----
    add(
        "open_gate_asymmetric_delta_caps",
        _make_inputs(delta_cap_up=0.1, delta_cap_down=0.9),
    )

    # ---- envelope hash None with finite_prefix_only=False (no hash blocker) ----
    add(
        "no_envelope_hash_blocker_when_finite_prefix_false",
        _make_inputs(
            finite_prefix_only=False,
            frozen_envelope_manifest_hash=None,
        ),
    )

    # ---- freshness floor above scheduled cap (still admissible; floor > target) ----
    add(
        "open_gate_high_floor",
        _make_inputs(fresh_noise_floor=0.9, scheduled_cap=0.2),
    )

    # ---- bundle identity preserved on the decision ----
    add(
        "decision_bundle_id_preserved",
        _make_inputs(bundle_id="b-special-id"),
    )

    # ---- channel name preserved on the decision ----
    add(
        "decision_channel_preserved",
        _make_inputs(channel="raw_pair"),
    )

    # ---- zero evidence_score open-gate path ----
    add(
        "open_gate_zero_score",
        _make_inputs(
            calibration=0.0,
            stability=0.0,
            support=0.0,
            ambiguity=1.0,
            degeneracy=1.0,
            recency=0.0,
        ),
    )

    return cases


def _serialise_inputs(inputs: ChannelRuleInputs) -> dict[str, Any]:
    """Convert a :class:`ChannelRuleInputs` to a JSON-friendly dict."""
    return _json_default(dataclasses.asdict(inputs))


def _serialise_decision(decision) -> dict[str, Any]:
    """Convert a :class:`ChannelTransferDecision` to a JSON-friendly dict."""
    return _json_default(dataclasses.asdict(decision))


# ===========================================================================
# claim_gate cases
# ===========================================================================


def _claim_gate_cases() -> list[dict[str, Any]]:
    """Build the claim_gate golden cases."""
    cases: list[dict[str, Any]] = []

    def add(name: str, *, config, evidence, round_=0) -> None:
        outputs = evaluate_claim_gate(config, evidence, evaluated_at_round=round_)
        cases.append(
            {
                "name": name,
                "inputs": {
                    "config": _json_default(dataclasses.asdict(config)),
                    "evidence": _json_default(evidence) if evidence is not None else None,
                    "evaluated_at_round": round_,
                },
                "expected": _serialise_evaluation(outputs),
            }
        )

    # ---- gate disabled (always defer with gate_disabled marker) ----
    add(
        "gate_disabled_with_empty_evidence",
        config=build_default_claim_gate_config(gate_enabled=False),
        evidence=None,
    )
    add(
        "gate_disabled_with_passing_evidence",
        config=build_default_claim_gate_config(gate_enabled=False),
        evidence={
            "contract_a": {"passed": True, "summary": "ok"},
            "paired_evidence_count": 10,
            "confidence_interval_coverage": 0.99,
            "evaluation_window_rounds": 10,
        },
    )

    # ---- gate enabled, empty evidence -> missing_evidence marker ----
    add(
        "gate_enabled_empty_evidence",
        config=build_default_claim_gate_config(gate_enabled=True),
        evidence=None,
        round_=0,
    )
    add(
        "gate_enabled_empty_dict_evidence",
        config=build_default_claim_gate_config(gate_enabled=True),
        evidence={},
        round_=1,
    )

    # ---- gate enabled, all conditions satisfied (still defers structurally) ----
    add(
        "gate_enabled_all_pass",
        config=build_default_claim_gate_config(
            required_contracts_passing=("contract_a", "contract_b"),
            required_paired_evidence_count=2,
            gate_enabled=True,
            evaluation_window_rounds=1,
            minimum_confidence_interval_coverage=0.5,
        ),
        evidence={
            "contract_a": {"passed": True, "summary": "ok"},
            "contract_b": {"passed": True, "summary": "ok"},
            "paired_evidence_count": 5,
            "confidence_interval_coverage": 0.9,
            "evaluation_window_rounds": 3,
        },
        round_=2,
    )

    # ---- contract failures ----
    add(
        "single_contract_failure",
        config=build_default_claim_gate_config(
            required_contracts_passing=("contract_a", "contract_b"),
            gate_enabled=True,
        ),
        evidence={
            "contract_a": {"passed": True, "summary": "ok"},
            "contract_b": {"passed": False, "summary": "fail"},
            "paired_evidence_count": 5,
            "confidence_interval_coverage": 0.9,
            "evaluation_window_rounds": 3,
        },
        round_=3,
    )
    add(
        "missing_contract_evidence",
        config=build_default_claim_gate_config(
            required_contracts_passing=("contract_a", "contract_missing"),
            gate_enabled=True,
        ),
        evidence={
            "contract_a": {"passed": True, "summary": "ok"},
            "paired_evidence_count": 5,
            "confidence_interval_coverage": 0.9,
            "evaluation_window_rounds": 3,
        },
        round_=4,
    )

    # ---- insufficient paired evidence count ----
    add(
        "insufficient_paired_evidence",
        config=build_default_claim_gate_config(
            required_paired_evidence_count=10,
            gate_enabled=True,
        ),
        evidence={
            "paired_evidence_count": 3,
        },
        round_=5,
    )

    # ---- insufficient confidence interval coverage ----
    add(
        "insufficient_ci_coverage",
        config=build_default_claim_gate_config(
            minimum_confidence_interval_coverage=0.95,
            gate_enabled=True,
        ),
        evidence={
            "confidence_interval_coverage": 0.5,
        },
        round_=6,
    )

    # ---- insufficient evaluation window ----
    add(
        "insufficient_window_rounds",
        config=build_default_claim_gate_config(
            evaluation_window_rounds=10,
            gate_enabled=True,
        ),
        evidence={
            "evaluation_window_rounds": 1,
        },
        round_=7,
    )

    # ---- calibration artifact hash matching ----
    add(
        "calibration_artifact_match",
        config=build_default_claim_gate_config(
            required_calibration_artifact_hash=ArtifactHash("a" * 64),
            gate_enabled=True,
        ),
        evidence={
            "calibration_artifact": {"hash": "a" * 64},
        },
        round_=8,
    )
    add(
        "calibration_artifact_mismatch",
        config=build_default_claim_gate_config(
            required_calibration_artifact_hash=ArtifactHash("a" * 64),
            gate_enabled=True,
        ),
        evidence={
            "calibration_artifact": {"hash": "b" * 64},
        },
        round_=9,
    )
    add(
        "calibration_artifact_missing",
        config=build_default_claim_gate_config(
            required_calibration_artifact_hash=ArtifactHash("a" * 64),
            gate_enabled=True,
        ),
        evidence={},
        round_=10,
    )

    # ---- multiple failures stacked ----
    add(
        "all_failures_stacked",
        config=build_default_claim_gate_config(
            required_contracts_passing=("c1", "c2", "c3"),
            required_paired_evidence_count=10,
            evaluation_window_rounds=10,
            minimum_confidence_interval_coverage=0.99,
            gate_enabled=True,
        ),
        evidence={
            "c1": {"passed": True, "summary": "ok"},
            "c2": {"passed": False, "summary": "fail"},
            "paired_evidence_count": 1,
            "confidence_interval_coverage": 0.1,
            "evaluation_window_rounds": 1,
        },
        round_=11,
    )

    # ---- boundary pass: count exactly equal ----
    add(
        "boundary_paired_count_equal",
        config=build_default_claim_gate_config(
            required_paired_evidence_count=5,
            gate_enabled=True,
        ),
        evidence={
            "paired_evidence_count": 5,
        },
        round_=12,
    )

    # ---- boundary pass: CI coverage exactly equal ----
    add(
        "boundary_ci_equal",
        config=build_default_claim_gate_config(
            minimum_confidence_interval_coverage=0.5,
            gate_enabled=True,
        ),
        evidence={
            "confidence_interval_coverage": 0.5,
        },
        round_=13,
    )

    # ---- boundary pass: window exactly equal ----
    add(
        "boundary_window_equal",
        config=build_default_claim_gate_config(
            evaluation_window_rounds=4,
            gate_enabled=True,
        ),
        evidence={
            "evaluation_window_rounds": 4,
        },
        round_=14,
    )

    # ---- zero requirements: empty config still defers (no conditions to pass) ----
    add(
        "zero_requirements_empty_evidence",
        config=build_default_claim_gate_config(gate_enabled=True),
        evidence=None,
        round_=0,
    )

    # ---- contract evidence not a Mapping (treated as missing) ----
    add(
        "contract_evidence_non_mapping",
        config=build_default_claim_gate_config(
            required_contracts_passing=("contract_a",),
            gate_enabled=True,
        ),
        evidence={
            "contract_a": "not-a-mapping",
        },
        round_=15,
    )

    # ---- big round index ----
    add(
        "gate_disabled_large_round",
        config=build_default_claim_gate_config(gate_enabled=False),
        evidence=None,
        round_=10_000,
    )

    return cases


def _serialise_evaluation(eval_: ClaimGateEvaluation) -> dict[str, Any]:
    """Convert a :class:`ClaimGateEvaluation` to a JSON-friendly dict."""
    return _json_default(dataclasses.asdict(eval_))


# ===========================================================================
# synthetic_evaluator cases
# ===========================================================================


#: Canonical synthetic digest prefix used by the golden generator. Eight
#: hex pairs = 8 bytes that feed the little-endian ``uint64`` fold.
_SYNTHETIC_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("coordinate"),
    ChannelName("charge"),
    ChannelName("raw_pair"),
    ChannelName("projected_pair"),
)


def _make_synthetic_state_bundle(
    digest: str,
    *,
    sample_id: str = "sample-synthetic",
) -> StateBundle:
    """Build a minimal valid :class:`StateBundle` for the synthetic oracle."""
    coord_channel = ChannelName("coordinate")
    return StateBundle(
        channels={coord_channel: TensorRef("coord-tensor-ref-golden")},
        masks={},
        batch_id="batch-synthetic",
        sample_id=sample_id,
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.synthetic_oracle_generator",),
        capability_token=AdapterCapabilities(
            has_ode_integration_surface=False,
            has_prior_export=False,
            has_state_export=False,
            has_condition_injection=False,
            has_restart_boundary=False,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=False,
            has_deterministic_seed=True,
            has_materialization_route=False,
            supported_channels=(coord_channel,),
            channel_domains={coord_channel: "continuous"},
        ),
    )


def _synthetic_evaluator_cases() -> list[dict[str, Any]]:
    """Build the ``synthetic_evaluator`` golden cases.

    Covers the canonical closed-form outputs across digest seeds,
    channels, and seeds; the oracle-equals-evaluate byte-for-byte
    contract; the published perturbation deltas; and the published
    stability-range contract (``[0.3, 0.95]``).
    """
    cases: list[dict[str, Any]] = []
    evaluator = SyntheticEvaluator()

    # ---- baseline: fixed digest, fixed seed, one channel ----
    digest = "abcdef0123456789"
    bundle = _make_synthetic_state_bundle(digest)
    oracle = evaluator.oracle(bundle, channel=ChannelName("coordinate"), seed=0)
    cases.append(
        {
            "name": "baseline_coordinate_seed_zero",
            "inputs": {
                "digest": digest,
                "channel": "coordinate",
                "seed": 0,
            },
            "expected": _serialise_oracle(oracle),
        }
    )

    # ---- every canonical channel, fixed seed + digest ----
    for channel_name in _SYNTHETIC_CHANNELS:
        oracle = evaluator.oracle(bundle, channel=channel_name, seed=0)
        cases.append(
            {
                "name": f"channel_{channel_name}_seed_zero",
                "inputs": {
                    "digest": digest,
                    "channel": str(channel_name),
                    "seed": 0,
                },
                "expected": _serialise_oracle(oracle),
            }
        )

    # ---- seed sweep: fixed digest, varying seeds ----
    for seed in (1, 2, 7, 17, 42, 1234, 9999, 0xDEAD):
        oracle = evaluator.oracle(bundle, channel=ChannelName("coordinate"), seed=seed)
        cases.append(
            {
                "name": f"seed_sweep_{seed}",
                "inputs": {
                    "digest": digest,
                    "channel": "coordinate",
                    "seed": int(seed),
                },
                "expected": _serialise_oracle(oracle),
            }
        )

    # ---- digest sweep: fixed seed, varying digests ----
    digests = [
        "0000000000000000",
        "0000000000000001",
        "0100000000000000",
        "ffffffffffffffff",
        "deadbeefcafebabe",
        "feedfacefeedface",
    ]
    for d in digests:
        b = _make_synthetic_state_bundle(d)
        oracle = evaluator.oracle(b, channel=ChannelName("coordinate"), seed=0)
        cases.append(
            {
                "name": f"digest_sweep_{d}",
                "inputs": {
                    "digest": d,
                    "channel": "coordinate",
                    "seed": 0,
                },
                "expected": _serialise_oracle(oracle),
            }
        )

    # ---- perturbation oracle: seed vs seed + 1 differ ----
    oracle_a = evaluator.oracle(bundle, channel=ChannelName("coordinate"), seed=10)
    oracle_b = evaluator.oracle(bundle, channel=ChannelName("coordinate"), seed=11)
    cases.append(
        {
            "name": "perturbation_seed_vs_seed_plus_one",
            "inputs": {
                "digest": digest,
                "channel": "coordinate",
                "seed_a": 10,
                "seed_b": 11,
            },
            "expected": {
                "seed_a": _serialise_oracle(oracle_a),
                "seed_b": _serialise_oracle(oracle_b),
                "raw_score_diff": float(oracle_b["raw_score"] - oracle_a["raw_score"]),
            },
        }
    )

    # ---- stability range contract: [0.3, 0.95] for every digest ----
    cases.append(
        {
            "name": "stability_range_lower_bound",
            "inputs": {
                "digest": "0000000000000000",
                "channel": "coordinate",
                "seed": 0,
            },
            "expected": {
                "perturbation_stability_lower_bound_min": 0.3,
                "perturbation_stability_lower_bound_max": 0.95,
                "value": float(
                    evaluator.oracle(
                        _make_synthetic_state_bundle("0000000000000000"),
                        channel=ChannelName("coordinate"),
                        seed=0,
                    )["perturbation_stability_lower_bound"]
                ),
            },
        }
    )

    # ---- audit-reason contract ----
    cases.append(
        {
            "name": "audit_reason_constant",
            "inputs": {"digest": digest, "channel": "coordinate", "seed": 0},
            "expected": {"audit_reason": SYNTHETIC_AUDIT_REASON},
        }
    )

    # ---- bounded_score == clip(raw_score) ----
    cases.append(
        {
            "name": "bounded_score_equals_clipped_raw_score",
            "inputs": {"digest": digest, "channel": "coordinate", "seed": 0},
            "expected": {
                "bounded_equals_clip": True,
            },
        }
    )

    return cases


def _serialise_oracle(oracle: Mapping[str, float]) -> dict[str, float]:
    """Convert an oracle mapping to a JSON-friendly dict (preserves keys)."""
    return {str(k): float(v) for k, v in oracle.items()}


# ===========================================================================
# Driver
# ===========================================================================


def _write_cases(subject: str, cases: list[dict[str, Any]]) -> None:
    out_dir = GOLDEN_ROOT / subject
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, case in enumerate(cases, start=1):
        path = out_dir / f"case_{idx:03d}.json"
        _write_json(path, case)
    print(f"  -> wrote {len(cases):>3d} cases to {out_dir.relative_to(_REPO_ROOT)}")


def main(argv: tuple[str, ...] | None = None) -> int:
    """Generate the golden matrices; respects ``--synthetic-evaluator`` / ``--only``."""
    parser = argparse.ArgumentParser(
        description="Regenerate the tests/golden JSON matrices deterministically.",
    )
    parser.add_argument(
        "--synthetic-evaluator",
        action="store_true",
        help="Generate only the ``synthetic_evaluator`` subject goldens.",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=("bounded_merge", "channel_rule", "claim_gate", "synthetic_evaluator"),
        help=(
            "Restrict generation to the named subject(s). May be passed "
            "multiple times. Overrides --synthetic-evaluator."
        ),
    )
    args = parser.parse_args(argv)

    selected: set[str]
    if args.only:
        selected = set(args.only)
    elif args.synthetic_evaluator:
        selected = {"synthetic_evaluator"}
    else:
        selected = {"bounded_merge", "channel_rule", "claim_gate", "synthetic_evaluator"}

    print(f"Generating golden matrices under {GOLDEN_ROOT.relative_to(_REPO_ROOT)}")
    print(f"  selected subjects: {sorted(selected)}")

    if "bounded_merge" in selected:
        bm = _bm_cases()
        _write_cases("bounded_merge", bm)
        assert len(bm) >= 40, f"expected >= 40 bounded_merge cases, got {len(bm)}"

    if "channel_rule" in selected:
        cr = _channel_rule_cases()
        _write_cases("channel_rule", cr)
        assert len(cr) >= 30, f"expected >= 30 channel_rule cases, got {len(cr)}"

    if "claim_gate" in selected:
        cg = _claim_gate_cases()
        _write_cases("claim_gate", cg)
        assert len(cg) >= 20, f"expected >= 20 claim_gate cases, got {len(cg)}"

    if "synthetic_evaluator" in selected:
        se = _synthetic_evaluator_cases()
        _write_cases("synthetic_evaluator", se)
        assert len(se) >= 10, f"expected >= 10 synthetic_evaluator cases, got {len(se)}"

    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
