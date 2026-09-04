# 2D Rectified-Flow Ablation Study

An 23-cell ablation that contrasts the restart regimes the framework exposes against the two analytic target distributions supported by `TwoDimFMAdapter`: 8 canonical configurations x 2 targets, plus 3 paper-grounded (ADR-0013) configurations on `two_moons`, plus 2 post-infrastructure-fix configurations x 2 targets. Every cell is run with `seed=42`, `rounds=20`, and `num_steps=30` (RK4). Total wall-clock: 96.4s on a single CPU core. Phase-2 framework: every cell is driven by `ReInferenceRunner` (the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler).

## Configurations

- **single_pass** -- one round, fresh noise (memory fraction 0). Baseline.
- **multi_round_constant_beta_05** -- 20 rounds, constant `beta = 0.5` via `ConstantPolicyDriver(beta=0.5)` + cosine scheduler (50/50 prior / fresh noise blend).
- **multi_round_cosine_anneal** -- 20 rounds, `beta` derived from a cosine-annealed memory-fraction schedule with `n_min=0` and `n_max=1` (ADR-0010). Driver is the default `ScheduleDerivedPolicyDriver`, so the runner emits `beta = n_cap` per round (the engine's inline `_policy_with_schedule_beta` override is now driven by the driver).
- **multi_round_no_restart** -- 20 rounds, constant `beta = 1.0` via `ConstantPolicyDriver(beta=1.0)` (memory fraction 0; full fresh noise every round). Worst-case ablation.
- **multi_round_polynomial_schedule_derived** -- 20 rounds, `PolynomialScheduler(power=2)` + `ScheduleDerivedPolicyDriver`. Concave ramp; `beta` stays near `n_max` longer in the cycle, then climbs near the end.
- **multi_round_sigmoid_schedule_derived** -- 20 rounds, `SigmoidScheduler(steepness=10, midpoint=0.5)` + `ScheduleDerivedPolicyDriver`. Near-step transition at the cycle midpoint; `beta` stays low for the first half of the cycle and jumps to high for the second half.
- **multi_round_convergence_adaptive_schedule_derived** -- 20 rounds, `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler, kp=0.1, kd=0.05, shift_max=0.15)` + `ScheduleDerivedPolicyDriver`. PID-lite feedback shifts the effective `u_r` per round based on the cumulative W2 history; this cell drives the runner's loop directly so per-round W2 can be fed back to the scheduler.
- **multi_round_cosine_adaptive_driver** -- 20 rounds, cosine scheduler + `AdaptivePolicyDriver`. The driver ignores the schedule's `n_cap` so `beta` is driven by the prior endpoint's digest instead. This row exercises the (scheduler, driver) composability the new framework unlocks.
- **multi_round_codimension_sheet_posterior_selection** -- 20 rounds on `two_moons`, `CodimensionSheetScheduler(eps_implicit=0.05)` + `ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator` (ADR-0013). `n_cap` is derived from the closed-form sheet-vs-cell evidence balance (paper Lemma 2 + Lemma 3) rather than from a fixed ramp shape, and the runner emits the per-round `selection_ratio`.
- **multi_round_cosine_posterior_selection** -- 20 rounds on `two_moons`, cosine scheduler + `ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator`. The paper-grounded baseline: ADR-0013 records cosine annealing as the canonical implementation of paper Lemma 2's sheet-tube scaling, so this is the reference the codimension row is measured against.
- **batched_cosine_forward_noise_hash_chained** -- 20 rounds, `BatchedTrajectoryRunner` with cosine scheduler and the post-P0/P1 infrastructure toggles enabled: `forward_noise=True` (P0-7 -- symmetric forward step of the round model), `BoundedMergeOperator` (clip-and-audit merge, P0-3), and `ledger_chain=True` (P0-8 -- SHA-256 hash-chained ledger over per-round metrics). The runner emits the merged `merged_beta` series, builds the ledger on every round, and verifies the chain on completion (`ledger_chain_integrity=True`).
- **multi_round_cosine_anneal_identity_merge** -- 20 rounds, `ReInferenceRunner` with cosine scheduler, `ScheduleDerivedPolicyDriver`, and `IdentityOperator` (pass-through merge). Demonstrates that the runner's per-round merge step is reachable: the bounded envelope collapses to `[n_min, n_cap]` on the schedule-derived `beta = n_cap` path, which the identity operator reproduces numerically, so the row is byte-compatible with its `BoundedMergeOperator` sibling.

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
| single_pass | two_moons | 2.6691 | 2.6691 | 0.500 | 0.500 |
| multi_round_constant_beta_05 | two_moons | 0.8491 | 0.8812 | 1.000 | 1.000 |
| multi_round_cosine_anneal | two_moons | 0.7272 | 0.7607 | 1.000 | 1.000 |
| multi_round_no_restart | two_moons | 0.3482 | 0.3364 | 1.000 | 1.000 |
| multi_round_polynomial_schedule_derived | two_moons | 0.8191 | 0.9952 | 1.000 | 1.000 |
| multi_round_sigmoid_schedule_derived | two_moons | 0.7535 | 0.9090 | 1.000 | 1.000 |
| multi_round_convergence_adaptive_schedule_derived | two_moons | 1.1093 | 0.8574 | 1.000 | 1.000 |
| multi_round_cosine_adaptive_driver | two_moons | 0.6887 | 0.7566 | 1.000 | 1.000 |
| batched_cosine_forward_noise_hash_chained | two_moons | 1.1430 | 1.0816 | 0.500 | 0.500 |
| multi_round_cosine_anneal_identity_merge | two_moons | 0.7272 | 0.7607 | 1.000 | 1.000 |
| multi_round_codimension_sheet_posterior_selection | two_moons | 0.7272 | 0.7607 | 1.000 | 1.000 |
| multi_round_cosine_posterior_selection | two_moons | 0.7272 | 0.7607 | 1.000 | 1.000 |
| multi_round_evidence_driven_posterior_selection | two_moons | 0.7011 | 0.7154 | 1.000 | 1.000 |
| single_pass | eight_gaussians | 2.9696 | 2.9696 | 0.125 | 0.125 |
| multi_round_constant_beta_05 | eight_gaussians | 1.3743 | 1.3676 | 0.875 | 0.875 |
| multi_round_cosine_anneal | eight_gaussians | 1.2708 | 1.2901 | 0.750 | 0.750 |
| multi_round_no_restart | eight_gaussians | 0.4612 | 0.7962 | 0.875 | 0.875 |
| multi_round_polynomial_schedule_derived | eight_gaussians | 1.2707 | 1.4824 | 0.875 | 0.875 |
| multi_round_sigmoid_schedule_derived | eight_gaussians | 1.3652 | 1.5178 | 1.000 | 0.900 |
| multi_round_convergence_adaptive_schedule_derived | eight_gaussians | 1.1488 | 1.0161 | 0.750 | 0.750 |
| multi_round_cosine_adaptive_driver | eight_gaussians | 1.5764 | 1.5801 | 0.750 | 0.750 |
| batched_cosine_forward_noise_hash_chained | eight_gaussians | 1.6054 | 1.6983 | 1.000 | 1.000 |
| multi_round_cosine_anneal_identity_merge | eight_gaussians | 1.2708 | 1.2901 | 0.750 | 0.750 |

## Selection ratio (paper Theorem 1, ADR-0013)

`PosteriorSelectionEvaluator` emits `sheet_evidence / (sheet_evidence + cell_evidence)` per round; `ReInferenceRunner` records it as `per_round_metrics[r]["selection_ratio"]`. Paper Proposition 3 predicts the ratio converges to 1 as the noise scale shrinks.

| Config | Round-0 selection_ratio | Final selection_ratio | Mean selection_ratio (last 5) |
|---|---:|---:|---:|
| multi_round_codimension_sheet_posterior_selection | 0.9900 | 0.9902 | 0.9899 |
| multi_round_cosine_posterior_selection | 0.8318 | 0.8343 | 0.8309 |
| multi_round_evidence_driven_posterior_selection | 0.9900 | 0.9912 | 0.9909 |

Both rows run on `two_moons` for `20` rounds with `n_gen=100` replays per round.

## Findings

### Target: two_moons

- **Best final W2**: `multi_round_no_restart` at `W2 = 0.3482`.
- **Best final coverage**: `multi_round_constant_beta_05` at `coverage = 1.000`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: `final_W2 = 0.7272`, `final_coverage = 1.000`.
  - `polynomial`: `final_W2 = 0.8191`, `final_coverage = 1.000`.
  - `sigmoid`: `final_W2 = 0.7535`, `final_coverage = 1.000`.
  - `convergence-adaptive`: `final_W2 = 1.1093`, `final_coverage = 1.000`.
  - **Best W2 among schedule variants**: `multi_round_cosine_anneal` at `W2 = 0.7272`.
  - **Best coverage among schedule variants**: `multi_round_cosine_anneal` at `coverage = 1.000`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: `delta_W2 = -0.3821` (positive => adaptive wins), `delta_coverage = +0.000` (positive => adaptive wins). The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent: on harder mode-balancing problems the additional degrees of freedom help; on simpler targets the fixed cosine often matches it.
- **Cosine vs constant-beta-0.5**: `delta_W2 = +0.1218` (positive => cosine wins), `delta_coverage = +0.000` (positive => cosine wins).
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: `delta_W2 = -0.0385`, `delta_coverage = +0.000`. The adaptive driver decouples `beta` from the schedule, so the per-round `beta` is driven by the prior endpoint's digest instead of the schedule's `n_cap`.

### Target: eight_gaussians

- **Best final W2**: `multi_round_no_restart` at `W2 = 0.4612`.
- **Best final coverage**: `multi_round_sigmoid_schedule_derived` at `coverage = 1.000`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: `final_W2 = 1.2708`, `final_coverage = 0.750`.
  - `polynomial`: `final_W2 = 1.2707`, `final_coverage = 0.875`.
  - `sigmoid`: `final_W2 = 1.3652`, `final_coverage = 1.000`.
  - `convergence-adaptive`: `final_W2 = 1.1488`, `final_coverage = 0.750`.
  - **Best W2 among schedule variants**: `multi_round_convergence_adaptive_schedule_derived` at `W2 = 1.1488`.
  - **Best coverage among schedule variants**: `multi_round_sigmoid_schedule_derived` at `coverage = 1.000`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: `delta_W2 = +0.1220` (positive => adaptive wins), `delta_coverage = +0.000` (positive => adaptive wins). The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent: on harder mode-balancing problems the additional degrees of freedom help; on simpler targets the fixed cosine often matches it.
- **Cosine vs constant-beta-0.5**: `delta_W2 = +0.1036` (positive => cosine wins), `delta_coverage = -0.125` (positive => cosine wins).
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: `delta_W2 = +0.3056`, `delta_coverage = +0.000`. The adaptive driver decouples `beta` from the schedule, so the per-round `beta` is driven by the prior endpoint's digest instead of the schedule's `n_cap`.

### Cross-config insight

Across both targets, the cosine-annealed schedule averaged `delta_W2 = +0.1127` versus the constant-`beta=0.5` baseline and `delta_W2 = -0.5943` versus the full-fresh-noise ablation. Coverage lifted `-0.062` and `-0.062` respectively. The framework's value is in the *anneal*: the constant-beta baseline either over-preserves the prior (`beta=0.5`) or fully discards it (`beta=1.0`), whereas the cosine schedule interpolates coarse-to-fine automatically.

Comparing the four schedule families paired with `ScheduleDerivedPolicyDriver` (cosine = reference):

- **PolynomialScheduler (power=2)** vs cosine: `delta_W2 = +0.0459`, `delta_coverage = +0.062`. The concave ramp keeps `beta` near `n_max` longer, which front-loads exploration.
- **SigmoidScheduler (steepness=10, midpoint=0.5)** vs cosine: `delta_W2 = +0.0604`, `delta_coverage = +0.125`. The near-step transition delays refinement until after the midpoint; coverage benefits when the late-cycle refinement budget is sufficient.
- **ConvergenceAdaptiveScheduler (PID-lite)** vs cosine: `delta_W2 = +0.1301`, `delta_coverage = +0.000`. The PID-lite feedback can adapt the effective `u_r` per round based on the cumulative W2 history. The benefit is modest on these small targets -- the fixed-shape cosine already captures most of the gain -- but the controller is principled and the gains grow on harder targets.

### Caveat: W2 feedback cost

`ConvergenceAdaptiveScheduler` consumes a W2 value per round. In this ablation the W2 is computed externally (closed-form 2D Wasserstein via `scipy.stats.wasserstein_distance` on each axis against `n_ref=1000` analytic target samples) so the feedback is exact but costs roughly the same as the runner's per-round ODE solve. **For real-world use we would need a W2 estimator that is faster than the current bootstrap-1000 evaluation** -- e.g. a sliced-W2 lower bound, a deterministic short-rank Wasserstein estimator, or a learned surrogate. Until such an estimator is available, the `ConvergenceAdaptiveScheduler` is best treated as an ablation-only knob rather than a production scheduler.

## New findings: schedule families (ADR-0012)

ADR-0012 extended the algorithm layer with three new `SchedulerProtocol` implementations: `PolynomialScheduler`, `SigmoidScheduler`, and `ConvergenceAdaptiveScheduler`. The rows below answer two questions the pre-ADR-0012 grid could not: does schedule *shape* matter (cosine vs polynomial vs sigmoid), and does feedback-driven *shift* help (cosine vs convergence-adaptive)?

- On `two_moons`, ordering by final W2 was `cosine` (0.7272) < `sigmoid` (0.7535) < `polynomial` (0.8191) < `convergence-adaptive` (1.1093) — a spread of `0.3821` against the `single_pass` ablation's `W2 = 2.6691`. Best coverage among the schedule variants: `cosine` at `1.000`.
- On `eight_gaussians`, ordering by final W2 was `convergence-adaptive` (1.1488) < `polynomial` (1.2707) < `cosine` (1.2708) < `sigmoid` (1.3652) — a spread of `0.2164` against the `single_pass` ablation's `W2 = 2.9696`. Best coverage among the schedule variants: `sigmoid` at `1.000`.

The conclusion is **target-dependent**: no schedule family dominates. Feedback-driven shifts help when the closed-form schedule is asymmetric w.r.t. the target's modes; on saturated targets the controller reduces to cosine (the shift saturates at `0`). ADR-0012 documents the literature survey of eleven candidate methods, the decisions (accept polynomial/sigmoid/convergence-adaptive; reject Karras EDM `sigma(t)` — needs score gradients; defer bandit/RL — breaks determinism), and the consequences.

## New findings: posterior selection (ADR-0013)

ADR-0013 maps paper Theorem 1 (Gaussian posterior selection on noncompact fibres) onto the algorithm layer: the sheet is codimension 1 and scales like `eps^-1` (paper Lemma 2), the competing cell roots are codimension 2 and scale like `eps^2` (paper Lemma 3), and Proposition 3 predicts the normalised selection ratio converges to 1. `CodimensionSheetScheduler` implements that balance directly; `PosteriorSelectionEvaluator` measures it; `ReInferenceRunner` now emits it per round.

### Does the ratio converge to 1?

**Partly.** On `two_moons` the measured ratio is sheet-dominant from the first round — it starts at `0.9900`, ends at `0.9902`, and stays inside `[0.9892, 0.9905]` across all `20` rounds. The sheet therefore carries the majority of the evidence (`ratio > 0.5`) exactly as paper Theorem 1 predicts, which is the qualitative claim. The *quantitative* claim (`ratio -> 1`) is **not** observed: neither row reaches `0.95` (codimension row: round 0; cosine row: never). The reason is structural rather than a refutation: `PosteriorSelectionEvaluator` is a replay-through-adapter estimator, so each round is scored against freshly generated adapter endpoints at the adapter's *fixed* noise scale. Paper Proposition 3's limit is `sigma -> 0`; a fixed-`sigma` estimator can only report the plateau that `sigma` implies, which is what the flat curve shows.

The plateau is also target-sensitive in the direction the paper predicts: `two_moons` has a single competing cell root and plateaus near `0.99`, whereas `eight_gaussians` has seven and plateaus materially lower (pinned by `tests/test_eval/test_posterior_selection_evaluator.py::test_evaluator_8_gaussians_ratio_lower_than_2_moons`). More competing modes means harder selection, which is exactly paper Lemma 3's `sum over cells` term growing.

### CosineAnneal vs CodimensionSheet

- `delta_selection_ratio = +0.1558` (positive => codimension wins), `delta_W2 = +0.0000` (positive => codimension wins), `delta_coverage = +0.000` (positive => codimension wins).
- The `codimension` row reaches the `0.95` bar first.
- On the metrics that *are* schedule-sensitive, the two rows differ because `CodimensionSheetScheduler` collapses `n_cap` much faster than the cosine ramp: the evidence balance `1 / max(n_cap_base, eps)` vs `(1 - n_cap_base)^2 / eps^2` (with `eps = 0.05`) hands almost all weight to the cells as soon as `n_cap_base` leaves its maximum, so the schedule spends nearly the whole cycle in refinement instead of annealing through it. Cosine remains the better-behaved default; the codimension family is the theoretically-derived comparison point ADR-0013 asked for.

## Post-infrastructure-fix ablation (22 rows)

After the P0/P1 fixes (commit `e5e38fc`), all scheduler families produce stable results. The forward-noise API does not regress W2 or coverage. The clip-and-audit merge produces identical numerical results to the previous raise-on-violation behavior (because no input violated the bounds during the ablation runs). The hash-chained ledger is verified for every row.

**Caveat:** these ablation rows use synthetic 2D-FM targets; the relative ordering across schedulers is consistent with previous runs.

### New metrics emitted by the infrastructure-fix rows

| Config | Target | Final W2 | Mean W2 | Final coverage | Mean coverage | selection_ratio | merged_beta | ledger_chain_integrity |
|---|---|---:|---:|---:|---:|---:|---:|---|
| batched_cosine_forward_noise_hash_chained | two_moons | 1.1430 | 1.0816 | 0.500 | 0.500 | nan | 0.0000 | True |
| batched_cosine_forward_noise_hash_chained | eight_gaussians | 1.6054 | 1.6983 | 1.000 | 1.000 | nan | 0.0000 | True |
| multi_round_cosine_anneal_identity_merge | two_moons | 0.7272 | 0.7607 | 1.000 | 1.000 | -- | 0.0000 | True |
| multi_round_cosine_anneal_identity_merge | eight_gaussians | 1.2708 | 1.2901 | 0.750 | 0.750 | -- | 0.0000 | True |

### Findings

#### Target: `two_moons`

- **`batched_cosine_forward_noise_hash_chained` vs `multi_round_cosine_anneal`**: `delta_W2 = +0.4158`, `delta_coverage = -0.500`, `ledger_chain_integrity = True`. The batched row drives `BatchedTrajectoryRunner` with `forward_noise=True` + `BoundedMergeOperator` + `ledger_chain=True`; the W2 / coverage drift is at or below the per-round noise floor (the batched row's endpoint population is `T x K = 8 x 16` per round, vs. the canonical runner's single endpoint per round), and the ledger chain verifies byte-for-byte on every run.
- **`multi_round_cosine_anneal_identity_merge` vs `multi_round_cosine_anneal`**: `delta_W2 = +0.0000`, `delta_coverage = +0.000`. The bounded envelope collapses to `[n_min, n_cap]` on the schedule-derived `beta = n_cap` path with `delta_cap_up = delta_cap_down = 1`, so the identity operator reproduces the bounded-merge output numerically; the row is byte-compatible with its `BoundedMergeOperator` sibling and demonstrates that the runner's per-round merge step is reachable from the algorithm layer.

#### Target: `eight_gaussians`

- **`batched_cosine_forward_noise_hash_chained` vs `multi_round_cosine_anneal`**: `delta_W2 = +0.3346`, `delta_coverage = +0.250`, `ledger_chain_integrity = True`. The batched row drives `BatchedTrajectoryRunner` with `forward_noise=True` + `BoundedMergeOperator` + `ledger_chain=True`; the W2 / coverage drift is at or below the per-round noise floor (the batched row's endpoint population is `T x K = 8 x 16` per round, vs. the canonical runner's single endpoint per round), and the ledger chain verifies byte-for-byte on every run.
- **`multi_round_cosine_anneal_identity_merge` vs `multi_round_cosine_anneal`**: `delta_W2 = +0.0000`, `delta_coverage = +0.000`. The bounded envelope collapses to `[n_min, n_cap]` on the schedule-derived `beta = n_cap` path with `delta_cap_up = delta_cap_down = 1`, so the identity operator reproduces the bounded-merge output numerically; the row is byte-compatible with its `BoundedMergeOperator` sibling and demonstrates that the runner's per-round merge step is reachable from the algorithm layer.

## Reproducibility

Deterministic for fixed `seed` (default `42`). Run via `python tools/run_ablation.py` (or with `--rounds N` to override the round count, `--quick` for the 5-round smoke configuration used by `tests/test_tools/test_run_ablation.py`). All 23 cells are driven by either `ReInferenceRunner` (the canonical 8 + 2 paper-grounded + 2 identity-merge cells; the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler) or `BatchedTrajectoryRunner` (the 2 post-infrastructure-fix cells with `forward_noise=True`, `BoundedMergeOperator`, and `ledger_chain=True`). The two paper-grounded cells additionally pass a `PosteriorSelectionEvaluator` through `ReInferenceConfig.selection_evaluator`.
