---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 10. Cosine-driven memory fraction

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

Chosen option: **add `memory_fraction_from_schedule` to the
schedule module, add `beta_from_schedule: bool = True` to
`FinalRestartPolicy`, and override `beta_by_channel` in
`Engine.run_round` before the `apply_restart_distribution` call.
The override is invisible to the caller (the supplied `policy` is
never mutated) and the round trace's `applied_policy_hash` is
recomputed via `hash_policy_hash` so the audit invariant holds.**

The wiring is structural:

* `adaptive_reflow.schedule.cosine.memory_fraction_from_schedule`
  returns `1.0 - n_cap` (clipped to `[0, 1]`); raises on
  non-finite or non-numeric `n_cap`; refuses `None`
  `schedule_sample`. Exported from `adaptive_reflow.schedule`.
* `FinalRestartPolicy.beta_from_schedule: bool = True` (default).
  When `True` the framework derives `beta_by_channel` from the
  schedule; when `False` the caller-supplied `beta_by_channel` is
  preserved verbatim (back-compat).
* `Engine.run_round` calls the new helper
  `adaptive_reflow.frame.engine._policy_with_schedule_beta` before
  forwarding the policy to `adapter.apply_restart_distribution`.
  The helper:

  1. Reads `policy.schedule_sample.n_cap`.
  2. Builds a new `beta_by_channel` mapping where every channel
     carries `FactorValue(n_cap)`.
  3. Replaces `beta_by_channel` on the policy and recomputes
     `policy_hash` via `hash_policy_hash`.

  When `policy.schedule_sample is None` (no schedule attached) the
  helper is a no-op and the policy is forwarded verbatim — this is
  the back-compat path every existing test relies on.

* `hash_policy_hash` includes `beta_from_schedule` in its payload
  so two policies that differ only by this flag hash differently;
  the recompute remains deterministic.
* `build_final_restart_policy` accepts a `beta_from_schedule` kwarg
  (default `True`); the orchestrator's `build_final_policy` calls
  it with `beta_from_schedule=True` so the orchestrator-built
  policies also benefit from the new wiring when the caller opts in
  via `schedule_sample`.

### Consequences

Positive:

* The per-round memory fraction is now schedule-derived by default.
  An ablation that compares "schedule-driven beta" against
  "fixed beta" reduces to "supply vs omit `schedule_sample`".
* The audit invariant `policy_hash == hash_policy_hash(policy)` is
  preserved through the override (the recompute runs after the
  override, not before).
* Backward compatibility is total: every existing test supplies
  `schedule_sample=None` and continues to see the explicit beta
  they set; the override is dormant until the caller opts in.
* The wiring lives at the engine, the single canonical entry
  point for every adapter-driven round; the universal Protocol is
  not modified.

Negative:

* The `FinalRestartPolicy` dataclass grows by one field
  (`beta_from_schedule`). Adding a field to a frozen dataclass
  requires `dataclasses.replace` callsites to keep working (every
  site that builds a policy by position has to add the new field).
  Existing sites use keyword arguments so no migration is needed;
  the field defaults to `True` so old code is forward-compatible.
* The `hash_policy_hash` payload grows by one entry. Any cached
  hash that was computed before this change is invalidated; this
  is intentional — the new hash is the canonical one.
* The override branch in `run_round` runs on every round when
  `beta_from_schedule=True`. The cost is a `dataclasses.replace`
  plus a `hash_policy_hash` call per round (the latter is O(F)
  where F is the total factor count). For the canonical 4-channel
  policy the overhead is sub-microsecond; for the perf-test 1000-
  round horizons it is invisible against the integrator cost.

### Confirmation

The decision is enforced by:

* `adaptive_reflow/schedule/cosine.py::memory_fraction_from_schedule`
  — the canonical derivation.
* `adaptive_reflow/contracts/authority.py::FinalRestartPolicy` —
  the `beta_from_schedule` field.
* `adaptive_reflow/contracts/hashes.py::hash_policy_hash` — the
  payload that includes the flag.
* `adaptive_reflow/frame/engine.py::_policy_with_schedule_beta` and
  `Engine.run_round` — the override wiring.
* `tests/test_adapters/test_twodim_fm.py` —
  `test_cosine_schedule_drives_per_round_memory_fraction`,
  `test_first_round_is_mostly_fresh_noise`,
  `test_last_round_is_mostly_prior`,
  `test_policy_beta_override_supersedes_schedule` — the four new
  regression tests.

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