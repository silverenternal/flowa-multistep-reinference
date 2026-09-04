---
status: accepted
date: 2026-08-28
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 11. Algorithm abstractions (scheduler / policy driver / merge operator / blender)

## Context and Problem Statement

Up to and including [ADR-0010](0010-cosine-driven-memory-fraction.md)
the framework's *algorithm* was not a layer — it was a set of
hard-wired concrete choices scattered across three packages:

* The per-round capacity was **always** the cosine annealing
  closed form. `adaptive_reflow/schedule/cosine.py::n_cap_for_round`
  was called directly; `CosineScheduleSampler` was the only stateful
  producer of per-round samples.
* The per-round *policy* was **always** "derive `beta` from the
  schedule's `n_cap`". ADR-0010 wired that derivation into
  `Engine.run_round` itself, behind the
  `FinalRestartPolicy.beta_from_schedule` flag. The only alternative
  the framework could express was "turn the derivation off and use
  whatever constant the caller baked into `beta_by_channel`".
* The bounded update operator was **always**
  `adaptive_reflow/frame/merge.py::bounded_merge`. Its prev-anchored
  envelope semantics ([ADR-0007](../ARCHIVE/adr/0007-prev-anchored-bounded-merge.md))
  were reachable only as a module-level function, so there was no seam
  at which a different update rule could be substituted.
* The prior/fresh blend was **always** the linear
  `memory_fraction * prior + (1 - memory_fraction) * fresh` written
  inline inside each adapter's `apply_restart_distribution`.

The consequence was a framework that could express exactly **one**
algorithm. An ablation that wanted to ask "does the *schedule* shape
matter, holding the policy fixed?" could not be written: the schedule
and the policy were the same decision. The `docs/ABLATION.md` grid
produced under ADR-0010 is the evidence — its four rows are four
points on a single axis (rounds x beta-source), not a cross-product,
because the code could not produce a cross-product.

The user's request was explicit: the algorithm layer must become
**abstract and optional**. Cosine annealing should be *one option*,
not *the framework*. The framework should accept any conforming
implementation, and the concrete implementations shipped today
should be one option each.

## Decision Drivers

* **The framework should depend on roles, not implementations.** A
  re-inference loop needs "something that yields per-round capacity"
  and "something that turns capacity into a policy" — it does not
  need cosine, and it does not need `n_cap = 1 - beta`.
* **Ablations are the product.** This is a research project; the
  ability to hold three axes fixed and vary the fourth is the whole
  point. Mix-and-match must be a constructor argument, not a patch.
* **Byte-for-byte back-compat is non-negotiable.** The existing
  behaviour (cosine schedule + schedule-derived beta + bounded merge
  + linear blend) is the *default*, and every existing caller,
  import path, and test must keep working unchanged.
* **Provenance must survive the abstraction.** The audit story
  (`policy_hash`, `applied_policy_hash`) depends on knowing which
  algorithm produced a round. Once the algorithm is pluggable, the
  *identity of the plugin* becomes part of the provenance and must
  be recorded.
* **The seam belongs above the engine, not inside it.** ADR-0010 put
  the beta derivation *inside* `Engine.run_round`. That was the right
  call for one algorithm and the wrong call for many: the engine's
  job is one round through the adapter
  ([ADR-0006](../ARCHIVE/adr/0006-engine-wraps-adapter-pattern.md)), not choosing
  the algorithm that drives the rounds.

## Considered Options

1. **Four `Protocol`s in a new `adaptive_reflow/algorithm/`
   package, plus a `ReInferenceRunner` outer framework that composes
   them around the existing `Engine`.** Concrete implementations
   (cosine, bounded merge, schedule-derived policy, linear blend)
   become one option each behind default factories.
2. **Keep the concrete functions and add `if family == ...`
   branches.** A `schedule_family` string threaded through
   `Engine.run_round` selects the capacity formula; a second string
   selects the merge rule. Rejected: it is a closed set masquerading
   as an abstraction. Every new schedule requires editing the engine,
   the branch set grows combinatorially with the number of axes, and
   third-party algorithms remain impossible.
3. **Subclassing: an abstract base class with a cosine subclass.**
   Rejected for consistency with the rest of the package — the
   universal layer is `Protocol`-based
   ([ADR-0002](0002-typed-contracts-core-boundary.md),
   [ADR-0003](0003-universal-vs-molecular-split.md)) precisely so
   implementations need not import the framework to satisfy it.
   Structural typing keeps the dependency arrow pointing one way.
4. **Plain callables instead of Protocols** (a scheduler as a bare
   round-index-to-capacity function). Rejected: the roles carry state
   (`reset`, `last_sample`) and identity (`schedule_family`,
   `config_hash`) that a bare callable cannot express, and the
   provenance requirement
   above needs that identity.

## Decision Outcome

Chosen option: **option 1 — four `Protocol`s under
`adaptive_reflow/algorithm/`, each with 2-4 concrete
implementations, composed by a new `ReInferenceRunner` outer
framework.**

### The four roles

| Role | Protocol | Default | Alternatives |
| --- | --- | --- | --- |
| Per-round capacity | `SchedulerProtocol` [CLM-019] | `CosineAnnealScheduler` | `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler`, `ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler`, `SequentialScheduler` |
| Bounded update | `MergeOperatorProtocol` [CLM-020] | `BoundedMergeOperator` | `IdentityOperator`, `EMAOperator` |
| Per-round policy | `PolicyDriverProtocol` | `ScheduleDerivedPolicyDriver` | `ConstantPolicyDriver`, `AdaptivePolicyDriver` |
| Prior/fresh blend | `RestartBlenderProtocol` | `LinearBlender` | `DistanceDecayBlender` |

> **Sequential chain** [CLM-021]. `SequentialScheduler`
> (`adaptive_reflow/algorithm/sequential.py`) is the multi-phase
> composition primitive that chains multiple sub-schedulers by round
> range — the `adaptive_reflow` analog of PyTorch's SequentialLR
> composite scheduler. See
> [`docs/sequential-protocol.md`](../sequential-protocol.md) for the
> worked example and [`docs/defaults-matrix.md`](../defaults-matrix.md)
> for the reader-facing scenario-to-config mapping.

* **`SchedulerProtocol`** (`adaptive_reflow/algorithm/scheduler.py`)
  answers "how much fresh-noise capacity does round *r* get?". Its
  surface is `sample(outer_cycle_id, round_in_cycle, target_round)`
  returning a `ScheduleSample`, plus `cycle_length`,
  `schedule_family`, `config_hash`, and `reset`. `ScheduleSample`
  carries `memory_fraction()` and an
  `as_cosine_schedule_sample()` bridge that yields the contracts-layer
  `CosineScheduleSample`, so every scheduler — including the
  non-cosine ones — feeds the existing `FinalRestartPolicy` and
  engine path unchanged.
* **`MergeOperatorProtocol`**
  (`adaptive_reflow/algorithm/merge_operator.py`) answers "given
  `prev`, `dynamic`, and a cap, what is the emitted value?".
  `BoundedMergeOperator` is the prev-anchored envelope of ADR-0007
  wrapped as an object, preserving its audit codes
  (`MERGE_DEGENERATE_INTERVAL`, `MERGE_FLOOR_FALLBACK`,
  `MERGE_PREV_ANCHORED_TO_LAST_EMITTED`) and its `MergeAuthorityError`
  fail-closed contract verbatim.
* **`PolicyDriverProtocol`**
  (`adaptive_reflow/algorithm/policy_driver.py`) answers "given this
  round's schedule sample, what is the applied `FinalRestartPolicy`?".
  This is the seam that ADR-0010 lacked: `ScheduleDerivedPolicyDriver`
  reproduces the ADR-0010 override exactly, `ConstantPolicyDriver`
  pins `beta` regardless of the schedule, and `AdaptivePolicyDriver`
  reacts to the prior round's endpoint digest.
* **`RestartBlenderProtocol`** (`adaptive_reflow/algorithm/blender.py`)
  answers "how are prior and fresh combined?". `LinearBlender` is the
  incumbent formula; `DistanceDecayBlender` weights the blend by the
  prior/fresh distance under a temperature.

Each implementation exposes a `config_hash` (and a `schedule_family` /
`driver_family` / `blender_family` label) so the *choice of algorithm*
is recoverable from a run's provenance.

### The outer framework

`adaptive_reflow/algorithm/runner.py::ReInferenceRunner` is the new
outer framework. It takes an adapter, the four algorithm objects
(each defaulting to its default factory), an optional evaluator, and
an optional `Engine`; `ReInferenceConfig` supplies `n_rounds`,
`outer_cycle_id`, `target_round`, `seed`, and `channels`. Per round
it samples the scheduler, asks the driver for the applied policy,
calls `Engine.run_round`, and asks the evaluator for the oracle. It
returns a `ReInferenceResult` carrying the per-round `RoundTrace`
tuple, the endpoints array, `per_round_metrics`, and
`algorithm_signatures` — the `{component: config_hash}` provenance
map.

The layering is explicit: `ReInferenceRunner` is the **outer** loop
(many rounds, pluggable algorithms), `Engine` remains the **inner**
step (one round through the adapter). ADR-0006's "engine wraps
adapter" invariant is untouched; the runner wraps the engine.

### Cosine is now one option

`CosineAnnealScheduler` is *an implementation of*
`SchedulerProtocol`, not the framework. Nothing in
`adaptive_reflow/algorithm/` requires cosine annealing. The
`SCHEDULER_REGISTRY` mapping and the `build_scheduler(family,
**kwargs)` factory let a family be selected by string (from a config
file, a CLI flag, or an ablation sweep); `default_cosine_scheduler`,
`default_policy_driver`, `default_bounded_merge_operator`, and
`default_blender` supply the drop-in defaults that preserve today's
behaviour.

### Consequences

Positive:

* The framework can express **any** `(scheduler, policy_driver,
  merge_operator, blender)` combination. The space is a product, not
  a list.
* Mix-and-match ablations are one-liners. `tools/run_ablation.py`
  now carries a row — `multi_round_cosine_constant_driver` (cosine
  scheduler paired with `ConstantPolicyDriver`) — that was
  **impossible to write in the old code**, because the old engine
  either applied the schedule-derived `beta` or the caller's constant
  and never the cross-product. That row is the executable proof that
  the abstraction bought expressivity rather than indirection.
* Provenance improved: `algorithm_signatures` records which algorithm
  produced a run, so two runs that differ only by scheduler family are
  distinguishable after the fact.
* Third-party algorithms need no framework import. Structural typing
  means a conforming class in a downstream repo is accepted as-is.

Negative:

* The package grows by ~3,000 lines across five modules. The
  abstraction is only worth that cost while more than one
  implementation per role is actually exercised — hence the 2-4
  implementations per role shipped here, not empty seams.
* There are now two ways to run a round: directly via `Engine` (the
  ADR-0010 path, still supported) and via `ReInferenceRunner`. The
  duplication is deliberate during migration but is a drift risk;
  the runner path is canonical for new multi-round code.
* `ScheduleSample.as_cosine_schedule_sample()` means non-cosine
  schedulers are carried through the contracts layer inside a
  *cosine-named* dataclass. This is a naming wart inherited from the
  contracts layer; renaming `CosineScheduleSample` is deferred rather
  than done here, to keep this change behaviour-preserving.
* `AdaptivePolicyDriver` derives its adjustment from an endpoint
  digest, so its output is deterministic but not continuous in the
  state. It is an existence proof for the state-dependent driver
  seam, not a tuned algorithm.

Backwards compatibility is total: `CosineScheduleSampler`,
`n_cap_for_round`, `bounded_merge`, and `bounded_merge_with_schedule`
remain importable from their existing modules with unchanged
behaviour, and the ADR-0010 engine-level override still fires for
callers who drive `Engine.run_round` directly.
`CosineScheduleSampler` now delegates to `CosineAnnealScheduler` and
emits a `DeprecationWarning` pointing at the algorithm-layer
replacement; its computed values are unchanged.

### Confirmation

The decision is enforced by:

* `adaptive_reflow/algorithm/scheduler.py` — `SchedulerProtocol`,
  `CosineAnnealScheduler`, `ConstantScheduler`, `LinearScheduler`,
  `ExponentialScheduler`, `SCHEDULER_REGISTRY`, `build_scheduler`.
* `adaptive_reflow/algorithm/merge_operator.py` —
  `MergeOperatorProtocol`, `BoundedMergeOperator`, `IdentityOperator`,
  `EMAOperator`.
* `adaptive_reflow/algorithm/policy_driver.py` —
  `PolicyDriverProtocol`, `ScheduleDerivedPolicyDriver`,
  `ConstantPolicyDriver`, `AdaptivePolicyDriver`.
* `adaptive_reflow/algorithm/blender.py` — `RestartBlenderProtocol`,
  `LinearBlender`, `DistanceDecayBlender`.
* `adaptive_reflow/algorithm/runner.py` — `ReInferenceRunner`,
  `ReInferenceConfig`, `ReInferenceResult`.
* `tests/test_algorithm/test_scheduler.py`,
  `tests/test_algorithm/test_merge_operator.py`,
  `tests/test_algorithm/test_policy_driver.py`,
  `tests/test_algorithm/test_blender.py`,
  `tests/test_algorithm/test_runner.py` — per-role conformance,
  determinism, and equivalence-to-legacy regression tests.
* `tools/run_ablation.py` — the runner-driven grid including the
  mixed `multi_round_cosine_constant_driver` row.

## More Information

* [docs/adr/0006](../ARCHIVE/adr/0006-engine-wraps-adapter-pattern.md) — the inner
  engine/adapter invariant that the outer runner composes over.
* [docs/adr/0007](../ARCHIVE/adr/0007-prev-anchored-bounded-merge.md) — the
  prev-anchored envelope semantics that `BoundedMergeOperator`
  preserves.
* [docs/adr/0010](0010-cosine-driven-memory-fraction.md) — the
  schedule-driven memory fraction, now reproduced by
  `ScheduleDerivedPolicyDriver` as *one* driver among several.
* `ARCHITECTURE.md` — the top-down layer map (outer framework /
  algorithm / protocol / contracts / foundation).
