# Wave 254 P4 — DATA_PRESENTATION.md §2.7 R6 mean_diff approximation fixes / R6 mean_diff 近似值修复

**Date (UTC)**: 2026-09-22 (Wave 254 P4)
**Author**: Wave 254 P4 agent
**Source audit**: `docs/audit/wave253-p3-number-verification.md` §1.8 (R6 per-tier scPerplexity mean_diff "≈−3.4" approximations wrong; medium pLDDT mean_diff +0.890 wrong)
**Target doc**: `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` §2.7 (R6 per-tier table, lines 217–221)
**Methodology**: replace 4 `mean_diff` cells with verified actuals from `verification_outputs/wave198-p3-difficulty-strata.csv`. **No source code edits. No framework source changes.**

---

## 1. Pre-fix doc §2.7 R6 per-tier table status (Wave 253 P3 audit findings)

### 1.1 Source-of-truth values

All values verified against `verification_outputs/wave198-p3-difficulty-strata.csv` (cited in `wave253-p3-number-verification.md` §1.8 lines 175–198):

| row | field | doc said (WRONG) | source ACTUAL |
|---|---|---:|---:|
| 217 | hard scPerplexity mean_diff | ≈−3.4 | **−2.99678487922889** (−2.997) |
| 218 | medium pLDDT mean_diff | +0.890 | **+2.585295682039977** (+2.585) |
| 219 | medium scPerplexity mean_diff | ≈−3.4 | **−3.9807800917434553** (−3.981) |
| 221 | easy scPerplexity mean_diff | ≈−3.4 | **−4.770440961206789** (−4.770) |

### 1.2 Why these are wrong

- **R6 hard scPerplexity mean_diff**: doc used `≈−3.4` (≈ sign indicates approximation). The actual per-tier hard scPerplexity mean_diff is −2.997, NOT a uniform −3.4.
- **R6 medium pLDDT mean_diff**: doc said `+0.890`. Actual is `+2.585`. This is a hard error, not an approximation — the sign is correct but the magnitude is wrong by ~2.9×.
- **R6 medium scPerplexity mean_diff**: doc used `≈−3.4`. Actual per-tier is −3.981. Rounding −3.981 to one decimal is −4.0, NOT −3.4.
- **R6 easy scPerplexity mean_diff**: doc used `≈−3.4`. Actual per-tier is −4.770. Rounding −4.770 to one decimal is −4.8, NOT −3.4.

The `≈−3.4` is a stale overall-uniform value (overall mean_diff is −3.917, which rounds to −3.9 not −3.4). The per-tier values are substantially different from the overall.

---

## 2. Post-fix doc §2.7 R6 per-tier table (lines 217–221)

| line | tier | metric | pre-fix mean_diff | post-fix mean_diff |
|---:|---|---|---:|---:|
| 217 | hard | scPerplexity | ≈−3.4 | **−2.997** |
| 218 | medium | pLDDT | +0.890 | **+2.585** |
| 219 | medium | scPerplexity | ≈−3.4 | **−3.981** |
| 221 | easy | scPerplexity | ≈−3.4 | **−4.770** |

The `≈` prefix has been dropped because we now have exact three-decimal-precision values from `wave198-p3-difficulty-strata.csv`. The surrounding `sd_diff` (≈3.3) and other columns remain unchanged — task scope was strictly mean_diff.

---

## 3. Audit consistency check

The corrected per-tier scPerplexity values still preserve the qualitative verdicts in §2.7:
- hard scPerplexity: −2.997 (still negative → framework lower-better WIN, unchanged verdict)
- medium scPerplexity: −3.981 (still negative → framework WIN, unchanged verdict)
- easy scPerplexity: −4.770 (still negative → framework WIN, unchanged verdict)
- medium pLDDT: +2.585 (still positive, magnitude now larger but verdict remains UNDERPOWERED because cluster p=0.260 is unchanged)

The cluster p-values, t-statistics, d_z, and p_raw columns are unchanged (they were always correct; only the mean_diff display values were stale/wrong).

---

## 4. Files changed

- `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` §2.7 (lines 217, 218, 219, 221 — 4 mean_diff cells)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave254-p4-fix-r6-mean-diff.md` (this file, NEW)

Total: 4 single-cell numeric replacements in DATA_PRESENTATION.md. No deletions, no row insertions, no surrounding text changes.

---

## 5. Hard rules compliance

- **DO NOT modify framework source code** — no edits to `flowa/`, `examples/`, `tools/`, `scripts/` outside this doc-only scope
- **DO NOT touch Wave 242 GPU task** — not modified
- **DO preserve D.4 30/30 PASS** — no change to D.4 gate or test corpus
- **DO preserve mkdocs 0 warnings** — no change to mkdocs config
- **DO preserve claims consistency no drift** — qualitative verdicts in §2.7 unchanged (see §3 above); no other doc sections cross-referenced these stale mean_diff values
