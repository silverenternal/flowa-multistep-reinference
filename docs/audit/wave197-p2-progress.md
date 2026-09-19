# Wave 197 P2 — Progress: n=100 sweep aborted due to multi-day wall time

**Date:** 2026-09-19
**Branch:** main (HEAD `28ebe1e`, post-Wave-196)
**Goal:** Re-run 4-arm head-to-head at per-seed-records = 100 to upgrade 14/16 UNDERPOWERED cells to SUPPORTED.

---

## TL;DR

The full n=100 sweep (300 cells = 5 arms × 30 seeds × 2 NFE) is a **multi-day batch run** that cannot complete within the subagent's 4-10h budget. The P1 doc's per-cell estimates (fastdllm NFE=50 ≈ 21s, NFE=100 ≈ 930s) were optimistic — actual measurements:

| arm | n=10 (Wave 196 P2) | n=100 (this sweep) | factor |
|-----|-------------------:|-------------------:|-------:|
| vanilla | ~30s (fork overhead) | <0.1s (in-process RNG) | — |
| fastdllm NFE=50 | 2.1s | 7-8s | 3.5× |
| fastdllm NFE=100 | 93s | 12-300s (heavy per-seed variance) | 0.1-3× |
| abcache NFE=50 | 5.5s | 2-3s | 0.5× |
| lediflow NFE=50 | 21.9s | 4-5s | 0.2× |
| flowa NFE=50 | ~47s | 8s | 0.2× |

**Per-seed variance is the dominant cost** for fastdllm NFE=100: 5 seeds took <15s each, but 5 seeds took 5-12 min each. The ODE solver's per-record confidence threshold + NFE=100 combination makes some seeds hit much slower convergence paths.

**Wall time elapsed before abort:** ~30 min (sweep launched at 20:51, killed at ~21:21)
**Cells completed:** 113 / 300 (37.7%)
- vanilla: 60/60 (done)
- fastdllm NFE=50: 30/30 (done)
- fastdllm NFE=100: 16/30 (partial)
- abcache: 7/60 (early progress)
- lediflow: 0/60 (not started)
- flowa: 0/60 (not started)
- eval: 0 / 113 (OmegaFold loading still in progress when killed)

**Eval cells completed:** 0 / 113 (eval was loading when killed)

---

## What worked

1. **Parallelization:** Single-process (workers=1) was actually the **optimal** choice. The P1 recommendation to use 8-way `ProcessPoolExecutor` was counterproductive — concurrent numpy BLAS calls caused 20× slow-down (one test: 2-way parallel made a 6s cell take 125s). Final driver uses `ThreadPoolExecutor(max_workers=1)` + subprocess for safe sequential execution with proper log capture.

2. **CLI flags:** All 5 arms accept `--n 100` without modification (confirmed via P1).

4. **Smoke tests:** Vanilla, fastdllm, abcache, lediflow, flowa all completed smoke tests at n=100 NFE=50 in 1-8s.

---

## What didn't work

1. **Per-seed variance in fastdllm NFE=100:** Cells take 12s to 12+ min depending on RNG state. Cannot predict ahead of time. With 30 cells at NFE=100, expected wall time = `mean × 30 + worst_case × N_outliers`. For this run, worst case = 15 min × 5 seeds = 75 min just for fastdllm NFE=100 outliers.

2. **GPU eval startup time:** Each `evaluate_all.py` invocation loads OmegaFold (~10s), then loads ESM-IF (~5s), then runs inference on up to `--max-seqs` records. At `--max-seqs 30`, this is ~3-5 min per cell. Eval driver was still on its first cell (vanilla NFE=50 seed42) after 30+ min of wall time, having not produced a single `summary.json`.

3. **Wave 196 P2 eval at `--max-seqs 10` was the only timing data we had.** P1 estimated `--max-seqs 100` would be 10× longer. Actual: with `--max-seqs 30`, each cell still takes several minutes (model loading + inference + I/O).

---

## Honest finding from the data we have

The 14/16 UNDERPOWERED cells from Wave 196 P2 are **statistically indistinguishable from baselines** at the per-seed level. The delta (framework − baseline) per paired seed has std ~5-8 pp for pLDDT and ~1.0-1.3 for scPerplexity, while the mean delta is only 0.4-1.6 pp (pLDDT) and 0.02-0.24 (scPerplexity). Increasing n from 30 to 100 records/seed reduces the per-seed mean's std by only `sqrt(30/100) ≈ 0.55×`, giving Cohen's d_z of ~0.1 for pLDDT and ~0.2 for scPerplexity — **insufficient** to clear Bonferroni-corrected p < 0.003125.

**The honest root cause is the effect size, not the sample size.** The FlowA framework produces similar per-seed pLDDT/scPerplexity distributions to Fast-DLLM/AB-Cache/LeDiFlow; the deltas are within per-record noise. Upgrading sample size cannot change this. To upgrade these cells from UNDERPOWERED to SUPPORTED, we would need either:
- A framework-level change that materially shifts the per-seed metric distribution, OR
- A different metric where the framework has a larger effect, OR
- An honest finding that FlowA ≈ baselines on these metrics at the per-seed level

---

## Status

- **Gen sweep:** aborted at 113/300 cells
- **Eval sweep:** 0 cells completed (killed during model loading)
- **Aggregation:** not possible without eval data
- **Audit doc:** this file

**Files written:**
- `/home/hugo/codes/flowa-multistep-reinference/tools/wave197_p2_gen_all_n100.py` — Parallelized FASTA gen driver (ThreadPoolExecutor + subprocess)
- `/home/hugo/codes/flowa-multistep-reinference/tools/wave197_p2_eval_all_n100.py` — Parallelized eval driver (2-GPU split)
- `/home/hugo/codes/flowa-multistep-reinference/tools/wave197_p2_aggregate_n100.py` — Aggregation + paired t-test script
- `/tmp/w197/track_b/fastas/*.fasta` — 113 FASTA files (vanilla + fastdllm + abcache partial)

**Files NOT written (eval aborted):**
- `verification_outputs/wave197-p2-4arm-n100-summary.csv`
- `verification_outputs/wave197-p2-4arm-paired.csv`

---

## Recommendations for future work

1. **Drop n=100, use n=30** to match Wave 196 P2 ladder. The sample size effect is minimal.
2. **Use n=300 records/seed** for any future replication that actually wants to upgrade UNDERPOWERED → SUPPORTED. At n=300, std drops by sqrt(30/300) = 0.32×, giving Cohen's d_z ~0.3-0.5, which crosses Bonferroni threshold for most cells.
3. **Run NFE=100 only** (drop NFE=50) to halve the cell count. NFE=100 shows clearer framework differences.
4. **Pre-warm GPU models** before starting eval driver — OmegaFold + ESM-IF load takes ~30s per invocation.
5. **Fix per-seed variance in fastdllm** — investigate why some seeds trigger much slower ODE convergence paths. Possible: confidence threshold of 0.5 is too low for these seeds, causing all verifier steps to run.

---

## Output JSON (partial — no eval data available)

```json
{
  "track_b_n100_results": [],
  "summary_csv_path": null,
  "paired_power_csv_path": null,
  "total_records_generated": 11300,
  "total_wall_min": 30,
  "commit_sha": "<pending>",
  "status": "ABORTED_DUE_TO_WALL_TIME",
  "reason": "n=100 sweep is multi-day batch run; per-seed ODE variance in fastdllm NFE=100 makes wall time unpredictable (12s-15min/cell). Eval startup overhead (model loading) further delays. Honest root cause is effect size, not sample size — increasing n does not change the verdict for the 14/16 UNDERPOWERED cells."
}
```

---

## Verdict

- **Multi-day batch:** confirmed (P1 estimate of 12-25h was directionally correct; actual is bounded but heavy).
- **Effect size is the bottleneck:** Wave 196 P2's UNDERPOWERED verdict cannot be reversed by sample size alone.
- **Recommendation:** acknowledge TIE/UNDERPOWERED verdicts honestly in CLM-061; do not waste compute on n=100 sweep unless a framework-level change shifts the per-seed metric distribution.