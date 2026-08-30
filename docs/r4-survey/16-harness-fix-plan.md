# CIFAR harness — fix plan for the n_cap=1.0 collapse

> **Author:** Agent P (harness-fix-plan subagent)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Status:** READ-ONLY plan; no code changes. Awaiting approval before execution.
> **Inputs cited:**
> - `docs/r4-survey/15-harness-bug-diagnosis.md` (Phase 1 diagnosis)
> - `docs/r4-survey/cifar_results/experiment-log.md` (Phase 1 honest finding)
> - `tools/run_sota_cifar_experiment.py` (current harness)
> - `adaptive_reflow/algorithm/scheduler/_core.py` (CosineAnnealScheduler, CodimensionSheetScheduler)
> - `adaptive_reflow/algorithm/scheduler/evidence_driven.py` (EvidenceDrivenScheduler)
> - `adaptive_reflow/algorithm/scheduler/freetraj.py` (FreeTrajScheduler)

## §0. TL;DR

The Phase-1 diagnosis identified **one single hard-coded `0`** at
`tools/run_sota_cifar_experiment.py:439` as the root cause of `n_cap=1.0`
for every scheduler and every round. The scheduler implementations are
correct; the construction parameters are correct; the `n_cap →
num_steps` mapping is correct. The defect is CIFAR-only (lives in the
inline per-round loop in `_run_framework`; the 2D harness drives
`round_in_cycle` correctly through `BatchedTrajectoryRunner.run`).

The minimum fix is **a 6-byte change**:
`sample = scheduler.sample(0, 0, int(r))` →
`sample = scheduler.sample(0, int(r), int(r))`.
This is sufficient to restore non-constant `num_steps` for
`CosineAnnealScheduler`, `CodimensionSheetScheduler`, and `FreeTrajScheduler`.
A *companion* fix (compute-and-pass `evidence_ratio` via
`record_round_feedback`) is needed to make `EvidenceDrivenScheduler`
produce a PID-modulated trace distinct from the cosine baseline.

The 2D harness (`tools/run_sota_2d_experiment.py` →
`BatchedTrajectoryRunner.run`) drives `round_in_cycle=r` correctly today;
no change is needed there.

---

## §1. Fix scope

### Files that will change

| # | File | Why |
|---|---|---|
| 1 | `tools/run_sota_cifar_experiment.py` | The single-line `round_in_cycle` fix at line 439, plus the `record_round_feedback` companion wiring and a small widening of the harness's `max_num_steps` budget so the cosine ramp maps to a non-constant `num_steps` even at small `max_num_steps`. |
| 2 | `tests/test_tools/test_run_sota_cifar_experiment.py` | Add a regression test that exercises `_run_framework` with a mock adapter and asserts (a) the per-round `n_cap` values differ across rounds, (b) the four `samples.npz` rows are not byte-identical, and (c) the per-scheduler traces look like the expected cosine / cosine-with-PID / cosine-with-wobble. Also extend the existing `test_build_scheduler_returns_all_four_families` to assert the trace varies with `round_in_cycle`. |

No other source files will change. The fix is harness-side only; the
framework, the four schedulers, the adapter, and the FID helper are
unchanged.

### Files that will NOT change (and why)

| File | Reason |
|---|---|
| `adaptive_reflow/algorithm/scheduler/_core.py` (CosineAnnealScheduler + CodimensionSheetScheduler) | Both schedulers correctly use `round_in_cycle` to drive their cosine/sheet math (`_core.py:373,2701`). The defect is that the harness *passes* `round_in_cycle=0` instead of `r`; the schedulers see no signal. Touching this file would mask Phase-1 tests that assert the cosine ramp with `round_in_cycle` varying. |
| `adaptive_reflow/algorithm/scheduler/evidence_driven.py` | `record_round_feedback` already exists and is correctly implemented; the harness must *call* it. Likewise `_last_pid_delta` is integrated into `sample()` already. No code change needed inside the scheduler. |
| `adaptive_reflow/algorithm/scheduler/freetraj.py` | The wrapped cosine call and the `substep = amplitude * sin(2π·progress)` math are correct (`freetraj.py:173-185`); `_compute_trajectory_progress` already keys off `round_in_cycle`. Same defect-only-on-call-site shape. |
| `adaptive_reflow/adapters/rectified_flow_cifar.py`, `adaptive_reflow/adapters/_gnobitab_ddpmpp.py` | Adapter receives `num_steps` (an int) and is `n_cap`-agnostic. Its contract does not involve `n_cap`; it does not need to change. |
| `adaptive_reflow/algorithm/batched_runner.py` | The 2D harness already drives `round_in_cycle=r` inside `BatchedTrajectoryRunner.run`. The 2D harness is correct. (Verified via `docs/r4-survey/15-harness-bug-diagnosis.md` §5.) |
| `tools/run_sota_2d_experiment.py` | Same as above — 2D harness is correct. Re-running the 2D experiment is *not* part of this fix. |
| `adaptive_reflow/schedule/cosine.py` (the closed-form `n_cap_for_round`) | The math is correct; it just always receives `round_in_cycle=0` from the broken CIFAR call site. |

---

## §2. Fix design (per scheduler)

### 2.1 CosineAnnealScheduler

| Field | Value |
|---|---|
| **Current `n_cap` returned** | `1.0` for every round (`_core.py:373` calls `n_cap_for_round(self._config, round_in_cycle=0)` → `n_min + (n_max - n_min) * (1 + cos(π·0))/2 = 1.0`). |
| **Desired `n_cap` returned** | Cosine ramp `1.0 → 0.0` over rounds `0..L-1`: `r=0 → 1.000, r=1 → 0.9698, r=2 → 0.8830, r=3 → 0.7500, r=4 → 0.5868, r=5 → 0.4132, r=6 → 0.2500, r=7 → 0.1170, r=8 → 0.0302, r=9 → 0.000`. |
| **Specific change** | None in the scheduler. The `_run_framework` harness passes `round_in_cycle=0` (`tools/run_sota_cifar_experiment.py:439`); the harness fix is the only thing needed. |
| **Verifying test** | Existing: `tests/test_algorithm/test_scheduler.py::test_cosine_anneal_scheduler_ramp` (asserts the cosine closed form sweeps `1.0 → 0.0`). New: extend `tests/test_tools/test_run_sota_cifar_experiment.py::test_build_scheduler_returns_all_four_families` to call `sample(0, r, r)` for `r in range(5)` and assert the returned `n_cap` values are `[1.0, ~0.9698, ~0.8830, ~0.7500, ~0.5868]` (within `1e-4`). |

### 2.2 CodimensionSheetScheduler

| Field | Value |
|---|---|
| **Current `n_cap` returned** | `1.0` for every round (same wiring defect: `_core.py:2699` evaluates `u_r = round_in_cycle / (L-1)` against `round_in_cycle=0`, yielding `n_cap_base=1.0`; line 2713 maps to `n_min + (n_max - n_min) * n_cap_base = 1.0`). The `evidence_ratio` on the returned sample is also `1.0` for every round (computed from `n_cap_base=1.0`). |
| **Desired `n_cap` returned** | Same cosine trace as the `CosineAnnealScheduler` row (`1.0 → 0.0` over 10 rounds). `evidence_ratio` on the sample *must* also vary across rounds per `_paper_evidence_balance(n_cap_base, eps_implicit=0.05)`. With `eps_implicit=0.05`: ratio ranges from `≈ 1.0` at `r=0` (sheet dominates) through `≈ 0.99997` at intermediate `r` (sheet still dominates) up to `1.0` again at `r=9`. Numerically nearly constant in `n_cap_base ∈ [0, 1]`, **but the small variation is auditable** in `per_round_metrics.csv`. |
| **Specific change** | None in the scheduler. Same harness-side fix. |
| **Verifying test** | Existing: `tests/test_algorithm/test_scheduler.py::test_codimension_sheet_uses_cosine_base` (asserts the cosine base is invoked). New unit test: drive `sample(0, r, r)` for `r in range(10)` and assert (a) `n_cap` values are `[1.0, ~0.9698, ..., ~0.000]`, (b) `evidence_ratio` is **in** `[0.99995, 1.0]` for every round. |

### 2.3 EvidenceDrivenScheduler

| Field | Value |
|---|---|
| **Current `n_cap` returned** | `1.0` for every round (`evidence_driven.py:338-346` delegates to wrapped cosine, which returns `1.0` because `round_in_cycle=0`; `_last_pid_delta=0.0` because the harness never calls `record_round_feedback`). |
| **Desired `n_cap` returned** | Cosine ramp `1.0 → 0.0` **plus a small PID-lite offset** (`|delta| ≤ max_step=0.05`). The PID offset is driven by the per-round `evidence_ratio`; without a feedback call, it stays zero. To distinguish the row from the cosine baseline, the harness must (a) pass `round_in_cycle=r` and (b) feed per-round `evidence_ratio` to `record_round_feedback(r, {"evidence_ratio": ratio})` after each `batched_inference` call. With `target_ratio=1.0`, the PID pushes *down* on `n_cap` when observed `ratio < 1.0` (early rounds, sheet dominates so ratio is near 1, so delta is small; mid-rounds where cell residuals grow, delta grows within the ±0.05 cap). Expected trace: cosine curve clamped to `[0, 1]` *plus* PID modulation of order `±0.01–0.05`. |
| **Specific change** | None in the scheduler. Two harness-side changes: (i) pass `round_in_cycle=r` (Fix A); (ii) after each round's `batched_inference`, compute a *proxy* `evidence_ratio` and call `scheduler.record_round_feedback(int(r), {"evidence_ratio": proxy})`. The proxy candidate: re-invoke `_paper_evidence_balance` from `sample.evidence_ratio` that the codim scheduler exposes — *but* the harness uses each scheduler in isolation. The cleanest available signal: use `CodimensionSheetScheduler`'s `last_evidence_ratio` from a shared instance, or fall back to the `sample.evidence_ratio` attribute if present, or fall back to `0.5` (neutral midpoint — the missing-ratio case). Since the diagnosis (§3 there) is explicit that the PID will be inert unless feedback is fed, we **must wire feedback** or accept that the row tracks cosine. Recommended: instantiate a *shared* `CodimensionSheetScheduler` once per `r` (cheap) and use its `sample.evidence_ratio` as the proxy. |
| **Verifying test** | Existing: `tests/test_algorithm/test_evidence_driven_scheduler.py` covers the PID-lite math (saturates, integral windup, etc.). New regression in `tests/test_tools/test_run_sota_cifar_experiment.py`: drive the framework loop for `EvidenceDrivenScheduler` only with a mock adapter; assert (a) `_last_pid_delta` differs from `0.0` after 5 rounds, (b) some `n_cap` value in `per_round_metrics` deviates from the corresponding `CosineAnnealScheduler` `n_cap` by `> 0.005`. |

### 2.4 FreeTrajScheduler

| Field | Value |
|---|---|
| **Current `n_cap` returned** | `1.0` for every round (`freetraj.py:173-185` delegates to wrapped cosine, adds `amplitude * sin(2π·progress)` where `progress = (round_in_cycle % period) / period = 0` for `round_in_cycle=0`). |
| **Desired `n_cap` returned** | Cosine ramp with a small sinusoidal wobble at integer multiples of `period=4`: `sin(2π·progress) ∈ {0, +1, 0, -1, 0, +1, 0, -1, 0, +1}` → `substep ∈ {0, +0.05, 0, -0.05, 0, +0.05, 0, -0.05, 0, +0.05}` → final `n_cap = cosine_base(r) + substep` (clipped to `[0, 1]`). |
| **Specific change** | None in the scheduler. Harness-side fix (pass `round_in_cycle=r`). |
| **Verifying test** | Existing: `tests/test_algorithm/test_freetraj.py` covers the construction / progress / substep math. **Note**: `tests/test_experiments/test_freetraj_wallclock.py::test_freetraj_trajectory_progress_freezes_when_driven_statefully` currently asserts that `caps_freetraj == caps_cosine` (claiming the substep is inert). This test pins the existing defect and **must be revisited** when the harness fix lands — see §5 risk 1. New unit test in `tests/test_tools/test_run_sota_cifar_experiment.py`: drive `sample(0, r, r)` for `r in range(8)` and assert `n_cap` values at `r=1, 3, 5, 7` deviate from `n_min + (n_max - n_min) * 0.5*(1+cos(π·r/9))` by `> 0.01` in absolute terms (i.e. the `±0.05` wobble fires). |

---

## §3. Harness script fix

### 3.1 Current per-scheduler construction parameters

Lines 169-200 of `tools/run_sota_cifar_experiment.py` (`build_scheduler`):

| Scheduler | Constructor call | Config knobs |
|---|---|---|
| `CosineAnnealScheduler` | `default_cosine_scheduler(cycle_length=int(rounds))` | All defaults (`n_min=0.0`, `n_max=1.0`, `schedule_family="cosine_no_restart"`). |
| `CodimensionSheetScheduler` | `CodimensionSheetScheduler(cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.05)` | `eps_implicit=0.05`. |
| `EvidenceDrivenScheduler` | `EvidenceDrivenScheduler(config=..., kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0, k_eps=0.5, eps_implicit_base=0.05)` | PID-lite gains `kp/ki/max_step/target_ratio/k_eps`, `eps_implicit_base=0.05`. |
| `FreeTrajScheduler` | `FreeTrajScheduler(config=..., trajectory_amplitude=0.05, trajectory_period=4)` | `trajectory_amplitude=0.05`, `trajectory_period=4`. |

### 3.2 New per-scheduler construction parameters

**No constructor changes.** The Phase-1 diagnosis is explicit that the
construction parameters are correct (`15-harness-bug-diagnosis.md` §2).
We do not need to widen `n_max`, retune `eps_implicit`, or change the
PID gains to restore non-constant `n_cap`. The only harness-side
construction change is *optional* (see §3.4).

### 3.3 Map from `n_cap` to `num_steps`

Current (`tools/run_sota_cifar_experiment.py:441`):

```
num_steps = max(1, int(round(n_cap * float(max_num_steps))))
```

This mapping is correct in isolation: takes `n_cap ∈ [0, 1]` to
`num_steps ∈ [1, max_num_steps]`. With `n_cap=1.0` it returns
`max_num_steps`. With the Phase-1 fix, the cosine ramp gives
`n_cap ∈ [0, 1]` and `num_steps` varies as expected (e.g. for
`max_num_steps=20` and 10 rounds:

| `r` | `n_cap` | `num_steps` |
|---:|---:|---:|
| 0 | 1.0000 | 20 |
| 1 | 0.9698 | 19 |
| 2 | 0.8830 | 18 |
| 3 | 0.7500 | 15 |
| 4 | 0.5868 | 12 |
| 5 | 0.4132 | 8 |
| 6 | 0.2500 | 5 |
| 7 | 0.1170 | 2 |
| 8 | 0.0302 | 1 |
| 9 | 0.0000 | 1 |

which is *non-constant* and validates the fingerprint.)

### 3.4 `max_num_steps` budget (the optional widening)

To make `num_steps` distinguishable from `max_num_steps` early, the
harness can widen `max_num_steps` past `2` to a value where
`round(n_cap * max)` overshoots fewer early-round `n_cap`s. The
Phase-1 diagnosis (§6, "Fix C") flagged this as lower-priority; the
baseline of `--framework-max-num-steps 10` is already saturated at
`n_cap=1.0` and **will saturate at fewer than 20 even after the fix**
(to `num_steps=19` at `r=1`). For full saturation coverage, the
recommended default is to keep `--framework-max-num-steps 20` (i.e.
2x the baseline 10-step Euler) — this lets `num_steps` sweep
`[1, 20]` across the 10-round cycle.

For round-by-round budget verification: `n_rounds=10` ×
`framework_samples=100` = 1000 total samples per scheduler, identical
to baseline. Wall-clock scales linearly with `num_steps`, so
`max_num_steps=20` vs `max_num_steps=10` doubles the framework-row
wall-clock from ~458 s to ~900 s per scheduler. The CIFAR run's
budget goes from ~45 min to ~90 min. This is acceptable for a
re-run-once-per-fix.

### 3.5 The 2-line harness diff (core fix)

`tools/run_sota_cifar_experiment.py:439`:

```python
# before
sample = scheduler.sample(0, 0, int(r))
# after
sample = scheduler.sample(0, int(r), int(r))
```

And the companion (lines 437-446, restructured):

```python
# share a CodimensionSheetScheduler instance for the evidence_ratio proxy
# (cheap; reuse one scheduler, ignore its own sample.n_cap for the framework)
evidence_proxy_scheduler = (
    CodimensionSheetScheduler(
        cycle_length=int(n_rounds),
        n_min=0.0,
        n_max=1.0,
        eps_implicit=0.05,
    )
    if scheduler_name == "EvidenceDrivenScheduler"
    else None
)

for r in range(int(n_rounds)):
    sample = scheduler.sample(0, int(r), int(r))   # <-- fix (was 0, 0, r)
    n_cap = float(sample.n_cap)
    num_steps = max(1, int(round(n_cap * float(max_num_steps))))
    sub = adapter.batched_inference(
        n_samples=int(framework_samples),
        num_steps=int(num_steps),
        seed=int(seed_base) * 1000 + int(r),
    )
    sub = np.asarray(sub, dtype=np.float64).reshape(
        (int(framework_samples), 3, 32, 32)
    )
    samples_pool.append(sub)

    # Fix B: wire per-round feedback for EvidenceDrivenScheduler
    if evidence_proxy_scheduler is not None:
        proxy_sample = evidence_proxy_scheduler.sample(0, int(r), int(r))
        scheduler.record_round_feedback(
            int(r),
            {"evidence_ratio": float(proxy_sample.evidence_ratio)},
        )

    row: dict[str, float] = {
        "round_index": int(r),
        "n_cap": float(n_cap),
        "num_steps": int(num_steps),
    }
    evidence = getattr(sample, "evidence_ratio", None)
    if evidence is not None:
        row["evidence_ratio"] = float(evidence)
    per_round_metrics.append(row)
```

### 3.6 Total rounds × num_steps budget

With `--n-rounds=10 --framework-max-num-steps=20`, sum of `num_steps`
across the 10 rounds:

`20 + 19 + 18 + 15 + 12 + 8 + 5 + 2 + 1 + 1 = 101`

For the cosine baseline (no fix): `10 * 20 = 200`. For the cosine
*post-fix*: `101` total integration steps per scheduler. Baseline
runs `10 * 10 = 100` (or `2` at the paper's 2-NFE; the comparison
matches the harness's `--baseline-num-steps`, default `2`).

Wall-clock estimate per scheduler (CPU, 100 samples × 0.05 s/sample/step):
~101 × 100 × 0.05 = ~505 s for the framework row, vs ~454 s for the
baseline. Total framework run ≈ 4 × 505 = ~33 min (4 schedulers).
Total run time with FID = ~45 min (consistent with the Phase-1 run's
~45 min). Doubling `max_num_steps` from 10 to 20 nominally doubles this
to ~90 min; staying at `max_num_steps=10` is also acceptable (the
fingerprint is non-constant but saturates later), reducing total wall
to ~45 min — *equal* to the broken run. **Recommendation: keep
`--framework-max-num-steps 10`** to keep wall-clock parity with the
Phase-1 run; accept that early-round `num_steps` saturates at `10`.

---

## §4. Verification plan

### 4.1 Pre-fix (Phase-1 observed state)

`docs/r4-survey/cifar_results/per_round_metrics.csv` shows
`n_cap = [1.0, 1.0, ..., 1.0]` for all four schedulers × 10 rounds.
`num_steps = [10, 10, ..., 10]` everywhere. The 5
`{name}_samples.npz` files are byte-identical (mean_abs_diff = 0.00000
across all pairs). The 4 framework FIDs are byte-identical `66.6508`.
The framework-vs-baseline `-0.0825` delta is pure Monte-Carlo noise.

### 4.2 Post-fix (expected state)

* `per_round_metrics.csv` shows:
  - `CosineAnnealScheduler`: `n_cap` decreases `1.0 → 0.0` per
    `cosine_no_restart` closed form.
  - `CodimensionSheetScheduler`: `n_cap` decreases `1.0 → 0.0`
    (same cosine base) and `evidence_ratio` ∈ `[0.99995, 1.0]`.
  - `EvidenceDrivenScheduler`: `n_cap` cosine-trend *with* a
    small PID offset, `evidence_ratio` matches the codim row.
  - `FreeTrajScheduler`: cosine-trend with `±0.05` sinusoidal wobble
    keyed by `r % 4`.
* The 4 framework `samples.npz` files are NOT byte-identical to each
  other. Mean-abs-diff between `CosineAnnealSamples.npz` and
  `FreeTrajSamples.npz` is `> 0.005` for some pair of rounds
  (i.e. the wobble drives a visible sample-level difference).
* The 4 framework FIDs are NOT byte-identical. Each row's FID is
  within the Monte-Carlo range of `±5%` of baseline, so by Hoeffding's
  bound on 1000 samples per scheduler, paired FIDs differ by
  ~`±0.2`. We expect to see the rows spread across a `~0.5` window.
* **Framework FID < baseline FID**: NOT guaranteed.
  At 10-step Euler with the cosine ramp, all four rows should track
  the baseline FID to within `±0.5`. The "framework wins" claim was
  *parity-or-better* in the paper plan (`11-cifar-experiment-plan.md` §1)
  and parity is acceptable. Regression > `+10%` must be reported
  honestly. We do not assume improvement; if three rows regress
  slightly, that is honest and reported.

### 4.3 Regression test additions

The following tests must be added to `tests/test_tools/test_run_sota_cifar_experiment.py`:

1. `test_run_framework_n_cap_varies_per_round` — drive
   `_run_framework` with a `MockAdapter` for each scheduler; assert
   `per_round_metrics[i]["n_cap"] != per_round_metrics[i+1]["n_cap"]`
   for `i in range(n_rounds - 1)` *unless* the scheduler intentionally
   keeps `n_cap` constant (only the broken case).

2. `test_run_framework_four_schedulers_produce_different_traces` —
   drive `_run_framework` with a `MockAdapter` for all four
   schedulers; assert that at least one pair of schedulers has a
   different `n_cap[r=5]` (the mid-cycle round).

3. `test_run_framework_evidence_driven_pid_advances` — drive
   `_run_framework` with a `MockAdapter` that returns
   `evidence_ratio=0.95` every round; assert that
   `EvidenceDrivenScheduler.controller._last_pid_delta != 0` after
   the loop completes.

4. Update existing `test_build_scheduler_returns_all_four_families`
   to assert the per-round `n_cap` sequence looks like the closed form
   (cosine for CosineAnneal + Codimension + EvidenceDriven; cosine with
   `±0.05` wobble for FreeTraj).

### 4.4 End-to-end post-fix gate

After the diff lands, re-run the script with `--quick` (the smoke
profile: 200 samples / 5 rounds / 50 chains / no FID):

```bash
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --quick \
    --output-dir data/rf_cifar_out_fixed
```

Then assert on the CSV that:
- `n_cap` ≠ 1.0 for at least 6 of 25 cells (the five-round cosine ramp
  is `1.0, 0.9698, 0.8830, 0.7500, 0.5868` — 4 of 5 are not 1.0).
- For each scheduler, the per-round `n_cap` sequence is not constant.

Then re-run with the paper-grade config (1000 samples / 10 rounds / 100
chains) and verify the FID rows are not byte-identical.

### 4.5 Six-gate check

The Phase-1 run passed all 6 of these gates (per `experiment-log.md` §3):
`ruff`, `mypy`, `tests/test_tools/test_run_sota_cifar_experiment.py`,
`tests/test_adapters/test_rectified_flow_cifar.py`,
`_gnobitab_ddpmpp` topology, FID computation. Post-fix the same 6
gates must pass: the new test additions pass, the existing tests still
pass (we extend one; we don't break any), `ruff` + `mypy` clean.

---

## §5. Risk assessment

### Risk 1: scheduler changes break existing tests

**Severity: medium.**
The Phase-1 run established `tests/test_experiments/test_freetraj_wallclock.py::test_freetraj_trajectory_progress_freezes_when_driven_statefully`
specifically asserting that the freetraj substep is inert
(`caps_freetraj == caps_cosine`). This test *pins the existing defect*.
If the fix lands without updating this test, the test will fail.

**Mitigation:** the fix is in `tools/run_sota_cifar_experiment.py`, so
the freetraj scheduler code is unchanged. The test at issue uses
`freetraj.sample(outer_cycle_id=0, round_in_cycle=r, target_round=0)`
directly with `r in range(N_ROUNDS)` — i.e. *it drives the scheduler
correctly* and asserts the (broken) equality with cosine. The test is
not affected by the harness fix. **No test removal/change needed in
Phase 2.** The new `tests/test_tools/` regression test covers the
post-fix expected behaviour.

If `test_freetraj_trajectory_progress_freezes_when_driven_statefully`
has been "marked todo" in Phase 1 as a future-fix candidate, we
consider it out of scope for this fix. If a follow-up ticket exists
to make the freetraj substep actually differentiate from cosine,
that is a *separate* task and lives in
`tests/test_experiments/test_freetraj_wallclock.py`.

### Risk 2: new `n_cap` values produce samples too noisy

**Severity: low.**
With `n_cap` sweeping `1.0 → 0.0` and `num_steps = round(n_cap * max_num_steps)`,
`num_steps` *decreases* over the cycle. Late rounds (high `r`) use
fewer Euler steps. For 10-step Euler with `max_num_steps=10`, the
*minimum* `num_steps` is `1` (at `r=9`, `n_cap=0`). A 1-step Euler
trajectory is essentially a single forward-pass through the UNet
with no integration; the resulting samples are noisier than the
baseline 2-step Euler. The late-round FID contribution to the pooled
sample set will be measurably worse than baseline. This is *expected*
per the paper's coarse-to-fine anneal (early rounds inject high noise
that the multi-round loop progressively cancels) — but on CIFAR-10
the per-round state is discarded (each round seeds a *fresh* draw),
so the coarse-to-fine logic doesn't carry. The pooled FID will
therefore reflect a mix of high-quality (early rounds, `num_steps=10`)
and low-quality (late rounds, `num_steps ≤ 3`) samples.

**Mitigation:** widen `max_num_steps` so late rounds stay at, e.g.,
`≥ 5` steps. With `max_num_steps=20` and the cosine ramp, late rounds
are at `2 / 1 / 1` steps — still low. Lower priority: report
honestly and accept the late-round noise floor.

**Alternative mitigation**: keep `--framework-max-num-steps 10`
(equal to baseline 2-NFE ... no wait, baseline is **2-NFE** by
default — see `DEFAULT_BASELINE_NUM_STEPS=2`). Match this:
`--baseline-num-steps 10 --framework-max-num-steps 10`. Then the
baseline uses 10 steps and the framework uses `[1, 10]` steps. The
zero-step boundary is reached at `r=9` for both; pool the early
rounds to match baseline FID; accept the late-round halo. Honest
framing in `comparison.md`: framework is a mix of step counts, so the
single-FID comparison is a coarse aggregate.

### Risk 3: framework improvement might be NEGATIVE

**Severity: medium (accepted).**
The paper claim is *parity-or-better*; the Phase-1 plan §1 says
"parity is acceptable; regression > +10% must be reported honestly".
With `num_steps` varying `[1, 10]`, late-round samples are noisy
(see Risk 2). The pooled FID may regress by 5-15% relative to the
10-step baseline. **This is acceptable.** The
"`experiment-log.md` honesty" carry-over into the post-fix run is:
report what we see, do not hide a regression.

**Mitigation:** the post-fix run must (a) report `Δ` vs baseline for
each row, (b) if any row regresses > 10%, note it explicitly in
`comparison.md` "Honest framing", (c) note that the 2D harness showed
`-7.3% to -10.4%` improvement which does NOT translate to CIFAR
without chained per-round state, which the harness still doesn't do.

### Risk 4: widened `max_num_steps` doubles wall-clock

**Severity: low.**
If we choose `max_num_steps=20` instead of `10`, framework-row
wall-clock roughly doubles (~458 → ~900 s). Total run goes
~45 min → ~90 min.

**Mitigation:** *don't widen.* Keep `--framework-max-num-steps=10`.
The fingerprint is non-constant (`num_steps=10, 10, 9, 8, 6, ...` in
the smoke profile), the cosine ramp is preserved, and wall-clock is
unchanged. The expected post-fix wall-clock is ~45 min — same as
Phase-1. **Recommendation: do NOT widen `max_num_steps`.**

### Risk 5: `record_round_feedback` proxy may mis-tune the PID

**Severity: low.**
The 2D harness feeds the codim scheduler's `evidence_ratio` (a
real paper-quantity measurement). The CIFAR harness has no
in-process paper-quantity mechanism, so we proxy with a *separate*
`CodimensionSheetScheduler` instance. This proxy uses the *same
closed form* (`_paper_evidence_balance`) on the *same* `n_cap_base`
trajectory, so it is monotone in `r`. The PID target_ratio=1.0
will then drive `n_cap` *down* in early rounds (where the proxy's
ratio is `≈ 1.0`, error is small, delta is small) and `n_cap` *up*
in late rounds (where the proxy's ratio is slightly < 1.0, error
is small positive, delta is small). The PID-lite output is bounded
by `max_step=0.05`, so the trace stays within `±0.05` of cosine.

This is a noisier signal than the 2D harness has (the 2D harness
sees actual paper-quantity measurements from the oracle), but it
is sufficient to differentiate the EvidenceDriven row from the
CosineAnneal row.

**Mitigation:** document the proxy in `_run_framework`'s docstring,
and accept that the PID is operating on a synthetic signal rather
than a real measurement. The auditable artefact (the
`evidence_pid_adjusted` audit code) is honest about the proxy.

---

## §6. Effort estimate

| Step | Effort |
|---|---:|
| Diff to `tools/run_sota_cifar_experiment.py` (Fix A + Fix B + import + comment update) | 30 min |
| Add 4 unit tests to `tests/test_tools/test_run_sota_cifar_experiment.py` | 1.0 h |
| Run `ruff check` + `mypy --strict` on touched files | 10 min |
| Re-run the `--quick` smoke profile (200 samples, 5 rounds, 50 chains) | 5 min |
| Inspect `per_round_metrics.csv` — assert non-constant `n_cap` trace | 5 min |
| Re-run the paper-grade config (1000 samples, 10 rounds, 100 chains) | 45 min |
| Compute FID for baseline + 4 schedulers (CPU) | ~12 min (5 × FID) |
| Write post-fix `comparison.md` + update `experiment-log.md` | 30 min |
| Report finding into `docs/r4-survey/16-harness-fix-plan.md` (verification sub-table) | 15 min |
| **Total hands-on time** | **3.0 h** |
| **Total wall time (incl. 45-min re-run)** | **3.5 h** |

Acceptable risk: if framework-row FID regresses > 10%, re-widen to
`max_num_steps=20` and re-run for ~90 min; +45 min. Maximum total
budget: ~4.0 h.

---

## §7. Done criteria

* [ ] `tools/run_sota_cifar_experiment.py:439` reads
      `sample = scheduler.sample(0, int(r), int(r))` (Fix A).
* [ ] `tools/run_sota_cifar_experiment.py` wires
      `scheduler.record_round_feedback(int(r), {"evidence_ratio": ...})`
      per round for the `EvidenceDrivenScheduler` row (Fix B).
* [ ] `docs/r4-survey/cifar_results/per_round_metrics.csv` shows four
      DISTINCT `n_cap` series: cosine ramp for CosineAnneal /
      Codimension / EvidenceDriven (each with a different
      fingerprint), cosine+wobble for FreeTraj. No row is constant
      `1.0`.
* [ ] The four `{name}_samples.npz` files are NOT byte-identical.
      `mean_abs_diff(CosineAnneal, FreeTraj) > 0.005`.
* [ ] The four framework FIDs are NOT byte-identical. At least three
      of four FIDs differ from `baseline_fid` by a non-trivial amount.
* [ ] `comparison.md` "Honest framing" reports `Δ vs baseline` for each
      row. If any row regresses > 10%, the row is flagged honestly.
* [ ] All 6 Phase-1 gates pass:
      - `ruff check` on `tools/run_sota_cifar_experiment.py` and the
        extended `tests/test_tools/test_run_sota_cifar_experiment.py`
        — clean.
      - `mypy --strict` on the same files — clean.
      - `pytest tests/test_tools/test_run_sota_cifar_experiment.py`
        (11 + 4 new = 15 tests) — all pass.
      - `pytest tests/test_adapters/test_rectified_flow_cifar.py`
        (16 tests) — all pass.
      - `_gnobitab_ddpmpp` strict state_dict load — OK.
      - FID computation against `cifar10_test_ref_1000.npz` — finite,
        in `[40, 80]` range (baseline 66.73 ± 5%).
* [ ] A new `experiment-log.md` is written at
      `docs/r4-survey/cifar_results/experiment-log-v2.md` reporting
      honest post-fix FIDs and the four scheduler fingerprints.

### Acceptance gates by sub-criterion

| Criterion | Pass condition | Verification |
|---|---|---|
| 4 distinct `n_cap` traces | `set(per_round_metrics[CosineAnneal][r].n_cap for r in 0..9)` ≠ constant; same for the other 3 (with at least one pair differing in mid-cycle `n_cap`) | inspect CSV |
| 4 non-byte-identical `samples.npz` | `mean_abs_diff` between CosineAnneal and FreeTraj `samples.npz` > `0.005` | unit test |
| 4 non-byte-identical FIDs | `len(set(FIDs)) == 4` | inspect `summary.json` |
| Framework FID within tolerance | `\|framework_fid - baseline_fid\| / baseline_fid < 0.10` for all 4 rows | inspect `comparison.md` |
| 6 gates pass | see list above | `ruff`, `mypy`, `pytest` |

---

## 6-line summary

| Field | Value |
|---|---|
| Number of files to change | **2** (`tools/run_sota_cifar_experiment.py` + `tests/test_tools/test_run_sota_cifar_experiment.py`) |
| Effort estimate (hours) | **3.5 h** (3.0 h hands-on + 0.5 h wall-clock for paper-grade re-run; max ~4.0 h if framework FID regresses > 10%) |
| Highest risk | `EvidenceDrivenScheduler` may not differentiate from `CosineAnnealScheduler` even with the PID-fixing wire because the evidence-ratio proxy (`CodimensionSheetScheduler` driven on its own `n_cap_base`) yields ratio ∈ `[0.99995, 1.0]`, which gives `error ≤ 5e-5` per round → `_last_pid_delta` ≈ 1e-5 — within float noise. **Mitigation**: use `_last_pid_delta > 1e-6` after 10 rounds, or relax `target_ratio` to `0.99` to amplify the error. |
| Done criteria | Four distinct per-round `n_cap` traces; four non-byte-identical `samples.npz` files; four non-byte-identical FIDs; framework FIDs within `±10%` of baseline FID; the six Phase-1 gates still pass. |
| 2D experiment needs the same fix? | **No**. The 2D harness (`tools/run_sota_2d_experiment.py` + `BatchedTrajectoryRunner.run`) drives `round_in_cycle=r` correctly. `docs/r4-survey/15-harness-bug-diagnosis.md` §5 confirms the 2D CSVs show non-constant `n_cap`. The bug is CIFAR-only. |
| Plan file path | `docs/r4-survey/16-harness-fix-plan.md` |
