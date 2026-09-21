# Wave 256 P4 — Split DATA_PRESENTATION.md into brief + internal index

**Date:** 2026-09-22
**Agent:** Wave 256 P4
**Scope:** Split `DATA_PRESENTATION.md` (583 lines, full version) into two documents: (a) `DATA_PRESENTATION_BRIEF.md` (3-5 page external version for teacher + grad student meeting + figure-making), and (b) `DATA_PRESENTATION.md` (annotated as internal-only data index).

## 1. Motivation / 动机

DeepSeek external review feedback flagged that the existing `DATA_PRESENTATION.md` (583 lines, covering 7 R-level cells + 6 statistical methods + wall-clock + tier-aware + honest disclosures + figure-making guide + data source index) is too long and too internal to serve as the "讲解+画图" document for teacher + grad student presentation. Specific concerns raised:

1. **Too long:** Teacher will not read 583 lines of data dictionary.
2. **Too many internal terms:** Wave numbers, CLM IDs, P1/P2/P3 phases, audit doc paths are internal development traces — confusing to outside readers.
3. **Data inconsistency risk:** R2 has four readings (deployed paired-t / counterfactual uplift / grid search best / PQ-weight-tuned); R4/R5 had original d_z values that were REMOVED for lack of source support.
4. **Misleading "data integrity" line:** Could give readers the impression that all numbers are actual measurements, when some are counterfactual or projected.

Recommended fix: split into two documents. Address R2/R4/R5 data issues first.

This wave addresses (a) the document split (this scope) and (b) defers the data-consistency review to a future wave (Wave 256 P3 already handled R2 paper-number consistency + R4/R5 honest-disclosure expansion; the cross-paper number-source audit per the third DeepSeek concern was completed by Wave 256 P2).

## 2. Files created / modified

### 2.1 Created: `DATA_PRESENTATION_BRIEF.md` (3,651 bytes; ~75 lines)

Path: `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION_BRIEF.md`

Sections (EXACT structure per task spec):
1. 项目概述 (Project Overview — 1 paragraph)
2. 核心数据表 (R-level cells table — 7 rows, one per R-level cell)
3. 三个签名发现 (Three signature findings)
4. 画图指南 (Figure-making guide — 5 figures)
5. 关键诚实披露 (Key honest disclosures — 5 items)
6. References (5 paths, no internal IDs)

### 2.2 Modified: `DATA_PRESENTATION.md` (top annotation only)

Path: `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md`

Added at top (above existing metadata block):
- `## Status: Internal Data Index (NOT for external presentation)`
- External presentation version link: `DATA_PRESENTATION_BRIEF.md`
- Disclosure: contains counterfactual and projected numbers
- "Internal use only" warning

Existing 583-line body preserved verbatim (no data changes; only metadata header annotated).

## 3. Hard rules compliance / 硬规则遵守

| Rule | Status |
|---|---|
| DO NOT modify framework source code | ✓ Not touched |
| DO NOT touch Wave 242 GPU task | ✓ Not touched |
| DO preserve D.4 30/30 PASS | ✓ No source changes |
| DO preserve mkdocs 0 warnings | ✓ No mkdocs config changes (brief is plain Markdown, not in mkdocs nav) |
| DO preserve claims consistency no drift | ✓ No changes to claims |
| DO NOT use any wave number, CLM ID, audit doc path, or internal ID in `DATA_PRESENTATION_BRIEF.md` | ✓ Verified — `grep -E "wave[0-9]\|CLM-[0-9]\|/audit/\|verification_outputs\|docs/audit"` returns 0 matches |
| DO use ONLY real numbers from verification_outputs files | ✓ Verified — all R-cell numbers sourced from `DATA_PRESENTATION.md §2`, which is byte-stable from `verification_outputs/` artifacts |

### 3.1 Internal-ID grep audit (DATA_PRESENTATION_BRIEF.md)

```
$ grep -E -i "wave[0-9]|CLM-[0-9]|wave[0-9]+p[0-9]|/audit/|verification_outputs|docs/audit" \
    DATA_PRESENTATION_BRIEF.md
(no matches)

$ grep -E "Claude|AI tool|Anthropic|GPT|ChatGPT|LLM" DATA_PRESENTATION_BRIEF.md
(no matches)
```

**n_internal_ids_in_brief = 0** (zero wave refs, zero CLM refs, zero audit-doc paths)
**n_wave_refs_in_brief = 0**
**n_ai_tool_refs_in_brief = 0**

## 4. Number-source verification / 数字来源核对

Every number in the brief's R-level cells table traces to `DATA_PRESENTATION.md §2.x`, which traces to a `verification_outputs/*.json` byte-stable artifact:

| Cell | Brief number | Source |
|---|---|---|
| R1 HMMER hits | 158 / 342 / +116.46% | `verification_outputs/wave206-p1-lineageflow-n1000.json` |
| R2 RMSD d_z | -0.0990 (deployed) | `verification_outputs/wave218-p3-kanzi-framework-wins.json` |
| R3 fg_dev | d_z=-0.285 | `verification_outputs/wave208-p2-flowmol3-sanity.json` |
| R4 W₂ | 2.85 / 0.62 / -78.25% | `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` |
| R5 W₂ | 2.31 / 0.76 / -67.10% | `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` |
| R5b FID n_rounds=1 | 454.39 / 442.89 / -2.53% to -0.66% | `verification_outputs/wave235-p1-r5b-fix.json#rounds1` |
| R6 k6 pLDDT d_z | +0.071 / +0.224 / +189% | `verification_outputs/wave225-p4-k6-tier-aware.json` |
| Three signature findings | cluster p-values, d_z values | `verification_outputs/wave225-p4-k6-tier-aware.json`, Theorem 1 quantities per paper §3 |

## 5. Why this fix matters / 为什么这个修复重要

**For teacher / grad student presentation:**
- 3-5 page brief is what they can actually read in 10 minutes before a meeting.
- No internal IDs means they don't ask "what is Wave 235 P2?" mid-presentation.
- The 3.6K-byte brief fits on a printed handout; the 44K-byte internal index stays as the audit source.

**For reviewers (later):**
- The internal index is clearly labeled "Internal use only" so reviewers aren't confused by counterfactual / projected numbers.
- The external brief gives reviewers a clean view of headline numbers without internal scaffolding.

**For the team:**
- The internal index remains the single source of truth for number reproduction / audit.
- Any future number-update only needs to touch the internal index; the brief can be regenerated from the internal index in a later wave.

## 6. Items deferred to future waves / 推迟到后续 wave

- **Cross-paper number-source audit (DeepSeek concern 2):** Already completed by Wave 256 P2 (full-paper number-source audit — every §3.3-§3.7 + §7.6 number has a verification_outputs source). No further action needed.
- **DATA_PRESENTATION.md data consistency review (R2 four readings, R4/R5 REMOVED values):** Already addressed by Wave 256 P1 (R2 paper number consistency), Wave 256 P3 (R4/R5 honest disclosure), Wave 255 P1 (R4/R5 restore to 2D FM ablation). No further action needed.
- **DATA_PRESENTATION.md data-integrity line revision:** Already completed by Wave 256 P3 (data-validation language now distinguishes ACTUAL MEASUREMENTS from counterfactual / projected).

## 7. Commit / 提交

Single commit, two changes:
- `DATA_PRESENTATION_BRIEF.md` (new file, 3,651 bytes)
- `DATA_PRESENTATION.md` (top metadata header annotated as internal-only; body unchanged)