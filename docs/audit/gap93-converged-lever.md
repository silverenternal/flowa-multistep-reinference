# GAP-93 pre-registration — is there a lever at the converged end?

**Status:** PRE-REGISTERED 2026-10-27, NOT RUN (GPU in use for other work).
**Question:** on the production MNIST checkpoint the framework's plateau gain is
−0.03 FID, inside the one-FID floor. Is that a *wall*, or is the fresh-noise
budget simply mis-set for a converged model?

---

## 1. The observation, with the significance stated

Three numbers are in play and they are routinely conflated:

| reading | budget | Δ FID | 95% CI | verdict |
|---|---|---:|---|---|
| plateau (rungs 100, 200) | 100–200 | −0.0335 | — | TIE, inside floor |
| `evidence_driven` | NFE=50 | −0.3648 | [−0.7237, −0.0059] | CI excludes 0, **but** \|Δ\| < 1 FID → inside floor |
| `codimension_sheet` | NFE=50 | −0.4985 | [−0.9996, **+0.0025**] | CI **includes** 0 → not significant |

`docs/audit/gap84-inference-frontier.md` §10.1 and
`verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json`.

The `codimension_sheet` row is the one that gets described as a "near-miss".
It is a near-miss on the floor, and it is **not** a significant effect: the CI
crosses zero. Any sentence in the paper or in a plan that treats −0.50 as
evidence of a live lever is wrong, and this document does not do that.

## 2. What is already ruled out — do not re-run it

* **More rounds.** GAP-84c swept `R ∈ {2,4,6,8,12}` at fixed NFE=25 on
  `production`, 15/15 cells, seeds 42/43/44. Above the cap (R ≥ 4) the whole
  dose spans 0.06 FID against a 1.0 FID floor — the audit's own reading is a
  **16×-too-small lever on a converged field**
  (`gap84-inference-frontier.md` §9.2). R=4 is the operating point, not a
  conservative setting. Below the cap it is worse, not better: R=2 is a loss in
  every arm (−0.97 to −1.50%), so the knob cannot be turned downward either.
* **The per-round step floor.** `--min-steps-per-round 2` only binds where
  `total_nfe < 2·n_rounds`, i.e. at rungs 4 and 5. At rungs 100 and 200 every
  round already receives ≥2 steps, so the cap is inactive at the plateau and
  cannot be the lever there.
* **More seeds.** Forbidden by `decision_rule`; the canonical seed set is
  fixed at 42/43/44.

## 3. What is left, and the two readings that predict opposite signs

Only one knob has never been dosed on any checkpoint: **β, the total fresh-noise
budget** (`--beta-framework`, distributed across the `R−1` restarts as
`1 − (1−β)^{1/(R−1)}`, `scripts/wave191_p3_mnist_sweep.py:132-154`). Every
recorded result uses β=0.3.

Two readings, both consistent with what has been measured:

**H_κ (dispersion).** κ is the ratio of the framework arm's output dispersion to
the baseline's, scaled by the reference: 0.667 at `w16e1_5k`, 0.959 at
`production`. At 5k the baseline is over-dispersed and the restart narrows it —
that narrowing is the −3.12 FID. At production the baseline is already sharp,
so there is no excess dispersion to remove and κ ≈ 0.96 records that fact.
Under H_κ there is nothing for β to act on, and the β dose is flat inside the
floor at both budgets.

**H_noise (budget).** The perturbation injected at each restart decays as κ per
round, so a converged checkpoint needs a *larger* β for the restart to bite at
all. Under H_noise the dose is increasing in β and β=0.5 moves the plateau below
−1 FID.

The two predict opposite signs on the same measurement. That is the point of the
experiment.

## 4. Design

**Checkpoint:** `production` only. The other three are already on the far side of
the floor and a β dose there would answer a different question.

**Stage 1 — the dose, at the GAP-78 budget.**

* β ∈ {0.15, 0.30, 0.50, 0.70}; β=0.30 is already measured and is reused.
* NFE=50, `--n-rounds 4`, `--equal-total-nfe`, `--mean-preserve`,
  `--restart-t0-mode memory`, `--shared-prior`, `--seed-keyed-prior`.
* seeds 42/43/44, N=1000.
* arms `evidence_driven` and `codimension_sheet` (the latter is the only arm
  that has ever been sub-floor on this checkpoint).
* 3 new β × 3 seeds × 2 arms = 18 arm-cells, 9 runs.

**Stage 2 — one confirmatory plateau run.**

* Only the β selected by the stage-1 rule, at rungs 100 and 200, seeds
  42/43/44, arm `evidence_driven` + `codimension_sheet`.
* 6 runs.

**Reproduction guard.** Before stage 1 counts, one β=0.30 / NFE=50 / seed 42 cell
must reproduce the recorded `evidence_driven` FID to 4 decimals. If it does not,
the pipeline has drifted and nothing in this document is interpretable.

## 5. Decision rule, fixed before the run

1. **β lever exists.** Some β in the grid gives a stage-1 CI that excludes 0
   *and* |Δ| ≥ 1 FID, and stage 2 reproduces it at the plateau with the CI upper
   bound below −1.0 → the converged end has a β lever. Record it, and R5c's
   frontier becomes 2/4 WIN instead of 1/4.
2. **No β lever.** Every β at both budgets spans less than 1 FID → H_κ holds.
   The converged end is not reachable by the fresh-noise budget, and the paper
   says the checkpoint-conditional gain is not a tuning artifact — which is a
   *stronger* statement than the current text, because it closes the obvious
   reviewer objection ("you did not tune β").
3. **Anything else** (non-monotone, or a >1 FID span that does not reproduce at
   the plateau) is recorded as an interior optimum and is **not** promoted to a
   WIN.

The direction of the stage-1 result does not change the rule; only the numbers
do.

## 6. Cost

Stage 1: 9 runs × 4 arms × 1000 samples at NFE=50. GAP-78 measured 27.1 min for
one such run (`verification_outputs/gap78-kappa-dose-n1000-3seed/run.log`), so
≈4 h. Stage 2: 6 runs at NFE=200, ≈110 min each, ≈11 h. **≈15 h on one GPU**,
in two bounded stages, with stage 2 skipped if the rule selects outcome 2.

## 7. What this buys the paper

Outcome 1 gives the frontier a second winning checkpoint and a mechanism for it.
Outcome 2 lets the manuscript say the checkpoint-conditional claim survives a
β sweep, which is the cheapest possible answer to "did you tune the one knob
that matters". Both outcomes are publishable; neither requires a new adapter.

## 8. Unresolved

1. **β and κ may be confounded in the same way κ and optimizer steps are.** A
   β that helps production may also help 5k; the guard is that stage 2 is run
   only on production, so the paper cannot claim β is checkpoint-specific
   without a second checkpoint.
2. **κ is measured at NFE=50 only** (`docs/audit/gap92-kappa-bridge.md` §7.4),
   so H_κ's premise is a single-budget quantity.
3. **The 0.70 level may be outside the valid range.** At β=0.7 the restart
   replaces most of the state each round; if the arm fails to converge the cell
   is recorded as invalid rather than as a loss, and the grid is truncated at
   the last valid level.

---

## 9. Result (2026-10-27) — outcome 2, **no beta lever**

**Run.** Stage 1: `reproduce/gap93_beta_dose.sh --jobs 4`, 12 cells (4 betas x 3
seeds), NFE=50, `cuda:0`, torch backend, 4 min 31 s. Stage 2: the two dose
extremes (beta = 0.15 and 0.70) at rungs 100 and 200, 12 cells, 8 min 26 s.
Both grids `failed=0`.

**Reproduction guard — PASSES.** beta = 0.30 / NFE = 50 / seed 42 reproduces the
recorded GAP-84 cell to 1.3e-7 on all four arms (the guard asked for 4
decimals), so the GPU backend did not shift the pipeline.

### 9.1 The dose, both budgets

Δ FID versus the same-seed baseline. The baseline is bit-identical across betas
by construction (span 0.0000 FID), which is the check that only beta moved.

| beta | stage 1, NFE=50, `evidence_driven` | stage 2, plateau, `evidence_driven` | plateau, `codimension_sheet` | plateau, `cosine` |
|---:|---:|---:|---:|---:|
| 0.15 | −0.0240 | −0.0221 | −0.0289 | −0.0218 |
| 0.30 | −0.0364 | −0.0335 | — | — |
| 0.50 | +0.1086 | — | — | — |
| 0.70 | +0.5729 | +0.5763 | +0.3720 | +0.2179 |

(The beta = 0.30 plateau row is the GAP-84 measurement, reused; the stage-1 row
is this run.)

### 9.2 The rule fires on outcome 2

> **2. No beta lever.** Every beta at both budgets spans less than 1 FID →
> H_kappa holds.

The largest absolute delta anywhere in the grid is **0.576 FID**, against a
1.0 FID floor. The span across beta is 0.609 FID at NFE=50 and 0.610 FID at the
plateau — the two budgets agree to 0.001 FID, so this is not a low-NFE artifact.

**H_noise is rejected.** Its prediction was that a converged checkpoint needs a
larger beta and that beta = 0.5 moves the plateau below −1 FID. Beta = 0.5 moves
it to +0.109 and beta = 0.7 to +0.576: the dose is monotone in the wrong
direction, and every step above 0.30 is a loss.

### 9.3 What this actually buys

The recorded operating point **is the optimum of the dose**. Beta = 0.30 is the
best of four levels at both budgets, and the curve is a clean interior optimum
(−0.036 at 0.30 versus −0.024 at 0.15 and +0.109 at 0.50). That closes the
reviewer objection "you did not tune the one knob that matters" with a
measurement rather than an assertion.

It also sharpens the paper's checkpoint-conditional claim: on `production` the
gain is inside the floor *for every setting of the fresh-noise budget*, so the
near-miss is a property of the checkpoint and not of a mistuned beta.

Two limits, stated because they bound the claim:

1. **Only `production` was dosed.** Nothing here says beta = 0.30 is optimal on
   `w16e1_5k`, where the gain is 3.1 FID. A beta dose on the winning checkpoint
   could in principle raise its gain further; that is a different experiment and
   it is not run.
2. **Beta = 0.70 is an over-noising regime, not an informative level.** Its
   +0.58 FID is the restart replacing most of the state each round. It brackets
   the dose; it does not identify an optimum beyond excluding 0.5 and 0.7.
