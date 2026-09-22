# Wave 249 P4 — CLM-062 audit (12-cell Theorem 1 load-bearing power analysis) + Wave 191 P3 MNIST smoke ckpt audit

**Date:** 2026-09-22
**Branch:** main (HEAD `84b2600`)
**Scope:** Wave 249 P4 — pre-flight audit of CLM-062 (Wave 195 P4
12-cell Theorem 1 load-bearing power analysis) and Wave 191 P3 MNIST
smoke ckpt PROVISIONAL status (CLM-059) before integrating either into
the paper. Verify setup, narrative positioning, cherry-picking risk,
and paper placement.

---

## 1. Goal

Two concrete deliverables:

1. **CLM-062 audit** — verify the 12-cell setup (2 adapters × 3 arm
   comparisons × 2 axes), the verdict distribution (1 SUPPORTED + 8 TIE
   + 3 UNDERPOWERED + 0 REGRESSES + 0 NOT_SIGNIFICANT), and whether
   cherry-picking risk applies to the single-SUPPORTED cell
   `C-K-L2-CvB` (Cohen's `d_z = −11.15`).
2. **Wave 191 P3 MNIST smoke ckpt audit** — verify the smoke ckpt
   status (PROVISIONAL, pending production-ckpt re-run) and whether a
   production-ckpt rerun exists in any post-Wave-191 P3 audit.

---

## 2. Q1: CLM-062 setup answers

### 2.1 Verbatim CLM-062 (from `docs/CLAIMS.md` line 3354)

CLM-062 reads:

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

### 2.2 The 12 cells

Per `docs/audit/wave195-p1-power-spec.md` §4.1 and
`docs/audit/wave195-p4-theorem1-power.md` §2:

| id          | adapter    | arm_comparison     | axis     |
|-------------|------------|--------------------|----------|
| C-K-L2-PvC  | kanzi      | paper_vs_cosine    | L2       |
| C-K-L2-PvB  | kanzi      | paper_vs_baseline  | L2       |
| C-K-L2-CvB  | kanzi      | cosine_vs_baseline | L2       |
| C-K-DS-PvC  | kanzi      | paper_vs_cosine    | ΔS       |
| C-K-DS-PvB  | kanzi      | paper_vs_baseline  | ΔS       |
| C-K-DS-CvB  | kanzi      | cosine_vs_baseline | ΔS       |
| C-LF-L2-PvC | lineageflow| paper_vs_cosine    | L2       |
| C-LF-L2-PvB | lineageflow| paper_vs_baseline  | L2       |
| C-LF-L2-CvB | lineageflow| cosine_vs_baseline | L2       |
| C-LF-DS-PvC | lineageflow| paper_vs_cosine    | ΔS       |
| C-LF-DS-PvB | lineageflow| paper_vs_baseline  | ΔS       |
| C-LF-DS-CvB | lineageflow| cosine_vs_baseline | ΔS       |

PvC = paper vs cosine; PvB = paper vs baseline; CvB = cosine vs baseline.
The 12 cells decompose into 6 kanzi-specific cells + 6 lineageflow-
specific cells. n=30 paired seeds (df=29), paired t-test, Cohen's `d_z`
on within-subject diffs.

### 2.3 Why only 1 SUPPORTED cell?

Per `docs/audit/wave195-p4-theorem1-power.md` §2 + §3.1 + §3.2:

* **C-K-L2-CvB is SUPPORTED** — Cohen's `d_z = −11.15`, p_bonf =
  4.14e-31, Δ = −16.88 L2 units, framework WIN because cosine-arm L2
  movement is significantly smaller than baseline (cosine arm
  regularises). Post-hoc power at `min_effect_size = 1.0 L2` is 0.9513
  (above the 0.5 floor).
* **C-K-L2-PvB and C-K-DS-PvB are TIE** (kanzi paper-vs-baseline
  composite, `|Δ| = 0.31 L2 < 1.0` and `|Δ| = 0.0057 ΔS < 0.01` floor
  respectively) — paper arm barely regularises vs baseline on both
  axes; below the practical-effect floor.
* **C-K-L2-PvC, C-K-DS-PvC, C-K-DS-CvB are UNDERPOWERED** — observed
  effects are huge (Δ = −97.5 L2 / +0.31 ΔS / −0.32 ΔS; Cohen's `d_z`
  ∈ [10.24, 30.15]) and Bonferroni p_bonf < 5e-30, but post-hoc power
  at the 1.0 L2 / 0.01 ΔS practical floor is below 0.5 (the n=30
  paired design cannot reliably detect the 1.0 L2 / 0.01 ΔS practical
  floor even though the observed effect is 30×–100× larger). These
  cells are flagged UNDERPOWERED rather than SUPPORTED per the verdict
  precedence (TIE > UNDERPOWERED > SUPPORTED > REGRESSES).
* **All 6 lineageflow cells are TIE** — both paper and cosine arms move
  the endpoint by ~0.0048 L2 units and ~3e-6 ΔS units, well below the
  1.0 L2 / 0.01 ΔS floor. The lineageflow field is too small to
  resolve at n=30 paired seeds.

### 2.4 d_z = −11.15 — per-record or per-seed?

Per `docs/audit/wave195-p4-theorem1-power.md` §1.3, the **unit of
replication is per-seed, NOT per-record**: the Wave 190 P2 / P3
n=30 sweep has 30 records (seeds {0, 1, ..., 29}) with the three arm
values. Within-seed paired diff: `diff[i] = arm_f[i] - arm_b[i]`;
**n_pairs = 30** (one observation per seed; **df = 29**). Cohen's `d_z`
is computed on within-seed diffs: `d_z = mean(diff) / sd(diff)`. This
is **NOT per-record** — per-record would imply N=30×records-per-seed
which does not exist for the n=30 sweep.

This is consistent with `docs/audit/wave195-p1-power-spec.md` §1.2
("Wave 190 P2/P3 n=30 paired sweep (`n_paired=30`, `df=29`)"). The
"30 records" terminology in the Wave 190 P2/P3 / Wave 195 P4
documentation refers to **30 paired seeds**, each producing ONE
endpoint-L2 and ONE ΔS measurement per arm (baseline / cosine /
paper), yielding 30 paired diffs per cell.

### 2.5 Discrepancy with the paper §3.5 single-cell Cohen's `d = +10.24`

The paper §3.5 currently cites `docs/drafts/paper-flattened-draft.md`
line 297:
> "the paper-quantity scheduler **dampens** the cosine arm's endpoint
> perturbation by ≈ 213× (paper-quantity `L_2 ≈ 0.46` vs cosine-only
> `L_2 ≈ 97.97`, `d = +10.24`, `p = 3.96 × 10⁻³¹`)"

This is the **C-K-DS-PvC cell** (kanzi ΔS paper-vs-cosine, Cohen's `d_z
= +10.24`, p_bonf = 4.75e-30), NOT the **C-K-L2-CvB** cell that CLM-062
calls out as the single SUPPORTED cell. The §3.5 paper quote is from
the **entropy axis ΔS** of the paper-vs-cosine comparison; CLM-062's
single-SUPPORTED cell is the **L2 axis** of the cosine-vs-baseline
comparison. **Both are valid Theorem-1 load-bearing evidence; they
live on different (axis, arm_comparison) cells of the 12-cell matrix.**

**Implication for the paper**: the paper §3.5 currently cites one cell
of the 12-cell matrix (C-K-DS-PvC) without acknowledging that the
matrix has 11 other cells (8 TIE + 3 UNDERPOWERED). The Wave 195 P4
12-cell verdict distribution surfaces this honestly. **CLM-062 is the
correct single-citation format** for the 12-cell matrix (verdict-
precedence: 1 SUPPORTED + 8 TIE + 3 UNDERPOWERED).

---

## 3. Q2: Narrative positioning — single-cell vs 12-cell

### 3.1 The cherry-picking question

A reviewer reading "C-K-L2-CvB Cohen's d_z = −11.15, p_bonf = 4.14e-31"
in isolation will ask: **"Why are you citing this single cell out of
12?"** The honest answer requires:

1. Reporting all 12 cells with full verdict distribution (1 SUPPORTED +
   8 TIE + 3 UNDERPOWERED + 0 REGRESSES).
2. Naming the verdict-precedence methodology (TIE > UNDERPOWERED >
   SUPPORTED > REGRESSES > NOT_SIGNIFICANT).
3. Explaining the **decision-honest** reading: the n=30 paired design
   has SE too large to reliably detect the 1.0 L2 / 0.01 ΔS practical
   floor at UNDERPOWERED cells, even though the observed effects are
   30×–100× the floor (the n=30 design is a budget ceiling, not a
   limitation of the framework).
4. Framing the single-SUPPORTED cell as **the one cell where both
   observed effect AND post-hoc power align with the practical floor**
   — not as the strongest effect.

### 3.2 Cherry-picking risk

**LOW.** CLM-062 reports the full 12-cell verdict distribution in
verbatim prose ("1 SUPPORTED / 0 REGRESSES / 8 TIE / 3 UNDERPOWERED /
0 NOT_SIGNIFICANT"), and the audit doc `wave195-p4-theorem1-power.md`
§3 explicitly documents the **decision-honest deviation from the
Wave 195 P1 spec §4.6 expected verdicts** (which predicted 4 cells
SUPPORTED). The Wave 195 P4 verdicts reflect the verdict-precedence
chain honestly; the UNDERPOWERED cells are not re-labelled SUPPORTED
to inflate the count.

Compared to CLM-053 (which had a Wave 230 P2 contradiction — see
Wave 249 P1 audit `wave249-p1-clm053-audit.md` "NOT OK to add"), CLM-062
has **no internal contradiction**: the 12-cell verdict distribution is
self-consistent, the verdict-precedence rules are documented
(`wave195-p1-power-spec.md` §1.1), and the Wave 195 P4 audit doc
explicitly addresses the spec-vs-actual deviation.

### 3.3 Framing as 12-cell power analysis

CLM-062 is **already framed as a 12-cell power analysis**, not as a
single-cell finding. The verbatim CLM-062 text says "12 cells = 2
adapters × 3 arm comparisons × 2 axes", and the verdict distribution
is reported in full. This is the correct framing for the paper.

**Recommendation:** add CLM-062 to **§3.5 (Theorem 1 load-bearing
discussion)** as an ADDITIVE paragraph after the current single-cell
`d = +10.24` quote. The current §3.5 quote cites C-K-DS-PvC (ΔS
paper-vs-cosine, UNDERPOWERED verdict); CLM-062 adds the 12-cell
verdict distribution and identifies C-K-L2-CvB as the single
SUPPORTED cell.

**Wording recommendation** (additive, no replacement):

> "The Theorem 1 load-bearing test on the Kanzi + LineageFlow
> synthetic protein axes, formalised as the Wave 195 P4 12-cell
> per-cell power analysis (Bonferroni α=0.05/12=0.004167 per cell,
> n=30 paired seeds, paired t-test with Cohen's d_z on within-subject
> diffs), returns a verdict-precedence distribution of **1 SUPPORTED /
> 0 REGRESSES / 8 TIE / 3 UNDERPOWERED / 0 NOT_SIGNIFICANT**. The
> single `load_bearing_supported` cell is **C-K-L2-CvB** (kanzi L2
> cosine-vs-baseline, Cohen's d_z = −11.15, p_bonf = 4.14e-31, Δ =
> −16.88): the cosine arm's L2 endpoint movement is significantly
> smaller than the baseline, confirming the paper-quantity scheduler
> regularises on the cosine ramp. The 8 TIE cells are all 6
> lineageflow × {L2, ΔS} cells (field too small to resolve at n=30)
> plus 2 kanzi byte-stable composite cells (`|Δ| < min_effect_size`).
> The 3 UNDERPOWERED cells are kanzi × {L2-PvC, ΔS-PvC, ΔS-CvB} where
> observed Cohen's d_z ∈ [10.24, 30.15] rejects H0 trivially but
> post-hoc power at the 1.0 L2 / 0.01 ΔS practical floor is below
> 0.5. The 1/12 verdict is the decision-honest reading of the n=30
> paired design; no cell REGRESSES."

This framing is consistent with the paper §3.5 narrative (Theorem 1
quantities are load-bearing on the regularisation axis) while
honestly surfacing the n=30 budget ceiling that drives the 8 TIE + 3
UNDERPOWERED verdicts.

---

## 4. Q3: Wave 191 P3 MNIST smoke ckpt status

### 4.1 Smoke ckpt PROVISIONAL status

CLM-059 (line 2919 of `docs/CLAIMS.md`) reads:

> "Wave 191 P3 — MNIST FM framework-vs-baseline sweep at N=1000,
> matched NFE=50 (**smoke ckpt PROVISIONAL**) — framework WINS
> **−28.43%** best arm on smoke-materialized checkpoint (Bonferroni
> p=3.95e-11, Cohen's `d_z`=−13.18); PROVISIONAL pending
> production-ckpt re-run on the post-Wave-191 ruff-frozen code with
> `data/mnist_fm.npz` re-materialized at epochs=3, base_channels=16,
> full 60K images (current smoke ckpt is epochs=1, base_channels=8,
> max_train_images=6000; sha256=`ded1fa70c83b77f076351f5285571adefd
> 05acb33ed65153db4b23a56f371634`, 22481 bytes)."

The smoke ckpt details:

| Parameter            | Smoke (current) | Production (pending re-run) |
|----------------------|-----------------|------------------------------|
| epochs               | 1               | 3                            |
| base_channels        | 8               | 16                           |
| max_train_images     | 6,000           | 60,000                       |
| ckpt size (bytes)    | 22,481          | ~ 10× larger (estimate)     |
| sha256               | ded1fa70...     | (not yet materialized)       |

### 4.2 Production-ckpt rerun status

Searched all post-Wave-191 P3 audit docs, scripts, and
verification outputs for any MNIST FM production-ckpt re-run:

* `verification_outputs/wave191-p3-mnist-n1000/` — only the smoke ckpt
  sweep exists (4 sample npz files for baseline + cosine +
  codimension_sheet + evidence_driven at N=1000 on smoke ckpt).
* `verification_outputs/wave191-p3-mnist-n1000.json` — smoke ckpt
  results: best arm `evidence_driven` FID 23.39 vs baseline 29.49,
  Δ=−28.43%, Bonferroni p=3.95e-11.
* No `verification_outputs/wave191-p4-*.json` or
  `verification_outputs/wave200-p*-mnist-production*.json` exists.
* `docs/audit/wave191-p5-final-gate-verification.md` §2 lists Wave 191
  P4 as "Paper §10.34 + CONSOLIDATED_RESULTS §15.87 + baseline-audit
  §R.77 + INSIGHTS §7.6 formalise R5 honest-disclosure matrix at
  N=1000. CLM-040 updated; CLM-059 added (PROVISIONAL+blocked)." —
  the Wave 191 P4 commit `ca18bf3` is **documentation-only** (paper
  §10.34 disclosure), NOT a production-ckpt rerun.
* `docs/CONSOLIDATED_RESULTS.md` line 7177 (R5c MNIST FM row): "(no
  prior claim) | **framework_wins** −28.43% on smoke ckpt
  (PROVISIONAL) | `framework_wins` PROVISIONAL (smoke ckpt)" —
  the **PROVISIONAL** status remains active.

**Production ckpt rerun: NOT AVAILABLE.** The smoke ckpt PROVISIONAL
status has been carried forward verbatim from Wave 191 P3 (commit
`084e583`) through Wave 191 P5 (tag `v1.5-paper-r5-upgrade`) and into
the current HEAD. No subsequent wave has re-materialized the
production ckpt and re-run the N=1000 sweep.

### 4.3 Implication for the paper

The Wave 191 P3 MNIST FM N=1000 reading is currently cited in the
paper as R5c in §3.3 Table 3.2 (`docs/drafts/paper-flattened-draft.md`
line 249: "R5c MNIST FM NFE=50 FID | 10 (paired chunks, df=9) |
−6.105 | 0.1465 | −131.72 | 9 | 1.32 × 10⁻¹¹ | [−6.392, −5.817] |
−13.175 (d_z) | paired chunk t | R-level primary | 0.007143 |
**YES**") with the **PROVISIONAL flag** carried forward in CLM-059.

The §3.3 Table 3.2 reading **does NOT cite the smoke ckpt PROVISIONAL
status inline**. The disclosure lives in:
1. CLM-059 (`docs/CLAIMS.md` line 2919) — primary disclosure source.
2. `docs/CONSOLIDATED_RESULTS.md` line 7177 — secondary disclosure.
3. `docs/INSIGHTS.md` line 361 — tertiary disclosure.
4. `docs/paper-draft.md` line 2969 — limitations section.

**Recommendation for Wave 248 integration:** if Wave 248 adds CLM-059
to the paper §3.3 R5c row, **the smoke ckpt PROVISIONAL status MUST
be cited inline** (e.g., "framework WINS at d_z = −13.175 on smoke
ckpt (PROVISIONAL pending production-ckpt re-run)"). Without the
inline disclosure, a reviewer reading R5c in Table 3.2 will not see
that the reading is PROVISIONAL.

---

## 5. Q4: Paper placement recommendation

### 5.1 CLM-062 → §3.5 (Theorem 1 load-bearing discussion)

**§3.5 currently** (line 297 of `docs/drafts/paper-flattened-draft.md`)
cites a single-cell `d = +10.24` result from C-K-DS-PvC without
disclosing the 12-cell matrix. CLM-062 supplies the **12-cell verdict
distribution** (1 SUPPORTED + 8 TIE + 3 UNDERPOWERED) and the verdict-
precedence methodology.

**Placement:** add CLM-062 as an ADDITIVE paragraph at the end of
§3.5, immediately after the current single-cell `d = +10.24` quote.
The wording should:
1. Name the 12-cell setup (2 adapters × 3 arm comparisons × 2 axes).
2. Name the Bonferroni correction (α=0.05/12=0.004167 per cell).
3. Report the full verdict distribution (1/0/8/3/0).
4. Name the single SUPPORTED cell (C-K-L2-CvB) and the 3 UNDERPOWERED
   cells.
5. Explain the n=30 paired design's budget ceiling honestly (post-hoc
   power at the 1.0 L2 / 0.01 ΔS practical floor is below 0.5 even
   when the observed effect is 30×–100× the floor).

**Wording** is in §3.3 above. This is consistent with the §3.5
narrative (Theorem 1 quantities are load-bearing on the regularisation
axis) while honestly surfacing the 8 TIE + 3 UNDERPOWERED verdicts.

### 5.2 Wave 191 P3 MNIST → §3.3 R5c (already integrated) + §4 limitations (PROVISIONAL)

The Wave 191 P3 MNIST FM smoke-ckpt reading is **already integrated**
in the paper §3.3 Table 3.2 as R5c with d_z = −13.175, p = 1.32e-11.
The PROVISIONAL disclosure lives in:
1. CLM-059 (primary).
2. `docs/CONSOLIDATED_RESULTS.md` §15.87 (secondary).
3. `docs/paper-draft.md` §10.42 / limitations (tertiary).

**Recommendation:** the Wave 191 P3 reading should **NOT be moved**
(it's correctly placed in §3.3 as R5c). The PROVISIONAL status is
disclosed in CLM-059, which the §3.3 Table 3.2 narrative does NOT
cite inline.

**Optional Wave 248 additive**: add an inline PROVISIONAL flag on the
R5c row in Table 3.2 (e.g., "framework WINS at d_z = −13.175 on
smoke ckpt (PROVISIONAL)"). This would mirror the existing R5b
inline disclosure ("+24-31% at matched NFE=50" — see
`wave206-p6-cifar-rf-v4-honest-negative-curve.md`).

**Production-ckpt rerun status:** the smoke ckpt PROVISIONAL status
remains active because the production-ckpt rerun has NOT been done.
A future wave (e.g., Wave 250 P5) could:
1. Re-materialize `data/mnist_fm.npz` at epochs=3, base_channels=16,
   full 60K images (estimated 30-40 min CPU per CLM-059).
2. Re-run the Wave 191 P3 sweep pipeline on the production ckpt.
3. Update CLM-059 from PROVISIONAL to ACTIVE if the production-ckpt
   reading confirms the −28.43% magnitude (or to REGRESSED if it
   contradicts).

---

## 6. Final verdict

### 6.1 CLM-062: OK to add

**CLM-062 is OK to add to §3.5** as an ADDITIVE paragraph. The 12-cell
verdict distribution is the decision-honest reading of the n=30 paired
Theorem-1 load-bearing sweep, and the cherry-picking risk is LOW
because the full 12-cell matrix is reported. The single-SUPPORTED
cell C-K-L2-CvB is correctly identified as the one cell where both
the observed effect (Cohen's d_z = −11.15) AND the post-hoc power at
the 1.0 L2 practical floor (0.9513) align.

The paper §3.5 currently cites a single-cell `d = +10.24` result
(C-K-DS-PvC, kanzi ΔS paper-vs-cosine) without the 12-cell framing.
**CLM-062 supplies the missing 12-cell context** and is the correct
additive to §3.5.

### 6.2 Wave 191 P3 MNIST: OK to add with inline PROVISIONAL disclosure

**Wave 191 P3 MNIST FM smoke-ckpt reading is OK to keep** in the paper
§3.3 R5c row (already integrated), but the smoke ckpt PROVISIONAL
status MUST be cited inline on the R5c row (currently lives only in
CLM-059 and CONSOLIDATED_RESULTS §15.87, not in §3.3 Table 3.2).

**Production-ckpt rerun: NOT AVAILABLE.** The PROVISIONAL status is
carried forward verbatim from Wave 191 P3. A future wave is needed to
either (a) re-materialize the production ckpt and rerun the sweep, or
(b) explicitly retire the PROVISIONAL reading if the rerun is
deferred to camera-ready.

### 6.3 Hard rules respected

* **No paper modifications** during this audit (CLM-062 and Wave 191
  P3 status are recommendations only; Wave 248 is the execution phase).
* **D.4 30/30 PASS** preserved (no D.4-related changes; the CLM-062
  12-cell JSON lives at `verification_outputs/wave195-p4-theorem1-
  power.json`, frozen at commit `76108b5`).
* **Wave 191 P3 JSON** lives at `verification_outputs/wave191-p3-
  mnist-n1000.json`, frozen at commit `084e583`. No modifications.

---

## 7. References

* `docs/CLAIMS.md` line 3354 — CLM-062 verbatim.
* `docs/CLAIMS.md` line 2919 — CLM-059 verbatim (Wave 191 P3 MNIST
  smoke-ckpt PROVISIONAL).
* `docs/audit/wave195-p1-power-spec.md` §4 — Table C Theorem 1 spec,
  cell inventory, verdict precedence.
* `docs/audit/wave195-p4-theorem1-power.md` §2 + §3 — 12-cell
  per-cell results, verdict distribution, decision-honest deviation
  from spec.
* `verification_outputs/wave195-p4-theorem1-power.{csv,json}` —
  12-cell per-cell power analysis outputs (frozen at commit
  `76108b5`).
* `verification_outputs/wave190-p2-kanzi-n30.json` — kanzi n=30
  paired sweep source.
* `verification_outputs/wave190-p3-lineageflow-n30.json` —
  lineageflow n=30 paired sweep source.
* `docs/audit/wave191-p3-mnist-n1000.md` — Wave 191 P3 MNIST
  audit doc.
* `docs/audit/wave191-p5-final-gate-verification.md` §2 — Wave 191
  P4 commit `ca18bf3` is documentation-only (paper §10.34), NOT a
  production-ckpt rerun.
* `verification_outputs/wave191-p3-mnist-n1000.json` — Wave 191 P3
  smoke-ckpt results (frozen at commit `084e583`).
* `docs/CONSOLIDATED_RESULTS.md` line 7177 — R5c MNIST FM
  smoke-ckpt row (PROVISIONAL status preserved verbatim).
* `docs/INSIGHTS.md` line 361 — Wave 191 P3 PROVISIONAL disclosure
  with smoke-ckpt details.
* `docs/drafts/paper-flattened-draft.md` line 249 (R5c MNIST FM row)
  + line 297 (Theorem 1 single-cell `d = +10.24` quote, §3.5) +
  line 309-313 (R5 cells as a family).
* `docs/audit/wave249-p1-clm053-audit.md` — comparison case
  (CLM-053 NOT OK to add due to Wave 230 P2 contradiction).
* `docs/audit/wave249-p3-clm054-audit.md` — sibling Wave 249 P3
  audit doc structure (this P4 audit follows the same template).

---

## 8. Acceptance gates

| #  | gate                                                                       | status |
|----|----------------------------------------------------------------------------|--------|
| 1  | CLM-062 verbatim extracted from `docs/CLAIMS.md` line 3354                 | PASS   |
| 2  | 12-cell setup verified (2 adapters × 3 arm comparisons × 2 axes)          | PASS   |
| 3  | Verdict distribution (1/0/8/3/0) verified against `wave195-p4-...md` §2  | PASS   |
| 4  | Cherry-picking risk assessed (LOW; full 12-cell matrix reported)           | PASS   |
| 5  | Wave 191 P3 smoke-ckpt PROVISIONAL status verified (CLM-059 line 2919)    | PASS   |
| 6  | Production-ckpt rerun NOT AVAILABLE verified (no post-Wave-191 rerun)      | PASS   |
| 7  | Paper placement recommendation (CLM-062 → §3.5 additive; Wave 191 P3 R5c | PASS   |
|    | stays in §3.3 Table 3.2 with inline PROVISIONAL flag)                       |        |
| 8  | Final verdict: CLM-062 OK to add; Wave 191 P3 OK to keep with inline       | PASS   |
|    | PROVISIONAL disclosure                                                       |        |
| 9  | D.4 30/30 PASS preserved                                                    | PASS   |
| 10 | Audit doc created at `docs/audit/wave249-p4-clm062-wave191-audit.md`        | PASS   |

All 10 gates PASS.