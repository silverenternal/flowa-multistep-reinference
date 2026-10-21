# GAP-75 — the corrected R5c table: 9 regressions, 1 win, 2 ties

**Date:** 2026-10-21
**Status:** closed. This is the R5c number the paper should quote.
**Question:** with the invalid chunk statistic retired (GAP-73), what does R5c
actually say at N=1000, across the three seeds that already exist?

---

## 1. What was run

`tools/gap75_r5c_table.py`, CPU only. It reads
`verification_outputs/gap57-equal-nfe-ladder-n1000/<ckpt>_s<seed>/`, which
already holds 4 checkpoints × 3 seeds × (baseline + 3 arms) at N=1000, matched
NFE=50, `restart_t0_mode=memory`, `shared_prior`, `seed_keyed_prior`.

The three seeds are genuinely independent draws — the prior batch id carries
the seed suffix, and the baseline `npz` md5s differ across seeds
(`production`: `661b1cd9`, `9c621528`, `99ed255a`). No sampling was done.

Per cell:

* **headline Δ** — FID(arm) − FID(baseline) at N=1000 against the full 10 000
  reference, which is the statistic GAP-73 validated;
* **within-seed SE** — 30 paired N=500 subsamples, matched-N reference, scaled
  by `sqrt(500/1000)`;
* **across-seed CI** — mean ± `t(0.975, df=2) × sd/√3`;
* **two verdicts** — the paper's effect-floor rule (`|mean| >= 1 FID`, the
  `CLM-060` convention) and the strict rule (the 3-seed CI excludes 0). They
  disagree on cells that are statistically clear but under one FID unit.

## 2. Observed

| ckpt | arm | mean ΔFID | mean Δ% | 95 % CI (FID) | effect-floor | strict |
|---|---|---:|---:|---|---|---|
| `production` | cosine | +0.951 | +9.52 % | [+0.82, +1.09] | TIE | REGRESSES |
| `production` | codimension_sheet | +1.285 | +12.87 % | [+1.23, +1.34] | REGRESSES | REGRESSES |
| `production` | evidence_driven | +1.033 | +10.34 % | [+0.82, +1.24] | REGRESSES | REGRESSES |
| `w16e1_10k` | cosine | +0.476 | +2.81 % | [+0.35, +0.60] | TIE | REGRESSES |
| `w16e1_10k` | codimension_sheet | +1.812 | +10.69 % | [+1.74, +1.88] | REGRESSES | REGRESSES |
| `w16e1_10k` | evidence_driven | +1.271 | +7.49 % | [+1.15, +1.39] | REGRESSES | REGRESSES |
| `w16e1_60k` | cosine | +1.774 | +15.59 % | [+1.69, +1.86] | REGRESSES | REGRESSES |
| `w16e1_60k` | codimension_sheet | +2.211 | +19.43 % | [+2.06, +2.37] | REGRESSES | REGRESSES |
| `w16e1_60k` | evidence_driven | +1.806 | +15.87 % | [+1.72, +1.89] | REGRESSES | REGRESSES |
| `w16e1_5k` | cosine | −2.294 | −9.37 % | [−2.45, −2.14] | **SUPPORTS** | **SUPPORTS** |
| `w16e1_5k` | codimension_sheet | +0.042 | +0.17 % | [−0.06, +0.15] | TIE | TIE |
| `w16e1_5k` | evidence_driven | +0.061 | +0.25 % | [−0.11, +0.23] | UNDERPOWERED | TIE |

**Effect-floor distribution (12 cells):** 7 REGRESSES, 3 TIE, 1 SUPPORTS,
1 UNDERPOWERED.
**Strict distribution (12 cells):** 9 REGRESSES, 2 TIE, 1 SUPPORTS.

## 3. Interpretation

### 3.1 The sign is not in doubt

Every one of the nine regression cells has all three seeds on the same side,
and the per-seed spread is small (+0.9/+1.0/+1.0 FID for `production`/cosine;
+1.8/+1.8/+1.8 for `w16e1_60k`/cosine). The 3-seed CIs are narrow for the same
reason: the seeds differ only in the prior draw, and at N=1000 the sampling
noise is already small. This is not an underpowered cell in the usual sense.

### 3.2 What it replaces

The published R5c reading is "framework WINS −28.43 %" (`CLM-059`, smoke
checkpoint, chunk test `d_z = −13.18`). At N=1000 with the corrected statistic
the same model family gives **9 regressions, 1 win, 2 ties**, with the largest
regression at +19.4 % (`w16e1_60k`/`codimension_sheet`) and the only win at
−9.4 % (`w16e1_5k`/cosine).

The single win is the least-trained checkpoint in the ladder, and it is the one
where the baseline's own FID is worst (24.50). That is consistent with GAP-64's
finding that R5c has no NFE headroom: on a converged baseline the restart can
only add perturbation cost, and the one model that is far from converged is the
one where the perturbation buys something.

### 3.3 What the verdict labels mean here

The two verdict columns disagree on four cells, and the disagreement is
informative rather than a defect:

* `production`/cosine (+0.951 FID, +9.5 %) and `w16e1_10k`/cosine (+0.476 FID,
  +2.8 %) are statistically clear (CI excludes 0, three seeds agreeing) but
  under the paper's one-FID-unit floor. Calling them TIE is the paper's own
  convention and should be kept *if* the floor is applied consistently — but
  the table must then also say that the regression is 9.5 % and 2.8 %, not
  "no effect".
* `w16e1_5k`/evidence_driven is below the floor and its seeds straddle zero
  (−0.0, +0.1, +0.1). Effect-floor says UNDERPOWERED, strict says TIE. Both are
  defensible; TIE is the honest one, because the CI is tight around +0.06 FID.

### 3.4 What the CI does *not* cover

The 3-seed CI is a **seed-to-seed** interval. It does not include the
estimator's own bias: GAP-73 measured a +0.7 pp gap between the matched-N
N=1000 estimate and the 10K-reference headline on `production`, and the 1/N fit
put the asymptote within 0.7 pp of the headline on all four checkpoints. So the
bias is small but not zero, and it is not in these error bars. The table should
be quoted with that caveat, not as an exact effect size.

## 4. Flags raised, not acted on

Per the recording policy the frozen surfaces are untouched. This table makes
three existing statements untenable and they are flagged, not edited:

1. **`CLM-059` R5c "WINS −28.43 %"** — chunk statistic, superseded.
2. **`CLM-060` R5c power row** — inherits the chunk statistic.
3. **Any §10 table quoting an R5c ΔFID** — same.

Also flagged, because it is the same defect one level up: the R5c cell is
currently counted as a WINS in the 5-of-7 R-level wins tally
(`CLM-060` line 3842). On this table it is a REGRESSES cell. The tally is not
edited here.

## 5. Unresolved

* The smoke checkpoint (`data/mnist_fm.npz`, the `CLM-059` subject) has no
  N=1000 3-seed ladder on disk, so the −28.43 % number cannot be recomputed at
  the corrected statistic without new sampling. The four production-ladder
  checkpoints are the available evidence, and they are unanimous in direction
  except for the single `w16e1_5k` win.
* Nothing here explains *why* the framework loses; that is GAP-72.
