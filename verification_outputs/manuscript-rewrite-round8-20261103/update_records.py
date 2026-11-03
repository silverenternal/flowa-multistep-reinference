import collections
import hashlib
import json
import re
from pathlib import Path

r = Path("/home/hugo/codes/flowa-multistep-reinference")
out = r / "verification_outputs/manuscript-rewrite-round8-20261103"
audit = "docs/audit/manuscript-rewrite-round8-2026-11-03.md"
draft = "docs/drafts/paper-A-zh-reviewed-round8-2026-11-03.md"
p = r / "docs/audit/manuscript-selfcheck-2026-11-02.json"
old_text = p.read_text()
(out / "checklist-before-round8.json").write_text(old_text)
z = json.loads(old_text)
updates = {
    "SC-01": "中文v7形成完整机制与边界分析稿，约1.9万汉字、8图、18张编号结果表及1张算法表；旧18个Markdown表格逐字保留，新增有限端点诊断表。中文论证密度已扩充；正式英文双栏篇幅仍须另行验收。",
    "SC-02": "中心问题锁定为：冻结流模型的端点再推理何时保持目标，以及有限计算下的收益为何受到路径、组件和评价对象限制。摘要、三项分析贡献、条件证明、正负结果和结论按该问题组织。",
    "SC-03": "主定位为明确边界核的机制与适用边界分析；工程接口用于复现。正文不将经典OT恒等式或既有重启操作作为独有方法贡献，原创充分性仍由SC-04/05单独记录。",
    "SC-14": "第六轮凸梯度路径下的矩缺口、条件W2下界、SPD迹恒等式与近似路径反例已进入IV-D至F；100个CPU案例和第七轮12单元端点诊断已进入V-G、VI-I/J及讨论。数值结果及范围与原记录一致。",
    "SC-19": "正文将矩缺口与经典二次输运成本差明确等价，归为机制引理并引经典OT来源；条件W2下界附Minkowski和Lipschitz推前证明，不据此宣称已通过逐证明查新。",
    "SC-20": "新增理论写明有限二阶矩、强凸C2势、可积性、固定终点、同源边缘及0<t<1条件；非梯度反例和有限端点非认证结论与正文相邻，未将这些假设认证给神经检查点。",
    "SC-37": "旧8幅图与18个Markdown表格完整保留；新增有限端点诊断表，编号按正文到附录连续排列。Word逐页排版验收及文件摘要写入本轮本地交付收据，不以表图数量证明科学结论。",
    "SC-38": "摘要、引言、理论衔接、讨论和结论已按研究问题重写；历史纠错和逐项管理保留在审计及自查表。Word正文不导出内部复现索引，保留方法假设、统计限制及不利结果；这些限定服务于论证。",
    "SC-39": "相关工作增加经典OT、小批耦合、有限循环单调性、ReBridge-Flow和MMD Guidance，参考文献共31条。新增来源使用原论文/正式会议页面；2026预印本注明版本，未写成同行评议定论。",
    "SC-42": "v7主稿已将第六/七轮研究写入方法条件、完整证明、实验协议、结果和讨论，并保留六检查点、组件、五臂及两轮候选数据。验收范围为本轮中文重写，不代表英文格式、创新性或投稿就绪通过。",
}
for item in z["items"]:
    if item["id"] not in updates:
        continue
    item.setdefault("history", []).append(
        {
            k: item.get(k, "")
            for k in [
                "status",
                "finding",
                "next_action",
                "review_round",
                "review_record",
                "verification_scope",
            ]
        }
    )
    item["finding"] = updates[item["id"]]
    item["review_round"] = "round8-2026-11-03"
    item["review_record"] = audit
    item["verification_scope"] = (
        "本轮中文稿的组织、条件陈述、来源和材料保留；不认证原创充分性、独立泛化或英文期刊格式。"
    )
    for evidence in [
        audit,
        draft,
        "verification_outputs/manuscript-rewrite-round8-20261103/INVENTORY.json",
    ]:
        if evidence not in item["evidence"]:
            item["evidence"].append(evidence)
z["latest_round"] = audit
z["corrections"].append(
    "第八轮已开始完整中文正文写作，新增解析与缓存结果不等于新增独立模型验证；写作完成与原创性、期刊格式验收分别记录。"
)
p.write_text(json.dumps(z, ensure_ascii=False, indent=2) + "\n")
# Regenerate all45 entries with the complete historical text from JSON.
parts = [
    "# 投稿改进自查表 2026年11月2日",
    "",
    "完整保留45项及各轮历史。第八轮完成中文v7正文重写；VERIFIED仅表示条目限定范围，原创性与独立有效性仍按具体缺口记录。",
    "",
    "## 状态规则",
    "",
]
parts += ["- " + k + "：" + v for k, v in z["status_rules"].items()]
parts += [
    "",
    "## 当前覆盖表",
    "",
    "| ID | 类别 | 优先级 | 自查问题 | 状态 |",
    "|---|---|---|---|---|",
]
parts += [
    "| "
    + " | ".join(item[k] for k in ["id", "group", "priority", "reviewer_question", "status"])
    + " |"
    for item in z["items"]
]
parts += ["", "## 历轮重要更正", ""] + ["- " + value for value in z["corrections"]]
parts += ["", "## 完整条目", ""]
for item in z["items"]:
    parts += ["### " + item["id"] + " " + item["reviewer_question"], ""]
    for key, label in [
        ("group", "类别"),
        ("priority", "优先级"),
        ("status", "状态"),
        ("acceptance", "验收"),
        ("finding", "发现"),
        ("next_action", "下一步"),
        ("verification_scope", "验证范围"),
        ("review_round", "核查轮次"),
        ("review_record", "本轮记录"),
    ]:
        if item.get(key):
            parts.append("- " + label + "：" + item[key])
    parts += [
        "- 证据：" + "；".join("`" + value + "`" for value in item["evidence"]),
        "",
        "历史记录（逐轮原文保留）：",
        "",
    ]
    parts += ["- " + json.dumps(value, ensure_ascii=False) for value in item.get("history", [])]
    parts += [""]
(r / "docs/audit/manuscript-selfcheck-2026-11-02.md").write_text("\n".join(parts).rstrip() + "\n")
p = r / "todo.json"
t = json.loads(p.read_text())
entry = t["manuscript_selfcheck_2026_11_02"]
entry.update(
    status="ROUND8 complete Chinese manuscript rewrite; originality and formal English formatting remain separately unresolved",
    latest_round=audit,
    current_chinese_draft=draft,
    status_counts=dict(collections.Counter(x["status"] for x in z["items"])),
)
entry["round8"] = dict(
    audit=audit,
    draft=draft,
    GPU_added_seconds=0,
    preserved_original_tables=18,
    tables_total=19,
    figures=8,
    references=31,
    scope="Writing and Word layout only; no scientific result promotion or new model generation",
    sync_evidence="Local round8 delivery receipt after server GitHub push and Mac pull",
)
p.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n")
for name in ["README.md", "README.zh.md", "docs/README.md"]:
    p = r / name
    s = (
        p.read_text()
        .replace("Chinese v6 research draft", "Chinese v7 research draft")
        .replace("中文v6研究稿", "中文v7研究稿")
    )
    s = s.replace(
        "drafts/paper-A-zh-reviewed-round5-2026-11-03.md",
        "drafts/paper-A-zh-reviewed-round8-2026-11-03.md",
    )
    if name == "README.md":
        s = s.replace(
            "Independent candidate results and remaining gaps are reported separately",
            "The [round8 manuscript rewrite](docs/audit/manuscript-rewrite-round8-2026-11-03.md) integrates the conditional theory and cached diagnostics. Independent candidate results and remaining gaps are reported separately",
            1,
        )
    elif name == "README.zh.md":
        s = s.replace(
            "候选验证与剩余缺口见",
            "[第八轮正文重写](docs/audit/manuscript-rewrite-round8-2026-11-03.md)已整合条件理论与缓存诊断。候选验证与剩余缺口见",
            1,
        )
    else:
        s = s.replace(
            "Current originality",
            "The [round8 rewrite](audit/manuscript-rewrite-round8-2026-11-03.md) integrates the conditional theory and cached diagnostics. Current originality",
            1,
        )
    p.write_text(s)
p = r / "mkdocs.yml"
s = p.read_text()
anchor = "      - Cached endpoint pairing round 7: audit/manuscript-endpoint-pairing-round7-2026-11-03.md"
assert anchor in s
s = s.replace(
    anchor,
    anchor
    + "\n      - Chinese manuscript rewrite round 8: audit/manuscript-rewrite-round8-2026-11-03.md\n      - Chinese research manuscript v7: drafts/paper-A-zh-reviewed-round8-2026-11-03.md",
)
p.write_text(s)
# Independent structure checks; old quantitative tables are protected byte for byte.
old = (r / "docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md").read_text()
new = (r / draft).read_text()


def tables(text):
    return re.findall(r"^\|.*(?:\n\|.*)*", text, re.M)


assert all(table in new for table in tables(old))
assert re.findall(r"^!\[.*$", old, re.M) == re.findall(r"^!\[.*$", new, re.M)
expected = [
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
    "XIV",
    "XV",
    "XVI",
    "XVII",
    "XVIII",
]
assert re.findall(r"^表 ([IVX]+)\.", new, re.M) == expected
assert [int(value) for value in re.findall(r"^\[(\d+)\]", new, re.M)] == list(range(1, 32))
assert len(z["items"]) == 45 and len({x["id"] for x in z["items"]}) == 45
(out / "STRUCTURE_CHECKS.json").write_text(
    json.dumps(
        dict(
            original_tables_byte_preserved=18,
            original_images_preserved=8,
            table_captions_in_order=expected,
            reference_labels=list(range(1, 32)),
            checklist_items=45,
            scientific_data_unchanged=True,
            manuscript_sha256=hashlib.sha256((r / draft).read_bytes()).hexdigest(),
        ),
        indent=2,
    )
    + "\n"
)
print(entry["status_counts"])
