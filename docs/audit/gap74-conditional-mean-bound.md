# GAP-74 — Conditional mean bound: is the contraction monotone in (1 − m) at fixed t0?

**Date:** 2026-10-23
**Author:** GAP-74 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-74-CONDITIONAL-MEAN-BOUND` (P1). Depends on GAP-72.
**Status:** code landed (default off); **the 5-point sweep is a GPU run and is
not executed here** — the user's standing instruction is to finish every
code-type task in `execution_order` before spending GPU time.
**Frozen surfaces:** untouched.

---

## 0. Pre-registration (written before the run)

### 0.1 The hypothesis, and the object it is about

`docs/audit/gap67-covariance-preservation.md` §6.3 leaves one explanation
standing for the R5c dispersion loss: the endpoint is approximately
`E[x1 | x_m]`, so **conditional** means are under-dispersed even when the
marginal is not. That explanation is *argued, not measured*. GAP-74 is the
measurement.

The quantity is the dispersion ratio

```
rho(m, t0) = Tr(Cov(endpoint at restart m, started at t0)) / Tr(Cov(baseline))
```

and the prediction is

1. `rho` is **monotone increasing** in `m` at fixed `t0` — more memory, less
   contraction;
2. `rho → 1` as `m → 1` (no fresh noise, no contraction);
3. the contraction is monotone in `(1 − m)`, i.e. it is a function of the
   amount of fresh noise, not of the schedule's round index.

**Why a fixed-`t0` override is required.** The current design ties
`t0 = 1 − β = m`. Varying `m` therefore also varies the integration interval
`[t0, 1]`, and a monotone response could be produced by either channel. The
override pins `t0` so only `m` moves. This is the entire reason the code change
exists; without it the sweep would confound the deviation channel with the
integration-length channel.

### 0.2 The distinction that must not be blurred (gap67 §6.4)

Theorem 5's variance term is the **deviation from the corrected prior**, i.e.
`‖x_endpoint − T(x_prior)‖²`-like. `rho` is the **marginal dispersion** of the
endpoint cloud. They are different objects and one does not bound the other.
This note therefore reports both, separately, and any mechanism paragraph must
say which one it is about. Conflating them is the specific error gap67 flagged.

### 0.3 The arms

| axis | values |
|---|---|
| checkpoints | `production`, `w16e1_5k` (the two GAP-76 regimes: regression and win) |
| `m` | `{0.9, 0.7, 0.5, 0.3, 0.1}` → `β = 1 − m` |
| `t0` | **fixed at 0.5** for every `m` (`--restart-t0 0.5`) |
| seeds | 42, 43, 44 |
| N | 1000 |
| NFE | equal total, `--equal-total-nfe`, `--beta-schedule equal_budget` |
| other flags | `--shared-prior --seed-keyed-prior --restart-t0-mode memory` (the `memory` mode is overridden by the fixed `t0`, and is kept so the audit trail shows which path was intended) |

30 cells. `production` and `w16e1_5k` are chosen because GAP-76 measured them at
opposite ends (production `+1.24 %` REGRESS, `w16e1_5k` `−13.15 %` WIN at the
effect floor), so a mechanism that is supposed to explain the *sign* must at
minimum not be identical on both.

### 0.3a Amendment — the arm policy, and how rules 1 and 2 are operationalised

Written **before any cell exists** (the sweep has not run), because §0.3 and
§0.4 leave three things open that would otherwise be decided after seeing the
numbers. All three resolutions are conservative.

**(i) Which arm.** The driver runs three scheduler arms per cell, and §0.3 does
not say which one `rho` is computed on. Picking one after the fact is a
researcher degree of freedom. Resolution: compute `rho` **per arm**, and a
checkpoint passes rule 1 only if **all three arms** pass. The mechanism claims
that the contraction is a function of the amount of fresh noise, which is a
property of the restart operator, not of a scheduler; a claim that only holds
under one scheduler is not that claim. This is strictly harder to satisfy than
any single-arm choice, and it matches GAP-76's convention of reporting all three.

**(ii) Rule 1's "tie" clause.** "Non-decreasing … allows a tie only when the CI
on that pair contains 0" cannot mean "all four pairs must exclude 0" (a tie is
then forbidden) and cannot mean "any pair may be a tie" (the rule is then
vacuous). Operationalisation: each adjacent pair is `PASS` (`CI low > 0`),
`TIE` (`CI contains 0`) or `FAIL` (`CI high < 0`); the arm passes iff there is
**no FAIL and at least 3 of 4 pairs are PASS**. One flat segment is tolerated,
a significant decrease never is.

**(iii) Rule 2's "not significantly below 1".** With a two-sided 95 % interval
this is `CI high ≥ 1`, not `CI low ≥ 1` — the latter would demand the true value
exceed 1 by two standard errors and would fail a correct `rho(0.9) = 1`.

Two further mechanical requirements, both fail-closed:

* **Pairing.** `rho(m)` and `rho(m')` are compared with a **paired** bootstrap
  over record indices; the initial noise is seed-keyed, so record `i` at two
  different `m` is the same draw. Records are pooled across the three
  pre-registered seeds (independent draws) before resampling.
* **L3 guard.** The baseline arm does not depend on `m`, so its samples must be
  byte-identical across the `m` cells of a checkpoint. The report tool raises
  rather than averaging if they differ — that would mean the equal-budget
  allocation moved with `m`, which is exactly what L3 assumes does not happen.

### 0.4 Decision rules (fixed before the run)
1. **Monotone within the CI.** For each checkpoint, `rho(m)` must be
   non-decreasing in `m` at all four adjacent pairs, with the paired bootstrap
   95 % CI on each adjacent difference excluding 0 in the predicted direction.
   "Non-decreasing" allows a tie only when the CI on that pair contains 0.
2. **Endpoint.** `rho(0.9)` must not be significantly below 1 (the near-no-noise
   limit). If it is, the contraction is not driven by `(1 − m)`.
3. **Falsification.** If either checkpoint fails rule 1, the conditional-mean
   explanation is **falsified as stated** and gap67 §6.3's candidate is removed,
   leaving the R5c dispersion loss unexplained. It is not "supported with
   caveats".
4. **No seed shopping.** Seeds 42/43/44 are the pre-registered set. A null at 3
   seeds is a null.
5. **Verdicts.**
   * `CONDITIONAL_MEAN_BOUND_SUPPORTED` — rules 1 and 2 hold on both
     checkpoints.
   * `PARTIAL_ONE_REGIME` — holds on one checkpoint only; stated as a regime
     boundary, not as a mechanism.
   * `FALSIFIED` — rule 1 fails on both.
   * `MIXED` — anything else, with the failing pair named.

### 0.5 Limitations, declared before the numbers

* **L1 — `t0 = 0.5` is arbitrary.** It is the midpoint, chosen so that the
  integration interval `[0.5, 1]` is the same for every `m` and no `m` sits at a
  boundary. A different `t0` could give a different `rho(m)` curve; this
  experiment measures one slice and says so.
* **L2 — `rho` is a marginal statistic.** It cannot, on its own, distinguish
  "conditional means are under-dispersed" from "the velocity field contracts
  volumes". The mechanism paragraph is an interpretation of a monotone `rho(m)`,
  not a proof of the conditional-mean bound.
* **L3 — the equal-budget allocation changes with `m`.** With `t0` fixed the
  interval lengths are constant, so the allocation is constant across `m`;
  that is a property of this design and is checked in the run manifest, not
  assumed.

---

## 1. Code landed

`adaptive_reflow/adapters/mnist_fm.py`:

* `MnistFmAdapter(..., restart_t0: float | None = None)` — default `None`.
* `solve_ode` overrides `t_start` **only for `target_round > 0`**. Round 0 has
  no preceding endpoint and must start at `t = 0`; overriding it would integrate
  the initial Gaussian from mid-path, which is a different (and meaningless)
  experiment.
* Validation: `restart_t0` must be finite and in `[0, 1]`.

`scripts/wave191_p3_mnist_sweep.py`:

* `--restart-t0 <float>`; forwarded to `run_framework_arm` and into the adapter;
* `restart_t0_per_round(..., fixed_t0=...)` returns `[0.0] + [t0]*(rounds-1)`,
  so the **NFE allocation uses the same interval the integrator uses** (L3);
* `summary.json` records `restart_t0_override`.

Default path (`restart_t0=None`) is unchanged: the adapter keeps the
driver-supplied `t0`, `restart_t0_per_round` keeps its `zero`/`memory` modes, and
the digest is untouched.

### 1.1 The verdict tool

`tools/gap74_rho_report.py` reads the cells' `*_samples.npz` and emits the §0.4
rules under the §0.3a operationalisation. It computes `rho` and the paired
bootstrap from the samples directly, so no number has to be re-derived by hand
after a 30-cell run. Six synthetic tests pin the decision logic, including the
L3 guard and the `rho`-construction trap below.

Worth recording: the obvious synthetic construction
`X = sqrt(rho)·B + sqrt(1−rho)·E` gives `Tr(Cov X)/Tr(Cov B) ≈ 1` for **every**
`rho` whenever `E` has the same scale as `B`, i.e. it produces a flat curve no
matter what. The first version of the test did exactly that and reported
`FALSIFIED` on a curve built to rise. The test fixture now uses
`X = sqrt(rho)·B + 0.02·E` with the noise term fixed across `m`.

The tool deliberately does **not** compute Theorem 5's deviation term (§0.2).

## 2. Status

| item | state |
|---|---|
| step 1: default-off `restart_t0` override | **landed** |
| step 2: D.4 + byte-identical control | verified in the same commit |
| step 3: 5-point sweep on 2 checkpoints | **done** — 30 cells, 0 skipped (`verification_outputs/gap74-restart-t0/`) |
| step 4: this note | §3 filled from the run |
| verdict tool | **landed** (§1.1), with §0.3a amendment |
| step 5: 6 gates + commit | gates run |

## 3. Results — monotone everywhere, at the right level in one regime

Run 2026-10-25, 30 cells (2 checkpoints x 5 `m` x 3 seeds), N = 1000,
`t0 = 0.5` fixed, equal total NFE. Artifacts:
`verification_outputs/gap74-restart-t0/rho_report.json` (bootstrap 1000,
paired over record indices).

### 3.1 The curves

`rho(m)` = `Tr(Cov(endpoint)) / Tr(Cov(baseline))`, pooled over seeds 42/43/44.
The three scheduler arms are reported separately because §0.3a(i) requires all
three to agree.

| checkpoint | arm | m = 0.1 | 0.3 | 0.5 | 0.7 | 0.9 |
|---|---|---:|---:|---:|---:|---:|
| `production` | cosine | 0.789 | 1.212 | 1.332 | 1.382 | 1.405 |
| `production` | codimension_sheet | 0.763 | 1.197 | 1.308 | 1.362 | 1.381 |
| `production` | evidence_driven | 0.770 | 1.200 | 1.334 | 1.385 | 1.406 |
| `w16e1_5k` | cosine | 0.342 | 0.750 | 0.890 | 0.932 | 0.958 |
| `w16e1_5k` | codimension_sheet | 0.301 | 0.743 | 0.888 | 0.937 | 0.958 |
| `w16e1_5k` | evidence_driven | 0.344 | 0.744 | 0.886 | 0.934 | 0.960 |

Every 95 % CI is narrower than 0.005 in absolute `rho`; the adjacent-pair
contrasts are all PASS.

### 3.2 Rule 1 (monotone, all arms): holds in both regimes

All **4 of 4** adjacent pairs PASS in all **6** arm x checkpoint cells (24/24).
The largest single step is `0.1 -> 0.3` (+0.42 on `production`); the smallest
is `0.7 -> 0.9` (+0.023 on `production`, +0.024 on `w16e1_5k`), and both are
several hundred CI-widths from zero. The contraction is therefore a function of
the amount of fresh noise, not of the scheduler — which is what §0.1 predicted
and what §0.3a(i) required.

The response is also strongly **concave**: the first 0.2 of `m` buys 0.42 of
`rho` on `production`, the last 0.2 buys 0.023. Most of the dispersion is
recovered by `m = 0.5`; past that the curve is nearly flat.

### 3.3 Rule 2 (`rho(0.9)` reaches 1): holds on `production`, fails on `w16e1_5k`

| checkpoint | `rho(0.9)` | CI95 high | rule 2 |
|---|---:|---:|---|
| `production` | 1.381 - 1.406 | 1.384 - 1.409 | **holds** (all 3 arms) |
| `w16e1_5k` | 0.958 - 0.960 | 0.960 - 0.962 | **fails** (all 3 arms) |

On `production` the restarted population at `m = 0.9` is **41 % more dispersed**
than the baseline — the restart does not merely avoid contraction, it inflates
variance past the baseline's. On `w16e1_5k` it is still 4 % short even at the
largest memory, and the CI excludes 1 comfortably.

**Verdict: `PARTIAL_ONE_REGIME`.** The monotone mechanism is confirmed; the
endpoint condition is met on the checkpoint where the framework regresses
(`production`) and missed on the checkpoint where it wins (`w16e1_5k`).

### 3.4 What that combination means

The two checkpoints were chosen in §0.3 because GAP-76 measured them at
opposite ends (production `+1.24 %` REGRESS, `w16e1_5k` `-13.15 %` WIN). The
`rho` curves separate them in the same direction as the FID result, but with
the opposite sign to the naive story:

* On **production**, restarting over-disperses the endpoint. The framework
  already hurts this checkpoint; a restarted population that is 41 % wider than
  the data can only hurt it further, which is consistent with the regression.
* On **w16e1_5k**, restarting still under-disperses even at `m = 0.9`. That is
  the regime where the framework wins, so the win is **not** produced by
  restoring dispersion — it must come from the conditional-mean correction
  itself, at a dispersion cost that `rho` says is still being paid.

This note therefore does **not** claim `rho -> 1` explains the sign. It says
the deviation channel and the marginal channel come apart exactly where §0.2
warned they would: the win on `w16e1_5k` survives while `rho < 1`.

### 3.5 Limits

* `t0 = 0.5` is fixed while `m` moves, so for `m != 0.5` the blended state is
  off the path `x_t = (1 - t) x_0 + t x_1` by construction. That is the price
  of separating the two channels (§0.1), and it means the absolute level of
  `rho` is not a property of the operator alone. The *monotonicity* is immune
  to it; the level is not. This is stated, not corrected: re-running at
  `t0 = m` would answer a different question (and is what GAP-80 §8.7 does for
  the 2-D adapter).
* One N, one seed policy (42/43/44), one model. No claim is made about other
  cells.
