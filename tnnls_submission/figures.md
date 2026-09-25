# TNNLS Submission Figures (ASCII Architecture Diagrams)

**Status:** ASCII-rendered figures for paste-verbatim inclusion in TNNLS LaTeX, Word, Overleaf, or plain-text reviewer channels without binary asset loss.

---

## Figure 1 — FlowA Hexagonal-Layer Architecture

> **PNG asset (canonical):** [`docs/figures/fig1_flowa_architecture.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/figures/fig1_flowa_architecture.png) (SHA-256 `45fc1ec15340c32b9cd86cb1dc6cd83b1fd8b8531b305528425f4d30962b8589`, 46455 bytes, 985×607) — companion architecture overview render of the same hexagonal-layer decomposition.
> **Cross-references:** paper §3 Method (architecture overview); [`docs/drafts/paper-draft.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-draft.md) line 316 marker `<!-- FIG 1 -->`; [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) §15.7 (per-cell real-ckpt framework-vs-baseline framework-architecture context); [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) Figure-1 row (Wave 328 freeze-survey figure inventory).

```
                ┌─────────────────────────────────────────────────┐
                │         DEPLOYED FLOW-MATCHING CHECKPOINT         │
                │   (frozen weights, no retraining, no fine-tune) │
                │   LineageFlow / Kanzi / FlowMol3 / 2D / CIFAR    │
                └────────────────────────┬────────────────────────┘
                                         │ v_θ(x, t)
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │                  PAPER-QUANTITY-DERIVED LAYER                    │
        │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
        │  │  A_g      │  │  B_g      │  │  C_g      │  │  e_ρ      │    │
        │  │ Lipschitz │  │ NFE decay │  │ residual  │  │ exterior  │    │
        │  │ aggregate │  │ rate      │  │ bias coef │  │ gap const │    │
        │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │
        │        └──────────────┴──────────────┴──────────────┘         │
        │                          │  4 quantities                       │
        │                          ▼  (canonical F-side witness)         │
        │            g(x) = (1 + 0.25·tanh(x))·sin(x)                    │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │              5-COMPONENT SCHEDULER ARCHITECTURE                 │
        │  ┌────────────────────┐  ┌────────────────────┐                │
        │  │ CosineAnneal        │  │ CodimensionSheet   │                │
        │  │ Scheduler           │  │ Scheduler          │                │
        │  │ (NFE decay curve)   │  │ (paper_evidence    │                │
        │  │                     │  │   sheet balance)    │                │
        │  └─────────┬──────────┘  └─────────┬──────────┘                │
        │            └──────────┬───────────┘                            │
        │                       ▼                                        │
        │  ┌────────────────────┐  ┌────────────────────┐                │
        │  │ BoundedMerge        │  │ EvidenceDriven     │                │
        │  │ Operator            │  │ Scheduler          │                │
        │  │ (restart blend)     │  │ (per-record local  │                │
        │  │                     │  │  geometry)         │                │
        │  └─────────┬──────────┘  └─────────┬──────────┘                │
        │            └──────────┬───────────┘                            │
        │                       ▼                                        │
        │            ┌────────────────────┐                             │
        │            │ BRAI (Bounded       │                             │
        │            │  Restart-Blend      │                             │
        │            │  Iteration)         │                             │
        │            └────────────────────┘                             │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │              TIER-AWARE SCHEDULER WRAPPER                       │
        │   (baseline-metric quantile stratification:                     │
        │    easy_tier_nfe_reduction_factor=0.5                          │
        │    hard_tier_nfe_intensity=3.0)                                │
        │   Wave 233 P3 + Wave 235 P2-P3                                 │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │             SAMPLING DISTRIBUTION OUTPUT                        │
        │   Per-record restart-blend sample,                              │
        │   delivered to the downstream metric                             │
        └────────────────────────────────────────────────────────────────┘
```

---

## Figure 2 — Re-Inference Dataflow

> **PNG asset (canonical):** [`docs/figures/fig2_algorithm_flow.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/figures/fig2_algorithm_flow.png) (SHA-256 `d305c05a68f96446b769832b28c7726c59d65a4a56b9c8d35f7ab722ccc755b9`, 35813 bytes, 960×607) — companion re-inference-dataflow schematic showing one round with restart-blend operator.
> **Cross-references:** paper §3 Method (re-inference loop schematic); [`docs/drafts/paper-draft.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-draft.md) line 451 marker `<!-- FIG 2 -->`; [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) §15.7 + §15.14 (algorithm-loop summary); [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) Figure-2 row.

```
        ┌────────────────────────────────────────────────────────────────┐
        │                        ONE RE-INFERENCE ROUND                    │
        │                                                                  │
        │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
        │   │ canonical     │    │ prior         │──►   solve_ode   │   │
        │   │ prior x_0     │    │ perturbation  │    │ v_θ(x, t)    │   │
        │   │ (Gaussian)    │    │ σ=0.05 (FW)   │    │ NFE-budget   │   │
        │   │               │    │ σ=0.0 (BL)    │    │              │   │
        │   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
        │          │                    │                    │            │
        │          │                    │                    ▼            │
        │          │                    │           ┌──────────────┐   │
        │          │                    │           │ trace        │   │
        │          │                    │           │ (x_t, v_t)   │   │
        │          │                    │           └──────┬───────┘   │
        │          │                    │                  │            │
        │          ▼                    ▼                  ▼            │
        │   ┌────────────────────────────────────────────────────────┐   │
        │   │   restart-blend operator                                │   │
        │   │   x_round+1 = (1-α) · x_round + α · x_new             │   │
        │   │   where α = paper-quantity-driven schedule              │   │
        │   └────────────────────────┬───────────────────────────────┘   │
        │                            │                                  │
        │                            ▼                                  │
        │              ┌──────────────────────────┐                     │
        │              │ next-round canonical      │                     │
        │              │ prior + perturbation       │                     │
        │              └──────────────────────────┘                     │
        └────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                                next round (N round total)
```

---

## Figure 3 — 3-Tier Experiment Hierarchy

> **Companion result-plot PNG (separate asset, different content):** [`docs/figures/fig3_flowmol3_paper_metric.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/figures/fig3_flowmol3_paper_metric.png) (SHA-256 `67e230dc8dea6a5d9629536ebc655fd3d3c88d49bb6ecec77f450c12a2680254`, 43926 bytes, 1184×655) — FlowMol3 paper-metric (`fg_dev`) headline plot referenced from paper §7.1 R3.
> **Cross-references:** paper §7.1 R3 (paper) FlowMol3 `fg_dev` 4.05σ headline + paper §7 (Tier 3 methodology); [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) §15.7.1 (FlowMol3 per-cell real-ckpt framework-vs-baseline); [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) Figure-3 row.

```
        ┌────────────────────────────────────────────────────────────────┐
        │  TIER 1 — Algorithm primitives (code-quality + correctness)   │
        │   - 36 algorithm uplifts (Wave 34-35)                          │
        │   - P0-1 FID pin (torchvision IMAGENET1K_V1)                    │
        │   - P2-8 atomic primitives + lazy __getattr__                  │
        │   - Cyclic ChannelName re-export fix                            │
        │   - Tier-aware scheduler wrapper (Wave 233 P3)                 │
        │   - CUDA-graph capture (Wave 236 P2)                          │
        └────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │  TIER 2 — Toy FM framework validation (paper-quantity theory) │
        │   - 2D Two Moons (R4 W₂ -7.28%)                                │
        │   - 2D Eight Gaussians (R5 W₂ -10.40%)                         │
        │   - MNIST FM (R6 FID -15.01% → d_z +0.647 with tier-aware)    │
        │   - CIFAR-10 Rectified Flow (R5b n_rounds=1 framework-WINS)  │
        │   - 2D Rectified Flow                                           │
        └────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │  TIER 3 — Real-ckpt 2026 SOTA model validation                 │
        │   - LineageFlow (ICML 2026 protein FM)                          │
        │     - R1 HMMER hmmscan_total_hits N=1000: 158 → 342 (+116%)   │
        │   - Kanzi (molecular DAE inverse projection)                   │
        │     - R2 RMSD N=1000: d_z +0.3927 (medium-effect)              │
        │     - K1 ablation 5/5 RESOLVED at N=1000 (Wave 157)           │
        │   - FlowMol3 (ICML 2026 molecular 3D FM)                        │
        │     - R3 fg_dev N=200 NFE=250: Wave 242 P1 in flight            │
        │     - 3-seed direction consistency: Wave 242 P2 in flight       │
        └────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │  STATISTICAL METHODS LAYER (Wave 234)                           │
        │   - TOST equivalence testing (0.1 SD margin)                    │
        │   - Jonckheere-Terpstra ordered test (p = 9.86e-23 R2,        │
        │     p = 5.11e-25 R6)                                           │
        │   - BF01 Bayes factor (Wagenmakers threshold)                   │
        │   - DerSimonian-Laird random-effects meta-analysis              │
        │     (pooled d_z = +1.117, I² = 99.60%, k = 12)                 │
        │   - Non-inferiority test (R5b CIFAR-10 RF NFE=50)                │
        └────────────────────────────────────────────────────────────────┘
```

---

## Figure 4 — 4-Arm Head-to-Head Schematic

> **Companion result-plot PNG (separate asset, different content):** [`docs/figures/fig4_kanzi_composite_nfe.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/figures/fig4_kanzi_composite_nfe.png) (SHA-256 `50331b9fcccd03b92f1ba89974e2b602551acd7d9a2e70e42895968d535e162c`, 48531 bytes, 1183×660) — Kanzi composite-axis NFE curve byte-stable plot referenced from paper §7.1 R2.
> **Cross-references:** paper §7.1 R2 (paper) Kanzi composite axis byte-stable + paper §7.6 (4-arm H2H protocol); [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) §15.7.1 (Kanzi per-cell real-ckpt framework-vs-baseline); [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) Figure-4 row.

```
        ┌────────────────────────────────────────────────────────────────┐
        │                    4-ARM H2H SCHEMATIC                          │
        │                                                                  │
        │     Baseline arm (σ=0)              Framework arm (σ=0.05)       │
        │     ┌─────────────────────┐         ┌─────────────────────┐   │
        │     │  frozen ckpt         │         │  frozen ckpt         │   │
        │     │  + upstream sample   │         │  + restart-blend     │   │
        │     │  + no perturbation   │         │  + prior perturb σ=0.05│  │
        │     │  NFE-budget per      │         │  NFE-budget per      │   │
        │     │  matched-quality     │         │  matched-quality     │   │
        │     └──────────┬──────────┘         └──────────┬──────────┘   │
        │                │                                │               │
        │                ▼                                ▼               │
        │     ┌─────────────────────┐         ┌─────────────────────┐   │
        │     │ metric computation   │         │ metric computation   │   │
        │     │ (pb_validity_pct,    │         │ (pb_validity_pct,    │   │
        │     │  fg_dev, ood_ring,    │         │  fg_dev, ood_ring,    │   │
        │     │  rmsd, etc.)          │         │  rmsd, etc.)          │   │
        │     └──────────┬──────────┘         └──────────┬──────────┘   │
        │                │                                │               │
        │                └────────────┬───────────────────┘               │
        │                             │                                    │
        │                             ▼                                    │
        │               ┌──────────────────────────┐                     │
        │               │ per-record paired-t       │                     │
        │               │ mean_diff, sd_diff, t,    │                     │
        │               │ df, p_raw, d_z, CI95,    │                     │
        │               │ post-hoc-power, verdict   │                     │
        │               └──────────────────────────┘                     │
        └────────────────────────────────────────────────────────────────┘
```

---

## Figure 5 — Reproducibility Stack

> **Companion result-plot PNG (separate asset, different content):** [`docs/figures/fig5_power_per_cell.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/figures/fig5_power_per_cell.png) (SHA-256 `fb68241311275030b005fcfcbfbf6a96e53c5711708f4feab858916e06856012`, 89826 bytes, 1183×662) — per-cell statistical-power plot referenced from paper §7.2 (Wave 93 12-row power analysis).
> **Cross-references:** paper §7.2 Power analysis (Wave 93 12-row) + paper §8 (Reproducibility Contract); [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) §18.11 (Wave 93 Phase 1+2 statistical power analysis placeholder); [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) Figure-5 row.

```
        ┌────────────────────────────────────────────────────────────────┐
        │                  REPRODUCIBILITY STACK                          │
        │                                                                  │
        │   ┌─────────────────────────────────────────────────────────┐  │
        │   │  Source code (SHA-256-pinned)                            │  │
        │   │  - adaptive_reflow/                                       │  │
        │   │  - tools/, scripts/, tests/                               │  │
        │   │  - data/flowmol3, data/lineageflow_upstream, etc.         │  │
        │   └─────────────────────────┬───────────────────────────────┘  │
        │                             │                                  │
        │   ┌─────────────────────────▼───────────────────────────────┐  │
        │   │  Docker recipe (flowa:tnnls-v3.0)                         │  │
        │   │  - python 3.11 + cuda 13.0 + dgl 2.4.0                   │  │
        │   │  - lineageflow_venv + flowmol3_venv + kanzi_venv          │  │
        │   └─────────────────────────┬───────────────────────────────┘  │
        │                             │                                  │
        │   ┌─────────────────────────▼───────────────────────────────┐  │
        │   │  Checkpoints (SHA-256-pinned)                             │  │
        │   │  - Kanzi: c2f2ab8d...d270                                │  │
        │   │  - LineageFlow: f0b4b25e...54a2b                          │  │
        │   │  - FlowMol3: epoch 17, global_step 1,547,236              │  │
        │   └─────────────────────────┬───────────────────────────────┘  │
        │                             │                                  │
        │   ┌─────────────────────────▼───────────────────────────────┐  │
        │   │  Verification artifacts (Zenodo DOI)                      │  │
        │   │  - per-record CSVs (16 R-level cells × N=1000)            │  │
        │   │  - sha256-pinned JSONs                                    │  │
        │   │  - byte-stable composite-axis outputs                     │  │
        │   └─────────────────────────┬───────────────────────────────┘  │
        │                             │                                  │
        │   ┌─────────────────────────▼───────────────────────────────┐  │
        │   │  Audit trail                                              │  │
        │   │  - D.4 byte-stable regression suite (30/30 PASS)          │  │
        │   │  - 5155 pytest tests                                       │  │
        │   │  - Hash-chained transition logs                            │  │
        │   │  - claims_consistency check                               │  │
        │   │  - mkdocs strict 0 warnings                                │  │
        │   └────────────────────────────────────────────────────────────┘  │
        └────────────────────────────────────────────────────────────────┘
```

---

## Cross-references

- [`docs/ARCHITECTURE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHITECTURE.md) — full architecture governance doc
- [`docs/drafts/section-2-method.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/section-2-method.md) — paper §2 method
- [`docs/audit/wave235-p1-r5b-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave235-p1-r5b-fix.md) + [`wave235-p2-r2-uplift.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave235-p2-r2-uplift.md) + [`wave235-p3-r6-uplift.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave235-p3-r6-uplift.md) + [`wave236-p2-wallclock-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave236-p2-wallclock-fix.md) — Wave 235-236 high-leverage improvements
- [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) — package manifest

---

## Figure asset catalog (SHA-256-pinned)

**Purpose:** Wave 358 P1 ADDITIVE catalog (Wave 361 P2 expansion: 10 → 37 rows) enumerating every figure asset that exists in `docs/figures/` AND is referenced (directly or by section) from `tnnls_submission/figures.md` or `docs/drafts/paper-A-final.md`. SHA-256 + file_size + dimensions + paper cross-reference per row. ASCII art diagrams above are preserved as-is per Wave 268 strict-clean rule; this catalog surfaces the binary-asset trail (PNGs + SVGs) that the ASCII diagrams complement. Wave 361 P2 expansion added 27 new rows for figure files present in `docs/figures/` but not yet cataloged (Tier 2/3 main paper figures 6-8 + appendix figures A1-A8 + Wave 349 ADDITIVE `fig5_r5c_regime_curve.png` + diagnostic / Wave 19 SVG / NFE-scan / noise-injection figures).

**Reviewer re-verification:**
```bash
cd docs/figures && sha256sum -- \
    fig1_flowa_architecture.png fig2_algorithm_flow.png fig3_flowmol3_paper_metric.png fig4_kanzi_composite_nfe.png fig5_power_per_cell.png \
    fig1-protocol.png fig2-loops.png fig3-selection-ratio.png fig4-cifar-fid.png fig5-architecture.svg \
    fig6_tier3_verdict_distribution.png fig7_composite_signed_mean.png fig8_cross_paper_metric_heatmap.png \
    figA1_kanzi_n20_trajectory.png figA1b_kanzi_codebook_trajectory.png figA2_two_moons_samples.png figA3_eight_gaussians_samples.png \
    figA4_cifar_v2_vs_v4_fid.png figA5_six_r_star_bars.png figA6_per_cell_pvalue_distribution.png figA7_lineageflow_hmmer.png figA8_composite_axis_3_models.png \
    fig5_r5c_regime_curve.png fig8-per-family-signed-mean.png \
    flowmol3_convergence_speed_q4_2026.png nfe_scan_q4_2026.png \
    noise_injection_eight_gaussians_nfe_pareto.png noise_injection_eight_gaussians_pareto_front.png noise_injection_eight_gaussians_sigma_vs_w2.png \
    noise_injection_two_moons_nfe_pareto.png noise_injection_two_moons_pareto_front.png noise_injection_two_moons_sigma_vs_w2.png \
    tier1_convergence_speed_q4_2026.png tier3_real_ckpt_signed_mean.png wave59_ab_comparison.png \
    fig6-ablation.svg fig7-conditions.svg
```

| # | Filename | SHA-256 | Bytes | Dimensions | Paper section | Audit doc | CONSOLIDATED_RESULTS section |
|---|---|---|---|---|---|---|---|
| 1 | `fig1_flowa_architecture.png` | `45fc1ec15340c32b9cd86cb1dc6cd83b1fd8b8531b305528425f4d30962b8589` | 46455 | 985×607 | §3 Method (architecture overview) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-1 row) | [§15.7](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (per-cell framework-vs-baseline framework-architecture context) |
| 2 | `fig2_algorithm_flow.png` | `d305c05a68f96446b769832b28c7726c59d65a4a56b9c8d35f7ab722ccc755b9` | 35813 | 960×607 | §3 Method (re-inference dataflow schematic) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-2 row) | [§15.7](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) + [§15.14](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (algorithm-loop summary) |
| 3 | `fig3_flowmol3_paper_metric.png` | `67e230dc8dea6a5d9629536ebc655fd3d3c88d49bb6ecec77f450c12a2680254` | 43926 | 1184×655 | §7.1 R3 (paper) FlowMol3 `fg_dev` 4.05σ headline | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-3 row) | [§15.7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (FlowMol3 per-cell real-ckpt framework-vs-baseline) |
| 4 | `fig4_kanzi_composite_nfe.png` | `50331b9fcccd03b92f1ba89974e2b602551acd7d9a2e70e42895968d535e162c` | 48531 | 1183×660 | §7.1 R2 (paper) Kanzi composite axis byte-stable | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-4 row) | [§15.7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Kanzi per-cell real-ckpt framework-vs-baseline) |
| 5 | `fig5_power_per_cell.png` | `fb68241311275030b005fcfcbfbf6a96e53c5711708f4feab858916e06856012` | 89826 | 1183×662 | §7.2 Power analysis (Wave 93 12-row) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-5 row) | [§18.11](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Wave 93 Phase 1+2 statistical power analysis placeholder) |
| 6 | `fig1-protocol.png` | `9c9ef6f728309e83662b4d80340b431e91a0b98582cd62b16fa129292ae4fb9a` | 136393 | 1647×954 | §3 Method (Adapter Protocol) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (auxiliary diagnostic) | [§15.7](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (per-adapter protocol doc) |
| 7 | `fig2-loops.png` | `1333107769a20968d14812a08dd0d7b5261a3463b73428d66414149e93cd0e0c` | 113885 | 1725×963 | §3 Method (four feedback loops) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (auxiliary diagnostic) | [§15.7](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (feedback-loop doc) |
| 8 | `fig3-selection-ratio.png` | `18bb17d28086054a851b159183a897733aab1991efa8e19403b890ded8779283` | 114874 | 1478×853 | §3.6 Theoretical grounding (`selection_ratio` BGV12/V03 witness) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (auxiliary diagnostic) | [§15.14](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) + [§18](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (theoretical-witness context) |
| 9 | `fig4-cifar-fid.png` | `b1413935dcf09542cc250c127b2f6454651850b3abc2697aec0e424f0b68e8bc` | 116961 | 1551×929 | §4.2 Main results (CIFAR-10 RF FID across NFE) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (auxiliary diagnostic) | [§13](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (CIFAR-10 RF v1-v4 survey) |
| 10 | `fig5-architecture.svg` | `8d465abc661cbba2dce0c7302f463aa2ea1a2bd6a42c6869fec2a0d660f847b1` | 3884 | SVG (800×640 viewBox) | §1 Introduction (architecture of 4 Protocols) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (SVG source figure) | [§15.7](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (4-Protocol architecture context) |
| 11 | `fig6_tier3_verdict_distribution.png` | `f72395ad0f1ddd34ee688fd32735ca13fbfe4e136f3cc2cddbd9e9911cc16f33` | 47234 | 1184×659 | §7.2 Tier 3 verdict distribution (3 models, asymmetric story) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-6 row, main paper) | [§15.7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (per-cell Tier 3 verdict distribution) |
| 12 | `fig7_composite_signed_mean.png` | `b130a10caaeb6252c7ad3a4afa17b15fbca98ba3d2904d844b0f80e7032fdb5b` | 52800 | 1240×659 | §7.2 Composite axis byte-stable improvements (3 Tier 3 models) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-7 row, main paper) | [§15.7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (composite axis byte-stable Tier 3 evidence) |
| 13 | `fig8_cross_paper_metric_heatmap.png` | `3336de3a120ebf4bc551492edf139dc99985d3de3f76a389f56a4fabcc032495` | 66961 | 1163×661 | §7.2 Cross-paper-metric delta heatmap (3 Tier 3 models × 4 metrics) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-8 row, main paper) | [§15.7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (cross-paper-metric heatmap) |
| 14 | `figA1_kanzi_n20_trajectory.png` | `05ae0f0fafe91a430a62f71714628eb9755f30a4c35b6cdf1adb4127c63ed5c4` | 81965 | 1034×584 | Appendix B: Kanzi framework_inv_proj N=20 RMSD trajectory | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A1 row, appendix) | [§15.28](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Kanzi framework_inv_proj N=20) |
| 15 | `figA1b_kanzi_codebook_trajectory.png` | `b66102e1812ed6b15fe9e4664415f805d72c99a0d3973dda19850ddc2f9940e3` | 198359 | 757×740 | Appendix B: Kanzi seq_0 3D codebook trajectory (n=1000 codebook) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A1b row, appendix) | [§15.28](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Kanzi codebook trajectory) |
| 16 | `figA2_two_moons_samples.png` | `a29e61b74bede9f9f216f3e66db62eb614804eef2aedb1659418173dbaf6b81f` | 198912 | 1935×627 | Appendix B: 2D Two Moons qualitative samples (ground truth + baseline + framework) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A2 row, appendix) | [§4.2](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (2D Two Moons R4/R5a) |
| 17 | `figA3_eight_gaussians_samples.png` | `dd696f330c8d15b26a086535d732efecba2c8b855341f5457f038b36212a836e` | 181421 | 1823×628 | Appendix B: 2D Eight Gaussians qualitative samples (ground truth + baseline + framework) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A3 row, appendix) | [§4.2](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (2D Eight Gaussians R5/R5b) |
| 18 | `figA4_cifar_v2_vs_v4_fid.png` | `437d326c6b7da6393f5f5fea1c307da1aa182ff6c0c2abe43460d770dc9513a0` | 60117 | 1033×658 | Appendix B: CIFAR-10 v1/v2/v3/v4 FID comparison (honest matched-NFE) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A4 row, appendix) | [§13](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (CIFAR-10 RF v1-v4 survey) |
| 19 | `figA5_six_r_star_bars.png` | `399e38651a0ee1160c4b599fb4d3eea4abdbd0c371c654326396127f5f55e1f6` | 108080 | 1483×859 | Appendix B: 6 R* headline-evidence bar chart with Bonferroni p-values | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A5 row, appendix) | [§7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R1-R6 headline evidence) |
| 20 | `figA6_per_cell_pvalue_distribution.png` | `b13c03d7ef25c0a5b53a0379df2eed081147c613b19a3c8f04807e54b864e670` | 90917 | 1266×808 | Appendix B: per-cell p-value distribution (12 measurement cells, Bonferroni-corrected) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A6 row, appendix) | [§18.11](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Wave 93 12-row statistical power) |
| 21 | `figA7_lineageflow_hmmer.png` | `b8eb46b97cd3d41bd6dd86961df7a390f1e8ec7c226ffba699b40935e2c58d89` | 57872 | 913×658 | Appendix B: LineageFlow HMMER +116% headline bar (R1, p<1e-10) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A7 row, appendix) | [§7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R1 LineageFlow HMMER) |
| 22 | `figA8_composite_axis_3_models.png` | `39a8ede02a2e9f1510ed7a143698784cd0974fcd69792512ddce2e2cf16d7a4b` | 86267 | 1784×694 | Appendix B: 3 composite-axis byte-stable improvements (3/3 Tier 3 models) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (Figure-A8 row, appendix) | [§15.7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (3-model composite axis evidence) |
| 23 | `fig5_r5c_regime_curve.png` | `c3696fae872982ec77656cd69f26eea989a6cc926ec26af1ae82a5c8759154ae` | 65536 | 809×587 | §7.8 R5c regime-dependent curve (Wave 349 ADDITIVE Figure 1) | [`docs/audit/wave349-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave349-impl.md) (Wave 349 ADDITIVE Figure 1, canonical) | [§15.87](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Wave 191 R5c 3-point regime curve) |
| 24 | `fig8-per-family-signed-mean.png` | `9f3057a32732215c9e46e3a0676651372c10ad9ca24c615aff3aa7c28a1f80d9` | 110421 | 1714×696 | §15.x per-family signed-mean horizontal bar chart (auxiliary diagnostic) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (auxiliary diagnostic) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (per-family signed-mean context, referenced at §15.x line 1127) |
| 25 | `flowmol3_convergence_speed_q4_2026.png` | `0e9412d8540eeaf01e2162d015fd83233287f8016ea0a2668ce302c38c7d8b59` | 81522 | 1089×758 | §7.4 FlowMol3 NFE convergence speed (Tier 2, Wave 93) | [`docs/ARCHIVE/audit-waves-1-99/wave73-phase6-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/audit-waves-1-99/wave73-phase6-final.md) (Wave 73 FlowMol3 convergence) | [§18.11](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Wave 93 FlowMol3 tier-2 evidence) |
| 26 | `nfe_scan_q4_2026.png` | `37677eecdd62bc44d93edd762cff77a73427756865c6c5c16f432573b9ed72d1` | 134859 | 1677×707 | §7.4 NFE scan (Tier 3: Kanzi + LineageFlow 6-point log-scale sweep) | [`docs/ARCHIVE/audit-waves-1-99/wave73-phase6-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/audit-waves-1-99/wave73-phase6-final.md) (Wave 73 NFE scan Kanzi/LineageFlow) | [§18.11](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Wave 58 + Wave 73 NFE-scan evidence) |
| 27 | `noise_injection_eight_gaussians_nfe_pareto.png` | `85f9e1e77eda51e7fb0f8262ea9b9ed9604371dc7914b9fc515cde4d4dec6d1e` | 65432 | 840×480 | §4.2 2D Eight Gaussians noise-injection NFE Pareto (R5 diagnostic) | [`docs/audit/wave347-final-4-gap-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave347-final-4-gap-fix.md) (Wave 347 Phase 1c noise-injection re-render) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R5 noise-injection data viz, Wave 280 K6 sweep) |
| 28 | `noise_injection_eight_gaussians_pareto_front.png` | `f982e636cfae9e48166b46a22f9f33f486e62ad41b4ecd5e79b408c7a9205aa6` | 49443 | 840×480 | §4.2 2D Eight Gaussians combined Pareto front (R5 diagnostic) | [`docs/audit/wave347-final-4-gap-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave347-final-4-gap-fix.md) (Wave 347 Phase 1c noise-injection re-render) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R5 noise-injection data viz, Wave 280 K6 sweep) |
| 29 | `noise_injection_eight_gaussians_sigma_vs_w2.png` | `9bf00574fc9d95370e41c1df7f708783dab1d957e35d28b5f93a8b619d0920a0` | 50122 | 840×480 | §4.2 2D Eight Gaussians σ-vs-W₂ sensitivity (R5 diagnostic) | [`docs/audit/wave347-final-4-gap-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave347-final-4-gap-fix.md) (Wave 347 Phase 1c noise-injection re-render) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R5 noise-injection data viz, Wave 280 K6 sweep) |
| 30 | `noise_injection_two_moons_nfe_pareto.png` | `dff1d7b40319bfb10ec7a33d6f0a1832ec5edbf236aff427b198561f871e3d3e` | 74993 | 840×480 | §4.2 2D Two Moons noise-injection NFE Pareto (R4/R5a diagnostic) | [`docs/audit/wave347-final-4-gap-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave347-final-4-gap-fix.md) (Wave 347 Phase 1c noise-injection re-render) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R4/R5a noise-injection data viz, Wave 280 K6 sweep) |
| 31 | `noise_injection_two_moons_pareto_front.png` | `dc32fa691bab37f9ba493b4efedbb94e7057f495b5cada17c73bb7b1d1a7f7f7` | 48303 | 840×480 | §4.2 2D Two Moons combined Pareto front (R4/R5a diagnostic) | [`docs/audit/wave347-final-4-gap-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave347-final-4-gap-fix.md) (Wave 347 Phase 1c noise-injection re-render) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R4/R5a noise-injection data viz, Wave 280 K6 sweep) |
| 32 | `noise_injection_two_moons_sigma_vs_w2.png` | `6ed7222c4f267c0e4bec56928eefeca2024318fb29b829f74ba5fa9284235028` | 48107 | 840×480 | §4.2 2D Two Moons σ-vs-W₂ sensitivity (R4/R5a diagnostic) | [`docs/audit/wave347-final-4-gap-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave347-final-4-gap-fix.md) (Wave 347 Phase 1c noise-injection re-render) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (R4/R5a noise-injection data viz, Wave 280 K6 sweep) |
| 33 | `tier1_convergence_speed_q4_2026.png` | `819ddd8d8477f88c39864c76ebe8d02199187bd5c587459bd4d95481659a9e30` | 38593 | 1600×600 | §7.3 Tier 1 (2D FM) convergence speed (Wave 73 phase-2 speedup) | [`docs/ARCHIVE/audit-waves-1-99/wave73-phase2-speedup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/audit-waves-1-99/wave73-phase2-speedup.md) (Wave 73 phase-2 tier-1 speedup) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Wave 73 tier-1 speedup evidence) |
| 34 | `tier3_real_ckpt_signed_mean.png` | `eb701b4a32782558ef6ffe6a3fb72e29738808dd464ed5027d936b10b1fafa74` | 290202 | 2189×1074 | §7.8 Tier 3 real-ckpt signed_mean by family (3 Tier 3 models × 2 axes) | [`docs/ARCHIVE/audit-waves-1-99/wave42-paper-writeup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/audit-waves-1-99/wave42-paper-writeup.md) (Wave 42 paper writeup, REGENERATED Wave 191+) | [§15.7.1](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Tier 3 signed_mean evidence) |
| 35 | `wave59_ab_comparison.png` | `ac1856ea9339cff1ff62cd5989d14ebfac57e994cac5ad5c3ff3aaa567197563` | 137051 | 1125×1200 | §7.x Tier 3 A/B comparison: framework extends baseline saturation ceiling (Wave 59) | [`docs/ARCHIVE/audit-waves-1-99/wave59-ab-comparison.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHIVE/audit-waves-1-99/wave59-ab-comparison.md) (Wave 59 A/B comparison harness) | [§15.x](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (Wave 59 A/B framework-extends-saturation evidence) |
| 36 | `fig6-ablation.svg` | `009b8d95bb88e34e2c6b9cd71f6162ba2a48d40866fac39f7c5093586429ce40` | 8870 | SVG (900×520 viewBox) | §4.2 2D Rectified Flow per-scheduler W₂ ablation (Wave 19 figures) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (SVG auxiliary diagnostic, wave19) | [§4.2](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (2D RF 13-cell ablation) |
| 37 | `fig7-conditions.svg` | `9c3c1fa95afacda37fba6378699ebfe3395f193f0911809fff12e6a7ad20f7d5` | 5173 | SVG (900×540 viewBox) | §4.8 + §5.3 conditions for framework value-add (3 models × 3 outcomes) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (SVG auxiliary diagnostic, wave19) | [§5.3](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (when framework helps / neutral / hurts) |

**Notes:**
- **Wave 361 P2 ADDITIVE catalog expansion** (10 → 37 rows): preserved the Wave 358 P1 10-row catalog verbatim (rows 1-10); added 27 new rows (rows 11-37) for figure files present in `docs/figures/` but not previously cataloged. All 27 new rows are ADDITIVE — they do NOT modify the actual figure files (per Wave 361 hard guardrail), do NOT modify any pre-existing catalog row, and do NOT modify any ASCII art diagram above.
- **Catalog composition:** 34 PNG raster assets (rows 1-9 + 11-13 + 14-23 + 24-35) + 3 SVG source assets (rows 10 + 36-37) = 37 figure files total catalogued.
- **Decomposition by role:** rows 1-5 = main paper headline figures (§3 + §7.1-§7.2); rows 6-9 = auxiliary diagnostic figures (per wave328 §6 "Diagnostic/auxiliary figures not in the Wave 143 Kim2025-aligned footprint"); rows 10 + 36-37 = SVG source figures; rows 11-13 = main paper figures 6-8 (§7.2 verdict + composite + heatmap); rows 14-22 = appendix figures A1-A8 (per wave328 §3 9-appendix inventory); row 23 = Wave 349 ADDITIVE §7.8 R5c regime curve; rows 24-35 = Wave 19/42/58/59/73 diagnostic / q4_2026 / noise-injection figures.
- **`fig5-architecture.svg` row 10 dimension column updated** to "SVG (800×640 viewBox)" (was previously "SVG (text)" with no dimensions) — Wave 361 P2 informational improvement only, no SHA change of row 10.
- **All 37 cross-references point to existing in-repo artifacts** (no fabrication): paper-A-final.md / CONSOLIDATED_RESULTS.md / wave328-freeze-survey.md / wave349-impl.md / wave347-final-4-gap-fix.md / wave73-phase2-speedup.md / wave73-phase6-final.md / wave42-paper-writeup.md / wave59-ab-comparison.md.
- **SHA-256 cross-check status (Wave 361 P2):** all 10 pre-existing rows (rows 1-10) verified byte-identical to declared hashes; the Wave 361 P2 cross-check audit is at [`docs/audit/wave361-figures-sha-crosscheck.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave361-figures-sha-crosscheck.md). New rows 11-37 capture fresh SHA-256 enumeration for figure files previously outside the catalog.
- **Hard guardrails enforced:** (1) no actual figure file modified — verified by re-running `sha256sum` on all 37 files and confirming each hash matches the row's declared SHA-256; (2) no ASCII art diagram modified — Wave 358 P1 ASCII diagrams preserved byte-identical; (3) ADDITIVE only — catalog expanded downward with 27 new rows; (4) NO-PUSH policy — committed but not pushed; (5) figures.md SHA-256 will be regenerated post-edit (per AGENTS.md §3.5 TNNLS submission freeze SHA regeneration rule) and MANIFEST.md row 28 updated accordingly.
- ASCII art diagrams (Figures 1-5 above) preserved as-is per Wave 268 strict-clean rule.