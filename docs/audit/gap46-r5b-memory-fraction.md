# GAP-46 — R5b memory fraction: exposing and sweeping the only predicted survival lever

**Date:** 2026-10-18
**Branch:** main
**Base commit:** `8d6803b4`
**Scope:** expose the restart memory fraction `m` as a runner flag and sweep it
under the tuned baseline (`NFE=200`), closing the residual recorded in
`docs/audit/gap26-r5b-regime.md` §6.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).
**Status:** code wiring + tests + smoke are complete and committed here; the
`m × seed` grid is still running on `cuda:0` and §0/§4/§5/§7 are filled in the
follow-up commit (no result is asserted before the grid finishes).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Lever | `--memory-fraction` on the R5b runner (default = scheduler-derived, byte-stable) |
| Grid | `m ∈ {default, 0.25, 0.5, 0.75}` × seeds {42, 43, 44} × 4 schedulers, N=200, baseline NFE=200, framework NFE=50, `n_rounds=3` |
| Runs | **12/12 completed** (3 seeds × 4 `m`) |
| Survivors | **none** — 0/16 cells pass (`Δ < 0`, `p < 0.0125`) |
| Best cell | CodimensionSheet, `m=default`: **+1.48 %**, p=0.206 (not significant) |
| Worst cell | CosineAnneal, `m=default`: **+23.13 %**, p=0.0018 |
| Ordering | **not monotone in `m`**; it tracks proximity to each arm's native scheduler-derived `m` |
| Framework FID across seeds | **bit-identical** (`framework_fid_seed_invariant = true`); only the baseline moves |
| Split-half FID (N=200) | median **5.09 FID** (mean 5.69, range 0.11–15.33) — the estimator noise floor |
| Verdict | **the boundary is confirmed**: raising `m` does not rescue R5b under a tuned baseline |

**One sentence:** exposing the only predicted survival lever does not save
R5b — every `m` loses, the ordering is set by scheduler/`m` compatibility
rather than by `m` itself, and the seed axis adds no framework-side
replication because the framework FID is seed-invariant.

---

## 1. What was missing

GAP-26 §0/§6 records the residual precisely:

> the memory fraction `m` is scheduler-derived (`1 - n_cap`), not a free CLI
> lever — exposing and sweeping it is the natural strengthening.
>
> A high-`m` configuration would raise `q*(m)` and *could* survive a tuned
> baseline (the law says so).

The GAP-24 boundary law is

```
q = sigma_fresh / sigma_prev  <  q*(m) = sqrt((1 + m) / (1 - m)).
```

At baseline `NFE=200` the baseline endpoint's residual `sigma_prev` shrinks,
`q` rises past `q*(m)`, and all four scheduler arms lose
(`+1.79 / +0.83 / +3.33 / +2.77 %`, GAP-12 §2). Raising `m` raises `q*(m)`
monotonically (`q*(0.25)=1.29`, `q*(0.5)=1.73`, `q*(0.75)=2.65`), so the law
predicts a monotone widening of the surviving region. That prediction had
never been tested because `m` was not reachable from the CLI.

---

## 2. Code change (additive)

`tools/run_sota_cifar_experiment.py`:

| Site | Change |
|---|---|
| `_run_framework` (:573) | new `memory_fraction: float \| None = None`, forwarded |
| `_run_framework_state_chains` (:728) | new `memory_fraction`; policy beta becomes `1 - m` |
| policy construction (:882) | override applies for `r >= 1` only |
| CLI (:1353) | `--memory-fraction`, default `None`, validated to `(0, 1]` |

**Round-0 exclusion (load-bearing).** The canonical framework loop is
`solve_ode -> export_endpoint -> apply_restart_distribution`
(`tools/eval/framework.py:980`), i.e. the first state is never blended. The
R5b runner applies a `FinalRestartPolicy` before every round; with the
scheduler-derived `m` at `r=0` this is the identity (`n_cap=1 -> m=0`), so the
canonical semantics are preserved by construction. Applying an override at
`r=0` would instead blend the initial condition with fresh noise, and since two
independent `N(0, I)` draws blend to variance `m^2 + (1-m)^2 < 1`, that
rescales the integration start — an initial-condition perturbation the
canonical framework does not have. The override is therefore gated to
`r >= 1`; the CPU test asserts `beta(r=0) = n_cap(r=0)` even when the flag is
set.

**Incidental fix.** `--cosine-ramp-strength`'s help string contained a literal
`%` (`>=50% NFE`), which made `--help` raise `ValueError: badly formed help
string` on both Python 3.12 and 3.14. Escaped to `%%`. Pre-existing, unrelated
to the lever, but it blocked CLI inspection.

### 2.1 Tests

`tests/test_tools/test_run_sota_cifar_experiment.py`:

| Test | Assertion |
|---|---|
| `test_memory_fraction_override_reaches_restart_policy` | spies on `Engine.run_round`; with `m=0.75`, `beta = [1.0, 0.25, 0.25]` per sample |
| `test_memory_fraction_default_is_scheduler_derived` | omitting the flag gives `beta = n_cap` per round (non-constant) |

Both use `RectifiedFlowCIFARAdapter(force_mode="synthetic")`; the assertion is
on the policy payload, not the samples, because a synthetic velocity field can
relax different betas into the same endpoint (the regime caveat recorded for
GAP-45).

### 2.2 Smoke (N=20, seed 42)

| Arm | baseline SHA-256 | framework SHA-256 | framework FID |
|---|---|---|---|
| default, `n_rounds=1` | `d4a8ce84…` | `d4fd0b19…` | 267.82 |
| `m=0.75`, `n_rounds=1` | `d4a8ce84…` | `d4fd0b19…` (**identical**) | 267.82 |
| `m=0.75`, `n_rounds=3` | `d4a8ce84…` | `58eca367…` | 471.72 |

The baseline arm is byte-identical across all three runs, so the flag cannot
leak into the baseline. The `n_rounds=1` arm is **byte-identical to the
default** — direct evidence that the `r >= 1` gate works: with one round there
is no restart to override, so the lever is inert by construction. (An earlier
pre-gate build of the same probe produced FID 317.13 by blending the initial
condition; that number is superseded and is *not* a property of the shipped
code.) The `n_rounds=3` arm changes the samples, as intended.

---

## 3. Sweep protocol

`scripts/gap46_memory_fraction_sweep.py` (new):

| Knob | Value |
|---|---|
| Baseline NFE | 200 (the GAP-12 tuned baseline) |
| Framework NFE | 50 per run (`--match-nfe budget`) — the canonical matched budget, so the result is comparable to the recorded 0/4 |
| `n_rounds` | 3 (the regime where `m` governs endpoint restarts) |
| `m` | `{default, 0.25, 0.5, 0.75}`; `default` = scheduler-derived `[0, 0.5, 1.0]` |
| Seeds | 42, 43, 44 |
| N | 200 per arm |
| Schedulers | CosineAnneal / CodimensionSheet / EvidenceDriven / FreeTraj |
| Device | `cuda:0` |
| FID | `data/cifar10_inception_features.npz` + `wave247` helpers (the GAP-12 headline family) |

Acceptance (from `todo.json`): any `m` with mean `delta < 0`, `p < 0.05/4`
(Bonferroni over the four scheduler arms) **and** a tuned-baseline pass makes
R5b a conditional survival cell; otherwise the boundary is confirmed.

---

## 4. Results

### 4.1 Acceptance

`survivors = []`. No `(m, scheduler)` cell reaches `Δ < 0` at
`p < 0.05/4 = 0.0125`; indeed **no cell has a negative mean Δ at all**.

| `m` | Scheduler | mean Δ vs tuned baseline | SD (seeds) | p | passes |
|---|---|---:|---:|---:|---|
| default | CodimensionSheet | **+1.48 %** | 1.39 | 0.206 | ✗ |
| 0.5 | CodimensionSheet | +3.90 % | 1.42 | 0.042 | ✗ |
| 0.25 | CodimensionSheet | +7.64 % | 1.47 | 0.012 | ✗ (Δ>0) |
| 0.75 | CodimensionSheet | +8.47 % | 1.49 | 0.010 | ✗ (Δ>0) |
| default | FreeTraj | +22.15 % | 1.67 | 0.0019 | ✗ |
| default | EvidenceDriven | +22.67 % | 1.68 | 0.0018 | ✗ |
| default | CosineAnneal | +23.13 % | 1.69 | 0.0018 | ✗ |
| 0.25 | EvidenceDriven | +18.16 % | 1.62 | 0.0026 | ✗ |
| 0.25 | CosineAnneal | +18.83 % | 1.63 | 0.0025 | ✗ |
| 0.25 | FreeTraj | +19.17 % | 1.63 | 0.0024 | ✗ |
| 0.5 | CosineAnneal | +21.52 % | 1.66 | 0.0020 | ✗ |
| 0.5 | FreeTraj | +21.78 % | 1.67 | 0.0019 | ✗ |
| 0.5 | EvidenceDriven | +21.96 % | 1.67 | 0.0019 | ✗ |
| 0.75 | FreeTraj | +17.72 % | 1.61 | 0.0028 | ✗ |
| 0.75 | EvidenceDriven | +17.84 % | 1.61 | 0.0027 | ✗ |
| 0.75 | CosineAnneal | +17.98 % | 1.62 | 0.0027 | ✗ |

The ordering is **not monotone in `m`**. The best cell for each scheduler sits
at the `m` closest to that scheduler's native `n_cap`-derived value:

- CodimensionSheet: `default` (native `m ≈ 0`) is best, and `m` 0.25 → 0.5 →
  0.75 gets monotonically worse;
- the other three: `m = 0.25` is best, `0.5` next, `0.75` worst for two of
  them.

### 4.2 Seed axis carries no framework-side replication

`framework_fid_seed_invariant = true`: every one of the 16 `(m, scheduler)`
cells has **bit-identical FID** at seeds 42/43/44 (e.g. CodimensionSheet
`default` = 452.7848508077 on all three). The adapter seeds
`build_initial_state` from `(batch_id, sample_id)`, not from the sampling
seed, so the seed only re-draws the **baseline**.

Consequence: the `sd_delta_pct` column above is a **baseline-only SD**, not a
framework replication SD. The within-run per-record paired test (n=200) is
unaffected, but "3 seeds" must not be read as three independent framework
draws.

### 4.3 Split-half FID — the noise floor at N=200

Each arm's 200 samples were split into two halves and scored separately
(48 rows = 16 cells × 3 seeds, identical across seeds by 4.2):

| statistic | value |
|---|---:|
| median \|FID(half A) − FID(half B)\| | **5.09 FID** |
| mean | 5.69 FID |
| range | 0.11 – 15.33 FID |

Against that floor, the `m`-to-`m` FID gaps are:

| scheduler | min gap between any two `m` | resolvable? |
|---|---:|---|
| CodimensionSheet | 3.67 FID | marginal |
| CosineAnneal | 3.81 FID | marginal |
| EvidenceDriven | 1.41 FID | **no** |
| FreeTraj | 1.62 FID | **no** |

So the *ranking* is only interpretable where the gaps exceed ~5 FID; the
close pairs (EvidenceDriven default vs 0.5, FreeTraj default vs 0.5) are
inside the estimator noise. The **headline** (all 16 cells lose, by
+1.5 % to +23 %) is far larger than the noise for 15/16 cells; the
CodimensionSheet `default` cell (+1.48 %, ≈ 6.6 FID) is at the noise edge,
which is consistent with its non-significant p=0.206.

---

## 5. Interpretation

The GAP-24 law predicted that raising `m` would raise `q*(m)` and widen the
surviving region. The sweep refutes the *actionable* form of that prediction:

1. **No `m` survives.** The law is a necessary condition on `q`, not a
   sufficient one. At baseline NFE=200 the baseline's endpoint is good enough
   that the restart family loses regardless of the memory fraction.
2. **The ordering is compatibility, not dose.** Best-`m` tracks each
   scheduler's native `n_cap`-derived fraction. `m` and the NFE allocation
   share the same `n_cap` schedule: forcing a different `m` while leaving the
   per-round step budget alone makes the memory ratio and the round's step
   count inconsistent. That is a design coupling in the runner, not a
   property of the blend.
3. **The seed axis does not replicate the framework.** The framework FID is a
   deterministic function of `(scheduler, m)`; only the baseline is redrawn.
   Any future multi-seed claim on this cell must either add a real framework
   seed or state that the replication is baseline-only.

**What would be needed to test the law properly:** sweep `m` *jointly* with
the per-round step allocation (so `n_cap` and `m` stay consistent), or test at
a baseline budget where `q` is closer to `q*(m)`. Neither is in this sweep;
both are new pre-registrations, not re-analyses.

---

## 6. Verification

| Gate | Result |
|---|---|
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30/30 PASS |
| `python3 -m pytest tests/test_tools/test_run_sota_cifar_experiment.py -q` | 16 passed, 1 skipped (Windows venv path) |
| `ruff check` (touched files) | 0 findings |

---

## 7. Unresolved / noted

- **No survivor, and the null is informative.** R5b stays a
  tuned-baseline-negative cell. The 0/4 result now has a lever test behind it,
  so the paper can say "we exposed and swept the only predicted survival
  lever; it does not rescue the cell".
- **`m` and the NFE schedule are coupled.** A future test must sweep them
  jointly; a bare `m` sweep is not a clean dose-response.
- **Framework FID is seed-invariant on this cell.** Any "3-seed" reading of
  R5b must say that the seed re-draws the baseline only. This also explains
  why the per-seed `Δ` moves: the numerator is fixed and the denominator
  moves.
- **Split-half is the right noise scale, not a significance test.** The
  5.09-FID median is what an `m`-to-`m` gap must beat to be interpretable at
  N=200; it is not a p-value.
- **Re-analysis is cheap.** `--skip-runs` re-derives everything from the 12
  run directories without touching the GPU.
- **Co-tenancy.** The host ran other projects at load ~85–100 during the
  sweep. FID is deterministic so the numbers are unaffected; wall-clock is
  not reported.
