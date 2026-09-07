# Wave 14 — Algorithm improvement A + 9 baseline audits

**Status:** done (Wave 14: 11 pending tasks parallelised across 3 workflows — re-pointed Theorem1StatementChecker + 36-uplift isolation tests + F.5 env_hash infrastructure) (+ Wave 15: parallel repair of 11 framework gaps closed all sub-items; Wave 17-19: extended the 36-uplift isolation suite; Wave 29: re-audit confirmed A.0 row green; Wave 41-54: glue-layer extensions consume these 11 tasks)
**Date:** 2026-09-05
**Owner:** framework maintainer
**Goal:** execute Algorithm improvement A (re-point Theorem1StatementChecker to
true R^2 BL) + run all 9 baseline audits from framework-internal-metrics rev 2
§6.

## Background

Wave 12 high-3 (A1-high-3) added `planar_bl_convergence_witness` to
`lipschitz_diagnostic.py` with the explicit `PLANAR_BL_CONSTANT = sqrt(2/pi)`
rate bound. The agent's own follow-up note flagged that
`theorem1_bl_convergence_witness` and `Theorem1StatementChecker` still used
the old 1-D y=0 projection. Wave 14 A fixes that.

In parallel, framework-internal-metrics rev 2 §6 listed 9 baseline audits
needed before Wave 13+ work. Wave 14 runs them all.

## Delivery

### A — Re-point Theorem1StatementChecker

- Files changed: `checkers.py` + `tests/test_theory/test_theorem1_unified.py`
- Tests: 9/9 pass (7 existing + 2 new planar-path tests)
- Pre-existing tests preserved: 44/44 pass in test_theory/ (excluding
  pre-existing rdkit-blocked `test_proposition6_escaping_sharpness.py`)
- Pre-existing failures confirmed (NOT introduced by A): rdkit missing in
  sandbox, mkdocs nav missing `docs/baseline-audit-report.md` (W1 created
  it during this wave)
- Commit: `6d12744` (not pushed per directive)

**Key design choices:**
- **Lazy importlib bypass** for `PlanarBLConvergenceReport` to avoid rdkit
  import in `adaptive_reflow.eval.__init__` when only checkers.py is loaded.
- **TYPE_CHECKING-only import** for the dataclass — preserved as public
  surface but doesn't trigger eval __init__.
- **2 new tests** independently re-run the planar witness with same seed
  and assert checker output matches `bl_distances[idx_min]` to 1e-12
  tolerance.

### 9 Baseline Audits → `docs/baseline-audit-report.md`

See that file for full per-audit detail (524 lines). Summary:

| Metric | Current | Rev 2 target | Gap |
|---|---|---|---|
| A.0 | 20 statements + 7 gaps | parity | none blocking |
| A.4 | 0.171 | ≥ 0.90 | -0.729 |
| A.7 | 75% strict | 100% constructive | -25pp |
| B.4 | vacuous | 0 failures | MET vacuously |
| D.3 | 226/226 = 100% hand | 18/18 against D.5 | D.5 missing |
| D.5 | MISSING | live by Wave 14 | 1 file |
| E.2 | 0.571 | ≥ 0.9 | -0.329 |
| F.2 | 4/8 REPRODUCED | ≥ 6/8 | -2 rows |
| F.5 | MISSING | HARD gate | 4 artifacts |

## Top next actions (per audit report)

1. **F.5 env_hash infrastructure (HARD gate blocker)** — see
   `todo/algo-improvement-env-hash.md`
2. **D.5 conformance battery** — see
   `todo/algo-improvement-conformance-battery.md`
3. **A.4 + A.7 + B.4 paper-traceability hardening** — see
   `todo/algo-improvement-traceability-hardening.md`
4. **F.2 flip NOT_REPRODUCED → REPRODUCED** — see
   `todo/algo-improvement-f2-reproduction.md`
5. **A.0 G4 (= Algorithm improvement B)** — already in
   `todo/algo-improvement-rate-bound.md`

## Acceptance gates

- `G-ALGO-PLANAR-BL` (A) passed
- `G-FRAMEWORK-HEALTH` §6 (audits baseline populated)

## Caveats

- Pre-existing environmental failures (rdkit, mkdocs nav) confirmed via
  stash + rerun
- Algo C (uplift isolation tests) still in progress (workflow `w96dowom2`)
- Algo B (rate bound theorem) blocked on A — **now unblocked**
- uv.lock drift discovered (framework lacks own uv-managed venv);
  tracked as part of F.5 task

## Wave 56 close-out

Status refreshed: Wave 14 (3 parallel workflows) unblocked Algo B + shipped the 36-uplift isolation suite. Wave 15 extended the suite; Wave 29 re-audit confirmed A.0 row green. Wave 41-54 glue-layer extensions build on top. F.5 env_hash infrastructure (Wave 14 P1) remains the canonical "environment state" gate. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).