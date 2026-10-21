# GAP-65 — out-of-family test of the dispersion sign rule

**Status:** CLOSED — **CONSISTENT, but the positive direction is untested out of family**
**Date:** 2026-10-21
**Pre-registration:** the decision rule below was written into `todo.json`
(`GAP-65-DISPERSION-SELECTOR.acceptance`) *before* any of the numbers in §3 were
computed. It is reproduced verbatim here so the ordering is auditable.
**Tools:** `tools/gap64_dispersion_diagnostic.py` (MNIST), ad-hoc re-read of the
cached InceptionV3 features for R5b (no new sampling).

---

## 0. TL;DR

| cell | `rho_base` | rule predicts | measured `dFID` | match |
|---|---:|---|---:|---|
| R5c `production` | 0.782 | hurt | +8.91% | yes |
| R5c `w16e1_10k` | 0.752 | hurt | +2.47% | yes |
| R5c `w16e1_60k` | 0.704 | hurt | +15.42% | yes |
| R5c `w16e1_5k` | 1.006 | **help** | **−9.65%** | yes |
| R5b CIFAR-10 | 0.972 | hurt | +1.48% (best arm) | yes |

**5/5 where the rule is computable.** The pre-registered threshold was 6/7; only
5 cells are computable because R1 and R3 have no FID-style feature space, so the
threshold is **not met on a technicality of applicability, not on a failed
prediction**. That distinction is recorded rather than smoothed over.

But the rule's *useful* direction has exactly **one** supporting cell. In 4 of 5
cells the selector would output "do not apply the framework". A selector that
says "no" four times out of five is a monitoring statistic, not a contribution.

Within R5b, across 16 recorded cells (4 memory fractions × 4 arms × 3 seeds):

    corr(rho_arm, dFID) = -0.93

which is driven almost entirely by the three arms that **collapsed** to
`rho_arm ~ 0.10` (they received 75-79 NFE against codimension_sheet's 150) and
paid +18 to +23%. Within the non-collapsed arm the ordering is noisy
(`rho_arm` 0.972/0.978/0.872/0.938 → `dFID` +1.48/+7.64/+3.90/+8.47). So what
the R5b data establishes is **"dispersion collapse is the dominant FID cost"**,
not "`rho = 1` is the optimum".

## 1. Pre-registered rule (copied from `todo.json`, unchanged)

> The selector is SUPPORTED if the sign of the measured delta matches
> `sign(rho_base - 1)` in >= 6 of 7 cells (4 MNIST + 3 out-of-family);
> NOT_SUPPORTED otherwise, and in that case the rho rule is recorded as
> MNIST-specific and the paper's claim narrows to the measured cells.

Applicability was not pre-specified. That is a defect in the pre-registration
and it is disclosed as such: R1 and R3 were always going to be inapplicable
because their metrics are per-record scalars (hmmscan hits, `fg_dev`), not
distances in a feature space, and no reference dispersion exists for them.

## 2. Protocol

* **R5c** — already recorded in `docs/audit/gap64-r5c-operating-regime.md` §3.3;
  N=1000, seed 42, dispersion in the 128-d random projection.
* **R5b** — cached InceptionV3 features under
  `verification_outputs/gap46-r5b-memory/seed{42,43,44}-{default,m0.25,m0.5,m0.75}/inception_feats_cache/`,
  reference = `data/cifar10_inception_features.npz` (10 000 × 2048).
  `rho = tr(S_gen)/tr(S_ref)`, averaged over the three seeds.
  Measured `dFID` = `mean_delta_pct` from `gap46-memory-fraction.csv`.
* **R1 / R3** — no feature-space reference; rule not computable.

## 3. Observed

### 3.1 R5b, all 16 cells

| m | arm | `rho_arm` | `dFID%` |
|---|---|---:|---:|
| default | codimension_sheet | 0.9722 | +1.48 |
| default | cosine_anneal | 0.1483 | +23.13 |
| default | evidence_driven | 0.1513 | +22.67 |
| default | free_traj | 0.1421 | +22.15 |
| 0.25 | codimension_sheet | 0.9780 | +7.64 |
| 0.25 | cosine_anneal | 0.0956 | +18.83 |
| 0.25 | evidence_driven | 0.0973 | +18.16 |
| 0.25 | free_traj | 0.0940 | +19.17 |
| 0.5 | codimension_sheet | 0.8718 | +3.90 |
| 0.5 | cosine_anneal | 0.0963 | +21.52 |
| 0.5 | evidence_driven | 0.0943 | +21.96 |
| 0.5 | free_traj | 0.0972 | +21.78 |
| 0.75 | codimension_sheet | 0.9381 | +8.47 |
| 0.75 | cosine_anneal | 0.0945 | +17.98 |
| 0.75 | evidence_driven | 0.1003 | +17.84 |
| 0.75 | free_traj | 0.0983 | +17.72 |

`rho_base = 0.9717` on every row (same baseline; a correctness check on the
measurement, not a result).

### 3.2 The collapse is a budget artefact, not a mechanism

The three non-codimension arms received **75-79 NFE** against codimension_sheet's
**150** in this driver, because the arm's step count is set by its own `n_cap`
and the memory sweep never applied an equal-total-NFE constraint. Their
`rho_arm ~ 0.10` is what a 4x under-budgeted sampler looks like: it has not
finished moving, so the cloud is a shrunken blob. Reading their +18 to +23% as
evidence about the blend would be wrong; it is evidence about the budget.

This is the same defect GAP-55 fixed for the MNIST driver and it has **not** been
fixed for the R5b driver.

## 4. Interpretation

1. The sign rule is not falsified, and it is not established either. It has one
   positive cell (`w16e1_5k`, `rho_base = 1.006`) and four negative ones.
2. The generalisable content is narrower and still useful: **the framework's FID
   cost is governed by how far it moves the output dispersion away from the
   data's**, with collapse being catastrophic. `rho_arm` is a cheap monitor that
   a practitioner can compute from a 200-sample pilot.
3. The selector framing ("apply iff `rho_base >= 1`") survives as an engineering
   guard rail — it would have correctly refused the framework on 4 of 5 cells
   where it loses — but it is not a contribution that can carry a paper.
4. Therefore the paper **cannot** claim a fidelity improvement from this
   mechanism, and cannot claim "never worse" as a measured property. The
   measurable claim lives on the coverage / functional metrics (R1, R6), which is
   exactly what GAP-60 has to test for a collapse artefact.

## 5. What this changes in the plan

* `GAP-65-DISPERSION-SELECTOR` — **closed, CONSISTENT-BUT-UNTESTED**. Not a
  contribution. `rho` demoted from "selector" to "monitoring statistic".
* New prerequisite for any R5b claim: the R5b driver must adopt the GAP-55
  equal-total-NFE constraint before another R5b number is quoted. Recorded as
  `GAP-66-R5B-EQUAL-BUDGET`.
* GAP-60 is promoted: if R1's +74% is also a shrinkage artefact, the framework
  has no demonstrated quality win anywhere, and that has to be known before any
  further compute is spent.

## 6. Unresolved

* R1 and R3 remain without a dispersion analogue. Constructing one (e.g. per-record
  pLDDT spread against a natural-protein reference) is a research task, not a
  measurement, and is not scheduled.
* `rho` is measured on 200 generated samples for R5b and 1000 for R5c. The R5b
  values are therefore noisier; the 3-seed averaging mitigates but does not
  remove that.
