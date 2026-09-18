# Wave 195 P3 — Per-cell power analysis for 12 4-arm head-to-head deltas

**Date.** 2026-09-19
**Agent.** Wave 195 P3 4-arm power analysis agent
**Working directory.** `/home/hugo/codes/flowa-multistep-reinference`
**Commit SHA (analysis-frozen).** `ff6ae12` (HEAD at start of Wave 195 P3).
**Scope.** 12 per-cell power analyses for the 4-arm head-to-head
(FlowA vs each of Fast-DLLM, AB-Cache, LeDiFlow; 2 metrics × 2 NFE per
baseline).

**Output artifacts.**
- `verification_outputs/wave195-p3-4arm-power.csv` — 12 rows × 26 cols
- `verification_outputs/wave195-p3-4arm-power.json` — full JSON spec
- `tools/wave195_p3_4arm_power.py` — reproducible script

---

## 1. Methodology

### 1.1 Verdict precedence (matches Wave 195 P1 spec §1.1)

| rank | verdict          | trigger                                                                  |
|------|------------------|--------------------------------------------------------------------------|
| 1    | `TIE`            | `|delta| < min_effect_size` (1 pp noise floor)                           |
| 2    | `UNDERPOWERED`   | post-hoc power at `min_effect_size` < 0.5                                |
| 3    | `SUPPORTED`      | Bonferroni-corrected `p < α` AND `delta > 0` (framework wins)            |
| 4    | `REGRESSES`      | Bonferroni-corrected `p < α` AND `delta < 0` (framework loses)           |
| 5    | `NOT_SIGNIFICANT`| fallback (no significant difference, but neither clearly underpowered)   |

### 1.2 Pairing strategy — explicit `unpaired`

Per Wave 195 P1 spec §3.3 (and §10.26 (e) honest disclosure): each arm
(Fast-DLLM, AB-Cache, LeDiFlow, FlowA) was evaluated as a **separate
experiment** with its own ODE trajectory. AGG rows are cross-experiment
aggregates, NOT within-seed paired diffs. Therefore:

* **Statistical test**: Welch's t-test (unequal-variance two-sample).
* **Cohen's `d_s`** (between-subject, pooled SD):
  `d = (mean_F - mean_B) / sqrt((var_B + var_F) / 2)`.
* **SE_delta** = `sqrt(var_B / n_B + var_F / n_F)`.
* **CI_95** = `delta ± 1.96 * SE_delta`.

### 1.3 Unit of replication — `n = 3` seeds per arm

For each arm × (NFE, metric) cell, we have:

* **Baseline arm** (Fast-DLLM / AB-Cache / LeDiFlow): 3 per-seed mean
  values from `wave{180,181,182}-p2-*-summary.csv` (filtered by `nfe`,
  excluding the AGG row).
* **Framework arm (FlowA)**: aggregate mean + SD across 3 seed means
  from `wave179-p4-aggregation.csv` (lineageflow rows filtered by `nfe`).

The Wave 195 P1 spec §3.1 labels this as `n_b = n_f = 90` referring to
the underlying record count (3 seeds × 30 records/seed). However, the
**unit of replication for the t-test is `n = 3`** (the 3 independent
seeds), since the per-record within-seed variance is NOT separately
reported for FlowA in the same per-seed CSVs. This matches the Wave
195 P2 R5a pattern (Two Moons W2 per-seed aggregates, n=3 per arm).
The `n_records_per_arm = 90` field is included in the JSON `extra`
for transparency.

### 1.4 Bonferroni correction

* `α_family = 0.05`.
* `α_per_cell = 0.05 / 12 = 0.004167` (12 cells: 3 baselines × 2 NFE × 2 metrics).
* `p_bonf = min(p_raw × 12, 1.0)`.

### 1.5 `min_effect_size`

* pLDDT (higher better): `min_effect_size = 0.01` (1 pp absolute on
  the pLDDT scale [0, 100]).
* scPerplexity (lower better): `min_effect_size = 0.01` (1 pp absolute
  on the scPerplexity scale).

---

## 2. Per-cell results

12 cells total. All 12 cells are **UNDERPOWERED** at the 1pp
`min_effect_size` threshold with n=3 per arm (this is the honest
finding; see §3 for why this differs from the Wave 195 P1 spec §3.6
expected verdicts).

| cell                          | baseline | metric  | NFE | Δ (F−B)        | Cohen's d_s | p_raw    | p_bonf   | observed power | power @ min_effect | verdict       |
|-------------------------------|----------|---------|----:|---------------:|------------:|---------:|---------:|---------------:|-------------------:|---------------|
| fastdllm_pLDDT_NFE100         | FastDLLM | pLDDT   | 100 | +6.925         | +4.52       | 0.0180   | 0.2160   | 0.9998         | 0.0500             | UNDERPOWERED  |
| fastdllm_pLDDT_NFE200         | FastDLLM | pLDDT   | 200 | +7.081         | +4.58       | 0.0126   | 0.1506   | 0.9999         | 0.0500             | UNDERPOWERED  |
| fastdllm_scPerplexity_NFE100  | FastDLLM | scPerp  | 100 | −0.422         | −0.30       | 0.7398   | 1.0000   | 0.0655         | 0.0500             | UNDERPOWERED  |
| fastdllm_scPerplexity_NFE200  | FastDLLM | scPerp  | 200 | −0.414         | −0.28       | 0.7554   | 1.0000   | 0.0637         | 0.0500             | UNDERPOWERED  |
| abcache_pLDDT_NFE100          | AB-Cache | pLDDT   | 100 | +3.938         | +0.97       | 0.3304   | 1.0000   | 0.2208         | 0.0500             | UNDERPOWERED  |
| abcache_pLDDT_NFE200          | AB-Cache | pLDDT   | 200 | +3.060         | +0.66       | 0.4878   | 1.0000   | 0.1278         | 0.0500             | UNDERPOWERED  |
| abcache_scPerplexity_NFE100   | AB-Cache | scPerp  | 100 | −0.959         | −0.85       | 0.3605   | 1.0000   | 0.1804         | 0.0500             | UNDERPOWERED  |
| abcache_scPerplexity_NFE200   | AB-Cache | scPerp  | 200 | −0.529         | −0.47       | 0.5949   | 1.0000   | 0.0894         | 0.0500             | UNDERPOWERED  |
| lediflow_pLDDT_NFE100         | LeDiFlow | pLDDT   | 100 | +4.376         | +1.10       | 0.2828   | 1.0000   | 0.2687         | 0.0500             | UNDERPOWERED  |
| lediflow_pLDDT_NFE200         | LeDiFlow | pLDDT   | 200 | +4.095         | +1.03       | 0.3089   | 1.0000   | 0.2416         | 0.0500             | UNDERPOWERED  |
| lediflow_scPerplexity_NFE100  | LeDiFlow | scPerp  | 100 | −0.559         | −0.41       | 0.6510   | 1.0000   | 0.0791         | 0.0500             | UNDERPOWERED  |
| lediflow_scPerplexity_NFE200  | LeDiFlow | scPerp  | 200 | −0.174         | −0.14       | 0.8767   | 1.0000   | 0.0533         | 0.0500             | UNDERPOWERED  |

### 2.1 Effect size summary

* **fastdllm pLDDT** (2 cells): large effect (`|d| ≈ 4.5`), Δ ≈ +7 pLDDT,
  observed power ≥ 0.999. Bonferroni fails (p_bonf ≈ 0.15-0.22 > 0.004167).
* **abcache pLDDT** (2 cells): moderate effect (`|d| ≈ 0.7-1.0`),
  Δ ≈ +3 pLDDT, observed power ≈ 0.13-0.22. Not even uncorrected
  significant (p_raw ≈ 0.33-0.49).
* **lediflow pLDDT** (2 cells): moderate effect (`|d| ≈ 1.0-1.1`),
  Δ ≈ +4 pLDDT, observed power ≈ 0.24-0.27. Not significant
  (p_raw ≈ 0.28-0.31).
* **scPerplexity** (6 cells, all baselines): small effect
  (`|d| ≈ 0.14-0.85`), observed power ≤ 0.18. Not significant
  (p_raw ≈ 0.36-0.88).

### 2.2 Direction summary

All 12 cells show FlowA in the winning direction:
* 6 pLDDT cells: Δ > 0 (FlowA wins on pLDDT for all 3 baselines × 2 NFE).
* 6 scPerplexity cells: Δ < 0 (FlowA wins on scPerplexity for all
  3 baselines × 2 NFE; lower better).

The direction is consistent across all 12 cells, even though none reach
Bonferroni-corrected significance at n=3.

---

## 3. Honest deviation from Wave 195 P1 spec §3.6 expected verdicts

The Wave 195 P1 spec §3.6 predicted "All 12 expected verdicts:
SUPPORTED" based on the assumption that "Effect sizes are very large
(`d > 1.5` for all cells), so post-hoc power ≥ 0.99 on every cell."

This prediction is incorrect for the actual data:

1. **Effect sizes are not all `d > 1.5`.** Only fastdllm pLDDT
   achieves `|d| > 1.5` (d ≈ 4.5). The other 10 cells have
   `|d| ∈ [0.14, 1.10]` — moderate to small effects, not "very large".
   The spec's claim of `d > 1.5` for all cells appears to have
   assumed per-record std rather than the per-seed std actually
   available in the source CSVs.

2. **With n=3 per arm, post-hoc power at min_effect_size ≈ 0.05 for
   every cell.** The "UNDERPOWERED at 1pp" verdict flag (precedence
   rank 2 in §1.1) is triggered unconditionally because the test
   cannot detect a 1pp effect with n=3 per arm — even with the
   observed effect being 1000× larger than 1pp. This is structurally
   the same situation as the Wave 195 P2 R-level table, where all 7
   R-level cells are also flagged UNDERPOWERED (except R2 which is
   REGRESSES on a composite byte-stable cell with effectively
   infinite power).

3. **The fastdllm pLDDT cells come closest to SUPPORTED but still
   fail Bonferroni.** With `p_raw ≈ 0.013-0.018` and `α_bonf = 0.004167`,
   the Bonferroni-corrected p ≈ 0.15-0.22 is well above α. To reach
   Bonferroni significance, we'd need either a smaller p_raw (more
   seeds) or a larger effect (larger Δ / smaller SE).

### 3.1 Implications

This is an **honest limitation** of the Wave 180/181/182 data: with
n=3 seeds per arm and per-seed variance inflated by the lineageflow
between-seed heterogeneity (seeds {42, 43, 44} produce quite different
pLDDT ranges, e.g., 34.5-45.2 for AB-Cache at NFE=100), the 4-arm
head-to-head cannot formally establish statistical significance at
the Bonferroni-corrected α=0.004167 threshold.

The **direction** is robust (all 12 cells show FlowA winning in the
expected direction, consistent with §10.26/§10.27/§10.30 in the
paper-draft), but the **magnitude of evidence** is not enough to call
any individual cell Bonferroni-significant at n=3.

### 3.2 Recommended follow-up

To upgrade the 4-arm head-to-head from "all directions consistent" to
"some cells Bonferroni-significant":

* **Increase seed count** to n=10+ per arm (R5a R-level cell pattern
  with 10 seeds reaches Bonferroni significance at the same effect
  size).
* **Pair all four arms at the generation step** to convert from
  unpaired Welch's t-test (large SE due to cross-experiment
  variance) to paired t-test (small SE due to within-seed diffs).
  This was already called out as a Wave 5+ follow-up in CLM-050
  caveat (1).
* **Or**: relax the Bonferroni threshold to per-axis
  `α_per_axis = 0.05 / 4 = 0.0125` (4 cells per axis instead of 12)
  to gain statistical power while still correcting for multiple
  testing.

None of these follow-ups block the Wave 195 P3 deliverable. The
script and JSON correctly compute and report the actual statistics
with the spec-prescribed methodology; the "all UNDERPOWERED" finding
is itself a meaningful result that documents the small-N limitation
of the Wave 180/181/182 data.

---

## 4. Output JSON spec

```json
{
  "4arm_power_table": [
    {"cell": "fastdllm_pLDDT_NFE100", "baseline_arm": "FastDLLM", "framework_arm": "FlowA",
     "metric": "pLDDT", "nfe": 100, "higher_better": true, "pairing": "unpaired",
     "baseline_mean": 36.9037, "framework_mean": 43.8284, "n_b": 3, "n_f": 3,
     "delta": 6.9247, "delta_se": 1.2507,
     "ci_95": [4.4733, 9.3761],
     "p_value_raw": 0.0180, "p_value_bonferroni": 0.2160,
     "cohens_d_z": 4.5205,
     "post_hoc_power": 0.9998, "post_hoc_power_min_effect": 0.0500,
     "min_effect_size": 0.01, "alpha_bonferroni": 0.004167,
     "verdict": "UNDERPOWERED",
     "data_source": "verification_outputs/wave180-p2-fastdllm-summary.csv + verification_outputs/wave179-p4-aggregation.csv",
     "extra": {"t_stat": 5.9150, "b_per_seed": [36.248, 37.045, 37.419],
               "f_per_seed_std": 2.0821, "b_var": 0.358, "f_var": 4.335,
               "pooled_sd": 1.532, "higher_better": true, "n_records_per_arm": 90}
    },
    ...
  ],
  "summary": {
    "n_cells": 12,
    "n_supported_flowa_wins": 0,
    "n_regresses": 0,
    "n_underpowered": 12,
    "n_tie": 0,
    "n_not_significant": 0,
    "alpha_family": 0.05,
    "alpha_bonferroni": 0.004166666666666667,
    "n_tests_for_bonferroni": 12,
    "n_baselines": 3, "n_metrics": 2, "n_nfe": 2
  },
  "methodology": {
    "statistical_test": "Welch's t-test (unequal-variance two-sample)...",
    "unit_of_replication": "n = 3 seeds per arm (seeds {42, 43, 44})...",
    "ci_95_formula": "delta ± 1.96 * SE_delta",
    "cohens_d_kind": "d_s (between-subject, pooled SD)",
    "post_hoc_power_formula": "Cohen 1988 §2.4: power = Phi(|delta|/SE - z_alpha/2) + Phi(-|delta|/SE - z_alpha/2)",
    "bonferroni_rule": "alpha_per_cell = 0.05 / 12 = 0.004167",
    "verdict_precedence": [...],
    "min_effect_size_policy": {"pLDDT_pp": 0.01, "scPerplexity_pp": 0.01},
    "references": ["Cohen 1988", "Welch 1947", "Bonferroni 1935", "Hunter & Levine 2024", "Wave 195 P1 spec"]
  },
  "commit_sha": "ff6ae12003c44e9d81db702cc89e622f14039289"
}
```

---

## 5. Acceptance gates

| #  | gate                                                                  | status |
|----|-----------------------------------------------------------------------|--------|
| 1  | Spec referenced (`docs/audit/wave195-p1-power-spec.md` §3 Table B)    | PASS   |
| 2  | 12 cells (3 baselines × 2 NFE × 2 metrics) loaded and computed       | PASS   |
| 3  | Per-arm aggregates computed from per-seed means (n=3 unit)            | PASS   |
| 4  | Bonferroni α = 0.05 / 12 = 0.004167 applied per cell                 | PASS   |
| 5  | `min_effect_size = 0.01` per axis (pLDDT + scPerp)                    | PASS   |
| 6  | Cohen's `d_s` (between-subject pooled SD) computed per cell           | PASS   |
| 7  | Post-hoc power (observed + at min_effect_size) computed per cell      | PASS   |
| 8  | Verdict precedence matches Wave 195 P1 spec §1.1                      | PASS   |
| 9  | CSV + JSON outputs written with full per-cell + summary + methodology | PASS   |
| 10 | Audit doc created (`docs/audit/wave195-p3-4arm-power.md`)             | PASS   |
| 11 | Honest finding documented (all 12 UNDERPOWERED; deviation from P1     | PASS   |
|    | §3.6 expected verdicts explained)                                     |        |
| 12 | commit_sha `ff6ae12` pinned in JSON output                            | PASS   |

All 12 gates PASS.

---

## 6. References

* `docs/audit/wave195-p1-power-spec.md` §3 — Table B 4-arm head-to-head
  spec, methodology, expected verdicts.
* `tools/wave195_p2_r_level_power.py` — reference implementation of the
  per-cell power analysis machinery (verdict precedence, post-hoc power
  formula, Bonferroni correction).
* `verification_outputs/wave179-p4-aggregation.csv` — FlowA per-NFE
  aggregate (mean, std across 3 seed means, n_seeds).
* `verification_outputs/wave180-p2-fastdllm-summary.csv` — Fast-DLLM
  per-seed summary (seeds {42, 43, 44}; NFE {100, 200}).
* `verification_outputs/wave181-p2-abcache-summary.csv` — AB-Cache
  per-seed summary.
* `verification_outputs/wave182-p2-lediflow-summary.csv` — LeDiFlow
  per-seed summary.
* `docs/CLAIMS.md` CLM-050 caveat (1) — already calls out the cross-
  experiment (unpaired) limitation of the Wave 181 4-arm comparison
  and identifies a Wave 5+ paired-t-test follow-up.
* Cohen 1988 *Statistical Power Analysis* §2.4 — post-hoc power formula.
* Welch 1947 — unequal-variance t-test.
* Bonferroni 1935 — multiple-testing correction.
* Hunter & Levine 2024 — modern power analysis for ML benchmarks.
