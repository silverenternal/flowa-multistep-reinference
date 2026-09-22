# Wave 274 P4 — paper-tnnls.pdf rebuild BLOCKED

**Status:** BLOCKED
**Date:** 2026-09-22
**Wave / phase:** Wave 274 / P4 (TNNLS submission)

## Blocker

The IEEEtran LaTeX class (`IEEEtran.cls`) is required by the requested TNNLS rebuild
(`\documentclass[journal]{IEEEtran}`, two-column), but it is **not installed** in the
local TeX Live 2026/Arch Linux distribution:

```
$ kpsewhich IEEEtran.cls
(empty — no path returned)
```

The source-phase environment probe also reported `networkAvailable: false`, so the
class file cannot be downloaded on demand (e.g. via `tlmgr install ieeetran` or a
manual fetch from CTAN).

## Decision

Per Wave 274 source-phase recommendation `"BLOCKED-need-ieeetran"` and EXECUTE
option B (`ieeeTranAvailable=false`):

- **No fake compile attempted.** A `pdflatex paper-tnnls.tex` run on a plain
  `\documentclass[journal]{IEEEtran}` source would fail with
  `! LaTeX Error: File 'IEEEtran.cls' not found.`, producing either a fatal error
  or a misleading 0-page PDF.
- **Existing `docs/paper-tnnls.pdf` left untouched.** It remains the
  Sept-21 22:47 build (505017 bytes) produced from `paper-eaai.tex` under the
  NeurIPS template. The README headline numbers may have drifted since that
  build (this is a known divergence tracked elsewhere in Wave 274 P1/P2), but
  rebuilding the PDF against the IEEEtran template is out of scope for this run.

## To unblock the rebuild

1. Restore network access, then run:
   ```
   tlmgr install ieeetran
   ```
   (or fetch `IEEEtran.cls`, `IEEEtran.clo`, and the supporting BibTeX style
   files from CTAN into a local `texmf` tree and `texhash`).
2. Verify with:
   ```
   kpsewhich IEEEtran.cls   # should now return a path
   ```
3. Re-run Wave 274 P4 with `recommendation: "rebuild-from-new-tex"` and
   `ieeeTranAvailable: true`. The EXECUTE option A path will then create
   `docs/drafts/paper-tnnls.tex`, run `pdflatex` twice into
   `/tmp/wf274-paper/`, and promote the resulting PDF to `docs/paper-tnnls.pdf`.

## Files NOT modified

- `docs/paper-tnnls.pdf` — untouched (build artifact from 2026-09-21).
- `docs/drafts/paper-flattened-draft.md` — untouched.
- `docs/build_pdf/` — no new artifacts written here (build scratch lives in
  `/tmp/wf274-paper/` and was not even created in this blocked run).
