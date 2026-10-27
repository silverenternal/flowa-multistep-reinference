# GAP-94 decision memo — the competitive-benchmark question

**Status:** USER GATED. Nothing in this document has been run, and no GPU time
is requested here. It exists so the decision can be made on numbers rather than
on adjectives.

---

## 1. The objection, stated at full strength

The strongest image result in the manuscript is a −12.75% FID plateau on a
5,000-image MNIST checkpoint (baseline plateau 24.48 → 21.36). In 2026 a
generative-acceleration paper is read against ImageNet-256 / DiT / SD-class
results. There are none in this paper. No amount of prose closes that, and the
packaging pass did not try: §VII-A now says the evidence is structured and
small-data generation.

The question this memo answers is whether the gap can be closed cheaply enough
to be worth the delay.

## 1a. Amendment (2026-10-27) — the premise is wrong: the generator is broken, not (proven to be) the checkpoint

This memo was written on the reading "the checkpoint is at FID 448, so it
cannot be a competitive benchmark". A diagnostic run on `cuda:0` the same day
shows that the FID number is not a property of the checkpoint alone, and that
the generator is producing a collapsed population:

* `cifar10_rf.pth`, NFE=2, seed 0, N=2000 generated in 24.5 s.
* Sample statistics: `mean = -0.052`, **`sd = 0.098`**, range `[-0.685, 0.611]`.
  Real CIFAR-10 in `[-1, 1]` has `sd` roughly three times that and uses the
  full range. A near-constant output cloud is what a collapsed or
  mis-integrated sampler looks like, not what a converged RF model looks like.
* FID on that single fixed population, subsampled so N is the only variable:

  | N | 200 | 500 | 1000 | 2000 |
  |---|---:|---:|---:|---:|
  | FID | 247.19 | 215.34 | 198.29 | 184.56 |

  The number falls with N, as the 2048-dimensional covariance bias predicts,
  but it converges nowhere near the published 2.21. **The small-N bias is not
  the explanation.** (The R5b cells that report 447.9 also use N=200 with a
  2048-dim feature covariance, so they carry both defects at once.)

Consequence for this memo: option B is no longer "acquire a better checkpoint".
The first task is to find out why the existing checkpoint generates a collapsed
cloud — time direction, the `t` convention in `batched_inference`, the
normalisation of the reference `cifar10_test_ref.npz`, or a state-dict load
that is silently non-strict (`_load_torch_unet` passes `strict=False`). Until
that is answered, no CIFAR FID in this repository — including the 447.9 the
memo quotes — should be compared to the literature, and the R5b relative
deltas (−1.6 % to −2.5 %) are only interpretable as within-run comparisons.

This does not change the recommendation ordering (B before A), but it changes
option B's first step from "buy a checkpoint" to "diagnose the existing one",
which is cheaper and is a prerequisite for either option.

## 2. What the repository already has, and why it does not answer the objection

| artifact | what it is | measured baseline |
|---|---|---|
| `data/rectified_flow_cifar10.pth` | a CIFAR-10 rectified-flow checkpoint (944 MB) | **FID 447.9 / 455.7 / 453.7** at NFE=50, seeds 42/43/44 |
| `data/cifar10_rf.pth` | a second RF checkpoint (236 MB) | not used in a headline cell |

(`docs/audit/gap04-r5b-rounds.md:39`.)

A model at FID 448 is not a competitive benchmark. At that distance from the
data, FID is dominated by model quality, not by the sampler — which is also the
honest reading of why R5b is the one REGRESSES cell: the restart is being asked
to repair a model that has not learned the distribution. Running a grid on this
checkpoint (GAP-95) is worth doing for R5b's own verdict, but it **cannot** be
presented as evidence on a competitive model.

## 3. Option B — a properly trained CIFAR-10 model (recommended)

**What it needs.** A CIFAR-10 flow-matching / rectified-flow checkpoint at
FID ≤ 10, then the existing frontier protocol on it.

**Adapter cost: low.** The CIFAR path already exists:
`tools/run_sota_cifar_experiment.py` with `--checkpoint`, the InceptionV3-tfport
feature cache (`data/cifar10_inception_features.npz`), and the shared
`_fid_numpy`. A new checkpoint is a loader change, not a new adapter.

**Compute.** 5 rungs × 3 seeds × 2 arms × N=1000. CIFAR is 32×32 and the
measured throughput at NFE=50 is 1167–1573 s per 200-sample cell
(`gap04-r5b-rounds.md:43`); scaling to N=1000 and to NFE up to 200 puts a full
frontier at roughly **30 GPU-hours ≈ 1.5 GPU-days** on one device.

**Acceptance.** Five or more rungs, three seeds, N ≥ 1000, reported as a
frontier (never a single point), the same floor rule as R5c.

**Risk.** The result may be a TIE. A converged CIFAR model is the case the
κ diagnostic predicts *should* tie: no excess dispersion to remove. That risk is
real and is the main argument for doing Option B only after GAP-90, which tests
the same prediction on the axis we already own.

## 4. Option A — SD / DiT-class at 256²

**What it needs.** A pretrained latent model, an adapter for the VAE latent
space, CFG handling and a 256² FID reference. None of these exist in the repo;
`data/hidream_i1`, `data/lumina_image_2_0` and `data/wan2.2` are vendored but no
headline cell runs them.

**Cost.** 5–15 GPU-days dominated by adapter work and reference statistics, not
by sampling. **Not recommended before Option B**, because it spends the same
decision on a much larger surface.

## 5. If neither runs

The paper keeps the scope sentence it already has. The manuscript must not
imply general acceleration, and the abstract must not use "accelerator" without
the structured-data qualifier. That is the current state and it is defensible;
it is simply weaker than a measured CIFAR frontier.

## 6. Decision needed

One of:

* **B** — authorise a properly trained CIFAR-10 checkpoint and a frontier run
  (~1.5 GPU-days plus checkpoint acquisition);
* **A** — authorise a 256² latent-model adapter (5–15 GPU-days, higher risk);
* **neither** — keep the scope sentence, and spend the time on GAP-90/93
  instead.

Record the choice and the date in `todo.json` under this gap. No agent work
starts before that.
