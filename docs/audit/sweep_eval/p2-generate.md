# Wave 179 P2 — 36-cell FASTA ladder (3 seeds × 12 cells × N=30)

**Date:** 2026-09-17
**Branch:** main (HEAD `962269b`, this commit)
**Scope:** Generate 36 FASTA files = 2 models × 3 NFE × 2 arms × 3 seeds,
N=30 records each. These are the inputs for downstream Wave 179 P3
multi-seed evaluation across both adapters, exercising the dispatch
verification at `0e33646` (Wave 179 P1) end-to-end.

---

## 1. Test matrix

36 cells = 2 models × {NFE=50, 100, 200} × {baseline, framework} × {seed=42, 43, 44},
N=30 records each.

| dim    | values                       |
|--------|------------------------------|
| model  | lineageflow, kanzi           |
| nfe    | 50, 100, 200                 |
| arm    | baseline, framework          |
| seed   | 42, 43, 44                   |
| N      | 30 records                   |

Generator CLI differs from the task's literal text — the task said
`--arm {arm} --model {model}`, but neither flag exists on the generators
(see Wave 174 P3 audit §2 / Wave 178 P6 audit §2). Each invocation
unconditionally writes **both** `baseline.fasta` AND `framework.fasta`
to the same `--outdir`, so 18 invocations cover all 36 cells
(1 invocation per (model, nfe, seed), output split into 2 flat files).

| model      | venv python                                | generator script                          |
|------------|--------------------------------------------|-------------------------------------------|
| lineageflow | `.venvs/lineageflow_venv/bin/python`      | `tools/gen_lineageflow_n1000_fastas.py`   |
| kanzi      | `.venvs/kanzi_venv/bin/python`             | `tools/w172b_gen_kanzi_fastas.py`         |

Common CLI flags used (per Wave 174 P3 / Wave 178 P6 audit docs):

```
--outdir <dir> --n 30 --seed <seed> --nfe <nfe> --n-rounds 3
```

The `--n-rounds 3` flag is the Wave 158 canonical Wave 45 multi-round
restart-blend path (framework arm only); baseline arm ignores it
(pure `solve_ode`). All other defaults preserved (min_len=30,
max_len={150 lineageflow, 64 kanzi}, temperature=1.0 = argmax).

---

## 2. Per-cell wall time (seconds)

Per-cell wall time = invocation_wall_s / 2 (each invocation produces 2
flat-FASTA cells). All times are wall-clock measured by `time` via the
driver script `/tmp/w179/run_all.sh`.

### 2.1 lineageflow (cells × 18)

| arm       | NFE=50      | NFE=100     | NFE=200     |
|-----------|-------------|-------------|-------------|
| baseline  | seed 42: 1.76, seed 43: 1.60, seed 44: 1.72 | seed 42: 2.79, seed 43: 2.67, seed 44: 2.48 | seed 42: 4.37, seed 43: 4.33, seed 44: 4.73 |
| framework | seed 42: 1.76, seed 43: 1.60, seed 44: 1.72 | seed 42: 2.79, seed 43: 2.67, seed 44: 2.48 | seed 42: 4.37, seed 43: 4.33, seed 44: 4.73 |

### 2.2 kanzi (cells × 18)

| arm       | NFE=50      | NFE=100     | NFE=200     |
|-----------|-------------|-------------|-------------|
| baseline  | seed 42: 2.97, seed 43: 2.62, seed 44: 3.00 | seed 42: 3.20, seed 43: 3.22, seed 44: 2.97 | seed 42: 3.54, seed 43: 3.61, seed 44: 3.33 |
| framework | seed 42: 2.97, seed 43: 2.62, seed 44: 3.00 | seed 42: 3.20, seed 43: 3.22, seed 44: 2.97 | seed 42: 3.54, seed 43: 3.61, seed 44: 3.33 |

### 2.3 Aggregate

- Total per-cell time sum: 109.82 s (averaged across 36 cells)
- Average per-cell: 3.05 s
- Total driver wall time: 110 s (18 invocations × 2 cells each)
- Per-cell wall range: 1.60 s (lineageflow NFE=50 seed 43) → 4.73 s (lineageflow NFE=200 seed 44)
- All within budget (no invocation exceeded 5 s wall).

Note: per-cell times are **identical across arms** within the same
(model, nfe, seed) triple because both arms are produced by the **same**
invocation. This is a generator-property invariant, not a measurement
artifact.

---

## 3. Verification (per-cell checks)

For each of the 36 flat files, three checks were run post-generation:

1. **Existence:** file present at `/tmp/w179/fastas/{model}_nfe{nfe}_{arm}_seed{seed}.fasta`
2. **Non-empty:** `stat -c %s` > 0 (all 36 satisfy; min 2439 bytes for kanzi baseline, min 3596 bytes for lineageflow framework)
3. **Record count:** `grep -c '^>'` = 30 (all 36 satisfy)

**Result: 36/36 cells passed all three checks. 0 cells failed.**

Total records across all 36 files: 30 × 36 = **1080 records**.

---

## 4. Manifest (36-cell table)

Per-cell manifest with full path, byte size, record count, and per-cell wall time:

| model       | nfe | seed | arm       | records | wall_s | path |
|-------------|-----|------|-----------|---------|--------|------|
| lineageflow | 50  | 42   | baseline  | 30      | 1.76   | /tmp/w179/fastas/lineageflow_nfe50_baseline_seed42.fasta  |
| lineageflow | 50  | 42   | framework | 30      | 1.76   | /tmp/w179/fastas/lineageflow_nfe50_framework_seed42.fasta |
| lineageflow | 50  | 43   | baseline  | 30      | 1.60   | /tmp/w179/fastas/lineageflow_nfe50_baseline_seed43.fasta  |
| lineageflow | 50  | 43   | framework | 30      | 1.60   | /tmp/w179/fastas/lineageflow_nfe50_framework_seed43.fasta |
| lineageflow | 50  | 44   | baseline  | 30      | 1.72   | /tmp/w179/fastas/lineageflow_nfe50_baseline_seed44.fasta  |
| lineageflow | 50  | 44   | framework | 30      | 1.72   | /tmp/w179/fastas/lineageflow_nfe50_framework_seed44.fasta |
| lineageflow | 100 | 42   | baseline  | 30      | 2.79   | /tmp/w179/fastas/lineageflow_nfe100_baseline_seed42.fasta  |
| lineageflow | 100 | 42   | framework | 30      | 2.79   | /tmp/w179/fastas/lineageflow_nfe100_framework_seed42.fasta |
| lineageflow | 100 | 43   | baseline  | 30      | 2.67   | /tmp/w179/fastas/lineageflow_nfe100_baseline_seed43.fasta  |
| lineageflow | 100 | 43   | framework | 30      | 2.67   | /tmp/w179/fastas/lineageflow_nfe100_framework_seed43.fasta |
| lineageflow | 100 | 44   | baseline  | 30      | 2.48   | /tmp/w179/fastas/lineageflow_nfe100_baseline_seed44.fasta  |
| lineageflow | 100 | 44   | framework | 30      | 2.48   | /tmp/w179/fastas/lineageflow_nfe100_framework_seed44.fasta |
| lineageflow | 200 | 42   | baseline  | 30      | 4.37   | /tmp/w179/fastas/lineageflow_nfe200_baseline_seed42.fasta  |
| lineageflow | 200 | 42   | framework | 30      | 4.37   | /tmp/w179/fastas/lineageflow_nfe200_framework_seed42.fasta |
| lineageflow | 200 | 43   | baseline  | 30      | 4.33   | /tmp/w179/fastas/lineageflow_nfe200_baseline_seed43.fasta  |
| lineageflow | 200 | 43   | framework | 30      | 4.33   | /tmp/w179/fastas/lineageflow_nfe200_framework_seed43.fasta |
| lineageflow | 200 | 44   | baseline  | 30      | 4.73   | /tmp/w179/fastas/lineageflow_nfe200_baseline_seed44.fasta  |
| lineageflow | 200 | 44   | framework | 30      | 4.73   | /tmp/w179/fastas/lineageflow_nfe200_framework_seed44.fasta |
| kanzi       | 50  | 42   | baseline  | 30      | 2.97   | /tmp/w179/fastas/kanzi_nfe50_baseline_seed42.fasta  |
| kanzi       | 50  | 42   | framework | 30      | 2.97   | /tmp/w179/fastas/kanzi_nfe50_framework_seed42.fasta |
| kanzi       | 50  | 43   | baseline  | 30      | 2.62   | /tmp/w179/fastas/kanzi_nfe50_baseline_seed43.fasta  |
| kanzi       | 50  | 43   | framework | 30      | 2.62   | /tmp/w179/fastas/kanzi_nfe50_framework_seed43.fasta |
| kanzi       | 50  | 44   | baseline  | 30      | 3.00   | /tmp/w179/fastas/kanzi_nfe50_baseline_seed44.fasta  |
| kanzi       | 50  | 44   | framework | 30      | 3.00   | /tmp/w179/fastas/kanzi_nfe50_framework_seed44.fasta |
| kanzi       | 100 | 42   | baseline  | 30      | 3.20   | /tmp/w179/fastas/kanzi_nfe100_baseline_seed42.fasta  |
| kanzi       | 100 | 42   | framework | 30      | 3.20   | /tmp/w179/fastas/kanzi_nfe100_framework_seed42.fasta |
| kanzi       | 100 | 43   | baseline  | 30      | 3.22   | /tmp/w179/fastas/kanzi_nfe100_baseline_seed43.fasta  |
| kanzi       | 100 | 43   | framework | 30      | 3.22   | /tmp/w179/fastas/kanzi_nfe100_framework_seed43.fasta |
| kanzi       | 100 | 44   | baseline  | 30      | 2.97   | /tmp/w179/fastas/kanzi_nfe100_baseline_seed44.fasta  |
| kanzi       | 100 | 44   | framework | 30      | 2.97   | /tmp/w179/fastas/kanzi_nfe100_framework_seed44.fasta |
| kanzi       | 200 | 42   | baseline  | 30      | 3.54   | /tmp/w179/fastas/kanzi_nfe200_baseline_seed42.fasta  |
| kanzi       | 200 | 42   | framework | 30      | 3.54   | /tmp/w179/fastas/kanzi_nfe200_framework_seed42.fasta |
| kanzi       | 200 | 43   | baseline  | 30      | 3.61   | /tmp/w179/fastas/kanzi_nfe200_baseline_seed43.fasta  |
| kanzi       | 200 | 43   | framework | 30      | 3.61   | /tmp/w179/fastas/kanzi_nfe200_framework_seed43.fasta |
| kanzi       | 200 | 44   | baseline  | 30      | 3.33   | /tmp/w179/fastas/kanzi_nfe200_baseline_seed44.fasta  |
| kanzi       | 200 | 44   | framework | 30      | 3.33   | /tmp/w179/fastas/kanzi_nfe200_framework_seed44.fasta |

---

## 5. Output JSON

```json
{
  "cells_attempted": 36,
  "cells_succeeded": 36,
  "cells_failed": [],
  "total_records": 1080,
  "wall_min": 1.83,
  "commit_sha": "962269b"
}
```

`wall_min` = 110 s ÷ 60 = 1.83 min (driver wall from `date +%s` deltas).

---

## 6. Observations

### 6.1 Byte-stability across NFE for same (model, arm, seed)

The generator's `--nfe` flag is wired into `NFE_PER_RECORD` via global
reassignment but the emitted byte sequence is byte-stable across NFE=50,
100, 200 at temperature=1.0 (argmax). This matches Wave 158 / Wave 161 K6
/ Wave 167 P5 byte-stability finding.

Sample (kanzi baseline seed 42):

| NFE  | bytes | sha256[:8]                  |
|------|-------|------------------------------|
| 50   | 2439  | (identical across NFE)       |
| 100  | 2439  | (identical across NFE)       |
| 200  | 2439  | (identical across NFE)       |

This is the expected property: `--nfe` only affects the framework solver
budget, not the byte emission when argmax decoding.

### 6.2 Per-family distribution

Both `baseline_per_family_count` and `framework_per_family_count`
match the canonical Wave 174 manifest distribution:

```
{PF00005.27: 8, PF00072.24: 8, PF00183.19: 7, PF02517.18: 7}
```

Zero fallback (`framework_fallback_per_family_count = {}`) across all
18 invocations. Consistent with Wave 178 P6 finding (zero fallback at
NFE=50/100/200 for kanzi real mode).

---

## 7. Reproducibility

The driver script `/tmp/w179/run_all.sh` (bash, ~80 lines) contains
the exact loop used here. Re-running it will reproduce the same
36 cells (modulo timestamps). Manifest CSV at `/tmp/w179/manifest.csv`
serves as the machine-readable version of §4.

Per-invocation invocation log: `/tmp/w179/run.log` (cell-generator
stdout/stderr; all invocations exited 0).