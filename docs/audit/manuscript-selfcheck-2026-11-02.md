# 投稿改进自查表（2026-11-02）

完整保留45项及各轮历史；更新至2026-11-03第五轮路径条件、独立图像验证与原始方法对照。VERIFIED仅表示条目限定修正，不代表整稿科学主张或一区录用成立。

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
| SC-04 | 创新性 | P0 | 是否仅为已有 restart sampling 加接口封装？ | EVIDENCE_GAP |
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
| SC-23 | 比较公平性 | P0 | 收益来自重启还是求解器、初值、额外计算？ | VERIFIED |
| SC-24 | 比较公平性 | P1 | 是否拼接不同N、seed、checkpoint和evaluator？ | EVIDENCE_GAP |
| SC-25 | 比较公平性 | P1 | 等 NFE 是否被写成等耗时或加速？ | VERIFIED |
| SC-26 | 统计 | P0 | 独立运行次数、记录数和家族数是否混淆？ | EVIDENCE_LOCATED |
| SC-27 | 统计 | P0 | Kanzi 索引匹配是否错误当作天然配对？ | VERIFIED |
| SC-28 | 统计 | P1 | 三种子自举与家族相关性是否充分披露？ | EVIDENCE_LOCATED |
| SC-29 | 统计 | P1 | 多重比较和效应阈值是否一致？ | REVISION_NEEDED |
| SC-30 | 指标 | P1 | projection-FID 与标准 FID 是否混淆？ | VERIFIED |
| SC-31 | 指标 | P1 | 蛋白代理指标能否代表结构/功能/家族覆盖？ | VERIFIED |
| SC-32 | 指标 | P1 | 合成重建与分子有效性定义是否准确？ | EVIDENCE_GAP |
| SC-33 | 指标 | P1 | 质量提升是否伴随新颖性/多样性损失？ | VERIFIED |
| SC-34 | 消融与机制 | P0 | 哪些组件真的必要？ | VERIFIED |
| SC-35 | 消融与机制 | P1 | round数、beta、预算分配的解释是否被已有记录反驳？ | VERIFIED |
| SC-36 | 消融与机制 | P1 | 残差修正解释是否被误当成机制证明？ | VERIFIED |
| SC-37 | 呈现与复现 | P2 | 图表是否完整且可供判断？ | VERIFIED |
| SC-38 | 呈现与复现 | P2 | 文字是否像审计报告、反复重复限制？ | VERIFIED |
| SC-39 | 呈现与复现 | P2 | 参考文献和上游归属是否完整？ | REVISION_NEEDED |
| SC-40 | 呈现与复现 | P2 | 审计可复现是否被当成科学正确性？ | VERIFIED |
| SC-41 | 三轮执行计划 | P0 | 第一轮：主张与贡献是否锁定？ | REVISION_NEEDED |
| SC-42 | 三轮执行计划 | P1 | 第二轮：方法、相关工作、主结果是否重写到位？ | REVISION_NEEDED |
| SC-43 | 三轮执行计划 | P1 | 第三轮：是否按拒稿理由复查？ | EVIDENCE_LOCATED |
| SC-44 | 投稿决策 | P1 | TNNLS是否仍是合理首投？ | EVIDENCE_LOCATED |
| SC-45 | 记录与同步 | P0 | 是否完整记录全部上一轮审稿建议并同步源码？ | VERIFIED |

## 逐项记录

### SC-01 当前中文稿是否具备完整投稿稿的论证密度？

- 类别/优先级：篇幅与定位 / P0
- 状态：REVISION_NEEDED
- 验收：按正文、方法、协议、结果和文献逐节核算，区分中文页数与英文双栏；不以扩写背景凑页。
- 发现：正文围绕路径条件、组件和独立图像对照重写，历史跨域与参数资料移入附录；中文稿的实际字数、表图数另列验收。正式英文双栏与期刊页数尚未编排。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：在科学主张稳定后按目标期刊英文模板编排，核对正文/附录页数及图表密度；不按中文Word页数推算英文合规。
- 证据：`docs/audit/gap96-manuscript-compression.md`；`docs/drafts/paper-A-final.tex`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-02 中心主张是否可用一句话表述且被证据覆盖？

- 类别/优先级：篇幅与定位 / P0
- 状态：VERIFIED
- 验收：记录一句中心主张、三项贡献及各自最强证据；所有超出证据范围的词单列。
- 发现：中心问题收窄为端点再推理的路径条件、组件作用与独立适用性；完整配置不具备普遍质量保证，所有定量结论来自锁定研究。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/PAPER-EVIDENCE.md`；`todo.json`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-03 是方法论文还是软件框架论文？

- 类别/优先级：篇幅与定位 / P0
- 状态：VERIFIED
- 验收：明确主定位及次贡献；章节和实验围绕同一定位，不用工程接口代替方法新意。
- 发现：当前主定位为指定边界核的条件分析和受控实证，接口工程为复现支持。能否形成足够原创的一区方法贡献仍属SC-04/05缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/drafts/paper-A-final.md`；`docs/STRATEGY_FRAMEWORK_SCOPE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-04 是否仅为已有 restart sampling 加接口封装？

- 类别/优先级：创新性 / P0
- 状态：EVIDENCE_GAP
- 验收：与最接近原始论文逐项比较状态、反馈、训练需求、预算、重启方式；不能凭源码存在判定新颖性。
- 发现：已补同RF权重、实际调用匹配的原始Restart函数与VE-Heun控制；Diamond Maps端点特例及NR-SMC状态更新存在直接重合，不能再把端点混合作为独有操作。完整系统的奖励/后验目标没有对照，原创贡献仍未充分建立。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：先列与Diamond Maps/NR-SMC/Restart逐操作及目标的差异；若没有独立且有价值的可检验主张，改为条件分析定位，暂缓按新采样方法投稿。
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/gap94-standard-benchmark.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-05 相比固定权重混合究竟新增什么？

- 类别/优先级：创新性 / P0
- 状态：EVIDENCE_GAP
- 验收：给出唯一可辨的算法差异、代码路径和对应对照；不用多个功能同时变化的比较归因。
- 发现：主参数组件矩阵与独立零时间简化配置区分组件；后段时间匹配两轮候选另行留出验证。操作差异及经典误差界不足以证明相对固定混合/先前端点构造的新颖性。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：以已有单因素矩阵判断哪些差异真实影响结果；仅对可识别的新差异设计最小控制，不把路径一致修正本身当新算子。
- 证据：`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/blender/blender.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-06 首次性、普适性、全面占优是否有依据？

- 类别/优先级：创新性 / P0
- 状态：VERIFIED
- 验收：逐词检查标题摘要贡献；不能证实的首次、普适、SOTA或全面优势删除或收窄。
- 发现：题目、摘要和结论按实际结果写条件与适用性，删除首次/普适/全面优势；同一检查点新生成种子不称新模型确认。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/drafts/paper-A-final.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-07 FlowA 主方法是否是确定且可复现的算法？

- 类别/优先级：方法定义 / P0
- 状态：VERIFIED
- 验收：锁定主方法实例，完整定义状态、反馈、调度、混合、停止和预算；可选框架配置另列。
- 发现：明确MNIST四轮配置、CIFAR移植、四轮零时间候选和两轮物理时间一致候选；预算、状态、时间、全批质心处理和随机政策分别记录，候选不替换原主配置。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/scheduler/evidence_driven.py`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-08 反馈究竟读取什么信息？

- 类别/优先级：方法定义 / P0
- 状态：VERIFIED
- 验收：列出评价/标签/参考数据是否参与控制、调用时机和成本，区分事后评价与在线控制。
- 发现：CIFAR五臂和两轮候选均不以测试参考作在线控制，固定调度；参考仅用于事后特征评分。不能将预定调度描述为自适应质量反馈。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`adaptive_reflow/algorithm/evidence_driver.py`；`adaptive_reflow/algorithm/runner/runner.py`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-09 连续、离散、掩码和图通道的操作是否合法？

- 类别/优先级：方法定义 / P0
- 状态：EVIDENCE_LOCATED
- 验收：逐通道核对状态域、先验、尺度、混合和验证，明确线性理论仅适用的范围。
- 发现：已区分连续线性实例与跨域通道适配；尚未逐个核完离散/图通道的实际headline路径。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：逐个离散/图通道检查先验、合法域和混合执行路径；未满足连续理论的任务仅保留集成范围。
- 证据：`adaptive_reflow/algorithm/blender/per_channel_blender.py`；`adaptive_reflow/adapters`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-10 实际调用次数是否等于宣称预算？

- 类别/优先级：方法定义 / P0
- 状态：VERIFIED
- 验收：核对求解器每步调用、round floor、取整和不可执行设置；报告真实 NFE 而非仅配置步数。
- 发现：MNIST的RK4成本C=4S；CIFAR逐臂计数匹配25/49/99/199实际速度场调用。Restart原函数计数与Heun控制单独测试，两轮分配C99=[76,23]、C199=[153,46]。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`adaptive_reflow/algorithm/nfe_allocation.py`；`adaptive_reflow/algorithm/solver.py`；`docs/audit/gap90-optsteps-dose.md`；`scripts/wave191_p3_mnist_sweep.py`；`adaptive_reflow/adapters/mnist_fm.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-11 四接口与算法步骤、伪代码是否一一对应？

- 类别/优先级：方法定义 / P1
- 状态：VERIFIED
- 验收：画方法图并给出可复现伪代码；接口只解释职责，指出真实调用实现和旁路。
- 发现：III-E伪代码、III-F接口与实际驱动区分，明确预先调度、restart与batch后处理；不以通用runner替代实际实验路径。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/runner/sequential.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-12 各任务是否验证同一个机制？

- 类别/优先级：贡献与证据 / P0
- 状态：VERIFIED
- 验收：建立贡献→组件→实际比较臂→artifact 对应表；只验证集成的任务不得当作算法优势。
- 发现：正文仅以MNIST及独立CIFAR检验指定连续边界核；R1/R6随机序列与R2不同来源结构记录移附录，当前证据等级降为PARTIAL，历史记录保留。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/PAPER-EVIDENCE.md`；`docs/paper-evidence.json`；`paper-data`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-13 各实验到底有没有真实多轮重启？

- 类别/优先级：贡献与证据 / P0
- 状态：EVIDENCE_LOCATED
- 验收：逐格追踪实际启用的调度、restart、反馈与 no-op 路径；单轮不能证明多轮迭代价值。
- 发现：MNIST端点多轮、Kanzi单次rollout、FlowMol3历史及GAP39一次solve已追踪。R6三份清单nfe10<门槛20，源码915行降一轮；历史清单未存生成提交/加载模式，不能据请求三轮当作实际三轮。其余扩展单元仍逐格保留核对。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：按每任务实际配置与日志记录有效轮数、门槛和no-op；没有完整生成日志的格子维持未验收。
- 证据：`docs/audit/gap80-r5a-harness.md`；`docs/audit/gap95-frontier-grids.md`；`docs/PAPER-EVIDENCE.md`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-14 已有但未写入中文稿的证据有哪些？

- 类别/优先级：贡献与证据 / P0
- 状态：VERIFIED
- 验收：纳入 GAP-90 六检查点、GAP-91 描述性拟合、GAP-92 κ诊断及 GAP-93剂量记录；明确其有限结论，不重跑已有实验。
- 发现：新稿加入GAP-90六点/受控轴、GAP-91插值与修正区间、GAP-92κ诊断，并保留已有预注册失败和边界。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/audit/gap92-kappa-bridge.md`；`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-15 优势集中一个 MNIST 检查点意味着什么？

- 类别/优先级：主结果 / P0
- 状态：VERIFIED
- 验收：完整报告六检查点/受控轴及历史四检查点关系、平台、局部损失、绝对效应；不得沿用仅四点且全部混杂的旧判断。
- 发现：完整保留六检查点一WIN五TIE及弱检查点平台−12.75%；新增独立图像研究不与投影指标合并，按其真实正负结果判断迁移。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-16 是否有第二条独立可信的实证主线？

- 类别/优先级：主结果 / P0
- 状态：EVIDENCE_GAP
- 验收：核对 live 蛋白结果及比较臂、指标、种子/家族限制，判断能否支撑第二主结果，不凭 pooled n 决定。
- 发现：已建立独立CIFAR同模型、同特征、匹配调用的可信验证；是否产生正向结果按预定分析报告，不能把负向验证、两个预算点候选或同权重新种子包装成第二条完整正向前沿。尚无新训练重复。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：优先根据现有独立研究判定是否值得继续候选；后续需新训练检查点及完整成本网格，当前预算内不再启动GPU。
- 证据：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap95-frontier-grids.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-17 训练充分性/检查点条件性是关联还是因果？

- 类别/优先级：主结果 / P0
- 状态：VERIFIED
- 验收：区分固定宽度的数据剂量、固定数据的 epoch 剂量、宽度对照及未满足的严格单调条件；按预注册逐条报告。
- 发现：区分数据规模轴、epoch轴和宽度对照；数据规模和优化步数并非独立变量，严格单调假设失败公开报告。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-18 WIN/TIE 与显著性、实用阈值、局部退化是否混淆？

- 类别/优先级：主结果 / P1
- 状态：VERIFIED
- 验收：明确绝对/相对阈值、区间、平台和逐档条件；TIE不写成严格等效，也不隐去低预算损失。
- 发现：原绝对WIN/TIE规则完整保留；CIFAR使用事前KID面积、家族内Holm、实用阈值与逐档前沿核查，未达到条件不等于等效。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap84-inference-frontier.md`；`docs/paper-evidence.json`；`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-19 经典收缩与恒等式是否被包装成新理论？

- 类别/优先级：理论 / P0
- 状态：VERIFIED
- 验收：明确经典工具与新增推导的边界；基础性质不单独承担创新性。
- 发现：独立插值恒等式、Wasserstein耦合与偏差—收缩递推明确为基础工具；Restart已有误差/收缩竞争分析，不把重述经典性质当新理论。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-20 定理假设是否覆盖实际算法？

- 类别/优先级：理论 / P0
- 状态：VERIFIED
- 验收：逐项对应固定fresh input、m、状态域、Lipschitz、精确/数值映射；变化参数或随机输入不直接套固定点结论。
- 发现：独立训练耦合与正确物理时间为充分条件；逐轮不等参数的乘积—求和误差界对应数值误差，L和偏差未估计；全批质心配置不直接套理想样本核。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/drafts/paper-A-final.md`；`adaptive_reflow/algorithm/blender/blender.py`；`adaptive_reflow/algorithm/nfe_allocation.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-21 是否越级推出目标分布或 FID 改善？

- 类别/优先级：理论 / P0
- 状态：VERIFIED
- 验收：分开固定点收敛、状态误差、特征分布距离；未建立的桥梁不写成定理推论。
- 发现：加入目标正态且速度场精确为零的耦合反例，以及错误时间导致方差偏离的反例；状态收缩不推出目标保持、W2不推出FID符号。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/gap92-kappa-bridge.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-22 κ诊断与理论 Lipschitz 收缩因子是否混称？

- 类别/优先级：理论 / P1
- 状态：VERIFIED
- 验收：核对 κ 的计算定义、数据依赖、预算/调度臂和样本数；不得把经验协方差比等同于mK或因果规律。
- 发现：经验κ仍为指定样本协方差比，不作Lipschitz估计、因果解释或跨家族性能预测器；理论未给可用全局L/误差上界。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`；`tools/gap78_observable_screen.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-23 收益来自重启还是求解器、初值、额外计算？

- 类别/优先级：比较公平性 / P0
- 状态：VERIFIED
- 验收：各臂列相同/变化因素；把solver、初始化、表示桥接、反馈、预算分离；不能归因的结果限缩解释。
- 发现：CIFAR五臂包含Euler、完整配置、零时间候选、VE-Heun与原Restart适配，匹配模型调用；求解器和时间网格对照仍不意味着原EDM模型最佳结果重现，完整配置迁移的差异不单独归因重启。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/PAPER-EVIDENCE.md`；`paper-data`；`adaptive_reflow/adapters`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-24 是否拼接不同N、seed、checkpoint和evaluator？

- 类别/优先级：比较公平性 / P1
- 状态：EVIDENCE_GAP
- 验收：建立逐单元协议表；异协议/历史端点分列；每个数值及其统计都来自兼容的artifact。
- 发现：新研究全部逐单元锁定N、seed、参考、特征与实际调用；不同阶段不合并种子，不跨TF-port/torchvision/projection绝对比较。历史部分任务仍缺兼容的完整质量—成本网格，不能由新增CIFAR补填。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：为历史每个数值补协议兼容性键；无法确认特征/参考/比较臂一致的格子保留分列，不补造完整网格。
- 证据：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap90-optsteps-dose.md`；`paper-data`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-25 等 NFE 是否被写成等耗时或加速？

- 类别/优先级：比较公平性 / P1
- 状态：VERIFIED
- 验收：单独报告辅助评价和状态转换开销；实际时间只在同设备同实现下比较；外推加速不写成实测。
- 发现：逐单元保留外层作业耗时并保守计GPU预算；同NFE不写等耗时，CPU评价与画像计入范围单独说明，没有实测跨实现加速结论。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-26 独立运行次数、记录数和家族数是否混淆？

- 类别/优先级：统计 / P0
- 状态：EVIDENCE_LOCATED
- 验收：每个CI/p/效应量写统计单位；pooled记录不替代种子重复，合成变体不替代独立结构。
- 发现：新增推断以整次生成运行的三个种子为单位；质心平移使批内图像相关，主KID限定固定N有限批得分，另以独立种子批对做探索性核诊断。历史家族/合成记录的独立性仍有限。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：逐历史CI/p注明种子、模板与家族单位；在缺原始簇信息的条目停止作独立样本确认解释。
- 证据：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-27 Kanzi 索引匹配是否错误当作天然配对？

- 类别/优先级：统计 / P0
- 状态：VERIFIED
- 验收：追踪实际样本生成和相关性、检验实现及源均值；核对独立样本分析与dz命名，按正确单位重述；不预先认定旧检验正确。
- 发现：从0d070700恢复被9c28d52f删除的原baseline，SHA256 be03a0a9…，1000键完全匹配，均值及旧p=.001794精确复现。新增Welch p=.002254、CI[-.031124,-.006804]Å，七R级家族校正p=.01578。两臂测不同来源结构，索引差值不称同输入配对，dz只标历史。验证范围为来源、统计重算与正确解释；不认定天然总体因果获益。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-28 三种子自举与家族相关性是否充分披露？

- 类别/优先级：统计 / P1
- 状态：EVIDENCE_LOCATED
- 验收：写明有限种子自举分辨率/区间局限、聚类单位与已有敏感性分析；不靠追加种子自动过关。
- 发现：新增三运行t(df=2)及名义区间明确依赖分布假设；补充精确符号翻转敏感性，三个配对最小双侧p=.25，不能据极小参数p声称稳健非参数确认。历史簇相关问题不因新研究解决。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留t假设与符号翻转分辨率；更广训练重复应服务外部有效性，不为通过显著性而补种子。
- 证据：`docs/audit/gap84-inference-frontier.md`；`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-29 多重比较和效应阈值是否一致？

- 类别/优先级：统计 / P1
- 状态：REVISION_NEEDED
- 验收：定义检验家族、选择规则、校正次数、效应量和区间；区分探索与确认，缺失区间不补写。
- 发现：五臂研究四个面积比较Holm校正，两轮留出阶段另为两个比较；单比较内四成本Bonferroni用于前沿核查。名义t区间不是同时区间，没有研究间整体FWER保证；历史探索性拟合及选择后比较仍需保持探索标签。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：最终逐表核验预定/探索家族和区间覆盖范围，旧拟合/筛选项保持探索标签，不能补写不存在的确认区间。
- 证据：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap84-inference-frontier.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-30 projection-FID 与标准 FID 是否混淆？

- 类别/优先级：指标 / P1
- 状态：VERIFIED
- 验收：追踪特征提取器、投影、参考集、样本量、随机种子与实现；不跨特征空间比较绝对值。
- 发现：保留MNIST投影FID/KID名称，CIFAR统一TF-port Inception2048及同一10000测试参考；主KID不缩放，FID辅助。初始real-real FID门槛失败不删除、不作分数相减修正。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`adaptive_reflow/adapters/mnist_fm.py`；`adaptive_reflow/eval`；`docs/audit/gap84-inference-frontier.md`；`adaptive_reflow/eval/mnist_fid.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-31 蛋白代理指标能否代表结构/功能/家族覆盖？

- 类别/优先级：指标 / P1
- 状态：VERIFIED
- 验收：逐项解释pLDDT、scPerplexity、HMMER与家族身份，明确其能与不能支持的结论。
- 发现：v4新增指标—源码—原始来源表：scPPL为ESM-IF非padding token平均交叉熵指数，pLDDT为OmegaFold Cα置信度均值，HMMER/Pfam家族、MMseqs2参考库新颖性分别解释；不推成实验功能/天然误差。验证范围为定义和引文，历史版本完整性见SC39。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap79-r1-family-lever.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-32 合成重建与分子有效性定义是否准确？

- 类别/优先级：指标 / P1
- 状态：EVIDENCE_GAP
- 验收：核对坐标来源、单位、对齐、几何桥接、PoseBusters与RDKit的区别及逐记录存储完整性。
- 发现：进一步追踪R3实际compute_all_paper_metrics：默认尝试PB YAML注入，非另一helper的xtb重评；降级路径存在，旧汇总未存成功检查集合和逐分子verdict。v4明确该限制，不宣称原论文PB设置完全复现。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：对历史分子/结构任务核对逐样本坐标、对齐、几何重建及有效性定义，缺原始数据的范围明确保持缺口。
- 证据：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/audit/gap39-flowmol3-real-restart-blend.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-33 质量提升是否伴随新颖性/多样性损失？

- 类别/优先级：指标 / P1
- 状态：VERIFIED
- 验收：公开K7负结果及参考数据库/阈值；将质量、自一致性、覆盖和新颖性分开，不主张同步改善。
- 发现：已在主文保留K7新颖性46.6%→3.7%的不利读数及数据库/阈值范围；未宣称所有质量轴同步提升。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap70-lineageflow-position-blend.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-34 哪些组件真的必要？

- 类别/优先级：消融与机制 / P0
- 状态：VERIFIED
- 验收：盘点已有无反馈、固定混合、自适应控制、完整方法对照；相同协议才可拼成因果消融，不存在的格子标缺失。
- 发现：主参数单因素对照显示部分作用反向；五臂迁移和新两轮候选是完整配置比较，不冒充逐组件因果消融。组件必要性仍仅限已测检查点与协议。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`adaptive_reflow/algorithm/policy_driver.py`；`docs/ABLATION.md`；`docs/audit/gap90-optsteps-dose.md`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-35 round数、beta、预算分配的解释是否被已有记录反驳？

- 类别/优先级：消融与机制 / P1
- 状态：VERIFIED
- 验收：检查GAP-84/90/93和各适配器真实路径；保留已证伪杠杆和不显著结果，不重复提出已做实验。
- 发现：从39个既有summary重算production的β和轮数敏感性，并纳入v4：β=.5平台未测，β=.7变差；R≥4的evidence臂跨度.0346。轮数联动beta/分配，不归因纯迭代；只验证这两组既有扫描及范围，不是所有任务的全参数规律。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`todo.json`；`docs/audit/gap90-optsteps-dose.md`；`docs/ABLATION.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-36 残差修正解释是否被误当成机制证明？

- 类别/优先级：消融与机制 / P1
- 状态：VERIFIED
- 验收：把直接观测、解释与未知分开；源码只证明执行机制，不能单独证明质量变化的因果机制。
- 发现：将路径恒等式、实现、反例和质量观测分别表述；不从源码、状态收缩、误差界或κ诊断推断残差修正的质量机制。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-37 图表是否完整且可供判断？

- 类别/优先级：呈现与复现 / P2
- 状态：VERIFIED
- 验收：方法图、可执行算法、逐任务协议表、主曲线不确定性、案例和完整状态表；图注自解释且可回溯源数据。
- 发现：新增四项匹配调用差值曲线、五臂预定索引与独立候选图，完整表格保留全部成本与种子范围；图轴、区间与选择规则注明，最终Word图表另做原生核查。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/drafts/paper-A-final.md`；`tnnls_submission/figures.md`；`tnnls_submission/tables.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-38 文字是否像审计报告、反复重复限制？

- 类别/优先级：呈现与复现 / P2
- 状态：VERIFIED
- 验收：每节先写发现与意义再限定范围；重复caveat集中到必要位置，wave/内部路径/开发历史移到补充。
- 发现：正文按问题与结果组织，将历史跨域记录及旧参数敏感性移附录，执行来源放内部索引；限制集中讨论，避免以审计叙事代替科学论证。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/gap96-manuscript-compression.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-39 参考文献和上游归属是否完整？

- 类别/优先级：呈现与复现 / P2
- 状态：REVISION_NEEDED
- 验收：补齐直接相关原始文献、模型/数据/指标版本，逐条验证论断；不追求任意引用数量。
- 发现：新增流匹配路径、随机插值、Diamond Maps、NR-SMC及Coupled Guidance/ReCouple原始文献与具体关联定位，共26条；旧模型/数据库的精确版本及正式出版格式仍需最后核验，引用数量不作为验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：逐项补精确模型/数据库版本和正式出版信息，投稿前按目标期刊格式核对；已验证原始文献不反复检索凑引用数。
- 证据：`docs/drafts/paper-A-final.md`；`tnnls_submission/data_availability.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-40 审计可复现是否被当成科学正确性？

- 类别/优先级：呈现与复现 / P2
- 状态：VERIFIED
- 验收：区分hash完整性、重放范围、实验有效性；补充精确命令环境、独立clone检查和匿名发布材料。
- 发现：完整保留协议、失败资源门槛、时限修订、来源摘要与逐分数核见证；全部主分数可复算，指定完整特征可CPU重算，其余大样本留服务器并列摘要。复现层级不等于科学正确性或所有历史模型重生成。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 证据：`reproduce`；`paper-data`；`docs/environments.md`；`tools/check_clone_integrity.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/thread_environment_check.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-41 第一轮：主张与贡献是否锁定？

- 类别/优先级：三轮执行计划 / P0
- 状态：REVISION_NEEDED
- 验收：完成SC-02/03/04/07/12，交付一句中心主张、三贡献与证据映射，再进行大段重写。
- 发现：当前中心问题与实例已锁定，但前置SC-04的独有创新尚未建立；撤回此前整项VERIFIED，不能以完成写作组织代替原创性验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：以SC-04/05的实质创新判断重新验收贡献锁定，完成写作组织不能使本项恢复整项通过。
- 证据：`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-42 第二轮：方法、相关工作、主结果是否重写到位？

- 类别/优先级：三轮执行计划 / P1
- 状态：REVISION_NEEDED
- 验收：围绕已核实证据扩写并同步协议、图表和引文；不以背景和工程功能凑篇幅。
- 发现：v6按路径条件、原Restart控制与独立验证重写方法/理论/主结果，附录保留历史记录；原创性和正式英文投稿编排尚未完成，不把本轮扩充等同可投最终稿。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：先完成创新定位决策和证据映射，再安排英文模板与投稿材料，中文v6作为研究稿保存。
- 证据：`docs/audit/gap96-manuscript-compression.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-43 第三轮：是否按拒稿理由复查？

- 类别/优先级：三轮执行计划 / P1
- 状态：EVIDENCE_LOCATED
- 验收：对创新、理论、比较、指标、统计逐项验收；每个残留新实验建议注明解决的问题与是否已有证据。
- 发现：本轮按创新重合、训练耦合、最接近控制、批相关KID及三种子推断逐项复查；残余拒稿风险已列优先计划，没有安排超预算实验或把工程门禁当录用标准。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：用本轮真实正负结果逐项复查五类拒稿风险；只在新的研究问题可辨且资源明确时启动后续验证。
- 证据：`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-44 TNNLS是否仍是合理首投？

- 类别/优先级：投稿决策 / P1
- 状态：EVIDENCE_LOCATED
- 验收：P0复核后重评目标，区分大类/小类/分区年份；主题匹配不等于已证明达到录用标准。
- 发现：TNNLS仅保留主题方向候选；此前主观录用概率与旧分区/影响因子不再作当前判断。官方已宣布2026起不再更新分区表，应按2025历史版本、大类/小类及用户单位认定规则复核；本轮官网作者页面抓取受限，不能宣称2026最新全文已验收。当前不足以称硬一区稿。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：在核心科学缺口解决后，核对2025历史中科院大类/小类、单位适用规则及可获得的最新官网作者须知，再决定首投；不沿用旧录用概率。
- 证据：`docs/audit/gap94-standard-benchmark.md`；`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

### SC-45 是否完整记录全部上一轮审稿建议并同步源码？

- 类别/优先级：记录与同步 / P0
- 状态：VERIFIED
- 验收：保存本表和JSON、注册todo入口、更新audit索引；提交并推送服务器现有源码/记录历史后，从GitHub获取本地正式副本并核对HEAD。
- 发现：科学源码与证据提交5edbd6c5d701f6764e91c134662e2ca8fb7b44ae已从服务器推送GitHub并由Mac正式clone快进拉取；本地核对126个发布文件摘要、78个主分数及运行间统计、5个指定完整特征FID/KID。45项及历史全部保留。本项验收的是该科学提交的同步与限定复算，不表示所有历史模型在Mac重生成或整稿可投。记录闭环提交的最终HEAD另见Mac交付收据。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 下一步：保留本轮同步与复算回执；后续源码/证据改动须再次核对来源与Mac副本。
- 证据：`todo.json`；`docs/audit/INDEX.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round5-2026-11-03/MAC_REPLAY.json`
