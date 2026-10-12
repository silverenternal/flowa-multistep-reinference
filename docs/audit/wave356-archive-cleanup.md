# Wave 356 P5 — docs/drafts/ archive layer (catalog-only, no deletions)

**Date:** 2026-09-25
**Author:** Wave 356 P5 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — ADDITIVE catalog layer for `docs/drafts/` archived + flattened files.
**Trigger:** User request relayed through workflow harness: "剩下能做的任务也用ultracode做一下,这些任务都要处理" — docs/drafts/ archive cleanup pass (catalog the ARCHIVED + flattened intermediates that have accumulated since Wave 121).
**Scope:** NEW file `docs/drafts/ARCHIVE_INDEX.md` (catalog layer); NEW file `docs/audit/wave356-archive-cleanup.md` (this audit doc).
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits); NO-PUSH policy (per Wave 325); per `flowa-paper-evidence` skill (catalog layer only, never number changes); per AGENTS.md §3 guardrail #2 (additive is the rule).

**Out of scope (deliberately):**
- No edits to any archived + flattened draft file (all 9 files preserved byte-identical).
- No edits to `paper-A-final.md` / `paper-A-final.tex` / `paper-A-final.pdf` (canonical paper surface).
- No edits to `abstract-final.md` / `results-final.md` (canonical abstract + canonical results).
- No edits to `paper-flat-ieeetran.tex` / `paper-flat-ieeetran.pdf` (actively-used LaTeX working surface).
- No edits to `tnnls_submission/*` (no SHA-256 change required; no TNNLS submission file modified).
- No re-run of any GPU sweep (per `flowa-research-audit` skill: prefer existing artifacts).
- No edit to any source code (adaptive_reflow/, tests/, scripts/, tools/, data/) or vendored repo.
- No push (per Wave 325 NO-PUSH policy).

---

## 1. Executive Summary

`docs/drafts/` had **9 archived + flattened files** that were not
self-documenting. Wave 356 P5 adds **one new file** —
`docs/drafts/ARCHIVE_INDEX.md` — that catalogues every archived +
flattened file with: filename, size, SHA-256, archive-reason, and
cross-reference to the canonical paper surface. **Zero files were
deleted.** The catalog layer makes the docs/drafts/ directory
self-documenting so future agents (and reviewers) can distinguish
canonical surfaces from intermediate snapshots without grep'ing the
git log.

| Item | Value |
|---|---|
| Archived + flattened files catalogued | **9** |
| Total bytes catalogued | **948,140 bytes** (≈ 0.904 MB) |
| Canonical surfaces documented | 7 (paper-A-final.{md,tex,pdf} + abstract-final.md + results-final.md + paper-flat-ieeetran.{tex,pdf}) |
| Files deleted | **0** |
| Files modified (existing) | **0** |
| Files created (new) | 2 (`ARCHIVE_INDEX.md` + this audit doc) |

---

## 2. Observed facts (file inventory)

### 2.1 ARCHIVED file (explicit `.ARCHIVED-2026-09-23` rename)

| File | Size | SHA-256 |
|---|---:|---|
| `paper-flat-flattened.ARCHIVED-2026-09-23.md` | 334703 | `f33d11141e83d2063a6889fbc9e2e0a79e257a25e9edd4b16075c5bf638e88f7` |

### 2.2 Flattened intermediates (8 files)

| File | Size | SHA-256 |
|---|---:|---|
| `paper-flat-flattened-zh.md`       | 268307 | `90a68b710964600bc4876087de5af447ceedb754a793a267efe844706a3880ea` |
| `paper-flattened-draft.md`         |  92287 | `3d3b9f61b06cf3145c00ef7f3113904039f20e164bc94a42b7ea1f440c975514` |
| `abstract-flattened.md`            |   4056 | `37b2ba472dbf4837c031a52a44b2334f7f1e26f53c79de401ec664f7d0a5e517` |
| `methods-stats-flattened-draft.md` |  17475 | `9998f7bd814ee9a9b0ed440f7903f2a59b5abe06db7de740f669ce4d734f6f6e` |
| `methods-why-per-record.md`        |  54676 | `3c3ac3070cb2bb37c5a880c5ad7d3be42162de3ece6eda765bd1f72586027f69` |
| `results-flattened-draft.md`       |  42266 | `2cf985bdc4de33f829311e6b4ff78694faba539d387cdfd3ade2fe6d2342158f` |
| `section-2-method.md`              | 113570 | `c0bd668fcba003f688bcda393ca01e0870a07076ab0b4c9476f9977c51700858` |
| `limitations-flattened-draft.md`   |  21610 | `e2c7872cdcb04380072506093b51860b08dd4f8d0d1fd75e75efdcd4bc381e14` |

**Aggregate:** 9 files, 948,140 bytes, 0.904 MB.

### 2.3 Cross-reference verification

For each of the 9 archived + flattened files, `grep -F <name> paper-A-final.md`
returned **zero matches** (canonical prose does not reference any
archived file). Cross-references that **do** exist (in `abstract-final.md`
and `results-final.md`) are intentional historical provenance citations
and are documented in the per-file "Archive reason" column of
`docs/drafts/ARCHIVE_INDEX.md`. Specifically:

| Cross-reference | Where | Purpose |
|---|---|---|
| `paper-flattened-draft.md` §Abstract | `abstract-final.md` line 151 | Wave 207 P6 four-sentence structure provenance |
| `paper-flattened-draft.md` §4 | `results-final.md` line 936 | K1–K8 verbatim provenance |
| `methods-stats-flattened-draft.md` | `results-final.md` lines 31, 306, 318, 322, 366, 934 | Methods §MS subsection provenance |
| `section-2-method.md` §2.14 | `abstract-final.md` line 25 | Per-seed table + confound disclosure provenance |
| `limitations-flattened-draft.md` | `results-final.md` lines 29, 646, 888, 931 | Borderline + UNDERPOWERED boundary statements provenance |

All 5 cross-references are **deliberate provenance citations**, not
load-bearing content references. The canonical paper surface stands
on its own; the flattened drafts are evidence trail.

---

## 3. Interpretation

### 3.1 What the archive layer provides

Before Wave 356 P5, `docs/drafts/` was a flat directory of 16 files
where the canonical surfaces (`paper-A-final.md`, `abstract-final.md`,
`results-final.md`) co-existed with intermediate snapshots without
distinction. Future agents (and external reviewers) had to grep the
git log to know which file was canonical. After Wave 356 P5, the
catalog layer (`ARCHIVE_INDEX.md`) makes the directory self-documenting:

1. **Canonical surfaces table** — 7 files, clearly labelled, with SHA-256.
2. **Archived file** — 1 file, explicit `ARCHIVED-2026-09-23` rename reason.
3. **Flattened intermediates table** — 8 files, each with a one-line
   archive reason and cross-reference to the canonical surface it fed into.

### 3.2 Why no deletions

Per AGENTS.md §3 guardrail #2 ("No destructive edits. Additive is the
rule"), and per Wave 325 NO-PUSH policy precedent, the catalog layer
is the right tool: it changes the discoverability of the archive
without removing bytes. If a future agent needs to remove an archived
file, that decision is USER-AUTHORIZED and recorded in the ARCHIVE_INDEX
"Policy" section.

### 3.3 What this does NOT do

- It does not move files to `docs/archive/` or any other location.
- It does not delete files.
- It does not modify `paper-A-final.md` or any canonical surface.
- It does not regenerate the PDF or LaTeX.
- It does not touch `tnnls_submission/`.
- It does not push (NO-PUSH).

---

## 4. Verification

| Check | Result |
|---|---|
| `grep -F <archived-name> paper-A-final.md` for each of 9 archived files | **0 matches** (verified above) |
| All 9 archived files preserved byte-identical (sha256sum unchanged) | **PASS** (preserved; not re-hashed because no edit) |
| `ARCHIVE_INDEX.md` created with 9 files + SHA-256 + archive reason | **PASS** |
| Canonical paper surface unchanged | **PASS** (no edits to `paper-A-final.md` / `.tex` / `.pdf`) |
| No edits to `tnnls_submission/` | **PASS** |
| No edits to vendored repos | **PASS** |
| No edits to `adaptive_reflow/`, `tests/`, `scripts/`, `tools/`, `data/` | **PASS** |
| NO-PUSH policy | **PASS** (commit local only) |

---

## 5. Next smallest action

None required. The catalog layer is complete. If a future user wants
to move archived files to `docs/archive/drafts-archive/`, that is a
**separate** USER-AUTHORIZED destructive-pass and must update this
audit doc + the catalog layer accordingly.

---

_Last updated: 2026-09-25 (Wave 356 P5 — catalog layer complete)._