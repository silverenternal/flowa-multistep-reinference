# Wave 374 — Final PDF symbol, list, and page-break check

**Date:** 2026-09-27  
**Base commit:** `f01f64a`  
**Scope:** `docs/drafts/paper-A-final.tex` and rebuilt PDF. No experiment or code change; no model sidecar was activated.

## Observed facts

1. The §II.B equation in TeX uses `\Phi_T^{v_\theta}` and the surrounding prose uses `v_\theta`; there is no `v_g` token in the source. The extracted or recognized PDF glyph can resemble `g`, but the source and compiled mathematical symbol are theta.
2. The four Protocol entries in §III.A and nine adapter-method entries in §V.B were each enclosed in a separate `enumerate` environment. LaTeX therefore printed `1)` for every entry. The repeated environment boundaries were merged into one four-item and one nine-item list; the rebuilt PDF now prints `1)`–`4)` and `1)`–`9)`.
3. The §IX limitations sentence was complete in TeX, but the PDF page boundary split it after “intermediate.” The prose was tightened without changing its claims, and a column break now follows a complete sentence. Page 7 ends after “the intermediate uses one seed”; page 8 starts with the complete future-work sentence.

## Interpretation and remaining limits

The symbol concern was an extraction or OCR reading, while list numbering and the sentence break were real typesetting defects. The PDF remains eight IEEEtran double-column pages. This check changes no metric, status, theorem, experiment protocol, or vendored code.

## Verification

The final TeX was compiled twice with `pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/tmp docs/drafts/paper-A-final.tex`. `pdfinfo` and `pdftotext -layout` checked page count, numbering, and the page 7/8 boundary. Manifest SHA-256 and size rows for the TeX/PDF were refreshed. Claims consistency, strict MkDocs build, D.4 30/30 regression vectors, `git diff --check`, and vendored-path checks are recorded in the final turn checks.
