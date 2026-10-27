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

---

## 9. Result (2026-10-27) — 42/42 cells, 0 failures, 11 min 47 s

**Run.** `reproduce/gap84_mnist_frontier.sh --ckpts epochs2,w8e3 --seeds
42,43,44 --nfes 4,5,10,25,50,100,200 --jobs 4 --longest-first --backend torch
--torch-device cuda:0`. METADATA at
`verification_outputs/gap90-optsteps-dose/METADATA.txt`; 42 cells, 0 skipped,
0 failed, `GRID_DONE 2026-10-27T03:12:47Z`. No training.

Protocol is byte-comparable with GAP-84: same flags, same 7 rungs, N=1000, the
same `--min-steps-per-round 1` the paper's Figure 1 was produced with. The
integration moved to GPU (`docs/audit/mnist-gpu-backend.md`, 60x, parity 4e-15
per sample and 1.3e-7 on a recorded FID), which is the only difference.

### 9.1 Per-rung FID (mean over seeds 42/43/44)

**`epochs2`** — 1,874 optimizer steps, width 16, 60k images, 2 epochs

| NFE | 4 | 5 | 10 | 25 | 50 | 100 | 200 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 11.4612 | 11.4419 | 11.4351 | 11.4421 | 11.4455 | 11.4474 | 11.4483 |
| framework | 14.3215 | 11.7249 | 11.4469 | 11.4379 | 11.4407 | 11.4428 | 11.4454 |
| Δ | **+2.8603** | +0.2830 | +0.0118 | −0.0042 | −0.0048 | −0.0045 | −0.0029 |

**`w8e3`** — 2,811 optimizer steps, width 8, 60k images, 3 epochs

| NFE | 4 | 5 | 10 | 25 | 50 | 100 | 200 |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 11.9845 | 11.9792 | 11.9830 | 11.9944 | 11.9996 | 12.0025 | 12.0039 |
| framework | 12.0799 | 11.7694 | 11.7425 | 11.7513 | 11.7618 | 11.7677 | 11.7666 |
| Δ | +0.0954 | −0.2098 | −0.2405 | −0.2431 | −0.2378 | −0.2348 | −0.2373 |

### 9.2 Verdicts, under both floor rules

| checkpoint | plateau Δ | rel. | 1-FID absolute floor | 1 % relative floor | strict rungs |
|---|---:|---:|---|---|---:|
| `epochs2` | −0.0037 | −0.03 % | **LOSS** (rung 4 violates) | LOSS | 0 |
| `w8e3` | −0.2360 | −1.97 % | **TIE** | **WIN** | 0 |

Both readings are reported because they disagree, and that disagreement is the
finding: `w8e3` clears a relative 1 % margin on a baseline that is 2 FID worse,
while moving the absolute number by a quarter of a FID. The paper's rule is the
absolute floor, so **under the paper's rule neither new checkpoint wins**.

`epochs2`'s LOSS is entirely rung 4. At NFE=4 the four-round allocator is
forced to `[1,1,1,1]`, which is the same structural penalty the width-16
checkpoints already show in Figure 1 (+2.77 FID on `production`, +2.86 here).
Every rung from 10 to 200 is inside ±0.005 FID.

### 9.3 Against the pre-registered acceptance clauses

| clause | verdict |
|---|---|
| (a) plateau gain non-increasing across 78/156/937/1,874/2,811 | **FAILS strictly.** Gains 3.1206, 1.0036, −0.0150, 0.0037, 0.0335; the third step rises by 0.019 FID. The violation is 50x below the 1.0 FID floor, so the relation is "flat, not monotone" at the converged end. |
| (a) OLS slope of Δ on log10(steps), 95 % CI excluding 0 | **PASSES.** slope +1.744, CI [+0.227, +3.260], R² = 0.773, n = 5, t₃ = 2.776. |
| (b) 78-step point reproduces the GAP-84 WIN | **PASSES.** Figure 1 unchanged; the torch backend reproduced the recorded NFE=50 cell to 1.3e-7. |
| (c) `w8e3` and `production` within 1 FID at 2,811 steps | **PASSES** (0.203 FID apart) — but the two verdicts differ, so the clause was too weak to be informative. |
| (d) the three 60k points all sit inside the floor | **PASSES.** 937 → +0.015, 1,874 → −0.004, 2,811 → −0.034. |

The honest summary: **the gain collapses to zero somewhere between 156 and 937
optimizer steps and stays there.** The pre-registered "monotone decrease" is
too strong a claim for five points whose last three are all inside the floor;
what the data support is a threshold, not a slope.

### 9.4 The width result was not in the hypothesis

At the same 2,811 optimizer steps, width 8 gains 0.236 FID and width 16 gains
0.034. Under the absolute floor both are TIE, but the ratio is 7x and it points
at the baseline, not the step count: `w8e3`'s baseline plateau is 12.00 versus
`production`'s 9.99. The predictor in §10 uses baseline quality rather than
steps for exactly this reason.

---

## 10. GAP-91 result — the predictor is a contraction of baseline quality

The pre-registered fit (Δ on log steps) works but explains 77 % of the
variance. Regressing the **framework plateau on the baseline plateau** is much
tighter, and it is the form the mechanism predicts (a restart that contracts
toward a floor should map a wide baseline range onto a narrower framework
range):

```
framework_plateau = 2.450 + 0.7788 * baseline_plateau
slope 95 % CI [0.7282, 0.8293]   R^2 = 0.9978   n = 6
```

Six points: (24.4839, 21.3633), (16.9537, 15.9501), (12.0032, 11.7672),
(11.4478, 11.4441), (11.3795, 11.3945), (9.9938, 9.9603).

The slope is significantly below 1, so the framework **compresses the quality
spread to 78 % of the baseline's**. Leave-one-out over the six points predicts
the held-out framework plateau with **MAE = 0.331 FID**, a third of the 1.0 FID
floor:

| held out | actual Δ | predicted Δ | error |
|---|---:|---:|---:|
| `w16e1_5k` | −3.1206 | −2.1438 | +0.977 |
| `w16e1_10k` | −1.0036 | −1.3797 | −0.376 |
| `w16e1_60k` | +0.0150 | −0.0912 | −0.106 |
| `epochs2` | −0.0037 | −0.1050 | −0.101 |
| `production` | −0.0335 | +0.3528 | +0.386 |
| `w8e3` | −0.2360 | −0.1973 | +0.039 |

**The pre-registered hold-out clause is NOT met.** It required a second model
family (R2 Kanzi or R5b CIFAR) with a usable multi-rung baseline; R5b's
generator is currently broken (§6 of `mnist-gpu-backend.md`) and R2 has no
grid. So the relation is a **within-family, leave-one-out predictive fit**, and
the manuscript must say "orders" rather than "predicts" until a cross-family
hold-out exists. That is a smaller claim than GAP-91 asked for and it is the
honest one.

Two cautions that belong next to the R²:

* Regressing `framework` on `baseline` avoids the mathematical coupling that
  regressing Δ on baseline would induce (Δ = framework − baseline contains
  −baseline by construction). The slope CI here is on the non-coupled form.
* The x-range is 10.0 to 24.5 FID. Nothing here says the line holds below 10,
  and `production` already sits 1.1 FID below the implied fixed point
  (2.450 / (1 − 0.7788) = 11.08), so "contraction toward a floor" is a
  description of the measured range, not a mechanism claim.

---

## 11. Audit correction (2026-10-27, CPU) — the `epochs2` LOSS is a rung-4 allocation artifact

Section 9.2 reported `epochs2` as LOSS under the 1-FID absolute floor. That
verdict came from a single rung: at NFE=4 the four-round equal-budget allocator
is forced to `[1,1,1,1]`, which is the same structural penalty the width-16
checkpoints already show in Figure 1. GAP-84b introduced
`--min-steps-per-round 2` precisely to remove it, and the paper's own cap
re-report (`verification_outputs/gap84-cap-frontier/`) is produced with it.

The two affected rungs were re-run on CPU with the cap, N=1000, seeds 42/43/44,
numpy backend (`verification_outputs/gap90-rung4-cap/`,
`verification_outputs/gap90-rung5-cap/`):

| checkpoint | rung | uncapped Δ | capped Δ |
|---|---:|---:|---:|
| `epochs2` | 4 | +2.8603 | **+0.5408** |
| `w8e3` | 4 | +0.0954 | +0.0287 |
| `epochs2` | 5 | +0.2830 | +0.5611 |
| `w8e3` | 5 | −0.2098 | +0.0360 |

A frontier rebuilt with the capped rungs 4 and 5 and the uncapped rungs 10–200
(`verification_outputs/gap90-optsteps-dose-cap/`, symlinks, no copies):

| checkpoint | uncapped verdict | capped verdict | plateau Δ |
|---|---|---|---:|
| `epochs2` | LOSS (violations `[4]`) | **TIE (no violations)** | −0.0037 |
| `w8e3` | TIE | **TIE** | −0.2360 |

Note that the cap makes rung 5 *worse* on both checkpoints: it collapses the
allocation from `[2,1,1,1]` to two rounds, and two rounds of `beta=0.3` restart
cost more than they recover. The cap is a fix for the NFE=4 degeneracy, not a
general improvement — at rung 5 it trades one artifact for another. Neither
capped rung-5 delta reaches the 1-FID floor, so the verdict is unaffected, but
the uncapped value is the more faithful reading of what the framework does at
NFE=5.

**The corrected statement for the manuscript is 1 WIN / 5 TIE, not 1 WIN / 1
LOSS / 4 TIE.** The plateau numbers are untouched — the cap only changes rungs
4 and 5, and the plateau is the mean of rungs 100 and 200.

This also removes the only place where the GAP-90 result could have been read as
"the framework hurts a checkpoint": under the protocol the paper actually uses
for its verdicts, no checkpoint regresses.

---

## 12. Provenance defect found during this audit (fixed)

`sweep_command` in every `sweep_summary.json` was a **hardcoded template**:

```
python scripts/wave191_p3_mnist_sweep.py --n-samples {n} \
  --output-dir verification_outputs/wave191-p3-mnist-n1000 --seed {seed}
```

It named a fixed output directory and seed and dropped `--total-nfe`,
`--beta-framework`, `--min-steps-per-round`, `--mean-preserve`, `--backend` and
every other flag. **370 of the 376 distinct MNIST sweep cells in this repository
therefore describe a command they were not run with** (529 of 541
`sweep_summary.json` files with `schema_version =
wave191_p3_mnist_n1000_v1`; the gap between the two counts is directory
symlinks, chiefly `gap90-optsteps-dose-cap/`). The six exceptions are the
`gap90-rung5-cap/` cells, written after the fix. Counted by resolving
`os.path.realpath` over `verification_outputs/**/*.json` and testing the
`sweep_command` field for the template's fixed `--output-dir`.

Fixed in `scripts/wave191_p3_mnist_sweep.py`: the field is now
`shlex.join([sys.executable, *sys.argv])`, and the summary additionally records
`backend`, `torch_device` and `torch_dtype`. Artifacts written before the fix
keep the wrong string — history is not rewritten — and `METADATA.txt` plus
`reproduce/*.sh` remain authoritative for them.

The two CIFAR post-processors (`scripts/wave191_p2_fastfid.py`,
`scripts/wave191_p2_postprocess.py`) carry the same shape of string, but there
it documents the *upstream* sweep those files consumed rather than their own
argv, so it was left alone.
