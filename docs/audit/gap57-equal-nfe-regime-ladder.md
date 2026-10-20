# GAP-57 — the GAP-35 regime ladder, re-measured at equal total NFE

**Status:** complete at `N = 1000`; the `N = 200` screen is retained only as a
screen (see §7).
**Increment:** `gap57-equal-nfe-ladder` (N=200) and
`gap57-equal-nfe-ladder-n1000` (N=1000, primary).
**Supersedes nothing.** Additive to `gap35-cross-domain.md`,
`gap56-restart-t0-defect.md` and `gap53-initial-condition-contraction.md` §9.

---

## 0. TL;DR

GAP-35 reported that the restart gain is monotone in the model's optimisation
budget: the framework wins by 25–28 % on under-trained MNIST-FM checkpoints and
regresses once the velocity field converges. **Every framework arm in that table
ran at the legacy per-round cap (cosine 25 / codim 48 / evidence 25 total NFE)
against a 50-NFE baseline**, so the size of each win was confounded with
compute.

Re-measured with **50 NFE on both sides at N = 1000**, the ladder survives:

| ckpt | baseline FID | Δ% at equal NFE (best arm) | Δ% at legacy NFE (best arm) | compute share of the win |
|---|---:|---:|---:|---:|
| `w16e1_5k` | 24.49 | **−9.37** (cosine) | −22.52 (codim) | **13.15 pp** |
| `w16e1_10k` | 16.96 | +2.81 (cosine) | −7.10 (evidence) | 9.91 pp |
| `w16e1_60k` | 11.38 | +15.59 (cosine) | +16.88 (evidence) | −1.29 pp |
| `production` | 9.99 | +9.52 (cosine) | — | — |

Least squares of Δ % on the baseline FID over 12 (checkpoint × draw) points:
slope **−1.177 %/FID unit**, R² **0.855**, zero crossing at baseline FID
**≈ 22.5**. Record-level paired bootstrap: **3 wins / 27 losses / 6 ties** over
36 cells; the only wins are the three `w16e1_5k` cosine cells, where the CI
excludes zero in every draw.

**The honest headline for this mechanism is −9.4 % at matched NFE, not
−28.4 %.** About 58 % of the historical `w16e1_5k` win was compute.

A second, independent defect surfaced while doing this and is recorded in §7:
**FID is badly biased upward at `n = 200`**, which inflated every earlier
`N = 200` effect size by 40–65 % and flipped one sign.

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
run is **−22.52 %**.

---

## 2. Protocol

Held fixed across all 12 runs:

| item | value |
|---|---|
| driver | `scripts/wave191_p3_mnist_sweep.py` |
| N | **1000** (primary); 200 (screen, §7) |
| draws | seeds 42 / 43 / 44 via `--seed-keyed-prior` (genuinely distinct priors; verified byte-distinct) |
| pairing | `--shared-prior` — baseline and all arms share the round-0 prior *within* a draw |
| budget | `--equal-total-nfe --total-nfe 50`, `--nfe-allocation scheduler` |
| rounds | `--n-rounds 4`, `--beta-schedule equal_budget`, `--beta-framework 0.5` |
| restart | `--restart-t0-mode memory` (round `r` starts at `t = 1 − β_r`) |
| threads | `OMP_NUM_THREADS=1` (BLAS oversubscription is 12.7× slower, GAP-56 §8.3) |
| estimator | `fid_headline` (full 10k MNIST reference), record-level paired bootstrap B=2000, `BOOT_SEED=20261020`, Bonferroni over 3 arms, bias-corrected interval (§7.2) |

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
bash reproduce/gap57_equal_nfe_ladder.sh 6      # N=200 screen, 12 runs, 14m51s
# N=1000: same flags with --n-samples 1000, 12 runs, ~45 min at 6 concurrent
python3 tools/gap57_regime_ladder.py --root verification_outputs/gap57-equal-nfe-ladder-n1000
python3 tools/gap56_r5c_paired_bootstrap.py --run-dir <dir> --out <dir>/paired_bootstrap.json
```

---

## 3. Observed — per-draw, N = 1000

Equal total NFE = 50 on both sides.

| ckpt | seed | baseline FID | cosine | codim | evidence | Δ% cos | Δ% codim | Δ% evid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `w16e1_5k` | 42 | 24.4977 | 22.1330 | 24.5235 | 24.4815 | −9.65 | +0.11 | −0.07 |
| `w16e1_5k` | 43 | 24.5911 | 22.3419 | 24.6815 | 24.6995 | −9.15 | +0.37 | +0.44 |
| `w16e1_5k` | 44 | 24.3764 | 22.1088 | 24.3872 | 24.4667 | −9.30 | +0.04 | +0.37 |
| `w16e1_10k` | 42 | 16.9632 | 17.3826 | 18.7859 | 18.2508 | +2.47 | +10.74 | +7.59 |
| `w16e1_10k` | 43 | 17.0408 | 17.5427 | 18.8753 | 18.3489 | +2.95 | +10.77 | +7.68 |
| `w16e1_10k` | 44 | 16.8724 | 17.3804 | 18.6516 | 18.0891 | +3.01 | +10.55 | +7.21 |
| `w16e1_60k` | 42 | 11.4009 | 13.1593 | 13.6144 | 13.1757 | +15.42 | +19.41 | +15.57 |
| `w16e1_60k` | 43 | 11.3469 | 13.0983 | 13.4944 | 13.1464 | +15.44 | +18.93 | +15.86 |
| `w16e1_60k` | 44 | 11.3908 | 13.2034 | 13.6630 | 13.2351 | +15.91 | +19.95 | +16.19 |
| `production` | 42 | 9.9670 | 10.8551 | 11.2670 | 10.9111 | +8.91 | +13.04 | +9.47 |
| `production` | 43 | 9.9906 | 10.9692 | 11.2849 | 11.0317 | +9.79 | +12.95 | +10.42 |
| `production` | 44 | 10.0103 | 10.9966 | 11.2716 | 11.1228 | +9.85 | +12.60 | +11.11 |

The baseline is now reproducible across draws to ±0.11 FID at worst — an order
of magnitude tighter than at `N = 200` (±0.71), because the estimator, not the
prior, dominated the `N = 200` spread.

## 4. Observed — three-draw summary, against the legacy protocol

Both Δ % columns are **headline ratios**, so the two protocols are compared with
the same estimator.

| ckpt | baseline FID (mean ± sd) | Δ% by arm, equal NFE | best arm | Δ% by arm, GAP-35 legacy | compute share |
|---|---:|---|---:|---|---:|
| `w16e1_5k` | 24.488 ± 0.108 | cos **−9.37** / codim +0.17 / evid +0.25 | cosine −9.37 | cos −21.82 / codim −22.52 / evid −22.13 | **+13.15 pp** |
| `w16e1_10k` | 16.959 ± 0.084 | cos +2.81 / codim +10.69 / evid +7.49 | cosine +2.81 | cos +1.61 / codim +4.04 / evid −7.10 | +9.91 pp |
| `w16e1_60k` | 11.380 ± 0.029 | cos +15.59 / codim +19.43 / evid +15.87 | cosine +15.59 | cos +17.83 / codim +31.16 / evid +16.88 | −1.29 pp |
| `production` | 9.989 ± 0.022 | cos +9.52 / codim +12.87 / evid +10.34 | cosine +9.52 | — | — |

"Compute share" = equal-NFE best-arm Δ % minus legacy best-arm Δ %. Positive
means the legacy protocol *overstated* the win.

## 5. Observed — record-level paired bootstrap, N = 1000

Full 36-cell table: `python3 tools/gap57_regime_ladder.py --root
verification_outputs/gap57-equal-nfe-ladder-n1000` §"Record-level paired
bootstrap". Summary:

| checkpoint | cells favouring the framework | verdict |
|---|---:|---|
| `w16e1_5k` | **3 / 9** (cosine 3/3; codim and evidence tie) | cosine wins in every draw, CI excludes 0 |
| `w16e1_10k` | 0 / 9 | baseline wins in every cell |
| `w16e1_60k` | 0 / 9 | baseline wins in every cell |
| `production` | 0 / 9 | baseline wins in every cell |

Sign census: **3 wins / 27 losses / 6 ties**.

The winning cells: Δ = −2.365, −2.249, −2.268 FID, CIs
`[−2.620, −2.122]`, `[−2.495, −2.000]`, `[−2.505, −2.028]`, 100 % of bootstrap
replicates favouring the framework in all three.

## 6. Observed — the ladder

Least squares of Δ % (mean over the three arms) on the baseline FID, 12 points:

- slope **−1.177 % per FID unit**
- intercept **+26.45 %**
- R² **0.855**
- zero crossing at baseline FID **≈ 22.48**

All four checkpoints are `base_channels=16`, and their baselines are
step-insensitive at NFE = 50 (GAP-35 §4: `w16e1_5k` 27.2361 → 27.2311 across
50/100/200 steps), so the equal-NFE comparison does not starve the baseline.

---

## 7. The estimator defect this increment uncovered

### 7.1 Observation

While bootstrapping the `N = 200` ladder, the percentile interval repeatedly
**excluded its own point estimate** (e.g. `w16e1_5k_s42` cosine: Δ = −3.575,
95 % percentile CI `[−5.510, −4.223]`). A bootstrap interval that does not
contain the estimate is a symptom of a biased functional, not a coding error.

### 7.2 Calibration

`tools/gap56_fid_small_n_bias.py`, `d = 128`, 10 000-sample reference,
10 repetitions. `X ~ N(0, I)` has a true FID of 0 against the reference;
`Z ~ N(0, 1.3² I)` has a true FID of 11.52.

| n | E[FID X] (true 0) | E[FID Z] (true 11.52) | E[Δ̂] (true 11.52) | Δ bias |
|---:|---:|---:|---:|---:|
| 50 | 108.19 | 154.97 | 46.79 | +10.30 |
| 100 | 57.27 | 85.99 | 28.72 | +11.62 |
| **200** | **23.98** | **42.98** | **18.99** | **+6.77** |
| 500 | 9.27 | 23.52 | 14.25 | +2.53 |
| **1000** | **4.73** | **17.73** | **12.99** | **+1.26** |
| 2000 | 2.56 | 14.78 | 12.22 | +0.63 |

The bias is O(1), not O(1/n): `Tr(√(Σ̂ Σ_ref))` is concave in `Σ̂`, and at
`n = 200` with `d = 128` the sample covariance is noisy enough (`n/d = 1.56`)
that Jensen's gap dominates. A bootstrap resample of `n` points with duplicates
has an *even noisier* covariance, which adds a second upward shift — that is why
the raw percentile interval sits below the point estimate.

### 7.3 Consequence, and what was done

- The bootstrap tool now reports a **bias-corrected percentile interval**
  (`delta_ci95`, plus the raw `delta_boot_bias`, the percentile and the basic
  interval for transparency) and a p-value consistent with it. Every interval in
  §5 contains its point estimate.
- **`N = 200` effect sizes are not usable as estimates.** The `N = 200` ladder is
  kept in `verification_outputs/gap57-equal-nfe-ladder/` as a screen only.
- The screen was not merely noisy, it **flipped a sign**: at `N = 200`,
  `w16e1_10k` cosine read −1.89 % (a win); at `N = 1000` it reads **+2.81 %**
  (a significant regression). That is why §3–§6 use `N = 1000`.
- GAP-56 §5.5 (N=200) carries a matching caveat note; its signs and ordering
  stand, its magnitudes are inflated.

---

## 8. Interpretation

1. **The mechanism is real.** At `w16e1_5k` the framework beats the baseline by
   9.2–9.7 % in every draw at `N = 1000`, at the same total NFE, with a
   record-level CI that excludes zero. This is not a compute artifact and not a
   chunk-estimator artifact.
2. **The historical magnitude was inflated twice over.** GAP-35's −22.52 %
   headline on the same checkpoint becomes −9.37 % when the compute is matched:
   **13.15 pp of the 22.5 pp win was the extra NFE**, about 58 %. The paper may
   not quote −25.39 % (chunk-mean), −28.43 % (smoke checkpoint), or any
   `N = 200` number as this mechanism's effect size.
3. **The sign flip is a property of the model, not of the budget.** With NFE
   held at 50 everywhere, the sign still flips between baseline FID 24.5 and
   17.0, and the fitted crossing is at 22.5. The mechanism corrects residual
   velocity-field error; once the field has converged there is no residual left
   to correct and the restart only adds variance.
4. **The best arm changes with the protocol.** Legacy best arm is
   `codimension_sheet` at 5k and `evidence_driven` at 10k/60k; at equal NFE the
   best arm is `cosine` at every checkpoint. This is mechanical: under the
   scheduler allocation `cosine` receives `[25, 18, 6, 1]` — half the budget on
   round 0 — whereas `codimension_sheet` receives `[13, 12, 12, 13]`. The
   front-loaded allocation is what makes the restart useful.
5. **Only one of the three arms survives at all.** At `w16e1_5k`, codim and
   evidence are ties (+0.17 %, +0.25 %). The win is a `cosine`-allocation
   property, not a property of "the framework" in general.

---

## 9. What this changes, and what it does not

**Changes.**

- R5c's effect size at matched NFE is **−9.37 %** on `w16e1_5k`
  (baseline 24.488 ± 0.108), significant in 3/3 draws.
- The mechanism has a **documented boundary**: baseline FID ≳ 22.5 favours the
  framework, baseline FID ≲ 17 favours the baseline.
- The GAP-35 ladder is confirmed *and* corrected: the sign pattern survives,
  the magnitude falls to about 42 % of the legacy value.
- The FID estimator's small-`n` bias is now measured and documented (§7).

**Does not change.**

- The production-checkpoint R5c cell still regresses (+9.52 %, 9/9 cells,
  record-level CI excludes zero). No sampler-side configuration tested in
  GAP-55/56/57 beats the baseline there.
- The historical −28.43 % remains a smoke-checkpoint artifact and −25.39 %
  remains a chunk-mean artifact. Neither is a valid target.
- No frozen surface (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
  `docs/drafts/paper-A-final.*`, `tnnls_submission/**`) is modified by this
  increment.

---

## 10. Unresolved gaps

1. **One architecture family, one width.** All four checkpoints are
   `base_channels=16` MNIST-FM. The ladder is a statement about *this* model
   family.
2. **The ladder axis is confounded.** `w16e1_5k → 10k → 60k → production` varies
   optimisation steps, weight norm (17.27 → 17.46 → 18.25 → 19.19) and the
   baseline's own FID together. The regression of Δ % on baseline FID describes
   this ladder; it is not a causal statement about any one variable.
3. **Round count and β were not re-tuned at `w16e1_5k`.** The configuration is
   the one fixed on `production` in GAP-56 (`R=4`, `β=0.5`, scheduler
   allocation). At `w16e1_5k` round 3 receives a single Euler step; `R=2` or
   `R=3` would give round 0 more of the budget. Untested, and deliberately not
   tuned after seeing the result.
4. **Only the MNIST adapter honours `t0`/`t1`.** The other 11 adapters still
   hard-code `[0, 1]` (GAP-56 §8.2). Any cell that wires a restart through them
   has the same latent defect.
5. **The threshold ≈ 22.5 is an extrapolation** between 17.0 and 24.5. No
   checkpoint in the ladder sits inside (17.0, 24.5), so the crossing is fitted,
   not observed.
6. **FID remains biased at `N = 1000`** (+4.73 on a true 0, +1.26 on a true
   11.52). The paired design cancels most of it, but the *absolute* FIDs in §3
   are not comparable with FIDs computed at other `n`.
