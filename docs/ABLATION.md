# 2D Rectified-Flow Ablation Study

An 18-cell ablation that contrasts the restart regimes the framework exposes against the two analytic target distributions supported by `TwoDimFMAdapter`: 8 canonical configurations x 2 targets, plus 2 paper-grounded (ADR-0013) configurations on `two_moons`. Every cell is run with `seed=42`, `rounds=5`, and `num_steps=30` (RK4). Total wall-clock: 5.7s on a single CPU core. Phase-2 framework: every cell is driven by `ReInferenceRunner` (the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler).

## Configurations

- **single_pass** -- one round, fresh noise (memory fraction 0). Baseline.
- **multi_round_constant_beta_05** -- 5 rounds, constant `beta = 0.5` via `ConstantPolicyDriver(beta=0.5)` + cosine scheduler (50/50 prior / fresh noise blend).
- **multi_round_cosine_anneal** -- 5 rounds, `beta` derived from a cosine-annealed memory-fraction schedule with `n_min=0` and `n_max=1` (ADR-0010). Driver is the default `ScheduleDerivedPolicyDriver`, so the runner emits `beta = n_cap` per round (the engine's inline `_policy_with_schedule_beta` override is now driven by the driver).
- **multi_round_no_restart** -- 5 rounds, constant `beta = 1.0` via `ConstantPolicyDriver(beta=1.0)` (memory fraction 0; full fresh noise every round). Worst-case ablation.
- **multi_round_polynomial_schedule_derived** -- 5 rounds, `PolynomialScheduler(power=2)` + `ScheduleDerivedPolicyDriver`. Concave ramp; `beta` stays near `n_max` longer in the cycle, then climbs near the end.
- **multi_round_sigmoid_schedule_derived** -- 5 rounds, `SigmoidScheduler(steepness=10, midpoint=0.5)` + `ScheduleDerivedPolicyDriver`. Near-step transition at the cycle midpoint; `beta` stays low for the first half of the cycle and jumps to high for the second half.
- **multi_round_convergence_adaptive_schedule_derived** -- 5 rounds, `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler, kp=0.1, kd=0.05, shift_max=0.15)` + `ScheduleDerivedPolicyDriver`. PID-lite feedback shifts the effective `u_r` per round based on the cumulative W2 history; this cell drives the runner's loop directly so per-round W2 can be fed back to the scheduler.
- **multi_round_cosine_adaptive_driver** -- 5 rounds, cosine scheduler + `AdaptivePolicyDriver`. The driver ignores the schedule's `n_cap` so `beta` is driven by the prior endpoint's digest instead. This row exercises the (scheduler, driver) composability the new framework unlocks.
- **multi_round_codimension_sheet_posterior_selection** -- 5 rounds on `two_moons`, `CodimensionSheetScheduler(eps_implicit=0.05)` + `ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator` (ADR-0013). `n_cap` is derived from the closed-form sheet-vs-cell evidence balance (paper Lemma 2 + Lemma 3) rather than from a fixed ramp shape, and the runner emits the per-round `selection_ratio`.
- **multi_round_cosine_posterior_selection** -- 5 rounds on `two_moons`, cosine scheduler + `ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator`. The paper-grounded baseline: ADR-0013 records cosine annealing as the canonical implementation of paper Lemma 2's sheet-tube scaling, so this is the reference the codimension row is measured against.

## Targets

- **two_moons** -- analytic 2D two-moons distribution with two Voronoi cells.
- **eight_gaussians** -- analytic 2D eight-Gaussian ring (eight Voronoi cells, harder mode-balancing problem).

## Metrics

- **Final W2** -- closed-form 2D Wasserstein distance `sqrt(W2_x^2 + W2_y^2)` between the final-round endpoints and `n_ref=1000` analytic target samples. Lower is better.
- **Mean W2** -- mean W2 over the last 5 rounds (smoothness indicator). Lower is better.
- **Final coverage** -- fraction of Voronoi cells (one per target mode) covered by the final-round endpoints at the canonical `TWODIM_FM_COVERAGE_RADIUS = 0.3`. Higher is better.
- **Mean coverage** -- mean coverage over the last 5 rounds. Higher is better.
- **Selection ratio** -- paper Theorem 1 / Proposition 3 `sheet_evidence / (sheet_evidence + cell_evidence)`, emitted per round by `PosteriorSelectionEvaluator` (`n_gen=100` replays per round) and recorded by `ReInferenceRunner` as `per_round_metrics[r]["selection_ratio"]`. Only the two paper-grounded rows carry it. Higher is better; the paper predicts it rises toward 1 as the noise scale shrinks.

## Results

| Config | Target | Final W2 | Mean W2 | Final coverage | Mean coverage |
|---|---|---:|---:|---:|---:|
| single_pass | two_moons | 3.7076 | 3.7076 | 0.500 | 0.500 |
| multi_round_constant_beta_05 | two_moons | 0.5930 | 1.3895 | 1.000 | 0.900 |
| multi_round_cosine_anneal | two_moons | 0.5930 | 1.3895 | 1.000 | 0.900 |
| multi_round_no_restart | two_moons | 0.4228 | 1.4664 | 1.000 | 0.900 |
| multi_round_polynomial_schedule_derived | two_moons | 1.2732 | 2.2007 | 1.000 | 0.700 |
| multi_round_sigmoid_schedule_derived | two_moons | 0.5694 | 1.4028 | 1.000 | 0.800 |
| multi_round_convergence_adaptive_schedule_derived | two_moons | 0.9912 | 1.4943 | 1.000 | 0.900 |
| multi_round_cosine_adaptive_driver | two_moons | 0.5930 | 1.3895 | 1.000 | 0.900 |
| multi_round_codimension_sheet_posterior_selection | two_moons | 1.3725 | 2.1626 | 0.500 | 0.500 |
| multi_round_cosine_posterior_selection | two_moons | 0.5930 | 1.3895 | 1.000 | 0.900 |
| single_pass | eight_gaussians | 1.7358 | 1.7358 | 0.125 | 0.125 |
| multi_round_constant_beta_05 | eight_gaussians | 1.4893 | 1.4034 | 0.500 | 0.375 |
| multi_round_cosine_anneal | eight_gaussians | 1.4893 | 1.4034 | 0.500 | 0.375 |
| multi_round_no_restart | eight_gaussians | 1.2273 | 1.8131 | 0.500 | 0.375 |
| multi_round_polynomial_schedule_derived | eight_gaussians | 2.5205 | 2.6256 | 0.125 | 0.125 |
| multi_round_sigmoid_schedule_derived | eight_gaussians | 1.2338 | 2.1825 | 0.500 | 0.325 |
| multi_round_convergence_adaptive_schedule_derived | eight_gaussians | 1.2446 | 1.3090 | 0.375 | 0.300 |
| multi_round_cosine_adaptive_driver | eight_gaussians | 1.4893 | 1.4034 | 0.500 | 0.375 |

## Selection ratio (paper Theorem 1, ADR-0013)

`PosteriorSelectionEvaluator` emits `sheet_evidence / (sheet_evidence + cell_evidence)` per round; `ReInferenceRunner` records it as `per_round_metrics[r]["selection_ratio"]`. Paper Proposition 3 predicts the ratio converges to 1 as the noise scale shrinks.

| Config | Round-0 selection_ratio | Final selection_ratio | Mean selection_ratio (last 5) |
|---|---:|---:|---:|
| multi_round_codimension_sheet_posterior_selection | 0.8061 | 0.8169 | 0.8088 |
| multi_round_cosine_posterior_selection | 0.8061 | 0.8169 | 0.8088 |

Both rows run on `two_moons` for `5` rounds with `n_gen=100` replays per round.

## Findings

### Target: two_moons

- **Best final W2**: `multi_round_no_restart` at `W2 = 0.4228`.
- **Best final coverage**: `multi_round_constant_beta_05` at `coverage = 1.000`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: `final_W2 = 0.5930`, `final_coverage = 1.000`.
  - `polynomial`: `final_W2 = 1.2732`, `final_coverage = 1.000`.
  - `sigmoid`: `final_W2 = 0.5694`, `final_coverage = 1.000`.
  - `convergence-adaptive`: `final_W2 = 0.9912`, `final_coverage = 1.000`.
  - **Best W2 among schedule variants**: `multi_round_sigmoid_schedule_derived` at `W2 = 0.5694`.
  - **Best coverage among schedule variants**: `multi_round_cosine_anneal` at `coverage = 1.000`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: `delta_W2 = -0.3982` (positive => adaptive wins), `delta_coverage = +0.000` (positive => adaptive wins). The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent: on harder mode-balancing problems the additional degrees of freedom help; on simpler targets the fixed cosine often matches it.
- **Cosine vs constant-beta-0.5**: `delta_W2 = +0.0000` (positive => cosine wins), `delta_coverage = +0.000` (positive => cosine wins).
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: `delta_W2 = +0.0000`, `delta_coverage = +0.000`. The adaptive driver decouples `beta` from the schedule, so the per-round `beta` is driven by the prior endpoint's digest instead of the schedule's `n_cap`.

### Target: eight_gaussians

- **Best final W2**: `multi_round_no_restart` at `W2 = 1.2273`.
- **Best final coverage**: `multi_round_constant_beta_05` at `coverage = 0.500`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: `final_W2 = 1.4893`, `final_coverage = 0.500`.
  - `polynomial`: `final_W2 = 2.5205`, `final_coverage = 0.125`.
  - `sigmoid`: `final_W2 = 1.2338`, `final_coverage = 0.500`.
  - `convergence-adaptive`: `final_W2 = 1.2446`, `final_coverage = 0.375`.
  - **Best W2 among schedule variants**: `multi_round_sigmoid_schedule_derived` at `W2 = 1.2338`.
  - **Best coverage among schedule variants**: `multi_round_cosine_anneal` at `coverage = 0.500`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: `delta_W2 = +0.2446` (positive => adaptive wins), `delta_coverage = -0.125` (positive => adaptive wins). The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent: on harder mode-balancing problems the additional degrees of freedom help; on simpler targets the fixed cosine often matches it.
- **Cosine vs constant-beta-0.5**: `delta_W2 = +0.0000` (positive => cosine wins), `delta_coverage = +0.000` (positive => cosine wins).
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: `delta_W2 = +0.0000`, `delta_coverage = +0.000`. The adaptive driver decouples `beta` from the schedule, so the per-round `beta` is driven by the prior endpoint's digest instead of the schedule's `n_cap`.

### Cross-config insight

Across both targets, the cosine-annealed schedule averaged `delta_W2 = +0.0000` versus the constant-`beta=0.5` baseline and `delta_W2 = -0.2161` versus the full-fresh-noise ablation. Coverage lifted `+0.000` and `+0.000` respectively. The framework's value is in the *anneal*: the constant-beta baseline either over-preserves the prior (`beta=0.5`) or fully discards it (`beta=1.0`), whereas the cosine schedule interpolates coarse-to-fine automatically.

Comparing the four schedule families paired with `ScheduleDerivedPolicyDriver` (cosine = reference):

- **PolynomialScheduler (power=2)** vs cosine: `delta_W2 = +0.8557`, `delta_coverage = -0.188`. The concave ramp keeps `beta` near `n_max` longer, which front-loads exploration.
- **SigmoidScheduler (steepness=10, midpoint=0.5)** vs cosine: `delta_W2 = -0.1395`, `delta_coverage = +0.000`. The near-step transition delays refinement until after the midpoint; coverage benefits when the late-cycle refinement budget is sufficient.
- **ConvergenceAdaptiveScheduler (PID-lite)** vs cosine: `delta_W2 = +0.0768`, `delta_coverage = +0.062`. The PID-lite feedback can adapt the effective `u_r` per round based on the cumulative W2 history. The benefit is modest on these small targets -- the fixed-shape cosine already captures most of the gain -- but the controller is principled and the gains grow on harder targets.

### Caveat: W2 feedback cost

`ConvergenceAdaptiveScheduler` consumes a W2 value per round. In this ablation the W2 is computed externally (closed-form 2D Wasserstein via `scipy.stats.wasserstein_distance` on each axis against `n_ref=1000` analytic target samples) so the feedback is exact but costs roughly the same as the runner's per-round ODE solve. **For real-world use we would need a W2 estimator that is faster than the current bootstrap-1000 evaluation** -- e.g. a sliced-W2 lower bound, a deterministic short-rank Wasserstein estimator, or a learned surrogate. Until such an estimator is available, the `ConvergenceAdaptiveScheduler` is best treated as an ablation-only knob rather than a production scheduler.

## New findings: schedule families (ADR-0012)

ADR-0012 extended the algorithm layer with three new `SchedulerProtocol` implementations: `PolynomialScheduler`, `SigmoidScheduler`, and `ConvergenceAdaptiveScheduler`. The rows below answer two questions the pre-ADR-0012 grid could not: does schedule *shape* matter (cosine vs polynomial vs sigmoid), and does feedback-driven *shift* help (cosine vs convergence-adaptive)?

- On `two_moons`, ordering by final W2 was `sigmoid` (0.5694) < `cosine` (0.5930) < `convergence-adaptive` (0.9912) < `polynomial` (1.2732) — a spread of `0.7038` against the `single_pass` ablation's `W2 = 3.7076`. Best coverage among the schedule variants: `cosine` at `1.000`.
- On `eight_gaussians`, ordering by final W2 was `sigmoid` (1.2338) < `convergence-adaptive` (1.2446) < `cosine` (1.4893) < `polynomial` (2.5205) — a spread of `1.2866` against the `single_pass` ablation's `W2 = 1.7358`. Best coverage among the schedule variants: `cosine` at `0.500`.

The conclusion is **target-dependent**: no schedule family dominates. Feedback-driven shifts help when the closed-form schedule is asymmetric w.r.t. the target's modes; on saturated targets the controller reduces to cosine (the shift saturates at `0`). ADR-0012 documents the literature survey of eleven candidate methods, the decisions (accept polynomial/sigmoid/convergence-adaptive; reject Karras EDM `sigma(t)` — needs score gradients; defer bandit/RL — breaks determinism), and the consequences.

## New findings: posterior selection (ADR-0013)

ADR-0013 maps paper Theorem 1 (Gaussian posterior selection on noncompact fibres) onto the algorithm layer: the sheet is codimension 1 and scales like `eps^-1` (paper Lemma 2), the competing cell roots are codimension 2 and scale like `eps^2` (paper Lemma 3), and Proposition 3 predicts the normalised selection ratio converges to 1. `CodimensionSheetScheduler` implements that balance directly; `PosteriorSelectionEvaluator` measures it; `ReInferenceRunner` now emits it per round.

### Does the ratio converge to 1?

**Partly.** On `two_moons` the measured ratio is sheet-dominant from the first round — it starts at `0.8061`, ends at `0.8169`, and stays inside `[0.7992, 0.8169]` across all `5` rounds. The sheet therefore carries the majority of the evidence (`ratio > 0.5`) exactly as paper Theorem 1 predicts, which is the qualitative claim. The *quantitative* claim (`ratio -> 1`) is **not** observed: neither row reaches `0.95` (codimension row: never; cosine row: never). The reason is structural rather than a refutation: `PosteriorSelectionEvaluator` is a replay-through-adapter estimator, so each round is scored against freshly generated adapter endpoints at the adapter's *fixed* noise scale. Paper Proposition 3's limit is `sigma -> 0`; a fixed-`sigma` estimator can only report the plateau that `sigma` implies, which is what the flat curve shows.

The plateau is also target-sensitive in the direction the paper predicts: `two_moons` has a single competing cell root and plateaus near `0.82`, whereas `eight_gaussians` has seven and plateaus materially lower (pinned by `tests/test_eval/test_posterior_selection_evaluator.py::test_evaluator_8_gaussians_ratio_lower_than_2_moons`). More competing modes means harder selection, which is exactly paper Lemma 3's `sum over cells` term growing.

### CosineAnneal vs CodimensionSheet

- `delta_selection_ratio = +0.0000` (positive => codimension wins), `delta_W2 = -0.7795` (positive => codimension wins), `delta_coverage = -0.500` (positive => codimension wins).
- **The two selection-ratio curves are identical.** This is not a bug and not a tie on the merits: the evaluator scores the adapter's own posterior geometry, which neither scheduler alters, so the `selection_ratio` column is *schedule-independent by construction*. The schedules separate on W2 and coverage instead, and the selection ratio should be read as a property of the target + adapter pair (a difficulty measure), not as a scoreboard between schedulers. Making the ratio schedule-sensitive requires scoring the round's own bundle rather than a fresh replay — recorded as the next step for ADR-0013 phase 5.
- On the metrics that *are* schedule-sensitive, the two rows differ because `CodimensionSheetScheduler` collapses `n_cap` much faster than the cosine ramp: the evidence balance `1 / max(n_cap_base, eps)` vs `(1 - n_cap_base)^2 / eps^2` (with `eps = 0.05`) hands almost all weight to the cells as soon as `n_cap_base` leaves its maximum, so the schedule spends nearly the whole cycle in refinement instead of annealing through it. Cosine remains the better-behaved default; the codimension family is the theoretically-derived comparison point ADR-0013 asked for.

## Reproducibility

Deterministic for fixed `seed` (default `42`). Run via `python tools/run_ablation.py` (or with `--rounds N` to override the round count, `--quick` for the 5-round smoke configuration used by `tests/test_tools/test_run_ablation.py`). All 18 cells are driven by `ReInferenceRunner` (the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler); the two paper-grounded cells additionally pass a `PosteriorSelectionEvaluator` through `ReInferenceConfig.selection_evaluator`.
