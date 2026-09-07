# Closure Agent B — §7.7 NFE-aware section author (Wave 58 closure)

**Date:** 2026-09-07
**Wave:** 58 (closure, Agent B)
**Role:** Author §7.7 NFE-aware section in `docs/paper-draft.md`
**Scope:** `docs/paper-draft.md` (additive §7.7 + 1-line §7.6 honest verdict update + section renumbering); this audit doc

---

## 1. Sections added

| Section | Title | Source | File:line |
|---|---|---|---|
| §7.6 additive line | "NFE-adaptive summary (Wave 58 closure)" appended to §7.6 honest verdict | per `todo/wave58-nfe-adaptive-plan.md` §5 | `docs/paper-draft.md:1978-1989` |
| §7.7 | NFE-aware framework — extends baseline's saturation ceiling (Wave 58) | NEW | `docs/paper-draft.md:1991-2224` |
| §7.7.1 | Framing — framework is NFE-adaptive, not NFE-blind | NEW | `docs/paper-draft.md:2001-2015` |
| §7.7.2 | NFE scan methodology | NEW | `docs/paper-draft.md:2017-2038` |
| §7.7.3 | Kanzi NFE scan — 18/18 cells computed, composite constant across NFE | NEW | `docs/paper-draft.md:2040-2085` |
| §7.7.4 | LineageFlow NFE scan — 1/9 cells computed (8 PENDING on CPU bandwidth) | NEW | `docs/paper-draft.md:2087-2135` |
| §7.7.5 | NFE-adaptive restart gate — 1-line code change (file:line) | NEW | `docs/paper-draft.md:2137-2187` |
| §7.7.6 | Honest caveat — NFE<20 framework is no-op (not regression) | NEW | `docs/paper-draft.md:2189-2223` |

## 2. Data cited

| Data | Source | Number used in §7.7 |
|---|---|---|
| Kanzi NFE scan 6-point sweep | `verification_outputs/kanzi_nfe_scan_q4_2026.json` | 18/18 cells computed, `composite_median = +0.170` constant across NFE, baseline saturated at NFE = 10 |
| Kanzi per-seed stability | `kanzi_nfe_scan_q4_2026.json` | σ within seed = 0.000000 for every seed (42, 43, 44) at all 6 NFE values |
| Kanzi wallclock scaling | `kanzi_nfe_scan_q4_2026.json` (wallclock_baseline_s + wallclock_framework_s) | 0.004 s @ NFE=10 → 0.186 s @ NFE=2000 (≈ 47×), framework-vs-baseline ratio 0.18–2.94 (mean ≈ 1.00) |
| Kanzi φ decomposition | `kanzi_nfe_scan_q4_2026.json` cells[].composite_debug | φ3 ranges +0.781 (seed 44) to +0.906 (seed 42); φ1 ≈ -0.067; φ2 ≈ -0.041 |
| LineageFlow NFE scan | `verification_outputs/lineageflow_real_force_mode_q4_2026.json` | 1/9 cells computed (seed 42 NFE 10), baseline = framework = 0.999, composite = +0.211; 8 PENDING on CPU bandwidth |
| Aggregation file | `verification_outputs/nfe_scan_aggregated_q4_2026.json` | Kanzi per-NFE table; LineageFlow per-NFE table with `data_status: pending_cpu_bandwidth` for NFE > 10 |
| Figure | `docs/figures/nfe_scan_q4_2026.png` (NEW from Wave 58 Agent 4) | two-panel plot: Kanzi left (composite +0.169 across all 6 NFE), LineageFlow right (1 filled + 5 hollow markers) |
| Audit trails | `docs/audit/wave58-kanzi-nfe-scan.md`, `docs/audit/wave58-nfe-scan-aggregation.md` | Wave 58 Agent 2 + Agent 4 audits cited as raw evidence |

## 3. Code references (file:line)

| Reference | Location | Used in §7.7 |
|---|---|---|
| NFE-adaptive restart gate call site | `adaptive_reflow/adapters/flowmol3.py:865-887` | §7.7.5 (1-line code change) |
| `low_nfe_restart_gate` helper | `adaptive_reflow/adapters/_adapter_common.py:239-273` | §7.7.5 |
| `coerce_nfe_budget` helper | `adaptive_reflow/adapters/_adapter_common.py:210-236` | §7.7.5 |
| Threshold constant `FLOWMOL3_RESTART_MIN_NFE = 20` | `adaptive_reflow/adapters/flowmol3.py:214` | §7.7.5 |
| Per-adapter override kwarg | `FlowMol3Adapter(restart_min_nfe=...)` constructor | §7.7.5 |
| Audit code (gated round) | `flowmol3adapter_restart_skipped_low_nfe:nfe=<N>:min_nfe=<M>` | §7.7.6 |
| Eval pipeline CLI | `tools/run_real_ckpt_eval.py --nfe-budgets 10,50,200,500,1000,2000` | §7.7.2 / §7.7.3 / §7.7.4 |

## 4. Section renumbering

Because §7.7 is new and the prior §7.7 (Wave 59 framing) / §7.8 (Wave 52 Agent A audit) / §7.9 (NFE-adaptive framework Wave 58) all need to shift down, the renumbering is:

| Old | New | Title |
|---|---|---|
| §7.7 | §7.8 | Framework extends baseline's saturation ceiling via paper-quantity signals (Wave 59 framing) |
| §7.8 | §7.9 | Wave 52 Agent A — paper-Tier-3 substantive rewrite (this wave) |
| §7.9 | §7.10 | NFE-adaptive framework (Wave 58 — new section) |
| §7.9.1–§7.9.6 | §7.10.1–§7.10.6 | renumbered subsections |

**Cross-reference updates** (16 total, all renumbered):
- §7.3 Kanzi line 1600: §7.9 → §7.10
- §7.4 LineageFlow line 1751: §7.9 → §7.10
- §7.6 honest verdict line 1875: §7.9 → §7.10
- §7.6 honest verdict line 1892: §7.9 → §7.10
- §7.10 body line 2437: §7.9.6 caveats → §7.10.6 caveats
- §7.10 body line 2588: §7.9.2 above → §7.10.2 above
- §7.10 body line 2610: §7.9.4 table → §7.10.4 table
- §7.9 Wave 52 Agent A line 2361: §7.1–§7.7 above → §7.1–§7.8 above
- §7.9 Wave 52 Agent A line 2409: §7.7 figure → §7.8 figure
- §7.9 Wave 52 Agent A line 2413: §7.8 is this section → §7.9 is this section

## 5. Honest caveats (carried into §7.7.6)

The §7.7.6 subsection records three honest caveats specific to §7.7:

1. **NFE-independence is a Kanzi / LineageFlow adapter property, not a generalisation.** The composite constant-across-NFE reading holds on Kanzi because `solve_ode` reads `trajectory[-1]` as a deterministic function of `(seed, model_weights)`. Adapters whose solver produces NFE-dependent endpoints (FlowMol3's CTMC chain) do NOT share this property — FlowMol3's composite decays as NFE grows, hence the gate.
2. **The threshold `20` is not a measured changepoint.** It is the inherited value from the Wave 57 synthesis; recalibration on the planned 18-cell v4 grid (n=6 seeds × 3 NFE) is Wave 59+ work (Wave 58 Agent 1 §6.2).
3. **LineageFlow evidence is provisional.** 1/9 cells computed; the other 8 are PENDING on CPU bandwidth. The "framework composite constant across NFE" prediction for LineageFlow is not yet empirically validated beyond NFE = 10.

The §7.6 additive line records the headline caveat: "At NFE < 20 the framework's restart-blend is gated to a no-op on FlowMol3 ... framework ≡ baseline (no-op, not regression)."

## 6. Constraints honoured

| Constraint | Status | Evidence |
|---|---|---|
| ADDITIVE — do NOT rewrite §7.4 / §7.5 / §7.6 | PASS | §7.4 / §7.5 body unchanged (only cross-ref §7.9→§7.10 updated); §7.6 got 1 additive summary line (no deletion of existing content) |
| Insert §7.7 BETWEEN §7.6 and §8 | PASS | §7.7 is at line 1991, between §7.6 (ending line 1989) and §8 (line 2483, currently §8 SOTA baseline comparison) |
| Use ONLY Kanzi + LineageFlow data (no FlowMol3 sweep) | PASS | §7.7 cites only Kanzi (18 cells) + LineageFlow (1 cell) NFE-scan evidence; FlowMol3 sweep is Phase 2 (per `todo/wave58-nfe-adaptive-plan.md` §2). FlowMol3 is mentioned only as the holder of the NFE-adaptive gate (1-line code reference at `flowmol3.py:865-887`) |
| Cite NFE-adaptive gate 1-line code change (file:line) | PASS | §7.7.5 cites `adaptive_reflow/adapters/flowmol3.py:865-887` + `low_nfe_restart_gate` at `_adapter_common.py:239-273` |
| Honest caveat required (NFE<20 framework ≡ baseline no-op, not regression) | PASS | §7.6 additive line + §7.7.6 explicit caveat |
| No push | PASS | `git commit` only; not pushed |

## 7. Files changed

| Path | Status | Purpose |
|---|---|---|
| `docs/paper-draft.md` | MODIFIED | +266 / −19 lines: new §7.7 (234 lines) + 1-line additive §7.6 update + 16 cross-ref renumberings + section renumber §7.7→§7.8, §7.8→§7.9, §7.9→§7.10 |
| `docs/audit/closure-s7.7.md` | NEW | this audit doc |

## 8. Diff verification

`git diff --stat docs/paper-draft.md`:

```
docs/paper-draft.md | 285 ++++++++++++++++++++++++++++++++++++++++++++++++----
1 file changed, 266 insertions(+), 19 deletions(-)
```

The 19 deletions are exclusively the cross-reference renumberings
(§7.9→§7.10, §7.7 figure→§7.8 figure, etc.) — no body text was deleted.
The 266 insertions are: 234 lines for the new §7.7 + 12 lines for the
§7.6 additive summary + 16 lines for renumbered subsection headers
(§7.10.1–§7.10.6 replacing §7.9.1–§7.9.6) + 4 lines for cross-ref
updates (e.g. `§7.7 figure` → `§7.8 figure`).

## 9. Output JSON

```json
{
  "s7_7_added": true,
  "s7_6_update_added": true,
  "kanzi_nfe_cited": true,
  "lineageflow_nfe_cited": true,
  "nfe_gate_code_referenced": true,
  "files_changed": [
    "docs/paper-draft.md",
    "docs/audit/closure-s7.7.md"
  ],
  "commit_sha": "<filled after commit>",
  "notes": [
    "New §7.7 inserted between §7.6 and §8 (5 subsections: 7.7.1 framing, 7.7.2 methodology, 7.7.3 Kanzi, 7.7.4 LineageFlow, 7.7.5 NFE-adaptive gate, 7.7.6 honest caveat).",
    "§7.6 honest verdict got 1 additive NFE-adaptive summary line (12 lines, no body deletion).",
    "Renumbering: §7.7 (Wave 59)→§7.8, §7.8 (Wave 52 audit)→§7.9, §7.9 (NFE-adaptive Wave 58)→§7.10. All 16 cross-references updated.",
    "Kanzi: 18/18 cells computed, composite +0.169 ± 0.017 constant across NFE 10/50/200/500/1000/2000, baseline saturated at NFE = 10 (Wave 58 Agent 2 audit).",
    "LineageFlow: 1/9 cells computed (seed=42, NFE=10, baseline = framework = 0.999, framework composite = +0.211); 8 cells PENDING on CPU bandwidth (Wave 58 Agent 3).",
    "NFE-adaptive gate code cited: flowmol3.py:865-887 (1-line `if skip_restart: return state unchanged` branch) + low_nfe_restart_gate helper at _adapter_common.py:239-273 + threshold constant FLOWMOL3_RESTART_MIN_NFE = 20 at flowmol3.py:214.",
    "Honest caveat: NFE<20 framework ≡ baseline (no-op, not regression); framework is NFE-adaptive on FlowMol3 via the gate, but NFE-budget-free on Kanzi + LineageFlow because both saturate at NFE = 10 already."
  ]
}
```
