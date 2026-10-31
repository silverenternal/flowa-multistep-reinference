# The README gate table quoted a run that no longer existed

**Date:** 2026-10-31
**Surfaces:** `README.md`, `README.zh.md`, `docs/GATES.md`, `docs/ARCHITECTURE.md`,
`tnnls_submission/cover_letter.md`, `tnnls_submission/FILL_GUIDE.md`,
`tnnls_submission/submission_checklist.md`, `tools/render_cover_letter.py`
**Change:** reading corrections, wave-label compression, one validator repaired
**No result number, status label, verdict or claim changed.**

## 1. Observed

The README's *Submission Gates* table is the page a reviewer reads to decide
whether the package is real. Six of its eight rows quoted a state that no
longer existed, and one row's "Verification" cell named a path that matches
nothing:

| Row | Quoted | Actual |
|---|---|---|
| Pytest | `5155 passed / 196 skipped` (also `subset green` in the gate table) | 5646 passed / 180 skipped / 0 failed |
| Mypy | `0 errors` via `mypy adaptive_reflow/` | 0 errors in 232 files, but only through `.venvs/flowmol3_venv/bin/python -m mypy --strict` |
| Abstract | 183 words, sourced from `docs/drafts/abstract-final.md` | 167 words; that file's own banner says it is *not* the submitted abstract |
| TNNLS package | 7 files | 13 files + a 22-entry `SHA256SUMS` |
| Data integrity | 6/149/0 | 15/703/0 |
| Contracts suite | `tests/test_contracts*.py` | no such glob — the suite is the directory `tests/test_contracts/` |

The last row is the quiet one. `pytest tests/test_contracts*.py` exits 0 with
"no tests ran", so a gate row that looked green was executing nothing. This is
the same shape as the `mypy_0` SKIPPED and the six never-run §6 commands: a
check that reports success without checking.

## 2. The cover letter asked for a grep that could never come back empty

`cover_letter.md` §0 said:

> All placeholders are marked with the `[USER TO FILL: ...]` convention below,
> and they are also tagged inline … The output must be empty before the cover
> letter is uploaded.

The body carried no markers — the shipped letter substitutes
`INTERACTIVE_DEFAULTS` exemplar values — so `grep 'USER TO FILL'` returned the
twelve lines of §0 itself and could never return nothing. An author following
the instruction would either conclude the letter was broken or upload
`hugo@example.com`.

The line numbers in the same section (`line 11`, `line 16`, `line 19`) had also
rotted: they were measured against `docs/cover-letter-tnnls.md`, not against
the file §0 was talking about.

**Fixed** by rewriting §0 around the exemplar values: the 17 fields are named
by section (not line number), and the completion check greps the exemplar
strings themselves — `example.com`, `example.edu`, `univ-eiffel.fr`,
`stanford.edu`, `meta.com`, `to be confirmed at submission`,
`University of Example`, `MIT CSAIL`, `Hugo Huang`, `Ming Li`.

## 3. `--validate` inferred "filled" from "no marker"

`tools/render_cover_letter.py --validate` printed:

```
Summary: 17/17 placeholders filled; 0 still unfilled.
All 17 placeholders are filled.
```

from a letter that still contained `hugo@example.com` at the signature. The
code made the inference explicit in a comment — *"Placeholder no longer
present in the file — already filled"* — which is true only for a letter that
keeps its markers. The shipped letter does not.

Two signals are now reported separately: marker state (`[UNFILLED]` /
`[MARKER GONE]`, never `[FILLED]`), and an exemplar scan that lists every
surviving `INTERACTIVE_DEFAULTS` value with its line number. The summary reads
`17/17 markers gone; 0 still unfilled; 20 exemplar hits`. Four tests in
`tests/test_tools/test_render_cover_letter_validate.py` pin the distinction,
including one that asserts the repository's own letter does not validate as
filled.

## 4. FILL_GUIDE pointed at the wrong file, and following it would have lost work

`FILL_GUIDE.md` said its target was `tnnls_submission/cover_letter.md` but its
line numbers were measured on `docs/cover-letter-tnnls.md`. Worse, the two
files are not interchangeable: the uploadable letter carries three 2026-10-27
addenda (the retitle, the current-manuscript summary, the mechanism addendum)
that the source does not. An author who re-rendered from the source would have
silently reverted the title and dropped the addenda.

The guide now states the 2026-10-31 state at the top, tells the author to edit
in place rather than re-render, and replaces the marker-grep steps with
`--validate`.

## 5. Wave labels

Reviewer-facing pages counted internal iterations in prose. Removed from
`docs/GATES.md` (9) and `docs/ARCHITECTURE.md` (27 headings and sentences);
commit hashes, dates and `docs/audit/waveNNN-*.md` paths are unchanged,
because those are addresses rather than chronology. `verification_outputs/waveNNN-*/`
paths in `tables.md`, `figures.md` and `data_availability.md` were left alone
for the same reason.

## 6. Verification

```
check_reviewer_pointers                        checked=1020 dead=0
pytest tests/test_tools tests/test_docs        469 passed / 53 skipped
render_cover_letter.py --validate              17/17 markers gone, 0 unfilled, 20 exemplar hits
check_submission_manifest                      rows=26 drift=0 ledger_drift=0
sha256sum -c SHA256SUMS                        22 OK
mkdocs build --strict                          exit 0
```
