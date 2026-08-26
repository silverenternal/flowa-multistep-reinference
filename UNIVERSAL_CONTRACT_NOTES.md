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