# Wave 231 P1 — B_g paper-draft fix (replace stale "B_g^emp = 0" claims)

**Wave:** 231 P1
**Date:** 2026-09-21
**Status:** COMPLETE — both paper-draft references to the broken
`B_g^emp = 0` claim replaced with the Wave 230 P1 fix values
(`B_g^emp = 1.1697` for all 3 core adapters, A_g within 1% of canonical).

## TL;DR

| File | Before | After |
|---|---|---|
| `docs/drafts/section-2-method.md:717` | `B_g^emp = 0 for all three (the sorted empirical residuals are monotone and never cross zero, yielding an empty packing sum — a degenerate but valid profile that the paper-quantity evaluators handle)` | `B_g^emp = 1.1697 for all three core adapters (sin(s) modulation per Wave 230 P1; A_g within 1% of canonical; full B_g = sum_{k=-N..N} e^{-(kπ)²/4} recovers the canonical value). The empirical A_g for LineageFlow, Kanzi, FlowMol3 are 0.847, 0.854, 0.854 respectively — within 1% of the canonical witness A_g = 0.8549.` |
| `docs/cover-letter-tpami.md:125` | `$B_g^{\text{emp}} = 0$ for all three core adapters (the sorted empirical residuals are monotone and never cross zero)` | `$B_g^{\text{emp}} = 1.1697$ for all three core adapters (matching canonical; sin(s) modulation per Wave 230 P1 fixes the monotone-profile degeneracy)` |

`docs/drafts/abstract-final.md` had no `B_g = 0` or `B_g^emp = 0` claim
to replace; verified clean.

## Background

Wave 230 P1 (`docs/audit/wave230-p1-b-g-diagnosis.md`) fixed the
`B_g = 0.0` bug by wrapping the empirical residual profile with
`sin(s)` modulation in `adaptive_reflow/adapters/profile_residual.py`.
The fix produces:

| Adapter | A_g before | A_g after | B_g before | B_g after |
|---|---:|---:|---:|---:|
| LineageFlowAdapter | 0.8601889540 | 0.8466680032 | 0.0000000000 | **1.1697134028** |
| KanziAdapter | 0.7463983125 | 0.8541862921 | 0.0000000000 | **1.1697133530** |
| FlowMol3V2Adapter | 0.8482000796 | 0.8543099612 | 0.0000000000 | **1.1697133153** |

All three `A_g` values are now within ~1% of the canonical witness
`A_g = 0.8549457422`. All three `B_g` values are now positive and
within numerical precision of the canonical witness
`B_g ≈ 1.1697133855`. The bound
`A_g · exp(-NFE / B_g) + C_g · e_ρ` is no longer degenerate for any
of the three core adapters.

The paper drafts (`docs/drafts/section-2-method.md`,
`docs/cover-letter-tpami.md`) were written **before** the Wave 230 P1
fix and still claimed `B_g^emp = 0` for all three. DeepSeek flagged
this as a **bound-formula implementation bug**; the implementation is
fixed but the paper text still propagated the stale claim. This wave
patches the paper drafts to match the post-fix values.

## Edits applied

### Edit 1: `docs/drafts/section-2-method.md`

**Location:** line 717, in the §2.5 disclosure paragraph about the
3 core adapters' empirical paper-quantities.

**Before** (4 lines):
```
for all 12 adapters; B_g^emp = 0 for all three (the sorted
empirical residuals are monotone and never cross zero, yielding
an empty packing sum — a degenerate but valid profile that
the paper-quantity evaluators handle). **The 3 core adapters
```

**After** (1 line):
```
for all 12 adapters; B_g^emp = 1.1697 for all three core adapters (sin(s) modulation per Wave 230 P1; A_g within 1% of canonical; full B_g = sum_{k=-N..N} e^{-(kπ)²/4} recovers the canonical value). The empirical A_g for LineageFlow, Kanzi, FlowMol3 are 0.847, 0.854, 0.854 respectively — within 1% of the canonical witness A_g = 0.8549. **The 3 core adapters
```

The replacement preserves the local narrative (empirical A_g ≤ 1% of
canonical, framework byte-stable at both canonical and empirical
profiles, "mixed: canonical + 3 adapter-specific" paper-quantity
regime) while removing the stale `B_g^emp = 0` claim.

### Edit 2: `docs/cover-letter-tpami.md`

**Location:** line 125, in the cover-letter paragraph that motivates
the adapter-specific paper-quantity disclosures.

**Before** (3 lines):
```
for all 12 adapters; $B_g^{\text{emp}} = 0$ for all three core
adapters (the sorted empirical residuals are monotone and never
cross zero). The paper quantities are computed via typed
```

**After** (1 line):
```
for all 12 adapters; $B_g^{\text{emp}} = 1.1697$ for all three core adapters (matching canonical; sin(s) modulation per Wave 230 P1 fixes the monotone-profile degeneracy). The paper quantities are computed via typed
```

### Edit 3: `docs/drafts/abstract-final.md`

No `B_g = 0` or `B_g^emp = 0` claim existed in this file; the
abstract speaks at the *framework claim* level (BL bound with the
four paper quantities) without naming any specific empirical value.
**No edit required.**

## Scope verification

Searched `docs/` for any remaining `B_g = 0`, `B_g^emp = 0`,
`B_g^{\text{emp}} = 0`, or `B_g\\^emp = 0` patterns. Categorized the
13 hits by context:

### In-scope fixes applied (2)

| File | Line | Disposition |
|---|---:|---|
| `docs/drafts/section-2-method.md` | 717 | REPLACED (Wave 231 P1) |
| `docs/cover-letter-tpami.md` | 125 | REPLACED (Wave 231 P1) |

### Out-of-scope references (intentionally NOT modified)

| File | Line | Why out of scope |
|---|---:|---|
| `docs/governance/02-algorithm-audit.md` | 131 | Canonical edge-case test: `B_g = 0 (no roots)` for `g(x) = exp(x) + 1` — mathematically correct (a constant profile has no roots, so `B_g = 0` is the right value). This is a doctest-grade correctness check, not an empirical claim. |
| `docs/r17-survey/img-comparison.md` | 536 | Survey of CIFAR-10 Rectified Flow (`twodim_fm` adapter), NOT a core adapter. The `B_g=0.0` in the `paper_quantities_snapshot` is for the `twodim_fm` profile (monotone empirical residual in the CIFAR-10 survey); the Wave 230 P1 fix only touched LineageFlow / Kanzi / FlowMol3 wrappers in `adaptive_reflow/adapters/profile_residual.py`. Fixing `twodim_fm` would be a Wave 231 P2 (or later) task. |
| `docs/CLAIMS.md`, `doc/INSIGHTS.md`, `docs/supplementary/wave193-audit-trail.md`, `docs/paper-draft-precut.md.bak` | various | Historical Wave 189 / Wave 190 records about a *statistical* p-value (`p = 0.103 marginal at n_paired = 3`) for the cosine-arm-vs-paper-arm L2 endpoint movement, not about `B_g`. The "marginal at n=3" phrasing refers to the paired-t p-value, not to `B_g = 0`. |
| `docs/benchmark-uplifts.md`, `docs/benchmark-round2-uplifts.md`, `docs/benchmark-deep-uplifts.md` | various | Benchmark tables reporting `(B_g >= 0 + tail < 1e-20)` invariants and `(B_g for sin profile) = 1.16971` canonical values — the `0` in the table is a count (`0 failures`), not a `B_g` value. |
| `docs/算法实现说明.md` | various | Chinese-language supplementary note; `A_g·ε / (A_g·ε + C_g·B_g·ε²) = 0.0085 / (0.0085 + 0.0000154)` is a ratio computation, not a `B_g = 0` claim. |
| `docs/audit/wave162-audit.md`, `docs/audit/wave185-p1-design.md`, `docs/lean/PAPER_QUANTITIES_MAPPING.md`, `docs/tables/tbl1-paper-quantities.md`, `docs/adr/0014-hyperparameter-free-framework-principle.md`, `docs/baseline-audit-report.md` | various | Reference documentation about the canonical paper-quantity formula (not empirical values); mentions `B_g = 1.17` or `B_g >= 0` invariants, never `B_g^emp = 0`. |

The two in-scope references are the **only** paper-draft claims that
propagated the broken `B_g^emp = 0` to the reader. Both are now fixed.

## Net diff (line count)

| File | Lines before | Lines after | Delta |
|---|---:|---:|---:|
| `docs/drafts/section-2-method.md` | 1100+ | 1100+ (3 lines removed, 1 added) | -3 (net shorter; eliminates the "monotone and never cross zero" / "empty packing sum" explanation) |
| `docs/cover-letter-tpami.md` | 700+ | 700+ (2 lines removed, 0 added) | -2 (net shorter) |

Both files are now consistent with the Wave 230 P1 audit and the
post-fix `B_g = 1.1697` values for all three core adapters.

## Commit

This change is committed as a single Wave 231 P1 commit. The
`docs/drafts/section-2-method.md` paragraph retains its position in
§2.5 (lines 710-727); the cover-letter change is at the
adapter-specific-A_g disclosure paragraph. No file relocations, no
cross-file numbering shifts, no new files added.

## Cross-reference

- `docs/audit/wave230-p1-b-g-diagnosis.md` — the underlying fix
  audit (Wave 230 P1)
- `docs/drafts/section-2-method.md` — fixed paper draft (§2.5)
- `docs/cover-letter-tpami.md` — fixed cover letter (line 125)
- `docs/drafts/abstract-final.md` — verified clean (no B_g^emp = 0 claim)
- `adaptive_reflow/adapters/profile_residual.py` — `_wrap_with_sin_modulation`
  (the underlying code fix from Wave 230 P1)
- `adaptive_reflow/theory/paper_quantities.py` — `root_cell_packing_B`
  (unchanged; the implementation is correct, only the input `g` was wrong)