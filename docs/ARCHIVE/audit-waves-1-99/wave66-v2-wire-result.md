# Wave 66 Agent 1 — v2 FlowMol3 adapter wiring audit

Date: 2026-09-07
Branch: main (post-Wave 65; pre-push)
Scope: `tools/run_real_ckpt_eval.py::_resolve_adapter` factory dispatch
Outcome: wire active (v2 adapter now constructed for `force_mode in {real, auto}`); metric layer reports BLOCKED on the missing-observer hook (honest fail-closed).

## 1. Motivation (from Wave 65 §5.1 alternative)

Per the Wave 65 Agent 1 analysis, every FlowMol3 9-cell sweep cell ended in
`TIE_AT_SATURATION` because the v1 placeholder `FlowMol3Adapter.solve_ode` is a
hash-stable stub that does NOT integrate the real FlowMol3 ckpt. The metric
layer's `_compute_flowmol3_real_metric_via_trace` (added Wave 53) consumes
`adapter.observe_entropy_reduction(trace, ...)`, which the v1 placeholder
exposes but with a trivial uniform-vs-uniform reading. The v2 adapter at
`adaptive_reflow/adapters/flowmol3_v2_adapter.py` is the real integration
path; it exposes `observe_endpoint` (and an end-to-end CTMC velocity field on
the shipped 65 MB Lightning ckpt) but does NOT expose
`observe_entropy_reduction`. So pre-Wave-66:

* Wire v1 path: every cell `TIE_AT_SATURATION` (placeholder reading, no
  framework-vs-baseline delta).
* No v2 path: the eval pipeline never constructed the real adapter.

Wave 65 §5.1 recommended: "wire the v2 adapter into the eval pipeline so the
real model integrates, producing real per-atom entropy from the real FlowMol3
ckpt". Wave 66 Agent 1 implements the wire.

## 2. Code change (1-LOC branch in `_resolve_adapter`)

File: `tools/run_real_ckpt_eval.py`, function `_resolve_adapter` (lines
838-928). Pre-fix the factory path comes verbatim from
`DOWNSTREAM_METRICS[model]["adapter_factory"]`; the ``flowmol3`` entry
points at the v1 placeholder unconditionally.

Post-fix: when ``model == "flowmol3"`` AND the registry factory_path ends in
``:default_flowmol3_adapter`` (v1) AND ``force_mode in {"real", "auto"}``,
override ``factory_path`` to the v2 factory:

```diff
     spec = DOWNSTREAM_METRICS[model]
     factory_path = spec["adapter_factory"]
     if factory_path is None:
         return None, "BLOCKED"
+    # Wave 66 Agent 1 — wire v2 FlowMol3 adapter for real integration.
+    # The registry entry for ``flowmol3`` (v1) routes to the hash-based
+    # placeholder (``default_flowmol3_adapter``) which does NOT actually
+    # integrate the real FlowMol3 ckpt; the v2 adapter
+    # (``default_flowmol3adapter`` at
+    # ``adaptive_reflow.adapters.flowmol3_v2_adapter``) does. Switch
+    # the factory path to v2 when ``force_mode`` is real/auto so the
+    # real model integrates and the per-atom entropy surface is real
+    # (not the Wave 53 placeholder uniform-vs-uniform reading).
+    if (
+        model == "flowmol3"
+        and factory_path.endswith(":default_flowmol3_adapter")
+        and force_mode in {"real", "auto"}
+    ):
+        factory_path = (
+            "adaptive_reflow.adapters.flowmol3_v2_adapter:default_flowmol3adapter"
+        )
     module_path, attr = factory_path.rsplit(":", 1)
```

Net effect: 1 conditional block, ~12 LOC. The other 13 models are untouched
(the guard is `model == "flowmol3"`-scoped). The ``synthetic`` path is
preserved (the guard requires `force_mode in {"real", "auto"}`), so the
zero-dep CI path keeps using the v1 placeholder.

## 3. Regression tests added

File: `tests/test_tools/test_run_real_ckpt_eval.py`. Four new tests in
section "5. Bug D — flowmol3 v2 wiring for force_mode=real (Wave 66 Agent 1)":

1. `test_resolve_adapter_flowmol3_real_uses_v2` — when `force_mode='real'`,
   the constructed adapter's class name is `FlowMol3V2Adapter`, NOT
   `FlowMol3Adapter`. Uses a tolerant monkey-patch on the v2 factory so the
   test runs in CPU-only / no-ckpt CI envs without skipping.
2. `test_resolve_adapter_flowmol3_synthetic_uses_v1` — when
   `force_mode='synthetic'`, the constructed adapter's class name is
   `FlowMol3Adapter` (v1 placeholder), NOT `FlowMol3V2Adapter`. Guards
   against the wire accidentally redirecting synthetic traffic.
3. `test_resolve_adapter_flowmol3_auto_uses_v2` — when `force_mode='auto'`,
   the v2 adapter is constructed (same wire semantics as `real`).
4. `test_resolve_adapter_other_models_unaffected` — kanzi (an unrelated
   PHASE-4 model) does NOT route through FlowMol3; the v2 wire is scoped to
   `model == "flowmol3"` only.

All four tests pass (4 passed, 13 deselected, 3 warnings). The pre-existing
v1/v2 factory tests (`test_flowmol3_v2_factory_accepts_force_mode_real` and
siblings) continue to pass — the new tests add to, not replace, the existing
test surface.

Full pytest on `tests/test_adapters/test_flowmol3_adapter.py`:
**85 passed, 3 warnings** (no regression).

## 4. 9-cell sweep result (with v2 wired)

Command:

```bash
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 \
    --force-mode real \
    --metric-mode real \
    --composite-metric real \
    --seeds 42,43,44 \
    --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_v2_wired_q4_2026.json
```

Per-cell result:

| seed | nfe | status       | baseline_marker | framework_marker | baseline_debug.reason                  | framework_debug.reason                 | composite_marker |
|------|-----|--------------|-----------------|------------------|-----------------------------------------|----------------------------------------|------------------|
| 42   | 10  | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 42   | 50  | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 42   | 200 | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 43   | 10  | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 43   | 50  | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 43   | 200 | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 44   | 10  | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 44   | 50  | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |
| 44   | 200 | PENDING      | blocked         | blocked          | adapter_missing_observe_entropy_reduction | adapter_missing_observe_entropy_reduction | computed       |

Cell status = `PENDING` because the metric layer returns `value=None` for both
arms (the eval pipeline's exit code distinguishes PENDING/BLOCKED via
`baseline_marker`/`framework_marker`, both of which carry `marker="blocked"`
here). The cell is fail-closed: the runner does NOT fabricate a number when
the entropy surface is unavailable.

The composite layer (`flowmol3_composite`) reports `marker=computed` with
`composite=0.0` because the chemistry input dict is empty (the metric helper
never populated it). This is the documented Wave 49 Agent D fallback when
the chemistry metric is blocked.

Critically: **the wire is active**. The `adapter_mode` field on every cell is
`"real"` and the v2 class is constructed. The reason every cell is BLOCKED
is the missing-observer hook (`observe_entropy_reduction`), NOT the missing
v2 wire. To unblock the metric, the v2 adapter needs to expose
`observe_entropy_reduction` (or the metric helper needs to be taught the
v2-native path: `_compute_flowmol3_real_atom_type_marginal`).

## 5. Honest assessment

| Wave | Cell outcome (9 cells)                                             |
|------|--------------------------------------------------------------------|
| Wave 64 | 5/9 REGRESSION, 0/9 SUPPORTED, 4/9 TIE (Bug A — pre-Bug-A state) |
| Wave 65 | 0/9 REGRESSION, 0/9 SUPPORTED, 9/9 TIE (all TIE_AT_SATURATION)   |
| Wave 66 | 0/9 REGRESSION, 0/9 SUPPORTED, 0/9 TIE, **9/9 BLOCKED**          |

Wave 66 does NOT yet produce real SUPPORTED counts because the v2 adapter
does not expose the `observe_entropy_reduction` hook the metric helper
requires. The wire alone is necessary but not sufficient. Wave 66 Agent 1
delivers the wire; the missing follow-up is to either:

(a) teach `_compute_flowmol3_real_metric_via_trace` to consume the v2-native
    per-atom atom-type marginal via `_compute_flowmol3_real_atom_type_marginal`
    (the helper added by Wave 54 Agent A, which lazy-imports the v2
    `theta_after` directly); or

(b) teach `FlowMol3V2Adapter` to expose an `observe_entropy_reduction`
    shim that delegates to the v2-native `theta_after` computation.

Either option is a separate, larger change. Wave 66 Agent 1 was scoped to the
wire itself per the user directive.

**What Wave 66 DOES deliver**:

* The eval pipeline now constructs `FlowMol3V2Adapter` for every real
  FlowMol3 sweep cell. The wire is provably active in the JSON output
  (`adapter_mode="real"`; the v2 class is constructed in the regression
  tests).
* The pre-Wave-66 false-positive `TIE_AT_SATURATION` readings are now
  replaced with honest `BLOCKED` readings (no fabricated metric).
* The composite layer remains a separate code path (`composite_marker=
  computed` with `composite=0.0` from the empty chemistry input) — the
  glue class is wired but the input dict is empty until the metric helper
  populates it.

**What Wave 66 does NOT yet deliver**:

* Real per-atom entropy surface from the v2 adapter. The v2 exposes
  `observe_endpoint` (which materialises `(x, a, c, e)` at t=1) but not
  `observe_entropy_reduction` (the v1 hook). Closing this gap is the
  follow-up plan (option (a) or (b) above).
* A flipped SUPPORTED count. Until the metric helper is taught the v2
  surface, every cell remains BLOCKED. The honest reading is that the
  FlowMol3 Tier-3 claim is still INCONCLUSIVE — neither SUPPORTED nor
  REGRESSION nor TIE, just BLOCKED on the metric-axis gap.

## 6. Files changed (this commit)

| File                                                  | Change                                                                                  |
|-------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `tools/run_real_ckpt_eval.py`                         | +12 LOC: factory-path override for `flowmol3` v2 wiring (1 conditional block)           |
| `tests/test_tools/test_run_real_ckpt_eval.py`         | +~190 LOC: 4 regression tests + section header docstring                                |
| `docs/audit/wave66-v2-wire-result.md`                 | NEW (this file): wire audit + 9-cell table + honest assessment                          |

No other files were modified. No adapter files (`flowmol3.py`,
`flowmol3_v2_adapter.py`, `flowmol3_glue.py`) were touched — the wire is
localised to the eval pipeline's factory dispatch. The v2 adapter itself
remains unchanged per the user directive's "READ-ONLY reference, do not
modify" constraint.

## 7. Recommendations for follow-up waves

* **Wave 67 Agent 1 (recommended)**: extend `_compute_flowmol3_real_metric_via_trace`
  to detect the v2 adapter class (via `isinstance` or
  `type(adapter).__name__ == "FlowMol3V2Adapter"`) and route to
  `_compute_flowmol3_real_atom_type_marginal` instead of
  `observe_entropy_reduction`. This is the option (a) follow-up. It is a
  ~20-30 LOC change in the metric helper and unblocks the metric-axis for
  every FlowMol3 cell.
* **Wave 67 Agent 2 (alternative)**: add an `observe_entropy_reduction`
  shim to `FlowMol3V2Adapter` that delegates to the v2-native atom-type
  marginal. This is the option (b) follow-up. It is a ~10-15 LOC adapter
  change but keeps the metric helper single-path.
* Either way, Wave 67 should produce a real per-cell SUPPORTED count
  for FlowMol3 with v2 wired, closing the Wave 65 §5.1 alternative
  recommendation in full.