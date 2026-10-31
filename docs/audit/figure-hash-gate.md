# The figure table pinned 37 digests and nothing checked them

**Date:** 2026-10-31
**Surface:** `tnnls_submission/figures.md` (editor-facing figure inventory)
**Change:** new gate `tools/check_figure_hashes.py` + 7 tests; wired into
`todo.json` `gate_chain` (entry 23) and CI
**No result number, status label, verdict or claim changed.**

## 1. Observed

`figures.md` is the file an editor uses to confirm they hold the figures the
manuscript refers to. Each of its 37 rows names a PNG, a SHA-256 and a byte
size. Three hash checkers exist and each stops just short of it:

| Checker | Covers |
|---|---|
| `check_artifact_hashes` | the manuscript artifacts cited in the two root READMEs (8 citations) |
| `check_submission_manifest` | the `tnnls_submission/` ledger rows and `SHA256SUMS` |
| `check_paper_data_manifest` | `paper-data/*/SOURCE.md` |
| — | **`tnnls_submission/figures.md`: 37 digests, unchecked** |

The digests are not decoration: five of the figures are the paper's headline
plots, and the row is the only place the package states which bytes those are.

## 2. What the new check does

A join, not a recomputation: every row's digest and size must equal the file's
real digest and size, and the file must resolve under one of the four tracked
roots (`docs/figures`, `paper-figures/main`, `paper-figures/appendix`,
`paper-data`).

Two fail-closed decisions, both learned from earlier gates in this chain:

* **A table that parses to zero rows is a failure, not a clean result.** The
  `drift_33` gate read "the scan did not run" as "no drift"; a regex that stops
  matching would do the same thing here. It reports `unparsed`.
* **Copies must agree.** The same PNG legitimately exists in two roots (23 of
  the 37 rows resolve to more than one path). Accepting whichever copy sorts
  first would let a stale duplicate sit next to the shipped file indefinitely.
  Identical copies pass; copies whose bytes differ report `divergent`.

## 3. Current reading

```
python3 tools/check_figure_hashes.py
OK: 37 figure rows match the files on disk
```

No drift today. The gate exists so that the first drift is caught by CI rather
than by an editor who cannot match a figure.

## 4. Deliberately not done

* The sizes are checked but not the pixel dimensions in the same row. Those
  would need an image decoder (`Pillow`), which is not a dependency of the gate
  chain; the digest already pins the bytes, and dimensions are a function of
  the bytes.
* `figures.md`'s prose sections were not rewritten. Several cite
  `docs/audit/waveNNN-*.md`; those are addresses.

## 5. Verification

```
check_figure_hashes                 OK: 37 figure rows match the files on disk
pytest tests/test_tools/test_figure_hashes.py   7 passed
ruff check tools/check_figure_hashes.py          All checks passed
```
