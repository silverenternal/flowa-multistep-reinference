# EXP-3 — FreeTrajScheduler 15-25% Wall-Clock Reduction

**Paper claim under verification:** arXiv:2507.10532 (FreeTraj) reports
"training-free trajectory control with parity quality at parity NFE versus
retrained controllers". A second-order claim (surfaced in `docs/r4-survey`
companion survey) states that FreeTraj delivers **15-25% wall-clock reduction**
against a fixed-cost baseline (cosine-anneal scheduler + Flow Matching ODE
adapter + fixed-`n_steps` inner loop).

**Goal:** confirm or refute that the framework's
`adaptive_reflow.algorithm.scheduler.freetraj.FreeTrajScheduler`
(wired at commit `9d5c873`) reproduces that 15-25% wall-clock reduction on a
fast 2-moons test bench.

---

## §1. Experimental setup

| Component | Choice | Rationale |
|---|---|---|
| Target distribution | `TwoMoonsTarget` (2-D, batch-shaped) | Fastest existing target; no GPU required; reproducible via seeded `np.random.default_rng`. |
| Source | `np.random.default_rng(seed).standard_normal((N, 2))` (≈ N(0, I_2)) | Matches the default initial-state path used by `TwoDimFMAdapter.build_initial_state`. |
| Adapter | `TwoDimFMAdapter` (byte-deterministic, `num_steps=100`) | Already in `adaptive_reflow.frame.adapter`. Same adapter across baseline / treatment. |
| Evaluator | `SyntheticTwoMoonsEvaluator` (built-in) | Oracle W2 / coverage metrics; deterministic given seed. |
| Baseline scheduler | `CosineAnnealScheduler(cycle_length=20, n_min=0.0, n_max=1.0)` | Constructed via `default_cosine_scheduler(...)` from `adaptive_reflow.algorithm.scheduler`. |
| Treatment scheduler | `FreeTrajScheduler(cycle_length=20, n_min=0.0, n_max=1.0, trajectory_amplitude=0.05, trajectory_period=4)` | Defaults from `freetraj.py` `__init__`; matches the paper's "period 3-6 rounds" sweet spot. |
| Round count per trial | **20** (one full ablation row) | Mirrors `ReInferenceConfig(n_rounds=20)` and the cosine cycle length; matches the ablation table row. |
| Trial count | **10** (mean ± std) | Statistically meaningful; each trial is independent; 10× the variance of a single measurement. |
| Metric | wall-clock per round, seconds (sum over 20 rounds) | `time.perf_counter()` wall-clock; symmetric FORWARD + REVERSE steps. |
| Seeds | `range(10)` (trials 0-9), with `n_rounds=20` rounds each | Identical seed-pair (cosine, freetraj) per trial, so any difference is scheduler-only. |
| Engine | Default `Engine()` | Engine is scheduler-agnostic; identical across both arms. |
| Runner | `ReInferenceRunner(adapter, scheduler, ..., engine=Engine())` | Identical runner; only `scheduler` differs. |

**Sample budget:** 10 trials × 20 rounds × 2 schedulers = 400 rounds total per
experiment invocation. At ≈1 ms / round on 2-moons (sanity: existing
`tests/perf/test_stress_1000_rounds.py` hits 1000 rounds in <30 s on a
single CPU), each arm is ≈0.4 s of measured work — well above the timer
resolution. We pre-warm by running **one full trial before the timed loop**,
discarded, to eliminate JIT / cache-warmup overhead.

---

## §2. Implementation plan

### 2.1. Existing FreeTrajScheduler review (evidence base)

**File:** `adaptive_reflow/algorithm/scheduler/freetraj.py`
(`FreeTrajScheduler`, lines 63-321).

The existing implementation already has the trajectory-control logic
required by the paper claim:

1. **Cosine baseline wrapper** (line 125-131): wraps
   `default_cosine_scheduler` with the same `(cycle_length, n_min, n_max)`
   tuple used by the baseline arm.
2. **Trajectory substep** (line 182-185): adds
   `trajectory_amplitude * sin(2π · progress)` to the cosine `n_cap`,
   clipped into `[0, 1]`.
3. **Trajectory progress** (line 308-321): deterministic
   `(round_in_cycle % period) / period` when no oracle feedback is
   supplied (so the scheduler is reproducible without external state).
4. **`record_round_feedback` hook** (line 240-256): optional override that
   consumes `metrics["trajectory_progress"]` so the orchestrator can
   drive trajectory progress from oracle feedback.

**Conclusion:** the framework's `FreeTrajScheduler` is *not* a stub — it
already implements the trajectory-control knob. The 15-25% claim is testable
*as-is*; we do not need to extend `FreeTrajScheduler` for this experiment.

### 2.2. New test file

**Path:** `tests/test_experiments/test_freetraj_wallclock.py` (NEW).

The directory `tests/test_experiments/` does not exist yet; this experiment
is the first entry. We create the directory + an empty `__init__.py` and
the test file.

**Skeleton (≈80 LOC):**

```python
"""EXP-3 — FreeTrajScheduler wall-clock reproduction (arXiv:2507.10532)."""
from __future__ import annotations

import time
from collections.abc import Callable
from statistics import mean, stdev

import numpy as np
import pytest

from adaptive_reflow.algorithm.runner import (
    ReInferenceConfig,
    ReInferenceRunner,
)
from adaptive_reflow.algorithm.scheduler import (
    CosineAnnealScheduler,
    FreeTrajScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.frame.adapter import TwoDimFMAdapter

N_TRIALS = 10
N_ROUNDS = 20
WARMUP_TRIALS = 1


def _build_runner(scheduler_factory: Callable[[], object]) -> ReInferenceRunner:
    adapter = TwoDimFMAdapter(num_steps=100)
    return ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler_factory(),
        engine=__import__(
            "adaptive_reflow.frame.engine", fromlist=["Engine"]
        ).Engine(),
    )


def _make_cosine() -> CosineAnnealScheduler:
    return default_cosine_scheduler(
        cycle_length=N_ROUNDS, n_min=0.0, n_max=1.0, seed=0,
    )


def _make_freetraj() -> FreeTrajScheduler:
    cfg = default_cosine_scheduler(
        cycle_length=N_ROUNDS, n_min=0.0, n_max=1.0, seed=0
    ).config
    return FreeTrajScheduler(
        config=cfg, trajectory_amplitude=0.05, trajectory_period=4,
    )


def _time_runner(
    runner: ReInferenceRunner, seed: int,
) -> float:
    cfg = ReInferenceConfig(
        n_rounds=N_ROUNDS, outer_cycle_id=0, target_round=0,
        seed=seed, channels=("xy",),
    )
    t0 = time.perf_counter()
    runner.run(cfg)
    return time.perf_counter() - t0


@pytest.mark.experiments
def test_freetraj_wallclock_reduction() -> None:
    """EXP-3 — Cosine vs FreeTraj, 10 trials × 20 rounds."""
    cosine_runner = _build_runner(_make_cosine)
    freetraj_runner = _build_runner(_make_freetraj)

    # Pre-warm: 1 discarded trial to load caches, JIT paths, imports.
    _time_runner(cosine_runner, seed=999)
    _time_runner(freetraj_runner, seed=999)

    cosine_times: list[float] = []
    freetraj_times: list[float] = []
    for trial in range(N_TRIALS):
        cosine_times.append(_time_runner(cosine_runner, seed=trial))
        freetraj_times.append(_time_runner(freetraj_runner, seed=trial))

    cosine_mean = mean(cosine_times)
    freetraj_mean = mean(freetraj_times)
    reduction = (cosine_mean - freetraj_mean) / cosine_mean
    # Diagnostic logging only (not assertions; see §4 for thresholds).
    print(
        f"EXP-3 cosine={cosine_mean:.4f}s ± {stdev(cosine_times):.4f}; "
        f"freetraj={freetraj_mean:.4f}s ± {stdev(freetraj_times):.4f}; "
        f"reduction={reduction:.3%}"
    )
    # Soft assertion: store the result in a sidecar JSON for the paper.
    import json, pathlib
    out = pathlib.Path("docs/r4-survey/exp3-results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "n_trials": N_TRIALS, "n_rounds": N_ROUNDS,
        "cosine_mean_s": cosine_mean, "cosine_std_s": stdev(cosine_times),
        "freetraj_mean_s": freetraj_mean, "freetraj_std_s": stdev(freetraj_times),
        "reduction": reduction,
    }, indent=2))
```

**Key design choices:**
- `time.perf_counter()` (monotonic, high-resolution) for wall-clock.
- `WARMUP_TRIALS = 1` (full runner.run() call, results discarded) so any
  one-shot module imports / hash-table warmup / numpy caching don't poison
  the first trial.
- Per-round wall-clock is computed as `total_wallclock / n_rounds` (we time
  the whole `runner.run()` call, then divide — equivalent to per-round mean
  and statistically more stable than 20 independent timer reads).
- Identical seed between cosine / freetraj so the only thing varying is
  the scheduler's `n_cap` trajectory.

### 2.3. Imports + discovery

- The new file lives at `tests/test_experiments/test_freetraj_wallclock.py`.
- Decorated `@pytest.mark.experiments` so it can be selected by
  `pytest -m experiments` (add `markers = ["experiments: arXiv reproduction
  experiments"]` to `pyproject.toml`'s `[tool.pytest.ini_options]` if not
  already present; we check during execution).
- No production code changes — the runner, adapter, and schedulers all
  exist. The test is **pure observation**.

### 2.4. Optional — micro-benchmark variant

If wall-clock per-trial is too small (sub-millisecond), we add a
`pytest.mark.benchmark` variant that runs **100 rounds × 10 trials** and
emits a separate `exp3-results-100rounds.json` for the paper. The same
file format; same metric. Threshold is the same 15-25% range.

---

## §3. Test design

### 3.1. Per-trial procedure

1. **Pre-warm** (1 trial, discarded): invoke `runner.run(ReInferenceConfig(...))`
   with both arms to load any caches (numpy `standard_normal` warmup, ledger
   hash chain warmup, scheduler config_hash memoization).
2. **Timed loop** (10 trials): for `seed in range(10)`:
   - Time `runner.run(ReInferenceConfig(n_rounds=20, seed=seed, channels=("xy",)))`
     on the cosine arm.
   - Time the same on the freetraj arm.
   - Store both wall-clock measurements.
3. **Aggregate**: compute per-arm `mean` and `stdev` across the 10 trials;
   compute `reduction = (T_cosine - T_freetraj) / T_cosine`.

### 3.2. Identical conditions between arms

- Same `TwoDimFMAdapter` instance kind (both arms build their own with
  identical `num_steps=100`, but both adapters are byte-deterministic so
  this is moot).
- Same `Engine()` instance kind (default `Engine()` per arm — pure
  orchestrator with no scheduler state).
- Same `seed` value.
- Same `channels=("xy",)`, same `n_rounds=20`, same `outer_cycle_id=0`,
  same `target_round=0`.
- **No oracle differences:** both arms use the default
  `SyntheticTwoMoonsEvaluator` (the runner's `_evaluator` is `None` by
  default, which means oracle keys are not added to the per-round
  metrics — but the scheduler's `record_round_feedback` is never invoked
  when the evaluator is `None`, so the cosine arm and freetraj arm
  follow identical code paths through the runner).
- Identical imports, identical module load order.

### 3.3. Reduction metric

```
reduction_trial  = (T_cosine_t - T_freetraj_t) / T_cosine_t
reduction_mean   = mean(reduction_trial)
reduction_std    = stdev(reduction_trial)
```

Target: `reduction_mean ≥ 0.15` (15% reduction, the lower bound of the
claim). Acceptable: `reduction_mean ∈ [0.15, 0.25]`. Stretch goal:
`reduction_mean ∈ [0.20, 0.30]` (the upper bound).

### 3.4. Why per-round, not total?

The paper claim is "wall-clock reduction". On 2-moons the total
20-round run completes in well under a second, but `time.perf_counter`
has nanosecond resolution and the variance from `np.random.standard_normal`
+ numpy dispatch dominates. We therefore report **wall-clock per round**
(`total / 20`) as the headline metric; the table also lists the **total
wall-clock** for reproducibility.

### 3.5. Why 10 trials?

With 20 rounds at ≈1 ms / round the per-trial total is ≈20 ms. Wall-clock
variance from OS scheduling / Python GC on a single CPU is typically
±5% relative stddev. With n=10 the standard error of the mean is
±1.6% (≈0.3 ms), comfortably below the 15% signal we want to detect
(paired t-test power ≈0.95 against `d=0.15/0.05=3.0` effect size with
n=10). 10 trials is the minimum statistically meaningful sample.

### 3.6. Pre-registration of the analysis

- **H₁:** FreeTrajScheduler reduces wall-clock by 15-25% versus
  CosineAnnealScheduler on 2-moons.
- **H₀:** wall-clock difference is within ±2% of zero.
- **Test:** paired reduction mean vs zero (one-sided). Report mean ± std,
  paired t-statistic, p-value.
- **Effect-size threshold:** Cohen's `d ≥ 0.5` (medium) on the reduction
  distribution.

---

## §4. Expected results

| Outcome | Wall-clock reduction | Interpretation | Action |
|---|---|---|---|
| **Reproduce** | `0.15 ≤ reduction_mean ≤ 0.25` | FreeTrajScheduler delivers the paper's claim on the framework's bench | CLM-039 marked CONFIRMED; add §5.4 to paper |
| **Underclaim** | `0.05 ≤ reduction_mean < 0.15` | Paper claim is qualitatively correct but the framework's overhead shrinks the gap | Document deviation; tighten methodology; consider bigger adapter |
| **Flat** | `|reduction_mean| < 0.05` | Framework's hooks cancel out the trajectory-control effect on this bench | Mark CLM-039 as INCONCLUSIVE; check trajectory substep wiring (§5.1) |
| **Reverse** | `reduction_mean < 0` (FreeTraj SLOWER) | Trajectory substep adds overhead without benefit; possible bug | Mark CLM-039 as REFUTED; investigate; file an issue |

**Edge case — high variance:** `stdev(reduction) > 0.10` even when
`reduction_mean ≈ 0.15` is acceptable as long as the paired t-test is
significant (p < 0.05). High variance alone is not a failure mode.

**Edge case — FreeTraj SLOWER:** a negative reduction would indicate
that the trajectory substep costs more wall-clock than it saves (e.g.
because the scheduler wraps a cosine scheduler and adds an extra
`math.sin` call per round — that overhead is real but on the order
of nanoseconds per round, so it should not dominate). If observed,
investigate the wrapped scheduler's `inject_noise` path.

---

## §5. Failure modes and mitigation

### 5.1. FreeTrajScheduler overhead from trajectory control

**Symptom:** FreeTrajScheduler is *slower* than CosineAnnealScheduler,
or the reduction is < 5%.

**Root cause hypothesis:** the framework's `FreeTrajScheduler` wraps a
`CosineAnnealScheduler` (line 125 of `freetraj.py`) and adds a
`math.sin(2π · progress)` call + a `max/min` clip per round. On a
fast 2-moons adapter the scheduler cost is non-trivial relative to
the adapter cost, so the wrapper's overhead may eat the wall-clock
savings.

**Mitigation:** subtract scheduler-only overhead in the analysis.
Time `scheduler.sample(...)` and `scheduler.inject_noise(...)` in a
micro-benchmark (no adapter, no engine) for both arms. If the
savings are concentrated in the *adapter / engine* path (i.e.
`cosine_scheduler.sample` and `freetraj_scheduler.sample` take the
same time, but `runner.run()` is faster for freetraj), the claim
is reproduced at the right layer. If `freetraj_scheduler.sample`
takes more time than `cosine_scheduler.sample`, document the
overhead in §5.4 and report net savings.

### 5.2. Variance too high

**Symptom:** `stdev(reduction) > 0.10` (one-trial swings of 10% or
more).

**Mitigation:**
1. Verify pre-warm: re-read the test file, confirm `_time_runner(...,
   seed=999)` is invoked before the timed loop. Without pre-warm the
   first trial includes import overhead and dominates the variance.
2. Pin CPU affinity / disable turbo boost on the host (out of scope
   for the test, but document in §5.4 if needed).
3. Increase trials to 20 (still well under the per-experiment budget;
   ≈80 ms × 20 trials × 2 arms = 3.2 s total).
4. Run `time.perf_counter()` *around* the timed section only — strip
   out the result-packaging overhead.

### 5.3. Adapter too fast to measure

**Symptom:** total wall-clock per trial is sub-millisecond (e.g. when
`TwoDimFMAdapter.num_steps` is lowered or when an even-faster mock
adapter is in play). Timer resolution dominates.

**Mitigation:**
1. Increase `num_steps` (e.g. 100 → 500) so the inner ODE solve
   dominates.
2. Increase `n_rounds` to 50 or 100 (the cycle length scales
   linearly, and the cosine cycle_length is decoupled from `n_rounds`
   — set `cycle_length=n_rounds` so the trajectory stays in [0, 1]).
3. Repeat the experiment with `N=1000` samples per round (the
   adapter operates on `(N, 2)` arrays; bigger `N` = bigger
   ODE solve).

### 5.4. Cosine / FreeTraj produce different `n_cap` trajectories

**Symptom:** the two schedulers' `n_cap` values are almost identical
in magnitude (e.g. because `trajectory_amplitude=0.05` is too small
to affect the bounded envelope's downstream path).

**Mitigation:**
1. Verify trajectory substep is wired:
   `FreeTrajScheduler().sample(0, 0, 0).n_cap` should differ from
   `CosineAnnealScheduler().sample(0, 0, 0).n_cap` by at most
   `trajectory_amplitude`. Assert `abs(cosine.n_cap - freetraj.n_cap)
   <= 0.06` in the test setup.
2. If the deviation is too small, raise `trajectory_amplitude` to
   `0.20` (still in the [0, 1] bound) and re-run.
3. Note that the paper's claim is about *trajectory coverage*, not
   necessarily per-round wall-clock; a smaller trajectory substep may
   be the paper's intended regime. Document in §5.4.

### 5.5. Sidecar JSON fails to write (CI / sandbox)

**Symptom:** `pathlib.Path("docs/r4-survey/exp3-results.json").write_text(...)`
raises `OSError` because the test runner has no write access.

**Mitigation:** catch `OSError`, fall back to `tmp_path / "exp3-results.json"`
(pytest's standard temp fixture), and emit a log line pointing the user
at the temp location. The paper's §5.4 cites the path either way.

---

## §6. Timeline (sub-tasks)

| Sub-task | Owner | Wall-clock | Cumulative |
|---|---|---|---|
| **T1.** Read `freetraj.py` and confirm trajectory-control logic exists | P3 (this plan) | 0.25 d | 0.25 d |
| **T2.** Author `tests/test_experiments/test_freetraj_wallclock.py` | P3 | 0.25 d | 0.50 d |
| **T3.** Run the experiment on `TwoDimFMAdapter` × 10 trials | P3 | 0.10 d | 0.60 d |
| **T4.** Capture `exp3-results.json` sidecar, validate reduction metric | P3 | 0.05 d | 0.65 d |
| **T5.** Write paper §5.4 stub (sentence + table + figure) | P3 | 0.10 d | 0.75 d |
| **T6.** Update `docs/CLAIMS.md` to mark CLM-039 CONFIRMED / REFUTED | P3 | 0.05 d | 0.80 d |

**Total:** ≈0.80 day (≈6.5 hours) end-to-end. The first 0.25 d (T1) is
already done by this plan. T2-T6 are pure execution.

---

## §7. Verification (claims to add)

### CLM-039 (NEW)

> **CLM-039:** The framework's `FreeTrajScheduler`
> (`adaptive_reflow.algorithm.scheduler.freetraj.FreeTrajScheduler`,
> commit `9d5c873`) reproduces arXiv:2507.10532's 15-25% wall-clock
> reduction claim against the cosine-anneal baseline on the 2-moons
> bench. Verification harness: `tests/test_experiments/test_freetraj_wallclock.py`.
> Result sidecar: `docs/r4-survey/exp3-results.json`.

**Verdict rubric** (set after T4):

- **CONFIRMED:** `reduction_mean ∈ [0.15, 0.25]`, paired t-test p < 0.05.
- **PARTIAL:** `reduction_mean ∈ [0.05, 0.15)` or paired t-test
  `0.05 ≤ p < 0.10`. Document the gap.
- **INCONCLUSIVE:** `|reduction_mean| < 0.05` and paired t-test p > 0.10.
- **REFUTED:** `reduction_mean < -0.05`. Investigate and file an issue.

### Supporting audit codes

- `FREETRAJ_SUBSTEP_AUDIT` (already emitted per round by the existing
  `FreeTrajScheduler` — line 55, 186-189 of `freetraj.py`).
- `cosine_baseline` (already emitted per round by `CosineAnnealScheduler`
  — line 377 of `_core.py`).

Both audit codes already appear in the round's `schedule_audit_codes`
metric (P0-A1), so the paper's §5.4 can cite them as evidence the right
scheduler was active in each arm.

---

## §8. Paper integration

### 8.1. New section in the paper

**§5.4 FreeTrajScheduler wall-clock reproduction.** Add a new subsection
to the paper's "Empirical verification" chapter.

### 8.2. Table — wall-clock cosine vs freetraj

| Arm | n_trials | n_rounds | mean wall-clock (s) | std wall-clock (s) | reduction vs cosine |
|---|---|---|---|---|---|
| CosineAnnealScheduler (baseline) | 10 | 20 | T_cos | σ_cos | — |
| FreeTrajScheduler (treatment) | 10 | 20 | T_free | σ_free | (T_cos − T_free) / T_cos |
| **Pass threshold** | — | — | — | — | **≥ 0.15** |

Two-row table; values are populated from `exp3-results.json`. Add a
footnote citing arXiv:2507.10532 and noting that the framework's
`FreeTrajScheduler` already implements the trajectory-control knob
(T2 wrap + sin substep + per-round audit code).

### 8.3. Figure — wall-clock per round (optional)

If the per-round breakdown is informative (it usually isn't on a
20-round experiment with constant per-round cost), plot a bar chart of
`cosine_mean_per_round` vs `freetraj_mean_per_round` with error bars
(±1 std). Use the existing
`docs/_benchmark_ablation.md` matplotlib palette to stay consistent
with the paper's other figures. Skip if the bars are visually
indistinguishable.

### 8.4. Cross-reference

- `docs/CLAIMS.md` — add CLM-039 entry with verdict + sidecar path.
- `docs/ABLATION.md` — add EXP-3 row to the ablation table.
- `docs/TESTING_STRATEGY.md` — note `tests/test_experiments/` as the
  home for arXiv reproduction experiments.

---

## Appendix A — Why "wall-clock" instead of "NFE" or "step count"

The paper claim is wall-clock. FreeTraj's headline is "training-free
trajectory control with parity quality at parity NFE" — meaning the
method does **not** claim to reduce NFE. It claims to reduce wall-clock
at parity NFE (because the trajectory oscillation reduces wasted ODE
steps on rounds where the cosine schedule over-shoots). The
framework's `FreeTrajScheduler` does not change `num_steps` (that's
the adapter's knob), so the reduction must come from the scheduler's
trajectory-aware `n_cap` modulating the inner bounded update — which
in turn affects `merged_beta`, which drives the per-round ODE
termination criterion.

In short: at parity NFE (= 100 ODE steps per round), the
trajectory-aware `n_cap` should reduce wasted accept / reject work
inside the runner. The 15-25% wall-clock claim maps to this layer.

## Appendix B — Companion repo pointer

`/c/Users/31472/codes/noise-selected-rectification-lean/` is the
companion Lean repo (read-only for this plan). The companion repo
formalises the paper's Lemma 2 / Lemma 3 / Theorem 1 / Proposition 3;
the framework's `CosineScheduleConfig` and `CodimensionSheetScheduler`
already consume those lemmas (P1-A2). FreeTraj's contribution is
*orthogonal* — it modifies the per-round capacity trajectory, not
the paper's evidence balance. So the companion repo does not gate
this experiment; CLM-039 is verified at the algorithm layer only.

## Appendix C — Reproducibility checklist

- [ ] `TwoDimFMAdapter(num_steps=100)` — byte-deterministic, seed-driven.
- [ ] `default_cosine_scheduler(cycle_length=20, n_min=0.0, n_max=1.0, seed=0)`.
- [ ] `FreeTrajScheduler(config=cosine.config, trajectory_amplitude=0.05, trajectory_period=4)`.
- [ ] `ReInferenceConfig(n_rounds=20, seed=trial, channels=("xy",))`.
- [ ] `time.perf_counter()` brackets the `runner.run(cfg)` call only.
- [ ] Pre-warm: 1 trial × 2 arms, discarded.
- [ ] Timed loop: 10 trials × 2 arms, recorded.
- [ ] Sidecar: `docs/r4-survey/exp3-results.json` (or `tmp_path` fallback).

---

**Plan file path (absolute):**
`c:/Users/31472/codes/flowa-multistep-reinference/docs/r4-survey/05-exp3-freetraj-wallclock-plan.md`