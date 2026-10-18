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

_(filled after the sweep completes)_

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

_(filled after the sweep completes)_

---

## 5. Interpretation

_(filled after the sweep completes)_

---

## 6. Verification

| Gate | Result |
|---|---|
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30/30 PASS |
| `python3 -m pytest tests/test_tools/test_run_sota_cifar_experiment.py -q` | 16 passed, 1 skipped (Windows venv path) |
| `ruff check` (touched files) | 0 findings |

---

## 7. Unresolved / noted

_(filled after the sweep completes)_
