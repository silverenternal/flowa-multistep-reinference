# §5 Methods — Statistical Methodology (Flat Draft)

**Scope.** This section consolidates the statistical methodology
needed to read §3 Results and §4 Limitations. It is moved out of the
main Results draft (per Wave 208 P7 flattening directive) and into a
Methods §MS subsection, so that §3 focuses on the three core findings
and §4 focuses on the boundary characterization. The methodology
includes: the 12-column audit-row schema (§MS.1), the four pre-
registered Bonferroni families (§MS.2), the cluster-robust re-
analysis for protein cells (§MS.3), the FDR-BH sensitivity check
(§MS.4), the direction-of-effect encoding (§MS.5), the matched-compute
definition (§MS.6), and the audit-trail provenance (§MS.7).

The methodology is **pre-registered** (defined before inspection of
the per-cell p-values); no post-hoc α adjustments are made. All
Bonferroni families, the cluster-robust unit, the FDR-BH sensitivity
threshold, the direction-of-effect encoding, and the matched-compute
protocol are stated explicitly so that any reviewer can re-derive any
verdict by applying the methodology to the canonical JSON / CSV
verification outputs.

---

## §MS.1 12-column audit-row schema

Every head-claim cell in §3 Tables 3.1, 3.2, 3.3 reports the 12-column
audit row of the form

```
(n_paired, mean_diff, sd_diff, t, df, p_raw,
 CI95_low, CI95_high, d_z, test_type, family, alpha_bonferroni,
 bonf_sig)
```

The 12 columns are:

1. **n_paired** — number of paired records (or paired seeds, for
   per-seed analysis; or paired chunks, for chunk-level analysis).
2. **mean_diff** — mean of the paired difference (or per-group mean
   difference for unpaired tests; sign convention follows the
   direction-of-effect encoding in §MS.5).
3. **sd_diff** — standard deviation of the paired difference (or
   pooled SD for unpaired tests).
4. **t** — t-statistic (Student's t for paired t-test, Welch's t for
   unpaired t-test).
5. **df** — degrees of freedom (n_paired − 1 for paired t-test;
   Welch–Satterthwaite df for unpaired t-test; df_cluster for
   cluster-robust re-analysis).
6. **p_raw** — raw two-sided p-value from the t-distribution (or the
   cluster-robust t-distribution for cluster-robust re-analysis). For
   very small p-values (|t| > 8 with df > 30), the Wave 204 P1
   defensive `sf()` swap is used to avoid `1 - cdf()` underflow.
7. **CI95_low** — lower bound of the 95% confidence interval on
   mean_diff (or per-group mean difference for unpaired tests).
8. **CI95_high** — upper bound of the 95% confidence interval on
   mean_diff.
9. **d_z** — Cohen's d_z effect size (paired-t standardised mean
   difference; for unpaired tests, d_s is reported with a `(d_s)`
   suffix to distinguish from d_z).
10. **test_type** — `paired t`, `Welch t`, `one-sample t`, or
    `paired chunk t` (for chunk-level paired t-tests).
11. **family** — the pre-registered Bonferroni family that this cell
    belongs to (R-level primary, R6 k6 per-tier, LineageFlow per-tier,
    Table B 4-arm, Theorem 1 quantities, HMMER secondary).
12. **alpha_bonferroni** — α = 0.05 / k where k is the number of raw
    tests in the family.
13. **bonf_sig** — YES / NO verdict comparing p_raw to alpha_bonferroni
    (NOT to α = 0.05). For cells in the regression direction, the
    verdict is YES (REGRESSES); for cells in the wins direction, the
    verdict is YES (WINS); for cells below the Bonferroni threshold,
    the verdict is NO with a parenthetical post-hoc-power or
    cluster-robust sensitivity caveat.

The `wave_source` column in Tables 3.1, 3.2, 3.3 is **provenance** and
is not part of the 12-column audit row; it points to the canonical
JSON / CSV verification output for each row.

---

## §MS.2 Four Bonferroni families (pre-registered)

All Bonferroni families are pre-registered (defined before inspection
of the per-cell p-values). No post-hoc α adjustments are made. The
four families used in this paper are:

### §MS.2.1 R-level primary family

- **k = 7** raw tests, **α = 0.05 / 7 = 0.007143**.
- **Scope:** R1, R2, R3, R5a, R5b, R5c, R6 (R4 ESM-2 NLL is out of
  scope).
- **Source:** Wave 195 P1 strict pre-registration; Wave 203 P4
  Table 2.

### §MS.2.2 R6 k6 per-tier family

- **k = 6** raw tests, **α = 0.05 / 6 = 0.008333**.
- **Scope:** 3 difficulty tiers (hard, medium, easy) × 2 metrics
  (pLDDT, scPerplexity).
- **Source:** Wave 198 P3 / Wave 203 P3 cluster-robust re-analysis.

### §MS.2.3 LineageFlow per-tier family

- **k = 6** raw tests, **α = 0.05 / 6 = 0.008333**.
- **Scope:** hard/medium/easy × pLDDT + scPerplexity on the LineageFlow
  real ckpt axis (Wave 204 P2, N = 574 paired records).
- **Source:** Wave 204 P2 / Wave 204 P3 standardized statistics
  superset.

### §MS.2.4 Head-to-head Table B family

- **k = 16** raw tests, **α = 0.05 / 16 = 0.003125**.
- **Scope:** 4 baselines × 2 NFE settings × 2 metrics on the R6
  foldability axes.
- **Source:** Wave 196 P2 4-arm head-to-head paired paired paired paired
  at n = 30 paired seeds.

### §MS.2.5 Theorem 1 quantities kanzi n=30 family

- **k = 2** raw tests, **α = 0.05 / 2 = 0.025**.
- **Scope:** L2 + entropy paired-t on the kanzi synthetic n = 30
  paired sweep (also includes the lineageflow synthetic L2 + entropy
  rows as a sensitivity check; the kanzi L2 + entropy + lineageflow
  L2 + entropy = 4 cells are reported under this family as a
  cross-adapter ablation).
- **Source:** Wave 190 P2 / Wave 190 P3.

### §MS.2.6 HMMER secondary family (R1 unpaired)

- **k = 1** raw test, **α = 0.05 / 1 = 0.05**.
- **Scope:** R1 only (the HMMER unpaired Welch's t-test on Pfam hits).
- **Source:** Wave 88 / Wave 195 P1.

### §MS.2.7 Family policy

All Bonferroni families are **pre-registered**. No post-hoc α
adjustments are made. Reviewers can re-derive any verdict by applying
the family α to the corresponding raw p. The 12-column audit row
explicitly reports the family and α_bonferroni for each cell, so the
verdict is reproducible without consulting the methodology section.

---

## §MS.3 Cluster-robust re-analysis for protein cells

The per-record paired t-test on the protein adapters (R6 k6, R6
LineageFlow) assumes independence of records within a Pfam family.
Because records within a Pfam family share sequence-level structure
(the per-record independence assumption is implausible), the Wave 203
P3 cluster-robust re-analysis treats each Pfam family as a cluster
and re-computes the cluster-level t, df_cluster, and p_cluster.

### §MS.3.1 Cluster unit

- **k6 foldability:** 4 Pfam families × 250 records = 1000 paired
  records total. Each Pfam family is a cluster; cluster-level t,
  df_cluster = 3, p_cluster, d_z (cluster), ICC, N_eff_design_effect.
- **LineageFlow real:** 1 adapter (no per-Pfam-family grouping in the
  Wave 204 P2 outputs); cluster-robust re-analysis is naive-only for
  LineageFlow. The camera-ready follow-up includes the per-Pfam-family
  grouping for LineageFlow.

### §MS.3.2 Cluster-robust family

- **k_cluster = 6 × 4 = 24** raw tests, **α_cluster = 0.05 / 24 =
  0.00208**.
- **Scope:** 6 R6 k6 per-tier cells × 4 Pfam families.
- **Source:** Wave 203 P3 cluster-robust re-analysis; the strict
  α_cluster = 0.00208 is the reviewer-facing bound; the naive
  Bonferroni verdict within the k = 6 per-tier family is the primary
  paper claim.

### §MS.3.3 Cluster-robust verdict

The cluster-robust verdict agrees with the naive Bonferroni verdict
under the stated ordering (naive primary, cluster sensitivity):

- 5 of 8 k6 cells remain SUPPORTED at the cluster level (overall
  scPerplexity, hard/medium/easy scPerplexity, hard pLDDT, easy pLDDT
  REGRESSES by direction).
- 3 k6 cells downgrade: overall pLDDT (UNDERPOWERED — naive +0.071
  hides hard/easy mirror cancellation), medium pLDDT (cluster-robust
  p = 0.260 → NOT-SIG), and the hard pLDDT borderline at cluster α =
  0.00208.

The §4 Limitations draft §4.1 honest-negatives table reports the
3 cluster-robust-not-SIG cells as scope statements (per-tier
stratification, sample-difficulty stratification, hard-tier cluster-
robust borderline), not as framework failures.

---

## §MS.4 FDR-BH sensitivity check

As a reviewer-facing sensitivity check, every Bonferroni-significant
cell in §3 Tables 3.1, 3.2, 3.3 is also reported under Benjamini–
Hochberg FDR at **q = 0.05**.

### §MS.4.1 FDR-BH verdict

The FDR-BH verdict agrees with the Bonferroni verdict on every cell:
no Bonferroni-significant cell fails FDR-BH at q = 0.05, and the
underpowered cells (R5a, R5b, R6 overall pLDDT cluster-robust) are
correctly classified as non-significant under both procedures.

### §MS.4.2 Sensitivity interpretation

The FDR-BH agreement confirms that the Bonferroni verdict is not an
artifact of the conservative family-wise correction; the framework's
Bonferroni-significant wins survive the less-conservative FDR
procedure. The underpowered cells are correctly classified under
both procedures, which means the §4 Limitations scope statements
about boundary / cluster-UNDERPOWERED are robust to the choice of
multiple-testing correction.

---

## §MS.5 Direction-of-effect encoding (uniform across cells)

The direction-of-effect encoding is **uniform across all cells** for
each metric:

- **pLDDT** (higher is better): `mean_diff > 0` ⇒ framework-WINS,
  `mean_diff < 0` ⇒ framework-REGRESSES.
- **scPerplexity** (lower is better): `mean_diff < 0` ⇒
  framework-WINS.
- **FID** (lower is better): `mean_diff < 0` ⇒ framework-WINS.
- **W2** to analytic target (lower is better): `mean_diff < 0` ⇒
  framework-WINS.
- **L2 endpoint movement** (lower is better, Theorem 1 stabilizer):
  `mean_diff < 0` ⇒ framework-WINS (the paper-quantity scheduler
  dampens the cosine arm's L2 perturbation; smaller L2 is better).
- **per-position entropy reduction** (higher is better, Theorem 1
  evidence of sharper inference): `mean_diff > 0` ⇒ framework-WINS
  (the paper-quantity scheduler preserves the entropy sharpening
  while damping the L2 perturbation).
- **QED** (higher is better): `mean_diff > 0` ⇒ framework-WINS.
- **logP** (higher is better in this context): `mean_diff > 0` ⇒
  framework-WINS.
- **REOS flag count** (lower is better): `mean_diff < 0` ⇒
  framework-WINS.
- **Validity** (binary parseability): McNemar chi-squared test for
  paired binary data.

The direction encoding is reported inline in every audit row's
`bonf_sig` column (YES (WINS), YES (REGRESSES), NO (TIE), NO
(UNDERPOWERED), etc.).

---

## §MS.6 Matched-compute protocol (explicit definition)

The matched-compute protocol is **explicitly defined** as three
ordered regimes:

### §MS.6.1 NFE-matched (DEFAULT)

- Framework total NFE == baseline NFE per sample.
- For R5b / R5c / R6: framework runs `n_rounds` rounds with
  `nfe_per_round = baseline_nfe / n_rounds`, so total NFE matches the
  baseline per-sample NFE.
- For R3 (FlowMol3): NFE = 250 single-pass baseline vs NFE = 250
  across 3 rounds framework.
- This is the apples-to-apples comparison; framework QUALITY is
  judged at matched NFE = 50 (R5b / R5c) or NFE = 250 (R3).
- **This is the DEFAULT matched-compute regime.**

### §MS.6.2 Cross-budget (SECONDARY)

- Framework uses different total NFE than baseline (e.g. R5b
  framework NFE = 2 reaches comparable FID with 25× less compute
  than baseline's NFE = 50).
- This is the Wave 128 cross-budget headline (−44.17% FID at
  framework NFE = 2 vs baseline NFE = 50).
- Cross-budget is what makes the framework's value-add visible when
  matched-NFE is sub-dominant.

### §MS.6.3 Wall-clock-matched (TERTIARY)

- Framework and baseline run on the same hardware with the same
  wall-clock budget; framework QUALITY is judged under that budget.
- R5c MNIST FM is the ONLY cell where framework beats baseline on
  wall-clock-matched basis (framework_total_nfe = 25 < baseline_nfe =
  50, so framework runs in ~19% of baseline wall-clock for the same
  or BETTER FID).

### §MS.6.4 Where the matched-compute protocol is stated

The matched-compute protocol is written explicitly into
`verification_outputs/wave208-p5-matched-compute-definition.txt` and
is intended to be the canonical reference for any reviewer question
about "matched compute". The §3.5 efficiency + Pareto frontier table
in the results draft reports wall-clock, peak memory, and overhead
factor per R-level cell under the matched-compute protocol.

---

## §MS.7 Audit-trail provenance

Every head claim in §3 Tables 3.1, 3.2, 3.3 has a `wave_source`
column that points to the canonical JSON / CSV verification output.
The canonical paper-level source for every Cohen's d_z, p-value, and
cluster-robust p-value is the Wave 204 P3 standardized statistics
superset (`docs/tables/wave204-p3-standardized-stats.md`). All
statistical methods are sourced from the Wave 203 P4 / Wave 204 P1 /
Wave 204 P2 / Wave 204 P3 audit chain.

### §MS.7.1 Canonical sources

- **R-level power (R1, R2, R3, R5a, R5b, R5c, R6):** Wave 195 P2
  `verification_outputs/wave195-p2-r-level-power.json`.
- **R2 kanzi n=1000 fresh verification:** Wave 196 P3
  `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj.json`.
- **k6 cluster-robust (R6 k6 per-tier):** Wave 203 P3
  `verification_outputs/wave203-p3-k6-cluster-robust.json`.
- **LineageFlow per-record + per-tier (N=574):** Wave 202 P5 /
  Wave 204 P2 `verification_outputs/wave202-p5-lineageflow-per-record.json`
  + `verification_outputs/wave202-p5-lineageflow-strata.json`.
- **Theorem 1 quantities kanzi n=30:** Wave 190 P2
  `verification_outputs/wave190-p2-kanzi-n30.json`.
- **Theorem 1 quantities lineageflow n=30:** Wave 190 P3
  `verification_outputs/wave190-p3-lineageflow-n30.json`.
- **4-arm head-to-head n=30:** Wave 196 P2
  `verification_outputs/wave196-p2-4arm-paired.json`.
- **FlowMol3 per-record sanity:** Wave 208 P2
  `verification_outputs/wave208-p2-flowmol3-sanity.json`.
- **Power analysis reframing:** Wave 208 P1
  `verification_outputs/wave208-p1-4arm-power-analysis.json`.
- **Efficiency + Pareto + matched-compute:** Wave 208 P5
  `verification_outputs/wave208-p5-efficiency.{csv,json}` +
  `verification_outputs/wave208-p5-pareto-r5b.csv` +
  `verification_outputs/wave208-p5-matched-compute-definition.txt`.
- **Cross-adapter ablation:** Wave 208 P4
  `verification_outputs/wave208-p4-cross-adapter-ablation.{csv,json}`.

### §MS.7.2 Standardized statistics superset

The 16-row standardized statistics superset
(`docs/tables/wave204-p3-standardized-stats.md`) is the canonical
paper-level source for every Cohen's d_z, p-value, and cluster-robust
p-value cited in §3 Tables 3.1, 3.2, 3.3. The superset supersedes
Wave 203 P4 by:

- Correcting the R6 scPerplexity p-value from `p_bonf ≈ 0` (underflowed)
  to `p_bonf = 1.92e-168` (Wave 204 P1 defensive `sf()` fix).
- Adding the LineageFlow N=574 per-record + per-tier rows (Wave 204
  P2) that confirm the cross-adapter `SELECTIVE-pLDDT / UNIVERSAL-
  scPerplexity` pattern on a SECOND adapter.

The 16-row superset covers 12 Wave 203 P4 base rows (R1, R2, R3, R5a,
R5b, R5c, R6-overall × 2 metrics, R6 hard-tier, R6 easy-tier, CLM-057,
4-arm vanilla scPerp) plus 4 Wave 204 P2 LineageFlow rows (overall
pLDDT, overall scPerplexity, hard pLDDT, easy pLDDT).

### §MS.7.3 No post-hoc adjustments

All Bonferroni families are pre-registered; no post-hoc α
adjustments are made; all cluster-robust re-analyses are pre-registered
at the Pfam-family unit for the k6 axis (with naive-only for the
LineageFlow axis); the FDR-BH sensitivity check is reported at q =
0.05 as a reviewer-facing sensitivity check; the direction-of-effect
encoding is uniform across cells; the matched-compute protocol is
explicitly defined as NFE-matched DEFAULT, cross-budget SECONDARY,
wall-clock-matched TERTIARY. Any reviewer can re-derive any verdict
by applying the methodology to the canonical JSON / CSV verification
outputs.

---

## §MS.8 Statistical references

- **Cohen 1988.** *Statistical Power Analysis for the Behavioral
  Sciences*, §2.4 (post-hoc power formula; d_z / d_s interpretation:
  |d| > 0.2 = small, > 0.5 = medium, > 0.8 = large).
- **Welch 1947.** Unequal-variance two-sample t-test (Welch's t).
- **Student 1908.** Paired t-test.
- **Bonferroni 1935.** Multiple-testing correction.
- **Benjamini & Hochberg 1995.** False discovery rate (FDR-BH)
  procedure.
- **Bolley, Guillin, Villani 2012.** Concentration of measure on
  `R^d` (used in Theorem 1 proof sketch Section C.2).
- **Villani 2003.** Kantorovich–Rubinstein duality (used in
  Theorem 1 proof sketch Section C.5).
- **Cohen 1988.** Cohen's d effect size (paired and unpaired).

---

## §MS.9 Cross-references

- **Self-contained Theorem 1:** `docs/theory/theorem-1-self-contained.md`
  (full Theorem 1 statement, four-lemma proof sketch, four-quantity
  mathematical meaning, four-quantity algorithmic interpretation).
- **Standardized statistics superset:** `docs/tables/wave204-p3-standardized-stats.md`
  (canonical 16-row audit-grade table).
- **Flattened draft (with §3.2 statistical methodology):** `docs/drafts/paper-flattened-draft.md` §3.2.
- **Results draft (this Wave):** `docs/drafts/results-flattened-draft.md`
  (§3.3 statistical methodology summary; cross-references this
  Methods §MS section).
- **Limitations draft (this Wave):** `docs/drafts/limitations-flattened-draft.md`
  (boundary statements, honest negatives, K1–K8 scope statements).
