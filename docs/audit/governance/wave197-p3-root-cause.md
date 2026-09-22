# Wave 197 P3 — Root-cause analysis: why n=100 sweep cannot upgrade Table B

**Date:** 2026-09-19
**Branch:** main (HEAD `af2fb74`, post-Wave-197-P2-abort)
**Status:** HONEST FINDING — n=100 sweep (the Wave 197 P2 aborted plan) would NOT upgrade the verdict distribution. Effect size, not sample size, is the binding constraint.

---

## TL;DR

The Wave 197 P2 sweep was aborted (multi-day wall time) because it cannot fit in the available subagent budget. The deeper issue, identified in the P2 progress doc and confirmed by this root-cause analysis:

| n=100 sweep outcome (3 scenarios) | SUPPORTED | UNDERPOWERED | REGRESSES |
|---|---:|---:|---:|
| Pessimistic (std_d unchanged) | 2 | 14 | 0 |
| Realistic   (std_d × 0.7)       | 2 | 14 | 0 |
| Optimistic  (std_d × 0.316)     | 2 | 14 | 0 |
| **Wave 196 P4 baseline (n=10 records, 30 seeds)** | **2** | **14** | **0** |

**Delta: 0 cells upgraded.** The n=100 sweep is a no-op for the verdict distribution.

**Alternative: more seeds (not more records).** Predicted outcome at n=300 paired seeds (10× current), R=10:
- 2 SUPPORTED + 13 UNDERPOWERED + **1 REGRESSES** (`fastdllm_pLDDT_NFE100`)
- The framework has a slight per-seed pLDDT regression vs fastdllm at NFE=100 that is currently masked by sample size. More data **exposes** this regression rather than upgrading SUPPORTED count.

At n=1000 paired seeds: 3 SUPPORTED + 7 UNDERPOWERED + 6 REGRESSES — net loss. The effect sizes have mixed signs across cells.

---

## 1. Why n=100 records/seed cannot help

The paired t-test at the seed level is invariant to `n_records_per_seed` in the dominant regime:

```
paired_diff_per_seed = mean_metric_baseline(seed) − mean_metric_framework(seed)
                    = (1/R) * Σ_r record_baseline(seed, r) − (1/R) * Σ_r record_framework(seed, r)
```

The variance of `paired_diff_per_seed` decomposes as:

```
Var(paired_diff_per_seed) = Var_seed(μ_b(seed) − μ_f(seed)) + (1/R) * Var_record(b − f)
                            \_____________________________/      \______________________/
                              seed-to-seed variance              per-record variance / R
```

For protein flow matching with `n_seeds=30`, `R=10`:
- **Seed-to-seed variance dominates**: μ_b(seed) varies from ~33 to ~62 (pLDDT, vanilla baseline) across seeds — this is the seed-to-seed RNG variation.
- **Per-record variance is small**: each seed produces 10 records with similar quality; the per-record noise averages out fast.

So `Var(paired_diff_per_seed) ≈ Var_seed(μ_b − μ_f)`, which is essentially **independent of R**.

At R=100 vs R=10: only the per-record variance term shrinks, and it's already small. The seed-to-seed variance term is unchanged. **Cohen's d_z is unchanged.**

### Numerical confirmation

For the 14 UNDERPOWERED cells (max d_z = 0.226):

| n=100 scenario | std_d scaling | max d_z upgrade | Bonferroni threshold met? |
|---|---|---:|---:|
| Pessimistic | 1.000× | 0% | 0/14 |
| Realistic   | 0.700× | 43% | 0/14 |
| Optimistic  | 0.316× | 216% | 0/14 |

Even in the most optimistic scenario (all variance is per-record, std_d × sqrt(10/100) = 0.316×), the resulting d_z is still 0.05–0.7, and Bonferroni-corrected p stays > 0.003125 for all 14 cells (some cells even flip to REGRESSES due to small negative d_z being amplified).

---

## 2. Why more seeds exposes regressions (not upgrades)

The honest per-cell math (reproduced in `tools/wave197_p3_root_cause_analysis.py`):

```
t_stat(n) = d_z * sqrt(n)    # Cohen's d_z unchanged, n increases
p_value   = 2 * scipy.stats.t.sf(abs(t_stat), n-1)
```

| n_seeds | SUPPORTED | UNDERPOWERED | REGRESSES | new REGRESSES cells |
|---:|---:|---:|---:|---|
| 30   | 2 | 14 | 0 | (baseline) |
| 60   | 2 | 14 | 0 | — |
| 100  | 2 | 14 | 0 | — |
| 300  | 2 | 13 | **1** | `fastdllm_pLDDT_NFE100` |
| 500  | 3 | 9 | **4** | `fastdllm_pLDDT_NFE100`, `abcache_scPerplexity_NFE50`, `lediflow_pLDDT_NFE50`, `lediflow_scPerplexity_NFE50` |
| 1000 | 3 | 7 | **6** | + `fastdllm_pLDDT_NFE50`, `abcache_pLDDT_NFE100` |

**Net effect: more seeds does NOT upgrade SUPPORTED.** It exposes pre-existing small regressions where the framework is statistically slightly worse than baselines on certain cells:

- `fastdllm_pLDDT_NFE100` (d_z = -0.226, framework slightly worse on pLDDT vs fastdllm at higher NFE)
- `lediflow_pLDDT_NFE50`, `lediflow_scPerplexity_NFE50` (d_z = ±0.191, mixed signs)
- `abcache_scPerplexity_NFE50` (d_z = -0.195, framework slightly worse)

This is the **honest per-seed finding**: FlowA framework is statistically tied with FastDLLM/AB-Cache/LeDiFlow on per-seed pLDDT/scPerplexity. The framework's value-add is NOT a per-seed metric uplift over these baselines at the LineageFlow evaluation protocol.

---

## 3. What's actually winning at the per-seed level

Looking at the per-seed breakdown (Wave 196 P2 data, NFE=50, common seeds 42-71):

| arm | mean pLDDT (over 30 seeds) | best-seed count | worst-seed count |
|---|---:|---:|---:|
| vanilla | 40.71 | 10 | 20 |
| fastdllm | 42.12 | 12 | 18 |
| abcache | 41.68 | 13 | 17 |
| lediflow | 42.34 | 16 | 14 |
| flowa | 41.17 | 11 | 19 |

Each arm is best on some seeds and worst on others. **No arm consistently wins across all seeds.** The per-seed variance is dominated by RNG state (different sequences are easier/harder for each solver).

For scPerplexity (lower better):

| arm | mean scPerplexity (over 30 seeds) | std |
|---|---:|---:|
| vanilla | 17.76 | 0.76 |
| fastdllm | 13.87 | 1.00 |
| abcache | 14.11 | 0.95 |
| lediflow | 13.65 | 1.05 |
| flowa | 13.89 | 0.85 |

All four solvers (FastDLLM/AB-Cache/LeDiFlow/FlowA) produce scPerplexity ~13.5-14.1, indistinguishable at the per-seed level. Vanilla (no solver) produces ~17.8, much higher. **The framework is competitive with other solvers, but no framework wins on this metric.**

---

## 4. Recommendations

### 4.1 (RECOMMENDED) Honest reframe in CLM-061

Update CLM-061 status from:
> "2 SUPPORTED + 14 UNDERPOWERED at n=30 paired t-test (4-arm with +Vanilla control) — paper-level significance on the 14 underpowered cells requires n ≥ 100 seeds (Wave 197+ scope)"

to:
> "2 SUPPORTED + 14 UNDERPOWERED at n=30 paired t-test (4-arm with +Vanilla control). The 14 UNDERPOWERED cells are bounded by per-seed effect size (Cohen's d_z = 0.05–0.23), not sample size. Predicted verdict distribution at n=100 records/seed or n=300 paired seeds is unchanged or NET WORSE (exposes regressions). Paper-level verdict: FlowA framework is competitive with FastDLLM/AB-Cache/LeDiFlow on per-seed pLDDT/scPerplexity; value-add is NOT a per-seed metric uplift at the LineageFlow evaluation protocol."

This is honest and matches the data.

### 4.2 (ALTERNATIVE) Investigate framework-level changes that DO shift per-seed distribution

The framework's value-add is in:
1. Restart policy + re-inference for difficult seeds
2. Adaptive step-size control
3. Theoretical guarantees from JMAA Theorem 1

If the goal is per-seed pLDDT uplift, we need:
- A solver that genuinely improves per-seed metric distributions (not just framework overhead)
- OR a different evaluation protocol that captures what the framework actually improves

This requires framework-level work, not more sampling.

### 4.3 (OPTIONAL) Bayesian analysis / equivalence testing (TOST)

For the 14 UNDERPOWERED cells, instead of trying to prove "framework > baseline", we can prove "framework ≈ baseline" with TOST (two one-sided tests) at a sensible equivalence bound (e.g., ±2 pp for pLDDT, ±0.5 for scPerplexity). This would convert the 14 cells from "we don't know" to "we know they're tied within ±2 pp".

But this is a paper-presentation choice, not a sample-size fix.

### 4.4 (NOT RECOMMENDED) n=100 records/seed sweep

The Wave 197 P2 sweep was aborted because:
- Multi-day wall time (18-37 h per P1 estimate)
- 113/300 cells generated before abort; 0/113 evals completed
- Even if completed: 0 cells upgraded (per this analysis)

**Conclusion: do not relaunch n=100 sweep.** The math says it cannot fix the issue.

---

## 5. Output JSON

```json
{
  "root_cause_finding": "n=100 records/seed cannot upgrade Table B verdict distribution. Effect size (Cohen's d_z ~ 0.05-0.23) is the binding constraint; increasing records/seed does not change d_z. Alternative n=300 paired seeds NET WORSE (exposes regressions). Honest reframe is the right answer.",
  "wave196_p4_baseline": {"SUPPORTED": 2, "UNDERPOWERED": 14, "REGRESSES": 0},
  "n100_sweep_predicted_outcomes": {
    "pessimistic": {"SUPPORTED": 2, "UNDERPOWERED": 14, "REGRESSES": 0, "delta_supported": 0},
    "realistic":   {"SUPPORTED": 2, "UNDERPOWERED": 14, "REGRESSES": 0, "delta_supported": 0},
    "optimistic":  {"SUPPORTED": 2, "UNDERPOWERED": 14, "REGRESSES": 0, "delta_supported": 0}
  },
  "alternative_n_seeds_predicted_outcomes": {
    "n_60":  {"SUPPORTED": 2, "UNDERPOWERED": 14, "REGRESSES": 0},
    "n_100": {"SUPPORTED": 2, "UNDERPOWERED": 14, "REGRESSES": 0},
    "n_300": {"SUPPORTED": 2, "UNDERPOWERED": 13, "REGRESSES": 1, "new_regresses": ["fastdllm_pLDDT_NFE100"]},
    "n_500": {"SUPPORTED": 3, "UNDERPOWERED": 9,  "REGRESSES": 4, "new_regresses": ["fastdllm_pLDDT_NFE100", "abcache_scPerplexity_NFE50", "lediflow_pLDDT_NFE50", "lediflow_scPerplexity_NFE50"]},
    "n_1000":{"SUPPORTED": 3, "UNDERPOWERED": 7,  "REGRESSES": 6, "new_regresses": ["+ fastdllm_pLDDT_NFE50", "+ abcache_pLDDT_NFE100"]}
  },
  "comparison_to_wave196_p4": {
    "wave196_supported": 2,
    "wave197_supported_n100_pessimistic": 2,
    "delta_supported_n100_pessimistic": 0,
    "delta_supported_n300": 0,
    "delta_supported_n1000": 1,
    "delta_regresses_n300": 1,
    "delta_regresses_n1000": 6
  },
  "recommended_fix": "Honest reframe in CLM-061: acknowledge TIE/UNDERPOWERED for 14 cells, no longer claim 'requires n ≥ 100 seeds' (the math shows it doesn't help).",
  "commit_sha": "af2fb74"
}
```

---

## 6. Per-cell predictions

Full per-cell predictions in `verification_outputs/wave197-p3-root-cause-analysis.{csv,json}`. Summary:

- All 14 UNDERPOWERED cells stay UNDERPOWERED at n=100 records/seed (any scenario).
- 1 cell (`fastdllm_pLDDT_NFE100`, d_z = -0.226) flips to REGRESSES at n=300+ paired seeds.
- 4 additional cells flip to REGRESSES at n=500+ paired seeds.
- The framework's pLDDT effect vs fastdllm/abcache/lediflow is consistently slightly negative or near-zero at the per-seed level; scPerplexity effect is near-zero (framework is competitive, not winning).

---

## 7. Honest verdict

The FlowA framework's value-add at the LineageFlow evaluation protocol is NOT a per-seed pLDDT/scPerplexity uplift over FastDLLM/AB-Cache/LeDiFlow. The 14/16 UNDERPOWERED cells are an honest reflection of this finding. Increasing sample size does not change this; it exposes pre-existing small regressions.

The honest paper-level claim for Table B is:
> "FlowA framework is competitive with FastDLLM, AB-Cache, and LeDiFlow on per-seed pLDDT and scPerplexity at the LineageFlow protein evaluation protocol. The 2 SUPPORTED cells (vanilla_scPerplexity) reflect the framework's value over no-distillation control; the 14 UNDERPOWERED cells reflect statistical ties with other solvers at the per-seed level. This is consistent with the framework's design goal (re-inference + adaptive restart for difficult seeds, not a different per-seed metric distribution)."

---

## 8. CLM-061 status change proposal

Update CLM-061 from:

> "Wave 196 P4 verdict transitions this claim from '12/12 UNDERPOWERED at n=3 unpaired' to '2 SUPPORTED + 14 UNDERPOWERED at n=30 paired t-test (4-arm with +Vanilla control)' — **paper-level significance on the 14 underpowered cells requires n ≥ 100 seeds (Wave 197+ scope)**"

to:

> "Wave 196 P4 verdict transitions this claim from '12/12 UNDERPOWERED at n=3 unpaired' to '2 SUPPORTED + 14 UNDERPOWERED at n=30 paired t-test (4-arm with +Vanilla control)'. **Wave 197 P3 root-cause analysis confirms the 14 UNDERPOWERED cells are bounded by per-seed effect size (Cohen's d_z = 0.05–0.23), not sample size. Predicted verdict distribution at n=100 records/seed (P1-P3 plan) is unchanged (2/16 SUPPORTED). Predicted verdict at n=300 paired seeds is NET WORSE (1 cell flips to REGRESSES). The framework's value-add is not per-seed metric uplift over FastDLLM/AB-Cache/LeDiFlow at the LineageFlow evaluation protocol.**"