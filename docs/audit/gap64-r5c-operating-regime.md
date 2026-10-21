# GAP-64 — R5c operating-regime census, NFE headroom, and the shrinkage mechanism

**Status:** CLOSED (negative for the "allocation is the missing lever" hypothesis;
positive for a mechanism-level explanation of R5c)
**Date:** 2026-10-21
**Cell:** R5c — MNIST-FM projection FID (784 → 128 random projection, full 10k reference)
**Owner surfaces:** `tools/gap64_r5c_census.py`, `tools/gap64_nfe_headroom.py`,
`tools/gap64_dispersion_diagnostic.py`
**Evidence:** `verification_outputs/gap64-evidence-allocation/`,
`verification_outputs/gap64b-nfe-headroom/`, `verification_outputs/gap64c-dispersion/`

---

## 0. TL;DR

Three facts, in the order they were established.

1. **The framework's own NFE allocator does not rescue R5c.** `nfe_steps_for_evidence`
   (Wave 35 FIX-3, previously used only by `tools/run_controlled_audit.py`) was
   wired into `scripts/wave191_p3_mnist_sweep.py` as `--nfe-allocation evidence`
   and measured at NFE ∈ {16, 50}. It is *worse* than the `n_cap` allocation at
   NFE=16 (+10.09% vs +9.05% for `codimension_sheet`) and indistinguishable at
   NFE=50 (+8.70% vs +8.55%). No sign flip.

2. **R5c cannot discriminate sampler efficiency at all.** A baseline-only NFE
   ladder with a byte-identical prior shows the single-pass FID is flat from
   NFE=3 to NFE=100: **11.1035 → 11.0675 (0.33%)** on `production`, and
   **26.9258 → 26.7300 (0.73%)** on `w16e1_5k`. The RK4 sampler is already
   converged at three steps, so there is no integration error for a restart
   mechanism to recover. The recorded `ΔFID` on this cell measures only the
   *cost* of the restart perturbation.

3. **The restart blend is a variance-shrinkage operator, and that explains the
   whole R5c table.** Total dispersion `rho = tr(Σ_gen)/tr(Σ_ref)` measured in
   the FID projection space:

   | checkpoint | `rho` (baseline) | framework shrinks to | measured `ΔFID` (cosine) |
   |---|---:|---:|---:|
   | `production` | 0.782 | 0.745 | **+8.91%** |
   | `w16e1_10k` | 0.752 | 0.508 | **+2.47%** |
   | `w16e1_60k` | 0.704 | 0.611 | **+15.42%** |
   | `w16e1_5k` | **1.006** | 0.550 | **−9.65%** |

   Sign rule: shrinkage helps iff the **base** model is at or above the data's
   dispersion. 4/4 correct. The one cell the framework wins is the only cell
   where `rho >= 1`.

**Consequence for the claim.** "The framework improves inference quality for
*any* flow-matching model" is **not** supported on fidelity metrics, and cannot
be, because the mechanism is a one-directional shrinkage. The supported
statement is conditional and *predictive*: the framework improves a model
exactly when the model's sampler is mis-calibrated in the direction the
shrinkage corrects, and a pilot-batch dispersion probe tells you which case you
are in before you commit the compute.

---

## 1. What was asked

The prior increment (GAP-56/57) closed R5c as "REGRESSES, model-conditional".
That left one live hypothesis: *the framework is implemented but under-used, so
the regression is a wiring artefact, not a property of the mechanism.*
Specifically, `nfe_steps_for_evidence` — the framework's own step allocator,
which apportions NFE inversely to each round's `eps_implicit` so the fine-eps
terminal rounds get more steps — had never been used by a headline cell. Every
headline cell allocated by scheduler `n_cap`, and `CodimensionSheetScheduler`
returns `n_cap ≈ 1.0` on every round, so that allocation had silently
degenerated to **uniform** (`[13, 12, 12, 13]` at NFE=50, R=4).

GAP-64 tests that hypothesis, and then, because it failed, asks the prior
question of whether the cell can carry the signal at all.

## 2. Protocol

All runs use `scripts/wave191_p3_mnist_sweep.py`, N=200, seed 42,
`--seed-keyed-prior --shared-prior` (baseline and framework start from the same
`x0`), `--beta-schedule equal_budget --beta-framework 0.5`,
`--restart-t0-mode memory`, `--n-rounds 4`, `--equal-total-nfe`.

* **Allocator probe** — `--nfe-allocation {scheduler, evidence}` ×
  `--total-nfe {16, 50}`, `production` checkpoint.
* **Headroom ladder** — baseline only, `--nfe {3, 5, 10, 25, 50, 100}`,
  checkpoints `production` and `w16e1_5k`, shared prior so the `x0` is
  byte-identical across every rung.
* **Dispersion diagnostic** — re-reads the N=1000 `*_samples.npz` from
  `gap57-*`, so it adds no sampling.

## 3. Observed

### 3.1 The allocator does not flip the sign

| NFE | allocation | cosine | codimension_sheet | evidence_driven | baseline |
|---:|---|---:|---:|---:|---:|
| 16 | `scheduler` | +4.83% | **+9.05%** | +6.50% | 12.9605 |
| 16 | `evidence` | +4.83% | **+10.09%** | +6.50% | 12.9605 |
| 50 | `scheduler` | +5.03% | **+8.55%** | +6.70% | 12.9753 |
| 50 | `evidence` | +4.44% | **+8.70%** | +6.26% | 12.9753 |

`cosine` and `evidence_driven` are byte-identical across the two allocations
because their `ScheduleSample.eps_implicit` is `None` and the allocator falls
back to the same weights. Only `codimension_sheet` carries a real `eps`
profile, and the terminal-heavy split (`[5, 6, 11, 28]` at NFE=50) is 0.15 pp
worse there. **The allocator is not the missing lever.**

### 3.2 The baseline has no NFE headroom

| checkpoint | NFE=3 | 5 | 10 | 25 | 50 | 100 | headroom (3→100) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `production` | 11.1035 | 11.0418 | 11.0440 | 11.0578 | 11.0640 | 11.0675 | **0.32%** |
| `w16e1_5k` | 26.9258 | 26.8306 | 26.7706 | 26.7394 | 26.7300 | 26.7250 | **0.75%** |

Both ladders are flat to within 1%. A restart mechanism whose premise is
"recover the error the single pass leaves behind" has, on this cell, no error
to recover. The `ΔFID` measured here is therefore a **cost**, not a
**failure-to-improve**.

### 3.3 The mechanism is shrinkage

`apply_restart_distribution` builds `m·x1_hat + (1−m)·x0` with `m = 1 − beta`.
Averaged over the fresh `x0`, this contracts the sample cloud toward the
model's own conditional mean. Measured total dispersion in the FID projection
space, N=1000:

| checkpoint | baseline | cosine | codimension_sheet | evidence_driven |
|---|---:|---:|---:|---:|
| `production` | 0.7819 | 0.7449 | 0.7375 | 0.7465 |
| `w16e1_10k` | 0.7523 | 0.5078 | 0.4977 | 0.4986 |
| `w16e1_60k` | 0.7039 | 0.6105 | 0.5968 | 0.6011 |
| `w16e1_5k` | **1.0055** | 0.5495 | 0.5434 | 0.5434 |

Every arm on every checkpoint contracts. The measured `ΔFID` sign tracks the
**baseline** `rho`, not the post-shrinkage `rho`: 4/4.

This also reconciles two results that previously read as contradictory:

* **K7** (novelty −42.9 pp) is what shrinkage *must* do — contracting toward the
  model mean removes tail samples, and novelty lives in the tail.
* **R1** (+74% hmmscan hits) and **R6** (scPerplexity `d_z = −0.84`) are metrics
  that reward a *smoother, higher-likelihood* population, which is exactly what
  contraction produces.

One mechanism, three signs of the same coin.

## 4. Interpretation

* R5c should be **retired as a headline cell**, not reported as a framework
  regression. Reporting "+9.5%" invites the reading "the framework degrades a
  good model"; the accurate reading is "on a sampler that is converged at three
  steps, a shrinkage operator costs 9.5% of fidelity and buys nothing, because
  there is nothing to buy".
* The correct R5c contribution is the **sign rule**: `rho_base >= 1` predicts
  where shrinkage pays. That is a cheap, pre-registrable selector (one pilot
  batch of ~200 samples, no labels, no reference beyond the training set).
* The "always improves any model" framing must be replaced. The framework is a
  **directional operator**, and the honest claim is about *matching the operator
  to the model's miscalibration*, not about universal improvement.

## 5. What this changes in the plan

* `GAP-64-EVIDENCE-ALLOCATION` — **closed, negative**. The framework's own
  allocator is not a lever on this cell. Recorded, not hidden.
* `GAP-57` R5c status — the "REGRESSES" label stays factually true but the
  *interpretation* changes; the audit that quotes it must cite §3.2.
* New `GAP-65-DISPERSION-SELECTOR` — turn the 4/4 sign rule into a deployable
  selector and validate it on the cells that are **not** NFE-saturated
  (R5b CIFAR, R1 LineageFlow, R3 FlowMol3). This is the experiment that can
  support a *universal* statement of the form "never worse, strictly better
  when mis-calibrated".

## 6. Unresolved

* The sign rule is fitted on **4 checkpoints of one model family**. It is a
  hypothesis with 4/4 support, not a law. R5b / R1 / R3 are the out-of-family
  tests.
* `w16e1_10k` (`rho = 0.752`, +2.47%) and `w16e1_60k` (`rho = 0.704`, +15.42%)
  show the *magnitude* is not monotone in `rho` even though the sign is. The
  missing variable is plausibly the mean shift (2.94 vs 2.36), which is not
  currently modelled.
* All numbers here are N=200 for §3.1–3.2 and N=1000 for §3.3. Per the
  project's own FID calibration, only the N=1000 numbers may be quoted as
  effect sizes; the N=200 ladder is a *screen* whose conclusion (flatness) is
  robust because it is a within-ladder comparison, not an effect size.
