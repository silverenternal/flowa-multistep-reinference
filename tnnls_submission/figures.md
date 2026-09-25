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

**Purpose:** Wave 358 P1 ADDITIVE catalog enumerating every figure asset that this `figures.md` document references (directly or by section) — 10 figures total. SHA-256 + file_size + dimensions + paper cross-reference per row. ASCII art diagrams above are preserved as-is per Wave 268 strict-clean rule; this catalog surfaces the binary-asset trail (PNGs + one SVG) that the ASCII diagrams complement.

**Reviewer re-verification:**
```bash
cd docs/figures && sha256sum -- fig1_flowa_architecture.png fig2_algorithm_flow.png fig3_flowmol3_paper_metric.png fig4_kanzi_composite_nfe.png fig5_power_per_cell.png fig1-protocol.png fig2-loops.png fig3-selection-ratio.png fig4-cifar-fid.png fig5-architecture.svg
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
| 10 | `fig5-architecture.svg` | `8d465abc661cbba2dce0c7302f463aa2ea1a2bd6a42c6869fec2a0d660f847b1` | 3884 | SVG (text) | §1 Introduction (architecture of 4 Protocols) | [`docs/audit/wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave328-freeze-survey.md) (SVG source figure) | [§15.7](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) (4-Protocol architecture context) |

**Notes:**
- 9 PNG raster assets (rows 1-9) + 1 SVG source asset (row 10); all 10 files exist in `docs/figures/` per `ls -la docs/figures/`.
- Catalog is ADDITIVE — does NOT modify the actual figure files (per hard guardrail).
- `fig5-architecture.svg` is the canonical 4-layer architecture overview SVG; PNG rasterizations (rows 1-2) are derivative renderings.
- All 10 cross-references point to existing in-repo artifacts (no fabrication).
- ASCII art diagrams (Figures 1-5 above) preserved as-is per Wave 268 strict-clean rule.