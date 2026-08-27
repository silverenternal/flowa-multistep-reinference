# `adaptive_reflow.contracts`

Pure-stdlib typed contracts: dataclasses, `NewType` aliases, hash
helpers, validators. The leaf of the dependency graph; nothing inside
`adaptive_reflow.contracts` imports from any other `adaptive_reflow`
subpackage.

The page below drills into each split file inside the `contracts`
subpackage rather than stopping at the top-level `__init__.py`
re-exports, so internal symbols (audit-code sentinels, error-class
strings, frozen-hash constants) that are not re-exported publicly still
show up in the rendered reference.

## `adaptive_reflow.contracts.bundle`

Atomic source bundle: `RoundResultBundle` + per-channel source-round
validator. Hosts the lazy `__getattr__` re-export shim that breaks the
import cycle with `molecular.bundle`.

::: adaptive_reflow.contracts.bundle
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.decision`

Channel-decision dataclasses + audit-code sentinels used by the
`frame.channel_rule` gate.

::: adaptive_reflow.contracts.decision
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.envelope`

Runtime envelope dataclasses: `EnvelopeLayer`, `EnvelopeManifest`,
`TailBudgetAccumulator`. Pure data, stdlib-only.

::: adaptive_reflow.contracts.envelope
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.schedule`

Cosine / linear / constant outer-restart-noise schedule
(`CosineScheduleSample`, `CosineScheduleParams`).

::: adaptive_reflow.contracts.schedule
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.phase`

`PhaseState` dataclass + phase-transition validator. The contracts
version of `PhaseState` is the leaf; the `frame.phase` module re-exports
the universal helpers that operate on it.

::: adaptive_reflow.contracts.phase
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.operations`

Operation composition dataclasses: `OperationStep`,
`OperationCompositionContract`, `CommutatorResidual`.

::: adaptive_reflow.contracts.operations
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.authority`

Final-policy writer authority + audit sentinels (DTB-S1, DTB-G2).

::: adaptive_reflow.contracts.authority
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.archive`

Archive-round dataclasses + pruning sentinels (DTB-R4).

::: adaptive_reflow.contracts.archive
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.types`

`NewType` aliases shared across the contracts subpackage: `ChannelName`,
`ChannelDomain`, `Predicate`, `ArtifactHash`, `BundleId`, etc.

::: adaptive_reflow.contracts.types
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.hashes`

Content-hash helpers (`canonical_fnv1a_hash`, `compute_round_trace_v3_content_hash`,
etc.) used to freeze the manifests and round-trace payloads.

::: adaptive_reflow.contracts.hashes
    options:
      members: true
      show_source: true

## `adaptive_reflow.contracts.validators`

Pure validation helpers (fail-closed): `validate_round_result_bundle`,
`validate_phase_state_transition`, and friends. The single entry point
for contracts-layer invariants.

::: adaptive_reflow.contracts.validators
    options:
      members: true
      show_source: true