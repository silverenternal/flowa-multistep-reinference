# Wave 383 — Reformulation positioning and mechanism placement

**Date:** 2026-09-27

## Revision

The manuscript now states the high-level claim explicitly: FlowA reformulates inference on both sides of the sampling relation. The four-interface mechanism section remains the operational decomposition of that reformulation. The title is now **“FlowA: Geometry-Aware State-Intervention Reformulation for Frozen Flow-Matching Checkpoints.”**

The mechanism figure was moved next to the mechanism subsection, after the state-transition equation and mechanism map. Internal wave identifiers were removed from the paper body and replaced with the reviewer-facing “fixed-NFE round-count study.” The cover-letter title was synchronized.

## Verification

- `pdflatex` twice: pass; 10-page IEEEtran PDF.
- No overfull boxes or fatal LaTeX errors.
- `python3 tools/check_claims_consistency.py`: pass, no drift.
- `mkdocs build --strict`: pass.
- Formula environments and theorem statements compile with consistent automatic numbering.
