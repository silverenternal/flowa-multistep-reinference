# Wave 287 P — Paper-grounded Scheduler Codepath Audit (READ-ONLY)

**Date:** 2026-09-23
**Branch:** main (no code changes in this phase)
**Scope:** every paper-grounded (paper-quantity-driven / paper-quantity-aware /
adaptive-with-paper-inputs) scheduler in the framework, plus the constant / NFE
families they wrap. Goal: surface algorithm bugs that the user directive
"找paper-grounded 控制器的漏洞做算法和测试用例的加强" calls out.

## Inventory

| # | Class | File:line | Family | Adaptive? |
|---|---|---|---|---|
| 1 | `CodimensionSheetScheduler` | `adaptive_reflow/algorithm/scheduler/adaptive.py:1004` | `codimension_sheet` | no (paper-quantity-driven) |
| 2 | `PaperRatioAdaptiveScheduler` | `adaptive_reflow/algorithm/scheduler/adaptive.py:2035` | `paper_ratio_adaptive_codimension` | yes (fully-integrated) |
| 3 | `ConvergenceAdaptiveScheduler` | `adaptive_reflow/algorithm/scheduler/adaptive.py:117` | `convergence_adaptive_cosine` | yes (W2 PID) |
| 4 | `EvidenceDrivenScheduler` + `_PIDLiteController` | `adaptive_reflow/algorithm/scheduler/evidence_driven.py:140, 248` | `evidence_driven` | yes (evidence PID) |
| 5 | `NFEAwareMemoryScheduler` | `adaptive_reflow/algorithm/scheduler/nfe_aware.py:110` | `nfe_aware_memory` | no (NFE-driven constant) |
| 6 | `FreeTrajScheduler` | `adaptive_reflow/algorithm/scheduler/freetraj.py:63` | `freetraj` | no (trajectory-aware) |
| 7 | `TierAwareCodimensionSheetScheduler` | `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` | `tier_aware_codimension` | wrapper (stateless) |
| 8 | `EDMScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:58` | `edm` | optional sigma_max adaptive |
| 9 | `AdaptivePIDScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:381` | `adaptive_pid_cosine` | yes (full PID) |
| 10 | `JitteredConstantScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:825` | `jittered_constant` | no |
| 11 | `MultiChannelJitteredConstantScheduler` | `adaptive_reflow/algorithm/scheduler_extra.py:999` | `multi_channel_jittered` | no |
| 12 | `MultiChannelJitteredConstantScheduler` | `adaptive_reflow/algorithm/scheduler_r2.py:30` | `multi_channel_jittered` | no (R2 impl) |

Total = **12 scheduler classes audited** across 7 files.

The free functions `_paper_evidence_balance` (adaptive.py:874) and
`adjust_n_cap_for_target_rms` / `paper_quantity_driven_beta`
(adaptive.py:2486, 2576) are audited alongside the classes that consume them.

---

## Severity legend

* **critical** — algorithm contract violation; the documented behaviour is
  silently broken OR a paper-quantity-grounded invariant is violated.
* **major** — silent failure, NaN / inf propagation, unbounded memory
  growth, or a determinism bug that a downstream test would miss.
* **minor** — defensive gap, dead code, API nit, or a robustness issue
  that does not affect the canonical schedule.

---

## Bug inventory (24 findings)

### C-1 — `MultiChannelJitteredConstantScheduler` (r2) silently ignores `per_channel_jitter_std`
- **file:line:** `adaptive_reflow/algorithm/scheduler_r2.py:174-186`
- **class:** silent failure of documented contract
- **severity:** critical
- **reproduction:**
  ```python
  s = MultiChannelJitteredConstantScheduler(
      n_cap=0.5,
      per_channel_jitter_std={"a": 0.01, "b": 0.20},
  )
  sample = s.sample(0, 0, 0)
  # The docstring promises
  #     n_cap_c = n_cap + per_channel_jitter_std[c] * N(0, 1)
  # i.e. channel "a" should be nearly deterministic and channel "b" should
  # have large jitter. Inspection of _regime/audit_codes/record_round_feedback
  # shows the per-channel jitter_scale is **never read** by sample(): the
  # loop (lines 181-185) hard-codes ``self._default_jitter_std`` for every
  # sample. The reported ``n_cap`` is therefore the average of N(0.5,
  # default_jitter_std) samples — independent of the supplied per-channel
  # map.
  ```
- **fix proposal:** diff the loop body against the `scheduler_extra.py:1156`
  reference (which uses `self._per_channel_jitter_std.get(ch, default)`)
  and select the channel key in scheduler_r2.py:
  ```python
  channels = list(self._per_channel.keys()) or ["default"]
  ...
  for ch in channels:
      j = self._per_channel.get(ch, self._default_jitter_std)
      samples.append(float(self._n_cap) + float(j) * float(rng.standard_normal()))
  ```
  …and remove the unused `channel_keys` argument from the constructor (or
  hoist it onto the r2 class so the contract is consistent with
  `scheduler_extra.py`'s implementation). Add a property
  `per_channel_jitter_std` (the r2 file lacks this) so the audit trail can
  surface the wiring.

---

### C-2 — `_paper_evidence_balance` silently falls back to heuristic on all-zero paper quantities
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:952-986`
- **class:** silent fallback that breaks paper-quantity-grounded contract
- **severity:** critical
- **reproduction:**
  ```python
  # profile_residual_fn configured, but the underlying paper_quantities
  # helper returns (A_g = 0, B_g = 0, C_g = 0) for some edge case (e.g.
  # constant-zero profile). Then:
  #     sheet = 0 * eps = 0
  #     cell  = 0 * 0 * eps**2 = 0
  #     denom = 0  ->  recompute fallback runs
  #     sheet = max(n_clipped, eps)     # heuristic
  #     cell  = (1 - n_clipped)**2 * eps**2
  # The scheduler was constructed WITH profile_residual_fn and advertised
  # itself as paper-quantity-grounded (audit code
  # "codimension_paper_quantity_grounded"), but the actual ratio is from
  # the framework heuristic. This silently turns an "all-quantities-zero"
  # profile into a cosine-ramp schedule while the audit trail asserts
  # paper-quantity grounding.
  ```
- **fix proposal:** raise `ValueError` when `sheet_A == packing_B == cell_C
  == 0` *and* the augmented path was selected, instead of silently falling
  back. Add an explicit "all-zero paper quantities" branch that returns
  `0.0` (cell dominance) and emits a distinct audit code
  `codimension_all_zero_paper_quantities`. Update the docstring to reflect
  the new contract.

---

### M-1 — `CodimensionSheetScheduler.__init__` does NOT validate `n_min <= n_max`
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:1168-1175`
- **class:** sign mismatch (silent inversion)
- **severity:** major
- **reproduction:**
  ```python
  s = CodimensionSheetScheduler(cycle_length=2, n_min=0.8, n_max=0.2)
  s.sample(0, 0, 0).n_cap   # >= 0.8
  s.sample(0, 1, 1).n_cap   # <= 0.2
  # The verifier expected n_cap in [0.2, 0.8]; instead the schedule ramps
  # DOWN despite ``n_min > n_max``. The constructor validates each value
  # individually in [0, 1] but not the ordering.
  ```
- **fix proposal:** after the per-value validation add
  ```python
  if float(n_min) > float(n_max):
      raise ValueError(f"n_min ({n_min!r}) must be <= n_max ({n_max!r})")
  ```
  Add a similar guard to `CosineAnnealScheduler`, `TierAware...`, and
  `PaperRatioAdaptiveScheduler` so the whole family shares the contract.

---

### M-2 — `EvidenceDrivenScheduler.record_round_feedback` deduplication of `EVIDENCE_RATIO_MISSING` is broken
- **file:line:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py:790-795` and `581-583`
- **class:** silent failure / audit-code deduplication never triggers
- **severity:** major
- **reproduction:**
  ```python
  s = EvidenceDrivenScheduler(...)
  for r in range(5):
      s.record_round_feedback(r, {})  # no evidence_ratio / selection_ratio
  # Expected: at most one "evidence_ratio_missing" audit code emitted.
  # Actual: append-once check reads self._last_audit_codes, but
  # sample() at lines 581-583 reassigns the field every call:
  #     self._last_audit_codes = codes
  # So at the time of the second record_round_feedback, the field no
  # longer carries the EVIDENCE_RATIO_MISSING code — the membership test
  # always fails and the code is appended every call.
  ```
- **fix proposal:** track the membership on a separate boolean (e.g.
  `self._emitted_ratio_missing: bool = False`) or use a `set` accumulator
  cleared on `reset()`. Toggle the flag in `record_round_feedback` and
  reset it in `reset()`.

---

### M-3 — `EvidenceDrivenScheduler._regime_warnings` accumulates unboundedly
- **file:line:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py:637-638`
- **class:** unbounded memory growth
- **severity:** major
- **reproduction:**
  ```python
  s = EvidenceDrivenScheduler(..., regime_aware=True)
  fake_metrics = {"W2": 100.0}  # every round violates the Lemma 4 ceiling
  for r in range(10_000_000):
      s.record_round_feedback(r, fake_metrics)
  # regime_violation_warnings() returns a tuple of len(10_000_000). No
  # truncation. The list lives on the scheduler instance; reset() only
  # clears regime_warnings at the start of the next run.
  ```
- **fix proposal:** cap the list (e.g. `_REGIME_WARNING_CAP = 1024`) and
  truncate FIFO on overflow, OR emit `set` semantics:
  ```python
  if len(self._regime_warnings) >= _REGIME_WARNING_CAP:
      self._regime_warnings.pop(0)
  self._regime_warnings.append(warning)
  ```

---

### M-4 — `EvidenceDrivenScheduler._last_audit_codes` accumulates unboundedly
- **file:line:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py:822`
- **class:** unbounded memory growth
- **severity:** major
- **reproduction:**
  ```python
  s = EvidenceDrivenScheduler(...)
  for r in range(1_000_000):
      s.record_round_feedback(r, {"W2": 1.0})  # emits one EVIDENCE_PID_ADJUSTED code per call
  # _last_audit_codes grows without bound; sample() at line 581-583 only
  # reassigns, never truncates. last_audit_codes property returns the
  # entire history.
  ```
- **fix proposal:** cap the audit code buffer to the last N entries (e.g.
  `_AUDIT_CODE_BUFFER_LIMIT = 256`), drop FIFO on overflow, document the
  cap. Or fold the codes into a fixed-size `deque(maxlen=N)`.

---

### M-5 — `TierAwareCodimensionSheetScheduler.set_baseline_metrics(None)` returns `(nan, nan)`
- **file:line:** `adaptive_reflow/algorithm/scheduler/tier_aware.py:395-398`
- **class:** broken return-value contract
- **severity:** major
- **reproduction:**
  ```python
  s = TierAwareCodimensionSheetScheduler(...)
  low, high = s.set_baseline_metrics(None)
  # returns (nan, nan). NaN compares unordered; callers using these
  # values to set thresholds, build audits, or compare with prior
  # boundaries all break (low <= x may be False for any x).
  # The docstring says the function returns "(low, high) tier boundaries"
  # but does not document the NaN-tuple case.
  ```
- **fix proposal:** return `(0.0, 1.0)` (the safe fall-through boundaries)
  or raise a documented exception when ``baseline_metrics is None``.
  Document the chosen behavior in the docstring.

---

### M-6 — `EvidenceDrivenScheduler._PIDLiteController` integral anti-windup ±10 may silently saturate PID output
- **file:line:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py:227`
- **class:** saturation may be too aggressive / hidden
- **severity:** major
- **reproduction:**
  ```python
  ctrl = _PIDLiteController(kp=2.0, ki=0.5, max_step=0.1, target_ratio=0.99)
  # observed ratio stays at 0.0 (oracle degenerate)
  for r in range(20):
      delta, _ = ctrl.step(observed_ratio=0.0)
  # Each call: error = 0.99, integral saturates at 10 within 11 calls.
  # raw = kp*err + ki*int = 1.98 + 5 = 6.98 -> saturated to max_step.
  # Caller cannot tell from ``saturated`` (which only signals the
  # per-step clip) whether the integral itself has been pinned — there
  # is no observability surface for integral-windup.
  ```
- **fix proposal:** expose ``pid_integral_for_round(round_in_cycle)``
  (parallel to ``pid_delta_for_round``) and add a debug flag
  `_integral_windup: bool` that flips on when the integral is pinned
  for more than K consecutive rounds. Surface the flag on the
  ``schedule_pid_integral_windup`` audit code when active.

---

### M-7 — `FreeTrajScheduler.sample` does NOT validate `outer_cycle_id` / `target_round` nonnegativity
- **file:line:** `adaptive_reflow/algorithm/scheduler/freetraj.py:168-226`
- **class:** missing input validation (vs sibling schedulers)
- **severity:** major
- **reproduction:**
  ```python
  s = FreeTrajScheduler(CosineScheduleConfig(...))
  s.sample(outer_cycle_id=-7, round_in_cycle=2, target_round=2)
  # NFEAwareMemoryScheduler.sample would raise via _coerce_int_nonneg;
  # FreeTraj silently accepts -7, building an RNG with
  #     default_rng(seed + 2*1009 + (-7)*31)
  # (deterministic but off-protocol). downstream consumers that expect
  # non-negative ids may misbehave (e.g. ledger hashing).
  ```
- **fix proposal:** call `_coerce_int_nonneg(outer_cycle_id, ...)` /
  `_coerce_int_nonneg(target_round, ...)` at the top of `sample()`
  (mirroring `nfe_aware.py:368-369`).

---

### M-8 — `CodimensionSheetScheduler._shift_history` accumulates unboundedly with potentially-inf values
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:1807-1817`
- **class:** unbounded growth + silent NaN/inf propagation
- **severity:** major
- **reproduction:**
  ```python
  s = CodimensionSheetScheduler(...)
  for r in range(1_000_000):
      s.record_round_feedback(
          r,
          metrics={},
          paper_quantities={
              "sheet_A": 1e30,    # arbitrarily large
              "cell_C": 1e-45,    # arbitrarily small
              "packing_B": 1.0,
          },
      )
  # _shift_history.append(sheet_A / max(cell_C * packing_B, 1e-12))
  #   == 1e30 / 1e-12 == 1e42 -> appended to history. shift_history
  # property returns the full tuple; round counts of 10**6 produce a
  # 10**6-tuple of floats. _reset() clears the list, but nothing
  # bounds it during a run. Also: a non-finite sample sneaks through
  # the ``denom > 0`` check silently (denom = inf, ratio = 0/inf = 0,
  # appended).
  ```
- **fix proposal:** apply `math.isfinite` to the appended value and
  cap the buffer with FIFO drop when it exceeds N entries (parity
  with M-3 / M-4). Document the cap on the `shift_history` property.

---

### M-9 — `AdaptivePIDScheduler.__init__` has dead duplicate base-construction branch
- **file:line:** `adaptive_reflow/algorithm/scheduler_extra.py:425-428` and `477-480`
- **class:** dead code / redundant work
- **severity:** major
- **reproduction:** always reach lines 425-428 in the `base is None` path
  (so `self._base` is assigned at line 429). The second `if base is
  None:` at line 477 is unreachable for the documented constructor flow.
  Both branches build a brand-new `ConvergenceAdaptiveScheduler`, so
  removing the second block is safe.
- **fix proposal:** delete the `if base is None:` block at lines 477-480;
  keep only the first construction (lines 425-428).

---

### M-10 — `AdaptivePIDScheduler.record_round_feedback` builds and appends dead arrays (`weighted_history`, `blended_history`)
- **file:line:** `adaptive_reflow/algorithm/scheduler_extra.py:709-710`
- **class:** dead code / wasted allocation
- **severity:** major
- **reproduction:** every call appends `float(weight)` and `v` to two
  no-longer-used lists; the lists grow forever and no consumer reads
  them. Memory-cost per round = O(K).
- **fix proposal:** delete lines 709-710 entirely (the lists are
  vestigial from an earlier blended-signal design).

---

### M-11 — `MultiChannelJitteredConstantScheduler` (scheduler_extra.py) silently drops channels when caller supplies only a subset
- **file:line:** `adaptive_reflow/algorithm/scheduler_extra.py:1083`
- **class:** silent default (channel-set disagreement)
- **severity:** major
- **reproduction:**
  ```python
  s = MultiChannelJitteredConstantScheduler(
      n_cap=0.5,
      per_channel_jitter_std={"a": 0.01},  # subset of "global channel set"
      channel_keys=None,                    # not supplied
  )
  s.channel_keys  # ('a',)  -- only the supplied channels are scheduled
  # Downstream callers that feed a richer channel set fail to match
  # the audit ``f"channels:{','.join(...)}"`` with their expected
  # channel ordering. The docstring is silent on this drop.
  ```
- **fix proposal:** add a `channel_keys` validation step that warns or
  raises when the supplied `per_channel_jitter_std` is a strict subset
  of the caller's expected channel universe. Add a `WARNINGS` list
  and forward the warning to the audit trail.

---

### M-12 — `CodimensionSheetScheduler.should_terminate_round` uses raw history (not EMA-smoothed) and may miss early plateaus
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:1879-1891`
- **class:** early-termination false negatives
- **severity:** major
- **reproduction:**
  ```python
  s = CodimensionSheetScheduler(
      cycle_length=20,
      early_stop_min_rounds=3,
      early_stop_window=2,
      early_stop_plateau_rel_tol=0.005,
      early_stop_min_rounds=3,
  )
  w2_history = [1.0, 0.999, 0.9985, 0.998]   # 0.1% drift, plateau'd
  for i, w in enumerate(w2_history):
      s.record_round_feedback(i, {"W2": w})
  # expected: terminate (the smoothed series is < 0.005 relative change
  # for 2 consecutive steps). actual:
  #   first pair: |0.999 - 1.0| / 1.0 = 0.001 < 0.005 -> ok
  #   second pair: |0.9985 - 0.999| / 0.999 = 0.0005 < 0.005 -> ok
  # returns True. So the *easy* plateau works.
  #
  # Failure mode: noisy oracle — w2_history = [1.0, 0.95, 1.0, 0.999, 0.998]
  # One noisy spike (1.0) injects a 5% jump that poisons every pair the
  # spike touches. The raw-history design is documented in the docstring
  # but the failure mode is not named; an EMA-smoothed variant would
  # have absorbed the spike.
  ```
- **fix proposal:** add a *blended* evaluation that consults the EMA
  series (already computed in `record_round_feedback`) in addition to
  the raw series; terminate if EITHER series is plateaued for
  `early_stop_window` consecutive steps. Add a knob
  `early_stop_history_mode: Literal["raw", "ema", "either"]` so
  callers can opt into a stricter setting.

---

### m-1 — `CodimensionSheetScheduler._paper_evidence_balance` overflows to inf at very large `sheet_A * eps`
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:952-986`
- **class:** overflow guard
- **severity:** minor
- **reproduction:** if `sheet_A = 1e300, eps_per_round = 1e5`, then
  `sheet_f * eps_per_round = 1e305 → 1e308 (near max)`. With
  `cell_C_f * pack_f * eps * eps ≈ 1e-300`, `denom` is dominated by
  sheet → `ratio ≈ 1.0` (correct behavior, but the product is within
  noise of `inf`). No explicit overflow guard.
- **fix proposal:** add a `max(sheet, 1e150)` / `max(cell, 1e150)` clamp
  in the paper-augmented branch. The ratio result is unaffected by the
  clamp (numerically both halves are mapped to 1.0).

---

### m-2 — `CodimensionSheetScheduler._paper_evidence_balance` underflows to 0 for tiny paper quantities
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:952-986`
- **class:** underflow guard
- **severity:** minor
- **reproduction:** `sheet_A = 1e-200, pack_B = 1e-200, cell_C = 1.0,
  eps = 1e-100` → `sheet ≈ 1e-300` (denorm float), `cell ≈ 1e-400`
  (rounds to 0). `denom = sheet ≈ 1e-300`, `ratio = 1.0`. Same failure
  mode as C-2 in spirit (the heuristic fallback should be unreachable
  here because denom > 0).
- **fix proposal:** detect denormal numbers via `math.isdenom` (or
  `0 < abs(x) < sys.float_info.min`) and short-circuit the ratio to
  `1.0` (sheet dominance) with an audit marker.

---

### m-3 — `ConvergenceAdaptiveScheduler._shift` clip uses `if/elif` instead of clamping at the boundary
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:791-795` and `2446-2450`
- **class:** off-by-one at the exact `shift_max` value
- **severity:** minor
- **reproduction:** if `new_shift == self._shift_max`, the `>` test fails,
  the `<` test fails, value is preserved. OK in the trivial case. The
  `elif` would skip if `new_shift > shift_max`, so equality is fine. But
  when `new_shift == nan`, neither `>` nor `<` triggers — `nan` slips
  through unchanged. `nan` cannot come from the closed form because
  `kp * (1 - ratio) - kd * delta` is finite; but a defensive clamp via
  `max(-shift_max, min(shift_max, new_shift if math.isfinite(new_shift)
  else 0.0))` would harden the path.
- **fix proposal:** replace the `if/elif` with
  `new_shift = max(-shift_max, min(shift_max, new_shift))` and guard
  against non-finite values explicitly.

---

### m-4 — `CodimensionSheetScheduler.inject_noise` ignores per-round `n_cap` when `profile_residual_fn` is configured
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:1929-1942`
- **class:** design gap (informational)
- **severity:** minor
- **description:** when `_sheet_A is not None`, the noise mass is
  `max(sheet_A, exterior_gap_e_rho / 4)` for **every** round. This means
  the framework's documented per-round `n_cap` (`ScheduleSample.n_cap`)
  is decoupled from the forward-noise injection. Callers wiring
  paper-quantity quantities may be surprised that varying `n_cap`
  through the cycle does not change forward noise. The behavior is
  documented, but unflagged.
- **fix proposal:** emit an audit marker
  `codimension_inject_noise_decoupled` when `_sheet_A is not None`,
  so downstream consumers see the contract in the audit trail.

---

### m-5 — `MultiChannelJitteredConstantScheduler` (scheduler_r2.py) constructor lacks `channel_keys` validation parity with scheduler_extra.py
- **file:line:** `adaptive_reflow/algorithm/scheduler_r2.py:60-110`
- **class:** API parity gap
- **severity:** minor
- **description:** scheduler_extra.py's variant has `channel_keys` (with
  duplicate-key check, empty-list rejection, sort order guarantee);
  scheduler_r2.py lacks the parameter entirely. Two implementations of
  the same family diverge.
- **fix proposal:** extract a single shared base / canonical class
  (or have one call the other via `from_config`); eliminate the
  duplicate implementation.

---

### m-6 — `TierAwareCodimensionSheetScheduler.record_round_feedback` exception-handler fallback retries with semantically wrong kwarg name
- **file:line:** `adaptive_reflow/algorithm/scheduler/tier_aware.py:580-602`
- **class:** silent contract violation on TypeError
- **severity:** minor
- **reproduction:**
  ```python
  # Inner scheduler is paper_ratio_adaptive (accepts paper_quantities)
  # caller passes both metrics and paper_quantities;
  # try: record_round_feedback(r, metrics=..., paper_quantities=...)
  # try: succeeded (paper_ratio_adaptive accepts it)
  # vs: caller passes only paper_quantities
  # try: kwargs = {round_in_cycle, paper_quantities}
  # try: paper_ratio_adaptive accepts it -> ok
  # vs: caller passes only metrics
  # try: kwargs = {round_in_cycle, metrics=...}
  # try: paper_ratio_adaptive raises TypeError (no metrics kwarg)
  # fallback: paper_quantities=metrics (treats metrics dict as paper_quantities)
  # The fallback maps "metrics dict" into paper-quantity semantics.
  # The keys are the same string family but they are different things
  # (metrics has W2/evidence_ratio keys; paper_quantities has sheet_A keys).
  # The fallback silently corrupts the EMA with W2 values.
  ```
- **fix proposal:** distinguish "I expect metrics" vs "I expect
  paper_quantities" — add a `feedback_kind` flag to the wrapper, or
  refuse the fallback outright (raise a typed exception that the
  runner catches).

---

### m-7 — `CodimensionSheetScheduler.should_terminate_round` default `early_stop_plateau_rel_tol = 0.005` may be too tight for noisy oracles
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:1094`
- **class:** tunability nit (not an algorithm bug)
- **severity:** minor
- **reproduction:** a noisy W2 oracle with σ ≈ 0.01 on a baseline of 1.0
  yields typical relative changes of ~1%, which exceed 0.005, so
  termination never fires. There is no automatic rel-tol widening.
- **fix proposal:** document a recommendation (`>=10 * σ_relative`) and
  add a diagnostic metric
  `schedule_early_stop_relaxable:false/true` when the test fails.

---

### m-8 — `NFEAwareMemoryScheduler._compute_memory_fraction` ratio may be gigantic for huge NFE per round
- **file:line:** `adaptive_reflow/algorithm/scheduler/nfe_aware.py:288-300`
- **class:** saturation behaviour (intended)
- **severity:** minor
- **description:** when `nfe_per_round / threshold` is large (e.g. NFE=500
  with `threshold=10` → ratio=50, ratio²=2500), the closed form
  `m = min(M, M * ratio²)` saturates correctly. No infinite value can
  arise. This is logged here as a confirmed correct saturation path.
- **fix proposal:** none (verification record).

---

### m-9 — `ConvergenceAdaptiveScheduler._safe_fetch_paper_quantity` rejects negative inputs but `Packing_B` may legitimately be signed in some profiles
- **file:line:** `adaptive_reflow/algorithm/scheduler/adaptive.py:817-821`
- **class:** defensive guard (over-restrictive?)
- **severity:** minor
- **description:** paper Lemma 5's `B_g` is documented as non-negative, but
  the helper rejects any negative numeric silently. If a future profile
  ever produces a signed quantity (e.g. for a deviation), it would be
  dropped without diagnostic.
- **fix proposal:** issue a `warnings.warn` (one-shot per scheduler) when
  a negative is dropped, so the audit trail can flag the schema
  mismatch.

---

### m-10 — `AdaptivePIDScheduler.to_config` includes `seed` / `integral_window` / `metric_weights` but `from_config` round-trip may drop `seed`
- **file:line:** `adaptive_reflow/algorithm/scheduler_extra.py:766-812`
- **class:** config round-trip gap
- **severity:** minor
- **reproduction:**
  ```python
  s = AdaptivePIDScheduler(seed=42)
  cfg = s.to_config()  # contains "seed": 42
  rebuilt = AdaptivePIDScheduler.from_config(cfg)
  # rebuilt.seed == 42 only if base was provided; if base is None the
  # inner ConvergenceAdaptiveScheduler is rebuilt without seed
  # propagation.
  ```
- **fix proposal:** thread `seed` through to the inner
  `ConvergenceAdaptiveScheduler` constructor (currently no seed
  forwarding on the inner constructor call), or document the asymmetry.

---

## Cross-cutting findings (design-level)

* **Determinism:** every scheduler returns byte-identical output for the
  same inputs (modulo `np.random.Generator` seed variance in the
  `JitteredConstantScheduler` family, which is itself deterministic
  given `(seed, round_in_cycle, outer_cycle_id)`). The `FreeTraj`
  `np.random.Generator` is not actually invoked (audit
  `substep = amp * sin(2π * progress)` is closed-form), so the
  "stdlib-only" docstring is technically accurate.

* **Thread safety:** none of the schedulers claim thread safety; the
  runner is single-threaded in the codebase. No shared-state bugs found.

* **`reset()` hygiene:** every scheduler has a `reset()` that clears
  accumulated state. The paper-quantity drivers
  (`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`,
  `ConvergenceAdaptiveScheduler`, `TierAwareCodimensionSheetScheduler`)
  all reset to a known empty state. The
  `EvidenceDrivenScheduler._last_audit_codes` is NOT truncated on
  `reset()` (see M-4) but is reassigned to `()` — partial hygiene.

* **Config round-trip (`to_config` ↔ `from_config`):** the
  `CodimensionSheetScheduler.from_config` rebuilds with
  `profile_residual_fn=None`, dropping the callable; the audit trail's
  `profile_signature` is preserved but the actual profile behaviour is
  not. This is documented in the docstring; flagging here for
  completeness.

---

## Severity roll-up

| severity | count | ids |
|---|---:|---|
| critical | 2 | C-1, C-2 |
| major    | 11 | M-1, M-2, M-3, M-4, M-5, M-6, M-7, M-8, M-9, M-10, M-11, M-12 |
| minor    | 10 | m-1, m-2, m-3, m-4, m-5, m-6, m-7, m-8, m-9, m-10 |
| **total** | **24** | |

(Note: `m-8` is a verification record — kept in the inventory to document
that the saturation path was *checked* not just *claimed* correct.)

---

## Test-case priorities (for the user's "算法和测试用例的加强" directive)

1. **C-1** — write a regression that constructs the r2 family with
   non-uniform `per_channel_jitter_std` and asserts the per-channel
   emitted samples have **different** standard deviations (currently
   they all share `default_jitter_std`).
2. **C-2** — write a regression for the all-zero paper-quantity
   fallback path; assert that the scheduler raises (post-fix) or
   emits the audit marker (current behavior).
3. **M-1** — regression for `n_min > n_max`; assert the constructor
   raises.
4. **M-2** — regression for the `EVIDENCE_RATIO_MISSING` dedup
   contract; record N rounds without ratio and assert the audit code
   appears exactly once.
5. **M-3 / M-4** — long-run memory regression (10⁴ rounds).
6. **M-7** — `FreeTraj` sample input-validation regression mirroring
   `NFEAwareMemoryScheduler.sample`.

---

## Invariants preserved

This was a **read-only** audit. No scheduler code was modified. Files
touched: only `docs/audit/wave287-p-scheduler-codepath-audit.md`
(this file).

* D.4 headline regression ledger: untouched.
* `tools/run_sota_cifar_experiment.py`: untouched.
* vendored code under `data/lineageflow_upstream/`, `data/FlowMol3/`,
  `data/Kanzi/`, etc.: untouched.
* ruff / mkdocs gates: untouched.
