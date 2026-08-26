"""Adaptive reflow typed contracts — atomic bundle (DTB-R1 + DTB-R2).

.. note::
   This module historically declared the molecule-specific
   :class:`RoundResultBundle` with the four molecule channel fields.
   The molecule half has been moved to
   :class:`adaptive_reflow.molecular.bundle.MoleculeRoundResultBundle`;
   the molecule-aware canonical home for the cross-contract validator
   is :func:`adaptive_reflow.molecular.bundle.validate_molecule_round_result_bundle`.

   This module re-exports :class:`MoleculeRoundResultBundle` under the
   historic name ``RoundResultBundle`` so existing imports
   (``from adaptive_reflow.contracts import RoundResultBundle``) keep
   working. The molecule-specific channel ``source_round`` check is
   enforced by ``validate_molecule_round_result_bundle`` (the same
   function, accessible here as ``validate_round_result_bundle``).

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from .hashes import hash_trace_digest
from .types import (
    ArtifactHash,
    BundleId,
    ChannelName,
    ChargeChannelRef,
    ConditionDigest,
    CoordinateChannelRef,
    EvaluatorProvenanceRef,
    FactorValue,
    FeedbackEvidenceRef,
    FeedbackMode,
    FrameSpec,
    LedgerRowId,
    MaterializationEvidenceRef,
    MechanismId,
    ProjectedPairChannelRef,
    ProvenanceChain,
    RawPairChannelRef,
    RunId,
    SampleId,
    ShapeSpec,
    TailBudgetRowId,
    TraceDigest,
)
from .validators import ValidationResult, _ok, validate_unit_factor

# ---------------------------------------------------------------------------
# Lazy re-export of the molecule atomic source bundle.
# ---------------------------------------------------------------------------
# The molecule-aware :class:`MoleculeRoundResultBundle` lives in
# ``adaptive_reflow.molecular.bundle``; we re-export it under the
# historical name ``RoundResultBundle`` for back-compat. The re-export
# is *lazy* (via ``__getattr__``) to break the import cycle:
#
#   ``contracts.bundle`` -> ``molecular.bundle`` -> ``contracts.hashes``
#     -> ``contracts.types`` (loads ``contracts.__init__``)
#     -> ``contracts.bundle`` (in-flight, no ``RoundResultBundle`` yet)
#
# The lazy ``__getattr__`` defers the molecule import until first
# attribute access. Type-checkers (mypy/pyright) see the names via the
# ``TYPE_CHECKING`` block below; the runtime defers via ``__getattr__``.
if TYPE_CHECKING:
    from adaptive_reflow.molecular.bundle import (  # pragma: no cover - typing only
        MoleculeRoundResultBundle as RoundResultBundle,
    )
    from adaptive_reflow.molecular.bundle import (  # pragma: no cover - typing only
        validate_molecule_round_result_bundle as validate_round_result_bundle,
    )

    from .phase import PhaseState

_MOLECULE_BUNDLE_NAMES = frozenset({"RoundResultBundle", "validate_round_result_bundle"})


def __getattr__(name: str) -> Any:  # pragma: no cover - exercised via re-export
    """Lazy-load the molecule bundle re-exports to break the import cycle."""
    if name in _MOLECULE_BUNDLE_NAMES:
        from adaptive_reflow.molecular import bundle as _mol_bundle

        value = getattr(_mol_bundle, name)
        globals()[name] = value
        return value
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )

# ---------------------------------------------------------------------------
# Atomic source bundle (CONTRACTS.md §1) — DTB-R1
# ---------------------------------------------------------------------------


# ``RoundResultBundle`` is the molecule-aware atomic source bundle.
# Defined in ``adaptive_reflow.molecular.bundle``; re-exported above
# for back-compat. The four molecule channel fields are documented on
# the molecule class.

# We retain the contract-level channel/decision/ledger dataclasses
# (which are NOT molecule-specific) in this module.

# ---------------------------------------------------------------------------
# Channel/decision/ledger dataclasses — universal
# ---------------------------------------------------------------------------


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
    ledger_version: str = "v3"


@dataclass(frozen=True)
class NoiseBiasInputRow:
    """DTB-R5: input row for the legacy ``noise_bias`` provenance feed.

    Each row records *which* producer emitted the row, *under which* authority
    mode, and whether the orchestrator adopted it as part of the final
    executable policy. The row is consumed by ``trace_schema`` (v3) and by
    any downstream auditing that needs to reconcile the legacy
    ``noise_bias`` stream with the per-round ledger.
    """

    producer_id: MechanismId
    producer_mode: Literal[
        "diagnostic_only",
        "legacy_standalone",
        "adaptive_reflow_executable",
        "flowa_core_consumer",
    ]
    was_adopted: bool
    calibration_artifact_hash: ArtifactHash
    feedback_mode: FeedbackMode
    round_in_cycle: int
    score: float
    uncertainty: float
    audit_reason: str


# ---------------------------------------------------------------------------
# Channel rule (CONTRACTS.md §3) — DTB-R2
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelRuleInputs:
    """Inputs to the per-channel rule. Pure-data carrier; no I/O."""

    bundle: RoundResultBundle
    evidence: ChannelTransferEvidence
    phase_state: PhaseState
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
# Dataclass validators — channel evidence (universal)
# ---------------------------------------------------------------------------


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

    for score_name, score_value in (
        ("raw_score", e.raw_score),
        ("bounded_score", e.bounded_score),
    ):
        if not isinstance(score_value, (int, float)) or isinstance(score_value, bool):
            errors.append(f"{score_name} must be a finite real number")
            continue
        if not math.isfinite(float(score_value)):
            errors.append(f"{score_name} must be finite, got {score_value!r}")

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
