# Wave 199 P3: LineageFlow difficulty-stratified per-record paired t-test

## Honest finding: BLOCKED-ON-DATA — N=1000 sweep was killed

### Source data status

The Wave 199 P3 task spec called for N=1000 per-record paired data at:

  `verification_outputs/wave199-p2-lineageflow-n1000/{baseline,framework}/{fold,sc}/*.jsonl`

Inspection of that directory on 2026-09-19:

```
wave199-p2-lineageflow-n1000/baseline/fold/   (empty)
wave199-p2-lineageflow-n1000/baseline/sc/     (empty)
wave199-p2-lineageflow-n1000/framework/fold/  (empty)
wave199-p2-lineageflow-n1000/framework/sc/    (empty)
```

The Wave 199 P2 script (`scripts/wave199_p2_lineageflow_per_record_paired.py`) was authored pointing at this directory, but the N=1000 sweep was **killed for CPU wallclock** per Wave 84 lineageflow_n1000_omegafold notes:

> "CPU wallclock for N=1000 OmegaFold + ESM-IF was estimated >40 hours per arm; smoke test N=5 used as proof-of-pipeline."

The only LineageFlow per-record data that exists on disk is the **N=5 smoke subset** at:

  `verification_outputs/lineageflow_n1000_omegafold_q4_2026/{baseline,framework}/{fold,sc}/*.jsonl`

This is exactly the data Wave 198 P2/P3 already analyzed (with the same `lineageflow_omegafold` dataset label) and found TIE on both metrics because baseline and framework per-record values are **identical** for each qid in that smoke run.

### Per-record paired t-test results (LineageFlow)

Operates on the N=5 smoke data (the only lineageflow per-record data on disk).

| metric | N | mean_diff | sd_diff | t | df | p_value_raw | d_z | verdict |
|---|---|---|---|---|---|---|---|---|
| plddt_mean | 5 | 0.000000 | 0.0000 | 0.0000 | 4 | 1.000 | 0.0000 | TIE |
| sc_perplexity | 5 | 0.000000 | 0.0000 | 0.0000 | 4 | 1.000 | 0.0000 | TIE |

Bonferroni alpha = 0.05/2 = 0.025. Both metrics fail to reject H0 (mean_diff = 0). Verdict: TIE per Wave 193 P4 precedence (|d_z| < 0.05).

### Difficulty-stratified results (LineageFlow N=5)

Tier boundaries (33rd, 67th baseline_pLDDT percentile): [43.798, 51.815].

Tier sizes:
- hard: n=2 (q2: plddt=41.17, q4: plddt=32.44)
- medium: n=1 (q0: plddt=49.39) — too small for t-test (SKIP)
- easy: n=2 (q1: plddt=52.96, q3: plddt=59.03)

| tier | metric | n | mean_baseline | mean_framework | mean_diff | d_z | p_value_raw | verdict |
|---|---|---|---|---|---|---|---|---|
| hard | plddt_mean | 2 | 36.801 | 36.801 | 0.000 | 0.000 | 1.000 | TIE |
| hard | sc_perplexity | 2 | 19.254 | 19.254 | 0.000 | 0.000 | 1.000 | TIE |
| medium | plddt_mean | 1 | (skipped, n<2) |
| medium | sc_perplexity | 1 | (skipped, n<2) |
| easy | plddt_mean | 2 | 55.993 | 55.993 | 0.000 | 0.000 | 1.000 | TIE |
| easy | sc_perplexity | 2 | 12.702 | 12.702 | 0.000 | 0.000 | 1.000 | TIE |

Bonferroni alpha = 0.05/6 = 0.00833.

Monotone pattern test: hard > medium > easy in |d_z| → **NOT TESTABLE** (medium tier skipped due to N=1; all tiers TIE).

### Cross-adapter consistency check (vs k6_w161 from Wave 198 P3)

k6_foldability_w161 (Wave 198 P3, N=1000):
- plddt_mean: hard d_z=+1.19, medium +0.22, easy -1.00 → hard > medium > easy in d_z ✓
- sc_perplexity: hard d_z=-1.03, medium -1.14, easy -1.14 → monotone in |d_z|: |hard|≈|medium|≈|easy| ≈ 1.0

LineageFlow N=5 (Wave 199 P3): all tiers TIE on both metrics — comparison is **VACUOUS** because the framework adapter produced no observable per-record difference on the smoke run (baseline values equal framework values for every qid).

### Conclusion

**Wave 199 P3 is BLOCKED-ON-DATA for LineageFlow**: N=1000 sweep was killed; only N=5 smoke data exists; that data shows identical baseline/framework values → no statistical signal can be detected.

The Wave 199 P3 outputs (4 files) document this honestly:
- `wave199-p3-lineageflow-per-record.csv`
- `wave199-p3-lineageflow-per-record.json`
- `wave199-p3-lineageflow-strata.csv`
- `wave199-p3-lineageflow-strata.json`

For LineageFlow N=1000 strata analysis to be meaningful, the N=1000 sweep must be re-run — but Wave 84 lineageflow_n1000_omegafold notes estimate >40 hours per arm on CPU, which is the original reason the sweep was killed. A GPU-accelerated lineageflow re-run (e.g., 5090) would be needed to produce the N=1000 per-record paired data this analysis requires.

### Supersession status

- Wave 199 P2 → **VACUOUS** (N=1000 data doesn't exist; P2 script points to empty dir)
- Wave 199 P3 → **VACUOUS** (this analysis; same root cause)
- Wave 198 P2/P3 lineageflow entry → **STILL APPLIES** as the only honest finding on actual LineageFlow per-record data (N=5 smoke, TIE on both metrics)
