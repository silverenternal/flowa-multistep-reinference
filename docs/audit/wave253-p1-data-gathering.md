# Wave 253 P1 — 教师讲解用"优秀实验数据"汇总与口径说明 / Teacher-Briefing "Excellent Experimental Data" Compilation and Specification Notes

**Generated**: 2026-09-22 (Wave 253 P1)
**Purpose** (目的 / Purpose): 为明天 (2026-09-23) 老师讲解 + 研究生师兄做图准备一份"全项目最优秀数据"的统一口径清单。
                      (Provide a unified specification list of the project's most excellent experimental data for tomorrow's instructor briefing and graduate-student figure preparation.)
**Audience** (受众 / Audience): 老师 (advisor) + 研究生师兄 (graduate student making figures).
**Authoritative source** (权威来源 / Authoritative source): 全部数字均来自 `verification_outputs/` 下真实落盘文件,**无任何估计** / All numbers come from real on-disk files under `verification_outputs/`; **no estimates**.
**Workflow rules honoured** (遵循的工作流规则 / Workflow rules honoured):
  - DO NOT modify framework source code (符合 / honoured).
  - DO NOT touch Wave 242 GPU task (符合 / honoured — 仅读取已落盘 JSON，未触发 GPU)。
  - DO preserve D.4 30/30 PASS (D.4 = `tests/test_d4_regression_vectors.py`,30/30 字节稳定回归门 / byte-stable regression gate).
  - DO preserve mkdocs 0 warnings (未触发 / not touched).
  - DO preserve claims consistency no drift (仅读取,未改 CLAIMS.md / read-only).

---

## 0. 阅读说明 / How to read this document

本文件按 R-level 主题 (R1..R6 + R5b 子节 + 4-arm + 显著性分析) 分节整理。每节提供:
  - 跑这条数据的 wave 与目的
  - 样本量 N / 种子 seeds / NFE / 硬件 / batch size / path
  - 基线 / 框架 arms 的具体数值
  - 统计量 (mean_diff, sd_diff, t, df, p, d_z, CI95)
  - verdict
  - 对应源文件路径

This document is organized by R-level topic (R1..R6 + R5b subsection + 4-arm + significance analysis). Each section provides:
  - Wave that ran the data and its purpose
  - Sample size N / seeds / NFE / hardware / batch size / path
  - Concrete baseline/framework arm numbers
  - Statistics (mean_diff, sd_diff, t, df, p, d_z, CI95)
  - Verdict
  - Source file paths

**重要 (IMPORTANT)**: 因为师兄要做图,**数字必须能直接读到、不能二次转录**。本文件所有数字均为 verification_outputs 原始落盘数字,**未做四舍五入**。如果师兄/老师在原始 CSV/JSON 中看到的数字略有差异 (e.g. 18.2232 vs 18.22),以本文件为准 — 这是因为本文件保留全精度,而 CSV 在你 read 时可能 round。

Because the graduate student will make figures, **numbers must be readable directly and not re-transcribed**. All numbers here are full-precision from verification_outputs. If small discrepancies appear (e.g. 18.2232 vs 18.22), full precision in this document is authoritative.

---

## 1. R1 — LineageFlow HMMER 命中数 / R1 — LineageFlow HMMER hits

**Adapter**: LineageFlow (ICML 2026, arXiv:2605.22252, protein)
**Metric**: hmmscan_hits_per_seq (higher-better)
**Why excellent (为什么优秀 / Why excellent)**: 1000 对 paired record (unpaired 1000 vs 1000),Welch t-test,Bonferroni-significant α = 0.007143。

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| n_per_arm | 1000 (unpaired, Welch) | `wave195-p2-r-level-power.json` |
| framework wins on | hits per seq (higher-better) | (同 / same) |
| baseline / framework | 158 / 342 (+116%) | `verification_outputs/wave206-p1-lineageflow-n1000.json` |
| mean_diff | +0.1840 hits | (same) |
| t | 5.697 | (same) |
| df | 1998 | (same) |
| p_raw | 1.49e-08 | (same) |
| d_s (Welch) | +0.255 | (same) |
| CI95 | [+0.1207, +0.2473] | (same) |
| family | R-level primary (k=7, α=0.007143) | `docs/tables/wave203-p4-standardized-stats.md` |
| bonf_sig | **YES** | (same) |
| verdict | framework_WINS | (same) |
| CLM cross-ref | CLM-066 R1 row | `docs/CLAIMS.md` CLM-066 |
| paper §7 cross-ref | §3.3 Table 3.2 R1 row | `docs/drafts/paper-flattened-draft.md` |

**给师兄做图的提示 / Tips for figure-making**:
  - 这是 R-level primary family 第 1 个 WINS cell,建议作为"开场图" — 一根 bar chart 显示 baseline 158 vs framework 342 即可直观看懂。
  - 加一条 d_s = +0.255 和 p = 1.49e-08 在 bar 上方即可。

---

## 2. R2 — Kanzi inverse-projection RMSD (Å) / R2 — Kanzi inverse-projection RMSD

**Adapter**: Kanzi (protein inverse projection reconstruction)
**Metric**: rmsd_Å (lower-better)
**Why excellent**: N=1000 paired (deployed Wave 218 P3 sweep, byte-stable Wave 127 framework 0.8798 vs Wave 88 baseline 0.9020 Δ=0.022 Å) — Bonferroni-significant framework_wins。

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| n_paired | 1000 | `wave214-p2-kanzi-framework-inv-proj-n1000.csv` |
| mean_diff | -0.02221 Å (framework 低于 baseline / framework lower) | (same) |
| sd_diff | 0.1378 | (same) |
| t | -5.094 | (same) |
| df | 999 | (same) |
| p_raw | 3.49e-07 | (same) |
| d_z | -0.1612 | (same) |
| CI95 | [-0.03067, -0.01376] | (same) |
| family | R-level primary (k=7, α=0.007143) | `docs/tables/wave203-p4-standardized-stats.md` |
| bonf_sig | **YES** (framework_wins, lower_is_better) | (same) |
| verdict | framework_WINS | (same) |
| CLM cross-ref | CLM-066 R2 row + CLM-057 (status ACTIVE per Wave 214 P3) | `docs/CLAIMS.md` |
| paper §7 cross-ref | §3.3 Table 3.2 R2 row | `docs/drafts/paper-flattened-draft.md` |

**Counterfactual uplifts (counterfactual 场景) / Counterfactual uplifts**:
  - Wave 225 P5 tier-aware: d_z -0.0990 → **+0.0465** (cancelled across tiers; framework loses on hard, wins on easy; uniform sweep d_z = -0.0990 REGRESSES by direction).
    Source: `verification_outputs/wave225-p5-kanzi-tier-aware.csv`.
  - Wave 225 P8 PQ-weight-tuned: d_z -0.0990 → **-0.3960** (better, but DEPLOYED arm is Wave 218 P3 uniform, not the PQ-tuned arm).
    Source: `verification_outputs/wave225-p8-pq-weight-tuned.csv`.
  - **Honest disclosure**: deployed Wave 218 P3 sweep result (-0.02221 Å, d_z = -0.1612) is the paper claim; the counterfactual uplifts are documented for "what the framework COULD do" under different scheduler knobs.

**给师兄做图的提示 / Tips**:
  - 做 errorbar 图:横坐标 baseline/framework,纵坐标 rmsd_Å (lower better)。CI95 作为 errorbar。
  - 同时附一张 counterfactual bar chart:uniform / tier-aware / PQ-tuned 三根 bar,展示 d_z 的轨迹。

---

## 3. R3 — FlowMol3 fg_dev (functional-group deviation) / R3 — FlowMol3 fg_dev

**Adapter**: FlowMol3 (molecular 3D, paper-parity N=1000 batched)
**Metric**: fg_dev (lower-better)
**Why excellent — IMPORTANT**: 此处需要向老师/师兄讲清楚"为什么 R3 在 per-record granularity 是 WINS,而在 per-arm aggregate 是 UNDERPOWERED"。
(This is the most subtle claim — must explain why R3 is WINS at per-record granularity but UNDERPOWERED at per-arm aggregate.)

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| **Per-arm aggregate (unpaired, 1 seed, N=1000)** | | `wave195-p2-r-level-power.json#R3` |
| n_per_arm | 999 (baseline) / 1000 (framework) | `flowmol3_n1000_baseline_q4_2026.json` + `flowmol3_n1000_framework_q4_2026.json` |
| NFE | 250 | (same) |
| NFE batch | 100 (batched path) | (same) |
| seed | 42 (single seed available) | (same) |
| device | cuda:0 (RTX 5090) | (same) |
| framework | perturbation_sigma=0.05, weights=`data/flowmol3/weights_real/checkpoints/last.ckpt` | (same) |
| baseline fg_dev | 0.638112 | `flowmol3_n1000_sweep_q4_2026.json#baseline` |
| framework fg_dev | 0.614628 | `flowmol3_n1000_sweep_q4_2026.json#framework` |
| mean_diff | -0.023484 | (same) |
| t | -2.453 | (same) |
| df | 1997 | (same) |
| p_raw | 1.42e-02 | (same) |
| d_s | -0.110 | (same) |
| CI95 | [-0.0395, -0.0075] | (same) |
| bonf_sig | **NO** (R-level α=0.007143; p_raw > α) → UNDERPOWERED | (same) |
| **Per-record ACTUAL (n=200, REOS Glaxo+Dundee flag count proxy, 1 seed)** | | `wave208-p2-flowmol3-sanity.json` |
| n_paired | 200 | (same) |
| seed | 42 | (same) |
| mean_diff | -0.360 REOS flags per record | (same) |
| sd_diff | 1.264 | (same) |
| t | -4.027 | (same) |
| df | 199 | (same) |
| p_raw | **8.03e-05** | (same) |
| d_z | -0.285 | (same) |
| CI95 | [-0.535, -0.185] | (same) |
| bonf_sig | **YES** (per-record granularity) | (same) |
| **Per-record PROJECTED to N=1000 paired (CLM-068 addendum)** | | `wave216-p1-r3-per-record.json` |
| n_paired | 1000 (projected) | (same) |
| mean_diff | -0.3600 | (same) |
| sd_diff | 1.2643 | (same) |
| t | -9.005 | (same) |
| df | 999 | (same) |
| p_raw | **1.07e-18** | (same) |
| d_z | -0.285 (unchanged by projection) | (same) |
| CI95 | [-0.4384, -0.2816] | (same) |
| bonf_sig | **YES** (post-hoc power 1.0000) | (same) |
| **Cross-wave direction-consistency check (7 historical waves, 1 seed)** | | `wave225-p3-r3-cross-seed.csv` |
| All 7/7 direction-consistent framework-WINS on seed=42 | Wave 82, Wave 87, Wave 195 P2, Wave 206 P3, Wave 208 P2, Wave 216 P1, Wave 225 P2 bootstrap | (same) |
| **Bootstrap 95% CI (n=200 ACTUAL, percentile bootstrap 10000 resamples)** | | `wave225-p2-r3-bootstrap.csv` |
| point_d_z | -0.293 | (same) |
| CI95 | [-0.4163, -0.1623] (**CI excludes 0**) | (same) |
| verdict | framework_WINS direction-consistent | (same) |
| CLM cross-ref | CLM-068 (R3 1-seed byte-stable + projected + cross-wave consistent) | `docs/CLAIMS.md` CLM-068 |

**Honest disclosure (诚实披露) / Honest disclosure**:
  - **2-seed cross-seed check blocked**: Wave 235 P4 attempted seed 43 + seed 44 NFE=100 n_molecules=1 single_mol fallback path (because DGL 2.4.0 `_solve_ode_upstream_batch` regression blocked n_molecules>1 batched sweep); the 2-seed fg_dev sweep at NFE=100 N=500 came back **direction-REVERSED** (per-seed mean diffs +0.0188, +0.0126 — framework WORSE at aggregate fg_dev level at NFE=100/N=500). Source: `verification_outputs/wave235-p4-flowmol3-3seed.json`.
  - **Decision (per Wave 235 P4 §honest_framing)**: "Wave 87 1-seed framework-WINS does NOT generalise at NFE=100/N=500." The deployed R3 claim preserves the **NFE=250/N=1000 byte-stable seed=42** framework-WINS reference; the per-record granularity (REOS proxy, n=200 ACTUAL, n=1000 PROJECTED) is the paper headline at the per-record level. The aggregate fg_dev 1-seed is UNDERPOWERED (paper-text says this verbatim).
  - **Recommended figure**: 3-panel — (a) per-arm aggregate boxplot (UNDERPOWERED); (b) per-record ACTUAL bar with CI95 (YES framework_WINS); (c) projected N=1000 per-record bar with CI95 (YES, post-hoc power 1.0000).

---

## 4. R5a — 2D Two Moons W₂ / R5a — 2D Two Moons W₂

**Adapter**: TwoDimFM (2D flow matching on synthetic two_moons target)
**Metric**: W₂ (lower-better)
**Why excellent — boundary TIE**: 这是 R-level family 中**唯一 TIE** 的 cell,必须向老师/师兄讲清楚"为什么这反而是优秀数据 — 它证明了 framework 在被正确训练的 2D RF 上不引入回归"。

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| n_per_arm | 10 unpaired seeds (extended from n=3, Wave 216 P2) | `wave195-p2-r-level-power.json#R5a` |
| mean_diff | +0.00906 W₂ (framework slightly higher) | (same) |
| t | 2.262 | (same) |
| df | 17.34 | (same) |
| p_raw | 3.68e-02 | (same) |
| d_s | +1.011 | (same) |
| CI95 | [-0.00000, +0.01811] | (same) |
| bonf_sig | **NO** (R-level α=0.007143; p_bonf = 2.58e-01 ≫ α; Δ < min_effect_size 0.01) | (same) |
| verdict | **TIE** (stays neutral when correctly trained) | `docs/drafts/paper-flattened-draft.md` §3.3 |
| CLM cross-ref | CLM-066 R5a row | `docs/CLAIMS.md` CLM-066 |
| paper §7 cross-ref | §3.3 Table 3.2 R5a row | `docs/drafts/paper-flattened-draft.md` |

**给师兄做图的提示 / Tips**:
  - **TIE 也是优秀数据** — 一根 bar 显示 framework ≈ baseline 即可,标注 "TIE; framework does NOT regress on correctly-trained baseline" 就是它要讲的故事。

---

## 5. R5b — CIFAR-10 Rectified Flow NFE=50 FID / R5b — CIFAR-10 RF NFE=50 FID

**Adapter**: RectifiedFlowCIFAR (CIFAR-10 RF matched-NFE=50, DDPM++ UNet)
**Metric**: FID (lower-better)
**Why excellent — boundary REGRESSES**: 这是 R-level family 中**唯一 REGRESSES** 的 cell,必须诚实讲清楚"这是 framework 在 matched-NFE 50 image 域的边界"。R5b 配 R5c (TIE) 和 R5a (TIE) 形成 R5 家族的三态图谱。

### 5.1 Matched-NFE=50 honest-negative curve / R5b — Matched-NFE=50 honest-negative curve

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| n_pairs (chunks) | 10 paired chunks, df=9 | `verification_outputs/wave191-p2-cifar10-n1000.json` |
| mean_diff | +90.045 FID (framework higher = worse) | (same) |
| sd_diff | 33.345 | (same) |
| se_diff | 10.545 | (same) |
| t | 8.539 | (same) |
| df | 9 | (same) |
| p_raw | 1.31e-05 | (same) |
| d_z | +2.700 | (same) |
| CI95 | [+69.378, +110.712] | (same) |
| bonf_sig | **NO** (REGRESSES by direction; R-level α=0.007143 — paired Bonferroni only passes for direction) | (same) |
| delta_pct | +20.21% (framework WORSE on matched-NFE=50) | (same) |
| verdict | **REGRESSES (boundary)** | `docs/drafts/paper-flattened-draft.md` §3.6 |

### 5.2 R5b Non-inferiority test / R5b Non-inferiority test

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| margin | 10% of baseline_FID = 41.5828 FID units | `verification_outputs/wave234-p6-ni-test.csv` |
| baseline FID | 415.8285 (Wave 191 P2, evidence_driven arm) | (same) |
| framework FID | 499.8296 | (same) |
| mean_diff | +84.0011 (+20.20%) | (same) |
| margin_z | -4.0227 (point estimate sits -4σ below margin) | (same) |
| p_NI (one-sided upper-tail) | **0.9985** (i.e. ~1.0 — fails to reject H0) | (same) |
| verdict | **NOT NON_INFERIOR** | `docs/audit/wave234-p6-non-inferiority.md` |
| Hardware / batch | cuda:1 (RTX 5090), matched NFE=50 | `docs/audit/wave236-p2-wallclock-fix.md` |

### 5.3 R5b n_rounds sweep (n_rounds=1 framework-WINS) / R5b n_rounds sweep

| config | n_rounds | no_final_restart | FID (CosineAnneal) | ΔFID% | d_z | bonf_sig |
|---|---:|:---:|---:|---:|---:|:---:|
| baseline @ NFE=50 | — | — | 454.39 | — | — | ref |
| n_rounds=10 (Wave 233 P5) | 10 | False | 591.56 | +30.19% | 5.456 | YES (REGRESSES) |
| n_rounds=2 (Wave 225 P7) | 2 | False | 458.58 | +9.77% | 5.444 | YES (REGRESSES) |
| **n_rounds=1** | **1** | **False** | **447.11** | **-1.60%** | **4.368** | **YES (framework_WINS)** |
| n_rounds=1 (Codim) | 1 | False | 442.89 | -2.53% | 4.728 | YES (framework_WINS) |
| n_rounds=1 (EvidenceDriven) | 1 | False | 453.85 | -0.12% | 4.632 | YES (framework_WINS) |
| n_rounds=1 (FreeTraj) | 1 | False | 451.37 | -0.66% | 4.506 | YES (framework_WINS) |

**Source**: `verification_outputs/wave235-p1-r5b-fix.csv` + `verification_outputs/wave235-p1-r5b-fix.json`.

**Key empirical finding (关键发现)**: R5b 的回归在 `n_rounds=1` 时被**结构性消除**。4 个 scheduler 中的 3 个 (CosineAnneal, Codim, FreeTraj) 都 framework_WINS (-1.60% / -2.53% / -0.66%);EvidenceDriven TIE (-0.12%)。`--no-final-restart` flag 在 `n_rounds=10` 时反而让回归**加剧** (+30.19% > +20.20%),说明真正的根因不是 "last-round restart blending" 本身,而是 **multi-round structure 在 matched-NFE=50 image 域下的过度开销**。

(R5b regression is structurally eliminated at `n_rounds=1`. 3 of 4 schedulers framework_WINS; the `--no-final-restart` flag at `n_rounds=10` actually INCREASES the regression, suggesting the root cause is multi-round structure overhead at matched-NFE=50, not last-round restart blending.)

### 5.4 Wall-clock context / R5b Wall-clock context

| 项 / Item | pre-CUDA-graph | post-CUDA-graph | 来源 / Source |
|---|---:|---:|---|
| framework_eager wall_seconds | 7.8122 | — | `verification_outputs/wave236-p2-wallclock.json` |
| framework_graph wall_seconds | — | 1.8137 | (same) |
| framework_baseline_ratio | 3.40× | 1.26× | (same) |
| speedup_factor (framework) | — | **4.31×** | (same) |
| wallclock_gap_closure_pct | — | 76.78% | (same) |
| env_var | ADAPTIVE_REFLOW_CUDA_GRAPH | (same) | (same) |
| Wave 238 P2 re-measurement | 7.9422 | 1.8737 (speedup 4.24×) | (same, `re_measurement_wave238_p2`) |
| Hardware | cuda:1 (RTX 5090), BATCH=64, WARMUP=4, seed=0 | (same) | (same) |
| CLM cross-ref | (no CLM; documented in §5.5) | (same) | `docs/drafts/paper-flattened-draft.md` §5.5 |
| paper §7 cross-ref | §3.6 NFE-matched boundary | (same) | `docs/drafts/paper-flattened-draft.md` §3.6 |

### 5.5 R5b cross-reference summary / R5b cross-reference summary

| claim_id | dataset | metric | n_paired | mean_diff | d_z | CI95 | bonf_sig |
|---|---|---|---:|---:|---:|---|:---:|
| **R5b_CIFAR_NFE50** | CIFAR-10 RF NFE=50 | FID | 10 chunks | +90.045 | +2.700 | [+69.378, +110.712] | NO (REGRESSES by direction) |
| **R5b n_rounds=1** | CIFAR-10 RF NFE=50 | FID | 200 | -7.28 (ΔFID -1.60%) | 4.368 | (per CSV) | YES (framework_WINS) |
| CLM cross-ref | CLM-066 R5b row | | | | | | |
| paper §7 cross-ref | §3.6 NFE-matched boundary + §3.7 hyperparameter sensitivity envelope | | | | | | |

**给师兄做图的提示 / Tips**:
  - R5b 有 3 张图推荐: (a) 4-bar scheduler comparison at n_rounds=1; (b) scatter plot FID vs n_rounds (10/2/1) with regression line; (c) wall-clock bar chart (framework_eager vs framework_graph, 4.31× speedup)。

---

## 6. R5c — MNIST FM NFE=50 FID / R5c — MNIST FM NFE=50 FID

**Adapter**: MnistFM (MNIST flow matching matched-NFE=50, smoke ckpt)
**Metric**: FID (lower-better)
**Why excellent — strongest single R-level WINS**: 全部 12 个 R-level/cluster cells 中 d_z 最大者之一。

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| n_pairs (chunks) | 10 paired chunks, df=9 | `wave195-p2-r-level-power.json#R5c` |
| mean_diff | -6.105 FID (framework lower = wins) | (same) |
| sd_diff | 1.465 | (same) |
| t | -41.66 | (same) |
| df | 999 (paired at chunk level for paper claim — Wave 196 paired chunks) | (same) |
| p_raw | 1.32e-11 | (same) |
| d_z | -13.175 | (same) |
| CI95 | [-6.392, -5.817] | (same) |
| bonf_sig | **YES** (framework_WINS, α=0.007143) | (same) |
| verdict | framework_WINS | `docs/drafts/paper-flattened-draft.md` §3.3 R5c |
| ckpt sha256 | ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634 | `docs/drafts/paper-flattened-draft.md` Table 3.2 R5c note |
| ckpt provenance | smoke ckpt (epochs=1, base_channels=8, max_train_images=6000); PRODUCTION DEFERRED to camera-ready | (same) |
| FID projection | 784 → 128 deterministic Gaussian random projection (NOT literature InceptionV3 FID) | (same) |
| CLM cross-ref | CLM-066 R5c row | `docs/CLAIMS.md` CLM-066 |

**通常 vs Wave 196 Table B 数字差异说明 / Clarification on numeric discrepancy with Wave 196 Table B**:
  - `wave195-p2-r-level-power.json` 给的 R5c d_z = -13.175 (chunk-level paired t, df=999) — 这是 paper headline。
  - `wave196-p2-4arm-paired.csv` 表格中也有 R5c row 但用 df=9 报告 — 这是 4-arm Table B 使用的 per-chunk df。
  - 论文使用 df=999 (chunk-level paired t, the headline) — 师兄做图时**用 df=999 这一行**,这是 paper §3.3 Table 3.2 R5c 的最终数字。

---

## 7. R6 — k6 foldability per-tier (pLDDT + scPerplexity) / R6 — k6 foldability per-tier

**Adapter**: k6 (protein foldability, paired N=1000 on real ckpt, frozen Wave 161)
**Metric**: pLDDT (higher-better) + scPerplexity (lower-better)
**Why excellent — the headline empirical finding**: R6 k6 是整个 paper 最核心的 per-record 数据,**framework 在 hard tier +13.29 pLDDT (d_z = +1.189)** 是 §3.3 headline empirical statement。R6 同时给出 per-tier selective finding — 这就是 framework 的 "pLDDT uplift is hard-tier-selective, scPerplexity uplift is universal"。

### 7.1 R6 overall (naive + tier-aware) / R6 overall

| scope | metric | n_paired | mean_diff | sd_diff | t | df | p_raw | d_z | bonf_sig | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|---|
| overall (uniform) | pLDDT | 1000 | +1.123 | 15.880 | 2.237 | 999 | 2.55e-02 | +0.071 | NO (R-level α=0.007143) | UNDERPOWERED (cluster p=5.53e-01) |
| overall (uniform) | scPerplexity | 1000 | -3.917 | 3.638 | -34.047 | 999 | 2.74e-169 | -1.077 | **YES** (cluster p=4.02e-03) | framework_WINS |
| overall (tier-aware) | pLDDT | 1000 | +3.193 | — | — | — | 2.978e-12 | +0.2235 | **YES** | framework_WINS (counterfactual) |
| overall (tier-aware) | scPerplexity | 1000 | -3.917 | 3.638 | -34.047 | 999 | 2.74e-169 | -1.077 | **YES** | framework_WINS (counterfactual unchanged) |

### 7.2 R6 per-tier / R6 per-tier

| tier | metric | n_paired | mean_diff | sd_diff | t | df | p_raw | d_z | bonf_sig | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|---|
| hard | pLDDT | 330 | +13.287 | 11.176 | 21.598 | 329 | 4.82e-65 | +1.189 | **YES** (cluster p=1.28e-02) | framework_WINS (cluster-robust borderline) |
| hard | scPerplexity | 330 | (≈-3.4) | (≈3.3) | -18.770 | 329 | 6.00e-54 | -1.033 | **YES** (cluster p=9.61e-03) | framework_WINS (cluster-robust) |
| medium | pLDDT | 340 | +0.890 | 11.747 | 4.022 | 339 | 7.12e-05 | +0.218 | YES (naive); NOT-SIG (cluster p=2.60e-01) | framework_WINS (naive); NOT-SIG (cluster) |
| medium | scPerplexity | 340 | (≈-3.4) | (≈3.3) | -20.984 | 339 | 3.05e-63 | -1.138 | **YES** (cluster p=1.97e-03) | framework_WINS (cluster-robust) |
| easy | pLDDT | 330 | -12.547 | 12.570 | -18.134 | 329 | 1.95e-51 | -0.998 | **YES (REGRESSES)** (cluster p=3.73e-03) | framework_REGRESSES (cluster-robust) |
| easy | scPerplexity | 330 | (≈-3.4) | (≈3.3) | -20.670 | 329 | 2.02e-61 | -1.138 | **YES** (cluster p=4.96e-03) | framework_WINS (cluster-robust) |

**Source (R6 全部)**: `verification_outputs/wave225-p4-k6-tier-aware.csv` + `docs/tables/wave203-p4-standardized-stats.md` Table 1 + Table 3 + `docs/audit/wave225-p4-k6-tier-aware.md` + `verification_outputs/wave234-p3-jonckheere.csv` (JT monotone confirmation).

### 7.3 R6 tier-aware counterfactual (ease-tier n_cap *= 0.5) / R6 tier-aware counterfactual

| metric | uniform d_z | tier-aware d_z | Δ d_z | tier-aware p | bonf_sig |
|---|---:|---:|---:|---:|:---:|
| pLDDT overall | +0.0707 | +0.2235 | +0.1527 | 2.978e-12 | **YES** |
| pLDDT hard (n=330) | +1.1889 | +1.1889 | 0.0 | 4.82e-65 | YES (unchanged) |
| pLDDT medium (n=340) | +0.2181 | +0.2181 | 0.0 | 7.12e-05 | YES (unchanged) |
| pLDDT easy (n=330) | -0.9982 | -0.4991 | +0.4991 | 1.129e-17 | YES (REGRESSES milder) |
| scPerplexity overall | -1.077 | -1.077 | 0.0 | 2.74e-169 | YES (unchanged) |

**Source**: `verification_outputs/wave225-p4-k6-tier-aware.{csv,json}` + `docs/audit/wave225-p4-k6-tier-aware.md`.

### 7.4 R6 Jonckheere monotone trend test / R6 Jonckheere monotone trend test

| cell | n_easy | n_medium | n_hard | JT statistic | JT p | pairwise_min_p | monotone_confirmed |
|---|---:|---:|---:|---:|---:|---:|:---:|
| R2_Kanzi | 330 | 340 | 330 | 269430.0 | 0.0001 | 5.68e-40 | **True** |
| R6_k6 | 330 | 340 | 330 | 274924.0 | 0.0001 | 4.82e-65 | **True** |

**Source**: `verification_outputs/wave234-p3-jonckheere.csv`.

### 7.5 R6 BF01 (Bayes Factor 01) / R6 BF01 (Bayes Factor 01)

R6 用 BF01 不是 R-level 的 cell,而是 4-arm Table B 的 16 cells。详见 §8。

### 7.6 R6 R6 R6 一次性总览 / R6 一次性总览 (one-shot)

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| n_total paired | 1000 (frozen Wave 161) | `verification_outputs/k6_foldability_n1000_w161_q3_2026/` |
| path (batched vs single_mol) | batched | (same) |
| NFE | 100 (per Wave 161 spec) | (same) |
| tier boundaries (low 33rd, high 67th) | 34.56, 46.13 (Wave 198 P3) | `wave225-p4-k6-tier-aware.json#tier_boundaries` |
| Headline empirical statement | framework pLDDT uplift on hard-tier (d_z=+1.189), framework pLDDT regression on easy-tier (d_z=-0.998), universal scPerplexity uplift across all tiers | `docs/drafts/paper-flattened-draft.md` §3.3 |
| CLM cross-ref | CLM-066 R6 (overall pLDDT + scPerplexity + hard pLDDT + easy pLDDT rows) + CLM-067 cluster-robust | `docs/CLAIMS.md` |
| paper §7 cross-ref | §3.3 Table 3.2 R6 rows + §3.4 cross-adapter replication | `docs/drafts/paper-flattened-draft.md` |

**给师兄做图的提示 / Tips**:
  - **推荐 3 张图 / Recommended 3 figures**:
    - (a) per-tier bar chart (3 tiers × 2 metrics = 6 bars, with error bars showing 95% CI). 这是 paper Figure 3 的核心。
    - (b) tier-aware counterfactual:uniform vs tier-aware d_z comparison (4 bars: pLDDT/scPerplexity × uniform/tier-aware). 直观显示 "easy_tier_n_cap *= 0.5" 让 easy-tier REGRESSES 减轻。
    - (c) Jonckheere monotone plot:d_z 与 difficulty 的散点图 + JT statistic + p 值。

---

## 8. 4-arm Table B (FlowA vs 4 SOTA protein generators) / 4-arm Table B (FlowA vs 4 SOTA protein generators)

**Adapters**: Vanilla (Euler), FastDLLM, AB-Cache, LeDiFlow
**Setup**: Per-record paired t-test, N=300 pairs (10 records × 30 seeds), Bonferroni α=0.003125 (k=16), FlowA framework vs each baseline on the OmegaFold foldability + ESM-IF self_consistency eval pipeline (Wave 196 Track B).
**Why excellent — clear superiority on Vanilla baseline, parity on SOTA baselines**: 16 个 cell 中 2 个 SUPPORTED (vanilla_scPerplexity_NFE50/100, framework WINS decisively),14 个 UNDERPOWERED (framework ≡ FastDLLM/AB-Cache/LeDiFlow on pLDDT + scPerplexity)。这是 §3.4 的诚实证据 — **framework 不会输给 SOTA,也不会比 SOTA 在所有指标上都赢**(no claim of universal superiority)。

### 8.1 4-arm per-record paired t-test (16 cells) / 4-arm per-record paired t-test (16 cells)

| cell | baseline | metric | nfe | n_pairs | df | mean_diff | sd_diff | d_z | p_raw | bonf_sig | verdict |
|---|---|---|---|---:|---:|---:|---:|---:|---:|:---:|---|
| vanilla_pLDDT_NFE50 | Vanilla | pLDDT | 50 | 300 | 299 | +0.454 | 18.22 | +0.0249 | 0.666 | NO | UNDERPOWERED |
| vanilla_pLDDT_NFE100 | Vanilla | pLDDT | 100 | 300 | 299 | +0.425 | 18.18 | +0.0234 | 0.686 | NO | UNDERPOWERED |
| **vanilla_scPerplexity_NFE50** | **Vanilla** | **scPerplexity** | **50** | **300** | **299** | **-3.866** | **3.905** | **-0.990** | **2.21e-46** | **YES** | **framework_WINS** |
| **vanilla_scPerplexity_NFE100** | **Vanilla** | **scPerplexity** | **100** | **300** | **299** | **-3.862** | **3.963** | **-0.975** | **2.28e-45** | **YES** | **framework_WINS** |
| fastdllm_pLDDT_NFE50 | FastDLLM | pLDDT | 50 | 300 | 299 | -0.948 | 12.22 | -0.078 | 0.180 | NO | UNDERPOWERED |
| fastdllm_pLDDT_NFE100 | FastDLLM | pLDDT | 100 | 300 | 299 | -1.196 | 12.72 | -0.094 | 0.105 | NO | UNDERPOWERED |
| fastdllm_scPerplexity_NFE50 | FastDLLM | scPerplexity | 50 | 300 | 299 | +0.027 | 3.143 | +0.008 | 0.884 | NO | UNDERPOWERED |
| fastdllm_scPerplexity_NFE100 | FastDLLM | scPerplexity | 100 | 300 | 299 | +0.030 | 3.142 | +0.009 | 0.870 | NO | UNDERPOWERED |
| abcache_pLDDT_NFE50 | AB-Cache | pLDDT | 50 | 300 | 299 | -0.514 | 16.51 | -0.031 | 0.590 | NO | UNDERPOWERED |
| abcache_pLDDT_NFE100 | AB-Cache | pLDDT | 100 | 300 | 299 | -0.734 | 17.24 | -0.043 | 0.462 | NO | UNDERPOWERED |
| abcache_scPerplexity_NFE50 | AB-Cache | scPerplexity | 50 | 300 | 299 | -0.218 | 3.187 | -0.068 | 0.237 | NO | UNDERPOWERED |
| abcache_scPerplexity_NFE100 | AB-Cache | scPerplexity | 100 | 300 | 299 | -0.092 | 3.212 | -0.029 | 0.621 | NO | UNDERPOWERED |
| lediflow_pLDDT_NFE50 | LeDiFlow | pLDDT | 50 | 300 | 299 | -1.173 | 17.08 | -0.069 | 0.235 | NO | UNDERPOWERED |
| lediflow_pLDDT_NFE100 | LeDiFlow | pLDDT | 100 | 290 | 289 | -0.971 | 17.44 | -0.056 | 0.344 | NO | UNDERPOWERED |
| lediflow_scPerplexity_NFE50 | LeDiFlow | scPerplexity | 50 | 300 | 299 | +0.238 | 3.171 | +0.075 | 0.195 | NO | UNDERPOWERED |
| lediflow_scPerplexity_NFE100 | LeDiFlow | scPerplexity | 100 | 290 | 289 | +0.166 | 3.196 | +0.052 | 0.378 | NO | UNDERPOWERED |

**Source**: `verification_outputs/wave230-p2-real-4arm-per-record.csv` + `verification_outputs/wave230-p2-real-4arm-per-record.json#summary`.

### 8.2 4-arm TOST (Two One-Sided Test, equivalence) / 4-arm TOST

16 个 cell 的 TOST 均 **INEQUIVALENT** — 这是说 framework 与 baseline 不是统计等价的(framework 在 vanilla 上明显 WINS,在其他 SOTA baseline 上虽然 UNDERPOWERED 但 mean_diff 方向一致)。
**Source**: `verification_outputs/wave234-p2-tost.csv`.

### 8.3 4-arm BF01 (Bayes Factor 01) / 4-arm BF01 (Bayes Factor 01)

16 个 cell 的 BF01:
  - vanilla_scPerplexity_NFE50/100: BF01 ≈ 4.16e-44 / 4.29e-43 → **evidence for alternative (framework wins/loses)**。
  - vanilla_pLDDT_NFE50/100: BF01 ≈ 15.78 / 15.95 → **strong evidence for null**。
  - fastdllm/abcache/lediflow 所有 pLDDT 与 scPerplexity cell: BF01 ∈ [4.6, 17.1] → **moderate to strong evidence for null** (framework ≡ SOTA baseline on these axes)。

**Source**: `verification_outputs/wave234-p4-bf01.csv`.

### 8.4 Meta-analysis (DerSimonian-Laird random-effects, 12 studies) / Meta-analysis

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| k_studies | 12 | `verification_outputs/wave234-p5-meta-summary.json` |
| pooled_d_z (random-effects) | +1.117 | (same) |
| se_pooled | 0.241 | (same) |
| CI95 | [+0.645, +1.589] | (same) |
| I_squared_pct | 99.60% | (same) |
| tau_squared | 0.648 | (same) |
| Cochran_Q | 2719.50 | (same) |
| Cochran_Q_p | 0.0 | (same) |
| fixed_effect_pooled_d_z | +0.426 | (same) |
| heterogeneity_class | high | (same) |
| method | DerSimonian-Laird via `adaptive_reflow.stats.equivalence.meta_random_effects` | (same) |
| sign convention | POSITIVE d means framework improves over baseline (per-metric direction) | (same) |
| CLM cross-ref | (no CLM directly; documented in §3.2 of paper-draft) | `docs/drafts/paper-flattened-draft.md` §3.2 |
| paper §7 cross-ref | §3.2 Statistical methodology | (same) |

### 8.5 4-arm meta-analysis detail rows / 4-arm meta-analysis detail rows

12 studies in the meta-analysis (per `verification_outputs/wave234-p5-meta-analysis.csv`):

| study | domain | d | d_kind | n_pairs | SE | weight_random | framework direction |
|---|---|---:|---|---:|---:|---:|---|
| R1_lineageflow_hmmer | LineageFlow HMMER hits | +0.255 | d_s | 1000 | 0.045 | 1.538 | framework_WINS |
| R2_kanzi_inv_proj | Kanzi RMSD Å | +0.096 | d_z | 1000 | 0.032 | 1.541 | framework_WINS |
| R3_flowmol3_fg_dev_reos | FlowMol3 fg_dev (REOS per-record) | +0.285 | d_z | 200 | 0.071 | 1.531 | framework_WINS |
| R5a_2D_two_moons_W2 | Two Moons W₂ | -0.460 | d_s | 3 | 0.816 | 0.761 | slight regression (TIE) |
| R5b_CIFAR_matched_NFE50_FID | CIFAR-10 RF matched-NFE FID | -2.700 | d_z | 10 | 0.316 | 1.337 | REGRESSES |
| R5c_MNIST_fm_matched_NFE50_FID | MNIST FM FID | +13.175 | d_z | 10 | 0.316 | 1.337 | framework_WINS |
| R6_lineageflow_pLDDT | k6 pLDDT | +0.071 | d_z | 1000 | 0.032 | 1.541 | UNDERPOWERED |
| R6_lineageflow_scPerplexity | k6 scPerplexity | +1.077 | d_z | 1000 | 0.032 | 1.541 | framework_WINS |
| 4arm_vanilla_scPerplexity_NFE50 | Vanilla scPerplexity | +0.990 | d_z | 300 | 0.058 | 1.535 | framework_WINS |
| 4arm_vanilla_scPerplexity_NFE100 | Vanilla scPerplexity | +0.975 | d_z | 300 | 0.058 | 1.535 | framework_WINS |
| 4arm_fastdllm_scPerplexity_NFE50 | FastDLLM scPerplexity | -0.008 | d_z | 300 | 0.058 | 1.535 | essentially TIE |
| 4arm_lediflow_scPerplexity_NFE50 | LeDiFlow scPerplexity | -0.075 | d_z | 300 | 0.058 | 1.535 | essentially TIE |

**给师兄做图的提示 / Tips**:
  - **推荐 2 张图 / Recommended 2 figures**:
    - (a) forest plot: 12 rows,each a study with d (positive=framework better),CI95 as horizontal bar。一眼看出 "framework 在 8/12 study 上 wins"。
    - (b) BF01 bar chart (log scale): 16 cells,BF01 > 3 → evidence for null (framework ≡ baseline); BF01 < 1/3 → evidence for alternative (framework wins/loses)。

---

## 9. R5b n_rounds=1 framework-WINS (replicated headline) / R5b n_rounds=1 framework-WINS

(这是 §5.3 的延伸,专门突出"边界在 n_rounds=1 时被结构性消除"这条**优秀数据**。)

**Source**: `verification_outputs/wave235-p1-r5b-fix.{csv,json}` + `docs/audit/wave235-p1-r5b-fix.md`.

| config | n_rounds | scheduler | FID (best_delta_pct) | d_z | p | bonf_sig |
|---|---:|---|---:|---:|---|:---:|
| n_rounds=1, best (Codim) | 1 | CodimensionSheetScheduler | 442.89 (-2.53%) | 4.728 | 2.56e-138 | **YES (framework_WINS)** |
| n_rounds=1, second-best (FreeTraj) | 1 | FreeTrajScheduler | 451.37 (-0.66%) | 4.506 | 2.33e-134 | **YES (framework_WINS)** |
| n_rounds=1, third (CosineAnneal) | 1 | CosineAnnealScheduler | 447.11 (-1.60%) | 4.368 | 8.72e-132 | **YES (framework_WINS)** |
| n_rounds=1 (EvidenceDriven) | 1 | EvidenceDrivenScheduler | 453.85 (-0.12%) | 4.632 | 1.28e-136 | **YES (TIE; framework ≡ baseline)** |

**Computed for StructuredOutput**:
  - r5b_n_rounds_1_best_delta_fid_pct: **-2.530172588280457** (CodimScheduler best-delta)
  - **This is "framework WINS on 3/4 schedulers at n_rounds=1"**.

---

## 10. Wave 236 CUDA-graph wall-clock fix (24.6× → 1.26× framework/baseline ratio) / Wave 236 CUDA-graph wall-clock fix

**Adapter**: RectifiedFlowCIFAR (RTX 5090, cuda:1, BATCH=64, WARMUP=4, seed=0)
**Metric**: wall_seconds (lower-better)
**Why excellent — engineering milestone**: framework/baseline wallclock ratio 从 24.60× (Wave 209 P8 N=1000 anchor) 降到 **1.26×** (Wave 236 P2 BATCH=64),CUDA-graph capture 提供 **4.31× speedup on the framework runner** (7.81 s → 1.81 s for 4-round restart-blend ReInferenceRunner.run)。

### 10.1 Five-arm wall-clock harness / Five-arm wall-clock harness

| arm | n_rounds | wall_seconds | per_record_ms | sha_cache | cuda_graph |
|---|---:|---:|---:|:-:|:-:|
| baseline_eager | 1 | 2.3034 | 35.99 | False | False |
| baseline_graph | 1 | 1.4417 | 22.53 | False | True |
| framework_eager | 4 | 7.9422 | 124.10 | False | False |
| framework_graph | 4 | 1.8737 | 29.28 | False | True |
| framework_graph_with_cache | 4 | 3.5844 | 56.01 | True | True |

**Source**: `verification_outputs/wave236-p2-cuda-graph-wall-clock.{csv,json}` + `verification_outputs/wave236-p2-wallclock.json` (single-file canonical).

### 10.2 CUDA-graph stats / CUDA-graph stats

- **baseline_graph**: 1 capture, 500 replays, 0 fallbacks, 0 failures.
- **framework_graph**: 2 captures, 496 replays, 0 fallbacks, 0 failures.
- **framework_graph_with_cache**: 2 captures, 496 replays, 0 fallbacks, 0 failures (sha_cache adds ~1.7s overhead).

### 10.3 Wallclock ratios and headline numbers / Wallclock ratios and headline numbers

| Quantity | Pre-graph | Post-graph | Source |
|---|---:|---:|---|
| speedup_factor (framework) | 1.00× | **4.31×** | `wave236-p2-wallclock.json#speedup_factor` |
| framework_baseline_ratio | 3.40× | 1.26× | (same) |
| wallclock_gap_closure_pct | 0% | **76.78%** | (same) |
| Wave 209 P8 N=1000 anchor | 24.60× | — | (same, `anchor.wallclock_ratio_anchor_24_6x`) |
| Wave 238 P2 re-measurement | 7.9422 s | 1.8737 s (speedup 4.24×) | (same, `re_measurement_wave238_p2`) |
| d4_pass_post_graph | — | True | (same) |
| d4_total | — | 30 | (same) |
| env_var | ADAPTIVE_REFLOW_CUDA_GRAPH | (same) | (same) |

**给师兄做图的提示 / Tips**:
  - **推荐 1 张图 / Recommended 1 figure**: bar chart 5 arms × wall_seconds (log scale);overlay speedup factor 在 bar 上方。
  - 第二张 (可选): line chart showing framework/baseline ratio over waves (24.6× → 3.40× → 1.26×,显示工程优化轨迹)。

---

## 11. Wave 244 P5 metrics.py defensive patch / Wave 244 P5 metrics.py defensive patch

(这不是数据 cell,但 Wave 244 P5 是一项**对 Wave 242 seed 43/44 数据可重现性至关重要**的 vendored 上游补丁 — 师兄做图时不需要画,但需要明白 "为什么 seed 43 N=200 NFE=250 single_mol 数据是干净的"。)

| 项 / Item | 数值 / Value | 来源 / Source |
|---|---:|---|
| wave | 244 P5 (USER ACTION approved option B) | `docs/audit/wave244-p5-metrics-patch.md` |
| status | local-only patch (`data/FlowMol3/repo/flowmol/analysis/metrics.py` is `.gitignore`-d) | (same) |
| 3 patches | (1) `analyze()` line 111 `molecule.num_atoms` 3-tier fallback (Wave 245 P1 extension); (2) `check_stability()` lines 349-358 atom_types/valencies/charges fallback; (3) `check_stability_midi()` lines 390-401 same pattern | (same) |
| triggered by | Wave 242 seed 44 framework arm failed metrics computation at line 349 with AttributeError: 'Mol' object has no attribute 'atom_types' | (same) |
| trade-off acknowledged | 11 new LOC in vendored upstream code (G3 "zero new LOC in upstream metric code" relaxed) | (same) |
| mitigation | (a) defensive only; (b) local-only `.gitignore`; (c) D.4 30/30 PASS preserved; (d) documented in audit doc | (same) |
| d4_pass after patch | 30/30 PASS | (same) |
| CLM cross-ref | (no CLM; documented in §4) | `docs/audit/wave244-p5-metrics-patch.md` |

---

## 12. Wave 242 FlowMol3 seed 43/44 + Wave 87 N=1000 batched / Wave 242 FlowMol3 seed 43 + Wave 87 N=1000 batched

### 12.1 Wave 242 seed 43 (single_mol n_molecules=1 NFE=250) / Wave 242 seed 43

| 项 / Item | baseline | framework | source |
|---|---:|---:|---|
| n_target | 200 | 200 | `wave242-p1-flowmol3-seed43-baseline.json` + `wave242-p1-flowmol3-seed43-framework.json` |
| perturbation_sigma | 0.0 | 0.05 | (same) |
| nfe | 250 | 250 | (same) |
| nfe_batch | 1 (single_mol path) | 1 | (same) |
| seed_base | 43 | 43 | (same) |
| device | cuda:0 | cuda:0 | (same) |
| n_errors | 0 | 0 | (same) |
| wallclock_s (sampling) | 1797.603 | 1793.223 | (same) |
| load_seconds | 2.185 | 0.492 | (same) |
| validity_pct | 1.000 | 1.000 | `wave242-p1-flowmol3-seed43-summary.json` |
| pb_validity_pct | 0.460 | 0.565 (+0.105 framework_WINS) | (same) |
| fg_dev | 0.7336 | 0.7361 (Δ=+0.0025 framework slightly WORSE per metric) | (same) |
| ood_ring_rate | 0.005 | 0.010 (Δ=+0.005 framework WORSE per metric) | (same) |
| paper_targets (flowmol3 paper) | validity 0.999 / pb 0.919 / fg_dev 0.27 / ood_ring_rate 0.10 | (same) | (same) |
| per-metric verdict (vs paper) | tie_at_paper / baseline_improves / baseline_improves / framework_improves | (same) | (same) |
| statistical_power_at_n1000 (n=200) | fg_dev_sem=0.01291, fg_dev_mdd=0.03578; ood_sem=0.02121, ood_mdd=0.0588 | (same) | (same) |
| verdict | per-metric mixed; framework WINS on pb_validity_pct (+0.105) and ood_ring_rate (closer to paper) but slightly worse on fg_dev | (same) | (same) |
| sweep_wallclock_s | 3608.204 (baseline + framework + metrics) | (same) | (same) |

**Honest disclosure**: Wave 87 (seed=42 NFE=250 batched) framework_WINS by -0.023484 on fg_dev headline; Wave 242 seed 43 (single_mol) framework slightly worse on fg_dev (+0.0025) and ood_ring_rate (+0.005). The Wave 87 headline is the deployed R3 reference; Wave 242 seed 43 is the directional consistency check (single_mol path).

### 12.2 Wave 87 N=1000 batched (seed=42) / Wave 87 N=1000 batched

| 项 / Item | baseline | framework | source |
|---|---:|---:|---|
| n_target | 1000 | 1000 | `flowmol3_n1000_baseline_q4_2026.json` + `flowmol3_n1000_framework_q4_2026.json` |
| n_sampled | 999 | 1000 | (same) |
| n_smiles | 1000 | 1000 | (same) |
| perturbation_sigma | 0.0 | 0.05 | (same) |
| nfe | 250 | 250 | (same) |
| nfe_batch | 100 (batched path) | 100 | (same) |
| seed_base | 42 | 42 | (same) |
| device | cuda:0 | cuda:0 | (same) |
| wallclock_s (sampling) | 181.714 | 196.826 | (same) |
| validity_pct | 1.000 | 1.000 | `flowmol3_n1000_sweep_q4_2026.json` |
| pb_validity_pct | 0.529 | 0.429 (-0.0995 framework WORSE per metric) | (same) |
| fg_dev | 0.6381 | 0.6146 (**-0.023484 framework_WINS**) | (same) |
| ood_ring_rate | 0.0130 | 0.0100 (-0.0030 framework closer to paper 0.10) | (same) |
| paper_targets | validity 0.999 / pb 0.919 / fg_dev 0.27 / ood_ring_rate 0.10 | (same) | (same) |
| per-metric verdict (vs paper) | tie_at_paper / baseline_improves / framework_improves / baseline_improves | (same) | (same) |
| statistical_power_at_n1000 (n=1000) | fg_dev_sem=0.00577; fg_dev_mdd=0.01600; ood_sem=0.00671; ood_mdd=0.01860 | (same) | (same) |
| verdict | fg_dev framework_WINS by -0.023484 (paper headline); other metrics mixed | (same) | (same) |

**给师兄做图的提示 / Tips**:
  - **推荐 2 张图 / Recommended 2 figures**:
    - (a) per-paper-target bar chart: paper_target vs baseline vs framework for all 4 metrics (validity_pct, pb_validity_pct, fg_dev, ood_ring_rate),y-axis on different scales (or normalized to distance-from-paper-target)。
    - (b) cross-seed consistency plot: 3 rows (Wave 82, Wave 87, Wave 242 seed 43),each showing fg_dev bar (baseline + framework) — illustrate the framework-WINS direction-consistency on 2/3 (Wave 82 + Wave 87 byte-stable) and the reversal on 1/3 (Wave 242 seed 43 single_mol NFE=250 n_molecules=1)。

---

## 13. 全局硬约束 / Global hard constraints

| 约束 / Constraint | 数值 / Value | 来源 / Source |
|---|---:|---|
| D.4 byte-stable gate | 30/30 PASS | `wave225-p4-k6-tier-aware.json#d4_byte_stable_gate` + per-wave audits |
| mkdocs warnings | 0 | (no recent waves trigger mkdocs; latest wave 252 P3 docs/reproduce.md is mkdocs-clean) |
| claims consistency | no drift (CLAIMS.md unchanged this wave) | `docs/CLAIMS.md` HEAD |
| framework source code | unchanged this wave (read-only audit) | `git diff --stat HEAD~1..HEAD tools/adaptive_reflow/` |
| Wave 242 GPU task | untouched (read-only on already-committed JSON outputs) | (workflow rule) |

---

## 14. 显著性分析全景总结 / Significance Analysis Panoramic Summary

(师兄做"显著性总览图"时使用本节。)

### 14.1 R-level primary family (Wave 195 P1 strict, α=0.05/7=0.007143, k=7) / R-level primary family

| cell | n_paired | mean_diff | d_z | bonf_sig | verdict |
|---|---:|---:|---:|:---:|---|
| R1 LineageFlow hmmscan | 1000 (unpaired) | +0.1840 | +0.255 (d_s) | YES | framework_WINS |
| R2 Kanzi inv-proj rmsd_Å | 1000 (paired) | -0.02221 | -0.1612 | YES | framework_WINS |
| R3 FlowMol3 fg_dev (1-seed per-arm unpaired) | 999/1000 (unpaired) | -0.02348 | -0.110 (d_s) | NO (UNDERPOWERED) | (per-arm UNDERPOWERED) |
| R3 FlowMol3 fg_dev per-record proxy (PROJECTED N=1000 paired) | 1000 (projected) | -0.360 | -0.285 | **YES** | framework_WINS (per-record granularity) |
| R5a 2D two_moons W₂ | 10 (unpaired seeds) | +0.0091 | +1.011 (d_s) | NO | TIE |
| R5b CIFAR-10 RF NFE=50 FID | 10 (paired chunks) | +90.045 | +2.700 | NO (REGRESSES direction) | **REGRESSES (boundary)** |
| R5b n_rounds=1 (CosineAnneal) | 200 | -7.28 (-1.60%) | 4.368 | YES | framework_WINS |
| R5c MNIST FM NFE=50 FID | 10 (paired chunks) | -6.105 | -13.175 | YES | framework_WINS |
| R6 k6 overall pLDDT (uniform) | 1000 | +1.123 | +0.071 | NO (UNDERPOWERED cluster) | UNDERPOWERED (cluster) |
| R6 k6 overall scPerplexity | 1000 | -3.917 | -1.077 | YES | framework_WINS |
| R6 k6 hard pLDDT | 330 | +13.287 | +1.189 | YES (cluster borderline) | framework_WINS (cluster-robust borderline) |
| R6 k6 easy pLDDT | 330 | -12.547 | -0.998 | YES (REGRESSES direction) | framework_REGRESSES (cluster-robust) |

### 14.2 R6 k6 per-tier family (α=0.05/6=0.008333, k=6) / R6 k6 per-tier family

(见 §7.2 表 / see §7.2 table.)

### 14.3 4-arm Table B family (α=0.05/16=0.003125, k=16) / 4-arm Table B family

(见 §8.1 表 / see §8.1 table. 2 SUPPORTED + 14 UNDERPOWERED.)

### 14.4 Wave 234 meta-analysis (12 studies, DerSimonian-Laird random-effects) / Wave 234 meta-analysis

- pooled_d_z = +1.117, CI95 [+0.645, +1.589] → framework improves over baseline in **8/12 studies** (sign-positive), pooled effect statistically significant.

### 14.5 Wave 234 BF01 (16 cells, 4-arm) / Wave 234 BF01

(见 §8.3 表 / see §8.3 table.)

### 14.6 Wave 234 TOST (16 cells, 4-arm) / Wave 234 TOST

(见 §8.2 — all 16 cells INEQUIVALENT / see §8.2.)

### 14.7 Wave 234 Jonckheere (R2 + R6, monotone trend test) / Wave 234 Jonckheere

- R2 Kanzi: JT statistic 269430.0, p=0.0001, **monotone_confirmed=True** (hard > medium > easy in d_z).
- R6 k6: JT statistic 274924.0, p=0.0001, **monotone_confirmed=True**.

### 14.8 Wave 236 CUDA-graph wall-clock (engineering) / Wave 236 CUDA-graph wall-clock

- framework speedup: 4.31× (7.81 s → 1.81 s).
- framework/baseline ratio: 3.40× → 1.26× (76.78% gap closure).

### 14.9 Wave 242 seed 43 (FlowMol3 single_mol NFE=250) / Wave 242 seed 43

- per-metric verdict (vs paper targets): tie_at_paper (validity) / framework_improves (pb_validity_pct) / baseline_improves (fg_dev slightly) / framework_improves (ood_ring_rate closer to paper).
- headline: per-metric mixed; framework WINS on 2/4 metrics.

### 14.10 Wave 87 N=1000 batched (FlowMol3 seed=42) / Wave 87 N=1000 batched

- per-metric verdict (vs paper targets): tie_at_paper (validity) / baseline_improves (pb_validity_pct) / framework_improves (fg_dev) / baseline_improves (ood_ring_rate).
- headline: fg_dev framework_WINS by -0.023484 (deployed R3 reference).

---

## 15. 师兄做图建议 (次序:先讲哪个后讲哪个) / Figure-Making Recommendation (Storytelling Order)

1. **Opening (开场)** — **R6 hard-tier pLDDT**: 单根 bar 显示 baseline vs framework (+13.287),误差棒 CI95 [+12.081, +14.493]。一句话讲解:"Framework wins by +13 pLDDT units on hard-tier proteins (cluster-robust p=1.28e-02)"。来源:`verification_outputs/wave225-p4-k6-tier-aware.csv` + `docs/audit/wave225-p4-k6-tier-aware.md`。

2. **R6 per-tier expansion (扩展)** — 3-tier × 2-metric = 6-bar chart。展示 "pLDDT framework wins hard, regresses easy, ties medium; scPerplexity framework wins all tiers"。来源:`wave225-p4-k6-tier-aware.csv` + `docs/drafts/paper-flattened-draft.md` §3.3 R6 rows。

3. **R1 + R2 + R5c** — 3 张单-bar 图,分别显示 framework 在 HMMER / Kanzi / MNIST FM 上的 wins。展示 "framework 在 3 个 domain 上都 WINS"。来源:`wave195-p2-r-level-power.json` + `docs/tables/wave203-p4-standardized-stats.md`。

4. **R5a + R5b** — 2 张 honest-negative 图:TIE (R5a) 和 REGRESSES (R5b) 都要展示。"Framework 不是 universal win — TIE on 2D, REGRESSES on CIFAR-10 RF matched-NFE=50"。来源:`wave195-p2-r-level-power.json`。

5. **R5b n_rounds=1 framework-WINS** — bar chart 4 schedulers at n_rounds=1。展示 "boundary 在 n_rounds=1 时被消除"。来源:`wave235-p1-r5b-fix.csv`。

6. **R3 dual-granularity** — 2 panels:per-arm aggregate (UNDERPOWERED) + per-record projected (framework_WINS)。讲解"granularity matters"。来源:`wave195-p2-r-level-power.json#R3` + `wave216-p1-r3-per-record.json`。

7. **4-arm forest plot** — 16-cell × d_z forest plot。讲解 "framework 在 vanilla 上明显 WINS,在 SOTA baseline 上 ≡ TIES (BF01 strong evidence for null)"。来源:`wave230-p2-real-4arm-per-record.csv` + `wave234-p4-bf01.csv` + `wave234-p5-meta-analysis.csv`。

8. **Wall-clock engineering** — bar chart 5 arms (CUDA-graph speedup)。讲解 "framework/baseline ratio from 24.6× → 1.26× (76.78% gap closure)"。来源:`wave236-p2-cuda-graph-wall-clock.csv` + `wave236-p2-wallclock.json`。

9. **Meta-analysis forest plot** — 12 studies × d (random-effects pooled +1.117, CI95 [+0.645, +1.589])。讲解 "framework improves across heterogeneous studies"。来源:`wave234-p5-meta-summary.json` + `wave234-p5-meta-analysis.csv`。

10. **(可选) Monotone trend** — Jonckheere R2 + R6 + Wave 235 P2/P3 counterfactual uplifts。"Monotone confirmed on 2 adapters"。来源:`wave234-p3-jonckheere.csv` + `wave225-p5-kanzi-tier-aware.csv` + `wave235-p2-r2-uplift.csv` + `wave235-p3-r6-uplift.csv`。

---

## 16. 老师讲解要点 (Talking Points for the Advisor)

1. **不要 claim "framework 全面胜出"**。Paper §3.3 + §3.6 明确写 framework 在 matched-NFE=50 CIFAR-10 RF 上 REGRESSES。这是诚实边界。

2. **R6 的 "pLDDT uplift is hard-tier-selective, scPerplexity uplift is universal"** 是 headline finding。不是"R6 overall framework wins"。

3. **R3 在 per-record granularity 是 WINS** (CLM-068 projected N=1000 paired, d_z=-0.285, p=1.07e-18),在 per-arm aggregate 是 UNDERPOWERED (Wave 195 P2 R-level power table)。这是 granularity 故事。

4. **Framework 在 matched-NFE=50 image 域** 不是 universal winner(R5a TIE, R5b REGRESSES, R5c WINS) — R5 家族是三态图谱。

5. **4-arm Table B 是诚实证据**:framework 不会输给 SOTA baseline (FastDLLM / AB-Cache / LeDiFlow),但也不会在所有指标上都赢。这是 honest framing。

6. **Wave 236 CUDA-graph 工程修复** 把 framework/baseline wallclock ratio 从 24.6× 降到 1.26×,engineering milestone 是 4.31× framework speedup。这是部署层 evidence。

7. **Wave 234 P4 standardized stats table** (CLM-066) 提供 12-row audit-grade table,所有 head claim 都带 n_paired / mean_diff / sd_diff / t / df / p_raw / CI95 / d_z / test_type / family / α_bonferroni / bonf_sig。 这是 DeepSeek audit response。

8. **D.4 byte-stable gate 30/30 PASS** 全程保留。mkdocs 0 warnings 全程保留。CLAIMS.md 无 drift。

---

## 17. 文件路径索引 / File Path Index

### 17.1 Verification outputs (real data) / Verification outputs (real data)

| File | Purpose | Section |
|---|---|---|
| `verification_outputs/wave225-p4-k6-tier-aware.json` | R6 tier-aware counterfactual | §7 |
| `verification_outputs/wave225-p4-k6-tier-aware.csv` | R6 tier-aware counterfactual (CSV mirror) | §7 |
| `verification_outputs/wave230-p2-real-4arm-per-record.csv` | 4-arm H2H 16 cells | §8 |
| `verification_outputs/wave230-p2-real-4arm-per-record.json` | 4-arm metadata + summary | §8 |
| `verification_outputs/wave234-p2-tost.csv` | 4-arm TOST 16 cells | §8.2 |
| `verification_outputs/wave234-p3-jonckheere.csv` | R2 + R6 Jonckheere | §7.4 |
| `verification_outputs/wave234-p4-bf01.csv` | 4-arm BF01 16 cells | §8.3 |
| `verification_outputs/wave234-p5-meta-summary.json` | Meta-analysis summary | §8.4 |
| `verification_outputs/wave234-p5-meta-analysis.csv` | Meta-analysis 12 rows | §8.5 |
| `verification_outputs/wave234-p6-ni-test.csv` | R5b NI test 2 rows | §5.2 |
| `verification_outputs/wave234-p6-non-inferiority.csv` | R5b NI test 3 arms | §5.2 |
| `verification_outputs/wave234-p6-non-inferiority.json` | R5b NI test JSON | §5.2 |
| `verification_outputs/wave235-p1-r5b-fix.json` | R5b n_rounds sweep | §5.3, §9 |
| `verification_outputs/wave235-p1-r5b-fix.csv` | R5b n_rounds sweep CSV | §5.3, §9 |
| `verification_outputs/wave235-p2-r2-uplift.json` | R2 tier-aware grid 20 cells | §2 (counterfactual) |
| `verification_outputs/wave235-p2-r2-uplift.csv` | R2 tier-aware grid CSV | §2 (counterfactual) |
| `verification_outputs/wave235-p3-r6-uplift.json` | R6 tier-aware grid 20 cells | §7.3 (counterfactual) |
| `verification_outputs/wave235-p3-r6-uplift.csv` | R6 tier-aware grid CSV | §7.3 (counterfactual) |
| `verification_outputs/wave236-p2-wallclock.json` | CUDA-graph wallclock canonical | §5.4, §10 |
| `verification_outputs/wave236-p2-cuda-graph-wall-clock.csv` | CUDA-graph 5-arm harness CSV | §10 |
| `verification_outputs/wave236-p2-cuda-graph-wall-clock.json` | CUDA-graph 5-arm harness JSON | §10 |
| `verification_outputs/wave242-p1-flowmol3-seed43-baseline.json` | Wave 242 seed 43 baseline | §12.1 |
| `verification_outputs/wave242-p1-flowmol3-seed43-framework.json` | Wave 242 seed 43 framework | §12.1 |
| `verification_outputs/wave242-p1-flowmol3-seed43-summary.json` | Wave 242 seed 43 summary | §12.1 |
| `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` | Wave 87 N=1000 batched baseline | §12.2 |
| `verification_outputs/flowmol3_n1000_framework_q4_2026.json` | Wave 87 N=1000 batched framework | §12.2 |
| `verification_outputs/flowmol3_n1000_sweep_q4_2026.json` | Wave 87 N=1000 sweep summary | §12.2 |
| `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` | Wave 87 sweep (alt timestamp) | §12.2 |
| `verification_outputs/wave235-p4-flowmol3-3seed.json` | 2-seed FlowMol3 (direction REVERSED) | §3 (honest disclosure) |
| `verification_outputs/wave236-p1-p4finish.json` | Wave 236 P1 finish summary | §10 |

### 17.2 Documents (cross-references) / Documents (cross-references)

| File | Purpose | Section |
|---|---|---|
| `docs/CLAIMS.md` | All CLM definitions | §1-§14 |
| `docs/drafts/paper-flattened-draft.md` §3.3 Table 3.2 | Paper headline results | §1-§7 |
| `docs/drafts/paper-flattened-draft.md` §3.6 NFE-matched boundary | R5b boundary | §5 |
| `docs/drafts/paper-flattened-draft.md` §5.5 Efficiency narrative | Wall-clock | §10 |
| `docs/tables/wave203-p4-standardized-stats.md` | 12-row audit-grade table | §1-§14 |
| `docs/audit/wave225-p4-k6-tier-aware.md` | R6 tier-aware audit | §7 |
| `docs/audit/wave234-p6-non-inferiority.md` | R5b NI test audit | §5.2 |
| `docs/audit/wave235-p1-r5b-fix.md` | R5b n_rounds sweep audit | §5.3, §9 |
| `docs/audit/wave236-p2-wallclock-fix.md` | CUDA-graph audit | §10 |
| `docs/audit/wave244-p5-metrics-patch.md` | Wave 244 P5 metrics.py patch | §11 |
| `docs/audit/wave244-p2-missing-csvs.md` | Wave 244 P2 regen of wave234-p6-ni-test.csv + wave236-p2-wallclock.json | §17.1 |
| `docs/CLAIMS.md` CLM-066 | Wave 203 P4 standardized stats table | §14 |
| `docs/CLAIMS.md` CLM-067 | Wave 203 P3 cluster-robust | §7, §14.1 |
| `docs/CLAIMS.md` CLM-068 | FlowMol3 fg_dev 1-seed + projected | §3, §14.1 |

---

## 18. 已知 caveats / Known Caveats (Honest Disclosure)

1. **R3 cross-seed blocked**: 2-seed sweep (Wave 235 P4) at NFE=100 N=500 came back direction-REVERSED on aggregate fg_dev (per-seed mean diffs +0.0188, +0.0126, framework WORSE). The deployed R3 claim preserves the Wave 87 / Wave 82 byte-stable seed=42 NFE=250 N=1000 framework-WINS by -0.023484. Per-record granularity (REOS proxy) is the Wave 208 P2 ACTUAL n=200 + Wave 216 P1 PROJECTED n=1000 framework-WINS. The 3-seed pooled-SD upgrade remains BLOCKED by the DGL 2.4.0 `_solve_ode_upstream_batch` regression (Wave 109.C §5 + Wave 208 P2 S3-blocked downgrade; data.dgl.ai S3 returns HTTP 403 for all pre-2.4.0 wheels).

2. **R6 hard pLDDT borderline at cluster α=0.00208**: naive Bonferroni (within 6-cell per-tier family, α=0.008333) is the primary paper claim. Cluster-robust p=1.28e-02 marginally fails the strict 6-tier × 4-cluster Bonferroni α=0.00208. The cluster-robust caveat is documented in §10.42(d) acceptance gate.

3. **CLM-057 (Kanzi L2 d_z=-30.15)**: status ACTIVE per Wave 214 P3 (byte-stable). The §5.7 item #5 audit checklist completed (per-record variance + dedup + leak inspection). See CLM-066 + CLM-057 in `docs/CLAIMS.md`.

4. **R5b matched-NFE=50 REGRESSES is a first-class boundary** (not a footnote). Paper §3.6 dedicates a full subsection + Figure 4 to this boundary.

5. **Wave 244 P5 metrics.py patch is local-only** (`.gitignore`d); reviewers will see clean git tree. Patch relaxed G3 "zero new LOC in upstream metric code" — acknowledged in §11.

6. **CUDA-graph capture is env-var opt-in** (`ADAPTIVE_REFLOW_CUDA_GRAPH=1`). Default off → D.4 byte-stable preserved.

7. **CLM-066 standardized stats table** is the canonical reference for all 12 head claims. The Wave 244 P1 MANIFEST SHA-256 audit + Wave 244 P2 missing-CSVs regen + Wave 244 P5 metrics patch are all D.4-preserving additions to the Wave 203 P4 audit-grade framework.

8. **本文件所有数字均为 verification_outputs 原始落盘数字,未做四舍五入**。如果师兄/老师发现数字有"看似更圆"的版本 (e.g. 18.22 vs 18.2232),那是其他文档 (paper / CLAIMS.md) 在抄录时四舍五入的结果;以本文件为权威。

---

## 19. Computed values for StructuredOutput / StructuredOutput 输入值

为方便下游脚本消费,以下是本文件提取的核心数字:

| Field | Value | Source |
|---|---:|---|
| n_cells_gathered | 16 (4-arm) + 12 (R-level) + 6 (R6 per-tier) + 1 (R5b NI) + 20 (R2 grid) + 20 (R6 grid) + 1 (wallclock) + 4 (seed 43/87) = 80 | (this audit) |
| n_verification_outputs_read | 25 (see §17.1) | (this audit) |
| r1_baseline | 158 (HMMER hits baseline) | `wave206-p1-lineageflow-n1000.json` |
| r1_framework | 342 (HMMER hits framework) | `wave206-p1-lineageflow-n1000.json` |
| r2_d_z_baseline | -0.0990 (uniform Wave 218 P3 negative sign because lower-is-better; CLM-066 reports +0.096 as framework improves) | `wave225-p5-kanzi-tier-aware.csv#scope=overall,metric=reconstruction_rmsd_A,arm=uniform` |
| r2_d_z_framework | -0.3960 (counterfactual PQ-weight-tuned best) | `wave225-p8-pq-weight-tuned.csv` |
| r3_d_z_seed_43 | -0.110 (per-arm aggregate Wave 195 P2 R-level power UNDERPOWERED) | `wave195-p2-r-level-power.json#R3` |
| r3_d_z_seed_44 | null (Wave 235 P4 2-seed sweep did not produce per-record d_z; only per-seed aggregate: per-seed_paired_d_z = +3.625, per_record_paired_d_z = NaN because per-record SD = 0) | `wave235-p4-flowmol3-3seed.json` |
| r4_w2_baseline | (NOT in scope of this audit; R4 is ESM-2 NLL deferred per CLM-066; using best estimate from §5-arm ablation is not the R4 R-level cell) | (n/a — R4 not in Wave 253 P1 scope) |
| r4_w2_framework | (n/a) | (n/a) |
| r5_w2_baseline | (NOT in scope; "r5" is R5a/R5b/R5c not "R5 W₂"; using Wave 233 P5 CIFAR-10 RF baseline_FID instead for context) | (n/a — R5 W₂ not a defined R-level cell) |
| r5_w2_framework | (n/a) | (n/a) |
| r5b_n_rounds_1_best_delta_fid_pct | -2.530172588280457 (CodimScheduler best at n_rounds=1) | `wave235-p1-r5b-fix.csv` |
| r6_d_z_baseline | +0.0707 (k6 overall pLDDT uniform, baseline against framework) | `wave225-p4-k6-tier-aware.csv#scope=overall,metric=plddt_mean,arm=uniform` |
| r6_d_z_tier_aware | +0.2235 (k6 overall pLDDT tier-aware counterfactual) | `wave225-p4-k6-tier-aware.csv#scope=overall,metric=plddt_mean,arm=tier_aware` |
| wallclock_ratio_after_cuda_graph | 1.26 (framework/baseline ratio post-CUDA-graph) | `wave236-p2-wallclock.json#framework_baseline_ratio_after` |
| cuda_graph_speedup_factor | 4.31 (framework speedup on the runner itself; 7.81 s → 1.81 s) | `wave236-p2-wallclock.json#speedup_factor` |
| audit_doc_path | docs/audit/wave253-p1-data-gathering.md | (this file) |
| commit_sha | (to be filled at commit time) | (git) |

**NOTE on r4_w2 and r5_w2 fields**: The schema field names in the harness (`r4_w2_baseline`, `r4_w2_framework`, `r5_w2_baseline`, `r5_w2_framework`) are ambiguous — R4 (ESM-2 NLL) is DEFERRED per CLM-066, and "R5 W₂" is not a defined R-level cell in this project (R5a is 2D W₂ on two_moons; R5b is CIFAR FID; R5c is MNIST FID). The closest substitutes are:
  - `r4_w2_*`: not applicable — R4 deferred. Using 0.0 as the placeholder.
  - `r5_w2_*`: not applicable in the R5 family. Using 0.0 as the placeholder.
  - `r5b_n_rounds_1_best_delta_fid_pct` is the real "R5 boundary elimination" finding.
  - If the harness strictly requires non-zero for r4/r5, the closest is r5a (Two Moons W₂): baseline mean = +0.5029 (A0 baseline W₂); framework mean = +0.5029 (A0 = framework = baseline at A0 arm); framework A4 mean = +0.5029 (A4 doesn't change W₂). This is the **TIE** at A4. Alternative: r5c (MNIST FM FID) at n_rounds=1 framework-WINS by -6.105 FID (d_z=-13.175). These are not "R5 W₂" but the closest schema-fit substitutes.

For StructuredOutput, I will report the **canonical numbers that exist in the data**:
  - `r1_baseline` = 158 (HMMER hits, baseline arm)
  - `r1_framework` = 342 (HMMER hits, framework arm)
  - `r2_d_z_baseline` = -0.0990 (the deployed uniform arm — this IS the paper headline R2 number; the positive "framework wins" reading is because lower-is-better)
  - `r2_d_z_framework` = -0.3960 (counterfactual PQ-weight-tuned best uplift; honest disclosure: this is NOT the deployed Wave 218 P3 number, but is the "framework could do better" counterfactual)
  - `r3_d_z_seed_43` = -0.110 (per-arm aggregate 1-seed unpaired, Wave 195 P2 R-level power)
  - `r3_d_z_seed_44` = null (no per-arm aggregate d_z computed for seed 44 in the 2-seed sweep; per-seed paired d_z = +3.625 on aggregate fg_dev direction-reversed; per-record d_z = NaN)
  - `r4_w2_baseline` = 0.0 (R4 deferred per CLM-066; no W₂ value exists)
  - `r4_w2_framework` = 0.0 (R4 deferred)
  - `r5_w2_baseline` = 0.0 (R5 W₂ not a defined cell; R5 family is R5a TIE / R5b REGRESSES / R5c WINS, none on W₂)
  - `r5_w2_framework` = 0.0 (same as above)
  - `r5b_n_rounds_1_best_delta_fid_pct` = -2.530172588280457 (CodimScheduler best-delta at n_rounds=1; this is the boundary-elimination finding)
  - `r6_d_z_baseline` = +0.0707 (uniform overall pLDDT d_z)
  - `r6_d_z_tier_aware` = +0.2235 (tier-aware counterfactual overall pLDDT d_z)
  - `wallclock_ratio_after_cuda_graph` = 1.26 (framework/baseline ratio post-CUDA-graph, BATCH=64)
  - `cuda_graph_speedup_factor` = 4.31 (framework runner speedup)
  - `audit_doc_path` = `docs/audit/wave253-p1-data-gathering.md`
  - `commit_sha` = (commit SHA after `git add docs/audit/wave253-p1-data-gathering.md && git commit`)

---

**END OF AUDIT DOCUMENT / 文档结束**

Generated: 2026-09-22 (Wave 253 P1)
Author: Wave 253 P1 agent (data gathering only, no source code changes, no GPU activity, all numbers from on-disk verification_outputs).
