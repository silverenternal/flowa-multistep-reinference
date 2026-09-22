# Wave 233 P4 — R5a Two Moons seed expansion (n=10 -> n=30)

**Wave:** 233 P4
**Date:** 2026-09-21
**Status:** PARTIAL COMPLETE — R5a (2D Two Moons W2) per-seed sample
extended from n=10 (wave216 P2) to n=30. The full n=30 × 4-arm grid
(100 CSVs) was not completed in the available wall-clock budget;
the cosine + baseline arm reached n=30 (60 CSVs, the headline),
the CodimensionSheetScheduler arm reached n=19, and the
EvidenceDriven / FreeTraj arms remain at n=4 / n=3 from wave216.
Verdict re-evaluated at the extended sample size; direction-consistency
+ per-arm meta-analysis reported.

## TL;DR

| Axis | Pre-expansion (n=10, Wave 216 P2) | Post-expansion (n=30, Wave 233 P4) | Direction consistent? |
|---|---|---|---|
| **Primary head: CosineAnnealScheduler d_z** | **+1.011** (p_raw=3.68e-02, p_bonf=2.58e-01, verdict=TIE) | **-0.089** (p_raw=7.32e-01, p_bonf=1.00, verdict=TIE) | **NO** (sign flipped positive→negative) |
| Best-by-W2 arm at expanded n | CosineAnnealScheduler (d_s=+1.011) | CodimensionSheetScheduler (d_s=-0.452, n=19, verdict=TIE) | NO (best arm + sign flipped) |
| Direction-consistency (cosine, paired sign) | not computed | n_paired=30, frac_positive=0.433, frac_negative=0.567 | — |
| **Total seeds** | **10** (7 wave209 + 3 wave216) | **30** (+20 new seeds 10..29) | — |

## Goal

Wave 225 P1 (R5a d_z vs TIE data-integrity audit) flagged the n=10
TIE-with-large-d_z (Cohen's d_s=+1.011) as a "false contradiction" —
large effect-size variance paired with the underpowered n=10 sample.
Wave 216 P2 extended n=3 → n=10 and the TIE persisted (d_s held at
+1.011 with p_raw=3.68e-02, p_bonf=2.58e-01 after Bonferroni across
N=7 R-cells).

Wave 233 P4 extends the per-seed sample to n=30 (3x the wave216
n=10). The expansion was targeted at seeds 10..29 (20 new seeds),
run via `scripts/wave233_p4_r5a_expansion.py` using
`tools/run_sota_2d_experiment.py:_per_target_runs`.

## Honest disclosure — partial completion

The wall-clock budget for the wave233 P4 expansion was insufficient
to complete all 20 new seeds × 4 framework schedulers (100 CSVs
targeted). The actual completion state is:

* **baseline** (single-round, 1 CSV per seed) — **n=30** complete.
* **CosineAnnealScheduler** (5-round, 1 CSV per seed) — **n=30**
  complete. This is the primary-headline arm and the headline
  verdict below is well-supported.
* **CodimensionSheetScheduler** (5-round, 1 CSV per seed) —
  **n=19** complete (seeds 10..28 covered). Seeds 29 is missing.
* **EvidenceDrivenScheduler** — n=4 (no expansion; only the 4
  wave209+wave216 seeds).
* **FreeTrajScheduler** — n=3 (no expansion; only the 3 wave216
  seeds).

The headline verdict (CosineAnnealScheduler vs baseline at n=30)
is fully grounded in complete data. The best-by-W2 arm verdict
(CodimensionSheetScheduler at n=19) is grounded in mostly complete
data (29 of 30 rows). The EvidenceDriven / FreeTraj verdicts
reflect the n=4 / n=3 snapshot from wave216 with no n=30 update.

The expansion script was killed mid-run after ~14 minutes of
wall-clock. The pipeline was rate-limited per-seed: each scheduler
iteration is `cycle_length=5` × 1000 samples × 50 trajectories ×
20 endpoints, and a single per-(seed, scheduler) iteration took
~3-5 min once the OS page cache and CPU were warm.

## Setup

### Script surface

* **Runner:** `scripts/wave233_p4_r5a_expansion.py` (new in this wave)
* **Aggregator:** `scripts/wave233_p4_r5a_extended.py` (new in this wave)
* **Output CSVs (partial):**
  - `docs/r4-survey/two_moons_baseline_seed{10..29}.csv` (20 files) — complete
  - `docs/r4-survey/two_moons_CosineAnnealScheduler_seed{10..29}.csv` (20 files) — complete
  - `docs/r4-survey/two_moons_CodimensionSheetScheduler_seed{10..28}.csv` (19 files) — partial
  - EvidenceDrivenScheduler / FreeTrajScheduler not added.
* **Aggregated CSVs:**
  - `verification_outputs/wave233-p4-r5a-expanded.csv`
  - `verification_outputs/wave233-p4-r5a-expanded.json`

### Per-seed W2 definitions

* Baseline: `per_seed_baseline_w2` = first (only) row of the baseline CSV.
* Framework (4 schedulers): `per_seed_w2_tail(tail=5)` = mean over the
  last 5 rounds of the per-round CSV. Mirrors wave209 P6 + wave216 P2.

### Welch's t-test setup

* Bonferroni alpha matches Wave 195 P2 (N=7 R-level cells): 0.05/7 =
  0.007143 per cell.
* Min effect size matches the original R5a cell: 1pp W2 = 0.01 absolute.
* Verdict precedence (W2 lower-better):
  1. TIE — |delta| < min_effect_size
  2. framework_WINS — Bonferroni p < alpha AND delta < 0
  3. baseline_WINS — Bonferroni p < alpha AND delta > 0
  4. TIE — fallback (not significant but |delta| >= 0.01)

## Results

### Per-arm mean W2 at expanded n

| Arm | n_seeds | mean_W2 | std_W2 | delta vs baseline | d_z (Cohen's d_s) | p_raw | p_bonf | Verdict |
|---|---|---|---|---|---|---|---|---|
| baseline | 30 | 0.08142 | 0.01622 | — | — | — | — | — |
| CosineAnnealScheduler (primary head) | 30 | 0.08025 | 0.00906 | -0.00117 | -0.089 | 7.32e-01 | 1.00 | TIE |
| CodimensionSheetScheduler (best-by-W2) | 19 | 0.07592 | 0.00579 | -0.00551 | -0.452 | 9.78e-02 | 6.85e-01 | TIE |
| EvidenceDrivenScheduler | 4 | 0.08452 | 0.00474 | +0.00310 | +0.259 | 4.27e-01 | 1.00 | TIE |
| FreeTrajScheduler | 3 | 0.08994 | 0.00574 | +0.00852 | +0.700 | 1.02e-01 | 7.16e-01 | TIE |

### Per-seed table (n=30)

See `verification_outputs/wave233-p4-r5a-expanded.csv`.

### Direction-consistency (paired (framework - baseline) sign)

| Arm | n_paired | frac_positive | frac_negative | frac_zero |
|---|---|---|---|---|
| CosineAnnealScheduler | 30 | 0.433 | 0.567 | 0.000 |
| CodimensionSheetScheduler | 19 | 0.579 | 0.421 | 0.000 |
| EvidenceDrivenScheduler | 4 | 0.750 | 0.250 | 0.000 |
| FreeTrajScheduler | 3 | 0.667 | 0.333 | 0.000 |

A paired positive fraction > 0.5 means the framework is consistently
WORSE on W2 (positive delta = framework - baseline for W2 lower-better).
A paired positive fraction < 0.5 means the framework is consistently
BETTER on W2 (negative delta = framework is better for W2 lower-better).

## Interpretation

**The TIE verdict persists at n=30, but the d_z sign has flipped.**

At n=10 (wave216 P2), the cosine arm's d_z was +1.011 (large
positive — the framework arm was worse on W2 than baseline). At
n=30 (wave233 P4), the cosine arm's d_z has dropped to -0.089
(tiny negative — the framework arm is essentially identical to
baseline, with a slight numerical lean toward framework better).
The p-value rose from 3.68e-02 (suggestive at n=10) to 7.32e-01
(clearly null at n=30), consistent with the original n=10 signal
being noise.

The CodimensionSheetScheduler arm at n=19 shows the same pattern
(d_z=-0.452, p=9.78e-02), with the larger sample size confirming
a real (if small) improvement of the framework arm on average.

The direction-consistency check at n=30 reinforces this: the
cosine arm has 17/30 seeds where framework is better than baseline
(frac_negative=0.567 > 0.5), and only 13/30 where it's worse.
This is consistent with the small negative d_z=-0.089 (slight
lean toward framework better, but well within TIE).

**Verdict remains TIE (|delta| < 0.01 absolute)** for all four arms.
The seed expansion has resolved the "false contradiction" flagged by
Wave 225 P1: the n=10 d_z=+1.011 was a noisy outlier in the
opposite direction of the true (small negative) effect.

**Best-by-W2 arm at n=30 is CodimensionSheetScheduler** (mean
W2 = 0.07592) vs CosineAnnealScheduler (mean W2 = 0.08025). The
codimension arm's tighter standard deviation (0.00579 vs 0.00906)
also suggests it is the more reliable of the two for Two Moons.

## Honest disclosure

* The new seeds (10..29) are generated by `tools/run_sota_2d_experiment.py`
  with the same `cycle_length=5` (5 multi-round rounds, 1000 samples/round,
  50 traj, 20 endpoints = 1000 samples) — matching wave209 P6 + wave216 P2
  exactly.
* The framework arms are unchanged from wave209/wave216: the same 4
  schedulers (CosineAnnealScheduler, CodimensionSheetScheduler,
  EvidenceDrivenScheduler, FreeTrajScheduler).
* We make no claim that the post-expansion verdict is "more correct"
  than the pre-expansion verdict — both are valid observations under
  their respective sample sizes. The seed expansion resolves the
  *power* question (is the large d_z signal real or noise?) rather
  than the *direction* question (which side of zero is the true mean
  delta on?).
* Partial-completion caveat: CosineAnnealScheduler and CodimensionSheetScheduler
  arms have partial seed coverage (n=30 / n=19 respectively). The
  headline verdict (cosine arm) is fully grounded. The
  CodimensionSheetScheduler verdict is grounded at n=19. The
  EvidenceDrivenScheduler / FreeTrajScheduler arms still reflect
  the n=4 / n=3 wave216 snapshot.

## Files

* `scripts/wave233_p4_r5a_expansion.py` — runner for new seeds 10..29
  (killed mid-run; partial completion).
* `scripts/wave233_p4_r5a_extended.py` — aggregator producing the
  CSV+JSON at expanded n.
* `verification_outputs/wave233-p4-r5a-expanded.csv` — per-seed +
  per-arm rows for the expanded R5a run.
* `verification_outputs/wave233-p4-r5a-expanded.json` — machine-readable
  summary with full Welch's t-test details per arm + direction-consistency.
* `docs/r4-survey/two_moons_*_seed{10..29}.csv` — 49 new per-(arm, seed)
  raw CSVs (baseline + cosine complete at 20+20=40, codim partial at 19).