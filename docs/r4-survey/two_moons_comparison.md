# 2D Rectified-Flow SOTA Experiment — target: `two_moons`

Configuration: 1000 samples/round × 20 rounds × 3 seeds. Same adapter, same weights, same evaluator; only the inference strategy differs between baseline (1-pass, cycle_length=1) and framework (multi-round, cycle_length=20). Total wall-clock: 990.2s.

## Scheduler comparison (paper Theorem 1 metric)

| Method | Mean selection_ratio (last 5 rounds, across seeds) | std | Mean W2 (last 5 rounds, across seeds) | std | Delta selection vs baseline | Delta selection (% of baseline) |
|---|---:|---:|---:|---:|---:|---:|
| baseline (1-pass) | 0.8143 | 0.0003 | 0.5029 | 0.0098 | — | — |
| CosineAnnealScheduler | 0.8091 | 0.0001 | 0.4663 | 0.0078 | -0.0052 | -0.64% |
| CodimensionSheetScheduler | 0.8091 | 0.0001 | 0.4663 | 0.0078 | -0.0052 | -0.64% |
| EvidenceDrivenScheduler | 0.8099 | 0.0001 | 0.5031 | 0.0049 | -0.0044 | -0.54% |
| FreeTrajScheduler | 0.8091 | 0.0001 | 0.4663 | 0.0078 | -0.0052 | -0.64% |

## Best per metric

- **Best W2 (lowest)**: `CosineAnnealScheduler` at `W2 = 0.4663`.
- **Best selection_ratio (highest)**: `EvidenceDrivenScheduler` at `selection_ratio = 0.8099`.
- **Delta vs baseline**: `delta_W2 = +0.0366` (positive => framework wins), `delta_selection_ratio = -0.0044` (`-0.54%` of baseline).

## Per-round tail averages (mean over last 5 rounds, all seeds)

| Method | Per-seed mean selection_ratio (last 5 rounds) | Per-seed mean W2 (last 5 rounds) | Δ W2 vs baseline | % W2 reduction |
|---|---:|---:|---:|---:|
| baseline (1-pass) | 0.8143 | 0.5029 | — | — |
| CosineAnnealScheduler | 0.8091 | 0.4663 | +0.0366 | +7.28% |
| CodimensionSheetScheduler | 0.8091 | 0.4663 | +0.0366 | +7.28% |
| EvidenceDrivenScheduler | 0.8099 | 0.5031 | -0.0001 | -0.03% |
| FreeTrajScheduler | 0.8091 | 0.4663 | +0.0366 | +7.28% |

## Per-seed raw values

### baseline (1-pass)

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.5133 | 0.8141 |
| 1 | 0.5018 | 0.8142 |
| 2 | 0.4938 | 0.8146 |

### CosineAnnealScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.4753 | 0.8091 |
| 1 | 0.4631 | 0.8089 |
| 2 | 0.4606 | 0.8092 |

### CodimensionSheetScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.4753 | 0.8091 |
| 1 | 0.4631 | 0.8089 |
| 2 | 0.4606 | 0.8092 |

### EvidenceDrivenScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.5085 | 0.8098 |
| 1 | 0.5018 | 0.8099 |
| 2 | 0.4989 | 0.8100 |

### FreeTrajScheduler

| Seed | Mean W2 (last 5) | Mean selection_ratio (last 5) |
|---:|---:|---:|
| 0 | 0.4753 | 0.8091 |
| 1 | 0.4631 | 0.8089 |
| 2 | 0.4606 | 0.8092 |
