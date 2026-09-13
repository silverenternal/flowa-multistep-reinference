# FlowA 工作流与技能适配

本项目采用小波次、可恢复、证据先行的工作流。每个波次只处理一个明确问题，完成后留下审计记录和可机器读取的结果；长时间 GPU 扫描必须由用户单独决定。

## 推荐循环

1. **定位问题**：从 `todo/STATUS.md`、`docs/CLAIMS.md` 和相关 audit 确认目标、当前结论和缺口。
2. **审计与设计**：确认代码路径、配置、适配器能力、sidecar venv、GPU 资源和验收指标。
3. **最小实现**：只修改完成该波次所需的文件，先做 focused smoke test。
4. **受控实验**：固定 seed、N、环境和输出目录；保存 JSON/JSONL 原始结果与命令元数据。
5. **证据整理**：运行相关回归向量、claims/docs consistency 检查，更新 audit、结果表和论文表述。
6. **检查点**：提交一个小变更集；下一波次从审计结果继续，不隐式串联长流程。

## 三个项目技能

- `flowa-research-audit`：代码、配置、结果和论文 claim 的可追溯审计。
- `flowa-experiment-sweep`：绑定 sidecar 环境的 GPU/CPU 实验与可恢复扫描。
- `flowa-paper-evidence`：把已验证结果同步到 claims、论文、补充材料和投稿清单。

技能源码位于 `.codex/skills/`。技能只描述项目特有决策；通用编码、测试和权限规则仍由 Codex 默认规范负责。

## 检查点规则

- 单个波次建议 1 个目标、最多 3 个阶段、1 个提交。
- 长任务必须有 `--max-records` 或等效边界、独立输出目录和恢复方式。
- 结果不足以支持结论时，保留 `NOT_SIGNIFICANT`、`UNDERPOWERED` 或 `DEFERRED`，并记录下一步所需数据。
