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
| `scripts/wave191_p3_mnist_sweep.py` | Attribution controls: `--total-nfe` (shared budget for both arms), `--baseline-num-steps` (baseline-only override), `--n-rounds`. |
| `scripts/wave191_p3_mnist_sweep.py` | `--seed-keyed-prior` folds `--seed` into the prior batch id. Default off; without it `--seed` has no effect at all (§6). |
| `tools/gap56_r5c_paired_bootstrap.py` | Record-level paired bootstrap on the headline FID (full 10k reference). Replaces the chunk-level test, which is biased by its 20-image reference (§4.3). |
| `tools/gap56_nfe_floor.py` | Single-pass FID versus Euler step count, with the Fréchet decomposition. |
| `tools/gap56_r5c_report.py` | Consolidates every run dir into one markdown table. |
| `tools/gap55_r1_score_fastas.py` | Scores an existing R1 FASTA pair with the upstream HMMER pipeline (no regeneration). |
| `tests/test_gap56_restart_t0.py` | 26 tests: the `beta = 0` no-op invariant (random + production weights), the on-path identity, interval plumbing, digest separation, invalid-interval rejection, the three allocation modes, and the seed axis. |

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
`n = 200`, one prior draw (the fixed `wave191-p3` batch; §5.5 shows it is a
lucky draw and that the paired `Δ%` is what survives). `Δ%` is on the
**headline** FID (Fréchet distance against the full 10 000-image
reference). Lower is better; positive = the framework is worse than the
single-pass baseline.

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

### 4.2 The structural step-count argument — tested and refuted

At a fixed total NFE the restart scheme cannot have a finer mean step than
the single pass. The path each round covers is `1` for round 0 and `1 - m_r`
for the rest, so

```
total path = 1 + sum_r (1 - m_r)  >=  1        (equality iff m_r = 1, no restart)
mean step  = total path / NFE     >=  1/NFE    = the baseline's step
```

Measured for `β_total = 0.5`, `equal_budget` (`m_r = 0.7937`):
total path `1.619`, mean step `0.032` versus the baseline's `0.020`.

The natural inference — "round 0 is starved, that is the regression" — was
tested directly in §5.2 and is **false**: a 25-step baseline scores
`11.0578` against the 50-step baseline's `11.0640`. Halving the first pass
costs nothing on this model, because the baseline is already at its FID
floor by ~15 NFE. The step-count argument therefore explains nothing here;
§5.3 locates the actual mechanism.

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

## 5. Follow-up experiments (all N=200, seed 42, production ckpt)

Four experiments were run to test whether the residual regression is a
tuning problem. It is not.

### 5.1 The β curve is flat

`equal_budget`, `t0=0`, `scheduler` allocation, `NFE=50`:

| β_total | β per round | cosine Δ% | codim Δ% | evidence Δ% |
|---:|---:|---:|---:|---:|
| 0.10 | 0.0345 | +7.87 | +9.32 | +8.64 |
| 0.20 | 0.0717 | +8.10 | +9.11 | +7.74 |
| 0.35 | 0.1338 | +8.28 | +7.53 | +7.09 |
| 0.50 | 0.2063 | +6.94 | +8.50 | +8.97 |

A 5× change in the injected-noise budget moves the delta by ~1.5
percentage points with no monotone trend. **The penalty is not caused by
how much noise the restart injects.**

### 5.2 The baseline is already at its FID floor by ~15 NFE

`tools/gap56_nfe_floor.py`, single-pass Euler, N=200:

| NFE | 1 | 2 | 3 | 5 | 8 | 10 | 15 | 20 | 25 | 50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FID | 20.66 | 16.97 | 14.88 | 13.37 | 12.59 | 12.35 | 12.06 | 11.92 | 11.84 | 11.70 |

From NFE 15 to 50 the FID improves by 0.36 (3 %). The direct control inside
the sweep agrees: baseline at 25 steps `11.0578`, at 31 steps `11.0601`, at
50 steps `11.0640` — the 25-step baseline is, within noise, *identical* to
the 50-step baseline.

So the "starved first pass" hypothesis in §4.2 is **wrong**: halving round
0's step count costs nothing. Whatever the restart rounds are doing, it is
not compensating for a coarse first pass — there is no coarse-first-pass
penalty to compensate for.

### 5.3 Where the FID gap actually lives

Decomposing FID into `‖Δμ‖² + Tr(Σ) + Tr(Σ_ref) − 2Tr(√(ΣΣ_ref))` on the
saved sample clouds (`Tr(Σ_ref) = 35.281`):

| run | arm | Tr(Σ) | bias `‖Δμ‖²` | cross | FID |
|---|---|---:|---:|---:|---:|
| — | baseline | 26.55 | 4.23 | 54.99 | 11.06 |
| `legacy_const` | cosine | 33.76 | 5.83 | 61.74 | 13.13 |
| `eqbeta_zero` | cosine | 38.65 | 4.20 | 66.29 | 11.83 |
| `prop_eq` | cosine | 25.57 | 5.15 | 54.04 | 11.96 |

Two distinct mechanisms, and they trade off:

* **`t0 = 0` inflates the variance.** Re-integrating the whole path from a
  blend re-draws noise that the model does not fully contract: `Tr(Σ)` goes
  from 26.5 to 38.6 (+46 %). The mean bias is untouched (4.23 → 4.20).
* **`t0 = memory` preserves the variance but adds bias.** `Tr(Σ)` stays at
  25.6 (−4 %), but `‖Δμ‖²` rises 4.23 → 5.15.

Neither is a large effect on the scale that matters: the *baseline itself*
is 26.5 against a reference of 35.3 and sits 4.23 away in the mean, so the
model-versus-reference mismatch is ~11 FID units while the entire sampler
choice is worth ~1. **The cell is model-limited, not sampler-limited**, and
that is why no configuration wins.

### 5.4 Low-NFE regime: still dominated

Since the baseline is at its floor above ~15 NFE, the only place a sampler
mechanism could show is below it. `proportional` allocation,
`equal_budget`, best arm per cell:

| total NFE | R=2 `t0=memory` | R=2 `t0=zero` | R=3 `t0=memory` | R=3 `t0=zero` |
|---:|---:|---:|---:|---:|
| 3 | +20.96 | +8.97 | — | +19.79 |
| 4 | +20.02 | +8.30 | — | **+4.20** |
| 5 | +18.04 | — | +9.88 | +4.18 |
| 10 | +17.06 | — | +8.38 | +5.18 |
| 15 | +16.69 | — | +8.12 | +5.78 |
| 50 | — | — | +8.07 | +6.94 |

`R=3, t0=zero` has a shallow minimum of **+4.2 %** at NFE 4–5 and rises on
both sides. It never crosses zero: below NFE=4 a 3-round scheme has no
steps left to distribute.

### 5.5 Genuine 3-draw confirmation

> **N=200 caveat (added 2026-10-20, GAP-57 §7).** The FID estimator used here is
> strongly biased upward at small `n`, and the bias is arm-dependent. Measured
> calibration at `d=128` against a 10 000-image reference with a true FID of 0:
> the estimate is 23.98 at `n=200` and 4.73 at `n=1000`; for a paired delta
> whose true value is 11.52 the estimate is 18.99 at `n=200` and 12.99 at
> `n=1000` (`tools/gap56_fid_small_n_bias.py`). The magnitudes below are
> therefore **inflated by roughly 40–65 %**; the signs and ordering are what
> this section is evidence for. Every number quoted outside this audit must come
> from the `N=1000` re-measurement.

With `--seed-keyed-prior` the seed axis is real (§6). Two configurations ×
three prior draws, `NFE=50`, headline FID, `Δ%` versus the baseline of the
same draw:

| config | seed | baseline FID | cosine | codim | evidence |
|---|---:|---:|---:|---:|---:|
| legacy (β const 0.5) | 42 | 12.9753 | +13.77 | +18.44 | +10.70 |
| legacy | 43 | 12.4798 | +17.91 | +22.20 | +10.38 |
| legacy | 44 | 12.0098 | +15.95 | +22.17 | +11.18 |
| **legacy mean** | | **12.4883** | **+15.88 ± 2.07** | **+20.94 ± 2.16** | **+10.75 ± 0.40** |
| equal_budget (t0=0) | 42 | 12.9753 | +5.30 | +8.57 | +8.51 |
| equal_budget | 43 | 12.4798 | +7.04 | +10.68 | +9.78 |
| equal_budget | 44 | 12.0098 | +7.82 | +9.79 | +10.39 |
| **equal_budget mean** | | **12.4883** | **+6.72 ± 1.29** | **+9.68 ± 1.06** | **+9.56 ± 0.96** |

All **18** cells are positive (framework worse); sign test `p = 2⁻¹⁸ ≈
3.8e-06`. The β-accounting fix halves the excess (legacy +10.8…+20.9 →
+6.7…+9.7) and the ordering is stable across draws, so the mechanism
finding is robust even though the absolute FID is not.

**Baseline FID varies 12.01–12.98 across draws at N=200** (sd 0.48, 3.8 %).
The earlier single-draw value of 11.064 came from the fixed
`wave191-p3` batch and is a lucky draw; 12.5 is the honest N=200 estimate.
Paired `Δ%` is unaffected by this.

## 6. Second defect found: the seed axis was vacuous

While setting up the 3-seed confirmation, the seed axis turned out not to
exist.

* `MnistFmAdapter.build_initial_state` keys the Gaussian prior on
  `(batch_id, sample_id, adapter_seed_offset)` — **not** on the run seed.
* `MnistFmAdapter.solve_ode` begins with `del seed  # deterministic`.
* The driver passes `seed_offset=args.seed` into `seed_for_round`, which is
  then discarded.

So `--seed` changes nothing about the generated samples. Measured:

```
$ python3 -c "... compare npz ..."
baseline seed42 vs seed43: array_equal = True,  max|diff| = 0.0
cosine   seed42 vs seed43: array_equal = True,  max|diff| = 0.0
```

and on the frozen Wave 280 artifacts:

```
verification_outputs/wave280-p-r5c/seed{42,43,44}/*_samples.npz
  baseline 42 vs 43: bit-equal   42 vs 44: bit-equal
  cosine   42 vs 43: bit-equal   42 vs 44: bit-equal
```

**The R5c "3-seed × N=200 paired t-test" reported in
`docs/audit/mnist/wave280-p-r5c-sweep-result.md` §3 is three copies of one
deterministic draw.** The `outcome=STRONG` label attached to that cell on
the strength of the three seeds is not supported.

Fix: `--seed-keyed-prior` folds the seed into the prior batch id
(`wave191-p3-s{seed}`). Verified to change the draw
(`array_equal = False`, `max|diff| = 2.0` on a 20-sample probe). Default
off, so every historical artifact keeps its meaning — including the
discovery that they are all one draw.

This is a second, independent reason the R5c evidence grade was too high,
and it is not specific to R5c: any cell whose driver relies on `--seed`
while the adapter discards it has the same problem.

## 7. Conclusion

1. **The defect is real and fixed.** `solve_ode` ignored `t0`/`t1`; the
   `beta = 0` no-op invariant was violated by a full-scale sample
   inversion. Both are now covered by tests.
2. **The fix halves the regression but does not remove it.** Legacy
   +10.8…+20.9 % → +6.7…+9.7 % at NFE=50 (three-draw means, §5.5).
3. **No tested configuration beats the baseline anywhere in NFE ∈ [3, 50]**
   — 25 configurations, five mechanisms (β budget, restart start time, NFE
   allocation, round count, total budget). Confirmed on three genuine prior
   draws: 18/18 cells positive, sign test `p ≈ 3.8e-06`.
4. **The reason is not a tuning failure.** The baseline reaches its FID
   floor at ~15 NFE, the β curve is flat, and the FID decomposition shows
   the sampler moves ~1 unit of an ~11-unit model-versus-reference gap.
5. **The historical −28.43 % is not a valid target for this cell.** It was
   measured on the smoke checkpoint (`wf334-r5c-regime-curve.md` §1); on
   the production checkpoint the framework has never won at matched NFE.
6. **The R5c seed axis was vacuous** (§6). The Wave 280 three-seed
   `outcome=STRONG` label is not supported by its own artifacts.

## 8. Unresolved gaps

1. **N=200, one seed.** Confirmation at N=1000 with the pre-registered
   3-seed design is required before any status label changes. Seeds are a
   diagnostic axis here, never a significance lever.
2. **Only the MNIST adapter honours `t0`/`t1`.** The other 11 adapters
   still hard-code `[0, 1]`; if the same wiring is used elsewhere the same
   defect exists there. Not yet audited.
3. **Thread oversubscription.** BLAS threads are 12.7× *slower* than one
   thread on this workload (2.06 s vs 26.22 s for 10 × 50-NFE solves at 1
   vs 32 threads). All GAP-56 runs use `OMP_NUM_THREADS=1`; the results are
   bit-identical to the 32-thread control (headline FID agrees to 1e-14).
4. **Absolute FID depends on the prior batch.** The same 50-step baseline
   scores 11.70 with `batch_id="gap56-nfe-floor"` and 11.04 with
   `batch_id="wave191-p3"` at N=200, so absolute values are not comparable
   across batch ids and the record-level bootstrap (which resamples within
   one draw) understates the true uncertainty. All deltas in this note are
   paired within one draw and are unaffected.
5. **Checkpoint-path reporting was wrong until this increment.** Summaries
   written before the reporting fix carry `"checkpoint":
   "data/mnist_fm.npz"` even when `--ckpt` pointed elsewhere.
   `checkpoint_sha256` was always correct and is the authoritative field.
