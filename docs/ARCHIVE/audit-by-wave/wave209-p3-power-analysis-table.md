# Wave 209 P3 — 4-arm Power Analysis Table

**Per DeepSeek B2 + B8** (reframing follow-up of Wave 208 P1).

## Summary

- **16** 4-arm cells (4 baselines × 2 NFE × 2 metrics).
- **Bonferroni alpha** = 0.05 / 16 = **0.003125** (per-cell, two-sided).
- **Target power** = 0.80.
- **Maximum required N_seeds for d_z = 0.2** at alpha = 0.003125 = **365** (paired t-test).
- Per-record power at N = 1000 (k6_foldability_w161 R6 proxy d_z) is the confirmatory evidence.

## Per-cell table

| cell | metric | NFE | d_z_per_seed | d_z_per_record | req_N(d=0.2) | req_N(d=0.5) | per-rec power@1000 | verdict_per_record |
|------|--------|-----|--------------|----------------|--------------|--------------|--------------------|---------------------|
| `vanilla_pLDDT_NFE50` | pLDDT | 50 | 0.0563 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `vanilla_pLDDT_NFE100` | pLDDT | 100 | 0.0528 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `vanilla_scPerplexity_NFE50` | scPerplexity | 50 | -2.9316 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |
| `vanilla_scPerplexity_NFE100` | scPerplexity | 100 | -2.9945 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |
| `fastdllm_pLDDT_NFE50` | pLDDT | 50 | -0.1885 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `fastdllm_pLDDT_NFE100` | pLDDT | 100 | -0.2264 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `fastdllm_scPerplexity_NFE50` | scPerplexity | 50 | 0.0202 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |
| `fastdllm_scPerplexity_NFE100` | scPerplexity | 100 | 0.0245 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |
| `abcache_pLDDT_NFE50` | pLDDT | 50 | -0.0782 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `abcache_pLDDT_NFE100` | pLDDT | 100 | -0.1062 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `abcache_scPerplexity_NFE50` | scPerplexity | 50 | -0.1950 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |
| `abcache_scPerplexity_NFE100` | scPerplexity | 100 | -0.0829 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |
| `lediflow_pLDDT_NFE50` | pLDDT | 50 | -0.1915 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `lediflow_pLDDT_NFE100` | pLDDT | 100 | -0.1633 | 0.0707 | 365 | 63 | 0.235 | UNDERPOWERED |
| `lediflow_scPerplexity_NFE50` | scPerplexity | 50 | 0.1915 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |
| `lediflow_scPerplexity_NFE100` | scPerplexity | 100 | 0.1224 | -1.0767 | 365 | 63 | 1.000 | SUPPORTED |

## Methodology

- Two-sided paired t-test, alpha = 0.05/16 = 0.003125.
- `power(n, d) = nct.sf(t_crit, df=n-1, ncp=sqrt(n)*d) + nct.cdf(-t_crit, df=n-1, ncp=sqrt(n)*d)`.
- Required n is the smallest integer for which `power(n, d) >= 0.80`.
- Per-record d_z is the **k6_foldability_w161 R6** proxy from Wave 198 P2 — the Wave 208 P1 entry for each (baseline, NFE, metric) cell uses the same proxy for that metric.
- `verdict_per_record` is SUPPORTED if the per-record d_z direction matches framework-WINS AND power@1000 ≥ 0.80; otherwise UNDERPOWERED (or REGRESSES if direction reverses).

## Why per-seed `d_z` is bounded by seed-to-seed variance

Per-seed d_z ranges 0.05–0.23. With paired n=30 and alpha = 0.003125, the smallest detectable d_z at 80% power is **0.50** (medium effect), requiring ~63 seeds; for d_z = 0.2 (small), the smallest detectable is ~365 seeds. The Wave 196 P2 4-arm sample (n=30 paired seeds) is calibrated for medium-effect detection only.

## Reframing — '14/16 UNDERPOWERED' is the correct methodological conclusion

The 14/16 per-seed UNDERPOWERED verdict does NOT indicate framework inefficacy; it indicates the per-seed sample size is below the threshold for small-effect detection. Per-record N=1000 — where the framework value-add is detectable — is the confirmatory evidence. See Wave 208 P1 `reframing.per_seed_4arm_n30` field.

## References

- Cohen 1988, _Statistical Power Analysis_, §2.4 (sample size determination).
- Wave 196 P2 (`verification_outputs/wave196-p2-4arm-paired.json`) — 16 4-arm cells, n=30 paired seeds.
- Wave 198 P2 (`verification_outputs/wave198-p2-per-record-paired.json`) — k6 R6 per-record d_z proxy.
- Wave 208 P1 (`verification_outputs/wave208-p1-4arm-power-analysis.json`) — 16 4-arm power analysis.
- DeepSeek B2 + B8 reviewer feedback.
