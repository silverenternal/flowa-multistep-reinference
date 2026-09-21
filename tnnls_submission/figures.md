# TNNLS Submission Figures (ASCII Architecture Diagrams)

**Status:** ASCII-rendered figures for paste-verbatim inclusion in TNNLS LaTeX, Word, Overleaf, or plain-text reviewer channels without binary asset loss.

---

## Figure 1 — FlowA Hexagonal-Layer Architecture

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

- `docs/ARCHITECTURE.md` — full architecture governance doc
- `docs/drafts/section-2-method.md` — paper §2 method
- `docs/audit/wave235-p1-r5b-fix.md` + `wave235-p2-r2-uplift.md` + `wave235-p3-r6-uplift.md` + `wave236-p2-wallclock-fix.md` — Wave 235-236 high-leverage improvements
- `tnnls_submission/MANIFEST.md` — package manifest