# FlowA / FlowoE Integration with FlowA-Multistep-Reinference Framework

This document maps the five FlowA / FlowoE Lean files in
`/c/Users/31472/codes/noise-selected-rectification-lean/` to the framework
contracts in
`c:/Users/31472/codes/flowa-multistep-reinference/adaptive_reflow/contracts/`.

The five files are:

1. `FlowA/CurrentHybridReflowEvidence.lean` (71 lines)
2. `FlowA/CurrentTrainingDataSignificance.lean` (81 lines)
3. `FlowA/DataSignificance.lean` (140 lines)
4. `FlowA/HybridReflowEffectiveness.lean` (594 lines)
5. `FlowAArchitectureProofs.lean` (1773 lines)

All five are *architecture feasibility* proofs only — no empirical metric
claims are formalised.

---

## 1. `FlowA/CurrentHybridReflowEvidence.lean`

**Lines:** 71 (generated certificate; do not edit constants by hand).

**What it proves.** This file records the SHA-256 hashes of the four
upstream reflow-evidence artifacts and freezes a snapshot of the recorded
metric panel:

* `hybridEvidenceHistoricalPanelSha256` (line 11-12)
* `hybridEvidenceSemanticExpertSha256` (line 14-15)
* `hybridEvidenceTrainingProbeSha256` (line 17-18)
* `hybridEvidenceGNINACalibrationSha256` (line 20-21)
* `hybridEvidenceActivePlanSha256` (line 23-24)
* Historical panel: 64 attempts, 61 evaluator-ready, 58 PoseBusters pass,
  QED mean 0.1751, GNINA mean -0.7400 (line 26-33)
* Semantic expert: 255 processed rows, five-state macro F1 0.9326,
  aromatic edge F1 0.9983, charged atom macro F1 0.5881, pair ECE
  0.0109, sanitization 100% (line 35-42)
* Training probe: 2 optimizer updates, diagnostic-only, no router,
  12 adapters (line 44-53)
* GNINA calibration: target-disjoint, 0 overlaps, 277 held-out, MAE
  1.7714 (above 1.5000 admission threshold), guidance not enabled
  (line 55-63)
* `hybridEvidenceCurrentRouteEndpointPanelPresent = false` (line 65-66)
* `hybridEvidenceCurrentRoutePanelBlockerWitnessed = true` (line 68-69)

**Framework contract relation.** This is the Lean-side counterpart of
the framework's `bundle.py` / `envelope.py` evidence registry. It
certifies that the *current* recorded evidence is exactly the evidence
the framework's algorithm layer may consume — no more, no less. The
explicit `hybridEvidenceCurrentRouteEndpointPanelPresent = false`
flag is the Lean analogue of the framework's
`phase_state.current_route_endpoint_panel_present = False`, which keeps
the flowa's claim claim gate closed.

---

## 2. `FlowA/CurrentTrainingDataSignificance.lean`

**Lines:** 81 (generated certificate; constants regenerated from the
dataset and preflight artifacts).

**What it proves.** Instantiates `TrainingDataCertificate` (from
`FlowA/DataSignificance.lean`) with the current recorded dataset
metrics:

* 2792 train rows, 277 dev rows, 0 target/homology/scaffold/SMILES
  overlaps (line 11-21)
* LowQED, weakGNINA, PoseBusters sub-coverage (line 22-36)
* All `*Ready` boolean flags set to `true` (line 44-53)

Then it proves:

* `current_training_data_has_unknown_pocket_learnability_evidence` —
  `SupportsUnknownPocketFitting currentTrainingDataSignificanceCertificate`
  (line 55-67)
* `current_training_data_is_not_toy_evidence` —
  `NonToyDataEvidence currentTrainingDataSignificanceCertificate`
  (line 69-71)
* `current_training_data_has_metric_outcome_supervision` —
  `HasMetricOutcomeSupervision currentTrainingDataSignificanceCertificate`
  (line 73-79)

**Framework contract relation.** This file is the Lean counterpart of
the framework's `envelope.py` data-significance contract. The
`TrainingDataCertificate` structure mirrors the JSON shape of the
framework's data-significance artifact, and the three theorems prove
the same "NonToyDataEvidence, HasUnknownPocketSplitEvidence,
HasMetricOutcomeSupervision" predicates the framework enforces
upstream of the algorithm layer. The dev/train disjointness
(targetOverlapCount = 0, etc.) matches the framework's split contract.

---

## 3. `FlowA/DataSignificance.lean`

**Lines:** 140 (hand-written contract layer).

**What it proves.** Defines the contract surface that the
`CurrentTrainingDataSignificance.lean` certificate instantiates:

* `structure FamilyCoverage` (line 14-18): `rowCount`, `uniqueTargets`,
  `uniqueScaffolds`.
* `structure TrainingDataCertificate` (line 20-52): the full set of
  recorded metrics.
* `FamilyCoverage.Significant` (line 54-59): significance predicate.
* `NonToyDataEvidence` (line 61-68): scale thresholds (≥ 2000 train,
  ≥ 200 dev, ≥ 2000 unique train targets, ≥ 1000 scaffolds).
* `HasUnknownPocketSplitEvidence` (line 70-76): disjointness on
  target/homology/scaffold/SMILES axes.
* `HasMetricOutcomeSupervision` (line 78-84): LowQED ≥ 1000, weakGNINA
  ≥ 100, PoseBusters ≥ 200, druglikePositiveRows ≥ 1000,
  bindingPositiveRows ≥ 2000, poseGeometryPositiveRows ≥ 2500.
* `HasChemistryDiversitySignal` (line 86-88): aromatic + charged sample
  positivity.
* `HasCleanStructuralEvidence` (line 90-92): zero sample-coordinate
  failures, zero RDKit problems.
* `HasMechanismLearningRoute` (line 94-103): 9 readiness flags.
* `SupportsUnknownPocketFitting` (line 105-111): the conjunction.
* `ClaimsEmpiricalEndpointSuccess := False` (line 113-114):
  *explicit* claim that this contract does *not* certify empirical
  endpoint success.
* Projection lemmas (line 116-132): pulling back the conjuncts.
* `lean_data_certificate_does_not_claim_endpoint_success`
  (line 134-138): the Lean counterpart of
  "this contract is bounded by design".

**Framework contract relation.** This is the Lean mirror of the
framework's `envelope.py` data-significance contract. The numeric
thresholds in `HasMetricOutcomeSupervision`, `NonToyDataEvidence`,
`HasCleanStructuralEvidence` are the same thresholds the framework
enforces. The `ClaimsEmpiricalEndpointSuccess := False` definition is
the explicit Lean statement that the flowa framework's "bounded
contract" claim holds — the data certificate certifies only that the
data is structurally significant, not that any particular training run
will succeed.

---

## 4. `FlowA/HybridReflowEffectiveness.lean`

**Lines:** 594 (hand-written contract layer; theorem-only).

**What it proves.** This file formalises the *mathematical boundary*
implemented by the current sampler:

* One round = one initial-value solve (line 24-83):
  `run_hybrid_rounds_has_one_more_state_than_solves`,
  `one_round_is_one_solve_with_source_and_endpoint`,
  `adaptive_reflow_R_rounds_are_R_initial_value_solves`,
  `heun_rhs_evaluations_do_not_create_extra_reflow_solves`.
* Necessary causes of a changed deterministic endpoint (line 85-145):
  `unchanged_source_and_condition_replay_the_same_endpoint`,
  `deterministic_endpoint_change_requires_source_or_condition_change`,
  `routed_but_unconsumed_expert_is_conditionally_null`,
  `routed_but_unconsumed_expert_cannot_change_deterministic_endpoint`,
  `consumed_identity_expert_is_also_conditionally_null`,
  `consumed_identity_expert_cannot_change_deterministic_endpoint`.
* Metric observability and channel freezing (line 147-203):
  `deterministic_metric_change_requires_semantic_state_change`,
  `unchanged_semantic_state_cannot_change_deterministic_metric`,
  `frozen_observable_cannot_improve_its_metric`,
  `changed_condition_without_rhs_sensitivity_leaves_endpoint_unchanged`,
  `changed_condition_without_rhs_sensitivity_leaves_metric_unchanged`,
  `semantic_change_without_metric_sensitivity_does_not_imply_gain`.
* Proxy improvement is not true-metric improvement (line 205-234):
  `proxy_gain_can_strictly_reverse_the_true_metric` (counterexample
  `false, true`), `calibrated_proxy_prevents_strict_true_metric_reversal`.
* Upstream stage bottlenecks (line 236-270):
  `end_to_end_metric_readiness_requires_materialization`,
  `materialization_failure_blocks_full_endpoint_success`,
  `full_endpoint_success_implies_every_downstream_metric_is_ready`.
* Conditional multi-objective effectiveness (line 272-319):
  `certified_round_gain_is_real_target_gain`,
  `two_certified_target_gains_compose`,
  `non_regression_is_transitive`,
  `later_non_regressive_round_preserves_earlier_strict_gain`.
* Recorded metric evidence and current claim boundary (line 321-439):
  `protectedHistorical64Snapshot` (translating the
  `hybridEvidenceHistorical*` constants into an `EndpointMetricSnapshot`),
  `protected_historical_posebusters_exceeds_ninety_percent_overall`,
  `protected_historical_posebusters_exceeds_ninety_percent_when_available`,
  `protected_historical_qed_and_gnina_values_are_preserved`,
  `protected_historical_panel_cannot_close_current_raw_claim`,
  `recordedSemanticDecoderSnapshot`,
  `semantic_decoder_snapshot_preserves_recorded_subsystem_metrics`,
  `semantic_decoder_subsystem_result_is_not_endpoint_generation_evidence`,
  `freshCurrentRouteEndpointPanelPresent`,
  `current_effectiveness_claim_is_blocked_until_fresh_panel_exists`.
* Artifact-backed execution and guidance witnesses (line 441-491):
  `latest_probe_consumes_mechanism_adapters_but_does_not_route_flowoe`,
  `latest_probe_witnesses_missing_teacher_supervision`,
  `latest_gnina_surrogate_is_split_safe_but_not_guidance_ready`,
  `latest_gnina_mae_exceeds_admission_threshold`.
* Diagnostic consequences (line 493+):
  `inductive MetricStallCause` enumerating the four architectural stall
  causes (unchangedSourceAndCondition, expertRoutedButNotConsumed,
  targetObservableFrozen, proxyNotOrderPreserving).

**Framework contract relation.** This file is the Lean counterpart of
the framework's `operations.py`, `decision.py`, `schedule.py` and
`validators.py` contracts. Each theorem is a one-to-one with a framework
invariant:

* "one round = one solve" → `adaptive_reflow.contract.solve_is_one_per_round`
* "frozen observable cannot improve its metric" → `adaptive_reflow.contract.frozen_channel_blocks_metric_gain`
* "proxy gain can strictly reverse the true metric" → `adaptive_reflow.contract.proxy_not_order_preserving`
* `protectedHistorical64Snapshot` → `adaptive_reflow.bundle.historical_panel`
* `current_effectiveness_claim_is_blocked_until_fresh_panel_exists` →
  `adaptive_reflow.contract.claim_gate_blocked_until_fresh_evidence`
* `MetricStallCause` → `adaptive_reflow.contract.metric_stall_diagnostic`

This is the lean-theorem layer that the algorithm layer's validators
import via `validators.py`.

---

## 5. `FlowAArchitectureProofs.lean`

**Lines:** 1773 (top-level architecture feasibility proof).

**What it proves.** Defines the full architecture surface as a single
formal record:

* `inductive MetricFamily` (line 23-28): materialization,
  posebustersGeometry, druglikeness, bindingContact.
* `inductive FlowChannel` (line 30-37): atom, coordinate, pairChemical,
  charge, pocketCondition, propertyCondition.
* `inductive Surface` (line 39-42): modelInternal, inferenceExternal.
* `inductive MechanismSurface` (line 44-51): mainlineCore,
  trainableModelInternal, inferenceExternal, postprocessAssisted,
  evaluatorExternal, claimGateExternal.
* `inductive StateField` (line 53-67): 14 enumerated state fields.
* `inductive MechanismId` (line 72-99): 27 named mechanism ids mirroring
  the framework's `flowa_metric_family_bundles.json`.
* `inductive ExpertId` (line 101-108): 6 expert ids.
* `inductive GeneratedObject` (line 113-115): one shared object
  (`ligandInPocket`).
* `inductive FlowPathKind` (line 117-122): 4 path kinds.
* `inductive IntegratorKind` (line 124-127): euler, heun.
* `inductive RoutePayloadView` (line 129-135): 5 payload views.
* `inductive ExpertRunWeightAuthority` (line 137-140): 2 authorities.
* `inductive ImplementedAdapterId` (line 142-148): 5 implemented
  adapters.
* `inductive PythonInterfaceId` (line 150-162): 11 python-side runtime
  symbols.
* `inductive SchemaId` (line 164-173): 8 schema names.
* `inductive PairStateView` (line 175-178): raw Markov state vs.
  valence-projected state.
* `structure CoordinateFlowContract` (line 180-186), `DiscreteFlowContract`
  (line 188-195), `IntegratorContract` (line 197-202),
  `ExpertDeltaFlowContract` (line 204-208), `AdaptiveFreezeContract`
  (line 210-216), `FlowMatchingImplementationContract` (line 218-227),
  `InferenceInitializationContract` (line 229-236),
  `InferenceSamplingContract` (line 238-244),
  `InferenceMaterializationContract` (line 246-252),
  `InferenceSidecarContract` (line 254-260),
  `InferenceRuntimeContract` (line 262-269).
* `structure FlowMainline` (line 271-277), `ExpertContract` (line 279-290),
  `MechanismContract` (line 292-299), `ReInferenceContract`
  (line 301-308), `RouterInterfaceContract` (line 310-318),
  `ExpertAdapterInterfaceContract` (line 320-329),
  `JointIntegratorInterfaceContract` (line 331-342),
  `TrainingObjectiveBoundaryContract` (line 344-348),
  `ReInferencePlanInterfaceContract` (line 350-357),
  `PythonInterfaceMirrorContract` (line 359-366),
  `FlowoERuntimeContract` (line 368-374),
  `FlowoEArchitecture` (line 376-383).
* Helper definitions: `ExpertOwns` (line 385-395), `ChannelPathKind`
  (line 397-403), `PairViewUsedForConditioning` (line 405-407),
  `PairViewUsedForTransitionMemory` (line 409-411),
  `ExpertUsableWithMainline` (line 413-418), `RouterSound`
  (line 420-424), `EveryMetricHasSomeExpert` (line 426-427),
  `AllExpertsUseSameGeneratedObject` (line 429-430),
  `ModelAndInferenceSurfacesBothPresent` (line 432-434),
  `ReInferenceCompatibleWithMainline` (line 436-444),
  `RoutePayloadViewImplemented` (line 446-451),
  `PythonInterfaceImplemented` (line 453-464),
  `SchemaImplemented` (line 466-474),
  `ImplementedAdapterFamily` (line 476-481),
  `ImplementedAdapterPrimaryChannel` (line 483-488),
  `ImplementedAdapterRegisteredInDefaultLibrary` (line 490-495),
  `ImplementedAdapterOwnsFamily` (line 497-498).

The remainder of the file (lines 500-1773) contains the explicit
*contract predicates*, the *router-soundness* lemmas, the
*inference-time reconditioning* boundary, and the bundle-level
possession lemmas proving each implemented Python adapter, schema, and
interface is reachable in `FlowoEArchitecture`.

**Framework contract relation.** This is the Lean mirror of the
framework's `types.py`, `authority.py` and `bundle.py` contracts.
Specifically:

* `MetricFamily`, `FlowChannel`, `Surface`, `MechanismSurface`,
  `StateField`, `MechanismId`, `ExpertId` →
  `adaptive_reflow.contracts.types.*`.
* `CoordinateFlowContract`, `DiscreteFlowContract`, `IntegratorContract`,
  `ExpertDeltaFlowContract`, `AdaptiveFreezeContract`,
  `FlowMatchingImplementationContract` →
  `adaptive_reflow.contracts.types.flow_mainline_contracts.*`.
* `InferenceInitializationContract`, `InferenceSamplingContract`,
  `InferenceMaterializationContract`, `InferenceSidecarContract`,
  `InferenceRuntimeContract` →
  `adaptive_reflow.contracts.types.inference_runtime_contracts.*`.
* `FlowoEArchitecture`, `RouterSound`, `ReInferenceCompatibleWithMainline`,
  `ExpertUsableWithMainline`, `AllExpertsUseSameGeneratedObject` →
  `adaptive_reflow.contracts.authority.*` and
  `adaptive_reflow.contracts.bundle.*`.
* `RoutePayloadViewImplemented`, `PythonInterfaceImplemented`,
  `SchemaImplemented`, `ImplementedAdapterFamily`,
  `ImplementedAdapterPrimaryChannel`,
  `ImplementedAdapterRegisteredInDefaultLibrary`,
  `ImplementedAdapterOwnsFamily` →
  `adaptive_reflow.contracts.bundle.*` (the implemented-adapter registry
  the framework consumes).

The architecture feasibility proof is the upstream of the
`adaptive_reflow/contracts/` boundary: every Lean statement here is the
proof obligation the framework's algorithm layer relies on.

---

## Summary

| FlowA Lean file | Framework counterpart | Proves |
| --- | --- | --- |
| `FlowA/CurrentHybridReflowEvidence.lean` | `bundle.py`, `envelope.py` | Records SHA-256 hashes of upstream artifacts and freezes the current evidence panel (PoseBusters, QED, GNINA, semantic-decoder F1, training-probe state, GNINA-MAE admission). |
| `FlowA/CurrentTrainingDataSignificance.lean` | `envelope.py` data-significance | Instantiates `TrainingDataCertificate` from recorded dataset metrics and proves `SupportsUnknownPocketFitting`. |
| `FlowA/DataSignificance.lean` | `envelope.py` data-significance contract | Defines the contract surface: significance predicates, projection lemmas, `ClaimsEmpiricalEndpointSuccess := False`. |
| `FlowA/HybridReflowEffectiveness.lean` | `operations.py`, `decision.py`, `schedule.py`, `validators.py` | Mathematical boundary of the sampler: one-round-is-one-solve, deterministic-endpoint-change, frozen-observable, proxy-not-order-preserving, end-to-end-readiness, `CertifiedRoundGain`, recorded panel snapshots, diagnostic consequences. |
| `FlowAArchitectureProofs.lean` | `types.py`, `authority.py`, `bundle.py` | Full architecture feasibility: `MetricFamily`, `FlowChannel`, `MechanismId`, `ExpertId`, all 12 contract structures, all 5 `Implemented*` registries, `FlowoEArchitecture` assembly. |

**No file proves empirical metric improvement.** All five are *bounded
contract* files: they prove what the architecture *can* and *cannot*
do, not what the algorithm *does* do on a specific run. The framework's
"bounded contract" claim is the Lean-certified version of this
self-imposed boundary.