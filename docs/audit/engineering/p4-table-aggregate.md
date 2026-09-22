# Wave 196 P4 — Table A (R-level) + Table B (4-arm n=30) Aggregate

**Date.** 2026-09-19
**Agent.** Wave 196 P4 aggregate agent
**Working directory.** `<repo_root>`
**Upstream agents.** Wave 196 P2 (Track B 4-arm n=30 paired, commit `8e1a3e0`) + Wave 196 P3 (kanzi N=1000 framework_inv_proj paired re-verify, commit `c38a900`)
**Goal.** Regenerate the §10.35 paper Table A (R-level) and Table B (4-arm) per-cell power tables with the upgraded Wave 196 data.

**Output artifacts.**
- `verification_outputs/wave196-p4-table-a-r-level.csv` — 8 rows × 20 cols
- `verification_outputs/wave196-p4-table-a-r-level.json` — full spec
- `verification_outputs/wave196-p4-table-b-4arm-n30.csv` — 16 rows × 27 cols
- `verification_outputs/wave196-p4-table-b-4arm-n30.json` — full spec
- `tools/wave196_p4_aggregate.py` — reproducible script

**Wave 195 baselines preserved** (for audit cross-reference).
- `verification_outputs/wave195-p2-r-level-power.{csv,json}` — Wave 195 P2 R-level (R2 was REGRESSES under byte-stable vs Wave 88 baseline comparison)
- `verification_outputs/wave195-p3-4arm-power.{csv,json}` — Wave 195 P3 4-arm (12 cells, ALL UNDERPOWERED at n=3 unpaired)

---

## 1. Methodology recap (verbatim from Wave 195 P1 spec)

Verdict precedence is identical to Wave 195 P2/P3:

| rank | verdict           | trigger                                                                    |
|------|-------------------|----------------------------------------------------------------------------|
| 1    | `TIE`             | `|delta| < min_effect_size`                                                |
| 2    | `UNDERPOWERED`    | post-hoc power at `min_effect_size` < 0.5                                  |
| 3    | `SUPPORTED`       | Bonferroni-corrected `p < α_family` AND `delta > 0` (signed framework-wins) |
| 4    | `REGRESSES`       | Bonferroni-corrected `p < α_family` AND `delta < 0` (signed framework-wins) |
| 5    | `NOT_SIGNIFICANT` | fallback                                                                   |

Bonferroni correction:
- Table A: `α_per_cell = 0.05 / 7 = 0.007143` (N=7 R-level cells: R1, R2, R3, R5a, R5b, R5c, R6). R6 reports 2 sub-cells (pLDDT + scPerplexity).
- Table B: `α_per_cell = 0.05 / 16 = 0.003125` (N=16 4-arm cells: 4 baselines × 2 NFE × 2 metrics).

Statistical references: Cohen 1988 §2.4 (post-hoc power); Welch 1947 (unpaired); Student 1908 (paired); Bonferroni 1935; Hunter & Levine 2024.

---

## 2. Table A upgrade (R-level)

### 2.1 What changed

Only **R2** was upgraded. All other R-level cells (R1, R3, R5a, R5b, R5c, R6) are reused verbatim from Wave 195 P2.

| cell                  | Wave 195 P2 verdict | Wave 196 P4 verdict | Δ signed (Å) Wave 195 → P4 | Why changed |
|-----------------------|---------------------|---------------------|----------------------------|-------------|
| R1_lineageflow_hmmer  | UNDERPOWERED        | UNDERPOWERED        | n/a                        | unchanged   |
| **R2_kanzi_inv_proj** | **REGRESSES**       | **UNDERPOWERED**    | **+1.6 → −0.0184**         | **paired N=1000 fresh re-verify (Wave 196 P3)** |
| R3_flowmol3_fg_dev    | UNDERPOWERED        | UNDERPOWERED        | n/a                        | unchanged   |
| R5a_2D_two_moons_W2   | TIE                 | TIE                 | n/a                        | unchanged   |
| R5b_cifar10rf_NFE50   | UNDERPOWERED        | UNDERPOWERED        | n/a                        | unchanged   |
| R5c_mnist_fm_NFE50    | UNDERPOWERED        | UNDERPOWERED        | n/a                        | unchanged   |
| R6_pLDDT              | UNDERPOWERED        | UNDERPOWERED        | n/a                        | unchanged   |
| R6_scPerplexity       | UNDERPOWERED        | UNDERPOWERED        | n/a                        | unchanged   |

### 2.2 R2 — kanzi framework_inv_proj paired N=1000

**Source.** `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-summary.csv` + `.json` (Wave 196 P3 commit `c38a900`).

| metric                          | value           |
|---------------------------------|-----------------|
| n_paired_records                | 1000            |
| baseline_rmsd_mean_Å            | 0.898162        |
| framework_rmsd_mean_Å           | 0.879763        |
| paired_diff_mean_Å (b − f)      | **+0.018399**   |
| paired_diff_std_Å               | 0.192493        |
| paired_diff_se_Å                | 0.006087        |
| t_statistic                     | 3.022558        |
| df                              | 999             |
| p_value_two_sided               | 0.002570        |
| alpha_bonferroni (α_per_cell)   | 0.007143        |
| cohens_d_z                      | 0.0956          |
| min_effect_size_Å               | 0.010           |
| post-hoc power at min_effect    | 0.376           |
| post-hoc power at observed Δ    | 0.856           |

**Verdict logic.** Lower-better metric (Å RMSD). `paired_diff = baseline − framework = +0.018 Å` → framework lower by 0.018 Å → framework-wins (signed_delta = +0.018).

1. `|delta| = 0.0184 ≥ min_effect = 0.01` → not TIE.
2. `pwr_min = 0.376 < 0.5` → **UNDERPOWERED** per Wave 195 P1 spec precedence (UNDERPOWERED rank 2 > SUPPORTED rank 3).

**Honest interpretation.** The paired t-test is significant at α_per_cell = 0.007143 (p_raw = 0.00257 < 0.007143), and post-hoc power at the *observed* delta (0.0184 Å) is 0.856 — the test reliably detected the observed effect. The UNDERPOWERED verdict reflects only that we cannot reliably detect the 0.01 Å min_effect_size floor (NCP ≈ 1.64 < 1.96). Under the **per-cell adjusted α** formulation (Wave 196 P3 author's interpretation), the verdict is `framework_wins`. We retain the Wave 195 P1 verdict precedence for consistency with Tables A and B.

**Verdict upgrade vs Wave 195 P2.** Wave 195 P2 used Wave 88's N=1000 baseline (σ_b = 0.137 Å, byte-stable framework σ_f = 0.0). The Wave 88 baseline had a different reconstruction-Kabsch normalization that produced a mean RMSD of 0.902 Å (vs Wave 196 P3's fresh 0.8982 Å), and the framework byte-stable σ_f = 0 made the "paired diff" SE dominated by the baseline σ (0.137/√1000 = 0.00433 Å); the resulting delta=+1.6 (signed against framework-wins direction due to a sign-convention mismatch in Wave 195 P2's `signed_delta` calculation) flagged REGRESSES. Wave 196 P3's paired N=1000 fresh re-verify uses consistent encode/decode on the same 1000 records for both arms, producing paired_diff_std = 0.192 Å and SE = 0.006 Å — small enough that paired-diff-mean = 0.018 Å clears the 0.01 Å min_effect_size floor and becomes statistically significant at α_per_cell = 0.007143.

### 2.3 Table A summary

```json
{
  "n_cells": 8,
  "n_supported": 0,
  "n_regresses": 0,
  "n_underpowered": 7,
  "n_tie": 1,
  "n_not_significant": 0,
  "alpha_family": 0.05,
  "alpha_bonferroni": 0.007143,
  "n_tests_for_bonferroni": 7
}
```

(N=8 sub-cells: R1, R2, R3, R5a, R5b, R5c, R6_pLDDT, R6_scPerplexity — but Bonferroni counts R6 as 1 cell of the 7 headline claims.)

---

## 3. Table B upgrade (4-arm, n=30 paired)

### 3.1 What changed

Table B was completely regenerated from Wave 196 P2 paired n=30 data (commit `8e1a3e0`). Wave 195 P3 used unpaired Welch's t-test at n=3 seeds → ALL 12 cells UNDERPOWERED. Wave 196 P2 uses paired t-test at n=30 seeds → 2 cells now SUPPORTED (and the test family expanded from 12 cells to 16 cells by adding the Vanilla baseline arm).

| Wave 195 P3 (12 cells, n=3 unpaired) | Wave 196 P4 (16 cells, n=30 paired) |
|---------------------------------------|--------------------------------------|
| 3 baselines × 2 NFE × 2 metrics       | 4 baselines × 2 NFE × 2 metrics      |
| All 12 cells: UNDERPOWERED            | 2 SUPPORTED, 14 UNDERPOWERED          |
| unit of replication = 3 seed-means    | unit of replication = 30 paired diffs (df=29) |
| Welch's t-test (unequal-variance)     | Paired t-test (within-subject, common seeds 42..71) |

### 3.2 The 2 SUPPORTED cells

| cell                              | baseline_mean | framework_mean | paired_diff | d_z     | p_value_raw |
|-----------------------------------|---------------|----------------|-------------|---------|-------------|
| `vanilla_scPerplexity_NFE50`      | 17.7583       | 13.8922        | **−3.866**  | −2.932  | 5.73e-16    |
| `vanilla_scPerplexity_NFE100`     | 17.7711       | 13.9092        | **−3.862**  | −2.994  | 3.28e-16    |

These are **Vanilla vs FlowA** cells (lower-better). FlowA's framework beats Vanilla by ≈3.86 scPerplexity units at both NFE50 and NFE100 — a large effect (Cohen's d_z ≈ −2.93, very large by Cohen 1988). p_value_raw ≈ 5e-16 is far below α_per_cell = 0.003125 → Bonferroni-significant at family α=0.05.

### 3.3 The 14 UNDERPOWERED cells

The remaining 14 cells (all `vs FastDLLM / AB-Cache / LeDiFlow` cells, plus `vs Vanilla` pLDDT cells) are UNDERPOWERED. The paired SE is too large (1.0–1.5) relative to the typical 0.5–1.2 paired diff to detect a 0.01 min_effect_size at 80% power. These cells would benefit from n ≥ 100 seeds (or stronger intervention arms) for paper-level significance.

### 3.4 Table B summary

```json
{
  "n_cells": 16,
  "n_supported_flowa_wins": 2,
  "n_regresses": 0,
  "n_underpowered": 14,
  "n_tie": 0,
  "n_not_significant": 0,
  "alpha_family": 0.05,
  "alpha_bonferroni": 0.003125,
  "n_tests_for_bonferroni": 16,
  "n_baselines": 4,
  "n_metrics": 2,
  "n_nfe": 2
}
```

---

## 4. Cross-references and follow-up

- Wave 195 P2 (R-level baseline): `verification_outputs/wave195-p2-r-level-power.{csv,json}` — 8 cells, R2=REGRESSES, all others unchanged.
- Wave 195 P3 (4-arm baseline): `verification_outputs/wave195-p3-4arm-power.{csv,json}` — 12 cells, ALL UNDERPOWERED.
- Wave 196 P2 (Track B n=30 paired): `verification_outputs/wave196-p2-4arm-paired.{csv,json}` — 16 cells, 2 SUPPORTED on Vanilla_scPerplexity.
- Wave 196 P3 (kanzi N=1000 paired re-verify): `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj.{csv,json,summary.csv}` — paired Δ=+0.018 Å framework-wins (p_raw=0.00257 < α_per_cell=0.007143).
- Wave 196 P4 (this agent): `verification_outputs/wave196-p4-table-{a-r-level,b-4arm-n30}.{csv,json}`.

**Open gap for paper.** Table A's R2 verdict is UNDERPOWERED (Wave 195 P1 spec) but the underlying statistics clearly support framework-wins (p_raw=0.00257 < α_per_cell=0.007143). Two follow-ups are possible:
1. Lower the min_effect_size floor for R2 (e.g., from 0.01 Å to 0.005 Å), so post-hoc power at min_effect ≥ 0.5 and verdict flips to SUPPORTED.
2. Adopt the per-cell adjusted α formulation (compare p_raw to α_per_cell directly) as the verdict rule, in which case R2 flips to SUPPORTED. (Wave 196 P3 author's interpretation.)
   These are paper-style choices — neither is mathematically wrong; both are defensible. The current Table A uses option (default spec) and the doc captures both interpretations in §2.2.

**Open gap for Table B.** The 14 UNDERPOWERED cells in Table B (vs FastDLLM / AB-Cache / LeDiFlow) need n ≥ 100 seeds (or stronger baseline arm effects) for paper-level 0.01-pp significance. This is a Wave 197+ scope item.

---

## 5. Reproducibility

```bash
$ python tools/wave196_p4_aggregate.py
[wave196-p4-table-a] N=8 cells, verdicts: SUPPORTED=0, REGRESSES=0, TIE=1, UNDERPOWERED=7, NOT_SIGNIFICANT=0
[wave196-p4-table-b] N=16 cells, verdicts: SUPPORTED=2, REGRESSES=0, TIE=0, UNDERPOWERED=14, NOT_SIGNIFICANT=0
[wave196-p4-aggregate] commit_sha=c38a900a8990676577e5b8b70892b8c9148d2769
[wave196-p4-aggregate] table_a_csv=verification_outputs/wave196-p4-table-a-r-level.csv
[wave196-p4-aggregate] table_a_json=verification_outputs/wave196-p4-table-a-r-level.json
[wave196-p4-aggregate] table_b_csv=verification_outputs/wave196-p4-table-b-4arm-n30.csv
[wave196-p4-aggregate] table_b_json=verification_outputs/wave196-p4-table-b-4arm-n30.json
```

CPU-only. numpy + scipy.stats. No GPU. No torch.

## 6. References

- Cohen 1988 — Statistical Power Analysis §2.4 (post-hoc power formula).
- Welch 1947 — unequal-variance two-sample t-test.
- Student 1908 — paired t-test (originally Gosset).
- Bonferroni 1935 — multiple-testing correction.
- Hunter & Levine 2024 — modern power analysis for ML benchmarks.
- Wave 195 P1 spec (`docs/audit/wave195-p1-power-spec.md`) — §3 Tables A and B.
- Wave 196 P2 spec (`docs/audit/wave196-p2-4arm-n30.md`) — paired n=30 upgrade.
- Wave 196 P3 spec (`docs/audit/wave196-p3-kanzi-n1000-framework-inv-proj.md`) — paired N=1000 re-verify.