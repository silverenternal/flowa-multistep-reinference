import hashlib
import json
import re
from pathlib import Path

r = Path("/home/hugo/codes/flowa-multistep-reinference")
old = r / "docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md"
s = old.read_text().replace(
    "本版在基准提交29da2565af30a3829aa1a44ca6a6682f4c150e10上重组正文；修订记录见 docs/audit/manuscript-rewrite-round8-2026-11-03.md。",
    "本版在基准提交a80acdda4a4f0ca6bf2edbc859481c6323bd0d4c上补充路径可识别性分析；修订记录见 docs/audit/manuscript-supplement-round9-2026-11-03.md。",
)
s = s.replace("中文修订稿 v7", "中文修订稿 v8", 1)
s = s.replace(
    "12个既有CIFAR操作点的有限端点配对检查未发现违例，但不能认证全局输运结构。",
    "进一步构造端点映射完全相同的光滑流，证明固定的端点刷新仍可产生任意正的高斯输出尺度；36个CPU控制验证了端点诊断与真实中间边缘的区别。12个既有CIFAR操作点未发现有限配对违例，但不能认证实际路径。",
    1,
)
s = s.replace(
    "并用既有端点缓存检查一项理论必要条件。",
    "并用既有端点缓存检查一项理论必要条件；端点不可区分的光滑流反例进一步说明，端点配对信息不能替代中间边缘观测。",
    1,
)
start = s.index("### G. 与经验诊断和评价指标的区别")
s = (
    s[:start]
    + """### G. 端点诊断的可识别性与中间边缘

端点配对检查只约束一项映射。即使知道完整的端点映射，而不只是有限样本，通常仍不能恢复路径的全部中间边缘。随机插值框架本就允许在给定两端分布后设计不同路径[22]；下面将这一已知自由度具体用于端点刷新问题，给出可直接核验的不可区分构造。

**命题2（端点信息的不足）。** 固定0<m<1，先验与目标均为二维标准高斯。存在一族全局光滑、可逆的确定性流，所有成员均具有Φ₀=Φ₁=I及相同的端点联合分布Law(Z,Z)，但对同一独立刷新W′=mX+(1−m)Z′、X=Φ₁(Z)，其精确后段输出可以为N(0,σ²I₂)，其中σ为任意给定正数。

证明：令c=m²+(1−m)²，qₛ=exp(a sin(πs))、θₛ=b sin(πs)，Φₛ(z)=qₛR(θₛ)z；R为二维旋转，b为任意固定实数。q₀=q₁=1，θ₀=θ₁=0，因此端点映射恒为I。这是速度场vₛ(x)=πcos(πs)(aI+bJ)x的精确流，J为90度旋转矩阵，所有时刻qₛ>0。取a=log(√c/σ)/sin(πm)，则真实中间边缘为N(0,qₘ²I₂)，而重组状态为N(0,cI₂)。精确后段映射为Φ₁∘Φₘ⁻¹=qₘ⁻¹R(−θₘ)，故

Cov(Y) = (c/qₘ²)I₂ = σ²I₂。                              (9)

当σ<1、σ=1及σ>1时分别收缩、保持及膨胀。所有成员的端点样本和全局端点配对成本完全相同，因此任何只读取这些端点信息的规则都无法在该流族上判定刷新是否保持目标。此结论不假设这些成员来自相同的独立直线训练路径；已知训练概率路径时，可以排除不相容的成员。它也不把一般路径非唯一性作为首次发现。

中间边缘则包含这一构造中缺少的信息。设rₘ为重组分布，μₘ为真实中间分布，F为把μₘ推至μ的精确可逆后段映射。若F与F⁻¹的Lipschitz上界分别为L和L⁻，且相关分布具有有限二阶矩，记dₘ=W₂(rₘ,μₘ)，则标准推前不等式给出

dₘ/L⁻ ≤ W₂(F#rₘ,μ) ≤ Ldₘ。                              (10)

上界直接对F使用Lipschitz推前性质；下界对F⁻¹使用同一性质。可逆性还给出F#rₘ=μ当且仅当rₘ=μₘ。在命题2的高斯流族中，两侧均精确等于dₘ/qₘ，因此既有保持例子，也有尺度可计算的失配例子。式（10）是经典距离传播的推论，不承担独有理论工具主张。实际神经流的逆映射界尚未认证，不能将该式升级为FID/KID证书。

命题2说明端点信息不足以识别一般边界核的正确性；式（10）解释了测量真实中间边缘的必要作用。二者为第VI-J节有限缓存检查提供适用边界，也为后续诊断提出要求：区分真实轨迹边缘与端点直线插值边缘，再检验预定干预的作用，而不是从未发现端点违例直接推断实际刷新无偏。

"""
    + s[start:].replace("### G. 与经验诊断和评价指标的区别", "### H. 与经验诊断和评价指标的区别", 1)
)
pos = s.index("## VI. 结果")
s = (
    s[:pos]
    + """### H. 端点不可区分流的CPU控制

固定二维标准高斯，m∈{0.2,0.5,0.8}、σ∈{0.5,1,2}、b∈{0,0.7}及源相关系数ρ∈{0,0.7}，共36个确定性案例。ρ=0对应命题2的独立刷新；ρ=0.7仅为保持高斯源边缘的相关刷新控制，此时c改为m²+(1−m)²+2m(1−m)ρ。所有配置在单元预检查后按同一固定网格保存并正式执行，不作公共预注册或确认性推断。

独立DOP853数值求解器积分速度场的矩阵基本解，与解析Φₛ比较；数值后段矩阵进一步给出输出协方差。W₂由协方差特征值计算，与中间距离的缩放关系核对。五个固定源点的完整指派用于验证端点诊断输入相同，不是分布质量抽样。计算仅使用NumPy/SciPy，未加载神经检查点。

"""
    + s[pos:]
)
pos = s.index("## VII. 讨论")
s = (
    s[:pos]
    + """### K. 端点不可区分的路径控制

36个案例全部完成，无跳过，收缩、保持和膨胀控制各12个；ρ=0的独立刷新子集为18个。数值全程映射与I的最大元素误差小于3.3×10⁻¹¹，后段矩阵误差小于4.3×10⁻¹¹，输出协方差误差小于1.5×10⁻¹⁰，W₂缩放关系误差小于7×10⁻¹⁶。固定源点的端点指派改善在全部案例中均为零。表XIV给出m=0.5、ρ=0、b=0.7的预定切片。

| 输出标准差σ | 真实中间标准差qₘ | 每维输出方差 | 中间W₂差dₘ | 输出W₂差 | 端点指派改善 |
|---|---|---|---|---|---|
| 0.5 | 1.414214 | 0.25 | 1.000000 | 0.707107 | 0 |
| 1.0 | 0.707107 | 1.00 | 0.000000 | 0.000000 | 0 |
| 2.0 | 0.353553 | 4.00 | 0.500000 | 1.414214 | 0 |

表 XIV. 同一端点映射、相同刷新操作下的精确高斯控制。零值按数值容差显示。三行不是独立模型重复，也不是图像质量结果；全部36例和容差检查另附可复算记录。

![端点信息相同而路径边缘与刷新输出不同](../figures/review-path-identifiability-20261103.png)

图 9. 左侧为三条真实中间标准差曲线及独立端点弦线的标准差；两端均为1。右侧为相同m=0.5独立刷新后的输出方差，目标为1。线型和标记区分不同流，颜色不承担唯一辨识作用。

本控制识别的是理论对象之间的区别：相同端点配对不足以区分三种输出，而真实中间边缘差异能够在这个指定流族上刻画偏差。它没有检验实际CIFAR检查点，也没有验证该诊断在非高斯神经流上的预测能力。其价值在于排除把端点成本当作一般正确性证书的推理，并为后续真实轨迹研究提供必须通过的解析控制。

"""
    + s[pos:]
)
# The new table precedes the appendix; shift only old appendix caption labels/references.
pos = s.index("## 附录 A.")
front, appendix = s[:pos], s[pos:]
for before, after in [
    ("XVIII", "XIX"),
    ("XVII", "XVIII"),
    ("XVI", "XVII"),
    ("XV", "XVI"),
    ("XIV", "XV"),
]:
    appendix = re.sub(
        r"表( ?)" + before + r"(?![IVX])",
        lambda m, after=after: "表" + m[1] + "TEMP" + after,
        appendix,
    )
s = front + appendix.replace("TEMP", "")
s = s.replace(
    "首先应在可解析的曲线路径上验证诊断的区分能力，再预先锁定独立模型和等调用干预。",
    "本研究的光滑高斯路径控制已完成解析区分；下一步需要预先锁定真实中间轨迹的采集、独立模型和等调用干预，并检验这种区分是否在非高斯模型上保留。",
)
s = s.replace(
    "有限缓存检查未检出配对违例，也未认证实际路径条件。",
    "端点不可区分的光滑流控制说明相同端点映射可对应不同刷新偏差；有限缓存检查未检出配对违例，也未认证实际路径条件。",
)
pos = s.index("## 参考文献")
s = (
    s[:pos]
    + """## 致谢与AI辅助使用说明

本文中文稿的摘要、引言、方法与相关工作说明、理论推导说明、结果叙述及讨论使用OpenAI Codex辅助组织和生成[32]。本轮解析控制的程序实现、数值核对与图表整理也使用该工具辅助。AI不列为作者；最终文本、程序与科学结论的核验及责任由作者承担。

"""
    + s[pos:]
)
pos = s.index("## 内部复现索引")
s = (
    s[:pos]
    + "[32] OpenAI, “Codex,” AI-assisted writing and derivation organization tool, accessed Nov. 3, 2026. https://openai.com/codex/\n\n"
    + s[pos:]
)
s += "\n第九轮新增路径可识别性控制对应 tools/review_path_identifiability_20261103.py、verification_outputs/path-identifiability-20261103/{METADATA.json,RESULTS.json} 及 docs/audit/manuscript-supplement-round9-2026-11-03.md。当前作者须知核对见 docs/audit/tnnls-author-requirements-2026-11-03.md。\n"
# IEEE references in order of first appearance. Expand ranges before relabeling.
body, refs = s.split("## 参考文献", 1)
ref_text, index = refs.split("## 内部复现索引", 1)
entries = dict(re.findall(r"^\[(\d+)\] (.+)$", ref_text, re.M))
body = re.sub(
    r"\[(\d+)\][–−-]\[(\d+)\]",
    lambda m: ",".join("[" + str(i) + "]" for i in range(int(m[1]), int(m[2]) + 1)),
    body,
)
order = list(dict.fromkeys(re.findall(r"\[(\d+)\]", body)))
assert set(order) == set(entries), (set(entries) - set(order), set(order) - set(entries))
mapping = {old: str(i + 1) for i, old in enumerate(order)}
body = re.sub(r"\[(\d+)\]", lambda m: "[" + mapping[m[1]] + "]", body)
new_refs = "\n\n".join("[" + mapping[old] + "] " + entries[old] for old in order)
s = body + "## 参考文献\n\n" + new_refs + "\n\n## 内部复现索引" + index
path = r / "docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md"
path.write_text(s)
out = r / "verification_outputs/path-identifiability-20261103"
(out / "CITATION_MAPPING.json").write_text(json.dumps(mapping, indent=2) + "\n")
original_tables = re.findall(r"^\|.*(?:\n\|.*)*", old.read_text(), re.M)
new_tables = re.findall(r"^\|.*(?:\n\|.*)*", s, re.M)


def no_citations(table):
    return re.sub(r"\[\d+\]", "[REF]", table)


assert all(
    no_citations(table) in [no_citations(t) for t in new_tables] for table in original_tables
)
assert len(original_tables) == 19 and len(new_tables) == 20
inventory = dict(
    base_commit="a80acdda4a4f0ca6bf2edbc859481c6323bd0d4c",
    original_table_objects_preserved_except_citation_labels=19,
    table_objects=20,
    numbered_tables=19,
    figures=9,
    references=32,
    original_result_values_unchanged=True,
    GPU_added_seconds=0,
    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
)
(out / "MANUSCRIPT_INVENTORY.json").write_text(json.dumps(inventory, indent=2) + "\n")
print(inventory)
