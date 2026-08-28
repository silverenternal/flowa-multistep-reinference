---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 10. Cosine-driven memory fraction (driver → runner → engine)

## Context and Problem Statement

The `adaptive_reflow` framework's `apply_restart_distribution`
boundary (the universal `FlowMatchingODEAdapter` Protocol hook that
every adapter implements) blends the prior endpoint with fresh noise
via a per-round `memory_fraction`. The adapter implements the blend
as

```
memory_fraction = 1.0 - beta
x0_new = memory_fraction * prior + (1 - memory_fraction) * fresh
```

where `beta` is read from `policy.beta_by_channel[channel]`. The
canonical algorithm described in the framework documentation says the
per-round `memory_fraction` should be *driven by the cosine
schedule* — specifically, the schedule's `n_cap` (fresh-noise
capacity) is the per-round fresh-noise fraction, and the memory
fraction is its complement.

The schedule supplies the *capacity*; **the driver transforms `n_cap`
into `beta`**; **the runner runs the merge operator over the
driver's `beta`**; **the engine applies the policy verbatim** (the
engine is no longer the source of `beta_by_channel` — it only
validates that the policy is well-formed). This split is the
canonical driver ↔ runner ↔ engine chain; the engine override is a
legacy back-compat path that has been removed from the canonical
driver path.

Before this ADR the cosine schedule's `n_cap` did *not* drive the
adapter-level memory fraction. The schedule's `n_cap` was consumed
only at the *bounded merge* layer (`adaptive_reflow.frame.merge.
bounded_merge_with_schedule`), where it served as the *cap* on a
bounded update over `prev` and `dynamic` fractions. The
adapter-level blend, by contrast, read `beta` directly from the
caller-supplied `policy.beta_by_channel` and never consulted the
schedule. Callers who wanted cosine-annealed memory fractions had
to compute the per-round beta themselves and thread it through a
freshly minted `FinalRestartPolicy` every round — exactly the kind
of plumbing the framework's closed schedule family is supposed to
eliminate.

The user's audit asked three questions:

1. Where is `policy.beta_by_channel["xy"]` set? *Externally, in
   tests, as a constant per round.*
2. Where is `cosine_schedule.n_cap` produced? *In
   `n_cap_for_round` and consumed only by `bounded_merge_with_schedule`.*
3. Where is the actual blend? *In
   `TwoDimFMAdapter.apply_restart_distribution` /
   `ToyGaussianAdapter.apply_restart_distribution`, where `beta` is
   read from the supplied policy verbatim.*

The audit confirmed the algorithmic gap: the cosine schedule did
not drive the per-round memory fraction; the framework's
documented behavior was not wired.

## Decision Drivers

* The framework's closed schedule family
  (`constant` / `linear` / `cosine_no_restart` /
  `cosine_guarded_restart`) is the canonical source of per-round
  capacity. The user-supplied `policy.beta_by_channel` is supposed
  to *carry* the schedule-derived values, not supply them ad hoc.
* The "coarse-to-fine" drug-design intuition (lots of fresh noise
  for exploration early, preserve the prior for refinement late)
  matches the cosine-annealed schedule directly: at round 0 with
  `n_cap = n_max` (large), the memory fraction is small (lots of
  fresh noise); at round `L-1` with `n_cap = n_min` (small), the
  memory fraction is large (preserve the prior). The math is the
  natural complement: `memory_fraction = 1 - n_cap`.
* Backward compatibility matters: existing callers (and the entire
  test surface) supply an explicit `beta` and expect it to be used
  verbatim when the policy does not carry a schedule sample. The
  default must be "framework drives beta" so the new behavior
  activates whenever the caller sets `schedule_sample`; the
  escape hatch (back-compat) is a single `bool` flag the caller
  can flip.
* The `policy_hash` audit invariant (`policy_hash ==
  hash_policy_hash(policy)`) must continue to hold *after* the
  override. The hash already covers `beta_by_channel`, so
  recomputing the hash against the post-override `beta_by_channel`
  is sufficient — no new field needs to be added to the hash
  *payload*, but adding `beta_from_schedule` to the payload
  preserves the invariant that two policies that differ only by
  this flag hash differently.

## Considered Options

1. **`memory_fraction_from_schedule(schedule_sample) -> float` in
   `adaptive_reflow/schedule/cosine.py`; the engine overrides
   `beta_by_channel` so `beta = n_cap` whenever
   `policy.beta_from_schedule is True` (default) and
   `policy.schedule_sample is not None`; `FinalRestartPolicy` adds
   the `beta_from_schedule: bool = True` field; `hash_policy_hash`
   includes the flag in its payload.**
2. **Add the per-round memory fraction computation directly to
   `apply_restart_distribution`** (every adapter re-derives
   `memory_fraction` from the schedule's `n_cap` inline). Rejected
   because the universal Protocol is supposed to consume the
   policy as-is; the adapter is not the right place for schedule
   arithmetic, and there are adapters outside this repo
   (molecular, etc.) that would need to be patched in lockstep.
3. **Compute the memory fraction only in the orchestrator's
   `evaluate_bundle`** (the policy is built with the schedule-
   derived beta and the engine forwards it verbatim). Rejected
   because the engine is the canonical entry point for every
   adapter-driven round; the wiring should happen at the engine so
   `apply_restart_distribution` consumers see the schedule-driven
   beta without depending on the orchestrator.

## Decision Outcome

Chosen option: **delegate the `beta_by_channel` mutation to the
algorithm-layer driver + runner path** and demote the engine's
inline `_policy_with_schedule_beta` helper to a *legacy back-compat
path that fires only when no driver has set the dedup flag*. The
canonical chain is:

1. **Schedule** — supplies `n_cap` (the fresh-noise capacity) for
   the round via `ScheduleSample.n_cap` / `n_min`.
2. **Driver** — transforms `n_cap` into `beta` via
   `PolicyDriverProtocol.compute_policy`. The canonical driver is
   `ScheduleDerivedPolicyDriver` which writes `beta = n_cap`. The
   driver sets `policy.driver_computed_beta = True` so the engine
   skips its inline re-override (Contract 1.2).
3. **Runner** — calls `MergeOperatorProtocol.merge` to produce the
   final `beta`. The merge step uses
   `prev = previous_round_emitted_beta`,
   `dynamic = driver.beta_by_channel[channel]`,
   `cap = schedule.n_cap`,
   `floor = schedule.n_min`,
   `delta_cap_up = delta_cap_down = 1.0`
   so the bounded merge collapses to `clamp(dynamic, floor, cap)`;
   the runner records the merge audit codes in
   `per_round_metrics[r]["merge_audit_codes"]` (Contract 2.4).
4. **Engine** — receives the post-merge `policy` and forwards it
   to `adapter.apply_restart_distribution` verbatim. The engine's
   legacy `_policy_with_schedule_beta` helper still exists but
   only fires when `policy.beta_from_schedule is True` AND
   `policy.driver_computed_beta is False` (i.e. the caller
   constructed the policy without using the driver abstraction);
   this preserves backward compatibility with legacy
   `FinalRestartPolicy` shapes.

The wiring is structural:

* `adaptive_reflow.schedule.cosine.memory_fraction_from_schedule`
  returns `1.0 - n_cap` (clipped to `[0, 1]`); raises on
  non-finite or non-numeric `n_cap`; refuses `None`
  `schedule_sample`. Exported from `adaptive_reflow.schedule`.
* `FinalRestartPolicy.beta_from_schedule: bool = True` (default).
  When `True` and the schedule sample is attached and
  `driver_computed_beta is False`, the engine applies its legacy
  inline `_policy_with_schedule_beta` helper. When
  `driver_computed_beta is True`, the engine SKIPS its inline
  helper (Contract 1.2).
* `FinalRestartPolicy.driver_computed_beta: bool = False`
  (default). Drivers that mutate `beta_by_channel` (e.g.
  `ScheduleDerivedPolicyDriver.compute_policy`) MUST set this to
  `True` via `dataclasses.replace(..., driver_computed_beta=True)`.
  The canonical helper
  `adaptive_reflow.algorithm.policy_driver._override_beta_by_channel`
  sets the flag automatically.
* `hash_policy_hash` includes `beta_from_schedule` and
  `driver_computed_beta` in its payload so two policies that
  differ only by these flags hash differently; the recompute
  remains deterministic.
* `Engine.run_round` checks `policy.beta_from_schedule and not
  policy.driver_computed_beta` before calling
  `_policy_with_schedule_beta`. When `driver_computed_beta is True`
  the engine forwards the policy verbatim. When the helper fires
  it sets `applied_policy_hash` to the post-override recompute.

### Consequences

Positive:

* The `beta_by_channel` source of truth is the canonical
  `PolicyDriverProtocol` — switching drivers plugs in a new beta
  philosophy without touching the engine, the adapter, or the
  schedule. The engine re-override is now a back-compat path
  used only when `driver_computed_beta=False`.
* The runner is the canonical site for the merge step
  (Contract 2.4); the bounded merge is observable in
  `per_round_metrics[r]["beta"]`, `driver_beta`, and
  `merge_audit_codes` so a downstream audit reader can
  audit-replay every per-round restart decision.
* The audit invariant `policy_hash == hash_policy_hash(policy)` is
  preserved through both the driver mutation (the driver's
  `_override_beta_by_channel` helper recomputes the hash) and the
  runner's post-merge replace (the runner recomputes the hash
  after applying the merge step).
* Backward compatibility is total: every existing test that
  builds a `FinalRestartPolicy` with `driver_computed_beta=False`
  continues to see the legacy engine-driven override; tests that
  use the runner see the canonical driver-driven chain.
* The wiring lives at the engine + runner, the two canonical
  entry points for every adapter-driven round; the universal
  Protocol is not modified.

Negative:

* The `FinalRestartPolicy` dataclass grows by one field
  (`driver_computed_beta`). Adding a field to a frozen dataclass
  requires `dataclasses.replace` callsites to keep working (every
  site that builds a policy by position has to add the new field).
  Existing sites use keyword arguments so no migration is needed;
  the field defaults to `False` so old code is forward-compatible.
* The `hash_policy_hash` payload grows by two entries
  (`beta_from_schedule` and `driver_computed_beta`). Any cached
  hash computed before this change is invalidated; this is
  intentional — the new hash is the canonical one.
* The runner now performs a merge step + a `dataclasses.replace`
  per round; the cost is sub-microsecond per round on the
  canonical 4-channel policy and remains invisible against the
  integrator cost.

### Confirmation

The decision is enforced by:

* `adaptive_reflow/schedule/cosine.py::memory_fraction_from_schedule`
  — the canonical derivation.
* `adaptive_reflow/contracts/authority.py::FinalRestartPolicy` —
  the `beta_from_schedule` and `driver_computed_beta` fields.
* `adaptive_reflow/contracts/hashes.py::hash_policy_hash` —
  the payload that includes both flags.
* `adaptive_reflow/algorithm/policy_driver.py::PolicyDriverProtocol`
  and `ScheduleDerivedPolicyDriver.compute_policy` —
  the driver that writes `beta = n_cap` and sets
  `driver_computed_beta=True`.
* `adaptive_reflow/algorithm/runner.py::ReInferenceRunner.run` —
  the merge step that calls
  `self._merge.merge(prev, dynamic, cap, floor, ...)` between
  policy emission and `engine.run_round`.
* `adaptive_reflow/frame/engine.py::Engine.run_round` —
  the engine-side dispatch that skips the inline override when
  `driver_computed_beta=True`.
* `tests/test_algorithm/test_runner.py` —
  `test_runner_calls_merge_operator_between_policy_and_engine`,
  `test_runner_merge_step_observable_in_beta_trajectory`,
  `test_runner_with_identity_operator_passes_dynamic_through`
  — the new Contract 2.4 regression tests.
* `tests/test_algorithm/test_policy_driver.py` —
  `test_schedule_derived_driver_matches_engine_override` — the
  updated Contract 1.2 / Contract 3.1 regression test.
* `tests/test_algorithm/test_blender.py` —
  `test_blender_direction_memory_fraction_not_beta` — the new
  Contract 3.1 direction test.
* `tests/test_algorithm/test_merge_operator.py` — the P0-3
  regression suite (`test_p0_3_*`).

## More Information

* [docs/adr/0005](0005-fail-closed-audit-code-policy.md) — the
  audit-code catalogue that the round trace's
  `applied_policy_hash` recompute depends on.
* [docs/adr/0007](0007-prev-anchored-bounded-merge.md) — the
  bounded-merge authority that consumes the schedule's `n_cap` as
  the *cap*, never the *prev*. The new wiring is the *memory
  fraction* counterpart: the schedule drives `beta` (the prior
  retention) directly, while the bounded merge drives `cap` (the
  per-round delta envelope).
* `adaptive_reflow/schedule/cosine.py::n_cap_for_round` — the
  closed-form cosine capacity function.
* `adaptive_reflow/frame/engine.py::Engine.run_round` — the
  override wiring.
* `adaptive_reflow/adapters/twodim_fm.py::TwoDimFMAdapter.
  apply_restart_distribution` — the universal Protocol consumer
  that the override activates.