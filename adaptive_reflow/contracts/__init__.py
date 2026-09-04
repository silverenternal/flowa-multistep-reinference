"""Adaptive reflow typed contracts (CONTRACTS.md §1-§8).

Pure stdlib dataclasses, NewType aliases, hash helpers, validators.
No I/O, no torch, no other adaptive_reflow imports.

.. note::
   ``RoundResultBundle`` and ``validate_round_result_bundle`` are
   molecule-aware. They are re-exported from
   :mod:`adaptive_reflow.molecular.bundle` (canonical home) under the
   historical names for back-compat. The re-export in
   :mod:`contracts.bundle` is eager with a :class:`DeprecationWarning`
   shim; a small ``__getattr__`` resolver here remains as
   belt-and-suspenders because
   :mod:`adaptive_reflow.molecular.__init__` runs an eager
   ``_resolve_contracts_round_result_bundle`` lookup at its own module
   import time, which would otherwise hit the partially-initialized
   :mod:`adaptive_reflow.contracts` package.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Lazy resolver for the molecule-aware atomic source bundle names.
# ---------------------------------------------------------------------------
# ``RoundResultBundle`` and ``validate_round_result_bundle`` live in
# :mod:`adaptive_reflow.molecular.bundle` (canonical home) and are
# re-exported under the historical names via :mod:`contracts.bundle`'s
# own eager DeprecationWarning shim. We keep this resolver as
# belt-and-suspenders for the partial-init cycle through
# :mod:`adaptive_reflow.molecular.__init__`'s eager
# ``_resolve_contracts_round_result_bundle`` call.
_LAZY_BUNDLE_NAMES = frozenset({"RoundResultBundle", "validate_round_result_bundle"})


def __getattr__(name: str) -> Any:  # pragma: no cover - exercised via re-export
    """Lazy-load the molecule-aware bundle re-exports."""
    if name in _LAZY_BUNDLE_NAMES:
        from . import bundle as _bundle_module

        value = getattr(_bundle_module, name)
        globals()[name] = value
        return value
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


# ---- NewType aliases ----
# ---- DTB-R1 + DTB-R2 contract (universal carriers) ----
# ---- Audit-code typed structure + chain consistency (CONTRACTS.md §9.1-§9.2) ----
from .audit import (
    AuditCode,
    coerce_audit_code,
    coerce_audit_codes,
    make_audit_code,
    parse_audit_code,
    validate_audit_chain,
    validate_audit_code,
)
from .bundle import (
    ChannelRuleInputs,
    ChannelRuleOutputs,
    ChannelTransferDecision,
    ChannelTransferEvidence,
    DynamicRestartTransferLedger,
    NoiseBiasInputRow,
    validate_channel_evidence,
)

# ---- DTB-NC1 / NC2 contract (re-exported molecule envelope) ----
# ``contracts.envelope`` is lazy (its module-level ``__getattr__`` defers
# the ``adaptive_reflow.molecular.envelope`` import until first access),
# so this ``from .envelope import ...`` resolves the four dataclasses
# and two validators through that lazy mechanism without triggering the
# historical ``contracts`` ↔ ``molecular`` cycle.
from .envelope import (
    EnvelopeClassification,
    EnvelopeLayer,
    FrozenEnvelopeManifest,
    TailBudgetRow,
    validate_envelope_manifest,
    validate_tail_budget_row,
)

# ---- Hash helpers ----
from .hashes import (
    hash_artifact,
    hash_bundle_id,
    hash_phase_state_digest,
    hash_policy_hash,
    hash_trace_digest,
)

# ---- DTB-L1 contract + factory ----
from .phase import (
    PhaseState,
    empty_provenance,
    make_default_phase_state,
    make_default_phase_state_digest,
)
from .phase import (
    validate_phase_state as _validate_phase_state_contract,
)

# ---- DTB-NA1 contract ----
from .schedule import (
    LEMMA4_REGIME_SLACK,
    CosineScheduleConfig,
    CosineScheduleSample,
    FreshNoiseFloor,
    RegimeAwareSchedulerProtocol,
    RegimeGate,
    RestartTriggerEvent,
)

# ---- Literal-set constants ----
from .types import (
    AUTHORITY_MODES,
    CHANNEL_NAMES,
    COMPLEMENT_BLOCKER_CODES,
    DEFAULT_OPERATION_ORDER,
    FEEDBACK_MODES,
    FRESH_NOISE_FLOOR_SOURCES,
    OPERATION_STEPS,
    RESTART_TRIGGER_CODES,
    SCHEDULE_FAMILIES,
    SCHEDULE_PHASES,
    ArtifactHash,
    BundleId,
    ChannelName,
    ChargeChannelRef,
    ComplementBlockerCode,
    ConditionDigest,
    CoordinateChannelRef,
    EvaluatorProvenanceRef,
    FactorValue,
    FeedbackEvidenceRef,
    FeedbackMode,
    FrameSpec,
    LedgerRowId,
    ManifestId,
    MaterializationEvidenceRef,
    MechanismId,
    PolicyId,
    ProjectedPairChannelRef,
    ProvenanceChain,
    RawPairChannelRef,
    RestartTriggerCode,
    RunId,
    SampleId,
    ShapeSpec,
    TailBudgetRowId,
    TraceDigest,
    TriggerId,
)

# ---- Validators + ValidationResult ----
from .validators import (
    AUDIT_SOURCE_REVOKED,
    ValidationResult,
    validate_nonneg_int,
    validate_positive_int,
    validate_unit_factor,
    validate_unit_float,
)

# Re-export to the original symbol name; the frame runtime imports
# it under a different name (validate_phase_state_runtime) to avoid
# shadowing.
validate_phase_state = _validate_phase_state_contract

# ---- DTB-L2 contract ----
# ---- DTB-R4 contract ----
from .archive import (
    ArchiveAuditTrail,
    ArchiveQuota,
    validate_archive_quota,
)

# ---- D4: Dynamic noise bias typed contracts ----
from .dynamic_noise_bias import (
    DynamicNoiseBiasResult,
    PaperQuantitiesSnapshot,
)

# ---- DTB-S1 contract ----
from .authority import (
    FinalRestartPolicy,
    LegacyCompatibilityWindow,
    RestartPolicyAuthorityContract,
    validate_final_restart_policy,
)
from .operations import (
    CommutatorResidualDiagnostic,
    OperationCompositionContract,
)

# ---- Generic state machine library (PEP 695, stdlib-only) ----
from .state_machine import (
    GuardRejected,
    HistoryKind,
    InvalidTransitionError,
    StateMachine,
    StateMachineError,
    StateNotFoundError,
    TransitionBuilder,
    TransitionContext,
    TransitionGuardedBuilder,
    TransitionKind,
    TransitionLog,
)

# ---- D8: Typed Condition discriminated union ----
from .condition import (
    BFNInpaintCondition,
    CFGCondition,
    CONDITION_KINDS,
    Condition,
    ConditionKind,
    InpaintingCondition,
    MappingConditionAdapter,
    NullCondition,
    PropertyCondition,
    condition_kind_of,
    condition_to_mapping,
    validate_condition,
    wrap_condition,
)

# ---- D5: Per-channel state-type + shape contracts (Design #3) ----
from .state_channel import (
    STATE_CHANNELS,
    StateChannel,
    StateChannelKind,
    StateShape,
    validate_channel_types,
    validate_state_channel,
    validate_state_shape,
)

# ---- D10: Typed materialization route (Design #4) ----
from .materialization import (
    EnvelopeStateBundle,
    LegacyProtocolAdapter,
    LossTolerance,
    MATERIALIZER_NOOP_DIGEST,
    MaterializationRoute,
    MaterializerHandle,
    NativeChannelAccessor,
    NativeStateBundle,
    NoOpMaterializer,
    default_materializer_route,
)

# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------
__all__ = [
    "AUTHORITY_MODES",
    "AUDIT_SOURCE_REVOKED",
    "ArchiveAuditTrail",
    "AuditCode",
    "ArchiveQuota",
    "ArtifactHash",
    "BFNInpaintCondition",
    "BundleId",
    "CFGCondition",
    "CHANNEL_NAMES",
    "CONDITION_KINDS",
    "COMPLEMENT_BLOCKER_CODES",
    "ChannelName",
    "ChargeChannelRef",
    "ComplementBlockerCode",
    "CommutatorResidualDiagnostic",
    "Condition",
    "ConditionDigest",
    "ConditionKind",
    "CoordinateChannelRef",
    "CosineScheduleConfig",
    "CosineScheduleSample",
    "DEFAULT_OPERATION_ORDER",
    "DynamicNoiseBiasResult",
    "DynamicRestartTransferLedger",
    "EvaluatorProvenanceRef",
    "FEEDBACK_MODES",
    "FRESH_NOISE_FLOOR_SOURCES",
    "FactorValue",
    "FeedbackEvidenceRef",
    "FeedbackMode",
    "FinalRestartPolicy",
    "FrameSpec",
    "FreshNoiseFloor",
    "FrozenEnvelopeManifest",
    "InpaintingCondition",
    "LEMMA4_REGIME_SLACK",
    "LedgerRowId",
    "LegacyCompatibilityWindow",
    "ManifestId",
    "MappingConditionAdapter",
    "MaterializationEvidenceRef",
    "MechanismId",
    "NoiseBiasInputRow",
    "NullCondition",
    "OPERATION_STEPS",
    "OperationCompositionContract",
    "PaperQuantitiesSnapshot",
    "PhaseState",
    "PolicyId",
    "ProjectedPairChannelRef",
    "PropertyCondition",
    "ProvenanceChain",
    "RESTART_TRIGGER_CODES",
    "RawPairChannelRef",
    "RestartPolicyAuthorityContract",
    "RegimeAwareSchedulerProtocol",
    "RegimeGate",
    "RestartTriggerCode",
    "RestartTriggerEvent",
    "RoundResultBundle",
    "RunId",
    "SCHEDULE_FAMILIES",
    "SCHEDULE_PHASES",
    "SampleId",
    "ShapeSpec",
    "STATE_CHANNELS",
    "StateChannel",
    "StateChannelKind",
    "StateShape",
    "TailBudgetRow",
    "TailBudgetRowId",
    "TraceDigest",
    "TriggerId",
    "ValidationResult",
    "condition_kind_of",
    "condition_to_mapping",
    "empty_provenance",
    "hash_artifact",
    "hash_bundle_id",
    "hash_phase_state_digest",
    "hash_policy_hash",
    "hash_trace_digest",
    "make_default_phase_state",
    "make_default_phase_state_digest",
    "validate_archive_quota",
    "validate_audit_chain",
    "validate_audit_code",
    "validate_channel_evidence",
    "validate_channel_types",
    "validate_condition",
    "validate_final_restart_policy",
    "validate_nonneg_int",
    "validate_positive_int",
    "validate_round_result_bundle",
    "validate_state_channel",
    "validate_state_shape",
    "validate_unit_factor",
    "validate_unit_float",
    "wrap_condition",
    # Audit-code typed structure (CONTRACTS.md §9.1-§9.2)
    "coerce_audit_code",
    "coerce_audit_codes",
    "make_audit_code",
    "parse_audit_code",
    # Envelope (molecule-aware)
    "EnvelopeClassification",
    "EnvelopeLayer",
    "validate_envelope_manifest",
    "validate_tail_budget_row",
    # Phase state validator
    "validate_phase_state",
    # Generic state machine library
    "GuardRejected",
    "HistoryKind",
    "InvalidTransitionError",
    "StateMachine",
    "StateMachineError",
    "StateNotFoundError",
    "TransitionBuilder",
    "TransitionContext",
    "TransitionGuardedBuilder",
    "TransitionKind",
    "TransitionLog",
    # D10 typed materialization route (Design #4)
    "EnvelopeStateBundle",
    "LegacyProtocolAdapter",
    "LossTolerance",
    "MATERIALIZER_NOOP_DIGEST",
    "MaterializationRoute",
    "MaterializerHandle",
    "NativeChannelAccessor",
    "NativeStateBundle",
    "NoOpMaterializer",
    "default_materializer_route",
]
