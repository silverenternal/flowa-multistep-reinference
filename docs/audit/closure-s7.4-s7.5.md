# Closure Agent D — §7.4 / §7.5 additive Tier 3 composite update (Wave 68 closure)

**Date:** 2026-09-07
**Wave:** 68 closure, Agent D
**Role:** Author additive Tier 3 composite updates in `docs/paper-draft.md`
§7.4 (LineageFlow byte-stable citation) + §7.5 (FlowMol3 closure
verdict update) — without rewriting §7.4 / §7.5 / §7.6 / §7.7
bodies, preserving the §7.7 NFE-aware section added by Wave 58
closure Agent B.
**Inputs read:**
- `docs/paper-draft.md` (current §7.4 / §7.5 / §7.7)
- `docs/audit/closure-flowmol3-sweep.md` (Agent C output — Wave 68 closure verdict)
- `docs/audit/wave52-kanzi-composite.md` (Kanzi composite — 9/9 framework_improves, median +0.170)
- `docs/audit/wave47-lineageflow-glue-impl.md` (LineageFlowGlue — composite +0.211 byte-stable)
- `docs/audit/closure-s7.7.md` (verify §7.7 in place)

---

## 1. Per-section diff summary

### 1.1 §7.4 LineageFlow (additive only — Wave 47 byte-stable)

| Edit | Old text (excerpt) | New text | Lines (post-edit) |
|---|---|---|---|
| +1 paragraph after aggregate | (none — pre-existing Wave 47 aggregate block) | "**Wave 47 byte-stable citation (closure Agent D).** The `composite_median = +0.210937`, `composite_verdict = "framework_improves"`, `n_cells = 1` (seed 42 NFE 10)..." paragraph confirming Wave 47 numbers are byte-stable, citing `wave47-lineageflow-glue-impl.md` + `LineageFlowGlue` class location + Wave 47 Agent B F-4 EsmModel dtype fix + Wave 47 Agent C `_compute_lineageflow_composite` wiring. | `docs/paper-draft.md:1691-1710` |

**No body deletion. No table change. No aggregate-field change.** The
existing `composite_median = +0.210937` and
`composite_verdict = "framework_improves"` (rounds to +0.211) at
`docs/paper-draft.md:1682-1683` are the **Wave 47 byte-stable
numbers** and remain unchanged. The new paragraph is a citation
additive, not a number update.

### 1.2 §7.5 FlowMol3 (additive only — Wave 68 closure verdict update)

| Edit | Old text (excerpt) | New text | Lines (post-edit) |
|---|---|---|---|
| +1 paragraph after Wave 53 implementation status | (none — pre-existing Wave 53 honest reading) | "**Wave 68 closure verdict update (Agent C — entropy-reduction metric unblocked; RDKit/xtb env-degraded).** Per `docs/audit/closure-flowmol3-sweep.md` (Wave 68 closure Agent C, re-run 2026-09-07), the 9-cell FlowMol3 sweep that was **9/9 BLOCKED** in Wave 68 Phase 5 ... is now **9/9 TIE_AT_SATURATION** with **real, finite, byte-stable** per-position entropy-reduction readings..." + cite commit `223a225` + fix locations `flowmol3_v2_adapter.py:3280-3284 + :3422-3437` + 2 regression tests | `docs/paper-draft.md:1822-1841` |
| +1 9-cell sweep table (replaces "placeholder uniform-vs-uniform" framing with real entropy-reduction reading) | (none — pre-existing placeholder table) | New 9-row table: per-cell `(baseline_marker, framework_marker, baseline_metric=0.07340423794186401, framework_metric=0.07340423794186401, delta_pct=0.0, status=TIE, composite=0.0000, composite_verdict=no_signal)` for seeds 42/43/44 × NFE 10/50/200 | `docs/paper-draft.md:1843-1853` |
| +1 aggregate block (Wave 68 closure, real metric) | (none — pre-existing Wave 50/53 aggregate) | New aggregate: `n_blocked = 0` (was 9 in W68 Phase 5), `n_real_computed = 9`, `composite_median = +0.0000` (still, RDKit/xtb env-degraded), `verdict_overall = TIE_AT_SATURATION` (now genuinely real), `g1_mean_signed_delta_pct = 0.0`, `observation_surface = observe_as_dict_protocol` | `docs/paper-draft.md:1855-1875` |
| +1 honest reading paragraph (Wave 68 closure supersedes Wave 53 placeholder) | (none — pre-existing Wave 53 honest reading retained) | "**Wave 68 closure honest reading (replaces the Wave 53 placeholder framing).** ... The metric layer is now real — entropy-reduction reads 0.07340423794186401 nats on every cell (byte-stable) ... The remaining `composite = +0.0000` reading is an **env-level degradation**, NOT a code bug: RDKit is not importable ... xtb is not on `$PATH` ..." | `docs/paper-draft.md:1877-1893` |
| +1 verdict evolution table | (none — pre-existing) | New 7-row table: W50 BLOCKED → W53 TIE (misleading) → W54 REGRESSION → W65 TIE → W66 BLOCKED → W68 BLOCKED → **W68 closure TIE_AT_SATURATION (real metric)** | `docs/paper-draft.md:1895-1903` |
| ~1 paragraph replace | "**What this means for the Tier 3 figure.** ... the bar represents 'metric layer placeholder,' NOT 'framework matched baseline at the saturation ceiling.'" | "**What this means for the Tier 3 figure.** ... per the **Wave 68 closure honest reading** above, the bar now represents '**env-level RDKit/xtb unavailability** — metric layer is real (entropy-reduction = 0.0734 nats, byte-stable), composite glue ran end-to-end on every cell, but chemistry + geometry axes read 0.0 because RDKit is not importable in this venv and xtb is not on `$PATH`,' NOT 'framework matched baseline at the saturation ceiling' and NOT 'metric layer placeholder.'" | `docs/paper-draft.md:1956-1974` |

**Wave 53 honest reading + placeholder table RETAINED** (not
deleted) — both are still factually correct historical record of the
Wave 53 implementation-gap-close state. The Wave 68 closure verdict
update is **additive on top** of the Wave 53 record, with explicit
"supersedes the Wave 53 placeholder framing" language in the new
honest reading.

### 1.3 §7.7 verification — INTACT

| Item | Status | Evidence |
|---|---|---|
| §7.7 NFE-aware section header at line 2107 | INTACT | `grep -n "^### §7\." docs/paper-draft.md` shows `2107:### §7.7 NFE-aware framework — extends baseline's saturation ceiling (Wave 58)` (shifted from 1991 by my additive insertions in §7.4 / §7.5 — section body is unchanged) |
| §7.7 subsections (§7.7.1 framing, §7.7.2 methodology, §7.7.3 Kanzi, §7.7.4 LineageFlow, §7.7.5 NFE-adaptive gate, §7.7.6 honest caveat) | INTACT | Section boundaries preserved at `docs/paper-draft.md:2123, 2139, 2162, 2209, 2258, 2312` (shifted down by 116 lines, body content identical) |
| §7.7 source citations (Kanzi 18/18, LineageFlow 1/9) | INTACT | Kanzi NFE scan table at §7.7.3, LineageFlow NFE scan at §7.7.4 — no edits to either subsection body |
| §7.7 NFE-adaptive gate code citation | INTACT | `adaptive_reflow/adapters/flowmol3.py:865-887` + `low_nfe_restart_gate` helper at `_adapter_common.py:239-273` — unchanged in §7.7.5 |

---

## 2. Citations

### 2.1 Wave 52 Kanzi composite (NOT modified — confirmed byte-stable in §7.3)

| Source | Value | Citation in §7.5 update |
|---|---|---|
| `verification_outputs/kanzi_real_composite_q4_2026.json` | 9 cells (3 seeds × 3 NFE), composite positive on every cell | cited via existing §7.3 reference (no change to §7.5) |
| `docs/audit/wave52-kanzi-composite.md` | `composite_median = 0.170175`, `composite_verdict = "framework_improves"`, `n_composite_computed = 9` | NOT cited in §7.5 update — Kanzi is in §7.3 and was already byte-stable |
| Wave 58 NFE scan (`verification_outputs/kanzi_nfe_scan_q4_2026.json`) | 18 cells (3 seeds × 6 NFE), σ within seed = 0.000000 | NOT cited in §7.5 update — Kanzi is in §7.3 / §7.7.3 |

### 2.2 Wave 47 LineageFlow composite (cited in §7.4 additive paragraph)

| Source | Value | Citation in §7.4 update |
|---|---|---|
| `verification_outputs/lineageflow_real_metric_v2_q4_2026.json` | 1/1 cell (seed 42, NFE 10), `composite = +0.210937`, `composite_verdict = "framework_improves"` | cited at `docs/paper-draft.md:1691-1704` (Wave 47 byte-stable paragraph) |
| `/tmp/q4_w47.json` (Wave 47 Agent A smoke test, gitignored) | per-cell phi1/phi2/phi3 + composite | cited at `docs/paper-draft.md:1697-1699` |
| `docs/audit/wave47-lineageflow-glue-impl.md` | Wave 47 Agent A LineageFlowGlue implementation record | cited at `docs/paper-draft.md:1701` |
| `adaptive_reflow/adapters/lineageflow_glue.py` | `LineageFlowGlue` class (264 LOC) | cited at `docs/paper-draft.md:1701-1702` |
| Wave 47 Agent B F-4 EsmModel dtype fix | 5-LOC `argmax(x_t, axis=-1).long()` before EsmModel encoder | cited at `docs/paper-draft.md:1703` |
| Wave 47 Agent C `_compute_lineageflow_composite` | DOWNSTREAM_METRICS wiring | cited at `docs/paper-draft.md:1703-1704` |

### 2.3 Wave 68 closure FlowMol3 sweep (cited in §7.5 additive verdict update)

| Source | Value | Citation in §7.5 update |
|---|---|---|
| `docs/audit/closure-flowmol3-sweep.md` | Wave 68 closure Agent C, re-run 2026-09-07 | cited at `docs/paper-draft.md:1822-1823` |
| `verification_outputs/flowmol3_closure_q4_2026.json` | 9 cells, all `status=TIE`, `baseline_metric = framework_metric = 0.07340423794186401` | NOT explicitly cited by path (file is gitignored) — values cited via the closure-flowmol3-sweep.md audit doc |
| `commit 223a225` | Wave 54 Phase 2 Fix — v2 observation dispatch + dict-keyed surface + defensive state=None guard | cited at `docs/paper-draft.md:1829` |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3280-3284` | observe() defensive guard for state=None | cited at `docs/paper-draft.md:1829-1830` |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3422-3437` | observe_as_dict() defensive guard for state=None | cited at `docs/paper-draft.md:1830` |
| 2 regression tests in `tests/test_adapters/test_flowmol3_v2_adapter.py` | `test_observe_with_state_none_returns_entropy_only` + `test_observe_as_dict_with_state_none_returns_entropy_kind` | cited at `docs/paper-draft.md:1831-1833` |
| `pytest` 118 passed (combined v1 + v2 adapter tests) | Wave 68 closure baseline + 2 new tests | cited at `docs/paper-draft.md:1833-1835` |
| 9-cell Wave 68 closure sweep table | per-cell `baseline_metric = framework_metric = 0.07340423794186401` (entropy_reduction, nats), `status = TIE` | at `docs/paper-draft.md:1843-1853` |
| Wave 68 closure aggregate block | `n_blocked = 0`, `n_real_computed = 9`, `verdict_overall = TIE_AT_SATURATION` (real), `composite_verdict = no_signal` (env-degraded) | at `docs/paper-draft.md:1855-1875` |
| Wave 68 verdict evolution table | W50 BLOCKED → W53 TIE (misleading) → W54 REGRESSION → W65 TIE → W66 BLOCKED → W68 BLOCKED → W68 closure TIE_AT_SATURATION | at `docs/paper-draft.md:1895-1903` |

---

## 3. File:line references

### 3.1 Edited file

| Path | Lines added | Lines removed | Sections touched | Sections untouched |
|---|---:|---:|---|---|
| `docs/paper-draft.md` | +116 | -10 | §7.4 aggregate block (additive paragraph), §7.5 Wave 53 paragraph (additive Wave 68 closure paragraph + table + aggregate block + honest reading + verdict evolution), §7.5 "What this means for the Tier 3 figure" (paragraph replace, additive content) | §7.1, §7.2, §7.3, §7.6, §7.7, §7.8, §7.9, §7.10, §8, References |

**`git diff --stat docs/paper-draft.md`:**

```
docs/paper-draft.md | 136 ++++++++++++++++++++++++++++++++++++++++++++++++----
1 file changed, 126 insertions(+), 10 deletions(-)
```

The 10 deletions are exclusively the replaced "What this means for the
Tier 3 figure" paragraph (placeholder framing → env-degraded framing).
No body text was deleted from any Tier 3 result table; all tables are
additive.

### 3.2 Section line numbers (post-edit)

| Section | Old line | New line | Δ |
|---|---:|---:|---:|
| §7.4 header | 1629 | 1629 | 0 |
| §7.4 additive paragraph end | (was at aggregate block) | 1710 | +20 (cumulative after aggregate block) |
| §7.5 header | 1779 | 1799 | +20 |
| §7.5 Wave 68 closure end | (was after Wave 53 implementation status) | 1903 | +104 (cumulative) |
| §7.5 Wave 53 honest reading | 1836 | 1905 | +69 |
| §7.5 "What this means" | 1848 | 1956 | +108 |
| §7.6 header | 1860 | 1976 | +116 |
| §7.7 header | 1991 | 2107 | +116 |
| §7.7 body content | (unchanged) | (unchanged) | 0 |

§7.7 body content is byte-stable — only the header line number
shifted (+116 lines, equal to total §7.4 + §7.5 additions).

### 3.3 Code citations referenced (not modified)

| File | Lines | Reference |
|---|---|---|
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | 3280-3284 | `observe()` defensive guard for `state=None` (Wave 54 Phase 2 Fix, commit `223a225`) |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | 3422-3437 | `observe_as_dict()` defensive guard for `state=None` (Wave 54 Phase 2 Fix, commit `223a225`) |
| `adaptive_reflow/adapters/lineageflow_glue.py` | (file 264 LOC) | `LineageFlowGlue` class (Wave 47 Agent A) |
| `adaptive_reflow/adapters/flowmol3.py` | 865-887 | NFE-adaptive restart gate (cited in §7.7.5, not modified by this closure) |
| `adaptive_reflow/adapters/_adapter_common.py` | 239-273 | `low_nfe_restart_gate` helper (cited in §7.7.5, not modified by this closure) |

### 3.4 Audit docs referenced (not modified)

| Path | Role |
|---|---|
| `docs/audit/closure-flowmol3-sweep.md` | Wave 68 closure Agent C — 9/9 BLOCKED → 9/9 TIE_AT_SATURATION |
| `docs/audit/wave52-kanzi-composite.md` | Wave 52 Agent A — Kanzi composite 9/9 framework_improves, median +0.170 |
| `docs/audit/wave47-lineageflow-glue-impl.md` | Wave 47 Agent A — LineageFlowGlue class |
| `docs/audit/closure-s7.7.md` | Wave 58 closure Agent B — §7.7 NFE-aware section author |

---

## 4. Constraints honoured

| Constraint | Status | Evidence |
|---|---|---|
| ADDITIVE — DO NOT rewrite §7.4 / §7.5 / §7.6 | PASS | §7.4 body unchanged; §7.5 Wave 53 honest reading + placeholder table RETAINED (additive Wave 68 closure verdict update on top); §7.6 untouched |
| Update only the Tier 3 composite claim paragraphs and verdict lines | PASS | §7.4 +20 lines (Wave 47 byte-stable citation); §7.5 +96 lines (Wave 68 closure verdict update + table + aggregate + honest reading + verdict evolution); §7.5 -10 lines (only the replaced "What this means for the Tier 3 figure" paragraph, body content preserved as env-degraded framing) |
| Cite FlowMol3 verdict from closure-flowmol3-sweep.md | PASS | Closure audit doc cited at `docs/paper-draft.md:1822-1823`; verdict evolution table at `docs/paper-draft.md:1895-1903`; honest reading cites the doc at `docs/paper-draft.md:1877-1878` |
| Cite Kanzi + LineageFlow composite numbers from Wave 47/52 audits | PASS | Wave 47 LineageFlow citation at `docs/paper-draft.md:1691-1704` (cite `wave47-lineageflow-glue-impl.md`); Wave 52 Kanzi NOT explicitly cited in §7.5 (Kanzi lives in §7.3 — byte-stable since Wave 52) |
| No push | PASS | `git commit` only; not pushed |

---

## 5. Honest caveats

1. **§7.4 LineageFlow is single-cell (1/9).** The composite
   `+0.210937` rests on a single computed cell (seed=42, NFE=10).
   The 8 remaining NFE-scan cells (NFE=50/200/500/1000/2000) remain
   `pending_cpu_bandwidth` pending GPU re-sweep. The Wave 47 byte-stable
   citation additive paragraph explicitly states this in
   `docs/paper-draft.md:1705-1708`.
2. **§7.5 FlowMol3 composite still 0.0 (env-degraded).** The
   Wave 68 closure honest reading supersedes the Wave 53 placeholder
   framing but does NOT change the composite value (`+0.0000`). The
   metric layer is now real (entropy-reduction = 0.0734 nats,
   byte-stable), but RDKit is not importable in the FlowMol3 venv
   and xtb is not on `$PATH`. Installing RDKit (e.g. `pip install
   rdkit-pypi` in the FlowMol3 sidecar venv) and xtb on `$PATH` will
   unblock the chemistry + geometry axes. This is an env-level
   degradation, NOT a code bug.
3. **§7.7 body content unchanged.** Only the line numbers shifted
   (+116 lines, equal to total §7.4 + §7.5 additions). All §7.7
   subsection bodies, citations, code references, and honest caveats
   are byte-stable.

---

## 6. Output JSON

```json
{
  "s7_4_updated": true,
  "s7_5_updated": true,
  "s7_7_intact": true,
  "kanzi_updated": false,
  "lineageflow_updated": true,
  "flowmol3_updated": true,
  "files_changed": [
    "docs/paper-draft.md",
    "docs/audit/closure-s7.4-s7.5.md"
  ],
  "commit_sha": "<filled after commit>",
  "notes": [
    "§7.4 LineageFlow: ADDITIVE Wave 47 byte-stable citation paragraph (no body deletion, no number change). composite_median = +0.210937 (rounds to +0.211), composite_verdict = framework_improves, n_cells = 1 (seed 42 NFE 10) are byte-stable since Wave 47 Agent A (smoke test /tmp/q4_w47.json, LineageFlowGlue class at adaptive_reflow/adapters/lineageflow_glue.py, F-4 EsmModel dtype fix). 8/9 cells remain pending_cpu_bandwidth pending GPU re-sweep.",
    "§7.5 FlowMol3: ADDITIVE Wave 68 closure verdict update (no body deletion of Wave 53 record). 9/9 BLOCKED (Wave 68 Phase 5) → 9/9 TIE_AT_SATURATION (real metric, byte-stable) after Wave 54 Phase 2 Fix (commit 223a225) added callee-side defensive guards at flowmol3_v2_adapter.py:3280-3284 (observe) + :3422-3437 (observe_as_dict). All 9 cells: baseline_metric = framework_metric = 0.07340423794186401 (entropy_reduction, nats), delta_pct = 0.0, status = TIE. Composite still 0.0 because RDKit is not importable in FlowMol3 venv + xtb not on $PATH — env-level degradation, NOT a code bug. Verdict evolution table shows W50 BLOCKED → W53 TIE (misleading) → W54 REGRESSION → W65 TIE → W66 BLOCKED → W68 BLOCKED → W68 closure TIE_AT_SATURATION.",
    "§7.7 NFE-aware section INTACT at line 2107 (shifted +116 from line 1991, body content byte-stable). All 6 subsections preserved: §7.7.1 framing, §7.7.2 NFE scan methodology, §7.7.3 Kanzi 18/18 cells, §7.7.4 LineageFlow 1/9 cells, §7.7.5 NFE-adaptive restart gate (file:line refs intact), §7.7.6 honest caveat.",
    "git diff --stat docs/paper-draft.md: 1 file changed, 126 insertions(+), 10 deletions(-). The 10 deletions are exclusively the replaced 'What this means for the Tier 3 figure' paragraph (placeholder framing → env-degraded framing). All result tables are additive.",
    "Wave 52 Kanzi composite NOT re-cited in §7.5 — Kanzi lives in §7.3 and is byte-stable since Wave 52 Agent A (composite_median = 0.170175, composite_verdict = framework_improves, n_composite_computed = 9). The §7.3 numbers were already in the paper at the start of this closure pass.",
    "No source code change. No pytest run. No build run. Pure additive paper-draft.md edit + audit doc. Closure verification-only operation."
  ]
}
```
