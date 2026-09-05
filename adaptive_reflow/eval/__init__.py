"""Adaptive reflow — DTB-R7 / DTB-R8 evaluation + reporting.

CPU-only DTB-R7 (calibration + paired evaluation + manifest I/O) and
DTB-R8 (claim gate + promotion + rollback + layered metric panel).

Wave 15 C: rdkit-dependent submodules (:mod:`mmff_conformer`,
:mod:`fg_deviation`, :mod:`flowmol3_eq4_fg_deviation`,
:mod:`rdkit_oracle`) are **lazy-imported** via PEP 562 module-level
``__getattr__`` so that ``import adaptive_reflow.eval`` succeeds in
environments where rdkit is NOT installed (this is the real fix for
the Wave 14 A importlib bypass on :mod:`theory.checkers`).
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
    selection_ratio,  # Wave 30 F-4: back-compat alias
    sheet_cell_centers,
    sheet_evidence,
    sheet_vs_cells_proxy,
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

# P1-6: unified eval orchestrator + typed result shape.
from .result import (  # noqa: E402
    SCHEMA_VERSION,
    EvalResult,
    MetricKind,
    MetricResult,
)
from .run_eval import run_eval  # noqa: E402

# Note: ``PosteriorSelectionEvaluator`` is the deprecated alias for
# :class:`EvidenceScaleGapMetric`. Accessing it on
# ``adaptive_reflow.eval.posterior_selection_evaluator`` triggers a
# :class:`DeprecationWarning` via the PEP 562 module-level
# ``__getattr__`` defined in that submodule. Downstream callers
# should switch to ``EvidenceScaleGapMetric`` directly.


# ---------------------------------------------------------------------------
# Wave 15 C — lazy import surface for rdkit-dependent submodules
# ---------------------------------------------------------------------------
#
# The four submodules below eagerly import rdkit at module load time
# (``from rdkit import Chem``). Wave 14 A added an importlib.util bypass
# on :mod:`adaptive_reflow.theory.checkers` to avoid the rdkit trigger;
# the REAL fix is here: route the four submodules through a PEP 562
# ``__getattr__`` so ``import adaptive_reflow.eval`` does NOT execute
# them. Downstream callers that need the symbols must
# ``import adaptive_reflow.eval.mmff_conformer`` directly (or trigger
# the attribute access below).
#
# Why a module-level ``__getattr__`` rather than a per-call helper:
#   - PEP 562 ``__getattr__`` fires only on attribute access, so plain
#     ``import adaptive_reflow.eval`` never loads rdkit.
#   - Existing call sites that do ``from adaptive_reflow.eval import
#     embed_mmff`` continue to work: the ``__getattr__`` resolves the
#     attribute, importing the submodule on demand.
#   - The eager ``from .mmff_conformer import ...`` form (used before
#     Wave 15 C) is replaced by lazy loaders, removing the
#     ``rdkit-not-installed`` import error that previously surfaced in
#     ``adaptive_reflow.theory.checkers``.
# ---------------------------------------------------------------------------

_RDKIT_LAZY_MODULES: dict[str, str] = {
    "DEFAULT_MMFF_MAX_ITERS": "mmff_conformer",
    "DEFAULT_NUM_CONFS": "mmff_conformer",
    "DEFAULT_RANDOM_SEED": "mmff_conformer",
    "MMFF_CONFORMER_FAILURE": "mmff_conformer",
    "embed_mmff": "mmff_conformer",
    "embed_mmff_smiles": "mmff_conformer",
    "DEFAULT_REFERENCE_PATH": "fg_deviation",
    "DUNDEE_FR_SMARTS_NAMES": "fg_deviation",
    "compute_flowmol3_fg_deviation": "fg_deviation",
    "count_fg_hits": "fg_deviation",
    "dundee_smarts_dict": "fg_deviation",
    "fg_deviation_l1": "fg_deviation",
    "glaxo_smarts_dict": "fg_deviation",
    "fg_deviation_eq4": "flowmol3_eq4_fg_deviation",
    "RDKIT_AUDIT_REASON": "rdkit_oracle",
    "RDKIT_BUNDLE_ID_PREFIX": "rdkit_oracle",
    "RDKitOracle": "rdkit_oracle",
    "SyntheticEvaluator": "rdkit_oracle",  # only if re-exported; see below
}


def __getattr__(name: str):  # PEP 562 lazy loader
    """Lazily import rdkit-dependent submodules on first attribute access.

    Triggered when ``from adaptive_reflow.eval import X`` (or
    ``adaptive_reflow.eval.X``) is used and ``X`` is a symbol that
    lives in one of the rdkit-pulling submodules. Without this hook,
    importing the package would unconditionally pull rdkit, which is
    not vendored in every sandbox (this is the root cause of the
    Wave 14 A importlib bypass in :mod:`theory.checkers`).
    """
    mod_name = _RDKIT_LAZY_MODULES.get(name)
    if mod_name is None:
        raise AttributeError(
            f"module 'adaptive_reflow.eval' has no attribute {name!r}"
        )
    import importlib

    full = f"adaptive_reflow.eval.{mod_name}"
    mod = importlib.import_module(full)
    value = getattr(mod, name)
    globals()[name] = value  # cache for subsequent accesses
    return value


def __dir__() -> list[str]:  # PEP 562 dir() support
    return sorted(set(globals().keys()) | _RDKIT_LAZY_MODULES.keys())
