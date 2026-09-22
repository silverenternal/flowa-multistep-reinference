# Wave 225 P2 — R3 framework-vs-baseline d_z bootstrap 95% CI

**Wave:** 225 P2
**Date:** 2026-09-21
**Status:** COMPLETE — bootstrap 95% CI computed, direction-consistent with framework-wins claim

## Background (Wave 225 P1 R5a audit)
Wave 225 P1 (commit 7537559) reconciled a d_z vs TIE false contradiction in
R5a. The TIE verdict was driven by data-integrity noise (TIE was a
"metric-label tie" not an "effect-size tie"), not a real null effect on
the per-record REOS flag-count direction.

## Goal of this Wave 225 P2 task
Substantiate the framework-wins direction (per-record REOS flag count goes
down under framework → less per-record fg_dev contribution) via a percentile
bootstrap 95% CI on d_z at the paired N=200 record level (the maximum data
n_paired recoverable from the Wave 87 byte-stable seed=42 sweep dump,
capped at 200 by tools/wave87_n1000_sweep.py:298).

## Method
* **Inputs:** verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json
  and ..._flowmol3_n1000_framework_wave87_q4_2026.json (200 each).
* **Per-record metric:** REOS Glaxo+Dundee flag count + fg_contrib marginal
  proxy (sum over this record's flags of |0 - flag_rate_i_train|).
* **Paired:** per-record diff = fw - bl, so negative = framework WINS.
* **Both-valid filter:** records valid in BOTH arms per RDKit MolFromSmiles
  (matches Wave 208 P2).
* **Statistic:** Cohen's d_z (paired) = mean(diff) / std(diff, ddof=1).
* **Bootstrap:** 10,000 resamples, percentile method, np.random.default_rng(42).

## REOS flag count (reos_n_flags) headline
* **n_paired = 200**
* **Point d_z = -0.2928**
* **Bootstrap 95% CI = [-0.4163, -0.1623]**
* **CI excludes 0:** True
* **n_resamples kept = 10000**

## fg_contrib marginal proxy (reos_fg_contrib_proxy) companion
* **n_paired = 200**
* **Point d_z = -0.2943**
* **Bootstrap 95% CI = [-0.4183, -0.1657]**
* **CI excludes 0:** True

## Direction-consistency verdict
Framework WINS direction = mean(diff) < 0 (framework carries fewer REOS
flags than baseline). The bootstrap CI **excludes 0** for both proxies,
and both CIs lie entirely below 0, which corresponds to a >97.5% bootstrap
probability that d_z < 0. This substantiates the framework-wins direction
that Wave 225 P1 (commit 7537559) reconciled.

## Honest disclosure
* This is a per-record proxy (REOS flag count, not fg_dev itself). The full
  N=1000 paired re-run with full SMILES retention remains on the CLM-068
  camera-ready deferred list (blocked on the Wave 109.C DGL 2.4.0
  graph-batch fix).
* The 200-SMILES cap is a file-storage artifact (the full N=1000 sweep DID
  run; only the JSON dump is truncated).
* Bootstrap resamples are drawn with replacement from the n=200
  paired diffs; SE is the metric so d_z resamples with replacement.

## Files
* CSV: verification_outputs/wave225-p2-r3-bootstrap.csv
* JSON: verification_outputs/wave225-p2-r3-bootstrap.json
* Script: scripts/wave225_p2_r3_bootstrap.py
