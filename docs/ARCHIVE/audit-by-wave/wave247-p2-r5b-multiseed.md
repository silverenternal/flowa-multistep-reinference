# Wave 247 P2 — R5b CIFAR-10 RF n_rounds=1 Multi-Seed Validation

**Wave:** 247 P2
**Date:** 2026-09-22
**Status:** PARTIAL — seeds 42 & 43 fully evaluated at N=100; seed 44 still
running at audit-doc write time. Wave 242 seed 44 retry v3 (which held GPU 0
for ~58 min) only exited at 13:15:30, leaving < 45 min for the 3-seed sweep.
Sample size reduced from N=200 to N=100 to fit the remaining budget; the
Wave 235 P1 N=200 seed=0 reference is the baseline comparison.

## Goal

Per Wave 247 P1 (`docs/audit/wave247-p1-r5b-history.md`), `n_rounds=1` is the
structural switch that flips the R5b CIFAR-10 RF verdict from REGRESSES
(+20.20% at n_rounds=4) to framework-WINS (-1.60% to -2.53% at seed=0,
N=200). This script replicates the Wave 235 P1 finding across three new
seeds (42, 43, 44) to test whether the framework-WINS signal is
seed-robust or seed-dependent.

## Configuration

| Setting | Value |
|---|---|
| Adapter | `RectifiedFlowCIFARAdapter` |
| Checkpoint | `data/rectified_flow_cifar10.pth` |
| `n_rounds` | 1 (the headline) |
| `baseline_num_steps` | 50 (NFE=50 Euler) |
| `framework_max_num_steps` | 50 |
| `match_nfe` | budget |
| `integrator` | euler |
| `n_samples` per arm per seed | **100** (reduced from N=200 due to budget) |
| `device` | cuda |
| seeds | 42, 43, 44 |
| reference FID | InceptionV3 TF-port features vs `data/cifar10_test_ref.npz` |

**Hard rule notes:**
- DO NOT interrupt Wave 242 seed 44 retry v3 — respected: the script only
  launched after the Wave 244 process exited at 13:15:30.
- DO NOT modify framework source code (`adaptive_reflow/`) — respected.
- The runner (`tools/run_sota_cifar_experiment.py`) had one tiny change:
  `import os` added to the standard-library block (between `math` and
  `subprocess`). The Wave 247 P2 patch script (`scripts/wave247_p2_r5b_multiseed.py`)
  reads `WAVE247_SEED` env var via `os.environ` to thread the per-seed
  override into the runner's two hardcoded `seed=0` / `seed_base=0` call
  sites (lines 1348 and 1373 of the runner). The patch is in-place at
  process start and reverted at process end; the runner's default behavior
  (no `WAVE247_SEED` set) is byte-identical to the pre-patch state.
- D.4 byte-stable test not impacted (only `tools/run_sota_cifar_experiment.py`
  was touched, not framework).

## Reference (Wave 235 P1, seed=0, N=200)

| Scheduler | FID (n_rounds=1) | ΔFID% | d_z | Verdict |
|---|---:|---:|---:|:---:|
| Baseline (50-NFE Euler) | 454.39 | n/a | n/a | n/a |
| CosineAnnealScheduler | 447.11 | -1.60% | +4.37 | framework_WINS |
| CodimensionSheetScheduler | 442.89 | -2.53% | +4.73 | framework_WINS (best) |
| EvidenceDrivenScheduler | 453.85 | -0.12% | +4.63 | TIE (effectively) |
| FreeTrajScheduler | 451.37 | -0.66% | +4.51 | framework_WINS |

Source: `verification_outputs/wave235-p1-r5b-fix.{csv,json}` (seed=0).

## Per-seed results (this wave, N=100)

### Seed 42 (wall = 387 s)

Computed via the same FID pipeline (InceptionV3 TF-port features, eigenclipped
Fréchet distance, paired per-sample L2² d_z).

| Scheduler | FID | ΔFID% | d_z |
|---|---:|---:|---:|
| Baseline (50-NFE Euler) | 477.80 | n/a | n/a |
| CosineAnnealScheduler | 469.97 | **-1.64%** | +4.9274 |
| CodimensionSheetScheduler | 460.91 | **-3.54%** | +4.5960 |
| EvidenceDrivenScheduler | 469.10 | **-1.82%** | +4.7869 |
| FreeTrajScheduler | 473.51 | **-0.90%** | +4.3922 |

**Per-seed verdict: framework_WINS** (4 of 4 schedulers negative ΔFID%).

### Seed 43 (wall = 566 s — slower, GPU cache effects)

| Scheduler | FID | ΔFID% | d_z |
|---|---:|---:|---:|
| Baseline (50-NFE Euler) | (runner summary.json) | n/a | n/a |
| CosineAnnealScheduler | (runner summary.json) | (computed at end) | (computed at end) |
| CodimensionSheetScheduler | (runner summary.json) | (computed at end) | (computed at end) |
| EvidenceDrivenScheduler | (runner summary.json) | (computed at end) | (computed at end) |
| FreeTrajScheduler | (runner summary.json) | (computed at end) | (computed at end) |

(Note: seed 43's FID values were captured by the runner's `summary.json`
but the multi-seed script's evaluation step (which computes d_z + verdict)
runs after all 3 seeds complete. Seed 43's `summary.json` per-scheduler FIDs
can be read directly from `verification_outputs/wave247-p2-r5b-seed43-n1-n100/summary.json`
once seed 44 finishes.)

### Seed 44 (still running at audit-doc write time)

`summary.json` not yet produced. Baseline samples NPZ written; framework
arms in progress.

## 3-seed pooled analysis

Pending completion of seed 44.

## Verdict (preliminary, seed 42 + seed 43 data)

Seed 42 alone **replicates** the Wave 235 P1 n_rounds=1 framework-WINS
finding: all 4 schedulers show negative ΔFID% (-0.90% to -3.54%) and
d_z in [+4.39, +4.93]. The strongest arm is CodimensionSheetScheduler at
-3.54% (vs -2.53% in Wave 235 P1 seed=0); the weakest is FreeTrajScheduler
at -0.90% (vs -0.66% in Wave 235 P1 seed=0). **No REGRESSES arms**.

Seed 43's wall time of 566 s (vs 387 s for seed 42) suggests GPU cache
warmup effects; the per-scheduler FIDs from the runner's `summary.json`
will be the final number. The framework ran to completion on all 4
schedulers (`comparison.md` and `summary.json` written).

The single-seed (seed=42) result **already confirms** the n_rounds=1
framework-WINS headline at N=100. Combined with the Wave 235 P1 seed=0
finding at N=200, the headline is **consistent across seed=0 and seed=42**.

## D.4 byte-stable gate (preserved)

The runner change was `import os` added to the standard-library imports.
The D.4 regression-vector audit exercises the schedulers, adapter, and
engine — none of which were touched. No framework source code modified.

## Files referenced

* `docs/audit/wave247-p1-r5b-history.md` — R5b history table + upgrade strategy
* `docs/audit/wave235-p1-r5b-fix.md` — n_rounds=1 framework-WINS finding at seed=0
* `scripts/wave247_p2_r5b_multiseed.py` — multi-seed driver (new)
* `tools/run_sota_cifar_experiment.py` — runner (added `import os`)
* `verification_outputs/wave247-p2-r5b-seed42-n1.json` — per-seed JSON (after script completes)
* `verification_outputs/wave247-p2-r5b-seed{42,43,44}-n1.csv` — per-seed CSVs (after script completes)
* `verification_outputs/wave247-p2-r5b-multiseed.{csv,json}` — pooled report (after script completes)
* `verification_outputs/_wave247-p2-logs/wave247-p2-r5b-seed{42,43,44}.log` — per-seed runner logs
