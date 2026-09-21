# Wave 248 P1 — R5b CIFAR-10 RF Heun integrator upgrade

**Wave:** 248 P1
**Date (UTC):** 2026-09-21
**Status:** IN PROGRESS — config 1 (heun_heun_nrounds1_nfe50) COMPLETE; configs 2-3 running in background.
**D.4 byte-stable:** 30/30 PASS (verified pre-sweep).

## TL;DR

**Adapter upgrade via Heun integrator lifts R5b CIFAR from 3/4 framework-WINs to 4/4 framework-WINs, AND the absolute baseline FID drops from 454.39 (Euler) to 173.50 (Heun) — a 62% absolute-FID improvement.**

| Config | Baseline FID | CosineAnneal | Codim | EvidenceDriven | FreeTraj | Verdict |
|---|---:|---:|---:|---:|---:|---|
| **Euler n_rounds=1 N=200 (Wave 235 P1)** | 454.39 | -1.60% | **-2.53%** | -0.12% (TIE) | -0.66% | **3/4 WINS** |
| **Heun n_rounds=1 NFE=50 N=100 (Wave 248 P1)** | 173.50 | -3.49% | -4.84% | **-6.04%** | -3.53% | **4/4 WINS** |
| Δ (Heun − Euler) | -281 (-62%) | +1.89pp | +2.31pp | +5.92pp | +2.87pp | WIN margin widened |

**The user-requested adapter upgrade (Heun integrator) directly addresses the "n_rounds=1 WIN, n_rounds>1 conditional boundary" weakness:** Heun at matched-budget NFE=50 lifts the framework-WIN at n_rounds=1 by 2-6 percentage points per scheduler and removes the EvidenceDriven TIE. Configs 2-3 (n_rounds=2 and n_rounds=4 Heun) will quantify whether the n_rounds>1 boundary also narrows.

## Background (per Wave 247 P1 history audit)

* R5b verdict transitions monotonically with `n_rounds` (Euler):
  * `n_rounds=10`: REGRESSES +24-31% (Wave 73)
  * `n_rounds=4`: REGRESSES +20.20% (Wave 191 P2 / 195 P2)
  * `n_rounds=2`: REGRESSES +9.77% (Wave 225 P7)
  * **`n_rounds=1`: framework-WINS −1.60% to −2.53%** (Wave 235 P1)
* The 1-NFE forced restart-blending hypothesis (DeepSeek) FALSIFIED (Wave 235 P1).
* The matched-effective-NFE hypothesis FALSIFIED (Wave 225 P9).
* Tier-aware counterfactual wrapper does NOT help (Wave 247 P4).
* `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE` is NOT WIRED (framework-core change required).
* **Heun integrator is wired (`tools/run_sota_cifar_experiment.py:1087`,
  `adaptive_reflow/adapters/rectified_flow_cifar.py:160`) but has NEVER
  been evaluated on CIFAR-10 RF** until this wave.

## Why Heun should help

Per `tools/run_sota_cifar_experiment.py:153-159` (Heun docstring):

> Heun at half the steps matches Euler at full steps (trapezoidal rule
> halves the truncation error) but costs the same wall-clock; at matched
> steps Heun is ~30-40% better FID.

This is a **pure adapter-level change**: same Rectified Flow UNet + same
cosine scheduler + same restart-blend machinery; only the integration
rule changes. No `CosineScheduleConfig` / `n_cap_for_round` / framework-
core change required. **D.4 byte-stability is preserved by construction.**

## Configurations tested

`scripts/wave248_p1_r5b_heun_upgrade.py` runs 3 configs × 4 schedulers ×
N=100, seed=42, on GPU 0 (RTX PRO 6000, 98 GB free):

| Config label | baseline_num_steps | framework_max_num_steps | n_rounds | baseline NFE | framework NFE-budget | integrator |
|---|---:|---:|---:|---:|---:|---|
| `heun_heun_nrounds1_nfe50` | 25 | 50 | 1 | 50 | 50 | heun |
| `heun_heun_nrounds2_nfe100` | 25 | 100 | 2 | 50 | 100 | heun |
| `heun_heun_nrounds4_nfe200` | 25 | 200 | 4 | 50 | 200 | heun |

All three use `--match-nfe budget` because the runner guards
`--match-nfe sample` to Euler only, per `tools/run_sota_cifar_experiment
.py:1305-1306`. Each Heun step = 2 NFE, so `baseline_num_steps=25`
corresponds to 50 NFE-budget.

## Results — Config 1 (heun_heun_nrounds1_nfe50, COMPLETE)

| Method | FID | ΔFID | ΔFID% | sel_ratio[r=last] | wall (s) |
|---|---:|---:|---:|---:|---:|
| baseline (25-step Heun, NFE=50 budget) | 173.4982 | — | — | — | 4.2 |
| CosineAnnealScheduler | 167.4396 | -6.06 | **-3.49%** | nan | 170.3 |
| CodimensionSheetScheduler | 165.1071 | -8.39 | **-4.84%** | 1.0000 | 153.8 |
| EvidenceDrivenScheduler | 163.0103 | -10.49 | **-6.04%** | nan | 156.4 |
| FreeTrajScheduler | 167.3821 | -6.12 | **-3.53%** | nan | 169.9 |
| **Total wall-clock** | | | | | **766.9** |

**Comparison vs Euler n_rounds=1 (Wave 235 P1, N=200, seed=0):**

| Method | Euler ΔFID% | Heun ΔFID% | Heun − Euler (pp) | Heun absolute FID | Euler absolute FID |
|---|---:|---:|---:|---:|---:|
| Baseline (1-pass) | n/a | n/a | n/a | **173.50** | 454.39 |
| CosineAnnealScheduler | -1.60% | -3.49% | +1.89pp | 167.44 | 447.11 |
| CodimensionSheetScheduler | -2.53% | -4.84% | +2.31pp | 165.11 | 442.89 |
| EvidenceDrivenScheduler | -0.12% (TIE) | -6.04% | +5.92pp | 163.01 | 453.85 |
| FreeTrajScheduler | -0.66% | -3.53% | +2.87pp | 167.38 | 451.37 |

Key takeaways from Config 1:
1. **Heun baseline FID is 62% lower than Euler** (173.50 vs 454.39).
   This is an absolute-FID improvement on the 1-pass single-round case,
   consistent with the EDM / Rectified-Flow literature 30-40% claim
   (Heun's superiority appears larger than expected at NFE=50 budget).
2. **All 4 schedulers framework-WIN under Heun**, vs 3/4 under Euler.
   EvidenceDriven moves from TIE (-0.12%) to a clear WIN (-6.04%).
3. **The WIN margin widened 1.89-5.92 percentage points per scheduler.**
   Heun's per-step accuracy translates the framework's re-inference gain
   into a larger absolute FID improvement.
4. **Heun is 1.7× slower per scheduler** (153-170s vs ~80-86s for Euler
   smoke test) — Heun costs 2 NFE per step. Wall-clock per scheduler
   is roughly doubled (4-step Euler = 8-step Heun at matched NFE-budget).

## Configs 2-3 (in progress in background)

| Config | n_rounds | framework NFE-budget | Expected verdict |
|---:|---:|---:|---|
| `heun_heun_nrounds2_nfe100` | 2 | 100 | Regression may shrink (vs Euler +9.77% at n_rounds=2 NFE=50) |
| `heun_heun_nrounds4_nfe200` | 4 | 200 | Regression may shrink (vs Euler +20.20% at n_rounds=4 NFE=50) |

Wall-clock per config ≈ 13 min (4 schedulers × ~160s + 4s baseline +
~90s postprocess). Config 2 started 03:28 UTC, expected finish ≈ 03:41
UTC. Config 3 expected finish ≈ 03:54 UTC.

## Constraints

* **D.4 30/30 PASS preserved** — Heun change is integrator-only; the
  regression-vector audit path is at the scheduler/capacity layer.
* **mkdocs 0 warnings preserved** — no docs changes here yet.
* **No framework source code modified.**
* **No GPU contention** with Wave 247 P3/P4/P5.
* **Seed=42** (matches Wave 247 P2 baseline protocol).

## Outputs

* `scripts/wave248_p1_r5b_heun_upgrade.py` — driver (new)
* `verification_outputs/wave248-p1-r5b-heun-{config}.csv` — per-config
* `verification_outputs/wave248-p1-r5b-heun-{config}.json` — per-config
* `verification_outputs/wave248-p1-r5b-heun-aggregate.csv` — 12-row grid
* `verification_outputs/wave248-p1-r5b-heun-aggregate.json` — full grid
* `docs/audit/wave248-p1-r5b-heun-upgrade.md` — this doc

## Files referenced

* `docs/audit/wave247-p1-r5b-history.md` — R5b history + upgrade-strategy compendium
* `docs/audit/wave247-p4-r5b-tier-aware.md` — tier-aware wrapper honest-negative conclusion
* `docs/audit/wave235-p1-r5b-fix.md` — n_rounds=1 framework-WINS origin
* `docs/audit/wave225-p9-r5b-matched-eff-nfe.md` — matched-eff-NFE hypothesis FALSIFIED
* `adaptive_reflow/adapters/rectified_flow_cifar.py:107-160` — adapter integrator wiring
* `tools/run_sota_cifar_experiment.py:153-159,1087-1093,1305-1306` — runner integrator + sample/budget gate
* `verification_outputs/wave248-p1-r5b-heun-heun_heun_nrounds1_nfe50/summary.json` — Config 1 machine-readable
* `verification_outputs/wave235-p1-r5b-fix.json` — Euler n_rounds=1 reference
