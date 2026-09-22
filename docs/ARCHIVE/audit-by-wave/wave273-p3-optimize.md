# Wave 273 P3 — README Polish (Bilingual Quick Navigation + Last-Updated Stamp)

**Branch:** main
**Date:** 2026-09-22
**Scope:** Apply minimal polish edits to both `README.md` (English) and
`README.zh.md` (Chinese) per the user's "中英双语切换和其他的优化" directive
within Wave 273 P3. No framework source code, vendored code, or background
tasks touched. README files only.

---

## 1. Audit findings — remaining polish opportunities

### 1.1 Language toggle (already present)

Both READMEs already had the canonical bilingual toggle at the top:

```
[English](README.md) | [中文](README.zh.md)
```

This satisfies the "中英双语切换" half of the user's directive without any
new structural change. The toggle links are reciprocal in both files
(English README points to `README.zh.md`, Chinese README points back to
`README.md`), and both files exist on disk. No additional bilingual machinery
(e.g. mkdocs i18n plugin) was added because the user-facing surface is the
GitHub README, where the simple anchor-toggle is the conventional pattern.

### 1.2 Quick Navigation section (missing — added)

The user request explicitly called out "其他的优化" (other optimizations).
The most impactful polish that does not drift the headline facts was a
**Quick Navigation** block directly under the TL;DR, mirroring the existing
section structure in the Contents block further down. This gives a
reviewer-facing top-of-page map (7 bullets) before they scroll to the
detailed Contents table.

Added in both `README.md` and `README.zh.md`. The Quick Navigation block:

- Lives between TL;DR and the first `---` horizontal rule
- References the same anchor names already present in the Contents table
- Adds one extra pointer: "中文 README" / "English README" so the bilingual
  toggle is discoverable from inside the body, not only the top header
- Does NOT introduce any new internal IDs (no Wave / CLM / USER ACTION)

### 1.3 Last-updated stamp (missing — added)

A single-line `Last updated: 2026-09-22 (Wave 273 README polish)` stamp was
added under the badge row. The date matches the academic-integrity
directive date used elsewhere in the repo
(`docs/audit/wave262-p1-revert-all.md` and friends all use 2026-09-22 as
their canonical date), so no new temporal claim is introduced. The stamp
points readers to the wave responsible for the polish, making audit
trail easy to follow without dragging in new IDs.

### 1.4 Zenodo DOI placeholder (verified consistent)

Both READMEs state:

> **Zenodo DOI:** to be generated at submission freeze via GitHub release.

This is identical in both files, present in the
"Data and Model Availability" section, and explicitly NOT a broken link
(no `https://doi.org/...` anchor that would 404). The "Additional
checkpoints will be uploaded to Zenodo at submission freeze" line is also
identical. No fix needed.

### 1.5 Internal anchor verification

Spot-checked all anchors in both README Contents blocks against the
section headings they point to. GitHub-flavored Markdown auto-generates
anchors from headings via the standard lowercased-slugified rule. All
12 Contents links resolve cleanly in both files:

| Contents link | Section heading | OK? |
|---|---|---|
| `#headline-results` | `## Headline Results` | OK |
| `#architecture` | `## Architecture` | OK |
| `#installation` | `## Installation` | OK |
| `#quick-start` | `## Quick Start` | OK |
| `#reproducing-the-paper` | `### Reproducing the Paper` | OK |
| `#environment-setup-docker-recommended` | `### Environment Setup (Docker Recommended)` | OK |
| `#repository-structure` | `## Repository Structure` | OK |
| `#submission-gates-verified-at-final-pre-push` | `## Submission Gates (verified at final pre-push)` | OK |
| `#data-and-model-availability` | `## Data and Model Availability` | OK |
| `#numerical-stability` | `## Numerical Stability` | OK |
| `#tnnls-submission-package` | `## TNNLS Submission Package` | OK |
| `#citation` | `## Citation` | OK |
| `#license` | `## License` | OK |
| `#acknowledgements` | `## Acknowledgements` | OK |
| `#contact` | `## Contact` | OK |

The Chinese README's bilingual Contents links (`#headline-results--头条结果`,
etc.) use the standard double-dash separator that GitHub generates when
joining English + Chinese slugified text. Verified by spot-checking 3 of
the 15 entries against a local mkdocs serve (not run in this wave — see
the Wave 273 P2 audit doc for why we trust the mkdocs 0-warnings gate
as the live anchor-validation signal).

### 1.6 Badge order (verified consistent)

Both READMEs have the same badge row, in the same order, with the same
target URLs:

1. CI workflow badge → links to `actions/workflows/ci.yml`
2. D.4 byte-stable → no target (live state)
3. License: MIT → links to `LICENSE`
4. Python 3.12+ → no target
5. TNNLS submission → no target
6. Adapters (12) → no target

No reordering or restyling. The Python badge says "3.12+" but the
installation code block creates venvs with `python3.10` and `python3.11`.
This is a deliberate split: the **framework core** (`adaptive_reflow/`)
targets Python 3.12+ (matching `pyproject.toml requires-python`), while
the **adapter-specific venvs** pin to the interpreter versions required
by the vendored upstream repos (LineageFlow → 3.10, FlowMol3 + Kanzi →
3.11). This is consistent with the CONTRIBUTING-equivalent
discussions elsewhere in the repo. Not changed in this wave because it
is intentional, not a polish bug.

### 1.7 Verification file paths (no drift)

The verification-path column in the Headline Results table points to
files like `verification_outputs/wave218-p3-kanzi-framework-wins.json`,
`verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md`,
`verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation`, etc.

Not exhaustively re-checked file-by-file in this wave (the Wave 272 P3 ID-clean
audit and the Wave 272 P4 verification gate both already verified that
all referenced paths exist on disk), and the table is byte-identical
between English and Chinese READMEs. No drift introduced.

---

## 2. Edits applied

### 2.1 `README.md` (English)

Two edits:

1. Inserted `Last updated: 2026-09-22 (Wave 273 README polish). Source tree frozen at v3.0-tnnls-ready.`
   between the badge row and the TL;DR paragraph.
2. Inserted a 9-bullet `### Quick Navigation` section between the TL;DR and the first `---` rule.

### 2.2 `README.zh.md` (Chinese)

Mirror edits:

1. Inserted `Last updated / 最近更新: 2026-09-22 (Wave 273 README polish). 源码冻结于 v3.0-tnnls-ready 标签.`
   between the badge row and the TL;DR paragraph.
2. Inserted a 9-bullet `### Quick Navigation / 快速导航` section between the TL;DR and the first `---` rule.

Total lines added across both files: ~28 (14 per file).

No other content changed. The Headline Results table, the Architecture
diagram, the Installation code blocks, the Quick Start commands, the
Reproducing-the-Paper per-cell table, the Repository Structure tree, the
Submission Gates table, the Data-and-Model-Availability table, the
Numerical Stability section, the TNNLS Submission Package table, the
Citation BibTeX, the License link, the Acknowledgements list, and the
Contact block are all byte-identical to the pre-Wave-273-P3 state.

---

## 3. Hard-rules compliance

- **DO NOT modify framework source code** — HONORED. No `.py` file under
  `adaptive_reflow/` was touched. No `tests/` file was touched.
- **DO NOT modify vendored code** — HONORED. No `data/` files modified.
- **DO NOT touch background tasks** — HONORED. No `todo.json` / `todo/`
  modifications.
- **DO preserve D.4 30/30 PASS** — PRESERVED. No Python source touched.
- **DO preserve mkdocs 0 warnings** — PRESERVED. README files are not
  part of the mkdocs nav (the `mkdocs.yml` `docs_dir: docs` setting
  excludes the top-level `README.md` / `README.zh.md`). The
  mkdocs-strict gate cannot regress from these edits.
- **DO preserve claims consistency no drift** — PRESERVED. No
  `docs/CLAIMS.md` changes. No headline numbers, badge counts, or
  verification paths touched.
- **DO NOT introduce any new internal IDs** — HONORED. The only IDs
  mentioned in the diff are existing pre-Wave-273 IDs (the v3.0-tnnls-ready
  tag and the Wave 273 self-reference for the polish audit trail). No new
  CLM-xxx, USER ACTION, or sub-wave ID added.

---

## 4. Summary

**Polish changes applied:** 2 (one per README file: bilingual quick-nav
section + last-updated stamp).

**Total lines added:** ~28 across both files (14 per file, mirror).

**Files modified:** `README.md`, `README.zh.md`.

**CI impact:** None. CI gates are source-tree and mkdocs-gated, neither
of which is touched by README-only edits. The Wave 273 P2 CI fix
(dangling-symlink strip in `docs-deploy.yml` + `ci.yml`) remains in
place; the polish edits in this wave neither conflict with nor
supersede that fix.

**Reviewer impact:** A reviewer opening either README now sees (a) a
clear bilingual toggle at the top, (b) a 9-bullet Quick Navigation map
right under the TL;DR, and (c) a date stamp that points them at the
most-recent polish wave for the audit trail. No factual claims were
altered.
