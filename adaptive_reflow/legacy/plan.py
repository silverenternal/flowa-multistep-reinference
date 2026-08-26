"""Typed metric-aware plans for multi-step adaptive reflow inference."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pocket_modules.mechanisms.inference.channel_freeze.schedule import (
    channel_freeze_runtime_plan,
)

from adaptive_reflow.contracts import (
    ArchiveAuditTrail,
    ArchiveQuota,
    RoundResultBundle,
    RunId,
    SampleId,
    TraceDigest,
)
from adaptive_reflow.policy.archive import (
    SameSampleArchive,
)

REINFERENCE_ROUND_PLAN_SCHEMA_VERSION = "adaptive_reflow_metric_aware_round_plan_v2"
REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1 = "adaptive_reflow_metric_aware_round_plan_v1"
REINFERENCE_DIFFICULTY_COMPARISON_SCHEMA_VERSION = "adaptive_reflow_metric_difficulty_order_comparison_v1"
METRIC_FAMILIES = (
    "materialization",
    "posebusters_geometry",
    "binding_gnina",
    "druglikeness_qed_admet",
)
DIFFICULTY_STRATEGIES = (
    "materialization_first",
    "pose_first",
    "qed_first",
    "gnina_first",
    "adaptive_deficit_first",
)
REAL_EVALUATOR_FEEDBACK_KEYS = {
    "gnina_score",
    "cross_gnina_score",
    "label_gnina_affinity",
    "qed",
    "QED",
    "posebusters_pass",
    "all_checks_pass",
    "posebusters_failure_fraction",
    "failure_fraction",
    "posebusters_failure_reasons",
    "failure_reasons",
}
TRUE_METRIC_FEEDBACK_MODES = {
    "inference_external_diagnostic",
    "diagnostic_true_metric_external",
    "formal_training_protocol_authorized",
}

_FIXED_STRATEGY_ORDERS = {
    "materialization_first": (
        "materialization",
        "posebusters_geometry",
        "binding_gnina",
        "druglikeness_qed_admet",
    ),
    "pose_first": (
        "posebusters_geometry",
        "materialization",
        "binding_gnina",
        "druglikeness_qed_admet",
    ),
    "qed_first": (
        "druglikeness_qed_admet",
        "materialization",
        "posebusters_geometry",
        "binding_gnina",
    ),
    "gnina_first": (
        "binding_gnina",
        "posebusters_geometry",
        "materialization",
        "druglikeness_qed_admet",
    ),
}
_INTRINSIC_DIFFICULTY = {
    "materialization": 0.90,
    "posebusters_geometry": 0.86,
    "binding_gnina": 0.78,
    "druglikeness_qed_admet": 0.62,
}
_ACTIVE_EXPERTS = {
    "materialization": (
        "state.pair_chemistry",
        "materialization.graph_materialization",
    ),
    "posebusters_geometry": (
        "conditioning.pocket_spatial_envelope",
        "conditioning.nci_contact",
        "inference.pde_physics_sidecar",
        "inference.physical_descent",
    ),
    "binding_gnina": (
        "conditioning.nci_contact",
        "conditioning.pocket_spatial_envelope",
        "training.property_heads",
        "inference.distilled_guidance",
    ),
    "druglikeness_qed_admet": (
        "conditioning.property_vectors",
        "conditioning.functional_group_tokens",
        "training.property_heads",
    ),
    "bootstrap": ("flowa.mainline_ode",),
}


def _strict_positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a positive integer")
    if int(value) < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _strict_round_index(value: Any, *, rounds: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("round_index must be an integer")
    index = int(value)
    if index < 0 or index >= int(rounds):
        raise ValueError("round_index must be within [0, rounds)")
    return index


@dataclass(frozen=True)
class ReInferenceRoundPlan:
    """One executable adaptive-reflow round plan."""

    round_index: int
    target_metric_family: str
    observed_deficit: float
    difficulty_rank: int
    condition_delta: Mapping[str, Any]
    restart_bias_scale: float
    frozen_channels: tuple[str, ...]
    active_experts: tuple[str, ...]
    rationale: str
    feedback_mode: str
    uses_true_metric_feedback: bool
    difficulty_strategy: str
    restart_distribution_policy: str = "prior_rms_preserving_channel_memory_noise_mix_v2"
    channel_freeze_policy: str = "state_writeback_lock_only_preserve_time_synchronized_conditioning_read_v1"
    cross_attention_policy: str = "frozen_channels_remain_readable_for_clocked_cross_attention_v1"
    ode_update_scope: str = "condition_vector_and_restart_distribution_only"
    schema_version: str = REINFERENCE_ROUND_PLAN_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["condition_delta"] = _json_safe_mapping(self.condition_delta)
        row["frozen_channels"] = list(self.frozen_channels)
        row["active_experts"] = list(self.active_experts)
        return row


def contains_true_metric_feedback(feedback: Mapping[str, Any] | None) -> bool:
    """Return whether evaluator-derived metrics are present in a feedback payload."""

    if not isinstance(feedback, Mapping):
        return False
    return any(key in feedback for key in REAL_EVALUATOR_FEEDBACK_KEYS)


def validate_true_metric_feedback_policy(
    feedback: Mapping[str, Any] | None,
    *,
    feedback_mode: str,
    formal_training_protocol_authorized: bool = False,
) -> None:
    """Fail closed if real evaluator metrics are used outside the inference boundary."""

    if not contains_true_metric_feedback(feedback):
        return
    if bool(formal_training_protocol_authorized):
        return
    if str(feedback_mode) not in TRUE_METRIC_FEEDBACK_MODES:
        raise ValueError(
            "true metric feedback may only drive adaptive reflow in inference-external diagnostic mode "
            "or an explicitly authorized formal training protocol"
        )


def metric_family_from_priority(priority: Any) -> str:
    """Map historical controller priority strings onto coarse metric families."""

    text = str(priority or "").lower()
    if "posebuster" in text or "geometry" in text or "internal_energy" in text:
        return "posebusters_geometry"
    if "gnina" in text or "binding" in text:
        return "binding_gnina"
    if "preserve" in text:
        return "binding_gnina"
    if "qed" in text or "drug" in text or "admet" in text:
        return "druglikeness_qed_admet"
    if "materialization" in text or "topology" in text or "pair" in text:
        return "materialization"
    if text in {"", "none", "off", "bootstrap", "unspecified"}:
        return "bootstrap"
    return text


def metric_family_deficits(
    feedback: Mapping[str, Any] | None = None,
    proxy: Mapping[str, Any] | None = None,
    *,
    gnina_target_score: float = -4.0,
    qed_target: float = 0.65,
) -> dict[str, float]:
    """Convert real/proxy feedback into normalized per-family deficits."""

    fb = dict(feedback or {})
    px = dict(proxy or {})
    materialized = _bool_or_none(fb.get("materialized"))
    if materialized is None:
        materialized = _float_or_none(px.get("materialized")) == 1.0
    materialization_deficit = 0.0 if materialized else 1.0
    pair_reliability = _bounded(_float_or_none(px.get("pair_reliability")), default=0.0)
    geometry_reliability = _bounded(_float_or_none(px.get("geometry_reliability")), default=0.0)
    if materialized:
        materialization_deficit = max(0.0, min(1.0, 1.0 - pair_reliability))

    pose_failure_fraction = _float_or_none(fb.get("posebusters_failure_fraction"))
    if pose_failure_fraction is None:
        pose_failure_fraction = _float_or_none(fb.get("failure_fraction"))
    pose_pass = _bool_or_none(fb.get("posebusters_pass", fb.get("all_checks_pass")))
    if pose_failure_fraction is not None:
        pose_deficit = max(0.0, min(1.0, float(pose_failure_fraction)))
    elif pose_pass is not None:
        pose_deficit = 0.0 if pose_pass else 1.0
    else:
        pose_deficit = max(0.0, min(1.0, 1.0 - geometry_reliability))

    gnina_score = _first_float(fb, "gnina_score", "cross_gnina_score", "label_gnina_affinity")
    gnina_deficit = 0.0 if gnina_score is None else max(0.0, min(1.0, (float(gnina_score) - gnina_target_score) / 3.0))
    qed = _first_float(fb, "qed", "QED")
    qed_deficit = 0.0 if qed is None else max(0.0, min(1.0, (qed_target - float(qed)) / 0.30))
    return {
        "materialization": float(materialization_deficit),
        "posebusters_geometry": float(pose_deficit),
        "binding_gnina": float(gnina_deficit),
        "druglikeness_qed_admet": float(qed_deficit),
    }


def compare_reinference_difficulty_orders(
    deficits: Mapping[str, float],
    *,
    selected_strategy: str = "adaptive_deficit_first",
) -> dict[str, Any]:
    """Return all planned metric-family orders for experiment comparability."""

    if selected_strategy not in DIFFICULTY_STRATEGIES:
        raise ValueError(f"difficulty strategy must be one of {', '.join(DIFFICULTY_STRATEGIES)}")
    normalized = {family: _bounded(deficits.get(family), default=0.0) for family in METRIC_FAMILIES}
    adaptive_order = tuple(
        item[0]
        for item in sorted(
            normalized.items(),
            key=lambda item: (float(item[1]) * _INTRINSIC_DIFFICULTY[item[0]], _INTRINSIC_DIFFICULTY[item[0]]),
            reverse=True,
        )
    )
    orders = {**_FIXED_STRATEGY_ORDERS, "adaptive_deficit_first": adaptive_order}
    return {
        "schema_version": REINFERENCE_DIFFICULTY_COMPARISON_SCHEMA_VERSION,
        "selected_strategy": str(selected_strategy),
        "metric_family_deficits": normalized,
        "intrinsic_difficulty": dict(_INTRINSIC_DIFFICULTY),
        "orders": {key: list(value) for key, value in orders.items()},
        "selected_order": list(orders[selected_strategy]),
    }


def build_reinference_round_plan(
    *,
    round_index: int,
    rounds: int,
    feedback: Mapping[str, Any] | None = None,
    proxy: Mapping[str, Any] | None = None,
    controls: Mapping[str, Any] | None = None,
    current_condition: Mapping[str, Any] | None = None,
    property_preference: Mapping[str, Any] | None = None,
    difficulty_strategy: str = "adaptive_deficit_first",
    feedback_mode: str = "proxy_only",
    formal_training_protocol_authorized: bool = False,
    ledger_row: Mapping[str, Any] | None = None,
    candidate_bundles: Sequence[RoundResultBundle] | None = None,
    evidence_score_by_bundle: Mapping[str, float] | None = None,
    archive_quota: ArchiveQuota | None = None,
    archive_run_id: RunId | None = None,
    archive_sample_id: SampleId | None = None,
    archive_trace_lineage: TraceDigest | None = None,
    archive_checkpoint_id: str | None = None,
    consumed_fresh_noise_mass: float = 0.0,
) -> ReInferenceRoundPlan:
    """Build a typed plan for one round from applied controls and metric feedback.

    DTB-R4: when ``candidate_bundles`` is supplied together with the
    ``archive_*`` lineage anchors and an ``archive_quota``, candidate
    selection runs through :class:`SameSampleArchive` and exactly ONE
    :class:`RoundResultBundle` is selected via deterministic tie-break.
    Unselected candidates are kept for audit only and never influence the
    per-channel rule (which still runs once via the orchestrator on the
    single selected bundle).
    """

    total_rounds = _strict_positive_int(rounds, "rounds")
    index = _strict_round_index(round_index, rounds=total_rounds)
    if index < 0 or index >= total_rounds:
        raise ValueError("round_index must be within [0, rounds)")
    ctrl = dict(controls or {})
    if proxy is None:
        proxy = _proxy_from_controls(ctrl)
    if feedback is None:
        feedback = _feedback_from_controls(ctrl)
    validate_true_metric_feedback_policy(
        feedback,
        feedback_mode=feedback_mode,
        formal_training_protocol_authorized=formal_training_protocol_authorized,
    )
    deficits = metric_family_deficits(feedback, proxy)
    comparison = compare_reinference_difficulty_orders(deficits, selected_strategy=difficulty_strategy)
    selected_family = metric_family_from_priority(ctrl.get("selected_metric_priority"))
    if selected_family == "bootstrap":
        selected_family = comparison["selected_order"][0] if index > 0 or feedback or proxy else "bootstrap"
    observed_deficit = _observed_deficit_from_controls(ctrl, selected_family, deficits)
    selected_order = list(comparison["selected_order"])
    difficulty_rank = (
        selected_order.index(selected_family) if selected_family in selected_order else len(selected_order)
    )

    # DTB-R4: candidate selection through SameSampleArchive. When the
    # caller does not supply the archive anchors we skip selection.
    archive_audit: ArchiveAuditTrail | None = None
    selected_bundle: RoundResultBundle | None = None
    if (
        candidate_bundles is not None
        and archive_quota is not None
        and archive_run_id is not None
        and archive_sample_id is not None
        and archive_trace_lineage is not None
        and archive_checkpoint_id is not None
    ):
        selected_bundle, archive_audit = select_source_bundle_via_archive(
            candidate_bundles=candidate_bundles,
            evidence_score_by_bundle=evidence_score_by_bundle,
            quota=archive_quota,
            run_id=archive_run_id,
            sample_id=archive_sample_id,
            trace_lineage=archive_trace_lineage,
            checkpoint_id=archive_checkpoint_id,
            current_round=index,
            consumed_fresh_noise_mass=consumed_fresh_noise_mass,
        )

    condition_delta = _condition_delta_from_controls(
        controls=ctrl,
        current_condition=current_condition,
        property_preference=property_preference,
        ledger_row=ledger_row,
    )
    restart_bias_scale = _restart_bias_scale(ctrl, current_condition)
    frozen_channels = _frozen_channels_from_controls(ctrl)
    freeze_plan = channel_freeze_runtime_plan(
        round_index=index,
        rounds=total_rounds,
        freeze_charge_state_schedule=(
            [False] * index + [("charge" in frozen_channels)] + [False] * (total_rounds - index - 1)
        ),
        freeze_pair_chemical_state_schedule=[
            False
        ]
        * index
        + [("pair_chemical" in frozen_channels)]
        + [False] * (total_rounds - index - 1),
        metric_priority=selected_family,
    )
    if not freeze_plan["ready"]:
        raise ValueError(f"invalid channel freeze plan: {freeze_plan['blockers']}")
    rationale = _rationale(selected_family, ctrl, observed_deficit, feedback_mode)
    condition_delta["metric_family_deficits"] = dict(comparison["metric_family_deficits"])
    condition_delta["difficulty_order_comparison"] = comparison
    condition_delta["channel_freeze_runtime_plan"] = freeze_plan
    if archive_audit is not None:
        condition_delta["candidate_archive_audit"] = _json_safe_archive_audit(archive_audit)
        if selected_bundle is not None:
            condition_delta["selected_source_bundle_id"] = str(selected_bundle.bundle_id)
            condition_delta["selected_source_bundle_summary"] = _bundle_summary(selected_bundle)
        else:
            condition_delta["selected_source_bundle_id"] = None
    return ReInferenceRoundPlan(
        round_index=index,
        target_metric_family=selected_family,
        observed_deficit=float(observed_deficit),
        difficulty_rank=int(difficulty_rank),
        condition_delta=condition_delta,
        restart_bias_scale=float(restart_bias_scale),
        frozen_channels=tuple(sorted(frozen_channels)),
        active_experts=tuple(_ACTIVE_EXPERTS.get(selected_family, ())),
        rationale=rationale,
        feedback_mode=str(feedback_mode),
        uses_true_metric_feedback=contains_true_metric_feedback(feedback),
        difficulty_strategy=str(difficulty_strategy),
    )


def _condition_delta_from_controls(
    *,
    controls: Mapping[str, Any],
    current_condition: Mapping[str, Any] | None,
    property_preference: Mapping[str, Any] | None,
    ledger_row: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the condition delta and embed the orchestrator ledger row.

    DTB-R5: when the orchestrator has produced a
    ``DynamicRestartTransferLedger`` row for this round, embed it under
    ``ledger_row`` so that every downstream consumer of the plan can
    reproduce the final beta_by_channel from a single ledger row. The
    embedded row is the *only* per-round evidence required by the v3 trace
    reader.
    """

    embedded_ledger = _json_safe_ledger_row(ledger_row)
    decision = controls.get("external_metric_decision")
    if isinstance(decision, Mapping):
        update = decision.get("ode_condition_update")
        if isinstance(update, Mapping):
            return {
                "source": "external_metric_decision.ode_condition_update",
                "scalar_controls": _json_safe_mapping(update.get("scalar_controls") or {}),
                "property_controls": _json_safe_mapping(update.get("property_controls") or {}),
                "freeze_controls": _json_safe_mapping(update.get("freeze_controls") or {}),
                "ledger_row": embedded_ledger,
            }
    decision = controls.get("metric_priority_decision")
    if isinstance(decision, Mapping):
        return {
            "source": "metric_priority_decision",
            "property_controls": _delta_rows(
                dict(property_preference or {}),
                dict(decision.get("property_preference_delta") or controls.get("property_preference_delta") or {}),
            ),
            "scalar_controls": _scalar_delta_rows(controls, current_condition),
            "freeze_controls": _freeze_control_rows(controls),
            "ledger_row": embedded_ledger,
        }
    return {
        "source": "applied_sampler_controls",
        "property_controls": _delta_rows(
            dict(property_preference or {}),
            dict(controls.get("property_preference_delta") or {}),
        ),
        "scalar_controls": _scalar_delta_rows(controls, current_condition),
        "freeze_controls": _freeze_control_rows(controls),
        "ledger_row": embedded_ledger,
    }


def _proxy_from_controls(controls: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Recover the proxy payload embedded by closed-loop controllers."""

    for decision_key, proxy_key in (
        ("metric_priority_decision", "previous_round_proxy"),
        ("external_metric_decision", "round_proxy"),
    ):
        decision = controls.get(decision_key)
        if isinstance(decision, Mapping) and isinstance(decision.get(proxy_key), Mapping):
            return dict(decision[proxy_key])
    confidence = controls.get("proxy_confidence")
    if isinstance(confidence, Mapping):
        return {
            "materialized": confidence.get("materialized"),
            "charge_reliability": confidence.get("charge_reliability"),
            "pair_reliability": confidence.get("pair_reliability"),
            "geometry_reliability": confidence.get("geometry_reliability"),
        }
    return None


def _feedback_from_controls(controls: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Recover real evaluator feedback embedded by external metric decisions."""

    decision = controls.get("external_metric_decision")
    if isinstance(decision, Mapping) and isinstance(decision.get("external_feedback"), Mapping):
        return dict(decision["external_feedback"])
    return None


def _observed_deficit_from_controls(
    controls: Mapping[str, Any],
    selected_family: str,
    deficits: Mapping[str, float],
) -> float:
    if selected_family == "bootstrap":
        return 0.0
    for decision_key in ("external_metric_decision", "metric_priority_decision"):
        decision = controls.get(decision_key)
        if not isinstance(decision, Mapping):
            continue
        metric_gaps = decision.get("metric_gaps")
        if isinstance(metric_gaps, Mapping):
            gap = _deficit_from_metric_gaps(metric_gaps, selected_family)
            if gap is not None:
                return gap
        difficulty_order = decision.get("metric_difficulty_order") or decision.get("difficulty_order")
        if isinstance(difficulty_order, Sequence) and not isinstance(difficulty_order, str | bytes | bytearray):
            for row in difficulty_order:
                if not isinstance(row, Mapping):
                    continue
                row_family = metric_family_from_priority(row.get("metric") or row.get("selected_metric_priority"))
                if row_family != selected_family:
                    continue
                value = _float_or_none(row.get("difficulty_score"))
                if value is None:
                    value = _float_or_none(row.get("pressure"))
                if value is None:
                    value = _float_or_none(row.get("severity"))
                if value is not None:
                    return max(0.0, min(1.0, float(value)))
    return float(deficits.get(selected_family, 0.0))


def _deficit_from_metric_gaps(metric_gaps: Mapping[str, Any], selected_family: str) -> float | None:
    if selected_family == "materialization":
        value = metric_gaps.get("materialized")
        parsed = _bool_or_none(value)
        if parsed is not None:
            return 0.0 if parsed else 1.0
    if selected_family == "posebusters_geometry":
        value = _float_or_none(metric_gaps.get("pose_pressure"))
        if value is None:
            value = _float_or_none(metric_gaps.get("posebusters_failure_fraction"))
        if value is not None:
            return max(0.0, min(1.0, float(value)))
    if selected_family == "binding_gnina":
        value = _float_or_none(metric_gaps.get("binding_pressure"))
        if value is not None:
            return max(0.0, min(1.0, float(value)))
    if selected_family == "druglikeness_qed_admet":
        value = _float_or_none(metric_gaps.get("drug_pressure"))
        if value is not None:
            return max(0.0, min(1.0, float(value)))
    return None


def _scalar_delta_rows(controls: Mapping[str, Any], current_condition: Mapping[str, Any] | None) -> dict[str, Any]:
    current = dict(current_condition or {})
    rows: dict[str, Any] = {}
    for key in ("memory_fraction", "charge_memory_fraction", "pair_memory_fraction", "temperature", "bond_threshold"):
        if controls.get(key) is None:
            continue
        before = _float_or_none(current.get(key))
        after = _float_or_none(controls.get(key))
        if after is None:
            continue
        rows[key] = {
            "before": before,
            "after": after,
            "delta": None if before is None else float(after - before),
        }
    return rows


def _delta_rows(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for key, value in after.items():
        parsed_after = _float_or_none(value)
        if parsed_after is None:
            continue
        parsed_before = _float_or_none(before.get(key))
        rows[str(key)] = {
            "before": parsed_before,
            "after": parsed_after,
            "delta": None if parsed_before is None else float(parsed_after - parsed_before),
        }
    return rows


def _freeze_control_rows(controls: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "freeze_charge_state": _strict_freeze_control_bool(controls, "freeze_charge_state"),
        "freeze_pair_chemical_state": _strict_freeze_control_bool(controls, "freeze_pair_chemical_state"),
        "local_pair_freeze_gate_pass": _strict_freeze_control_bool(controls, "local_pair_freeze_gate_pass"),
    }


def _restart_bias_scale(controls: Mapping[str, Any], current_condition: Mapping[str, Any] | None) -> float:
    value = controls.get("memory_fraction")
    if value is None and current_condition is not None:
        value = current_condition.get("memory_fraction")
    parsed = _float_or_none(value)
    return 0.0 if parsed is None else max(0.0, min(1.0, parsed))


def _frozen_channels_from_controls(controls: Mapping[str, Any]) -> set[str]:
    frozen: set[str] = set()
    if _strict_freeze_control_bool(controls, "freeze_charge_state"):
        frozen.add("charge")
    if _strict_freeze_control_bool(controls, "freeze_pair_chemical_state"):
        frozen.add("pair_chemical")
    if _strict_freeze_control_bool(controls, "local_pair_freeze_gate_pass"):
        frozen.add("pair_chemical_local")
    return frozen


def _strict_freeze_control_bool(controls: Mapping[str, Any], key: str) -> bool:
    if key not in controls or controls.get(key) is None:
        return False
    value = controls.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(float(value)):
        if float(value) == 1.0:
            return True
        if float(value) == 0.0:
            return False
    raise ValueError(f"reinference_plan_{key}_must_be_boolean_or_numeric_0_1")


def _rationale(selected_family: str, controls: Mapping[str, Any], observed_deficit: float, feedback_mode: str) -> str:
    decision = controls.get("external_metric_decision") or controls.get("metric_priority_decision")
    if isinstance(decision, Mapping) and decision.get("selected_priority_reason"):
        return str(decision["selected_priority_reason"])
    if selected_family == "bootstrap":
        return "first round uses the base ODE condition before metric feedback is available"
    return (
        f"{selected_family} selected by metric difficulty policy with deficit "
        f"{float(observed_deficit):.3f} under {feedback_mode}"
    )


def _first_float(source: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _float_or_none(source.get(key))
        if value is not None:
            return value
    return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        return parsed if math.isfinite(parsed) else None
    return None


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        if float(value) == 1.0:
            return True
        if float(value) == 0.0:
            return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no", ""}:
            return False
    return None


def _bounded(value: Any, *, default: float) -> float:
    parsed = _float_or_none(value)
    if parsed is None:
        return float(default)
    return max(0.0, min(1.0, float(parsed)))


def _json_safe_mapping(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_mapping(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe_mapping(item) for item in value]
    parsed = _float_or_none(value)
    if parsed is not None:
        return parsed
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    return str(value)


def _json_safe_ledger_row(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """JSON-safe serialisation of a ``DynamicRestartTransferLedger`` row.

    Used to embed the single per-round ledger row inside
    ``ReInferenceRoundPlan.condition_delta`` for DTB-R5 reproducibility.
    Returns ``None`` when no ledger row was supplied.
    """

    if row is None:
        return None
    if not isinstance(row, Mapping):
        raise TypeError("ledger_row must be a Mapping")
    serialised = _json_safe_mapping(dict(row))
    if not isinstance(serialised, dict):
        raise TypeError("ledger_row serialisation did not yield a dict")
    return serialised


def read_round_plan_v1(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the v1 round plan payload unchanged, after schema validation.

    DTB-R5: keeps the v1 reader alive so downstream consumers that have not
    yet been migrated to the v2 schema can still be exercised. Raises
    ``ValueError`` if the schema name is not v1.
    """

    if not isinstance(payload, Mapping):
        raise TypeError("v1 round plan payload must be a Mapping")
    schema_name = payload.get("schema_version")
    if schema_name != REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1:
        raise ValueError(
            "v1 reader requires schema_version="
            f"{REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1!r}; "
            f"got {schema_name!r}"
        )
    return dict(payload)


# ---------------------------------------------------------------------------
# DTB-R4 candidate selection via SameSampleArchive
# ---------------------------------------------------------------------------


def select_source_bundle_via_archive(
    *,
    candidate_bundles: Sequence[RoundResultBundle],
    evidence_score_by_bundle: Mapping[str, float] | None,
    quota: ArchiveQuota,
    run_id: RunId,
    sample_id: SampleId,
    trace_lineage: TraceDigest,
    checkpoint_id: str,
    current_round: int,
    consumed_fresh_noise_mass: float = 0.0,
) -> tuple[RoundResultBundle | None, ArchiveAuditTrail]:
    """Pick ONE :class:`RoundResultBundle` via :class:`SameSampleArchive`.

    The function:

    * constructs a fresh :class:`SameSampleArchive` scoped to the
      ``(run_id, sample_id, trace_lineage, checkpoint_id)`` tuple;
    * inserts every candidate (dedup by ``bundle_id``), preserving
      evidence scores keyed by ``bundle_id`` when supplied;
    * calls :meth:`SameSampleArchive.select_one_bundle` to deterministically
      pick ONE bundle via lexicographic-by-bundle_id tie-break;
    * returns the selected bundle (or ``None``) alongside the audit trail.

    The per-channel rule MUST only ever see ``selected_bundle``; the
    unselected candidates are kept in the audit trail for audit only.
    Cross-lineage bundles are rejected via
    :class:`CandidateArchiveLineageError`.
    """

    archive = SameSampleArchive(
        quota=quota,
        run_id=run_id,
        sample_id=sample_id,
        trace_lineage=trace_lineage,
        checkpoint_id=checkpoint_id,
    )
    scores: Mapping[str, float] = (
        dict(evidence_score_by_bundle) if evidence_score_by_bundle is not None else {}
    )
    for bundle in candidate_bundles:
        bid = str(bundle.bundle_id)
        archive.add_candidate(
            bundle,
            evidence_score=float(scores.get(bid, 1.0)),
        )
    selected_entry = archive.select_one_bundle(
        current_round=int(current_round),
        consumed_fresh_noise_mass=float(consumed_fresh_noise_mass),
    )
    selected_bundle = selected_entry.bundle if selected_entry is not None else None
    return selected_bundle, archive.audit_trail


def _bundle_summary(bundle: RoundResultBundle) -> dict[str, Any]:
    """Return a JSON-safe summary of the selected bundle for audit."""

    return {
        "bundle_id": str(bundle.bundle_id),
        "source_round": int(bundle.source_round),
        "round_count": int(bundle.round_count),
        "run_id": str(bundle.run_id),
        "sample_id": str(bundle.sample_id),
        "trace_digest": str(bundle.trace_digest),
        "feedback_mode": str(bundle.feedback_mode),
        "update_scope": str(bundle.update_scope),
        "revoked": bool(bundle.revoked),
    }


def _json_safe_archive_audit(audit: ArchiveAuditTrail) -> dict[str, Any]:
    """JSON-safe serialisation of an :class:`ArchiveAuditTrail`."""

    return {
        "selected_bundle_id": (
            None if audit.selected_bundle_id is None else str(audit.selected_bundle_id)
        ),
        "rejected_bundle_ids": [str(b) for b in audit.rejected_bundle_ids],
        "dedup_count": int(audit.dedup_count),
        "total_influence_kept": float(audit.total_influence_kept),
        "archive_size": int(audit.archive_size),
        "fresh_noise_mass_used": float(audit.fresh_noise_mass_used),
        "fresh_noise_floor_required": float(audit.fresh_noise_floor_required),
        "consecutive_reuse_count": int(audit.consecutive_reuse_count),
        "max_consecutive_reuse_rounds": int(audit.max_consecutive_reuse_rounds),
        "current_round": int(audit.current_round),
        "audit_hash": str(audit.audit_hash),
    }


__all__ = [
    "DIFFICULTY_STRATEGIES",
    "METRIC_FAMILIES",
    "REAL_EVALUATOR_FEEDBACK_KEYS",
    "REINFERENCE_DIFFICULTY_COMPARISON_SCHEMA_VERSION",
    "REINFERENCE_ROUND_PLAN_SCHEMA_VERSION",
    "REINFERENCE_ROUND_PLAN_SCHEMA_VERSION_LEGACY_V1",
    "ReInferenceRoundPlan",
    "build_reinference_round_plan",
    "compare_reinference_difficulty_orders",
    "contains_true_metric_feedback",
    "metric_family_deficits",
    "metric_family_from_priority",
    "read_round_plan_v1",
    "select_source_bundle_via_archive",
    "validate_true_metric_feedback_policy",
]
