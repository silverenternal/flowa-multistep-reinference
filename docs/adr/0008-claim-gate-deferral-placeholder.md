---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 8. Claim-gate deferral placeholder

## Context and Problem Statement

`adaptive_reflow.eval.claim_gate.evaluate_claim_gate` is the
structural evaluator that decides whether a candidate claim passes,
fails, or is deferred for human review. The promote/rollback branches
of the decision depend on R7 GPU calibration data which has not yet
landed in the project. Until R7 lands, the evaluator cannot make a
principled promote/rollback decision and the function must return
`"defer"` for every call.

The risk is that the deferral is implicit: an empty `if` branch
or a `return "defer"` line at the bottom of `evaluate_claim_gate`
would hide the deferral behind the public surface. A future R7
maintainer would then have to read the whole function body to find
the deferral and would be tempted to inline the new logic into the
existing body — a refactor that *should* be a one-line body
replacement becomes a public-surface change.

The decision answers two questions:

1. **Where** does the deferral live? Inside a module-level helper
   named `_resolve_decision(passed, failed) -> ClaimGateDecision`
   that `evaluate_claim_gate` calls.
2. **What** does the helper do today? It returns `"defer"`
   structurally. When R7 lands, only the body of `_resolve_decision`
   needs to change — the public surface of `evaluate_claim_gate` and
   the contract on `ClaimGateDecision` stay the same.

## Decision Drivers

* The deferral must be visible to a future maintainer who is wiring
  R7. The name `_resolve_decision` and the signature
  `(passed, failed) -> ClaimGateDecision` are deliberate: they tell
  the maintainer exactly where the new logic lands.
* The public surface of `evaluate_claim_gate` — its signature, the
  shape of `ClaimGateDecision`, and the audit-trail emission — must
  stay stable so the wiring change is purely a body replacement.
* The deferral must not be silent on the audit trail. The
  `ClaimGateDecision` carries a `reason` field that names the
  deferral so a downstream consumer can grep for it.

## Considered Options

1. **Delegate the resolve to a module-level helper
   `_resolve_decision(passed, failed) -> ClaimGateDecision`. Today
   the helper returns `"defer"` structurally with a `reason`
   describing the missing R7 data.**
2. **Inline the deferral in `evaluate_claim_gate`.** Rejected
   because a future R7 maintainer would have to read the whole
   function to find the deferral and would be tempted to refactor
   the public surface.
3. **Raise `NotImplementedError` until R7 lands.** Rejected because
   the helper is consumed by the orchestrator in the present
   release; a raised exception would crash the round.

## Decision Outcome

Chosen option: **`evaluate_claim_gate` delegates decision resolution
to the module-level helper `_resolve_decision(passed, failed) ->
ClaimGateDecision`. Today the helper returns `ClaimGateDecision(
verdict="defer", reason="r7_calibration_pending")` structurally.
When R7 lands, the helper body is the only function that changes:
`_resolve_decision` is replaced with the real promote/rollback
logic, and `evaluate_claim_gate` keeps the same public surface.**

The structural deferral is exposed in two places:

* The helper signature, which is the search anchor for a future R7
  maintainer.
* The `reason` field of the returned `ClaimGateDecision`, which is
  the audit-trail anchor for downstream consumers.

The orchestrator-side invariant is documented in
`adaptive_reflow/eval/claim_gate.py` as the
`evaluate_claim_gate` public surface; any consumer of the claim gate
must tolerate `"defer"` verdicts today and may need to update when
R7 lands.

### Consequences

Positive:

* The R7 wiring is a one-line body replacement. A future maintainer
  finds the helper by its name, sees the structural deferral, and
  knows exactly where to add the real logic.
* The public surface of `evaluate_claim_gate` and the shape of
  `ClaimGateDecision` are stable across the R7 transition.
* The deferral is observable on the audit trail via the `reason`
  field.

Negative:

* The orchestrator must tolerate `"defer"` verdicts today. This is
  a real constraint: the orchestrator cannot promote a claim until
  R7 lands, so any "promote" branch in the orchestrator's round
  loop is gated on a non-`"defer"` verdict.
* The deferral's `reason` string (`"r7_calibration_pending"`) is
  part of the public surface; renaming it is a breaking change for
  any consumer that greps the audit trail by reason.

### Confirmation

The decision is enforced by:

* `tests/test_eval/test_claim_gate.py` — the property test that
  asserts `evaluate_claim_gate` returns a `"defer"` verdict with
  reason `"r7_calibration_pending"` for every input today.
* `tools/check_docs_against_code.py` — every reference to
  `_resolve_decision` and `evaluate_claim_gate` in the docs
  resolves to a real symbol.

## More Information

* [docs/adr/0004](0004-engine-seven-step-operation-order.md) — the
  related future ADR that ADR-0004 cross-references; both ADRs name
  the same R7 milestone.
* `adaptive_reflow/eval/claim_gate.py::_resolve_decision` — the
  helper that is the structural deferral.
* `adaptive_reflow/eval/claim_gate.py::evaluate_claim_gate` — the
  public function that delegates to the helper.
* `ROADMAP.md` — the R7 entry that names the milestone that
  unblocks the helper body.