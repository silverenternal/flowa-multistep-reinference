# ARCHITECTURE_PLAN — flowa-multistep-reinference (target)

**Repo (current):** 32 flat `.py` modules + 11 test files + `tests/conftest.py` at the
repo root; 362 tests pass.
**Target:** a single importable Python package, `adaptive_reflow/`, organised
*by concern*, not by feature.

The target layout is inspired by the lifecycle-stage separation used in
`vllm/{engine,executor,model_executor,entrypoints,...}` and Diffusers'
`pipelines/`, with three principles borrowed directly from those repos:

1. **Role-based packages.** Each subpackage owns *one* concern (contracts,
   frame, policy, schedule, envelope, writer, adapters, eval, diagnostics,
   legacy). No "kitchen sink" modules.
2. **Single-direction imports.** `contracts/` is a leaf (stdlib-only). Every
   other subpackage depends downward through `contracts/`. There are no
   upward edges and no peer-level cycles.
3. **Curated `__init__.py`.** Each subpackage exposes a narrow, documented
   public surface; everything else stays module-internal.

The split of `restart_memory_types.py` is described in detail in
`SPLIT_NOTES.md`. The exact file-by-file move is in `FILE_MAPPING.md`.
This document covers the *why*.

---

## 1. Top-level package layout

```
adaptive_reflow/                 <- the public Python package
├── __init__.py                  <- curated public surface (small)
├── contracts/                   <- frozen typed dataclasses + NewTypes (DTB-R0/R1/R2/R4/R5/NC1/NA1/L1/L2/S1)
│   ├── __init__.py
│   ├── types.py                 <- NewType aliases + literal-set constants
│   ├── hashes.py                <- deterministic sha256 helpers (hash_artifact, hash_*)
│   ├── validators.py            <- validate_unit_factor / _positive_int / _nonneg_int / ValidationResult
│   ├── bundle.py                <- DTB-R1: RoundResultBundle, ChannelTransferEvidence, ChannelTransferDecision,
│   │                             DynamicRestartTransferLedger, NoiseBiasInputRow, ChannelRuleInputs, ChannelRuleOutputs
│   ├── decision.py              <- DTB-R2: decision-related contract bits (none beyond §3, kept for symmetry)
│   ├── envelope.py              <- DTB-NC1/NC2: EnvelopeLayer, FrozenEnvelopeManifest, EnvelopeClassification, TailBudgetRow
│   ├── schedule.py              <- DTB-NA1: CosineScheduleConfig, CosineScheduleSample, FreshNoiseFloor, RestartTriggerEvent
│   ├── phase.py                 <- DTB-L1: PhaseState + make_default_phase_state factory
│   ├── operations.py            <- DTB-L2: OperationCompositionContract, CommutatorResidualDiagnostic + OPERATION_STEPS
│   ├── authority.py             <- DTB-S1: RestartPolicyAuthorityContract, LegacyCompatibilityWindow, FinalRestartPolicy
│   └── archive.py               <- DTB-R4: ArchiveQuota, ArchiveAuditTrail
├── envelope/                    <- runtime envelope + tail-budget machinery (DTB-NC1 + DTB-L3 partial)
│   ├── __init__.py
│   ├── manifest.py              <- FrozenEnvelopeManifestBuilder, classify_endpoint, TailBudgetAccumulator, StratifiedTailBudgetRow
│   ├── classifier.py            <- observable extraction + per-layer threshold check (split for testability)
│   └── tail_budget.py           <- accumulator only (StratifiedTailBudgetRow stays with manifest for now)
├── frame/                       <- the universal frame (engine + merge + operation + trace + channel rule)
│   ├── __init__.py
│   ├── adapter.py               <- DTB-G1: FlowMatchingODEAdapter Protocol, StateBundle, ODEConditionDelta,
│   │                             ODEIntegratorTrace, AdapterCapabilities, TensorRef, validators, DOMAIN_BY_CHANNEL
│   ├── engine.py                <- DTB-G1: Engine, EngineRoundResult, RoundTrace (engine-level), LedgerRow, PhaseState (engine-level)
│   ├── merge.py                 <- DTB-R3: bounded_merge, bounded_merge_with_schedule, MergeAuthorityError
│   ├── operation.py             <- DTB-L2 runtime: build_default_composition_contract, validate_operation_order,
│   │                             record_commutator_residual, replay_default_order
│   ├── channel_rule.py          <- DTB-R2: compute_channel_decision, check_monotonicity_property, blocker codes
│   ├── phase.py                 <- DTB-L1 runtime: build_phase_state, advance_phase, make_default_phase_state (run_id_seed),
│   │                             validate_phase_state_transition
│   ├── trace.py                 <- DTB-R5: RoundTraceV3 + v2 reader + content hash + freeze + round_trip
│   └── orchestrator.py          <- DTB-S1: AdaptiveReflowPolicyOrchestrator + PolicyOrchestratorError subclasses
├── policy/                      <- pure decision logic (candidates, stratification, pruning, noise accounting)
│   ├── __init__.py
│   ├── archive.py               <- DTB-R4: SameSampleArchive, ArchiveEntry, CandidateArchiveError family
│   ├── stratification.py        <- DTB-L3: Stratum enum, StratumAssignment, dominance_ratio, cross_stratum_mix_rejected
│   ├── pruning.py               <- DTB-L3: PruneGate, UnorderedAuditResult, PruneDecision
│   └── noise_mass.py            <- DTB-L4 calc leg: physical_noise_proxy, RMS_preserving_mixing_coefficient,
│                                  exact_spectral_variance, ThreeWayDistinction, adversarial_stagnation_test
├── schedule/                    <- restart-noise schedule (DTB-NA1)
│   ├── __init__.py
│   └── cosine.py                <- CosineScheduleSampler, n_cap_for_round, validate_cosine_schedule_config,
│                                  default_floor_by_channel, build_fresh_noise_diagnostics, ERR_*
├── diagnostics/                 <- observation-only ledgers (DTB-L4 observe leg)
│   ├── __init__.py
│   └── ledger.py                <- FreshNoiseCumulativeMassRecord, SpectralResidualBandProxy, TailDiagnosticStatus
│                                 + their validators + empty_diagnostics
├── writer/                      <- writer authority + arbitration + handoff + registry + audit
│   ├── __init__.py
│   ├── authority.py             <- DTB-S1 runtime: WriterArbitrator, build_default_authority_contract,
│   │                             build_final_restart_policy, verify_policy_against_ledger
│   ├── handoff.py               <- DTB-R3: CoreRuntimeHandoff, build_core_runtime_handoff, write_handoff_spec
│   ├── registry.py              <- DTB-G2: CandidateEntry, CandidateRegistry, make_initial_registry,
│   │                             admit_entry, default_registry, FLOWMOL3_PINNED_COMMIT, make_default_flowmol3_entry
│   └── audit.py                 <- DTB-G2: AuditTemplate, DEFAULT_AUDIT_TEMPLATE, validate_audit_completeness,
│                                  render_audit_checklist, registry_summary
├── adapters/                    <- model glue (DTB-G1 + DTB-G2)
│   ├── __init__.py
│   ├── reference_flowa.py       <- ReferenceFlowAAdapter (placeholder)
│   ├── flowmol3.py              <- FlowMol3Adapter placeholder + FlowMol3Capabilities + default_flowmol3_adapter
│   └── synthetic.py             <- SyntheticContinuousAdapter, SyntheticDiscreteAdapter, SyntheticMixedChannelAdapter,
│                                  SyntheticUnsupportedAdapter
├── eval/                        <- DTB-R7 / DTB-R8 evaluation + reporting
│   ├── __init__.py
│   ├── calibration.py           <- DTB-R7 CPU: wilson_lower_bound, beta_lower_bound, CalibrationBucket,
│   │                             CalibrationManifest, CalibrationTimeSplit, StabilityPerturbationProtocol,
│   │                             classify_bucket, manifest_digest, lower_bound constants
│   ├── protocol.py              <- DTB-R7: PairedComparisonArm, PairedComparisonRegistry,
│   │                             EvaluatorProvenanceGuard, evaluator_guard_digest,
│   │                             RoundToRoundOscillationDetector
│   ├── manifests.py             <- DTB-R7: write_calibration_manifest, read_calibration_manifest,
│   │                             validate_manifest_frozen, frozen_manifest_hash, DEFERRED_GPU_SENTINEL
│   ├── claim_gate.py            <- DTB-R8: ClaimGateConfig, ClaimGateDecision, ClaimGateEvaluation,
│   │                             evaluate_claim_gate, build_default_claim_gate_config, DEFERRED_R8_REASON
│   ├── promotion.py             <- DTB-R8: PromotionReport, PolicyVersionHashRecorder,
│   │                             build_deferred_promotion_report, derive_policy_hash_from_version
│   ├── rollback.py              <- DTB-R8: RollbackFlag, RollbackAudit, apply_rollback,
│   │                             build_disabled_rollback_flag, DEFAULT_DISABLED_REASON
│   └── metric_panel.py          <- DTB-R8: LayeredMetricPanel, enforce_separation,
│                                  build_default_layered_metric_panel, TIER_LABELS
└── legacy/                      <- existing torch-bound / pocket_modules-coupled modules, kept under a subpackage
    ├── __init__.py              <- explicit "this is legacy" warning; nothing new may import from here
    ├── control_policy.py
    ├── metric_feedback.py       <- external_metric_feedback.py renamed
    ├── orchestration.py
    ├── restart_mixer.py         <- restart_memory.py renamed
    ├── plan.py                  <- reinference_plan.py renamed
    ├── loop.py
    ├── loop_contract.py
    ├── mechanism_adapter.py
    └── services.py

tests/                            <- mirrors source structure (see FILE_MAPPING.md §B)
```

---

## 2. Subpackage-by-subpackage rationale

### 2.1 `adaptive_reflow/contracts/` — the foundation

* **Role:** pure data. Frozen dataclasses, `NewType` aliases, hash helpers,
  validators. No I/O, no torch, no mutation of inputs.
* **Borrowed pattern:** vLLM's `protocol.py` + `arg_utils.py` (data carriers
  + Pydantic request/response). vLLM's `arg_utils.py` is "typed request
  shape"; our `contracts/` is the same idea but for a runtime ledger instead
  of a HTTP API.
* **Why a leaf:** every other subpackage depends on this one. The module's
  own docstring says so explicitly: *"stdlib-only: no torch, no other
  adaptive_reflow imports, no IO."* Splitting `restart_memory_types.py` into
  multiple files inside `contracts/` does not violate that — none of the
  new files import each other except by the natural validator→data-class
  dependency within the same package.
* **Public surface (`contracts/__init__.py`):** every dataclass, NewType,
  literal-set constant, hash helper, factory and validator declared in
  `CONTRACTS.md` §1–§8. No internal helpers (`_ok`, `_err`, etc.) leak.

### 2.2 `adaptive_reflow/envelope/` — runtime envelope + tail budget

* **Role:** build/validate the run-start frozen envelope, classify
  endpoints against it, accumulate tail-budget mass.
* **Why its own subpackage:** the envelope + tail-budget machinery is the
  largest *coherent* unit of work in DTB-NC1 + DTB-NC2 + DTB-L3. It pulls
  together `EnvelopeLayer` thresholds, the complement classifier, the
  per-round mass accumulator, and the stratified tail-budget row.
* **Borrowed pattern:** vLLM's `engine/arg_utils.py` + `engine/protocol.py`
  (request shaping before the engine loop).
* **Cycle check:** `envelope/manifest.py` imports from `contracts/` and
  `policy/stratification.py`. No edge into `frame/` or `writer/`.

### 2.3 `adaptive_reflow/frame/` — the universal round frame

* **Role:** every artifact needed to drive *one round* end-to-end: the
  engine + adapter protocol, the bounded merge, the channel rule, the
  operation order, the phase transitions, the round-trace v3 schema, and
  the orchestrator that ties them all together.
* **Why its own subpackage:** vLLM splits `engine/` (the loop) from
  `model_executor/` (per-rank forward). Our `frame/` plays *both* roles
  because there is no distributed scheduling layer — the orchestrator is
  the engine and the channel rule / merge are the per-rank forward
  primitives.
* **`adapter.py` vs `engine.py`:** the adapter Protocol lives with the
  engine that consumes it (mirrors `vllm/model_executor/models/registry.py`
  + `vllm/model_executor/custom_op.py`). The Protocol is *declared* in
  `adapter.py`; the `Engine` class that *consumes* the protocol lives in
  `engine.py`. The decision is intentional: `frame/adapter.py` is the
  duck-typed surface, `frame/engine.py` is the loop.
* **`phase.py` vs `contracts/phase.py`:** the contract (`PhaseState`) and
  the *factory* (`make_default_phase_state` with a deterministic digest)
  live in `contracts/phase.py`; the *runtime helpers*
  (`build_phase_state`, `advance_phase`, `validate_phase_state_transition`)
  live in `frame/phase.py`. This mirrors vLLM's pattern of putting
  Pydantic-shaped args in `arg_utils.py` and engine glue in `engine.py`.
* **`trace.py`:** `RoundTraceV3` is a per-round provenance record consumed
  by the orchestrator and the policy-authority boundary. It is "frame"
  because it is the shape of *one round's evidence*, not a control surface.

### 2.4 `adaptive_reflow/policy/` — pure decision logic

* **Role:** stateless decision logic that is not itself a frame piece
  (archive selection, stratification, pruning, noise accounting).
* **Borrowed pattern:** vLLM's `model_executor/layers/` (hardware-agnostic
  math + bookkeeping, not the model itself).
* **Cycle check:** `policy/` depends on `contracts/` and on
  `envelope/manifest.py` (`StratifiedTailBudgetRow` reaches into `Stratum`).
  No edge into `frame/` — the channel rule and bounded merge live in
  `frame/` because they are *applied* during a round.

### 2.5 `adaptive_reflow/schedule/` — outer restart-noise budget

* **Role:** the closed cosine / linear / constant schedule family and the
  stateful sampler.
* **Why its own subpackage:** DTB-NA1 is a single, well-bounded
  concern. A peer-level subpackage keeps `frame/orchestrator.py` from
  importing schedule internals.

### 2.6 `adaptive_reflow/diagnostics/` — observation-only ledgers

* **Role:** the *observe* leg of DTB-L4. Frozen dataclasses with
  `ledger_only=True`; never influence `beta` / claim / prune.
* **Why its own subpackage:** `noise_mass_accounting.py` (the *calc* leg)
  is in `policy/`, but the *observation* rows are different from the
  calculated quantities and must not be confused with them. Splitting
  them makes the boundary explicit at the import level.

### 2.7 `adaptive_reflow/writer/` — single-writer authority + registry

* **Role:** DTB-S1 writer arbitration, DTB-G2 registry + audit template,
  DTB-R3 core-runtime handoff.
* **Borrowed pattern:** vLLM's `entrypoints/` (the canonical public
  surface for the component). All four modules are "what talks to the
  rest of the system" — the writer authority decides who is allowed to
  write, the registry decides which candidates are admitted, the audit
  template decides what an auditor needs, the handoff describes what the
  downstream owner must implement.
* **`audit.py` vs `registry.py`:** the audit template is a separate
  concern from the registry itself. Putting them in the same subpackage
  keeps them near each other (they share types) without forcing one
  file to depend on the other.

### 2.8 `adaptive_reflow/adapters/` — model glue (DTB-G1/G2)

* **Role:** every concrete `FlowMatchingODEAdapter` implementation.
* **Borrowed pattern:** vLLM's `model_executor/models/` (per-architecture
  forward passes).
* **`synthetic.py` lives here, not in `tests/`:** the four synthetic
  fixtures are public artifacts consumed by both the test suite *and*
  any future external parity harness. Hiding them in `tests/` would
  prevent re-use.

### 2.9 `adaptive_reflow/eval/` — R7/R8 protocols

* **Role:** CPU-only DTB-R7 (calibration + paired evaluation + manifest
  I/O) and DTB-R8 (claim gate + promotion + rollback + layered metric
  panel).
* **Borrowed pattern:** vLLM's `benchmarks/` + `tests/` (off-line
  measurement harnesses).
* **Why its own subpackage:** these are observability + reporting
  surfaces, not control surfaces. Putting them at peer level with
  `frame/` makes the boundary obvious.

### 2.10 `adaptive_reflow/legacy/` — existing torch + pocket_modules glue

* **Role:** the eight existing modules that depend on torch and / or the
  upstream `pocket_modules` package. They are kept (so the rest of the
  codebase that imports them still works) but quarantined.
* **`legacy/__init__.py` rule:** emits a `DeprecationWarning` at import
  time so any new code that accidentally reaches in is warned. Nothing
  inside `legacy/` may be imported by any other `adaptive_reflow/*`
  subpackage.

---

## 3. Import direction

The package forms a strict DAG. Every edge points "downward":

```
legacy ──> frame ──> envelope ──> contracts
   │         │           │
   │         ├───────────┤
   │         v           v
   │       policy ──> diagnostics
   │         │
   │         v
   │       schedule ──> contracts
   │
   └─> adapters ──> frame ──> contracts
   └─> eval ──> frame, contracts
   └─> writer ──> frame, contracts, adapters, policy
```

Rules enforced by `contracts/__init__.py` (the leaf):

1. **No upward edges.** `contracts/` imports nothing from this package.
2. **No peer-level cycles.** `frame/orchestrator.py` reaches into
   `writer/authority.py` for `WriterArbitrator` — but `writer/` never
   imports `frame/orchestrator.py`.
3. **No cross-package reach.** `policy/stratification.py` is used by
   `envelope/manifest.py` (for `StratifiedTailBudgetRow`); neither is
   used by `frame/`. This is intentional: the channel rule and bounded
   merge never see `Stratum`, only the orchestrator + envelope do.
4. **Legacy isolation.** `legacy/` is a sink; nothing else points into it.

### 3.1 Cycle-risk audit (called out before the move)

| Pair | Risk | Mitigation |
|---|---|---|
| `frame/orchestrator.py` ↔ `writer/authority.py` | Orchestrator holds a `WriterArbitrator`; arbitrator needs contract types only. | `writer/authority.py` imports from `contracts/authority.py` only. |
| `envelope/manifest.py` ↔ `policy/stratification.py` | Stratified tail-budget row depends on `Stratum`. | `policy/stratification.py` imports from `contracts/` only. |
| `writer/audit.py` ↔ `writer/registry.py` | Audit template references `CandidateEntry`. | `audit.py` imports from `registry.py`; `registry.py` does not import from `audit.py`. |
| `adapters/flowmol3.py` ↔ `writer/registry.py` | FlowMol3 adapter pulls `FLOWMOL3_PINNED_COMMIT` from the registry. | One-way edge: adapters → writer. |
| `eval/promotion.py` ↔ `eval/claim_gate.py` | Promotion report carries `ClaimGateDecision`. | `promotion.py` imports from `claim_gate.py`; `claim_gate.py` does not import `promotion.py`. |
| `frame/engine.py` ↔ `frame/adapter.py` | Engine consumes the adapter Protocol. | One-way edge: `engine.py` → `adapter.py`. |
| `frame/orchestrator.py` ↔ `frame/{merge,channel_rule,operation,phase,engine,trace}.py` | Orchestrator pulls many runtime helpers. | One-way edge: `orchestrator.py` → everything else in `frame/`. |

No cycle. The DAG is acyclic by construction.

---

## 4. `__init__.py` curated surfaces (one entry per subpackage)

Each subpackage exposes a *narrow* public API. Internal helpers stay
module-internal. "Public" here means "importable via the package's
top-level re-exports" — anything else must be reached via the explicit
module path (e.g. `adaptive_reflow.frame.merge.bounded_merge`).

### 4.1 `adaptive_reflow/__init__.py`

```python
"""Adaptive reflow — typed contracts + frame + policy + writer + eval.

Public, dependency-free surface (lazy imports to keep import cost low):
"""

from .contracts import (
    BundleId, LedgerRowId, ManifestId, RunId, SampleId, TriggerId,
    TraceDigest, ConditionDigest, ArtifactHash, MechanismId, ChannelName,
    FeedbackMode, FactorValue, ComplementBlockerCode, RestartTriggerCode,
    PolicyId, ProvenanceChain,
    RoundResultBundle, ChannelTransferEvidence, ChannelTransferDecision,
    DynamicRestartTransferLedger, NoiseBiasInputRow,
    EnvelopeLayer, FrozenEnvelopeManifest, EnvelopeClassification, TailBudgetRow,
    ChannelRuleInputs, ChannelRuleOutputs,
    CosineScheduleConfig, CosineScheduleSample, FreshNoiseFloor, RestartTriggerEvent,
    PhaseState, OperationCompositionContract, CommutatorResidualDiagnostic,
    RestartPolicyAuthorityContract, LegacyCompatibilityWindow, FinalRestartPolicy,
    ArchiveQuota, ArchiveAuditTrail,
    hash_artifact, hash_bundle_id, hash_trace_digest,
    hash_phase_state_digest, hash_policy_hash,
    make_default_phase_state, make_default_phase_state_digest,
)
```

### 4.2 `adaptive_reflow/contracts/__init__.py`

Re-export everything documented in `CONTRACTS.md` §1–§8 + the NewTypes,
literal-set constants, hash helpers, and validators.

### 4.3 `adaptive_reflow/envelope/__init__.py`

```python
from .manifest import (
    FrozenEnvelopeManifestBuilder, ManifestBuildError,
    classify_endpoint, TailBudgetAccumulator, StratifiedTailBudgetRow,
)
```

### 4.4 `adaptive_reflow/frame/__init__.py`

```python
from .adapter import (
    TensorRef, AdapterCapabilities, StateBundle, ODEConditionDelta, ODEIntegratorTrace,
    FlowMatchingODEAdapter, RestartPolicy,
    CapabilityMissingError, CapabilityMismatchError,
    REFERENCE_FRAMES, NORMALIZATION_KINDS, DOMAIN_BY_CHANNEL,
    validate_state_bundle, validate_condition_delta,
    validate_integrator_trace, validate_capabilities,
)
from .engine import (
    ENGINE_VERSION, DEFAULT_OPERATION_STEPS, FEATURE_FLAG_KEY,
    RoundTrace, LedgerRow, PhaseState, EngineRoundResult, Engine,
    ERR_BUNDLE_NONE, ERR_BUNDLE_INVALID, ERR_POLICY_NONE, ERR_PHASE_STATE_NONE,
    ERR_ROUND_INDEX_NEGATIVE, ERR_ADAPTER_NONE, ERR_CAPABILITIES_INVALID,
    ERR_CHANNEL_UNSUPPORTED, ERR_CHANNEL_DOMAIN_MISMATCH, ERR_DETACH_PROOF_FAILED,
    ERR_CONDITION_DELTA_NO_EFFECT, ERR_INTEGRATOR_TRACE_MISSING,
    ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH, ERR_FEATURE_DISABLED,
)
from .merge import (
    MERGE_AUTHORITY_SCHEMA_NAME, MERGE_AUTHORITY_SCHEMA_VERSION,
    MergeAuthorityError, bounded_merge, bounded_merge_with_schedule,
)
from .operation import (
    DEFAULT_OPERATION_ORDER, DEFAULT_OPERATION_COMPOSITION_VERSION,
    DEFAULT_COMMUTATOR_RESIDUAL_TOLERANCE,
    ERR_OPERATION_ORDER_EMPTY, ERR_OPERATION_ORDER_DUPLICATE,
    ERR_OPERATION_ORDER_UNKNOWN, ERR_OPERATION_ORDER_INCOMPLETE,
    ERR_VERSION_EMPTY, ERR_VERSION_NONE, ERR_CONTRACT_NONE,
    ERR_RECORDED_AT_ROUND_NONE, ERR_RECORDED_AT_ROUND_NON_INT,
    ERR_RECORDED_AT_ROUND_NEGATIVE, ERR_RESIDUAL_NORM_NON_NUMERIC,
    ERR_STEPS_NONE,
    build_default_composition_contract, validate_operation_order,
    record_commutator_residual, replay_default_order,
)
from .channel_rule import (
    CANONICAL_FACTOR_ORDER,
    BLOCKER_TAIL_INADMISSIBLE, BLOCKER_COMPLEMENT_EXCLUDED, BLOCKER_PROXY_ONLY,
    BLOCKER_HORIZON_UNPROVEN, BLOCKER_NOT_FINITE_PREFIX,
    BLOCKER_ENVELOPE_HASH_MISSING, BLOCKER_MISSING_FACTOR,
    BLOCKER_NON_FINITE, BLOCKER_NAN_OR_INF,
    BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL,
    check_monotonicity_property, compute_channel_decision,
    required_factors_in_unit_interval,
)
from .phase import (
    build_phase_state, advance_phase, make_default_phase_state,
    validate_phase_state_transition,
)
from .trace import (
    ROUND_TRACE_V2_SCHEMA_NAME, ROUND_TRACE_V3_SCHEMA_NAME,
    PRODUCER_MODES, ALLOWED_FINAL_POLICY_WRITERS,
    FINAL_POLICY_WRITER_ADAPTIVE_REFLOW, FINAL_POLICY_WRITER_LEGACY_NOISE_BIAS,
    RoundTraceV3,
    compute_round_trace_v3_content_hash, freeze_round_trace_v3,
    round_trip_round_trace_v3, read_round_trace_v2,
)
from .orchestrator import (
    AdaptiveReflowPolicyOrchestrator,
    PolicyOrchestratorError, PolicyOrchestratorValidationError,
)
```

### 4.5 `adaptive_reflow/policy/__init__.py`

```python
from .archive import (
    ArchiveEntry, SameSampleArchive,
    CandidateArchiveError, CandidateArchiveLineageError,
    CandidateArchiveValidationError,
)
from .stratification import (
    Stratum, StratumAssignment,
    dominance_ratio, cross_stratum_mix_rejected,
)
from .pruning import (
    PruneDecision, PruneGate, UnorderedAuditResult,
)
from .noise_mass import (
    physical_noise_proxy, RMS_preserving_mixing_coefficient,
    exact_spectral_variance, ThreeWayDistinction,
    adversarial_stagnation_test,
    ERR_PROXY_INPUT_INVALID, ERR_BETA_INPUT_INVALID,
    ERR_SPECTRAL_INPUT_INVALID, ERR_CURVE_NOT_SEQUENCE,
    ERR_CURVE_ENTRY_NOT_FINITE,
)
```

### 4.6 `adaptive_reflow/schedule/__init__.py`

```python
from .cosine import (
    n_cap_for_round, CosineScheduleSampler,
    validate_cosine_schedule_config, default_floor_by_channel,
    build_fresh_noise_diagnostics,
    ERR_CYCLE_LENGTH_NON_INT, ERR_CYCLE_LENGTH_TOO_SMALL,
    ERR_SCHEDULE_FAMILY_INVALID, ERR_N_MIN_NOT_FINITE, ERR_N_MAX_NOT_FINITE,
    ERR_N_MIN_OUT_OF_RANGE, ERR_N_MAX_OUT_OF_RANGE, ERR_N_MAX_LT_N_MIN,
    ERR_PER_CHANNEL_CAP_INVALID, ERR_FRESH_NOISE_FLOOR_INVALID,
    ERR_DELTA_CAP_INVALID, ERR_UNKNOWN_CHANNEL, ERR_RESTART_TRIGGER_INVALID,
    ERR_CONFIG_HASH_EMPTY, ERR_NOT_FROZEN_BEFORE_EVAL,
)
```

### 4.7 `adaptive_reflow/diagnostics/__init__.py`

```python
from .ledger import (
    FreshNoiseCumulativeMassRecord, SpectralResidualBandProxy, TailDiagnosticStatus,
    validate_fresh_noise_cumulative_mass_record,
    validate_spectral_residual_band_proxy, validate_tail_diagnostic_status,
    empty_diagnostics,
    ERR_ROUND_NOT_INT, ERR_ROUND_NEGATIVE, ERR_CYCLE_NOT_INT, ERR_CYCLE_NEGATIVE,
    ERR_N_CAP_NOT_FINITE, ERR_N_MIN_NOT_FINITE, ERR_N_MAX_NOT_FINITE,
    ERR_MASS_NOT_FINITE, ERR_MASS_NEGATIVE, ERR_CAPACITY_CURVE_NOT_TUPLE,
    ERR_CAPACITY_ENTRY_NOT_PAIR, ERR_RESIDUAL_LOWER_NOT_FINITE,
    ERR_RESIDUAL_UPPER_NOT_FINITE, ERR_RESIDUAL_ORDER,
    ERR_SUMMABLE_STATUS_INVALID,
)
```

### 4.8 `adaptive_reflow/writer/__init__.py`

```python
from .authority import (
    WriterArgumentError, WriterArbitrator,
    build_default_authority_contract,
    build_final_restart_policy, verify_policy_against_ledger,
    DEFAULT_AUTHORITY_CONTRACT_VERSION, EXECUTABLE_WRITER_MECHANISM_ID,
    DIAGNOSTIC_WRITER_MECHANISM_ID, CONSUMER_WRITER_ID,
    LEGACY_SCHEMA_READ_COMPATIBILITY_VERSION, REQUEST_MODES, DEFAULT_MODE_FLAGS,
)
from .handoff import (
    CORE_RUNTIME_OWNER, CORE_RUNTIME_HANDBOFF_SCHEMA_NAME,
    CORE_RUNTIME_HANDBOFF_SCHEMA_VERSION,
    CoreRuntimeHandoff, CoreRuntimeHandoffError,
    build_core_runtime_handoff, write_handoff_spec,
)
from .registry import (
    FLOWMOL3_PINNED_COMMIT,
    AdapterStatus, TaskCondition,
    CandidateEntry, CandidateRegistry,
    admit_entry, make_initial_registry, default_registry,
    make_default_flowmol3_entry,
)
from .audit import (
    DEFAULT_AUDIT_TEMPLATE, AuditTemplate,
    validate_audit_completeness, render_audit_checklist, registry_summary,
)
```

### 4.9 `adaptive_reflow/adapters/__init__.py`

```python
from .reference_flowa import REFERENCE_FLOWA_CHANNELS, ReferenceFlowAAdapter
from .flowmol3 import (
    FLOWMOL3_CHANNELS, FlowMol3Adapter, FlowMol3Capabilities,
    default_flowmol3_adapter, flowmol3_registry_entry,
)
from .synthetic import (
    CONTINUOUS_CHANNELS, DISCRETE_CHANNELS, MIXED_CHANNELS, ALL_SYNTHETIC_CHANNELS,
    SyntheticContinuousAdapter, SyntheticDiscreteAdapter,
    SyntheticMixedChannelAdapter, SyntheticUnsupportedAdapter,
)
```

### 4.10 `adaptive_reflow/eval/__init__.py`

```python
from .calibration import (
    CalibrationDatasetId, BucketKey, IsoTimestamp, SampleCount, ConfidenceLevel,
    LOWER_BOUND_METHODS, PREDECLARED_SAFETY_METRICS, CHANNEL_NAMES_FOR_CALIBRATION,
    wilson_lower_bound, beta_lower_bound,
    CalibrationTimeSplit, CalibrationBucket, CalibrationManifest,
    StabilityPerturbationProtocol,
    classify_bucket, manifest_digest,
)
from .protocol import (
    ArmName, PolicyHash, ConfigHash, EvaluatorVersion, MaterializationRoute,
    TargetPocketHash,
    PAIRED_ARM_KINDS,
    PairedComparisonArm, PairedComparisonRegistry,
    EvaluatorProvenanceGuard, evaluator_guard_digest,
    RoundToRoundOscillationDetector,
)
from .manifests import (
    JsonString, ValidationResult,
    DEFERRED_GPU_SENTINEL,
    write_calibration_manifest, read_calibration_manifest,
    validate_manifest_frozen, frozen_manifest_hash,
)
from .claim_gate import (
    DEFERRED_R8_REASON,
    ClaimGateConfig, ClaimGateDecision, ClaimGateEvaluation,
    ClaimGateArgumentError,
    build_default_claim_gate_config, evaluate_claim_gate,
)
from .promotion import (
    DEFERRED_GAIN, DEFERRED_COST, DEFERRED_R8_REASON,
    PromotionReport, PolicyVersionHashRecorder,
    PromotionArgumentError,
    build_deferred_promotion_report, derive_policy_hash_from_version,
)
from .rollback import (
    DEFAULT_DISABLED_REASON,
    RollbackFlag, RollbackAudit,
    RollbackArgumentError,
    apply_rollback, build_disabled_rollback_flag,
)
from .metric_panel import (
    TIER_LABELS, LayeredEvidenceTiers, LayeredMetricPanel,
    LayeredMetricPanelArgumentError,
    build_default_layered_metric_panel, enforce_separation,
)
```

### 4.11 `adaptive_reflow/legacy/__init__.py`

```python
"""Legacy adaptive_reflow modules (torch + pocket_modules bound).

This subpackage is a quarantine. Nothing else in ``adaptive_reflow/*``
imports from here; nothing here is part of the public surface. The
modules are kept so existing tests and the upstream ``pocket_modules``
binding keep working until the migration plan retires them.

Re-export is intentionally empty.
"""
import warnings as _warnings
_warnings.warn(
    "adaptive_reflow.legacy is a quarantine; do not import from it in new code",
    DeprecationWarning,
    stacklevel=2,
)
__all__: list[str] = []
```

---

## 5. Decisions and adjustments to the proposed layout

The proposed layout (in the prompt) was the right starting point. The
following adjustments were made after reading every module:

1. **`frame/` owns `trace.py`.** The `RoundTraceV3` schema is a
   per-round provenance record consumed by the orchestrator; it is
   naturally framed next to `engine.py` / `orchestrator.py` / `phase.py`.
2. **`contracts/decision.py` is reserved-but-empty.** DTB-R2 contract
   types (`ChannelRuleInputs` / `ChannelRuleOutputs`) live in
   `contracts/bundle.py` because they pair with the per-channel evidence
   dataclasses. `decision.py` exists to keep the layout symmetric with
   `envelope.py` / `schedule.py` / etc., and to host any future
   decision-shape additions.
3. **`envelope/manifest.py` keeps `StratifiedTailBudgetRow`.** It is
   built by `TailBudgetAccumulator.stratified_snapshot`, not by
   `policy/stratification.py`. Splitting it off into a separate module
   would create a one-class file with no collaborators.
4. **`adapters/synthetic.py` is *not* in `tests/`.** It is consumed by
   the test suite *and* by any future external parity harness.
5. **`legacy/control_policy.py` / `metric_feedback.py` / `plan.py` /
   `restart_mixer.py` are renamed** to remove the legacy module names
   from the package's URL space (the originals collide with no other
   `adaptive_reflow/*` module, but renaming makes the quarantine
   unmistakable: anything in `legacy/` is a renamed original).
6. **`writer/registry.py` is renamed from `candidate_registry.py`.**
   The new name matches the subpackage (`writer/`) so the import path
   reads `adaptive_reflow.writer.registry`.
7. **`frame/channel_rule.py` is renamed from `channel_rule.py`.** Same
   reason — the import path becomes `adaptive_reflow.frame.channel_rule`.
8. **`eval/` is one subpackage, not split between `r7/` and `r8/`.**
   Splitting by DTB id would create three-to-five-file subpackages; the
   shared `eval/` keeps related CPU-only validation harnesses in one
   place (mirrors vLLM's `benchmarks/`).

---

## 6. Migration plan (sketch; not in scope for this phase)

The actual file moves, subpackage splits, and conftest updates are
described in `FILE_MAPPING.md`. The order is:

1. Create `adaptive_reflow/{contracts,envelope,frame,policy,schedule,
   diagnostics,writer,adapters,eval,legacy}/__init__.py` files.
2. Move files into the leaf subpackages per `FILE_MAPPING.md`.
3. Split `restart_memory_types.py` into `contracts/{types,hashes,
   validators,bundle,decision,envelope,schedule,phase,operations,
   authority,archive}.py` per `SPLIT_NOTES.md`.
4. Split `envelope_manifest.py` into `envelope/{manifest,classifier,
   tail_budget}.py` per `SPLIT_NOTES.md`.
5. Update `tests/conftest.py` and the test files to import from the new
   package paths.
6. Delete the old flat root files.

Each step keeps the existing 362 tests green until the very last step
(the import paths change in lockstep with the source moves).