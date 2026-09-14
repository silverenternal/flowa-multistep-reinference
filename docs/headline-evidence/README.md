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

## Figures (Wave 143 Kim2025-aligned footprint)

The paper-bound figures for the Tier-1 SCI submission live under
[`docs/figures/`](../../figures/README.md). Below is the index with
one-line descriptions; full captions + per-figure generator paths live in
[`docs/figures/README.md`](../../figures/README.md).

### Main-paper figures (8, matplotlib-rendered)

| # | Title | Source |
|---|---|---|
| 1 | FlowA architecture overview (4 Protocols + 17 typed state machines + 333 transitions) | `docs/figures/fig1_flowa_architecture.png` |
| 2 | FlowA inference-time re-inference loop schematic (multi-round restart-blend pipeline) | `docs/figures/fig2_algorithm_flow.png` |
| 3 | FlowMol3 paper-metric baseline vs framework (N=1000, NFE=50; fg_dev 4.05σ) | `docs/figures/fig3_flowmol3_paper_metric.png` |
| 4 | Kanzi composite axis across NFE budget (3 seeds × 6 NFE = 18 cells, byte-stable) | `docs/figures/fig4_kanzi_composite_nfe.png` |
| 5 | Statistical power per-cell (Wave 93 power analysis, 11 axes) | `docs/figures/fig5_power_per_cell.png` |
| 6 | Tier 3 paper-metric verdict distribution per model (3 models, asymmetric story) | `docs/figures/fig6_tier3_verdict_distribution.png` |
| 7 | Framework composite-axis improvement (3 models, byte-stable σ=0 or 3-run byte-identical) | `docs/figures/fig7_composite_signed_mean.png` |
| 8 | Cross-paper-metric delta heatmap (3 models × 6 paper-metric axes) | `docs/figures/fig8_cross_paper_metric_heatmap.png` |

### Appendix figures (9, matplotlib-rendered)

| # | Title | Source |
|---|---|---|
| A1 | Kanzi framework_inv_proj N=20 RMSD trajectory | `docs/figures/figA1_kanzi_n20_trajectory.png` |
| A1b | Kanzi seq_0 3D codebook trajectory (qualitative) | `docs/figures/figA1b_kanzi_codebook_trajectory.png` |
| A2 | 2D Two Moons qualitative samples (ground truth / baseline / framework) | `docs/figures/figA2_two_moons_samples.png` |
| A3 | 2D Eight Gaussians qualitative samples (ground truth / baseline / framework) | `docs/figures/figA3_eight_gaussians_samples.png` |
| A4 | CIFAR-10 v2 vs v4 FID comparison (the honest matched-NFE reading) | `docs/figures/figA4_cifar_v2_vs_v4_fid.png` |
| A5 | 6 R* headline evidence bar chart (R1–R6 Bonf-sig framework_better) | `docs/figures/figA5_six_r_star_bars.png` |
| A6 | Per-cell p-value distribution (12 measurement cells ranked by −log₁₀ p) | `docs/figures/figA6_per_cell_pvalue_distribution.png` |
| A7 | LineageFlow HMMER +116% headline bar (the single Bonf-sig Tier 3 cell) | `docs/figures/figA7_lineageflow_hmmer.png` |
| A8 | 3 composite axis byte-stable improvements (Kanzi / LineageFlow / FlowMol3) | `docs/figures/figA8_composite_axis_3_models.png` |

Total: **17 figures (8 main + 9 appendix)**. All regenerable from
`tools/_make_wave143_main_figures.py` (main) + `tools/_make_wave143_appendix_figures.py`
(appendix); committed as static binaries for paper integration.

## Tables (Wave 143 Kim2025-aligned footprint)

The 8 numbered main-paper tables (A–H) live in
[`docs/paper-draft.md` §7.6.6](../../paper-draft.md) (per-cell Tier 3 + Tier 1 + Tier 2
consolidation, Kim2025-aligned count). Below is the index with
one-line descriptions; full per-cell data + source JSON lives in
`docs/paper-draft.md` §7.6.6.

### Main-paper tables (8, numbered A–H)

| ID | Title | Source |
|---|---|---|
| **A** | Consolidated Tier 3 + Tier 1 + Tier 2 paper-metric framework_improves (R1–R6) | `docs/paper-draft.md` §7.6.6 Table A |
| **B** | Internal composite axis byte-stable improvements (3/3 Tier 3 models) | `docs/paper-draft.md` §7.6.6 Table B |
| **C** | Ablation study — algorithm primitive impact (5 arms × 3 models) | `docs/paper-draft.md` §7.6.6 Table C |
| **D** | Hyperparameter sensitivity (β schedule, NFE, restart radius) | `docs/paper-draft.md` §7.6.6 Table D |
| **E** | Time complexity + runtime (per-record wallclock, Kanzi / LineageFlow / FlowMol3) | `docs/paper-draft.md` §7.6.6 Table E |
| **F** | Per-cell statistical power verdict (Wave 93 12-row; source `verification_outputs/power_analysis/per_cell.csv`) | `docs/paper-draft.md` §7.6.6 Table F |
| **G** | FlowA vs each baseline (cross-method comparison; BoN / SMC / CoDe / SVDD / RBF per Kim2025 §7) | `docs/paper-draft.md` §7.6.6 Table G |
| **H** | Domain coverage + per-domain verdict (6 axes: image / 2D-synthetic / protein / molecule / FID / W₂) | `docs/paper-draft.md` §7.6.6 Table H |

### Appendix table (1)

| ID | Title | Source |
|---|---|---|
| **A1** | Per-component ablation matrix (5 arms × 3 models, extended Wave 52 ablation) | `docs/paper-draft.md` §Ablations.1 |

Total: **8 numbered main-paper tables (A–H) + 1 appendix table (A1)**.
Data sourced from existing `verification_outputs/` + `docs/audit/` + `docs/CONSOLIDATED_RESULTS.md`
§15.28 (per Wave 143 Phase 1 commit `bee7f1f`).

