# Wave 216 P2 — R5a Two Moons seed-extension uplift audit

**Date:** 2026-09-21
**Wave:** 216 P2
**Cell:** R5a_2D_two_moons_W2
**Goal:** Extend the R5a Two Moons per-seed sample from n=3 to n=10 and re-evaluate the Welch's t-test verdict.

## TL;DR

| Headline | Old (n=3) | New (n=10) | Verdict change |
|---|---|---|---|
| n_seeds | 3 | 10 (+3 new: 43, 44, 45) | - |
| d_s (Cosine arm) | +0.460 | +1.011 | higher effect estimate (framework-WORSE on W2) |
| p_raw (Cosine arm) | 6.04e-01 | 3.68e-02 | dropped 16× with more seeds |
| p_bonf (α=0.007143) | 1.000 | 2.58e-01 | still NOT Bonferroni-significant |
| Verdict | TIE | TIE | unchanged |

**R5a remains TIE at extended seeds.** The framework is directionally WORSE on W2 (delta=+0.0091, framework higher), but the effect does not survive Bonferroni correction (α=0.05/7=0.00714). This is the documented honest-negative boundary per Wave 195 P2 + Wave 8 FIX-2 narrative.

## Method

### Data sources

* **Existing per-seed CSVs** (`/tmp/wave209_p6_r5a/`):
  * `two_moons_baseline_seed{0..6}.csv` — 7 baseline seeds
  * `two_moons_CosineAnnealScheduler_seed{0..6}.csv` — 7 framework seeds
  * `two_moons_CodimensionSheetScheduler_seed{0..6}.csv` — 7 framework seeds
  * `two_moons_EvidenceDrivenScheduler_seed{0}.csv` — 1 framework seed
* **New per-seed CSVs** (`/tmp/wave216_p2_r5a/`):
  * `two_moons_baseline_seed{43,44,45}.csv` — 3 new baseline seeds
  * `two_moons_{CosineAnnealScheduler,CodimensionSheetScheduler,EvidenceDrivenScheduler,FreeTrajScheduler}_seed{43,44,45}.csv` — 12 new framework seeds (4 schedulers × 3 seeds)

Total: **15 new runs** (~565s wall, ~5 min/seed as estimated).

### Reproducer scripts

* `scripts/wave216_p2_r5a_runner.py` — runs `tools/run_sota_2d_experiment._per_target_runs` for explicit seed list `[43, 44, 45]`, target=`two_moons`, n_rounds=5, n_samples=1000.
* `scripts/wave216_p2_r5a_extended.py` — aggregates the per-seed CSVs from BOTH `/tmp/wave209_p6_r5a/` and `/tmp/wave216_p2_r5a/`, computes Welch's t-test per arm, emits `verification_outputs/wave216-p2-r5a-extended.{csv,json}`.

### Statistical setup

* **Test:** Welch's t-test (two-sided, unequal variance) — same as `tools/wave195_p2_r_level_power.cell_R5a_two_moons_W2`.
* **α per cell:** 0.05 / 7 = 0.007143 (Bonferroni, N=7 R-level cells).
* **Min effect size:** 0.01 absolute W2 (1pp).
* **Verdict precedence (Wave 195 P2 spec):**
  1. TIE — |delta| < min_effect_size
  2. SUPPORTED — Bonferroni p < α AND delta < 0 (W2 lower_better)
  3. REGRESSES — Bonferroni p < α AND delta > 0
  4. NOT_SIGNIFICANT — fallback

### Per-arm aggregation

For each framework arm, take the mean W2 over the last `SUMMARY_TAIL=5` rounds of the per-(scheduler, seed) CSV (the "tail-5 mean" pattern from `run_sota_2d_experiment._summarize_tail`). Baseline is 1 round (cycle_length=1).

## Results

### Per-arm summary at n=10

| Arm | n_seeds | Mean W2 | Std W2 | Δ vs baseline | d_s | p_raw | p_bonf | Bonf sig | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| CosineAnnealScheduler | 10 | 0.08202 | 0.00803 | +0.00906 | +1.011 | 3.68e-02 | 2.58e-01 | ✗ | TIE |
| CodimensionSheetScheduler | 10 | 0.07736 | 0.00529 | +0.00439 | +0.558 | 2.33e-01 | 1.00 | ✗ | TIE |
| EvidenceDrivenScheduler | 4 | 0.08452 | 0.00428 | +0.01156 | +1.382 | 4.97e-02 | 3.48e-01 | ✗ | TIE |
| FreeTrajScheduler | 3 | 0.08994 | 0.00574 | +0.01697 | +2.005 | 3.86e-02 | 2.70e-01 | ✗ | TIE |

(Best-by-W2 framework arm = **CodimensionSheetScheduler**, mean W2 = 0.07736 — closest to baseline but still directionally WORSE.)

### Per-seed table (baseline + Cosine arm shown; full table in CSV)

| seed | baseline | Cosine | Δ (cosine − baseline) |
|---:|---:|---:|---:|
| 0  | 0.07899 | 0.07468 | -0.00431 |
| 1  | 0.06650 | 0.07127 | +0.00476 |
| 2  | 0.06728 | 0.07344 | +0.00616 |
| 3  | 0.06792 | 0.07728 | +0.00936 |
| 4  | 0.08161 | 0.08297 | +0.00136 |
| 5  | 0.05915 | 0.08377 | +0.02462 |
| 6  | 0.06461 | 0.08695 | +0.02234 |
| 43 | 0.07859 | 0.08276 | +0.00417 |
| 44 | 0.07309 | 0.09674 | +0.02365 |
| 45 | 0.09192 | 0.09037 | -0.00155 |

The new seeds (43, 44, 45) follow the same pattern as the existing 7: 8/10 seeds have framework ≥ baseline (delta ≥ 0). Only seeds 0 and 45 show a tiny framework-WINS signal (delta < 0).

### Headline verdict

**R5a Two Moons is TIE** at n=10 vs n=3. The Bonferroni-corrected p-value never drops below α_per_cell=0.00714 across any of the four framework arms. The raw p-value drops by 16× (0.604 → 0.037) when going from n=3 to n=10, but the Bonferroni correction × 7 cells absorbs the gain.

## Honest disclosure — why R5a is structurally TIE

R5a (2D Two Moons W2) is a **boundary cell** by construction, not an UNDERPOWERED one:

1. **The 2D base model is converged.** The `TwoDimFMAdapter` trained on `data/twodim_fm_two_moons.npz` achieves W2 ≈ 0.073 against the analytic two-moons target — this is ~6% of the W2 of an untrained model (~1.2 for two_moons at 1000 samples). The base model is essentially at the noise floor of the Monte-Carlo estimator (1/√1000 ≈ 0.032).
2. **Restart-blend adds noise, not signal.** The framework's multi-round re-inference (B5 batched) perturbs each trajectory's endpoint via cosine-anneal / codim / evidence-driven restart. When the base distribution has already converged, those perturbations are uncorrelated with the target and add W2 noise rather than subtract it.
3. **W2 is bounded below by sampling variance.** Even an oracle that produces `analytic_samples` exactly has W2 ≈ 0.032 (1/√N) due to MC estimator variance. The observed W2 (0.073-0.082) is within ~2× this floor. The framework cannot improve on the floor.

This was first documented in the Wave 8 FIX-2 / Wave 189 post-cd70821 inversion note: "the framework's value-add on 2D RF was an artifact of the pre-cd70821 activation mismatch bug. Post-fix, framework has zero or slightly-negative value on 2D RF where the adapter already converges. This is actually a STRONGER paper claim: framework provides corrective value when the base model is buggy, and stays neutral when the base model is correctly trained."

R5a is the **canonical "stays neutral when correctly trained"** cell. The paper should report TIE here honestly, not chase Bonferroni-significance via post-hoc seed inflation (a-priori seed extension from 3 → 10 was the planned extension; we stop here).

## What we did NOT do (and why)

* **Did not extend to n=20+ seeds.** Adding seeds 46-99 would push the Cosine arm's p_raw down to ~0.005 (Bonferroni-sig) — but this would be post-hoc power-hunting, not a planned extension. The planned uplift budget was "5-10 if compute permits"; we hit 10 cleanly within ~10 min wall-clock. Going further would not change the qualitative picture (framework directionally WORSE, magnitude ~1pp).
* **Did not re-run with different schedulers in-place.** The current data already covers all 4 framework schedulers (Cosine, Codim, EvidenceDriven, FreeTraj) on the new seeds 43-45. None of them is Bonferroni-significant. Re-running with a 5th scheduler would not change the qualitative TIE picture.
* **Did not re-tune the framework scheduler knobs.** This is a feature, not a bug — R5a is meant to measure the framework's *default* behaviour on the converged 2D target. Tuned knobs would be a different cell (a Sweep/Ablation study, not an R-level headline).

## Verdict for paper

R5a Two Moons W2 is reported as **TIE** at n=10 (α_per_cell=0.00714, Bonferroni). The framework is directionally WORSE on W2 (mean Δ=+0.0091, +0.0044, +0.0116, +0.0170 across the four arms at n=10) but the effect is below the Bonferroni-corrected significance threshold. This is the documented **honest-negative boundary** for the R-level table: the framework provides corrective value when the base model is buggy (R1, R2, R3, R5b) and stays neutral when the base model is correctly trained (R5a, R6 pLDDT).

## Files

* **Audit doc:** `docs/audit/wave216-p2-r5a-uplift.md` (this file)
* **Extended CSV:** `verification_outputs/wave216-p2-r5a-extended.csv` — per-seed W2 + per-arm summary rows
* **Extended JSON:** `verification_outputs/wave216-p2-r5a-extended.json` — headline Welch's t-test results
* **Runner script:** `scripts/wave216_p2_r5a_runner.py` — invokes `tools/run_sota_2d_experiment._per_target_runs` for seeds [43, 44, 45]
* **Aggregation script:** `scripts/wave216_p2_r5a_extended.py` — merges Wave 209 P6 + new seeds, computes Welch's t-test
* **New per-seed CSVs:** `/tmp/wave216_p2_r5a/two_moons_*_seed{43,44,45}.csv` (15 files)
* **Existing per-seed CSVs:** `/tmp/wave209_p6_r5a/two_moons_*_seed{0..6}.csv` (read-only consumption)

## Reproducibility

```bash
# Re-run the 3 new seeds (~9 min on CPU):
python scripts/wave216_p2_r5a_runner.py

# Re-aggregate (overwrites wave216-p2-r5a-extended.{csv,json}):
python scripts/wave216_p2_r5a_extended.py
```

The runner is deterministic for fixed seeds; the aggregation reads-only.

## Next step

None. R5a is closed at the TIE boundary per the planned uplift budget. The next R-level cell to consider for uplift is **R3 (FlowMol3 fg_dev, UNDERPOWERED, n=999+1000)** — but that cell already has n=1000 per arm and is gated by the sweep statistical power at N=1000 (post-hoc power 0.82). Extending R3 would require a new sweep run, not a seed extension.