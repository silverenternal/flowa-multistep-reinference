"""Adaptive reflow orchestration helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

# DTB-R3: ``merge_controls_fn`` is retained for backward compatibility
# but is being replaced by the orchestrator's
# ``AdaptiveReflowPolicyOrchestrator.merge_fraction_authority`` method.
# Callers that have a constructed ``AdaptiveReflowPolicyOrchestrator``
# should pass it via the new ``policy_orchestrator`` keyword (preferred)
# and let the orchestrator route the merge. The legacy callable is
# invoked only when no orchestrator is supplied, and any unconditional
# ``max(previous, dynamic)`` operator is no longer present in this
# module.


SCHEDULE_KEYS = (
    "property_preference_schedule",
    "memory_fraction_schedule",
    "charge_memory_fraction_schedule",
    "pair_memory_fraction_schedule",
    "freeze_charge_state_schedule",
    "freeze_pair_chemical_state_schedule",
    "bond_threshold_schedule",
    "temperature_schedule",
    "external_metric_feedback_schedule",
    "closed_loop_reconditioning_policy",
)


def _require_round_index(round_index: int, rounds: int) -> tuple[int, int]:
    if isinstance(round_index, bool) or isinstance(rounds, bool):
        raise ValueError("adaptive reflow round_index and rounds must be integers")
    index = int(round_index)
    count = int(rounds)
    if count < 1:
        raise ValueError("adaptive reflow rounds must be positive")
    if not 0 <= index < count:
        raise ValueError("adaptive reflow round_index must be in [0, rounds)")
    return index, count


def _schedule_value(schedule: Sequence[Any] | None, *, round_index: int, rounds: int, name: str) -> Any | None:
    if schedule is None:
        return None
    if isinstance(schedule, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence with one value per reflow round")
    if len(schedule) != int(rounds):
        raise ValueError(f"{name} length must match adaptive reflow rounds")
    return schedule[int(round_index)]


def _finite_float(
    value: Any,
    *,
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and numeric < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and numeric > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return numeric


def _bool_schedule_value(value: Any, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "n", "off", "disabled", ""}:
            return False
    raise ValueError(f"{name} values must be boolean")


def _route_merge(
    *,
    merge_controls_fn: Any,
    policy_orchestrator: Any | None,
    scheduled_memory_fraction: float,
    scheduled_charge_memory_fraction: float,
    scheduled_pair_memory_fraction: float,
    scheduled_freeze_charge_state: bool,
    scheduled_freeze_pair_chemical_state: bool,
    dynamic_control_delta: Mapping[str, Any],
) -> dict[str, Any]:
    """Route the merge through the orchestrator when one is available.

    DTB-R3: when ``policy_orchestrator`` is supplied, call its
    :meth:`merge_fraction_authority` method per channel and emit the
    bounded merge. Otherwise fall back to the legacy
    ``merge_controls_fn`` callable for backward compatibility. The
    legacy path is never used to bypass the bounded merge when an
    orchestrator is available.
    """
    if policy_orchestrator is not None:
        # The orchestrator owns the bounded merge; we still need a
        # ``freeze_*`` decision, which the orchestrator does not emit
        # directly. Apply the per-channel merge for fractions and fall
        # back to the supplied ``scheduled_freeze_*`` for the booleans.
        from adaptive_reflow.contracts import (
            ChannelName,
            CosineScheduleSample,
        )

        schedule_sample: CosineScheduleSample | None = getattr(
            policy_orchestrator, "_schedule_sampler", None
        )
        last_sample = (
            getattr(schedule_sample, "last_sample", None)
            if schedule_sample is not None
            else None
        )

        def _channel(channel: str, scheduled: float, dynamic: float) -> float:
            merge = getattr(policy_orchestrator, "merge_fraction_authority", None)
            if merge is None:
                return float(scheduled)
            result = merge(
                channel=ChannelName(channel),
                dynamic=float(dynamic),
                prev=None,
                schedule_sample=last_sample,
                fresh_noise_floor=float(scheduled),
            )
            return float(result)

        memory_fraction = _channel(
            "coordinate",
            scheduled_memory_fraction,
            dynamic_control_delta.get(
                "memory_fraction", scheduled_memory_fraction
            ),
        )
        charge_memory_fraction = _channel(
            "charge",
            scheduled_charge_memory_fraction,
            dynamic_control_delta.get(
                "charge_memory_fraction", scheduled_charge_memory_fraction
            ),
        )
        pair_memory_fraction = _channel(
            "raw_pair",
            scheduled_pair_memory_fraction,
            dynamic_control_delta.get(
                "pair_memory_fraction", scheduled_pair_memory_fraction
            ),
        )
        projected_pair_memory_fraction = _channel(
            "projected_pair",
            scheduled_pair_memory_fraction,
            dynamic_control_delta.get(
                "projected_pair_memory_fraction", scheduled_pair_memory_fraction
            ),
        )
        return {
            "memory_fraction": memory_fraction,
            "charge_memory_fraction": charge_memory_fraction,
            "pair_memory_fraction": pair_memory_fraction,
            "projected_pair_memory_fraction": projected_pair_memory_fraction,
            "freeze_charge_state": bool(scheduled_freeze_charge_state),
            "freeze_pair_chemical_state": bool(
                scheduled_freeze_pair_chemical_state
            ),
        }

    # Legacy / backward-compatible path.
    return merge_controls_fn(
        scheduled_memory_fraction=scheduled_memory_fraction,
        scheduled_charge_memory_fraction=scheduled_charge_memory_fraction,
        scheduled_pair_memory_fraction=scheduled_pair_memory_fraction,
        scheduled_freeze_charge_state=scheduled_freeze_charge_state,
        scheduled_freeze_pair_chemical_state=scheduled_freeze_pair_chemical_state,
        dynamic_control_delta=dynamic_control_delta,
    )


def prepare_outer_reflow_round(
    *,
    round_index: int,
    rounds: int,
    sample_kwargs: Mapping[str, Any],
    previous: Any | None,
    next_property_preference: Mapping[str, Any] | None,
    dynamic_control_delta: Mapping[str, Any],
    base_property_schedule: Sequence[Mapping[str, float] | None] | None,
    bond_threshold_schedule: Sequence[float] | None,
    temperature_schedule: Sequence[float] | None,
    memory_fraction_schedule: Sequence[float] | None,
    charge_memory_fraction_schedule: Sequence[float] | None,
    pair_memory_fraction_schedule: Sequence[float] | None,
    freeze_charge_state_schedule: Sequence[bool] | None,
    freeze_pair_chemical_state_schedule: Sequence[bool] | None,
    merge_controls_fn: Any,
    policy_orchestrator: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    """Build one adaptive reflow sampler call without executing the model.

    DTB-R3: ``merge_controls_fn`` is retained for backward compatibility
    but is deprecated. When ``policy_orchestrator`` is supplied (the
    recommended path) the orchestrator's
    :meth:`AdaptiveReflowPolicyOrchestrator.merge_fraction_authority`
    is invoked instead, ensuring the bounded merge uses
    per-channel delta caps, a fresh-noise floor, and can both raise
    and lower the prior-round fraction. The legacy ``merge_controls_fn``
    callable is only invoked when no orchestrator is supplied.
    """

    round_index, rounds = _require_round_index(round_index, rounds)
    kwargs = dict(sample_kwargs)
    for key in SCHEDULE_KEYS:
        kwargs.pop(key, None)
    updated_property_preference = dict(next_property_preference or {}) if next_property_preference is not None else None
    if base_property_schedule is not None and updated_property_preference is None:
        updated_property_preference = dict(
            _schedule_value(
                base_property_schedule,
                round_index=round_index,
                rounds=rounds,
                name="base_property_schedule",
            )
            or {}
        )
    elif base_property_schedule is not None:
        scheduled = dict(
            _schedule_value(
                base_property_schedule,
                round_index=round_index,
                rounds=rounds,
                name="base_property_schedule",
            )
            or {}
        )
        scheduled.update(updated_property_preference or {})
        updated_property_preference = scheduled
    kwargs["property_preference"] = updated_property_preference
    if temperature_schedule is not None:
        kwargs["temperature"] = _finite_float(
            _schedule_value(temperature_schedule, round_index=round_index, rounds=rounds, name="temperature_schedule"),
            name="temperature_schedule",
            minimum=0.0,
        )
    if "temperature" in dynamic_control_delta:
        kwargs["temperature"] = _finite_float(dynamic_control_delta["temperature"], name="temperature", minimum=0.0)
    if bond_threshold_schedule is not None:
        kwargs["bond_threshold"] = _finite_float(
            _schedule_value(
                bond_threshold_schedule,
                round_index=round_index,
                rounds=rounds,
                name="bond_threshold_schedule",
            ),
            name="bond_threshold_schedule",
            minimum=0.0,
            maximum=1.0,
        )
    if "bond_threshold" in dynamic_control_delta:
        kwargs["bond_threshold"] = _finite_float(
            dynamic_control_delta["bond_threshold"],
            name="bond_threshold",
            minimum=0.0,
            maximum=1.0,
        )
    memory_fraction = (
        _finite_float(
            _schedule_value(
                memory_fraction_schedule,
                round_index=round_index,
                rounds=rounds,
                name="memory_fraction_schedule",
            ),
            name="memory_fraction_schedule",
            minimum=0.0,
            maximum=1.0,
        )
        if memory_fraction_schedule is not None
        else 0.0
    )
    charge_memory_fraction = (
        _finite_float(
            _schedule_value(
                charge_memory_fraction_schedule,
                round_index=round_index,
                rounds=rounds,
                name="charge_memory_fraction_schedule",
            ),
            name="charge_memory_fraction_schedule",
            minimum=0.0,
            maximum=1.0,
        )
        if charge_memory_fraction_schedule is not None
        else memory_fraction
    )
    pair_memory_fraction = (
        _finite_float(
            _schedule_value(
                pair_memory_fraction_schedule,
                round_index=round_index,
                rounds=rounds,
                name="pair_memory_fraction_schedule",
            ),
            name="pair_memory_fraction_schedule",
            minimum=0.0,
            maximum=1.0,
        )
        if pair_memory_fraction_schedule is not None
        else memory_fraction
    )
    freeze_charge_state = (
        _bool_schedule_value(
            _schedule_value(
                freeze_charge_state_schedule,
                round_index=round_index,
                rounds=rounds,
                name="freeze_charge_state_schedule",
            ),
            name="freeze_charge_state_schedule",
        )
        if freeze_charge_state_schedule is not None
        else False
    )
    freeze_pair_chemical_state = (
        _bool_schedule_value(
            _schedule_value(
                freeze_pair_chemical_state_schedule,
                round_index=round_index,
                rounds=rounds,
                name="freeze_pair_chemical_state_schedule",
            ),
            name="freeze_pair_chemical_state_schedule",
        )
        if freeze_pair_chemical_state_schedule is not None
        else False
    )
    merged_controls = _route_merge(
        merge_controls_fn=merge_controls_fn,
        policy_orchestrator=policy_orchestrator,
        scheduled_memory_fraction=memory_fraction,
        scheduled_charge_memory_fraction=charge_memory_fraction,
        scheduled_pair_memory_fraction=pair_memory_fraction,
        scheduled_freeze_charge_state=freeze_charge_state,
        scheduled_freeze_pair_chemical_state=freeze_pair_chemical_state,
        dynamic_control_delta=dynamic_control_delta,
    )
    memory_fraction = _finite_float(
        merged_controls["memory_fraction"],
        name="merged_memory_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    charge_memory_fraction = _finite_float(
        merged_controls["charge_memory_fraction"],
        name="merged_charge_memory_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    pair_memory_fraction = _finite_float(
        merged_controls["pair_memory_fraction"],
        name="merged_pair_memory_fraction",
        minimum=0.0,
        maximum=1.0,
    )
    freeze_charge_state = _bool_schedule_value(
        merged_controls["freeze_charge_state"],
        name="merged_freeze_charge_state",
    )
    freeze_pair_chemical_state = _bool_schedule_value(
        merged_controls["freeze_pair_chemical_state"],
        name="merged_freeze_pair_chemical_state",
    )
    if previous is None and (freeze_charge_state or freeze_pair_chemical_state):
        freeze_charge_state = False
        freeze_pair_chemical_state = False
    if previous is not None:
        kwargs.update(
            {
                "fixed_sampled_symbols": previous.predicted_symbols,
                "restart_memory_coords": previous.flow.coords,
                "restart_memory_fraction": memory_fraction,
                "restart_charge_memory_fraction": charge_memory_fraction,
                "restart_pair_memory_fraction": pair_memory_fraction,
                "initial_charge_probability_state": previous.flow.charge_probability_state,
                "initial_raw_pair_chemical_probability": previous.flow.raw_pair_chemical_probability,
                "initial_projected_pair_chemical_probability": previous.flow.projected_pair_chemical_probability,
                "freeze_charge_probability_state": freeze_charge_state,
                "freeze_pair_chemical_probability": freeze_pair_chemical_state,
            }
        )
    kwargs["adaptive_reflow_round_index"] = int(round_index)
    kwargs["adaptive_reflow_round_count"] = int(rounds)
    controls = {
        "memory_fraction": memory_fraction,
        "charge_memory_fraction": charge_memory_fraction,
        "pair_memory_fraction": pair_memory_fraction,
        "freeze_charge_state": freeze_charge_state,
        "freeze_pair_chemical_state": freeze_pair_chemical_state,
    }
    return kwargs, controls, updated_property_preference
