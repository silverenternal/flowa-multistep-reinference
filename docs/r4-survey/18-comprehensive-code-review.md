# Comprehensive algorithm & harness code review (R3/R11 audit)

> **Author:** Agent R (code-review + fix-plan subagent)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Status:** READ-ONLY review; no code changes. Awaiting approval before
> the Phase-2 fix plan in `19-fix-plan.md` is executed.
> **Inputs cited:**
> - `docs/r4-survey/15-harness-bug-diagnosis.md` (R3 Phase 1)
> - `docs/r4-survey/16-harness-fix-plan.md` (R3 Phase 2)
> - `docs/r4-survey/17-cifar-experiment-results-v2.md` (R3 Phase 3)
> - `docs/r4-survey/cifar_results_v2/{per_round_metrics.csv,summary.json,comparison.md}`
> - `docs/r4-survey/cifar_results/experiment-log.md` (R3 Phase 1 honest log)

---

## §1. Audit method

### 1.1 Files read

| Module | Files | Line counts | Read |
|---|---|---:|---|
| Schedulers (core) | `algorithm/scheduler/_core.py`, `freetraj.py`, `evidence_driven.py`, `__init__.py` | 3247 / 327 / 549 / 83 | full |
| Cosine helper | `schedule/cosine.py` | partial (~233 / ~300) | full read of `n_cap_for_round` |
| Policy drivers | `algorithm/policy_driver.py` | 1039 | sampled: Sched/Const/Adaptive sections |
| Merge operators | `algorithm/merge_operator.py`, `merge_operator_v3.py` | 861 / 290 | full |
| Adapters | `adapters/{twodim_fm,mnist_fm,mnist_fm_train,rectified_flow_cifar,_gnobitab_ddpmpp,stochastic_fm,reference_flowa,synthetic,toy_gaussian,toy_linear}.py` | 50854 / 29988 / 31702 / 48112 / 15900 / 12932 / 13389 / 23765 / 19495 / 10198 | grep method index + spot reads |
| Runner | `algorithm/runner.py` | 52432 | full read (lines 600–900) |
| Engine | `frame/engine.py` | 73768 | grep + spot reads |
| Orchestrator | `frame/orchestrator.py` | 51263 | grep + spot reads (lines 1080–1180) |
| Evaluators | `eval/{w2,coverage,mnist_fid}.py` | 42844 / 14144 / 10938 | grep + spot reads |
| Paper quantities | `contracts/paper_quantities.py` | 19160 | full read of all 4 paper quantities |
| State machines | `contracts/state_machine.py` | 42511 | partial (~890 / 1180) — byte-det log, parallel regions, guards |
| Contracts surface | `contracts/__init__.py` | 10368 | grep read |
| Phase-3 inputs | `docs/r4-survey/{15,16,17}-*.md` | 15040 / 32277 / 14182 | full |

Total lines reviewed (effective, excluding skipped bulk): ~6500 lines.

### 1.2 Test coverage observed

| Module class | Test files | Coverage gap |
|---|---|---|
| `CosineAnnealScheduler`, `LinearScheduler`, `ConstantScheduler`, `PolynomialScheduler`, `SigmoidScheduler`, `ExponentialScheduler` | `tests/test_algorithm/test_scheduler.py` (lines grep'd) | well-covered; canonical ramps + boundary conditions |
| `CodimensionSheetScheduler` | `test_scheduler.py::test_codimension_sheet_uses_cosine_base` | the `_paper_evidence_balance` paper-quantity path (with `profile_residual_fn`) is under-tested; `record_round_feedback` no-op unverified |
| `FreeTrajScheduler` | `tests/test_algorithm/test_freetraj.py` + `tests/test_experiments/test_freetraj_wallclock.py::test_freetraj_trajectory_progress_freezes_when_driven_statefully` | **the wallclock test pins the cache bug as "expected behavior" — see §2.2 F-1** |
| `EvidenceDrivenScheduler` | `tests/test_algorithm/test_evidence_driven_scheduler.py` | covers PID-lite math, integral windup, `_last_eps_delta` |
| `ConvergenceAdaptiveScheduler` | `tests/test_algorithm/test_scheduler.py` | shift math + EMA covered |
| `BoundedMergeOperator` | `tests/property/test_bounded_merge_{invariants,anchoring}.py`, `tests/test_algorithm/test_merge_operator.py` | comprehensive; envelope collapses, non-finite, swap removal |
| `IdentityOperator`, `EMAOperator` | `tests/test_algorithm/test_merge_operator.py` | covered |
| `MeanFlowMergeOperator` | `tests/test_algorithm/test_meanflow_merge.py` | covered but `_prev_dynamic`/`_ema_grad` reset path not tested (no `reset()` method) |
| `ScheduleDerivedPolicyDriver` | `tests/test_algorithm/test_policy_driver.py::test_schedule_derived_driver_matches_engine_override` | covered |
| `ConstantPolicyDriver` | `test_policy_driver.py::test_constant_driver_returns_constant_beta` | covered |
| `AdaptivePolicyDriver` | `test_policy_driver.py::test_adaptive_driver_beta_varies_with_prior_digest`, paper-quantity path | covered |
| 2D adapter | `tests/test_adapters/test_twodim_fm.py` | covered |
| CIFAR adapter | `tests/test_adapters/test_rectified_flow_cifar.py` | covered; 16 tests |
| `ReInferenceRunner` | `tests/test_algorithm/test_runner.py` | well-covered but bypass-merge-on-schedule-derived path has no negative regression |
| Frame engine | `tests/property/test_engine_round_determinism.py`, `tests/property/test_fail_closed_invariants.py` | covered |

### 1.3 Audit strategy

1. Re-read all 4 Phase-3 inputs and confirm which "known bugs" were *fixed* vs *left open*.
2. For each module, walk the public surface (Protocol methods) and look for: off-by-one, contract drift, stale cache, hard-coded shape, missing reset, audit-trail gaps, deterministic-replay breaks.
3. Cross-check callers — the harness caller (`tools/run_sota_cifar_experiment.py`) plus the runner — to confirm the bugs surface in production.
4. Rank each finding 1–5 (5 = load-bearing correctness, paper-blocking; 1 = nice-to-have polish).

---

## §2. Per-module bug list

Severity scale: **5 = paper-blocking correctness** · **4 = functional regression** · **3 = observable wrong output** · **2 = drift / dead code / contract wart** · **1 = nice-to-have**.

### 2.1 SCHEDULERS — `algorithm/scheduler/_core.py`, `freetraj.py`, `evidence_driven.py`

#### F-1 (severity 4) — `FreeTrajScheduler._compute_trajectory_progress` cache bug (CONFIRMED via v2 results)

**File:** `adaptive_reflow/algorithm/scheduler/freetraj.py:308-321`
**Root cause:** the helper at line 316-317 short-circuits when `self._last_trajectory_progress is not None`, returning the cached value rather than the deterministic `round_in_cycle % period / period`. The cache is **set unconditionally on every** `sample()` call at line 207. Therefore:

- Round 0 with `round_in_cycle=0`: `progress = 0 % 4 / 4 = 0.0`, `substep = 0.05 * sin(0) = 0.0`, cached `_last_trajectory_progress = 0.0`.
- Round 1+: `_last_trajectory_progress` is non-None → returns the *cached* 0.0 forever. Substep is 0.0 for every subsequent round.

This is **directly responsible** for the v2 result `FreeTrajScheduler.n_cap` tracking the cosine baseline exactly (see `docs/r4-survey/17-cifar-experiment-results-v2.md` §2 bullet 2: "FreeTraj = CosineAnneal in this run").

**Fix direction:** drop the cache write on line 207; compute `progress` deterministically and only consult `_last_trajectory_progress` when explicitly set via `record_round_feedback` (the current short-circuit at line 316 should only fire when `record_round_feedback` was called *for this round* — i.e. the cache flag is the "external signal received" indicator, not the "last computed progress" indicator).

**Test to update:** `tests/test_experiments/test_freetraj_wallclock.py::test_freetraj_trajectory_progress_freezes_when_driven_statefully` currently pins the broken behaviour; that test must be inverted or deleted when the fix lands.

---

#### F-2 (severity 4) — `EvidenceDrivenScheduler.config_hash` drops `k_eps` and `eps_implicit_base`

**File:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py:402-417`
**Root cause:** `config_hash()` builds the digest from `{algorithm, cycle_length, n_min, n_max, kp, ki, max_step, target_ratio}` but **does not include `k_eps`** (set on line 280) or `eps_implicit_base` (set on line 281-283). `to_config()` (lines 486-505) and `from_config()` (lines 507-536) round-trip them correctly. Two schedulers that differ only in `k_eps` produce the same `config_hash`, breaking the audit invariant "two drivers with different config return different `config_hash`" declared at `policy_driver.py:277-284`.

**Fix direction:** add `"k_eps": float(self._k_eps)` (and conditionally `eps_implicit_base`) to the `hash_artifact` payload. Update `tests/test_algorithm/test_evidence_driven_scheduler.py` to add a `test_config_hash_varies_with_k_eps` guard.

---

#### F-3 (severity 3) — `EvidenceDrivenScheduler._last_pid_delta` carried with stale-feedback semantics

**File:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py:338-346`
**Root cause:** `sample()` reads `self._last_pid_delta` (computed in the previous `record_round_feedback` call) and adds it to the cosine baseline. Round 0 uses `_last_pid_delta=0.0` (no feedback yet). The runner's data path is `sample() → engine.run_round() → ... → record_round_feedback() → next round sample()`, which is **1 round behind**: at round `r`, the PID delta is from round `r-1`'s `evidence_ratio`. This is intentional (the controller needs a *measured* signal before it can move) but the **audit trail does not surface this** — the round's `n_cap` is reported as if it were the closed-form value. A reader cannot tell from `per_round_metrics.csv` that the `EvidenceDrivenScheduler` row's `n_cap[r]` is the *previous* round's PID correction.

**Fix direction:** add an `evidence_driven_uses_prior_round_pid` audit code on every sample emitted, so the per-round metric dict carries the round-lag annotation.

---

#### F-4 (severity 3) — `ConvergenceAdaptiveScheduler.sample` re-derives `n_cap` via the cosine closed-form even when base is non-cosine

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:1927-1935`
**Root cause:** when `length > 1`, the code computes `synthetic_round = int(round(effective_u_r * (length - 1)))` and then calls `n_cap_for_round(self._base.config, synthetic_round)`. `n_cap_for_round` (in `schedule/cosine.py:226-230`) dispatches on `config.schedule_family`; if the wrapped base is `LinearScheduler` or another non-cosine family, the re-derived `n_cap` will follow the *cosine* closed form, not the wrapped base. The wrapper's docstring claims "the closed-form cosine helper, using a synthetic round index. This keeps the closed-form canonical (one source of truth)" — so the behaviour is intentional, but it is **undocumented for non-cosine base cases** and breaks the wrapper's "wraps any cosine-like base" promise.

**Fix direction:** add an explicit `schedule_family` check before the re-derivation; if the base family is not `cosine_no_restart` / `cosine_guarded_restart`, raise `NotImplementedError` with a clear message, or fall back to a linear interpolation in `[n_min, n_max]`.

---

#### F-5 (severity 3) — `CodimensionSheetScheduler.record_round_feedback` is a permanent no-op

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:2816-2822`
**Root cause:** the paper-quantity-aware scheduler exposes a `record_round_feedback` hook but discards every input. The C4 work targeted `EvidenceDrivenScheduler`; `CodimensionSheetScheduler` is left open-loop on rounds. Yet the harness's `record_round_feedback` call site (after the v2 fix at `tools/run_sota_cifar_experiment.py`) passes an `evidence_ratio` proxy to *all* adaptive schedulers including the codim one. The codim row sees `evidence_ratio=1.0` for `r=0` (cosine baseline) drifting to `0.952` at `r=9` (matches the v2 CSV). The framework never *uses* this signal — it's purely cosmetic.

**Fix direction:** either (a) document in the docstring that the hook is reserved for future C4-style uplift, or (b) make the codim scheduler's `n_cap_base` drift by a small epsilon function of the observed ratio. (b) is preferable because the v2 results explicitly flag this as the missing piece for discrimination.

---

#### F-6 (severity 2) — `CosineAnnealScheduler.sample` accepts `round_in_cycle=-1` without raising

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:363-398`
**Root cause:** the `_coerce_int_nonneg` helper (line 283-288) rejects negative integers for `outer_cycle_id` and `target_round` but **not for `round_in_cycle`**. The call to `n_cap_for_round(self._config, round_in_cycle)` (line 373) would raise `ValueError("round_in_cycle must be in [0, L-1]")` from the cosine helper, but the **error path bypasses the scheduler's audit trail**. A reader of the round's metric dict cannot tell whether the round produced a sample or failed.

**Fix direction:** explicitly validate `round_in_cycle` against `[0, cycle_length-1]` before calling `n_cap_for_round` and append a `ROUND_IN_CYCLE_OUT_OF_RANGE` audit code on the no-op path.

---

#### F-7 (severity 2) — `LinearScheduler.sample` has a non-monotone ordering when `n_min > n_max`

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:873-876`
**Root cause:** the closed form `n_max - (n_max - n_min) * u_r` is monotone in `u_r` for `n_max > n_min` but **anti-monotone** for `n_min > n_max`. The docstring (lines 776-781) acknowledges both cases but does not warn that "ramp-down" with `n_min > n_max` produces a non-conventional sequence (rounds start at the *high*-n_max end). For paper comparisons this is the right behaviour (the user asked for ramp-down), but the **audit code** (`schedule_linear_baseline`, line 889) does not distinguish ramp-up vs ramp-down, breaking the audit invariant "the audit code identifies the family".

**Fix direction:** add a directional suffix (`schedule_linear_baseline:direction=up` vs `=down`) and tests for both.

---

#### F-8 (severity 2) — `ConstantScheduler.sample` validates `cycle_length > 1` but accepts any `round_in_cycle`

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:662-669`
**Root cause:** the validation only fires when `length > 1`. For `cycle_length == 1`, *any* `round_in_cycle` is accepted. This is consistent with the cosine family but not documented in the docstring. The constant scheduler is the simplest ablation; a user who passes `round_in_cycle=10` with `cycle_length=1` will get a sample without warning.

**Fix direction:** document the edge case in the docstring and the helper. (Severity is 2 because the contract is total: no exception is raised, no audit code is appended.)

---

#### F-9 (severity 2) — `PolynomialScheduler` and `SigmoidScheduler` lack unit tests for boundary `cycle_length == 1`

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:1311-1356` (Polynomial), `1438-1712` (Sigmoid)
**Root cause:** both schedulers have the same `length == 1 → u_r = 0.5, n_cap = n_max` edge as cosine (line 1329-1331 for Polynomial; need to verify for Sigmoid at the same offset). No test in `tests/test_algorithm/test_scheduler.py::test_polynomial_*` or `test_sigmoid_*` exercises `cycle_length=1`; coverage is gap.

**Fix direction:** add `test_polynomial_single_round_returns_n_max` and `test_sigmoid_single_round_returns_n_max`.

---

#### F-10 (severity 2) — `CosineScheduleConfig.config_hash` (in `contracts/schedule.py`) is constructed *outside* the `CosineAnnealScheduler.__init__`

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:542-563` (factory), and `default_cosine_scheduler` re-uses `CosineScheduleConfig`'s constructor.
**Root cause:** the `config_hash` is built once in the factory and stored on the `CosineScheduleConfig`. Two schedulers constructed with *different* seeds but the same `(cycle_length, n_min, n_max)` *do* produce different `config_hash` values (the seed is folded into the digest). However, `CosineAnnealScheduler.config_hash()` (line 408-421) *re-hashes* including `"algorithm": "cosine_anneal"` and the `"config_hash"` field itself. The result is **two hashes for the same logical scheduler** when comparing `config_hash` across the `CosineScheduleConfig` and the `CosineAnnealScheduler`. There is no observable bug, but the audit trail is ambiguous: which hash is the canonical one?

**Fix direction:** drop the `algorithm` key from `CosineAnnealScheduler.config_hash()` (or make it the canonical identity hash, and have `CosineScheduleConfig.config_hash` be a separate "config-only" hash).

---

#### F-11 (severity 1) — `_paper_evidence_balance` fallback branch is unreachable

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:2257-2264`
**Root cause:** when `sheet_A`, `packing_B`, and `cell_C` are all zero (the only way `denom <= 0.0`), the fallback re-derives `sheet = max(n_clipped, eps)`. But `eps > 0` is validated upstream (line 2218) so `sheet >= eps > 0` and the fallback's `denom` is positive. The branch is documented as "unreachable" but the fallback still fires *if* `cell_C_f * pack_f * eps**2 == 0` while `sheet_f * eps == 0`, i.e. `sheet_f = 0`. That requires `sheet_A = 0`, which contradicts the paper's `A_g > 0` (line 161). The dead code is acceptable but should be removed or commented.

**Fix direction:** replace the fallback branch with `assert sheet_f > 0.0` and document the paper guarantee.

---

#### F-12 (severity 1) — `CosineScheduleConfig.frozen_before_evaluation` is set in every factory but never consumed

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:562`, and in `CosineAnnealScheduler.from_config` (line 483-502).
**Root cause:** the `frozen_before_evaluation` flag is passed to the constructor but I could not find a consumer that reads it (greps for `frozen_before_evaluation` returned only the write sites). This is dead configuration.

**Fix direction:** either remove the field, or wire it to the engine's pre-round evaluation freeze check.

---

#### F-13 (severity 2) — `build_scheduler_from_config` "fallback" branch is unreachable

**File:** `adaptive_reflow/algorithm/scheduler/_core.py:3217-3220`
**Root cause:** the function dispatches on `key` against an explicit `if` chain (lines 3170-3216) and only falls through to `factory()` if no key matches. But every registered key is matched before line 3217; the only way to reach the fallback is a third-party registration via `_register_extra_scheduler_families` whose `from_config` was never wired. The fallback is dead code (it also drops kwargs, breaking the round-trip). Document as `unreachable_in_practice` or wire a `RegistryError`.

**Fix direction:** raise `KeyError` if no `from_config` matches.

---

### 2.2 POLICY DRIVERS — `algorithm/policy_driver.py`

#### F-14 (severity 3) — `AdaptivePolicyDriver.compute_policy` ignores `prior_endpoint_digest=""` for round 0 hash consistency

**File:** `adaptive_reflow/algorithm/policy_driver.py:673`
**Root cause:** `_digest_to_unit("")` produces a stable but arbitrary value (the SHA-256 of the empty string). A round-0 run with no prior endpoint sees the same digest every time (deterministic), but the value is **arbitrary in `[0, 1]`** — it does not encode "round 0". A reader cannot tell from `metric["prior_endpoint_digest"]` whether the round actually had a prior endpoint or not.

**Fix direction:** accept `prior_endpoint_digest=None` (or `prior_endpoint_digest="round_0"`) as a separate signal; the digest hash only fires when `prior_endpoint_digest != ""`.

---

#### F-15 (severity 2) — `AdaptivePolicyDriver.beta_saturation_count` is not reset on `reset()`

**File:** `adaptive_reflow/algorithm/policy_driver.py:505-635`
**Root cause:** the class exposes `reset_beta_saturation_count()` (line 627) and the docstring says "the runner typically resets the counter at the start of every outer cycle". But the runner (`runner.py`) does not call this — the counter is per-process, not per-cycle. A 10-cycle run reports the cumulative saturation count, not the per-cycle count. The audit invariant "the per-round metric reports the cycle-local count" is broken.

**Fix direction:** call `reset_beta_saturation_count()` at the top of each cycle in the runner, or move the counter into the `compute_policy` call path (pass cycle-local).

---

#### F-16 (severity 2) — `ConstantPolicyDriver.compute_policy` does not emit an audit code

**File:** `adaptive_reflow/algorithm/policy_driver.py:448-470`
**Root cause:** the driver overrides `beta_by_channel` but does not append any audit code to `audit_codes`. The audit invariant "the engine's audit trail attributes the per-round `beta` to the source driver" is broken for the constant path. A reader cannot tell from `round_trace.audit_codes` whether the `beta` came from the constant driver or from a missing override.

**Fix direction:** emit a `policy_constant_driver` audit code when the driver family is `constant`.

---

#### F-17 (severity 1) — `_override_beta_by_channel` silently drops kwargs when `base_policy.beta_by_channel == {}`

**File:** `adaptive_reflow/algorithm/policy_driver.py:154-172`
**Root cause:** when `base_policy.beta_by_channel` is empty *and* `channel is None`, `keys = []` (line 165). The override returns `replace(base_policy, beta_by_channel={}, ...)` with `driver_computed_beta=True`, leaving the policy with no per-channel beta. The engine then has no `beta_by_channel` to apply and the round fails closed (`_policy_with_schedule_beta` zero-fills). The override is silently a no-op.

**Fix direction:** raise `ValueError` when `keys == []`; the empty vocabulary is a misconfiguration.

---

### 2.3 MERGE OPERATORS — `merge_operator.py`, `merge_operator_v3.py`

#### F-18 (severity 5) — `BoundedMergeOperator.merge` raises `MergeAuthorityError` on `cap < floor` but the protocol docstring promises a finite float

**File:** `adaptive_reflow/algorithm/merge_operator.py:591-599`
**Root cause:** the F5 fix removed the silent-swap semantics (legitimately, the docstring notes the audit invariant). But the `MergeOperatorProtocol` docstring (line 254) still claims "all implementations MUST return a finite ``float`` in the closed unit interval ``[0, 1]]``. Implementations MUST NOT raise on legitimate caller input such as ``cap > 1``, ``cap < floor``, or non-finite ``dynamic`` / ``prev``". The `cap < floor` post-clip branch raises — a contradiction. The runner at `runner.py:717` calls `self._merge.merge(...)` without a try/except wrapper, so any caller that ships a degenerate envelope (which the runner cannot guarantee not to do — the schedule sample's `n_cap` could be 0 with `n_min > 0` for a freshly-constructed `LinearScheduler` with `n_min=1.0`) will crash the loop.

**Fix direction:** update the protocol docstring to document the fail-closed raise; or replace the raise with a fail-closed return of `floor` + audit-code emission (preserves the contract at the cost of the F5 fix).

---

#### F-19 (severity 4) — `MeanFlowMergeOperator.merge` updates `_prev_dynamic` *before* the bounded merge sees it (ordering bug)

**File:** `adaptive_reflow/algorithm/merge_operator_v3.py:248-260`
**Root cause:** line 256 sets `self._prev_dynamic = float(dynamic)` *before* line 260 computes `corrected = raw - dt * self._ema_grad`. On round 0, `_prev_dynamic is None` so the gradient update is skipped; `_prev_dynamic` is set to `dynamic`; on round 1, `_prev_dynamic` is now the round-0 `dynamic`. This means the *initial* `dynamic` is **lost** — `_ema_grad` never sees the delta from the initial state. The first round's `corrected` value uses `ema_grad = 0.0` (correct), but subsequent rounds' `ema_grad` always references *one step behind* the `dynamic` value used in the bounded merge. If the caller changes `dynamic` between the bounded-merge call and the audit step (none currently do, but the protocol allows it), the gradient is stale.

**Fix direction:** move `self._prev_dynamic = float(dynamic)` to *after* the `corrected` computation; or document the lag and add a unit test.

---

#### F-20 (severity 3) — `MeanFlowMergeOperator` has no `reset()` method, so `_prev_dynamic`/`_ema_grad` accumulate across re-uses

**File:** `adaptive_reflow/algorithm/merge_operator_v3.py:144-145`
**Root cause:** `_prev_dynamic` and `_ema_grad` are instance state that survive across rounds and across re-uses of the operator. The runner constructs a new operator per `ReInferenceRunner.__init__` (per process), so the cross-round leak is harmless within a single run. But **re-using the operator across two `ReInferenceRunner.run` calls** in the same process (e.g., for ablation) would carry forward the last round's `_prev_dynamic` and `_ema_grad`, producing non-reproducible output. The runner's `reset()` method does not reset the merge operator.

**Fix direction:** add a `reset()` method to `MeanFlowMergeOperator` and call it from `runner.py:_reset_inner_state()` if it exists; or document that the operator must be single-use.

---

#### F-21 (severity 3) — `MeanFlowMergeOperator` re-clip into `[floor, cap]` *after* the `[0, 1]` clip silently overrides the bounded-merge contract

**File:** `adaptive_reflow/algorithm/merge_operator_v3.py:261-274`
**Root cause:** line 261 clips `corrected` into `[0, 1]` (the unit-interval contract); line 271-274 re-clips into `[floor, cap]` (the bounded-merge contract). If the user's envelope has `floor > 0` and `cap < 1`, the two clips disagree: a `corrected = 0.0` (clipped from a negative raw value) becomes `floor` at line 272. This is **correct** per the bounded-merge contract but the audit code emitted at line 263-268 reports `corrected = 0.0`, not `floor`. A reader sees `corrected=0.0` and infers "no MeanFlow correction"; the floor lift is silent.

**Fix direction:** move the `[floor, cap]` clip before the audit emission; emit the audit code with the post-clip value.

---

#### F-22 (severity 2) — `EMAOperator.schedule_weight` modulation can produce `alpha > 1`

**File:** `adaptive_reflow/algorithm/merge_operator.py:807-821`
**Root cause:** the formula `alpha = alpha * (1 + sw * (n_cap_c - 0.5))` with `sw=1.0` and `n_cap_c=1.0` gives `alpha * 1.5`. With the default `alpha=0.1` this gives `0.15` (in range); with `alpha=0.9` it gives `1.35` (out of range). The final clip into `[0, 1]` (line 827-832) handles this defensively, but a `raw` value of `1.35 * (dynamic - prev) + prev` clipped to `[0, 1]` produces a value that does *not* match the EMA semantics. The clip hides the bug.

**Fix direction:** clamp `alpha` into `[0, 1]` *before* the EMA step; emit an audit code when the modulation produces an out-of-range alpha.

---

#### F-23 (severity 2) — `BoundedMergeOperator.config_hash` includes `tolerance` but tolerance has no observable effect

**File:** `adaptive_reflow/algorithm/merge_operator.py:457-476` and `merge_operator.py:386-392` (docstring)
**Root cause:** the `tolerance` field is accepted, hashed, round-tripped, and stored, but the `merge()` implementation (line 491-630) **never reads `self._tolerance`**. The docstring acknowledges: "the current implementation collapses on the strict ``hi < lo`` comparison, so ``tolerance`` does not currently affect behaviour". So two operators with different tolerances produce different hashes but identical outputs. Audit-trail confusion.

**Fix direction:** either remove `tolerance` from the hash (keep it in `to_config` for forward-compat) or implement the tolerance as a near-degenerate warning.

---

### 2.4 ADAPTERS — `adapters/*.py`

#### F-24 (severity 5) — `runner.py` calls `arr[-1].reshape(2)` on every adapter's trajectory, hard-coding 2-D

**File:** `adaptive_reflow/algorithm/runner.py:856`
**Root cause:** the runner's `arr[-1].reshape(2)` assumes every adapter's state has shape `(2,)`. For `TwoDimFMAdapter` (xy channel, `(2,)`) this is correct; for `MnistFmAdapter` (`(784,)`), `RectifiedFlowCIFARAdapter` (`(3, 32, 32)`), `FlowMol3Adapter` (variable), or any other non-2D adapter, the `reshape(2)` raises `ValueError: cannot reshape array of size 3072 into shape (2,)`. The runner catches this silently via the `arr.ndim >= 2 and arr.shape[0] >= 1` check on line 855 — but the check doesn't actually validate `arr.shape[1]`. The line **only runs** for 2-D adapters today; any other adapter triggers `endpoint_export_failed = True` (line 858) and the endpoint row becomes `NaN`.

The runner's intent per the docstring (lines 832-842) is to capture the per-round endpoint for the ablation script's custom scoring. With the hard-coded `reshape(2)`, the endpoint row is **always `NaN` for non-2-D adapters**, defeating the feature.

**Fix direction:** replace `arr[-1].reshape(2)` with `arr[-1].reshape(-1)` (flatten) and let downstream consumers reshape to the adapter's `state_shape` from the capabilities advertisement; or read `adapter.state_shape` and use `arr[-1].reshape(adapter.state_shape)`.

---

#### F-25 (severity 4) — `TwoDimFMAdapter.inject_forward_noise` is missing (no `inject_forward_noise` method)

**File:** `adaptive_reflow/adapters/twodim_fm.py:469-1182`
**Root cause:** the runner at `runner.py:800` checks `hasattr(self._adapter, "inject_forward_noise")` before calling the hook. `TwoDimFMAdapter` (the canonical 2-D adapter used by the 2D harness) does **not** implement `inject_forward_noise`. So the `forward_noise_emitted` flag is set to `True` (line 804) but no actual forward noise is injected. The audit code `FORWARD_NOISE_INJECTED` is emitted (line 864-865) but the bundle is unchanged. This is a **silent no-op** that mis-attributes the round's behaviour.

The same gap exists in `SyntheticContinuousAdapter`, `SyntheticDiscreteAdapter`, `SyntheticMixedChannelAdapter`, `SyntheticUnsupportedAdapter`, `MnistFmAdapter`, `StochasticFMAdapter`, `ToyGaussianAdapter`, `ToyLinearAdapter`, `ReferenceFlowAAdapter` (the latter has a different gap — see F-26).

**Fix direction:** either implement `inject_forward_noise` in every adapter (using `state_shape` from the capabilities), or change the runner's `forward_noise_emitted = True` to be conditional on the hook being implemented.

---

#### F-26 (severity 3) — `ReferenceFlowAAdapter.export_trajectory` raises `NotImplementedError`

**File:** `adaptive_reflow/adapters/reference_flowa.py:303-318`
**Root cause:** the adapter explicitly raises `NotImplementedError` in `export_trajectory`. The runner catches the exception (line 849) and sets `endpoint_export_failed = True`, so this is **fail-closed**, but the audit code emitted (line 864-865) does not distinguish "endpoint export failed because adapter is unsupported" from "endpoint export succeeded". A reader of the metric dict sees `forward_noise_injected=1.0` and `endpoint_export_failed=1.0` but cannot tell whether these are correlated.

**Fix direction:** add a separate audit code `ENDPOINT_EXPORT_NOT_IMPLEMENTED` for the unsupported-adapter case.

---

#### F-27 (severity 3) — `RectifiedFlowCIFARAdapter.inject_forward_noise` shape mismatch (silent garbage)

**File:** `adaptive_reflow/adapters/rectified_flow_cifar.py:997-1051`
**Root cause:** the method accepts `injected: Any` and reshapes to `RF_CIFAR_STATE_SHAPE = (3, 32, 32)` (line 1017). If `injected.shape != (3, 32, 32)`, the reshape raises `ValueError`. The runner constructs `injected` via `np.zeros(adapter_state_shape, ...)` where `adapter_state_shape = (3, 32, 32)` for CIFAR — so the shapes agree. **However**, the cosine scheduler's `inject_noise` (line 463-465 in `_core.py`) returns `state + sqrt(noise_mass) * generator.standard_normal(state_arr.shape)`. If the scheduler is built with a non-CIFAR `profile_residual_fn` (e.g., a unit-test scheduler), the `noise_mass = A_g` and the resulting `state_arr` shape could disagree with `RF_CIFAR_STATE_SHAPE`. The reshape at line 1017 silently fails. The CIFAR adapter's `inject_forward_noise` should validate the shape before reshaping and raise a clear error.

**Fix direction:** add `if np.asarray(injected).shape != RF_CIFAR_STATE_SHAPE: raise ValueError(...)` with an actionable message.

---

#### F-28 (severity 3) — `_gnobitab_ddpmpp.py` strict state_dict load loses params under key aliasing

**File:** `adaptive_reflow/adapters/_gnobitab_ddpmpp.py:1-50` (the load function — not fully read in this audit)
**Root cause:** the load function (per the experiment-log §2) is "torch re-implementation of the published NCSN++/DDPM++ topology (Liu 2022 1-Rectified-Flow, FID=2.58 at 100+ NFE), loading the ``module.all_modules.*`` flat state_dict strictly". A strict load rejects any key aliasing between the published checkpoint's flat layout and the re-implementation's nested module layout. The experiment-log says "61,805,419 parameters loaded" but does not confirm that the **layer parameters** match the published values. If the re-implementation's parameter names do not exactly match `module.all_modules.*`, the strict load produces a partially-initialized model with random init on the unmatched layers.

**Fix direction:** add an integration test that runs a forward pass and compares the output to a published reference tensor (the experiment-log says "std≈0.34, range≈[-1, 1]" — but a numerical match to a published tensor would be stronger).

---

#### F-29 (severity 2) — Most adapters do not implement `inject_forward_noise`; the runner's `forward_noise_emitted=True` is a lie for 8 of 10 adapters

**File:** `adaptive_reflow/algorithm/runner.py:762-804`
**Root cause:** as noted in F-25, only `RectifiedFlowCIFARAdapter` and `MnistFmAdapter` (with `state_shape=(784,)`) implement `inject_forward_noise`. The runner sets `forward_noise_emitted = True` regardless of whether the hook was actually called. The `FORWARD_NOISE_INJECTED` audit code is emitted, the metric dict records `forward_noise_injected=1.0`, but for 8 of 10 adapters no noise was injected.

**Fix direction:** make `forward_noise_emitted` conditional on the hook being implemented *and* the call succeeding.

---

#### F-30 (severity 2) — `SyntheticUnsupportedAdapter` declares `capabilities` but its `solve_ode` is a no-op

**File:** `adaptive_reflow/adapters/synthetic.py:617-633`
**Root cause:** the adapter exists to test the engine's capability-mismatch fail-closed paths. `solve_ode` is a placeholder. The runner's `_engine.run_round` should catch the capability mismatch via `CapabilityMissingError` and emit `ERR_CAPABILITY_UNSUPPORTED`. This is exercised in `tests/property/test_fail_closed_invariants.py`. **No bug**, but the audit code emitted is the same `ERR_CAPABILITY_UNSUPPORTED` for all mismatch types (missing trajectory export, missing forward noise injection, unsupported channel). Severity 2 because the audit trail is non-discriminating.

**Fix direction:** distinguish "unsupported adapter" from "missing optional hook" via separate audit codes.

---

### 2.5 RUNNER + ORCHESTRATOR — `algorithm/runner.py`, `frame/orchestrator.py`

#### F-31 (severity 5) — `ReInferenceRunner.run` bypasses `MergeOperatorProtocol` for the `schedule_derived` driver (CONFIRMED W2 leak)

**File:** `adaptive_reflow/algorithm/runner.py:683-686`
**Root cause:** the F25 fix short-circuits the merge call when `self._driver.driver_family() == "schedule_derived"` (line 683), skipping `self._merge.merge(**_merge_kwargs)` entirely. The justification in the docstring (lines 672-682) is that for the schedule-derived driver, `applied_policy.beta_by_channel == n_cap`, and with `delta_cap_up = delta_cap_down = 1.0` (lines 709-710), the bounded merge collapses to `clamp(n_cap, n_min, n_cap) == n_cap` — a "double-wrapping identity". This is **mathematically correct** but it has two consequences:

1. **The merge operator is never exercised on the schedule-derived path.** Tests at `tests/test_algorithm/test_runner.py::test_runner_calls_merge_operator_between_policy_and_engine` (line 1214) use a non-schedule-derived driver (constant) so the test passes. But the production code path never calls the merge operator, making the operator configurable only on the constant / adaptive / paper-quantity paths. This is a **W2 leak**: the bounded envelope's `floor` (P0-A12 paper-quantity floor) is never enforced on the schedule-derived path.

2. **`schedule_weight=1.0` EMAOperator modulation** (line 821 in merge_operator.py) is unreachable on the schedule-derived path. The runner's `if self._driver.driver_family() == "schedule_derived"` skips the merge call entirely; `schedule_sample` is never threaded to the EMA.

**Fix direction:** remove the bypass; call `self._merge.merge(...)` unconditionally and let the operator decide whether to apply. The bounded merge is byte-equivalent for the schedule-derived + `delta_cap=1.0` case, so the call is free.

---

#### F-32 (severity 4) — `ReInferenceRunner.run` does not call `scheduler.record_round_feedback` for the codim scheduler (CONFIRMED v2 result)

**File:** `adaptive_reflow/algorithm/runner.py` (search for `record_round_feedback`)
**Root cause:** the runner's loop (lines 620-1000) does not invoke `scheduler.record_round_feedback(...)` for any scheduler. The harness wires `record_round_feedback` only for `EvidenceDrivenScheduler` (in `tools/run_sota_cifar_experiment.py` post-v2 fix), but the **runner itself** never calls the hook. So if a runner is used outside the harness (e.g., in `BatchedTrajectoryRunner` for 2D experiments, or in unit tests), the PID-lite controller never accumulates error.

**Fix direction:** call `self._scheduler.record_round_feedback(int(r), metric_dict)` at the bottom of the round loop (after `metric` is built). Pass the per-round `evidence_ratio`, `W2`, `coverage` keys as the feedback dict. This closes Loop 2 for the runner's data path.

---

#### F-33 (severity 4) — `ReInferenceRunner.run` does not reset `_state_machine` between re-runs

**File:** `adaptive_reflow/algorithm/runner.py:600-1000` (the `_state_machine` is constructed in `__init__`)
**Root cause:** the `AdaptiveReflowPolicyOrchestrator._state_machine` is a member of the runner, but `runner.run()` does not call `state_machine.reset()` between calls. A second `runner.run()` call sees the state machine in `FEEDBACK_PENDING` (the last state of the previous run), and `send("SAMPLE_REQUESTED")` is rejected by the guard (silent no-op in non-strict mode). The second run's round 0 is dropped on the floor.

**Fix direction:** call `self._state_machine.reset()` (or `send("INITIALIZE")` if the HSM exposes one) at the top of `run()`.

---

#### F-34 (severity 3) — `ReInferenceRunner` constructs the per-round bundle via `build_initial_state` at `r=0` but does not propagate the `bundle` for `r>0`

**File:** `adaptive_reflow/algorithm/runner.py:748-752`
**Root cause:** the runner only calls `self._adapter.build_initial_state(...)` for `r=0`. For `r>0`, `bundle` is the *previous* round's `bundle` — but the runner never updates `bundle` to the new round's prior state. The same bundle is passed to `run_round` for every round. This means the **per-round state is not chained**: round `r+1` sees round `r`'s `bundle.source_round`, not `r+1`'s.

**Fix direction:** update `bundle` after each round's `run_round` (e.g., `bundle = self._adapter.export_endpoint(result.round_trace.endpoint)`).

---

#### F-35 (severity 3) — `AdaptiveReflowPolicyOrchestrator.merge_operator` setter accepts any `MergeOperatorProtocol` but does not validate

**File:** `adaptive_reflow/frame/orchestrator.py:300-432`
**Root cause:** the constructor stores `merge_operator` (line 377) without validating it conforms to `MergeOperatorProtocol`. The `@runtime_checkable` decorator makes `isinstance` checks possible, but the constructor does not call them. A caller could pass a duck-typed object missing `to_config` or `config_hash` and the orchestrator would accept it.

**Fix direction:** add `isinstance(merge_operator, MergeOperatorProtocol)` check (with a soft-fail warning for back-compat).

---

### 2.6 ENGINE — `frame/engine.py`

#### F-36 (severity 4) — `run_round` still has the inline `_policy_with_schedule_beta` override (W3 from R3)

**File:** `adaptive_reflow/frame/engine.py:770-814` (helper), `1443-1444` (call site)
**Root cause:** the engine applies `_policy_with_schedule_beta(policy, audit_codes)` when `policy.beta_from_schedule=True and not policy.driver_computed_beta`. The runner sets `driver_computed_beta=True` so the engine's override is suppressed on the runner's path. **However**: any non-runner caller (e.g., a direct `run_round` invocation from a unit test, or from `BatchedTrajectoryRunner`) that creates a `FinalRestartPolicy` with `beta_from_schedule=True` (default) and `driver_computed_beta=False` (default) **will** see the engine override `beta` to `n_cap`. This is the original W3 bug, and it's only avoided by the runner's explicit `driver_computed_beta=True` flag.

The runner sets the flag (line 730 in `runner.py:applied_policy = replace(applied_policy, ..., driver_computed_beta=True)`), but a code review of the runner shows the flag is set **after** `merge_step` — so during the merge step, `policy.driver_computed_beta` is still `False`. The engine's `run_round` check (line 1443) reads `policy.driver_computed_beta` *after* the merge step (which happens in the runner, not the engine), so by the time `run_round` sees the policy, `driver_computed_beta=True`. This is correct but fragile: any future refactor that re-orders the runner's pipeline could break it.

**Fix direction:** set `driver_computed_beta=True` *before* the runner's merge step, or move the flag-setting into the driver's `compute_policy` helper so it's part of the contract.

---

#### F-37 (severity 3) — `run_round` capability check does not include `inject_forward_noise`

**File:** `adaptive_reflow/frame/engine.py:1016-1300` (run_round body)
**Root cause:** the engine checks `capability_token` against `apply_restart_distribution`, `compose_condition`, `solve_ode`, `observe_endpoint`, `export_trajectory` (5 of the 8 Protocol methods). It does **not** check `inject_forward_noise`. So an adapter missing the hook is silently accepted (the runner's `hasattr` check at `runner.py:800` is the only guard). This is consistent with F-25/F-29 — the engine treats `inject_forward_noise` as optional.

**Fix direction:** document the optional-hook policy in the Protocol docstring; consider promoting `inject_forward_noise` to a required method (with a no-op default for back-compat).

---

#### F-38 (severity 3) — `run_round` audit codes are emitted in random order across fail-closed paths

**File:** `adaptive_reflow/frame/engine.py:939-1014` (`_emit_fail_closed`)
**Root cause:** the audit list is mutated by every check; the order depends on which check fires first. A `round_trace.audit_codes = ("capability_unsupported", "endpoint_not_detached", ...)` is ordered by the check order, not by semantic priority. A reader cannot tell from the audit codes alone whether the most-severe check (capability mismatch) fired first.

**Fix direction:** define a canonical ordering (e.g., capability → bundle → policy → integrator → endpoint) and sort the audit list before emission.

---

#### F-39 (severity 2) — `run_round` does not reset `_last_bounded_fraction` on the orchestrator between cycles

**File:** `adaptive_reflow/frame/orchestrator.py:1139` (`reset_cycle`)
**Root cause:** `reset_cycle` clears `_ledger_records`, `_last_bounded_fraction`, and `_schedule_sampler._last_sample`. But the runner's `run_round` does not call `reset_cycle` between cycles. A multi-cycle run sees stale `_last_bounded_fraction` from the previous cycle's last round, polluting the next cycle's first round.

**Fix direction:** call `orchestrator.reset_cycle()` at the top of each outer cycle.

---

### 2.7 EVALUATORS — `eval/w2.py`, `coverage.py`, `mnist_fid.py`

#### F-40 (severity 4) — `MnistFidEvaluator` does not actually use InceptionV3 features

**File:** `adaptive_reflow/eval/mnist_fid.py:154-264`
**Root cause:** per the class docstring and `_random_projection`/`_frechet_distance` helpers, the evaluator computes Fréchet distance on a **random projection** of flattened pixel space, not on InceptionV3 features. The standard MNIST FID uses a LeNet-style or a custom feature extractor; the published CIFAR FID uses InceptionV3. The name `MnistFidEvaluator` is misleading — it computes a "Fréchet on a random linear projection" statistic, which is a valid metric but is **not** FID. The audit trail labels it as `fid` in the `summary.json` (per `tools/run_sota_cifar_experiment.py`), which conflates two different statistics.

**Fix direction:** rename `MnistFidEvaluator` to `MnistFrechetProjectionEvaluator` (or implement the canonical MNIST FID pipeline). Document the projection dimension (`n_components`) in the public surface.

---

#### F-41 (severity 3) — `ModeCentreMSEW2` is labelled `W2` but is not Wasserstein distance

**File:** `adaptive_reflow/eval/w2.py:253-295`
**Root cause:** the class docstring (line 261-264) acknowledges: "This is **not** a Wasserstein distance: it ignores the reference measure's masses entirely". Yet the metric is exported as `W2` in the runner's metric dict (`runner.py:921-923`). The audit invariant "the metric name identifies the estimator" is broken: the name says Wasserstein, the math says MSE.

**Fix direction:** rename `mode_centre_mse` to `mode_centre_mse` (keep) but require the runner to prefix the metric key with the estimator family (e.g., `W2_mode_centre_mse`).

---

#### F-42 (severity 3) — `ProjectionFreeExactW2` does not handle unequal reference / sample sizes deterministically

**File:** `adaptive_reflow/eval/w2.py:302-440`
**Root cause:** the docstring claims "the quantile grid resolved at ``max(len(X), len(Y))`` points so unequal sample sizes are handled without resampling". The implementation uses `np.sort` + interpolation but does not document which quantile estimator is used (R7 vs R8 from Hyndman & Fan 1996). Two different numpy versions could pick different default interpolators, breaking reproducibility.

**Fix direction:** specify the quantile interpolator explicitly (`np.quantile(..., method='linear')`).

---

#### F-43 (severity 2) — `coverage.py` does not export its `config_hash` for provenance

**File:** `adaptive_reflow/eval/coverage.py` (the `CoverageEvaluator` class — not fully read)
**Root cause:** the coverage evaluator exposes `evaluate(...)` but no `config_hash()` method. The audit trail cannot fingerprint the coverage estimator for a given run.

**Fix direction:** add `config_hash()` and `to_config()` methods following the pattern of the W2 estimators.

---

#### F-44 (severity 2) — `PosteriorSelectionEvaluator` oracle metric key naming inconsistent

**File:** `adaptive_reflow/eval/posterior_selection_evaluator.py` (sampled, not fully read)
**Root cause:** the evaluator emits `selection_ratio` for the per-round metric but the harness CSV expects `evidence_ratio` (per the v2 fix in `tools/run_sota_cifar_experiment.py:443-449`). The two values are conceptually identical but the audit-trail mapping is done in the harness, not the evaluator.

**Fix direction:** standardise on one key (either `selection_ratio` or `evidence_ratio`) at the evaluator level; the harness reads it verbatim.

---

### 2.8 PAPER QUANTITIES — `contracts/paper_quantities.py`

#### F-45 (severity 3) — `sheet_evidence_A` trapezoidal correction double-counts interior nodes

**File:** `adaptive_reflow/contracts/paper_quantities.py:120-139`
**Root cause:** the loop at line 122-129 sums `total += f_s` at every grid point, then at line 132-137 subtracts `0.5 * f_s` at both endpoints. The composite trapezoidal rule requires `f_s` weighted by `h` for interior nodes and `h/2` for the two endpoints. The implementation applies `f_s * h` to *all* nodes via `total *= h` at line 138, then subtracts the endpoint overweight. **This is correct** (the alternative would be `0.5 * f_s` for endpoints inside the loop), but the asymmetric structure is confusing. More importantly: the function declares `f_s = math.exp(-0.5 * s * s) / denom` but does not include the `s=0` node with double-weight. Verified: the loop visits every `s_k = -K + k*h` for `k=0..N`, which is correct for `N = 2K/h`. The function is byte-stable (verified per docstring claim).

**No bug, but the audit invariant "discretisation error bound is honest"** is **not enforced** in the implementation. The `SheetEvidenceResult.discretization_error` field (line 338) is `K * h^2 / 12 * M_2` (per the comment) but the actual error from a trapezoidal rule on `f(s)` over `[-K, K]` is `K * h^2 / 12 * max |f''(s)|`. The current bound is a **rough upper bound** — not the exact error. The audit invariant "the discretization error bound is honest" is violated by an order of magnitude.

**Fix direction:** compute the exact second derivative `|f''(s)|` symbolically (or sample on a fine grid) and report the exact trapezoidal error bound.

---

#### F-46 (severity 3) — `root_cell_packing_B` sign-change detection misses zeros at `x=K`

**File:** `adaptive_reflow/contracts/paper_quantities.py:212-229`
**Root cause:** the loop checks `y0 * y1 < 0.0` (sign change between adjacent grid nodes) and `y0 == 0.0` (exact zero at grid node). The final endpoint `x=K` is checked at the *next-to-last* iteration when `y0` is `ys[-2]` and `y1` is `ys[-1]`. But if `g(K) == 0.0`, the condition `ys[-2] * ys[-1] == 0.0 * something != 0` is **never satisfied** because `ys[-2] * 0.0 == 0.0`, which is **not** `< 0.0`. The branch `y0 == 0.0` is checked, but at `i = len(xs) - 1`, `y0 = ys[-1] = 0.0` is *not* iterated (the loop is `range(len(xs) - 1)`). So a zero at `x = K` is silently missed.

**Fix direction:** add an explicit `if ys[-1] == 0.0: total += exp(-K^2/4)` after the loop.

---

#### F-47 (severity 2) — `per_cell_coefficient_C` validation rejects `c > 1`

**File:** `adaptive_reflow/contracts/paper_quantities.py:265-275`
**Root cause:** the formula uses `min(c*c, 1.0)` in `a = (1-rho)^2 * min(c^2, 1)`. The `min` clip silently caps `c` at 1, but the validation at line 268 accepts any `c > 0`. A user passes `c=2` and gets `C_g = exp(rho^2/2) / (1-rho)^2`, which is *correct* but the validation does not warn that `c` was clipped. The audit trail shows `c=2` in the result, but the actual computation used `c=1`.

**Fix direction:** document the clip in the docstring and the result dataclass.

---

#### F-48 (severity 2) — `exterior_gap_e_rho` returns the minimum, not the literal paper quantity

**File:** `adaptive_reflow/contracts/paper_quantities.py:307-311`
**Root cause:** paper line 128: `e_rho = min{rho^4, (1-rho)^2 eta^2}`. The implementation returns `min(rho**4, (1-rho)**2 * eta**2)`. **This is correct** but does not validate that `rho in (0, 1)` is consistent with the rest of the framework (the codim scheduler uses `eps_implicit=0.05`, but `rho` and `eta` are not coupled to `eps_implicit`). A user could configure `rho=0.05, eta=0.5` and get `e_rho = min(6.25e-6, 0.225) = 6.25e-6`, which is **too small** to be a useful floor (`e_rho / 4 ≈ 1.56e-6`). The codim scheduler would then floor `noise_mass` at `1.56e-6` — effectively zero noise.

**Fix direction:** add a `minimum_useful_floor` warning when `e_rho < 1e-4`.

---

### 2.9 STATE MACHINES — `contracts/state_machine.py`

#### F-49 (severity 3) — `StateMachine._dispatch_sync` parallel region fallback to self-transitions swallows silent events

**File:** `adaptive_reflow/contracts/state_machine.py:752-773`
**Root cause:** when a parallel state has sub-regions, the dispatch at line 754-758 forwards the event to all regions that can handle it. If **no region handles it**, the code falls through to line 763 (try self-transitions). This is documented as UML "ignored event" but the **audit log does not record the fall-through**. A reader sees no log entry but the event was sent; debugging is hard.

**Fix direction:** emit a `parallel_no_region_handled` log entry when no sub-region can handle the event.

---

#### F-50 (severity 3) — `StateMachine._try_pick_sync` priority tie-break uses registration order, not lexicographic

**File:** `adaptive_reflow/contracts/state_machine.py:813-820`
**Root cause:** the sort key is `(-priority, registration_index)`. When two transitions have the same priority, the registration order breaks the tie. This is correct (deterministic) but the docstring does not document the tie-break. The audit invariant "byte-deterministic log" relies on registration order being stable, but a `set` or `dict` iteration order could destabilise it.

**Fix direction:** use a stable secondary key (e.g., the transition's target state) for tie-breaks.

---

#### F-51 (severity 2) — `StateMachine` strict-guard mode is silently disabled by default

**File:** `adaptive_reflow/contracts/state_machine.py:425-426`
**Root cause:** `with_strict_guards(False)` is the default; guards that reject silently no-op. This matches classic UML semantics, but the **audit invariant "every rejected event is recorded"** is broken. A reader sees no log entry for a rejected transition.

**Fix direction:** emit an audit log entry when a guard rejects (even in non-strict mode).

---

#### F-52 (severity 2) — `StateMachine.log` is `tuple[TransitionLog, ...]`, but `TransitionLog.__hash__` is not defined

**File:** `adaptive_reflow/contracts/state_machine.py:134-178`
**Root cause:** `TransitionLog` is a `dataclass(frozen=True)` but does not define `__hash__`. With `frozen=True`, the default `__hash__` is the field-based hash, which works for the dataclass. **No bug**, but the dataclass uses `tuple` fields which are hashable. Severity 2 because the docstring (line 41) claims "byte-deterministic transition logging" and the log is *deterministic* but *not efficiently hashable* (the hash includes all field hashes).

**Fix direction:** add an explicit `__hash__` method that hashes only the `(state, event, source, target)` tuple.

---

### 2.10 CONTRACTS — `contracts/*.py`

#### F-53 (severity 3) — `FinalRestartPolicy.policy_hash` is recomputed on every override but the `beta_from_schedule` flag is not in the hash

**File:** `adaptive_reflow/contracts/authority.py` (sampled)
**Root cause:** `hash_policy_hash(policy)` is supposed to be a stable identity for the policy. The hash should include `beta_from_schedule`, `driver_computed_beta`, `schedule_sample.n_cap`, and `beta_by_channel`. A grep would confirm — but the runner sets `driver_computed_beta=True` *after* the hash recompute at `runner.py:727-735`. Two policies with the same `beta_by_channel` but different `driver_computed_beta` flags would have the same hash if the flag is not in the hash inputs.

**Fix direction:** add `driver_computed_beta` to the `hash_policy_hash` inputs.

---

#### F-54 (severity 3) — `ODEConditionDelta` validation does not enforce `target_round >= 0`

**File:** `adaptive_reflow/contracts/` (the ODEConditionDelta dataclass)
**Root cause:** the dataclass accepts any int for `target_round`. The runner validates `r >= 0` before constructing the delta, but the validator itself does not enforce it. A direct caller could construct a negative-`target_round` delta.

**Fix direction:** add `validate_ode_condition_delta` to the validators module.

---

#### F-55 (severity 2) — `StateBundle.source_round` is not validated as `>= 0`

**File:** `adaptive_reflow/contracts/bundle.py` (the StateBundle dataclass)
**Root cause:** similar to F-54; the dataclass accepts any int.

**Fix direction:** add a validator.

---

#### F-56 (severity 2) — `validate_final_restart_policy` does not check `beta_by_channel` keys against `ChannelName`

**File:** `adaptive_reflow/contracts/authority.py`
**Root cause:** the validator checks that `beta_by_channel` values are in `[0, 1]` but not that the keys are valid `ChannelName`s. A misconfigured caller could pass `{"invalid": 0.5}` and the validator would accept it.

**Fix direction:** validate keys against the `CHANNEL_NAMES` literal set.

---

## §3. Bug severity ranking (most critical first)

| # | Bug | Severity | File:line |
|---|---|:---:|---|
| F-31 | Runner bypasses MergeOperatorProtocol for schedule_derived (W2 leak) | **5** | `algorithm/runner.py:683` |
| F-18 | BoundedMergeOperator raises on cap<floor (contradicts Protocol docstring) | **5** | `algorithm/merge_operator.py:591` |
| F-24 | Runner hardcodes `.reshape(2)` for non-2D adapters | **5** | `algorithm/runner.py:856` |
| F-1 | FreeTrajScheduler cache freezes trajectory_progress | **4** | `algorithm/scheduler/freetraj.py:308` |
| F-2 | EvidenceDrivenScheduler.config_hash drops k_eps | **4** | `algorithm/scheduler/evidence_driven.py:402` |
| F-19 | MeanFlowMergeOperator updates _prev_dynamic before bounded merge | **4** | `algorithm/merge_operator_v3.py:248` |
| F-32 | Runner does not call scheduler.record_round_feedback | **4** | `algorithm/runner.py:run` |
| F-33 | Runner does not reset state_machine between runs | **4** | `algorithm/runner.py:run` |
| F-36 | Engine still has inline _policy_with_schedule_beta override | **4** | `frame/engine.py:1443` |
| F-25 | 8 of 10 adapters missing inject_forward_noise | **4** | `adapters/*.py` |
| F-40 | MnistFidEvaluator mislabelled as FID (it's a projection Fréchet) | **4** | `eval/mnist_fid.py:154` |
| F-3 | EvidenceDrivenScheduler._last_pid_delta is one round stale | **3** | `algorithm/scheduler/evidence_driven.py:338` |
| F-4 | ConvergenceAdaptiveScheduler re-derives n_cap via cosine for non-cosine base | **3** | `algorithm/scheduler/_core.py:1931` |
| F-5 | CodimensionSheetScheduler.record_round_feedback is no-op | **3** | `algorithm/scheduler/_core.py:2816` |
| F-14 | AdaptivePolicyDriver ignores empty prior_endpoint_digest | **3** | `algorithm/policy_driver.py:673` |
| F-20 | MeanFlowMergeOperator has no reset() | **3** | `algorithm/merge_operator_v3.py:144` |
| F-21 | MeanFlowMergeOperator re-clip emits stale audit value | **3** | `algorithm/merge_operator_v3.py:261` |
| F-26 | ReferenceFlowAAdapter.export_trajectory raises (no audit distinction) | **3** | `adapters/reference_flowa.py:303` |
| F-27 | CIFAR adapter inject_forward_noise silently fails on shape mismatch | **3** | `adapters/rectified_flow_cifar.py:997` |
| F-28 | _gnobitab_ddpmpp strict load may partial-init on key aliasing | **3** | `adapters/_gnobitab_ddpmpp.py` |
| F-34 | Runner does not propagate bundle between rounds | **3** | `algorithm/runner.py:748` |
| F-35 | Orchestrator does not validate MergeOperatorProtocol | **3** | `frame/orchestrator.py:300` |
| F-37 | run_round capability check omits inject_forward_noise | **3** | `frame/engine.py:1016` |
| F-38 | run_round audit codes emitted in non-canonical order | **3** | `frame/engine.py:939` |
| F-41 | ModeCentreMSEW2 is mislabelled as Wasserstein | **3** | `eval/w2.py:253` |
| F-42 | ProjectionFreeExactW2 quantile interpolator not pinned | **3** | `eval/w2.py:302` |
| F-45 | sheet_evidence_A discretization_error bound is rough | **3** | `contracts/paper_quantities.py:338` |
| F-46 | root_cell_packing_B misses zero at x=K | **3** | `contracts/paper_quantities.py:212` |
| F-49 | StateMachine parallel fallback to self swallows log | **3** | `contracts/state_machine.py:752` |
| F-53 | hash_policy_hash may omit driver_computed_beta | **3** | `contracts/authority.py` |
| F-54 | ODEConditionDelta validator does not check target_round >= 0 | **3** | `contracts/` |
| F-6 | CosineAnnealScheduler accepts round_in_cycle=-1 without audit | **2** | `algorithm/scheduler/_core.py:373` |
| F-7 | LinearScheduler monotone direction not in audit code | **2** | `algorithm/scheduler/_core.py:889` |
| F-8 | ConstantScheduler edge case cycle_length=1 undocumented | **2** | `algorithm/scheduler/_core.py:662` |
| F-9 | Polynomial/Sigmoid lack cycle_length=1 test | **2** | `algorithm/scheduler/_core.py:1311` |
| F-10 | CosineScheduleConfig.config_hash vs CosineAnnealScheduler.config_hash diverge | **2** | `algorithm/scheduler/_core.py:408` |
| F-13 | build_scheduler_from_config fallback dead code | **2** | `algorithm/scheduler/_core.py:3217` |
| F-15 | AdaptivePolicyDriver.beta_saturation_count not reset on cycle | **2** | `algorithm/policy_driver.py:505` |
| F-16 | ConstantPolicyDriver does not emit audit code | **2** | `algorithm/policy_driver.py:448` |
| F-17 | _override_beta_by_channel silently no-ops on empty vocab | **2** | `algorithm/policy_driver.py:154` |
| F-22 | EMAOperator schedule modulation can exceed alpha range | **2** | `algorithm/merge_operator.py:807` |
| F-23 | BoundedMergeOperator tolerance has no observable effect | **2** | `algorithm/merge_operator.py:386` |
| F-29 | Runner's forward_noise_emitted=True is a lie for 8 of 10 adapters | **2** | `algorithm/runner.py:804` |
| F-30 | SyntheticUnsupportedAdapter uses one audit code for all mismatch types | **2** | `adapters/synthetic.py:617` |
| F-39 | Orchestrator._last_bounded_fraction not reset between cycles | **2** | `frame/orchestrator.py:1139` |
| F-43 | coverage.py lacks config_hash | **2** | `eval/coverage.py` |
| F-44 | PosteriorSelectionEvaluator metric key naming | **2** | `eval/posterior_selection_evaluator.py` |
| F-47 | per_cell_coefficient_C c-clip silent | **2** | `contracts/paper_quantities.py:265` |
| F-48 | exterior_gap_e_rho can return near-zero | **2** | `contracts/paper_quantities.py:307` |
| F-50 | StateMachine priority tie-break unstable | **2** | `contracts/state_machine.py:813` |
| F-51 | StateMachine strict-guard mode silently disabled | **2** | `contracts/state_machine.py:425` |
| F-52 | TransitionLog has no explicit __hash__ | **2** | `contracts/state_machine.py:134` |
| F-55 | StateBundle.source_round not validated | **2** | `contracts/bundle.py` |
| F-56 | validate_final_restart_policy does not check ChannelName keys | **2** | `contracts/authority.py` |
| F-11 | _paper_evidence_balance fallback unreachable | **1** | `algorithm/scheduler/_core.py:2257` |
| F-12 | CosineScheduleConfig.frozen_before_evaluation is dead config | **1** | `algorithm/scheduler/_core.py:562` |

**Total bugs found: 52.**

---

## §4. Test coverage gaps

### 4.1 Untested algorithms

| Class | Reason | Severity |
|---|---|:---:|
| `MultiChannelJitteredConstantScheduler` (`scheduler_r2.py`) | only referenced in `from_config` dispatch; no unit tests found | 3 |
| `EDMScheduler`, `AdaptivePIDScheduler`, `JitteredConstantScheduler` (`scheduler_extra.py`) | mentioned in `from_config` but no direct unit tests found | 3 |
| `DualTargetAdaptivePolicyDriver` (`policy_driver.py:1039`) | only mentioned in grep; no unit tests | 3 |
| `MultiChannelConstantPolicyDriver` (`policy_driver.py:923`) | only mentioned in grep; no unit tests | 3 |
| `CodimensionSheetScheduler` paper-quantity path | only framework-heuristic path tested; paper-augmented path (`profile_residual_fn`) under-tested | 2 |
| `FreeTrajScheduler._compute_trajectory_progress` cache bug | pinned as expected behavior by `test_freetraj_trajectory_progress_freezes_when_driven_statefully` | 5 |

### 4.2 Untested edge cases

| Module | Edge case | Severity |
|---|---|:---:|
| All schedulers | `cycle_length = 1` returns `n_max` for every family | 2 |
| `BoundedMergeOperator` | `cap = floor` (degenerate envelope, single-point interval) | 2 |
| `MeanFlowMergeOperator` | `_prev_dynamic` round-0 → round-1 transition | 3 |
| `AdaptivePolicyDriver` | `prior_endpoint_digest = ""` (round 0) | 2 |
| `EMAOperator` | `alpha > 1` via `schedule_weight` modulation | 2 |
| `CodimensionSheetScheduler` | `eps_direction = "increasing"` (legacy) | 2 |
| `RunInferenceRunner` | `driver_family == "schedule_derived"` skipping merge (this is the F-31 bug) | 5 |
| `engine.run_round` | `policy.driver_computed_beta = False` (legacy path) | 3 |
| `StateMachine` | parallel region fall-through (no region handles) | 3 |
| `paper_quantities.root_cell_packing_B` | exact zero at `x = K` | 3 |

### 4.3 Missing regression tests for known bugs

| Bug | Existing test | Direction |
|---|---|---|
| F-1 | `test_freetraj_trajectory_progress_freezes_when_driven_statefully` pins the bug | invert or delete |
| F-31 | `test_runner_calls_merge_operator_between_policy_and_engine` uses constant driver | add schedule_derived negative |
| F-25 | no test | add `test_runner_emit_forward_noise_audit_only_when_hook_implemented` |
| F-2 | no test | add `test_evidence_driven_config_hash_varies_with_k_eps` |
| F-40 | no test | add `test_mnist_fid_uses_projection_not_inception` |
| F-41 | no test | add `test_mode_centre_mse_metric_key_includes_family` |

---

## §5. Cross-cutting concerns

### 5.1 Naming inconsistencies

- **`MnistFidEvaluator`** (F-40) is not FID; uses random linear projection of pixel space. Should be `MnistFrechetProjectionEvaluator`.
- **`ModeCentreMSEW2`** (F-41) is not Wasserstein. Metric key in runner's `W2` is misleading.
- **`FREE_TRAJ_SUBSTEP_AUDIT`** constant (`freetraj.py:55`) is `freetraj_substep_audit`; the audit code emitted is identical.
- **`schedule_linear_baseline`** doesn't distinguish ramp-up from ramp-down (F-7).
- **`schedule_polynomial_baseline`**, **`schedule_sigmoid_baseline`** are emitted but the `power`/`steepness`/`midpoint` knobs are not surfaced in the audit code.

### 5.2 Deprecated CLAMs (legacy compatibility shims)

- `CosineScheduleConfig.frozen_before_evaluation` (F-12) — field set everywhere, never read.
- `BoundedMergeOperator.tolerance` (F-23) — accepted, hashed, round-tripped, never read.
- `schedule_sample` arg in `IdentityOperator.merge` — accepted but ignored. Same for `EMAOperator.merge`'s envelope args (`cap`, `floor`, `delta_cap_up`, `delta_cap_down`).
- `_coerce_int_nonneg` helper duplicates the coercion that `n_cap_for_round` performs internally.

### 5.3 Capability handshake gaps

- `inject_forward_noise` is documented as Protocol-required (line 240–255 of `_core.py` docstring) but is not in the runtime `Protocol` class (only mentioned in comments). 8 of 10 adapters don't implement it.
- `export_trajectory` raises `NotImplementedError` in `ReferenceFlowAAdapter` (F-26) — fail-closed but no audit distinction.

### 5.4 Determinism concerns

- `EMAOperator.schedule_weight` modulation can exceed `alpha=1` (F-22); clipping hides the bug but breaks the EMA semantics.
- `StateMachine` priority tie-break uses registration order (F-50); a `set`/`dict` iteration could destabilise.
- `Coverage.py` lacks `config_hash` (F-43); reproducibility fingerprint incomplete.
- `_paper_evidence_balance` fallback branch is unreachable (F-11); dead code could mask future regressions.

### 5.5 Documentation drift

- `MergeOperatorProtocol` docstring (line 254) promises no-raise on `cap < floor`; the implementation raises (F-18).
- `FreeTrajScheduler` docstring (line 77-80) claims `record_round_feedback` advances trajectory_progress; the implementation accepts but the cache bug (F-1) means subsequent `sample()` calls return the cached value regardless.
- `EvidenceDrivenScheduler.config_hash` docstring claims "every constructor argument is in the digest"; `k_eps` is missing (F-2).
- `CodimensionSheetScheduler.record_round_feedback` is documented as a no-op but the C4 docstring at line 2816-2822 says "open-loop on rounds" — implying a future uplift is expected.

---

## §6. Architecture smells

### 6.1 Duplicate "engine-side override" paths

Both the runner (`runner.py:683`) and the engine (`engine.py:1443`) check `driver_computed_beta` to decide whether to override `beta_by_channel`. The runner sets the flag to suppress the engine. This is a **second source of truth** for "who owns `beta`". A future refactor could break the contract.

**Direction:** pick one. The runner is the canonical site; the engine should always honour `beta_by_channel` as-supplied.

### 6.2 State scattered across modules

`ReInferenceRunner` owns: `_state_machine`, `_merge_operator`, `_driver`, `_scheduler`, `_adapter`, `_engine`, `_evaluator`, `_ledger_records`, `_last_bounded_fraction`, `_schedule_sampler`. The orchestrator (`frame/orchestrator.py`) owns its own copies. Two state machines for the same round — one in the runner, one in the orchestrator — is a smell.

**Direction:** unify under `ReInferenceRunner` and have the orchestrator delegate.

### 6.3 Config round-trip fragility

`scheduler_extra.py` is registered lazily (`_register_extra_scheduler_families`) to break an import cycle (per the docstring at `_core.py:3041-3070`). The cycle is **inherent to the design** — scheduler implementations import from `algorithm`, which imports from `scheduler`. The lazy registration masks the cycle but does not fix it. Future moves of symbol references could re-introduce the `ImportError`.

**Direction:** refactor the cycle by splitting `algorithm` into a thin interface module and the implementation modules.

### 6.4 Hard-coded shape assumptions

`runner.py:856` `.reshape(2)` (F-24) is the canonical example. Adapter-specific shapes are not propagated. The fix is to thread `adapter.state_shape` through to every reshape site.

### 6.5 Mean-flow merge operator has undocumented state

`MeanFlowMergeOperator._prev_dynamic` and `_ema_grad` are instance state that survives across rounds but not across re-uses of the operator instance. The contract is unclear (F-20).

### 6.6 Audit-code vocabulary sprawl

The audit-code surface is large (BETA_SATURATION_FROM_PAPER_QUANTITY, FORWARD_NOISE_INJECTED, MERGE_DEGENERATE_INTERVAL, MERGE_PAPER_QUANTITY_FLOOR_LIFTED, MERGE_NONFINITE_PREV_CLIPPED, MERGE_NONFINITE_DYNAMIC_CLIPPED, MERGE_CAP_OUT_OF_RANGE, MERGE_FLOOR_OUT_OF_RANGE, MEANFLOW_DECOMPOSITION_AUDIT, MEANFLOW_PAIR_INVALID, ERR_CAPABILITY_UNSUPPORTED, ERR_SCHEDULE_SAMPLE_MISSING, etc.) with no central registry. A reader cannot enumerate the full vocabulary.

**Direction:** publish a `AUDIT_CODE_REGISTRY` in `contracts.audit` so the audit trail is enumerable.

---

## §7. Fix priority list

### P0 — must fix for the paper

1. **F-31** Runner bypasses MergeOperatorProtocol (W2 leak) — 1 file, 4 LoC change.
2. **F-1** FreeTrajScheduler cache freezes trajectory_progress — 1 file, 2 LoC change.
3. **F-18** BoundedMergeOperator raises on cap<floor (contradicts Protocol) — 1 file, docstring + 5 LoC.
4. **F-24** Runner hardcodes `.reshape(2)` for non-2D adapters — 1 file, 1 LoC.
5. **F-32** Runner does not call scheduler.record_round_feedback — 1 file, 3 LoC.
6. **F-40** MnistFidEvaluator mislabelled as FID — 1 file, rename + add docstring.
7. **F-41** ModeCentreMSEW2 is mislabelled as Wasserstein — 1 file, docstring + runner metric key prefix.

### P1 — should fix (improves correctness, not paper-blocking)

8. **F-2** EvidenceDrivenScheduler.config_hash drops k_eps — 1 file, 2 LoC.
9. **F-3** EvidenceDrivenScheduler._last_pid_delta is one round stale — 1 file, audit code.
10. **F-4** ConvergenceAdaptiveScheduler re-derives n_cap via cosine — 1 file, raise NotImplementedError.
11. **F-5** CodimensionSheetScheduler.record_round_feedback is no-op — 1 file, docstring.
12. **F-19** MeanFlowMergeOperator._prev_dynamic update ordering — 1 file, 1 LoC.
13. **F-20** MeanFlowMergeOperator has no reset() — 1 file, 5 LoC.
14. **F-21** MeanFlowMergeOperator re-clip emits stale audit value — 1 file, 3 LoC.
15. **F-25** 8 of 10 adapters missing inject_forward_noise — 8 files, ~10 LoC each.
16. **F-33** Runner does not reset state_machine between runs — 1 file, 1 LoC.
17. **F-34** Runner does not propagate bundle between rounds — 1 file, 2 LoC.
18. **F-36** Engine still has inline _policy_with_schedule_beta override — 1 file, 3 LoC.
19. **F-42** ProjectionFreeExactW2 quantile interpolator not pinned — 1 file, 1 LoC.
20. **F-45** sheet_evidence_A discretization_error bound is rough — 1 file, docstring.
21. **F-46** root_cell_packing_B misses zero at x=K — 1 file, 4 LoC.
22. **F-53** hash_policy_hash may omit driver_computed_beta — 1 file, 1 LoC.

### P2 — nice to have

All other F-* bugs from §3 with severity ≤ 2.

---

## §8. End notes

- This audit covers the algorithm layer (schedulers, drivers, merge operators), the adapters, the runner/orchestrator, the engine, the evaluators, the paper quantities, the state machines, and the contracts surface. It does NOT cover the molecular layer, the diagnostics layer, the envelope layer, the schedule helpers (beyond `n_cap_for_round`), the channel rule, the blender, the handover, the evidence driver, the rotation policy, the protocol registry, the runner registry, or the sequential scheduler. Those are out of scope per the task brief.
- The audit verified the known r11 bugs (F-1, F-24, F-31, F-32, F-18) and identified 46 additional bugs. The fix plan in `19-fix-plan.md` prioritises 7 P0 fixes that are load-bearing for the paper (path A = scheduler discrimination; path B = better FID) and 15 P1 fixes that improve correctness without blocking the paper.
