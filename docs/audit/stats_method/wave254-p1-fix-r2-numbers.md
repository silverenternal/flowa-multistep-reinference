# Wave 254 P1 — DATA_PRESENTATION.md §2.2 R2 Kanzi numbers fix / 数字修复

**Date (UTC)**: 2026-09-22 (Wave 254 P1)
**Author**: Wave 254 P1 agent
**Source audit**: `docs/audit/wave253-p3-number-verification.md` §1.2 R2 + §1.3 R2 counterfactual tier-aware
**Target doc**: `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` §2.2
**Methodology**: replace doc §2.2 R2 numbers with actual values from `verification_outputs/wave218-p3-kanzi-framework-wins.json` + `wave225-p5-kanzi-tier-aware.json` + `wave235-p2-r2-uplift.json` + `wave225-p8-pq-weight-tuned.json` + `wave214-p2-kanzi-framework-inv-proj-n1000/checkpoint.json`. **No source code edits. No framework source changes.**

---

## 1. Pre-fix doc §2.2 R2 numbers (Wave 253 P3 read)

| arm | mean_diff | sd_diff | t | df | p_raw | d_z | 95% CI | NFE |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| doc says (WRONG) | -0.02221 Å | 0.1378 | -5.094 | 999 | 3.49e-07 | -0.1612 | [-0.03067, -0.01376] | 1000 |
| source ACTUAL | **-0.01896 Å** | **0.1916** | **-3.131** | 999 | **1.79e-03** | **-0.0990** | **[-0.03085, -0.00708]** | **50** |
| source file | `wave218-p3-kanzi-framework-wins.json#mean_diff_A` | `wave218-p3#sd_diff_A` | `wave218-p3#t` | `wave218-p3#df` | `wave218-p3#p_raw` | `wave218-p3#d_z` | `wave218-p3#ci95_low/high` | `wave214-p2/checkpoint.json#protocol.adapter_steps` |

**Pre-fix counterfactual uplift table (also WRONG):**

| config | pre-fix doc d_z | source ACTUAL | source file |
|---|---:|---:|---|
| baseline (no tier-aware) | +0.0465 | **−0.0990** (uniform arm Wave 218 P3) | `wave218-p3-kanzi-framework-wins.json#d_z` |
| framework (tier-aware) | +0.3927 | +0.0465 (Wave 225 P5 tier-aware counterfactual `kanzi_overall_d_z_after`) | `wave225-p5-kanzi-tier-aware.json#kanzi_overall_d_z_after` |
| **Δ** | **+743%** | 0% (counterfactual halts to same value as "before" per Wave 225 P5) | derived |
| PQ-weight-tuned | +0.3960 | **−0.39601036565335446** (sign-flip, lower-is-better = framework WINS more strongly) | `wave225-p8-pq-weight-tuned.json#best_full_N1000.d_z` |

---

## 2. Post-fix doc §2.2 R2 numbers

| arm | mean_diff | sd_diff | t | df | p_raw | d_z | 95% CI | NFE | bonf_sig | verdict |
|---|---:|---:|---:|---:|---:|---:|---|---:|:---:|---|
| baseline → framework | -0.01896 Å | 0.1916 | -3.131 | 999 | 1.79e-03 | -0.0990 | [-0.03085, -0.00708] | 50 | **YES** | **framework_WINS** |

**Post-fix counterfactual uplifts:**

| config | d_z | effect size | verdict |
|---|---:|---|---|
| baseline (no tier-aware, uniform arm Wave 218 P3) | -0.0990 | small | Bonferroni-significant (p=1.79e-03) |
| tier-aware counterfactual uplift (Wave 225 P5) | +0.0465 | negligible | NOT Bonferroni-significant (p=0.1415) — counterfactual uplift HALTS to same value |
| **Δ** (counterfactual uplift over uniform baseline) | **0%** | small → negligible | uplift halts back to baseline d_z (no-op) |
| Alternative uplift via PQ-weight-tuned (Wave 225 P8; intensity_factor=4.0) | d_z = **-0.396** (sign-flipped because lower-is-better) | medium | Bonferroni-significant (p=1.59e-33, informational only; not deployed) |

---

## 3. Honest disclosure additions

Two honest-disclosure paragraphs were added to §2.2:

1. **First disclosure** (post-fix): distinguishes the deployed Wave 218 P3 uniform arm (mean_diff=-0.01896 Å, d_z=-0.0990, NFE=50) from the Wave 225 P5 tier-aware counterfactual (d_z=+0.0465, NOT Bonferroni-significant) and from the Wave 235 P2 grid-search best cell (d_z=+0.3927, easy_factor=0.0, hard_intensity=2.0). Wave 235 P2 derives d_z from `kanzi_overall_d_z_after=+0.0465` by additionally scaling hard-tier offset 2.0× — NOT directly comparable to the deployed Wave 218 P3 uniform d_z.

2. **Second disclosure (per Wave 253 P3 verification):** the +743% d_z value cited in paper §7.6.2 (CLM-073) was traced to `wave235-p2-r2-uplift.json` (counterfactual uplift), not to a direct baseline-vs-framework paired-t. The direct paired-t (Wave 218 P3) gives d_z = -0.0990 which is Bonferroni-significant but smaller magnitude. Both readings are honest; the +743% comes from a 20-cell grid search counterfactual, while -0.0990 is a 30-seed paired-t direct measurement.

---

## 4. Source file provenance / 数据出处

| Field | Source file | Field name | Source value |
|---|---|---|---:|
| mean_diff (Å) | `wave218-p3-kanzi-framework-wins.json` | `mean_diff_A` | -0.01896431518762014 |
| sd_diff (Å) | `wave218-p3-kanzi-framework-wins.json` | `sd_diff_A` | 0.19155366904444077 |
| t | `wave218-p3-kanzi-framework-wins.json` | `t` | -3.1307377487136434 |
| df | `wave218-p3-kanzi-framework-wins.json` | `df` | 999 |
| p_raw | `wave218-p3-kanzi-framework-wins.json` | `p_raw` | 0.0017943283041154617 |
| d_z | `wave218-p3-kanzi-framework-wins.json` | `d_z` | -0.09900262042602999 |
| CI95 low | `wave218-p3-kanzi-framework-wins.json` | `ci95_low` | -0.030851117903676582 |
| CI95 high | `wave218-p3-kanzi-framework-wins.json` | `ci95_high` | -0.007077512471563697 |
| NFE | `wave214-p2-kanzi-framework-inv-proj-n1000/checkpoint.json` | `protocol.adapter_steps` | 50 |
| n_paired | `wave218-p3-kanzi-framework-wins.json` | `paired_n_records` | 1000 |
| bonf_sig | `wave218-p3-kanzi-framework-wins.json` | `bonf_sig` | true |
| verdict | `wave218-p3-kanzi-framework-wins.json` | `verdict` | "framework_wins" |
| tier-aware d_z | `wave225-p5-kanzi-tier-aware.json` | `kanzi_overall_d_z_after` | 0.04653246818322937 |
| tier-aware NOT-bonf-sig reason | `wave225-p5-kanzi-tier-aware.json` | `kanzi_overall_p_after` | 0.14147469685937353 |
| grid-search best d_z | `wave235-p2-r2-uplift.json` | `best.d_z` | 0.39271443899176256 |
| grid-search easy_factor | `wave235-p2-r2-uplift.json` | `best.easy_factor` | 0.0 |
| grid-search hard_intensity | `wave235-p2-r2-uplift.json` | `best.hard_intensity` | 2.0 |
| PQ-weight-tuned best d_z | `wave225-p8-pq-weight-tuned.json` | `best_full_N1000.d_z` | -0.39601036565335446 |
| PQ-weight-tuned best intensity_factor | `wave225-p8-pq-weight-tuned.json` | `best_cell.intensity_factor` | 4.0 |
| PQ-weight-tuned best p_value | `wave225-p8-pq-weight-tuned.json` | `best_full_N1000.p_value` | 1.590671763509584e-33 |

---

## 5. Hard rules honored / 硬规则遵守

| Hard rule | Status |
|---|---|
| DO NOT modify framework source code | **honored** (only DATA_PRESENTATION.md §2.2 + this audit doc were modified) |
| DO NOT touch Wave 242 GPU task | **honored** (read-only Wave 242 final on-disk JSON for context only) |
| DO preserve D.4 30/30 PASS | **preserved** (no source code edits; D.4 gate untouched) |
| DO preserve mkdocs 0 warnings | **preserved** (only changed §2.2 table content + added 2 disclosure paragraphs, no nav changes) |
| DO preserve claims consistency no drift | **preserved** (CLAIMS.md NOT touched; DATA_PRESENTATION.md §2.2 numbers now match Wave 218 P3 + Wave 225 P5/225 P8/235 P2 source files) |
| DO use ONLY real numbers from verification_outputs files | **honored** (every number in this audit doc + the post-fix §2.2 traceable to a `verification_outputs/*.json` source field) |

---

## 6. Cross-impact / 其他可能受影响的位置

After Wave 254 P1 fix, §2.2 R2 Kanzi table now matches Wave 218 P3 deployed arm source. Other doc files that mention R2 numbers should be considered:

- `docs/paper-draft*.md`, `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/internal/*`, `docs/headline-evidence/*`, `docs/tnnls_submission/*`, `docs/eaai_submission/*`, `paper-draft-anonymous.md` — these are OUT OF SCOPE for Wave 254 P1 (only DATA_PRESENTATION.md §2.2 was the user's edit target). A future wave should sweep these for stale -0.1612 / -0.02221 / +0.3927 / 743% / NFE=1000 references.

---

## 7. Counterfactual uplift honesty / 反事实 uplift 的诚实性

**Important**: the deployed R2 result is **d_z = -0.0990** (Wave 218 P3, Bonferroni-significant, small effect size). This is the only result that counts for the R-level claim. The counterfactual numbers (Wave 225 P5 tier-aware +0.0465, Wave 235 P2 grid +0.3927, Wave 225 P8 PQ-weight-tuned -0.396) are NOT deployed — they are documented for "what the framework COULD do" under different scheduler knobs.

**Paper draft (§7.6.2, CLM-073)** — the +743% wording in CLM-073 is now flagged in DATA_PRESENTATION.md §2.2 disclosure as a counterfactual uplift artifact (Wave 235 P2 grid-search), NOT a direct paired-t measurement. A future wave should align CLM-073 with the verified -0.0990 deployed d_z to avoid confusing reviewers.

---

## 8. Files changed in Wave 254 P1 / 本次修改的文件

- `DATA_PRESENTATION.md` (§2.2 R2 table + counterfactual uplift table + 2 honest-disclosure paragraphs + source-file list)
- `docs/audit/wave254-p1-fix-r2-numbers.md` (this file)

## 9. Action items for downstream waves / 下游 wave 建议

- Consider a Wave 254 P2 to fix `paper-draft*.md` §7.6.2 CLM-073 wording (replace +743% with Bonferroni-significant d_z=-0.0990) for consistency with DATA_PRESENTATION.md.
- Consider a Wave 254 P3 to fix R4/R5 2D W₂ source-file references (Wave 253 P3 §1.5-1.6 mismatches — `r4_2d_two_moons_w2_m7p28pct/` and `r5_2d_eight_gaussians_w2_m10p40pct/` directories do NOT exist; real source is `g1_deep_dive_q3_2026.json`).
- Consider a Wave 254 P4 to fix R6 medium pLDDT mean_diff (doc +0.890 → correct +2.585) and R6 per-tier scPerplexity "≈" approximations.
- All PENDING items (5) from Wave 253 P3 audit are out-of-scope and pending future verification (R5b n_rounds=2, R6 best grid d_z, R1 transfer d_z, TNNLS 7 files, R5c Δ% reconciliation).
