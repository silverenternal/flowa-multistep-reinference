# Wave 256 P5 — Final Verification

**Date:** 2026-09-22
**Agent:** Wave 256 P5
**Scope:** Final verification of Wave 256 P1-P4 work that addresses DeepSeek external review feedback on `DATA_PRESENTATION.md`.

## 1. Verification gates

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable | `pytest tests/test_d4_regression_vectors.py` | **30 passed, 3 warnings** (warnings pre-existing, non-fatal) |
| mkdocs build --strict | `mkdocs build --strict` | **PASS — 0 warnings**, built in 25.27 s |
| claims_consistency | `tools/check_claims_consistency.py` | **"No drift detected."** |
| DATA_PRESENTATION.md exists | `ls DATA_PRESENTATION.md` | **OK** (44,645 bytes, internal-only annotated) |
| DATA_PRESENTATION_BRIEF.md exists | `ls DATA_PRESENTATION_BRIEF.md` | **OK** (3,651 bytes, external version) |

## 2. DeepSeek feedback coverage

DeepSeek's feedback identified three CRITICAL data issues that must be addressed BEFORE splitting the document:

### 2.1 R2 Kanzi paper number consistency (DeepSeek concern 1)

| Reading | d_z value | Status |
|---|---|---|
| Deployed paired-t (Wave 218 P3) | -0.0990 | **Primary** (now cited in paper §7.6.2) |
| Counterfactual uplift (Wave 225 P5) | +0.0465 | Sensitivity analysis (§3.5) |
| Grid search best (Wave 235 P2) | +0.3927 | Sensitivity analysis (§3.5), NOT cited as primary |
| PQ-weight-tuned (Wave 225 P8) | -0.396 | Sensitivity analysis (§3.5), NOT cited as primary |

**Resolution:** Paper §7.6.2 now cites the deployed arm d_z=-0.0990 (the actual deployed framework arm). Counterfactual / grid-search / PQ-tuned readings are listed as §3.5 sensitivity analyses only. No reader can confuse them with the deployed number.

**Handled by:** Wave 256 P1 (`docs/audit/wave256-p1-r2-paper-number-fix.md`).

### 2.2 Cross-paper number-source audit (DeepSeek concern 2)

Wave 256 P2 (`docs/audit/wave256-p2-full-paper-audit.md`) audited every number in paper §3.3-§3.7 and §7.6. Result:

- **R4/R5 original d_z = -2.93 / -3.13 → CONFIRMED REMOVED.** No source supported these values; they are not in the current paper draft.
- **Every remaining §3.3-§3.7 + §7.6 number has a `verification_outputs/` source.**
- **Zero claims without source support** in the current draft.

### 2.3 Misleading "data integrity" line (DeepSeek concern 3)

Wave 256 P3 (`docs/audit/wave256-p3-validation-language.md`) revised the validation-language block to explicitly distinguish:
- **ACTUAL MEASUREMENTS** (read byte-addressable from `verification_outputs/`)
- **COUNTERFACTUAL / PROJECTED numbers** (sensitivity analyses only)

The data-integrity line is no longer ambiguous.

### 2.4 Document split (DeepSeek suggestion)

Wave 256 P4 (`docs/audit/wave256-p4-split-docs.md`) split `DATA_PRESENTATION.md` into:
- `DATA_PRESENTATION_BRIEF.md` (3,651 bytes / ~75 lines) — external version for teacher + grad student meeting + figure-making. **Zero internal IDs** (no Wave refs, no CLM refs, no audit-doc paths, no AI-tool refs).
- `DATA_PRESENTATION.md` (44,645 bytes / 583 lines) — annotated as `Internal Data Index (NOT for external presentation)` with explicit disclosure of counterfactual / projected numbers.

## 3. Number-source verification (final sanity check)

Every number in `DATA_PRESENTATION_BRIEF.md` traces through `DATA_PRESENTATION.md §2.x` to a `verification_outputs/*.json` byte-stable artifact:

| Brief number | Internal § | Verification source |
|---|---|---|
| R1: 158 / 342 / +116.46% | §2.1 | `wave206-p1-lineageflow-n1000.json` |
| R2: d_z=-0.0990 | §2.2 | `wave218-p3-kanzi-framework-wins.json` |
| R3: d_z=-0.285 | §2.3 | `wave208-p2-flowmol3-sanity.json` |
| R4: 2.85 / 0.62 / -78.25% | §2.4 | `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` |
| R5: 2.31 / 0.76 / -67.10% | §2.5 | `g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` |
| R5b: 454.39 / 442.89 | §2.6 | `wave235-p1-r5b-fix.json#rounds1` |
| R6 k6 pLDDT: +0.071 / +0.224 / +189% | §2.7 | `wave225-p4-k6-tier-aware.json` |
| Theorem 1 quantities | §3.3 / §3.4 | paper §3 (kanzi L2, lineageflow entropy) |

## 4. Internal-ID grep audit (DATA_PRESENTATION_BRIEF.md)

```
$ grep -E -i "wave[0-9]+p?[0-9]*|CLM-[0-9]+|/audit/|verification_outputs|docs/audit" \
    DATA_PRESENTATION_BRIEF.md
(no matches)
```

**n_internal_ids_in_brief = 0** (zero wave refs, zero CLM refs, zero audit-doc paths)

## 5. Pre-existing uncommitted changes (NOT my scope)

The working tree has 3 uncommitted files that pre-date this wave and are NOT my scope per the "no source code changes" rule:

| File | Change | Scope |
|---|---|---|
| `tools/run_sota_cifar_experiment.py` | `WAVE247_SEED` → `WAVE247_P3_SEED` | WAVE247 P3 work |
| `verification_outputs/wave225-p4-k6-tier-aware.json` | D.4 timing refresh (30.21 s) | WAVE247 D.4 refresh |
| `docs/audit/wave234-p6-non-inferiority.md` | minor metadata | WAVE234 P6 work |

These changes are out-of-scope for Wave 256 P5 and remain uncommitted.

## 6. Ready for teacher meeting

| Criterion | Status |
|---|---|
| Brief fits on 3-5 printed pages | ✓ (3,651 bytes / ~75 lines) |
| No internal IDs in brief | ✓ (grep audit clean) |
| R2 paper number consistency | ✓ (deployed -0.0990 primary, +0.3927 sensitivity only) |
| R4/R5 honest-disclosure expansion | ✓ (d_z=-2.93/-3.13 confirmed REMOVED) |
| Validation language distinguishes actual vs counterfactual | ✓ (Wave 256 P3) |
| Number-source audit complete | ✓ (Wave 256 P2) |
| 7/7 R-level cells framework_WINS | ✓ (R2 weak Bonf-sig, R5b conditional, others medium-large) |
| D.4 30/30 byte-stable | ✓ |
| mkdocs strict 0 warnings | ✓ |
| claims_consistency no drift | ✓ |

**Ready for teacher meeting: YES.**

## 7. Commit / 提交

This audit doc is added as a single commit. No source code changes.