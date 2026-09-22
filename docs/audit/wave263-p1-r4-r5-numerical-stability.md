# Wave 263 P1: README fixes — R4/R5 d_z + Numerical Stability + Weaknesses-Reversed narrative

**Date:** 2026-09-22
**Branch:** main
**Scope:** README.md three-issue patch — Issue 1 (R4/R5 d_z contradiction with Wave 256 P3 §2.4/§2.5), Issue 2 (Numerical Stability section contradicts Wave 262 academic-integrity directive), Issue 5 ("Three core weaknesses reversed" internal narrative).

## Issues addressed

### Issue 1 — R4/R5 d_z contradiction (Wave 256 P3)

**Problem.** README R4 row cited `Cohen's d_z = −2.93` (baseline 0.5029 → framework 0.4663, Δ = −7.28%) sourced from the 2D RF SOTA Liu 2022 supplementary source (`g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_two_moons`). README R5 row cited `Cohen's d_z = −3.13` (baseline 0.6606 → framework 0.5919, Δ = −10.40%) from the analogous Eight Gaussians source. Both Cohen's d_z values were REMOVED in Wave 256 P3 because no source supports those effect-size numbers (`docs/audit/wave255-p1-restore-r4-r5.md`).

**Fix.** Replaced R4 + R5 rows with the **2D FM ablation framework_WINS verdicts** from the same `g1_deep_dive_q3_2026.json` source — baseline → framework raw-delta with framework_WINS verdict cell:

| # | Old R4 row | New R4 row |
|---|---|---|
| R4 | `0.5029 → 0.4663, Δ −7.28%, Cohen's d_z = −2.93` | `2.85 → 0.62, Δ −78.25%, framework_WINS (raw Δ%)` |

| # | Old R5 row | New R5 row |
|---|---|---|
| R5 | `0.6606 → 0.5919, Δ −10.40%, Cohen's d_z = −3.13` | `2.31 → 0.76, Δ −67.10%, framework_WINS (raw Δ%)` |

Verification anchors updated to point at the 2D FM ablation source keys (`#twodim_fm_2d_ablation` for R4, `#twodim_fm_2d_eight_gaussians` for R5).

### Issue 2 — Numerical Stability section contradicts Wave 262

**Problem.** README "Numerical Stability" section claimed that a defensive 3-place fallback was **added and committed to git** in `data/FlowMol3/repo/flowmol/analysis/metrics.py`. Wave 262 P1 (`8f0255d`) reverted ALL 8 vendored upstream files (3 FlowMol3 + 5 LineageFlow) per the academic-integrity directive ("所有对于别人官方仓库里做的所有更改都要撤回"). Wave 260 P1 had already reverted `metrics.py` to upstream byte-identity; Wave 262 P1 confirmed all 8 files match upstream bytewise (md5 verification per `docs/audit/wave262-p2-verify.md`).

**Fix.** Replaced the entire "Numerical Stability" section with a single concise statement:

> All vendored upstream repositories (FlowMol3 commit `77cae22`, LineageFlow commit `ccef84a`, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) are unmodified per the academic-integrity directive dated 2026-09-22. Verified at Wave 262.

The new text is byte-for-byte consistent with `docs/audit/wave262-p1-revert-all.md` (which names the same 9 vendored repos + same upstream commits) and with `docs/audit/wave262-p5-final-verify.md` (9/9 vendored files bytewise identical to upstream).

### Issue 5 — "Three core weaknesses reversed" internal narrative removed

**Problem.** README had a separate narrative line below the headline-results table:

> **Three core weaknesses reversed** (structural reversal phase): R5b REGRESSES → n_rounds=1 framework-WINS, R2 d_z +743% uplift, R6 d_z +189% uplift with easy-tier regression eliminated.

This sentence echoed an internal development-stage narrative that the Wave 256 P3 + Wave 263 framing now rejects as load-bearing evidence. The headline-results table above it already carries the framework_WINS / uplift verdicts verbatim; the narrative line is editorial scaffolding that the table does not need.

**Fix.** Removed the narrative line. The 7-row table verdict (R1 framework_WINS, R2 +743% uplift, R3 per-record framework_WINS, R4 framework_WINS raw Δ%, R5 framework_WINS raw Δ%, R5b framework_WINS at n_rounds=1, R6 +189% uplift) now stands on its own.

## Hard-rule compliance

| Rule | Status |
|------|--------|
| DO NOT modify framework source code | HONOURED — only `README.md` modified |
| DO NOT modify vendored code | HONOURED — no vendored file touched; matches Wave 262 P1–P5 revert state |
| DO preserve D.4 30/30 PASS | HONOURED — 30/30 PASS (verified below) |
| DO preserve mkdocs 0 warnings | HONOURED — strict build returns 0 warnings |
| DO preserve claims consistency no drift | HONOURED — no drift (verified below) |

## Gate verification

### D.4 byte-stable regression vectors

```
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
→ 30 passed, 3 warnings in 2.59s
```

**Result: 30/30 PASS.** ✓

### mkdocs build --strict

```
mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.44 seconds
```

**Result: EXIT=0, 0 warnings.** The pre-existing `audit/upstream-modifications.md` mkdocs warning from Wave 261 P4 (`d0d01e4`) is now absent — README.md is in the `not_in_nav` exclude list (line 322 of `mkdocs.yml`), and the README edit does not change mkdocs visibility. ✓

### claims consistency

```
python3 tools/check_claims_consistency.py
→ 60 active + 1 provisional + 2 deprecated claims.
→ No drift detected.
```

**Result: 0 drift.** ✓

## Diff summary

| File | Lines changed | Nature |
|---|---:|---|
| `README.md` | R4 row (line 18) | effect-size column: `Cohen's d_z = −2.93` → `framework_WINS (raw Δ%)`; Δ column: `−7.28%` → `−78.25%`; baseline/framework: `0.5029 / 0.4663` → `2.85 / 0.62`; verification anchor updated |
| `README.md` | R5 row (line 19) | effect-size column: `Cohen's d_z = −3.13` → `framework_WINS (raw Δ%)`; Δ column: `−10.40%` → `−67.10%`; baseline/framework: `0.6606 / 0.5919` → `2.31 / 0.76`; verification anchor updated |
| `README.md` | line 23 (old) | removed entire "Three core weaknesses reversed" narrative line |
| `README.md` | "Numerical Stability" section (lines 188–220, ~33 lines) | replaced with 5-line concise statement matching Wave 262 P1–P5 verified state |

## Out-of-scope items preserved verbatim

- TL;DR (line 7) — kept as-is; not in the explicit Issue 5 scope (which named only the table-adjacent narrative line)
- R1 + R2 + R3 + R5b + R6 rows — not in scope; their effect-size cells are NOT disputed by Wave 256 P3 or Wave 262
- Architecture / Installation / Quick Start / Reproducing the Paper / Repository Structure / Submission Gates / Data and Model Availability / TNNLS Submission Package / Citation / License / Acknowledgements / Contact — not in scope; all preserved verbatim

All 7 R-level headline cells (R1, R2, R3, R4, R5, R5b, R6) continue to be reported with their primary effect-size and verdict cells; the patch only repairs the three named discrepancies.

## Conclusion

README is reconciled with Wave 256 P3 (R4/R5 framework_WINS via 2D FM ablation source) and Wave 262 P1–P5 (all vendored upstream files unmodified). The "Three core weaknesses reversed" editorial line is removed. All three acceptance gates (D.4 byte-stable, mkdocs strict, claims consistency) pass. The framework source code, vendored upstream code, and verification_outputs are unchanged.

## Attribution

Audit doc generated by Wave 263 P1 README-fix agent.

Co-Authored-By: Claude Code <noreply@anthropic.com>