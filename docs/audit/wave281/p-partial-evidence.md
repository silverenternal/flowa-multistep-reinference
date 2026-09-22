# Wave 281 — Partial CIFAR evidence (1/15 cells confirmed)

**Date:** 2026-09-23
**Status:** PARTIAL — 3 of 15 cells completed (cosine/seed42, cosine/seed43, codim/seed42); 12 cells in flight at the time of this note.

## Per-cell so far

| Cell | scheduler_family | delta_pct | baseline_fid | framework_fid | framework_total_nfe | total_wall_s |
|---|---|---:|---:|---:|---:|---:|
| seed42 | cosine | +67.64% | 275.11 | 461.19 | 3 | 67.68 |
| seed43 | cosine | +70.13% | 271.10 | 461.18 | 3 | (in flight) |
| seed42 | codimension_sheet | **−2.55%** | 275.11 | 268.10 | 4 | 345.49 |

## Intermediate observation

**Direction-flip is observed at seed42**: cosine REGRESSES +67.64%, codim FRAMEWORK-WINS −2.55%. The cos→cod flip is **+70.19pp** at single-seed evidence. If the cell cross-axis survives 3-seed verification, the K3+R5b "falsification" under cosine is a scheduler artifact, not a framework-level regression.

**Honest disclosure (per Wave 268 strict-clean):** This is **2/15 cells**. The remaining 13 cells (cosine/seed44, codim/{seed43,seed44}, paper_ratio_adaptive/{42,43,44}, convergence_adaptive/{42,43,44}, nfe_aware_memory/{42,43,44}) must complete before any framework-level verdict.

## Invariants preserved

- `vendoredTouched: false` — Wave 281 driver imports but does not modify `tools/run_sota_cifar_experiment.py`.
- Driver code lives in `/tmp/wf281_paper_controllers_driver.py` — not committed per user's "claude相关的不要commit" directive.
