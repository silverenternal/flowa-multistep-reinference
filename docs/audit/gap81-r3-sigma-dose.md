# GAP-81 — R3 FlowMol3: the sigma dose (pre-registration, written before any run)

**Date:** 2026-10-26
**Status:** PRE-REGISTERED — no screen and no confirmation has run.
**Scope:** `scripts/wave338_p5_r3_n1000_paired.py` (one additive CLI flag,
`--perturbation-sigma`, default = the module constant) + a new artifact tree
under `verification_outputs/gap81-r3-sigma-dose/`. No frozen surface is touched
(`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.*`,
`tnnls_submission/**` unchanged).

---

## 0. What the R3 cell actually measures

The published R3 arm is **not** a restart. `scripts/wave338_p5_r3_n1000_paired.py`
generates both arms with one solve at NFE = 250; the framework arm differs from
the baseline only by
`_framework_perturb_prior`: an additive `N(0, sigma^2)` draw on the
**coordinate channel only** of the canonical prior, with `sigma = 0.05` as a
module constant. `PERTURBATION_SIGMA_FRAMEWORK` has never been varied, so the
dose of the one knob the cell owns has never been measured.

Two corrections to the ledger entry, both established before this
pre-registration and both required before the gap can be tested honestly.

### 0.1 The restart premise is refuted by the code and by GAP-68

GAP-81's original statement was that "the restart perturbs the state as if it
were continuous, so a blend across a class boundary breaks the flow's Lipschitz
premise". That is false for this adapter: `_channel_aware_blend`
(`adaptive_reflow/adapters/flowmol3_v2_adapter.py:1195`) already resamples the
discrete `raw_pair` channel categorically — the prior label is kept with
probability `m_pair` and otherwise replaced by a fresh label; only
`coordinate` and `charge` are interpolated. The class-preserving variant is the
existing flag `--restart-memory-fraction-pair 1.0`, and GAP-68 measured it at
N = 1000 × seeds 42/43/44 (arm A2):

| arm | mean Δ fg_dev | CI95 | `d_z` vs baseline |
|---|---:|---|---:|
| A1 all channels free | +0.0152 | [−0.270, +0.300] | +0.132 |
| **A2 topology locked** | **−0.0217** | **[−0.277, +0.234]** | **−0.211** |

The lock does beat the free blend (`d_z = −0.83` on the paired difference), but
it is null against the baseline and the power analysis in GAP-68 §1.4 puts the
arm-vs-baseline test at ~280 seeds. It is also the wrong arm for this cell:
`docs/audit/gap68-flowmol3-channels.md` §0.1(b) records that the R3 headline is
the σ-proxy, not the restart. So the restart route is **closed**, not
re-opened here.

### 0.2 The "near-miss" is one seed, and the 3-seed result is further away

The −0.061 / CI [−0.117, −0.001] / p = 0.043 figures that GAP-81 inherited are
a **single-seed bootstrap over records** (`gap55-r3-full-smiles`;
`docs/audit/gap50-evidence-grade-table.md` row R3). They are not a 3-seed test.
The canonical 3-seed paired result is:

| seeds | mean Δ | sd | `d_z` | `p` | CI95 |
|---|---:|---:|---:|---:|---|
| 42/43/44 | −0.0377 | 0.0939 | −0.401 | 0.559 | [−0.271, +0.196] |

`verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.json`

### 0.3 The bar, stated before any dose is measured

At n = 3 seeds the R-level α = 0.05/7 = 0.007143 is a two-sided t test with
df = 2, whose critical value is **11.769**. With the observed
`se = sd/√n = 0.0542`, clearing the bar requires

```
|mean Δ| >= 11.769 × 0.0542 = 0.638  fg_dev units
```

i.e. **17× the current 3-seed effect** (−0.0377). Equivalently, at the current
mean the seed-level sd would have to fall from 0.0939 to 0.0055.

This is the load-bearing constraint of the whole gap and it is why the screen
below is written as a *step-change* test rather than a search for a 10–20 %
improvement: no seed top-up is allowed, so a lever that moves the mean by 10 %
cannot win, and a run that could only produce that is not worth the GPU.

---

## 1. Arms and dose grid

One knob, six levels, **seed 42 only** (the screen), N = 1000 per arm,
NFE = 250, `--shared-prior` (so both arms see the same canonical prior per
batch — the GAP-37 pairing), `nfe_batch = 100`, `cuda:0`. Baseline arm identical
across all cells (`sigma = 0`), so the paired difference is one subtraction per
cell.

| cell | `--perturbation-sigma` |
|---|---:|
| S0 | 0.01 |
| S1 | 0.02 |
| S2 | 0.05 (the canonical CLM-068 arm — the reference, not a candidate) |
| S3 | 0.10 |
| S4 | 0.20 |
| S5 | 0.40 |

Two readings per cell, both recorded: the aggregate `fg_dev` paired difference
(the headline) and a per-seed bootstrap CI over records on the same paired
difference (the GAP-55 method, which is the only CI available at one seed).
`pb_validity_pct` is recorded as the guard.

## 2. Decision rule

**Eligibility (screen).** A dose is eligible iff

1. its paired `fg_dev` difference is at least **10×** the canonical −0.0377
   (i.e. ≤ −0.377), **and**
2. `pb_validity_pct` does not fall below the σ = 0.05 cell by more than 0.01
   absolute, **and**
3. the sample has not collapsed: unique-SMILES fraction ≥ 0.95 of the σ = 0.05
   cell.

Select the **smallest** eligible σ (least intervention). If none is eligible,
the prior-smoothing reading is falsified and no confirmation run happens.

**Confirmation.** The single eligible σ at seeds 42/43/44, N = 1000. WIN
requires the 3-seed paired CI to exclude 0 at α = 0.007143 with `fg_dev`
decreasing. Three seeds, no top-ups.

**Why 10× in the screen and 17× to win.** The screen is a *screen*: a dose that
cannot plausibly reach 17× at three seeds should not consume a confirmation
run. 10× is the pre-registered floor for "plausible", and the confirmation bar
stays the α. A dose at 10–17× goes to confirmation and may still fail — that
outcome is reportable and is not reframed afterwards.

## 3. What would make this not a lever

* `fg_dev(σ)` is monotone in σ over the grid: then the prior-smoothing reading
  ("an interior optimum exists") is wrong and σ is not a lever, only a
  trade-off knob against validity.
* Every σ is flat within ±10 % of the σ = 0.05 cell: the perturbation is inert
  in this range and the cell is limited by something the prior noise does not
  touch.
* A large σ lowers `fg_dev` only by collapsing diversity (guard 3 fires): that
  is arm D wearing a σ, and it is not eligible.

## 4. Declared boundaries (L-class, recorded before the run)

* **One knob.** No interaction with NFE is measured. A larger perturbation may
  need more steps to re-converge; NFE is held at the canonical 250 for both
  arms so the comparison stays matched. If a dose is eligible at 250, the
  NFE interaction is the first follow-up, not part of this gap.
* **One seed for the screen.** The screen can choose a dose; it may never be
  quoted as a result.
* **Aggregate metric.** `fg_dev` is one number per arm. The per-record
  REOS-flag proxy (Wave 208 P2 / 216 P1: −0.360 flags/mol, p = 8.03e−05 at
  n = 200) is a *different granularity* and is not what this gap tests; it is
  already significant and is recorded in CLM-068 as a direction-consistent
  proxy, not as the headline.
* **The restart is out of scope.** GAP-68 closed it (null at 3 seeds, ~280
  seeds needed). Re-running it here would be a seed top-up by another name.

## 5. Not done, and why

* No new seeds beyond 42/43/44.
* No restart arm.
* No change to CLM-068 or any frozen surface. If a σ is confirmed, the claim
  status is the user's call and this doc supplies the number, not the label.
