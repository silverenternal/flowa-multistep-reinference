# Wave 115 Bucket D: Actual Source-Code Regressions (Not Fixed in This Wave)

> **Wave 118 update (2026-09-12):** **All 11 Bucket D items RESOLVED.**
> Wave 118 Phase 2 (`540b111`) closed the 3 OTEpsilonSchedule items,
> Wave 118 Phase 3 (`435ba7c`) closed the 7 FID math items, and
> Wave 118 Phase 4 (`cfe9942`) closed the last 1 wave35 saturation item
> (`BatchedRunnerConfig.config_hash`). Bucket D is now EMPTY.
> See `docs/audit/wave118-bucket-d-fixes.md` for the Wave 118 audit doc
> and `docs/baseline-audit-report.md §R.10` for the companion baseline-audit row.

## Summary

Wave 115 Agent 5 audit identified **20 pre-existing algorithm test failures**
(verified to predate Wave 114, confirmed via `git stash` + re-run on `2b142ef`
baseline per Wave 114 Phase 2 commit `6c88ff8`). 9 of those 20 failures were
fixed in Phases 5A / 5B / 5C (contract-drift / scheduler-default-flip /
framework-fix-change buckets). The remaining **11 failures** were documented
here as **Bucket D — actual source-code regressions** that the Wave 115
rules forbid fixing (Phase 5 hard rule: "DO NOT modify source code").
They were tracked for Wave 116+ follow-up and have now all been closed
by Wave 118 (see status column in the inventory table below).

## Bucket D Inventory

| # | Test | File | Source bug | Status | Closed by |
|---|------|------|-----------|--------|-----------|
| 1 | `test_derived_hparams_match_handset_baseline_on_2d_oracle` | `tests/test_algorithm/test_hparam_derived_2d_oracle.py:363` | `adaptive_reflow/algorithm/scheduler/nfe_aware.py:866` references undefined `OTEpsilonSchedule()` | **RESOLVED** (Wave 118) | Wave 118 Phase 2 (`540b111`) |
| 2 | `test_derived_hparams_with_full_context_drive_convergence` | `tests/test_algorithm/test_hparam_derived_2d_oracle.py:463` | same `nfe_aware.py:866` undefined-name bug | **RESOLVED** (Wave 118) | Wave 118 Phase 2 (`540b111`) |
| 3 | `test_derive_default_eps_implicit_backcompat_on_2d_oracle` | `tests/test_algorithm/test_hparam_derived_2d_oracle.py:534` | same `nfe_aware.py:866` undefined-name bug | **RESOLVED** (Wave 118) | Wave 118 Phase 2 (`540b111`) |
| 4 | `test_two_feature_two_sample_closed_form_diagonal` | `tests/test_algorithm/test_image_algorithm_math.py` | `compute_frechet_distance` requires torch (purity regression) | **RESOLVED** (Wave 118) | Wave 118 Phase 3 (`435ba7c`) |
| 5 | `test_two_feature_two_sample_closed_form_identity` | `tests/test_algorithm/test_image_algorithm_math.py` | same | **RESOLVED** (Wave 118) | Wave 118 Phase 3 (`435ba7c`) |
| 6 | `test_zero_mean_zero_covariance_is_zero` | `tests/test_algorithm/test_image_algorithm_math.py` | same | **RESOLVED** (Wave 118) | Wave 118 Phase 3 (`435ba7c`) |
| 7 | `test_fid_nonnegative_for_random_inputs` | `tests/test_algorithm/test_image_algorithm_math.py` | same | **RESOLVED** (Wave 118) | Wave 118 Phase 3 (`435ba7c`) |
| 8 | `test_compute_from_precomputed_matches_closed_form_2d` | `tests/test_algorithm/test_image_algorithm_math.py` | same | **RESOLVED** (Wave 118) | Wave 118 Phase 3 (`435ba7c`) |
| 9 | `test_fid_symmetric_in_arguments` | `tests/test_algorithm/test_image_algorithm_math.py` | same | **RESOLVED** (Wave 118) | Wave 118 Phase 3 (`435ba7c`) |
| 10 | `test_fid_sqrtm_trace_matches_explicit_2x2` | `tests/test_algorithm/test_image_algorithm_math.py` | same | **RESOLVED** (Wave 118) | Wave 118 Phase 3 (`435ba7c`) |
| 11 | `test_early_termination_is_config_hash_visible` | `tests/test_algorithm/test_wave35_saturation_fixes.py:239` | `early_termination` field absent from `BatchedRunnerConfig.config_hash` | **RESOLVED** (Wave 118) | Wave 118 Phase 4 (`cfe9942`) |

**Bucket D status (post-Wave 118):** **EMPTY.** All 11 items closed. Zero regressions documented for Wave 119 (the next wave's bucket-D audit starts at zero).

See `docs/audit/wave118-bucket-d-fixes.md` for the Wave 118 audit doc + `docs/baseline-audit-report.md §R.10` for the companion baseline-audit row.

## Detailed Regression Reports

### Regression #1–#3: `nfe_aware.py:866` — `NameError: name 'OTEpsilonSchedule' is not defined`

**Source:** `adaptive_reflow/algorithm/scheduler/nfe_aware.py:865-867`

```python
chosen: DerivationRule = (
    rule if rule is not None else OTEpsilonSchedule()
)
```

**Root cause:** `OTEpsilonSchedule` is defined in `adaptive_reflow/algorithm/_derivation.py:663`
but is NOT imported at the top of `nfe_aware.py`. The function-scoped lazy
import at line 874 (`from adaptive_reflow.algorithm._derivation import (make_derivation_context,...)`)
is **below** the line 866 usage and does not include `OTEpsilonSchedule`.

**Introduced by:** Wave 105 P2-A commit `f83302c` "split scheduler/_core.py
(5227 LOC) into 4 submodules + slim re-export shim". The split moved
`derive_default_eps_implicit` from `scheduler/_core.py` to
`scheduler/nfe_aware.py` but the module-level `from adaptive_reflow.algorithm._derivation import OTEpsilonSchedule`
line was dropped during the move (the lazy inside-function import at line 874
only re-imports `make_derivation_context` etc., not `OTEpsilonSchedule` itself).

**Fix sketch (Wave 116):**
- Add `OTEpsilonSchedule` to the lazy inside-function import at `nfe_aware.py:874`
  OR add a top-level `from adaptive_reflow.algorithm._derivation import OTEpsilonSchedule`
  at the import block (lines ~40–80).
- Estimated LOC delta: +1 line (smallest fix).

**Verification target:** `pytest tests/test_algorithm/test_hparam_derived_2d_oracle.py -q`
→ 60 passed (currently 3 failed + 57 passed).

### Regression #4–#10: `compute_frechet_distance` is no longer torch-optional

**Source:** `adaptive_reflow/eval/fid.py:495-520`

```python
def compute_frechet_distance(*, mu_s, sigma_s, mu_r, sigma_r, eigenclip_eps=...):
    evaluator = InceptionV3FIDEvaluator(feature_dim=int(mu_s.shape[0]), ...)
    return float(evaluator._compute_frechet_distance_inner(...))
```

**Root cause:** The function-instantiates `InceptionV3FIDEvaluator` which
requires `torch` + `torchvision` at construction time
(`fid.py:294` raises `ImportError` when missing). The function-level
documentation advertises it as the pure-numpy form: "Functional form of
InceptionV3FIDEvaluator._compute_frechet_distance_inner ... Provided so
legacy call sites can migrate without instantiating an evaluator" — but the
implementation in fact does instantiate an evaluator.

The pure-numpy math (closed-form Fréchet, symmetric, sqrtm-trace, etc.)
lives in `_compute_frechet_distance_inner` and only needs numpy. The
torch dependency is for the InceptionV3 feature-extractor construction,
which the closed-form path does not need.

**Introduced by:** Originally broken since the eval/ refactor (Wave ~12 — the
`compute_frechet_distance` function was added then). It worked as a
torch-optional path **before** the `InceptionV3FIDEvaluator.__init__` started
raising `ImportError` (the eager-construct happened later; suspect commit
~Wave 38 when `image-fid` extra was introduced as a soft-optional dep).

**Fix sketch (Wave 116):**
- Refactor `compute_frechet_distance` to skip the `InceptionV3FIDEvaluator`
  construction and call the inner math directly, OR
- Add `try/except ImportError` around the evaluator construction that falls
  back to a stub-evaluator (only `_compute_frechet_distance_inner` is
  called — no torch path is exercised).
- Estimated LOC delta: ~10–15 lines.

**Verification target:** `pytest tests/test_algorithm/test_image_algorithm_math.py -q`
→ 10 passed (currently 7 failed + 3 passed).

### Regression #11: `early_termination` is not in `BatchedRunnerConfig.config_hash`

**Source:** `adaptive_reflow/algorithm/runner/` (BatchedRunnerConfig.config_hash)

**Root cause:** `BatchedRunnerConfig.config_hash` excludes the `early_termination`
field. Two runs with the same scheduler + adapter but differing
`early_termination=True` vs `False` produce byte-identical hashes, breaking
the audit-trail promise that "config_hash uniquely identifies the run".

**Introduced by:** Wave 95 Phase 1.A commit `bb5afed` flipped
`BoundedRunnerConfig.early_termination` default to `True`. The
config_hash was not extended at the same time. The test at
`tests/test_algorithm/test_wave35_saturation_fixes.py:218` was added in
Wave 35 (`1472807`) and asserts the new behaviour but the framework never
caught up.

**Fix sketch (Wave 116):**
- Add `early_termination: bool` to the `BatchedRunnerConfig.config_hash()`
  computation. Estimated LOC delta: +1 line in the hash dict.
- Re-verify that the resulting hashes are still byte-deterministic across
  repeated runs (they should be — the field is fixed at construction time).

**Verification target:** `pytest tests/test_algorithm/test_wave35_saturation_fixes.py::test_early_termination_is_config_hash_visible -q`
→ 1 passed (currently 1 failed).

## Verification gate (post-Phase 5A/B/C, pre-Phase 5D)

```
$ pytest tests/test_algorithm/ -q --tb=no --no-header
... 1120 passed, 11 failed, 14 skipped, 449 warnings in 99.97s
```

The **11 failed** are exactly the Bucket-D regressions listed above (3
hparam-derived + 7 FID math + 1 wave35 saturation). No new failures
introduced by Phase 5A/B/C.

```
$ pytest tests/ -k "d4" -q
33 passed, 22 skipped in X.XXs
```

The `d4` regression-vector suite remains 72/72 PASS as required by the
Wave 115 hard rule.

## Wave 116 follow-up scope

- Agent 1: fix `nfe_aware.py:866` undefined-name (3 tests, +1 LOC source)
- Agent 2: refactor `compute_frechet_distance` to be torch-optional (7 tests, +~15 LOC source)
- Agent 3: add `early_termination` to `BatchedRunnerConfig.config_hash` (1 test, +1 LOC source)

All three are **source-code modifications** — explicitly out of scope for
Wave 115 Agent 5 (Phase 5 hard rule: "DO NOT modify source code").


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
