# `docs/` legacy-artifact inventory

**Date:** 2026-10-12
**Scope:** Unified inventory of the top-level `docs/*.md` surface, on user request
("统一盘点 docs 遗留件"). Classifies every top-level document as **LIVE** (current
reference), **HISTORICAL** (a point-in-time record, retained for provenance), or
**LEGACY** (superseded by a newer canonical artifact — misleading if read as
current). The three paper drafts and five further documents carry a top banner
after this pass.
**Status:** COMPLETE. Banners added to 5 documents (3 paper drafts were already
labelled in a prior pass). All gates green. **No manuscript artifact, metric,
claim, source module, or vendored-upstream file changed.**

---

## 1. Method

For each `docs/*.md` file: (a) read its title + date/status line, (b) check whether
it is referenced by any live surface (`README.md`, `README.zh.md`, `todo/WAVES.md`,
`todo/README.md`, `tnnls_submission/`), and (c) check whether a newer canonical
artifact supersedes it. Files are **not** deleted — the provenance rule keeps them
on disk; the banner tells a reader which are current.

## 2. Classification

### 2.1 LEGACY — superseded by a newer canonical artifact (bannered)

| Doc | Superseded by | Evidence |
|---|---|---|
| `paper-draft.md` | `drafts/paper-A-final.md` | EAAI-era draft; banner added in a prior pass |
| `paper-draft-anonymous.md` | `drafts/paper-A-final.md` | workshop draft (2026-09-05) |
| `paper-final-neurips.md` | `drafts/paper-A-final.md` | NeurIPS 2026 anonymous submission |
| `submission-checklist-final.md` | `tnnls_submission/submission_checklist.md` | NeurIPS-era checklist (2026-09-14); cites a missing `docs/supplementary-neurips.pdf` |
| `push-ready-summary.md` | `todo/PUSH-READY.md`, `todo/WAVES.md` | Wave 72-74 pre-push summary (2026-09-08) |
| `STRATEGY_FRAMEWORK_SCOPE.md` | `README.md`, `ARCHITECTURE.md` | 2026-09-04 "Draft for review" |

### 2.2 HISTORICAL — point-in-time record, retained (bannered)

| Doc | Date / scope |
|---|---|
| `code-release-checklist.md` | 2026-09-14 release record for tag `v1.0.1-paper-final`; current process is `RELEASING.md` |
| `reproducibility_record.md` | Wave 15 (2026-09-05) record; current recipe is `reproduce.md` |

### 2.3 LIVE — current reference (no banner)

Evidence records that are intentionally the canonical record (doc map §4/§5):
`CONSOLIDATED_RESULTS.md`, `CLAIMS.md`, `METRIC_LEDGER.md`, `ABLATION.md`,
`CONDITIONS.md`, `benchmark-uplifts.md`, `benchmark-round2-uplifts.md`,
`benchmark-deep-uplifts.md`, `baseline-audit-report.md`, `capability_g1_analysis.md`,
`mutation_audit_q4_2026.md`, `INSIGHTS.md`.

Reference / operations / onboarding docs: `ARCHITECTURE.md`, `ALGORITHMS.md`,
`GATES.md`, `TESTING_STRATEGY.md`, `PERFORMANCE_BUDGETS.md`, `environments.md`,
`reproduce.md`, `verification_outputs.md`, `ADAPTER_INTERFACE_SPEC.md`,
`adapter-dependencies.md`, `configs.md`, `defaults-matrix.md`, `DEPRECATION.md`,
`distinguishing-from-reflow.md`, `PLUG_IN_YOUR_MODEL.md`, `schedule-theory.md`,
`sequential-protocol.md`, `TUTORIAL.md`, `RELEASING.md`, `FLOWA_WORKFLOW.md`,
`CONTRIBUTING-cover-letter.md`, `cover-letter-tnnls.md` (canonical cover letter —
`tnnls_submission/cover_letter.md` is a frozen snapshot of it), `RELEASE-NOTES.md`,
`paper-profile.md`, `README.md`, `算法实现说明.md`.

## 3. Findings (observed facts)

| # | Finding | Evidence |
|---|---|---|
| F1 | **`docs/cover-letter-tnnls.md` is LIVE, not legacy.** It is the canonical TNNLS cover letter; `tnnls_submission/cover_letter.md` is a frozen snapshot (`tnnls_submission/MANIFEST.md:90`). A naive "dated ⇒ legacy" rule would have mislabelled it. | `tnnls_submission/MANIFEST.md:90`, `tnnls_submission/submission_checklist.md:12`. |
| F2 | **`docs/submission-checklist-final.md` has link-rot.** It cites `docs/supplementary-neurips.pdf`, which does not exist. | `test -e docs/supplementary-neurips.pdf` → false. |
| F3 | **`docs/RELEASE-NOTES.md` is one version behind.** It is `v3.0-tnnls-ready`, frozen at commit `51e0aa4` (2026-09-22), but the repo now carries `v3.1-*` tags. | `git tag` → `v3.1-tnnls-with-figure`; `docs/RELEASE-NOTES.md:4`. |
| F4 | **All 48 top-level `docs/*.md` are catalogued** in `docs/README.md`. | cross-reference scan. |

## 4. Changes (additive; no deletions)

- Added a top **LEGACY** banner to `docs/submission-checklist-final.md`,
  `docs/push-ready-summary.md`, `docs/STRATEGY_FRAMEWORK_SCOPE.md`.
- Added a top **HISTORICAL** banner to `docs/code-release-checklist.md`,
  `docs/reproducibility_record.md`.
- `docs/README.md` §5: the `reproducibility_record.md` / `code-release-checklist.md`
  rows now say "Historical"; §6 gains a "Legacy / historical `docs/` documents"
  bullet pointing at this inventory.

## 5. Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| readiness verifier | `python tools/verify_submission_readiness.py` | **READY_WITH_SKIPS: mypy_0** (exit 0) |
| claims consistency | `python tools/check_claims_consistency.py` | **PASS** — no drift |
| docs-against-code | `python tools/check_docs_against_code.py` | **PASS** |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0 |

## 6. Unresolved gaps / caveats

- **`docs/RELEASE-NOTES.md` (F3) is stale, not legacy** — it is the canonical
  release-notes file, simply not updated past `v3.0`. Left unbannered; flagged here
  for a future update.
- **`docs/paper-profile.md`** (2026-09-16) is a dated venue profile still referenced
  by the doc map; classified LIVE, left unbannered.
- **Evidence records** (`baseline-audit-report.md`, `capability_g1_analysis.md`,
  `mutation_audit_q4_2026.md`, the `benchmark-*.md` trio, `ABLATION.md`,
  `CONDITIONS.md`) are dated but are the *intentional* evidence record (doc map
  §4/§5); left unbannered.
- **Bodies preserved verbatim** — every edit is a top-of-file banner.
