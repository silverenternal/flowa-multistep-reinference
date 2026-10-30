# Compressing increment identifiers out of the reviewer-facing package

**Date:** 2026-10-30
**Scope:** `tnnls_submission/` reviewer-facing documents + `docs/README.md`
**Rule:** no metric, verdict, status label, or claim changed; only the
internal increment identifier was removed from the prose around it.

## Why

Every document in the submission package accumulated change-log prose of
the form "— **Wave 348 Phase 1b cross-doc fix**: 57 local repo paths →
GitHub URLs". That identifier is an internal project-iteration counter. A
reviewer reading the package does not know what a "wave" is, cannot look
one up without the private audit tree, and does not care how many
iterations the package went through. The identifier was noise in the
sentence it sat in: it displaced the noun that carried the meaning
("cross-doc fix", "grid search", "counterfactual") and made every
description read as a diff log rather than a description.

The compression therefore removes the *label*, never the *substance*: the
audit records themselves are still linked from the rows they annotate, and
every number, verdict and status label in the sentence is preserved
character-for-character.

## What changed

| File | Wave tokens before | after |
|---|---:|---:|
| `tnnls_submission/cover_letter.md` | 128 | 0 |
| `tnnls_submission/MANIFEST.md` | 158 | 0 |
| `tnnls_submission/SUBMISSION_READINESS.md` | 139 | 0 |
| `tnnls_submission/submission_checklist.md` | 127 | 0 |
| `tnnls_submission/figures.md` | 64 | 0 |
| `tnnls_submission/tables.md` | 44 | 0 |
| `tnnls_submission/data_availability.md` | 33 | 0 |
| `docs/README.md` | 7 | 0 |
| `tnnls_submission/highlights.md` | 1 | 0 |
| `tnnls_submission/README.md` | 1 | 0 |

Total: **702** identifiers (`Wave[- ]?<digits>`, case-sensitive).

`README.md`, `README.zh.md`, `docs/PAPER-EVIDENCE.md` and `AGENTS.md`
already carried zero and were not touched.

## What was deliberately kept

**Paths, filenames, JSON keys, commit-message quotes and §-section
identifiers are untouched.** `verification_outputs/wave230-p2-real-4arm-per-record.csv`,
`docs/audit/wave349-impl.md`, `re_measurement_wave238_p2`, and
`` `git commit -m "Wave 274 P3: fill ..."` `` are addresses, not
annotations: rewriting them would break a link or a lookup. The
`docs/audit/wave*.md` corpus keeps its names for the same reason — 600+
records and every citation into them are keyed on those filenames.

Three of the ten files needed a judgement call:

- `MANIFEST.md` row 136 (`paper-A-final.md`) carried a 22-identifier
  change-log cell. It was rewritten as one continuous "earlier additive
  layers, preserved underneath" clause rather than deleting the history.
  Every §-reference, every measurement (`L_local ≈ 0.3810`,
  `eps_theta ≈ 0.0506`, `~33x at k=20`), every status
  (`PARTIALLY CLOSED`, `INCONCLUSIVE`, `RESERVED`) and every linked audit
  document survives.
- `data_availability.md` closed with a fifteen-bullet, increment-by-
  increment catalogue of audit documents. It is now a short pointer to
  [`docs/audit/INDEX.md`](INDEX.md), which is the maintained index of all
  622 records and covers every bullet that was removed.
- `tables.md` quoted nine `[§15.XX — Wave NNN …]` link labels that
  paraphrase CONSOLIDATED_RESULTS section headings. The wave clause was
  dropped from the label and the §-number kept, so the label still names
  the section it points at.

## How it was verified

Three independent checks per file:

1. **Numeric invariance.** Every `Wave NNN [Pn]` token is normalised to
   `<W>` in both the pre- and post-edit text, then the multiset of all
   remaining numeric literals is compared. The diff must contain only
   digits that belonged to a removed identifier. This is what catches the
   failure mode the first attempt hit: a regex with a trailing
   `(?:—\s*P?\d+)?` range group swallowed `— 24` out of
   `Wave 236 P2 — 24.6×` and produced `.6×`. The final pass uses exact
   string replacement, not a token regex, and the numeric diff is empty
   of unexplained deltas on all ten files.
2. **ASCII-art width invariance.** `figures.md` contains six box diagrams.
   Each edit to a boxed line keeps the line length constant by moving the
   removed character count into the padding before the trailing border
   glyph; block-by-block line lengths are identical before and after
   (offset by one where a whole line was dropped).
3. **Gate chain.** `check_submission_manifest` (`known_stale=0
   unknown=0 addendum_drift=0 ledger_drift=0`), `check_reviewer_pointers`
   (`dead=0`), `check_claims_consistency` (no drift), `check_doc_links`,
   `check_doc_anchors`, `check_recipe_flags`, `check_data_provenance`
   (`drifts=0 disclosed=3`), `check_docs_against_code`,
   `check_paper_data_manifest`, `check_data_integrity`,
   `check_vendored_pristine` and the paper-evidence check all pass after
   the edit.

`tnnls_submission/SHA256SUMS` was regenerated (`sha256sum -c` → 22 OK)
and the `MANIFEST.md` rows for every edited file were refreshed.

## What was not compressed, and why

**`docs/drafts/paper-A-final.md` carries 44 identifiers, 9 of them in
headings** (e.g. `#### 3.5.1 Concrete SHA-256 ledger example (Wave 349 R1
3-seed GPU artifact)`). The compiled manuscript
`paper-A-final.tex` carries exactly one, and it is inside a LaTeX comment
(`% IEEEtran-journal typeset for TNNLS submission (Wave 331)`), so the
PDF a reviewer receives contains **zero** visible identifiers. Editing the
markdown reading copy would either leave it inconsistent with the PDF or
require a PDF rebuild, which changes `paper-A-final.pdf`'s SHA-256 and
page count and cascades through `MANIFEST.md`, `SUBMISSION_READINESS.md`
and `tables.md`. That is a manuscript-freeze decision, not a documentation
edit, so it is left open and recorded here rather than taken unilaterally.

`tnnls_submission/FILL_GUIDE.md` keeps one occurrence because it is a
literal example commit message a user is meant to copy.
