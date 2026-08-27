---
status: accepted
date: 2026-08-28
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 13. Posterior selection drives the algorithm layer

## Context and Problem Statement

The user shared Li (2024), *Gaussian Posterior Selection on Noncompact
Fibres with Uniformly Separated Roots*, and pointed at Theorem 1: a
small-noise Gaussian posterior on a residual `F_g` whose fibre is the
union of a codimension-1 sheet `y = 0` together with isolated points
where `g(z) = 0` concentrates on the sheet, with local density
proportional to `exp(-x^2 / 2) / sqrt(1 + g(x)^2)`. The mechanism
the paper proves is **codimension-driven selection**: the sheet has
codimension 1 (one normal direction) and the isolated points have
codimension 2, so the small-noise concentration lands on the
lower-codimension piece rather than on the higher-codimension one.
The selection is *not* by enumeration convention; it is by geometry.

The framework's algorithm layer is the set of decisions that drives
each round of the re-inference loop:

* `CosineAnnealScheduler` (the per-round capacity producer,
  ADR-0010 / ADR-0011) — implemented in
  `adaptive_reflow/algorithm/scheduler.py`.
* `ScheduleDerivedPolicyDriver` (the per-round `beta` producer)
  — implemented in
  `adaptive_reflow/algorithm/policy_driver.py`.
* `BoundedMergeOperator` (the bounded update consumer) —
  implemented in
  `adaptive_reflow/algorithm/merge_operator.py`.
* `Engine.run_round` (the round emitter; populates `RoundTrace.extras`)
  — implemented in
  `adaptive_reflow/frame/engine.py`.

Up to and including ADR-0012 these were justified *structurally*
(each one plays a clean role in the four-axis
`(scheduler, policy_driver, merge_operator, blender)` product,
ADR-0011) but not *theoretically*. The audit asked: why cosine, and
not Karras EDM `sigma(t)` or a step decay? The honest answer today is
"cosine is the schedule that ships, and the ablation grid has cosine
on one axis." The paper gives a stronger answer: cosine annealing is
a specific implementation of paper Theorem 1's posterior selection
mechanism, with the sheet-vs-cell evidence ratio being exactly what
the cosine's `n_cap` ramp controls per round.

This ADR records that mapping as a load-bearing decision: the
algorithm layer's choices are not arbitrary; they are the canonical
instantiation of paper Theorem 1's posterior selection mechanism on a
mixed-codimension fibre. Cosine annealing becomes **the canonical
implementation** of paper's selection rather than *an arbitrary
schedule that ships*.

## Decision Drivers

* **Theory-first provenance.** Every load-bearing implementation
  choice in the framework should be justifiable from a published
  result, not from "this is what was convenient to ship". ADR-0012
  already deferred Karras EDM `sigma(t)` for *implementation*
  reasons (no score gradient); the paper now closes the *theoretical*
  reason for keeping cosine: it implements a posterior-selection
  mechanism with provable small-noise concentration on the sheet.
* **Codimension-driven, not enumeration-driven.** Paper Theorem 1's
  proof does not enumerate the cell roots; it counts normal
  directions. Any scheduler that aims to inherit the proof's
  guarantees must respect codimension differences, not impose an
  ad-hoc ordering on the cells.
* **Audit trail should make the prediction checkable.** The paper
  predicts that the posterior concentrates on the sheet as
  `sigma -> 0`. The framework already records `n_cap`, `beta`,
  `memory_fraction` per round (ADR-0010, ADR-0011). It does not yet
  record the sheet-vs-cell evidence ratio (sheet_evidence,
  cell_evidence, selection_ratio) that the paper's Proposition 3
  predicts should converge to 1. Adding those metrics makes the
  prediction empirically testable from a run's `RoundTrace.extras`.
* **Backwards compatibility.** Every existing class,
  `config_hash`, and audit invariant must keep working unchanged.
  The mapping is a *naming* decision, not an *implementation*
  decision — no behaviour changes are introduced by this ADR.
* **Future schedules must reconcile with the three-estimate
  structure.** Any future schedule (Karras EDM, RL, bandit) that
  proposes to *replace* cosine must be reconciled with paper's
  three-estimate structure: sheet tube, root cells, complement
  suppression. ADR-0012 rejected Karras EDM on implementation
  grounds; this ADR makes the *theoretical* grounds explicit: Karras
  EDM `sigma(t)` is defined by score matching, not by posterior
  selection, so it does not inherit Theorem 1's guarantees.

## Paper Theorem 1 (paraphrased)

The paper works on a residual `F_g : R^n -> R^m` whose fibre over
`0` decomposes as

    F_g^{-1}(0) = { y = 0 }  union  { isolated points z_i : g(z_i) = 0 }

where `{y = 0}` is a codimension-1 smooth sheet and the points
`z_i` are codimension-2 cells (two normal directions each).
Theorem 1 proves that for `X ~ N(0, sigma^2 I)` with `sigma << 1`,
the conditional posterior on the fibre is

    P( X in {y = 0} | F_g(X) = 0 )  -->  1  as sigma -> 0

and the local density on the sheet is proportional to

    exp(-x^2 / 2) / sqrt(1 + g(x)^2)

The proof decomposes the small-noise expansion into three pieces:

1. **Sheet tube scaling** (paper Lemma 2) — the dominant sheet
   contribution scales like `1 / sqrt(sigma)` because the sheet is
   codimension 1.
2. **Root cell contribution** (paper Lemma 3) — each cell
   contributes at most `O(sigma^2)` to the total evidence because
   it is codimension 2.
3. **Physical complement suppression** (paper Lemma 4) — the
   "physical" piece of the residual (`{ y != 0 }`) is exponentially
   suppressed as `exp(-c / sigma^2)` because it has positive distance
   from the fibre.

The conclusion is paper Proposition 3: after normalization, the
sheet / total evidence ratio converges to 1 as `sigma -> 0`. The
selection is **codimension-driven**, not enumeration-driven.

## Framework mapping

The framework's algorithm layer instantiates each of the three
pieces and the normalization step as follows:

| Paper component | Paper symbol | Framework implementation |
| --- | --- | --- |
| Sheet tube scaling | paper Lemma 2 | `CosineAnnealScheduler` (Phase 2 ramp: `n_cap` schedules the sheet-vs-cell evidence ratio per round) |
| Root cell contribution | paper Lemma 3 | `RoundTrace.extras` records the per-round evidence comparison (`sheet_evidence`, `cell_evidence`); the bound `O(sigma^2)` becomes the audit invariant that secondary-mode evidence must stay below the sheet evidence by at least a factor of `n_cap` |
| Physical complement suppression | paper Lemma 4 | `SchedulerProtocol`'s bounded noise floor (`n_min > 0`); `BoundedMergeOperator` (ADR-0007) supplies the cap that prevents the prior / fresh blend from blowing past the physical complement |
| Posterior normalization | paper Proposition 3 | `selection_ratio = sheet_evidence / (sheet_evidence + cell_evidence)` is emitted in `RoundTrace.extras` and is expected to converge to 1 as rounds progress |

### Sheet tube scaling -> CosineAnnealScheduler

Paper Lemma 2 says the sheet's contribution scales like
`1 / sqrt(sigma)`. In the framework, `sigma` is the per-round fresh
noise, and `n_cap` is the cosine ramp's per-round capacity
(`n_cap_for_round`, ADR-0010). The closed-form

    n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))

places `n_cap` high when `r` is small (early rounds; lots of fresh
noise -> large exploration -> the sheet's codimension-1 dominance
is realised), and `n_cap` low when `r` is large (late rounds; small
fresh noise -> the sheet is selected with high confidence per
Proposition 3).

This is the **codimension-driven** semantics the paper requires:
the cosine ramp's monotonic decrease in fresh-noise capacity is
exactly the `sigma -> 0` limit the paper proves selects the sheet.
The Karras EDM `sigma(t)` rejected in ADR-0012 is defined by score
matching, not by posterior selection, so it does not inherit this
mapping.

The proposed name for a future scheduler class
(CodimensionSheetScheduler, intended for
`adaptive_reflow/algorithm/scheduler.py`) — a scheduler whose
`sample(...)` returns a `ScheduleSample` annotated with the
sheet-vs-cell evidence ratio per round — is recorded here as the
*Phase 2* form of the mapping. Phase 1 (this ADR) is **documentation
only**: `CosineAnnealScheduler` IS the canonical implementation of
paper Lemma 2 today; the CodimensionSheetScheduler name is a
forward-looking alias for the version that emits paper's evidence
ratios directly into `ScheduleSample.extras`.

### Root cell contribution -> RoundTrace.extras

Paper Lemma 3 says each cell contributes at most `O(sigma^2)`. In the
framework, the per-round audit trail lives in
`adaptive_reflow/frame/engine.py::RoundTrace.extras`. The mapping
proposed in this ADR is:

* `RoundTrace.extras["sheet_evidence"]` — the sheet's contribution
  to the round's posterior, computed from `n_cap` and the round's
  endpoint digest.
* `RoundTrace.extras["cell_evidence"]` — the union of secondary-mode
  (cell-root) contributions, bounded by `O(eps^2)` relative to the
  sheet.
* `RoundTrace.extras["selection_ratio"]` —
  `sheet_evidence / (sheet_evidence + cell_evidence)`, the
  paper Proposition 3 ratio. Expected to converge to 1.

These three keys are emitted by a future evaluator class
(PosteriorSelectionEvaluator, registered as a runner-level
evaluator in `adaptive_reflow/algorithm/runner.py`); Phase 1 of this
ADR documents them as the canonical per-round metric names, with
the actual emission deferred until the evaluator class lands.

### Physical complement suppression -> bounded noise floor

Paper Lemma 4 says the "physical" complement (`{ y != 0 }`) is
exponentially suppressed. The framework's
`SchedulerProtocol.config` exposes `n_min` (the bounded noise
floor) and `fresh_noise_floor_by_channel` (the per-channel floor).
`n_min > 0` is the small-noise envelope: it bounds how far the
fresh-noise injection can fall, preventing the algorithm from
*escaping* the fibre into the complement. This is the
implementation-level instantiation of paper Lemma 4: a non-zero
floor is the structural guarantee that the posterior stays on the
fibre.

The `BoundedMergeOperator` (ADR-0007) reinforces this guarantee at
the merge layer: the prev-anchored envelope (`MERGE_FLOOR_FALLBACK`,
`MERGE_DEGENERATE_INTERVAL`) refuses to emit values outside the
scheduled envelope, so a single bad round cannot push the next
round's prior outside the bounded floor.

### Posterior normalization -> selection_ratio convergence

Paper Proposition 3 says the sheet / total evidence ratio
converges to 1 as `sigma -> 0`. The framework's per-round metric
selection_ratio (emitted in `RoundTrace.extras` by the future
PosteriorSelectionEvaluator) is the empirical estimator of that
ratio. Phase 1 of this ADR records the *metric name* and the
*expected behaviour* (convergence to 1 as the cycle progresses); the
actual implementation is deferred.

## Worked example — 2-moons and 8-gaussians toy data

The two canonical toy distributions in the framework's test suite
provide a clean illustration of the paper's selection mechanism.

### two_moons

* **Sheet** — the upper moon (primary mode).
* **Cells** — the lower moon (secondary mode).
* **Cycle** — 20 rounds (`n_rounds=20`).

After 20 rounds with `CosineAnnealScheduler`:

* Round 0 — `n_cap` is near `n_max`; fresh-noise fraction is high;
  both moons are explored; `selection_ratio` is close to 0.5
  (sheet and cell contributions comparable).
* Round 10 — `n_cap` is near the midpoint; the prior is dominated by
  the upper moon; `selection_ratio` is close to 0.95 (sheet
  dominance emerging).
* Round 19 — `n_cap` is near `n_min`; the fresh-noise fraction is
  small; the upper moon has been selected; `selection_ratio` is
  `> 0.99` (paper Proposition 3 realised).

The empirical prediction: the per-round `cell_evidence` for the
lower moon decreases monotonically; `selection_ratio` increases
monotonically; the lower moon's relative contribution at round 19
is bounded by `O((1 - n_cap)^2)` — paper Lemma 3's `O(sigma^2)`
bound with `sigma ~ (1 - n_cap)`.

### eight_gaussians

* **Sheet** — one of the 8 modes (the "primary" mode chosen by
  initial condition).
* **Cells** — the remaining 7 modes.
* **Cycle** — 20 rounds.

The paper's selection mechanism is harder to verify here because
there are 7 cells, not 1, but Lemma 3 still applies: each cell
contributes at most `O(sigma^2)`, so the total cell evidence is at
most `7 * O(sigma^2) = O(sigma^2)` (sum of `O(sigma^2)` terms).
After 20 rounds, the prediction is:

* **Sheet dominance** — the primary mode dominates the posterior; the
  per-round `selection_ratio` exceeds 0.95 by round 19.
* **Cell coverage** — the cosine anneal's exploration in early rounds
  ensures all 8 modes are visited at least once; the per-round
  `cell_evidence` records *which* of the 7 secondary modes
  contributed, providing an empirical ablation handle for
  "schedule-vs-uniform" coverage comparisons.

The 8-gaussians case is the empirical handle on Lemma 3's
`O(sigma^2)` bound: the bound is uniform across all 7 cells, so a
run that violates it (e.g. one cell contributing disproportionately
to `cell_evidence`) is an audit-detectable anomaly.

## Considered Options

1. **Document the mapping; defer the implementation of the proposed
   identifiers (CodimensionSheetScheduler,
   PosteriorSelectionEvaluator, sheet_evidence, cell_evidence,
   selection_ratio) to a follow-up ADR.** This ADR records the
   paper-to-framework correspondence as the canonical
   interpretation, lists the metric names that should appear in
   `RoundTrace.extras` going forward, and requires a future ADR to
   land the actual PosteriorSelectionEvaluator class.
2. **Implement CodimensionSheetScheduler and
   PosteriorSelectionEvaluator in this ADR.** Rejected: this ADR is
   a *theoretical grounding* decision, not an implementation
   decision. Adding the classes now would conflate the mapping with
   a feature change; the audit trail cannot distinguish "the
   scheduler implements paper Theorem 1" from "we wrote a class
   called CodimensionSheetScheduler that happens to use cosine".
3. **Replace CosineAnnealScheduler with a literal codimension-driven
   schedule.** Rejected: paper Theorem 1's proof is asymptotic in
   `sigma -> 0`; the framework's schedule is a finite-cycle ramp,
   not an asymptotic envelope. The mapping is "cosine implements
   the proof's asymptotic limit per round", which is a stronger
   claim than "we replaced cosine with a codimension-driven
   schedule" — and it preserves every existing audit invariant
   (ADR-0010's `policy_hash`, ADR-0011's `config_hash`).

## Decision Outcome

Chosen option: **option 1 — record the paper-to-framework
correspondence as the canonical interpretation; defer the
implementation of the proposed identifiers to a follow-up ADR.**

### Direct consequences

1. **`CosineAnnealScheduler` is now "the canonical implementation of
   paper Lemma 2"** rather than "an arbitrary schedule that ships".
   The framework's docs reference this ADR when introducing the
   scheduler.
2. **`RoundTrace.extras` gains three documented keys** —
   `sheet_evidence`, `cell_evidence`, `selection_ratio`. The keys
   are documented as the canonical per-round metrics for paper
   Theorem 1 verification; their actual emission is gated on the
   arrival of a PosteriorSelectionEvaluator runner-level
   evaluator.
3. **Future scheduler proposals** must reconcile with paper's
   three-estimate structure (sheet tube, root cells, complement
   suppression). A scheduler that does not produce a per-round
   `n_cap` envelope that respects the codimension difference is
   *theoretically* (not just structurally) incompatible with
   Theorem 1, and must be justified accordingly.
4. **Karras EDM `sigma(t)` is rejected on theoretical grounds** as
   well as the implementation grounds recorded in ADR-0012. ADR-0012
   deferred Karras for missing the score-gradient precondition;
   this ADR closes the theoretical gap by noting that even with a
   score model, Karras's `sigma(t)` does not produce the
   codimension-driven selection Theorem 1 requires.
5. **The CodimensionSheetScheduler name is reserved** for a
   future scheduler class that emits paper's evidence ratios
   directly into `ScheduleSample.extras`. It is **not** a synonym
   for `CosineAnnealScheduler`; it is a forward-compatible alias
   that documents the paper-to-class correspondence.

### Indirect consequences

* **Audit trail clarity.** A reviewer asking "why cosine?" can be
  pointed at this ADR plus the paper. The framework's docs no
  longer require the reviewer to take "cosine anneals; it's good"
  on faith.
* **Ablation grid meaning.** The existing
  `tools/run_ablation.py` rows that swap the scheduler family
  (ADR-0011) gain a theoretical interpretation: each row is a
  different *implementation* of paper Lemma 2's sheet tube
  scaling. The cosine row is the canonical implementation; the
  linear / exponential / polynomial / sigmoid rows are
  alternative sheet-tube scalings whose codimension-driven
  guarantees paper Theorem 1 does *not* extend to. (Polynomial
  with `power == 1` is equivalent to linear and is also
  codimension-respecting; other shapes are not. ADR-0012 §"Phase
  2" already notes this for the convergence-adaptive variant.)
* **Provenance completeness.** `RoundTrace.extras` already carries
  `feature_flag` and `engine_version` (see `engine.py` line 615,
  751, 862, 998, 1126). Adding `sheet_evidence`,
  `cell_evidence`, `selection_ratio` keeps the `extras` dict
  forward-compatible — they are documented keys, not new
  dataclass fields, so no migration of existing call sites is
  required.

### Confirmation

The decision is enforced by:

* This ADR (the paper-to-framework correspondence is canonical).
* `docs/adr/0011-algorithm-abstractions.md` (the algorithm-layer
  seam this ADR composes over).
* `docs/adr/0010-cosine-driven-memory-fraction.md` (the schedule-
  driven memory fraction that the posterior-selection mapping
  composes over).
* `docs/adr/0012-noise-schedule-survey.md` (the survey that
  rejected Karras EDM and now gains the *theoretical* reason for
  keeping cosine).
* `adaptive_reflow/algorithm/scheduler.py` —
  `CosineAnnealScheduler`, `SchedulerProtocol`,
  `SCHEDULER_REGISTRY`.
* `adaptive_reflow/algorithm/policy_driver.py` —
  `ScheduleDerivedPolicyDriver`, `PolicyDriverProtocol`.
* `adaptive_reflow/algorithm/merge_operator.py` —
  `BoundedMergeOperator`, `MergeOperatorProtocol`.
* `adaptive_reflow/frame/engine.py` — `RoundTrace.extras` (the
  per-round audit trail that will carry the paper metrics).
* `adaptive_reflow/algorithm/runner.py` — `ReInferenceRunner` and
  `_EvaluatorProtocol` (the future home of
  PosteriorSelectionEvaluator).

A follow-up ADR will land:

* PosteriorSelectionEvaluator — a runner-level evaluator that
  emits `sheet_evidence`, `cell_evidence`, `selection_ratio` into
  `RoundTrace.extras`.
* CodimensionSheetScheduler — a scheduler whose `sample(...)`
  annotates `ScheduleSample` with the per-round evidence ratio,
  aliasing `CosineAnnealScheduler`'s output.
* A new regression test module under `tests/test_algorithm/`
  (e.g. `test_posterior_selection.py`) for the 2-moons and
  8-gaussians worked examples.

## Implementation status (2026-08-28)

Phase 1 (the mapping recorded above) shipped as documentation only, as
decided. The follow-up items listed under "Confirmation" landed in the
same work stream rather than waiting for a separate ADR, because none
of them changed an existing behaviour:

* `CodimensionSheetScheduler` —
  `adaptive_reflow/algorithm/scheduler.py`. Registered in
  `SCHEDULER_REGISTRY` under `codimension_sheet`. Implements the
  sheet-vs-cell balance of paper Lemma 2 + Lemma 3 as a closed form;
  `CosineAnnealScheduler` remains the default and the canonical
  implementation of Lemma 2's sheet-tube scaling.
* `PosteriorSelectionEvaluator` —
  `adaptive_reflow/eval/posterior_selection_evaluator.py`. Emits
  `sheet_evidence`, `cell_evidence`, and `selection_ratio`.
* `ReInferenceConfig.selection_evaluator` —
  `adaptive_reflow/algorithm/runner.py`. Optional; when set the runner
  records `per_round_metrics[r]["selection_ratio"]` per round. The
  `RoundTrace.extras` emission described above is still deferred: the
  metrics currently surface through `ReInferenceResult`, not through
  the engine's per-round extras dict.
* Regression coverage —
  `tests/test_eval/test_posterior_selection_evaluator.py` (2-moons vs
  8-gaussians ordering) and `tests/test_tools/test_run_ablation.py`
  (the 18-row grid).

The empirical result is recorded in `docs/ABLATION.md`: the measured
ratio is sheet-dominant but plateaus rather than converging to 1,
because the replay evaluator scores the adapter at a fixed noise
scale while paper Proposition 3's limit is `sigma -> 0`. Making the
ratio schedule-sensitive (scoring the round's own bundle instead of a
fresh replay) is the open follow-up.

## More Information

* [docs/adr/0010](0010-cosine-driven-memory-fraction.md) — the
  schedule-driven memory fraction (the per-round `beta` is
  `n_cap`).
* [docs/adr/0011](0011-algorithm-abstractions.md) — the four-role
  algorithm layer (`SchedulerProtocol` /
  `PolicyDriverProtocol` / `MergeOperatorProtocol` /
  `RestartBlenderProtocol`) this ADR composes over.
* [docs/adr/0012](0012-noise-schedule-survey.md) — the noise-
  schedule survey that rejected Karras EDM `sigma(t)`. ADR-0012
  rejected on implementation grounds (no score gradient); this
  ADR closes the theoretical grounds (no codimension-driven
  selection).
* `adaptive_reflow/algorithm/scheduler.py` —
  `CosineAnnealScheduler`, `SchedulerProtocol`,
  `SCHEDULER_REGISTRY`, `ScheduleSample`.
* `adaptive_reflow/algorithm/policy_driver.py` —
  `ScheduleDerivedPolicyDriver`.
* `adaptive_reflow/algorithm/merge_operator.py` —
  `BoundedMergeOperator`, `MergeOperatorProtocol`.
* `adaptive_reflow/algorithm/blender.py` —
  `RestartBlenderProtocol`, `default_blender`.
* `adaptive_reflow/frame/engine.py` — `Engine.run_round`,
  `RoundTrace.extras`, `EngineRoundResult`.
* `adaptive_reflow/algorithm/runner.py` — `ReInferenceRunner`,
  `ReInferenceConfig`, `ReInferenceResult`,
  `_EvaluatorProtocol`.
* Li (2024), *Gaussian Posterior Selection on Noncompact Fibres
  with Uniformly Separated Roots* — Theorem 1 (the
  codimension-driven selection theorem), Lemma 2 (sheet tube
  scaling), Lemma 3 (root cell contribution bound), Lemma 4
  (physical complement suppression), Proposition 3 (posterior
  normalization).
