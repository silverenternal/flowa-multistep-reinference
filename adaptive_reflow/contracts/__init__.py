"""Adaptive reflow typed contracts (CONTRACTS.md §1-§8).

Pure stdlib dataclasses, NewType aliases, hash helpers, validators.
No I/O, no torch, no other adaptive_reflow imports.

.. note::
   ``RoundResultBundle`` and ``validate_round_result_bundle`` are
   molecule-aware. They are re-exported from
   :mod:`adaptive_reflow.molecular.bundle` (canonical home) under the
   historical names for back-compat. The re-export is **lazy** via
   ``__getattr__`` to break the import cycle between
   :mod:`contracts.bundle` and :mod:`molecular.bundle`.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Lazy re-exports of the molecule-aware atomic source bundle.
# ---------------------------------------------------------------------------
# ``RoundResultBundle`` and ``validate_round_result_bundle`` are
# molecule-aware; they live in :mod:`adaptive_reflow.molecular.bundle`
# (canonical home) and are re-exported under the historical names via
# :mod:`contracts.bundle`. We declare the lazy ``__getattr__`` resolver
# AND pre-populate the module namespace BEFORE the eager
# ``from .bundle import ...`` block below because the eager chain
# (``contracts.bundle`` -> ``contracts.types`` ->
# ``molecular.channels`` -> ``molecular.__init__``) triggers a
# ``from adaptive_reflow.contracts import RoundResultBundle`` while
# ``adaptive_reflow.contracts`` is mid-init. Without the early
# registration the eager import fails with a circular-import error
# (Python's ``from X import Y`` consults ``X.__dict__`` directly during
# a partial init and does NOT always fall through to module-level
# ``__getattr__``).
#
# We register a ``__getattr__`` resolver AND pre-populate
# ``globals()["RoundResultBundle"]`` / ``["validate_round_result_bundle"]``
# so both lookup paths succeed.
_LAZY_BUNDLE_NAMES = frozenset({"RoundResultBundle", "validate_round_result_bundle"})


def __getattr__(name: str) -> Any:  # pragma: no cover - exercised via re-export
    """Lazy-load the molecule-aware bundle re-exports to break the cycle."""
    if name in _LAZY_BUNDLE_NAMES:
        from . import bundle as _bundle_module

        value = getattr(_bundle_module, name)
        globals()[name] = value
        return value
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


def _prepopulate_molecule_bundle_names() -> None:
    """Pre-populate ``RoundResultBundle`` / ``validate_round_result_bundle``
    in this module's namespace so the eager chain in
    :mod:`adaptive_reflow.molecular.__init__` finds them via direct
    namespace lookup. Safe to call at top-of-file: ``molecular.bundle``
    does not import :mod:`adaptive_reflow.contracts.__init__` directly
    (it imports only ``contracts.types`` / ``contracts.validators``),
    so no cycle is triggered here.
    """
    try:
        from adaptive_reflow.molecular.bundle import (
            MoleculeRoundResultBundle as _RRB,
        )
        from adaptive_reflow.molecular.bundle import (
            validate_molecule_round_result_bundle as _VRRB,
        )
    except ImportError:
        return
    globals()["RoundResultBundle"] = _RRB
    globals()["validate_round_result_bundle"] = _VRRB


_prepopulate_molecule_bundle_names()


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
    CosineScheduleConfig,
    CosineScheduleSample,
    FreshNoiseFloor,
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

# ---------------------------------------------------------------------------
# Lazy re-exports of the molecule-aware atomic source bundle.
# ---------------------------------------------------------------------------
# NOTE: The ``__getattr__`` resolver and ``_LAZY_BUNDLE_NAMES`` set are
# declared at the TOP of this module (before the eager ``from .bundle
# import ...`` block) so the lazy resolver is in place when the eager
# chain triggers ``from adaptive_reflow.contracts import
# RoundResultBundle`` mid-init. See the comment near the top of the
# file for the full rationale.


__all__ = [
    "AUTHORITY_MODES",
    "AUDIT_SOURCE_REVOKED",
    "ArchiveAuditTrail",
    "AuditCode",
    "ArchiveQuota",
    "ArtifactHash",
    "BundleId",
    "CHANNEL_NAMES",
    "COMPLEMENT_BLOCKER_CODES",
    "ChannelName",
    "ChannelRuleInputs",
    "ChannelRuleOutputs",
    "ChannelTransferDecision",
    "ChannelTransferEvidence",
    "ChargeChannelRef",
    "ComplementBlockerCode",
    "CommutatorResidualDiagnostic",
    "ConditionDigest",
    "CoordinateChannelRef",
    "CosineScheduleConfig",
    "CosineScheduleSample",
    "DEFAULT_OPERATION_ORDER",
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
    "LedgerRowId",
    "LegacyCompatibilityWindow",
    "ManifestId",
    "MaterializationEvidenceRef",
    "MechanismId",
    "NoiseBiasInputRow",
    "OPERATION_STEPS",
    "OperationCompositionContract",
    "PhaseState",
    "PolicyId",
    "ProjectedPairChannelRef",
    "ProvenanceChain",
    "RESTART_TRIGGER_CODES",
    "RawPairChannelRef",
    "RestartPolicyAuthorityContract",
    "RestartTriggerCode",
    "RestartTriggerEvent",
    "RoundResultBundle",
    "RunId",
    "SCHEDULE_FAMILIES",
    "SCHEDULE_PHASES",
    "SampleId",
    "ShapeSpec",
    "TailBudgetRow",
    "TailBudgetRowId",
    "TraceDigest",
    "TriggerId",
    "ValidationResult",
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
    "validate_final_restart_policy",
    "validate_nonneg_int",
    "validate_positive_int",
    "validate_round_result_bundle",
    "validate_unit_factor",
    "validate_unit_float",
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
]
