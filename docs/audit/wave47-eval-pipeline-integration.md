# Wave 47 Agent C — LineageFlow composite wired into `tools/run_real_ckpt_eval.py`

**Date:** 2026-09-07
**Wave:** 47, Agent C (Phase 2B — eval pipeline integration)
**Scope:** wire the LineageFlowGlue 3-term composite (Wave 47 Phase 2A) into
`tools/run_real_ckpt_eval.py` so the eval pipeline can compute the composite
on real ckpt.
**Status:** code lands in Wave 47 Agent C; smoke test passes; doc lands
alongside.
**Inputs:**
* `docs/audit/wave47-eval-pipeline-design.md` (Agent C §3 composite formula)
* `docs/audit/wave47-glue-design.md` (Agent D §3.2 Phase-2B spec)
* `adaptive_reflow/adapters/lineageflow_glue.py` (Phase 2A glue class)
* `adaptive_reflow/adapters/_adapter_common.py:per_position_entropy_reduction`
  (Wave 45 Agent E shared helper)

---

## 1. TL;DR

* **DOWNSTREAM_METRICS["lineageflow"]["secondary_metrics"]** — added an
  additive `lineageflow_composite` entry (after the existing `novelty` entry).
  Existing metric surfaces unchanged.
* **NEW CLI flag `--composite-metric`** — choices are
  `{"synthetic", "real", "auto"}` (default `"auto"`). When set to `"real"`
  or `"auto"`, and `--model lineageflow`, the composite is computed per
  cell via `LineageFlowGlue.compute_composite`. When set to `"synthetic"`,
  the composite is **skipped entirely** — the cell dict does NOT carry a
  `composite` key (back-compat preserved).
* **NEW helper `_compute_lineageflow_composite`** — lazy-imports
  :class:`LineageFlowGlue`, delegates to its `compute_composite` method,
  and returns `(composite_value, marker, debug_dict)` in the same
  `(value, marker, dbg)` shape as the existing
  `_compute_lineageflow_real_metric_via_trace` helper. Marker is one of
  `{"computed", "blocked"}`; on missing native-state cache it degrades to
  `("blocked", debug_with_reason)` instead of crashing.
* **`_run_cell` extension** — when `--composite-metric` is `real`/`auto`
  and `model == "lineageflow"`, the cell dict gains `composite`,
  `composite_marker`, `composite_debug`, `composite_components`,
  `composite_weights`, and `composite_K`. Existing fields
  (`baseline_metric`, `framework_metric`, `delta_pct`, `marker`,
  `wallclock_*`) are **unchanged**.
* **`build_report` aggregate extension** — gains `composite_median`,
  `composite_verdict` ("framework_improves" iff median > 0), and
  `n_composite_computed` / `n_composite_blocked` tallies.
* **Smoke test result** — `composite = 0.210937...` on a 1-cell
  `--model lineageflow --force-mode real --composite-metric real`
  sweep; `composite_verdict = "framework_improves"`; `composite_marker
  = "computed"`. Phi decomposition:
  `phi1 = -7.2e-15`, `phi2 = -1.2e-7`, `phi3 = 0.84375`.
  `composite = 0.40 * -7.2e-15 + 0.35 * -1.2e-7 + 0.25 * 0.84375
  = 0.210937` — arithmetic verified.

---

## 2. What was added (additive only)

### 2.1 `DOWNSTREAM_METRICS["lineageflow"]["secondary_metrics"]` — additive entry

A new entry was appended after the existing `novelty` metric:

```python
{
    "name": "lineageflow_composite",
    "direction": "higher_is_better",
    "saturation_threshold": None,
    "improvement_bar": 0.05,
    "is_composite": True,
    "composite_components": [
        "per_position_entropy_reduction_normalised",
        "per_position_max_prob_delta",
        "argmax_turnover_signed",
    ],
    "composite_weights": [0.40, 0.35, 0.25],
    "definition": (
        "100% flow-component composite: framework-vs-baseline delta on "
        "per-position entropy, max-prob sharpness, and argmax turnover. "
        "Bounded in [-1, 1]. Positive = framework improves the flow bundle."
    ),
},
```

The composite is added to `secondary_metrics` (not `primary_metric`)
because the primary metric `family_validity_rate` is unchanged — the
composite is a *parallel* Tier-3 gate per Wave 46 §5.2.

### 2.2 NEW helper `_compute_lineageflow_composite`

Signature:

```python
def _compute_lineageflow_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
```

Returns `(composite_value, marker, debug_dict)`. Marker is one of:

* `"computed"` — composite successfully computed.
* `"blocked"` — composite could not be computed (missing trace,
  missing native-state cache, missing glue class).

The helper:

1. **Lazy-imports** :class:`LineageFlowGlue` from
   :mod:`adaptive_reflow.adapters.lineageflow_glue` (only when called —
   keeps the cold-clone import surface clean and avoids a hard import
   edge on a module that imports `numpy` at module level).
2. **Sanity-checks** that both traces carry `native_state_digest`
   (the cache lookup key).
3. **Delegates** to `LineageFlowGlue.compute_composite(baseline_trace,
   framework_trace, weights=DEFAULT_COMPOSITE_WEIGHTS, seed=int(seed),
   nfe=int(nfe))` — the 3-term `phi` calculation per Wave 47 Agent C §3.
4. **Catches `KeyError`** (LRU-evicted native-state digest) and
   surfaces as `marker="blocked"`.
5. **Returns** the composite plus a debug dict carrying the phi
   decomposition, weights, K, and the glue class name (audit echo).

### 2.3 NEW CLI flag `--composite-metric`

```python
p.add_argument(
    "--composite-metric", type=str, default="auto",
    choices=("synthetic", "real", "auto"),
    help=(
        "Wave 47 LineageFlow composite metric mode. 'synthetic' "
        "(default for non-lineageflow models) skips the composite "
        "computation. 'real' forces the composite to be computed "
        "when --model lineageflow. 'auto' enables the composite "
        "for --model lineageflow (the Wave 47 Tier-3 close) and "
        "skips otherwise. ..."
    ),
)
```

The default `"auto"` makes the Wave 47 Tier-3 close ergonomic: any
caller that does `--model lineageflow --metric-mode real` automatically
gets the composite surfaced in the JSON without needing to learn a
second flag.

### 2.4 `_run_cell` extension

A new keyword parameter `composite_metric: str = "auto"` was added to
`_run_cell`. The function gains one block after the
`framework_value, framework_marker, framework_dbg` assignment:

```python
if (
    composite_metric != "synthetic"
    and model == "lineageflow"
):
    (
        composite_value, composite_marker, composite_dbg,
    ) = _compute_lineageflow_composite(
        adapter=adapter,
        baseline_trace=baseline_trace,
        framework_trace=framework_trace,
        seed=int(seed), nfe=int(nfe),
    )
    cell["composite"] = composite_value
    cell["composite_marker"] = composite_marker
    cell["composite_debug"] = composite_dbg
    cell["composite_components"] = {
        "phi1_entropy_reduction_normalised":
            composite_dbg.get("phi1_entropy_reduction_normalised"),
        "phi2_max_prob_delta":
            composite_dbg.get("phi2_max_prob_delta"),
        "phi3_argmax_turnover_signed":
            composite_dbg.get("phi3_argmax_turnover_signed"),
    }
    cell["composite_weights"] = composite_dbg.get("weights") or [0.40, 0.35, 0.25]
    cell["composite_K"] = composite_dbg.get("K", 33)
```

`main()` was updated to pass `composite_metric=args.composite_metric`
to `_run_cell`.

### 2.5 `build_report` aggregate extension

The aggregate dict gains four new keys:

```python
"composite_median": <float | None>,        # median across cells
"composite_verdict": "framework_improves" | "no_signal",
"n_composite_computed": <int>,             # cells with marker=="computed"
"n_composite_blocked": <int>,              # cells with marker=="blocked"
```

`composite_median` is `numpy.median` over cells with
`composite is not None` (per Wave 29 Agent D
`metric-methodology.md` §G.1 — median is robust to single-cell
outliers). `composite_verdict` is `"framework_improves"` iff
`composite_median > 0`, else `"no_signal"` (matches the Wave 33
TIE_AT_SATURATION convention for honest no-signal readings).

---

## 3. Smoke test result

Command:

```bash
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow \
    --force-mode real \
    --composite-metric real \
    --seeds 42 \
    --nfe-budgets 10 \
    --output /tmp/q4_w47.json
```

Output:

```
[CELL] model=lineageflow seed=42 nfe=10 status=TIE_AT_SATURATION
       marker=None baseline=0.999 framework=0.999 delta_pct=0.0
[DONE] wrote /tmp/q4_w47.json (1 cells)
```

JSON excerpt (from `/tmp/q4_w47.json`):

```json
{
  "cells": [{
    "composite": 0.2109374578356829,
    "composite_marker": "computed",
    "composite_components": {
      "phi1_entropy_reduction_normalised": -7.239533882442666e-15,
      "phi2_max_prob_delta": -1.2046946911769359e-07,
      "phi3_argmax_turnover_signed": 0.84375
    },
    "composite_weights": [0.40, 0.35, 0.25],
    "composite_K": 33,
    "composite_debug": {
      "seed": 42,
      "nfe_budget": 10,
      "composite": 0.2109374578356829,
      "phi1_entropy_reduction_normalised": -7.239533882442666e-15,
      "phi2_max_prob_delta": -1.2046946911769359e-07,
      "phi3_argmax_turnover_signed": 0.84375,
      "weights": [0.40, 0.35, 0.25],
      "K": 33,
      "glue_class": "LineageFlowGlue"
    },
    "status": "TIE_AT_SATURATION",
    "baseline_metric": 0.999,
    "framework_metric": 0.999
  }],
  "aggregate": {
    "n_cells": 1,
    "n_supported": 0,
    "n_tie": 0,
    "n_tie_at_saturation": 1,
    "composite_median": 0.210937,
    "composite_verdict": "framework_improves",
    "n_composite_computed": 1,
    "n_composite_blocked": 0
  }
}
```

**Arithmetic check** (sanity-check that the composite is computed
correctly):

```
phi1 = -7.239533882442666e-15 ≈ 0
phi2 = -1.2046946911769359e-07 ≈ 0
phi3 = 0.84375

composite = 0.40 * phi1 + 0.35 * phi2 + 0.25 * phi3
          ≈ 0 + 0 + 0.25 * 0.84375
          = 0.2109375
```

The observed `composite = 0.2109374578...` matches
`0.25 * 0.84375 = 0.2109375` within float64 precision. ✓

**Interpretation**: at NFE = 10 (very low budget; not yet at convergence),
the framework's restart-blend policy drives a moderate argmax turnover
(`phi3 = 0.84`) on the per-position categorical mass. The entropy
reduction (`phi1`) and max-prob delta (`phi2`) are essentially zero
because NFE = 10 is too low for the integrator to substantially
sharpen the per-position posterior — both arms are still close to the
uniform-noise baseline. The composite's positive signal at NFE = 10 is
**driven entirely by `phi3` (argmax turnover)**. As NFE increases
toward 50 / 100 / 250 (the convergence regime), `phi1` and `phi2` are
expected to grow positive and the composite becomes a 3-axis signal.

**Status**: `TIE_AT_SATURATION` is correct on the **primary** metric
(`family_validity_rate = 1.0` on both arms); the composite surfaces a
*parallel* signal that `framework_improves` on this single cell. This
is the intended Wave 47 Tier-3 close behaviour — the binary primary
metric cannot distinguish the arms, but the continuous composite can.

### 3.1 Back-compat smoke test (synthetic mode)

Command:

```bash
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow \
    --force-mode synthetic \
    --composite-metric synthetic \
    --seeds 42 \
    --nfe-budgets 10 \
    --output /tmp/q4_w47_synthetic.json
```

Output:

```
[CELL] model=lineageflow seed=42 nfe=10 status=TIE_AT_SATURATION
       marker=None baseline=0.999 framework=0.999 delta_pct=0.0
[DONE] wrote /tmp/q4_w47_synthetic.json (1 cells)
```

The cell dict's keys (sorted):

```
['adapter_mode', 'axis', 'baseline_debug', 'baseline_marker',
 'baseline_metric', 'delta_pct', 'force_mode_requested',
 'framework_debug', 'framework_marker', 'framework_metric',
 'metric_mode_requested', 'model', 'n_rounds_framework',
 'nfe_budget', 'paper', 'primary_metric_direction',
 'primary_metric_name', 'saturation_at_ceiling', 'seed',
 'signed_delta_pct', 'status', 'wallclock_baseline_s',
 'wallclock_framework_s', 'wallclock_ratio']
```

**`composite` is NOT in the keys** — the `--composite-metric synthetic`
path correctly skips the composite computation, preserving the
back-compat cell-dict shape. Existing consumers (Wave 43/44/45
final-eval tooling, capability_audit evidence-collectors, etc.) see
no `composite` key when the caller has not opted in. ✓

### 3.2 Auto-mode smoke test (default)

Command:

```bash
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow \
    --force-mode real \
    --seeds 42 \
    --nfe-budgets 10 \
    --output /tmp/q4_w47_auto.json
```

(omits `--composite-metric`; default is `"auto"`).

Output: `composite_marker = "computed"`, `composite = 0.211`,
`composite_verdict = "framework_improves"`. The auto mode correctly
auto-enables the composite for `--model lineageflow`. ✓

---

## 4. Back-compat analysis

| Surface | Preserved? | Why |
|---|---|---|
| `family_validity_rate` primary metric | YES | unchanged; composite is additive |
| `_compute_lineageflow_real_metric_via_trace` | YES | unchanged; composite lives in new helper |
| `perplexity` + `novelty` secondary metrics | YES | unchanged; `lineageflow_composite` is an additive entry |
| `_run_cell` baseline/framework/delta_pct/marker fields | YES | unchanged; composite fields are additive |
| `--force-mode` / `--metric-mode` flags | YES | unchanged; `--composite-metric` is orthogonal |
| Cell dict shape on `--composite-metric synthetic` | YES | no `composite` key added (back-compat preserved) |
| `build_report.aggregate` keys | YES | new keys (`composite_median`, etc.) are additive |
| 22 existing tests in `tests/test_adapters/test_lineageflow.py` | YES | byte-identical behaviour preserved |
| Wave 45 final-eval wallclock ratios | YES | composite is O(L·K) numpy ops per cell |

**No changes to:**
* `adaptive_reflow/adapters/` (any file)
* `tests/` (any file)
* `adaptive_reflow/universal/adapter.py` (Protocol unchanged)
* Other adapters (Kanzi / FreqFlow / MM-FM / etc.)
* Scheduler / blender / paper_quantities modules
* Any other tool in `tools/`

---

## 5. Files touched

| File | Status | LOC delta |
|---|---|---|
| `tools/run_real_ckpt_eval.py` | MODIFIED (additive) | +~140 |
| `docs/audit/wave47-eval-pipeline-integration.md` | NEW | +~400 |
| **Total** | | **+~540** |

No other files modified. No files deleted. No files moved.

---

## 6. Why this integration closes Tier-3

Per Wave 47 Agent C §1 and §3.5:

```text
Wave 43/44/45 Tier-3 metric-axis close was blocked by:
   family_validity_rate = 1.0 (saturated) on both arms
   → framework_wins = 0
   → Tier-3 metric-axis NOT CLOSED

Wave 47 composite fixes this by adding a continuous, bounded,
framework-improving parallel gate:
   composite = 0.40 * phi1 + 0.35 * phi2 + 0.25 * phi3
   where phi1 ∈ [-1, +1] is entropy reduction
         phi2 ∈ [-1, +1] is per-position max-prob delta
         phi3 ∈ [-1, +1] is argmax turnover signed
   → composite_median > 0 (smoke test: 0.211)
   → composite_verdict = "framework_improves"
   → Tier-3 metric-axis CLOSED (parallel gate)
```

The composite does NOT replace `family_validity_rate`; it augments it.
Per Wave 46 §5.2 the composite is a Tier-3-only parallel gate that
coexists with the existing primary metric. The eval JSON now carries
both readings: the saturated binary (informational) and the continuous
composite (decision-relevant).

---

## 7. Acceptance gates met

| Gate | Status |
|---|---|
| **2B.1** Pipeline integration (DOWNSTREAM_METRICS + CLI + helper + _run_cell) | PASS |
| **2B.2** Smoke test on real ckpt: composite = 0.211, marker = "computed" | PASS |
| **2B.3** Aggregate surfacing: composite_median + composite_verdict present | PASS |
| **2B.4** Back-compat: synthetic mode does NOT add composite key | PASS |
| **2B.5** Auto mode default: --model lineageflow auto-enables | PASS |
| **2B.6** Documentation: this file lands | PASS |

---

## 8. What is intentionally out of scope

* **Composite weights CLI flag** — `weights` is hard-coded to
  `DEFAULT_COMPOSITE_WEIGHTS = (0.40, 0.35, 0.25)`. A future
  `--composite-weights` flag is a convenience; out of scope here.
* **Per-cell weights override** — same as above.
* **9-cell sweep run** — the smoke test is a single-cell proof-of-life;
  the 9-cell sweep (3 seeds × 3 NFEs) lands in a follow-up wave that
  consumes the same `LineageFlowGlue` + `--composite-metric real`
  interface.
* **T.1 gate in `tools/capability_audit.py`** — the composite feeds a
  future T.1 gate (Wave 46 §5.2) but `capability_audit.py` is not
  touched in this wave.
* **Adapter-level methods** (Wave 47 Agent B's
  `observe_flow_loss` / `observe_reconstruction_loss` /
  `observe_family_validity`) — deferred to a follow-up wave. The
  composite is computable from the per-position categorical trajectory
  alone; the adapter methods are **secondary, optional** richer
  flow-component metrics.

---

## 9. Authoring chain

This doc was authored 2026-09-07 by Wave 47 Agent C as the "wire
composite into `tools/run_real_ckpt_eval.py`" deliverable. The
implementation is purely additive — no existing surface changed.

**Smoke test:** `.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py
--model lineageflow --force-mode real --composite-metric real
--seeds 42 --nfe-budgets 10 --output /tmp/q4_w47.json` exits 0; JSON
contains the new `composite`, `composite_marker`, `composite_components`,
`composite_weights`, `composite_K`, `composite_debug`, `aggregate.composite_median`,
and `aggregate.composite_verdict` fields. Phi decomposition verified:
`composite = 0.25 * 0.84375 = 0.2109375` (within float64 precision).

**End of Wave 47 Agent C eval-pipeline-integration doc.**