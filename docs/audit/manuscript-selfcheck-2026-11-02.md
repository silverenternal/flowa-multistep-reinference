# 投稿改进自查表 2026年11月2日

完整保留45项及各轮历史。第十轮补充中文v9真实中间路径与边界干预；VERIFIED仅表示条目限定范围，原创性与独立有效性仍按具体缺口记录。

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

## 历轮重要更正

- 前两轮中文稿与评议遗漏GAP-90/91/92既有记录，不能继续声称项目只有未经受控解释的四检查点横截面。
- 既有GAP-90记录六检查点、受控数据/epoch剂量及宽度对照，但严格单调假设和跨家族预测要求仍须按预注册结果解释。
- 源码可确定实现、启用路径和指标定义；新颖性、因果效力、外部有效性与期刊接受度不能仅凭源码判定。
- 第二轮从Git历史恢复首轮未找到的Kanzi原baseline，首轮“来源缺失”是当时检索范围的状态，不再沿用为永久缺失。
- 既有GAP76为实际组件干预，已从原样本复算；参数不同于主前沿，不能拼接。
- live评价器不等同于匹配生成器对照；R6随机序列基线与门控限制已进入v3。
- 第三轮纠正前稿“每轮至少两步”：legacy命名min_steps_per_round仅限制总轮数，实际权重分配可有一步轮次。
- 第三轮定位旧GAP93的−.3648为百分比，绝对指标差为−.0364203；β=.5的高预算平台没有测。
- 原LineageFlow已提出rerouting，新增为直接相关工作；Kanzi书目按Dilip等原文，不沿用旧JSON的Shah标签。
- 第四轮主参数匹配消融显示质心保持与零时间重启的作用随检查点反向，不能沿用β=.5局部结果推定β=.3组件必要性。
- 独立CIFAR TF-port与旧torchvision特征缓存不兼容；N1000 real-real FID32.0719，初始<10门槛未校准且没有通过。
- 弱检查点projection-FID降低但探索性projection-KID上升；图像仍有明显形态缺陷，不能称全面感知质量改善。
- 第五轮原始Restart函数的RF接口匹配对照已完成；不能再写完全没有最近方法对照。
- Diamond Maps与NR-SMC存在直接相关端点构造，不主张端点混合首次性。
- 独立插值路径的理想目标保持不适用于任意训练耦合，收缩到错误分布的反例已进入正文。
- 完整配置的批次质心处理耦合图像，标准iid KID无偏性不能直接套用；三个种子的参数p值另配符号翻转分辨率说明。
- 撤回SC-41整项VERIFIED：原创性前置项尚未完成；此前主观录用概率不作当前预测。
- 第六轮将高斯特例推广为凸梯度路径的Bregman缺口及W2下界候选；小非梯度误差可翻转符号，不能将强单调或接近OT当作充分假设。原创性仍待逐证明查新。
- 第六轮二次审查：矩缺口等于t(1−t)乘输运成本差；最优路径下非负性是经典OT最优性，障碍命题降级为机制引理，不包装为主要原创贡献。
- 第八轮已开始完整中文正文写作，新增解析与缓存结果不等于新增独立模型验证；写作完成与原创性、期刊格式验收分别记录。

- 第九轮直接读取现行TNNLS官网：双匿名、常规超过10页每页200美元且正文总长最多15页；旧2012年13页口径为历史规则。解析路径控制已补充，实际神经流中间边缘与独立干预仍未完成。

- 第十轮完成真实CIFAR检查点中间轨迹和固定后段边界干预：原噪声弦线逐样本更近但整体边缘更远；不据一般耦合反例判定独立刷新有害。含失败重跑保守GPU总核算7158/7200秒。

## 完整条目

### SC-01 当前中文稿是否具备完整投稿稿的论证密度？

- 类别：篇幅与定位
- 优先级：P0
- 状态：REVISION_NEEDED
- 验收：按正文、方法、协议、结果和文献逐节核算，区分中文页数与英文双栏；不以扩写背景凑页。
- 发现：中文v7形成完整机制与边界分析稿，约1.9万汉字、8图、18张编号结果表及1张算法表；旧18个Markdown表格逐字保留，新增有限端点诊断表。中文论证密度已扩充；正式英文双栏篇幅仍须另行验收。
- 下一步：在科学主张稳定后按目标期刊英文模板编排，核对正文/附录页数及图表密度；不按中文Word页数推算英文合规。
- 验证范围：本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。
- 核查轮次：round8-2026-11-03
- 本轮记录：docs/audit/manuscript-rewrite-round8-2026-11-03.md
- 证据：`docs/audit/gap96-manuscript-compression.md`；`docs/drafts/paper-A-final.tex`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "新版按证据扩充方法、六检查点、统计与诊断；正式英文双栏页数尚未编排，不能按中文页数验收。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "REVISION_NEEDED", "finding": "正文围绕路径条件、组件和独立图像对照重写，历史跨域与参数资料移入附录；中文稿的实际字数、表图数另列验收。正式英文双栏与期刊页数尚未编排。", "next_action": "在科学主张稳定后按目标期刊英文模板编排，核对正文/附录页数及图表密度；不按中文Word页数推算英文合规。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "verification_scope": "仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。"}

### SC-02 中心主张是否可用一句话表述且被证据覆盖？

- 类别：篇幅与定位
- 优先级：P0
- 状态：VERIFIED
- 验收：记录一句中心主张、三项贡献及各自最强证据；所有超出证据范围的词单列。
- 发现：中心问题锁定为：冻结流模型的端点再推理何时保持目标，以及有限计算下的收益为何受到路径、组件和评价对象限制。摘要、三项分析贡献、条件证明、正负结果和结论按该问题组织。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。
- 核查轮次：round8-2026-11-03
- 本轮记录：docs/audit/manuscript-rewrite-round8-2026-11-03.md
- 证据：`docs/PAPER-EVIDENCE.md`；`todo.json`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "新版引言给出单句问题、三层贡献及证据范围；验证范围为稿件组织，不代表创新性获得外部认可。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "VERIFIED", "finding": "中心问题收窄为端点再推理的路径条件、组件作用与独立适用性；完整配置不具备普遍质量保证，所有定量结论来自锁定研究。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "verification_scope": "仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。"}

### SC-03 是方法论文还是软件框架论文？

- 类别：篇幅与定位
- 优先级：P0
- 状态：VERIFIED
- 验收：明确主定位及次贡献；章节和实验围绕同一定位，不用工程接口代替方法新意。
- 发现：主定位为明确边界核的机制与适用边界分析；工程接口用于复现。正文不将经典OT恒等式或既有重启操作作为独有方法贡献，原创充分性仍由SC-04/05单独记录。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。
- 核查轮次：round8-2026-11-03
- 本轮记录：docs/audit/manuscript-rewrite-round8-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`docs/STRATEGY_FRAMEWORK_SCOPE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "定位为明确算法实例及其检查点条件性实证，框架接口降为复用实现；不以接口数量替代方法贡献。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "VERIFIED", "finding": "当前主定位为指定边界核的条件分析和受控实证，接口工程为复现支持。能否形成足够原创的一区方法贡献仍属SC-04/05缺口。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "verification_scope": "仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。"}

### SC-04 是否仅为已有 restart sampling 加接口封装？

- 类别：创新性
- 优先级：P0
- 状态：EVIDENCE_GAP
- 验收：与最接近原始论文逐项比较状态、反馈、训练需求、预算、重启方式；不能凭源码存在判定新颖性。
- 发现：已补一个真实CIFAR检查点的中间轨迹与受控边界替换，36个干预单元完整。主时刻原噪声弦线虽更贴近单轨迹，却比独立噪声弦线更偏离中间及接续边缘；三种子、两精度和三带宽方向一致。新增的是对象区分和诊断证据，CMM/CorrFlow已覆盖边缘匹配或部署分布议题；没有新采样器，原创充分性仍未验收。
- 下一步：冻结本轮诊断作为机制证据；下一阶段先明确超出CMM/已有重启方法的可证伪预测，再考虑独立模型和匹配总调用的动作验证。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/gap94-standard-benchmark.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`docs/audit/manuscript-endpoint-pairing-round7-2026-11-03.md`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "已核对Restart、FM/RF、DPM-Solver与一致性模型原始来源并增加比较表；同协议最接近方法数值对照仍缺。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "已补原Restart算法B.2与LineageFlow rerouting具体差异及原始引文；当前源码/记录中没有同检查点、同调用次数/评价器的匹配对照。操作差异不作为优越性证明。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}
- {"status": "EVIDENCE_GAP", "finding": "已补同RF权重、实际调用匹配的原始Restart函数与VE-Heun控制；Diamond Maps端点特例及NR-SMC状态更新存在直接重合，不能再把端点混合作为独有操作。完整系统的奖励/后验目标没有对照，原创贡献仍未充分建立。", "next_action": "先列与Diamond Maps/NR-SMC/Restart逐操作及目标的差异；若没有独立且有价值的可检验主张，改为条件分析定位，暂缓按新采样方法投稿。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "EVIDENCE_GAP", "finding": "已排除首次重启/端点混合/双端点修正/MMD引导等重合。新增证明及100个CPU检查完成后，发现矩缺口恰为经典输运成本差，核心障碍命题降为背景机制引理，不作为主要原创贡献。锐下界和近似路径反例仍有直接经典推论风险；原创问题未解决。", "next_action": "追溯OT重排/Bregman差额和边缘保持理论；若已直接覆盖则降为引理；寻找可估计判别量及独立干预。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md"}
- {"status": "EVIDENCE_GAP", "finding": "第七轮在12个既有CIFAR操作点各取固定256对端点，未发现有限循环单调性违例；不能确认全局凸梯度或预测质量。小批配对优化和有限单调性已有直接文献，诊断不作为新方法。核心原创性缺口仍在。", "next_action": "先获取/验证实际中间边缘的可观测诊断；只有区分路径弯曲与配对改变并超出已有方法后才考虑独立干预。", "review_round": "round7-2026-11-03", "review_record": "docs/audit/manuscript-endpoint-pairing-round7-2026-11-03.md", "verification_scope": "本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。"}
- {"status": "EVIDENCE_GAP", "finding": "新增相同端点映射与联合分布、不同刷新输出的光滑流构造，36个CPU控制验证端点诊断不能替代真实中间边缘。路径自由度和Lipschitz传播已有经典基础；针对指定刷新核的构造未被确认为足够独立的新颖贡献。原有操作重合不变，原创充分性仍缺证据。", "next_action": "先获取/验证实际中间边缘的可观测诊断；只有区分路径弯曲与配对改变并超出已有方法后才考虑独立干预。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-05 相比固定权重混合究竟新增什么？

- 类别：创新性
- 优先级：P0
- 状态：EVIDENCE_GAP
- 验收：给出唯一可辨的算法差异、代码路径和对应对照；不用多个功能同时变化的比较归因。
- 发现：本轮已完成同后段网格的真实边界状态干预，尚非前瞻诊断选择或独立模型预测验证；独立臂接近有限样本参照不能证明目标保持。未得到匹配总调用的质量收益或新部署决策，独有方法贡献仍缺证据。
- 下一步：只有在独立检查点上预先锁定诊断到动作的规则，并取得匹配总调用的实际质量证据后，再评估方法贡献；本轮不再新增GPU。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/blender/blender.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "源码确认主配置包含partial-time restart与batch质心平移；缺同协议逐组件归因，不能宣称自适应反馈独立贡献。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "已补质心组件的局部隔离，但固定混合、重启时间、调度与质心在主前沿βtot=.3下的同协议完整矩阵仍缺，无法从源码认定新增组件各自必要。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "已完成主参数β=.3、两检查点×三种子×六臂、C200匹配组件矩阵；均匀预算差异远小于1单位，无法支持原调度的实用必要性。 该矩阵削弱组件必要性主张，未给出超越最接近方法的唯一创新性证据；创新性验收仍未闭合。", "review_round": "round4-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round4-2026-11-03.md", "next_action": "继续检验其余检查点/多预算与交互；本项只验收局部组件对照，不验收新颖性或普适必要性。"}
- {"status": "EVIDENCE_GAP", "finding": "主参数组件矩阵与独立零时间简化配置区分组件；后段时间匹配两轮候选另行留出验证。操作差异及经典误差界不足以证明相对固定混合/先前端点构造的新颖性。", "next_action": "以已有单因素矩阵判断哪些差异真实影响结果；仅对可识别的新差异设计最小控制，不把路径一致修正本身当新算子。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "EVIDENCE_GAP", "finding": "固定调度本身的新颖性仍不足。本轮贡献候选转向训练耦合决定刷新合法性的机制分析，不再以增加混合权重或接口作为创新。", "next_action": "理论差异通过后才锁定实用修正；同等调用收益和新模型验证仍未完成。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md", "verification_scope": "本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。"}
- {"status": "EVIDENCE_GAP", "finding": "当前新增的是可检验的端点不可识别性分析，不是新的端点混合算法。无新神经模型干预或迁移收益，不能以控制数量替代独有方法证据。", "next_action": "理论差异通过后才锁定实用修正；同等调用收益和新模型验证仍未完成。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-06 首次性、普适性、全面占优是否有依据？

- 类别：创新性
- 优先级：P0
- 状态：VERIFIED
- 验收：逐词检查标题摘要贡献；不能证实的首次、普适、SOTA或全面优势删除或收窄。
- 发现：题目、摘要和结论按实际结果写条件与适用性，删除首次/普适/全面优势；同一检查点新生成种子不称新模型确认。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "新版标题、摘要和结论不作首次、普适质量或普遍加速主张；结果限定到检查点与具体配置。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-07 FlowA 主方法是否是确定且可复现的算法？

- 类别：方法定义
- 优先级：P0
- 状态：VERIFIED
- 验收：锁定主方法实例，完整定义状态、反馈、调度、混合、停止和预算；可选框架配置另列。
- 发现：明确MNIST四轮配置、CIFAR移植、四轮零时间候选和两轮物理时间一致候选；预算、状态、时间、全批质心处理和随机政策分别记录，候选不替换原主配置。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/policy_driver.py`；`adaptive_reflow/algorithm/scheduler/evidence_driven.py`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": "scripts/wave191_p3_mnist_sweep.py:473-651 定义主实验 run_framework_arm；memory模式在后续轮次从 t_start=1-beta_r 积分至1；mean_preserve模式以首轮终点样本均值平移最终样本。中文稿的固定完整流映射是简化表达，需按该实例补齐时间区间和batch级操作。"}
- {"status": "VERIFIED", "finding": "新版III-A至E明确首轮、fresh prior、累计beta、实际轮数、部分区间RK4与最终batch质心平移，配可执行步骤表。仅核实定义。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "纠正前稿每轮至少两步的误述：h=2只控制有效轮数R≤S//h，权重分配仍允许Sk=1。v4方法和算法表同步，驱动docstring/help修正；实际算法、参数与历史样本未改。验证范围为操作定义。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}

### SC-08 反馈究竟读取什么信息？

- 类别：方法定义
- 优先级：P0
- 状态：VERIFIED
- 验收：列出评价/标签/参考数据是否参与控制、调用时机和成本，区分事后评价与在线控制。
- 发现：CIFAR五臂和两轮候选均不以测试参考作在线控制，固定调度；参考仅用于事后特征评分。不能将预定调度描述为自适应质量反馈。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`adaptive_reflow/algorithm/evidence_driver.py`；`adaptive_reflow/algorithm/runner/runner.py`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": "scripts/wave191_p3_mnist_sweep.py:334-386 的调度预算在生成前通过 sched.sample 计算；该文件没有 record_round_feedback 调用。不能从 EvidenceDriven 名称推断此实验启用了在线PID反馈；仍需与通用 runner 的反馈路径和具体运行参数区分。"}
- {"status": "VERIFIED", "finding": "主MNIST驱动预先取scheduler权重且无record_round_feedback调用；新稿不声称已启用在线PID。通用runner能力另列。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-09 连续、离散、掩码和图通道的操作是否合法？

- 类别：方法定义
- 优先级：P0
- 状态：EVIDENCE_LOCATED
- 验收：逐通道核对状态域、先验、尺度、混合和验证，明确线性理论仅适用的范围。
- 发现：已区分连续线性实例与跨域通道适配；尚未逐个核完离散/图通道的实际headline路径。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：逐个离散/图通道检查先验、合法域和混合执行路径；未满足连续理论的任务仅保留集成范围。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`adaptive_reflow/algorithm/blender/per_channel_blender.py`；`adaptive_reflow/adapters`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "已区分连续线性实例与跨域通道适配；尚未逐个核完离散/图通道的实际headline路径。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-10 实际调用次数是否等于宣称预算？

- 类别：方法定义
- 优先级：P0
- 状态：VERIFIED
- 验收：核对求解器每步调用、round floor、取整和不可执行设置；报告真实 NFE 而非仅配置步数。
- 发现：MNIST的RK4成本C=4S；CIFAR逐臂计数匹配25/49/99/199实际速度场调用。Restart原函数计数与Heun控制单独测试，两轮分配C99=[76,23]、C199=[153,46]。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`adaptive_reflow/algorithm/nfe_allocation.py`；`adaptive_reflow/algorithm/solver.py`；`docs/audit/gap90-optsteps-dose.md`；`scripts/wave191_p3_mnist_sweep.py`；`adaptive_reflow/adapters/mnist_fm.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": "scripts/wave191_p3_mnist_sweep.py:537 将 num_steps_per_round 求和记为 total_nfe；adaptive_reflow/adapters/mnist_fm.py:276-279 与309-312的RK4实现每步含四次速度场评价。已定位步数与函数评估数的口径风险，需继续核对实际backend与artifact，不预先判定整条比较不公平。"}
- {"status": "VERIFIED", "finding": "NumPy和Torch的实际积分循环均每步四次速度场调用。新图以C=4S标轴；原始JSON的nfe键不改写。等RK4步数仍为等调用次数。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-11 四接口与算法步骤、伪代码是否一一对应？

- 类别：方法定义
- 优先级：P1
- 状态：VERIFIED
- 验收：画方法图并给出可复现伪代码；接口只解释职责，指出真实调用实现和旁路。
- 发现：III-E伪代码、III-F接口与实际驱动区分，明确预先调度、restart与batch后处理；不以通用runner替代实际实验路径。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`adaptive_reflow/algorithm/runner/runner.py`；`adaptive_reflow/algorithm/runner/sequential.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "III-E伪代码、III-F接口与实际驱动区分，明确预先调度、restart与batch后处理；不以通用runner替代实际实验路径。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-12 各任务是否验证同一个机制？

- 类别：贡献与证据
- 优先级：P0
- 状态：VERIFIED
- 验收：建立贡献→组件→实际比较臂→artifact 对应表；只验证集成的任务不得当作算法优势。
- 发现：正文仅以MNIST及独立CIFAR检验指定连续边界核；R1/R6随机序列与R2不同来源结构记录移附录，当前证据等级降为PARTIAL，历史记录保留。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/PAPER-EVIDENCE.md`；`docs/paper-evidence.json`；`paper-data`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "已按任务/臂分层呈现；尚未把所有跨域路径核到足以证明同一机制，跨域不再作为统一组件因果证据。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "v3表A建立组件→实际比较臂→证据范围。Kanzi是不同来源结构的自编码往返；R6随机序列基线及低预算门控不支持同机制跨域验证；FlowMol3历史坐标扰动与GAP39全通道prior混合分列。验证范围为映射与稿件表述。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md", "next_action": "按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。"}

### SC-13 各实验到底有没有真实多轮重启？

- 类别：贡献与证据
- 优先级：P0
- 状态：EVIDENCE_LOCATED
- 验收：逐格追踪实际启用的调度、restart、反馈与 no-op 路径；单轮不能证明多轮迭代价值。
- 发现：MNIST端点多轮、Kanzi单次rollout、FlowMol3历史及GAP39一次solve已追踪。R6三份清单nfe10<门槛20，源码915行降一轮；历史清单未存生成提交/加载模式，不能据请求三轮当作实际三轮。其余扩展单元仍逐格保留核对。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：按每任务实际配置与日志记录有效轮数、门槛和no-op；没有完整生成日志的格子维持未验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap80-r5a-harness.md`；`docs/audit/gap95-frontier-grids.md`；`docs/PAPER-EVIDENCE.md`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": "MNIST驱动的run_framework_arm真实调用restart操作；同时调度步数提前生成、末端可有mean-preserve平移。需要分别标注重启、在线反馈、预算调度和batch平移是否启用，不能合称一个已验证组件。"}
- {"status": "EVIDENCE_LOCATED", "finding": "MNIST真实restart已核实且单轮不能证明多轮价值；其他headline任务的逐路径核查尚未全部闭合。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_LOCATED", "finding": "MNIST端点多轮、Kanzi单次rollout、FlowMol3历史及GAP39一次solve已追踪。R6三份清单nfe10<门槛20，源码915行降一轮；历史清单未存生成提交/加载模式，不能据请求三轮当作实际三轮。其余扩展单元仍逐格保留核对。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md", "next_action": "按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。"}

### SC-14 已有但未写入中文稿的证据有哪些？

- 类别：贡献与证据
- 优先级：P0
- 状态：VERIFIED
- 验收：纳入 GAP-90 六检查点、GAP-91 描述性拟合、GAP-92 κ诊断及 GAP-93剂量记录；明确其有限结论，不重跑已有实验。
- 发现：中文v9新增V-I、VI-L、图10与表XV，纳入真实中间路径而非只复用端点缓存；保留原20个表格对象、9图与全部旧数值，仅随新增文献重排引用。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/audit/gap92-kappa-bridge.md`；`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": ""}
- {"status": "VERIFIED", "finding": "新稿加入GAP-90六点/受控轴、GAP-91插值与修正区间、GAP-92κ诊断，并保留已有预注册失败和边界。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "VERIFIED", "finding": "新稿加入GAP-90六点/受控轴、GAP-91插值与修正区间、GAP-92κ诊断，并保留已有预注册失败和边界。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "verification_scope": "仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。"}
- {"status": "VERIFIED", "finding": "第六轮凸梯度路径下的矩缺口、条件W2下界、SPD迹恒等式与近似路径反例已进入IV-D至F；100个CPU案例和第七轮12单元端点诊断已进入V-G、VI-I/J及讨论。数值结果及范围与原记录一致。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round8-2026-11-03", "review_record": "docs/audit/manuscript-rewrite-round8-2026-11-03.md", "verification_scope": "本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。"}
- {"status": "VERIFIED", "finding": "中文v8新增IV-G的光滑流构造与双侧W2界、V-H协议、VI-K结果、图9和表XIV；旧19个表格对象保留，仅重排文献标签，原科学数据不变。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-15 优势集中一个 MNIST 检查点意味着什么？

- 类别：主结果
- 优先级：P0
- 状态：VERIFIED
- 验收：完整报告六检查点/受控轴及历史四检查点关系、平台、局部损失、绝对效应；不得沿用仅四点且全部混杂的旧判断。
- 发现：完整保留六检查点一WIN五TIE及弱检查点平台−12.75%；新增独立图像研究不与投影指标合并，按其真实正负结果判断迁移。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": ""}
- {"status": "VERIFIED", "finding": "六点表与两张新图补齐；一个WIN、五个TIE按当前绝对规则报告，低预算未限制与限制版本分开。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-16 是否有第二条独立可信的实证主线？

- 类别：主结果
- 优先级：P0
- 状态：EVIDENCE_GAP
- 验收：核对 live 蛋白结果及比较臂、指标、种子/家族限制，判断能否支撑第二主结果，不凭 pooled n 决定。
- 发现：已建立独立CIFAR同模型、同特征、匹配调用的可信验证；是否产生正向结果按预定分析报告，不能把负向验证、两个预算点候选或同权重新种子包装成第二条完整正向前沿。尚无新训练重复。
- 下一步：优先根据现有独立研究判定是否值得继续候选；后续需新训练检查点及完整成本网格，当前预算内不再启动GPU。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap95-frontier-grids.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "R6 live指标作为第二领域点证据纳入，不提升为完整前沿；家族/训练重复有效性仍有限。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "已追到live R6评价与生成入口：baseline为家族偏置随机抽样，framework走适配器；live指标不等于匹配模型对照。R6清单和门控也不足以证实多轮。当前不存在已闭合的第二条同机制跨家族前沿主线，正文降为描述性结果。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "新增独立CIFAR官方网络逐点一致性零误差；N1000基线TF-port FID35.5045、初始<10门槛失败，real-real校准32.0719提示门槛失当。未生成方法比较，第二家族前沿仍缺。", "review_round": "round4-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round4-2026-11-03.md", "next_action": "先锁定适合样本量的独立评价协议，再进行第二家族多预算匹配比较；不得把门槛失败改记通过。"}

### SC-17 训练充分性/检查点条件性是关联还是因果？

- 类别：主结果
- 优先级：P0
- 状态：VERIFIED
- 验收：区分固定宽度的数据剂量、固定数据的 epoch 剂量、宽度对照及未满足的严格单调条件；按预注册逐条报告。
- 发现：区分数据规模轴、epoch轴和宽度对照；数据规模和优化步数并非独立变量，严格单调假设失败公开报告。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": ""}
- {"status": "VERIFIED", "finding": "区分数据规模轴、epoch轴和宽度对照；数据规模和优化步数并非独立变量，严格单调假设失败公开报告。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-18 WIN/TIE 与显著性、实用阈值、局部退化是否混淆？

- 类别：主结果
- 优先级：P1
- 状态：VERIFIED
- 验收：明确绝对/相对阈值、区间、平台和逐档条件；TIE不写成严格等效，也不隐去低预算损失。
- 发现：原绝对WIN/TIE规则完整保留；CIFAR使用事前KID面积、家族内Holm、实用阈值与逐档前沿核查，未达到条件不等于等效。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap84-inference-frontier.md`；`docs/paper-evidence.json`；`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "新稿区分零差异、绝对效应阈值、相对规则、平台及低档局部损失；TIE不称为严格等效。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "维持WIN/TIE、区间和实用阈值区别；新增单位纠正：旧headline_mean −.3648为百分比，绝对delta_units_mean为−.0364203。不按绝对量读取旧百分比区间。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}

### SC-19 经典收缩与恒等式是否被包装成新理论？

- 类别：理论
- 优先级：P0
- 状态：VERIFIED
- 验收：明确经典工具与新增推导的边界；基础性质不单独承担创新性。
- 发现：继续明确OT、Lipschitz推前、核双样本和理想RF边缘关系的既有基础。新增查新包含CMM累计边缘目标、CorrFlow残差修正与部署分布分析，不把“关注中间状态”或经典高斯对象区分写成首次。
- 下一步：继续查新，不能将数值一致性等同于原创性。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "新稿明言经典压缩映射原理与凸组合恒等式不单独承担新的理论贡献。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "VERIFIED", "finding": "独立插值恒等式、Wasserstein耦合与偏差—收缩递推明确为基础工具；Restart已有误差/收缩竞争分析，不把重述经典性质当新理论。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "VERIFIED", "finding": "新增四个条件命题均附逐步证明，并明确凸性、Bregman恒等式和W2耦合工具为经典内容；候选组合结论与原创性验收分开。", "next_action": "继续查新，不能将数值一致性等同于原创性。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md", "verification_scope": "本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。"}
- {"status": "VERIFIED", "finding": "正文将矩缺口与经典二次输运成本差明确等价，归为机制引理并引经典OT来源；条件W2下界附Minkowski和Lipschitz推前证明，不据此宣称已通过逐证明查新。", "next_action": "继续查新，不能将数值一致性等同于原创性。", "review_round": "round8-2026-11-03", "review_record": "docs/audit/manuscript-rewrite-round8-2026-11-03.md", "verification_scope": "本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。"}
- {"status": "VERIFIED", "finding": "既有矩缺口仍标明经典OT关系；新增双侧W2界明确为标准Lipschitz推前推论。端点不可识别性为具体构造，不将一般路径自由度当作首次发现，也不以数值通过代替逐证明查新。", "next_action": "继续查新，不能将数值一致性等同于原创性。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-20 定理假设是否覆盖实际算法？

- 类别：理论
- 优先级：P0
- 状态：VERIFIED
- 验收：逐项对应固定fresh input、m、状态域、Lipschitz、精确/数值映射；变化参数或随机输入不直接套固定点结论。
- 发现：真实CIFAR数值轨迹已采集并比较两精度；原噪声弦线更近单轨迹却更偏离经验边缘，独立臂在参照附近。该结果限制凸梯度直线路径理论的直接迁移，未认证神经流凸性、精确中间边缘、逆Lipschitz界或历史质量退化原因。
- 下一步：将精确概率路径、数值轨迹边缘和训练插值严格分开；外部验证前不归因历史CIFAR退化。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`adaptive_reflow/algorithm/blender/blender.py`；`adaptive_reflow/algorithm/nfe_allocation.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "新稿限定固定输入、固定映射、状态域与数值稳定性假设；变化时间/轮数和batch平移不被套入完整收敛结论。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "VERIFIED", "finding": "独立训练耦合与正确物理时间为充分条件；逐轮不等参数的乘积—求和误差界对应数值误差，L和偏差未估计；全批质心配置不直接套理想样本核。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "VERIFIED", "finding": "新命题限定确定性强凸梯度直线路径；近似梯度路径有显式误差项，强单调性单独不足。当前CIFAR训练路径、批次平移和积分误差未被命题覆盖。", "next_action": "建立可估计假设与实际模型对应，不从合成例子外推图像因果机制。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md", "verification_scope": "本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。"}
- {"status": "VERIFIED", "finding": "新增理论写明有限二阶矩、强凸C2势、可积性、固定终点、同源边缘及0<t<1条件；非梯度反例和有限端点非认证结论与正文相邻，未将这些假设认证给神经检查点。", "next_action": "建立可估计假设与实际模型对应，不从合成例子外推图像因果机制。", "review_round": "round8-2026-11-03", "review_record": "docs/audit/manuscript-rewrite-round8-2026-11-03.md", "verification_scope": "本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。"}
- {"status": "VERIFIED", "finding": "端点不可识别性限于一般光滑可逆流族，不要求同一独立直线训练路径；已知训练概率路径时可缩小该类别。双侧界需精确后段映射及正有限正逆Lipschitz上界，未认证给CIFAR模型。", "next_action": "建立可估计假设与实际模型对应，不从合成例子外推图像因果机制。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-21 是否越级推出目标分布或 FID 改善？

- 类别：理论
- 优先级：P0
- 状态：VERIFIED
- 验收：分开固定点收敛、状态误差、特征分布距离；未建立的桥梁不写成定理推论。
- 发现：W2下界仅为分布失配，不推出FID/KID方向；100个解析检查不是质量提升或有效统计样本。
- 下一步：新增神经模型论证必须独立登记，保持原负结果。
- 验证范围：本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。
- 核查轮次：round6-2026-11-03
- 本轮记录：docs/audit/manuscript-originality-round6-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/gap92-kappa-bridge.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "状态误差、固定点、特征分布距离分开陈述，未将两条性质写成FID或目标分布保证。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "VERIFIED", "finding": "加入目标正态且速度场精确为零的耦合反例，以及错误时间导致方差偏离的反例；状态收缩不推出目标保持、W2不推出FID符号。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}

### SC-22 κ诊断与理论 Lipschitz 收缩因子是否混称？

- 类别：理论
- 优先级：P1
- 状态：VERIFIED
- 验收：核对 κ 的计算定义、数据依赖、预算/调度臂和样本数；不得把经验协方差比等同于mK或因果规律。
- 发现：经验κ仍为指定样本协方差比，不作Lipschitz估计、因果解释或跨家族性能预测器；理论未给可用全局L/误差上界。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`；`tools/gap78_observable_screen.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": "tools/gap78_observable_screen.py:111-136 以投影特征协方差迹的比值计算contraction；实现为tr_fw/(tr_ref*rho)。这是经验分布离散度诊断，不是流映射Lipschitz常数mK的直接估计。"}
- {"status": "VERIFIED", "finding": "κ源码为经验投影协方差迹比；新稿不等同mK，披露不同预算/多臂汇总以及需要框架臂样本的条件。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-23 收益来自重启还是求解器、初值、额外计算？

- 类别：比较公平性
- 优先级：P0
- 状态：VERIFIED
- 验收：各臂列相同/变化因素；把solver、初始化、表示桥接、反馈、预算分离；不能归因的结果限缩解释。
- 发现：CIFAR五臂包含Euler、完整配置、零时间候选、VE-Heun与原Restart适配，匹配模型调用；求解器和时间网格对照仍不意味着原EDM模型最佳结果重现，完整配置迁移的差异不单独归因重启。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/PAPER-EVIDENCE.md`；`paper-data`；`adaptive_reflow/adapters`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "共享先验和等RK4调用已核；完整主臂同时改变多项操作，尚缺足够控制臂来独立归因。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "REVISION_NEEDED", "finding": "v3按任务分列变化因素，Kanzi桥接/样本来源、蛋白生成器不同、FlowMol3先验扰动均不再归因于端点多轮；MNIST已复算质心隔离，但主前沿完整组件归因仍缺。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "主参数单因素矩阵识别局部干预效应：质心保持和重启起点作用随检查点反向，固定时间下取消混合效应小；不再归因于全部组件共同必要。", "review_round": "round4-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round4-2026-11-03.md", "next_action": "验证范围为局部干预效应；交互项、训练重复与速度场误差因果解释仍未识别。"}

### SC-24 是否拼接不同N、seed、checkpoint和evaluator？

- 类别：比较公平性
- 优先级：P1
- 状态：EVIDENCE_GAP
- 验收：建立逐单元协议表；异协议/历史端点分列；每个数值及其统计都来自兼容的artifact。
- 发现：新研究全部逐单元锁定N、seed、参考、特征与实际调用；不同阶段不合并种子，不跨TF-port/torchvision/projection绝对比较。历史部分任务仍缺兼容的完整质量—成本网格，不能由新增CIFAR补填。
- 下一步：为历史每个数值补协议兼容性键；无法确认特征/参考/比较臂一致的格子保留分列，不补造完整网格。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap90-optsteps-dose.md`；`paper-data`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_GAP", "finding": "发现部分summary残留beta_framework=0.5而有效beta_total=0.3，且命令为模板字符串；不改历史文件，不盲信这些字段。需逐运行重建完整manifest。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "已重建39运行的聚合来源，核对seed目录/jobs、N1000、checkpoint SHA、evaluator、累计beta/步数分配；旧summary缺seed、命令为模板、beta_framework遗留.5。生成时完整命令/源码提交仍不确定；h=2只是轮数cap，不是summary分配必须≥2，不能据名判断协议冲突。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}

### SC-25 等 NFE 是否被写成等耗时或加速？

- 类别：比较公平性
- 优先级：P1
- 状态：VERIFIED
- 验收：单独报告辅助评价和状态转换开销；实际时间只在同设备同实现下比较；外推加速不写成实测。
- 发现：逐单元保留外层作业耗时并保守计GPU预算；同NFE不写等耗时，CPU评价与画像计入范围单独说明，没有实测跨实现加速结论。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "新稿不把等NFE写成等时间；MNIST横轴换算真实调用，质量平台优势不称实测加速。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-26 独立运行次数、记录数和家族数是否混淆？

- 类别：统计
- 优先级：P0
- 状态：EVIDENCE_LOCATED
- 验收：每个CI/p/效应量写统计单位；pooled记录不替代种子重复，合成变体不替代独立结构。
- 发现：新增推断以整次生成运行的三个种子为单位；质心平移使批内图像相关，主KID限定固定N有限批得分，另以独立种子批对做探索性核诊断。历史家族/合成记录的独立性仍有限。
- 下一步：逐历史CI/p注明种子、模板与家族单位；在缺原始簇信息的条目停止作独立样本确认解释。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "新稿明确seed/record/cluster概念并不以pooled n代表独立运行；跨域原始统计独立核查仍未全部完成。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_LOCATED", "finding": "新增Kanzi索引相关.04563及四PDB×250变体，Welch仅作独立记录假设敏感性；消融以三个生成种子为单位。R6按qid对应不等于同一序列前后，pooled3000不作独立生成器重复。其他单元单位仍保留逐格核对。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md", "next_action": "按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。"}

### SC-27 Kanzi 索引匹配是否错误当作天然配对？

- 类别：统计
- 优先级：P0
- 状态：VERIFIED
- 验收：追踪实际样本生成和相关性、检验实现及源均值；核对独立样本分析与dz命名，按正确单位重述；不预先认定旧检验正确。
- 发现：从0d070700恢复被9c28d52f删除的原baseline，SHA256 be03a0a9…，1000键完全匹配，均值及旧p=.001794精确复现。新增Welch p=.002254、CI[-.031124,-.006804]Å，七R级家族校正p=.01578。两臂测不同来源结构，索引差值不称同输入配对，dz只标历史。验证范围为来源、统计重算与正确解释；不认定天然总体因果获益。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_GAP", "finding": "R2聚合文件所指wave218 baseline原始JSON在服务器不存在，不能重建原配对/独立检验；新稿暂不将其显著性列为新主证据。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "从0d070700恢复被9c28d52f删除的原baseline，SHA256 be03a0a9…，1000键完全匹配，均值及旧p=.001794精确复现。新增Welch p=.002254、CI[-.031124,-.006804]Å，七R级家族校正p=.01578。两臂测不同来源结构，索引差值不称同输入配对，dz只标历史。验证范围为来源、统计重算与正确解释；不认定天然总体因果获益。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md", "next_action": "已复算来源与统计；如要主张同输入优化，另需同输入或同生成器匹配设计，不通过改标签获得。"}

### SC-28 三种子自举与家族相关性是否充分披露？

- 类别：统计
- 优先级：P1
- 状态：EVIDENCE_LOCATED
- 验收：写明有限种子自举分辨率/区间局限、聚类单位与已有敏感性分析；不靠追加种子自动过关。
- 发现：新增三运行t(df=2)及名义区间明确依赖分布假设；补充精确符号翻转敏感性，三个配对最小双侧p=.25，不能据极小参数p声称稳健非参数确认。历史簇相关问题不因新研究解决。
- 下一步：保留t假设与符号翻转分辨率；更广训练重复应服务外部有效性，不为通过显著性而补种子。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap84-inference-frontier.md`；`docs/audit/gap90-optsteps-dose.md`；`docs/drafts/paper-A-final.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "三种子自举局限已披露；四点回归df=2临界值已修复并有失败后通过的回归测试。全体蛋白家族敏感性未独立重算。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-29 多重比较和效应阈值是否一致？

- 类别：统计
- 优先级：P1
- 状态：REVISION_NEEDED
- 验收：定义检验家族、选择规则、校正次数、效应量和区间；区分探索与确认，缺失区间不补写。
- 发现：五臂研究四个面积比较Holm校正，两轮留出阶段另为两个比较；单比较内四成本Bonferroni用于前沿核查。名义t区间不是同时区间，没有研究间整体FWER保证；历史探索性拟合及选择后比较仍需保持探索标签。
- 下一步：最终逐表核验预定/探索家族和区间覆盖范围，旧拟合/筛选项保持探索标签，不能补写不存在的确认区间。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/PAPER-EVIDENCE.md`；`docs/audit/gap84-inference-frontier.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "已将决策阈值和回归区间分开；所有历史检验家族、选择规则和校正仍需逐格核对，特别R2。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "REVISION_NEEDED", "finding": "Kanzi沿历史七R级家族报告校正p，明确不覆盖后续调参与多指标；消融12区间未作同时覆盖、仅探索描述。全项目选择路径及检验家族仍未统一闭合。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md", "next_action": "按本项剩余范围继续核对已有记录；不自动启动新的长时生成或训练。"}

### SC-30 projection-FID 与标准 FID 是否混淆？

- 类别：指标
- 优先级：P1
- 状态：VERIFIED
- 验收：追踪特征提取器、投影、参考集、样本量、随机种子与实现；不跨特征空间比较绝对值。
- 发现：保留MNIST投影FID/KID名称，CIFAR统一TF-port Inception2048及同一10000测试参考；主KID不缩放，FID辅助。初始real-real FID门槛失败不删除、不作分数相减修正。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`adaptive_reflow/adapters/mnist_fm.py`；`adaptive_reflow/eval`；`docs/audit/gap84-inference-frontier.md`；`adaptive_reflow/eval/mnist_fid.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": "adaptive_reflow/eval/mnist_fid.py:90-109与203-214 定义像素空间的确定性高斯随机投影及参考样本特征；默认784→128，参考为MNIST测试集。它不是Inception特征FID；具体实验是否覆盖默认维度/种子仍需核对命令和artifact。"}
- {"status": "VERIFIED", "finding": "已沿主驱动到MnistFrechetProjectionEvaluator核实784→128固定高斯像素投影和10000测试图像参考；新稿与Inception FID分开。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-31 蛋白代理指标能否代表结构/功能/家族覆盖？

- 类别：指标
- 优先级：P1
- 状态：VERIFIED
- 验收：逐项解释pLDDT、scPerplexity、HMMER与家族身份，明确其能与不能支持的结论。
- 发现：v4新增指标—源码—原始来源表：scPPL为ESM-IF非padding token平均交叉熵指数，pLDDT为OmegaFold Cα置信度均值，HMMER/Pfam家族、MMseqs2参考库新颖性分别解释；不推成实验功能/天然误差。验证范围为定义和引文，历史版本完整性见SC39。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap31-r6-live-uplift.md`；`docs/audit/gap79-r1-family-lever.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "代理指标解释已收窄；上游评估器版本和对应原始文献归属待完整补齐。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "v4新增指标—源码—原始来源表：scPPL为ESM-IF非padding token平均交叉熵指数，pLDDT为OmegaFold Cα置信度均值，HMMER/Pfam家族、MMseqs2参考库新颖性分别解释；不推成实验功能/天然误差。验证范围为定义和引文，历史版本完整性见SC39。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}

### SC-32 合成重建与分子有效性定义是否准确？

- 类别：指标
- 优先级：P1
- 状态：EVIDENCE_GAP
- 验收：核对坐标来源、单位、对齐、几何桥接、PoseBusters与RDKit的区别及逐记录存储完整性。
- 发现：进一步追踪R3实际compute_all_paper_metrics：默认尝试PB YAML注入，非另一helper的xtb重评；降级路径存在，旧汇总未存成功检查集合和逐分子verdict。v4明确该限制，不宣称原论文PB设置完全复现。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：对历史分子/结构任务核对逐样本坐标、对齐、几何重建及有效性定义，缺原始数据的范围明确保持缺口。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`；`docs/audit/gap39-flowmol3-real-restart-blend.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_GAP", "finding": "Kanzi点读数保留为合成重建，原始基线缺失阻碍完整统计和几何协议重建；PoseBusters/RDKit不混称。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "Kanzi底层恢复并核对输入为4模板扰动、桥生成结构与各自自编码往返；两臂来源不同不称天然结构恢复。FlowMol3历史proxy及真实通道混合分列，PoseBusters逐分子verdict缺口仍未恢复。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "进一步追踪R3实际compute_all_paper_metrics：默认尝试PB YAML注入，非另一helper的xtb重评；降级路径存在，旧汇总未存成功检查集合和逐分子verdict。v4明确该限制，不宣称原论文PB设置完全复现。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}

### SC-33 质量提升是否伴随新颖性/多样性损失？

- 类别：指标
- 优先级：P1
- 状态：VERIFIED
- 验收：公开K7负结果及参考数据库/阈值；将质量、自一致性、覆盖和新颖性分开，不主张同步改善。
- 发现：已在主文保留K7新颖性46.6%→3.7%的不利读数及数据库/阈值范围；未宣称所有质量轴同步提升。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap70-lineageflow-position-blend.md`；`docs/PAPER-EVIDENCE.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "已在主文保留K7新颖性46.6%→3.7%的不利读数及数据库/阈值范围；未宣称所有质量轴同步提升。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-34 哪些组件真的必要？

- 类别：消融与机制
- 优先级：P0
- 状态：VERIFIED
- 验收：盘点已有无反馈、固定混合、自适应控制、完整方法对照；相同协议才可拼成因果消融，不存在的格子标缺失。
- 发现：主参数单因素对照显示部分作用反向；五臂迁移和新两轮候选是完整配置比较，不冒充逐组件因果消融。组件必要性仍仅限已测检查点与协议。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`adaptive_reflow/algorithm/policy_driver.py`；`docs/ABLATION.md`；`docs/audit/gap90-optsteps-dose.md`；`scripts/wave191_p3_mnist_sweep.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "EVIDENCE_LOCATED", "finding": "scripts/wave191_p3_mnist_sweep.py:637-641 在mean_preserve启用时平移最终cloud，使均值等于首轮endpoint均值。消融应单独识别该batch级处理与重启/调度，不能把完整臂的收益直接归因于自适应反馈。"}
- {"status": "EVIDENCE_LOCATED", "finding": "已定位mean_preserve对均值项的直接影响；不把它写成单独已验证组件收益，同协议完整归因矩阵仍未核齐。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_LOCATED", "finding": "GAP76已有实际质心消融，不只是反事实。36比较从96个既有NPZ复算，协方差控制36/36；seed42仅6/12 Δ≤0未达到8/12预测。βtot=.5与主前沿.3不同，不能补成主前沿完整矩阵。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "新增主参数完整配置、无质心、均匀分配、固定时间无混合、零时间重启及单轮基线，六单元全部无跳过、调用计数均C200，历史复现保护全部通过。", "review_round": "round4-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round4-2026-11-03.md", "next_action": "本项关闭主参数局部矩阵缺口；完整因子交互、其他检查点及多预算不在本次验收范围。"}

### SC-35 round数、beta、预算分配的解释是否被已有记录反驳？

- 类别：消融与机制
- 优先级：P1
- 状态：VERIFIED
- 验收：检查GAP-84/90/93和各适配器真实路径；保留已证伪杠杆和不显著结果，不重复提出已做实验。
- 发现：从39个既有summary重算production的β和轮数敏感性，并纳入v4：β=.5平台未测，β=.7变差；R≥4的evidence臂跨度.0346。轮数联动beta/分配，不归因纯迭代；只验证这两组既有扫描及范围，不是所有任务的全参数规律。 第五轮复查：本项历史范围与未解决部分保留，独立图像研究不补填不同任务的缺口。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`todo.json`；`docs/audit/gap90-optsteps-dose.md`；`docs/ABLATION.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "已有round/beta/low-budget审计保留，不重复安排训练或长时采样；尚未逐份重建所有消融配置。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "VERIFIED", "finding": "从39个既有summary重算production的β和轮数敏感性，并纳入v4：β=.5平台未测，β=.7变差；R≥4的evidence臂跨度.0346。轮数联动beta/分配，不归因纯迭代；只验证这两组既有扫描及范围，不是所有任务的全参数规律。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}

### SC-36 残差修正解释是否被误当成机制证明？

- 类别：消融与机制
- 优先级：P1
- 状态：VERIFIED
- 验收：把直接观测、解释与未知分开；源码只证明执行机制，不能单独证明质量变化的因果机制。
- 发现：将路径恒等式、实现、反例和质量观测分别表述；不从源码、状态收缩、误差界或κ诊断推断残差修正的质量机制。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`docs/audit/gap92-kappa-bridge.md`；`docs/audit/gap90-optsteps-dose.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "新稿区分源码执行、经验统计与残差修正解释，未把后者当成因果证明。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-37 图表是否完整且可供判断？

- 类别：呈现与复现
- 优先级：P2
- 状态：VERIFIED
- 验收：方法图、可执行算法、逐任务协议表、主曲线不确定性、案例和完整状态表；图注自解释且可回溯源数据。
- 发现：中文v9共21个表格对象、20张编号表、10图、35条参考文献；新图完整展示预定三时刻、两分辨率与三生成种子均值±标准差，负超额读数保留且不当作负MMD或质量收益。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`tnnls_submission/figures.md`；`tnnls_submission/tables.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "已增加六点含种子SD前沿图、三条受控轴图和方法/协议/证据表；定性样本案例、完整匿名补充仍未完成。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "REVISION_NEEDED", "finding": "v4新增敏感性表和指标来源表，保留两幅主图；h=2定义和β单位已同步。定性样本案例与完整匿名补充仍未完成。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md"}
- {"status": "VERIFIED", "finding": "新增事前保存前64索引中前8样本图，两个检查点六臂并列、seed42、统一显示范围；稿中明确碎片和形态缺陷，不以FID代替视觉质量。", "review_round": "round4-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round4-2026-11-03.md", "next_action": "本项只验收不挑样本的定性展示；仍需独立任务指标或盲评，不把样本图当确认性质量证据。"}
- {"status": "VERIFIED", "finding": "新增四项匹配调用差值曲线、五臂预定索引与独立候选图，完整表格保留全部成本与种子范围；图轴、区间与选择规则注明，最终Word图表另做原生核查。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "verification_scope": "仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。"}
- {"status": "VERIFIED", "finding": "旧8幅图与18个Markdown表格完整保留；新增有限端点诊断表，编号按正文到附录连续排列。Word逐页排版验收及文件摘要写入本轮本地交付收据，不以表图数量证明科学结论。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round8-2026-11-03", "review_record": "docs/audit/manuscript-rewrite-round8-2026-11-03.md", "verification_scope": "本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。"}
- {"status": "VERIFIED", "finding": "中文v8保留8幅已有图，新增可识别性图9；20个表格对象包含19张编号表和1张算法表。三种输出切片均展示，36例逐例记录可复算，不把合成控制写成图像生成质量。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-38 文字是否像审计报告、反复重复限制？

- 类别：呈现与复现
- 优先级：P2
- 状态：VERIFIED
- 验收：每节先写发现与意义再限定范围；重复caveat集中到必要位置，wave/内部路径/开发历史移到补充。
- 发现：摘要、引言、理论衔接、讨论和结论已按研究问题重写；历史纠错和逐项管理保留在审计及自查表。Word正文不导出内部复现索引，保留方法假设、统计限制及不利结果；这些限定服务于论证。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。
- 核查轮次：round8-2026-11-03
- 本轮记录：docs/audit/manuscript-rewrite-round8-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`docs/audit/gap96-manuscript-compression.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "正文按问题—实例—分析—结果—解释重组；运行路径和内部编号集中到内部复现索引。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "VERIFIED", "finding": "正文按问题与结果组织，将历史跨域记录及旧参数敏感性移附录，执行来源放内部索引；限制集中讨论，避免以审计叙事代替科学论证。", "next_action": "保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "verification_scope": "仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。"}

### SC-39 参考文献和上游归属是否完整？

- 类别：呈现与复现
- 优先级：P2
- 状态：REVISION_NEEDED
- 验收：补齐直接相关原始文献、模型/数据/指标版本，逐条验证论断；不追求任意引用数量。
- 发现：补入并读取CMM v2、CorrFlow v1和Gretton核双样本原始论文/正式页面，35条文献按首次出现重排。预印本版本与方法差异明确，历史上游精确版本及最终书目仍待逐项核验。
- 下一步：继续原始证明与引用追溯；科学主张稳定后统一稿件书目。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`docs/drafts/paper-A-final.md`；`tnnls_submission/data_availability.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "参考文献扩展到8条核实来源；上游蛋白/分子模型、指标和数据的完整版本引文仍待补齐。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "REVISION_NEEDED", "finding": "主要原始来源补至19项：直接Restart/rerouting、Kanzi/FlowMol3、OmegaFold/ESMIF/PoseBusters、HMMER/MMseqs2/Pfam及MNIST/CIFAR。原始作者/年份纠正，不抄旧JSON；历史全部依赖版本/数据库release/成功PB设置仍待补齐。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}
- {"status": "REVISION_NEEDED", "finding": "新增流匹配路径、随机插值、Diamond Maps、NR-SMC及Coupled Guidance/ReCouple原始文献与具体关联定位，共26条；旧模型/数据库的精确版本及正式出版格式仍需最后核验，引用数量不作为验收。", "next_action": "逐项补精确模型/数据库版本和正式出版信息，投稿前按目标期刊格式核对；已验证原始文献不反复检索凑引用数。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "REVISION_NEEDED", "finding": "新增Coupled Guidance、ReBridge-Flow、MMD Guidance与经典OT对照；候选命题还需逐定理查新，当前未宣称文献覆盖完整。", "next_action": "继续原始证明与引用追溯；科学主张稳定后统一稿件书目。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md", "verification_scope": "本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。"}
- {"status": "REVISION_NEEDED", "finding": "相关工作增加经典OT、小批耦合、有限循环单调性、ReBridge-Flow和MMD Guidance，参考文献共31条。新增来源使用原论文/正式会议页面；2026预印本注明版本，未写成同行评议定论。", "next_action": "继续原始证明与引用追溯；科学主张稳定后统一稿件书目。", "review_round": "round8-2026-11-03", "review_record": "docs/audit/manuscript-rewrite-round8-2026-11-03.md", "verification_scope": "本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。"}
- {"status": "REVISION_NEEDED", "finding": "32条文献按首次出现重排，含真实AI辅助披露所用系统引用。官方作者须知有效地址、双匿名、10页收费阈值与15页上限已直接核对，旧2012年13页口径不再作现行规则。", "next_action": "继续原始证明与引用追溯；科学主张稳定后统一稿件书目。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-40 审计可复现是否被当成科学正确性？

- 类别：呈现与复现
- 优先级：P2
- 状态：VERIFIED
- 验收：区分hash完整性、重放范围、实验有效性；补充精确命令环境、独立clone检查和匿名发布材料。
- 发现：完整保留协议、失败资源门槛、时限修订、来源摘要与逐分数核见证；全部主分数可复算，指定完整特征可CPU重算，其余大样本留服务器并列摘要。复现层级不等于科学正确性或所有历史模型重生成。
- 下一步：保留本项具体修正；新增实验或稿件改动若改变适用范围须重新验收。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`reproduce`；`paper-data`；`docs/environments.md`；`tools/check_clone_integrity.py`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/thread_environment_check.json`；`docs/audit/manuscript-selfcheck-round4-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md`；`verification_outputs/component-study-20261103/REPORT.json`；`verification_outputs/component-study-20261103/PROTOCOL.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_GAP", "finding": "发现GitHub原副本缺若干被引用前沿JSON，本轮将现存规范化前沿/输入纳入版本控制；完整原始运行及R2缺失源不能由此补造。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "恢复原Kanzi并纳入两臂1000记录，新增统计重算工具与SHA清单；消融提供派生表/24份运行汇总，96个服务器NPZ登记hash但未新发布。Git clone可重建统计/表格层，完整样本重生成及匿名材料层仍缺，未称完全复现。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md"}
- {"status": "EVIDENCE_GAP", "finding": "恢复原Kanzi并纳入两臂1000记录，新增统计重算工具与SHA清单；消融提供派生表/24份运行汇总，96个服务器NPZ登记hash但未新发布。Git clone可重建统计/表格层，完整样本重生成及匿名材料层仍缺，未称完全复现。 第三轮在限制BLAS/OpenMP线程后Lumina哈希回归不一致，恢复原环境通过；不扩大逐字节复现承诺。39次敏感性summary可从clone重聚合，未重新验证原始生成环境。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md"}
- {"status": "VERIFIED", "finding": "v5明确工程门禁、审计复算与科学有效性分开：36对保存特征指标可复算不能证明方法新颖或外部泛化；新增权重/特征发布层与服务器保留大文件边界清楚。", "review_round": "round4-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round4-2026-11-03.md", "next_action": "验收表图/统计/特征指标重算层；未声称冷克隆可完整重生成所有历史样本。"}

### SC-41 第一轮：主张与贡献是否锁定？

- 类别：三轮执行计划
- 优先级：P0
- 状态：REVISION_NEEDED
- 验收：完成SC-02/03/04/07/12，交付一句中心主张、三贡献与证据映射，再进行大段重写。
- 发现：条件分析、端点不可识别性与真实边界干预已形成连贯证据；主张收窄为逐样本接近不足以判定边缘相容。原创充分性及外部预测仍未验收，不能因本轮实验完成就把贡献锁定记为通过。
- 下一步：评估已有工作之外的具体主张与外部可检验性；本轮完成写作与单模型干预，不替代原创性验收。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "中心主张、三层贡献和证据层级已在新版落实；方法/框架定位明确。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "REVISION_NEEDED", "finding": "当前中心问题与实例已锁定，但前置SC-04的独有创新尚未建立；撤回此前整项VERIFIED，不能以完成写作组织代替原创性验收。", "next_action": "以SC-04/05的实质创新判断重新验收贡献锁定，完成写作组织不能使本项恢复整项通过。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "REVISION_NEEDED", "finding": "原创贡献收窄到刷新失配理论候选，完整证明/反例已形成；原创性、可部署性和独立干预仍未验收，贡献锁定未完成。", "next_action": "以逐命题文献差异和实际可证伪预测作为下一轮门槛。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md", "verification_scope": "本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。"}

### SC-42 第二轮：方法、相关工作、主结果是否重写到位？

- 类别：三轮执行计划
- 优先级：P1
- 状态：REVISION_NEEDED
- 验收：围绕已核实证据扩写并同步协议、图表和引文；不以背景和工程功能凑篇幅。
- 发现：中文v9已整合真实轨迹协议、受控结果、对象区分与最新相关工作，未将单检查点诊断写成质量改善或新算法。英文模板、最终篇幅和匿名材料仍待处理。
- 下一步：原创性门槛通过后再整合主稿，不通过则降为背景理论。
- 验证范围：同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。
- 核查轮次：round10-2026-11-03
- 本轮记录：docs/audit/manuscript-intermediate-round10-2026-11-03.md
- 证据：`docs/audit/gap96-manuscript-compression.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round2-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-round2-2026-11-02.md`；`verification_outputs/manuscript-selfcheck-round2-2026-11-02/source_manifest.json`；`docs/audit/manuscript-selfcheck-round3-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round3-2026-11-03.md`；`docs/audit/manuscript-literature-ledger-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`docs/audit/manuscript-rewrite-round8-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md`；`verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`；`docs/audit/manuscript-intermediate-round10-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md`；`verification_outputs/cifar-intermediate-path-20261103-retry1/RESULTS.json`；`verification_outputs/cifar-intermediate-path-20261103-retry1/PROTOCOL.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "REVISION_NEEDED", "finding": "方法、相关工作与主结果已实质重写；逐模型引用与完整补充尚需下一轮完成。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md"}
- {"status": "REVISION_NEEDED", "finding": "已生成v3，新增实际组件消融、Kanzi复算与任务路径映射，收紧跨域主张。完整相关工作匹配对照、全部上游引文及正式英文模板仍待后续。", "review_round": "round2-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round2-2026-11-02.md"}
- {"status": "REVISION_NEEDED", "finding": "新增中文v4，按源码更正预算cap、补敏感性和主要文献及metric定义。正式英文模板、定性图和缺失的公平对照仍未完成。", "review_round": "round3-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round3-2026-11-03.md"}
- {"status": "REVISION_NEEDED", "finding": "v5纳入主参数局部组件矩阵、固定索引定性图、探索性核距离和CIFAR评价校准；正式英文模板、完整匿名材料及公平对照仍未完成。", "review_round": "round4-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round4-2026-11-03.md", "next_action": "按本项限定范围保留已完成核对；剩余证据不足不通过改标签消除，先查现有材料，不自动启动长时采样。"}
- {"status": "REVISION_NEEDED", "finding": "v6按路径条件、原Restart控制与独立验证重写方法/理论/主结果，附录保留历史记录；原创性和正式英文投稿编排尚未完成，不把本轮扩充等同可投最终稿。", "next_action": "先完成创新定位决策和证据映射，再安排英文模板与投稿材料，中文v6作为研究稿保存。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "REVISION_NEEDED", "finding": "新增第六轮中文问题段、候选贡献段与章节组织，保留v6主结果；未将尚未确立的新意写成完成版投稿摘要。", "next_action": "原创性门槛通过后再整合主稿，不通过则降为背景理论。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md", "verification_scope": "本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。"}
- {"status": "REVISION_NEEDED", "finding": "v7主稿已将第六/七轮研究写入方法条件、完整证明、实验协议、结果和讨论，并保留六检查点、组件、五臂及两轮候选数据。验收范围为本轮中文重写，不代表英文格式、创新性或投稿就绪通过。", "next_action": "原创性门槛通过后再整合主稿，不通过则降为背景理论。", "review_round": "round8-2026-11-03", "review_record": "docs/audit/manuscript-rewrite-round8-2026-11-03.md", "verification_scope": "本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。"}
- {"status": "REVISION_NEEDED", "finding": "中文v8已补路径不可识别性命题、控制协议、结果、图表与AI辅助披露；另完成当前TNNLS投稿核对单。中文稿写作验收不等于英文双栏PDF、作者确认或原创充分性验收。", "next_action": "原创性门槛通过后再整合主稿，不通过则降为背景理论。", "review_round": "round9-2026-11-03", "review_record": "docs/audit/manuscript-supplement-round9-2026-11-03.md", "verification_scope": "本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。"}

### SC-43 第三轮：是否按拒稿理由复查？

- 类别：三轮执行计划
- 优先级：P1
- 状态：EVIDENCE_LOCATED
- 验收：对创新、理论、比较、指标、统计逐项验收；每个残留新实验建议注明解决的问题与是否已有证据。
- 发现：本轮按创新重合、训练耦合、最接近控制、批相关KID及三种子推断逐项复查；残余拒稿风险已列优先计划，没有安排超预算实验或把工程门禁当录用标准。
- 下一步：用本轮真实正负结果逐项复查五类拒稿风险；只在新的研究问题可辨且资源明确时启动后续验证。
- 验证范围：仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。
- 核查轮次：round5-2026-11-03
- 本轮记录：docs/audit/manuscript-selfcheck-round5-2026-11-03.md
- 证据：`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "本轮按定义、预算、理论和统计识别并修正具体问题；剩余拒稿风险在表中保留，不宣称全稿验收。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}

### SC-44 TNNLS是否仍是合理首投？

- 类别：投稿决策
- 优先级：P1
- 状态：EVIDENCE_LOCATED
- 验收：P0复核后重评目标，区分大类/小类/分区年份；主题匹配不等于已证明达到录用标准。
- 发现：已定位并直接读取现行TNNLS作者须知及5个官方页面，当前采用双匿名、IEEE Author Portal、常规10页收费阈值和15页最大长度。文章类型和主题适配可继续考察，但原创性、独立干预、英文编排及机构分区认可仍未据此通过；不将官网形式要求核对等同于首投合理性结论。
- 下一步：在核心科学缺口解决后，核对2025历史中科院大类/小类、单位适用规则及可获得的最新官网作者须知，再决定首投；不沿用旧录用概率。
- 验证范围：本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。
- 核查轮次：round9-2026-11-03
- 本轮记录：docs/audit/manuscript-supplement-round9-2026-11-03.md
- 证据：`docs/audit/gap94-standard-benchmark.md`；`todo.json`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`docs/audit/manuscript-supplement-round9-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md`；`verification_outputs/path-identifiability-20261103/RESULTS.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "EVIDENCE_LOCATED", "finding": "继续以TNNLS为目标，但竞争性benchmark、消融与引用缺口仍影响投稿判断；本轮未新做期刊排名结论。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "EVIDENCE_LOCATED", "finding": "TNNLS仅保留主题方向候选；此前主观录用概率与旧分区/影响因子不再作当前判断。官方已宣布2026起不再更新分区表，应按2025历史版本、大类/小类及用户单位认定规则复核；本轮官网作者页面抓取受限，不能宣称2026最新全文已验收。当前不足以称硬一区稿。", "next_action": "在核心科学缺口解决后，核对2025历史中科院大类/小类、单位适用规则及可获得的最新官网作者须知，再决定首投；不沿用旧录用概率。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "verification_scope": "仅本项列出的实现、统计与稿件修正；剩余科学条件以发现及下一步为准。"}

### SC-45 是否完整记录全部上一轮审稿建议并同步源码？

- 类别：记录与同步
- 优先级：P0
- 状态：VERIFIED
- 验收：保存本表和JSON、注册todo入口、更新audit索引；提交并推送服务器现有源码/记录历史后，从GitHub获取本地正式副本并核对HEAD。
- 发现：完整45项及既有历史保留。科学提交e505feb88a6393a9823f1873dd170f14409be7c0已推送GitHub，Mac快进拉取且工作树干净；核对14个科学文件摘要，100案例CPU回放最大误差8.881784197001252e−16，容差1e−9。工程门禁在服务器通过，不宣称Mac执行全套或新增图像生成。
- 下一步：本轮Word交付和最终闭环提交号见Mac收据；继续沿SC-04/05保留的原创性缺口推进。
- 验证范围：本轮记录的条件证明、CPU数值检查与表达修正；不代表新颖性、神经模型外部验证或一区成熟度通过。
- 核查轮次：round6-2026-11-03
- 本轮记录：docs/audit/manuscript-originality-round6-2026-11-03.md
- 证据：`todo.json`；`docs/audit/INDEX.md`；`docs/audit/manuscript-selfcheck-round1-2026-11-02.md`；`docs/drafts/paper-A-zh-reviewed-2026-11-02.md`；`docs/audit/manuscript-selfcheck-round5-2026-11-03.md`；`docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md`；`verification_outputs/manuscript-selfcheck-round5-2026-11-03/MAC_REPLAY.json`；`docs/audit/manuscript-originality-round6-2026-11-03.md`；`verification_outputs/ot-refresh-20261103/MAC_REPLAY.json`

历史记录（逐轮原文保留）：

- {"round": "registration", "status": "RECORDED", "finding": ""}
- {"status": "VERIFIED", "finding": "上一轮全部45项与源码已同步；本轮在相同表中保留历史并记录范围，不以VERIFIED表示整个项目已无问题。", "review_round": "round1-2026-11-02", "review_record": "docs/audit/manuscript-selfcheck-round1-2026-11-02.md", "next_action": "按本轮发现中保留的缺口继续核对；已修正的表述不重复重跑实验。"}
- {"status": "EVIDENCE_LOCATED", "finding": "45项和各轮历史全部保留，新源码/证据/稿件待最终检查后提交GitHub并拉取Mac；完成同步后以独立回执核对HEAD及本地复算，不提前宣称本轮同步完成。", "review_round": "round5-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md", "next_action": "最终门禁通过后提交并推送GitHub，从Mac正式clone拉取同一HEAD，复算核统计/指定特征并导出Word，以同步回执验收。"}
- {"status": "VERIFIED", "finding": "科学源码与证据提交5edbd6c5d701f6764e91c134662e2ca8fb7b44ae已从服务器推送GitHub并由Mac正式clone快进拉取；本地核对126个发布文件摘要、78个主分数及运行间统计、5个指定完整特征FID/KID。45项及历史全部保留。本项验收的是该科学提交的同步与限定复算，不表示所有历史模型在Mac重生成或整稿可投。记录闭环提交的最终HEAD另见Mac交付收据。", "next_action": "保留本轮同步与复算回执；后续源码/证据改动须再次核对来源与Mac副本。", "review_round": "round5-sync-2026-11-03", "review_record": "docs/audit/manuscript-selfcheck-round5-2026-11-03.md"}
- {"status": "EVIDENCE_LOCATED", "finding": "全部45项及既有历史保留，本轮源码/证明/逐条CPU证据已整理；GitHub推送及Mac回放待闭环。", "next_action": "完成服务器检查、推送GitHub、Mac快进拉取与100案例回放后记录收据。", "review_round": "round6-2026-11-03", "review_record": "docs/audit/manuscript-originality-round6-2026-11-03.md"}
