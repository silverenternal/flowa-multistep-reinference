# Wave 251 P1 — CLM-053 NOT_OK formal decision document

**Date:** 2026-09-22
**Branch:** main
**Scope:** Wave 251 P1 — formal single-document decision trail formalising
the Wave 249 P1 audit conclusion that CLM-053 is **NOT_OK to add** to the
TNNLS submission paper.

---

## Decision

**CLM-053 is NOT added to the TNNLS submission paper.**

## Decision-maker

**Wave 249 P1 audit** (`docs/audit/wave249-p1-clm053-audit.md`, dated
2026-09-22) — pre-flight audit produced as the 4th-pass pre-check by the
DeepSeek 2026-09-22 review cycle. The Wave 249 P1 audit was conducted
specifically to confirm or refute whether CLM-053 should be integrated
alongside the other Wave 250 additions (CLM-054, CLM-057, CLM-058,
CLM-062, Wave 191 P3 PROVISIONAL flag).

## Decision date

**2026-09-22** (same date as the Wave 249 P1 audit; this Wave 251 P1 doc
formalises the audit's conclusion into a single decision trail).

## Decision rationale (verbatim from Wave 249 P1 audit)

The following three quotes are the Wave 249 P1 audit's verbatim rationale
for the NOT_OK verdict, sourced from
`docs/audit/wave249-p1-clm053-audit.md`:

> 1. "CLM-053 (Wave 182 P3) and Wave 230 P2 4-arm are **NOT the same
>    experiment**: different NFE ({100,200} vs {50,100}), seeds ({42,43,44}
>    3 seeds vs {42..71} 30 seeds), N (90 vs 300 records per arm/NFE), and
>    granularity (per-seed aggregate vs per-record paired)."

> 2. "They are **direction-consistent on every cell** but **statistically
>    differ**: CLM-053 reports 'all 16 WINS' as direction-consistent point
>    estimates with no formal test; Wave 230 P2 reports **2 SUPPORTED**
>    (vanilla scPerplexity at both NFE, d_z ≈ −0.99, p < 1e-44) + **14
>    UNDERPOWERED** (paired-diff d_z ∈ [0.02, 0.10], too small for
>    0.01-pp min_effect at df=299 with Bonferroni α=0.003125)."

> 3. "CLM-053 **NOT OK to add as a standalone claim** — would re-introduce
>    the Wave 229 P1 bootstrap-projection problem and conflict with the
>    canonical Wave 230 P2 verdict."

### Why these three points force NOT_OK

| dimension | CLM-053 (Wave 182 P3) | Wave 230 P2 4-arm (canonical) | consequence |
|-----------|------------------------|-------------------------------|-------------|
| NFE | {100, 200} | {50, 100} | **different NFE settings** — not directly substitutable |
| seeds | {42, 43, 44} (3 seeds) | {42..71} (30 seeds) | **different sample population** — Wave 230 P2 has 10× more seeds |
| N per cell | 30 records | 300 records | **10× more records per cell** — Wave 230 P2 has 10× more statistical power |
| N_total | 180 records | 4,800 records (16 cells × 300) | **27× more total records** |
| analysis granularity | per-seed aggregate mean | per-record paired diff | **different statistical layer** — CLM-053 aggregates before testing |
| statistical test | NONE (point estimate) | paired t-test, df=299 | **no formal test in CLM-053** — point estimate only |
| multiple-testing correction | NONE | Bonferroni α = 0.05/16 = 0.003125 | **CLM-053 ignores multi-testing** — Wave 230 P2 corrects for 16 cells |
| verdict label | "all 16 WINS" (direction-consistent) | "2 SUPPORTED / 14 UNDERPOWERED" (formal) | **opposite statistical layers** — direction vs significance |

**Bottom line.** CLM-053's "all 16 WINS" framing is a direction-consistent
point-estimate observation from a 3-seed × 30-record per-cell aggregate
(N_total = 180 records). Wave 230 P2's "2 SUPPORTED + 14 UNDERPOWERED"
verdict is a formal per-record paired t-test with Bonferroni correction
from a 30-seed × 10-record per-cell paired experiment (N_total = 4,800
records, df=299 per cell, α=0.003125). They are **direction-consistent
but statistically non-equivalent**: every cell has the same sign in both
analyses, but CLM-053's "WIN" requires only a non-trivial point-estimate
margin (no formal test), while Wave 230 P2's "SUPPORTED" requires
Bonferroni-significance at α=0.003125 with df=299.

If CLM-053 were added as a standalone claim alongside Wave 230 P2, the
reader would see two contradictory verdict distributions on the same 4
arms × 2 NFE × 2 metrics = 16 cells:

* CLM-053 would say "16/16 WINS"
* Wave 230 P2 would say "2/16 SUPPORTED + 14/16 UNDERPOWERED"

This contradiction would re-introduce the Wave 229 P1 bootstrap-projection
problem (overstate per-record effects without formal test) and undermine
the canonical Wave 230 P2 verdict-precedence distribution that the paper
currently reports as the formal evidence.

---

## Honest disclosure (per Wave 249 P1 audit §5.2)

> "Only the per-token FlowA vs per-family LeDiFlow granularity
> distinction from CLM-053 has potential novelty value, but the Wave 230
> P2 verdict-precedence distribution (2 SUPPORTED + 14 UNDERPOWERED) on
> the 4-arm axis is canonical and supersedes CLM-053. The granularity
> distinction can be added to §3.5 with explicit disclosure that Wave 230
> P2 per-record paired-t is **UNDERPOWERED on the LeDiFlow cells**
> (d_z = +0.075/+0.052)."

The per-token (FlowA) vs per-family (LeDiFlow) granularity distinction
captures a structural-position claim about why FlowA's restart-blend
exploits per-token classifier confidence while LeDiFlow only shifts the
prior by a single per-family direction. This insight is **partially
captured** in §3.5 (the "Why the paper quantities are load-bearing on
`selection_ratio`" discussion) and can be **expanded** to cite the Wave
182 LeDiFlow solver as the structural cousin, with the honest disclosure
that Wave 230 P2 per-record paired-t is **UNDERPOWERED** on the
LeDiFlow-vs-FlowA cells (mean_diff d_z = +0.075 / +0.052, both
UNDERPOWERED at df=299, Bonferroni α=0.003125).

**This Wave 251 P1 decision does NOT close the door on that §3.5
expansion.** The Wave 249 P1 audit explicitly leaves that path open as a
separate, scoped integration that does not re-introduce the
"all 16 WINS" framing.

---

## Why CLM-053 would be P0 if true (DeepSeek 2026-09-22 5th-pass note)

DeepSeek's 2026-09-22 5th-pass review correctly notes that a
**"4-baseline all WIN at both NFE 50+100"** claim would be a strong P0
addition to the paper **IF TRUE** — it would directly answer the reviewer
question "is FlowA's value-add real, or is it just what any
training-free diffusion accelerator would buy?" by demonstrating that
FlowA wins against all four canonical training-free acceleration
families (vanilla + parallel-decoding + cache-reuse + distribution-guided
prior-shift) on both quality metrics (pLDDT + scPerplexity).

However, the claim is **NOT TRUE under formal paired-t test**:

* The only formally SUPPORTED cells under Wave 230 P2 protocol are
  **vanilla scPerplexity at both NFE** (d_z ≈ −0.99, p < 1e-44).
* The other 14 cells have paired-diff Cohen's d_z ∈ [0.02, 0.10] —
  too small to detect a 0.01-pp min_effect at 80% power with df=299.
* CLM-053's "all 16 WINS" framing uses a direction-consistent
  point-estimate definition (no formal test), which is a weaker
  statistical claim that Wave 230 P2 supersedes.

Adding CLM-053 as-is would re-introduce the bootstrap-projection problem
that Wave 229 P1 already corrected, and would conflict with the canonical
Wave 230 P2 verdict-precedence distribution that the paper already
reports. The paper would lose credibility with reviewers who attempt to
reproduce the formal test and find 14/16 UNDERPOWERED.

---

## Alternative future work

If a reviewer explicitly requests stronger 4-baseline validation, the
**future work** path is:

1. Re-run the Wave 182 5-arm with the Wave 230 P2 protocol:
   * **NFE ∈ {50, 100}** (not {100, 200})
   * **30 seeds × 10 records per cell** (not 3 seeds × 30 records)
   * **300 records per cell** with **per-record paired diff**
   * **Paired t-test** at **df=299**, **Bonferroni α=0.003125**
2. Report the actual verdict-precedence distribution (2/16 SUPPORTED + 14/16
   UNDERPOWERED is the current Wave 230 P2 result; re-running with
   Fast-DLLM / AB-Cache / LeDiFlow on the same NFE ∈ {50, 100} grid and
   same per-record pairing would yield a like-for-like verdict).
3. Disclose honestly which cells are SUPPORTED vs UNDERPOWERED under
   Bonferroni correction.

Until this re-run is performed, CLM-053's "all 16 WINS" framing is
**direction-consistent but statistically not equivalent** to the canonical
Wave 230 P2 verdict-precedence distribution, and the paper should not
include the CLM-053 "all 16 WINS" framing as a standalone claim.

---

## Status — what the paper contains today

* **Wave 250 added:** CLM-054 (HP sensitivity envelope, §3.7),
  CLM-057 + CLM-058 (Theorem 1 load-bearing, §3.5), CLM-062 (12-cell
  power analysis, §3.5 with full verdict table 1/0/8/3/0), Wave 191 P3
  PROVISIONAL flag (Table 3.2 R5c row).
* **Wave 250 did NOT add:** CLM-053 (per this Wave 251 P1 decision, NOT_OK
  to add).
* **Pre-existing bugs in `docs/drafts/paper-flattened-draft.md` flagged by
  Wave 249 P1 but not in scope of this Wave 251 P1 decision:**
  * Line 317 "Bonferroni-significant across all 4 baselines on
    scPerplexity" — inconsistent with Wave 230 P2 (only vanilla is
    SUPPORTED on scPerplexity).
  * Line 319 "14 of 16 Bonferroni-significant" — inconsistent with Wave
    230 P2 (only 2/16 SUPPORTED + 14/16 UNDERPOWERED).
  These bugs are separate from the CLM-053 decision and were fixed in
  Wave 250 P6 alongside the other pre-existing bug reconciliation
  (commit `82f6802`).

---

## Hard-rule compliance

This Wave 251 P1 decision:

1. **DOES NOT modify the paper.** CLM-053 is correctly excluded from the
   paper; this decision formalises the exclusion without any source-code
   or paper-text changes.
2. **Preserves D.4 30/30 PASS** — no verification script was modified.
3. **Preserves mkdocs 0 warnings** — no documentation build artefact was
   modified.
4. **Preserves claims consistency no drift** — `docs/CLAIMS.md` CLM-053
   entry (line 2269) is unchanged; the entry remains `Status: ACTIVE` in
   `docs/CLAIMS.md` but is NOT integrated into the paper, which is a
   valid "claim held in registry but not surfaced in submission"
   posture.

---

## Files referenced

* `docs/CLAIMS.md` line 2269 — CLM-053 verbatim claim text
* `docs/audit/wave249-p1-clm053-audit.md` — Wave 249 P1 audit (this
  decision's source)
* `docs/audit/wave182-p1-setup.md` — LeDiFlow setup + continuous-FM
  analog solver
* `docs/audit/wave182-p2-eval.md` — LeDiFlow eval on R6 (6 cells ×
  N=30 = 180 records)
* `docs/audit/wave182-p3-comparison.md` — 5-arm comparison table
* `verification_outputs/wave182-p3-five-arm-comparison.csv` — 2-row ×
  13-col 5-arm table
* `verification_outputs/wave182-p2-lediflow-summary.csv` — 8-row
  LeDiFlow per-seed summary
* `verification_outputs/wave230-p2-real-4arm-per-record.csv` — 16-row
  per-cell Table B with `data_kind = real_per_record_paired` (canonical
  Wave 230 P2 verdict)
* `docs/audit/wave230-p2-real-4arm-per-record.md` — 4-arm per-record
  paired analysis
* `docs/drafts/paper-flattened-draft.md` line 177, 213, 317-319 —
  existing head-to-head cell narrative (with the pre-existing bugs
  flagged in Wave 249 P1 §5.3, already fixed in Wave 250 P6 commit
  `82f6802`)
* `docs/CLAIMS.md` line 3133 — CLM-061 (4-arm head-to-head per-cell
  power analysis; the canonical verdict for Table B)

---

## Decision summary (one-liner)

**CLM-053 is NOT_OK to add to the TNNLS submission paper.** The Wave 249
P1 audit (4th-pass DeepSeek pre-check, 2026-09-22) concludes that CLM-053
and Wave 230 P2 4-arm are NOT the same experiment (different NFE, seeds,
N, granularity, statistical test), are direction-consistent but
statistically differ (point-estimate WINS vs Bonferroni-significant
SUPPORTED + UNDERPOWERED), and adding CLM-053 as a standalone claim
would re-introduce the Wave 229 P1 bootstrap-projection problem and
conflict with the canonical Wave 230 P2 verdict-precedence distribution
(2 SUPPORTED + 14 UNDERPOWERED at α=0.003125, df=299, N=300 per cell).
The per-token FlowA vs per-family LeDiFlow granularity distinction from
CLM-053 can be integrated into §3.5 separately, with explicit honest
disclosure that Wave 230 P2 is UNDERPOWERED on the LeDiFlow cells
(d_z = +0.075/+0.052).

---

## Status

**Wave 251 P1 complete.** CLM-053 NOT_OK to add formalised in this
single-document decision trail. No paper source files modified. No
verification scripts modified. All hard rules preserved (D.4 30/30 PASS,
mkdocs 0 warnings, claims consistency no drift).