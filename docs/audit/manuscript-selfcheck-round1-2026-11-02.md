# 投稿自查首轮：源码对齐、统计修正与中文稿 v2

**日期：** 2026-11-02；**基准提交：** 86dab3a8e2ac7cab9e50901d99328fd12b95115d。
**范围：** 现有源码和artifact复核、派生统计修正、新中文工作稿。未训练、未采样、未覆盖原始实验和冻结投稿包。

## 1. 观察事实与修改

1. MNIST的两个RK4后端每步四次速度场调用。旧nfe字段为步数S，新图/稿使用C=4S。比较臂求解器相同时相对预算匹配保持；不把其他模型套入此换算。源码：scripts/wave191_p3_mnist_sweep.py 的 run_baseline / run_framework_arm；adaptive_reflow/adapters/mnist_fm.py 的 _integrate_rk4 / solve_ode；adaptive_reflow/adapters/mnist_fm_torch.py 的 integrate_rk4。
2. 当前主实例包含equal_budget beta、memory时间起点、每轮两步的轮数限制及mean_preserve总体平移。采样驱动提前生成调度权重，未调用record_round_feedback。新稿不宣称主曲线已验证在线自适应。
3. tools/gap91_holdout.py 对四训练点回归使用df=2但误置t=2.776（df=4）。改为4.302652729749464；NIST表0.975/df=2为4.303。点估计和原始样本不变。
4. 新回归测试以已知OLS样本x=(0,1,2,3)、y=(1,2,2,5)及x*=1.5检验95%预测区间，修复前失败（下界-0.444），修复后通过（下界-2.064）。这是覆盖率口径的回归保护，未依赖模型权重。
5. 先前公开副本只有一个当前MNIST前沿report。补入服务器现存的四检查点及新增两检查点规范化输入/报告，让新图和回归读取版本控制中的同源数据。该补充不代表原始运行全部公开。
6. R2汇总文件指向的baseline原始JSON verification_outputs/wave218-p3-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json 在服务器不存在；无法独立重建原检验。新稿保留方向读数，暂不将其显著性作为独立主证据。

## 2. 派生复核（无新采样）

N=1000/arm/seed，生成seeds=42/43/44；低预算使用当前cap输入。原四点主要CPU NumPy；GAP-90主要Torch float64/cuda:0，最低档cap重算CPU。源参数、原始/修正区别见 docs/audit/gap90-optsteps-dose.md。

| checkpoint | baseline | framework | delta | verdict |
|---|---:|---:|---:|---|
| w16e1_5k | 24.483877760641 | 21.363228547493 | -3.120649213148 | WIN |
| w16e1_10k | 16.953746145798 | 15.950122708817 | -1.003623436982 | TIE |
| w16e1_60k | 11.379498350658 | 11.394493319567 | 0.014994968908 | TIE |
| epochs2 | 11.447843468495 | 11.444124977945 | -0.003718490550 | TIE |
| production | 9.993808898502 | 9.960306662613 | -0.033502235889 | TIE |
| w8e3 | 12.003195563633 | 11.767167368873 | -0.236028194760 | TIE |

修正后的四点斜率95%区间：[0.663456855980, 0.897439934961]。两拟合外检查点预测区间：

- epochs2: [9.774319448278, 12.918313084934]；点误差 -0.097808711339。
- w8e3: [10.227093312325, 13.332386524031]；点误差 0.012572549305。

关系仍是事后家族内插值，不满足跨家族预测验收。历史审计中的较窄区间不删除；本记录与新稿明确取代其区间口径。Kanzi未生成替代p值，不能用另一个历史baseline冒充缺失来源。

## 3. 稿件改进与仍未解决项

新稿：docs/drafts/paper-A-zh-reviewed-2026-11-02.md。补充六检查点、三条受控轴、经验κ与理论mK区别、回归自由度修正；主方法定义与实际执行对应。经典命题明确为辅助性质，不主张新的普适理论。

仍需：最近邻方法数值对照；完整组件归因；R2原始来源；逐任务统计家族；上游模型/指标引用；匿名补充。源码可确认实现，不能单独证明新颖性、因果效力与外部有效性。未把这些问题转成未经授权的长时GPU实验。

## 4. 状态与复现

{"RECORDED": 0, "EVIDENCE_LOCATED": 10, "VERIFIED": 22, "REVISION_NEEDED": 9, "EVIDENCE_GAP": 4}

派生结果与SHA-256在 verification_outputs/manuscript-selfcheck-round1-2026-11-02/derived_review.json；回归原输出在同目录 corrected_gap91_output.txt。

复算：python3 tools/gap91_holdout.py；绘图：python3 tools/render_review_figures_20261102.py。

验证结果将追加在下一节；生成时尚未把工程通过等同为科学验收。

参考：NIST Critical Values of Student t，https://itl.nist.gov/div898/handbook/eda/section3/eda3672.htm （访问2026-11-02）。

## 5. 验证与实际范围

- 35项定向测试通过，覆盖新回归区间测试、前沿判定/输入及现有provenance测试；新回归测试先失败后通过。
- 72个D.4/adapter回归向量通过；四目录Ruff通过；指定环境类型检查通过；就绪检查为READY。
- todo.json的24项门禁全部执行。初次有一个文档链接误识别：公式的方括号后接括号被当作链接；改用不歧义的公式记号后，链接检查通过。系统Python下anchor检查曾跳过，指定文档环境重跑后101个片段链接通过。
- 严格MkDocs构建通过；138行metric ledger生成与check一致；投稿包/原有图表/原始校验和未改动且检查通过。
- 保留已有披露：ledger生成器有6条非致命旧状态解析消息；链接检查报告2条历史broken及1条ambiguous、1条archived，按现有规则不阻断。不是所有历史记录完美的声明。
- 本轮没有跑完整pytest执行，仅执行35项定向测试、72个回归向量及门禁要求的全测试收集。不把收集通过写成全套执行通过。

完整初次/修正后输出尾部在 verification_outputs/manuscript-selfcheck-round1-2026-11-02/checks.json。工程检查不代表缺失的Kanzi原始文件已恢复，也不代表所有审稿问题已解决。
