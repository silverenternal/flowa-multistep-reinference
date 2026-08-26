"""Adaptive reflow — DTB-R7 / DTB-R8 evaluation + reporting.

CPU-only DTB-R7 (calibration + paired evaluation + manifest I/O) and
DTB-R8 (claim gate + promotion + rollback + layered metric panel).
"""
from .calibration import (
    CHANNEL_NAMES_FOR_CALIBRATION,
    LOWER_BOUND_METHODS,
    PREDECLARED_SAFETY_METRICS,
    BucketKey,
    CalibrationBucket,
    CalibrationDatasetId,
    CalibrationManifest,
    CalibrationTimeSplit,
    ConfidenceLevel,
    IsoTimestamp,
    SampleCount,
    StabilityPerturbationProtocol,
    beta_lower_bound,
    classify_bucket,
    manifest_digest,
    wilson_lower_bound,
)
from .claim_gate import (
    DEFERRED_R8_REASON,
    ClaimGateArgumentError,
    ClaimGateConfig,
    ClaimGateDecision,
    ClaimGateEvaluation,
    build_default_claim_gate_config,
    evaluate_claim_gate,
)
from .manifests import (
    DEFERRED_GPU_SENTINEL,
    JsonString,
    ValidationResult,
    frozen_manifest_hash,
    read_calibration_manifest,
    validate_manifest_frozen,
    write_calibration_manifest,
)
from .metric_panel import (
    TIER_LABELS,
    LayeredEvidenceTiers,
    LayeredMetricPanel,
    LayeredMetricPanelArgumentError,
    build_default_layered_metric_panel,
    enforce_separation,
)
from .promotion import (
    DEFERRED_COST,
    DEFERRED_GAIN,
    PolicyVersionHashRecorder,
    PromotionArgumentError,
    PromotionReport,
    build_deferred_promotion_report,
    derive_policy_hash_from_version,
)
from .protocol import (
    PAIRED_ARM_KINDS,
    ArmName,
    ConfigHash,
    EvaluatorProvenanceGuard,
    EvaluatorVersion,
    MaterializationRoute,
    PairedComparisonArm,
    PairedComparisonRegistry,
    PolicyHash,
    RoundToRoundOscillationDetector,
    TargetPocketHash,
    evaluator_guard_digest,
)
from .rollback import (
    DEFAULT_DISABLED_REASON,
    RollbackArgumentError,
    RollbackAudit,
    RollbackFlag,
    apply_rollback,
    build_disabled_rollback_flag,
)
