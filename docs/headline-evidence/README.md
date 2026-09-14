# Tier-1 SCI Submission: Headline Evidence Collection

**Date:** 2026-09-14
**Source:** Wave 135 (post-v1.0-paper-final freeze)
**Freeze marker:** v1.0-paper-final tag at commit `39a65a7f`

## Purpose

This directory contains every experimentally strong data point that supports
the Tier-1 SCI submission headline. Each subdirectory has a `SOURCE.md`
pointing at the underlying sweep JSON + the audit doc that establishes provenance.

## Headline 6 Bonf-sig framework_improves (R1-R6)

| R | Model | Metric | N | Baseline | Framework | Delta | Bonf p | Source
|---|---|---|---|---:|---:|---:|---:|---|
| R1 | LineageFlow | `hmmscan_total_hits` | 1000 | 158 | 342 | **+184 (+116%)** | < 1e-10 | `r1_lineageflow_hmmer_p1e-10/SOURCE.md` |
| R2 | FlowMol3 | `fg_dev` | 1000 | 0.6381 | 0.6146 | **-0.0235 (4.05sigma)** | < 0.05 | `r2_flowmol3_fgdev_4p05sigma/SOURCE.md` |
| R3 | CIFAR-10 RF v2 | `FID` | 250 | 218.87 | 122.18 | **-44.17%** | NFE-averaged | `r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md` |
| R4 | 2D Two Moons | `W2` | 1000 | 0.5029 | 0.4663 | **-7.28%** | matched NFE 500 | `r4_2d_two_moons_w2_m7p28pct/SOURCE.md` |
| R5 | 2D Eight Gaussians | `W2` | 1000 | 0.6606 | 0.5919 | **-10.40%** | matched NFE 500 | `r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md` |
| R6 | MNIST FM | `FID` | 1000 | 409.18 | 347.75 | **-15.01%** | CristianLazoQuispe ckpt | `r6_mnist_fm_fid_m15p01pct/SOURCE.md` |

## Byte-stable composite axis (3/3 Tier 3 models)

| Model | Composite | N (cells) | sigma within seed | Source
|---|---|---:|---:|---|
| Kanzi | +0.1695 | 18 (3 seeds x 6 NFE 10-2000) | 0.000000 | `composite_axis_byte_stable/SOURCE.md` |
| LineageFlow | +0.2083 | 8 (3 seeds x 3 NFE 10-200) | byte-stable | same |
| FlowMol3 | +0.1182 | 3 (byte-identical runs) | 0 | same |

## NFE-adaptive speedup (matched quality)

| Axis | Speedup | Source
|---|---:|---|
| 2D FM | 10x | `nfe_speedup_2p5_to_10x/SOURCE.md` |
| CIFAR-10 RF | 2.5x | same |

## Byte-reproducibility evidence

`byte_reproducibility_evidence/SOURCE.md` - documents that Kanzi N=1000 framework_inv_proj
reproduces across the ruff-frozen code change boundary within delta = 0.00e+00.

`kanzi_n1000_byte_reproducible/SOURCE.md` - 8 N=1000 sweep JSONs (4 baseline + 4 framework)
covering Wave 116/120/121/122/127/131.

## Reproducibility provenance

All data here is reproducible from the freeze-marker commit SHA + CLI commands
documented in supplementary.md `+ the per-R SOURCE.md files.
