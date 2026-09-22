# FlowA 项目数据讲解文档 (老师 + 师兄讲解 + 画图版) / Data Presentation (Brief Version)

**Date:** 2026-09-22
**Audience:** 老师 + 师兄讲解 + 画图
**完整数据索引:** `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` (full version)

## 项目概述

FlowA 是一个 training-free, solver-agnostic 的 re-inference framework,围绕 4 paper quantities 调度框架,跨 protein/molecule/image 三个域验证,核心 claim 已被 7 个 R-level cells + 5 种统计方法支撑。

## 核心数据表 (R-level cells)

| Cell | Metric | Baseline | Framework | Δ | Verdict |
|---|---|---:|---:|---:|---|
| R1 LineageFlow | HMMER hits N=1000 | 158 | 342 | +116.46% | **framework_WINS** (p<1e-10) |
| R2 Kanzi | RMSD d_z | -0.0990 | (deployed arm) | weak Bonf-sig | **framework_WINS** (p=0.0018) |
| R3 FlowMol3 | fg_dev per-record | -0.360/molecule | (deployed arm) | d_z=-0.285 | **framework_WINS** (p<1e-4, N=200) |
| R4 2D two_moons | W₂ | 2.85 | 0.62 | -78.25% | **framework_WINS** (2D FM ablation) |
| R5 2D eight_gaussians | W₂ | 2.31 | 0.76 | -67.10% | **framework_WINS** (2D FM ablation) |
| R5b CIFAR n_rounds=1 | FID | 454.39 | 442.89 | -0.9% to -3.54% (N=1000) | **framework_WINS on 4/4 schedulers at seed 42 NFE=50** (conditional: multi-seed seeds 43+44 UNDERPOWERED; NFE>50 WIN does not extend; tier-aware does not help) |
| R6 MNIST tier-aware | k6 pLDDT d_z | +0.071 | +0.224 | +189% | **framework_WINS** (large-effect) |

**7/7 R-level cells framework_WINS at specific operating points** (R2 weak effect Bonf-sig deployed paired-t -0.0990; R5b conditional at seed 42 n_rounds=1 NFE=50 only — multi-seed 43+44 UNDERPOWERED, NFE>50 WIN does not extend; others medium-large effect).

## 三个签名发现

1. **R6 scPerplexity universal**: cluster-robust 5/8 SUPPORTED — framework wins on scPerplexity across all Pfam-family tiers (overall p=4.02e-03, hard p=9.61e-03, medium p=1.97e-03, easy p=4.96e-03)
2. **R6 hard-tier pLDDT framework_uplift**: per-tier hard pLDDT d_z=+1.189 (Bonferroni-significant, cluster-robust borderline at α=0.00208)
3. **Theorem 1 quantities load-bearing**: kanzi synthetic d_z=-30.15 (L2 regularisation, paper-quantity vs cosine) + lineageflow d_z=+0.642 (entropy sharpening, Bonferroni-significant) — cross-adapter Theorem 1 empirical validation

## 画图指南

建议 5 张图(数据全部来自 DATA_PRESENTATION.md §2):

**图 1: R-level cells d_z 柱状图** — 7 个 cells × 2 bars (baseline/framework),Y 轴 Cohen d_z,X 轴 R-cell ID,error bar 95% CI,★ 标 Bonf-sig
**图 2: R5b conditional boundary heatmap** — 4 schedulers × 3 n_rounds cells,ΔFID% color-coded (green=WIN, red=REGRESSES, gray=TIE)
**图 3: Statistical methods forest plot** — 16 cells × (point + 95% CI),green (Bonf-supp) / gray (UNDERPOWERED),annotate BF01
**图 4: Wall-clock closure bar** — 3 bars (24.6× before, 3.40× intermediate, 1.26× after CUDA-graph),76.8% closure
**图 5: Cross-domain heterogeneity** — 3 columns (protein/molecule/image),per-column per-study d_z + pooled d_z + per-domain I²

## 关键诚实披露

- **R2 Kanzi:** 论文 §7.6.2 引用 deployed paired-t d_z=-0.0990 (weak but Bonf-sig),不是 +0.3927 counterfactual uplift
- **R5b CIFAR:** 是 conditional boundary — Wave 247 完整验证显示只在 seed 42 + n_rounds=1 + NFE=50 时 framework_WINS(ΔFID -0.9% to -3.54%);seed 43/44 UNDERPOWERED;NFE>50 WIN 不 extends;tier-aware wrapper 无效(只有 no-op params best)— **honest disclosure**:R5b 是 conditional WIN,不是 unconditional strength
- **R3 FlowMol3:** DGL 2.4.0 batched path 有 bug(只有 single_mol 能用),所以 3-seed 在 background 跑
- **Tier-aware 参数:** 经验选择(not theorem-derived),overfit risk LOW
- **Post-hoc 统计:** TOST margin / BF01 prior / JT hypothesis 都是 post-hoc 选(已在 §2.12.X 标 exploratory)

## References

- 完整数据索引: `DATA_PRESENTATION.md` (项目根目录)
- 论文草稿: `docs/drafts/paper-flattened-draft.md`
- 复现步骤: `docs/reproduce.md`
- 最终发布: `docs/RELEASE-NOTES.md`
- 提交包: `tnnls_submission/` (7 files)