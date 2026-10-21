# GAP-67 — second-moment-preserving restart blend

**Date:** 2026-10-21
**Status:** closed — **design hypothesis falsified**. The blend's second moment is
not the control variable: the correction is a null with the wrong sign on 4/4
checkpoints (§5, §6.1). The R5c cost on the calibrated checkpoints is a **mean
shift**, not a dispersion effect (§2.1, §6.5).
**Question:** is the R5c fidelity cost (production +0.63 %/+2.93 %, w16e1_60k
+1.4 %/+3.6 %) caused by the blend's second-moment deficit, and does restoring
that moment remove the cost?
**Answer:** no.

---

## 0. Pre-registration (written before any code change)

The gap entry in `todo.json` carried acceptance criterion (1) as

> `rho_framework/rho_base in [0.95,1.05] on all four MNIST checkpoints`

**That criterion is ill-posed and is being revised here, before the run, not
after.** The reason is measured, not argued: on `w16e1_10k` and `w16e1_5k` the
framework's FID *improves* by −11.4 % and −19.6 % while `rho` falls to 0.68 and
0.55 of baseline. Requiring `rho` ratio ≈ 1 on those two checkpoints means
requiring the restart to stop changing the sample distribution — i.e. requiring
the framework to stop working. Criterion (1) can only be applied where the
framework *loses*, which is the two well-calibrated checkpoints.

Revised, pre-registered readings:

| # | reading | falsifies if |
|---|---|---|
| R1 | `rho_framework/rho_base` rises to ≥ 0.97 on `production` (0.953 now) and ≥ 0.95 on `w16e1_60k` (0.867 now) | it does not move, or moves the wrong way |
| R2 | on those two checkpoints the paired chunk ΔFID moves toward 0 (≤ +0.5 %) | it stays at +1.4…+3.6 % |
| R3 | on `w16e1_10k` / `w16e1_5k` the −11.4 % / −19.6 % wins **shrink toward 0** | the wins survive intact |
| R4 | the measured output-dispersion response to an input-dispersion change is ≈ constant across the four checkpoints | it is not, i.e. the map is not a scalar dispersion operator |

R3 is the load-bearing one. If the wins survive, the framework's value on
under-trained models is **not** a dispersion effect and the GAP-64 sign rule is
only a near-calibration rule. If the wins shrink, the restart operator is a
dispersion knob and nothing else — a stronger and much cleaner mechanism claim
than the current "sometimes it helps, sometimes it hurts".

No new seeds. One draw (seed 42), reusing the frozen `gap57` baselines.

## 1. Derivation — where the variance goes

Flow-matching path on MNIST: `x_t = (1-t) x0 + t x1`, `x0 ~ N(0,1)`,
`x1 ~ data`. The restart writes the path state at `t = m`:

    y = m * x1_hat + (1 - m) * x0_fresh,     m = 1 - beta

and integrates `[m, 1]`. `x1_hat` is the previous round's endpoint, `x0_fresh`
is fresh noise. If the two are independent, the blend's per-coordinate variance is

    Var(y) = m^2 * v_hat + (1 - m)^2,        v_hat = Var(x1_hat)

while the **correct** path state at `t = m` has

    D_m = m^2 * s^2 + (1 - m)^2,             s^2 = Var(data)

So the blend is under-dispersed by

    Var(y) / D_m = 1 - m^2 (s^2 - v_hat) / D_m

i.e. the model's own dispersion error `s^2 - v_hat` is fed back into the
restart state, scaled by `m^2/D_m`. At `m = 0.5`, `D_m ≈ 0.32`, so the feedback
gain is `m^2/D_m ≈ 0.79`.

The correction that removes the deficit is a scalar on the fresh noise:

    c^2 = 1 + m^2 (s^2 - v_hat) / (1 - m)^2,      y' = m x1_hat + (1-m) c x0_fresh

which gives `Var(y') = D_m` exactly, and leaves `Corr(y', x1_hat)` unchanged
(correlation is scale-invariant, so the memory term is preserved by
construction).

**Which `s^2`?** Two references are available. The *data* variance asks "is the
blend on the true path"; the *baseline* variance `v_base` asks "is the restart a
fixed point of the model's own distribution". The acceptance criterion is a
ratio against baseline, so `v_base` is the right target — and it is measurable
from one baseline pass, with no reference set. The screen below uses `v_base`.

### 1.1 This is a post-map, and Theorem 5 must be restated

Theorem 5 (`docs/audit/wave350-thm5.md`, Eq. 6) bounds the operator's value-add
with two channels: a one-shot correction `(1-m) * eps_theta * 1{k=1}` and an
accumulating blend-variance term `(1-m) * sigma_blend^2 * (k-1) * sqrt(k/L)`.
The rescale multiplies the deviation from the blended mean by `c`, so **both
channels scale by the same `c`**: the sign of `VA_k` and therefore the `k* = 1`
regime boundary are unchanged, but the bound's magnitude is `c` times larger.

That means the rescale does **not** improve the per-trajectory squared error —
it enlarges it by `c^2`. What it fixes is the *marginal*, which is what FID
measures. Stated plainly: the correction trades trajectory-wise MSE for
distributional fidelity. Theorem 5's identity survives only for the convex
part; the rescale must be stated as a post-map and the theorem re-stated as
holding up to the factor `c`. This is recorded now so it cannot be quietly
skipped later.

## 2. What the existing samples already say (no GPU)

Measured from the frozen `gap57-equal-nfe-ladder-n1000/*_s42` artifacts, seed
42, N=1000, NFE=50, `cosine` arm, `m = 0.5`.

Pixel space (`784` dims, per-dimension variance averaged):

| ckpt | `v_base` | `v_cos` | `v_cos/v_base` | `rho_cos/rho_base` (128-d proj) |
|---|---:|---:|---:|---:|
| `production` | 0.2153 | 0.2049 | 0.9520 | 0.9527 |
| `w16e1_10k` | 0.2073 | 0.1415 | 0.6824 | 0.6750 |
| `w16e1_60k` | 0.1947 | 0.1691 | 0.8687 | 0.8674 |
| `w16e1_5k` | 0.2762 | 0.1529 | 0.5536 | 0.5465 |

Two facts follow, both of which the derivation had to predict:

1. **The contraction is isotropic.** The pixel-space variance ratio and the
   128-dim projection `rho` ratio agree to within 1.5 % on all four
   checkpoints. The shrinkage is a global scale, not a few collapsed
   directions — so a scalar `c` is the right functional form, and the
   "per-direction coefficient" alternative in the gap entry is not needed.
2. **The map amplifies the input deficit by 4.6–6.1×, and roughly uniformly.**
   The right reference for "no change" is the *model's own* dispersion
   `v_base`, not the data variance: the target is `rho` ratio 1, i.e. the
   restart must be a fixed point of the model's own distribution. Then
   `D_m' = m^2 v_base + (1-m)^2` and

   | ckpt | `D_m'` | `Var(y)` | input deficit | output deficit | amplification |
   |---|---:|---:|---:|---:|---:|
   | `production` | 0.3038 | 0.3012 | 0.86 % | 4.83 % | 5.64× |
   | `w16e1_10k` | 0.3018 | 0.2854 | 5.45 % | 31.74 % | 5.82× |
   | `w16e1_60k` | 0.2987 | 0.2923 | 2.14 % | 13.15 % | 6.14× |
   | `w16e1_5k` | 0.3191 | 0.2882 | 9.66 % | 44.64 % | 4.62× |

   The amplification spans 4.6–6.1× (mean 5.6×) — close enough to a constant
   that the operator behaves as a **scalar dispersion map** to first order.
   That is R4, answered affirmatively from existing samples before any GPU
   time. It also means a single scalar `c` is the right functional form: a
   per-direction correction would be fitting noise.

Required scale, `c^2 = 1 + m^2 (v_base - v_hat) / (1-m)^2`, `m = 0.5`:

| ckpt | `c^2` | `c` |
|---|---:|---:|
| `production` | 1.0104 | 1.0052 |
| `w16e1_10k` | 1.0658 | 1.0324 |
| `w16e1_60k` | 1.0256 | 1.0127 |
| `w16e1_5k` | 1.1233 | 1.0599 |

Note what this reference choice buys: `v_base` is measurable from **one
baseline pass**, with no reference set and no test data. So the calibration is
not oracle-dependent in principle — it costs one extra sampling pass, which is
exactly the pass every evaluation already runs. It is still labelled
"oracle-calibrated" below because the numbers in this table were taken from
the *already measured* arm rather than from a fresh calibration pass.

**These `c` values are oracle-calibrated**: they use `v_hat` measured from the
arm being corrected. That is acceptable for a mechanism screen (the question is
"does the second moment explain it", not "is this deployable yet") and is
labelled as such everywhere. A reference-free estimator is a follow-up, not
part of this gap.

### 2.1 The FID decomposition says the gap is mean-driven (pre-registered)

Before the corrected arms finished, the Fréchet decomposition
`FID = ||mu_g - mu_ref||^2 + tr(S_g + S_ref - 2 (S_g S_ref)^{1/2})` was computed
on the same frozen samples. It changes what R2 can possibly achieve:

| ckpt | arm | FID | mean term | covariance term |
|---|---|---:|---:|---:|
| `production` | baseline | 9.967 | 4.881 | 5.087 |
| `production` | cosine | 10.855 | 5.641 | 5.215 |
| `w16e1_10k` | baseline | 16.963 | 8.632 | 8.331 |
| `w16e1_10k` | cosine | 17.383 | 9.836 | 7.547 |
| `w16e1_60k` | baseline | 11.401 | 5.585 | 5.816 |
| `w16e1_60k` | cosine | 13.159 | 7.065 | 6.094 |
| `w16e1_5k` | baseline | 24.498 | 13.138 | 11.360 |
| `w16e1_5k` | cosine | 22.133 | 14.022 | 8.111 |

Reading: the **mean term increases on all four checkpoints** (+0.76, +1.20,
+1.48, +0.88). The covariance term moves in *both* directions (worse on
`production`/`60k`, better on `10k`/`5k`). So on the two checkpoints where the
framework loses, the loss is almost entirely a mean shift:

- `production`: covariance contributes +0.128 of the +0.888 gap (14 %).
- `w16e1_60k`: covariance contributes +0.278 of the +1.758 gap (16 %).

**P5 (pre-registered): the second-moment correction recovers at most ~20 % of
the headline gap on the two calibrated checkpoints, and R2 therefore fails.**
If it recovers more, the amplification argument in §2 is incomplete and the
covariance term must be interacting with the mean.

### 2.2 The chunk-level test and the N=1000 headline disagree in sign

Also measured before the corrected arms, and independent of GAP-67:

| ckpt | N=1000 headline Δ | reported chunk-mean Δ |
|---|---:|---:|
| `production` | **+8.91 %** | +0.63 % |
| `w16e1_10k` | **+2.47 %** | **−11.37 %** |
| `w16e1_60k` | **+15.42 %** | +1.53 % |
| `w16e1_5k` | **−9.65 %** | −19.56 % |

The signs disagree on `w16e1_10k`. The chunk FID is computed at n = 100 per
chunk, where the Fréchet estimator is biased upward, and the bias scales with
`tr(S_g)` — so the *shrunk* arm is systematically rewarded. This is the same
small-N pathology already recorded for N=200, at a smaller N. The headline
N=1000 number is the only quotable one, and it says the framework hurts
`production` and `w16e1_60k` far more than the chunk test reports, and hurts
`w16e1_10k` rather than helping it.

**P6 (pre-registered): the corrected arm's chunk-level Δ will move toward 0
faster than its headline Δ, because the chunk statistic is measuring the
dispersion rather than the quality.** If so, every R5c number quoted from the
chunk test is a dispersion proxy and must be re-derived at N=1000 before it can
support any claim. That is recorded as a follow-up gap, not fixed here.

## 3. Implementation

`MnistFmAdapter(..., restart_noise_scale: float = 1.0)`. The scalar multiplies
`x0_fresh` after the clip and before the blend. Default `1.0` takes a guarded
branch that does not execute the multiply, so the default path stays
byte-identical. The scale enters the restart digest only when it is not `1.0`,
following the GAP-56 interval precedent.

`blender` protocol note: `adaptive_reflow/algorithm/blender/` ships four
families and the module docstring admits the adapters inline the same math, so
the protocol is still unused. Wiring the scale through `LinearBlender` would be
the right home, but that is a refactor of a frozen surface and is **not** part
of this gap — recorded as a follow-up instead.

## 4. What was run

`tools/gap67_noise_scale_screen.py` — `cosine` arm only, four checkpoints,
`c` from the table in §2, N=1000, NFE=50, seed 42, baselines reused verbatim
from `verification_outputs/gap57-equal-nfe-ladder-n1000/<ckpt>_s42/baseline_samples.npz`
(RK4 is deterministic and `shared_prior` makes round 0 byte-identical, so the
baseline does not need re-sampling).

**Control (run first).** `production` at `c = 1.0` through the new code path:

| quantity | this run | gap57 frozen | match |
|---|---:|---:|---|
| `rho` | 0.7449 | 0.7449 | exact |
| FID headline | 10.8551 | 10.8551 | exact |
| chunk Δ | +0.63 % | +0.63 % | exact |
| `p` (Bonferroni, 3 arms) | 0.948 | 0.948 | exact |

So the `restart_noise_scale` branch is byte-identical at its default and the
screen's `c = 1.0` column is directly comparable to the frozen ladder.

*(corrected-arm numbers appended below after the run)*

## 5. Observed

All four checkpoints, seed 42, N=1000, NFE=50, `cosine` arm. "frozen" = the
`gap57` `c = 1.0` column; "corrected" = this run.

| ckpt | `c` | `c^2 - 1` | `rho` ratio frozen → corrected | predicted | pixel-variance ratio frozen → corrected | chunk ΔFID | N=1000 headline FID |
|---|---:|---:|---:|---:|---:|---:|---:|
| `production` | 1.0052 | +0.0104 | 0.9527 → **0.9524** | 1.00 | 0.9520 → 0.9517 | +0.63 % → +0.67 % | 10.855 → 10.866 |
| `w16e1_10k` | 1.0324 | +0.0658 | 0.6750 → **0.6716** | 1.00 | 0.6824 → 0.6789 | −11.37 % → −10.64 % | 17.383 → 17.613 |
| `w16e1_60k` | 1.0127 | +0.0256 | 0.8674 → **0.8657** | 1.00 | 0.8687 → 0.8670 | +1.53 % → +1.67 % | 13.159 → 13.200 |
| `w16e1_5k` | 1.0599 | +0.1234 | 0.5465 → **0.5396** | 1.00 | 0.5536 → 0.5466 | −19.56 % → −18.01 % | 22.133 → 22.772 |

Causal sensitivity, `d(rho ratio) / d(c^2)`:

| ckpt | measured | predicted by §1 |
|---|---:|---:|
| `production` | **−0.033** | +5.64 |
| `w16e1_10k` | **−0.051** | +5.82 |
| `w16e1_60k` | **−0.067** | +6.14 |
| `w16e1_5k` | **−0.056** | +4.62 |

The correction is a **null with the wrong sign**, two orders of magnitude below
the prediction, on all four checkpoints, and it makes the chunk-level ΔFID
uniformly slightly worse (4/4). R1, R2 and R3 all fail as stated. P5 holds
(the gap is not recoverable from the second moment). P6 holds (the chunk Δ
moved *toward* 0 — −11.37 → −10.64 and −19.56 → −18.01 — while the N=1000
headline moved *away* from 0 — 17.383 → 17.613 and 22.133 → 22.772 — the two
statistics respond to the dispersion change in opposite directions, which is
the dispersion-proxy signature).

## 6. Interpretation

### 6.1 The design hypothesis is falsified

`Var(y)` is not the variable that controls `rho`. Raising the fresh-noise scale
by 1–12 % moved the output dispersion by 0.03–0.7 %, in the wrong direction.
The map from `t = m` to `t = 1` is **scale-normalizing**: the learned velocity
field maps a neighbourhood of the path back onto the path, so a small change in
the injected noise's magnitude is absorbed. There is no gain to be had from
re-weighting the blend's second moment, because the operator does not read that
moment.

### 6.2 Why §2's cross-checkpoint "amplification" was spurious

§2 regressed the output deficit on the input deficit **across four
checkpoints**, and got a tight 4.6–6.1×. That looked like a causal gain. It was
not: both deficits are monotone in model quality, so the cross-section
correlates two consequences of the same latent variable. The dose-response
above is the causal measurement — the same checkpoint, one knob, two points —
and it gives ≈ −0.05×. **The cross-section was confounded and the intervention
was not.** This is the reason the screen was worth running before the
confirmation ladder: the 3 h ladder would have produced the same null with
three seeds and a much larger bill.

### 6.3 What does explain the contraction

The restart injects *independent* noise at `t = m` and integrates to `t = 1`.
For each sample, the endpoint is therefore (approximately) a conditional
expectation `E[x1 | x_m]` rather than a draw from `p(x1)`. The law of total
variance gives `Var(E[x1 | x_m]) <= Var(x1)`, with equality only when `x1` is
measurable with respect to `x_m` — i.e. only when no noise was injected. The
contraction is therefore a property of **conditioning**, not of the blend's
arithmetic, and no rescale of the injected noise can remove it.

This makes a sharper prediction than the variance story did, and one that can
be tested without ambiguity: the contraction should be monotone in the injected
noise fraction `1 - m` and should vanish at `m = 1`. `m = 1` is the trivial
"do not restart" arm, so the prediction is not practically useful — but it is
what distinguishes this explanation from the falsified one, and it should be
tested before the claim is written into the paper as a mechanism.

### 6.4 Consequence for Theorem 5

Theorem 5's second term is `(1-m) * sigma_blend^2 * (k-1) * sqrt(k/L)`, the
variance of the *deviation from the corrected prior*. That is a different
object from the *marginal dispersion* measured by `rho`. §1.1 predicted the
rescale would scale both channels by `c`; the experiment shows the marginal
channel does not respond at all, so the two objects are not merely different in
magnitude — they are decoupled. Any sentence in the paper that reads Theorem
5's variance term as an explanation of the observed `rho` contraction is
conflating them and must be rewritten. **Recorded as a flag only; the paper
surface is frozen and is not edited here.**

### 6.5 What survives

* The `restart_noise_scale` knob is kept: default `1.0` is byte-identical
  (control in §4), and the knob is the instrument that produced this
  falsification. It is a diagnostic, not a proposed method.
* The pixel-space / projection-space agreement (§2 point 1) stands and is
  useful on its own: the contraction is isotropic.
* The FID decomposition (§2.1) stands and is the more useful diagnostic: the
  R5c cost on the calibrated checkpoints is a **mean shift** (+0.76 and +1.48
  of the +0.89 and +1.76 headline gaps), not a covariance effect. That
  redirects the mechanism question from "dispersion" to "why does the restart
  move the mean", which is the next gap, not this one.

## 7. Unresolved

* The conditional-mean explanation (§6.3) is **argued, not measured**. It has
  a clean test (monotone in `1 - m`, vanishing at `m = 1`) that was not run.
  Until it is, the honest status is "the second-moment explanation is
  falsified; the conditional-mean explanation is the surviving candidate".
* The mean-shift mechanism is untouched. Nothing here says why the restart
  moves the mean by +0.76 to +1.48 in FID units, or whether that is fixable.
* The chunk-vs-headline sign flip (§2.2) is a defect in the R5c *statistic*,
  independent of GAP-67. It is not fixed here.


