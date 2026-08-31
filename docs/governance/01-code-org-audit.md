# Code Organization + Documentation Audit

**Auditor:** Agent A1 (code organization + documentation auditor)
**Scope:** read-only audit of package layout, documentation coverage, doc hierarchy, and build/CI state.
**Date:** 2026-08-31
**Working dir:** `c:/Users/31472/codes/flowa-multistep-reinference`

---

## §1. Module structure

The runtime package `adaptive_reflow/` ships **thirteen** peer subpackages (the
governance doc claims twelve; the new `algorithm/` package added after the
doc was last touched is the thirteenth). Each owns one concern; layered DAG
is enforced by `tests/test_universal/test_no_molecular_import.py` and the
mypy `--strict` per-module overrides in `pyproject.toml`.

| # | Subpackage | Purpose | Public API surface | Internal modules | Cross-cutting concerns |
|---|---|---|---|---|---|
| 1 | `contracts/` | Stdlib-only typed contracts (frozen dataclasses, NewType aliases, hash helpers, validators). DTB-R0/R1/R2/R4/R5/NC1/NA1/L1/L2/S1 + the generic PEP-695 state-machine library. **Leaf of the DAG.** | `RoundResultBundle`, `ChannelTransferEvidence`, `PhaseState`, `CosineScheduleConfig`, `ArchiveQuota`, `RestartPolicyAuthorityContract`, `FinalRestartPolicy`, hash helpers, validators, `AuditCode` family, the `StateMachine` library. | `archive.py`, `authority.py`, `audit.py`, `bundle.py`, `decision.py`, `envelope.py`, `hashes.py`, `operations.py`, `phase.py`, `schedule.py`, `state_machine.py`, `types.py`, `validators.py` | Backward-compat shim: lazy `__getattr__` for `RoundResultBundle` (molecule-aware home is `molecular.bundle`) breaks the `contracts.bundle ↔ molecular.bundle` cycle. `decision.py` is a placeholder for future DTB-R2/R8 additions. |
| 2 | `universal/` | Model-family-agnostic kernel: `FlowMatchingODEAdapter` Protocol, `RestartMixer`, `EnvelopeCriterion`, `Evaluator` Protocols + stdlib-only carriers + validators. **Zero molecule-specific imports** — AST guard verified by `tests/test_universal/test_no_molecular_import.py`. | `FlowMatchingODEAdapter`, `RestartMixer`, `EnvelopeCriterion`, `Evaluator`, `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace`, `AdapterCapabilities`, `EnvelopeClassification`, validators (`validate_state_bundle`, `validate_condition_delta`, `validate_integrator_trace`, `validate_capabilities`, `validate_envelope_criterion`, `validate_envelope_classification`, `validate_blend_inputs`, `validate_evaluator_artifact_hash`, `validate_unit_factor`, `validate_unit_float`, `validate_positive_int`, `validate_nonneg_int`). | `state.py`, `adapter.py`, `envelope.py`, `evaluator.py`, `mixer.py`, `validators.py` | Module docstring on `adapter.py` is exemplary (40+ lines documenting module boundary, public surface, and DTB tasks satisfied). `evaluator.py` is the leanest module (5 `"""` markers — likely the under-documented sibling). |
| 3 | `envelope/` | Runtime envelope builder + tail-budget accumulator. DTB-NC1 + DTB-L3 partial. | `FrozenEnvelopeManifestBuilder`, `TailBudgetAccumulator`, `classify_endpoint`, `StratifiedTailBudgetRow`, `EvidenceRowHash`, `ManifestBuildError`. | `classifier.py`, `manifest.py`, `tail_budget.py` | No peer-edge dependencies; pulled in by `frame/` and `molecular/`. |
| 4 | `molecular/` | Concrete pocket-conditioned 3D flow matching implementation of the universal Protocols: molecule channel vocabulary, bundle, envelope manifest, RMS-preserving restart mixer, GNINA / PoseBusters / QED / ADMET evaluators. **Implements** universal abstractions; `molecular/` does **not** import from `frame/`. | `MOLECULE_CHANNELS`, `MOLECULE_DOMAIN_BY_CHANNEL`, `MOLECULE_CALIBRATION_TARGETS`, `MOLECULE_CHANNEL_TO_METRIC`, `MoleculeChannel`, `MoleculeRoundResultBundle`, `MoleculeEnvelopeLayer/Manifest/Classification`, `MoleculeTailBudgetRow`, `MoleculeStratum`, `RMSPreservingCoordinateMixer`, `GNINAEvaluator`, `PoseBustersEvaluator`, `QEDEvaluator`, `ADMETEvaluator`, back-compat helpers. | `bundle.py`, `channels.py`, `domain.py`, `envelope.py`, `stratification.py`, `mixer.py`, `calibration_protocols.py` | Per-file-ignores cover the lazy `__getattr__` cycle breakers and forward references. |
| 5 | `frame/` | Universal round frame: `Engine`, bounded merge, channel rule, operation order, phase, trace v3, orchestrator. DTB-G1/R3/R5/S1/L1/L2/R2. | `Engine`, `EngineRoundResult`, `RoundTrace`, `LedgerRow`, `bounded_merge`, `bounded_merge_with_schedule`, `compute_channel_decision`, `check_monotonicity_property`, `RoundTraceV3`, `AdaptiveReflowPolicyOrchestrator`, `build_phase_state`, `advance_phase`, audit codes (`AUDIT_*`, `BLOCKER_*`, `ERR_*`), schema constants. | `adapter.py`, `channel_rule.py`, `engine.py`, `merge.py`, `operation.py`, `orchestrator.py`, `phase.py`, `trace.py` | Re-export shim: `frame/adapter.py` re-exports the universal `FlowMatchingODEAdapter` for back-compat. Hard-rule: `frame/engine.py` does not call `torch`. |
| 6 | `policy/` | Pure decision logic (archive, stratification, pruning, noise accounting). DTB-R4 + DTB-L3 + DTB-L4 calc. **Does not import from `frame/`.** | `SameSampleArchive`, `ArchiveEntry`, `CandidateArchiveError` family, `physical_noise_proxy`, `RMS_preserving_mixing_coefficient`, `exact_spectral_variance`, `ThreeWayDistinction`, `adversarial_stagnation_test`, `PruneGate`, `UnorderedAuditResult`, `PruneDecision`, `Stratum`, `StratumAssignment`, `dominance_ratio`, `cross_stratum_mix_rejected`. | `archive.py`, `noise_mass.py`, `pruning.py`, `stratification.py` | Audit-code constants re-exported at module level so the doc scanner indexes them. |
| 7 | `schedule/` | Outer restart-noise schedule (DTB-NA1). Closed family — `cosine.py` is the single module. | `CosineScheduleSampler`, `n_cap_for_round`, `validate_cosine_schedule_config`, `default_floor_by_channel`, `build_fresh_noise_diagnostics`, `ERR_*`. | `cosine.py` | Back-compat: `CosineScheduleSampler` now delegates to `CosineAnnealScheduler` and emits `DeprecationWarning` (algorithm layer replacement is preferred). |
| 8 | `diagnostics/` | Observation-only ledgers (`ledger_only=True`). Never influence `beta` / claim / prune. DTB-L4 observe leg. | `FreshNoiseCumulativeMassRecord`, `SpectralResidualBandProxy`, `TailDiagnosticStatus`, `empty_diagnostics`, `validate_fresh_noise_cumulative_mass_record`, `validate_spectral_residual_band_proxy`, `validate_tail_diagnostic_status`, `ERR_*`. | `ledger.py` | Split from `policy/noise_mass.py` to make observation / calculation boundary explicit at the import level. |
| 9 | `writer/` | Single-writer authority + registry + audit + handoff. DTB-S1, DTB-G2, DTB-R3. **Not** imported by `frame/` (orchestrator reaches *into* `writer/`, not vice-versa). | `WriterArbitrator`, `build_final_restart_policy`, `CoreRuntimeHandoff`, `CandidateRegistry`, `AuditTemplate`, `make_default_flowmol3_entry`, `FLOWMOL3_PINNED_COMMIT`, schema constants. | `audit.py`, `authority.py`, `handoff.py`, `registry.py` | Demand-side: `frame/orchestrator.py` imports from here. Supply-side: `writer/` reaches into `frame/orchestrator.py`, `universal/`, `contracts/`. |
| 10 | `adapters/` | Concrete `FlowMatchingODEAdapter` implementations (DTB-G1 + DTB-G2). **No `import torch`** is the hard rule. | `FlowMol3Adapter`, `FlowMol3Capabilities`, `ReferenceFlowAAdapter`, `SyntheticContinuousAdapter`/`DiscreteAdapter`/`MixedChannelAdapter`/`UnsupportedAdapter`, `ToyGaussianAdapter`, `ToyLinearAdapter`, `TwoDimFMAdapter`, integrators (`RK4Integrator`, `DPMSolverIntegrator`, `UniPCIntegrator`, `HeunIntegrator`, `DormandPrinceRK45Integrator`, `AMEDSolverIntegrator`), `KarrasPreconditioner`, channel-name constants. | `flowmol3.py`, `reference_flowa.py`, `synthetic.py`, `toy_gaussian.py`, `toy_linear.py`, `twodim_fm.py`, `mnist_fm.py`, `mnist_fm_train.py`, `stochastic_fm.py`, `_inject_forward_noise.py`, `_gnobitab_ddpmpp.py`, `karras_preconditioner.py`, `rectified_flow_cifar.py`, `integrators.py` | `TwoDimFMAdapter._native_states` is a bounded LRU cache (maxsize=128). `_inject_forward_noise.py` ships the generic P1-8 / F-25 helper. `integrators.py` registers a six-entry `INTEGRATOR_REGISTRY` and is re-exported via `from .integrators import ...` in `__init__.py`. |
| 11 | `eval/` | CPU-only DTB-R7 (calibration, paired evaluation, manifest I/O) + DTB-R8 (claim gate, promotion, rollback, layered metric panel). | `wilson_lower_bound`, `beta_lower_bound`, `ClaimGateConfig`, `evaluate_claim_gate`, `build_deferred_promotion_report`, `apply_rollback`, `LayeredMetricPanel`, `CalibrationManifest`, paired-comparison + provenance-guard machinery, W2 / coverage / energy / KDE coverage / bounded-Lipschitz metrics, paper quantities (`A_g` / `B_g` / `C_g` / `e_rho`). | `calibration.py`, `calibration_cdf.py`, `claim_gate.py`, `coverage.py`, `coverage_extra.py`, `coverage_r2.py`, `lipschitz_diagnostic.py`, `manifests.py`, `metric_panel.py`, `posterior_selection_evaluator.py`, `promotion.py`, `protocol.py`, `rdkit_oracle.py`, `rollback.py`, `synthetic_oracle.py`, `twodim_fm_evaluator.py`, `w2.py` | `rdkit_oracle.py` is chemistry-only and excluded from mypy strict (rdkit stub syntax error). |
| 12 | `legacy/` | Quarantine: pre-refactor torch-bound / `pocket_modules`-coupled modules. `__all__: list[str] = []`. `DeprecationWarning` emitted on import. **Sink only** — nothing else in `adaptive_reflow/*` imports from here. | (none — empty public surface) | `control_policy.py`, `loop.py`, `loop_contract.py`, `mechanism_adapter.py`, `metric_feedback.py`, `orchestration.py`, `plan.py`, `restart_mixer.py`, `services.py` | `metric_feedback.py` and `plan.py` are renamed (`external_metric_feedback.py` and `reinference_plan.py`); tracked under `docs/DEPRECATION.md`. |
| 13 | `algorithm/` | **Not enumerated in `ARCHITECTURE.md` §1 or §4.** Carries the four-protocol composition layer (SchedulerProtocol / PolicyDriverProtocol / MergeOperatorProtocol / RestartBlenderProtocol), the `ReInferenceRunner` orchestrator, `BatchedTrajectoryRunner`, `EvidenceDrivenScheduler`, `CodimensionSheetScheduler`, scheduler subpackage (`scheduler/`, `scheduler_extra.py`, `scheduler_r2.py`), `rotation_policy.py`, `sequential.py`, `state_machine_integration.py`. | `ReInferenceRunner`, `BatchedTrajectoryRunner`, `SchedulerProtocol`, `MergeOperatorProtocol`, `PolicyDriverProtocol`, `RestartBlenderProtocol`, the per-family implementations (`CosineAnnealScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler`, `ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler`, `EvidenceDrivenScheduler`, `FreeTrajScheduler`, `EDMScheduler`, `AdaptivePIDScheduler`, `SequentialScheduler`, `HandoffSequentialScheduler`, `MultiChannelJitteredConstantScheduler`, `JitteredConstantScheduler`, `BoundedMergeOperator`, `IdentityOperator`, `EMAOperator`, `MultiSourceKalmanMergeOperator`, `ScheduleDerivedPolicyDriver`, `ConstantPolicyDriver`, `AdaptivePolicyDriver`, `LinearBlender`, `DistanceDecayBlender`, `LatentConvexMixer`, `RMSPreservingCoordinateMixer`, `RotationPolicy`, `IntegrationIntegrator` registry), schedulers `CosineScheduleSampler`, `CosineScheduleConfig`, `n_cap_for_round`. | `batched_runner.py`, `blender.py`, `blender_extra.py`, `evidence_driver.py`, `handoff.py`, `merge_operator.py`, `merge_operator_extra.py`, `merge_operator_v3.py`, `merge_r2.py`, `policy_driver.py`, `protocol_registry.py`, `rotation_policy.py`, `round2_extra.py`, `runner.py`, `runner_registry.py`, `scheduler/`, `scheduler_extra.py`, `scheduler_r2.py`, `sequential.py`, `sequential_handoff.py`, `state_machine_integration.py` | Largest package by file count (≥ 23 .py files). Multiple "_extra" / "_r2" / "_v3" siblings per role suggest an active WIP consolidation: `merge_operator.py` / `merge_operator_extra.py` / `merge_operator_v3.py` / `merge_r2.py` are co-resident, and `scheduler/` / `scheduler_extra.py` / `scheduler_r2.py` form a three-way split. Module-level docstrings vary widely — `rotation_policy.py`, `merge_r2.py`, `round2_extra.py` are the likely under-documented siblings. |

**Cross-cutting concerns that span multiple subpackages:**

- **Audit-code vocabulary.** `AUDIT_*`, `ERR_*`, `BLOCKER_*`, `OBS_*` constants are emitted across `frame/channel_rule.py`, `contracts/validators.py`, `algorithm/{scheduler,merge_operator,blender,policy_driver}.py`, and the algorithm `scheduler/` subpackage. Each emission site must re-export the constant through the relevant `__init__.py` so the doc scanner indexes it (ADR-0005).
- **Hash determinism.** `contracts/hashes.py` ships the canonical `_canonical_json` / `_json_default` helpers (`numpy.float64` ↔ Python `float` equivalence closed in a recent polish pass). Cross-package consumers (`frame/engine.py`, `algorithm/runner.py`) import from `contracts/hashes.py` directly.
- **Per-file-ignores.** `pyproject.toml` carries a per-file-ignores table for `__init__.py` (F401, E402), `tests/**/*.py` (F401, F811, F821, B008, E402), `legacy/**/*.py` (F, B, SIM, UP, TRY, BLE), `contracts/**/*.py` (F401, F821, E402), `universal/**/*.py` (F401, F821, E402), `molecular/**/*.py` (F401, F821, E402). These are the load-bearing escape valves for the lazy `__getattr__` shims and forward references.
- **Mypy per-module overrides.** `[[tool.mypy.overrides]]` silences upstream stub noise for `rdkit.*`, `numpy.*`, and the four modules that import either of them (`adaptive_reflow.eval.rdkit_oracle`, `adaptive_reflow.adapters.twodim_fm*`, `adaptive_reflow.adapters.rectified_flow_cifar`, `adaptive_reflow.eval.twodim_fm_evaluator`, `adaptive_reflow.adapters._gnobitab_ddpmpp`).
- **Top-level `__init__.py`.** **No top-level `adaptive_reflow/__init__.py`** — by design. Importers go straight to a subpackage; this keeps the import graph explicit and prevents unintended re-exports.

---

## §2. Documentation coverage

Spot-checked module-level and public-symbol docstring quality across the
runtime tree. Counts below are `"""..."""` markers as a proxy for module /
function / class docstring presence; cross-references and paper-quantity
links are read from the file content. **Tallies are read-only observations;
no symbols were modified.**

### §2.1 Per-file docstring presence

| Subpackage / File | `def`/`class` count | `"""` count | Module docstring | Notes |
|---|---:|---:|---|---|
| `universal/adapter.py` | 11 | 16 | ✓ exemplary | 45-line module docstring + per-class docstrings + per-method docstrings. Sets the bar. |
| `universal/state.py` | 25 | (16 across file) | ✓ | `ChannelName` is a `NewType`; `TensorRef` is a `NewType`; carrier dataclasses (`StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace`) carry module-level + per-field docstrings. |
| `universal/envelope.py` | 10 | 10 | ✓ | `EnvelopeCriterion` Protocol + `EnvelopeClassification` + `Predicate`; per-method docstrings present. |
| `universal/evaluator.py` | 5 | 5 | ✓ | Smallest of the five; `Evaluator` Protocol + `ArtifactHash`. |
| `universal/mixer.py` | 6 | 12 | ✓ | `RestartMixer` Protocol + `validate_blend_inputs`. |
| `universal/validators.py` | 4 | (thin) | ✓ thin | Re-exports numeric validators; little to document. |
| `frame/engine.py` | 25 | (medium) | ✓ | `Engine` class docstring present; per-method docstrings spotty — many private helpers (`_digest`, `_canonical_json_default`, `_digest_state`, `_digest_condition`, `_ledger_row_id`, `_next_phase_state`, `_coerce_nonneg_int`, `_safe_source_round`, `_check_capabilities_advertise_dispatch`, `_safe_adapter_call`, `_policy_with_schedule_beta`, `_isfinite_or_skip`) lack docstrings. **Partial.** |
| `frame/merge.py` | 6 | (medium) | ✓ | `bounded_merge` and `bounded_merge_with_schedule` carry docstrings; `MergeAuthorityError` does not. |
| `frame/channel_rule.py` | — | — | ✓ | `compute_channel_decision`, `check_monotonicity_property`, blocker codes. Audit codes re-exported. |
| `frame/trace.py` | — | — | ✓ | `RoundTraceV3` + v2 reader + content hash + freeze + round-trip; FINAL_POLICY_WRITER_* constants documented. |
| `contracts/validators.py` | 6 | (thin) | ✓ thin | `validate_unit_float`, `validate_unit_factor`, `validate_positive_int`, `validate_nonneg_int`; trivial enough that docstrings would be tautological. |
| `contracts/types.py` | 1 (`__getattr__`) | — | ✓ thin | NewType aliases and literal-set constants only; trivial module. |
| `contracts/hashes.py` | 9 | (medium) | ✓ | `hash_artifact`, `hash_bundle_id`, `hash_trace_digest`, `hash_phase_state_digest`, `hash_policy_hash` all carry docstrings. |
| `contracts/bundle.py` | — | — | ✓ | `RoundResultBundle` is lazy-shimmed to `molecular.bundle`; `ChannelTransferEvidence` / `Decision` / `DynamicRestartTransferLedger` / `ChannelRuleInputs` / `ChannelRuleOutputs` / `NoiseBiasInputRow` documented. |
| `contracts/authority.py` | — | — | ✓ | `RestartPolicyAuthorityContract`, `LegacyCompatibilityWindow`, `FinalRestartPolicy`. |
| `contracts/state_machine.py` | — | — | ✓ | PEP-695 generic state-machine library; `StateMachine`, `TransitionBuilder`, `TransitionGuardedBuilder`, `HistoryKind`, `TransitionKind`, `GuardRejected`, `StateMachineError`, `InvalidTransitionError`, `StateNotFoundError`, `TransitionLog`, `TransitionContext`. |
| `eval/claim_gate.py` | — | — | ✓ | DTB-R8: `ClaimGateConfig`, `ClaimGateDecision`, `ClaimGateEvaluation`, `evaluate_claim_gate`. |
| `eval/calibration.py` | — | — | ✓ | DTB-R7: `wilson_lower_bound`, `beta_lower_bound`, `CalibrationBucket`, `CalibrationManifest`, `CalibrationTimeSplit`, `StabilityPerturbationProtocol`, `classify_bucket`, `manifest_digest`. |
| `eval/posterior_selection_evaluator.py` | — | — | ✓ | `EvidenceScaleGapMetric` (renamed from `PosteriorSelectionEvaluator`); explicit disclaimer that the metric is a framework-internal heuristic proxy, not a paper quantity. |
| `eval/rdkit_oracle.py` | — | — | ✓ | Chemistry-gated; mypy-strict excluded; runtime behaviour tested via `importorskip` gates. |
| `writer/registry.py` | — | — | ✓ | `CandidateEntry`, `CandidateRegistry`, `make_initial_registry`, `admit_entry`, `default_registry`, `FLOWMOL3_PINNED_COMMIT`, `make_default_flowmol3_entry`. |
| `writer/authority.py` | — | — | ✓ | `WriterArbitrator`, `build_default_authority_contract`, `build_final_restart_policy`, `verify_policy_against_ledger`, `REQUEST_MODES`, `EXECUTABLE_WRITER_MECHANISM_ID`, `CONSUMER_WRITER_ID`. |
| `adapters/_inject_forward_noise.py` | — | — | ✓ | `inject_forward_noise_into_state` — Google-style Args/Returns docstring; provenance tag documented. |
| `adapters/twodim_fm.py` | — | — | ✓ | Real CPU-runnable 2D rectified flow adapter; capability handshake, channel vocabulary, state representation documented. |
| `adapters/flowmol3.py` | — | — | ✓ | `FlowMol3Adapter`, `FlowMol3Capabilities`, `default_flowmol3_adapter`, `flowmol3_registry_entry`, `FLOWMOL3_CHANNELS`, `FLOWMOL3_CHANNEL_DOMAINS`. |
| `adapters/toy_gaussian.py` | — | — | ✓ | `ToyGaussianAdapter`, `GaussianAdapterCapabilities`, `default_toy_gaussian_adapter`, `gauss_score`. |
| `adapters/toy_linear.py` | — | — | ✓ | Smallest eight-method Protocol impl; `CHANNEL_DOMAINS`, `NATIVE_CONFIG_HASH`, `NATIVE_CONFIG_VERSION`, `SUPPORTED_CHANNELS`, `ToyLinearAdapter`, `default_toy_linear_adapter`. |
| `adapters/integrators.py` | — | — | ✓ | `RK4Integrator`, `DPMSolverIntegrator`, `UniPCIntegrator`, `HeunIntegrator`, `DormandPrinceRK45Integrator`, `AMEDSolverIntegrator`, `IntegratorProtocol`, `build_integrator`, `INTEGRATOR_REGISTRY`. |
| `algorithm/runner.py` | — | — | ✓ | 11-step orchestration lifecycle; recent fix (`_build_base_policy`, `_build_initial_phase_state`, `endpoints matrix` NaN-init) documented. |
| `algorithm/batched_runner.py` | — | — | ✓ | `BatchedTrajectoryRunner`; vectorised round generation; P0-8 / P1-8 uplifts documented. |
| `algorithm/merge_operator.py` | — | — | ✓ | `BoundedMergeOperator`, `IdentityOperator`, `EMAOperator`, `MultiSourceKalmanMergeOperator`; P0-3 fix (`cap < floor` -> return floor + audit code) recorded. **CLM-025 doc-drift** still references removed `MergeAuthorityError` raise path — flagged under CLM-042. |
| `algorithm/policy_driver.py` | — | — | ✓ | `ScheduleDerivedPolicyDriver`, `ConstantPolicyDriver`, `AdaptivePolicyDriver`; B4 docstring correction (floor divisor `2**64`, not `2**256`) recorded. |
| `algorithm/blender.py` | — | — | ✓ | `LinearBlender`, `DistanceDecayBlender`; `BLENDER_MEMORY_FRACTION_CLIPPED` audit emission; `config_hash` now hashes real configuration (temperature included). |
| `algorithm/scheduler/` | — | — | ✓ | `_core.py` (14+ scheduler families), `evidence_driven.py` (PID-lite controller). The `_paper_evidence_balance` closed-form helper is documented (Lemma 2/3 mapping). |
| `algorithm/sequential.py` | — | — | ✓ | `SequentialScheduler`, `HandoffSequentialScheduler`. |
| `molecular/bundle.py` | — | — | ✓ | `MoleculeRoundResultBundle` is the canonical home; back-compat alias re-exported via `contracts/__init__.py` lazy `__getattr__`. |
| `molecular/envelope.py` | — | — | ✓ | `MoleculeEnvelopeLayer`, `MoleculeEnvelopeManifest`, `MoleculeEnvelopeClassification`, `MoleculeTailBudgetRow`. |
| `molecular/mixer.py` | — | — | ✓ | `RMSPreservingCoordinateMixer` (concrete universal `RestartMixer` Protocol impl); back-compat `adaptive_reflow_memory_restart_coords` free function. |
| `molecular/calibration_protocols.py` | — | — | ✓ | `GNINAEvaluator`, `PoseBustersEvaluator`, `QEDEvaluator`, `ADMETEvaluator` (four concrete universal `Evaluator` Protocol impls). |
| `molecular/channels.py` | — | — | ✓ | `MOLECULE_CHANNELS`, `MoleculeChannel`, four `*ChannelRef` NewType aliases. |

### §2.2 Audit findings on documentation coverage

1. **Module-level docstrings: present on every module** in the runtime tree (the spot-check found zero `pass`-only or empty-module cases).
2. **`adaptive_reflow/algorithm/` is not catalogued in `ARCHITECTURE.md` §1 or §4.** The package is the largest by file count and ships the algorithm abstractions, but `ARCHITECTURE.md` claims "twelve peer subpackages" and lists only the other twelve. **Doc-drift** — the package needs to be added to §1 (table) and §4 (public API surface) and to §7 (file inventory).
3. **`adaptive_reflow/frame/engine.py` private helpers lack docstrings** — `_digest`, `_canonical_json_default`, `_digest_state`, `_digest_condition`, `_channel_domain_lookup`, `_ledger_row_id`, `_next_phase_state`, `_coerce_nonneg_int`, `_safe_source_round`, `_check_capabilities_advertise_dispatch`, `_safe_adapter_call`, `_policy_with_schedule_beta`, `_isfinite_or_skip`. **Severity: LOW** — these are file-internal helpers; the doc scanner does not index them.
4. **`adaptive_reflow/algorithm/` has multiple "_extra" / "_r2" / "_v3" siblings** for the same role (`merge_operator.py` / `merge_operator_extra.py` / `merge_operator_v3.py` / `merge_r2.py`; `scheduler/` / `scheduler_extra.py` / `scheduler_r2.py`). The intent is consolidation per role, but the file inventory in `ARCHITECTURE.md` §7 only enumerates the canonical module per role and skips the WIP siblings. **Severity: LOW** — doc gap, not code gap.
5. **No `examples/` Jupyter notebook referenced from the doc scanner.** `examples/01_quickstart.ipynb` is mentioned in `README.md` and `mkdocs.yml` (auto-rendered site), but the notebook itself was not spot-checked for execution state in this audit.

### §2.3 Paper-quantity cross-references

The four paper quantities are reified as framework contracts in
`adaptive_reflow/contracts/paper_quantities.py` and cross-referenced from:

- `docs/CLAIMS.md` (CLM-008, CLM-012, CLM-015, CLM-022, CLM-032, CLM-041, CLM-042, CLM-043)
- `docs/adr/0013-posterior-selection-drives-algorithm.md`
- `docs/INSIGHTS.md`
- `docs/ABLATION.md`
- `docs/audit/EPSILON_DIRECTION.md`
- `docs/audit/PHASE4_DOCSTRING_AUDIT.md`
- `docs/governance/02-algorithm-audit.md` (paper-quantity correctness audit)

The doc scanner verifies every `Asserted by` / `Disputed by` reference
in `docs/CLAIMS.md` via `tools/check_claims_consistency.py`.

### §2.4 Examples + paper references

| Public class / function | Docstring (yes/partial/no) | Type hints | Examples in docstring | Paper references | Cross-refs |
|---|---|---|---|---|---|
| `Engine.run_round` | ✓ | ✓ | minimal | ADR-0004 | ADR-0006, ARCHITECTURE.md §1, §3 |
| `bounded_merge` | ✓ | ✓ | minimal | ADR-0007 | ARCHITECTURE.md §1, DTB-R3 |
| `compute_channel_decision` | ✓ | ✓ | none | DTB-R0 §3 case 2 / case 5 | ADR-0005 |
| `RoundTraceV3` | ✓ | ✓ | none | DTB-R5 | ARCHITECTURE.md §7.1 |
| `AdaptiveReflowPolicyOrchestrator` | ✓ | ✓ | none | DTB-S1 | ARCHITECTURE.md §3.7 |
| `CosineScheduleSampler` | ✓ | ✓ | none | ADR-0010 | ADR-0012 |
| `CodimensionSheetScheduler` | ✓ | ✓ | none | Li 2026 Theorem 1 + Lemmas 2-4 | ADR-0013, ARCHITECTURE.md §1 |
| `EvidenceDrivenScheduler` | ✓ | ✓ | none | Li 2026 Theorem 1 | ADR-0013 |
| `BoundedMergeOperator` | ✓ | ✓ | none | Li 2026 Lemma 5 | CLM-025 (doc-drift), CLM-042 |
| `EvidenceScaleGapMetric` | ✓ | ✓ | none | Li 2026 Theorem 1 (heuristic proxy only) | CLM-008, ADR-0013 |
| `paper_quantities.sheet_evidence_A` | ✓ | ✓ | none | Li 2026 line 161 (verbatim) | CLM-012 |
| `paper_quantities.root_cell_packing_B` | ✓ | ✓ | none | Li 2026 line 159 (verbatim) | CLM-012 |
| `paper_quantities.per_cell_coefficient_C` | ✓ | ✓ | none | Li 2026 line 191 (verbatim) | CLM-012 |
| `paper_quantities.exterior_gap_e_rho` | ✓ | ✓ | none | Li 2026 line 128 (verbatim) | CLM-012 |
| `RMSPreservingCoordinateMixer` | ✓ | ✓ | none | DTB-L3 / ADR-0009 | ARCHITECTURE.md §1 |
| `GNINAEvaluator`, `PoseBustersEvaluator`, `QEDEvaluator`, `ADMETEvaluator` | ✓ | ✓ | none | (chemistry-domain evaluators) | ARCHITECTURE.md §7.1 |

**Invariant (load-bearing):** every public symbol in `adaptive_reflow/`
**must** be re-exported from its subpackage `__init__.py`; the doc scanner
refuses to merge a new public symbol that is not mentioned in
`ARCHITECTURE.md` §4 or §7 inside a Python fenced code block (ADR-0005).
**This invariant is the load-bearing contract between code and docs.**

---

## §3. Documentation hierarchy

The mkdocs nav (top-level + one "Paper-supporting survey (r4-survey)" section)
is short, narrow, and curated — by design, it surfaces only what a new reader
needs first. The bulk of the governance material is reachable via cross-references
from these nav entries (and the `not_in_nav` allow-list silences the
mkdocs `--strict` warning for the deeply-linked governance docs).

### §3.1 Tutorial / how-to / reference levels

| Level | Doc | Coverage |
|---|---|---|
| **Tutorial** (5-minute on-ramp) | `docs/TUTORIAL.md`, `QUICKSTART.md` | Both present; `TUTORIAL.md` covers the seven-step engine round, writing an adapter, hostile-case tests, golden snapshots, property-based tests, mutation testing, performance budgets, contributing. `QUICKSTART.md` is the adapter-author on-ramp. |
| **How-to** (task-oriented recipes) | `docs/PLUG_IN_YOUR_MODEL.md` (5 steps from `.npz` weights to baseline-vs-framework comparison), `docs/RELEASING.md`, `CONTRIBUTING.md` (4 recipes: hostile-case test, adapter, mutation test, docs scanner catalogue). | All present; the four CONTRIBUTING recipes match the four workflows named in `ARCHITECTURE.md` §10. |
| **Algorithms reference** (catalog) | `docs/ALGORITHMS.md` — full catalog of all 16 schedulers, 5 drivers, 8 merge operators, 6 blenders; paper grounding + copy-paste samples. | Present; supplementary surface `docs/schedule-theory.md` adds closed-form expressions + comparison to field standards + decision tree. |
| **Reference** (architectural governance) | `ARCHITECTURE.md` (current governance), `CONTRACTS.md` (§1–§8 typed-contract skeletons), `DESIGN_BOUNDARY.md` (DTB-R0 design boundary), `STATUS.md` (component boundary), `docs/ARCHITECTURE.md` (governance). | Present; `ARCHITECTURE_PLAN.md`, `FILE_MAPPING.md`, `SPLIT_NOTES.md` are historical and clearly marked. |
| **API reference** (auto-generated) | `docs/api/*.md` — 7 hand-written `::: adaptive_reflow.<subpackage>` directives driving mkdocstrings + griffe. `inherited_members: true` and `griffe>=1.0` pin means inherited Protocol methods and dataclass fields show up under each class heading. | Present; `mkdocs build --strict` is Gate 6 in the six-gate suite. |
| **ADRs** (load-bearing decisions) | `docs/adr/0001`–`docs/adr/0013` (MADR 4.0 format). | Present; ADR-0001 is the meta-ADR adopting the format; ADR-0013 is the paper-grounded algorithm layer. |
| **Testing** | `docs/TESTING_STRATEGY.md` (six-layer test architecture), `docs/PERFORMANCE_BUDGETS.md` (kernel p95 budgets). | Present; the tests/conftest.py and tools/check_docs_against_code.py back the tests-not-docs invariant. |
| **Audit + audit** | `docs/audit/EPSILON_DIRECTION.md`, `docs/audit/PHASE4_DOCSTRING_AUDIT.md`. | Present; PHASE4_DOCSTRING_AUDIT.md is the most recent audit surface (37 modules flagged as missing-or-stale on documentation axes). |
| **Ablation + benchmarks** | `docs/ABLATION.md`, `docs/ABLATION_METRIC_PROBE.md`, `docs/benchmark-uplifts.md`, `docs/benchmark-deep-uplifts.md`, `docs/benchmark-round2-uplifts.md`. | Present; `tools/benchmark_uplifts.py` is the canonical emitter. |

### §3.2 Nav clarity

- **Top-level `nav`** (per `mkdocs.yml`): Home, User guide (Tutorial / Plug in your model / Algorithms catalog), API reference (Contracts / Universal / Frame / Molecular / Eval / Adapters), Architecture, Testing, Paper-supporting survey (r4-survey). Six top-level buckets.
- **`not_in_nav` allow-list** (`mkdocs.yml:133-168`): explicitly silenced for the docs that are reachable via cross-references but not first-class nav landing surfaces (ADRs, `INSIGHTS.md`, `CLAIMS.md`, `paper-draft.md`, `lean/*.md`, `audit/*.md`, `review/*.md`, the algorithm-uplift plans, etc.).
- **Validation** (`mkdocs.yml:170-189`): `validation.nav.omitted_files: warn`, `validation.nav.not_found: ignore`, `validation.links.{not_found, absolute_links, unrecognized_links: ignore, anchors: warn}`. The strict build will warn on missing nav entries, broken internal links, and unresolved mkdocstrings references; cross-references to repo-root files outside `docs/` are silenced because they live at `../CHANGELOG.md` etc. and are read by the doc-claim linter, not by mkdocs.

### §3.3 Orphan docs

The following `docs/` files are linked from at least one other doc but are **not** in the mkdocs `nav` and not in the `not_in_nav` allow-list:

- None found in this audit. The `not_in_nav` allow-list is comprehensive against the spot-checked docs tree.

### §3.4 Missing docs

- **`docs/ALGORITHM.md`** — referenced by `README.md` and `mkdocs.yml` `nav` but the file is `ALGORITHMS.md` (plural). The README cross-link resolves to `ALGORITHMS.md`; the mkdocs nav entry says `ALGORITHMS.md`; both spellings match. **Not actually missing** (single canonical filename).
- **`docs/algorithm-deep-uplift-plan.md` / `docs/algorithm-round2-uplift-plan.md` / `docs/algorithm-uplift-plan.md`** — present in `not_in_nav`. They are linked from `CHANGELOG.md` and `docs/benchmark-*.md` but are not landing surfaces.
- **`docs/benchmark-uplifts.md` / `docs/benchmark-deep-uplifts.md` / `docs/benchmark-round2-uplifts.md`** — present in `not_in_nav`. Linked from `CHANGELOG.md`.
- **`docs/_benchmark_ablation.md` / `docs/_test_ablation_quick.md`** — leading-underscore convention marks them as "private to the docs tree"; in the `not_in_nav` allow-list. Not orphan, but the leading underscore is not documented as a convention.
- **`docs/architecture/index.md`** — referenced from `mkdocs.yml` (`Architecture: ARCHITECTURE.md`) but the file is the repo-root `ARCHITECTURE.md` accessed via a junction inside `docs/`. The mkdocs config comment at `mkdocs.yml:24-31` documents this as a deliberate workaround. **Not missing, but the junction mechanic is a hidden coupling** — if the junction is ever recreated without preserving the `docs/ARCHITECTURE.md` symlink, the strict build breaks.
- **`adaptive_reflow/algorithm/` documentation** — not enumerated in `ARCHITECTURE.md` §1 or §4. **Doc gap, not orphan.** This is the highest-priority missing entry.

### §3.5 Doc-claim verification

- **`tools/check_docs_against_code.py`** — walks every `*.md` file under the repo root plus `docs/`, extracts CamelCase / SCREAMING_SNAKE_CASE identifiers and `adaptive_reflow/...` path claims, verifies each resolves to a real public symbol. Exits non-zero on drift. Most recent counts: **2663** claims verified (per `CHANGELOG.md`).
- **`tools/check_claims_consistency.py`** — walks `docs/CLAIMS.md`, resolves every `Asserted by` / `Disputed by` reference, enforces the governance-surface cross-reference rule. Most recent counts: **32 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED** (CLM-016, CLM-017).
- **`mkdocs build --strict`** — fails on missing nav entries, broken internal links, and unresolved mkdocstrings references. Clean in the most recent run.

---

## §4. Build / package / CI state

### §4.1 `pyproject.toml` metadata

- **Build backend:** `hatchling.build` (`pyproject.toml:13-15`). PEP 621 metadata + PEP 517 install via `pip install .`. `only-include` filter ships the runtime package + `tools/` + `tests/` + the `README.md` / `CHANGELOG.md` / `LICENSE` triad; `legacy/` quarantine is excluded from the wheel.
- **Project metadata** (`pyproject.toml:17-90`):
  - `name = "flowa-multistep-reinference"`, `version = "0.1.0"` (initial PyPI release; **NOT** semver — `CHANGELOG.md` explicitly disclaims semver conformance).
  - `description = "Typed-contracts framework + Flow Matching ODE re-inference engine."`
  - `requires-python = ">=3.12"` (PEP 440 compatible).
  - `license = "MIT"` (SPDX expression, PEP 639 canonical form); `license-files = ["LICENSE", "LICENSE-*"]`.
  - `readme = "README.md"`.
  - `authors = [{name: "silverenternal", email: "silverenternal@users.noreply.github.com"}]`.
  - `keywords = ["flow-matching", "reinference", "machine-learning", "contracts", "typed", "research"]`.
  - `classifiers` follow PyPI's controlled vocabulary (`Development Status :: 3 - Alpha`, `Intended Audience :: Science/Research`, `Topic :: Scientific/Engineering :: Artificial Intelligence`, `Typing :: Typed`, `Programming Language :: Python :: 3.12`, `License :: OSI Approved :: MIT License`).
- **`[project.urls]`**: `Homepage`, `Repository`, `Documentation` (mkdocs site), `Issues`, `Changelog` — all populated.
- **`[project.scripts]`**: `claims-consistency = "tools.check_claims_consistency:main"` — single CLI entry point. Wired into the pre-commit hook (Gate 5).
- **`[project.optional-dependencies]`** (`pyproject.toml:104-144`):
  - `dev = ["mkdocs>=1.5", "mkdocstrings[python]>=0.24", "griffe>=1.0"]` — doc-build toolchain (Gate 6).
  - `chemistry = ["rdkit>=2024.3.1"]` — opt-in RDKit oracle.
  - `flow_matching = ["numpy>=2.0,<2.5", "scipy>=1.10"]` — opt-in 2D rectified flow adapter + offline trainer. NumPy is pinned `<2.5` because NumPy 2.5+ ships a PEP 695 `type` statement that mypy 1.x cannot parse.

### §4.2 Tool configuration

- **`[tool.pytest.ini_options]`** (`pyproject.toml:146-162`): six custom markers (`slow`, `benchmark`, `property`, `adversarial`, `stress`, `experiments`); `--strict-markers` enforced so a typo is caught at collection time.
- **`[tool.pytest-benchmark]`** (`pyproject.toml:164-178`): `min_rounds=5`, `max_time=5.0`, `warmup=true`, `warmup_iterations=10`, `sort="mean"`. Defaults tuned for fast kernel benchmarks.
- **`[tool.hypothesis]`** (`pyproject.toml:180-211`): three profiles (`default` — `max_examples=500`, `deadline=2000ms`; `slow` — `max_examples=200`, `deadline=30000ms`; `stress` — `max_examples=50`, `deadline=60000ms`). `too_slow` health check suppressed (Windows file-IO variance).
- **`[tool.ruff]`** (`pyproject.toml:213-298`): `line-length=100`, `target-version="py312"`, rule set `E/W/F/I/B/UP/SIM`. Per-file-ignores cover `__init__.py` re-exports, tests, `legacy/`, `contracts/`, `universal/`, `molecular/`.
- **`[tool.mypy]`** (`pyproject.toml:308-412`): `strict=true`, `python_version="3.12"`, `explicit_package_bases=true`, `ignore_missing_imports=true`. Per-module overrides for `_gnobitab_ddpmpp` (subclass-any relaxation), `contracts.*` / `universal.*` (type-arg + no-any-return silenced), `legacy.metric_feedback` (arg-type / var-annotated / assignment silenced), `rdkit.*` / `rdkit_stubs.*` (follow_imports="skip"), `rdkit_oracle` (ignore_errors), `numpy.*` (follow_imports="skip"), the four NumPy-importing adapters + the CIFAR adapter (`ignore_errors=true`).
- **Hatchling wheel/sdist targets** (`pyproject.toml:429-452`): explicit `only-include` lists (mirror each other) ship `adaptive_reflow/`, `tools/`, `tests/`, `README.md`, `CHANGELOG.md`, `LICENSE`, `pyproject.toml`. The `site/`, `docs/_*`, and rendered docs are explicitly excluded from the wheel.

### §4.3 `LICENSE`

- **MIT**, copyright (c) 2026 silverenternal.
- SPDX `MIT` in `pyproject.toml` matches the file.
- `LICENSE-*` glob in `license-files` covers any future re-licensing swap without `pyproject.toml` edits.

### §4.4 `CHANGELOG.md`

- **Format:** [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/). **NOT** semver (explicit disclaimer in the preamble).
- **Entries:** thirteen `[Unreleased]` sections (most recent first), followed by `[0.1.0] - 2026-08-31 - Initial PyPI release`. The `[Unreleased]` sections are the per-round audit + fix + polish history (Phase-4 code review, algorithm depth uplift round 1 + round 2, final polish pass, close 3 identified gaps, paper-grounded alignment fixes, code review fixes, paper-grounded algorithm layer, new scheduler families, algorithm abstractions, cosine-driven memory fraction + ablation, Python 3.12 pin, 2D Rectified Flow Adapter integration, algorithmic gap closure, governance scaffolding). The pattern is "every merged PR adds one `[Unreleased]` section with phase 1-4 phases, then the `[0.1.0]` entry consolidates the manifest".
- **How-to-read section:** explicit guidance for Added / Changed / Deprecated / Removed / Fixed / Security semantics. Useful.

### §4.5 CI workflows (`.github/workflows/`)

| Workflow | Trigger | What it gates |
|---|---|---|
| `ci.yml` | push to main + every PR + manual | Lint + types + docs-drift scanners (ruff, mypy, `check_docs_against_code.py`, `check_claims_consistency.py`) AND `test-docs` (pytest full suite slow/benchmark excluded + mkdocs `--strict`). Two parallel jobs. |
| `cpu-tests.yml` | push to main + every PR | ruff + pytest (non-slow, non-benchmark) + doc scanner |
| `docs-validate.yml` | push to main + every PR | ruff + doc scanner + full pytest |
| `bench-regression.yml` | weekly Mon 04:00 UTC + manual | `pytest --benchmark-only` + `tools/bench/check_budgets.py` |
| `mutation-nightly.yml` | nightly 03:00 UTC + manual | `bash tools/mutate/run_mutmut.sh`; mutation-score release gate enforced; `mutmut-report` artifact uploaded |
| `stress-nightly.yml` | nightly 03:30 UTC + manual | `pytest tests/perf/test_stress_1000_rounds.py` against the `SyntheticEvaluator` oracle; rejects leaks > 5 MB / 1000 rounds |
| `docs-deploy.yml` | push to main (paths-filtered) | `mkdocs build --strict` + GitHub Pages publish |
| `dependabot.yml` | dependabot | dependency-update PR cadence |

### §4.6 Pre-commit hooks (`.pre-commit-config.yaml`)

Six local-repo hooks mirroring the six CI gates:

| # | Hook | Mirrors CI gate | Local command |
|---|---|---|---|
| 1 | `pytest-fast` | Gate 1 | `PYTHONPATH=. python -m pytest tests/ -m 'not slow and not benchmark' --no-header -q` |
| 2 | `ruff-check` | Gate 2 | `ruff check adaptive_reflow/ tests/` |
| 3 | `mypy-strict` | Gate 3 | `python -m mypy adaptive_reflow` |
| 4 | `check-docs` | Gate 4 | `python tools/check_docs_against_code.py` |
| 5 | `check-claims` | Gate 5 | `python tools/check_claims_consistency.py` |
| 6 | `mkdocs-strict` | Gate 6 | `mkdocs build --strict` (only fires on `docs/` changes) |

Hooks run on the full tree (not staged-only) for `ruff-check` / `mypy-strict` / `check-docs` / `check-claims` so deleting a file does not silently remove its residual lint signal. `mkdocs-strict` is gated to `files: ^docs/` to keep the per-commit wall-clock bounded for source-only commits.

### §4.7 `tools/` scripts

| Script | Role | CI integration |
|---|---|---|
| `tools/check_docs_against_code.py` | Walks every `*.md` under repo root + `docs/`; verifies CamelCase / SCREAMING_SNAKE_CASE / `adaptive_reflow/...` path claims resolve to real public symbols. Most recent: 2663 verified. | Gate 4 + pre-commit `check-docs`. |
| `tools/check_claims_consistency.py` | Walks `docs/CLAIMS.md`; resolves `Asserted by` / `Disputed by` references; enforces governance-surface cross-reference rule. Most recent: 32 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED. | Gate 5 + pre-commit `check-claims` + CLI entry point `claims-consistency`. |
| `tools/benchmark_uplifts.py` | Emits the three benchmark sections (Round-1 / Round-2 / Round-2-followup). Most recent: wall-clock 8.6s for Round-2-followup, 60.5s for ablation re-run. | Manual; surfaced via `docs/benchmark-*.md`. |
| `tools/generate_golden.py` | Emits the recorded input / output JSON under `tests/golden/<kernel>/`. | Manual; replayed by `tests/property/test_golden_replay.py`. |
| `tools/bench/check_budgets.py` vs `tools/bench/budgets.json` | 20% regression threshold gate for kernel p95 budgets. | `bench-regression.yml`. |
| `tools/run_ablation.py` | 22-row ablation grid (`docs/ABLATION.md`); baseline vs framework on four scheduler families. | Manual. |
| `tools/verify_c4_on_mnist.py`, `tools/extract_mnist_test.py`, `tools/generate_mnist_samples.py`, `tools/materialize_mnist_fm.py`, `tools/materialize_twodim_fm.py`, `tools/eval_rf_cifar.py`, `tools/plot_rf_cifar.py`, `tools/run_rf_cifar_ablation.py`, `tools/compute_cifar_fid.py` | MNIST / CIFAR verification scripts. **Not part of the PR-loop gate** — gated by `importorskip("torch")` and the slow / benchmark pytest markers. | Manual / nightly only. |
| `tools/run_sota_2d_experiment.py`, `tools/run_sota_cifar_experiment.py`, `tools/run_sota_comparison.py` | SOTA comparison scripts (R5 survey). | Manual / nightly only. |
| `tools/run_metric_per_family.py` | Per-family metric panel. | Manual. |
| `tools/mutate/` (ast_mutator + mutmut.toml + run_mutmut.sh) | Mutation testing on `contracts / universal / molecular / frame`. | `mutation-nightly.yml` only. Native Windows run deferred to upstream mutmut issue 397; the Linux nightly job captures the canonical score. |
| `tools/_make_figures.py` | mkdocs figure generation. | Pre-rendered; committed. |

### §4.8 Gate state — pre-existing failures

- **No pre-existing failures detected** in this audit. All six gates are green per the most recent `CHANGELOG.md` entries (most recent: Phase-4 code-review entry, pytest 1235 passed / 7 skipped, ruff 0, mypy 0 across 90-118 source files depending on the entry, claims consistency 32 ACTIVE, mkdocs `--strict` clean).
- **Open P0/P1/P2 fixes** (per Phase-4 audit, `docs/r4-survey/19-fix-plan.md`): 7 P0 fixes totalling ~70 LoC across 7 files; 15 P1 (severity 3-4); 30 P2 (severity 1-2). These are documented as "deferred behind a future code-review pass that applies them" per `CHANGELOG.md` Phase-4 entry.

### §4.9 mkdocs `--strict` state

- `mkdocs build --strict` is clean (per `CHANGELOG.md` Phase-4 entry). The `not_in_nav` allow-list is comprehensive; the `validation.links.{not_found, absolute_links, unrecognized_links: ignore, anchors: warn}` configuration silences the cross-doc warnings for repo-root files outside mkdocs' input tree.

---

## §5. Issues found (severity-tagged)

| # | Severity | Component | Description |
|---|---|---|---|
| **A1-01** | **MEDIUM** | `ARCHITECTURE.md` §1 + §4 | **`adaptive_reflow/algorithm/` not enumerated in the architecture doc.** The package is the largest by file count (≥ 23 .py files) and ships the four-protocol composition layer (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`), `ReInferenceRunner`, `BatchedTrajectoryRunner`, `EvidenceDrivenScheduler`, `CodimensionSheetScheduler`, scheduler subpackage, rotation policy, sequential protocol, state-machine integration. `ARCHITECTURE.md` lists twelve subpackages and never names `algorithm/` in §1 (table) or §4 (public API surface). The doc scanner indexes the public symbols (they are re-exported via their respective `__init__.py`), but a reader looking for the algorithm layer's structure finds it only in `CHANGELOG.md` and `README.md`. **Doc-drift risk** for any future ADR or CLAIM that names an algorithm-layer symbol. |
| **A1-02** | **LOW** | `ARCHITECTURE.md` §7.1 (file inventory) | **`adaptive_reflow/algorithm/` module inventory is incomplete.** Only the canonical module per role is enumerated; the WIP siblings (`merge_operator_extra.py`, `merge_operator_v3.py`, `merge_r2.py`, `scheduler_extra.py`, `scheduler_r2.py`, `blender_extra.py`, `round2_extra.py`, `batched_runner.py`, `evidence_driver.py`, `rotation_policy.py`, `sequential.py`, `sequential_handoff.py`, `state_machine_integration.py`) are not in the inventory. Intent is consolidation; the doc gap is silent. |
| **A1-03** | **LOW** | `adaptive_reflow/frame/engine.py` | **Private helper docstrings missing.** `_digest`, `_canonical_json_default`, `_digest_state`, `_digest_condition`, `_channel_domain_lookup`, `_ledger_row_id`, `_next_phase_state`, `_coerce_nonneg_int`, `_safe_source_round`, `_check_capabilities_advertise_dispatch`, `_safe_adapter_call`, `_policy_with_schedule_beta`, `_isfinite_or_skip` lack module-/per-helper-level docstrings. `Engine.run_round` and the public `Engine` dataclasses are documented; the helpers are not. Severity LOW (file-internal helpers; doc scanner does not index them). |
| **A1-04** | **LOW** | `mkdocs.yml` `nav` | **`ARCHITECTURE.md` is referenced via a junction inside `docs/`.** The mkdocs config comment at `mkdocs.yml:24-31` documents this as a deliberate workaround for mkdocs requiring `docs_dir` to be a child of the config file directory. The junction mechanic is hidden coupling: if a maintainer recreates `docs/ARCHITECTURE.md` without preserving the canonical junction, the strict build breaks. Severity LOW (comment-documented workaround; works today). |
| **A1-05** | **LOW** | `docs/_*.md` convention | **`docs/_benchmark_ablation.md` and `docs/_test_ablation_quick.md` use a leading-underscore convention that is not documented.** Both files are in the `not_in_nav` allow-list (`mkdocs.yml:156-163`); the underscore is the implicit "private to the docs tree" marker. A maintainer unfamiliar with the convention may mis-file a new governance doc without the underscore and trip the strict build. Severity LOW (mkdocs would catch the mis-file via `validation.nav.omitted_files: warn`). |
| **A1-06** | **LOW** | `tools/check_docs_against_code.py` vs `docs/audit/PHASE4_DOCSTRING_AUDIT.md` | **Phase-4 docstring audit lists 37 MISSING/STALE/THIN/MISLEADING flags** on `adaptive_reflow/` modules. Each entry carries a recommended remediation; the actual remediation is documented as deferred behind a future code-review pass (per `CHANGELOG.md` Phase-4 entry). No action required for this audit; the catalogue is the audit surface itself. Severity LOW (acknowledged backlog). |
| **A1-07** | **LOW** | `adaptive_reflow/algorithm/scheduler/evidence_driven.py` | **PID round-lag annotation is not emitted on every sample.** Per Phase-4 audit F-3, the runner's data path is `sample() → engine → record_round_feedback()` so at round `r` the PID delta is from round `r-1`; the `pid_delta_by_round` dict mitigation lets callers amend round `r`'s metric, but the audit-trail surface is incomplete (severity-3 finding, partially mitigated). Severity LOW (already triaged; not a doc gap per se but a doc-vs-code drift risk for `evidence_driven.py:543-516`). |
| **A1-08** | **LOW** | `adaptive_reflow/eval/posterior_selection_evaluator.py` | **`EvidenceScaleGapMetric._compute_metrics` does not reject `nan` `eps_round`** (per Phase-4 audit M3, severity 2). The runner's `_compute_metrics(eps_round=eps_round)` clips `eps_round < 0` to `0.0` but does NOT reject `nan`. Upstream scheduler floors `eps_implicit` at `1e-6`, so practical exposure is low but the boundary is not airtight. Severity LOW (already triaged in Phase-4 audit; doc-drift risk for the boundary semantics). |
| **A1-09** | **LOW** | `docs/audit/PHASE4_DOCSTRING_AUDIT.md` | **Audit-code vocabulary sprawl.** §6.6 of the Phase-4 audit catalogues the `AUDIT_*`, `ERR_*`, `BLOCKER_*`, `OBS_*` constant sprawl as an action item for a future `AUDIT_CODE_REGISTRY`. The doc scanner currently indexes every re-exported audit code; a future consolidation pass should pin a canonical list. Severity LOW (acknowledged backlog). |
| **A1-10** | **LOW** | `adaptive_reflow/algorithm/merge_operator.py` | **CLM-025 doc-drift — `BoundedMergeOperator.merge` docstring still references removed `MergeAuthorityError` raise path.** Tracked under CLM-042 (Phase-4 fix-v2 capability set). P0-3 fix replaces `raise MergeAuthorityError` with `return floor + audit code`; the docstring update is a Phase-4 follow-up. Severity LOW (doc-drift only; runtime behaviour is correct). |

**Cross-references to the other governance audits** (per the task brief):

- **`docs/governance/02-algorithm-audit.md`** — paper-as-algorithm verification. Cross-references this audit for **paper-quantity equivalence (§1: A_g, B_g, C_g, e_rho all match paper definitions to 6+ decimals; B_g matches analytic sum to 6 decimals on sin(x))** and **math bugs (0)**. Findings M1 (e_rho/4 factor not paper-derived), M2 (cell-evidence linear vs paper's eps^2), M3 (nan eps_round not rejected) are **out of scope** for code-organization + documentation audit.
- **`docs/governance/03-framework-audit.md`** — Protocol, State Machine, Runner / Engine / Orchestrator integrity. Cross-references this audit for **state-machine inventory (17 SMs: 1 runner + 16 schedulers)**, **adapter audit (2 of 11 directly spot-checked; 9 indirectly via runner integration tests)**, and **F-A3-01..F-A3-10 framework-bug findings, all LOW or MEDIUM cosmetic / coupling**.

---

## §6. Strengths (worth preserving)

1. **Layered DAG with explicit dependency-direction rules.** `ARCHITECTURE.md` §3 lists eleven numbered rules + the five tests that enforce them. The two-layer universal / molecular split is a model for any future protocol surface (`ADR-0003`).
2. **No top-level `__init__.py`** forces importers to declare their surface explicitly. Clean failure mode for typos.
3. **Curated `__init__.py` per subpackage** — every public symbol re-exported with a curated `__all__`. The doc scanner indexes the curated surface, not the implementation.
4. **Frozen typed contracts as the leaf of the DAG** — stdlib-only, no I/O, no torch, no peer imports. The `audit.py` / `hashes.py` / `validators.py` / `state_machine.py` (PEP-695 generic library) split is exemplary.
5. **Per-file-ignores in `pyproject.toml`** document every deliberate lint relaxation with an inline rationale. The escape valves (F401 / E402 / F821) are documented, not silent.
6. **Six-gate CI / pre-commit symmetry** — every gate has a local command, a CI workflow, and a pre-commit hook. The `not_in_nav` allow-list + `validation.links` configuration in `mkdocs.yml` are equally well-documented.
7. **Mutation score is a release gate.** Four scopes (`contracts`, `universal`, `frame`, `molecular`) with explicit target scores (90% / 85% / 75% / 70%); nightly job `mutation-nightly.yml` enforces it. Surviving mutants are filed as follow-ups (ADR-0005).
8. **CHANGELOG format.** Per-PR `[Unreleased]` section with phase 1-4 phases; `[0.1.0]` consolidates the manifest. Every gate-impact section reports the gate state at the time of the entry.
9. **`not_in_nav` allow-list is comprehensive.** Spot-checked 30+ governance docs all matched an entry in the allow-list (or were first-class nav landing surfaces). No orphan docs.
10. **Audit + audit + ADR + CLAIMS + INSIGHTS + ABLATION cross-references via `[CLM-NNN]` tags.** Drift is detectable mechanically by `tools/check_claims_consistency.py`.

---

## §7. Recommendations (priority-ordered)

1. **A1-01 (MEDIUM).** Add `adaptive_reflow/algorithm/` to `ARCHITECTURE.md` §1 (table row: "Algorithm abstractions: SchedulerProtocol / MergeOperatorProtocol / PolicyDriverProtocol / RestartBlenderProtocol + the per-family implementations + `ReInferenceRunner` orchestrator + `BatchedTrajectoryRunner` + scheduler subpackage + sequential protocol + state-machine integration") and to §4 (public API surface listing the per-family implementations). Update §7 file inventory to enumerate the WIP siblings.
2. **A1-02 (LOW).** Update `ARCHITECTURE.md` §7 file inventory to enumerate the `algorithm/` siblings (`merge_operator_extra.py`, `merge_operator_v3.py`, `merge_r2.py`, `scheduler_extra.py`, `scheduler_r2.py`, `blender_extra.py`, `round2_extra.py`, `batched_runner.py`, `evidence_driver.py`, `rotation_policy.py`, `sequential.py`, `sequential_handoff.py`, `state_machine_integration.py`). Either mark them as "consolidation-in-progress, see ROADMAP.md" or remove the WIP siblings in a follow-up commit.
3. **A1-03 (LOW).** Add module-/per-helper-level docstrings to `frame/engine.py` private helpers. A single-paragraph docstring per helper is sufficient; the goal is to make the helpers greppable and self-documenting.
4. **A1-04 (LOW).** Document the `docs/ARCHITECTURE.md` junction mechanic in `docs/CONTRIBUTING.md` or a `docs/README.md` so a maintainer recreating the docs tree doesn't accidentally break the strict build.
5. **A1-05 (LOW).** Document the `docs/_*.md` leading-underscore convention (private to the docs tree, not in the strict build's nav) in `mkdocs.yml` or `docs/README.md`.
6. **A1-06 (LOW).** When the Phase-4 fix pass lands, update the 37 missing/stale docstrings in the same commit so the next doc-drift scan finds them.
7. **A1-07 (LOW).** Close F-3 in `evidence_driven.py` by emitting the round-lag annotation on every sample (not just on `record_round_feedback` calls that use the `pid_delta_by_round` dict).
8. **A1-08 (LOW).** Close M3 in `posterior_selection_evaluator.py` by rejecting `nan` `eps_round` upstream of the `total > 0` guard.
9. **A1-09 (LOW).** Pin a canonical `AUDIT_CODE_REGISTRY` in `ARCHITECTURE.md` §10 (governance) so the audit-code vocabulary sprawl from Phase-4 audit §6.6 has a single source of truth.
10. **A1-10 (LOW).** Update `BoundedMergeOperator.merge` docstring to remove the `MergeAuthorityError` raise reference; the runtime behaviour is `return floor + audit code` (post-P0-3 fix).

---

## 5-line summary

```
Docs reviewed (count): 38 modules + 13 subpackages + 8 CI workflows + 12 governance docs (ARCHITECTURE / CONTRIBUTING / DESIGN_BOUNDARY / CONTRACTS / STATUS / TUTORIAL / QUICKSTART / FAQ / ROADMAP / SECURITY / CODEOWNERS / CHANGELOG) + 13 ADRs + 7 API reference pages + 14 docs-tree docs (ABLATION, CLAIMS, INSIGHTS, etc.) + pyproject.toml + mkdocs.yml + .pre-commit-config.yaml = ~110 source-of-truth artefacts reviewed.
Gaps found (count): 10 (1 MEDIUM — `algorithm/` package missing from ARCHITECTURE.md §1/§4; 9 LOW — module-inventory gap, private-helper docstrings, junction-mechanic hidden coupling, leading-underscore convention undocumented, Phase-4 37-module docstring backlog, F-3 PID round-lag, M3 nan eps_round, audit-code vocabulary sprawl, CLM-025 doc-drift on BoundedMergeOperator).
Pre-existing gate failures (count): 0 (all six gates green per CHANGELOG.md Phase-4 entry: pytest 1235 passed / 7 skipped, ruff 0, mypy 0 across 90 source files, claims consistency 32 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED, docs scanner 2663 claims verified, mkdocs --strict clean).
Biggest issue: A1-01 — the `adaptive_reflow/algorithm/` package (the largest by file count, hosting the four-protocol composition layer + ReInferenceRunner + BatchedTrajectoryRunner + the 14+ scheduler families + scheduler subpackage + sequential protocol + state-machine integration) is not enumerated in ARCHITECTURE.md §1 or §4 or §7. The public symbols are re-exported via their `__init__.py` and indexed by the doc scanner, but the architecture governance doc misleads a reader who looks there for the algorithm layer's structure. Doc-drift risk for any future ADR or CLAIM naming an algorithm-layer symbol.
Governance grade: B+ (layered DAG with explicit dependency-direction rules and per-file-ignores documented; curated __init__.py per subpackage; six-gate CI / pre-commit symmetry; mutation score as a release gate; CHANGELOG format exemplary; not_in_nav allow-list comprehensive; cross-references via [CLM-NNN] tags; one MEDIUM doc-drift gap — algorithm/ package missing from ARCHITECTURE.md — and nine LOW gaps).
```