# GAP-53 — Breaking initial-condition sensitivity by round count

**Status:** IMPLEMENTATION + PROBE DONE; metric-dispersion stage running
(no confirmatory seed block).
**Parent:** `docs/audit/gap52-charge-channel-run.md` (charge fix and
per-channel `m` both null on R3 `fg_dev`).
**Theory anchor:** `docs/drafts/paper-A-final.md` §6.5, Theorem 4
(conditional contraction of the re-inference map).
**Frozen surfaces:** untouched.
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 1. Why more seeds is the wrong lever

GAP-43 measured the as-wired arm on 50 seeds: `fg_dev` Δ = −0.0192
(p = 0.130), `pb_validity` Δ = +0.212 (50/50 seeds). GAP-52 then changed
the two most plausible mechanism knobs (charge representation, per-channel
memory) and neither improved `fg_dev`. The residual is therefore **not a
representation bug and not a power problem** — it is the map's sensitivity
to the initial condition.

Averaging more initial conditions would only estimate that sensitivity more
precisely. It would not remove it. The project's own theory says the
sensitivity is a property of the composite map, so the fix must change the
map, not the sample size.

## 2. The bound

Let `Φ` be the flow map of the frozen velocity field over `[0, 1]`, and let
`B_m(x) = m x + (1 - m) b` be the restart blend with a fresh input `b`.
The round map is `G_b = Φ ∘ B_m`. If `Φ` is `K`-Lipschitz, then

```
||G_b(x) - G_b(y)|| = ||Φ(B_m x) - Φ(B_m y)||
                    ≤ K ||m(x - y)||
                    = (m K) ||x - y||.
```

So `q := m K` is the per-round contraction factor, exactly Theorem 4. If
`v_θ` is `L`-Lipschitz on the invariant envelope, Grönwall gives the
sufficient bound `K ≤ e^{L T}` with `T = 1`, hence `q ≤ m e^L`.

After `R` rounds with the same map family,

```
||G^R(x) - G^R(y)|| ≤ q^R ||x - y||.
```

**The round count is the contraction knob.** `R = 1` (the canonical driver)
gives one factor of `q`; `R = 4` gives `q^4`. If `q = 0.9`, one round keeps
90 % of the initial-condition discrepancy and four rounds keep 66 %; if
`q = 0.7`, four rounds keep 24 %.

Crucially, this costs **no extra NFE** if the per-round budget is `NFE / R`:
the total integration budget is fixed and the contraction comes from the
composition, not from more compute.

## 3. What the canonical driver actually does

`scripts/wave338_p5_r3_n1000_paired.py` applies **one** prior-side blend and
then **one** full `[0, 1]` solve. That is `R = 1`. The framework's round
structure — the thing the contraction theorem is about — is not exercised on
the valid-molecule path. The SOTA harness does loop (`n_rounds`), but its
export is all-`None` (GAP-39 §3), so it cannot measure R3/K1.

This is the same class of defect as GAP-39: the headline arm was not running
the mechanism the paper describes.

## 4. Implementation (additive, default off)

New flag `--restart-rounds R` (default `1` = byte-identical to today):

```
bundle = blend(build_initial_state(batch_id), fresh_0)   # round-1 prior
for r in range(R):
    nfe_r = nfe // R + (nfe % R if r == R - 1 else 0)
    trace = solve_ode(bundle, num_steps=nfe_r)
    if r < R - 1:
        endpoint = observe_endpoint(trace, bundle)
        bundle = apply_restart_distribution(endpoint, policy)  # endpoint x fresh_r
export(trace)
```

- `R = 1` reproduces the current arm exactly (one prior blend, one solve).
- `R > 1` adds `R - 1` endpoint blends and re-solves, with the **same total
  NFE**. Each `apply_restart_distribution` uses the existing channel-aware
  blend and the existing memory fraction; no new math.
- The fresh draw `b_r` is re-drawn each round (`_sample_native_state` seeded
  by `(policy_hash, round)`), which is the stochastic version of Theorem 4.
  The per-round bound `q` is unchanged because each `G_{b_r}` is
  `q`-Lipschitz for any `b_r`.
- **Round type.** Each round is a full `[0, 1]` re-solve with `NFE / R`
  steps — the canonical restart contract (`G_b = Φ ∘ B_m`), not a
  partial-window continuation. This avoids touching the vendored
  integrator and keeps the total budget fixed.

### 4.1 Batch-path fix (required for the diagnostic)

The first R=2 smoke produced **byte-identical** `fg_dev` for both arms.
Root cause: `n_molecules > 1` caches `traj_x_batch` and does not populate
`traj_x`, so `observe_endpoint` either raised `KeyError` or observed the
wrong state; the restart then blended a stale prior. Three additive
changes close the loop (all default-off, R=1 byte-stable):

| Surface | Change |
|---|---|
| `observe_endpoint` | reads `traj_*_batch[:, -1]`, stores a per-molecule endpoint with a leading molecule axis + `n_molecules` |
| `apply_restart_distribution` | per-molecule fresh draw, seeded by `(restart_seed, mol_idx)`; molecules no longer collapse |
| `_solve_ode_upstream_batch` | consumes per-molecule prior arrays; edge layout is per-molecule `[upper_m, lower_m]` (the legacy tiled path is unchanged) |

Pinned by `tests/test_gap53_batch_endpoint.py` (4 tests) and
`tests/test_gap53_restart_rounds.py` (11 tests). After the fix the R=2
smoke gives different arms (`fg_dev` 0.959 vs 1.182 at N=100, seed 55,
m=0.5) — the mechanism is live.

## 5. Diagnostic (not a seed experiment)

The diagnostic uses a **fixed set of prior draws** (re-used from the
existing block 55…405) and measures the map, not a hypothesis test.

1. **Paired perturbation probe (decisive).** For a prior `x` and a
   fixed unit direction `v`, form `x' = x + ε v` (ε = 0.01) and run
   the *same* map `G = Φ ∘ B_m` on both, with the same restart policy
   and the same upstream seed (so the CTMC draws are identical). With
   the discrete channels held at `m = 1` the paired runs differ **only**
   in the coordinate channel. Record

   ```
   D_r = RMS( G^r(x) - G^r(x') ),   D_0 = ε
   q̂   = (D_R / D_0)^(1/R)
   ```

   over 8 directions. `q̂` is the per-round factor `m K`, measured
   directly rather than inferred from a hypothesis test.

   **Piecewise-smooth caveat.** The upstream sampler is a CTMC: a
   `10^-2` coordinate perturbation can flip a discrete class, which is
   a genuine jump and not a Lipschitz failure of the continuous flow.
   The diagnostic therefore reports the **median** per-round ratio
   (robust to the jumps) plus the fraction of expanding steps, which
   quantifies how often the discrete sampler dominates.

   **Observed (2026-10-19, first probe).** The perturbation probe is
   *not* globally well-posed on FlowMol3: the CTMC can change the
   **atom count** (`24 -> 23` at `ε = 10^-2`), so the coordinate RMS is
   undefined across that event and the strict Lipschitz premise of
   Theorem 4 holds only **within a fixed discrete class**. The probe
   therefore also records a dimension-invariant functional (mean radius
   of gyration) and a `dim_changes` count. This is a limitation of the
   checkpoint's sampler, not of the round structure: the theorem is
   conditional on `a, e` being fixed, which the framework's restart
   blend does not guarantee on this model.

2. **Metric dispersion (expensive, optional).** Record the cross-prior
   SD of `fg_dev` and `pb_validity` at each `R` over the existing seed
   block. The prediction is monotone shrinkage at fixed NFE; the mean
   must not degrade beyond the paired noise.

3. **Identify `K` and the contracting `m`.** At the measured `q̂` and
   the known memory fraction `m`, `K_eff = q̂ / m`. The bound
   `q(m) = m K_eff` then gives `m* = 0.9 / K_eff` for a 10 %-per-round
   contraction. If `q̂ ≥ 1` at `m = 0.5`, that is **not** evidence that
   the map cannot contract — it is evidence that `m` is too large.
   Run a second pass at `m*` and report both.

This is a measurement of `q`, the paper's own stability variable. It is
not a seed-significance test, and no new seed block is created.

## 6. Decision rule

- **CONTRACTION CONFIRMED at `m`** if the median `S(R+1)/S(R)` (or the
  probe's median per-round ratio) is `< 1`.
- **NO CONTRACTION AT THIS `m`** otherwise. Then read off `K_eff` and
  test the predicted `m* = 0.9 / K_eff`. A second null at `m*` means
  the single-round map is not the bottleneck, and the honest conclusion
  is that FlowMol3's `fg_dev` residual is a data/checkpoint limit, not
  an initial-condition limit.
- Either way the result is recorded; no seed block is added.

## 7. Cost

| Stage | Runs | Estimate |
|---|---|---|
| CPU tests + import check | — | minutes |
| GPU smoke (R=2, N=100, 1 seed) | 2 arms | ~5 min |
| Diagnostic (K=8, N=100, R∈{1,2,3,4}) | 4 × 8 × 2 arms | ~1 h |
| Re-evaluate R3 on the existing seed block (only if contraction confirmed) | 50 seeds | ~6.5 h |

The last row re-uses the **existing** GAP-43 seed block (55…545). No fresh
seeds.

## 8. Probe result (2026-10-19)

First run: prior 55, `ε = 10^-2`, `m = 0.5`, 4 directions, `R ∈ {1, 2}`,
N = 4 molecules per batch.

| Direction | `q̂` (R=1) | `q̂` (R=2) | `dim_changes` |
|---|---|---|---|
| 0 | 0.122 | 0.298 | 0 |
| 1 | 27.78 | 7.84 | 0 |
| 2 | 29.89 | 6.20 | 0 |
| 3 | 51.17 | 7.14 | 0 |

**Observed.** One direction contracts (0.12); three amplify by 28–51×.
The amplification is not a smooth Lipschitz constant: the CTMC's final
categorical draw flips a discrete class under a `10^-2` coordinate
perturbation, and in one cell the atom count itself changed (24 → 23).
The realized map is therefore **discontinuous across discrete classes**;
Theorem 4's Lipschitz premise holds only conditional on `(a, e)`.

**Interpretation.** This is a property of the FlowMol3 checkpoint's
sampler, not of the round structure. The continuous flow may still be
contracting within a class, but the framework's restart blend cannot
keep the class fixed — the fresh draw and the CTMC resample both change
it. Consequently `R > 1` cannot be expected to contract `fg_dev` through
coordinate sensitivity on this model, and `m* = 0.9 / K_eff` is not
meaningful when `K_eff` is set by class flips.

The metric-dispersion stage (§5 item 2) is the remaining empirical test:
if the cross-prior SD of `fg_dev` does not shrink with `R`, the honest
conclusion is that the single-round map is not the bottleneck here.

### 8.1 Metric dispersion (K = 4 priors, N = 100, fixed NFE = 250, m = 0.5)

Priors 55 / 105 / 155 / 205 (existing block). Framework arm only; the
paired baseline screen is separate.

| R | `fg_dev` mean | `fg_dev` SD | `pb_validity` mean | `pb_validity` SD | `S` (centroid) |
|---|---|---|---|---|---|
| 1 | 1.1144 | 0.7592 | 0.5225 | 0.3873 | 0.03118 |
| 2 | **0.7877** | **0.3206** | 0.4200 | 0.4202 | **0.01744** |
| 3 | 1.0680 | 0.3757 | 0.3418 | 0.4458 | 0.02203 |

- `S(2)/S(1) = 0.559` (bootstrap CI [0.43, 2.09], K = 4 → wide);
  `S(3)/S(2) = 1.263` ([0.48, 1.86]).
- Per-prior `fg_dev` deltas `R=2 − R=1`: −0.078, +0.038, −0.260,
  −1.007 (3/4 negative; mean −0.327).
- Per-prior `pb_validity` deltas `R=2 − R=1`: −0.15, −0.06, −0.20,
  0.00 (3/4 negative; mean −0.103).

**Reading.** `R = 2` improves both the mean and the cross-prior SD of
`fg_dev`, but it **costs `pb_validity`**. `R = 3` (83 steps per round)
is dominated: no `fg_dev` gain and a larger `pb_validity` loss. The
round count is therefore a **trade-off knob**, not a free win — which
is itself the operating-regime statement the paper wants. Whether the
`R = 2` `fg_dev` gain survives a paired baseline comparison is the
open question; the K = 4 dispersion is not a significance test.

**Caveat.** K = 4 priors, N = 100, one memory fraction. The bootstrap
CI on the `S` ratio includes 1, so the dispersion contraction is
suggestive, not established. No new seeds were used.

### 8.2 Paired driver screen (R = 2 vs baseline, existing seeds, N = 200)

The dispersion stage above is **not** a paired comparison — it changes
the prior between the `R` cells. The decisive test is the canonical
driver with `--restart-rounds 2 --real-restart-blend --shared-prior`,
which pairs both arms on the same prior.

| Seed | baseline `fg_dev` | framework `fg_dev` | Δ`fg_dev` | baseline `pb` | framework `pb` | Δ`pb` |
|---|---|---|---|---|---|---|
| 55 | 0.7317 | 0.8669 | +0.1353 | 0.5450 | 0.7296 | +0.1846 |
| 105 | 0.6016 | 0.6319 | +0.0303 | 0.6834 | 0.6700 | −0.0134 |
| 155 | 1.0228 | 0.9070 | −0.1159 | 0.9697 | 0.7273 | −0.2424 |
| 205 | 0.6977 | 0.6468 | −0.0509 | 0.5600 | 0.6450 | +0.0850 |

**Reading.** The four `fg_dev` deltas are `+0.135, +0.030, −0.116,
−0.051` (mean `−0.0003`, 2/4 favourable). The four `pb_validity` deltas
are `+0.185, −0.013, −0.242, +0.085` (mean `+0.0034`, 2/4 favourable).
Both are a **wash**. `R = 2` neither improves nor degrades the metrics
on average; the seed-to-seed spread is larger than the effect.

**Not significant.** `2/4` favourable with a mean of `−0.0003`
(`fg_dev`) and `+0.0034` (`pb_validity`) is not evidence of a win. No
significance test is reported because the point estimate is zero; a
larger block would only estimate the null more precisely. Per the
no-seed-engineering directive, no extension is run.

**Conclusion.** `R = 2` is null on FlowMol3. It buys no `fg_dev` and
does not reproduce the R = 1 `pb_validity` advantage (GAP-43: +0.212,
50/50 seeds) — but it does not destroy it either; the four-seed mean is
zero with a large spread. The round count is a real knob, but on this
checkpoint the extra round acts as an additional stochastic
perturbation rather than a contraction, exactly what the class-flip
mechanism predicts. Keep the canonical `R = 1` arm for the FlowMol3
claims; do not spend a 50-seed block on `R = 2`.

---

## 9. GAP-54 — class-preserving probe (`sampler_stochasticity = 0`), 2026-10-20

§8 attributed the amplification to CTMC class flips, which left open whether the
*continuous* map contracts once the class is held fixed. GAP-54 tests exactly
that: the upstream `FlowMol.sample` stochasticity is set to 0 (deterministic
CTMC, additive default-off passthrough, `tests/test_gap54_sampler_stochasticity.py`),
so a `10^-2` coordinate perturbation cannot change which class is drawn.

**Protocol.** `K = 8` existing priors (55 / 105 / … / 405, the GAP-43 block —
no new seeds), `R ∈ {1,2,3,4}`, 4 directions each, `eps = 10^-2`, `m = 0.5`,
`N = 20` molecules, total NFE = 250 split evenly across rounds,
`.venvs/flowmol3_venv`, `cuda:0`, `OMP_NUM_THREADS=1`. Artifacts:
`verification_outputs/gap54-contraction-stochasticity0/` (32 cells, 128
direction-runs, `METADATA.txt` + `probe.log` + `summary.json`).

### 9.1 Observed

**The class is fixed.** `dim_changes = 0` in all 128 direction-runs. The
stochasticity passthrough does what it claims: with the CTMC deterministic, the
atom count never diverges. Acceptance condition (2) first half is met.

**The map still expands.** Median per-round ratio by round index:

| round | n | median ratio | share > 1 |
|---:|---:|---:|---:|
| 1 | 128 | **11.91** | 0.80 |
| 2 | 96 | **3.80** | 1.00 |
| 3 | 64 | **1.49** | 0.98 |
| 4 | 32 | **1.23** | 1.00 |

Cell-level `ratio_median` by round count:

| R | cells | median | range |
|---:|---:|---:|---|
| 1 | 8 | 19.10 | [0.28, 40.31] |
| 2 | 8 | 7.56 | [2.72, 11.73] |
| 3 | 8 | 3.12 | [1.83, 4.36] |
| 4 | 8 | 1.70 | [1.18, 2.08] |

Verdict (`summary.json`): `NO CONTRACTION AT THIS m (CI upper >= 1)`,
`ratio_median = 3.74`, bootstrap 95 % CI **[2.33, 7.02]**, `K_eff = 11.64`,
`m* (q = 0.9) = 0.077`.

### 9.2 Interpretation

1. **The GAP-53 null is not a class-flip artefact.** With the class provably
   fixed, 98–100 % of round transitions still expand. The continuous flow map
   on this checkpoint has `K > 1` in the coordinate channel at `m = 0.5`.
2. **The expansion is real but decaying.** 11.9 → 3.80 → 1.49 → 1.23. The
   sequence is consistent with a fixed-point expansion factor just above 1
   that the first round overshoots; it does not approach or cross 1 within
   `R = 4`.
3. **Contraction would require discarding the memory.** `m* ≈ 0.08` means
   `β ≈ 0.92`: a restart that keeps 8 % of the previous sample. At that point
   the "restart" is a fresh draw with a rounding error of the old one, and the
   mechanism is no longer the one Theorem 4 describes.
4. **Acceptance (3) is not triggered.** The paired `R = 2` screen was
   conditional on contraction; it is not run, and no new seeds are spent.

### 9.3 Caveat — `D_0` bookkeeping in this run

The recorded `D[0]` is `eps = 10^-2`, but the direction is normalised in
Frobenius norm, so the perturbation's per-coordinate RMS is
`eps / sqrt(3 * n_atoms)` — smaller than `eps` by 5.5–13× for the atom counts
in this block. Every ratio that involves `D[0]` (i.e. the round-1 ratio and
`q_hat`) is therefore **understated** by that factor. The tool was corrected
after the run (`d[0] = RMS(x_base - x_perturbed)`); the artifacts above keep
the old convention. The correction can only make the round-1 ratios larger —
already a median of 11.9 and 80 % above 1 — so the verdict is unchanged in
either direction.

### 9.4 Consequence

**GAP-54 is closed.** The contraction premise does not hold on the realized
FlowMol3 map even with the discrete class held fixed, so Theorem 4 cannot be
exercised there at any `m` that still counts as a restart. The FlowMol3 cells
keep `R = 1`. This is a negative result about the *model*, not about the
framework: the same probe is the right test for any other adapter, and it is
cheap (about 90 min on one GPU for 128 direction-runs).
