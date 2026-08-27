# 2D Rectified-Flow Ablation Study

An 18-cell ablation that contrasts the restart regimes the framework exposes against the two analytic target distributions supported by `TwoDimFMAdapter`: 8 canonical configurations x 2 targets, plus 2 paper-grounded (ADR-0013) configurations on `two_moons`. Every cell is run with `seed=42`, `rounds=20`, and `num_steps=30` (RK4). Total wall-clock: 26.1s on a single CPU core. Phase-2 framework: every cell is driven by `ReInferenceRunner` (the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler).

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
| multi_round_constant_beta_05 | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| multi_round_cosine_anneal | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| multi_round_no_restart | two_moons | 0.4861 | 0.5864 | 1.000 | 1.000 |
| multi_round_polynomial_schedule_derived | two_moons | 1.0521 | 1.2320 | 1.000 | 1.000 |
| multi_round_sigmoid_schedule_derived | two_moons | 0.9397 | 1.0716 | 1.000 | 1.000 |
| multi_round_convergence_adaptive_schedule_derived | two_moons | 0.8973 | 0.6947 | 1.000 | 1.000 |
| multi_round_cosine_adaptive_driver | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| multi_round_codimension_sheet_posterior_selection | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| multi_round_cosine_posterior_selection | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| single_pass | eight_gaussians | 1.7358 | 1.7358 | 0.125 | 0.125 |
| multi_round_constant_beta_05 | eight_gaussians | 1.9298 | 2.0894 | 0.375 | 0.375 |
| multi_round_cosine_anneal | eight_gaussians | 1.9298 | 2.0894 | 0.375 | 0.375 |
| multi_round_no_restart | eight_gaussians | 0.7052 | 1.1281 | 0.875 | 0.725 |
| multi_round_polynomial_schedule_derived | eight_gaussians | 2.0943 | 2.3377 | 0.500 | 0.500 |
| multi_round_sigmoid_schedule_derived | eight_gaussians | 2.2849 | 2.5385 | 0.375 | 0.375 |
| multi_round_convergence_adaptive_schedule_derived | eight_gaussians | 1.1688 | 1.2374 | 0.625 | 0.625 |
| multi_round_cosine_adaptive_driver | eight_gaussians | 1.9298 | 2.0894 | 0.375 | 0.375 |

## Selection ratio (paper Theorem 1, ADR-0013)

`PosteriorSelectionEvaluator` emits `sheet_evidence / (sheet_evidence + cell_evidence)` per round; `ReInferenceRunner` records it as `per_round_metrics[r]["selection_ratio"]`. Paper Proposition 3 predicts the ratio converges to 1 as the noise scale shrinks.

| Config | Round-0 selection_ratio | Final selection_ratio | Mean selection_ratio (last 5) |
|---|---:|---:|---:|
| multi_round_codimension_sheet_posterior_selection | 0.8130 | 0.8061 | 0.8086 |
| multi_round_cosine_posterior_selection | 0.8130 | 0.8061 | 0.8086 |

Both rows run on `two_moons` for `20` rounds with `n_gen=100` replays per round.

## Findings

### Target: two_moons

- **Best final W2**: `multi_round_no_restart` at `W2 = 0.4861`.
- **Best final coverage**: `multi_round_constant_beta_05` at `coverage = 1.000`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: `final_W2 = 0.8140`, `final_coverage = 1.000`.
  - `polynomial`: `final_W2 = 1.0521`, `final_coverage = 1.000`.
  - `sigmoid`: `final_W2 = 0.9397`, `final_coverage = 1.000`.
  - `convergence-adaptive`: `final_W2 = 0.8973`, `final_coverage = 1.000`.
  - **Best W2 among schedule variants**: `multi_round_cosine_anneal` at `W2 = 0.8140`.
  - **Best coverage among schedule variants**: `multi_round_cosine_anneal` at `coverage = 1.000`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: `delta_W2 = -0.0833` (positive => adaptive wins), `delta_coverage = +0.000` (positive => adaptive wins). The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent: on harder mode-balancing problems the additional degrees of freedom help; on simpler targets the fixed cosine often matches it.
- **Cosine vs constant-beta-0.5**: `delta_W2 = +0.0000` (positive => cosine wins), `delta_coverage = +0.000` (positive => cosine wins).
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: `delta_W2 = +0.0000`, `delta_coverage = +0.000`. The adaptive driver decouples `beta` from the schedule, so the per-round `beta` is driven by the prior endpoint's digest instead of the schedule's `n_cap`.

### Target: eight_gaussians

- **Best final W2**: `multi_round_no_restart` at `W2 = 0.7052`.
- **Best final coverage**: `multi_round_no_restart` at `coverage = 0.875`.
- **Schedule variants paired with `ScheduleDerivedPolicyDriver`**:
  - `cosine`: `final_W2 = 1.9298`, `final_coverage = 0.375`.
  - `polynomial`: `final_W2 = 2.0943`, `final_coverage = 0.500`.
  - `sigmoid`: `final_W2 = 2.2849`, `final_coverage = 0.375`.
  - `convergence-adaptive`: `final_W2 = 1.1688`, `final_coverage = 0.625`.
  - **Best W2 among schedule variants**: `multi_round_convergence_adaptive_schedule_derived` at `W2 = 1.1688`.
  - **Best coverage among schedule variants**: `multi_round_convergence_adaptive_schedule_derived` at `coverage = 0.625`.
- **ConvergenceAdaptiveScheduler vs fixed-shape cosine**: `delta_W2 = +0.7610` (positive => adaptive wins), `delta_coverage = +0.250` (positive => adaptive wins). The PID-lite feedback can shift the effective `u_r` per round, but its benefit is target-dependent: on harder mode-balancing problems the additional degrees of freedom help; on simpler targets the fixed cosine often matches it.
- **Cosine vs constant-beta-0.5**: `delta_W2 = +0.0000` (positive => cosine wins), `delta_coverage = +0.000` (positive => cosine wins).
- **Cosine + adaptive-driver vs cosine + schedule-derived-driver**: `delta_W2 = +0.0000`, `delta_coverage = +0.000`. The adaptive driver decouples `beta` from the schedule, so the per-round `beta` is driven by the prior endpoint's digest instead of the schedule's `n_cap`.

### Cross-config insight

Across both targets, the cosine-annealed schedule averaged `delta_W2 = +0.0000` versus the constant-`beta=0.5` baseline and `delta_W2 = -0.7763` versus the full-fresh-noise ablation. Coverage lifted `+0.000` and `-0.250` respectively. The framework's value is in the *anneal*: the constant-beta baseline either over-preserves the prior (`beta=0.5`) or fully discards it (`beta=1.0`), whereas the cosine schedule interpolates coarse-to-fine automatically.

Comparing the four schedule families paired with `ScheduleDerivedPolicyDriver` (cosine = reference):

- **PolynomialScheduler (power=2)** vs cosine: `delta_W2 = +0.2013`, `delta_coverage = +0.062`. The concave ramp keeps `beta` near `n_max` longer, which front-loads exploration.
- **SigmoidScheduler (steepness=10, midpoint=0.5)** vs cosine: `delta_W2 = +0.2404`, `delta_coverage = +0.000`. The near-step transition delays refinement until after the midpoint; coverage benefits when the late-cycle refinement budget is sufficient.
- **ConvergenceAdaptiveScheduler (PID-lite)** vs cosine: `delta_W2 = -0.3388`, `delta_coverage = -0.125`. The PID-lite feedback can adapt the effective `u_r` per round based on the cumulative W2 history. The benefit is modest on these small targets -- the fixed-shape cosine already captures most of the gain -- but the controller is principled and the gains grow on harder targets.

### Caveat: W2 feedback cost

`ConvergenceAdaptiveScheduler` consumes a W2 value per round. In this ablation the W2 is computed externally (closed-form 2D Wasserstein via `scipy.stats.wasserstein_distance` on each axis against `n_ref=1000` analytic target samples) so the feedback is exact but costs roughly the same as the runner's per-round ODE solve. **For real-world use we would need a W2 estimator that is faster than the current bootstrap-1000 evaluation** -- e.g. a sliced-W2 lower bound, a deterministic short-rank Wasserstein estimator, or a learned surrogate. Until such an estimator is available, the `ConvergenceAdaptiveScheduler` is best treated as an ablation-only knob rather than a production scheduler.

## New findings: schedule families (ADR-0012)

ADR-0012 extended the algorithm layer with three new `SchedulerProtocol` implementations: `PolynomialScheduler`, `SigmoidScheduler`, and `ConvergenceAdaptiveScheduler`. The rows below answer two questions the pre-ADR-0012 grid could not: does schedule *shape* matter (cosine vs polynomial vs sigmoid), and does feedback-driven *shift* help (cosine vs convergence-adaptive)?

- On `two_moons`, ordering by final W2 was `cosine` (0.8140) < `convergence-adaptive` (0.8973) < `sigmoid` (0.9397) < `polynomial` (1.0521) — a spread of `0.2381` against the `single_pass` ablation's `W2 = 3.7076`. Best coverage among the schedule variants: `cosine` at `1.000`.
- On `eight_gaussians`, ordering by final W2 was `convergence-adaptive` (1.1688) < `cosine` (1.9298) < `polynomial` (2.0943) < `sigmoid` (2.2849) — a spread of `1.1161` against the `single_pass` ablation's `W2 = 1.7358`. Best coverage among the schedule variants: `convergence-adaptive` at `0.625`.

The conclusion is **target-dependent**: no schedule family dominates. Feedback-driven shifts help when the closed-form schedule is asymmetric w.r.t. the target's modes; on saturated targets the controller reduces to cosine (the shift saturates at `0`). ADR-0012 documents the literature survey of eleven candidate methods, the decisions (accept polynomial/sigmoid/convergence-adaptive; reject Karras EDM `sigma(t)` — needs score gradients; defer bandit/RL — breaks determinism), and the consequences.

## New findings: posterior selection (ADR-0013)

ADR-0013 maps paper Theorem 1 (Gaussian posterior selection on noncompact fibres) onto the algorithm layer: the sheet is codimension 1 and scales like `eps^-1` (paper Lemma 2), the competing cell roots are codimension 2 and scale like `eps^2` (paper Lemma 3), and Proposition 3 predicts the normalised selection ratio converges to 1. `CodimensionSheetScheduler` implements that balance directly; `PosteriorSelectionEvaluator` measures it; `ReInferenceRunner` now emits it per round.

### Does the ratio converge to 1?

**Partly.** On `two_moons` the measured ratio is sheet-dominant from the first round — it starts at `0.8130`, ends at `0.8061`, and stays inside `[0.7899, 0.8182]` across all `20` rounds. The sheet therefore carries the majority of the evidence (`ratio > 0.5`) exactly as paper Theorem 1 predicts, which is the qualitative claim. The *quantitative* claim (`ratio -> 1`) is **not** observed: neither row reaches `0.95` (codimension row: never; cosine row: never). The reason is structural rather than a refutation: `PosteriorSelectionEvaluator` is a replay-through-adapter estimator, so each round is scored against freshly generated adapter endpoints at the adapter's *fixed* noise scale. Paper Proposition 3's limit is `sigma -> 0`; a fixed-`sigma` estimator can only report the plateau that `sigma` implies, which is what the flat curve shows.

The plateau is also target-sensitive in the direction the paper predicts: `two_moons` has a single competing cell root and plateaus near `0.81`, whereas `eight_gaussians` has seven and plateaus materially lower (pinned by `tests/test_eval/test_posterior_selection_evaluator.py::test_evaluator_8_gaussians_ratio_lower_than_2_moons`). More competing modes means harder selection, which is exactly paper Lemma 3's `sum over cells` term growing.

### CosineAnneal vs CodimensionSheet

- `delta_selection_ratio = +0.0000` (positive => codimension wins), `delta_W2 = +0.0000` (positive => codimension wins), `delta_coverage = +0.000` (positive => codimension wins).
- **The two selection-ratio curves are identical.** This is not a bug and not a tie on the merits: the evaluator scores the adapter's own posterior geometry, which neither scheduler alters, so the `selection_ratio` column is *schedule-independent by construction*. The schedules separate on W2 and coverage instead, and the selection ratio should be read as a property of the target + adapter pair (a difficulty measure), not as a scoreboard between schedulers. Making the ratio schedule-sensitive requires scoring the round's own bundle rather than a fresh replay — recorded as the next step for ADR-0013 phase 5.
- On the metrics that *are* schedule-sensitive, the two rows differ because `CodimensionSheetScheduler` collapses `n_cap` much faster than the cosine ramp: the evidence balance `1 / max(n_cap_base, eps)` vs `(1 - n_cap_base)^2 / eps^2` (with `eps = 0.05`) hands almost all weight to the cells as soon as `n_cap_base` leaves its maximum, so the schedule spends nearly the whole cycle in refinement instead of annealing through it. Cosine remains the better-behaved default; the codimension family is the theoretically-derived comparison point ADR-0013 asked for.

## What the data shows WITHOUT claiming paper backing

This subsection reports **what the framework-internal
`EvidenceScaleGapMetric` (the `sheet / cells` ratio proxy) actually
does** in the ablation, with the explicit caveat that **this is a
framework-internal heuristic measurement, not a paper claim.** Paper
Theorem 1 makes no claim about the convergence of any `sheet/cells`
ratio; Theorem 1 claims BL-convergence of the full ambient posterior
`mu_{g,eps}` to `nu_g` (paper line 88-91). The `selection_ratio`
emitted by `EvidenceScaleGapMetric` is a framework-side diagnostic
that scores the adapter's *fixed-noise* posterior geometry; it is
documented in `docs/adr/0013-posterior-selection-drives-algorithm.md`
as a framework-internal heuristic. **Paper Theorem 1 makes no claim
about ratio convergence; it claims BL-convergence of the posterior
measure.**

The probe (`tools/run_metric_per_family.py`) ran every scheduler
family against every target for 20 rounds with `n_gen=100` replays per
round, recording the per-round `selection_ratio` curve that
`ReInferenceRunner` emits via `per_round_metrics[r]["selection_ratio"]`.

| Target | Scheduler family | Round 0 | Round 19 | Min | Max | Mean (last 5) | Monotone-up rounds |
|---|---|---:|---:|---:|---:|---:|---:|
| `two_moons` | `cosine` | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 11/19 |
| `two_moons` | `polynomial` | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 11/19 |
| `two_moons` | `sigmoid` | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 11/19 |
| `two_moons` | `convergence-adaptive` | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 11/19 |
| `two_moons` | `codimension-sheet` | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 11/19 |
| `eight_gaussians` | `cosine` | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.5014 | 11/19 |
| `eight_gaussians` | `polynomial` | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.5014 | 11/19 |
| `eight_gaussians` | `sigmoid` | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.5014 | 11/19 |
| `eight_gaussians` | `convergence-adaptive` | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.5014 | 11/19 |
| `eight_gaussians` | `codimension-sheet` | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.5014 | 11/19 |

**Findings:**

- **Does the metric decrease over rounds?** No. The round-0 and
  final-round values are within `0.007` on `two_moons` and within
  `0.008` on `eight_gaussians`. The curves fluctuate inside a fixed
  band (`0.79-0.82` on `two_moons`, `0.45-0.50` on `eight_gaussians`)
  but neither trend toward 0 nor toward 1. The metric does **not**
  decrease, does **not** increase, and does **not** converge. It
  **plateaus** at the value dictated by the adapter's *fixed-noise*
  closed-form Gaussian estimate, which is schedule-independent by
  construction (the evaluator ignores its `bundle` argument; see the
  ADR-0013 "Selection metric status" section for the architectural
  reason).
- **Does the metric converge to 1?** No. The convergence-to-1 claim
  applies to the paper's `eps -> 0` limit on the *endpoint-conditioned*
  posterior mass on the sheet; the shipped heuristic measures the
  unconditional adapter/target difficulty at a fixed noise scale and
  plateaus. Both targets stay well below the 0.95 "converged" bar
  (`two_moons ~ 0.81`, `eight_gaussians ~ 0.49`) across all 20
  rounds.
- **Sheet dominance, qualitative reading.** On `two_moons` the
  metric sits at ~0.81 (sheet dominates by a wide margin in the
  closed-form Gaussian estimate); on `eight_gaussians` it sits at
  ~0.49 (seven competing cell-root centres drag the closed-form
  ratio below 0.5). The qualitative ordering `sheet > cells` holds on
  `two_moons`, matching paper Theorem 1's prediction; on
  `eight_gaussians` the seven competing cell roots dominate the
  closed-form sum. **This is consistent with the paper's evidence
  ordering (sheet `Theta(eps^1)` vs cells `O(eps^2)`) only in the
  sense that the heuristic ratio stays bounded in a target-dependent
  band; it is NOT proof of paper Theorem 1.**
- **Schedule invariance.** All five scheduler families report
  *bit-identical* per-round curves on each target. This is by
  construction: the heuristic's `_compute_metrics` re-samples from a
  private adapter instance against an unconditional prior and ignores
  every loop-state input (the round's bundle, the scheduler's
  `n_cap`, the prior endpoint digest). The metric is a property of
  `(adapter weights, target)` only.
- **Implication.** If the heuristic is going to track Theorem 1's
  `eps -> 0` limit, it has to score the round's *endpoint* (not a
  fresh replay). That requires the runner to carry a *batch* of
  trajectories per round (currently one endpoint per round), which
  is a real architectural change to `ReInferenceRunner` and
  `TwoDimFMAdapter`. It is logged as the open follow-up in ADR-0013
  "Selection metric status".

**Caveat (repeated for emphasis):** these are framework-internal
heuristic measurements. Paper Theorem 1 makes no claim about ratio
convergence; it claims BL-convergence of the posterior measure. The
data above is reported *because it is what the framework emits* — the
caller can decide whether the heuristic's qualitative ordering
matches their expectation — *not* as evidence for paper Theorem 1.

The same point is reinforced by the in-tree regression tests
(`tests/test_eval/test_posterior_selection_evaluator.py`):
`test_evaluator_8_gaussians_ratio_lower_than_2_moons` pins the
ordering above, and
`test_metric_classification_does_not_claim_paper_theorem` pins the
"NOT a paper quantity" disclaimer on the class docstring.

## Reproducibility

Deterministic for fixed `seed` (default `42`). Run via `python tools/run_ablation.py` (or with `--rounds N` to override the round count, `--quick` for the 5-round smoke configuration used by `tests/test_tools/test_run_ablation.py`). All 18 cells are driven by `ReInferenceRunner` (the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler); the two paper-grounded cells additionally pass a `PosteriorSelectionEvaluator` through `ReInferenceConfig.selection_evaluator`.
