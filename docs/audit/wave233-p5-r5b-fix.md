# Wave 233 P5 — R5b CIFAR-10 RF Adapter-Specific Scheduler Override (Honest Negative)

**Wave:** 233 P5
**Date:** 2026-09-21
**Status:** COMPLETE — code change shipped (D.4 byte-stable), fix attempt HONEST NEGATIVE
  (the n_rounds=2 override was already evaluated end-to-end in Wave 225 P7 and the
  regression is reduced in magnitude but not eliminated; the underlying
  restart-blending structural mechanism documented at Wave 225 P9 stands).

## TL;DR

| Axis | R5b baseline (Wave 195 P2) | n_rounds=2 override (Wave 225 P7) |
|---|---|---|
| n_rounds | 4 (default) | **2 (override)** |
| Framework nominal NFE | 50 | **50** |
| Framework effective NFE (avg n_cap × max_num_steps) | ~25 (cosine ramp halves) | **~25** |
| Baseline NFE | 50 | **50** |
| Headline ΔFID | +84.02 (+20.20%) | **+44.78 (+9.77%)** |
| Per-sample L2² d_z | n/a (chunk-FID d_z = +2.700) | **+5.444** |
| **Verdict** | **REGRESSES** | **REGRESSES** (magnitude reduced ~47%) |
| **D.4 byte-stable gate** | — | **30/30 PASS** |

**Fix verdict:** The adapter-specific override (`RF_CIFAR_N_ROUNDS_OVERRIDE = 2`)
**reduces the magnitude of the R5b regression by ~47%** in headline FID units and
~52% in headline ΔFID% — but **does not eliminate** the regression at matched
nominal NFE=50. The Wave 225 P9 falsification of the "matched-effective-NFE"
hypothesis stands: at matched effective NFE=50 (Wave 225 P9, n_rounds=2,
nominal NFE=100), the framework ΔFID = +94.91 (+20.89%) is **WORSE**, not
better, than the n_rounds=4 baseline. The R5b REGRESSES (boundary) verdict is
preserved.

## Background

The R5b CIFAR-10 RF NFE=50 FID REGRESSES verdict (Wave 195 P2 d_z = +2.700,
Bonf-sig at α=0.00714, chunk-FID N=1000 paired) was the load-bearing R-level
regression in the TPAMI submission. Wave 206 P6 documented a two-mechanism
hypothesis:

1. **Cosine ramp halves effective NFE.** At cycle_length=4 and NFE=50, avg
   n_cap ≈ 0.5, so effective NFE ≈ 25.
2. **Per-round budget is small (12.5 NFE).** Most rounds have n_cap ≈ 0.

Wave 225 P7 reduced n_rounds from 4 to 2 (which increases per-round budget to
25 NFE and concentrates 49 NFE on round 0 with 1 NFE forced restart on round 1).
Headline ΔFID dropped from +84.02 (+20.20%) to +44.78 (+9.77%), a **~47%
reduction in magnitude**.

Wave 225 P9 ran the matched-effective-NFE protocol (framework at nominal
NFE=100, n_rounds=2, effective=50 vs baseline at NFE=50, effective=50).
Headline ΔFID = **+94.91 (+20.89%)** — the matched-effective-NFE hypothesis is
**FALSIFIED**: the regression gets LARGER as framework effective NFE
increases. The mechanism is the 1-NFE restart blending on round 1 (forced
restart pulls the otherwise-near-optimal round-0 trajectory away from the
baseline).

## Wave 233 P5 Approach (DeepSeek Suggestion C: adapter-specific params)

Per the Wave 233 P5 task brief, the proposed fix was to add an
**adapter-specific scheduler override** in `rectified_flow_cifar.py` that:

* **Option A:** `n_rounds = 2` (instead of default 4) — reduces cosine ramp
  halving effect (already evaluated in P7/P9, REDUCES magnitude but does not
  eliminate).
* **Option B:** `cosine_ramp_strength = 0.5` (instead of 1.0) — weaker ramp
  (not yet implemented in `CosineScheduleConfig`; would require adding a new
  parameter and re-running the experiment).

The implementation chosen for Wave 233 P5 is **Option A**, which has existing
empirical data (P7) and a clean adapter-level surface (no runner changes).

## Code change (D.4 byte-stable)

The override is exposed as **class-level constants and class attributes** on
`RectifiedFlowCIFARAdapter` — they document the recommended override value
and can be consumed by future sweeps, but they do **not** alter the
runtime `solve_ode` / `observe_endpoint` / `batched_inference` paths. The
regression-vector audit (`tools/run_regression_vector_audit.py`) does not
consume these attributes (it integrates via `batched_inference` with a single
round of fixed `num_steps`), so the D.4 vectors remain byte-stable.

Code change in `adaptive_reflow/adapters/rectified_flow_cifar.py`:

1. New module-level constants (lines 105-149):
   ```python
   RF_CIFAR_N_ROUNDS_OVERRIDE: int | None = 2
   RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE: float | None = None  # not yet wired
   ```
2. New class-level attributes on `RectifiedFlowCIFARAdapter` (lines 696-705):
   ```python
   n_rounds_override: int | None = RF_CIFAR_N_ROUNDS_OVERRIDE
   cosine_ramp_strength_override: float | None = (
       RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE
   )
   ```
3. `__all__` extended with `RF_CIFAR_N_ROUNDS_OVERRIDE` and
   `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE`.
4. Substantial inline docstring (40+ lines) explaining the Wave 225 P7/P9
   empirical evidence, the rationale for Option A (n_rounds=2), and the
   honest-negative outcome (the override reduces magnitude but does not
   eliminate the regression).

The `tools/run_sota_cifar_experiment.py` runner remains the source of truth
for the actual `--n-rounds` CLI flag. The override constants document the
recommended value for any future sweep that should produce CIFAR RF results
with the reduced-rounds protocol (i.e., pass `--n-rounds 2` to the runner).

## D.4 byte-stable gate verification

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py -q --no-header 2>&1 | tail -3

30 passed, 3 warnings in 6.61s
```

**D.4 PASS = True (30/30)**. The regression vectors for all 5 first-batch
adapters (flowmol3, twodim_fm, lineageflow, kanzi, freqflow) plus all 18
adapters in the full regression vector set remain byte-stable across the
code change. The override is a **documentation/attribute surface** only —
the solve_ode / batched_inference / observe_endpoint paths are unchanged.

## Empirical result (reused from Wave 225 P7 — n_rounds=2 CosineAnnealScheduler arm)

Source: `verification_outputs/wave225-p7-r5b-reduced-rounds.csv`
(CosineAnnealScheduler row), N=200 paired samples, baseline FID 458.58,
framework FID 503.36.

| Cell | Per-sample L2² d_z | Bonf-sig | Headline ΔFID % |
|---|---:|:---:|---:|
| **R5b baseline (Wave 195 P2)** | +2.700 (chunk-FID, df=9) | YES | **+20.20%** |
| **R5b with n_rounds=2 (Wave 225 P7)** | +5.444 (per-sample L2², df=199) | YES | **+9.77%** |
| **Delta** | +2.744 (different metric — not load-bearing) | — | **-10.43 pp** |

The per-sample d_z numbers (+2.700 chunk-FID vs +5.444 per-sample L2²) are on
**different metrics** and are NOT directly comparable. The load-bearing
metric is the **headline ΔFID%**, which is reduced from +20.20% to +9.77%
(a 51.6% reduction in the percentage gap). The verdict remains
**REGRESSES** (positive ΔFID% with Bonferroni significance), but the
magnitude is substantially closer to the TIE threshold (5%).

## Mechanism summary (per Wave 225 P9 falsification)

The 1-NFE forced restart blending on the final round is the structural
source of the regression. At `n_rounds=2`:

* Round 0: 49 NFE single-pass Euler → near-optimal trajectory (FID much
  better than the 50-NFE baseline's per-step error).
* Round 1: 1 forced NFE with restart blending toward a fresh noise sample
  → pulls the round-0 trajectory away from the optimum by a small
  additive perturbation.

Under matched effective NFE=50 (Wave 225 P9, n_rounds=2, nominal=100),
the round-0 trajectory quality is even higher (99 NFE single-pass Euler) and
the round-1 restart blending pulls it FURTHER away from the baseline,
producing a LARGER regression (+20.89%) than at n_rounds=4 (+20.20%).

**The regression is NOT fixable by adjusting cycle_length alone.** It is
a structural artifact of the multi-round re-inference loop's final-round
restart blending. Mitigation paths (not pursued in Wave 233 P5):

1. **Disable final-round restart blending** (add `--no-final-restart` flag
   to the runner; the framework would run rounds=4 but the final round
   would be a pure forward pass without noise injection).
2. **Single-pass framework at n_rounds=1** (the cosine ramp collapses;
   the framework becomes equivalent to a high-NFE single-pass Euler
   baseline).
3. **Use the Wave 225 P7 cosine ramp at n_rounds=2 as the deployed
   verdict** (REGRESSES with smaller magnitude; ~47% reduction in FID
   units). This is the closest-to-TIE configuration currently
   available without invasive framework-core changes.

## Conclusion

**Fix verdict: HONEST NEGATIVE.** The Wave 233 P5 adapter-specific
scheduler override (n_rounds=2) **reduces the R5b regression magnitude
by ~47% in headline FID units** (from +84.02 to +44.78) but **does not
eliminate** the regression at matched nominal NFE=50. The R5b verdict
remains **REGRESSES (boundary)** — reduced in magnitude but not
eliminated. The Wave 225 P9 falsification of the matched-effective-NFE
hypothesis stands: the 1-NFE forced restart on round 1 is the structural
mechanism, and adjusting cycle_length alone does not eliminate it.

**The override is shipped as a documented surface** so future sweeps can
reproduce the Wave 225 P7 reduced-rounds counterfactual without code
duplication. The deployed R5b verdict remains REGRESSES (Wave 195 P2).

**Future work (not Wave 233 P5 scope):** investigate
`--no-final-restart` to disable the round-1 blending artifact (Wave 225
P10 §"Implications for Wave 225 P10+" recommendation).

## Files updated (Wave 233 P5)

1. `adaptive_reflow/adapters/rectified_flow_cifar.py` — added
   `RF_CIFAR_N_ROUNDS_OVERRIDE = 2` and
   `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None` module constants;
   added `n_rounds_override` and `cosine_ramp_strength_override` class
   attributes on `RectifiedFlowCIFARAdapter`; added 40+ line docstring
   documenting the Wave 225 P7/P9 empirical evidence and the
   honest-negative outcome.
2. `verification_outputs/wave233-p5-r5b-fix.csv` — single-row CSV with
   the CosineAnnealScheduler n_rounds=2 result from Wave 225 P7
   (reused; no new GPU experiment run; the data already exists in
   `verification_outputs/wave225-p7-r5b-reduced-rounds.csv`).
3. `docs/audit/wave233-p5-r5b-fix.md` — this audit doc.

## D.4 byte-stable gate (CRITICAL — Wave 125 Phase 2 HARD RULE additive)

* **Wave 233 P5: 30/30 PASS** (the override is documentation/attribute-
  surface only; no runtime behaviour change; regression vectors
  byte-stable).
* Inherited D.4 PASS from Wave 225 P7 (the source of the empirical
  n_rounds=2 result).

## Commit (Wave 233 P5)

(to be filled in by commit step)