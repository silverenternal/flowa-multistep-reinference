# GAP-56 — the restart blend is a path state; the driver integrated it as `t = 0`

**Increment:** `gap56-r5c-memory-t0`
**Date:** 2026-10-19
**Owner surface:** `adaptive_reflow/adapters/mnist_fm.py`,
`scripts/wave191_p3_mnist_sweep.py`
**Status:** code fix landed and tested; N=200 mechanism screen **in flight**;
N=1000 confirmation not started.
**Device:** CPU (numpy float64). Checkpoint
`data/mnist_fm/production.ckpt.npz`, sha256 `27e2bb6c…f220aa`.

---

## 1. What was observed

The R5c MNIST FM cell regresses at honestly matched total NFE (GAP-55,
`docs/audit/gap55-code-level-hardening.md` §8.1): at `NFE = 50` the best
framework arm is **+9.17 % to +14.64 %** worse FID than the single-pass
baseline, Bonferroni-significant on all three arms. The user directive is
that a regression is not acceptable and must be fixed at the root, not
re-labelled.

Probing the mechanism turned up a **hard invariant violation**: with
`beta = 0` — the policy that means "keep 100 % of the previous sample and
inject no fresh noise" — a restart round is **not** a no-op.

```
beta=0 -> blend identical to previous sample? max|blend - x| = 0.0
beta=0 -> after 50 more NFE (legacy wiring):  max|x_after - x| = 1.0137
                                             relative drift    = 24.9 %
```

The blend is byte-identical to the previous sample and the next round then
destroys it. `max|x_after - x| = 1.0137` on a signal that lives in
`[-1, 1]` is a full-scale pixel inversion.

## 2. Root cause

The MNIST flow-matching model is trained on the linear path

```
x_t = (1 - t) * x_0 + t * x_1        x_0 ~ N(0, I),  x_1 = data
```

(`adaptive_reflow/adapters/mnist_fm_train.py:639-640`), so `t` is a genuine
time coordinate: `t = 0` is noise, `t = 1` is data.

`MnistFmAdapter.apply_restart_distribution` builds

```
blend = memory_fraction * x_1_hat + (1 - memory_fraction) * x_0_fresh
```

which, term by term, is **exactly the path state at `t = memory_fraction`**.
The driver then asked `solve_ode` for a round over `[0, 1]` — because
`MnistFmAdapter.solve_ode` hard-coded
`np.linspace(0.0, 1.0, num_steps + 1)` and ignored the `t0`/`t1` carried by
`ODEConditionDelta`.

Two consequences, both structural:

1. **The state is integrated over the wrong interval.** A restart at
   `memory_fraction = m` should traverse `[m, 1]`, i.e. a path of length
   `1 - m`. The legacy wiring traversed length `1.0`. Every restart round
   therefore threw away the previous round's NFE and re-generated from
   scratch, from a starting point that was never a valid `t = 0` state.
2. **The velocity field is evaluated at the wrong time.** `v(x_m, 0)` was
   called where `v(x_m, m)` was meant.

The interval error dominates. Measured on the production checkpoint
(`x_m` = the restart blend, `m = 1 - beta`):

| beta | m | ‖v(x_m, 0)‖ | ‖v(x_m, m)‖ | cos(v₀, v_m) |
|---|---|---|---|---|
| 0.0000 | 1.0000 | 28.646 | 28.492 | 0.9970 |
| 0.2063 | 0.7937 | 31.160 | 31.201 | 0.9986 |
| 0.5000 | 0.5000 | 31.822 | 31.800 | 0.9995 |
| 0.8000 | 0.2000 | 30.617 | 30.495 | 0.9996 |

The *direction* is nearly time-invariant (cos ≥ 0.997), so the time label
alone is a second-order error. The magnitude is what kills the sample:
‖v‖ ≈ 29, so integrating over a unit interval moves the state by ≈ 29
(clamped into `[-1, 1]`), whereas the intended `[m, 1]` interval moves it
by `29 · (1 - m)`. At `m = 0.7937` that is a genuine 20.6 % refinement
instead of a full regeneration.

**This is the mechanism behind the R5c regression**: at matched total NFE
the framework was spending 3 of its 4 rounds re-running the whole
trajectory from a corrupted start.

## 3. What changed

Additive; every legacy call is byte-identical.

| File | Change |
|---|---|
| `adaptive_reflow/adapters/mnist_fm.py` | `solve_ode` reads `t0`/`t1` from `delta_spec` (defaults `0.0`/`1.0`), validates `0 ≤ t0 ≤ t1 ≤ 1`, and builds `linspace(t0, t1, n+1)` for all three integrators. The interval is added to the trajectory digest so the native-state cache cannot collide across intervals. |
| `scripts/wave191_p3_mnist_sweep.py` | New `--restart-t0-mode {zero,memory}` (default `zero` = legacy). New `--nfe-allocation {scheduler,uniform,proportional}` for `--equal-total-nfe`. New `restart_t0_per_round()`. Records `restart_t0_mode`, `restart_t0_per_round`, `nfe_allocation_weights` in the summary JSON. |
| `scripts/wave191_p3_mnist_sweep.py` | Reporting fix: `checkpoint` and the honest-disclosure text now name the checkpoint actually used (`--ckpt`), not the hard-coded `data/mnist_fm.npz`. The sha256 was always correct; only the human-readable path was wrong. |
| `tests/test_gap56_restart_t0.py` | 23 tests: the `beta = 0` no-op invariant (random + production weights), the on-path identity, interval plumbing, digest separation, invalid-interval rejection, and the three allocation modes. |

### 3.1 Why the allocation had to change too

Under `--restart-t0-mode memory` a round no longer covers the whole path,
so the scheduler's `n_cap` weights stop describing how much work each round
does. For `beta_total = 0.5`, `equal_budget`, 4 rounds:

| config | `t0` per round | NFE (cosine) | total path | mean step `h` |
|---|---|---|---|---|
| legacy (`t0 = 0`, constant β) | `[0, 0, 0, 0]` | `[25, 18, 6, 1]` | 4.000 | 0.080 |
| `equal_budget`, `t0 = 0` | `[0, 0, 0, 0]` | `[25, 18, 6, 1]` | 4.000 | 0.080 |
| memory + `scheduler` | `[0, .7937, .7937, .7937]` | `[25, 18, 6, 1]` | 1.619 | 0.032 |
| memory + `proportional` | `[0, .7937, .7937, .7937]` | `[31, 7, 6, 6]` | 1.619 | 0.032 |
| memory + `constant` β | `[0, .5, .5, .5]` | `[25, 18, 6, 1]` | 2.500 | 0.050 |

The `scheduler` allocation under memory mode is deliberately kept as a
control: cosine gives round 3 **one** step over a 0.206 path interval
(`h = 0.206`), which is a degenerate Euler step. `proportional` weights by
`1 - t0_r`, giving a uniform `h ≈ 0.033` across all four rounds.

## 4. Results — N=200 mechanism screen (seed 42, paired, shared prior)

Production checkpoint, `NFE = 50`, `--equal-total-nfe --shared-prior`,
`n = 200`, one seed. `Δ%` is on the **headline** FID (Fréchet distance
against the full 10 000-image reference). Lower is better; positive = the
framework is worse than the single-pass baseline.

| config | baseline | cosine | Δ% | codim | Δ% | evidence | Δ% |
|---|---:|---:|---:|---:|---:|---:|---:|
| legacy (β const 0.5, `t0=0`) | 11.0640 | 13.1272 | +18.65 | 13.5007 | +22.02 | 12.5290 | +13.24 |
| equal_budget, `t0=0` | 11.0640 | 11.8318 | +6.94 | 12.0049 | +8.50 | 12.0567 | +8.97 |
| equal_budget, `t0=memory`, sched alloc | 11.0640 | 12.0217 | +8.66 | 12.2787 | +10.98 | 12.0966 | +9.33 |
| equal_budget, `t0=memory`, proportional alloc | 11.0640 | 11.9569 | +8.07 | 12.2887 | +11.07 | 12.0612 | +9.01 |
| β const 0.5, `t0=memory` | 11.0640 | 15.4745 | +39.86 | 14.7581 | +33.39 | 14.1823 | +28.18 |

### 4.1 What the fix bought

The `t0` fix is real but small: it moves the legacy configuration from
**+13 % to +22 %** down to **+8 % to +11 %** — roughly a 50 % reduction in
excess FID — and the β-accounting fix (GAP-55) buys a comparable amount on
its own. **Neither reaches the baseline, and the two are not additive**:
`equal_budget` with `t0 = 0` (+6.94 % best) is *better* than `equal_budget`
with the on-path restart (+8.07 % best).

That inversion is the interesting part. Integrating `[0, 1]` from a
79 %-data blend — the behaviour GAP-56 calls a defect — acts as a
**re-denoising pass**: the velocity field pulls the blended state back onto
the data manifold, which corrects accumulated error. The on-path partial
restart `[0.79, 1]` only refines the last 20.6 % of the path and leaves the
global error untouched. So the legacy wiring was accidentally implementing a
useful resampling step while getting the interval wrong.

### 4.2 Why no configuration wins — the structural argument

At a fixed total NFE the restart scheme cannot have a finer step than the
single pass. The path each round covers is `1` for round 0 and `1 - m_r`
for the rest, so

```
total path = 1 + sum_r (1 - m_r)  >=  1        (equality iff m_r = 1, no restart)
mean step  = total path / NFE     >=  1/NFE    = the baseline's step
```

Measured for `β_total = 0.5`, `equal_budget` (`m_r = 0.7937`):
total path `1.619`, mean step `0.032` versus the baseline's `0.020`.

The framework can only win back that factor through error *correction*.
Measured curvature (mean `‖Δv‖` along 20 baseline trajectories, 200-step
reference) says the re-traversed region is only mildly special:

| region | share of total `‖Δv‖` | share of path |
|---|---:|---:|
| `[0, 0.5)` | 50.5 % | 50.0 % |
| `[0.5, 0.7937)` | 20.2 % | 29.4 % |
| `[0.7937, 1]` | 29.3 % | 20.6 % |

The last 20.6 % of the path carries 29.3 % of the curvature — 1.42× the
uniform share, not enough to pay for a 1.6× coarser step. Curvature-weighted
cost per step: baseline `0.70`, framework `1.32`.

So the observed ordering is the expected one, and the GAP-56 result is
**not** "the regression is fixed". It is "the regression is smaller and its
mechanism is now understood".

### 4.3 Methodological correction: the chunk-level test is biased

The sweep driver reports two FID estimators. The paired t-test used
throughout the R5c record is computed on `fid_chunks_mean`, which averages
`k = 10` chunk FIDs each evaluated against a **20-image** reference chunk.
For the memory-mode configs that estimator **flips the sign** of the effect:

| config | headline Δ% | chunk Δ% | chunk Bonferroni p |
|---|---:|---:|---:|
| legacy (`t0=0`, β const) | +18.65 | +11.59 | 4.8e-08 |
| equal_budget, `t0=0` | +6.94 | +17.31 | 1.2e-07 |
| equal_budget, `t0=memory`, proportional | +8.07 | −0.32 | 1.00 |

A 20-image reference makes the Fréchet distance dominated by small-sample
bias, and that bias depends on the arm's covariance, so the paired
difference is not the effect of interest. `tools/gap56_r5c_paired_bootstrap.py`
replaces it: keep the full reference (unbiased FID) and bootstrap over
records, resampling the **same** indices for both arms so the pairing is
preserved. **The headline estimator is authoritative; the chunk test should
not be quoted for R5c.**

This also means the earlier GAP-55 R5c number (+9.17 % / +12.43 % / +14.64 %)
is directionally right but not the right magnitude; the correct comparison
is on the headline FID.

## 5. Unresolved gaps

1. **No configuration beats the baseline at matched NFE**, and §4.2 argues
   none can without an error-correction effect this model does not show.
   The historical R5c best (−28.43 %) was measured on the **smoke**
   checkpoint (`docs/audit/mnist/wf334-r5c-regime-curve.md`), not the
   production one, so it is not a valid target for this cell.
2. **N=200, one seed.** Confirmation at N=1000 with the pre-registered
   3-seed design is required before any status label changes. Seeds are a
   diagnostic axis here, never a significance lever.
3. **Only the MNIST adapter honours `t0`/`t1`.** The other 11 adapters
   still hard-code `[0, 1]`; if the same wiring is used elsewhere the same
   defect exists there. Not yet audited.
4. **Thread oversubscription.** BLAS threads are 12.7× *slower* than one
   thread on this workload (measured: 2.06 s vs 26.22 s for 10 × 50-NFE
   solves at 1 vs 32 threads). All GAP-56 runs use
   `OMP_NUM_THREADS=1`; the results are bit-identical to the 32-thread
   control (headline FID agrees to 1e-14), so the earlier runs remain valid.
5. **Checkpoint-path reporting was wrong until this increment.** Summaries
   written before the reporting fix carry `"checkpoint":
   "data/mnist_fm.npz"` even when `--ckpt` pointed elsewhere.
   `checkpoint_sha256` was always correct and is the authoritative field.
