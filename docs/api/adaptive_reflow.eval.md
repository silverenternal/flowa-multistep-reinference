# `adaptive_reflow.eval`

DTB-R7 (calibration + paired evaluation + manifest I/O) and DTB-R8
(claim gate + promotion + rollback + layered metric panel).

The page below drills into each split file inside the `eval`
subpackage rather than stopping at the top-level `__init__.py`
re-exports, so internal symbols (calibration buckets, claim-gate
config dataclasses, metric-panel tier constants) that are not
re-exported publicly still show up in the rendered reference.

## `adaptive_reflow.eval.calibration`

DTB-R7 calibration: `BucketKey`, `CalibrationBucket`,
`CalibrationManifest`, `wilson_lower_bound`, `beta_lower_bound`,
`classify_bucket`, `manifest_digest`.

::: adaptive_reflow.eval.calibration
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.manifests`

Calibration manifest I/O -- `read_calibration_manifest`,
`write_calibration_manifest`, `frozen_manifest_hash`,
`validate_manifest_frozen`, `DEFERRED_GPU_SENTINEL`.

::: adaptive_reflow.eval.manifests
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.claim_gate`

DTB-R8 claim gate -- `ClaimGateConfig`, `ClaimGateDecision`,
`ClaimGateEvaluation`, `build_default_claim_gate_config`,
`evaluate_claim_gate`, `DEFERRED_R8_REASON`.

::: adaptive_reflow.eval.claim_gate
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.promotion`

DTB-R8 promotion -- `PromotionDecision`, `PromotionRecord`,
`evaluate_promotion`, `apply_promotion`.

::: adaptive_reflow.eval.promotion
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.rollback`

DTB-R8 rollback -- `RollbackDecision`, `RollbackRecord`,
`evaluate_rollback`, `apply_rollback`.

::: adaptive_reflow.eval.rollback
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.metric_panel`

Layered metric panel -- `LayeredMetricPanel`,
`LayeredEvidenceTiers`, `build_default_layered_metric_panel`,
`enforce_separation`.

::: adaptive_reflow.eval.metric_panel
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.protocol`

Paired-evaluation protocol -- shared dataclasses / sentinels used by
`eval.calibration` + `eval.promotion` + `eval.rollback`.

::: adaptive_reflow.eval.protocol
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.synthetic_oracle`

The synthetic evaluator oracle used by the DTB-R7 paired evaluation
harness. Stays in-tree (rather than `tests/`) so external parity
harnesses can import it.

::: adaptive_reflow.eval.synthetic_oracle
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.rdkit_oracle`

The RDKit-backed evaluator oracle. Opt-in via the `[chemistry]`
extra dependency (`rdkit>=2024.3.1`).

::: adaptive_reflow.eval.rdkit_oracle
    options:
      members: true
      show_source: true

## `adaptive_reflow.eval.twodim_fm_evaluator`

The 2D rectified-flow evaluator. Opt-in via the `[flow_matching]`
extra dependency (`numpy>=2.0,<2.5`, `scipy>=1.10`).

::: adaptive_reflow.eval.twodim_fm_evaluator
    options:
      members: true
      show_source: true