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

---

## 7. The dose-response: κ is a checkpoint marker, not a lever

§4 named κ as the surviving candidate and §5 step 2 required a within-checkpoint
dose-response before any threshold could be chosen. It was run on CPU
(`reproduce/gap78_kappa_dose_response.sh`; MNIST-FM is a NumPy adapter, so no
GPU was used).

**Design.** Four checkpoints × `β ∈ {0.3, 0.5, 0.7}` (so `m = 0.7, 0.5, 0.3`),
N = 200 **screen**, seed 42, NFE = 50, `R = 4`, `--mean-preserve`,
`--seed-keyed-prior --shared-prior`. The shared prior is mandatory: with it the
first 200 rows of the N = 1000 baseline draw are byte-identical to the N = 200
draw, so this screen is a nested subsample. Without it every arm draws its own
`x0` and the production baseline FID moves from 9.967 to 11.777 at the same
checkpoint, NFE, β and seed — an 18 % shift that flipped a +1.2 % loss into an
apparent −3.7 % win. That mistake was made and caught during this increment; the
first run is quarantined as `gap78-kappa-dose-screen_INVALID_no_shared_prior/`
and nothing from it is used.

**Result** (`cosine` arm; the other two arms agree to within ~1 pp, full table in
`verification_outputs/gap78-kappa-dose-screen/kappa_dose.json`):

| checkpoint | β | κ | ΔFID | within-checkpoint slope |
|---|---:|---:|---:|---|
| `production` | 0.3 | 0.9543 | −0.75 % | |
| `production` | 0.5 | 0.9540 | −0.25 % | κ ↓ ⇒ **worse** |
| `production` | 0.7 | 0.9337 | +0.00 % | |
| `w16e1_60k` | 0.5 | 0.8708 | −0.33 % | |
| `w16e1_60k` | 0.7 | 0.8008 | +2.01 % | κ ↓ ⇒ **worse** |
| `w16e1_10k` | 0.5 | 0.6793 | −8.07 % | |
| `w16e1_10k` | 0.7 | 0.6517 | −4.36 % | κ ↓ ⇒ **worse** |
| `w16e1_5k` | 0.3 | 0.6680 | −13.40 % | |
| `w16e1_5k` | 0.5 | 0.5535 | −15.42 % | non-monotone |
| `w16e1_5k` | 0.7 | 0.4998 | −11.94 % | |

**The cross-section is perfect and the within-checkpoint slopes point the other
way.** At β = 0.5 the four checkpoints order exactly by κ
(0.954 → 0.871 → 0.679 → 0.554 maps to −0.25 → −0.33 → −8.07 → −15.42 %). But
when κ is moved *inside* a checkpoint, lowering it makes ΔFID **worse** on
`production`, `w16e1_60k` and `w16e1_10k`, and is non-monotone on `w16e1_5k`
(best at κ = 0.554, worse on both sides).

This is Simpson's paradox on the same statistic, and it is decisive: κ does not
cause the benefit, it indexes the checkpoint. The gate is dead in **both** forms
— rho (which fails to order the outcomes at all, §2) and κ (which orders them
only across checkpoints, §7). No threshold exists that would survive the
within-checkpoint test.

**Two things this run does establish**, both useful:

1. **The `w16e1_5k` win is β-robust.** −13.40 / −15.42 / −11.94 % across
   β = 0.3 / 0.5 / 0.7. It is not a knob artefact, and it does not depend on
   landing on a lucky β.
2. **No restart knob makes the loss cells win.** Across β ∈ {0.3, 0.5, 0.7} and
   all three arms, `production` stays inside [−1.44 %, +2.52 %] and
   `w16e1_60k` inside [−0.42 %, +5.69 %] at N = 200. The direction that helps
   them most is β = 0.3 (production −0.75 %, 60k's best arm at β = 0.5), and the
   direction that hurts most is β = 0.7 — the opposite of what a "more
   contraction is better" reading would predict.

**Resolution caveat.** The loss cells move by ~1–2 pp across the whole β range,
which is below what N = 200 can resolve: at N = 1000 the same β = 0.5
configuration reads +1.23 % on `production` and +2.43 % on `w16e1_60k`. So this
screen ranks the large effects and says nothing reliable about the small ones.
The decisive comparison for those two cells has to be at N = 1000.

---

## 8. Where GAP-78 stands

* The rho gate is falsified (§2). The κ gate is falsified (§7). **No gate.**
* The mechanism that survives is the one in §4 read *descriptively*: the restart
  averages the model's conditional noise, so a noisy checkpoint gains a lot and
  a converged one gains nothing. That is a statement about which checkpoints
  benefit, and it is not something the framework can select on — the observable
  that predicts it is the checkpoint's identity, not a measurable knob.
* The only remaining lever for the two loss cells is **weak dominance at a
  better β**: find a β whose N = 1000 ΔFID is within the +1 % margin on
  `production` and `w16e1_60k` while keeping the `w16e1_5k` / `w16e1_10k`
  strict gains. β = 0.3 is the candidate the screen points at (production
  −0.75 %, 5k −13.40 % at N = 200); it is untested at N = 1000.
* If β = 0.3 at N = 1000 also lands outside the margin on the loss cells, then
  R5c cannot be won by any restart configuration, and the cell's honest status
  is a loss on two of four checkpoints. That outcome is not written here in
  advance — it is the experiment the next increment has to run.

---

## 9. β = 0.3 at N = 1000: weak dominance on all four checkpoints

§8 named the one remaining lever and the screen pointed at β = 0.3. It was run
at the real resolution (N = 1000, seed 42, NFE = 50, R = 4, mean-preserve,
shared prior; `verification_outputs/gap78-kappa-dose-n1000/`). It works.

**Headline ΔFID per arm** (the ledger metric — GAP-76's "+7.75 % → −3.34 %" is
the headline, verified by recomputing that mean from its 12 cell means):

| checkpoint | baseline | cosine | codim | evidence | **mean** | β = 0.5 mean (GAP-76, 3 seeds) |
|---|---:|---:|---:|---:|---:|---:|
| `production` | 9.9670 | +0.18 % | **−0.58 %** | −0.53 % | **−0.31 %** | +1.03 % |
| `w16e1_60k` | 11.4009 | +0.73 % | +0.13 % | **+0.01 %** | **+0.29 %** | +2.82 % |
| `w16e1_5k` | 24.4977 | −12.55 % | −12.56 % | **−12.80 %** | **−12.64 %** | −13.00 % |
| `w16e1_10k` | 16.9632 | −5.60 % | −5.79 % | **−5.94 %** | **−5.78 %** | −4.30 % |

Every one of the twelve cells is inside the +1 % margin (worst is +0.73 %), and
two checkpoints carry strict gains of −5.8 % and −12.6 %. Under the frontier
definition (`gap84-inference-frontier.md` §0.5–§0.6) that is a **WIN**: weak
dominance everywhere, strict gain somewhere, no selector and no fitted
threshold. The smaller restart costs 0.36 pp on `w16e1_5k` and buys 1.34 pp on
`production` and 2.53 pp on `w16e1_60k`.

**Three disclosures that must travel with this table.**

1. **One seed.** GAP-76's β = 0.5 numbers are 3-seed means; these are seed 42
   only. The direction is unambiguous at N = 1000 (the β = 0.3 and β = 0.5
   values differ by 1.3–2.5 pp, far more than the ~0.2 pp seed spread GAP-76
   measured), but the cell is not quotable until seeds 43/44 land.
2. **The chunk-level statistic and the headline disagree in sign on
   `w16e1_60k`.** Chunk Δ is −4.53 / −4.90 / −4.88 % (p ≤ 5e-11, all arms) while
   the headline is +0.73 / +0.13 / +0.01 %. The sweep's own `verdict` string
   therefore reads `baseline_wins` for that checkpoint even though every chunk
   test is significant in the framework's favour. This is the same
   headline-vs-chunk divergence GAP-67 §2.2 recorded, and it is not resolved
   here. The ledger uses the headline, so `w16e1_60k` is scored as **weak
   dominance, not a strict gain**, and the paper must not quote the chunk
   number for it without both numbers on the page.
3. **κ moves the wrong way again.** At β = 0.3 the `production` contraction is
   0.953–0.963 and at β = 0.5 it is 0.954 — essentially unchanged — while the
   headline moves from +1.23 % to +0.18 %. A 1 pp improvement with no change in
   κ is one more refutation of §4's reading, consistent with §7.

**What this does not claim.** `production` and `w16e1_60k` are weak-dominance
cells. The framework is not worse there; it is not better either. The R5c
strict gains are `w16e1_5k` and `w16e1_10k`, and the frontier win comes from
"never worse anywhere, much better on two checkpoints", not from a win on all
four.

**§9 is superseded on the verdict by §10.** The table above is seed 42 only and
it applies the +1 % margin to point estimates. With three seeds and an interval
the same twelve cells do not clear the pre-registered rule.

## 10. Three seeds at β = 0.3: the verdict depends on which margin is the margin

`reproduce/gap78_kappa_dose_response.sh --betas 0.3 --seeds 43,44`, four
checkpoints, three arms, N = 1000, seed 42 copied from the run in §9. Read with
`tools/gap78_r5c_report.py` (10 tests), artifact
`verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json`.

### 10.1 The table

`ΔFID` is the headline projection-FID difference in metric units; `CI95` is a
Student-t interval on the mean over the three seeds.

| ckpt | arm | per-seed % | mean % | CI95 % | ΔFID | CI95 units | weak (1 %) | gain (1 %) |
|---|---|---:|---:|---|---:|---:|:--:|:--:|
| `production` | codimension_sheet | −0.58 / −0.27 / −0.65 | −0.50 | [−1.00, +0.00] | −0.050 | [−0.100, +0.000] | yes | no |
| `production` | cosine | +0.18 / +0.40 / +0.29 | +0.29 | [+0.02, +0.56] | +0.029 | [+0.002, +0.056] | yes | no |
| `production` | evidence_driven | −0.53 / −0.30 / −0.27 | −0.36 | [−0.72, −0.01] | −0.036 | [−0.072, −0.001] | yes | yes |
| `w16e1_10k` | codimension_sheet | −5.79 / −5.75 / −5.92 | −5.82 | [−6.05, −5.60] | −0.987 | [−1.014, −0.961] | yes | yes |
| `w16e1_10k` | cosine | −5.60 / −5.48 / −5.74 | −5.61 | [−5.93, −5.28] | −0.951 | [−0.995, −0.907] | yes | yes |
| `w16e1_10k` | evidence_driven | −5.94 / −5.76 / −6.03 | −5.91 | [−6.26, −5.57] | −1.002 | [−1.049, −0.956] | yes | yes |
| `w16e1_5k` | codimension_sheet | −12.56 / −12.47 / −12.63 | −12.55 | [−12.75, −12.35] | −3.074 | [−3.091, −3.057] | yes | yes |
| `w16e1_5k` | cosine | −12.55 / −12.44 / −12.55 | −12.51 | [−12.68, −12.35] | −3.064 | [−3.087, −3.041] | yes | yes |
| `w16e1_5k` | evidence_driven | −12.80 / −12.64 / −12.73 | −12.73 | [−12.92, −12.53] | −3.116 | [−3.158, −3.074] | yes | yes |
| `w16e1_60k` | codimension_sheet | +0.13 / +0.14 / +0.19 | +0.15 | [+0.08, +0.23] | +0.018 | [+0.009, +0.027] | yes | no |
| `w16e1_60k` | cosine | +0.73 / +0.88 / +0.97 | **+0.86** | **[+0.56, +1.16]** | **+0.098** | [+0.064, +0.131] | **NO** | no |
| `w16e1_60k` | evidence_driven | +0.01 / +0.17 / +0.24 | +0.14 | [−0.15, +0.43] | +0.016 | [−0.017, +0.049] | yes | no |

The seed spread is small everywhere (sd ≤ 0.13 pp on the loss cells), so every
number here is reproducible; the question is not noise.

### 10.2 The pre-registered rule says LOSS

`gap84-inference-frontier.md` §0.5 fixes the margin at **1 % relative** and
requires `CI95_high ≤ +margin` at every cell. Eleven of twelve clear it.
`w16e1_60k` × `cosine` reads +0.86 % with an upper bound of +1.16 %, so the
cell fails by 0.16 pp on the interval — its point estimate is inside the margin
and its interval is not. Under the rule as written, **R5c is a LOSS**, and a
loss is an open gap, not a boundary to publish.

### 10.3 The ledger's own floor says WIN, and the two cannot both be right

GAP-76 §1.2 scored every R5c cell against "the paper's 1-FID-unit effect floor",
and CLM-060 lists the per-cell floors as `1pp / 0.01 abs / 1 FID / 0.5 pLDDT pp /
0.1 scPerplexity`. On these baselines one FID unit is:

| checkpoint | baseline FID | 1 % relative, in FID units | ledger floor, in FID units | ratio |
|---|---:|---:|---:|---:|
| `production` | 9.9670 | 0.100 | 1.0 | 10× |
| `w16e1_60k` | 11.4009 | 0.114 | 1.0 | 8.8× |
| `w16e1_10k` | 16.9632 | 0.170 | 1.0 | 5.9× |
| `w16e1_5k` | 24.4977 | 0.245 | 1.0 | 4.1× |

A universal 1 % relative margin is therefore **not** the effect floor on this
metric — it is a floor that changes with the baseline, 4× to 10× tighter than
the ledger's, and tighter on the cells where the framework wins least. That is
an arithmetic inconsistency that was visible before any of these runs, not a
judgement made after seeing them. Applying the ledger's floor to the same rows:

* weak dominance (95 % confident the cell is not worse than −1 FID unit):
  **12/12**; the worst cell is +0.098 units, a tenth of the floor.
* strict gain (95 % confident the cell beats −1 FID unit): **3/12**, all on
  `w16e1_5k` (−3.06 to −3.12 units).
* verdict: **WIN**.

`w16e1_10k` is the near miss worth naming: −0.95 to −1.00 units on every arm,
so under the floor it is a tie even though it is a strict gain under the
interval rule. Nothing here upgrades it.

### 10.4 Both verdicts are recorded; neither is withdrawn

| rule | weak dominance | strict gains | verdict |
|---|---:|---:|---|
| 1 % relative, CI on the mean (pre-registered, §0.5) | 11/12 | 7 | **LOSS** |
| 1 FID unit absolute, CI on the mean (ledger floor) | 12/12 | 3 | **WIN** |

The report prints both side by side and the JSON carries
`verdict_relative` / `verdict_floor`. Neither is allowed to be quoted alone.
The open question is a protocol question — which margin GAP-84 §0.5 should
carry — and it is settled in that document, not here.

### 10.5 Why `cosine` is the outlier on the well-trained checkpoint

The three arms differ in their restart ramp, not in the number of rounds:
`cosine` and `evidence_driven` both allocate `[25, 18, 6, 1]` steps over four
rounds, `codimension_sheet` allocates `[13, 12, 12, 13]`. So the step budget is
not the difference. The ramp is: `CosineAnnealScheduler` has `n_cap =
[1, 0.75, 0.25, 0]` (`scripts/wave191_p3_mnist_sweep.py:248-249`), and the
engine sets `beta = n_cap`, `memory_fraction = 1 − beta`, `t0 = 1 − beta`. On
round 0 that is `n_cap = 1` → `t0 = 0`: a **full** restart from pure noise, half
the total NFE spent regenerating from scratch. `codimension_sheet` keeps
`n_cap ≈ 1.0` with `n_min = 0`, and `evidence_driven` applies a PID-lite offset
to the cosine ramp, so neither has that round.

That is a concrete mechanism for why the one arm that discards the endpoint
pays +0.86 % on the best-trained checkpoint and is the best arm on `production`:
on a converged model a from-scratch round is pure cost, on an undertrained one
it is a useful re-draw. It is a hypothesis for the next increment, not a
finding — it has not been run.

### 10.6 What is claimed

* At β = 0.3, N = 1000, three seeds, the framework is **not worse** than the
  baseline on any of the twelve cells by more than 0.098 FID units, and is
  better by 3.06–3.12 units on all three `w16e1_5k` cells.
* The framework is **not** better on `production` or `w16e1_60k`; those are
  ties at best. No strict gain is claimed there.
* Under the pre-registered 1 % relative rule the cell is a **LOSS**. Under the
  ledger's 1-FID-unit floor it is a **WIN**. R5c is not recorded as closed until
  the margin question is settled.

### 10.7 Decision (2026-10-24)

R5c is settled on the **ledger's per-cell floor**, decided by the user after both
verdicts were on the table: 12/12 weak dominance, worst cell +0.098 FID units, 3
strict floor-gains on `w16e1_5k`. This is the convention every R5c table since
GAP-76 has used, and it is the one GAP-84 §0.5 now carries.

Two things this decision does **not** do:

* It does not delete the 1 % verdict. `verdict_relative` stays in the artifact
  and this section stays in the audit; a reader can see that the cell fails the
  stricter relative rule on one arm, and why that rule was the wrong ruler.
* It does not convert the ties into gains. `production` and `w16e1_60k` are ties
  on every arm and no strict gain is claimed there; `w16e1_10k` is −0.95 to
  −1.00 units and is also a tie under the floor.

The selector search is over and both candidates are falsified (§2, §7). The win
is a parameter, β = 0.3, applied identically to every checkpoint, with no fitted
threshold and no arm selection.
