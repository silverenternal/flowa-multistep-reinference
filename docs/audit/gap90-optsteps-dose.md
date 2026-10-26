# GAP-90 pre-registration — optimizer-steps dose under the corrected frontier protocol

**Status:** PRE-REGISTERED, NOT RUN. This document is committed before the
first sample, per `decision_rule` in `todo.json`.
**Supersedes:** the `GAP-90-EPOCH-DOSE-CONTROLLED` entry as first written on
2026-10-27, which proposed training five new epoch checkpoints. That design was
wrong on the facts; §1 records why.

---

## 1. Correction that re-scoped this experiment

The first version of GAP-90 assumed the four MNIST checkpoints behind R5c
differ in architecture, training-set size **and** training time at once, and
that a controlled epoch sweep therefore had to be trained from scratch.

That is false for three of the four. `verification_outputs/gap35-mnist-regime/aggregate.json`
records the configuration of every checkpoint that exists on disk:

| checkpoint | `base_channels` | epochs | train images | optimizer steps | file |
|---|---:|---:|---:|---:|---|
| `w16e1_5k` | 16 | 1 | 5,000 | 78 | `data/mnist_fm/w16e1_5k.ckpt.npz` |
| `w16e1_10k` | 16 | 1 | 10,000 | 156 | `data/mnist_fm/w16e1_10k.ckpt.npz` |
| `w16e1_60k` | 16 | 1 | 60,000 | 937 | `data/mnist_fm/w16e1.ckpt.npz` |
| `epochs2` | 16 | 2 | 60,000 | 1,874 | `data/mnist_fm/epochs2.ckpt.npz` |
| `production` | 16 | 3 | 60,000 | 2,811 | `data/mnist_fm/production.ckpt.npz` |
| `w8e3` | 8 | 3 | 60,000 | 2,811 | `data/mnist_fm/w8e3.ckpt.npz` |

Verified independently: `down1_w` has shape `(16, 2, 3, 3)` in `w16e1`,
`epochs2` and `production`, and `(8, 2, 3, 3)` in `w8e3`. So

* `w16e1_5k` → `w16e1_10k` → `w16e1_60k` is already a **clean dose in training-set
  size at fixed architecture and fixed epoch count** — no confound at all;
* `w16e1_60k` → `epochs2` → `production` is already a **clean dose in epochs at
  fixed architecture and fixed training set**;
* `w8e3` vs `production` is a **width control at identical optimizer steps**
  (2,811).

Nothing needs training. What is missing is the frontier measurement on the two
checkpoints that never received one: `epochs2` and `w8e3`. GAP-84 covered the
other four.

This also means the sentence the manuscript currently carries — that the four
R5c checkpoints "still differ in architecture and training-set size as well as
in training time" — is true only because `production` is in the set. The
`5k / 10k / 60k` triple is controlled.

## 2. What is already measured

GAP-84's frontier, seven rungs, N=1000 per arm, seeds 42/43/44, at least two
integration steps per round:

| checkpoint | opt steps | baseline plateau | Δ plateau | Δ% | verdict |
|---|---:|---:|---:|---:|---|
| `w16e1_5k` | 78 | 24.4839 | −3.1206 | −12.75% | **WIN**, 7/7 strict |
| `w16e1_10k` | 156 | 16.9537 | −1.0036 | −5.92% | TIE (CI low 0.984 vs the 1.0 floor) |
| `w16e1_60k` | 937 | 11.3795 | +0.0150 | +0.13% | TIE |
| `production` | 2,811 | 9.9938 | −0.0335 | −0.34% | TIE |

Three points already lie on a monotone curve in optimizer steps. The two
missing points are `epochs2` (1,874 steps) and `w8e3` (2,811 steps, width 8).

## 3. Hypothesis

**H1 (primary).** The framework's plateau gain is a function of the
checkpoint's optimizer-step budget, and is non-increasing in it.

**H2 (width).** At identical optimizer steps (2,811), a width-8 checkpoint and
a width-16 checkpoint give plateau gains that agree within the 1-FID floor.
This is the second half of GAP-35's claim ("governed by optimization budget,
not width") tested under the corrected protocol rather than at a single NFE.

**H3 (negative control).** Within the 60,000-image family, varying epochs alone
(937 → 1,874 → 2,811 steps) does not move the plateau gain outside the floor.
If H3 fails — that is, if `epochs2` shows a gain while `w16e1_60k` and
`production` do not — then the law is not a function of optimizer steps and H1
is rejected.

**Pre-registered predictions.** Plateau Δ ≈ 0 at 1,874 steps and ≈ 0 at
2,811 steps for both widths; the fitted slope of Δ against log(opt steps) is
positive (gain shrinks as steps grow) with a 95% CI excluding 0.

## 4. Design

**Checkpoints (new measurements only):** `epochs2`, `w8e3`. Both already exist
on disk; no training.

**Protocol.** Exactly GAP-84's, so the points are comparable:

* N = 1000 samples per arm;
* sampling seeds 42 / 43 / 44;
* NFE rungs {4, 5, 10, 25, 50, 100, 200};
* `--min-steps-per-round 2`;
* headline arm `evidence_driven`;
* plateau = mean of the last two rungs (100, 200);
* floor rule: 1 FID absolute, with the 1% relative rule reported alongside;
* verdict via `tools/frontier_report.py`, unmodified.

**Cell count.** 2 checkpoints × 7 rungs × 3 seeds × 2 arms = 84 cells at
N = 1000.

**Artifacts.** `verification_outputs/gap90-optsteps-dose/`, with
`frontier_input_<ckpt>_evidence_driven.json` per checkpoint in the same schema
GAP-84 used, so `tools/frontier_report.py` consumes them without adaptation.

## 5. Acceptance

All four clauses, or the law is rejected and the manuscript keeps its current
hypothesis wording:

1. **Monotone dose.** Across the five optimizer-step levels
   (78, 156, 937, 1,874, 2,811), the plateau gain is non-increasing, and the
   OLS slope of Δ on log(opt steps) has a 95% CI excluding 0.
2. **Reproduction at the bottom.** The 78-step point reproduces the GAP-84 WIN
   (7/7 strict rungs, plateau CI clearing the floor). This is a consistency
   check on the new pipeline, not new evidence.
3. **Width agreement.** At 2,811 steps, `w8e3` and `production` differ by less
   than 1 FID in plateau gain.
4. **Flat epoch sub-axis.** The three 60,000-image points (937 / 1,874 / 2,811)
   all sit inside the floor.

**Falsification is a result.** If clause 1 or 3 fails, the paper's
"distance to floor" reading is replaced by whatever the data show, and the
`venue_assessment` in `todo.json` is revised downward.

## 6. What this buys the paper

If it holds, the manuscript can replace

> the four checkpoints still differ in architecture and training-set size as
> well as in training time

with a measured dose curve in optimizer steps, two widths, and a controlled
epoch sub-axis. That converts the paper's central claim from a four-point
cross-section into an identification, which is the single largest item in
`venue_assessment.drivers_against`.

## 7. Cost

Two frontier runs, 84 N=1000 cells, no training. On the throughput GAP-84
recorded, this is a few hours on one GPU — not the two days the first version
of this pre-registration estimated, because that version assumed five
checkpoints had to be trained first.

---

## 8. GAP-91 — the predictor (same document, second section)

**Question.** Given a checkpoint's optimizer-step budget, can the plateau gain
be predicted out of sample, or is the relation only descriptive?

**Fit.** Regress Δ on log(opt steps) using the five GAP-90 levels. Report the
fit, R², and the residual scale.

**Hold-out.** The fit is on MNIST FM only. The held-out test is a second
family: the Kanzi reconstruction cell (R2) or the CIFAR-10 RF cell (R5b),
whichever has a usable multi-rung baseline. Predict the sign of that cell's
plateau Δ from its own optimizer-step budget and compare with the measured
value.

**Acceptance.** Held-out sign correct AND |predicted − observed| < 1 FID.
Otherwise the relation is reported as descriptive only, and the manuscript says
"orders" rather than "predicts".

**Why the hold-out matters.** A monotone relation fitted on five points of one
family is an index, not a lever. The hold-out is what distinguishes the two.
