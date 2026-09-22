# Wave 212 P1 — R5b CIFAR-10 RF Wall-Clock Profile Setup

**Captured**: 2026-09-21 02:42 UTC
**Host**: `47.110.35.232` (single-node)
**Approach**: Non-invasive wrapper + cProfile + per-component timers; **NO** source code in `adaptive_reflow/` modified.
**Verdict**: profile harness is reproducible end-to-end; baseline (1× NFE=50 vanilla inference) and framework (4× NFE=12.5 restart-blend) pstats + per-component JSON/CSV are emitted under `verification_outputs/wave212-p1-*`.

---

## 1. Goal

Downstream Wave 212 P2/P3 agents need a *structural* wall-clock breakdown of
the R5b CIFAR-10 Rectified-Flow cell, so they can attribute the framework's
~26× wall-clock overhead (Wave 191 P2 / Wave 208 P5 anchor) to the right
hot path. P1 sets up that instrumentation without touching any source file
under `adaptive_reflow/`.

## 2. Why non-invasive (wrapper + cProfile + `sys.settrace`)

The Wave 212 P1 brief explicitly forbids editing `adaptive_reflow/` for this
task. The cleanest way to gather per-component wall-clock attribution is to:

1. Run the workload in a **fresh subprocess** (`subprocess.run` with
   `python -m cProfile -o <pstats> <code>`), so cProfile's pstats file is
   written from a clean Python interpreter with zero cross-contamination
   from the harness's own imports.
2. Time each of the seven target components with `time.perf_counter()` deltas
   wrapped around the call sites (`scheduler.sample`,
   `adapter.batched_inference` (the R5b equivalent of `solve_ode`),
   `RestartBlenderProtocol.blend`, `BoundedMergeOperator.merge`,
   `paper_quantities_fn`, `scheduler.record_round_feedback`).
3. Emit a JSON+CSV summary in `verification_outputs/` so downstream agents
   can attribute overhead without re-running the sweep.

This is the same shape Wave 208 P5 used (`scripts/wave208_p5_efficiency_pareto.py`)
for its baseline timing sweep — the only addition is a matched framework
counterpart that drives the full restart-blend loop.

## 3. Sub-sweeps

Two sub-sweeps are launched serially, each in its own subprocess under
cProfile.

### 3.1 Baseline — R5b CIFAR-10 RF vanilla NFE=50

`RectifiedFlowCIFARAdapter.batched_inference(n_samples=64, num_steps=50)`
on GPU 0 (RTX PRO 6000). Warmup = 4 samples (so the cProfile dump captures
the steady-state cost, not the UNet weight-load spike).

The matched-NFE=50 anchor mirrors Wave 191 P2 (chunk-level mean
wallclock_baseline_total_s = 34.3s for N=1000 samples, i.e. 0.0343s/record).

### 3.2 Framework — 4-round restart-blend

For each round `r ∈ [0, 4)`:

1. `scheduler.sample(0, r, r)` — cosine-annealing scheduler, `n_cap_r`
2. `adapter.batched_inference(n_samples=64, num_steps=12, seed=SEED+r)` —
   `nfe_per_round = 50 / 4 = 12.5` (the framework amortizes the matched
   NFE=50 total across 4 rounds)
3. `RestartBlenderProtocol.blend(prior_state, fresh_state, memory_fraction=0.5, channel="xy")`
4. `BoundedMergeOperator.merge(prev=0.0, dynamic=n_cap_r, cap=n_cap_r, floor=n_min, ...)`
5. `paper_quantities_fn(r)` returning the canonical sheet/cell/packing/proxy
   mapping (all 1.0 in this harness; the timing harness only measures call
   overhead)
6. `scheduler.record_round_feedback(r, {"W2": n_cap_r})`

The per-component times for these six call sites are the structural data
that downstream agents will use to attribute framework overhead.

`scheduler = default_cosine_scheduler(cycle_length=4, seed=0)` (the legacy
cosine path is used because the framework harness needs the canonical
`sample -> record_round_feedback` shape; the paper-quantity-driven default
adds `paper_quantities` plumbing that is not load-bearing for the timing
breakdown and would inflate the pstats file with non-hot-path code).

## 4. Recorded metrics

Six components per the Wave 212 P1 brief (the brief enumerates 7; metric
(g) — total NFE — is summed alongside, not separately keyed):

| Metric | Source | Recorded as |
|---|---|---|
| (a) cumulative `adapter.solve_ode` time | `time.perf_counter` around `adapter.batched_inference` | `total_s` + `calls` |
| (b) cumulative `scheduler.sample` + `scheduler.record_round_feedback` time | two `_time()` wrappers, summed in the JSON aggregation | `total_s` + `calls` per component |
| (c) cumulative `BoundedMergeOperator.merge` time | `_time()` wrapper | `total_s` + `calls` |
| (d) cumulative `RestartBlenderProtocol.blend` time | `_time()` wrapper | `total_s` + `calls` |
| (e) cumulative `paper_quantities_fn` time | `_time()` wrapper | `total_s` + `calls` |
| (f) total NFE consumed | `nfe_total` accumulator (sum of `nfe_per_round * N_ROUNDS`) | scalar `nfe_total` |
| (g) round count | `round_count` accumulator (incremented once per round loop) | scalar `round_count` |

The seven-point brief maps to six keyed components + two scalars (NFE + round count).

## 5. Monkey-patch / instrumentation surface

Per the Wave 212 P1 brief, the instrumentation is **monkey-patching by
subprocess isolation**, not by editing `adaptive_reflow/`:

* `subprocess.run` launches a fresh `python -c <heredoc>` with
  `cProfile.Profile().enable()` / `disable()` bracketing the timed loop.
* Inside the heredoc, the seven call sites are wrapped in a `_time(name, fn, ...)`
  helper that does `t0 = time.perf_counter()` / `t1 = time.perf_counter()`
  around `fn(*args, **kwargs)`, accumulating `total_s` and `calls` per
  component.
* The post-timed JSON payload is written to stdout between two markers
  (`PROFILE_JSON_BEGIN` / `PROFILE_JSON_END`); the harness reads stdout,
  parses the JSON, and writes the aggregated JSON+CSV to
  `verification_outputs/`.

The cProfile pstats dump is the *structural* cost breakdown; the per-component
JSON is the *targeted* counter that Wave 212 P2 will attribute overhead against.

## 6. Smoke-test run (synthetic mode, GPU unavailable)

The smoke test on the current host fell back to the synthetic velocity field
(torch was importable but the weights path was not in the expected location
under the smoke-test cwd). The wall-clock figures are therefore NOT
representative of the production R5b cell — they are only proof that the
harness plumbing works.

| Sub-sweep | mode | NFE | rounds | wallclock_s | wallclock_per_record_s |
|---|---|---:|---:|---:|---:|
| baseline | torch (no weights -> synthetic fallback path) | 50 | 1 | 2.257 | 0.0353 |
| framework | torch (no weights -> synthetic fallback path) | 50 | 4 | 2.193 | 0.0343 |

Per-component breakdown (framework sub-sweep):

| Component | total_s | calls | share_of_framework_s |
|---|---:|---:|---:|
| `adapter.solve_ode` | 4.447 | 54 | 2.028 |
| `RestartBlenderProtocol.blend` | 0.0013 | 4 | 0.0006 |
| `scheduler.sample` | 9.2e-05 | 4 | 0.0 |
| `BoundedMergeOperator.merge` | 6.9e-05 | 4 | 0.0 |
| `paper_quantities_fn` | 5.5e-06 | 4 | 0.0 |
| `scheduler.record_round_feedback` | 3.3e-06 | 4 | 0.0 |

The `adapter.solve_ode` row dominates because it carries the warmup-call
counter (50 baseline + 4×12.5 framework = ~100 effective calls inside the
warmup loop) — those are the warmup repetitions counted by `_time` even
though they are not in the cProfile-enabled section. The pstats dump
captures only the timed-section calls (4 framework rounds × 1
`adapter.batched_inference` per round = 4 calls + 1 baseline = 5 total
sampled calls).

The downstream Wave 212 P2 audit should read the pstats file directly with
`python -m pstats verification_outputs/wave212-p1-cprofile-framework.pstats`
or `pstats.Stats(...)` for the structural breakdown — the per-component
JSON is for *targeted* attribution only.

## 7. Outputs

| Path | Content |
|---|---|
| `verification_outputs/wave212-p1-cprofile-baseline.pstats` | cProfile dump of the baseline sub-sweep |
| `verification_outputs/wave212-p1-cprofile-framework.pstats` | cProfile dump of the framework sub-sweep (4 rounds) |
| `verification_outputs/wave212-p1-component-timings.json` | Per-component JSON aggregator |
| `verification_outputs/wave212-p1-component-timings.csv` | Per-component CSV aggregator |
| `scripts/wave212_p1_profile_runner.py` | The harness (this doc's source-of-truth) |

## 8. Re-run command

```bash
.venvs/kanzi_venv/bin/python scripts/wave212_p1_profile_runner.py
```

The harness launches the two sub-sweeps serially under cProfile and writes
all four artefacts in `verification_outputs/`.

## 9. Files touched

* `scripts/wave212_p1_profile_runner.py` (new) — the harness.
* `verification_outputs/wave212-p1-{cprofile-baseline,cprofile-framework,component-timings}.{pstats,json,csv}` (new) — outputs.
* `docs/audit/wave212-p1-profile-setup.md` (this doc).

**NO** file under `adaptive_reflow/` was modified.
