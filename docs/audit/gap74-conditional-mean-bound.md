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

## 2. Status

| item | state |
|---|---|
| step 1: default-off `restart_t0` override | **landed** |
| step 2: D.4 + byte-identical control | verified in the same commit |
| step 3: 5-point sweep on 2 checkpoints | **not run** (GPU deferred) |
| step 4: this note | §0 written before the run; §3 empty |
| step 5: 6 gates + commit | gates run |

## 3. Results

_None. Nothing in this section may be filled in from an earlier run; the
`t0 = 1 − β` design cannot produce a fixed-`t0` reading._
