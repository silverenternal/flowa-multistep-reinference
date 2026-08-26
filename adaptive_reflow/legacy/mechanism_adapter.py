"""MechanismRuntime adapter for adaptive reflow."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from pocket_modules.flowa_core import FlowCondition, FlowDecodeOutput, FlowState
from pocket_modules.mechanism_runtime import MechanismContext, MechanismTrace
from pocket_modules.mechanisms.inference.adaptive_reflow.control_policy import (
    adaptive_reflow_dynamic_property_preference,
    adaptive_reflow_metric_priority_controls,
)
from pocket_modules.mechanisms.inference.adaptive_reflow.external_metric_feedback import (
    adaptive_reflow_external_metric_controls,
    strict_bool_or_none,
)
from pocket_modules.mechanisms.inference.adaptive_reflow.reinference_plan import (
    build_reinference_round_plan,
    contains_true_metric_feedback,
)
from pocket_modules.mechanisms.inference.noise_bias.restart_bias import (
    metric_direction_for_name,
    noise_bias_from_metric_delta,
)


class AdaptiveReflowMechanism:
    mechanism_id = "inference.adaptive_reflow"

    def __init__(self) -> None:
        self._events: list[Mapping[str, Any]] = []
        self._last_feedback: Mapping[str, Any] = {}
        self._services: Mapping[str, Any] = {}

    def prepare(self, context: MechanismContext) -> MechanismTrace:
        self._services = dict(context.services)
        self._events.append({"event": "prepare", "config_keys": sorted(context.config)})
        return self.export_trace()

    def condition_delta(self, state: FlowState, metrics: Mapping[str, Any]) -> FlowCondition:
        feedback = {**dict(self._last_feedback), **dict(metrics)}
        self._events.append({"event": "condition_delta", "metric_keys": sorted(str(key) for key in feedback)})
        property_vector = dict(state.condition.property_vector)
        restart_bias = dict(state.condition.restart_bias)
        freeze_masks = dict(state.condition.freeze_masks)
        controls = feedback.get("adaptive_reflow_controls")
        service_calls: list[str] = []
        blockers: list[str] = []
        round_proxy = feedback.get("round_proxy") or self._services.get("round_proxy")
        if isinstance(round_proxy, Mapping):
            try:
                priority_controls = adaptive_reflow_metric_priority_controls(
                    round_proxy,
                    round_memory_fraction=float(
                        feedback.get("round_memory_fraction", self._services.get("round_memory_fraction", 0.10))
                    ),
                    round_charge_memory_fraction=float(
                        feedback.get(
                            "round_charge_memory_fraction",
                            self._services.get("round_charge_memory_fraction", 0.10),
                        )
                    ),
                    round_pair_memory_fraction=float(
                        feedback.get(
                            "round_pair_memory_fraction",
                            self._services.get("round_pair_memory_fraction", 0.10),
                        )
                    ),
                    round_temperature=float(
                        feedback.get("round_temperature", self._services.get("round_temperature", 1.0))
                    ),
                    round_bond_threshold=float(
                        feedback.get("round_bond_threshold", self._services.get("round_bond_threshold", 0.50))
                    ),
                    best_proxy_confidence=float(
                        feedback.get("best_proxy_confidence", self._services.get("best_proxy_confidence", -1.0))
                    ),
                    base_property_preference=property_vector,
                )
                priority_controls["dynamic_property_preference"] = adaptive_reflow_dynamic_property_preference(
                    property_vector,
                    priority_controls,
                )
                feedback["adaptive_reflow_priority_controls"] = priority_controls
                controls = priority_controls
                service_calls.extend(
                    [
                        "adaptive_reflow_metric_priority_controls",
                        "adaptive_reflow_dynamic_property_preference",
                    ]
                )
            except Exception as exc:
                blockers.append(f"adaptive_reflow_metric_priority_controls:{type(exc).__name__}:{exc}")
        else:
            blockers.append(f"{self.mechanism_id}:missing_required_input:round_proxy")
        if isinstance(controls, Mapping):
            proposed = (
                controls.get("dynamic_property_preference")
                or controls.get("property_preference")
                or controls.get("updated_property_preference")
                or {}
            )
            if isinstance(proposed, Mapping):
                for key, value in proposed.items():
                    parsed_value = _finite_float_control(value)
                    if parsed_value is None:
                        blockers.append(f"{self.mechanism_id}:property_preference_{key}_must_be_finite_float")
                        continue
                    property_vector[str(key)] = parsed_value
            sampler_controls: dict[str, float] = {}
            for key in (
                "memory_fraction",
                "charge_memory_fraction",
                "pair_memory_fraction",
                "temperature",
                "bond_threshold",
            ):
                if controls.get(key) is not None:
                    value = _finite_float_control(controls[key])
                    if value is None:
                        blockers.append(f"{self.mechanism_id}:{key}_must_be_finite_float")
                        continue
                    restart_bias[f"adaptive_reflow_{key}"] = value
                    sampler_controls[key] = value
                    if key == "memory_fraction":
                        restart_bias[key] = value
            if sampler_controls:
                restart_bias["sampler_controls"] = {
                    **dict(restart_bias.get("sampler_controls") or {}),
                    **sampler_controls,
                    "source": self.mechanism_id,
                }
            for control_key, mask_key in (
                ("freeze_charge_state", "charge_state"),
                ("freeze_pair_chemical_state", "pair_chemical_state"),
                ("local_pair_freeze_gate_pass", "local_pair_freeze_gate_pass"),
            ):
                if controls.get(control_key) is None:
                    continue
                parsed_bool = strict_bool_or_none(controls.get(control_key))
                if parsed_bool is None:
                    blockers.append(f"{self.mechanism_id}:{control_key}_must_be_boolean")
                    continue
                freeze_masks[mask_key] = parsed_bool
            restart_bias["adaptive_reflow_controls"] = dict(controls)
            try:
                round_count = max(1, int(feedback.get("rounds", self._services.get("rounds", 2))))
                round_index = max(
                    0,
                    min(
                        round_count - 1,
                        int(feedback.get("round_index", self._services.get("round_index", 0))),
                    ),
                )
                typed_plan = build_reinference_round_plan(
                    round_index=round_index,
                    rounds=round_count,
                    feedback=feedback if contains_true_metric_feedback(feedback) else None,
                    proxy=round_proxy if isinstance(round_proxy, Mapping) else None,
                    controls=controls,
                    current_condition={
                        "memory_fraction": feedback.get(
                            "round_memory_fraction",
                            self._services.get("round_memory_fraction", 0.0),
                        ),
                        "charge_memory_fraction": feedback.get(
                            "round_charge_memory_fraction",
                            self._services.get("round_charge_memory_fraction", 0.0),
                        ),
                        "pair_memory_fraction": feedback.get(
                            "round_pair_memory_fraction",
                            self._services.get("round_pair_memory_fraction", 0.0),
                        ),
                        "temperature": feedback.get("round_temperature", self._services.get("round_temperature", 1.0)),
                        "bond_threshold": feedback.get(
                            "round_bond_threshold",
                            self._services.get("round_bond_threshold", 0.50),
                        ),
                    },
                    property_preference=property_vector,
                    feedback_mode=(
                        "inference_external_diagnostic" if contains_true_metric_feedback(feedback) else "proxy_only"
                    ),
                ).as_dict()
                restart_bias["adaptive_reflow_round_plan"] = typed_plan
                service_calls.append("build_reinference_round_plan")
            except Exception as exc:
                blockers.append(f"build_reinference_round_plan:{type(exc).__name__}:{exc}")
        return FlowCondition(
            property_vector=property_vector,
            metric_feedback=feedback,
            freeze_masks=freeze_masks,
            restart_bias=restart_bias,
            extra={
                **dict(state.condition.extra),
                "adaptive_reflow": {
                    "mechanism_id": self.mechanism_id,
                    "ready": not blockers,
                    "blockers": blockers,
                    "service_calls": service_calls,
                    "controls": dict(controls) if isinstance(controls, Mapping) else {},
                    "round_plan": dict(restart_bias.get("adaptive_reflow_round_plan") or {}),
                },
            },
        )

    def pre_step(self, state: FlowState) -> FlowState:
        self._events.append({"event": "pre_step", "step_index": state.step_index})
        return state

    def post_step(self, state: FlowState, output: FlowDecodeOutput) -> FlowDecodeOutput:
        self._events.append({"event": "post_step", "candidate_id": output.candidate_id or state.candidate_id})
        return output

    def loss_terms(self, batch: Mapping[str, Any], output: FlowDecodeOutput) -> Mapping[str, Any]:
        del batch, output
        return {
            "mechanism_id": self.mechanism_id,
            "ready": False,
            "blockers": [f"{self.mechanism_id}:inference_only_no_training_loss_terms"],
            "service_calls": [],
            "outputs": {
                "owned_hooks": ["condition_delta", "feedback_update"],
                "reason": "adaptive_reflow_changes_inference_conditions_not_training_losses",
            },
        }

    def decode_policy(self, logits: Mapping[str, Any], context: MechanismContext) -> Mapping[str, Any]:
        del logits, context
        return {
            "mechanism_id": self.mechanism_id,
            "ready": False,
            "blockers": [f"{self.mechanism_id}:condition_delta_only_no_decode_policy_override"],
            "service_calls": [],
            "policy": "condition_delta_owned_adaptive_reflow",
            "outputs": {
                "owned_hooks": ["condition_delta", "feedback_update"],
                "reason": "adaptive_reflow_updates_property_restart_and_freeze_conditions_before_sampling",
            },
        }

    def feedback_update(self, evaluator_result: Mapping[str, Any]) -> MechanismTrace:
        feedback = dict(evaluator_result)
        controls: dict[str, Any] = {}
        property_names = tuple(str(name) for name in self._services.get("property_names", ("qed", "gnina")))
        if feedback and any(key in feedback for key in ("gnina_score", "qed", "posebusters_pass", "all_checks_pass")):
            try:
                controls = adaptive_reflow_external_metric_controls(
                    feedback,
                    round_proxy=dict(
                        self._services.get("round_proxy") or {"materialized": feedback.get("materialized", 0)}
                    ),
                    round_memory_fraction=float(self._services.get("round_memory_fraction", 0.30)),
                    round_charge_memory_fraction=float(self._services.get("round_charge_memory_fraction", 0.30)),
                    round_pair_memory_fraction=float(self._services.get("round_pair_memory_fraction", 0.30)),
                    round_temperature=float(self._services.get("round_temperature", 1.0)),
                    round_bond_threshold=float(self._services.get("round_bond_threshold", 0.5)),
                    base_property_preference=self._services.get("base_property_preference"),
                    property_names=property_names,
                    previous_external_feedback=self._last_feedback,
                )
                feedback["adaptive_reflow_controls"] = controls
            except Exception as exc:
                feedback["adaptive_reflow_control_blocker"] = f"{type(exc).__name__}:{exc}"
        if feedback.get("metric_delta") is not None and feedback.get("metric_deficit") is not None:
            try:
                metric_name = str(feedback.get("metric_name") or "panel_metric")
                metric_direction = metric_direction_for_name(
                    metric_name,
                    feedback.get("metric_direction") or feedback.get("optimization_direction") or "auto",
                )
                feedback["restart_noise_bias_ledger"] = noise_bias_from_metric_delta(
                    metric_name=metric_name,
                    metric_delta=float(feedback["metric_delta"]),
                    metric_deficit=float(feedback["metric_deficit"]),
                    base_memory_fraction=float(self._services.get("base_memory_fraction", 0.20)),
                    max_memory_fraction=float(self._services.get("max_memory_fraction", 0.70)),
                    freeze_improved_channels=bool(self._services.get("freeze_improved_channels", True)),
                    metric_direction=metric_direction,
                ).as_row()
            except Exception as exc:
                feedback["restart_noise_bias_blocker"] = f"{type(exc).__name__}:{exc}"
        self._last_feedback = feedback
        self._events.append(
            {
                "event": "feedback_update",
                "metric_keys": sorted(str(key) for key in evaluator_result),
                "service_calls": [
                    name
                    for name in ("adaptive_reflow_external_metric_controls", "noise_bias_from_metric_delta")
                    if (
                        name == "adaptive_reflow_external_metric_controls"
                        and "adaptive_reflow_controls" in feedback
                    )
                    or (name == "noise_bias_from_metric_delta" and "restart_noise_bias_ledger" in feedback)
                ],
                "blockers": [
                    value
                    for key, value in feedback.items()
                    if str(key).endswith("_blocker") and isinstance(value, str)
                ],
            }
        )
        return self.export_trace()

    def export_trace(self) -> MechanismTrace:
        return MechanismTrace(
            mechanism_id=self.mechanism_id,
            events=tuple(self._events),
            metrics=dict(self._last_feedback),
        )


def _finite_float_control(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


__all__ = ["AdaptiveReflowMechanism"]
