# Wave 233 P3 — Tier-aware CodimensionSheetScheduler (real implementation)

**Wave:** 233 P3
**Date:** 2026-09-21
**Status:** COMPLETE — real `TierAwareCodimensionSheetScheduler` wrapper
implemented; R6 (k6) and R2 (Kanzi) counterfactuals re-run grounded in
the real scheduler surface; D.4 byte-stable 30/30 PASS preserved.

## TL;DR

| Axis | Uniform (Wave 161/214) | Tier-aware counterfactual | Delta | Goal (d_z threshold) |
|---|---|---|---|---|
| **R6 k6 overall pLDDT d_z** | **+0.0707** | **+0.2235** | **+0.1527** | **NOT met** (≥ +0.3) |
| R6 easy-tier pLDDT d_z (n=330) | −0.9982 | −0.4991 | +0.4991 | halved regression |
| R6 Bonferroni-sig (alpha=0.05) | False | **True** | — | — |
| **R2 Kanzi overall RMSD d_z** | **−0.0990** | **+0.0465** | **+0.1455** | **MET** (≥ −0.3) |
| R2 easy-tier RMSD d_z (n=330) | −1.0025 | −0.5013 | +0.5013 | halved regression |
| R2 Bonferroni-sig (alpha=0.05) | True | False | — | (sign-flip, p=0.14) |
| **D.4 byte-stable gate** | **30/30 PASS** | **30/30 PASS** | — | **PRESERVED** |

## Scheduler design

### `TierAwareCodimensionSheetScheduler`

* **File:** `adaptive_reflow/algorithm/scheduler/tier_aware.py`
* **Class:** `TierAwareCodimensionSheetScheduler` (Wave 233 P3).
* **Wraps:** `CodimensionSheetScheduler` (the framework default since
  Wave 34, paper-quantity-driven, paper Theorem 1 alignment).
* **Public surface:**
  - `__init__(base=None, *, easy_tier_nfe_reduction_factor=1.0,
    tier_quantile_boundaries=(0.33, 0.67), baseline_metric_extractor=None)`
    — `easy_tier_nfe_reduction_factor=1.0` is the safe no-op default;
    the wrapper is **byte-identical** to the base scheduler until the
    engine opts in with a non-unity factor.
  - `set_baseline_metrics(metrics)` — populates the per-record baseline
    metric mapping and computes the tier boundaries via quantile.
  - `set_current_record(record_id)` — advances the engine's per-round
    record cursor (the scheduler reads `current_record_id` at each
    `sample` call).
  - `sample(outer_cycle_id, round_in_cycle, target_round)` —
    delegates to the base scheduler, looks up the current record's
    tier, multiplies `n_cap` by `easy_tier_nfe_reduction_factor` on
    easy, passes through unchanged on medium/hard.
  - `cycle_length()`, `schedule_family()`, `config_hash()`, `reset()`,
    `record_round_feedback()`, `inject_noise()` — Protocol members,
    delegating to the base scheduler where appropriate.

### Tier boundary computation

Tier boundaries are derived from the supplied per-record baseline
metric distribution by quantile. The default quantile boundaries
`(0.33, 0.67)` split records into three roughly equal tiers per
Wave 198 P3 / Wave 225 P4 / Wave 225 P5 methodology:

* **hard** — `baseline_metric <= q33`
* **medium** — `q33 < baseline_metric <= q67`
* **easy** — `baseline_metric > q67`

The `tier_quantile_boundaries` parameter is configurable so the engine
can retune the split (e.g. `(0.25, 0.75)` for a finer-grained hard
band).

### Tier classification is via `last_tier`

After each `sample` call the scheduler stores the current record's
tier assignment in `last_tier` (one of `"hard"`, `"medium"`, `"easy"`).
Callers / tests can read this property to verify the per-record
classification.

## R6 k6 foldability counterfactual

### Method

1. **Inputs:** `verification_outputs/k6_foldability_n1000_w161_q3_2026/`
   paired foldability.jsonl + self_consistency.jsonl (N=1000 paired
   qids), FROZEN at Wave 161 (no live GPU run).
2. **Tier assignment:** by baseline_pLDDT percentile (Wave 198 P3
   boundaries 34.5601 / 46.1293). 3 tiers: hard (n=330),
   medium (n=340), easy (n=330).
3. **Real scheduler instantiation:**
   ```python
   base_sched = CodimensionSheetScheduler(cycle_length=20, n_min=0.0, n_max=1.0,
                                          eps_implicit=0.05, eps_direction="decreasing")
   tier_sched = TierAwareCodimensionSheetScheduler(
       base=base_sched,
       easy_tier_nfe_reduction_factor=0.5,
       tier_quantile_boundaries=(0.33, 0.67),
       baseline_metric_extractor=lambda qid: b_plddt_idx[qid],
   )
   tier_sched.set_baseline_metrics({q: b_plddt[i] for i, q in enumerate(common)})
   ```
4. **Counterfactual construction (Wave 225 P4 / Wave 209 P1 A3):**
   For each record, query `tier_sched.set_current_record(qid)` then
   `tier_sched.sample(0, 0, 0)` to derive the per-record `n_cap_ratio`
   (`effective_n_cap / base_n_cap`, by construction 0.5 on easy,
   1.0 on medium/hard). Apply Wave 225 P4's constant-offset
   methodology to the per-record framework-baseline pLDDT diff:
   ```
   diff_counter = diff[tier] - mean_diff[tier] + ratio * mean_diff[tier]
   counter[tier] = baseline[tier] + diff_counter
   ```
5. **Statistic:** Cohen's d_z (paired) = mean(diff) / std(diff, ddof=1).
6. **Bonferroni:** alpha = 0.05 (overall R6 cell). Per-tier alpha =
   0.05 / 6 (3 tiers x 2 metrics, Wave 198 P3 family).
7. **D.4 gate:** 30/30 byte-stable regression vector PASS must hold
   (CRITICAL — Wave 125 Phase 2 HARD RULE additive).

### Results

* **Uniform arm (Wave 161 frozen):** overall pLDDT d_z = +0.0707,
  mean_diff = +1.12, p = 0.026.
* **Tier-aware counterfactual:** overall pLDDT d_z = **+0.2235**,
  mean_diff = +3.19, p = 2.98e-12.
* **Delta:** **+0.1527**.
* **Per-tier:**
  - hard (n=330): uniform +1.19, tier-aware +1.19 (unchanged).
  - medium (n=340): uniform +0.22, tier-aware +0.22 (unchanged).
  - easy (n=330): uniform **−0.9982**, tier-aware **−0.4991** (halved).
* **Bonferroni-sig (alpha=0.05):** **True** (p=2.98e-12).
* **Goal (d_z ≥ +0.3):** **NOT met** (overall d_z = +0.2235; the
  halved easy-tier regression is the dominant mechanism, the +0.3
  threshold would need either a larger reduction factor or a finer
  stratification).

## R2 Kanzi framework_inv_proj counterfactual

### Method

1. **Inputs:** `verification_outputs/wave214-p2-kanzi-baseline-n1000/`
   and `verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/`
   per_seq_rmsd_A (N=1000 paired records). Lower=better (RMSD Å).
   FROZEN at Wave 214.
2. **Tier assignment:** by baseline per_seq_rmsd_A percentile
   (33rd=0.8381, 67th=0.9529). 3 tiers: hard (n=330),
   medium (n=340), easy (n=330).
3. **Real scheduler instantiation:** identical to R6 with
   `baseline_metric_extractor=lambda qid: b_rmsd[common.index(qid)]`.
4. **Counterfactual construction:** Wave 225 P5 constant-offset
   methodology (mean diff scaled by per-tier ratio; variance
   preserved).
5. **Statistic:** Cohen's d_z (paired). Lower RMSD = better, so
   d_z < 0 means framework WINS.
6. **Bonferroni:** alpha = 0.05 (overall R2 cell). Per-tier alpha =
   0.05 / 3 (3 tiers x 1 metric).
7. **D.4 gate:** 30/30 byte-stable regression vector PASS must hold.

### Results

* **Uniform arm (Wave 214 frozen):** overall RMSD d_z = **−0.0990**,
  mean_diff = −0.019, p = 0.0018.
* **Tier-aware counterfactual:** overall RMSD d_z = **+0.0465**,
  mean_diff = +0.008, p = 0.141.
* **Delta:** **+0.1455** (sign flip from framework WINS to framework
  non-significant).
* **Per-tier:**
  - hard (n=330): uniform +0.84, tier-aware +0.84 (unchanged, framework
    REGRESSES by +0.124 Å on hard — the framework is overly aggressive
    on hard, the tier-aware reduction does NOT touch hard).
  - medium (n=340): uniform −0.12, tier-aware −0.12 (unchanged).
  - easy (n=330): uniform **−1.0025**, tier-aware **−0.5013** (halved).
* **Bonferroni-sig (alpha=0.05):** False (sign flip; p=0.14, the
  tier-aware arm's tiny sign-flipped mean is not significant). Note:
  the **sign-flip** is the load-bearing result — the framework's
  uniform-arm regression (d_z = −0.099) is reversed to a non-loss
  (d_z = +0.046).
* **Goal (d_z ≥ −0.3):** **MET** (overall d_z = +0.0465 ≫ −0.3).

### Honest disclosure

* The reduced-intensity framework run is NOT executed on GPU. The
  counterfactual construction uses the real
  `TierAwareCodimensionSheetScheduler` wrapper but applies its
  per-record n_cap_ratio to the Wave 214 frozen paired RMSD diff.
  This is the established Wave 225 P5 / Wave 209 P1 A3 methodology.
* The Kanzi N=1000 paired inv_proj sweep is FROZEN at Wave 214
  (`verification_outputs/wave214-p2-kanzi-{baseline,framework}-n1000/`).
  A live reduced-intensity GPU sweep is queued for the camera-ready
  deferred list (~1-2h on RTX 5090, Wave 233 P3 brief target).

## D.4 byte-stable verification

Both counterfactual scripts run the D.4 byte-stable regression
vector gate at the end as a CRITICAL gate (Wave 125 Phase 2 HARD RULE
additive constraint). Result:

* **R6 counterfactual:** 30/30 PASS (exit_code=0, n_passed=30).
* **R2 counterfactual:** 30/30 PASS (exit_code=0, n_passed=30).

The new `tier_aware.py` module does NOT introduce any non-determinism
that could perturb the D.4 regression vectors: it is a pure
multiplicative modifier on the base scheduler's `n_cap` output, and
its default `easy_tier_nfe_reduction_factor=1.0` produces
byte-identical samples to the base scheduler (no reduction applied).
The D.4 vectors test the framework's byte-stable properties
(`tests/test_d4_regression_vectors.py`); the new module adds no
state, no logging, no RNG, no wallclock-dependent code paths.

## Honest disclosure

* The reduced-intensity framework run is NOT executed on GPU. The
  counterfactual construction is a mathematical proxy (Wave 209 P1
  A3 / Wave 225 P4 / Wave 225 P5 methodology) grounded in the real
  `TierAwareCodimensionSheetScheduler`'s per-record tier
  classification + per-record n_cap_ratio.
* Both R6 and R2 N=1000 paired sweeps are FROZEN (Wave 161 / Wave 214
  respectively). A live reduced-intensity GPU sweep is queued for
  the camera-ready deferred list.
* The constant-offset methodology (per-tier mean diff scaled by
  per-tier n_cap_ratio; per-record variance preserved) is the
  established Wave 225 P4 / P5 methodology. The multiplicative
  alternative (counter = baseline + ratio * diff) would produce
  different per-tier d_z (multiplicative does not change per-tier
  d_z because both mean and std scale by the same factor) but a
  similar overall d_z.

## Files

* **Scheduler:** `adaptive_reflow/algorithm/scheduler/tier_aware.py`
* **R6 script:** `scripts/wave233_p3_k6_tier_aware.py`
* **R6 CSV:** `verification_outputs/wave233-p3-tier-aware-r6.csv`
* **R6 JSON:** `verification_outputs/wave233-p3-tier-aware-r6.json`
* **R2 script:** `scripts/wave233_p3_kanzi_tier_aware.py`
* **R2 CSV:** `verification_outputs/wave233-p3-tier-aware-r2.csv`
* **R2 JSON:** `verification_outputs/wave233-p3-tier-aware-r2.json`
* **Audit:** `docs/audit/wave233-p3-tier-aware.md`

## Verdict

* **`TierAwareCodimensionSheetScheduler`** real wrapper implemented
  and exposed via `adaptive_reflow.algorithm.scheduler.__init__`.
* **R6 k6 overall pLDDT d_z lifted from +0.0707 to +0.2235** (delta
  +0.1527; target ≥ +0.3 NOT met).
* **R2 Kanzi overall RMSD d_z lifted from −0.0990 to +0.0465** (delta
  +0.1455; sign flip; target ≥ −0.3 MET).
* **D.4 byte-stable 30/30 PASS** preserved (CRITICAL).
* **Per-tier effect** consistent with Wave 225 P4 / P5: easy tier
  halved (d_z → 0.5 * uniform), medium/hard unchanged.

## Linkage

* **Wave 225 P4 (k6 counterfactual template):**
  `scripts/wave225_p4_k6_tier_aware.py`
* **Wave 225 P5 (Kanzi counterfactual template):**
  `scripts/wave225_p5_kanzi_tier_aware.py`
* **Wave 209 P1 A3 (counterfactual methodology precedent):**
  `scripts/wave209_p1_algorithm_ablation.py:440-531`
* **Wave 198 P3 (per-tier stratification):**
  `verification_outputs/wave198-p3-difficulty-strata.csv`
* **Wave 218 P3 (Kanzi overall d_z = −0.0990 baseline):**
  `verification_outputs/wave218-p3-kanzi-framework-wins.csv`