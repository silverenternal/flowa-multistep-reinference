---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 4. Engine seven-step operation order

## Context and Problem Statement

`adaptive_reflow.frame.engine.Engine.run_round` is a 7-step operation.
The canonical order is captured as a tuple constant:

```
DEFAULT_OPERATION_STEPS = (
    "capabilities_handshake",
    "build_initial_state",
    "apply_restart_distribution",
    "compose_condition",
    "solve_ode",
    "observe_endpoint",
    "detach_and_validate_endpoint",
)
```

The order is load-bearing: each step assumes the previous step's
output is well-formed, and the round trace produced at the end is the
canonical record of *what* was called and in *what* order. Reordering
a step silently breaks the trace contract, the
`OperationCompositionContract.operation_order_version`, and every
golden replay test.

## Decision Drivers

* The operation order is part of the public surface: it appears in
  `EngineRoundResult.round_trace_v3.operation_order`, in
  `OperationCompositionContract.version`, and in the kernel
  benchmarks under `tests/perf/`.
* The order is also a *correctness* invariant: stepping past
  `compose_condition` before `apply_restart_distribution` would mean
  the ODE condition delta was applied to a non-restarted state, which
  is not what the engine is supposed to do.
* The seven steps are not negotiable as a *set* — every step exists
  for a documented reason. The order between them is the question.

## Considered Options

1. **Fix the 7-step order as a constant; changes require a new ADR.**
2. **Make the order pluggable.** Each adapter author supplies their
   own step list. Rejected because the round trace contract would
   then be adapter-dependent and the trace v3 content hash would not
   be comparable across adapters.
3. **Drop the canonical order entirely; rely on docstrings.** Rejected
   because the trace and the contract both consume the tuple.

## Decision Outcome

Chosen option: **The seven-step order is fixed and is the single
canonical order. Changing it requires a new ADR that names the new
step, the new position, and the migration path for every existing
golden and benchmark.**

The tuple `DEFAULT_OPERATION_STEPS` lives in
`adaptive_reflow/frame/engine.py` and is re-exported as
`adaptive_reflow.frame.DEFAULT_OPERATION_STEPS`. The
`OperationCompositionContract.version` constant
(`DEFAULT_OPERATION_COMPOSITION_VERSION`) is bumped in the same
commit that introduces the new order.

### Consequences

Positive:

* The round trace is comparable across runs and across adapters — the
  `operation_order` field is always one of the seven canonical names.
* The kernel benchmark under `tests/perf/` has a stable call graph.
* The doc scanner can resolve every reference to the seven step names
  to a real symbol or a documented literal.

Negative:

* A future operation that does not fit the seven steps must either be
  appended (requires an ADR) or implemented *within* an existing step
  (requires documenting the new sub-step in the step's docstring).
* The `operation_order_version` constant is a public migration marker;
  bumping it is a breaking change for any consumer that compares the
  string directly.

### Confirmation

The decision is confirmed when:

* `tests/test_frame/test_engine.py` asserts the literal value of
  `DEFAULT_OPERATION_STEPS` (a tuple-equality test).
* A property test (when added) asserts that `replay_default_order`
  produces the same step names in the same order.
* The bench budget for `engine_round_loop` references the seven-step
  sequence by name (see `docs/PERFORMANCE_BUDGETS.md`).

## More Information

* [ARCHITECTURE.md §5.5](../../ARCHITECTURE.md) — the
  per-round contract that the seven steps implement.
* [docs/PERFORMANCE_BUDGETS.md](../PERFORMANCE_BUDGETS.md) — the
  `engine_round_loop_us_p95` budget that gates the seven-step call
  graph.
* `adaptive_reflow/frame/engine.py::DEFAULT_OPERATION_STEPS` — the
  pinned tuple constant.
* `adaptive_reflow/contracts/operations.py::OperationCompositionContract`
  — the migration marker that bumps when the order changes.

## Related Future ADRs

* **ADR-0008 (planned)** — *Claim-gate deferral placeholder.* The
  DTB-R8 claim gate's structural evaluator currently always returns
  ``"defer"`` (see `adaptive_reflow/eval/claim_gate.py`). The
  promote/rollback branches depend on R7 GPU data which has not
  landed yet. The future ADR will author the R7 wiring for the
  module-level ``_resolve_decision(passed, failed) -> ClaimGateDecision``
  helper, which is exposed today precisely so that R7 wiring becomes a
  one-line body replacement rather than a public-surface change.