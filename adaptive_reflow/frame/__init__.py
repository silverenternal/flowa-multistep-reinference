"""Adaptive reflow — the universal round frame.

Engine + adapter protocol + bounded merge + channel rule + operation order +
phase transitions + round-trace v3 + orchestrator. The ``frame`` subpackage
is the universal driver of one round end-to-end.

The legacy ``DOMAIN_BY_CHANNEL`` constant that used to live here has been
removed; per-channel domain resolution is now each adapter's responsibility
via ``AdapterCapabilities.channel_domains``. The molecule-only fallback
table remains at ``adaptive_reflow.molecular.domain.MOLECULE_DOMAIN_BY_CHANNEL``
for molecule-aware callers.
"""
from .adapter import (
    NORMALIZATION_KINDS,
    REFERENCE_FRAMES,
    AdapterCapabilities,
    CapabilityMismatchError,
    CapabilityMissingError,
    FlowMatchingODEAdapter,
    ODEConditionDelta,
    ODEIntegratorTrace,
    RestartPolicy,
    StateBundle,
    TensorRef,
    validate_capabilities,
    validate_condition_delta,
    validate_integrator_trace,
    validate_state_bundle,
)
from .channel_rule import (
    AUDIT_SOURCE_REVOKED,
    AUDIT_STABILITY_COLLAPSE,
    BLOCKER_COMPLEMENT_EXCLUDED,
    BLOCKER_ENVELOPE_HASH_MISSING,
    BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL,
    BLOCKER_HORIZON_UNPROVEN,
    BLOCKER_MISSING_FACTOR,
    BLOCKER_NAN_OR_INF,
    BLOCKER_NON_FINITE,
    BLOCKER_NOT_FINITE_PREFIX,
    BLOCKER_PROXY_ONLY,
    BLOCKER_TAIL_INADMISSIBLE,
    CANONICAL_FACTOR_ORDER,
    PERTURBATION_STABILITY_FLOOR,
    check_monotonicity_property,
    compute_channel_decision,
    evaluate_channel_evidence_with_revocation,
    required_factors_in_unit_interval,
)
from .engine import (
    DEFAULT_OPERATION_STEPS,
    ENGINE_VERSION,
    ERR_ADAPTER_NONE,
    ERR_BUNDLE_INVALID,
    ERR_BUNDLE_NONE,
    ERR_CAPABILITIES_INVALID,
    ERR_CHANNEL_DOMAIN_MISMATCH,
    ERR_CHANNEL_UNSUPPORTED,
    ERR_CONDITION_DELTA_NO_EFFECT,
    ERR_DETACH_PROOF_FAILED,
    ERR_FEATURE_DISABLED,
    ERR_INTEGRATOR_TRACE_MISSING,
    ERR_PHASE_STATE_NONE,
    ERR_POLICY_NONE,
    ERR_ROUND_INDEX_NEGATIVE,
    ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH,
    FEATURE_FLAG_KEY,
    Engine,
    EngineRoundResult,
    LedgerRow,
    PhaseState,
    RoundTrace,
)
from .merge import (
    MERGE_AUTHORITY_SCHEMA_NAME,
    MERGE_AUTHORITY_SCHEMA_VERSION,
    MergeAuthorityError,
    bounded_merge,
    bounded_merge_with_schedule,
)
from .operation import (
    DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE,
    DEFAULT_OPERATION_COMPOSITION_VERSION,
    DEFAULT_OPERATION_ORDER,
    ERR_CONTRACT_NONE,
    ERR_OPERATION_ORDER_DUPLICATE,
    ERR_OPERATION_ORDER_EMPTY,
    ERR_OPERATION_ORDER_INCOMPLETE,
    ERR_OPERATION_ORDER_UNKNOWN,
    ERR_RECORDED_AT_ROUND_NEGATIVE,
    ERR_RECORDED_AT_ROUND_NON_INT,
    ERR_RECORDED_AT_ROUND_NONE,
    ERR_RESIDUAL_NORM_NON_NUMERIC,
    ERR_STEPS_NONE,
    ERR_VERSION_EMPTY,
    ERR_VERSION_NONE,
    build_default_composition_contract,
    record_commutator_residual,
    replay_default_order,
    validate_operation_order,
)
from .orchestrator import (
    WRITER_ID,
    AdaptiveReflowPolicyOrchestrator,
    PolicyOrchestratorError,
    PolicyOrchestratorValidationError,
)
from .phase import (
    advance_phase,
    build_phase_state,
    make_default_phase_state,
    validate_phase_state_transition,
)
from .trace import (
    ALLOWED_FINAL_POLICY_WRITERS,
    FINAL_POLICY_WRITER_ADAPTIVE_REFLOW,
    FINAL_POLICY_WRITER_LEGACY_NOISE_BIAS,
    PRODUCER_MODES,
    ROUND_TRACE_V2_SCHEMA_NAME,
    ROUND_TRACE_V3_SCHEMA_NAME,
    RoundTraceV3,
    compute_round_trace_v3_content_hash,
    freeze_round_trace_v3,
    read_round_trace_v2,
    round_trip_round_trace_v3,
)
