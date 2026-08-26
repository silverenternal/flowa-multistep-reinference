"""External metric feedback runner for adaptive reflow inference."""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _write_feedback(round_dir: Path, feedback: Mapping[str, Any]) -> None:
    (round_dir / "feedback.json").write_text(
        json.dumps(dict(feedback), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def finite_float_from(source: Mapping[str, Any], *keys: str) -> float | None:
    """Return the first finite float-like value from a metric payload."""

    for key in keys:
        if key not in source:
            continue
        value = source.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, bool):
            raise ValueError(f"external_metric_feedback:{key}_must_be_finite_float")
        if isinstance(value, (int, float)):
            parsed = float(value)
            if not math.isfinite(parsed):
                raise ValueError(f"external_metric_feedback:{key}_must_be_finite_float")
            return parsed
        if isinstance(value, str):
            try:
                parsed = float(value)
            except ValueError:
                raise ValueError(f"external_metric_feedback:{key}_must_be_finite_float") from None
            if not math.isfinite(parsed):
                raise ValueError(f"external_metric_feedback:{key}_must_be_finite_float")
            return parsed
        raise ValueError(f"external_metric_feedback:{key}_must_be_finite_float")
    return None


def _strict_round_proxy_unit_float(round_proxy: Mapping[str, Any], key: str, *, default: float = 0.0) -> float:
    if key not in round_proxy or round_proxy.get(key) in (None, ""):
        return float(default)
    value = round_proxy.get(key)
    if isinstance(value, bool):
        raise ValueError(f"external_metric_round_proxy:{key}_must_be_unit_float")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"external_metric_round_proxy:{key}_must_be_unit_float") from None
    if not math.isfinite(parsed):
        raise ValueError(f"external_metric_round_proxy:{key}_must_be_finite")
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"external_metric_round_proxy:{key}_must_be_unit_interval")
    return float(parsed)


def _strict_optional_metric_float(value: Any, *, name: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"external_metric_feedback:{name}_must_be_finite_float")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"external_metric_feedback:{name}_must_be_finite_float") from None
    if not math.isfinite(parsed):
        raise ValueError(f"external_metric_feedback:{name}_must_be_finite_float")
    return float(parsed)


def _strict_optional_bool(value: Any, *, name: str, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    raise ValueError(f"external_metric_feedback:{name}_must_be_boolean")


def _strict_current_control_float(
    value: Any,
    *,
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool):
        raise ValueError(f"external_metric_current_control:{name}_must_be_finite_float")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"external_metric_current_control:{name}_must_be_finite_float") from None
    if not math.isfinite(parsed):
        raise ValueError(f"external_metric_current_control:{name}_must_be_finite_float")
    if minimum is not None and parsed < minimum:
        raise ValueError(f"external_metric_current_control:{name}_below_minimum")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"external_metric_current_control:{name}_above_maximum")
    return float(parsed)


def strict_bool_or_none(value: Any) -> bool | None:
    """Parse evaluator booleans without treating arbitrary strings as true."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        if float(value) == 1.0:
            return True
        if float(value) == 0.0:
            return False
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
    return None


def strict_bool(value: Any, *, default: bool = False) -> bool:
    parsed = strict_bool_or_none(value)
    return bool(default) if parsed is None else parsed


def feedback_reason_tokens(value: Any) -> set[str]:
    """Normalize evaluator failure-reason fields from list/CSV/string forms."""

    if value in (None, ""):
        return set()
    if isinstance(value, str):
        normalized = value.replace(",", "|").replace(";", "|")
        return {token.strip() for token in normalized.split("|") if token.strip()}
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        tokens: set[str] = set()
        for item in value:
            tokens.update(feedback_reason_tokens(item))
        return tokens
    return {str(value)}


@dataclass(frozen=True)
class ConditionPolicyParameters:
    """Explicit real-metric policy constants for adaptive ODE reconditioning."""

    gnina_target_score: float = -4.0
    qed_target: float = 0.65
    pose_failure_gap_scale: float = 1.0
    binding_gap_scale: float = 2.5
    druglikeness_gap_scale: float = 0.25
    materialization_priority_weight: float = 1.25
    posebusters_priority_weight: float = 1.15
    gnina_priority_weight: float = 1.05
    qed_priority_weight: float = 1.0
    worsening_trend_bonus: float = 0.20
    max_memory_delta: float = 0.14
    max_charge_memory_delta: float = 0.32
    max_pair_memory_delta: float = 0.42
    max_temperature_delta: float = 0.12
    max_bond_threshold_delta: float = 0.10
    max_property_delta: float = 0.24
    uncertainty_half_trust: float = 0.35
    proxy_fallback_allowed: bool = False


def _strict_policy_float(source: Mapping[str, Any], key: str, default: float) -> float:
    if key not in source:
        return float(default)
    value = source[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"external_metric_condition_policy:{key}_must_be_numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"external_metric_condition_policy:{key}_must_be_finite")
    return parsed


def _strict_policy_bool(source: Mapping[str, Any], key: str, default: bool) -> bool:
    if key not in source:
        return bool(default)
    value = source[key]
    if not isinstance(value, bool):
        raise ValueError(f"external_metric_condition_policy:{key}_must_be_boolean")
    return value


def _strict_unit_property_value(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field}_must_be_numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{field}_must_be_finite")
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"{field}_must_be_unit_interval")
    return parsed


def _strict_property_preference(
    value: Any,
    *,
    allowed_property_names: set[str],
    field: str,
) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field}_must_be_mapping")
    parsed: dict[str, float] = {}
    for key, raw in value.items():
        name = str(key)
        if name not in allowed_property_names:
            raise ValueError(f"{field}_unknown_property:{name}")
        parsed[name] = _strict_unit_property_value(raw, field=f"{field}:{name}")
    return parsed


def condition_policy_parameters_from_feedback(
    external_feedback: Mapping[str, Any],
    *,
    gnina_target_score: float,
    qed_target: float,
) -> ConditionPolicyParameters:
    """Load optional per-run policy constants without hiding defaults in branches."""

    raw_policy = external_feedback.get("condition_policy_parameters") or external_feedback.get("condition_policy")
    if raw_policy is None:
        policy = {}
    elif isinstance(raw_policy, Mapping):
        policy = raw_policy
    else:
        raise ValueError("external_metric_condition_policy_must_be_mapping")
    defaults = ConditionPolicyParameters(gnina_target_score=float(gnina_target_score), qed_target=float(qed_target))
    return ConditionPolicyParameters(
        gnina_target_score=_strict_policy_float(policy, "gnina_target_score", defaults.gnina_target_score),
        qed_target=_strict_policy_float(policy, "qed_target", defaults.qed_target),
        pose_failure_gap_scale=max(
            1.0e-6, _strict_policy_float(policy, "pose_failure_gap_scale", defaults.pose_failure_gap_scale)
        ),
        binding_gap_scale=max(1.0e-6, _strict_policy_float(policy, "binding_gap_scale", defaults.binding_gap_scale)),
        druglikeness_gap_scale=max(
            1.0e-6, _strict_policy_float(policy, "druglikeness_gap_scale", defaults.druglikeness_gap_scale)
        ),
        materialization_priority_weight=_strict_policy_float(
            policy, "materialization_priority_weight", defaults.materialization_priority_weight
        ),
        posebusters_priority_weight=_strict_policy_float(
            policy, "posebusters_priority_weight", defaults.posebusters_priority_weight
        ),
        gnina_priority_weight=_strict_policy_float(policy, "gnina_priority_weight", defaults.gnina_priority_weight),
        qed_priority_weight=_strict_policy_float(policy, "qed_priority_weight", defaults.qed_priority_weight),
        worsening_trend_bonus=max(
            0.0, _strict_policy_float(policy, "worsening_trend_bonus", defaults.worsening_trend_bonus)
        ),
        max_memory_delta=max(0.0, _strict_policy_float(policy, "max_memory_delta", defaults.max_memory_delta)),
        max_charge_memory_delta=max(
            0.0,
            _strict_policy_float(policy, "max_charge_memory_delta", defaults.max_charge_memory_delta),
        ),
        max_pair_memory_delta=max(
            0.0,
            _strict_policy_float(policy, "max_pair_memory_delta", defaults.max_pair_memory_delta),
        ),
        max_temperature_delta=max(
            0.0,
            _strict_policy_float(policy, "max_temperature_delta", defaults.max_temperature_delta),
        ),
        max_bond_threshold_delta=max(
            0.0,
            _strict_policy_float(policy, "max_bond_threshold_delta", defaults.max_bond_threshold_delta),
        ),
        max_property_delta=max(0.0, _strict_policy_float(policy, "max_property_delta", defaults.max_property_delta)),
        uncertainty_half_trust=max(
            1.0e-6,
            _strict_policy_float(policy, "uncertainty_half_trust", defaults.uncertainty_half_trust),
        ),
        proxy_fallback_allowed=_strict_policy_bool(policy, "proxy_fallback_allowed", defaults.proxy_fallback_allowed),
    )


def _metric_uncertainty(external_feedback: Mapping[str, Any], metric: str) -> float | None:
    for key in (
        f"{metric}_uncertainty",
        f"{metric}_std",
        f"{metric}_stderr",
        "metric_uncertainty",
        "evaluator_uncertainty",
    ):
        value = finite_float_from(external_feedback, key)
        if value is not None:
            return max(0.0, float(value))
    return None


def _metric_trust(uncertainty: float | None, *, half_trust: float) -> float:
    if uncertainty is None:
        return 1.0
    return max(0.15, min(1.0, float(half_trust) / (float(half_trust) + float(uncertainty))))


def _bounded_update(before: float, proposed: float, *, max_delta: float) -> float:
    delta = max(-float(max_delta), min(float(max_delta), float(proposed) - float(before)))
    return float(before) + delta


def adaptive_reflow_external_metric_controls(
    external_feedback: Mapping[str, Any],
    round_proxy: Mapping[str, Any],
    *,
    round_memory_fraction: float,
    round_charge_memory_fraction: float,
    round_pair_memory_fraction: float,
    round_temperature: float,
    round_bond_threshold: float,
    base_property_preference: Mapping[str, float] | Any | None,
    property_names: Sequence[str],
    previous_external_feedback: Mapping[str, Any] | None = None,
    best_gnina_score: float | None = None,
    best_qed_value: float | None = None,
    best_posebusters_pass: bool = False,
    gnina_target_score: float = -4.0,
    qed_target: float = 0.65,
) -> dict[str, Any]:
    """Plan the next reflow round from real evaluator feedback.

    This owner is deliberately independent of ``pocket_model_core``.  The core
    module passes its current property vocabulary into this helper so checkpoint
    compatibility exports stay facade-only while evaluator-guided ODE condition
    policy lives with adaptive reflow inference mechanisms.
    """

    if not isinstance(external_feedback, Mapping) or not external_feedback:
        raise ValueError("external_metric_controller_v1 requires non-empty external feedback")
    allowed_property_names = {str(name) for name in property_names}
    policy_parameters = condition_policy_parameters_from_feedback(
        external_feedback,
        gnina_target_score=gnina_target_score,
        qed_target=qed_target,
    )
    gnina_target_score = float(policy_parameters.gnina_target_score)
    qed_target = float(policy_parameters.qed_target)
    best_gnina_score = _strict_optional_metric_float(best_gnina_score, name="best_gnina_score")
    best_qed_value = _strict_optional_metric_float(best_qed_value, name="best_qed_value")
    best_posebusters_pass = _strict_optional_bool(best_posebusters_pass, name="best_posebusters_pass")
    round_memory_fraction = _strict_current_control_float(
        round_memory_fraction,
        name="round_memory_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    round_charge_memory_fraction = _strict_current_control_float(
        round_charge_memory_fraction,
        name="round_charge_memory_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    round_pair_memory_fraction = _strict_current_control_float(
        round_pair_memory_fraction,
        name="round_pair_memory_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    round_temperature = _strict_current_control_float(round_temperature, name="round_temperature", minimum=0.0)
    round_bond_threshold = _strict_current_control_float(
        round_bond_threshold,
        name="round_bond_threshold",
        minimum=0.0,
        maximum=1.0,
    )

    def finite_float(*keys: str) -> float | None:
        return finite_float_from(external_feedback, *keys)

    proxy_materialized = _strict_round_proxy_unit_float(round_proxy, "materialized")
    pair_reliability = _strict_round_proxy_unit_float(round_proxy, "pair_reliability")
    decoded_graph_available = _strict_round_proxy_unit_float(round_proxy, "decoded_graph_available") >= 1.0
    materialized = strict_bool(external_feedback.get("materialized"), default=proxy_materialized >= 1.0)
    materialization_error = str(
        external_feedback.get("materialization_error") or external_feedback.get("model_materialization_error") or ""
    )
    coordinate_materialization_failed = bool(
        decoded_graph_available
        and (
            "semantic_graph_etkdg_embedding_failed" in materialization_error
            or "raw_coordinate" in materialization_error
            or "forcefield" in materialization_error
        )
    )
    pose_value = external_feedback.get("posebusters_pass", external_feedback.get("all_checks_pass"))
    parsed_pose = strict_bool_or_none(pose_value)
    posebusters_known = parsed_pose is not None
    posebusters_good = bool(parsed_pose) if posebusters_known else False
    gnina_score = finite_float("gnina_score", "cross_gnina_score", "label_gnina_affinity")
    gnina_known = gnina_score is not None
    gnina_good = bool(gnina_known and float(gnina_score) <= float(gnina_target_score))
    qed_value = finite_float("qed", "QED")
    qed_good = bool(qed_value is not None and float(qed_value) >= float(qed_target))
    pose_failure_fraction = finite_float("posebusters_failure_fraction", "failure_fraction")
    failure_reasons = set()
    for reason_key in ("posebusters_failure_reasons", "failure_reasons", "claim_grade_blockers"):
        failure_reasons.update(feedback_reason_tokens(external_feedback.get(reason_key)))
    geometry_failure_terms = {
        "bond_lengths",
        "bond_angles",
        "internal_steric_clash",
        "internal_energy",
        "aromatic_ring_flatness",
        "double_bond_flatness",
        "protein-ligand_maximum_distance",
        "minimum_distance_to_protein",
        "volume_overlap_with_protein",
        "posebusters_failed",
    }
    if pose_failure_fraction is None:
        if posebusters_known and not posebusters_good:
            pose_failure_fraction = max(0.15, min(1.0, float(len(failure_reasons) or 1) / 8.0))
        elif posebusters_good:
            pose_failure_fraction = 0.0
    pose_pressure = max(0.0, min(1.0, float(pose_failure_fraction or 0.0) / policy_parameters.pose_failure_gap_scale))
    pose_quality = 1.0 - max(0.0, min(1.0, float(pose_failure_fraction or 0.0)))
    gnina_gap = None if gnina_score is None else max(0.0, float(gnina_score) - float(gnina_target_score))
    binding_pressure = (
        0.0 if gnina_gap is None else max(0.0, min(1.0, float(gnina_gap) / policy_parameters.binding_gap_scale))
    )
    qed_gap = None if qed_value is None else max(0.0, float(qed_target) - float(qed_value))
    drug_pressure = (
        0.0
        if qed_gap is None
        else max(0.0, min(1.0, float(qed_gap) / policy_parameters.druglikeness_gap_scale))
    )
    previous_gnina = (
        finite_float_from(previous_external_feedback, "gnina_score", "cross_gnina_score", "label_gnina_affinity")
        if isinstance(previous_external_feedback, Mapping)
        else None
    )
    previous_qed = (
        finite_float_from(previous_external_feedback, "qed", "QED")
        if isinstance(previous_external_feedback, Mapping)
        else None
    )
    gnina_worsened = bool(
        gnina_score is not None and previous_gnina is not None and float(gnina_score) > float(previous_gnina) + 0.05
    )
    qed_worsened = bool(
        qed_value is not None and previous_qed is not None and float(qed_value) + 0.01 < float(previous_qed)
    )
    best_gnina_good = bool(best_gnina_score is not None and best_gnina_score <= float(gnina_target_score))
    best_qed_good = bool(best_qed_value is not None and best_qed_value >= float(qed_target))
    binding_preserve_required = bool(gnina_good or best_gnina_good)
    druglikeness_preserve_required = bool(qed_good or best_qed_good)
    geometry_bad = bool((not posebusters_good and posebusters_known) or (failure_reasons & geometry_failure_terms))
    hard_geometry_failure_terms = {
        "bond_lengths",
        "bond_angles",
        "internal_steric_clash",
        "internal_energy",
        "aromatic_ring_flatness",
        "double_bond_flatness",
        "protein-ligand_maximum_distance",
        "minimum_distance_to_protein",
        "volume_overlap_with_protein",
    }
    severe_geometry_bad = bool(
        geometry_bad
        and (
            float(pose_failure_fraction or 0.0) >= 0.12
            or bool(failure_reasons & hard_geometry_failure_terms)
        )
    )
    minor_pose_failure_binding_eligible = bool(
        geometry_bad
        and not severe_geometry_bad
        and pose_quality >= 0.90
        and gnina_known
        and not gnina_good
    )
    base_condition = _strict_property_preference(
        base_property_preference,
        allowed_property_names=allowed_property_names,
        field="external_metric_base_property_preference",
    )
    base_delta = dict(base_condition)

    if not materialized and coordinate_materialization_failed:
        selected = "materialization_geometry"
        reason = "real feedback reports coordinate materialization failure after a decoded graph was available"
        next_memory = max(0.10, min(0.18, float(round_memory_fraction) + 0.02))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.55)
        next_pair_memory = max(min(float(round_pair_memory_fraction), 0.58), 0.46)
        next_temperature = max(0.92, min(1.02, float(round_temperature) - 0.02))
        next_bond_threshold = max(0.50, min(0.56, float(round_bond_threshold)))
        base_delta.update(
            {
                "qed": 0.64,
                "ertl_sa": 0.20,
                "mw": 0.38,
                "rotors": max(0.16, 0.22 - 0.04 * pose_pressure),
                "rings": max(0.22, 0.28 - 0.04 * pose_pressure),
            }
        )
        freeze_charge = True
        freeze_pair = False
        local_pair_freeze = bool(pair_reliability >= 0.70)
        if binding_preserve_required:
            next_memory = max(float(next_memory), min(0.32, max(float(round_memory_fraction), 0.26)))
            next_pair_memory = max(float(next_pair_memory), 0.58)
            next_temperature = min(float(next_temperature), 0.96)
            local_pair_freeze = bool(local_pair_freeze or pair_reliability >= 0.62)
    elif not materialized:
        selected = "materialization_topology"
        reason = "real feedback reports materialization failure"
        next_memory = 0.08
        next_charge_memory = max(float(round_charge_memory_fraction), 0.45)
        next_pair_memory = max(float(round_pair_memory_fraction), 0.62)
        next_temperature = max(0.98, min(1.10, float(round_temperature) + 0.04 + 0.02 * pose_pressure))
        next_bond_threshold = min(0.48, max(0.44, float(round_bond_threshold) - 0.04 - 0.02 * pose_pressure))
        base_delta.update(
            {
                "qed": 0.62,
                "ertl_sa": 0.24,
                "mw": 0.40,
                "rotors": max(0.16, 0.24 - 0.06 * pose_pressure),
                "rings": max(0.22, 0.30 - 0.06 * pose_pressure),
            }
        )
        freeze_charge = False
        freeze_pair = False
        local_pair_freeze = False
        if binding_preserve_required:
            next_memory = max(float(next_memory), min(0.24, max(float(round_memory_fraction), 0.18)))
            next_pair_memory = max(float(next_pair_memory), 0.66)
            next_temperature = min(float(next_temperature), 1.02)
            freeze_charge = True
    elif geometry_bad and not minor_pose_failure_binding_eligible:
        selected = "posebusters_real_geometry"
        reason = "real PoseBusters feedback failed before binding/drug-likeness polishing"
        next_memory = max(0.16, min(0.26, float(round_memory_fraction) + 0.03 + 0.03 * (1.0 - pose_pressure)))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.65)
        next_pair_memory = max(min(float(round_pair_memory_fraction), 0.60), 0.46 + 0.08 * (1.0 - pose_pressure))
        next_temperature = max(0.88, min(1.00, float(round_temperature) - 0.02 - 0.04 * pose_pressure))
        next_bond_threshold = max(0.50, min(0.58, float(round_bond_threshold) + 0.02 * pose_pressure))
        base_delta.update(
            {
                "qed": 0.66,
                "ertl_sa": max(0.16, 0.22 - 0.06 * pose_pressure),
                "rotors": max(0.14, 0.22 - 0.08 * pose_pressure),
                "rings": max(0.22, 0.30 - 0.08 * pose_pressure),
            }
        )
        freeze_charge = True
        freeze_pair = False
        local_pair_freeze = bool(pair_reliability >= 0.70)
        if binding_preserve_required:
            next_memory = max(float(next_memory), min(0.38, max(float(round_memory_fraction), 0.32)))
            next_pair_memory = max(float(next_pair_memory), 0.64)
            next_temperature = min(float(next_temperature), 0.94)
            local_pair_freeze = bool(local_pair_freeze or pair_reliability >= 0.60)
        if druglikeness_preserve_required:
            base_delta["qed"] = max(float(base_delta.get("qed", 0.0)), 0.68)
            base_delta["mw"] = min(float(base_delta.get("mw", 0.42)), 0.42)
            base_delta["rotors"] = min(float(base_delta.get("rotors", 0.22)), 0.20)
    elif gnina_known and not gnina_good:
        selected = "gnina_real_binding"
        reason = (
            "real GNINA score is weaker than the target after structural gates"
            if not minor_pose_failure_binding_eligible
            else "real GNINA score is weak and PoseBusters failure is minor enough for binding-preserving polishing"
        )
        next_memory = max(0.24, min(0.40, float(round_memory_fraction) + 0.05 + 0.07 * binding_pressure))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.72)
        next_pair_memory = max(float(round_pair_memory_fraction), 0.62 + 0.10 * binding_pressure)
        next_temperature = max(0.86, min(0.98, float(round_temperature) - 0.03 - 0.04 * binding_pressure))
        next_bond_threshold = max(
            0.52 if minor_pose_failure_binding_eligible else 0.50,
            min(0.58, float(round_bond_threshold)),
        )
        base_delta.update(
            {
                "qed": 0.68,
                "logp": min(0.62, 0.50 + 0.08 * binding_pressure),
                "tpsa": 0.50,
                "hba": min(0.64, 0.54 + 0.08 * binding_pressure),
                "rings": min(0.44, 0.34 + 0.08 * binding_pressure),
            }
        )
        freeze_charge = True
        freeze_pair = False
        local_pair_freeze = True
        if minor_pose_failure_binding_eligible:
            next_memory = max(float(next_memory), min(0.36, max(float(round_memory_fraction), 0.30)))
            next_pair_memory = max(float(next_pair_memory), 0.68)
            base_delta["ertl_sa"] = max(0.18, min(float(base_delta.get("ertl_sa", 0.22)), 0.22))
            base_delta["rotors"] = max(0.16, min(float(base_delta.get("rotors", 0.22)), 0.22))
    elif qed_value is not None and not qed_good:
        selected = "qed_real_druglikeness"
        reason = "real QED is below target after structure and binding gates"
        next_memory = max(0.20, min(0.34, float(round_memory_fraction) + 0.04 + 0.05 * drug_pressure))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.70)
        next_pair_memory = max(float(round_pair_memory_fraction), 0.62)
        next_temperature = max(0.86, min(0.98, float(round_temperature) - 0.03 - 0.04 * drug_pressure))
        next_bond_threshold = max(0.50, min(0.56, float(round_bond_threshold)))
        base_delta.update(
            {
                "qed": min(0.78, 0.68 + 0.08 * drug_pressure),
                "ertl_sa": max(0.16, 0.22 - 0.06 * drug_pressure),
                "mw": max(0.34, 0.42 - 0.06 * drug_pressure),
                "rotors": max(0.14, 0.22 - 0.06 * drug_pressure),
                "rings": max(0.26, 0.36 - 0.06 * drug_pressure),
            }
        )
        freeze_charge = True
        freeze_pair = False
        local_pair_freeze = True
    else:
        selected = "real_metric_preserve"
        reason = "real feedback satisfies available structural and score targets; preserve improved channels"
        next_memory = max(0.24, min(0.34, float(round_memory_fraction) + 0.04))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.78)
        next_pair_memory = max(float(round_pair_memory_fraction), 0.70)
        next_temperature = max(0.86, min(0.96, float(round_temperature) - 0.05))
        next_bond_threshold = max(0.52, min(0.58, float(round_bond_threshold)))
        base_delta.update({"qed": 0.70, "logp": 0.52, "tpsa": 0.50, "mw": 0.42, "hba": 0.56})
        freeze_charge = True
        freeze_pair = False
        local_pair_freeze = True

    metric_uncertainty = {
        "materialization": _metric_uncertainty(external_feedback, "materialization"),
        "posebusters": _metric_uncertainty(external_feedback, "posebusters"),
        "gnina": _metric_uncertainty(external_feedback, "gnina"),
        "qed": _metric_uncertainty(external_feedback, "qed"),
    }
    metric_trust = {
        key: _metric_trust(value, half_trust=policy_parameters.uncertainty_half_trust)
        for key, value in metric_uncertainty.items()
    }
    policy_delta_limits = {
        "memory_fraction": float(policy_parameters.max_memory_delta),
        "charge_memory_fraction": float(policy_parameters.max_charge_memory_delta),
        "pair_memory_fraction": float(policy_parameters.max_pair_memory_delta),
        "temperature": float(policy_parameters.max_temperature_delta),
        "bond_threshold": float(policy_parameters.max_bond_threshold_delta),
        "property": float(policy_parameters.max_property_delta),
    }
    next_memory = _bounded_update(
        float(round_memory_fraction),
        float(next_memory),
        max_delta=policy_parameters.max_memory_delta,
    )
    next_charge_memory = _bounded_update(
        float(round_charge_memory_fraction),
        float(next_charge_memory),
        max_delta=policy_parameters.max_charge_memory_delta,
    )
    next_pair_memory = _bounded_update(
        float(round_pair_memory_fraction),
        float(next_pair_memory),
        max_delta=policy_parameters.max_pair_memory_delta,
    )
    next_temperature = _bounded_update(
        float(round_temperature),
        float(next_temperature),
        max_delta=policy_parameters.max_temperature_delta,
    )
    next_bond_threshold = _bounded_update(
        float(round_bond_threshold),
        float(next_bond_threshold),
        max_delta=policy_parameters.max_bond_threshold_delta,
    )
    property_delta = {}
    for key, value in _strict_property_preference(
        base_delta,
        allowed_property_names=allowed_property_names,
        field="external_metric_property_preference_delta",
    ).items():
        property_delta[key] = max(
            0.0,
            min(
                1.0,
                _bounded_update(
                    float(base_condition.get(key, 0.0)),
                    value,
                    max_delta=policy_parameters.max_property_delta,
                ),
            ),
        )
    scalar_condition_update = {
        "memory_fraction": {"before": float(round_memory_fraction), "after": float(next_memory)},
        "charge_memory_fraction": {
            "before": float(round_charge_memory_fraction),
            "after": float(next_charge_memory),
        },
        "pair_memory_fraction": {"before": float(round_pair_memory_fraction), "after": float(next_pair_memory)},
        "temperature": {"before": float(round_temperature), "after": float(next_temperature)},
        "bond_threshold": {"before": float(round_bond_threshold), "after": float(next_bond_threshold)},
    }
    for payload in scalar_condition_update.values():
        payload["delta"] = float(payload["after"] - payload["before"])
    property_condition_update = {
        str(key): {
            "before": float(base_condition.get(key, 0.0)),
            "after": float(value),
            "delta": float(value) - float(base_condition.get(key, 0.0)),
        }
        for key, value in property_delta.items()
    }
    condition_vector_before = {
        "memory_fraction": float(round_memory_fraction),
        "charge_memory_fraction": float(round_charge_memory_fraction),
        "pair_memory_fraction": float(round_pair_memory_fraction),
        "temperature": float(round_temperature),
        "bond_threshold": float(round_bond_threshold),
        "properties": {
            str(key): float(value)
            for key, value in base_condition.items()
            if key in allowed_property_names and math.isfinite(float(value))
        },
    }
    condition_vector_after = {
        "memory_fraction": float(next_memory),
        "charge_memory_fraction": float(next_charge_memory),
        "pair_memory_fraction": float(next_pair_memory),
        "temperature": float(next_temperature),
        "bond_threshold": float(next_bond_threshold),
        "properties": property_delta,
    }
    metric_delta = {
        "gnina_score": (
            None
            if gnina_score is None or previous_gnina is None
            else float(gnina_score) - float(previous_gnina)
        ),
        "qed": None if qed_value is None or previous_qed is None else float(qed_value) - float(previous_qed),
        "posebusters_pass": (
            None
            if not isinstance(previous_external_feedback, Mapping)
            else int(bool(posebusters_good))
            - int(strict_bool(previous_external_feedback.get("posebusters_pass"), default=False))
        ),
        "materialized": (
            None
            if not isinstance(previous_external_feedback, Mapping)
            else int(bool(materialized))
            - int(strict_bool(previous_external_feedback.get("materialized"), default=False))
        ),
    }
    metric_difficulty_order = sorted(
        [
            {
                "metric": "materialization",
                "pressure": 0.0 if materialized else 1.0,
                "trend_delta": metric_delta["materialized"],
                "priority_weight": float(policy_parameters.materialization_priority_weight),
                "metric_trust": metric_trust["materialization"],
                "difficulty_score": float(
                    (0.0 if materialized else 1.0)
                    * policy_parameters.materialization_priority_weight
                    * metric_trust["materialization"]
                    + (
                        policy_parameters.worsening_trend_bonus
                        if metric_delta["materialized"] is not None and float(metric_delta["materialized"]) < 0.0
                        else 0.0
                    )
                ),
            },
            {
                "metric": "posebusters",
                "pressure": pose_pressure,
                "trend_delta": metric_delta["posebusters_pass"],
                "priority_weight": float(policy_parameters.posebusters_priority_weight),
                "metric_trust": metric_trust["posebusters"],
                "difficulty_score": float(
                    pose_pressure * policy_parameters.posebusters_priority_weight * metric_trust["posebusters"]
                    + (
                        policy_parameters.worsening_trend_bonus
                        if (
                            metric_delta["posebusters_pass"] is not None
                            and float(metric_delta["posebusters_pass"]) < 0.0
                        )
                        else 0.0
                    )
                ),
            },
            {
                "metric": "gnina",
                "pressure": binding_pressure,
                "trend_delta": metric_delta["gnina_score"],
                "priority_weight": float(policy_parameters.gnina_priority_weight),
                "metric_trust": metric_trust["gnina"],
                "difficulty_score": float(
                    binding_pressure * policy_parameters.gnina_priority_weight * metric_trust["gnina"]
                    + (policy_parameters.worsening_trend_bonus if gnina_worsened else 0.0)
                ),
            },
            {
                "metric": "qed",
                "pressure": drug_pressure,
                "trend_delta": metric_delta["qed"],
                "priority_weight": float(policy_parameters.qed_priority_weight),
                "metric_trust": metric_trust["qed"],
                "difficulty_score": float(
                    drug_pressure * policy_parameters.qed_priority_weight * metric_trust["qed"]
                    + (policy_parameters.worsening_trend_bonus if qed_worsened else 0.0)
                ),
            },
        ],
        key=lambda item: float(item["difficulty_score"]),
        reverse=True,
    )
    expected_tradeoff = {
        "schema_version": "adaptive_reflow_expected_tradeoff_v1",
        "primary_metric": selected,
        "metric_difficulty_order": metric_difficulty_order,
        "metric_conflict_matrix": {
            "materialization_topology": ["gnina_can_temporarily_worsen", "qed_can_temporarily_worsen"],
            "posebusters_real_geometry": ["gnina_can_worsen_if_contact_shell_moves"],
            "gnina_real_binding": [
                "posebusters_can_worsen_without_geometry_freeze",
                "qed_can_worsen_via_logp_pressure",
            ],
            "qed_real_druglikeness": ["gnina_can_worsen_if_hydrophobic_contacts_removed"],
        },
        "preserve_controls": {
            "freeze_charge_state": bool(freeze_charge),
            "freeze_pair_chemical_state": bool(freeze_pair),
            "local_pair_freeze_gate_pass": bool(local_pair_freeze),
        },
        "expected_risk": (
            "topology_exploration_can_reduce_binding_temporarily"
            if selected in {"materialization_topology", "materialization_geometry"}
            else "metric_polishing_should_preserve_materialized_structure"
        ),
    }
    metric_to_condition_map = [
        {
            "metric": "materialization",
            "pressure": 0.0 if materialized else 1.0,
            "condition_channels": ["bond_threshold", "temperature", "pair_memory_fraction", "ertl_sa", "rings"],
        },
        {
            "metric": "posebusters",
            "pressure": pose_pressure,
            "condition_channels": ["temperature", "bond_threshold", "rotors", "rings", "ertl_sa"],
        },
        {
            "metric": "gnina",
            "pressure": binding_pressure,
            "condition_channels": ["memory_fraction", "pair_memory_fraction", "logp", "hba", "rings"],
        },
        {
            "metric": "qed",
            "pressure": drug_pressure,
            "condition_channels": ["qed", "ertl_sa", "mw", "rotors", "temperature"],
        },
    ]
    decision = {
        "schema_version": "adaptive_reflow_external_metric_decision_v1",
        "selected_metric_priority": selected,
        "selected_priority_reason": reason,
        "external_feedback": dict(external_feedback),
        "round_proxy": dict(round_proxy),
        "gnina_score": gnina_score,
        "gnina_target_score": float(gnina_target_score),
        "gnina_good": bool(gnina_good),
        "posebusters_good": bool(posebusters_good),
        "posebusters_known": bool(posebusters_known),
        "qed": qed_value,
        "qed_target": float(qed_target),
        "qed_good": bool(qed_good),
        "metric_gaps": {
            "gnina_gap": gnina_gap,
            "qed_gap": qed_gap,
            "posebusters_failure_fraction": pose_failure_fraction,
            "pose_quality": pose_quality,
            "severe_geometry_bad": severe_geometry_bad,
            "minor_pose_failure_binding_eligible": minor_pose_failure_binding_eligible,
            "pose_pressure": pose_pressure,
            "binding_pressure": binding_pressure,
            "drug_pressure": drug_pressure,
        },
        "decoded_graph_available": decoded_graph_available,
        "materialization_error": materialization_error,
        "coordinate_materialization_failed": coordinate_materialization_failed,
        "metric_trend": {
            "previous_gnina_score": previous_gnina,
            "best_gnina_score": best_gnina_score,
            "best_gnina_good": bool(best_gnina_good),
            "binding_preserve_required": bool(binding_preserve_required),
            "gnina_worsened_from_previous": gnina_worsened,
            "previous_qed": previous_qed,
            "best_qed": best_qed_value,
            "best_qed_good": bool(best_qed_good),
            "druglikeness_preserve_required": bool(druglikeness_preserve_required),
            "qed_worsened_from_previous": qed_worsened,
            "best_posebusters_pass": best_posebusters_pass,
        },
        "materialized": bool(materialized),
        "failure_reasons": sorted(failure_reasons),
        "condition_vector_before": condition_vector_before,
        "condition_vector_after": condition_vector_after,
        "metric_delta": metric_delta,
        "metric_uncertainty": metric_uncertainty,
        "metric_trust": metric_trust,
        "metric_difficulty_order": metric_difficulty_order,
        "metric_to_condition_map": metric_to_condition_map,
        "condition_policy_parameters": asdict(policy_parameters),
        "policy_delta_limits": policy_delta_limits,
        "proxy_fallback_allowed": bool(policy_parameters.proxy_fallback_allowed),
        "expected_tradeoff": expected_tradeoff,
        "actual_tradeoff_from_previous_round": metric_delta,
        "ode_condition_update": {
            "schema_version": "real_metric_gap_to_ode_condition_update_v1",
            "selected_metric_priority": selected,
            "condition_vector_before": condition_vector_before,
            "condition_vector_after": condition_vector_after,
            "metric_delta": metric_delta,
            "metric_uncertainty": metric_uncertainty,
            "metric_trust": metric_trust,
            "metric_difficulty_order": metric_difficulty_order,
            "condition_policy_parameters": asdict(policy_parameters),
            "policy_delta_limits": policy_delta_limits,
            "scalar_controls": scalar_condition_update,
            "property_controls": property_condition_update,
            "freeze_controls": {
                "freeze_charge_state": bool(freeze_charge),
                "freeze_pair_chemical_state": bool(freeze_pair),
                "local_pair_freeze_gate_pass": bool(local_pair_freeze),
            },
            "best_metric_preserve_gates": {
                "binding_preserve_required": bool(binding_preserve_required),
                "druglikeness_preserve_required": bool(druglikeness_preserve_required),
            },
        },
        "controls": {
            "memory_fraction": next_memory,
            "charge_memory_fraction": next_charge_memory,
            "pair_memory_fraction": next_pair_memory,
            "temperature": next_temperature,
            "bond_threshold": next_bond_threshold,
            "freeze_charge_state": bool(freeze_charge),
            "freeze_pair_chemical_state": bool(freeze_pair),
            "local_pair_freeze_gate_pass": bool(local_pair_freeze),
        },
        "property_preference_delta": property_delta,
        "uses_external_posebusters_or_gnina": True,
        "uses_native_ligand_or_teacher": False,
        "controller_mode": "evaluator_guided_inference",
    }
    return {
        "schema_version": "adaptive_reflow_external_metric_controls_v1",
        "selected_metric_priority": selected,
        "memory_fraction": next_memory,
        "charge_memory_fraction": next_charge_memory,
        "pair_memory_fraction": next_pair_memory,
        "temperature": next_temperature,
        "bond_threshold": next_bond_threshold,
        "freeze_charge_state": bool(freeze_charge),
        "freeze_pair_chemical_state": bool(freeze_pair),
        "gnina_preserving_channel_memory_gate_pass": bool(
            selected not in {"materialization_topology", "materialization_geometry"}
        ),
        "local_pair_freeze_gate_pass": bool(local_pair_freeze),
        "local_pair_freeze_min_probability": 0.66,
        "property_preference_delta": property_delta,
        "condition_policy_parameters": asdict(policy_parameters),
        "policy_delta_limits": policy_delta_limits,
        "metric_uncertainty": metric_uncertainty,
        "metric_trust": metric_trust,
        "metric_difficulty_order": metric_difficulty_order,
        "expected_tradeoff": expected_tradeoff,
        "external_metric_decision": decision,
        "best_metric_preserve_gates": {
            "binding_preserve_required": bool(binding_preserve_required),
            "druglikeness_preserve_required": bool(druglikeness_preserve_required),
        },
    }


def run_external_reflow_metric_feedback(
    sample: Any,
    *,
    candidate_id: str,
    target: Mapping[str, Any],
    receptor_path: Path,
    output_dir: Path,
    round_index: int,
    geometry_materialization: str,
    bond_threshold_hint: float,
    repo_root: Path,
    mol_from_sample_fn: Any,
    chem_module: Any,
    qed_module: Any,
    pocket_coords: Any | None = None,
    pocket_symbols: Sequence[str] | None = None,
    pose_projection_fn: Any | None = None,
    apply_metric_pose_projection: bool = True,
    python_executable: str = sys.executable,
    subprocess_run_fn: Any = subprocess.run,
    perf_counter_fn: Any = time.perf_counter,
    environ: Mapping[str, str] = os.environ,
) -> dict[str, Any]:
    """Materialize one reflow round and collect real evaluator feedback."""

    round_dir = output_dir / "external_metric_reflow" / str(candidate_id) / f"round_{int(round_index):02d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    feedback: dict[str, Any] = {
        "schema_version": "external_metric_reflow_feedback_v1",
        "candidate_id": str(candidate_id),
        "round_index": int(round_index),
        "uses_external_posebusters_or_gnina": True,
        "uses_native_ligand_or_teacher": False,
    }
    try:
        mol, edge_count = mol_from_sample_fn(
            sample,
            threshold=float(bond_threshold_hint),
            name=f"{candidate_id}_external_metric_round_{int(round_index):02d}",
            geometry_materialization=geometry_materialization,
        )
    except Exception as exc:
        feedback.update(
            {
                "materialized": False,
                "materialization_error": f"{type(exc).__name__}:{exc}",
            }
        )
        _write_feedback(round_dir, feedback)
        return feedback

    if mol is None:
        feedback.update({"materialized": False, "materialization_error": "materialized_mol_missing"})
        _write_feedback(round_dir, feedback)
        return feedback

    feedback.update({"materialized": True, "materialized_edge_count": int(edge_count)})
    pose_projection_applied = False
    pose_projection_error = ""
    if apply_metric_pose_projection and pose_projection_fn is not None and pocket_coords is not None and pocket_symbols:
        try:
            ligand_symbols = list(getattr(sample, "predicted_symbols", ()) or [])
            placement_diag = pose_projection_fn(
                mol,
                pocket_coords,
                list(pocket_symbols),
                ligand_symbols,
                rigid_place=True,
                apply_clash_projection=False,
            )
            clash_diag = pose_projection_fn(
                mol,
                pocket_coords,
                list(pocket_symbols),
                ligand_symbols,
                rigid_place=False,
                apply_clash_projection=True,
            )
            feedback["metric_pose_projection"] = {
                "schema_version": "external_metric_feedback_pose_projection_v1",
                "applied": True,
                "placement": dict(placement_diag or {}),
                "clash_projection": dict(clash_diag or {}),
                "native_ligand_or_teacher_used": False,
            }
            pose_projection_applied = True
        except Exception as exc:
            pose_projection_error = f"{type(exc).__name__}:{exc}"
            feedback["metric_pose_projection"] = {
                "schema_version": "external_metric_feedback_pose_projection_v1",
                "applied": False,
                "error": pose_projection_error,
                "native_ligand_or_teacher_used": False,
            }
    else:
        feedback["metric_pose_projection"] = {
            "schema_version": "external_metric_feedback_pose_projection_v1",
            "applied": False,
            "reason": "projection_inputs_unavailable_or_disabled",
            "native_ligand_or_teacher_used": False,
        }
    feedback["metric_pose_projection_applied"] = bool(pose_projection_applied)
    feedback["metric_pose_projection_error"] = pose_projection_error
    mol.SetProp("candidate_id", str(candidate_id))
    mol.SetProp("target_id", str(target.get("target_id") or target.get("public_target_id") or ""))
    if qed_module is not None:
        try:
            feedback["qed"] = float(qed_module.qed(mol))
        except Exception as exc:
            feedback["qed_error"] = f"{type(exc).__name__}:{exc}"

    sdf_path = round_dir / "candidate.sdf"
    writer = chem_module.SDWriter(str(sdf_path))
    writer.write(mol)
    writer.close()

    target_id = str(target.get("target_id") or target.get("public_target_id") or "")
    pocket_candidate_id = str(target.get("pocket_candidate_id") or "primary")
    denominator_id = str(target.get("denominator_id") or "external_metric_reflow")
    records_json = round_dir / "records.json"
    records = [
        {
            "target_id": target_id,
            "pocket_candidate_id": pocket_candidate_id,
            "candidate_id": str(candidate_id),
            "attempt_id": str(candidate_id),
            "denominator_id": denominator_id,
            "endpoint_accepted": True,
            "sanitized": True,
            "status": "success",
            "failure_reason": "",
        }
    ]
    records_json.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_csv = round_dir / "manifest.csv"
    manifest_fields = sorted(set(target.keys()) | {"target_id", "pocket_candidate_id", "pocket_path", "denominator_id"})
    manifest_row = dict(target)
    manifest_row["target_id"] = target_id
    manifest_row["pocket_candidate_id"] = pocket_candidate_id
    manifest_row["pocket_path"] = str(receptor_path)
    manifest_row["denominator_id"] = denominator_id
    with manifest_csv.open("w", newline="", encoding="utf-8") as handle:
        writer_csv = csv.DictWriter(handle, fieldnames=manifest_fields, extrasaction="ignore")
        writer_csv.writeheader()
        writer_csv.writerow(manifest_row)

    gnina_input = round_dir / "gnina_input.json"
    gnina_output = round_dir / "gnina_score_only.json"
    gnina_input.write_text(
        json.dumps(
            [
                {
                    "candidate_id": str(candidate_id),
                    "target_id": target_id,
                    "source_pocket_path": str(receptor_path),
                    "ligand_sdf_path": str(sdf_path),
                    "ligand_sdf_record_index": 1,
                    "endpoint_accepted": True,
                }
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    gnina_started = perf_counter_fn()
    gnina_completed = subprocess_run_fn(
        [
            python_executable,
            "tools/vina_score_backend.py",
            str(gnina_input),
            str(gnina_output),
            "--vina-workers",
            "1",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        timeout=float(environ.get("EXTERNAL_METRIC_REFLOW_GNINA_TIMEOUT", "360")),
    )
    feedback["gnina_wall_seconds"] = float(perf_counter_fn() - gnina_started)
    feedback["gnina_returncode"] = int(gnina_completed.returncode)
    if gnina_completed.returncode == 0 and gnina_output.is_file():
        payload = json.loads(gnina_output.read_text(encoding="utf-8"))
        rows = payload.get("candidate_metrics") or []
        metrics = dict((rows[0] or {}).get("metrics") or {}) if rows else {}
        score = metrics.get("gnina_affinity_kcal_mol", metrics.get("vina_score"))
        if isinstance(score, (int, float)) and math.isfinite(float(score)):
            feedback["gnina_score"] = float(score)
        feedback["gnina_metrics"] = metrics
    else:
        feedback["gnina_error"] = (
            gnina_completed.stderr[-1000:] or gnina_completed.stdout[-1000:] or "gnina_backend_failed"
        )

    posebusters_python = Path(
        environ.get("POSEBUSTERS_PYTHON")
        or environ.get("FLOWA_P0_POSEBUSTERS_PYTHON")
        or str(repo_root / ".eval_envs" / "posebusters311" / "bin" / "python")
    )
    posebusters_dir = round_dir / "posebusters"
    if posebusters_python.is_file():
        pb_started = perf_counter_fn()
        pb_completed = subprocess_run_fn(
            [
                str(posebusters_python),
                "scripts/evaluate_denovo_posebusters_panel.py",
                "--records-json",
                str(records_json),
                "--candidates-sdf",
                str(sdf_path),
                "--manifest-csv",
                str(manifest_csv),
                "--output-dir",
                str(posebusters_dir),
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=float(environ.get("EXTERNAL_METRIC_REFLOW_POSEBUSTERS_TIMEOUT", "360")),
        )
        feedback["posebusters_wall_seconds"] = float(perf_counter_fn() - pb_started)
        feedback["posebusters_returncode"] = int(pb_completed.returncode)
        pb_csv = posebusters_dir / "posebusters_frozen_denominator.csv"
        if pb_completed.returncode == 0 and pb_csv.is_file():
            with pb_csv.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            row = rows[0] if rows else {}
            from pocket_modules.scoring_evaluation.pose_validity.posebusters_feedback import (
                posebusters_teacher_fields_from_row,
            )

            feedback.update(posebusters_teacher_fields_from_row(row))
        else:
            feedback["posebusters_error"] = (
                pb_completed.stderr[-1000:] or pb_completed.stdout[-1000:] or "posebusters_failed"
            )
    else:
        feedback["posebusters_error"] = f"posebusters_python_missing:{posebusters_python}"

    _write_feedback(round_dir, feedback)
    return feedback
