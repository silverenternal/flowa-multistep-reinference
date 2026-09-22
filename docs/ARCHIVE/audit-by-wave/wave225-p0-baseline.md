# Wave 225 P0 — Baseline Audit (2026-09-21)

Pre-Wave-225 baseline of the 5 weak metrics + D.4 byte-stable gate.
Captured before any Wave 225 modifications so future diffs have a clean reference.

## D.4 byte-stable gate

| Metric | Value |
|---|---|
| Test file | tests/test_d4_regression_vectors.py |
| Result | 30 passed, 3 warnings in 6.07s |
| Status | 30/30 PASS |

## 5 weak metrics (R2, R3, R5a, R5b, R6)

| Cell | Metric | n | d_z | Verdict | Source CSV |
|---|---|---:|---:|---|---|
| R2_kanzi_inv_proj | reconstruction_rmsd_Å | 1000 | -0.0990 | framework_wins | wave218-p3-kanzi-framework-wins.csv |
| R3_flowmol3_fg_dev (projected n=1000) | reos_n_flags | 1000 | -0.2847 | framework_wins | wave216-p1-r3-per-record.csv |
| R5a_two_moons (CosineAnneal vs baseline) | W2 (d_s) | 10 vs 10 | 1.011 | TIE | wave216-p2-r5a-extended.csv |
| R5b_cifar10rf_matched_NFE50 | FID chunk-paired | 1000 | 2.7004 | REGRESSES | wave195-p2-r-level-power.csv |
| R6_overall_naive | pLDDT (cluster-robust) | 1000 | 0.0707 | UNDERPOWERED | wave216-p4-r6-uplift.csv |

## Notes

- **R2** (`framework_wins`, d_z = -0.099): Kanzi inverse projection RMSD, paired n=1000.
  Bonferroni-significant at alpha=0.00714.
- **R3** (`framework_wins`, d_z = -0.285 projected from 200-record cap at wave87 sweep):
  FlowMol3 functional-group deviation, projected to n=1000. Actual n=200 also bonf-sig.
- **R5a** (`TIE`): 2D two-moons W2 distance, 4 paper-quantity schedulers compared to baseline
  (10 baseline seeds vs 10 scheduler seeds per arm). All 4 verdicts TIE despite d_s in
  [0.558, 2.115] range — driven by small sample size at scheduler-arm level.
- **R5b** (`REGRESSES`, d_z = +2.70): CIFAR-10 RF matched-NFE50 FID, chunk-paired.
  Framework loses by +90 FID at matched NFE. Documented as known regression;
  not in scope for Wave 225.
- **R6** (`UNDERPOWERED`, d_z = +0.071 overall, cluster_p = 0.553): LineageFlow foldability
  pLDDT, 4-cluster robust inference. Overall verdict UNDERPOWERED; per-tier analysis
  shows SUPPORTED on hard (cluster_p = 0.0128) and medium (cluster_p = 0.260, mixed-effects
  SUPPORTED) tiers.

## Snapshot artifact

`verification_outputs/wave225-p0-baseline-snapshot.csv`

## Used by

Wave 225 subsequent phases (P1+) — diff against this snapshot to detect regressions
or improvements.
