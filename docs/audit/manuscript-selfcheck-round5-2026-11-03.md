# 投稿自查第五轮：独立模型匹配验证与路径条件

日期2026-11-03。用户明确授权持续goal、按推荐路线自主推进，并沿用现有服务器、不购买资源、总计2 GPU小时上限。基准提交af7955bda500270b775300c0d5210adc1c142f77；旧稿v5与冻结投稿包保留，新稿v6按新增证据组织。本轮按研究审计、实验与论文证据技能执行；不以负结果改参数或追加种子。

## 1. 评价校准与事前锁定

旧N1000基线FID35.5045未通过<10门槛，原失败记录仍保留。真实—真实N1000/9000比较FID32.0719，显示绝对门槛未作适当小样本校准。新研究改用事前锁定的相对KID面积，FID为次指标，不相减作无偏校正。独立真实特征的5组固定互斥排列KID在约−7.10e-5至+7.70e-5间；这些排列共享数据，不能称5个独立数据集。

第一协议在任何pilot或方法生成前于2026-11-02T17:59:02 UTC本地锁定；不是公共注册。第二候选在第一研究运行中、见过部分seed42结果和理论分析后另行锁定，新配置与生成种子101/102/103未被运行。它留出的是生成随机性，不是新数据集或模型。两研究不合并种子，不声称全研究多重性统一受控。

## 2. 运行修正与基线来源

初始N32代码pilot处理完整且调用匹配，但按冷启动时间外推触发时间保护，正式研究未启动。独立运行剖析显示预热后的25次调用约.5秒；RUNTIME_AMENDMENT只修正资源估计、加入每单元冷启动/评分余量，采样源码、臂、种子、N、指标和假设均未改变。初始失败保护、pilot、剖析和修正文件保留。没有基于质量取消或改选比较臂。

环境为.venvs/flowmol3_venv，Torch2.7.0+cu128等版本与Inception权重SHA见ENVIRONMENT。CIFAR科学生成用GPU1 RTX5090、FP32网络/Euler状态；原VE函数保留FP64状态，matmulTF32关闭、cuDNN TF32开启。代数核查和统计为CPU。GPU0的N2/C25官方Euler整段核对最大误差0；564个清理推理参数与原始训练checkpoint的EMA逐个完全一致，sigmas缓冲相同、训练step800001。它们支持本地提取与实现路径，不独立证明远程下载真实性或复现已发表50k FID。

## 3. 第一研究的完整观察

12个固定种子—成本单元、五臂、N1000/臂/单元；种子42/43/44，实际C25/49/99/199。每臂实际调用匹配，无跳过，源代码SHA受协议保护。五臂为Euler、主参数四轮完整配置、均匀预算/零时间/无质心候选、VE-Heun、原Restart函数的RF接口适配。原Restart源码字节不改；使用源发布配置格式的一组参数，不称原EDM/VP最佳结果复现。

主统计量为每种子的KID关于log C归一化面积；四个预定差值用df2配对t和Holm4。以下方向为前臂减后臂、越负越好：

| 前臂 | 后臂 | 均值差 | 名义95%区间 | Holm p | 改善条件 |
|---|---|---:|---|---:|---|
| full_euler | baseline_euler | +0.008077871 | [0.007300319576536451, 0.008855422941570644] | 0.00100022 | False |
| simple_euler | baseline_euler | +0.130650729 | [0.1284584993263563, 0.13284295857072062] | 6.08311e-05 | False |
| simple_euler | ve_restart | +0.132118430 | [0.12884093256264692, 0.13539592799876424] | 9.97206e-05 | False |
| ve_restart | ve_heun | +0.001191206 | [0.000643881531526164, 0.0017385296828075687] | 0.0112122 | False |

主推断针对固定N整批分数的运行间变化。质心处理会使同批输出相关，不能声称KID U统计量对完整臂仍满足iid条件下的总体无偏性；STATISTICAL_SCOPE_ADDENDUM在研究完成前记录此解释范围，数值统计与假设不改。三个种子不能验证正态假设，双侧精确符号翻转只有8种分配、最小p=.25；精确p只作探索性敏感性，不替换已登记t分析。跨批次核距离诊断不依赖批内独立生成核的假设，但仅3批、无新增p或CI，也不替换主分数。

## 4. 两轮路径一致候选

候选R2、m=.7、实际后段时间[.7,1]、按区间长度[1,.3]分配C99:[76,23]、C199:[153,46]，不作质心平移。该配置使用项目已有比例分配能力，不作为新发明的再噪声算子。资源门槛只看剩余时间，未根据第一组质量分数决定启动。固定新种子101/102/103，不为旧配置补种子。

全部6单元/18臂结果完整、无跳过。两点KID面积的两项预定比较用Holm2，不能把两预算写成完整前沿。

| 前臂 | 后臂 | 均值差 | 名义95%区间 | Holm p | 改善条件 |
|---|---|---:|---|---:|---|
| consistent_two_round | baseline_euler | +0.000344264 | [-0.00038096412247011886, 0.001069491178333168] | 0.177846 | False |
| consistent_two_round | ve_restart | +0.001643537 | [0.0009437076912455622, 0.002343367020727012] | 0.0193045 | False |

## 5. 理论与新颖性边界

新推导针对随机端点核，而非只对固定输入映射作压缩论证：独立端点路径与理想后段流给出目标保持；实际不等预算映射满足带未知偏差和Lipschitz常数的递推。全局常数没有被经验κ认证，该界也不是FID改善保证。解析反例说明耦合训练路径下零速度场可以已精确生成目标，而相同端点混合仍将方差从1缩至.68、最终1/9（m=.8）。均值平移不能修复协方差。推导和12组代数核查见manuscript-boundary-kernel审计，不把有限网格测试当证明或新模型实验。

直接相关文献补核见manuscript-related-work-round5审计。Diamond Maps的端点特例与当前混合操作有具体代数对应，NR-SMC也使用端点估计与新源噪声重构中间状态。原Restart已分析收缩与新增误差的竞争。因此噪声再注入、重复流映射或该经典误差权衡不作为项目独有新颖性；原函数匹配对照也不等于胜过完整奖励引导系统。

## 6. 证据发布、当前寄存器与稿件

全部新分数、协议、执行来源、核统计量及预定图像发布；指定原始生成特征与完整参考支持CPU重算。大型原始像素与其余完整特征保留服务器，各文件SHA及是否纳入Git由SOURCE_MANIFEST区分。表图/统计重算、完整特征指标重放和模型样本重生成是不同层次，不声称冷克隆已验证所有历史生成环境。

当前paper-evidence寄存器的旧R1/R2/R6机理WIN不能继续作为当前等级：随机序列基线、不同结构来源以及低预算有效一轮不构成匹配机理增益。旧快照、原数值和冻结稿保留；当前寄存器改记该匹配主张未测，降为局部材料等级。MNIST仍只有w16e1_5k满足记录的projection-FID前沿规则；CIFAR新增研究与旧torchvision缓存分列，不把新主指标KID偷偷换成原FID WIN。

中文v6把主论证集中到路径条件、组件与独立图像验证，历史跨域记录/敏感性保留附录。45项自查继续保存历史，未闭合的新颖性、独立正向主线、旧执行版本/指标设置与正式模板问题不通过改标签消除。

## 7. 全局资源记账

GPU作业外层墙钟保守计入 6638 秒（上限7200秒），剩余 562 秒未使用；包括先前360秒、剖析120秒、Euler核对60秒、第一研究含pilot外层墙钟及可选第二阶段外层墙钟。该口径还包含评分和IO时间，没有购买资源。原始运行日志与GLOBAL_BUDGET_FINAL保存精确口径。

## 8. 科学判断与下一步

独立对照与条件反例提高了论证可辨性，不自动使论文成为“硬中科院一区”。当前操作与已有工作的重合是实质新颖性问题，不能靠引用数、篇幅、接口或工程门禁解决。后续应依据已测结果重建可辨的科学贡献，并在更广模型、参考/训练重复和完整竞争性协议下验证；不追加种子或继续花GPU来挑选有利结果。

## 9. 工程与本地核查

全部24项强制门禁退出0，72项D4/adapter回归和23项定向测试通过；严格文档、原始上游完整性与账本新鲜度通过。完整测试只作收集，不声称全套执行。28条检查的原始退出码保存在本轮checks.json；补充git格式检查因原样上游/模板字节及生成Markdown合法换行出现非零，未修改其原字节，另以WHITESPACE_SCOPE.json列出精确例外、摘要与项目改动检查退出0。工程通过不等于科学主张成立。Mac从GitHub拉取同一提交后重算全部核统计与指定完整特征指标，再导出Word和本地收据。原始上游与冻结投稿包未改。

## 10. 本轮结论与复算入口

五臂研究完整配置对Euler的KID面积差+0.0080778713；两轮后段时间匹配候选对Euler+0.0003442635、对Restart+0.0016435374，均未达到登记改善条件。后者对Restart的零差异t检验家族内Holm p=.0193045，但名义区间下限.0009437没有越过预定.001实用退化边界；不混淆零差异检验与实用阈值，也不把Euler的不显著比较称等效。候选不提升为已验证改进，原完整配置不作为跨模型质量优越性的证据。本轮剩余562秒GPU额度未使用，不安排新的配置筛选。

高斯相关性连续诊断为CPU闭式核查，36组条件刷新方差恒等式保存在本轮verification目录；不是训练模型实验。新增Coupled Guidance与ReCouple原文进一步说明耦合偏离和耦合—实现关系已有背景，本稿仍须识别独立贡献。官方2026起停止更新中科院分区；历史2025分类、单位认定规则与最新可取得的作者须知须分开验收，详见相关文献审计。

统计解释复核记录在第一研究INFERENTIAL_SCOPE_REVIEW.json：Holm检验零差异；.001实用参照使用名义区间而非同时覆盖。穷举符号翻转的参考解释需符号可交换/对称性，不是仅凭均值零即可成立的分布无关检验。本记录为第一研究结果后的解释核查，不改已登记规则、假设或任何分数。

下列源码起始行由当前文件语法树提取；它们指向实际执行/复算路径，不是只凭接口名称判断启用。

| 文件 | 函数/类 | 起始行 |
|---|---|---:|
| `tools/cifar_matched_frontier_20261103.py` | `digest` | 25 |
| `tools/cifar_matched_frontier_20261103.py` | `official_sampler` | 29 |
| `tools/cifar_matched_frontier_20261103.py` | `main_steps` | 41 |
| `tools/cifar_matched_frontier_20261103.py` | `denoiser_value` | 48 |
| `tools/cifar_matched_frontier_20261103.py` | `RFDenoiser` | 57 |
| `tools/cifar_matched_frontier_20261103.py` | `generate` | 74 |
| `tools/cifar_consistent_candidate_20261103.py` | `sha` | 22 |
| `tools/cifar_consistent_candidate_20261103.py` | `candidate` | 26 |
| `tools/cifar_study_metrics_20261103.py` | `kernel_rows` | 9 |
| `tools/cifar_study_metrics_20261103.py` | `kernel_score` | 29 |
| `tools/report_cifar_study_20261103.py` | `exact_signflip_three` | 17 |
| `tools/report_cifar_study_20261103.py` | `log_area` | 33 |
| `tools/report_cifar_study_20261103.py` | `analyze` | 44 |
| `tools/report_cifar_study_20261103.py` | `figures` | 211 |
| `tools/report_cifar_candidate_20261103.py` | `analyze` | 17 |
| `tools/review_coupling_continuum_20261103.py` | `coupling_diagnostic` | 11 |

在具有NumPy/SciPy的CPU环境中，从仓库根目录运行；输出指向临时文件，避免覆盖已发布记录：

```bash
python3 tools/report_cifar_study_20261103.py --root verification_outputs/cifar-study-20261103 --out /tmp/flowa-first-replayed.json
python3 tools/report_cifar_candidate_20261103.py --root verification_outputs/cifar-consistent-candidate-20261103 --repository . --out /tmp/flowa-candidate-replayed.json
python3 tools/replay_cifar_features_20261103.py --repository . --study verification_outputs/cifar-study-20261103 --out /tmp/flowa-first-fullfeatures.json
python3 tools/replay_cifar_features_20261103.py --repository . --study verification_outputs/cifar-consistent-candidate-20261103 --out /tmp/flowa-candidate-fullfeatures.json
```

前两项从全部78个臂结果的核统计量重算主分数/运行间推断；后两项读取指定的2+3个完整生成特征及共同10000参考，重算FID和KID。FID跨依赖数值容差1e-4，KID容差1e-12。它们不加载生成模型、不使用GPU，不构成从噪声重新生成全部样本。服务器与Mac的实际SciPy/NumPy版本及误差以各自回执为准。

工程旧警告原样保留：账本6条非致命状态解析消息与历史链接检查的诊断均见checks.json实际输出，不把退出0解释为全库无历史警告。源码与原始记录先提交/推送，再从GitHub拉取Mac核对并导出Word；同步完成信息由后续收据记录。

## 11. GitHub到Mac科学提交复核

科学提交5edbd6c5d701f6764e91c134662e2ca8fb7b44ae已推送GitHub，Mac正式clone快进拉取且工作树干净。本地核对126个发布文件摘要和协议来源，78个主分数/统计复算一致，5个指定完整特征FID/KID在登记数值容差内。详细版本和逐臂误差见本轮MAC_REPLAY.json。该回执不声称重新生成全部图像或执行Mac全套工程门禁；本轮工程门禁在服务器执行。文稿和自查表的Word交付及最终记录闭环HEAD另存Mac交付收据。
