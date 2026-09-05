# Algorithm improvement — paper_quantities threading (HIGH-1 + MEDIUM-6 + MEDIUM-8)

**Status:** CLOSED in Wave 38 (commit ff56e55, Wave 38 Agent C WF1) — HIGH-1 + MEDIUM-6 + MEDIUM-8 closed: paper_quantities threaded through 3 sites (CodimensionSheetScheduler.record_round_feedback, SequentialScheduler.record_round_feedback, BatchedTrajectoryRunner.run) + 3 regression tests
**Date:** 2026-09-05
**Priority:** high (3 issues, same class of bug as Wave 30 F-1/F-4/F-5)
**Depends on:** Wave 31 `PaperRatioAdaptiveScheduler` (live)
**Owner:** framework maintainer
**Wave:** Wave 33 (target)
**Goal:** thread the `paper_quantities` keyword argument through the
3 sites that currently silently drop it: `CodimensionSheetScheduler.record_round_feedback`
(HIGH-1), `SequentialScheduler.record_round_feedback` (MEDIUM-6),
`BatchedTrajectoryRunner.run` (MEDIUM-8). Single PR; closes a class of
bugs that mirrors F-1 / F-4 / F-5 from Wave 30.

## Background

Per Wave 32 Agent C (`docs/audit/framework-code-review.md` §1.6 + §1.8 + §1.9):

### HIGH-1: `CodimensionSheetScheduler.record_round_feedback` is a no-op

> Unlike `CosineAnnealScheduler` (which is also a no-op), the codimension
> scheduler is the *adaptive* one in the paper sense (it already computes
> paper-quantity ratios per round). It never accepts feedback, so a
> `runner` that calls `scheduler.record_round_feedback(r, {"W2": w2})`
> for the codimension scheduler does nothing.
>
> **Smallest experiment**: construct a `CodimensionSheetScheduler` with
> `profile_residual_fn=math.sin`, run 2 rounds, call
> `record_round_feedback(0, {"W2": 1.0})`, assert `_shift_history` is
> unchanged (currently no such history exists — no test breaks).
>
> **Fix**: add an override that consumes `paper_quantities` and applies
> a paper-quantity PID (analogous to `PaperRatioAdaptiveScheduler.record_round_feedback`)
> OR remove `record_round_feedback` from the `CodimensionSheetScheduler`
> API surface so runners skip it.

### MEDIUM-6: `SequentialScheduler.record_round_feedback` drops `paper_quantities`

> When a `PaperRatioAdaptiveScheduler` is in slot[1] and a
> `ConvergenceAdaptiveScheduler` in slot[0], the runner's
> `record_round_feedback(r, {"W2": w2}, paper_quantities={...})`
> forwards `{"W2": w2}` to BOTH schedulers but the `paper_quantities`
> kwarg is silently dropped.
>
> **Fix**: mirror the signature — accept `paper_quantities` kwarg
> and forward to slots that accept it.

### MEDIUM-8: `batched_runner.run` drops `paper_quantities`

> `record_round_feedback` is invoked on the scheduler with
> `{"W2": float(w2)}` only — `paper_quantities` is NOT forwarded. The
> runner is the *single chokepoint* for `record_round_feedback` and
> currently drops `paper_quantities` even if the runner config carries
> a `paper_quantities_fn`.
>
> **Fix**: add a `paper_quantities` constructor parameter and forward it.

## Why this matters

This is the same *class* of bug surfaced by F-1 / F-4 / F-5 in Wave 30
but for a different protocol surface. The runner / sequential /
codimension-scheduler surface is the **control loop** for adaptive
re-inference; if `paper_quantities` is dropped, the loop runs without
the paper-quantity signal and the adaptive control regresses to a
heuristic.

## What to do

### Phase A — CodimensionSheetScheduler (HIGH-1)

**Decision**: implement option (a) — consume `paper_quantities` and
apply a paper-quantity PID (analogous to `PaperRatioAdaptiveScheduler`).

1. **Read `adaptive_reflow/algorithm/scheduler/_core.py`** to understand
   the current `CodimensionSheetScheduler.record_round_feedback` method
2. **Add `paper_quantities` kwarg** to `record_round_feedback`
3. **Implement a paper-quantity-driven adjustment**:
   - Compute `ratio = paper_quantities["sheet_A"] / max(paper_quantities["cell_C"] * paper_quantities["packing_B"], eps)`
   - If `ratio > 1`, the sheet dominates → shift `n_cap` down
   - If `ratio < 1`, the cells dominate → shift `n_cap` up
   - Use the same PID-style update as `PaperRatioAdaptiveScheduler`
4. **Add `_shift_history` attribute** to track the PID state

### Phase B — SequentialScheduler (MEDIUM-6)

1. **Read `adaptive_reflow/algorithm/sequential.py`** to understand the
   current `record_round_feedback` signature
2. **Add `paper_quantities` kwarg** to `record_round_feedback`
3. **Forward to each sub-scheduler** that accepts `paper_quantities`:
   ```python
   def record_round_feedback(self, r, metrics, paper_quantities=None):
       for slot in self._slots:
           sub_scheduler = slot.scheduler
           if hasattr(sub_scheduler, "record_round_feedback"):
               # Forward only if the sub-scheduler accepts paper_quantities
               try:
                   sub_scheduler.record_round_feedback(r, metrics, paper_quantities=paper_quantities)
               except TypeError:
                   # Sub-scheduler doesn't accept paper_quantities (legacy)
                   sub_scheduler.record_round_feedback(r, metrics)
   ```
4. **Alternative**: use `inspect.signature` to check which schedulers
   accept `paper_quantities`; only forward to those

### Phase C — BatchedTrajectoryRunner (MEDIUM-8)

1. **Read `adaptive_reflow/algorithm/batched_runner.py`** to find the
   `run` method and the `record_round_feedback` invocation site
2. **Add `paper_quantities` constructor parameter** to `BatchedTrajectoryRunner.__init__`
3. **Forward `paper_quantities` in the `record_round_feedback` call**:
   ```python
   scheduler.record_round_feedback(r, {"W2": float(w2)}, paper_quantities=self._paper_quantities)
   ```
4. **Optionally**: add a `paper_quantities_fn` constructor parameter
   that the runner can call per round to capture the latest values

### Phase D — Regression tests (3 tests)

For each of the 3 fixes, author a regression test:

1. **`tests/test_algorithm/test_codimension_scheduler_paper_quantities.py`**:
   ```python
   def test_codimension_scheduler_consumes_paper_quantities() -> None:
       """HIGH-1 fix: paper_quantities kwarg is consumed; _shift_history grows."""
       scheduler = CodimensionSheetScheduler(profile_residual_fn=math.sin)
       assert scheduler._shift_history == []  # initially empty
       scheduler.record_round_feedback(0, {"W2": 1.0},
                                       paper_quantities={"sheet_A": 0.5, "cell_C": 0.3, "packing_B": 0.4})
       assert len(scheduler._shift_history) == 1
   ```

2. **`tests/test_algorithm/test_sequential_scheduler_paper_quantities.py`**:
   ```python
   def test_sequential_scheduler_forwards_paper_quantities_to_paper_ratio_slot() -> None:
       """MEDIUM-6 fix: paper_quantities is forwarded to PaperRatioAdaptiveScheduler slot."""
       paper_ratio = PaperRatioAdaptiveScheduler(...)
       cosine = CosineAnnealScheduler(...)
       seq = SequentialScheduler(schedulers=[(cosine, 4), (paper_ratio, 4)])
       seq.record_round_feedback(2, {"W2": 0.5},
                                  paper_quantities={"sheet_A": 0.3, "cell_C": 0.2, "packing_B": 0.5})
       assert paper_ratio._shift != 0.0  # consumed the signal
   ```

3. **`tests/test_algorithm/test_batched_runner_paper_quantities.py`**:
   ```python
   def test_batched_runner_forwards_paper_quantities_to_scheduler() -> None:
       """MEDIUM-8 fix: BatchedTrajectoryRunner forwards paper_quantities."""
       scheduler = PaperRatioAdaptiveScheduler(...)
       runner = BatchedTrajectoryRunner(scheduler=scheduler, ...)
       # run() should call scheduler.record_round_feedback with paper_quantities
       runner.run(...)  # this should now update scheduler._shift
       assert scheduler._shift != 0.0
   ```

### Phase E — Verification + docs

1. **Run `pytest tests/test_algorithm/ -v`** — all 3 new tests pass
2. **Run `pytest tests/ -v --timeout=60`** — no regression
3. **Run `python tools/capability_audit.py`** — no gate regression
4. **Update `docs/audit/framework-code-review.md` §1.6 + §1.8 + §1.9** —
   mark HIGH-1 + MEDIUM-6 + MEDIUM-8 as RESOLVED
5. **Update `docs/baseline-audit-report.md`** if applicable

## Files affected

- `adaptive_reflow/algorithm/scheduler/_core.py` (UPDATE; ~30-50 LOC for HIGH-1 fix)
- `adaptive_reflow/algorithm/sequential.py` (UPDATE; ~10 LOC for MEDIUM-6 fix)
- `adaptive_reflow/algorithm/batched_runner.py` (UPDATE; ~10 LOC for MEDIUM-8 fix)
- `tests/test_algorithm/test_codimension_scheduler_paper_quantities.py` (NEW)
- `tests/test_algorithm/test_sequential_scheduler_paper_quantities.py` (NEW)
- `tests/test_algorithm/test_batched_runner_paper_quantities.py` (NEW)
- `docs/audit/framework-code-review.md` (UPDATE; mark 3 issues RESOLVED)
- `docs/baseline-audit-report.md` (UPDATE if applicable)

## Acceptance

- [ ] `CodimensionSheetScheduler.record_round_feedback` consumes `paper_quantities`
- [ ] `SequentialScheduler.record_round_feedback` forwards `paper_quantities`
- [ ] `BatchedTrajectoryRunner.run` forwards `paper_quantities`
- [ ] 3 regression tests pass deterministically
- [ ] `pytest tests/` still passes (no regression)
- [ ] `python tools/capability_audit.py` still passes (no gate regression)
- [ ] `docs/audit/framework-code-review.md` marks 3 issues RESOLVED

## Acceptance gate

Passes if:
1. All 3 sites consume `paper_quantities` (no silent drops)
2. All 3 regression tests pass
3. No regression in the full test suite

## Estimated time

~1-2 hours total (3 small fixes + 3 regression tests).

## Risk

- **MEDIUM**: changing `CodimensionSheetScheduler` semantics could affect
  existing callers that relied on the no-op behaviour
  → **Mitigation**: the new PID is conservative (small shifts per round);
  add a `paper_quantity_pid_enabled` flag (default True) for opt-out
- **LOW**: `SequentialScheduler` might forward to sub-schedulers that
  raise on `paper_quantities=None`
  → **Mitigation**: use `inspect.signature` to only forward where accepted

## Related fix opportunities (within scope of this PR)

Per `docs/audit/framework-code-review.md` §1.6 + §1.8 + §1.9:
- MEDIUM-3: `PaperRatioAdaptiveScheduler.record_round_feedback` has no
  unit test for `paper_quantities={"sheet_A": float("nan")}` — include
  in this PR
- MEDIUM-4: `ConstantScheduler.record_round_feedback` accepts
  `round_in_cycle=0` for cycle_length=1 but rejects `round_in_cycle=2` —
  include in this PR (1-line fix)
- LOW-7: `ConvergenceAdaptiveScheduler.record_round_feedback` monotonicity
  documentation — include in this PR (doc-only)
- LOW-12: `SequentialScheduler.inject_noise` fallback to slot[0]
  — document (acceptable as designed; defer)
- LOW-13: `SequentialScheduler._resolve_slot` helper name misleading —
  rename or document (defer; cosmetic)

Per `docs/audit/framework-code-review.md` §1.9:
- LOW-15: `cfg.merge_operator.merge(prev=..., dynamic=..., cap=...)` NaN
  guard missing — include in this PR (1-line math.isfinite wrap)
- MEDIUM-7: `_w2_to_mode_centres` returns `0.0` for empty inputs —
  raise on empty `flat` (include in this PR)
## Wave 38 close-out

CLOSED in Wave 38 by commit **ff56e55** (Wave 38 Agent C WF1).

**Result summary**:
- HIGH-1 + MEDIUM-6 + MEDIUM-8 closed: `paper_quantities` is now threaded through the three call sites that previously dropped the signal on the floor
  - `CodimensionSheetScheduler.record_round_feedback` now consumes `paper_quantities` (Phase A — required for `PaperRatioAdaptiveScheduler` to take effect)
  - `SequentialScheduler.record_round_feedback` forwards `paper_quantities` (Phase B)
  - `BatchedTrajectoryRunner.run` forwards `paper_quantities` (Phase C)
- 3 regression tests in `tests/test_theory/` cover each threading site
- Same-class bug as Wave 30 F-1/F-4/F-5 (`paper_quantities` lost at scheduler boundary) — Wave 38 closes the remaining instances

**Files shipped** (see `git show --stat ff56e55` for the canonical list): scheduler edits in `adaptive_reflow/scheduler/_core.py` + `adaptive_reflow/scheduler/sequential.py` + `adaptive_reflow/framework/batched_runner.py` + 3 new regression tests.

**Verification**: pytest tests pass + commit (no push). Wave 31 `PaperRatioAdaptiveScheduler` now actually takes effect because the upstream signals survive the scheduler boundary. Plan status flipped from `pending (Wave 33 target)` to CLOSED.
