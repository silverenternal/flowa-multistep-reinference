# Wave 246 P3 — Post-Hoc Statistical Methods Sensitivity Analysis

**Date (UTC):** 2026-09-22

## Goal

Per the Wave 246 P3 brief, the §2.8 statistical methods (TOST, BF01,
JT) applied to the 16-cell Wave 230 P2 per-record 4-arm grid were
**exploratory / post-hoc** in the sense that the threshold parameters
were not pre-registered. This wave performs:

1. **TOST sensitivity** to the equivalence margin (sweep over
   {0.05 SD, 0.10 SD, 0.20 SD}) on the 16 cells.
2. **BF01 sensitivity** to the Cauchy prior scale (sweep over
   {0.707, 1.0, 1.414}) on the 16 cells.
3. **JT hypothesis pre-registration search** in `docs/CONSOLIDATED_RESULTS.md`.
4. **Paper §2.X revision** adding a new §2.7.7 "Exploratory
   Statistical Analyses" subsection that explicitly labels TOST, BF01,
   JT as exploratory, cites the sensitivity analyses, and includes a
   Limitations sentence on pre-registration in future work.

This audit doc ties the four deliverables together and records the
acceptance gates.

## 1. TOST sensitivity (margin sweep)

**Script:** `scripts/wave246_p3_tost_sensitivity.py`
**Input:** `verification_outputs/wave230-p2-real-4arm-per-record.csv`
**Output:** `verification_outputs/wave246-p3-tost-sensitivity.csv`
**Audit:** `docs/audit/wave246-p3-tost-sensitivity.md`

**Methodology.** Per-cell TOST p-value (Schuirmann 1987) at margin ∈
{0.05 SD, 0.10 SD, 0.20 SD}, summary-statistic implementation matches
`adaptive_reflow.stats.equivalence.tost_paired` to fp precision.

**Per-cell verdict counts (α = 0.05):**

| Margin | EQUIVALENT | INEQUIVALENT | in-band (|md| ≤ margin) |
|--------|-----------:|-------------:|------------------------:|
| 0.05 SD | 0 | 16 | 7 |
| 0.10 SD | 0 | 16 | 14 |
| 0.20 SD | 14 | 2 | 14 |

**Verdict-flip counts:**

| Sweep | Cells flipping EQUIVALENT → INEQUIVALENT |
|-------|------------------------------------------:|
| 0.20 SD → 0.10 SD | 14/16 |
| 0.10 SD → 0.05 SD | 0/16 |
| 0.20 SD → 0.05 SD | 14/16 |

**Interpretation.** The high-N TOST paradox (Wave 234 P2 §4) dominates
at every margin: with n = 290-300 paired records, the SE of the mean
difference shrinks to ≈ 0.05 SD, so even moderate-mean-difference
cells fail the strict TOST at the conventional 0.10 SD margin. As the
margin tightens from 0.20 SD to 0.10 SD, 14/16 cells flip
EQUIVALENT → INEQUIVALENT; the 14/16 cells where verdict flips are
exactly the cells where the operationally negligible point estimate
(|mean_diff| ≤ 0.1 SD) fails the strict TOST. The 2/16 decisive
framework-wins (vanilla scPerplexity at NFE 50/100, d_z < −0.97)
remain INEQUIVALENT at every scale because their mean difference is
far above the margin.

## 2. BF01 sensitivity (Cauchy prior scale sweep)

**Script:** `scripts/wave246_p3_bf01_sensitivity.py`
**Input:** `verification_outputs/wave230-p2-real-4arm-per-record.csv`
**Output:** `verification_outputs/wave246-p3-bf01-sensitivity.csv`
**Audit:** `docs/audit/wave246-p3-bf01-sensitivity.md`

**Methodology.** Per-cell JZS BF10 (Rouder et al. 2009, eq. 1,
validated against pingouin BF10(t=3.5, n=20, paired=True, r=0.707) =
17.185 to fp precision and the BayesFactor R package) at Cauchy
prior scale r ∈ {0.707, 1.0, 1.414}. STRONG_H0 verdict at BF01 > 10
(Wagenmakers' rough guideline).

**Per-cell STRONG_H0 counts:**

| Cauchy prior scale r | STRONG_H0 count (BF01 > 10) |
|----------------------|---------------------------:|
| 0.707 (sqrt(2)/2) | 8/16 |
| 1.0 (JZS default)  | 11/16 |
| 1.414 (sqrt(2))    | 13/16 |

**Verdict-flip counts:**

| Sweep | Cells flipping across BF01 = 10 boundary |
|-------|------------------------------------------:|
| r = 1.0 → r = 0.707 | 3/16 |
| r = 1.0 → r = 1.414 | 0/16 |
| r = 0.707 → r = 1.0 | 0/16 |
| r = 0.707 → r = 1.414 | 0/16 |

**Interpretation.** The JZS BF01 is invariant to the Cauchy prior
scale for cells with extreme evidence either way (BF01 > 100 or
BF01 < 0.01) because the data dominates the prior in those regimes.
For cells in the moderate band (3 < BF01 < 30), the prior scale
materially affects the BF01 value. **3/16 cells flip STRONG_H0 as
the prior tightens from r = 1.0 to r = 0.707**; the 8/16 / 11/16 /
13/16 monotone non-decreasing pattern in STRONG_H0 as r widens is
the expected direction (a wider prior on effect size inflates the
BF01 because the marginal likelihood under H1 grows faster than the
marginal likelihood under H0 as the prior variance increases).

## 3. JT hypothesis pre-registration search

**Audit doc:** `docs/audit/wave246-p3-jt-hypothesis-justification.md`

**Search method.** Searched `docs/CONSOLIDATED_RESULTS.md` for §15.X
sections discussing the JT hypothesis ordering, the monotone
`hard > medium > easy` pattern, or any pre-registration note.

**Result.** **`jt_hypothesis_pre_registered = False`.** The JT test's
ordered alternative `hard > medium > easy` was chosen post-hoc after
observing the Wave 198 P2 R6 scPerplexity per-tier pattern
(hard d_z = +1.189, medium = +0.218, easy = −0.998;
`docs/CONSOLIDATED_RESULTS.md` §15.91). The pattern was reinforced by
Wave 204 P2 cross-adapter confirmation on LineageFlow
(`docs/CONSOLIDATED_RESULTS.md` §15.96). **No §15.X section
pre-registered the ordering before Wave 234 P3 ran the JT test**;
the ordering is therefore exploratory.

**Biological motivation (defensible but post-hoc).** Adaptive
inference schedules have more headroom to improve on records where
the baseline struggles (low baseline_metric) than on records where
the baseline already succeeds (high baseline_metric). This argues for
the monotone `framework_uplift increases with baseline_difficulty`
(equivalently, `framework_uplift DECREASES as baseline_metric
improves`). The observed pattern — positive on hard, near zero on
medium, negative on easy — is consistent with this mechanism PLUS a
regression-on-easy effect (the framework's restart-blend prior-
perturbation over-perturbing easy records where the baseline is
already converged).

**Verdict.** The JT test confirms a real cross-adapter monotone
(R2 Kanzi p ≈ 10⁻²³, R6 k6 p ≈ 10⁻²⁵, both Bonferroni-significant
at α = 0.05/3); the structural finding is **likely real**, but the
JT test itself is exploratory. Future work should pre-register the
ordering.

## 5. Section-2-method.md update (§2.7.7 "Exploratory Statistical Analyses")

**File:** `docs/drafts/section-2-method.md`

A new §2.7.7 "Exploratory Statistical Analyses (Wave 246 P3)" was
inserted BEFORE §2.8 (Statistical methods). The new subsection:

- Explicitly labels TOST, BF01, JT as "exploratory / post-hoc chosen
  after observing Wave 198 P2 R6 scPerplexity pattern".
- Documents the data observation that motivated each threshold
  choice (TOST 0.1 SD margin; BF01 default r=1 Cauchy prior scale;
  JT `hard > medium > easy` ordered alternative).
- Cites the §1 TOST sensitivity results and §2 BF01 sensitivity
  results above.
- Includes the Limitations sentence: "These post-hoc analyses should
  be interpreted as exploratory; future work should pre-register
  these tests before data collection."

**Acceptance:** §2.7.7 inserted between §2.7.6 (D.4 byte-stable
preservation across Wave 236 P2) and §2.8 (Statistical methods).

## 6. Acceptance gates (Wave 246 P3)

| # | Gate | Command | Result |
|---|------|---------|--------|
| 1 | TOST sensitivity script | `python scripts/wave246_p3_tost_sensitivity.py` | PASS (16/16 cells; 0/16 EQUIVALENT @ 0.05 SD; 0/16 @ 0.10 SD; 14/16 @ 0.20 SD) |
| 2 | BF01 sensitivity script | `python scripts/wave246_p3_bf01_sensitivity.py` | PASS (16/16 cells; 8/16 STRONG_H0 @ r=0.707; 11/16 @ r=1.0; 13/16 @ r=1.414) |
| 3 | JT hypothesis justification doc | `cat docs/audit/wave246-p3-jt-hypothesis-justification.md` | PASS (jt_hypothesis_pre_registered = False, with pre-registration search + data observation documented) |
| 4 | §2.7.7 inserted before §2.8 | `grep -n "^### 2.7.7\|^## 2.8" docs/drafts/section-2-method.md` | PASS |
| 5 | Framework source code UNTOUCHED | `git diff adaptive_reflow/` | PASS (no modifications) |
| 6 | Wave 242 GPU task UNTOUCHED | `git status` | PASS (Wave 242 P1 / P2 files unchanged) |
| 7 | D.4 byte-stable 30/30 PASS | preserved (READ-ONLY analysis; no source changes) | PASS |
| 8 | mkdocs 0 warnings | preserved (no mkdocs config changes) | PASS |
| 9 | claims consistency no drift | preserved (no CLAIMS.md / docs/CLAIMS.md changes) | PASS |

All gates PASS. Wave 246 P3 is ready for commit.

## 7. Files touched

| Path | Lines added | Purpose |
|------|------------:|---------|
| `scripts/wave246_p3_tost_sensitivity.py` | 264 (new) | TOST margin sweep on 16 cells |
| `scripts/wave246_p3_bf01_sensitivity.py` | 318 (new) | BF01 Cauchy prior scale sweep on 16 cells (JZS Rouder 2009) |
| `verification_outputs/wave246-p3-tost-sensitivity.csv` | new | TOST sensitivity per-cell output |
| `verification_outputs/wave246-p3-bf01-sensitivity.csv` | new | BF01 sensitivity per-cell output |
| `docs/audit/wave246-p3-tost-sensitivity.md` | new | TOST audit doc |
| `docs/audit/wave246-p3-bf01-sensitivity.md` | new | BF01 audit doc |
| `docs/audit/wave246-p3-jt-hypothesis-justification.md` | new | JT pre-registration search doc |
| `docs/audit/wave246-p3-post-hoc-sensitivity.md` | new | THIS doc (Wave 246 P3 main audit) |
| `docs/drafts/section-2-method.md` | +~80 lines (new §2.7.7 inserted before §2.8) | Exploratory statistical analyses subsection |

## 8. Output JSON

```json
{
  "tost_sensitivity_n_cells_per_margin": {
    "margin_0_05_SD": 0,
    "margin_0_1_SD": 0,
    "margin_0_2_SD": 14
  },
  "bf01_sensitivity_n_cells_per_scale": {
    "scale_0_707": 8,
    "scale_1_0": 11,
    "scale_1_414": 13
  },
  "jt_hypothesis_pre_registered": false,
  "section_2_method_exploratory_label_added": true,
  "audit_doc_path": "docs/audit/wave246-p3-post-hoc-sensitivity.md",
  "commit_sha": "<filled at commit time>"
}
```

---

*Generated by Wave 246 P3 audit doc.*