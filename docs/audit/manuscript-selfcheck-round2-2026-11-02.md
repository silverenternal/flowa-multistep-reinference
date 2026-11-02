# 投稿自查第二轮：恢复底层、组件消融与跨任务比较对象

日期：2026-11-02。基准：11e231555019f30411af93fc02b18088c8379538。

本轮延续用户“顺着自查表继续优化”，处理既有证据恢复、统计复算与中文稿 v3。不新训练、不新采样，不改冻结投稿包或上游数据。45项全部保留，历史状态在JSON中；VERIFIED表示逐项注明的范围，不代表论文全部验收。

## 1. Kanzi原始基线恢复与统计

首轮在当前目录未找到baseline，本轮进一步检索完整Git历史：提交0d070700f441c81f1292bb8f58a952b6c116400d引入，9c28d52f清理删除。

恢复路径：`verification_outputs/wave218-p3-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json`。SHA-256：`be03a0a9628e8ed6aa765d1a9a0398822e4b6ca74f89aa1b095fcc2f1314148b`。恢复字节来自Git blob，不重建或替换其他运行。

与`verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json`的1000个键严格一致；源码统计工具拒绝静默取交集、非有限数和退化方差。

- 基线均值0.9027630950 Å，框架均值0.8837987798 Å，差−0.0189643152 Å；索引相关0.0456279。
- 旧索引差值重算：SE0.006057459、df999、p0.001794328、dz−0.09900262；与历史汇总一致。
- Welch独立记录假设敏感性：SE0.006200528、df1996.8697、p0.002254022、95%区间[−0.031124497,−0.006804133] Å。沿历史7个R级检验的Bonferroni校正p0.015778156。不是对整个后续搜索的校正。
- `docs/audit/gap23-r2-paired-comparison-invalid.md`含历史撤回；其撤回说明的Welch近似使用别次运行SD，不能替代本轮对原始Wave218+214记录的精确复算。低索引相关本身不使旧差值显著性“凭空产生”；也不证明同输入配对或可归因的优化。

源码：`tools/_kanzi_sweep_runner.py` 439–465行构造新latent并桥接，777–830行分支选择两种坐标，928–952行各自encode/decode往返。baseline是原输入的重建；framework是生成结构自身的重建。基线输入由`verification_outputs/kanzi_n1000_manifest.json`记录的4个PDB各250个扰动变体构成，不能视作1000个独立天然模板。重建误差差异保留为描述性结果；不作为同结构细化、多轮贡献或生物学质量保证。

复算：使用`.venvs/flowmol3_venv/bin/python tools/review_kanzi_statistics_20261102.py`，传入上述baseline/framework路径及`--output verification_outputs/manuscript-selfcheck-round2-2026-11-02/kanzi_statistics.json`。新输出不覆盖旧汇总。

## 2. 已有质心消融确实存在，且有未满足的预测

本轮用现有`tools/gap76_report.py`直接读取GAP57与GAP76的96个既有NPZ，复算36个比较。命令为`PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venvs/flowmol3_venv/bin/python tools/gap76_report.py --out verification_outputs/manuscript-selfcheck-round2-2026-11-02/mean_preserve_recomputed.json`。无新样本生成。

- 4检查点×3调度臂×3生成种子；每臂1000样本；历史S50、R4、βtot=.5、equal_budget、memory。两臂均为MNIST RK4，C200。
- 与主前沿βtot=.3不同；旧消融有每轮1步配置，不能拼成当前每轮至少2步的前沿。
- 协方差迹/交叉项36/36通过平移不变量控制。三种子聚合重新从cells计算，未沿用旧chunk显著性。本轮不变量最大误差为trace 7.1e−15、cross 7.8e−14；与历史report的ΔFID最大差约9.54e−8，属数值环境容差，正文三位小数不变，不声称派生浮点结果逐字节相同。
- 预先预测seed42至少8/12单元Δ≤0，实际6/12；三种子合计18/36。未满足条件进入正文，不能只展示有利单元。
- 开启后的12个检查点—调度单元，三种子t区间按是否排除零为6有利/6不利；只按均值1单位阈值为3有利/9阈值内。这个均值阈值不是主前沿多预算优势规则。
- 正文展示evidence_driven四检查点完整表，其他两臂见派生JSON。各区间未作同时覆盖校正，定位探索性。

来源、96个NPZ的hash和24个运行汇总在`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`。本轮将派生结果与小体积运行汇总纳入Git；96个NPZ未新发布，完整样本级重算仍依赖服务器原数据。

## 3. 跨任务不是同一机制的自动重复

| 单元 | 核对来源 | 发现与正文处理 |
|---|---|---|
| MNIST | `scripts/wave191_p3_mnist_sweep.py` | 明确端点多轮、部分区间、预定预算、质心；已有局部消融不等同于完整矩阵 |
| Kanzi R2 | `tools/_kanzi_sweep_runner.py` | 新latent桥接与一次rollout，评价其自编码往返；不称原输入优化 |
| LineageFlow R1/R6 | `tools/gen_lineageflow_n1000_fastas.py`、`tools/sweep_r6_tier_aware_live.py` | `_write_baseline_arm`971行开始为家族AA偏置RNG，不调用生成模型；live评价的对照不等于匹配生成器 |
| R6门控 | 上述生成器908–925行；GAP30 as-designed三份manifest | nfe10、请求3轮、门槛20；现存源码有效1轮，历史清单缺生成提交与加载模式，因此不据请求轮数认定真实多轮 |
| FlowMol3 R3 | `scripts/wave338_p5_r3_n1000_paired.py` 230–270行；GAP39 summary | 历史坐标prior扰动和另行全通道prior混合一次求解分别报告；选项存在不等于旧结果已启用 |

R6真实评价读数、三个种子和各层方向均保留；但不能把相同qid对应的不同生成序列称为同序列前后处理，或将pooled3000当作独立模型/家族重复。当前尚未闭合第二条同机制跨家族前沿，SC16更新为EVIDENCE_GAP。该更新反映验收条件更明确，不是删除不利结果。

## 4. 自查表与后续顺序

状态：24 VERIFIED、9 EVIDENCE_LOCATED、7 REVISION_NEEDED、5 EVIDENCE_GAP。SC27关闭的是原始来源/检验重算/解释范围；不包含匹配结构因果结论。SC12关闭的是组件—证据映射。SC05仍缺主前沿参数下的同协议固定混合与组件矩阵。

后续优先：主前沿参数下的已有对照盘点；最接近Restart方法的匹配比较；上游模型/数据/指标引文；缺失PoseBusters逐分子材料；英文官方模板与匿名材料。没有的证据保留缺口，不把增加文字当作完成实验。

## 5. 验证

40项定向测试通过（含5项新增解析/异常输入测试）；todo.json全部24项门禁通过，覆盖72个D4回归向量、严格文档构建、类型与格式检查、全测试收集及原投稿材料一致性。不是完整pytest执行。系统Python下anchor工具依旧跳过，指定文档环境重跑通过。旧ledger的6条非致命状态解析消息、旧链接检查的2条broken/1条ambiguous/1条archived保留披露；原投稿包未改动。详细输出尾部见verification_outputs/manuscript-selfcheck-round2-2026-11-02/checks.json。

新增Word由同步到Mac的相同版本导出，再做内容与原生Word视觉检查；结果记录在Mac输出收据。工程门禁通过不等于科学设计充分。
