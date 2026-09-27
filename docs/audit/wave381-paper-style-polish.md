# Wave 381 — Submission-style prose polish

**Date:** 2026-09-27  
**Workflow:** `academic-paper` / `academic-paper-review` writing-quality pass.

## Edits

- Recast the mechanism section in research-claim language rather than engineering-report language.
- Tightened the inference-dynamics explanation so the frozen ODE and the composite map are stated in one sentence.
- Reframed theorem-to-metric wording as complementary diagnostics and empirical operating curves.
- Preserved all quantitative values, evidence status labels, and protocol boundaries.
- Kept the 10-page IEEEtran layout and mechanism figure/table unchanged in structure.

## Checks

- `pdflatex` twice: pass; PDF remains 10 pages.
- No overfull boxes or fatal LaTeX errors.
- `python3 tools/check_claims_consistency.py`: pass.
- `mkdocs build --strict`: pass.
