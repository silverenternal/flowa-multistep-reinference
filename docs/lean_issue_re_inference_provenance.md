# Lean issue: per-round provenance and condition-trace evidence (DTB-R5)

This is a **minimal** Lean architecture/source-covenant change request. It is
explicitly **not** a claim about empirical drug efficacy, molecular docking
quality, or any dynamic-weight performance result.

## Scope

Two source modules need a third clause added to their existing architecture
contract:

1. `flowa_iterative_ode.conditionTrace_v3` (new module under
   `FlowA.IterativeODE`)
2. `pocket_modules.mechanisms.inference.adaptive_reflow.trace_schema` (Python
   mirror)

The Lean change is purely a contract addendum:

* **Schema name**: `flowa_iterative_ode_condition_trace_schema_v3` (paired
  with a frozen legacy reader for the existing v2 schema).
* **Closed carrier**: the v3 trace must contain exactly the documented field
  set. Any addition requires a new schema name and a new reader.
* **Hash determinism**: the trace carries a content hash that is stable
  across process restarts and Python versions.

## What the contract guarantees

| Contract line                                  | Guarantee                                                                              |
|------------------------------------------------|----------------------------------------------------------------------------------------|
| `RoundTraceV3` is `frozen`                     | Immutable after emission; the orchestrator cannot mutate a written trace.             |
| `final_policy_writer` is single-valued         | At most one executable writer is recorded per round; legacy-only runs name `noise_bias`.|
| Two executable writers cannot coexist          | `validate_round_trace_v3` rejects rows that attempt to declare both.                   |
| `per_factor_raw` / `per_factor_bounded` exist  | The trace is the *only* place where the pre/post calibration split lives.             |
| `content_hash` is recomputable                  | A separate consumer (audit, replay, diff) can verify reproducibility offline.          |
| v2 reader remains available                    | Legacy `flowa_iterative_ode_condition_trace_schema_v2` payloads still parse cleanly.   |

## What this contract does **not** claim

* This change does **not** assert any empirical drug efficacy. It is a
  provenance / reproducibility contract only.
* This change does **not** claim that any dynamic-weight schedule
  outperforms a constant-weight schedule. Performance comparisons are out of
  scope for DTB-R5.
* This change does **not** alter the dual-writer arbitration policy; it only
  records the result of that arbitration inside the trace.

## Required Lean changes (architecture/source covenant only)

1. **New module**: `FlowA.IterativeODE.ConditionTrace.V3`
   * `RoundTraceV3 : Type` — frozen record with the documented field set.
   * `computeRoundTraceV3ContentHash : RoundTraceV3 → String` — deterministic.
   * `roundTripRoundTraceV3 : RoundTraceV3 → Except String RoundTraceV3`.
   * `readRoundTraceV2 : Json → Except String Json` — v2-only reader.

2. **Carrier additions** in `PocketModules.Mechanisms.Inference.AdaptiveReflow.Types`:
   * `NoiseBiasInputRow` (frozen record).
   * `DynamicRestartTransferLedger` gains a `ledger_version : String` field
     (default `"v3"`).

3. **Plan carrier bump** in `PocketModules.Mechanisms.Inference.AdaptiveReflow.ReinferencePlan`:
   * `REINFERENCE_ROUND_PLAN_SCHEMA_VERSION` advanced to
     `"adaptive_reflow_metric_aware_round_plan_v2"`.
   * `read_round_plan_v1` retained for legacy readers.
   * `build_reinference_round_plan` now accepts a `ledger_row` and embeds it
     into `condition_delta` so that a single round's `beta_by_channel` is
     reproducible from a single ledger row.

## Acceptance gate

A round trace is **runtime-valid** if and only if all of the following hold:

* Every required field is non-`None`.
* Every numeric value is finite.
* The embedded `content_hash` matches the recomputed digest.
* The condition (`condition_delta`) is unchanged-or-rewritten; partial
  rewriting is rejected.

If any of these fail, the runtime write to the
`DynamicRestartTransferLedger` is refused.

## Non-goals

This change does not touch:

* The cosine schedule (`CosineScheduleConfig`).
* The phase state machine (`PhaseState`).
* The operation order contract (`OperationCompositionContract`).
* The envelope ladder (`FrozenEnvelopeManifest`).

Those modules already have their own contracts and are not modified by
DTB-R5.