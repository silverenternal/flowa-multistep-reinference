# GAP-76 — removing the first-moment defect at the source

**Date:** 2026-10-21
**Status:** running (seed 42 launched 2026-10-21T12:28Z, pre-registration written after launch but before any result was read).
**Question:** GAP-77 measured that the restart displaces the batch mean away from
the reference in **36/36** cells and contracts the covariance in **36/36**, and
that removing the displacement arithmetically moves the mean ΔFID from
**+7.97 % to −3.33 %** (4/36 → 18/36 wins). Can that removal be done **at the
source**, without the reference and without a post-hoc calibration to a data
statistic?

---

## 0. Pre-registration

### 0.1 The operator change

`scripts/wave191_p3_mnist_sweep.py --mean-preserve` (additive, default off).
After the last round, the framework arm's cloud is translated so its batch
centroid equals the **round-0** centroid of the same run:

```
x_final ← x_final − ( mean(x_final) − mean(x_round0) )
```

`x_round0` is the single-pass endpoint the same run already produces, so the
correction costs nothing extra and uses **no reference statistic**. A
translation leaves the covariance matrix unchanged, so by construction this
removes the first-moment channel and leaves the contraction channel intact.

This is deliberately *not* GAP-72's calibration, which translated both arms to
the **training** mean. That version is post-hoc and needs a data statistic; this
one is an operator.

### 0.2 Predictions (falsifiable)

1. **Control — the run is bit-identical up to the translation.**
   `Tr(Σ)` and `cross` must reproduce the `gap57-equal-nfe-ladder-n1000`
   values *exactly* (they are translation-invariant). If they do not, the run
   is not comparable and nothing below counts.

2. **The displacement collapses.** `‖mean(arm) − mean(baseline)‖` must fall from
   ~1.9–4.7 (GAP-72) to **< 0.2**.

3. **The ΔFID matches the GAP-77 counterfactual** to within seed noise. Predicted
   seed-42 values (`gap77-restart-mechanism/decomposition.json`, column
   `mean_preserved_delta_fid`):

   | ckpt | cosine | codimension_sheet | evidence_driven |
   |---|---:|---:|---:|
   | `production` | +0.128 | +0.119 | +0.088 |
   | `w16e1_5k` | −3.249 | −3.181 | −3.247 |
   | `w16e1_10k` | −0.784 | −0.677 | −0.732 |
   | `w16e1_60k` | +0.279 | +0.353 | +0.338 |

   Falsified if any cell is off by more than the seed-42 ↔ 43 spread of the
   same quantity in the gap57 ladder.

4. **The win count rises.** At least 8 of the 12 seed-42 cells should be
   non-positive ΔFID, against 2/12 in the measured ladder.

### 0.3 What would make this not a fix

If prediction 2 holds but prediction 3 fails, the mean was not the only thing
the translation moved and the two-channel story in GAP-77 is incomplete. If
prediction 1 fails, the comparison is void and the run must be redone rather
than reinterpreted.

### 0.4 Scope limit, stated up front

This is a **batch-level** correction: it needs the whole generated batch to
estimate one centroid. It is legitimate for a benchmark comparison and for any
sampling job where a batch is produced anyway, but it is not a per-sample
operator, and the paper must say so. It also cannot help a *single* sample
generated in isolation.

## 1. Results

*(filled in after the seed-42 sweep completes; see `reproduce/gap76_mean_preserving.sh`)*
