"""Adaptive reflow proxy and ODE-condition control policies."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, cast

from pocket_modules.core.models.multirate_flow import pair_chemical_decision_views
from pocket_modules.core.models.property_adapters import PROPERTY_NAMES
from pocket_modules.mechanisms.inference.adaptive_reflow import external_metric_feedback

try:
    import torch
except Exception:  # pragma: no cover - optional dependency
    torch = None


def require_torch() -> None:
    if torch is None:  # pragma: no cover - optional dependency
        raise RuntimeError("torch is required for adaptive reflow control policy")


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
    previous_external_feedback: Mapping[str, Any] | None = None,
    best_gnina_score: float | None = None,
    best_qed_value: float | None = None,
    best_posebusters_pass: bool = False,
    gnina_target_score: float = -4.0,
    qed_target: float = 0.65,
) -> dict[str, Any]:
    result = external_metric_feedback.adaptive_reflow_external_metric_controls(
        external_feedback,
        round_proxy,
        round_memory_fraction=round_memory_fraction,
        round_charge_memory_fraction=round_charge_memory_fraction,
        round_pair_memory_fraction=round_pair_memory_fraction,
        round_temperature=round_temperature,
        round_bond_threshold=round_bond_threshold,
        base_property_preference=base_property_preference,
        property_names=PROPERTY_NAMES,
        previous_external_feedback=previous_external_feedback,
        best_gnina_score=best_gnina_score,
        best_qed_value=best_qed_value,
        best_posebusters_pass=best_posebusters_pass,
        gnina_target_score=gnina_target_score,
        qed_target=qed_target,
    )
    return cast(dict[str, Any], result)


def adaptive_reflow_lightweight_proxy(result: Any) -> dict[str, Any]:
    """Score whether a detached round state is safe to preserve next round.

    The proxy is intentionally generation-local: it uses only the molecule
    materialisation result and decoder ledger produced by this sample, never
    native ligands, teacher labels, docking scores, or external evaluators.
    """

    ledger = dict(result.topology_ledger or {})
    pair_boundary = dict(ledger.get("pair_chemical_boundary") or {})
    heavy_atoms = max(1, int(result.heavy_atom_count))
    tree_edges = max(1, heavy_atoms - 1)
    decoded_graph_available = (
        1.0
        if (
            result.decoded_molecule is not None
            and bool(ledger.get("connected"))
            and not str(ledger.get("sanitize_error") or "")
        )
        else 0.0
    )
    # This proxy is produced inside the sampler, before the deployment
    # materialization route has run.  A decoded RDKit graph is useful topology
    # evidence, but it is not the same thing as a postprocessed SDF ligand that
    # survived ETKDG/raw-coordinate fallback, stage writing, and metric bridge
    # resolution.  Keep the old "materialized" channel fail-closed so proxy-only
    # controllers cannot freeze or preserve channels based on a molecule that
    # later fails deployment materialization.
    materialized = 0.0
    raw_hierarchical_edges = float(pair_boundary.get("raw_hierarchical_bond_event_count", 0.0) or 0.0)
    raw_candidate_edges = float(pair_boundary.get("raw_decoder_candidate_count", 0.0) or 0.0)
    raw_joint_edges = float(pair_boundary.get("raw_joint_map_edge_count", 0.0) or 0.0)
    projected_edges = float(pair_boundary.get("projected_hierarchical_bond_event_count", 0.0) or 0.0)
    projection_removed_mass = max(0.0, float(pair_boundary.get("soft_projection_removed_bonded_mass", 0.0) or 0.0))
    charge_abs_sum = float(abs(sum(int(value) for value in result.formal_charges)))
    charge_reliability = 1.0 if charge_abs_sum <= 1.0 else 0.55 if charge_abs_sum <= 2.0 else 0.20
    edge_supply = min(1.0, raw_hierarchical_edges / float(tree_edges))
    candidate_supply = min(1.0, raw_candidate_edges / float(tree_edges))
    joint_alignment = min(1.0, raw_joint_edges / float(max(1.0, raw_hierarchical_edges)))
    projection_penalty = min(1.0, projection_removed_mass / float(tree_edges + 1))
    pair_reliability = max(
        0.0,
        min(
            1.0,
            0.20 * decoded_graph_available
            + 0.25 * edge_supply
            + 0.20 * candidate_supply
            + 0.15 * joint_alignment
            + 0.05 * (1.0 - projection_penalty),
        ),
    )
    geometry_reliability = max(0.0, min(1.0, 0.45 * decoded_graph_available + 0.55 * edge_supply))
    return {
        "materialized": materialized,
        "decoded_graph_available": decoded_graph_available,
        "materialization_state_source": "postprocessing_not_run_sampler_local_proxy_fail_closed_v1",
        "tree_edge_target": float(tree_edges),
        "raw_hierarchical_edge_count": raw_hierarchical_edges,
        "projected_hierarchical_edge_count": projected_edges,
        "raw_decoder_candidate_count": raw_candidate_edges,
        "raw_joint_map_edge_count": raw_joint_edges,
        "charge_abs_sum": charge_abs_sum,
        "charge_reliability": charge_reliability,
        "pair_reliability": pair_reliability,
        "geometry_reliability": geometry_reliability,
    }


def adaptive_reflow_pair_local_freeze_mask(
    result: Any,
    *,
    min_probability: float = 0.62,
    max_pair_count: int | None = None,
) -> Any | None:
    """Select high-confidence detached pair states for local reflow locking."""

    if result.flow.raw_pair_chemical_probability is None:
        return None
    probability = result.flow.raw_pair_chemical_probability
    decisions = pair_chemical_decision_views(probability)
    edge_probability = decisions.topology_probability
    atom_count = int(edge_probability.shape[0])
    if atom_count <= 1:
        return torch.zeros(atom_count, atom_count, device=edge_probability.device, dtype=torch.bool)
    upper = torch.triu(
        torch.ones(atom_count, atom_count, device=edge_probability.device, dtype=torch.bool),
        diagonal=1,
    )
    candidate = upper & decisions.hierarchical_edge_mask & (edge_probability >= float(min_probability))
    if max_pair_count is None:
        max_pair_count = max(1, atom_count - 1)
    max_pair_count = max(0, int(max_pair_count))
    selected = torch.zeros_like(candidate)
    if max_pair_count > 0 and bool(candidate.any()):
        scores = edge_probability.masked_fill(~candidate, -torch.inf)
        flat_scores = scores.flatten()
        keep = min(max_pair_count, int(candidate.sum().detach().cpu()))
        indices = torch.topk(flat_scores, k=keep).indices
        selected.view(-1)[indices] = True
    mask = selected | selected.T
    mask.fill_diagonal_(False)
    return mask


def _strict_unit_property_value(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field}_must_be_numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{field}_must_be_finite")
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"{field}_must_be_unit_interval")
    return parsed


def _strict_property_preference_mapping(value: Any, *, field: str) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field}_must_be_mapping")
    parsed: dict[str, float] = {}
    for key, raw in value.items():
        if key not in PROPERTY_NAMES:
            raise ValueError(f"{field}_unknown_property:{key}")
        parsed[str(key)] = _strict_unit_property_value(raw, field=f"{field}:{key}")
    return parsed


def _strict_proxy_unit_signal(proxy: Mapping[str, Any], key: str, *, default: float) -> float:
    value = proxy.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"adaptive_reflow_proxy_confidence:{key}_must_be_numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"adaptive_reflow_proxy_confidence:{key}_must_be_finite")
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"adaptive_reflow_proxy_confidence:{key}_must_be_unit_interval")
    return parsed


def _strict_proxy_nonnegative_scalar(proxy: Mapping[str, Any], key: str, *, default: float) -> float:
    value = proxy.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"adaptive_reflow_metric_priority_proxy:{key}_must_be_numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"adaptive_reflow_metric_priority_proxy:{key}_must_be_finite")
    if parsed < 0.0:
        raise ValueError(f"adaptive_reflow_metric_priority_proxy:{key}_must_be_nonnegative")
    return parsed


def _strict_proxy_edge_target(proxy: Mapping[str, Any]) -> float:
    target = _strict_proxy_nonnegative_scalar(proxy, "tree_edge_target", default=1.0)
    if target < 1.0:
        raise ValueError("adaptive_reflow_metric_priority_proxy:tree_edge_target_must_be_at_least_one")
    return target


def adaptive_reflow_proxy_confidence(proxy: Mapping[str, Any]) -> dict[str, str | float]:
    """Convert generation-local proxy channels into a smooth trust signal.

    Literature-guided inference should not hinge on one hand-picked threshold.
    Use a harmonic mean so a weak channel dominates the trust signal, and an
    agreement penalty so inconsistent proxy channels receive less credit.
    """

    materialized = 1.0 if _strict_proxy_unit_signal(proxy, "materialized", default=0.0) >= 1.0 else 0.0
    decoded_graph_available = (
        1.0 if _strict_proxy_unit_signal(proxy, "decoded_graph_available", default=materialized) >= 1.0 else 0.0
    )
    charge = _strict_proxy_unit_signal(proxy, "charge_reliability", default=0.0)
    pair = _strict_proxy_unit_signal(proxy, "pair_reliability", default=0.0)
    geometry = _strict_proxy_unit_signal(proxy, "geometry_reliability", default=0.0)
    values = (charge, pair, geometry)
    epsilon = 1.0e-6
    harmonic = len(values) / sum(1.0 / max(epsilon, value) for value in values)
    agreement = 1.0 - min(1.0, max(values) - min(values))
    confidence = max(0.0, min(1.0, materialized * harmonic * agreement))
    return {
        "schema_version": "adaptive_reflow_proxy_confidence_v1",
        "joint_confidence": confidence,
        "weakest_channel_reliability": min(values),
        "channel_agreement": agreement,
        "charge_reliability": charge,
        "pair_reliability": pair,
        "geometry_reliability": geometry,
        "materialized": materialized,
        "decoded_graph_available": decoded_graph_available,
    }


def adaptive_reflow_soft_closed_loop_controls(
    round_proxy: Mapping[str, Any],
    *,
    round_memory_fraction: float,
    round_charge_memory_fraction: float,
    round_pair_memory_fraction: float,
    best_proxy_confidence: float,
    base_property_preference: Mapping[str, float] | Any | None,
) -> dict[str, Any]:
    """Return smooth closed-loop controls from proxy confidence.

    This follows the guidance pattern used in recent diffusion/flow work:
    multi-objective evidence is aggregated continuously, discrete channels are
    handled separately from coordinates, and guidance scales are bounded rather
    than expressed as all-or-nothing hard-coded thresholds.
    """

    confidence = adaptive_reflow_proxy_confidence(round_proxy)
    joint = float(confidence["joint_confidence"])
    materialized = float(confidence["materialized"]) >= 1.0
    previous_best = float(best_proxy_confidence)
    if previous_best < 0.0:
        history_credit = joint
    else:
        history_credit = max(0.0, min(1.0, joint / max(previous_best, 1.0e-6)))
    trust = max(0.0, min(1.0, joint * history_credit))
    if materialized:
        next_memory = float(round_memory_fraction) + (0.30 - float(round_memory_fraction)) * (0.35 * trust)
        next_memory = max(0.0, min(0.30, next_memory))
    else:
        next_memory = max(0.0, min(float(round_memory_fraction), float(round_memory_fraction) * 0.50))

    # Discrete atom/charge/bond states are high-leverage during sampling, but
    # they are also the easiest way to lock in a bad topology.  Increase them
    # only as a small continuous excess over the coordinate restart strength.
    channel_excess = 0.18 * trust * trust
    next_charge_memory = max(
        0.0,
        min(0.55, next_memory + channel_excess * float(confidence["charge_reliability"])),
    )
    next_pair_memory = max(
        0.0,
        min(0.55, next_memory + channel_excess * float(confidence["pair_reliability"])),
    )

    property_delta = _strict_property_preference_mapping(
        base_property_preference,
        field="adaptive_reflow_soft_closed_loop_base_property_preference",
    )
    if property_delta and trust > 0.0:
        property_scale = 0.10 * trust
        anchors = {"qed": 0.66, "logp": 0.50, "hba": 0.52}
        for key, anchor in anchors.items():
            if key not in PROPERTY_NAMES:
                continue
            current = property_delta.get(key, anchor)
            property_delta[key] = max(0.0, min(1.0, current + property_scale * (anchor - current)))

    return {
        "schema_version": "adaptive_reflow_soft_closed_loop_controls_v1",
        "memory_fraction": next_memory,
        "charge_memory_fraction": next_charge_memory,
        "pair_memory_fraction": next_pair_memory,
        "freeze_charge_state": False,
        "freeze_pair_chemical_state": False,
        "geometry_reliability_improved": bool(joint > previous_best if previous_best >= 0.0 else joint > 0.0),
        "gnina_preserving_channel_memory_gate_pass": bool(trust > 0.0 and materialized),
        "local_pair_freeze_gate_pass": bool(trust > 0.0 and materialized),
        "proxy_confidence": confidence,
        "proxy_history_credit": history_credit,
        "proxy_guidance_trust": trust,
        "proxy_guidance_channel_excess": channel_excess,
        "property_preference_delta": property_delta,
    }


def adaptive_reflow_metric_priority_controls(
    round_proxy: Mapping[str, Any],
    *,
    round_memory_fraction: float,
    round_charge_memory_fraction: float,
    round_pair_memory_fraction: float,
    round_temperature: float,
    round_bond_threshold: float,
    best_proxy_confidence: float,
    base_property_preference: Mapping[str, float] | Any | None,
) -> dict[str, Any]:
    """Plan the next reflow round from explicit metric-priority proxy evidence.

    This controller is intentionally strict about evidence.  It uses only
    generation-local materialisation/topology/geometry proxy channels, then
    exposes in the ledger that external PoseBusters/GNINA scores were not used
    inside the sampler.  Structural prerequisites are prioritised before
    drug-like polishing so a later objective cannot lock in an invalid graph.
    """

    confidence = adaptive_reflow_proxy_confidence(round_proxy)
    materialized = float(confidence["materialized"]) >= 1.0
    charge_reliability = float(confidence["charge_reliability"])
    pair_reliability = float(confidence["pair_reliability"])
    geometry_reliability = float(confidence["geometry_reliability"])
    proxy_joint = float(confidence["joint_confidence"])
    history_credit = (
        proxy_joint if best_proxy_confidence < 0.0
        else max(0.0, min(1.0, proxy_joint / max(float(best_proxy_confidence), 1.0e-6)))
    )
    trust = max(0.0, min(1.0, proxy_joint * history_credit))

    tree_target = _strict_proxy_edge_target(round_proxy)
    raw_edges = _strict_proxy_nonnegative_scalar(round_proxy, "raw_hierarchical_edge_count", default=0.0)
    projected_edges = _strict_proxy_nonnegative_scalar(round_proxy, "projected_hierarchical_edge_count", default=0.0)
    raw_candidates = _strict_proxy_nonnegative_scalar(round_proxy, "raw_decoder_candidate_count", default=0.0)
    raw_joint_edges = _strict_proxy_nonnegative_scalar(round_proxy, "raw_joint_map_edge_count", default=0.0)
    raw_edge_ratio = raw_edges / tree_target
    projected_edge_ratio = projected_edges / tree_target
    overconnected_ratio = max(raw_edge_ratio, raw_joint_edges / tree_target)
    candidate_ratio = raw_candidates / tree_target

    difficulty_rows = [
        {
            "metric": "materialization_topology",
            "rank": 0,
            "active": (not materialized) or projected_edge_ratio < 0.45,
            "severity": max(1.0 - projected_edge_ratio, 1.0 if not materialized else 0.0),
            "reason": "decoded molecule missing or too few projected structural edges",
        },
        {
            "metric": "topology_pair_calibration",
            "rank": 1,
            "active": overconnected_ratio >= 2.20 or (raw_edges >= 1.50 * tree_target and projected_edges <= 0.0),
            "severity": min(1.0, max(0.0, (overconnected_ratio - 1.0) / 2.5)),
            "reason": "raw pair evidence is much denser than the target molecular tree",
        },
        {
            "metric": "posebusters_geometry_proxy",
            "rank": 2,
            "active": materialized and geometry_reliability < 0.68,
            "severity": 1.0 - geometry_reliability,
            "reason": "materialized graph exists but geometry proxy is weak",
        },
        {
            "metric": "binding_druglikeness_proxy",
            "rank": 3,
            "active": materialized and pair_reliability >= 0.62 and geometry_reliability >= 0.62,
            "severity": max(0.0, 0.82 - min(pair_reliability, geometry_reliability, charge_reliability)),
            "reason": "structural proxies are usable; tighten model-visible property condition",
        },
        {
            "metric": "druglikeness_polish",
            "rank": 4,
            "active": materialized,
            "severity": max(0.05, 1.0 - proxy_joint),
            "reason": "fallback property polish after structural gates",
        },
    ]
    active_rows = [row for row in difficulty_rows if bool(row["active"])]
    selected = min(active_rows or [difficulty_rows[-1]], key=lambda row: int(str(row["rank"])))
    selected_metric = str(selected["metric"])

    base_condition = _strict_property_preference_mapping(
        base_property_preference,
        field="adaptive_reflow_metric_priority_base_property_preference",
    )
    base_delta = dict(base_condition)
    if selected_metric == "materialization_topology":
        next_memory = max(0.06, min(0.12, float(round_memory_fraction) * 0.60))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.40)
        next_pair_memory = max(float(round_pair_memory_fraction), 0.58)
        next_temperature = max(0.95, min(1.10, float(round_temperature) + 0.04))
        next_bond_threshold = min(0.48, max(0.44, float(round_bond_threshold) - 0.04))
        base_delta.update(
            {
                "qed": 0.62,
                "ertl_sa": 0.24,
                "logp": 0.50,
                "tpsa": 0.42,
                "mw": 0.36,
                "hbd": 0.30,
                "hba": 0.38,
                "rotors": 0.18,
                "rings": 0.30,
            }
        )
        freeze_charge = False
        freeze_pair = False
        local_pair_freeze = False
    elif selected_metric == "topology_pair_calibration":
        next_memory = max(0.08, min(0.18, float(round_memory_fraction)))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.50)
        next_pair_memory = min(max(float(round_pair_memory_fraction), 0.20), 0.35)
        next_temperature = max(0.92, min(1.05, float(round_temperature)))
        next_bond_threshold = max(0.54, min(0.60, float(round_bond_threshold) + 0.03))
        base_delta.update(
            {
                "qed": 0.64,
                "ertl_sa": 0.22,
                "tpsa": 0.42,
                "mw": 0.36,
                "hbd": 0.30,
                "hba": 0.38,
                "rotors": 0.18,
                "rings": 0.28,
            }
        )
        freeze_charge = charge_reliability >= 0.82
        freeze_pair = False
        local_pair_freeze = False
    elif selected_metric == "posebusters_geometry_proxy":
        next_memory = max(0.18, min(0.24, float(round_memory_fraction) + 0.04))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.60 if charge_reliability >= 0.70 else 0.50)
        next_pair_memory = max(min(float(round_pair_memory_fraction), 0.52), 0.42)
        next_temperature = max(0.90, min(1.00, float(round_temperature) - 0.03))
        next_bond_threshold = max(0.50, min(0.54, float(round_bond_threshold)))
        base_delta.update(
            {
                "qed": 0.66,
                "ertl_sa": 0.22,
                "tpsa": 0.40,
                "mw": 0.36,
                "hbd": 0.28,
                "hba": 0.36,
                "rotors": 0.18,
                "rings": 0.30,
            }
        )
        freeze_charge = charge_reliability >= 0.72
        freeze_pair = False
        local_pair_freeze = pair_reliability >= 0.72 and overconnected_ratio < 1.50
    else:
        next_memory = max(0.24, min(0.35, float(round_memory_fraction) + 0.06))
        next_charge_memory = max(float(round_charge_memory_fraction), 0.70)
        next_pair_memory = max(float(round_pair_memory_fraction), 0.62)
        next_temperature = max(0.88, min(1.00, float(round_temperature) - 0.05))
        next_bond_threshold = max(0.50, min(0.57, float(round_bond_threshold)))
        base_delta.update(
            {
                "qed": 0.70,
                "logp": 0.52,
                "tpsa": 0.40,
                "mw": 0.34,
                "hbd": 0.26,
                "hba": 0.34,
                "rotors": 0.16,
                "rings": 0.34,
            }
        )
        freeze_charge = charge_reliability >= 0.70
        freeze_pair = False
        local_pair_freeze = pair_reliability >= 0.70 and overconnected_ratio < 1.50

    property_delta = _strict_property_preference_mapping(
        base_delta,
        field="adaptive_reflow_metric_priority_property_preference_delta",
    )
    compact_controls = {
        "memory_fraction": next_memory,
        "charge_memory_fraction": next_charge_memory,
        "pair_memory_fraction": next_pair_memory,
        "temperature": next_temperature,
        "bond_threshold": next_bond_threshold,
        "freeze_charge_state": bool(freeze_charge),
        "freeze_pair_chemical_state": bool(freeze_pair),
        "local_pair_freeze_gate_pass": bool(local_pair_freeze),
    }
    decision = {
        "schema_version": "adaptive_reflow_metric_priority_decision_v1",
        "selected_metric_priority": selected_metric,
        "selected_priority_reason": str(selected["reason"]),
        "difficulty_order": [
            {
                "metric": str(row["metric"]),
                "rank": int(str(row["rank"])),
                "active": bool(row["active"]),
                "severity": float(str(row["severity"])),
                "reason": str(row["reason"]),
            }
            for row in difficulty_rows
        ],
        "available_proxy_metrics": sorted(str(key) for key in round_proxy),
        "previous_round_proxy": dict(round_proxy),
        "proxy_confidence": confidence,
        "proxy_history_credit": history_credit,
        "proxy_guidance_trust": trust,
        "controls": compact_controls,
        "property_preference_delta": property_delta,
        "freeze_decision": {
            "freeze_charge_state": bool(freeze_charge),
            "freeze_pair_chemical_state": bool(freeze_pair),
            "local_pair_freeze_gate_pass": bool(local_pair_freeze),
            "global_pair_freeze_blocked_reason": "avoid locking invalid or overconnected pair topology",
        },
        "uses_external_posebusters_or_gnina": False,
        "uses_native_ligand_or_teacher": False,
        "gnina_proxy_available": False,
        "gnina_proxy_policy": "defer binding-score optimization until structural proxy gates are satisfied",
        "structural_ratios": {
            "raw_edge_ratio": raw_edge_ratio,
            "projected_edge_ratio": projected_edge_ratio,
            "candidate_ratio": candidate_ratio,
            "overconnected_ratio": overconnected_ratio,
        },
    }
    return {
        "schema_version": "adaptive_reflow_metric_priority_controls_v1",
        "selected_metric_priority": selected_metric,
        "memory_fraction": next_memory,
        "charge_memory_fraction": next_charge_memory,
        "pair_memory_fraction": next_pair_memory,
        "temperature": next_temperature,
        "bond_threshold": next_bond_threshold,
        "freeze_charge_state": bool(freeze_charge),
        "freeze_pair_chemical_state": bool(freeze_pair),
        "geometry_reliability_improved": bool(
            proxy_joint > best_proxy_confidence if best_proxy_confidence >= 0.0 else proxy_joint > 0.0
        ),
        "gnina_preserving_channel_memory_gate_pass": bool(
            selected_metric in {"binding_druglikeness_proxy", "druglikeness_polish"}
        ),
        "local_pair_freeze_gate_pass": bool(local_pair_freeze),
        "local_pair_freeze_min_probability": 0.64 if selected_metric == "posebusters_geometry_proxy" else 0.68,
        "proxy_confidence": confidence,
        "proxy_history_credit": history_credit,
        "proxy_guidance_trust": trust,
        "property_preference_delta": property_delta,
        "metric_priority_decision": decision,
    }


def adaptive_reflow_dynamic_property_preference(
    base: Mapping[str, float] | Any | None,
    controls: Mapping[str, Any],
) -> Mapping[str, float] | Any | None:
    """Adjust the next round's numeric ODE condition from prior round proxies."""

    dynamic = controls.get("property_preference_delta")
    if dynamic is None:
        return base
    if not isinstance(dynamic, Mapping):
        raise ValueError("adaptive_reflow_dynamic_property_preference_delta_must_be_mapping")
    if not dynamic:
        return base
    merged = _strict_property_preference_mapping(
        base,
        field="adaptive_reflow_dynamic_base_property_preference",
    )
    for key, scalar in _strict_property_preference_mapping(
        dynamic,
        field="adaptive_reflow_dynamic_property_preference_delta",
    ).items():
        merged[key] = scalar
    return merged or base


def _strict_property_feedback_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"property_expert_feedback_{field}_must_be_boolean")


def _strict_property_feedback_float(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"property_expert_feedback_{field}_must_be_numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"property_expert_feedback_{field}_must_be_finite")
    return parsed


def _strict_property_feedback_route_weight(route_weights: Any) -> float | None:
    if not isinstance(route_weights, Mapping):
        return None
    if "property_condition" not in route_weights:
        return None
    route_weight = _strict_property_feedback_float(
        route_weights["property_condition"],
        field="route_weight",
    )
    if route_weight < 0.0:
        raise ValueError("property_expert_feedback_route_weight_must_be_nonnegative")
    if route_weight > 2.0:
        raise ValueError("property_expert_feedback_route_weight_out_of_range")
    return min(1.0, route_weight)


def adaptive_reflow_property_expert_controls(
    base: Mapping[str, float] | Any | None,
    property_terminal_ledger: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Turn a frozen terminal graph critic into the next ODE condition.

    The requested property vector is the desired normalized endpoint.  The
    terminal expert predicts the current normalized endpoint from the actual
    soft graph.  We extrapolate by the signed residual, weighted continuously
    by the expert's aleatoric uncertainty and router weight.  This preserves
    direction for properties where a lower target is desired and avoids a
    fixed pass/fail threshold.
    """

    if not isinstance(base, Mapping) or not base:
        return {
            "ready": False,
            "blockers": ["property_expert_feedback_requires_explicit_property_preference"],
    }
    ledger = dict(property_terminal_ledger or {})
    if "applied" not in ledger:
        return {"ready": False, "blockers": ["property_terminal_expert_not_applied"]}
    if not _strict_property_feedback_bool(ledger.get("applied"), field="applied"):
        return {"ready": False, "blockers": ["property_terminal_expert_not_applied"]}
    if "uses_effective_terminal_soft_graph_response" not in ledger:
        return {"ready": False, "blockers": ["property_terminal_expert_missing_effective_state_response"]}
    if not _strict_property_feedback_bool(
        ledger.get("uses_effective_terminal_soft_graph_response"),
        field="uses_effective_terminal_soft_graph_response",
    ):
        return {"ready": False, "blockers": ["property_terminal_expert_no_effective_state_response"]}
    if "state_response_norm" not in ledger:
        return {"ready": False, "blockers": ["property_terminal_expert_missing_effective_state_response"]}
    response_norm = _strict_property_feedback_float(
        ledger.get("state_response_norm"),
        field="state_response_norm",
    )
    if response_norm <= 0.0:
        return {"ready": False, "blockers": ["property_terminal_expert_no_effective_state_response"]}
    prediction = ledger.get("prediction")
    deviation = ledger.get("standard_deviation")
    if not isinstance(prediction, Mapping) or not isinstance(deviation, Mapping):
        return {"ready": False, "blockers": ["property_terminal_expert_missing_distribution"]}
    route_weight = _strict_property_feedback_route_weight(ledger.get("route_weights"))
    if route_weight is None or route_weight <= 0.0:
        return {"ready": False, "blockers": ["property_terminal_expert_property_route_inactive"]}

    updated: dict[str, float] = {}
    residuals: dict[str, float] = {}
    confidence: dict[str, float] = {}
    for name, requested_value in base.items():
        if name not in PROPERTY_NAMES or name not in prediction or name not in deviation:
            continue
        target = _strict_property_feedback_float(requested_value, field=f"target:{name}")
        predicted = _strict_property_feedback_float(prediction[name], field=f"prediction:{name}")
        sigma = _strict_property_feedback_float(deviation[name], field=f"standard_deviation:{name}")
        if sigma < 0.0:
            raise ValueError(f"property_expert_feedback_negative_standard_deviation:{name}")
        target = max(0.0, min(1.0, target))
        predicted = max(0.0, min(1.0, predicted))
        trust = route_weight / (1.0 + sigma)
        residual = target - predicted
        updated[name] = max(0.0, min(1.0, target + trust * residual))
        residuals[name] = residual
        confidence[name] = trust
    if not updated:
        return {"ready": False, "blockers": ["property_terminal_expert_no_overlapping_requested_properties"]}
    return {
        "schema_version": "adaptive_reflow_property_expert_controls_v1",
        "ready": True,
        "blockers": [],
        "property_preference_delta": updated,
        "requested_minus_predicted": residuals,
        "uncertainty_weighted_route_trust": confidence,
        "source": "frozen_terminal_soft_graph_property_expert",
        "uses_measured_endpoint_metrics": False,
        "uses_native_ligand": False,
    }
