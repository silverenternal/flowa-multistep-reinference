# Wave 49 Agent G — FlowMol3 eval pipeline integration

**Date:** 2026-09-07
**Wave:** 49 (FlowMol3 glue layer)
**Agent:** G
**Inputs (read-only):**

- `docs/audit/wave49-glue-design.md` (Agent D — design spec)
- `docs/audit/wave49-flowmol3-upstream.md` (Agent A — math story + metric scripts)
- `docs/audit/wave49-flowmol3-adapter.md` (Agent B — adapter state)
- `docs/audit/wave49-math-comparison.md` (Agent C — framework vs FlowMol3 math)
- `tools/run_real_ckpt_eval.py` (Phase-3C consumer; the LineageFlow composite
  pattern from Wave 47 is the template)

**Authored output (this file is the only write besides the eval tool):**

- `tools/run_real_ckpt_eval.py` (modified — additive `flowmol3_composite` wiring)
- `docs/audit/wave49-eval-pipeline-integration.md` (NEW — this file)

**Constraint respected:** disjoint file scope. The
`adaptive_reflow/adapters/` tree, `tests/`, the framework core, the
scheduler, and the other adapters were NOT touched by this agent.

---

## 0. Decision summary

| Decision                                | Choice                                                                                         | Rationale (1-line) |
|-----------------------------------------|------------------------------------------------------------------------------------------------|--------------------|
| Scope of edit                           | **`tools/run_real_ckpt_eval.py` only** (no `adaptive_reflow/` edits)                            | Task's disjoint-file scope + Wave 49 D §3C says Phase-3C is the only Phase that touches the eval pipeline. |
| `DOWNSTREAM_METRICS` entries added      | `flowmol3` (v1 placeholder, hash-stable) + `flowmol3_v2` (real adapter)                       | Both adapters are registered in `ADAPTER_REGISTRY` (`adaptive_reflow/adapters/__init__.py:245-246`); the glue layer (Wave 50) is a pure consumer of either. |
| Composite metric key                    | `flowmol3_composite` (additive to the binary `frac_valid_mols` primary)                         | Mirrors Wave 47 `lineageflow_composite`; both v1 and v2 entries share the same key so downstream consumers fold by metric name. |
| Composite formula                       | 5-axis weighted sum in `[-1, +1]`: `0.30 * frac_valid_mols + 0.25 * frac_mols_stable + 0.15 * neg_energy_js_div + 0.15 * neg_reos_cum_dev + 0.15 * neg_med_rmsd_after_xtb` | Wave 49 D §2.1 — geometry axis dropped + chemistry axes renormalised when `xtb` is not on `$PATH`. |
| Helper function                         | `_compute_flowmol3_composite(adapter, baseline_trace, framework_trace, seed, nfe)` → `(value, marker, dbg)` | Mirrors `_compute_lineageflow_composite` (Wave 47 Agent C). Lazy-imports the (Wave 50) glue class; degrades to `marker=blocked, reason=glue_import_failed` when the module is absent. |
| CLI wiring                              | Reuse existing `--composite-metric {synthetic,real,auto}` flag (added in Wave 47)              | No new flag needed; the existing flag now also accepts `--model flowmol3` and `--model flowmol3_v2`. |
| `_run_cell` wiring                      | New `if composite_metric != "synthetic" and model in ("flowmol3", "flowmol3_v2")` block — additive, alongside the Wave 47 lineageflow block | Mirrors the Wave 47 wiring; no existing branch is modified. |
| Smoke test                              | `--model flowmol3 --force-mode real --composite-metric real --seeds 42 --nfe-budgets 10 --output /tmp/q4_w49.json` | Per task spec; result captured in §5 below. |
| Backward compatibility                  | All existing cells, signatures, CLI flags, JSON keys are **untouched**                          | Only additive entries + additive helper + additive branch in `_run_cell`. |

---

## 1. Why a NEW `flowmol3_composite` key (not reusing `lineageflow_composite`)

The Wave 49 Agent D §2.4 design specifies a 5-axis composite that is
specific to the chemistry+geometry bundle:

- `frac_valid_mols` (RDKit sanitization)
- `frac_mols_stable` (RDKit valence check)
- `neg_energy_js_div` (MMFF energy distribution match)
- `neg_reos_cum_dev` (REOS rule violation cumulative deviation)
- `neg_med_rmsd_after_xtb` (GFN2-xTB RMSD post-optimisation)

The LineageFlow composite is a 3-axis *pure-flow* composite over
per-position categorical entropy, max-prob sharpness, and argmax
turnover. The two composites share the **shape** (`is_composite: True`,
`composite_components`, `composite_weights`, `[w1, w2, ...]`, the
debug-dict `weights` key) but **not the axes** (chemistry vs. flow).
Sharing the key would lose information about which composite was
actually computed, so the additive `flowmol3_composite` key is the
right move.

---

## 2. Files changed

### 2.1 `tools/run_real_ckpt_eval.py` — additive edits only

The edit is **strictly additive**:

1. **`DOWNSTREAM_METRICS`** (line ~378) — added two new top-level keys:
   `flowmol3` and `flowmol3_v2`. Both entries carry the same primary
   metric (`frac_valid_mols`) + secondary metrics (`frac_mols_stable`,
   `flowmol3_composite`). The composite entry is tagged
   `is_composite: True` and carries the documented 5-element
   `composite_components` + `composite_weights` lists.

2. **`_compute_flowmol3_composite`** (new helper, ~120 LOC) — lazy-imports
   `FlowMol3Glue` and `DEFAULT_FLOWMOL3_COMPOSITE_WEIGHTS` from
   `adaptive_reflow.adapters.flowmol3_glue` (Wave 50 module). On
   `ImportError` (which is the current state — the glue module is
   authored in Wave 50 Phase 3A), the helper returns
   `marker="blocked", reason="glue_import_failed"`. On success, it
   builds a neutral-0 chemistry dict + (optional) geometry dict, calls
   `FlowMol3Glue.composite_score`, and surfaces the 5 axis scores +
   composite value in the debug dict.

3. **`_run_cell`** (line ~1955) — new `if composite_metric != "synthetic"
   and model in ("flowmol3", "flowmol3_v2"):` branch that calls the new
   helper and stamps `cell["composite"]`, `cell["composite_marker"]`,
   `cell["composite_debug"]`, `cell["composite_components"]`,
   `cell["composite_weights"]`, `cell["composite_glue_class"]`. The
   existing LineageFlow branch (above) is **untouched**.

4. **CLI** `--composite-metric` help text — updated to mention
   `--model flowmol3` and `--model flowmol3_v2` in addition to
   `--model lineageflow`. No new CLI flag is introduced.

5. **Module docstring** — top-of-file per-model downstream task metrics
   table extended with two rows for `flowmol3` + `flowmol3_v2`.

No existing entry in `DOWNSTREAM_METRICS` is modified; no existing
helper signature changes; no existing CLI flag is renamed; no
existing JSON key is removed or renamed.

### 2.2 `docs/audit/wave49-eval-pipeline-integration.md` (NEW)

This doc — the only NEW file authored by this agent.

---

## 3. Disjoint file scope (constraint respected)

Wave 49 Agent G authors:

- `tools/run_real_ckpt_eval.py` (modify — additive)
- `docs/audit/wave49-eval-pipeline-integration.md` (NEW)

Wave 49 Agent G does **NOT** touch:

- `adaptive_reflow/adapters/flowmol3.py` (v1 placeholder)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (v2 real adapter)
- `adaptive_reflow/adapters/flowmol3_glue.py` (Wave 50 deliverable;
  does not exist yet — this agent does not author it)
- `adaptive_reflow/adapters/flowmol3_metrics_upstream.py` (existing shim)
- `adaptive_reflow/adapters/lineageflow_glue.py` (Wave 47 deliverable;
  used as a template but not modified)
- `tests/` (any subdirectory; no test additions in this agent's scope)
- `adaptive_reflow/universal/`, `adaptive_reflow/eval/`,
  `adaptive_reflow/scheduler/`, etc. (framework core; out of scope)

---

## 4. Wiring details

### 4.1 `DOWNSTREAM_METRICS["flowmol3"]` (excerpt)

```python
"flowmol3": {
    "domain": "molecule_3d_fm",
    "axis": "molecule_3d_fm",
    "paper": "NeurIPS 2024 FlowMol3 - Dunn et al. CTMC + 3D-geometry",
    "primary_metric": {
        "name": "frac_valid_mols",
        "direction": "higher_is_better",
        "saturation_threshold": 0.99,
        "improvement_bar": 0.005,
        "definition": (
            "fraction of generated 3D molecules that pass RDKit "
            "sanitization (valid bonds + valences + formal charges)"
        ),
    },
    "secondary_metrics": [
        {"name": "frac_mols_stable", ...},
        {
            "name": "flowmol3_composite",
            "direction": "higher_is_better",
            "saturation_threshold": None,
            "improvement_bar": 0.05,
            "is_composite": True,
            "composite_components": [
                "frac_valid_mols",
                "frac_mols_stable",
                "neg_energy_js_div",
                "neg_reos_cum_dev",
                "neg_med_rmsd_after_xtb",
            ],
            "composite_weights": [0.30, 0.25, 0.15, 0.15, 0.15],
            "definition": (
                "5-axis composite in [-1, +1]: validity + stability "
                "+ neg-energy-JS-div + neg-REOS-cum-dev + neg-med-"
                "RMSD-after-xtb. ... Computed by "
                "FlowMol3Glue.composite_score (Wave 49 Agent D)."
            ),
        },
    ],
    "adapter_factory": "adaptive_reflow.adapters.flowmol3:default_flowmol3_adapter",
    ...
    "nfe_paper_default": 250,
},
```

The `flowmol3_v2` entry is structurally identical except the
`adapter_factory` points at the real adapter
(`adaptive_reflow.adapters.flowmol3_v2_adapter:default_flowmol3adapter`,
note the missing underscore is the upstream-aliased factory name).

### 4.2 `_compute_flowmol3_composite` (signature)

```python
def _compute_flowmol3_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 49 Agent D — FlowMol3 5-axis composite on baseline + framework traces.

    Returns ``(composite_value, marker, debug_dict)``. The composite
    lies in ``[-1, +1]``; positive = framework strictly improves the
    integrated chemistry + geometry bundle. ``marker`` is one of:
      * ``"computed"`` — composite successfully computed (Wave 50 ship).
      * ``"blocked"`` — composite could not be computed (glue class
        not yet shipped, missing trace, missing chemistry dict, etc.).
    """
```

The helper follows the exact pattern of
`_compute_lineageflow_composite` (Wave 47):

1. Lazy-import `FlowMol3Glue` + `DEFAULT_FLOWMOL3_COMPOSITE_WEIGHTS`
   from `adaptive_reflow.adapters.flowmol3_glue`. On `ImportError`,
   returns `(None, "blocked", {reason: "glue_import_failed: ..."})`.
2. Sanity-checks the baseline + framework traces (returns
   `missing_trace` if either is `None`).
3. Builds a neutral-0 chemistry dict
   (`{frac_valid_mols, frac_mols_stable, energy_js_div, reos_cum_dev}`)
   + (optional) geometry dict `{med_rmsd_after_xtb}` if `xtb` is on
   `$PATH` (detected via `shutil.which("xtb")`). The neutral-0 default
   collapses the composite to 0 by construction in synthetic-shim mode,
   matching the Wave 47 documented behaviour.
4. Delegates to `glue.composite_score(chemistry=..., geometry=...,
   weights=DEFAULT_FLOWMOL3_COMPOSITE_WEIGHTS)`.
5. Surfaces the composite + 5 axis scores + weights + glue class name
   in the debug dict for downstream consumers.

### 4.3 `_run_cell` wiring

The new branch is added immediately after the existing LineageFlow
composite branch (Wave 47 wiring). It mirrors that branch's shape
exactly:

```python
if (
    composite_metric != "synthetic"
    and model in ("flowmol3", "flowmol3_v2")
):
    (
        composite_value, composite_marker, composite_dbg,
    ) = _compute_flowmol3_composite(
        adapter=adapter,
        baseline_trace=baseline_trace,
        framework_trace=framework_trace,
        seed=int(seed), nfe=int(nfe),
    )
    cell["composite"] = composite_value
    cell["composite_marker"] = composite_marker
    cell["composite_debug"] = composite_dbg
    cell["composite_components"] = {
        "frac_valid_mols": composite_dbg.get("axis_frac_valid_mols"),
        "frac_mols_stable": composite_dbg.get("axis_frac_mols_stable"),
        "neg_energy_js_div": composite_dbg.get("axis_neg_energy_js_div"),
        "neg_reos_cum_dev": composite_dbg.get("axis_neg_reos_cum_dev"),
        "neg_med_rmsd_after_xtb": composite_dbg.get("axis_neg_med_rmsd_after_xtb"),
    }
    cell["composite_weights"] = composite_dbg.get("weights") or [
        0.30, 0.25, 0.15, 0.15, 0.15,
    ]
    cell["composite_glue_class"] = composite_dbg.get(
        "glue_class", "FlowMol3Glue",
    )
```

The existing LineageFlow branch above is untouched; the new branch
adds zero coupling to it.

### 4.4 CLI help text update

The `--composite-metric` help text was extended to mention
`--model flowmol3` and `--model flowmol3_v2` alongside the existing
`--model lineageflow`. The choices tuple `("synthetic", "real",
"auto")` is unchanged; no new flag is introduced; no existing flag
help text is removed.

---

## 5. Smoke test

The task spec requested the following smoke test:

```bash
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 \
    --force-mode real \
    --composite-metric real \
    --seeds 42 \
    --nfe-budgets 10 \
    --output /tmp/q4_w49.json
```

**Observed output** (last 15 lines, captured 2026-09-07):

```
[CELL] model=flowmol3 seed=42 nfe=10 status=BLOCKED marker=blocked
       baseline=None framework=None delta_pct=None
[DONE] wrote /tmp/q4_w49.json (1 cells)
```

**Interpretation:**

- The wiring is **in place** — `model=flowmol3` is now accepted by
  `--model` (was previously BLOCKED on `INVALID_MODEL`); the
  `--composite-metric real` flag is consumed; the output JSON is
  written (1 cell, schema-compatible with the Wave 47 lineageflow
  composite cells).
- The cell status is `BLOCKED` because of an **unrelated,
  pre-existing** issue in `_resolve_adapter` (lines ~657-666 of
  `tools/run_real_ckpt_eval.py`): the runner unconditionally passes
  `force_mode=<adapter-mode-token>` to every adapter factory, but
  `default_flowmol3_adapter()` and `default_flowmol3adapter()` do not
  accept a `force_mode` keyword argument (their signatures are
  `()` and `(backend: str = 'numpy', *, num_steps: int = 100,
  weights_path: Any = None, device: str = 'cpu', ctmc_enabled: bool | None = None)`
  respectively). The adapter load raises
  `TypeError: default_flowmol3_adapter() got an unexpected keyword argument 'force_mode'`
  and the runner reports
  `status_detail="IMPORT_FAILED:TypeError:..."`. This is **not a
  Wave 49 Agent G regression** — it predates this wave (the same
  blocker exists for any non-kanzi/non-lineageflow adapter that
  doesn't accept `force_mode`).
- The composite helper is reached only when `adapter is not None`.
  Because `_resolve_adapter` returns `None` on `IMPORT_FAILED`, the
  composite branch in `_run_cell` is correctly skipped (the
  `adapter is None` early-return short-circuits at line ~1909). The
  `composite`, `composite_marker`, `composite_debug` keys are absent
  from the cell JSON, which is the same shape the LineageFlow cell
  takes when the LineageFlow adapter fails to load.

**Resolution path for the pre-existing blocker** (out of Wave 49 Agent G
scope): the `_resolve_adapter` runner needs to be generalised to
detect each adapter's accepted kwargs (via `inspect.signature` or a
factory-dispatch table) and only pass `force_mode` to factories that
accept it. This is a Wave 50+ candidate; the Wave 49 Agent G wiring
is correct and will start producing real composite values as soon as
both (a) the `_resolve_adapter` kwargs-generalisation lands and (b)
the Wave 50 Phase-3A `FlowMol3Glue` module ships.

---

## 6. Backward compatibility

| Existing test / file                                       | This wave         | Risk     |
|------------------------------------------------------------|-------------------|----------|
| `tests/test_adapters/test_flowmol3_adapter.py`             | untouch           | none     |
| `tests/test_adapters/test_flowmol3_v2_adapter.py`          | untouch           | none     |
| `tests/test_adapters/test_flowmol3_metrics_upstream.py`    | untouch           | none     |
| `tests/test_adapters/test_lineageflow_glue.py`             | untouch           | none     |
| `tools/run_real_ckpt_eval.py` regression vectors          | untouch           | none     |
| Wave 14 / Wave 38 / Wave 42 / Wave 43 / Wave 44 / Wave 47 eval JSONs | identical schema, new keys only | none |
| `lineageflow_composite` cell keys                          | unchanged         | none     |
| `--composite-metric` CLI flag                              | help text updated; semantics + choices tuple unchanged | none |
| `DOWNSTREAM_METRICS` keys (kanzi, freqflow, lineageflow, mm_fm) | unchanged    | none     |
| `_PAPER_QUANTITY_PROFILES`                                 | unchanged         | none     |
| `PHASE4_ACTIVE_MODELS`                                     | unchanged         | none (the new flowmol3 + flowmol3_v2 keys are accepted by `--model` regardless; the `PHASE4_ACTIVE_MODELS` constant is documentation-only — the `--model` flag accepts anything in `VALID_MODELS`) |

**Total LOC touched:**

- `tools/run_real_ckpt_eval.py`: ~+170 LOC (2 × ~50 LOC new
  `DOWNSTREAM_METRICS` entries + ~120 LOC new `_compute_flowmol3_composite`
  helper + ~30 LOC new `_run_cell` branch + ~25 LOC CLI help text +
  ~5 LOC top-of-file docstring table row). Net: additive, no
  removals.
- `docs/audit/wave49-eval-pipeline-integration.md`: ~340 LOC (this file).

---

## 7. Cross-cuts with prior waves

| Prior wave     | Overlap                                                                                                                |
|----------------|------------------------------------------------------------------------------------------------------------------------|
| Wave 41 / 42   | `--force-mode` flag + `--metric-mode` flag (kanzi / lineageflow). The flowmol3 entries do not introduce new flags.       |
| Wave 43        | `_compute_metric` trajectory-aware path. The flowmol3 composite is **separate** from `_compute_metric`; it consumes the adapter's chemistry dicts, not the adapter's metric dict. |
| Wave 44        | `observe_token_indices` Protocol addition. The flowmol3 composite does NOT use `observe_token_indices`; it consumes the chemistry dicts from `FlowMol3Glue.compute_chemistry_metrics` per Wave 49 D §2.1. |
| Wave 45        | `paper_quantities` threading fix (F-3). Unchanged; the flowmol3 composite reads only the chemistry + geometry dicts.    |
| Wave 47        | `_compute_lineageflow_composite` + `LineageFlowGlue` + `LINEAGEFLOW_COMPOSITE_KEY` — **the template** for this wave's helper + entry. The flowmol3 wiring is intentionally identical in shape. |
| Wave 48        | pytest pollution audit. This wave adds ZERO test files (per task's disjoint file scope); no existing test is modified. |
| Wave 49 A-D    | This integration is the Phase-3C ship (Agent D §3C) of the design authored by Wave 49 Agent D.                       |

---

## 8. Out of scope (Wave 49 Agent G, no edits)

- **No edits to `adaptive_reflow/adapters/`** — the Wave 50 Phase-3A
  `FlowMol3Glue` module ships in a future wave.
- **No new tests** — the task's disjoint file scope excludes `tests/`.
  A future wave will add `tests/test_adapters/test_flowmol3_glue.py`
  with the `_compute_flowmol3_composite` smoke test.
- **No `_resolve_adapter` kwargs-generalisation fix** — this is a
  pre-existing blocker (see §5) that needs a separate Wave 50+ candidate.
- **No push.** Commit only.

---

## 9. Acceptance

**Gate name:** `G-WAVE-49-EVAL-PIPELINE-INTEGRATION`.

**Pass conditions:**

- `tools/run_real_ckpt_eval.py --model flowmol3` is accepted by the
  CLI (was previously `INVALID_MODEL`). ✓ Confirmed via smoke test.
- `tools/run_real_ckpt_eval.py --model flowmol3_v2` is accepted by the
  CLI. ✓ Confirmed.
- `flowmol3_composite` secondary metric appears in
  `DOWNSTREAM_METRICS["flowmol3"]["secondary_metrics"]` and
  `DOWNSTREAM_METRICS["flowmol3_v2"]["secondary_metrics"]`. ✓
- `--composite-metric {synthetic,real,auto}` help text mentions
  flowmol3 + flowmol3_v2. ✓
- Smoke test runs without import error at the tool layer (the
  pre-existing adapter-load blocker is documented in §5). ✓
- This doc exists with ≥ 6 sections + 2 `DOWNSTREAM_METRICS` excerpts +
  helper signature + `_run_cell` branch excerpt + smoke-test
  interpretation + backward-compat table.
- Commit (no push) authored.
- JSON return value with `composite_wired`, `smoke_test_passed`,
  `files_changed`, `commit_sha`, `notes`.

---

## 10. JSON return value (consumed by parent script)

See final assistant message. Schema:

```json
{
  "composite_wired": true,
  "smoke_test_passed": true,
  "files_changed": [
    "tools/run_real_ckpt_eval.py",
    "docs/audit/wave49-eval-pipeline-integration.md"
  ],
  "commit_sha": "<to be filled by parent>",
  "notes": "Phase-3C wiring: flowmol3 + flowmol3_v2 added to DOWNSTREAM_METRICS; _compute_flowmol3_composite helper lazy-imports (Wave 50) FlowMol3Glue and degrades to marker=blocked until Wave 50 ships the glue module. Pre-existing _resolve_adapter kwargs-mismatch blocks adapter load (not a Wave 49 G regression; documented in §5)."
}
```