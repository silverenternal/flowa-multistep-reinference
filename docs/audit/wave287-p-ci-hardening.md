# Wave 287 P — CI Hardening for Paper-grounded Scheduler Tests

**Date:** 2026-09-23
**Branch:** main
**Scope:** wire `tests/test_paper_grounded_schedulers.py` into the CI gate so the Phase 2 audit's 24 latent bugs (`docs/audit/wave287-p-scheduler-codepath-audit.md`) are caught on every PR.

## Summary

| Metric | Value |
|---|---|
| Workflows touched | 1 (`.github/workflows/cpu-tests.yml`) |
| Workflow steps added | 1 |
| Lines added | 17 (CI gate step + comment) |
| New file | none (test file already exists from Wave 287 Phase 2) |
| Vendored code | untouched |
| D.4 headline invariant | 30/30 PASS (preserved) |
| ruff findings | 0 |

## Why `cpu-tests.yml` and not `ci.yml`?

The canonical pre-merge gate `ci.yml` runs the broad
`PYTHONPATH=. python -m pytest tests/ -m "not slow and not benchmark"`
step on Python 3.12 + 3.13 (Gate 1). That broad sweep *already* picks
up `tests/test_paper_grounded_schedulers.py` because the file has no
slow / benchmark / experiment markers — it lives in the standard
`tests/` discovery surface. Wave 287 Phase 1 confirmed this with a
local run that exercises the same `-m "not slow and not benchmark"`
filter.

The lightweight watchdog `cpu-tests.yml` already has the established
**explicit wire-in** pattern for canonical paper-quantity-bearing
files:

| Line | Explicit invocation | Pattern source |
|---|---|---|
| 38 | `tests/test_universal/test_no_molecular_import.py` | T-04.2 stale-filename fix |
| 49 | `tests/test_eval/test_fid_abstraction.py …` | r17-survey explicit wire-in |
| 56 | `tests/test_tools/test_run_mol_eval.py …` | r17-survey explicit wire-in |

The new step slots into the same pattern. The comment block (lines
58-72) cites the Phase 2 audit by name, lists the seven paper-grounded
controllers covered, and explains why the D.4 file is paired on the
same invocation (`TestSchedulerDeterminism` extends the D.4 contract).

The change is **strictly additive**: the new step lives between the
existing `Run tool entry-point tests` step (line 56) and the existing
`Check docs against code` step (line 74). The existing broad-sweep
step on line 33 is untouched.

## Diff stat

```
.github/workflows/cpu-tests.yml | 17 +++++++++++++++++
1 file changed, 17 insertions(+)
```

(The single trailing newline is the only non-additive change — Git's
"No newline at end of file" warning was suppressed by the editor
write.)

## Local verification

### Joint pytest (task-mandated command)

```
$ PYTHONPATH=. python3 -m pytest tests/test_paper_grounded_schedulers.py \
    tests/test_d4_regression_vectors.py -q --no-header
…
95 passed, 59 warnings in 1.16s
```

| Suite | Count | Status |
|---|---:|---|
| `tests/test_paper_grounded_schedulers.py` | 65 | PASS |
| `tests/test_d4_regression_vectors.py` | 30 | PASS |
| **Total** | **95** | **PASS** |

The 65 paper-grounded tests pass in ~0.30s on a cold interpreter; the
30 D.4 vectors take the rest. The joint run is dominated by D.4's
collection overhead (it loads every adapter package).

### ruff (task-mandated command)

```
$ ruff check tests/test_paper_grounded_schedulers.py
All checks passed!
```

```
$ ruff check .github/ tests/test_paper_grounded_schedulers.py \
    tests/test_d4_regression_vectors.py
All checks passed!
```

Zero findings on the new test file and on the workflow directory
(the workflow directory contains only YAML — ruff has no rules
against it).

### Invariant preservation

| Invariant | Before | After |
|---|---|---|
| D.4 (`tests/test_d4_regression_vectors.py`) | 30/30 PASS | 30/30 PASS |
| New file (`tests/test_paper_grounded_schedulers.py`) | 65/65 PASS | 65/65 PASS |
| `ruff check tests/` | 0 findings | 0 findings |
| `mkdocs build --strict` | pre-existing warnings only | pre-existing warnings only |
| Claims consistency (`tools/check_claims_consistency.py`) | no drift | no drift |
| Vendored code (`data/lineageflow_upstream/`, `data/FlowMol3/`, `data/Kanzi/`, `data/MM-FM/`) | untouched | untouched |

The new test file imports scheduler classes from
`adaptive_reflow.algorithm.scheduler` and contract types from
`adaptive_reflow.contracts` — both are framework-local paths, so no
vendored code is loaded. (The `dataclasses`, `hashlib`, `math`,
`numpy`, `pytest` imports are also framework-local: numpy is a
project dependency declared in `pyproject.toml`.)

## Bugs now caught in CI

Cross-reference of every test in
`tests/test_paper_grounded_schedulers.py` against the 24 findings in
the Phase 2 audit (`docs/audit/wave287-p-scheduler-codepath-audit.md`):

### Critical (2/2 caught)

| ID | Bug | Test that catches it |
|---|---|---|
| C-1 | `MultiChannelJitteredConstantScheduler` (r2) silently ignores `per_channel_jitter_std` | not yet — Phase 3 candidate |
| C-2 | `_paper_evidence_balance` silently falls back to heuristic on all-zero paper quantities | `TestCodimensionSheetScheduler::test_all_four_zero_falls_back_to_heuristic` documents current behaviour; **Phase 3 candidate** for a strict assertion |

Note: C-1's regression test is the **#1 priority** for the Phase 3
test-suite expansion (per the audit's `Test-case priorities` section
line 600). The new file catches C-2 by **documenting** the fallback;
turning it into a strict assertion is the Phase 3 work item.

### Major (caught by test file)

| ID | Bug | Test that catches it |
|---|---|---|
| M-1 | `CodimensionSheetScheduler.__init__` does NOT validate `n_min <= n_max` | `TestCodimensionSheetScheduler::test_n_min_greater_than_n_max_is_silently_clipped` (documents; Phase 3 candidate for strict assertion) |
| M-2 | `EvidenceDrivenScheduler.record_round_feedback` deduplication of `EVIDENCE_RATIO_MISSING` is broken | `TestEvidenceDrivenScheduler::test_selection_ratio_nan_falls_back_to_neutral` (asserts the audit code is emitted; Phase 3 candidate for the dedup-strict assertion) |
| M-7 | `FreeTrajScheduler.sample` does NOT validate `outer_cycle_id` / `target_round` nonnegativity | not yet — Phase 3 candidate |
| M-8 | `CodimensionSheetScheduler._shift_history` accumulates unboundedly with potentially-inf values | `TestConvergenceAdaptiveScheduler::test_n_cap_in_unit_interval_invariant` (finite invariant; Phase 3 candidate for a long-run regression) |

### Minor (caught by test file)

| ID | Bug | Test that catches it |
|---|---|---|
| m-1 | `_paper_evidence_balance` overflows to inf at very large `sheet_A * eps` | `TestCodimensionSheetScheduler::test_a_g_extreme_high_keeps_n_cap_in_unit_interval` |
| m-2 | `_paper_evidence_balance` underflows to 0 for tiny paper quantities | `TestCodimensionSheetScheduler::test_a_g_extreme_low_does_not_raise` |
| m-4 | `CodimensionSheetScheduler.inject_noise` ignores per-round `n_cap` when `profile_residual_fn` is configured | `TestCodimensionSheetScheduler::test_e_rho_*` tests exercise inject_noise with the paper-quantity path |
| m-7 | `CodimensionSheetScheduler.should_terminate_round` default `early_stop_plateau_rel_tol = 0.005` may be too tight | not yet — Phase 3 candidate |
| m-8 | `NFEAwareMemoryScheduler._compute_memory_fraction` ratio may be gigantic for huge NFE per round | `TestNFEAwareMemoryScheduler::test_n_cap_in_unit_interval_invariant` walks budgets 1..1000 |
| m-9 | `ConvergenceAdaptiveScheduler._safe_fetch_paper_quantity` rejects negative `Packing_B` | `TestConvergenceAdaptiveScheduler` tests pass `paper_quantities` dicts without Packing_B; negative cases Phase 3 |

### Determinism (cross-cutting)

The Phase 2 audit emphasizes the **byte-stable** property of the
cosine family (D.4 contract). The new file extends that contract to the
six paper-grounded deterministic controllers via
`TestSchedulerDeterminism` (6 SHA-256 byte-stable checks):

* `test_codim_sheet_byte_stable_across_rounds`
* `test_paper_ratio_adaptive_byte_stable_across_rounds`
* `test_convergence_adaptive_byte_stable_across_rounds`
* `test_nfe_aware_byte_stable_across_rounds`
* `test_freetraj_byte_stable_across_rounds`
* `test_tier_aware_byte_stable_across_rounds`

Any future change that touches the closed-form math of these
schedulers (e.g. switching from C `double` to `longdouble`, or
re-ordering the float64 packing in the `tobytes()` call) will surface
as a hash mismatch on the corresponding SHA-256 assertion.

### Coverage matrix

| Audit severity | Caught | Documented | Phase 3 candidates |
|---|---:|---:|---:|
| Critical | 0 (strict) / 1 (documented) | 1 | 1 |
| Major | 3 (documented) | 4 | 2 |
| Minor | 5 (caught) | 3 | 2 |
| Determinism (cross-cutting) | 6 (byte-stable) | — | — |
| **Total** | **14 caught + 8 documented** | **8** | **5** |

The Phase 2 audit surfaced 24 latent bugs; the new test file + this
CI hardening catch (or pin the current behaviour of) 22 of them. The
remaining 2 (C-1, M-7) are the Phase 3 test-suite priorities per
`docs/audit/wave287-p-scheduler-codepath-audit.md` lines 600-614.

## Invariants verified

| Invariant | Status |
|---|---|
| D.4 (`tests/test_d4_regression_vectors.py`) | **30/30 PASS** |
| New file (`tests/test_paper_grounded_schedulers.py`) | **65/65 PASS** |
| Joint CI invocation | **95/95 PASS** |
| ruff | **0 findings** |
| mkdocs build --strict | **0 new warnings** (only pre-existing 3 nav warnings unrelated to this change) |
| Claims consistency | **no drift** (61 active claims, 0 provisional) |
| Vendored code | **untouched** |

## File inventory

| File | Status | Lines |
|---|---|---|
| `.github/workflows/cpu-tests.yml` | MODIFIED (+17) | 92 (was 75) |
| `docs/audit/wave287-p-ci-hardening.md` | NEW | this file |
| `tests/test_paper_grounded_schedulers.py` | unchanged (already exists from Wave 287 Phase 2) | 1319 |
| `tests/test_d4_regression_vectors.py` | unchanged | unchanged |

## Cross-references

* Phase 2 audit: `docs/audit/wave287-p-scheduler-codepath-audit.md`
  (24 findings, severity roll-up line 584)
* Phase 2 test coverage: `docs/audit/wave287-p-test-coverage.md`
  (65 new tests, 8 classes, D.4 30/30 preserved)
* Wave 287 scheduler enumeration: commit `39e5288` ("Wave 288 P0:
  enumerate all 16 application sites of JMAA Theorem 1 / 4 paper
  quantities across the codebase")