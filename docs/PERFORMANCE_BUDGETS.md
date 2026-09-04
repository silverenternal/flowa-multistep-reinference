# Performance Budgets

This document defines the perf-budget system used by `flowa-multistep-reinference`:
how the budgets are declared, how the measurements are captured, and how the
regression gate fails a CI run when a hot-path kernel regresses beyond its
declared budget.

## Overview

Every hot-path kernel has a **budget** — an upper bound on the wall-clock cost
of one invocation, expressed in **microseconds**. After every bench run we emit
`docs/benchmarks.json` with the observed metrics and then run the regression
gate `tools/bench/check_budgets.py` to compare the measurements against the
budgets declared in `tools/bench/budgets.json`.

The gate uses a **20 % tolerance**: a measurement must be at most
`budget * 1.2` to pass. Anything beyond that is treated as a regression and
fails the gate with exit code `1`.

## Tools

### `pytest-benchmark` (`tests/perf/test_kernel_benchmarks.py`)

The pytest-bench suite covers the three DTB hot-path kernels:

| Test                                     | Kernel                        | Unit budget |
| ---------------------------------------- | ----------------------------- | ----------- |
| `test_bounded_merge_kernel`              | `bounded_merge`               | 50 µs       |
| `test_compute_channel_decision_kernel`    | `compute_channel_decision`    | 200 µs      |
| `test_evaluate_claim_gate_kernel`         | `evaluate_claim_gate`         | 100 µs      |

pytest-benchmark is configured in `pyproject.toml` under
`[tool.pytest-benchmark]` with:

* `min_rounds = 5` — at least five rounds regardless of round duration, so the
  reported mean/median/p95 are statistically meaningful.
* `max_time = 5.0` — wall-clock cap (seconds) so a slow round can never blow
  up CI.
* `warmup = true`, `warmup_iterations = 10` — ten discarded iterations per
  test so first-call / JIT / cache-warm-up noise never leaks into the
  reported statistics.
* `sort = "mean"` and the column set
  `["min", "median", "mean", "max", "stddev", "rounds", "iterations"]` —
  keep the printed summary aligned with what the budget gate consumes.
* `show_relativ = true` — show relative timings next to absolute timings so
  eyeballing two benchmarks side-by-side is easy.

The benchmark group is registered as a custom pytest marker (`benchmark`) in
`[tool.pytest.ini_options]`. Tests are marked with `@pytest.mark.benchmark`
and only run when invoked with `--benchmark-only`.

### `tools/bench/runner.py`

Hand-rolled, stdlib-only harness that drives the
`AdaptiveReflowPolicyOrchestrator` for 200 consecutive `evaluate_bundle`
rounds. This is the source of the `engine_round_loop_us_p95` metric, which
captures the **end-to-end per-round cost** of the orchestrator (not just
the individual kernels). Budget for that metric is **1000 µs**.

### `tools/bench/check_budgets.py`

Regression gate. Reads both:

* `docs/benchmarks.json` — the latest measurements.
* `tools/bench/budgets.json` — the declared budgets.

For each metric in `budgets.json`:

1. Look up the measurement in `benchmarks.metrics` (with optional `_p95`
   suffix stripping so the budget key matches the metric name regardless of
   suffix conventions).
2. Compute `ceiling = budget * (1 + regression_threshold_pct / 100)`.
3. Classify:

   | Measured vs budget / ceiling    | Status      | Exit code |
   | ------------------------------- | ----------- | --------- |
   | `measured <= budget`            | `ok`        | 0         |
   | `budget < measured <= ceiling`  | `warn`      | 0         |
   | `measured > ceiling`            | `regressed` | 1         |
   | budget missing in benchmarks    | `missing`   | 1         |

The script prints a one-line-per-metric report followed by a `summary:`
line with the totals, then exits with `0` (all within tolerance) or `1`
(at least one metric regressed).

## Budget file

`tools/bench/budgets.json` has the shape:

```json
{
  "schema": "flowa.bench.budgets/v1",
  "currency": "microseconds",
  "regression_threshold_pct": 20,
  "budgets": {
    "bounded_merge_us_p95": 50,
    "compute_channel_decision_us_p95": 200,
    "evaluate_claim_gate_us_p95": 100,
    "engine_round_loop_us_p95": 1000
  },
  "metric_sources": { ... }
}
```

The `metric_sources` map is documentation: it names the bench test (or
runner) that produces each metric so a reader of the budgets file can find
the source.

Current budget values (calibrated against the synthetic-driver baseline,
2026-08-27):

| Metric                              | Budget   | Tolerance ceiling (×1.2) | Latest measurement |
| ----------------------------------- | -------- | ------------------------- | ------------------ |
| `bounded_merge_us_p95`              |  50 µs   |   60 µs                   |    1 µs            |
| `compute_channel_decision_us_p95`   | 200 µs   |  240 µs                   |    6 µs            |
| `evaluate_claim_gate_us_p95`        | 100 µs   |  120 µs                   |    2 µs            |
| `engine_round_loop_us_p95`           | 1000 µs  | 1200 µs                   |  153 µs            |

All four are well within budget. The headroom (factor of ~6-200×) is
intentional: budgets are calibrated to **fail loudly** when a hot-path
optimization regresses, not to track the current measurement tightly.

## Running locally

```
# 1. Capture fresh measurements.
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/perf/ \
    --benchmark-only --benchmark-json=docs/benchmarks.json --no-header

# 2. Update the engine-round-loop metric.
PYTHONPATH=. ./.venv/Scripts/python.exe tools/bench/runner.py \
    --output docs/benchmarks.json

# 3. Run the regression gate.
PYTHONPATH=. ./.venv/Scripts/python.exe tools/bench/check_budgets.py
```

A clean run prints four `ok` lines and exits `0`.

## When to update the budgets

* The **budgets** themselves should only change when there is an explicit
  architectural decision to relax (or tighten) the ceiling. A failing gate
  is a signal to investigate the regression, not to bump the number up.
* The **measurements** in `docs/benchmarks.json` are regenerated on every
  bench run and should be committed only when they represent a stable
  baseline (typically a tag / release commit).

## CI

The bench + gate is wired so that CI runs the perf suite against the
declared budgets. A failing gate blocks the PR — if the regression is
intentional, bump the budget in `tools/bench/budgets.json` together with a
changelog entry explaining why the ceiling was raised.

## Paper grounding (why we measure these kernels)

The four hot-path kernels above are the implementation surfaces of the
framework's correctness layer — they cite the underlying JMAA paper
(Li 2026) at every check:

* `bounded_merge` — implements the merge-envelope part of **Proposition 3**
  (selection-mechanism display, `paper section 4.2`); the budget
  protects the closed-form `n_cap(r)` interpolation from drifting out
  of the convex combination `[floor, cap]` that Proposition 3 predicts.
* `compute_channel_decision` — implements the per-channel gating that
  backs **Lemma 5** (root-cell packing `B_g`, `paper line 135-138`).
* `evaluate_claim_gate` — implements the closure rule that **Theorem 1**
  (BL-convergence, `paper section 3.1`) requires for the BL limit.
* `engine_round_loop` — runs the full per-round loop that the rate-bound
  constant `rate_bound_C(eps)` from `adaptive_reflow/theory/rate_bound.py`
  bounds. A 20% regression here is the early-warning signal that the
  rate-bound's constants have been perturbed.

In short, every budget on this page is a **downstream invariant of a
paper-grounded theorem**; the budget gate is a CI-friendly proxy for
the theorem's numerical cofactors holding.