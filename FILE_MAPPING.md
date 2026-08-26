# FILE_MAPPING — old → new

**Repo root today (c:/Users/31472/codes/flowa-multistep-reinference/):**
32 flat `.py` modules + `CONTRACTS.md` + `DESIGN_BOUNDARY.md` +
`README.md` + `STATUS.md` + `docs/` + `tests/`.
**Target root:** `adaptive_reflow/` package with 10 subpackages.

This document enumerates every file move, every split, and every
test-file rename. It is the source of truth for the migration; do
not move files in a different order than the one listed here.

Conventions:

* **`legacy/`** — the original file is renamed (not copied verbatim)
  so its presence in the package signals "this is a legacy module".
* **`frame/`** — files keep their original name unless they collide
  with another `frame/*` file.
* **Splits** — the source file's contents are distributed across the
  listed target files. See `SPLIT_NOTES.md` for the per-symbol
  placement and the per-line ranges.

---

## A. Source files (repo root) → target subpackage

### A.1 `adaptive_reflow/contracts/`

| Old file | New file | Notes |
|---|---|---|
| `restart_memory_types.py` (split) | `contracts/types.py` | NewType aliases + literal-set constants. See `SPLIT_NOTES.md` §1. |
| `restart_memory_types.py` (split) | `contracts/hashes.py` | `hash_artifact`, `hash_bundle_id`, `hash_trace_digest`, `hash_phase_state_digest`, `hash_policy_hash`, `_canonical_json`, `_json_default`, `_bundle_identity_payload`, `_sorted_items`. |
| `restart_memory_types.py` (split) | `contracts/validators.py` | `ValidationResult` alias, `_ok`, `_err`, `validate_unit_float`, `validate_unit_factor`, `validate_positive_int`, `validate_nonneg_int`. |
| `restart_memory_types.py` (split) | `contracts/bundle.py` | §1 atomic bundle: `RoundResultBundle`, `ChannelTransferEvidence`, `ChannelTransferDecision`, `DynamicRestartTransferLedger`, `NoiseBiasInputRow`, `ChannelRuleInputs`, `ChannelRuleOutputs`, `validate_round_result_bundle`, `validate_channel_evidence`. |
| `restart_memory_types.py` (split) | `contracts/decision.py` | Reserved for future DTB-R2/R8 decision-shape additions. Empty after the split. |
| `restart_memory_types.py` (split) | `contracts/envelope.py` | §2 envelope: `EnvelopeLayer`, `FrozenEnvelopeManifest`, `EnvelopeClassification`, `TailBudgetRow`, `validate_envelope_manifest`, `validate_tail_budget_row`. |
| `restart_memory_types.py` (split) | `contracts/schedule.py` | §4 cosine schedule: `CosineScheduleConfig`, `CosineScheduleSample`, `FreshNoiseFloor`, `RestartTriggerEvent`. |
| `restart_memory_types.py` (split) | `contracts/phase.py` | §5 phase: `PhaseState`, `make_default_phase_state` factory, `make_default_phase_state_digest`. |
| `restart_memory_types.py` (split) | `contracts/operations.py` | §6 operation order: `OperationCompositionContract`, `CommutatorResidualDiagnostic`, `OPERATION_STEPS`, `DEFAULT_OPERATION_ORDER`. |
| `restart_memory_types.py` (split) | `contracts/authority.py` | §7 writer authority: `RestartPolicyAuthorityContract`, `LegacyCompatibilityWindow`, `FinalRestartPolicy`, `validate_final_restart_policy`. |
| `restart_memory_types.py` (split) | `contracts/archive.py` | §8 archive: `ArchiveQuota`, `ArchiveAuditTrail`, `validate_archive_quota`. |

### A.2 `adaptive_reflow/envelope/`

| Old file | New file | Notes |
|---|---|---|
| `envelope_manifest.py` (split) | `envelope/manifest.py` | `FrozenEnvelopeManifestBuilder`, `ManifestBuildError`, `classify_endpoint`, `TailBudgetAccumulator`, `StratifiedTailBudgetRow`. |
| `envelope_manifest.py` (split) | `envelope/classifier.py` | Observable extraction (`_read_observables`, `_coerce_*` helpers), `_within_layer`, `_classify_blocker`, and the `OBS_*` key constants. |
| `envelope_manifest.py` (split) | `envelope/tail_budget.py` | Reserved for future tail-budget-only moves; currently contains only `EvidenceRowHash` (moved from `envelope_manifest.py`'s NewType section). |

### A.3 `adaptive_reflow/frame/`

| Old file | New file | Notes |
|---|---|---|
| `flow_matching_adapter.py` | `frame/adapter.py` | Unchanged. The Protocol + carriers stay together. |
| `flow_matching_engine.py` | `frame/engine.py` | Unchanged. The engine + `EngineRoundResult` + engine-local `PhaseState` / `RoundTrace` / `LedgerRow` stay together. |
| `merge_authority.py` | `frame/merge.py` | Unchanged. |
| `operation_composition.py` | `frame/operation.py` | Unchanged. |
| `channel_rule.py` | `frame/channel_rule.py` | Renamed in import path; contents unchanged. |
| `phase_state.py` | `frame/phase.py` | Unchanged. (The runtime helpers land here; the contract `PhaseState` is in `contracts/phase.py`.) |
| `trace_schema.py` | `frame/trace.py` | Renamed in import path; contents unchanged. |
| `policy_orchestrator.py` | `frame/orchestrator.py` | Renamed in import path; contents unchanged. |

### A.4 `adaptive_reflow/policy/`

| Old file | New file | Notes |
|---|---|---|
| `candidate_archive.py` | `policy/archive.py` | Renamed in import path; contents unchanged. |
| `stratification.py` | `policy/stratification.py` | Renamed in import path; contents unchanged. |
| `pruning_gate.py` | `policy/pruning.py` | Renamed in import path; contents unchanged. |
| `noise_mass_accounting.py` | `policy/noise_mass.py` | Renamed in import path; contents unchanged. |

### A.5 `adaptive_reflow/schedule/`

| Old file | New file | Notes |
|---|---|---|
| `cosine_schedule.py` | `schedule/cosine.py` | Renamed in import path; contents unchanged. |

### A.6 `adaptive_reflow/diagnostics/`

| Old file | New file | Notes |
|---|---|---|
| `diagnostic_ledger.py` | `diagnostics/ledger.py` | Renamed in import path; contents unchanged. |

### A.7 `adaptive_reflow/writer/`

| Old file | New file | Notes |
|---|---|---|
| `policy_authority.py` | `writer/authority.py` | Renamed in import path; contents unchanged. |
| `core_runtime_handoff.py` | `writer/handoff.py` | Renamed in import path; contents unchanged. |
| `candidate_registry.py` | `writer/registry.py` | Renamed in import path; contents unchanged. |
| `audit_template.py` | `writer/audit.py` | Renamed in import path; contents unchanged. |

### A.8 `adaptive_reflow/adapters/`

| Old file | New file | Notes |
|---|---|---|
| `reference_flowa_adapter.py` | `adapters/reference_flowa.py` | Renamed in import path; contents unchanged. |
| `flowmol3_adapter.py` | `adapters/flowmol3.py` | Renamed in import path; contents unchanged. |
| `synthetic_adapters.py` | `adapters/synthetic.py` | Renamed in import path; contents unchanged. |

### A.9 `adaptive_reflow/eval/`

| Old file | New file | Notes |
|---|---|---|
| `calibration_protocol.py` | `eval/calibration.py` | Renamed in import path; contents unchanged. |
| `evaluation_protocol.py` | `eval/protocol.py` | Renamed in import path; contents unchanged. |
| `protocol_manifests.py` | `eval/manifests.py` | Renamed in import path; contents unchanged. |
| `claim_gate.py` | `eval/claim_gate.py` | Renamed in import path; contents unchanged. |
| `promotion.py` | `eval/promotion.py` | Renamed in import path; contents unchanged. |
| `rollback.py` | `eval/rollback.py` | Renamed in import path; contents unchanged. |
| `layered_metric_panel.py` | `eval/metric_panel.py` | Renamed in import path; contents unchanged. |

### A.10 `adaptive_reflow/legacy/`

| Old file | New file | Notes |
|---|---|---|
| `control_policy.py` | `legacy/control_policy.py` | Renamed in import path; contents unchanged. |
| `external_metric_feedback.py` | `legacy/metric_feedback.py` | Renamed to drop `external_` prefix; contents unchanged. |
| `orchestration.py` | `legacy/orchestration.py` | Unchanged. |
| `restart_memory.py` | `legacy/restart_mixer.py` | Renamed to reflect that the module is the torch-bound mixer. Contents unchanged. |
| `reinference_plan.py` | `legacy/plan.py` | Renamed; contents unchanged. |
| `loop.py` | `legacy/loop.py` | Unchanged. |
| `loop_contract.py` | `legacy/loop_contract.py` | Unchanged. |
| `mechanism_adapter.py` | `legacy/mechanism_adapter.py` | Unchanged. |
| `services.py` | `legacy/services.py` | Unchanged. |

### A.11 Module files that **stay at the repo root**

| Old file | Stays where? | Notes |
|---|---|---|
| `CONTRACTS.md` | repo root | Already top-level documentation. The package layout does not move it. |
| `DESIGN_BOUNDARY.md` | repo root | Same. |
| `README.md` | repo root | Same. |
| `STATUS.md` | repo root | Same. |
| `todo.json` | repo root | Same. |
| `docs/` | repo root | Same. |

---

## B. Test files (`tests/`) → mirrored subpackages

Tests follow the source layout; one test file per source module, plus
shared fixtures.

### B.1 Direct module-to-test mapping

| Test file (today) | New test file (target) |
|---|---|
| `tests/test_calibration_protocol.py` | `tests/test_eval/test_calibration.py` |
| `tests/test_candidate_archive.py` | `tests/test_policy/test_archive.py` |
| `tests/test_candidate_registry.py` | `tests/test_writer/test_registry.py` |
| `tests/test_claim_gate.py` | `tests/test_eval/test_claim_gate.py` |
| `tests/test_diagnostic_ledger.py` | `tests/test_diagnostics/test_ledger.py` |
| `tests/test_evaluation_protocol.py` | `tests/test_eval/test_protocol.py` |
| `tests/test_flow_matching_engine.py` | `tests/test_frame/test_engine.py` |
| `tests/test_merge_authority_bounded.py` | `tests/test_frame/test_merge.py` |
| `tests/test_stratification_and_pruning.py` | `tests/test_policy/test_stratification_and_pruning.py` |
| `tests/test_trace_schema_v3.py` | `tests/test_frame/test_trace.py` |

### B.2 Test files that need to be added (none today)

No new test files are required by the move; the existing 11 test files
+ `conftest.py` cover the move. New tests for the split
`restart_memory_types.py` symbols land in `tests/test_contracts/`,
split per the contracts split:

| New test file | Covers |
|---|---|
| `tests/test_contracts/test_bundle.py` | `RoundResultBundle`, `ChannelTransferEvidence`, `ChannelTransferDecision`, `DynamicRestartTransferLedger`, `NoiseBiasInputRow`, `ChannelRuleInputs`, `ChannelRuleOutputs` |
| `tests/test_contracts/test_envelope.py` | `EnvelopeLayer`, `FrozenEnvelopeManifest`, `EnvelopeClassification`, `TailBudgetRow` |
| `tests/test_contracts/test_schedule.py` | `CosineScheduleConfig`, `CosineScheduleSample`, `FreshNoiseFloor`, `RestartTriggerEvent` |
| `tests/test_contracts/test_phase.py` | `PhaseState` factory + digest round-trip |
| `tests/test_contracts/test_operations.py` | `OperationCompositionContract`, `CommutatorResidualDiagnostic` |
| `tests/test_contracts/test_authority.py` | `RestartPolicyAuthorityContract`, `LegacyCompatibilityWindow`, `FinalRestartPolicy` |
| `tests/test_contracts/test_archive.py` | `ArchiveQuota`, `ArchiveAuditTrail` |
| `tests/test_contracts/test_hashes.py` | `hash_artifact`, `hash_bundle_id`, `hash_trace_digest`, `hash_phase_state_digest`, `hash_policy_hash` |
| `tests/test_contracts/test_validators.py` | `validate_unit_factor`, `validate_positive_int`, `validate_nonneg_int`, `validate_round_result_bundle`, `validate_channel_evidence`, `validate_envelope_manifest`, `validate_tail_budget_row`, `validate_phase_state`, `validate_final_restart_policy`, `validate_archive_quota` |
| `tests/test_contracts/test_types.py` | NewType aliases + literal-set constants (mostly parametrized) |

### B.3 `tests/conftest.py` adjustments

* The package-context bootstrap (`_ensure_package_context`) becomes
  *simpler*: tests now `import adaptive_reflow` directly, and pytest
  collects them as `tests/test_<subpackage>/test_<file>.py`. The
  synthetic-package fallback path is removed.
* The repo no longer has top-level `.py` files that pytest would
  auto-collect as modules, so the `_alias_top_level` indirection is
  removed.
* The `_REPO_ROOT / _POCKET_MODULES_ROOT` walk is kept (so the legacy
  tests still find `pocket_modules` ancestors), but only the legacy
  tests use it.

---

## C. Imports — old → new

Below is the canonical rename for every public import. Test files and
external callers must use the new path.

### C.1 Old → new (one-to-one renames)

| Old import | New import |
|---|---|
| `from restart_memory_types import RoundResultBundle, ...` | `from adaptive_reflow.contracts import RoundResultBundle, ...` |
| `from envelope_manifest import FrozenEnvelopeManifestBuilder, ...` | `from adaptive_reflow.envelope import FrozenEnvelopeManifestBuilder, ...` |
| `from channel_rule import compute_channel_decision` | `from adaptive_reflow.frame import compute_channel_decision` |
| `from flow_matching_adapter import FlowMatchingODEAdapter` | `from adaptive_reflow.frame import FlowMatchingODEAdapter` |
| `from flow_matching_engine import Engine, EngineRoundResult` | `from adaptive_reflow.frame import Engine, EngineRoundResult` |
| `from merge_authority import bounded_merge, MergeAuthorityError` | `from adaptive_reflow.frame import bounded_merge, MergeAuthorityError` |
| `from operation_composition import build_default_composition_contract` | `from adaptive_reflow.frame import build_default_composition_contract` |
| `from phase_state import build_phase_state, advance_phase` | `from adaptive_reflow.frame import build_phase_state, advance_phase` |
| `from trace_schema import RoundTraceV3, freeze_round_trace_v3` | `from adaptive_reflow.frame import RoundTraceV3, freeze_round_trace_v3` |
| `from policy_orchestrator import AdaptiveReflowPolicyOrchestrator` | `from adaptive_reflow.frame import AdaptiveReflowPolicyOrchestrator` |
| `from candidate_archive import SameSampleArchive` | `from adaptive_reflow.policy import SameSampleArchive` |
| `from stratification import Stratum, dominance_ratio` | `from adaptive_reflow.policy import Stratum, dominance_ratio` |
| `from pruning_gate import PruneGate, UnorderedAuditResult` | `from adaptive_reflow.policy import PruneGate, UnorderedAuditResult` |
| `from noise_mass_accounting import physical_noise_proxy, ...` | `from adaptive_reflow.policy import physical_noise_proxy, ...` |
| `from cosine_schedule import CosineScheduleSampler, n_cap_for_round` | `from adaptive_reflow.schedule import CosineScheduleSampler, n_cap_for_round` |
| `from diagnostic_ledger import FreshNoiseCumulativeMassRecord, ...` | `from adaptive_reflow.diagnostics import FreshNoiseCumulativeMassRecord, ...` |
| `from policy_authority import WriterArbitrator, build_final_restart_policy` | `from adaptive_reflow.writer import WriterArbitrator, build_final_restart_policy` |
| `from core_runtime_handoff import build_core_runtime_handoff` | `from adaptive_reflow.writer import build_core_runtime_handoff` |
| `from candidate_registry import CandidateEntry, CandidateRegistry` | `from adaptive_reflow.writer import CandidateEntry, CandidateRegistry` |
| `from audit_template import AuditTemplate, validate_audit_completeness` | `from adaptive_reflow.writer import AuditTemplate, validate_audit_completeness` |
| `from reference_flowa_adapter import ReferenceFlowAAdapter` | `from adaptive_reflow.adapters import ReferenceFlowAAdapter` |
| `from flowmol3_adapter import FlowMol3Adapter, default_flowmol3_adapter` | `from adaptive_reflow.adapters import FlowMol3Adapter, default_flowmol3_adapter` |
| `from synthetic_adapters import SyntheticContinuousAdapter, ...` | `from adaptive_reflow.adapters import SyntheticContinuousAdapter, ...` |
| `from calibration_protocol import wilson_lower_bound, beta_lower_bound` | `from adaptive_reflow.eval import wilson_lower_bound, beta_lower_bound` |
| `from evaluation_protocol import PairedComparisonArm, ...` | `from adaptive_reflow.eval import PairedComparisonArm, ...` |
| `from protocol_manifests import write_calibration_manifest, ...` | `from adaptive_reflow.eval import write_calibration_manifest, ...` |
| `from claim_gate import evaluate_claim_gate, ClaimGateConfig` | `from adaptive_reflow.eval import evaluate_claim_gate, ClaimGateConfig` |
| `from promotion import build_deferred_promotion_report` | `from adaptive_reflow.eval import build_deferred_promotion_report` |
| `from rollback import apply_rollback, build_disabled_rollback_flag` | `from adaptive_reflow.eval import apply_rollback, build_disabled_rollback_flag` |
| `from layered_metric_panel import LayeredMetricPanel` | `from adaptive_reflow.eval import LayeredMetricPanel` |
| `from control_policy import adaptive_reflow_external_metric_controls` | `from adaptive_reflow.legacy import adaptive_reflow_external_metric_controls` (DeprecationWarning) |
| `from external_metric_feedback import ...` | `from adaptive_reflow.legacy import ...` (DeprecationWarning; renamed module is `metric_feedback.py`) |
| `from orchestration import ...` | `from adaptive_reflow.legacy import ...` |
| `from restart_memory import adaptive_reflow_memory_restart_coords` | `from adaptive_reflow.legacy import adaptive_reflow_memory_restart_coords` |
| `from reinference_plan import ...` | `from adaptive_reflow.legacy import ...` |
| `from loop import build_loop_contract` | `from adaptive_reflow.legacy import build_loop_contract` |
| `from loop_contract import run_local_loop` | `from adaptive_reflow.legacy import run_local_loop` |
| `from mechanism_adapter import AdaptiveReflowMechanism` | `from adaptive_reflow.legacy import AdaptiveReflowMechanism` |
| `from services import available_services` | `from adaptive_reflow.legacy import available_services` |

### C.2 Cross-package relocations

The following symbols move *between* subpackages (not just renamed in
place). Both old and new imports must work during the migration
window; only the new import is canonical after the move.

| Symbol | Old location | New location |
|---|---|---|
| `make_default_phase_state` | `restart_memory_types.make_default_phase_state` | `adaptive_reflow.contracts.phase.make_default_phase_state` (the factory stays with the contract). `frame.phase.make_default_phase_state` (the `run_id_seed`-taking convenience wrapper) is renamed `make_default_phase_state` at the package surface and exposed via `frame.phase`. The two are distinct symbols: the contracts one is the factory; the frame one is the runner. |

### C.3 Conftest update (rough sketch — not code, just the change)

* Remove `_PKG_NAME = "adaptive_reflow"`; tests use the real package.
* Remove `_alias_top_level` (no more bare-name aliases).
* Keep the `pocket_modules` ancestor walk — the *legacy* tests still
  need it. Add a marker (`@pytest.mark.legacy`) so the legacy tests
  are gated on the ancestor walk succeeding.

---

## D. Migration order (preserves 362 passing tests)

1. **Stage 1 — create empty subpackages.** Create the 10 subpackages
   with empty `__init__.py` files. No source files move yet; the
   32 flat modules keep working.
2. **Stage 2 — add new modules alongside the old.** Each new file
   (`adaptive_reflow/frame/adapter.py`, etc.) is created as a verbatim
   copy of the old file with corrected imports (`from
   restart_memory_types import …` → `from adaptive_reflow.contracts
   import …`). Tests still import from the old flat root, so they
   continue to pass.
3. **Stage 3 — split `restart_memory_types.py`.** Implement
   `adaptive_reflow/contracts/{types,hashes,validators,bundle,
   decision,envelope,schedule,phase,operations,authority,archive}.py`
   per `SPLIT_NOTES.md`. Tests for the split bits are added
   under `tests/test_contracts/`.
4. **Stage 4 — split `envelope_manifest.py`.** Implement
   `adaptive_reflow/envelope/{manifest,classifier,tail_budget}.py`.
5. **Stage 5 — point the old modules at the new package.** Replace
   each old flat module's body with re-exports from
   `adaptive_reflow.*`. The 11 test files continue to import from the
   flat root, so they still pass.
6. **Stage 6 — update test imports.** Update each test file's imports
   to point at `adaptive_reflow.*`. Run tests after every file
   change.
7. **Stage 7 — delete the old flat modules.** Run the full 362-test
   suite; expect zero regressions.

The new-package files should be reviewed and (if necessary) tidied
before Stage 7. Splits that produce near-verbatim copies (most of
`frame/*`, `policy/*`, `eval/*`, etc.) need no code change; splits of
`restart_memory_types.py` and `envelope_manifest.py` need the line
ranges from `SPLIT_NOTES.md` and the import-rewrite pass.