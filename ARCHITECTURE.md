# ARCHITECTURE — flowa-multistep-reinference (current)

This document is the **project governance doc** for the post-refactor layout.
It supersedes the planning notes (`ARCHITECTURE_PLAN.md`, `FILE_MAPPING.md`,
`SPLIT_NOTES.md`) for the *current* code state. The planning notes remain as
historical artefacts explaining *why* the move happened; this file describes
*what is now true*.

**Status:** refactor + universal split complete. The package ships
two domain adapters (`molecular/` as the concrete pocket-3D flow
matching impl, `adapters/toy_gaussian.py` as the second, non-molecular
domain) plus the legacy `adapters/toy_linear.py` worked example. DTB-R0
§3 hostile-case 2 (monotonic uncertainty / stability collapse) and
case 5 (source revocation) are now **hard gates** — the audit codes
[`AUDIT_STABILITY_COLLAPSE`](adaptive_reflow/frame/channel_rule.py)
and
[`AUDIT_SOURCE_REVOKED`](adaptive_reflow/contracts/validators.py)
are re-exported from the public `__init__.py` and indexed by the
doc-drift scanner. Top-level flat modules and the in-tree `.py` files
in the repo root are **stale re-export shims** that will be removed in
a follow-up pass.

---

## 0. Universal core vs molecular concrete implementation

`adaptive_reflow/` is organised as a **two-layer split** between a
model-family-agnostic *universal core* and the *molecular concrete
implementation* that consumes it.

* **`universal/`** is the model-family-agnostic kernel. It declares the
  abstract `Protocol`s, validators, and stdlib-only carriers that *any*
  Flow Matching ODE family (molecular, graph, image, sequence) can
  implement. **`universal/` has zero molecule-specific imports** — it
  does not reach into `molecular/`, `legacy/`, `frame/`, or any molecule
  vocabulary. This invariant is enforced by
  `tests/test_universal/test_no_molecular_import.py` (AST-level guard).
* **`molecular/`** is the pocket-conditioned 3D flow matching
  *concrete* implementation of those universal abstractions. Every
  molecule-specific dataclass, channel vocabulary entry, and protocol
  impl lives here. **`molecular/` implements the universal abstractions**:
  `molecular/mixer.py` provides a concrete `RMSPreservingCoordinateMixer`
  that implements the universal `RestartMixer` Protocol; `molecular/envelope.py`
  provides `MoleculeEnvelopeLayer` / `MoleculeEnvelopeManifest` that
  implement the universal `EnvelopeCriterion` Protocol; and so on.
* `frame/` is the engine layer that drives one round end-to-end. It
  re-exports a thin shim over the universal Protocols (so the existing
  `from adaptive_reflow.frame import FlowMatchingODEAdapter` import path
  is preserved for back-compat) but its canonical home is `universal/`.
  The frame delegates to `molecular/` adapters for molecule work and to
  any future non-molecule adapter for non-molecule work — both via the
  same universal Protocol surface.

The dependency direction is therefore:

```
    universal/  ──►  frame/  (frame re-exports the universal Protocols)
        ▲
        │
        └──  molecular/  (molecular implements the universal Protocols;
                          molecular DOES NOT import from frame)
```

**Invariant (load-bearing):** *`universal/` has zero molecule-specific
imports; `molecular/` implements universal abstractions.* Breaking the
first half fails `tests/test_universal/test_no_molecular_import.py`;
breaking the second half means a new molecule-specific concept has
leaked into the universal layer where it would force every other model
family to take on molecule-shaped dependencies.

---

## 1. Layered structure overview

`adaptive_reflow/` is a single importable Python package with twelve peer
subpackages. Each subpackage owns **one concern**, and the concern is named
in the docstring of the subpackage's `__init__.py`. The subpackages are
listed in dependency order (leaf first):

| Subpackage             | Concern                                                                                    | Dep tasks satisfied                |
| ---------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------- |
| `contracts/`           | Frozen typed dataclasses, `NewType` aliases, hash helpers, validators. Leaf.               | DTB-R0/R1/R2/R4/R5/NC1/NC2/NA1/L1/L2/S1 |
| `universal/`           | Model-family-agnostic kernel: `FlowMatchingODEAdapter`, `RestartMixer`, `EnvelopeCriterion`, `Evaluator` Protocols + stdlib-only carriers + validators. No molecule-specific imports. | DTB-G1, DTB-NC1, DTB-NC2, DTB-L3, DTB-L4, DTB-R7 |
| `envelope/`            | Runtime envelope builder + tail-budget accumulator.                                         | DTB-NC1 + DTB-L3 partial           |
| `molecular/`           | Concrete pocket-conditioned 3D flow matching implementation of the universal Protocols: molecule channel vocabulary, molecule bundle, molecule envelope manifest, RMS-preserving restart mixer, GNINA/PoseBusters/QED/ADMET evaluators. | DTB-G1, DTB-NC1, DTB-NC2, DTB-L3, DTB-L4, DTB-R7 |
| `frame/`               | The universal round frame (engine, adapter protocol, bounded merge, channel rule, trace).  | DTB-G1, DTB-R3, DTB-R5, DTB-S1, DTB-L1, DTB-L2, DTB-R2 |
| `policy/`              | Pure decision logic (archive, stratification, pruning, noise accounting).                  | DTB-R4, DTB-L3, DTB-L4 calc        |
| `schedule/`            | Outer restart-noise schedule (cosine / linear / constant).                                 | DTB-NA1                            |
| `diagnostics/`         | Observation-only ledgers (`ledger_only=True`). Never influence `beta` / claim / prune.     | DTB-L4 observe                     |
| `writer/`              | Single-writer authority + registry + audit + core-runtime handoff.                         | DTB-S1, DTB-G2, DTB-R3             |
| `adapters/`            | Concrete `FlowMatchingODEAdapter` implementations (synthetic + reference + flowmol3).     | DTB-G1 + DTB-G2                    |
| `eval/`                | CPU-only DTB-R7 + DTB-R8 evaluation / reporting.                                           | DTB-R7, DTB-R8                     |
| `legacy/`              | Existing torch-bound / `pocket_modules`-coupled modules. Quarantined.                      | (none — kept only for migration)   |

### Why each subpackage exists (one paragraph each)

* **`contracts/`** — pure data. The package docstring says so explicitly:
  *"stdlib-only: no torch, no other `adaptive_reflow` imports, no IO."* It is
  the leaf every other subpackage depends on.
* **`universal/`** — the model-family-agnostic kernel. Declares the
  `FlowMatchingODEAdapter`, `RestartMixer`, `EnvelopeCriterion`, and
  `Evaluator` Protocols together with their carriers (`StateBundle`,
  `ODEConditionDelta`, `EnvelopeClassification`, …) and validators.
  Stdlib-only. **Zero molecule-specific imports** — verified by the AST
  guard at `tests/test_universal/test_no_molecular_import.py`.
* **`envelope/`** — the run-start envelope builder and the tail-budget
  accumulator. The contract types live in `contracts/`; the runtime builders
  and the per-round classifier live here.
* **`molecular/`** — the concrete pocket-conditioned 3D flow matching
  implementation of the universal abstractions: molecule channel
  vocabulary (`MOLECULE_CHANNELS`, `MoleculeChannel` enum), molecule bundle
  (`MoleculeRoundResultBundle`), molecule envelope manifest
  (`MoleculeEnvelopeLayer` / `MoleculeEnvelopeManifest` /
  `MoleculeTailBudgetRow`), RMS-preserving restart mixer
  (`RMSPreservingCoordinateMixer` implementing the universal `RestartMixer`
  Protocol), and the four molecule evaluator arms (GNINA, PoseBusters, QED,
  ADMET) implementing the universal `Evaluator` Protocol.
* **`frame/`** — everything that drives *one round* end-to-end. Engine,
  adapter protocol, bounded merge, channel rule, operation order, phase
  transitions, round-trace v3, and the orchestrator that ties them together.
  `frame/adapter.py` re-exports the universal `FlowMatchingODEAdapter`
  Protocol for back-compat with existing imports.
* **`policy/`** — stateless decision logic that is not itself a frame piece:
  archive selection, stratification, pruning, noise accounting.
* **`schedule/`** — the closed schedule family (cosine / linear / constant)
  and the stateful sampler.
* **`diagnostics/`** — observation-only rows that the policy decision *never*
  reads. Splitting them from `policy/noise_mass.py` (the calc leg) makes the
  observation / calculation boundary explicit at the import level.
* **`writer/`** — "what talks to the rest of the system". Writer arbitration,
  candidate registry, audit template, and the core-runtime handoff.
* **`adapters/`** — every concrete adapter implementation. The synthetic
  fixtures live here (not in `tests/`) so external parity harnesses can
  import them too.
* **`eval/`** — DTB-R7 (calibration, paired evaluation, manifest I/O) and
  DTB-R8 (claim gate, promotion, rollback, layered metric panel).
* **`legacy/`** — the eight pre-refactor torch-bound modules. Quarantined;
  emits a `DeprecationWarning` at import time so any new code that
  accidentally reaches in is warned.

---

## 2. Target directory tree (current)

```
flowa-multistep-reinference/
├── adaptive_reflow/                     <- the public Python package
│   ├── adapters/                        <- DTB-G1 + DTB-G2 model glue
│   │   ├── __init__.py
│   │   ├── flowmol3.py                  <- FlowMol3Adapter, FlowMol3Capabilities,
│   │   │                                  default_flowmol3_adapter, FLOWMOL3_CHANNELS,
│   │   │                                  flowmol3_registry_entry
│   │   ├── reference_flowa.py           <- ReferenceFlowAAdapter, REFERENCE_FLOWA_CHANNELS
│   │   └── synthetic.py                 <- SyntheticContinuousAdapter, SyntheticDiscreteAdapter,
│   │                                      SyntheticMixedChannelAdapter, SyntheticUnsupportedAdapter,
│   │                                      ALL_SYNTHETIC_CHANNELS, CONTINUOUS_CHANNELS,
│   │                                      DISCRETE_CHANNELS, MIXED_CHANNELS
│   ├── contracts/                       <- frozen typed dataclasses + NewTypes (DTB-R0/R1/R2/R4/R5/NC1/NA1/L1/L2/S1)
│   │   ├── __init__.py                  <- curated public surface
│   │   ├── archive.py                   <- DTB-R4: ArchiveQuota, ArchiveAuditTrail, validate_archive_quota
│   │   ├── authority.py                 <- DTB-S1: RestartPolicyAuthorityContract,
│   │   │                                  LegacyCompatibilityWindow, FinalRestartPolicy,
│   │   │                                  validate_final_restart_policy
│   │   ├── bundle.py                    <- DTB-R1: RoundResultBundle, ChannelTransferEvidence,
│   │   │                                  ChannelTransferDecision, DynamicRestartTransferLedger,
│   │   │                                  NoiseBiasInputRow, ChannelRuleInputs, ChannelRuleOutputs,
│   │   │                                  validate_round_result_bundle, validate_channel_evidence
│   │   ├── decision.py                  <- reserved for future DTB-R2/R8 additions
│   │   ├── envelope.py                  <- DTB-NC1/NC2: EnvelopeLayer, FrozenEnvelopeManifest,
│   │   │                                  EnvelopeClassification, TailBudgetRow,
│   │   │                                  validate_envelope_manifest, validate_tail_budget_row
│   │   ├── hashes.py                    <- deterministic sha256 helpers (hash_artifact, hash_*)
│   │   ├── operations.py                <- DTB-L2: OperationCompositionContract,
│   │   │                                  CommutatorResidualDiagnostic
│   │   ├── phase.py                     <- DTB-L1: PhaseState + make_default_phase_state factory
│   │   ├── schedule.py                  <- DTB-NA1: CosineScheduleConfig, CosineScheduleSample,
│   │   │                                  FreshNoiseFloor, RestartTriggerEvent
│   │   ├── types.py                     <- NewType aliases + literal-set constants
│   │   └── validators.py                <- validate_unit_factor, validate_positive_int, etc.
│   ├── diagnostics/                     <- DTB-L4 observe leg
│   │   ├── __init__.py
│   │   └── ledger.py                    <- FreshNoiseCumulativeMassRecord, SpectralResidualBandProxy,
│   │                                      TailDiagnosticStatus + validators + empty_diagnostics
│   ├── envelope/                        <- DTB-NC1 + DTB-L3 partial
│   │   ├── __init__.py
│   │   ├── classifier.py                <- observable extraction + per-layer threshold check
│   │   ├── manifest.py                  <- FrozenEnvelopeManifestBuilder, classify_endpoint,
│   │   │                                  TailBudgetAccumulator, StratifiedTailBudgetRow,
│   │   │                                  EvidenceRowHash, ManifestBuildError
│   │   └── tail_budget.py               <- tail-budget-only code (EvidenceRowHash currently)
│   ├── universal/                       <- model-family-agnostic kernel (stdlib-only, ZERO molecule imports)
│   │   ├── __init__.py                  <- re-export universal Protocols + carriers + validators
│   │   ├── state.py                     <- StateBundle, ODEConditionDelta, ODEIntegratorTrace,
│   │   │                                  NORMALIZATION_KINDS, REFERENCE_FRAMES, ChannelName, TensorRef
│   │   ├── adapter.py                   <- FlowMatchingODEAdapter Protocol + AdapterCapabilities +
│   │   │                                  RestartPolicy + ChannelDomain + validate_capabilities
│   │   ├── envelope.py                  <- EnvelopeCriterion Protocol + EnvelopeClassification +
│   │   │                                  Predicate + validate_envelope_*
│   │   ├── evaluator.py                 <- Evaluator Protocol + ArtifactHash + validate_evaluator_artifact_hash
│   │   ├── mixer.py                     <- RestartMixer Protocol + validate_blend_inputs
│   │   └── validators.py                <- numeric validators (validate_unit_factor, …)
│   ├── molecular/                       <- concrete pocket-3D flow matching impl of universal Protocols
│   │   ├── __init__.py                  <- re-export molecule channel vocabulary + concrete Protocol impls
│   │   ├── bundle.py                    <- MoleculeRoundResultBundle + validate_molecule_round_result_bundle
│   │   ├── envelope.py                  <- MoleculeEnvelopeLayer / MoleculeEnvelopeManifest /
│   │   │                                  MoleculeEnvelopeClassification / MoleculeTailBudgetRow
│   │   │                                  (implements universal EnvelopeCriterion Protocol)
│   │   ├── channels.py                  <- MOLECULE_CHANNELS, MoleculeChannel enum,
│   │   │                                  CoordinateChannelRef / ChargeChannelRef /
│   │   │                                  RawPairChannelRef / ProjectedPairChannelRef
│   │   ├── domain.py                    <- MOLECULE_DOMAIN_BY_CHANNEL fallback table
│   │   ├── stratification.py             <- MoleculeStratum / MoleculeStratumAssignment /
│   │   │                                  dominance_ratio / cross_stratum_mix_rejected
│   │   ├── mixer.py                     <- RMSPreservingCoordinateMixer
│   │   │                                  (concrete RestartMixer Protocol impl) +
│   │   │                                  adaptive_reflow_memory_restart_coords back-compat
│   │   └── calibration_protocols.py     <- GNINAEvaluator / PoseBustersEvaluator /
│   │                                      QEDEvaluator / ADMETEvaluator
│   │                                      (concrete Evaluator Protocol impls)
│   ├── eval/                            <- DTB-R7 / DTB-R8 evaluation + reporting
│   │   ├── __init__.py
│   │   ├── calibration.py               <- DTB-R7 CPU: wilson_lower_bound, beta_lower_bound,
│   │   │                                  CalibrationBucket, CalibrationManifest,
│   │   │                                  CalibrationTimeSplit, StabilityPerturbationProtocol,
│   │   │                                  classify_bucket, manifest_digest
│   │   ├── claim_gate.py                <- DTB-R8: ClaimGateConfig, ClaimGateDecision,
│   │   │                                  ClaimGateEvaluation, evaluate_claim_gate,
│   │   │                                  build_default_claim_gate_config, DEFERRED_R8_REASON
│   │   ├── manifests.py                 <- DTB-R7: write_calibration_manifest,
│   │   │                                  read_calibration_manifest, validate_manifest_frozen,
│   │   │                                  frozen_manifest_hash, DEFERRED_GPU_SENTINEL
│   │   ├── metric_panel.py              <- DTB-R8: LayeredMetricPanel, enforce_separation,
│   │   │                                  build_default_layered_metric_panel, TIER_LABELS
│   │   ├── promotion.py                 <- DTB-R8: PromotionReport, PolicyVersionHashRecorder,
│   │   │                                  build_deferred_promotion_report,
│   │   │                                  derive_policy_hash_from_version
│   │   ├── protocol.py                  <- DTB-R7: PairedComparisonArm, PairedComparisonRegistry,
│   │   │                                  EvaluatorProvenanceGuard, evaluator_guard_digest,
│   │   │                                  RoundToRoundOscillationDetector
│   │   └── rollback.py                  <- DTB-R8: RollbackFlag, RollbackAudit, apply_rollback,
│   │                                      build_disabled_rollback_flag, DEFAULT_DISABLED_REASON
│   ├── frame/                           <- the universal round frame
│   │   ├── __init__.py
│   │   ├── adapter.py                   <- DTB-G1: FlowMatchingODEAdapter Protocol, StateBundle,
│   │   │                                  ODEConditionDelta, ODEIntegratorTrace,
│   │   │                                  AdapterCapabilities, TensorRef, validators,
│   │   │                                  DOMAIN_BY_CHANNEL, NORMALIZATION_KINDS, REFERENCE_FRAMES
│   │   ├── channel_rule.py              <- DTB-R2: compute_channel_decision,
│   │   │                                  check_monotonicity_property, blocker codes,
│   │   │                                  CANONICAL_FACTOR_ORDER
│   │   ├── engine.py                    <- DTB-G1: Engine, EngineRoundResult,
│   │   │                                  RoundTrace (engine-level), LedgerRow,
│   │   │                                  PhaseState (engine-level), FEATURE_FLAG_KEY, ERR_*
│   │   ├── merge.py                     <- DTB-R3: bounded_merge, bounded_merge_with_schedule,
│   │   │                                  MergeAuthorityError, schema constants
│   │   ├── operation.py                 <- DTB-L2 runtime: build_default_composition_contract,
│   │   │                                  validate_operation_order, record_commutator_residual,
│   │   │                                  replay_default_order, ERR_*
│   │   ├── orchestrator.py              <- DTB-S1: AdaptiveReflowPolicyOrchestrator,
│   │   │                                  PolicyOrchestratorError, PolicyOrchestratorValidationError,
│   │   │                                  WRITER_ID
│   │   ├── phase.py                     <- DTB-L1 runtime: build_phase_state, advance_phase,
│   │   │                                  make_default_phase_state (run_id_seed),
│   │   │                                  validate_phase_state_transition
│   │   └── trace.py                     <- DTB-R5: RoundTraceV3 + v2 reader + content hash +
│   │                                      freeze + round_trip, FINAL_POLICY_WRITER_*
│   ├── legacy/                          <- quarantine: torch-bound / pocket_modules-coupled
│   │   ├── __init__.py                  <- emits DeprecationWarning; empty __all__
│   │   ├── control_policy.py            <- (torch import; quarantined)
│   │   ├── loop.py
│   │   ├── loop_contract.py
│   │   ├── mechanism_adapter.py
│   │   ├── metric_feedback.py           <- external_metric_feedback.py renamed
│   │   ├── orchestration.py
│   │   ├── plan.py                      <- reinference_plan.py renamed
│   │   ├── restart_mixer.py             <- (torch import; quarantined) restart_memory.py renamed
│   │   └── services.py
│   ├── policy/                          <- pure decision logic (DTB-R4 + DTB-L3 + DTB-L4 calc)
│   │   ├── __init__.py
│   │   ├── archive.py                   <- DTB-R4: SameSampleArchive, ArchiveEntry,
│   │   │                                  CandidateArchiveError family
│   │   ├── noise_mass.py                <- DTB-L4 calc: physical_noise_proxy,
│   │   │                                  RMS_preserving_mixing_coefficient,
│   │   │                                  exact_spectral_variance, ThreeWayDistinction,
│   │   │                                  adversarial_stagnation_test, ERR_*
│   │   ├── pruning.py                   <- DTB-L3: PruneGate, UnorderedAuditResult, PruneDecision
│   │   └── stratification.py            <- DTB-L3: Stratum, StratumAssignment,
│   │                                      dominance_ratio, cross_stratum_mix_rejected
│   ├── schedule/                        <- DTB-NA1 outer restart-noise schedule
│   │   ├── __init__.py
│   │   └── cosine.py                    <- CosineScheduleSampler, n_cap_for_round,
│   │                                      validate_cosine_schedule_config,
│   │                                      default_floor_by_channel,
│   │                                      build_fresh_noise_diagnostics, ERR_*
│   └── writer/                          <- single-writer authority + registry + audit + handoff
│       ├── __init__.py
│       ├── audit.py                     <- DTB-G2: AuditTemplate, DEFAULT_AUDIT_TEMPLATE,
│       │                                  validate_audit_completeness, render_audit_checklist,
│       │                                  registry_summary
│       ├── authority.py                 <- DTB-S1 runtime: WriterArbitrator,
│       │                                  build_default_authority_contract,
│       │                                  build_final_restart_policy, verify_policy_against_ledger,
│       │                                  REQUEST_MODES, EXECUTABLE_WRITER_MECHANISM_ID,
│       │                                  CONSUMER_WRITER_ID, ERR_DUAL_EXECUTABLE
│       ├── handoff.py                   <- DTB-R3: CoreRuntimeHandoff,
│       │                                  build_core_runtime_handoff, write_handoff_spec
│       └── registry.py                  <- DTB-G2: CandidateEntry, CandidateRegistry,
│                                          make_initial_registry, admit_entry, default_registry,
│                                          FLOWMOL3_PINNED_COMMIT, make_default_flowmol3_entry
├── docs/                                <- project-internal research notes
├── tests/                               <- mirrors source structure
│   ├── conftest.py                      <- package-context bootstrap; legacy-only
│   │                                      pocket_modules ancestor walk
│   ├── test_contracts/                  <- (placeholder; contracts tests live elsewhere today)
│   ├── test_diagnostics/
│   │   └── test_ledger.py               <- FreshNoiseCumulativeMassRecord + validators
│   ├── test_eval/
│   │   ├── test_calibration.py          <- wilson / beta lower bound + CalibrationBucket
│   │   ├── test_claim_gate.py           <- ClaimGateDecision + DEFERRED_R8_REASON
│   │   └── test_protocol.py             <- PairedComparisonArm + EvaluatorProvenanceGuard
│   ├── test_frame/
│   │   ├── test_engine.py               <- Engine + PhaseState + capability handshake
│   │   ├── test_merge.py                <- bounded_merge + bounded_merge_with_schedule
│   │   └── test_trace.py                <- RoundTraceV3 + content hash + freeze + round_trip
│   ├── test_policy/
│   │   ├── test_archive.py              <- SameSampleArchive + ArchiveQuota
│   │   └── test_stratification_and_pruning.py
│   ├── test_universal/                  <- universal/molecular split guards
│   │   ├── test_no_molecular_import.py  <- AST-level guard: universal/ has zero molecular imports
│   │   ├── test_adapter_universality.py <- non-molecular adapter satisfies FlowMatchingODEAdapter
│   │   ├── test_envelope_criterion.py   <- EnvelopeCriterion Protocol is non-molecule-satisfiable
│   │   └── test_mixer_protocol.py       <- RestartMixer Protocol is non-molecule-satisfiable
│   └── test_writer/
│       └── test_registry.py             <- CandidateRegistry + FLOWMOL3_PINNED_COMMIT
├── ARCHITECTURE.md                      <- this file (governance doc)
├── ARCHITECTURE_PLAN.md                 <- historical: why the move happened
├── CONTRACTS.md                         <- §1–§8 typed-contract skeletons
├── DESIGN_BOUNDARY.md                   <- DTB-R0 design boundary + non-claim boundary
├── FILE_MAPPING.md                      <- historical: old → new file moves
├── README.md                            <- entry point
├── SPLIT_NOTES.md                       <- historical: per-symbol placement
├── STATUS.md                            <- component boundary
└── todo.json                            <- canonical task list
```

---

## 3. Dependency direction rules

The package forms a strict DAG. Every edge points "downward":

```
                           ┌────────────────────┐
                           │   contracts (leaf) │  stdlib-only
                           └────────────────────┘
                              ▲          ▲
                              │          │
                ┌─────────────┘          └─────────────┐
                │                                     │
        ┌───────┴────────┐                   ┌────────┴───────┐
        │   schedule     │                   │    policy      │
        └────────────────┘                   └────────────────┘
                              ▲                  ▲   ▲
                              │                  │   │
                              │          ┌───────┘   │
                              │          │           │
                       ┌──────┴──────────┴───┐  ┌────┴───────────┐
                       │      envelope      │  │   diagnostics   │
                       └────────────────────┘  └────────────────┘
                                       ▲
                                       │
                       ┌───────────────┴───────────────┐
                       │           universal           │  stdlib-only
                       │   (kernel Protocols +        │  zero molecule
                       │    validators + carriers)     │  imports
                       └───────────────────────────────┘
                          ▲                          ▲
                          │                          │
                          │ re-export shim           │ concrete impl
                          │                          │
                  ┌───────┴───────┐         ┌────────┴────────┐
                  │    frame      │         │    molecular    │
                  │   (engine +   │         │  (concrete      │
                  │    adapter    │         │   pocket-3D     │
                  │    protocol + │         │   flow matching │
                  │    bounded    │         │   of the        │
                  │    merge +    │         │   universal     │
                  │    channel    │         │   Protocols)    │
                  │    rule + …)  │         │                 │
                  └───────────────┘         └─────────────────┘
                          ▲           ▲           ▲
                          │           │           │
        ┌─────────────────┐│           │┌──────────┘
        │   adapters      ││           ││  writer  │
        └─────────────────┘│           │└──────────┘
                           │           │
                    ┌──────┴────┐  ┌───┴────┐
                    │   eval    │  │legacy  │
                    └───────────┘  └────────┘
                                     (sink only;
                                      nothing else
                                      imports from here)
```

### Rules

1. **`contracts/` imports nothing from `adaptive_reflow/*`.** It is stdlib-only.
2. **`universal/` imports nothing from `adaptive_reflow/*` except possibly
   itself.** It is the model-family-agnostic kernel and **must have zero
   molecule-specific imports** (no `molecular/`, no `legacy/`, no
   `frame/`-only types, no molecule vocabulary). The Protocol surface is
   defined here; the concrete molecule implementation lives in `molecular/`.
3. **`frame/` may import from `contracts/`, `universal/`, `envelope/`,
   `policy/`, `schedule/`, `diagnostics/`.** The frame is the universal round
   driver; it reaches into the lower layers to consume them. The frame
   re-exports a thin shim over `universal/adapter.py`'s
   `FlowMatchingODEAdapter` Protocol for back-compat.
4. **`policy/` may import from `contracts/`, `envelope/manifest.py`.** It must
   not import from `frame/` — the channel rule and bounded merge live in
   `frame/` because they are *applied* during a round, not because they are
   pure decision logic.
5. **`molecular/` may import from `universal/` and `contracts/`.** It must
   not import from `frame/` (the molecule impl is a universal Protocol
   *consumer*, not a frame piece). It implements the universal
   `FlowMatchingODEAdapter` / `RestartMixer` / `EnvelopeCriterion` /
   `Evaluator` Protocols.
6. **`schedule/`, `envelope/`, `diagnostics/` may import only from `contracts/`
   (and within their own package).** No peer edges.
7. **`writer/` is the single-writer authority.** It may import from `contracts/`,
   `universal/`, `frame/`, `adapters/`, `policy/` (it needs `WriterArbitrator`,
   `AdaptiveReflowPolicyOrchestrator`, `CandidateRegistry`, etc.). It must not
   be imported by `frame/` (the orchestrator reaches *into* `writer/`, never
   the other way around).
8. **`adapters/` may import from `universal/` (for the Protocol + StateBundle +
   ODEConditionDelta types) and from `contracts/`.** No edge into `writer/`,
   `policy/`, `eval/`.
9. **`eval/` may import from `universal/`, `frame/`, `contracts/`, and its own
   package.** No edge into `writer/`, `policy/`, `adapters/`.
10. **`legacy/` is a sink.** Nothing else in `adaptive_reflow/*` imports from
    `legacy/`. The `legacy/__init__.py` emits a `DeprecationWarning` on import.
11. **No peer-level cycles.** The import graph is a DAG; if you find a cycle,
    the design is wrong.

These rules are enforced by:

* Module docstrings stating the boundary.
* `tests/test_frame/test_engine.py::test_no_torch_in_any_new_file` asserting
  that no engine / adapter module imports `torch`.
* `tests/test_policy/test_stratification_and_pruning.py::TestNoTorchDependency::test_no_torch_in_new_modules`
  asserting that the new policy modules don't pull `torch` transitively.
* `tests/test_universal/test_no_molecular_import.py` asserting (via AST walk)
  that no file in `adaptive_reflow/universal/` imports from
  `adaptive_reflow.molecular`.
* `tests/test_universal/test_envelope_criterion.py`,
  `tests/test_universal/test_mixer_protocol.py`, and
  `tests/test_universal/test_adapter_universality.py` asserting that the
  `EnvelopeCriterion`, `RestartMixer`, and `FlowMatchingODEAdapter` Protocols
  are satisfiable by non-molecular adapters.
* The `legacy/__init__.py` `DeprecationWarning`.

---

## 4. Public API surface (top-level `__init__.py` exports)

There is **no top-level `adaptive_reflow/__init__.py`**. Importers go directly
to the subpackage they need; each subpackage has a curated `__init__.py` that
re-exports only the documented public surface.

### 4.1 `adaptive_reflow.contracts`

```python
from adaptive_reflow.contracts import (
    # --- §1 DTB-R1 bundle ---
    RoundResultBundle,
    ChannelTransferEvidence,
    ChannelTransferDecision,
    DynamicRestartTransferLedger,
    NoiseBiasInputRow,
    ChannelRuleInputs,
    ChannelRuleOutputs,
    validate_round_result_bundle,
    validate_channel_evidence,
    # --- §2 DTB-NC1 / NC2 envelope ---
    EnvelopeClassification,
    EnvelopeLayer,
    FrozenEnvelopeManifest,
    TailBudgetRow,
    validate_envelope_manifest,
    validate_tail_budget_row,
    # --- Hash helpers ---
    hash_artifact,
    hash_bundle_id,
    hash_phase_state_digest,
    hash_policy_hash,
    hash_trace_digest,
    # --- §5 DTB-L1 phase ---
    PhaseState,
    empty_provenance,
    make_default_phase_state,
    make_default_phase_state_digest,
    validate_phase_state,
    # --- §4 DTB-NA1 schedule ---
    CosineScheduleConfig,
    CosineScheduleSample,
    FreshNoiseFloor,
    RestartTriggerEvent,
    # --- NewType aliases + literal-set constants ---
    ArtifactHash, BundleId, ChannelName, ChargeChannelRef,
    ComplementBlockerCode, ConditionDigest, CoordinateChannelRef,
    EvaluatorProvenanceRef, FactorValue, FeedbackEvidenceRef,
    FeedbackMode, FrameSpec, LedgerRowId, ManifestId,
    MaterializationEvidenceRef, MechanismId, PolicyId,
    ProjectedPairChannelRef, ProvenanceChain, RawPairChannelRef,
    RestartTriggerCode, RunId, SampleId, ShapeSpec, TailBudgetRowId,
    TraceDigest, TriggerId,
    AUTHORITY_MODES, CHANNEL_NAMES, COMPLEMENT_BLOCKER_CODES,
    DEFAULT_OPERATION_ORDER, FEEDBACK_MODES, FRESH_NOISE_FLOOR_SOURCES,
    OPERATION_STEPS, RESTART_TRIGGER_CODES, SCHEDULE_FAMILIES,
    SCHEDULE_PHASES,
    # --- Validators ---
    ValidationResult,
    validate_nonneg_int,
    validate_positive_int,
    validate_unit_factor,
    validate_unit_float,
    # --- §7 DTB-S1 authority ---
    FinalRestartPolicy,
    LegacyCompatibilityWindow,
    RestartPolicyAuthorityContract,
    validate_final_restart_policy,
    # --- §8 DTB-R4 archive ---
    ArchiveAuditTrail,
    ArchiveQuota,
    validate_archive_quota,
    # --- §6 DTB-L2 operation ---
    CommutatorResidualDiagnostic,
    OperationCompositionContract,
)
```

### 4.2 `adaptive_reflow.frame`

```python
from adaptive_reflow.frame import (
    # --- adapter protocol + carriers ---
    FlowMatchingODEAdapter, StateBundle, ODEConditionDelta,
    ODEIntegratorTrace, AdapterCapabilities, TensorRef,
    RestartPolicy, CapabilityMismatchError, CapabilityMissingError,
    DOMAIN_BY_CHANNEL, NORMALIZATION_KINDS, REFERENCE_FRAMES,
    validate_capabilities, validate_condition_delta,
    validate_integrator_trace, validate_state_bundle,
    # --- engine ---
    Engine, EngineRoundResult, RoundTrace, LedgerRow, PhaseState,
    ENGINE_VERSION, DEFAULT_OPERATION_STEPS, FEATURE_FLAG_KEY, ERR_*,
    # --- bounded merge ---
    bounded_merge, bounded_merge_with_schedule, MergeAuthorityError,
    MERGE_AUTHORITY_SCHEMA_NAME, MERGE_AUTHORITY_SCHEMA_VERSION,
    # --- operation order ---
    build_default_composition_contract, validate_operation_order,
    record_commutator_residual, replay_default_order,
    DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE,
    DEFAULT_OPERATION_COMPOSITION_VERSION, DEFAULT_OPERATION_ORDER,
    ERR_*,
    # --- channel rule ---
    compute_channel_decision, check_monotonicity_property,
    required_factors_in_unit_interval, CANONICAL_FACTOR_ORDER,
    BLOCKER_*,
    # --- phase runtime ---
    build_phase_state, advance_phase, make_default_phase_state,
    validate_phase_state_transition,
    # --- trace ---
    RoundTraceV3, compute_round_trace_v3_content_hash,
    freeze_round_trace_v3, read_round_trace_v2,
    round_trip_round_trace_v3, ROUND_TRACE_V2_SCHEMA_NAME,
    ROUND_TRACE_V3_SCHEMA_NAME, FINAL_POLICY_WRITER_*,
    PRODUCER_MODES, ALLOWED_FINAL_POLICY_WRITERS,
    # --- orchestrator ---
    AdaptiveReflowPolicyOrchestrator, PolicyOrchestratorError,
    PolicyOrchestratorValidationError, WRITER_ID,
)
```

### 4.3 `adaptive_reflow.policy`

```python
from adaptive_reflow.policy import (
    # --- archive (DTB-R4) ---
    ArchiveEntry, SameSampleArchive,
    CandidateArchiveError, CandidateArchiveLineageError,
    CandidateArchiveValidationError,
    # --- noise mass (DTB-L4 calc) ---
    physical_noise_proxy, RMS_preserving_mixing_coefficient,
    exact_spectral_variance, ThreeWayDistinction,
    adversarial_stagnation_test, ERR_*,
    # --- pruning (DTB-L3) ---
    PruneDecision, PruneGate, UnorderedAuditResult,
    # --- stratification (DTB-L3) ---
    Stratum, StratumAssignment, dominance_ratio,
    cross_stratum_mix_rejected,
)
```

### 4.4 `adaptive_reflow.schedule`

```python
from adaptive_reflow.schedule import (
    CosineScheduleSampler, n_cap_for_round,
    validate_cosine_schedule_config, default_floor_by_channel,
    build_fresh_noise_diagnostics, ERR_*,
)
```

### 4.5 `adaptive_reflow.diagnostics`

```python
from adaptive_reflow.diagnostics import (
    FreshNoiseCumulativeMassRecord,
    SpectralResidualBandProxy,
    TailDiagnosticStatus,
    empty_diagnostics,
    validate_fresh_noise_cumulative_mass_record,
    validate_spectral_residual_band_proxy,
    validate_tail_diagnostic_status,
    ERR_*,
)
```

### 4.6 `adaptive_reflow.envelope`

```python
from adaptive_reflow.envelope import (
    EvidenceRowHash,
    FrozenEnvelopeManifestBuilder,
    ManifestBuildError,
    StratifiedTailBudgetRow,
    TailBudgetAccumulator,
    classify_endpoint,
)
```

### 4.7 `adaptive_reflow.writer`

```python
from adaptive_reflow.writer import (
    # --- audit ---
    AuditTemplate, DEFAULT_AUDIT_TEMPLATE,
    registry_summary, render_audit_checklist,
    validate_audit_completeness,
    # --- authority ---
    WriterArbitrator, WriterArgumentError,
    build_default_authority_contract, build_final_restart_policy,
    verify_policy_against_ledger,
    CONSUMER_WRITER_ID, DEFAULT_AUTHORITY_CONTRACT_VERSION,
    DEFAULT_MODE_FLAGS, DIAGNOSTIC_WRITER_MECHANISM_ID,
    ERR_DUAL_EXECUTABLE, EXECUTABLE_WRITER_MECHANISM_ID,
    LEGACY_SCHEMA_READ_COMPATIBILITY_VERSION, REQUEST_MODES,
    # --- handoff ---
    CoreRuntimeHandoff, CoreRuntimeHandoffError,
    build_core_runtime_handoff, write_handoff_spec,
    CORE_RUNTIME_HANDBOFF_SCHEMA_NAME, CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION,
    CORE_RUNTIME_OWNER,
    # --- registry ---
    CandidateEntry, CandidateRegistry, TaskCondition,
    admit_entry, default_registry, make_default_flowmol3_entry,
    make_initial_registry, AdapterStatus,
    FLOWMOL3_PINNED_COMMIT,
)
```

### 4.8 `adaptive_reflow.adapters`

```python
from adaptive_reflow.adapters import (
    # --- FlowMol3 ---
    FlowMol3Adapter, FlowMol3Capabilities,
    default_flowmol3_adapter, FLOWMOL3_CHANNELS,
    flowmol3_registry_entry,
    # --- Reference FlowA ---
    ReferenceFlowAAdapter, REFERENCE_FLOWA_CHANNELS,
    # --- Synthetic fixtures (also used by parity harnesses) ---
    SyntheticContinuousAdapter, SyntheticDiscreteAdapter,
    SyntheticMixedChannelAdapter, SyntheticUnsupportedAdapter,
    ALL_SYNTHETIC_CHANNELS, CONTINUOUS_CHANNELS,
    DISCRETE_CHANNELS, MIXED_CHANNELS,
)
```

### 4.9 `adaptive_reflow.eval`

```python
from adaptive_reflow.eval import (
    # --- calibration (DTB-R7 CPU) ---
    wilson_lower_bound, beta_lower_bound,
    BucketKey, CalibrationBucket, CalibrationDatasetId,
    CalibrationManifest, CalibrationTimeSplit,
    ConfidenceLevel, IsoTimestamp, SampleCount,
    StabilityPerturbationProtocol,
    classify_bucket, manifest_digest,
    CHANNEL_NAMES_FOR_CALIBRATION, LOWER_BOUND_METHODS,
    PREDECLARED_SAFETY_METRICS,
    # --- claim gate (DTB-R8) ---
    ClaimGateArgumentError, ClaimGateConfig, ClaimGateDecision,
    ClaimGateEvaluation, build_default_claim_gate_config,
    evaluate_claim_gate, DEFERRED_R8_REASON,
    # --- manifests (DTB-R7) ---
    JsonString, ValidationResult,
    write_calibration_manifest, read_calibration_manifest,
    validate_manifest_frozen, frozen_manifest_hash,
    DEFERRED_GPU_SENTINEL,
    # --- metric panel (DTB-R8) ---
    LayeredEvidenceTiers, LayeredMetricPanel,
    LayeredMetricPanelArgumentError,
    build_default_layered_metric_panel, enforce_separation,
    TIER_LABELS,
    # --- promotion (DTB-R8) ---
    PolicyVersionHashRecorder, PromotionArgumentError, PromotionReport,
    build_deferred_promotion_report,
    derive_policy_hash_from_version,
    DEFERRED_COST, DEFERRED_GAIN, DEFERRED_R8_REASON,
    # --- protocol (DTB-R7) ---
    ArmName, ConfigHash, EvaluatorProvenanceGuard, EvaluatorVersion,
    MaterializationRoute, PairedComparisonArm, PairedComparisonRegistry,
    PolicyHash, RoundToRoundOscillationDetector, TargetPocketHash,
    evaluator_guard_digest, PAIRED_ARM_KINDS,
    # --- rollback (DTB-R8) ---
    RollbackArgumentError, RollbackAudit, RollbackFlag,
    apply_rollback, build_disabled_rollback_flag,
    DEFAULT_DISABLED_REASON,
)
```

### 4.10 `adaptive_reflow.legacy`

`__all__: list[str] = []`. Nothing is re-exported. Importing the subpackage
emits a `DeprecationWarning`. Existing modules are kept so legacy tests
continue to work until they are migrated.

### 4.11 `adaptive_reflow.universal`

The canonical home for the model-family-agnostic kernel. Stdlib-only,
zero molecule-specific imports. The Protocols defined here are the
universal surface that every concrete model family (molecular, graph,
image, sequence, …) must implement.

```python
from adaptive_reflow.universal import (
    # --- Pure-data carriers (state) ---
    StateBundle, ODEConditionDelta, ODEIntegratorTrace,
    # --- Pure-data carriers (adapter) ---
    AdapterCapabilities,
    # --- Pure-data carriers (envelope) ---
    EnvelopeClassification, EnvelopeCriterion,
    # --- NewType aliases ---
    ArtifactHash, BundleId, ChannelDomain, ChannelName,
    ComplementBlockerCode, Predicate, RestartPolicy, TensorRef,
    # --- String enums ---
    NORMALIZATION_KINDS, REFERENCE_FRAMES,
    # --- Protocols (the model-family-agnostic kernel) ---
    FlowMatchingODEAdapter,    # Protocol: engine + adapter handshake
    RestartMixer,              # Protocol: per-round coordinate blender
    Evaluator,                 # Protocol: per-channel scorer (R7)
    # --- Exceptions ---
    CapabilityMismatchError, CapabilityMissingError,
    # --- Validators (state / adapter / envelope / mixer / numeric) ---
    validate_state_bundle, validate_condition_delta,
    validate_integrator_trace, validate_capabilities,
    validate_envelope_criterion, validate_envelope_classification,
    validate_blend_inputs, validate_evaluator_artifact_hash,
    validate_unit_factor, validate_unit_float,
    validate_positive_int, validate_nonneg_int,
    ValidationResult,
)
```

### 4.12 `adaptive_reflow.molecular`

The concrete pocket-conditioned 3D flow matching implementation of the
universal abstractions. Every name below is *molecule-specific* — it lives
here, not in `universal/`, so that no non-molecule adapter is forced to
take on molecule-shaped dependencies.

```python
from adaptive_reflow.molecular import (
    # --- Molecule channel vocabulary ---
    MOLECULE_CHANNELS, MOLECULE_DOMAIN_BY_CHANNEL,
    MOLECULE_CALIBRATION_TARGETS, MOLECULE_CHANNEL_TO_METRIC,
    MoleculeChannel,
    CoordinateChannelRef, ChargeChannelRef,
    RawPairChannelRef, ProjectedPairChannelRef,
    # --- Pure-data carriers (molecule bundle) ---
    MoleculeRoundResultBundle,
    # --- Pure-data carriers (molecule envelope) ---
    MoleculeEnvelopeLayer, MoleculeEnvelopeManifest,
    MoleculeEnvelopeClassification, MoleculeTailBudgetRow,
    # --- Pure-data carriers (molecule stratification) ---
    MoleculeStratum, MoleculeStratumAssignment,
    # --- Concrete RestartMixer Protocol impl ---
    RMSPreservingCoordinateMixer,
    adaptive_reflow_memory_restart_coords,
    # --- Concrete Evaluator Protocol impls (four arms) ---
    GNINAEvaluator, PoseBustersEvaluator,
    QEDEvaluator, ADMETEvaluator,
    gnina_evaluator, posebusters_evaluator,
    qed_evaluator, admet_evaluator,
    # --- Validators ---
    validate_molecule_round_result_bundle,
    validate_molecule_envelope_manifest,
    validate_molecule_tail_budget_row,
    # --- Back-compat helpers ---
    attach_molecule_channels,
)
```

---

## 5. Adapter Protocol — how to add a new model

> **Authoritative spec**: [`docs/ADAPTER_INTERFACE_SPEC.md`](docs/ADAPTER_INTERFACE_SPEC.md)
> covers the full Protocol surface, capability handshake, mixer/envelope/evaluator
> registration, per-round lifecycle, fail-closed failure modes, hard rules,
> versioning, and a worked `ToyLinearAdapter` example. This section is the
> short version; defer to the spec when writing a real adapter.

The Protocol lives in `adaptive_reflow.universal.adapter` (DTB-G1). The
concrete state carriers (`StateBundle`, `ODEConditionDelta`,
`ODEIntegratorTrace`, `TensorRef`) are in
`adaptive_reflow.universal.state`. The `RestartPolicy` alias is in
`adaptive_reflow.universal.adapter`; the underlying class
`FinalRestartPolicy` is in `adaptive_reflow.contracts.authority`.

### 5.1 Reference implementations — `ToyLinearAdapter` and `ToyGaussianAdapter`

Two in-tree worked examples ship today:

* **`ToyLinearAdapter`** at `adaptive_reflow/adapters/toy_linear.py`
  — the smallest possible eight-method `FlowMatchingODEAdapter`
  implementation. One continuous channel, a deterministic linear ODE
  step, no restart, no condition. Sanity-check target for the universal
  engine and copy-this-skeleton template for new adapter authors.
* **`ToyGaussianAdapter`** at `adaptive_reflow/adapters/toy_gaussian.py`
  — the **second domain**. A 1-D Gaussian mixture flow whose ODE
  `dx/dt = -x + target_mean` admits a closed-form solution. Exercises
  the full eight-method Protocol with `has_restart_boundary=True` and
  `has_condition_injection=True`. Exists to prove that the universal
  layer is universal: the exact same engine + Protocol + capability
  handshake + ledger row emission that drives `molecular/` also drives
  a non-molecule domain, with zero references to
  `adaptive_reflow.molecular` (enforced by
  `tests/test_universal/test_toy_gaussian.py::test_universal_imports_no_molecular`).

Tests at `tests/test_adapters/test_toy_linear.py` and
`tests/test_universal/test_toy_gaussian.py` cover:

- Capability handshake values (10 booleans + channels + mixer)
- `build_initial_state` happy path and `source_round < 0` rejection
- `solve_ode` determinism: same `(state, seed, steps)` → same next state
- Fail-closed for unadvertised capabilities: `compose_condition` and
  `apply_restart_distribution` raise `CapabilityMissingError` when the
  corresponding capability is `False`

### 5.2 Step 1 — declare the channel vocabulary

For a new model, decide what `ChannelName` values the model carries. For
a Stable Diffusion 3 latent model:

```python
class LatentImageAdapter:
    SUPPORTED_CHANNELS = (ChannelName("latent"),)
    CHANNEL_DOMAINS = {ChannelName("latent"): "latent"}
```

For a molecule coordinate flow matching model:

```python
class CoordinateFlowMolAdapter:
    SUPPORTED_CHANNELS = (
        ChannelName("coordinate"),
        ChannelName("charge"),
        ChannelName("raw_pair"),
        ChannelName("projected_pair"),
    )
    CHANNEL_DOMAINS = {
        ChannelName("coordinate"): "continuous",
        ChannelName("charge"): "continuous",
        ChannelName("raw_pair"): "discrete",
        ChannelName("projected_pair"): "discrete",
    }
```

### 5.3 Step 2 — implement `FlowMatchingODEAdapter`

Implement the eight methods listed in
`docs/ADAPTER_INTERFACE_SPEC.md` §2. The actual adapter skeleton is
the `ToyLinearAdapter` body — copy and adapt. The implementation may
delegate to torch / RPC / subprocess / in-memory dict as long as the
Protocol invariants hold.

```python
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    FlowMatchingODEAdapter,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)


class CoordinateFlowMolAdapter(FlowMatchingODEAdapter):
    """Adapter for a coordinate + charge + pair flow matching model."""

    def __init__(self):
        self._caps = AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=True,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            supported_channels=(
                ChannelName("coordinate"),
                ChannelName("charge"),
                ChannelName("raw_pair"),
                ChannelName("projected_pair"),
            ),
            channel_domains={
                ChannelName("coordinate"): "continuous",
                ChannelName("charge"): "continuous",
                ChannelName("raw_pair"): "discrete",
                ChannelName("projected_pair"): "discrete",
            },
            # Pluggable backend declarations.
            required_mixer=<your MixerClass>,
            exposed_envelope_criteria=(<your criteria>,),
            exposed_evaluators=(<your evaluators>,),
            native_config_hash="<your config hash>",
            native_config_version="<your semver>",
        )

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    def build_initial_state(self, batch_id, sample_id, *, source_round=0):
        # See ToyLinearAdapter.build_initial_state for the pattern.
        ...

    def export_endpoint(self, state): ...
    def detach_and_validate_endpoint(self, state): ...
    def apply_restart_distribution(self, state, policy): ...
    def compose_condition(self, state, delta): ...
    def solve_ode(self, state, seed, *, steps=1): ...
    def observe_endpoint(self, state): ...
```

### 5.4 Step 3 — register the adapter in `adaptive_reflow.adapters`

```python
# adaptive_reflow/adapters/my_model.py
from .reference_flowa import ReferenceFlowAAdapter  # copy this skeleton

class MyModelAdapter(ReferenceFlowAAdapter):
    """Override the methods that differ from the reference."""
    ...
```

```python
# adaptive_reflow/adapters/__init__.py — add:
from .my_model import MyModelAdapter, default_my_model_adapter
```

### 5.5 Step 4 — register the candidate in `adaptive_reflow.writer.registry`

See `adaptive_reflow/writer/registry.py::CandidateRegistry` and the
DTB-G2 spec. The candidate entry carries:

- `repo_url`, `commit`, `license`, `paper_id`, `paper_date`
- `task_conditions` — task domain (e.g. `("pocket_conditioned",)`)
- `compatible_channels` — must match the adapter's `SUPPORTED_CHANNELS`
- `adapter_status` — `unsupported` / `blocked` / `admitted` /
  `admitted_unconditional_only`
- `audit_notes` — required non-empty entry describing what was audited

### 5.6 Step 5 — write tests under `tests/test_adapters/`

The pattern (see `tests/test_adapters/test_toy_linear.py`):

1. Construct a synthetic test harness with a known adapter instance.
2. Walk one round end-to-end and assert the per-round contract:
   `validate_state_bundle` holds after every method, the
   `native_state_digest` is deterministic for `(state, seed, steps)`,
   and `policy_hash` is reproducible.
3. Add a hostile-case test for each capability the adapter *does not*
   advertise (e.g. missing `has_discrete_channels` should fail closed
   on a `raw_pair`-channel request with a `CapabilityMissingError`).

The Protocol itself is `@runtime_checkable` so a duck-type assertion
is also possible (`isinstance(adapter, FlowMatchingODEAdapter)`).
   `EngineRoundResult.round_trace_v3` is frozen, the `final_policy_writer`
   matches the adapter's `mechanism_id`, and `policy_hash` is deterministic.
3. Add a hostile-case test for each capability the adapter *does not*
   advertise (e.g. missing `has_discrete_channels` should fail closed on a
   `pair`-channel request with a `CapabilityMissingError`).

The Protocol itself is `@runtime_checkable` so a duck-type assertion is also
possible (`isinstance(adapter, FlowMatchingODEAdapter)`).

### 5.5 Hard rules for new adapters

* **No `import torch`** in `adaptive_reflow/adapters/*`. Adapters that need a
  tensor library wrap it behind an opaque `TensorRef` boundary so the engine
  never sees a native tensor.
* **Capability handshake is mandatory.** The engine calls
  `validate_capabilities` against the adapter's `AdapterCapabilities` before
  any native call. Returning the wrong capabilities is a fail-closed error.
* **`source_round` is non-negative int.** A negative source round fails
  closed (`validate_state_bundle` raises `ValueError`).
* **Deterministic seed.** The adapter must accept a `seed: int` and use it for
  any randomness it introduces. The engine will re-run the same round with
  the same seed and expect byte-equal `trace_digest`.

---

## 6. Governance reference — patterns we adopted

| Pattern                         | From                                      | Why we adopted it                                                                 |
| ------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------- |
| Role-based subpackages          | vLLM (`engine/`, `executor/`, `model_executor/`, `entrypoints/`) | One subpackage, one concern. Forces each module to declare its role.              |
| Typed request / response shapes | vLLM (`protocol.py`, `arg_utils.py`)      | `adaptive_reflow/contracts/` is the same idea but for a runtime ledger instead of a HTTP API. |
| Per-architecture forward passes | vLLM (`model_executor/models/`)           | `adaptive_reflow/adapters/` is per-architecture: one file per model family.        |
| Adapter Protocol + opaque tokens | vLLM + HuggingFace `transformers`          | `TensorRef` (opaque string) means the engine is library-agnostic.                 |
| Pipeline-as-package             | Diffusers (`pipelines/`)                  | Each adapter is a small, swappable unit; the orchestrator composes them.          |
| Frozen dataclass schemas        | PyTorch (e.g. `torch.dtype`) + ONNX Runtime (`op_type_proto`) | Every contract is `frozen=True` so hashes are stable.                              |
| Deterministic JSON serialisation| ONNX Runtime (`helper.py` `make_model_info`) | `_canonical_json` / `_json_default` give a stable byte representation for hashing. |
| Strict DAG of subpackages       | PyTorch (`torch/`, `torch.nn/`, `torch.optim/`) | Lower layers do not import from higher layers; `contracts/` is the leaf.            |
| Runtime-checkable Protocols     | PEP 544 + `typing.Protocol`               | `FlowMatchingODEAdapter` is `@runtime_checkable` so external adapters can be duck-typed. |
| Curated `__init__.py`           | PyTorch (`torch.nn.__init__`)             | Each subpackage exposes only the documented public surface; internal helpers stay module-internal. |
| Quarantine subpackage           | PyTorch (`torch.legacy`) + NumPy (`numpy.core._internal`) | `adaptive_reflow.legacy/` is the same pattern: kept around, warned at import, never imported by new code. |
| Marker for quarantined tests    | pytest (`@pytest.mark.legacy`)            | Legacy tests are gated on a successful `pocket_modules` ancestor walk.             |
| Capability handshake            | ONNX Runtime (`IExecutionProvider`)        | Adapter capabilities are advertised up-front; the engine fails closed on mismatch. |
| Schema name + version constants | JSON Schema (`$id`, `$schema`)             | `MERGE_AUTHORITY_SCHEMA_NAME`, `ROUND_TRACE_V3_SCHEMA_NAME`, `CORE_RUNTIME_HANDBOFF_SCHEMA_NAME` give a stable identity. |
| Single-writer authority         | SQLite WAL + vLLM `StatLoggerFactory`     | `WriterArbitrator` ensures exactly one writer (`inference.adaptive_reflow`) is allowed to write the executable policy per run. |
| Handoff doc + handoff schema    | Apache Beam (`PTransform` + runner protocol) | `CoreRuntimeHandoff` is the contract between this repo and the downstream owner. |

### What we did NOT adopt (and why)

* **Pydantic.** We use stdlib `dataclasses(frozen=True)` so the package is
  `pip install`-free for the contracts layer. Adding Pydantic would force
  every contract consumer to take on the dependency.
* **`__init__.py` lazy imports.** Every `__init__.py` imports its public
  surface eagerly so a typo in a subpackage import fails at import time, not
  at first call.
* **Generic-typed Protocol surface.** `FlowMatchingODEAdapter` is a concrete
  Protocol with named carriers (`StateBundle`, `ODEConditionDelta`,
  `ODEIntegratorTrace`) rather than a generic `Protocol[T]` so that the
  carrier types can carry contract-level invariants (e.g.
  `validate_state_bundle`).

---

## 7. File inventory

### 7.1 Source files

| File                                                          | One-line description                                                                                |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `adaptive_reflow/__init__.py`                                 | (does not exist — package has no top-level `__init__.py`; imports go straight to a subpackage)      |
| `adaptive_reflow/adapters/__init__.py`                        | Re-export all concrete adapters + channel-name constants.                                          |
| `adaptive_reflow/adapters/flowmol3.py`                        | `FlowMol3Adapter` + capabilities + default factory + registry entry.                               |
| `adaptive_reflow/adapters/reference_flowa.py`                 | `ReferenceFlowAAdapter` placeholder + channel-name constant.                                       |
| `adaptive_reflow/adapters/synthetic.py`                       | Four synthetic fixtures (continuous / discrete / mixed / unsupported) + channel-name constants.   |
| `adaptive_reflow/contracts/__init__.py`                       | Curated public surface of all §1–§8 contracts.                                                      |
| `adaptive_reflow/contracts/archive.py`                        | DTB-R4: `ArchiveQuota`, `ArchiveAuditTrail`, `validate_archive_quota`.                              |
| `adaptive_reflow/contracts/authority.py`                      | DTB-S1: `RestartPolicyAuthorityContract`, `LegacyCompatibilityWindow`, `FinalRestartPolicy`, validator. |
| `adaptive_reflow/contracts/bundle.py`                         | DTB-R1: `RoundResultBundle`, `ChannelTransferEvidence`, `ChannelTransferDecision`, `DynamicRestartTransferLedger`, validators. |
| `adaptive_reflow/contracts/decision.py`                       | Reserved for future DTB-R2/R8 decision-shape additions.                                            |
| `adaptive_reflow/contracts/envelope.py`                       | DTB-NC1/NC2: `EnvelopeLayer`, `FrozenEnvelopeManifest`, `EnvelopeClassification`, `TailBudgetRow`, validators. |
| `adaptive_reflow/contracts/hashes.py`                         | Deterministic sha256 helpers (`hash_artifact`, `hash_bundle_id`, etc.) + canonical-JSON helpers.    |
| `adaptive_reflow/contracts/operations.py`                     | DTB-L2: `OperationCompositionContract`, `CommutatorResidualDiagnostic`.                            |
| `adaptive_reflow/contracts/phase.py`                          | DTB-L1: `PhaseState` + factory + digest round-trip + validator.                                     |
| `adaptive_reflow/contracts/schedule.py`                       | DTB-NA1: `CosineScheduleConfig`, `CosineScheduleSample`, `FreshNoiseFloor`, `RestartTriggerEvent`.  |
| `adaptive_reflow/contracts/types.py`                          | NewType aliases + literal-set constants (CHANNEL_NAMES, SCHEDULE_FAMILIES, etc.).                   |
| `adaptive_reflow/contracts/validators.py`                     | `ValidationResult`, `validate_unit_float`, `validate_positive_int`, etc.                            |
| `adaptive_reflow/diagnostics/__init__.py`                     | Re-export observation-only ledger types + validators + `empty_diagnostics`.                        |
| `adaptive_reflow/diagnostics/ledger.py`                       | `FreshNoiseCumulativeMassRecord`, `SpectralResidualBandProxy`, `TailDiagnosticStatus` + validators. |
| `adaptive_reflow/envelope/__init__.py`                        | Re-export `FrozenEnvelopeManifestBuilder`, `TailBudgetAccumulator`, `classify_endpoint`.            |
| `adaptive_reflow/envelope/classifier.py`                      | Observable extraction + per-layer threshold check + `OBS_*` key constants.                         |
| `adaptive_reflow/envelope/manifest.py`                        | `FrozenEnvelopeManifestBuilder`, `classify_endpoint`, `TailBudgetAccumulator`, `StratifiedTailBudgetRow`. |
| `adaptive_reflow/envelope/tail_budget.py`                     | Tail-budget-only code (`EvidenceRowHash`).                                                          |
| `adaptive_reflow/eval/__init__.py`                            | Re-export all DTB-R7/R8 types + functions.                                                         |
| `adaptive_reflow/eval/calibration.py`                         | DTB-R7 CPU: `wilson_lower_bound`, `beta_lower_bound`, `CalibrationBucket`, `CalibrationManifest`, `StabilityPerturbationProtocol`. |
| `adaptive_reflow/eval/claim_gate.py`                          | DTB-R8: `ClaimGateConfig`, `ClaimGateDecision`, `evaluate_claim_gate`, `build_default_claim_gate_config`. |
| `adaptive_reflow/eval/manifests.py`                           | DTB-R7: `write_calibration_manifest`, `read_calibration_manifest`, `validate_manifest_frozen`, `frozen_manifest_hash`. |
| `adaptive_reflow/eval/metric_panel.py`                        | DTB-R8: `LayeredMetricPanel`, `enforce_separation`, `build_default_layered_metric_panel`.           |
| `adaptive_reflow/eval/promotion.py`                           | DTB-R8: `PromotionReport`, `PolicyVersionHashRecorder`, `build_deferred_promotion_report`.          |
| `adaptive_reflow/eval/protocol.py`                            | DTB-R7: `PairedComparisonArm`, `PairedComparisonRegistry`, `EvaluatorProvenanceGuard`, `RoundToRoundOscillationDetector`. |
| `adaptive_reflow/eval/rollback.py`                            | DTB-R8: `RollbackFlag`, `RollbackAudit`, `apply_rollback`, `build_disabled_rollback_flag`.          |
| `adaptive_reflow/frame/__init__.py`                           | Re-export all frame-level types + functions.                                                       |
| `adaptive_reflow/frame/adapter.py`                            | DTB-G1: `FlowMatchingODEAdapter` Protocol + `StateBundle` + `ODEConditionDelta` + `ODEIntegratorTrace` + `AdapterCapabilities` + `TensorRef`. |
| `adaptive_reflow/frame/channel_rule.py`                       | DTB-R2: `compute_channel_decision`, `check_monotonicity_property`, blocker codes.                  |
| `adaptive_reflow/frame/engine.py`                             | DTB-G1: `Engine`, `EngineRoundResult`, engine-level `RoundTrace` + `LedgerRow` + `PhaseState`, `FEATURE_FLAG_KEY`, `ERR_*`. |
| `adaptive_reflow/frame/merge.py`                              | DTB-R3: `bounded_merge`, `bounded_merge_with_schedule`, `MergeAuthorityError`, schema constants.    |
| `adaptive_reflow/frame/operation.py`                          | DTB-L2 runtime: `build_default_composition_contract`, `validate_operation_order`, `record_commutator_residual`, `replay_default_order`. |
| `adaptive_reflow/frame/orchestrator.py`                       | DTB-S1: `AdaptiveReflowPolicyOrchestrator` + error classes + `WRITER_ID`.                           |
| `adaptive_reflow/frame/phase.py`                              | DTB-L1 runtime: `build_phase_state`, `advance_phase`, `make_default_phase_state` (run_id_seed), `validate_phase_state_transition`. |
| `adaptive_reflow/frame/trace.py`                              | DTB-R5: `RoundTraceV3` + v2 reader + content hash + freeze + round-trip + final-policy-writer constants. |
| `adaptive_reflow/legacy/__init__.py`                          | Empty `__all__`; emits `DeprecationWarning` on import.                                             |
| `adaptive_reflow/legacy/control_policy.py`                    | Pre-refactor torch-bound control policy (quarantined).                                             |
| `adaptive_reflow/legacy/loop.py`                              | Pre-refactor loop (quarantined).                                                                    |
| `adaptive_reflow/legacy/loop_contract.py`                     | Pre-refactor loop contract (quarantined).                                                           |
| `adaptive_reflow/legacy/mechanism_adapter.py`                 | Pre-refactor `AdaptiveReflowMechanism` (quarantined).                                              |
| `adaptive_reflow/legacy/metric_feedback.py`                   | `external_metric_feedback.py` renamed (quarantined).                                               |
| `adaptive_reflow/legacy/orchestration.py`                     | Pre-refactor orchestration (quarantined).                                                          |
| `adaptive_reflow/legacy/plan.py`                              | `reinference_plan.py` renamed (quarantined).                                                       |
| `adaptive_reflow/legacy/restart_mixer.py`                     | `restart_memory.py` renamed (torch-bound; quarantined).                                            |
| `adaptive_reflow/legacy/services.py`                          | Pre-refactor services (quarantined).                                                               |
| `adaptive_reflow/universal/__init__.py`                       | Re-export universal kernel Protocols + carriers + validators. Stdlib-only, zero molecule imports. |
| `adaptive_reflow/universal/state.py`                          | `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace`, `NORMALIZATION_KINDS`, `REFERENCE_FRAMES`. |
| `adaptive_reflow/universal/adapter.py`                        | `FlowMatchingODEAdapter` Protocol + `AdapterCapabilities` + `RestartPolicy` + validators.            |
| `adaptive_reflow/universal/envelope.py`                       | `EnvelopeCriterion` Protocol + `EnvelopeClassification` + validators.                               |
| `adaptive_reflow/universal/evaluator.py`                      | `Evaluator` Protocol + `validate_evaluator_artifact_hash`.                                         |
| `adaptive_reflow/universal/mixer.py`                          | `RestartMixer` Protocol + `validate_blend_inputs`.                                                  |
| `adaptive_reflow/universal/validators.py`                     | Single entry point for universal numeric validators.                                                |
| `adaptive_reflow/molecular/__init__.py`                       | Re-export molecule channel vocabulary + concrete universal-Protocol impls.                        |
| `adaptive_reflow/molecular/bundle.py`                         | `MoleculeRoundResultBundle` + `validate_molecule_round_result_bundle`.                             |
| `adaptive_reflow/molecular/envelope.py`                       | `MoleculeEnvelopeLayer` / `MoleculeEnvelopeManifest` / `MoleculeEnvelopeClassification` / `MoleculeTailBudgetRow` (implements the universal `EnvelopeCriterion` Protocol). |
| `adaptive_reflow/molecular/channels.py`                       | `MOLECULE_CHANNELS`, `MoleculeChannel` enum, four `*ChannelRef` NewType aliases.                    |
| `adaptive_reflow/molecular/domain.py`                         | `MOLECULE_DOMAIN_BY_CHANNEL` fallback domain table.                                                 |
| `adaptive_reflow/molecular/stratification.py`                  | `MoleculeStratum` / `MoleculeStratumAssignment` / `dominance_ratio` / `cross_stratum_mix_rejected`. |
| `adaptive_reflow/molecular/mixer.py`                          | `RMSPreservingCoordinateMixer` (concrete universal `RestartMixer` Protocol impl) + back-compat free function. |
| `adaptive_reflow/molecular/calibration_protocols.py`          | `GNINAEvaluator` / `PoseBustersEvaluator` / `QEDEvaluator` / `ADMETEvaluator` (concrete universal `Evaluator` Protocol impls). |
| `adaptive_reflow/policy/__init__.py`                          | Re-export all pure decision-logic types + functions.                                               |
| `adaptive_reflow/policy/archive.py`                           | DTB-R4: `SameSampleArchive`, `ArchiveEntry`, `CandidateArchiveError` family.                        |
| `adaptive_reflow/policy/noise_mass.py`                        | DTB-L4 calc: `physical_noise_proxy`, `RMS_preserving_mixing_coefficient`, `exact_spectral_variance`, `adversarial_stagnation_test`. |
| `adaptive_reflow/policy/pruning.py`                           | DTB-L3: `PruneGate`, `UnorderedAuditResult`, `PruneDecision`.                                       |
| `adaptive_reflow/policy/stratification.py`                    | DTB-L3: `Stratum`, `StratumAssignment`, `dominance_ratio`, `cross_stratum_mix_rejected`.            |
| `adaptive_reflow/schedule/__init__.py`                        | Re-export `CosineScheduleSampler`, `n_cap_for_round`, validators, ERR_*.                            |
| `adaptive_reflow/schedule/cosine.py`                          | DTB-NA1: `CosineScheduleSampler` + `n_cap_for_round` + `validate_cosine_schedule_config` + `default_floor_by_channel` + `build_fresh_noise_diagnostics`. |
| `adaptive_reflow/writer/__init__.py`                          | Re-export authority + handoff + registry + audit types + functions.                                |
| `adaptive_reflow/writer/audit.py`                             | DTB-G2: `AuditTemplate`, `DEFAULT_AUDIT_TEMPLATE`, `validate_audit_completeness`, `render_audit_checklist`, `registry_summary`. |
| `adaptive_reflow/writer/authority.py`                         | DTB-S1 runtime: `WriterArbitrator`, `build_default_authority_contract`, `build_final_restart_policy`, `verify_policy_against_ledger`. |
| `adaptive_reflow/writer/handoff.py`                           | DTB-R3: `CoreRuntimeHandoff`, `build_core_runtime_handoff`, `write_handoff_spec`.                   |
| `adaptive_reflow/writer/registry.py`                          | DTB-G2: `CandidateEntry`, `CandidateRegistry`, `make_initial_registry`, `admit_entry`, `default_registry`, `FLOWMOL3_PINNED_COMMIT`. |

### 7.2 Test files

| File                                                       | One-line description                                                                                |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `tests/conftest.py`                                        | Package-context bootstrap; legacy-only `pocket_modules` ancestor walk.                              |
| `tests/test_diagnostics/test_ledger.py`                    | `FreshNoiseCumulativeMassRecord` + validator + `empty_diagnostics`.                                 |
| `tests/test_eval/test_calibration.py`                      | `wilson_lower_bound`, `beta_lower_bound`, `CalibrationBucket`, `classify_bucket`, `manifest_digest`. |
| `tests/test_eval/test_claim_gate.py`                       | `ClaimGateDecision`, `evaluate_claim_gate`, `DEFERRED_R8_REASON`.                                   |
| `tests/test_eval/test_protocol.py`                         | `PairedComparisonArm`, `EvaluatorProvenanceGuard`, `evaluator_guard_digest`, `RoundToRoundOscillationDetector`. |
| `tests/test_frame/test_engine.py`                          | `Engine` round-walk + capability handshake + **no-torch assertion** on engine / adapter modules.   |
| `tests/test_frame/test_merge.py`                           | `bounded_merge`, `bounded_merge_with_schedule`, `MergeAuthorityError`.                              |
| `tests/test_frame/test_trace.py`                           | `RoundTraceV3` + content hash + freeze + round-trip + legacy compat.                                |
| `tests/test_policy/test_archive.py`                        | `SameSampleArchive`, `ArchiveQuota`, archive-lineage hostile cases.                                 |
| `tests/test_policy/test_stratification_and_pruning.py`     | `Stratum`, `StratumAssignment`, `PruneGate`, `physical_noise_proxy`, **no-torch assertion** on policy modules. |
| `tests/test_universal/test_no_molecular_import.py`         | AST-level guard: no file in `adaptive_reflow/universal/` imports from `adaptive_reflow.molecular`.  |
| `tests/test_universal/test_adapter_universality.py`        | Synthetic non-molecular adapter satisfies the universal `FlowMatchingODEAdapter` Protocol.         |
| `tests/test_universal/test_envelope_criterion.py`          | `EnvelopeCriterion` Protocol is satisfiable by non-molecular criteria.                              |
| `tests/test_universal/test_mixer_protocol.py`              | `RestartMixer` Protocol is satisfiable by non-molecular mixers.                                     |
| `tests/test_writer/test_registry.py`                       | `CandidateRegistry`, `FLOWMOL3_PINNED_COMMIT`, `admit_entry`, `default_registry`.                   |

### 7.3 Documentation files

| File                            | One-line description                                                              |
| ------------------------------- | --------------------------------------------------------------------------------- |
| `README.md`                     | Entry point — repo purpose, mounting path, promotion requirements, component boundary. |
| `STATUS.md`                     | Component boundary snapshot (sole executable writer; companion repo link).        |
| `DESIGN_BOUNDARY.md`            | DTB-R0 design boundary + non-claim boundary + hostile-case catalogue.            |
| `CONTRACTS.md`                  | §1–§8 typed-contract skeletons referenced by `contracts/`.                        |
| `ARCHITECTURE.md`               | This file — current governance doc.                                               |
| `ARCHITECTURE_PLAN.md`          | Historical — the planned target layout (now superseded by this file).             |
| `FILE_MAPPING.md`               | Historical — old → new file moves (now superseded by §7 above).                   |
| `SPLIT_NOTES.md`                | Historical — per-symbol placement for the `restart_memory_types.py` and `envelope_manifest.py` splits. |
| `todo.json`                     | Canonical task list (DTB-R0/R1/.../DTB-RFG).                                      |
| `docs/`                         | Project-internal research notes (candidate-registry init + Lean provenance).      |
| `docs/api/*.md` | Auto-generated, **griffe-driven** API reference. Each page drills into per-internal-module directives (`::: adaptive_reflow.frame.merge`, `::: adaptive_reflow.contracts.bundle`, `::: adaptive_reflow.universal.adapter`, ...) rather than stopping at the subpackage `__init__.py` re-exports, so symbols that live only in the split files (error sentinels, validator helpers, audit-code constants, per-adapter `*_CHANNELS` tables) appear in the rendered reference. mkdocstrings' Python handler uses [griffe](https://mkdocstrings.github.io/griffe/) as its signature-extraction back-end (declared as an explicit `griffe>=1.0` pin in `[project.optional-dependencies].dev`); `mkdocs.yml` sets `inherited_members: true` so inherited dataclass fields and Protocol methods show up under each class heading. Build via `python -m mkdocs build --strict` (use the `.venv` interpreter the project pins); `--strict` fails the build on missing nav entries, broken cross-references, and unresolved mkdocstrings directives so doc drift is caught at PR time. |

---

## 8. Governance invariants (enforced by the test suite)

These are the rules that the tests enforce; if you break one, the suite fails.

1. **`tests/test_frame/test_engine.py::test_no_torch_in_any_new_file`** —
   no engine / adapter module imports `torch`.
2. **`tests/test_policy/test_stratification_and_pruning.py::TestNoTorchDependency::test_no_torch_in_new_modules`** —
   no new policy module pulls `torch` transitively.
3. **`tests/test_frame/test_trace.py`** (deprecation warning) — `adaptive_reflow.legacy`
   emits a `DeprecationWarning` on import.
4. **`tests/test_universal/test_no_molecular_import.py`** — no file in
   `adaptive_reflow/universal/` may import from `adaptive_reflow.molecular`.
   Enforced by AST walking every `.py` file under `adaptive_reflow/universal/`
   and asserting no `ast.Import` / `ast.ImportFrom` node targets the
   `adaptive_reflow.molecular` namespace.
5. **`tests/test_universal/test_adapter_universality.py`** and
   **`tests/test_universal/test_toy_gaussian.py`** — a synthetic
   non-molecular adapter (the 1-D Gaussian `ToyGaussianAdapter`) drives
   the universal `FlowMatchingODEAdapter` Protocol end-to-end without
   importing `adaptive_reflow.molecular`. This is the *positive*
   satisfiability proof for the universal surface; the AST guard
   above is the *negative* prevention.
6. **`tests/test_universal/test_envelope_criterion.py`** —
   `EnvelopeCriterion` Protocol is satisfiable by a non-molecular criterion.
7. **`tests/test_universal/test_mixer_protocol.py`** — `RestartMixer`
   Protocol is satisfiable by a non-molecular mixer.
8. **Hard gates for DTB-R0 §3 case 2 / case 5**
   (`tests/test_adversarial/test_hostile_cases.py`) — the audit codes
   [`AUDIT_STABILITY_COLLAPSE`](adaptive_reflow/frame/channel_rule.py)
   (= `perturbation_stability_below_threshold`) and
   [`AUDIT_SOURCE_REVOKED`](adaptive_reflow/contracts/validators.py)
   (= `source_revoked`) are now **hard gates**, not xfail markers. The
   adversarial layer asserts they appear in `audit_reason` and
   `blocker_codes` on the failing path; both constants are re-exported
   from `adaptive_reflow.contracts`, `adaptive_reflow.frame`, and
   `adaptive_reflow.policy` so the doc scanner indexes them.
9. **Full test suite (475+ tests)** — round-trip + capability handshake +
   bounded-merge + channel-rule + phase-transition + registry-admit + claim-gate
   + rollback + promotion + calibration + trace-v3 round-trip + diagnostic
   ledger + universal-Protocol universality + property-based invariants
   (Hypothesis) + adversarial hostile-case fixtures (DTB-R0 §3 case 1–6,
   now with audit-code-indexed closures for case 2 and case 5) + end-to-end
   round walks + doc-drift scanner self-test + golden replay + kernel
   benchmarks + memory-footprint probes + 1000-round stress run.

---

## 8.5 Testing infrastructure

The contract layer *is* the product, so the test suite is built around
the contracts themselves rather than around empirical model behaviour.
The full single-source-of-truth for *what* we test, *how* the layers
fit together, and *what bars* (mutation score, benchmark budgets, doc
verification) a change has to clear before it merges is
**[docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)**. The kernel
performance budgets are documented separately in
**[docs/PERFORMANCE_BUDGETS.md](docs/PERFORMANCE_BUDGETS.md)**. This
sub-section is the index that points to them from the governance doc.

The test surface is organised in **six cooperating layers**, each of
which catches a different class of defect:

| Layer | Purpose | Files |
|-------|---------|-------|
| Unit | Per-module black-box tests over the public surface | `tests/test_frame/`, `tests/test_eval/`, `tests/test_policy/`, `tests/test_diagnostics/`, `tests/test_writer/`, `tests/test_universal/`, `tests/test_adapters/` |
| Property | `hypothesis`-driven exploration of bounded `[0, 1]` envelopes; stdlib-only | `tests/property/` |
| Adversarial | One test per hostile case in DESIGN_BOUNDARY.md §3 (now including the `AUDIT_STABILITY_COLLAPSE` and `AUDIT_SOURCE_REVOKED` hard gates for case 2 and case 5); fail-closed | `tests/test_adversarial/` |
| Golden | Recorded input / output JSON under `tests/golden/<kernel>/`; replayed via `tests/property/test_golden_replay.py`; generated by `tools/generate_golden.py` | `tests/golden/` |
| Benchmark | `pytest-benchmark` decorated kernel benchmarks; p95 budgets in `tools/bench/budgets.json`; JSON dump in `docs/benchmarks.json` | `tests/perf/` |
| Doc-drift scanner | AST-walk of governance docs + `docs/*.md` to verify every CamelCase / SCREAMING_SNAKE_CASE / `adaptive_reflow/...` claim resolves to a real symbol; fails CI on drift | `tools/check_docs_against_code.py` + `tests/test_tools/test_check_docs_against_code.py` |

### Synthetic evaluator oracle (DTB-R7 / DTB-R8)

The DTB-R7 / DTB-R8 evaluation leg is exercised on CPU through
[`SyntheticEvaluator`](adaptive_reflow/eval/synthetic_oracle.py) — a
deterministic closed-form evaluator whose four primary diagnostics
(`raw_score`, `bounded_score`, `calibration_lower_bound`,
`perturbation_stability_lower_bound`) are pure closed-form functions of
`(native_state_digest, channel, seed)`. The companion `oracle` method
re-derives the same four values via the *same* private helpers, so any
test can assert `evaluate(b, c, s) == oracle(b, c, s)` byte-for-byte
without depending on GNINA / QED / ADMET / PoseBusters. This is what
makes the universal layer exercisable end-to-end without a model in
the loop. The corresponding golden set lives at
`tests/golden/synthetic_evaluator/`.

### Audit-code catalogue (ADR-0005)

The audit-code catalogue is the index of every `AUDIT_*`, `ERR_*`,
`BLOCKER_*`, and `OBS_*` constant the engine can emit. Every
catalogue entry must be re-exported from the relevant public
`__init__.py` so the doc scanner can verify it. The constants
indexed today include:

* `AUDIT_STABILITY_COLLAPSE` (`adaptive_reflow.frame.channel_rule`) =
  `perturbation_stability_below_threshold` — DTB-R0 §3 case 2.
* `AUDIT_SOURCE_REVOKED` (`adaptive_reflow.contracts.validators`) =
  `source_revoked` — DTB-R0 §3 case 5.
* `BLOCKER_PROXY_ONLY` = `proxy_only_cannot_satisfy_calibration` —
  DTB-R0 §3 case 6.
* `COMPLEMENT_BLOCKER_CODES`, `RESTART_TRIGGER_CODES`, `FEEDBACK_MODES`
  — literal-set tuples in `adaptive_reflow.contracts.types`.

Adding a new audit code without re-exporting it surfaces as a
doc-scanner drift failure; ADR-0005 is the policy that pins the
re-export step.

### Tooling (CPU-only, no model in the loop)

* **`hypothesis`** — property-based test generation. Pinned profile in
  `pyproject.toml [tool.hypothesis]` (`max_examples=200`,
  `deadline=5000 ms`, `too_slow` suppressed for Windows file-IO
  variance).
* **`pytest-benchmark`** — microsecond kernel benchmarking. Pinned
  profile in `pyproject.toml [tool.pytest-benchmark]` (`min_rounds=5`,
  `warmup_iterations=10`, `sort=mean`).
* **`mutmut`** — mutation testing, nightly only. Scoped to
  `contracts / universal / molecular / frame` in
  `tools/mutate/mutmut.toml`; runner in
  `tools/mutate/run_mutmut.sh`. Native Windows run is deferred to
  upstream mutmut issue 397; the Linux nightly job captures the
  canonical score and uploads the report as the `mutmut-report`
  artifact. The mutation score is itself a release gate (see
  "Mutation score targets" below).
* **`tools/bench/check_budgets.py`** vs `tools/bench/budgets.json` —
  the 20% regression threshold gate.
* **`tests/perf/test_stress_1000_rounds.py`** — 1,000-round stress
  run driven by the `AdaptiveReflowPolicyOrchestrator` against the
  `SyntheticEvaluator` oracle. Catches leaks and unbounded growth
  that the microsecond kernel benchmarks miss.

### CI workflows (under `.github/workflows/`)

| Workflow | Trigger | What it gates |
|----------|---------|----------------|
| `cpu-tests.yml` | push to main + every PR | ruff + pytest (non-slow, non-benchmark) + doc scanner |
| `docs-validate.yml` | push to main + every PR | ruff + doc scanner + full pytest |
| `bench-regression.yml` | weekly Mon 04:00 UTC + manual | `pytest --benchmark-only` + `tools/bench/check_budgets.py` |
| `mutation-nightly.yml` | nightly 03:00 UTC + manual | `bash tools/mutate/run_mutmut.sh`; mutation-score release gate enforced; `mutmut-report` artifact uploaded |
| `stress-nightly.yml` | nightly 03:30 UTC + manual | `pytest tests/perf/test_stress_1000_rounds.py` against the `SyntheticEvaluator` oracle; rejects leaks > 5 MB / 1000 rounds |

### Mutation score targets (release gate)

| Scope | Target |
|-------|-------:|
| `adaptive_reflow.contracts` | `>= 90%` killed |
| `adaptive_reflow.universal` | `>= 85%` killed |
| `adaptive_reflow.frame`     | `>= 75%` killed |
| `adaptive_reflow.molecular` | `>= 70%` killed (best-effort) |

The nightly `mutation-nightly.yml` job **fails the gate** when any
scope drops below its target. A surviving mutant in `contracts` or
`universal` is, by definition, either (a) an equivalent mutant or
(b) a missing test; the latter is filed as a follow-up and blocks the
PR that introduced it (ADR-0005). The stress-nightly job gates leaks
and unbounded growth that the microsecond kernel benchmarks cannot
see — together they form the "doesn't run fast *and* doesn't grow"
pair the merge bar requires.

### Conventions for adding a new test

See [docs/TESTING_STRATEGY.md §6](docs/TESTING_STRATEGY.md) for the
full convention. The short form:

1. Pick the layer that matches the defect class.
2. Place the file under the right `tests/` subdirectory.
3. Use `tests/_utils/asserters.py` helpers for envelope / hash / gate
   equality rather than re-implementing the predicate.
4. Mark slow tests with `@pytest.mark.slow`; mark kernel tests with
   `@pytest.mark.benchmark`.
5. Update **this file** if the change introduces a new public symbol;
   the doc scanner refuses to merge otherwise.
6. Run the full gate locally before pushing: `pytest tests/ &&
   python tools/check_docs_against_code.py && ruff check adaptive_reflow/ tests/`.

If you add a new module:

* If it lives under `adaptive_reflow.contracts`, it must be stdlib-only.
* If it lives under any other subpackage, it must not import from
  `adaptive_reflow.legacy`.
* If it implements a new adapter, follow §5.
* If it adds a new contract, add a test in `tests/test_contracts/` and an entry
  to `CONTRACTS.md` §1–§8.
* If it adds a new public symbol, update §7 and the doc scanner will
  verify the claim before CI goes green.

---

## 9. Companion repos and cross-references

`flowa-multistep-reinference` is one component of a larger flow-A
ecosystem. The companion repos that consume or extend this package
are documented in `STATUS.md`; the load-bearing boundary between this
component and its neighbours is the **single executable writer**
(`inference.adaptive_reflow`) named in `CODEOWNERS` and `CONTRACTS.md`.
Cross-repo changes must clear both this repo's CI and the companion's
CI before the shared artefact (typically a `FinalRestartPolicy.policy_hash`
recorded against a `RoundResultBundle`) is admitted downstream.

---

## 10. Governance

This section is the index from the architecture doc to every
governance artefact that is *not* a code-level invariant. The code-level
invariants live in §8; the bench / mutation / stress gates live in §8.5;
the patterns we adopted and rejected live in §6. Everything else —
roadmap, contribution workflow, security posture, code ownership,
deprecation policy, architectural decisions — is documented in the
files below. If a load-bearing boundary changes, the change is
recorded here first.

| Governance artefact | Path | Purpose |
|---|---|---|
| Roadmap | [`ROADMAP.md`](ROADMAP.md) | Now / Next / Later buckets; entry for every DTB-R0/R1/.../DTB-RFG task in `todo.json`; target dates; ADR cross-references. |
| Contributing | [`CONTRIBUTING.md`](CONTRIBUTING.md) | Four workflows the maintainer runs on every change (hostile-case test, adapter, mutation test, docs scanner); local pre-push gate. |
| Security | [`SECURITY.md`](SECURITY.md) | Single-maintainer scope; explicit "no security-sensitive surface" claim; reporting channel for build / supply-chain defects. |
| Code ownership | [`CODEOWNERS`](CODEOWNERS) | GitHub code-owner routing. Load-bearing boundaries (`contracts/`, `universal/`, `frame/engine.py`, public `__init__.py` files, the doc scanner, the docs governance tree) are pinned explicitly. |
| Deprecation policy | [`docs/DEPRECATION.md`](docs/DEPRECATION.md) | Versioned deprecation table for every `adaptive_reflow.legacy/*` module; quarantine mechanics; sunset / removal convention. |
| ADRs | [`docs/adr/`](docs/adr/) | Architectural decisions (MADR 4.0). The five shipped today cover (1) the meta-format, (2) the typed-contracts core boundary, (3) the universal / molecular split, (4) the seven-step engine order, and (5) the fail-closed audit-code policy. New load-bearing decisions follow the same template. |
| Hands-on walk-through | [`TUTORIAL.md`](TUTORIAL.md) | Step-by-step tutorial: mental model, the seven-step engine round, writing an adapter, hostile-case tests, golden snapshots, property-based tests, mutation testing, performance budgets, contributing. |

### 10.1 Where to look first

| Question | Read |
|---|---|
| "What is this package?" | `README.md`, `STATUS.md` |
| "What does the engine do, end to end?" | §5 of this file, then `docs/ADAPTER_INTERFACE_SPEC.md` |
| "Why is the universal / molecular split the way it is?" | ADR-0003, then `tests/test_universal/test_no_molecular_import.py` |
| "How do I add a new adapter?" | `TUTORIAL.md` §3, then `docs/ADAPTER_INTERFACE_SPEC.md` §9 |
| "How do I add a hostile-case test?" | `TUTORIAL.md` §4, then `CONTRIBUTING.md` §1 |
| "Why did we choose seven steps, not six or eight?" | ADR-0004 |
| "Why is this `AUDIT_*` constant where it is?" | ADR-0005, then `tools/check_docs_against_code.py` |
| "When is the next feature landing?" | `ROADMAP.md` |
| "Is there a security boundary I need to respect?" | `SECURITY.md` |
| "Who reviews PRs against the contracts layer?" | `CODEOWNERS` |