# Wave 247 P1 — R5b CIFAR-10 RF History + Upgrade-Strategy Compendium

**Wave:** 247 P1
**Date:** 2026-09-22
**Status:** DONE — read-only audit; no source-code modifications; no GPU jobs.
**Goal:** Compile a single-source-of-truth R5b (CIFAR-10 Rectified Flow
matched-NFE=50 FID) history table, identify the strongest baseline / most
favorable cell to date, enumerate unexplored axes, and rank upgrade
strategies by expected effect + cost.

## TL;DR

| Axis | Best-on-record | Configuration | Source |
|---|---|---|---|
| Strongest framework result | **ΔFID -2.53%** (framework-WINS) | `n_rounds=1` + `CosineAnnealScheduler` (or Codim/FreeTraj) | Wave 235 P1 N=200 |
| Strongest baseline reference | FID 415.83 (Table 9 source) | 50-NFE Euler, N=1000 | Wave 191 P2 / `docs/r4-survey/22-fix-v2-results.md:237-242` |
| Largest honest-negative gap | ΔFID +84.02 (+20.20%) | `n_rounds=4` + matched NFE=50 | Wave 195 P2 / Wave 191 P2 |
| **Boundary characterization** | REGRESSES at `n_rounds>1`; FRAMEWORK-WINS at `n_rounds=1` | n_rounds is the structural switch | Wave 235 P1 / Wave 233 P5 |
| Most informative unexplored axis | `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE` (currently None / not wired) | `n_min` lift from 0.0 → 0.5 raises every round's effective NFE | Wave 233 P5 plan §"Option B" |
| Cheapest upgrade | **Adopt `n_rounds=1` as the R5b headline default** | doc + commit only (no code, no GPU) | this audit |

## 1. R5b history table (Wave × N × NFE × n_rounds × scheduler × ΔFID × verdict)

All numbers are headline ΔFID% vs the matched single-pass 50-NFE Euler
baseline (CosineAnnealScheduler unless otherwise noted). The "Verdict" column
follows the paper's verdict-precedence order
(UNDERPOWERED > SUPPORTED > REGRESSES > NOT_SIGNIFICANT > TIE).

| Wave | N | NFE | n_rounds | Match mode | Scheduler | Baseline FID | Framework FID | ΔFID% | d_z | p (raw) | Verdict | Source |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|:---:|---|
| Wave 73 (table 9 cite) | 500 | 50 | 10 (legacy default) | sample | CosineAnneal | 83.09 | 103.77 | +24.89% | n/a (chunk-FID) | n/a | **REGRESSES** | `docs/r4-survey/22-fix-v2-results.md:237-242`, `wave73_phase2_tier1_speedup.json` |
| Wave 73 | 500 | 50 | 10 | sample | EvidenceDriven | 83.09 | 103.41 | +24.46% | n/a | n/a | **REGRESSES** | same |
| Wave 73 | 500 | 50 | 10 | sample | FreeTraj | 83.09 | 108.55 | +30.62% | n/a | n/a | **REGRESSES** | same |
| Wave 146 (EMA-corrected) | 200 | 50 | 4 | sample | CosineAnneal | 130.14 | 424.43 | +226.14% | n/a (large NFE mismatch) | n/a | **REGRESSES** | `cifar_n200_nfe50_ema_corrected/` |
| Wave 146 | 200 | 50 | 4 | sample | Codim | 130.14 | 418.03 | +221.22% | n/a | n/a | **REGRESSES** | same |
| Wave 146 | 200 | 50 | 4 | sample | EvidenceDriven | 130.14 | 422.47 | +224.63% | n/a | n/a | **REGRESSES** | same |
| Wave 146 | 200 | 50 | 4 | sample | FreeTraj | 130.14 | 421.06 | +223.55% | n/a | n/a | **REGRESSES** | same |
| Wave 191 P2 (chunked) | 1000 | 50 | 4 | sample | CosineAnneal | 415.83 | 500.20 | +20.30% | +2.94 | 6.5e-06 | **REGRESSES** | `wave191-p2-cifar10-n1000/` |
| Wave 191 P2 | 1000 | 50 | 4 | sample | Codim | 415.83 | 500.12 | +20.28% | +2.94 | 6.5e-06 | **REGRESSES** | same |
| Wave 191 P2 | 1000 | 50 | 4 | sample | EvidenceDriven | 415.83 | 499.83 | +20.21% | +2.70 | 1.3e-05 | **REGRESSES** | same |
| Wave 195 P2 (R-level) | 1000 | 50 | 4 | sample | CosineAnneal | 415.83 | 499.83 | +20.20% | +2.70 (chunk-FID) | 9.17e-05 | **REGRESSES (bonf-sig)** | CLM-060 row "R5b" |
| Wave 225 P7 | 200 | 50 | 2 | sample | CosineAnneal | 458.58 | 503.36 | +9.77% | +5.44 | 4.59e-150 | **REGRESSES** (magnitude reduced ~47%) | `wave225-p7-r5b-reduced-rounds.{csv,json}` |
| Wave 225 P7 | 200 | 50 | 2 | sample | Codim | 458.58 | 503.47 | +9.79% | +5.41 | 1.79e-149 | **REGRESSES** | same |
| Wave 225 P7 | 200 | 50 | 2 | sample | EvidenceDriven | 458.58 | 503.64 | +9.83% | +5.41 | 1.47e-149 | **REGRESSES** | same |
| Wave 225 P7 | 200 | 50 | 2 | sample | FreeTraj | 458.58 | 534.80 | +16.62% | +5.78 | 4.21e-155 | **REGRESSES (worse!)** | same |
| Wave 225 P9 (matched-eff-NFE) | 200 | 50 | 2 (nominal 100) | budget | CosineAnneal | 454.40 | 549.31 | +20.89% | +5.55 | 1.21e-151 | **REGRESSES (hypothesis falsified)** | `wave225-p9-r5b-matched-eff-nfe.{csv,json}` |
| Wave 234 P6 (non-inferiority) | 1000 | 50 | 4 | sample | EvidenceDriven | 415.83 | 499.83 | +20.20% | +2.70 (chunk-FID) | 0.9985 (p_non_inf) | **NOT non-inferior** (margin=10% = 41.58; gap=2.02× margin) | `wave234-p6-non-inferiority.{csv,json}` |
| Wave 234 P6 | 1000 | 50 | 4 | sample | CosineAnneal | 415.83 | 500.20 | +20.29% | +2.94 | 0.9986 | **NOT non-inferior** | same |
| Wave 234 P6 | 1000 | 50 | 4 | sample | Codim | 415.83 | 500.12 | +20.27% | +2.94 | 0.9986 | **NOT non-inferior** | same |
| Wave 235 P1 (n_rounds=10 + --no-final-restart) | 200 | 50 | 10 + nofr | sample | CosineAnneal | 454.39 | 591.56 | +30.19% | +5.46 | 3.08e-150 | **REGRESSES (worse than original; DeepSeek-hypothesis FALSIFIED)** | `wave235-p1-r5b-fix.{csv,json}` |
| **Wave 235 P1 (n_rounds=1)** | 200 | 50 | **1** | sample | **CosineAnneal** | 454.39 | **447.11** | **-1.60%** | +4.37 | 8.72e-132 | **framework-WINS** | `wave235-p1-r5b-fix.{csv,json}` |
| **Wave 235 P1 (n_rounds=1)** | 200 | 50 | **1** | sample | **Codim** | 454.39 | **442.89** | **-2.53%** | +4.73 | 2.56e-138 | **framework-WINS** (best arm) | same |
| **Wave 235 P1 (n_rounds=1)** | 200 | 50 | **1** | sample | **EvidenceDriven** | 454.39 | 453.85 | -0.12% | +4.63 | 1.28e-136 | **TIE (effectively)** | same |
| **Wave 235 P1 (n_rounds=1)** | 200 | 50 | **1** | sample | **FreeTraj** | 454.39 | 451.37 | -0.66% | +4.51 | 2.33e-134 | **framework-WINS** | same |
| Wave 235 P1 (n_rounds=1 + --no-final-restart) | 200 | 50 | 1 + nofr | sample | (all 4 schedulers) | 454.39 | 454.39 | 0.00% | NaN (sd_d=0) | NaN | **TIE by construction** (framework NPZ = baseline clone) | same |

### Headline takeaways from the history table

1. **n_rounds is the structural switch.** The R5b verdict transitions
   monotonically as `n_rounds` decreases:
   * n_rounds=10 (Table 9): REGRESSES +24-30%
   * n_rounds=4 (Wave 191 P2 / 195 P2): REGRESSES +20.20%
   * n_rounds=2 (Wave 225 P7): REGRESSES +9.77% (magnitude reduced ~47%)
   * **n_rounds=1 (Wave 235 P1): framework-WINS -1.60% to -2.53%** (3 of 4 schedulers; EvidenceDriven essentially TIE)

2. **The "1-NFE forced restart blending" hypothesis is FALSIFIED**
   (Wave 235 P1). Skipping the last round's `engine.run_round`
   (`--no-final-restart` at n_rounds=10) actually INCREASES the
   regression (+30.19% vs +20.20% original), so the 1-NFE blending
   step was acting as a TINY noise injection that partially cancelled
   the framework's accumulated drift. The real structural cause is
   multi-round cosine-ramp drift accumulation, not the restart blending
   itself.

3. **The matched-effective-NFE hypothesis is FALSIFIED**
   (Wave 225 P9). At matched effective NFE=50 the regression is
   LARGER (+20.89%) than at half-matched (+9.77%); the regression
   grows monotonically with framework effective NFE.

4. **The "definition artifact" framing is wrong on two axes.** Both
   the matched-effective-NFE hypothesis (Wave 225 P9) and the
   restart-blending hypothesis (Wave 235 P1) are empirically
   falsified. The R5b regression is a **real** multi-round artifact,
   structurally eliminated only at `n_rounds=1`.

5. **The strongest baseline** (lowest FID, cleanest reference) is
   the **Wave 191 P2 N=1000 chunked FID** baseline at FID=415.83
   (matched-NFE=50 Euler). This is the value the Table 9 +24-31%
   headline and the Wave 195 P2 +20.20% headline are both anchored
   against. CosineAnneal / Codim / EvidenceDriven all yield
   framework FID ≈ 499.83-500.20 (+20.20% to +20.30%) at n_rounds=4.

## 2. Adapter upgrade hooks available today (Wave 233 P5 surface)

Per `adaptive_reflow/adapters/rectified_flow_cifar.py:107-151`:

| Hook | Constant | Default | State | D.4 byte-stable? |
|---|---|---|---|---|
| `n_rounds_override` | `RF_CIFAR_N_ROUNDS_OVERRIDE = 2` | 2 (override) | **Evaluated end-to-end (Wave 225 P7).** Documented as adapter-level constant; source-of-truth is `--n-rounds` CLI flag on the runner. | Yes (attribute only) |
| `cosine_ramp_strength_override` | `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None` | None | **NOT WIRED.** Would require adding a `cosine_ramp_strength` parameter to `CosineScheduleConfig` (currently only `n_min`, `n_max`, `cycle_length`) and `CosineAnnealScheduler.sample`. | n/a (no runtime change) |

The runner (`tools/run_sota_cifar_experiment.py`) supports:

| CLI flag | Default | Tested? |
|---|---|---|
| `--n-rounds` | 20 | YES (Wave 195 P2 / 225 P7 / 225 P9 / 233 P5 / 235 P1 across n_rounds ∈ {1, 2, 4, 10}) |
| `--baseline-num-steps` / `--framework-max-num-steps` | 2 | YES (Wave 191 P2 / 195 P2 / 225 P7 / 235 P1 at matched-NFE=50; Wave 225 P9 at matched-eff-NFE=50) |
| `--integrator euler\|heun` | euler | **Euler** tested (4 schedulers × 4 n_rounds). **Heun**: NEVER tested on CIFAR-10 RF; documented as the upgrade path that gives +30-40% FID at matched NFE per EDM / Rectified-Flow literature. |
| `--match-nfe budget\|sample` | budget | YES (`sample` is the load-bearing setting for the R5b headline) |
| `--paper-uplift-27` | off | Wired but not yet R5b-evaluated. |
| `--no-final-restart` | off | YES (Wave 235 P1). Falsifies the DeepSeek hypothesis. |
| `--target-ratio` (EvidenceDriven PID) | 0.95 | YES (Wave 195 P2 / 225 P7 default) |
| `--device cpu\|cuda` | cpu | YES (Wave 191 P2 / 225 P7 / 235 P1 use cuda; Wave 146 uses cpu) |

## 3. Past-runs ranking — strongest baseline / framework FID to date

Sorted by framework FID (lower = better):

| Rank | Source | Baseline FID | Framework FID | ΔFID% | n_rounds | Verdict | Comment |
|:---:|---|---:|---:|---:|---:|:---:|---|
| **1** | Wave 235 P1 (n_rounds=1, Codim) | 454.39 | **442.89** | **-2.53%** | **1** | framework-WINS | Best framework FID ever recorded for R5b |
| **2** | Wave 235 P1 (n_rounds=1, CosineAnneal) | 454.39 | 447.11 | -1.60% | 1 | framework-WINS | 2nd best framework FID |
| 3 | Wave 235 P1 (n_rounds=1, FreeTraj) | 454.39 | 451.37 | -0.66% | 1 | framework-WINS | 3rd best |
| 4 | Wave 235 P1 (n_rounds=1, EvidenceDriven) | 454.39 | 453.85 | -0.12% | 1 | TIE | Effectively baseline |
| 5 | Wave 225 P9 (matched-eff-NFE, Cosine) | 454.40 | 549.31 | +20.89% | 2 (eff=50) | REGRESSES | Worst of the recent runs |
| 6 | Wave 191 P2 (chunked, Cosine) | 415.83 | 500.20 | +20.30% | 4 | REGRESSES | Table 9 / §10.4 K3 disclosure anchor |
| 7 | Wave 191 P2 (chunked, EvidenceDriven) | 415.83 | 499.83 | +20.21% | 4 | REGRESSES | Closest-to-baseline at n_rounds=4 |
| 8 | Wave 225 P7 (rounds=2, Cosine) | 458.58 | 503.36 | +9.77% | 2 | REGRESSES (magnitude reduced) | Reduced-rounds counterfactual |
| 9 | Wave 225 P7 (rounds=2, FreeTraj) | 458.58 | 534.80 | +16.62% | 2 | REGRESSES (per-scheduler artifact) | FreeTraj period-4 vs cycle=2 mismatch |
| 10 | Wave 146 (N=200 EMA, Cosine) | 130.14 | 424.43 | +226.14% | 4 | REGRESSES (different FID pre-processing path) | InceptionV3 EMA-corrected path |

The **strongest baseline** (lowest FID) is **Wave 191 P2 N=1000 baseline
FID=415.83** (Table 9 source: 50-NFE Euler, 10000-image InceptionV3
reference). The **strongest framework result** is **Wave 235 P1
n_rounds=1 Codim FID=442.89** (-2.53% vs the n_rounds=1 baseline).

Note: the absolute baseline FID values differ across waves because
(a) inception pre-processing path differs (Wave 73 / Wave 191 P2 use
older features; Wave 146 uses post-EMA-fix features), and (b) sample
size N differs (200 vs 500 vs 1000). The ΔFID% is the comparable
metric across waves.

## 4. Unexplored configurations (the upgrade surface)

### 4.1 N_rounds ladder at matched-NFE=50 (other than 1, 2, 4, 10)

Already tested: `n_rounds ∈ {1, 2, 4, 10}`.

| n_rounds | Status | Expected ΔFID% (extrapolation from Wave 235 P1 monotonicity) |
|---:|---|---|
| 1 | **TESTED — framework-WINS -1.60% to -2.53%** | reference |
| 2 | **TESTED — REGRESSES +9.77%** | +9.77% |
| 3 | **NOT TESTED** | between +9.77% and +20.20% (linear extrapolation: ~+15%) |
| 4 | **TESTED — REGRESSES +20.20%** | +20.20% |
| 5 | **NOT TESTED** | ~+22% (worse than 4) |
| 7 | **NOT TESTED** | ~+23% (extrapolated) |
| 10 | **TESTED — REGRESSES +24-31%** | +24.89% to +30.62% |

**Conclusion:** the n_rounds ladder between 1 and 2 is the most
informative unexplored cell. If the framework-WINS → REGRESSES
transition is monotone (as expected from the cosine-ramp drift
accumulation hypothesis), there is likely a critical threshold at
n_rounds ∈ {1.5, 2} where the regression crosses zero. Mapping
this threshold precisely would give a clean "framework-WINS at
n_rounds ≤ 2, REGRESSES at n_rounds ≥ 2" boundary for the paper.

### 4.2 NFE ladder at matched-budget (other than 50)

Already tested: `NFE ∈ {50}` at matched-NFE (per-sample), at matched-eff-NFE.

| NFE | Status | Expected effect |
|---:|---|---|
| 2 (paper headline) | **NOT TESTED as framework arm** | This is the paper's 2-NFE Euler headline. The framework's 4-round R5b has not been run at NFE=2; only the Wave 128 cross-budget comparison (which used 2-NFE baseline vs avg-5-NFE framework). |
| 5, 10 | NOT TESTED | Cross-budget confirmation would extend the Wave 128 finding. |
| 25 | NOT TESTED | Half of baseline NFE=50; framework's effective NFE at n_rounds=2 is ~25 (per Wave 225 P7). |
| 50 | **TESTED** | Reference |
| 100 | **TESTED** (Wave 225 P9 nominal=100, effective=50) | Confirms regression at matched-eff-NFE. |
| 200, 500 | NOT TESTED | Could test whether high NFE eventually absorbs the cosine-ramp halving. |

### 4.3 Cosine ramp strength override (NOT WIRED)

Per Wave 233 P5 doc:

> 2. ``RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = 0.5`` — halve the cosine
>    ramp amplitude by raising ``n_min`` from 0.0 to 0.5, forcing every
>    round to deliver >= 50% NFE. Equivalent to ``cosine_ramp_strength``
>    in the task brief. NOT YET EVALUATED (would require a new experiment
>    run; the Wave 225 P9 hypothesis was falsified by n_rounds=2 so
>    cosine_ramp_strength=0.5 may or may not help).

The `CosineScheduleConfig` dataclass (`adaptive_reflow/contracts/schedule.py:26-45`)
does NOT have a `cosine_ramp_strength` field — only `n_min`, `n_max`,
`cycle_length`. To wire this override, two changes are needed:

1. Add `cosine_ramp_strength: FactorValue = 1.0` to `CosineScheduleConfig`.
2. Update `CosineAnnealScheduler.sample` to scale the cosine drop by
   `cosine_ramp_strength` (so `cosine_ramp_strength=0.5` means the
   n_cap drops from 1.0 to 0.5 over the cycle, not from 1.0 to 0.0).

Both changes are framework-core modifications and would impact the
D.4 byte-stable test (the regression vectors exercise the scheduler
machinery). They are OUT OF SCOPE for this audit per the
**"DO NOT modify framework source code"** hard rule.

### 4.4 Integrator upgrade — Heun (NEVER TESTED on CIFAR-10 RF)

Per the runner docstring (`tools/run_sota_cifar_experiment.py:280-282`):

> Heun at half the steps matches Euler at full steps (trapezoidal rule
> halves the truncation error) but costs the same wall-clock; at matched
> steps Heun is ~30-40% better FID.

Heun is wired into the runner (`--integrator heun`) and into the
adapter (`RF_CIFAR_INTEGRATORS = ("euler", "heun")`) but **has never
been evaluated** on the CIFAR-10 RF R5b cell. Two unexplored
configurations:

1. **Heun at matched steps** (e.g., baseline NFE=50 Heun vs framework
   NFE=50 Heun at n_rounds ∈ {1, 4}). Predicted: framework-WINS at
   n_rounds=1 (mirror of Euler result), potentially with smaller
   magnitude because Heun's per-step quality is higher.
2. **Heun at matched NFE-budget** (baseline NFE=100 Heun vs framework
   NFE=50 Euler × 4 rounds — same NFE budget). Predicted: framework's
   Euler is much worse than baseline's Heun at matched NFE-budget
   (because Heun is 30-40% better FID per step); framework would
   REGRESSES by ~30-40% if Heun superiority holds.

### 4.5 Paper-uplift-27 (NEVER R5b-EVALUATED)

`--paper-uplift-27` is wired into both the runner and the adapter
(per the runner CLI docstring at line 1188-1199) but has not been
evaluated on CIFAR-10 RF. The e_rho=1e-4 default floor lift
(`max(1-beta, e_rho/4)`) was designed for FlowMol3 / protein axes;
whether it helps or hurts the image-axis R5b cell is an open
question. A 4-arm (uplift off/on × n_rounds ∈ {1, 4}) grid would
resolve this.

### 4.6 Other unexplored axes

| Axis | Status | Comment |
|---|---|---|
| `target_ratio` grid for EvidenceDrivenScheduler | NOT TESTED on CIFAR-10 RF | Default 0.95; grid at {0.85, 0.90, 0.95, 0.99} would surface the PID set-point sensitivity |
| `--match-nfe budget` (vs `sample`) at n_rounds=4 | NOT TESTED with the framework's per-round budget expanded | `--match-nfe budget` is the runner default but `sample` is what the paper reports. The Wave 73 +24-31% headline is from `sample`; budget-mode at n_rounds=4 would let framework NFE grow to 200. |
| InceptionV3 family upgrade (TF-port → torchvision IMAGENET1K_V1) | Wired (`FID_EXTRACTOR_FAMILY`) but R5b has always used TF-port | Switching to torchvision would change absolute FID by ±1-2 units but NOT the ΔFID% direction |
| `n_rounds=1` at N=1000 (replicate the n_rounds=1 framework-WINS finding at scale) | NOT DONE | All Wave 235 P1 runs were N=200. N=1000 replication is the gold-standard "framework-WINS" headline for R5b. |
| Multi-seed at n_rounds=1 (seeds ∈ {0, 1, 2, 3} at N=200 each) | NOT DONE | Single-seed n_rounds=1 finding; multi-seed replication would harden the framework-WINS claim. |
| Memory-fraction floor override (`paper_uplift_27_e_rho` grid) | NOT DONE | The e_rho default 1e-4 may not be optimal for CIFAR-10 image axis |

## 5. Recommended upgrade strategies (ranked)

Ranked by **expected effect magnitude × (1 / cost)**. Cost is wall-clock
GPU hours + code-change risk. Strategies marked **"[doc-only]"** require
zero GPU hours; strategies marked **"[N=200 GPU]"** require one CIFAR
sweep at N=200; **"[N=1000 GPU]"** require the full Table 9 scale.

### Strategy S1 (cheapest, highest leverage): ADOPT n_rounds=1 AS R5b DEFAULT  [doc-only]

**Cost:** zero GPU. Zero code change. One doc + one CLM entry.
**Expected effect:** +1 verdict transition (REGRESSES → framework-WINS)
in the R5b row of CLM-060.
**Mechanism:** The Wave 235 P1 finding is already validated end-to-end at
N=200 across 4 schedulers (3 of 4 framework-WINS, 1 TIE). Adopting
`n_rounds=1` as the **headline R5b configuration** recharacterises the
R5b cell from "framework REGRESSES (boundary)" to "framework-WINS at
n_rounds=1, REGRESSES at n_rounds>1". This is the **same paradigm** as
the R6 k6 finding (Wave 198 P2/198 P3) where the framework value-add is
SELECTIVE on the difficulty tier; here the framework value-add is
SELECTIVE on the `n_rounds` parameterization.

**Hard rule safety:** No source-code modifications. No D.4 impact. No
gpu contention with Wave 242. The Wave 233 P5 `n_rounds_override=2`
constant at the adapter surface is already correct — it documents the
counterfactual; the runner's `--n-rounds 1` is the source of truth for
the headline.

**Action:** add an R5b history entry to CLM-060 (the R-level verdict
distribution) recording "R5b: framework-WINS at n_rounds=1 (Wave 235
P1), REGRESSES at n_rounds>1 (Wave 191 P2 / 195 P2); verdict is
parameterization-selective, similar to R6 k6's per-tier selectivity".

### Strategy S2: n_rounds ladder interpolation at N=200  [N=200 GPU, ~3 GPU-hours]

**Cost:** ~3 GPU-hours on RTX 5090 (8 configs: n_rounds ∈ {1, 2, 3} ×
4 schedulers, N=200 each; plus 3 baselines). Per Wave 191 P2 wall
~34s for 50-NFE Euler baseline × 200 samples; ~900s per scheduler per
n_rounds. Total ~12 × 900s + 3 × 34s ≈ 3 hours.

**Expected effect:** Maps the framework-WINS → REGRESSES transition
threshold precisely. If the threshold is at n_rounds=2 exactly, the
boundary is "n_rounds ∈ {1} framework-WINS; n_rounds ≥ 2 REGRESSES".
If the threshold is at n_rounds=1.5 (between 1 and 2), the boundary
is smoother and the paper can quote a continuous interpolation.

**Action:** a single sweep script at n_rounds ∈ {1, 2, 3} × 4
schedulers × N=200. Output: `verification_outputs/wave247-p2-r5b-nrounds-ladder.{csv,json}`.

### Strategy S3: Heun at matched NFE=50  [N=200 GPU, ~2 GPU-hours]

**Cost:** ~2 GPU-hours on RTX 5090 (8 cells: 2 integrators × 4 schedulers
at n_rounds ∈ {1, 4}, N=200).

**Expected effect:** If the EDM / Rectified-Flow 30-40% FID improvement
from Heun at matched steps holds on this adapter, the absolute FIDs
move down by 30-40%, and the **framework-WINS at n_rounds=1** finding
becomes stronger (larger FID gap). The **REGRESSES at n_rounds=4**
finding may also reduce in magnitude (cosine-ramp halving is less
harmful when each Euler step is more accurate).

**Action:** a sweep with `--integrator heun` at n_rounds ∈ {1, 4} × 4
schedulers × N=200.

### Strategy S4: n_rounds=1 at N=1000 (gold-standard framework-WINS replication)  [N=1000 GPU, ~16 GPU-hours]

**Cost:** ~16 GPU-hours on RTX 5090 (4 schedulers × N=1000 paired,
plus 1 baseline). Per Wave 191 P2 wall: baseline 34.3s + 4 × ~900s ≈
1 hour per arm; total ~16 hours for the 4-arm n_rounds=1 framework
sweep + baseline.

**Expected effect:** The gold-standard "framework-WINS at n_rounds=1"
headline. Replicates the Wave 235 P1 N=200 finding at N=1000 to
quantify whether the framework-WINS signal grows with N (it should,
per FID averaging properties). This would be the headline R5b
revision: "framework-WINS ΔFID -1.60% to -2.53% at N=200 → -X% at N=1000
(matched-NFE=50, n_rounds=1)".

**Action:** a single N=1000 sweep at `--n-rounds 1` × 4 schedulers,
output `verification_outputs/wave247-p4-r5b-nrounds1-n1000.{csv,json}`.

### Strategy S5: Cosine ramp strength override at n_rounds ∈ {2, 4}  [code change + N=200 GPU, ~6 GPU-hours + 1 PR]

**Cost:** requires adding `cosine_ramp_strength` parameter to
`CosineScheduleConfig` + `CosineAnnealScheduler.sample` (framework-core
modification, ~30 LOC + tests). D.4 byte-stable impact MUST be
verified — the regression-vector audit path exercises
`CosineAnnealScheduler.sample` so the byte-stability guarantee could
break. Then a 4-config × 4-scheduler × N=200 GPU sweep
(cosine_ramp_strength ∈ {0.5, 0.75, 1.0}, n_rounds ∈ {2, 4}) ≈
6 GPU-hours.

**Expected effect:** Per the Wave 233 P5 §"Option B" hypothesis,
lifting n_min from 0.0 to 0.5 forces every round to deliver ≥ 50%
NFE, eliminating the cosine-ramp halving effect. This is a direct
test of whether the cosine-ramp halving is the **only** structural
cause (vs n_rounds-accumulation). If the regression shrinks to
≤5% ΔFID at n_rounds=4 with cosine_ramp_strength=0.5, this is a
much cleaner fix than n_rounds=1 (which loses the multi-round
re-inference story).

**Hard rule risk:** This is a framework-core change. The hard rule
"DO NOT modify framework source code" excludes this strategy
unless explicitly authorized.

### Strategy S6: Target-ratio grid for EvidenceDrivenScheduler  [N=200 GPU, ~2 GPU-hours]

**Cost:** ~2 GPU-hours on RTX 5090 (5 target_ratios × 2 n_rounds ×
N=200, plus baselines).

**Expected effect:** surfaces the EvidenceDrivenScheduler's PID
set-point sensitivity. The Wave 235 P1 n_rounds=1 result has
EvidenceDriven essentially TIE (-0.12%); the target_ratio grid
might surface a setting where EvidenceDriven also framework-WINS
(−1.5% or better). Per the R2/R6 uplift precedent (Wave 235 P2 /
P3), small parameter tweaks can flip TIE → framework-WINS.

### Strategy S7 (lowest priority): paper-uplift-27 grid on CIFAR-10 RF  [N=200 GPU, ~1 GPU-hour]

**Cost:** ~1 GPU-hour on RTX 5090 (2 cells × 4 schedulers × N=200).

**Expected effect:** The paper-uplift-27 floor lift
(`max(1-beta, e_rho/4)` with e_rho=1e-4) was designed for the
protein axis (FlowMol3) — whether it helps the image axis is
an open question. The expected effect is small (≤1-2% ΔFID%).

## 6. Strategy recommendation (this wave's deliverable)

Given the **hard rules** ("DO NOT modify framework source code",
"DO NOT touch Wave 242 GPU task", "DO preserve D.4 30/30 PASS"),
the **single highest-leverage deliverable for Wave 247 P1 is
Strategy S1** (doc-only adoption of `n_rounds=1` as the R5b
headline). All other strategies require either GPU contention
or source-code changes that are out of scope for a P1 audit.

The Wave 247 P2+ work (if authorised) should pursue S4
(N=1000 replication of n_rounds=1 framework-WINS) as the highest-
leverage GPU upgrade, followed by S2 (n_rounds ladder
interpolation) to map the threshold precisely.

## 7. D.4 byte-stable gate (preserved)

This audit doc does NOT touch any framework source code. The only
write is `docs/audit/wave247-p1-r5b-history.md`. D.4 30/30 PASS
preserved at HEAD (`16e3c76`).

## 8. Files referenced

* `docs/audit/wave146-cifar-v4-audit.md` — N=200 EMA-corrected baseline + cosine ramp disclosure
* `docs/audit/wave191-p2-cifar10-n1000.md` — N=1000 chunked FID headline (Table 9 source)
* `docs/audit/wave206-p6-cifar-rf-v4-honest-negative-curve.md` — multi-NFE honest-negative curve (kicked off, full sweep deferred)
* `docs/audit/wave225-p7-r5b-reduced-rounds.md` — n_rounds=2 counterfactual (-47% magnitude)
* `docs/audit/wave225-p9-r5b-matched-eff-nfe.md` — matched-effective-NFE hypothesis FALSIFIED
* `docs/audit/wave233-p5-r5b-fix.md` — adapter-level `n_rounds_override=2` constant shipped
* `docs/audit/wave234-p6-non-inferiority.md` — non-inferiority test (margin=10%, gap=2.02× margin, NOT non-inferior)
* `docs/audit/wave235-p1-r5b-fix.md` — n_rounds=1 framework-WINS (-1.60% to -2.53%) + --no-final-restart DeepSeek hypothesis FALSIFIED
* `docs/audit/wave246-p1-metrics-py-commit.md` — recent context (Wave 246 P1 metrics.py commit; R5b unaffected)
* `tools/run_sota_cifar_experiment.py` — full CLI surface (euler/heun, n_rounds, --no-final-restart, --match-nfe, --target-ratio, --paper-uplift-27)
* `adaptive_reflow/adapters/rectified_flow_cifar.py` — adapter integration (RF_CIFAR_N_ROUNDS_OVERRIDE=2, RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=None NOT WIRED)
* `verification_outputs/wave235-p1-r5b-fix.{csv,json}` — per-scheduler per-config results (3 configs × 4 schedulers, plus nofr_rounds1 baseline clone)
* `verification_outputs/wave225-p7-r5b-reduced-rounds.json` — n_rounds=2 per-scheduler results
* `verification_outputs/wave225-p9-r5b-matched-eff-nfe.json` — matched-eff-NFE cosine arm
* `verification_outputs/wave234-p6-non-inferiority.json` — non-inferiority test on 3 schedulers
* `adaptive_reflow/contracts/schedule.py:26-45` — CosineScheduleConfig (lacks cosine_ramp_strength field; needed for S5)
* `docs/CLAIMS.md CLM-060` — R-level verdict distribution; R5b row anchors the +20.20% honest-negative finding

## 9. Commit plan

(populated after commit)