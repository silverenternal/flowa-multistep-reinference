# GAP-57 — the GAP-35 regime ladder, re-measured at equal total NFE

**Status:** observed facts complete; one open attribution (round-count axis).
**Increment:** `gap57-equal-nfe-ladder`
**Supersedes nothing.** Additive to `gap35-cross-domain.md` and
`gap56-restart-t0-defect.md`.

---

## 0. TL;DR

GAP-35 reported that the restart gain is monotone in the model's optimisation
budget: the framework wins by 25–28 % on under-trained MNIST-FM checkpoints and
regresses once the velocity field converges. **Every framework arm in that table
ran at the legacy per-round cap (cosine 25 / codim 48 / evidence 25 total NFE)
against a 50-NFE baseline**, so the size of each win was confounded with
compute.

Re-measured with **50 NFE on both sides**, the ladder survives:

| ckpt | baseline FID | Δ% at equal NFE (best arm) | Δ% at legacy NFE (best arm) | compute share of the win |
|---|---:|---:|---:|---:|
| `w16e1_5k` | 27.20 | **−13.18** (cosine) | −22.52 (codim) | **9.33 pp** |
| `w16e1_10k` | 19.21 | −1.89 (cosine) | −7.10 (evidence) | 5.21 pp |
| `w16e1_60k` | 13.51 | +10.48 (cosine) | +16.88 (evidence) | −6.39 pp |
| `production` | 12.49 | +6.08 (cosine) | — | — |

Least squares of Δ % on the baseline FID over 12 (checkpoint × draw) points:
slope **−1.145 %/FID unit**, R² **0.925**, zero crossing at baseline FID
**≈ 21.1**. Record-level paired bootstrap: **13 wins / 18 losses / 5 ties** over
36 cells, and all 9 cells at `w16e1_5k` favour the framework with a CI that
excludes zero.

**The honest headline for this mechanism is −13.2 % at matched NFE, not
−28.4 %.** Roughly 40 % of the historical `w16e1_5k` win was compute.

---

## 1. Why this re-measurement was necessary

Two independent defects had already invalidated the R5c numbers:

1. **GAP-55** — the R5c arms were not NFE-matched (25/48/25 vs 50). The paper
   described the comparison as "matched NFE"; it was not.
2. **GAP-56** — `solve_ode` ignored `t0`/`t1`, so every restart re-integrated
   the full `[0, 1]` from a state that is only valid at `t = m`; and the prior
   was keyed only on `(batch_id, sample_id)` while `solve_ode` discards its
   seed, so every "multi-seed" design produced byte-identical draws.

Both are fixed. What remained untested is the thing GAP-35 actually claimed:
that the *mechanism* — restart-blend correcting residual velocity-field error —
is what produced the wins, rather than the extra compute that came with them.

GAP-35's own numbers already hinted at a compute confound. Its three "seeds"
have **identical** `baseline_fid` and **identical** `fid_headline` (only the
chunk partition changes), so its pooled `d_z = −42.49` is a chunk-partition
statistic, not a cross-draw one. And its `delta_pct_mean = −25.39 %` is a
chunk-mean delta against a 20-image reference; the headline ratio of the same
run is **−22.52 %**. Those two estimators disagree because the small-reference
Fréchet bias is arm-dependent (GAP-56 §4.3).

---

## 2. Protocol

Held fixed across all 12 runs:

| item | value |
|---|---|
| driver | `scripts/wave191_p3_mnist_sweep.py` |
| N | 200 (chunked `k=10` for the driver's own test; bootstrap is record-level) |
| draws | seeds 42 / 43 / 44 via `--seed-keyed-prior` (genuinely distinct priors; verified byte-distinct) |
| pairing | `--shared-prior` — baseline and all arms share the round-0 prior *within* a draw |
| budget | `--equal-total-nfe --total-nfe 50`, `--nfe-allocation scheduler` |
| rounds | `--n-rounds 4`, `--beta-schedule equal_budget`, `--beta-framework 0.5` |
| restart | `--restart-t0-mode memory` (round `r` starts at `t = 1 − β_r`) |
| threads | `OMP_NUM_THREADS=1` (BLAS oversubscription is 12.7× slower, GAP-56 §8.3) |
| estimator | `fid_headline` (full 10k MNIST reference), record-level paired bootstrap B=2000, `BOOT_SEED=20261020`, Bonferroni over 3 arms |

Per-round NFE at this budget (all arms total exactly 50):

| arm | `num_steps_per_round` | total |
|---|---|---:|
| cosine | `[25, 18, 6, 1]` | 50 |
| codimension_sheet | `[13, 12, 12, 13]` | 50 |
| evidence_driven | `[25, 18, 6, 1]` | 50 |

Checkpoints (all `base_channels=16`, none smoke by size):

| tag | path | size | sha256 (16) |
|---|---|---:|---|
| `w16e1_5k` | `data/mnist_fm/w16e1_5k.ckpt.npz` | 75 035 | `01729867b67372e3` |
| `w16e1_10k` | `data/mnist_fm/w16e1_10k.ckpt.npz` | 75 146 | `c2a18c89f605729a` |
| `w16e1_60k` | `data/mnist_fm/w16e1.ckpt.npz` | 75 370 | `ae384ec81cebecff` |
| `production` | `data/mnist_fm/production.ckpt.npz` | 75 472 | `27e2bb6c44758822` |

Driver:

```bash
bash reproduce/gap57_equal_nfe_ladder.sh 6      # 12 runs, 6 concurrent, 14m51s wall
python3 tools/gap57_regime_ladder.py            # tables + regression
python3 tools/gap56_r5c_paired_bootstrap.py --run-dir <dir> --out <dir>/paired_bootstrap.json
```

---

## 3. Observed — per-draw

Equal total NFE = 50 on both sides.

| ckpt | seed | baseline FID | cosine | codim | evidence | Δ% cos | Δ% codim | Δ% evid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `w16e1_5k` | 42 | 28.0127 | 24.4373 | 26.7994 | 27.0127 | −12.76 | −4.33 | −3.57 |
| `w16e1_5k` | 43 | 26.7407 | 22.9248 | 25.5262 | 25.4619 | −14.27 | −4.54 | −4.78 |
| `w16e1_5k` | 44 | 26.8405 | 23.4806 | 25.7420 | 25.8549 | −12.52 | −4.09 | −3.67 |
| `w16e1_10k` | 42 | 19.8989 | 19.4377 | 20.8753 | 20.4807 | −2.32 | +4.91 | +2.92 |
| `w16e1_10k` | 43 | 18.8371 | 18.5388 | 20.0027 | 19.3254 | −1.58 | +6.19 | +2.59 |
| `w16e1_10k` | 44 | 18.8845 | 18.5508 | 19.8299 | 19.3000 | −1.77 | +5.01 | +2.20 |
| `w16e1_60k` | 42 | 14.2800 | 15.7353 | 16.0742 | 15.7853 | +10.19 | +12.56 | +10.54 |
| `w16e1_60k` | 43 | 13.4525 | 14.8577 | 15.3119 | 14.9092 | +10.45 | +13.82 | +10.83 |
| `w16e1_60k` | 44 | 12.8030 | 14.1877 | 14.4877 | 14.1143 | +10.82 | +13.16 | +10.24 |
| `production` | 42 | 12.9753 | 13.6277 | 14.0847 | 13.8441 | +5.03 | +8.55 | +6.70 |
| `production` | 43 | 12.4798 | 13.1971 | 13.7043 | 13.3577 | +5.75 | +9.81 | +7.04 |
| `production` | 44 | 12.0098 | 12.9060 | 13.1255 | 12.9429 | +7.46 | +9.29 | +7.77 |

## 4. Observed — three-draw summary, against the legacy protocol

Both Δ % columns are **headline ratios**, so the two protocols are compared
with the same estimator.

| ckpt | baseline FID (mean ± sd) | Δ% by arm, equal NFE | best arm | Δ% by arm, GAP-35 legacy | compute share |
|---|---:|---|---:|---|---:|
| `w16e1_5k` | 27.198 ± 0.707 | cos −13.18 / codim −4.32 / evid −4.01 | cosine −13.18 | cos −21.82 / codim −22.52 / evid −22.13 | **+9.33 pp** |
| `w16e1_10k` | 19.207 ± 0.600 | cos −1.89 / codim +5.37 / evid +2.57 | cosine −1.89 | cos +1.61 / codim +4.04 / evid −7.10 | +5.21 pp |
| `w16e1_60k` | 13.512 ± 0.740 | cos +10.48 / codim +13.18 / evid +10.54 | cosine +10.48 | cos +17.83 / codim +31.16 / evid +16.88 | −6.39 pp |
| `production` | 12.488 ± 0.483 | cos +6.08 / codim +9.22 / evid +7.17 | cosine +6.08 | — | — |

"Compute share" = equal-NFE best-arm Δ % minus legacy best-arm Δ %. Positive
means the legacy protocol *overstated* the win.

## 5. Observed — record-level paired bootstrap

Full 36-cell table: `python3 tools/gap57_regime_ladder.py` §"Record-level
paired bootstrap". Summary:

| checkpoint | cells favouring the framework | verdict |
|---|---:|---|
| `w16e1_5k` | **9 / 9** | framework wins, CI excludes 0 in every arm and draw |
| `w16e1_10k` | 4 / 9 (cosine 3/3, evidence 1/3) | cosine wins; codim ties |
| `w16e1_60k` | 0 / 9 | baseline wins in every cell |
| `production` | 0 / 9 | baseline wins in every cell |

Sign census over 36 cells: **13 wins / 18 losses / 5 ties**.

Two cells that the driver's *chunk-level* test calls significant regressions
are **ties** at record level: `w16e1_10k_s42 codimension_sheet`
(chunk p = 3.6e-08, bootstrap CI `[−0.3942, +0.4602]`) and
`w16e1_10k_s44 codimension_sheet` (chunk p = 5.8e-08, CI
`[−0.4156, +0.4341]`). This is the GAP-56 §4.3 bias again, now with an
independent sign: the chunk estimator is not a valid test for this comparison.

## 6. Observed — the ladder

Least squares of Δ % (mean over the three arms) on the baseline FID, 12 points:

- slope **−1.145 % per FID unit**
- intercept **+24.16 %**
- R² **0.925**
- zero crossing at baseline FID **≈ 21.10**

All four checkpoints are `base_channels=16`, and their baselines are
step-insensitive at NFE = 50 (GAP-35 §4: `w16e1_5k` 27.2361 → 27.2311 across
50/100/200 steps), so the equal-NFE comparison does not starve the baseline.

---

## 7. Interpretation

1. **The mechanism is real.** At `w16e1_5k` the framework beats the baseline by
   12.5–14.3 % in every draw with a record-level CI that excludes zero, at the
   same total NFE. This is not a compute artifact and not a chunk-estimator
   artifact.
2. **The historical magnitude was inflated.** GAP-35's −22.52 % headline on the
   same checkpoint becomes −13.18 % when the compute is matched: **9.33 pp of
   the 22.5 pp win was the extra NFE**, about 41 %. The paper may not quote
   −25.39 % (chunk-mean) or −28.43 % (smoke checkpoint) as this mechanism's
   effect size.
3. **The sign flip is a property of the model, not of the budget.** With NFE
   held at 50 everywhere, the sign still flips between baseline FID 19.2 and
   13.5, and the fitted crossing is at 21.1. The mechanism corrects residual
   velocity-field error; once the field has converged there is no residual left
   to correct and the restart only adds variance.
4. **The best arm changes with the protocol.** Legacy best arm is
   `codimension_sheet` at 5k and `evidence_driven` at 10k/60k; at equal NFE the
   best arm is `cosine` at every checkpoint. This is mechanical: under the
   scheduler allocation `cosine` receives `[25, 18, 6, 1]` — half the budget on
   round 0 — whereas `codimension_sheet` receives `[13, 12, 12, 13]`. The
   front-loaded allocation is what makes the restart useful.
5. **`production` is the mildest regression of the converged checkpoints**
   (+6.08 % vs +10.48 % at `w16e1_60k`), consistent with it being the best
   model in the ladder and therefore the one with the least residual error.

---

## 8. What this changes, and what it does not

**Changes.**

- R5c's effect size at matched NFE is **−13.18 %** on `w16e1_5k`
  (`w16e1_5k` baseline 27.198 ± 0.707), significant in 9/9 cells.
- The mechanism now has a **documented boundary**: baseline FID ≳ 21 favours
  the framework, baseline FID ≲ 19 favours the baseline.
- The GAP-35 ladder is confirmed *and* corrected: the sign pattern survives,
  the magnitude roughly halves.

**Does not change.**

- The production-checkpoint R5c cell still regresses (+6.08 %, 9/9 cells,
  record-level CI excludes zero). No sampler-side configuration tested in
  GAP-55/56/57 beats the baseline there.
- The historical −28.43 % remains a smoke-checkpoint artifact and −25.39 %
  remains a chunk-mean artifact. Neither is a valid target.
- No frozen surface (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
  `docs/drafts/paper-A-final.*`, `tnnls_submission/**`) is modified by this
  increment.

---

## 9. Unresolved gaps

1. **N = 200, one architecture family.** The 12 runs are 4 checkpoints × 3
   prior draws at N=200. A confirmation at N=1000 is required before any status
   label moves; the three draws are a diagnostic axis, never a significance
   lever.
2. **The ladder axis is confounded.** `w16e1_5k → 10k → 60k → production`
   varies optimisation steps, weight norm (17.27 → 17.46 → 18.25 → 19.19) and
   the baseline's own FID together. The regression of Δ % on baseline FID is a
   description of this ladder, not a causal statement about any one variable.
3. **Round count and β were not re-tuned at `w16e1_5k`.** The configuration is
   the one fixed on `production` in GAP-56 (`R=4`, `β=0.5`, scheduler
   allocation). At `w16e1_5k` round 3 receives a single Euler step; `R=2` or
   `R=3` would give round 0 more of the budget. Untested, and deliberately not
   tuned after seeing the result.
4. **Only the MNIST adapter honours `t0`/`t1`.** The other 11 adapters still
   hard-code `[0, 1]` (GAP-56 §8.2). Any cell that wires a restart through them
   has the same latent defect.
5. **The threshold ≈ 21.1 is an extrapolation** between 19.21 and 13.51 on one
   side and from 27.20 on the other. No checkpoint in the ladder sits inside
   (19.2, 27.2), so the crossing is fitted, not observed.
