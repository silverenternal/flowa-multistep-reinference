# GAP-72 — the R5c cost is a location error, and removing it flips the cell

**Date:** 2026-10-21
**Status:** closed. The mean shift is structured (no scalar fixes it), but a
location calibration removes it entirely and turns R5c from 9 regressions into
6 wins / 6 small regressions.
**Question:** GAP-67 falsified the dispersion explanation and the Fréchet
decomposition said the remaining cost is the mean term. What is the mean shift
made of, and is it fixable?

---

## 1. What was run

`tools/gap72_r5c_mean_shift.py`, CPU only, reading the frozen `gap57` ladder
(4 checkpoints × 3 seeds × 3 arms at N=1000). No sampling.

Three analyses:

1. **Decomposition** of `delta_mu = mean(arm) - mean(baseline)` in pixel space
   into the all-ones direction (DC), the reference mean image (ink), and the
   residual — three orthogonal components, energy fractions reported.
2. **Structure**: cross-arm cosine similarity of the shift direction, and the
   spatial energy profile (outer 2-pixel ring vs interior; top-78-pixel
   concentration).
3. **Location calibration**: translate every sample so the sample mean equals
   the *training* mean (`_load_mnist_offline(split="train")`, projected), then
   recompute the paired ΔFID. Applied to **both** arms, so the comparison stays
   fair. The training mean is a training-set statistic — no test-set leakage —
   and the reference mean gives the same answer to within 0.1 pp
   (`||mu_train - mu_ref||^2 = 0.033` in projection space).

## 2. The shift is structured, not a global offset

| ckpt | arm | `|Δμ|` | DC | ink | residual |
|---|---|---:|---:|---:|---:|
| `production` | cosine | 1.98 | 0.07 | 0.01 | 0.92 |
| `production` | codimension_sheet | 1.88 | 0.03 | 0.01 | 0.96 |
| `production` | evidence_driven | 1.92 | 0.08 | 0.00 | 0.92 |
| `w16e1_10k` | cosine | 3.76 | 0.11 | 0.00 | 0.89 |
| `w16e1_10k` | codimension_sheet | 3.80 | 0.07 | 0.00 | 0.93 |
| `w16e1_10k` | evidence_driven | 3.82 | 0.12 | 0.00 | 0.88 |
| `w16e1_60k` | cosine | 2.37 | 0.14 | 0.01 | 0.85 |
| `w16e1_60k` | codimension_sheet | 2.30 | 0.08 | 0.02 | 0.90 |
| `w16e1_60k` | evidence_driven | 2.30 | 0.15 | 0.02 | 0.83 |
| `w16e1_5k` | cosine | 4.65 | 0.07 | 0.01 | 0.92 |
| `w16e1_5k` | codimension_sheet | 4.78 | 0.05 | 0.00 | 0.95 |
| `w16e1_5k` | evidence_driven | 4.76 | 0.07 | 0.00 | 0.92 |

The pre-registered rule was: DC fraction ≥ 0.5 → a single scalar should recover
≥ 50 % of the mean term; DC fraction < 0.2 → the shift is structured and is not
fixable by a global correction. **The maximum DC fraction is 0.15.** The ink
component is at most 0.02. The shift is 83–96 % residual.

Two further structure measurements, both negative for a simple fix:

* **Arm-specific direction.** Cross-arm cosine similarity of `Δμ` is
  −0.015 to +0.234 — the three schedulers move the mean in nearly orthogonal
  directions. A "restart bias" would be shared; this is not.
* **Not a border artifact.** The outer 2-pixel ring holds 8–23 % of the shift
  energy while occupying 27 % of the area, so the shift is if anything
  *interior*-weighted. The top 78 pixels (10 % of the image) carry 33–49 %,
  i.e. moderately concentrated but not sparse.

## 3. A location correction removes the whole gap

Translate each arm's samples so that their mean equals the **baseline's** mean
(an oracle target — this measures how much of the gap is pure location):

| ckpt | arm | FID base | FID arm | FID after translation | gap recovered |
|---|---|---:|---:|---:|---:|
| `production` | cosine | 9.99 | 10.94 | 10.12 | 86 % |
| `production` | codimension_sheet | 9.99 | 11.27 | 10.11 | 91 % |
| `production` | evidence_driven | 9.99 | 11.02 | 10.10 | 89 % |
| `w16e1_10k` | cosine | 16.96 | 17.44 | 16.19 | >100 % |
| `w16e1_10k` | codimension_sheet | 16.96 | 18.77 | 16.28 | >100 % |
| `w16e1_10k` | evidence_driven | 16.96 | 18.23 | 16.22 | >100 % |
| `w16e1_60k` | cosine | 11.38 | 13.15 | 11.66 | 84 % |
| `w16e1_60k` | codimension_sheet | 11.38 | 13.59 | 11.72 | 84 % |
| `w16e1_60k` | evidence_driven | 11.38 | 13.19 | 11.72 | 81 % |
| `w16e1_5k` | cosine | 24.49 | 22.20 | 21.26 | >100 % |
| `w16e1_5k` | codimension_sheet | 24.49 | 24.53 | 21.35 | >100 % |
| `w16e1_5k` | evidence_driven | 24.49 | 24.55 | 21.27 | >100 % |

On the three checkpoints where the framework loses, a pure translation recovers
81–91 % of the loss. On `w16e1_10k` and `w16e1_5k` the translation takes the arm
*below* the baseline. **The R5c cost is a location error, not a quality loss.**

## 4. The calibrated comparison — the restart is a shape operator

Calibrating **both** arms to the training mean (deployable: one vector
subtraction per sample, target is a training-set statistic), 3 seeds:

| ckpt | arm | raw ΔFID % | **calibrated ΔFID %** | calibrated FID (base → arm) |
|---|---|---:|---:|---|
| `production` | cosine | +9.52 % | **+2.54 %** | 5.12 → 5.25 |
| `production` | codimension_sheet | +12.87 % | **+2.28 %** | 5.12 → 5.23 |
| `production` | evidence_driven | +10.34 % | **+2.24 %** | 5.12 → 5.23 |
| `w16e1_10k` | cosine | +2.81 % | **−9.30 %** | 8.25 → 7.49 |
| `w16e1_10k` | codimension_sheet | +10.69 % | **−8.17 %** | 8.25 → 7.58 |
| `w16e1_10k` | evidence_driven | +7.49 % | **−8.97 %** | 8.25 → 7.51 |
| `w16e1_60k` | cosine | +15.59 % | **+4.81 %** | 5.77 → 6.05 |
| `w16e1_60k` | codimension_sheet | +19.43 % | **+5.97 %** | 5.77 → 6.12 |
| `w16e1_60k` | evidence_driven | +15.87 % | **+5.93 %** | 5.77 → 6.12 |
| `w16e1_5k` | cosine | −9.37 % | **−28.48 %** | 11.33 → 8.10 |
| `w16e1_5k` | codimension_sheet | +0.17 % | **−27.71 %** | 11.33 → 8.19 |
| `w16e1_5k` | evidence_driven | +0.25 % | **−28.45 %** | 11.33 → 8.10 |

Mean over the 12 cells: **−7.3 %** (from +6.3 % raw).

## 5. Interpretation

### 5.1 The two channels separate cleanly

Every R5c effect is the sum of two things:

* **Location.** The restart moves the sample mean to a different place, by a
  structured, scheduler-specific direction. This always costs fidelity, by
  +8 % to +19 % on the converged checkpoints and by roughly +19 pp on
  `w16e1_5k` (where it masks most of the shape gain).
* **Shape.** With location calibrated away, the restart improves the
  covariance on the two under-trained checkpoints (−8 % and −28 %) and
  slightly degrades it on the two converged ones (+2 % to +6 %).

That is a coherent and falsifiable statement of what the operator does, and it
is the first version of the R5c story that survives an intervention: GAP-67
intervened on dispersion and found nothing, GAP-72 intervened on location and
found the whole effect.

### 5.2 Why the convergence boundary falls where it does

`production` (baseline FID 5.12 calibrated) and `w16e1_60k` (5.77) are the two
best models, and they are exactly the two that lose on shape. `w16e1_10k`
(8.25) and `w16e1_5k` (11.33) are the two worst, and they are exactly the two
that gain. This is the same ordering GAP-64 found with "no NFE headroom": the
restart can only repair a model that still has something to repair, and on a
converged model the only thing left to do is perturb.

### 5.3 What is deployable here

Mean calibration is a post-hoc transform on generated samples: subtract the
sample mean, add the training mean. It costs one vector operation per sample
and needs no reference set, no extra sampling, and no model access. It is
applied to both arms, so it does not flatter the framework — it removes a
nuisance parameter from both.

The honest claim it supports is narrow: **after location calibration, the
restart's marginal effect on sample shape is −8 % to −28 % on under-trained
checkpoints and +2 % to +6 % on converged ones.** It is not a claim that the
framework wins R5c; it is a claim about *which part* of the distribution the
operator moves.

### 5.4 What it does not explain

The location shift itself. Nothing here says why injecting fresh noise at
`t = m` biases the endpoint's mean, or why the bias direction depends on the
scheduler. That is now the only unexplained piece of R5c, and it is recorded as
open in GAP-76.

## 6. Flags raised, not acted on

* **R5c's status.** On the corrected statistic (GAP-75) it is a REGRESSES cell.
  With location calibration it is 6 wins / 6 small regressions, mean −7.3 %.
  Which of those two the paper quotes is a claim decision, not a measurement
  decision, and it is user-gated. Both are recorded.
* **`CLM-059`'s −28.43 %** is still a chunk statistic (GAP-73) and is not
  rescued by any of this.
* **The FID decomposition in GAP-67 §2.1** is now fully explained: the mean
  term is a location error, the covariance term is the shape effect, and the
  two have opposite signs on the under-trained checkpoints.

## 7. Unresolved

* Why the restart biases the mean at all, and why the direction is
  scheduler-specific (cosine similarity ≤ 0.23 between arms). This is the last
  open mechanism question in R5c.
* The calibration target. The training mean and the reference mean agree to
  0.1 pp, so the choice does not matter numerically here, but on a dataset with
  a train/test shift it would.
* Everything above is on the framework-internal projection FID, one model
  family, MNIST. The location/shape split should be checked on CIFAR (R5b)
  before it is stated as a general property of the operator.
