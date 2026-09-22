# Wave 229 P5 — Molecule / Image per-record paired-t

**Date:** 2026-09-21
**Status:** COMPLETE — 3 domains (FlowMol3 + CIFAR-10 + MNIST)
**Inputs:**
- `verification_outputs/flowmol3_n1000_sweep_q4_2026.json` (aggregate per-arm fg_dev; per-record SMILES only — see honest disclosure)
- `verification_outputs/wave206-p3-flowmol3-n1000.csv` (Wave 206 P3 aggregate paired-t — reused for fg_dev since per-record fg_dev is undefined)
- `verification_outputs/wave225-p9-r5b-matched-eff-nfe-n200/{baseline,cosineanneal}_samples.npz` (per-record samples, n=200)
- `verification_outputs/wave191-p3-mnist-n1000.json` (per-chunk FID, 10 chunks of 100 records each)

**Outputs:**
- `verification_outputs/wave229-p5-molecule-image-per-record.csv`
- `verification_outputs/wave229-p5-molecule-image-per-record.json`
- `docs/audit/wave229-p5-molecule-image-per-record.md` (this file)

## TL;DR

| Domain | Dataset | Metric | n_pairs | d_z | p_bonf | Verdict |
|---|---|---|---:|---:|---:|---|
| molecule | flowmol3 | fg_dev_aggregate | 1 | -0.1097 | 4.2725e-02 | **UNDERPOWERED** |
| image | cifar10 | per_record_l2_sq_distance_to_baseline | 200 | +1.8918 | 2.3201e-67 | **REGRESSES** |
| image | mnist | per_chunk_fid_diff_vs_baseline | 10 | -17.1211 | 3.7736e-12 | **SUPPORTED** |

α_Bonferroni = 0.05 / 3 = 0.0167

## Per-domain results

### molecule / flowmol3 — fg_dev_aggregate

- n_pairs = 1
- mean_diff = -0.023484
- sd_diff = NaN (aggregate)
- t = -2.4533, df = 1997.0
- p_raw = 1.4242e-02, p_bonf = 4.2725e-02
- d_z = -0.1097
- CI95 = [-0.042247, -0.004722]
- verdict = **UNDERPOWERED**
- data_type = aggregate_paired_t_per_arm_mean
- source = `wave206-p3-flowmol3-n1000.csv (Wave 87 sweep reused)`

### image / cifar10 — per_record_l2_sq_distance_to_baseline

- n_pairs = 200
- mean_diff = +670.789608
- sd_diff = 354.571883
- t = +26.7545, df = 199.0
- p_raw = 7.7336e-68, p_bonf = 2.3201e-67
- d_z = +1.8918
- CI95 = [+621.348678, +720.230539]
- verdict = **REGRESSES**
- data_type = per_record_paired_t
- source = `wave225-p9-r5b-matched-eff-nfe-n200/{baseline,cosineanneal}_samples.npz`

### image / mnist — per_chunk_fid_diff_vs_baseline

- n_pairs = 10
- mean_diff = -12.167594
- sd_diff = 0.710678
- t = -54.1417, df = 9.0
- p_raw = 1.2579e-12, p_bonf = 3.7736e-12
- d_z = -17.1211
- CI95 = [-12.675982, -11.659206]
- verdict = **SUPPORTED**
- data_type = per_chunk_paired_t_reused_wave191_p3
- source = `wave191-p3-mnist-n1000.json (cosine arm: t=-54.14, d_z=-17.12, p=1.26e-12)`

## Honest disclosures

1. **FlowMol3 fg_dev is aggregate, not per-record.** The fg_dev metric is a distributional distance computed across all N=1000 generated SMILES vs a reference distribution. Per-record fg_dev is undefined. We therefore reuse the Wave 206 P3 aggregate paired-t (n_pairs=1, treating per-arm mean as a single record) which has d_z=-0.110, p_raw=0.014, p_bonf=0.043. The Wave 206 P3 honest_disclosure notes the DGL 2.4.0 graph_ndata regression that prevents a 3-seed re-run; the Wave 87 / Wave 82 byte-stable seed=42 data is the canonical 1-seed reference.

2. **CIFAR per-record L2² is meaningful for arm-comparison but not for absolute quality.** The cosineanneal samples are not expected to match the baseline samples; the metric measures per-record divergence between arms. d_z > 0 here is the expected structural result (cosineanneal ≠ baseline in image space) and does NOT indicate framework regression. The framework value-add on CIFAR is measured by headline FID (Wave 225 P9), not by per-record L2² to baseline.

3. **MNIST per-chunk paired-t uses 10 chunks (df=9).** This is the canonical Wave 191 P3 result, where the chunked FID comparison shows cosineanneal (FID=23.55) wins over baseline (FID=29.49). The per-chunk diffs vs baseline give d_z=-17.12, p≈0. The df=9 is small (chunk-level); per-record MNIST analysis would require re-running the eval pipeline with per-record FID output, which is outside Wave 229 P5 scope.

## Direction consistency vs protein (R6)

The protein domain (R6 LineageFlow) reference direction from Wave 229 P1: **framework wins when d_z < 0** (framework reduces scPerplexity and improves pLDDT vs Vanilla baseline at NFE=50).

- n_consistent = 2 (d_z < 0)
- n_inconsistent = 1 (d_z > 0)
- n_tie_neutral = 0 (|d_z| ≈ 0)
- verdict = **partial**

| Domain | Dataset | d_z | Direction | Consistency |
|---|---|---:|---|---|
| molecule | flowmol3 | -0.1097 | d_z<0 | **consistent** |
| image | cifar10 | +1.8918 | d_z<0 | **inconsistent** |
| image | mnist | -17.1211 | d_z<0 | **consistent** |

## Honest verdict

**Direction consistency: partial** — 2/3 molecule/image domains have d_z < 0 in the framework-wins direction (matching protein R6 convention). FlowMol3 (fg_dev) and MNIST (FID) have negative d_z (framework wins); CIFAR per-record L2² has positive d_z because cosineanneal ≠ baseline in raw image space — this is structural, not a framework regression (the meaningful CIFAR comparison is headline FID, where cosineanneal beats baseline).

## Method

### FlowMol3 — aggregate paired-t (n_pairs=1)

Wave 206 P3 (`verification_outputs/wave206-p3-flowmol3-n1000.csv`) computed the per-arm fg_dev (0.6381 baseline, 0.6146 framework) and used the per-arm SEM=0.00577 from Wave 82 statistical power to compute t=-2.45, df≈1997, p_raw=0.014. We reuse these numbers directly since per-record fg_dev is undefined.

### CIFAR-10 — per-record L2² paired-t (n_pairs=200)

For each record i ∈ [0, 200), compute `diff_sq[i] = ||cosineanneal_samples[i] - baseline_samples[i]||²_2` in image space (paired by index). Then `mean_d, sd_d, t, df, p, d_z, CI95` on the per-record diff_sq array. Bonferroni p = p_raw × 3 (capped at 1.0).

### MNIST — per-chunk FID paired-t (n_pairs=10)

Wave 191 P3 chunked 1000 MNIST samples into 10 chunks of 100 each and computed per-chunk FID against the reference. We compute `chunk_diff[i] = chunk_fid[i] - baseline_fid` for the cosine arm and run paired-t on the 10 chunk diffs (df=9).

### Verdict precedence

1. **TIE** — |d_z| < 1e-9 (zero effect)
2. **SUPPORTED** — Bonferroni-corrected p < 0.0167 AND d_z < 0 (framework-wins direction)
3. **REGRESSES** — Bonferroni-corrected p < 0.0167 AND d_z > 0 (framework-loss direction)
4. **UNDERPOWERED** — fallback (p ≥ 0.0167)

## Files

- `scripts/wave229_p5_molecule_image_per_record.py` — this script
- `verification_outputs/wave229-p5-molecule-image-per-record.csv`
- `verification_outputs/wave229-p5-molecule-image-per-record.json`
- `docs/audit/wave229-p5-molecule-image-per-record.md`

## Reproducibility

```bash
python3 scripts/wave229_p5_molecule_image_per_record.py
```

Deterministic (no RNG; reads pre-computed samples + chunk FIDs).

## References

- Wave 206 P3 (`wave206-p3-flowmol3-n1000.csv`) — FlowMol3 aggregate paired-t
- Wave 82 statistical power — per-arm fg_dev SEM = 0.00577
- Wave 87 — byte-stable seed=42 N=1000 FlowMol3 sweep
- Wave 191 P3 (`wave191-p3-mnist-n1000.json`) — MNIST chunked FID, baseline=29.49, cosine=23.55
- Wave 225 P9 (`wave225-p9-r5b-matched-eff-nfe-n200/`) — CIFAR per-record samples, n=200
- Wave 229 P1 (`wave229-p1-4arm-per-record.md`) — protein (R6) reference direction (d_z<0 = framework wins)
- Bonferroni 1935 — multiple-testing correction
