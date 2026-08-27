---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 9. Mixer RMS-preservation precondition

## Context and Problem Statement

`adaptive_reflow.molecular.mixer.EqualRmsCoordinateMixer` is the
concrete molecule implementation of the universal
`RestartMixer` Protocol. The mixer's job is to blend a fresh prior
state with a detached endpoint memory state, preserving the fresh
prior's RMS around its center. The legacy class name
`RMSPreservingCoordinateMixer` was misleading: the RMS of the
*blend* is preserved only when the two input tensors have equal
centred RMS within `1e-6`. When they differ by more than the
tolerance, the legacy implementation silently rescaled the inputs
to make the RMS values match, erasing the diagnostic value of the
mismatch.

The risk is twofold:

1. **Naming**: the legacy `RMSPreservingCoordinateMixer` name
   implies RMS preservation is unconditional, hiding the
   precondition from a future caller.
2. **Silent rescaling**: a large RMS mismatch is a real defect
   (the prior and memory states are not calibrated to the same
   variance regime), and silently rescaling them produces a
   plausible-looking but undiagnosed blend.

The decision answers three questions:

1. **What is the canonical class name?** `EqualRmsCoordinateMixer`.
2. **What happens when the precondition fails?** The audit code
   `MIXER_RMS_PRECEDENCE_FAIL` is appended to the returned ledger's
   `audit_codes` list; the blend is still computed (the behaviour is
   observable, not silent), but the caller must inspect the audit
   trail.
3. **How is back-compat preserved?** The legacy name
   `RMSPreservingCoordinateMixer` is kept as a module-level alias
   to `EqualRmsCoordinateMixer`; importing it emits a
   `DeprecationWarning`.

## Decision Drivers

* The mixer's RMS preservation is conditional on an input
  precondition (RMS-equal within `1e-6`). A class name that omits
  the precondition is misleading; the new name
  `EqualRmsCoordinateMixer` puts the precondition in the name.
* The audit trail must distinguish "well-behaved blend" from
  "precondition failed" from "legacy silent rescale". The first
  case carries no audit code; the second carries
  `MIXER_RMS_PRECEDENCE_FAIL`; the third is no longer reachable
  after the rename.
* The back-compat alias is the load-bearing migration tool: every
  test, doc, and downstream consumer that references the legacy
  name must keep working until they migrate. The
  `DeprecationWarning` is the migration signal.

## Considered Options

1. **Rename to `EqualRmsCoordinateMixer`. Keep
   `RMSPreservingCoordinateMixer` as a back-compat alias that emits
   a `DeprecationWarning`. Append `MIXER_RMS_PRECEDENCE_FAIL` to
   the ledger when the precondition fails; never silently
   rescale.**
2. **Rename and drop the legacy alias.** Rejected because the
   legacy name appears in tests, docs, and (potentially) external
   consumer code; dropping it is a breaking change for no benefit.
3. **Keep the legacy name and document the precondition in the
   docstring.** Rejected because the name is misleading and the
   `DeprecationWarning` is the migration signal.

## Decision Outcome

Chosen option: **`EqualRmsCoordinateMixer` is the canonical class
name. `RMSPreservingCoordinateMixer` is preserved as a back-compat
alias that emits a `DeprecationWarning` on import. RMS is preserved
only when inputs are RMS-equal within `1e-6`; otherwise the helper
`adaptive_reflow_memory_restart_coords` appends
`MIXER_RMS_PRECEDENCE_FAIL` to the returned ledger's `audit_codes`
list. The blend is still computed (the behaviour is observable,
not silent); callers that depend on the equality precondition must
inspect `ledger["audit_codes"]`.**

The decision is structural:

* `class EqualRmsCoordinateMixer:` — the canonical implementation
  that wraps `adaptive_reflow_memory_restart_coords` and reshapes
  its return to the universal `(state, ledger)` contract.
* `RMSPreservingCoordinateMixer = EqualRmsCoordinateMixer`
  immediately followed by
  `warnings.warn("RMSPreservingCoordinateMixer is deprecated; use
  EqualRmsCoordinateMixer", DeprecationWarning, stacklevel=2)` —
  the back-compat alias.
* `MIXER_RMS_PRECEDENCE_FAIL` is the module-level constant in
  `adaptive_reflow/molecular/mixer.py`, re-exported in
  `molecular/__init__.py`.
* `_require_equal_rms(memory, restart, *, tolerance=1e-6,
  audit_codes=None)` is the helper that computes the two RMS
  values and appends `MIXER_RMS_PRECEDENCE_FAIL` when the
  difference exceeds the tolerance.

The audit-code policy is preserved: `MIXER_RMS_PRECEDENCE_FAIL` is
added to the catalogue in
[ADR-0005](0005-fail-closed-audit-code-policy.md).

### Consequences

Positive:

* The class name carries the precondition. A future caller cannot
  read the name and conclude "RMS is preserved unconditionally".
* The precondition failure is observable on the audit trail.
  Callers that depend on RMS preservation must inspect
  `ledger["audit_codes"]` and surface the failure; callers that do
  not depend on it (e.g. a research prototype) can ignore the audit
  code without changing the blend's numeric output.
* The back-compat alias lets existing tests, docs, and downstream
  consumers migrate at their own pace; the `DeprecationWarning` is
  the migration signal.

Negative:

* The `DeprecationWarning` is emitted *at import time* (not at
  call time) because the alias is a module-level rebinding. A
  consumer that imports `RMSPreservingCoordinateMixer` once at the
  top of a long-lived process will see exactly one warning. A
  consumer that imports it conditionally inside a function will see
  one warning per import; for a research codebase this is the
  intended behaviour.
* The `1e-6` tolerance is hard-coded inside
  `_require_equal_rms`. A future caller that needs a tighter or
  looser tolerance cannot override it without editing the helper.

### Confirmation

The decision is enforced by:

* `tests/test_molecular/test_mixer.py` — the property test that
  asserts `EqualRmsCoordinateMixer` returns a ledger with
  `audit_codes == [MIXER_RMS_PRECEDENCE_FAIL]` when the input RMS
  values differ by more than `1e-6`.
* `tests/test_molecular/test_mixer.py` — the deprecation-warning
  test that asserts `RMSPreservingCoordinateMixer` is a function
  alias of `EqualRmsCoordinateMixer` and emits a
  `DeprecationWarning` on import.
* `tools/check_docs_against_code.py` — every reference to
  `EqualRmsCoordinateMixer`, `RMSPreservingCoordinateMixer`, and
  `MIXER_RMS_PRECEDENCE_FAIL` in the docs resolves to a real
  symbol.

## More Information

* [docs/adr/0005](0005-fail-closed-audit-code-policy.md) — the
  audit-code catalogue that lists `MIXER_RMS_PRECEDENCE_FAIL`.
* `adaptive_reflow/molecular/mixer.py::EqualRmsCoordinateMixer` —
  the canonical mixer.
* `adaptive_reflow/molecular/mixer.py::RMSPreservingCoordinateMixer` —
  the back-compat alias that emits a `DeprecationWarning`.
* `adaptive_reflow/molecular/mixer.py::adaptive_reflow_memory_restart_coords` —
  the free function that performs the blend and emits the audit
  code.
* `adaptive_reflow/molecular/mixer.py::MIXER_RMS_PRECEDENCE_FAIL` —
  the module-level audit-code constant.
* `adaptive_reflow/molecular/__init__.py` — the curated re-export
  layer that exposes both names plus the audit-code constant.