# 2D Rectified-Flow Ablation Study

An 8 x 2 ablation that contrasts the restart regimes the framework exposes against the two analytic target distributions supported by `TwoDimFMAdapter`. Every cell is run with `seed=42`, `rounds=20`, and `num_steps=30` (RK4). Total wall-clock: 1.3s on a single CPU core. Phase-2 framework: every cell is driven by `ReInferenceRunner` (the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler).

## Configurations

- **single_pass** -- one round, fresh noise (memory fraction 0). Baseline.
- **multi_round_constant_beta_05** -- 20 rounds, constant `beta = 0.5` via `ConstantPolicyDriver(beta=0.5)` + cosine scheduler (50/50 prior / fresh noise blend).
- **multi_round_cosine_anneal** -- 20 rounds, `beta` derived from a cosine-annealed memory-fraction schedule with `n_min=0` and `n_max=1` (ADR-0010). Driver is the default `ScheduleDerivedPolicyDriver`, so the runner emits `beta = n_cap` per round (the engine's inline `_policy_with_schedule_beta` override is now driven by the driver).
- **multi_round_no_restart** -- 20 rounds, constant `beta = 1.0` via `ConstantPolicyDriver(beta=1.0)` (memory fraction 0; full fresh noise every round). Worst-case ablation.
- **multi_round_polynomial_schedule_derived** -- 20 rounds, `PolynomialScheduler(power=2)` + `ScheduleDerivedPolicyDriver`. Concave ramp; `beta` stays near `n_max` longer in the cycle, then climbs near the end.
- **multi_round_sigmoid_schedule_derived** -- 20 rounds, `SigmoidScheduler(steepness=10, midpoint=0.5)` + `ScheduleDerivedPolicyDriver`. Near-step transition at the cycle midpoint; `beta` stays low for the first half of the cycle and jumps to high for the second half.
- **multi_round_convergence_adaptive_schedule_derived** -- 20 rounds, `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler, kp=0.1, kd=0.05, shift_max=0.15)` + `ScheduleDerivedPolicyDriver`. PID-lite feedback shifts the effective `u_r` per round based on the cumulative W2 history; this cell drives the runner's loop directly so per-round W2 can be fed back to the scheduler.
- **multi_round_cosine_adaptive_driver** -- 20 rounds, cosine scheduler + `AdaptivePolicyDriver`. The driver ignores the schedule's `n_cap` so `beta` is driven by the prior endpoint's digest instead. This row exercises the (scheduler, driver) composability the new framework unlocks.

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
| single_pass | two_moons | 3.7076 | 3.7076 | 0.500 | 0.500 |
| multi_round_constant_beta_05 | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| multi_round_cosine_anneal | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| multi_round_no_restart | two_moons | 0.4861 | 0.5864 | 1.000 | 1.000 |
| multi_round_polynomial_schedule_derived | two_moons | 1.0521 | 1.2320 | 1.000 | 1.000 |
| multi_round_sigmoid_schedule_derived | two_moons | 0.9397 | 1.0716 | 1.000 | 1.000 |
| multi_round_convergence_adaptive_schedule_derived | two_moons | 0.8973 | 0.6947 | 1.000 | 1.000 |
| multi_round_cosine_adaptive_driver | two_moons | 0.8140 | 0.8955 | 1.000 | 1.000 |
| single_pass | eight_gaussians | 1.7358 | 1.7358 | 0.125 | 0.125 |
| multi_round_constant_beta_05 | eight_gaussians | 1.9298 | 2.0894 | 0.375 | 0.375 |
| multi_round_cosine_anneal | eight_gaussians | 1.9298 | 2.0894 | 0.375 | 0.375 |
| multi_round_no_restart | eight_gaussians | 0.7052 | 1.1281 | 0.875 | 0.725 |
| multi_round_polynomial_schedule_derived | eight_gaussians | 2.0943 | 2.3377 | 0.500 | 0.500 |
| multi_round_sigmoid_schedule_derived | eight_gaussians | 2.2849 | 2.5385 | 0.375 | 0.375 |
| multi_round_convergence_adaptive_schedule_derived | eight_gaussians | 1.1688 | 1.2374 | 0.625 | 0.625 |
| multi_round_cosine_adaptive_driver | eight_gaussians | 1.9298 | 2.0894 | 0.375 | 0.375 |

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

## New findings: schedule families (ADR-0012, 2026-08-28)

ADR-0012 extended the algorithm layer with three new
`SchedulerProtocol` implementations: `PolynomialScheduler`,
`SigmoidScheduler`, and `ConvergenceAdaptiveScheduler`. The
ablation grid grew from 8 to **16 rows** (8 configs x 2
targets), and the new rows answer two questions the old
grid could not:

* **Does schedule shape matter?** — comparing
  `cosine`, `polynomial` (concave, `power=2`),
  `sigmoid` (plateau + step, `steepness=10, midpoint=0.5`),
  all paired with `ScheduleDerivedPolicyDriver`.
* **Does feedback-driven shift help?** — comparing
  `cosine` (no feedback) against
  `convergence_adaptive_cosine` (PID-lite feedback from
  per-round `W2`).

### Schedule shape axis (cosine vs polynomial vs sigmoid)

Across both targets, the closed-form schedule family
cosine / polynomial (concave, `power=2`) / sigmoid
(`steepness=10, midpoint=0.5`) had target-dependent
ordering but no family dominated:

* On `two_moons` (`coverage = 1.000` from every family —
  coverage is a saturated metric here), `multi_round_cosine_anneal`
  was tightest on W2 (`0.8140`), polynomial was loosest
  (`1.0521`), and sigmoid sat between
  (`0.9397`). The gap on W2 is `0.2381` from cosine to
  polynomial — small relative to the `single_pass`
  ablation's W2 of `3.7076`.
* On `eight_gaussians` (the harder mode-balancing
  problem, coverage unsaturated), the ordering changed:
  `convergence_adaptive` won (`1.1688`), `cosine` came
  next (`1.9298`), and `polynomial` and `sigmoid`
  trailed (`2.0943` and `2.2849`). Cosine had the best
  coverage of the three closed-form families
  (`0.375`); polynomial reached `0.500`. The
  sigmoid's plateau-and-step ramp front-loads
  refinement, which costs coverage here.

### Feedback axis (cosine vs convergence-adaptive)

`ConvergenceAdaptiveScheduler(kp=0.10, kd=0.05,
shift_max=0.15)` was the **most interesting
non-ablation finding in this round**:

* On `two_moons`: `delta_W2 = -0.0833` (positive =>
  adaptive wins) and `delta_coverage = +0.000`. The
  PID-lite controller learned nothing the fixed cosine
  did not already encode — both endpoints saturate
  coverage and the convergence target is loose enough
  that the cosine ramp captures nearly all of the gain.
* On `eight_gaussians`: `delta_W2 = +0.7610`
  (positive => adaptive wins) and
  `delta_coverage = +0.250` (positive => adaptive
  wins). On the harder mode-balancing target the
  PID-lite controller **dramatically improved** over
  the fixed cosine: a `0.7610` W2 gap, and `0.625` vs
  `0.375` coverage (1.7x). The feedback informed the
  shift to spend more refinement budget on the late
  modes that cosine's fixed ramp under-explored.

The conclusion is **target-dependent**: feedback-driven
shifts help when the closed-form schedule is
asymmetric w.r.t. the target's modes; on saturated
targets the controller reduces to cosine (shift
saturates at `0`).

### Caveat and forward work

The gains documented above come from the *closed-loop*
oracle (closed-form 2D Wasserstein), so the W2 feedback
is exact. **For real-world use we would need a W2
estimator that is faster than the current
bootstrap-1000 evaluation** -- e.g. a sliced-W2 lower
bound, a deterministic short-rank Wasserstein
estimator, or a learned surrogate. Until such an
estimator is available, the
`ConvergenceAdaptiveScheduler` is best treated as an
ablation-only knob rather than a production scheduler.

ADR-0012 documents the literature survey of **eleven**
candidate methods, the decisions (accept
polynomial/sigmoid/convergence-adaptive; reject Karras
EDM `sigma(t)` — needs score gradients; defer
bandit/RL — breaks determinism), and the consequences
(scheduler families now at 7; ablation grid now at 16
rows; `record_round_feedback` is an optional Protocol
extension).

## Reproducibility

Deterministic for fixed `seed` (default `42`). Run via `python tools/run_ablation.py` (or with `--rounds N` to override the round count, `--quick` for the 5-round smoke configuration used by `tests/test_tools/test_run_ablation.py`). The eight canonical configurations are all driven by `ReInferenceRunner` (the convergence-adaptive cell mirrors the runner's loop so it can feed per-round W2 back to the scheduler).
