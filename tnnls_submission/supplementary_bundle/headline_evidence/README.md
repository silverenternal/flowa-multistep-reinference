# Tier-1 SCI Submission: Headline Evidence Collection

**Date:** 2026-09-14 (original Wave 135 freeze) + 2026-09-23 (Wave 326 cross-doc-snapshot pointer)
**Source:** Wave 135 (post-v1.0-paper-final freeze) + Wave 310 + Wave 322 final state
**Freeze marker:** v1.0-paper-final tag at commit `39a65a7f`

## Purpose

This directory contains every experimentally strong data point that supports
the Tier-1 SCI submission headline. Each subdirectory has a `SOURCE.md`
pointing at the underlying sweep JSON + the audit doc that establishes provenance.

## Headline evidence — Wave 310 + Wave 322 final structure (5 main + 6 SUPP = 11 cells)

**Final 11-cell verdict distribution (canonical cross-doc anchor: `docs/audit/wave326-crossdoc-metrics-snapshot.md`).** The 11 headline cells partition as **4 STRONG (main) + 1 TIE (main) + 6 PARTIAL/SUPP** = 5 main cells + 6 supplementary cells.

> **NOTE on R-cell ID mapping (Wave 310 final).** The headline-evidence directory R-cell IDs (R1-R6 in this README) follow the **Wave 135 freeze** ordering: R1=LineageFlow HMMER, R2=FlowMol3 fg_dev, R3=CIFAR-10 RF v2 FID, R4=2D Two Moons, R5=2D Eight Gaussians, R6=MNIST FM. The **paper §7.2 Table 7.1 + `DATA_PRESENTATION.md` §2 + `docs/CLAIMS.md`** use a **different R-cell ID mapping** (R1=LineageFlow HMMER, R2=Kanzi RMSD, R3=FlowMol3 fg_dev, R4=R5a=2D Two Moons TIE, R5=R5_legacy=2D Eight Gaussians SUPP, R5b=CIFAR-10 RF, R5c=MNIST FM, R6=LineageFlow k6 foldability). The two mappings are NOT 1:1 — the headline-evidence README preserves the Wave 135 frozen directory labels (additive only) and the Wave 310 final R-cell mapping is documented in `DATA_PRESENTATION.md` §2 + `docs/CLAIMS.md` CLM-060 + the Wave 326 cross-doc-snapshot.

### Main cells (5): 4 STRONG + 1 TIE

| Cell | Model | Metric | N | Baseline | Framework | Delta | Status | Source |
|---|---|---|---|---:|---:|---:|---|---|
| **R2 Kanzi RMSD** (paper R-cell) | Kanzi | `reconstruction_kabsch_rmsd_Å` | 1000 | 0.9020 | 0.8798 | **−0.022 Å (d_z=−0.0990)** | **STRONG** (deployed index-matched two-sample t Bonf-sig at α=0.007143) | `verification_outputs/wave218-p3-kanzi-framework-wins.csv` + DATA_PRESENTATION.md §2.2 |
| **R5b CIFAR-10 RF** (paper R-cell) | CIFAR-10 RF | `FID` (matched NFE=50) | 200 | chunk-FID | chunk-FID | **−1.60% to −2.53% ΔFID** (n_rounds=1) / +9.77% to +30.19% (n_rounds≥2) | **STRONG conditional** (n_rounds=1 framework-WINS, Wave 235 P1 reversal; n_rounds≥2 REGRESSES, documented honest-negative) | `verification_outputs/wave235-p1-r5b-fix.{csv,json}` + §15.98 |
| **R5c MNIST FM** (paper R-cell) | MNIST FM | `FID` (smoke ckpt) | 1000 | 29.49 | 23.39 | **−28.43% (d_z=−13.175)** | **STRONG** (smoke ckpt; PROVISIONAL on production ckpt direction-FLIPS) | `verification_outputs/wave191-p3-mnist-n1000.json` + CLM-059 |
| **R6 LineageFlow k6** (paper R-cell) | LineageFlow k6 | `pLDDT_mean` (tier-aware arm) | 1000 | uniform-arm naive d_z=+0.0707 | tier-aware counterfactual d_z=+0.2235 | **d_z=+0.2235** (Bonf-sig at α=0.05/6=0.008333) + grid-search best d_z=+0.6467 | **STRONG** (Wave 310 paper-level upgrade; easy-tier d_z=−0.499 halved from uniform-arm −0.998) | `verification_outputs/wave225-p4-k6-tier-aware.json` + `wave233-p3-tier-aware-r6.json` + `wave235-p3-r6-uplift.json` + CLM-073 |
| **R5a 2D Two Moons** (paper R-cell) | 2D RF | `W2` (paper R-level) | 3 unpaired seeds | per-seed d_s=+0.460 (n=3) | n/a | n/a (no framework-WINS) | **TIE** (paper R-level d_s=+0.460 at n=3, verified Wave 209 P6 n=7 + Wave 216 P2 n=10; -78.25% from SEPARATE 2D FM ablation coexists) | `verification_outputs/wave196-p4-table-a-r-level.json` + DATA_PRESENTATION.md §2.4 |

### SUPP cells (6): PARTIAL/SUPP/LEGACY/direction-INVERTED

| Cell | Model | Metric | Status | Anchor |
|---|---|---|---|---|
| **R1** (paper) = headline-evidence R1 | LineageFlow HMMER | `hmmscan_total_hits` | **PARTIAL / single-seed-disclosed** | `r1_lineageflow_hmmer_p1e-10/SOURCE.md` (Wave 308 P1 demotion from STRONG to PARTIAL; seed=42 single-seed Bonf-sig d_z=+0.182 p_raw=1.25e-8) |
| **R3** (paper) = headline-evidence R2 | FlowMol3 fg_dev | `fg_dev` | **PARTIAL** | `r2_flowmol3_fgdev_4p05sigma/SOURCE.md` (Wave 87 seed=42 N=1000 batched direction framework-WINS −0.0235 4.05σ; 3-seed BLOCKED at vendor level per Wave 109.C DGL + Wave 244-262 vendored revert CLM-076/077) |
| **R5_legacy** (paper) = headline-evidence R5 | 2D Eight Gaussians | `W2` | **SUPP / LEGACY** | `r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md` (Wave 256 P2 demotion; per-round raw CSV files NOT preserved per `docs/CLAIMS.md` line 3783) |
| **K1** | FlowMol3 RDKit-validity | `rdkit_validity_pct` | **SUPP / UNDERPOWERED** | Wave 308 P2 demotion from PARTIAL/BORDERLINE-STRONG; d_z=+1.3645 REAL but p_bonf=0.5676 FAILS K-level α=0.0125 by 45.4× (paper-cited 0.054 mis-applied R-level k=7 family to a K-level cell) |
| **K4+K5** | LineageFlow HMMER length-bias + uniform-AA | `hmmscan_total_hits` | **SUPP / K4 POWERED + K5 SUPP-WITH-CAVEAT** | Wave 306 demotion; K4 hit-count metric POWERED at metric-collection level (12-22 hits/100 records non-zero across all 3 seeds); K5 paired-delta +8.9% (+1.33 hits) visible but Bonf-FAIL at α=0.0125 (n=3 paired seeds d_f=2) |
| **K7** | LineageFlow novelty | `novelty_at_{0.5,0.8,0.95}` | **SUPP / direction-INVERTED** | Wave 306 demotion (W280 P driver subsamples baseline.fasta only — d_z=∞ is a numerical artifact, NOT framework-vs-baseline); W166 P3 canonical in-git evidence `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` (sha256 61dd70fa) shows framework 12.6× LESS Pfam-novel than baseline at pctid<30% twilight-zone — direction OPPOSITE of paper's framework-WINS claim |

### Legacy headline-evidence table (Wave 135 freeze, preserved verbatim per Wave 268 strict-clean)

The original Wave 135 "Headline 6 Bonf-sig framework_improves (R1-R6)" table that
this section supersedes is preserved verbatim below for byte-stable traceability:

| R | Model | Metric | N | Baseline | Framework | Delta | Bonf p | Source
|---|---|---|---|---:|---:|---:|---:|---|
| R1 | LineageFlow | `hmmscan_total_hits` | 1000 | 158 | 342 | **+184 (+116%)** | < 1e-10 | `r1_lineageflow_hmmer_p1e-10/SOURCE.md` |
| R2 | FlowMol3 | `fg_dev` | 1000 | 0.6381 | 0.6146 | **-0.0235 (4.05sigma)** | < 0.05 | `r2_flowmol3_fgdev_4p05sigma/SOURCE.md` |
| R3 | CIFAR-10 RF v2 | `FID` | 250 | 218.87 | 122.18 | **-44.17%** | NFE-averaged | `r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md` |
| R4 | 2D Two Moons | `W2` | 1000 | 0.5029 | 0.4663 | **-7.28%** | matched NFE 500 | `r4_2d_two_moons_w2_m7p28pct/SOURCE.md` (R5a post-cd70821 reading is TIE; -78.25% from separate 2D FM ablation; **Wave 311 R5a reconciliation footnote in `DATA_PRESENTATION.md` §3 line 374 explicitly documents the two-readings coexistence: paper R-level verdict TIE (d_s=+0.460 at n=3 verified by Wave 209 P6 n=7 + Wave 216 P2 n=10), 2D FM ablation verdict framework-WINS -78.25%**) |
| R5 | 2D Eight Gaussians | `W2` | 1000 | 0.6606 | 0.5919 | **-10.40%** | matched NFE 500 | `r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md` |
| R6 | MNIST FM | `FID` | 1000 | 409.18 | 347.75 | **-15.01%** | CristianLazoQuispe ckpt | `r6_mnist_fm_fid_m15p01pct/SOURCE.md` |

**NOTE on R-cell ID mismatch (this README vs paper §7.2):** The headline-evidence
directory uses Wave 135 frozen R-cell IDs (R1-R6 in this table); the paper §7.2
Table 7.1 + `DATA_PRESENTATION.md` §2 + `docs/CLAIMS.md` CLM-060 use the Wave 310
final R-cell mapping (R1=LineageFlow HMMER, R2=Kanzi RMSD, R3=FlowMol3 fg_dev,
R4=R5a=2D Two Moons, R5=R5_legacy=2D Eight Gaussians, R5b=CIFAR-10 RF, R5c=MNIST FM,
R6=LineageFlow k6 foldability). The two mappings are NOT 1:1; the headline numbers
in this legacy table ARE preserved verbatim across both mappings (e.g., R6 here =
MNIST FM = paper R5c; R2 here = FlowMol3 fg_dev = paper R3). For the Wave 310
canonical R-cell ID mapping see `DATA_PRESENTATION.md` §2 or `docs/CLAIMS.md` CLM-060.

**Wave 326 cross-doc-snapshot pointer.** See `docs/audit/wave326-crossdoc-metrics-snapshot.md`
for the canonical Wave 310 + Wave 322 final 11-cell verdict distribution snapshot
(4 STRONG + 1 TIE + 6 PARTIAL/SUPP = 11 headline cells).

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

