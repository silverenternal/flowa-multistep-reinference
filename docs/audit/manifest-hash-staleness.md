# Submission manifest: the manuscript rows are current, the package rows are not

**Date:** 2026-10-28
**Scope:** `tnnls_submission/MANIFEST.md`, every `| file | bytes | sha256 |` row.
**Status:** CPU-only. No frozen file edited.
**Reproducer:** `tools/check_submission_manifest.py`, `tests/test_submission_manifest.py`.

## 0. Result

27 rows. 11 resolve exactly, 13 are stale (10 distinct files, three listed
twice), 2 are superseded historical artifacts, 1 is the manifest itself.

| Class | Count | Files |
|---|---:|---|
| `ok` | 11 | `FILL_GUIDE.md`, `data_availability.md`, `supplementary/README.md`, `supplementary_bundle.zip`, 6 figure PNGs |
| `STALE` | 13 rows / 10 files | `README.md`, `MANIFEST.md`, `cover_letter.md`, `highlights.md`, `tables.md`, `figures.md`, `submission_checklist.md`, `paper-A-final.{md,tex,pdf}` |
| `superseded` | 2 | `paper-flat-ieeetran.{pdf,tex}` — absent, and marked "do NOT upload" |
| `self-reference` | 1 | `MANIFEST.md` (see §3) |

## 1. The manuscript artifacts are fine — via the addendum, not the table

The table's three manuscript rows record the **Wave 331** build:

| Row | Table | On disk |
|---|---|---|
| `paper-A-final.md` | 213 574 B / `c6978764…` | 226 324 B / `b66ea07a…` |
| `paper-A-final.tex` | 66 156 B / `cd600246…` | 74 254 B / `0847cd1e…` |
| `paper-A-final.pdf` | 448 996 B / `b3fd1c3e…` | 615 789 B / `8b94570c…` |

But the 2026-10-27 packaging addendum at the top of the same file declares
`b66ea07a…` / `0847cd1e…` / `8b94570c…` with those exact byte counts, and states
that it supersedes every SHA-256 reading that differs. **All three match on
disk, byte for byte.** So the manifest is self-consistent under its own
precedence rule; a reviewer who reads the addendum first gets the right values.

The problem is that the same precedence rule does not help for the other seven
files, because no addendum gives their current hashes.

## 2. Seven package documents have no current hash anywhere

| File | Table says | Actual |
|---|---:|---:|
| `README.md` | 12 638 B | 12 640 B |
| `cover_letter.md` | 74 060 B | 75 400 B |
| `highlights.md` | 9 098 B | 3 422 B |
| `tables.md` | 22 729 B | 24 270 B |
| `figures.md` | 53 656 B | 53 736 B |
| `submission_checklist.md` | 34 347 B | 35 402 B |
| `MANIFEST.md` | 73 488 B | 86 979 B |

Each difference is explained by a later additive pass (the Wave 348 path fixes,
the Wave 358 table-of-tables, the Wave 361 figure catalog, the Wave 372–385
manuscript addenda). None is a corruption. But a reviewer who follows the table
gets a hash mismatch on seven of the eleven package documents and has no
authoritative value to compare against.

`highlights.md` is the extreme case: the table records 9 098 bytes and the file
is 3 422. That is not a small edit — it is the "rebuilt as a single five-bullet
list" rewrite described in the packaging addendum, after which the row was never
refreshed.

## 3. `MANIFEST.md` cannot carry its own hash

The row `| MANIFEST.md | 73488 | cc640412… |` is unsatisfiable by construction:
writing the hash into the file changes the file. Any refresh has to either drop
the row or move it to an external `SHA256SUMS` (which the package already uses
for the R1 3-seed ledger, `verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS`).

## 4. The two absent rows are correctly labelled

`paper-flat-ieeetran.pdf` and `.tex` do not exist, and both descriptions say
"**SUPERSEDED by paper-A-final…** … archived for historical reference; do NOT
upload". The checker treats them as superseded rather than missing. No action
needed beyond, optionally, deleting the rows.

## 5. Duplicates

`paper-A-final.{md,tex,pdf}` and `cover_letter.md` each appear twice in the
table (rows 11–13 and 24–26, and rows 3 and 27). The duplicates carry the same
stale values, so they do not create a contradiction — but a refresh has to
update both copies or the file will disagree with itself.

## 6. Reproduction

```
python3 tools/check_submission_manifest.py        # 27 rows, 0 unknown
python3 -m pytest tests/test_submission_manifest.py -q
```

The checker resolves every row, skips rows marked superseded, checks the three
addendum-declared artifacts separately, and exits non-zero on any stale row that
is not in `KNOWN_STALE`. Deleting an entry from that set is how a refresh is
recorded; `test_known_stale_list_stays_honest` fails if an entry is left behind
after the row is fixed.

## 7. Authorisation required

Refreshing seven size/SHA pairs plus the three table rows (and deciding what to
do about the self-referential row) is a mechanical edit of
`tnnls_submission/MANIFEST.md`. It changes no number the paper cites and no
claim; it only makes the integrity table verifiable again.
