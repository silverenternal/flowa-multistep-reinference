# GAP-76 — removing the first-moment defect at the source

**Date:** 2026-10-21
**Status:** complete — 3 seeds × 12 cells. Predictions 1–3 exact (36/36),
prediction 4 missed and recorded as a mis-set bar (§1.3).
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

## 1. Results — three seeds

Sweep: 4 checkpoints × 4 arms × **3 seeds** × N=1000, matched NFE=50, R=4,
β_total=0.5, `equal_budget`, `t0=memory`, shared seed-keyed prior. NumPy/CPU,
1 h 40 m wall per seed (4 h 59 m total). `PYTHONPATH=. python3 tools/gap76_report.py`.

### 1.1 Predictions 1–3 hold exactly

| check | pre-registered bar | observed |
|---|---|---|
| 1. control (`Tr(Σ)`, `cross` unchanged) | exact | **36/36**, max \|Δcross\| = 6.0e−14, max \|ΔTr\| = 3.6e−15 |
| 2. displacement `‖mean(arm)−mean(base)‖` | < 0.2 | **0.0037 … 0.0152** (was 0.787 … 1.972) |
| 3. ΔFID vs GAP-77 counterfactual | within seed noise | **max error 0.019 FID units** across all 36 cells |
| 4. ≥ 8 of 12 cells non-positive | ≥ 8/12 | **6/12 at seed 42; 18/36 across seeds — misses** (see §1.3) |

The control is the load-bearing one: the translation changes `bias` and nothing
else. Every downstream number in this section is therefore the *same run* as the
gap57 ladder with one moment moved, not a new sample of the model.

### 1.2 The table — 3 seeds, CI at 95 % (t, df = 2)

`ΔFID` in FID units against the same-seed baseline; `%` against that baseline's
FID. Two verdicts, the pair used by `gap75-r5c-n1000-table.md`: **strict** = the
seed CI excludes 0; **floor** = the paper's 1-FID-unit effect floor.

| ckpt | arm | Δ old | **Δ new** | **CI95** | **new %** | strict | floor |
|---|---|---:|---:|---|---:|---|---|
| `production` | cosine | +0.951 | **+0.124** | [+0.081, +0.166] | +1.24 % | REGRESS | TIE |
| `production` | codimension_sheet | +1.285 | **+0.102** | [+0.082, +0.122] | +1.02 % | REGRESS | TIE |
| `production` | evidence_driven | +1.033 | **+0.109** | [+0.039, +0.178] | +1.09 % | REGRESS | TIE |
| `w16e1_10k` | cosine | +0.476 | **−0.765** | [−0.842, −0.688] | −4.51 % | **WIN** | TIE |
| `w16e1_10k` | codimension_sheet | +1.812 | **−0.666** | [−0.730, −0.603] | −3.93 % | **WIN** | TIE |
| `w16e1_10k` | evidence_driven | +1.271 | **−0.738** | [−0.792, −0.684] | −4.35 % | **WIN** | TIE |
| `w16e1_5k` | cosine | −2.294 | **−3.220** | [−3.288, −3.152] | −13.15 % | **WIN** | **WIN** |
| `w16e1_5k` | codimension_sheet | +0.042 | **−3.120** | [−3.229, −3.010] | −12.74 % | **WIN** | **WIN** |
| `w16e1_5k` | evidence_driven | +0.061 | **−3.215** | [−3.270, −3.161] | −13.13 % | **WIN** | **WIN** |
| `w16e1_60k` | cosine | +1.774 | **+0.276** | [+0.271, +0.281] | +2.43 % | REGRESS | TIE |
| `w16e1_60k` | codimension_sheet | +2.211 | **+0.341** | [+0.274, +0.408] | +2.99 % | REGRESS | TIE |
| `w16e1_60k` | evidence_driven | +1.806 | **+0.340** | [+0.289, +0.392] | +2.99 % | REGRESS | TIE |

Census:

| rule | old | new |
|---|---|---|
| strict (CI excludes 0) | 1 W / 2 T / 9 R | **6 W / 0 T / 6 R** |
| effect floor (\|ΔFID\| < 1.0) | 1 W / 5 T / 6 R | **3 W / 9 T / 0 R** |

Mean ΔFID across the 12 cells: **+7.75 % → −3.34 %**, against GAP-77's
arithmetic prediction of −3.33 %. The largest remaining regression is **+2.99 %**
(was +19.41 %). Under the paper's own effect floor there are **no regressions
left**; under the stricter CI rule the six remaining losses are all on
`production` (+1.0 … +1.2 %) and `w16e1_60k` (+2.4 … +3.0 %).

Per checkpoint, mean of the three arms:

| ckpt | old | new |
|---|---:|---:|
| `production` | +10.47 % | **+1.04 %** |
| `w16e1_10k` | +6.93 % | **−4.28 %** |
| `w16e1_5k` | −3.20 % | **−13.12 %** |
| `w16e1_60k` | +16.80 % | **+2.82 %** |

The contraction channel is what survives: `Tr(Σ)` is unchanged by construction,
so the entire −3.34 % is the covariance gain that the location defect was
masking. On `w16e1_5k` that gain is worth 3.2 FID units; on `production` it is
worth ~0.9, which is exactly the defect's size — the two channels cancel and the
cell lands on a tie.

### 1.3 Prediction 4 misses, and it was mis-set

The pre-registration asked for ≥ 8/12 non-positive. Observed: **6/12** at seed
42 and **18/36** across seeds. That is a miss and it stands as one.

It was also a bad bar, and the reason is in GAP-77's own output: the
counterfactual census there is **18/36 = 50 %**, and the measured census is
**18/36 = 50 %**. Prediction 3 and prediction 4 were sourced from the same
counterfactual, so 4 could not have been 8/12 without 3 failing. The bar was
written from the headline *mean* (−3.33 %) rather than from the *census* that
produced it. Recording this as a pre-registration defect, not as a result that
"should have" passed. The fact that the measured census lands on the predicted
census exactly is itself the strongest single check in this doc.

### 1.4 What this does and does not establish

- It establishes that the two-channel decomposition is **quantitatively exact**:
  the counterfactual predicted all 36 ΔFID values to within 0.019 FID units from
  a completely separate run, and predicted the win census exactly (18/36).
  GAP-77's model is not a narrative.
- It establishes that the defect is **removable without a reference statistic**
  and that removing it costs nothing on the covariance channel (36/36 exact).
- It establishes **significance for the six wins**: every `w16e1_10k` and
  `w16e1_5k` cell has a 3-seed CI excluding 0, the tightest being
  [−3.288, −3.152] for `w16e1_5k/cosine`.
- It does **not** establish that the six remaining losses are large. All six are
  under the paper's 1-FID-unit effect floor (+0.28 … +0.34 FID units), so under
  the rule the paper actually uses they are ties, not regressions. Reporting both
  rules rather than picking one.
- It does **not** touch the model-limited ceiling noted in GAP-77: `production`'s
  baseline FID is 9.97 and its 3-step endpoint is within 0.32 % of its 100-step
  endpoint, so no sampling-side operator can move that cell beyond the tie band.

### 1.5 Scope

The correction is batch-level (§0.4) and is a *translation*, so it cannot fix a
shape error. It also cannot recover a cell whose contraction gain is smaller
than its first-moment defect — `production` and `w16e1_60k` remain slightly
positive for exactly that reason, and no amount of anchoring changes it.
