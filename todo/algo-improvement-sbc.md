# Algorithm improvement — Simulation-Based Calibration for stochastic re-inference (C.7)

**Status:** pending (rev 2 §1 says deferred to Wave 18; bumping forward
per user "framework depth" priority)
**Date:** 2026-09-05
**Priority:** medium (per rev 2 §1 C.7 = 0%; stochastic algorithm
verification missing — without it, framework could converge to a wrong
stationary distribution with no test catching it)
**Depends on:** Wave 15 Phase 1 (F.5 env_hash) completed
**Owner:** framework maintainer
**Goal:** Every public stochastic algorithm in the framework verified via
Talts et al. 2018 SBC (rank-uniformity test). Behind `--runslow`;
parallelisable across algorithms.

## Background

Framework-internal-metrics rev 2 §1 C.7:
> Simulation-Based Calibration (SBC) for stochastic re-inference: rank
> histogram approximately uniform at N≥1000 samples. Behind
> `--runslow`; parallelisable across stochastic algorithms; N=200
> first then N≥1000 if compute budget allows; per-stochastic-algorithm
> compute budget tracked.

Per Talts et al. 2018 (Stan reference implementation): draw N
(theta, x) pairs with theta ~ prior, x ~ p(x|theta); re-infer
theta_hat; rank histogram of theta_hat vs theta must be approximately
uniform for calibrated algorithm.

Per Research 4 G.6: without SBC, the framework could converge to a
wrong stationary distribution and no test would catch it.

## Scope

### Stochastic algorithms (target list)

- `adaptive_reflow/algorithm/dynamic_noise_bias.py` — noise bias stochastic
- `adaptive_reflow/algorithm/scheduler/` — stochastic scheduler components
- `adaptive_reflow/algorithm/policy_driver.py` — stochastic policy
- Noise schedules (variance schedule for SDE-style re-inference)

## Tasks

1. **Enumerate** public stochastic algorithms (grep for `random` /
   `stochastic` / noise draws)
2. **For each**: implement SBC test
   - Define prior on theta (algorithm's parameter space)
   - Define simulator: theta → x
   - Define re-inference: x → theta_hat
   - Run N=200 trials; compute rank histogram
   - If uniform (chi-squared p > 0.05), pass; else log root cause
3. **Behind `--runslow` marker** (not per-PR)
4. **Parallelise across algorithms** (pytest-xdist)
5. **Compute budget tracking per algorithm** (log in run output)
6. **Optionally: N=1000 second pass** for algorithms passing N=200

## Files affected

- `tests/test_sbc/__init__.py` (NEW)
- `tests/test_sbc/test_dynamic_noise_bias_sbc.py` (NEW)
- `tests/test_sbc/test_scheduler_sbc.py` (NEW)
- `tests/test_sbc/test_policy_driver_sbc.py` (NEW)
- `tools/run_sbc_audit.py` (NEW; standalone runner for nightly CI)
- `framework-internal-metrics.md` §1 C.7 (UPDATE)

## Acceptance

- [ ] All identified public stochastic algorithms have SBC tests
- [ ] Each test passes (rank histogram uniform, chi-squared p > 0.05)
      at N=200
- [ ] `--runslow` marker respected
- [ ] `docs/baseline-audit-report.md` §C.7 updated to "MET"
- [ ] Commit + push

## Estimated time

6-12 hours GPU (N=200 with multiple algorithms; sequential run
acceptable for first pass).

## Acceptance gate

**Gate name:** `G-C7-SBC` (new)

**Pre-condition:** At least one public stochastic algorithm exists
**Pass conditions:**
- [ ] All acceptance checklist items
- [ ] `docs/baseline-audit-report.md` §C.7 marked MET

## Pitfall (per Research 4)

SBC requires many samples to be statistically meaningful. A
rank-uniformity test with N=100 is uninformative; typical Stan guidance
is N ≥ 1000. Mitigation: gate SBC tests behind `--runslow` so CI runs
them nightly but not every commit.

## Out of scope

- Continuous-benchmarking via Stan SBC across all stochastic algorithms
  (this task covers the framework's own stochastic code; model
  integration verification is separate)

## Related

- `framework-internal-metrics.md` §1 C.7 (defines the metric)
- `todo/algo-improvement-convergence-order.md` (C.6; sister task;
  deterministic counterpart)