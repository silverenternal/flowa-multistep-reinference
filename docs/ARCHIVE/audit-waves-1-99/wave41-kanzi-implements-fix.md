# Wave 41 Agent A — KanziAdapter `@implements` 1-line fix

**Date:** 2026-09-05
**Agent:** Wave 41 Agent A
**Scope:** `adaptive_reflow/adapters/kanzi.py`, `tests/test_adapters/test_kanzi.py`
**Constraint:** disjoint file scope — no touch of framework/, scheduler/, paper_quantities, regression-vectors, test_claims, other adapters

## Background

The Wave 32 framework code review (`docs/audit/framework-code-review.md`
§1.13, finding **MEDIUM-11**) requires every registered adapter to
declare its Protocol surface via the `@implements(...)` class decorator
so that `assert_adapter_compliance()` can walk `__protocols__` and
enforce structural typing. Wave 38 Agent A (commit `f7ee3ae`) added the
CI test that enforces this for every registered family.

The Wave 39 Agent B regression check (commit `fb652bb6`, READ-ONLY
audit) found `KanziAdapter` missing the `@implements(FlowMatchingODEAdapter)`
decorator on the class declaration. Every other registered adapter
(`flowmol3.py`, `toy_gaussian.py`, `freqflow.py`, `graphbfn.py`,
`wan2_2_video.py`, `hidream_i1.py`, `lineageflow.py`,
`rectified_flow_cifar.py`, `toy_linear.py`, `mnist_fm.py`,
`protbfn_abbfn_adapter.py`, `lumina_image_2_0.py`, `flowmol3_v2_adapter.py`,
`twodim_fm.py`, `self_flow.py`) carries the decorator. Kanzi was the
lone straggler.

## Fix (1 line + import)

**File:** `adaptive_reflow/adapters/kanzi.py`

Added `from adaptive_reflow.framework.interfaces import implements`
to the import block (line 131), then added the decorator above the
class declaration:

```python
@implements(FlowMatchingODEAdapter)
class KanziAdapter(FlowMatchingODEAdapter):
    ...
```

This matches the pattern used in `flowmol3.py` (line 70 import, line 282
decorator) — the canonical reference adapter.

## Regression tests (3 added)

**File:** `tests/test_adapters/test_kanzi.py`

1. **`test_kanzi_adapter_declares_implements_decorator`** — the
   trip-wire test. Checks `KanziAdapter.__protocols__` includes
   `FlowMatchingODEAdapter` and `isinstance(KanziAdapter,
   FlowMatchingODEAdapter)` passes the structural check. If a future
   edit removes the decorator, this test fails immediately.
2. **`test_kanzi_adapter_default_factory_carries_implements`** — the
   default-factory path. Confirms `default_kanzi_adapter()` instances
   inherit the decorator's protocol set (decorators on a class apply
   to every instance).
3. **`test_kanzi_adapter_passes_assert_adapter_compliance`** — the
   end-to-end check. Mirrors the CI gate in
   `tests/test_framework/test_assert_adapter_compliance.py` so a
   KanziAdapter-specific regression surfaces locally before the
   registry sweep catches it.

## MEDIUM-11 gate — PASSES

The decorator now satisfies the `assert_adapter_compliance()` CI gate
for `KanziAdapter` (also asserted locally by the third regression test
above). The registry-level check at
`tests/test_framework/test_assert_adapter_compliance.py` covers
Kanzi via the registered-family loop.

## Verify

```
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_kanzi.py \
    tests/test_framework/test_assert_adapter_compliance.py \
    -q --tb=line

48 passed, 6 skipped, 3 warnings in 28.55s
```

- **6 env-skips** are pre-existing (kanzi package not installed in
  this venv for 3 tests, mnist_fm weights missing, wan2_2 dependency
  missing) — not regressions.
- **3 new regression tests** (`test_kanzi_adapter_declares_implements_decorator`,
  `test_kanzi_adapter_default_factory_carries_implements`,
  `test_kanzi_adapter_passes_assert_adapter_compliance`) all PASS.

## Out-of-scope confirmation

- `framework/` — untouched
- `scheduler/` — untouched
- `paper_quantities` — untouched
- `regression-vectors` — untouched
- `test_claims` — untouched
- Other adapters — untouched

## Status

FIXED. MEDIUM-11 gate PASSES for KanziAdapter. No push (per Wave 41
directive: commit only).
