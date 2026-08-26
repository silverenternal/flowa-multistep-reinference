"""Property tests: replay every ``tests/golden/**/*.json`` case.

Templates 22-25 from the brief:

22. ``bounded_merge`` golden replay — replay ``bounded_merge(inputs)`` for
    every JSON file under ``tests/golden/bounded_merge/`` and assert the
    actual value is float-equal to ``expected`` (within ``flowa_close``
    tolerance).
23. ``channel_rule`` golden replay — replay ``compute_channel_decision``
    for every JSON file under ``tests/golden/channel_rule/`` and assert
    the resulting :class:`ChannelTransferDecision` is **structurally**
    equal to ``expected`` (every field, including nested tuples).
24. ``claim_gate`` golden replay — replay ``evaluate_claim_gate(config,
    evidence, evaluated_at_round=...)`` for every JSON file under
    ``tests/golden/claim_gate/`` and assert the resulting
    :class:`ClaimGateEvaluation` is structurally equal to ``expected``.
25. Hash stability — ``hash_artifact({"x": frozen_obj})`` must be
    byte-stable across two runs.

The tests are stdlib-only (json + pathlib). They import the canonical
implementations from ``adaptive_reflow``.
"""
from __future__ import annotations

import dataclasses
import json
import math
import sys
from pathlib import Path
from typing import Any

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from adaptive_reflow.contracts import (  # noqa: E402
    ArtifactHash,
    BundleId,
    ChannelRuleInputs,
    ChannelTransferDecision,
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
    hash_artifact,
)
from adaptive_reflow.eval import (  # noqa: E402
    ClaimGateConfig,
    ClaimGateEvaluation,
    evaluate_claim_gate,
)
from adaptive_reflow.frame import (  # noqa: E402
    bounded_merge,
    compute_channel_decision,
)

# Import order matches the generator: import the molecule bundle first
# to break the ``contracts`` <-> ``molecular`` import cycle.
from adaptive_reflow.molecular.bundle import (  # noqa: E402
    RoundResultBundle,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

GOLDEN_ROOT = _REPO_ROOT / "tests" / "golden"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any]:
    """Load a single golden case as a dict."""
    with path.open("r", encoding="utf-8") as fh:
        return json.loads(fh.read())


def _golden_files(subject: str) -> list[Path]:
    """Return the sorted list of golden files for ``subject``."""
    sub = GOLDEN_ROOT / subject
    if not sub.is_dir():  # pragma: no cover - directory always exists
        return []
    return sorted(sub.glob("case_*.json"))


def _flowa_close(actual: float, expected: float, *, rel: float = 1e-9, abs_: float = 1e-12) -> bool:
    """Return True iff ``actual`` and ``expected`` are float-close.

    The function is the canonical "almost equal" helper used across the
    property tests. It combines a relative tolerance for normal-scale
    values with an absolute tolerance for near-zero values, so it
    handles both ``expected == 0.0`` and ``expected == 1.0`` corners.
    """
    if math.isnan(expected):
        return math.isnan(actual)
    if math.isinf(expected):
        return math.isinf(actual) and (actual > 0) == (expected > 0)
    return math.isclose(actual, expected, rel_tol=rel, abs_tol=abs_)


def _rebuild_inputs_from_json(inputs: dict[str, Any]) -> ChannelRuleInputs:
    """Reconstruct a :class:`ChannelRuleInputs` from its JSON dict."""
    bundle_dict = inputs["bundle"]
    evidence_dict = inputs["evidence"]
    phase_dict = inputs["phase_state"]

    # ---- bundle (MoleculeRoundResultBundle) ----
    bundle_kwargs = dict(bundle_dict)
    # ``observed_channels`` is ``init=False``; drop it so the dataclass
    # accepts the rest. ``__post_init__`` will rebuild it from the
    # four molecule channel fields.
    bundle_kwargs.pop("observed_channels", None)
    bundle = RoundResultBundle(**bundle_kwargs)

    # ---- evidence (ChannelTransferEvidence) ----
    evidence = ChannelTransferEvidence(
        bundle_id=BundleId(evidence_dict["bundle_id"]),
        channel=evidence_dict["channel"],
        materialization_pass=evidence_dict["materialization_pass"],
        geometry_pass=evidence_dict["geometry_pass"],
        perturbation_stability_lower_bound=FactorValue(
            evidence_dict["perturbation_stability_lower_bound"]
        ),
        condition_sensitivity_observable_pass=evidence_dict[
            "condition_sensitivity_observable_pass"
        ],
        external_metric_uncertainty=(
            FactorValue(evidence_dict["external_metric_uncertainty"])
            if evidence_dict["external_metric_uncertainty"] is not None
            else None
        ),
        proxy_only_evidence=evidence_dict["proxy_only_evidence"],
        ambiguity=FactorValue(evidence_dict["ambiguity"]),
        degeneracy_penalty=FactorValue(evidence_dict["degeneracy_penalty"]),
        support_coverage=FactorValue(evidence_dict["support_coverage"]),
        recency_decay=FactorValue(evidence_dict["recency_decay"]),
        calibration_lower_bound=FactorValue(evidence_dict["calibration_lower_bound"]),
        raw_score=evidence_dict["raw_score"],
        bounded_score=evidence_dict["bounded_score"],
        provenance=ProvenanceChain(tuple(evidence_dict["provenance"])),
        validation_errors=tuple(evidence_dict.get("validation_errors", ())),
    )

    # ---- phase state ----
    phase = _rebuild_phase_state(phase_dict)

    # ---- top-level rule inputs ----
    frozen_hash_raw = inputs["frozen_envelope_manifest_hash"]
    frozen_hash = (
        ArtifactHash(frozen_hash_raw) if frozen_hash_raw is not None else None
    )

    return ChannelRuleInputs(
        bundle=bundle,
        evidence=evidence,
        phase_state=phase,
        scheduled_cap=FactorValue(inputs["scheduled_cap"]),
        mixing_cap=FactorValue(inputs["mixing_cap"]),
        fresh_noise_floor=FactorValue(inputs["fresh_noise_floor"]),
        delta_cap_up=FactorValue(inputs["delta_cap_up"]),
        delta_cap_down=FactorValue(inputs["delta_cap_down"]),
        tail_admissibility=inputs["tail_admissibility"],
        complement_excluded=inputs["complement_excluded"],
        frozen_envelope_manifest_hash=frozen_hash,
        finite_prefix_only=inputs["finite_prefix_only"],
        calibration_lower_bound=FactorValue(inputs["calibration_lower_bound"]),
        perturbation_stability_lower_bound=FactorValue(
            inputs["perturbation_stability_lower_bound"]
        ),
        support_coverage=FactorValue(inputs["support_coverage"]),
        ambiguity=FactorValue(inputs["ambiguity"]),
        degeneracy_penalty=FactorValue(inputs["degeneracy_penalty"]),
        recency_decay=FactorValue(inputs["recency_decay"]),
        horizon_coverage_proven=inputs["horizon_coverage_proven"],
        selected_bundle_id=BundleId(inputs["selected_bundle_id"]),
    )


def _rebuild_phase_state(d: dict[str, Any]):
    """Reconstruct a :class:`PhaseState` from its JSON dict."""
    from adaptive_reflow.contracts import PhaseState

    prev_trigger_raw = d.get("previous_trigger")
    previous_trigger = _rebuild_previous_trigger(prev_trigger_raw) if prev_trigger_raw else None

    return PhaseState(
        outer_cycle_id=d["outer_cycle_id"],
        round_in_cycle=d["round_in_cycle"],
        schedule_phase=d["schedule_phase"],
        schedule_phase_index=d["schedule_phase_index"],
        previous_trigger=previous_trigger,
        operation_order_version=d["operation_order_version"],
        source_selector_procedure=d["source_selector_procedure"],
        seed_lineage_digest=ArtifactHash(d["seed_lineage_digest"]),
        horizon_remaining=d["horizon_remaining"],
        horizon_coverage_proven=d["horizon_coverage_proven"],
        ambiguity_band_active=d["ambiguity_band_active"],
        phase_state_digest=ArtifactHash(d["phase_state_digest"]),
        recorded_at_round=d["recorded_at_round"],
    )


def _rebuild_previous_trigger(d: dict[str, Any]):
    """Reconstruct a :class:`RestartTriggerEvent` from its JSON dict."""
    from adaptive_reflow.contracts import RestartTriggerEvent

    return RestartTriggerEvent(**d)


def _rebuild_claim_gate_config(d: dict[str, Any]) -> ClaimGateConfig:
    """Reconstruct a :class:`ClaimGateConfig` from its JSON dict."""
    artifact_hash_raw = d["required_calibration_artifact_hash"]
    artifact_hash = (
        ArtifactHash(artifact_hash_raw) if artifact_hash_raw is not None else None
    )
    return ClaimGateConfig(
        required_contracts_passing=tuple(d["required_contracts_passing"]),
        required_calibration_artifact_hash=artifact_hash,
        required_paired_evidence_count=d["required_paired_evidence_count"],
        gate_enabled=d["gate_enabled"],
        evaluation_window_rounds=d["evaluation_window_rounds"],
        minimum_confidence_interval_coverage=FactorValue(
            d["minimum_confidence_interval_coverage"]
        ),
    )


def _decision_field_dict(decision: ChannelTransferDecision) -> dict[str, Any]:
    """Render a decision as a dict, normalising NaN/Infinity tokens."""
    out = dataclasses.asdict(decision)
    return _normalise_floats(out)


def _evaluation_field_dict(evaluation: ClaimGateEvaluation) -> dict[str, Any]:
    """Render an evaluation as a dict (no floats to normalise)."""
    return dataclasses.asdict(evaluation)


def _coerce_tuples_in_decision(d: dict[str, Any]) -> dict[str, Any]:
    """Force the tuple-typed decision fields back to tuples.

    The golden JSON files serialise Python tuples as JSON arrays, so the
    ``expected`` dict loaded from JSON has lists in the slot where the
    real ``ChannelTransferDecision`` carries a tuple. The replay test
    compares actual vs expected by ``==`` and therefore needs both
    sides to use the same container type.
    """
    d = dict(d)
    if "raw_factors" in d:
        d["raw_factors"] = tuple(d["raw_factors"])
    if "blocker_codes" in d:
        d["blocker_codes"] = tuple(d["blocker_codes"])
    return d


def _coerce_tuples_in_evaluation(d: dict[str, Any]) -> dict[str, Any]:
    """Force the tuple-typed evaluation fields back to tuples."""
    d = dict(d)
    for key in (
        "gate_conditions_passed",
        "gate_conditions_failed",
    ):
        if key in d:
            d[key] = tuple(d[key])
    return d


def _normalise_floats(value: Any) -> Any:
    """Convert sentinel strings ("NaN" / "Infinity" / "-Infinity") back to floats.

    Also normalise nested list-of-tuples so JSON-loaded ``expected`` dicts
    compare equal to the ``dataclasses.asdict`` output of the actual
    result (which preserves tuples).
    """
    if isinstance(value, dict):
        return {k: _normalise_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalise_floats(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_normalise_floats(v) for v in value)
    if value == "NaN":
        return float("nan")
    if value == "Infinity":
        return float("inf")
    if value == "-Infinity":
        return float("-inf")
    return value


# ---------------------------------------------------------------------------
# Template 22 — bounded_merge golden replay
# ---------------------------------------------------------------------------


class TestBoundedMergeGoldenReplay:
    """Template 22: replay every bounded_merge golden case."""

    @pytest.mark.parametrize(
        "path",
        _golden_files("bounded_merge"),
        ids=lambda p: p.name,
    )
    def test_bounded_merge_replay(self, path: Path) -> None:
        case = _load_json(path)
        inputs = case["inputs"]
        actual = bounded_merge(
            prev=inputs["prev"],
            dynamic=inputs["dynamic"],
            cap=inputs["cap"],
            floor=inputs["floor"],
            delta_cap_up=inputs["delta_cap_up"],
            delta_cap_down=inputs["delta_cap_down"],
        )
        assert _flowa_close(actual, case["expected"]), (
            f"{case['name']}: bounded_merge returned {actual!r}, "
            f"expected {case['expected']!r}"
        )

    def test_bounded_merge_case_count(self) -> None:
        """The brief specifies ``~40`` cases; assert we have at least 30."""
        files = _golden_files("bounded_merge")
        assert len(files) >= 30, (
            f"expected >= 30 bounded_merge golden cases, got {len(files)}"
        )


# ---------------------------------------------------------------------------
# Template 23 — channel_rule golden replay
# ---------------------------------------------------------------------------


class TestChannelRuleGoldenReplay:
    """Template 23: replay every channel_rule golden case."""

    @pytest.mark.parametrize(
        "path",
        _golden_files("channel_rule"),
        ids=lambda p: p.name,
    )
    def test_channel_rule_replay(self, path: Path) -> None:
        case = _load_json(path)
        inputs = _rebuild_inputs_from_json(case["inputs"])
        actual_decision = compute_channel_decision(inputs).decision

        actual = _normalise_floats(_decision_field_dict(actual_decision))
        expected = _coerce_tuples_in_decision(_normalise_floats(case["expected"]))

        assert actual == expected, (
            f"{case['name']}: decision mismatch.\n"
            f"actual:   {actual}\n"
            f"expected: {expected}"
        )

    def test_channel_rule_case_count(self) -> None:
        files = _golden_files("channel_rule")
        assert len(files) >= 20, (
            f"expected >= 20 channel_rule golden cases, got {len(files)}"
        )


# ---------------------------------------------------------------------------
# Template 24 — claim_gate golden replay
# ---------------------------------------------------------------------------


class TestClaimGateGoldenReplay:
    """Template 24: replay every claim_gate golden case."""

    @pytest.mark.parametrize(
        "path",
        _golden_files("claim_gate"),
        ids=lambda p: p.name,
    )
    def test_claim_gate_replay(self, path: Path) -> None:
        case = _load_json(path)
        inputs = case["inputs"]
        config = _rebuild_claim_gate_config(inputs["config"])
        evidence = inputs["evidence"]
        actual = evaluate_claim_gate(
            config, evidence, evaluated_at_round=inputs["evaluated_at_round"]
        )
        actual_dict = _evaluation_field_dict(actual)
        expected_dict = _coerce_tuples_in_evaluation(case["expected"])
        assert actual_dict == expected_dict, (
            f"{case['name']}: evaluation mismatch.\n"
            f"actual:   {actual_dict}\n"
            f"expected: {expected_dict}"
        )

    def test_claim_gate_case_count(self) -> None:
        files = _golden_files("claim_gate")
        assert len(files) >= 15, (
            f"expected >= 15 claim_gate golden cases, got {len(files)}"
        )


# ---------------------------------------------------------------------------
# Template 25 — hash_artifact byte-stability
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _HashProbe:
    """A tiny frozen dataclass used as the hash payload."""

    x: int
    y: float
    label: str


class TestHashStability:
    """Template 25: hash_artifact must be byte-stable across runs."""

    def test_hash_artifact_byte_stable_across_runs(self) -> None:
        """Run the same hash twice; assert the bytes are identical."""
        obj = _HashProbe(x=42, y=3.14159, label="flowa")
        first = hash_artifact({"x": obj})
        # Re-run, simulating a fresh interpreter invocation: build a
        # new frozen instance, hash it again, and compare bytes.
        second_obj = _HashProbe(x=42, y=3.14159, label="flowa")
        second = hash_artifact({"x": second_obj})
        assert first == second, (
            f"hash_artifact is not stable: first={first}, second={second}"
        )

    def test_hash_artifact_keys_sorted(self) -> None:
        """Reordering keys must not change the hash."""
        obj = _HashProbe(x=1, y=2.0, label="stable")
        h1 = hash_artifact({"x": obj, "y": 1})
        h2 = hash_artifact({"y": 1, "x": obj})
        assert h1 == h2

    def test_hash_artifact_distinct_inputs_distinct_hashes(self) -> None:
        """Distinct payloads must hash to distinct digests."""
        h1 = hash_artifact({"x": 1})
        h2 = hash_artifact({"x": 2})
        assert h1 != h2
