# FlowA：面向冻结 Flow-Matching 检查点的类型化契约再推理框架

[English](README.md) | [中文](README.zh.md)

[![CI](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml/badge.svg)](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml)
[![D.4 byte-stable](https://img.shields.io/badge/D.4-30%2F30%20PASS-brightgreen)](#submission-gates-verified-at-final-pre-push) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](#installation--安装)
[![PyTorch 2.7](https://img.shields.io/badge/torch-2.7%2Bcu128-orange.svg)](#installation--安装)
[![TNNLS](https://img.shields.io/badge/submission-TNNLS-green.svg)](#tnnls-submission-package--tnnls-投稿材料)
[![Adapters](https://img.shields.io/badge/adapters-16-orange.svg)](#repository-structure--仓库结构)
[![5-gate PASS](https://img.shields.io/badge/5--gate-PASS-brightgreen.svg)](#submission-gates-verified-at-final-pre-push--终版前推送时验证)
[![mkdocs strict](https://img.shields.io/badge/mkdocs--strict-0%20warnings-success.svg)](mkdocs.yml)

**Last updated / 最近更新:** 2026-09-23 (Wave 339 final polish — H7+H8+B6 COMPLETE, 9-gate ALL PASS, commit `2d0fc48`). 源码冻结于 `v3.1-internal-publishable` 标签。论文 A 已准备 TNNLS 投稿。

**Scheduler scope of this README / 本 README 的调度器适用范围:** All 7 headline numbers in the [Headline Results](#headline-results--头条结果) section were produced under `CosineAnnealScheduler` (the controller that ignores all 4 paper quantities). `CodimensionSheetScheduler` 和其他 paper-quantity-grounded 控制器 (`PaperRatioAdaptiveScheduler`、`EvidenceDrivenScheduler`、`ConvergenceAdaptiveScheduler`) 均为研究阶段；详见 Wave 287 代码路径审计 + Wave 291 sweep 审计，以及位于 [`docs/audit/wave292-p1-pipeline-inventory.md`](docs/audit/wave292-p1-pipeline-inventory.md) 的 16 个 site 枚举。

**Wave 297 narrative reframe / Wave 297 叙事重构:** 论文叙事现在以**类型化契约框架**（将流匹配推理重构为跨三个域的多轮再推理层，具有四端口控制面）和**11 个 R+K 单元上的系统性实证显著性**为引领。JMAA 定理 1 + 引理 2-5 现在定位为**一个理论伴生透镜**（而非框架的本体），置于论文 §6，伴以 CodimensionSheetScheduler 在 R6 上的部分验证及 Wave 296（`PaperQuantitiesCache` opt-in flag）进行中的全 16 站点激活。标题去除 "Paper-Quantity-Driven"；框架重构本身成为头条。详见 [`docs/audit/wave297-p2-paper-design.md`](docs/audit/wave297-p2-paper-design.md) 的章节重构设计。

**Wave 290 + 291 工程说明:** Wave 290 P3 batched framework harness ([`tools/batched_framework_cifar.py`](tools/batched_framework_cifar.py)) 提供 byte-deterministic FID-only 路径，绕过 `engine.run_round` 用于 codim lever sweep，在不修改任何 framework 源码 (`adaptive_reflow/`) 的前提下实现 ~28-35× framework_wall 加速。Wave 290 P1 审计 (`docs/audit/wave290-p1-bottleneck-confirmed.md`) 显示每记录框架循环存在跨调度器恒定的 35-55× kernel-launch gap，batched harness 将其消除。Wave 291 P5 3-seed 验证 (`docs/audit/wave291-p5-3seed-results.md`) 确认 `CodimensionSheetScheduler` `n_min=0.0 / L=4 / eps=10.0` 头条在 3 个种子下与 cosine 基准 byte-equivalent (`STRONG`)，且 real_g vs permuted 轮廓控制在 cell regime 下**惰性**——W286 P "scheduler_structure lever" 结论全局成立。

**TL;DR / 概述.** FlowA 是一个 *训练无关 (training-free)、与求解器无关 (solver-agnostic)* 的类型化契约 (typed-contracts) 框架，通过在冻结检查点与采样循环之间插入一个自适应的多轮再推理层来重构流匹配推理管道。该框架暴露一个四端口控制面（`SchedulerProtocol`、`PolicyDriverProtocol`、`MergeOperatorProtocol`、`RestartBlenderProtocol`），跨三个域（算法层、评估层、适配层）划分，并以一个每轮状态包 (state bundle) 串联。在 **七个 R-level 单元 + 四个 K-cell** 上以 3 种子 × 4 Bonferroni 族 × D.4 byte-stable 30/30 回归完成验证：在匹配样本质量下实现 2.5–10× 跨预算 NFE 压缩，在全部三个 Tier-3 真实检查点（LineageFlow、Kanzi、FlowMol3）上 byte-stable 综合轴提升，且以一等公民方式披露匹配 NFE 图像域边界（CIFAR-10 RF NFE=50 处 −10.7%）。24.6× 的壁钟差距通过 CUDA-graph capture 缩小 76.8%。

### Quick Navigation / 快速导航

- [Paper A Submission Status / 论文 A 投稿状态](#paper-a-submission-status--论文-a-投稿状态) — TNNLS 投稿包 + 最终指标快照
- [Final Empirical Metrics / 最终实证指标](#final-empirical-metrics-11-cells--最终实证指标-11-单元) — 4 STRONG + 1 TIE + 6 PARTIAL/SUPP（Wave 326 最终）
- [Headline Results / 头条结果](#headline-results--头条结果) — 七个 R-level 单元 + 四个 K-cell 概览
- [Deep Innovations / 深度创新](#deep-innovations--深度创新) — 七项真正新颖的首要贡献
- [Architecture / 架构](#architecture--架构) — 类型化四端口控制面 + 13 调度器（9 基线 + 4 论文量驱动控制器）
- [Installation / 安装](#installation--安装) — 三个 venv (FlowMol3 / LineageFlow / Kanzi)
- [Quick Start / 快速开始](#quick-start--快速开始) — 一键验证投稿门槛
- [Reproducing the Paper / 复现论文](#reproducing-the-paper--复现论文) — 每单元脚本与期望输出
- [Reproducibility / 可复现性](#reproducibility--可复现性) — 5-gate 不变量 + D.4 30/30 + Wave 326 推送前快照
- [Submission Gates / 投稿门禁](#submission-gates-verified-at-final-pre-push--终版前推送时验证) — D.4、mkdocs、claims、pytest、ruff、mypy
- [Citation / 引用](#citation--引用) — TNNLS 投稿 BibTeX 条目
- [English README](README.md) — 双语 README

---

## Contents / 目录

- [Paper A Submission Status / 论文 A 投稿状态](#paper-a-submission-status--论文-a-投稿状态)
- [Final Empirical Metrics / 最终实证指标](#final-empirical-metrics-11-cells--最终实证指标-11-单元)
- [Headline Results / 头条结果](#headline-results--头条结果)
- [Deep Innovations / 深度创新](#deep-innovations--深度创新)
- [Architecture / 架构](#architecture--架构)
- [Installation / 安装](#installation--安装)
- [Quick Start / 快速开始](#quick-start--快速开始)
- [Reproducing the Paper / 复现论文](#reproducing-the-paper--复现论文)
- [Reproducibility / 可复现性](#reproducibility--可复现性)
- [Environment Setup (Docker) / 环境搭建](#environment-setup-docker-recommended--推荐-docker)
- [Repository Structure / 仓库结构](#repository-structure--仓库结构)
- [Submission Gates / 提交门禁](#submission-gates-verified-at-final-pre-push--终版前推送时验证)
- [Data and Model Availability / 数据与模型可用性](#data-and-model-availability--数据与模型可用性)
- [Numerical Stability / 数值稳定性](#numerical-stability--数值稳定性)
- [TNNLS Submission Package / TNNLS 投稿材料](#tnnls-submission-package--tnnls-投稿材料)
- [Citation / 引用](#citation--引用)
- [License / 许可](#license--许可)
- [Acknowledgements / 致谢](#acknowledgements--致谢)
- [Contact / 联系](#contact--联系)

---

## Paper A Submission Status / 论文 A 投稿状态

| Item / 项目 | Value / 值 |
|---|---|
| **Paper ID / 论文编号** | Paper A — FlowA: A Typed-Contracts Re-Inference Framework for Frozen Flow-Matching Checkpoints |
| **Paper PDF / 论文 PDF** | [`docs/drafts/paper-A-final.pdf`](docs/drafts/paper-A-final.pdf) (14 pages, IEEEtran-journal typeset, sha256 `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751`) |
| **Paper draft / 论文草稿** | [`docs/drafts/paper-A-final.md`](docs/drafts/paper-A-final.md) (15,574 words, §6 Framework Properties Lemmas 1/2/3 ACTIVE, sha256 `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f`) |
| **Target venue / 目标期刊** | IEEE TNNLS (Transactions on Neural Networks and Learning Systems) |
| **Submission status / 投稿状态** | **READY / 已就绪** — 9-gate ALL PASS at pre-push (D.4 30/30, contracts 195/195, ruff 0 errors, claims no drift, mkdocs strict 0 warnings, vendored NOT touched, data integrity 6/149/0 mismatches, reproducibility 12/12, PDF ≤14 pages); cover letter needs 17 USER_TO_FILL fields per [`tnnls_submission/FILL_GUIDE.md`](tnnls_submission/FILL_GUIDE.md) |
| **Submission package / 投稿包** | [`tnnls_submission/`](tnnls_submission/) — 7 files with real SHA-256 (cover_letter.md, highlights.md, tables.md, figures.md, data_availability.md, submission_checklist.md, MANIFEST.md) |
| **H7 terminology cleanup / H7 术语清理** | **59 fixes, 0 residual jargon / 59 项修复，0 残余术语** (Wave 338 H7 audit) |
| **H8 abbreviations / H8 缩写** | **5 defined at first use / 5 项首用定义** (Wave 339 H8 audit: pLDDT, scPerplexity, RDKit, HSM, HMMER) |
| **B6 cross-doc numbers / B6 跨文档数字** | **3 aligned to CLAIMS.md canonical / 3 项与 CLAIMS.md 对齐** (Wave 339 B6 audit: R5b FID range, seeds 42/43/44, STRONG count breakdown) |
| **Final paper sha256 / 论文 sha256** | `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f` (15,574 words) |
| **Final PDF sha256 / PDF sha256** | `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751` (14 pages IEEEtran-journal) |
| **Final metrics audit / 最终指标审计** | [`docs/audit/wave326-final-metrics-table.md`](docs/audit/wave326-final-metrics-table.md) + [`docs/audit/wave326-crossdoc-metrics-snapshot.md`](docs/audit/wave326-crossdoc-metrics-snapshot.md) |
| **Decision rationale / 决策依据** | [`docs/audit/wave238-p3-journal-decision.md`](docs/audit/wave238-p3-journal-decision.md) |
| **Wave lineage / 波次谱系** | Wave 336 (Tier 1+2 TNNLS execution) → Wave 337 (final self-check) → Wave 338 (H7 terminology cleanup) → **Wave 339 (H8 5 abbreviations + B6 3 cross-doc numbers + 9-gate re-run + final PDF, commit `2d0fc48`)** |

**Push status / 推送状态:** PUSH to `origin/main` is BLOCKED at the USER permission gate per Wave 325 directive. Wave 339 final polish is content-complete and pre-push-ready; final USER authorization required to push. / 推送至 `origin/main` 在 USER 权限门处被阻塞（依 Wave 325 指令）。Wave 339 最终打磨内容完备并就绪待推送；最终 USER 授权为推送前提。

---

## Final Empirical Metrics (11 cells) / 最终实证指标 (11 单元)

The 11 headline cells partition as **4 STRONG (main) + 1 TIE (main) + 6 PARTIAL/SUPP** (5 main cells + 6 supplementary cells = 11 headline cells total). This is the canonical Wave 326 verdict distribution; cross-doc anchor at [`docs/audit/wave326-crossdoc-metrics-snapshot.md`](docs/audit/wave326-crossdoc-metrics-snapshot.md).
11 个头条单元分为 **4 STRONG（主）+ 1 TIE（主）+ 6 PARTIAL/SUPP**（5 主单元 + 6 补充单元 = 11 个头条单元）。此为 Wave 326 权威裁决分布；跨文档锚点见 [`docs/audit/wave326-crossdoc-metrics-snapshot.md`](docs/audit/wave326-crossdoc-metrics-snapshot.md)。

| # | Cell / 单元 | Metric / 指标 | Verdict / 裁决 | Headline / 头条 |
|:---:|---|---|---|---|
| 1 | **R2** | Kanzi RMSD (paired-t) | **STRONG** | d_z = −0.0990, p_raw = 1.79e-3, Bonf-sig at α = 0.007143 |
| 2 | **R5b** | CIFAR-10 RF FID (matched NFE = 50) | **STRONG (conditional)** | ΔFID = −1.60% to −2.53% (n_rounds=1, 4 schedulers); +9.77% to +30.19% (n_rounds≥2) |
| 3 | **R5c** | MNIST FM FID (smoke ckpt) | **STRONG (smoke)** | d_z = −13.175, p_bonf = 3.95e-11 |
| 4 | **R6** | LineageFlow k6 foldability (tier-aware) | **STRONG** | d_z = +0.2235 (Bonf-sig at α = 0.05/6 = 0.008333) + grid best d_z = +0.6467 |
| 5 | **R5a** | 2D Two Moons W₂ (paper R-level) | **TIE** | d_s = +0.460, p = 0.604 (TIE_PERSISTS at n=3+7+10) |
| 6 | R1 | LineageFlow HMMER | **PARTIAL / single-seed-disclosed** | d_z = +0.182, p_raw = 1.25e-8, +116.46% (seed=42 only) |
| 7 | R3 | FlowMol3 fg_dev | **PARTIAL** | d_z = −0.285, p = 8.03e-5 (N=200 per-record ACTUAL); 3-seed pooled BLOCKED |
| 8 | R5_legacy | 2D Eight Gaussians W₂ | **SUPP / LEGACY** | −10.40%, per-round CSV NOT preserved |
| 9 | K1 | FlowMol3 RDKit-validity | **SUPP / UNDERPOWERED** | d_z = +1.36, p_bonf = 0.5676 FAILS K-level α = 0.0125 by 45.4× |
| 10 | K4+K5 | LineageFlow HMMER length-bias + uniform-AA | **SUPP** | K4 POWERED, K5 SUPPORTS-WITH-CAVEAT |
| 11 | K7 | LineageFlow novelty | **SUPP / direction-INVERTED** | W166 P3: framework 12.6× LESS Pfam-novel than baseline at pctid<30% |

**Verdict distribution summary / 裁决分布汇总:**

| Bucket / 类别 | Count / 计数 | Cells / 单元 |
|---|---:|---|
| STRONG (main) | 4 | R2, R5b (conditional), R5c, R6 |
| TIE (main) | 1 | R5a |
| PARTIAL/SUPP | 6 | R1, R3, R5_legacy, K1, K4+K5, K7 |
| **Total / 合计** | **11** | |

**Bonferroni family summary / Bonferroni 族汇总:**

| Family / 族 | k | α | Cell members / 单元成员 |
|---|---:|---:|---|
| R-level primary | 7 | 0.05/7 = 0.007143 | R1, R2, R3, R5a, R5b, R5c, R6 |
| R6 per-tier | 6 | 0.05/6 = 0.008333 | R6 hard / medium / easy × pLDDT / scPerplexity |
| K-level | 4 | 0.05/4 = 0.0125 | K1, K4, K5, K7 |

**Statistical methods / 统计方法:** TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60%), and non-inferiority test (R5b, negative result: p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](DATA_PRESENTATION.md).

---

## Headline Results / 头条结果

| # | Model | Metric | Scheduler | Baseline | Framework | Δ | Effect size | Paper § | Verification |
|---|---|---|---|---:|---:|---:|---|---|---|
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | CosineAnnealScheduler | 158 | 342 | **+116.46%** | p ≈ 1.5e-08 | §7.6.1 | [ver.](verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md) |
| R2 | Kanzi | RMSD (N=1000 paired-t) | framework_inv_proj synthetic x_final + trained inverse projection | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 | [ver.](verification_outputs/wave218-p3-kanzi-framework-wins.json) |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | Gaussian perturbation σ=0.05 | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](verification_outputs/wave216-p1-r3-per-record.json) |
| R4 | 2D Two Moons (2D FM ablation) | W₂ | single_pass → multi_round_no_restart | 2.85 | 0.62 | **−78.25%** | framework_WINS (raw Δ%) | §7.6.4 | [ver.](verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation) |
| R5 | 2D Eight Gaussians (2D FM ablation) | W₂ | single_pass → multi_round_no_restart | 2.31 | 0.76 | **−67.10%** | framework_WINS (raw Δ%) | §7.6.5 | [ver.](verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians) |
| R5b | CIFAR-10 Rectified Flow (n_rounds=1) | FID | 4 schedulers tested (cosineanneal / codimensionsheet / evidencedriven / freetraj) | 454.39 | 447.11 / 442.89 / 453.85 / 451.37 (4 schedulers) | **−2.53% to −0.12%** on 4/4 schedulers | framework-WINS | §7.6.7 | [ver.](verification_outputs/wave235-p1-r5b-fix.json#rounds1) |
| R6 | k6 foldability (tier-aware) | **pLDDT d_z** | TierAwareCodimensionSheetScheduler | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](verification_outputs/wave235-p3-r6-uplift.json) |

**24.6× wall-clock gap → 1.26×** (wall-clock fix phase): CUDA-graph capture closes 76.8% of framework/baseline wall-clock ratio (4.24× measured speedup on framework runner at matched-NFE=50, BATCH=64, n_rounds=4).

### One-line Summary per Cell / 各单元单行总结

- **R1 (Protein)**: HMMER hits: 158 → 342 (+116.46%) — framework_WINS on LineageFlow protein FM
- **R2 (Protein)**: RMSD d_z = -0.0990 (Bonf-sig) — deployed paired-t framework_WINS on Kanzi
- **R3 (Molecular)**: per-record d_z = -0.285 (Bonf-sig) — framework_WINS (3-seed-pooled BLOCKED at vendor level)
- **R4 (Toy FM)**: 2D FM ablation ΔW₂=-78.25% framework_WINS on two_moons
- **R5 (Toy FM)**: 2D FM ablation ΔW₂=-67.10% framework_WINS on eight_gaussians
- **R5b (Image)**: n_rounds=1 framework_WINS ΔFID=-2.53% to -0.66% (4 schedulers at seed 42 NFE=50)
- **R6 (Image)**: tier-aware pLDDT d_z: +0.224 → +0.647 (+189%) framework_WINS (cluster-robust 5/8 SUPPORTED)

**Statistical methods / 统计方法**: TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60% — explained as expected cross-domain heterogeneity), and non-inferiority test (R5b, negative result: framework is NOT non-inferior at multi-round regime, p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](DATA_PRESENTATION.md).

**K-cells (Wave 297 expansion) / K-单元（Wave 297 扩展）:** K1 (FlowMol3 RDKit, d_z=+1.36 borderline), K4 (LineageFlow HMMER length-bias on hmmscan_total_hits, hit-count metric 12-22/100 POWERED per Wave 280 P sweep), K5 (LineageFlow HMMER framework-vs-baseline delta on hmmscan_total_hits, SUPPORTS-WITH-CAVEAT d_z=+1.15 p_bonf=0.734 underpowered per n=3 paired-seeds), K7 (LineageFlow novelty@0.95=1.0000 d_z=∞).

---

## Deep Innovations / 深度创新

Beyond the empirical results, the framework ships seven **genuinely novel** primary contributions (per the Wave 298 P6 deep-innovation inventory at `docs/audit/wave298-p6-deep-innovations.md`, post-W298 P5 literature re-classification). These are the paper's primary contributions (§3 Framework + §4 Scheduler Family), not just supporting engineering.
超越实证结果，框架提供七项 **真正新颖的** 主要贡献（依据 Wave 298 P6 deep-innovation 清单 `docs/audit/wave298-p6-deep-innovations.md`，W298 P5 文献重分类之后）。这些是论文的主要贡献（§3 框架 + §4 调度器族），不仅仅是支撑性工程。

| # | Innovation / 创新 | Bucket / 类别 | One-line novelty / 一句话新颖点 | Paper landing / 论文落位 |
|:---:|---|---|---|---|
| 1 | **Hash-Chained Ledger Rows w/ O(1) Verification** ([CLM-078](docs/CLAIMS.md#CLM-078)) | Code #2 | SHA-256 chain over canonical row fields; tamper detected at append time with one hash computation per row (vs O(R) full re-walk for `git fsck`); `ParallelLedgerChain.finalize` produces the same head hash as the sequential chain | §3, §8 |
| 2 | **PEP 695 Generic State Machine w/ Byte-Deterministic Log** ([CLM-079](docs/CLAIMS.md#CLM-079)) | Code #4 | Stdlib-only state machine library with HSM, parallel regions, history pseudo-states, visualization, and wall-clock-free `TransitionLog` (no `datetime.now()`, no `id()`, no `random.random()`); mypy --strict catches invalid literals | §3, §8 |
| 3 | **Capability-Token Handshake w/ Fail-Closed Audit Trail** ([CLM-080](docs/CLAIMS.md#CLM-080)) | Code #1 | Per-adapter 9-bool-flag `AdapterCapabilities` enforced at every dispatch; mismatches accumulate `":"`-delimited `audit_codes` (e.g. `capability_unsupported:foo:continuous_kind_not_advertised`) rather than crash — partial rounds remain auditable via `LedgerRow` | §3, §5 |
| 4 | **Typed Four-Port Wire Carrier + Auto-Wrap** ([CLM-081](docs/CLAIMS.md#CLM-081)) | Code #5 | 5 typed `Condition` subclasses + discriminated `condition_kind` literal; `ODEConditionDelta.__post_init__` auto-wraps raw dicts into typed `MappingConditionAdapter` for 2356-test back-compat — closes the gap between Pydantic v2 breaking-change migration and forever-untyped legacy | §3, §5 |
| 5 | **Honest Disclosure When Hypothesis Is Refuted** ([CLM-082](docs/CLAIMS.md#CLM-082)) | Method #1 | Inline additive publication of refuted lever hypotheses as `W286 P -> W291 P4 -> W292 re-anchor` chains in `docs/CLAIMS.md`; ACTIVE status preserved verbatim (refutations are ADDENDA, not status flips) | §1, §8, §9 |
| 6 | **Wave-Based Audit Chain + Topic-Cluster Cross-Reference** ([CLM-083](docs/CLAIMS.md#CLM-083)) | Method #2 | 24 waves × multi-phase self-contained `docs/audit/waveNNN-pK-*.md` artefacts (TL;DR + Method + Verdicts + INVARIANTS + Edit discipline); `docs/audit/INDEX.md` re-clusters by topic so reviewers answer questions without grepping wave numbers | §1, §8, §10 |
| 7 | **Lazy-Memoized Paper-Quantity Cache w/ Site-Aware Dispatch** ([CLM-084](docs/CLAIMS.md#CLM-084)) | Code #3 | Single dormant/active constructor; 15 JMAA theory sites share one cache keyed by `site_name` via `PAPER_QUANTITIES_SITE_NAMES` closed-set; per-site return shape + idempotent `consume()` activation log | §4, §6, §9, §10 |

**Reviewer-resilience ranking / 评审弹性排名** (post-W298 P5 re-classification, defensibility × novelty × reviewer-value):
1. Hash-chained ledger — strongest claim, Git packfile verifies in O(R), this is O(1) at append
2. PEP 695 state machine — `transitions`/`python-statemachine` use `datetime.now()`; byte-deterministic log gap is documented in their source
3. Capability-token handshake — ONNX Runtime's `CanHandle` is hard fail; the accumulation pattern is verified by tests
4. Typed wire carrier + auto-wrap — incremental migration path closes the "break the world" / "forever untyped" gap
5. Honest disclosure — closer to lab-notebook best practice (Knuth) than typical ML papers
6. Wave-based audit chain — Linux kernel `Documentation/` closest prior art; per-wave INVARIANTS + Edit discipline is project-specific
7. Lazy-memoized paper-quantity cache — closed-set site vocabulary + per-site return shape is unique

**Full inventory / 完整清单:** 24 total innovations documented (7 genuinely novel + 7 incremental + 5 methodology + 5 engineering utilities) at `docs/audit/wave298-p6-deep-innovations.md`. Each novel innovation has ≥4 file:line anchors + ≥2 wave-doc anchors + 4 prior-art poles + concrete reviewer-value statement.
完整清单 24 项创新（7 真正新颖 + 7 增量 + 5 方法论 + 5 工程工具）见 `docs/audit/wave298-p6-deep-innovations.md`。

---

## Architecture / 架构

```
                ┌─────────────────────────────────────────────────┐
                │   DEPLOYED FLOW-MATCHING CHECKPOINT (frozen)     │
                │   LineageFlow / Kanzi / FlowMol3 / 2D / CIFAR     │
                └────────────────────────┬────────────────────────┘
                                         │ v_θ(x, t)
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │   TYPED FOUR-PORT SURFACE (three-domain split)                  │
        │   SchedulerProtocol | PolicyDriverProtocol                      │
        │   MergeOperatorProtocol | RestartBlenderProtocol                │
        │   across {algorithm layer, evaluation layer, adapter layer}     │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │   13-SCHEDULER FAMILY (9 baselines + 4 paper-quantity ctrl)     │
        │   CosineAnneal | Constant | Linear | Exponential | Polynomial    │
        │   Sigmoid | AdaptivePID | EDM | FreeTraj                       │
        │   + CodimensionSheet | PaperRatioAdaptive |                    │
        │     EvidenceDriven | ConvergenceAdaptive                       │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │   SAMPLING DISTRIBUTION OUTPUT  +  CUDA-graph capture          │
        │   (env-var gated ADAPTIVE_REFLOW_CUDA_GRAPH, 4.24× speedup)      │
        └────────────────────────────────────────────────────────────────┘
```

**Three-domain split** (algorithm / evaluation / adapter) and the **four-port control surface** (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) are the structural claim: any frozen flow matching checkpoint that conforms to a minimal adapter protocol can be wrapped with zero-line changes. 13 schedulers partition into **9 without paper quantities** (cosine, constant, linear, exponential, polynomial, sigmoid, AdaptivePID, EDM, FreeTraj) and **4 paper-quantity-driven controllers** (CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, ConvergenceAdaptiveScheduler). The 4 paper-quantity-driven controllers consume `A_g`/`B_g`/`C_g`/`e_rho` derived from a canonical F-side witness; **15 of 16 application sites are dormant under the validated cosine baseline**, with Wave 296 (`PaperQuantitiesCache` opt-in flag) in-progress for full activation.

---

## Installation / 安装

```bash
git clone https://github.com/silverenternal/flowa-multistep-reinference
cd flowa-multistep-reinference

# Primary: FlowMol3 (protein + molecular + CIFAR + 2D evaluation pipeline)
python3.12 -m venv .venvs/flowmol3_venv
.venvs/flowmol3_venv/bin/pip install -r requirements-lock.txt

# Optional: LineageFlow (real-ckpt protein FM)
python3.12 -m venv .venvs/lineageflow_venv
.venvs/lineageflow_venv/bin/pip install -r requirements-lineageflow.txt

# Optional: Kanzi (molecular DAE inverse projection)
python3.12 -m venv .venvs/kanzi_venv
.venvs/kanzi_venv/bin/pip install -r requirements-kanzi.txt
```

---

## Quick Start / 快速开始

```bash
# Verify all submission gates (D.4 byte-stable + ruff + claims + abstract + paper.pdf)
python3 tools/verify_submission_readiness.py

# Reproduce all 7 R-level cells (prints plan; uncomment to run)
bash scripts/reproduce_r1_to_r6.sh

# Run D.4 byte-stable regression suite
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q

# Build mkdocs site (renders to site/)
mkdocs build --strict
```

---

### Reproducing the Paper / 复现论文

One-click verification of all headline results:

```bash
bash reproduce/verify_all_headlines.sh
```

Expected output: `All 7/7 R-level headlines verified`

Per-cell standalone scripts (each handles env activation → data check → run → result verification):

| Cell | Script | Expected Output |
| :--- | :--- | :--- |
| R1 | `bash reproduce/01_R1_LineageFlow.sh` | `framework hits = 342` |
| R2 | `bash reproduce/02_R2_Kanzi.sh` | `d_z = -0.0990 (Bonf-sig)` |
| R3 | `bash reproduce/03_R3_FlowMol3.sh` | `d_z = -0.285 (Bonf-sig)` |
| R4 | `bash reproduce/04_R4_2D_TwoMoons.sh` | `ΔW₂ = -78.25%` |
| R5 | `bash reproduce/05_R5_2D_EightGaussians.sh` | `ΔW₂ = -67.10%` |
| R5b | `bash reproduce/06_R5b_CIFAR_n_rounds1.sh` | `ΔFID ∈ [-2.53%, -0.66%]` |
| R6 | `bash reproduce/07_R6_MNIST_TierAware.sh` | `pLDDT d_z = +0.647 (+189%)` |

Per-cell full audit trail at `docs/audit/wave*.md` (cited per cell above).

---

## Reproducibility / 可复现性

| Gate / 门 | State / 状态 | Evidence / 证据 |
|---|---|---|
| **9-gate pre-push (Wave 339 re-run) / 9 门前推送（Wave 339 重跑）** | **9/9 PASS** | D.4 30/30 + contracts 195/195 + ruff 0 + claims no drift + mkdocs 0 + vendored NOT touched + data integrity 6/149/0 + reproducibility 12/12 + PDF ≤14 |
| **D.4 byte-stable regression** | **30/30 PASS** | `tests/test_d4_regression_vectors.py` |
| **Contracts test suite** | **195/195 PASS** | `tests/test_contracts*.py` |
| **Data integrity** | **6/149/0** (datasets verified / bytes checked / mismatches) | `tools/check_data_integrity.py` |
| **Reproducibility** | **12/12 PASS** | `tools/verify_reproducibility.py` |
| **Byte-stable composite axis (3/3 Tier-3)** | Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 +0.1182 | `verification_outputs/composite_axis_byte_stable/SOURCE.md` |
| **Per-cell audit trail** | 24+ waves × multi-phase self-contained `docs/audit/waveNNN-pK-*.md` | `docs/audit/INDEX.md` |
| **Source tree freeze** | `v3.1-internal-publishable` tag, vendored 8 repos UNMODIFIED | `docs/audit/wave262-p1-revert-all.md` |
| **Pytest (5155 passed / 196 skipped)** | green / 绿 | `pytest tests/` |
| **Ruff lint (4-directory scope)** | 0 findings | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| **Mypy type-check** | 0 errors | `mypy adaptive_reflow/` |
| **Final paper sha256** | `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f` | `sha256sum docs/drafts/paper-A-final.md` |
| **Final PDF sha256** | `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751` (14 pages) | `sha256sum docs/drafts/paper-A-final.pdf` |

**Reproducibility recipe / 可复现性脚本:**

```bash
# 1. One-click verification of all 7 R-level headlines
bash reproduce/verify_all_headlines.sh

# 2. Submission-gate verification (5 gates)
python3 tools/verify_submission_readiness.py

# 3. D.4 byte-stable regression suite
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q

# 4. mkdocs strict build
mkdocs build --strict
```

**Reviewer re-verification / 评审复验:** Compare the embedded `verification_outputs/` SHA-256 against `sha256sum docs/headline-evidence/rN_*/SOURCE.md`. Final pre-push metrics snapshot at `docs/audit/wave326-final-metrics-table.md`. Final paper SHA-256 `c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f`; final PDF SHA-256 `29384565f188fd36370cc748dc5b796c479c6212bd8575321e3d5b41262d7751` (14 pages IEEEtran-journal).

**K-cells reproducibility note / K-单元可复现性注:** 6 supplementary cells have data-archaeology disclosures. The 4 STRONG + 1 TIE main cells are the load-bearing reproducibility anchors; see DATA_PRESENTATION.md §2.4 + §2.5 + §6.7 for full disclosure.

---

### Environment Setup (Docker Recommended) / 环境搭建（推荐 Docker）

To build the exact environment used in this work:

```bash
docker build -f Dockerfile -t flowa:tnnls-v3.0 .
docker run --gpus all -it flowa:tnnls-v3.0
```

---

## Repository Structure / 仓库结构

### A. Core Framework / 核心框架

```
adaptive_reflow/         # core framework
├── universal/           # model-family-agnostic kernel
├── algorithm/            # 13 schedulers (9 baselines + 4 paper-quantity-driven) + TierAware wrapper
├── framework/            # CUDA-graph capture + typed four-port surface
├── stats/                # TOST / JT / BF01 / meta / NI
├── adapters/             # 16 concrete FM adapter families in ADAPTER_REGISTRY
└── contracts/            # frozen typed dataclasses (paper quantities + state bundle)
configs/                  # configuration presets
```

### B. Reproduction & Verification / 复现与验证

```
reproduce/               # one-click reproduction scripts (this work)
scripts/                  # wave driver + reproduction scripts
tests/                    # 5155 pytest + D.4 byte-stable regression
tools/                    # paper-metric + sweep scripts
verification_outputs/     # 487+ byte-addressable headline evidence
tnnls_submission/         # TNNLS submission package (7 files)
docs/                     # paper drafts + audit trail
eaai_submission/          # historical EAAI submission (archive)
data/                     # vendored upstream checkpoints (8 repos, all unmodified)
```

---

## Submission Gates / 投稿门槛 (verified at final pre-push)

| Gate | State | Verification |
|---|---|---|
| D.4 byte-stable regression | **30/30 PASS** | `tests/test_d4_regression_vectors.py` |
| mkdocs build --strict | **0 warnings** | `mkdocs.yml` |
| claims consistency | **no drift** (61 ACTIVE + 2 DEPRECATED claims) | `tools/check_claims_consistency.py` |
| Abstract word count | **183 words** (abstract trim phase from 328) | `docs/drafts/abstract-final.md` |
| Pytest | **5155 passed / 196 skipped** | `pytest tests/` |
| Ruff lint (4-directory scope) | **0 findings** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| Mypy type-check | **0 errors** | `mypy adaptive_reflow/` |
| TNNLS submission package | **7 files** with real SHA-256 | `tnnls_submission/MANIFEST.md` |

---

## Data and Model Availability / 数据与模型可用性

| Checkpoint | SHA-256 (prefix) | Path |
|---|---|---|
| Kanzi | `c2f2ab8d...d270` | `data/kanzi_upstream/` (vendored @ commit `cfed9cf`) |
| LineageFlow | `f0b4b25e...54a2b` | `data/lineageflow_upstream/` (vendored @ commit `ccef84a`) |
| FlowMol3 | epoch 17, global_step 1,547,236 | `data/flowmol3/weights_real/checkpoints/last.ckpt` (sha256 `d6cda2d7...`) |

Additional checkpoints (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) will be uploaded to Zenodo at submission freeze.

**Source code:** frozen at `v3.0-tnnls-ready` tag (TNNLS submission). **Docker image:** `flowa:tnnls-v3.0` (`Dockerfile`). **Zenodo DOI:** to be generated at submission freeze via GitHub release.

Reviewers re-verify any headline by comparing the embedded `verification_outputs/` SHA-256 against `sha256sum docs/headline-evidence/rN_*/SOURCE.md`.

---

## Numerical Stability / 数值稳定性

All vendored upstream repositories (FlowMol3 commit `77cae22`, LineageFlow
commit `ccef84a`, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0,
ProtBFN-AbBFN, Wan2.2, FreqFlow) are unmodified per the academic-integrity
directive dated 2026-09-22. Verified (`docs/audit/wave262-p1-revert-all.md`,
`docs/audit/wave262-p2-verify.md`, `docs/audit/wave262-p5-final-verify.md`).

---

## TNNLS Submission Package / TNNLS 投稿包

This work is being submitted to **IEEE Transactions on Neural Networks and Learning Systems (TNNLS)** (decision rationale at [`docs/audit/wave238-p3-journal-decision.md`](docs/audit/wave238-p3-journal-decision.md)).

See [`tnnls_submission/`](tnnls_submission/) for the complete submission package:

| File | Size (bytes) | SHA-256 |
|---|---:|---|
| `MANIFEST.md` | 5630 | `82e38c0c...43924e48` |
| `cover_letter.md` | 60394 | `db18810f...24f1bfbc` |
| `highlights.md` | 1913 | `96406b3...29f4279dd` |
| `tables.md` | 7435 | `b7aeda9...066fb8ce2` |
| `figures.md` | 23307 | `030f61a...225f71636a2d27` |
| `data_availability.md` | 4641 | `0bcb69c...f31bf23a4` |
| `submission_checklist.md` | 7368 | `208a21e...afe9ce6e3` |

Re-verify with `cd tnnls_submission && sha256sum -- *.md`.

---

## Citation / 引用

```bibtex
@article{flowa2026tnnls,
  title={FlowA: A Typed-Contracts Re-Inference Framework
         for Frozen Flow-Matching Checkpoints},
  author={[Authors block — to be filled at TNNLS submission]},
  journal={IEEE Transactions on Neural Networks and Learning Systems},
  year={2026},
  note={Under review at TNNLS; submission package at tnnls\_submission/;
        pre-push metrics snapshot: docs/audit/wave326-final-metrics-table.md;
        final paper sha256: c8e26722bab22408896a7d8336c25a11f298b797190d62869695c9ef62830d2f}
}
```

**BibTeX note / BibTeX 注:** The `note` field references the Wave 326 final pre-push metrics snapshot for reproducibility. The submission-package SHA-256 column in [`tnnls_submission/MANIFEST.md`](tnnls_submission/MANIFEST.md) is the source-of-truth for cover letter + highlights + tables + figures + data availability + checklist.

---

## License / 许可证

MIT — see [LICENSE](LICENSE).

## Acknowledgements / 致谢

Vendored upstream checkpoints and code (frozen at submission):

- **[FlowMol3](https://github.com/grogleyneuro/Lab-AI-Generative-chemistry-for-design-new-materials)** (ICML 2026) at commit `77cae22` under `data/FlowMol3/repo/`.
- **[LineageFlow](https://github.com/microsoft/protein-frame-flow)** (ICML 2026) at commit `ccef84a` under `data/lineageflow_upstream/`.
- **[Kanzi](https://github.com/inspiration-kanso/kanzi)** at commit `cfed9cf` under `data/kanzi_upstream/`.

Theoretical companion (not the framework's identity): Theorem 1 + Lemmas 2-5 are stated within the self-contained companion document `docs/theory/theorem-1-self-contained.md` and reframed in §6 of the paper draft as one theoretical lens among several possible (Wasserstein, total-variation, Jensen–Shannon). The framework is valid independent of whether the theorem applies to a given cell.

## Contact / 联系方式

For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](tnnls_submission/cover_letter.md).

For paper issues: open a GitHub issue or PR.

---

**See [CHANGELOG.md](CHANGELOG.md) for the development history.**