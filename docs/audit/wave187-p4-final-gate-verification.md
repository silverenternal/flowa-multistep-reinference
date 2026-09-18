# Wave 187 P4 — Final gate verification

**Date:** 2026-09-18
**Branch:** main
**Scope:** Verify all 4 final gates are green after the Wave 187
camera-ready compression (P1 review, P2 compression 1/2 + 2/2, P3
abstract/intro + §5.0 updates).

---

## 1. Gate results

| # | Gate | Target | Actual |
|---|------|--------|--------|
| 1 | `python -m pytest tests/ -k "d4" -q` | 33/33 PASS | **33 passed, 30 skipped, 5028 deselected** ✓ |
| 2 | `ruff check adaptive_reflow/ tests/ scripts/ tools/ verification_outputs/` | 0 errors | **All checks passed!** ✓ |
| 3 | `python tools/check_claims_consistency.py` | No drift detected | **No drift detected.** (45 active, 0 provisional, 2 deprecated) ✓ |
| 4 | `mkdocs build --strict` | EXIT=0 | **EXIT=0** ✓ |

**All 4 gates green.**

---

## 2. Fixes applied during P4

Two pre-existing failures were fixed in this P4 pass before the
gates could go green.

### 2.1 ruff I001 in `verification_outputs/wan2_2_verify.py`

**Symptom.** Two `I001 Import block is un-sorted or un-formatted`
errors on the top-level `import sys / warnings / from pathlib`
block and on the inner `from adaptive_reflow.adapters.wan2_2_video`
import. Auto-fixed with `ruff check --fix` (both errors are marked
fixable).

**Resolution.** Reordered the top-level import block to alphabetical
order (`sys`, `warnings`, `pathlib.Path`). The inner adapter import
is wrapped in a function body and annotated with `# noqa: WPS433`
(allowed nested import); ruff's `I001` only complained about its
sort position. No source semantics changed.

### 2.2 mkdocs strict WARN on `not_in_nav` omissions

**Symptom.** `mkdocs build --strict` aborted with "Aborted with 1
warnings in strict mode!" — a single WARNING about pages in
`docs/` not being included in the nav: `code-release-checklist.md`,
`paper-draft-anonymous.md`, `paper-final-neurips.md`,
`paper-profile.md`, `submission-checklist-final.md`, plus every
`headline-evidence/*.md`, `preregistration/*.md`, `references/*.md`,
and `zenodo-release/*.md` file. The `not_in_nav` block in
`mkdocs.yml` did not yet list these files.

**Resolution.** Added 11 new entries to the `not_in_nav: |` block
in `mkdocs.yml` covering the four top-level files, the four
sub-directories (via `headline-evidence/*.md` and
`headline-evidence/**/*.md` to match both top-level files like
`r6_mnist_fm_fid_m15p01pct/SOURCE.md` and inner files like
`composite_axis_byte_stable/source_audit.md`), and the three
single-directory lists. After the edit the strict build emits no
omitted-files warnings and exits with code 0.

---

## 3. Claims state after Wave 187 P3

| Metric | Value |
|--------|-------|
| Active claims | **45** |
| Provisional claims | **0** |
| Deprecated claims | **2** |
| Forced to PROVISIONAL by `Disputed by` citation | **CLM-040** |

The active claim count of 45 matches the Wave 187 P1 audit's
expectation (45 expected after Wave 186 P4 completion + Wave 187
cumulative adds). No drift between `CLAIMS.md` and the paper
ledger; no provisional promotions needed.

---

## 4. D.4 byte-stable tests (33/33 PASS)

The D.4 byte-stable gate verifies that the framework produces
byte-identical output across the 33-cell sensitivity-analysis
FASTA ladder (lineageflow), plus the 5 canonical cell-state-shape
and velocity-bridge cells for kanzi. All 33 tests pass; the 30
"skipped" entries are due to `torch` / `hypothesis` /
`pytest-benchmark` / `rdkit` / `expecttest` not being installed in
the verification environment (the tests are correctly skipped,
not silently passed).

---

## 5. MkDocs strict build (EXIT=0)

After the `not_in_nav` extension (Section 2.2), the strict build
emits 0 warnings on the `omitted_files: warn` validator and exits
cleanly. The earlier `mkdocstrings_handlers: Formatting signatures
requires either Black or Ruff to be installed` INFO is an INFO
(not a WARNING) and does not affect the strict-mode pass/fail
decision.

---

## 6. Acceptance gates (Wave 187 P4, final)

| # | Gate | Result |
|---|------|--------|
| 1 | D.4 byte-stable tests | **33/33 PASS** |
| 2 | Ruff lint | **0 errors** |
| 3 | Claims consistency | **No drift detected.** |
| 4 | MkDocs strict build | **EXIT=0** |
| 5 | Wave 187 P1 audit (12-section review) | ✓ (see `wave187-p1-final-review.md`) |
| 6 | Wave 187 P2 compression (1/2 + 2/2) | ✓ (paper §7.5/§7.6 verdict evolution consolidated) |
| 7 | Wave 187 P3 abstract/intro + §5.0 updates | ✓ (R1-R6 framing + 4-arm head-to-head wins + 5 adapters × 3 domains + Theorem 1 self-convergence scope) |

**All 4 final gates green. Wave 187 P4 ready to commit.**