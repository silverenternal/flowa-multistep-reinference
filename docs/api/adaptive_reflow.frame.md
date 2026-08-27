# `adaptive_reflow.frame`

The universal round frame: engine driver + bounded merge + channel
rule + operation order + phase transitions + round-trace v3 +
orchestrator. Owns the public `Engine` and `AdaptiveReflowPolicyOrchestrator`
entry points.

The page below drills into each split file inside the `frame` subpackage
rather than stopping at the top-level `__init__.py` re-exports, so
internal symbols (helper functions, error sentinels, schema constants)
that are not re-exported publicly still show up in the rendered
reference.

## `adaptive_reflow.frame.merge`

Bounded merge authority (DTB-R3) -- symmetric, capped, floor-aware merge
of a previous-round fraction and a dynamic evidence-derived fraction.

::: adaptive_reflow.frame.merge
    options:
      members: true
      show_source: true

## `adaptive_reflow.frame.engine`

Engine driver -- the seven-step default operation order, ledger row
emission, phase-state plumbing, and the round-trace v2 → v3 migration.

::: adaptive_reflow.frame.engine
    options:
      members: true
      show_source: true

## `adaptive_reflow.frame.channel_rule`

Per-channel decision + audit code catalogue (DTB-R0 §3 hostile cases 2
and 5). Hosts `AUDIT_STABILITY_COLLAPSE`, `AUDIT_SOURCE_REVOKED`, and
the seven `BLOCKER_*` codes.

::: adaptive_reflow.frame.channel_rule
    options:
      members: true
      show_source: true

## `adaptive_reflow.frame.adapter`

The thin re-export shim over `adaptive_reflow.universal.adapter`. Kept
under the historical import path (`from adaptive_reflow.frame import
FlowMatchingODEAdapter`) so legacy callers do not break.

::: adaptive_reflow.frame.adapter
    options:
      members: true
      show_source: true

## `adaptive_reflow.frame.orchestrator`

`AdaptiveReflowPolicyOrchestrator` -- the public orchestrator entry
point that wires the engine + bounded merge + channel rule + phase
transitions together.

::: adaptive_reflow.frame.orchestrator
    options:
      members: true
      show_source: true

## `adaptive_reflow.frame.operation`

Default operation composition contract + commutator residual
recorder. Hosts the `validate_operation_order` gate.

::: adaptive_reflow.frame.operation
    options:
      members: true
      show_source: true

## `adaptive_reflow.frame.phase`

Phase-state dataclass + transition validator. Hosts the
`advance_phase` and `validate_phase_state_transition` helpers.

::: adaptive_reflow.frame.phase
    options:
      members: true
      show_source: true

## `adaptive_reflow.frame.trace`

Round-trace v3 schema -- the frozen `RoundTraceV3` dataclass, the
schema-name / schema-version sentinels, and the `read_round_trace_v2`
back-compat migration.

::: adaptive_reflow.frame.trace
    options:
      members: true
      show_source: true