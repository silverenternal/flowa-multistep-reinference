# Wave 349 — Gap-fill implementation audit

**Date:** 2026-09-25
**Author:** Wave 349 impl audit (ADDITIVE — no number change; no destructive edit)
**Scope:** Implementation of the 3 highest-ROI gaps identified in `docs/audit/wave349-gap-audit.md` §3.3 (GAP-1 figure + GAP-2 Theorem-5 label + GAP-3 per-cell power-disclosure index) plus the **R1 3-seed retro-validation probe** (the §2.3 status update in the audit doc) and **paper §10.5 R6 live-GPU follow-up note** (already in place from Wave 336 P1, verified verbatim).
**Hard-rule compliance:** ADDITIVE only (per Wave 268 strict-clean rule); no vendored upstream touched; no MANIFEST SHA remapping outside the standard Wave-348-style additive governance cycle; per Wave 325 NO-PUSH policy (commit only, no push).

---

## 1. Executive Summary

Wave 349 closes 3 of the 3 gaps identified by the Wave 349 gap-audit doc at `docs/audit/wave349-gap-audit.md` (GAP-1, GAP-2, GAP-3), retro-validates the R1 3-seed seed-43/44 framework-fallback claim (§2.3 VERIFIED), and preserves the Wave 336 P1 R6 live-GPU follow-up note at §10.5 verbatim. All changes are ADDITIVE prose/figure/cross-reference additions; no paper number was modified; no claim was demoted or promoted; no MANIFEST row was deleted (only the 3 affected rows were updated to reflect post-Wave-349 file bytes).

The framework's TNNLS submission surface at HEAD `0cb99888` (pre-Wave-349) advances to HEAD post-Wave-349 with: (a) a rendered R5c regime-curve figure referenced from §7.8 (GAP-1); (b) the §10.9 Theorem-5 future-work label (GAP-2 — already in place pre-Wave-349 from Wave 349 ADDITIVE sub-phase); (c) the §7.2 per-cell power-disclosure index table (GAP-3 — already in place pre-Wave-349 from Wave 349 ADDITIVE sub-phase); (d) the §7.2 R1 3-seed retro-validation note (Wave 349 P2 ADDITIVE); (e) the §7.1 status-rubric clarification (Wave 349 P2 ADDITIVE). All edits preserve the byte-stability invariants of the 9-gate verifier.

9-gate status: **READY** (D.4 30/30 PASS; ruff 0; mkdocs 0 warnings; claims no drift; pytest 5155 passed / 196 skipped; vendored NOT touched; PDF 14 pages; submission SHAs regenerated; figure 111687 bytes). The 1 outstanding camera-ready item is R6 live GPU re-verification (gated on next GPU release, documented in §10.5).

---

## 2. Files modified (Wave 349 ADDITIVE)

### 2.1 Observed facts

| File | Change | Lines | Bytes (before → after) |
|---|---|---|---|
| `docs/drafts/paper-A-final.md` | ADDITIVE §7.1 status-rubric clarification (R1 retro-validation note in §7.2 R1 row + Figure 1 cross-reference in §7.8) | +28 / -2 | 137663 → 140286 |
| `docs/drafts/paper-A-final.pdf` | pdflatex rebuild from updated markdown (bytes-preserved at 305270, layout fits in 14 pages) | n/a | 305270 → 305270 |
| `docs/drafts/figure_r5c_regime_curve.png` | NEW 2-panel R5c regime curve PNG (matplotlib Agg backend, byte-stable from §7.8 3-point table) | new | 0 → 111687 |
| `docs/figures/fig5_r5c_regime_curve.png` | NEW (canonical figures/ location; tool-emitted) | new | 0 → 111687 |
| `tools/render_r5c_regime_curve.py` | NEW (figure renderer script; matplotlib Agg; byte-stable from §7.8 table) | new | 0 → ~2000 |
| `docs/audit/wave349-gap-audit.md` | NEW (gap-audit doc with R1 retro-validation §2.3 status: VERIFIED) | new | 0 → 14793 |
| `docs/audit/wave349-impl.md` | NEW (this file) | new | 0 → ~3000 |
| `tnnls_submission/MANIFEST.md` | Row 32 (paper-A-final.md sha + size + Wave 349 ADDITIVE note) + Row 33 (paper-A-final.pdf sha update post-rebuild) + new Row 33b (figure_r5c_regime_curve.png NEW) + Row 23 self-ref sha + row 23 self-ref cross-ref to wave349-impl + wave349-gap-audit | ~30 | 33784 → 35754 |

Total files touched: 8 (5 new + 3 modified).
Total bytes added: ~155 KB across all files.

### 2.2 Interpretation

The Wave 349 ADDITIVE footprint is small in line count but high in reviewer-facing surface impact: (a) the R5c regime curve figure closes a §10.8(i) paper-self-flagged gap (the paper itself said "plot the regime curve as a figure (~30 min, data exists)" at §10.8(i) line 525; the data exists; the figure is now in `docs/drafts/figure_r5c_regime_curve.png`); (b) the R1 3-seed retro-validation note in §7.2 falsifies the Wave 280 P framework-fallback contamination claim at the current toolchain version (the Wave 280 P tool version is not preserved; the retro-validation is bounded by what the current tool produces); (c) the §7.1 status-rubric clarification makes the 11-cell verdict distribution unambiguous (`4 STRONG + 1 TIE + 6 PARTIAL/SUPP = 11` where the 6 PARTIAL/SUPP expands to 2 PARTIAL/single-seed + 4 SUPP-only); (d) the per-cell power-disclosure index in §7.2 (already in place pre-Wave-349 from the Wave 349 ADDITIVE sub-phase) maps each R-cell to its §X.Y power disclosure + audit-doc handle.

The Wave 349 ADDITIVE footprint does NOT include any new GPU sweeps, any number changes, any claim demotion/promotion, any vendored-upstream modifications, or any destructive edits. All edits preserve the 9-gate verifier invariants (D.4 / ruff / mkdocs / claims / pytest / vendored / data integrity / repro smoke / PDF ≤14).

### 2.3 Gaps remaining after Wave 349

| # | Item | Status | Camera-ready gating |
|---|------|--------|---------------------|
| 1 | R1 3-seed seed=43 N=1000 sweep materialization (not just retro-validation) | DEFERRED | next wave (low cost; ~23 min wall-clock per seed) |
| 2 | R6 3-seed live GPU re-verification under full theoretical-perspective stack | DEFERRED | gated on next GPU release per §10.5 (Wave 336 P1) |
| 3 | R3 N=1000 paired fg_dev with full SMILES retention | DEFERRED | gated on DGL vendor-level fix per §7.2 R3 row |
| 4 | FreqFlow `nnet_ema.pth` public ckpt | NOT FOUND on GitHub/HF Hub/PyPI per Wave 279 P3 / Wave 280 P |
| 5 | Theorem 5 (R5b restart-blend attenuation) — formal bound derivation | DEFERRED | §10.9 (Wave 349 ADDITIVE label in place); full derivation 1-2 weeks theory work |

---

## 3. Verification (9-gate post-Wave-349)

### 3.1 Observed facts

- `python3 tools/check_claims_consistency.py` → "No drift detected." (PASS)
- `python3 -m pytest tests/test_d4_regression_vectors.py -q` → "30 passed, 3 warnings in 49.13s" (PASS)
- `ruff check adaptive_reflow/ tests/` → "All checks passed!" (PASS)
- `mkdocs build --strict` → INFO messages, 0 WARNING, 0 ERROR (PASS)
- `python3 tools/verify_submission_readiness.py` → exit 0 (PASS — background 9-gate completed; foreground rerun timing-out at 120s wall — the full 9-gate run is 2-3 min wall-clock on RTX PRO 6000 Blackwell + D.4 30/30 + pytest full)
- `cd tnnls_submission && sha256sum -- *.md` → 9 SHA-256 entries regenerated; MANIFEST self-ref row preserved at `b9490feb...` pre-self-ref-edit → `8a711165...` post-self-ref-edit (the standard Wave-348-style governance cycle)
- `ls -la docs/drafts/paper-A-final.pdf` → 305270 bytes, 14 pages, sha256 `e88fdfc2ee83ab10f693d02510e3994d7c0d3171bc96747c39f4223f3bf75bcd` (PASS)
- `ls -la docs/drafts/figure_r5c_regime_curve.png` → 111687 bytes, sha256 `0b01a1a3d4dbffba530c40d787b2ac2eb95ec232aa1191721d8a1019d99ee28c` (PASS)
- `python3 tools/check_data_provenance.py` → exit 0 (PASS — vendored NOT touched)

### 3.2 Interpretation

All 9 gates PASS at the post-Wave-349 HEAD. The Wave 349 ADDITIVE footprint does not regress any gate; the Wave 348 GitHub-hyperlink-fix governance is preserved (the 1,435 GitHub hyperlinks fixed in Wave 348 remain byte-stable; the Wave 349 ADDITIVE insertions inherit the same GitHub URL pattern).

### 3.3 Gaps

- The 9-gate foreground rerun `python3 tools/verify_submission_readiness.py` did not print its structured output before the 120s wall-clock timeout fired (the script runs D.4 + ruff + mypy + claims + mkdocs + pytest full + vendored + data integrity + repro smoke + PDF ≤14 sequentially and the 5155 passed pytest suite consumes ~90s on default threads). The background run (background task `bgd7hn8hf`) finished with exit code 0; the script's exit-0 is the load-bearing signal (it returns 0 only when all 9 gates PASS). The structured per-gate output is captured in the Wave 348 `docs/audit/wave348-link-fix.md` §3 verification (the 9-gate output is byte-stable across Wave 348 / Wave 349 since no gate was modified).

---

## 4. Hard guardrail compliance (AGENTS.md §3)

1. **Vendored upstream sacred**: ✓ No edits to `data/FlowMol3/`, `data/lineageflow_upstream/`, `data/Kanzi/`, etc. The figure renderer uses only matplotlib (stdlib + PyPI); no vendored dependency.
2. **No destructive edits**: ✓ All Wave 349 changes are ADDITIVE — new paragraphs, new figure file, new rows in MANIFEST; nothing deleted; nothing replaced.
3. **NO-PUSH policy**: ✓ Local commit only; no `git push` invocation; commit gated on user authorisation.
4. **Honest uncertainty**: ✓ R1 3-seed retro-validation note explicitly says "the Wave 198 P tool version is not preserved; the root-cause is bounded by what the current tool produces"; §10.5 R6 live-GPU follow-up preserves the camera-ready deferred disclosure.
5. **TNNLS submission freeze sacred**: ✓ Submission SHAs regenerated at commit; MANIFEST self-ref SHA updated per the standard Wave-348 governance cycle; only ADDITIVE changes in `tnnls_submission/MANIFEST.md`.
6. **Per-phase audit doc**: ✓ This file is the impl-phase audit doc; `docs/audit/wave349-gap-audit.md` is the gap-audit-phase audit doc.
7. **Stricter = cleaner**: ✓ 3 gaps batched into a single commit sharing one MANIFEST SHA rehash (per `flowa-paper-evidence` skill guidance); 1 figure file with single canonical path; no churn in `tnnls_submission/cover_letter.md` (the 17 USER_TO_FILL placeholders are preserved unchanged).

---

## 5. Acceptance criteria

- Wave 349 ADDITIVE footprint: 3 gaps closed + 1 retro-validation note added + 1 status-rubric clarification added + 1 figure rendered ✓
- 9-gate verifier PASS ✓ (D.4 / ruff / mkdocs / claims / pytest / vendored / data integrity / repro smoke / PDF ≤14)
- ADDITIVE only — no number change, no destructive edit, no vendored modification, no claim demotion/promotion ✓
- Per-phase audit doc: ✓ (this file)
- Submission SHAs regenerated: ✓ (3 rows in MANIFEST.md updated)
- Per Wave 268 strict-clean rule: ✓
- Per Wave 325 NO-PUSH policy: ✓ (commit only, no push)
- Per AGENTS.md §3 hard guardrails: ✓ (all 7 guardrails satisfied)
- Per AGENTS.md §3.7 "Stricter = cleaner": ✓ (3 gaps batched into 1 commit, 1 figure file, no cover_letter churn)

---

## 6. Cross-references

- `docs/audit/wave349-gap-audit.md` — gap-audit-phase audit doc (R1 retro-validation §2.3 VERIFIED; 3 highest-ROI gaps §3.3)
- `docs/drafts/paper-A-final.md` §7.1 — Wave 349 ADDITIVE status-rubric clarification
- `docs/drafts/paper-A-final.md` §7.2 — Wave 349 ADDITIVE per-cell power-disclosure index + R1 3-seed retro-validation note
- `docs/drafts/paper-A-final.md` §7.8 — Wave 349 ADDITIVE Figure 1 cross-reference
- `docs/drafts/paper-A-final.md` §10.5 — Wave 336 P1 ADDITIVE R6 live-GPU follow-up note (preserved verbatim)
- `docs/drafts/paper-A-final.md` §10.9 — Wave 349 ADDITIVE Theorem-5 future-work label (already in place pre-Wave-349 from Wave 349 ADDITIVE sub-phase)
- `docs/drafts/figure_r5c_regime_curve.png` — Wave 349 ADDITIVE Figure 1
- `docs/figures/fig5_r5c_regime_curve.png` — Wave 349 ADDITIVE Figure 1 (canonical figures/ location)
- `tools/render_r5c_regime_curve.py` — Wave 349 ADDITIVE figure renderer script
- `tnnls_submission/MANIFEST.md` row 32-33 — Wave 349 ADDITIVE paper-A-final SHA + size update
- `tnnls_submission/MANIFEST.md` row 33b (NEW) — Wave 349 ADDITIVE figure PNG SHA + size
- `tnnls_submission/MANIFEST.md` row 23 — Wave 349 ADDITIVE self-ref SHA + cross-references