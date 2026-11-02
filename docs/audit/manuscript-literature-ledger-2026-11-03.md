# 中文稿主要文献与指标来源核对（2026-11-03）

对象：中文v4；基准提交b6bb14518dbf2eb8085ecf7c26fc85bee0d2e982。仅用原始论文、出版方或作者官方资源核对书目信息与相关定义；没有把当前官网版本等同于历史运行版本。新增编号9–19；原编号1–8保留。机器记录在`verification_outputs/manuscript-selfcheck-round3-2026-11-03/literature_sources.json`。

## 1. 直接相关工作

- Restart：[原文Appendix B.2与C.1–C.2](https://arxiv.org/html/2306.14878v2)区分前向噪声核、重启区间与反向ODE；不限定为只能用Heun。本项目主实例的端点混合/部分时间/RK4/质心是另一具体配置。当前源码搜索未找到原始Restart匹配比较，不把“有差异”写成“已超过”。
- LineageFlow：[原文](https://arxiv.org/html/2605.22252v2)4.2已有中间时刻rerouting。它是必须讨论的相近干预；本项目随机序列baseline不能取代原文base-flow/no-rerouting对照。
- Kanzi：[原文作者与题名](https://arxiv.org/abs/2510.00351)为Rohit Dilip、Evan Zhang、Ayush Varshney、David Van Valen，2025预印本。旧JSON中的“Shah/ICLR2026”不作为书目来源，也不据当前README确认未核实的会议归属。
- FlowMol3：[原文](https://arxiv.org/abs/2508.12629)作者Ian Dunn、David R. Koes，2025预印本。旧工具注释“NeurIPS2024 + 2508.12629”年代不一致，不进入新稿。代码pin仍按项目原记录，不用当前发布的新版本替换旧结果。

## 2. 指标—源码—原始来源

| 对象 | 源码与检查位置 | 原始来源 | 新稿处理 |
|---|---|---|---|
| scPerplexity | `data/lineageflow_upstream/evaluation/self_consistency_esmif.py`190–217行 | [Hsu等ICML2022](https://proceedings.mlr.press/v162/hsu22a.html) | 非padding token平均交叉熵的指数；含ll截断；不是实验功能测量 |
| pLDDT | `data/lineageflow_upstream/evaluation/foldability_omegafold.py`365–402行 | [OmegaFold作者官方代码与citation](https://github.com/HeliXonProtein/OmegaFold) | PDB的Cα置信度字段、去重残基、序列均值；不写天然误差。bioRxiv正文访问403，书目与输出约定用作者README核对 |
| HMMER | `data/lineageflow_upstream/evaluation/family_validity_hmmer.py`150–169、246–251行 | [Eddy2011](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1002195) | 目标家族与任意命中分开；默认阈值不自动归给历史运行 |
| MMseqs2 | `data/lineageflow_upstream/evaluation/novelty_mmseqs2.py` | [Steinegger与Söding2017](https://www.nature.com/articles/nbt.3988) | 库版本、覆盖和一致性阈值影响含义；不能只写“新颖” |
| Pfam | 上述家族/新颖性驱动及运行数据库路径 | [Mistry等2021](https://academic.oup.com/nar/article/49/D1/D412/5943818) | 2021是引用文献年份，不代表本项目数据库release |
| 分子有效性 | `scripts/wave338_p5_r3_n1000_paired.py`324行→`tools/paper_metrics.py`942–1046行 | [PoseBusters原文](https://pubs.rsc.org/en/content/articlelanding/2024/sc/d3sc04185a) | RDKit sanitization与几何/能量检查分开；actual all-metrics函数不调用另一个xtb helper |
| MNIST | 现有训练配置与`adaptive_reflow/eval/mnist_fid.py` | [作者原始文献页面](https://bottou.org/papers/lecun-98h) | 自训练检查点与自定义projection特征分别披露；IEEE正文受JS检查限制 |
| CIFAR-10 | 各历史评估配置及特征缓存 | [作者原始技术报告](https://www.cs.toronto.edu/~kriz/learning-features-2009-TR.pdf) | 数据引用不是FID配置等同证明；缓存/权重仍需逐运行来源 |

## 3. 不能从引用补足的层次

- 上游pin：LineageFlow ccef84a、Kanzi cfed9cf、FlowMol3 77cae22，来自`tools/check_vendored_pristine.py`。这只是项目版本pin与完整性检查，不自动证明某次历史运行实际加载了哪些权重。
- R6真实评价不等于匹配生成模型对照；原稿已限缩，新增文献不能替其补上对照。
- FlowMol3实际driver调用`compute_all_paper_metrics`。其`full_pb=True`尝试项目YAML注入，失败会降到subset；该函数不会调用另一个`compute_pb_validity_pct`中的xtb重评。只保留一个总率的历史JSON不能证明当时成功启用的精确检查集合，逐分子verdict缺口保留。
- 历史运行的全部依赖版本、数据库release、PoseBusters配置与成功注入记录仍不完整。主要书目补齐不等于SC39全部通过，也不等于匿名材料就绪。
