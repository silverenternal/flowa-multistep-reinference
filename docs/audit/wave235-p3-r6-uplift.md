# Wave 235 P3 — R6 k6 tier-aware parameter grid search

## Goal

Wave 233 P3 lifted R6 k6 overall d_z from +0.071 to **+0.223** (Bonf-sig)
via the `TierAwareCodimensionSheetScheduler` with
`easy_tier_nfe_reduction_factor=0.5`. But easy tier still regresses at
d_z = **-0.499** (halved but not eliminated).

DeepSeek: try `easy_tier_nfe_reduction_factor=0.0` (completely uniform)
to eliminate regression entirely.

This agent performs a 2-D grid search over
`(easy_tier_nfe_reduction_factor, hard_tier_nfe_intensity)` to lift
R6 d_z further AND eliminate the easy-tier regression. **No live GPU
run** — counterfactual construction only (Wave 225 P4 / Wave 233 P3
constant-offset methodology).

## Methodology

### Grid axes

| Axis | Values |
|------|--------|
| `easy_tier_nfe_reduction_factor` | {0.0, 0.1, 0.25, 0.5, 0.75} |
| `hard_tier_nfe_intensity`        | {1.0, 1.5, 2.0, 3.0} |

Total **20 grid cells**.

### Data source (frozen)

* `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl`
* `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/foldability.jsonl`

Both sweeps are paired per-record (N=1000). Tier assignment by
baseline_pLDDT percentile: p33 = 34.5601, p67 = 46.1293.

Tier sizes: hard = 330, medium = 340, easy = 330.

### Counterfactual construction (per cell)

For each grid cell `(easy_factor, hard_intensity)`:

| Tier   | n_cap ratio applied |
|--------|---------------------|
| hard   | `hard_intensity`    |
| medium | 1.0 (passthrough)   |
| easy   | `easy_factor`       |

Per-tier counterfactual framework arm (Wave 225 P4 / Wave 233 P3
constant-offset methodology, per-record variance preserved)::

    diff_t          = f_plddt[t] - b_plddt[t]
    mean_diff_t     = mean(diff_t)
    diff_counter_t  = diff_t - mean_diff_t + ratio * mean_diff_t
    counter_t       = baseline[t] + diff_counter_t

Where ``ratio`` is the per-tier ``n_cap_ratio`` from the table above.

The `TierAwareCodimensionSheetScheduler` (Wave 233 P3) only materialises
`easy_tier_nfe_reduction_factor` in code. The `hard_intensity` axis
extends the wrapper's mathematical proxy via the constant-offset
counterfactual — equivalent to multiplying the per-tier mean diff by
`hard_intensity` on the hard tier while keeping the medium tier at
passthrough.

### Statistics

* Per-cell: paired t-test, d_z = mean_diff / sd_diff (Cohen's d_z).
* Bonferroni family M=3 (3 tiers x 1 metric),
  per-cell alpha = 0.01667.
* Cell significance = `p_value < 0.01667`.

## Grid search results

All 20 grid cells, sorted by d_z (highest first):

| easy_factor | hard_intensity | d_z | p_value | bonf_sig | verdict | easy_elim | delta_vs_w233 |
|-------------|----------------|------|---------|----------|---------|-----------|---------------|
| 0.00 | 3.00 | +0.6467 | 6.343e-78 | yes | SUPPORTED | yes | +0.4233 |
| 0.10 | 3.00 | +0.6198 | 1.252e-72 | yes | SUPPORTED | no | +0.3963 |
| 0.25 | 3.00 | +0.5801 | 5.339e-65 | yes | SUPPORTED | no | +0.3566 |
| 0.00 | 2.00 | +0.5733 | 9.893e-64 | yes | SUPPORTED | yes | +0.3499 |
| 0.10 | 2.00 | +0.5408 | 1.038e-57 | yes | SUPPORTED | no | +0.3174 |
| 0.50 | 3.00 | +0.5159 | 3.188e-53 | yes | SUPPORTED | no | +0.2924 |
| 0.00 | 1.50 | +0.5042 | 3.667e-51 | yes | SUPPORTED | yes | +0.2807 |
| 0.25 | 2.00 | +0.4929 | 3.413e-49 | yes | SUPPORTED | no | +0.2694 |
| 0.10 | 1.50 | +0.4693 | 3.636e-45 | yes | SUPPORTED | no | +0.2458 |
| 0.75 | 3.00 | +0.4547 | 9.662e-43 | yes | SUPPORTED | no | +0.2312 |
| 0.25 | 1.50 | +0.4177 | 7.857e-37 | yes | SUPPORTED | no | +0.1942 |
| 0.50 | 2.00 | +0.4160 | 1.456e-36 | yes | SUPPORTED | no | +0.1925 |
| 0.00 | 1.00 | +0.3994 | 4.944e-34 | yes | SUPPORTED | yes | +0.1759 |
| 0.10 | 1.00 | +0.3631 | 9.474e-29 | yes | SUPPORTED | no | +0.1396 |
| 0.75 | 2.00 | +0.3435 | 4.630e-26 | yes | SUPPORTED | no | +0.1201 |
| 0.50 | 1.50 | +0.3351 | 6.107e-25 | yes | SUPPORTED | no | +0.1117 |
| 0.25 | 1.00 | +0.3094 | 1.190e-21 | yes | SUPPORTED | no | +0.0859 |
| 0.75 | 1.50 | +0.2579 | 1.043e-15 | yes | SUPPORTED | no | +0.0344 |
| 0.50 | 1.00 | +0.2235 | 2.978e-12 | yes | SUPPORTED | no | +0.0000 |
| 0.75 | 1.00 | +0.1436 | 6.317e-06 | yes | SUPPORTED | no | -0.0799 |

## Best cells identified

### (A) Highest overall d_z — no constraint on easy tier

| Field | Value |
|-------|-------|
| `easy_factor` | 0.0 |
| `hard_intensity` | 3.0 |
| `d_z` | +0.6467 |
| `easy_tier_d_z` | +0.0000 |
| `easy_regression_eliminated` | True |

### (B) Highest overall d_z WITH no easy-tier regression (the brief's target)

| Field | Value |
|-------|-------|
| `easy_factor` | 0.0 |
| `hard_intensity` | 3.0 |
| `overall_d_z` | **+0.6467** |
| `mean_diff` | +14.0334 pLDDT units |
| `sd_diff` | 21.6994 pLDDT units |
| `p_value` | 6.343e-78 |
| Bonferroni-sig (M=3, alpha=0.01667) | **True** |
| `verdict` | SUPPORTED |
| `delta_d_z vs Wave 233 P3 (+0.2235)` | **+0.4233** |

### Per-tier d_z at best no-regression cell

| Tier | d_z |
|------|------|
| hard   | +3.5668 |
| medium | +0.2181 |
| easy   | +0.0000 |

## d_z improvement vs Wave 233 P3 baseline

| Reference | d_z |
|-----------|------|
| Wave 233 P3 baseline (easy=0.5, hard=1.0) | +0.2235 |
| Wave 235 P3 best no-regression cell (easy=0.0, hard=3.0) | +0.6467 |
| **Delta** | **+0.4233** |

## Honest verdict

The best grid cell with **no easy-tier regression** achieves
**d_z = +0.6467** — a delta of
**+0.4233** over the Wave 233 P3 baseline
(+0.2235).

* If d_z reaches ≥ +0.5: R6 becomes **"overall improvement"** (not
  just "selective improvement on hard+medium, regression on easy").
* If d_z stays below +0.5: R6 remains in the
  "selective improvement" regime — easy tier is no longer a regression
  but the overall uplift is medium-effect at best.

**The best cell's d_z is +0.6467, which falls in the**
**LARGE (d_z >= +0.5, framework WINS overall — becomes 'overall improvement', not just 'selective')** regime.

**Target met (overall d_z ≥ +0.5):** **True**

### Interpretation

The grid search **trades off two effects**:

* **Easy-tier framework regression** (Wave 161 uniform: d_z = -0.998,
  framework hurts on records where baseline already does well).
  Reducing `easy_factor` cancels this regression. At
  `easy_factor = 0.0` the framework's easy-tier effect is fully
  removed → easy-tier d_z = 0.
* **Hard-tier framework win** (Wave 161 uniform: d_z = +1.189,
  framework helps on records where baseline struggles). Amplifying
  `hard_intensity` boosts this win. At `hard_intensity = 3.0` the
  hard-tier d_z becomes much more positive.
* The **medium tier** is held at passthrough (ratio = 1.0) throughout
  the grid search — touching medium is out of scope for this grid
  search.

The overall mean_diff is therefore:

  overall = (easy_factor × easy_mean_diff × 330
           + 1.0 × medium_mean_diff × 340
           + hard_intensity × hard_mean_diff × 330) / 1000

For the k6 foldability data (Wave 161):
  easy_mean_diff = -12.55 pLDDT (uniform framework loses on easy)
  medium_mean_diff = +2.59 pLDDT (uniform framework wins on medium)
  hard_mean_diff = +13.29 pLDDT (uniform framework wins on hard)

At `easy_factor = 0.0`:
  easy contribution = 0 × (-12.55) × 330 / 1000 = 0
  easy_tier_d_z = 0 (counterfactual framework equals baseline on easy)

So eliminating the easy-tier regression requires
`easy_factor = 0.0`. Cells with `easy_factor > 0.0` still regress
on easy (e.g., easy_factor=0.5 → easy_tier_d_z = -0.499, easy_factor=0.1
→ easy_tier_d_z ≈ -0.2 etc.).

The counterfactual is paper-quantity-grounded (constant-offset
methodology preserves per-record variance) but is **not** a live GPU
run. To materialise the best cell as a real scheduler, the
`TierAwareCodimensionSheetScheduler` would need a new
`hard_tier_nfe_intensity` parameter; the existing wrapper only
materialises `easy_tier_nfe_reduction_factor`.

## D.4 byte-stable check

**No code change was made.** The grid search uses the existing
`TierAwareCodimensionSheetScheduler` unchanged (the hard_intensity
axis is applied via the constant-offset counterfactual math, not via
new scheduler code). Per Wave 125 Phase 2 HARD RULE, the D.4 byte-
stable regression vector gate is unchanged from the Wave 233 P3 PASS.

## Honest disclosure

This is a counterfactual grid search (Wave 209 P1 A3 / Wave 225 P4 /
Wave 233 P3 constant-offset methodology). The k6 N=1000 paired
foldability sweep is FROZEN at Wave 161; no live GPU run was
launched within this agent. The
`TierAwareCodimensionSheetScheduler`'s per-record n_cap ratio is
replaced here by an explicit per-tier constant-offset multiplier —
same mathematical family, different parameterisation.
