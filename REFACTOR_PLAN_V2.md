# REFACTOR PLAN V2 — Universal / Molecular split

**Status:** Planning document only. No source files modified.
**Working dir:** `c:/Users/31472/codes/flowa-multistep-reinference/`
**Date:** 2026-08-26

This plan supersedes the prior `ARCHITECTURE_PLAN.md` (which collapsed
universal/molecular code into one package). It introduces an explicit
`adaptive_reflow/universal/` core (model-family-agnostic) and an
`adaptive_reflow/molecular/` concrete implementation (pocket-conditioned 3D
molecular flow matching). The `frame/`, `contracts/`, `policy/`, `schedule/`,
`diagnostics/`, `writer/`, `eval/`, and `legacy/` subpackages are reorganised
so each molecule-specific field becomes a generic, pluggable contract that a
non-molecular adapter can also satisfy.

---

## 1. Motivation — why split

The current `adaptive_reflow/` package already separates the universal
"round frame" (`frame/`) from molecule-specific concerns, but several files
hardcode molecule vocabulary:

* `contracts/bundle.py::RoundResultBundle` — fields named
  `coordinate_channel`, `charge_channel`, `raw_pair_channel`,
  `projected_pair_channel`. A graph-flow or image-flow model has different
  channels.
* `contracts/envelope.py::EnvelopeLayer` — fields named
  `coordinate_extent_rms_max`, `pocket_distance_max`,
  `pocket_contact_support_min`, `atom_count_min/max`,
  `graph_complexity_max`, `valence_rules_hash`, `pair_entropy_min`. None
  of these apply to a non-molecular flow matching model.
* `frame/adapter.py::DOMAIN_BY_CHANNEL` — maps the four molecule
  channel names to `"continuous"` / `"discrete"` domains. A non-molecular
  adapter that uses `latent_vector` / `topology_tensor` cannot reuse this
  table.
* `eval/calibration.py::CHANNEL_NAMES_FOR_CALIBRATION` and
  `PREDECLARED_SAFETY_METRICS` — molecule-specific metric names
  (`binding_affinity_kcal`, `qed`, `admet_tox_flag`, `synthesizability`).
* `eval/protocol.py::TargetPocketHash` — explicit pocket hash.
* `policy/stratification.py::Stratum` — closed enum
  `GEOMETRY / CHARGE / PAIR / MATERIALIZATION / LINEAGE`. The first three
  are molecule-specific.
* `legacy/restart_mixer.py::adaptive_reflow_memory_restart_coords` —
  hardcodes `(N, 3)` coordinate tensor shape and RMS-preserving
  coordinate geometry. Nothing else in the package can call this.

These vocabulary leaks make it impossible for a non-molecular Flow
Matching adapter to use `adaptive_reflow` without either monkey-patching
the channels or forking the package.

The governance patterns from `sklearn`, `pytorch_lightning`, and
`huggingface/transformers` show how to factor this cleanly:

* `sklearn.base.BaseEstimator` provides a universal parameter
  introspection + clone contract that any estimator (classifier,
  regressor, clusterer, transformer) inherits unchanged. Subpackage-
  specific algorithms implement only `fit` and the prediction surface.
* `pytorch_lightning.LightningModule` is a universal *lifecycle*
  contract (training_step, configure_optimizers, etc.). The Trainer
  owns everything outside the model. A researcher can write a new
  LightningModule without ever importing `Trainer`'s internals.
* `huggingface/transformers` splits the universal `PretrainedConfig` /
  `PreTrainedModel` base classes from per-architecture implementations
  in `models/`. The base classes provide shared IO + tensor utilities;
  the per-model files provide only the model-specific forward pass.

The same factoring applies here: the "round frame" is a universal
lifecycle; the channel vocabulary, threshold predicates, and evaluator
protocols are molecule-specific.

---

## 2. Design principles

| Principle | Source | Application |
|---|---|---|
| **Universal kernel + molecule concrete layer** | sklearn `BaseEstimator` + subpackages | `universal/` provides generic Protocols + dataclasses; `molecular/` implements them with molecule-specific dataclasses. |
| **Adapter capabilities are advertised, not assumed** | ONNX Runtime `IExecutionProvider` | `AdapterCapabilities.supported_channels` stays a free-form tuple. Channel vocabulary is per-adapter, not hardcoded. |
| **Library-agnostic opaque handles** | HF `PreTrainedModel` + vLLM | `TensorRef` (already an opaque string) survives the split unchanged. |
| **Round frame is universal, schedule family is closed but not molecule-specific** | Lightning `Trainer` | `Engine.run_round` does not assume molecule channels; the channel rule consumes per-channel evidence via generic `Mapping[str, ChannelTransferEvidence]`. |
| **Closed literal sets are *contracts*, not vocabularies** | sklearn `_parameter_constraints` | `COMPLEMENT_BLOCKER_CODES`, `AUTHORITY_MODES`, `SCHEDULE_PHASES` remain closed; `CHANNEL_NAMES` becomes a *declared* set rather than a fixed vocabulary. |
| **Failure modes named by code, not by string** | JSON Schema `$id`/`$schema` | `ERR_*` constants stay; "molecule" never appears in an error code. |
| **Pure stdlib at the contract layer** | Existing governance | `universal/` is stdlib-only; `molecular/` may import torch (via adapter) for its RMS-preserving mixer. |

---

## 3. Target directory tree

```
flowa-multistep-reinference/
├── adaptive_reflow/                          # package root
│   ├── __init__.py                           # NEW: empty or re-export shims only
│   ├── contracts/                            # KEEP and GENERALIZE: drop molecule channel/channelref names
│   ├── frame/                                # KEEP: engine + adapter Protocol + bounded_merge
│   ├── policy/                               # KEEP: mostly already universal
│   ├── schedule/                             # KEEP: already universal
│   ├── diagnostics/                          # KEEP: already universal
│   ├── writer/                               # KEEP: already universal
│   ├── adapters/                             # KEEP: per-model glue (flowmol3, reference, synthetic)
│   ├── universal/                            # NEW: explicit model-family-agnostic core
│   │   ├── __init__.py
│   │   ├── state.py                          # generic StateBundle / TensorRef / ChannelRef (no domain)
│   │   ├── adapter.py                        # FlowMatchingODEAdapter Protocol + AdapterCapabilities
│   │   │                                       (the four channel names go to molecular/channels.py)
│   │   ├── envelope.py                       # generic EnvelopeCriterion: Predicate-based threshold
│   │   ├── evaluator.py                      # generic Evaluator Protocol (not GNINA-specific)
│   │   ├── mixer.py                          # RestartMixer Protocol: RMS-preserving / latent-convex / discrete-identity
│   │   └── validators.py                     # universal validators
│   ├── molecular/                            # NEW: concrete molecule implementation
│   │   ├── __init__.py
│   │   ├── bundle.py                         # MoleculeRoundResultBundle(coordinate, charge, raw_pair, projected_pair)
│   │   ├── envelope.py                       # MoleculeEnvelopeLayer(rms_max, pocket_distance_max,
│   │   │                                       atom_count_*, pair_entropy_min, valence_rules_hash)
│   │   ├── channels.py                       # MOLECULE_CHANNELS = ("coordinate", "charge", "raw_pair", "projected_pair")
│   │   ├── domain.py                         # MOLECULE_DOMAIN_BY_CHANNEL + DECLARED channel kind hints
│   │   ├── stratification.py                 # Stratum enum (GEOMETRY/CHARGE/PAIR/MATERIALIZATION/LINEAGE)
│   │   ├── calibration_targets.py            # MOLECULE_CALIBRATION_TARGETS (binding_affinity_kcal,
│   │   │                                       qed, admet_tox_flag, synthesizability) + channel-to-metric map
│   │   ├── mixer.py                          # RMSPreservingCoordinateMixer
│   │   │                                       (the current adaptive_reflow_memory_restart_coords logic)
│   │   └── legacy_mixer.py                   # ← legacy/restart_mixer.py, kept verbatim for compat
│   ├── eval/                                 # KEEP + SPLIT: Wilson/Beta math universal, evaluator
│   │   │                                       protocols move to molecular/calibration_targets.py
│   │   ├── __init__.py
│   │   ├── wilson.py                         # ← eval/calibration.py: wilson_lower_bound only
│   │   ├── beta.py                           # ← eval/calibration.py: beta_lower_bound only
│   │   ├── manifest.py                       # ← eval/manifests.py
│   │   ├── claim_gate.py                     # KEEP
│   │   ├── promotion.py                      # KEEP
│   │   ├── rollback.py                       # KEEP
│   │   ├── metric_panel.py                   # KEEP
│   │   └── protocol.py                       # KEEP (PairedComparisonArm + EvaluatorProvenanceGuard
│   │                                           + RoundToRoundOscillationDetector — all universal)
│   └── legacy/                               # KEEP: torch-bound modules; eventually empty
│       ├── __init__.py                       # emits DeprecationWarning; empty __all__
│       ├── control_policy.py                 # (unchanged)
│       ├── loop.py                           # (unchanged)
│       ├── loop_contract.py                  # (unchanged)
│       ├── mechanism_adapter.py              # (unchanged)
│       ├── metric_feedback.py                # (unchanged)
│       ├── orchestration.py                  # (unchanged)
│       ├── plan.py                           # (unchanged)
│       ├── restart_mixer.py                  # DEPRECATED: moved to molecular/legacy_mixer.py
│       └── services.py                       # (unchanged)
├── tests/
│   ├── test_universal/                       # NEW: verifies universal/ works without molecular/
│   │   ├── test_no_molecular_import.py       # assert no universal/ module imports molecular/
│   │   ├── test_state_bundle.py              # generic StateBundle + TensorRef round-trip
│   │   ├── test_envelope_predicate.py        # Predicate-based envelope
│   │   ├── test_evaluator_protocol.py        # generic Evaluator Protocol
│   │   └── test_mixer_protocol.py            # RestartMixer Protocol
│   ├── test_molecular/                       # NEW: 362 tests' molecule behaviour preserved
│   │   ├── test_molecule_bundle.py           # was tests/test_contracts/.../test_bundle.py (split later)
│   │   ├── test_molecule_envelope.py         # was tests/test_envelope/...
│   │   ├── test_molecule_stratification.py   # was tests/test_policy/...
│   │   ├── test_molecule_calibration.py      # was tests/test_eval/test_calibration.py (channel-specific parts)
│   │   └── test_molecule_mixer.py            # was tests/test_legacy/restart_mixer tests
│   ├── test_contracts/                       # KEEP: contracts tests
│   ├── test_diagnostics/                     # KEEP
│   ├── test_eval/                            # KEEP: only universal Wilson/Beta math + claim_gate + protocol
│   ├── test_frame/                           # KEEP: engine, merge, trace
│   ├── test_policy/                          # KEEP: archive, pruning (stratification moves to molecular/)
│   ├── test_schedule/                        # KEEP
│   └── test_writer/                          # KEEP
├── REFACTOR_PLAN_V2.md                       # this file
├── UNIVERSAL_MOLECULAR_MAPPING.md            # file-by-file mapping
├── UNIVERSAL_CONTRACT_NOTES.md               # universal replacements for molecule dataclasses
├── ARCHITECTURE.md                           # updated governance doc (post-execution)
├── ARCHITECTURE_PLAN.md                      # historical: prior plan
├── CONTRACTS.md                              # §1-§8 typed-contract skeletons (updated)
├── DESIGN_BOUNDARY.md                        # DTB-R0 design boundary
├── FILE_MAPPING.md                           # historical: old → new file moves
├── README.md
├── STATUS.md
├── SPLIT_NOTES.md                            # historical: per-symbol placement
├── todo.json
└── docs/                                     # project-internal research notes
```

---

## 4. What changes

### 4.1 Universal core (`adaptive_reflow/universal/`)

* **`state.py`** — the current `frame/adapter.py` carrier types
  (`StateBundle`, `TensorRef`, `AdapterCapabilities`, `ODEConditionDelta`,
  `ODEIntegratorTrace`) move here with no field changes. `StateBundle.channels`
  remains `Mapping[str, TensorRef]`; no molecule-specific keys are baked in.
* **`adapter.py`** — `FlowMatchingODEAdapter` Protocol + `validate_*`
  helpers. `DOMAIN_BY_CHANNEL` is removed; domain resolution becomes a
  function of `AdapterCapabilities.supported_channels` per adapter.
* **`envelope.py`** — `EnvelopeCriterion` Protocol:
  `class EnvelopeCriterion(Protocol): def matches(self, *, observables: Mapping[str, float], evidence: Mapping[str, bool]) -> tuple[bool, ComplementBlockerCode | None]: ...`
  Replaces the molecule-specific `EnvelopeLayer` field-by-field check.
* **`evaluator.py`** — `Evaluator` Protocol:
  `class Evaluator(Protocol): def evaluate(self, *, sample: Mapping[str, Any]) -> tuple[float, Mapping[str, float]]: ...`
  Replaces the implicit `gnina_target` / `qed_target` / `admet_target` /
  `posebusters_target` assumptions in `eval/protocol.py`.
* **`mixer.py`** — `RestartMixer` Protocol:
  `class RestartMixer(Protocol): def mix(self, *, prior: Any, memory: Any, beta: float, ...) -> tuple[Any, Mapping[str, Any]]: ...`
  Subsumes `adaptive_reflow_memory_restart_coords`, plus latent-convex
  mixing for non-coordinate domains and discrete-identity mixing for
  pair/topology channels.
* **`validators.py`** — `validate_unit_factor`, `validate_nonneg_int`,
  `validate_positive_int`, `ValidationResult` (already in
  `contracts/validators.py`; re-exported from `universal/validators.py`).

### 4.2 Molecular concrete (`adaptive_reflow/molecular/`)

* **`bundle.py`** — `MoleculeRoundResultBundle` adds the four molecule
  channel refs (`CoordinateChannelRef`, `ChargeChannelRef`,
  `RawPairChannelRef`, `ProjectedPairChannelRef`). The base carrier is
  the universal `RoundResultBundle`; molecule-specific channels are
  declared in `channels.py`.
* **`envelope.py`** — `MoleculeEnvelopeLayer` carries
  `coordinate_extent_rms_max`, `pocket_distance_max`,
  `pocket_contact_support_min`, `atom_count_min/max`,
  `graph_complexity_max`, `valence_rules_hash`, `pair_entropy_min`,
  `projection_loss_max`, `internal_geometry_pass_required`,
  `evaluator_provenance_required`. Implements `EnvelopeCriterion.matches`.
* **`channels.py`** — `MOLECULE_CHANNELS = ("coordinate", "charge",
  "raw_pair", "projected_pair")` and the four `NewType` aliases. The
  universal `AdapterCapabilities.supported_channels` becomes the
  intersection of the adapter's own declaration and any caller-supplied
  binding.
* **`domain.py`** — `MOLECULE_DOMAIN_BY_CHANNEL = {"coordinate":
  "continuous", "charge": "continuous", "raw_pair": "discrete",
  "projected_pair": "discrete"}`. Used as a *fallback* by molecule-aware
  callers only.
* **`stratification.py`** — `Stratum` enum with the current five members.
  Re-exports `StratumAssignment`, `dominance_ratio`,
  `cross_stratum_mix_rejected`. Imported by
  `adaptive_reflow/policy/stratification.py` as a re-export so existing
  tests that import from `policy.stratification` keep working.
* **`calibration_targets.py`** —
  `MOLECULE_CALIBRATION_TARGETS = {"binding_affinity_kcal": "gnina",
  "qed": "qed_target", "admet_tox_flag": "admet_target",
  "synthesizability": "synth_target"}` and
  `MOLECULE_CHANNEL_TO_METRIC = {"coordinate": "binding_affinity_kcal",
  "charge": "qed", "raw_pair": "admet_tox_flag",
  "projected_pair": "synthesizability"}`. Replaces the literal set in
  `eval/calibration.py::PREDECLARED_SAFETY_METRICS`.
* **`mixer.py`** — `RMSPreservingCoordinateMixer` implements the
  current `adaptive_reflow_memory_restart_coords` logic verbatim but
  exposes it via the `RestartMixer` Protocol.
* **`legacy_mixer.py`** — verbatim copy of
  `legacy/restart_mixer.py` so existing legacy tests continue to pass
  until they are migrated.

### 4.3 `eval/` (split)

* **`wilson.py`** — pure Wilson lower-bound constructor. No molecule
  fields. `wilson_lower_bound(successes, trials, confidence=0.95)` stays
  unchanged.
* **`beta.py`** — pure Beta posterior lower quantile. No molecule
  fields. `beta_lower_bound(successes, trials, confidence=0.95)` stays
  unchanged.
* **`manifest.py`** — JSON serialisation for `CalibrationManifest`,
  `validate_manifest_frozen`, `frozen_manifest_hash`. The
  `CHANNEL_NAMES_FOR_CALIBRATION` and `PREDECLARED_SAFETY_METRICS`
  literal sets are removed; their callers reference
  `molecular.calibration_targets` instead.
* **`claim_gate.py`**, **`promotion.py`**, **`rollback.py`**,
  **`metric_panel.py`**, **`protocol.py`** — KEEP unchanged. They are
  already model-family-agnostic.

### 4.4 `frame/` (no structural change)

The `frame/` subpackage stays the universal round driver. Its
`adapter.py` becomes a thin re-export from `universal/adapter.py` (the
canonical home) so existing imports from `adaptive_reflow.frame.adapter`
keep working without modification. The `Engine` and `PhaseState`
classes stay in `frame/`; they are not molecule-specific.

### 4.5 `contracts/` (vocabulary changes)

* **`types.py`** — the four molecule channel aliases
  (`CoordinateChannelRef`, `ChargeChannelRef`, `RawPairChannelRef`,
  `ProjectedPairChannelRef`) move to `molecular/channels.py`. The
  generic `ChannelRef = NewType("ChannelRef", Mapping[str, Any])` stays.
  `CHANNEL_NAMES = ("coordinate", "charge", "raw_pair", "projected_pair")`
  is removed; callers reference `molecular.MOLECULE_CHANNELS`.
* **`bundle.py`** — `RoundResultBundle` loses the four molecule channel
  fields. It keeps `condition_digest`, `state_lock_is_detached`,
  `update_scope`, `feedback_mode`, `provenance`, etc. — those are
  universal. The cross-contract validator stops checking the four
  molecule channel source-rounds and instead validates that
  `bundle.observed_channels` is a `Mapping[str, Any]` with each value
  carrying a `source_round` that equals `bundle.source_round`.
* **`envelope.py`** — `EnvelopeLayer`, `FrozenEnvelopeManifest`,
  `EnvelopeClassification`, `TailBudgetRow` are **moved** to
  `molecular/envelope.py`. The `envelope/manifest.py` runtime builder
  becomes a thin wrapper that calls the molecule-layer builder. A new
  universal `Envelope` Protocol in `universal/envelope.py` describes
  what every model-family must implement.

### 4.6 `policy/`, `schedule/`, `diagnostics/`, `writer/`, `adapters/`

These subpackages are unchanged. `policy/stratification.py` re-exports
`Stratum`, `StratumAssignment`, etc. from `molecular/stratification.py`
so existing tests keep passing. `adapters/flowmol3.py` continues to
implement `FlowMatchingODEAdapter` and advertises the molecule
channels; `adapters/synthetic.py` already works at the channel-set
level and only needs the universal `DOMAIN_BY_CHANNEL` removal.

### 4.7 `legacy/`

No source changes in this phase. `legacy/restart_mixer.py` keeps
working. Eventually it is replaced by a thin re-export of
`molecular/legacy_mixer.py`.

---

## 5. Test preservation strategy

The 362-test suite currently tests molecule behaviour in
`tests/test_eval/`, `tests/test_frame/`, `tests/test_policy/`,
`tests/test_writer/`, `tests/test_diagnostics/`. After the split:

1. **No source change in this phase.** The three planning docs are the
   only deliverables. All 362 tests continue to pass.
2. **Re-export shims in `frame/`, `policy/`, `contracts/`** keep the
   existing import paths working (`from adaptive_reflow.frame.adapter
   import FlowMatchingODEAdapter`, etc.).
3. **New `tests/test_universal/`** verifies that the universal core
   imports nothing from `molecular/`. This is the load-bearing test
   that protects the split: if a future change drags a molecule import
   into `universal/`, the test fails closed.
4. **Migration phase (separate plan)** moves the 362 tests into
   `tests/test_molecular/` and adds the new universal tests.

---

## 6. Out of scope (deferred to execution phase)

* **Renaming `frame/adapter.py` to `universal/adapter.py`** — depends on
  how many callers outside `adaptive_reflow/` import from `frame/`.
* **Removing `DOMAIN_BY_CHANNEL` from `frame/adapter.py`** —
  `molecular/domain.py` becomes the source of truth; `frame/adapter.py`
  re-exports it for back-compat.
* **Splitting `eval/calibration.py` into `wilson.py` + `beta.py`** —
  depends on confirming no caller reaches into the calibration module
  for the literal sets. The literal sets move first; the math split
  follows.
* **Deleting `legacy/restart_mixer.py`** — happens only after
  `molecular/legacy_mixer.py` is in production and all legacy tests
  are migrated or marked `@pytest.mark.legacy`.

---

## 7. Summary of governance changes

| Aspect | Before | After |
|---|---|---|
| **Channel vocabulary** | Hardcoded in 5+ files (`contracts/types.py`, `contracts/bundle.py`, `contracts/envelope.py`, `frame/adapter.py`, `eval/calibration.py`, `eval/protocol.py`, `policy/stratification.py`) | Declared in `molecular/channels.py`; referenced via `molecular.MOLECULE_CHANNELS`. |
| **Envelope thresholds** | Hardcoded molecule fields on `EnvelopeLayer` | Generic `EnvelopeCriterion` Protocol in `universal/`; `MoleculeEnvelopeLayer` implements it. |
| **Evaluator vocabulary** | Implicit GNINA/QED/ADMET/PoseBusters in `eval/protocol.py` and `eval/calibration.py` | Generic `Evaluator` Protocol in `universal/`; concrete molecule targets in `molecular/calibration_targets.py`. |
| **Restart mixer** | `(N, 3)` coordinate tensor shape hardcoded in `legacy/restart_mixer.py` | `RestartMixer` Protocol in `universal/`; `RMSPreservingCoordinateMixer` implements it in `molecular/`. |
| **Adapter capability advertisement** | Implicit via `DOMAIN_BY_CHANNEL` lookup | `AdapterCapabilities.supported_channels` is the only source of truth. |
| **Layered metric panel** | Tier labels hardcoded (`raw_generation`/`adaptive_reflow`/`postprocess_assisted`) | KEEP — the labels are already model-family-agnostic. |

The cleanest mental model after this split: **`universal/` is the
"BaseEstimator + Trainer" kernel; `molecular/` is the per-architecture
`models/` directory; `frame/`, `eval/`, `policy/`, `schedule/`,
`diagnostics/`, `writer/` are the orchestration / evaluation /
lifecycle plumbing that both layers share.**

---

## 8. Migration risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Renaming breaks an external import path | Medium | Medium | Re-export shims in `frame/`, `contracts/`, `policy/` during transition. |
| A test reaches into `eval/calibration.py` for `CHANNEL_NAMES_FOR_CALIBRATION` | High | Low | Move the literal to `molecular/calibration_targets.py`; re-export from `eval/` for one release. |
| `state_lock_is_detached` validator logic regresses | Low | High | `validate_round_result_bundle` keeps the universal `detach_proof` check; the molecule channel `source_round` check moves to `validate_molecule_bundle`. |
| `RestartMixer` Protocol loses the RMS-preserving property | Medium | High | `RMSPreservingCoordinateMixer` is a verbatim copy of `adaptive_reflow_memory_restart_coords`; its `mix()` returns the same `(coords, ledger)` tuple. |
| `frame/engine.py` imports a molecule symbol by accident | Medium | High | Add `tests/test_universal/test_no_molecular_import.py` that scans `universal/` AST for `import molecular`. |
| `eval/calibration.py` literal sets are referenced by a downstream harness | Medium | Medium | Move literal sets with back-compat re-exports; one release deprecation. |

The split is **additive** in this phase: nothing is deleted; everything
molecule-specific is duplicated into `molecular/`, with re-export shims
in place to keep the 362 tests passing. Removal of the legacy paths is
deferred to a follow-up execution plan.