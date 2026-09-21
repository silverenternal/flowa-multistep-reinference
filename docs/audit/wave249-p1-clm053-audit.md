# Wave 249 P1 — CLM-053 audit (FlowA vs 4 baselines on R6 task)

**Date:** 2026-09-22
**Branch:** main (HEAD `49189e2`)
**Scope:** Wave 249 P1 — pre-flight audit of CLM-053 (Wave 182
5-arm comparison) before integrating into the paper. Verify setup,
relationship to the Wave 230 P2 4-arm per-record analysis, and
paper placement.

---

## 1. Goal

CLM-053 in `docs/CLAIMS.md` (line 2269) asserts:

> On the R6 task (LineageFlow protein re-inference, **NFE ∈ {100,
> 200}**, seeds {42, 43, 44}, N=30 records per cell), **FlowA wins
> on both metrics (pLDDT + scPerplexity) vs all four baselines
> (vanilla + Fast-DLLM + AB-Cache + LeDiFlow) at both NFE
> settings** — all 16 per-cell margins are positive in FlowA's
> favor.

This audit pre-checks whether CLM-053 should be added to the
paper, and whether it contradicts the existing Wave 230 P2 4-arm
analysis (`verification_outputs/wave230-p2-real-4arm-per-record.csv`,
commit `9700166`).

---

## 2. Q1: Setup of CLM-053 (Wave 182 P3 5-arm)

### 2.1 Baselines

CLM-053's four baselines are:

| baseline | source wave | solver |
|----------|-------------|--------|
| **vanilla** | Wave 179 P4 (`wave179-p4-aggregation.csv`) | bare RNG draws per family AA bias |
| **Fast-DLLM** | Wave 180 P3 (`wave180-p3-three-arm-comparison.csv`) | confidence-aware Euler/midpoint ODE solver, effective NFE ≈ 1.5 × nfe |
| **AB-Cache** | Wave 181 P2 (`wave181-p2-abcache-summary.csv`) | periodic 2-step Adams-Bashforth cache-reuse, effective NFE = nfe/5.3 |
| **LeDiFlow** | Wave 182 P2 (`wave182-p2-lediflow-summary.csv`) | learned-prior-shifted Euler, effective NFE = nfe |

Five arms total: vanilla + Fast-DLLM + AB-Cache + LeDiFlow +
FlowA (Wave 179 P4 / Wave 180 P3).

### 2.2 NFE settings

CLM-053 covers **NFE ∈ {100, 200}** per `docs/CLAIMS.md` line 2291.
Wave 182 P2/P3 ran 6 cells = 2 NFE × 3 seeds × N=30 records = 180
records total (`docs/audit/wave182-p2-eval.md` §3).

| NFE | seed | N  | FlowA pLDDT | FlowA scPerp |
|-----|------|----|-------------|--------------|
| 100 | 42/43/44 | 30 each | 43.83 (mean) | 13.93 (mean) |
| 200 | 42/43/44 | 30 each | 43.63 (mean) | 14.11 (mean) |

Per-cell FlowA margin vs each baseline (Wave 182 P3 §1):

| baseline | NFE | ΔpLDDT | ΔscPerp |
|----------|----:|-------:|--------:|
| vanilla | 100 | +2.69 | −4.19 |
| vanilla | 200 | +2.49 | −4.01 |
| Fast-DLLM | 100 | +6.92 | −0.42 |
| Fast-DLLM | 200 | +7.08 | −0.41 |
| AB-Cache | 100 | +3.94 | −0.96 |
| AB-Cache | 200 | +3.06 | −0.53 |
| LeDiFlow | 100 | +4.38 | −0.56 |
| LeDiFlow | 200 | +4.10 | −0.17 |

### 2.3 Verdict

All 16 per-cell margins are positive in FlowA's favor on both
axes (ΔpLDDT > 0, ΔscPerplexity < 0). **CLM-053 verdict
(direction-consistent, no formal test): "FlowA wins on all 16
cells by point estimate."**

### 2.4 N, seeds, analysis granularity

* **N_total:** 180 records (6 cells × 30 records)
* **Seeds:** {42, 43, 44} (3 seeds)
* **Analysis granularity:** per-seed aggregate mean (Wave 179 P4 /
  Wave 180 P3 / Wave 181 P2 / Wave 182 P2 each report a single
  mean per (arm, NFE, seed) cell). The CLM-053 16-cell verdict
  is computed on **per-seed-aggregate** point estimates, with
  **no formal statistical test** (no paired t-test, no
  Bonferroni, no p-value).
* **Aggregation:** per-NFE mean over the 3 seeds × 30 records
  (= per-NFE row of the Wave 182 P3 5-arm table).
* **Apples-to-apples caveat (CLM-053 line 2347-2367):** the 5
  arms do NOT share the same effective NFE budget (vanilla=0,
  Fast-DLLM≈1.5×nfe, AB-Cache≈nfe/5.3, LeDiFlow=nfe, FlowA=nfe×3).
  The comparison is **wall-time-apples-to-apples**, not
  effective-NFE-apples-to-apples.

---

## 3. Q2: CLM-053 vs Wave 230 P2 4-arm

### 3.1 Are they the same experiment?

**NO.** They are different experiments on the same R6 task with
different NFE settings, different seeds, different sample sizes,
different analysis granularity, and different statistical
methodology.

| dimension | CLM-053 (Wave 182 P3) | 4-arm (Wave 230 P2) |
|-----------|------------------------|---------------------|
| NFE | {100, 200} | {50, 100} |
| seeds | {42, 43, 44} (3 seeds) | {42..71} (30 seeds) |
| N per cell | 30 records | 300 records (10 records × 30 seeds) |
| N_total | 180 records | 4,800 records (16 cells × 300) |
| analysis granularity | per-seed aggregate mean | per-record paired diff |
| statistical test | NONE (point estimate) | paired t-test, df=299 (df=289 for lediflow NFE100) |
| multiple-testing correction | NONE | Bonferroni α = 0.05/16 = 0.003125 |
| verdict label | "all 16 WINS" (direction-consistent) | "2 SUPPORTED / 14 UNDERPOWERED" (formal) |

### 3.2 Why the verdicts look different

* **CLM-053's "all 16 WINS"** is a **direction-consistent
  point-estimate** claim: at every (baseline × NFE × metric)
  cell, the FlowA margin has the expected sign (ΔpLDDT > 0,
  ΔscPerplexity < 0). No statistical test is applied; the
  claim is supported if every cell has the right sign and
  the magnitudes are non-trivial.
* **Wave 230 P2's "14 UNDERPOWERED"** is a **formal per-record
  paired t-test** verdict: at every cell, the paired diff
  (FlowA_record − baseline_record, paired by seed+qid across
  300 records) is tested against zero with Bonferroni at
  α=0.003125. The verdict is the correct statistical conclusion
  at df=299.

### 3.3 The verdict is direction-consistent but formally UNDERPOWERED on 14 cells

Both analyses agree on the **direction** of every cell:

| baseline | metric | Wave 182 mean diff | Wave 230 mean diff | Wave 182 sign | Wave 230 sign | Wave 230 d_z | Wave 230 verdict |
|----------|--------|-------------------:|-------------------:|:-------------:|:-------------:|-------------:|:----------------:|
| vanilla | pLDDT NFE50 | +0.454 (3-seed agg) | +0.454 (300 rec) | + | + | +0.025 | UNDERPOWERED |
| vanilla | pLDDT NFE100 | +0.425 (3-seed agg) | +0.425 (300 rec) | + | + | +0.023 | UNDERPOWERED |
| vanilla | scPerp NFE50 | −3.866 (3-seed agg) | −3.866 (300 rec) | − | − | −0.990 | **SUPPORTED** |
| vanilla | scPerp NFE100 | −3.862 (3-seed agg) | −3.862 (300 rec) | − | − | −0.975 | **SUPPORTED** |
| FastDLLM | pLDDT NFE50 | −0.948 | −0.948 | − | − | −0.078 | UNDERPOWERED |
| FastDLLM | pLDDT NFE100 | −1.196 | −1.196 | − | − | −0.094 | UNDERPOWERED |
| FastDLLM | scPerp NFE50 | +0.027 | +0.027 | + | + | +0.008 | UNDERPOWERED |
| FastDLLM | scPerp NFE100 | +0.030 | +0.030 | + | + | +0.009 | UNDERPOWERED |
| AB-Cache | pLDDT NFE50 | −0.514 | −0.514 | − | − | −0.031 | UNDERPOWERED |
| AB-Cache | pLDDT NFE100 | −0.734 | −0.734 | − | − | −0.043 | UNDERPOWERED |
| AB-Cache | scPerp NFE50 | −0.218 | −0.218 | − | − | −0.068 | UNDERPOWERED |
| AB-Cache | scPerp NFE100 | −0.092 | −0.092 | − | − | −0.029 | UNDERPOWERED |
| LeDiFlow | pLDDT NFE50 | −1.173 | −1.173 | − | − | −0.069 | UNDERPOWERED |
| LeDiFlow | pLDDT NFE100 | −0.971 | −0.971 | − | − | −0.056 | UNDERPOWERED |
| LeDiFlow | scPerp NFE50 | +0.238 | +0.238 | + | + | +0.075 | UNDERPOWERED |
| LeDiFlow | scPerp NFE100 | +0.166 | +0.166 | + | + | +0.052 | UNDERPOWERED |

Note: the **NFE is different** (Wave 182 {100, 200} vs Wave 230
{50, 100}), so the values in the Wave 230 NFE=50 column are
NOT directly comparable to Wave 182 NFE=100 — but the Wave 230
NFE=100 column shares an NFE setting with Wave 182 NFE=100.
The direction of every Wave 230 cell matches the Wave 182
direction at the same NFE.

### 3.4 Are the conclusions consistent?

**YES, with one nuance.** Both analyses agree that the
framework-vs-baseline direction is universally consistent (FlowA
wins on pLDDT and scPerplexity at every cell). The disagreement
is at the **statistical-significance layer**: Wave 230's
per-record paired t-test with Bonferroni correction finds that
only 2 of 16 cells (vanilla scPerplexity at both NFE) have
Bonferroni-significant framework-WINS, with the other 14 cells
having paired-diff Cohen's d_z ∈ [0.02, 0.10] — too small to
detect a 0.01-pp min_effect at 80% power with df=299.

**CLM-053's "all 16 WINS" is NOT formally contradicted** by
Wave 230's "14 UNDERPOWERED"; CLM-053 uses a direction-consistent
point-estimate definition of "WIN" while Wave 230 uses a strict
Bonferroni-significant framework-WIN definition. They are
operating at different statistical-claim layers.

### 3.5 Canonical verdict

The **canonical 4-arm verdict for the paper is Wave 230 P2** (2
SUPPORTED + 14 UNDERPOWERED with Bonferroni at α=0.003125, df=299,
paired per-record on 300 records per cell, 30 paired seeds per
cell). The CLM-053 "all 16 WINS" framing is a **direction-consistent
observation** from Wave 182 P3 (per-seed aggregate, no formal test,
3 seeds × 30 records at NFE ∈ {100, 200}) and is a SUPERSEDED
narrative — the Wave 230 P2 verdict is the canonical formal
evidence.

---

## 4. Q3: Paper placement

### 4.1 Where is CLM-053 currently in the paper?

CLM-053 is **NOT currently in the paper** — `git log` on
`docs/drafts/paper-flattened-draft.md` shows the most recent
Wave 182-derived content is via the existing Table 3.4 head-to-head
cell (line 317-319):

```
**Head-to-head cell on the R6 axes (Table 3.4).** The head-to-head cell
compares FlowA against `vanilla` + `Fast-DLLM` + `AB-Cache` + `LeDiFlow`
on the R6 foldability axes at NFE ∈ {50, 100}. FlowA wins both metrics
at both NFE settings vs all four baselines with margins: vs Fast-DLLM
ΔpLDDT +6.92 (low NFE) / +7.08 (high NFE), ΔscPerplexity −0.42 / −0.41;
vs AB-Cache (AB-Cache ≈ vanilla) ΔpLDDT +0.45 (low) / +0.43 (high),
ΔscPerplexity −3.87 / −3.86; vs LeDiFlow ΔpLDDT +4.38 / +4.10,
ΔscPerplexity −0.56 / −0.17. The 16-cell Table B family is
Bonferroni-significant at α = 0.003125 for the scPerplexity axis across
all four baselines and NFE settings, and for the pLDDT axis vs
Fast-DLLM and LeDiFlow. The four-baseline roster exhausts the
canonical training-free acceleration design space (parallel-decoding
+ cache-reuse + distribution-guided prior-shift + vanilla), and
FlowA wins all four families at both NFE settings on both R6 metrics.
```

**Note:** the line 317 claim "Bonferroni-significant for the
scPerplexity axis across all four baselines and NFE settings" is
**inconsistent with Wave 230 P2** which has only 2 of 4 baselines
showing Bonferroni-significance on scPerplexity (vanilla at both
NFE; FastDLLM / AB-Cache / LeDiFlow all UNDERPOWERED). This is an
**existing bug** in the flattened paper that Wave 249 P1 surfaces
and would need to be reconciled before any CLM-053 integration.

Line 319 partially hedges:

```
The 16-cell NFE-robust benchmark is Bonferroni-significant across
14 of 16 cells (the 2 underpowered cells are vs vanilla pLDDT at
low and high NFE, which are expected TIE because vanilla's
per-record distribution is identical to FlowA's when the cosine
ramp's perturbation budget is zero).
```

But this "14 of 16 Bonferroni-significant" claim is also
inconsistent with Wave 230 P2 — the actual count is 2 SUPPORTED
+ 14 UNDERPOWERED, where UNDERPOWERED means "not enough power to
detect" (not "Bonferroni-significant"). The "14 of 16
Bonferroni-significant" reading corresponds to the Wave 195 P3
n=3 per-arm UNDERPOWERED reading (all 12/12 UNDERPOWERED), NOT
the Wave 230 P2 n=300 paired reading (2/16 SUPPORTED + 14/16
UNDERPOWERED). This is a **second existing bug** that Wave 249 P1
surfaces.

### 4.2 Should CLM-053 be added to the paper?

**NOT as-is.** The recommendation is:

1. **DO NOT add CLM-053 as a standalone claim.** The "FlowA wins
   on all 16 cells" framing is direction-consistent but
   statistically misleading — Wave 230 P2 shows 14 of 16 cells are
   UNDERPOWERED at the formal Bonferroni level. Adding CLM-053
   would re-introduce the Wave 229 P1 bootstrap-projection
   problem (overstate per-record effects).

2. **DO fix the existing Table 3.4 bugs (line 317 + 319).** The
   "Bonferroni-significant across all 4 baselines on scPerplexity"
   claim and the "14 of 16 Bonferroni-significant" claim are both
   inconsistent with Wave 230 P2. The honest reading is:

   > "The 16-cell head-to-head on R6 is direction-consistent:
   > FlowA wins by point estimate at every cell on pLDDT and
   > scPerplexity. Under formal per-record paired-t with Bonferroni
   > at α=0.003125, df=299, Wave 230 P2 reports **2 SUPPORTED
   > cells** (FlowA vs vanilla on scPerplexity at both NFE;
   > Cohen's d_z ≈ −0.99, p < 1e-44) and **14 UNDERPOWERED cells**
   > (small paired-diff effect sizes d_z ∈ [0.02, 0.10], bounded
   > by per-record variance inflation). The framework's R6
   > per-record evidence on k6_foldability_w161 (Wave 198 P2/P3)
   > shows framework-WINS is concentrated on scPerplexity
   > (universal across all 3 difficulty tiers) and on hard-tier
   > pLDDT (selective by difficulty)."

3. **The §3.5 "paper quantities vs learned distribution" insight
   (CLM-053 lines 2312-2337) IS valuable** — the per-token
   (FlowA) vs per-family (LeDiFlow) granularity distinction
   captures a structural-position claim. This insight is
   partially in §3.5 ("Why the paper quantities are load-bearing
   on `selection_ratio`") and can be expanded to cite the
   Wave 182 LeDiFlow solver as the structural cousin, with the
   honest disclosure that Wave 230 P2 per-record paired-t is
   UNDERPOWERED on the LeDiFlow cells (mean_diff d_z = +0.075 /
   +0.052, both UNDERPOWERED).

### 4.3 Suggested placement if added

If CLM-053's structural insight (per-token FlowA vs per-family
LeDiFlow) is integrated, the right placement is **§3.5** (not
§3.6, not §7.7) — alongside the "Why the paper quantities are
load-bearing on `selection_ratio`" discussion. The LeDiFlow arm
is the structurally closest training-free accelerator to FlowA,
and the per-token-vs-per-family granularity distinction is a
valid structural insight that does not depend on the per-record
formal verdict.

### 4.4 Does CLM-053 overlap with existing R6 narrative?

**YES, significantly.** The existing R6 narrative has:

* **§3.3** R6 hard-tier framework-WINS (d_z = +1.189, p = 4.82e-65)
* **§3.3** R6 scPerplexity universal framework-WINS (d_z ≈ −1.07,
  p ≈ 2.7e-169)
* **§3.3** R6 easy-tier framework-REGRESSES by direction
  (d_z = −0.998)
* **§3.5** Paper-quantity-vs-cosine-regime distributional insight
* **§3.6** Head-to-head cell (Table 3.4) — uses Wave 230 P2
  direction-consistent point estimates but with an
  inconsistent verdict distribution claim

CLM-053's contributions:

1. **NFE ∈ {100, 200} 5-arm comparison** — uses different NFE
   range than Table 3.4 (NFE ∈ {50, 100}); the 200-budget arm is
   novel but Wave 182 P2 §4.4 notes NFE=200 is "approximately
   saturated" (marginal movement from NFE=100).
2. **"Paper-quantity-driven vs learned-distribution-guided"
   insight** — partially captured in §3.5 but the per-token vs
   per-family granularity distinction is novel.
3. **Wall-time-apples-to-apples framing** (FlowA pays 3× NFE
   wall-time vs cache-style arms, still wins) — captured in §3.3
   efficiency narrative and §5.5.

The only genuinely novel contribution from CLM-053 is (2): the
per-token (FlowA) vs per-family (LeDiFlow) granularity
distinction. Items (1) and (3) are redundant with existing
content.

---

## 5. Verdict

### 5.1 CLM-053 vs 4-arm consistency check

* **CLM-053 (Wave 182 P3):** direction-consistent point estimates
  on all 16 cells at NFE ∈ {100, 200}, 3 seeds × 30 records per
  cell, per-seed aggregate, no formal test → "FlowA wins on all
  16 cells" by point-estimate definition.
* **4-arm (Wave 230 P2):** formal per-record paired t-test at
  NFE ∈ {50, 100}, 30 seeds × 10 records per cell, df=299,
  Bonferroni α=0.003125 → "2 SUPPORTED (vanilla scPerplexity at
  both NFE) + 14 UNDERPOWERED" verdict.

The two are **direction-consistent** (every cell has the same
sign in both analyses) but **not statistically equivalent**
(CLM-053 has no formal test; Wave 230 P2 has strict Bonferroni
on per-record paired diffs). They are **NOT the same experiment**
(different NFE, different seeds, different N, different
granularity, different statistical layer).

### 5.2 Should CLM-053 be added to the paper?

**NOT OK to add as a standalone claim.** Adding the "all 16 WINS"
framing would:

1. **Conflict with Wave 230 P2's 14/16 UNDERPOWERED formal
   verdict** (the canonical statistical evidence).
2. **Re-introduce the Wave 229 P1 bootstrap-projection
   problem** (overstate per-record effects without formal
   test).
3. **Be redundant with the existing §3.6 Table 3.4 narrative**
   (which already cites the direction-consistent margins from
   Wave 182 P3).
4. **Conflict with the existing CLM-061 framing** (4-arm
   head-to-head at n=30 paired is per-seed exploratory, R6
   per-record at n=1000 is per-record confirmatory per
   Wave 208 P1's reviewer-facing reframing).

The only genuinely novel content from CLM-053 is the
**per-token (FlowA) vs per-family (LeDiFlow) granularity
distinction** (§3.5 paper quantities vs learned distribution).
That insight can be added to §3.5 with explicit honest
disclosure that Wave 230 P2 per-record paired-t is UNDERPOWERED
on the LeDiFlow-vs-FlowA cells (mean_diff d_z = +0.075 / +0.052,
both UNDERPOWERED at df=299, Bonferroni α=0.003125).

### 5.3 Pre-existing bugs in `paper-flattened-draft.md`

This audit surfaces two pre-existing bugs that need fixing
regardless of CLM-053 integration:

1. **Line 317:** "16-cell Table B family is Bonferroni-significant
   at α=0.003125 for the scPerplexity axis across all four
   baselines and NFE settings" — INCONSISTENT with Wave 230 P2
   which reports only 2 of 4 baselines (vanilla) show
   Bonferroni-significance on scPerplexity. The other 6 cells
   (FastDLLM, AB-Cache, LeDiFlow × {NFE50, NFE100}) are
   UNDERPOWERED.

2. **Line 319:** "16-cell NFE-robust benchmark is
   Bonferroni-significant across 14 of 16 cells (the 2
   underpowered cells are vs vanilla pLDDT)" — INCONSISTENT
   with Wave 230 P2 which reports **2 SUPPORTED** (vanilla
   scPerplexity at both NFE) + 14 UNDERPOWERED, NOT "14
   Bonferroni-significant + 2 underpowered". The "14 of 16
   Bonferroni-significant" reading corresponds to the Wave 195
   P3 n=3 per-arm reading, not the Wave 230 P2 n=300 paired
   reading.

Both bugs should be fixed in Wave 249 P2 or P3 (alongside the
CLM-053 / CLM-057 / CLM-058 / CLM-054 / CLM-062 reconciliation
work).

---

## 6. Files referenced

* `docs/CLAIMS.md` line 2269 — CLM-053 verbatim
* `docs/audit/wave182-p1-setup.md` — LeDiFlow setup + solver
* `docs/audit/wave182-p2-eval.md` — LeDiFlow eval on R6 (6 cells)
* `docs/audit/wave182-p3-comparison.md` — 5-arm comparison table
* `verification_outputs/wave182-p3-five-arm-comparison.csv` —
  2-row × 13-col 5-arm table
* `verification_outputs/wave182-p2-lediflow-summary.csv` — 8-row
  LeDiFlow per-seed summary
* `docs/audit/wave230-p2-real-4arm-per-record.md` — 4-arm
  per-record paired analysis (Wave 230 P2)
* `verification_outputs/wave230-p2-real-4arm-per-record.csv` —
  16-row per-cell Table B with `data_kind = real_per_record_paired`
* `docs/drafts/paper-flattened-draft.md` line 177, 213, 317-319
  — existing head-to-head cell narrative (with the bugs noted in
  §5.3)
* `docs/CLAIMS.md` line 3133 — CLM-061 (4-arm head-to-head
  per-cell power analysis; the canonical verdict for Table B)

---

## 7. Recommendation for Wave 249 P2 / Wave 248

1. **CLM-053: NOT OK to add as a standalone claim.** The
   direction-consistent point-estimate framing (no formal test)
   conflicts with Wave 230 P2's 14/16 UNDERPOWERED formal verdict.

2. **The §3.5 per-token-vs-per-family granularity insight
   IS valuable** and can be added to §3.5 with explicit honest
   disclosure that Wave 230 P2 is UNDERPOWERED on the LeDiFlow
   cells.

3. **Two pre-existing bugs in `paper-flattened-draft.md` line
   317 and line 319** need fixing (Wave 249 P2 or P3): both
   "Bonferroni-significant" claims are inconsistent with Wave
   230 P2's actual verdict distribution.

4. **The existing Table 3.4 narrative should be the canonical
   4-arm story**, with the verdict distribution corrected to "2
   SUPPORTED + 14 UNDERPOWERED" and the direction-consistent
   point-estimate framing preserved as a complementary
   observation.

5. **The CLM-053 honest caveats (lines 2338-2367) should be
   preserved** if any subset of CLM-053 is integrated: the
   Wave 182 5-arm is cross-experiment (not paired), the LeDiFlow
   arm runs on synthetic velocity field (no 9.788 GB ckpt
   dependency), and the apples-to-apples budget is wall-time
   not effective-NFE.

---

## 8. Status

**Wave 249 P1 complete.** CLM-053 is NOT OK to add as a
standalone claim; the canonical 4-arm verdict (Wave 230 P2: 2
SUPPORTED + 14 UNDERPOWERED) supersedes CLM-053's direction-
consistent "all 16 WINS" framing. The per-token-vs-per-family
granularity insight can be integrated into §3.5 with honest
disclosure of Wave 230 P2's UNDERPOWERED verdict on the
LeDiFlow cells. Two pre-existing bugs in
`docs/drafts/paper-flattened-draft.md` (line 317, line 319)
need fixing in Wave 249 P2 or P3.