# GAP-78 — the dispersion gate, tested offline and falsified

**Date:** 2026-10-23
**Author:** GAP-78 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-78-R5C-DISPERSION-GATE` (P0), acceptance step (1) —
"first an offline check: the chosen observable must order the four checkpoints'
measured rho correctly, using only existing samples".
**Status:** the pre-registered premise is **falsified offline**. No GPU run was
spent on it. The gate is re-scoped to the observable the data does support.
**Frozen surfaces:** untouched.

---

## 0. Pre-registration (written before the numbers below)

Two questions, deliberately separated, because they are not the same test:

* **Q1 — is the observable a rho proxy?** Kendall tau between the observable
  across the four checkpoints and their measured baseline `rho` (GAP-64c,
  `verification_outputs/gap64c-dispersion/dispersion.json`). The pre-registration
  named this test.
* **Q2 — does the observable separate the outcomes?** Is there a single
  threshold putting every checkpoint the framework **wins** on one side and
  every checkpoint it **loses** on the other, with the outcome read from the
  GAP-76 3-seed grid at N = 1000, NFE = 50?

**Admissibility rule, fixed before looking.** Q1 alone is not enough — an
observable can order rho perfectly and still be useless as a gate (the trivial
case is rho itself). Q2 alone is not enough either: with four checkpoints, any
statistic monotone in model quality separates them, and GAP-67 §6.2 already
showed this cross-section is confounded. A gate is admissible only if it passes
**both** and has a mechanism that predicts the sign without fitting a threshold
to these four points. Anything that fails that bar is reported and **not**
implemented.

Falsification: if no admissible observable exists, GAP-78's gate design is dead
as stated and the gap is re-scoped, not re-run.

---

## 1. Data

Four MNIST-FM checkpoints, the GAP-76 grid, seed 42, N = 1000, NFE = 50,
`cosine` arm. Baseline samples are the arm's own (`baseline_samples.npz`); the
framework samples are `cosine_samples.npz` from the same run, so the pair is
exact and no re-sampling is involved.

Outcomes (GAP-76, three seeds, ΔFID relative to the matched baseline):

| checkpoint | ΔFID (s42/s43/s44) | outcome |
|---|---|---:|
| `production` | +1.23 / +1.42 / +1.07 % | LOSS |
| `w16e1_60k` | +2.43 / +2.41 / +2.44 % | LOSS |
| `w16e1_10k` | −4.61 / −4.28 / −4.65 % | WIN |
| `w16e1_5k` | −13.24 / −12.97 / −13.24 % | WIN |

Reproduce: `tools/gap78_observable_screen.py`, output in
`verification_outputs/gap78-observable-screen/screen.json`.

---

## 2. Result

| observable | production | 60k | 10k | 5k | Q1 τ vs rho | Q2 separates |
|---|---:|---:|---:|---:|---:|:--:|
| `rho` (the pre-registered gate) | 0.7819 | 0.7039 | 0.7523 | 1.0055 | +1.00 | **no** |
| `mean_shift` (needs reference) | 2.2092 | 2.3633 | 2.9381 | 3.6246 | +0.33 | yes |
| `participation_ratio` | 38.20 | 42.12 | 63.34 | 79.08 | +0.33 | yes |
| `mean_nn_dist` | 5.369 | 5.207 | 5.736 | 6.906 | +0.67 | yes |
| `mean_pair_dist` | 7.342 | 6.999 | 7.230 | 8.370 | +1.00 | no |
| `mean_norm` | 9.635 | 9.649 | 8.312 | 7.264 | −0.67 | yes (lower) |
| `contraction` κ | 0.9527 | 0.8674 | 0.6751 | 0.5465 | −0.33 | yes (lower) |

**`rho` fails Q2.** The counterexample is `w16e1_10k` against `production`:
10k is *more* under-dispersed (0.7523 vs 0.7819) and yet wins by 4.3 % while
production loses by 1.2 %. A monotone rule in the base's dispersion therefore
predicts the wrong sign on one of the four checkpoints. The gate as designed
cannot be implemented, and no GPU run should be spent on it.

`mean_pair_dist` also has τ = +1.00 with rho and also fails Q2 — the same
inversion, one dimension up.

---

## 3. Why the four observables that pass Q2 are still not admissible

`mean_shift`, `participation_ratio`, `mean_nn_dist`, `mean_norm` and κ all
separate 4/4. None of them is admissible under §0:

* `mean_shift` needs the reference mean, so it is not computable from the
  model's own samples — it cannot be the deployment gate.
* The other four have τ ≤ +0.67 against rho, i.e. they are **not** rho proxies.
  They pass Q2 by implementing a *different* hypothesis than the one
  pre-registered, which is exactly the post-hoc selector the pre-registration
  forbids.
* All of them are monotone in model quality across four checkpoints. GAP-67
  §6.2 measured this confound directly: the same cross-section gave a
  4.6–6.1× "amplification" that a within-checkpoint dose-response then
  falsified at ≈ −0.05×. A 4/4 separation here is the same object.

So: **the offline check cannot license any gate.** That is the finding
acceptance step (1) asked for, and it is negative.

---

## 4. What the data does say, and why it changes the mechanism

The one observable with a causal reading is the **realised contraction**

```
kappa = tr(Sigma_restart) / tr(Sigma_base)
```

measured on the same samples, reference-free, and available at inference time
from a pilot batch. Its ordering against the outcome is exact:

| κ | 0.5465 | 0.6751 | 0.8674 | 0.9527 |
|---|---|---|---|---|
| outcome | WIN −13 % | WIN −4.3 % | LOSS +2.4 % | LOSS +1.2 % |

The mechanism is **not** the dispersion of the base. It is Monte-Carlo variance
reduction: each restart round re-draws the noise and re-integrates, so the
`R`-round endpoint averages over the model's *own* conditional noise at `t = m`.
The amount of noise averaged out **is** `1 − κ`. A near-deterministic model
(`production`, κ = 0.95) has almost nothing to average, so the extra rounds only
add cost; a noisy model (`w16e1_5k`, κ = 0.55) has a great deal to average, and
the averaging is worth 13 %.

`rho` is a **side effect** of κ, not its cause — which is why rho fails to
predict the sign. GAP-67 §6.3 reached the same place from the other direction:
the contraction is a property of conditioning (`Var(E[x1|x_m]) ≤ Var(x1)`), not
of the blend's arithmetic.

This also explains why GAP-67's noise-scale correction was absorbed (the
velocity field is scale-normalising, so the input moment is not read) while the
output moment moves freely.

---

## 5. Consequence for GAP-78

**A gate cannot turn `production` into a win.** A gate can only *skip* the
restart where κ ≈ 1, and skipping returns the baseline exactly — a zero delta,
not a negative one. GAP-64's census of 35 recorded configurations on this cell
never produced a negative delta on `production`, which is consistent: a
converged sampler has no error for an averaging step to remove.

Under the pre-registered win definition (`docs/audit/gap84-inference-frontier.md`
§0.5–§0.6) that is still enough for a **cell** win, because a zero delta passes
weak dominance. What it is not enough for is a *strict gain* on those two
checkpoints, and the paper must not claim one.

Re-scope, in order:

1. **κ as a deployment selector**, not rho. Measure κ from a pilot batch
   (round-0 vs round-`R` trace ratio), skip the restart when κ is above a
   threshold. This makes the framework **never worse**, which is the
   precondition for frontier dominance.
2. **Fix the threshold causally, not from these four points.** The test is a
   within-checkpoint dose-response: sweep `m ∈ {0.3, 0.5, 0.7, 0.9}` on one
   losing and one winning checkpoint and check whether the sign of ΔFID flips
   exactly where κ crosses the candidate threshold. MNIST-FM is NumPy/CPU, so
   this needs no GPU — it is the only experiment in this gap that does not.
3. **Do not claim a strict gain on `production` / `w16e1_60k`.** They are
   weak-dominance cells. The R5c strict gains are `w16e1_10k` and `w16e1_5k`.

---

## 6. What was not done, and why

* No GPU run. The premise failed the offline check, which is exactly what the
  offline check is for.
* No threshold was chosen. Choosing one from four points would be fitting the
  gate to its own test set, and GAP-67 §6.2 shows the resulting number would not
  replicate.
* `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md` and `tnnls_submission/**`
  are untouched: nothing here changes a recorded claim, it removes a planned
  one.
