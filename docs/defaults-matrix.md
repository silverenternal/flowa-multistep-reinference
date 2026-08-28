# Defaults matrix — recommended `(scheduler, driver, merge, blender)` configs by scenario

This page is the **P1-4 external** heuristic guide that maps common
deployment scenarios to a recommended `(scheduler, driver, merge,
blender)` configuration. It is the reader-facing complement to
[`docs/schedule-theory.md`](schedule-theory.md) (the schedule-theory
derivation) and to [`docs/INSIGHTS.md`](INSIGHTS.md) (the paper-
grounded framing). The four axes the matrix covers correspond
directly to the four `Protocol`s composed by `ReInferenceRunner`:

* `SchedulerProtocol` — emits `n_cap(r)` per round [CLM-019]
* `PolicyDriverProtocol` — translates `n_cap(r)` into `beta_by_channel`
* `MergeOperatorProtocol` — bounds the per-round update inside
  `[floor, cap]` and refuses to escape the envelope [CLM-020]
* `RestartBlenderProtocol` — mixes the prior endpoint with fresh
  noise per channel

## 1. The matrix

Each row is a complete `(scheduler, driver, merge, blender)`
configuration. The Rationale column links to the paper section, ADR,
or ablation finding that motivated the choice.

| Scenario | Scheduler | PolicyDriver | MergeOperator | Blender | Rationale |
| --- | --- | --- | --- | --- | --- |
| **Short run** (4 rounds, fast feedback) | `CosineAnnealScheduler(cycle_length=4)` | `ScheduleDerivedPolicyDriver` (`schedule_derived`) | `BoundedMergeOperator(floor=0.1)` | `LinearBlender` (`linear`) | Cosine is the canonical `eps -> 0`-aligned ramp at the *direction* level ([CLM-005], ADR-0010); `floor=0.1` prevents the bounded-merge escape documented at [CLM-010]. |
| **Long run** (20 rounds, paper-aligned) | `CodimensionSheetScheduler(eps_implicit=0.05)` | `ScheduleDerivedPolicyDriver` (`schedule_derived`) | `BoundedMergeOperator(floor=0.05)` | `DistanceDecayBlender(temperature=1.0)` (`distance_decay`) | Codimension sheet is the closed-form implementation of paper Lemma 2 + Lemma 3 ([CLM-006], ADR-0013); `floor=0.05` matches the paper Theorem 1 magnitude level ([CLM-015]); `distance_decay` is the temperature-1 blender ADR-0013 §"Distance-decay blend" recommends for paper-grounded runs. |
| **Adaptive** (convergence feedback) | `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler(...))` | `ScheduleDerivedPolicyDriver` (`schedule_derived`) | `BoundedMergeOperator` | `LinearBlender` (`linear`) | PID-lite feedback-driven shift on a base cosine is the only `SchedulerProtocol` that consumes per-round oracle feedback (ADR-0012 §"Convergence-adaptive"); the bounded-merge floor still enforces the noise envelope ([CLM-020]). For W2-improving regimes (see ablation `multi_round_convergence_adaptive_schedule_derived` [CLM-018]). |
| **Sequential** (multi-phase) | `SequentialScheduler([(CosineAnnealScheduler, 8), (ExponentialScheduler, 4), (ConstantScheduler, 8)])` | `ScheduleDerivedPolicyDriver` (`schedule_derived`) | `BoundedMergeOperator` | `LinearBlender` (`linear`) | Mirrors PyTorch's SequentialLR composite scheduler ([CLM-021]); the three-phase chain (cosine → exponential → constant) is the canonical coarse-to-fine recipe (`docs/sequential-protocol.md` §2). |

### 1.1 Reading the table

Each column maps to a single first-class implementation in
[`adaptive_reflow/algorithm/`](../adaptive_reflow/algorithm/):

| Axis | Module | Implementations |
| --- | --- | --- |
| Scheduler | [`adaptive_reflow/algorithm/scheduler.py`](../adaptive_reflow/algorithm/scheduler.py) + [`adaptive_reflow/algorithm/sequential.py`](../adaptive_reflow/algorithm/sequential.py) | `CosineAnnealScheduler`, `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler`, `ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler`, `SequentialScheduler` |
| PolicyDriver | [`adaptive_reflow/algorithm/policy_driver.py`](../adaptive_reflow/algorithm/policy_driver.py) | `ScheduleDerivedPolicyDriver` (`schedule_derived`), `ConstantPolicyDriver` (`constant`), `AdaptivePolicyDriver` (`adaptive`) |
| MergeOperator | [`adaptive_reflow/algorithm/merge_operator.py`](../adaptive_reflow/algorithm/merge_operator.py) | `BoundedMergeOperator` (`bounded`), `IdentityOperator` (`identity`), `EMAOperator` (`ema`) |
| Blender | [`adaptive_reflow/algorithm/blender.py`](../adaptive_reflow/algorithm/blender.py) | `LinearBlender` (`linear`), `DistanceDecayBlender` (`distance_decay`) |

The matrix uses **four** of the nine scheduler families, **one** of the
three driver families, **one** of the three merge families, and
**one** of the two blender families. The other combinations exist
and are valid; they are not the *defaults*.

## 2. Why these defaults

### 2.1 Scheduler

The default scheduler in three of four rows is
`CosineAnnealScheduler` because:

1. It is the **canonical implementation of paper Lemma 2's sheet-tube
   scaling** at the direction level [CLM-005] (ADR-0010).
2. The 18-row ablation in `tools/run_ablation.py` records
   `cosine < convergence-adaptive < sigmoid < polynomial` on
   `two_moons` and `cosine < polynomial < sigmoid` on `eight_gaussians`
   by final W2 [CLM-018]; cosine ties or wins on the canonical
   2D-FM target.
3. The closed form is `C^1` and monotone-decreasing on the whole
   cycle (no staircase artefacts at the endpoints; see
   [`docs/schedule-theory.md`](schedule-theory.md) §1).

The **long run** row uses `CodimensionSheetScheduler` because that is
the closed-form implementation of paper Lemma 2 + Lemma 3 [CLM-006]
(ADR-0013). When the goal is *explicit* paper alignment (Theorem 1
magnitude level [CLM-015]) over the 20-round canonical ablation
horizon, the codimension-sheet closed form is the audit-friendly
choice.

The **adaptive** row uses `ConvergenceAdaptiveScheduler` because it is
the only `SchedulerProtocol` implementation that consumes per-round
oracle feedback (ADR-0012 §"Convergence-adaptive") and provides a
PID-lite shift on a base cosine. It is the right choice when
*external* convergence signal is available.

The **sequential** row uses `SequentialScheduler` because some
regimes want a piecewise schedule (e.g. cosine-then-constant for
"explore then freeze"). `SequentialScheduler` is the
[PyTorch SequentialLR analog](https://pytorch.org/docs/stable/optim.html#torchio-optimizer-lr-scheduler)
[CLM-021] and is registered under `"sequential"` in
`SCHEDULER_REGISTRY`.

### 2.2 PolicyDriver

All four rows use `ScheduleDerivedPolicyDriver` because the framework's
canonical transform is `beta = n_cap` (ADR-0010). The other two
drivers (`ConstantPolicyDriver`, `AdaptivePolicyDriver`) are valid for
ablation studies — `ConstantPolicyDriver` is the constant-`beta=0.5`
baseline that the cosine schedule was ablated against in ADR-0010 —
but they are **not** the recommended default.

### 2.3 MergeOperator

All four rows use `BoundedMergeOperator` because paper Lemma 4's
exponential suppression of the physical complement requires a
**non-zero noise floor** (the bounded-merge `floor`) [CLM-010]. The
`floor` value drops with `cycle_length` (0.1 for short runs, 0.05
for long runs) because longer cycles can tolerate a lower floor —
the algorithm has more rounds over which to escape the floor's
attractor.

The `IdentityOperator` and `EMAOperator` are valid for specialised
workloads (no merge, exponential moving average) but are not
defaults.

### 2.4 Blender

Three rows use `LinearBlender` because linear is the canonical
default that mirrors the convex blend
`memory_fraction · prior + (1 − memory_fraction) · fresh` documented
in [`docs/distinguishing-from-reflow.md`](distinguishing-from-reflow.md)
§4. The **long run** row uses `DistanceDecayBlender(temperature=1.0)`
because temperature-1 distance decay is the temperature where
[`DistanceDecayBlender`](../adaptive_reflow/algorithm/blender.py)
degenerates to the linear family in the high-temperature limit but
provides a softer transition in the low-temperature limit (ADR-0013
§"Distance-decay blend").

## 3. How to choose a configuration

The matrix is **a heuristic guide, not a hard guarantee**. A reader
who wants a deterministic recipe should pick the row whose Scenario
matches their run shape; a reader who wants to ablate should pick
**one** column to vary and hold the other three fixed. The ablation
grid in `tools/run_ablation.py` already does this on the canonical
2D-FM target.

For the schedule-family axis specifically, see
[`docs/schedule-theory.md`](schedule-theory.md) §"How to choose a
schedule" for the per-`cycle_length` decision tree.

## 4. Caveats

* **The matrix is target-agnostic.** It is calibrated against the
  canonical 2D-FM target (`two_moons`, `eight_gaussians`); targets
  with very different posterior geometries may need different
  defaults. The reader should run `tools/run_ablation.py` on the
  target of interest before trusting the row.
* **The matrix is not a paper claim.** None of the four rows is
  derived from paper Theorem 1 directly; the rationale column
  documents the *engineering* reasoning (what has been ablated, what
  has been validated) rather than the *paper* reasoning. The paper
  does not recommend any particular scheduler / driver / merge /
  blender combination; the framework's defaults are
  empirical-best.
* **The matrix is not a hard guarantee.** It is a heuristic guide.
  Any deployment that depends on a specific convergence or stability
  property must run the configuration against the target before
  trusting the row.

## 5. References

* [`docs/sequential-protocol.md`](sequential-protocol.md) — the
  `SequentialScheduler` reference (worked example, config round-trip).
* [`docs/schedule-theory.md`](schedule-theory.md) — the schedule-
  theory derivation (closed form, EDM analogy, decision tree).
* [`docs/distinguishing-from-reflow.md`](distinguishing-from-reflow.md)
  — the inference-time framing (linear blender = convex blend
  `memory_fraction · prior + (1 − memory_fraction) · fresh`).
* [`docs/INSIGHTS.md`](INSIGHTS.md) — the paper-grounded framing
  ([CLM-005], [CLM-006], [CLM-010], [CLM-015], [CLM-018]).
* [`docs/adr/0011-algorithm-abstractions.md`](adr/0011-algorithm-abstractions.md)
  — the algorithm-abstraction ADR; rationale for why all four axes
  are first-class protocols.
* [`docs/adr/0012-noise-schedule-survey.md`](adr/0012-noise-schedule-survey.md)
  — the noise-schedule survey ADR; rationale for accepting
  `ConvergenceAdaptiveScheduler` and the rejected candidates.
* [`docs/adr/0013-posterior-selection-drives-algorithm.md`](adr/0013-posterior-selection-drives-algorithm.md)
  — the paper-grounded algorithm-layer ADR; rationale for
  `CodimensionSheetScheduler` and `DistanceDecayBlender`.
* [`adaptive_reflow/algorithm/scheduler.py`](../adaptive_reflow/algorithm/scheduler.py)
  — the `SchedulerProtocol` implementations.
* [`adaptive_reflow/algorithm/sequential.py`](../adaptive_reflow/algorithm/sequential.py)
  — the `SequentialScheduler` implementation (P1-2).
* [`adaptive_reflow/algorithm/policy_driver.py`](../adaptive_reflow/algorithm/policy_driver.py)
  — the `PolicyDriverProtocol` implementations.
* [`adaptive_reflow/algorithm/merge_operator.py`](../adaptive_reflow/algorithm/merge_operator.py)
  — the `MergeOperatorProtocol` implementations.
* [`adaptive_reflow/algorithm/blender.py`](../adaptive_reflow/algorithm/blender.py)
  — the `RestartBlenderProtocol` implementations.
* [`tests/test_docs/test_defaults_matrix.py`](../tests/test_docs/test_defaults_matrix.py)
  — the regression that parses this doc and verifies every row
  references real implementations.