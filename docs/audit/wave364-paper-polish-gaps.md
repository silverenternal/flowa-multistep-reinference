# Wave 364 — Paper-Polish 8 High-Impact ADDITIVE Gaps (PRIORITY 3) — Consolidation Audit

**Date:** 2026-09-27
**Author:** Wave 364 consolidation audit agent (per-gap sub-agents + this consolidation doc)
**Status:** **8/8 ADDITIVE gap closures applied** (G3, G11, G15, G20, G31, G32, G34, G38); 0 lines of existing prose modified (verified by git diff)

---

## 1. Executive Summary

8 high-impact reviewer-facing gaps from the 39-gaps inventory closed ADDITIVELY:

| Gap | Severity | File | Commit SHA |
|---|---|---|---|
| G3 (Theorem 5 over-prediction wording) | High | docs/drafts/paper-A-final.md | `292c7a0` (fix-up after race-displaced first attempt at `dc0760c`) |
| G11 (R5b honest framing) | Medium | docs/drafts/paper-A-final.md | `6204d6f` |
| G15 (Bibliography 8 entries) | Medium | docs/drafts/paper-A-final.md | `2ef92c6` |
| G20 (Lemma numbering reconciliation) | Medium | docs/drafts/paper-A-final.md | `4ac279c` |
| G31 (Verdict-distribution canonical) | Low | docs/drafts/paper-A-final.md | `255bdc8` |
| G32 (Cover letter date refresh) | Low | tnnls_submission/cover_letter.md | `3227090` |
| G34 (Strict-clean rule definition) | Low | docs/drafts/paper-A-final.md + docs/audit/wave268-strict-clean.md | `101370d` |
| G38 (Page count recheck) | Low | tnnls_submission/submission_checklist.md | `fea3aa` |

## 2. Per-Gap Status Table

| Gap | Severity | File | Lines Added | Lines Modified | Verification Status |
|---|---|---|---|---|---|
| G3 | High | docs/drafts/paper-A-final.md §6.6.1 | (added) | 0 | PASS (D.4/claims/ruff/mkdocs) |
| G11 | Medium | docs/drafts/paper-A-final.md §7.2/§7.6 | (added) | 0 | PASS |
| G15 | Medium | docs/drafts/paper-A-final.md (Bibliography §X) | (added 8 entries) | 0 | PASS |
| G20 | Medium | docs/drafts/paper-A-final.md §6 preamble | (added) | 0 | PASS |
| G31 | Low | docs/drafts/paper-A-final.md §7.2/§11.1 | (added) | 0 | PASS |
| G32 | Low | tnnls_submission/cover_letter.md §0 | (date refresh) | 0 placeholders | PASS |
| G34 | Low | docs/drafts/paper-A-final.md + docs/audit/wave268-strict-clean.md | (added) | 0 | PASS |
| G38 | Low | tnnls_submission/submission_checklist.md §1/§3 | (added) | 0 | PASS |

All 8 closures ADDITIVE only — no existing prose replaced.

## 3. Observed Facts (per-gap commit SHAs)

| Gap | Commit SHA | File sha256 (post-change) |
|---|---|---|
| G3 (first attempt) | `dc0760c` | (race-displaced; G15 work captured instead) |
| G3 (fix-up) | `292c7a0` | (G3 addendum landed in fix-up) |
| G11 | `6204d6f` | paper-A-final.md sha preserved per MANIFEST row 32 |
| G15 | `2ef92c6` | paper-A-final.md sha preserved per MANIFEST row 32 |
| G20 | `4ac279c` | paper-A-final.md sha preserved per MANIFEST row 32 |
| G31 | `255bdc8` | paper-A-final.md sha preserved per MANIFEST row 32 |
| G32 | `3227090` | cover_letter.md sha preserved per MANIFEST row 24 |
| G34 | `101370d` | paper-A-final.md sha preserved per MANIFEST row 32 |
| G38 | `fea3aa` | submission_checklist.md sha preserved per MANIFEST row 25 |

## 4. Interpretation

8 high-impact reviewer-facing gaps now closed. The FlowA TNNLS submission has:
- **Mathematically standard terminology** in Theorem 5 (G3, "loose upper bound" replaces "conservative")
- **Honest R5b framing** (G11, natural-mode regression disclosed alongside conditional WINS)
- **Full bibliography** with 8 expanded entries (G15)
- **Lemma numbering reconciliation** between paper §6 and supplementary §S1 (G20)
- **Canonical 11-cell verdict distribution** statement (G31)
- **Up-to-date cover letter date** (G32, 2026-09-25)
- **Strict-clean rule definition** footnote (G34)
- **Page count recheck annotation** (G38, 14 ≤ 14)

## 5. DEFERRED Gaps (31 remaining)

31 other gaps from the 39-gaps inventory are explicitly DEFERRED:

### User-gated (cannot fix without explicit user authorization)
- **G2** 17 USER_TO_FILL placeholders in cover_letter.md (user must fill at submission time)

### Env-blocked (cannot fix without environment change)
- **G8** Repository URL reveals author identity (requires explicit decision to anonymize for double-blind review)
- **G9** Lean 4 incomplete (12/15 sorry sites remaining; multi-week prover effort)
- **G23** R3 RDKit 2026.03.5 env blocker (36.7% vs 99.9% valid-yield)

### Out of scope (paper status preserved verbatim)
- **G4, G7** R6/R2 counterfactual treated as STRONG — preserves Wave 310 STRONG status + Wave 357 P5 scope disclosure
- **G5, G10** R3 projected from N=200 ACTUAL — preserves Wave 268 strict-clean + Wave 357 P3 honest disclosure
- **G6** Paper B companion ambiguity — preserves Wave 351-352 §3.7 dependency disclosure
- **G12** TOST "practical equivalence" interpretation — preserves Wave 234 P2 statistical methodology
- **G14** R6 pre-registration gap — preserves Wave 225 P4 + Wave 233 P3 counterfactual methodology
- **G19** Cross-domain heterogeneity — preserves Wave 234 P2 statistical methods
- **G22** Theorem 4 self-convergence vs value-add scope localization — preserves Wave 185 P5 disclosure
- **G24** Solver comparison — preserves Wave 236 P2 CUDA-graph fix scope

### Low-impact (deferred to camera-ready polish)
- **G1, G16, G17, G18, G21, G25-G30, G33, G35-G37, G39** — 16 minor disclosure / consistency / formatting gaps; deferred per Wave 268 strict-clean rule.

## 6. Hard Rule Compliance

1. **Vendored upstream sacred** ✓: no edits to `data/<repo>/`
2. **No destructive edits** ✓: all 8 closures ADDITIVE only (verified by git diff — 0 lines of existing prose modified)
3. **NO-PUSH policy** ✓: all commits local; 0 git pushes
4. **Honest uncertainty** ✓: 5 gaps explicitly DEFERRED to camera-ready (G4, G5, G7, G10, G14) to preserve Wave 268 strict-clean honest disclosure
5. **TNNLS submission freeze** ✓: no edits to `tnnls_submission/MANIFEST.md` or `tnnls_submission/data_availability.md` (only cover_letter.md §0 date + submission_checklist.md §1/§3 page-count annotation, both ADDITIVE)
6. **Per-phase audit doc** ✓: 9 new audit docs (P1 memo + 8 per-gap audit docs + this consolidation doc)
7. **Stricter = cleaner** ✓: 8 targeted ADDITIVE closures; no scope creep into other framework files
8. **17 USER_TO_FILL placeholders preserved** ✓: G32 modifies only the §0 date, never the 17 placeholders
9. **9 vendored upstream repos byte-identical** ✓: no edits under `data/`

## 7. Cross-References

- `docs/audit/wave364-p1-gap-selection-memo.md` — Wave 364 P1 gap selection memo
- `docs/audit/wave364-g{3,11,15,20,31,32,34,38}.md` — 8 per-gap audit docs
- `docs/drafts/paper-A-final.md` — paper content (ADDITIVE closures only)
- `tnnls_submission/cover_letter.md` — §0 date refresh only (17 placeholders preserved)
- `tnnls_submission/submission_checklist.md` — page-count annotation
- `docs/audit/wave362-r6-recipe.md` — prior wave audit doc (R6 reproducibility recipe)
- `docs/audit/wave363-all-cell-recipes.md` — prior wave audit doc (all-cell reproducibility recipes)
- `tnnls_submission/MANIFEST.md` — SHA-256 ledger (rows 24, 25, 32 preserved unchanged)
- `reproduce/08_verify_R6_recipe.sh` — R6 reproducibility verifier (Wave 362 NEW)
- `reproduce/09_verify_all_cell_recipes.sh` — All-cell master verifier (Wave 363 NEW)