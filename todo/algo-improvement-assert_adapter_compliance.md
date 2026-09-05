# Algorithm improvement — assert_adapter_compliance enforcement (HIGH-4 + MEDIUM-11)

**Status:** CLOSED in Wave 38 (commit f7ee3ae, Wave 38 Agent A WF1) — HIGH-4 + MEDIUM-11 closed: explicit warning on non-runtime Protocol + @implements discipline on every registered adapter + CI enforcement test parametrised over ADAPTER_REGISTRY
**Date:** 2026-09-05
**Priority:** high (framework Protocol conformance currently unenforced)
**Depends on:** Wave 11 Phase 2 (Protocol surfaces declared)
**Owner:** framework maintainer
**Wave:** Wave 33 (target)
**Goal:** enforce Protocol conformance via `@implements(...)` decorator
on every registered adapter + add a CI test that calls
`assert_adapter_compliance` for each adapter. Closes the Wave 11
Phase 3 "Shrink adapters" follow-up gap (task #344) at the
**conformance-enforcement** level (the shrinking itself is D.1, gated
on framework-core glue).

## Background

Per Wave 32 Agent C (`docs/audit/framework-code-review.md` §1.13):

### HIGH-4: `assert_adapter_compliance` silently skips non-`runtime_checkable` Protocols

> `assert_adapter_compliance` checks
> `getattr(protocol, "_is_runtime_protocol", False)` to identify
> runtime-checkable Protocols (line 511).
>
> **But** the standard library `typing.Protocol` does NOT set
> `_is_runtime_protocol` — this attribute is set by `runtime_checkable`
> only on the *class* that was decorated. All 12 Protocols in this
> file ARE decorated, so the gate works.
>
> **BUT** the gate silently skips any Protocol that is NOT decorated
> (line 514 `continue`), so a future contributor adding a
> `@runtime` (not `@runtime_checkable`) decorator would get a
> silent pass-through.
>
> **Fix**: add an explicit warning when a non-runtime Protocol is
> declared.

### MEDIUM-11: No adapter uses `@implements(...)`

> No adapter in the repo uses `@implements(...)`. The decorator is
> declared in the docstring but only the *example* uses it; no concrete
> adapter passes `assert_adapter_compliance`.
>
> This means the framework's Protocol conformance is *not enforced* —
> adapters may silently violate the Protocol surface.
>
> **Fix**: Wave 32 follow-up — declare conformance on every adapter and
> add a CI test that calls `assert_adapter_compliance` per adapter.

## What to do

### Phase A — HIGH-4 fix (small)

1. **Read `adaptive_reflow/framework/interfaces.py`** to find the
   `assert_adapter_compliance` function (around line 511)
2. **Add an explicit warning** when a non-runtime Protocol is declared:
   ```python
   for protocol in declared_protocols:
       if not getattr(protocol, "_is_runtime_protocol", False):
           warnings.warn(
               f"Protocol {protocol.__name__} is not @runtime_checkable; "
               f"assert_adapter_compliance will silently skip it. "
               f"Add @runtime_checkable decorator to enforce conformance.",
               RuntimeWarning,
               stacklevel=2,
           )
           continue
       # ... existing check ...
   ```
3. **Add a regression test** in `tests/test_framework/test_assert_adapter_compliance.py`:
   ```python
   def test_assert_adapter_compliance_warns_on_non_runtime_protocol():
       """HIGH-4 fix: explicit warning when a non-runtime Protocol is declared."""
       class NonRuntimeProtocol(Protocol):
           def foo(self) -> None: ...
       with pytest.warns(RuntimeWarning, match=r"NonRuntimeProtocol is not @runtime_checkable"):
           assert_adapter_compliance(MockAdapter(), [NonRuntimeProtocol])
   ```

### Phase B — MEDIUM-11 fix (lightweight @implements discipline)

**Decision**: add `@implements(<smallest relevant Protocol>)` to every
registered adapter (1 decorator per adapter; matches scikit-learn
`check_estimator` pattern of "1 protocol = 1 conformance check").

1. **Enumerate the 18 registered adapters** (per
   `adaptive_reflow/adapters/__init__.py` `ADAPTER_REGISTRY`)

2. **For each adapter, identify the smallest relevant Protocol**:
   - `FlowMatchingODEAdapter` (D.2 verified) — for all ODE-style adapters
   - `ChannelwiseBlender` — for adapters that support restart_blend
   - `BatchedVectorisedAdapterProtocol` — for adapters that support batched trajectory
   - etc.

3. **Add `@implements(...)` decorator** to each adapter class definition:
   ```python
   @implements(FlowMatchingODEAdapter)
   @implements(ChannelwiseBlender)  # if applicable
   class FlowMol3V2Adapter(...):
       ...
   ```

4. **Verify each adapter still passes `assert_adapter_compliance`**

### Phase C — CI test (the core enforcement)

1. **Author `tests/test_framework/test_adapter_protocol_enforcement.py`**:
   ```python
   """CI gate: every registered adapter passes assert_adapter_compliance."""
   import pytest
   from adaptive_reflow.adapters import ADAPTER_REGISTRY
   from adaptive_reflow.framework.interfaces import assert_adapter_compliance

   @pytest.mark.deterministic
   @pytest.mark.parametrize("adapter_name,adapter_factory",
                            list(ADAPTER_REGISTRY.items()))
   def test_every_adapter_passes_assert_adapter_compliance(adapter_name, adapter_factory):
       adapter = adapter_factory(seed=0)  # if factory; else instantiate
       assert_adapter_compliance(adapter)  # raises if any Protocol violated
   ```

2. **Verify the test fails** if any adapter violates a declared Protocol
   (negative test — temporarily remove a `@implements` from one adapter
   and confirm the test fails)

3. **Add the test to `.github/workflows/cpu-tests.yml`** as part of the
   existing protocol-conformance job

### Phase D — Verification + docs

1. **Run `pytest tests/test_framework/test_adapter_protocol_enforcement.py -v`** —
   all 18 adapters pass
2. **Run `pytest tests/ -v --timeout=60`** — no regression
3. **Run `python tools/capability_audit.py`** — no gate regression
4. **Update `docs/audit/framework-code-review.md` §1.13** — mark HIGH-4
   + MEDIUM-11 as RESOLVED
5. **Update `docs/baseline-audit-report.md`** if applicable
6. **Update `framework-internal-metrics.md` §1 D.3** if D.3 metric text
   should reference the new enforcement test

## Files affected

- `adaptive_reflow/framework/interfaces.py` (UPDATE; ~10 LOC for HIGH-4 fix)
- `adaptive_reflow/adapters/*.py` (UPDATE × 18 files; 1-2 LOC each for MEDIUM-11 fix)
- `tests/test_framework/test_assert_adapter_compliance.py` (NEW)
- `tests/test_framework/test_adapter_protocol_enforcement.py` (NEW)
- `.github/workflows/cpu-tests.yml` (UPDATE; add new test to CI)
- `docs/audit/framework-code-review.md` §1.13 (UPDATE; mark 2 issues RESOLVED)
- `docs/baseline-audit-report.md` (UPDATE if applicable)

## Acceptance

- [ ] HIGH-4 fix: explicit warning on non-runtime Protocol
- [ ] MEDIUM-11 fix: `@implements(...)` on every registered adapter
- [ ] 2 new test files authored; CI test parametrised over 18 adapters
- [ ] All 18 adapters pass `assert_adapter_compliance`
- [ ] `pytest tests/` still passes (no regression)
- [ ] `python tools/capability_audit.py` still passes (no gate regression)
- [ ] CI workflow runs the new test on every PR
- [ ] `docs/audit/framework-code-review.md` §1.13 marks 2 issues RESOLVED

## Acceptance gate

Passes if:
1. The CI test fails when an adapter silently violates a declared Protocol
2. All 18 registered adapters pass `assert_adapter_compliance`
3. No regression in the full test suite

## Estimated time

~1-2 hours total (HIGH-4 fix + MEDIUM-11 sweep + CI test + verification).

## Risk

- **MEDIUM**: an adapter may currently violate a Protocol that it
  implicitly relies on; adding `@implements` would expose the violation
  → **Mitigation**: add `@implements` to one adapter at a time, verify
  pass, then move to the next
- **LOW**: some adapters may have non-trivial Protocol violations (e.g.
  missing method) that require code changes to fix
  → **Mitigation**: each exposed violation gets a follow-up issue;
  expect 1-3 adapter fixes in Wave 33

## Related fix opportunities (within scope of this PR)

Per `docs/audit/framework-code-review.md` §1.13:
- LOW-23: `emit_theorem1_statement` does not call `validate_f_side` —
  doc-only update (include in this PR)
- LOW-24: `PosteriorEvaluator.nu_g_density` Protocol declared but no
  consumer — remove or document (decision: document the intended
  consumer; defer removal)

Per `docs/audit/framework-code-review.md` §2.4:
- The full D.1 "Shrink adapters" gap (task #344) is **not** in scope here;
  that's a separate plan (gated on MUST-3 framework-core glue)
## Wave 38 close-out

CLOSED in Wave 38 by commit **f7ee3ae** (Wave 38 Agent A WF1).

**Result summary**:
- HIGH-4 closed: explicit `RuntimeWarning` when `assert_adapter_compliance` is invoked with a Protocol that is not decorated with `@runtime_checkable` (silent-skip path removed)
- MEDIUM-11 closed: `@implements(<smallest relevant Protocol>)` decorator discipline applied across the registered adapter set (Phase B sweep)
- Phase C CI test shipped in `tests/test_framework/test_adapter_protocol_enforcement.py`, parametrised over `ADAPTER_REGISTRY` so every registered adapter is exercised by the enforcement gate

**Files shipped** (see `git show --stat f7ee3ae` for the canonical list): enforcement-warning path in `adaptive_reflow/framework/interfaces.py`, `@implements` decorators across `adaptive_reflow/adapters/*.py`, two new test files, CI workflow wiring.

**Verification**: pytest + mkdocs build --strict run + commit (no push). Wave 38 dispatched 5 parallel workflows; this plan was Wave 38 Agent A WF1. Plan status flipped from `pending (Wave 33 target)` to CLOSED.

Refs: `docs/audit/framework-code-review.md` §1.13 (HIGH-4 + MEDIUM-11 now RESOLVED).
