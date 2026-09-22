# Wave 264 P1 — README TL;DR Cleanup

**Date:** 2026-09-22
**Branch:** main

## Summary

Final TL;DR cleanup per deepseek feedback after Wave 263. Three remaining issues addressed in one edit:

1. **ISSUE 1 — "three core weaknesses reversed" narrative removed.** This was internal-narrative language inappropriate for the TL;DR section. Reviewers do not need to know about the "structural reversal cycle" process.
2. **ISSUE 2 — R2 d_z +0.39 (counterfactual) vs table -0.0990 (deployed) contradiction.** Eliminated by removing the contradictory sentence entirely. The R2 row in the Headline Results table is the authoritative source for R2 numbers.
3. **ISSUE 3 — "six R-level cells" vs 7-row table.** Fixed to "seven R-level cells" (table has R1, R2, R3, R4, R5, R5b, R6 = 7 rows).

## Change Applied

Single edit to README.md line 7 (TL;DR paragraph).

**Before:**

> Validated across **six R-level cells** spanning protein (LineageFlow), molecular 3D (FlowMol3), and image (CIFAR-10 RF, MNIST FM, 2D), with three core weaknesses reversed after the structural reversal cycle: R5b REGRESSES → n_rounds=1 framework-WINS, R2 d_z +0.05 → +0.39 (medium-effect, +743%), R6 d_z +0.22 → +0.65 (large-effect, +189%, easy-tier regression eliminated), and the 24.6× wall-clock gap closed 76.8% via CUDA-graph capture.

**After:**

> Validated across **seven R-level cells** spanning protein (LineageFlow), molecular 3D (FlowMol3), and image (CIFAR-10 RF, MNIST FM, 2D). The 24.6× wall-clock gap is closed 76.8% via CUDA-graph capture.

## Notes on R2 Table Column Semantics

The deepseek feedback also suggested renaming the R2 Baseline/Framework columns from `-0.0990 / -0.0990` to `reference / d_z = -0.0990` for clearer semantics. This is a downstream polish that does not affect the data integrity contradiction flagged in the TL;DR; deferred to a follow-up wave if the maintainer wants it.

## Verification Results

| Check | Result |
|-------|--------|
| D.4 byte-stable regression | 30 passed (preserved) |
| mkdocs build --strict | 0 warnings (preserved) |
| claims_consistency | No drift detected |
| Internal IDs in README.md | 0 matches |
| TL;DR contradiction (R2 +0.39 vs table -0.0990) | Eliminated |
| R-level cell count consistency | "seven" matches table 7 rows |

## Verdict

PASS — TL;DR is now consistent with the Headline Results table (no internal numbers, correct cell count, no counterfactual data in the visible series). Ready for commit.