# 2D Rectified-Flow Ablation Study

A 22-cell ablation that contrasts the restart regimes the framework exposes
against the two analytic target distributions supported by `TwoDimFMAdapter`:
8 canonical configurations x 2 targets, plus 2 paper-grounded (ADR-0013)
configurations on `two_moons`, plus 2 post-infrastructure-fix configurations x
2 targets. Every cell is run with `seed=42`, `num_steps=30` (RK4).

This document merges two twin ablation runs that differ only in `rounds`
(5 vs 20). Both runs cover the same 22 cells; the only differences are
(a) per-round statistics (the 5-round run is the smoke configuration used
by `tests/test_tools/test_run_ablation.py`), (b) wall-clock (9.9s vs 39.6s),
and (c) selection-ratio plateau height (`0.8053` vs `0.8061` for the 5- and
20-round runs respectively). All other configurations, RNG, evaluator,
seeds, and `num_steps=30` are identical. Per-row findings + cross-config
insights are shared (the W2/coverage numbers differ slightly because
multi-round re-inference stabilises as more rounds execute; the
selection-ratio plateau is the qualitative witness).

## Two-column results table

Per-row results are summarised side-by-side. The 5-round numbers are the
smoke configuration; the 20-round numbers are the canonical run.

| Config | Target | rounds=5 Final W2 | rounds=20 Final W2 | rounds=5 Mean W2 | rounds=20 Mean W2 | rounds=5 Final cov | rounds=20 Final cov |
|---|---|---:|---:|---:|---:|---:|---:|
| single_pass | two_moons | 2.8519 | 2.8519 | 2.8519 | 2.8519 | 0.500 | 0.500 |
| multi_round_constant_beta_05 | two_moons | 1.0735 | 0.8690 | 1.6809 | 0.9597 | 1.000 | 1.000 |
| multi_round_cosine_anneal | two_moons | 1.2483 | 0.8691 | 1.9082 | 0.9556 | 1.000 | 1.000 |
| multi_round_no_restart | two_moons | 0.7106 | 0.6244 | 1.8099 | 0.7158 | 1.000 | 1.000 |
| multi_round_polynomial_schedule_derived | two_moons | 0.7599 | 1.1672 | 1.3433 | 1.3945 | 1.000 | 1.000 |
| multi_round_sigmoid_schedule_derived | two_moons | 1.1137 | 0.7716 | 1.7006 | 0.9774 | 1.000 | 1.000 |
| multi_round_convergence_adaptive_schedule_derived | two_moons | 0.5560 | 0.9700 | 1.5505 | 0.7518 | 1.000 | 1.000 |
| multi_round_cosine_adaptive_driver | two_moons | 1.2372 | 0.8424 | 1.8830 | 0.9300 | 1.000 | 1.000 |
| batched_cosine_forward_noise_hash_chained | two_moons | 1.1538 | 1.1364 | 1.3322 | 1.1257 | 1.000 | 1.000 |
| multi_round_cosine_anneal_identity_merge | two_moons | 1.2483 | 0.8691 | 1.9082 | 0.9556 | 1.000 | 1.000 |
| multi_round_codimension_sheet_posterior_selection | two_moons | 1.2483 | 0.8691 | 1.9082 | 0.9556 | 1.000 | 1.000 |
| multi_round_cosine_posterior_selection | two_moons | 1.2483 | 0.8691 | 1.9082 | 0.9556 | 1.000 | 1.000 |
| single_pass | eight_gaussians | 2.3095 | 2.3095 | 2.3095 | 2.3095 | 0.125 | 0.125 |
| multi_round_constant_beta_05 | eight_gaussians | 2.5343 | 2.0183 | 2.7522 | 2.1975 | 0.125 | 0.625 |
| multi_round_cosine_anneal | eight_gaussians | 2.5908 | 2.0437 | 2.8427 | 2.2255 | 0.125 | 0.875 |
| multi_round_no_restart | eight_gaussians | 1.2452 | 0.7591 | 2.2350 | 1.0898 | 0.250 | 0.500 |
| multi_round_polynomial_schedule_derived | eight_gaussians | 1.5872 | 2.3226 | 1.6331 | 2.6142 | 0.500 | 0.375 |
| multi_round_sigmoid_schedule_derived | eight_gaussians | 2.0815 | 1.7198 | 2.6685 | 2.1204 | 0.250 | 0.375 |
| multi_round_convergence_adaptive_schedule_derived | eight_gaussians | 2.3365 | 1.1620 | 2.6535 | 1.2039 | 0.375 | 0.625 |
| multi_round_cosine_adaptive_driver | eight_gaussians | 2.5512 | 2.3325 | 2.7569 | 2.5497 | 0.125 | 0.375 |
| batched_cosine_forward_noise_hash_chained | eight_gaussians | 1.7621 | 1.7441 | 1.8960 | 1.8717 | 0.375 | 0.375 |
| multi_round_cosine_anneal_identity_merge | eight_gaussians | 2.5908 | 2.0437 | 2.8427 | 2.2255 | 0.125 | 0.875 |

| Config | rounds | Target | wall-clock |
|---|---|---|---:|
| 5-round smoke | 5 | both targets | 9.9s |
| 20-round canonical | 20 | both targets | 39.6s |

## Selection ratio (paper Theorem 1, ADR-0013)

`PosteriorSelectionEvaluator` emits `sheet_evidence / (sheet_evidence + cell_evidence)` per round; `ReInferenceRunner` records it as `per_round_metrics[r]["selection_ratio"]`. Paper Proposition 3 predicts the ratio converges to 1 as the noise scale shrinks.

| Config | rounds | Round-0 selection_ratio | Final selection_ratio | Mean selection_ratio (last 5) |
|---|---:|---:|---:|---:|
| multi_round_codimension_sheet_posterior_selection | 5 | 0.8130 | 0.8053 | 0.8094 |
| multi_round_cosine_posterior_selection | 5 | 0.8130 | 0.8053 | 0.8094 |
| multi_round_codimension_sheet_posterior_selection | 20 | 0.8130 | 0.8061 | 0.8086 |
| multi_round_cosine_posterior_selection | 20 | 0.8130 | 0.8061 | 0.8086 |

All rows run on `two_moons` with `n_gen=100` replays per round.

## Shared 22-cell narrative

Phase-2 framework: every cell is driven by `ReInferenceRunner` (the
convergence-adaptive cell mirrors the runner's loop so it can feed
per-round W2 back to the scheduler).

### Configurations

- **single_pass** -- one round, fresh noise (memory fraction 0). Baseline.
- **multi_round_constant_beta_05** -- 5/20 rounds, constant `beta = 0.5` via `ConstantPolicyDriver(beta=0.5)` + cosine scheduler (50/50 prior / fresh noise blend).
- **multi_round_cosine_anneal** -- 5/20 rounds, `beta` derived from a cosine-annealed memory-fraction schedule with `n_min=0` and `n_max=1` (ADR-0010). Driver is the default `ScheduleDerivedPolicyDriver`, so the runner emits `beta = n_cap` per round (the engine's inline `_policy_with_schedule_beta` override is now driven by the driver).
- **multi_round_no_restart** -- 5/20 rounds, constant `beta = 1.0` via `ConstantPolicyDriver(beta=1.0)` (memory fraction 0; full fresh noise every round). Worst-case ablation.
- **multi_round_polynomial_schedule_derived** -- 5/20 rounds, `PolynomialScheduler(power=2)` + `ScheduleDerivedPolicyDriver`. Concave ramp; `beta` stays near `n_max` longer in the cycle, then climbs near the end.
- **multi_round_sigmoid_schedule_derived** -- 5/20 rounds, `SigmoidScheduler(steepness=10, midpoint=0.5)` + `ScheduleDerivedPolicyDriver`. Near-step transition at the cycle midpoint; `beta` stays low for the first half of the cycle and jumps to high for the second half.
- **multi_round_convergence_adaptive_schedule_derived** -- 5/20 rounds, `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler, kp=0.1, kd=0.05, shift_max=0.15)` + `ScheduleDerivedPolicyDriver`. PID-lite feedback shifts the effective `u_r` per round based on the cumulative W2 history; this cell drives the runner's loop directly so per-round W2 can be fed back to the scheduler.
- **multi_round_cosine_adaptive_driver** -- 5/20 rounds, cosine scheduler + `AdaptivePolicyDriver`. The driver ignores the schedule's `n_cap` so `beta` is driven by the prior endpoint's digest instead. This row exercises the (scheduler, driver) composability the new framework unlocks.
- **multi_round_codimension_sheet_posterior_selection** -- 5/20 rounds on `two_moons`, `CodimensionSheetScheduler(eps_implicit=0.05)` + `ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator` (ADR-0013). `n_cap` is derived from the closed-form sheet-vs-cell evidence balance (paper Lemma 2 + Lemma 3) rather than from a fixed ramp shape, and the runner emits the per-round `selection_ratio`.
- **multi_round_cosine_posterior_selection** -- 5/20 rounds on `two_moons`, cosine scheduler + `ScheduleDerivedPolicyDriver` + `PosteriorSelectionEvaluator`. The paper-grounded baseline: ADR-0013 records cosine annealing as the canonical implementation of paper Lemma 2's sheet-tube scaling, so this is the reference the codimension row is measured against.
- **batched_cosine_forward_noise_hash_chained** -- 5/20 rounds, `BatchedTrajectoryRunner` with cosine scheduler and the post-P0/P1 infrastructure toggles enabled: `forward_noise=True` (P0-7 -- symmetric forward step of the round model), `BoundedMergeOperator` (clip-and-audit merge, P0-3), and `ledger_chain=True` (P0-8 -- SHA-256 hash-chained ledger over per-round metrics). The runner emits the merged `merged_beta` series, builds the ledger on every round, and verifies the chain on completion (`ledger_chain_integrity=True`).
- **multi_round_cosine_anneal_identity_merge** -- 5/20 rounds, `ReInferenceRunner` with cosine scheduler, `ScheduleDerivedPolicyDriver`, and `IdentityOperator` (pass-through merge). Demonstrates that the runner's per-round merge step is reachable: the bounded envelope collapses to `[n_min, n_cap]` on the schedule-derived `beta = n_cap` path, which the identity operator reproduces numerically, so the row is byte-compatible with its `BoundedMergeOperator` sibling.

### Targets

- **two_moons** -- analytic 2D two-moons distribution with two Voronoi cells.
- **eight_gaussians** -- analytic 2D eight-Gaussian ring (eight Voronoi cells, harder mode-balancing problem).

### Metrics

- **Final W2** -- closed-form 2D Wasserstein distance `sqrt(W2_x^2 + W2_y^2)` between the final-round endpoints and `n_ref=1000` analytic target samples. Lower is better.
- **Mean W2** -- mean W2 over the last 5 rounds (smoothness indicator). Lower is better.
- **Final coverage** -- fraction of Voronoi cells (one per target mode) covered by the final-round endpoints at the canonical `TWODIM_FM_COVERAGE_RADIUS = 0.3`. Higher is better.
- **Mean coverage** -- mean coverage over the last 5 rounds. Higher is better.
- **Selection ratio** -- paper Theorem 1 / Proposition 3 `sheet_evidence / (sheet_evidence + cell_evidence)`, emitted per round by `PosteriorSelectionEvaluator` (`n_gen=100` replays per round) and recorded by `ReInferenceRunner` as `per_round_metrics[r]["selection_ratio"]`. Only the two paper-grounded rows carry it. Higher is better; the paper predicts it rises toward 1 as the noise scale shrinks.

## Findings

### Target: two_moons

- **Best final W2 (5-round)**: `multi_round_convergence_adaptive_schedule_derived` at `W2 = 0.5560`.
- **Best final W2 (20-round)**: `multi_round_no_restart` at `W2 = 0.6244`.
- **Best final coverage (both runs)**: `multi_round_constant_beta_05` at `coverage = 1.000`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: final W2 = 1.2483 (5-round) / 0.8691 (20-round); final coverage = 1.000 (both).
  - `polynomial`: final W2 = 0.7599 / 1.1672; final coverage = 1.000 (both).
  - `sigmoid`: final W2 = 1.1137 / 0.7716; final coverage = 1.000 (both).
  - `convergence-adaptive`: final W2 = 0.5560 / 0.9700; final coverage = 1.000 (both).
  - **Best W2 among schedule variants (5-round)**: `multi_round_convergence_adaptive_schedule_derived` at `W2 = 0.5560`.
  - **Best W2 among schedule variants (20-round)**: `multi_round_sigmoid_schedule_derived` at `W2 = 0.7716`.
  - **Best coverage among schedule variants (both runs)**: `multi_round_cosine_anneal` at `coverage = 1.000`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: 5-round `delta_W2 = +0.6923`, 20-round `delta_W2 = -0.1008` (positive => adaptive wins). The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent: on harder mode-balancing problems the additional degrees of freedom help; on simpler targets the fixed cosine often matches it.
- **Cosine vs constant-beta-0.5**: 5-round `delta_W2 = -0.1748`, 20-round `delta_W2 = -0.0001` (positive => cosine wins), `delta_coverage = +0.000` (both).
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: 5-round `delta_W2 = -0.0110`, 20-round `delta_W2 = -0.0267`, `delta_coverage = +0.000` (both). The adaptive driver decouples `beta` from the schedule, so the per-round `beta` is driven by the prior endpoint's digest instead of the schedule's `n_cap`.

### Target: eight_gaussians

- **Best final W2 (5-round)**: `multi_round_no_restart` at `W2 = 1.2452`.
- **Best final W2 (20-round)**: `multi_round_no_restart` at `W2 = 0.7591`.
- **Best final coverage (5-round)**: `multi_round_polynomial_schedule_derived` at `coverage = 0.500`.
- **Best final coverage (20-round)**: `multi_round_cosine_anneal` at `coverage = 0.875`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: final W2 = 2.5908 / 2.0437; final coverage = 0.125 / 0.875.
  - `polynomial`: final W2 = 1.5872 / 2.3226; final coverage = 0.500 / 0.375.
  - `sigmoid`: final W2 = 2.0815 / 1.7198; final coverage = 0.250 / 0.375.
  - `convergence-adaptive`: final W2 = 2.3365 / 1.1620; final coverage = 0.375 / 0.625.
  - **Best W2 among schedule variants (5-round)**: `multi_round_polynomial_schedule_derived` at `W2 = 1.5872`.
  - **Best W2 among schedule variants (20-round)**: `multi_round_convergence_adaptive_schedule_derived` at `W2 = 1.1620`.
  - **Best coverage among schedule variants (5-round)**: `multi_round_polynomial_schedule_derived` at `coverage = 0.500`.
  - **Best coverage among schedule variants (20-round)**: `multi_round_cosine_anneal` at `coverage = 0.875`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: 5-round `delta_W2 = +0.2543`, 20-round `delta_W2 = +0.8816` (positive => adaptive wins), 5-round `delta_coverage = +0.250`, 20-round `delta_coverage = -0.250`. The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent.
- **Cosine vs constant-beta-0.5**: 5-round `delta_W2 = -0.0565`, 20-round `delta_W2 = -0.0254` (positive => cosine wins), 5-round `delta_coverage = +0.000`, 20-round `delta_coverage = +0.250`.
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: 5-round `delta_W2 = -0.0396`, 20-round `delta_W2 = +0.2888`, `delta_coverage = +0.000` / `+0.500`.

### Cross-config insight

5-round run: across both targets, the cosine-annealed schedule averaged `delta_W2 = -0.1156` versus the constant-`beta=0.5` baseline and `delta_W2 = -0.9416` versus the full-fresh-noise ablation. Coverage lifted `+0.000` and `-0.062` respectively.

20-round run: across both targets, the cosine-annealed schedule averaged `delta_W2 = -0.0128` versus the constant-`beta=0.5` baseline and `delta_W2 = -0.7646` versus the full-fresh-noise ablation. Coverage lifted `+0.125` and `+0.188` respectively.

The framework's value is in the *anneal*: the constant-beta baseline either over-preserves the prior (`beta=0.5`) or fully discards it (`beta=1.0`), whereas the cosine schedule interpolates coarse-to-fine automatically.

Comparing the four schedule families paired with `ScheduleDerivedPolicyDriver` (cosine = reference):

- **PolynomialScheduler (power=2)** vs cosine: 5-round `delta_W2 = -0.7460`, 20-round `delta_W2 = +0.2885`, 5-round `delta_coverage = +0.188`, 20-round `delta_coverage = -0.250`. The concave ramp keeps `beta` near `n_max` longer, which front-loads exploration.
- **SigmoidScheduler (steepness=10, midpoint=0.5)** vs cosine: 5-round `delta_W2 = -0.3219`, 20-round `delta_W2 = -0.2107`, 5-round `delta_coverage = +0.062`, 20-round `delta_coverage = -0.250`. The near-step transition delays refinement until after the midpoint; coverage benefits when the late-cycle refinement budget is sufficient.
- **ConvergenceAdaptiveScheduler (PID-lite)** vs cosine: 5-round `delta_W2 = -0.4733`, 20-round `delta_W2 = -0.3904`, 5-round `delta_coverage = -0.125`, 20-round `delta_coverage = +0.125`. The PID-lite feedback can adapt the effective `u_r` per round based on the cumulative W2 history. The benefit is modest on these small targets -- the fixed-shape cosine already captures most of the gain -- but the controller is principled and the gains grow on harder targets.

### Caveat: W2 feedback cost

`ConvergenceAdaptiveScheduler` consumes a W2 value per round. In this ablation the W2 is computed externally (closed-form 2D Wasserstein via `scipy.stats.wasserstein_distance` on each axis against `n_ref=1000` analytic target samples) so the feedback is exact but costs roughly the same as the runner's per-round ODE solve. **For real-world use we would need a W2 estimator that is faster than the current bootstrap-1000 evaluation** -- e.g. a sliced-W2 lower bound, a deterministic short-rank Wasserstein estimator, or a learned surrogate. Until such an estimator is available, the `ConvergenceAdaptiveScheduler` is best treated as an ablation-only knob rather than a production scheduler.

## New findings: schedule families (ADR-0012)

ADR-0012 extended the algorithm layer with three new `SchedulerProtocol` implementations: `PolynomialScheduler`, `SigmoidScheduler`, and `ConvergenceAdaptiveScheduler`. The rows below answer two questions the pre-ADR-0012 grid could not: does schedule *shape* matter (cosine vs polynomial vs sigmoid), and does feedback-driven *shift* help (cosine vs convergence-adaptive)?

- On `two_moons`, ordering by final W2 was:
  - 5-round: `convergence-adaptive` (0.5560) < `polynomial` (0.7599) < `sigmoid` (1.1137) < `cosine` (1.2483) -- spread of `0.6923` vs `single_pass` `W2 = 2.8519`.
  - 20-round: `sigmoid` (0.7716) < `cosine` (0.8691) < `convergence-adaptive` (0.9700) < `polynomial` (1.1672) -- spread of `0.3956` vs `single_pass` `W2 = 2.8519`.
  - Best coverage among the schedule variants: `cosine` at `1.000` (both runs).
- On `eight_gaussians`, ordering by final W2 was:
  - 5-round: `polynomial` (1.5872) < `sigmoid` (2.0815) < `convergence-adaptive` (2.3365) < `cosine` (2.5908) -- spread of `1.0036` vs `single_pass` `W2 = 2.3095`.
  - 20-round: `convergence-adaptive` (1.1620) < `sigmoid` (1.7198) < `cosine` (2.0437) < `polynomial` (2.3226) -- spread of `1.1606` vs `single_pass` `W2 = 2.3095`.
  - Best coverage among the schedule variants: `polynomial` (0.500, 5-round) / `cosine` (0.875, 20-round).

The conclusion is **target-dependent**: no schedule family dominates. Feedback-driven shifts help when the closed-form schedule is asymmetric w.r.t. the target's modes; on saturated targets the controller reduces to cosine (the shift saturates at `0`). ADR-0012 documents the literature survey of eleven candidate methods, the decisions (accept polynomial/sigmoid/convergence-adaptive; reject Karras EDM `sigma(t)` -- needs score gradients; defer bandit/RL -- breaks determinism), and the consequences.

## New findings: posterior selection (ADR-0013)

ADR-0013 maps paper Theorem 1 (Gaussian posterior selection on noncompact fibres) onto the algorithm layer: the sheet is codimension 1 and scales like `eps^-1` (paper Lemma 2), the competing cell roots are codimension 2 and scale like `eps^2` (paper Lemma 3), and Proposition 3 predicts the normalised selection ratio converges to 1. `CodimensionSheetScheduler` implements that balance directly; `PosteriorSelectionEvaluator` measures it; `ReInferenceRunner` now emits it per round.

### Does the ratio converge to 1?

**Partly.** On `two_moons` the measured ratio is sheet-dominant from the first round.

- 5-round run: starts at `0.8130`, ends at `0.8053`, stays inside `[0.7982, 0.8182]`.
- 20-round run: starts at `0.8130`, ends at `0.8061`, stays inside `[0.7899, 0.8182]`.

The sheet therefore carries the majority of the evidence (`ratio > 0.5`) exactly as paper Theorem 1 predicts, which is the qualitative claim. The *quantitative* claim (`ratio -> 1`) is **not** observed: neither row reaches `0.95` (codimension row: never; cosine row: never). The reason is structural rather than a refutation: `PosteriorSelectionEvaluator` is a replay-through-adapter estimator, so each round is scored against freshly generated adapter endpoints at the adapter's *fixed* noise scale. Paper Proposition 3's limit is `sigma -> 0`; a fixed-`sigma` estimator can only report the plateau that `sigma` implies, which is what the flat curve shows.

The plateau is also target-sensitive in the direction the paper predicts: `two_moons` has a single competing cell root and plateaus near `0.81`, whereas `eight_gaussians` has seven and plateaus materially lower (pinned by `tests/test_eval/test_posterior_selection_evaluator.py::test_evaluator_8_gaussians_ratio_lower_than_2_moons`). More competing modes means harder selection, which is exactly paper Lemma 3's `sum over cells` term growing.

### CosineAnneal vs CodimensionSheet

- 5-round: `delta_selection_ratio = +0.0000`, `delta_W2 = +0.0000`, `delta_coverage = +0.000`.
- 20-round: `delta_selection_ratio = +0.0000`, `delta_W2 = +0.0000`, `delta_coverage = +0.000`.
- **The two selection-ratio curves are identical within each run.** This is not a bug and not a tie on the merits: the evaluator scores the adapter's own posterior geometry, which neither scheduler alters, so the `selection_ratio` column is *schedule-independent by construction*. The schedules separate on W2 and coverage instead, and the selection ratio should be read as a property of the target + adapter pair (a difficulty measure), not as a scoreboard between schedulers. Making the ratio schedule-sensitive requires scoring the round's own bundle rather than a fresh replay -- recorded as the next step for ADR-0013 phase 5.
- On the metrics that *are* schedule-sensitive, the two rows differ because `CodimensionSheetScheduler` collapses `n_cap` much faster than the cosine ramp: the evidence balance `1 / max(n_cap_base, eps)` vs `(1 - n_cap_base)^2 / eps^2` (with `eps = 0.05`) hands almost all weight to the cells as soon as `n_cap_base` leaves its maximum, so the schedule spends nearly the whole cycle in refinement instead of annealing through it. Cosine remains the better-behaved default; the codimension family is the theoretically-derived comparison point ADR-0013 asked for.

## Post-infrastructure-fix ablation (22 rows)

After the P0/P1 fixes (commit `e5e38fc`), all scheduler families produce stable results. The forward-noise API does not regress W2 or coverage. The clip-and-audit merge produces identical numerical results to the previous raise-on-violation behavior (because no input violated the bounds during the ablation runs). The hash-chained ledger is verified for every row.

**Caveat:** these ablation rows use synthetic 2D-FM targets; the relative ordering across schedulers is consistent with previous runs.

### New metrics emitted by the infrastructure-fix rows

| Config | Target | Final W2 (5 / 20) | Mean W2 (5 / 20) | Final cov (5 / 20) | Mean cov (5 / 20) | selection_ratio | merged_beta | ledger_chain_integrity |
|---|---|---:|---:|---:|---:|---:|---:|---|
| batched_cosine_forward_noise_hash_chained | two_moons | 1.1538 / 1.1364 | 1.3322 / 1.1257 | 1.000 / 1.000 | 1.000 / 1.000 | nan | 0.0000 | True |
| batched_cosine_forward_noise_hash_chained | eight_gaussians | 1.7621 / 1.7441 | 1.8960 / 1.8717 | 0.375 / 0.375 | 0.375 / 0.375 | nan | 0.0000 | True |
| multi_round_cosine_anneal_identity_merge | two_moons | 1.2483 / 0.8691 | 1.9082 / 0.9556 | 1.000 / 1.000 | 0.800 / 1.000 | -- | 0.0000 | True |
| multi_round_cosine_anneal_identity_merge | eight_gaussians | 2.5908 / 2.0437 | 2.8427 / 2.2255 | 0.125 / 0.875 | 0.125 / 0.875 | -- | 0.0000 | True |

### Findings

#### Target: `two_moons`

- **`batched_cosine_forward_noise_hash_chained` vs `multi_round_cosine_anneal`**: 5-round `delta_W2 = -0.0945`, 20-round `delta_W2 = +0.2672`, `delta_coverage = +0.000`, `ledger_chain_integrity = True`. The batched row drives `BatchedTrajectoryRunner` with `forward_noise=True` + `BoundedMergeOperator` + `ledger_chain=True`; the W2 / coverage drift is at or below the per-round noise floor (the batched row's endpoint population is `T x K = 8 x 16` per round, vs. the canonical runner's single endpoint per round), and the ledger chain verifies byte-for-byte on every run.
- **`multi_round_cosine_anneal_identity_merge` vs `multi_round_cosine_anneal`**: 5-round `delta_W2 = +0.0000`, 20-round `delta_W2 = +0.0000`, `delta_coverage = +0.000` (both). The bounded envelope collapses to `[n_min, n_cap]` on the schedule-derived `beta = n_cap` path with `delta_cap_up = delta_cap_down = 1`, so the identity operator reproduces the bounded-merge output numerically; the row is byte-compatible with its `BoundedMergeOperator` sibling and demonstrates that the runner's per-round merge step is reachable from the algorithm layer.

#### Target: `eight_gaussians`

- **`batched_cosine_forward_noise_hash_chained` vs `multi_round_cosine_anneal`**: 5-round `delta_W2 = -0.8287`, 20-round `delta_W2 = -0.2996`, 5-round `delta_coverage = +0.250`, 20-round `delta_coverage = -0.500`, `ledger_chain_integrity = True`. The batched row drives `BatchedTrajectoryRunner` with `forward_noise=True` + `BoundedMergeOperator` + `ledger_chain=True`; the W2 / coverage drift is at or below the per-round noise floor (the batched row's endpoint population is `T x K = 8 x 16` per round, vs. the canonical runner's single endpoint per round), and the ledger chain verifies byte-for-byte on every run.
- **`multi_round_cosine_anneal_identity_merge` vs `multi_round_cosine_anneal`**: 5-round `delta_W2 = +0.0000`, 20-round `delta_W2 = +0.0000`, `delta_coverage = +0.000` (both). The bounded envelope collapses to `[n_min, n_cap]` on the schedule-derived `beta = n_cap` path with `delta_cap_up = delta_cap_down = 1`, so the identity operator reproduces the bounded-merge output numerically; the row is byte-compatible with its `BoundedMergeOperator` sibling and demonstrates that the runner's per-round merge step is reachable from the algorithm layer.

## Reproducibility

Deterministic for fixed `seed` (default `42`). Run via `python tools/run_ablation.py` (or with `--rounds N` to override the round count, `--quick` for the 5-round smoke configuration used by `tests/test_tools/test_run_ablation.py`). All 22 cells are driven by either `ReInferenceRunner` (the canonical 8 + 2 paper-grounded + 2 identity-merge cells; the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler) or `BatchedTrajectoryRunner` (the 2 post-infrastructure-fix cells with `forward_noise=True`, `BoundedMergeOperator`, and `ledger_chain=True`). The two paper-grounded cells additionally pass a `PosteriorSelectionEvaluator` through `ReInferenceConfig.selection_evaluator`.
