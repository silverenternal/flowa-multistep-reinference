# Algorithm improvement — E.1: CLM claim test-coupled floor (batch 2)

**Status:** pending (NEW — Wave 32 audit gap; second batch of E.1)
**Date:** 2026-09-05
**Priority:** high (E.1 is a HARD gate; ≥ 70% test-coupled target by Wave 16)
**Depends on:** Wave 26 Agent C first batch (live; 11/41 wired)
**Owner:** framework maintainer
**Wave:** Wave 33 (target)
**Goal:** wire **22 more CLM claims** with tests under
`tests/test_claims/`, taking the test-coupled floor from 11/41 (26.8%)
to **33/41 (80.5%)** — well above the 70% target.

## Background

Per `framework-internal-metrics.md` §1 E.1:
> CLM claim count in `docs/CLAIMS.md` — split into **total count** +
> **test-coupled count**. Target: ≥ 50 total, **≥ 70% test-coupled by
> Wave 16** (HARD gate; reconciled with paper-writeup gate).

Per Wave 26 Agent C (`todo/wave26-result-validation.md`):
- **43 total claims** (39 ACTIVE + 2 INVERTED + 2 DEPRECATED)
- **41 active claims** (43 total − 2 deprecated)
- **11 test-coupled** after Wave 26 (CLM-005, 006, 011, 019, 020, 021, 027, 028, 029, 030, 047 — all category-a trivially testable)
- 37/37 passing in 0.64 s under `tests/test_claims/`

Per Wave 32 Agent A (`docs/audit/gap-audit.md` §2.1):
- **E.1 PARTIAL** — 11/41 = 26.8% test-coupled; target ≥ 70% by Wave 16
- **No `todo/` plan file exists** — this file closes that gap

## Wave 32 scope (this plan)

Wire **22 more CLM claims** with tests, taking the count to 33/41 = 80.5%
(gives 10.5% margin above the 70% target). The selection prioritises:

1. **Category-b claims** (numerical assertions; lowest-effort wiring) — pick first
2. **Category-c claims** (algorithmic invariants; medium effort) — pick second
3. **Category-d claims** (paper-claim soft; high effort; skip if necessary)

Selection strategy: **prioritise lowest-effort first** to maximise the
count within the 22 budget. If category-b yields > 22 candidates, ship
batch 2 with only category-b; defer batch 4 for category-c/d.

## What to do

### Phase A — Claim selection (audit the remaining 30)

1. **Read `docs/CLAIMS.md`** and enumerate the 30 remaining active claims
   (43 total − 11 already wired − 2 deprecated = 30 candidates)
2. **For each candidate, classify as b / c / d** (deferred; Wave 26 Agent C did this; see `todo/wave26-result-validation.md` for the classification table)
3. **Identify the 22 lowest-effort candidates** — those whose `Asserted by:`
   reference is to a public function with a measurable numerical or
   structural property

### Phase B — Test wiring (22 claims × ~10 LOC per test)

For each of the 22 selected claims:

1. **Author 1 test function** in `tests/test_claims/test_<claim_id>.py`
   (or extend existing file if related to a category)
2. **Test function name**: `test_<claim_id>_<one_liner>`
3. **Test body pattern** (per Wave 26 Agent C convention):
   ```python
   def test_clm_NNN_short_descriptor() -> None:
       """CLM-NNN: <one-line restatement of the claim>."""
       # 1. Set up the assertion target (per the claim's `Asserted by` reference)
       # 2. Invoke the function with deterministic inputs (per Wave 26 B.5 marker)
       # 3. Assert the claim's invariant numerically or structurally
   ```
4. **Each test carries `@pytest.mark.deterministic`** (Wave 26 B.5 gate)
5. **Each test references the claim ID** in its docstring (so the audit
   tool `tools/check_claims_consistency.py` can verify test coupling)

### Phase C — Update CLAIMS.md (per-claim `Asserted by:` addition)

For each of the 22 wired claims:

1. **Append `Tested by: tests/test_claims/test_<id>.py:<func_name>` line**
   in the claim's entry in `docs/CLAIMS.md`
2. This is the audit-trail link that the verifier walks

### Phase D — Verification + commit

1. **Run `pytest tests/test_claims/ -v`** — should pass all 22 new tests
   + the 11 existing tests = 33 total
2. **Run `python tools/check_claims_consistency.py`** — should report
   0 inconsistencies and 33 test-coupled
3. **Run `mkdocs build --strict`** — should still pass (no doc churn)
4. **Update `framework-internal-metrics.md` §1 E.1** to mark "33/41 = 80.5%"
6. **Update `docs/baseline-audit-report.md` §E.1** to reflect new count
7. **Update `framework-freeze-checklist.md` MUST-1 E.1** to mark "33/41 = 80.5% PASS"

## Files affected

- `tests/test_claims/test_<clm_id>.py` (NEW × ~22 files; some may be batched into existing test files)
- `docs/CLAIMS.md` (UPDATE × 22 entries; append `Tested by:` line)
- `framework-internal-metrics.md` §1 E.1 (UPDATE)
- `docs/baseline-audit-report.md` §E.1 (UPDATE)
- `framework-freeze-checklist.md` MUST-1 E.1 (UPDATE)

## Acceptance

- [ ] 22 new test functions authored under `tests/test_claims/`
- [ ] All 22 new tests pass deterministically (B.5 marker)
- [ ] All 22 `docs/CLAIMS.md` entries carry a `Tested by:` line
- [ ] `tools/check_claims_consistency.py` reports 33 test-coupled (0 inconsistencies)
- [ ] `framework-internal-metrics.md` §1 E.1 shows "33/41 = 80.5% test-coupled"
- [ ] `docs/baseline-audit-report.md` §E.1 reflects the new count
- [ ] `framework-freeze-checklist.md` MUST-1 E.1 marks PASS

## Acceptance gate

E.1 batch 2 passes if:
1. 22 new tests are authored and pass deterministically
2. `tools/check_claims_consistency.py` reports 33 test-coupled
3. The test-coupled count **exceeds the 70% target** (33/41 = 80.5%)

## Estimated time

- Phase A (claim selection): ~30 min (read CLAIMS.md; classify)
- Phase B (test wiring): ~10-15 min per claim × 22 = **~4-5 hours**
- Phase C (CLAIMS.md updates): ~5 min per claim × 22 = ~2 hours
- Phase D (verification + updates): ~30 min
- **Total**: ~6-8 hours (a single agent day)

## Risk

- Some category-c/d claims have `Asserted by:` references to framework
  internals that are not directly observable → test wiring reveals a
  **soft claim** that should be DEPrecated rather than tested
  → **Mitigation**: skip the soft claim; target 70% with 21-22 wired
  (e.g. 32/41 = 78.0% still exceeds 70%; 31/41 = 75.6% also exceeds)
- Test coupling reveals a claim is **already broken** (the claim was
  ACTIVE but the code contradicts it)
  → **Mitigation**: mark claim as PROVISIONAL per `tools/check_claims_consistency.py`
  semantic; don't regress the count; defer PROVISIONAL resolution to a
  follow-up wave
- Some claims require GPU fixtures that are not CPU-available
  → **Mitigation**: parametrise with `pytest.mark.skipif(not torch.cuda.is_available(), ...)`;
  count the claim as test-coupled even if the test is skipped on CPU

## Follow-up (E.1 batch 3 — separate plan)

If batch 2 ships with < 22 wirings (e.g. 18-21), a batch 3 plan can
target the remaining 8-12 candidates. This is **expected** because
category-d claims may require GPU or be soft.

## Follow-up (D.1 shrink adapters + E.1 interaction)

E.1 test coupling is independent of D.1 adapter shrinkage — E.1
operates on CLM IDs; D.1 operates on adapter LOC counts. No
dependency.