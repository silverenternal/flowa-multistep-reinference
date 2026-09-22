# Wave 272 P1 — Bilingual README

**Branch:** main
**Date:** 2026-09-22
**Scope:** README docs only — no source code, vendored code, CI workflow, or background tasks touched.

---

## 1. Goal

Create a Chinese mirror of `README.md` and add a language switcher at the top
of both files, so reviewers can read the project in either language while
keeping technical terms, file paths, commands, numbers, and SHA-256 prefixes
in English (preserving reproducibility).

## 2. Changes

### 2.1 New file: `README.zh.md`

A Chinese mirror of `README.md`. The translation covers the prose around
technical sections (TL;DR, architecture, installation, quick start,
reproduction, submission gates, acknowledgements) while preserving:

- All file paths, repo URLs, commands, and code blocks **unchanged**.
- All numbers, percentage signs, and SHA-256 prefixes **unchanged**.
- All technical terms (D.4, TNNLS, CI, GPU, FID, d_z, framework, FM, NFE,
  W₂, Bonf-sig, CUDA-graph, etc.) **in English** — reviewers not familiar
  with Chinese can copy-paste commands and verify SHA-256 against `verification_outputs/`.
- Section headings rendered bilingually where useful (e.g. "TL;DR / 概述",
  "Headline Results / 头条结果", "Architecture / 架构", "Installation / 安装",
  "Quick Start / 快速开始", "Reproducing the Paper / 复现论文", "Repository
  Structure / 仓库结构", "Submission Gates / 投稿门槛", "License / 许可证",
  "Acknowledgements / 致谢", "Contact / 联系方式").

### 2.2 `README.md` (English) — language switcher

Added a single line after the title block:

```
[English](README.md) | [中文](README.zh.md)
```

Placed before the CI/D.4/License badges to give readers a way to switch
language immediately on landing.

### 2.3 `README.zh.md` (Chinese) — same language switcher

Same line (`[English](README.md) | [中文](README.zh.md)`) added at the top,
so the switcher is reciprocal.

## 3. Sections translated

| # | Section | Translated? |
|---|---|---|
| 1 | TL;DR / 概述 | yes |
| 2 | Headline Results table | headers bilingual; numbers/IDs preserved |
| 3 | One-line Summary per Cell | bilingual header; bullets kept verbatim |
| 4 | Statistical methods paragraph | yes |
| 5 | Architecture (ASCII diagram + caption) | ASCII preserved verbatim; bilingual caption label |
| 6 | 4 paper quantities paragraph | yes |
| 7 | Installation code block | commands unchanged; bilingual header |
| 8 | Quick Start code block | commands unchanged; bilingual header |
| 9 | Reproducing the Paper table + script | commands unchanged; bilingual header |
| 10 | Environment Setup (Docker) | commands unchanged; bilingual header |
| 11 | Repository Structure (A + B) | bilingual headers; tree blocks unchanged |
| 12 | Submission Gates table | bilingual header; values unchanged |
| 13 | Data and Model Availability table | unchanged |
| 14 | Numerical Stability paragraph | unchanged |
| 15 | TNNLS Submission Package | bilingual header |
| 16 | Citation bibtex | unchanged |
| 17 | License | bilingual header |
| 18 | Acknowledgements | bilingual header |
| 19 | Contact | bilingual header |
| 20 | CHANGELOG footer | unchanged |

Total prose-translated sections: **20**.

## 4. Hard-rule compliance

- No framework source code modified — `git diff` is limited to `README.md`
  (+2 lines) and a new untracked `README.zh.md`.
- No vendored code modified.
- No background tasks touched.
- No new internal IDs (no Wave / CLM / USER ACTION) introduced in either
  README.
- All SHA-256 prefixes, percentages, file paths, commands, table headers,
  and bibtex entries are byte-identical between `README.md` and `README.zh.md`.
- D.4 30/30 PASS gate untouched (no `adaptive_reflow/` edits).
- `mkdocs.yml` untouched (mkdocs 0 warnings preserved).
- Claims consistency untouched (no claim numbers in either README).

## 5. Files touched

- `README.md` — +2 lines (language switcher at top).
- `README.zh.md` — new file (Chinese mirror with same switcher).
- `docs/audit/wave272-p1-bilingual-readme.md` — this audit doc.

## 6. Suggested verification

```bash
git diff README.md                       # 2-line addition (switcher)
wc -l README.md README.zh.md             # README.zh.md is the mirror
grep -c "README.zh.md" README.md         # 1 (switcher link)
grep -c "README.md" README.zh.md         # 1 (switcher link)
```

The Chinese mirror can be re-synced with English on each future README edit
by the same 2-step recipe (translate prose, preserve paths/numbers/commands).
