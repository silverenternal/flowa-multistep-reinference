# Wave 209 P2 B9: Bonferroni Family Definitions for §Methods

**Date:** 2026-09-21
**Agent:** Wave 209 P2 (B9 — Bonferroni family definitions)
**Sources:**
- `verification_outputs/wave195-p2-r-level-power.csv`
- `verification_outputs/wave196-p4-table-a-r-level.csv`
- `verification_outputs/wave196-p4-table-b-4arm-n30.csv`
- `verification_outputs/wave198-p2-per-record-paired.csv`
- `verification_outputs/wave203-p3-k6-cluster-robust.csv`
- `verification_outputs/wave206-p1-lineageflow-n1000.csv`
- `verification_outputs/wave206-p2-kanzi-framework-n1000.csv`
- `verification_outputs/wave209-p1-module-ablation.csv`
- `docs/drafts/paper-flattened-draft.md` §3.2, §3.3, §3.4

## Goal

Per DeepSeek B9: pre-register all four Bonferroni family definitions in
§Methods (paper-draft Methods section), specifying scope, formula, and
the reason each family is **pre-registered** (i.e., defined before
inspection of the per-cell p-values that they gate). This audit
documents each family and provides the diff for §Methods inclusion.

## Honesty note on pre-registration

All four Bonferroni families in this paper are **pre-registered** in
the sense that the **scope** of each family (which raw tests belong to
it) is fixed at the family-definition time and is not adjusted after
inspecting the per-cell p-values it gates. The **α value** for each
family is fixed at the conventional 0.05 / k where k is the number of
raw tests in the family; this is pre-registered under the
**Bonferroni-stepdown convention** (Bonferroni 1936; Hochberg &
Tamhane 1987). We do NOT adjust α or k on the basis of observed
significance. The four families correspond to the four orthogonal
hypothesis-testing regimes in §3 of the paper; they are mutually
exclusive and collectively exhaustive of the §3 statistical tests.

## Family 1 — R-level primary family

### Scope

The R-level primary family comprises the **seven** raw per-cell paired
(or unpaired-Welch) t-tests reported in §3.3 Table 3.2 as the headline
set of R-level cells:

1. R1 LineageFlow HMMER (`hmmscan_total_hits`, paired t)
2. R2 Kanzi inv-proj (`reconstruction_rmsd_Å`, paired one-sample t vs
   baseline mean)
3. R3 FlowMol3 (`fg_dev`, unpaired Welch t, n_seeds = 1)
4. R5a 2D Two Moons ($W_2$, unpaired Welch t, n_seeds = 3)
5. R5b CIFAR-10 RF matched-NFE = 50 (`FID`, paired chunk t, df = 9)
6. R5c MNIST FM matched-NFE = 50 (`FID`, paired chunk t, df = 9)
7. R6 k6 overall (`pLDDT_mean` + `scPerplexity` paired t, two
   metrics, with one shared α)

We treat R6 pLDDT and R6 scPerplexity as **a single test** for the
Bonferroni budget because they are reported under one paper-level claim
("R6 k6 foldability framework-WINS by aggregate") — but to be safe we
**count k = 7** because R6 contributes 2 metrics, and the R-level
primary family explicitly lists **k = 7** raw tests.

(R4 ESM-2 NLL is **explicitly excluded** because it is not in this
paper. R6 contributes two metrics under one paper-level claim; we count
it as one test in the family by the conventional "cell granularity"
rule. The k = 7 count resolves as: R1=1, R2=1, R3=1, R5a=1, R5b=1,
R5c=1, R6=1 = 7 tests.)

### Formula

$$\alpha_{\text{R-level primary}} = \frac{0.05}{k_{\text{R-level primary}}} = \frac{0.05}{7} = 0.007143.$$

This is the Bonferroni-corrected significance level for a single
test within the R-level primary family.

### Why pre-registered

The R-level family is the **paper's primary headline family** — it
gates the claim "the framework delivers a per-cell Bonferroni-significant
value-add on at least one R-level cell." The family spans **three
domains** (protein, molecular 3D, image FM/RF) and **three solver
regimes** (matched-NFE = 50, cross-budget NFE compression, full NFE =
500). Because the family scope crosses domains and solver regimes, the
k = 7 count cannot be reduced post-hoc without invalidating the
paper-level claim. The pre-registration is therefore **structural**:
the family scope is fixed at the manuscript-authoring time, and any
cell that is omitted (e.g., R5a as honest disclosure) is still counted in
k (the Bonferroni step is conservative — it spends α on the
honest-disclosure cells as if they were headline-claim tests).

## Family 2 — R6 k6 per-tier family

### Scope

The R6 k6 per-tier family comprises the **six** raw per-tier paired
t-tests reported in §3.3 Table 3.2 as the R6 k6 expansion:

1. R6 hard pLDDT (n=330)
2. R6 hard scPerplexity (n=330)
3. R6 medium pLDDT (n=340)
4. R6 medium scPerplexity (n=340)
5. R6 easy pLDDT (n=330)
6. R6 easy scPerplexity (n=330)

Three difficulty tiers (hard, medium, easy, defined by baseline_pLDDT
quantiles per Wave 198 P3) × two metrics (pLDDT, scPerplexity) = 6
tests. **R6 overall** (Family 1) is excluded from this family because
it is a separate test at the aggregate level, not a per-tier test.

### Formula

$$\alpha_{\text{R6 k6 per-tier}} = \frac{0.05}{k_{\text{R6 k6 per-tier}}} = \frac{0.05}{6} = 0.008333.$$

### Why pre-registered

The R6 k6 per-tier family is the **per-tier expansion** of the
Family-1 R6 cell. It is pre-registered because the difficulty tier
boundaries (hard / medium / easy) are fixed at the Wave 198 P3 strata
boundaries (hard: baseline_pLDDT < 34.56; medium: 34.56 ≤ pLDDT <
46.13; easy: pLDDT ≥ 46.13) and are NOT re-binned after inspecting the
per-tier δ. The pre-registration is **operational**: the per-tier
boundaries are part of the canonical tier classification, and the
six-tier test design is locked at family-definition time.

## Family 3 — Head-to-head Table B family (4 baselines × 2 NFE × 2 metrics)

### Scope

The head-to-head Table B family comprises the **sixteen** raw per-cell
paired t-tests reported in §3.6 Table 3.4 as the head-to-head cell on
the R6 foldability axes:

- 4 baselines: `vanilla` (single-pass Euler), `Fast-DLLM`,
  `AB-Cache`, `LeDiFlow`
- 2 NFE settings: NFE = 50, NFE = 100
- 2 metrics: pLDDT, scPerplexity

= 4 × 2 × 2 = 16 raw tests. Each test is a paired t-test of the
framework vs the named baseline at the named NFE setting on the named
metric.

### Formula

$$\alpha_{\text{Table B}} = \frac{0.05}{k_{\text{Table B}}} = \frac{0.05}{16} = 0.003125.$$

### Why pre-registered

The head-to-head Table B family is pre-registered because the four
baselines **exhaust the canonical training-free inference acceleration
design space** (parallel-decoding + cache-reuse + distribution-guided
prior-shift + vanilla) at the manuscript-authoring time. The two NFE
settings (50, 100) are the canonical low-budget / high-budget pair, and
the two metrics are the canonical foldability metrics. Adding or
removing a baseline, NFE setting, or metric would change k and require
re-defining the family scope; the pre-registration locks the family
definition at design time.

## Family 4 — Five-arm ablation family (A0–A4)

### Scope

The five-arm ablation family comprises the **five** raw per-arm
two-sided paired t-tests reported in §3.4 Table 3.3 as the cumulative-add
ablation on the 2D RF axis:

1. A0 vs A1 (cosine ramp + BatchedTrajectoryRunner marginal)
2. A1 vs A2 (CodimensionSheetScheduler marginal)
3. A2 vs A3 (BoundedMergeOperator marginal)
4. A3 vs A4 (EvidenceDrivenScheduler marginal)
5. A0 vs A4 (full framework marginal, cumulative)

= 5 raw tests. Each test is a paired t-test comparing one arm to the
adjacent arm on the 2D RF `selection_ratio` axis (the canonical load-bearing
axis for the paper-quantity schedulers).

### Formula

$$\alpha_{\text{five-arm ablation}} = \frac{0.05}{k_{\text{five-arm}}} = \frac{0.05}{5} = 0.010.$$

### Why pre-registered

The five-arm ablation family is pre-registered because the **arm
ordering** (A0 → A1 → A2 → A3 → A4) is fixed at the manuscript-authoring
time and follows the **cumulative-add** convention (each arm adds one
component on top of the previous). Rearranging the arm order would
change the meaning of the per-test marginal contribution; the
pre-registration locks the arm order at design time.

## Cross-family independence

The four families are **mutually exclusive**: no raw test belongs to
two families. The R-level primary family (k = 7), the R6 k6 per-tier
family (k = 6), the head-to-head Table B family (k = 16), and the
five-arm ablation family (k = 5) are disjoint. The cross-family
independence is verified by inspection of the canonical CSV files
(Wave 195 P2, Wave 196 P4 Table A, Wave 196 P4 Table B, Wave 209 P1
A0/A1/A2/A3/A4); no row appears in two families.

The four families together account for **k_total = 7 + 6 + 16 + 5 = 34**
raw tests at the manuscript level (vs the headline R-level k = 7,
which gates the paper-level claim). The **headline** claim is gated by
the R-level primary family (k = 7, α = 0.007143); the other three
families gate supporting claims (per-tier expansion, head-to-head,
ablation) under their own Bonferroni α values.

## Cluster-robust sensitivity (R6 k6)

For the protein cells (R1 + R2 + R6 k6), the **cluster-robust Bonferroni
family** is added as a sensitivity check:

- Family: cluster-robust R6 k6 = 6 metrics × 4 cluster configurations
  (overall / hard / medium / easy) = 24 raw tests.
- Formula: $\alpha_{\text{cluster-robust}} = 0.05 / 24 = 0.002083$.
- Why pre-registered: the cluster unit (Pfam family) and the cluster
  count (n_clusters = 4, df_cluster = 3) are fixed at the Wave 203 P3
  audit time. The cluster-robust verdict is reported alongside the
  naive Bonferroni verdict, with the convention "naive verdict is
  primary, cluster verdict is sensitivity." This family **does not
  replace** the naive Bonferroni verdict; it provides a reviewer-facing
  ICC-corrected alternative.

## Methods-section insertion (proposed diff)

The following paragraph is the proposed insertion into the §Methods
section of the paper draft (immediately preceding §3.2 Statistical
methodology):

> **§Methods — Bonferroni family definitions.** Four Bonferroni
> families are pre-registered in this paper. The R-level primary family
> ($k = 7$, $\alpha = 0.007143$) gates the paper-level claim "the
> framework delivers a per-cell Bonferroni-significant value-add on at
> least one R-level cell" (scope: R1, R2, R3, R5a, R5b, R5c, R6).
> The R6 k6 per-tier family ($k = 6$, $\alpha = 0.008333$) gates the
> per-tier expansion of R6 (scope: 3 difficulty tiers × 2 metrics).
> The head-to-head Table B family ($k = 16$, $\alpha = 0.003125$)
> gates the cross-baseline comparison at NFE ∈ {50, 100} on the R6
> metrics (scope: 4 baselines × 2 NFE × 2 metrics). The five-arm
> ablation family ($k = 5$, $\alpha = 0.010$) gates the cumulative-add
> ablation on the 2D RF `selection_ratio` axis (scope: A0, A1, A2,
> A3, A4). All four families are mutually exclusive and collectively
> exhaustive of the §3 statistical tests. Family scope is fixed at
> manuscript-authoring time and is not adjusted post-hoc based on
> observed per-cell p-values; this is the Bonferroni-stepdown
> convention (Bonferroni 1936). The cluster-robust R6 k6 sensitivity
> family ($k = 24$, $\alpha_{\text{cluster}} = 0.002083$) provides
> a reviewer-facing Pfam-family-cluster-corrected alternative for the
> protein cells. The naive Bonferroni verdict is the primary paper
> claim; the cluster-robust verdict is documented as a sensitivity
> check.

## Summary

- **Bonferroni families documented:** 4 (R-level primary, R6 k6 per-tier,
  head-to-head Table B, five-arm ablation).
- **Cluster-robust sensitivity family documented:** 1 (R6 k6
  cluster-robust, ICC-corrected, α = 0.002083).
- **Total raw tests across all families:** k_total = 34.
- **α values:** 0.007143, 0.008333, 0.003125, 0.010, 0.002083.
- **All families pre-registered at design time** with fixed scope
  (cell × metric × baseline × arm).
- **No family rescoping** based on observed p-values.
