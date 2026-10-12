# GAP-19 — Venue-fit alignment: self-assessed acceptance probability removed from the submission docs

**Date:** 2026-10-12
**Increment:** GAP-19 (from `todo/SUBMISSION-GAP-CHECKLIST.md`)
**Decision:** user-selected option **"移除，与手稿对齐"** (remove, align with the manuscript)
**Status:** RESOLVED

---

## 1. Observed facts

1. **The manuscript carries no Q1 acceptance-probability estimate.**
   `grep -nE "Q1|acceptance" docs/drafts/paper-A-final.md` returns only two
   "acceptance test" hits (§3.4.2) — no acceptance-probability disclosure. The
   removal is deliberate: `git log --oneline -S "60-75" -- docs/drafts/paper-A-final.md`
   shows commit `62154e0` *"Wave 370 (USER-EXPLICIT DESTRUCTIVE REWRITE …): …
   §11.1 'solid Q2 / borderline Q1 contribution' sentence removed (author
   self-rating); §11.1 'Wave 354 P3 ADDITIVE paragraph' deleted; §11.2 … deleted
   …"*.

2. **Three submission-facing surfaces still cited the removed estimate.**
   - `tnnls_submission/SUBMISSION_READINESS.md` — line 14 ("the Q1
     acceptance-probability 60-75 % is cited here verbatim"), an entire §5
     ("Q1 acceptance probability — 60-75 %", lines 132–161), a §7 summary-table
     row, and a §7 single-line JSON key `q1_acceptance_probability_pct: 60-75%`;
     plus §8.3 and §9 references.
   - `tnnls_submission/submission_checklist.md:87` — "**TNNLS acceptance
     probability:** **50-65%**".
   - `tnnls_submission/MANIFEST.md` row 56 — the manuscript provenance chain
     records the *addition* of the disclosure (Wave 354 P3) but not its later
     removal.

3. **The two numeric claims contradicted each other** (60-75 % in
   `SUBMISSION_READINESS.md` vs 50-65 % in `submission_checklist.md`), and the
   `SUBMISSION_READINESS.md` attribution ("per `docs/drafts/paper-A-final.md`
   §11.1 (b) verbatim disclosure") was **false**: §11.1 no longer carries it.

4. **`SUBMISSION_READINESS.md` is not in the MANIFEST SHA ledger** (its own
   §11 / §8.2 state it does not enter the ledger); `submission_checklist.md`
   **is** (MANIFEST row 54).

## 2. Interpretation

The estimate is a self-assessed *meta*-projection of acceptance likelihood, not a
paper quantity. The user deliberately deleted it from the manuscript at Wave 370.
Leaving it in the submission-facing docs produced (a) a false attribution to a
manuscript section that no longer contains it and (b) an internal contradiction
between two submission docs. The user's decision was to remove the self-assessed
probability from the submission docs so they align with the manuscript, rather
than to retain it as a historical estimate.

## 3. Changes

| File | Change |
|---|---|
| `tnnls_submission/SUBMISSION_READINESS.md` | §5 retitled "Venue fit — no self-assessed acceptance probability" + a removal note; the numeric estimate (60-75 % / prior 45-60 %) stripped from §5.1–§5.3; reviewer-facing strengths + risk factors retained as qualitative notes (§5.1 / §5.2). Line 14 claim corrected; §7 summary-table row → "Not asserted"; §7 JSON key → `not_asserted`; §8.3 + §9 numeric references stripped. New §19 addendum records the in-place edit (the doc's only exception to its §10–§18 additive convention). **Not in the MANIFEST ledger → no SHA row.** |
| `tnnls_submission/submission_checklist.md` | "Acceptance probability estimate" section retitled "Reviewer-facing strengths"; the "**TNNLS acceptance probability:** **50-65%**" line removed; the 6 improvement bullets retained. **MANIFEST row 54 SHA + size refreshed.** |
| `tnnls_submission/MANIFEST.md` | Row 56 (manuscript provenance) gains an additive note that Wave 370 removed the disclosure; row 54 (`submission_checklist.md`) SHA `35c2814a…`/33589 → `74689694…`/34347; row 47 (self-SHA) set to the pre-edit actual `55f0ba7f…`/72765. |

No metric, claim number, per-cell status label, theorem statement, or paper
quantity was changed. The removal is of a self-assessed probability only.

## 4. Gates (run after the edits)

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable (combined) | `python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | 72 passed |
| claims consistency | `python tools/check_claims_consistency.py` | no drift |
| docs-against-code | `python tools/check_docs_against_code.py` | OK |
| mkdocs strict | `mkdocs build --strict` | exit 0 |
| readiness verifier | `python tools/verify_submission_readiness.py` | READY_WITH_SKIPS: mypy_0 |

## 5. Digests (SHA-256)

| File | Pre-edit | Post-edit |
|---|---|---|
| `docs/drafts/paper-A-final.md` | (unchanged) | `49e8880e85c1dac56551422cb039581a8adf74cd80472b644205db2c2b8baf33` |
| `tnnls_submission/submission_checklist.md` | `35c2814ab19ddc538845b4852b993444cea6a1fa468bdd85027d6aac2cebaef4` (33589 B) | `74689694a6aec1601ce7e9ec3de78a9f5bb03c2e56681ed77ede412da898d47b` (34347 B) |
| `tnnls_submission/SUBMISSION_READINESS.md` | (not ledgered) | `3d4097ad7fe54d36b6f59f686e80e98e9125c25c47bf9106b3645dffc74750b1` (48660 B) |
| `tnnls_submission/MANIFEST.md` | `55f0ba7fa580a5b5e3fe0d156e70fe545564a8b34b412d28a10c1f8b71328fb9` (72765 B) | `cc640412ab7092658dad04d112ef0ef9e540ac9c3cd87e7a8ae6e0b8fbeb511a` (73488 B) |

**Self-referencing-SHA note.** MANIFEST row 47 displays the hash of the file
*before* the current edit (`55f0ba7f…`); the post-edit actual is
`cc640412ab7092658dad04d112ef0ef9e540ac9c3cd87e7a8ae6e0b8fbeb511a` (73488 B),
recorded here per the established convention.

## 6. Caveats

- The manuscript PDF (`.tex` build) is **not** affected: the `.tex` contains none
  of the changed submission-doc text, and the manuscript markdown was not edited
  in this increment.
- `docs/audit/engineering/p3-journal-decision.md` retains its historical
  "TNNLS ~50–65 %" recommendation. It is a dated engineering-decision audit
  record (not a submission-facing surface) and is left as historical evidence.
