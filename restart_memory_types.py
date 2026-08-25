"""Typed data carriers and validators for the adaptive_reflow component.

This module is the foundation of the adaptive_reflow typed contract. It declares:

* NewType-style aliases for every identifier / factor / provenance chain used
  by the contracts. Aliases are real ``typing.NewType`` wrappers so they round-
  trip through pickle, JSON and dataclass-asdict without losing identity.
* Frozen dataclasses exactly matching ``CONTRACTS.md`` sections 1-7.
* Deterministic sha256 hash helpers built on stdlib ``hashlib`` + ``json``.
* Pure helpers and validators returning ``ValidationResult = (ok, errors)``.

Tasks satisfied (per ``new/pocket_modules/mechanisms/inference/adaptive_reflow/todo.json``):

* ``DTB-R1``  — typed ``RoundResultBundle`` and channel evidence contract
* ``DTB-NC1`` — noncompact envelope ladder + tail budget + complement gate
* ``DTB-NC2`` — noncompact tail admissibility into dynamic transfer weight
* ``DTB-R2``  — calibrated per-channel dynamic contraction rule
* ``DTB-NA1`` — cosine annealed outer restart-noise budget
* ``DTB-L1``  — phase memory + horizon coverage + branch uncertainty
* ``DTB-L2``  — operation order commutator-safe semantics
* ``DTB-S1``  — writer arbitration between adaptive_reflow and noise_bias

The module is **stdlib-only**: no ``torch``, no other adaptive_reflow imports,
no IO. Anything heavier (rule evaluation, mixer logic, ledger persistence) is
a downstream concern.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal, Mapping, NewType, Tuple


# ---------------------------------------------------------------------------
# NewType aliases (round-trippable)
# ---------------------------------------------------------------------------

BundleId = NewType("BundleId", str)
LedgerRowId = NewType("LedgerRowId", str)
ManifestId = NewType("ManifestId", str)
RunId = NewType("RunId", str)
SampleId = NewType("SampleId", str)
TriggerId = NewType("TriggerId", str)
TraceDigest = NewType("TraceDigest", str)
ConditionDigest = NewType("ConditionDigest", str)
ArtifactHash = NewType("ArtifactHash", str)
MechanismId = NewType("MechanismId", str)
ChannelName = NewType("ChannelName", str)
FeedbackMode = NewType("FeedbackMode", str)
FactorValue = NewType("FactorValue", float)
ComplementBlockerCode = NewType("ComplementBlockerCode", str)
RestartTriggerCode = NewType("RestartTriggerCode", str)
PolicyId = NewType("PolicyId", str)
ProvenanceChain = NewType("ProvenanceChain", tuple)
FrameSpec = NewType("FrameSpec", Mapping[str, Any])
ShapeSpec = NewType("ShapeSpec", Mapping[str, Any])
MaterializationEvidenceRef = NewType("MaterializationEvidenceRef", Mapping[str, Any])
EvaluatorProvenanceRef = NewType("EvaluatorProvenanceRef", Mapping[str, Any])
FeedbackEvidenceRef = NewType("FeedbackEvidenceRef", Mapping[str, Any])
CoordinateChannelRef = NewType("CoordinateChannelRef", Mapping[str, Any])
ChargeChannelRef = NewType("ChargeChannelRef", Mapping[str, Any])
RawPairChannelRef = NewType("RawPairChannelRef", Mapping[str, Any])
ProjectedPairChannelRef = NewType("ProjectedPairChannelRef", Mapping[str, Any])
TailBudgetRowId = NewType("TailBudgetRowId", str)


# ---------------------------------------------------------------------------
# Channel/feedback/trigger/schedule literal sets (string enums inlined)
# ---------------------------------------------------------------------------

CHANNEL_NAMES: Tuple[str, ...] = ("coordinate", "charge", "raw_pair", "projected_pair")
FEEDBACK_MODES: Tuple[str, ...] = (
    "inference_external_diagnostic",
    "proxy_only",
    "training_authorized",
)
COMPLEMENT_BLOCKER_CODES: Tuple[str, ...] = (
    "out_of_envelope",
    "materialization_failure",
    "geometry_failure",
    "evaluator_provenance_missing",
    "lineage_invalid",
    "unclassified",
)
RESTART_TRIGGER_CODES: Tuple[str, ...] = (
    "tail_budget_violation",
    "complement_unclassified",
    "materialization_regression",
    "geometry_regression",
    "calibration_drift",
    "valid_evidence_no_progress",
)
SCHEDULE_FAMILIES: Tuple[str, ...] = (
    "constant",
    "linear",
    "cosine_no_restart",
    "cosine_guarded_restart",
    "empirical_learned",
)
SCHEDULE_PHASES: Tuple[str, ...] = (
    "high_noise",
    "anneal",
    "low_noise",
    "post_restart",
)
FRESH_NOISE_FLOOR_SOURCES: Tuple[str, ...] = (
    "schedule",
    "calibration",
    "manual_override",
)

# Per the brief, the OperationStep, AuthorityMode, and ChannelRule (Callable)
# aliases are not exposed as separate top-level types. They are inlined as
# Literal / Callable expressions where used. The Literal tuples are kept here
# so validators can iterate over the legal values without depending on
# typing.Protocol.
OPERATION_STEPS: Tuple[str, ...] = (
    "validate",
    "select",
    "restart_distribution",
    "condition_delta",
    "declared_freeze",
    "native_ODE_solve",
    "endpoint_observation",
)
DEFAULT_OPERATION_ORDER: Tuple[str, ...] = OPERATION_STEPS
AUTHORITY_MODES: Tuple[str, ...] = (
    "noise_bias_diagnostic_only",
    "noise_bias_legacy_standalone",
    "adaptive_reflow_executable",
    "flowa_core_consumer",
)


# ---------------------------------------------------------------------------
# Validation result alias
# ---------------------------------------------------------------------------

ValidationResult = Tuple[bool, Tuple[str, ...]]


def _ok() -> ValidationResult:
    return (True, ())


def _err(*messages: str) -> ValidationResult:
    return (False, tuple(messages))


# ---------------------------------------------------------------------------
# Hash helpers (deterministic, stdlib-only)
# ---------------------------------------------------------------------------


def _canonical_json(payload: Any) -> str:
    """Serialize ``payload`` to a deterministic JSON string."""
    return json.dumps(payload, sort_keys=True, default=_json_default)


def _json_default(obj: Any) -> Any:
    """Fallback serializer for non-JSON-native types (dataclasses, etc.)."""
    if dataclasses.is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, Mapping):
        return {k: v for k, v in obj.items()}
    if isinstance(obj, (tuple, list)):
        return [v for v in obj]
    if isinstance(obj, set):
        return sorted(v for v in obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return str(obj)


def hash_artifact(payload: Any) -> ArtifactHash:
    """Return a deterministic sha256 hex digest for ``payload``.

    ``payload`` may be any JSON-serializable structure or dataclass. Dataclasses
    are converted via ``dataclasses.asdict`` first, then the result is
    JSON-encoded with sorted keys and UTF-8 bytes before hashing.
    """
    if dataclasses.is_dataclass(payload):
        payload = asdict(payload)
    serialized = _canonical_json(payload)
    return ArtifactHash(hashlib.sha256(serialized.encode("utf-8")).hexdigest())


def hash_bundle_id(
    bundle_id: BundleId,
    source_round: int,
    round_count: int,
    run_id: RunId,
    sample_id: SampleId,
) -> ArtifactHash:
    """Return the content-derived sha256 hex for a bundle identity.

    The five input fields match the canonical recompute used by
    :func:`hash_trace_digest`; the function is exposed under a distinct name so
    callers can use it semantically as a "bundle id".
    """
    payload = _bundle_identity_payload(bundle_id, source_round, round_count, run_id, sample_id)
    return hash_artifact(payload)


def hash_trace_digest(
    bundle_id: BundleId,
    source_round: int,
    round_count: int,
    run_id: RunId,
    sample_id: SampleId,
) -> TraceDigest:
    """Return the deterministic trace digest for a ``RoundResultBundle``.

    The recompute rule is exactly the five-tuple ``(bundle_id, source_round,
    round_count, run_id, sample_id)``. ``RoundResultBundle.trace_digest`` must
    match the result of this function when validated.
    """
    payload = _bundle_identity_payload(bundle_id, source_round, round_count, run_id, sample_id)
    return TraceDigest(hash_artifact(payload))


def _bundle_identity_payload(
    bundle_id: BundleId,
    source_round: int,
    round_count: int,
    run_id: RunId,
    sample_id: SampleId,
) -> dict:
    return {
        "bundle_id": str(bundle_id),
        "source_round": int(source_round),
        "round_count": int(round_count),
        "run_id": str(run_id),
        "sample_id": str(sample_id),
    }


def hash_phase_state_digest(phase: "PhaseState") -> ArtifactHash:
    """Return the deterministic ``phase_state_digest`` for ``phase``.

    The digest is the sha256 of every field on the ``PhaseState`` *except*
    ``phase_state_digest`` itself (to avoid circular hash).
    """
    payload = {
        f.name: getattr(phase, f.name)
        for f in fields(phase)
        if f.name != "phase_state_digest"
    }
    return hash_artifact(payload)


def hash_policy_hash(policy: "FinalRestartPolicy") -> ArtifactHash:
    """Return the deterministic ``policy_hash`` for ``policy``.

    Recomputes from the canonical field tuple
    ``(policy_id, writer_id, run_id, target_round, outer_cycle_id,
    beta_by_channel, alpha_by_channel, fresh_noise_floor_by_channel,
    freeze_admission_by_channel)``.
    """
    payload = {
        "policy_id": str(policy.policy_id),
        "writer_id": str(policy.writer_id),
        "run_id": str(policy.run_id),
        "target_round": int(policy.target_round),
        "outer_cycle_id": int(policy.outer_cycle_id),
        "beta_by_channel": _sorted_items(policy.beta_by_channel),
        "alpha_by_channel": _sorted_items(policy.alpha_by_channel),
        "fresh_noise_floor_by_channel": _sorted_items(
            policy.fresh_noise_floor_by_channel
        ),
        "freeze_admission_by_channel": _sorted_items(
            {k: bool(v) for k, v in policy.freeze_admission_by_channel.items()}
        ),
    }
    return hash_artifact(payload)


def _sorted_items(mapping: Mapping[Any, Any]) -> list:
    """Return ``mapping`` as a sorted list of ``[key, value]`` pairs."""
    return [[str(k), v] for k, v in sorted(mapping.items(), key=lambda kv: str(kv[0]))]


# ---------------------------------------------------------------------------
# Atomic source bundle (CONTRACTS.md §1) — DTB-R1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundResultBundle:
    """Typed atomic source bundle; one per source round, no cross-round stitching."""

    bundle_id: BundleId
    source_round: int
    round_count: int
    run_id: RunId
    sample_id: SampleId
    trace_digest: TraceDigest
    condition_digest: ConditionDigest
    feedback_mode: FeedbackMode
    calibration_artifact_hash: ArtifactHash
    state_lock_is_detached: bool
    update_scope: str
    coordinate_channel: CoordinateChannelRef | None
    charge_channel: ChargeChannelRef | None
    raw_pair_channel: RawPairChannelRef | None
    projected_pair_channel: ProjectedPairChannelRef | None
    materialization_evidence: MaterializationEvidenceRef | None
    evaluator_provenance: EvaluatorProvenanceRef | None
    feedback_evidence: FeedbackEvidenceRef | None
    shape_spec: ShapeSpec
    frame_spec: FrameSpec
    provenance: ProvenanceChain
    created_at_round: int
    revoked: bool = False


@dataclass(frozen=True)
class ChannelTransferEvidence:
    """Per-channel transfer evidence; ``validation_errors`` must be empty."""

    bundle_id: BundleId
    channel: ChannelName
    materialization_pass: bool | None
    geometry_pass: bool | None
    perturbation_stability_lower_bound: FactorValue
    condition_sensitivity_observable_pass: bool | None
    external_metric_uncertainty: FactorValue | None
    proxy_only_evidence: bool
    ambiguity: FactorValue
    degeneracy_penalty: FactorValue
    support_coverage: FactorValue
    recency_decay: FactorValue
    calibration_lower_bound: FactorValue
    raw_score: float
    bounded_score: float
    provenance: ProvenanceChain
    validation_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChannelTransferDecision:
    """Per-channel decision; ``gate`` is True iff every required factor is valid."""

    bundle_id: BundleId
    channel: ChannelName
    gate: bool
    raw_factors: tuple[FactorValue, ...]
    evidence_score: FactorValue
    scheduled_cap: FactorValue
    bounded_target_fraction: FactorValue
    fresh_noise_floor: FactorValue
    alpha: FactorValue
    beta: FactorValue
    audit_reason: str
    blocker_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DynamicRestartTransferLedger:
    """Per-round ledger row: bundle selection + per-channel evidence/decision."""

    ledger_row_id: LedgerRowId
    run_id: RunId
    sample_id: SampleId
    trace_digest: TraceDigest
    source_round: int
    target_round: int
    outer_cycle_id: int
    selected_bundle_id: BundleId | None
    rejected_bundle_ids: tuple[BundleId, ...]
    per_channel_evidence: tuple[ChannelTransferEvidence, ...]
    per_channel_decision: tuple[ChannelTransferDecision, ...]
    alpha_by_channel: Mapping[ChannelName, FactorValue]
    beta_by_channel: Mapping[ChannelName, FactorValue]
    raw_fraction_by_channel: Mapping[ChannelName, FactorValue]
    bounded_fraction_by_channel: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    calibration_artifact_hash: ArtifactHash
    frozen_envelope_manifest_hash: ArtifactHash | None
    tail_budget_row_ref: TailBudgetRowId | None
    finite_prefix_only: bool
    empirical_only: bool
    feedback_mode: FeedbackMode
    writer_id: MechanismId
    provenance: ProvenanceChain
    validation_errors: tuple[str, ...]
    created_at_round: int


# ---------------------------------------------------------------------------
# Envelope ladder (CONTRACTS.md §2) — DTB-NC1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeLayer:
    """One layer in the run-start frozen compact-envelope ladder."""

    layer_index: int
    label: str
    coordinate_extent_rms_max: float
    coordinate_extent_rms_source_stats_hash: ArtifactHash
    pocket_distance_max: float
    pocket_contact_support_min: float
    atom_count_min: int
    atom_count_max: int
    graph_complexity_max: int
    sanitization_required: bool
    valence_rules_hash: ArtifactHash
    pair_entropy_min: float
    pair_entropy_source_stats_hash: ArtifactHash
    projection_loss_max: float
    internal_geometry_pass_required: bool
    evaluator_provenance_required: bool
    source_stats_hash: ArtifactHash
    threshold_digest: ArtifactHash
    layer_hash: ArtifactHash


@dataclass(frozen=True)
class FrozenEnvelopeManifest:
    """Run-start frozen envelope manifest. ``tail_selection_certified`` is False."""

    manifest_id: ManifestId
    run_id: RunId
    sample_id: SampleId
    target_pocket_hash: ArtifactHash
    config_hash: ArtifactHash
    created_at_round: Literal[0]
    layers: tuple[EnvelopeLayer, ...]
    empirical_only: bool
    finite_prefix_only: bool
    tail_selection_certified: Literal[False]
    manifest_hash: ArtifactHash


@dataclass(frozen=True)
class EnvelopeClassification:
    """Per-bundle envelope classification; ``complement_blocker`` is first match."""

    bundle_id: BundleId
    matched_layer_index: int | None
    complement_blocker: ComplementBlockerCode | None
    within_layer_thresholds: bool
    residual_extents: Mapping[str, float]


@dataclass(frozen=True)
class TailBudgetRow:
    """Per-round tail budget row; ``tail_selection_certified`` is always False."""

    row_id: TailBudgetRowId
    manifest_id: ManifestId
    outer_cycle_id: int
    round_in_cycle: int
    target_round: int
    archive_count: int
    deduplicated_archive_count: int
    deduplicated_transfer_score_mass: float
    requested_restart_write_mass: float
    accepted_restart_write_mass: float
    unknown_complement_mass: float
    missing_evidence_mass: float
    per_layer_excess_mass: Mapping[int, float]
    empirical_only: bool
    finite_prefix_only: bool
    tail_selection_certified: Literal[False]
    ledger_hash: ArtifactHash


# ---------------------------------------------------------------------------
# Channel rule (CONTRACTS.md §3) — DTB-R2
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelRuleInputs:
    """Inputs to the per-channel rule. Pure-data carrier; no I/O."""

    bundle: RoundResultBundle
    evidence: ChannelTransferEvidence
    phase_state: "PhaseState"
    scheduled_cap: FactorValue
    mixing_cap: FactorValue
    fresh_noise_floor: FactorValue
    delta_cap_up: FactorValue
    delta_cap_down: FactorValue
    tail_admissibility: bool
    complement_excluded: bool
    frozen_envelope_manifest_hash: ArtifactHash | None
    finite_prefix_only: bool
    calibration_lower_bound: FactorValue
    perturbation_stability_lower_bound: FactorValue
    support_coverage: FactorValue
    ambiguity: FactorValue
    degeneracy_penalty: FactorValue
    recency_decay: FactorValue
    horizon_coverage_proven: bool
    selected_bundle_id: BundleId


@dataclass(frozen=True)
class ChannelRuleOutputs:
    """Outputs of the per-channel rule."""

    decision: ChannelTransferDecision
    monotonicity_check_passed: bool
    validation_errors: tuple[str, ...] = ()


# ChannelRule is declared inline where needed as
# ``Callable[[ChannelRuleInputs], ChannelRuleOutputs]`` rather than as a
# top-level alias to keep this module free of Protocol re-exports.


# ---------------------------------------------------------------------------
# Cosine restart budget (CONTRACTS.md §4) — DTB-NA1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CosineScheduleConfig:
    """Frozen schedule configuration for the outer cycle."""

    schedule_family: Literal[
        "constant",
        "linear",
        "cosine_no_restart",
        "cosine_guarded_restart",
        "empirical_learned",
    ]
    cycle_length: int
    n_min: FactorValue
    n_max: FactorValue
    per_channel_caps: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    symmetric_delta_caps_by_channel: Mapping[ChannelName, FactorValue]
    restart_triggers_allowed: tuple[RestartTriggerCode, ...]
    config_hash: ArtifactHash
    frozen_before_evaluation: bool


@dataclass(frozen=True)
class CosineScheduleSample:
    """Sample of the schedule for a single round."""

    schedule_hash: ArtifactHash
    outer_cycle_id: int
    round_in_cycle: int
    cycle_length: int
    n_cap: FactorValue
    n_min: FactorValue
    n_max: FactorValue
    u_r: float
    family: str
    computed_at_round: int


@dataclass(frozen=True)
class FreshNoiseFloor:
    """Per-channel fresh-noise floor, with its provenance source."""

    channel: ChannelName
    floor_value: FactorValue
    source: Literal["schedule", "calibration", "manual_override"]
    config_hash: ArtifactHash


@dataclass(frozen=True)
class RestartTriggerEvent:
    """Record of one restart-trigger event (warm restart boundary)."""

    trigger_id: TriggerId
    outer_cycle_id_old: int
    outer_cycle_id_new: int
    trigger_code: RestartTriggerCode
    trigger_metric_snapshot: Mapping[str, float]
    discarded_source_bundle_ids: tuple[BundleId, ...]
    noise_capacity_before: FactorValue
    noise_capacity_after: FactorValue
    unresolved_metric_deficit: Mapping[str, float]
    provenance: ProvenanceChain
    recorded_at_round: int


# ---------------------------------------------------------------------------
# Phase state (CONTRACTS.md §5) — DTB-L1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhaseState:
    """Required controller input; cannot be reconstructed from endpoint score alone."""

    outer_cycle_id: int
    round_in_cycle: int
    schedule_phase: Literal["high_noise", "anneal", "low_noise", "post_restart"]
    schedule_phase_index: int
    previous_trigger: RestartTriggerEvent | None
    operation_order_version: str
    source_selector_procedure: str
    seed_lineage_digest: ArtifactHash
    horizon_remaining: int
    horizon_coverage_proven: bool
    ambiguity_band_active: bool
    phase_state_digest: ArtifactHash
    recorded_at_round: int


# ---------------------------------------------------------------------------
# Operation composition (CONTRACTS.md §6) — DTB-L2
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperationCompositionContract:
    """Operation order contract; the default order is fixed."""

    version: str
    operation_order: tuple[str, ...]
    default_order: tuple[str, ...] = DEFAULT_OPERATION_ORDER
    commutator_residual_tolerance: float = 0.0
    contract_hash: ArtifactHash = field(default=ArtifactHash(""))


@dataclass(frozen=True)
class CommutatorResidualDiagnostic:
    """Diagnostic row produced by an AB-vs-BA paired test."""

    contract_hash: ArtifactHash
    ab_endpoint_digest: TraceDigest
    ba_endpoint_digest: TraceDigest
    residual_norm: float
    within_tolerance: bool
    inputs_digest_ab: ArtifactHash
    inputs_digest_ba: ArtifactHash
    operation_order_version: str
    recorded_at_round: int


# ---------------------------------------------------------------------------
# Writer authority (CONTRACTS.md §7) — DTB-S1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RestartPolicyAuthorityContract:
    """Single-writer authority contract. ``adaptive_reflow`` is sole executable writer."""

    contract_version: str
    executable_writer_id: Literal["inference.adaptive_reflow"]
    diagnostic_writer_ids: tuple[MechanismId, ...]
    consumer_writer_id: Literal["flowa_core_runtime"]
    mode_flags: tuple[str, ...]
    legacy_compatibility_window: "LegacyCompatibilityWindow"
    contract_hash: ArtifactHash


@dataclass(frozen=True)
class LegacyCompatibilityWindow:
    """Bounded compatibility window for the legacy ``noise_bias`` standalone route."""

    enabled: bool
    legacy_mechanism_id: MechanismId
    legacy_mode: Literal["legacy_standalone"]
    exclusive_with: tuple[MechanismId, ...]
    schema_read_compatibility_version: str
    writes_sampler_controls: Literal[False]


@dataclass(frozen=True)
class FinalRestartPolicy:
    """Immutable final restart policy consumed by ``flowa_core_runtime``."""

    policy_id: PolicyId
    writer_id: MechanismId
    run_id: RunId
    target_round: int
    outer_cycle_id: int
    beta_by_channel: Mapping[ChannelName, FactorValue]
    alpha_by_channel: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    schedule_sample: CosineScheduleSample | None
    freeze_admission_by_channel: Mapping[ChannelName, bool]
    ledger_row_id: LedgerRowId
    policy_hash: ArtifactHash
    created_at_round: int


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def empty_provenance() -> ProvenanceChain:
    """Return the canonical empty provenance chain.

    Callers must replace this with a non-empty producer list before validation.
    """
    return ProvenanceChain(())


def make_default_phase_state(
    *,
    outer_cycle_id: int = 0,
    round_in_cycle: int = 0,
    schedule_phase: Literal[
        "high_noise", "anneal", "low_noise", "post_restart"
    ] = "high_noise",
    schedule_phase_index: int = 0,
    previous_trigger: RestartTriggerEvent | None = None,
    operation_order_version: str = "v1",
    source_selector_procedure: str = "deterministic.previous_round",
    seed_lineage_digest: ArtifactHash = ArtifactHash(""),
    horizon_remaining: int = 1,
    horizon_coverage_proven: bool = False,
    ambiguity_band_active: bool = False,
    recorded_at_round: int = 0,
) -> PhaseState:
    """Build a :class:`PhaseState` with sensible defaults for tests."""
    seed_lineage_digest = ArtifactHash(seed_lineage_digest) if seed_lineage_digest else ArtifactHash(
        hash_artifact(
            {
                "selector": source_selector_procedure,
                "outer_cycle_id": outer_cycle_id,
                "round_in_cycle": round_in_cycle,
            }
        )
    )
    state = PhaseState(
        outer_cycle_id=outer_cycle_id,
        round_in_cycle=round_in_cycle,
        schedule_phase=schedule_phase,
        schedule_phase_index=schedule_phase_index,
        previous_trigger=previous_trigger,
        operation_order_version=operation_order_version,
        source_selector_procedure=source_selector_procedure,
        seed_lineage_digest=seed_lineage_digest,
        horizon_remaining=horizon_remaining,
        horizon_coverage_proven=horizon_coverage_proven,
        ambiguity_band_active=ambiguity_band_active,
        phase_state_digest=ArtifactHash(""),
        recorded_at_round=recorded_at_round,
    )
    digest = hash_phase_state_digest(state)
    return dataclasses.replace(state, phase_state_digest=digest)


def make_default_phase_state_digest(state: PhaseState) -> ArtifactHash:
    """Return the deterministic digest that ``state`` should carry."""
    return hash_phase_state_digest(state)


# ---------------------------------------------------------------------------
# Numeric / scalar validators
# ---------------------------------------------------------------------------


def validate_unit_float(x: float) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is finite and in ``[0, 1]``."""
    if not isinstance(x, (int, float)):
        return _err(f"expected a real number, got {type(x).__name__}")
    fx = float(x)
    if not math.isfinite(fx):
        return _err(f"value must be finite, got {fx!r}")
    if fx < 0.0 or fx > 1.0:
        return _err(f"value must be in [0, 1], got {fx!r}")
    return _ok()


def validate_unit_factor(x: FactorValue, name: str) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is finite and in ``[0, 1]``.

    The error message includes ``name`` so per-factor validation surfaces which
    factor caused the rejection.
    """
    if name is None or str(name).strip() == "":
        return _err("validate_unit_factor requires a non-empty name")
    if not isinstance(x, (int, float)):
        return _err(f"{name}: expected a real number, got {type(x).__name__}")
    fx = float(x)
    if not math.isfinite(fx):
        return _err(f"{name}: value must be finite, got {fx!r}")
    if fx < 0.0 or fx > 1.0:
        return _err(f"{name}: value must be in [0, 1], got {fx!r}")
    return _ok()


def validate_positive_int(x: int, name: str) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is a positive integer (``>= 1``)."""
    if name is None or str(name).strip() == "":
        return _err("validate_positive_int requires a non-empty name")
    if isinstance(x, bool) or not isinstance(x, int):
        return _err(f"{name}: expected int, got {type(x).__name__}")
    if x < 1:
        return _err(f"{name}: must be >= 1, got {x}")
    return _ok()


def validate_nonneg_int(x: int, name: str) -> ValidationResult:
    """Return ``(True, ())`` iff ``x`` is a non-negative integer (``>= 0``)."""
    if name is None or str(name).strip() == "":
        return _err("validate_nonneg_int requires a non-empty name")
    if isinstance(x, bool) or not isinstance(x, int):
        return _err(f"{name}: expected int, got {type(x).__name__}")
    if x < 0:
        return _err(f"{name}: must be >= 0, got {x}")
    return _ok()


# ---------------------------------------------------------------------------
# Dataclass validators
# ---------------------------------------------------------------------------


def _channel_source_round(channel: Mapping[str, Any] | None) -> int | None:
    if channel is None or not isinstance(channel, Mapping):
        return None
    if "source_round" not in channel:
        return None
    value = channel["source_round"]
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def validate_round_result_bundle(b: RoundResultBundle) -> ValidationResult:
    """Validate ``RoundResultBundle`` per the cross-contract invariants.

    Rejects when ``state_lock_is_detached`` is ``False``, ``update_scope`` is
    not ``"ode_restart_distribution_only"``, any non-``None`` channel carries a
    ``source_round`` that does not equal ``b.source_round``, ``provenance`` is
    empty, ``calibration_artifact_hash`` is empty, ``trace_digest`` does not
    match the deterministic recompute, ``created_at_round > source_round``, or
    the round/run/sample identifiers are empty or non-integer.
    """
    errors: list[str] = []

    if not b.state_lock_is_detached:
        errors.append("state_lock_is_detached must be True")
    if b.update_scope != "ode_restart_distribution_only":
        errors.append(
            f"update_scope must be 'ode_restart_distribution_only', got {b.update_scope!r}"
        )
    if not b.bundle_id:
        errors.append("bundle_id must be non-empty")
    if not b.run_id:
        errors.append("run_id must be non-empty")
    if not b.sample_id:
        errors.append("sample_id must be non-empty")
    if isinstance(b.source_round, bool) or not isinstance(b.source_round, int):
        errors.append(f"source_round must be int, got {type(b.source_round).__name__}")
    elif b.source_round < 0:
        errors.append(f"source_round must be >= 0, got {b.source_round}")
    if isinstance(b.round_count, bool) or not isinstance(b.round_count, int):
        errors.append(f"round_count must be int, got {type(b.round_count).__name__}")
    elif b.round_count < 0:
        errors.append(f"round_count must be >= 0, got {b.round_count}")
    if (
        isinstance(b.created_at_round, bool)
        or not isinstance(b.created_at_round, int)
        or b.created_at_round < 0
    ):
        errors.append(
            f"created_at_round must be non-negative int, got {b.created_at_round!r}"
        )
    elif (
        isinstance(b.source_round, int)
        and not isinstance(b.source_round, bool)
        and b.created_at_round > b.source_round
    ):
        errors.append(
            f"created_at_round ({b.created_at_round}) must be <= source_round "
            f"({b.source_round})"
        )
    if not b.provenance:
        errors.append("provenance must be non-empty")
    if not b.calibration_artifact_hash:
        errors.append("calibration_artifact_hash must be non-empty")

    expected_trace = hash_trace_digest(
        b.bundle_id, b.source_round, b.round_count, b.run_id, b.sample_id
    )
    if b.trace_digest != expected_trace:
        errors.append(
            "trace_digest does not match deterministic recompute of "
            "(bundle_id, source_round, round_count, run_id, sample_id)"
        )

    # Every non-None channel must carry a source_round equal to b.source_round;
    # missing source_round is treated as cross-round stitching (forbidden).
    for label, channel in (
        ("coordinate_channel", b.coordinate_channel),
        ("charge_channel", b.charge_channel),
        ("raw_pair_channel", b.raw_pair_channel),
        ("projected_pair_channel", b.projected_pair_channel),
    ):
        if channel is None:
            continue
        if not isinstance(channel, Mapping):
            errors.append(f"{label} must be a Mapping when present")
            continue
        if "source_round" not in channel:
            errors.append(
                f"{label} must declare source_round when present; "
                "missing source_round is treated as cross-round stitching"
            )
            continue
        ch_sr = channel["source_round"]
        if (
            isinstance(ch_sr, bool)
            or not isinstance(ch_sr, int)
            or ch_sr != b.source_round
        ):
            errors.append(
                f"{label}.source_round ({ch_sr!r}) must equal bundle.source_round "
                f"({b.source_round}); cross-round stitching is forbidden"
            )

    if errors:
        return (False, tuple(errors))
    return _ok()


def validate_channel_evidence(e: ChannelTransferEvidence) -> ValidationResult:
    """Validate :class:`ChannelTransferEvidence`.

    Rejects when any required factor is outside ``[0, 1]`` or non-finite,
    ``raw_score``/``bounded_score`` is non-finite, ``proxy_only_evidence`` is
    ``True`` while ``calibration_lower_bound`` is not exactly ``0.0``, or
    ``validation_errors`` is non-empty on a freshly constructed row.
    """
    errors: list[str] = []

    for name, value in (
        ("perturbation_stability_lower_bound", e.perturbation_stability_lower_bound),
        ("ambiguity", e.ambiguity),
        ("degeneracy_penalty", e.degeneracy_penalty),
        ("support_coverage", e.support_coverage),
        ("recency_decay", e.recency_decay),
        ("calibration_lower_bound", e.calibration_lower_bound),
    ):
        ok, sub_errors = validate_unit_factor(value, name)
        if not ok:
            errors.extend(sub_errors)

    if e.external_metric_uncertainty is not None:
        ok, sub_errors = validate_unit_factor(
            e.external_metric_uncertainty, "external_metric_uncertainty"
        )
        if not ok:
            # validate_unit_factor emits "name:" prefixes; the optional-None
            # branch message should not be considered a hard error since the
            # field is allowed to be None. We surface only the numeric issues.
            errors.extend(sub_errors)

    for name, value in (("raw_score", e.raw_score), ("bounded_score", e.bounded_score)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{name} must be a finite real number")
            continue
        if not math.isfinite(float(value)):
            errors.append(f"{name} must be finite, got {value!r}")

    if e.proxy_only_evidence and float(e.calibration_lower_bound) != 0.0:
        errors.append(
            "proxy_only_evidence=True requires calibration_lower_bound=0.0; "
            f"got {float(e.calibration_lower_bound)!r}"
        )
    if e.validation_errors:
        errors.append(
            "validation_errors must be empty when evidence is constructed; "
            f"got {tuple(e.validation_errors)!r}"
        )
    if errors:
        return (False, tuple(errors))
    return _ok()


def validate_envelope_manifest(m: FrozenEnvelopeManifest) -> ValidationResult:
    """Validate :class:`FrozenEnvelopeManifest`.

    Rejects when ``empirical_only`` is not ``True``, ``tail_selection_certified``
    is not ``False``, ``created_at_round`` is not ``0``, layers are not strictly
    monotone by ``layer_index``, or ``manifest_hash`` is empty.
    """
    errors: list[str] = []

    if not m.empirical_only:
        errors.append("empirical_only must be True")

    if m.tail_selection_certified is not False:
        errors.append(
            "tail_selection_certified must be False (forbidden to set True); "
            f"got {m.tail_selection_certified!r}"
        )
    if m.created_at_round != 0:
        errors.append(
            f"created_at_round must be exactly 0 (frozen at run start), got {m.created_at_round!r}"
        )
    if not m.manifest_hash:
        errors.append("manifest_hash must be non-empty")
    indices = [layer.layer_index for layer in m.layers]
    for i in range(1, len(indices)):
        if indices[i - 1] >= indices[i]:
            errors.append(
                f"layers must be strictly monotone by layer_index; "
                f"got {indices[i - 1]} >= {indices[i]} at position {i}"
            )
    if errors:
        return (False, tuple(errors))
    return _ok()


def validate_tail_budget_row(t: TailBudgetRow) -> ValidationResult:
    """Validate :class:`TailBudgetRow`.

    Rejects when ``empirical_only`` or ``finite_prefix_only`` is not ``True``,
    ``tail_selection_certified`` is not ``False``, or ``row_id`` / ``manifest_id``
    is empty.
    """
    errors: list[str] = []
    if not t.empirical_only:
        errors.append("empirical_only must be True")
    if not t.finite_prefix_only:
        errors.append("finite_prefix_only must be True")
    if t.tail_selection_certified is not False:
        errors.append(
            "tail_selection_certified must be False (forbidden to set True); "
            f"got {t.tail_selection_certified!r}"
        )
    if not t.row_id:
        errors.append("row_id must be non-empty")
    if not t.manifest_id:
        errors.append("manifest_id must be non-empty")
    if errors:
        return (False, tuple(errors))
    return _ok()


def validate_phase_state(p: PhaseState) -> ValidationResult:
    """Validate :class:`PhaseState`.

    Rejects when ``schedule_phase`` is not in the canonical literal set,
    ``operation_order_version`` is empty, ``horizon_remaining`` is not a
    positive integer, or ``phase_state_digest`` does not match the
    deterministic recompute.
    """
    errors: list[str] = []

    if p.schedule_phase not in SCHEDULE_PHASES:
        errors.append(
            f"schedule_phase must be one of {SCHEDULE_PHASES!r}, got {p.schedule_phase!r}"
        )

    if not p.operation_order_version:
        errors.append("operation_order_version must be non-empty")

    ok, sub_errors = validate_positive_int(p.horizon_remaining, "horizon_remaining")
    if not ok:
        errors.extend(sub_errors)

    expected_digest = hash_phase_state_digest(p)
    if p.phase_state_digest != expected_digest:
        errors.append(
            "phase_state_digest does not match deterministic recompute of "
            "all other PhaseState fields"
        )

    if errors:
        return (False, tuple(errors))
    return _ok()


def validate_final_restart_policy(p: FinalRestartPolicy) -> ValidationResult:
    """Validate :class:`FinalRestartPolicy`.

    Rejects when ``writer_id`` is not exactly ``"inference.adaptive_reflow"`` or
    ``policy_hash`` does not match the deterministic recompute of the canonical
    field tuple.
    """
    errors: list[str] = []
    if p.writer_id != "inference.adaptive_reflow":
        errors.append(
            f"writer_id must be 'inference.adaptive_reflow'; got {p.writer_id!r}"
        )
    expected_hash = hash_policy_hash(p)
    if p.policy_hash != expected_hash:
        errors.append(
            "policy_hash does not match deterministic recompute of "
            "(policy_id, writer_id, run_id, target_round, outer_cycle_id, "
            "beta_by_channel, alpha_by_channel, fresh_noise_floor_by_channel, "
            "freeze_admission_by_channel)"
        )
    if errors:
        return (False, tuple(errors))
    return _ok()


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    # ID / factor / ref NewType aliases
    "BundleId",
    "LedgerRowId",
    "ManifestId",
    "RunId",
    "SampleId",
    "TriggerId",
    "TraceDigest",
    "ConditionDigest",
    "ArtifactHash",
    "MechanismId",
    "ChannelName",
    "FeedbackMode",
    "FactorValue",
    "ComplementBlockerCode",
    "RestartTriggerCode",
    "PolicyId",
    "ProvenanceChain",
    "FrameSpec",
    "ShapeSpec",
    "MaterializationEvidenceRef",
    "EvaluatorProvenanceRef",
    "FeedbackEvidenceRef",
    "CoordinateChannelRef",
    "ChargeChannelRef",
    "RawPairChannelRef",
    "ProjectedPairChannelRef",
    "TailBudgetRowId",
    # Literal-set constants
    "CHANNEL_NAMES",
    "FEEDBACK_MODES",
    "COMPLEMENT_BLOCKER_CODES",
    "RESTART_TRIGGER_CODES",
    "SCHEDULE_FAMILIES",
    "SCHEDULE_PHASES",
    "FRESH_NOISE_FLOOR_SOURCES",
    "OPERATION_STEPS",
    "DEFAULT_OPERATION_ORDER",
    "AUTHORITY_MODES",
    # Validation result alias
    "ValidationResult",
    # §1 Atomic source bundle (DTB-R1)
    "RoundResultBundle",
    "ChannelTransferEvidence",
    "ChannelTransferDecision",
    "DynamicRestartTransferLedger",
    # §2 Envelope ladder (DTB-NC1)
    "EnvelopeLayer",
    "FrozenEnvelopeManifest",
    "EnvelopeClassification",
    "TailBudgetRow",
    # §3 Channel rule (DTB-R2)
    "ChannelRuleInputs",
    "ChannelRuleOutputs",
    # §4 Cosine restart budget (DTB-NA1)
    "CosineScheduleConfig",
    "CosineScheduleSample",
    "FreshNoiseFloor",
    "RestartTriggerEvent",
    # §5 Phase state (DTB-L1)
    "PhaseState",
    # §6 Operation composition (DTB-L2)
    "OperationCompositionContract",
    "CommutatorResidualDiagnostic",
    # §7 Writer authority (DTB-S1)
    "RestartPolicyAuthorityContract",
    "LegacyCompatibilityWindow",
    "FinalRestartPolicy",
    # Hash helpers
    "hash_artifact",
    "hash_bundle_id",
    "hash_trace_digest",
    "hash_phase_state_digest",
    "hash_policy_hash",
    # Pure helpers
    "empty_provenance",
    "make_default_phase_state",
    "make_default_phase_state_digest",
    # Validators
    "validate_unit_float",
    "validate_unit_factor",
    "validate_positive_int",
    "validate_nonneg_int",
    "validate_round_result_bundle",
    "validate_channel_evidence",
    "validate_envelope_manifest",
    "validate_tail_budget_row",
    "validate_phase_state",
    "validate_final_restart_policy",
]