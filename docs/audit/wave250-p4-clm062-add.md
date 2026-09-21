# Wave 250 P4 — CLM-062 added to paper §3.5 (Wave 195 P4 12-cell Theorem 1 load-bearing verdict distribution)

**Date:** 2026-09-22
**Branch:** main
**Scope:** Wave 250 P4 — add CLM-062 (Wave 195 P4 12-cell per-cell Theorem 1
load-bearing power analysis) to paper §3.5 as an additive paragraph after the
current §3.5 CLM-058 paragraph, reporting the full 12-cell verdict
distribution (1 SUPPORTED / 0 REGRESSES / 8 TIE / 3 UNDERPOWERED / 0 NOT_SIGNIFICANT).

---

## 1. Goal

Additive integration of CLM-062 into paper §3.5 (Theorem 1 load-bearing
discussion) so the §3.5 narrative cites the **decision-honest 12-cell verdict
distribution** in addition to the single-cell `$d = +10.24$` quote already
present. The full 12-cell matrix is reported (1 SUPPORTED + 0 REGRESSES + 8
TIE + 3 UNDERPOWERED + 0 NOT_SIGNIFICANT), the single SUPPORTED cell
(`C-K-L2-CvB`) is named explicitly, and the n=30 paired-design budget ceiling
is surfaced honestly (3 cells UNDERPOWERED with post-hoc power at the 1.0 L2 /
0.01 ΔS practical floor < 0.5).

---

## 2. CLM-062 verbatim (from `docs/CLAIMS.md` line 3354)

> **CLM-062**: Wave 195 P4 — Theorem 1 load-bearing per-cell power
> analysis (12 cells = 2 adapters × 3 arm comparisons × 2 axes on kanzi
> + lineageflow at n=30 paired seeds) — Bonferroni-corrected α=0.05/12
> =0.004167 per cell, verdict-precedence distribution is **1 SUPPORTED
> / 0 REGRESSES / 8 TIE / 3 UNDERPOWERED / 0 NOT_SIGNIFICANT**; the
> single `load_bearing_supported` cell is **C-K-L2-CvB** (kanzi L2
> cosine-vs-baseline, Cohen's `d_z = −11.15`, p_bonf = 4.14e-31, Δ =
> −16.88, framework WIN: cosine-arm L2 movement is significantly
> smaller than baseline); the 8 TIE cells are all lineageflow × {L2,
> ΔS} cells + 2 kanzi byte-stable composite cells where `|Δ| <
> min_effect_size` (1.0 L2 unit / 0.01 ΔS unit floor); the 3
> UNDERPOWERED cells are kanzi × {L2-PvC, ΔS-PvC, ΔS-CvB} where the
> test rejects H0 trivially on the observed δ (Cohen's `d_z` 10.24–
> 30.15, p_bonf < 5e-30) but post-hoc power at `min_effect_size` is
> below 0.5 — load_bearing_supported count is **1/12 cells (1/4 of the
> kanzi cells)**; no cell REGRESSES.

---

## 3. 12-cell matrix (reference)

Per `docs/audit/wave195-p1-power-spec.md` §4.1 and
`docs/audit/wave195-p4-theorem1-power.md` §2:

| id          | adapter    | arm_comparison     | axis     | verdict       |
|-------------|------------|--------------------|----------|---------------|
| C-K-L2-PvC  | kanzi      | paper_vs_cosine    | L2       | UNDERPOWERED  |
| C-K-L2-PvB  | kanzi      | paper_vs_baseline  | L2       | TIE           |
| C-K-L2-CvB  | kanzi      | cosine_vs_baseline | L2       | **SUPPORTED** |
| C-K-DS-PvC  | kanzi      | paper_vs_cosine    | ΔS       | UNDERPOWERED  |
| C-K-DS-PvB  | kanzi      | paper_vs_baseline  | ΔS       | TIE           |
| C-K-DS-CvB  | kanzi      | cosine_vs_baseline | ΔS       | UNDERPOWERED  |
| C-LF-L2-PvC | lineageflow| paper_vs_cosine    | L2       | TIE           |
| C-LF-L2-PvB | lineageflow| paper_vs_baseline  | L2       | TIE           |
| C-LF-L2-CvB | lineageflow| cosine_vs_baseline | L2       | TIE           |
| C-LF-DS-PvC | lineageflow| paper_vs_cosine    | ΔS       | TIE           |
| C-LF-DS-PvB | lineageflow| paper_vs_baseline  | ΔS       | TIE           |
| C-LF-DS-CvB | lineageflow| cosine_vs_baseline | ΔS       | TIE           |

**Tally**: 1 SUPPORTED + 0 REGRESSES + 8 TIE + 3 UNDERPOWERED + 0
NOT_SIGNIFICANT = 12 cells.

---

## 4. Paper edit

### 4.1 File

`/home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-flattened-draft.md`

### 4.2 Location

§3.5 (Theorem 1 load-bearing discussion), inserted as the new **5th paragraph**
after the existing CLM-058 paragraph (line 301 of the prior state of the
file). The new paragraph now lives at line 303 of the updated file; the §3.5
heading (`### 3.5 Why the paper quantities are load-bearing...`) is at line
293 and §3.6 (NFE-matched boundary) remains at line 305.

### 4.3 Wording (verbatim from Wave 249 P4 audit recommendation, applied with
the paper's existing LaTeX math conventions for $\alpha$, $d_z$,
$p_{\text{bonf}}$, $\Delta$, $H_0$):

> "The Theorem 1 load-bearing test on the Kanzi + LineageFlow synthetic
> protein axes, formalised as the Wave 195 P4 12-cell per-cell power
> analysis (Bonferroni $\alpha = 0.05/12 = 0.004167$ per cell, n=30 paired
> seeds, paired t-test with Cohen's $d_z$ on within-subject diffs), returns
> a verdict-precedence distribution of **1 SUPPORTED / 0 REGRESSES / 8 TIE
> / 3 UNDERPOWERED / 0 NOT_SIGNIFICANT**. The single
> `load_bearing_supported` cell is **C-K-L2-CvB** (kanzi L2
> cosine-vs-baseline, Cohen's $d_z = -11.15$, $p_{\text{bonf}} = 4.14
> \times 10^{-31}$, $\Delta = -16.88$). The 8 TIE cells are all 6
> lineageflow cells (field too small to resolve at n=30) plus 2 kanzi
> byte-stable composite cells ($|\Delta| < \text{min\_effect\_size}$). The
> 3 UNDERPOWERED cells are kanzi × {L2-PvC, ΔS-PvC, ΔS-CvB} where
> observed Cohen's $d_z \in [10.24, 30.15]$ rejects $H_0$ trivially but
> post-hoc power at the 1.0 L2 / 0.01 ΔS practical floor is below 0.5.
> The 1/12 verdict is the decision-honest reading of the n=30 paired
> design; no cell REGRESSES (CLM-062, Wave 195 P4 12-cell verdict
> distribution)."

### 4.4 Diff (before → after, §3.5)

**Before (4 paragraphs):**
- §3.5 ¶1 (line 295): "A reviewer-facing observation..." — structural
  load-bearing observation.
- §3.5 ¶2 (line 297): "The Theorem 1 load-bearing test on the Kanzi..." —
  single-cell `$d = +10.24$` quote (C-K-DS-PvC).
- §3.5 ¶3 (line 299): "On the kanzi synthetic protein axis..." — CLM-057.
- §3.5 ¶4 (line 301): "Cross-adapter Theorem 1 quantities confirmation..." —
  CLM-058.

**After (5 paragraphs):**
- §3.5 ¶1-4 unchanged.
- **§3.5 ¶5 (new, line 303)**: "The Theorem 1 load-bearing test on the Kanzi
  + LineageFlow synthetic protein axes..." — CLM-062 12-cell verdict
  distribution (1/0/8/3/0), single SUPPORTED C-K-L2-CvB identified,
  decision-honest framing.

No existing paragraph was rewritten or removed; the edit is **purely
additive** per the Wave 250 P4 hard rule "DO NOT remove or rewrite existing
§3.5 (additive only)".

---

## 5. Rationale

### 5.1 Why additive (not replacement)?

CLM-062 is the **12-cell matrix framing** of the Theorem 1 load-bearing
finding; the existing §3.5 ¶2 single-cell `$d = +10.24$` quote cites
**one cell** (C-K-DS-PvC, kanzi ΔS paper-vs-cosine, UNDERPOWERED verdict).
Without the 12-cell context, a reviewer reading the single-cell quote might
suspect cherry-picking. CLM-062 surfaces the full matrix: 1 SUPPORTED + 8 TIE
+ 3 UNDERPOWERED + 0 REGRESSES, naming the single SUPPORTED cell
(`C-K-L2-CvB`) and the 3 UNDERPOWERED cells.

### 5.2 Why this is the single SUPPORTED cell?

Per `docs/audit/wave195-p4-theorem1-power.md` §3.1:
* **C-K-L2-CvB** is the **cosine-vs-baseline** arm comparison on the **L2
  axis** of the **kanzi** adapter. Cohen's `$d_z = -11.15$` on n=30 paired
  diffs (df=29), p_bonf = 4.14e-31, Δ = -16.88 L2 units. The cosine arm's
  L2 endpoint movement is significantly **smaller** than the baseline,
  confirming the cosine ramp regularises the L2 perturbation. Post-hoc
  power at the 1.0 L2 practical floor is 0.9513 (above the 0.5 floor), so
  this cell has both **observed effect** AND **post-hoc power** aligned with
  the practical floor — the only cell where both align.

### 5.3 Why are 3 cells UNDERPOWERED (not SUPPORTED)?

Per the Wave 195 P4 verdict-precedence chain (TIE > UNDERPOWERED > SUPPORTED
> REGRESSES > NOT_SIGNIFICANT, see `wave195-p1-power-spec.md` §1.1):
* **C-K-L2-PvC, C-K-DS-PvC, C-K-DS-CvB** have observed Cohen's `$d_z \in
  [10.24, 30.15]$` and p_bonf < 5e-30, so the **observed effect** is huge.
  But post-hoc power at the 1.0 L2 / 0.01 ΔS practical floor is below 0.5
  (the n=30 paired design cannot reliably detect the practical floor even
  though the observed effect is 30×–100× the floor). These cells are flagged
  UNDERPOWERED rather than SUPPORTED per the verdict-precedence chain.
* The verdict-precedence chain is **decision-honest**: re-labelling these
  cells as SUPPORTED to inflate the count would be cherry-picking. The
  Wave 195 P4 audit doc explicitly documents this deviation from the Wave
  195 P1 spec §4.6 expected verdicts (which predicted 4 cells SUPPORTED).

### 5.4 Why are 8 cells TIE?

* **All 6 lineageflow × {L2, ΔS} cells** are TIE because the lineageflow
  field's natural scale (~5) leaves both arms at ~0.115 L2 — the field is
  too small to resolve at n=30 paired seeds.
* **2 kanzi byte-stable composite cells (C-K-L2-PvB, C-K-DS-PvB)** are TIE
  because `|Δ| < min_effect_size` (1.0 L2 / 0.01 ΔS floor).

### 5.5 Cherry-picking risk

**LOW.** The full 12-cell matrix is reported in verbatim prose (1/0/8/3/0);
the single SUPPORTED cell is **named** (not implied), and the 3
UNDERPOWERED cells are **named** with the post-hoc-power reasoning. The
verdict-precedence chain (TIE > UNDERPOWERED > SUPPORTED > REGRESSES >
NOT_SIGNIFICANT) is documented in `wave195-p1-power-spec.md` §1.1 and
referenced in `wave195-p4-theorem1-power.md` §3.

---

## 6. Acceptance gates

| #  | gate                                                                       | status |
|----|----------------------------------------------------------------------------|--------|
| 1  | CLM-062 verbatim extracted from `docs/CLAIMS.md` line 3354                 | PASS   |
| 2  | 12-cell setup verified (2 adapters × 3 arm comparisons × 2 axes)          | PASS   |
| 3  | Verdict distribution (1/0/8/3/0) verified against `wave195-p4-...md` §2  | PASS   |
| 4  | Single SUPPORTED cell C-K-L2-CvB disclosed in §3.5 ¶5 (new)               | PASS   |
| 5  | Single SUPPORTED cell Cohen's d_z = -11.15 disclosed                      | PASS   |
| 6  | Single SUPPORTED cell p_bonf = 4.14e-31 disclosed                          | PASS   |
| 7  | Single SUPPORTED cell Δ = -16.88 disclosed                                 | PASS   |
| 8  | Decision-honest framing ("decision-honest reading of n=30 paired design") | PASS   |
| 9  | "no cell REGRESSES" disclosed                                              | PASS   |
| 10 | §3.5 ¶1-4 NOT modified (additive only)                                     | PASS   |
| 11 | §3.6 onward NOT modified                                                   | PASS   |
| 12 | D.4 30/30 PASS preserved                                                   | PASS   |
| 13 | mkdocs 0 warnings preserved                                                | PASS   |
| 14 | Audit doc created at `docs/audit/wave250-p4-clm062-add.md`                 | PASS   |

All 14 gates PASS.

---

## 7. References

* `docs/CLAIMS.md` line 3354 — CLM-062 verbatim.
* `docs/audit/wave249-p4-clm062-wave191-audit.md` — Wave 249 P4 pre-flight
  audit (CLM-062 OK to add as additive §3.5 paragraph; Wave 191 P3 MNIST
  smoke-ckpt PROVISIONAL status).
* `docs/audit/wave195-p1-power-spec.md` §4 + §1.1 — 12-cell setup,
  verdict-precedence chain (TIE > UNDERPOWERED > SUPPORTED > REGRESSES >
  NOT_SIGNIFICANT).
* `docs/audit/wave195-p4-theorem1-power.md` §2 + §3 — 12-cell per-cell
  results, decision-honest deviation from spec.
* `verification_outputs/wave195-p4-theorem1-power.{csv,json}` — 12-cell
  per-cell power analysis outputs (frozen at commit `76108b5`).
* `verification_outputs/wave190-p2-kanzi-n30.json` — kanzi n=30 paired sweep
  source.
* `verification_outputs/wave190-p3-lineageflow-n30.json` — lineageflow n=30
  paired sweep source.
* `docs/drafts/paper-flattened-draft.md` §3.5 (current HEAD) — paper
  destination.
* `docs/CLAIMS.md` line 2661 — CLM-057 (kanzi n=30 upgrade).
* `docs/CLAIMS.md` line 2810 — CLM-058 (cross-adapter Theorem 1 quantities).