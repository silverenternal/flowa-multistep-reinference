# GAP-76 — removing the first-moment defect at the source

**Date:** 2026-10-21
**Status:** seed 42 complete (12/12 cells, predictions 1–3 exact, prediction 4
missed); seeds 43/44 running for the significance table.
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

## 1. Results — seed 42

Seed-42 sweep: 4 checkpoints × 4 arms × N=1000, matched NFE=50, R=4, β_total=0.5,
`equal_budget`, `t0=memory`, shared seed-keyed prior. NumPy/CPU, 1 h 40 m wall for
the four checkpoints. `PYTHONPATH=. python3 tools/gap76_report.py`.

### 1.1 Predictions 1–3 hold exactly

| check | pre-registered bar | observed |
|---|---|---|
| 1. control (`Tr(Σ)`, `cross` unchanged) | exact | **12/12**, max \|Δcross\| = 6.0e−14, max \|ΔTr\| = 3.6e−15 |
| 2. displacement `‖mean(arm)−mean(base)‖` | < 0.2 | **0.0037 … 0.0152** (was 0.797 … 1.969) |
| 3. ΔFID vs GAP-77 counterfactual | within seed noise | **max error 0.019 FID units** across all 12 cells |
| 4. ≥ 8 of 12 cells non-positive | ≥ 8/12 | **6/12 — misses** (see §1.3) |

The control is the load-bearing one: the translation changes `bias` and nothing
else. Every downstream number in this section is therefore the *same run* as the
gap57 ladder with one moment moved, not a new sample of the model.

### 1.2 The table

`ΔFID` in FID units against the same-seed baseline; `%` against that baseline's
FID. Verdict uses the paper's own effect floor (`|ΔFID| < 1.0` ⇒ tie), the same
rule as `gap75-r5c-n1000-table.md`.

| ckpt | arm | base FID | Δ old | old % | **Δ new** | **new %** | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `production` | cosine | 9.97 | +0.888 | +8.91 % | **+0.122** | **+1.23 %** | TIE |
| `production` | codimension_sheet | 9.97 | +1.300 | +13.04 % | **+0.105** | **+1.05 %** | TIE |
| `production` | evidence_driven | 9.97 | +0.944 | +9.47 % | **+0.082** | **+0.82 %** | TIE |
| `w16e1_10k` | cosine | 16.96 | +0.419 | +2.47 % | **−0.782** | **−4.61 %** | TIE |
| `w16e1_10k` | codimension_sheet | 16.96 | +1.823 | +10.74 % | **−0.669** | **−3.95 %** | TIE |
| `w16e1_10k` | evidence_driven | 16.96 | +1.288 | +7.59 % | **−0.729** | **−4.30 %** | TIE |
| `w16e1_5k` | cosine | 24.50 | −2.365 | −9.65 % | **−3.243** | **−13.24 %** | **WIN** |
| `w16e1_5k` | codimension_sheet | 24.50 | +0.026 | +0.11 % | **−3.162** | **−12.91 %** | **WIN** |
| `w16e1_5k` | evidence_driven | 24.50 | −0.016 | −0.07 % | **−3.241** | **−13.23 %** | **WIN** |
| `w16e1_60k` | cosine | 11.40 | +1.758 | +15.42 % | **+0.277** | **+2.43 %** | TIE |
| `w16e1_60k` | codimension_sheet | 11.40 | +2.213 | +19.41 % | **+0.350** | **+3.07 %** | TIE |
| `w16e1_60k` | evidence_driven | 11.40 | +1.775 | +15.57 % | **+0.337** | **+2.96 %** | TIE |

Census at the effect floor: **old 1 W / 5 T / 6 R → new 3 W / 9 T / 0 R**.
Mean ΔFID: **+7.75 % → −3.39 %**, against GAP-77's arithmetic prediction of
−3.33 %. The largest remaining regression is **+3.07 %** (was +19.41 %).

Per checkpoint, mean of the three arms:

| ckpt | old | new |
|---|---:|---:|
| `production` | +10.47 % | **+1.04 %** |
| `w16e1_10k` | +6.93 % | **−4.28 %** |
| `w16e1_5k` | −3.20 % | **−13.12 %** |
| `w16e1_60k` | +16.80 % | **+2.82 %** |

The contraction channel is what survives: `Tr(Σ)` is unchanged by construction,
so the entire −3.39 % is the covariance gain that the location defect was
masking. On `w16e1_5k` that gain is worth 3.2 FID units; on `production` it is
worth ~0.9, which is exactly the defect's size — the two channels cancel and the
cell lands on a tie.

### 1.3 Prediction 4 misses, and it was mis-set

The pre-registration asked for ≥ 8/12 non-positive. Observed: 6/12. That is a
miss and it stands as one.

It was also a bad bar, and the reason is in GAP-77's own output: the
counterfactual census there is **18/36 = 50 %**, and 6/12 = 50 %. Prediction 3
and prediction 4 were sourced from the same counterfactual, so 4 could not have
been 8/12 without 3 failing. The bar was written from the headline *mean*
(−3.33 %) rather than from the *census* that produced it. Recording this as a
pre-registration defect, not as a result that "should have" passed.

### 1.4 What this does and does not establish

- It establishes that the two-channel decomposition is **quantitatively exact**:
  the counterfactual predicted all 12 ΔFID values to within 0.019 FID units from
  a completely separate run. GAP-77's model is not a narrative.
- It establishes that the defect is **removable without a reference statistic**
  and that removing it costs nothing on the covariance channel (12/12 exact).
- It does **not** establish significance: one seed. The three apparent wins are
  all on `w16e1_5k`; the other nine cells are ties at the effect floor, and a
  three-seed CI is required before any of them can be called a win or a loss.
  Seeds 43/44 are running (`SEEDS="43 44" bash reproduce/gap76_mean_preserving.sh`).
- It does **not** touch the model-limited ceiling noted in GAP-77: `production`'s
  baseline FID is 9.97 and its 3-step endpoint is within 0.32 % of its 100-step
  endpoint, so no sampling-side operator can move that cell beyond the tie band.

### 1.5 Scope

The correction is batch-level (§0.4) and is a *translation*, so it cannot fix a
shape error. It also cannot recover a cell whose contraction gain is smaller
than its first-moment defect — `production` and `w16e1_60k` remain slightly
positive for exactly that reason, and no amount of anchoring changes it.
