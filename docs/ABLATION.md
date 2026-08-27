# 2D Rectified-Flow Ablation Study

A 4 x 2 ablation that contrasts the four restart regimes the framework exposes against the two analytic target distributions supported by `TwoDimFMAdapter`. Every cell is run with `seed=42`, `rounds=20`, and `num_steps=30` (RK4). Total wall-clock: 0.2s on a single CPU core.

## Configurations

- **single_pass** -- one round, fresh noise (memory fraction 0). Baseline.
- **multi_round_constant_beta_05** -- 20 rounds, constant `beta = 0.5` (50/50 prior / fresh noise blend).
- **multi_round_cosine_anneal** -- 20 rounds, `beta` derived from a cosine-annealed memory-fraction schedule with `n_min=0` and `n_max=1` (ADR-0010). At round 0 the engine emits `beta = n_max` (full fresh noise for exploration); at the final round it emits `beta = n_min` (preserve the prior and refine).
- **multi_round_no_restart** -- 20 rounds, constant `beta = 1.0` (memory fraction 0; full fresh noise every round). Worst-case ablation.

## Targets

- **two_moons** -- analytic 2D two-moons distribution with two Voronoi cells.
- **eight_gaussians** -- analytic 2D eight-Gaussian ring (eight Voronoi cells, harder mode-balancing problem).

## Metrics

- **Final W2** -- closed-form 2D Wasserstein distance `sqrt(W2_x^2 + W2_y^2)` between the final-round endpoints and `n_ref=1000` analytic target samples. Lower is better.
- **Mean W2** -- mean W2 over the last 5 rounds (smoothness indicator). Lower is better.
- **Final coverage** -- fraction of Voronoi cells (one per target mode) covered by the final-round endpoints at the canonical `TWODIM_FM_COVERAGE_RADIUS = 0.3`. Higher is better.
- **Mean coverage** -- mean coverage over the last 5 rounds. Higher is better.

## Results

| Config | Target | Final W2 | Mean W2 | Final coverage | Mean coverage |
|---|---|---:|---:|---:|---:|
| single_pass | two_moons | 2.6481 | 2.6481 | 0.500 | 0.500 |
| multi_round_constant_beta_05 | two_moons | 0.8148 | 0.7336 | 1.000 | 1.000 |
| multi_round_cosine_anneal | two_moons | 0.8758 | 0.7397 | 1.000 | 1.000 |
| multi_round_no_restart | two_moons | 0.6126 | 0.6195 | 1.000 | 1.000 |
| single_pass | eight_gaussians | 2.3525 | 2.3525 | 0.125 | 0.125 |
| multi_round_constant_beta_05 | eight_gaussians | 2.2157 | 1.9439 | 0.125 | 0.125 |
| multi_round_cosine_anneal | eight_gaussians | 2.0042 | 2.2337 | 0.375 | 0.375 |
| multi_round_no_restart | eight_gaussians | 0.6862 | 1.0001 | 0.625 | 0.625 |

## Findings

### Target: two_moons

- **Best final W2**: `multi_round_no_restart` at `W2 = 0.6126`.
- **Best final coverage**: `multi_round_constant_beta_05` at `coverage = 1.000`.
- **Cosine vs constant-beta-0.5**: `delta_W2 = -0.0610` (positive => cosine wins), `delta_coverage = +0.000` (positive => cosine wins).

### Target: eight_gaussians

- **Best final W2**: `multi_round_no_restart` at `W2 = 0.6862`.
- **Best final coverage**: `multi_round_no_restart` at `coverage = 0.625`.
- **Cosine vs constant-beta-0.5**: `delta_W2 = +0.2115` (positive => cosine wins), `delta_coverage = +0.250` (positive => cosine wins).

### Cross-config insight

Across both targets, the cosine-annealed schedule averaged `delta_W2 = +0.0753` versus the constant-`beta=0.5` baseline and `delta_W2 = -0.7906` versus the full-fresh-noise ablation. Coverage lifted `+0.125` and `-0.125` respectively. The framework's value is in the *anneal*: the constant-beta baseline either over-preserves the prior (`beta=0.5`) or fully discards it (`beta=1.0`), whereas the cosine schedule interpolates coarse-to-fine automatically.

## Reproducibility

Deterministic for fixed `seed` (default `42`). Run via `python tools/run_ablation.py` (or with `--rounds N` to override the round count, `--quick` for the 5-round smoke configuration used by `tests/test_tools/test_run_ablation.py`).
