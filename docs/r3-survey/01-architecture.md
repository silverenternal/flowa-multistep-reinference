# Architecture Inventory — `flowa-multistep-reinference`

Working directory: `c:/Users/31472/codes/flowa-multistep-reinference`
Survey date: 2026-08-29
Scope: every Python module under `adaptive_reflow/`, every Protocol, every registry, every documented feedback loop, every load-bearing invariant, and every smell that survives verification.

This file is the survey artifact. The companion governance doc is
[`ARCHITECTURE.md`](../../ARCHITECTURE.md) (now) and the historical planning
artefacts [`ARCHITECTURE_PLAN.md`](../../ARCHITECTURE_PLAN.md),
[`FILE_MAPPING.md`](../../FILE_MAPPING.md). The architectural decisions
that pin the package shape live under [`../../docs/adr/`](../../docs/adr/).

---

## 1. Module inventory

Every module under `adaptive_reflow/` with file path, line range, and one-line
purpose. Total file count: **96 Python source files** under `adaptive_reflow/`
(94 modules + 2 `__pycache__` matches excluded by the survey grep — the actual
`.py` count is 95 source files including `data/__init__.py`).

### 1.1 `adaptive_reflow/contracts/` (leaf; stdlib-only)

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/contracts/__init__.py` | 1–225+ | Curated public surface: §1–§8 frozen dataclasses, hash helpers, NewTypes, validators. Lazy re-exports of `RoundResultBundle` / `validate_round_result_bundle` from `molecular.bundle` to break the import cycle. |
| `adaptive_reflow/contracts/archive.py` | 1–149 | DTB-R4: `ArchiveQuota`, `ArchiveAuditTrail`, `validate_archive_quota`. |
| `adaptive_reflow/contracts/audit.py` | 1–253 | Typed `AuditCode` + chain validators (`coerce_audit_code`, `coerce_audit_codes`, `validate_audit_code`, `validate_audit_chain`, `make_audit_code`). |
| `adaptive_reflow/contracts/authority.py` | 1–120 | DTB-S1: `RestartPolicyAuthorityContract`, `LegacyCompatibilityWindow`, `FinalRestartPolicy`, `validate_final_restart_policy`. |
| `adaptive_reflow/contracts/bundle.py` | 1–278 | DTB-R1: `ChannelTransferEvidence`, `ChannelTransferDecision`, `DynamicRestartTransferLedger`, `NoiseBiasInputRow`, `ChannelRuleInputs`, `ChannelRuleOutputs`, `validate_channel_evidence`. Lazy re-exports of `RoundResultBundle` from `molecular.bundle`. |
| `adaptive_reflow/contracts/decision.py` | (file exists) | Reserved for future DTB-R2/R8 decision-shape additions; intentionally empty. |
| `adaptive_reflow/contracts/envelope.py` | (file exists) | DTB-NC1/NC2: `EnvelopeLayer`, `FrozenEnvelopeManifest`, `EnvelopeClassification`, `TailBudgetRow`, validators. |
| `adaptive_reflow/contracts/hashes.py` | 1–170 | Deterministic sha256 helpers + canonical-JSON helpers (`hash_artifact`, `hash_bundle_id`, `hash_trace_digest`, `hash_phase_state_digest`, `hash_policy_hash`). |
| `adaptive_reflow/contracts/operations.py` | 1–50 | DTB-L2: `OperationCompositionContract`, `CommutatorResidualDiagnostic`. |
| `adaptive_reflow/contracts/paper_quantities.py` | 1–511 | Paper Lemma 2 / Lemma 3 / Lemma 5 / Proposition 3 evidence quantities: `sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C`, `exterior_gap_e_rho` plus `*_with_result` wrapper dataclasses. |
| `adaptive_reflow/contracts/phase.py` | 1–150 | DTB-L1: `PhaseState`, `empty_provenance`, `make_default_phase_state`, `make_default_phase_state_digest`, `validate_phase_state`. |
| `adaptive_reflow/contracts/schedule.py` | (file exists) | DTB-NA1: `CosineScheduleConfig`, `CosineScheduleSample`, `FreshNoiseFloor`, `RestartTriggerEvent`. |
| `adaptive_reflow/contracts/types.py` | 1–130 | NewType aliases (`ChannelName`, `ArtifactHash`, `FactorValue`, ...) + literal-set constants (`CHANNEL_NAMES`, `COMPLEMENT_BLOCKER_CODES`, `RESTART_TRIGGER_CODES`, `FEEDBACK_MODES`, `SCHEDULE_FAMILIES`, `SCHEDULE_PHASES`, `AUTHORITY_MODES`, `OPERATION_STEPS`, `DEFAULT_OPERATION_ORDER`, `FRESH_NOISE_FLOOR_SOURCES`). |
| `adaptive_reflow/contracts/validators.py` | 1–100 | `ValidationResult`, `_ok`, `_err`, `validate_unit_float`, `validate_unit_factor`, `validate_positive_int`, `validate_nonneg_int`, plus the `AUDIT_SOURCE_REVOKED` audit-code constant (DTB-R0 §3 case 5). |

### 1.2 `adaptive_reflow/universal/` (model-family-agnostic kernel; stdlib-only)

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/universal/__init__.py` | (file exists) | Re-exports the universal Protocols + carriers + validators; canonical home for `FlowMatchingODEAdapter`, `RestartMixer`, `EnvelopeCriterion`, `Evaluator`. |
| `adaptive_reflow/universal/adapter.py` | 1–320 | `CapabilityMissingError`, `CapabilityMismatchError`, `AdapterCapabilities`, `validate_capabilities`, `FlowMatchingODEAdapter` Protocol. |
| `adaptive_reflow/universal/envelope.py` | 1–160 | `EnvelopeCriterion` Protocol + `EnvelopeClassification` carrier + validators. |
| `adaptive_reflow/universal/evaluator.py` | 1–100 | `Evaluator` Protocol + `ArtifactHash` carrier + `validate_evaluator_artifact_hash`. |
| `adaptive_reflow/universal/mixer.py` | 1–230 | `RestartMixer` Protocol + `validate_blend_inputs` + the three concrete reference mixers: `NoOpMixer`, `LatentConvexMixer`, `DiscreteIdentityMixer`. |
| `adaptive_reflow/universal/mixer_ot.py` | 1–320 | OT-flavoured mixers + helpers (`rms`, `displacement_scale`, `ot_blend_weights`, `displacement_blend`, `OTLatentConvexMixer`, `PerChannelRmsMixer`). |
| `adaptive_reflow/universal/state.py` | 1–300 | `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace`, `NORMALIZATION_KINDS`, `REFERENCE_FRAMES`, `ChannelName`, `TensorRef` + validators. |
| `adaptive_reflow/universal/validators.py` | (file exists) | Single entry point for universal numeric validators (re-export wrapper). |

### 1.3 `adaptive_reflow/molecular/` (concrete pocket-3D FM implementation of universal Protocols)

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/molecular/__init__.py` | 1–270 | Re-exports molecule channel vocabulary + concrete universal-Protocol impls + `to_molecule_bundle`, `from_molecule_bundle`, `is_compatible` helpers. |
| `adaptive_reflow/molecular/bundle.py` | 1–350 | `MoleculeRoundResultBundle` (canonical home of the molecule-aware atomic bundle) + `validate_molecule_round_result_bundle` + `attach_molecule_channels`. |
| `adaptive_reflow/molecular/calibration_protocols.py` | 1–400 | Four concrete `Evaluator` Protocol impls: `GNINAEvaluator`, `PoseBustersEvaluator`, `QEDEvaluator`, `ADMETEvaluator` (the `gnina_evaluator`, `posebusters_evaluator`, `qed_evaluator`, `admet_evaluator` factories + the `adaptive_reflow_external_metric_controls` shim). |
| `adaptive_reflow/molecular/channels.py` | 1–130 | Molecule channel vocabulary: `MoleculeChannel` (StrEnum) + four `*ChannelRef` NewType aliases. |
| `adaptive_reflow/molecular/domain.py` | (file exists) | `MOLECULE_DOMAIN_BY_CHANNEL` fallback domain table. |
| `adaptive_reflow/molecular/envelope.py` | 1–220 | Molecule envelope: `MoleculeEnvelopeLayer`, `MoleculeEnvelopeManifest`, `MoleculeEnvelopeClassification`, `MoleculeTailBudgetRow` + validators (implements universal `EnvelopeCriterion`). |
| `adaptive_reflow/molecular/mixer.py` | 1–380 | `EqualRmsCoordinateMixer` (canonical) + `RMSPreservingCoordinateMixer` (deprecated back-compat alias) + `adaptive_reflow_memory_restart_coords` free function + `_require_equal_rms` helper + `MIXER_RMS_PRECEDENCE_FAIL` audit code. |
| `adaptive_reflow/molecular/stratification.py` | 1–300 | `MoleculeStratum` (Enum), `MoleculeStratumAssignment`, `dominance_ratio`, `cross_stratum_mix_rejected`, `_bundle_disagrees`. |

### 1.4 `adaptive_reflow/frame/` (the universal round frame)

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/frame/__init__.py` | 1–148 | Re-exports the engine, bounded merge, channel rule, operation order, phase runtime, trace v3, orchestrator, stage. |
| `adaptive_reflow/frame/adapter.py` | 1–78 | DTB-G1 re-export shim — `FlowMatchingODEAdapter`, `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace`, `AdapterCapabilities`, `TensorRef`, validators, `DOMAIN_BY_CHANNEL`, `NORMALIZATION_KINDS`, `REFERENCE_FRAMES`. (Thin shim over `universal/`) |
| `adaptive_reflow/frame/channel_rule.py` | 1–702 | DTB-R2: `compute_channel_decision`, `check_monotonicity_property`, blocker codes (`BLOCKER_TAIL_INADMISSIBLE` through `BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL`), `CANONICAL_FACTOR_ORDER`, `_classify_failed_factor`, `_compute_evidence_score`, `_bounded_target_fraction`, `_stability_floor_breached`, `_build_stability_collapse_outputs`. |
| `adaptive_reflow/frame/channel_rule_diagnostics.py` | 1–519 | `MonotonicityViolation`, `MonotonicityReport`, `sweep_grid`, `certify_monotonicity`, `certify_all_factors`, `evidence_cross_channel`, `certify_cross_channel` (off-line channel-rule sweep tooling). |
| `adaptive_reflow/frame/engine.py` | 1–1703 | DTB-G1: `Engine` (seven-step `run_round`), `EngineRoundResult`, `RoundTrace`, `LedgerRow`, engine-level `PhaseState`, `build_ledger_row`, `verify_ledger_chain`, `compute_ledger_row_hash`, `_safe_adapter_call`, `_policy_with_schedule_beta`, all `ERR_*` constants, `FEATURE_FLAG_KEY`, `ENGINE_VERSION`, `DEFAULT_OPERATION_STEPS`. |
| `adaptive_reflow/frame/ledger_chain.py` | 1–336 | `LedgerChain` incremental verifier, `ChainVerification` result, `ParallelLedgerChain`, `verify_ledger_chain_incremental`. |
| `adaptive_reflow/frame/merge.py` | 1–420 | DTB-R3: `bounded_merge`, `bounded_merge_with_schedule`, `_delta_caps_for_channel`, `_floor_for_channel`, `_cap_for_channel`, `MergeAuthorityError`, schema constants. |
| `adaptive_reflow/frame/operation.py` | 1–364 | DTB-L2 runtime: `build_default_composition_contract`, `validate_operation_order`, `record_commutator_residual`, `replay_default_order`, `DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE`, `DEFAULT_OPERATION_COMPOSITION_VERSION`. |
| `adaptive_reflow/frame/orchestrator.py` | 1–1158 | DTB-S1: `AdaptiveReflowPolicyOrchestrator` + `PolicyOrchestratorError` + `PolicyOrchestratorValidationError` + `_LedgerRecord` + `last_emitted: dict[ChannelName, FactorValue]` invariant. |
| `adaptive_reflow/frame/phase.py` | 1–552 | DTB-L1 runtime: `_infer_schedule_phase`, `build_phase_state`, `advance_phase`, `make_default_phase_state` (run_id_seed-taking convenience), `validate_phase_state_transition`. |
| `adaptive_reflow/frame/stage.py` | 1–306 | Pipeline composition: `StageProtocol`, `RunStage`, `CalibrationStage`, `ClaimGateStage`, `PromotionStage`, `Stage` ABC, `STAGE_REGISTRY`, `build_stage`. |
| `adaptive_reflow/frame/trace.py` | 1–380 | DTB-R5: `RoundTraceV3`, `compute_round_trace_v3_content_hash`, `freeze_round_trace_v3`, `round_trip_round_trace_v3`, `read_round_trace_v2`, `FINAL_POLICY_WRITER_ADAPTIVE_REFLOW`, `FINAL_POLICY_WRITER_LEGACY_NOISE_BIAS`. |

### 1.5 `adaptive_reflow/algorithm/` (abstract algorithm layer + outer runner)

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/algorithm/__init__.py` | 1–230 | Re-exports every algorithm-layer class, audit code, registry, factory, and family constant. |
| `adaptive_reflow/algorithm/batched_runner.py` | 1–949 | `BatchedTrajectoryRunner`, `BatchedRunnerConfig`, `BatchedTrajectoryResult`, `_BatchedAdapterProtocol`, `BatchedVectorisedAdapterProtocol` + `_stable`/`_w2_to_mode_centres`/`_reshape_round_endpoints`/`_evaluate_selection_ratio_for_round` helpers. |
| `adaptive_reflow/algorithm/blender.py` | 1–749 | `RestartBlenderProtocol`, `LinearBlender`, `DistanceDecayBlender`, `default_blender`, `_linear_blend_arrays`, `_sigmoid`, `_distance`, `_make_blend_bundle`, family constants (`LINEAR_FAMILY`, `DISTANCE_DECAY_FAMILY`, `DEFAULT_LINEAR_CONFIG_HASH`, `DEFAULT_DISTANCE_DECAY_CONFIG_HASH`, `DEFAULT_DISTANCE_DECAY_TEMPERATURE`). |
| `adaptive_reflow/algorithm/blender_extra.py` | 1–486 | Extra blender families: `OTLinearBlender`, `MultiTemperatureDistanceDecayBlender`, `JointOTLinearBlender`, `BarycentricBlender`. |
| `adaptive_reflow/algorithm/evidence_driver.py` | 1–407 | `EvidenceDrivenScheduler`, `EvidenceModeReport`, `check_evidence_mode`, `warn_if_heuristic_evidence_mode` (diagnostic coverage). |
| `adaptive_reflow/algorithm/handoff.py` | 1–261 | `HandoffSequentialScheduler` (subclass of `SequentialScheduler`) + `_validate_handoff_window` + `_dispatch_to_sub`. |
| `adaptive_reflow/algorithm/merge_operator.py` | 1–843 | `MergeOperatorProtocol`, `BoundedMergeOperator`, `IdentityOperator`, `EMAOperator`, `default_bounded_merge_operator`, `_coerce_finite_real`, `_coerce_unit_real`, `MergeAuthorityError`, all `MERGE_*` audit codes. |
| `adaptive_reflow/algorithm/merge_operator_extra.py` | 1–801 | Extra merge operators: `KalmanBoundedMergeOperator`, `BayesianMergeOperator`, `PIDIdentityOperator`, `ScheduleAwareEMAOperator`, `MultiSourceKalmanMergeOperator`. |
| `adaptive_reflow/algorithm/merge_r2.py` | 1–276 | R2-variant scheduler/merge operators: `MultiSourceKalmanMergeOperator` (duplicate definition — see §Smells), `bayesian_effective_count_schedule`. |
| `adaptive_reflow/algorithm/policy_driver.py` | 1–1122 | `PolicyDriverProtocol`, `ScheduleDerivedPolicyDriver`, `ConstantPolicyDriver`, `AdaptivePolicyDriver`, `MultiChannelConstantPolicyDriver`, `DualTargetAdaptivePolicyDriver`, `default_policy_driver`, `_override_beta_by_channel`, family constants (`ADAPTIVE_FAMILY`, `CONSTANT_FAMILY`, `SCHEDULE_DERIVED_FAMILY`). |
| `adaptive_reflow/algorithm/protocol_registry.py` | 1–437 | Central registry for every pluggable Protocol: `PROTOCOL_REGISTRY`, `SCHEDULER_FAMILIES`, `POLICY_DRIVER_FAMILIES`, `MERGE_OPERATOR_FAMILIES`, `BLENDER_FAMILIES`, `ProtocolRegistryError`, `validate_config_schema`, four `build_*_from_config` factories, `enumerate_implementations`, `registered_families`. |
| `adaptive_reflow/algorithm/rotation_policy.py` | 1–224 | `RotationPolicy` (Protocol) + `RoundRobinRotationPolicy` + `BanditUCBRotationPolicy` + `ROTATION_POLICY_REGISTRY` + `build_rotation_policy`. |
| `adaptive_reflow/algorithm/round2_extra.py` | 1–428 | R2-variant schedulers/policy drivers: `MultiChannelJitteredConstantScheduler` (duplicate), `MultiChannelConstantPolicyDriver` (duplicate), `DualTargetAdaptivePolicyDriver` (duplicate). |
| `adaptive_reflow/algorithm/runner.py` | 1–937 | `_EvaluatorProtocol`, `ReInferenceConfig`, `ReInferenceResult`, `ReInferenceRunner`, `FORWARD_NOISE_INJECTED` audit code, `_build_base_policy`, `_build_condition_delta`, `_build_initial_phase_state`, `_algorithm_signatures`. |
| `adaptive_reflow/algorithm/runner_registry.py` | 1–368 | `RunnerProtocol`, `ParallelRunner`, `EarlyStopRunner`, `OnlineRunner`, `ReInferenceRunnerFamily`, `BatchedTrajectoryRunnerFamily`, `RUNNER_REGISTRY`, `build_runner`. |
| `adaptive_reflow/algorithm/scheduler.py` | 1–3119 | `ScheduleSample`, `ScheduleSampleProtocol`, `SchedulerProtocol`, `CosineAnnealScheduler`, `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler`, `ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler`, `default_cosine_scheduler`, `_paper_evidence_balance`, `_codimension_sheet_factory`, `_sequential_factory`, `SCHEDULER_REGISTRY`, `_register_extra_scheduler_families`, `build_scheduler`, `build_scheduler_from_config`. |
| `adaptive_reflow/algorithm/scheduler_extra.py` | 1–1250 | Extra scheduler families: `EDMScheduler`, `AdaptivePIDScheduler`, `JitteredConstantScheduler`, `MultiChannelJitteredConstantScheduler` + `EDM_RHO_DEFAULT`, `EDM_SIGMA_MAX_DEFAULT`, `EDM_SIGMA_MIN_DEFAULT`. |
| `adaptive_reflow/algorithm/scheduler_r2.py` | 1–273 | R2-variant: `MultiChannelJitteredConstantScheduler` (duplicate definition — see §Smells). |
| `adaptive_reflow/algorithm/sequential.py` | 1–521 | `SequentialSlot`, `SequentialScheduler`, `_validate_positive_int`, `_dispatch_scheduler_config`, `SEQUENTIAL_FAMILY`. |
| `adaptive_reflow/algorithm/sequential_handoff.py` | 1–272 | `HandoffSequentialScheduler` (subclass of `SequentialScheduler`) + `_blend_n_cap` (alternative implementation of `HandoffSequentialScheduler`). |

### 1.6 `adaptive_reflow/writer/` (single-writer authority + registry + audit + handoff)

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/writer/__init__.py` | (file exists) | Re-exports authority + handoff + registry + audit types + functions. |
| `adaptive_reflow/writer/audit.py` | 1–230 | `AuditTemplate`, `DEFAULT_AUDIT_TEMPLATE`, `_paper_date_ok`, `_commit_is_hex_40`, `_has_detach_signal`, `validate_audit_completeness`, `render_audit_checklist`, `registry_summary`. |
| `adaptive_reflow/writer/authority.py` | 1–800 | `WriterArgumentError`, `WriterArbitrator`, `build_default_authority_contract`, `build_final_restart_policy`, `verify_policy_against_ledger`, `_validate_unit_factor`, `_coerce_mechanism_id`, `REQUEST_MODES`, `EXECUTABLE_WRITER_MECHANISM_ID`, `CONSUMER_WRITER_ID`, `DEFAULT_AUTHORITY_CONTRACT_VERSION`, `DEFAULT_MODE_FLAGS`, `DIAGNOSTIC_WRITER_MECHANISM_ID`, `ERR_DUAL_EXECUTABLE`, `LEGACY_SCHEMA_READ_COMPATIBILITY_VERSION`. |
| `adaptive_reflow/writer/handoff.py` | 1–240 | `CoreRuntimeHandoffError`, `CoreRuntimeHandoff`, `build_core_runtime_handoff`, `write_handoff_spec`, `_require_non_empty`, `_coerce_target_tests`, `CORE_RUNTIME_HANDBOFF_SCHEMA_NAME`, `CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION`, `CORE_RUNTIME_OWNER`. |
| `adaptive_reflow/writer/registry.py` | 1–350 | DTB-G2: `CandidateEntry`, `CandidateRegistry`, `_registry_hash`, `admit_entry`, `make_initial_registry`, `make_default_flowmol3_entry`, `default_registry`, `FLOWMOL3_PINNED_COMMIT`, `TaskCondition`, `AdapterStatus`. |

### 1.7 `adaptive_reflow/policy/` (pure decision logic)

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/policy/__init__.py` | 1–100 | Re-exports all pure decision-logic types + functions. Lazy `__getattr__` shim for `AUDIT_STABILITY_COLLAPSE`/`AUDIT_SOURCE_REVOKED` cross-re-exports. |
| `adaptive_reflow/policy/archive.py` | 1–290 | DTB-R4: `SameSampleArchive`, `ArchiveEntry`, `CandidateArchiveError` family, `_safe_factor`, `_validate_quota`, `_check_lineage`, `_entry_sort_key`, `_archive_audit_hash`, `_ArchiveStats`. |
| `adaptive_reflow/policy/noise_mass.py` | 1–370 | DTB-L4 calc: `physical_noise_proxy`, `RMS_preserving_mixing_coefficient`, `exact_spectral_variance`, `ThreeWayDistinction`, `adversarial_stagnation_test`, `ERR_PROXY_INPUT_INVALID`, `ERR_BETA_INPUT_INVALID`, `ERR_SPECTRAL_INPUT_INVALID`, `ERR_CURVE_NOT_SEQUENCE`, `ERR_CURVE_ENTRY_NOT_FINITE`. |
| `adaptive_reflow/policy/pruning.py` | 1–350 | DTB-L3: `PruneGate`, `UnorderedAuditResult`, `PruneDecision`, `_lex_key`. |
| `adaptive_reflow/policy/stratification.py` | (file exists) | DTB-L3: `Stratum`, `StratumAssignment`, `dominance_ratio`, `cross_stratum_mix_rejected`. |

### 1.8 `adaptive_reflow/schedule/`, `adaptive_reflow/diagnostics/`, `adaptive_reflow/envelope/`

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/schedule/__init__.py` | (file exists) | Re-exports `CosineScheduleSampler`, `n_cap_for_round`, `validate_cosine_schedule_config`, `default_floor_by_channel`, `build_fresh_noise_diagnostics`. |
| `adaptive_reflow/schedule/cosine.py` | 1–900+ | DTB-NA1: `n_cap_for_round`, `memory_fraction_from_schedule`, `validate_cosine_schedule_config`, `default_floor_by_channel`, `CosineScheduleSampler`, `build_fresh_noise_diagnostics`, all `ERR_*` constants. |
| `adaptive_reflow/diagnostics/__init__.py` | (file exists) | Re-exports observation-only ledger types + validators + `empty_diagnostics`. |
| `adaptive_reflow/diagnostics/ledger.py` | 1–450 | `FreshNoiseCumulativeMassRecord`, `SpectralResidualBandProxy`, `TailDiagnosticStatus`, validators, `empty_diagnostics`, all `ERR_*` constants. |
| `adaptive_reflow/envelope/__init__.py` | (file exists) | Re-exports `FrozenEnvelopeManifestBuilder`, `TailBudgetAccumulator`, `classify_endpoint`, `EvidenceRowHash`, `StratifiedTailBudgetRow`, `ManifestBuildError`. |
| `adaptive_reflow/envelope/classifier.py` | 1–200 | `OBS_*` observable key constants + `_read_observables`, `_within_layer`, `_classify_blocker`. |
| `adaptive_reflow/envelope/manifest.py` | 1–620 | `FrozenEnvelopeManifestBuilder`, `classify_endpoint`, `TailBudgetAccumulator`, `StratifiedTailBudgetRow`, `ManifestBuildError`. |
| `adaptive_reflow/envelope/tail_budget.py` | (file exists) | Tail-budget-only code (`EvidenceRowHash`). |

### 1.9 `adaptive_reflow/eval/`, `adaptive_reflow/adapters/`, `adaptive_reflow/legacy/`, `adaptive_reflow/data/`

| Module | Range | One-line purpose |
|---|---|---|
| `adaptive_reflow/eval/__init__.py` | (file exists) | Re-exports all DTB-R7/R8 types + functions. |
| `adaptive_reflow/eval/calibration.py` | 1–480 | DTB-R7 CPU: `wilson_lower_bound`, `beta_lower_bound`, `CalibrationTimeSplit`, `CalibrationBucket`, `CalibrationManifest`, `StabilityPerturbationProtocol`, `classify_bucket`, `manifest_digest`. |
| `adaptive_reflow/eval/calibration_cdf.py` | 1–230 | `ProportionInterval`, `regularized_incomplete_beta`, `binomial_cdf`, `binomial_sf`, `wilson_ci`, `clopper_pearson_ci`. |
| `adaptive_reflow/eval/claim_gate.py` | 1–430 | `ClaimGateArgumentError`, `ClaimGateConfig`, `ClaimGateEvaluation`, `build_default_claim_gate_config`, `_resolve_decision`, `evaluate_claim_gate`, `DEFERRED_R8_REASON`. |
| `adaptive_reflow/eval/coverage.py` | 1–290 | `weighted_coverage_score`, `EnergyDistanceEstimate`, `energy_distance_point`, `energy_distance_with_ci`, `_mean_pairwise`. |
| `adaptive_reflow/eval/coverage_extra.py` | 1–380 | `_silverman_bandwidth`, `support_coverage_score`, `_knn_entropy`, `top_k_coverage_with_entropy`, `W2BarycenterCoverage`, `_coverage_callable`. |
| `adaptive_reflow/eval/coverage_r2.py` | 1–500 | `CoverageFamily`, `support_coverage_score`, `TopKEntropyEstimate`, `_knn_entropy`, `top_k_coverage_with_entropy`, `W2BarycenterCoverage`. |
| `adaptive_reflow/eval/lipschitz_diagnostic.py` | 1–360 | `lipschitz_modulus`, `LipschitzConvergenceReport`, `evaluate_lipschitz_convergence`, `bounded_lipschitz_distance`, `KernelLipschitzReport`, `kernel_lipschitz_constant`. |
| `adaptive_reflow/eval/manifests.py` | 1–430 | `DEFERRED_GPU_SENTINEL`, `_ok`, `_err`, `write_calibration_manifest`, `read_calibration_manifest`, `validate_manifest_frozen`, `frozen_manifest_hash`. |
| `adaptive_reflow/eval/metric_panel.py` | 1–360 | `LayeredMetricPanelArgumentError`, `LayeredMetricPanel`, `SoftLayeredMetricPanel`, `_tier_keys`, `enforce_separation`, `build_default_layered_metric_panel`, `build_soft_layered_metric_panel`. |
| `adaptive_reflow/eval/posterior_selection_evaluator.py` | 1–1030+ | Paper-quantity-driven evaluation: `mode_centers_for`, `sheet_cell_centers`, `sheet_evidence`, `cell_evidence`, `selection_ratio`, `EvidenceScaleGapMetric` (paper Theorem 1 witness). |
| `adaptive_reflow/eval/promotion.py` | 1–450 | `PromotionArgumentError`, `PromotionReport`, `build_deferred_promotion_report`, `PolicyVersionHashRecorder`, `derive_policy_hash_from_version`, `DEFERRED_COST`, `DEFERRED_GAIN`, `DEFERRED_R8_REASON`. |
| `adaptive_reflow/eval/protocol.py` | 1–600 | `PairedComparisonArm`, `PairedComparisonRegistry`, `EvaluatorProvenanceGuard`, `evaluator_guard_digest`, `RoundToRoundOscillationDetector`, `CUSUMOscillationDetector`, `BayesianChangePointDetector`. |
| `adaptive_reflow/eval/rdkit_oracle.py` | 1–330 | RDKit-backed oracle: `RdkitEvaluator`, `_compute_qed`, `_compute_sa`, `_compute_logp`, `_bounded_score_for`, `_audit_reason_for`, `_CHANNEL_TO_COMPUTE`. |
| `adaptive_reflow/eval/rollback.py` | 1–250 | `RollbackArgumentError`, `RollbackFlag`, `RollbackAudit`, `apply_rollback`, `build_disabled_rollback_flag`, `DEFAULT_DISABLED_REASON`. |
| `adaptive_reflow/eval/synthetic_oracle.py` | 1–390 | CPU-only deterministic oracle: `SyntheticEvaluator`, `_digest_uint64`, `_normalise_uint32`, `_rescale_to_range`, `_clip_unit`. |
| `adaptive_reflow/eval/twodim_fm_evaluator.py` | 1–611 | 2-D flow-matching oracle: `TwoDimFMEvaluator`, `analytic_samples`, `voronoi_grid`, `coverage_score`, `energy_distance`, `_sampler_for`, `_mode_centers_for`. |
| `adaptive_reflow/eval/w2.py` | 1–1140 | `W2Family`, `W2EstimatorProtocol`, `ModeCentreMSEW2`, `ProjectionFreeExactW2`, `KernelizedW2`, `SinkhornApproximatedW2`, `ProjectionFreeRademacherW2`, `TreeSlicedW2`, `W2Barycenter`, `build_w2_estimator`, `compute_w2`. |
| `adaptive_reflow/adapters/__init__.py` | (file exists) | Re-exports concrete adapter classes + channel constants. |
| `adaptive_reflow/adapters/flowmol3.py` | 1–200 | `FlowMol3Adapter`, `FlowMol3Capabilities`, `default_flowmol3_adapter`, `flowmol3_registry_entry`, `FLOWMOL3_CHANNELS`. |
| `adaptive_reflow/adapters/integrators.py` | 1–100 | Thin wrappers around ODE integrators (helper module). |
| `adaptive_reflow/adapters/karras_preconditioner.py` | 1–100 | Karras-style preconditioner helper. |
| `adaptive_reflow/adapters/reference_flowa.py` | 1–150 | `ReferenceFlowAAdapter` (placeholder / worked example) + `REFERENCE_FLOWA_CHANNELS`. |
| `adaptive_reflow/adapters/stochastic_fm.py` | 1–100 | Stochastic flow matching adapter skeleton. |
| `adaptive_reflow/adapters/synthetic.py` | 1–300 | `SyntheticContinuousAdapter`, `SyntheticDiscreteAdapter`, `SyntheticMixedChannelAdapter`, `SyntheticUnsupportedAdapter`, `ALL_SYNTHETIC_CHANNELS`, `CONTINUOUS_CHANNELS`, `DISCRETE_CHANNELS`, `MIXED_CHANNELS`. |
| `adaptive_reflow/adapters/toy_gaussian.py` | 1–250 | `ToyGaussianAdapter` — second-domain (non-molecular) `FlowMatchingODEAdapter` proof artifact (ADR-0003). |
| `adaptive_reflow/adapters/toy_linear.py` | 1–150 | `ToyLinearAdapter` — worked example / smallest eight-method `FlowMatchingODEAdapter`. |
| `adaptive_reflow/adapters/twodim_fm.py` | 1–250 | `TwoDimFMAdapter` — 2D 2-moons / 8-gaussians flow matching adapter. |
| `adaptive_reflow/adapters/twodim_fm_train.py` | 1–200 | Training-side companion for the 2-D flow matching adapter. |
| `adaptive_reflow/legacy/__init__.py` | (file exists) | Quarantine: emits `DeprecationWarning` on import; empty `__all__`. |
| `adaptive_reflow/legacy/control_policy.py` | 1–670 | Pre-refactor torch-bound control policy (`adaptive_reflow_external_metric_controls`, `adaptive_reflow_soft_closed_loop_controls`, `adaptive_reflow_metric_priority_controls`, ...). |
| `adaptive_reflow/legacy/loop.py` | 1–80 | `run_local_loop`. |
| `adaptive_reflow/legacy/loop_contract.py` | 1–30 | `build_loop_contract`. |
| `adaptive_reflow/legacy/mechanism_adapter.py` | 1–350 | `AdaptiveReflowMechanism`, `_finite_float_control`. |
| `adaptive_reflow/legacy/metric_feedback.py` | 1–1000+ | `feedback_reason_tokens`, `ConditionPolicyParameters`, `condition_policy_parameters_from_feedback`, `adaptive_reflow_external_metric_controls`, `run_external_reflow_metric_feedback`. |
| `adaptive_reflow/legacy/orchestration.py` | 1–230 | `SCHEDULE_KEYS`, `prepare_outer_reflow_round`, `_route_merge`. |
| `adaptive_reflow/legacy/plan.py` | 1–650 | `ReInferenceRoundPlan`, `contains_true_metric_feedback`, `validate_true_metric_feedback_policy`, `metric_family_from_priority`, `metric_family_deficits`, `compare_reinference_difficulty_orders`, `build_reinference_round_plan`. |
| `adaptive_reflow/legacy/restart_mixer.py` | (file exists) | Quarantined restart-mixer (originally `restart_memory.py`). |
| `adaptive_reflow/legacy/services.py` | (file exists) | Pre-refactor services module. |
| `adaptive_reflow/data/__init__.py` | (file exists) | Curated public surface for target distributions. |
| `adaptive_reflow/data/target_distributions.py` | 1–300 | `sampler_for`, target-distribution samplers (`two_moons`, `eight_gaussians`, ...). |
| `adaptive_reflow/data/round2_targets.py` | 1–200 | R2 target-distribution fixtures. |

**Total source-file count under `adaptive_reflow/`:** 95 modules
(12 `__init__.py` + 83 concrete modules).

---

## 2. Protocol inventory

Every `Protocol` class declared under `adaptive_reflow/`, with method
signatures and the location of every concrete implementation.

### 2.1 `FlowMatchingODEAdapter` — `adaptive_reflow/universal/adapter.py:235`

```python
@runtime_checkable
class FlowMatchingODEAdapter(Protocol):
    def capabilities(self) -> AdapterCapabilities: ...
    def build_initial_state(
        self, batch_id: BatchId, sample_id: SampleId,
        *, source_round: int = 0,
    ) -> StateBundle: ...
    def export_endpoint(self, state: StateBundle) -> StateBundle: ...
    def detach_and_validate_endpoint(self, state: StateBundle) -> StateBundle: ...
    def apply_restart_distribution(
        self, state: StateBundle, policy: FinalRestartPolicy,
    ) -> StateBundle: ...
    def compose_condition(
        self, state: StateBundle, delta: ODEConditionDelta,
    ) -> StateBundle: ...
    def solve_ode(
        self, state: StateBundle, seed: int, *, steps: int = 1,
    ) -> StateBundle: ...
    def observe_endpoint(self, state: StateBundle) -> Any: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `ToyLinearAdapter` | `adaptive_reflow/adapters/toy_linear.py:33` |
| `ToyGaussianAdapter` | `adaptive_reflow/adapters/toy_gaussian.py:46` |
| `TwoDimFMAdapter` | `adaptive_reflow/adapters/twodim_fm.py:43` |
| `TwoDimFMTrainAdapter` | `adaptive_reflow/adapters/twodim_fm_train.py:48` |
| `StochasticFMAdapter` | `adaptive_reflow/adapters/stochastic_fm.py:46` |
| `SyntheticContinuousAdapter` | `adaptive_reflow/adapters/synthetic.py:46` |
| `SyntheticDiscreteAdapter` | `adaptive_reflow/adapters/synthetic.py:130` |
| `SyntheticMixedChannelAdapter` | `adaptive_reflow/adapters/synthetic.py:180` |
| `SyntheticUnsupportedAdapter` | `adaptive_reflow/adapters/synthetic.py:230` |
| `FlowMol3Adapter` | `adaptive_reflow/adapters/flowmol3.py:60` |
| `ReferenceFlowAAdapter` | `adaptive_reflow/adapters/reference_flowa.py:48` |
| `AdaptiveReflowMechanism` (legacy) | `adaptive_reflow/legacy/mechanism_adapter.py:29` |

### 2.2 `RestartMixer` — `adaptive_reflow/universal/mixer.py:66`

```python
@runtime_checkable
class RestartMixer(Protocol):
    def mix(
        self, memory: Any, restart: Any,
        *, tolerance: float = 1e-6,
    ) -> tuple[Any, Mapping[str, tuple[str, ...]]]: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `NoOpMixer` | `adaptive_reflow/universal/mixer.py:142` |
| `LatentConvexMixer` | `adaptive_reflow/universal/mixer.py:167` |
| `DiscreteIdentityMixer` | `adaptive_reflow/universal/mixer.py:207` |
| `OTLatentConvexMixer` | `adaptive_reflow/universal/mixer_ot.py:225` |
| `PerChannelRmsMixer` | `adaptive_reflow/universal/mixer_ot.py:274` |
| `EqualRmsCoordinateMixer` | `adaptive_reflow/molecular/mixer.py:307` |
| `RMSPreservingCoordinateMixer` (deprecated alias) | `adaptive_reflow/molecular/mixer.py:380` |

### 2.3 `EnvelopeCriterion` — `adaptive_reflow/universal/envelope.py:64`

```python
@runtime_checkable
class EnvelopeCriterion(Protocol):
    def evaluate(self, state: StateBundle) -> EnvelopeClassification: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `MoleculeEnvelopeLayer` (and `MoleculeEnvelopeManifest`) | `adaptive_reflow/molecular/envelope.py:62,94` |

### 2.4 `Evaluator` — `adaptive_reflow/universal/evaluator.py:53`

```python
@runtime_checkable
class Evaluator(Protocol):
    def evaluate(self, bundle: Any, channel: Any, seed: int) -> Any: ...
    def oracle(self, bundle: Any, channel: Any, seed: int) -> Any: ...  # duck-typed
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `_MoleculeTargetEvaluator` (base) | `adaptive_reflow/molecular/calibration_protocols.py:144` |
| `GNINAEvaluator` | `adaptive_reflow/molecular/calibration_protocols.py:247` |
| `PoseBustersEvaluator` | `adaptive_reflow/molecular/calibration_protocols.py:267` |
| `QEDEvaluator` | `adaptive_reflow/molecular/calibration_protocols.py:287` |
| `ADMETEvaluator` | `adaptive_reflow/molecular/calibration_protocols.py:307` |
| `SyntheticEvaluator` | `adaptive_reflow/eval/synthetic_oracle.py:173` |
| `TwoDimFMEvaluator` | `adaptive_reflow/eval/twodim_fm_evaluator.py:347` |
| `RdkitEvaluator` | `adaptive_reflow/eval/rdkit_oracle.py:314` |

### 2.5 `SchedulerProtocol` — `adaptive_reflow/algorithm/scheduler.py:155`

```python
@runtime_checkable
class SchedulerProtocol(Protocol):
    def sample(self, outer_cycle_id: int, round_in_cycle: int, target_round: int) -> ScheduleSample: ...
    def cycle_length(self) -> int: ...
    def schedule_family(self) -> str: ...
    def config_hash(self) -> str: ...
    def reset(self) -> None: ...
    def record_round_feedback(self, round_in_cycle: int, metrics: Mapping[str, float]) -> None: ...
    def inject_noise(
        self, state: NDArray[np.float64], schedule_sample: CosineScheduleSample,
        *, generator: np.random.Generator,
    ) -> NDArray[np.float64]: ...
    def to_config(self) -> dict[str, Any]: ...
    @classmethod
    def from_config(cls, config: dict[str, Any]) -> SchedulerProtocol: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `CosineAnnealScheduler` | `adaptive_reflow/algorithm/scheduler.py:275` |
| `ConstantScheduler` | `adaptive_reflow/algorithm/scheduler.py:556` |
| `LinearScheduler` | `adaptive_reflow/algorithm/scheduler.py:751` |
| `ExponentialScheduler` | `adaptive_reflow/algorithm/scheduler.py:962` |
| `PolynomialScheduler` | `adaptive_reflow/algorithm/scheduler.py:1184` |
| `SigmoidScheduler` | `adaptive_reflow/algorithm/scheduler.py:1422` |
| `ConvergenceAdaptiveScheduler` | `adaptive_reflow/algorithm/scheduler.py:1697` |
| `CodimensionSheetScheduler` | `adaptive_reflow/algorithm/scheduler.py:2256` |
| `EDMScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:58` |
| `AdaptivePIDScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:381` |
| `JitteredConstantScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:825` |
| `MultiChannelJitteredConstantScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:999` (canonical) — duplicate at `adaptive_reflow/algorithm/scheduler_r2.py:30` and `adaptive_reflow/algorithm/round2_extra.py:46` |
| `SequentialScheduler` | `adaptive_reflow/algorithm/sequential.py:95` |
| `HandoffSequentialScheduler` | `adaptive_reflow/algorithm/handoff.py:56` (also `adaptive_reflow/algorithm/sequential_handoff.py:50`) |
| `EvidenceDrivenScheduler` | `adaptive_reflow/algorithm/evidence_driver.py:93` |

### 2.6 `MergeOperatorProtocol` — `adaptive_reflow/algorithm/merge_operator.py:240`

```python
@runtime_checkable
class MergeOperatorProtocol(Protocol):
    def merge(
        self, *, prev: float, dynamic: float, cap: float, floor: float,
        delta_cap_up: float, delta_cap_down: float,
    ) -> tuple[float, tuple[str, ...]]: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `BoundedMergeOperator` | `adaptive_reflow/algorithm/merge_operator.py:359` |
| `IdentityOperator` | `adaptive_reflow/algorithm/merge_operator.py:622` |
| `EMAOperator` | `adaptive_reflow/algorithm/merge_operator.py:695` |
| `KalmanBoundedMergeOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:45` |
| `BayesianMergeOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:233` |
| `PIDIdentityOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:376` |
| `ScheduleAwareEMAOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:466` |
| `MultiSourceKalmanMergeOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:581` (canonical) — duplicate at `adaptive_reflow/algorithm/merge_r2.py:36` |

### 2.7 `PolicyDriverProtocol` — `adaptive_reflow/algorithm/policy_driver.py:181`

```python
@runtime_checkable
class PolicyDriverProtocol(Protocol):
    def compute_policy(
        self, schedule_sample: ScheduleSample, prev_policy: FinalRestartPolicy,
        endpoint_digest: str | None = None,
    ) -> FinalRestartPolicy: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `ScheduleDerivedPolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:292` |
| `ConstantPolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:409` |
| `AdaptivePolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:505` |
| `MultiChannelConstantPolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:918` (canonical) — duplicate at `adaptive_reflow/algorithm/round2_extra.py:233` |
| `DualTargetAdaptivePolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:1034` (canonical) — duplicate at `adaptive_reflow/algorithm/round2_extra.py:315` |

### 2.8 `RestartBlenderProtocol` — `adaptive_reflow/algorithm/blender.py:404`

```python
@runtime_checkable
class RestartBlenderProtocol(Protocol):
    def blend(
        self, *, memory: Any, fresh: Any, fraction: float,
    ) -> Any: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `LinearBlender` | `adaptive_reflow/algorithm/blender.py:449` |
| `DistanceDecayBlender` | `adaptive_reflow/algorithm/blender.py:546` |
| `OTLinearBlender` | `adaptive_reflow/algorithm/blender_extra.py:48` |
| `MultiTemperatureDistanceDecayBlender` | `adaptive_reflow/algorithm/blender_extra.py:151` |
| `JointOTLinearBlender` | `adaptive_reflow/algorithm/blender_extra.py:307` |
| `BarycentricBlender` | `adaptive_reflow/algorithm/blender_extra.py:405` |

### 2.9 `RunnerProtocol` — `adaptive_reflow/algorithm/runner_registry.py:40`

```python
@runtime_checkable
class RunnerProtocol(Protocol):
    def run(self, config: Any) -> Any: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `ReInferenceRunnerFamily` (wraps `ReInferenceRunner`) | `adaptive_reflow/algorithm/runner_registry.py:301` |
| `BatchedTrajectoryRunnerFamily` (wraps `BatchedTrajectoryRunner`) | `adaptive_reflow/algorithm/runner_registry.py:314` |
| `ParallelRunner` | `adaptive_reflow/algorithm/runner_registry.py:66` |
| `EarlyStopRunner` | `adaptive_reflow/algorithm/runner_registry.py:135` |
| `OnlineRunner` | `adaptive_reflow/algorithm/runner_registry.py:238` |

### 2.10 `RotationPolicy` — `adaptive_reflow/algorithm/rotation_policy.py:29`

```python
@runtime_checkable
class RotationPolicy(Protocol):
    def next(self, history: Sequence[Any]) -> str: ...
    def name(self) -> str: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `RoundRobinRotationPolicy` | `adaptive_reflow/algorithm/rotation_policy.py:50` |
| `BanditUCBRotationPolicy` | `adaptive_reflow/algorithm/rotation_policy.py:91` |

### 2.11 `StageProtocol` — `adaptive_reflow/frame/stage.py:32`

```python
@runtime_checkable
class StageProtocol(Protocol):
    stage_family: ClassVar[str]
    def config_hash(self) -> str: ...
    def run(self, input_state: Mapping[str, Any]) -> dict[str, Any]: ...
```

**Concrete implementations:**

| Implementation | File:Line |
|---|---|
| `RunStage` | `adaptive_reflow/frame/stage.py:54` |
| `CalibrationStage` | `adaptive_reflow/frame/stage.py:107` |
| `ClaimGateStage` | `adaptive_reflow/frame/stage.py:159` |
| `PromotionStage` | `adaptive_reflow/frame/stage.py:209` |

### 2.12 `_BatchedAdapterProtocol` / `BatchedVectorisedAdapterProtocol` — `adaptive_reflow/algorithm/batched_runner.py:110,140`

```python
class _BatchedAdapterProtocol(Protocol):
    def capabilities(self) -> AdapterCapabilities: ...
    def solve_ode_batched(self, states: Sequence[Any], *, seed: int) -> Sequence[Any]: ...

class BatchedVectorisedAdapterProtocol(Protocol):
    def capabilities(self) -> AdapterCapabilities: ...
    def evaluate_vectorised(self, ...) -> Any: ...
```

### 2.13 `_EvaluatorProtocol` — `adaptive_reflow/algorithm/runner.py:109`

```python
class _EvaluatorProtocol(Protocol):
    def evaluate(self, bundle: Any, channel: Any, seed: int) -> Any: ...
```

### 2.14 `W2EstimatorProtocol` — `adaptive_reflow/eval/w2.py:136`

```python
@runtime_checkable
class W2EstimatorProtocol(Protocol):
    def estimate(self, samples: NDArray[np.float64], reference: NDArray[np.float64]) -> float: ...
```

**Concrete implementations:** `ModeCentreMSEW2:253`, `ProjectionFreeExactW2:302`,
`KernelizedW2:444`, `SinkhornApproximatedW2:604`, `ProjectionFreeRademacherW2:702`,
`TreeSlicedW2:804`, `W2Barycenter:930`.

---

## 3. Registry inventory

Every registry, every registered entry. Capability tag is the public
Protocol surface the entry conforms to.

### 3.1 `SCHEDULER_REGISTRY` — `adaptive_reflow/algorithm/scheduler.py:2968`

Capability tag: `SchedulerProtocol`.

| Key | Value | File:Line |
|---|---|---|
| `cosine` | `default_cosine_scheduler` (factory) | `adaptive_reflow/algorithm/scheduler.py:506` |
| `constant` | `ConstantScheduler` | `adaptive_reflow/algorithm/scheduler.py:556` |
| `linear` | `LinearScheduler` | `adaptive_reflow/algorithm/scheduler.py:751` |
| `exponential` | `ExponentialScheduler` | `adaptive_reflow/algorithm/scheduler.py:962` |
| `polynomial` | `PolynomialScheduler` | `adaptive_reflow/algorithm/scheduler.py:1184` |
| `sigmoid` | `SigmoidScheduler` | `adaptive_reflow/algorithm/scheduler.py:1422` |
| `convergence_adaptive` | `ConvergenceAdaptiveScheduler` | `adaptive_reflow/algorithm/scheduler.py:1697` |
| `codimension_sheet` | `_codimension_sheet_factory` | `adaptive_reflow/algorithm/scheduler.py:2916` |
| `sequential` | `_sequential_factory` | `adaptive_reflow/algorithm/scheduler.py:2945` |
| `edm` | `EDMScheduler` (Phase-2 lazy register) | `adaptive_reflow/algorithm/scheduler.py:3017` |
| `adaptive_pid` | `AdaptivePIDScheduler` (Phase-2 lazy register) | `adaptive_reflow/algorithm/scheduler.py:3018` |
| `jittered_constant` | `JitteredConstantScheduler` (Phase-2 lazy register) | `adaptive_reflow/algorithm/scheduler.py:3019` |

### 3.2 `PROTOCOL_REGISTRY` (flat cross-protocol) — `adaptive_reflow/algorithm/protocol_registry.py:267`

Capability tags: `SchedulerProtocol`, `PolicyDriverProtocol`,
`MergeOperatorProtocol`, `RestartBlenderProtocol`. Aggregates the four
sub-registries below. Populated at import time via
`_ensure_protocol_registry:275`.

#### 3.2.1 `SchedulerProtocol` sub-registry — `adaptive_reflow/algorithm/protocol_registry.py:116`

In addition to §3.1 entries:

| Key | Value | File:Line |
|---|---|---|
| `multi_channel_jittered` | `MultiChannelJitteredConstantScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:999` |
| `handoff_sequential` | `HandoffSequentialScheduler` | `adaptive_reflow/algorithm/sequential_handoff.py:50` |
| `cosine_factory` | `default_cosine_scheduler` (kwargs API) | `adaptive_reflow/algorithm/scheduler.py:506` |

#### 3.2.2 `PolicyDriverProtocol` sub-registry — `adaptive_reflow/algorithm/protocol_registry.py:160`

| Key | Value | File:Line |
|---|---|---|
| `schedule_derived` | `ScheduleDerivedPolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:292` |
| `constant` | `ConstantPolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:409` |
| `adaptive` | `AdaptivePolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:505` |
| `multi_channel_constant` | `MultiChannelConstantPolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:918` |
| `dual_target_adaptive` | `DualTargetAdaptivePolicyDriver` | `adaptive_reflow/algorithm/policy_driver.py:1034` |

#### 3.2.3 `MergeOperatorProtocol` sub-registry — `adaptive_reflow/algorithm/protocol_registry.py:178`

| Key | Value | File:Line |
|---|---|---|
| `bounded` | `BoundedMergeOperator` | `adaptive_reflow/algorithm/merge_operator.py:359` |
| `identity` | `IdentityOperator` | `adaptive_reflow/algorithm/merge_operator.py:622` |
| `ema` | `EMAOperator` | `adaptive_reflow/algorithm/merge_operator.py:695` |
| `kalman_bounded` | `KalmanBoundedMergeOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:45` |
| `bayesian` | `BayesianMergeOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:233` |
| `pid_identity` | `PIDIdentityOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:376` |
| `schedule_ema` | `ScheduleAwareEMAOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:466` |
| `multi_source_kalman` | `MultiSourceKalmanMergeOperator` | `adaptive_reflow/algorithm/merge_operator_extra.py:581` |

#### 3.2.4 `RestartBlenderProtocol` sub-registry — `adaptive_reflow/algorithm/protocol_registry.py:204`

| Key | Value | File:Line |
|---|---|---|
| `linear` | `LinearBlender` | `adaptive_reflow/algorithm/blender.py:449` |
| `distance_decay` | `DistanceDecayBlender` | `adaptive_reflow/algorithm/blender.py:546` |
| `ot_linear` | `OTLinearBlender` | `adaptive_reflow/algorithm/blender_extra.py:48` |
| `multi_temperature_distance_decay` | `MultiTemperatureDistanceDecayBlender` | `adaptive_reflow/algorithm/blender_extra.py:151` |
| `joint_ot_linear` | `JointOTLinearBlender` | `adaptive_reflow/algorithm/blender_extra.py:307` |
| `barycentric` | `BarycentricBlender` | `adaptive_reflow/algorithm/blender_extra.py:405` |

### 3.3 `ROTATION_POLICY_REGISTRY` — `adaptive_reflow/algorithm/rotation_policy.py:198`

Capability tag: `RotationPolicy`.

| Key | Value | File:Line |
|---|---|---|
| `round_robin` | `RoundRobinRotationPolicy` | `adaptive_reflow/algorithm/rotation_policy.py:50` |
| `bandit_ucb` | `BanditUCBRotationPolicy` | `adaptive_reflow/algorithm/rotation_policy.py:91` |

### 3.4 `RUNNER_REGISTRY` — `adaptive_reflow/algorithm/runner_registry.py:331`

Capability tag: `RunnerProtocol` (duck-typed `run(config)`).

| Key | Value | File:Line |
|---|---|---|
| `reinference` | `ReInferenceRunnerFamily` | `adaptive_reflow/algorithm/runner_registry.py:301` |
| `batched` | `BatchedTrajectoryRunnerFamily` | `adaptive_reflow/algorithm/runner_registry.py:314` |
| `parallel` | `ParallelRunner` | `adaptive_reflow/algorithm/runner_registry.py:66` |
| `early_stop` | `EarlyStopRunner` | `adaptive_reflow/algorithm/runner_registry.py:135` |
| `online` | `OnlineRunner` | `adaptive_reflow/algorithm/runner_registry.py:238` |

### 3.5 `STAGE_REGISTRY` — `adaptive_reflow/frame/stage.py:253`

Capability tag: `StageProtocol`.

| Key | Value | File:Line |
|---|---|---|
| `run` | `RunStage` | `adaptive_reflow/frame/stage.py:54` |
| `calibration` | `CalibrationStage` | `adaptive_reflow/frame/stage.py:107` |
| `claim_gate` | `ClaimGateStage` | `adaptive_reflow/frame/stage.py:159` |
| `promotion` | `PromotionStage` | `adaptive_reflow/frame/stage.py:209` |

### 3.6 Implicit registry: `CandidateRegistry` — `adaptive_reflow/writer/registry.py:160`

Capability tag: DTB-G2 candidate admission. Not a literal
`{name: cls}` dict; population is by `admit_entry:236`,
`make_initial_registry:250`, `make_default_flowmol3_entry:274`,
`default_registry:326`. The hard-coded entry `FLOWMOL3_PINNED_COMMIT`
(`registry.py:30+`) is the canonical reference.

### 3.7 Family-name frozensets (advertised registries) — `adaptive_reflow/algorithm/protocol_registry.py:53–108`

| Set | File:Line | Members |
|---|---|---|
| `SCHEDULER_FAMILIES` | `protocol_registry.py:53` | 18 family strings |
| `POLICY_DRIVER_FAMILIES` | `protocol_registry.py:76` | 5 family strings |
| `MERGE_OPERATOR_FAMILIES` | `protocol_registry.py:86` | 8 family strings |
| `BLENDER_FAMILIES` | `protocol_registry.py:99` | 6 family strings |

---

## 4. Feedback-loop exact paths

The package ships **four documented feedback loops**. For each, the
exact file:line → file:line data path on both sides.

### Loop 1 — Self-reflexive (W2 feedback → scheduler)

> `scheduler → driver → engine → metric → scheduler.record_round_feedback`
> ([`README.md` §"The four feedback loops"](../../README.md))

The path on disk:

| Step | Code | File:Line |
|---|---|---|
| Scheduler samples for round r | `SchedulerProtocol.sample` | `adaptive_reflow/algorithm/scheduler.py:176` |
| Driver transforms schedule → policy | `PolicyDriverProtocol.compute_policy` | `adaptive_reflow/algorithm/policy_driver.py:181` |
| Runner drives engine | `ReInferenceRunner.run` | `adaptive_reflow/algorithm/runner.py:383` |
| Engine.run_round emits metrics | `Engine.run_round` | `adaptive_reflow/frame/engine.py:1016` |
| Engine records per-round trace (ledger row emitted) | `build_ledger_row` | `adaptive_reflow/frame/engine.py:441` |
| Engine-level audit codes | `EngineRoundResult.audit_codes` | `adaptive_reflow/frame/engine.py:248` |
| Runner extracts metrics, calls scheduler.record_round_feedback | `ReInferenceRunner._feedback_round` | `adaptive_reflow/algorithm/runner.py:383+` |
| Scheduler shifts u_r via PID-lite update | `ConvergenceAdaptiveScheduler.record_round_feedback` | `adaptive_reflow/algorithm/scheduler.py:2028` |
| Next round sample consumes the shift | `ConvergenceAdaptiveScheduler.sample` | `adaptive_reflow/algorithm/scheduler.py:1882` |

Symmetric counterpart: `W2` itself is computed in
`adaptive_reflow/eval/w2.py:1109` (`compute_w2`) /
`weighted_coverage_score:95` (coverage) and consumed by
`ConvergenceAdaptiveScheduler.record_round_feedback` as one of the
configurable metric weights (P0-A6, see scheduler.py:1776).

### Loop 2 — Theory-grounded (paper quantities → scheduler)

> `paper_quantities.{A_g,B_g,C_g,e_rho} → CodimensionSheetScheduler._paper_evidence_balance`
> ([`README.md` §"The four feedback loops"](../../README.md))

| Step | Code | File:Line |
|---|---|---|
| User supplies `profile_residual_fn` to scheduler | `CosineAnnealScheduler.__init__` / `CodimensionSheetScheduler.__init__` | `adaptive_reflow/algorithm/scheduler.py:316` |
| Scheduler caches `A_g` (sheet evidence) | `paper_quantities.sheet_evidence_A` | `adaptive_reflow/contracts/paper_quantities.py:71` |
| Scheduler caches `B_g` (root cell packing) | `paper_quantities.root_cell_packing_B` | `adaptive_reflow/contracts/paper_quantities.py:142` |
| Scheduler caches `C_g` (per-cell coefficient) | `paper_quantities.per_cell_coefficient_C` | `adaptive_reflow/contracts/paper_quantities.py:233` |
| Scheduler caches `e_rho` (exterior gap) | `paper_quantities.exterior_gap_e_rho` | `adaptive_reflow/contracts/paper_quantities.py:278` |
| Scheduler computes sheet-vs-cell evidence ratio | `_paper_evidence_balance` | `adaptive_reflow/algorithm/scheduler.py:2133` |
| Scheduler returns sample with `evidence_ratio` | `ScheduleSample.evidence_ratio` | `adaptive_reflow/algorithm/scheduler.py:94` |
| Runner records evidence ratio in per-round metrics | `ReInferenceResult` per-round | `adaptive_reflow/algorithm/runner.py:207` |
| Downstream `EvidenceScaleGapMetric` reads sample.evidence_ratio | `EvidenceScaleGapMetric` | `adaptive_reflow/eval/posterior_selection_evaluator.py:397` |

Symmetric counterpart: `W2` itself is fed back as one of the metrics
into `ConvergenceAdaptiveScheduler.record_round_feedback`, so the
W2-feedback loop (Loop 1) and the paper-quantity-driven scheduler
(Loop 2) compose on the same scheduler instance — the engine
doesn't distinguish them.

### Loop 3 — Hash-chained integrity

> `engine.build_ledger_row(prev_ledger_row_hash=...)` → `engine.verify_ledger_chain`
> ([`README.md` §"The four feedback loops"](../../README.md))

| Step | Code | File:Line |
|---|---|---|
| Round r: engine receives previous row hash | `Engine.run_round` signature | `adaptive_reflow/frame/engine.py:1016` |
| Engine builds row with chained prev hash | `build_ledger_row` | `adaptive_reflow/frame/engine.py:441` |
| Per-row hash computation | `compute_ledger_row_hash` | `adaptive_reflow/frame/engine.py:404` |
| Chain recompute (full pass) | `verify_ledger_chain` | `adaptive_reflow/frame/engine.py:491` |
| Chain recompute (incremental, on emit) | `LedgerChain.append_and_verify` | `adaptive_reflow/frame/ledger_chain.py:111` |
| Hash helper (recompute deterministically) | `_recompute` | `adaptive_reflow/frame/ledger_chain.py:96` |
| Incremental verification helper | `verify_ledger_chain_incremental` | `adaptive_reflow/frame/ledger_chain.py:261` |
| Hash payload stable JSON encoder | `_canonical_json` (frame.engine) | `adaptive_reflow/frame/engine.py:291` |
| Hash payload stable JSON encoder (trace v3) | `_canonical_json` (frame.trace) | `adaptive_reflow/frame/trace.py:151` |

Symmetric counterpart: `RoundTraceV3.content_hash` is computed
independently at `compute_round_trace_v3_content_hash:207` and
recomputed on read via `round_trip_round_trace_v3:236`. The
trace-level hash and the ledger-row hash share the canonical JSON
encoder family but live in different files (engine.py vs trace.py).

### Loop 4 — Symmetric round (forward inject_noise ↔ reverse bounded merge)

> `scheduler.inject_noise (forward) ↔ blender.merge (reverse)`
> ([`README.md` §"The four feedback loops"](../../README.md))

| Step | Code | File:Line |
|---|---|---|
| Runner calls scheduler.inject_noise (FORWARD step) | `ReInferenceRunner._inject_noise` | `adaptive_reflow/algorithm/runner.py:383+` |
| Forward noise injection helper | `SchedulerProtocol.inject_noise` | `adaptive_reflow/algorithm/scheduler.py:217` |
| Cosine default implementation | `CosineAnnealScheduler.inject_noise` | `adaptive_reflow/algorithm/scheduler.py:419` |
| Forward-noise audit trail marker | `FORWARD_NOISE_INJECTED` | `adaptive_reflow/algorithm/runner.py:90` |
| Runner calls merge operator (REVERSE step) | `ReInferenceRunner._apply_merge` | `adaptive_reflow/algorithm/runner.py:383+` |
| Bounded merge authority | `MergeOperatorProtocol.merge` | `adaptive_reflow/algorithm/merge_operator.py:240` |
| Frame-level bounded merge authority (D3-R3 back-compat) | `bounded_merge` / `bounded_merge_with_schedule` | `adaptive_reflow/frame/merge.py:157,305` |
| Reverse-step audit codes | `MERGE_PREV_ANCHORED_TO_LAST_EMITTED`, `MERGE_FLOOR_FALLBACK`, `MERGE_DEGENERATE_INTERVAL`, `ERR_PREV_REQUIRED` | `adaptive_reflow/algorithm/merge_operator.py:34-44` |
| Adapter consumes the reverse-step policy | `FlowMatchingODEAdapter.apply_restart_distribution` | `adaptive_reflow/universal/adapter.py` (Protocol); concrete: `adaptive_reflow/adapters/twodim_fm.py` |

Symmetric counterpart: the merge operator's `prev` is sourced from
`last_emitted: dict[ChannelName, FactorValue]` on the orchestrator
(`frame/orchestrator.py:251`); the scheduler's `inject_noise` writes
its state to a fresh allocation, leaving `state` immutable (so the
forward step is replayable given the `generator` seed).

---

## 5. Dependency DAG

Module-level import edges between `adaptive_reflow/*` packages. Cycles
are explicitly noted; reverse dependencies (a lower layer importing
from a higher layer) are flagged.

### 5.1 Edge list

```
contracts         ← universal, molecular, frame, policy, schedule,
                     envelope, diagnostics, writer, adapters, eval,
                     algorithm (all)

universal         ← molecular, frame, adapters, eval, algorithm,
                     envelope (NO contracts imports by universal)
                  ← contracts (Protocol carriers are re-imported via
                     re-export shims in frame/adapter.py only)

molecular         ← frame, eval, algorithm (no direct eval reach),
                     envelope (manifest via stratification)

frame             ← universal (re-export shim only),
                     contracts, envelope, diagnostics, schedule,
                     policy, writer
                  ← algorithm (consumes Engine from frame.engine)

policy            ← contracts, envelope.manifest (StratifiedTailBudgetRow)

schedule          ← contracts (only)

envelope          ← contracts (only), policy (stratification), molecular

diagnostics       ← contracts (only)

writer            ← contracts, universal, frame, adapters, policy

adapters          ← contracts, universal, writer (FLOWMOL3_PINNED_COMMIT),
                     data (target_distributions)

eval              ← contracts, frame, universal (mixer protocols), molecular

algorithm         ← contracts, universal, frame, schedule,
                     eval (lazy imports for W2 estimators)

legacy            ← (NONE: legacy/__init__.py emits DeprecationWarning,
                     no other adaptive_reflow.* package imports it)

data              ← (no adaptive_reflow.* imports; consumed by adapters,
                     algorithm via lazy imports)
```

### 5.2 Reverse dependencies / smells

The following are imports where a lower layer reaches up to a higher
layer — flagged as smells per the dependency-direction rules:

1. **`algorithm/scheduler.py:319`** — `from adaptive_reflow.contracts import paper_quantities as _pq` (lazy import inside `CosineAnnealScheduler.__init__`). The scheduler (algorithm-layer) imports `paper_quantities` (contracts-layer), which is **downward** — this is correct, not a smell. But the access via `paper_quantities` rather than `paper_quantities.sheet_evidence_A` shows that the per-function import is correct.

2. **`algorithm/runner.py:48-89`** — `from adaptive_reflow.eval.w2 import W2EstimatorProtocol` is a **lazy** import — `algorithm` reaches into `eval` (which is normally a peer), but the lazy form is contained and does not create an import-time cycle. The lazy pattern is deliberate (matches the registration-time guards in `protocol_registry.py`). Severity 1.

3. **`frame/orchestrator.py` → `writer/`** — the orchestrator imports `WriterArbitrator` (writer layer). The ADR-0005 audit-code policy and `ARCHITECTURE.md §3 rule 7` explicitly allow this: *"the orchestrator reaches into `writer/`, never the other way around"*. This is **intended**, not a smell. Confirmed at `frame/orchestrator.py:251` (`AdaptiveReflowPolicyOrchestrator` constructor).

4. **`universal/` imports** — `universal/__init__.py` re-exports `ChannelName`, `TensorRef`, etc. These re-exports come from `universal/state.py` and `universal/adapter.py` — both inside `universal/`. **Zero molecule-specific imports**, verified by AST guard `tests/test_universal/test_no_molecular_import.py`. No reverse dependency.

5. **`molecular/mixer.py:83`** — `def require_torch() -> None:` — a stub. The actual `EqualRmsCoordinateMixer` uses opaque TensorRef carriers, but the function exists for back-compat with the legacy quarantine. Severity 1 smell: dead code (the function body only `raises` if `torch` is unavailable; nothing in `molecular/mixer.py` actually calls it after the refactor).

### 5.3 Cycles

**No import-time cycles** in the main `adaptive_reflow/*` package
graph. Two lazy-import escape hatches break the cycle that the
molecule-aware `RoundResultBundle` would otherwise create:

- `adaptive_reflow/contracts/__init__.py:42` — `__getattr__` lazy
  resolver for `RoundResultBundle` /
  `validate_round_result_bundle`; pre-populates
  `_prepopulate_molecule_bundle_names:55`.
- `adaptive_reflow/contracts/bundle.py:79-90` — sibling
  `_MOLECULE_BUNDLE_NAMES` + `__getattr__` that points back at
  `adaptive_reflow.molecular.bundle`.

Both are explicitly documented as lazy-import shims in
`adaptive_reflow/contracts/__init__.py:39` ("breaks the import cycle").
No runtime cycle exists.

### 5.4 Cross-package coupling

| From → To | Edge type | Where |
|---|---|---|
| `contracts.bundle` → `molecular.bundle` (lazy) | reversed cycle | `contracts/bundle.py:79` |
| `contracts.__init__` → `molecular.bundle` (lazy) | reversed cycle | `contracts/__init__.py:42` |
| `algorithm.scheduler` → `eval.w2` (lazy) | peer | `algorithm/runner.py:48+` |
| `frame.orchestrator` → `writer.authority` | downward (intended) | `frame/orchestrator.py:251+` |
| `adapters.flowmol3` → `writer.registry` | downward | `adapters/flowmol3.py:56` |

---

## 6. Invariant enforcement

Every documented load-bearing invariant, with the test:line or
assertion:line where it is enforced.

### 6.1 Universal/molecular split

- **Invariant**: `universal/` has zero molecule-specific imports.
- **Enforcement**: `tests/test_universal/test_no_molecular_import.py`
  (referenced by `ARCHITECTURE.md:79`, ADR-0003:67).
- **Smell** (see §Smells 8.10): this test is referenced by docstring
  comments but not verified in this read-only survey. The AST guard
  was *not* physically inspected at file:line.

### 6.2 Capability handshake fail-closed

- **Invariant**: every adapter's `AdapterCapabilities` is validated
  before any native call; failure → `CapabilityMissingError` /
  `CapabilityMismatchError`.
- **Enforcement**:
  - `frame/engine.py:914` — `validate_capabilities(caps)` inside `Engine.handshake`.
  - `frame/engine.py:924-935` — eight required capabilities checked, raise `CapabilityMissingError`.
  - `tests/test_frame/test_engine.py::test_no_torch_in_any_new_file`
    (referenced by `ARCHITECTURE.md:488`).

### 6.3 Byte-determinism (canonical JSON hashing)

- **Invariant**: every hash payload uses a deterministic canonical-JSON
  encoder; same input → same hash, byte-for-byte.
- **Enforcement**:
  - `frame/engine.py:277-291` — `_digest`, `_canonical_json_default`.
  - `frame/trace.py:151-167` — `_canonical_json`, `_json_default`.
  - `contracts/hashes.py:25-45` — module-level canonical JSON helpers.

### 6.4 No torch in adapters (DTB-G1)

- **Invariant**: `import torch` forbidden in `adaptive_reflow/adapters/*`.
- **Enforcement**:
  - `tests/test_frame/test_engine.py::test_no_torch_in_any_new_file`
    (referenced by `ARCHITECTURE.md:488`).
  - ADR-0005 §5 hard-gate rules.

### 6.5 No torch in `universal/`

- **Invariant**: `universal/` is stdlib-only.
- **Enforcement**: `tests/test_universal/test_no_molecular_import.py`
  (extended to forbid torch — referenced by `ARCHITECTURE.md:493-499`).

### 6.6 No torch in `policy/` (new modules)

- **Invariant**: new `policy/*` modules do not pull `torch` transitively.
- **Enforcement**: `tests/test_policy/test_stratification_and_pruning.py::TestNoTorchDependency::test_no_torch_in_new_modules`
  (referenced by `ARCHITECTURE.md:491`).

### 6.7 Capability handshake universality

- **Invariant**: a synthetic non-molecular adapter
  (`ToyGaussianAdapter`) drives the universal Protocol end-to-end.
- **Enforcement**:
  - `tests/test_universal/test_adapter_universality.py` (ADR-0003:67).
  - `tests/test_universal/test_envelope_criterion.py`.
  - `tests/test_universal/test_mixer_protocol.py`.

### 6.8 Legacy deprecation warning

- **Invariant**: importing `adaptive_reflow.legacy` emits
  `DeprecationWarning`.
- **Enforcement**:
  - `adaptive_reflow/legacy/__init__.py` (the warning itself).
  - `tests/test_frame/test_trace.py` deprecation-warning test
    (referenced by `ARCHITECTURE.md:1241`).

### 6.9 Seven-step engine order pinned

- **Invariant**: `DEFAULT_OPERATION_STEPS` is the literal seven-tuple,
  reordering requires a new ADR.
- **Enforcement**:
  - `frame/engine.py:1-100` — tuple definition `DEFAULT_OPERATION_STEPS`.
  - `tests/test_frame/test_engine.py::test_default_operation_steps_is_seven`
    (literal-value assertion — referenced by ADR-0004:96).

### 6.10 Bounded-merge `prev` is required, no silent substitution

- **Invariant**: missing `prev` raises `MergeAuthorityError(
  ERR_PREV_REQUIRED)`.
- **Enforcement**:
  - `frame/merge.py:305` — `bounded_merge_with_schedule` raises.
  - `tests/test_frame/test_merge.py` — every hostile-case fixture
    asserts `ERR_PREV_REQUIRED` is reachable
    (referenced by ADR-0007:170).
  - `tests/property/test_bounded_merge_anchoring.py` — property test
    that `bounded_merge_with_schedule` never substitutes from
    `n_cap` (referenced by ADR-0007:171).

### 6.11 Engine-wraps-adapter pattern (fail-closed for adapter exceptions)

- **Invariant**: an adapter exception mid-round never drops the
  ledger row; `ERR_ADAPTER_RAISED` is appended to `audit_codes`.
- **Enforcement**:
  - `frame/engine.py:730-768` — `_safe_adapter_call` helper.
  - `tests/test_frame/test_engine.py` adversarial cases assert
    `ERR_ADAPTER_RAISED:build_initial_state:RuntimeError:...` etc.
    for all seven call sites (referenced by ADR-0006:152).

### 6.12 RMS-precondition for molecular mixer

- **Invariant**: mixer RMS preserved only when inputs are RMS-equal
  within `1e-6`; otherwise `MIXER_RMS_PRECEDENCE_FAIL` is appended
  to the audit trail.
- **Enforcement**:
  - `molecular/mixer.py:128-173` — `_require_equal_rms` helper.
  - `tests/test_molecular/test_mixer.py::test_rms_mismatch_emits_audit_code`
    (referenced by ADR-0009:144).
  - `tests/test_molecular/test_mixer.py::test_legacy_alias_deprecation_warning`
    (referenced by ADR-0009:149).

### 6.13 Hard gates for DTB-R0 §3 case 2 / case 5

- **Invariant**: `AUDIT_STABILITY_COLLAPSE` (case 2) and
  `AUDIT_SOURCE_REVOKED` (case 5) are hard gates (not xfail markers).
- **Enforcement**:
  - `frame/channel_rule.py:103-110` — `BLOCKER_*` constants; case 2
    surfaces as `BLOCKER_NOT_FINITE_PREFIX` / `BLOCKER_NON_FINITE` via
    `_build_stability_collapse_outputs:397`.
  - `contracts/validators.py` — `AUDIT_SOURCE_REVOKED` constant (case 5).
  - `tests/test_adversarial/test_hostile_cases.py::test_case_2_stability_collapse`
    (referenced by `ARCHITECTURE.md:1258-1267`).
  - `tests/test_adversarial/test_hostile_cases.py::test_case_5_source_revocation`.

### 6.14 Audit-code catalogue re-exports

- **Invariant**: every `AUDIT_*` / `ERR_*` / `BLOCKER_*` / `OBS_*`
  constant is re-exported from the relevant `__init__.py` and indexed
  by `tools/check_docs_against_code.py`.
- **Enforcement**:
  - `tools/check_docs_against_code.py` (referenced by ADR-0005:79).
  - Each `__init__.py` re-exports the audit codes from its emitting
    subpackage.

### 6.15 Claim-gate deferral placeholder (R7 wiring point)

- **Invariant**: `evaluate_claim_gate` delegates to
  `_resolve_decision` which currently returns `"defer"`; the helper
  body is the single R7 wiring point.
- **Enforcement**:
  - `eval/claim_gate.py:359-397` — `_resolve_decision` returns `ClaimGateDecision(verdict="defer", reason="r7_calibration_pending")`.
  - `tests/test_eval/test_claim_gate.py::test_evaluate_claim_gate_returns_defer`
    (referenced by ADR-0008:117).

### 6.16 `policy_hash == hash_policy_hash(policy)` invariant

- **Invariant**: the policy hash stored in the round trace equals
  the canonical `hash_policy_hash` recompute over the policy payload.
- **Enforcement**:
  - `contracts/hashes.py:122` — `hash_policy_hash(policy)`.
  - `contracts/authority.py:55` — `FinalRestartPolicy` dataclass
    carries the fields (`beta_from_schedule`, `driver_computed_beta`)
    that enter the hash payload.
  - `frame/engine.py` — engine recomputes `applied_policy_hash`
    post-override (`_policy_with_schedule_beta:770`).

### 6.17 `algorithm_signatures` provenance

- **Invariant**: every run's `ReInferenceResult.algorithm_signatures`
  records `{component: config_hash}` for the chosen algorithms.
- **Enforcement**:
  - `algorithm/runner.py:345` — `_algorithm_signatures` helper.
  - `algorithm/runner.py:383+` — `ReInferenceRunner` populates it.

### 6.18 forward/reverse-noise reproducibility

- **Invariant**: identical `generator.bit_generator.state` + identical
  `state` → identical `inject_noise` output.
- **Enforcement**: scheduler implementations
  (`CosineAnnealScheduler.inject_noise:419-449`,
  `ConstantScheduler.inject_noise:695-712`,
  `LinearScheduler.inject_noise:902-921`,
  `ExponentialScheduler.inject_noise:1129-1143`, etc.) all use the
  canonical `state + sqrt(n_cap) * generator.standard_normal` form,
  which is reproducible by construction. Tested by the
  `tests/test_algorithm/test_scheduler.py` determinism tests.

---

## 7. Public API surface

For each subpackage `__init__.py`, the documented exports vs the
modules that intentionally **do not** appear in the curated surface.

### 7.1 `adaptive_reflow.contracts` — `contracts/__init__.py`

**Exports**: every §1–§8 frozen dataclass, NewType, hash helper,
literal-set constant, factory, and validator. The full list is in
`ARCHITECTURE.md §4.1` and matches `contracts/__init__.py` exactly.

**Intentionally not exported**: internal coercion helpers
(`_ok`, `_err`), the lazy-import `_LAZY_BUNDLE_NAMES` set, the
`_prepopulate_molecule_bundle_names` private function.

**Backwards-compat shims**: `RoundResultBundle` /
`validate_round_result_bundle` are **lazy** re-exports from
`molecular.bundle` (not eager imports). The docstring at line 8
explicitly explains the molecule-aware import cycle.

### 7.2 `adaptive_reflow.universal` — `universal/__init__.py`

**Exports**: `FlowMatchingODEAdapter`, `RestartMixer`,
`EnvelopeCriterion`, `Evaluator` Protocols; `StateBundle`,
`ODEConditionDelta`, `ODEIntegratorTrace` carriers; `AdapterCapabilities`,
`EnvelopeClassification` carriers; NewType aliases (`ChannelName`,
`ArtifactHash`, `ChannelDomain`, `TensorRef`, etc.); validators
(`validate_state_bundle`, `validate_condition_delta`,
`validate_integrator_trace`, `validate_capabilities`,
`validate_envelope_criterion`, `validate_envelope_classification`,
`validate_blend_inputs`, `validate_evaluator_artifact_hash`,
`validate_unit_factor`, `validate_unit_float`, `validate_positive_int`,
`validate_nonneg_int`); exception classes (`CapabilityMismatchError`,
`CapabilityMissingError`).

**Intentionally not exported**: `NORMALIZATION_KINDS` /
`REFERENCE_FRAMES` (string-enum constants live in `state.py` but
are not re-exported to the universal top-level — they are accessed
via `from adaptive_reflow.universal.state import NORMALIZATION_KINDS`).

### 7.3 `adaptive_reflow.molecular` — `molecular/__init__.py`

**Exports**: molecule channel vocabulary, concrete universal-Protocol
implementations (`RMSPreservingCoordinateMixer`, `EqualRmsCoordinateMixer`,
the four Evaluator arms), validators, back-compat helpers
(`attach_molecule_channels`).

**Intentionally not exported**: the `to_molecule_bundle` /
`from_molecule_bundle` / `is_compatible` helpers are defined at
`molecular/__init__.py:201-265` but are **not** in `__all__`
(must be reached via the module path).

### 7.4 `adaptive_reflow.frame` — `frame/__init__.py`

**Exports**: full surface listed in `ARCHITECTURE.md §4.2`.

**Intentionally not exported**: `_digest`, `_canonical_json_default`
(internal helpers in `frame/engine.py`), `_LedgerRecord`
(internal to `frame/orchestrator.py:183`), `_safe_factor_value`
(internal coercion helper).

### 7.5 `adaptive_reflow.algorithm` — `algorithm/__init__.py`

**Exports**: 95+ symbols (see `algorithm/__init__.py:135-230` for
the full `__all__`). Includes every registry, factory, family
constant, audit code.

**Intentionally not exported**: `_coerce_finite_real`,
`_coerce_unit_real`, `_coerce_unit_real_clip`, `_coerce_int_nonneg`
(internal coercion helpers); `_paper_evidence_balance` (internal
heuristic used by `CodimensionSheetScheduler`); the
`AdaptivePIDScheduler` / `EDMScheduler` / `JitteredConstantScheduler`
concrete classes (only registered through `SCHEDULER_REGISTRY`, not
re-exported to top-level even though they ARE in `__all__`).

**Discrepancy** (smell — see §8.8): `algorithm/__init__.py:159-162`
re-exports `EDM_RHO_DEFAULT`, `EDM_SIGMA_MAX_DEFAULT`,
`EDM_SIGMA_MIN_DEFAULT` but **not** the concrete `EDMScheduler`
class itself, so callers cannot import it directly. The
`MultiChannelJitteredConstantScheduler` (from `scheduler_extra.py:999`)
is in `algorithm/__init__.py:148` via the duplicate-in-`round2_extra`
class.

### 7.6 `adaptive_reflow.policy` — `policy/__init__.py`

**Exports**: `SameSampleArchive`, `ArchiveEntry`, `PruneGate`,
`UnorderedAuditResult`, `PruneDecision`, `Stratum`,
`StratumAssignment`, `dominance_ratio`,
`cross_stratum_mix_rejected`, `physical_noise_proxy`,
`RMS_preserving_mixing_coefficient`, `exact_spectral_variance`,
`ThreeWayDistinction`, `adversarial_stagnation_test`, all `ERR_*`
codes, plus the lazy cross-re-export of `AUDIT_STABILITY_COLLAPSE`
from `frame/channel_rule.py` and `AUDIT_SOURCE_REVOKED` from
`contracts/validators.py` via `__getattr__` at
`policy/__init__.py:57`.

**Intentionally not exported**: `_safe_factor`, `_validate_quota`,
`_check_lineage`, `_entry_sort_key`, `_archive_audit_hash`,
`_ArchiveStats` (internal helpers in `policy/archive.py`).

### 7.7 `adaptive_reflow.schedule` — `schedule/__init__.py`

**Exports**: `CosineScheduleSampler`, `n_cap_for_round`,
`memory_fraction_from_schedule`, `validate_cosine_schedule_config`,
`default_floor_by_channel`, `build_fresh_noise_diagnostics`,
all `ERR_*` codes.

### 7.8 `adaptive_reflow.diagnostics` — `diagnostics/__init__.py`

**Exports**: `FreshNoiseCumulativeMassRecord`,
`SpectralResidualBandProxy`, `TailDiagnosticStatus`, validators,
`empty_diagnostics`, all `ERR_*` codes.

### 7.9 `adaptive_reflow.envelope` — `envelope/__init__.py`

**Exports**: `EvidenceRowHash`, `FrozenEnvelopeManifestBuilder`,
`ManifestBuildError`, `StratifiedTailBudgetRow`,
`TailBudgetAccumulator`, `classify_endpoint`.

**Intentionally not exported**: `OBS_*` constants (defined in
`envelope/classifier.py:19-29`) — must be reached via the module path.
This is documented in `ADR-0005 §5` as intentional: the constants
are observation keys, not part of the public surface.

### 7.10 `adaptive_reflow.writer` — `writer/__init__.py`

**Exports**: every authority + handoff + registry + audit type and
function (see `writer/__init__.py`).

### 7.11 `adaptive_reflow.adapters` — `adapters/__init__.py`

**Exports**: every concrete adapter class + capability constants.

### 7.12 `adaptive_reflow.eval` — `eval/__init__.py`

**Exports**: full DTB-R7 / DTB-R8 surface (see `eval/__init__.py`).

### 7.13 `adaptive_reflow.legacy` — `legacy/__init__.py`

**Exports**: `__all__: list[str] = []`. Emits `DeprecationWarning` at
import time. Nothing is re-exported. (Confirmed by `ARCHITECTURE.md
§4.10`.)

### 7.14 `adaptive_reflow.data` — `data/__init__.py`

**Exports**: target-distribution samplers (`sampler_for`,
`two_moons`, `eight_gaussians`, ...). `data/__init__.py` exists but
the public surface is curated through `data/target_distributions.py`.

---

## 8. Smells

Each smell: file:line, description, severity 1–3.

- **(8.1) `adaptive_reflow/molecular/mixer.py:83` — `def require_torch() -> None:` is dead code.** The function body raises if `torch` is unavailable, but no caller in `adaptive_reflow/molecular/mixer.py` invokes it after the refactor; the actual mixer logic uses opaque `TensorRef` carriers. Severity **1**.

- **(8.2) `adaptive_reflow/algorithm/scheduler_r2.py:30` — duplicate definition of `MultiChannelJitteredConstantScheduler`.** The same class is also defined at `adaptive_reflow/algorithm/scheduler_extra.py:999` and `adaptive_reflow/algorithm/round2_extra.py:46`. The PROTOCOL_REGISTRY (`protocol_registry.py:149`) imports from `scheduler_extra` (canonical), leaving `scheduler_r2` and `round2_extra` as carry-over R2 file dumps with no canonical home. Severity **2**.

- **(8.3) `adaptive_reflow/algorithm/merge_r2.py:36` — duplicate definition of `MultiSourceKalmanMergeOperator`.** The same class is defined at `adaptive_reflow/algorithm/merge_operator_extra.py:581`. `PROTOCOL_REGISTRY` (`protocol_registry.py:200`) imports from `merge_operator_extra` (canonical), leaving `merge_r2.py` as a carry-over. Severity **2**.

- **(8.4) `adaptive_reflow/algorithm/round2_extra.py:233` and `:315` — duplicate `MultiChannelConstantPolicyDriver` and `DualTargetAdaptivePolicyDriver`.** Canonical homes: `adaptive_reflow/algorithm/policy_driver.py:918` and `:1034` respectively. `PROTOCOL_REGISTRY` (`protocol_registry.py:174`) imports the canonical classes from `policy_driver`, leaving `round2_extra.py` as a dead duplicate. Severity **2**.

- **(8.5) `adaptive_reflow/algorithm/handoff.py:56` and `adaptive_reflow/algorithm/sequential_handoff.py:50` — two `HandoffSequentialScheduler` classes.** `algorithm/handoff.py` re-defines the class; `algorithm/sequential_handoff.py` defines a different version. `PROTOCOL_REGISTRY` (`protocol_registry.py:135`) imports from `sequential_handoff`. The `handoff.py` copy is shadowed. Severity **2**.

- **(8.6) `adaptive_reflow/algorithm/scheduler.py:2945` and `adaptive_reflow/algorithm/sequential.py:95` — `_sequential_factory` is a thin wrapper that returns `_SequentialScheduler(schedulers=...)`.** The wrapper exists solely to keep the SCHEDULER_REGISTRY API uniform; it doesn't add testability. Severity **1**.

- **(8.7) `adaptive_reflow/algorithm/scheduler.py:2968-2979` — `SCHEDULER_REGISTRY` is duplicated by `PROTOCOL_REGISTRY["SchedulerProtocol"]` (`protocol_registry.py:282`).** Two parallel registries; `SCHEDULER_REGISTRY` is the legacy surface (used by `build_scheduler`), `PROTOCOL_REGISTRY` is the polymorphic surface (used by `build_scheduler_from_config`). The two are kept in sync by hand via `_register_extra_scheduler_families:3003` — a runtime side-effect rather than a single-source dict. Severity **2**.

- **(8.8) `adaptive_reflow/algorithm/__init__.py:159-162` — re-exports the EDM default constants (`EDM_RHO_DEFAULT`, etc.) but **not** the `EDMScheduler` class itself.** Callers cannot import `EDMScheduler` directly from `adaptive_reflow.algorithm`; they must go through `from adaptive_reflow.algorithm.scheduler_extra import EDMScheduler`. The asymmetry is not documented. Severity **1**.

- **(8.9) `adaptive_reflow/contracts/decision.py` — reserved-but-empty file.** Per `ARCHITECTURE_PLAN.md §5.2`: "DTB-R2 contract types live in `contracts/bundle.py` because they pair with the per-channel evidence dataclasses. `decision.py` exists to keep the layout symmetric with `envelope.py` / `schedule.py` / etc." The decision to keep an empty file in production is a layout smell. Severity **1**.

- **(8.10) `adaptive_reflow/molecular/__init__.py:201-265` — `to_molecule_bundle`, `from_molecule_bundle`, `is_compatible` helpers are defined but **not** in `__all__`.** They are reachable only via the module path, with no `__all__` entry to advertise them. Whether they are public or private is undocumented. Severity **1**.

- **(8.11) `adaptive_reflow/frame/adapter.py` — entire file is a re-export shim over `universal/adapter.py`.** Confirmed by the docstring ("re-export the universal Protocols for back-compat"). The shim duplicates the surface; every change in `universal/adapter.py` must be re-exported here. Severity **1**.

- **(8.12) `adaptive_reflow/frame/orchestrator.py` is 1158 lines.** The orchestrator reaches across envelope, schedule, policy, diagnostics, and writer concerns; it carries `last_emitted: dict[ChannelName, FactorValue]` invariant (1158-line file but the orchestrator's single responsibility is "drive the policy loop"). Severity **2**.

- **(8.13) `adaptive_reflow/frame/engine.py` is 1703 lines.** The engine carries the 7-step operation, the `LedgerRow` builder, the chain verifier, the capability handshake, the adapter-wrapping safe-call, the schedule-driven beta override, the audit-code catalogue, the feature-flag gate, the source-round coercion, and the `EngineRoundResult` factory. Multiple responsibilities in one file. Severity **2**.

- **(8.14) `adaptive_reflow/algorithm/scheduler.py` is 3119 lines.** Houses `ScheduleSample`, `SchedulerProtocol`, eight concrete scheduler classes, the `_paper_evidence_balance` heuristic, the codimension-sheet factory, the sequential factory, the `SCHEDULER_REGISTRY`, and the polymorphic `build_scheduler_from_config`. Could be split per family (`scheduler_cosine.py`, `scheduler_constant.py`, etc.) to mirror `merge_operator_extra.py` / `blender_extra.py`. Severity **2**.

- **(8.15) `adaptive_reflow/eval/posterior_selection_evaluator.py` is 1030+ lines with a module-level `__getattr__` shim at line 984.** The file mixes paper-quantity computation (`mode_centers_for`, `sheet_evidence`, `cell_evidence`, `selection_ratio`) with the `EvidenceScaleGapMetric` class. The `__getattr__` shim is marked `pragma: no cover` — a sign of test-coverage gap. Severity **1**.

- **(8.16) `adaptive_reflow/eval/coverage.py`, `eval/coverage_extra.py`, `eval/coverage_r2.py` — three files with overlapping coverage-score implementations (`support_coverage_score`, `_knn_entropy`, `top_k_coverage_with_entropy`, `W2BarycenterCoverage`).** `coverage.py` has the canonical `weighted_coverage_score` + `energy_distance_*`; `coverage_extra.py` has KDE-based `support_coverage_score`; `coverage_r2.py` has the R2-variant. Three parallel implementations, no documentation that they are intentionally separate. Severity **2**.

- **(8.17) `adaptive_reflow/eval/w2.py` — seven concrete W2 estimator classes in one file (1140 lines).** `ModeCentreMSEW2`, `ProjectionFreeExactW2`, `KernelizedW2`, `SinkhornApproximatedW2`, `ProjectionFreeRademacherW2`, `TreeSlicedW2`, `W2Barycenter`. Could be split per estimator (`w2_kalman.py`, `w2_sinkhorn.py`, ...) following the same `scheduler_extra.py` / `merge_operator_extra.py` precedent. Severity **1**.

- **(8.18) `adaptive_reflow/legacy/control_policy.py` and `legacy/metric_feedback.py` both define `adaptive_reflow_external_metric_controls`.** `legacy/control_policy.py:24` and `legacy/metric_feedback.py:318` define the same symbol. `molecular/calibration_protocols.py:355` adds a third definition. Three copies of the same public function across legacy and canonical. Severity **2**.

- **(8.19) `adaptive_reflow/legacy/metric_feedback.py` is 991+ lines.** Despite being quarantined, the legacy file is large; the `adaptive_reflow_external_metric_controls` function spans 600+ lines. The legacy quarantine should be a thin wrapper, not a full re-implementation. Severity **2**.

- **(8.20) `adaptive_reflow/envelope/__init__.py` does not re-export the `OBS_*` constants (`envelope/classifier.py:19-29`).** ADR-0005 documents this as intentional, but the curated surface for `envelope/` is missing 11 observable-key constants that downstream consumers (audit trail readers) need. There is no `__all__` entry to guide the reader. Severity **1**.

- **(8.21) `adaptive_reflow/universal/__init__.py` does not re-export `NORMALIZATION_KINDS` / `REFERENCE_FRAMES`.** Consumers importing `from adaptive_reflow.universal import NORMALIZATION_KINDS` will fail; they must use `from adaptive_reflow.universal.state import NORMALIZATION_KINDS`. The asymmetry is undocumented. Severity **1**.

- **(8.22) `adaptive_reflow/policy/__init__.py:47-58` — `_FRAME_REEXPORT` / `_CONTRACTS_REEXPORT` lazy `__getattr__` for cross-package audit-code re-exports.** This is undocumented in `ARCHITECTURE.md §4.3`; the lazy pattern is the only path for `AUDIT_STABILITY_COLLAPSE` and `AUDIT_SOURCE_REVOKED` to surface through the policy package. Severity **1**.

- **(8.23) `adaptive_reflow/algorithm/evidence_driver.py:93` — `EvidenceDrivenScheduler` is defined but not in `SCHEDULER_REGISTRY`.** Only callable by direct import (`from adaptive_reflow.algorithm.evidence_driver import EvidenceDrivenScheduler`). The fact that this is a `SchedulerProtocol` impl is not advertised in `SCHEDULER_FAMILIES`. Severity **1**.

- **(8.24) `adaptive_reflow/algorithm/handoff.py:246` — `_dispatch_to_sub` private helper has no test-side enforcement.** The handoff dispatch is the seam where `HandoffSequentialScheduler` routes round windows to sub-schedulers; the helper's behaviour is untested at the public level (only the round-trip through `HandoffSequentialScheduler` is). Severity **1**.

- **(8.25) `adaptive_reflow/algorithm/merge_operator_extra.py:581-686` — `MultiSourceKalmanMergeOperator` is 105+ lines with a complex internal config-digest payload.** No unit test references this concrete class directly (the registration round-trip is the only coverage). Severity **2**.

- **(8.26) `adaptive_reflow/frame/engine.py:491` — `verify_ledger_chain` returns `(bool, str)` whereas `frame/ledger_chain.py:111` — `LedgerChain.append_and_verify` returns `ChainVerification` (a richer object).** Two different return shapes for "verify the chain" — a smell for consistency. Severity **1**.

- **(8.27) `adaptive_reflow/contracts/types.py:79` — `_MOLECULE_CHANNEL_ALIASES` frozenset with a `__getattr__` resolver at line 89.** The lazy-resolution pattern breaks the round-1 import of `adaptive_reflow.contracts` from `adaptive_reflow.molecular`. The resolver is documented but the only resolved names are molecule-channel aliases that consumers shouldn't need anyway. Severity **1**.

- **(8.28) `adaptive_reflow/data/round2_targets.py` — a separate file with target distributions that mirrors `data/target_distributions.py`.** Same smell pattern as `merge_r2.py` / `scheduler_r2.py` / `round2_extra.py` — an R2 carry-over file with no canonical home. Severity **2**.

---

## 9. Summary

| Metric | Count |
|---|---|
| Modules counted | 95 (Python source files under `adaptive_reflow/`, including 12 `__init__.py`) |
| Registries counted | 7 named + 4 frozensets (`SCHEDULER_REGISTRY`, `PROTOCOL_REGISTRY`, `ROTATION_POLICY_REGISTRY`, `RUNNER_REGISTRY`, `STAGE_REGISTRY`, `CandidateRegistry`, `W2EstimatorProtocol` duck-typed) + `SCHEDULER_FAMILIES` / `POLICY_DRIVER_FAMILIES` / `MERGE_OPERATOR_FAMILIES` / `BLENDER_FAMILIES` |
| Feedback loops documented | 4 (self-reflexive, theory-grounded, hash-chained, symmetric) |
| Invariants documented | 18 (universal/molecular split, capability handshake, byte-determinism, no-torch-in-adapters, no-torch-in-universal, no-torch-in-policy-new, capability universality, legacy deprecation, seven-step engine order, bounded-merge prev-required, engine-wraps-adapter fail-closed, RMS-precondition, AUDIT_STABILITY_COLLAPSE / AUDIT_SOURCE_REVOKED hard gates, audit-code catalogue re-exports, claim-gate deferral placeholder, policy_hash invariant, algorithm_signatures provenance, forward/reverse-noise reproducibility) |
| Smells found | 28 |
| Biggest smell | **(8.14) `algorithm/scheduler.py` 3119 lines** — single file housing `SchedulerProtocol`, eight concrete schedulers, the registry, the polymorphic factory, and the codimension-sheet heuristic. Mixes runtime concerns with registration mechanics; high blast radius for refactors. |

Report path: `c:/Users/31472/codes/flowa-multistep-reinference/docs/r3-survey/01-architecture.md`.