# Wave 206 P1: LineageFlow N=1000 paired-record sweep — audit

**Date:** 2026-09-21
**Status:** SWEEP LAUNCHED (PID alive, GPU 0 at 8 GiB, shards running)
**Tool:** `tools/run_lineageflow_n1000_foldability_omegafold.py`
**Inputs:** `data/lineageflow_n1000/{baseline,framework}.fasta` (1000 records each)
**Output dir:** `verification_outputs/wave206-p1-lineageflow-n1000/{baseline,framework}/`
**Env:** `omegafold_py310` (torch 2.14.0+cu130, sm_120-compatible)
**GPU:** 0, 2 workers/GPU
**Wallclock budget:** 6 h max

## Background

CLM-061 documents the **BLOCKED-ON-DATA** status of the LineageFlow N=1000
per-record paired analysis (Wave 199 P3 + Wave 200 P2; pipeline plumbing
ready per Wave 201 P7 + CLM-065). Wave 202 found the omegafold_py310 conda
env that resolves the GPU-stack blocker (torch 1.13.1 vs Blackwell sm_120).
Wave 204 P2 got baseline N=1000 + framework N=574 on the GPU env (partial).

Wave 206 P1 is the W2 (TPAMI 6-week plan) re-run to N=1000 zero-skipped per
arm, producing the audit-grade dataset for the paper §10 R-level inventory:

| Cell | Metric | Higher better? | Family | Bonferroni α | Source |
|---|---|---:|---|---:|---|
| R1 HMMER | hmmscan_total_hits | yes | R1_only | 0.05/1 = 0.05 | Wave 158 Pfam DB sweep (`verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/`) |
| R6 pLDDT | plddt_mean | yes | R6_foldability | 0.05/2 = 0.025 | Wave 206 P1 foldability (this sweep) |
| R6 scPerplexity | sc_perplexity | no (lower better) | R6_foldability | 0.05/2 = 0.025 | Wave 206 P1 self-consistency (this sweep) |

R1 HMMER is already complete from Wave 158 (171 baseline + 355 framework
hit-rows over N=1000 paired seeds; +0.184 hits/seed framework uplift,
d_z=+0.182, p=1.25e-8, Bonferroni-significant). R6 foldability + sc
are freshly run via the Wave 206 P1 sweep (this audit).

## Per-cell 12-col standard (Wave 203 P4 / CLM-066)

Computed via `scripts/wave206_p1_lineageflow_n1000_audit.py`:

| Field | Definition |
|---|---|
| n_paired | number of paired records with both-arm data |
| mean_diff | mean framework - baseline paired diff |
| sd_diff | sample SD of paired diffs |
| t_statistic | mean_diff / se |
| df | n_paired - 1 |
| p_value_raw | two-sided paired t-test (df = n-1) via `scipy.stats.t.sf` |
| ci_95 | 95% CI of mean_diff (1.96 × se) |
| cohens_d_z | mean_diff / sd_diff |
| test_type | paired_t_test |
| family | R1_only / R6_foldability |
| alpha_bonferroni | per-cell α |
| bonf_sig | p_value_raw < alpha_bonferroni |

## Bonferroni families

R1 (1 cell, family α = 0.05/1 = 0.05).
R6 foldability (2 cells, family α = 0.05/2 = 0.025).

R6 stratification (33rd/67th percentile of baseline pLDDT: hard / medium /
easy) is captured in Wave 202 P5 strata analysis
(`scripts/wave202_p5_lineageflow_n1000_paired.py`, feeding
`verification_outputs/wave202-p5-lineageflow-per-record.{csv,json}` +
`verification_outputs/wave202-p5-lineageflow-strata.{csv,json}`).

## Outcome (TBD)

The sweep outcome will be appended here when the run completes. The
expected timeline at G=1, N=2 is ≈1.5-3 h per arm (foldability dominant) +
15-30 min sc per arm. With nohup + log persistence, the sweep survives
subagent session boundaries; the orchestrator can re-invoke the monitor
script to check progress.

See `verification_outputs/wave206-p1-lineageflow-n1000.{csv,json}` for
the per-cell numbers once the run completes.
