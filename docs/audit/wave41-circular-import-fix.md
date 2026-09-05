# Wave 41 Agent C — test_algo_uplifts Circular Import Fix

**Date:** 2026-09-05
**Agent:** Wave 41 Agent C
**Host Python:** `.venvs/flowmol3_venv/bin/python` (CPython 3.12.13)
**Mode:** code-only, NO GPU

---

## 1. Goal

Resolve the pre-existing **collection-time circular import** that blocks
`tests/test_algo_uplifts/` from running. The 36-uplift isolation suite
(Wave 14 C deliverable, `tests/test_algo_uplifts/test_uplifts.py`)
never collected a single test — pytest aborted at module-load time
with:

```
ImportError: cannot import name 'EVIDENCE_SCALE_GAP_AUDIT_REASON'
from 'adaptive_reflow.eval.posterior_selection_evaluator'
(/home/hugo/.../posterior_selection_evaluator.py)
```

This blocks the Wave 14 C 36-uplift isolation suite, blocks the
Wave 17 Phase 4 long-running regression check, and propagates into
the Wave 39 Agent B framework-freeze verify (commit fb652bb6) as a
"1 pre-existing collection error". Fixing it is the prerequisite for
the Wave 40 / Wave 41 framework-freeze-final milestone.

---

## 2. Origin analysis

The full chain (from the running traceback):

```
tests/test_algo_uplifts/test_uplifts.py:56      ensure_eval_modules_loaded()
tests/test_algo_uplifts/conftest.py:67           _load_eval_submodule("posterior_selection_evaluator")
tests/test_algo_uplifts/conftest.py:55           spec.loader.exec_module(module)
adaptive_reflow/eval/posterior_selection_evaluator.py:123
                                                  from adaptive_reflow.adapters.twodim_fm import (...)
adaptive_reflow/adapters/__init__.py:9            from .flowmol3 import (...)
adaptive_reflow/adapters/flowmol3.py:54          from adaptive_reflow.framework.interfaces import implements
adaptive_reflow/framework/__init__.py:12         from adaptive_reflow.framework.interfaces import (...)
adaptive_reflow/framework/interfaces.py:63       from adaptive_reflow.theory.checkers import (...)
adaptive_reflow/theory/__init__.py:70            from adaptive_reflow.theory import checkers
adaptive_reflow/theory/checkers.py:79            from adaptive_reflow.eval.lipschitz_diagnostic import (...)
adaptive_reflow/eval/__init__.py:79              from .posterior_selection_evaluator import (EVIDENCE_SCALE_GAP_AUDIT_REASON, ...)
ImportError: cannot import name 'EVIDENCE_SCALE_GAP_AUDIT_REASON' from 'adaptive_reflow.eval.posterior_selection_evaluator'
```

**Root cause.** The conftest's `_load_eval_submodule` uses
`importlib.util.spec_from_file_location` + `exec_module` to load the
submodule directly (bypassing `adaptive_reflow.eval.__init__`'s
rdkit-deferred submodule path). It then runs the module body
top-to-bottom. When line 123 (`from
adaptive_reflow.adapters.twodim_fm import (...)`) executes, Python
loads `adaptive_reflow.adapters.twodim_fm`, which transitively
re-enters `adaptive_reflow.eval.lipschitz_diagnostic`, which triggers
the parent package `adaptive_reflow.eval` to load. `eval/__init__.py`
then runs `from .posterior_selection_evaluator import (EVIDENCE_SCALE_GAP_AUDIT_REASON, ...)`
at module load time — but `posterior_selection_evaluator` is
**partially loaded** (only lines 1-122 have executed; constants
start at line 159), so the symbol is not yet bound. ImportError.

**Why this matters.** The audit doc
`docs/audit/wave39-wave17-phase4-verify.md` (lines 33-110)
classifies this as PRE-EXISTING (Wave 30 Agent C, commit `8944a09`).
The fix is local to `adaptive_reflow/eval/__init__.py` and
specifically targets the eager import at lines 79-97.

---

## 3. Fix chosen — Option A (PEP 562 lazy `__getattr__`)

The audit doc lists two minimum-touch options:

* **Option A (preferred).** PEP 562 module-level `__getattr__` in
  `eval/__init__.py` so plain `import adaptive_reflow.eval` does NOT
  trigger `posterior_selection_evaluator`.
* **Option B.** Move `EVIDENCE_SCALE_GAP_AUDIT_REASON` constant
  definition in `posterior_selection_evaluator.py` above the imports
  at line 123.

**Decision:** Option A. Rationale:

1. The `eval/__init__.py` already has a working PEP 562
   `__getattr__` for the rdkit-deferred submodules
   (`_RDKIT_LAZY_MODULES`, lines 200-247 pre-fix). Reusing that
   pattern is a 17-entry dict-extension, not a new architecture.
2. **Option B alone is insufficient.** The eager import block at
   `eval/__init__.py:79-97` (pre-fix) imports seventeen symbols
   (`EVIDENCE_SCALE_GAP_AUDIT_REASON`, `EVIDENCE_SCALE_GAP_CHANNELS`,
   `POSTERIOR_SELECTION_AUDIT_REASON`, `POSTERIOR_SELECTION_BUNDLE_ID_PREFIX`,
   `POSTERIOR_SELECTION_CALIBRATION`, `POSTERIOR_SELECTION_CELLS_FOR_TARGET`,
   `POSTERIOR_SELECTION_CHANNELS`, `POSTERIOR_SELECTION_PERTURBATION`,
   `POSTERIOR_SELECTION_SHEET_FOR_TARGET`, `POSTERIOR_SELECTION_TARGETS`,
   `EvidenceScaleGapMetric`, `cell_evidence`, `mode_centers_for`,
   `selection_ratio`, `sheet_cell_centers`, `sheet_evidence`,
   `sheet_vs_cells_proxy`). Python fails on the FIRST missing name,
   so moving only `EVIDENCE_SCALE_GAP_AUDIT_REASON` to the top of
   `posterior_selection_evaluator.py` just shifts the error to
   `EVIDENCE_SCALE_GAP_CHANNELS` (line 178). Option B would require
   moving ALL seventeen symbols — a much larger and more fragile
   change.
3. Option A is **future-proof**: any future cycle through
   `posterior_selection_evaluator` is also broken by routing through
   `__getattr__`. Option B is a one-shot patch.

### 3.1 What changed

**File:** `adaptive_reflow/eval/__init__.py`

* **Removed** lines 79-97: the eager `from
  .posterior_selection_evaluator import (...)` block (seventeen
  symbols).
* **Added** a 12-line comment block documenting the rationale and the
  cycle mechanism (Wave 41 Agent C marker).
* **Renamed** `_RDKIT_LAZY_MODULES` → `_LAZY_MODULE_SYMBOLS` and
  added seventeen entries mapping each symbol to
  `"posterior_selection_evaluator"`.
* **Updated** the `__getattr__` docstring to cover BOTH
  rdkit-deferred and cycle-deferred submodules.

**Net change:** ~40 LOC replaced in one file. The public surface of
  `adaptive_reflow.eval` is unchanged — every symbol that was
  importable via `from adaptive_reflow.eval import X` remains
  importable; it now resolves through the lazy `__getattr__` instead
  of being bound eagerly.

**Files NOT touched (per task constraints):** scheduler,
  framework/, paper_quantities, regression-vectors, test_claims, and
  `posterior_selection_evaluator.py` itself (Option B was not needed).

### 3.2 Why the lazy `__getattr__` does not re-trigger the cycle

The lazy loader fires on **attribute access**, not on `import`. When
plain `import adaptive_reflow.eval` runs:

1. `eval/__init__.py` executes; the only `posterior_selection_evaluator`
   reference in the body is the lookup table `_LAZY_MODULE_SYMBOLS`
   (a string dict, no module load).
2. `posterior_selection_evaluator` is NOT triggered.
3. The `from adaptive_reflow.eval.lipschitz_diagnostic import (...)`
   in `theory/checkers.py:79` completes successfully — the parent
   package finished loading without re-entering the submodule.
4. The import chain unwinds.

Later, when downstream code does `from adaptive_reflow.eval import
EVIDENCE_SCALE_GAP_AUDIT_REASON`:

1. PEP 562 `eval.__getattr__("EVIDENCE_SCALE_GAP_AUDIT_REASON")` fires.
2. `_LAZY_MODULE_SYMBOLS` returns `"posterior_selection_evaluator"`.
3. `importlib.import_module("adaptive_reflow.eval.posterior_selection_evaluator")`
   returns the **fully loaded** module (no cycle, because the cycle
   only fires at first-load).
4. `getattr(mod, "EVIDENCE_SCALE_GAP_AUDIT_REASON")` returns the
   string.
5. The result is cached in `eval.__dict__` for subsequent accesses.

---

## 4. Verification

### 4.1 Collection + run

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_algo_uplifts/ -q --tb=line
50 passed, 27 warnings in 53.13s
```

All 50 collected tests pass. The 36-uplift isolation suite
(`test_uplifts.py`) plus the conftest helpers (`test_uplifts.py`'s
own doctest-like parametrizations and any sibling tests in the
directory) now run. The 27 warnings are all
`DeprecationWarning`s for the Wave 34 scheduler rename (existing,
unrelated).

### 4.2 No regression in `test_eval/test_posterior_selection_evaluator.py`

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_eval/test_posterior_selection_evaluator.py -q
49 passed, 12 warnings in 125.15s (0:02:05)
```

49/49 pass. This test imports the same seventeen symbols via the
parent-package path (`from adaptive_reflow.eval import
posterior_selection_evaluator as pse_mod`) and via the submodule path
(`from adaptive_reflow.eval.posterior_selection_evaluator import (...)`).
Both paths resolve correctly through the new lazy `__getattr__`.

### 4.3 Smoke test: lazy-load path

```
$ .venvs/flowmol3_venv/bin/python -c \
  "from adaptive_reflow.eval import EVIDENCE_SCALE_GAP_AUDIT_REASON, EvidenceScaleGapMetric; \
   print('EVIDENCE_SCALE_GAP_AUDIT_REASON:', repr(EVIDENCE_SCALE_GAP_AUDIT_REASON)); \
   print('EvidenceScaleGapMetric:', EvidenceScaleGapMetric)"

EVIDENCE_SCALE_GAP_AUDIT_REASON: 'evidence_scale_gap:sheet_vs_cells_O_eps_1_vs_O_eps_2'
EvidenceScaleGapMetric: <class 'adaptive_reflow.eval.posterior_selection_evaluator.EvidenceScaleGapMetric'>
```

Both symbols resolve correctly through the new lazy `__getattr__`.

### 4.4 Wave 39 Agent B verify doc prediction

The Wave 39 audit doc (lines 96-110 of
`docs/audit/wave39-wave17-phase4-verify.md`) predicted two possible
fixes. Option A (lazy `__getattr__`) was listed first as preferred;
this fix implements it exactly.

---

## 5. Files delivered by this fix

- `adaptive_reflow/eval/__init__.py` (modified — removed 19 LOC of
  eager imports, added 17 entries to `_LAZY_MODULE_SYMBOLS`, updated
  docstrings)
- `docs/audit/wave41-circular-import-fix.md` (this report)

**Commit:** Local commit only — **DO NOT PUSH** (per task constraint).

---

## 6. Conclusion

The pre-existing circular import that blocked
`tests/test_algo_uplifts/` collection for 11 waves (Wave 30
introduction through Wave 40 freeze-prep) is fixed via Option A (PEP
562 `__getattr__`). The fix is local to one file
(`adaptive_reflow/eval/__init__.py`), does not touch the framework,
scheduler, paper_quantities, regression-vectors, or test_claims code,
and preserves the full public surface of `adaptive_reflow.eval`. All
36+ uplift isolation tests now pass; no regression in the 49 sibling
`test_posterior_selection_evaluator.py` tests.