import csv
import hashlib
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path("/home/hugo/codes/flowa-multistep-reinference")
out = root / "verification_outputs/cifar-intermediate-path-20261103-retry1"
result = json.loads((out / "RESULTS.json").read_text())
rows = result["rows"]
assert len(rows) == 36 and result["skipped"] == 0
arms = ["own_source_chord", "independent_source_chord"]
labels = ["原噪声弦线", "独立噪声弦线"]
times = [0.5, 0.7, 0.7 ** (1 / 3)]


def selected(resolution, m, arm):
    return [r for r in rows if r["resolution"] == resolution and r["time"] == m and r["arm"] == arm]


def mean(rs, stage):
    return float(np.mean([x[stage + "_V_MMD2_excess"]["1.0"] for x in rs]))


def mean_sd(rs, stage):
    a = [x[stage + "_V_MMD2_excess"]["1.0"] * 1000 for x in rs]
    return f"{np.mean(a):+.4f} ± {np.std(a, ddof=1):.4f}"


with (out / "ALL36.csv").open("w") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(
        [
            "seed",
            "resolution",
            "m",
            "arm",
            "mid_V_MMD2_excess",
            "end_V_MMD2_excess",
            "paired_boundary_RMS",
            "paired_endpoint_RMS",
            "mid_empirical_W2_RMS_excess",
            "end_empirical_W2_RMS_excess",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["seed"],
                row["resolution"],
                row["time"],
                row["arm"],
                row["intermediate_V_MMD2_excess"]["1.0"],
                row["endpoint_V_MMD2_excess"]["1.0"],
                row["paired_boundary_RMS"],
                row["paired_endpoint_RMS"],
                row["intermediate_empirical_W2_RMS_excess"],
                row["endpoint_empirical_W2_RMS_excess"],
            ]
        )

summary = {}
for stage in ["intermediate", "endpoint"]:
    summary[stage] = {}
    for bandwidth in ["0.5", "1.0", "2.0"]:
        diffs = []
        for resolution in [1, 2]:
            for seed in [201, 202, 203]:
                group = [
                    r
                    for r in rows
                    if r["seed"] == seed and r["resolution"] == resolution and r["time"] == 0.7
                ]
                diffs.append(
                    next(r for r in group if r["arm"] == arms[0])[stage + "_V_MMD2_excess"][
                        bandwidth
                    ]
                    - next(r for r in group if r["arm"] == arms[1])[stage + "_V_MMD2_excess"][
                        bandwidth
                    ]
                )
        summary[stage][bandwidth] = dict(
            own_minus_independent_min=min(diffs),
            max=max(diffs),
            positive=sum(x > 0 for x in diffs),
            total=6,
        )
summary["scope"] = (
    "Descriptive primary-time comparison; six correlated seed-resolution cells, not six independent models or a significance test"
)
(out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")

gaussian = []
for m in times:
    q = np.sqrt(m * m + (1 - m) ** 2)
    gaussian.append(
        dict(
            m=m,
            true_mid_variance=q * q,
            own_chord_variance=1.0,
            independent_chord_variance=q * q,
            own_output_variance=1 / (q * q),
            independent_output_variance=1.0,
            own_paired_boundary_RMS=1 - q,
            independent_paired_boundary_RMS=float(np.sqrt((m - q) ** 2 + (1 - m) ** 2)),
        )
    )
(out / "GAUSSIAN_CALIBRATION.json").write_text(
    json.dumps(
        dict(
            rows=gaussian,
            deterministic=True,
            scope="Classical independent Gaussian RF example; calibration of pathwise versus marginal distinction, not a new theorem or real-model replication",
        ),
        indent=2,
    )
    + "\n"
)

fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), constrained_layout=True)
for ax, stage, title in zip(
    axes,
    ["intermediate", "endpoint"],
    ["Intermediate marginal", "After the same suffix"],
    strict=True,
):
    for index, arm in enumerate(arms):
        for resolution, linestyle, marker in [(1, "--", "o"), (2, "-", "s")]:
            groups = [selected(resolution, m, arm) for m in times]
            means = [mean(g, stage) * 1000 for g in groups]
            sd = [
                np.std([r[stage + "_V_MMD2_excess"]["1.0"] * 1000 for r in g], ddof=1)
                for g in groups
            ]
            ax.errorbar(
                times,
                means,
                yerr=sd,
                color=["#263f73", "#b65b12"][index],
                linestyle=linestyle,
                marker=marker,
                capsize=3,
                label=f"{['Own source', 'Independent source'][index]}, C={64 * resolution}",
            )
    ax.axhline(0, color=".5", linewidth=0.8)
    ax.set(xlabel="Boundary time m", ylabel="Excess pixel RBF V-MMD² × 1000", title=title)
    ax.set_xticks(times, ["0.5", "0.7", "0.887904"])
    ax.grid(alpha=0.15)
axes[0].legend(fontsize=7.5)
figure = root / "docs/figures/review-cifar-intermediate-path-20261103.png"
fig.savefig(figure, dpi=200)
plt.close(fig)

table = "| m | 边界状态 | 中间超额MMD² ×10³ | 终点超额MMD² ×10³ | 边界配对RMS |\n|---|---|---|---|---|\n"
for m in times:
    for arm, label in zip(arms, labels, strict=True):
        group = selected(2, m, arm)
        table += f"| {m:.6f} | {label} | {mean_sd(group, 'intermediate')} | {mean_sd(group, 'endpoint')} | {np.mean([r['paired_boundary_RMS'] for r in group]):.6f} |\n"
main_own = selected(2, 0.7, arms[0])
main_ind = selected(2, 0.7, arms[1])
path_range = [x["coarse_fine_paired_RMS"] for x in result["numerical_resolution_sensitivity"]]
finding = (
    f"在预定主时刻m=0.7，128步分辨率下，原噪声弦线的中间/终点超额MMD²均值分别为"
    f"{mean(main_own, 'intermediate'):+.8f}/{mean(main_own, 'endpoint'):+.8f}；独立噪声弦线为"
    f"{mean(main_ind, 'intermediate'):+.8f}/{mean(main_ind, 'endpoint'):+.8f}。原噪声弦线的边界配对RMS约"
    f"{np.mean([r['paired_boundary_RMS'] for r in main_own]):.6f}，反而小于独立噪声弦线的"
    f"{np.mean([r['paired_boundary_RMS'] for r in main_ind]):.6f}。"
)
protocol_text = """冻结与第V-E节相同的CIFAR-10 1RF EMA检查点，使用新生成种子201/202/203。每种子从先验生成两组各128条轨迹：A组用于干预，独立B组提供分布参照。同一初值在64与128次调用两档下重复使用；物理时间结点固定为0、0.5、0.7、0.7^(1/3)、1，粗档分段步数为[32,13,12,7]，细档逐段加倍。Euler增量使用实际dt，状态不裁剪。本诊断从物理时间0开始，区别于旧质量实验的epsilon时间约定，不作旧分数的直接复现。

在各时刻m，对A组分别采用数值真实状态、mX₁+(1−m)Z₀及mX₁+(1−m)Z′作为后段初值，其中Z₀是同条轨迹原始噪声，Z′为独立高斯噪声。所有臂使用同一冻结模型和同一后段网格。真实状态重放是软件正控制。两种弦线比较只更换边界输入；它们不是与历史完整采样器等总调用的质量比赛。

主时刻预定为m=0.7，其他两时刻为固定对照。主读数为3072维未裁剪像素上的高斯RBF经验V-MMD²，k(x,y)=exp(−||x−y||²/(2d))，d=3072[35]。分别比较干预A组对B组、真实A组对B组；两者之差称超额差异，仅是同规模有限样本参照，不是总体偏差扣除或无偏校正。另报未截零的U-MMD²、预定带宽0.5/2倍、归一化经验Hungarian-W₂及配对RMS。配对距离和经验W₂不替代总体W₂，也不把核距离称为FID/KID或感知质量。全部36个干预单元、18个重放控制及数值精度敏感性完整报告，不作显著性或普遍机制声明。"""
results_text = f"""36个干预单元和18个重放控制全部完成，跳过0。数值真实状态接续后的最大元素误差为0，这是同一离散网格的实现一致性检查，不是精确ODE正确性的独立证明。两档轨迹中间/终点状态的配对RMS差异范围为{min(path_range):.6f}—{max(path_range):.6f}，因此细档也不称无离散误差的真实分布。

{finding}主时刻原噪声弦线的中间和终点超额主指标在六个种子—精度单元均为正；独立噪声弦线则在有限样本参照附近变化，包含正负值。独立臂接近参照不能证明严格目标保持或统计等效。

{table}
表 XV. 细档128次调用数值路径的三生成种子均值±种子间样本标准差。正值表示较真实A对B的有限样本读数更高，负值不是负的MMD或超越真实目标。共享训练权重、种子及两档精度的比较不视为独立模型重复。

![真实模型的中间边缘与接续输出比较](../figures/review-cifar-intermediate-path-20261103.png)

图 10. 三个预定时刻、两档分辨率下的像素核差异。误差线为三个生成种子的一个标准差，不是置信区间。零线表示同规模真实路径参照；虚实线区分64/128次调用，标记与颜色共同区分边界操作。

在主时刻，两种臂的差异方向对三个预定核带宽均保持一致；归一化经验W₂也显示原噪声弦线较参照更远，而独立臂的变化在参照附近。数据支持一个限定判断：在该冻结检查点和数值协议中，沿原耦合构造的弦线可以更靠近逐样本轨迹，却更偏离整体边缘，接续后仍保留分布差异。逐样本接近不构成边缘相容的证书。

这也限制了对第IV-D节的使用：独立训练路径允许原始噪声—生成终点的诱导配对与训练乘积耦合不同，不能由学习端点的有限配对性质推出独立刷新必然失配。新增结果既不认证实际神经流的凸梯度假设或逆Lipschitz界，也不把历史CIFAR质量退化归因于独立刷新。"""

old = root / "docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md"
s = old.read_text().replace("中文修订稿 v8", "中文修订稿 v9", 1)
s = s.replace(
    "12个既有CIFAR操作点未发现有限配对违例，但不能认证实际路径。",
    "12个既有CIFAR操作点未发现有限配对违例；新增真实检查点的三种子、双分辨率边界干预进一步发现，逐样本更接近轨迹的原噪声弦线反而比独立噪声弦线更偏离中间边缘及接续终点。该发现限于指定像素指标与数值协议，独立臂接近参照不等于目标保持已被证明。",
    1,
)
s = s.replace(
    "本文的实证结论包括局部收益、作用反向和迁移退化",
    "新增真实中间轨迹干预将逐样本路径接近与边缘相容分开检验。本文的实证结论包括局部收益、作用反向和迁移退化",
    1,
)
point = s.index("### C. 质量—计算量前沿")
s = (
    s[:point]
    + """近期CMM以累计边缘差异构造少步模型训练目标[33]；CorrFlow训练利用冻结基模型表征的残差修正器，并分析修正后的部署状态分布[34]。前者已明确研究中间边缘，后者已把轨迹变化纳入修正分析，因此“关注中间状态”并非本文独有。本文不训练新模型，新增的是同一冻结检查点下将真实轨迹、原噪声弦线与独立噪声弦线置于相同后段网格的边界干预。它用于检验假设对应，不宣称在共同基准上优于这两套系统；两项2026预印本的结论亦不写为同行评议定论。

"""
    + s[point:]
)
point = s.index("## VI. 结果")
s = s[:point] + "### I. 真实模型中间路径与边界干预\n\n" + protocol_text + "\n\n" + s[point:]
point = s.index("## 附录 A.")
head, tail = s[:point], s[point:]
for a, b in [("XIX", "XX"), ("XVIII", "XIX"), ("XVII", "XVIII"), ("XVI", "XVII"), ("XV", "XVI")]:
    tail = re.sub(r"表( ?)" + a + r"(?![IVX])", lambda m, b=b: "表" + m[1] + "TEMP" + b, tail)
s = head + tail.replace("TEMP", "")
point = s.index("## VII. 讨论")
s = s[:point] + "### L. 真实路径与边界输入的受控验证\n\n" + results_text + "\n\n" + s[point:]
s = s.replace(
    "当前缓存缺少实际中间状态，也就不能用端点的弦上分布替代模型的中间边缘来解释独立实验。",
    "旧端点缓存缺少中间状态；第VI-L节已补充真实模型的数值中间轨迹与边界干预。原噪声弦线虽更接近逐样本路径，却更偏离经验边缘；独立臂接近参照则提醒我们不能由一般路径反例推断独立训练模型必然失配。",
)
s = s.replace(
    "本研究的光滑高斯路径控制已完成解析区分；下一步需要预先锁定真实中间轨迹的采集、独立模型和等调用干预，并检验这种区分是否在非高斯模型上保留。",
    "光滑高斯控制和一个真实CIFAR检查点上的预定边界干预已完成这种区分。下一步仍需独立训练检查点或模型家族、预先锁定的诊断决策，以及在匹配总调用下检验实际质量收益。当前固定m的比较没有给出部署选择规则，三个生成种子和两档精度不能替代外部预测验证。",
)
s = s.replace(
    "这些结果支持按具体训练路径、边界核、数值实现和评价对象检验再推理操作",
    "真实模型的中间路径干预进一步表明，逐样本轨迹接近和分布相容可能给出不同判断，独立刷新也不能因一般耦合反例而被笼统判为有害。这些结果支持按具体训练路径、边界核、数值实现和评价对象检验再推理操作",
    1,
)
s = s.replace(
    "本轮解析控制的程序实现、数值核对与图表整理也使用该工具辅助。",
    "解析控制和本轮真实模型诊断的程序实现、数值核对与图表整理也使用该工具辅助。",
)
body, rest = s.split("## 参考文献", 1)
refs, internal = rest.split("## 内部复现索引", 1)
entries = dict(re.findall(r"^\[(\d+)\] (.+)$", refs, re.M))
entries.update(
    {
        "33": "P. Regmi and R. Li, “Cumulative Marginal Matching for One-Step Diffusion,” arXiv:2610.34575v2, 2026. https://arxiv.org/abs/2610.34575v2",
        "34": "H. Zhang, N. Rouillé, and C. Zheng, “CorrFlow: Self-Correcting Flow Matching,” arXiv:2610.24750v1, 2026. https://arxiv.org/abs/2610.24750v1",
        "35": "A. Gretton et al., “A Kernel Two-Sample Test,” Journal of Machine Learning Research, vol. 13, pp. 723–773, 2012. https://www.jmlr.org/papers/v13/gretton12a.html",
    }
)
order = list(dict.fromkeys(re.findall(r"\[(\d+)\]", body)))
assert set(order) == set(entries)
mapping = {k: str(i + 1) for i, k in enumerate(order)}
body = re.sub(r"\[(\d+)\]", lambda m: "[" + mapping[m[1]] + "]", body)
s = (
    body
    + "## 参考文献\n\n"
    + "\n\n".join("[" + mapping[k] + "] " + entries[k] for k in order)
    + "\n\n## 内部复现索引"
    + internal
)
s += "\n第十轮真实中间路径证据：verification_outputs/cifar-intermediate-path-20261103-retry1/，源码tools/sweep_cifar_intermediate_20261103.py，记录docs/audit/manuscript-intermediate-round10-2026-11-03.md。基准提交05f608dd3d245fdf7c213734359e3edff069f02a；本轮保守GPU总核算7158/7200秒，含失败重跑。\n"
target = root / "docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md"
target.write_text(s)
(out / "CITATION_MAPPING.json").write_text(json.dumps(mapping, indent=2) + "\n")


def normalize(t):
    return re.sub(r"\[\d+\]", "[REF]", t)


oldtables = re.findall(r"^\|.*(?:\n\|.*)*", old.read_text(), re.M)
newtables = re.findall(r"^\|.*(?:\n\|.*)*", s, re.M)
assert len(oldtables) == 20 and len(newtables) == 21
assert all(normalize(t) in [normalize(n) for n in newtables] for t in oldtables)
inventory = dict(
    original_20_tables_preserved_except_citation_labels=True,
    table_objects=21,
    numbered_tables=20,
    figures=10,
    references=35,
    source_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
)
(out / "MANUSCRIPT_INVENTORY.json").write_text(json.dumps(inventory, indent=2) + "\n")

audit = f"""# 真实模型中间路径验证与原创贡献核查

日期为2026年11月3日，基准提交05f608dd3d245fdf7c213734359e3edff069f02a。新增证据把逐样本轨迹接近与中间边缘相容区分开：在一个真实CIFAR-10 1RF检查点上，保留原噪声的弦线比独立噪声弦线更贴近样本轨迹，却在预定主时刻呈现更高的中间和接续终点分布差异。本轮没有得到新采样算法或总体质量收益，原创充分性仍待评估。

## 实验对象与固定协议

{protocol_text.replace("[35]", "（Gretton等，2012）")}

环境为服务器flowmol3_venv，Python3.12.13、Torch2.7.0+cu128，物理GPU0为RTX PRO 6000 Blackwell。权重SHA-256为c29936c219f34800131c07b81a8da4862b0c0b6f4e5e50efea267d24eef1f2ec，沿用已核对官方EMA及前向一致性的检查点与加载器。相同训练权重并非多个独立训练重复。所有新实验配置均在任何真实模型生成前保存在本地协议文件；CPU单元测试先行，未进行公共预注册。

## 观察结果

{results_text.split(table)[0]}
{table}
细档结果为三种子均值±一个种子间样本标准差，非置信区间。全36单元CSV与JSON包括不利和负的超额读数，未按结果挑选时间、种子或核带宽。

![真实模型的中间边缘与接续输出比较](../figures/review-cifar-intermediate-path-20261103.png)

原噪声臂在主时刻的中间/终点超额MMD²于两精度、三种子均为正；三种预定带宽下，原噪声臂减独立臂均为正。归一化经验W₂呈现相同方向，原噪声臂较真实A对B的中间RMS距离高约0.029—0.032，接续终点高约0.053—0.056。独立臂在有限样本参照附近，不能据此主张严格不变性、等效、总体W₂证书或质量改善。

## 解释与可证伪边界

配对RMS衡量某条轨迹的移动，MMD比较整体边缘；二者的对象不同。独立训练路径在理想情形允许新独立噪声重建正确中间边缘，并不要求每条学习轨迹是直线。一个经典高斯校准已经体现这种区别：先验和目标均为N(0,1)，真实中间标准差qₘ=√(m²+(1−m)²)。m=0.5时，原噪声弦线配对RMS为0.292893，小于独立弦线的0.541196；但前者接续输出方差为2，后者为1。该解析校准不是新定理，逐时刻数值另有JSON记录。

新增真实模型数据与上述对象区分一致，不能把凸梯度直线路径的刷新障碍直接移用于独立训练的1RF，也不能据本轮单边界、无质心、物理时间诊断追认旧四轮CIFAR质量退化的原因。若未来外部模型上的预定诊断不能区分结果，或诊断指导动作没有匹配总调用的质量收益，应拒绝更强的机制和算法贡献主张。当前完成的是同一冻结模型下替换边界状态的受控干预，不是前瞻性诊断选择或外部泛化试验。

## 原创贡献与已有工作的对应

| 对象 | 已有基础 | 本轮增量与尚缺证据 |
|---|---|---|
| 再噪声后继续流映射 | Diamond Maps、Restart已有直接操作 | 不作为独有算法；未取得新质量优势 |
| 凸梯度成本差与传播界 | 经典OT、Bregman与Lipschitz推前 | 保留条件推导，不作为独有数学工具 |
| 端点不可区分构造 | 随机插值已有路径自由度 | 指定刷新核的显式反例；充分新颖性仍待逐命题评估 |
| 中间边缘匹配 | CMM已有累计边缘训练目标 | 冻结检查点边界替换与训练蒸馏不同；关注边缘本身不是首次 |
| 修正后的部署状态 | CorrFlow训练表征残差修正器并分析部署分布 | 本轮不训练修正器，只检验固定边界状态；未作共同基准优越性比较 |
| 路径接近与边缘相容 | RF及核双样本理论已有基础 | 新增真实模型三种子、双精度、同后段干预证据；尚缺训练重复、独立模型和可部署决策 |

CMM与CorrFlow均为2026年预印本，未视作同行评议定论。按现有证据，最稳妥的贡献表述是：围绕固定端点边界核给出条件与反例，并以真实模型验证逐样本接近不足以判定边缘相容。不使用“首次提出中间边缘诊断”“刷新必然有害”或“已达到硬一区标准”的表述。SC-04/05仍保留EVIDENCE_GAP，SC-41仍需修订；不以完成实验自动抬高新颖性状态。

## 运行故障与预算记录

首次运行已完成首种子粗档，写索引时因相对路径对绝对根目录调用relative_to而失败。原脚本、日志、协议、已生成原始文件均保留，未纳入科学分析。修复仅涉及索引路径解析及正确记录外层时限，数学、网格、种子、指标不变；新目录重新执行全部单元，无择优复用。失败耗时37.780690秒、成功重跑161.458738秒，合计199.239428秒GPU承载进程墙钟。保守核算分别计40和480秒，既有6638秒加本轮520秒为7158/7200秒；原失败记录的500秒是未耗尽的硬上限预留，释放说明与原记录一并留存，不将失败时间抹去。此后分析全部使用CPU，耗时{result["CPU_wall_seconds"]:.6f}秒，跳过0。

## 文稿 证据与后续验收

中文v9新增协议V-I、结果VI-L、图10和表XV，修正讨论与结论；旧20个表格对象与9幅图保留，科学数值不改。共21个表格对象、20张编号表、10幅图、35条文献。正式英文篇幅和匿名材料仍待编排。完整45项自查表保留历史；本轮真实干预不抵扣独立原创性或外部验证缺口。

协议、元数据、逐单元分数、逐批实际调用、故障说明、保守预算和完整原始数据摘要见本轮版本化材料。大型原始快照保留在研究服务器，并在代码和记录经GitHub同步后另存Mac以便CPU复算，不把文件存在称为全部科学假设成立。4项聚焦测试、24项项目检查和72个回归向量的结果以CHECKS.json为准，包含历史非致命警告。

## 原始来源

CMM的定义与累计边缘目标见https://arxiv.org/html/2610.34575 ，版本v2、2026年10月30日。CorrFlow的残差修正与部署分析见https://arxiv.org/html/2610.24750 ，版本v1、2026年10月17日。核双样本统计来源为https://www.jmlr.org/papers/v13/gretton12a.html 。RF原作者对训练插值与模型轨迹边缘的说明见https://www.cs.utexas.edu/~lqiang/rectflow/html/intro.html 。上述来源于本轮直接读取，用于界定方法归属，不从未发现相同句式推断首次性。
"""
# The audit uses a figure relative to docs/audit, as does the manuscript's docs/drafts location.
audit_path = root / "docs/audit/manuscript-intermediate-round10-2026-11-03.md"
audit_path.write_text(audit)
(out / "LITERATURE.json").write_text(
    json.dumps(
        dict(
            checked_date="2026-11-03",
            sources=[
                dict(
                    url="https://arxiv.org/html/2610.34575",
                    version="v2",
                    distinction="Training cumulative marginals, not this frozen boundary-state intervention",
                ),
                dict(
                    url="https://arxiv.org/html/2610.24750",
                    version="v1",
                    distinction="Trained refiner and deployment-law analysis, no common-benchmark superiority claimed",
                ),
                dict(
                    url="https://www.jmlr.org/papers/v13/gretton12a.html",
                    distinction="Existing MMD statistic, not a novel metric",
                ),
                dict(
                    url="https://www.cs.utexas.edu/~lqiang/rectflow/html/intro.html",
                    distinction="Training interpolation marginals versus learned endpoint coupling",
                ),
            ],
        ),
        indent=2,
    )
    + "\n"
)
print(inventory)
