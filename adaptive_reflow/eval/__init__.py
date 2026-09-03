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
from .clip_score import (
    CLIPSCORE_PAPER_SCALE,
    CLIPScoreProtocol,
    CLIPScoreResult,
    DEFAULT_CLIP_MODEL_NAME,
    HFCosineClipScoreEvaluator,
)
from .fg_deviation import (
    DEFAULT_REFERENCE_PATH,
    DUNDEE_FR_SMARTS_NAMES,
    compute_flowmol3_fg_deviation,
    count_fg_hits,
    dundee_smarts_dict,
    fg_deviation_l1,
    glaxo_smarts_dict,
)
from .fid import (
    FID_AUDIT_INSUFFICIENT_STATS,
    FID_EIGENCLIP_EPS_DEFAULT,
    FIDProtocol,
    FIDResult,
    InceptionV3FIDEvaluator,
    compute_frechet_distance,
)
from .freq_l1 import (
    BUNDLED_NATURAL_FASTA,
    DEFAULT_MAX_LENGTH,
    STANDARD_AA_ALPHABET,
    compute_freq_l1_block,
    per_position_freq_l1,
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
from .mmff_conformer import (
    DEFAULT_MMFF_MAX_ITERS,
    DEFAULT_NUM_CONFS,
    DEFAULT_RANDOM_SEED,
    MMFF_CONFORMER_FAILURE,
    embed_mmff,
    embed_mmff_smiles,
)
from .metric_panel import (
    TIER_LABELS,
    LayeredEvidenceTiers,
    LayeredMetricPanel,
    LayeredMetricPanelArgumentError,
    build_default_layered_metric_panel,
    enforce_separation,
)
from .posterior_selection_evaluator import (
    EVIDENCE_SCALE_GAP_AUDIT_REASON,
    EVIDENCE_SCALE_GAP_CHANNELS,
    POSTERIOR_SELECTION_AUDIT_REASON,
    POSTERIOR_SELECTION_BUNDLE_ID_PREFIX,
    POSTERIOR_SELECTION_CALIBRATION,
    POSTERIOR_SELECTION_CELLS_FOR_TARGET,
    POSTERIOR_SELECTION_CHANNELS,
    POSTERIOR_SELECTION_PERTURBATION,
    POSTERIOR_SELECTION_SHEET_FOR_TARGET,
    POSTERIOR_SELECTION_TARGETS,
    EvidenceScaleGapMetric,
    cell_evidence,
    mode_centers_for,
    selection_ratio,
    sheet_cell_centers,
    sheet_evidence,
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
from .twodim_fm_evaluator import (
    TWODIM_FM_COVERAGE_RADIUS,
    TWODIM_FM_EVALUATOR_AUDIT_REASON,
    TWODIM_FM_EVALUATOR_BUNDLE_ID_PREFIX,
    TWODIM_FM_EVALUATOR_CALIBRATION,
    TWODIM_FM_EVALUATOR_CHANNELS,
    TWODIM_FM_EVALUATOR_PERTURBATION,
    TWODIM_FM_GRID_BOUND,
    TWODIM_FM_GRID_RESOLUTION,
    TWODIM_FM_W2_MAX,
    TwoDimFMEvaluator,
    analytic_samples,
    coverage_score,
    energy_distance,
    voronoi_grid,
)
from .w2 import (
    DEFAULT_W2_FAMILY,
    W2_REGISTRY,
    KernelizedW2Estimator,
    ModeCentreMSEEstimator,
    ProjectionFreeW2Estimator,
    SinkhornW2Estimator,
    W2EstimatorProtocol,
    W2Family,
    build_w2_estimator,
    compute_w2,
)

# Note: ``PosteriorSelectionEvaluator`` is the deprecated alias for
# :class:`EvidenceScaleGapMetric`. Accessing it on
# ``adaptive_reflow.eval.posterior_selection_evaluator`` triggers a
# :class:`DeprecationWarning` via the PEP 562 module-level
# ``__getattr__`` defined in that submodule. Downstream callers
# should switch to ``EvidenceScaleGapMetric`` directly.
