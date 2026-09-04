# REFACTOR PLAN V2 — Universal / Molecular split

**Status:** Planning document only. No source files modified.

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
---

## Appendix A — universal contract notes

Companion to the main plan: documents the universal-replacement
shape of every molecule-specific dataclass or literal set. Originally
in [](UNIVERSAL_CONTRACT_NOTES.md) (deleted,
merged into this appendix).

# UNIVERSAL CONTRACT NOTES

**Status:** Planning document only. No source files modified.
**Companion to:** `REFACTOR_PLAN_V2.md`, `UNIVERSAL_MOLECULAR_MAPPING.md`.

For every molecule-specific dataclass or literal set in the current
`adaptive_reflow/` package, this document describes the universal
replacement that subsumes it. Each entry has three parts:

1. **Molecule form** — what it looks like today, with field-level
   molecule vocabulary called out.
2. **Universal form** — what it looks like after the split.
3. **Bridge** — how a molecule-aware caller maps a universal carrier
   back to the molecule vocabulary, and what invariants survive.

The universal replacements follow the `sklearn.base.BaseEstimator` +
`pytorch_lightning.LightningModule` governance pattern: the universal
contract is the *kernel*; the molecule implementation is a *subpackage-
specific* extension. A non-molecular flow matching model (graph-flow,
image-flow, sequence-flow) implements the kernel and never reaches into
`molecular/`.

---

## 1. `RoundResultBundle` — universal carrier

### 1.1 Molecule form (today)

```python
@dataclass(frozen=True)
class RoundResultBundle:
    bundle_id: BundleId
    source_round: int
    round_count: int
    run_id: RunId
    sample_id: SampleId
    trace_digest: TraceDigest
    condition_digest: ConditionDigest
    feedback_mode: FeedbackMode
    calibration_artifact_hash: ArtifactHash
    state_lock_is_detached: bool
    update_scope: str
    # ----- molecule-specific channels -----
    coordinate_channel: CoordinateChannelRef | None
    charge_channel: ChargeChannelRef | None
    raw_pair_channel: RawPairChannelRef | None
    projected_pair_channel: ProjectedPairChannelRef | None
    # -------------------------------------
    materialization_evidence: MaterializationEvidenceRef | None
    evaluator_provenance: EvaluatorProvenanceRef | None
    feedback_evidence: FeedbackEvidenceRef | None
    shape_spec: ShapeSpec
    frame_spec: FrameSpec
    provenance: ProvenanceChain
    created_at_round: int
    revoked: bool = False
```

The four `*_channel` fields name the molecule channel vocabulary:
*coordinate* (3D atom positions), *charge* (formal charges / atom
support), *raw_pair* (unprojected pair topology), *projected_pair*
(projected pair topology). A graph-flow adapter has no
`coordinate_channel`; an image-flow adapter has no `raw_pair_channel`.

### 1.2 Universal form

```python
@dataclass(frozen=True)
class RoundResultBundle:
    bundle_id: BundleId
    source_round: int
    round_count: int
    run_id: RunId
    sample_id: SampleId
    trace_digest: TraceDigest
    condition_digest: ConditionDigest
    feedback_mode: FeedbackMode
    calibration_artifact_hash: ArtifactHash
    state_lock_is_detached: bool
    update_scope: str
    # ----- generic observed channels -----
    observed_channels: Mapping[str, Mapping[str, Any]]
    # -------------------------------------
    materialization_evidence: Mapping[str, Any] | None
    evaluator_provenance: Mapping[str, Any] | None
    feedback_evidence: Mapping[str, Any] | None
    shape_spec: Mapping[str, Any]
    frame_spec: Mapping[str, Any]
    provenance: ProvenanceChain
    created_at_round: int
    revoked: bool = False
```

`observed_channels` is `channel_name -> {source_round, payload...}`,
where each value carries a `source_round` integer that must equal
`bundle.source_round`. The validator enforces this rule uniformly:
*every* channel kind must carry the right `source_round`, regardless of
whether the channel is `coordinate`, `latent_vector`, `topology_tensor`,
or anything else.

The `materialization_evidence` / `evaluator_provenance` /
`feedback_evidence` fields drop their `*Ref` NewType wrappers and
become plain `Mapping[str, Any]` because the *kinds* of evidence are
per-adapter.

### 1.3 Bridge

```python
# molecular/bundle.py
@dataclass(frozen=True)
class MoleculeRoundResultBundle(RoundResultBundle):
    coordinate_channel: CoordinateChannelRef | None = None
    charge_channel: ChargeChannelRef | None = None
    raw_pair_channel: RawPairChannelRef | None = None
    projected_pair_channel: ProjectedPairChannelRef | None = None

    def __post_init__(self) -> None:
        # Build observed_channels from the four named fields. We do this
        # in __post_init__ because the dataclass is frozen.
        mapping = {
            "coordinate": self.coordinate_channel,
            "charge": self.charge_channel,
            "raw_pair": self.raw_pair_channel,
            "projected_pair": self.projected_pair_channel,
        }
        observed = {k: v for k, v in mapping.items() if v is not None}
        object.__setattr__(self, "observed_channels", observed)
        validate_molecule_round_result_bundle(self)
```

The molecule `MoleculeRoundResultBundle` is a *thin* extension that
populates the universal `observed_channels` from the four named
fields. A molecule-aware caller sees the familiar field names; a
universal caller sees the `observed_channels` mapping.

---

## 2. `EnvelopeLayer` — universal criterion

### 2.1 Molecule form (today)

```python
@dataclass(frozen=True)
class EnvelopeLayer:
    layer_index: int
    label: str
    coordinate_extent_rms_max: float
    coordinate_extent_rms_source_stats_hash: ArtifactHash
    pocket_distance_max: float
    pocket_contact_support_min: float
    atom_count_min: int
    atom_count_max: int
    graph_complexity_max: int
    sanitization_required: bool
    valence_rules_hash: ArtifactHash
    pair_entropy_min: float
    pair_entropy_source_stats_hash: ArtifactHash
    projection_loss_max: float
    internal_geometry_pass_required: bool
    evaluator_provenance_required: bool
    source_stats_hash: ArtifactHash
    threshold_digest: ArtifactHash
    layer_hash: ArtifactHash
```

Every field except `layer_index`, `label`, and the three hash fields is
a molecule-specific threshold. None of these fields apply to a
graph-flow or image-flow model.

### 2.2 Universal form

```python
class EnvelopeCriterion(Protocol):
    """A predicate over observable + evidence that classifies a bundle."""

    def matches(
        self,
        *,
        observables: Mapping[str, float],
        evidence: Mapping[str, bool],
    ) -> tuple[bool, ComplementBlockerCode | None]: ...
```

A universal envelope is a *function* (or callable object) that maps
`{observable name -> value, evidence flag -> bool}` to
`(matches?, blocker?)`. The criterion is owned by the adapter / model
family that declares what observables are observable. There is no
canonical observable vocabulary at the universal layer; each criterion
declares its own.

```python
@dataclass(frozen=True)
class EnvelopeClassification:
    bundle_id: BundleId
    matched_layer_index: int | None
    complement_blocker: ComplementBlockerCode | None
    within_layer_thresholds: bool
    residual_extents: Mapping[str, float]  # generic name -> residual
```

`residual_extents` is `observable_name -> residual` so a graph-flow
criterion can populate `residual_extents = {"node_count": 5.0}` without
referring to molecules.

### 2.3 Bridge

```python
# molecular/envelope.py
@dataclass(frozen=True)
class MoleculeEnvelopeLayer:
    layer_index: int
    label: str
    coordinate_extent_rms_max: float
    pocket_distance_max: float
    pocket_contact_support_min: float
    atom_count_min: int
    atom_count_max: int
    graph_complexity_max: int
    sanitization_required: bool
    valence_rules_hash: ArtifactHash
    pair_entropy_min: float
    projection_loss_max: float
    internal_geometry_pass_required: bool
    evaluator_provenance_required: bool
    source_stats_hash: ArtifactHash
    threshold_digest: ArtifactHash
    layer_hash: ArtifactHash

    def matches(
        self,
        *,
        observables: Mapping[str, float],
        evidence: Mapping[str, bool],
    ) -> tuple[bool, ComplementBlockerCode | None]:
        # Existing _within_layer + _classify_blocker logic.
        ...
```

A molecule `MoleculeEnvelopeLayer` is a concrete `EnvelopeCriterion`
whose observables are `coordinate_extent_rms`, `pocket_distance`,
`pocket_contact_support`, `atom_count`, `graph_complexity`,
`pair_entropy`, `projection_loss`. A graph-flow criterion would use
`node_count`, `edge_count`, `degree_distribution_kl`, etc.

`FrozenEnvelopeManifest` / `TailBudgetAccumulator` /
`StratifiedTailBudgetRow` become generic containers that hold any
`EnvelopeCriterion` list. Their validators are re-typed as
`EnvelopeCriterion.matches(...)` invocations instead of field-by-field
arithmetic.

---

## 3. `DOMAIN_BY_CHANNEL` — universal capability

### 3.1 Molecule form (today)

```python
DOMAIN_BY_CHANNEL: Mapping[str, str] = {
    "coordinate": "continuous",
    "charge": "continuous",
    "raw_pair": "discrete",
    "projected_pair": "discrete",
    "coordinate.continuous": "continuous",
    "charge.continuous": "continuous",
    "raw_pair.discrete": "discrete",
    "projected_pair.discrete": "discrete",
}
```

Hardcoded molecule channel names mapped to `continuous` / `discrete`.

### 3.2 Universal form

Removed entirely. `AdapterCapabilities.supported_channels` is the
canonical source of truth. Each adapter advertises its own channels
and, via `has_continuous_channels` / `has_discrete_channels`, declares
which domain kinds it can carry. The engine consults the
capability token directly:

```python
# frame/engine.py (universal)
for channel in bundle.observed_channels:
    if channel not in caps.supported_channels:
        audit_codes.append(f"{ERR_CHANNEL_UNSUPPORTED}:{channel}")
    elif (
        _is_discrete_channel(channel, caps) and not caps.has_discrete_channels
    ) or (
        _is_continuous_channel(channel, caps) and not caps.has_continuous_channels
    ):
        audit_codes.append(f"{ERR_CHANNEL_DOMAIN_MISMATCH}:{channel}")
```

where `_is_discrete_channel` / `_is_continuous_channel` are adapter-
supplied predicates. The `ChannelKind` is inferred per-adapter from the
channel-name suffix (`.continuous` / `.discrete`) or via an explicit
`channel_kinds: Mapping[str, Literal["continuous", "discrete"]]` field
on `AdapterCapabilities`.

### 3.3 Bridge

```python
# molecular/domain.py
MOLECULE_DOMAIN_BY_CHANNEL: Mapping[str, str] = {
    "coordinate": "continuous",
    "charge": "continuous",
    "raw_pair": "discrete",
    "projected_pair": "discrete",
}
```

The molecule table is preserved for callers that want a quick lookup
but it is **not** consulted by the universal `Engine`. A
`FlowMol3Adapter` instance constructs its own `AdapterCapabilities`
with `supported_channels=("coordinate", "charge", "raw_pair",
"projected_pair")` and `channel_kinds=MOLECULE_DOMAIN_BY_CHANNEL` so the
universal engine routes correctly.

---

## 4. `CHANNEL_NAMES` + `CHANNEL_NAMES_FOR_CALIBRATION` — universal channels

### 4.1 Molecule form (today)

```python
# contracts/types.py
CHANNEL_NAMES: tuple[str, ...] = (
    "coordinate", "charge", "raw_pair", "projected_pair",
)

# eval/calibration.py
CHANNEL_NAMES_FOR_CALIBRATION: tuple[str, ...] = (
    "coordinate", "charge", "raw_pair", "projected_pair",
)
```

### 4.2 Universal form

Removed from `contracts/types.py`. Each module that needs the four
molecule channel names imports from `molecular.MOLECULE_CHANNELS`. The
universal layer has no canonical channel-name list — channels are
per-adapter.

```python
# molecular/channels.py
MOLECULE_CHANNELS: tuple[str, ...] = (
    "coordinate", "charge", "raw_pair", "projected_pair",
)

CoordinateChannelRef = NewType("CoordinateChannelRef", Mapping[str, Any])
ChargeChannelRef = NewType("ChargeChannelRef", Mapping[str, Any])
RawPairChannelRef = NewType("RawPairChannelRef", Mapping[str, Any])
ProjectedPairChannelRef = NewType("ProjectedPairChannelRef", Mapping[str, Any])
```

### 4.3 Bridge

`eval/wilson.py` + `eval/beta.py` no longer reference a channel-name
literal — calibration is per `(metric, channel)` where the channel is
whatever the caller supplies. A molecule caller passes
`MOLECULE_CHANNELS`; a graph-flow caller passes `("node_count",
"edge_count", "graph_spectrum")`.

---

## 5. `PREDECLARED_SAFETY_METRICS` — universal evaluator target

### 5.1 Molecule form (today)

```python
# eval/calibration.py
PREDECLARED_SAFETY_METRICS: tuple[str, ...] = (
    "binding_affinity_kcal",
    "qed",
    "admet_tox_flag",
    "synthesizability",
)
```

These are the molecule evaluation metrics (GNINA binding, QED drug-
likeness, ADMET toxicity flag, synthesizability).

### 5.2 Universal form

`eval/calibration.py` no longer carries a closed metric vocabulary.
Each calibration artifact names its own metrics in
`CalibrationManifest.per_metric_buckets`. The validation rule "metric
name must be non-empty" remains; the rule "metric must be in
`PREDECLARED_SAFETY_METRICS`" is removed.

```python
@dataclass(frozen=True)
class CalibrationManifest:
    manifest_id: ManifestId
    calibration_dataset: CalibrationDatasetId
    time_split: CalibrationTimeSplit
    per_metric_buckets: Mapping[str, tuple[CalibrationBucket, ...]]
    min_sample_count: int
    lower_bound_method: Literal["wilson", "beta"]
    artifact_hash: ArtifactHash
    frozen_before_evaluation: Literal[True] = True
```

### 5.3 Bridge

```python
# molecular/calibration_targets.py
MOLECULE_CALIBRATION_TARGETS: Mapping[str, str] = {
    "binding_affinity_kcal": "gnina",
    "qed": "qed_target",
    "admet_tox_flag": "admet_target",
    "synthesizability": "synth_target",
}
MOLECULE_CHANNEL_TO_METRIC: Mapping[str, str] = {
    "coordinate": "binding_affinity_kcal",
    "charge": "qed",
    "raw_pair": "admet_tox_flag",
    "projected_pair": "synthesizability",
}
```

The molecule caller uses `MOLECULE_CALIBRATION_TARGETS` to construct
the `per_metric_buckets` mapping. The literal lives in the molecule
layer; the universal `CalibrationManifest` is happy with any
non-empty metric name.

---

## 6. `TargetPocketHash` — universal condition hash

### 6.1 Molecule form (today)

```python
# eval/protocol.py
TargetPocketHash = NewType("TargetPocketHash", str)
```

The `EvaluatorProvenanceGuard` carries a
`required_materialization_route` that is typically a pocket-conditioned
route identifier.

### 6.2 Universal form

`TargetPocketHash` is renamed to `TargetConditionHash` and documented
as model-family-agnostic. The *kind* of condition (pocket, lattice,
sequence, class label, …) is recorded per-task.

```python
# eval/protocol.py
TargetConditionHash = NewType("TargetConditionHash", str)
# Deprecated back-compat alias; emits DeprecationWarning.
TargetPocketHash = TargetConditionHash
```

The `EvaluatorProvenanceGuard.required_materialization_route` stays a
free-form string; the universal layer does not interpret it.

### 6.3 Bridge

Molecule callers pass a pocket hash to `required_materialization_route`
and keep using `TargetPocketHash` (alias). Non-molecule callers pass a
lattice hash or sequence hash and use `TargetConditionHash`.

---

## 7. `Stratum` — universal stratification

### 7.1 Molecule form (today)

```python
class Stratum(Enum):
    GEOMETRY = "continuous_geometry"
    CHARGE = "atom_charge_support"
    PAIR = "pair_topology_support"
    MATERIALIZATION = "materialization_status"
    LINEAGE = "condition_lineage"
```

Closed enum with three molecule-specific members (GEOMETRY, CHARGE,
PAIR) and two cross-cutting members (MATERIALIZATION, LINEAGE).

### 7.2 Universal form

`Stratum` is no longer in the universal layer. The universal pruning
gate + dominance-ratio machinery operates on a generic
`score_gap: FactorValue` + `calibrated_error: FactorValue` and never
inspects the stratum kind. A non-molecular model that wants
stratification declares its own closed enum and registers an
`UnorderedAuditResult` per stratum kind.

```python
# universal/mixer.py / universal/validators.py (universal)
def dominance_ratio(
    score_gap: FactorValue,
    calibrated_error: FactorValue,
) -> FactorValue:
    """Pure math: score_gap / calibrated_error, fail-closed."""
    ...
```

`StratumAssignment` becomes generic:

```python
@dataclass(frozen=True)
class StratumAssignment:
    bundle_id: BundleId
    stratum: Any  # any closed enum; the gate does not inspect it
    score_gap: FactorValue
    calibrated_error: FactorValue
```

The `cross_stratum_mix_rejected` helper still rejects Frankensteins
(same `bundle_id`, different `stratum`) but it compares with `is`
identity, not with molecule-specific values.

### 7.3 Bridge

```python
# molecular/stratification.py
class MoleculeStratum(Enum):
    GEOMETRY = "continuous_geometry"
    CHARGE = "atom_charge_support"
    PAIR = "pair_topology_support"
    MATERIALIZATION = "materialization_status"
    LINEAGE = "condition_lineage"

# Back-compat alias so existing tests keep passing.
Stratum = MoleculeStratum

@dataclass(frozen=True)
class MoleculeStratumAssignment:
    bundle_id: BundleId
    stratum: MoleculeStratum
    score_gap: FactorValue
    calibrated_error: FactorValue
```

Molecule callers see `Stratum.GEOMETRY` etc. The dominance-ratio math
is the same code path; only the enum values differ.

---

## 8. `adaptive_reflow_memory_restart_coords` — universal mixer

### 8.1 Molecule form (today)

```python
# legacy/restart_mixer.py
def adaptive_reflow_memory_restart_coords(
    prior_coords: Any,
    memory_coords: Any,
    *,
    memory_fraction: float,
    physical_jitter_fraction: float = 0.0,
    source_round: int | None = None,
    metric_confidence: float | None = None,
) -> tuple[Any, dict[str, ...]]:
    require_torch()
    # Hardcoded (N, 3) coordinate tensor shape.
    if tuple(prior.shape) != tuple(memory.shape) or prior.dim() != 2 or int(prior.shape[-1]) != 3:
        raise ValueError("adaptive reflow memory coordinates must have shape (atoms, 3) matching the prior")
    # RMS-preserving coordinate blend.
    ...
```

The function is torch-bound, hardcodes `(N, 3)` shape, and uses
RMS-preserving coordinate geometry.

### 8.2 Universal form

```python
# universal/mixer.py
class RestartMixer(Protocol):
    """Generic restart mixer protocol."""

    def mix(
        self,
        *,
        prior: Any,
        memory: Any,
        beta: float,
        jitter_fraction: float = 0.0,
        source_round: int | None = None,
        metric_confidence: float | None = None,
    ) -> tuple[Any, Mapping[str, Any]]: ...
```

`beta` replaces the molecule-specific `memory_fraction`. The
contract does not specify shape; each mixer declares its own. The
return value is a tuple of `(mixed_state, ledger)` where `mixed_state`
is opaque and `ledger` is a `Mapping[str, Any]` of numeric diagnostics.

### 8.3 Bridge

```python
# molecular/mixer.py
class RMSPreservingCoordinateMixer:
    """RMS-preserving coordinate blender for (N, 3) coordinate tensors."""

    def mix(
        self,
        *,
        prior: Any,
        memory: Any,
        beta: float,
        jitter_fraction: float = 0.0,
        source_round: int | None = None,
        metric_confidence: float | None = None,
    ) -> tuple[Any, Mapping[str, Any]]:
        require_torch()
        if tuple(prior.shape) != tuple(memory.shape) or prior.dim() != 2 or int(prior.shape[-1]) != 3:
            raise ValueError("coordinate mixer requires (N, 3) shape")
        # Existing RMS-preserving logic from adaptive_reflow_memory_restart_coords.
        ...

# Back-compat free function.
def adaptive_reflow_memory_restart_coords(prior_coords, memory_coords, *, memory_fraction, ...):
    return RMSPreservingCoordinateMixer().mix(
        prior=prior_coords, memory=memory_coords, beta=memory_fraction, ...
    )
```

The molecule `RMSPreservingCoordinateMixer` is a verbatim port of the
existing function onto the universal Protocol. A graph-flow mixer
(`LatentConvexMixer`) would implement the same Protocol but operate
on `(N, D)` latent vectors without the `(N, 3)` constraint.

---

## 9. `TargetPocketHash` reference in `PairedComparisonRegistry` — universal

The `PairedComparisonRegistry` itself is universal; the `name` of an
arm is a free-form `ArmName` string. No molecule vocabulary appears
in the registry dataclass. The `TaskCondition` Literal in
`writer/registry.py` is the only place molecule task kinds appear, and
it is already documented as per-task:

```python
TaskCondition = Literal[
    "unconditional_3d",
    "pocket_conditioned",
    "sequence_conditioned",
    "other",
]
```

The split adds `"lattice_conditioned"` + `"graph_conditioned"` as
explicit alternatives to `pocket_conditioned`. No universal
replacement is needed because the type is already model-family-agnostic.

---

## 10. `LayeredMetricPanel` tier labels — universal (no change)

The `LayeredMetricPanel` tier labels
(`raw_generation` / `adaptive_reflow` / `postprocess_assisted`) are
**not** molecule-specific — they describe the *origin* of a metric
relative to the round frame, not the metric *kind*. A molecule metric
(`binding_affinity_kcal`) and a graph-flow metric (`spectral_gap`)
both have a `raw_generation` tier. No universal replacement is needed.

---

## 11. Summary table

| Molecule symbol | Universal replacement | Bridge |
|---|---|---|
| `RoundResultBundle.{coordinate,charge,raw_pair,projected_pair}_channel` | `RoundResultBundle.observed_channels: Mapping[str, Mapping[str, Any]]` | `MoleculeRoundResultBundle` populates `observed_channels` from the four named fields. |
| `EnvelopeLayer` (17 molecule fields) | `EnvelopeCriterion` Protocol | `MoleculeEnvelopeLayer` implements the protocol with the same 17 fields. |
| `FrozenEnvelopeManifest`, `TailBudgetRow`, `StratifiedTailBudgetRow` | Generic containers that hold `EnvelopeCriterion` lists | `MoleculeEnvelopeManifest` wraps the molecule criterion list. |
| `DOMAIN_BY_CHANNEL` | `AdapterCapabilities.supported_channels` + per-adapter `channel_kinds` | `MOLECULE_DOMAIN_BY_CHANNEL` provided as a back-compat fallback. |
| `CHANNEL_NAMES`, `CHANNEL_NAMES_FOR_CALIBRATION` | None (per-adapter) | `MOLECULE_CHANNELS` in `molecular/channels.py`. |
| `PREDECLARED_SAFETY_METRICS` | None (per-artifact) | `MOLECULE_CALIBRATION_TARGETS` in `molecular/calibration_targets.py`. |
| `TargetPocketHash` | `TargetConditionHash` | Back-compat alias; both name the same `str` NewType. |
| `Stratum` (closed enum) | None (per-task) | `MoleculeStratum` in `molecular/stratification.py`; `policy.stratification.Stratum = MoleculeStratum` re-export. |
| `adaptive_reflow_memory_restart_coords` | `RestartMixer` Protocol | `RMSPreservingCoordinateMixer` implements the protocol; free function re-export. |
| `LayeredMetricPanel` tier labels | (no change — already universal) | n/a |

Every molecule symbol has a universal replacement or a per-task
declaration. The 362 tests that exercise molecule vocabulary today
keep passing because the molecule extension re-populates the universal
carrier in `__post_init__`.
---

## Appendix B — universal/molecular module mapping

Companion to the main plan: enumerates every current source module
under `adaptive_reflow/` and specifies its destination after the
universal / molecular split. Originally in
[`UNIVERSAL_MOLECULAR_MAPPING.md`](UNIVERSAL_MOLECULAR_MAPPING.md)
(deleted, merged into this appendix).

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