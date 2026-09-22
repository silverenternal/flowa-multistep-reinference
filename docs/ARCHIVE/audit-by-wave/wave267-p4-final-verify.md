# Wave 267 P4 — Final Verify

**Date:** 2026-09-22
**Branch:** main
**Scope:** README.md only (no source code changes)

## Tasks executed

1. Read README.md "Repository Structure" section.
2. Split into A. Core Framework + B. Reproduction & Verification.
3. Updated "Reproducing the Paper" section to point at the `reproduce/` directory (one-click + per-cell standalone scripts).
4. Verified all three submission gates.

## Gate results

| Gate | State | Command |
|---|---|---|
| D.4 byte-stable regression | **30/30 PASS** | `.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q` |
| mkdocs build --strict | **0 warnings** | `mkdocs build --strict` |
| claims consistency | **no drift** | `python3 tools/check_claims_consistency.py` |

## README structure (after split)

### A. Core Framework
- `adaptive_reflow/` (universal / algorithm / framework / stats / adapters / contracts)
- `configs/`

### B. Reproduction & Verification
- `reproduce/`
- `scripts/`
- `tests/`
- `tools/`
- `verification_outputs/`
- `tnnls_submission/`
- `docs/`
- `eaai_submission/`
- `data/`

## Reproducing the Paper (after update)

- One-click: `bash reproduce/verify_all_headlines.sh` → "All 7/7 R-level headlines verified"
- Per-cell scripts: `reproduce/01_R1_LineageFlow.sh` ... `reproduce/07_R6_MNIST_TierAware.sh`
- Each script handles env activation → data check → run → result verification

## Hard rules compliance

- [x] No source code modified (README only)
- [x] No background tasks touched
- [x] D.4 30/30 PASS preserved
- [x] mkdocs 0 warnings preserved
- [x] claims consistency no drift preserved
- [x] No new internal IDs introduced

## Notes

- Repository structure split follows user feedback from deepseek老师 to align README with "一区课题" standards.
- Per-cell scripts already exist in `reproduce/` directory (Wave 267 P1).
- One-click verification script `reproduce/verify_all_headlines.sh` exists and is wired into README.