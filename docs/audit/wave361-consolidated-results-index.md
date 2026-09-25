# Wave 361 — §15 Index for CONSOLIDATED_RESULTS.md (per-§15.NN row + cross-reference)

**Date:** 2026-09-25
**Wave:** 361 (CPU-only documentation wave)
**Author:** Wave 361 additive index propagation
**Status:** ACTIVE — canonical §15 navigation anchor for reviewer-facing
CONSOLIDATED_RESULTS ledger.

## 1. Purpose

`docs/CONSOLIDATED_RESULTS.md` §15 has grown to **100+ top-level sections**
(Wave 41 B → Wave 357 P3) over the 2026-08-23 → 2026-09-25 timeline. A
reviewer opening the file has no single-source navigation map. This audit
doc + its companion `§15.INDEX` section (appended at the end of
`CONSOLIDATED_RESULTS.md`) close the navigation gap with **one row per §15.NN
section** containing:

- **section_id** — the `§15.NN` (or `15.NN`, or `## 15` intro) header
- **headline_summary** — first 1-sentence finding, verbatim or distilled
- **verification_outputs_ref** — pointer to `verification_outputs/<wave>/` JSON/CSV
  (or `n/a` if docs-only)
- **audit_doc_ref** — pointer to `docs/audit/wave<NNN>-*.md` (or
  `docs/audit/<subtopic>.md` for snapshot/cross-doc anchors)

## 2. Scope + Method

- **Scope:** every top-level §15.NN section in `docs/CONSOLIDATED_RESULTS.md`
  (lines 943-8953, current commit `d2f34c9`).
- **Method:** enumerate via `grep -nE "^### 15\.[0-9]+|^### §15\.[0-9]+|^## 15\.|^## §15\."`,
  then for each section read the first paragraph (post-header) and extract the
  load-bearing headline. Cross-references resolved by `ls verification_outputs/`
  + `ls docs/audit/` + targeted WebFetch against the Wave 326 cross-doc
  snapshot pattern.
- **No GPU**, **no edits** to existing §15.NN content — purely ADDITIVE
  navigation surface.

## 3. Cross-references

- `docs/CONSOLIDATED_RESULTS.md` §15.INDEX — the append-only navigation table
  (this wave's ADDITIVE §15 footer).
- `docs/audit/wave326-crossdoc-metrics-snapshot.md` — sibling cross-doc anchor
  (11-cell verdict distribution, Wave 326). The §15.INDEX table complements
  the snapshot by surfacing per-section provenance rather than aggregate
  verdict distribution.
- `docs/verification_outputs.md` — per-artifact citing-surfaces + integrity
  status (Wave 360 P4 cross-reference back-fill matrix). The §15.INDEX
  uses `verification_outputs_ref` entries that align with
  `docs/verification_outputs.md` rows where they overlap.

## 4. Acceptance gates (target)

| # | Gate | Command | Target |
|---|------|---------|--------|
| 1 | D.4 byte-stable regression vectors | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** (no source code touched) |
| 2 | Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (no CLM-* changes) |
| 3 | ruff on touched scope | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **0 findings** (no `.py` files touched) |
| 4 | mkdocs strict build | `mkdocs build --strict` | **EXIT=0** (no `mkdocs.yml` change) |
| 5 | §15.INDEX section appended | `grep -E "^## §15.INDEX" docs/CONSOLIDATED_RESULTS.md` | **PASS** — exactly 1 match |
| 6 | No prior §15.X paragraph modified | `git diff --stat docs/CONSOLIDATED_RESULTS.md` (expect only new §15.INDEX) | **PASS** — append-only |
| 7 | Cross-refs resolved | for each `verification_outputs_ref` and `audit_doc_ref`, verify file exists | **PASS** — 105 / 105 audit_doc_ref resolved (100%); ~80 / 105 verification_outputs_ref populated |

## 5. Index summary

The §15.INDEX table covers **105 top-level sections** (the canonical
§15 ledger from `## 15` intro through `## §15.105` + `## 15.NEXT`) +
**0 destructive edits** to existing §15 content. Sections are listed in
**document order** (same order as the §15.NN headers in the source file),
so a reader using the index can jump directly to any §15.NN by anchor
(`#§15.NN-N`).

Cross-references resolved at this authoring pass: **105 / 105 rows have
a populated `audit_doc_ref`**. The `verification_outputs_ref` column is
populated for ~80 / 105 rows; the remaining ~25 rows are docs-only waves
(Wave 130-153 polish + §15.89-§15.94 paper-additive waves) where the
audit doc is the closure artifact and the verification_outputs are
gitignored / non-byte-stable.

## 6. ADDITIVE only — does NOT modify any prior §15.1–§15.105 paragraph

This wave is purely navigation-surface ADDITIVE. No §15.NN section above
`§15.INDEX` is edited, deleted, or rewritten. The §15.INDEX table is
appended at the end of the file (after §15.105). Per Wave 268 strict-clean
rule (status history additive, no removal) and Wave 325 NO-PUSH policy,
this wave ships documentation-only.

## 7. Files modified by Wave 361 (additive only)

| File | Change |
|---|---|
| `docs/CONSOLIDATED_RESULTS.md` §15.INDEX (NEW) | New ADDITIVE §15.INDEX navigation table appended at end of file; no prior §15.NN paragraph modified |
| `docs/audit/wave361-consolidated-results-index.md` | New audit doc for this Wave 361 documentation step |

No `adaptive_reflow/`, no `tests/`, no `tools/`, no `data/`, no
`tnnls_submission/` files are touched. The `docs/paper-draft.md`,
`docs/CLAIMS.md`, `docs/drafts/*`, `README.md`, `README.zh.md`,
`cover-letter-tnnls.md` are also NOT touched by this wave.