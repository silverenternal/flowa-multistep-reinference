# Algorithm improvement — paper-traceability hardening (A.4 + A.7 + B.4)

**Status:** done (Wave 15 A — commit 3ead25f; A.4: 0.171 → 0.938; A.7: 75% → 87.5%; B.4: +5 doctests; 8 new must-fail fixtures in tests/test_theory/negative/)
**Date:** 2026-09-05
**Priority:** high (A.4 + A.7 are HARD gates in rev 2 §3 Phase 2 entry gate;
B.4 is HARD gate everywhere)
**Depends on:** framework-internal-metrics rev 2 (done)
**Owner:** framework maintainer
**Goal:** close per-equation citation density (0.171 → 0.90), promote
must-fail fixtures to 100% of constructive A.0 entries, add real doctests
+ CI wire-up.

## Background

Wave 14 baseline audit revealed three closely-related paper-traceability
gaps (all in `docs/baseline-audit-report.md`):

- **A.4 = 0.171** (14 / 82 public functions in `adaptive_reflow/theory/`
  have explicit paper equation/section references). Rev 2 target:
  ≥ 0.90 by Wave 14.
- **A.7 = 75% strict / 87.5% broad** (must-fail fixtures for
  hypothesis-violation testing). Rev 2 target: 100% of A.0 *constructive*
  entries by Wave 16.
- **B.4 = vacuous pass** (0 doctests collected → 0 failures → empty signal).
  Rev 2 target: 0 failures + ≥ 10 doctests by Wave 13.

All three are HARD gates per rev 2 §3 Phase 2 entry gate.

## Sub-tasks

### A.4.1 — Citation density sweep (0.171 → 0.90)

Per baseline audit next-action #4:
- Annotate `paper_quantities.py` `_with_result` wrappers with `Eq. N` /
  `Section N` anchors (4 funcs)
- Add paper anchors to `validation.py` helpers (`validate_g_admissible`,
  `_detect_zeros`)
- Lift `Theorem 1 (line 87-92)` anchor from `__init__.py` module docstring
  into each public re-export docstring
- Sweep `checkers.py` helpers for missing citations

Target: lift A.4 from 0.171 to ≥ 0.90.

### A.7.1 — Must-fail fixture coverage (75% → 100% constructive)

Per baseline audit next-action #6:
- **Lemma 3**: promote must-fail into `tests/test_theory/test_lemma3_per_cell_coefficient.py`
  (~10 LOC; restrict `test_paper_quantities_reject_invalid_params`
  parametrisation to `per_cell_coefficient_C`)
- **Proposition 2 symmetry**: either add a must-fail
  (`test_g_a_with_unbounded_a_fails_admissibility`) OR formally document
  the Prop-2 / Prop-6 symmetry in
  `docs/adr/0005-fail-closed-audit-code-policy.md`
- Optionally create `tests/test_theory/negative/` as the canonical
  must-fail directory (5 file moves + conftest.py import-path updates)

Target: 100% of A.0 *constructive* entries have ≥ 1 must-fail fixture.

### B.4.1 — Doctests + CI wire-up

Per baseline audit next-action #8:
- Insert worked `>>>` examples into `paper_quantities.py` (13/13 already
  documented) and `checkers.py` (8/9 documented)
- Add `pytest --doctest-modules adaptive_reflow/theory/` as an explicit
  step in `.github/workflows/cpu-tests.yml` (or to `addopts` in
  `pyproject.toml`)
- Treat exit code 5 as a failure in the CI step so silent loss of examples
  fails loudly

Target: ≥ 10 doctests collected, 0 failures.

## Files affected (estimated)

### A.4 sweep
- `adaptive_reflow/theory/paper_quantities.py` (~+4 paper anchors)
- `adaptive_reflow/theory/validation.py` (~+2 paper anchors)
- `adaptive_reflow/theory/checkers.py` (~+10 paper anchors)
- `adaptive_reflow/theory/__init__.py` (~+10 re-export docstring anchors)

### A.7 promotion
- `tests/test_theory/test_lemma3_per_cell_coefficient.py` (NEW)
- `tests/test_theory/negative/` (NEW directory; optional)
- `docs/adr/0005-fail-closed-audit-code-policy.md` (NEW; optional)

### B.4 doctests
- `adaptive_reflow/theory/paper_quantities.py` (~+10 doctests)
- `adaptive_reflow/theory/checkers.py` (~+5 doctests)
- `.github/workflows/cpu-tests.yml` (UPDATE)
- `pyproject.toml` (UPDATE; addopts)

## Acceptance

- [ ] A.4 ≥ 0.90 (re-audit confirms)
- [ ] A.7 = 100% of constructive A.0 entries (re-audit confirms)
- [ ] B.4: ≥ 10 doctests collected, 0 failures
- [ ] All 3 HARD gates pass
- [ ] pytest passes (no regression)
- [ ] mkdocs --strict still exits 0
- [ ] Commit + push

## Estimated time

- A.4: 1-2 hours (sweep + re-audit)
- A.7: 30-60 min (new test files)
- B.4: 30-60 min (doctest insertion + CI wire-up)

Total: ~2-4 hours CPU only.

## Acceptance gate

**Gate name:** `G-ALGO-TRACEABILITY-HARDENING` (new; defined here)

**Pre-condition:** framework-internal-metrics rev 2 §6 baseline audit done (✓)
**Pass conditions:**
- [ ] All acceptance checklist items
- [ ] `docs/baseline-audit-report.md` updated: A.4, A.7, B.4 marked MET
- [ ] `todo/STATUS.md` updated

## Out of scope

- F.2 reproduction work (separate task)
- D.5 conformance battery (separate task)
- A.0 G4 (Theorem 1 rate constant) — covered by
  `algo-improvement-rate-bound.md` (B)