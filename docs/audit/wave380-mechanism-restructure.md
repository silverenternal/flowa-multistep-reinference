# Wave 380 — Mechanism-centered manuscript restructure

**Date:** 2026-09-27  
**Scope:** `docs/drafts/paper-A-final.md`, `docs/drafts/paper-A-final.tex`, generated PDF, and TNNLS package metadata.  
**Workflow:** `flowa-paper-evidence` + `academic-paper-review`.

## Change

The manuscript is reorganized around the implemented causal chain:

1. checkpoint-native state geometry;
2. bounded restart state intervention;
3. residual/difficulty-aware capacity allocation;
4. frozen ODE response and metric observation.

The LaTeX manuscript now includes a mechanism subsection with the state-transition equation and a mechanism-to-evidence table. The empirical section adds a causal-ordering subsection centered on Wave 184, Kanzi R2, and the cross-adapter R6 difficulty pattern. The framework verdict heading is renamed to `Scope of the observed operating boundaries`. The conclusion presents FlowA as a geometry-aware inference layer.

## Evidence used

- Wave 184 / CLM-049: fixed NFE=100, `n_rounds ∈ {1,2,3,5,7}`; synthetic LineageFlow gain persists at all round counts, isolating restart glue.
- Kanzi R2: native latent → inverse projection → DAE decoder → backbone ODE path; index-matched two-sample RMSD 0.9020 → 0.8798 Å at `N=1000`.
- R6: hard/easy pLDDT effects replicate across Kanzi and LineageFlow, motivating tier-aware capacity allocation.
- `docs/audit/wave375-image-feedback-path.md`: image drivers are presented as adapter-specific operating regimes rather than being used to over-attribute endpoint feedback.

## Verification

- `python3 tools/check_claims_consistency.py`: pass, no drift.
- `pdflatex` twice: pass, no fatal errors.
- PDF: 10 pages, IEEEtran double-column; embedded Type 1/math fonts.
- No vendored upstream files changed.
