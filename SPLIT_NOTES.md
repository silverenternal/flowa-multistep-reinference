# SPLIT_NOTES — `restart_memory_types.py` + `envelope_manifest.py`

Two source files are too large to land in any single subpackage as-is:

* `restart_memory_types.py` — 1,363 lines, 49 KB. It declares every
  typed contract + NewType + hash helper + validator in the system.
* `envelope_manifest.py` — 836 lines, 36 KB. It carries the run-start
  envelope builder, the complement classifier, the tail-budget
  accumulator, and the DTB-L3 stratified extension.

Both will be split into multiple files inside their target subpackage.
This document enumerates the per-symbol placement, the line ranges
(measured against the current source), and the cross-file imports
that must be rewritten.

Line numbers below are derived from the file content read for this
review and are accurate at the time of writing; the migration step
should re-verify them with `grep -n` before the cut.

---

## 1. `restart_memory_types.py` → `adaptive_reflow/contracts/*`

The file is structured by `CONTRACTS.md` §1–§8 with three preceding
sections (NewTypes, literal sets, hash helpers + validators). The split
mirrors that structure: every section lands in its own file under
`adaptive_reflow/contracts/`.

### 1.1 `contracts/types.py`

* **Lines:** 39–70 (NewType aliases), 76–137 (literal-set constants).
* **Imports:** stdlib only.
* **Symbols:**
  * NewType aliases: `BundleId`, `LedgerRowId`, `ManifestId`, `RunId`,
    `SampleId`, `TriggerId`, `TraceDigest`, `ConditionDigest`,
    `ArtifactHash`, `MechanismId`, `ChannelName`, `FeedbackMode`,
    `FactorValue`, `ComplementBlockerCode`, `RestartTriggerCode`,
    `PolicyId`, `ProvenanceChain`, `FrameSpec`, `ShapeSpec`,
    `MaterializationEvidenceRef`, `EvaluatorProvenanceRef`,
    `FeedbackEvidenceRef`, `CoordinateChannelRef`, `ChargeChannelRef`,
    `RawPairChannelRef`, `ProjectedPairChannelRef`, `TailBudgetRowId`.
  * Literal-set tuples: `CHANNEL_NAMES`, `FEEDBACK_MODES`,
    `COMPLEMENT_BLOCKER_CODES`, `RESTART_TRIGGER_CODES`,
    `SCHEDULE_FAMILIES`, `SCHEDULE_PHASES`,
    `FRESH_NOISE_FLOOR_SOURCES`, `OPERATION_STEPS`,
    `DEFAULT_OPERATION_ORDER`, `AUTHORITY_MODES`.
* **Cross-file usage:** every other contracts file imports from
  `types.py`. The downstream `frame/`, `policy/`, `envelope/`,
  `schedule/`, `writer/`, `eval/`, `adapters/`, `diagnostics/` files
  import types from `contracts/__init__.py` (the re-export surface).

### 1.2 `contracts/hashes.py`

* **Lines:** 144–285 (helpers + canonical hashers).
* **Imports:** stdlib only + `.types` for the `ArtifactHash` /
  `TraceDigest` NewType wrappers.
* **Symbols:**
  * `ValidationResult` alias (moved from §1.4 below — see 1.4).
  * `_ok`, `_err` — internal; module-private, not re-exported.
  * `_canonical_json`, `_json_default` — internal.
  * `hash_artifact`, `hash_bundle_id`, `hash_trace_digest`,
    `hash_phase_state_digest`, `hash_policy_hash`,
    `_bundle_identity_payload`, `_sorted_items`.

### 1.3 `contracts/validators.py`

* **Lines:** 144 (alias only, see 1.4), 919–972 (numeric / scalar
  validators).
* **Imports:** stdlib only.
* **Symbols:**
  * `validate_unit_float`, `validate_unit_factor`,
    `validate_positive_int`, `validate_nonneg_int`.

### 1.4 `ValidationResult` alias placement — important

The `ValidationResult = Tuple[bool, Tuple[str, ...]]` alias is used by
nearly every `validate_*` function in the file. Two options:

* **Option A (chosen):** place `ValidationResult` in `hashes.py`
  alongside `_ok` / `_err`, since the validators that return it live
  there conceptually (they all use the `_ok` / `_err` helpers).
* **Option B:** place it in `validators.py`. Slightly more cohesive
  but requires `_ok` / `_err` to also live in `validators.py` —
  which is the cleaner factoring. Choose **Option B**: re-home
  `_ok` / `_err` and `ValidationResult` to `validators.py`; keep
  `hashes.py` purely about hash computation.

> **Correction to `ARCHITECTURE_PLAN.md` §4.2:** `ValidationResult`
> is in `contracts/validators.py`, not `contracts/hashes.py`. The
> `validators.py` public surface is:
>
> ```python
> from .validators import (
>     ValidationResult,
>     validate_unit_float, validate_unit_factor,
>     validate_positive_int, validate_nonneg_int,
> )
> ```

### 1.5 `contracts/bundle.py` (DTB-R1 + DTB-R2 inputs/outputs)

* **Lines:** 293–393 (`RoundResultBundle`, `ChannelTransferEvidence`,
  `ChannelTransferDecision`, `DynamicRestartTransferLedger`,
  `NoiseBiasInputRow`), 509–547 (`ChannelRuleInputs`,
  `ChannelRuleOutputs`), 991–1140 (`validate_round_result_bundle`,
  `validate_channel_evidence`).
* **Imports:** stdlib only + `.types` (NewTypes + literal sets) +
  `.validators` (`validate_unit_factor`).
* **Symbols:** `RoundResultBundle`, `ChannelTransferEvidence`,
  `ChannelTransferDecision`, `DynamicRestartTransferLedger`,
  `NoiseBiasInputRow`, `ChannelRuleInputs`, `ChannelRuleOutputs`,
  `validate_round_result_bundle`, `validate_channel_evidence`.
* **Note:** the channel-rule *runtime* (the `compute_channel_decision`
  pure function) lives in `frame/channel_rule.py`. Only the *inputs*
  and *outputs* of the rule are contracts; this is a deliberate
  boundary so the channel-rule logic can evolve without forcing
  contract changes.

### 1.6 `contracts/decision.py`

* **Lines:** (none — empty after the split).
* **Purpose:** symmetry with `contracts/envelope.py` and the other
  per-DTB files. Reserved for any future decision-shape dataclasses
  that need to live at peer-level with `bundle.py`. Do not export
  anything until an actual addition lands.

### 1.7 `contracts/envelope.py` (DTB-NC1 + DTB-NC2 contract types)

* **Lines:** 428–501 (`EnvelopeLayer`, `FrozenEnvelopeManifest`,
  `EnvelopeClassification`, `TailBudgetRow`), 1143–1201
  (`validate_envelope_manifest`, `validate_tail_budget_row`).
* **Imports:** stdlib only + `.types`.
* **Symbols:** `EnvelopeLayer`, `FrozenEnvelopeManifest`,
  `EnvelopeClassification`, `TailBudgetRow`,
  `validate_envelope_manifest`, `validate_tail_budget_row`.
* **Note:** the *runtime* (manifest builder, complement classifier,
  tail-budget accumulator) lives in `envelope/manifest.py`. Only
  the contract types and their validators live here.

### 1.8 `contracts/schedule.py` (DTB-NA1 contract types)

* **Lines:** 554–617 (`CosineScheduleConfig`, `CosineScheduleSample`,
  `FreshNoiseFloor`, `RestartTriggerEvent`).
* **Imports:** stdlib only + `.types`.
* **Symbols:** `CosineScheduleConfig`, `CosineScheduleSample`,
  `FreshNoiseFloor`, `RestartTriggerEvent`.
* **Note:** `n_cap_for_round`, `CosineScheduleSampler`,
  `validate_cosine_schedule_config` etc. live in `schedule/cosine.py`.

### 1.9 `contracts/phase.py` (DTB-L1 contract + factory)

* **Lines:** 624–641 (`PhaseState` dataclass), 867–915
  (`make_default_phase_state`, `make_default_phase_state_digest`),
  1204–1235 (`validate_phase_state`).
* **Imports:** stdlib only + `.types` + `.schedule` (for the forward
  reference to `RestartTriggerEvent` used in `PhaseState`).
* **Symbols:** `PhaseState`, `make_default_phase_state`,
  `make_default_phase_state_digest`, `validate_phase_state`.
* **Note:** the runtime helpers (`build_phase_state`, `advance_phase`,
  `validate_phase_state_transition`) live in `frame/phase.py`. They
  re-import `make_default_phase_state` as
  `_make_default_phase_state_from_types` and wrap it.

### 1.10 `contracts/operations.py` (DTB-L2 contract)

* **Lines:** 648–671 (`OperationCompositionContract`,
  `CommutatorResidualDiagnostic`).
* **Imports:** stdlib only + `.types`.
* **Symbols:** `OperationCompositionContract`,
  `CommutatorResidualDiagnostic`, `OPERATION_STEPS`,
  `DEFAULT_OPERATION_ORDER`.
* **Note:** the runtime (`build_default_composition_contract`,
  `validate_operation_order`, `record_commutator_residual`,
  `replay_default_order`) lives in `frame/operation.py`.

### 1.11 `contracts/authority.py` (DTB-S1 contract types)

* **Lines:** 679–720 (`RestartPolicyAuthorityContract`,
  `LegacyCompatibilityWindow`, `FinalRestartPolicy`), 1238–1260
  (`validate_final_restart_policy`), 257–280 (`hash_policy_hash`).
* **Imports:** stdlib only + `.types` + `.hashes` (for
  `hash_artifact`).
* **Symbols:** `RestartPolicyAuthorityContract`,
  `LegacyCompatibilityWindow`, `FinalRestartPolicy`,
  `validate_final_restart_policy`.
* **Note:** `hash_policy_hash` lives in `hashes.py`; this file just
  re-imports it for the public surface.

### 1.12 `contracts/archive.py` (DTB-R4 contract)

* **Lines:** 728–852 (`ArchiveQuota`, `ArchiveAuditTrail`),
  759–825 (`validate_archive_quota`).
* **Imports:** stdlib only + `.types` + `.validators`.
* **Symbols:** `ArchiveQuota`, `ArchiveAuditTrail`,
  `validate_archive_quota`.
* **Note:** the runtime (`SameSampleArchive`) lives in
  `policy/archive.py`.

### 1.13 Cross-file imports inside `contracts/`

Each contracts file may import from other contracts files. The
dependency graph inside `contracts/` is:

```
types  <--  hashes, validators, bundle, envelope, schedule,
             phase, operations, authority, archive

hashes <-- bundle (for hash_artifact), envelope (for hash_artifact),
          schedule (none directly), phase (for hash_phase_state_digest),
          operations (for hash_artifact), authority (for hash_policy_hash),
          archive (for hash_artifact)

validators <-- bundle (for validate_unit_factor),
              archive (for validate_unit_factor)

schedule <-- phase (PhaseState references RestartTriggerEvent)
```

No cycles. The split keeps each file under 400 lines.

### 1.14 `contracts/__init__.py` (re-export surface)

Curated, alphabetically grouped:

```python
"""Adaptive reflow typed contracts (CONTRACTS.md §1-§8).

Pure stdlib dataclasses, NewType aliases, hash helpers, validators.
No I/O, no torch, no other adaptive_reflow imports.
"""
# ---- NewType aliases ----
from .types import (
    ArtifactHash, BundleId, ChannelName, ChargeChannelRef,
    ComplementBlockerCode, ConditionDigest, CoordinateChannelRef,
    EvaluatorProvenanceRef, FactorValue, FeedbackEvidenceRef,
    FeedbackMode, FrameSpec, LedgerRowId, ManifestId, MaterializationEvidenceRef,
    MechanismId, PolicyId, ProjectedPairChannelRef, ProvenanceChain,
    RawPairChannelRef, RunId, SampleId, ShapeSpec, TailBudgetRowId,
    TraceDigest, TriggerId,
)

# ---- Literal-set constants ----
from .types import (
    AUTHORITY_MODES, CHANNEL_NAMES, COMPLEMENT_BLOCKER_CODES,
    DEFAULT_OPERATION_ORDER, FEEDBACK_MODES, FRESH_NOISE_FLOOR_SOURCES,
    OPERATION_STEPS, RESTART_TRIGGER_CODES, SCHEDULE_FAMILIES,
    SCHEDULE_PHASES,
)

# ---- Hash helpers ----
from .hashes import (
    hash_artifact, hash_bundle_id, hash_phase_state_digest,
    hash_policy_hash, hash_trace_digest,
)

# ---- Validators + ValidationResult ----
from .validators import (
    ValidationResult,
    validate_nonneg_int, validate_phase_state, validate_positive_int,
    validate_unit_factor, validate_unit_float,
)

# ---- DTB-R1 + DTB-R2 contract ----
from .bundle import (
    ChannelRuleInputs, ChannelRuleOutputs,
    ChannelTransferDecision, ChannelTransferEvidence,
    DynamicRestartTransferLedger, NoiseBiasInputRow, RoundResultBundle,
    validate_channel_evidence, validate_round_result_bundle,
)

# ---- DTB-NC1 / NC2 contract ----
from .envelope import (
    EnvelopeClassification, EnvelopeLayer, FrozenEnvelopeManifest,
    TailBudgetRow, validate_envelope_manifest, validate_tail_budget_row,
)

# ---- DTB-NA1 contract ----
from .schedule import (
    CosineScheduleConfig, CosineScheduleSample, FreshNoiseFloor,
    RestartTriggerEvent,
)

# ---- DTB-L1 contract + factory ----
from .phase import (
    PhaseState, make_default_phase_state, make_default_phase_state_digest,
    validate_phase_state as _validate_phase_state_contract,
)
# Re-export to the original symbol name; the frame runtime imports
# it under a different name (validate_phase_state_runtime) to avoid
# shadowing.
validate_phase_state = _validate_phase_state_contract

# ---- DTB-L2 contract ----
from .operations import (
    CommutatorResidualDiagnostic, OperationCompositionContract,
)

# ---- DTB-S1 contract ----
from .authority import (
    FinalRestartPolicy, LegacyCompatibilityWindow,
    RestartPolicyAuthorityContract, validate_final_restart_policy,
)

# ---- DTB-R4 contract ----
from .archive import (
    ArchiveAuditTrail, ArchiveQuota, validate_archive_quota,
)
```

---

## 2. `envelope_manifest.py` → `adaptive_reflow/envelope/*`

The file is structured as:

1. Local `NewType` (line 51).
2. Observable-key constants (60–77).
3. Observable extraction (`_coerce_*` helpers + `_read_observables`
   + `_within_layer`) (80–196).
4. `ManifestBuildError` + `FrozenEnvelopeManifestBuilder` (200–379).
5. Complement classifier (`_classify_blocker`, `classify_endpoint`)
   (382–485).
6. `TailBudgetAccumulator` + `reset_cycle` (488–725).
7. `StratifiedTailBudgetRow` + helpers (728–824).
8. `__all__` (827–836).

### 2.1 `envelope/manifest.py`

* **Lines:** 51 (the `EvidenceRowHash` NewType re-export, internal),
  204–379 (`ManifestBuildError`, `FrozenEnvelopeManifestBuilder` +
  `RunIdPlaceholder` / `SampleIdPlaceholder`), 418–485
  (`classify_endpoint`, `_classify_blocker`), 493–725
  (`TailBudgetAccumulator` + `reset_cycle`), 733–824
  (`StratifiedTailBudgetRow`).
* **Imports:**
  * `from adaptive_reflow.contracts import (
        ArtifactHash, BundleId, ComplementBlockerCode,
        EnvelopeClassification, EnvelopeLayer, FactorValue,
        FrozenEnvelopeManifest, ManifestId, RoundResultBundle,
        TailBudgetRow, TailBudgetRowId, hash_artifact,
    )`
  * `from adaptive_reflow.policy.stratification import Stratum`
* **Symbols:** `FrozenEnvelopeManifestBuilder`, `ManifestBuildError`,
  `EvidenceRowHash` (private NewType, internal), `classify_endpoint`,
  `TailBudgetAccumulator`, `StratifiedTailBudgetRow`.
* **Public exports:** `FrozenEnvelopeManifestBuilder`,
  `ManifestBuildError`, `EvidenceRowHash` (re-exported for tests),
  `classify_endpoint`, `TailBudgetAccumulator`,
  `StratifiedTailBudgetRow`.

### 2.2 `envelope/classifier.py`

* **Lines:** 60–196 (observable keys, coerce helpers, observable
  extraction, `_within_layer`).
* **Imports:** stdlib only.
* **Symbols (module-private; re-exported through `manifest.py`):**
  * Constants: `OBS_COORDINATE_EXTENT_RMS`, `OBS_POCKET_DISTANCE`,
    `OBS_POCKET_CONTACT_SUPPORT`, `OBS_ATOM_COUNT`,
    `OBS_GRAPH_COMPLEXITY`, `OBS_PAIR_ENTROPY`,
    `OBS_PROJECTION_LOSS`, `OBS_MATERIALIZATION_PASS`,
    `OBS_GEOMETRY_PASS`, `OBS_EVALUATOR_PROVENANCE_PRESENT`,
    `OBS_LINEAGE_DETACHED`.
  * Blocker constants: `_BLOCKER_UNCLASSIFIED`, `_BLOCKER_OUT_OF_ENVELOPE`,
    `_BLOCKER_MATERIALIZATION`, `_BLOCKER_GEOMETRY`,
    `_BLOCKER_EVAL_PROVENANCE`, `_BLOCKER_LINEAGE`.
  * Helpers: `_coerce_float`, `_coerce_int`, `_coerce_bool`,
    `_read_observables`, `_within_layer`.
* **Public surface:** none (private to `envelope/`).
* **Why a separate file:** the classifier is a self-contained,
  pure-data function of the bundle observables; isolating it makes
  it independently testable (we want fast tests for "what does
  `_within_layer` do when `pocket_distance` is missing?").

### 2.3 `envelope/tail_budget.py`

* **Lines:** none (empty for now).
* **Purpose:** reserved for the future split of `TailBudgetAccumulator`
  into a tail-budget-only module. The current `accumulator` is
  tightly coupled with `StratifiedTailBudgetRow` (built by
  `stratified_snapshot`); splitting now would require moving
  `record_stratum_excess_mass` and `record_stratified_audit` together
  with it. Hold off until a real second consumer of the accumulator
  (independent of `StratifiedTailBudgetRow`) lands.

### 2.4 `envelope/__init__.py`

Curated surface:

```python
"""Runtime envelope + tail-budget machinery (DTB-NC1 + DTB-L3 partial).

Builders, classifiers, and accumulators only. The contract types
(``EnvelopeLayer``, ``FrozenEnvelopeManifest``, ``EnvelopeClassification``,
``TailBudgetRow``) live in :mod:`adaptive_reflow.contracts.envelope`.
"""
from .manifest import (
    EvidenceRowHash,
    FrozenEnvelopeManifestBuilder,
    ManifestBuildError,
    StratifiedTailBudgetRow,
    TailBudgetAccumulator,
    classify_endpoint,
)
```

---

## 3. Cross-package import rewrites

After the split, the imports inside every other source module must be
rewritten. The canonical mapping is in
`FILE_MAPPING.md §C`. Below is the precise rewrites for the two
split source files' downstream consumers.

### 3.1 Imports of `restart_memory_types` symbols — old → new

| Old | New |
|---|---|
| `from restart_memory_types import RoundResultBundle` | `from adaptive_reflow.contracts import RoundResultBundle` |
| `from restart_memory_types import ChannelTransferEvidence, ChannelTransferDecision` | `from adaptive_reflow.contracts import ChannelTransferEvidence, ChannelTransferDecision` |
| `from restart_memory_types import DynamicRestartTransferLedger` | `from adaptive_reflow.contracts import DynamicRestartTransferLedger` |
| `from restart_memory_types import NoiseBiasInputRow` | `from adaptive_reflow.contracts import NoiseBiasInputRow` |
| `from restart_memory_types import ChannelRuleInputs, ChannelRuleOutputs` | `from adaptive_reflow.contracts import ChannelRuleInputs, ChannelRuleOutputs` |
| `from restart_memory_types import EnvelopeLayer, FrozenEnvelopeManifest, EnvelopeClassification, TailBudgetRow` | `from adaptive_reflow.contracts import EnvelopeLayer, FrozenEnvelopeManifest, EnvelopeClassification, TailBudgetRow` |
| `from restart_memory_types import CosineScheduleConfig, CosineScheduleSample, FreshNoiseFloor, RestartTriggerEvent` | `from adaptive_reflow.contracts import CosineScheduleConfig, CosineScheduleSample, FreshNoiseFloor, RestartTriggerEvent` |
| `from restart_memory_types import PhaseState` | `from adaptive_reflow.contracts import PhaseState` |
| `from restart_memory_types import make_default_phase_state as _make_default_phase_state_from_types` | `from adaptive_reflow.contracts import make_default_phase_state` (or via `adaptive_reflow.frame.make_default_phase_state` for the run_id_seed wrapper) |
| `from restart_memory_types import RestartPolicyAuthorityContract, LegacyCompatibilityWindow, FinalRestartPolicy` | `from adaptive_reflow.contracts import RestartPolicyAuthorityContract, LegacyCompatibilityWindow, FinalRestartPolicy` |
| `from restart_memory_types import OperationCompositionContract, CommutatorResidualDiagnostic, DEFAULT_OPERATION_ORDER` | `from adaptive_reflow.contracts import OperationCompositionContract, CommutatorResidualDiagnostic`; `DEFAULT_OPERATION_ORDER` from `adaptive_reflow.contracts.types` (or `adaptive_reflow.frame.operation`) |
| `from restart_memory_types import ArchiveQuota, ArchiveAuditTrail` | `from adaptive_reflow.contracts import ArchiveQuota, ArchiveAuditTrail` |
| `from restart_memory_types import hash_artifact, hash_bundle_id, hash_trace_digest, hash_phase_state_digest, hash_policy_hash` | `from adaptive_reflow.contracts import hash_artifact, hash_bundle_id, hash_trace_digest, hash_phase_state_digest, hash_policy_hash` |
| `from restart_memory_types import validate_*` | `from adaptive_reflow.contracts import validate_*` |
| `from restart_memory_types import empty_provenance` | `from adaptive_reflow.contracts import empty_provenance` |
| `from restart_memory_types import BundleId, RunId, SampleId, TraceDigest, ...` | `from adaptive_reflow.contracts import BundleId, RunId, SampleId, TraceDigest, ...` |

### 3.2 Imports of `envelope_manifest` symbols — old → new

| Old | New |
|---|---|
| `from envelope_manifest import FrozenEnvelopeManifestBuilder, ManifestBuildError` | `from adaptive_reflow.envelope import FrozenEnvelopeManifestBuilder, ManifestBuildError` |
| `from envelope_manifest import classify_endpoint` | `from adaptive_reflow.envelope import classify_endpoint` |
| `from envelope_manifest import TailBudgetAccumulator, StratifiedTailBudgetRow` | `from adaptive_reflow.envelope import TailBudgetAccumulator, StratifiedTailBudgetRow` |
| `from envelope_manifest import EvidenceRowHash` | `from adaptive_reflow.envelope import EvidenceRowHash` |

---

## 4. Files that *depend on* the split files — list

For review purposes only. The migration step must verify every file
below is updated before the old files are deleted.

### 4.1 Files importing from `restart_memory_types`

```
channel_rule.py
cosine_schedule.py
candidate_archive.py
envelope_manifest.py
flow_matching_engine.py
merge_authority.py
operation_composition.py
phase_state.py
policy_authority.py
policy_orchestrator.py
pruning_gate.py
stratification.py
candidate_registry.py          <- imports nothing directly but is used by audit_template + flowmol3_adapter
audit_template.py
flowmol3_adapter.py
core_runtime_handoff.py         <- imports hash_artifact only
rollback.py                     <- imports hash_artifact only
calibration_protocol.py
evaluation_protocol.py
protocol_manifests.py
claim_gate.py                   <- imports ArtifactHash, FactorValue
promotion.py                    <- imports ClaimGateDecision, hash_artifact, RunId, ArtifactHash
trace_schema.py                 <- imports nothing directly
reference_flowa_adapter.py      <- imports FinalRestartPolicy
synthetic_adapters.py           <- imports FinalRestartPolicy
tests/*.py                      <- many; see FILE_MAPPING.md §B
```

### 4.2 Files importing from `envelope_manifest`

```
policy_orchestrator.py
envelope_manifest.py itself (after split: `envelope/manifest.py`)
tests/*.py
```

---

## 5. Symbol-import table — full list of split-file consumers

This is the complete list of "what each downstream file imports from
`restart_memory_types`", grouped by file. Every entry must be
rewritten to the new import path.

| File | Imported symbols |
|---|---|
| `channel_rule.py` | `ChannelRuleInputs`, `ChannelRuleOutputs`, `ChannelTransferDecision`, `FactorValue` |
| `cosine_schedule.py` | `ArtifactHash`, `BundleId`, `CHANNEL_NAMES`, `ChannelName`, `CosineScheduleConfig`, `CosineScheduleSample`, `FactorValue`, `ProvenanceChain`, `RESTART_TRIGGER_CODES`, `RestartTriggerCode`, `RestartTriggerEvent`, `SCHEDULE_FAMILIES`, `TriggerId`, `hash_artifact` |
| `candidate_archive.py` | `ArchiveAuditTrail`, `ArchiveQuota`, `BundleId`, `FactorValue`, `RoundResultBundle`, `RunId`, `SampleId`, `TraceDigest`, `hash_artifact`, `validate_round_result_bundle` |
| `flow_matching_engine.py` | `FinalRestartPolicy`, `hash_policy_hash` |
| `merge_authority.py` | `ChannelName`, `CosineScheduleSample`, `FactorValue` |
| `operation_composition.py` | `ArtifactHash`, `CommutatorResidualDiagnostic`, `DEFAULT_OPERATION_ORDER`, `OperationCompositionContract`, `TraceDigest`, `hash_artifact` |
| `phase_state.py` | `ArtifactHash`, `PhaseState`, `RestartTriggerEvent`, `SCHEDULE_PHASES`, `hash_phase_state_digest`, `make_default_phase_state` |
| `policy_authority.py` | `ArtifactHash`, `ChannelName`, `CosineScheduleSample`, `DynamicRestartTransferLedger`, `FactorValue`, `FinalRestartPolicy`, `LedgerRowId`, `LegacyCompatibilityWindow`, `MechanismId`, `PolicyId`, `RestartPolicyAuthorityContract`, `RunId`, `hash_artifact`, `hash_policy_hash` |
| `policy_orchestrator.py` | `ArtifactHash`, `ChannelName`, `ChannelTransferDecision`, `ChannelTransferEvidence`, `ChannelRuleInputs`, `CosineScheduleConfig`, `CosineScheduleSample`, `DynamicRestartTransferLedger`, `FactorValue`, `FinalRestartPolicy`, `FrozenEnvelopeManifest`, `LedgerRowId`, `OperationCompositionContract`, `PhaseState`, `RestartPolicyAuthorityContract`, `RoundResultBundle`, `hash_artifact`, `hash_trace_digest`, `validate_channel_evidence`, `validate_phase_state`, `validate_round_result_bundle` |
| `pruning_gate.py` | `ArtifactHash`, `BundleId`, `FactorValue`, `hash_artifact` |
| `stratification.py` | `BundleId`, `FactorValue` |
| `core_runtime_handoff.py` | `hash_artifact` |
| `rollback.py` | `hash_artifact` |
| `calibration_protocol.py` | `ArtifactHash`, `FactorValue`, `ManifestId`, `hash_artifact` |
| `evaluation_protocol.py` | `ArtifactHash`, `FactorValue`, `hash_artifact` |
| `protocol_manifests.py` | `ArtifactHash`, `FactorValue`, `ManifestId` |
| `claim_gate.py` | `ArtifactHash`, `FactorValue` |
| `promotion.py` | `ArtifactHash`, `ClaimGateDecision` (re-export from `claim_gate`), `RunId`, `hash_artifact` |
| `audit_template.py` | `CandidateEntry`, `CandidateRegistry` (re-exports from `candidate_registry`, not directly from `restart_memory_types`) |
| `flowmol3_adapter.py` | (re-exports from `candidate_registry` and `flow_matching_adapter`, not directly) |
| `candidate_registry.py` | (none — fully self-contained) |
| `reference_flowa_adapter.py` | `FinalRestartPolicy` |
| `synthetic_adapters.py` | `FinalRestartPolicy` |
| `trace_schema.py` | (none — fully self-contained) |

### 5.1 All `envelope_manifest` consumers

| File | Imported symbols |
|---|---|
| `policy_orchestrator.py` | `classify_endpoint`, `EnvelopeClassification`, `EnvelopeLayer`, `FrozenEnvelopeManifest`, `ArtifactHash`, `BundleId`, `ComplementBlockerCode`, `FactorValue`, `ManifestId`, `RoundResultBundle`, `TailBudgetRow`, `TailBudgetRowId`, `hash_artifact` |
| `tests/test_*` | Various — see `tests/` imports in the test files. |

---

## 6. `envelope_manifest.py` post-split dependency graph

```
envelope/manifest.py
  -> contracts.envelope  (EnvelopeLayer, FrozenEnvelopeManifest,
                           EnvelopeClassification, TailBudgetRow,
                           validate_envelope_manifest,
                           validate_tail_budget_row)
  -> contracts.bundle    (RoundResultBundle, ArtifactHash, BundleId,
                           FactorValue, ComplementBlockerCode,
                           ManifestId, TailBudgetRowId)
  -> contracts.types     (none directly; via contracts.* re-exports)
  -> contracts.hashes    (hash_artifact)
  -> policy.stratification (Stratum)
```

No cycle. `envelope/manifest.py` is the *only* file in `envelope/` that
imports from `policy/`, and `policy/stratification.py` does not import
from `envelope/`.

---

## 7. Sanity checks before the cut

Before deleting `restart_memory_types.py` and `envelope_manifest.py`:

1. `grep -RE "from \.restart_memory_types|import restart_memory_types"
     adaptive_reflow/` returns zero hits.
2. `grep -RE "from \.envelope_manifest|import envelope_manifest"
     adaptive_reflow/` returns zero hits.
3. `grep -RE "from restart_memory_types|import restart_memory_types"
     tests/` returns zero hits.
4. `grep -RE "from envelope_manifest|import envelope_manifest"
     tests/` returns zero hits.
5. `pytest tests/` reports 362 passing, 0 failing.

If any of (1)–(4) still has hits, the migration is incomplete; do not
proceed to step (5).