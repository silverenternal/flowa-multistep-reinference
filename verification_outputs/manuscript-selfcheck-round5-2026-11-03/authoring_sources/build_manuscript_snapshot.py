from pathlib import Path
import json,re
r=Path('/home/hugo/codes/flowa-multistep-reinference')
p=r/'verification_outputs/cifar-study-20261103';q=r/'verification_outputs/cifar-consistent-candidate-20261103'
a=json.loads((p/'REPORT.json').read_text());b=json.loads((q/'REPORT.json').read_text())
assert a['n_canonical_cells']==12 and a['n_metric_witnesses_replayed']==60
assert b['status'] in ['COMPLETE','DEFERRED']
s=(r/'docs/drafts/paper-A-zh-reviewed-round4-2026-11-03.md').read_text()
labels={'baseline_euler':'Euler 单次积分','full_euler':'四轮完整配置','simple_euler':'零时间四轮候选','ve_heun':'VE-Heun 无重启','ve_restart':'Restart（RF 接口）','consistent_two_round':'后段时间匹配两轮候选'}
def fmtci(z):return f"[{z['nominal_ci95'][0]:+.6f}, {z['nominal_ci95'][1]:+.6f}]"
def verdict(z):
 if z['clears_preregistered_practical_improvement']:return '达到预设改善条件'
 if z.get('detectable_practical_regression'):return 't 模型下可检出退化'
 return '未达到预设改善条件'
def findrow(rep,arm,base):return next(z for z in rep['primary_contrasts'] if z['arm']==arm and z['baseline']==base)
full=findrow(a,'full_euler','baseline_euler')
if b['status']=='COMPLETE':
 h1=findrow(b,'consistent_two_round','baseline_euler');h2=findrow(b,'consistent_two_round','ve_restart')
 if h1['clears_preregistered_practical_improvement'] and h2['clears_preregistered_practical_improvement']:holdout_summary='两轮候选在另行锁定的两点生成随机性留出验证中满足相对两项控制的改善条件，尚不构成完整前沿优势。'
 elif h1['clears_preregistered_practical_improvement']:holdout_summary='两轮候选满足相对 Euler 的局部改善条件，但没有形成相对 Restart 的同等证据。'
 elif h1['mean']>=0 and h2['mean']>=0:holdout_summary='两轮候选对 Euler 与 Restart 的面积差均为正，未达到预设改善条件。'
 else:holdout_summary='两轮候选未形成相对 Euler 与 Restart 均达到预设实用改善的证据。'
else:holdout_summary='两轮候选因剩余预算条件未启动，不报告其质量结论。'
abstract=f'''轮次边界混合终点与先验为冻结流模型提供了再推理方式，但其目标保持条件与质量收益并不等同。本文分析独立插值路径的目标保持与学习误差递推，并给出耦合路径下的失效反例。六个 MNIST 检查点中，一个弱检查点的投影 Fréchet 平台改善 12.75%，其余五个按既定规则持平；两检查点组件对照中观察到作用反向。在独立 CIFAR-10 检查点上，对五种采样过程匹配实际速度场调用；完整配置相对 Euler 的未缩放核距离（KID）对数成本面积差为 {full['mean']:+.6f}，未观察到该配置的迁移优势。{holdout_summary}结果表明，端点再推理需结合训练路径、时间对应和数值实现逐项验证，状态收缩不能替代质量证据。'''
s=s.replace('# FlowA：面向冻结流匹配检查点的轮次边界再推理','# FlowA：冻结流匹配检查点端点再推理的适用条件与独立验证',1).replace('中文修订稿 v5','中文修订稿 v6',1)
intro_note=s[s.index('本版新增'):s.index('## 摘要')]
s=s.replace(intro_note,'中文研究稿根据操作定义、组件对照、独立模型验证与原始文献组织；正式投稿的英文模板与材料编排另行完成。\n\n')
s=re.sub(r'(## 摘要\n\n).*?(\n\n关键词：)',lambda m:m[1]+abstract+m[2],s,count=1,flags=re.S)
old_contribution='本文贡献分为三个层次。第一，给出可执行的轮次边界再推理定义，明确主实验实际使用的初值、时间区间、预算和样本级后处理。第二，以六检查点的匹配预算前沿及受控轴分析界定质量收益，并将经验协方差诊断与条件性数学性质联系但不等同。第三，以清楚区分任务和比较臂的跨域结果，以及可追溯的实现记录，展示该控制面的可复用性。完整前沿优势仍限于一个 MNIST 检查点；跨域点改善不承担普遍加速或普遍质量保证。'
assert old_contribution in s
s=s.replace(old_contribution,'本文研究三个相互关联的问题：端点混合在哪些路径条件下保持目标、实际组件是否必要、局部收益能否迁移到独立模型。我们首先对实际随机边界核写出条件与反例；随后用六检查点曲线及主参数单因素矩阵区分组件作用；最后以原始 Restart 函数的同模型适配、无重启求解器控制和留出生成随机性的候选验证检验外部适用性。方法操作的相关思想已有基础，本文的主张落在这些受控分析与实证结论，而不以接口数量或重新命名主张新颖性。')
s=s.replace('本次不据此构造方法胜负，也不与官方 50000 样本、不同求解协议的发表数值直接比较。','这一初始基线诊断不承担方法胜负，也不与官方 50000 样本、不同求解协议的发表数值直接比较。')
s=s.replace('后续应先锁定合适的样本量、参考政策和核距离/重复估计，再运行方法比较。当前完成了独立网络一致性与评价诊断，第二模型家族质量前沿仍未完成。','据此另行锁定参考政策与核距离分析，并运行后续五臂比较。该初始诊断的失败记录仍保留，后续协议与结果见第 V-E 节和第 VI-G 节。')
s=s.replace('当前材料没有这项与原始 Restart 实现的匹配对照。','本研究通过同 RF 检查点上的原函数适配补充匹配调用对照，另设 VE-Heun 控制求解器和时间网格变化；这不等于复现原 EDM/VP 检查点的最佳发表结果。')
needle='### C. 质量—计算量前沿'
related='''2026 年的 Diamond Maps 进一步给出再噪声后继续流映射的构造[23]，其端点特例与本文的混合操作相合；NR-SMC 则在奖励重采样时用端点估计和新源噪声重建中间状态[24]。本文没有它们的完整后验、价值函数或奖励粒子目标，不把状态操作视为独有创新，也不将本次无条件图像对照解释为胜过这些完整系统。流匹配路径与随机动态的基础关系参见[21]–[22]。\n\n'''
s=s.replace(needle,related+needle,1)
s=s.replace('流匹配路径与随机动态的基础关系参见[21]–[22]。','流匹配路径与随机动态的基础关系参见[21]–[22]。训练耦合偏离与指导稳定性的联系已由 Coupled Guidance 分析[25]；ReCouple 则研究训练配对、网络实现及有限成本采样之间的影响[26]。前者的指导任务与后者的后训练目标不同于本研究，但都说明耦合重要性本身不能视为独有发现。')
s=s.replace('算法的新颖性应由具体操作组合和对照证明，而不能由接口数量或工程检查数量代替。','方法原创性须结合最接近的已有构造和可辨科学贡献评价；对照检验效力，不能单独证明新颖性，接口和工程检查数量也不能代替这一判断。')
s=s.replace('本文围绕这一实例组织主结果，再把其他任务作为不同适配条件下的扩展证据。','本文以六检查点和主参数组件界定局部效应，再以独立 CIFAR 对照检验迁移；历史其他任务按其实际比较对象列入附录。')
s=s.replace('最接近的机制背景，不把重启本身列为首次贡献','同 RF 检查点原函数适配与 VE-Heun 控制；不把重启列为首次贡献')
start=s.index('### E. 数据与跨域指标的来源');end=s.index('## III. 方法与主实验实例')
legacy_metrics=s[start:end]
s=s[:start]+'''### E. 数据与评价来源

主数据为 MNIST[18]，独立图像验证使用 CIFAR-10[19]。MNIST 检查点来自项目训练流程；CIFAR 冻结检查点的来源和 EMA 提取核查见第 V-E 节。数据集、检查点、特征评价器与评价参考是不同对象。投影 Fréchet 与 TF-port Inception 指标分别解释，历史 torchvision 缓存也不与新研究混用。其他任务的代理指标及其来源单独列入附录 A。

'''+s[end:]
# Move implementation and legacy evidence out of the main mechanism/results argument.
start=s.index('### F. 实现边界与跨域适配');end=s.index('## IV. 数学性质与经验诊断')
legacy_implementation=s[start:end]
s=s[:start]+'''### F. 独立模型实例与接口边界

CIFAR-10 使用冻结 1RF 速度场，在同权重、同先验政策下分别实现 Euler、完整轮次配置、简化候选和原 Restart 去噪器接口适配。状态与时间转换及实际调用规则见第 V-E 节。接口能够表达一个操作，不代表它保持任意训练路径的边际分布；连续线性插值也不能直接移植为离散类别或图通道的合法更新。其他任务的实际启用路径与比较对象另列附录 A。

'''+s[end:]
start=s.index('## IV. 数学性质与经验诊断');end=s.index('## V. 数据、协议与统计')
s=s[:start]+Path('/tmp/flowa-theory-manuscript.md').read_text()+s[end:]
s=s.replace('此前工具误用了 2.776，本版以修正区间报告，点估计和原始样本不变。','本研究使用这一自由度报告区间；较高拟合度不替代独立家族的预测验证。')
s=s.replace('Kanzi 的逐记录文件本轮从历史版本恢复后，分别复算旧索引差值与 Welch 敏感性；这不使其合成变体成为独立天然结构。','Kanzi 的记录复算区分旧索引差值与 Welch 敏感性；其合成变体不被视为独立天然结构。')
s=s.replace('### D. 新增匹配组件协议','### D. 匹配组件协议').replace('新增实验在首个试运行前','组件实验在首个试运行前')
s=s.replace('文中称 projection-KID；它不是 Inception KID，不与标准 KID 量级比较。','文中称 projection-KID；它不是 Inception KID，不与标准 KID 量级比较。由于质心处理导致批次内相关性，不将该统计量在独立样本下的总体无偏性外推到所有臂。')
s=s.replace('## VI. 结果',Path('/tmp/flowa-cifar-protocol-manuscript.md').read_text()+'## VI. 结果',1)
s=s.replace('零时间重启是结果已被查看的候选变体；若据此提出更简洁方法，必须在独立协议和评价数据上验证，不能回填为事前主方法。','零时间变体由这项局部结果启发，随后作为组合配置在第 VI-G 节接受独立验证；该验证未支持其迁移，亦不将其回填为事前主方法。')
start=s.index('### D. 已有质心消融的复算');end=s.index('### F. 主参数下的匹配组件实验')
legacy_sensitivity=s[start:end].replace('第 VI-F 节','第 VI-D 节')
s=s[:start]+s[end:]
s=s.replace('### F. 主参数下的匹配组件实验','### D. 主参数下的匹配组件实验').replace('### G. 预定索引的定性结果','### E. 预定索引的定性结果').replace('### H. 独立 CIFAR 基线与评价门槛诊断','### F. 独立 CIFAR 基线与评价门槛诊断').replace('第 VI-F 节','第 VI-D 节')
s=s.replace('缺少另一模型家族的可用前沿时，不能将该关系写成可推广的性能预测器。','CIFAR 已增加独立采样验证，但其评价表征与检查点家族不同，没有检验这条投影指标回归的跨家族预测能力。')
start=s.index('### I. 跨域点结果及统计边界');end=s.index('## VII. 讨论')
legacy_results=s[start:end]
legacy_results=legacy_results.replace('CIFAR R5b、HMMER R1','历史 CIFAR R5b、HMMER R1').replace('表 XII. 各单元在当前论证中的地位。','表 XII. 历史记录的比较对象和范围；新增 CIFAR 锁定研究单独见正文，未与旧缓存合并。')
s=s[:start]+s[end:]
# Cross-model fixed results; do not select best rung or seed.
results='### G. CIFAR-10 五臂匹配验证\n\n同一冻结检查点上的 12 个预定种子—预算单元均完成五臂生成，每臂每次 1000 张、无跳过；实际调用与 C 完全一致。表 CIFAR_KID 与表 CIFAR_FID 分别列出三种子均值，不把两个指标合并成统一质量分数。\n\n'
for metric,tag,title,precision in [('kid_unscaled','CIFAR_KID','未缩放 KID',6),('fid_tfport','CIFAR_FID','TF-port FID',4)]:
 results+='| 采样过程 | '+' | '.join('C='+str(c) for c in a['costs'])+' |\n|---|'+'---:|'*len(a['costs'])+'\n'
 for arm,z in a['curves'].items():results+='| '+labels[arm]+' | '+' | '.join(f"{z['per_cost'][str(c)][metric]['mean']:.{precision}f}" for c in a['costs'])+' |\n'
 results+=f'\n表 {tag}. CIFAR-10 的{title}，每格 N=1000/臂/种子、种子 42/43/44；同一 10000 张测试参考。较低为好。\n\n'
results+='| 预定比较 | KID 面积差 | 名义 95% t 区间 | H0:Δ=0 的 Holm p | 判定范围 |\n|---|---:|---|---:|---|\n'
for z in a['primary_contrasts']:
 results+=f"| {labels[z['arm']]} − {labels[z['baseline']]} | {z['mean']:+.6f} | {fmtci(z)} | {z['holm_p']:.3g} | {verdict(z)} |\n"
results+='\n表 CIFAR_AUC. 关于 log C 的归一化梯形面积，差值为前臂减后臂；种子为统计单位，df=2。Holm 仅覆盖四项面积比较。名义区间不是研究范围内同时覆盖区间，也没有训练重复或参考集重采样。\n\n'
results+=f"完整配置相对 Euler 的预定面积差为 {full['mean']:+.6f}，{verdict(full)}。该结论针对迁移后的完整配置，不把其中的重启、分配或质心处理单独当作原因。零时间四轮候选的判定为：{verdict(findrow(a,'simple_euler','baseline_euler'))}；其 MNIST 局部方向不能直接推广到独立图像模型。\n\n"
diagnostic=json.loads((p/'CROSS_BATCH_KID_DIAGNOSTIC.json').read_text())
cross={(row['arm'],row['cost']):row['cross_batch_kid'] for row in diagnostic['rows']}
cross_deltas=[cross['full_euler',c]-cross['baseline_euler',c] for c in a['costs']]
results+=f"针对批次相关性的探索性跨批次核重算中，四档完整配置减 Euler 的差值仍为正，范围 [{min(cross_deltas):.6f}, {max(cross_deltas):.6f}]。这不替换主分析；仅三个独立生成批次，未添加区间或检验，也未把批对数当独立运行数。\n\n"
results+='![独立 CIFAR 匹配调用差异](../figures/review-cifar-matched-2026-11-03.png)\n\n图 5. 四个预定比较的逐成本 KID 差值，误差线为每项比较内四档 Bonferroni 区间。各子图纵轴尺度不同，正值不利于前臂。面积检验与逐档前沿核查分开报告。\n\n'
for z in a['frontier_checks']:
 results+=f"{labels[z['arm']]} 相对 {labels[z['baseline']]}：预定操作性平台条件{'满足' if z['baseline_operational_plateau'] else '未满足'}，完整前沿优势条件{'满足' if z['frontier_win'] else '未满足'}。"
results+='平台条件是有限网格上的规则，不是渐近分布或数值积分收敛证明。\n\n'
clip={arm:z['per_cost']['199']['clipped_fraction']['mean'] for arm,z in a['curves'].items()}
results+='评价前超出合法像素范围的比例在 C=199 时分别为：'+'；'.join(labels[k]+f" {v*100:.2f}%" for k,v in clip.items())+'。所有臂用同一截断和特征变换；较大截断比例是样本失真诊断，不能视为仅显示上的差异。\n\n'
results+='![独立 CIFAR 预定索引样本](../figures/review-cifar-preselected-2026-11-03.png)\n\n图 6. seed42、C=199 的前八个预定索引，五臂均保留，统一像素显示变换；没有按成功程度挑选图像。定性展示不是盲评或额外显著性证据。\n\n'
if b['status']=='COMPLETE':
 results+='### H. 后段时间匹配两轮候选的单独留出验证\n\n此阶段按资源条件启动并完成六个单元、18 个臂结果，无跳过；生成种子为 101/102/103，与五臂研究的种子不混合。表 HOLDOUT 显示两点均值和另行锁定的面积比较。\n\n| 采样过程 | C99 KID | C199 KID | C99 FID | C199 FID |\n|---|---:|---:|---:|---:|\n'
 for arm,z in b['curves'].items():results+='| '+labels[arm]+' | '+' | '.join(f"{z['per_cost'][str(c)][metric]['mean']:.6f}" if metric=='kid_unscaled' else f"{z['per_cost'][str(c)][metric]['mean']:.4f}" for metric,c in [('kid_unscaled',99),('kid_unscaled',199),('fid_tfport',99),('fid_tfport',199)])+' |\n'
 results+='\n表 HOLDOUT. 同一 1RF 检查点上的新生成随机性留出比较；N=1000/臂/种子、同一 10000 测试参考。它不提供新数据集或新训练检查点的确认。\n\n| 预定比较 | 两点 KID 面积差 | 名义 95% t 区间 | H0:Δ=0 的 Holm p | 判定范围 |\n|---|---:|---|---:|---|\n'
 for z in b['primary_contrasts']:results+=f"| {labels[z['arm']]} − {labels[z['baseline']]} | {z['mean']:+.6f} | {fmtci(z)} | {z['holm_p']:.3g} | {verdict(z)} |\n"
 results+='\n表 HOLDOUT_AUC. 两个对数成本端点的归一化面积等于其平均值；df=2，Holm 只覆盖这两个比较。该阶段由前期研究与路径分析提出，不宣称研究设计之间的整体多重性已被控制。\n\n'+holdout_summary+'\n\n![两轮候选的留出结果](../figures/review-cifar-consistent-candidate-2026-11-03.png)\n\n图 7. 两轮候选减对应控制的 KID，名义种子 t 区间。两档预算不能单独构成完整质量—成本前沿。\n\n'
 results+='![两轮候选的预定索引样本](../figures/review-cifar-candidate-preselected-2026-11-03.png)\n\n图 8. 留出协议预先指定的 seed101、C=199、前八索引，三臂使用相同显示变换；没有按质量选择样本，亦不据这些图像建立独立感知显著性结论。\n\n'
else:results+='### H. 两轮候选阶段的预算状态\n\n'+holdout_summary+'该阶段的预定配置、种子和资源门槛仍保留为可审计协议，未用已有四轮配置的结果补填。\n\n'
s=s.replace('## VII. 讨论',results+'## VII. 讨论',1)
start=s.index('## VII. 讨论');end=s.index('## VIII. 结论')
discussion='''## VII. 讨论

### A. 哪些结论能够迁移

MNIST 一个弱检查点的完整前沿优势说明轮次边界操作有可能改变单轨迹平台，但不等于每个组件必要、所有评价器同向或其他模型受益。主参数组件矩阵直接给出作用反向与很小的预算分配差异；独立 CIFAR 对照进一步检验迁移。这些结果不使用蛋白随机序列基线或不同结构来源的重建误差替代同模型验证。

### B. 机制条件与数值实现

理想目标保持要求正确路径分布和对应的时间起点；学习误差、训练耦合、有限步分配、epsilon 约定及批次处理都会改变实际核。耦合反例表明，即使状态距离收缩，也可能向错误分布收缩。经验 κ 与这套条件没有同一含义，较低 Fréchet 指标也不能代替可识别样本、任务效用或多样性检验。

### C. 与已有方法和复现层次的关系

再噪声后继续流映射、源噪声更新和误差—收缩竞争都有直接相关工作[3],[21]–[24]。本文的受控结论针对指定实例及其适用条件，不据接口封装主张独有操作，也不据一次无条件图像试验宣称胜过奖励引导系统。固定模型、统一特征和实际调用匹配提高了可比性，却不消除检查点与指标选择的限制。

原始像素、生成特征、预定图像索引和执行来源分别记录。版本控制中的核统计量能够重算全部主分数和种子统计，指定完整特征单元还能在 CPU 上重算 FID/KID；大型原始样本与其他特征保留在服务器并提供摘要。这些复现层次不被合称为所有历史模型的完整重生成，更不等于方法科学正确性。

### D. 限制与后续研究

当前独立验证仍限于一个 CIFAR 训练检查点、固定测试参考和少量生成运行。两轮候选阶段只留出生成随机性，没有新数据集或训练重复。完整配置的批次相关性、有限样本 FID、三个种子的参数推断，以及原 Restart 接口适配的参数范围均需保留。更广泛的路径耦合、独立感知/任务质量与训练重复应在后续研究中验证，不能通过增加背景篇幅或工程检查消除。

'''
s=s[:start]+discussion+s[end:]
start=s.index('## VIII. 结论');end=s.index('## 参考文献')
conclusion='## VIII. 结论\n\n本研究把冻结流模型的端点再推理明确分为状态重构、时间对应、预算和输出处理，并给出独立路径下的充分条件及训练耦合反例。六检查点 MNIST 曲线与主参数消融界定了局部收益；同权重 CIFAR 五臂比较中，完整配置相对 Euler '+verdict(full)+'。'+holdout_summary+'实验支持对具体核和检查点逐项检验，区分理想目标保持、状态收缩与实际质量。\n\n'
appendix='## 附录 A. 历史跨域记录的比较对象与边界\n\n这些记录用于说明适配与评价范围，不承担正文端点核的第二模型正向确认。\n\n'+legacy_implementation.replace('### F. 实现边界与跨域适配','### A. 实际组件与任务路径')+legacy_metrics.replace('### E. 数据与跨域指标的来源','### B. 历史任务的评价定义')+legacy_results.replace('### I. 跨域点结果及统计边界','### C. 蛋白与结构记录').replace('### J. 条件、未显著与不利结果','### D. 其他协议与不利结果')+'\n## 附录 B. 历史参数敏感性与输出平移\n\n'+legacy_sensitivity.replace('### D. 已有质心消融的复算','### A. β=.5 的质心消融').replace('### E. β 与轮数的已有敏感性','### B. β 与轮数的敏感性')
appendix=re.sub(r'已核对旧报告：.*?原报告与本轮复算的绝对读数一致。','绝对单位的复算、原始来源与单位核对见补充审计。',appendix,flags=re.S)
s=s[:start]+conclusion+appendix+'\n'+s[end:]
refs='''[21] Y. Lipman et al., “Flow Matching Guide and Code,” arXiv:2412.06264, 2024. https://arxiv.org/abs/2412.06264

[22] M. S. Albergo, N. M. Boffi, and E. Vanden-Eijnden, “Stochastic Interpolants: A Unifying Framework for Flows and Diffusions,” arXiv:2303.08797, 2023 (v4, 2025). https://arxiv.org/abs/2303.08797

[23] P. Holderrieth et al., “Diamond Maps: Efficient Reward Alignment via Stochastic Flow Maps,” arXiv:2602.05993v3, 2026. https://arxiv.org/abs/2602.05993v3

[24] W. Lian, Z. Zhao, and T. B. Schön, “Test-Time Scaling of Text-to-Image Flow Matching Models with Noise-Rejuvenated Sequential Monte Carlo,” arXiv:2610.25479v2, 2026. https://arxiv.org/abs/2610.25479v2

'''
refs+='''[25] M. Clémente, L. M. Brunswic, R. H. Yang, and A. Rasouli, “Coupled Guidance for Flow Matching,” arXiv:2610.40109v1, 2026. https://arxiv.org/abs/2610.40109v1

[26] S. H. Lim, A. Gupta, M. W. Mahoney, and N. B. Erichson, “Coarse-Graining Optimal Transport for Rollout-Free Post-Training of Flow Matching,” arXiv:2610.41269v1, 2026. https://arxiv.org/abs/2610.41269v1

'''
s=s.replace('## 内部复现索引',refs+'## 内部复现索引',1)
# Renumber table labels by final reading order, including moved appendix tables.
def roman(n):
 result=''
 for value,symbol in [(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
  while n>=value:result+=symbol;n-=value
 return result
captions=re.findall(r'^表 ([A-Z_]+)\.',s,re.M);assert len(captions)==len(set(captions)),captions
mapping={tag:roman(i+1) for i,tag in enumerate(captions)}
s=re.sub(r'表 ([A-Z_]+)(?=[. ，。；\n])',lambda m:'表 '+mapping.get(m[1],m[1]),s)
s=s.replace('本轮从','该分析从').replace('本轮用户','实验用户').replace('本轮补入','文中纳入').replace('本轮核查','实现核查').replace('新增组件实验','组件实验').replace('本轮','该分析')
s+='\n独立模型证据：verification_outputs/cifar-study-20261103/PROTOCOL.json、REPORT.json、STATISTICAL_SCOPE_ADDENDUM.json；两轮候选：verification_outputs/cifar-consistent-candidate-20261103/PROTOCOL.json、REPORT.json。理论与文献来源：docs/audit/manuscript-boundary-kernel-2026-11-03.md、docs/audit/manuscript-related-work-round5-2026-11-03.md。精确执行、实际 GPU 预算和未闭合自查项以 docs/audit/manuscript-selfcheck-round5-2026-11-03.md 为准。\n'
out=r/'docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md';out.write_text(s);print(out,len(s),len(captions),'captioned tables')
