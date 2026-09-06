# Wave 50 Agent B — FlowMol3 real-ckpt composite eval (Tier 3 metric-axis)

**Date:** 2026-09-07
**Agent:** Wave 50 Agent B
**Result:** **tier 3 flowmol3 metric-axis NOT closed** — composite = 0.0,
verdict = `no_signal`. Composite is computed (FlowMol3Glue ran end-to-end on
all 9 cells) but every phi term is 0 because the primary
`frac_valid_mols` metric is still `None` (no real-ckpt metric implementation
exists for `flowmol3`). The blocker is the missing **per-model metric
layer**, not the framework composite wiring.

---

## 1. Setup

### 1.1 Checkpoint

| Field | Value |
|-------|-------|
| Path | `data/flowmol3/weights_real/checkpoints/last.ckpt` |
| Size | 68 024 443 bytes (≈ 65 MB on disk) |
| mtime | 2026-09-01 01:31 |
| Format | PyTorch Lightning `last.ckpt` |
| n_tensors | 475 |
| epoch | 17 |
| global_step | 1 547 236 |
| pytorch-lightning_version | 2.1.3 |

### 1.2 Command

The task specified:

```
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real --metric-mode real \
    --composite-metric real --seeds 42,43,44 --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_real_composite_q4_2026.json
```

**First run (literal):** All 9 cells returned `status=BLOCKED,
status_detail=IMPORT_FAILED:ValueError:unknown_force_mode:torch (expected
'synthetic' | 'real' | 'auto')`. Root cause: the eval pipeline translates
`force_mode="real"` to `adapter_force_mode="torch"` at
`tools/run_real_ckpt_eval.py:797`, but Agent A's factory only accepts
`{"synthetic", "real", "auto"}` — not the legacy `"torch"` token used by
the kanzi/lineageflow adapters.

**Workaround run:** `--force-mode auto` (no translation needed — pipeline
forwards `"auto"` straight through). This is the result saved to
`verification_outputs/flowmol3_real_composite_q4_2026.json`.

### 1.3 Environment

| Key | Value |
|-----|-------|
| lock_hash | `983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092` |
| python_version | Python 3.12.13 |
| torch_version | torch:2.7.0+cu128+cuda12.8 |
| adapter_deps_hash | `c3c0294d0795e89e89c567a8da52002a825257df893c173b2fac6b4e734e0beb` |
| composite_hash | `193e049e8189a69ad704ab4c601390c6d214746809cc3719868dd849745ac9fe` |
| Force mode requested | `auto` (translated: skipped; pipeline forwards "auto" verbatim) |
| Adapter mode returned | `auto` |
| venv | `.venvs/flowmol3_venv` |

---

## 2. Aggregate

```json
{
  "n_cells": 9,
  "n_supported": 0,
  "n_tie": 0,
  "n_tie_at_saturation": 0,
  "n_regression": 0,
  "n_pending": 9,
  "n_blocked": 0,
  "n_run_error": 0,
  "n_real_computed": 0,
  "n_synthetic_fallback": 0,
  "composite_median": 0.0,
  "composite_verdict": "no_signal",
  "n_composite_computed": 9,
  "n_composite_blocked": 0,
  "g1_mean_signed_delta_pct": null,
  "verdict_overall": "TIE_AT_SATURATION"
}
```

- **`n_composite_computed = 9`** — FlowMol3Glue ran end-to-end on every cell.
- **`composite_median = 0.0`**, **`composite_verdict = no_signal`** — every
  phi term is 0 because the primary metric (`frac_valid_mols`) is `None`
  for both baseline and framework.
- **`n_pending = 9`**, **`n_real_computed = 0`** — `_compute_metric`
  returns `marker=blocked` with `reason="no real-ckpt metric
  implementation for model='flowmol3'"`.
- **`g1_mean_signed_delta_pct = null`** — the primary metric axis has no
  data; the metric-axis Tier 3 claim cannot be evaluated.

> **Important:** `verdict_overall = "TIE_AT_SATURATION"` is **misleading**
> — it is the default label when no cells have a real metric value. It
> does **not** mean the framework matched FlowMol3 at the saturation
> ceiling. The honest verdict is **NO SIGNAL** (composite cannot be
> evaluated because the metric layer is missing).

---

## 3. Per-cell results

| seed | nfe | composite | status | baseline_metric | framework_metric |
|------|-----|-----------|--------|-----------------|------------------|
| 42 | 10 | 0.0000 | PENDING | None | None |
| 42 | 50 | 0.0000 | PENDING | None | None |
| 42 | 200 | 0.0000 | PENDING | None | None |
| 43 | 10 | 0.0000 | PENDING | None | None |
| 43 | 50 | 0.0000 | PENDING | None | None |
| 43 | 200 | 0.0000 | PENDING | None | None |
| 44 | 10 | 0.0000 | PENDING | None | None |
| 44 | 50 | 0.0000 | PENDING | None | None |
| 44 | 200 | 0.0000 | PENDING | None | None |

All 9 cells share the same pattern:
- `baseline_marker = "blocked"`, `baseline_debug.reason = "no real-ckpt metric implementation for model='flowmol3'"`
- `framework_marker = "blocked"`, same reason
- `composite_marker = "computed"` (FlowMol3Glue ran), but
  `composite = 0.0` because all phi terms are 0 / None
- `wallclock_baseline_s = 0.0`, `wallclock_framework_s ≈ 0.001`
  (placeholder adapter; no actual ODE solve yet)
- `composite_glue_class = "FlowMol3Glue"` — confirms the glue wired in
  Wave 49 Agent E is the one being invoked.

### 3.1 Phi-term decomposition

| Phi | Definition | Value | Why |
|-----|------------|-------|-----|
| phi1 | frac_valid_mols | 0.0 | primary metric is None |
| phi2 | frac_mols_stable | 0.0 | primary metric is None |
| phi3 | neg_energy_js_div | -0.0 | chemistry input `energy_js_div = 0.0` |
| phi4 | neg_reos_cum_dev | -0.0 | chemistry input `reos_cum_dev = 0.0` |
| phi5 | neg_med_rmsd_after_xtb | None | `xtb_present = False` (xtb not on $PATH) |

Weights after `renormalize_for_geometry`:
`[0.3529, 0.2941, 0.1765, 0.1765, 0.0]` (phi5 dropped).

Composite formula:
```
composite = 0.3529·phi1 + 0.2941·phi2 + 0.1765·phi3 + 0.1765·phi4 + 0·phi5
          = 0.3529·0 + 0.2941·0 + 0.1765·(-0) + 0.1765·(-0) + 0·None
          = 0.0
```

The composite math is correct — it just has no signal to aggregate.

---

## 4. Honest reading

### 4.1 What works (post Agent A factory fix)

1. **Factory accepts `force_mode`**: `default_flowmol3_adapter(force_mode="real")`
   no longer raises `TypeError`. Verified at import time — `_force_mode =
   "real"`, `_real_ckpt_meta = {path, n_tensors=475, epoch=17, global_step=1547236, lightning_version=2.1.3}`.
2. **Real ckpt loads**: `_try_load_real_ckpt` reads the 65 MB
   `last.ckpt` from `data/flowmol3/weights_real/checkpoints/` and
   extracts the Lightning metadata. No I/O errors. No torch import
   errors.
3. **Composite glue runs end-to-end**: FlowMol3Glue.composite_score
   executes on all 9 cells; the auto-degrade for missing geometry
   (`xtb_present = False`) and renormalize-for-geometry weight logic
   both fire correctly.
4. **Eval pipeline accepts `--composite-metric real`** and dispatches
   to the `_compute_flowmol3_composite` helper. The composite metric
   wiring from Wave 49 Agent D is intact.

### 4.2 What does NOT work

1. **The eval pipeline translates `real → torch` for the adapter**
   (`tools/run_real_ckpt_eval.py:797`), but Agent A's factory does not
   accept `"torch"`. The literal `--force-mode real` invocation
   therefore BLOCKED every cell with a `ValueError` in `_resolve_adapter`.
   This is a **wiring mismatch** between Agent A's factory and the
   eval pipeline. `auto` is the only force-mode that flows through
   cleanly.
2. **There is no `_compute_flowmol3_real_metric` (or equivalent)**
   anywhere in `tools/run_real_ckpt_eval.py`. The metric layer for
   flowmol3 was never authored — `_compute_metric` returns
   `(None, "blocked", {"reason": "no real-ckpt metric implementation
   for model='flowmol3'"})`. This was true before Wave 50 and remains
   true after. Without a real chemistry metric, the 5-axis composite
   is forced to zero on all cells.
3. **The placeholder adapter has no `vector_field` that runs against
   the real FlowMol3 ckpt**. Agent A's fix only loads the ckpt and
   records metadata; it does not bind `state_dict` weights into a
   runnable `vector_field`. That is the `flowmol3_v2_adapter`'s job,
   and the v2 adapter also lacks a real-ckpt metric layer.

### 4.3 Why composite = 0 is the honest answer

The composite = 0 verdict is **not** a framework failure and **not** a
regression — it is a **missing-data signal**. The composite math is
being applied to an empty input vector because the per-model metric
layer that feeds it has never been implemented. The framework glue
(`FlowMol3Glue`) is wired correctly, the factory fix is wired correctly,
the eval pipeline dispatcher is wired correctly — but the chemistry
metric that produces the per-cell `frac_valid_mols` value still does
not exist for `flowmol3`.

---

## 5. Recommendations

### 5.1 Immediate (Wave 51)

Add `_compute_flowmol3_real_metric(adapter, baseline_trace,
framework_trace, ...)` to `tools/run_real_ckpt_eval.py`, parallel to
`_compute_kanzi_real_metric` and `_compute_lineageflow_real_metric`
authored in Wave 43 Agent A. This metric must:

- Sample a batch from both `baseline_trace` and `framework_trace` (the
  FlowMol3 placeholder returns raw atom-type / bond-type sequences).
- Decode to RDKit `Mol` objects via the upstream FlowMol3 decode path
  (or the `flowmol3_v2_adapter`'s built-in decoder if it has one).
- Compute `frac_valid_mols` = mean(RDKit `Chem.SanitizeMol` success)
  and `frac_mols_stable` = mean(chemistry sanitization success).

Without this, no framework composite can be measured for flowmol3 on a
real ckpt.

### 5.2 Factory fix follow-up (Wave 51 or later)

Two options to resolve the `real → torch` wiring mismatch:

**Option A (factory-side, preferred):** Extend Agent A's
`default_flowmol3_adapter` to also accept `"torch"` as an alias for
`"real"` — this matches the legacy token used by kanzi/lineageflow and
makes `--force-mode real` work without pipeline changes. One-line edit:

```python
if force_mode == "torch":
    force_mode = "real"
```

**Option B (pipeline-side):** Modify
`tools/run_real_ckpt_eval.py:797` to special-case `flowmol3` and skip
the `"torch"` translation. This is more invasive (touches the eval
pipeline) and creates per-model special cases — Option A is cleaner.

### 5.3 Real-ckpt sample decode (Wave 52+)

Even after the metric layer is in place, the placeholder
`FlowMol3Adapter.vector_field` will return token indices, not 3D
coordinates. The `flowmol3_v2_adapter` is the model that actually runs
inference against the loaded state dict — but it currently lives in a
sidecar venv (`flowmol3_venv` does not have the upstream FlowMol3
package installed). Verifying that the v2 adapter can decode samples
from the loaded ckpt is a prerequisite for any real-ckpt metric to
produce non-trivial values.

---

## 6. What did NOT close

| Tier 3 claim | Status |
|--------------|--------|
| flowmol3 metric-axis (composite > 0 with framework_improves verdict) | **NOT CLOSED** — composite = 0.0, verdict = no_signal, primary metric = None |

The Wave 50 factory fix (Agent A) + composite glue (Wave 49 Agent E) +
metric wiring (Wave 49 Agent D) form a **complete pipeline architecture**
for measuring flowmol3 on a real ckpt — but the pipeline has no data
to process because the real chemistry metric layer is still missing.
This is the single remaining blocker.

---

## 7. Files

| Path | Status |
|------|--------|
| `verification_outputs/flowmol3_real_composite_q4_2026.json` | NEW (gitignored) — 9-cell eval output |
| `docs/audit/wave50-flowmol3-real-eval.md` | NEW — this doc |
| `adaptive_reflow/adapters/flowmol3.py` | **Agent A owns this** — factory fix in working tree, not committed |
| `tools/run_real_ckpt_eval.py` | out of scope (Agent A only modified `flowmol3.py`) |

## 8. Verdict

**TIER 3 FLOWMOL3 METRIC-AXIS: STILL OPEN.** Composite is 0 because the
per-model chemistry metric layer (`_compute_flowmol3_real_metric`) was
never authored. The factory fix and composite glue are wired correctly;
the missing piece is the metric layer that produces non-trivial
`frac_valid_mols` values from real-ckpt samples.
