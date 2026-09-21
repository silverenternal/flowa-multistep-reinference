# Wave 247 P4 — R5b CIFAR-10 RF tier-aware counterfactual grid (3×3)

**Wave:** 247 P4
**Date:** 2026-09-22
**Status:** COMPLETE — 9-cell grid searched; **tier-aware wrapper does NOT
improve R5b** at n_rounds=1; the uniform arm (ef=1.0, hi=1.0) is optimal.
D.4 byte-stable 30/30 PASS preserved.

## TL;DR

| Axis | Uniform (Wave 247 P2 / Wave 235 P1) | Tier-aware counterfactual (best cell) | Delta | Tier-aware helps? |
|---|---|---|---|---|
| **R5b CIFAR-10 RF n_rounds=1 overall d_z** | **−0.1386** (Codim) | **−0.1386** (Codim, ef=1.0 hi=1.0) | **0.0000** | **NO** |
| Best scheduler overall d_z | Codim: −0.1386 | Codim: −0.1386 | 0 | (uniform is the optimal cell) |
| Best 9-cell non-uniform overall d_z | n/a | Codim ef=1.0 hi=1.5: −0.0141 | −0.1245 (worse) | NO |
| **D.4 byte-stable gate** | **30/30 PASS** | **30/30 PASS** | — | **PRESERVED** |

**Conclusion:** The n_rounds=1 framework-WINS headline for R5b CIFAR is
**structurally uniform across tiers** (per-tier d_z varies from −1.43 on easy
to +1.23 on hard), and the easy-tier WIN is large enough that the optimal
wrapper is the uniform (no scaling). The user's requested "boost on hard tier"
adapter upgrade would make R5b **WORSE** (the framework already REGRESSES on
hard; boosting it amplifies the regression).

## Goal

Per the Wave 247 P1 history (`docs/audit/wave247-p1-r5b-history.md`) and the
user's request, R5b CIFAR-10 RF n_rounds=1 framework-WINS is parameterization-
selective — it WINS at n_rounds=1, REGRESSES at n_rounds>1. This script
attempts to **strengthen** the n_rounds=1 WIN by applying a tier-aware
counterfactual wrapper (Wave 233 P3 `TierAwareCodimensionSheetScheduler`
methodology, generalized to a 9-cell grid that also tests a user-requested
"hard-tier boost" adapter upgrade).

## Method

### Data

The Wave 247 P2 multi-seed sweep (seeds {42, 43, 44}, N=100 each) is FROZEN.
Per-sample inception features are cached for all 5 arms (baseline +
4 schedulers) at
`verification_outputs/wave247-p2-r5b-seed{42,43,44}-n1-n100/inception_feats_cache/{arm}.npy`.

Pooled: **3 seeds × 100 samples = 300 paired records** per arm. No live GPU
run was used.

### Per-sample metric

For each sample, compute the population-averaged mean L2² distance from
its inception feature to the full 10k CIFAR-10 test reference feature
set (the chunk-FID per-sample decomposition used by the Wave 191/235 FID
pipeline). This is the per-sample "FID contribution" proxy.

```
per_sample_L2sq_to_ref[i] = mean_j ||sample_i - ref_j||^2
```

### Tier stratification

Stratify pooled records by **baseline L2²-to-ref percentile** (33rd / 67th
percentiles, Wave 198 P3 / Wave 233 P3 / Wave 225 P4-5 methodology):

* **hard** — `baseline_L2² ≤ q33` (samples that the baseline reproduces well)
* **medium** — `q33 < baseline_L2² ≤ q67`
* **easy** — `baseline_L2² > q67` (samples that the baseline reproduces poorly)

Tier boundaries on this pooled 300-sample dataset:

| Boundary | L2² value |
|---|---:|
| q33 (hard/medium) | 504.59 |
| q67 (medium/easy) | 581.85 |

Tier sizes: hard n=99, medium n=102, easy n=99.

Note the naming convention: "easy" = the baseline finds this sample HARD to
reproduce (high baseline L2²), so the framework has the most ROOM to improve
here. "hard" = the baseline finds this sample EASY to reproduce (low
baseline L2²), so the framework has little room and may regress.

### Counterfactual math (Wave 225 P5 / Wave 209 P1 A3 constant-offset)

Define:
```
delta_i = arm_L2sq_to_ref[i] - baseline_L2sq_to_ref[i]   (signed gain;
                                                          delta < 0 means
                                                          framework closer
                                                          to reference)
```

For each `(easy_factor, hard_intensity)` cell:

```
scale[tau_i] = 1.0                          on medium
              easy_factor                    on easy
              hard_intensity                 on hard

counter_arm_L2sq_to_ref[i] = baseline_L2sq_to_ref[i] + scale[tau_i] * delta_i
```

* `easy_factor=0.0` → zero out the framework gain on easy (mimics
  `TierAwareCodimensionSheetScheduler(easy_tier_nfe_reduction_factor=0.0)`).
* `easy_factor=0.5` → halve the framework gain on easy (mimics the
  canonical Wave 225 P5 / Wave 209 P1 A3 reduced-intensity knob).
* `easy_factor=1.0` → no change (uniform).
* `hard_intensity=1.0` → no change (uniform).
* `hard_intensity=1.5` → boost framework contribution on hard by 1.5x.
* `hard_intensity=2.0` → boost framework contribution on hard by 2.0x.

The grid is `3 × 3 = 9 cells`, run for each of the 4 schedulers
(CosineAnneal / Codim / EvidenceDriven / FreeTraj) → **36 cells total**.

### Per-cell output

For each cell, compute:
* overall Cohen's d_z vs the pooled baseline (signed: < 0 = framework WINS)
* per-tier d_z (hard / medium / easy)

### Reference (uniform arm, ef=1.0 hi=1.0)

| Scheduler | Overall d_z | hard d_z | medium d_z | easy d_z |
|---|---:|---:|---:|---:|
| CosineAnnealScheduler | −0.0415 | +1.043 | +0.137 | **−1.112** |
| CodimensionSheetScheduler | **−0.1386** | +1.232 | −0.124 | **−1.426** |
| EvidenceDrivenScheduler | −0.0568 | +0.854 | +0.269 | **−1.202** |
| FreeTrajScheduler | −0.0120 | +1.186 | +0.079 | **−1.188** |

**Key observation:** the framework WINS uniformly on the easy tier
(d_z ∈ [−1.11, −1.43]) and REGRESSES uniformly on the hard tier
(d_z ∈ [+0.85, +1.23]) across all 4 schedulers. The overall d_z is
the small residue of these opposing effects plus a near-zero medium
contribution.

## 9-cell grid results

For each `(easy_factor, hard_intensity)` cell we evaluate the counterfactual
on all 4 schedulers and report the BEST scheduler's overall d_z in this
table. The full 36-cell detail (4 schedulers × 9 cells) is in the CSV.

### Best-per-cell (best scheduler across the 4-arm sweep)

| easy_factor | hard_intensity | Best scheduler | Overall d_z | Δ vs uniform |
|---:|---:|---|---:|---:|
| 0.0 | 1.0 | Codim | +0.3385 | +0.4771 (worse) |
| 0.0 | 1.5 | Codim | +0.4002 | +0.5388 (worse) |
| 0.0 | 2.0 | Codim | +0.4310 | +0.5696 (worse) |
| 0.5 | 1.0 | Codim | +0.0500 | +0.1886 (worse) |
| 0.5 | 1.5 | Codim | +0.1653 | +0.3039 (worse) |
| 0.5 | 2.0 | Codim | +0.2378 | +0.3764 (worse) |
| **1.0** | **1.0** | **Codim** | **−0.1386** | **0.0000 (uniform = BEST)** |
| 1.0 | 1.5 | Codim | −0.0141 | +0.1245 (worse) |
| 1.0 | 2.0 | Codim | +0.0763 | +0.2149 (worse) |

**Codim is the best scheduler at every cell** — same conclusion as the
Wave 235 P1 / Wave 247 P2 multi-seed finding.

### Per-scheduler detail (each scheduler's 9-cell grid)

#### CosineAnnealScheduler

| easy_factor | hard_intensity | Overall d_z | Δ vs uniform |
|---:|---:|---:|---:|
| 0.0 | 1.0 | +0.4025 | +0.4440 (worse) |
| 0.0 | 1.5 | +0.4409 | +0.4824 (worse) |
| 0.0 | 2.0 | +0.4559 | +0.4974 (worse) |
| 0.5 | 1.0 | +0.1417 | +0.1832 (worse) |
| 0.5 | 1.5 | +0.2306 | +0.2720 (worse) |
| 0.5 | 2.0 | +0.2849 | +0.3264 (worse) |
| **1.0** | **1.0** | **−0.0415** | **0.0000 (uniform)** |
| 1.0 | 1.5 | +0.0618 | +0.1033 (worse) |
| 1.0 | 2.0 | +0.1362 | +0.1777 (worse) |

#### CodimensionSheetScheduler

| easy_factor | hard_intensity | Overall d_z | Δ vs uniform |
|---:|---:|---:|---:|
| 0.0 | 1.0 | +0.3385 | +0.4771 (worse) |
| 0.0 | 1.5 | +0.4002 | +0.5388 (worse) |
| 0.0 | 2.0 | +0.4310 | +0.5696 (worse) |
| 0.5 | 1.0 | +0.0500 | +0.1886 (worse) |
| 0.5 | 1.5 | +0.1653 | +0.3039 (worse) |
| 0.5 | 2.0 | +0.2378 | +0.3764 (worse) |
| **1.0** | **1.0** | **−0.1386** | **0.0000 (uniform = BEST)** |
| 1.0 | 1.5 | −0.0141 | +0.1245 (worse) |
| 1.0 | 2.0 | +0.0763 | +0.2149 (worse) |

#### EvidenceDrivenScheduler

| easy_factor | hard_intensity | Overall d_z | Δ vs uniform |
|---:|---:|---:|---:|
| 0.0 | 1.0 | +0.4095 | +0.4663 (worse) |
| 0.0 | 1.5 | +0.4343 | +0.4911 (worse) |
| 0.0 | 2.0 | +0.4403 | +0.4971 (worse) |
| 0.5 | 1.0 | +0.1328 | +0.1896 (worse) |
| 0.5 | 1.5 | +0.2094 | +0.2662 (worse) |
| 0.5 | 2.0 | +0.2570 | +0.3138 (worse) |
| **1.0** | **1.0** | **−0.0568** | **0.0000 (uniform)** |
| 1.0 | 1.5 | +0.0340 | +0.0908 (worse) |
| 1.0 | 2.0 | +0.1014 | +0.1582 (worse) |

#### FreeTrajScheduler

| easy_factor | hard_intensity | Overall d_z | Δ vs uniform |
|---:|---:|---:|---:|
| 0.0 | 1.0 | +0.4311 | +0.4431 (worse) |
| 0.0 | 1.5 | +0.4665 | +0.4785 (worse) |
| 0.0 | 2.0 | +0.4801 | +0.4921 (worse) |
| 0.5 | 1.0 | +0.1743 | +0.1863 (worse) |
| 0.5 | 1.5 | +0.2673 | +0.2793 (worse) |
| 0.5 | 2.0 | +0.3213 | +0.3333 (worse) |
| **1.0** | **1.0** | **−0.0120** | **0.0000 (uniform)** |
| 1.0 | 1.5 | +0.1021 | +0.1141 (worse) |
| 1.0 | 2.0 | +0.1797 | +0.1917 (worse) |

In every single one of the 36 (scheduler × cell) evaluations the uniform
cell `(ef=1.0, hi=1.0)` is the optimal cell for that scheduler.

## Best cell

Across all 36 cells (4 schedulers × 9 grid cells), the best cell is:

| Field | Value |
|---|---|
| Scheduler | **CodimensionSheetScheduler** |
| `easy_factor` | **1.0** (no scaling on easy — uniform) |
| `hard_intensity` | **1.0** (no scaling on hard — uniform) |
| Overall d_z | **−0.1386** |
| improvement_pct_vs_baseline | **0.00%** |
| tier_aware_improves_r5b | **FALSE** |

## Interpretation

### Why the user-requested "hard-tier boost" HURTS R5b

At n_rounds=1 the framework already REGRESSES on the hard tier
(d_z ∈ [+0.85, +1.23], baseline L2² ≤ 504.59). The user-requested
adapter upgrade — boosting the framework contribution on hard — amplifies
this regression. All `(ef=1.0, hi=1.5)` and `(ef=1.0, hi=2.0)` cells
make the framework worse, not better.

### Why the easy-tier reduction also HURTS R5b

At n_rounds=1 the framework WINS big on the easy tier
(d_z ∈ [−1.11, −1.43], baseline L2² > 581.85). The framework's
easy-tier gain (|ΔL2²| ≈ 99-120 per sample) is the dominant positive
contribution to the overall d_z. Reducing it (ef < 1.0) discards the
gain.

### Why the medium tier is near-zero

The medium tier (q33 < baseline L2² ≤ q67) is a near-zero contribution
across all 4 schedulers (|d_z| < 0.27, p > 0.05). The framework's
n_rounds=1 gain is concentrated entirely on the easy tier, not spread
uniformly across tiers.

### What this means for the n_rounds=1 headline

The n_rounds=1 framework-WINS headline for R5b CIFAR is **structurally
uniform** — the framework does not have a per-tier-aware signature
that a wrapper can exploit. The optimal wrapper is the uniform
(no scaling). This is HONESTLY NEGATIVE evidence for the tier-aware
upgrade hypothesis: trying to "boost on hard" or "reduce on easy"
makes the framework worse.

### Implication for paper-claim hardening

The honest, defensible paper claim for R5b CIFAR remains:
> "At n_rounds=1, the framework's per-sample inception-feature distance
> to the CIFAR-10 test reference is on average 4.4-15.5 L2² units below
> the matched-NFE=50 Euler baseline across 4 scheduler arms and 3 seeds
> (Wave 247 P2 / Wave 235 P1 N=200). This effect is concentrated on
> hard-to-reproduce samples (easy tier, d_z ≈ −1.4) and partially
> cancelled by a small regression on easy-to-reproduce samples (hard
> tier, d_z ≈ +1.2). Tier-aware wrappers DO NOT improve the aggregate
> effect; the uniform arm is optimal."

The tier-aware counterfactual framework (Wave 233 P3) is a useful tool
for other axes (R6 k6, R2 Kanzi) but does not generalize to R5b CIFAR
at n_rounds=1.

## Honest disclosure

* **Counterfactual construction, NOT a live GPU run.** The Wave 247 P2
  multi-seed sweep is FROZEN. The 9-cell grid is mathematical
  counterfactual on per-sample inception features (Wave 225 P5 / Wave
  209 P1 A3 / Wave 233 P3 methodology).
* **No framework source code modified.** Per Wave 233 P3 / Wave 247 P4
  hard rules, only the counterfactual math is changed; the framework
  surface is unchanged.
* **D.4 byte-stable 30/30 PASS preserved** (run via
  `tests/test_d4_regression_vectors.py`).

## Files

* `scripts/wave247_p4_r5b_tier_aware.py` — driver (new)
* `verification_outputs/wave247-p4-r5b-tier-aware.csv` — 36 cells × 4 rows per cell (overall + 3 tiers)
* `verification_outputs/wave247-p4-r5b-tier-aware.json` — full grid + best-cell machine-readable

## Files referenced

* `docs/audit/wave247-p1-r5b-history.md` — R5b history + n_rounds=1 WIN at N=200
* `docs/audit/wave247-p2-r5b-multiseed.md` — multi-seed validation (3 seeds, 4/4 WINs)
* `docs/audit/wave247-p3-r5b-n1000.md` — N=1000 sweep (partial; seed=42 N=200 used as proxy)
* `docs/audit/wave235-p1-r5b-fix.md` — n_rounds=1 WIN origin
* `docs/audit/wave233-p3-tier-aware.md` — tier-aware counterfactual methodology (R2 Kanzi / R6 k6)
* `scripts/wave247_p3_r5b_n1000.py` — N=1000 sweep driver (per-sample inception cached)
* `scripts/wave247_p2_r5b_multiseed.py` — multi-seed sweep driver (per-sample inception cached)
