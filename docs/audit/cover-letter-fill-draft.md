# Cover-letter placeholder fill — exemplar draft

**Date:** 2026-10-11
**Status:** READY_TO_COMMIT
**Trigger:** User directive *"Fill cover-letter placeholders"*; on the follow-up
question (real values vs. exemplar draft vs. structural-only) the user chose
**"Use repo exemplar defaults (draft)"**.
**Scope:** Fill the 17 `[USER TO FILL: …]` identity/contact fields in
`tnnls_submission/cover_letter.md` with the repository's `INTERACTIVE_DEFAULTS`
exemplar values; refresh the MANIFEST SHA-256 ledger for `cover_letter.md`. NO paper
content change, NO number/verdict change, NO vendored code change.

> **These are NOT real people or addresses.** Every value below is a repository
> exemplar (e.g. *Hugo Huang*, *hugo@example.com*, *University of Example*) and
> **must be overridden before any real submission** — see
> `tnnls_submission/FILL_GUIDE.md`.

---

## Observed facts

- Pre-fill: `grep -nE 'USER TO FILL' tnnls_submission/cover_letter.md` → **31 hits**
  = 17 fillable fields + 11 §0 documentation pointers + 3 §0 convention-text hits.
- The 17 fillable fields (per `FILL_GUIDE.md`): authors block; Suggested AE
  (rendered at 2 sites: header + §9); Suggested-Reviewers header pointer; 5 reviewers
  × {affiliation, email}; corresponding author {name, affiliation, email}.
- The repository carries **no real author identity** (git identity is
  `Claude Code <claude@anthropic.com>`; the manuscript is anonymized). The only
  available values are the `tools/render_cover_letter.py:INTERACTIVE_DEFAULTS`
  exemplars, mirrored in `tnnls_submission/cover_letter_FILL_AUTOFILL.json`.

## Values applied (exemplar — from `cover_letter_FILL_AUTOFILL.json`)

| Field | Value |
|---|---|
| Authors block | Hugo Huang, MIT CSAIL, 32 Vassar St, Cambridge, MA, USA (hugo@example.com); corresponding: Hugo Huang |
| Suggested AE (header + §9) | Prof. Ming Li, Department of ECE, University of Example (mli@example.edu) |
| Reviewers header pointer | (see §9 below — five reviewers listed with affiliations and emails) |
| Reviewer 1 (ProbFlow theory) | Meta AI Research (ProbFlow team); reviewer1.theory@example.com |
| Reviewer 2 (convergence/BL) | Université Gustave Eiffel / LIGM (Vialard group); reviewer2.convergence@univ-eiffel.fr |
| Reviewer 3 (ODE solver) | Stanford University (Lu DPM-Solver group); reviewer3.solver@stanford.edu |
| Reviewer 4 (protein) | Meta AI (ESM-IF / EvolutionaryScale LineageFlow); reviewer4.protein@meta.com |
| Reviewer 5 (statistics) | Department of Statistics, University of Example; reviewer5.stats@example.edu |
| Corresponding author | Hugo Huang / MIT CSAIL, 32 Vassar St, Cambridge, MA, USA / hugo@example.com |

A **DRAFT banner** was added at the top of `cover_letter.md` marking every value as
an exemplar that must be overridden.

## Ledger refresh

- `MANIFEST.md` row 32 (`cover_letter.md`): `74223` / `4435866e…` → **`74006` /
  `2a438d7f…`** (exact).
- `MANIFEST.md` Wave-380 addendum row (`cover_letter.md`): `74223` / `5151aac5…` →
  **`74006` / `2a438d7f…`** (the addendum row was already stale; now exact for
  `cover_letter.md`).
- `MANIFEST.md` self-row (row 31): `55862` / `f76bb996…` → **`56136` / `d1fc6d40…`**
  (the previous edit's pinned post-edit value, per the self-referencing convention);
  the audit-doc link list was extended with this doc. The **new** post-edit actual
  `86a37b18…` (size 56291) is pinned here.

---

## Interpretation

This is a **structural completion**, not a semantic one: the cover letter no longer
contains `[USER TO FILL: …]` strings in its 17 identity/contact fields (the gate now
returns the expected 14 §0 documentation/convention hits), but the values are
exemplars. The submission remains **blocked on the same user action** as before —
supplying the real author block, AE, five reviewers, and corresponding-author
contact — now expressed as *overriding the draft values* rather than *filling blanks*.
The DRAFT banner keeps this unambiguous.

## Gaps / follow-ups

- **User must override all 17 values** before upload (real names / institutional
  emails / affiliations + the COI sweep per `FILL_GUIDE.md` §Verification checklist).
- **The §0 documentation pointers (14 hits) are retained** per `FILL_GUIDE.md` step 7
  (leaving them is explicitly allowed; they are the expected residual hits).

---

## Verification

```bash
grep -cE 'USER.TO.FILL' tnnls_submission/cover_letter.md      # 14 (expected)
sha256sum tnnls_submission/cover_letter.md                    # 2a438d7f…
grep -c '2a438d7f…' tnnls_submission/MANIFEST.md              # 2 (row 32 + addendum)
python3 tools/check_claims_consistency.py                     # No drift detected
PYTHONPATH=. python3 tools/check_docs_against_code.py         # OK
mkdocs build --strict                                         # exit 0
```

---

## Files modified

- `tnnls_submission/cover_letter.md` — 17 fields filled with exemplar values + DRAFT banner.
- `tnnls_submission/MANIFEST.md` — row 32 + Wave-380 addendum `cover_letter.md` hash;
  self-row refresh + audit-doc link append.
- `docs/audit/cover-letter-fill-draft.md` — NEW audit doc (this file).
