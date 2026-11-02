# 直接相关工作补核：2026年端点与噪声更新方法

日期：2026-11-03。核对原始论文，未依赖搜索摘要或第三方评议作为技术依据。该补核在CIFAR五臂协议锁定之后进行；没有据文献或中途分数修改实验臂。尚未声称穷尽文献。

## NR-SMC

W. Lian, Z. Zhao, T. B. Schön, Test-Time Scaling of Text-to-Image Flow Matching Models with Noise-Rejuvenated Sequential Monte Carlo，arXiv:2610.25479v2，2026。来源：[原文](https://arxiv.org/html/2610.25479v2)，第3.2–3.3节、式(9)–(14)。工作以端点估计和新的源噪声重构中间状态，配合奖励加权、重采样及look-ahead。本文没有该奖励/粒子选择目标，现有MNIST预算策略也非在线SMC。不能再把“冻结FM、重构源噪声与端点”独列首次贡献；不同任务与目标也不构成本文胜过该方法的证据。

## Diamond Maps

P. Holderrieth et al., Diamond Maps: Efficient Reward Alignment via Stochastic Flow Maps，arXiv:2602.05993v3，2026。来源：[原文](https://arxiv.org/html/2602.05993v3)，第5节式(21)–(23)。其中对现有流映射先再噪声再映至终点的核，在α_t=t、σ_t=1−t和原时刻t=1时，特化为m*x+(1−m)*新噪声后从m积分至1。这部分操作与本项目主实例相同，不应只强调整篇工作还涉及训练而忽略该直接关系。该文的加权恢复奖励、后验和值函数目标与本文不同；无条件目标保持也不等于后验正确性。

## 基础来源与理论归属

Y. Lipman et al., Flow Matching Guide and Code，arXiv:2412.06264，2024：[原文入口](https://arxiv.org/abs/2412.06264)。M. S. Albergo, N. M. Boffi, E. Vanden-Eijnden, Stochastic Interpolants: A Unifying Framework for Flows and Diffusions，arXiv:2303.08797，2023、当前v4：[原文入口](https://arxiv.org/abs/2303.08797)。路径与随机动态的转换已有系统理论；本文的线性FM到VE去噪器接口与针对端点核的W₂耦合推论不作为该思想的首次提出。

原Restart已分析收缩与新增近似/离散误差的竞争：[原文第4.2节](https://arxiv.org/html/2306.14878v2)。因此“初始误差大时可能受益、过强重启可能累积新误差”不是本项目独有新理论。新增的源代码级同权重比较只验证本次锁定实例；不能替代奖励引导任务中的NR-SMC或Diamond Maps完整数值复现。

## 对稿件定位的影响

主状态操作与已有工作存在具体代数关系，创新性缺口比“需要再补两条引用”更实质。论文应以实际组件作用、状态—时间/训练耦合条件和独立协议结果为依据，明确哪些是分析推论、哪些是实证发现；若要作为强方法论文投稿，仍需独立于这些既有操作的新方法贡献和独立验证。不得靠更名、接口数、数学符号数量或工程门禁提高证据等级。

## 2026-11-03 分区与投稿口径复核

[中国科学院文献情报中心2026-03-27官方声明](https://las.cas.cn/news/tzgg/202603/t20260327_8178738.html)明确自2026年起不再更新与发布期刊分区表，其他机构发布的分区表与该中心无关。因此不能写成已经核验“2026中科院一区”；未来成果认定须区分2025历史版本、具体大类/小类以及作者所在单位适用规则。此处未获得用户单位政策，不能假定其认定规则，也不把JCR Q1自动替代为中科院一区。

TNNLS当前仅保留主题候选。IEEE CIS作者页面本次抓取返回418，官方IEEE Xplore检索可定位作者须知但可见文本仅元数据；本轮不据旧页面/第三方摘要宣称2026最新页数与费用要求已复核。先前结构用于中文研究稿，英文双栏及最新正式投稿须知继续保留为SC-01/39/44的未完成项。旧todo中的主观录用概率已被当前审稿判断明确取代，不作为测量或预测。

作者须知出处：[IEEE TNNLS Information for Authors](https://cis.ieee.org/publications/t-neural-networks-and-learning-systems)；2023原始须知出版记录：[IEEE Xplore](https://ieeexplore.ieee.org/abstract/document/10114441)。查阅日期2026-11-03；不能把2023出版记录当2026最新全文。

## 2026-11-03追加：耦合条件并非空白研究方向

- Clémente等，[Coupled Guidance for Flow Matching](https://arxiv.org/html/2610.40109v1)，arXiv:2610.40109v1，2026-10-29。§3.3式(6)–(10)协调重构源端与数据端，§3.4讨论训练耦合偏离及误差。任务为指导采样，不能当本研究无条件重启的直接胜负；“考虑耦合”的动机已有先例。
- Lim等，[Coarse-Graining Optimal Transport for Rollout-Free Post-Training of Flow Matching](https://arxiv.org/html/2610.41269v1)，arXiv:2610.41269v1，2026-10-30。引言及§3区分训练配对、有限网络实现与采样成本的影响，研究需后训练。它不是本次冻结权重控制臂，不据此主张本方法胜过ReCouple。

对本稿的影响：现有高斯反例与条件恒等式只能承担指定边界核的解释；不能把耦合重要性或这些基础推导重新包装成原创理论主线。尚需识别独立且可检验的贡献。上述为原始全文核对，未使用搜索聚合摘要作技术结论；没有新增GPU实验。
