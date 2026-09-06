# Algorithm improvement — D.5: conformance battery

**Status:** done (Wave 15 C — commit 4d30f41; D.5 LIVE: tests/test_adapters/conformance_battery.py — 8 conformance checks × 14 adapters = 90 passed) (+ Wave 47: composite_verdict=framework_improves on LineageFlow real ckpt; Wave 48: pytest pre-push fixes; Wave 52: Kanzi composite 9/9 cells framework_improves median=+0.170175; Wave 54: paper §7-8 honest verdict rewrite with Tier 3 numbers)
**Date:** 2026-09-05
**Priority:** high (D.5 enables D.3 to become a real HARD gate; currently
D.3 is soft because hand-written tests are easy to game)
**Depends on:** D.2 (adapters using abstract interfaces — verified)
**Owner:** framework maintainer
**Goal:** author `tests/test_adapters/conformance_battery.py` that
auto-generates conformance assertions for all registered adapters (single
source of truth, scikit-learn `check_estimator` pattern).

## Background

Per framework-internal-metrics rev 2 §1 D.5 + D.3:
- D.3 (current state): 226/226 = 100% pass rate across 13 hand-written
  per-adapter test files. **But**: hand-written tests are easy to game
  (each adapter passes its own self-written checks).
- D.5 (target): single auto-generated conformance battery (analogous to
  scikit-learn `check_estimator` and Lightning `tests/strategies/`) that
  iterates over all registered adapters and runs the same N checks.
- D.3 redefined as: "100% pass on the auto-generated battery."

Rev 2 §6 baseline audit found:
- D.3 hand-written baseline: 13 adapters (not 18 — 5 missing or
  out-of-scope; see baseline report §D.3)
- D.5 file: MISSING

## What to do

1. **Enumerate registered adapters**: read `adaptive_reflow/adapters/__init__.py`
   `ADAPTER_REGISTRY` or equivalent (or scan all `.py` files in
   `adaptive_reflow/adapters/`)
2. **Define shared conformance checks** (the "auto-battery" — scikit-learn
   pattern):
   - `check_adapter_has_velocity_field(adapter)` — Protocol surface check
   - `check_adapter_default_mode_is_synthetic(adapter)` — per Wave 11
     PHASE-3 gate
   - `check_adapter_uses_abstract_interfaces(adapter)` — D.2 verified
     (runtime isinstance check on SchedulerProtocol, etc.)
   - `check_adapter_byte_stable(adapter)` — same input + seed → same
     output (within atol)
   - `check_adapter_protocol_surface_matches(adapter, expected_protocols)`
   - `check_adapter_registered_in_init(adapter)` — already in
     `__init__.py`?
   - `check_adapter_handles_empty_batch(adapter)` — graceful failure
   - `check_adapter_handles_zero_noise(adapter)` — boundary case
3. **Author `tests/test_adapters/conformance_battery.py`** with
   parametrized tests that iterate over the registered adapters and run
   all checks
4. **Verify all registered adapters pass** (or document which fail + why)
5. **Add CI hook**: conformance_battery.py auto-picked-up by pytest
6. **Update D.3 metric target**: "18/18 against D.5 auto-battery"
7. **Update framework-internal-metrics.md** §1 D.3 + D.5 to reflect new
   state (move D.5 from "missing" to "live")

## Files affected

- `tests/test_adapters/conformance_battery.py` (NEW)
- `adaptive_reflow/adapters/__init__.py` (UPDATE; ensure ADAPTER_REGISTRY
  exports)
- `framework-internal-metrics.md` §1 D.3 + D.5 (UPDATE; metric table
  reflects new state)
- `todo/STATUS.md` (UPDATE)

## Acceptance

- [ ] `tests/test_adapters/conformance_battery.py` exists
- [ ] Battery has ≥ 8 conformance checks
- [ ] Battery runs over ≥ 13 adapters (current registered count)
- [ ] Battery pass rate reported per-adapter + per-check
- [ ] `pytest tests/test_adapters/conformance_battery.py -v` passes
- [ ] D.3 metric redefined in framework-internal-metrics.md to use D.5
- [ ] Commit + push

## Estimated time

1-2 hours (no GPU; pure test framework + adapter introspection).

## Acceptance gate

**Gate name:** `G-D5-CONFORMANCE-BATTERY` (new; defined here)

**Pre-condition:** ≥ 13 adapters registered
**Pass conditions:**
- [ ] All acceptance checklist items
- [ ] `docs/baseline-audit-report.md` §D.5 updated to "MET"
- [ ] `todo/STATUS.md` updated

## Out of scope

- Adding new adapters (separate task)
- Adapters currently failing (resolve those separately; don't gate the
  battery on them)
- F.2 reproduction (separate task)

## Wave 56 close-out

Status line updated to reflect Wave 47-54 stack: composite metric layer (Wave 47), pytest pre-push fixes (Wave 48), FlowMol3 glue + composite (Wave 49), Kanzi/LineageFlow real-ckpt composite eval (Wave 50-52), paper §Tier 3 honest verdict with 3 real numbers (Wave 54). D.5 conformance battery remains the foundational gate; downstream composite closes (kanzi 9/9, lineageflow framework_improves) build on top of it. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).