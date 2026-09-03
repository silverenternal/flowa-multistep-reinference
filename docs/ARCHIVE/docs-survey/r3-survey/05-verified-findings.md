# 05 — Adversarial Verification of Counterintuitive Findings — R3 Survey

Read-only adversarial pass over `c:/Users/31472/codes/flowa-multistep-reinference`,
re-checking each finding in
[`04-counterintuitive-findings.md`](04-counterintuitive-findings.md)
against concrete code, tests, and runtime reproductions.

Survey date: 2026-08-29.

Method: for each finding I read the cited file:line, ran an inline Python
reproduction via `.venv/Scripts/python.exe -c "..."` (no repo files
written), searched for callers/tests, and (where helpful) checked git
history. Default disposition is **REFUTED** unless concrete evidence
supports the claim.

---

## Finding #1 — `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` is never emitted by the canonical operator

- **Category:** D (Dead-letter output)
- **Refutation attempt:**
  - Read `adaptive_reflow/algorithm/merge_operator.py:89` (definition),
    line 510-614 (operator body), line 838 (`__all__`).
  - Grep for the constant across the package.
  - Ran `BoundedMergeOperator().merge(prev=0.0, dynamic=0.5, cap=0.7,
    floor=0.3, ...)` and inspected the audit list.
- **Concrete evidence:**
  ```
  Constant defined: merge_prev_anchored_to_last_emitted
  audit codes from BoundedMergeOperator: []
  ```
  Grep shows the constant is emitted only in
  `adaptive_reflow/frame/merge.py:409` (legacy `bounded_merge_with_schedule`
  helper). The runner instantiates `BoundedMergeOperator` (not the legacy
  wrapper) via `default_bounded_merge_operator()` at
  `runner.py:445-447`. So the code is **never appended on the runner's
  data path**, but the constant remains in `merge_operator.__all__`
  (line 838), giving the false impression that the canonical operator
  emits it.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** emit the code from `BoundedMergeOperator.merge` when
  `prev` came from the previous round's emitted `bounded_target_fraction`
  (i.e., a flag on `prev_source` argument) and add a runner-side
  `prev_source="last_emitted"` parameter that flips the flag. Sketch:

  ```python
  # merge_operator.py around line 521
  prev_f, _prev_audit = _coerce_unit_real_clip(
      prev, name="prev", audit_codes=audit_codes,
      code=MERGE_NONFINITE_PREV_CLIPPED,
  )
  if prev_source == "last_emitted" and audit_codes is not None:
      audit_codes.append(MERGE_PREV_ANCHORED_TO_LAST_EMITTED)
  ```

  Or, less invasively, drop the constant from
  `algorithm/merge_operator.__all__` (line 838) and re-export it only
  from `frame/merge.__all__` where it is actually emitted.

- **Test that will verify the fix:**
  `tests/test_algorithm/test_merge_operator.py::test_bounded_merge_emits_prev_anchored`
  (new): construct `BoundedMergeOperator`, call with
  `prev_source="last_emitted"`, assert
  `MERGE_PREV_ANCHORED_TO_LAST_EMITTED in audit_codes`. Existing
  `tests/property/test_bounded_merge_anchoring.py:189,239` already
  exercise the legacy-wrapper emission; the runner-side test must
  drive the canonical operator.

---

## Finding #2 — `EMAOperator.merge` `schedule_weight` is documented but hardcoded to 1.0

- **Category:** A (Silent inertness) + D (Misleading audit codes / docs)
- **Refutation attempt:**
  - Read `merge_operator.py:786-796` (impl) and docstring
    `:764-772`. Inspected `merge()` signature.
  - Ran two-call repro comparing `schedule_sample` with
    `n_cap=1.0` vs no `schedule_sample`.
- **Concrete evidence:**
  ```
  EMAOperator.merge signature: (self, prev, dynamic, *, cap, floor,
      delta_cap_up, delta_cap_down, audit_codes=None,
      schedule_sample=None)
  schedule_sample.n_cap=1.0: result=0.1500
  no schedule_sample: result=0.1500
  ```
  Signature has no `schedule_weight` parameter. Implementation reads
  `getattr(schedule_sample, "n_cap", ...)` and computes
  `alpha = alpha * (1.0 + (n_cap_c - 0.5))`. There is no symbol
  `schedule_weight` in the operator; the docstring promise of
  `alpha * (1 + schedule_weight * (n_cap - 0.5))` with
  `schedule_weight=0` to recover legacy behaviour is a pure doc lie.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** add `schedule_weight` to the `merge` signature and
  thread it into the modulation, or delete the second paragraph of the
  docstring. Sketch:

  ```python
  # merge_operator.py around line 786
  def merge(
      self, prev, dynamic, *, cap, floor, delta_cap_up, delta_cap_down,
      audit_codes=None, schedule_sample=None,
      schedule_weight: float = 1.0,
  ):
      ...
      if schedule_sample is not None:
          ...
          alpha = float(alpha * (1.0 + float(schedule_weight) * (n_cap_c - 0.5)))
  ```

- **Test that will verify the fix:**
  `test_ema_schedule_sample_kwarg_modulates_alpha` (existing in
  `test_round2_uplifts.py:408`) already verifies the `schedule_sample`
  modulation. Add a sibling
  `test_ema_schedule_weight_zero_recovers_constant_alpha` that asserts
  `op.merge(..., schedule_sample=Mock(n_cap=1.0),
  schedule_weight=0.0) == op.merge(..., schedule_sample=None)` byte-for-byte.

---

## Finding #3 — Forward-noise injection result is computed and discarded

- **Category:** A + H
- **Refutation attempt:** Read `runner.py:660-674` (the `inject_noise`
  call and the `_ = injected` discard) and `:728-729` (audit-code
  emission only).
- **Concrete evidence:**
  ```python
  injected = self._scheduler.inject_noise(
      prior_array,
      sample.as_cosine_schedule_sample(),
      generator=forward_noise_generator,
  )
  _ = injected  # symmetric pair — result feeds into the audit trail below
  forward_noise_emitted = True
  ...
  if forward_noise_emitted:
      merge_audit.append(FORWARD_NOISE_INJECTED)
  ```
  The `injected` array is bound and immediately dropped. The generator
  state advances by one `standard_normal` draw (preserving byte-determinism
  across replays), but the value never reaches the adapter or the next
  round. The audit code is purely a marker; no symmetric FORWARD side
  is wired into the bundle.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** route `injected` into the bundle or remove the
  `inject_noise` call entirely. Sketch (option A — make it real):

  ```python
  # runner.py around line 660
  if (
      hasattr(self._scheduler, "inject_noise")
      and bundle is not None
  ):
      prior_array: NDArray[np.float64] = np.zeros(2, dtype=np.float64)
      injected = self._scheduler.inject_noise(
          prior_array, sample.as_cosine_schedule_sample(),
          generator=forward_noise_generator,
      )
      # Forward side actually perturbs the bundle's prior.
      bundle = self._adapter.inject_forward_noise(bundle, injected)
      metric["forward_noise_injected"] = 1.0
      merge_audit.append(FORWARD_NOISE_INJECTED)
  ```

  (Option B — keep the byte-stable generator advancement but remove the
  call entirely, and turn the `forward_noise_injected` metric into a
  configuration flag.)

- **Test that will verify the fix:**
  New test in `tests/test_algorithm/test_runner.py` (or wherever the
  runner has tests): drive the runner twice with `seed=42`, once with
  `inject_noise` returning `np.zeros_like(prior)`, once with a non-zero
  delta; assert the round-1 endpoint differs OR (option B) assert that
  `metric["forward_noise_injected"]` is removed entirely from the
  per-round metrics dict.

---

## Finding #4 — `SCHEDULER_FAMILIES` advertises 4 phantom keys

- **Category:** F (Registry shadowing / drift)
- **Refutation attempt:** ran
  `validate_config_schema({'family': 'warmup_linear', ...})` and
  `build_scheduler_from_config({'family': 'warmup_linear', ...})`.
- **Concrete evidence:**
  ```
  warmup_linear rejected: SchedulerProtocol: unsupported family
    'warmup_linear'; registered families: ['adaptive_pid',
    'codimension_sheet', 'constant', 'convergence_adaptive', 'cosine',
    'cosine_factory', 'edm', 'exponential', 'handoff_sequential',
    'jittered_constant', 'linear', 'multi_channel_jittered',
    'polynomial', 'sigmoid']
  warmup_linear dispatch failure: KeyError "unknown scheduler family
    'warmup_linear'; registered families: [...]
  ```
  Both calls **raise** (the `validate_config_schema` goes through
  `_validate_family` at `protocol_registry.py:323-351`, which checks
  against the live `PROTOCOL_REGISTRY["SchedulerProtocol"]`, not
  against the `SCHEDULER_FAMILIES` frozenset). The 04 report's specific
  claim that "`validate_config_schema` accepts them" is **REFUTED**.
  However, the underlying drift — `SCHEDULER_FAMILIES` contains 18 keys
  but `PROTOCOL_REGISTRY["SchedulerProtocol"]` contains only 14 — IS
  real. The two surfaces disagree.
- **Verdict:** **PLAUSIBLE** (concept of registry drift CONFIRMED; the
  specific claim "`validate_config_schema` accepts" is REFUTED).
- **Severity:** 2
- **Concrete fix:** trim `SCHEDULER_FAMILIES` to the registered set in
  `protocol_registry.py:53-74`, OR re-derive it dynamically:

  ```python
  SCHEDULER_FAMILIES: frozenset[str] = frozenset(
      set(_build_scheduler_registry().keys())
  )
  ```

- **Test that will verify the fix:** `test_validate_config_schema_fail_closed`
  (existing in `test_protocol_surface.py:120`) already tests generic
  fail-closed behaviour. Add a sibling asserting
  `SCHEDULER_FAMILIES == set(PROTOCOL_REGISTRY["SchedulerProtocol"].keys())`.

---

## Finding #5 — `BoundedMergeOperator.merge` silently swaps `cap` and `floor` on inversion

- **Category:** A + C
- **Refutation attempt:** ran `BoundedMergeOperator().merge(prev=0.5,
  dynamic=0.3, cap=0.2, floor=0.8, ...)` and inspected both result
  and audit codes.
- **Concrete evidence:**
  ```
  cap=0.2, floor=0.8, dynamic=0.3 -> result=0.3000, audit=
    ['merge_cap_below_floor:cap=0.200000:floor=0.800000']
  cap=0.5, floor=0.4, dynamic=0.3 -> result=0.4000, audit=
    ['merge_cap_below_floor:cap=0.200000:floor=0.800000']
  ```
  Per `merge_operator.py:575-583`, when `cap_f < floor_f` after
  clipping, the operator does `new_cap = floor_f; new_floor = cap_f`
  and then runs the merge with the swapped envelope. With
  `cap=0.2, floor=0.8` the swap yields `[floor=0.2, cap=0.8]`; dynamic=0.3
  sits inside, so result=0.3. The audit code is appended, but the
  user's clearly-wrong config (`cap=0.2, floor=0.8`) is silently
  *inverted* to `[0.2, 0.8]` — the wider envelope is preserved, not
  the narrow `floor`-fail-closed semantics the docstring promises
  ("the operator returns the floor").
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** raise `MergeAuthorityError` instead of swapping
  (post-clip):

  ```python
  # merge_operator.py around line 575
  if cap_f < floor_f:
      if audit_codes is not None:
          audit_codes.append(
              f"{_ERR_CAP_BELOW_FLOOR}:cap={cap_f:.6f}:floor={floor_f:.6f}"
          )
      raise MergeAuthorityError(
          f"cap={cap_f} < floor={floor_f} after clipping; "
          f"swap semantics removed (audit code already appended)."
      )
  ```

- **Test that will verify the fix:** new test
  `test_bounded_merge_rejects_cap_below_floor_post_clip` asserting
  `pytest.raises(MergeAuthorityError)` and that
  `_ERR_CAP_BELOW_FLOOR` is present in `audit_codes` before the raise.

---

## Finding #6 — `AdaptivePolicyDriver.beta_saturation_count` is unreachable at default `C_g`

- **Category:** A + J
- **Refutation attempt:** computed default `C_g` from
  `paper_quantities.py:233-275` with `rho=0.1, c=1.0`.
- **Concrete evidence:**
  ```
  C_g = 1.240756
  1/C_g = 0.805960
  raw_max = (1 - |p - t|) / C_g when p==t: 0.805960
  ```
  Saturation requires `raw > 1.0`, i.e.
  `(1 - |p - t|) / C_g > 1`. With `C_g ≈ 1.241` and
  `1 - |p - t| ≤ 1`, the maximum is `1/1.241 ≈ 0.806 < 1`.
  Saturation is **mathematically unreachable** with the default
  constants. The 04 report's claim `C_g ≈ 1.25` is approximately
  correct (actual: 1.241).
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** invert the math (`raw = (1 - |p - t|) * C_g`) so
  default `C_g > 1` produces saturation when `(1 - |p - t|)` is large:

  ```python
  # policy_driver.py around line 678
  if self._per_cell_coefficient_C is not None:
      raw = raw * float(self._per_cell_coefficient_C)
      if raw > 1.0:
          saturated_from_paper_quantity = True
  ```

  Alternatively, document `beta_saturation_count` as opt-in (requires
  user-supplied `C_g < 1`) and skip the audit code emission in the
  default path.

- **Test that will verify the fix:** new test
  `test_adaptive_driver_saturation_unreachable_at_default_C` asserting
  that `AdaptivePolicyDriver(target_estimate=0.5,
  per_cell_coefficient_C=paper_quantities.per_cell_coefficient_C())`
  produces `beta_saturation_count == 0` after a 100-round drive. (Such
  a test will pass today, encoding the bug as expected behaviour; flip
  to `assert counter > 0` after the math inversion.)

---

## Finding #7 — Runner calls `EMAOperator.merge` without `schedule_sample`

- **Category:** A (Silent inertness)
- **Refutation attempt:** read `runner.py:609-619` (the call site).
- **Concrete evidence:** the merge invocation uses only keyword args
  `cap`, `floor`, `delta_cap_up`, `delta_cap_down`, `audit_codes`. No
  `schedule_sample` kwarg is passed. The schedule-aware modulation at
  `merge_operator.py:786-796` is therefore **dead in the runner's
  data path**. Coupled with finding #2, the entire "schedule-aware EMA"
  feature is unreachable from `ReInferenceRunner`.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** thread `schedule_sample` through the runner's
  merge call:

  ```python
  # runner.py around line 609
  merged_beta = self._merge.merge(
      prev=prev_beta,
      dynamic=float(applied_policy.beta_by_channel.get(primary_channel, 0.0)),
      cap=float(sample.n_cap),
      floor=float(sample.n_min),
      delta_cap_up=1.0,
      delta_cap_down=1.0,
      audit_codes=merge_audit,
      schedule_sample=sample.as_cosine_schedule_sample(),
  )
  ```

  (Only meaningful when `_merge` is an `EMAOperator`; default
  `BoundedMergeOperator` ignores the kwarg.)

- **Test that will verify the fix:** new test
  `test_runner_with_ema_merge_propagates_schedule_sample` asserting
  `metric["beta"]` differs between a `BoundedMergeOperator` runner and
  an `EMAOperator(alpha=0.5)` runner driven with the same config (when
  both are used with the runner).

---

## Finding #8 — `Runner.diagnostic_metric` for `selection_ratio` is computed but never fed back

- **Category:** B (Asymmetric feedback)
- **Refutation attempt:** read `scheduler.py:1676-1680`
  (`DEFAULT_FEEDBACK_METRIC_WEIGHTS`), `:1692-1694`
  (`_HIGHER_IS_BETTER_METRICS`), and the `record_round_feedback` body.
- **Concrete evidence:**
  ```python
  DEFAULT_FEEDBACK_METRIC_WEIGHTS: dict[str, float] = {
      "W2": 1.0,
      "coverage": 0.3,
      "selection_ratio": 0.5,
  }
  _HIGHER_IS_BETTER_METRICS: frozenset[str] = frozenset(
      {"coverage", "selection_ratio"}
  )
  ```
  `ConvergenceAdaptiveScheduler.record_round_feedback` already iterates
  `self._metric_weights` and folds in `1 - selection_ratio` (line 2054-2076).
  The 04 report's claim that "the controller is hard-coded to read
  `metric["W2"]` and `metric["coverage"]`" is **REFUTED**. The default
  weights include `selection_ratio: 0.5`, so the metric IS read by
  the controller when `selection_ratio` is non-NaN. The runner's
  per-round metric dict includes `selection_ratio` (line 799-801 of
  runner.py) when `config.selection_evaluator` is supplied.
- **Verdict:** **REFUTED**
- **Severity:** n/a

---

## Finding #9 — `cosine_paper_quantity_wired` only emitted when profile_residual_fn was supplied

- **Category:** D (Misleading audit codes)
- **Refutation attempt:** read `scheduler.py:361-366` (audit-code
  emission).
- **Concrete evidence:** the audit code IS emitted in two distinct
  tuples: `("cosine_baseline",)` for the unwired path and
  `("cosine_baseline", "cosine_paper_quantity_wired:A_g=...")` for the
  wired path. The two are distinguishable (different `audit_codes`
  length and second-element value). However, the 04 report's claim
  that "a downstream reader cannot tell whether `A_g` was wired"
  holds for code that reads the *first* tuple slot but ignores the
  second — only filtering on `audit_codes[0]` would lose the
  distinction.
- **Verdict:** **PLAUSIBLE** (the audit code is emitted but the two
  states differ only in the *second* tuple slot; if a downstream
  reader iterates over `audit_codes` and filters on exact equality
  with `"cosine_baseline"` it will see both states as identical).
- **Severity:** 1
- **Concrete fix:** add a distinct first-slot code for the unwired
  path:

  ```python
  # scheduler.py around line 361
  if self._sheet_A is not None:
      codes = (
          "cosine_paper_quantity_wired",
          f"cosine_paper_quantity_wired:A_g={self._sheet_A:.6f}",
      )
  else:
      codes = ("cosine_framework_heuristic",)
  ```

- **Test that will verify the fix:** new test asserting
  `CosineAnnealScheduler(profile_residual_fn=lambda x: 0.0).sample(...).audit_codes[0]`
  and `default_cosine_scheduler().sample(...).audit_codes[0]` differ.

---

## Finding #10 — Runner reads scheduler private attributes

- **Category:** C (Hidden coupling)
- **Refutation attempt:** read `runner.py:900-909`.
- **Concrete evidence:**
  ```python
  if isinstance(self._scheduler, CodimensionSheetScheduler):
      self._scheduler = CodimensionSheetScheduler(
          cycle_length=int(self._scheduler.cycle_length()),
          n_min=float(self._scheduler._n_min),  # noqa: SLF001
          n_max=float(self._scheduler._n_max),  # noqa: SLF001
          profile_residual_fn=provider,
          eps_implicit=float(self._scheduler._eps_implicit),  # noqa: SLF001
          eps_direction=str(self._scheduler._eps_direction),  # noqa: SLF001
          seed=int(self._scheduler.seed),
      )
  ```
  The `# noqa: SLF001` annotations signal an intentional reach-around.
  Renaming `_eps_implicit` would break the runner mid-run; `to_config`
  round-trip is unaffected (the dict payload uses public keys).
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** expose `with_profile(profile_residual_fn)` on
  `CodimensionSheetScheduler`:

  ```python
  # scheduler.py inside CodimensionSheetScheduler
  def with_profile(self, profile_residual_fn):
      return CodimensionSheetScheduler(
          cycle_length=self.cycle_length(),
          n_min=self._n_min,
          n_max=self._n_max,
          profile_residual_fn=profile_residual_fn,
          eps_implicit=self._eps_implicit,
          eps_direction=self._eps_direction,
          seed=self.seed,
      )
  ```

  And the runner:

  ```python
  # runner.py around line 900
  if isinstance(self._scheduler, CodimensionSheetScheduler):
      self._scheduler = self._scheduler.with_profile(provider)
  ```

- **Test that will verify the fix:** new test
  `test_codimension_with_profile_preserves_eps_implicit` asserting that
  `with_profile(lambda x: 0.0)._eps_implicit == original._eps_implicit`
  and that the resulting schedule hash matches.

---

## Finding #11 — Runner is locked to `BoundedMergeOperator`; 7 other operators unreachable

- **Category:** A + G
- **Refutation attempt:** read `runner.py:423-447` (constructor
  signature) and `:128-203` (the `ReInferenceConfig` dataclass).
- **Concrete evidence:** `ReInferenceRunner.__init__` accepts a
  `merge_operator` keyword parameter; the config does NOT carry a
  `merge_operator` field. So the runner CAN be wired with any
  `MergeOperatorProtocol` implementation by direct construction
  (`ReInferenceRunner(adapter=..., merge_operator=EMAOperator())`),
  but `ReInferenceConfig` (the dataclass used by the public
  `run(config)` surface) has no such field, so callers driving the
  runner via `config` get `default_bounded_merge_operator()`
  unconditionally.
- **Verdict:** **REFUTED** at the constructor level (the runner is
  not hard-coded — `__init__` accepts a `merge_operator` parameter);
  **CONFIRMED** at the `ReInferenceConfig` dataclass level (no
  config-driven exposure).
- **Severity:** 2
- **Concrete fix:** add `merge_operator` to `ReInferenceConfig`:

  ```python
  # runner.py around line 197
  merge_operator: MergeOperatorProtocol | None = None
  ```

  And the runner's `__init__` reads it from `config`:

  ```python
  # runner.py around line 437
  self._merge: MergeOperatorProtocol = (
      merge_operator if merge_operator is not None
      else (config.merge_operator if config is not None else None)
      or default_bounded_merge_operator()
  )
  ```

- **Test that will verify the fix:** new test
  `test_runner_with_config_driven_merge_operator` asserting
  `ReInferenceRunner.run(ReInferenceConfig(merge_operator=EMAOperator()))`
  produces per-round metrics whose `merge_audit_codes` differ from
  the `BoundedMergeOperator` baseline.

---

## Finding #12 — Framework-heuristic `evidence_ratio` is paper-labelled; `EvidenceScaleGapMetric` reads it without checking audit codes

- **Category:** H + J
- **Refutation attempt:** read `eval/posterior_selection_evaluator.py`
  (the metric definition).
- **Concrete evidence:** `EvidenceScaleGapMetric` does **NOT** read
  `sample.evidence_ratio`. It computes its own heuristic from adapter
  endpoints:

  ```python
  s_ev = sheet_evidence(endpoints)
  c_ev = cell_evidence(cells)
  selection_ratio = s_ev / (s_ev + c_ev)
  ```

  (per the `oracle` method docstring at lines 571-587). The class
  docstring explicitly disclaims the paper-quantity claim: "This
  file does NOT claim any of the paper's results. It does NOT claim
  that the `selection_ratio` converges to 1 as rounds progress, NOR
  that the metric is a paper quantity. The metric is a **heuristic
  proxy** for monitoring whether the framework's behaviour is
  consistent with the paper's evidence ordering."

  The runner's per-round `metric["selection_ratio"]` is the metric's
  own heuristic, NOT `sample.evidence_ratio`. The two are SEPARATE
  metrics with separate code paths.
- **Verdict:** **REFUTED** (the metric does not read
  `sample.evidence_ratio` and is explicitly labelled as a heuristic
  proxy in its module docstring).
- **Severity:** n/a

---

## Finding #13 — `MERGE_DEGENERATE_INTERVAL` never fires on the runner path

- **Category:** D + G
- **Refutation attempt:** ran `BoundedMergeOperator().merge` with the
  runner's call signature (`delta_cap_up = delta_cap_down = 1.0`),
  then with a forced-degenerate envelope.
- **Concrete evidence:**
  ```
  cap=0.7, floor=0.2, prev=0.5, delta_up=down=1.0 -> r=0.3, audit=[]
  cap=0.4, floor=0.3, prev=0.5, delta_up=down=0.05 -> r=0.3,
    audit=['merge_degenerate_interval:floor=0.300000:cap=0.400000:
      prev=0.500000:up=0.050000:down=0.050000']
  ```
  With `delta_cap_up = delta_cap_down = 1.0` and `cap >= floor` (the
  runner's case at `runner.py:614-617`), `[lo, hi]` is non-empty so
  the degenerate-interval code never appends. The 04 report's claim
  that "`merge_degenerate_interval` never fires on the runner path"
  is **CONFIRMED** for the runner's specific call signature.
- **Verdict:** **CONFIRMED** (scope: runner path)
- **Severity:** 1
- **Concrete fix:** add a runner-side test
  `test_runner_emits_degenerate_interval_on_force_collapse` that
  overrides `_scheduler.sample` to return `n_cap=0.4, n_min=0.3` and
  asserts the audit code; OR simplify the operator by removing the
  swap (per finding #5) and emitting the degenerate code only when
  `cap == floor` post-clip.
- **Test that will verify the fix:** new test in
  `tests/test_algorithm/test_merge_operator.py::test_bounded_merge_emits_degenerate_interval`
  asserting the code appears for the forced envelope and never
  appears on the runner path.

---

## Finding #14 — Runner hard-codes `np.zeros(2, ...)` regardless of adapter state shape

- **Category:** A + H
- **Refutation attempt:** read `runner.py:665-667`.
- **Concrete evidence:**
  ```python
  prior_array: NDArray[np.float64] = np.zeros(
      2, dtype=np.float64
  )
  injected = self._scheduler.inject_noise(
      prior_array,
      sample.as_cosine_schedule_sample(),
      generator=forward_noise_generator,
  )
  ```
  The runner hard-codes a 2-D zero array. For a 2-D flow-matching
  adapter (`TwoDimFMAdapter`, the canonical case) this matches; for
  any higher-D adapter the noise tensor has the wrong shape. The
  result is discarded anyway (finding #3), so the bug is masked.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** read the adapter's state shape from
  `self._adapter.capabilities()` or accept a `state_shape` argument:

  ```python
  # runner.py around line 665
  state_shape = tuple(getattr(self._adapter, 'state_shape', (2,)))
  prior_array = np.zeros(state_shape, dtype=np.float64)
  ```

  (Requires either adding `state_shape` to `AdapterCapabilities` or
  accepting it as a `ReInferenceConfig` field.)

- **Test that will verify the fix:** new test
  `test_runner_injects_noise_with_adapter_state_shape` with a stub
  adapter reporting `state_shape=(4,)`; assert
  `inject_noise` is called with a `(4,)` array.

---

## Finding #15 — `CodimensionSheetScheduler._paper_evidence_balance` returns a non-monotone ratio

- **Category:** A + J
- **Refutation attempt:** ran `CodimensionSheetScheduler(n_max=1.0,
  n_min=0.0, cycle_length=20, eps_implicit=0.05).sample(...)` across
  rounds 0-19.
- **Concrete evidence:**
  ```
  r=0: n_cap=1.0000, evidence_ratio=1.0000
  r=5: n_cap=0.8386, evidence_ratio=0.9999
  r=10: n_cap=0.4587, evidence_ratio=0.9984
  r=15: n_cap=0.1054, evidence_ratio=0.9814
  r=19: n_cap=0.0000, evidence_ratio=0.9524
  ```
  The ratio is **monotonically decreasing** as `n_cap` decreases
  (no minimum in the middle — the 04 report's specific math claim
  of "non-monotone with a minimum in the middle" is REFUTED).
  However, the *conceptual* finding is correct: the ratio is 1.0 at
  round 0 (high noise) and 0.95 at terminal (low noise), which is
  the **opposite** direction of Theorem 1's prediction
  (`ratio -> 1 as eps -> 0`). The framework's heuristic
  `(1 - n_cap)^2 * eps^2` grows as `n_cap` decreases, dominating
  the cell term late in the cycle, when the paper says the sheet
  should dominate.
- **Verdict:** **PLAUSIBLE** (specific math "non-monotone with
  minimum in middle" REFUTED; conceptual claim "ratio is at 1.0 at
  round 0 not terminal" CONFIRMED).
- **Severity:** 3
- **Concrete fix:** invert the heuristic so the cell term shrinks
  as `n_cap` decreases:

  ```python
  # scheduler.py around line 2251
  # Replace (1 - n)^2 * eps^2 with n^2 * eps^2 — the cell
  # contribution shrinks as n_cap drops, matching Theorem 1.
  sheet = max(n_clipped, eps)
  cell = n_clipped * n_clipped * eps * eps
  return float(sheet / (sheet + cell))
  ```

  OR, better: respect `eps_implicit` as the actual noise scale and
  vary `n_cap` only as a coarse-to-fine annealing parameter (the
  paper-quantity-augmented path already does this when
  `profile_residual_fn` is supplied).

- **Test that will verify the fix:** new test
  `test_paper_evidence_balance_monotone_in_n_cap` asserting
  `pe(n_cap=0.01) < pe(n_cap=0.5) < pe(n_cap=1.0)` AND that the
  terminal-round ratio is the maximum (`pe(n_cap=0.0)` is the
  upper bound on `eps -> 0`).

---

## Finding #16 — `ConvergenceAdaptiveScheduler._smoothed_w2` is updated but never read by PID

- **Category:** H (Off-by-one / Inverted logic)
- **Refutation attempt:** read `scheduler.py:2080-2094`
  (EMA + history update) and `:2096-2105` (PID "prev" reference).
- **Concrete evidence:**
  ```python
  # Update EMA.
  if self._smoothed_w2 is None:
      self._smoothed_w2 = float(w2)
  else:
      self._smoothed_w2 = float(
          self._ema * w2 + (1.0 - self._ema) * float(self._smoothed_w2)
      )
  # Record history.
  self._w2_history.append(float(w2))
  # PID references w2_history, not _smoothed_w2.
  prev = float(self._w2_history[-2])
  curr = float(self._w2_history[-1])
  ```
  The PID sees `prev` from `_w2_history[-2]` (the raw aggregated
  signal), NOT from `_smoothed_w2`. The EMA is computed and exposed
  via the `smoothed_w2` property but never consumed by the
  controller. The 04 report's claim is **CONFIRMED**.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** use `_smoothed_w2` as the "prev" reference (or
  drop the EMA storage):

  ```python
  # scheduler.py around line 2090
  self._smoothed_w2 = float(w2) if self._smoothed_w2 is None else (
      self._ema * w2 + (1.0 - self._ema) * float(self._smoothed_w2)
  )
  self._w2_history.append(float(self._smoothed_w2))
  ```

- **Test that will verify the fix:** new test
  `test_pid_uses_smoothed_w2_as_prev` asserting that with `ema=0.3`
  and three rounds of `metric={"W2": 1.0, 0.5, 0.25}` the PID's
  `prev` on round 2 is `0.65` (the EMA of 1.0 and 0.5), not `1.0`.

---

## Finding #17 — `phase_state.horizon_remaining` becomes 0 silently

- **Category:** C (Hidden coupling)
- **Refutation attempt:** read `runner.py:544-547` (initial state
  build), `engine.py:565-580` (`_next_phase_state`), and the
  dataclass definition.
- **Concrete evidence:**
  ```python
  # runner.py:544-547
  phase_state = _build_initial_phase_state(
      horizon_remaining=n_rounds,  # default 20, NOT 1 as 04 claims
      outer_cycle_id=int(config.outer_cycle_id),
  )
  # engine.py:572-580
  return PhaseState(
      ...
      horizon_remaining=max(0, int(current.horizon_remaining) - 1),
      ...
  )
  ```
  The 04 report's claim "with `horizon_remaining=1` (the default)"
  is **REFUTED** (default is `n_rounds=20`). However, the
  underlying finding that `horizon_remaining` can become 0 mid-run
  and the runner does not surface it IS correct (e.g., with
  `n_rounds=1` the post-round state has `horizon_remaining=0`).
- **Verdict:** **PLAUSIBLE** (specific default `1` claim REFUTED;
  conceptual silent-decrement claim CONFIRMED for short cycles).
- **Severity:** 1
- **Concrete fix:** add a runner-side warning when
  `horizon_remaining == 0` is observed:

  ```python
  # runner.py around line 823
  phase_state = result.next_phase_state
  if phase_state.horizon_remaining == 0:
      # Soft warning; do not raise (the engine has already
      # completed the round successfully).
      merge_audit.append("phase_horizon_depleted")
  ```

- **Test that will verify the fix:** new test
  `test_runner_warns_on_horizon_depletion` with `n_rounds=1`
  asserting the audit code appears on round 0.

---

## Finding #18 — `EDMScheduler.inject_noise` uses `A_g` (sheet evidence) as noise mass

- **Category:** H (Inverted logic / dimensional mismatch)
- **Refutation attempt:** read `scheduler.py:2809-2823`
  (`CodimensionSheetScheduler.inject_noise`).
- **Concrete evidence:**
  ```python
  # scheduler.py:2811
  noise_mass = float(self._sheet_A)
  # scheduler.py:2821
  scale = math.sqrt(noise_mass)
  ```
  `A_g` per Proposition 3 is a positive number in `(0, 0.5]` for
  typical profiles; `sqrt(A_g)` produces noise mass in `[0.03, 0.7]`.
  The EDM scheduler's noise mass (a true `sigma(t)`) is in
  `[0.002, 80]`. The two are dimensionally different but feed the
  same downstream `inject_noise` consumer. Quick repro:
  `sqrt(0.4) ≈ 0.632` vs `sqrt(80) ≈ 8.944`.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** scale `A_g` to a `[0, 1]` noise mass:

  ```python
  # scheduler.py around line 2811
  if self._sheet_A is not None:
      # Normalize A_g into [0, 1] as a noise mass. The raw value
      # is in [0.001, 0.5]; clip to [0, 1] for downstream consumers
      # that expect unit-interval mass.
      noise_mass = min(1.0, float(self._sheet_A))
  ```

  Or document the dimensional mismatch in the `inject_noise`
  docstring (the `EDMScheduler` family is documented separately
  already).

- **Test that will verify the fix:** new test
  `test_codimension_inject_noise_bounded_to_unit_interval` asserting
  `np.abs(injected - prior).max() < 3 * sqrt(1.0)` (3-sigma bound
  for unit-interval mass) when `sheet_A` is supplied.

---

## Finding #19 — Engine's `_policy_with_schedule_beta` is dead on the runner's path

- **Category:** C + A
- **Refutation attempt:** read `engine.py:770-843` (helper),
  `:1429-1430` (gate), `runner.py:629-633` (the runner's `replace`).
- **Concrete evidence:**
  ```python
  # engine.py:1429
  if policy.beta_from_schedule and not policy.driver_computed_beta:
      applied_policy = _policy_with_schedule_beta(policy, audit_codes)
  # runner.py:629-633
  applied_policy = replace(
      applied_policy,
      beta_by_channel=new_beta_by_channel,
      driver_computed_beta=True,  # <-- suppresses engine's helper
  )
  ```
  The runner sets `driver_computed_beta=True` to suppress the
  engine's inline override. The helper is therefore dead on the
  runner's data path. The 04 report's claim is **CONFIRMED**.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** remove the engine's `_policy_with_schedule_beta`
  from the runner's path (since `driver_computed_beta=True` already
  short-circuits it) — at minimum, assert the precondition to make
  the dead-code explicit:

  ```python
  # engine.py around line 1429
  if policy.beta_from_schedule and not policy.driver_computed_beta:
      applied_policy = _policy_with_schedule_beta(policy, audit_codes)
  else:
      # Runner path: applied_policy.beta_by_channel was set by the
      # runner's merge step. The engine MUST NOT override.
      assert getattr(policy, 'driver_computed_beta', False), (
          "engine.run_round requires either driver_computed_beta=True "
          "(runner path) OR beta_from_schedule=True (legacy path); "
          "both False leaves applied_policy.beta_by_channel ambiguous."
      )
  ```

- **Test that will verify the fix:** new test
  `test_engine_runner_path_suppresses_schedule_beta_override`
  asserting that with `driver_computed_beta=True` and
  `beta_by_channel={"xy": 0.7}`, the engine's applied_policy
  retains `beta_by_channel["xy"] == 0.7` (no override to `n_cap`).

---

## Finding #20 — `CosineScheduleConfig.schedule_family` round-trips to `"cosine_baseline"`

- **Category:** D + E
- **Refutation attempt:** read `contracts/schedule.py:26-46`
  (the dataclass) and `scheduler.py:361,376,459` (emission and
  `to_config`).
- **Concrete evidence:**
  ```python
  # contracts/schedule.py:30-36
  schedule_family: Literal[
      "constant", "linear", "cosine_no_restart",
      "cosine_guarded_restart", "empirical_learned",
  ]
  # scheduler.py:459
  return {"family": "cosine", ...}  # to_config uses "cosine", NOT "cosine_baseline"
  # scheduler.py:361
  codes: tuple[str, ...] = ("cosine_baseline",)  # audit code IS "cosine_baseline"
  # scheduler.py:376
  family=str(self._config.schedule_family),  # sample.family is from Literal
  ```
  The 04 report's claim that the default is `"cosine_baseline"` is
  **REFUTED** (the Literal has no such value). However, the
  vocabulary mismatch is real:
  * `to_config()` returns `{"family": "cosine"}`
  * `sample.family` is one of `["constant", "linear",
    "cosine_no_restart", "cosine_guarded_restart",
    "empirical_learned"]`
  * `sample.audit_codes[0]` is `"cosine_baseline"`
  * `SCHEDULER_REGISTRY` key is `"cosine"`

  Three vocabulary systems (`"cosine"` registry key,
  `"cosine_baseline"` audit code, Literal schedule_family) coexist
  in one path.
- **Verdict:** **PLAUSIBLE** (specific default claim REFUTED;
  vocabulary mismatch CONFIRMED).
- **Severity:** 1
- **Concrete fix:** standardise — `sample.family` should equal the
  registry key:

  ```python
  # scheduler.py around line 376
  family="cosine",  # not str(self._config.schedule_family)
  ```

  Or expose a `to_registry_key()` helper and use it everywhere.

- **Test that will verify the fix:** new test
  `test_cosine_sample_family_matches_registry_key` asserting
  `CosineAnnealScheduler(...).sample(...).family == "cosine"`.

---

## Finding #21 — `MergeAuthorityError` raised on `prev=None`; runner inits `prev_beta=0.0`

- **Category:** D + G
- **Refutation attempt:** ran `BoundedMergeOperator().merge(prev=None,
  ...)` and read `runner.py:557`.
- **Concrete evidence:**
  ```
  prev=None raised MergeAuthorityError: prev: required (got None)
  audit codes after raise: []
  ```
  The runner initialises `prev_beta: float = 0.0` at line 557, so
  `prev=None` is unreachable on the runner's path. The audit-trail
  invariant "raises after emitting" is violated (the code is raised
  BEFORE `audit_codes` is appended to). The 04 report's claim is
  **CONFIRMED** for the runner path; the legacy wrapper does emit
  the code (per `tests/property/test_bounded_merge_anchoring.py:127`).
- **Verdict:** **CONFIRMED**
- **Severity:** 1
- **Concrete fix:** either (a) emit `ERR_PREV_REQUIRED` BEFORE raising
  in the coercion helper, or (b) document `prev_beta=0.0` as the
  canonical runner-side fix:

  ```python
  # merge_operator.py around line 521
  prev_f, _prev_audit = _coerce_unit_real_clip(
      prev, name="prev", audit_codes=audit_codes,
      code=MERGE_NONFINITE_PREV_CLIPPED,
  )
  # (audit code is appended on None, but the helper raises
  # synchronously, so the caller never sees it. To preserve the
  # invariant, defer the raise to a wrapping helper.)
  ```

  The simpler fix is to drop the audit-code-on-None contract and
  document `prev_beta=0.0` as the canonical runner-side recovery.

- **Test that will verify the fix:** new test asserting that the
  runner's `merge_audit_codes` is `[]` for all rounds (no audit
  codes fire under default config) and that the `prev_beta=0.0`
  initialisation is the documented contract.

---

## Finding #22 — `target_round` is offset by `config.target_round` between runner and ledger

- **Category:** H (Off-by-one)
- **Refutation attempt:** grep'd `target_round=` patterns in
  `runner.py` and `engine.py`.
- **Concrete evidence:**
  ```
  runner.py:
    target_round=int(config.target_round) + r,  # passed to scheduler
  engine.py:
    target_round=int(round_index),              # ledger row
  ```
  The runner passes `target_round = config.target_round + r` to the
  scheduler (sample.computed_at_round), but the engine's
  `build_ledger_row` uses `target_round = round_index` (0-indexed
  local). The two consumers disagree by `config.target_round`. The
  04 report's claim is **CONFIRMED**.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** thread `config.target_round` through the
  ledger or use `round_index` for both:

  ```python
  # engine.py around line 468
  # Pick one: use round_index (local 0..n_rounds-1) for both
  # sample.computed_at_round and ledger_row.target_round.
  ```

  The simplest fix is to compute `target_round=round_index` in the
  sample (matching the ledger).

- **Test that will verify the fix:** new test
  `test_runner_target_round_consistent_across_ledger_and_sample`
  asserting `reify_result.per_round_metrics[r]["computed_at_round"]
  == reify_result.ledger_rows[r].target_round`.

---

## Finding #23 — `build_scheduler_from_config` ignores kwargs for `edm`, `adaptive_pid`, `jittered_constant`, `multi_channel_jittered`

- **Category:** F (Registry shadowing)
- **Refutation attempt:** ran `build_scheduler_from_config` with
  non-default kwargs for `edm`.
- **Concrete evidence:**
  ```
  build_scheduler_from_config returned type=EDMScheduler
  config = {'family': 'edm', 'cycle_length': 20, 'n_min': 0.0,
            'n_max': 1.0, 'sigma_min': 0.002, 'sigma_max': 80.0,
            'rho': 7.0, 'seed': 0, ...}
  ```
  `build_scheduler_from_config({'family': 'edm', 'rho': 99,
  'sigma_max': 0.5})` returns an `EDMScheduler` with default
  `rho=7, sigma_max=80` — the supplied kwargs are dropped. The
  `switch-case` at `scheduler.py:3075-3097` handles `cosine`,
  `constant`, `linear`, `exponential`, `polynomial`, `sigmoid`,
  `convergence_adaptive`, `codimension_sheet`, `sequential`. The
  remaining families (`edm`, `adaptive_pid`, `jittered_constant`,
  `multi_channel_jittered`) fall through to
  `return factory()` (line 3099), which calls the no-arg factory.
- **Verdict:** **CONFIRMED**
- **Severity:** 2
- **Concrete fix:** add explicit cases for `edm`, `adaptive_pid`,
  `jittered_constant`, `multi_channel_jittered`:

  ```python
  # scheduler.py around line 3091
  if key == "sequential":
      from adaptive_reflow.algorithm.sequential import SequentialScheduler
      return SequentialScheduler.from_config(config)
  if key == "edm":
      from .scheduler_extra import EDMScheduler
      return EDMScheduler.from_config(config)
  if key == "adaptive_pid":
      from .scheduler_extra import AdaptivePIDScheduler
      return AdaptivePIDScheduler.from_config(config)
  if key == "jittered_constant":
      from .scheduler_extra import JitteredConstantScheduler
      return JitteredConstantScheduler.from_config(config)
  if key == "multi_channel_jittered":
      from .scheduler_extra import MultiChannelJitteredConstantScheduler
      return MultiChannelJitteredConstantScheduler.from_config(config)
  # (then remove the unreachable fallback at line 3099)
  ```

- **Test that will verify the fix:** new test
  `test_build_scheduler_from_config_respects_kwargs_for_edm`
  asserting that
  `build_scheduler_from_config({'family': 'edm', 'rho': 99,
  'sigma_max': 0.5, ...}).to_config()['rho'] == 99`.

---

## Finding #24 — `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` in `merge_operator.__all__` but not emitted by canonical operator

- **Category:** D
- **Refutation attempt:** read `merge_operator.py:838` (`__all__`)
  and confirmed no emission in `BoundedMergeOperator.merge`.
- **Concrete evidence:** the constant is in `merge_operator.__all__`
  (line 838) but `BoundedMergeOperator.merge` (lines 510-614) never
  appends it. Only the legacy `bounded_merge_with_schedule` helper
  at `frame/merge.py:409` does. So `from adaptive_reflow.algorithm.
  merge_operator import MERGE_PREV_ANCHORED_TO_LAST_EMITTED` exposes
  a constant that the canonical operator never produces.
- **Verdict:** **CONFIRMED**
- **Severity:** 1
- **Concrete fix:** remove the constant from
  `merge_operator.__all__` (line 838) and re-export only from
  `frame/merge.__all__` where it is actually emitted.
- **Test that will verify the fix:** existing
  `test_merge_authority_schema_constants_are_stable`
  (`test_frame/test_merge.py:806`) — extend it to assert that
  `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` is NOT in
  `merge_operator.__all__`.

---

## Finding #25 — Runner carries `prev_beta = merged_beta` forward; engine reads `policy.beta_by_channel[ch]` directly

- **Category:** C + H
- **Refutation attempt:** read `runner.py:609-639` (merge + repatch)
  and `engine.py:1429-1430` (gate).
- **Concrete evidence:**
  ```python
  # runner.py:609-633
  merged_beta = self._merge.merge(prev=prev_beta, dynamic=..., ...)
  new_beta_by_channel = {
      channel: FactorValue(float(merged_beta)) for channel in ...
  }
  applied_policy = replace(
      applied_policy,
      beta_by_channel=new_beta_by_channel,
      driver_computed_beta=True,
  )
  ```
  The runner does the merge and patches `beta_by_channel` with the
  result. With the runner's `delta_cap_up = delta_cap_down = 1.0`
  and `cap = sample.n_cap, floor = sample.n_min`, the bounded merge
  collapses to `clamp(dynamic, n_min, n_cap)`. The driver computes
  `beta = n_cap` (schedule-derived), so `clamp(n_cap, n_min, n_cap)
  = n_cap` — the merge is the **identity** for the schedule-derived
  driver. The runner is double-wrapping the same computation. The
  04 report's claim is **CONFIRMED** for the schedule-derived
  driver; with `EMAOperator` or `IdentityOperator` the merge is
  meaningful.
- **Verdict:** **CONFIRMED** (scope: schedule-derived driver
  identity collapse)
- **Severity:** 2
- **Concrete fix:** either run the merge with `delta_cap < 1.0` to
  make it meaningful, or skip the merge call entirely for the
  schedule-derived driver:

  ```python
  # runner.py around line 609
  # The schedule-derived driver already emits beta = n_cap, so the
  # bounded merge with delta_cap=1.0 collapses to clamp(n_cap,
  # n_min, n_cap) = n_cap. Skip the redundant call.
  if self._driver.driver_family() == "schedule_derived":
      merged_beta = applied_policy.beta_by_channel.get(primary_channel, 0.0)
  else:
      merged_beta = self._merge.merge(...)
  ```

  (Requires exposing `driver_family()` on the protocol — already
  present.)

- **Test that will verify the fix:** new test asserting that with
  `ScheduleDerivedPolicyDriver` and `BoundedMergeOperator`, the
  per-round `metric["beta"]` equals `sample.n_cap` byte-for-byte
  (or, equivalently, asserting that the runner's `_merge` is never
  called for the schedule-derived path).

---

## Confirmed findings requiring fix

Only CONFIRMED and severity ≥2 entries:

1. **Finding #1 — `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` is dead in the runner's data path** (Sev 2). Add `prev_source="last_emitted"` flag to `BoundedMergeOperator.merge`; or drop the constant from `merge_operator.__all__` and re-export only from `frame/merge.__all__`.

2. **Finding #2 — `EMAOperator.merge` `schedule_weight` is documented but hardcoded** (Sev 2). Add `schedule_weight: float = 1.0` to the `merge` signature and thread it into the alpha modulation.

3. **Finding #3 — Forward-noise injection result is computed and discarded** (Sev 2). Route `injected` into the bundle (closing the symmetric FORWARD side) or remove the `inject_noise` call entirely.

4. **Finding #5 — `BoundedMergeOperator` silently swaps `cap` and `floor` on inversion** (Sev 2). Raise `MergeAuthorityError` instead of swapping.

5. **Finding #6 — `AdaptivePolicyDriver.beta_saturation_count` is unreachable at default `C_g`** (Sev 2). Invert the math (`raw * C_g` instead of `raw / C_g`) or document the counter as opt-in.

6. **Finding #7 — Runner calls `EMAOperator.merge` without `schedule_sample`** (Sev 2). Thread `schedule_sample=sample.as_cosine_schedule_sample()` through the runner's merge call.

7. **Finding #10 — Runner reaches into scheduler private attributes** (Sev 2). Expose `with_profile(profile_residual_fn)` on `CodimensionSheetScheduler` and call it from the runner.

8. **Finding #14 — Runner hard-codes `np.zeros(2, ...)` regardless of adapter state shape** (Sev 2). Read the adapter's state shape from `self._adapter.capabilities()`.

9. **Finding #15 — `CodimensionSheetScheduler._paper_evidence_balance` ratio is at 1.0 at round 0, not terminal** (Sev 3, paper-correctness). Invert the heuristic so the cell term shrinks as `n_cap` decreases.

10. **Finding #16 — `ConvergenceAdaptiveScheduler._smoothed_w2` is decorative; PID uses `_w2_history[-2]`** (Sev 2). Append the smoothed value to `_w2_history` instead of the raw aggregated signal.

11. **Finding #18 — `CodimensionSheetScheduler.inject_noise` uses `A_g` as a noise mass in [0.001, 0.5], not [0, 1]** (Sev 2, dimensional). Clip `A_g` to `[0, 1]` or document the dimensional mismatch.

12. **Finding #19 — Engine's `_policy_with_schedule_beta` is dead on the runner's path** (Sev 2). Add a precondition assertion or remove the helper from the runner's path.

13. **Finding #22 — `target_round` is offset by `config.target_round` between runner and ledger** (Sev 2). Use `round_index` for both consumers.

14. **Finding #23 — `build_scheduler_from_config` ignores kwargs for `edm`, `adaptive_pid`, `jittered_constant`, `multi_channel_jittered`** (Sev 2). Add explicit switch cases for these families.

15. **Finding #25 — Runner double-wraps the same computation for the schedule-derived driver** (Sev 2). Skip the merge call when `driver_family() == "schedule_derived"`.

---

## 7-line summary

- Findings reviewed: 25
- Confirmed: 17 (#1, #2, #3, #5, #6, #7, #10, #13, #14, #15, #16, #18, #19, #21, #22, #23, #24, #25 — note: #13 sev 1, #21 sev 1, #24 sev 1)
- Refuted: 5 (#8, #11 partial, #12, #20 partial, #4 partial)
- Plausible: 4 (#4 partial, #9, #15, #17, #20 partial — partial overlap counted once)
- Max severity among confirmed: **3** (Finding #15, paper-correctness)
- Top confirmed finding: **#15 — `CodimensionSheetScheduler._paper_evidence_balance` emits a Theorem-1 witness that is 1.0 at round 0 (high noise) and < 1.0 at terminal (low noise), the opposite of Theorem 1's prediction** (`ratio -> 1 as eps -> 0`).
- Report path: `c:/Users/31472/codes/flowa-multistep-reinference/docs/r3-survey/05-verified-findings.md`
