# 投稿论文审稿自查表（2026-11-02）

**基准提交：** `30866780de462469035dc1ddad88dc1e215ee51a` ；本表共有 **45 项**。

完整记录2026-11-02聊天中的10类审稿问题、全部子项、篇幅/定位判断与三轮计划；先追踪源代码和已有记录，不默认重跑实验。

## 使用规则

- **RECORDED**：已登记，未完成核对；不表示证据缺失或结论成立。
- **EVIDENCE_LOCATED**：找到相关既有记录，尚未独立验证全部路径/统计及其是否进入中文稿。
- **VERIFIED**：逐项附源码符号/行号、artifact和适用范围后才允许使用。
- **REVISION_NEEDED**：已有充分证据，但稿件未正确呈现。
- **EVIDENCE_GAP**：核对已有代码/记录后确认仍缺证据。

VERIFIED 需要证据逐项核对，本轮建立记录不宣称所有问题已经解决。验收应补充：观察事实、解释、未解决项、文件/符号/行号、运行协议和最小下一步。

## 已发现的上轮评议遗漏

- 前两轮中文稿与评议遗漏GAP-90/91/92既有记录，不能继续声称项目只有未经受控解释的四检查点横截面。
- 既有GAP-90记录六检查点、受控数据/epoch剂量及宽度对照，但严格单调假设和跨家族预测要求仍须按预注册结果解释。
- 源码可确定实现、启用路径和指标定义；新颖性、因果效力、外部有效性与期刊接受度不能仅凭源码判定。

## 覆盖总表

| ID | 类别 | 优先级 | 自查问题 | 状态 |
|---|---|---|---|---|
| SC-01 | 篇幅与定位 | P0 | 当前中文稿是否具备完整投稿稿的论证密度？ | EVIDENCE_LOCATED |
| SC-02 | 篇幅与定位 | P0 | 中心主张是否可用一句话表述且被证据覆盖？ | RECORDED |
| SC-03 | 篇幅与定位 | P0 | 是方法论文还是软件框架论文？ | RECORDED |
| SC-04 | 创新性 | P0 | 是否仅为已有 restart sampling 加接口封装？ | RECORDED |
| SC-05 | 创新性 | P0 | 相比固定权重混合究竟新增什么？ | RECORDED |
| SC-06 | 创新性 | P0 | 首次性、普适性、全面占优是否有依据？ | RECORDED |
| SC-07 | 方法定义 | P0 | FlowA 主方法是否是确定且可复现的算法？ | EVIDENCE_LOCATED |
| SC-08 | 方法定义 | P0 | 反馈究竟读取什么信息？ | EVIDENCE_LOCATED |
| SC-09 | 方法定义 | P0 | 连续、离散、掩码和图通道的操作是否合法？ | RECORDED |
| SC-10 | 方法定义 | P0 | 实际调用次数是否等于宣称预算？ | EVIDENCE_LOCATED |
| SC-11 | 方法定义 | P1 | 四接口与算法步骤、伪代码是否一一对应？ | RECORDED |
| SC-12 | 贡献与证据 | P0 | 各任务是否验证同一个机制？ | RECORDED |
| SC-13 | 贡献与证据 | P0 | 各实验到底有没有真实多轮重启？ | EVIDENCE_LOCATED |
| SC-14 | 贡献与证据 | P0 | 已有但未写入中文稿的证据有哪些？ | EVIDENCE_LOCATED |
| SC-15 | 主结果 | P0 | 优势集中一个 MNIST 检查点意味着什么？ | EVIDENCE_LOCATED |
| SC-16 | 主结果 | P0 | 是否有第二条独立可信的实证主线？ | RECORDED |
| SC-17 | 主结果 | P0 | 训练充分性/检查点条件性是关联还是因果？ | EVIDENCE_LOCATED |
| SC-18 | 主结果 | P1 | WIN/TIE 与显著性、实用阈值、局部退化是否混淆？ | RECORDED |
| SC-19 | 理论 | P0 | 经典收缩与恒等式是否被包装成新理论？ | RECORDED |
| SC-20 | 理论 | P0 | 定理假设是否覆盖实际算法？ | RECORDED |
| SC-21 | 理论 | P0 | 是否越级推出目标分布或 FID 改善？ | RECORDED |
| SC-22 | 理论 | P1 | κ诊断与理论 Lipschitz 收缩因子是否混称？ | EVIDENCE_LOCATED |
| SC-23 | 比较公平性 | P0 | 收益来自重启还是求解器、初值、额外计算？ | RECORDED |
| SC-24 | 比较公平性 | P1 | 是否拼接不同N、seed、checkpoint和evaluator？ | RECORDED |
| SC-25 | 比较公平性 | P1 | 等 NFE 是否被写成等耗时或加速？ | RECORDED |
| SC-26 | 统计 | P0 | 独立运行次数、记录数和家族数是否混淆？ | RECORDED |
| SC-27 | 统计 | P0 | Kanzi 索引匹配是否错误当作天然配对？ | RECORDED |
| SC-28 | 统计 | P1 | 三种子自举与家族相关性是否充分披露？ | RECORDED |
| SC-29 | 统计 | P1 | 多重比较和效应阈值是否一致？ | RECORDED |
| SC-30 | 指标 | P1 | projection-FID 与标准 FID 是否混淆？ | EVIDENCE_LOCATED |
| SC-31 | 指标 | P1 | 蛋白代理指标能否代表结构/功能/家族覆盖？ | RECORDED |
| SC-32 | 指标 | P1 | 合成重建与分子有效性定义是否准确？ | RECORDED |
| SC-33 | 指标 | P1 | 质量提升是否伴随新颖性/多样性损失？ | RECORDED |
| SC-34 | 消融与机制 | P0 | 哪些组件真的必要？ | EVIDENCE_LOCATED |
| SC-35 | 消融与机制 | P1 | round数、beta、预算分配的解释是否被已有记录反驳？ | RECORDED |
| SC-36 | 消融与机制 | P1 | 残差修正解释是否被误当成机制证明？ | RECORDED |
| SC-37 | 呈现与复现 | P2 | 图表是否完整且可供判断？ | RECORDED |
| SC-38 | 呈现与复现 | P2 | 文字是否像审计报告、反复重复限制？ | RECORDED |
| SC-39 | 呈现与复现 | P2 | 参考文献和上游归属是否完整？ | RECORDED |
| SC-40 | 呈现与复现 | P2 | 审计可复现是否被当成科学正确性？ | RECORDED |
| SC-41 | 三轮执行计划 | P0 | 第一轮：主张与贡献是否锁定？ | RECORDED |
| SC-42 | 三轮执行计划 | P1 | 第二轮：方法、相关工作、主结果是否重写到位？ | RECORDED |
| SC-43 | 三轮执行计划 | P1 | 第三轮：是否按拒稿理由复查？ | RECORDED |
| SC-44 | 投稿决策 | P1 | TNNLS是否仍是合理首投？ | RECORDED |
| SC-45 | 记录与同步 | P0 | 是否完整记录全部上一轮审稿建议并同步源码？ | RECORDED |

## 逐项验收与证据入口

### SC-01 — 当前中文稿是否具备完整投稿稿的论证密度？

- 类别 / 优先级 / 状态：篇幅与定位 / P0 / EVIDENCE_LOCATED
- 验收：按正文、方法、协议、结果和文献逐节核算，区分中文页数与英文双栏；不以扩写背景凑页。
- 证据类型：MANUSCRIPT_AND_RECORDS
- 入口：`docs/audit/gap96-manuscript-compression.md`；`docs/drafts/paper-A-final.tex`
- 本轮发现：已定位相关记录；不等于独立验收通过。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-02 — 中心主张是否可用一句话表述且被证据覆盖？

- 类别 / 优先级 / 状态：篇幅与定位 / P0 / RECORDED
- 验收：记录一句中心主张、三项贡献及各自最强证据；所有超出证据范围的词单列。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/PAPER-EVIDENCE.md`；`todo.json`；`docs/drafts/paper-A-final.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-03 — 是方法论文还是软件框架论文？

- 类别 / 优先级 / 状态：篇幅与定位 / P0 / RECORDED
- 验收：明确主定位及次贡献；章节和实验围绕同一定位，不用工程接口代替方法新意。
- 证据类型：MANUSCRIPT_AND_LITERATURE
- 入口：`docs/drafts/paper-A-final.md`；`docs/STRATEGY_FRAMEWORK_SCOPE.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-04 — 是否仅为已有 restart sampling 加接口封装？

- 类别 / 优先级 / 状态：创新性 / P0 / RECORDED
- 验收：与最接近原始论文逐项比较状态、反馈、训练需求、预算、重启方式；不能凭源码存在判定新颖性。
- 证据类型：SOURCE_AND_PRIMARY_LITERATURE
- 入口：`docs/drafts/paper-A-final.md`；`docs/audit/gap94-standard-benchmark.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-05 — 相比固定权重混合究竟新增什么？

- 类别 / 优先级 / 状态：创新性 / P0 / RECORDED
- 验收：给出唯一可辨的算法差异、代码路径和对应对照；不用多个功能同时变化的比较归因。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/blender/blender.py`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-06 — 首次性、普适性、全面占优是否有依据？

- 类别 / 优先级 / 状态：创新性 / P0 / RECORDED
- 验收：逐词检查标题摘要贡献；不能证实的首次、普适、SOTA或全面优势删除或收窄。
- 证据类型：MANUSCRIPT_AND_PRIMARY_LITERATURE
- 入口：`docs/drafts/paper-A-final.md`；`docs/PAPER-EVIDENCE.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-07 — FlowA 主方法是否是确定且可复现的算法？

- 类别 / 优先级 / 状态：方法定义 / P0 / EVIDENCE_LOCATED
- 验收：锁定主方法实例，完整定义状态、反馈、调度、混合、停止和预算；可选框架配置另列。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/scheduler/evidence_driven.py`
- 本轮发现：scripts/wave191_p3_mnist_sweep.py:473-651 定义主实验 run_framework_arm；memory模式在后续轮次从 t_start=1-beta_r 积分至1；mean_preserve模式以首轮终点样本均值平移最终样本。中文稿的固定完整流映射是简化表达，需按该实例补齐时间区间和batch级操作。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-08 — 反馈究竟读取什么信息？

- 类别 / 优先级 / 状态：方法定义 / P0 / EVIDENCE_LOCATED
- 验收：列出评价/标签/参考数据是否参与控制、调用时机和成本，区分事后评价与在线控制。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/algorithm/evidence_driver.py`；`adaptive_reflow/algorithm/runner/runner.py`
- 本轮发现：scripts/wave191_p3_mnist_sweep.py:334-386 的调度预算在生成前通过 sched.sample 计算；该文件没有 record_round_feedback 调用。不能从 EvidenceDriven 名称推断此实验启用了在线PID反馈；仍需与通用 runner 的反馈路径和具体运行参数区分。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-09 — 连续、离散、掩码和图通道的操作是否合法？

- 类别 / 优先级 / 状态：方法定义 / P0 / RECORDED
- 验收：逐通道核对状态域、先验、尺度、混合和验证，明确线性理论仅适用的范围。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/algorithm/blender/per_channel_blender.py`；`adaptive_reflow/adapters`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-10 — 实际调用次数是否等于宣称预算？

- 类别 / 优先级 / 状态：方法定义 / P0 / EVIDENCE_LOCATED
- 验收：核对求解器每步调用、round floor、取整和不可执行设置；报告真实 NFE 而非仅配置步数。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/algorithm/nfe_allocation.py`；`adaptive_reflow/algorithm/solver.py`；`docs/audit/gap90-optsteps-dose.md`
- 本轮发现：scripts/wave191_p3_mnist_sweep.py:537 将 num_steps_per_round 求和记为 total_nfe；adaptive_reflow/adapters/mnist_fm.py:276-279 与309-312的RK4实现每步含四次速度场评价。已定位步数与函数评估数的口径风险，需继续核对实际backend与artifact，不预先判定整条比较不公平。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-11 — 四接口与算法步骤、伪代码是否一一对应？

- 类别 / 优先级 / 状态：方法定义 / P1 / RECORDED
- 验收：画方法图并给出可复现伪代码；接口只解释职责，指出真实调用实现和旁路。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/runner/sequential.py`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-12 — 各任务是否验证同一个机制？

- 类别 / 优先级 / 状态：贡献与证据 / P0 / RECORDED
- 验收：建立贡献→组件→实际比较臂→artifact 对应表；只验证集成的任务不得当作算法优势。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/PAPER-EVIDENCE.md`；`docs/paper-evidence.json`；`paper-data`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-13 — 各实验到底有没有真实多轮重启？

- 类别 / 优先级 / 状态：贡献与证据 / P0 / EVIDENCE_LOCATED
- 验收：逐格追踪实际启用的调度、restart、反馈与 no-op 路径；单轮不能证明多轮迭代价值。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap80-r5a-harness.md`；`docs/audit/gap95-frontier-grids.md`；`docs/PAPER-EVIDENCE.md`
- 本轮发现：MNIST驱动的run_framework_arm真实调用restart操作；同时调度步数提前生成、末端可有mean-preserve平移。需要分别标注重启、在线反馈、预算调度和batch平移是否启用，不能合称一个已验证组件。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-14 — 已有但未写入中文稿的证据有哪些？

- 类别 / 优先级 / 状态：贡献与证据 / P0 / EVIDENCE_LOCATED
- 验收：纳入 GAP-90 六检查点、GAP-91 描述性拟合、GAP-92 κ诊断及 GAP-93剂量记录；明确其有限结论，不重跑已有实验。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap90-optsteps-dose.md`；`docs/audit/gap92-kappa-bridge.md`；`todo.json`
- 本轮发现：已定位相关记录；不等于独立验收通过。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-15 — 优势集中一个 MNIST 检查点意味着什么？

- 类别 / 优先级 / 状态：主结果 / P0 / EVIDENCE_LOCATED
- 验收：完整报告六检查点/受控轴及历史四检查点关系、平台、局部损失、绝对效应；不得沿用仅四点且全部混杂的旧判断。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap90-optsteps-dose.md`；`docs/PAPER-EVIDENCE.md`
- 本轮发现：已定位相关记录；不等于独立验收通过。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-16 — 是否有第二条独立可信的实证主线？

- 类别 / 优先级 / 状态：主结果 / P0 / RECORDED
- 验收：核对 live 蛋白结果及比较臂、指标、种子/家族限制，判断能否支撑第二主结果，不凭 pooled n 决定。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap95-frontier-grids.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-17 — 训练充分性/检查点条件性是关联还是因果？

- 类别 / 优先级 / 状态：主结果 / P0 / EVIDENCE_LOCATED
- 验收：区分固定宽度的数据剂量、固定数据的 epoch 剂量、宽度对照及未满足的严格单调条件；按预注册逐条报告。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap90-optsteps-dose.md`
- 本轮发现：已定位相关记录；不等于独立验收通过。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-18 — WIN/TIE 与显著性、实用阈值、局部退化是否混淆？

- 类别 / 优先级 / 状态：主结果 / P1 / RECORDED
- 验收：明确绝对/相对阈值、区间、平台和逐档条件；TIE不写成严格等效，也不隐去低预算损失。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap84-inference-frontier.md`；`docs/paper-evidence.json`；`docs/audit/gap90-optsteps-dose.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-19 — 经典收缩与恒等式是否被包装成新理论？

- 类别 / 优先级 / 状态：理论 / P0 / RECORDED
- 验收：明确经典工具与新增推导的边界；基础性质不单独承担创新性。
- 证据类型：MATHEMATICS_AND_PRIMARY_LITERATURE
- 入口：`docs/drafts/paper-A-final.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-20 — 定理假设是否覆盖实际算法？

- 类别 / 优先级 / 状态：理论 / P0 / RECORDED
- 验收：逐项对应固定fresh input、m、状态域、Lipschitz、精确/数值映射；变化参数或随机输入不直接套固定点结论。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/drafts/paper-A-final.md`；`adaptive_reflow/algorithm/blender/blender.py`；`adaptive_reflow/algorithm/nfe_allocation.py`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-21 — 是否越级推出目标分布或 FID 改善？

- 类别 / 优先级 / 状态：理论 / P0 / RECORDED
- 验收：分开固定点收敛、状态误差、特征分布距离；未建立的桥梁不写成定理推论。
- 证据类型：MATHEMATICS_AND_RECORDS
- 入口：`docs/drafts/paper-A-final.md`；`docs/audit/gap92-kappa-bridge.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-22 — κ诊断与理论 Lipschitz 收缩因子是否混称？

- 类别 / 优先级 / 状态：理论 / P1 / EVIDENCE_LOCATED
- 验收：核对 κ 的计算定义、数据依赖、预算/调度臂和样本数；不得把经验协方差比等同于mK或因果规律。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`
- 本轮发现：tools/gap78_observable_screen.py:111-136 以投影特征协方差迹的比值计算contraction；实现为tr_fw/(tr_ref*rho)。这是经验分布离散度诊断，不是流映射Lipschitz常数mK的直接估计。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-23 — 收益来自重启还是求解器、初值、额外计算？

- 类别 / 优先级 / 状态：比较公平性 / P0 / RECORDED
- 验收：各臂列相同/变化因素；把solver、初始化、表示桥接、反馈、预算分离；不能归因的结果限缩解释。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/PAPER-EVIDENCE.md`；`paper-data`；`adaptive_reflow/adapters`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-24 — 是否拼接不同N、seed、checkpoint和evaluator？

- 类别 / 优先级 / 状态：比较公平性 / P1 / RECORDED
- 验收：建立逐单元协议表；异协议/历史端点分列；每个数值及其统计都来自兼容的artifact。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap90-optsteps-dose.md`；`paper-data`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-25 — 等 NFE 是否被写成等耗时或加速？

- 类别 / 优先级 / 状态：比较公平性 / P1 / RECORDED
- 验收：单独报告辅助评价和状态转换开销；实际时间只在同设备同实现下比较；外推加速不写成实测。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-26 — 独立运行次数、记录数和家族数是否混淆？

- 类别 / 优先级 / 状态：统计 / P0 / RECORDED
- 验收：每个CI/p/效应量写统计单位；pooled记录不替代种子重复，合成变体不替代独立结构。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-27 — Kanzi 索引匹配是否错误当作天然配对？

- 类别 / 优先级 / 状态：统计 / P0 / RECORDED
- 验收：追踪实际样本生成和相关性、检验实现及源均值；核对独立样本分析与dz命名，按正确单位重述；不预先认定旧检验正确。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-28 — 三种子自举与家族相关性是否充分披露？

- 类别 / 优先级 / 状态：统计 / P1 / RECORDED
- 验收：写明有限种子自举分辨率/区间局限、聚类单位与已有敏感性分析；不靠追加种子自动过关。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap84-inference-frontier.md`；`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-29 — 多重比较和效应阈值是否一致？

- 类别 / 优先级 / 状态：统计 / P1 / RECORDED
- 验收：定义检验家族、选择规则、校正次数、效应量和区间；区分探索与确认，缺失区间不补写。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap84-inference-frontier.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-30 — projection-FID 与标准 FID 是否混淆？

- 类别 / 优先级 / 状态：指标 / P1 / EVIDENCE_LOCATED
- 验收：追踪特征提取器、投影、参考集、样本量、随机种子与实现；不跨特征空间比较绝对值。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/adapters/mnist_fm.py`；`adaptive_reflow/eval`；`docs/audit/gap84-inference-frontier.md`
- 本轮发现：adaptive_reflow/eval/mnist_fid.py:90-109与203-214 定义像素空间的确定性高斯随机投影及参考样本特征；默认784→128，参考为MNIST测试集。它不是Inception特征FID；具体实验是否覆盖默认维度/种子仍需核对命令和artifact。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-31 — 蛋白代理指标能否代表结构/功能/家族覆盖？

- 类别 / 优先级 / 状态：指标 / P1 / RECORDED
- 验收：逐项解释pLDDT、scPerplexity、HMMER与家族身份，明确其能与不能支持的结论。
- 证据类型：SOURCE_METRICS_AND_PRIMARY_LITERATURE
- 入口：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap79-r1-family-lever.md`；`docs/PAPER-EVIDENCE.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-32 — 合成重建与分子有效性定义是否准确？

- 类别 / 优先级 / 状态：指标 / P1 / RECORDED
- 验收：核对坐标来源、单位、对齐、几何桥接、PoseBusters与RDKit的区别及逐记录存储完整性。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/audit/gap39-flowmol3-real-restart-blend.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-33 — 质量提升是否伴随新颖性/多样性损失？

- 类别 / 优先级 / 状态：指标 / P1 / RECORDED
- 验收：公开K7负结果及参考数据库/阈值；将质量、自一致性、覆盖和新颖性分开，不主张同步改善。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/audit/gap70-lineageflow-position-blend.md`；`docs/PAPER-EVIDENCE.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-34 — 哪些组件真的必要？

- 类别 / 优先级 / 状态：消融与机制 / P0 / EVIDENCE_LOCATED
- 验收：盘点已有无反馈、固定混合、自适应控制、完整方法对照；相同协议才可拼成因果消融，不存在的格子标缺失。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`adaptive_reflow/algorithm/policy_driver.py`；`docs/ABLATION.md`；`docs/audit/gap90-optsteps-dose.md`
- 本轮发现：scripts/wave191_p3_mnist_sweep.py:637-641 在mean_preserve启用时平移最终cloud，使均值等于首轮endpoint均值。消融应单独识别该batch级处理与重启/调度，不能把完整臂的收益直接归因于自适应反馈。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-35 — round数、beta、预算分配的解释是否被已有记录反驳？

- 类别 / 优先级 / 状态：消融与机制 / P1 / RECORDED
- 验收：检查GAP-84/90/93和各适配器真实路径；保留已证伪杠杆和不显著结果，不重复提出已做实验。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`todo.json`；`docs/audit/gap90-optsteps-dose.md`；`docs/ABLATION.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-36 — 残差修正解释是否被误当成机制证明？

- 类别 / 优先级 / 状态：消融与机制 / P1 / RECORDED
- 验收：把直接观测、解释与未知分开；源码只证明执行机制，不能单独证明质量变化的因果机制。
- 证据类型：SOURCE_RECORDS_AND_CAUSAL_DESIGN
- 入口：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-37 — 图表是否完整且可供判断？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / RECORDED
- 验收：方法图、可执行算法、逐任务协议表、主曲线不确定性、案例和完整状态表；图注自解释且可回溯源数据。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`docs/drafts/paper-A-final.md`；`tnnls_submission/figures.md`；`tnnls_submission/tables.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-38 — 文字是否像审计报告、反复重复限制？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / RECORDED
- 验收：每节先写发现与意义再限定范围；重复caveat集中到必要位置，wave/内部路径/开发历史移到补充。
- 证据类型：MANUSCRIPT_AND_RECORDS
- 入口：`docs/drafts/paper-A-final.md`；`docs/audit/gap96-manuscript-compression.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-39 — 参考文献和上游归属是否完整？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / RECORDED
- 验收：补齐直接相关原始文献、模型/数据/指标版本，逐条验证论断；不追求任意引用数量。
- 证据类型：SOURCE_AND_PRIMARY_LITERATURE
- 入口：`docs/drafts/paper-A-final.md`；`tnnls_submission/data_availability.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-40 — 审计可复现是否被当成科学正确性？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / RECORDED
- 验收：区分hash完整性、重放范围、实验有效性；补充精确命令环境、独立clone检查和匿名发布材料。
- 证据类型：SOURCE_AND_RECORDS
- 入口：`reproduce`；`paper-data`；`docs/environments.md`；`tools/check_clone_integrity.py`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-41 — 第一轮：主张与贡献是否锁定？

- 类别 / 优先级 / 状态：三轮执行计划 / P0 / RECORDED
- 验收：完成SC-02/03/04/07/12，交付一句中心主张、三贡献与证据映射，再进行大段重写。
- 证据类型：WORKFLOW
- 入口：`todo.json`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-42 — 第二轮：方法、相关工作、主结果是否重写到位？

- 类别 / 优先级 / 状态：三轮执行计划 / P1 / RECORDED
- 验收：围绕已核实证据扩写并同步协议、图表和引文；不以背景和工程功能凑篇幅。
- 证据类型：WORKFLOW
- 入口：`docs/audit/gap96-manuscript-compression.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-43 — 第三轮：是否按拒稿理由复查？

- 类别 / 优先级 / 状态：三轮执行计划 / P1 / RECORDED
- 验收：对创新、理论、比较、指标、统计逐项验收；每个残留新实验建议注明解决的问题与是否已有证据。
- 证据类型：WORKFLOW
- 入口：`todo.json`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-44 — TNNLS是否仍是合理首投？

- 类别 / 优先级 / 状态：投稿决策 / P1 / RECORDED
- 验收：P0复核后重评目标，区分大类/小类/分区年份；主题匹配不等于已证明达到录用标准。
- 证据类型：VENUE_GUIDELINES_AND_MANUSCRIPT
- 入口：`docs/audit/gap94-standard-benchmark.md`；`todo.json`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

### SC-45 — 是否完整记录全部上一轮审稿建议并同步源码？

- 类别 / 优先级 / 状态：记录与同步 / P0 / RECORDED
- 验收：保存本表和JSON、注册todo入口、更新audit索引；提交并推送服务器现有源码/记录历史后，从GitHub获取本地正式副本并核对HEAD。
- 证据类型：WORKFLOW
- 入口：`todo.json`；`docs/audit/INDEX.md`
- 本轮发现：已登记，待逐项核对。
- 下一步：按所列证据核对，记录文件/符号/行号与实际运行；未核对不标通过。

## 执行与授权边界

用户2026-11-02本轮明确要求先推送现有源代码和记录更新到GitHub，再拉取到Mac；仅适用于本次同步，不修改长期no_push默认。

本次仅新增自查记录及管理入口，刷新审计索引；不修改上游代码，不修改冻结论文/声明/投稿包，不启动长时GPU实验。服务器工作树起始干净；现有未推送源码历史包含在用户要求的项目同步范围。

## 本轮验证

验证命令与结果另见同目录的 manuscript-selfcheck-validation-2026-11-02.md；若某门禁有既有失败，明确记录，不伪称通过。

## 首轮源码观察的范围

本轮额外追踪MNIST驱动、通用runner入口、RK4阶段与投影评价器。SC-07/08/10/13/22/30/34记录了精确文件与行段；这些仅是源码观察和待核对问题，不是对实验收益、预算公平性或创新性的最终验收。没有为追求通过而修改算法或实验数字。
