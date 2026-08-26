# UNIVERSAL ↔ MOLECULAR MAPPING

**Status:** Planning document only. No source files modified.
**Companion to:** `REFACTOR_PLAN_V2.md`, `UNIVERSAL_CONTRACT_NOTES.md`.

This file enumerates every current source module under
`adaptive_reflow/` and specifies its destination after the universal /
molecular split. Destination codes:

| Code | Meaning |
|---|---|
| **U** | Moves to `adaptive_reflow/universal/` (model-family-agnostic core). |
| **M** | Moves to `adaptive_reflow/molecular/` (concrete molecule implementation). |
| **K** | Stays in its current subpackage (`contracts/`, `frame/`, `policy/`, `schedule/`, `diagnostics/`, `writer/`, `adapters/`, `eval/`); may be edited in place. |
| **L** | Stays in `adaptive_reflow/legacy/` for one more release; eventually moves to `molecular/`. |
| **S** | Splits: part stays in the current subpackage, part moves to `universal/` or `molecular/`. |
| **R** | Becomes a thin re-export shim of the new canonical home. |

A "move" is additive in this phase — the legacy path is duplicated with
a back-compat re-export so the 362-test suite keeps passing.

---

## 1. `adaptive_reflow/contracts/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `contracts/__init__.py` | **R** | `contracts/__init__.py` (re-exports from `universal/state.py` + `molecular/bundle.py`) | After split, `contracts` re-exports the universal carriers and molecule-specific extensions. |
| `contracts/types.py` | **S** | `contracts/types.py` (universal aliases only) + `molecular/channels.py` (molecule channel aliases) | The four `*ChannelRef` NewType aliases move to `molecular/channels.py`. `CHANNEL_NAMES` literal set moves to `molecular/channels.py::MOLECULE_CHANNELS`. New `ChannelRef = NewType("ChannelRef", Mapping[str, Any])` stays in `contracts/types.py`. |
| `contracts/archive.py` | **K** | `contracts/archive.py` | DTB-R4 `ArchiveQuota`, `ArchiveAuditTrail`, `validate_archive_quota` are already universal. |
| `contracts/authority.py` | **K** | `contracts/authority.py` | DTB-S1 authority contract is already universal (mechanism ids are strings). |
| `contracts/bundle.py` | **S** | `contracts/bundle.py` (universal `RoundResultBundle` without molecule channel fields) + `molecular/bundle.py` (extension with four molecule channel refs) | `RoundResultBundle` keeps `bundle_id`, `source_round`, `round_count`, `run_id`, `sample_id`, `trace_digest`, `condition_digest`, `feedback_mode`, `calibration_artifact_hash`, `state_lock_is_detached`, `update_scope`, `materialization_evidence`, `evaluator_provenance`, `feedback_evidence`, `shape_spec`, `frame_spec`, `provenance`, `created_at_round`, `revoked`. The four `coordinate_channel / charge_channel / raw_pair_channel / projected_pair_channel` fields move to `molecular/bundle.py::MoleculeRoundResultBundle`. `validate_round_result_bundle` stops checking the four molecule channels' `source_round`; that check moves to `validate_molecule_round_result_bundle`. |
| `contracts/decision.py` | **K** | `contracts/decision.py` | Reserved for future use; unchanged. |
| `contracts/envelope.py` | **M** | `molecular/envelope.py` | `EnvelopeLayer`, `FrozenEnvelopeManifest`, `EnvelopeClassification`, `TailBudgetRow` are 100% molecule-specific. `validate_envelope_manifest` + `validate_tail_budget_row` move with them. The universal `EnvelopeCriterion` Protocol lives in `universal/envelope.py` (new). |
| `contracts/hashes.py` | **K** | `contracts/hashes.py` | sha256 helpers are pure / universal. |
| `contracts/operations.py` | **K** | `contracts/operations.py` | DTB-L2 `OperationCompositionContract`, `CommutatorResidualDiagnostic` are model-family-agnostic. |
| `contracts/phase.py` | **K** | `contracts/phase.py` | DTB-L1 `PhaseState` + factory + digest round-trip are universal. |
| `contracts/schedule.py` | **K** | `contracts/schedule.py` | DTB-NA1 schedule types are universal (schedule families are closed literals; channels are per-adapter). |
| `contracts/validators.py` | **K** | `contracts/validators.py` | `ValidationResult`, `validate_unit_factor`, `validate_positive_int`, etc. are universal. `universal/validators.py` re-exports them. |

---

## 2. `adaptive_reflow/frame/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `frame/__init__.py` | **R** | `frame/__init__.py` | Re-exports `Engine`, `FlowMatchingODEAdapter`, `StateBundle`, etc. from `frame/` + `universal/` so existing imports keep working. |
| `frame/adapter.py` | **S** | `frame/adapter.py` (thin re-export from `universal/state.py` + `universal/adapter.py`) | `FlowMatchingODEAdapter` Protocol, `AdapterCapabilities`, `TensorRef`, `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace` move to `universal/`. `frame/adapter.py` re-exports them for back-compat. The four `FlowMatchingODEAdapter` method signatures do not change. `DOMAIN_BY_CHANNEL` constant is **removed**; its function is replaced by `AdapterCapabilities.supported_channels` (already per-adapter). |
| `frame/channel_rule.py` | **K** | `frame/channel_rule.py` | DTB-R2 `compute_channel_decision`, `check_monotonicity_property`, blocker codes, `CANONICAL_FACTOR_ORDER` are universal — the six factors and the `evidence_score` formula do not assume a channel kind. The rule's `ChannelRuleInputs` consumes `ChannelTransferEvidence`, which is universal. |
| `frame/engine.py` | **K** | `frame/engine.py` | DTB-G1 `Engine`, `EngineRoundResult`, `RoundTrace`, `LedgerRow`, `PhaseState` (engine-local) are universal. The `Engine.handshake` capability list drops `DOMAIN_BY_CHANNEL` and uses `caps.supported_channels` directly. |
| `frame/merge.py` | **K** | `frame/merge.py` | DTB-R3 `bounded_merge`, `bounded_merge_with_schedule`, `MergeAuthorityError`, schema constants are universal — the bounded update is a closed-form [0,1] arithmetic rule. |
| `frame/operation.py` | **K** | `frame/operation.py` | DTB-L2 `build_default_composition_contract`, `validate_operation_order`, `record_commutator_residual`, `replay_default_order` are universal. |
| `frame/orchestrator.py` | **K** | `frame/orchestrator.py` | DTB-S1 `AdaptiveReflowPolicyOrchestrator` is universal; the mechanism id is a string. |
| `frame/phase.py` | **K** | `frame/phase.py` | DTB-L1 runtime phase helpers are universal. |
| `frame/trace.py` | **K** | `frame/trace.py` | DTB-R5 `RoundTraceV3` + v2 reader + content hash + freeze + round_trip are universal. |

---

## 3. `adaptive_reflow/policy/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `policy/__init__.py` | **R** | `policy/__init__.py` | Re-exports `Stratum`, `StratumAssignment`, `dominance_ratio`, `cross_stratum_mix_rejected` from `molecular/stratification.py` so existing tests that import from `policy.stratification` keep working. |
| `policy/archive.py` | **K** | `policy/archive.py` | DTB-R4 `SameSampleArchive`, `ArchiveEntry`, error family are universal (the archive key is a `BundleId`; the entry is a `Mapping[str, Any]`). |
| `policy/noise_mass.py` | **K** | `policy/noise_mass.py` | DTB-L4 `physical_noise_proxy`, `RMS_preserving_mixing_coefficient`, `exact_spectral_variance`, `ThreeWayDistinction`, `adversarial_stagnation_test` are universal — they are pure math / statistics, not molecule-aware. |
| `policy/pruning.py` | **K** | `policy/pruning.py` | DTB-L3 `PruneGate`, `UnorderedAuditResult`, `PruneDecision` consume `StratumAssignment` (which now lives in `molecular/stratification.py`). The pruning logic itself is universal; it only depends on `score_gap` and `calibrated_error`. |
| `policy/stratification.py` | **M** | `molecular/stratification.py` | `Stratum`, `StratumAssignment`, `dominance_ratio`, `cross_stratum_mix_rejected` move to `molecular/`. `policy/stratification.py` becomes a re-export shim. `Stratum` is closed (`GEOMETRY`/`CHARGE`/`PAIR`/`MATERIALIZATION`/`LINEAGE`); a non-molecular flow model that wants stratification must declare its own closed enum and the gate remains usable because the ratio + audit only depend on numeric `score_gap` / `calibrated_error`. |

---

## 4. `adaptive_reflow/schedule/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `schedule/__init__.py` | **K** | `schedule/__init__.py` | Unchanged. |
| `schedule/cosine.py` | **K** | `schedule/cosine.py` | DTB-NA1 `CosineScheduleSampler`, `n_cap_for_round`, validators, `default_floor_by_channel` are universal — channels are referenced by name, not by molecule kind. The `CHANNEL_NAMES` literal it currently reads is replaced by `molecular.MOLECULE_CHANNELS` (or whatever the caller supplies via the schedule config). |

---

## 5. `adaptive_reflow/diagnostics/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `diagnostics/__init__.py` | **K** | `diagnostics/__init__.py` | Unchanged. |
| `diagnostics/ledger.py` | **K** | `diagnostics/ledger.py` | DTB-L4 observation-only ledger rows are universal; they observe schedule outputs and have no molecule vocabulary. |

---

## 6. `adaptive_reflow/writer/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `writer/__init__.py` | **K** | `writer/__init__.py` | Unchanged. |
| `writer/audit.py` | **K** | `writer/audit.py` | DTB-G2 audit template is universal. |
| `writer/authority.py` | **K** | `writer/authority.py` | DTB-S1 `WriterArbitrator`, `build_default_authority_contract`, `build_final_restart_policy`, `verify_policy_against_ledger` are universal — they reference `MechanismId` strings. |
| `writer/handoff.py` | **K** | `writer/handoff.py` | DTB-R3 `CoreRuntimeHandoff` is universal. |
| `writer/registry.py` | **K** | `writer/registry.py` | DTB-G2 `CandidateEntry`, `CandidateRegistry`, `make_initial_registry`, `admit_entry`, `default_registry`, `FLOWMOL3_PINNED_COMMIT`. The `TaskCondition` Literal gains a `"lattice_conditioned"` and `"graph_conditioned"` value but is otherwise unchanged — molecules still use `"pocket_conditioned"`. |

---

## 7. `adaptive_reflow/adapters/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `adapters/__init__.py` | **K** | `adapters/__init__.py` | Unchanged. |
| `adapters/flowmol3.py` | **K** | `adapters/flowmol3.py` | `FlowMol3Adapter` continues to advertise the molecule channels via `AdapterCapabilities.supported_channels = FLOWMOL3_CHANNELS`. `FLOWMOL3_CHANNELS` becomes a re-export of `molecular.MOLECULE_CHANNELS`. |
| `adapters/reference_flowa.py` | **K** | `adapters/reference_flowa.py` | `ReferenceFlowAAdapter` already advertises molecule channels. Unchanged. |
| `adapters/synthetic.py` | **K** | `adapters/synthetic.py` | `SyntheticContinuousAdapter`, `SyntheticDiscreteAdapter`, `SyntheticMixedChannelAdapter`, `SyntheticUnsupportedAdapter` are already channel-set agnostic; they work on the generic `Mapping[str, TensorRef]`. The `CONTINUOUS_CHANNELS / DISCRETE_CHANNELS / MIXED_CHANNELS / ALL_SYNTHETIC_CHANNELS` literals stay. |

---

## 8. `adaptive_reflow/eval/` (split)

| File | Status | Destination | Notes |
|---|---|---|---|
| `eval/__init__.py` | **S** | `eval/__init__.py` (universal exports) + `molecular/calibration_targets.py` (molecule metric literals) | Re-exports from `wilson.py` + `beta.py` + `manifest.py` + `claim_gate.py` + `promotion.py` + `rollback.py` + `metric_panel.py` + `protocol.py`. |
| `eval/calibration.py` | **S** | `eval/wilson.py` (Wilson math only) + `eval/beta.py` (Beta math only) + `eval/manifest.py` (`CalibrationBucket` / `CalibrationManifest` / `CalibrationTimeSplit` / `StabilityPerturbationProtocol` / `manifest_digest` / `classify_bucket`) + `molecular/calibration_targets.py` (`MOLECULE_CALIBRATION_TARGETS` / `MOLECULE_CHANNEL_TO_METRIC`) | The literal sets `CHANNEL_NAMES_FOR_CALIBRATION` and `PREDECLARED_SAFETY_METRICS` move to `molecular/calibration_targets.py`. The math (`wilson_lower_bound`, `beta_lower_bound`) is universal. The `CalibrationBucket.channel` / `CalibrationManifest.per_metric_buckets` field names stay as `str`; the channel *value* is whatever the molecule / model family declares. |
| `eval/claim_gate.py` | **K** | `eval/claim_gate.py` | DTB-R8 claim gate is universal. |
| `eval/manifests.py` | **K** | `eval/manifest.py` | Renamed (avoid clash with future `eval/manifests/` directory). JSON serialisation for `CalibrationManifest` + `validate_manifest_frozen` + `frozen_manifest_hash`. Universal — the placeholder deferred-GPU fields stay. |
| `eval/metric_panel.py` | **K** | `eval/metric_panel.py` | DTB-R8 `LayeredMetricPanel` + `enforce_separation` + `build_default_layered_metric_panel` are universal. The tier labels (`raw_generation`, `adaptive_reflow`, `postprocess_assisted`) are not molecule-specific; they describe how metrics enter the report. |
| `eval/promotion.py` | **K** | `eval/promotion.py` | DTB-R8 `PromotionReport` + `PolicyVersionHashRecorder` + `build_deferred_promotion_report` + `derive_policy_hash_from_version` are universal. |
| `eval/protocol.py` | **K** | `eval/protocol.py` | DTB-R7 `PairedComparisonArm` + `PairedComparisonRegistry` + `EvaluatorProvenanceGuard` + `evaluator_guard_digest` + `RoundToRoundOscillationDetector` are universal. The `TargetPocketHash` NewType is renamed to `TargetConditionHash` and documented as model-family-agnostic (the *kind* of condition — pocket, lattice, sequence, etc. — is per-task). |
| `eval/rollback.py` | **K** | `eval/rollback.py` | DTB-R8 `RollbackFlag` + `RollbackAudit` + `apply_rollback` + `build_disabled_rollback_flag` are universal. |

---

## 9. `adaptive_reflow/legacy/`

| File | Status | Destination | Notes |
|---|---|---|---|
| `legacy/__init__.py` | **K** | `legacy/__init__.py` | Empty `__all__`; emits `DeprecationWarning`. |
| `legacy/control_policy.py` | **L** | `legacy/control_policy.py` | Quarantined torch-bound control policy. No change in this phase. |
| `legacy/loop.py` | **L** | `legacy/loop.py` | Quarantined. No change. |
| `legacy/loop_contract.py` | **L** | `legacy/loop_contract.py` | Quarantined. No change. |
| `legacy/mechanism_adapter.py` | **L** | `legacy/mechanism_adapter.py` | Quarantined. No change. |
| `legacy/metric_feedback.py` | **L** | `legacy/metric_feedback.py` | Quarantined `external_metric_feedback.py` rename. No change. |
| `legacy/orchestration.py` | **L** | `legacy/orchestration.py` | Quarantined. No change. |
| `legacy/plan.py` | **L** | `legacy/plan.py` | Quarantined `reinference_plan.py` rename. No change. |
| `legacy/restart_mixer.py` | **S** | `legacy/restart_mixer.py` (re-export from `molecular/legacy_mixer.py`) | The current `adaptive_reflow_memory_restart_coords` function moves to `molecular/legacy_mixer.py`. `legacy/restart_mixer.py` becomes a re-export shim that warns on import. |
| `legacy/services.py` | **L** | `legacy/services.py` | Quarantined. No change. |

---

## 10. `adaptive_reflow/universal/` (new)

| File | Status | Source of truth | Notes |
|---|---|---|---|
| `universal/__init__.py` | **NEW** | — | Re-exports the universal public surface: `TensorRef`, `StateBundle`, `AdapterCapabilities`, `ODEConditionDelta`, `ODEIntegratorTrace`, `FlowMatchingODEAdapter`, `RestartMixer`, `Evaluator`, `EnvelopeCriterion`, `ValidationResult`, `validate_*` helpers. |
| `universal/state.py` | **NEW** | ← `frame/adapter.py` (carriers only) | `TensorRef`, `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace`, validators. No molecule fields. |
| `universal/adapter.py` | **NEW** | ← `frame/adapter.py` (Protocol + capabilities) | `FlowMatchingODEAdapter` Protocol, `AdapterCapabilities`, `CapabilityMissingError`, `CapabilityMismatchError`. The `DOMAIN_BY_CHANNEL` constant is **removed**; per-adapter domain resolution is the adapter's own responsibility (advertised via `supported_channels`). |
| `universal/envelope.py` | **NEW** | — | `EnvelopeCriterion` Protocol + `EnvelopeClassification` universal base (carries only `bundle_id`, `within_layer_thresholds`, `complement_blocker`, `matched_layer_index`; no molecule-specific residual_extents). |
| `universal/evaluator.py` | **NEW** | — | `Evaluator` Protocol: `evaluate(*, sample: Mapping[str, Any]) -> tuple[float, Mapping[str, float]]`. No GNINA / QED / ADMET assumptions. |
| `universal/mixer.py` | **NEW** | — | `RestartMixer` Protocol: `mix(*, prior: Any, memory: Any, beta: float, jitter_fraction: float = 0.0) -> tuple[Any, Mapping[str, Any]]`. |
| `universal/validators.py` | **NEW** | ← `contracts/validators.py` (re-export) | Re-exports `ValidationResult`, `validate_unit_factor`, `validate_positive_int`, `validate_nonneg_int`, `validate_unit_float`. |

---

## 11. `adaptive_reflow/molecular/` (new)

| File | Status | Source of truth | Notes |
|---|---|---|---|
| `molecular/__init__.py` | **NEW** | — | Re-exports the molecule public surface: `MOLECULE_CHANNELS`, `MOLECULE_DOMAIN_BY_CHANNEL`, `MOLECULE_CALIBRATION_TARGETS`, `MOLECULE_CHANNEL_TO_METRIC`, `CoordinateChannelRef`, `ChargeChannelRef`, `RawPairChannelRef`, `ProjectedPairChannelRef`, `MoleculeRoundResultBundle`, `MoleculeEnvelopeLayer`, `MoleculeEnvelopeManifest`, `MoleculeEnvelopeClassification`, `MoleculeTailBudgetRow`, `MoleculeStratum`, `MoleculeStratumAssignment`, `RMSPreservingCoordinateMixer`, `adaptive_reflow_memory_restart_coords` (back-compat alias). |
| `molecular/channels.py` | **NEW** | ← `contracts/types.py` (channel aliases) | `MOLECULE_CHANNELS = ("coordinate", "charge", "raw_pair", "projected_pair")`, `CoordinateChannelRef`, `ChargeChannelRef`, `RawPairChannelRef`, `ProjectedPairChannelRef`. |
| `molecular/domain.py` | **NEW** | ← `frame/adapter.py::DOMAIN_BY_CHANNEL` (verbatim) | `MOLECULE_DOMAIN_BY_CHANNEL = {"coordinate": "continuous", "charge": "continuous", "raw_pair": "discrete", "projected_pair": "discrete"}`. Documented as a fallback / example; the canonical source of truth is each adapter's `AdapterCapabilities`. |
| `molecular/bundle.py` | **NEW** | ← `contracts/bundle.py::RoundResultBundle` (molecule extension) | `MoleculeRoundResultBundle` extends the universal `RoundResultBundle` with `coordinate_channel: CoordinateChannelRef | None`, `charge_channel: ChargeChannelRef | None`, `raw_pair_channel: RawPairChannelRef | None`, `projected_pair_channel: ProjectedPairChannelRef | None`. `validate_molecule_round_result_bundle` enforces the per-channel `source_round == bundle.source_round` rule. |
| `molecular/envelope.py` | **NEW** | ← `contracts/envelope.py` (verbatim) + `envelope/manifest.py` (verbatim) + `envelope/classifier.py` (verbatim) | `MoleculeEnvelopeLayer`, `MoleculeEnvelopeManifest`, `MoleculeEnvelopeClassification`, `MoleculeTailBudgetRow`, `MoleculeFrozenEnvelopeManifestBuilder`, `classify_endpoint`, `TailBudgetAccumulator`, `StratifiedTailBudgetRow`, `ManifestBuildError`, validators. Implements the `EnvelopeCriterion` Protocol. |
| `molecular/stratification.py` | **NEW** | ← `policy/stratification.py` (verbatim) | `MoleculeStratum` enum, `MoleculeStratumAssignment`, `dominance_ratio`, `cross_stratum_mix_rejected`. The `MoleculeStratum` enum keeps the five current members; an alias `Stratum = MoleculeStratum` is provided for backward compatibility. |
| `molecular/calibration_targets.py` | **NEW** | ← `eval/calibration.py::PREDECLARED_SAFETY_METRICS` + `eval/calibration.py::CHANNEL_NAMES_FOR_CALIBRATION` | `MOLECULE_CALIBRATION_TARGETS = {"binding_affinity_kcal": "gnina", "qed": "qed_target", "admet_tox_flag": "admet_target", "synthesizability": "synth_target"}` and `MOLECULE_CHANNEL_TO_METRIC = {"coordinate": "binding_affinity_kcal", "charge": "qed", "raw_pair": "admet_tox_flag", "projected_pair": "synthesizability"}`. |
| `molecular/mixer.py` | **NEW** | ← `legacy/restart_mixer.py::adaptive_reflow_memory_restart_coords` (verbatim, refactored onto `RestartMixer` Protocol) | `RMSPreservingCoordinateMixer` implements `RestartMixer.mix()` returning the same `(coords, ledger)` tuple. A back-compat free function `adaptive_reflow_memory_restart_coords` re-exports the legacy signature. |
| `molecular/legacy_mixer.py` | **NEW** | ← `legacy/restart_mixer.py` (verbatim) | Identical to the current `legacy/restart_mixer.py`. Used by `legacy/restart_mixer.py` re-export shim. |

---

## 12. `tests/` (new structure)

| File | Status | Destination | Notes |
|---|---|---|---|
| `tests/conftest.py` | **K** | `tests/conftest.py` | Unchanged. |
| `tests/test_adapters/` (placeholder) | **K** | `tests/test_adapters/` | Unchanged. |
| `tests/test_contracts/` (placeholder) | **K** | `tests/test_contracts/` | Unchanged. |
| `tests/test_diagnostics/test_ledger.py` | **K** | `tests/test_diagnostics/test_ledger.py` | Unchanged. |
| `tests/test_envelope/` (placeholder) | **M** | `tests/test_molecular/test_molecule_envelope.py` | Will move in execution phase; placeholder stays. |
| `tests/test_eval/test_calibration.py` | **S** | `tests/test_eval/test_calibration.py` (universal math) + `tests/test_molecular/test_molecule_calibration.py` (channel-specific parts) | The Wilson/Beta math tests stay in `test_eval/`. The literal-set / channel-name tests move to `test_molecular/`. |
| `tests/test_eval/test_claim_gate.py` | **K** | `tests/test_eval/test_claim_gate.py` | Unchanged. |
| `tests/test_eval/test_protocol.py` | **K** | `tests/test_eval/test_protocol.py` | Unchanged. |
| `tests/test_frame/test_engine.py` | **K** | `tests/test_frame/test_engine.py` | Unchanged. |
| `tests/test_frame/test_merge.py` | **K** | `tests/test_frame/test_merge.py` | Unchanged. |
| `tests/test_frame/test_trace.py` | **K** | `tests/test_frame/test_trace.py` | Unchanged. |
| `tests/test_policy/test_archive.py` | **K** | `tests/test_policy/test_archive.py` | Unchanged. |
| `tests/test_policy/test_stratification_and_pruning.py` | **S** | `tests/test_policy/test_stratification_and_pruning.py` (gate only) + `tests/test_molecular/test_molecule_stratification.py` (enum + assignment) | `Stratum` enum + `StratumAssignment` tests move; `PruneGate` + `physical_noise_proxy` tests stay. |
| `tests/test_schedule/` (placeholder) | **K** | `tests/test_schedule/` | Unchanged. |
| `tests/test_writer/test_registry.py` | **K** | `tests/test_writer/test_registry.py` | Unchanged. |
| `tests/test_universal/` (NEW) | **NEW** | — | `test_no_molecular_import.py` (asserts no `universal/` module imports `molecular/`), `test_state_bundle.py`, `test_envelope_predicate.py`, `test_evaluator_protocol.py`, `test_mixer_protocol.py`. |

---

## 13. Sequencing

The migration is performed in **six additive phases**. None of them
deletes a legacy path; each phase is independently releasable behind a
re-export shim.

1. **Phase 0 (this doc)** — planning. No source changes.
2. **Phase 1** — introduce `universal/state.py` + `universal/adapter.py`
   with verbatim contents of `frame/adapter.py`. `frame/adapter.py`
   becomes a re-export. All 362 tests pass.
3. **Phase 2** — introduce `molecular/channels.py` +
   `molecular/domain.py`. `contracts/types.py` removes the four
   molecule channel aliases (re-export them from `molecular/`).
   `frame/adapter.py` removes `DOMAIN_BY_CHANNEL` (re-export from
   `molecular/domain.py`). All 362 tests pass.
4. **Phase 3** — introduce `molecular/bundle.py` extending
   `contracts/bundle.py::RoundResultBundle`. `contracts/bundle.py`
   drops the four molecule channel fields. The validator splits into
   `validate_round_result_bundle` (universal) +
   `validate_molecule_round_result_bundle`. All 362 tests pass.
5. **Phase 4** — introduce `molecular/envelope.py` +
   `molecular/stratification.py`. `contracts/envelope.py` + `envelope/*`
   become re-exports. `policy/stratification.py` becomes a re-export of
   `molecular/stratification.py`. All 362 tests pass.
6. **Phase 5** — introduce `molecular/calibration_targets.py` +
   split `eval/calibration.py` into `wilson.py` + `beta.py` +
   `manifest.py`. `eval/calibration.py` becomes a re-export shim. All
   362 tests pass.
7. **Phase 6** — introduce `molecular/mixer.py` +
   `molecular/legacy_mixer.py`. `legacy/restart_mixer.py` becomes a
   re-export shim. Add `tests/test_universal/test_no_molecular_import.py`.
   All 362 tests pass; new universal tests added.
8. **Phase 7 (follow-up)** — remove legacy shims once tests have been
   migrated to `tests/test_molecular/`.

---

## 14. Backwards compatibility shims

For each `M` / `S` move, the source location becomes a re-export shim:

```python
# adaptive_reflow/contracts/bundle.py (post Phase 3)
from adaptive_reflow.molecular.bundle import (
    MoleculeRoundResultBundle,
    validate_molecule_round_result_bundle,
)

# Universal RoundResultBundle + validators stay in this file,
# minus the four molecule channel fields.
```

Existing test imports (`from adaptive_reflow.contracts import
RoundResultBundle`) keep working because the molecule extension is
applied at construction time, not at the import site. Tests that pass
molecule channel fields will need to be updated in Phase 3 to either:
(a) construct `MoleculeRoundResultBundle` directly, or (b) wrap a
universal `RoundResultBundle` with `molecule.attach_molecule_channels(bundle, coord=..., charge=..., raw_pair=..., projected_pair=...)`.

A deprecation `warnings.warn` is added to `contracts/bundle.py` only
when `state_lock_is_detached=False` to keep the runtime quiet for
existing callers; molecule-channel-aware callers receive no warning.