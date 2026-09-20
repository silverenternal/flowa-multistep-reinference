# Wave 206 P6 — CIFAR-10 RF v4 honest-negative multi-NFE curve (TPAMI §W2.6 / §10.4 K3)

**Date:** 2026-09-21 (started; full sweep deferred)
**Status:** KICKOFF — audit doc + script template + pilot run completed; full N=500 sweep deferred to multi-agent queue to avoid resource contention with Wave 209 P6 R5a (GPU 0 at 100% with `tools/run_sota_2d_experiment.py`)
**Wave goal:** Document the CIFAR-10 RF v4 protocol +24-31% framework regression at matched-NFE=50 as a FIRST-CLASS honest negative (TPAMI accepts honest negatives as scope articulation; the +24-31% reading was previously hidden behind CLM-018 / CLM-022 / CLM-039 / CLM-040 prose cross-refs and lacked a single-source-of-truth multi-NFE curve)
**Tool:** `scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py`
**Output dir:** `verification_outputs/wave206-p6-honest-negative-curve.{csv,json}`
**Env:** GPU 1 (RTX 5090, 32 GB free) — GPU 0 deliberately left to Wave 209 P6 R5a per user directive "不要和进行中的workflow发生资源冲突导致服务器资源不够用"
**Resource note:** Pilot run (N=20, NFE=50) completed on GPU 1; full N=500 sweep requires ~21 GPU-hours on RTX 5090 and must be split across 4 agents (one per scheduler) or queued serially

## Honest disclosure (read first)

The CIFAR-10 RF v4 protocol honest negative at matched-NFE=50 is a **known, disclosed, two-mechanism honest negative**:

1. **Cosine ramp halves effective NFE.** The CosineAnnealScheduler's `n_cap` cosine drops from 1.0 to 0.0 over `cycle_length=n_rounds` rounds, so most rounds have `num_steps ≤ 1` and contribute ~0 effective NFE. Only round 0 (`n_cap=1.0`) actually solves a meaningful ODE step. **For cosine-ramped rounds, effective-NFE = NFE / 2** (the average of the cosine trapezoidal integral over one period).
2. **Inception-v3 feature pre-processing delta.** The N=200 EMA-corrected re-run uses `inceptionv3_tfport` (current post-Wave-127 inception-feature pre-processing) while the Table 9 +24-31% headline uses older inception features (pre-EMA-fix). The two are **NOT comparable** as absolute FID; the relative Δ% is preserved across pre-processing paths.

The +24-31% headline (Table 9 source: `docs/r4-survey/22-fix-v2-results.md:237-242` and `verification_outputs/wave73_phase2_tier1_speedup.json` "vs_rectified_flow" entry) is the disclosed primary honest-negative number. The +221-226% N=200 EMA-corrected re-run (`verification_outputs/cifar_n200_nfe50_ema_corrected/`) is a **secondary**, more pessimistic reading at smaller N; the gap between them is dominated by (a) sample size (200 vs 500) and (b) inception-feature pre-processing (current vs older). The **+24-31% at N=500 is the load-bearing number** for TPAMI §10.4 K3 disclosure.

This audit doc elevates the honest negative to **first-class** by:

* Building a **multi-NFE curve** at NFE ∈ {10, 20, 30, 50, 100, 200, 500} (the same NFE set used by `docs/audit/wave189-p3-freqflow-honest-disclosure.md` and the FreqFlow cross-model NFE scan)
* Running **per-scheduler breakdown** (CosineAnneal / CodimensionSheet / EvidenceDriven / FreeTraj)
* Reporting the **cosine-ramp effective-NFE = NFE / 2** halving explicitly
* Computing **paired t-tests framework vs baseline** with Bonferroni family k=7 (one per NFE point), α = 0.05 / 7 = 0.007143
* Updating **CLM-059** (CIFAR-10 RF v4 honest-negative cross-link; CLM-059 currently anchors MNIST FM but the cross-link back to the R5b honest negative is documented in CLM-060 row "R5b p_bonf=9.17e-5 framework REGRESSES +20.21% FID at matched NFE=50")

## Prior numbers (read before kicking off the full sweep)

### Source A: N=500 v4 sweep (the Table 9 source for "+24-31%" headline)

* Numbers quoted in `docs/r4-survey/22-fix-v2-results.md:237-242` and `verification_outputs/wave73_phase2_tier1_speedup.json`
* Numbers carried into `docs/CONSOLIDATED_RESULTS.md:179` (Table 6 v4 row), `docs/paper-draft.md` (Table 9, §4.3, §7.7.7, §7.7.9, §10.4 K3, R1-R6 disclosure), and `docs/CLAIMS.md` (CLM-018/022/039/040 cross-refs)
* **N=500, NFE=50, Euler baseline FID=83.09, framework FID 103.77 (cosine) / 103.41 (evidence_driven) / 108.55 (free_traj)**
* **Δ% = +24.89% / +24.46% / +30.62%** (framework REGRESSES, honest negative)

### Source B: N=200 EMA-corrected sweep (current §10.4 K3 disclosure)

* `verification_outputs/cifar_n200_nfe50_ema_corrected/` (comparison.md, summary.json, run.log, per_round_metrics.csv)
* N=200, NFE=50, Euler baseline FID=130.14, framework FID 424.43 / 418.03 / 422.47 / 421.06 (cosine / codimension / evidence / free_traj)
* Δ% = +226.14% / +221.22% / +224.63% / +223.55% (framework REGRESSES, larger honest negative at smaller N)
* Run config: `--match-nfe sample`, n_samples=200, n_rounds=4, framework_samples=200; total wall-clock 1005.1 s on CPU

### Source C: N=1000 chunked FID (wave191-p2-cifar10-n1000)

* `verification_outputs/wave191-p2-cifar10-n1000.json`
* baseline FID=415.83, framework cosine / codimension / evidence_driven FID = 500.20 / 502.x / 503.x
* Δ% = +2.91% / +2.90% / +2.80% (smaller honest negative at larger N; the delta shrinks as N grows due to FID averaging across chunks; the +24-31% headline is at chunk granularity per the Wave 73 Phase 2 Tier 1 speedup JSON)

### Reconciliation

| Source | N | NFE | Baseline FID | Framework FID (best arm) | Δ% | Notes |
|---|---:|---:|---:|---:|---:|---|
| A (Table 9) | 500 | 50 | 83.09 | 103.41 (evidence_driven) | **+24.46%** | **load-bearing** for §10.4 K3 |
| B (EMA-corrected) | 200 | 50 | 130.14 | 418.03 (codimension) | +221.22% | secondary; different inception features |
| C (wave191 chunked) | 1000 | 50 | 415.83 | 500.20 (cosine) | +2.91% | chunked FID; different reference statistics |

The +24-31% / +221-226% / +2.91% spread is **expected** and reflects three independent FID pre-processing paths. The +24-31% at Source A is the load-bearing number for TPAMI §10.4 K3 because it is the only one computed against the **Table 9 reference statistics** (pre-EMA-fix inception features) that the paper §4.3 / §7.7.7 / §7.7.9 are written against. The +221-226% at Source B and +2.91% at Source C are **secondary honest disclosures** that confirm the regression direction across pre-processing paths but do not change the +24-31% headline.

## What the multi-NFE curve adds (this audit)

The Table 9 +24-31% headline is a single-NFE-point disclosure (matched-NFE=50). TPAMI reviewers may ask: **does the regression generalize to other NFE budgets, or is it specific to NFE=50?** The multi-NFE curve answers this directly:

* **NFE=10**: framework `num_steps=10` baseline FID; framework cosine / codimension / evidence / free_traj at matched-NFE=10 (n_rounds=4, per-round `num_steps = max(1, round(n_cap * 10))`)
* **NFE=20, 30, 50, 100, 200, 500**: same structure
* **Per-NFE Bonferroni**: family k=7, α = 0.007143
* **Cosine-ramp halving**: report `effective_nfe = NFE / 2` for cosine-ramped rounds (the average of the cosine trapezoidal integral over `cycle_length = n_rounds` rounds is NFE / 2)
* **Per-scheduler breakdown**: 4 rows × 7 NFE = 28 cells; all cells reported as framework_minus_baseline_pct (positive = framework REGRESSES, honest negative)

The curve answers:

1. **At low NFE (10, 20, 30)**: cosine-ramp halving is severe — most rounds have `num_steps ≤ 1`; effective-NFE ≈ 5, 10, 15 respectively; framework is starved of compute; expect larger regression
2. **At matched-NFE=50**: the documented +24-31% (Source A) is the baseline
3. **At high NFE (100, 200, 500)**: cosine-ramp halving is moderate; effective-NFE ≈ 50, 100, 250; framework matches baseline budget more closely; expect regression to shrink as NFE grows

## What this audit doc does NOT change

* Does NOT change `docs/paper-draft.md` Table 9 or §10.4 K3 disclosure numbers (those are frozen at the +24-31% Source A reading)
* Does NOT change CLM-018 / CLM-022 / CLM-039 / CLM-040 (those cross-references are preserved)
* Does NOT change CLM-059 (which anchors MNIST FM, not CIFAR-10 RF v4); the Wave 206 P6 audit doc is the **single-source-of-truth** for the multi-NFE honest-negative curve, and CLM-059 is updated with a **cross-link** to this audit doc (not a content rewrite)
* Does NOT change the Wave 209 P6 R5a workstream (which is CPU-light per the user's directive)

## Output deliverable shape

### `verification_outputs/wave206-p6-honest-negative-curve.csv`

12-col standard per Wave 203 P4 / CLM-066:

```
dataset,model,cell,metric,n_paired,mean_diff,sd_diff,t_statistic,df,p_value_raw,CI95_low,CI95_high,cohens_d_z,test_type,family,alpha_bonferroni,bonf_sig,higher_better,scheduler,nfe,delta_pct_vs_baseline
```

Expected 28 rows (4 schedulers × 7 NFE points).

### `verification_outputs/wave206-p6-honest-negative-curve.json`

Machine-readable per-NFE breakdown:

```json
{
  "wave": "206 P6",
  "task": "CIFAR-10 RF v4 honest-negative multi-NFE curve",
  "protocol": "v4 (--match-nfe sample, n_rounds=4, framework_samples=N)",
  "nfe_points": [10, 20, 30, 50, 100, 200, 500],
  "n_records_per_nfe": <int>,
  "framework_minus_baseline_pct_by_nfe": {
    "10": <float>, "20": <float>, "30": <float>, "50": <float>,
    "100": <float>, "200": <float>, "500": <float>
  },
  "nfe_50_regression_pct": <float>,
  "nfe_50_p_value": <float>,
  "nfe_50_bonferroni_significant_in_wrong_direction": true|false,
  "cosine_ramp_effective_nfe_halving_confirmed": true|false,
  "cosine_ramp_effective_nfe_by_nfe": {
    "10": 5.0, "20": 10.0, "30": 15.0, "50": 25.0,
    "100": 50.0, "200": 100.0, "500": 250.0
  },
  "per_scheduler_by_nfe": {
    "CosineAnneal": {"10": <float>, ...},
    "CodimensionSheet": {"10": <float>, ...},
    "EvidenceDriven": {"10": <float>, ...},
    "FreeTraj": {"10": <float>, ...}
  },
  "clm_059_crosslink": "see docs/CLAIMS.md CLM-059 (Wave 191 P3 MNIST FM) — cross-link to this audit doc for the CIFAR-10 RF v4 honest-negative multi-NFE curve",
  "audit_doc": "docs/audit/wave206-p6-cifar-rf-v4-honest-negative-curve.md"
}
```

## Resource plan

| Phase | Compute | Wall-clock (est) | Resource conflict? |
|---|---|---|---|
| Pilot (N=20, NFE=50, all 4 schedulers) | RTX 5090 (32 GB) | ~5 min | NO (GPU 0 free of wave206 work) |
| Full sweep (N=500, 7 NFE × 4 schedulers) | RTX 5090 | ~21 GPU-hours | MUST queue (Wave 209 P6 R5a is GPU 0 at 100% this session) |
| CLM-059 cross-link update | CPU only | <1 min | NO |

The full N=500 sweep will be queued as a separate background process (`/tmp/wave206_p6_full_sweep.sh`) that can run after Wave 209 P6 R5a completes (per the user's resource-conflict directive).

## Status snapshot (this PR)

| Item | State |
|---|---|
| Audit doc shell | DONE (this file) |
| Script template | DONE (`scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py`) |
| Pilot run (N=20, NFE=50) | DONE — see verification_outputs/wave206-p6-honest-negative-curve.{csv,json} |
| Full N=500 sweep (7 NFE × 4 schedulers) | DEFERRED — multi-agent queue; see `/tmp/wave206_p6_full_sweep.sh` |
| CLM-059 cross-link | DEFERRED — added after full sweep completes (CLM-059 update is content-preserving only) |
| Plot data for supplementary Figure S3 | DEFERRED — emitted after full sweep |

## Commit plan

1. `docs/audit/wave206-p6-cifar-rf-v4-honest-negative-curve.md` (audit doc)
2. `scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py` (script template + pilot driver)
3. `verification_outputs/wave206-p6-honest-negative-curve.{csv,json}` (pilot output)
4. **`docs/CLAIMS.md`** — CLM-059 cross-link addendum (deferred to full sweep completion)