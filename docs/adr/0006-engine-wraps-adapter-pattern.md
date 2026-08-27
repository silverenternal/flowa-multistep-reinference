---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 6. Engine-wraps-adapter pattern

## Context and Problem Statement

`adaptive_reflow.frame.engine.Engine.run_round` drives a Flow Matching
ODE round against a `FlowMatchingODEAdapter`. The adapter is an
author-supplied object that may be a toy, a research prototype, or a
production wrapper around a real ODE integrator. Before the gap
closure, a misbehaving adapter — one whose method raises an
`Exception` partway through the seven-step operation order — would
propagate the exception out of `run_round`, dropping the round and
the ledger row on the floor. The engine's *contract* is to emit a
fail-closed `EngineRoundResult` for *every* round so the ledger and
the audit trail are never silently truncated.

The risk is also asymmetric: an adapter exception on step 5
(`solve_ode`) is fundamentally different from one on step 7
(`detach_and_validate_endpoint`). A bare `except Exception` swallows
both without naming the step, and a bare `except BaseException`
swallows `KeyboardInterrupt` and `SystemExit`, which would make the
engine unresponsive to operator intervention.

The decision answers two questions:

1. **Where** does the wrapper live? (single helper inside
   `frame/engine.py`.)
2. **What** is the rejection criterion for log-emission? (the wrapper
   catches `Exception` — never `BaseException` — and emits
   `ERR_ADAPTER_RAISED` with a deterministic, forensic payload.)

## Decision Drivers

* `Engine.run_round` must always return an `EngineRoundResult`; an
  unhandled adapter exception would break the ledger and the audit
  trail in a way the downstream consumer cannot recover from.
* The audit code must be deterministic and parseable: the same
  exception must always produce the same audit-code string so the
  docs scanner, the adversarial tests, and the writer can replay it.
* The seven-step operation order is pinned by
  [ADR-0004](0004-engine-seven-step-operation-order.md); each step
  must appear in the audit payload so a downstream reader can locate
  the failure within the order without consulting the call site.
* The audit-code policy is pinned by
  [ADR-0005](0005-fail-closed-audit-code-policy.md); the new code is
  added to the engine's `__all__` and re-exported in
  `frame/__init__.py`.

## Considered Options

1. **Single `_safe_adapter_call` helper inside `frame/engine.py` that
   wraps every adapter invocation in `try/except Exception`.** The
   helper appends
   ``f"{ERR_ADAPTER_RAISED}:{step_name}:{ExcType}:{message[:80]}"``
   to the audit trail and returns `None` on failure.
2. **Per-step wrappers** (`_safe_build_initial_state`, `_safe_solve_ode`,
   ...). Rejected because the seven wrappers would each carry the
   same `try/except` boilerplate and the audit-code string would have
   to be assembled in seven places.
3. **Decorator (`@safe_adapter_call`)** applied to thin
   `Engine.run_round` sub-methods. Rejected because the wrapper must
   thread `audit_codes` *through* the call; a decorator that hides
   the threading is a foot-gun for future maintainers.

## Decision Outcome

Chosen option: **single `_safe_adapter_call` helper inside
`frame/engine.py`**, invoked at every adapter call site inside
`run_round`. The helper signature is:

```
def _safe_adapter_call(
    step_name: str,
    audit_codes: list[str],
    fn: Any,
    *args: Any,
    **kwargs: Any,
) -> Any
```

The rejection criterion is:

* `try: return fn(*args, **kwargs)`
* `except Exception as exc:` — **never** `except BaseException`.
  `KeyboardInterrupt` / `SystemExit` must still propagate.
* Append
  ``f"{ERR_ADAPTER_RAISED}:{step_name}:{type(exc).__name__}:{str(exc)[:80]}"``
  to `audit_codes`.
* Return `None`.

The call sites in the seven-step operation order are:

1. `build_initial_state`
2. `apply_restart_distribution`
3. `compose_condition`
4. `solve_ode`
5. `observe_endpoint`
6. `export_endpoint` (sub-step of `detach_and_validate_endpoint`)
7. `detach_and_validate_endpoint`

The `capabilities_handshake` step is *not* wrapped: it uses
`Engine.handshake(adapter)` directly and raises
`CapabilityMissingError` / `CapabilityMismatchError` / `RuntimeError`,
which the engine already converts into `ERR_CAPABILITIES_INVALID`
codes (see ADR-0005). Wrapping the handshake would mask a
*contract* failure as an *adapter-raised* failure, which would defeat
the diagnostic.

### Consequences

Positive:

* An adapter that crashes mid-round can never crash the engine; the
  ledger row is still emitted and the round trace still carries the
  `ERR_ADAPTER_RAISED` payload.
* The seven-step operation order is preserved verbatim (ADR-0004);
  the wrapper does not change step names or order.
* The audit-code policy is preserved (ADR-0005); the new code is
  added to the catalogue and the re-export layer.
* The forensic payload (step, exception type, message prefix) makes
  it trivial to triage failures: the writer can grep
  `ERR_ADAPTER_RAISED:solve_ode:` and find every ODE-integration
  failure across all adapters.

Negative:

* The 80-character message prefix truncates long error messages. The
  prefix is deliberately short so the audit trail stays bounded; the
  full message remains accessible to the caller via the engine's
  `extras` field when wired up by the orchestrator.
* `BaseException`-derived errors (other than `Exception`) propagate.
  In particular, `MemoryError` will still crash the engine. This is
  intentional: silently swallowing `MemoryError` would hide a real
  resource exhaustion from the operator.

### Confirmation

The decision is enforced by:

* The seven `_safe_adapter_call` invocations in
  `adaptive_reflow/frame/engine.py::Engine.run_round` — every adapter
  call must be wrapped, and the `step_name` argument must be one of
  the seven canonical names.
* The `tests/test_frame/test_engine.py` adversarial cases that assert
  `ERR_ADAPTER_RAISED:build_initial_state:RuntimeError:...` (and the
  other six) is reachable.
* `tools/check_docs_against_code.py` — every reference to
  `ERR_ADAPTER_RAISED` and `_safe_adapter_call` in the docs
  resolves to a real symbol.

## More Information

* [docs/adr/0004](0004-engine-seven-step-operation-order.md) —
  the seven-step operation order that the wrapper threads through.
* [docs/adr/0005](0005-fail-closed-audit-code-policy.md) — the
  audit-code catalogue that lists `ERR_ADAPTER_RAISED`.
* `adaptive_reflow/frame/engine.py::_safe_adapter_call` — the
  helper.
* `adaptive_reflow/frame/engine.py::Engine.run_round` — the seven
  call sites.