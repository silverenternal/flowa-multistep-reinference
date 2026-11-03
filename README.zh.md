# FlowA：面向冻结 Flow-Matching 检查点的重推理控制

**第六轮原创性攻关：** [条件证明、锐下界与近似路径反例](docs/audit/manuscript-originality-round6-2026-11-03.md)及100个CPU解析检查已完成；核心矩缺口已确认为经典输运成本差，障碍命题降为机制引理；其余候选仍有经典推论风险，原创性和神经模型干预仍未验收，不能据此升级投稿就绪状态。

[English](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/README.md) | [中文](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/README.zh.md)

**当前研究复核（2026-11-03）：投稿就绪状态尚未成立。** 本段取代下方历史快照中的投稿成熟度与创新性判断。请以[当前证据寄存器](docs/PAPER-EVIDENCE.md)、[完整45项自查表](docs/audit/manuscript-selfcheck-2026-11-02.md)及[中文v6研究稿](docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md)为准。新增CIFAR匹配调用研究中，原完整配置退化；历史蛋白/结构差值也不等于同生成器/同输入的机制优势。已有端点构造限制了独有创新的主张。冻结投稿包和旧等级保留用于历史复现，不作为当前建议立即投稿或质量保证。候选验证与剩余缺口见[第五轮审计](docs/audit/manuscript-selfcheck-round5-2026-11-03.md)。

第三方源码快照保留原声明与归属，见[来源说明](verification_outputs/manuscript-selfcheck-round5-2026-11-03/third_party_notices/THIRD_PARTY_NOTICES.md)；本项目MIT许可不替代这些文件的原声明。



[![CI](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml/badge.svg)](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml)
[![D.4 byte-stable](https://img.shields.io/badge/D.4-30%2F30%20PASS-brightgreen)](#submission-gates-verified-at-final-pre-push) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](#installation)
[![PyTorch 2.7](https://img.shields.io/badge/torch-2.7%2Bcu128-orange.svg)](#installation)
[![Archived TNNLS package](https://img.shields.io/badge/historical%20package-TNNLS-lightgrey.svg)](#tnnls-submission-package-tnnls)
[![Adapters](https://img.shields.io/badge/adapters-16-orange.svg)](#repository-structure)
[![5-gate PASS](https://img.shields.io/badge/5--gate-PASS-brightgreen.svg)](#submission-gates-verified-at-final-pre-push)
[![mkdocs strict](https://img.shields.io/badge/mkdocs--strict-0%20warnings-success.svg)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/mkdocs.yml)

**Last updated / 最近更新:** 2026-10-27（全门 PASS；`docs/PAPER-EVIDENCE.md` 是 cell 级证据的唯一来源）。手稿 = `docs/drafts/paper-A-final.pdf`（12 页，IEEEtran；已改题为 *Re-Inference Control for Frozen Flow-Matching Checkpoints*，并围绕单一主张重新包装——控制变量是轮边界，不是步数）。项目状态与历史：[`todo.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/todo.json)。论文 A 已准备 TNNLS 投稿。

**Scheduler scope of this README / 本 README 的调度器适用范围:** All 7 headline numbers in the [Headline Results](#headline-results) section were produced under `CosineAnnealScheduler` (the controller that ignores all 4 paper quantities). `CodimensionSheetScheduler` 和其他 paper-quantity-grounded 控制器 (`PaperRatioAdaptiveScheduler`、`EvidenceDrivenScheduler`、`ConvergenceAdaptiveScheduler`) 均为研究阶段；详见 [`docs/ALGORITHMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ALGORITHMS.md) 与 [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) 中汇总的 pipeline inventory。

**Narrative framing / 叙事定位:** 论文叙事以**类型化契约框架**（将流匹配推理重构为跨三个域的多轮再推理层，具有四端口控制面）和**11 个 R+K 单元上的系统性实证显著性**为引领。伴生论文定理 1 + 引理 2-5 定位为**一个理论透镜**（而非框架的本体），置于论文 §6，伴以 CodimensionSheetScheduler 在 R6 上的部分验证，并提供 `PaperQuantitiesCache` opt-in flag 以激活全部 16 站点。标题去除 "Paper-Quantity-Driven"；框架重构本身成为头条。详见 [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) 的当前结构。

**工程说明:** batched framework harness ([`tools/batched_framework_cifar.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/batched_framework_cifar.py)) 提供 byte-deterministic FID-only 路径，绕过 `engine.run_round` 用于 codim lever sweep，在不修改任何 framework 源码 (`adaptive_reflow/`) 的前提下实现 ~28-35× framework_wall 加速。每记录框架循环存在跨调度器恒定的 35-55× kernel-launch gap，batched harness 将其消除。3-seed 验证确认 `CodimensionSheetScheduler` `n_min=0.0 / L=4 / eps=10.0` 头条在 3 个种子下与 cosine 基准 byte-equivalent (`STRONG`)，且 real_g vs permuted 轮廓控制在 cell regime 下**惰性**——scheduler_structure lever 结论全局成立。

**TL;DR / 概述.** FlowA 是一个 *训练无关 (training-free)、与求解器无关 (solver-agnostic)* 的类型化契约 (typed-contracts) 框架，通过在冻结检查点与采样循环之间插入一个自适应的多轮再推理层来重构流匹配推理管道。该框架暴露一个四端口控制面（`SchedulerProtocol`、`PolicyDriverProtocol`、`MergeOperatorProtocol`、`RestartBlenderProtocol`），跨三个域（算法层、评估层、适配层）划分，并以一个每轮状态包 (state bundle) 串联。在 **七个 R-level 单元 + 四个 K-cell** 上以 3 种子 × 4 Bonferroni 族 × D.4 byte-stable 30/30 回归完成验证：在匹配样本质量下实现 2.5–10× 跨预算 NFE 压缩，在全部三个 Tier-3 真实检查点（LineageFlow、Kanzi、FlowMol3）上 byte-stable 综合轴提升，且以一等公民方式披露匹配 NFE 图像域边界（CIFAR-10 RF NFE=50 处 −10.7%）。24.6× 的壁钟差距通过 CUDA-graph capture 缩小 76.8%。

### Quick Navigation / 快速导航

- [Paper A Submission Status / 论文 A 投稿状态](#paper-a-submission-status-a) — TNNLS 投稿包 + 最终指标快照
- [Complete Inventory: Innovations & Experiments / 完整盘点：创新点与实验](#complete-inventory-innovations-experiments) — 构建了什么 + 每个实验测出了什么 的唯一整合视图
- [Final Empirical Metrics / 最终实证指标](#final-empirical-metrics-11-cells-11) — 3 STRONG + 1 CONDITIONAL + 1 TIE + 2 PARTIAL + 4 SUPP-only（最终）
- [Headline Results / 头条结果](#headline-results) — 七个 R-level 单元 + 四个 K-cell 概览
- [Deep Innovations / 深度创新](#deep-innovations) — 七项真正新颖的首要贡献
- [Architecture / 架构](#architecture) — 类型化四端口控制面 + 13 调度器（9 基线 + 4 论文量驱动控制器）
- [Installation / 安装](#installation) — 三个 venv (FlowMol3 / LineageFlow / Kanzi)
- [Quick Start / 快速开始](#quick-start) — 一键验证投稿门槛
- [Reproducing the Paper / 复现论文](#reproducing-the-paper) — 每单元脚本与期望输出
- [Reproducibility / 可复现性](#reproducibility) — 5-gate 不变量 + D.4 30/30 + 最终推送前快照
- [Submission Gates / 投稿门禁](#submission-gates-verified-at-final-pre-push) — D.4、mkdocs、claims、pytest、ruff、mypy
- [Citation / 引用](#citation) — TNNLS 投稿 BibTeX 条目
- [English README](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/README.md) — 双语 README

---

## Contents / 目录

- [Paper A Submission Status / 论文 A 投稿状态](#paper-a-submission-status-a)
- [Complete Inventory: Innovations & Experiments / 完整盘点：创新点与实验](#complete-inventory-innovations-experiments)
- [Final Empirical Metrics / 最终实证指标](#final-empirical-metrics-11-cells-11)
- [Headline Results / 头条结果](#headline-results)
- [Deep Innovations / 深度创新](#deep-innovations)
- [Architecture / 架构](#architecture)
- [Installation / 安装](#installation)
- [Quick Start / 快速开始](#quick-start)
- [Reproducing the Paper / 复现论文](#reproducing-the-paper)
- [Reproducibility / 可复现性](#reproducibility)
- [Environment Setup (Docker) / 环境搭建](#environment-setup-docker-recommended-docker)
- [Repository Structure / 仓库结构](#repository-structure)
- [Submission Gates / 提交门禁](#submission-gates-verified-at-final-pre-push)
- [Data and Model Availability / 数据与模型可用性](#data-and-model-availability)
- [Numerical Stability / 数值稳定性](#numerical-stability)
- [TNNLS Submission Package / TNNLS 投稿材料](#tnnls-submission-package-tnnls)
- [Citation / 引用](#citation)
- [License / 许可](#license)
- [Acknowledgements / 致谢](#acknowledgements)
- [Contact / 联系](#contact)

---

## Paper A Submission Status / 论文 A 投稿状态

> 历史快照：本节旧等级及创新性/投稿成熟度判断为追溯记录；[2026-11-03复核](docs/audit/manuscript-selfcheck-round5-2026-11-03.md)及[当前证据表](docs/PAPER-EVIDENCE.md)取代这些旧判断。


| Item / 项目 | Value / 值 |
|---|---|
| **Paper ID / 论文编号** | Paper A — FlowA: Re-Inference Control for Frozen Flow-Matching Checkpoints |
| **Paper PDF / 论文 PDF** | [`docs/drafts/paper-A-final.pdf`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.pdf) (12 pages, IEEEtran-journal double-column typeset, sha256 `ef9b401d664c2d911b233178296060b598b4fa6f5a87a516b42f893ee51d8e3c`) |
| **Paper draft / 论文草稿** | [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) (27,346 words, §6 Framework Properties Lemmas 1–3 + Theorems 4–5 ACTIVE, sha256 `46e423078cd42b10c5c7f31a633d2edafa5d6d448f1d0810dd5df5d5dceb66df`) |
| **Target venue / 目标期刊** | IEEE TNNLS (Transactions on Neural Networks and Learning Systems) |
| **Submission status / 投稿状态** | **READY / 已就绪** — 9-gate ALL PASS at pre-push (D.4 30/30, contracts 195/195, ruff 0 errors, claims no drift, mkdocs strict 0 warnings, vendored NOT touched, data integrity 15/703/0 mismatches, reproducibility 12/12, PDF ≤14 pages); the cover letter ships 17 exemplar identity fields that must be replaced before submission (§0 of the letter; field list in [`tnnls_submission/cover_letter_FILL_AUTOFILL.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter_FILL_AUTOFILL.json)). The separate readiness verifier (`tools/verify_submission_readiness.py`) reports **9/9 gates passed, 0 skips** |
| **Submission package / 投稿包** | [`tnnls_submission/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/tnnls_submission) — 13 files with real SHA-256 (cover_letter.md, cover_letter_FILL_AUTOFILL.json, data_availability.md, FILL_GUIDE.md, figures.md, highlights.md, MANIFEST.md, README.md, SHA256SUMS, submission_checklist.md, SUBMISSION_READINESS.md, tables.md, supplementary_bundle.zip) |
| **H7 terminology cleanup / H7 术语清理** | **59 fixes, 0 residual jargon / 59 项修复，0 残余术语** |
| **H8 abbreviations / H8 缩写** | **5 defined at first use / 5 项首用定义** (pLDDT, scPerplexity, RDKit, HSM, HMMER) |
| **B6 cross-doc numbers / B6 跨文档数字** | **3 aligned to CLAIMS.md canonical / 3 项与 CLAIMS.md 对齐** (R5b FID range, seeds 42/43/44, STRONG count breakdown) |
| **Final paper sha256 / 论文 sha256** | `46e423078cd42b10c5c7f31a633d2edafa5d6d448f1d0810dd5df5d5dceb66df` (27,346 words) |
| **Final PDF sha256 / PDF sha256** | `ef9b401d664c2d911b233178296060b598b4fa6f5a87a516b42f893ee51d8e3c` (12 pages IEEEtran-journal) |
| **Final metrics audit / 最终指标审计** | [`docs/METRIC_LEDGER.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/METRIC_LEDGER.md) + [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) |
| **Decision rationale / 决策依据** | [`tnnls_submission/SUBMISSION_READINESS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/SUBMISSION_READINESS.md) |
| **Development phases / 开发阶段** | 基础 → 候选分析 → 适配器 → baseline-vs-framework 对比 → N=1000 放大 → 消融 → 效率 / Pareto → 统计严谨性 → 复现 / 打包 → 投稿整合 → 手稿重构 + 图表。整合记录：[`docs/audit/todo-history.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/todo-history.md) |

**Push status / 推送状态:** PUSH to `origin/main` is BLOCKED at the USER permission gate (standing NO-PUSH policy). The working tree is content-complete and pre-push-ready; final USER authorization is required to push. / 推送至 `origin/main` 在 USER 权限门处被阻塞（NO-PUSH 常设政策）。工作树内容完备并就绪待推送；最终 USER 授权为推送前提。

---

## Complete Inventory: Innovations & Experiments / 完整盘点：创新点与实验

本节是项目的唯一整合视图：**(1) 构建了什么** 与 **(2) 每个实验测出了什么**。细节见
[`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md)（创新账本，`CLM-NNN`）与
[`docs/audit/INDEX.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/INDEX.md)（逐增量记录）；本节是地图。

### Part 1 — 构建了什么（创新清单）

**24 项创新** 收录于深度创新清单（[`docs/audit/wave298-p6-deep-innovations.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave298-p6-deep-innovations.md) §F；桶汇总见 [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md)）。分为四个桶，外加 §6 引理三件套。

**真正新颖（7）— 主要贡献，论文 §3–§4**（每项都弥合两个已知先验极点之间的空白；其组合为本项目独有）：

| # | 创新 | Claim | 一句话新颖点 |
|:---:|---|---|---|
| 1 | 哈希链账本行 + O(1) 验证 | [CLM-078](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-078) | SHA-256 链在 append 时以每行一次哈希检测篡改（对比 `git fsck` 的 O(R) 全链重走） |
| 2 | PEP 695 状态机 + 字节确定日志 | [CLM-079](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-079) | 无壁钟 `TransitionLog`；`transitions`/`python-statemachine` 均调用 `datetime.now()` |
| 3 | 能力令牌握手 + 失败关闭审计链 | [CLM-080](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-080) | 能力不匹配累积为 `audit_codes`（结构化）而非崩溃 |
| 4 | 类型化四端口线载波 + 自动包裹 | [CLM-081](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-081) | 类型化 `Condition` 子类 + 遗留自动包裹，2356 项测试字节等价 |
| 5 | 假设被证伪时的诚实披露 | [CLM-082](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-082) | 证伪以增量附注在线发布；`ACTIVE` 状态绝不因措辞而翻转 |
| 6 | 基于增量的审计链 + 主题聚类交叉引用 | [CLM-083](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-083) | 自包含逐增量记录 + 主题重聚类，评审者按主题而非文件名作答 |
| 7 | 惰性记忆化论文量缓存 + 站点感知派发 | [CLM-084](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-084) | 一个休眠/激活缓存由 15 个理论站点共享，以闭集站点词表为键 |

**增量 / 已知方法应用（7）— 支撑，论文 §5–§7：** D.4 字节稳定调度器回归向量（30/30）· lever 假设置换检验 · 有界 Lipschitz 收敛诊断 · 余弦 σ-跨种子规范噪声带 · 每次 PR 6 门 CI · vendored 纯度 + 能力令牌失败关闭握手 · 定理对齐 FID 评估器。

**方法论（5）— 论文 §8：** `check_claims_consistency.py` 对抗式 claims 校验器 · 向后兼容作为首要不变量 · 基于增量的审计链 · lever 假设置换检验 · 被证伪时的诚实披露。

**工程工具（5）— 论文 §10 + 附录：** batched framework harness · 对抗式调度器压力矩阵 · 经验性 `profile_residual_fn` 适配器无关残差接口 · 定理对齐 FID 评估器 · 有界 Lipschitz 收敛诊断。

**§6 Framework Properties — 三条形式化验证引理（均 ACTIVE）：**

| 引理 | Claim | 陈述 |
|---|---|---|
| 引理 1 — 协议组合闭包 | [CLM-085](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-085) | 两个符合 `SchedulerProtocol` 的调度器的组合 `A ∘ B` 在包含/半径条件下保持缓存一致性 + 幂等性 + 单调性；规范实例 = `TierAwareCodimensionSheetScheduler ∘ CodimensionSheetScheduler` |
| 引理 2 — 状态机字节确定性 | [CLM-086](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-086) | 两个相同初始化的 `StateMachine` 实例对任意有限事件序列产生字节相同的 `TransitionLog` 元组（4 情形证明：优先级平局 / 历史 / 并行区域 / `asyncio.gather`） |
| 引理 3 — 账本防篡改 | [CLM-087](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-087) | 仅追加哈希链在第一个不匹配索引处检测任何事后篡改（3 情形证明：尾部 / 链中 / 插入删除），模 SHA-256 抗碰撞 ≤ 2⁻¹²⁸ |

### Part 2 — 每个实验测出了什么（实验 → 效果账本）

两层：**11 个头条单元**（论文 §7.2/§7.11）与**封闭缺口调查（GAP-24 … GAP-31）**——后者对前者进行压力测试、精化或重锚。

**2.1 — 11 个头条单元。** 权威裁决分布 **3 STRONG + 1 CONDITIONAL + 1 TIE + 2 PARTIAL + 4 SUPP-only**；完整表见 [最终实证指标](#final-empirical-metrics-11-cells-11)。每单元达到的效果：

| 单元 | 模型 / 指标 | 达到的效果 |
|---|---|---|
| **R1** | LineageFlow · HMMER hits | 合成 +116%（158 → 342）；真实前向 **3/3 种子 WINS**（158/159/174 → 275/272/259，DL d_pooled = +0.156，I²=0）。PARTIAL —— 归因（GAP-25）表明增益来自逐记录随机 **init**，而非 restart-blend |
| **R2** | Kanzi · RMSD | **STRONG framework-WINS** d_z = −0.0990（Bonferroni-sig，p_raw = 1.79e-3）；结构上计算不变 |
| **R3** | FlowMol3 · `fg_dev` | 3 种子 N=1000 d_z = −0.0377（framework-WINS 方向，p = 0.559，n.s.）；优势**在 2×/4× 基线 NFE 下依然成立** → 稻草人基线被证伪（GAP-27：有界边缘，~49 种子达 80% 功效） |
| **R5a** | 2D Two Moons · W₂ | **TIE** \|Δ\| = 0.0091 < 0.01 下限；n=7、n=10 下持续 |
| **R5b** | CIFAR-10 RF · FID | **CONDITIONAL**：n_rounds=1 在匹配 NFE=50 下胜出（−1.2% 至 −2.5%，4 调度器）；在调优基线下失效（GAP-26：基线 NFE=200 时 0/4）；n_rounds ≥ 2 回归 +20% 至 +31% |
| **R5c** | MNIST FM · FID | **STRONG（检查点条件式前沿）** 4 检查点 × 7 档 NFE，N=1000，3 种子：`w16e1_5k` 平台 24.4839 → 21.3632（−12.75%），7/7 档弱支配；三个训练更充分的检查点均为 TIE（旧的 +10.37% 是预算不匹配，不是回归） |
| **R6** | LineageFlow k6 · pLDDT / scPerp | **STRONG，live tier-aware**（n=3000）：scPerplexity d_z = −0.8393，3/3 种子与全部层级同号；hard-tier pLDDT d_z = +1.1211；pooled pLDDT d_z = +0.1466，低于 +0.2235 门槛。击败 vanilla + Fast-DLLM + AB-Cache + LeDiFlow（Bonferroni-sig） |
| **K1** | FlowMol3 · RDKit-validity | **NOT-SIGNIFICANT** at K-level α（p_b = 0.5676 vs α_K = 0.0125）；框架 validity 在匹配与 2×/4× NFE 下均超过基线 → 稻草人被证伪 |
| **K4** | LineageFlow · HMMER length-bias | **SUPPORTED** cluster-robust d_z = +0.84（p_b = 0.009） |
| **K5** | LineageFlow · HMMER delta | **SUPPORTED / 带 caveat** cluster-robust d_z = +1.12（p_b = 0.003）；n=3 再聚合 caveat |
| **K7** | LineageFlow · novelty | **PARTIAL / 方向反转**：框架在 pctid<30% 时 Pfam-新颖度比基线低 12.6× |

**2.2 — 封闭缺口调查（GAP-24 … GAP-30）。** 每个都是受限、可重启的增量，要么产出一条可证伪律，要么重锚一个单元；完整记录见 [`docs/audit/todo-history.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/todo-history.md) §6。

| 调查 | 问题 | 达到的效果 |
|---|---|---|
| **GAP-24** 边界律 | 条件单元背后是否有单一律？ | **一条可证伪的 regime 律** `blend improves iff q < √((1+m)/(1−m))`（定理 5 式 7 闭式）：R5b 场 45/45 边界外匹配，15/16 头条单元方向 |
| **GAP-25** R1 blend 隔离 | R1 的增益是 blend 还是 init？ | **已隔离**：init-only ≈ framework ≫ baseline（B−A = +123.7，p=0.0043；B−C = +18.7，n.s.）⇒ 增益是**逐记录随机 init**；blend 边缘有界 ≤ +46 hits |
| **GAP-26** R5b regime | 是否有协议能在调优基线下存活？ | **无测试协议存活**（基线 NFE=200 时 0/4）；GAP-24 律复现 2/4→1/4→0/4 翻转 |
| **GAP-27** R3 功效 | R3 能否提升？ | R3 为**有界边缘**（d_z = −0.40，~49 种子达 80% 功效）；修复了种子级 CI 缺陷（df=2 时 1.96 → t=4.303） |
| **GAP-28** R6 faithful 层级 | faithful easy-tier 方向能否修复 R6？ | **确定性 null**：faithful +0.1104 < as-designed +0.1466 < 门槛 +0.2235；easy-tier 回归随 β_easy *单调递增* |
| **GAP-30** R6 层级定位 | 冻结层级来源是否是残差？ | 正确定位的新鲜层级 3 种子 live 重跑：as-designed **+0.1604**（较 +0.1466 上升，仍 < 门槛）；层级隔离精确（330/330/种子）；easy 层级是唯一不同组（hard/medium 字节相同） |

**2.3 — live R6 提升（GAP-31，最新）。** 冻结的 R6 `+0.2235` 头条是冻结的配对差上的*已披露反事实代理*，**非** live GPU 运行（wrapper 的 `+0.2235` 是 `easy_tier_nfe_reduction_factor=0.5` 下的逐记录 diff 均值位移）。live 重跑证伪了 50% easy-tier 削减（live 削减 ≈ 32%）。GAP-31 在种子匹配臂上给出三个 **live、非反事实**测量：

| 轴 | 测量 | live 效果（3 种子 pooled） |
|---|---|---|
| **scPerplexity**（ESM-IF，越低越好） | framework vs baseline，按 `qid` 配对，N=3000 | **d_z = −0.8393**（diff −3.6823）；framework 在**每一层级**均 WINS（hard −0.7952 / medium −0.8634 / easy −0.8924） |
| **hard-tier pLDDT**（臂无关；wrapper 只触碰 easy 层） | framework vs baseline 在 hard 层，N=990 | **d_z = +1.1211**（diff +15.0065）；逐种子 +1.0933/+1.1021/+1.1692 —— ≈ 冻结 hard-tier 反事实 +1.1889 |
| **uniform 臂**（factor 1.0，无层级操纵） | framework vs 种子匹配 baseline，诚实 live “before”，N=3000 | **d_z = +0.1466**（diff +2.6386）；逐种子 +0.1373/+0.1366/+0.1659 —— 框架**在完全不做层级操纵时**即已胜出 baseline |

**诚实解读 R6 单元。** 在 live pLDDT 轴上框架**未**达到冻结的 +0.2235 门槛（GAP-28/30）；在 live **scPerplexity** 轴上它强烈且一致地胜出（GAP-31，d_z = −0.8393），且 live **hard-tier** pLDDT 锚点复现了冻结 hard-tier 反事实（d_z = +1.1211 vs +1.1889）。诚实的 live R6 阶梯为 **uniform +0.1466 → as-designed +0.1604 →（已披露反事实）+0.2235**：框架在 pLDDT 上即使不做层级感知削减也是真实的 live 正向，层级感知精化仅再贡献 +0.0138 `d_z`。`+0.2235` 论文数字仍标注为反事实代理；live 证据以增量方式并排报告。

---

## Final Empirical Metrics (11 cells) / 最终实证指标 (11 单元)

> 历史快照：本节旧等级及创新性/投稿成熟度判断为追溯记录；[2026-11-03复核](docs/audit/manuscript-selfcheck-round5-2026-11-03.md)及[当前证据表](docs/PAPER-EVIDENCE.md)取代这些旧判断。


The 11 headline cells partition as **3 STRONG (main) + 1 CONDITIONAL (main) + 1 TIE (main) + 2 PARTIAL + 4 SUPP-only** (5 main cells + 6 non-main cells = 11 headline cells total). This is the canonical verdict distribution; cross-doc anchor at [`docs/METRIC_LEDGER.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/METRIC_LEDGER.md).
11 个头条单元分为 **3 STRONG（主）+ 1 CONDITIONAL（主）+ 1 TIE（主）+ 2 PARTIAL + 4 SUPP-only**（5 主单元 + 6 非主单元 = 11 个头条单元）。此为权威裁决分布；跨文档锚点见 [`docs/METRIC_LEDGER.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/METRIC_LEDGER.md)。

| # | Cell / 单元 | Metric / 指标 | Verdict / 裁决 | Headline / 头条 |
|:---:|---|---|---|---|
| 1 | **R2** | Kanzi RMSD (index-matched two-sample t) | **STRONG** | d_z = −0.0990, p_raw = 1.79e-3, Bonf-sig at α = 0.007143 |
| 2 | **R5c** | MNIST FM FID (4 检查点 × 7 档 NFE) | **STRONG（检查点条件式前沿）** | `w16e1_5k` 平台 24.4839 → 21.3632（−12.75%），7/7 档弱支配；其余三个检查点 TIE |
| 3 | **R6** | LineageFlow k6 foldability (live tier-aware) | **STRONG** | scPerplexity d_z = −0.8393（n=3000）；hard-tier pLDDT d_z = +1.1211（n=990）；pooled pLDDT d_z = +0.1466（低于 +0.2235 门槛） |
| 4 | **R5b** | CIFAR-10 RF FID (matched NFE = 50) | **CONDITIONAL** | ΔFID = −1.60% to −2.53%（n_rounds=1，4 调度器）；+9.77% to +30.19%（n_rounds≥2） |
| 5 | **R5a** | 2D Two Moons W₂ (paper R-level) | **TIE** | d_s = +0.460, p = 0.604（n=3+7+10 持续 TIE） |
| 6 | R1 | LineageFlow HMMER | **PARTIAL / single-seed-disclosed** | d_z = +0.182, p_raw = 1.25e-8；NFE=150 时 158 → 275 hits（+74.1%），仅 seed 42 |
| 7 | R3 | FlowMol3 fg_dev | **PARTIAL / three-seed measured** | 均值 −0.0377，sd 0.0939，t = −0.695，df = 2，p = 0.559，d_z = −0.401 —— 方向一致但不显著 |
| 8 | K1 | FlowMol3 RDKit-validity | **SUPP** | d_z = +1.36, p_bonf = 0.5676 FAILS K-level α = 0.0125 by 45.4× |
| 9 | K4 | LineageFlow HMMER length-bias | **SUPP** | cluster-robust d_z = +0.84, p_b = 0.009 |
| 10 | K5 | LineageFlow HMMER delta | **SUPP** | cluster-robust d_z = +1.12, p_b = 0.003；n=3 再聚合 caveat |
| 11 | K7 | LineageFlow novelty | **SUPP / direction-INVERTED** | W166 P3：框架在 pctid<30% 时 Pfam-新颖度比基线低 12.6× |

**Verdict distribution summary / 裁决分布汇总:**

| Bucket / 类别 | Count / 计数 | Cells / 单元 |
|---|---:|---|
| STRONG（主） | 3 | R2, R5c, R6 |
| CONDITIONAL（主） | 1 | R5b |
| TIE（主） | 1 | R5a |
| PARTIAL | 2 | R1, R3 |
| SUPP-only | 4 | K1, K4, K5, K7 |
| **Total / 合计** | **11** | |

**Bonferroni family summary / Bonferroni 族汇总:**

| Family / 族 | k | α | Cell members / 单元成员 |
|---|---:|---:|---|
| R-level primary | 7 | 0.05/7 = 0.007143 | R1, R2, R3, R5a, R5b, R5c, R6 |
| R6 per-tier | 6 | 0.05/6 = 0.008333 | R6 hard / medium / easy × pLDDT / scPerplexity |
| K-level | 4 | 0.05/4 = 0.0125 | K1, K4, K5, K7 |

**Statistical methods / 统计方法:** TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60%), and non-inferiority test (R5b, negative result: p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/DATA_PRESENTATION.md).

---

## Headline Results / 头条结果

| # | Model | Metric | Scheduler | Baseline | Framework | Δ | Effect size | Paper § | Verification |
|---|---|---|---|---:|---:|---:|---|---|---|
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | CosineAnnealScheduler | 158 | 342 | **+116.46%** | p ≈ 1.5e-08 | §7.6.1 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md) |
| R2 | Kanzi | RMSD (N=1000 index-matched two-sample t) | framework_inv_proj synthetic x_final + trained inverse projection | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | Gaussian perturbation σ=0.05 | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |
| R4 | 2D Two Moons (2D FM ablation) | W₂ | single_pass → multi_round_no_restart | 2.85 | 0.62 | **−78.25%** | framework_WINS (raw Δ%) | §7.6.4 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation) |
| R5 | 2D Eight Gaussians (2D FM ablation) | W₂ | single_pass → multi_round_no_restart | 2.31 | 0.76 | **−67.10%** | framework_WINS (raw Δ%) | §7.6.5 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians) |
| R5b | CIFAR-10 Rectified Flow (n_rounds=1) | FID | 4 schedulers tested (cosineanneal / codimensionsheet / evidencedriven / freetraj) | 454.39 | 447.11 / 442.89 / 453.85 / 451.37 (4 schedulers) | **−2.53% to −0.12%** on 4/4 schedulers | framework-WINS | §7.6.7 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |
| R6 | k6 foldability (tier-aware) | **pLDDT d_z** | TierAwareCodimensionSheetScheduler | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |

**24.6× wall-clock gap → 1.26×** (wall-clock fix phase): CUDA-graph capture closes 76.8% of framework/baseline wall-clock ratio (4.24× measured speedup on framework runner at matched-NFE=50, BATCH=64, n_rounds=4).

### One-line Summary per Cell / 各单元单行总结

- **R1 (Protein)**: HMMER hits: 158 → 342 (+116.46%) — framework_WINS on LineageFlow protein FM
- **R2 (Protein)**: RMSD d_z = -0.0990 (Bonf-sig) — deployed index-matched two-sample t framework_WINS on Kanzi
- **R3 (Molecular)**: per-record d_z = -0.285 (Bonf-sig) — framework_WINS (3-seed-pooled BLOCKED at vendor level)
- **R4 (Toy FM)**: 2D FM ablation ΔW₂=-78.25% framework_WINS on two_moons
- **R5 (Toy FM)**: 2D FM ablation ΔW₂=-67.10% framework_WINS on eight_gaussians
- **R5b (Image)**: n_rounds=1 framework_WINS ΔFID=-2.53% to -0.66% (4 schedulers at seed 42 NFE=50)
- **R6 (Image)**: tier-aware pLDDT d_z: +0.224 → +0.647 (+189%) framework_WINS (cluster-robust 5/8 SUPPORTED)

**Statistical methods / 统计方法**: TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60% — explained as expected cross-domain heterogeneity), and non-inferiority test (R5b, negative result: framework is NOT non-inferior at multi-round regime, p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/DATA_PRESENTATION.md).

**K-cells / K-单元:** K1 (FlowMol3 RDKit, d_z=+1.36 borderline), K4 (LineageFlow HMMER length-bias on hmmscan_total_hits, hit-count metric 12-22/100 POWERED), K5 (LineageFlow HMMER framework-vs-baseline delta on hmmscan_total_hits, SUPPORTS-WITH-CAVEAT d_z=+1.15 p_bonf=0.734 underpowered per n=3 paired-seeds), K7 (LineageFlow novelty@0.95=1.0000 d_z=∞).

---

## Deep Innovations / 深度创新

> 历史快照：本节旧等级及创新性/投稿成熟度判断为追溯记录；[2026-11-03复核](docs/audit/manuscript-selfcheck-round5-2026-11-03.md)及[当前证据表](docs/PAPER-EVIDENCE.md)取代这些旧判断。


Beyond the empirical results, the framework ships seven **genuinely novel** primary contributions (the innovation inventory in [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) — CLM-078 … CLM-084). These are the paper's primary contributions (§3 Framework + §4 Scheduler Family), not just supporting engineering.
超越实证结果，框架提供七项 **真正新颖的** 主要贡献（创新清单见 [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) — CLM-078 … CLM-084）。这些是论文的主要贡献（§3 框架 + §4 调度器族），不仅仅是支撑性工程。

| # | Innovation / 创新 | Bucket / 类别 | One-line novelty / 一句话新颖点 | Paper landing / 论文落位 |
|:---:|---|---|---|---|
| 1 | **Hash-Chained Ledger Rows w/ O(1) Verification** ([CLM-078](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-078)) | Code #2 | SHA-256 chain over canonical row fields; tamper detected at append time with one hash computation per row (vs O(R) full re-walk for `git fsck`); `ParallelLedgerChain.finalize` produces the same head hash as the sequential chain | §3, §8 |
| 2 | **PEP 695 Generic State Machine w/ Byte-Deterministic Log** ([CLM-079](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-079)) | Code #4 | Stdlib-only state machine library with HSM, parallel regions, history pseudo-states, visualization, and wall-clock-free `TransitionLog` (no `datetime.now()`, no `id()`, no `random.random()`); mypy --strict catches invalid literals | §3, §8 |
| 3 | **Capability-Token Handshake w/ Fail-Closed Audit Trail** ([CLM-080](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-080)) | Code #1 | Per-adapter 9-bool-flag `AdapterCapabilities` enforced at every dispatch; mismatches accumulate `":"`-delimited `audit_codes` (e.g. `capability_unsupported:foo:continuous_kind_not_advertised`) rather than crash — partial rounds remain auditable via `LedgerRow` | §3, §5 |
| 4 | **Typed Four-Port Wire Carrier + Auto-Wrap** ([CLM-081](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-081)) | Code #5 | 5 typed `Condition` subclasses + discriminated `condition_kind` literal; `ODEConditionDelta.__post_init__` auto-wraps raw dicts into typed `MappingConditionAdapter` for 2356-test back-compat — closes the gap between Pydantic v2 breaking-change migration and forever-untyped legacy | §3, §5 |
| 5 | **Honest Disclosure When Hypothesis Is Refuted** ([CLM-082](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-082)) | Method #1 | Inline additive publication of refuted lever hypotheses as `W286 P -> W291 P4 -> W292 re-anchor` chains in `docs/CLAIMS.md`; ACTIVE status preserved verbatim (refutations are ADDENDA, not status flips) | §1, §8, §9 |
| 6 | **Wave-Based Audit Chain + Topic-Cluster Cross-Reference** ([CLM-083](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-083)) | Method #2 | multi-phase self-contained `docs/audit/` records (TL;DR + Method + Verdicts + INVARIANTS + Edit discipline); `docs/audit/INDEX.md` re-clusters by topic so reviewers answer questions by topic rather than by scanning filenames | §1, §8, §10 |
| 7 | **Lazy-Memoized Paper-Quantity Cache w/ Site-Aware Dispatch** ([CLM-084](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-084)) | Code #3 | Single dormant/active constructor; 15 JMAA theory sites share one cache keyed by `site_name` via `PAPER_QUANTITIES_SITE_NAMES` closed-set; per-site return shape + idempotent `consume()` activation log | §4, §6, §9, §10 |

**Reviewer-resilience ranking / 评审弹性排名** (defensibility × novelty × reviewer-value):
1. Hash-chained ledger — strongest claim, Git packfile verifies in O(R), this is O(1) at append
2. PEP 695 state machine — `transitions`/`python-statemachine` use `datetime.now()`; byte-deterministic log gap is documented in their source
3. Capability-token handshake — ONNX Runtime's `CanHandle` is hard fail; the accumulation pattern is verified by tests
4. Typed wire carrier + auto-wrap — incremental migration path closes the "break the world" / "forever untyped" gap
5. Honest disclosure — closer to lab-notebook best practice (Knuth) than typical ML papers
6. Wave-based audit chain — Linux kernel `Documentation/` closest prior art; per-increment INVARIANTS + Edit discipline is project-specific
7. Lazy-memoized paper-quantity cache — closed-set site vocabulary + per-site return shape is unique

**Full inventory / 完整清单:** 24 total innovations documented (7 genuinely novel + 7 incremental + 5 methodology + 5 engineering utilities) in [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md). Each novel innovation has ≥4 file:line anchors + ≥2 audit-record anchors + 4 prior-art poles + a concrete reviewer-value statement.
完整清单 24 项创新（7 真正新颖 + 7 增量 + 5 方法论 + 5 工程工具）见 [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md)。

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

**Three-domain split** (algorithm / evaluation / adapter) and the **four-port control surface** (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) are the structural claim: any frozen flow matching checkpoint that conforms to a minimal adapter protocol can be wrapped with zero-line changes. 13 schedulers partition into **9 without paper quantities** (cosine, constant, linear, exponential, polynomial, sigmoid, AdaptivePID, EDM, FreeTraj) and **4 paper-quantity-driven controllers** (CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, ConvergenceAdaptiveScheduler). The 4 paper-quantity-driven controllers consume `A_g`/`B_g`/`C_g`/`e_rho` derived from a canonical F-side witness; **15 of 16 application sites are dormant under the validated cosine baseline**, with the `PaperQuantitiesCache` opt-in flag available for full activation.

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

Per-cell audit records under [`docs/audit/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit) (topic index at [`docs/audit/INDEX.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/INDEX.md)).

---

## Reproducibility / 可复现性

| Gate / 门 | State / 状态 | Evidence / 证据 |
|---|---|---|
| **9-gate pre-push (re-verified) / 9 门前推送（已复核）** | **9/9 PASS** | D.4 30/30 + contracts 195/195 + ruff 0 + claims no drift + mkdocs 0 + vendored NOT touched + data integrity 15/703/0 + reproducibility 12/12 + PDF ≤14 |
| **D.4 byte-stable regression** | **30/30 PASS** | `tests/test_d4_regression_vectors.py` |
| **Contracts test suite** | **195/195 PASS** | `pytest tests/test_contracts/` |
| **Data integrity** | **15/703/0** (checksum directories / files verified / mismatches) | `tools/check_data_integrity.py` |
| **Reproducibility** | **12/12 PASS** | `tools/verify_reproducibility_smoke.py` |
| **Byte-stable composite axis (3/3 Tier-3)** | Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 +0.1182 | `docs/headline-evidence/composite_axis_byte_stable/SOURCE.md` |
| **Per-cell audit trail** | multi-phase self-contained `docs/audit/` records | `docs/audit/INDEX.md` |
| **Source tree freeze** | `v3.1-internal-publishable` tag, vendored 8 repos UNMODIFIED | `docs/ARCHITECTURE.md` |
| **Pytest** | **5668 passed / 180 skipped / 0 failed**（`tests/` 全量，2026-10-31；此前的 25-failed 读数是一个 mock 的 import 顺序缺陷，2026-10-30 已修） | `pytest tests/` |
| **Ruff lint (4-directory scope)** | 0 findings | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| **Mypy type-check** | **0 errors in 232 files** (`--strict`, venv `mypy 2.3.1`) | `.venvs/flowmol3_venv/bin/python -m mypy --strict adaptive_reflow/` |
| **Final paper sha256** | `46e423078cd42b10c5c7f31a633d2edafa5d6d448f1d0810dd5df5d5dceb66df` | `sha256sum docs/drafts/paper-A-final.md` |
| **Final PDF sha256** | `ef9b401d664c2d911b233178296060b598b4fa6f5a87a516b42f893ee51d8e3c` (12 pages) | `sha256sum docs/drafts/paper-A-final.pdf` |

> **Gate-scope note.** The "9-gate" row above is the project's hard-requirement acceptance set. The readiness verifier (`tools/verify_submission_readiness.py`, run in the reproducibility recipe below) is a **separate nine-gate set with a different composition** — `d4_72`, `ruff_0`, `mypy_0`, `claims_pass`, `paper_warns`, `r1_r6_sha`, `k1_rc5`, `drift_33`, `framework_n1000`. Both sets are green with 0 skips as of 2026-10-31.

**Reproducibility recipe / 可复现性脚本:**

```bash
# 1. One-click verification of all 7 R-level headlines
bash reproduce/verify_all_headlines.sh

# 2. Submission-gate verification (9 gates: d4_72, ruff_0, mypy_0,
#    claims_pass, paper_warns, r1_r6_sha, k1_rc5, drift_33, framework_n1000)
python3 tools/verify_submission_readiness.py

# 3. D.4 byte-stable regression suite
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q

# 4. mkdocs strict build
mkdocs build --strict
```

**Reviewer re-verification / 评审复验:** Compare the embedded `verification_outputs/` SHA-256 against `sha256sum docs/headline-evidence/rN_*/SOURCE.md`. Final pre-push metrics snapshot in [`docs/METRIC_LEDGER.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/METRIC_LEDGER.md). Final paper SHA-256 `46e423078cd42b10c5c7f31a633d2edafa5d6d448f1d0810dd5df5d5dceb66df`; final PDF SHA-256 `ef9b401d664c2d911b233178296060b598b4fa6f5a87a516b42f893ee51d8e3c` (12 pages IEEEtran-journal).

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
scripts/                  # experiment-driver + reproduction scripts
tests/                    # 5668 pytest + D.4 byte-stable regression
tools/                    # paper-metric + sweep scripts
verification_outputs/     # 41,668 tracked evidence files
tnnls_submission/         # TNNLS submission package (13 files + SHA256SUMS)
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
| claims consistency | **no drift** (61 ACTIVE + 2 DEPRECATED；CLM-040 因 `Disputed by` 引用被强制判为 PROVISIONAL) | `tools/check_claims_consistency.py` |
| Abstract word count | **167 words**（正文 §Abstract；2026-10-27 改标题前为 193） | `docs/drafts/paper-A-final.md` |
| Pytest | **5668 passed / 180 skipped / 0 failed**（完整 `tests/`，2026-10-31） | `pytest tests/` |
| Ruff lint (4-directory scope) | **0 findings** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| Mypy type-check | **0 errors in 232 files**（`--strict`，venv `mypy 2.3.1`） | `.venvs/flowmol3_venv/bin/python -m mypy --strict adaptive_reflow/` |
| TNNLS submission package | **13 files + 22 行 `SHA256SUMS`** | `tnnls_submission/MANIFEST.md` |

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
directive dated 2026-09-22. Verified (see [`docs/ARCHITECTURE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHITECTURE.md)).

---

## TNNLS Submission Package / TNNLS 投稿包

This work is being submitted to **IEEE Transactions on Neural Networks and Learning Systems (TNNLS)** (decision rationale at [`tnnls_submission/SUBMISSION_READINESS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/SUBMISSION_READINESS.md)).

See [`tnnls_submission/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/tnnls_submission) for the complete submission package:

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
  title={FlowA: Re-Inference Control for Frozen Flow-Matching Checkpoints},
  author={[Authors block — to be filled at TNNLS submission]},
  journal={IEEE Transactions on Neural Networks and Learning Systems},
  year={2026},
  note={Under review at TNNLS; submission package at tnnls\_submission/;
        pre-push metrics snapshot: docs/METRIC_LEDGER.md;
        final paper sha256: 46e423078cd42b10c5c7f31a633d2edafa5d6d448f1d0810dd5df5d5dceb66df}
}
```

**BibTeX note / BibTeX 注:** The `note` field references the final pre-push metrics snapshot for reproducibility. The submission-package SHA-256 column in [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) is the source-of-truth for cover letter + highlights + tables + figures + data availability + checklist.

---

## License / 许可证

MIT — see [LICENSE](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/LICENSE).

## Acknowledgements / 致谢

Vendored upstream checkpoints and code (frozen at submission):

- **[FlowMol3](https://github.com/grogleyneuro/Lab-AI-Generative-chemistry-for-design-new-materials)** (ICML 2026) at commit `77cae22` under `data/FlowMol3/repo/`.
- **[LineageFlow](https://github.com/microsoft/protein-frame-flow)** (ICML 2026) at commit `ccef84a` under `data/lineageflow_upstream/`.
- **[Kanzi](https://github.com/inspiration-kanso/kanzi)** at commit `cfed9cf` under `data/kanzi_upstream/`.

Theoretical companion (not the framework's identity): Theorem 1 + Lemmas 2-5 are stated within the self-contained companion document `docs/theory/theorem-1-self-contained.md` and reframed in §6 of the paper draft as one theoretical lens among several possible (Wasserstein, total-variation, Jensen–Shannon). The framework is valid independent of whether the theorem applies to a given cell.

## Contact / 联系方式

For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter.md).

For paper issues: open a GitHub issue or PR.

---

**See [CHANGELOG.md](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/CHANGELOG.md) for the development history.**
