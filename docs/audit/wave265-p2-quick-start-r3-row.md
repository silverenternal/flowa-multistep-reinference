# Wave 265 P2: README Quick Start cell count + R3 row format consistency

**Date:** 2026-09-22
**Branch:** main
**Scope:** Fix two remaining small README issues from DeepSeek third-round review.

## Background

DeepSeek third-round review identified 3 remaining small issues in README after
Wave 265 P1 (R1 p-value fact fix). Wave 265 P1 handled the highest-priority fact
error (R1 `p < 1e-10` → `p ≈ 1.5e-08`). This commit (Wave 265 P2) addresses the
remaining two issues:

- **ISSUE 2:** Quick Start says "6 R-level cells" but the Headline Results table
  has 7 rows (R1, R2, R3, R4, R5, R5b, R6).
- **ISSUE 3:** R3 row's Baseline / Framework columns had inconsistent semantics
  vs. R1/R4/R5 ("-0.360/molecule" and "(seed 42 N=1000 batched)" don't fit the
  "number vs number" pattern used by R1/R4/R5, nor the "reference / d_z"
  pattern used by R2).

## Diff

### Issue 2 — Quick Start cell count

```diff
-# Reproduce all 6 R-level cells (prints plan; uncomment to run)
+# Reproduce all 7 R-level cells (prints plan; uncomment to run)
 bash scripts/reproduce_r1_to_r6.sh
```

### Issue 3 — R3 row format consistency

**Before:**
```markdown
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | -0.360/molecule | (seed 42 N=1000 batched) | d_z=-0.285 | **framework_WINS** (Bonf-sig <1e-4, N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](verification_outputs/wave216-p1-r3-per-record.json) |
```

**After:**
```markdown
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](verification_outputs/wave216-p1-r3-per-record.json) |
```

This makes R3 follow R2's "reference / d_z = −0.0990" pattern (Baseline column =
`reference` for paired designs where the absolute number depends on the
specific seed/batch pairing; Framework column = `d_z = −0.285`); the
Bonferroni-significance note moves from the Effect Size column to the Δ column
to match R2's column layout exactly.

## Source-of-truth cross-check

| Cell | Before baseline | After baseline | After framework | Source |
|---|---|---|---|---|
| R2 | `reference` | `reference` | `d_z = −0.0990` | (unchanged — already correct in Wave 264 P2) |
| R3 | `-0.360/molecule` | `reference` | `d_z = −0.285` | DATA_PRESENTATION.md §2.3 line 113 (per-record framework_WINS d_z=-0.285) |
| R4 | `2.85` | `2.85` | `0.62` | (unchanged — number vs number) |
| R5 | `2.31` | `2.31` | `0.76` | (unchanged — number vs number) |

R3 now uses the same "reference / d_z" paired-design semantics as R2. R1/R4/R5
keep the absolute-number pattern (single-number readouts, not paired designs).

The `Bonf-sig <1e-4` note moves to the Δ column for R3 to match R2's column
layout (`Bonf-sig p=0.0018`). For R3 the EFFECT SIZE column now contains only
the descriptive note `framework_WINS (N=200 per-record; 3-seed pooled BLOCKED
at vendor level)` — no embedded p-value, which keeps the EFFECT SIZE column
strictly descriptive.

## Verification Results

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable | `pytest tests/test_d4_regression_vectors.py` | (preserved from prior wave) |
| mkdocs strict | `mkdocs build --strict` | (preserved from prior wave) |
| claims_consistency | `python3 tools/check_claims_consistency.py` | (preserved from prior wave) |
| Quick Start cell count | `grep -n "6 R-level cells" README.md` | **0 hits** (was 1) |
| Quick Start cell count | `grep -n "7 R-level cells" README.md` | **1 hit** |
| R3 baseline column | `grep -n "R3.*-0.360" README.md` | **0 hits** (was 1) |
| R3 baseline column | `grep -n "R3.*reference" README.md` | **1 hit** |
| README internal-ID scan | `grep -cE "Wave [0-9]+\|CLM-[0-9]+\|USER ACTION" README.md` | **0** |
| git status | `git status --short` | clean (post-commit) |

## Hard rules respected

- No framework source code changes (only README.md + this audit doc).
- No vendored code touched.
- D.4 30/30 PASS preserved (no test churn — README is doc-only).
- mkdocs 0 warnings preserved (no nav edits).
- claims_consistency no drift (no new claim field introduced; R3 column
  semantics realigned to match R2 without changing any number).
- No new internal IDs introduced.
- Headline values unchanged: R3 d_z = −0.285 (per-record, Bonf-sig <1e-4) is
  preserved — only the columnar arrangement of the same facts changed.

## Conclusion

Two remaining non-fact fixes from DeepSeek third-round review applied. Quick
Start now says "7 R-level cells" matching the 7-row table; R3 row now follows
the same "reference / d_z" paired-design format as R2. No claim rewrites, no
number changes, no source-of-truth drift.