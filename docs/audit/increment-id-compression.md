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

## The manuscript sources

`docs/drafts/paper-A-final.md` carried **171** identifiers (44 lines, 9 of
them headings such as `#### 3.5.1 Concrete SHA-256 ledger example (Wave 349
R1 3-seed GPU artifact)`); `paper-A-final.tex` carried one, inside a LaTeX
comment. Both were compressed under the same rule, and the PDF was rebuilt.

The markdown file is dense enough that exact-substring replacement was not
practical, so a single token pattern was used instead:

```
Wave[- ]?\d+(?:\.\w+)?(?:\s*[PG]\d+)?(?:\s*[PG](?=\s))?
    (?:[–-]P?\d+)?(?:\s*\+\s*P?\d+[A-Za-z]*)?(?:/\s*\d+[A-Za-z]?)*
```

The range group requires the letter (`–P6`), never a bare number, so
`Wave 236 P2 — 24.6×` cannot be truncated to `.6×`; the `+` and `/` groups
exist for the compound forms that really occur (`Wave 156+156c`,
`Wave 127/131/132/152`, `Wave 349 P1 + P3`). The pattern was validated by
printing all 171 matches before applying anything: none contained a decimal
point. After deletion the numeric multiset is **identical** to the
pre-edit file with the same pattern normalised — zero deltas in either
direction, not merely "no unexplained delta".

Twenty-three grammatical artifacts from the deletion were then repaired by
hand (`**Proof-scope correction ().**` → `**Proof-scope correction.**`,
`* ADDITIVE footnote` → `*ADDITIVE footnote`, `the ** LineageFlow HMMER
K4**` → `**LineageFlow HMMER K4**`, `(+ + + + + + + + + +).` → removed,
`per)` → `)`, `per + CLM-056` → `per CLM-056`, and so on). A final scan for
double spaces, space-before-punctuation, `per)`/`per;`, `+ +` and `(` +
space finds nothing outside code blocks and LaTeX.

**Rebuild.** `pdflatex -interaction=nonstopmode -halt-on-error` twice in
`docs/drafts/`. Result: **12 pages** (unchanged), 615789 bytes (unchanged),
**0 overfull hboxes**, 0 undefined references, and `pdftotext` reports
**zero** occurrences of the identifier in the delivered PDF.

The PDF's SHA-256 necessarily changed (pdflatex embeds a creation date), so
the three `CURRENT_ARTIFACTS` entries in `tools/check_submission_manifest.py`,
the `MANIFEST.md` packaging banner and rows, `SHA256SUMS`,
`submission_checklist.md`, `SUBMISSION_READINESS.md`, `README.md` and
`README.zh.md` were all updated to the new `paper-A-final.{md,tex,pdf}`
digests and the new markdown word count (27 347, was 27 809).

**One word later removed.** A follow-up commit (`24f05bac` → the
`todo/`-retirement pass) deleted one word from §10.5: the sentence
"CLM-073 + the `todo/RISK-REGISTER.md` R-019 deferred items" became
"CLM-073 and the R-019 deferred items", because the register it named was
retired on 2026-10-13. The manuscript markdown is therefore 224 407 bytes
/ 27 346 words / `46e42307…` rather than 224 429 / 27 347 / `417f3183…`;
the `.tex` and the PDF are untouched (the string appears in neither), so
only the `.md` digest moved. The digests quoted in this paragraph are the
ones the compression commit produced.

One stale reading was corrected at the same time: `SUBMISSION_READINESS.md`
row 6 still quoted a 446 705-byte / `461ee92e…` PDF that no longer existed
at HEAD. It now quotes the real artifact.

## What was deliberately not compressed

`tnnls_submission/FILL_GUIDE.md` keeps one occurrence because it is a
literal example commit message a user is meant to copy.
`docs/audit/wave385-figures.md` and the superseded-artifact banners inside
`MANIFEST.md` keep theirs because they are historical records of what a
given build's hash was; rewriting them would make the record claim a hash
that never existed.
