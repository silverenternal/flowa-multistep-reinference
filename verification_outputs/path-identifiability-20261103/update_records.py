import collections
import json
import re
from pathlib import Path

r = Path("/home/hugo/codes/flowa-multistep-reinference")
out = r / "verification_outputs/path-identifiability-20261103"
audit = "docs/audit/manuscript-supplement-round9-2026-11-03.md"
draft = "docs/drafts/paper-A-zh-reviewed-round9-2026-11-03.md"
p = r / "docs/audit/manuscript-selfcheck-2026-11-02.json"
(out / "checklist-before-round9.json").write_text(p.read_text())
z = json.loads(p.read_text())
updates = {
    "SC-04": "新增相同端点映射与联合分布、不同刷新输出的光滑流构造，36个CPU控制验证端点诊断不能替代真实中间边缘。路径自由度和Lipschitz传播已有经典基础；针对指定刷新核的构造未被确认为足够独立的新颖贡献。原有操作重合不变，原创充分性仍缺证据。",
    "SC-05": "当前新增的是可检验的端点不可识别性分析，不是新的端点混合算法。无新神经模型干预或迁移收益，不能以控制数量替代独有方法证据。",
    "SC-14": "中文v8新增IV-G的光滑流构造与双侧W2界、V-H协议、VI-K结果、图9和表XIV；旧19个表格对象保留，仅重排文献标签，原科学数据不变。",
    "SC-19": "既有矩缺口仍标明经典OT关系；新增双侧W2界明确为标准Lipschitz推前推论。端点不可识别性为具体构造，不将一般路径自由度当作首次发现，也不以数值通过代替逐证明查新。",
    "SC-20": "端点不可识别性限于一般光滑可逆流族，不要求同一独立直线训练路径；已知训练概率路径时可缩小该类别。双侧界需精确后段映射及正有限正逆Lipschitz上界，未认证给CIFAR模型。",
    "SC-37": "中文v8保留8幅已有图，新增可识别性图9；20个表格对象包含19张编号表和1张算法表。三种输出切片均展示，36例逐例记录可复算，不把合成控制写成图像生成质量。",
    "SC-39": "32条文献按首次出现重排，含真实AI辅助披露所用系统引用。官方作者须知有效地址、双匿名、10页收费阈值与15页上限已直接核对，旧2012年13页口径不再作现行规则。",
    "SC-42": "中文v8已补路径不可识别性命题、控制协议、结果、图表与AI辅助披露；另完成当前TNNLS投稿核对单。中文稿写作验收不等于英文双栏PDF、作者确认或原创充分性验收。",
    "SC-44": "已定位并直接读取现行TNNLS作者须知及5个官方页面，当前采用双匿名、IEEE Author Portal、常规10页收费阈值和15页最大长度。文章类型和主题适配可继续考察，但原创性、独立干预、英文编排及机构分区认可仍未据此通过；不将官网形式要求核对等同于首投合理性结论。",
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
    item.update(
        finding=updates[item["id"]],
        review_round="round9-2026-11-03",
        review_record=audit,
        verification_scope="本轮解析控制、文稿与官方规则核查；不认证原创充分性、真实神经流预测或最终投稿合规。",
    )
    for name in [audit, draft, "verification_outputs/path-identifiability-20261103/RESULTS.json"]:
        if name not in item["evidence"]:
            item["evidence"].append(name)
z["latest_round"] = audit
z["corrections"].append(
    "第九轮直接读取现行TNNLS官网：双匿名、常规超过10页每页200美元且正文总长最多15页；旧2012年13页口径为历史规则。解析路径控制已补充，实际神经流中间边缘与独立干预仍未完成。"
)
p.write_text(json.dumps(z, ensure_ascii=False, indent=2) + "\n")
# Preserve every old historical line and replace only changed item sections.
p = r / "docs/audit/manuscript-selfcheck-2026-11-02.md"
s = p.read_text().replace("第八轮完成中文v7正文重写", "第九轮补充中文v8路径可识别性与现行投稿要求")
for item in z["items"]:
    if item["id"] not in updates:
        continue
    start = s.index("### " + item["id"] + " ")
    end = s.find("\n### SC-", start + 1)
    if end == -1:
        end = len(s)
    lines = [f"### {item['id']} {item['reviewer_question']}", ""]
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
            lines.append("- " + label + "：" + item[key])
    lines += [
        "- 证据：" + "；".join("`" + value + "`" for value in item["evidence"]),
        "",
        "历史记录（逐轮原文保留）：",
        "",
    ]
    lines += ["- " + json.dumps(value, ensure_ascii=False) for value in item.get("history", [])]
    s = s[:start] + "\n".join(lines) + "\n" + s[end:]
s = s.replace("## 完整条目\n", "- " + z["corrections"][-1] + "\n\n## 完整条目\n", 1)
p.write_text(s.rstrip() + "\n")
p = r / "todo.json"
t = json.loads(p.read_text())
entry = t["manuscript_selfcheck_2026_11_02"]
entry.update(
    status="ROUND9 path-identifiability controls and current TNNLS requirements added; originality remains unresolved",
    latest_round=audit,
    current_chinese_draft=draft,
    status_counts=dict(collections.Counter(x["status"] for x in z["items"])),
)
entry["round9"] = dict(
    audit=audit,
    draft=draft,
    CPU_controls=36,
    GPU_added_seconds=0,
    author_requirements="docs/audit/tnnls-author-requirements-2026-11-03.md",
    originality="Specific endpoint-indistinguishability construction added; not a new sampler or novelty certification",
    sync_evidence="Local round9 delivery receipt after GitHub push and Mac pull",
)
t["venue_assessment"]["current_author_requirements_2026_11_03"] = dict(
    source="docs/audit/tnnls-author-requirements-2026-11-03.md",
    review="double-anonymous",
    regular_overlength_after_pages=10,
    regular_max_pages_excluding_supplement=15,
    author_portal="https://ieee.atyponrex.com/journal/tnnls",
    historical_13_page_rule_not_current=True,
)
t["current_research_review_2026_11_03"]["latest_originality_audit"] = audit
p.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n")
for name in ["README.md", "README.zh.md", "docs/README.md"]:
    p = r / name
    s = (
        p.read_text()
        .replace("Chinese v7 research draft", "Chinese v8 research draft")
        .replace("中文v7研究稿", "中文v8研究稿")
    )
    s = s.replace(
        "drafts/paper-A-zh-reviewed-round8-2026-11-03.md",
        "drafts/paper-A-zh-reviewed-round9-2026-11-03.md",
    )
    p.write_text(s)
p = r / "mkdocs.yml"
s = p.read_text()
anchor = "      - Chinese research manuscript v7: drafts/paper-A-zh-reviewed-round8-2026-11-03.md"
assert anchor in s
s = s.replace(
    anchor,
    anchor
    + "\n      - Path identifiability supplement round 9: audit/manuscript-supplement-round9-2026-11-03.md\n      - Current TNNLS author requirements: audit/tnnls-author-requirements-2026-11-03.md\n      - Chinese research manuscript v8: drafts/paper-A-zh-reviewed-round9-2026-11-03.md",
)
p.write_text(s)
p = out / "plot_path.py"
s = p.read_text().replace(
    "docs/drafts/figures/path-identifiability-20261103.png",
    "docs/figures/review-path-identifiability-20261103.png",
)
p.write_text(s)
new = (r / draft).read_text()
assert len(z["items"]) == 45
assert re.findall(r"^表 ([IVX]+)\.", new, re.M) == [
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
    "XIX",
]
body = new.split("## 参考文献", 1)[0]
assert list(dict.fromkeys(int(x) for x in re.findall(r"\[(\d+)\]", body))) == list(range(1, 33))
print("All45 items retained;19 numbered tables;32 references in first-appearance order")
