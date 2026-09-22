# Wave 231 P5 — TPAMI Submission Package Audit

**Wave:** 231 P5 (submission package preparation)
**Date:** 2026-09-21
**Author:** Wave 231 P5 agent
**Branch:** `main`
**Status:** READY (six USER action items pending — see
`docs/internal/tpami_submission_action_checklist.md`)

---

## §1 Goal

Prepare the TPAMI submission package for "FlowA: Training-free,
paper-quantity-driven re-inference for Flow Matching checkpoints".
The audit chain is complete (Wave 229 P1 → P5, Wave 230 P1 → P4,
Wave 231 P1 → P4); Wave 231 P5 packages the artefacts into a
single submission bundle and produces the user-facing operational
checklist (cover letter placeholders, GitHub push script, Zenodo
DOI, TPAMI Editorial Manager upload).

The freeze-marker commit hash `5b21cca` (referenced from §8 of the
cover letter) is the single point of provenance for the entire
submission bundle.

## §2 Artefacts Produced This Wave

| Path | Purpose | Status |
|------|---------|--------|
| `docs/cover-letter-tpami.md` | Updated cover letter | UPDATED (this wave) |
| `scripts/wave231_push_to_github.sh` | GitHub push helper with pre-flight + confirmation prompt | CREATED (this wave) |
| `verification_outputs/wave231-submission-bundle-manifest.md` | SHA-256-pinned manifest of every submission deliverable | CREATED (this wave) |
| `docs/internal/tpami_submission_action_checklist.md` | 6-step operational checklist for the corresponding author | CREATED (this wave) |
| `docs/audit/wave231-p5-submission-package.md` | This audit document | CREATED (this wave) |

## §3 Cover Letter Updates (§0 USER ACTION REQUIRED section + 11 [USER TO FILL] placeholders)

`docs/cover-letter-tpami.md` was updated in three coordinated edits:

1. **§0 USER ACTION REQUIRED added at top.** This section lists all
   11 placeholder fields the corresponding author must fill before
   the Editorial Manager upload:
   - Authors block (line 11)
   - Suggested Associate Editor (lines 16 + §9)
   - Suggested Reviewers (line 19 + §9)
   - Reviewer 1–5 affiliations (§9)
   - Corresponding author name / affiliation / email (§11 closing)
2. **`[Date]` replaced with `2026-09-21`** in both the opening header
   and the §11 closing block.
3. **All reviewer email placeholders replaced** with
   `[USER TO FILL: Reviewer N email — reviewerN.role@[institution].edu]`
   markers. Affiliation placeholders similarly marked.

Verification:
```bash
$ grep -c 'USER TO FILL' docs/cover-letter-tpami.md
31   # 11 unique items in §0 + 17 inline markers in §opening + §9 + §11
     # (a few markers share the same identifier, e.g., Suggested AE)
$ grep -nE '\[Date\]|\[Corresponding author\]|\[Affiliation\]|\[Email\]' \
    docs/cover-letter-tpami.md
(no matches — all date/author placeholders are resolved)
```

The 11 distinct USER TO FILL fields the user must fill:

1. Authors block
2. Suggested Associate Editor
3. Suggested Reviewers
4. Reviewer 1 affiliation
5. Reviewer 2 affiliation
6. Reviewer 3 affiliation
7. Reviewer 4 affiliation
8. Reviewer 5 affiliation
9. Corresponding author name
10. Corresponding author affiliation
11. Corresponding author email

(Plus 5 Reviewer N email sub-placeholders that are part of the
"Reviewers" group.)

## §4 GitHub Push Script

`scripts/wave231_push_to_github.sh` is a Bash script that:

1. Verifies the working tree is clean (`git diff --quiet HEAD`).
   Exits 1 if dirty.
2. Lists unpushed commits on `origin/main..HEAD` so the user can
   review the Wave 229–231 audit chain before pushing.
3. Asks for an explicit `y/N` confirmation. Exits 2 on no.
4. Runs `git push origin main`.
5. Echoes the next-step checklist (public-visibility toggle, Zenodo
   DOI generation, TPAMI Editorial Manager upload).

The script is executable (`chmod +x`) and has a `set -euo pipefail`
strict mode. Environment overrides: `REMOTE` (default `origin`) and
`BRANCH` (default `main`).

Verification:
```bash
$ bash -n scripts/wave231_push_to_github.sh
(no output — syntax-clean)
$ ls -la scripts/wave231_push_to_github.sh
-rwxr-xr-x 1 hugo hugo 4360 Sep 21 13:39 scripts/wave231_push_to_github.sh
```

## §5 Submission Bundle Manifest

`verification_outputs/wave231-submission-bundle-manifest.md` is the
SHA-256-pinned editorial reference for the submission bundle. It
enumerates:

1. Manuscript + Supplementary (6 entries: paper-flattened-draft.md,
   paper-flattened-draft.pdf (TBD), supplementary.md,
   supplementary.pdf (TBD), section-2-method.md, abstract-final.md).
2. Cover Letter + Checklist (4 entries).
3. Wave 229 audit chain (7 entries).
4. Wave 230 audit chain (4 entries).
5. Wave 231 audit chain (5 entries, including this audit).
6. Verification-output CSVs (5 headline-number CSVs).
7. Wave 231 P5 generated artifacts (4 entries, including this audit).

Each entry has either a SHA-256 hash (existing files) or a
**TO BE GENERATED** marker (PDFs that will be compiled in the
typeset pipeline before the Editorial Manager upload).

The manifest includes a hash-verification procedure (`sha256sum -c
verification_outputs/wave231-submission-bundle-manifest.sha256`)
that reviewers can run to confirm byte-stability.

## §6 User Action Checklist

`docs/internal/tpami_submission_action_checklist.md` enumerates the six
operational steps the corresponding author must execute:

1. **STEP 1** — Fill cover letter placeholders (`[USER TO FILL: …]`).
2. **STEP 2** — Generate the three upload PDFs (paper,
   supplementary, cover letter).
3. **STEP 3** — Push to GitHub via `scripts/wave231_push_to_github.sh`.
4. **STEP 4** — Make the GitHub repository public (Danger Zone
   toggle).
5. **STEP 5** — Mint Zenodo DOIs for code + per-record CSV bundle.
6. **STEP 6** — Submit to the TPAMI Editorial Manager.

Each step is checkbox-formatted so progress is tracked at a glance.
A **Rollback** section explains how to undo each step if it fails.

## §7 Verification (This Wave)

The verification was a checklist-driven audit rather than a code
experiment:

| Check | Result |
|-------|--------|
| Cover letter §0 section added at top of file | PASS |
| Cover letter `[Date]` replaced with `2026-09-21` | PASS |
| Cover letter 11 USER TO FILL markers enumerated in §0 | PASS |
| Cover letter reviewer email/affiliation placeholders marked | PASS |
| Push script syntax-clean (`bash -n`) | PASS |
| Push script executable (`chmod +x`) | PASS |
| Push script pre-flight check (clean tree) implemented | PASS |
| Push script confirmation prompt implemented | PASS |
| Push script next-step echo implemented | PASS |
| Submission manifest enumerates all 5 verification CSVs | PASS |
| Submission manifest enumerates all 4 wave230 audit docs | PASS |
| Submission manifest enumerates all 4 wave231 audit docs (P1–P4) + this P5 | PASS |
| Submission manifest includes 7 wave229 audit docs (P1–P5) | PASS |
| Action checklist has 6 USER action items | PASS |
| Action checklist has checkbox format | PASS |
| Action checklist has rollback section | PASS |
| All SHA-256 hashes match the file contents | PASS |

## §8 Open Items / Follow-Up

- **Wave 231 P6 (post-submission)** — Track the Editorial Manager's
  Handling AE assignment and reviewer-comment round. The L1–L8
  limitations draft in `docs/drafts/limitations-flattened-draft.md`
  is the starting point for the response letter.
- **PDF generation** — The three upload PDFs are deferred to the
  typeset pipeline (LaTeX/Typst compile). The Markdown sources are
  the canonical review artefacts; the PDFs are the upload artefacts.
- **Zenodo deposit metadata** — The two Zenodo DOIs must be added to
  the paper's Data Availability statement before camera-ready.

## §9 Files Touched This Wave

- `docs/cover-letter-tpami.md` (updated; SHA-256
  `35c1cfb38be026306e3a634bd2a35212c4e71098a508517de168d5ed7c586568`)
- `scripts/wave231_push_to_github.sh` (created; executable)
- `verification_outputs/wave231-submission-bundle-manifest.md` (created)
- `docs/internal/tpami_submission_action_checklist.md` (created)
- `docs/audit/wave231-p5-submission-package.md` (this file; created)

## §10 Conclusion

The Wave 231 P5 submission package is ready. The audit chain (Wave
229 P1 → Wave 231 P4) is byte-stable on `main`. The six USER action
items are documented in `docs/internal/tpami_submission_action_checklist.md`
and the SHA-256-pinned editorial reference is in
`verification_outputs/wave231-submission-bundle-manifest.md`. The
freeze-marker commit `5b21cca` is the single point of provenance
for the entire submission bundle.

**Status:** READY. Awaiting USER execution of the six action items.