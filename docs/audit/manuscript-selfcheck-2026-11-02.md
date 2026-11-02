# 投稿改进自查表（2026-11-02）

完整保留45项；当前状态已更新至第二轮源码核对与中文修订。原登记状态和发现保留在JSON的history。VERIFIED的范围是条目所列具体定义/文字/统计修正，不代表全部科学主张成立。

## 状态规则

- RECORDED：已登记，未完成核对；不表示证据缺失或结论成立。
- EVIDENCE_LOCATED：找到相关既有记录，尚未独立验证全部路径/统计及其是否进入中文稿。
- VERIFIED：逐项附源码符号/行号、artifact和适用范围后才允许使用。
- REVISION_NEEDED：已有充分证据，但稿件未正确呈现。
- EVIDENCE_GAP：核对已有代码/记录后确认仍缺证据。

## 当前覆盖表

| ID | 类别 | 优先级 | 自查问题 | 状态 |
|---|---|---|---|---|
| SC-01 | 篇幅与定位 | P0 | 当前中文稿是否具备完整投稿稿的论证密度？ | REVISION_NEEDED |
| SC-02 | 篇幅与定位 | P0 | 中心主张是否可用一句话表述且被证据覆盖？ | VERIFIED |
| SC-03 | 篇幅与定位 | P0 | 是方法论文还是软件框架论文？ | VERIFIED |
| SC-04 | 创新性 | P0 | 是否仅为已有 restart sampling 加接口封装？ | REVISION_NEEDED |
| SC-05 | 创新性 | P0 | 相比固定权重混合究竟新增什么？ | EVIDENCE_GAP |
| SC-06 | 创新性 | P0 | 首次性、普适性、全面占优是否有依据？ | VERIFIED |
| SC-07 | 方法定义 | P0 | FlowA 主方法是否是确定且可复现的算法？ | VERIFIED |
| SC-08 | 方法定义 | P0 | 反馈究竟读取什么信息？ | VERIFIED |
| SC-09 | 方法定义 | P0 | 连续、离散、掩码和图通道的操作是否合法？ | EVIDENCE_LOCATED |
| SC-10 | 方法定义 | P0 | 实际调用次数是否等于宣称预算？ | VERIFIED |
| SC-11 | 方法定义 | P1 | 四接口与算法步骤、伪代码是否一一对应？ | VERIFIED |
| SC-12 | 贡献与证据 | P0 | 各任务是否验证同一个机制？ | VERIFIED |
| SC-13 | 贡献与证据 | P0 | 各实验到底有没有真实多轮重启？ | EVIDENCE_LOCATED |
| SC-14 | 贡献与证据 | P0 | 已有但未写入中文稿的证据有哪些？ | VERIFIED |
| SC-15 | 主结果 | P0 | 优势集中一个 MNIST 检查点意味着什么？ | VERIFIED |
| SC-16 | 主结果 | P0 | 是否有第二条独立可信的实证主线？ | EVIDENCE_GAP |
| SC-17 | 主结果 | P0 | 训练充分性/检查点条件性是关联还是因果？ | VERIFIED |
| SC-18 | 主结果 | P1 | WIN/TIE 与显著性、实用阈值、局部退化是否混淆？ | VERIFIED |
| SC-19 | 理论 | P0 | 经典收缩与恒等式是否被包装成新理论？ | VERIFIED |
| SC-20 | 理论 | P0 | 定理假设是否覆盖实际算法？ | VERIFIED |
| SC-21 | 理论 | P0 | 是否越级推出目标分布或 FID 改善？ | VERIFIED |
| SC-22 | 理论 | P1 | κ诊断与理论 Lipschitz 收缩因子是否混称？ | VERIFIED |
| SC-23 | 比较公平性 | P0 | 收益来自重启还是求解器、初值、额外计算？ | REVISION_NEEDED |
| SC-24 | 比较公平性 | P1 | 是否拼接不同N、seed、checkpoint和evaluator？ | EVIDENCE_GAP |
| SC-25 | 比较公平性 | P1 | 等 NFE 是否被写成等耗时或加速？ | VERIFIED |
| SC-26 | 统计 | P0 | 独立运行次数、记录数和家族数是否混淆？ | EVIDENCE_LOCATED |
| SC-27 | 统计 | P0 | Kanzi 索引匹配是否错误当作天然配对？ | VERIFIED |
| SC-28 | 统计 | P1 | 三种子自举与家族相关性是否充分披露？ | EVIDENCE_LOCATED |
| SC-29 | 统计 | P1 | 多重比较和效应阈值是否一致？ | REVISION_NEEDED |
| SC-30 | 指标 | P1 | projection-FID 与标准 FID 是否混淆？ | VERIFIED |
| SC-31 | 指标 | P1 | 蛋白代理指标能否代表结构/功能/家族覆盖？ | EVIDENCE_LOCATED |
| SC-32 | 指标 | P1 | 合成重建与分子有效性定义是否准确？ | EVIDENCE_GAP |
| SC-33 | 指标 | P1 | 质量提升是否伴随新颖性/多样性损失？ | VERIFIED |
| SC-34 | 消融与机制 | P0 | 哪些组件真的必要？ | EVIDENCE_LOCATED |
| SC-35 | 消融与机制 | P1 | round数、beta、预算分配的解释是否被已有记录反驳？ | EVIDENCE_LOCATED |
| SC-36 | 消融与机制 | P1 | 残差修正解释是否被误当成机制证明？ | VERIFIED |
| SC-37 | 呈现与复现 | P2 | 图表是否完整且可供判断？ | REVISION_NEEDED |
| SC-38 | 呈现与复现 | P2 | 文字是否像审计报告、反复重复限制？ | VERIFIED |
| SC-39 | 呈现与复现 | P2 | 参考文献和上游归属是否完整？ | REVISION_NEEDED |
| SC-40 | 呈现与复现 | P2 | 审计可复现是否被当成科学正确性？ | EVIDENCE_GAP |
| SC-41 | 三轮执行计划 | P0 | 第一轮：主张与贡献是否锁定？ | VERIFIED |
| SC-42 | 三轮执行计划 | P1 | 第二轮：方法、相关工作、主结果是否重写到位？ | REVISION_NEEDED |
| SC-43 | 三轮执行计划 | P1 | 第三轮：是否按拒稿理由复查？ | EVIDENCE_LOCATED |
| SC-44 | 投稿决策 | P1 | TNNLS是否仍是合理首投？ | EVIDENCE_LOCATED |
| SC-45 | 记录与同步 | P0 | 是否完整记录全部上一轮审稿建议并同步源码？ | VERIFIED |

## 逐项验收与发现

### SC-01 — 当前中文稿是否具备完整投稿稿的论证密度？

- 类别 / 优先级 / 状态：篇幅与定位 / P0 / REVISION_NEEDED
- 验收：按正文、方法、协议、结果和文献逐节核算，区分中文页数与英文双栏；不以扩写背景凑页。
- 本轮发现：新版按证据扩充方法、六检查点、统计与诊断；正式英文双栏页数尚未编排，不能按中文页数验收。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap96-manuscript-compression.md`；`docs/drafts/paper-A-final.tex`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-02 — 中心主张是否可用一句话表述且被证据覆盖？

- 类别 / 优先级 / 状态：篇幅与定位 / P0 / VERIFIED
- 验收：记录一句中心主张、三项贡献及各自最强证据；所有超出证据范围的词单列。
- 本轮发现：新版引言给出单句问题、三层贡献及证据范围；验证范围为稿件组织，不代表创新性获得外部认可。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/PAPER-EVIDENCE.md`；`todo.json`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-03 — 是方法论文还是软件框架论文？

- 类别 / 优先级 / 状态：篇幅与定位 / P0 / VERIFIED
- 验收：明确主定位及次贡献；章节和实验围绕同一定位，不用工程接口代替方法新意。
- 本轮发现：定位为明确算法实例及其检查点条件性实证，框架接口降为复用实现；不以接口数量替代方法贡献。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`docs/STRATEGY_FRAMEWORK_SCOPE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-04 — 是否仅为已有 restart sampling 加接口封装？

- 类别 / 优先级 / 状态：创新性 / P0 / REVISION_NEEDED
- 验收：与最接近原始论文逐项比较状态、反馈、训练需求、预算、重启方式；不能凭源码存在判定新颖性。
- 本轮发现：已核对Restart、FM/RF、DPM-Solver与一致性模型原始来源并增加比较表；同协议最接近方法数值对照仍缺。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`docs/audit/gap94-standard-benchmark.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-05 — 相比固定权重混合究竟新增什么？

- 类别 / 优先级 / 状态：创新性 / P0 / EVIDENCE_GAP
- 验收：给出唯一可辨的算法差异、代码路径和对应对照；不用多个功能同时变化的比较归因。
- 本轮发现：已补质心组件的局部隔离，但固定混合、重启时间、调度与质心在主前沿βtot=.3下的同协议完整矩阵仍缺，无法从源码认定新增组件各自必要。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/blender/blender.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-06 — 首次性、普适性、全面占优是否有依据？

- 类别 / 优先级 / 状态：创新性 / P0 / VERIFIED
- 验收：逐词检查标题摘要贡献；不能证实的首次、普适、SOTA或全面优势删除或收窄。
- 本轮发现：新版标题、摘要和结论不作首次、普适质量或普遍加速主张；结果限定到检查点与具体配置。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-07 — FlowA 主方法是否是确定且可复现的算法？

- 类别 / 优先级 / 状态：方法定义 / P0 / VERIFIED
- 验收：锁定主方法实例，完整定义状态、反馈、调度、混合、停止和预算；可选框架配置另列。
- 本轮发现：新版III-A至E明确首轮、fresh prior、累计beta、实际轮数、部分区间RK4与最终batch质心平移，配可执行步骤表。仅核实定义。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/scheduler/evidence_driven.py`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-08 — 反馈究竟读取什么信息？

- 类别 / 优先级 / 状态：方法定义 / P0 / VERIFIED
- 验收：列出评价/标签/参考数据是否参与控制、调用时机和成本，区分事后评价与在线控制。
- 本轮发现：主MNIST驱动预先取scheduler权重且无record_round_feedback调用；新稿不声称已启用在线PID。通用runner能力另列。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/algorithm/evidence_driver.py`；`adaptive_reflow/algorithm/runner/runner.py`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-09 — 连续、离散、掩码和图通道的操作是否合法？

- 类别 / 优先级 / 状态：方法定义 / P0 / EVIDENCE_LOCATED
- 验收：逐通道核对状态域、先验、尺度、混合和验证，明确线性理论仅适用的范围。
- 本轮发现：已区分连续线性实例与跨域通道适配；尚未逐个核完离散/图通道的实际headline路径。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/algorithm/blender/per_channel_blender.py`；`adaptive_reflow/adapters`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-10 — 实际调用次数是否等于宣称预算？

- 类别 / 优先级 / 状态：方法定义 / P0 / VERIFIED
- 验收：核对求解器每步调用、round floor、取整和不可执行设置；报告真实 NFE 而非仅配置步数。
- 本轮发现：NumPy和Torch的实际积分循环均每步四次速度场调用。新图以C=4S标轴；原始JSON的nfe键不改写。等RK4步数仍为等调用次数。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/algorithm/nfe_allocation.py`；`adaptive_reflow/algorithm/solver.py`；`docs/audit/gap90-optsteps-dose.md`；`scripts/wave191_p3_mnist_sweep.py`；`adaptive_reflow/adapters/mnist_fm.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-11 — 四接口与算法步骤、伪代码是否一一对应？

- 类别 / 优先级 / 状态：方法定义 / P1 / VERIFIED
- 验收：画方法图并给出可复现伪代码；接口只解释职责，指出真实调用实现和旁路。
- 本轮发现：III-E伪代码、III-F接口与实际驱动区分，明确预先调度、restart与batch后处理；不以通用runner替代实际实验路径。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/runner/sequential.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-12 — 各任务是否验证同一个机制？

- 类别 / 优先级 / 状态：贡献与证据 / P0 / VERIFIED
- 验收：建立贡献→组件→实际比较臂→artifact 对应表；只验证集成的任务不得当作算法优势。
- 本轮发现：v3表A建立组件→实际比较臂→证据范围。Kanzi是不同来源结构的自编码往返；R6随机序列基线及低预算门控不支持同机制跨域验证；FlowMol3历史坐标扰动与GAP39全通道prior混合分列。验证范围为映射与稿件表述。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/PAPER-EVIDENCE.md`；`docs/paper-evidence.json`；`paper-data`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-13 — 各实验到底有没有真实多轮重启？

- 类别 / 优先级 / 状态：贡献与证据 / P0 / EVIDENCE_LOCATED
- 验收：逐格追踪实际启用的调度、restart、反馈与 no-op 路径；单轮不能证明多轮迭代价值。
- 本轮发现：MNIST端点多轮、Kanzi单次rollout、FlowMol3历史及GAP39一次solve已追踪。R6三份清单nfe10<门槛20，源码915行降一轮；历史清单未存生成提交/加载模式，不能据请求三轮当作实际三轮。其余扩展单元仍逐格保留核对。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap80-r5a-harness.md`；`docs/audit/gap95-frontier-grids.md`；`docs/PAPER-EVIDENCE.md`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-14 — 已有但未写入中文稿的证据有哪些？

- 类别 / 优先级 / 状态：贡献与证据 / P0 / VERIFIED
- 验收：纳入 GAP-90 六检查点、GAP-91 描述性拟合、GAP-92 κ诊断及 GAP-93剂量记录；明确其有限结论，不重跑已有实验。
- 本轮发现：新稿加入GAP-90六点/受控轴、GAP-91插值与修正区间、GAP-92κ诊断，并保留已有预注册失败和边界。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap90-optsteps-dose.md`；`docs/audit/gap92-kappa-bridge.md`；`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-15 — 优势集中一个 MNIST 检查点意味着什么？

- 类别 / 优先级 / 状态：主结果 / P0 / VERIFIED
- 验收：完整报告六检查点/受控轴及历史四检查点关系、平台、局部损失、绝对效应；不得沿用仅四点且全部混杂的旧判断。
- 本轮发现：六点表与两张新图补齐；一个WIN、五个TIE按当前绝对规则报告，低预算未限制与限制版本分开。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap90-optsteps-dose.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-16 — 是否有第二条独立可信的实证主线？

- 类别 / 优先级 / 状态：主结果 / P0 / EVIDENCE_GAP
- 验收：核对 live 蛋白结果及比较臂、指标、种子/家族限制，判断能否支撑第二主结果，不凭 pooled n 决定。
- 本轮发现：已追到live R6评价与生成入口：baseline为家族偏置随机抽样，framework走适配器；live指标不等于匹配模型对照。R6清单和门控也不足以证实多轮。当前不存在已闭合的第二条同机制跨家族前沿主线，正文降为描述性结果。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap95-frontier-grids.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：先从既有匹配模型记录寻找独立同机制证据；没有则保留缺口，不以pooled记录数替代。

### SC-17 — 训练充分性/检查点条件性是关联还是因果？

- 类别 / 优先级 / 状态：主结果 / P0 / VERIFIED
- 验收：区分固定宽度的数据剂量、固定数据的 epoch 剂量、宽度对照及未满足的严格单调条件；按预注册逐条报告。
- 本轮发现：区分数据规模轴、epoch轴和宽度对照；数据规模和优化步数并非独立变量，严格单调假设失败公开报告。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-18 — WIN/TIE 与显著性、实用阈值、局部退化是否混淆？

- 类别 / 优先级 / 状态：主结果 / P1 / VERIFIED
- 验收：明确绝对/相对阈值、区间、平台和逐档条件；TIE不写成严格等效，也不隐去低预算损失。
- 本轮发现：新稿区分零差异、绝对效应阈值、相对规则、平台及低档局部损失；TIE不称为严格等效。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap84-inference-frontier.md`；`docs/paper-evidence.json`；`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-19 — 经典收缩与恒等式是否被包装成新理论？

- 类别 / 优先级 / 状态：理论 / P0 / VERIFIED
- 验收：明确经典工具与新增推导的边界；基础性质不单独承担创新性。
- 本轮发现：新稿明言经典压缩映射原理与凸组合恒等式不单独承担新的理论贡献。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-20 — 定理假设是否覆盖实际算法？

- 类别 / 优先级 / 状态：理论 / P0 / VERIFIED
- 验收：逐项对应固定fresh input、m、状态域、Lipschitz、精确/数值映射；变化参数或随机输入不直接套固定点结论。
- 本轮发现：新稿限定固定输入、固定映射、状态域与数值稳定性假设；变化时间/轮数和batch平移不被套入完整收敛结论。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`adaptive_reflow/algorithm/blender/blender.py`；`adaptive_reflow/algorithm/nfe_allocation.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-21 — 是否越级推出目标分布或 FID 改善？

- 类别 / 优先级 / 状态：理论 / P0 / VERIFIED
- 验收：分开固定点收敛、状态误差、特征分布距离；未建立的桥梁不写成定理推论。
- 本轮发现：状态误差、固定点、特征分布距离分开陈述，未将两条性质写成FID或目标分布保证。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`docs/audit/gap92-kappa-bridge.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-22 — κ诊断与理论 Lipschitz 收缩因子是否混称？

- 类别 / 优先级 / 状态：理论 / P1 / VERIFIED
- 验收：核对 κ 的计算定义、数据依赖、预算/调度臂和样本数；不得把经验协方差比等同于mK或因果规律。
- 本轮发现：κ源码为经验投影协方差迹比；新稿不等同mK，披露不同预算/多臂汇总以及需要框架臂样本的条件。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`；`tools/gap78_observable_screen.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-23 — 收益来自重启还是求解器、初值、额外计算？

- 类别 / 优先级 / 状态：比较公平性 / P0 / REVISION_NEEDED
- 验收：各臂列相同/变化因素；把solver、初始化、表示桥接、反馈、预算分离；不能归因的结果限缩解释。
- 本轮发现：v3按任务分列变化因素，Kanzi桥接/样本来源、蛋白生成器不同、FlowMol3先验扰动均不再归因于端点多轮；MNIST已复算质心隔离，但主前沿完整组件归因仍缺。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/PAPER-EVIDENCE.md`；`paper-data`；`adaptive_reflow/adapters`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-24 — 是否拼接不同N、seed、checkpoint和evaluator？

- 类别 / 优先级 / 状态：比较公平性 / P1 / EVIDENCE_GAP
- 验收：建立逐单元协议表；异协议/历史端点分列；每个数值及其统计都来自兼容的artifact。
- 本轮发现：发现部分summary残留beta_framework=0.5而有效beta_total=0.3，且命令为模板字符串；不改历史文件，不盲信这些字段。需逐运行重建完整manifest。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap90-optsteps-dose.md`；`paper-data`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-25 — 等 NFE 是否被写成等耗时或加速？

- 类别 / 优先级 / 状态：比较公平性 / P1 / VERIFIED
- 验收：单独报告辅助评价和状态转换开销；实际时间只在同设备同实现下比较；外推加速不写成实测。
- 本轮发现：新稿不把等NFE写成等时间；MNIST横轴换算真实调用，质量平台优势不称实测加速。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-26 — 独立运行次数、记录数和家族数是否混淆？

- 类别 / 优先级 / 状态：统计 / P0 / EVIDENCE_LOCATED
- 验收：每个CI/p/效应量写统计单位；pooled记录不替代种子重复，合成变体不替代独立结构。
- 本轮发现：新增Kanzi索引相关.04563及四PDB×250变体，Welch仅作独立记录假设敏感性；消融以三个生成种子为单位。R6按qid对应不等于同一序列前后，pooled3000不作独立生成器重复。其他单元单位仍保留逐格核对。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-27 — Kanzi 索引匹配是否错误当作天然配对？

- 类别 / 优先级 / 状态：统计 / P0 / VERIFIED
- 验收：追踪实际样本生成和相关性、检验实现及源均值；核对独立样本分析与dz命名，按正确单位重述；不预先认定旧检验正确。
- 本轮发现：从0d070700恢复被9c28d52f删除的原baseline，SHA256 be03a0a9…，1000键完全匹配，均值及旧p=.001794精确复现。新增Welch p=.002254、CI[-.031124,-.006804]Å，七R级家族校正p=.01578。两臂测不同来源结构，索引差值不称同输入配对，dz只标历史。验证范围为来源、统计重算与正确解释；不认定天然总体因果获益。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：已复算来源与统计；如要主张同输入优化，另需同输入或同生成器匹配设计，不通过改标签获得。

### SC-28 — 三种子自举与家族相关性是否充分披露？

- 类别 / 优先级 / 状态：统计 / P1 / EVIDENCE_LOCATED
- 验收：写明有限种子自举分辨率/区间局限、聚类单位与已有敏感性分析；不靠追加种子自动过关。
- 本轮发现：三种子自举局限已披露；四点回归df=2临界值已修复并有失败后通过的回归测试。全体蛋白家族敏感性未独立重算。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap84-inference-frontier.md`；`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-29 — 多重比较和效应阈值是否一致？

- 类别 / 优先级 / 状态：统计 / P1 / REVISION_NEEDED
- 验收：定义检验家族、选择规则、校正次数、效应量和区间；区分探索与确认，缺失区间不补写。
- 本轮发现：Kanzi沿历史七R级家族报告校正p，明确不覆盖后续调参与多指标；消融12区间未作同时覆盖、仅探索描述。全项目选择路径及检验家族仍未统一闭合。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap84-inference-frontier.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-30 — projection-FID 与标准 FID 是否混淆？

- 类别 / 优先级 / 状态：指标 / P1 / VERIFIED
- 验收：追踪特征提取器、投影、参考集、样本量、随机种子与实现；不跨特征空间比较绝对值。
- 本轮发现：已沿主驱动到MnistFrechetProjectionEvaluator核实784→128固定高斯像素投影和10000测试图像参考；新稿与Inception FID分开。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/adapters/mnist_fm.py`；`adaptive_reflow/eval`；`docs/audit/gap84-inference-frontier.md`；`adaptive_reflow/eval/mnist_fid.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-31 — 蛋白代理指标能否代表结构/功能/家族覆盖？

- 类别 / 优先级 / 状态：指标 / P1 / EVIDENCE_LOCATED
- 验收：逐项解释pLDDT、scPerplexity、HMMER与家族身份，明确其能与不能支持的结论。
- 本轮发现：代理指标解释已收窄；上游评估器版本和对应原始文献归属待完整补齐。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap79-r1-family-lever.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-32 — 合成重建与分子有效性定义是否准确？

- 类别 / 优先级 / 状态：指标 / P1 / EVIDENCE_GAP
- 验收：核对坐标来源、单位、对齐、几何桥接、PoseBusters与RDKit的区别及逐记录存储完整性。
- 本轮发现：Kanzi底层恢复并核对输入为4模板扰动、桥生成结构与各自自编码往返；两臂来源不同不称天然结构恢复。FlowMol3历史proxy及真实通道混合分列，PoseBusters逐分子verdict缺口仍未恢复。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/audit/gap39-flowmol3-real-restart-blend.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-33 — 质量提升是否伴随新颖性/多样性损失？

- 类别 / 优先级 / 状态：指标 / P1 / VERIFIED
- 验收：公开K7负结果及参考数据库/阈值；将质量、自一致性、覆盖和新颖性分开，不主张同步改善。
- 本轮发现：已在主文保留K7新颖性46.6%→3.7%的不利读数及数据库/阈值范围；未宣称所有质量轴同步提升。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap70-lineageflow-position-blend.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-34 — 哪些组件真的必要？

- 类别 / 优先级 / 状态：消融与机制 / P0 / EVIDENCE_LOCATED
- 验收：盘点已有无反馈、固定混合、自适应控制、完整方法对照；相同协议才可拼成因果消融，不存在的格子标缺失。
- 本轮发现：GAP76已有实际质心消融，不只是反事实。36比较从96个既有NPZ复算，协方差控制36/36；seed42仅6/12 Δ≤0未达到8/12预测。βtot=.5与主前沿.3不同，不能补成主前沿完整矩阵。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`adaptive_reflow/algorithm/policy_driver.py`；`docs/ABLATION.md`；`docs/audit/gap90-optsteps-dose.md`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-35 — round数、beta、预算分配的解释是否被已有记录反驳？

- 类别 / 优先级 / 状态：消融与机制 / P1 / EVIDENCE_LOCATED
- 验收：检查GAP-84/90/93和各适配器真实路径；保留已证伪杠杆和不显著结果，不重复提出已做实验。
- 本轮发现：已有round/beta/low-budget审计保留，不重复安排训练或长时采样；尚未逐份重建所有消融配置。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`todo.json`；`docs/audit/gap90-optsteps-dose.md`；`docs/ABLATION.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-36 — 残差修正解释是否被误当成机制证明？

- 类别 / 优先级 / 状态：消融与机制 / P1 / VERIFIED
- 验收：把直接观测、解释与未知分开；源码只证明执行机制，不能单独证明质量变化的因果机制。
- 本轮发现：新稿区分源码执行、经验统计与残差修正解释，未把后者当成因果证明。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-37 — 图表是否完整且可供判断？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / REVISION_NEEDED
- 验收：方法图、可执行算法、逐任务协议表、主曲线不确定性、案例和完整状态表；图注自解释且可回溯源数据。
- 本轮发现：已增加六点含种子SD前沿图、三条受控轴图和方法/协议/证据表；定性样本案例、完整匿名补充仍未完成。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`tnnls_submission/figures.md`；`tnnls_submission/tables.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-38 — 文字是否像审计报告、反复重复限制？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / VERIFIED
- 验收：每节先写发现与意义再限定范围；重复caveat集中到必要位置，wave/内部路径/开发历史移到补充。
- 本轮发现：正文按问题—实例—分析—结果—解释重组；运行路径和内部编号集中到内部复现索引。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`docs/audit/gap96-manuscript-compression.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-39 — 参考文献和上游归属是否完整？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / REVISION_NEEDED
- 验收：补齐直接相关原始文献、模型/数据/指标版本，逐条验证论断；不追求任意引用数量。
- 本轮发现：参考文献扩展到8条核实来源；上游蛋白/分子模型、指标和数据的完整版本引文仍待补齐。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/drafts/paper-A-final.md`；`tnnls_submission/data_availability.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-40 — 审计可复现是否被当成科学正确性？

- 类别 / 优先级 / 状态：呈现与复现 / P2 / EVIDENCE_GAP
- 验收：区分hash完整性、重放范围、实验有效性；补充精确命令环境、独立clone检查和匿名发布材料。
- 本轮发现：恢复原Kanzi并纳入两臂1000记录，新增统计重算工具与SHA清单；消融提供派生表/24份运行汇总，96个服务器NPZ登记hash但未新发布。Git clone可重建统计/表格层，完整样本重生成及匿名材料层仍缺，未称完全复现。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`reproduce`；`paper-data`；`docs/environments.md`；`tools/check_clone_integrity.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-41 — 第一轮：主张与贡献是否锁定？

- 类别 / 优先级 / 状态：三轮执行计划 / P0 / VERIFIED
- 验收：完成SC-02/03/04/07/12，交付一句中心主张、三贡献与证据映射，再进行大段重写。
- 本轮发现：中心主张、三层贡献和证据层级已在新版落实；方法/框架定位明确。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-42 — 第二轮：方法、相关工作、主结果是否重写到位？

- 类别 / 优先级 / 状态：三轮执行计划 / P1 / REVISION_NEEDED
- 验收：围绕已核实证据扩写并同步协议、图表和引文；不以背景和工程功能凑篇幅。
- 本轮发现：已生成v3，新增实际组件消融、Kanzi复算与任务路径映射，收紧跨域主张。完整相关工作匹配对照、全部上游引文及正式英文模板仍待后续。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap96-manuscript-compression.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`
- 下一步：按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。

### SC-43 — 第三轮：是否按拒稿理由复查？

- 类别 / 优先级 / 状态：三轮执行计划 / P1 / EVIDENCE_LOCATED
- 验收：对创新、理论、比较、指标、统计逐项验收；每个残留新实验建议注明解决的问题与是否已有证据。
- 本轮发现：本轮按定义、预算、理论和统计识别并修正具体问题；剩余拒稿风险在表中保留，不宣称全稿验收。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-44 — TNNLS是否仍是合理首投？

- 类别 / 优先级 / 状态：投稿决策 / P1 / EVIDENCE_LOCATED
- 验收：P0复核后重评目标，区分大类/小类/分区年份；主题匹配不等于已证明达到录用标准。
- 本轮发现：继续以TNNLS为目标，但竞争性benchmark、消融与引用缺口仍影响投稿判断；本轮未新做期刊排名结论。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`docs/audit/gap94-standard-benchmark.md`；`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。

### SC-45 — 是否完整记录全部上一轮审稿建议并同步源码？

- 类别 / 优先级 / 状态：记录与同步 / P0 / VERIFIED
- 验收：保存本表和JSON、注册todo入口、更新audit索引；提交并推送服务器现有源码/记录历史后，从GitHub获取本地正式副本并核对HEAD。
- 本轮发现：上一轮全部45项与源码已同步；本轮在相同表中保留历史并记录范围，不以VERIFIED表示整个项目已无问题。
- 验证范围：本项列明的源码或稿件修正；不是整项外部有效性、创新性或审稿录用保证。
- 入口：`todo.json`；`docs/audit/INDEX.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`
- 下一步：按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。
