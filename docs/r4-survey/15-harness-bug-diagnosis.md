# CIFAR harness — n_cap=1.0 root-cause diagnosis

> **Author:** Agent D (harness-bug-diagnosis subagent)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Status:** read-only diagnosis; no code changes in this phase.

## §1. Per-scheduler `n_cap` values (from `per_round_metrics.csv`)

`docs/r4-survey/cifar_results/per_round_metrics.csv` (verbatim summary):

| scheduler | r=0 | r=1 | r=2 | r=3 | r=4 | r=5 | r=6 | r=7 | r=8 | r=9 | num_steps | evidence_ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CosineAnnealScheduler | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 10 | (empty) |
| CodimensionSheetScheduler | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 10 | 1.0 |
| EvidenceDrivenScheduler | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 10 | (empty) |
| FreeTrajScheduler | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 10 | (empty) |

`num_steps` is `max(1, round(n_cap * framework_max_num_steps))` per
`tools/run_sota_cifar_experiment.py:441`. With `framework_max_num_steps=10`
and `n_cap=1.0` for every row, the harness collapses to a single
10-step Euler trajectory every round (and every scheduler).

For reference, the 2D experiment's
`docs/r4-survey/two_moons_CosineAnnealScheduler_seed0.csv` shows the
expected cosine ramp across 20 rounds: `1.0, 0.99, 0.94, 0.89, ...,
0.06, 0.05` — i.e. `n_cap` is clearly *not* stuck at 1.0 in the 2D
harness. The CIFAR-side value is therefore a harness-level defect, not
a scheduler defect.

## §2. Construction parameters (from the script)

`tools/run_sota_cifar_experiment.py:169-200` (`build_scheduler`):

| scheduler | constructor call | rounds | n_min | n_max | other knobs |
|---|---|---:|---:|---:|---|
| CosineAnnealScheduler | `default_cosine_scheduler(cycle_length=10)` | 10 | 0.0 (default) | 1.0 (default) | schedule_family default `"cosine_no_restart"` |
| CodimensionSheetScheduler | `CodimensionSheetScheduler(cycle_length=10, n_min=0.0, n_max=1.0, eps_implicit=0.05)` | 10 | 0.0 | 1.0 | `eps_implicit=0.05` |
| EvidenceDrivenScheduler | `EvidenceDrivenScheduler(config=_build_cosine_schedule_config(10), kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0, k_eps=0.5, eps_implicit_base=0.05)` | 10 | 0.0 | 1.0 | PID-lite (`kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0`), `k_eps=0.5`, `eps_implicit_base=0.05` |
| FreeTrajScheduler | `FreeTrajScheduler(config=_build_cosine_schedule_config(10), trajectory_amplitude=0.05, trajectory_period=4)` | 10 | 0.0 | 1.0 | `trajectory_amplitude=0.05`, `trajectory_period=4` |

The `_build_cosine_schedule_config` helper (lines 141-166) builds a
frozen `CosineScheduleConfig(schedule_family="cosine_no_restart",
cycle_length=10, n_min=0.0, n_max=1.0)`.

Note: `n_min=0.0`, `n_max=1.0` is the *correct* envelope for a cosine
ramp that should produce `n_cap ∈ [0, 1]`. The PID's `max_step=0.05` is
the *correct* cap on a per-round shift. Nothing in the *construction*
parameters forces `n_cap=1.0` for every round; the construction
parameters are sane.

The mapping from `n_cap` to `num_steps`
(`tools/run_sota_cifar_experiment.py:441`):

```
num_steps = max(1, int(round(n_cap * float(max_num_steps))))
```

is also sane in isolation: it takes `n_cap ∈ [0, 1]` and maps it to
`num_steps ∈ [1, max_num_steps]`. The defect is that *the input to
this mapping is always 1.0*, not the mapping itself.

## §3. Root cause analysis (what is wrong and why)

### The bug

`tools/run_sota_cifar_experiment.py:439` (inside `_run_framework`):

```python
for r in range(int(n_rounds)):
    sample = scheduler.sample(0, 0, int(r))   # <-- BUG: 2nd arg is 0, not r
    n_cap = float(sample.n_cap)
    num_steps = max(1, int(round(n_cap * float(max_num_steps))))
```

The second positional argument to `SchedulerProtocol.sample` is
`round_in_cycle` — the index that drives the cosine ramp and the
PID/substep accumulators. The script passes the literal `0` for every
iteration and forwards the loop variable `r` as the third argument
(`target_round`, a *provenance* field, not the schedule driver).

Every implementation keys its `n_cap` computation on `round_in_cycle`:

* `CosineAnnealScheduler.sample`
  (`adaptive_reflow/algorithm/scheduler/_core.py:363-398`) calls
  `n_cap_for_round(self._config, round_in_cycle)` which evaluates
  `u_r = r / (L - 1)` and the closed form
  `n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2`.
  With `round_in_cycle=0`, `u_r=0`, so
  `n_cap = n_min + (n_max - n_min) * 1.0 = n_max = 1.0` regardless of
  `cycle_length`.

* `CodimensionSheetScheduler.sample`
  (`adaptive_reflow/algorithm/scheduler/_core.py:2636-2769`) builds
  `n_cap_base` from its underlying cosine base (`u_r` derived from
  `round_in_cycle`), then maps to `[n_min, n_max]`. With
  `round_in_cycle=0` it returns `n_min + (n_max - n_min) * n_cap_base = 1.0`.
  `evidence_ratio` is computed inside `sample()` from
  `_paper_evidence_balance(n_cap_base=1.0, eps_implicit=0.05, ...)`
  which yields `ratio=1.0` for `n_cap_base=1.0` (sheet dominates).

* `EvidenceDrivenScheduler.sample`
  (`adaptive_reflow/algorithm/scheduler/evidence_driven.py:315-392`)
  delegates to the wrapped cosine (`n_cap_for_round(config,
  round_in_cycle)`), then adds `_last_pid_delta` (clipped to
  `[0, 1]`). With `round_in_cycle=0` the wrapped cosine returns
  `1.0`; `_last_pid_delta=0.0` (no feedback has been recorded — the
  harness never calls `record_round_feedback`), so `adjusted=1.0`.

* `FreeTrajScheduler.sample`
  (`adaptive_reflow/algorithm/scheduler/freetraj.py:160-208`) delegates
  to the wrapped cosine, then adds
  `amplitude * sin(2*pi*progress)`. With `round_in_cycle=0`,
  `progress = 0 % 4 / 4 = 0.0`, `substep = 0.05 * sin(0) = 0.0`,
  `adjusted = 1.0 + 0.0 = 1.0`.

So *every* scheduler is forced to round `0` of its cycle on every
call, and the only thing that varies is the (cosmetic) `audit_codes`
and `evidence_ratio` field on the `ScheduleSample`. The PID and
substep controllers are never advanced because (a) their inputs
(`round_in_cycle`) don't change, and (b) the harness never calls
`record_round_feedback` to feed the per-round metrics back.

The downstream mapping
`num_steps = max(1, round(n_cap * max_num_steps))` then collapses to
`num_steps = max_num_steps = 10` for every scheduler and every round,
so each scheduler's `{name}_samples.npz` is byte-identical to the
baseline row (and to each other).

### Why the symptom is so uniform

All four schedulers are *wrappers* around a cosine-derived baseline.
The wrapper offsets (PID delta, FreeTraj substep) are deliberately
*small* (`|delta| <= max_step=0.05`, `|substep| <= 0.05`). If the
bug had only affected one scheduler, the symptom would still be
`n_cap≈1.0` everywhere because (a) `round_in_cycle=0` makes the
baseline `1.0`, and (b) the wrapper offsets are at most ±0.05 and
zero in the no-feedback / default-progress case. The defect is
single-point but its footprint is wide because every scheduler
shares the same cosine core.

### What it is *not*

* **Not** a scheduler construction bug. Construction params
  (`n_min=0.0, n_max=1.0, cycle_length=10`, etc.) are the canonical
  ones — they would produce a `1.0 → 0.0` cosine ramp if
  `round_in_cycle` were wired correctly.
* **Not** a `n_cap_for_round` math bug. The closed form is correct;
  it just always receives `round_in_cycle=0`.
* **Not** a framework-adapter wrapping bug. The
  `_gnobitab_ddpmpp.py` adapter is the UNet forward path; it doesn't
  see `n_cap` at all in this harness. The harness consumes `n_cap`
  via `batched_inference(num_steps=int(num_steps), ...)` — a
  `num_steps`-keyed contract, not an `n_cap`-keyed contract.
* **Not** a `num_steps = n_cap * max_num_steps` mapping bug. The
  mapping is correct; it is fed a constant `1.0` because of the
  `round_in_cycle` wiring bug.

## §4. Expected `n_cap` behavior (per scheduler)

If `round_in_cycle` were wired correctly (`scheduler.sample(0, r, r)`),
the per-scheduler traces would be:

### CosineAnnealScheduler

Pure cosine ramp from `n_max=1.0` (round 0) to `n_min=0.0` (round 9).
Closed form
(`adaptive_reflow/schedule/cosine.py:144-233`,
`_core.py:363-398`):

```
n_cap(r) = 0.0 + (1.0 - 0.0) * (1 + cos(pi * r/9)) / 2
        = 0.5 * (1 + cos(pi * r/9))
```

Expected per-round values (`cosine_no_restart`):

```
r=0 → 1.000
r=1 → 0.9698
r=2 → 0.8830
r=3 → 0.7500
r=4 → 0.5868
r=5 → 0.4132
r=6 → 0.2500
r=7 → 0.1170
r=8 → 0.0302
r=9 → 0.000
```

(Matches the 2D experiment's `1.0, 0.99, 0.94, 0.89, ...` trace at
`cycle_length=20`.)

### CodimensionSheetScheduler

`n_cap = n_min + (n_max - n_min) * n_cap_base(r)`
(`_core.py:2713-2718`) where `n_cap_base(r)` is the cosine ramp above
scaled into `[0, 1]`. So the *same* cosine curve, but the
`evidence_ratio` reported on the sample *does* depend on the
paper-quantity closed form
(`_core.py:2733-2741` calling `_paper_evidence_balance`):

```
sheet = max(n_cap_base, eps_implicit)              # eps^{+1} (Lemma 2)
cell  = (1 - n_cap_base)**2 * eps_implicit**2      # eps^{+2} (Lemma 3)
ratio = sheet / (sheet + cell)
```

With `eps_implicit=0.05`, the ratio sweeps from
`1.0` at `r=0` (sheet dominates, `n_cap_base=1.0`) down to
`0.05/(0.05 + 0.95**2 * 0.05**2) ≈ 0.99997` at `r=9` and *rises
again toward 1* as `n_cap_base → 0` (sheet still dominates because
`eps_implicit=0.05` floors the sheet term). The current CSV shows
`evidence_ratio=1.0` for every round — the helper is being driven at
`n_cap_base=1.0` every time because `round_in_cycle=0`.

### EvidenceDrivenScheduler

`n_cap = cosine_base(r) + delta`
(`evidence_driven.py:338-346`), where
`delta ∈ [-max_step, +max_step] = [-0.05, +0.05]`. PID-lite
(`evidence_driven.py:103-184`) is updated by
`record_round_feedback(round_in_cycle, metrics)`, which the harness
*never calls*. So `_last_pid_delta=0.0` and
`n_cap == cosine_base(r)` clamped to `[0, 1]`. Expected trace: cosine
curve with a constant `±0.05` slack — the *direction* of the slack
is what would distinguish this row from the pure cosine row once
feedback is wired. As observed, the row tracks cosine exactly.

### FreeTrajScheduler

`n_cap = cosine_base(r) + amplitude * sin(2*pi*progress)`
(`freetraj.py:185`), where `progress = (r % period) / period =
(r % 4) / 4`. So at `period=4`:

```
progress sequence: 0/4, 1/4, 2/4, 3/4, 0/4, 1/4, ...
sin(2*pi*progress): 0, +1, 0, -1, 0, +1, 0, -1, 0, ...
substep (±0.05):   0, +0.05, 0, -0.05, 0, +0.05, 0, -0.05, 0, ...
```

Expected `n_cap` trace: cosine curve with a small ±0.05 sinusoidal
"wobble" indexed by `r % 4`. Currently the script reports `1.0`
because `r=0` always evaluates `progress=0` and `substep=0`.

## §5. Differences from the 2D experiment

The 2D harness (`tools/run_sota_2d_experiment.py:390-434`,
`_drive_batched` → `BatchedTrajectoryRunner.run`) does *not* expose
the same bug for two structural reasons:

1. **The 2D harness drives `n_cap` as a fraction, not as a step-count
   multiplier.** `n_cap` enters the 2D adapter via
   `inject_noise(state, schedule_sample, ...)` and via
   `memory_fraction = 1 - n_cap` (the canonical
   `apply_restart_distribution` boundary). It does *not* feed
   `n_cap` into the ODE step count. So even if `n_cap` were stuck at
   `1.0`, the 2D experiment would still produce per-round variation
   because each round draws a fresh batch of endpoints and re-runs
   `solve_ode` against the *previous round's endpoint distribution*.
   The 2D CSVs confirm this: `w2` and `selection_ratio` move round by
   round even when `n_cap` is constant.

2. **The 2D runner passes `round_in_cycle=r` correctly.**
   `BatchedTrajectoryRunner.run` (see the `round_in_cycle=r` call
   inside the runner) advances `round_in_cycle` per iteration, so
   the cosine ramp and the wrapper offsets move normally across
   rounds. The 2D CSVs show `n_cap` sweeping from `1.0` at `r=0` to
   `0.05` at `r=19` (cosine) / `0.0` at `r=19` (PID-modulated) /
   `0.0` at `r=19` with periodic wobble (FreeTraj).

The CIFAR harness inlines its own per-round loop (it does not call
`BatchedTrajectoryRunner`), and the inline loop is the place where
`round_in_cycle` is hard-coded to `0`. So the bug is *CIFAR-only* in
the sense that it lives in `tools/run_sota_cifar_experiment.py` and
not in any shared runner; the 2D harness is unaffected.

A subtle secondary difference: the 2D harness *does* call
`record_round_feedback` on its `EvidenceDrivenScheduler` (via the
batched runner + selection evaluator), so the PID-lite controller
actually accumulates error across rounds. The CIFAR harness skips
this hook entirely, so even with the `round_in_cycle` fix
`EvidenceDrivenScheduler` would only differentiate from cosine if
the harness also wires `record_round_feedback`.

## §6. Recommended fix direction (no code yet)

Two issues are stacked in `_run_framework`; both should be fixed
together to make the framework-vs-baseline comparison carry
information.

### Fix A (single-line): pass the loop index as `round_in_cycle`

In `tools/run_sota_cifar_experiment.py:439`, replace

```python
sample = scheduler.sample(0, 0, int(r))
```

with

```python
sample = scheduler.sample(0, int(r), int(r))
```

This single change restores the cosine ramp and the FreeTraj
substep wobble for `CosineAnnealScheduler`, `CodimensionSheetScheduler`,
and `FreeTrajScheduler`. `EvidenceDrivenScheduler` would also track
the cosine ramp (its PID delta stays zero until Fix B is applied).

### Fix B (small wrapper): call `record_round_feedback` per round

To make `EvidenceDrivenScheduler` actually carry information,
compute the round's `selection_ratio` (or the codimension sheet's
`evidence_ratio`) and pass it via
`scheduler.record_round_feedback(int(r), {"evidence_ratio": ratio})`
between the `sample()` call and the `batched_inference()` call. This
is the analogue of the 2D harness's per-round feedback path.

### Fix C (config tuning, optional): widen `n_max` so `num_steps` saturates

If Fix A alone is too timid to differentiate the framework rows
(the framework rows would still integrate on the same step grid as
the baseline for early rounds where `n_cap≈1`), the harness can
widen `n_max` past `1.0` (e.g. `n_max=2.0`) so that
`round(n_cap * max_num_steps)` overshoots `max_num_steps` early and
narrows later. This produces a distinguishing fingerprint even
without chained state. The cosine family clips `n_cap` to `[0, 1]`
defensively, so this requires either widening the script's
`max_num_steps` mapping or relaxing the cosine clip. Lower priority
than Fix A / Fix B.

### Direction summary

The fix direction is *change the call site in
`tools/run_sota_cifar_experiment.py:439`* (pass the loop index as
`round_in_cycle`). The scheduler implementation is correct; the
construction parameters are correct; the `n_cap → num_steps` mapping
is correct; the new `_gnobitab_ddpmpp.py` adapter is correct. The
defect is a single hard-coded `0` where the loop variable `r` was
intended.