# 投稿自查表验证记录（2026-11-02）

## 范围与环境

Canonical python3 and Ruff; MkDocs and mypy dispatched through .venvs/flowmol3_venv/bin/python, as the repository environment routing prescribes. Temporary wrappers are in /tmp only.

本次新增45项自查表、JSON记录、管理入口和文档导航，刷新审计索引及工程门禁元数据；未修改算法、上游代码、冻结声明、正文和投稿包。

## 初次完整门禁链

| 命令 | 退出码 | 用时（秒） |
|---|---|---|
| `python3 tools/verify_submission_readiness.py` | 1 | 145.0 |
| `python3 tools/check_claims_consistency.py` | 0 | 0.0 |
| `python3 tools/check_docs_against_code.py` | 0 | 3.1 |
| `python3 tools/check_doc_paper_refs.py` | 0 | 2.2 |
| `python3 tools/paper_evidence.py --check` | 0 | 0.0 |
| `python3 -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | 0 | 123.1 |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 | 0.0 |
| `mkdocs build --strict` | 1 | 0.2 |
| `python3 tools/check_submission_manifest.py` | 0 | 0.5 |
| `python3 tools/check_submission_links.py` | 0 | 0.0 |
| `python3 tools/check_data_integrity.py` | 0 | 0.4 |
| `python3 tools/check_doc_links.py` | 0 | 13.2 |
| `python3 tools/check_paper_data_manifest.py` | 0 | 0.2 |
| `python3 tools/check_artifact_hashes.py` | 0 | 0.0 |
| `python3 tools/check_clone_integrity.py` | 0 | 0.4 |
| `python3 tools/regen_audit_index.py --check` | 0 | 0.1 |
| `python3 tools/check_vendored_pristine.py` | 0 | 0.1 |
| `python3 tools/check_doc_anchors.py` | 0 | 0.8 |
| `python3 tools/check_reviewer_pointers.py` | 0 | 0.1 |
| `python3 tools/check_recipe_flags.py` | 0 | 0.1 |
| `python3 tools/check_data_provenance.py` | 0 | 0.5 |
| `python3 tools/check_tables_inventory.py` | 0 | 0.0 |
| `python3 tools/check_figure_hashes.py` | 0 | 0.1 |
| `python3 tools/build_metric_ledger.py --check` | 1 | 16.3 |

## 环境与导航修正后的验证

| 命令 | 退出码 | 用时（秒） |
|---|---|---|
| `python3 tools/verify_submission_readiness.py` | 0 | 69.7 |
| `python3 tools/build_metric_ledger.py` | 0 | 34.7 |
| `python3 tools/build_metric_ledger.py --check` | 0 | 29.8 |
| `python3 tools/regen_audit_index.py --check` | 0 | 0.1 |
| `python3 tools/check_claims_consistency.py` | 0 | 0.1 |
| `git diff --check` | 0 | 0.0 |

最终 readiness 为 READY，72 个回归向量通过；严格文档构建通过；138 行 metric ledger 与新生成结果一致。此处是工程验证，不代表45个科学/写作自查项已全部验收。

## 必须保留的披露

- Initial .venv readiness failed an unused-ignore check; designated mypy passed 232 files and canonical readiness subsequently passed all gates.
- Initial .venv MkDocs lacks material; designated MkDocs initially found the two new pages missing from nav. Added their navigation entries, then strict build passed within ledger regeneration/check.
- Regenerated only two engineering ledger rows: new mkdocs.yml digest and test collection count 5817→5820. No scientific metric, frozen claim, manuscript or submission package changed.
- Ledger generator reports six existing non-fatal claim-status parsing messages. They remain disclosed, not silently fixed or treated as scientific verification.
- Doc-link checker exits zero while reporting two broken legacy links and one ambiguous/one archived pointer. This is not a claim that every link is perfect.
- 45 self-check IDs and all evidence-entry paths verified. Entries marked RECORDED/EVIDENCE_LOCATED are not scientific acceptance passes.

## Git 同步授权与基准

用户本轮明确要求将服务器现有源代码和记录更新先推送到GitHub，再拉取到Mac。起始工作树干净，服务器 main 比 origin/main 多305个提交，起始远端为 07098f6a04e6aaadd81c7d385d3e812fb2966039；按正常快进同步，不强推。此授权仅适用于本轮，不改变长期no_push默认。
