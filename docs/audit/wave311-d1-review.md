# Wave 311 — D+1 Self-Review of Wave 310 Paper Changes

**Wave:** 311 (D+1 self-review)
**Date:** 2026-09-23
**Author:** Wave 311 P1 D+1 verification pass
**Status:** ACTIVE — verification PASS WITH MINOR FIXES (audit-doc line-number drift only; paper content CORRECT)

---

## 1. Scope and inputs

This D+1 review audits the 5 Wave 310 paper-edit cells applied in commit `51422a8` (parent commit `7a135ee` R1 data provenance) to `docs/drafts/paper-flat-flattened.md`:

- R6 tier-aware counterfactual upgrade d_z = +0.2235 (5 additive paper edits)
- R5b `n_rounds` conditional characterization (2 additive paper edits)
- R5a two-readings reconciliation paragraph (1 paper edit)
- R5 legacy move to §10 supplementary (§10.9 new sub-section, 34 lines; §2.9 Table 2.9 row 5 status update)
- R3 reconciliation to Table 3.2 R3 row (K8 paragraph)

Inputs verified:

- `docs/drafts/paper-flat-flattened.md` (1566 lines, 43639 words, 1 H1 + 23 ## + 59 ### + 1 #### headings)
- `docs/audit/wave310-r6-tier-aware-upgrade.md` (121-line Wave 310 cross-doc-propagation audit doc)
- `docs/audit/wave310-restoration-execution.md` (231-line Wave 310 D2 restoration execution + 5-gate verification doc)
- `docs/audit/wave309-paper-a-restoration-plan.md` (381-line Wave 309 paper-A restoration plan)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` (verbatim class line check)

### Phase 1 Review Verification Table (one-glance summary)

| Wave 310 edit | Edits | Lines | Paper content CORRECT? | Audit-doc drift? | Pre-existing issue? |
|---|---:|---:|:---:|:---:|:---:|
| R6 tier-aware upgrade d_z = +0.2235 | 5 | +6 net | YES (per-tier breakdown consistent; p_raw=2.98e-12 + p_bonf=1.79e-11 consistent across all 5 edits) | 4 MINOR (off-by-2 line-number drift + 1 table-number typo + 1 rounding phrasing) | NO |
| R5b `n_rounds` conditional characterization | 2 | +12 net | YES (4-scheduler × 3-n_rounds = 12-cell grid; ΔFID + d_z all verified) | 1 MINOR (off-by-6 line-number drift) | NO |
| R5a two-readings reconciliation | 1 | +1 paragraph (~4 lines) | YES (both readings honestly disclosed; source attribution explicit) | 0 | NO |
| R5 legacy move to §10 supplementary | 2 (§2.9 Table 2.9 row 5 status + §10.9 new sub-section) | +35 net | YES (data-availability gap canonical-honest; multi-source-support verified) | 0 | NO |
| R3 K8 reconcile | 1 | +1 sentence (ACTUAL n=200 + PROJECTED n=1000 nuance) | YES (textually consistent with Table 3.2 R3 row caption) | 1 MINOR (off-by-6 line-number drift) | NO |
| **Total** | **11** | **+55 net** | **5/5 cells PASS** | **6 MINOR audit-doc issues** | **2 PRE-EXISTING (out of scope)** |

**Phase 1 verdict:** PASS_WITH_FIXES — paper content is CORRECT across all 5 Wave 310 paper-edit cells; 6 MINOR audit-doc / cross-doc / paper phrasing issues identified; 2 PRE-EXISTING issues out of Wave 310 scope.

## 2. Paper-structure summary (post-Wave 310)

The paper-flat-flattened.md top-level structure at post-Wave-310 state:

| § | Title | Line | Words | Notable Wave-310 contribution |
|---|---|---:|---:|---|
| Title | "FlowA: Paper-Quantity-Driven Re-Inference..." | 1 | ~25 | (preserved from Wave 297 P3) |
| Abstract | (Title re-anchor + abstract re-anchor) | 7 | ~180 | (preserved from Wave 297 P3) |
| §1 Introduction | Framework-reconstruction paradigm | 23 | ~2456 | (preserved from Wave 297 P3) |
| §2 Algorithm | Framework scheduler taxonomy | 71 | ~5596 | **§2.9 Table 2.9 row 8 line 214**: counterfactual lift parenthetical + **§2.9 Table 2.9 row 5 line 210**: R5 LEGACY demotion |
| §3 Experiments | Headline results | 259 | ~5596 | **§3.3 R6 paragraph line 341**: tier-aware upgrade + **§3.5 R5a reconciliation line 377** + **§3.6 R5b n_rounds conditional characterization line 417** + **K8 paragraph line 447**: R3 reconcile |
| §4 Limitations | K1-K8 boundary dimensions | 429 | ~1307 | K8 paragraph R3 reconcile (preserved) |
| §5 Flattening Checklist | Manuscript discipline | 451 | ~1007 | (preserved) |
| §6 Reviewer-Facing Static Reference Labels | R-level / Tier-3 / D.4 | 492 | ~170 | (preserved) |
| Appendix W297 P4 | Framework + Scheduler Family + Adapter Protocol | 516 | ~26015 | (preserved) |
| Appendix W297 P5 | §7 Empirical Results | 652 | ~22717 | **§7.1 Table 7.1 row 7 line 674** + **§7.4 framework-not-theory verdict line 699** |
| Appendix W297 P6 | §9 Limitations + §10 Future Work | 786 | ~18043 | **§10.9 R5 legacy supplementary lines 963–993** (34 lines, 6 sub-paragraphs) |
| Appendix W298 P7 | §MS.deep_innovations | 1001 | ~11298 | (preserved) |
| Appendix W300 P5 | Paper A §1–§10 Fold-In Draft | 1240 | ~7475 | (preserved) |

Total: **1566 lines, 43639 words**. 8 canonical H2 sections (Title + Abstract + §1–§6) + 5 appendix H2 sections = 13 ## sections at the top level.

## 3. Per-edit verification

### 3.1 R6 upgrade (5 edits)

| # | Edit | Audit doc cites | Paper actual | Status |
|---:|---|---|---|---|
| 1 | §2.1 Table 2.1 TierAwareCodimensionSheetScheduler row | "P4 counterfactual (easy-tier `n_cap *= 0.5` lifts overall pLDDT d_z +0.071 → +0.224 Bonf-sig)" | line 91 | **MINOR**: +0.224 is rounded; other places use +0.2235 — minor phrasing inconsistency |
| 2 | §2.9 Table 2.9 row 8 (R6 k6 foldability) Status column | "line 214" + tier-aware counterfactual parenthetical | line 214 | **CORRECT** (content CORRECT, audit cites correct line) |
| 3 | §3.3 Table 3.2 R6 row d_z column + bonf_sig | line 324 + +0.2235 d_z column | line 324 | **CORRECT** |
| 4 | §3.3 R6 paragraph "R6 tier-aware upgrade" | "line 339-343" | line 341 | **CORRECT** (audit cites a range; actual paragraph line is 341) |
| 5 | §7.1 Table 7.1 row 7 d_z column + bonf_sig | "line 672" | line 674 | **MINOR DRIFT** (off by 2 lines; content CORRECT) |
| 6 | §7.4 framework-not-theory verdict body | "line 697" | line 699 | **MINOR DRIFT** (off by 2 lines; content CORRECT) |

**Tier-aware d_z = +0.2235 numerical identity** verified across all paper edits:
- Per-tier breakdown consistent: hard +1.189 unchanged, medium +0.218 unchanged, easy −0.499 halved from uniform −0.998 ✓
- Bonferroni α = 0.05/6 = 0.008333 for R6 k6 per-tier family (paper §3.2 line 294: "R6 k6 per-tier family, k = 6 raw tests, α = 0.05/6 = 0.008333") ✓
- p_raw = 2.98 × 10⁻¹², p_bonf_tier-aware = 1.79 × 10⁻¹¹ consistent across all 5 edits ✓
- Mathematical-proxy disclosure present in §3.3 R6 paragraph line 341 + §2.9 Table 2.9 row 8 parenthetical + §7.1 row 7 d_z column + §7.4 line 699 ✓
- Cluster-robust uniform-arm d_z = +0.333, cluster p = 0.553 preserved as supplementary reading ✓

**Scheduler class reference** `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` verified verbatim: line 158 of that file is `class TierAwareCodimensionSheetScheduler:` ✓ — and `easy_tier_nfe_reduction_factor: float = 1.0` default verified at line 204 ✓.

**build_scheduler registry key** `tier_aware_codimension` referenced in §3.3 R6 paragraph (line 341): "the `TierAwareCodimensionSheetScheduler` class itself is fully implemented and reachable via the `build_scheduler` registry key `tier_aware_codimension`" — sourced from Wave 233 P3 audit doc.

### 3.2 R5b `n_rounds` conditional characterization (2 edits)

| # | Edit | Audit doc cites | Paper actual | Status |
|---:|---|---|---|---|
| 1 | §3.3 Table 3.2 R5b row | line 322 + "full conditional grid at §3.6" | line 322 + cross-link to `docs/audit/wave235-p1-r5b-fix.md` | **CORRECT** |
| 2 | §3.6 R5b `n_rounds` conditional characterization paragraph | "line 411-413" | line 417 | **MINOR DRIFT** (audit cites 411-413 which contains "Reading the conditional grid" bullets; actual paragraph is line 417) |

**Content verification**:
- n_rounds=1 WINS 4/4 schedulers: ΔFID ∈ [−0.06%, −0.88%], d_z ∈ [+4.29, +4.49] ✓
- n_rounds=2 REGRESSES 4/4 schedulers: ΔFID ∈ [+9.77%, +16.40%], d_z ∈ [+2.46, +3.21] ✓
- n_rounds=10 REGRESSES 4/4 schedulers: ΔFID ∈ [+24.46%, +30.19%], d_z ∈ [+2.700, +3.05] ✓
- 4-scheduler × 3-n_rounds = 12-cell grid Bonferroni α = 0.05/12 = 0.00417 ✓
- 3-source provenance verified (Wave 235 P1 + Wave 247 P3 + wf286 CIFAR; sha256 488655ce, 9301972a, 66c3c7ca) ✓
- Wave 233 P5 `RF_CIFAR_N_ROUNDS_OVERRIDE=2` reference present ✓
- Wave 235 P1 n_rounds=1 reversal data present ✓
- 3-N-points boundary consistent (N=200 EMA-corrected +221% / N=500 Source A +24-46% / N=1000 chunked-paired +20.21%) ✓

### 3.3 R5a two-readings reconciliation (1 paper edit + cross-doc)

| # | Edit | Audit doc cites | Paper actual | Status |
|---:|---|---|---|---|
| 1 | §3.5 R5a reconciliation paragraph | line 377 | line 377 | **CORRECT** |

**Content verification**:
- (i) R5a R-level paper cell d_s=+0.460 TIE (n=3 unpaired, p_raw=6.04e-1, CI=[-0.0058,+0.0104]) ✓
- (ii) R4 2D FM ablation headline -78.25% from 2D FM single_pass→multi_round_no_restart head-to-head (baseline W₂=2.85, framework W₂=0.62) ✓
- Both readings honestly coexist (paper R-level TIE vs 2D FM ablation framework-WINS) ✓
- DATA_PRESENTATION.md §3 footnote cross-reference present ✓

### 3.4 R5 legacy move to §10 supplementary (§10.9 new sub-section)

| # | Edit | Audit doc cites | Paper actual | Status |
|---:|---|---|---|---|
| 1 | §2.9 Table 2.9 row 5 Status column | line 210 | line 210 | **CORRECT** |
| 2 | §10.9 new sub-section | §10.9.1 through §10.9.6 (34 lines) | lines 963-993 (34 lines, 6 sub-paragraphs) | **CORRECT** |

**Content verification**:
- Status transition STRONG (legacy) → LEGACY (demoted to §10 supplementary) ✓
- Per-round raw CSV files (3 seeds × 5 schedulers × 20 rounds × 1000 samples/round) NOT preserved (canonical-honest disclosure) ✓
- SHA-256 references match: `docs/r4-survey/10-sota-2d-experiment-results.md` sha256 `9618e8f9...` + `verification_outputs/g1_deep_dive_q3_2026.json` sha256 `74ae053a...` ✓
- Multi-source support table with 25+ files per Wave 307 ✓
- §3.1 Bonferroni family k=7 unaffected (R5 NOT enumerated in §3.1) ✓
- Per-seed scalars −10.43% / −10.46% / −10.32% with paired-t ≈ −49.04 (df=2, p_raw≈1.8e-4, Bonf-PASS by 5.7×) ✓

### 3.5 R3 reconciliation (K8 paragraph)

| # | Edit | Audit doc cites | Paper actual | Status |
|---:|---|---|---|---|
| 1 | Table 3.2 R3 row n_paired column | line 320 (implied) | line 320 | **CORRECT** |
| 2 | §K8 paragraph | "line 441" | line 447 | **MINOR DRIFT** (off by 6 lines; content CORRECT) |

**Content verification**:
- Table 3.2 R3 row line 320: d_s=-0.110, p_raw=1.42e-2, per-record ACTUAL n=200, PROJECTED n=1000 via t-scaling from N=200 ✓
- §K8 paragraph line 447: same d_s=-0.110, p=1.42e-2, per-record ACTUAL n=200 (capped by `tools/wave87_n1000_sweep.py:298`), d_z=-0.285, PROJECTED n=1000 unchanged ✓
- Consistent on N=200 ACTUAL + p=1.07e-18 PROJECTION (both via t_N = t_200 · sqrt(N/200) formula) ✓

## 4. Numerical consistency cross-check

| Cell | Metric | Paper value | Audit value | Wave 233/235 source | Match? |
|---|---|---:|---:|---|:---:|
| R6 tier-aware overall pLDDT | d_z | +0.2235 | +0.2235 | wave233-p3 + wave225-p4 | ✓ |
| R6 tier-aware overall pLDDT | p_raw | 2.98 × 10⁻¹² | 2.978 × 10⁻¹² | wave233-p3-tier-aware-r6.json | ✓ |
| R6 tier-aware overall pLDDT | p_bonf | 1.79 × 10⁻¹¹ | 1.79 × 10⁻¹¹ | (computed: 2.978e-12 × 6) | ✓ |
| R6 hard pLDDT (tier-aware) | d_z | +1.189 | +1.189 | (unchanged) | ✓ |
| R6 medium pLDDT (tier-aware) | d_z | +0.218 | +0.218 | (unchanged) | ✓ |
| R6 easy pLDDT (tier-aware) | d_z | −0.499 | −0.499 | (halved from −0.998) | ✓ |
| R5b n_rounds=1 ΔFID | range | [−0.06%, −0.88%] | [−0.06%, −0.88%] | wave235-p1-r5b-fix.csv | ✓ |
| R5b n_rounds=1 d_z | range | [+4.29, +4.49] | [+4.29, +4.49] | wave235-p1 + wave247-p3 | ✓ |
| R5b n_rounds=2 ΔFID | range | [+9.77%, +16.40%] | [+9.77%, +16.40%] | wave233-p5 + wave225-p7 | ✓ |
| R5b n_rounds=10 ΔFID | range | [+24.46%, +30.19%] | [+24.46%, +30.19%] | wave235-p1 + no_final_restart | ✓ |
| R5a (R-level paper) | d_s, p_raw | +0.460, 6.04e-1 | +0.460, 6.04e-1 | wave196-p4-table-a-r-level.json | ✓ |
| R4 -78.25% (R5a footnote) | baseline W₂ → framework W₂ | 2.85 → 0.62 | 2.85 → 0.62 | g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation | ✓ |
| R5 legacy | baseline W₂ → framework W₂ (Δ%) | 0.6606 → 0.5919 (−10.40%) | 0.6606 → 0.5919 (−10.40%) | r4-survey/10-sota-2d-experiment-results.md | ✓ |
| R3 (Table 3.2 R3 row + K8) | d_s, p_raw, n ACTUAL | −0.110, 1.42e-2, 200 | −0.110, 1.42e-2, 200 | wave195-p2-r-level-power.csv + tools/wave87_n1000_sweep.py:298 | ✓ |
| R3 (per-record projected) | d_z, p PROJECTED | −0.285, 1.07e-18 | −0.285, 1.07e-18 | wave216-p1-r3-per-record | ✓ |

**All 15 numerical identities match across paper, audit docs, and cross-docs.**

## 5. Issues found

### 5.1 CRITICAL (paper): None

### 5.2 MINOR (audit docs / cross-doc citations / paper phrasing)

| # | Issue | File | Severity | Fix? |
|---:|---|---|---|---|
| 1 | §2.1 Table 2.1 TierAwareCodimensionSheetScheduler row says "+0.224 Bonf-sig" while all other locations say "+0.2235" (4-decimal-place consistency) | `docs/drafts/paper-flat-flattened.md` line 91 | MINOR (rounding phrasing) | Phase 3 cross-doc fix (paper line) |
| 2 | §7.1 Table 7.1 row 7 cited as "line 672" — actual line 674 | `docs/audit/wave310-r6-tier-aware-upgrade.md` §3.1 row 3; `docs/audit/wave310-restoration-execution.md` §2.2 | MINOR (off-by-2) | Phase 3 cross-doc fix |
| 3 | §7.4 framework-not-theory verdict cited as "line 697" — actual paragraph line 699 | same as above | MINOR (off-by-2) | Phase 3 cross-doc fix |
| 4 | K8 paragraph cited as "line 441" — actual line 447 | `docs/audit/wave310-restoration-execution.md` §2.6 | MINOR (off-by-6) | Phase 3 cross-doc fix |
| 5 | §3.6 R5b `n_rounds` conditional characterization cited as "line 411-413" — actual line 417 | `docs/audit/wave310-restoration-execution.md` §2.3 | MINOR (off-by-6) | Phase 3 cross-doc fix |
| 6 | "§7.1 Table 7.1 row 8 (R6 k6 foldability)" in audit §3.1 row 5 — actual edit was at §2.9 Table 2.9 row 8 line 214 | `docs/audit/wave310-r6-tier-aware-upgrade.md` §3.1 row 5 | MINOR (table-number confusion: Table 2.9 vs Table 7.1) | Phase 3 cross-doc fix |

### 5.3 PRE-EXISTING (not introduced by Wave 310)

| # | Issue | File | Severity | Fix? |
|---:|---|---|---|---|
| P1 | §7.2 row 3 (R3) lists "Bonferroni p = 0.014" — this is the p_raw value (1.42e-2), not a Bonferroni-corrected value (which would be ~0.0994) | `docs/drafts/paper-flat-flattened.md` line 670 (pre-Wave 310) | MINOR (pre-existing labeling) | NOT Wave 310 scope |
| P2 | §7.2 row 1 (R1) lists `p = 1.25×10⁻⁸` as "Bonferroni p" — this is the single-seed p_raw (which clears α=0.07 by 2.4× for the single-seed case); cluster-robust reading is UNDERPOWERED | `docs/drafts/paper-flat-flattened.md` line 668 (pre-Wave 310) | MINOR (pre-existing) | NOT Wave 310 scope |

### 5.4 INTERNAL CONSISTENCY VERIFIED (no issues)

- R6 tier-aware α = 0.05/6 = 0.008333 used consistently across paper §3.2 (line 294), §3.3 (line 324), §3.3 R6 paragraph (line 341), §2.9 Table 2.9 row 8 (line 214), §7.1 Table 7.1 row 7 (line 674), §7.4 (line 699). ✓
- Bonferroni at strict α=0.00208 (cluster-robust) used consistently for R6 hard pLDDT cluster-robust verdict. ✓
- R5b 12-cell grid α = 0.05/12 = 0.00417 used consistently across §3.3 R5b row (line 322), §3.6 R5b conditional grid paragraph (line 417), §7.1 Table 7.1 row 5 (line 672). ✓
- R3 d_s = −0.110 used consistently across Table 3.2 (line 320) + §K8 (line 447). ✓
- R3 ACTUAL n=200 + PROJECTED n=1000 via t-scaling t_N = t_200 · sqrt(N/200) used consistently across Table 3.2 (line 320) + §K8 (line 447) + Table 7.1 row 3 (line 670). ✓
- R6 tier-aware p_raw=2.98e-12, p_bonf=1.79e-11 consistent across §3.3 (line 324), §3.3 paragraph (line 341), §7.1 row 7 (line 674). ✓
- TierAwareCodimensionSheetScheduler code citation `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` matches verified line 158 of source file. ✓

### 5.5 PHASING / SCOPE ASSESSMENT

| Wave 310 edit | Edit scope | Lines added | Risk | Verified? |
|---|---|---|---|---|
| R6 tier-aware upgrade | 5 additive paper edits (Table 2.1, Table 2.9, Table 3.2, §3.3 R6 paragraph, §7.1 row 7, §7.4 framework-not-theory verdict) | +6 lines net | LOW (mathematical-proxy disclosure explicit) | YES |
| R5b `n_rounds` conditional | 2 additive paper edits (Table 3.2 R5b row + §3.6 paragraph) | +12 lines net | LOW (12-cell grid bonus is byte-stable; per-row ΔFID + d_z all verified) | YES |
| R5a two-readings | 1 paper edit (§3.5 reconciliation paragraph) | +1 paragraph (~4 lines) | LOW (both readings honestly disclosed; source attribution explicit) | YES |
| R5 legacy §10.9 | §2.9 Table 2.9 row 5 status + §10.9 new sub-section (34 lines, 6 sub-paragraphs) | +35 lines net | LOW (data-availability gap canonical-honest; multi-source-support verified) | YES |
| R3 K8 reconcile | 1 paper edit (§K8 paragraph) | +1 sentence (ACTUAL n=200 + PROJECTED n=1000 nuance) | LOW (textually consistent with Table 3.2 R3 row caption) | YES |
| R1 data provenance (prior commit `7a135ee`) | hits.tbl files committed + SOURCE.md provenance | +3 commits | LOW (data-archaeology-verified per Wave 307; SHA-256 stable) | YES (by audit doc) |

## 6. Editing discipline verification (Wave 268 strict-clean)

- [✓] Wave 310 paper-edits apply ADDITIVE only — verified by commit `51422a8` summary: 52 lines added to `paper-flat-flattened.md`, 0 deletions to legacy content.
- [✓] No §1 / §2.1 / §2.2 / §2.3 / §2.4 / §2.5 / §2.6 / §2.7 / §2.8 deletions on `docs/drafts/paper-flat-flattened.md`.
- [✓] Legacy §3.3 / §3.4 / §3.6 / §4 / §5 / §6 content preserved verbatim (no deletions).
- [✓] 5 verification gates PASS (Gate A ruff = 0 errors, Gate B pytest contracts = 195 passed, Gate C claims-consistency = no drift, Gate D mkdocs strict = exit 0, Gate E vendored-data NOT touched).

## 7. Verdict

**reviewVerdict: PASS_WITH_FIXES** — paper content is CORRECT across all 5 Wave 310 paper-edit cells. 6 MINOR audit-doc / cross-doc / paper phrasing issues found (line-number drift + 1 rounding phrasing + 1 table-number typo). None affect the paper's scientific content. All 6 issues will be fixed in Phase 3 cross-doc propagation pass.

**No CRITICAL issues found.**

**No paper edits applied in this D+1 review pass** (per task directive: "If CRITICAL issues found: apply fixes via Edit tool. If MINOR issues found: list them in issuesFound but do not modify (will fix in Phase 3 cross-doc).")

## 8. Status

**ACTIVE — Wave 311 D+1 review PASS_WITH_MINOR_FIXES:**

- [x] Phase 1 — paper content verified CORRECT across all 5 Wave 310 cells
- [x] Phase 2 — numerical identity cross-check PASS (15/15 identities match)
- [x] Phase 3 — 6 MINOR audit-doc / cross-doc / paper phrasing issues identified (line-number drift + 1 rounding + 1 table-number confusion)
- [x] Phase 4 — 2 PRE-EXISTING issues identified (NOT introduced by Wave 310; out of scope)
- [x] Phase 5 — verification table written
- [x] NO paper edits applied (Phase 3 cross-doc fix deferred)
- [x] NO push per Wave 311 NO PUSH directive

## 9. References

- `docs/drafts/paper-flat-flattened.md` (paper body, 1566 lines / 43639 words / 1 H1 + 23 ## + 59 ### + 1 ####)
- `docs/audit/wave310-r6-tier-aware-upgrade.md` (121-line Wave 310 R6 cross-doc-propagation audit)
- `docs/audit/wave310-restoration-execution.md` (231-line Wave 310 D2 restoration execution + 5-gate verification)
- `docs/audit/wave309-paper-a-restoration-plan.md` (381-line Wave 309 paper-A restoration plan)
- `docs/audit/wave307-data-archaeology.md` (Wave 307 R1/R5c/K7/K1/K4 originals audit; supports §10.9 R5 disclosure)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` (TierAwareCodimensionSheetScheduler class)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:204` (`easy_tier_nfe_reduction_factor: float = 1.0` parameter)
- `tools/wave87_n1000_sweep.py:298` (R3 per-record ACTUAL n=200 cap)
- commit `51422a8` (Wave 310 D2 restoration execution)
- commit `7a135ee` (Wave 310 R1 data provenance, prior commit)

---

**End of Wave 311 D+1 self-review. Verdict: PASS_WITH_FIXES (paper CORRECT; 6 MINOR issues to fix in Phase 3).**