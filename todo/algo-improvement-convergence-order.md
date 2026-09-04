# Algorithm improvement — convergence-order verification (C.6)

**Status:** done (Wave 18 C.6 + Wave 20 P1 DPK45 fix — commits d7cd65b + 53e5d52; 5/5 in-scope integrators pass convergence tests, DPK45 step assembly bug fixed)
**Date:** 2026-09-05
**Priority:** medium-high (FM integrators without verified convergence
order silently degrade every reported number; SciML's test_convergence
is the gold standard we lack)
**Depends on:** Wave 15 Phase 1 (F.5 env_hash) completed; Algo B (rate
bound theorem) completed
**Owner:** framework maintainer
**Goal:** Every public deterministic FM integrator achieves its claimed
global-error order within 0.2 absolute tolerance on 3 analytic test
problems. Behind `--runslow` marker; nightly CI only.

## Background

Framework-internal-metrics rev 2 §1 C.6:
> Empirical convergence-order verification: every deterministic FM
> integrator achieves its claimed global-error order within 0.2 absolute
> tolerance on 3 analytic problems (linear drift, nonlinear drift,
> stiff). Stochastic integrators (SDE-style) instead verified under
> C.7 SBC. Behind `--runslow` marker, nightly only, not per-PR.

Per SciML's `test_convergence` pattern: log(error) vs log(NFE) fit
slope within 0.2 of claimed order (relaxed from 0.05 per Wave 13
verification fix).

Without C.6 verification, a "Heun-like" integrator that claims order
1.5 but achieves order 1.0 silently degrades every reported number.

## Scope

### Public FM integrators (target list)

Audit `adaptive_reflow/adapters/integrators.py` (1162 lines per Wave 14
baseline audit) and `adaptive_reflow/algorithm/integrators.py` (if it
exists) to enumerate:

- Heun (order 1)
- Midpoint (order 2)
- RK4 (order 4)
- DOPRI5 / DOPRI8 (order 5/8)
- Stochastic Heun (SDE-style — defers to C.7 SBC)

### Analytic test problems

| Problem | Drift | Analytical solution |
|---|---|---|
| Linear | `dx/dt = -x` | `x(t) = x0 · exp(-t)` |
| Nonlinear | `dx/dt = -x^3` | `x(t) = x0 / sqrt(2x0²·t + 1)` |
| Stiff | `dx/dt = -100·x` | `x(t) = x0 · exp(-100·t)` |

For each (integrator, problem) pair:
- Run at NFE ∈ {10, 20, 40, 80, 160, 320}
- Compute global error (L∞ norm or L²)
- Fit log(error) vs log(NFE); assert slope within 0.2 of claimed order

## Tasks

1. **Enumerate** public deterministic integrators (grep for Heun, RK4,
   DOPRI5, Euler, midpoint, etc.)
2. **Create `tests/test_convergence/`** directory
3. **Define test problems** in `tests/test_convergence/test_problems.py`
4. **Author convergence test per integrator**:
   `tests/test_convergence/test_<integrator>_convergence.py`
5. **Document expected slopes** in
   `tests/test_convergence/CONVERGENCE_TARGETS.md` (per-integrator expected
   orders + tolerances + exceptions for stochastic integrators)
6. **Behind `--runslow` marker** so nightly CI runs but PR doesn't
7. **Run on PRO 6000 GPU** (or 5090); each test ~5-10 min
8. **Track compute budget** per integrator (log in run output)

## Files affected

- `tests/test_convergence/__init__.py` (NEW)
- `tests/test_convergence/test_problems.py` (NEW)
- `tests/test_convergence/test_heun_convergence.py` (NEW)
- `tests/test_convergence/test_rk4_convergence.py` (NEW)
- `tests/test_convergence/test_midpoint_convergence.py` (NEW)
- `tests/test_convergence/test_euler_convergence.py` (NEW)
- `tests/test_convergence/CONVERGENCE_TARGETS.md` (NEW; per-integrator
  expected orders + tolerances + exceptions)
- `framework-internal-metrics.md` §1 C.6 (UPDATE; metric table reflects
  new state)

## Acceptance

- [ ] All identified public deterministic integrators have convergence tests
- [ ] Each test passes (within 0.2 absolute tolerance)
- [ ] CONVERGENCE_TARGETS.md documents expected slopes per integrator
- [ ] `pytest tests/test_convergence/ -m "not slow"` skips (PR-friendly)
- [ ] `pytest tests/test_convergence/ -m slow` runs (nightly)
- [ ] `docs/baseline-audit-report.md` §C.6 updated to "MET"
- [ ] Commit + push

## Estimated time

4-6 hours GPU (mostly running on PRO 6000; 5090 also works for smaller
problems).

## Acceptance gate

**Gate name:** `G-C6-CONVERGENCE-ORDER` (new)

**Pre-condition:** At least one public deterministic integrator exists
**Pass conditions:**
- [ ] All acceptance checklist items
- [ ] `docs/baseline-audit-report.md` §C.6 marked MET

## Exception process

Per rev 2 C.6 note: stochastic integrators (SDE-style) don't have
well-defined deterministic convergence order. They are instead verified
under C.7 (SBC). Document exception in CONVERGENCE_TARGETS.md for any
integrator that doesn't fit the deterministic pattern.

## Pitfall (per Research 4)

Performance-regression thresholds are hard to set. Asv (Python) and
BenchmarkCI (Julia) warn when wall-clock regresses by 10-20 percent,
but absolute thresholds break under hardware variance. Mitigation:
track relative percentiles (p50, p95), use paired commits (baseline vs
candidate in same machine), and treat accuracy-vs-NFE Pareto fronts as
the primary metric rather than raw speed. SciMLBenchmarks explicitly
tracks accuracy AND cost, never just cost.

## Out of scope

- Performance regression benchmarks (separate task; out of scope here)
- Stochastic integrator verification (covered by SBC task)

## Related

- `framework-internal-metrics.md` §1 C.6 (defines the metric)
- `todo/algo-improvement-property-based-testing.md` (B.7; sister task)
- `todo/algo-improvement-sbc.md` (C.7; sister task)