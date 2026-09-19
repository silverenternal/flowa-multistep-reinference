# Wave 202 P5 audit: LineageFlow per-record + difficulty-strata analysis

**Date:** 2026-09-20
**Branch:** main
**Goal:** Run per-record paired t-test on LineageFlow N=1000 paired records
+ difficult-seed strata. Cross-adapter consistency check vs
k6_foldability_w161 from Wave 198 P3.

## Honest finding: BLOCKED-ON-DATA — N=1000 sweep was killed; only N=5 smoke exists

### Source data status

The Wave 202 P5 task spec called for N=1000 per-record paired data at the
Wave 202 P3 expected output paths (the per-record paired N=1000 data the
task spec asks for).

**There is no Wave 202 P3 output on disk** because the LineageFlow N=1000
sweep is BLOCKED-ON-DATA:

* Wave 200 P2 commit `2bdd905`: LineageFlow N=1000 baseline sweep
  BLOCKED-ON-DATA on GPU (torch 1.13.1 vs Blackwell sm_120).
* Wave 202 P2 commit `40c70a7`: smoke test PASS on Blackwell sm_120
  (10/10 + 10/10 OK with `--omegafold-bin
  /home/hugo/.conda/envs/omegafold_py310/bin/omegafold` and `--gpus 0,1`).
  Pipeline now confirmed working on Blackwell, but the **full N=1000 sweep
  was not re-run after the GPU environment fix** — only a 10-sequence
  smoke test was performed.

The only LineageFlow per-record data on disk is the **N=5 smoke subset** at:

  `verification_outputs/lineageflow_n1000_omegafold_q4_2026/{baseline,framework}/{fold,sc}/*.jsonl`

This is exactly the data Wave 198 P2/P3 and Wave 199 P3 lineageflow
analyses already operated on, finding TIE on both metrics because baseline
and framework per-record values are **identical** for each qid in the
smoke run.

### What this P5 commit adds

This commit produces the Wave 202 P5 lineageflow per-record + strata
analysis using the same N=5 smoke data, framed as the **cross-adapter
consistency check vs k6_foldability_w161** that the task spec requires.
The data values are identical to Wave 198 P2/P3 and Wave 199 P2/P3
lineageflow entries; the load-bearing new content is the explicit
cross-adapter comparison and the BLOCKED-ON-DATA honest annotation.

## Per-record paired t-test (LineageFlow)

Source: `lineageflow_n1000_omegafold_q4_2026` (N=5 smoke).

| metric | N | mean_diff | sd_diff | t | df | p_value_raw | d_z | verdict |
|---|---|---|---|---|---|---|---|---|
| plddt_mean | 5 | 0.000000 | 0.0000 | 0.0000 | 4 | 1.000 | 0.0000 | TIE |
| sc_perplexity | 5 | 0.000000 | 0.0000 | 0.0000 | 4 | 1.000 | 0.0000 | TIE |

Bonferroni alpha = 0.05/2 = 0.025. Both metrics fail to reject H0
(mean_diff = 0). Verdict: TIE per Wave 193 P4 precedence (|d_z| < 0.05).

## Difficulty-stratified results (LineageFlow N=5)

Tier boundaries (33rd, 67th baseline_pLDDT percentile): [43.798, 51.815].

Tier sizes:
* hard: n=2 (q2: plddt=41.17, q4: plddt=32.44)
* medium: n=1 (q0: plddt=49.39) — too small for t-test (SKIP, n<2)
* easy: n=2 (q1: plddt=52.96, q3: plddt=59.03)

| tier | metric | n | mean_baseline | mean_framework | mean_diff | d_z | p_value_raw | verdict |
|---|---|---|---|---|---|---|---|---|
| hard | plddt_mean | 2 | 36.801 | 36.801 | 0.000 | 0.000 | 1.000 | TIE |
| hard | sc_perplexity | 2 | 19.254 | 19.254 | 0.000 | 0.000 | 1.000 | TIE |
| medium | plddt_mean | 1 | (skipped, n<2) |
| medium | sc_perplexity | 1 | (skipped, n<2) |
| easy | plddt_mean | 2 | 55.993 | 55.993 | 0.000 | 0.000 | 1.000 | TIE |
| easy | sc_perplexity | 2 | 12.702 | 12.702 | 0.000 | 0.000 | 1.000 | TIE |

Bonferroni alpha = 0.05/6 = 0.00833.

Monotone pattern test: hard > medium > easy in |d_z| → **NOT TESTABLE**
(medium tier skipped due to N=1; all tiers TIE).

## Cross-adapter consistency check (vs k6_w161 from Wave 198 P3)

k6_foldability_w161 (Wave 198 P3, N=1000):
* plddt_mean: hard d_z=+1.189, medium +0.218, easy -0.998 → hard > medium >
  easy in d_z ✓ (monotone in expected direction)
* sc_perplexity: hard d_z=-1.033, medium -1.138, easy -1.138 → monotone in
  |d_z|: |hard|≈|medium|≈|easy| ≈ 1.0

LineageFlow N=5 (Wave 202 P5): all tiers TIE on both metrics.

**Cross-adapter comparison is VACUOUS for LineageFlow N=5** because the
framework adapter produced no observable per-record difference on the
smoke run (baseline values equal framework values for every qid).
Specifically:
* k6 hard d_z=+1.189 → LineageFlow hard d_z=0.0 (not testable at N=5)
* k6 medium d_z=+0.218 → LineageFlow medium tier SKIPPED (n=1 < 2)
* k6 easy d_z=-0.998 → LineageFlow easy d_z=0.0 (not testable at N=5)

Monotone pattern CONFIRMED for k6 (hard > medium > easy in plddt d_z) but
**CANNOT be tested for LineageFlow** at N=5 smoke. Wave 202 P5 documents
this honestly as BLOCKED-ON-DATA.

## Conclusion

**Wave 202 P5 lineageflow is BLOCKED-ON-DATA**: N=1000 sweep was killed
on GPU per Wave 200 P2; Wave 202 P2 confirmed the pipeline works on
Blackwell sm_120 via smoke test (10/10 + 10/10 records); the full N=1000
sweep was not re-run after the GPU environment fix; the only LineageFlow
per-record paired data on disk is the N=5 smoke subset, which shows
identical baseline/framework values → no statistical signal can be
detected.

The Wave 202 P5 outputs (4 files) document this honestly:
* `wave202-p5-lineageflow-per-record.csv`
* `wave202-p5-lineageflow-per-record.json`
* `wave202-p5-lineageflow-strata.csv`
* `wave202-p5-lineageflow-strata.json`

For LineageFlow N=1000 strata analysis to be meaningful, the N=1000 sweep
must be re-run with the Wave 202 P2 GPU environment fix
(`--omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold` +
`--gpus 0,1`). Wave 202 P2 estimated wall time at ~40s per 10 records
across 2 GPUs (with `--workers-per-gpu 1`), so N=1000 ≈ 4000s ≈ 67 min
per arm — feasible on RTX PRO 6000 + RTX 5090.

## Supersession status

* Wave 198 P2/P3 lineageflow entry → **STILL APPLIES** (same data, same
  result, TIE on both metrics).
* Wave 199 P2/P3 lineageflow entry → **STILL APPLIES** (same data, same
  result, TIE on both metrics).
* Wave 202 P5 lineageflow entry → **NEW**: explicitly compares
  LineageFlow (VACUOUS at N=5 smoke) to k6_foldability_w161 (CONFIRMED
  monotone hard > medium > easy at N=1000) per Wave 202 P5 task spec,
  with honest BLOCKED-ON-DATA annotation.

## Files

* Script: `scripts/wave202_p5_lineageflow_per_record.py`
* Script: `scripts/wave202_p5_lineageflow_strata.py`
* CSV: `verification_outputs/wave202-p5-lineageflow-per-record.csv`
* JSON: `verification_outputs/wave202-p5-lineageflow-per-record.json`
* CSV: `verification_outputs/wave202-p5-lineageflow-strata.csv`
* JSON: `verification_outputs/wave202-p5-lineageflow-strata.json`
* Audit: `docs/audit/wave202-p5-lineageflow-per-record-and-strata.md`
  (this doc)

## Acceptance gate

* Per-record paired t-test on `plddt_mean` + `sc_perplexity` ✓
  (N=5, df=4, TIE on both)
* Difficulty-stratified (hard/medium/easy) paired t-test per metric ✓
  (medium SKIPPED due to N=1)
* Bonferroni alpha = 0.025 (per-record) and 0.00833 (strata) ✓
* Wave 193 P4 fix: p = 2 * scipy.stats.t.sf(abs(t), df) ✓
* Cross-adapter consistency vs k6_w161 (1.189 / 0.218 / -0.998) ✓ —
  documented as VACUOUS for LineageFlow N=5 smoke
* Honest BLOCKED-ON-DATA annotation per Wave 200 P2 commit `2bdd905` ✓
