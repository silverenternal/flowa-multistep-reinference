# Adaptive Reflow Data Contracts

Status: design-only dataclass skeletons. No runtime implementation. All dataclasses are
`frozen=True` unless explicitly marked mutable. Types use `typing` qualifiers and refer to
the canonical module-level identifiers introduced below (no imports inside skeletons).

Type conventions:
- `frozen=True` for evidence/ledger/manifest rows (immutable ledger semantics).
- `NewType` style aliases are referenced by name only; the concrete alias module is not
  defined here (e.g. `BundleId`, `ChannelName`, `FactorValue` are declared in
  `restart_memory_types.py` at implementation time).
- All float factors live in `[0,1]` unless annotated otherwise.
- All `source_round` / `round_in_cycle` indices are non-negative `int`; missing rounds are
  encoded as `None`, not as sentinel `0` or `-1`.

---

## 1. Atomic Source Bundle (DTB-R1)

Satisfies: `DTB-R1`, partially `DTB-R5` (provenance), partially `DTB-S1` (single writer
attached to bundle), partially `DTB-NC2` (carrier for tail/complement fields).

Subsumes these existing `RestartMemoryState` fields (see
`pocket_modules/mechanisms/inference/adaptive_reflow/restart_memory.py:20`):

- `alpha_noise`, `beta_memory`, `prior_rms`, `memory_rms`, `restart_rms`,
  `coords_bias_norm`, `physical_jitter_fraction`, `physical_jitter_rms`, `source_round`,
  `metric_confidence`, `state_lock_is_detached`, `update_scope`.

The legacy `RestartMemoryState` is retained as the *mixer-level* derived struct
(emitted per restart boundary) while `RoundResultBundle` becomes the *selection-level*
carrier passed to the policy. `RestartMemoryState.as_ledger()` is migrated to
`ChannelTransferEvidence.raw_score` rows, not retained as a parallel schema.

Cross-references:
- `reinference_plan.build_reinference_round_plan` consumes `RoundResultBundle`.
- `flowa_core.transport.adaptive_reflow_runtime` consumes
  `DynamicRestartTransferLedger`.
- `noise_bias.restart_bias.metric_direction_for_name` is invoked from
  `ChannelTransferDecision.metric_direction`, not the bundle itself.

Test fixture types:
- `BundleFixture`: valid detached bundle with finite tensors.
- `CrossRoundStitchFixture`: bundle A coords + bundle B pair/charge (must reject).
- `DetachedStateFixture`: bundle with `state_lock_is_detached=False` (must reject).
- `UnknownSchemaFixture`: missing channel (must reject).
- `DuplicateBundleIdFixture`: same id reused (must reject).
- `NaNInfFixture`: non-finite tensor entries (must reject).
- `FutureRoundFixture`: `source_round > current_round` (must reject).

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
    feedback_mode: FeedbackMode            # "inference_external_diagnostic" | "proxy_only" | "training_authorized"
    calibration_artifact_hash: ArtifactHash
    state_lock_is_detached: bool           # must be True
    update_scope: Literal["ode_restart_distribution_only"]
    coordinate_channel: CoordinateChannelRef | None  # None => channel gate=0
    charge_channel: ChargeChannelRef | None
    raw_pair_channel: RawPairChannelRef | None
    projected_pair_channel: ProjectedPairChannelRef | None
    materialization_evidence: MaterializationEvidenceRef | None
    evaluator_provenance: EvaluatorProvenanceRef | None
    feedback_evidence: FeedbackEvidenceRef | None
    shape_spec: ShapeSpec
    frame_spec: FrameSpec                    # reference frame / normalization contract
    provenance: ProvenanceChain
    created_at_round: int                   # round at which bundle was assembled
    revoked: bool = False                   # soft-revocation flag, not a deletion


@dataclass(frozen=True)
class ChannelTransferEvidence:
    bundle_id: BundleId
    channel: ChannelName                    # "coordinate" | "charge" | "raw_pair" | "projected_pair"
    materialization_pass: bool | None       # None => unknown => gate=0
    geometry_pass: bool | None              # PoseBusters / sanitization gate
    perturbation_stability_lower_bound: FactorValue  # [0,1]
    condition_sensitivity_observable_pass: bool | None
    external_metric_uncertainty: FactorValue | None  # [0,1] or None if missing
    proxy_only_evidence: bool               # True => cannot satisfy calibration_lower_bound
    ambiguity: FactorValue                  # [0,1] from independent selectors
    degeneracy_penalty: FactorValue         # [0,1] from low margin / projection loss
    support_coverage: FactorValue           # [0,1]
    recency_decay: FactorValue              # [0,1]
    calibration_lower_bound: FactorValue    # [0,1] from frozen time-split artifact
    raw_score: float                        # selection score, NOT a posterior
    bounded_score: float                    # monotonic bounded projection
    provenance: ProvenanceChain
    validation_errors: tuple[str, ...]      # empty when evidence is valid


@dataclass(frozen=True)
class ChannelTransferDecision:
    bundle_id: BundleId
    channel: ChannelName
    gate: bool                              # True iff every required component is valid
    raw_factors: tuple[FactorValue, ...]    # one per component above, ordered
    evidence_score: FactorValue             # product of [0,1] factors, 0 if gate=False
    scheduled_cap: FactorValue              # cosine or schedule-supplied cap for this channel
    bounded_target_fraction: FactorValue    # cap * evidence_score, bounded by delta caps
    fresh_noise_floor: FactorValue          # per-channel minimum fresh-noise mass
    alpha: FactorValue                      # 1 - bounded_target_fraction (no equality assumed)
    beta: FactorValue                       # final applied memory coefficient
    audit_reason: str                       # human-readable, not parsed
    blocker_codes: tuple[str, ...]          # empty iff gate=True


@dataclass(frozen=True)
class DynamicRestartTransferLedger:
    ledger_row_id: LedgerRowId
    run_id: RunId
    sample_id: SampleId
    trace_digest: TraceDigest
    source_round: int
    target_round: int
    outer_cycle_id: int
    selected_bundle_id: BundleId | None     # None iff no bundle passed the gate
    rejected_bundle_ids: tuple[BundleId, ...]
    per_channel_evidence: tuple[ChannelTransferEvidence, ...]
    per_channel_decision: tuple[ChannelTransferDecision, ...]
    alpha_by_channel: Mapping[ChannelName, FactorValue]
    beta_by_channel: Mapping[ChannelName, FactorValue]
    raw_fraction_by_channel: Mapping[ChannelName, FactorValue]
    bounded_fraction_by_channel: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    calibration_artifact_hash: ArtifactHash
    frozen_envelope_manifest_hash: ArtifactHash | None
    tail_budget_row_ref: TailBudgetRowId | None
    finite_prefix_only: bool
    empirical_only: bool                    # must be True for any run with finite cycles
    feedback_mode: FeedbackMode
    writer_id: MechanismId                  # "inference.adaptive_reflow"
    provenance: ProvenanceChain
    validation_errors: tuple[str, ...]
    created_at_round: int
```

---

## 2. Envelope Ladder (DTB-NC1)

Satisfies: `DTB-NC1`, partially `DTB-NC2` (tail admissibility references manifest hash),
partially `DTB-L3` (stratum membership), partially `DTB-R4` (archive bound to envelope).

The envelope ladder is frozen at run start and is not allowed to drift with
current-round scores; `EnvelopeClassification` is therefore a strictly derived view, not
a mutable plan.

Cross-references:
- `reinference_plan.build_reinference_round_plan` reads `FrozenEnvelopeManifest`.
- `external_metric_feedback` reads `EnvelopeClassification` only for diagnostic log lines,
  never for runtime gate decisions.
- `noise_bias.spectral_budget` is explicitly NOT a consumer of the envelope (diagnostics
  stay outside the gate).

Test fixture types:
- `ScoreDependentCutoffFixture`: same input/config with two different winner scores must
  produce identical `FrozenEnvelopeManifest`.
- `OutOfEnvelopeFixture`: endpoint exceeding every layer (must produce blocker).
- `UnclassifiedComplementFixture`: endpoint missing all classifiers (must produce blocker).
- `DuplicateEvidenceFixture`: two metric rows from same upstream bundle (must not
  inflate mass).
- `FinitePrefixFixture`: short run asserts `empirical_only=True` and forbids any field
  named `tail_selection_certified`.

```python
@dataclass(frozen=True)
class EnvelopeLayer:
    layer_index: int                        # 0..K-1, monotone by exhaustion
    label: str                              # e.g. "K_0_in_pocket", "K_1_contact_support"
    coordinate_extent_rms_max: float        # Angstroms
    coordinate_extent_rms_source_stats_hash: ArtifactHash
    pocket_distance_max: float              # Angstroms, or +inf if not bounded
    pocket_contact_support_min: float       # fraction, [0,1]
    atom_count_min: int
    atom_count_max: int
    graph_complexity_max: int               # edges / rings proxy
    sanitization_required: bool
    valence_rules_hash: ArtifactHash
    pair_entropy_min: float                 # bits
    pair_entropy_source_stats_hash: ArtifactHash
    projection_loss_max: float
    internal_geometry_pass_required: bool   # PoseBusters / sanitization
    evaluator_provenance_required: bool    # True unless layer explicitly diagnostic
    source_stats_hash: ArtifactHash          # manifest over training/development stats
    threshold_digest: ArtifactHash          # hash of the full threshold payload
    layer_hash: ArtifactHash                # hash of this layer's full configuration


@dataclass(frozen=True)
class FrozenEnvelopeManifest:
    manifest_id: ManifestId
    run_id: RunId
    sample_id: SampleId
    target_pocket_hash: ArtifactHash
    config_hash: ArtifactHash
    created_at_round: Literal[0]            # frozen at run start; immutable thereafter
    layers: tuple[EnvelopeLayer, ...]       # ordered K_0 subset K_1 subset ...
    empirical_only: bool                    # always True for finite cycles
    finite_prefix_only: bool                # always True for finite cycles
    tail_selection_certified: Literal[False]  # forbidden: never set, never emitted
    manifest_hash: ArtifactHash


@dataclass(frozen=True)
class EnvelopeClassification:
    bundle_id: BundleId
    matched_layer_index: int | None         # None iff unclassified complement
    complement_blocker: ComplementBlockerCode | None
    # Blockers are mutually exclusive; first match wins.
    # Valid codes:
    #   "out_of_envelope"
    #   "materialization_failure"
    #   "geometry_failure"
    #   "evaluator_provenance_missing"
    #   "lineage_invalid"
    #   "unclassified"
    within_layer_thresholds: bool           # True iff matched_layer_index is not None
    residual_extents: Mapping[str, float]   # observed vs. layer limits


@dataclass(frozen=True)
class TailBudgetRow:
    row_id: TailBudgetRowId
    manifest_id: ManifestId
    outer_cycle_id: int
    round_in_cycle: int
    target_round: int
    archive_count: int
    deduplicated_archive_count: int
    deduplicated_transfer_score_mass: float
    requested_restart_write_mass: float
    accepted_restart_write_mass: float
    unknown_complement_mass: float
    missing_evidence_mass: float
    per_layer_excess_mass: Mapping[int, float]   # layer_index -> excess
    empirical_only: bool
    finite_prefix_only: bool
    tail_selection_certified: Literal[False]     # forbidden: never set, never emitted
    ledger_hash: ArtifactHash
```

---

## 3. Channel Rule (DTB-R2)

Satisfies: `DTB-R2`, partially `DTB-NC2` (the rule carries the tail admissibility flag as
an input), partially `DTB-L1` (phase state is an input).

Pure function signature; no I/O, no mutation, no global state. The signature is declared
as a `Callable` so consumers can mock the rule in tests without inheriting a base class.

Cross-references:
- `restart_memory.adaptive_reflow_memory_restart_coords` remains the mixer primitive;
  the rule never replaces it — it only produces a `bounded_target_fraction` to feed it.
- `external_metric_feedback.adaptive_reflow_external_metric_controls` is the legacy
  heuristic that this rule replaces for the dynamic path; the heuristic survives only
  in `legacy_standalone` mode (DTB-S1).
- `noise_bias.restart_bias.noise_bias_from_metric_delta` provides the candidate ledger
  that the rule consults; it never writes the final `beta`.

Test fixture types:
- `MonotonicStabilityFixture`: increase `calibration_lower_bound` or
  `perturbation_stability_lower_bound` -> non-decreasing `beta` when others fixed.
- `MonotonicUncertaintyFixture`: increase `ambiguity` or `degeneracy_penalty` ->
  non-increasing `beta` when others fixed.
- `MissingCalibrationFixture`: `calibration_lower_bound=None` or invalid ->
  `beta=0`, `gate=False`.
- `ProxyOnlyFixture`: `proxy_only_evidence=True` -> `beta=0`.
- `SourceAgeFixture`: old source -> `recency_decay` reduces `beta`.
- `AllFactorsOneFixture`: all factors == 1 -> `beta == mixing_cap(n_cap)`.
- `TailBudgetViolationFixture`: `tail_admissibility=False` -> `beta=0`.

```python
ChannelRuleInputs = ...
ChannelRuleOutputs = ...


@dataclass(frozen=True)
class ChannelRuleInputs:
    bundle: RoundResultBundle
    evidence: ChannelTransferEvidence
    phase_state: PhaseState
    scheduled_cap: FactorValue              # from cosine / linear / constant schedule
    mixing_cap: FactorValue                 # empirically calibrated RMS-preserving map
    fresh_noise_floor: FactorValue          # per-channel floor
    delta_cap_up: FactorValue               # symmetric per-round upward cap
    delta_cap_down: FactorValue             # symmetric per-round downward cap
    tail_admissibility: bool                # from FrozenEnvelopeManifest + TailBudgetRow
    complement_excluded: bool
    frozen_envelope_manifest_hash: ArtifactHash | None
    finite_prefix_only: bool
    # All factor components must be present and in [0,1] when required.
    calibration_lower_bound: FactorValue
    perturbation_stability_lower_bound: FactorValue
    support_coverage: FactorValue
    ambiguity: FactorValue
    degeneracy_penalty: FactorValue
    recency_decay: FactorValue
    horizon_coverage_proven: bool           # from PhaseState
    selected_bundle_id: BundleId            # self-consistency with bundle


@dataclass(frozen=True)
class ChannelRuleOutputs:
    decision: ChannelTransferDecision
    monotonicity_check_passed: bool
    validation_errors: tuple[str, ...]


ChannelRule = Callable[[ChannelRuleInputs], ChannelRuleOutputs]
```

---

## 4. Cosine Restart Budget (DTB-NA1)

Satisfies: `DTB-NA1`, partially `DTB-L1` (cycle phase referenced from `PhaseState`),
partially `DTB-L4` (spectral ledger is *not* in this contract — only the schedule family
that feeds fresh-noise capacity).

Schedule family is closed: `constant`, `linear`, `cosine_no_restart`,
`cosine_guarded_restart`, and an `empirical_learned` slot reserved for future
calibration. The learned slot never becomes a default and never bypasses
`fresh_noise_floor` or any gate.

`n_cap(r) = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2`, where
`u_r = r / (L - 1)` and `L > 1`. `L == 1` is a deterministic edge case that returns
`n_max` and is exercised separately.

Cross-references:
- `restart_memory.physical_jitter_fraction` is unrelated to `fresh_noise_floor`; the
  jitter term is a per-tensor injection diagnostic, while the floor is a per-channel
  budget.
- `noise_bias.spectral_budget` consumes `CosineScheduleSample` only as a labeled input
  to its diagnostic ledger; it must never derive `beta` from it.
- `flowa_core.transport.adaptive_reflow_runtime` consumes `CosineScheduleConfig` as
  the schedule reference for the cycle; the runtime never overrides a failed gate.

Test fixture types:
- `ConstantScheduleFixture`: `family="constant"` -> capacity equal to `n_max`.
- `LinearScheduleFixture`: monotonic decrease from `n_max` to `n_min`.
- `CosineEndpointsFixture`: `r=0 -> n_max`, `r=L-1 -> n_min`.
- `CycleLengthOneFixture`: `L=1` -> deterministic edge case (returns `n_max`).
- `GateFailureFixture`: failed gate -> capacity recorded but `beta=0`.
- `WarmRestartFixture`: tail-budget violation -> new cycle, fresh prior, lineage
  recorded, prior endpoint transfer eligibility cleared.
- `DisabledCompatibilityFixture`: disabled profile keeps prior behavior.

```python
@dataclass(frozen=True)
class CosineScheduleConfig:
    schedule_family: Literal[
        "constant",
        "linear",
        "cosine_no_restart",
        "cosine_guarded_restart",
        "empirical_learned",
    ]
    cycle_length: int                       # L; must be >= 1
    n_min: FactorValue                      # [0,1]
    n_max: FactorValue                      # [0,1], n_max >= n_min
    per_channel_caps: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    symmetric_delta_caps_by_channel: Mapping[ChannelName, FactorValue]
    restart_triggers_allowed: tuple[RestartTriggerCode, ...]
    config_hash: ArtifactHash
    frozen_before_evaluation: bool          # must be True


@dataclass(frozen=True)
class CosineScheduleSample:
    schedule_hash: ArtifactHash
    outer_cycle_id: int
    round_in_cycle: int                     # r in [0, L-1]
    cycle_length: int                       # L
    n_cap: FactorValue                      # derived; n_min for r=L-1, n_max for r=0
    n_min: FactorValue
    n_max: FactorValue
    u_r: float                              # r / max(L-1, 1)
    family: str
    computed_at_round: int


@dataclass(frozen=True)
class FreshNoiseFloor:
    channel: ChannelName
    floor_value: FactorValue                # [0,1]
    source: Literal["schedule", "calibration", "manual_override"]
    config_hash: ArtifactHash


@dataclass(frozen=True)
class RestartTriggerEvent:
    trigger_id: TriggerId
    outer_cycle_id_old: int
    outer_cycle_id_new: int
    trigger_code: RestartTriggerCode
    # Valid codes:
    #   "tail_budget_violation"
    #   "complement_unclassified"
    #   "materialization_regression"
    #   "geometry_regression"
    #   "calibration_drift"
    #   "valid_evidence_no_progress"
    trigger_metric_snapshot: Mapping[str, float]
    discarded_source_bundle_ids: tuple[BundleId, ...]
    noise_capacity_before: FactorValue
    noise_capacity_after: FactorValue
    unresolved_metric_deficit: Mapping[str, float]
    provenance: ProvenanceChain
    recorded_at_round: int
```

---

## 5. Phase State (DTB-L1)

Satisfies: `DTB-L1`, partially `DTB-L2` (operation order carries a `version`), partially
`DTB-G1` (`PhaseState` is part of the public engine protocol).

`PhaseState` is the minimum required controller input; it is forbidden to reconstruct
phase from endpoint score alone. The same endpoint in different phases must produce
distinct state cache keys, and the digest is included in those keys.

Cross-references:
- `reinference_plan.build_reinference_round_plan` already has `round_index` and
  `rounds`; `PhaseState` supersedes those parameters without deleting them — the legacy
  parameters are retained as the cycle-index projection.
- `mechanism_adapter.AdaptiveReflowMechanism.condition_delta` consumes `PhaseState`
  via the `round_proxy` service.
- `external_metric_feedback` does NOT consume `PhaseState`; it remains phase-agnostic
  diagnostic feedback.

Test fixture types:
- `SameEndpointDifferentPhaseFixture`: identical endpoint, distinct `phase_state` ->
  distinct cache keys, distinct next-round controls.
- `H1CalibrationFixture`: H=1 calibration artifact rejected for H>1 policy unless
  `horizon_coverage_proven=True`.
- `AmbiguityBandFixture`: score gap <= calibrated uncertainty -> bounded unordered
  candidates, `forward_transfer_beta=0`.
- `PhaseUnknownFixture`: missing `schedule_phase` -> fail closed.
- `SeedLineageBreakFixture`: lineage digest mismatch -> reject.

```python
@dataclass(frozen=True)
class PhaseState:
    outer_cycle_id: int
    round_in_cycle: int                     # >= 0
    schedule_phase: Literal["high_noise", "anneal", "low_noise", "post_restart"]
    schedule_phase_index: int               # index into the frozen schedule family
    previous_trigger: RestartTriggerEvent | None
    operation_order_version: str            # matches OperationCompositionContract.version
    source_selector_procedure: str          # versioned name of the selection routine
    seed_lineage_digest: ArtifactHash
    horizon_remaining: int                  # > 0; 0 is a fail-closed condition
    horizon_coverage_proven: bool           # True iff artifact covers current H
    ambiguity_band_active: bool             # True iff dominance gap <= calibrated error
    phase_state_digest: ArtifactHash        # hash of all fields above
    recorded_at_round: int
```

---

## 6. Operation Composition (DTB-L2)

Satisfies: `DTB-L2`, partially `DTB-G1` (operation order is part of the public engine
protocol), partially `DTB-R5` (order version travels with the trace).

Default order (must be written into `RoundTrace`):
1. `validate` source bundle
2. `select` source bundle (deterministic over bundle id)
3. `restart_distribution` apply
4. `condition_delta` compose
5. `declared_freeze` apply (only declared write channels)
6. `native_ODE_solve` (delegated to adapter)
7. `endpoint_observation`

Unknown or missing `operation_order_version` fail closed.

Cross-references:
- `flowa_core.transport.adaptive_reflow_runtime` reads `OperationCompositionContract`
  to verify that any policy it consumes was produced under the same composition
  contract hash.
- `mechanism_adapter.AdaptiveReflowMechanism` does not itself re-order; it is the
  consumer side. Re-ordering adapters must declare their version.
- `restart_memory.adaptive_reflow_memory_restart_coords` is invoked at step 3 only.

Test fixture types:
- `DefaultOrderReplayFixture`: replay emits identical `RoundTrace` row order.
- `UnknownOrderVersionFixture`: missing version -> reject.
- `OrderReversalFixture`: synthetic AB vs BA produces different endpoints and is
  recorded distinctly in trace.
- `CommutingFixture`: known-commuting steps -> commutator-residual == 0.
- `AdapterParityFixture`: parity test binds to composition contract hash.

```python
@dataclass(frozen=True)
class OperationCompositionContract:
    version: str                            # semantic version of the contract
    operation_order: tuple[OperationStep, ...]
    default_order: tuple[OperationStep, ...] = (
        "validate",
        "select",
        "restart_distribution",
        "condition_delta",
        "declared_freeze",
        "native_ODE_solve",
        "endpoint_observation",
    )
    commutator_residual_tolerance: float    # upper bound for commuting fixture
    contract_hash: ArtifactHash

OperationStep = Literal[
    "validate",
    "select",
    "restart_distribution",
    "condition_delta",
    "declared_freeze",
    "native_ODE_solve",
    "endpoint_observation",
]


@dataclass(frozen=True)
class CommutatorResidualDiagnostic:
    contract_hash: ArtifactHash
    ab_endpoint_digest: TraceDigest
    ba_endpoint_digest: TraceDigest
    residual_norm: float
    within_tolerance: bool
    inputs_digest_ab: ArtifactHash
    inputs_digest_ba: ArtifactHash
    operation_order_version: str
    recorded_at_round: int
```

---

## 7. Writer Authority (DTB-S1)

Satisfies: `DTB-S1`, partially `DTB-R3` (single merge authority), partially `DTB-R5`
(writer id and policy hash in trace), partially `DTB-G1` (writer arbitration part of
public engine).

Three writers, mutually exclusive in executable mode:
- `noise_bias` -> stateless calculation / diagnostic provider.
- `adaptive_reflow` -> sole executable policy writer.
- `flowa_core_runtime` -> immutable `FinalRestartPolicy` consumer.

Dual-writer attempts fail closed. Legacy `noise_bias` standalone keeps a bounded
compatibility window with an explicit mode flag.

Cross-references:
- `noise_bias.mechanism_adapter.NoiseBiasMechanism` (existing) gains a `mode` field
  with values `diagnostic_only` or `legacy_standalone`. The legacy path is forbidden
  in the same run as `adaptive_reflow` unless the feature flag disables the latter.
- `flowa_core.transport.adaptive_reflow_runtime` accepts only `FinalRestartPolicy`
  byte/hash equality; it never re-derives `beta` from `noise_bias` rows or any other
  source.
- `DynamicRestartTransferLedger.writer_id` is the single source of truth for writer
  arbitration; no `max()` merge is permitted.

Test fixture types:
- `DualExecutableWriterFixture`: both `adaptive_reflow` and `noise_bias` request
  executable sampler controls in the same run -> fail closed with both ids reported.
- `DiagnosticCoexistenceFixture`: `noise_bias` in `diagnostic_only` mode -> identical
  `FinalRestartPolicy` byte/hash as without it.
- `LegacyStandaloneFixture`: `noise_bias` in `legacy_standalone` mode, `adaptive_reflow`
  disabled -> existing single-writer behavior preserved.
- `StaleWriterReplayFixture`: replay of an old writer id -> reject.
- `MissingPolicyHashFixture`: `FinalRestartPolicy` without hash -> reject.
- `MappingMergeOrderFixture`: implicit merge order changes -> reject.

```python
@dataclass(frozen=True)
class RestartPolicyAuthorityContract:
    contract_version: str
    executable_writer_id: Literal["inference.adaptive_reflow"]
    diagnostic_writer_ids: tuple[MechanismId, ...]    # noise_bias, ...
    consumer_writer_id: Literal["flowa_core_runtime"]
    mode_flags: tuple[AuthorityMode, ...]
    legacy_compatibility_window: LegacyCompatibilityWindow
    contract_hash: ArtifactHash


@dataclass(frozen=True)
class LegacyCompatibilityWindow:
    enabled: bool
    legacy_mechanism_id: MechanismId       # "inference.noise_bias"
    legacy_mode: Literal["legacy_standalone"]
    exclusive_with: tuple[MechanismId, ...]   # must be empty when enabled
    schema_read_compatibility_version: str
    writes_sampler_controls: Literal[False]    # always False under this contract


@dataclass(frozen=True)
class FinalRestartPolicy:
    policy_id: PolicyId
    writer_id: MechanismId                  # "inference.adaptive_reflow"
    run_id: RunId
    target_round: int
    outer_cycle_id: int
    beta_by_channel: Mapping[ChannelName, FactorValue]
    alpha_by_channel: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    schedule_sample: CosineScheduleSample | None
    freeze_admission_by_channel: Mapping[ChannelName, bool]
    ledger_row_id: LedgerRowId
    policy_hash: ArtifactHash
    created_at_round: int


AuthorityMode = Literal[
    "noise_bias_diagnostic_only",
    "noise_bias_legacy_standalone",
    "adaptive_reflow_executable",
    "flowa_core_consumer",
]
```

---

## Cross-Contract Invariants

These are the load-bearing invariants the contracts above collectively enforce; they
are repeated here because no individual contract owns them.

- `empirical_only=True` and `finite_prefix_only=True` on every `FrozenEnvelopeManifest`
  and every `TailBudgetRow`. The literal field `tail_selection_certified` exists with
  type `Literal[False]` and is never set to `True` in any code path.
- A `DynamicRestartTransferLedger` row that is missing `calibration_artifact_hash`,
  has non-finite values, has `condition_digest` mismatch, or has `feedback_mode ==
  "proxy_only"` together with a non-zero `beta` is invalid and must fail closed.
- `FinalRestartPolicy.beta_by_channel` keys must equal
  `DynamicRestartTransferLedger.beta_by_channel` keys; byte/hash equality is verified at
  the `flowa_core_runtime` boundary.
- `operation_order_version` is required on every `PhaseState`, every
  `CommutatorResidualDiagnostic`, and every `DynamicRestartTransferLedger`. Mismatch
  fails closed.
- `RoundResultBundle.coordinate_channel`, `charge_channel`, `raw_pair_channel`, and
  `projected_pair_channel` all derive from the same `source_round`. A mix of source
  rounds across channels in one bundle is rejected.
