# Wave 53 Agent C — FlowMol3 metric-layer impl + wiring fix

**Date:** 2026-09-07
**Wave:** 53, Agent C
**Scope:** Apply Agent A's metric-layer design (per-position atom-type
entropy reduction via `observe_entropy_reduction`) and Agent B's
wiring fix (per-model `force_mode` translation table +
`flowmol3_v2_adapter.force_mode` kwarg + v1 factory defensive alias).
**Goal:** Close the Wave 50 Agent B blocker — Tier-3 FlowMol3
metric-axis.

---

## TL;DR

| Item | Status |
|---|---|
| `_compute_flowmol3_real_metric_via_trace` added to `tools/run_real_ckpt_eval.py` | DONE (closes Wave 50 Agent B Bug A) |
| `_compute_metric` dispatch extended for `model in ("flowmol3", "flowmol3_v2")` | DONE |
| `_ADAPTER_FORCE_MODE_ALIAS` per-model translation table | DONE (closes Wave 50 Agent B Bug A — real→torch mismatch) |
| `default_flowmol3_adapter` defensive "torch" → "real" alias | DONE |
| `default_flowmol3adapter` v2 factory `force_mode` kwarg | DONE (closes Wave 50 Agent B Bug B) |
| 9 regression tests in `tests/test_tools/test_run_real_ckpt_eval.py` | DONE — all 9 pass |
| Real-ckpt eval run end-to-end | DONE — `marker=computed` on all 9 cells (was `blocked` in Wave 50) |
| Composite > 0 with `verdict=framework_improves` | **NO** — placeholder uniform-vs-uniform produces `reduction=0` (expected per Agent A §3.3) |

The **metric layer is now implemented and wired**. The wiring bug is
fixed. The remaining Tier-3 close (composite > 0 with
`verdict=framework_improves`) requires a real FlowMol3 ckpt + the
upstream `flowmol` package — outside Wave 53 scope.

---

## 1. Files changed

| File | LOC | Change |
|---|---|---|
| `tools/run_real_ckpt_eval.py` | +126 | New `_compute_flowmol3_real_metric_via_trace` helper; new `_ADAPTER_FORCE_MODE_ALIAS` table; per-model mapping in `_resolve_adapter`; helper dispatched for `flowmol3` + `flowmol3_v2` in `_compute_metric`. |
| `adaptive_reflow/adapters/flowmol3.py` | +8 | Defensive "torch" → "real" alias in `default_flowmol3_adapter` (mirrors the `_resolve_adapter` translation in reverse so any caller — pipeline or otherwise — can pass either token). |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | +19 | New `force_mode` kwarg on `default_flowmol3adapter` factory with backend mapping + validator. |
| `tests/test_tools/test_run_real_ckpt_eval.py` | NEW | 9 regression tests covering: metric helper happy path, blocked-when-adapter-lacks-method, NaN handling, wiring alias identity for flowmol3, legacy-token preservation for kanzi/lineageflow/freqflow, v1 "torch" defensive alias, v2 force_mode real/synthetic/bogus. |
| `verification_outputs/flowmol3_real_metric_v2_q4_2026.json` | NEW | Eval JSON output (gitignored) — 9 cells, all `marker=computed`. |

Total: ~155 LOC across 4 files + 1 verification artifact.

---

## 2. Metric helper design (per Agent A)

### 2.1 Signature

Mirrors `_compute_kanzi_real_metric_via_trace` /
`_compute_lineageflow_real_metric_via_trace`:

```python
def _compute_flowmol3_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
```

### 2.2 Algorithm

1. Lazy-import `paper_quantities` via
   `_compute_paper_quantities_for_model("flowmol3", ...)` (Wave 45
   F-3 fix parity — kanzi / lineageflow use the same pattern).
2. Call `adapter.observe_entropy_reduction(trace,
   paper_quantities=pq_snap)`. Returns
   `{"per_position_entropy_reduction": <float>}`.
3. Surface the value as the metric. Sign convention:
   "framework sharpens → positive" (mirrors LineageFlow / Kanzi).
4. Debug dict carries `metric_axis`,
   `metric_kind="entropy_reduction"`, `K_atom_types=10`,
   `log_K_bound=log(10)`, `decode_strategy`, `trace_source`,
   `seed`, `nfe_budget`, and the `paper_quantities` thread
   result (Wave 45 F-3 parity).

### 2.3 Failure paths

| Failure | Marker | Reason |
|---|---|---|
| Adapter has no `observe_entropy_reduction` | `blocked` | `adapter_missing_observe_entropy_reduction` |
| `observe_entropy_reduction` raised | `blocked` | `observe_entropy_reduction raised: <exc>` |
| Returned dict empty or missing the channel | `blocked` | `observe_entropy_reduction returned empty dict` / `flowmol3 observe_entropy_reduction missing per_position_entropy_reduction channel` |
| Reduction is NaN | `blocked` | `entropy_reduction_is_nan` |
| Reduction is non-numeric | `blocked` | `observe_entropy_reduction returned non-numeric reduction: ...` |
| Outer try/except | `blocked` | `flowmol3 via-trajectory metric failed: <exc>` |

Mirrors the kanzi / lineageflow "never raises" contract so the
eval pipeline can degrade gracefully.

### 2.4 Dispatch insertion

In `_compute_metric` (line ~2448), the via-trace branch now reads:

```python
elif model in ("flowmol3", "flowmol3_v2"):
    (
        real_value, real_marker, real_dbg,
    ) = _compute_flowmol3_real_metric_via_trace(
        adapter=adapter, trace=trace,
        seed=seed, nfe=nfe,
    )
```

The legacy fresh-forward branch (line ~2482) intentionally does
NOT have a FlowMol3 entry — the placeholder has no real forward
(no torch / dgl / flowmol upstream) and the v2 adapter's real
forward lives in `flowmol3_v2_adapter.export_trajectory`.

---

## 3. Wiring fix (per Agent B)

### 3.1 Per-model alias table

`_resolve_adapter` previously translated `force_mode="real"` →
`adapter_force_mode="torch"` unconditionally (correct for the 10
legacy adapters; wrong for flowmol3 v1 + v2 which adopted the new
`synthetic` / `real` / `auto` convention).

Wave 53 Agent C introduces a per-model alias table:

```python
_ADAPTER_FORCE_MODE_ALIAS: dict[str, dict[str, str]] = {
    "kanzi": {"real": "torch"},
    "lineageflow": {"real": "torch"},
    "freqflow": {"real": "torch"},
    "hidream_i1": {"real": "torch"},
    "rectified_flow_cifar": {"real": "torch"},
    "graphbfn": {"real": "torch"},
    "self_flow": {"real": "torch"},
    # flowmol3 + flowmol3_v2 are identity — no entry needed.
}
```

The pipeline call becomes:

```python
adapter_force_mode = _ADAPTER_FORCE_MODE_ALIAS.get(
    model, {},
).get(force_mode, force_mode)
```

So `--force-mode real --model flowmol3` now passes `"real"` to
`default_flowmol3_adapter(force_mode="real")` (which the Wave 50
Agent A factory accepts) rather than the legacy `"torch"` token
(which the v1 factory rejected with `unknown_force_mode:torch`).

### 3.2 Defensive "torch" → "real" alias in flowmol3 v1 factory

Mirrors the pipeline translation in reverse so any caller — pipeline
or otherwise — can pass either token:

```python
# Wave 53 Agent C: defensive alias. The eval pipeline translates
# CLI "real" → "torch" for the 10 legacy {torch, synthetic, auto}
# adapters. flowmol3 v1 adopted the new {synthetic, real, auto}
# convention (Wave 50 Agent A); to keep callers from other contexts
# (not the eval pipeline) working, accept "torch" as a synonym for
# "real".
if force_mode == "torch":
    force_mode = "real"
```

### 3.3 flowmol3_v2_adapter factory force_mode kwarg

The v2 factory `default_flowmol3adapter` did not accept `force_mode`
at all in Wave 50; the pipeline called
`factory(force_mode="torch")` and got `TypeError(unexpected keyword
argument 'force_mode')`. Wave 53 Agent C adds the kwarg with a
defensive backend mapping:

```python
def default_flowmol3adapter(
    backend: str = "numpy",
    *,
    num_steps: int = FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT,
    weights_path: Any = None,
    device: str = "cpu",
    ctmc_enabled: bool | None = None,
    force_mode: str | None = None,
) -> FlowMol3V2Adapter:
    if force_mode == "torch":
        force_mode = "real"
    if force_mode is not None:
        if force_mode not in {"synthetic", "real", "auto"}:
            raise ValueError(
                f"unknown_force_mode:{force_mode} "
                "(expected 'synthetic' | 'real' | 'auto' | 'torch')"
            )
        if backend == "numpy":
            backend = "torch" if force_mode in {"real", "auto"} else "numpy"
    return FlowMol3V2Adapter(...)
```

`backend` takes precedence when explicitly passed; `force_mode` is
the CLI-friendly selector that maps to the v2 factory's native
`backend` parameter.

---

## 4. Regression tests (9)

All in `tests/test_tools/test_run_real_ckpt_eval.py`:

| Test | Asserts |
|---|---|
| `test_flowmol3_metric_helper_returns_value_marker_dbg` | Helper returns `(float, 'computed', dbg)` with `reduction_value == 0.0` (placeholder uniform-vs-uniform). |
| `test_flowmol3_metric_helper_returns_blocked_when_adapter_lacks_method` | Helper degrades to `marker='blocked'` with `reason='adapter_missing_observe_entropy_reduction'`. |
| `test_flowmol3_metric_helper_blocks_on_nan_reduction` | NaN reduction → `marker='blocked'` with `reason='entropy_reduction_is_nan'`. |
| `test_flowmol3_wiring_alias_does_not_translate_real_to_torch` | `_ADAPTER_FORCE_MODE_ALIAS["flowmol3"]` is identity (no entry). |
| `test_legacy_adapters_still_translate_real_to_torch` | kanzi / lineageflow / freqflow still receive `"torch"` (no Wave 53 regression). |
| `test_flowmol3_v1_factory_accepts_torch_alias` | `default_flowmol3_adapter(force_mode='torch')` no longer raises `ValueError(unknown_force_mode)`. |
| `test_flowmol3_v2_factory_accepts_force_mode_real` | `default_flowmol3adapter(force_mode='real')` accepted (no `TypeError(unexpected keyword)`). |
| `test_flowmol3_v2_factory_accepts_force_mode_synthetic` | `force_mode='synthetic'` → `backend='numpy'`. |
| `test_flowmol3_v2_factory_rejects_unknown_force_mode` | `force_mode='bogus'` → `ValueError(unknown_force_mode)`. |

All 9 pass:

```
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_metric_helper_returns_value_marker_dbg PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_metric_helper_returns_blocked_when_adapter_lacks_method PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_metric_helper_blocks_on_nan_reduction PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_wiring_alias_does_not_translate_real_to_torch PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_legacy_adapters_still_translate_real_to_torch PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v1_factory_accepts_torch_alias PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v2_factory_accepts_force_mode_real PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v2_factory_accepts_force_mode_synthetic PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v2_factory_rejects_unknown_force_mode PASSED
9 passed, 3 warnings in 0.32s
```

---

## 5. Real-ckpt eval results

```
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py --model flowmol3 \
    --force-mode real --metric-mode real --composite-metric real \
    --seeds 42,43,44 --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_real_metric_v2_q4_2026.json
```

| Marker | Wave 50 (before fix) | Wave 53 (after fix) |
|---|---|---|
| `baseline_marker` | `blocked` | `computed` (9/9 cells) |
| `framework_marker` | `blocked` | `computed` (9/9 cells) |
| `composite_marker` | `blocked` | `computed` (9/9 cells; FlowMol3Glue ran end-to-end) |
| `composite` value | `0.0` | `0.0` |
| `status` | `no_signal` | `TIE` (TIE_AT_SATURATION — placeholder arms are byte-identical) |

The **metric layer is no longer `blocked`** — the primary blocker
(Wave 50 Agent B Bug A + Bug B) is fixed. The `composite=0.0`
result is the expected outcome for the placeholder, per Agent A
§3.3 Option A (uniform reference): both arms produce uniform
atom-type distributions in synthetic mode → `H(uniform) -
H(uniform) = 0` → `reduction_value = 0.0` → both arms identical
→ composite collapses to 0 by construction.

The framework `delta_pct=0.0` / `signed_delta_pct=0.0` / `status=TIE`
is the **documented trivial reading of the synthetic shim**, not a
regression. To get `composite > 0` with `verdict=framework_improves`,
the follow-up waves need:

1. A real FlowMol3 PyTorch Lightning ckpt (v1 placeholder's
   `_try_load_real_ckpt` only inspects metadata; it doesn't run
   inference).
2. The upstream `flowmol` package + RDKit + xtb in a sidecar venv
   so `FlowMol3Glue.compute_chemistry_metrics` can produce
   non-zero `frac_valid_mols` / `frac_mols_stable`.
3. The v2 adapter's `vector_field` wired against the loaded
   `last.ckpt` (separate Wave 36 / Wave 50 scope).

Per Agent A §3.3: "Wave 53 ships Axis A (per-atom entropy
reduction) first; Axis B (RDKit `frac_valid_mols`) and Axis C
(upstream `SampleAnalyzer.analyze`) are follow-ups."

---

## 6. Verdict — Tier 3 FlowMol3 metric-axis

**Partial close.** The metric layer (Wave 50 Agent B Bug A — the
missing helper) is implemented and wired. The wiring mismatch
(Wave 50 Agent B Bug A + Bug B — `real → torch` translation)
is fixed across both v1 and v2 factories. The eval pipeline runs
end-to-end and the metric layer returns `marker=computed` instead
of `marker=blocked`.

The composite stays at `0.0` because the placeholder doesn't run
real inference — this is **expected** for the Wave 53 deliverable
per Agent A §3.3. The "framework_improves" verdict requires real
FlowMol3 ckpt + upstream packages, owned by follow-up waves.

**Files committed (no push):** 4 source files + 1 verification
artifact + 1 audit doc. All 9 regression tests pass.

---

## 7. What ships

```
A  docs/audit/wave53-flowmol3-metric-impl.md
A  tests/test_tools/test_run_real_ckpt_eval.py
M  adaptive_reflow/adapters/flowmol3.py
M  adaptive_reflow/adapters/flowmol3_v2_adapter.py
M  tools/run_real_ckpt_eval.py
?? verification_outputs/flowmol3_real_metric_v2_q4_2026.json   (gitignored)
```