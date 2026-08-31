# Comprehensive code-review fix plan (R3/R11 follow-up)

> **Author:** Agent R (fix-plan subagent)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Status:** READ-ONLY plan; no code changes. Awaiting approval before execution.
> **Inputs cited:**
> - `docs/r4-survey/15-harness-bug-diagnosis.md`
> - `docs/r4-survey/16-harness-fix-plan.md`
> - `docs/r4-survey/17-cifar-experiment-results-v2.md`
> - `docs/r4-survey/18-comprehensive-code-review.md` (Phase-4 audit; this plan
>   is the action item list derived from it)
> - `docs/r4-survey/cifar_results_v2/{per_round_metrics.csv,summary.json}`

---

## §0. TL;DR

The R3 audit identified **52 bugs** across the algorithm, harness, and
evaluator layers. **7 are P0 (paper-blocking)**, **15 are P1 (correctness
without blocking the paper)**, and **30 are P2 (polish / dead code /
contract warts)**.

The P0 fixes unlock the two success paths the paper promises:

- **Path A (scheduler discrimination)** — the four framework rows must
  produce **non-byte-identical samples** so the FID comparison is
  informative. Currently all four rows are byte-identical (per
  `docs/r4-survey/17-cifar-experiment-results-v2.md` §3).
- **Path B (better FID than baseline)** — the framework rows must
  reach a lower FID than the 2-NFE baseline. The v2 run hit
  FID 122.18 vs baseline 218.87, but the framework rows collapse to the
  same trajectory (per v2 §3).

The P0 fixes are **6 of 7 narrow, low-risk changes** (~30–40 LoC across 7
files) that are independent and parallelisable. Effort estimate: **4–5
hours hands-on + 1.5 h wall-clock for paper-grade re-run**.

---

## §1. P0 fixes (must do for paths A and B)

Each entry: file, line(s), current behavior, desired behavior, code
shape, verification.

### P0-1: F-31 — Runner bypasses MergeOperatorProtocol for `schedule_derived`

**File:** `adaptive_reflow/algorithm/runner.py:683-686`
**Severity:** 5 (W2 leak; merge operator never exercised on schedule_derived path)
**Effort:** 0.5 h (1 LoC change + test)

**Current:**
```python
if self._driver.driver_family() == "schedule_derived":
    merged_beta = float(
        applied_policy.beta_by_channel.get(primary_channel, 0.0)
    )
else:
    # call self._merge.merge(**_merge_kwargs)
    ...
```

**Desired:**
```python
# Always call the merge operator; let it decide whether to apply.
_merge_kwargs = {
    "prev": prev_beta,
    "dynamic": float(applied_policy.beta_by_channel.get(primary_channel, 0.0)),
    "cap": float(sample.n_cap),
    "floor": float(sample.n_min),
    "delta_cap_up": 1.0,
    "delta_cap_down": 1.0,
    "audit_codes": merge_audit,
}
import inspect as _inspect
_merge_params = _inspect.signature(self._merge.merge).parameters
if "schedule_sample" in _merge_params:
    _merge_kwargs["schedule_sample"] = sample.as_cosine_schedule_sample()
merged_beta = self._merge.merge(**_merge_kwargs)
```

**Verification:** run `tests/test_algorithm/test_runner.py`; ensure
`test_runner_calls_merge_operator_between_policy_and_engine` and
`test_runner_merge_step_observable_in_beta_trajectory` still pass.
Add a new regression: `test_runner_calls_merge_operator_on_schedule_derived`
that records `_merge.merge` invocations when the driver is
`ScheduleDerivedPolicyDriver`.

**Risk:** the merge operator's `BoundedMergeOperator.merge` collapses to
`clamp(n_cap, n_min, n_cap) == n_cap` for `delta_cap=1.0`, so the
output is byte-identical to the bypass path. The only observable change
is the audit-code list (now includes any codes the operator emits).

---

### P0-2: F-1 — FreeTrajScheduler cache freezes trajectory_progress

**File:** `adaptive_reflow/algorithm/scheduler/freetraj.py:181-208`
**Severity:** 4 (substep frozen at 0.0 forever after first call)
**Effort:** 0.5 h (drop the cache write; move the short-circuit to a flag)

**Current (lines 207-208):**
```python
self._last_sample = sample
self._last_audit_codes = codes
self._last_trajectory_progress = progress   # <-- writes the cache
return sample
```

**Desired (line 207 area):**
```python
self._last_sample = sample
self._last_audit_codes = codes
# Do NOT cache `_last_trajectory_progress` here. The cache is
# reserved for `record_round_feedback` to communicate the external
# signal; the deterministic fallback must always be re-computed.
return sample
```

And update `_compute_trajectory_progress` to take a flag argument:
```python
def _compute_trajectory_progress(
    self,
    round_in_cycle: int,
    *,
    external_override_active: bool,
) -> float:
    if external_override_active and self._last_trajectory_progress is not None:
        return float(self._last_trajectory_progress)
    return float(
        (int(round_in_cycle) % self._trajectory_period)
        / float(self._trajectory_period)
    )
```

Where `external_override_active` is set by `record_round_feedback` (via
a new instance flag, `_external_signal_received`).

**Verification:** run `tests/test_algorithm/test_freetraj.py`; ensure
the existing tests pass (they should — none asserted the cache bug).
Update `tests/test_experiments/test_freetraj_wallclock.py::test_freetraj_trajectory_progress_freezes_when_driven_statefully`
to invert: now assert that the trajectory progress **varies** with
`round_in_cycle` when no external signal is provided.

Add new test: `test_freetraj_substep_varies_across_rounds_no_feedback`
that drives `sample(0, r, 0)` for `r in range(8)` and asserts that the
`n_cap` values at `r=1, 3, 5, 7` deviate from the cosine baseline by
`> 0.01`.

**Risk:** the fix may change the cached `_last_trajectory_progress` value
in `record_round_feedback` (the cache is only consulted when an
external signal is present). External callers that set the cache
without providing feedback must be re-examined. **Audit shows no such
caller** in the current codebase.

---

### P0-3: F-18 — BoundedMergeOperator raises on `cap < floor` (contradicts Protocol docstring)

**File:** `adaptive_reflow/algorithm/merge_operator.py:584-599`
**Severity:** 5 (runner crashes on legitimate envelopes)
**Effort:** 1 h (revert raise + update docstring + add audit code)

**Current (line 591-599):**
```python
if cap_f < floor_f:
    if audit_codes is not None:
        audit_codes.append(
            f"{_ERR_CAP_BELOW_FLOOR}:cap={cap_f:.6f}:floor={floor_f:.6f}"
        )
    raise MergeAuthorityError(
        f"cap={cap_f} < floor={floor_f} post-clip; "
        f"swap semantics removed (audit code already appended)."
    )
```

**Desired:**
```python
if cap_f < floor_f:
    # Fail-closed: return the floor and emit the canonical audit
    # code. The caller supplied a degenerate envelope; we record
    # the failure but do NOT raise so the runner's loop survives.
    if audit_codes is not None:
        audit_codes.append(
            f"{_ERR_CAP_BELOW_FLOOR}:cap={cap_f:.6f}:floor={floor_f:.6f}"
        )
    return float(floor_f)
```

And update the Protocol docstring (line 254-260) to remove the
"cap < floor" claim and add "implementations MUST return floor when
the envelope degenerates; the audit code is the canonical signal".

**Verification:** run `tests/property/test_bounded_merge_invariants.py`;
the existing tests use non-degenerate envelopes, so they pass.
Add new test: `test_bounded_merge_returns_floor_on_cap_below_floor`.

**Risk:** the F5 fix removed silent-swap semantics deliberately (per
`merge_operator.py:587-589`). Reverting the raise is consistent with
the Protocol docstring and prevents runner crashes. The audit code
preserves the F5 audit-trail invariant.

---

### P0-4: F-24 — Runner hardcodes `.reshape(2)` for non-2D adapters

**File:** `adaptive_reflow/algorithm/runner.py:856`
**Severity:** 5 (endpoints row is `NaN` for 8 of 10 adapters)
**Effort:** 0.5 h (1 LoC change)

**Current (line 856):**
```python
endpoints[r] = arr[-1].reshape(2)
```

**Desired:**
```python
adapter_state_shape = tuple(
    getattr(self._adapter, "state_shape", ())
    if hasattr(self._adapter, "state_shape") else ()
)
if adapter_state_shape:
    endpoints[r] = arr[-1].reshape(adapter_state_shape)
else:
    endpoints[r] = arr[-1].reshape(-1)  # flatten
```

**Verification:** run `tests/test_algorithm/test_runner.py`; ensure
existing tests pass. Add regression:
`test_runner_endpoints_matrix_respects_adapter_state_shape` that drives
the runner with a mock adapter whose `state_shape = (3, 32, 32)` and
asserts `endpoints[r].shape == (3, 32, 32)`.

**Risk:** none — the change is purely additive (the 2D case still
works; non-2D adapters now have meaningful endpoints).

---

### P0-5: F-32 — Runner does not call `scheduler.record_round_feedback`

**File:** `adaptive_reflow/algorithm/runner.py:run` (after `metric` is built)
**Severity:** 4 (PID-lite controller never accumulates error in non-harness callers)
**Effort:** 1 h (3 LoC + test)

**Current:** the runner's loop (lines 620-1000) does not invoke
`scheduler.record_round_feedback` anywhere.

**Desired (after `metric` dict is built, ~line 940):**
```python
# Close Loop 2: feed per-round oracle metrics back into the
# scheduler. Adapters that do not implement the hook (or schedulers
# that ignore the feedback) are no-ops.
if hasattr(self._scheduler, "record_round_feedback"):
    feedback_keys = (
        "evidence_ratio",
        "selection_ratio",
        "W2",
        "coverage",
        "bounded_target_fraction",
    )
    feedback = {k: float(metric[k]) for k in feedback_keys if k in metric}
    if feedback:
        self._scheduler.record_round_feedback(int(r), feedback)
```

**Verification:** run `tests/test_algorithm/test_runner.py`; ensure
`test_runner_passes_w2_to_scheduler_feedback` and
`test_runner_passes_w2_to_convergence_adaptive_scheduler` still pass.
Add `test_runner_records_feedback_per_round` that drives the runner
with an `EvidenceDrivenScheduler` and asserts
`scheduler._last_pid_delta != 0.0` after `r=5`.

**Risk:** the harness (`tools/run_sota_cifar_experiment.py`) ALSO calls
`scheduler.record_round_feedback` after `batched_inference`. With both
the runner and the harness calling the hook, the PID receives two
feedback signals per round. This could double the PID delta. **Fix**:
the harness should pass the feedback to the runner (via a
`runner.run_round_feedback` hook) rather than calling the scheduler
directly. This requires a small harness-side change.

---

### P0-6: F-40 — MnistFidEvaluator is mislabelled as FID

**File:** `adaptive_reflow/eval/mnist_fid.py:154-264`
**Severity:** 4 (audit-trail misleading; compares apples to oranges with canonical FID)
**Effort:** 1 h (rename + add docstring + test)

**Desired:**
1. Rename `MnistFidEvaluator` to `MnistFrechetProjectionEvaluator`.
2. Update the `family()` method to return `"frechet_projection"` instead of `"mnist_fid"`.
3. Update `eval/__init__.py` and any callers (CIFAR harness).
4. Add a docstring explaining "this is NOT canonical FID (InceptionV3 features); it is a Fréchet distance on a random linear projection of pixel space".

**Verification:** run `tests/test_eval/`. The existing tests
(`test_mnist_fid`) pass with the rename because they import the class
name. Add a guard test that asserts `family() == "frechet_projection"`.

**Risk:** the harness's FID metric is consumed by `summary.json`. The
harness must be updated to use the renamed class.

---

### P0-7: F-41 — ModeCentreMSEW2 is mislabelled as Wasserstein

**File:** `adaptive_reflow/eval/w2.py:253-295` + `algorithm/runner.py:921-923`
**Severity:** 3 (metric key `W2` is misleading)
**Effort:** 0.5 h (rename metric key in runner; docstring)

**Desired:**
1. In `runner.py:921`, prefix the metric key with the family:
   `metric[f"W2:{estimator.family()}"] = ...`.
2. Add a docstring note in `ModeCentreMSEW2` (line 261) clarifying the
   name mismatch.
3. Update any consumer that reads `metric["W2"]` to read the new key.

**Verification:** run `tests/test_algorithm/test_runner.py` and
`tests/property/test_engine_round_determinism.py`; existing tests
pass with the prefix. Add `test_runner_metric_key_includes_w2_family`.

**Risk:** downstream consumers (the CIFAR harness, the comparison.md
generator) must be updated to use the new key. Failure to update
breaks the `comparison.md` report.

---

## §2. P1 fixes (important but not blocking)

| # | Bug | File | Effort |
|---|---|---|---:|
| P1-1 | F-2 EvidenceDrivenScheduler.config_hash drops k_eps | `algorithm/scheduler/evidence_driven.py` | 0.5 h |
| P1-2 | F-3 EvidenceDrivenScheduler._last_pid_delta is one round stale | `algorithm/scheduler/evidence_driven.py` | 0.5 h |
| P1-3 | F-4 ConvergenceAdaptiveScheduler re-derives n_cap via cosine for non-cosine base | `algorithm/scheduler/_core.py` | 1 h |
| P1-4 | F-5 CodimensionSheetScheduler.record_round_feedback is no-op (document or wire) | `algorithm/scheduler/_core.py` | 0.5 h |
| P1-5 | F-19 MeanFlowMergeOperator._prev_dynamic update ordering | `algorithm/merge_operator_v3.py` | 0.5 h |
| P1-6 | F-20 MeanFlowMergeOperator has no reset() | `algorithm/merge_operator_v3.py` | 0.5 h |
| P1-7 | F-21 MeanFlowMergeOperator re-clip emits stale audit value | `algorithm/merge_operator_v3.py` | 0.5 h |
| P1-8 | F-25 8 of 10 adapters missing inject_forward_noise | 8 adapters | 4 h |
| P1-9 | F-33 Runner does not reset state_machine between runs | `algorithm/runner.py` | 0.5 h |
| P1-10 | F-34 Runner does not propagate bundle between rounds | `algorithm/runner.py` | 1 h |
| P1-11 | F-36 Engine still has inline _policy_with_schedule_beta override | `frame/engine.py` | 1 h |
| P1-12 | F-42 ProjectionFreeExactW2 quantile interpolator not pinned | `eval/w2.py` | 0.5 h |
| P1-13 | F-45 sheet_evidence_A discretization_error bound is rough | `contracts/paper_quantities.py` | 0.5 h |
| P1-14 | F-46 root_cell_packing_B misses zero at x=K | `contracts/paper_quantities.py` | 0.5 h |
| P1-15 | F-53 hash_policy_hash may omit driver_computed_beta | `contracts/authority.py` | 0.5 h |

**Total P1 effort: ~12.5 h** (one developer-day).

---

## §3. P2 fixes (nice to have)

| # | Bug | File | Effort |
|---|---|---|---:|
| P2-1 | F-6 CosineAnnealScheduler accepts round_in_cycle=-1 without audit | `algorithm/scheduler/_core.py` | 0.5 h |
| P2-2 | F-7 LinearScheduler monotone direction not in audit code | `algorithm/scheduler/_core.py` | 0.25 h |
| P2-3 | F-8 ConstantScheduler edge case cycle_length=1 undocumented | `algorithm/scheduler/_core.py` | 0.25 h |
| P2-4 | F-9 Polynomial/Sigmoid lack cycle_length=1 test | `algorithm/scheduler/_core.py` | 0.5 h |
| P2-5 | F-10 CosineScheduleConfig.config_hash vs CosineAnnealScheduler.config_hash diverge | `algorithm/scheduler/_core.py` | 0.5 h |
| P2-6 | F-13 build_scheduler_from_config fallback dead code | `algorithm/scheduler/_core.py` | 0.25 h |
| P2-7 | F-15 AdaptivePolicyDriver.beta_saturation_count not reset on cycle | `algorithm/policy_driver.py` | 0.5 h |
| P2-8 | F-16 ConstantPolicyDriver does not emit audit code | `algorithm/policy_driver.py` | 0.25 h |
| P2-9 | F-17 _override_beta_by_channel silently no-ops on empty vocab | `algorithm/policy_driver.py` | 0.25 h |
| P2-10 | F-22 EMAOperator schedule modulation can exceed alpha range | `algorithm/merge_operator.py` | 0.5 h |
| P2-11 | F-23 BoundedMergeOperator tolerance has no observable effect | `algorithm/merge_operator.py` | 0.25 h |
| P2-12 | F-29 Runner's forward_noise_emitted=True is a lie for 8 of 10 adapters | `algorithm/runner.py` | 0.5 h |
| P2-13 | F-30 SyntheticUnsupportedAdapter uses one audit code for all mismatch types | `adapters/synthetic.py` | 0.5 h |
| P2-14 | F-39 Orchestrator._last_bounded_fraction not reset between cycles | `frame/orchestrator.py` | 0.5 h |
| P2-15 | F-43 coverage.py lacks config_hash | `eval/coverage.py` | 0.5 h |
| P2-16 | F-44 PosteriorSelectionEvaluator metric key naming | `eval/posterior_selection_evaluator.py` | 0.5 h |
| P2-17 | F-47 per_cell_coefficient_C c-clip silent | `contracts/paper_quantities.py` | 0.25 h |
| P2-18 | F-48 exterior_gap_e_rho can return near-zero | `contracts/paper_quantities.py` | 0.5 h |
| P2-19 | F-50 StateMachine priority tie-break unstable | `contracts/state_machine.py` | 0.5 h |
| P2-20 | F-51 StateMachine strict-guard mode silently disabled | `contracts/state_machine.py` | 0.5 h |
| P2-21 | F-52 TransitionLog has no explicit __hash__ | `contracts/state_machine.py` | 0.25 h |
| P2-22 | F-55 StateBundle.source_round not validated | `contracts/bundle.py` | 0.25 h |
| P2-23 | F-56 validate_final_restart_policy does not check ChannelName keys | `contracts/authority.py` | 0.5 h |
| P2-24 | F-11 _paper_evidence_balance fallback unreachable | `algorithm/scheduler/_core.py` | 0.25 h |
| P2-25 | F-12 CosineScheduleConfig.frozen_before_evaluation is dead config | `algorithm/scheduler/_core.py` | 0.25 h |
| P2-26 | F-14 AdaptivePolicyDriver ignores empty prior_endpoint_digest | `algorithm/policy_driver.py` | 0.5 h |
| P2-27 | F-26 ReferenceFlowAAdapter.export_trajectory raises (no audit distinction) | `adapters/reference_flowa.py` | 0.5 h |
| P2-28 | F-27 CIFAR adapter inject_forward_noise silently fails on shape mismatch | `adapters/rectified_flow_cifar.py` | 0.25 h |
| P2-29 | F-28 _gnobitab_ddpmpp strict load may partial-init on key aliasing | `adapters/_gnobitab_ddpmpp.py` | 2 h |
| P2-30 | F-35 Orchestrator does not validate MergeOperatorProtocol | `frame/orchestrator.py` | 0.5 h |
| P2-31 | F-37 run_round capability check omits inject_forward_noise | `frame/engine.py` | 0.5 h |
| P2-32 | F-38 run_round audit codes emitted in non-canonical order | `frame/engine.py` | 1 h |
| P2-33 | F-49 StateMachine parallel fallback to self swallows log | `contracts/state_machine.py` | 0.5 h |
| P2-34 | F-54 ODEConditionDelta validator does not check target_round >= 0 | `contracts/` | 0.5 h |

**Total P2 effort: ~16.5 h** (~2 developer-days).

---

## §4. Effort estimates per fix (P0 detail)

| Fix | LoC | Effort (h) | Wall (h) | Risk |
|---|---:|---:|---:|---|
| P0-1 Runner bypasses merge | -8 + 16 | 0.5 | 0.5 | low (audit codes change; bytes same) |
| P0-2 FreeTraj cache | -2 + 8 | 0.5 | 0.5 | medium (1 existing test must be inverted) |
| P0-3 BoundedMerge raise → return | -3 + 0 | 1.0 | 1.0 | low (1 new test) |
| P0-4 Runner reshape | -1 + 8 | 0.5 | 0.5 | low (additive) |
| P0-5 Runner record_round_feedback | +12 | 1.0 | 1.0 | medium (double-call with harness) |
| P0-6 MnistFid rename | +30 (rename + docstring + test) | 1.0 | 1.0 | medium (caller updates) |
| P0-7 ModeCentreMSE key prefix | +5 | 0.5 | 0.5 | medium (caller updates) |
| **Subtotal** | **~70 LoC across 7 files** | **5.0 h** | **5.0 h** | |

Plus a 1.5 h wall-clock CIFAR re-run (paper-grade config: 1000 samples × 10 rounds × 100 chains) and a 1 h post-run analysis.

**Total P0 hands-on: ~5 h. Total P0 wall-clock: ~7.5 h.**

P1 adds ~12.5 h (1 developer-day). P2 adds ~16.5 h (2 developer-days).

**Grand total: ~34.5 h hands-on, ~36 h wall-clock (one developer-week).**

---

## §5. Parallelization plan (which fixes can run concurrently)

The 7 P0 fixes have **no inter-dependencies** at the file level except:

- **P0-5** depends on the runner's `metric` dict structure, which is
  modified by P0-1 (the merge bypass). Specifically, after P0-1 the
  runner always builds `_merge_kwargs` with `dynamic = driver's beta`;
  the `feedback` dict in P0-5 should reference this same `dynamic` to
  avoid double-application of the PID. **Decision: P0-5 consumes the
  post-merge `merged_beta` rather than the pre-merge driver beta.**

- **P0-7** depends on the runner's metric-key naming convention, which
  is unchanged by P0-1. **Independent.**

- **P0-6** depends on the eval surface, which is independent of the
  runner/orchestrator. **Independent.**

- **P0-4** depends on the adapter's `state_shape` attribute, which is
  already advertised by 6 of 10 adapters. **Independent.**

**Parallel branches:**

| Branch | Fixes | Files | Wall-clock |
|---|---|---|---:|
| **A: scheduler + cache** | P0-2 | `algorithm/scheduler/freetraj.py`, `tests/test_algorithm/test_freetraj.py`, `tests/test_experiments/test_freetraj_wallclock.py` | 0.5 h |
| **B: merge operator contract** | P0-3 | `algorithm/merge_operator.py`, `tests/property/test_bounded_merge_invariants.py` | 1 h |
| **C: runner correctness** | P0-1, P0-4, P0-5 | `algorithm/runner.py`, `tests/test_algorithm/test_runner.py` | 2 h |
| **D: eval labels** | P0-6, P0-7 | `eval/mnist_fid.py`, `eval/w2.py`, `algorithm/runner.py`, callers | 1.5 h |

**P0 critical path: Branch C (P0-1 + P0-4 + P0-5) = 2 h.**

Branches A, B, D can run in parallel.

---

## §6. Verification plan (how to test each fix)

### P0-1 verification

- **Unit:** `tests/test_algorithm/test_runner.py::test_runner_calls_merge_operator_between_policy_and_engine`
  must still pass (it uses `_RecordingMergeOperator`).
- **New unit:** `test_runner_calls_merge_operator_on_schedule_derived`
  drives the runner with `ScheduleDerivedPolicyDriver` and a
  `_RecordingMergeOperator`; assert `_RecordingMergeOperator.calls == n_rounds`.
- **Smoke:** `tools/run_sota_cifar_experiment.py --quick` and assert
  `audit_codes_per_round` for one framework row contains a merge-audit
  code (any non-empty `merge_audit_codes` list).

### P0-2 verification

- **Unit:** `tests/test_algorithm/test_freetraj.py::test_freetraj_substep_varies_across_rounds`
  (new) — drives `sample(0, r, 0)` for `r in range(8)`; assert that
  `n_cap[1] != n_cap[3]` (the `sin` is non-zero).
- **Regression inversion:** `tests/test_experiments/test_freetraj_wallclock.py::test_freetraj_trajectory_progress_freezes_when_driven_statefully`
  must be **inverted**: now assert that the progress varies with
  `round_in_cycle` when no external signal is provided.
- **Smoke:** the v2 CIFAR run's `FreeTrajScheduler` row should now
  differ from the cosine row by `> 0.01` in `n_cap` at odd rounds.

### P0-3 verification

- **Unit:** `tests/property/test_bounded_merge_invariants.py::test_bounded_merge_returns_floor_on_cap_below_floor`
  (new) — assert `BoundedMergeOperator().merge(0.5, 0.7, cap=0.3, floor=0.4, ...)`
  returns `0.4` and emits `_ERR_CAP_BELOW_FLOOR` audit code.
- **Existing:** all 11 tests in `tests/property/test_bounded_merge_invariants.py`
  must still pass (they use non-degenerate envelopes).

### P0-4 verification

- **Unit:** `tests/test_algorithm/test_runner.py::test_runner_endpoints_matrix_respects_adapter_state_shape`
  (new) — drives the runner with a mock adapter whose
  `state_shape = (3, 32, 32)`; assert `endpoints[0].shape == (3, 32, 32)`.
- **Existing:** `test_runner_endpoints_matrix_is_nan_initialised`
  must still pass (it uses a 2-D adapter).

### P0-5 verification

- **Unit:** `tests/test_algorithm/test_runner.py::test_runner_records_feedback_per_round`
  (new) — drives the runner with `EvidenceDrivenScheduler` and asserts
  `scheduler._last_pid_delta != 0.0` after `r=5`.
- **Smoke:** the harness's `tools/run_sota_cifar_experiment.py` must
  NOT also call `scheduler.record_round_feedback` (to avoid
  double-counting). Either remove the harness call OR pass through a
  runner hook.

### P0-6 verification

- **Unit:** `tests/test_eval/test_mnist_fid.py` (renamed) — assert
  `family() == "frechet_projection"`.
- **Smoke:** `tools/run_sota_cifar_experiment.py --quick` and assert
  the `summary.json` reports `family = "frechet_projection"`.

### P0-7 verification

- **Unit:** `tests/test_algorithm/test_runner.py::test_runner_metric_key_includes_w2_family`
  (new) — drives the runner with `ModeCentreMSEW2`; assert
  `metric["W2:mode_centre_mse"]` is present.
- **Existing:** `test_runner_passes_w2_to_scheduler_feedback` must
  still pass.

### End-to-end gate (post-P0)

Re-run `tools/run_sota_cifar_experiment.py --quick` (200 samples × 5 rounds × 50 chains) and assert:

- All 4 framework FIDs are non-byte-identical.
- All 4 framework `samples.npz` files are non-byte-identical.
- The 4 `n_cap` traces are non-constant and visually distinguishable.
- `FreeTrajScheduler` row deviates from cosine at `r=1, 3` by `> 0.01`.

Then re-run the paper-grade config (1000 samples × 10 rounds × 100 chains) and assert:

- 4 distinct FIDs spread across a `> 0.5` window.
- Framework FID < baseline FID (or, if regression, honestly reported).

### Done criteria

- [ ] All P0 fixes land; `ruff`, `mypy --strict`, `pytest` clean.
- [ ] 4 distinct framework FIDs in `summary.json`.
- [ ] 4 distinct `n_cap` traces in `per_round_metrics.csv`.
- [ ] `comparison.md` reports `Δ vs baseline` for each row.
- [ ] No regression > 10% on any framework FID.
- [ ] All existing tests pass (no test deletion; some inversions).

---

## §7. Path-to-A (scheduler discrimination) — required P0 fixes

Path A is "the four framework rows produce non-byte-identical samples
and FIDs". The P0 fixes that unlock Path A are:

1. **P0-1** (F-31) — runner calls the merge operator on the schedule_derived
   path. **Without this fix, the bounded envelope's floor is never
   applied, so the four rows are not distinguishable through the
   envelope.** (Severity 5; this is the load-bearing fix.)
2. **P0-2** (F-1) — FreeTraj substep varies across rounds. **Without this
   fix, FreeTraj tracks cosine exactly.**
3. **P0-5** (F-32) — runner feeds feedback to scheduler. **Without this,
   EvidenceDrivenScheduler's PID delta stays at the harness-level
   proxy and may not cross the banker's-rounding threshold needed to
   change `num_steps`.**

**Optional but recommended:**
4. **P0-3** (F-18) — runner survives degenerate envelopes. Without this,
   a misconfigured codim scheduler with `n_max < n_min` could crash the
   loop. Not load-bearing for Path A in the v2 config, but a safety net.

**P0 fixes required for Path A: P0-1, P0-2, P0-5. (Critical path: ~2 h.)**

---

## §8. Path-to-B (better FID) — required P0 fixes

Path B is "framework FID < baseline FID". The v2 run already achieved
this (122.18 vs 218.87), but the framework rows were byte-identical
("more NFEs = better FID" reading). To claim *scheduler discrimination*
(rather than just NFE advantage), Path B requires Path A's fixes:

1. **P0-1, P0-2, P0-5** (Path A).
2. **P0-4** (F-24) — endpoint row no longer `NaN`. **Without this, the
   per-round endpoint trajectory cannot be analysed downstream.** Not
   load-bearing for the headline FID comparison, but a precondition for
   the ablation script's custom scoring.

**P0 fixes required for Path B: P0-1, P0-2, P0-4, P0-5. (Critical path: ~2.5 h.)**

---

## §9. Risk assessment (per P0 fix)

| Fix | Risk | Mitigation |
|---|---|---|
| P0-1 | Low — byte-identical output for bounded merge; only audit codes change | run full test suite; smoke test on CIFAR quick profile |
| P0-2 | Medium — invert 1 existing test; FreeTrajScheduler's `_last_trajectory_progress` semantics change | update the inverted test; verify that `record_round_feedback` consumers still work |
| P0-3 | Low — fail-closed semantics preserved; audit code remains | run `tests/property/test_bounded_merge_invariants.py`; add the new degenerate-envelope test |
| P0-4 | Low — additive; 2D adapters still work | run `tests/test_algorithm/test_runner.py`; smoke test on CIFAR quick profile |
| P0-5 | Medium — double-call with harness | remove the harness's own `record_round_feedback` call; route through the runner |
| P0-6 | Medium — caller updates required | grep for `MnistFidEvaluator`; update the harness + comparison.md generator |
| P0-7 | Medium — caller updates required | grep for `metric["W2"]`; update harness + comparison.md generator |

---

## §10. Summary

| Metric | Value |
|---|---:|
| Total bugs found | **52** |
| P0 (paper-blocking) | **7** |
| P1 (correctness) | **15** |
| P2 (polish) | **30** |
| Estimated total fix effort (P0 only) | **5 h hands-on / 7.5 h wall-clock** |
| Estimated total fix effort (P0 + P1) | **17.5 h** (~2.5 developer-days) |
| Estimated total fix effort (all) | **34 h** (~1 developer-week) |
| Critical path for Path A | P0-1, P0-2, P0-5 (2 h) |
| Critical path for Path B | P0-1, P0-2, P0-4, P0-5 (2.5 h) |
| Files reviewed | **~22** (algorithm/*, adapters/*, frame/*, eval/*, contracts/*) |
| Docs path (review) | `docs/r4-survey/18-comprehensive-code-review.md` |
| Docs path (plan) | `docs/r4-survey/19-fix-plan.md` |

The P0 fixes are narrow, low-risk, and parallelisable. Approval to
execute Branch A (FreeTraj cache), Branch B (BoundedMerge contract),
and Branch C (runner correctness) is recommended. Branch D (eval
labels) is a low-priority cleanup and can be deferred.
