# Wave 44 Agent A — Group A cold-import cycle fix

**Date:** 2026-09-07
**Agent:** Wave 44 Agent A
**Scope:** Group A push-blocker — break the cold-import cycle in `adaptive_reflow`.

## Problem

`import adaptive_reflow.theory` failed outside pytest with:

```
ImportError: cannot import name 'Theorem1Statement' from partially
initialized module 'adaptive_reflow.theory.checkers' (most likely due
to a circular import)
```

The cycle (Wave 43 WF2 Agent C root cause):

```
theory/__init__.py:70 → checkers
checkers.py:79 → eval.lipschitz_diagnostic
eval/__init__.py:122 → eval.twodim_fm_evaluator
eval/twodim_fm_evaluator.py:95 → adapters.twodim_fm
adapters/__init__.py:9 → adapters.flowmol3
adapters/flowmol3.py:68 → framework.interfaces.implements
framework/__init__.py:12 → framework.interfaces
framework/interfaces.py:63 → theory.checkers     ← cycle closes
```

**Affected tests:**
* `tests/test_contracts/test_paper_quantities.py::test_no_torch`
  (subprocess imports `adaptive_reflow.contracts.paper_quantities`,
  which imports `adaptive_reflow.theory.paper_quantities`, which
  triggers the cycle).
* `tests/test_tools/test_benchmark_internal_uplifts.py`
  (collection triggered `tools.benchmark_uplifts` which imports the
  framework chain; the cycle blocked the whole file's collection).

## Fix (Option B — defer eval/__init__.py:122 import)

**File touched:** `adaptive_reflow/eval/__init__.py`

The fix removes the eager `from .twodim_fm_evaluator import (...)`
block at line 122 and routes the 14 exported symbols through the
existing PEP 562 module-level `__getattr__` lazy loader (originally
added in Wave 15 C for rdkit submodules; expanded in Wave 41 Agent C
for `posterior_selection_evaluator` cycle-dependent symbols).

**Why Option B (not Option A)?**

* **Smaller disruption** — Option B reuses the existing PEP 562
  pattern already in `eval/__init__.py` (no new lazy loader scaffold),
  and only touches one file instead of two.
* **Cycle-breaking point** — `eval/__init__.py:122` is the
  load-time edge that re-enters `adapters → framework → theory`.
  Removing the eager edge breaks the cycle directly.
* **Option A doesn't fully fix** — even with a lazy
  `__getattr__` on `framework.interfaces`, the `framework/__init__.py`
  re-export `from adaptive_reflow.framework.interfaces import
  Theorem1Statement` would still call `__getattr__('Theorem1Statement')`
  while `theory.checkers` is partially loaded (the framework re-export
  is an eager load that triggers the partial theory-checkers re-entry
  mid-cycle).

**PEP 562 lazy loader (already present in `eval/__init__.py`)** routes
14 `twodim_fm_evaluator` symbols:

```python
_LAZY_MODULE_SYMBOLS: dict[str, str] = {
    # ... existing rdkit + posterior_selection_evaluator entries ...
    # twodim_fm_evaluator cycle-dependent (Wave 44 Agent A)
    "TWODIM_FM_COVERAGE_RADIUS": "twodim_fm_evaluator",
    "TWODIM_FM_EVALUATOR_AUDIT_REASON": "twodim_fm_evaluator",
    "TWODIM_FM_EVALUATOR_BUNDLE_ID_PREFIX": "twodim_fm_evaluator",
    "TWODIM_FM_EVALUATOR_CALIBRATION": "twodim_fm_evaluator",
    "TWODIM_FM_EVALUATOR_CHANNELS": "twodim_fm_evaluator",
    "TWODIM_FM_EVALUATOR_PERTURBATION": "twodim_fm_evaluator",
    "TWODIM_FM_GRID_BOUND": "twodim_fm_evaluator",
    "TWODIM_FM_GRID_RESOLUTION": "twodim_fm_evaluator",
    "TWODIM_FM_W2_MAX": "twodim_fm_evaluator",
    "TwoDimFMEvaluator": "twodim_fm_evaluator",
    "analytic_samples": "twodim_fm_evaluator",
    "coverage_score": "twodim_fm_evaluator",
    "energy_distance": "twodim_fm_evaluator",
    "voronoi_grid": "twodim_fm_evaluator",
}
```

The eager `from .twodim_fm_evaluator import (...)` block is replaced by
a comment explaining the cycle history (preserves the audit trail).

## Verification

### Cold-import cycle broken

```
$ .venvs/flowmol3_venv/bin/python -c "import adaptive_reflow.theory"
OK: theory imports cleanly
```

### Lazy loader resolves `from adaptive_reflow.eval import X`

```
$ .venvs/flowmol3_venv/bin/python -c "
from adaptive_reflow.eval import TwoDimFMEvaluator, TWODIM_FM_EVALUATOR_CHANNELS, TWODIM_FM_COVERAGE_RADIUS
print(f'TwoDimFMEvaluator = {TwoDimFMEvaluator}')
print(f'TWODIM_FM_EVALUATOR_CHANNELS = {TWODIM_FM_EVALUATOR_CHANNELS}')
print(f'TWODIM_FM_COVERAGE_RADIUS = {TWODIM_FM_COVERAGE_RADIUS}')
"
TwoDimFMEvaluator = <class 'adaptive_reflow.eval.twodim_fm_evaluator.TwoDimFMEvaluator'>
TWODIM_FM_EVALUATOR_CHANNELS = ('xy',)
TWODIM_FM_COVERAGE_RADIUS = 0.3
OK: lazy loaders resolve correctly
```

### `contracts.paper_quantities` cold-import

```
$ .venvs/flowmol3_venv/bin/python -c "
from adaptive_reflow.contracts.paper_quantities import sheet_evidence_A
print(f'sheet_evidence_A(0) = {sheet_evidence_A(lambda x: 0)}')
"
sheet_evidence_A(0) = 1.0000000000000004
OK: contracts.paper_quantities imports cleanly
```

### Test results

```
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_contracts/test_paper_quantities.py::test_no_torch \
    tests/test_tools/test_benchmark_internal_uplifts.py \
    -q --tb=line 2>&1 | tail -5
=========================== short test summary info ============================
FAILED tests/test_tools/test_benchmark_internal_uplifts.py::test_round2_external_covers_expected_keys
FAILED tests/test_tools/test_benchmark_internal_uplifts.py::test_round2_external_every_target_is_achieved
2 failed, 19 passed, 10 warnings in 11.75s
```

`test_no_torch` (the target test): **passes** (subprocess imports
`adaptive_reflow.contracts.paper_quantities` successfully).

`test_benchmark_internal_uplifts.py`: **19/21 pass**. Before this fix,
the cycle blocked ALL 21 tests at collection time (ERROR, not FAIL).
The 2 remaining failures are **pre-existing data-set mismatches** in
the Round-2 external uplift expected key set:

* `EXPECTED_ROUND2_EXTERNAL_KEYS` declares 7 keys
  (`DPMSolverPPIntegrator, UniPCIntegrator2, UniPCIntegrator3,
  DormandPrinceRK45Integrator, EulerMaruyamaIntegrator,
  SDEHeunIntegrator, SymplecticLeapfrogIntegrator`) but the actual
  benchmark only reports 6 keys (missing `DPMSolverPPIntegrator`).
* `test_round2_external_every_target_is_achieved` then fails the
  `>= total - 1` budget because `DPMSolverPPIntegrator` + the
  deleted-in-Wave-33 `StochasticFMAdapter` are both reported as missed.

These are **not** caused by the cold-import cycle fix and are out of
scope for Wave 44 Group A. They belong to a separate "Round-2
external uplifts data set drift" task.

## Files changed

* `adaptive_reflow/eval/__init__.py` — replaced eager
  `from .twodim_fm_evaluator import (...)` block (lines 122-137) with a
  comment block; added 14 symbols to `_LAZY_MODULE_SYMBOLS` dict.

## Constraints honoured

* Did **not** touch: scheduler, paper_quantities,
  regression-vectors, test_claims, framework core/, adapters.
* Did **not** push.

## Wave 44 status

Group A push-blocker closed: cold-import cycle broken, both target
tests pass (cycle-wise). The 2 pre-existing test fixture
mismatches in `test_benchmark_internal_uplifts.py` are out of scope
and need a separate data-set update.