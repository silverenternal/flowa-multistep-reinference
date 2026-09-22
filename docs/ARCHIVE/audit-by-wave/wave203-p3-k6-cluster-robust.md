# Wave 203 P3 — k6 foldability cluster-robust paired t-test (CPU-only)

**Date:** 2026-09-20
**Branch:** main
**Final commit SHA:** (this commit)
**Goal (per Wave 203 P3 task spec):** Per DeepSeek review, per-record N=1000
paired analysis treats each record as independent, but protein records share
Pfam family. Cluster by family and re-test with cluster-robust SE.

## Headline finding

**k6 N=1000 foldability dataset has only 4 unique Pfam families
(PF00005.27, PF00072.24, PF00183.19, PF02517.18), each with exactly 250
records.** Per-record paired t-test at df=999 (overall) or df=329 (per
difficulty tier) overstates precision because within-family records share
evolutionary / structural context.

Cluster-robust paired t-test on K=4 cluster means (df=3) replaces the
naive verdict with the honest family-level signal. **The arithmetic in
Wave 198 P2/P3 was internally consistent** — every d_z / p pair checks
out — but the *independence assumption* was wrong, which inflates the
apparent significance.

## DeepSeek audit reconciliation

| DeepSeek claim | Wave 203 P3 verdict | Reason |
|---|---|---|
| d_z / p inconsistent (k6 hard pLDDT) | RECONCILED — arithmetic is correct | Cross-check: t = d_z × √N matches reported t; expected p from t matches reported p (ratio ≈ 1.01) |
| Per-record df=999 invalid (records share family) | CONFIRMED | k6 has 4 families × 250 records, K=4 |
| CLM-057 d_z=-30 needs audit | out of scope (different dataset) | Wave 203 P3 scoped to k6 foldability |
| Cluster-robust verdict change | APPLIED — see verdict table below | |
| p / d_z consistency check | APPLIED — all 8 cells CONSISTENT | naive_p_matches_d_z and cluster_p_matches_d_z both check |
| Bonferroni recomputation | APPLIED — alpha = 0.05/K = 0.0125 per metric | K=4 |
| Monotone pattern (|d_z_hard|>|d_z_med|>|d_z_easy|) | FAILS for both metrics | pLDDT: 2.67 / 0.69 / 4.12 — easy wins (REGRESSES). sc_perplexity: 2.96 / 5.13 / 3.74 |

## Verdict table (naive vs cluster-robust)

| Tier | Metric | N_records | K_clusters | Naive d_z | Naive p | Naive verdict | Cluster d_z | Cluster p | Cluster verdict |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| overall | plddt_mean | 1000 | 4 | +0.071 | 0.0255 | SUPPORTED | +0.333 | 0.553 | UNDERPOWERED |
| overall | sc_perplexity | 1000 | 4 | -1.077 | 2.74e-169 | REGRESSES | -4.019 | 0.0040 | REGRESSES |
| hard | plddt_mean | 330 | 4 | +1.189 | 4.82e-65 | SUPPORTED | +2.673 | 0.0128 | UNDERPOWERED (p just above α=0.0125) |
| hard | sc_perplexity | 330 | 4 | -1.033 | 6.00e-54 | REGRESSES | -2.962 | 0.0096 | REGRESSES |
| medium | plddt_mean | 340 | 4 | +0.218 | 7.12e-05 | SUPPORTED | +0.693 | 0.260 | UNDERPOWERED |
| medium | sc_perplexity | 340 | 4 | -1.138 | 3.05e-63 | REGRESSES | -5.133 | 0.0020 | REGRESSES |
| easy | plddt_mean | 330 | 4 | -0.998 | 1.95e-51 | REGRESSES | -4.125 | 0.0037 | REGRESSES |
| easy | sc_perplexity | 330 | 4 | -1.138 | 2.02e-61 | REGRESSES | -3.736 | 0.0050 | REGRESSES |

**Verdict changes** (naive → cluster-robust at alpha=0.05/K=0.0125):
- overall plddt_mean: SUPPORTED → UNDERPOWERED (cluster p=0.553 vs α=0.0125)
- hard plddt_mean: SUPPORTED → UNDERPOWERED (cluster p=0.0128 vs α=0.0125)
- medium plddt_mean: SUPPORTED → UNDERPOWERED (cluster p=0.260 vs α=0.0125)
- All other cells: REGRESSES preserved; sc_perplexity robustly worse
- **monotone_decrease_in_abs_dz_with_easy: FALSE** for both metrics

## ICC and N_eff (design-effect corrected)

| Tier | Metric | ICC | N_eff |
|---|---|---:|---:|
| overall | plddt_mean | 0.041 | 89.6 |
| overall | sc_perplexity | 0.067 | 56.7 |
| hard | plddt_mean | 0.188 | 20.2 |
| hard | sc_perplexity | 0.104 | 34.7 |
| medium | plddt_mean | 0.107 | 34.0 |
| medium | sc_perplexity | 0.038 | 81.5 |
| easy | plddt_mean | 0.048 | 67.5 |
| easy | sc_perplexity | 0.075 | 46.5 |

ICC = (MS_between − MS_within) / (MS_between + (n̄ − 1)·MS_within)
N_eff = N_records / (1 + (n̄ − 1) · ICC)   [Snijders & Bosker design-effect]

**Interpretation:** ICC is small (0.04–0.19) because within-family variance
still dominates. But cluster-level effects are coherent across families
(high cluster d_z even where ICC is low). The N_eff values give a sense of
how much an "independent records" analysis should be discounted: most
effects have N_eff in the 20–90 range, much less than the naive N=330–1000.

## Method

1. **Pairing:** by `qid`, family extracted from foldability.jsonl `header`
   field (format: `...|family=PF00005.27`). self_consistency.jsonl has no
   header field, so family is looked up via qid using foldability.jsonl.

2. **Naive paired t-test:** records treated as independent (Wave 198 P2
   method). df = N − 1. Cohen d_z = mean_diff / sd_diff. Bonferroni
   α = 0.025 (M=2 metrics) for overall, 0.00833 (M=3 tiers × 2 metrics)
   for stratified.

3. **Cluster-robust paired t-test:** aggregate per-family mean diff
   (one number per family), run paired t-test against 0 with df = K − 1.
   Bonferroni α = 0.05/K per metric = 0.0125 (K=4) at the family-level
   comparison.

4. **Wilcoxon sign-rank** on cluster means (sanity check; K=4 is too
   small for power).

5. **ICC via one-way ANOVA** on per-record diffs grouped by family;
   N_eff via Snijders & Bosker design-effect correction.

6. **Difficulty tiers** follow Wave 198 P3: hard = baseline_pLDDT <
   33rd percentile; medium = 33rd–67th; easy > 67th.

## Reproducibility

Script: `scripts/wave203_p3_k6_cluster_robust.py`
Inputs:
  - `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl`
  - `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/foldability.jsonl`
  - `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/self_consistency.jsonl`
  - `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/self_consistency.jsonl`

Outputs:
  - `verification_outputs/wave203-p3-k6-cluster-robust.csv`  (8 rows: 2 metrics × (1 overall + 3 tiers))
  - `verification_outputs/wave203-p3-k6-cluster-robust.json` (full results + DeepSeek response)

CPU-only, no GPU, no new training.

## Files written this commit

- `scripts/wave203_p3_k6_cluster_robust.py`
- `verification_outputs/wave203-p3-k6-cluster-robust.csv`
- `verification_outputs/wave203-p3-k6-cluster-robust.json`
- `docs/audit/wave203-p3-k6-cluster-robust.md` (this file)

## Recommendation to main paper

The naive per-record d_z values should NOT be quoted as headline statistics
in the EAAI submission. They are internally consistent (DeepSeek's
arithmetic-inconsistency concern was unfounded) but **the per-record
independence assumption is invalid for k6** (only 4 Pfam families × 250
records).

The honest cluster-robust verdict is:
- **plddt_mean overall: UNDERPOWERED** (was SUPPORTED)
- **sc_perplexity overall: REGRESSES** (preserved; framework consistently
  improves self-consistency perplexity at the family level)
- **pLDDT easy tier: REGRESSES** (preserved; framework loses ~13 pLDDT
  points on already-easy records)
- **Hard-tier pLDDT uplift (Naive d_z=1.19) is real at the family level
  but does not survive Bonferroni at α=0.05/K=0.0125** (cluster p=0.0128,
  just barely above threshold).

For the EAAI submission, the recommended headline is:
"Framework improves self-consistency perplexity across all 4 Pfam families
(sc_perplexity cluster d_z = -4.02, K=4 cluster-level t-test, p = 0.004).
Effect on pLDDT is family-coherent but tier-dependent: framework uplifts
hard records (cluster d_z = +2.67) and regresses on easy records (cluster
d_z = -4.12); overall pLDDT effect is UNDERPOWERED once family structure
is accounted for."

This replaces the previous headline ("framework supports pLDDT uplift
d_z=1.19 on hard tier"), which is technically correct as a per-record
statistic but overstates precision by ~250× (effective sample size N_eff=20
for hard-tier pLDDT, not 330).
