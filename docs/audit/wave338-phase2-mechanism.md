# Wave 338 Phase 2 — R6 LineageFlow Glue Engineering (Scheduler Knob)

**Date:** 2026-09-23
**Author:** Wave 338 Phase 2 — R6 LineageFlow glue engineering agent
**Scope:** Expose scheduler selection on the LineageFlow N=1000 framework glue path so the live R6 `TierAwareCodimensionSheetScheduler` sweep is reachable end-to-end.
**Status:** GLUE WIRED; live R6 sweep runnable via `--scheduler tier_aware_codimension`.

---

## 1. Executive Summary

| Item                                                  | Value                                                                                             |
|-------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| Wave 334 finding                                      | Framework glue does not expose scheduler selection                                                |
| Wave 338 Phase 2 deliverable                          | `--scheduler` knob wired end-to-end: gen script → `_solve_framework` → `build_scheduler`          |
| Default scheduler                                     | `cosine` — preserves legacy byte-stable `[3, 3, 4]` NFE distribution for `nfe=10, n_rounds=3`    |
| R6 sweep scheduler                                    | `tier_aware_codimension` — live `TierAwareCodimensionSheetScheduler` wrapper registered & exposed |
| `_solve_framework` signature change                   | Added `scheduler_name: str = "cosine"` kwarg (additive, default-safe)                             |
| YAML knob                                             | `scheduler: cosine` (default) or `tier_aware_codimension` (live R6)                              |
| Pre-existing bug fixed (in scope)                     | `_patched_make_framework_policy` rejected the Wave 275 P4 R6 kwargs (`tier_aware_n_cap` etc.); now passed through |
| Test status                                           | 211 scheduler + gen-script tests pass; 1057+ broader tests pass with 1 pre-existing assertion updated for the new registry entry |

**Headline:** Scheduler selection is now first-class on the LineageFlow framework glue. The default `cosine` path is byte-stable against Wave 158 / Wave 161 K6 / Wave 172b lineageflow anchors; the live R6 sweep runs by passing `--scheduler tier_aware_codimension`.

---

## 2. Problem Statement

Wave 334 found that the LineageFlow N=1000 GPU framework glue path is opaque to scheduler selection:

* `tools/gen_lineageflow_n1000_fastas.py` invokes `_solve_framework` with no `scheduler_name` argument.
* `tools/eval/framework.py:_solve_framework` hardcodes the per-round NFE distribution (`[base, ..., base+remainder]`) and never imports `build_scheduler`.
* `configs/runs/lineageflow_n1000_gpu.yaml` has no scheduler override knob.

`TierAwareCodimensionSheetScheduler` exists in `adaptive_reflow/algorithm/scheduler/tier_aware.py` but is not registered in `SCHEDULER_REGISTRY`, so `build_scheduler("tier_aware_codimension", ...)` would raise `KeyError`.

The R6 sweep needs the live tier-aware wrapper to redistribute per-round NFE on LineageFlow — without the glue, the sweep is unreachable from the gen-script / YAML entry points.

---

## 3. Implementation

### 3.1 `adaptive_reflow/algorithm/scheduler/tier_aware.py`

Added `_tier_aware_codimension_factory` so the wrapper can be looked up via `build_scheduler`. Mirrors `_codimension_sheet_factory` (constructor kwargs surface). Lazy-imports `CodimensionSheetScheduler` to keep the cycle-safe import order.

```python
def _tier_aware_codimension_factory(
    *,
    cycle_length: int = 20,
    n_min: float = 0.0,
    n_max: float = 1.0,
    eps_implicit: float = 0.05,
    eps_direction: str = "decreasing",
    seed: int = 0,
    easy_tier_nfe_reduction_factor: float = 1.0,
    tier_quantile_boundaries: tuple[float, float] = DEFAULT_TIER_QUANTILES,
    baseline_metric_extractor: Callable[[Any], float] | None = None,
) -> TierAwareCodimensionSheetScheduler: ...
```

### 3.2 `adaptive_reflow/algorithm/scheduler/nfe_aware.py`

Registered the factory under `SCHEDULER_REGISTRY["tier_aware_codimension"]`. Lazy-imports the module (same pattern as `_sequential_factory`) so the cycle-closed `scheduler/__init__.py` → `scheduler/_core.py` → `scheduler/tier_aware.py` → `scheduler/__init__.py` partial is not re-opened at module-load time.

### 3.3 `tools/eval/framework.py:_solve_framework`

Added `scheduler_name: str = "cosine"` to the signature. The legacy `[base, ..., base+remainder]` NFE distribution is preserved when `scheduler_name == "cosine"` (byte-stable against Wave 158/161/172b). For any other registered family the scheduler is built via `build_scheduler(scheduler_name, cycle_length=n_rounds)` and per-round NFE is derived from `n_cap`:

```python
_nfe_per_round = int(round(float(n_cap) * float(nfe)))
_nfe_per_round = max(1, min(int(nfe), int(_nfe_per_round)))
```

Sum is reconciled to `nfe` exactly by adding the rounding deficit to the LAST round (mirrors the legacy pattern).

### 3.4 `tools/gen_lineageflow_n1000_fastas.py`

* Added module-level `SCHEDULER_NAME: str = "cosine"` constant.
* Added `--scheduler {NAME}` CLI argument (default `"cosine"`).
* Wired `scheduler_name` through `_framework_emit_sequence` → `_solve_framework`.
* Captured `scheduler_name` in the per-cell `manifest.json` so the audit doc can correlate FASTA bytes to the chosen scheduler.
* Fixed a pre-existing bug in `_patched_make_framework_policy`: the Wave 186 P2 sensitivity patch wrapper did not accept the Wave 275 P4 R6 kwargs (`tier_aware_n_cap`, `tier_aware_baseline_metrics`, `current_record_id`) nor the new `scheduler_name`. Added them to the wrapper's signature and forwarded them to the underlying `_orig_policy` call (tier-aware kwargs only; `scheduler_name` is absorbed by the wrapper as it's not consumed by the policy helper).

### 3.5 `configs/runs/lineageflow_n1000_gpu.yaml`

Added the `scheduler: cosine` knob in §2.b with a comment explaining how to switch to `tier_aware_codimension` for the live R6 sweep.

---

## 4. Verification

### 4.1 Default `cosine` byte-stability

For `nfe=10, n_rounds=3`, the new cosine path reproduces the legacy `[3, 3, 4]` NFE distribution exactly (confirmed via direct `_solve_framework` unit test with a stub adapter). The synthetic adapter's re-anchor step (`tools/eval/framework.py:_solve_framework` lines 802-810) uses `(seed=seed, steps=nfe)` deterministically, so the cosine path produces identical `framework.fasta` bytes to pre-Wave-338.

### 4.2 `tier_aware_codimension` live sweep runnable

* `build_scheduler("tier_aware_codimension", cycle_length=3)` resolves to a `TierAwareCodimensionSheetScheduler` instance.
* `_solve_framework(..., scheduler_name="tier_aware_codimension")` builds the scheduler and uses its `n_cap` to derive per-round NFE.
* The gen script's `framework_fallback_per_family_count` is `{}` for both `cosine` and `tier_aware_codimension` runs (i.e., the framework glue runs without falling back to bare RNG).
* The manifest captures `"scheduler_name": "tier_aware_codimension"` so the per-cell audit can verify the chosen scheduler.

### 4.3 Test suite

| Test file                                                      | Result        |
|----------------------------------------------------------------|---------------|
| `tests/test_paper_grounded_schedulers.py`                      | 65 passed     |
| `tests/test_algorithm/test_scheduler/test_cosine_default.py`  | 17 passed (1 assertion updated for new registry entry) |
| `tests/test_algorithm/test_scheduler/*`                        | 211 passed    |
| `tests/test_tools/test_gen_lineageflow_n1000_fastas.py`        | 4 passed      |
| `tests/test_adapters/test_lineageflow_conformance.py` (synthetic subset) | passed |
| Wider test suite (1057+ tests)                                 | passed (1 unrelated test assertion updated for the new `tier_aware_codimension` registry entry) |

### 4.4 File-level sha256 (post-change)

```
904ac40061f51a6051828d0ad5a2cafa09d597314e34408250435e93ce9efdce  tools/gen_lineageflow_n1000_fastas.py
03c68d250abd7079a65bb3e939e343d8a6935a192b208792f51d941e6433a831  tools/eval/framework.py
ac9bd883d32bb349a4ca88caf15e20e26ce864d6e38ebcc9d41ade5c766fd432  configs/runs/lineageflow_n1000_gpu.yaml
926427b7cd3cd908d5a4c728c9346532354b555c97d513b6e40358cb675fb900  adaptive_reflow/algorithm/scheduler/nfe_aware.py
36a1a80551a97fcdcebc03f7ed12399e2e0634dc37e7abfc52ab27e2e4fb5d08  adaptive_reflow/algorithm/scheduler/tier_aware.py
```

---

## 5. Notes

### 5.1 Per-round NFE allocation is scheduler-driven but final output is re-anchored

`_solve_framework` ends with a "re-anchor" step (Wave 64 Agent 1 fix) that runs a final `solve_ode(cur_bundle, final_condition, seed=int(seed))` with `num_steps=nfe`. The re-anchor uses `(seed=seed, steps=nfe)` deterministically — independent of the per-round NFE allocation. For the LineageFlow synthetic adapter this means:

* The framework glue runs the scheduler-driven per-round allocation as designed.
* The final `framework.fasta` bytes are determined by the re-anchor step, which is scheduler-agnostic.
* The scheduler's effect propagates to per-round traces (consumed by the restart-blend glue) but is collapsed by the re-anchor when computing the final trace's `steps=nfe`.

This is by design (matched-NFE comparison invariant from Wave 64). The scheduler's effect on per-round restart-blend state is observable through the framework glue's per-round behaviour (auditable via per-round logs), but the final FASTA bytes are byte-stable against pre-Wave-338 for the cosine default.

### 5.2 Pre-existing `_patched_make_framework_policy` kwarg rejection

Discovered during verification: the Wave 186 P2 sensitivity patch wrapper installed by `_apply_sensitivity_patches` rejected the Wave 275 P4 R6 kwargs (`tier_aware_n_cap`, `tier_aware_baseline_metrics`, `current_record_id`). This caused the framework glue path to raise `TypeError` and fall back to bare RNG for every record (visible as non-empty `framework_fallback_per_family_count`). Fixed as part of Phase 2 because the R6 sweep needs the framework glue to actually run.

### 5.3 `tier_aware_codimension` defaults to safe no-op

The wrapper is registered with `easy_tier_nfe_reduction_factor=1.0` (the safe no-op default). The engine must opt in by supplying a non-empty `tier_aware_baseline_metrics` mapping AND a `tier_aware_n_cap < 1.0` to actually exercise the easy-tier reduction. This is consistent with Wave 275 P4 R6 design (the wrapper is byte-stable until the engine configures it).

---

## 6. Files Modified

| File                                                                       | Change                                                            |
|----------------------------------------------------------------------------|-------------------------------------------------------------------|
| `tools/gen_lineageflow_n1000_fastas.py`                                    | Added `--scheduler` CLI arg + module-level `SCHEDULER_NAME` constant; wired `scheduler_name` to `_solve_framework`; fixed `_patched_make_framework_policy` to accept Wave 275 P4 R6 kwargs + new `scheduler_name` kwarg |
| `tools/eval/framework.py`                                                  | Added `scheduler_name: str = "cosine"` kwarg to `_solve_framework`; imports `build_scheduler`; special-cases `cosine` for byte-stability; uses scheduler's `n_cap` to derive per-round NFE for any other family |
| `configs/runs/lineageflow_n1000_gpu.yaml`                                  | Added `scheduler: cosine` knob in §2.b with comment on `tier_aware_codimension` activation |
| `adaptive_reflow/algorithm/scheduler/tier_aware.py`                        | Added `_tier_aware_codimension_factory` (mirrors `_codimension_sheet_factory`) |
| `adaptive_reflow/algorithm/scheduler/nfe_aware.py`                         | Registered `tier_aware_codimension` in `SCHEDULER_REGISTRY` (lazy import, cycle-safe) |
| `tests/test_algorithm/test_scheduler/test_cosine_default.py`               | Updated `test_all_schedulers_conform_to_protocol` to include `tier_aware_codimension` in the expected registry set |