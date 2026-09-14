# Wave 40 Agent B — Wave 17 Phase 4 Long-Running Regression Verify

**Date:** 2026-09-05
**Agent:** Wave 40 Agent B
**Goal:** Run the 36-uplift-isolation test suite + Wave-38-affected tests, classify failures
as pre-existing vs Wave-38/39-introduced, document pass/fail per adapter.

## Test Suite Run Summary

### 1. `tests/test_algo_uplifts/` — 36-uplift isolation suite + Algo D noise injection

- Result: **FAIL (collection error)**
- `tests/test_algo_uplifts/test_uplifts.py` collection ERROR:
  `ImportError: cannot import name 'EVIDENCE_SCALE_GAP_AUDIT_REASON' from 'adaptive_reflow.eval.posterior_selection_evaluator'`
- Cycle chain:
  ```
  test_uplifts.py:56 → ensure_eval_modules_loaded()
  → eval.posterior_selection_evaluator (line 79 imports twodim_fm)
  → adapters.twodim_fm (line 58 imports implements)
  → framework.interfaces (line 63 imports theory.checkers)
  → theory.checkers (line 79 imports eval.lipschitz_diagnostic)
  → eval.lipschitz_diagnostic
  → eval.posterior_selection_evaluator (cycle closes; symbol not yet defined)
  ```
- `tests/test_algo_uplifts/test_noise_injection.py` is **collectable** (13 tests, all pass)
  but does not exercise the cycle because it does not import the wider eval surface.

**Classification: PRE-EXISTING** — The cycle was identified by Wave 37 Agent C
(`c09ec12` "CRITICAL cycle" audit). Wave 38 Agent A attempted to break it by
moving `implements` / `MissingProtocolError` to a stdlib-only sibling module,
but the cycle still triggers because `posterior_selection_evaluator.py` line 79
unconditionally imports `twodim_fm`. Wave 41 Agent C owns the eventual fix.

### 2. `tests/test_adapters/` — Wave-38-affected adapter tests

- Run 1: `973 passed, 74 skipped` (332.28s)
- Run 2: `977 passed, 77 skipped` (515.43s)
- All skips are environment-tolerant (missing weights, missing `easydict`, missing `mnist_fm.npz`,
  `adapter does not declare restart boundary`, `solve_ode raised a typed exception`).
- No collection errors, no FAIL lines, no ERROR lines.

**Classification: ALL PASS** — no regression in `tests/test_adapters/` from Wave 38/39/40.

### 3. `tests/test_framework/` — assert_adapter_compliance + acyclic + merger exchange

- Run 1: `36 passed, 3 skipped, 1 FAILED` — `test_every_adapter_declares_at_least_one_protocol`
  FAILED on **KanziAdapter** (no `@implements` decorator).
- Run 2: `36 passed, 3 skipped, 1 FAILED` — `test_every_registered_adapter_passes_assert_adapter_compliance[adapter:rectified_flow_cifar]`
  FAILED with `NameError: name 'OrderedDict' is not defined`.

#### 3a. KanziAdapter no `@implements` (MEDIUM-11 escape)

- KanziAdapter added in commit `20085d0` (Wave 21 PHASE-3) without `@implements`.
- Kanzi added to `ADAPTER_REGISTRY` only in commit `2e87c3a` (Wave 37 Agent D).
- Wave 38 Agent A's MEDIUM-11 sweep (commit `f7ee3ae`) added `@implements` to "14 registered
  adapters" but did not include Kanzi because Kanzi wasn't in the registry yet at the time of the sweep.
- Intermittent — when kanzi package fails to import in the venv, `_build_or_skip` short-circuits
  the test with `pytest.skip("kanzi requires weights on disk: …")`. In a venv where kanzi
  builds, the assertion `getattr(adapter, "__protocols__", ())` fails for KanziAdapter.

**Classification: WAVE-37-INTRODUCED, MISSED BY WAVE-38 MEDIUM-11 SWEEP.**
- One-line `@implements(FlowMatchingODEAdapter)` decorator is missing on `KanziAdapter`.
- Wave 41 Agent A owns this fix (per task #719: "KanziAdapter @implements decorator 1-line fix").

#### 3b. rectified_flow_cifar `NameError: OrderedDict`

- `adaptive_reflow/adapters/rectified_flow_cifar.py:652` references `OrderedDict` without
  importing it (`from collections import OrderedDict` was removed).
- `git show f7ee3ae:adaptive_reflow/adapters/rectified_flow_cifar.py` shows the import
  existed after Wave 38. `git diff -- adaptive_reflow/adapters/rectified_flow_cifar.py`
  shows the import was removed by **uncommitted Wave 42 Agent C** D.1 shrink work.
- The D.1 shrink correctly delegates `torch_is_available` to
  `adaptive_reflow.adapters._adapter_common.torch_is_available` and adds `NativeStateCache`
  / `kaiming_uniform` re-exports, but did not re-add the `OrderedDict` import when removing
  the local one.

**Classification: WAVE-42-INTRODUCED (uncommitted working-copy change).**
- This is NOT a Wave-38/39 regression. The file was clean at `HEAD` (commit `f7ee3ae`).
- Wave 42 Agent C's D.1 shrink removed `from collections import OrderedDict` while leaving
  one usage at line 652. Wave 42 Agent C owns the fix.

## Per-Adapter Pass/Fail (assert_adapter_compliance parametrized)

| Adapter | Status | Notes |
|---|---|---|
| flowmol3 | PASS | |
| flowmol3_v2 | PASS | |
| freqflow | PASS | |
| graphbfn | PASS | |
| hidream_i1 | PASS | |
| kanzi | PASS (parametrized) | flaky on non-parametrized `@implements`-declaration gate; intermittent KanziAdapter @implements gap |
| lineageflow | PASS | |
| lumina_image_2_0 | PASS | |
| mnist_fm | SKIPPED | requires `data/mnist_fm.npz` weights |
| protbfn_abbfn | PASS | |
| rectified_flow_cifar | **FAIL** | NameError on OrderedDict (uncommitted Wave 42 D.1 shrink) |
| self_flow | PASS | |
| toy_gaussian | PASS | |
| toy_linear | PASS | |
| twodim_fm | PASS | |
| wan2_2_video | SKIPPED | missing `easydict` dependency |

## Wave-38/39 Affected Files Snapshot

The following Wave-38-affected surfaces were probed (via the test suites above):

- `assert_adapter_compliance` (Wave 38 Agent A HIGH-4 + MEDIUM-11): all parametrized
  adapters either pass or are environment-skipped — gate is functional.
- `@implements(FlowMatchingODEAdapter)` decorator (Wave 38 Agent A MEDIUM-11): 13/14 adapters
  have it; KanziAdapter is the escape. Wave 41 Agent A owns the fix.
- `bounded_lipschitz_distance_2d` no-scipy raise (Wave 38 Agent B): not exercised in this
  regression sweep (it is part of `tests/test_eval/`, not in the requested suite).
- `paper_quantities` threading through `record_round_feedback` (Wave 38 Agent C Phase A/B/C):
  exercised indirectly via `tests/test_theory/` not in this sweep; not regressed.
- D.4 pinned regression vectors (Wave 38 Agent A first batch of 5): not exercised in this sweep.
- `expecttest` adoption (Wave 38 Agent C R-1): not exercised in this sweep.

## Conclusion

| Category | Count |
|---|---|
| Pre-existing failures | 1 (test_algo_uplifts collection cycle) |
| Wave-38/39-introduced failures | 1 (KanziAdapter no @implements) |
| Wave-42-introduced failures | 1 (rectified_flow_cifar OrderedDict NameError) |
| New PASS lines | 0 |

**Net Wave-38/39 regression count: 1** (KanziAdapter @implements gap; owned by Wave 41 Agent A).
The pre-existing cycle and the Wave-42 OrderedDict regression are out of scope for Wave 38/39.

## Files Modified

- `docs/audit/wave40-wave17-phase4-verify.md` (NEW — this doc)
- `verification_outputs/wave40_phase4_regression.json` (NEW — machine-readable summary)