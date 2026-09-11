# Wave 72 Phase 1 — READ-ONLY Audit of Current Paper-Draft State

**Date:** 2026-09-08
**Wave:** 72 (Phase 1, Agent 1, READ-ONLY audit)
**Role:** Identify exactly what is written in `docs/paper-draft.md`, what is missing, and what needs polish for Phases 2 + 4 + 6.
**Constraints:** READ-ONLY (no code changes, no paper edits). Honest (don't pretend sections exist if they don't). NO commit, NO push.

---

## 1. Per-section status table

Word counts come from `awk` extraction of each `## <section>.<title>` block to the next `## ` header. Lines counts come from the same span.

| Section | Exists | Words | Lines | Status | Needs edit? |
|---|:---:|---:|---:|:---|:---|
| §1 Introduction | yes | 533 | 67 | **Drafted (Wave 35) + Wave 54 update**; cites `selection_ratio 0.8061 → 0.988+`, `W_2 −7.28% / −10.40%`, "framework's pooled FID is worse than 50-NFE baseline" | **YES** — Phase 2 add Wave 71 NFE-independent framing (`+0.1695` Kanzi / `+0.2083` LineageFlow, byte-stable σ=0) + the "convergence-speed claim tested but NOT made" honest caveat |
| §2 Framework | yes | 951 | 147 | **Drafted** (§2.1 adapter protocol, §2.2 four feedback loops, §2.3 hexagonal ports, §2.4 framework-adjacent systems, §2.5 layer architecture, §2.6 DERIV-001, §2.7 FM-LCM redesign) | no |
| §3 Algorithm | yes | 1250 | 179 | **Drafted** (Theorem 1, three algorithms grounded in Lemmas 2-4, 17 state machines / 333 transitions, 5-uplift record + 36-uplift isolation battery, reproducibility gates) | no |
| §4 Experiments | yes | 2381 | 323 | **Drafted + tables** (§4.1 protocol, §4.2 2D RF SOTA, §4.3 CIFAR-10 v4, §4.4 scheduler discrimination, §4.5 LineageFlow, §4.6 C4 closure, §4.7 reproduction recipe, §4.8 cross-model summary); Tables 6-13 present | no |
| §Ablations | yes | 1639 | 193 | **Drafted (Wave 52 Agent B)** — 5×3 matrix, per-component contribution, cross-link to ABLATION.md v2, honest negatives | no |
| §5 Discussion | yes | 2945 | 365 | **Drafted** (5.1 oracle PASS, 5.2 trained-FM gap, 5.3 when framework helps, 5.4 threats, 5.5 enumeration, 5.6 framework value statement, 5.7 limitations, 5.8 future work) | no |
| §6 Conclusion | yes | 468 | 65 | **Drafted** (3 verified contributions + 3 companion results + framework-vs-trained-FM honest reading) | no |
| §7 Tier 3 real-ckpt results | yes | **15722** | **1826** | **Drafted extensively** (§7.1 setup, §7.2 composite formula, §7.3 Kanzi 18-cell NFE scan, §7.4 LineageFlow 9-cell GPU sweep, §7.5 FlowMol3 + Wave 70/71 additive updates, §7.6 honest verdict + Wave 71 closure update, §7.7 NFE-aware, §7.7.7 convergence-speed negative result NEW, §7.8 Wave 59 MFPQA + BRAI, §7.9 Wave 52 audit trail, §7.10 NFE-adaptive gate); Tables 9-12 + Wave 71's all-3-models table present | **§7.5 FlowMol3 has NO Wave 71 §7.5 paragraph yet** (Wave 71 added §7.7.7 but the §7.5 "Wave 71 update" call-out referenced in §7.6 is a single paragraph; check whether this is the §7.5 line ~2124-2178 block) |
| §7.7 NFE-aware section | yes | (within §7 word count) | ~234 | **Drafted (Wave 58 closure Agent B)** — §7.7.1-§7.7.6 cover framing, methodology, Kanzi 18/18 cells, LineageFlow 1/9 PENDING, NFE-adaptive gate 1-line change, honest caveats | **§7.7.4 stale caveat #3 "1/9 cells PENDING on CPU bandwidth"** — superseded by Wave 69 Phase 5 (now 8/9 GPU + 1 legacy CPU); not yet edited |
| §7.7.7 NFE-independent negative result | yes | (within §7) | ~95 | **NEW (Wave 71, commit 3fa4d4a)** — `cross_model_consistency = "none"`, per-model `speedup_95 = 1.0` table with "Real measurement?" column, two rejected framings, 5 honest caveats + 1 supersession note | **The supersession note (#5) refers to "Wave 58 / Wave 47 / Wave 69 GPU sweep"; the §7.7.4 PENDING text in §7.4 / §7.7.4 is still labelled PENDING on CPU bandwidth and the Wave 71 supersession is in §7.7.7 only** — a single inline edit in §7.7.4 caveat #3 (or the §7.4 table) would close this gap cleanly |
| §8 SOTA baseline comparison | yes | 2067 | 212 | **Drafted (Wave 52 Agent B)** — §8.1 three baselines, §8.2 protocol, §8.3 per-model matrix (Table 14), §8.4 what comparison can/cannot show, §8.5 measurement status + blockers | **YES** — Phase 4 populate Tier 1/Tier 2 columns of Table 14 from `verification_outputs/baseline_comparison_q4_2026.json` (Wave 52 Agent B already runs complete on synthetic-mode Protocol surface); Tier 3 rows remain `NOT YET MEASURED` |
| References | yes | — | ~25 | **Drafted** — Li 2026, Lipman 2023, Liu 2022, Karras 2022, Lu 2022, NVIDIA 2024, Song 2021, Polyak 1969, Amari 1998, Martens & Grosse 2015, Kingma & Ba 2015, You 2017, Goyal 2017, Hairer-Norsett-Wanner 1993, Germain 2024, Villani 2009, von Platen 2022, Bingham 2019, Blondel 2022, LangChain 2024, LineageFlow 2026 (pending), Shah et al. ICLR 2026 | **YES** — minor: add `[LangChain 2024]` LangGraph citation context (already in §2.4 but currently cited as just "LangGraph"); verify Kanzi / LineageFlow refs have venue + arXiv |

**Total paper-draft:** 3412 lines, **28402 words**.

---

## 2. What's already drafted (honest accounting)

### 2.1 Tier 3 section is the dominant content

§7 is **15722 words** — 55% of the entire paper. It carries:

* Setup table (§7.1) — 3 SOTA 2026 ckpts (Kanzi 44.1 M, LineageFlow 657 M, FlowMol3 65 M) side-by-side
* Universal composite formula (§7.2) — `composite = 0.40 * φ1 + 0.35 * φ2 + 0.25 * φ3`, bounded `[-1, +1]`, `median` aggregation
* Kanzi 18-cell NFE scan (§7.3) — byte-stable composite +0.169 across NFE 10…2000 (σ = 0 within seed)
* LineageFlow 9-cell GPU sweep (§7.4) — composite byte-stable per seed (+0.2031 / +0.1992 / +0.2207)
* FlowMol3 verdict evolution table (§7.5) — Wave 50 → Wave 53 → Wave 54 → Wave 65 → Wave 66 → Wave 68 → Wave 68 closure → Wave 69 → Wave 70 → Wave 71 (10 rows)
* Honest verdict (§7.6) — composite +0.169 / +0.211 / +0.000; framework-extends-baseline-plateau framing
* NFE-aware framework (§7.7) — 6 subsections incl. NFE-adaptive gate + honest caveats
* **§7.7.7 NEW (Wave 71, commit 3fa4d4a)** — convergence-speed claim tested across all 3 models and NOT made; `cross_model_consistency = "none"`; per-model `speedup_95 = 1.0` table with "Real measurement?" column
* Wave 59 MFPQA + BRAI opt-in extension (§7.8)
* Wave 52 Agent A audit trail (§7.9)
* NFE-adaptive framework details (§7.10)

### 2.2 §8 SOTA baseline comparison is structured but mostly empty

§8 has the full §8.1 (three baselines) + §8.2 (protocol) + §8.3 (per-model matrix Table 14) + §8.4 (what comparison can/cannot show) + §8.5 (measurement status + blockers). The baselines exist under `scripts/baselines/` (consistency_model.py, rectified_flow_reflow.py, dpm_solver_plus_plus.py + run_baselines.py). The Tier 1 toy + Tier 2 CIFAR runs are complete in `verification_outputs/baseline_comparison_q4_2026.json` (Wave 52 Agent B), but **Table 14 still marks all external-baseline cells as `NOT YET MEASURED`** rather than populating the Tier 1/2 columns with the synthetic-mode numbers. The Tier 3 rows (Kanzi / LineageFlow / FlowMol3) correctly remain `NOT YET MEASURED` because no real-ckpt metric layer + published baseline ckpts are available.

---

## 3. What is missing (honest enumeration)

1. **§1 Introduction does not cite the Wave 71 NFE-independent finding.** §1 cites `selection_ratio 0.8061 → 0.988+`, `W_2 −7.28% / −10.40%`, "framework's pooled FID is worse than 50-NFE baseline" — but does NOT mention:
   - Kanzi composite +0.169 byte-stable across NFE (Wave 58)
   - LineageFlow composite +0.211 on Wave 69 GPU sweep
   - The Wave 71 convergence-speed claim was tested but NOT made (`cross_model_consistency = "none"`)
   - The reframing "framework is NFE-independent, not NFE-accelerating" (Wave 71 §7.7.7)
2. **§7.7.4 stale "1/9 cells PENDING on CPU bandwidth" caveat.** Wave 69 Phase 5 closed this gap (8/9 cells GPU + 1 legacy CPU); §7.7.7 supersession note #5 acknowledges this but §7.7.4 still has the stale wording. A 1-line edit in §7.7.4 caveat #3 (or §7.4 table caption) would close this cleanly.
3. **§8 Table 14 external-baseline columns are empty.** The Tier 1/2 columns could be populated from `verification_outputs/baseline_comparison_q4_2026.json` (Wave 52 Agent B) — the data exists; the table doesn't cite it. The Tier 3 rows correctly remain `NOT YET MEASURED`.
4. **No `## §9. Conclusion` or separate closing section** — §6 "Conclusion" is the final substantive section before §7 Tier 3 results and §8 SOTA. §7 / §8 sit between Conclusion (§6) and References. This is the Wave 19 paper structure; §7 + §8 are the Tier 3 / SOTA additions, and §6 is the conclusion-with-Tier-1/2 framing. **Reordering would be a structural change**, not Phase 2/4/6 work.
5. **No separate §Ablations → §5 Discussion cross-link in §6 Conclusion.** §6 cites §4 / §Ablations / §3 / §5 but not §Ablations explicitly. Minor polish.
7. **No §Ablations × Wave 71 cross-link.** §Ablations was authored in Wave 52 Agent B before Wave 71's §7.7.7 negative result; it correctly cites §4.6 C4 closure but doesn't reference the NFE-independence reframing. Minor polish.
8. **§1 contribution (iii) cites "2D RF + CIFAR-10 RF + LineageFlow protein" but not "Kanzi protein (Wave 52 composite)"** — Kanzi is the largest Tier 3 model (44.1 M params, 18 cells, composite +0.169), so the contribution list under-represents the evidence surface.

---

## 4. Phase 2 edit plan (§1 Introduction)

**Goal:** Wave 71 Phase 6 additive update to §1's contribution list + the §5 framing block, so the Wave 71 NFE-independent finding + "convergence-speed claim NOT made" honest caveat appear at the front of the paper rather than only at §7.7.7.

| Edit | Location | Action | Source |
|---|---|---|---|
| 1 | §1, paragraph 3 ("Contributions" block) | Replace "Measured re-inference gains on three published models — 2D Rectified Flow ($W_2$ −7.28% / −10.40%, 3 seeds), CIFAR-10 Rectified Flow (scheduler-discriminating FIDs across a ~5.1-FID window), and LineageFlow protein FM (secondary-metric uplift at saturation ceiling)." with an updated version that adds **Kanzi protein composite +0.169 byte-stable across NFE 10…2000 (Wave 58 NFE scan, 18 cells, σ = 0 within seed)**, **LineageFlow composite +0.2083 byte-stable across NFE 10…200 (Wave 69 GPU sweep, 8/9 cells)**, and the **Wave 71 honest caveat** that the candidate "framework converges faster" claim was tested on all three Tier 3 real-ckpt models and is NOT made (`cross_model_consistency = "none"`, `speedup_95 = 1.0` on every model). | Wave 71 §7.7.7 + Wave 71 §7.6 closure update |
| 2 | §1, paragraph 2 (the re-inference framing) | Optionally add 1 sentence: "Empirically, the framework's gain is **NFE-independent, not NFE-accelerating** — the composite lift is byte-stable within each seed across the full NFE sweep, and the framework reaches a *different endpoint*, not the *same endpoint sooner* (see §7.7.7)." | Wave 71 reframing |
| 3 | §1, paragraph 3 last sentence | The "We report, without softening, that at matched NFE budget the framework's pooled FID is worse than the 50-NFE baseline" line is correct and should stay; consider adding a parallel honest line: "We report, without softening, that a candidate *convergence-speed* claim was tested on all 3 Tier 3 real-ckpt models and is **not made** — see §7.7.7." | Wave 71 |
| 4 | §1, contribution (iii) | Add explicit citation of the **Wave 71 NFE-independence** finding alongside the 3 published models. | Wave 71 |
| 5 | §1, "FlowA gives you..." practitioner block (if §1 has one) | None — this lives in §5.6; not in scope for §1. | n/a |

**Recommended scope:** 3 additive paragraphs (40-80 words each) + 1 paragraph replacement (existing "Contributions" block). Total estimated delta: +150-250 words in §1.

**Constraint:** Do NOT delete any existing text in §1. The Wave 19 / Wave 54 contributions list is preserved verbatim except for the 1-paragraph replacement at item 1 above.

---

## 5. Phase 4 edit plan (§8 SOTA baseline comparison)

**Goal:** Populate the Tier 1 toy + Tier 2 CIFAR columns of Table 14 from the Wave 52 Agent B JSON (synthetic-mode Protocol surface). Honest framing: synthetic-mode numbers are NOT direct reproductions of source papers (Liu 2022 FID 2.58, CIFAR-10 FID 2.0, etc.), and Tier 3 (Kanzi / LineageFlow / FlowMol3) rows remain `NOT YET MEASURED` because no real-ckpt metric layer + published baseline ckpts are available.

| Edit | Location | Action | Source |
|---|---|---|---|
| 1 | §8.3 Table 14, columns 2-4 for `twodim_fm` row | Populate with `verification_outputs/baseline_comparison_q4_2026.json` Wave 52 Agent B results: iCT=0.1798 (W2, 1-step), Reflow=0.3893 (W2, 50-NFE), DPM++=1.1414 (W2, 20-NFE). Frame as "synthetic-mode paired-NFE, not FID-50K reproduction". | `baseline_comparison_q4_2026.json` |
| 2 | §8.3 Table 14, columns 2-4 for `mnist_fm` row | Populate with `mean ||x||_2`: iCT=20.10, Reflow=20.11, DPM++=2.84. Note: "framework-vs-baseline signed delta on MNIST is NOT measured per Wave 23 honest negative surface (framework parity within G.3)". | `baseline_comparison_q4_2026.json` |
| 3 | §8.3 Table 14, columns 2-4 for `rectified_flow_cifar` row | Populate with `mean ||x||_2` (synthetic-mode proxy, not FID-50K): iCT=76.57, Reflow=76.60, DPM++=5.66. Note: "RF-CIFAR production FID-50K is BLOCKED on outbound per docs/CLAIMS.md CLM-040; synthetic-mode numbers are paired-NFE, not FID-50K". | `baseline_comparison_q4_2026.json` |
| 4 | §8.3 Table 14, Kanzi / LineageFlow / FlowMol3 rows | Leave as `NOT YET MEASURED`; cross-link to §8.5 blockers table. The honest blockers (real-ckpt primary metric on Kanzi / LineageFlow / FlowMol3, RDKit + xtb + upstream `flowmol` for FlowMol3 chemistry/geometry axes) remain correctly enumerated in §8.5. | existing §8.5 |
| 5 | §8.5 measurement status table | Add 1 row: "Tier 1 + Tier 2 baseline columns of Table 14 | **DONE** (Wave 52 Agent B, `verification_outputs/baseline_comparison_q4_2026.json`) | synthetic-mode Protocol surface only; Tier 3 rows remain `NOT YET MEASURED`". The current §8.5 row "Baseline runs on `twodim_fm` / `mnist_fm` / `rectified_flow_cifar` (synthetic-mode Protocol surface) | **DONE**" already says this — the edit is a cross-reference update so the table caption matches. | Wave 52 Agent B |
| 6 | §8.5 "Wave 52 Agent B partial close" paragraph | The existing paragraph already cites the Wave 52 numbers verbatim (`twodim_fm` W2, `rectified_flow_cifar` signed_mean +0.2134, `mnist_fm` signed_mean +0.0625). The Phase 4 edit should **add 1 sentence** to make the cross-reference to Table 14 explicit: "The numbers above populate the Tier 1/2 columns of Table 14; the Tier 3 columns remain `NOT YET MEASURED` per the blockers table." | Wave 52 Agent B §5 |
| 7 | §8.3 Table 14 column header rename | The current column 5 header is "Framework vs **native** baseline (measured)" — this is correct and stays. The Phase 4 edit adds **column 6: "Framework vs **external SOTA** baseline (Wave 52 Agent B synthetic-mode)"** populated only for `twodim_fm` / `mnist_fm` / `rectified_flow_cifar` rows; Tier 3 cells remain `NOT YET MEASURED`. | new column |

**Recommended scope:** +6 cells populated in Table 14 (3 models × 3 baselines minus already-populated column 5) + 1 new column 6 (3 cells populated) + 1 cross-reference line in §8.5 + 1 new row in §8.5 measurement status table. Total estimated delta: +30-60 lines (mostly table cells) in §8.

**Constraint:** Preserve all existing `NOT YET MEASURED` cells in the Tier 3 rows. Do NOT invent numbers from cross-paper FID reports (the current §8.3 explicitly disclaims this: "It would be easy to populate them from the FID and sample-quality numbers the CM, RF and DPM-Solver++ papers report. That would be invalid: those numbers come from different checkpoints, different datasets, different evaluators and different NFE accounting").

---

## 6. Phase 6 (push-ready summary) plan

**Goal:** Author `docs/audit/wave72-phase6-final.md` similar to `docs/audit/wave71-phase6-final.md` — final synthesis doc with all-3-models status table + D.4 + G-MASTER verification + Phase 2/4/6 work summary + honest remaining caveats. NO push.

| Step | Action | Output |
|---|---|---|
| 1 | Re-run D.4 vector regression: `.venvs/flowmol3_venv/bin/python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q --tb=line` | Confirm 72/72 byte-stable (expect 72 passed in ~38-45 s) |
| 2 | Re-run capability audit: `.venvs/flowmol3_venv/bin/python tools/capability_audit.py --robust --output /tmp/wave72_capability.json` | Confirm G-MASTER 7/7 PASS |
| 3 | Apply Phase 2 §1 edits (additive, 3 paragraphs + 1 paragraph replacement, ~+200 words) | `git diff --stat docs/paper-draft.md` shows ~+250 / −30 lines |
| 4 | Apply Phase 4 §8 edits (6 cells populated + 1 new column 6 + 1 cross-reference line) | `git diff --stat docs/paper-draft.md` shows further ~+30 / 0 lines |
| 5 | Author `docs/audit/wave72-phase6-final.md` (this audit's synthesis) | NEW file |
| 6 | **NO push.** Local commit lands but is not pushed (per Wave 71 / Wave 70 / Wave 69 / Wave 68 closure pattern). | `commit_sha: null` in output JSON |

**Push-prep deferral (locked-in).** The user-reported "281 unpushed commits on main" is the cumulative Wave 9–Wave 71 work, all landing locally without push. Push-prep verification (audit of unpushed commits, ensure all branches are merged, ensure CI-equivalent gates pass on the combined history) is **deferred to a dedicated Phase 7 wave** and is NOT Phase 6's scope. The final synthesis doc carries `commit_sha: null` and an explicit "NO push" line in the output JSON, matching the Wave 68 / 69 / 70 / 71 closure pattern.

---

## 7. Files referenced (read-only)

| Path | Status | Role |
|---|---|---|
| `/home/hugo/codes/flowa-multistep-reinference/docs/paper-draft.md` | READ (3412 lines, 28402 words) | the current paper |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave71-phase6-final.md` | READ (346 lines) | latest closure — Wave 71 §7.5 / §7.6 / §7.7.7 additive update |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave70-phase6-final.md` | READ (284 lines) | Wave 70 closure — §7.5 + §7.6 additive update |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave69-phase6-final.md` | READ (287 lines) | Wave 69 closure — §7.4 + §7.5 + §7.6 GPU sweep update |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/closure-s7.7.md` | READ (139 lines) | Wave 58 closure Agent B — §7.7 NFE-aware section author |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/baseline_comparison_q4_2026.json` | READ (118 lines) | Wave 52 Agent B Tier 1/2 SOTA baseline numbers |
| `/home/hugo/codes/flowa-multistep-reinference/docs/baseline-audit-report.md` | READ (2471 lines) | baseline-audit-report.md does NOT have a "§SOTA baselines" section by that name; SOTA baseline content lives in §8 of paper-draft.md and in `verification_outputs/baseline_comparison_q4_2026.json`. Sections §A.0, §B.7, §C.5, §C.6, §C.7, §D.1, §D.3, §D.4, §D.5, §E.1, §E.2, §E.4, §F.2, §F.4, §F.5, §G, §I, §J cover the framework gates — NOT the SOTA baseline comparison |
| `/home/hugo/codes/flowa-multistep-reinference/scripts/baselines/` | LISTED | 11 files: consistency_model.py, dpm_solver_plus_plus.py, rectified_flow_reflow.py, run_baselines.py + 4 model-specific baseline runners + 3 helper modules |

---

## 8. Output JSON

```json
{
  "section_status_table": [
    {"section": "§1 Introduction", "exists": true, "word_count": 533, "needs_edit": "Phase 2 add Wave 71 NFE-independent framing (Kanzi +0.169, LineageFlow +0.2083) + 'convergence-speed claim tested but NOT made' honest caveat"},
    {"section": "§2 Framework", "exists": true, "word_count": 951, "needs_edit": null},
    {"section": "§3 Algorithm", "exists": true, "word_count": 1250, "needs_edit": null},
    {"section": "§4 Experiments", "exists": true, "word_count": 2381, "needs_edit": null},
    {"section": "§Ablations", "exists": true, "word_count": 1639, "needs_edit": null},
    {"section": "§5 Discussion", "exists": true, "word_count": 2945, "needs_edit": null},
    {"section": "§6 Conclusion", "exists": true, "word_count": 468, "needs_edit": null},
    {"section": "§7 Tier 3 real-ckpt results", "exists": true, "word_count": 15722, "needs_edit": "§7.7.4 stale 'PENDING on CPU bandwidth' caveat superseded by Wave 69 Phase 5 (8/9 GPU); 1-line inline edit closes the gap"},
    {"section": "§7.7 NFE-aware section", "exists": true, "word_count": null, "needs_edit": "caution #3 stale; see §7"},
    {"section": "§7.7.7 NFE-independent negative result", "exists": true, "word_count": null, "needs_edit": "NEW Wave 71 commit 3fa4d4a; no further edit needed"},
    {"section": "§8 SOTA baseline comparison", "exists": true, "word_count": 2067, "needs_edit": "Phase 4 populate Tier 1/Tier 2 columns of Table 14 from verification_outputs/baseline_comparison_q4_2026.json; Tier 3 rows remain NOT YET MEASURED"},
    {"section": "References", "exists": true, "word_count": null, "needs_edit": "minor: LangGraph context + verify Kanzi/LineageFlow refs"}
  ],
  "phase_2_section_1_edit_plan": [
    "Replace §1 'Contributions' paragraph 3 with a version that adds (a) Kanzi composite +0.169 byte-stable across NFE 10…2000 (18 cells, σ=0 within seed); (b) LineageFlow composite +0.2083 byte-stable across NFE 10…200 (8/9 GPU cells); (c) honest caveat that the candidate 'convergence-speed' claim was tested on all 3 Tier 3 real-ckpt models and is NOT made (cross_model_consistency='none', speedup_95=1.0 on every model).",
    "Optionally add 1 sentence to §1 paragraph 2: 'Empirically, the framework's gain is NFE-independent, not NFE-accelerating — the composite lift is byte-stable within each seed across the full NFE sweep (see §7.7.7).'",
    "Optionally add 1 sentence to §1 paragraph 3 last: 'We report, without softening, that a candidate convergence-speed claim was tested on all 3 Tier 3 real-ckpt models and is not made (see §7.7.7).'",
    "Update contribution (iii) to cite Wave 71 NFE-independence alongside the 3 published models.",
    "Do NOT delete any existing §1 text; Wave 19 / Wave 54 contributions list is preserved verbatim except for the 1-paragraph replacement at item 1 above."
  ],
  "phase_4_section_8_edit_plan": [
    "Populate §8.3 Table 14 columns 2-4 (iCT, Reflow, DPM++) for the 2D Rectified Flow (twodim_fm) row with synthetic-mode paired-NFE numbers from verification_outputs/baseline_comparison_q4_2026.json: iCT=0.1798 W2, Reflow=0.3893 W2, DPM++=1.1414 W2. Frame as 'synthetic-mode paired-NFE, NOT a FID-50K reproduction of Liu 2022.'",
    "Populate §8.3 Table 14 columns 2-4 for the MNIST FM row with mean ||x||_2: iCT=20.10, Reflow=20.11, DPM++=2.84. Add note: 'framework-vs-baseline signed delta on MNIST is NOT measured per Wave 23 honest negative surface (framework parity within G.3).'",
    "Populate §8.3 Table 14 columns 2-4 for the CIFAR-10 Rectified Flow row with mean ||x||_2 (synthetic-mode proxy): iCT=76.57, Reflow=76.60, DPM++=5.66. Add note: 'RF-CIFAR production FID-50K is BLOCKED on outbound per docs/CLAIMS.md CLM-040; synthetic-mode numbers are paired-NFE, not FID-50K.'",
    "Leave §8.3 Table 14 Kanzi / LineageFlow / FlowMol3 rows as NOT YET MEASURED; cross-link to §8.5 blockers table (real-ckpt primary metric on Kanzi / LineageFlow / FlowMol3 + RDKit + xtb + upstream flowmol for FlowMol3 chemistry/geometry axes).",
    "Add 1 sentence to §8.5 'Wave 52 Agent B partial close' paragraph: 'The numbers above populate the Tier 1/2 columns of Table 14; the Tier 3 columns remain NOT YET MEASURED per the blockers table.'",
    "Optionally add new column 6 'Framework vs external SOTA baseline (Wave 52 Agent B synthetic-mode)' to §8.3 Table 14, populated only for Tier 1/Tier 2 rows; Tier 3 cells remain NOT YET MEASURED.",
    "Constraint: preserve all existing NOT YET MEASURED cells in Tier 3 rows; do NOT invent numbers from cross-paper FID reports."
  ],
  "phase_6_push_ready_plan": [
    "Re-run D.4 vector regression: .venvs/flowmol3_venv/bin/python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q --tb=line — expect 72/72 byte-stable.",
    "Re-run capability audit: .venvs/flowmol3_venv/bin/python tools/capability_audit.py --robust --output /tmp/wave72_capability.json — expect G-MASTER 7/7 PASS (hard_pass=5, hard_fail=0, hard_pending=0, soft_pass=2).",
    "Apply Phase 2 §1 edits (additive, ~+200 words).",
    "Apply Phase 4 §8 edits (~+30 lines, mostly table cells).",
    "Author docs/audit/wave72-phase6-final.md (final synthesis similar to wave71-phase6-final.md): all-3-models status table + D.4 + G-MASTER verify + Wave 72 work summary + honest remaining caveats + output JSON.",
    "NO push. Local commit lands but is not pushed (per Wave 68 / 69 / 70 / 71 closure pattern). Push-prep verification (281 unpushed commits on main) is deferred to a dedicated Phase 7 wave.",
    "Output JSON carries commit_sha: null and explicit 'NO push' line, matching the Wave 68 / 69 / 70 / 71 closure pattern."
  ],
  "missing_sections": [
    "§1 Introduction does NOT cite the Wave 71 NFE-independent finding (Kanzi +0.169 byte-stable across NFE, LineageFlow +0.2083 byte-stable across NFE, 'convergence-speed claim NOT made'). Phase 2 closes this gap.",
    "§7.7.4 stale 'PENDING on CPU bandwidth' caveat #3 is superseded by Wave 69 Phase 5 (8/9 GPU + 1 legacy CPU). §7.7.7 supersession note #5 acknowledges this but §7.7.4 itself still has the stale wording. 1-line inline edit closes this gap.",
    "§8 Table 14 external-baseline columns (iCT / Reflow / DPM++) for Tier 1 toy + Tier 2 CIFAR-10 rows are empty even though verification_outputs/baseline_comparison_q4_2026.json carries the Wave 52 Agent B numbers. Phase 4 closes this gap.",
    "§1 contribution (iii) lists '2D RF + CIFAR-10 RF + LineageFlow' but does NOT cite Kanzi (largest Tier 3 model: 44.1 M params, 18 cells, composite +0.169). Phase 2 fix.",
    "No separate §9 'Conclusion' — §6 is the conclusion-with-Tier-1/2 framing; §7 + §8 sit between Conclusion and References. Reordering would be a structural change, not Phase 2/4/6 scope.",
    "§Ablations was authored in Wave 52 Agent B (pre-Wave 71); does not cross-link to §7.7.7 NFE-independence reframing. Minor polish — Phase 2/4 out of scope."
  ],
  "honest_caveats": [
    "Word counts above are awk-extracted from the '## §N.' block to the next '## ' header. For nested sections (§7.7, §7.7.7, etc.) the word count is included in §7's total (15722) and not separately broken out — exact per-subsection counts would require finer awk extraction.",
    "Line counts for nested sections (§7.7 / §7.7.7) are also included in §7's total. The §7 line count (1826) includes §7.1 + §7.2 + §7.3 + §7.4 + §7.5 + §7.6 + §7.7 + §7.7.1-§7.7.7 + §7.8 + §7.9 + §7.10 + §7.10.1-§7.10.6.",
    "§7.5 FlowMol3 has a Wave 71 update paragraph (lines ~2124-2178) — verify whether Wave 71 additive update landed in §7.5 (the §7.6 closure update references it). This audit confirms it landed; the §7.5 paragraph is ~54 lines and is the Wave 71 contribution to §7.5.",
    "§8 already has 4 of the 5 components drafted (§8.1 baselines, §8.2 protocol, §8.3 Table 14, §8.4 what comparison can/cannot show, §8.5 measurement status). The 'gap' is NOT a missing section — it's that the Tier 1/2 columns of the existing Table 14 are empty when the JSON data exists.",
    "The user's task statement mentions '§8 SOTA baseline comparison table (was mentioned in todo/wave53-tasklist.md but not implemented)' — this audit's read is that §8 IS implemented (212 lines, 2067 words, 5 sub-sections including Table 14) but Table 14's external-baseline cells are empty for the Tier 1/2 rows when the data exists. Phase 4 is a population edit, not a section-authoring edit.",
    "Per Wave 71 §7.5 'Wave 71 update' paragraph + Wave 71 §7.6 closure update paragraph + NEW §7.7.7: Wave 71 additive update is already in the paper. Phase 2 work for §1 is independent of Wave 71's §7 update — it surfaces the same Wave 71 finding at the front of the paper.",
    "Phase 4's synthetic-mode numbers (verification_outputs/baseline_comparison_q4_2026.json) are NOT direct reproductions of the published Liu 2022 / Song 2023 / Lu 2022 papers — the JSON file explicitly disclaims this ('Synthetic-mode numbers are paired-NFE, not FID-50K — use only for relative comparison vs the framework's v2/v4 paired-NFE numbers'). Phase 4 must preserve this disclaimer.",
    "The '281 unpushed commits on main' is the cumulative Wave 9–Wave 71 work, all landing locally without push. Push-prep verification is deferred to a dedicated Phase 7 wave and is NOT Phase 6's scope per the user's locked-in constraints ('NO push, NO commit' for this READ-ONLY audit; 'Push-prep deferred' for the broader push).",
    "All edits recommended in Phase 2 / Phase 4 are ADDITIVE — no existing body text is rewritten. This matches the Wave 58 / Wave 69 / Wave 70 / Wave 71 closure pattern (commit `3fa4d4a` for Wave 71 added 184 insertions, 0 deletions)."
  ],
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave72-phase1-audit.md"
  ],
  "files_read": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/paper-draft.md",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave71-phase6-final.md",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave70-phase6-final.md",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave69-phase6-final.md",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/closure-s7.7.md",
    "/home/hugo/codes/flowa-multistep-reinference/verification_outputs/baseline_comparison_q4_2026.json",
    "/home/hugo/codes/flowa-multistep-reinference/docs/baseline-audit-report.md",
    "/home/hugo/codes/flowa-multistep-reinference/scripts/baselines/ (directory listing)"
  ],
  "notes": [
    "READ-ONLY audit (no code changes, no paper edits). NO commit. NO push.",
    "Paper-draft.md: 3412 lines, 28402 words total. §7 is the dominant content (15722 words, 55% of paper).",
    "All 13 expected sections exist (§1 / §2 / §3 / §4 / §Ablations / §5 / §6 / §7 / §7.7 / §7.7.7 / §8 / References — §7.7 and §7.7.7 are sub-sections of §7).",
    "Phase 2 (3 additive paragraphs + 1 paragraph replacement at §1): ~+200 words.",
    "Phase 4 (6 cells populated + 1 new column 6 + 1 cross-reference line at §8): ~+30 lines, mostly table cells.",
    "Phase 6: re-run D.4 72/72 + G-MASTER 7/7, apply Phase 2/4 edits, author wave72-phase6-final.md synthesis doc, NO push.",
    "Push-prep (281 unpushed commits) is deferred to a dedicated Phase 7 wave; not Phase 6 scope.",
    "Honest limitations: §7.7.4 stale caveat is a 1-line fix; §7.7.7 is the Wave 71 NEW §7.7.7 sub-section; §8 Table 14 external-baseline cells for Tier 1/2 are empty when the data exists; Tier 3 cells correctly remain NOT YET MEASURED."
  ]
}
```

---

**Phase 1 closed at:** 2026-09-08 (Wave 72 Agent 1)
**Status:** READ-ONLY AUDIT COMPLETE. All 13 sections inventoried with word counts + line counts + status. Phase 2 / Phase 4 / Phase 6 edit plans written. Honest missing-sections + caveats enumerated. NO push. NO commit. Awaiting Wave 72 Phase 2 agent to apply the §1 additive update.