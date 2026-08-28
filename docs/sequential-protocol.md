# SequentialScheduler — chaining multiple `SchedulerProtocol` instances by round range

This page is the reference for the **P1-2 external** extension
[`SequentialScheduler`](../adaptive_reflow/algorithm/sequential.py) — a
`SchedulerProtocol` implementation that takes a list of
`(sub_scheduler, n_rounds)` pairs and routes round `r` to the
sub-scheduler at slot index `i` where `r` falls in
`[sum(n_rounds[:i]), sum(n_rounds[:i+1]))`. The construction is the
`adaptive_reflow` analog of PyTorch's
SequentialLR composite scheduler (PyTorch ≥ 2.0): build a piecewise
schedule by chaining deterministic sub-schedulers, each of which
drives a contiguous slice of the outer cycle.

The implementation lives at
[`adaptive_reflow/algorithm/sequential.py`](../adaptive_reflow/algorithm/sequential.py);
the per-round behaviour round-trip is pinned by
[`tests/test_algorithm/test_sequential.py`](../tests/test_algorithm/test_sequential.py);
the family is registered in
[`SCHEDULER_REGISTRY`](../adaptive_reflow/algorithm/scheduler.py) under
the key `"sequential"`.

## 1. The closed form

Let `L_i = slot.n_rounds` for slot `i` and let
`C_k = sum_{i=0..k-1} L_i` (the cumulative round offset). For round
`r` in `[0, sum_i L_i - 1]` the chain resolves to slot

```
i(r) = min { k : r < C_{k+1} }
```

and the chain's `n_cap(r)` is the slot's `n_cap(r - C_{i(r)})` — i.e.
the sub-scheduler observes its own **cycle-relative** round index, not
the chain-relative one. The companion `u_r` (`round_in_cycle /
(L - 1)`) and `family` strings are rewritten by the chain: the
returned `ScheduleSample.family` becomes
`"sequential[<i>]:<sub_family>"` and `schedule_hash` is the chain's
single frozen `config_hash`, so downstream consumers see one stable
identifier for the entire chain regardless of which slot is active.

The chain's `cycle_length()` returns `sum_i L_i` (the chain's total
length in rounds); the chain's `config_hash()` includes every
sub-scheduler's own `config_hash()` so two chains with the same shape
but different sub-schedulers produce distinct hashes.

## 2. Worked example — cosine for 8 rounds, then exponential for 4 rounds, then constant for 8 rounds

A common case is **coarse-to-fine** with three regimes:

1. rounds 0..7 — cosine annealing from `n_max = 1.0` down to `n_min = 0.1`
   (the canonical "explore then refine" envelope);
2. rounds 8..11 — exponential decay with `alpha = 0.3` (rapid refinement
   after the cosine ramp has done its work);
3. rounds 12..19 — constant at `n_cap = 0.05` (a low-noise "rest"
   plateau; the bounded noise floor still injects `sqrt(0.05)` per
   round so the algorithm does not freeze on the prior).

The chain is constructed as:

```python
from adaptive_reflow.algorithm.scheduler import (
    ConstantScheduler,
    ExponentialScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.sequential import SequentialScheduler

cosine = default_cosine_scheduler(cycle_length=8, n_min=0.1, n_max=1.0)
expo = ExponentialScheduler(cycle_length=4, n_max=1.0, alpha=0.3)
const = ConstantScheduler(cycle_length=8, n_cap=0.05)

chain = SequentialScheduler(
    schedulers=[(cosine, 8), (expo, 4), (const, 8)],
)
```

`chain.cycle_length()` returns `20` (the chain's total length).
Sampling round-by-round produces the trajectory tabulated below; the
slot index column shows which sub-scheduler is active, and the
`family` column shows the chain's rewritten `"sequential[<i>]:<sub>"`
identifier.

| `r` | slot | `n_cap(r)` (analytical)         | `family` (rewritten)       |
|----:|:-----:|:---------------------------------|:---------------------------|
|   0 | 0 (cosine)  | `0.1 + 0.5 * (1.0 - 0.1) * (1 - cos(0))` = `0.1` (sub-round 0) | `sequential[0]:cosine_no_restart` |
|   1 | 0 (cosine)  | `0.1 + 0.45 * (1 - cos(pi / 7))` ≈ `0.1704` | `sequential[0]:cosine_no_restart` |
|   7 | 0 (cosine)  | `0.1 + 0.45 * (1 - cos(pi))` = `1.0` (terminal) | `sequential[0]:cosine_no_restart` |
|   8 | 1 (expo)    | `1.0 * exp(-0.3 * 0)` = `1.0` (sub-round 0)    | `sequential[1]:exponential`       |
|   9 | 1 (expo)    | `1.0 * exp(-0.3 * 1)` ≈ `0.7408`               | `sequential[1]:exponential`       |
|  11 | 1 (expo)    | `1.0 * exp(-0.3 * 3)` ≈ `0.4066`               | `sequential[1]:exponential`       |
|  12 | 2 (const)   | `0.05` (every round in slot 2)                 | `sequential[2]:constant`          |
|  19 | 2 (const)   | `0.05`                                         | `sequential[2]:constant`          |

Round 0 of the chain maps to sub-round 0 of the cosine slot, which
returns `n_min = 0.1` (the cosine starts at its minimum and climbs
to `n_max` over its 8-round cycle). Round 7 is the cosine's terminal
round (`n_cap = 1.0`); round 8 begins the exponential slot; round 12
enters the constant slot. The chain's per-round behaviour is
reproducible by replaying the same sub-scheduler in isolation —
`chain.sample(0, r, r)` returns the same `n_cap` as the active
sub-scheduler's `sample(0, sub_round, sub_round)`.

### Config round-trip

```python
cfg = chain.to_config()
assert cfg == {
    "family": "sequential",
    "total_rounds": 20,
    "slots": [
        {"scheduler": cosine.to_config(), "n_rounds": 8},
        {"scheduler": expo.to_config(),    "n_rounds": 4},
        {"scheduler": const.to_config(),  "n_rounds": 8},
    ],
}

rebuilt = SequentialScheduler.from_config(cfg)
assert rebuilt.cycle_length() == 20
assert rebuilt.config_hash() == chain.config_hash()
```

The round-trip is byte-identical at the `config_hash` level; the
per-round `n_cap` trajectory is byte-identical as well (verified by
`test_sequential_round_trip_trajectory_identical`).

## 3. When to use a chain vs a single composite scheduler

Use `SequentialScheduler` when:

* you want **two or more distinct schedule shapes** in sequence (e.g.
  cosine-then-constant, or linear-then-cosine for a ramp-up +
  anneal pattern);
* each phase has a known **fixed budget** (the slot's
  `n_rounds` is part of the chain's `config_hash`, so two chains with
  different budgets hash differently);
* you need to **reuse a single `SchedulerProtocol` implementation**
  in two non-contiguous ranges (slot 0 and slot 2 use the same
  sub-scheduler class with different knobs).

Do **not** use `SequentialScheduler` when:

* the desired shape can be expressed by a **single**
  `SchedulerProtocol` implementation (e.g. a custom
  `ConvergenceAdaptiveScheduler` with a different `base` or
  `shift_max`). The single-scheduler form is cheaper to audit (one
  `config_hash` rather than a chain of three) and one fewer layer of
  indirection to reason about.
* the round budget per phase is **not known at construction time**.
  `SequentialScheduler` requires a positive integer per slot and
  refuses to dispatch on `round_in_cycle >= total_rounds` (raises
  `ValueError` at the `sample` boundary). Adaptive phasing is the job
  of `ConvergenceAdaptiveScheduler`, not of `SequentialScheduler`.

## 4. Common failure modes

* **Empty slot list.** `SequentialScheduler(schedulers=[])` raises
  `ValueError`; the chain must have at least one slot.
* **Zero / negative `n_rounds`.** Each slot's `n_rounds` is
  validated to be an `int >= 1`; `SequentialScheduler(schedulers=[(c, 0)])`
  raises `ValueError`.
* **Out-of-range round.** `chain.sample(0, total_rounds, total_rounds)`
  raises `ValueError("round_in_cycle must be in [0, total_rounds - 1]")`.
  Set the engine's outer cycle length to match `chain.cycle_length()`
  when wiring through `ReInferenceConfig`.
* **Non-`SchedulerProtocol` sub-scheduler.** A sub-scheduler that is
  missing one of the eight required `SchedulerProtocol` methods
  (`sample`, `cycle_length`, `schedule_family`, `config_hash`, `reset`,
  `inject_noise`, `to_config`, `from_config`) raises `TypeError` at
  construction time, not at sample time.
* **Nested chains.** Nested `SequentialScheduler` instances are
  supported — pass a `SequentialScheduler` as a slot's scheduler and
  the outer chain's `from_config` will dispatch the nested chain
  through `SequentialScheduler.from_config` (no recursion through
  the outer `build_scheduler_from_config`). The inner chain's
  `inject_noise` and `record_round_feedback` calls fall through to
  the first slot of the inner chain (documented fallback for the
  edge case where the per-round `computed_at_round` does not resolve
  into any slot).

## 5. Protocol surface

`SequentialScheduler` conforms to
[`SchedulerProtocol`](../adaptive_reflow/algorithm/scheduler.py). The
eight required methods are implemented as follows:

| Method | Behaviour |
| --- | --- |
| `sample(outer_cycle_id, round_in_cycle, target_round)` | Resolve slot; delegate to sub-scheduler with sub-round index; rewrite `family` to `"sequential[<i>]:<sub_family>"`; freeze `schedule_hash` to the chain-level hash. |
| `cycle_length()` | `sum(slot.n_rounds for slot in slots)` |
| `schedule_family()` | `"sequential"` |
| `config_hash()` | `hash_artifact({slots, total_rounds})` including every sub-scheduler's own `config_hash()`. |
| `reset()` | Reset every sub-scheduler; drop cached `last_sample`. |
| `record_round_feedback(round_in_cycle, metrics)` | Resolve slot; forward `metrics` to active sub-scheduler. Falls back to no-op when `round_in_cycle` is out of range. |
| `inject_noise(state, schedule_sample, *, generator)` | Resolve active sub-scheduler from `schedule_sample.computed_at_round`; delegate. Falls back to the first slot's `inject_noise` when no slot matches. |
| `to_config()` / `from_config()` | Round-trip the chain through the `SCHEDULER_REGISTRY["sequential"]` slot; nested chains round-trip via the dedicated `SequentialScheduler.from_config` constructor. |

## 6. References

* [`adaptive_reflow/algorithm/sequential.py`](../adaptive_reflow/algorithm/sequential.py)
  — the implementation (220+ lines incl. the dispatcher).
* [`adaptive_reflow/algorithm/scheduler.py`](../adaptive_reflow/algorithm/scheduler.py)
  — the `SchedulerProtocol` definition and the `SCHEDULER_REGISTRY`
  entry under `"sequential"`.
* [`tests/test_algorithm/test_sequential.py`](../tests/test_algorithm/test_sequential.py)
  — the regression suite (16+ tests covering construction,
  trajectory, reset, noise injection, config round-trip, nested
  chains, and dispatcher routing).
* [`docs/adr/0012-schedule-family-survey.md`](adr/0012-schedule-family-survey.md)
  — the ADR that surveys schedule families and accepts
  `SequentialScheduler` as the multi-phase composition primitive.
* [`docs/distinguishing-from-reflow.md`](distinguishing-from-reflow.md)
  — the inference-time framing (chains operate at sample time, not
  training time; PyTorch's SequentialLR is the closest published
  analog).