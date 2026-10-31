# The submission checklist disagreed with itself, and with the letter

**Date:** 2026-10-31
**Surface:** `tnnls_submission/submission_checklist.md` (hash-pinned, frozen package)
**Change:** five in-place reading corrections + one additive section
**No result number, status label, verdict or claim changed.**

## 1. Observed

The checklist is the file an author works through before uploading. Two of its
readings contradicted the same file's own banner, and one contradicted the
artifact it names.

| line | said | is |
|---|---|---|
| 22 | "Current build **11 pages**" | `pdfinfo` → 12; the 2026-10-27 banner 15 lines above says 12; `MANIFEST.md` records 12 pages / 615789 bytes |
| 74 | "typeset to double-column **14-page** TNNLS format" | 12 |
| 42 | "Pytest: **5582** passed / 180 skipped / 0 xfailed (2026-10-29 CPU run, 12 torch-dependent `test_paper_metrics.py` tests excluded)" | 5646 passed / 180 skipped / 0 failed (2026-10-31) |
| 80, 104 | "paste the **three** bullets" / "**3** editor-facing highlights" | `highlights.md` states "Five highlights" and lists five |
| 23 | "**All 11 USER ACTION placeholders filled before upload**" (checked) | the letter carries example identities, not filled placeholders |

The page-count pair is the sharpest: the file says 12 at the top and 11 in the
Manuscript row, so a reader cannot tell which reading is current.

The pytest row's parenthetical was also the wrong *cause*. The 12
`test_paper_metrics.py` failures were an import-order defect in the test's mock,
fixed 2026-10-30 (`docs/audit/pytest-order-dependence.md`); they now run and
pass, so "excluded" describes a state that no longer exists.

## 2. The cover letter

```
$ grep -oE 'USER.TO.FILL' tnnls_submission/cover_letter.md | wc -l   -> 14
$ grep -oE '\[USER TO FILL[^]]*\]' tnnls_submission/cover_letter.md | wc -l -> 12
$ grep -oE 'USER.TO.FILL' docs/cover-letter-tnnls.md | wc -l         -> 31
$ grep -oE '\[USER TO FILL[^]]*\]' docs/cover-letter-tnnls.md | wc -l -> 20
```

The shipped snapshot's 11 placeholders all sit in §0's documentation list,
which explains where placeholders would go. The body has none: it carries
`hugo@example.com` at the corresponding-author line and
`University of Example (mli@example.edu)` at the suggested-reviewer header.
The canonical source `docs/cover-letter-tnnls.md` is where the 20 brackets and
the 9 real body fields live.

So three documents describe three different states — the checklist says
"11 placeholders filled", `SUBMISSION_READINESS.md` says "17 USER_TO_FILL
placeholders preserved verbatim", `FILL_GUIDE.md` says "31 occurrences / 17
distinct fields". Only the last is measured, and it is measured against the
canonical source, not the snapshot.

Nothing here was "fixed" by editing the letter. Filling it is the user-gated
upload blocker (`SUBMISSION_READINESS.md` §2 PENDING #1), and rewriting a
frozen package file to insert placeholder text would destroy the artifact the
hash pins. The correction is to the description.

## 3. The 24.6×

The *Reviewer-facing strengths* bullet read

```
- **24.6× wall-clock fix:** CUDA-graph capture 4.24× speedup (76.8% closure)
```

which parses as "the fix bought 24.6×". It did not. 24.6× is the **pre-fix
N=1000 per-record ratio** (baseline 37.83 ms vs framework 930.52 ms,
`docs/audit/algorithm_4arm/p2-wallclock-fix.md` §2). The measured speedup at
matched NFE=50 / BATCH=64 is 4.31× (4.24× on re-measurement), taking the
framework/baseline ratio 3.40× → 1.26×. Both numbers are real and they come
from different harnesses; the bullet put them in one sentence without saying
so. `tnnls_submission/tables.md` Table 4 already carries the correct pair, and
`tools/check_tables_inventory.py` recomputes it — the checklist was the only
place the two were conflated.

## 4. What was changed

Five in-place corrections (page count ×2, highlights count ×2, pytest row) and
one additive section, *Reading corrections (2026-10-31, ADDITIVE)*, carrying
the cover-letter and 24.6× items.

In place rather than additive for the first five because each is a reading that
contradicts another line in the same file; an additive note would leave the
reader holding two versions of a page count. Additive for the last two because
they describe state the user must act on, and because a checklist is a
contract with its author, not a document to be rewritten underneath them.

## 5. Deliberately untouched

* The statistical rows (TOST 14/16, Jonckheere-Terpstra z, DerSimonian-Laird
  pooled `d_z`, non-inferiority `p`), the K1–K6 disclosure rows, and the
  wall-clock table row. These are results; changing them is a claim change,
  which this pass does not make.
* The dated annotation at line 256 ("Pages: 11 … sha256 `a9883fc9…`"). It is a
  snapshot of the 2026-10-12 build and says so.
* The `[x]` state of "Cover letter uploaded to Editorial Manager". The
  repository records no upload, but whether an upload happened is not
  something a file can assert either way; the additive section states what the
  artifact contains instead of flipping the box.

## 6. Verification

```
pdfinfo docs/drafts/paper-A-final.pdf            Pages: 12
render_cover_letter.py --validate               17/17 markers gone, 20 exemplar hits
check_submission_manifest                        rows=26 drift=0 ledger_drift=0
sha256sum -c SHA256SUMS                          22 OK
22/22 gate chain                                 OK
```
