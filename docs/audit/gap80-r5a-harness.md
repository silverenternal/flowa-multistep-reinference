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
| fix (a) record-scoped seed | **not implemented — USER GATE** (changes restart semantics); measured as a diagnostic arm (§9) |
| fix (b) restart-capable R5a arm | **landed** — `tools/r5a_restart_driver.py` + 8 tests (§8, §9) |
| §8.7 time-alignment fix (2-D `t0`/`t1`) | **landed**, default-off, byte-identical (D.4 30/30) |
| R5a verdict | **TIE, measured on a real restart** — 0.0844 vs 0.0783, p = 0.29; the shipped restart is a 16x LOSS (§9) |

---

## 8. Pre-registration for the restart-capable arm (written before the N = 1000 run)

**Date written:** 2026-10-25, before the N = 1000 grid. §8.1–§8.5 are frozen
once that grid starts; results go in §9.

### 8.1 What is being compared

`tools/r5a_restart_driver.py` runs three arms on the same adapter, the same
initial states and the same NFE budget:

| arm | rounds | restart | fresh-draw seed |
|---|---:|---|---|
| **A** baseline | 1 | no | — |
| **B** restart, shipped seeding | 5 | yes | `sha256(policy_hash, next_round)` — record-invariant (§3, F2) |
| **C** restart, record-scoped seeding | 5 | yes | `sha256(policy_hash, record, next_round)` — **diagnostic only** |

All three go through the adapter protocol (`solve_ode → observe_endpoint →
apply_restart_distribution`), so A vs B isolates the restart and B vs C
isolates the seeding convention. A is additionally cross-checked against
`_run_baseline` to confirm the protocol path lands on the published baseline's
scale; that check is a distribution check, not a byte check, because
`_run_baseline` draws `x0` through `generate_trajectory`.

`C` does **not** modify the adapter. It re-hashes the policy before the call,
which is enough because `TwoDimFMAdapter.apply_restart_distribution` derives the
fresh draw from `policy.policy_hash` and nothing else. Nothing in
`adaptive_reflow/` changes, so §5(a)'s gate is untouched: C measures what the
gate would buy, it does not exercise the gate.

### 8.2 Fixed settings

| axis | value | why |
|---|---|---|
| N | 1000 | the cell's own N |
| seeds | 42 … 51 | the canonical ten the published R5a table uses; no top-ups |
| NFE | 150 | `TWODIM_FM_NUM_STEPS`, the baseline's budget |
| rounds | 5 | §5's pre-registration |
| β | `1 − n_cap` from `CosineAnnealScheduler(cycle_length=5)`, passed via `beta_override` with `nfe=0` | the nominal schedule, *without* the NFE-adaptive rescale, so β is exactly what the schedule says |
| NFE split | even, remainder in the last round | total equals the baseline's |
| metric | closed-form 2-D `W2` (`_wasserstein_2d`) | the cell's metric |

### 8.3 Decision rules

1. **Primary (C vs A).** `WIN` iff `|Δ| > 0.01` (the R5a effect floor) **and**
   the paired 95 % CI over the ten seeds excludes 0 in the improving direction.
   `TIE` iff the CI contains 0 or `|Δ| ≤ 0.01`. `LOSS` iff the CI excludes 0 in
   the worsening direction.
2. **B vs A is diagnostic, not a candidate.** B is the arm the shipped
   convention produces. It is expected to be worse (§3's contraction); if it is
   not, that is itself worth reporting, but it cannot be the paper's arm because
   it would mean the contraction is not the mechanism.
3. **If C wins, R5a does not automatically become a WIN.** C requires the
   record-scoped convention, which is a user-gated change to restart semantics
   (§5a). The verdict in that case is `HARNESS_FIXED_NEEDS_GATE`: the cell's
   TIE is explained and the fix is measured, but the paper number cannot move
   until the gate is answered.
4. **If C loses, R5a stays a TIE** and the boundary is the blend's variance
   behaviour, not the harness. No further seed, no further schedule.
5. **Report the variance ratio.** For each arm, `Tr(Cov(endpoints))` against
   A's. A convex blend of two independent `N(0, I)` draws has variance
   `m² + (1 − m)²`, which is `< 1` for every `m ∈ (0, 1)` — so *both* restart
   arms are expected to contract, and the ratio says by how much. This is
   reported whether or not C wins.

### 8.4 Screen (N = 100, seed 42, `SCREEN_ONLY`)

One seed at N = 100 was run to check the driver is not inert before spending
the grid. It is not quoted as evidence and it selected nothing:

```
baseline 0.26761 | B (policy) +171.63 % | C (record) -45.15 %
```

The sign split is the expected one (B collapses toward one common point, C
resamples), and the magnitude is why the grid is worth running. It fixes no
parameter: the grid above was written first.

### 8.5 What this cannot settle

* It cannot tell whether a *variance-preserving* restart (`m·x + sqrt(1−m²)·ε`,
  or interpolation along the probability path) would beat both. That is a
  different operator and would need its own pre-registration.
* It cannot move any `docs/CLAIMS.md` number. R5a's published row stays as is
  until the §8.3 rule 3 gate is answered.

### 8.6 Amendment — a variance-preserving arm (written before its first run)

§8.5 said a variance-preserving operator "would need its own pre-registration".
This is that paragraph, written after the N = 100 screen and **before** the
N = 1000 run of the arm.

**Why.** The convex blend `m·prior + (1−m)·fresh` of two independent draws has
input variance `m² + (1−m)²`, which is `< 1` for every `m ∈ (0, 1)` — at
`m = 0.5` it is 0.5. The 2-D flow is strongly scale-sensitive (measured:
feeding `x0` scaled by 0.85 costs +23 % W2, by 0.5 costs +181 %), so the blend
mechanically hands the integrator an under-dispersed input. `vp` replaces the
coefficient on the fresh term with `sqrt(1 − m²)`, which restores input
variance to 1 for unit-variance inputs while keeping the fixed points
(`m = 1` → prior, `m = 0` → fresh).

**Arm.** `vp_record` = the `convex_record` arm with only that coefficient
changed. The record-scoped seeding is kept because the two defects are
independent and the variance question is only legible once the draw is
record-scoped. `convex_record` remains the matched control for this arm; the
driver's `convex` helper is asserted byte-identical to
`TwoDimFMAdapter.apply_restart_distribution`
(`test_convex_helper_reproduces_the_adapter_byte_for_byte`), so the pair differs
by exactly one line of arithmetic.

**Rule.** Same as §8.3 rule 1, read against `convex_record` rather than the
baseline: `WIN` iff the paired CI excludes 0 in the improving direction **and**
`|Δ| > 0.01`. If `vp_record` closes the gap to the baseline but does not beat
it, the verdict is `CONTRACTION_IS_THE_MECHANISM` and R5a stays a TIE — the
operator recovers what it destroyed, it does not add anything.

### 8.7 Amendment — time-aligned restart (written before its first N = 1000 run)

**The defect this names.** On the two-moons adapter the path is
`x_t = (1 − t)·x_0 + t·x_1`, so the restart blend `m·x_1 + (1 − m)·x_0` is the
path state at **`t = m`**. `TwoDimFMAdapter.solve_ode` built its grid as
`linspace(0, 1)` unconditionally, so the next round integrated a mid-path state
from `t = 0` — evaluating the velocity field at the wrong time. That is exactly
the defect GAP-56 fixed for `MnistFMAdapter`, which reads `t0`/`t1` from the
condition and integrates `[t_start, 1]`.

**Code change.** `twodim_fm.py::solve_ode` now reads `t0`/`t1` from
`condition.delta_spec` with defaults `0.0`/`1.0`, validates
`0 ≤ t0 ≤ t1 ≤ 1`, and uses them for the grid and the Dormand-Prince call. The
defaults reproduce the old grid exactly, so every legacy call is byte-identical
(D.4 30/30 re-run after the change). The trajectory digest gains `t0`/`t1`
**only when they differ from the defaults**, so no historical digest moves and
two solves cannot collide in the cache.

**Arm.** `aligned_record` = `convex_record` with `t0 = memory_fraction` on every
post-restart round. Nothing else changes: same blend, same record-scoped
drawing, same NFE split. `aligned_policy` is the same with the shipped seeding
and is reported for completeness.

**Rule.** Same as §8.3 rule 1 against the baseline. If `aligned_record` removes
the deficit but does not beat the baseline, the verdict is
`TIME_COORDINATE_IS_THE_MECHANISM` and R5a stays a TIE.

**Why this is not a gate.** It is the 2-D instance of a fix the MNIST path
already carries, it is off by default in the sense that `t0` is absent from
every existing call, and it moves no published number. The restart *semantics*
question of §5(a) (which seeding convention is the framework's) is untouched.

---

## 9. Result — the restart's deficit was two implementation defects, and fixing both lands on the baseline

Run 2026-10-25, N = 1000, seeds 42-51, NFE = 150, 5 rounds, cosine `n_cap`.
Artifacts: `verification_outputs/gap80-r5a-restart/` (`r5a_restart.json`,
`aligned/r5a_restart.json`).

### 9.1 The baseline is the published baseline

| arm | W2 |
|---|---:|
| protocol baseline (this driver, 1 round) | 0.07828 |
| `_run_baseline` (the published path) | 0.07910 |

Paired over the ten seeds: Δ = −0.0008, t = −0.20, p = 0.84. The protocol path
lands on the published value, so every contrast below is against the cell's own
baseline rather than against a different sampler.

### 9.2 The ladder

| arm | what it changes | W2 | Δ | Δ CI95 | Δ % | var ratio | verdict |
|---|---|---:|---:|---|---:|---:|---|
| `convex_policy` | nothing (the shipped operator + seeding) | 1.2804 | +1.2021 | [+0.955, +1.449] | +1536 % | 0.062 | **LOSS** |
| `convex_record` | fresh draw scoped to the record | 0.2300 | +0.1517 | [+0.131, +0.173] | +194 % | 0.914 | **LOSS** |
| `vp_record` | + variance-preserving blend | 0.2059 | +0.1277 | [+0.104, +0.151] | +163 % | 0.995 | **LOSS** |
| `aligned_record` | + integrate from `t = memory` | 0.0844 | +0.0061 | [−0.006, +0.018] | +7.8 % | 1.007 | **TIE** |

All p-values are ≤ 6e-7 except the last (p = 0.29).

Three things this ladder settles:

1. **The shipped restart is a loss, not a tie.** With the operator exactly as
   the code runs it (`convex_policy`), the restarted population is **16x** the
   baseline's W2 and its variance is 6 % of the baseline's. The published TIE
   was measured on a path that never dispatches the restart (§2), so it never
   saw this.
2. **§8.6's variance hypothesis is falsified.** `vp_record` restores the
   variance exactly (ratio 0.995 vs 0.914) and moves W2 by only 0.024
   (0.230 → 0.206). Variance was a symptom, not the mechanism.
3. **The time coordinate is the mechanism.** Going from `convex_record` to
   `aligned_record` — one change, `t0 = memory` — removes 96 % of the remaining
   deficit (0.152 → 0.006) and brings the variance ratio to 1.007. That is the
   GAP-56 defect, and it was still present in the 2-D adapter.

**Verdict: `TIME_COORDINATE_IS_THE_MECHANISM`.** Per §8.7 the cell stays a
**TIE**: the restart now matches the baseline and adds nothing.

### 9.3 Dose-response (screen, seed 42 only — not evidence)

| rounds | aligned W2 | Δ % |
|---:|---:|---:|
| 2 | 0.06343 | **0.00 %** |
| 3 | 0.07817 | +23.2 % |
| 5 | 0.08928 | +40.8 % |

`R = 2` is degenerate rather than a win: cosine `n_cap` is 1.0 at round 0, so
the first restart is the identity and the second round integrates `[1, 1]`.
The two non-degenerate points are monotonically worse with more restarts. One
seed, quoted only to show the shape; the 10-seed grid is the evidence.

### 9.4 What this means for R5a

The cell is a **TIE for the shipped path and a TIE for a correctly implemented
restart**, which is a stronger statement than the original one: the earlier TIE
was uninformative (§4), and this one is a measurement. Two conditions attach to
it and neither is satisfied by the current code:

* the fresh draw must be record-scoped (§5a, **USER GATE** — it changes restart
  semantics for every R-level cell), and
* the post-restart round must integrate from `t = memory` (§8.7, landed for the
  2-D adapter; MNIST already had it).

Without both, the restart is a 16x regression. With both, it is neutral. That
is the honest status: **the restart does not buy anything on this cell**, and
the paper should not claim otherwise.

`docs/CLAIMS.md` is untouched. The published R5a row still describes the
no-restart path, which is what it was measured on.
