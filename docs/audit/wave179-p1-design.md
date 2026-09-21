# Wave 179 P1 — multi-seed generation + eval dispatch verification (3 seeds × 36 cells)

**Date:** 2026-09-17
**Branch:** main
**Scope:** Wave 179 P1 — verify the multi-seed generation + eval protocol
works end-to-end on 1 seed (42) before scaling to 3 seeds
({42, 43, 44}). Dispatch table for the 36-cell sweep: 2 models ×
3 NFE × 2 arms × 3 seeds × N=30 records = 1080 total records.

---

## 1. Goal & matrix

Re-run the Wave 174 P3 + Wave 178 P6 ladder at multiple seeds to
separate small-N noise from real framework-vs-baseline gap. The Wave
178 P6 N=10 sweep showed framework pLDDT worse than baseline at
NFE=100 (52.83 vs 57.07, Δ = −4.24) — plausibly noise. Three seeds
× N=30 records per cell gives 90 records per arm/NFE bucket and
90 × 2 = 180 per (model, NFE) bucket, sufficient for tight CIs.

### 1.1 Cell matrix (per seed)

| Model       | arm       | NFE  | n  | outdir                                    |
|-------------|-----------|------|----|-------------------------------------------|
| lineageflow | baseline  | 50   | 30 | `/tmp/w179/cells/lineageflow_nfe_50/`      |
| lineageflow | baseline  | 100  | 30 | `/tmp/w179/cells/lineageflow_nfe_100/`     |
| lineageflow | baseline  | 200  | 30 | `/tmp/w179/cells/lineageflow_nfe_200/`     |
| lineageflow | framework | 50   | 30 | `/tmp/w179/cells/lineageflow_nfe_50/`      |
| lineageflow | framework | 100  | 30 | `/tmp/w179/cells/lineageflow_nfe_100/`     |
| lineageflow | framework | 200  | 30 | `/tmp/w179/cells/lineageflow_nfe_200/`     |
| kanzi       | baseline  | 50   | 30 | `/tmp/w179/cells/kanzi_nfe_50/`            |
| kanzi       | baseline  | 100  | 30 | `/tmp/w179/cells/kanzi_nfe_100/`           |
| kanzi       | baseline  | 200  | 30 | `/tmp/w179/cells/kanzi_nfe_200/`           |
| kanzi       | framework | 50   | 30 | `/tmp/w179/cells/kanzi_nfe_50/`            |
| kanzi       | framework | 100  | 30 | `/tmp/w179/cells/kanzi_nfe_100/`           |
| kanzi       | framework | 200  | 30 | `/tmp/w179/cells/kanzi_nfe_200/`           |

**Per seed:** 12 cells, 360 records. **3 seeds total:** 36 cells,
1080 records.

Each FASTA contains both `baseline.fasta` and `framework.fasta`
(mirroring the Wave 174 P3 + Wave 178 P6 single-invocation pattern —
one generator call per NFE produces both arms).

### 1.2 Eval matrix (per seed)

| Model       | arm       | NFE  | eval outdir                                       |
|-------------|-----------|------|---------------------------------------------------|
| lineageflow | baseline  | 50   | `/tmp/w179/eval/baseline/lineageflow/nfe_50/`     |
| lineageflow | baseline  | 100  | `/tmp/w179/eval/baseline/lineageflow/nfe_100/`    |
| lineageflow | baseline  | 200  | `/tmp/w179/eval/baseline/lineageflow/nfe_200/`    |
| lineageflow | framework | 50   | `/tmp/w179/eval/framework/lineageflow/nfe_50/`    |
| lineageflow | framework | 100  | `/tmp/w179/eval/framework/lineageflow/nfe_100/`   |
| lineageflow | framework | 200  | `/tmp/w179/eval/framework/lineageflow/nfe_200/`   |
| kanzi       | baseline  | 50   | `/tmp/w179/eval/baseline/kanzi/nfe_50/`           |
| kanzi       | baseline  | 100  | `/tmp/w179/eval/baseline/kanzi/nfe_100/`          |
| kanzi       | baseline  | 200  | `/tmp/w179/eval/baseline/kanzi/nfe_200/`          |
| kanzi       | framework | 50   | `/tmp/w179/eval/framework/kanzi/nfe_50/`          |
| kanzi       | framework | 100  | `/tmp/w179/eval/framework/kanzi/nfe_100/`         |
| kanzi       | framework | 200  | `/tmp/w179/eval/framework/kanzi/nfe_200/`         |

Per-cell eval runs foldability + self_consistency on GPUs 0+1
(Wave 178 P6 runner pattern). Total eval cells across 3 seeds:
36, plus 1080 scPerplexity records and 1080 pLDDT records
(2 metrics × 1080 records each).

---

## 2. Generator dispatch (verified, mirrors Wave 174 P3 + Wave 178 P6)

Per Wave 174 P3 §2, the two generators are **sibling scripts** —
each is locked to one model:

| Model       | Script                                  |
|-------------|-----------------------------------------|
| lineageflow | `tools/gen_lineageflow_n1000_fastas.py` |
| kanzi       | `tools/w172b_gen_kanzi_fastas.py`       |

DO NOT invoke the lineageflow script for kanzi cells (silently
emits LineageFlow content under a kanzi filename; caught by
Wave 174 P3 SHA-256 cross-model verification).

### 2.1 LineageFlow FASTA generation CLI

Per NFE, per seed:

```bash
.venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w179/cells/lineageflow_nfe_${NFE}  \
  --n 30 --seed ${SEED} --nfe ${NFE} --n-rounds 3
```

Defaults `--min-len`, `--max-len`, `--temperature` (1.0 = argmax,
byte-stable) preserved. `--n-rounds 3` matches Wave 81/86/158
manifest bytes. Emits both `baseline.fasta` + `framework.fasta`
+ `manifest.json` in `--outdir`.

Per seed: 3 invocations (NFE=50/100/200). Per 3 seeds:
9 invocations.

### 2.2 Kanzi FASTA generation CLI

Per NFE, per seed:

```bash
.venvs/kanzi_venv/bin/python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w179/cells/kanzi_nfe_${NFE}  \
  --n 30 --seed ${SEED} --nfe ${NFE} --n-rounds 3
```

Wave 178 P2-P4 path: real-mode ckpt when available, trajectory
in `(L, 3)` coord space, no per-step CPU bridge. Default
`--min-len`, `--max-len` preserved. Per-family count consistent
across arms (`{PF00005.27:x, PF00072.24:x, PF00183.19:y,
PF02517.18:y}` summing to 30; baseline-arm distribution is
RNG-driven by seed). Emits both `baseline.fasta` +
`framework.fasta` + `manifest.json`.

Per seed: 3 invocations. Per 3 seeds: 9 invocations.

### 2.3 Total generation invocations

18 invocations (9 lineageflow + 9 kanzi), each producing one
FASTA per arm. Output: 36 FASTAs (12 cells × 1 fasta per arm ×
2 arms? — actually 12 cells per seed × 2 arms × 3 seeds = 72
FASTAs, but each `--outdir` carries one baseline + one framework
file = 36 dirs × 2 FASTAs each = 72 FASTAs total).

---

## 3. GPU eval pipeline (Wave 178 P6 run_eval.sh pattern)

Per arm, per model, per NFE, per seed, the eval runs foldability
(self-consistency uses the same fasta; folds are precomputed
once). One eval call per cell — i.e. 12 eval calls per seed ×
3 seeds = 36 eval cells.

```bash
PY=/home/hugo/.conda/envs/omegafold_py310/bin/python
OMEGAFOLD=/home/hugo/.conda/envs/omegafold_py310/bin/omegafold
PATH=/home/hugo/.conda/envs/omegafold_py310/bin:$PATH
export PATH
export LD_LIBRARY_PATH=/home/hugo/.conda/envs/omegafold_py310/lib:${LD_LIBRARY_PATH:-}
cd <repo_root>

# Per (model, arm, nfe, seed) cell:
$PY data/lineageflow_upstream/evaluation/evaluate_all.py \
  --metrics foldability self_consistency \
  --max-seqs 30 \
  --fold-gpus 0,1 --sc-gpus 0,1 \
  --no-plots \
  --omegafold-bin "$OMEGAFOLD" \
  --fasta /tmp/w179/cells/${MODEL}_nfe_${NFE}/${ARM}.fasta \
  --outdir /tmp/w179/eval/${ARM}/${MODEL}/nfe_${NFE}/
```

Differences from Wave 178 P6 runner:
- `--max-seqs 30` (was 10) — match N=30 generation
- `--fasta` + `--outdir` updated to `/tmp/w179/...` paths
- `--sc-gpus 0,1` retained (ESM-IF shard across both GPUs)

Per-cell wall budget (extrapolated from Wave 178 P6):
- Wave 178 P6 (N=10): ~37 s/cell mean → ~110 s/cell for N=30
  (linear in N for both foldability and self-consistency).
- 36 cells × 110 s ≈ **66 min total eval** (1.1 hour). Comfortably
  fits in a single Wave 179 budget.

The runner script `/tmp/w179/run_eval.sh` mirrors
`/tmp/w178/run_eval.sh` line-for-line; the sweep script
`/tmp/w179/run_all.sh` mirrors `/tmp/w174/run_all.sh`.

---

## 4. venv / conda dispatch

| Model       | Interpreter                                        | PyTorch / runtime       |
|-------------|----------------------------------------------------|-------------------------|
| lineageflow | `.venvs/lineageflow_venv/bin/python` (uv-managed)  | transformers + ESM-2 + LineageFlow upstream |
| kanzi       | `.venvs/kanzi_venv/bin/python` (uv-managed)        | torch 2.14.0+cu130 + kanzi upstream pkg |
| eval        | `/home/hugo/.conda/envs/omegafold_py310/bin/python` | real OmegaFold + ESM-IF, GPU 0+1 |

Verified symlinks all resolve:
- `.venvs/lineageflow_venv/bin/python` → `python3.12`
- `.venvs/kanzi_venv/bin/python` → `/home/hugo/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12`
- `/home/hugo/.conda/envs/omegafold_py310/bin/python` → `python3.10`

DO NOT mix venvs — the lineageflow script imports
`transformers` + ESM-2 (lineageflow_venv only); the kanzi
script imports `kanzi` upstream (kanzi_venv only); the eval
script imports OmegaFold + ESM-IF (omegafold_py310 only).

---

## 5. Output directory state (pre-sweep)

```
/tmp/w179/                  — empty (created at P1 commit time)
/tmp/w179/cells/            — to be created at first generation run
/tmp/w179/eval/             — to be created at first eval run
/tmp/w178/cells/, /tmp/w178/eval/ — Wave 178 P6 artifacts (untouched)
```

Verified clean — `/tmp/w179/` does not exist prior to this commit;
the Wave 178 P6 artifacts under `/tmp/w178/` are read-only inputs
for any cross-wave comparison but not modified by Wave 179.

---

## 6. Sweep runner pattern

The 36-cell sweep is sequential within each (seed × model × nfe × arm)
tuple but parallelizable across (model, arm, nfe) within a seed
(GPU 0+1 shared). Recommended order:

1. **Seed 42 only first** (P2 of Wave 179). 12 cells × ~110 s =
   ~22 min eval + ~3 min generation = ~25 min wall. Confirms
   protocol works end-to-end on 1 seed before scaling to 3.
2. **Seed 43 + 44** (P3 of Wave 179). Two more ~25-min runs.
   Total 3-seed budget: ~75 min wall.

If the P2 1-seed run surfaces a protocol issue (e.g. N=30 OOM on
foldability GPU 1 due to longer mean sequence length, or eval
timeout), the 3-seed budget is forfeit — fix the issue first,
re-run P2, then re-launch P3.

---

## 7. Cross-model SHA-256 verification (mirrors Wave 174 P3 §3)

After seed-42 generation, the Wave 174 P3 byte-distinct check
extends naturally:

| Comparison                                          | Expected result      |
|-----------------------------------------------------|----------------------|
| lineageflow_nfe_50/baseline vs kanzi_nfe_50/baseline | DIFFERENT            |
| lineageflow_nfe_100/baseline vs kanzi_nfe_100/baseline | DIFFERENT          |
| lineageflow_nfe_200/baseline vs kanzi_nfe_200/baseline | DIFFERENT          |

Baseline byte-stability (per model) within a seed is **not**
preserved across NFE (different `--seed` invocations differ on
framework-arm bytes by NFE, baseline bytes by seed — but for a
given seed, lineageflow baseline is byte-stable across NFE
because `--nfe` only feeds the framework arm; kanzi baseline is
byte-stable across NFE in synthetic mode). The
`{lineageflow,kanzi}_nfe_{50,100,200}/baseline.fasta` SHA
within a seed should match the Wave 174 P3 reference table at
seed=42 (modulo any --seed default changes).

---

## 8. Gates & dependencies

- D.4: **PASS at HEAD** (`468bc25`); Wave 178 P7 confirmed no D.4
  regressions.
- Ruff on `tools/` + `docs/audit/`: **expected PASS** at P2 commit
  time (only `wave179-p1-design.md` added).
- Claims consistency: **expected PASS** — no claim text modified.
- GPU availability: GPU 0 (RTX PRO 6000 Black, 98 GB) + GPU 1
  (RTX 5090, 32 GB) confirmed at Wave 178 P6.

---

## 9. Decision

**Dispatch verified.** All CLIs, venvs, output paths, and the
eval pipeline are confirmed against the Wave 174 P3 lineageflow
generator + Wave 178 P6 kanzi generator + Wave 178 P6 eval
runner. 1-seed dry-run budget is ~25 min wall; full 3-seed
budget is ~75 min wall. Wave 179 P2 (1-seed dry-run) is
**GO**.