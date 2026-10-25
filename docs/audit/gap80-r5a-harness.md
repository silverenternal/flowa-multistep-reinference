# GAP-80 — R5a is scored on a path that never restarts

**Date:** 2026-10-25
**Author:** GAP-80 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-80-R5A-2D-WIN` (P2). This document replaces the
gap's inherited design hypothesis with two measured facts about the harness.
**Frozen surfaces:** untouched.

---

## 0. What the gap assumed, and what is actually true

`todo.json` said: R5a is a TIE, W2 is mode-dominated, and the lever is to make
the restart act on the **mode assignment** rather than on within-mode
coordinates.

Three measurements below, in the order they were made:

1. §1 — the mode lever's ceiling is **0.0034 W2**, one third of the 0.01
   effect floor. The inherited hypothesis cannot win the cell even if
   implemented perfectly.
2. §2 — the R5a framework arm **never dispatches a restart**. The runner that
   scores the cell re-samples the same generator each round.
3. §3 — the restart's fresh component is **record-invariant**, so the blend
   contracts a population instead of resampling it.

§4 states what the existing TIE therefore means, §5 the fix and why it needs a
gate, §6 what this document does not claim.

---

## 1. The mode lever's ceiling: 0.0034 W2 (measured before any code)

Two moons: component A is the upper half-circle, component B the lower one
shifted by `(1, -0.5)`, both with `TWO_MOONS_NOISE = 0.08`.

Closed-form quantities (`scipy.stats.wasserstein_distance` per axis, combined
in quadrature exactly as `tools/run_sota_2d_experiment._wasserstein_2d` does):

| quantity | value |
|---|---:|
| `W2(A_moon, B_moon)` | 2.037 |
| `W2(A_moon, target)` | 1.019 |
| `W2(B_moon, target)` | 1.019 |
| `W2` sampling floor, N = 1000 iid vs a 400k reference | 0.0349 (sd 0.0117) |
| `W2` with modes **perfectly** balanced, same within-mode draws | 0.0315 (sd 0.0076) |
| paired drop from perfect balance | **0.0034** (sd 0.0119) |

A mode-proportion error `eps` costs `~2.04 * eps` in W2 (measured at
`eps in {0.0025, 0.005, 0.01, 0.02}` → 0.0060 / 0.0095 / 0.0184 / 0.0435), so
the linearised slope is 2.04 — but the *achievable* gain is much smaller than
`2.04 * eps`, because W2 can reallocate mass within each moon and therefore
absorbs most of a count imbalance. Perfect mode balance is worth **0.0034**.

The R5a acceptance is `|delta| > 0.01` with a CI excluding 0. A lever whose
best case is 0.0034 cannot clear it. **The inherited design hypothesis is
falsified by arithmetic, before any code.** This is the same shape of result as
`docs/audit/gap79-r1-family-lever.md` §1.

---

## 2. F1 — the scored path never restarts

`verification_outputs/wave216-p2-r5a-extended.csv` is produced by
`scripts/wave216_p2_r5a_runner.py` → `tools/run_sota_2d_experiment._per_target_runs`
→ `_drive_batched` → `BatchedTrajectoryRunner`
(`adaptive_reflow/algorithm/runner/batched_runner.py:730`).

The runner's round loop (`batched_runner.py:929-960`) calls
`adapter.generate_trajectory(seed=...)` once per round.
`TwoDimFMAdapter.generate_trajectory`
(`adaptive_reflow/adapters/twodim_fm.py:1432`) draws a **fresh**
`x0 ~ N(0, I_2)` for every endpoint on every call. There is no
`apply_restart_distribution` call anywhere in the batched runner — grep of the
module returns only docstrings and the `should_skip_restart_small_sigma`
helper.

Measured directly (3 rounds, counting subclass):

```
rounds: 3
apply_restart_distribution calls: []
round n_cap: [1.0, 0.5, 0.0]
```

The schedule is live (`n_cap` varies), the restart is not. So the "framework"
arm is **the baseline generator sampled five times with different seeds**, and
the reported W2 is the mean over those five independent batches.

### 2.1 The existing numbers agree with that reading

If both arms are the same generator, the paired per-seed difference must be
pure sampling noise. Its scale is known from §1: the W2 of a 1000-sample iid
draw has sd **0.0117**. The observed `diff_sd` over the canonical 10 seeds is
**0.0107** (`verification_outputs/wave351-r5a-n10/r5a_n10_paired.json`).

The two agree to 9 %. That is the quantitative signature of "same generator,
different seeds", and it is the reason the cell has been stuck at TIE under
every aggregation convention: there is no mechanism to detect.

---

## 3. F2 — the fresh restart draw is record-invariant

`TwoDimFMAdapter.apply_restart_distribution`
(`twodim_fm.py:930-1000`) computes

```
restart_seed = sha256(repr((policy.policy_hash, next_round)))[:8]
fresh_x0     = default_rng(restart_seed).standard_normal(2)
```

`policy_hash` is built by `tools/eval/framework._make_framework_policy`
(`tools/eval/framework.py:382-714`) from `(target_round, seed, channel names,
beta)` — **the record is not an input**. Every record in a population therefore
draws the *same* fresh point at a given round.

Measured at `m = 0` (where the blend is exactly the fresh draw):

```
x0 per record (m=0):
   [-0.11969946  1.49997672]
   [-0.11969946  1.49997672]
   [-0.11969946  1.49997672]
all identical: True
```

At `m = 0.5` the population's spread is `m` × the prior's, not 1 × the prior's
(pinned in `tests/test_gap80_batched_restart.py`). For a population metric this
is a mechanical defect: the blend `m * prior_i + (1 - m) * fresh_common`
**contracts** the sample and adds a common offset. It cannot improve W2, and at
small `m` it would collapse the population toward a single point.

The same seed derivation exists in `LineageFlowAdapter.apply_restart_distribution`
(`adaptive_reflow/adapters/lineageflow.py:2259-2265`), so the defect is shared.
It is *masked* in R1 because `m` stays large there and each record's own prior
trajectory carries the diversity — which is exactly why R1 works while a
population metric at small `m` would not.

---

## 4. What the existing R5a TIE means

**It is not evidence about the restart.** The cell compares the same generator
against itself with different seeds; the TIE says the harness is unbiased
(diff mean 0 within noise), which is a useful sanity check and nothing more.

It is also **not** a statement that the framework cannot win R5a. Nothing in
this document measures a restarted population on this cell, because the harness
never built one.

Two things follow:

1. The inherited lever (mode assignment) is dead on arithmetic (§1).
2. The first measurement that has to exist is a **restarted** R5a arm (§5).
   Until it exists, the cell is unmeasured rather than negative.

---

## 5. The fix, and why it needs a gate

Two independent changes, both opt-in so no existing byte-stable number moves:

**(a) Record-scoped restart seed.** Add the record identity to the restart seed
blob, e.g.

```
restart_seed = sha256(repr((policy_hash, next_round, batch_id, sample_id)))
```

behind an adapter flag (default off). This is what makes a restart a
*resampling* of the population instead of a contraction. It changes every
downstream byte when enabled, so R1 / R3 / R6 keep the flag off and their
published numbers stay reproducible.

**(b) A restart-capable R5a arm.** The batched runner has no condition delta and
therefore cannot chain rounds through the adapter protocol. The additive route
is a dedicated driver that reuses the canonical loop
(`tools/eval/framework.py:996-1071`): `solve_ode → observe_endpoint →
apply_restart_distribution → solve_ode`, with `_run_baseline` imported from
`tools/run_sota_2d_experiment` so the control arm is byte-identical to the
existing baseline.

**Why this is a gate, not an autonomous change.** (a) touches the restart
semantics that every R-level headline depends on. Even with the flag defaulting
off, the *decision* to introduce a second seeding convention into the framework
is a paper-level decision (which convention is the framework's?), and the user
has gated every change of that class. (b) is additive and can proceed
independently.

Pre-registration for (b), to be written before the first run:

* Arm: restarted population, `n_rounds = 5`, cosine `n_cap`, N = 1000, the
  canonical 10 seeds.
* Control: `_run_baseline` at the same seed and N (already byte-stable).
* WIN: `|delta| > 0.01` with the paired 95 % CI excluding 0 in the improving
  direction.
* Because (a) is off by default, the first run of (b) *will* exhibit the
  contraction of §3. It is therefore a diagnostic of the contraction, not a
  candidate for the paper. The two changes have to be evaluated together.

---

## 6. What this document does not claim

* It does not claim R5a is a boundary or that the framework cannot win it. It
  says the cell has never been measured with a restart, so its TIE carries no
  information about the mechanism.
* It does not change any number in `docs/CLAIMS.md`, `CLM-060`, or the §7.2
  R5a row. Those remain as published.
* It does not assert that (a) alone is sufficient: §1 shows that even a perfect
  mode balance is worth only 0.0034, so the restarted arm has to win on
  within-mode accuracy, which is a different question that only the run can
  answer.

---

## 7. Status

| item | state |
|---|---|
| §1 mode-lever ceiling | **measured**, 0.0034 < 0.01 floor — inherited hypothesis falsified |
| §2 F1 (no restart on the scored path) | **measured**, 0 calls over 3 rounds |
| §2.1 noise-scale consistency | **measured**, predicted 0.0117 vs observed 0.0107 |
| §3 F2 (record-invariant fresh draw) | **measured**, identical `x0` across records at `m = 0` |
| characterisation tests | `tests/test_gap80_batched_restart.py` (3) |
| fix (a) record-scoped seed | **not implemented — USER GATE** (changes restart semantics) |
| fix (b) restart-capable R5a arm | **not implemented — additive, ready to build** |
| R5a verdict | unchanged: TIE, and now known to be uninformative about the restart |
