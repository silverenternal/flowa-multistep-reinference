# Algorithm improvement D — failure-mode controlled noise injection

**Status:** done (Wave 17 P2 = Algo D — noise_sigma in twodim_fm + docs/CONDITIONS.md Pareto plots + framework-internal-metrics C.5; 2026-09-05)
**Priority:** medium
**Depends on:** at least one base adapter (twodim_fm or self_flow)
**Owner:** framework maintainer
**Goal:** produce a controlled "noise level vs framework uplift" table
that characterises WHEN the framework helps, WHEN it is neutral, and
WHEN it regresses. Honest characterization of the framework's value
boundary.

## Background

The framework has known empirical points on the value boundary:

| Setting | Framework behavior | Source |
|---|---|---|
| 2D RF, baseline correct | framework WORSE -13.5% | Wave 8 FIX-3 |
| FlowMol3 §1.1.d | framework not applicable (CTMC gap) | Wave 6 R5 |
| LineageFlow real ckpt | BLOCKED on upstream `core` | Wave 10 |
| Toy 8-gaussians | framework helps (~10%) | Wave 6 |

This is **observational** data — the framework's value is known at
discrete points. There is no **controlled** characterisation: we don't
know at what noise level the framework starts to help, when it stops
helping, or whether it actually hurts.

This task injects controlled Gaussian noise into a base adapter's
velocity output and measures the framework's recovery rate.

## Method

For a base adapter (start with `twodim_fm`, the simplest):

1. Run baseline at noise level σ = 0 (correct velocity) → metric M₀.
2. Run framework at noise level σ = 0 → metric F₀.
3. Inject Gaussian noise into the base velocity output:
   `v_noisy = v_clean + σ * N(0, I)`.
4. For each σ in {0.0, 0.01, 0.05, 0.10, 0.20, 0.50}:
   - Run baseline (1 round, fixed NFE) → M(σ).
   - Run framework (multi-round) → F(σ).
   - Compute uplift U(σ) = (F(σ) - M(σ)) / M(σ).
5. Produce table:

| σ | M(σ) | F(σ) | U(σ) | verdict |
|---|---|---|---|---|
| 0.0 | ... | ... | ... | ... |
| 0.01 | ... | ... | ... | ... |
| 0.05 | ... | ... | ... | ... |
| 0.10 | ... | ... | ... | ... |
| 0.20 | ... | ... | ... | ... |
| 0.50 | ... | ... | ... | ... |

## Expected outcomes (hypotheses, not assumptions)

- σ = 0: framework ≈ neutral (matches Wave 8 FIX-3).
- σ small: framework starts to help (the framework's selection is a
  noise-tolerant estimator).
- σ medium: framework strongly helps (its multi-round consensus
  averages out noise).
- σ large: framework regresses (the noise dominates the signal; even
  multi-round consensus can't recover).

The "transition point" σ* (where framework starts to help) is the
**value boundary** — a quantitative number the framework can publish.

## Files affected (estimated)

- `tools/noise_injection_experiment.py` (new) — experiment driver.
- `adaptive_reflow/adapters/twodim_fm.py` — may need a noise-injection
  hook (currently the adapter is a thin wrapper; may need to add a
  flag).
- `docs/CONDITIONS.md` (new) — the table above + interpretation.
- `tests/test_algo_uplifts/test_noise_injection.py` (new) — the
  experiment as a parametrized test (default 3 seeds × 6 σ levels).

## Acceptance

- [ ] Experiment script runs end-to-end on twodim_fm (~30 min).
- [ ] Table produced for twodim_fm (one row per σ, 3 seeds averaged).
- [ ] `docs/CONDITIONS.md` exists with the table + interpretation.
- [ ] Test version runs in <10 min (reduced N for CI).
- [ ] pytest passes.
- [ ] Commit + push.

## Estimated time

1-2 hours GPU (twodim_fm is cheap). Could also do self_flow later
(~2-3 hours GPU; longer convergence).

## Acceptance gate

**Gate name:** `G-ALGO-FAILURE-MODES` (new; defined here)

**Pre-condition:** twodim_fm adapter ready + baseline metric
established.
**Pass conditions:**
- [ ] Acceptance checklist above all met
- [ ] `todo/STATUS.md` updated
- [ ] `docs/CONDITIONS.md` cross-references Wave 8 FIX-3 negative result

## Out of scope

- Running this experiment on ALL adapters (start with twodim_fm;
  extend to self_flow if time permits).
- Theoretical analysis of WHY the framework helps at certain noise
  levels (the experiment is empirical; a separate task could derive
  bounds from the rate bound in task B).
- Negative-result suppression: all σ levels are reported, including
  the ones where framework regresses.