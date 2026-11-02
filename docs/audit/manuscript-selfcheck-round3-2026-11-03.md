# 投稿自查第三轮：敏感性、单位与方法定义纠正

日期：2026-11-03；基准提交b6bb14518dbf2eb8085ecf7c26fc85bee0d2e982。延续用户按自查表优化；沿项目研究审计→论文证据技能顺序。无新训练/采样，上游与冻结投稿包不变。中文v3保留，新增v4。

## 1. 观察到的实现与前稿纠正

`effective_rounds`只计算R=min(R_requested,max(1,S//h))，h历史命名min_steps_per_round。随后`per_round_num_steps_equal_budget`将权重交给分配器，其正整数保证为至少一步，不是每轮h步。例：S50、R4的evidence_driven分配[25,18,6,1]；R12/S25也存在一步轮次。前稿把h=2写为每轮至少两步，属于本次审计纠正的错误。

本轮只修正`scripts/wave191_p3_mnist_sweep.py`的docstring、CLI help和相邻注释；运行算法与默认参数不改。中文v4方法、算法表和消融说明同步更正；旧稿和历史记录不重写。

## 2. 已有39次运行重算

来源：`verification_outputs/gap93-beta-dose/`24个运行汇总、`verification_outputs/gap84c-round-dose/`15个汇总。每臂1000，种子标签42/43/44，production检查点，主比较臂evidence_driven；三个调度臂均进入机器报告。

新工具`tools/review_mnist_sensitivity_20261103.py`核对每组种子标签、N、检查点sha、特征定义、累计beta与每轮beta、步数分配长度/总和/正整数。以种子整批headline计算差值和df2的t区间，拒绝缺种子、重复种子、混协议和非有限结果。分组内协议检查不等于完全历史manifest。输出：`verification_outputs/manuscript-selfcheck-round3-2026-11-03/sensitivity.json`。

- β扫描：R4/S50，β=.15/.30/.50/.70，Δ依次−.024038/−.036420/+.108633/+.572879。
- 平台：只有β=.15与.70在S100/200新测，Δ平台均值约−.022088与+.576329；β=.30沿用主前沿−.0335，β=.50平台未测。不能说四个β都测了平台，也不能把局部结果提升为全局最优或κ因果证明。
- 轮数：S25、β=.3，R2/4/6/8/12，Δ依次+.149415/−.040655/−.063443/−.064169/−.029554；evidence_driven在R≥4跨度约.034615。轮数与重启比例、分配共同变化，不能当纯轮数效应。
- 区间均为探索性，未校正多个参数/臂选择。三个生成种子不等于3000次独立运行。仅production，不外推获益检查点。

## 3. 百分比与绝对量混用的定位

`tools/gap78_r5c_report.py`73行将每种子差值除baseline乘100得到headline_delta；74行另存绝对headline_delta_units。旧报告`verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json`中production/evidence_driven的headline_mean=−.36478555实际是百分比，delta_units_mean=−.036420268。

旧GAP93说明把−.3648标作ΔFID，并引用其百分比区间[−.72365,−.00592]；这不能按绝对单位读。原始报告的绝对区间[−.07205057,−.00078997]与新复算一致。v4按绝对量展示，不修改原报告。这是单位标注问题，不是新旧模型表现变化。

## 4. 来源、局限与主要文献

本轮把39个summary及METADATA/jobs等54个小文件按原字节纳入Git，来源sha清单在同目录`source_manifest.json`。目录和jobs给出种子标签；某些summary没有seed字段、beta_framework遗留.5而beta_total为实际.3、sweep_command仍是模板。不能据模板重建精确执行命令或历史执行源码提交。因此SC24仍保留证据缺口，不用当前源码替代执行时manifest。

主要文献、指标到源码的对应新增于`docs/audit/manuscript-literature-ledger-2026-11-03.md`，中文引用扩至19项。直接讨论原Restart与LineageFlow rerouting，明确没有匹配数值对照。Kanzi作者/年份按原始论文纠正，不沿用旧JSON的Shah标签。

分子metric实际all-metrics调用路径与独立xtb helper不同；精确PB检查集合与逐分子verdict仍缺。补引文不提高证据等级。

## 5. 剩余优先级

主参数下完整组件矩阵、原Restart/同生成器rerouting的匹配对照、独立模型家族前沿仍缺。已测参数敏感性与准确书目让这些问题更可辨，不能替代缺失实验。自查表45项全部保留，所有状态变化注明范围并追加历史。

## 6. 验证

50项定向测试通过（含5项新增区间/分组异常检查与既有round-cap测试）。初次为缩短检查而设置OPENBLAS_NUM_THREADS=1、OMP_NUM_THREADS=1，导致Lumina逐字节回归1失败/71通过；未改回归基准。恢复项目原环境后，单项Lumina先复核1通过（45.67s），再执行readiness、全部72个D4/adapter及ledger检查，均通过。24项门禁中的两项初次失败由对应标准环境复核闭合，其余均通过；所有初次/复核输出保留。系统Python的anchor检查跳过，另在文档环境执行通过。全测试只做收集，未声称全套执行。

额外比较驱动源码AST：去掉函数docstring和argparse帮助字符串后，与基准完全一致；记录于driver_semantics_check.json。这支持“实际采样计算不变”的范围陈述，不证明算法科学效力。完整检查尾部见同目录checks.json。

旧ledger仍有6条非致命状态解析消息；旧链接检查仍披露2条broken、1条ambiguous和1条archived，按现有规则不阻断。工程检查不是科学有效性验收。Word由GitHub拉取到Mac的相同提交导出，输出检查单独记录在Mac收据。
