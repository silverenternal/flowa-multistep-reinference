---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 7. Prev-anchored bounded merge

## Context and Problem Statement

`adaptive_reflow.frame.merge.bounded_merge` and its orchestrator
helper `bounded_merge_with_schedule` are the canonical
`DTB-R3` merge authorities. The merge takes a `prev` (previous
round's `bounded_target_fraction`), a `dynamic` (evidence-derived
target fraction), a hard `[floor, cap]` envelope, and per-round
`delta_cap_up` / `delta_cap_down` step caps. The orchestrator helper
threads a schedule sample through the merge so a single call site
produces a `FactorValue` per channel per round.

Before the gap closure, the orchestrator helper could silently
substitute the schedule's `n_cap` value for `prev` when the caller
forgot to thread the previous round's emitted fraction through the
ledger. This double-counted the schedule value (it became both the
*cap* and the *prev*) and erased any ledger-driven information about
the channel's recent history. The risk is that an orchestrator bug
that forgets to thread `prev` looks identical on the audit trail to
a well-behaved first round (where `prev` is legitimately undefined
*and* the schedule value is being used as a one-time initialiser).

The decision answers three questions:

1. **What is the canonical source of `prev`?** The previous round's
   emitted `bounded_target_fraction` for the channel, stored in the
   orchestrator's `last_emitted[channel]` mapping.
2. **What is the canonical source of the cap?** The schedule sample's
   `n_cap` (or `1.0` as the no-sample default). The cap is never the
   prev.
3. **What happens when `prev` is missing?** The merge refuses with
   `MergeAuthorityError(ERR_PREV_REQUIRED)`; the helper does NOT
   silently substitute a default.

## Decision Drivers

* The bounded merge is fail-closed: any non-finite input, a non-
  numeric type, a negative floor, a cap below the floor, or a
  `delta_cap` outside `[0, 1]` already raises
  `MergeAuthorityError`. A missing `prev` is in the same family of
  "the caller handed us malformed arguments" failures and must be
  treated identically.
* The audit trail must distinguish "schedule-derived first round"
  from "ledger-driven subsequent round" from "caller forgot to thread
  `prev`". The first two cases carry
  `MERGE_PREV_ANCHORED_TO_LAST_EMITTED`; the third carries
  `ERR_PREV_REQUIRED` and a `MergeAuthorityError`.
* The schedule's `n_cap` value is the *cap*, never the prev. A
  caller that confuses the two would inflate the per-round change
  envelope (the prev-anchored delta interval collapses around a
  schedule value that is already at the cap), and the audit trail
  must surface this as a structural defect, not a numeric surprise.

## Considered Options

1. **`prev` is required; missing `prev` raises
   `MergeAuthorityError(ERR_PREV_REQUIRED)`. The orchestrator
   threads `last_emitted[channel]` (the previous round's emitted
   `bounded_target_fraction`) as the prev. The schedule's `n_cap`
   is the cap, never the prev.**
2. **Silently substitute `n_cap` (or `0.0`) for `prev` when the
   caller forgot to thread it.** Rejected because the audit trail
   cannot distinguish "well-behaved first round" from "orchestrator
   forgot to thread `prev`".
3. **Treat the first round specially: `prev` defaults to `n_cap`
   when `last_emitted[channel]` is missing.** Rejected because the
   rule "prev defaults to `n_cap`" is exactly the double-counting
   defect the gap closure is closing; making it explicit would
   *preserve* the defect.

## Decision Outcome

Chosen option: **the bounded merge and its orchestrator helper
never silently substitute a default for `prev`. The orchestrator
threads `last_emitted[channel]` (the previous round's emitted
`bounded_target_fraction`) as the prev. When `prev=None`, the merge
rejects with `MergeAuthorityError`; the helper appends
`ERR_PREV_REQUIRED` to `audit_codes` before raising. The schedule's
`n_cap` is the cap, never the prev.**

The decision is structural:

* `bounded_merge(prev, dynamic, *, cap, floor, delta_cap_up,
  delta_cap_down, audit_codes=None) -> float` — `prev` is a
  positional required argument. A `None` value is caught by
  `_coerce_finite_real` and raised as `MergeAuthorityError`.
* `bounded_merge_with_schedule(*, channel, dynamic, schedule_sample,
  fresh_noise_floor, delta_caps_by_channel,
  fresh_noise_floor_by_channel=None, prev=None, audit_codes=None)
  -> FactorValue` — `prev=None` triggers the explicit
  `ERR_PREV_REQUIRED` branch:

  ```
  if prev is None:
      if audit_codes is not None:
          audit_codes.append(ERR_PREV_REQUIRED)
      raise MergeAuthorityError(
          "prev is required for orchestrator-driven merge; "
          "the schedule value is the cap, not the prev"
      )
  prev_v = _coerce_finite_real(prev, name="prev")
  if audit_codes is not None:
      audit_codes.append(MERGE_PREV_ANCHORED_TO_LAST_EMITTED)
  ```

* The schedule sample's `n_cap` is consumed only by `_cap_for_channel`
  (always the cap) and as the conservative fallback in
  `_floor_for_channel` (with `MERGE_FLOOR_FALLBACK` audit code). It
  is never consumed by the prev path.

The orchestrator-side invariant is documented in
`adaptive_reflow/frame/orchestrator.py` as the
`last_emitted: dict[ChannelName, FactorValue]` mapping that the
engine / orchestrator maintains per channel. On every round the
orchestrator looks up `last_emitted.get(channel)` and passes the
result as `prev=...` to `bounded_merge_with_schedule`. The first
round on a channel (where `last_emitted` has no entry) is the only
case where `prev=None` legitimately reaches the helper; the
orchestrator must surface this as a structural defect (the channel
should have been initialised before the round loop started) and the
merge must reject it with `ERR_PREV_REQUIRED` rather than silently
fall back to the schedule value.

### Consequences

Positive:

* The audit trail distinguishes three states unambiguously:
  * `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` — the merge was driven
    from the ledger (`prev` came from the previous round's emitted
    fraction).
  * `MERGE_FLOOR_FALLBACK` — the merge could not find a per-channel
    floor and fell back to the schedule's `n_cap` (or `0.0`).
  * `ERR_PREV_REQUIRED` (+ `MergeAuthorityError`) — the caller
    handed the merge a structural defect (missing `prev`). The
    ledger row is still emitted with the audit code, and the round
    trace carries the failure.
* The bounded merge is total on legitimate inputs and refuses on
  illegitimate ones. The rule is symmetric: every "missing required
  argument" branch raises `MergeAuthorityError`, every "structural
  fallback" branch emits an audit code.

Negative:

* A round on a fresh channel that has never been initialised will
  fail closed. The orchestrator must therefore ensure every channel
  is initialised (with an explicit `last_emitted[channel] = ...`
  seeding) before the first round on it. This is the intended
  behaviour but it does add a small orchestration burden; the
  burden is documented in the orchestrator's docstring.
* The `bounded_merge_with_schedule` helper is stricter than a
  naively permissive caller might want. This is the point: a
  silently-permissive helper is a foot-gun in a research codebase
  where the orchestrator author is often the maintainer.

### Confirmation

The decision is enforced by:

* `tests/test_frame/test_merge.py` — every hostile-case fixture
  asserts `ERR_PREV_REQUIRED` is reachable.
* `tests/property/test_bounded_merge_anchoring.py` — the property
  test that asserts `bounded_merge_with_schedule` never returns a
  result whose `prev` was substituted from the schedule sample.
* `tools/check_docs_against_code.py` — every reference to
  `ERR_PREV_REQUIRED`, `MERGE_PREV_ANCHORED_TO_LAST_EMITTED`, and
  `MERGE_FLOOR_FALLBACK` in the docs resolves to a real symbol.

## More Information

* [docs/adr/0005](0005-fail-closed-audit-code-policy.md) — the
  audit-code catalogue that lists the three merge codes.
* `adaptive_reflow/frame/merge.py::bounded_merge` —
  the canonical merge.
* `adaptive_reflow/frame/merge.py::bounded_merge_with_schedule` —
  the orchestrator helper.
* `adaptive_reflow/frame/orchestrator.py::AdaptiveReflowPolicyOrchestrator` —
  the orchestrator that threads `last_emitted[channel]` as the
  prev.