# Wave 234 P6 — R5b CIFAR-10 RF non-inferiority test

**Date (UTC)**: 2026-09-21T06:41:38.343301+00:00

## Summary

R5b CIFAR-10 Rectified Flow at matched NFE=50 (Wave 191 P2 N=1000, best arm `evidence_driven`) regresses on FID by +84.0011 units (+20.20%) vs the 50-NFE Euler baseline. The pre-specified non-inferiority margin (10% of baseline_FID = 41.5828) is **far below** the point estimate of the regression:

* baseline FID: **415.8285**
* framework FID (evidence_driven): **499.8296**
* mean_diff_FID (framework - baseline): **84.0011** (+20.20%)
* margin (10% baseline_FID): **41.5828**
* mean_diff - margin = **+42.4183** (positive => worse than margin)

## Methodology

**One-sided non-inferiority test** (Schuirmann 1987 / ICH E9 framework). Let $\Delta = \text{FID}_{\text{fw}} - \text{FID}_{\text{bl}}$. Pre-specified hypotheses:

```
H0:  Δ >= margin      (framework regresses beyond margin)
H1:  Δ <  margin      (framework is non-inferior within margin)
```

with $\text{margin} = 0.10 \cdot \text{FID}_{\text{baseline}} = 41.5828$ (typical image-FID regression budget; e.g. StyleGAN3 / DiT-XL cross-run reporting accepts +/- 10% FID as within-budget). The test statistic is $t = (\text{margin} - \bar{\Delta}) / (\text{sd}_\Delta / \sqrt{n})$ with ``direction='upper'`` in `adaptive_reflow.stats.equivalence.non_inferiority`.

**Variance source** — the chunk-level paired FID test from `verification_outputs/wave191-p2-cifar10-n1000.json` provides the matched-NFE paired-diff SD:

* n_chunks = 10, df = 9
* Cohen's d_z on chunk FID diffs = +2.7004
* chunk mean_diff_FID = +90.0451
* chunk SD_diff_FID (per pair) = 33.3451
* chunk SE_diff_FID = 10.5446

The chunk-level SD (per pair) is propagated as the matched-NFE paired uncertainty for the non-inferiority test on the headline FID delta.

## Results (primary arm: `evidence_driven`)

| Quantity | Value |
|---|---:|
| baseline FID | 415.8285 |
| framework FID | 499.8296 |
| mean_diff_FID | 84.0011 (+20.20%) |
| margin (10% baseline) | 41.5828 |
| SD_diff (per chunk pair) | 33.3451 |
| SE_diff (n=10) | 10.5446 |
| 95% CI on Δ | [63.3336, 104.6686] |
| t (non-inferiority) | -4.0227 |
| p_non_inferiority | **0.9985** |
| margin_z (margin - mean) / SE | -4.0227 |
| **verdict_non_inferior** | **False** |

## Honest framing

While the R5b CIFAR-10 Rectified Flow regression at matched NFE=50 (Wave 191 P2 N=1000, d_z = +2.700 on chunk-level FID diffs) is *statistically unambiguous* (chunk-level d_z = +2.7 corresponds to ~10x stronger signal than the 10% margin), it is **NOT non-inferior** within the pre-specified 10% FID margin. The point estimate ΔFID = +84.0011 (+20.20%) is roughly **2.02x the margin**, with the margin sitting **-4.0 standard errors** below the point estimate (p_non_inferiority = 0.9985, i.e. essentially 1.0). The non-inferiority test decisively fails to reject H0.

## Cross-arm view (all 3 framework schedulers, primary = evidence_driven)

| arm | baseline_FID | framework_FID | ΔFID (units, %) | margin | p_non_inferiority | verdict |
|---|---:|---:|---:|---:|---:|---|
| cosine | 415.8285 | 500.1991 | +84.3706 (+20.29%) | 41.5828 | 0.9986 | NOT non-inferior |
| codimension_sheet | 415.8285 | 500.1180 | +84.2895 (+20.27%) | 41.5828 | 0.9986 | NOT non-inferior |
| evidence_driven | 415.8285 | 499.8296 | +84.0011 (+20.20%) | 41.5828 | 0.9985 | NOT non-inferior |

## Reproducibility

* Script: `scripts/wave234_p6_non_inferiority.py`
* Input: `verification_outputs/wave191-p2-cifar10-n1000.json`
* Output CSV: `verification_outputs/wave234-p6-non-inferiority.csv`
* Output JSON: `verification_outputs/wave234-p6-non-inferiority.json`
* Backend: `adaptive_reflow.stats.equivalence.non_inferiority`
* Alpha: 0.05 (one-sided, upper-tail test)

