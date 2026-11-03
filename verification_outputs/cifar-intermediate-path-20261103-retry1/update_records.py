import collections
import hashlib
import json
import re
from pathlib import Path

root = Path("/home/hugo/codes/flowa-multistep-reinference")
out = root / "verification_outputs/cifar-intermediate-path-20261103-retry1"
audit = "docs/audit/manuscript-intermediate-round10-2026-11-03.md"
draft = "docs/drafts/paper-A-zh-reviewed-round10-2026-11-03.md"
item_path = root / "docs/audit/manuscript-selfcheck-2026-11-02.json"
(out / "checklist-before-round10.json").write_text(item_path.read_text())
data = json.loads(item_path.read_text())
findings = {
    "SC-04": "已补一个真实CIFAR检查点的中间轨迹与受控边界替换，36个干预单元完整。主时刻原噪声弦线虽更贴近单轨迹，却比独立噪声弦线更偏离中间及接续边缘；三种子、两精度和三带宽方向一致。新增的是对象区分和诊断证据，CMM/CorrFlow已覆盖边缘匹配或部署分布议题；没有新采样器，原创充分性仍未验收。",
    "SC-05": "本轮已完成同后段网格的真实边界状态干预，尚非前瞻诊断选择或独立模型预测验证；独立臂接近有限样本参照不能证明目标保持。未得到匹配总调用的质量收益或新部署决策，独有方法贡献仍缺证据。",
    "SC-14": "中文v9新增V-I、VI-L、图10与表XV，纳入真实中间路径而非只复用端点缓存；保留原20个表格对象、9图与全部旧数值，仅随新增文献重排引用。",
    "SC-19": "继续明确OT、Lipschitz推前、核双样本和理想RF边缘关系的既有基础。新增查新包含CMM累计边缘目标、CorrFlow残差修正与部署分布分析，不把“关注中间状态”或经典高斯对象区分写成首次。",
    "SC-20": "真实CIFAR数值轨迹已采集并比较两精度；原噪声弦线更近单轨迹却更偏离经验边缘，独立臂在参照附近。该结果限制凸梯度直线路径理论的直接迁移，未认证神经流凸性、精确中间边缘、逆Lipschitz界或历史质量退化原因。",
    "SC-37": "中文v9共21个表格对象、20张编号表、10图、35条参考文献；新图完整展示预定三时刻、两分辨率与三生成种子均值±标准差，负超额读数保留且不当作负MMD或质量收益。",
    "SC-39": "补入并读取CMM v2、CorrFlow v1和Gretton核双样本原始论文/正式页面，35条文献按首次出现重排。预印本版本与方法差异明确，历史上游精确版本及最终书目仍待逐项核验。",
    "SC-41": "条件分析、端点不可识别性与真实边界干预已形成连贯证据；主张收窄为逐样本接近不足以判定边缘相容。原创充分性及外部预测仍未验收，不能因本轮实验完成就把贡献锁定记为通过。",
    "SC-42": "中文v9已整合真实轨迹协议、受控结果、对象区分与最新相关工作，未将单检查点诊断写成质量改善或新算法。英文模板、最终篇幅和匿名材料仍待处理。",
}
next_actions = {
    "SC-04": "冻结本轮诊断作为机制证据；下一阶段先明确超出CMM/已有重启方法的可证伪预测，再考虑独立模型和匹配总调用的动作验证。",
    "SC-05": "只有在独立检查点上预先锁定诊断到动作的规则，并取得匹配总调用的实际质量证据后，再评估方法贡献；本轮不再新增GPU。",
    "SC-20": "将精确概率路径、数值轨迹边缘和训练插值严格分开；外部验证前不归因历史CIFAR退化。",
    "SC-41": "评估已有工作之外的具体主张与外部可检验性；本轮完成写作与单模型干预，不替代原创性验收。",
}
for item in data["items"]:
    if item["id"] not in findings:
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
        finding=findings[item["id"]],
        next_action=next_actions.get(item["id"], item["next_action"]),
        review_round="round10-2026-11-03",
        review_record=audit,
        verification_scope="同一冻结真实模型的数值中间路径、受控边界替换和对象区分；非总体不变性、感知质量、新方法或独立泛化认证。",
    )
    for name in [
        audit,
        draft,
        str(out.relative_to(root) / "RESULTS.json"),
        str(out.relative_to(root) / "PROTOCOL.json"),
    ]:
        if name not in item["evidence"]:
            item["evidence"].append(name)
data["latest_round"] = audit
data["corrections"].append(
    "第十轮完成真实CIFAR检查点中间轨迹和固定后段边界干预：原噪声弦线逐样本更近但整体边缘更远；不据一般耦合反例判定独立刷新有害。含失败重跑保守GPU总核算7158/7200秒。"
)
item_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
p = root / "docs/audit/manuscript-selfcheck-2026-11-02.md"
s = p.read_text().replace(
    "第九轮补充中文v8路径可识别性与现行投稿要求", "第十轮补充中文v9真实中间路径与边界干预"
)
for item in data["items"]:
    if item["id"] not in findings:
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
s = s.replace("## 完整条目\n", "- " + data["corrections"][-1] + "\n\n## 完整条目\n", 1)
p.write_text(s.rstrip() + "\n")
p = root / "todo.json"
t = json.loads(p.read_text())
entry = t["manuscript_selfcheck_2026_11_02"]
entry.update(
    status="ROUND10 real-checkpoint intermediate paths and fixed-suffix interventions complete; novelty/external prediction unresolved",
    latest_round=audit,
    current_chinese_draft=draft,
    status_counts=dict(collections.Counter(x["status"] for x in data["items"])),
)
entry["round10"] = dict(
    audit=audit,
    draft=draft,
    artifacts=str(out.relative_to(root)),
    intervention_cells=36,
    controls=18,
    samples_per_cohort=128,
    generation_seeds=[201, 202, 203],
    checkpoint_count=1,
    resolutions=[64, 128],
    GPU_added_conservative_seconds=520,
    GPU_accounted_total_seconds=7158,
    GPU_remaining_conservative_seconds=42,
    GPU_bearing_process_actual_wall_seconds=199.23942755989266,
    scientific_scope="Real-model pathwise-versus-marginal distinction; no learned correction or quality advantage",
    sync_evidence="Local round10 receipt after GitHub push, Mac pull and complete raw CPU replay",
)
review = t["current_research_review_2026_11_03"]
review["budget_before_round10"] = review["budget"]
review.update(
    latest_originality_audit=audit,
    draft=draft,
    budget="User-authorized real-path follow-up within original7200s; conservatively7158s including failed attempt and full retry cap. No further GPU jobs this round.",
    priority=[
        "Assess specific novelty beyond existing marginal-matching and restart work",
        "Define prospective diagnostic-to-action rules before any external experiment",
        "Seek independent checkpoint and matched-total-call quality validation if future budget is authorized",
    ],
)
p.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n")
for name in ["README.md", "README.zh.md", "docs/README.md"]:
    p = root / name
    p.write_text(
        p.read_text()
        .replace("Chinese v8 research draft", "Chinese v9 research draft")
        .replace("中文v8研究稿", "中文v9研究稿")
        .replace(
            "drafts/paper-A-zh-reviewed-round9-2026-11-03.md",
            "drafts/paper-A-zh-reviewed-round10-2026-11-03.md",
        )
    )
p = root / "mkdocs.yml"
s = p.read_text()
anchor = "      - Chinese research manuscript v8: drafts/paper-A-zh-reviewed-round9-2026-11-03.md"
assert anchor in s
s = s.replace(
    anchor,
    anchor
    + "\n      - Real intermediate paths round 10: audit/manuscript-intermediate-round10-2026-11-03.md\n      - Chinese research manuscript v9: drafts/paper-A-zh-reviewed-round10-2026-11-03.md",
)
p.write_text(s)
generation = json.loads((out / "GENERATION.json").read_text())
failed = root / "verification_outputs/cifar-intermediate-path-20261103"
failed_raw = failed / "raw/s201_r1.npz"
manifest = dict(
    successful_files=generation["files"],
    excluded_failed_attempt=dict(
        path=str(failed_raw.relative_to(root)),
        sha256=hashlib.sha256(failed_raw.read_bytes()).hexdigest(),
        bytes=failed_raw.stat().st_size,
        scope="Preserved technical failure; not included in scientific analysis",
    ),
    policy="Large raw snapshots not versioned in Git; server originals and full Mac scientific copy with hash verification",
    available_scientific_files=6,
    scientific_raw_total_bytes=sum(x["bytes"] for x in generation["files"]),
)
(out / "RAW_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
statuses = {x["id"]: x["status"] for x in data["items"]}
assert (
    len(statuses) == 45
    and statuses["SC-04"] == statuses["SC-05"] == "EVIDENCE_GAP"
    and statuses["SC-41"] == "REVISION_NEEDED"
)
print("All45 items and prior history retained; statuses unchanged; conservative GPU7158/7200")
