# GAP-73 — the R5c chunk statistic is an n=100 statistic, and it reverses the sign

**Date:** 2026-10-21
**Status:** closed. **The paired chunk test is invalid for R5c.** Every published
R5c delta is either attenuated by 10–14× or has the wrong sign.
**Question:** does the 10-chunk paired t-test that produced every R5c number
measure sample quality, or does it measure sample dispersion?

---

## 1. What was run

`tools/gap73_r5c_nscan.py`, CPU only, reading the frozen
`verification_outputs/gap57-equal-nfe-ladder-n1000/<ckpt>_s42/*_samples.npz`.
No new sampling.

Three measurements per checkpoint, `cosine` arm:

1. **`Delta(N)`** — FID(arm) − FID(baseline) with the *generated* set
   subsampled to N and the *reference* subsampled to the same N, using the
   same generated indices for both arms (paired), averaged over 30 random
   draws at N ∈ {100, 200, 500, 1000}. The matched-N reference reproduces the
   chunk test's regime, which scores 100 generated samples against a
   100-sample reference slice.
2. **The headline** — both arms at their full N=1000 against the full 10 000
   reference. This is the number the sweep already reports as
   `headline_fids`, and it is *not* the number any claim quotes.
3. **The exact chunk test**, reproduced from the sweep's own code path, to
   confirm that measurement 1 is measuring the same thing.

## 2. Observed

| ckpt | Δ(100) | Δ(200) | Δ(500) | Δ(1000) | **headline (10K ref)** | conservative 95 % CI | **chunk test** | chunk p |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| `production` | +1.0 | +3.8 | +6.9 | +8.2 | **+8.91 %** | [+8.32, +9.50] | **+0.64 %** | 0.30 |
| `w16e1_10k` | −10.4 | −5.4 | −0.3 | +1.6 | **+2.47 %** | [+1.35, +3.60] | **−11.36 %** | 2.4e-08 |
| `w16e1_60k` | +2.2 | +6.9 | +12.1 | +14.2 | **+15.42 %** | [+14.35, +16.49] | **+1.55 %** | 0.018 |
| `w16e1_5k` | −19.0 | −14.9 | −11.8 | −10.3 | **−9.65 %** | [−10.36, −8.95] | **−19.55 %** | 3.5e-11 |

The conservative CI is `headline ± 1.96 × sd` with `sd` the spread across the
30 independent draws at N=1000 (0.30–0.58 pp). The bootstrap CI is also in the
artifact but is flagged as biased: resampling with replacement creates
duplicate points, the Fréchet covariance shrinks with ties, and the bootstrap
distribution is consequently not centred on the point estimate.

Three facts, in order of importance:

**2.1 The chunk test *is* Δ(100).** It reproduces the N=100 subsample average
to within 0.6 pp on all four checkpoints (+0.64 vs +1.0, −11.36 vs −10.4,
+1.55 vs +2.2, −19.55 vs −19.0). It is not an estimator of the headline; it is
the headline computed at n=100 with a 100-sample reference.

**2.2 Δ(N) is monotone in N on all four checkpoints, and it converges.** A
linear fit in 1/N gives intercepts of +8.5, +2.3, +14.7, −9.7, all within
0.7 pp of the N=1000 headline. So the N=1000 headline is a valid estimate and
does not need an extrapolation correction — the defect is entirely in the
small-N statistic. (The fit is an extrapolation, not a measurement; it is
reported to show the curve has flattened, not to move any number.)

**2.3 The bias always favours the shrunk arm, and its size tracks the
shrinkage.** The two most-contracted checkpoints (`w16e1_10k` at `rho` ratio
0.675, `w16e1_5k` at 0.547) show the largest attenuation; `production` (0.953)
shows the smallest. That is the signature of an estimator bias that scales
with `tr(S_g)`, not a quality difference.

## 3. The consequence for every published R5c number

The N=1000 headline for all three arms, against the chunk deltas that the paper
quotes:

| ckpt | arm | chunk Δ (published) | **headline Δ (N=1000)** | ratio |
|---|---|---:|---:|---:|
| `production` | cosine | +0.6 % | **+8.9 %** | 14× |
| `production` | codimension_sheet | +2.9 % | **+13.0 %** | 4.5× |
| `production` | evidence_driven | +1.1 % | **+9.5 %** | 8.6× |
| `w16e1_10k` | cosine | −11.4 % | **+2.5 %** | **sign flip** |
| `w16e1_10k` | codimension_sheet | −5.8 % | **+10.7 %** | **sign flip** |
| `w16e1_10k` | evidence_driven | −7.8 % | **+7.6 %** | **sign flip** |
| `w16e1_60k` | cosine | +1.5 % | **+15.4 %** | 10× |
| `w16e1_60k` | codimension_sheet | +3.6 % | **+19.4 %** | 5.4× |
| `w16e1_60k` | evidence_driven | +1.4 % | **+15.6 %** | 11× |
| `w16e1_5k` | cosine | −19.6 % | **−9.7 %** | 2× |
| `w16e1_5k` | codimension_sheet | −12.7 % | **+0.1 %** | **sign flip** |
| `w16e1_5k` | evidence_driven | −12.9 % | **−0.1 %** | **sign flip** |

At N=1000 the framework **loses 10 of 12 cells** (two of them by less than
0.1 %, i.e. ties in practice) and wins 2. The chunk test reported **6 wins and
6 losses** — the split is not merely rescaled, it is inverted: the four cells
the chunk test called wins by 5.8–12.9 % are, at N=1000, two losses of +7.6 %
and +10.7 % and two ties.

The three `w16e1_5k` rows are the sharpest: the chunk test reports −12.7 % and
−12.9 % wins for `codimension_sheet` and `evidence_driven`, and the N=1000
headline reports +0.1 % and −0.1 %. Two ties were published as large wins.

## 4. Corroboration from an independent run

The Wave 280 R5c production sweep (`verification_outputs/wave280-p-r5c/seed42/`,
N=200, chunk size 20, pre-GAP-56 configuration) shows the same direction on all
three arms, at a smaller magnitude because that run predates the `t0 = m` fix:

| arm | headline Δ (N=200) | chunk Δ |
|---|---:|---:|
| cosine | +16.98 % | +14.78 % |
| codimension_sheet | +26.85 % | +13.27 % |
| evidence_driven | +13.99 % | +11.90 % |

So the defect is not specific to the GAP-57 configuration or to chunk size 100.
It is a property of scoring a shrunk arm at small n.

## 5. Interpretation

### 5.1 What the chunk test actually measured

At n = 100 in a 128-dimensional projection, the sample covariance is
near-singular and the Fréchet distance is dominated by estimator noise whose
magnitude scales with `tr(S_g)`. A restart arm that has contracted its sample
cloud is therefore scored as *closer* to the reference for a reason that is
purely an artefact of the estimator. The chunk test was never measuring the
framework's effect on sample quality; it was measuring the framework's effect
on sample dispersion, with the sign arranged so that shrinkage looks good.

This is the same pathology already recorded for N=200 FID (a 40–65 % effect-size
inflation), at a smaller N and therefore larger.

### 5.2 What this does to GAP-64 and GAP-67

GAP-64's sign rule ("shrinkage helps iff `rho_base >= 1`") was fitted on the
chunk statistic, so it was fitted on the bias. GAP-67 then tested the rule's
mechanism by intervening on `rho` — and found that `rho` does not respond to the
intervention. Both results are now explained by the same thing: the chunk
statistic is a monotone function of `rho`, so a rule fitted on it is a rule
about `rho`, not about FID. GAP-64's rule is not wrong as a statement about the
chunk statistic; it is wrong as a statement about fidelity.

### 5.3 What must not be concluded

The headline numbers above are **one seed, one arm set, and a framework-internal
projection FID**, not Inception-FID. They are sufficient to show that the chunk
statistic is invalid, because the two statistics are computed on the same
samples and disagree in sign. They are **not** sufficient to publish
"+15.4 % on `w16e1_60k`" as a new effect size — that needs the 3-seed design the
frozen `gap57` ladder was built for, and the decision rule says not to buy it
until the statistic is settled.

What is settled is the direction of the correction: the published R5c deltas
are too kind to the framework by roughly an order of magnitude, and on
`w16e1_10k` and two of the three `w16e1_5k` arms they have the wrong sign.

### 5.4 Flags raised, not acted on

Per the recording policy, the frozen surfaces are untouched. Three things are
flagged for whoever owns them:

1. **CLM-059's R5c "WINS −28.43 %"** rests on the smoke-checkpoint chunk test
   (`d_z = −13.18`, df=9). This analysis says that statistic is a dispersion
   proxy. The claim's status is not edited here.
2. **The Wave 280 production addendum** (`baseline_wins +10.37 %`, N=200) is
   directionally right and quantitatively low; the N=1000 headline for the same
   checkpoint is +8.9 % to +13.0 % depending on the arm.
3. **`CLM-060`'s R5c power row** and any §10 table quoting a chunk ΔFID inherit
   the same defect.

## 6. Unresolved

* The scan covers the `cosine` arm at N=1000 in detail; the other two arms are
  reported at the headline only. Their Δ(N) curves were not scanned.
* The 1/N convergence is an extrapolation. A direct N=2000 or N=5000 run would
  settle it, and would also settle whether the N=1000 headline is still
  attenuated (the fit says it is not, but the fit is a model).
* Nothing here says *why* the framework loses on the well-trained checkpoints;
  that is GAP-72's question (the FID decomposition says it is a mean shift).
