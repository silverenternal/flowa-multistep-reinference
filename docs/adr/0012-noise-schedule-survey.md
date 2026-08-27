---
status: accepted
date: 2026-08-28
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 12. Noise-injection schedule survey & family expansion

## Context and Problem Statement

Up to and including
[ADR-0011](0011-algorithm-abstractions.md) the algorithm layer
exposes exactly **three** deterministic schedule families
(`cosine`, `linear`, `exponential`) plus a constant baseline
(`ConstantScheduler`). All four are *closed-form*, no-parameter
(except the cycle anchors `n_min`/`n_max`), and none of them
consume the runner's per-round oracle feedback
([ADR-0011](0011-algorithm-abstractions.md) §"The outer framework").

The user asked: *what noise-injection schedule methods exist
beyond cosine annealing?* The question is grounded — for a
research codebase whose product is ablation tables, a
single-schedule framework cannot answer "does the *shape* of the
schedule matter, holding the cycle anchors fixed?". Before this
ADR the answer was "yes, and the only legal shapes are cosine,
linear, exponential, and constant".

A brief literature survey of the diffusion-model and noise-injection
literature identified **eleven** candidate methods, summarised in
§"Candidate methods surveyed". The user requested that the project
*not* ship a megillah on day one — instead the proposed change
selects a small handful of candidates whose implementation cost is
trivial and whose ablation value is high, and defers the rest with
reasoned justification.

The decision drivers are therefore:

* **Ablation value.** A new schedule that is hard to implement
  but exercises the same axis as cosine is research-not-product.
  We pick candidates that occupy new *axes* in the ablation grid
  (shape, feedback-driven, plateau-then-ramp).
* **Determinism.** The framework depends on byte-identical
  re-runs and frozen `config_hash` provenance
  ([ADR-0001](0001-record-architecture-decisions.md) §"Format").
  Candidates whose update rule is stochastic (bandit arms,
  online RL) are out for this round.
* **No-train.** Schedulers live in `adaptive_reflow/algorithm/`,
  which is a *closed-form* layer; introducing learned parameters
  breaks the contracts-layer / algorithm-layer / molecular-layer
  decomposition
  ([ADR-0002](0002-typed-contracts-core-boundary.md)). Candidates
  that require learned parameters (Karras EDM `sigma(t)`, RL
  policies) are deferred until the learned-parameter seam is
  designed.
* **Backwards compatibility.** All existing call paths
  (`Engine.run_round`, `ReInferenceRunner`, the four-string
  schedule family taxonomy) MUST keep working unchanged.

## Decision Drivers

* A schedule family's value is its placement on a new *axis*
  in the ablation grid (shape, feedback, plateau, ...), not
  its arithmetic novelty.
* Determinism and frozen `config_hash` provenance are non-negotiable;
  candidates whose update is stochastic, online-learned, or
  involves a sampled random variable that is not in the
  scheduler's constructor break the audit story
  ([ADR-0005](0005-fail-closed-audit-code-policy.md)) and are
  deferred.
* Implementation cost must be small — a single ~80-line file
  per family — so the framework can absorb multiple families in
  one round.
* The runner already exposes a per-round oracle feedback path;
  candidates that consume that signal (PID-lite, thresholded
  decay) compound on the existing wiring rather than introduce
  a parallel channel.

## Candidate methods surveyed

The following candidate methods surfaced from the literature
survey:

| # | Method | Family | Feedback? | Stochastic? | Trainable? | Verdict |
|---|--------|--------|-----------|-------------|------------|---------|
| 1 | Cosine annealing (Loshchilov & Hutter, 2017) | convex/concave shape | No | No | No | already shipped |
| 2 | Linear ramp | monotonic interpolation | No | No | No | already shipped (ADR-0011) |
| 3 | Exponential decay (Devlin / synth.) | fast-then-slow | No | No | No | already shipped (ADR-0011) |
| 4 | **Polynomial decay** `(1 - u_r^p)` | power-law | No | No | No | **ACCEPTED** (this round) |
| 5 | **Sigmoid / logit ramp** `sigmoid(k(u_r - m))` | plateau + step | No | No | No | **ACCEPTED** (this round) |
| 6 | Step (piecewise constant) | discrete jumps | No | No | No | subsumed by sigmoid in the limit (deferred) |
| 7 | Cyclical LR (Smith, 2017) | oscillating | No | No | No | incompatible with the "one cycle = one anneal" semantics — deferred |
| 8 | **Convergence-adaptive / PID-lite** | feedback-driven | **Yes** (W2) | No | No | **ACCEPTED** (this round, headline novelty) |
| 9 | Karras EDM `sigma(t)` (Karras et al. 2022) | score-matched | No | No | **Yes (score model)** | needs score gradients — REJECTED this round |
| 10 | Bandit / UCB schedule | arms = cycle anchors | Yes (reward) | **Yes** | No | breaks determinism — REJECTED this round |
| 11 | RL-policy schedule | policy = shift rule | Yes | **Yes** | **Yes (online)** | breaks determinism AND contracts-layer seam — REJECTED this round |

## Considered Options

1. **Implement PolynomialScheduler + SigmoidScheduler
   (trivial) + ConvergenceAdaptiveScheduler (headline
   PID-lite) in this round. Reject Karras EDM `sigma(t)`
   (needs score gradients). Defer bandit / RL schedules
   (breaks determinism). Defer cyclical and step schedules
   (subsumed by sigmoid in the limit, or incompatible
   semantics).** Three files, ~400 LOC, three new entries in
   `SCHEDULER_REGISTRY`, all deterministic and unlearned,
   `SchedulerProtocol` extended with an optional
   `record_round_feedback` hook that defaults to a no-op on
   the four non-adaptive families. Runner wires
   `record_round_feedback` after the per-round promotion.
2. **Implement all seven deterministic candidates in one
   round.** Rejected: cost is high (~600 LOC plus a longer
   test matrix), the marginal ablation value is low
   (polynomial already subsumes step in the limit, sigmoid
   subsumes thresholded decay), and the headline novelty
   (PID-lite feedback) would be lost in the noise.
3. **Implement Karras EDM `sigma(t)` even without a score
   model, using a hand-rolled analytic surrogate.** Rejected:
   the published `sigma(t)` is *defined* by the score-matching
   precondition; a surrogate loses the calibration property
   and introduces a hidden second source of truth. The
   surrogate also cannot be implemented without a parametric
   model. This is a research question deferred to its own
   ADR.
4. **Implement a stochastic bandit/UCB scheduler in this
   round anyway.** Rejected: bandit updates are stochastic,
   the `config_hash` provenance no longer pins re-runs
   bit-identical, and the audit story
   ([ADR-0005](0005-fail-closed-audit-code-policy.md))
   requires every per-round decision to be reconstructable
   from the frozen config alone. A stochastic arm draw breaks
   that invariant.

## Decision Outcome

Chosen option: **option 1 — three new deterministic
`SchedulerProtocol` implementations, one of which consumes
the runner's per-round feedback via a new optional hook.**

### Phase 1: two trivial closed-form families

**`PolynomialScheduler`** (`adaptive_reflow/algorithm/scheduler.py`).
Closed form:

    n_cap(r) = n_min + (n_max - n_min) * (1 - u_r ** power)
    u_r = round_in_cycle / max(L - 1, 1)

* `power == 1` — exactly equivalent to
  `LinearScheduler` (sanity check).
* `power > 1` (e.g. `2`) — concave ramp: capacity stays
  high longer, then climbs late. Cosine is the `power == 2`
  approximate; the polynomial family lets us sweep the
  convex/concave shape without changing the family.
* `0 < power < 1` (e.g. `0.5`) — convex ramp: capacity
  climbs quickly early, then plateaus near `n_max` —
  useful for front-loaded exploration followed by
  refinement.

`power` is required to be strictly positive (`power > 0`).
Output is deterministically clipped to `[0, 1]`. Family
identifier: `polynomial`. Registered in `SCHEDULER_REGISTRY`
under `"polynomial"`.

**`SigmoidScheduler`** (`adaptive_reflow/algorithm/scheduler.py`).
Closed form:

    n_cap(r) = n_min + (n_max - n_min) * sigmoid(steepness * (u_r - midpoint))
    sigmoid(z) = 1 / (1 + exp(-z))

* `steepness == 0` — degenerate: `n_cap = (n_min + n_max) / 2`
  for every round (equivalent to a constant).
* Small `steepness` — gradual (smooth, near-linear) curve.
* Large `steepness` — near-step function at the chosen
  `midpoint`.
* `midpoint == 0.5` is the symmetric midpoint; smaller /
  larger values shift the ramp's transition earlier /
  later in the cycle.

`steepness` may be any finite real (a negative steepness
flips the ramp direction); `midpoint` is unconstrained.
Both participate in the frozen `config_hash`. Family
identifier: `sigmoid`. Registered in `SCHEDULER_REGISTRY`
under `"sigmoid"`.

### Phase 2: headline novelty — `ConvergenceAdaptiveScheduler`

**`ConvergenceAdaptiveScheduler`** is a thin PID-lite
wrapper around a base `CosineAnnealScheduler`. It maintains
a bounded *shift* on the cosine's effective `u_r`, updated
by the runner's per-round `W2` feedback. Concretely:

1. `sample(...)` asks the base scheduler for the canonical
   `(u_r, n_cap)`, then shifts:
       effective_u_r = clip(u_r + self._shift, 0, 1)
   and re-derives `n_cap` from the base cosine closed-form
   (`n_cap_for_round`) applied to a synthetic round index
   `round(effective_u_r * (L - 1))`. The closed-form cosine
   stays the single source of truth.
2. `record_round_feedback(round_in_cycle, metrics)`
   consumes `metrics["W2"]`:
   * Non-finite `W2` is ignored — neither the EMA nor the
     `w2_history` is updated, so a broken oracle cannot
     poison the controller.
   * The EMA is updated
     `smoothed = ema * w2 + (1 - ema) * prev_smoothed`.
   * With at least two samples, the controller computes
         ratio = w2[-1] / w2[-2]
         delta = w2[-1] - w2[-2]
         shift_update = kp * (1.0 - ratio) - kd * delta
         shift = clip(shift + shift_update, -shift_max, +shift_max)
3. **Interpretation:**
   * When W2 is improving (`delta < 0`, `ratio < 1`):
     `shift_update > 0` → shift grows → push toward refinement
     (later in the cycle).
   * When W2 is worsening (`delta > 0`, `ratio > 1`):
     `shift_update < 0` → shift shrinks → push toward
     exploration (earlier in the cycle).
   * When W2 stalls (`delta == 0`, `ratio == 1`):
     `shift_update = 0` → shift holds.

The shift is hard-bounded in `[-shift_max, +shift_max]`
(default `0.15`) so a single bad round cannot blow up the
schedule. Defaults: `kp = 0.10`, `kd = 0.05`,
`shift_max = 0.15`, `ema = 0.30`. All four participate in
the frozen `config_hash` (along with `base.config_hash()`),
so two schedulers with different gains remain
distinguishable in provenance.

Critically: the wrapper is **deterministic and no-train**. No
gradient, no bandit arm, no online learning step. The
controller is a 2-line gain-multiply-and-clip rule. When
no feedback is available (e.g. the runner is bypassed in a
test), the scheduler reduces to plain cosine with
`shift = 0`, so the round-trip remains sane.

Family identifier: `convergence_adaptive_cosine`. Registered
in `SCHEDULER_REGISTRY` under `"convergence_adaptive"`. The
family identifier (not the registry key) is the audit-visible
one, matching `schedule_family()`-style output used elsewhere
in the framework.

### Phase 3: optional feedback hook

The four non-adaptive families (`cosine`, `constant`,
`linear`, `exponential`) and the two new trivial families
(`polynomial`, `sigmoid`) implement
`record_round_feedback(round_in_cycle, metrics)` as a
**default no-op**. The runner's feedback call is gated on
`hasattr(self._scheduler, "record_round_feedback")` so that
third-party schedulers that pre-date this hook continue to
work unmodified. This preserves byte-for-byte backwards
compatibility — the runner's behaviour, in the absence of
`record_round_feedback`, is identical to ADR-0011's
behaviour.

### Phase 4: ablation row extension

`tools/run_ablation.py` gains **four** new rows
(`multi_round_polynomial_schedule_derived`,
`multi_round_sigmoid_schedule_derived`,
`multi_round_convergence_adaptive_schedule_derived`,
`multi_round_cosine_adaptive_driver`) which paired with the
existing four rows (`single_pass`,
`multi_round_constant_beta_05`,
`multi_round_cosine_anneal`, `multi_round_no_restart`) bring
the grid from 8 rows to **16 rows** (8 configs x 2 targets).
The convergence-adaptive row drives the runner's loop
*directly* (mirroring the runner's body) so that the W2
metric computed by the evaluator can be fed back to the
scheduler via `record_round_feedback`. The other rows use
the same `ReInferenceRunner` path as ADR-0011.

### Consequences

Positive:

* `SchedulerProtocol` now has **seven** registered families
  (`cosine`, `constant`, `linear`, `exponential`,
  `polynomial`, `sigmoid`, `convergence_adaptive`).
  `SCHEDULER_REGISTRY` and `build_scheduler(family,
  **kwargs)` dispatch all seven.
* The ablation grid extends to **16 rows** and answers new
  questions: *does schedule shape matter on harder targets?*
  (polynomial / sigmoid vs cosine) and *does feedback-driven
  shift help?* (convergence-adaptive vs cosine).
* `record_round_feedback` is the first feedback hook in
  the algorithm layer. It is optional, gated on `hasattr`,
  and the four non-adaptive implementations make it a
  default no-op — so no existing caller, test, or import
  path breaks.
* `ConvergenceAdaptiveScheduler` introduces a non-train,
  deterministic feedback-driven schedule without
  requiring a score model, a bandit, or online learning.
  It is a *small algorithmic surface* (one 250-line class)
  with a *bounded shift* (default `[-0.15, +0.15]`) so the
  scheduler cannot run away under a broken oracle.

Negative:

* The ablation cost grows. The convergence-adaptive row
  needs the runner's loop inlined, not delegated, because
  the W2 metric produced *by the evaluator* needs to be
  fed back *to the scheduler* via
  `record_round_feedback`. The runner already supports
  this; the row just exercises the path.
* `ConvergenceAdaptiveScheduler`'s PID-lite gains (`kp`,
  `kd`, `shift_max`, `ema`) are **untuned**. The ablation
  defaults are principled (small gains, hard-bounded
  shift), not optimal. Tuning the gains is a follow-up
  research question, not in scope for this ADR.
* Karras EDM `sigma(t)` is rejected for this round, but
  the rejection is *deferred*, not *decline*: the
  research question ("can we score-match our way to a
  better per-round noise schedule?") is open.
* Bandit / RL schedules remain rejected because they
  break determinism. A future ADR that proposes a
  frozen-seed stochastic seam could revisit them.
* Three new ScheduleSample `family` strings
  (`"polynomial"`, `"sigmoid"`,
  `"convergence_adaptive_cosine"`) and one new ablation
  row per family need to be indexed by
  `tools/check_docs_against_code.py` and by the
  doc-drift scanner.

### Confirmation

The decision is enforced by:

* `adaptive_reflow/algorithm/scheduler.py` —
  `PolynomialScheduler`, `SigmoidScheduler`,
  `ConvergenceAdaptiveScheduler`; `SchedulerProtocol`'s
  `record_round_feedback` default no-op; `SCHEDULER_REGISTRY`
  extended with the three new keys; `__all__` updated.
* `adaptive_reflow/algorithm/runner.py` — feedback wiring
  at line 475: `if hasattr(self._scheduler,
  "record_round_feedback"): self._scheduler.record_round_feedback(r, metric)`
  fires once per round, after the metric promotion.
* `tests/test_algorithm/test_scheduler.py` — conformance,
  determinism, and equivalence-to-legacy regression tests
  for the three new families (closed-form invariants,
  `record_round_feedback` no-op on non-adaptive, PID-lite
  bounded shift on adaptive).
* `tools/run_ablation.py` — four new rows; the
  convergence-adaptive row mirrors the runner's loop.
* `docs/ABLATION.md` — empirical findings paragraph on the
  schedule-shape axis and the feedback axis.
* `CHANGELOG.md` — the new `[Unreleased] - New scheduler
  families` section.
* `ROADMAP.md` — "New scheduler families" line moved to
  completed.

## More Information

* [docs/adr/0011](0011-algorithm-abstractions.md) — the
  algorithm-layer abstraction that this ADR composes over.
* [docs/adr/0010](0010-cosine-driven-memory-fraction.md) —
  the cosine-driven memory fraction that the new families
  reproduce via `ScheduleDerivedPolicyDriver`.
* `ARCHITECTURE.md` — the top-down layer map.
* Karras et al. (2022), *Elucidating the Design Space of
  Diffusion-Based Generative Models* (NeurIPS) — the
  `sigma(t)` parameterisation that this ADR rejects for
  this round.
* Loshchilov & Hutter (2017), *SGDR: Stochastic Gradient
  Descent with Warm Restarts* — the original cosine
  annealing schedule.
