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

## 1a. Amendment (2026-10-27) — the 447.9 is an NFE=2 artifact, but the checkpoint still is not competitive

This memo was written on the reading "the checkpoint is at FID 448, so it cannot
be a competitive benchmark". Diagnostics on `cuda:0` the same day split that
statement into three parts, and only the last one survives.

**The checkpoint loads correctly.** `cifar10_rf.pth` is detected as a gnobitab
1-RF checkpoint (565 keys, `all_modules.*` prefix) and
`load_gnobitab_rf_cifar_unet` loads it with `strict=True`. There is no silent
random-weight path here; the earlier suspicion that `strict=False` was hiding a
mismatch is wrong.

**The samples are not collapsed — the integration was under-resolved.** The
reference `cifar10_test_ref.npz` has `sd = 0.5024`. Generated populations of
256 samples at seed 0:

| NFE | 1 | 2 | 4 | 10 | 50 |
|---|---:|---:|---:|---:|---:|
| generated `sd` | 0.0764 | 0.0987 | 0.1880 | 0.3373 | **0.4696** |

At NFE=50 the cloud is within 7 % of the reference's dispersion. At NFE=2 — the
setting every R5b cell uses — it is at a fifth of it. Two Euler steps from pure
noise is simply not enough for this checkpoint, and that, not a broken model, is
what the 447.9 measures.

**The FID is still not competitive at any tested step count.** N=1000, seed 0,
same reference:

| NFE | 2 (N=2000 population, subsampled) | 10 | 50 |
|---|---:|---:|---:|
| FID | 184.56 (N=2000) | 45.01 | **34.92** |

The published 1-RF number for this model family is FID 4.3 at one step and 2.21
for the 2-RF reflowed variant. So the gap to the literature is roughly **8x at
NFE=50**, and it is not explained by any of the three things this memo could
cheaply test (load, dispersion, small-N bias — the last is worth ~2 FID at
N=1000, d=2048).

Consequences, in order of importance:

1. **Every R5b relative delta is measured at an operating point where the
   baseline is not converged.** −1.6 % to −2.5 % on a 450 FID baseline is a
   comparison between two under-integrated samplers. The relative deltas are
   internally valid; they are not evidence about converged generation.
2. **The 447.9 quoted in §2 of this memo must not be used as a model property.**
   It is a (checkpoint, NFE=2, N=200) triple.
3. **Option B is still the right shape, but its first step changes again**: not
   "buy a checkpoint" and not "the generator is broken", but "find the 8x". The
   remaining candidates are the sampler's time convention in
   `RFVelocityUNet`'s `t * 999` fold, the InceptionV3 weight family
   (`pytorch_fid` TF-port vs torchvision IMAGENET1K_V1 — the repo has both and
   they are not comparable), and whether this checkpoint is 1-RF rather than
   2-RF. That is one bounded diagnostic, not a GPU-week.

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
