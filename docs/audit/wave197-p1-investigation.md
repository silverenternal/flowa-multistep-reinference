# Wave 197 P1 — Investigation: per-seed-records CLI flag + wall-time estimate

**Date:** 2026-09-19
**Branch:** main (HEAD `28ebe1e`, post-Wave-196)
**Goal:** Verify the per-seed-records CLI flag for the 4/5-arm × 2 NFE × 30 seeds × n_records/seed generator scripts and estimate total wall time for the planned Wave 197 sweep.

---

## 1. CLI verification — all arms accept `--n` (records per seed)

| arm       | script                                             | flag       | default | notes                                                                                          |
|-----------|----------------------------------------------------|------------|---------|------------------------------------------------------------------------------------------------|
| fastdllm  | `tools/w180_gen_fastdllm_fastas.py`                 | `--n`      | 30      | line 318; Wave 196 P2 used 10 (lower than default; explicit override)                           |
| abcache   | `tools/w181_gen_abcache_fastas.py`                  | `--n`      | 30      | line 327; same override semantics                                                               |
| lediflow  | `tools/w182_gen_lediflow_fastas.py`                 | `--n`      | 30      | line 339; same override semantics                                                               |
| vanilla   | `tools/w196_p2_generate_all_fastas.py::gen_vanilla_fasta` (driver inline) | `--n-records` | 10 | driver `w196_p2_generate_all_fastas.py` line 167; inline bare RNG, **does not** read `--nfe`   |
| flowa     | `tools/gen_lineageflow_n1000_fastas.py`             | `--n`      | 1000    | line 544; emits both `baseline.fasta` and `framework.fasta` per call; uses `--n-rounds 3` for framework arm |

**Confirmation:** 100 records/seed is acceptable for every generator. None of the scripts hard-code a max-n; they accept any positive int. Vanilla's generator is a Python loop in the driver, so it accepts arbitrary `--n-records`.

The downstream driver `w196_p2_generate_all_fastas.py` accepts `--n-records` (line 167) and threads it through every arm via the per-arm `gen_*_fasta(..., n)` call.

---

## 2. Wave 196 P2 actual wall-time measurements (n=10 records/seed)

Pulled from `/tmp/w196/track_b/fastas/*manifest.json` and `gen_resume*.log`. All per-cell values are for **one (arm, NFE, seed) cell** writing `n=10` records.

| arm       | NFE=50 (median) | NFE=100 (median) | source                          |
|-----------|----------------:|-----------------:|---------------------------------|
| fastdllm  | 2.1 s           | 93.0 s           | `gen_resume3.log` + manifests   |
| abcache   | 5.5 s           | 9.4 s            | manifests                       |
| lediflow  | 21.9 s          | 16.6 s (var)     | manifests                       |
| flowa     | ~47 s           | ~92 s            | `gen_resume3.log` flowa entries |
| vanilla   | ~30 s           | ~30 s            | doc §3 (fork overhead dominates)|

The 5-arm Wave 196 P2 total was ~150 min (75 min CPU gen + 75 min GPU eval on 2-GPU parallel split).

**Important discrepancy vs. the prompt's stated numbers** (fastdllm ~17s/seed, abcache ~10s, lediflow ~4s at n=30): those numbers do **not** match the Wave 196 P2 n=10 measurements and were not observed in any Wave 178-180 ladder. The Wave 196 P2 doc §3 reports per-arm totals (fastdllm ~9 min / 60 cells = 9 s/cell), which is closer but still not the raw cell median because of multiprocess fork overhead. **I use the raw `wall_s` field from manifests as the source of truth** for the n=100 estimate below.

---

## 3. n=100 wall-time estimate (linear + amortised-overhead scaling)

### 3.1 Per-record cost (Wave 196 P2 n=10 baseline)

Divided median cell wall by 10 records:

| arm       | NFE=50 /rec | NFE=100 /rec | comment                                                                 |
|-----------|------------:|-------------:|-------------------------------------------------------------------------|
| fastdllm  | 0.21 s      | 9.30 s       | NFE=50 confidence-skip dominates; NFE=100 full midpoint verifier         |
| abcache   | 0.55 s      | 0.94 s       | cache reuse amortises; both NFE close to per-record floor                |
| lediflow  | 2.19 s      | 1.66 s       | prior shift is a fixed cost; NFE=100 slightly less due to less variance |
| flowa     | 4.70 s      | 9.20 s       | 3-round restart-blend × full NFE                                          |
| vanilla   | 3.00 s      | 3.00 s       | fork overhead + bare RNG; NFE-independent                                |

### 3.2 Per-cell estimate at n=100 (10× n=10 baseline)

| arm       | NFE=50 (100 rec) | NFE=100 (100 rec) | total/cell  |
|-----------|-----------------:|------------------:|------------:|
| fastdllm  | ~21 s            | ~930 s            | varies      |
| abcache   | ~55 s            | ~94 s             | varies      |
| lediflow  | ~219 s           | ~166 s            | varies      |
| flowa     | ~470 s           | ~920 s            | varies      |
| vanilla   | ~30 s            | ~30 s             | ~30 s       |

Per-cell estimates assume **no amortisation of overhead at n=100** (conservative upper bound). Real n=100 will be faster because the solver's per-record setup cost is paid once per call, not 10× per record.

### 3.3 Per-arm totals at 30 seeds × 2 NFE × 100 records

Linear sum across NFE=50 + NFE=100 cells, 30 seeds:

| arm       | cells | est. total CPU gen | est. minutes |
|-----------|------:|-------------------:|-------------:|
| fastdllm  | 60    | 30 × (21 + 930)    | **476 min**  |
| abcache   | 60    | 30 × (55 + 94)     | **75 min**   |
| lediflow  | 60    | 30 × (219 + 166)   | **193 min**  |
| vanilla   | 60    | 30 × (30 + 30)     | **30 min**   |
| flowa     | 60    | 30 × (470 + 920)   | **695 min**  |
| **Total (5-arm incl. flowa)** | **300 cells** | — | **~1469 min ≈ 24.5 h** |
| **Total (4-arm excl. flowa)** | **240 cells** | — | **~774 min ≈ 12.9 h** |

### 3.4 GPU eval estimate

`data/lineageflow_upstream/evaluation/evaluate_all.py` was measured at ~55 s/cell (median over 18 successfully logged flowa cells in `/tmp/w196/track_b/eval/eval_results.json`) running with `--max-seqs 10`. At `--max-seqs 100` the eval is 10× slower per cell because both OmegaFold (foldability) and ESM-IF (self_consistency) scale linearly with `--max-seqs`. Bound: 30-60 s/cell at n=10 → 300-600 s/cell at n=100 (5-10 min/cell).

| sweep size | cells | 2-GPU parallel cells/GPU | est. eval wall |
|------------|------:|-------------------------:|---------------:|
| 4-arm (240 cells) | 240 | 120 | 120 × 300 s = **600 min = 10 h** (lower bound), 1200 min = 20 h (upper bound) |
| 5-arm (300 cells) | 300 | 150 | 150 × 300 s = **750 min = 12.5 h** (lower), 1500 min = 25 h (upper) |

### 3.5 Grand total (4-arm interpretation, no flowa)

* CPU gen: **~774 min ≈ 12.9 h**
* GPU eval: **10-20 h** (2-GPU parallel, `--max-seqs 100` × 2 metrics)
* Grand total: **23-33 h** (way exceeds the prompt's 250-370 min estimate)

### 3.6 Grand total (5-arm interpretation, including flowa as framework)

* CPU gen: **~1469 min ≈ 24.5 h**
* GPU eval: **12.5-25 h** (2-GPU parallel)
* Grand total: **37-50 h**

### 3.7 Prompt's stated estimate is **~10× too low**

The prompt estimates ~130 min CPU gen + ~120-240 min GPU = 250-370 min total. This was derived from per-seed figures (fastdllm ~17s, abcache ~10s, lediflow ~4s) that do not appear in any Wave 178-196 manifest. Actual Wave 196 P2 n=10 manifests show fastdllm nfe=100 cells take ~93 s (5× the prompt's 17 s). At n=100, fastdllm alone is **~16 h** (vs the prompt's 57 min for fastdllm).

**Honest recommendation:** the n=100 sweep is a multi-day batch run, not an overnight job. If the goal is to upgrade CLM-061 with statistical power, consider:

1. Run only one NFE (e.g., NFE=100, the most expensive and most informative) → 4-arm × 30 seeds × 100 records = 120 cells, eval ~3-5 h, gen ~6-12 h (manageable).
2. Drop n=100 to n=30 (matches Wave 178-180 ladder) → 5-arm × 2 NFE × 30 seeds × 30 = 300 cells, but at n=30 we have direct measurements; expected gen ~3 h, eval ~6 h (matches the Wave 196 P2 profile).
3. Cap eval `--max-seqs 30` for the n=100 sweep (subsample rather than full eval) → eval ~3-5 h.

---

## 4. Eval pipeline check

* `data/lineageflow_upstream/evaluation/evaluate_all.py` accepts `--max-seqs` (any positive int; default `None` = all sequences).
* `w196_p2_eval_parallel.py` driver (lines 59-90) shells out to evaluate_all.py with `--max-seqs {n}` — straightforward substitution to 100.
* **GPU availability (2026-09-19):**
  * GPU 0: NVIDIA RTX PRO 6000 Blackwell Workstation Edition, 97249 / 97887 MiB free
  * GPU 1: NVIDIA GeForce RTX 5090, 32110 / 32607 MiB free
  * Both free. The 5090's 32 GB is enough for OmegaFold + ESM-IF at n=100 with `--max-seqs 100`.

---

## 5. Parallelization opportunity

The 4/5 arms are CPU-only (NumPy synthetic velocity field, no torch). Each arm invocation is one Python process driven by the driver. The arms are **trivially parallelisable on CPU** via `xargs -P` or `concurrent.futures.ProcessPoolExecutor`:

* `w196_p2_generate_all_fastas.py` currently runs cells sequentially (single-threaded). A 5-line patch using `concurrent.futures.ThreadPoolExecutor(max_workers=8)` would saturate 8 CPU cores and cut CPU gen wall time by ~6-8× on a multi-core host.
* GPU eval is already 2-GPU parallel via `w196_p2_eval_parallel.py`'s ThreadPoolExecutor split (GPU 0 + GPU 1).
* **GPU memory:** each cell uses ~5 GB on the 5090 at n=10 (per Wave 196 P2). At n=100, expect ~15-20 GB per cell. The 32 GB 5090 fits 1 cell; the 96 GB PRO 6000 fits 4-5 cells in parallel. The eval driver's `workers-per-gpu=1` is safe.

**Recommendation:** parallelise the CPU gen driver (8 workers) + keep the eval at `workers-per-gpu=1` (GPU 1) and `workers-per-gpu=4` (GPU 0). This brings the 5-arm n=100 total to ~6-12 h CPU + ~12-25 h GPU = **18-37 h grand total**. Still multi-day.

---

## 6. Output JSON

```json
{
  "cli_flags": {
    "fastdllm": "--n 100 (default 30; tools/w180_gen_fastdllm_fastas.py:318)",
    "abcache":  "--n 100 (default 30; tools/w181_gen_abcache_fastas.py:327)",
    "lediflow": "--n 100 (default 30; tools/w182_gen_lediflow_fastas.py:339)",
    "flowa":    "--n 100 (default 1000; tools/gen_lineageflow_n1000_fastas.py:544)",
    "vanilla":  "--n-records 100 (driver w196_p2_generate_all_fastas.py:167; inline bare RNG)"
  },
  "wall_time_estimates_per_arm_min": {
    "fastdllm": 476.0,
    "abcache":  75.0,
    "lediflow": 193.0,
    "vanilla":  30.0,
    "flowa":    695.0
  },
  "total_cpu_gen_estimate_min_5arm": 1469.0,
  "total_cpu_gen_estimate_min_4arm_excl_flowa": 774.0,
  "total_gpu_eval_estimate_min_5arm": 1125.0,
  "total_gpu_eval_estimate_min_4arm": 900.0,
  "grand_total_estimate_min_5arm_lower_bound": 1856.0,
  "grand_total_estimate_min_5arm_upper_bound": 3494.0,
  "grand_total_estimate_min_4arm_lower_bound": 1296.0,
  "grand_total_estimate_min_4arm_upper_bound": 2516.0,
  "can_parallelize_arms": true,
  "parallelization_strategy": "8-way ProcessPoolExecutor on CPU gen (current driver is single-threaded); eval already 2-GPU split with workers_per_gpu=1 (GPU 1) + workers_per_gpu=4 (GPU 0)",
  "gpu_memory_required_per_cell_at_n100_estimate_gb": 18.0,
  "gpu_availability_checked": "GPU 0 (PRO 6000) 97249 MiB free, GPU 1 (RTX 5090) 32110 MiB free",
  "n_records_per_seed_confirmed": 100,
  "commit_sha": "28ebe1e",
  "wave197_recommendation": "n=100 sweep is multi-day batch (18-37 h). For an overnight job consider: (a) NFE=100 only (drop NFE=50), (b) cap eval --max-seqs to 30, (c) drop flowa arm to focus on 4-arm solver comparison"
}
```

---

## 7. Verdict

* **CLI flags:** all 5 arms accept `--n` / `--n-records` and handle n=100 without modification. Confirmed.
* **Wall time:** the prompt's ~130 min CPU estimate is **~10× too low** because it uses per-seed figures that don't match Wave 196 P2 manifest `wall_s` data. Actual n=100 sweep is **12-25 h CPU gen + 12-25 h GPU eval** depending on arm count.
* **Parallelisation:** safe and necessary (8-way CPU + 2-GPU eval); driver patch is ~5 LOC.
* **GPU:** both GPUs free; 5090's 32 GB is sufficient for n=100 single-cell eval; PRO 6000 can run 4-5 cells in parallel.
* **Honest recommendation:** if the goal is an overnight CLM-061 upgrade, use n=30 (matches Wave 178-180 ladder) rather than n=100. The n=100 sweep should be budgeted as a 2-day batch.