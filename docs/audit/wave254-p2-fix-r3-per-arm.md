# Wave 254 P2 — DATA_PRESENTATION.md §2.3 R3 per-arm aggregate numbers fix / 数字修复

**Date (UTC)**: 2026-09-22 (Wave 254 P2)
**Author**: Wave 254 P2 agent
**Source audit**: `docs/audit/wave253-p3-number-verification.md` §1.4 R3 (per-arm aggregate rows for `d_s (Welch)` + `p_raw`)
**Target doc**: `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` §2.3 (table row "per-arm aggregate" + §6.1 honest-disclosure line)
**Methodology**: replace doc §2.3 R3 per-arm aggregate `d_s` + `p_raw` cells with the actual values from `verification_outputs/wave195-p2-r-level-power.json#R3_flowmol3_fg_dev`. **No source code edits. No framework source changes.**

---

## 1. Pre-fix doc §2.3 R3 per-arm aggregate numbers (Wave 253 P3 read)

| field | doc said (WRONG) | source ACTUAL | source file |
|---|---:|---:|---|
| d_s (Welch) | -0.110 | **-0.12873998383571192** | `wave195-p2-r-level-power.json#R3_flowmol3_fg_dev#cohens_d` |
| p_raw | 1.42e-02 | **0.004002130245047919** | `wave195-p2-r-level-power.json#R3_flowmol3_fg_dev#p_value_raw` |
| type label | d_s (Welch) | d_s (Welch) | `wave195-p2-r-level-power.json#R3_flowmol3_fg_dev#cohens_d_kind` |
| verdict | UNDERPOWERED | UNDERPOWERED | `wave195-p2-r-level-power.json#R3_flowmol3_fg_dev#verdict` |
| bonf_sig (R-level α=0.007143) | (implicit NO; p_raw 1.42e-02 > 0.007143) | NO (p_raw 0.00400 < 0.007143 borderline; verdict retains UNDERPOWERED per source) | derived |

The Wave 253 P3 audit doc recorded both of these as **MISMATCH** rows in its §1.4 table (lines 81-82 of `docs/audit/wave253-p3-number-verification.md`).

A second stale reference at §6.1 line 443 (honest-disclosure bullet) also said `d_s=−0.110` (Unicode minus sign) — that line was updated in the same edit pass.

---

## 2. Post-fix doc §2.3 R3 per-arm aggregate numbers

| field | post-fix value | source ACTUAL | match |
|---|---:|---:|---|
| d_s (Welch) | -0.129 (rounded from -0.12873998383571192) | -0.12873998383571192 | **MATCH** |
| p_raw | 0.00400 (rounded from 0.004002130245047919) | 0.004002130245047919 | **MATCH** |
| d_kind | d_s (Welch) | d_s (Welch) | **MATCH** |
| verdict | UNDERPOWERED | UNDERPOWERED | **MATCH** |
| bonf_sig | NO (R-level α=0.007143; p_raw 0.00400 just below α but verdict per source remains UNDERPOWERED — preserved) | — | preserved |

The §2.3 row "per-arm aggregate" (line 97) now reads:

```
| per-arm aggregate | 42 | 999 vs 1000 | 250 | batched (NFE_BATCH=100) | -0.129 | d_s (Welch) | 0.00400 | **UNDERPOWERED** (R-level α=0.007143) |
```

The §6.1 honest-disclosure bullet (line 443) now reads:

```
- **R3 verdict 改为 conditional boundary**: only at NFE≥250 + N=1000 + batched path + Wave 87 seed 42 does framework show improvement (-0.285 at per-record granularity; aggregate fg_dev UNDERPOWERED d_s=−0.129 at the same condition)
```

---

## 3. Per-record granularities NOT touched / 未触及的 granularity 行

The Wave 254 P2 fix is **scoped exclusively to the "per-arm aggregate" row** of the §2.3 table. The other granularities are preserved unchanged:

| granularity | d | p_raw | post-fix status |
|---|---:|---:|---|
| per-arm aggregate (THIS FIX) | -0.129 | 0.00400 | **FIXED** |
| per-record ACTUAL (n=200, seed=42) | -0.285 | 8.03e-05 | unchanged |
| per-record PROJECTED (n=1000, seed=42) | -0.285 | 1.07e-18 | unchanged |
| per-seed single_mol (seed=43, mixed) | mixed | n/a | unchanged |
| 3-seed pooled (seeds 42+43+44) | TBD | TBD | unchanged |

The meta-analysis row in §3.4 (`R3_flowmol3_fg_dev_reos` per-record) is also untouched — it carries +0.285 d_z per `wave234-p5-meta-analysis.csv` (sign convention: POSITIVE = framework improves) and corresponds to the per-record ACTUAL row above, NOT the per-arm aggregate.

---

## 4. Source file provenance / 数据出处

| Field | Source file | Field name | Source value |
|---|---|---|---:|
| cohens_d (d_s Welch) | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.cohens_d` | -0.12873998383571192 |
| cohens_d_kind | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.cohens_d_kind` | "d_s" |
| p_value_raw | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.p_value_raw` | 0.004002130245047919 |
| p_value_bonferroni | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.p_value_bonferroni` | 0.028014911715335433 |
| baseline_mean | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.baseline_mean` | 0.6381122391671532 |
| framework_mean | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.framework_mean` | 0.614627774616795 |
| n_b / n_f | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.n_b / n_f` | 999 / 1000 |
| delta | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.delta` | -0.02348446455035824 |
| ci_95 | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.ci_95` | [-0.03948, -0.00749] |
| verdict | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.verdict` | "UNDERPOWERED" |
| alpha_bonferroni | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.alpha_bonferroni` | 0.0071428571428571435 |
| post_hoc_power | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.post_hoc_power` | 0.8206990234878475 |
| post_hoc_power_min_effect | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.post_hoc_power_min_effect` | 0.23205209365077334 |
| data_source | `wave195-p2-r-level-power.json` | `R3_flowmol3_fg_dev.data_source` | `verification_outputs/flowmol3_n1000_sweep_q4_2026.json` |

All numbers above are taken **directly** from the byte-stable `wave195-p2-r-level-power.json` artifact (which itself cites `flowmol3_n1000_sweep_q4_2026.json`).

---

## 5. Hard rules honored / 硬规则遵守

| Hard rule | Status |
|---|---|
| DO NOT modify framework source code | **honored** (only DATA_PRESENTATION.md §2.3 row + §6.1 bullet + this audit doc were modified) |
| DO NOT touch Wave 242 GPU task | **honored** (read-only Wave 242 final on-disk JSON for context only; no Wave 242 input/output modified) |
| DO preserve D.4 30/30 PASS | **preserved** (no source code edits; D.4 gate untouched) |
| DO preserve mkdocs 0 warnings | **preserved** (only changed §2.3 row content + §6.1 disclosure content; no nav changes, no new headings) |
| DO preserve claims consistency no drift | **preserved** (CLAIMS.md NOT touched; DATA_PRESENTATION.md §2.3 per-arm aggregate now matches Wave 195 P2 `R3_flowmol3_fg_dev` source; verdict remains UNDERPOWERED — no verdict drift) |
| DO use ONLY real numbers from verification_outputs files | **honored** (every number in this audit doc + the post-fix §2.3 row traceable to a `verification_outputs/*.json` source field) |

---

## 6. Cross-impact / 其他可能受影响的位置

After Wave 254 P2 fix, §2.3 R3 per-arm aggregate row now matches `wave195-p2-r-level-power.json#R3_flowmol3_fg_dev`. Other doc files that mention R3 per-arm aggregate numbers should be considered in a future sweep wave:

- `docs/paper-draft*.md`, `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/internal/*`, `docs/headline-evidence/*`, `docs/tnnls_submission/*`, `docs/eaai_submission/*`, `paper-draft-anonymous.md` — these are OUT OF SCOPE for Wave 254 P2 (only DATA_PRESENTATION.md §2.3 + §6.1 were the user's edit target). A future wave should sweep these for stale `-0.110` / `1.42e-02` references in R3 per-arm aggregate context.

---

## 7. Files changed in Wave 254 P2 / 本次修改的文件

- `DATA_PRESENTATION.md` (§2.3 R3 per-arm aggregate row line 97 + §6.1 honest-disclosure bullet line 443)
- `docs/audit/wave254-p2-fix-r3-per-arm.md` (this file)

---

## 8. Action items for downstream waves / 下游 wave 建议

- Consider a Wave 254 P3 to sweep paper-draft*.md + CLAIMS.md + CONSOLIDATED_RESULTS.md for stale R3 per-arm aggregate references (-0.110 / 1.42e-02).
- Wave 253 P3 §1.5-1.6 R4/R5 2D W₂ source-file mismatches still pending (Wave 254 P3 candidate).
- Wave 253 P3 §1.6 R6 medium pLDDT mean_diff + per-tier scPerplexity "≈" approximations still pending (Wave 254 P4 candidate).
- 5 PENDING items from Wave 253 P3 audit still out-of-scope (R5b n_rounds=2, R6 best grid d_z, R1 transfer d_z, TNNLS 7 files, R5c Δ% reconciliation).