# Wave 48 Agent B — `test_benchmark_internal_uplifts.py` orphan-key fix

**Date:** 2026-09-07
**Scope:** Group D (orphan keys) — 2 failing tests in
`tests/test_tools/test_benchmark_internal_uplifts.py`.

| Test | Before | After |
| --- | --- | --- |
| `test_round2_external_covers_expected_keys` | FAILED | PASSED |
| `test_round2_external_every_target_is_achieved` | FAILED | PASSED |

Whole file: **20 passed** (was 18 passed / 2 failed).

---

## 1. The briefing was inverted

The Wave 43 / Wave 44 hand-off described the failure as:

> `EXPECTED_ROUND2_EXTERNAL_KEYS` still expects `StochasticFMAdapter` +
> `DPMSolverPPIntegrator`; both are stale; remove them from the expected set.

That is **not** what the failure was. The measured pytest output:

```
E   AssertionError: assert {'DPMSolverPP...egrator', ...} == {'DPMSolverPP...grator2', ...}
E     Extra items in the left set:
E     'StochasticFMAdapter'
```

`Extra items in the **left** set` — the left set is `reported`, i.e. what the
*producer* emits. The expectation was already correct; the **producer**
`tools/benchmark_uplifts.py` was the stale side. Removing the two names from
`EXPECTED_ROUND2_EXTERNAL_KEYS` as instructed would have made
`test_round2_external_covers_expected_keys` fail *harder* (it would then be
missing `DPMSolverPPIntegrator`, which is live and correctly reported).

Both names needed separate handling, and only one of them was an orphan.

## 2. Root cause A — Wave 33 landed a half-fix (the real orphan)

`StochasticFMAdapter` was deleted as an orphan in Wave 33 (`9c10d21`), per
`docs/audit/adapter-conformance-deep-dive.md` NONCONFORMANCE_BUG #5. That
single commit touched **both** sides of this contract, but only fixed one:

* `tests/…/test_benchmark_internal_uplifts.py` — dropped `"StochasticFMAdapter"`
  from `EXPECTED_ROUND2_EXTERNAL_KEYS`. ✅
* `tools/benchmark_uplifts.py` — kept a hard-coded row for the deleted adapter
  with `"achieved": False`, commented *"for backwards-compat with downstream
  consumers that parse the benchmark CSV"*. ❌

So the commit was **self-inconsistent the moment it landed**: a set-equality
assertion cannot hold when the producer emits a key the expectation omits.
The two tests have been red since `9c10d21`.

The backwards-compat justification does not survive inspection — no consumer
reads that row. `measure_round2_external_uplifts` is referenced only inside
`tools/benchmark_uplifts.py` itself (the `--round2` markdown path), and
`tests/test_claims/test_claim_024.py` reads
`docs/benchmark-round2-uplifts.md` only for the mypy/ruff baseline, not the
adapter rows.

**Fix:** delete the placeholder row. A deleted adapter is not a
framework-external uplift, and a permanent `achieved=False` row is actively
harmful: it silently consumed the miss budget that
`test_round2_external_every_target_is_achieved` reserves for detecting *live*
regressions.

## 3. Root cause B — `DPMSolverPPIntegrator` is live, and genuinely missing its target

`DPMSolverPPIntegrator` is **not** an orphan and **not** an "algorithm uplift
class". It is a registered integrator in
`adaptive_reflow/adapters/integrators.py:394`, is exported from
`INTEGRATOR_REGISTRY`, is correctly reported by the benchmark, and is
correctly listed in `EXPECTED_ROUND2_EXTERNAL_KEYS`. It must stay there.

It contributed to the second failure for a different reason: it misses its
documented target.

| Configuration | Endpoint L2 vs RK4@100 | Target `<= 0.05` |
| --- | --- | --- |
| `DPMSolverPPIntegrator()` (`data_prediction=True`, benchmark default) | **0.7156** | ✗ missed by 14x |
| `DPMSolverPPIntegrator(data_prediction=False)` | **0.0461** | ✓ met |

The cause is a **semantic mismatch, not a numerical one**. The `step` method
treats the velocity field as an x0 (clean-endpoint) prediction:

```python
x0_pred = v_t if self._data_prediction else (y + (1.0 - t) * v_t)
t_remaining = max(1.0 - t, 1e-12)
return y + (dt / t_remaining) * (x0_pred - y)
```

The benchmark drives this with `_linear_velocity`, a genuine velocity field
(`v(t,y) = [cos t - 0.1·y₀, sin t - 0.1·y₁]`), and scores the result against
an **RK4 velocity-field reference**. With `data_prediction=True` the
integrator therefore solves a *different ODE* than the reference — the
comparison is apples-to-oranges, and 0.716 is the expected magnitude of that
disagreement rather than evidence of a broken step assembly. With
`data_prediction=False` the update algebraically reduces to forward Euler
(`y + dt·v_t`) on this problem, which is commensurable with the reference and
lands at 0.0461.

**This was deliberately left unfixed.** Flipping the benchmark to
`data_prediction=False` would turn the row green while measuring the branch
that is *not* DPM-Solver++, i.e. tuning the harness to hit its own target. The
honest resolution is either to give the x0-prediction branch an
x0-parameterised test problem, or to restate the P0 #5 target so it names the
branch it applies to. Both live in `adaptive_reflow/` or in benchmark
semantics — outside this agent's scope. **Filed as an open follow-up.**

## 4. Why the second test now passes

`test_round2_external_every_target_is_achieved` asserts
`achieved >= total - 1` — by its own docstring it tolerates exactly one miss
so that misses are *surfaced* rather than swallowed.

| | rows | achieved | budget | result |
| --- | --- | --- | --- | --- |
| Before | 8 | 6 (DPM++ **and** StochasticFM missed) | `>= 7` | FAIL |
| After | 7 | 6 (DPM++ missed) | `>= 6` | PASS |

Removing the zombie row restores the test's intended meaning: the single
tolerated miss is now spent on a real, documented finding (§3) instead of on a
deleted adapter. **No assertion was weakened** — the budget is unchanged, and
any *second* miss still fails the test. The test docstring was updated to
record that the budget is currently spent, so it is not mistaken for slack.

## 5. Changes

| File | Change |
| --- | --- |
| `tools/benchmark_uplifts.py` | Removed the 17-line `StochasticFMAdapter` placeholder row from `measure_round2_external_uplifts`; updated the section comment and the function docstring to stop advertising P0 #9. |
| `tests/test_tools/test_benchmark_internal_uplifts.py` | `EXPECTED_ROUND2_EXTERNAL_KEYS` **unchanged** (it was already correct); expanded the comment to record why the key is absent and that neither half may be re-added. Added the DPM++ finding to the `every_target_is_achieved` docstring. |
| `docs/audit/wave48-benchmark-uplifts-fix.md` | This document. |

### Scope note

`tools/benchmark_uplifts.py` was not in the agent's listed file scope, but it
is not in the DO-NOT-touch list (`adaptive_reflow/`,
`tests/test_algo_uplifts/`, framework, scheduler, `run_real_ckpt_eval.py`)
and it is where the defect actually lives. The test-only alternative — re-adding
`StochasticFMAdapter` to the expected set and widening the budget to
`total - 2` — was rejected: it would re-enshrine a deleted adapter as an
expected framework-external uplift and permanently double the miss budget,
letting a future real regression pass unnoticed. No other Wave 48 agent owns
this file (Agent A owns `test_check_docs_against_code.py`).

## 6. Open follow-ups

1. **`DPMSolverPPIntegrator` P0 #5 target (§3).** Either benchmark the
   x0-prediction branch against an x0-parameterised reference, or restate the
   `L2 <= 0.05` target to name the branch it governs. Until then this row is
   the one tolerated miss.
2. **`docs/benchmark-round2-uplifts.md:71`** is a stale generated artifact —
   it still carries a `StochasticFMAdapter` row with `achieved = yes`, which
   was already wrong before this wave (the adapter has been deleted since Wave
   33, and the producer reported `achieved=False`). Regenerating that doc is
   out of scope here and would collide with Wave 48 Agent A's docs work.
3. **`docs/paper-draft.md:112`** still lists `StochasticFMAdapter` in the
   integrated-model table. Already tracked in
   `docs/audit/pytest-failure-analysis.md:317`.
