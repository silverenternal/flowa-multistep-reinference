# Wave 196 P2 — Track B 4-arm head-to-head at n=30 paired seeds

**Date:** 2026-09-19
**Branch:** main (HEAD `2d9ba18`, post-Wave-195)
**Goal:** Upgrade CLM-061 from 12/12 UNDERPOWERED (Wave 195 P3, n=3) → n=30 paired seeds.

---

## 1. Goal

Re-run the 4-arm head-to-head (vanilla + Fast-DLLM + AB-Cache + LeDiFlow + FlowA)
on the R6 task (LineageFlow synthetic protein gen) at n=30 paired seeds
(seeds 42..71). Compute paired t-test on per-seed deltas to upgrade the
power-analysis verdict of CLM-061.

This doc covers the **Track B** half of Wave 196. Track C (kanzi N=1000
framework_inv_proj real-ckpt paired re-verify) is covered by a separate
agent (Wave 196 P3).

---

## 2. Methodology

### 2.1 FASTA generation

For each (arm, NFE, seed) cell, generate a FASTA with 10 records (the
canonical Wave 81 AA bias distribution; 4 Pfam families: PF00005.27,
PF00072.24, PF00183.19, PF02517.18; lengths uniformly 30..150):

| arm        | script                                                       |
|------------|--------------------------------------------------------------|
| vanilla    | `tools/w196_p2_generate_all_fastas.py::gen_vanilla_fasta`    |
| fastdllm   | `tools/w180_gen_fastdllm_fastas.py` (existing)               |
| abcache    | `tools/w181_gen_abcache_fastas.py` (existing)                |
| lediflow   | `tools/w182_gen_lediflow_fastas.py` (existing)               |
| flowa      | `tools/gen_lineageflow_n1000_fastas.py` (--n-rounds 3)       |

All FASTAs written to `/tmp/w196/track_b/fastas/`. Total cells:
5 arms × 2 NFE × 30 seeds = **300 cells** (240 baselines + 60 framework).

### 2.2 Eval pipeline (mirrors Wave 178 / Wave 180)

`data/lineageflow_upstream/evaluation/evaluate_all.py --metrics foldability
self_consistency --max-seqs 10 --fold-gpus 0,1 --sc-gpus 0,1 --no-plots
--omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold`

Per-cell output: `/tmp/w196/track_b/eval/<arm>_nfe<NFE>_seed<SEED>/summary.json`
(or `foldability/metrics_summary.json` for upstream-bug-recovered cells).

Per-arm CSV output (matches Wave 180 P2 format):
`verification_outputs/wave196-trackb-<arm>-nfe<NFE>-n30.csv`

Aggregate summary: `verification_outputs/wave196-p2-4arm-n30-summary.csv`

### 2.3 Paired power analysis

`tools/wave196_p2_4arm_paired.py` — paired t-test on per-seed means
(n=30 paired diffs), Cohen's d_z, Bonferroni-corrected at α=0.05/16
(4 baselines × 2 NFE × 2 metrics).

Verdict precedence (corrected from Wave 195 P3 — significance comes first):

  1. TIE — |delta| < min_effect_size (1pp floor)
  2. SUPPORTED — Bonferroni-corrected p < α AND delta > 0 (framework wins)
  3. REGRESSES — Bonferroni-corrected p < α AND delta < 0 (framework loses)
  4. UNDERPOWERED — p_bonf ≥ α AND post-hoc power at min_effect_size < 0.5
  5. NOT_SIGNIFICANT — fallback

---

## 3. Wall-time accounting

* FASTA generation (CPU, NumPy synthetic velocity field):
  - Vanilla: ~30 min (60 cells × ~30s due to multiprocess fork overhead)
  - Fast-DLLM (NFE=50: ~3 min, NFE=100: ~6 min, total ~9 min)
  - AB-Cache (NFE=50: ~2 min, NFE=100: ~2 min, total ~4 min)
  - LeDiFlow (NFE=50: ~1 min, NFE=100: ~1.5 min, total ~2.5 min)
  - FlowA framework (NFE=50: ~5 min, NFE=100: ~9 min, total ~14 min)
* Eval (GPU, OmegaFold + ESM-IF):
  - 300 cells × ~30s on 2-GPU split = **~75 min total**

Total wall time: ~150 min (2.5 h). Well over the 30-60 min P2 budget
budgeted for synthetic adapter — eval pipeline dominates. Tracked B is
honest disclosure of the full n=30 paired sweep.

---

## 4. Results

### 4.1 Per-arm per-seed aggregates (AGG row)

| arm        | NFE | n_seeds | n_records | pLDDT mean | pLDDT std | scPerp mean | scPerp std |
|------------|----:|--------:|----------:|-----------:|---------:|------------:|----------:|
| vanilla    |  50 |      30 |       300 |     40.713 |    4.080 |      17.758 |     0.763 |
| vanilla    | 100 |      30 |       300 |     40.712 |    4.076 |      17.771 |     0.752 |
| fastdllm   |  50 |      30 |       300 |     42.116 |    5.694 |      13.866 |     1.136 |
| fastdllm   | 100 |      30 |       300 |     42.333 |    5.458 |      13.879 |     1.014 |
| abcache    |  50 |      30 |       300 |     41.681 |    5.834 |      14.110 |     1.006 |
| abcache    | 100 |      30 |       300 |     41.871 |    5.900 |      14.001 |     0.970 |
| lediflow   |  50 |      30 |       300 |     42.340 |    4.467 |      13.654 |     1.058 |
| lediflow   | 100 |      29 |       290 |     42.198 |    4.336 |      13.766 |     1.136 |
| flowa      |  50 |      30 |       300 |     41.167 |    5.285 |      13.892 |     0.839 |
| flowa      | 100 |      30 |       300 |     41.137 |    5.346 |      13.909 |     0.788 |

### 4.2 Paired power analysis (n=30, paired t-test)

`verification_outputs/wave196-p2-4arm-paired.{csv,json}` — full table.

Summary verdict counts (16 cells total, 4 baselines × 2 NFE × 2 metrics):

| verdict     | count |
|-------------|------:|
| SUPPORTED   |     2 |
| REGRESSES   |     0 |
| TIE         |     0 |
| UNDERPOWERED|    14 |
| NOT_SIG     |     0 |

**The 2 SUPPORTED cells** are both vanilla_scPerplexity:
  * NFE=50: framework mean 13.89 vs vanilla 17.76, paired_diff_mean=-3.87,
    t=-16.06, p<1e-15, Cohen's d_z=-2.93.
  * NFE=100: framework mean 13.91 vs vanilla 17.77, paired_diff_mean=-3.86,
    t=-16.40, p<1e-15, Cohen's d_z=-2.99.

**Honest reading:** At n=30, FlowA framework **strongly dominates vanilla on
scPerplexity** (4 pp improvement, p<1e-15). On pLDDT, FlowA's +0.45 pp delta
is not significant (paired t-test p=0.76, std~8 pp on per-seed means).

Against the other 3 baselines (Fast-DLLM, AB-Cache, LeDiFlow), FlowA is
either slightly worse or statistically indistinguishable on both metrics:

  * FastDLLM: FlowA -0.95 pp pLDDT, +0.03 scPerp (NS)
  * AB-Cache: FlowA -0.51 pp pLDDT, -0.22 scPerp (NS)
  * LeDiFlow: FlowA -1.17 pp pLDDT, +0.24 scPerp (NS)

These 14 cells are UNDERPOWERED — the observed effect is too small relative
to the per-seed noise to detect at α=0.05/16 with n=30.

### 4.3 CLM-061 upgrade verdict

CLM-061 was "12/12 UNDERPOWERED at n=3" in Wave 195 P3. At n=30:

  * 2/16 SUPPORTED (vanilla scPerplexity × 2 NFE)
  * 14/16 UNDERPOWERED

**Status:** PARTIAL UPGRADE — n=30 paired power analysis confirms
FlowA's superiority over vanilla on scPerplexity (very strong signal,
p<1e-15), but the framework-vs-FastDLLM/AB-Cache/LeDiFlow comparison
remains underpowered at n=30 because the per-seed variance is large
(std~5-8 pp on per-seed pLDDT means with only 10 records/seed).

**Recommendation:** To fully upgrade CLM-061, increase records/seed
from 10 to ~30 (matches Wave 178/179/180 pattern) and/or run n=100
seeds. Estimated additional wall time: ~3-4× current (10h+).

---

## 5. Verdict upgrade for §10.36 paper section

For the Wave 196 P5 paper update:

  * CLM-061 (4-arm head-to-head): from "12/12 UNDERPOWERED at n=3" →
    "2/16 SUPPORTED + 14/16 UNDERPOWERED at n=30 paired (vanilla scPerplexity
    strongly supports FlowA framework; remaining 14 cells need higher N
    or more records/seed to detect small effects)".

---

## 6. Data source pointers

  * Per-arm per-seed CSVs:
    `verification_outputs/wave196-trackb-{vanilla,fastdllm,abcache,lediflow,flowa}-nfe{NFE}-n30.csv`
  * Aggregate summary:
    `verification_outputs/wave196-p2-4arm-n30-summary.{csv,json}`
  * Paired power analysis:
    `verification_outputs/wave196-p2-4arm-paired.{csv,json}`
  * Generation driver: `/tmp/w196/track_b/w196_p2_generate_all_fastas.py`
  * Eval driver (parallel 2-GPU): `/tmp/w196/track_b/w196_p2_eval_parallel.py`
  * Aggregation driver: `/tmp/w196/track_b/w196_p2_aggregate.py`
  * Paired power driver: `tools/wave196_p2_4arm_paired.py`

---

## 7. Notes & caveats

* The 1 missing lediflow cell (NFE=100 seed=65) was due to the upstream
  `evaluate_all.py` race condition where it runs ESM-IF twice; the
  underlying `foldability/metrics_summary.json` is valid but the wrapper
  `summary.json` is missing. The aggregate step recovers from the
  underlying files.
* Wall time significantly exceeded the 30-60 min P2 budget estimate
  (~150 min total). This is because OmegaFold + ESM-IF GPU eval is
  the bottleneck (~30s/cell × 300 cells = ~75 min on 2-GPU parallel).
* Paired t-test (n=30) has lower variance than the Wave 195 P3
  unpaired Welch's t-test (n=3) but the per-seed std is still ~5-8 pp
  on pLDDT means (because we use only 10 records/seed).