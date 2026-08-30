# 2D Rectified-Flow SOTA Experiment — target: `eight_gaussians`

Configuration: 1000 samples/round × 20 rounds × 3 seeds. Same adapter, same weights, same evaluator; only the inference strategy differs between baseline (1-pass, cycle_length=1) and framework (multi-round, cycle_length=20). Total wall-clock: 975.7s.

## Scheduler comparison (paper Theorem 1 metric)

| Method | Mean selection_ratio (last 5 rounds, across seeds) | std | Mean W2 (last 5 rounds, across seeds) | std | Delta selection vs baseline | Delta selection (% of baseline) |
|---|---:|---:|---:|---:|---:|---:|
| baseline (1-pass) | 0.4804 | 0.0005 | 0.6606 | 0.0123 | — | — |
| CosineAnnealScheduler | 0.4808 | 0.0003 | 0.5919 | 0.0110 | +0.0004 | +0.07% |
| CodimensionSheetScheduler | 0.4808 | 0.0003 | 0.5919 | 0.0110 | +0.0004 | +0.07% |
| EvidenceDrivenScheduler | 0.4805 | 0.0006 | 0.6530 | 0.0171 | +0.0001 | +0.02% |
| FreeTrajScheduler | 0.4808 | 0.0003 | 0.5919 | 0.0110 | +0.0004 | +0.07% |

## Best per metric

- **Best W2 (lowest)**: `CosineAnnealScheduler` at `W2 = 0.5919`.
- **Best selection_ratio (highest)**: `CosineAnnealScheduler` at `selection_ratio = 0.4808`.
- **Delta vs baseline**: `delta_W2 = +0.0687` (positive => framework wins), `delta_selection_ratio = +0.0004` (`+0.07%` of baseline).

## Per-round tail averages (mean over last 5 rounds, all seeds)

| Method | Per-seed mean selection_ratio (last 5 rounds) | Per-seed mean W2 (last 5 rounds) | Δ W2 vs baseline | % W2 reduction |
|---|---:|---:|---:|---:|
| baseline (1-pass) | 0.4804 | 0.6606 | — | — |
| CosineAnnealScheduler | 0.4808 | 0.5919 | +0.0687 | +10.40% |
| CodimensionSheetScheduler | 0.4808 | 0.5919 | +0.0687 | +10.40% |
| EvidenceDrivenScheduler | 0.4805 | 0.6530 | +0.0076 | +1.15% |
| FreeTrajScheduler | 0.4808 | 0.5919 | +0.0687 | +10.40% |

## Per-seed raw values

### baseline (1-pass)

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.6478 | 0.4801 |
| 1 | 0.6723 | 0.4801 |
| 2 | 0.6619 | 0.4810 |

### CosineAnnealScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.5802 | 0.4812 |
| 1 | 0.6020 | 0.4805 |
| 2 | 0.5936 | 0.4806 |

### CodimensionSheetScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.5802 | 0.4812 |
| 1 | 0.6020 | 0.4805 |
| 2 | 0.5936 | 0.4806 |

### EvidenceDrivenScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.6334 | 0.4811 |
| 1 | 0.6648 | 0.4805 |
| 2 | 0.6608 | 0.4799 |

### FreeTrajScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.5802 | 0.4812 |
| 1 | 0.6020 | 0.4805 |
| 2 | 0.5936 | 0.4806 |
