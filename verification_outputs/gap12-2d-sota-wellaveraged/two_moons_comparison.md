# 2D Rectified-Flow SOTA Experiment — target: `two_moons`

Configuration: 1000 samples/round × 20 rounds × 1 seeds. Same adapter, same weights, same evaluator; only the inference strategy differs between baseline (1-pass, cycle_length=1) and framework (multi-round, cycle_length=20). Total wall-clock: 511.4s.

## Scheduler comparison (paper Theorem 1 metric)

| Method | Mean selection_ratio (last 5 rounds, across seeds) | std | Mean W2 (last 5 rounds, across seeds) | std | Delta selection vs baseline | Delta selection (% of baseline) |
|---|---:|---:|---:|---:|---:|---:|
| baseline (1-pass) | 0.8336 | 0.0000 | 0.0790 | 0.0000 | — | — |
| CosineAnnealScheduler | 0.8284 | 0.0000 | 0.0866 | 0.0000 | -0.0052 | -0.62% |
| CodimensionSheetScheduler | 0.8292 | 0.0000 | 0.0746 | 0.0000 | -0.0044 | -0.53% |
| EvidenceDrivenScheduler | 0.8309 | 0.0000 | 0.0834 | 0.0000 | -0.0027 | -0.32% |
| FreeTrajScheduler | 0.8296 | 0.0000 | 0.0822 | 0.0000 | -0.0040 | -0.48% |

## Best per metric

- **Best W2 (lowest)**: `CodimensionSheetScheduler` at `W2 = 0.0746`.
- **Best selection_ratio (highest)**: `EvidenceDrivenScheduler` at `selection_ratio = 0.8309`.
- **Delta vs baseline**: `delta_W2 = +0.0044` (positive => framework wins), `delta_selection_ratio = -0.0027` (`-0.32%` of baseline).

## Per-round tail averages (mean over last 5 rounds, all seeds)

| Method | Per-seed mean selection_ratio (last 5 rounds) | Per-seed mean W2 (last 5 rounds) | Δ W2 vs baseline | % W2 reduction |
|---|---:|---:|---:|---:|
| baseline (1-pass) | 0.8336 | 0.0790 | — | — |
| CosineAnnealScheduler | 0.8284 | 0.0866 | -0.0076 | -9.68% |
| CodimensionSheetScheduler | 0.8292 | 0.0746 | +0.0044 | +5.60% |
| EvidenceDrivenScheduler | 0.8309 | 0.0834 | -0.0044 | -5.60% |
| FreeTrajScheduler | 0.8296 | 0.0822 | -0.0032 | -4.01% |

## Per-seed raw values

### baseline (1-pass)

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.0790 | 0.8336 |

### CosineAnnealScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.0866 | 0.8284 |

### CodimensionSheetScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.0746 | 0.8292 |

### EvidenceDrivenScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.0834 | 0.8309 |

### FreeTrajScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.0822 | 0.8296 |
