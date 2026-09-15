# Wave 160 — K6 Foldability + Self-Consistency N=1000 Sweep

**Wave**: 160 (Agent 1 / P1)
**Date**: 2026-09-15 (Q3 2026)
**Branch**: main
**Status**: SWEEP COMPLETE (sanity PASS + N=1000 PASS for both arms); K6 UNBLOCKED

---

## 1. Goal

Produce on-disk N=1000 foldability + self-consistency results for both baseline
+ framework arms of LineageFlow — the final K6 unblock. The sweep had been
env-blocked for 80+ waves; Wave 159 P3 supplied the OmegaFold Python 3.10
sidecar venv at `/home/hugo/.conda/envs/omegafold_py310/`. FASTAs from Wave 158
P2 (real LineageFlowAdapter-solved) were already on disk at
`/tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta` (1000 records each).

## 2. Step 1 — OmegaFold venv verification

```
$ ls /home/hugo/.conda/envs/omegafold_py310/bin/omegafold
/home/hugo/.conda/envs/omegafold_py310/bin/omegafold   # exists
```

Sidecar Python: `/home/hugo/.conda/envs/omegafold_py310/bin/python` (3.10).
Sidecar torch: 2.14.0+cu130. OmegaFold CLI ready.

## 3. Step 2 — FASTA verification

```
$ ls -la /tmp/w158/lineageflow_real_fastas/baseline.fasta /tmp/w158/lineageflow_real_fastas/framework.fasta
-rw-r--r-- 1 hugo hugo 126939 Sep 15 16:25 baseline.fasta
-rw-r--r-- 1 hugo hugo 128313 Sep 15 16:25 framework.fasta
```

Both ~127 KB, 1000 records each (LineageFlowAdapter-solved, real path).

## 4. Step 3 — Upstream `evaluate_all.py` interface

CLI uses `--fasta` / `--outdir` (not `--input` / `--output`); metrics selected via
`--metrics foldability self_consistency` (space-separated, comma also accepted).
Implemented dispatch in `data/lineageflow_upstream/evaluation/evaluate_all.py`
calls `run_foldability.py` which in turn calls
`foldability_omegafold.py` then `self_consistency_esmif.py`.

## 5. Step 4 — Sanity N=5 sweep (PASS)

Two dependency gaps surfaced and were filled in the sidecar venv:

1. `fair-esm` + `biotite` missing for ESM-IF (inverse folding).
2. `torch_scatter` CUDA extension binary unavailable for torch 2.14 / cu130
   (PyG only ships wheels up to torch 2.9); the ESM-IF GVP module imports
   `scatter_add` from `torch_scatter` (called once at runtime). Since the
   upstream signature used by GVP is the simple "src + index + dim_size"
   pattern, we wrote a ~50-line stub package
   `/tmp/w160/torch_scatter_stub/torch_scatter/__init__.py` that implements
   `scatter_add` via native `torch.Tensor.scatter_add_` and aliases
   `scatter`/`scatter_sum`/`scatter_mean` to it. Stub tested and verified.

Sanity N=5 results (both arms run on GPU 0 in series):

| arm        | pLDDT mean | sc_perplexity mean |
|------------|-----------:|-------------------:|
| baseline   | 36.74      | 15.97              |
| framework  | 40.51      | 13.63              |

Both arms produced 5/5 foldability scores and 5/5 self-consistency scores
with 0 errors. PATH: `PYTHONPATH=/tmp/w160/torch_scatter_stub`.

## 6. Step 5 — N=1000 sweep launch (background)

Two independent runs, parallelized across the two GPUs:

```bash
# Baseline on GPU 0
PYTHONPATH=/tmp/w160/torch_scatter_stub nohup \
  /home/hugo/.conda/envs/omegafold_py310/bin/python \
  data/lineageflow_upstream/evaluation/evaluate_all.py \
  --metrics foldability self_consistency \
  --fasta /tmp/w158/lineageflow_real_fastas/baseline.fasta \
  --outdir /tmp/w160/foldability_n1000/baseline \
  --omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold \
  --fold-gpus 0 --sc-gpus 0 --no-plots \
  > /tmp/w160/foldability_n1000/baseline/sweep.log 2>&1 &
# → PID 407036

# Framework on GPU 1
PYTHONPATH=/tmp/w160/torch_scatter_stub nohup \
  /home/hugo/.conda/envs/omegafold_py310/bin/python \
  data/lineageflow_upstream/evaluation/evaluate_all.py \
  --metrics foldability self_consistency \
  --fasta /tmp/w158/lineageflow_real_fastas/framework.fasta \
  --outdir /tmp/w160/foldability_n1000/framework \
  --omegafold-bin /home/hugo/.conda/envs/omegafold_py310/bin/omegafold \
  --fold-gpus 1 --sc-gpus 1 --no-plots \
  > /tmp/w160/foldability_n1000/framework/sweep.log 2>&1 &
# → PID 407137
```

Both launched at **18:33** local. ETA per Wave 80 budget was ~25 h/arm; actual
wallclock was **~50 min/arm** because (a) RTX PRO 6000 Blackwell + RTX 5090
both ≥2× faster than the Wave 80 hardware envelope and (b) the sidecar venv
already had OmegaFold weights cached.

## 7. Step 6 — Monitoring (15 min + first hour)

```
=== Minute  5 ===  both PIDs alive; PDB shard dir empty (OmegaFold weights loading)
=== Minute 10 ===  both PIDs alive; OmegaFold shards running on GPUs (util 12-21%)
=== Minute 15 ===  baseline_pdbs=0  framework_pdbs=0  (shard dir; main pdb/ is per-shard)
   AFTER 15 min: baseline_alive=1  framework_alive=1  no errors

# Wallclock progress at the 60-min checkpoint (process exit):
[19:40:16] baseline_alive=0  framework_alive=0
[19:40:16] baseline_pdbs=1000  framework_pdbs=1000
```

Both runs wrote `[ok] wrote: /tmp/w160/foldability_n1000/{baseline,framework}`
and exited 0 cleanly at **19:25** (baseline) and **19:29** (framework). Total
wallclock: ~52 min baseline + ~56 min framework (parallel across GPUs ⇒
~56 min end-to-end, **30× faster than the Wave 80 budget**).

## 8. Step 7 — Final N=1000 results

### 8.1 Per-arm summaries (on-disk SHA256 verified)

| file | sha256 | bytes |
|------|--------|-------|
| baseline/summary.json | `7dc407880063760bd36806518dfbf9f81f7057729fd1ce0a69dafbf906bd0e3d` | 344 |
| baseline/foldability/summary.json | `5d483e3f4619dd9ebb26f3644e68b3e9522579ceed4240b447880a19ace23e20` | 247 |
| baseline/foldability/metrics_summary.json | `f50f3fc6fb353645e89e5cec7da86981fe08ba4ecd735f2f758e263aa6670a60` | 302 |
| baseline/foldability/foldability.jsonl | `164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261` | 265386 |
| baseline/foldability/self_consistency.jsonl | `fd21d98829eb5d5df9d87d3295637bd4a9c5524cff6663ed6f384d43db45ea92` | 185368 |
| baseline/foldability/metrics.jsonl | `684df8487b5afd15ce1bd0a9391e3805007955c21183430c3fc270318074cd4e` | 343550 |
| framework/summary.json | `0aa63c652c6a6ba1bcd5dddfd89c5183efbd76d00dae3557ff1db838a1350269` | 346 |
| framework/foldability/summary.json | `e96b1e2592a36d25a29658df9258fd408be454aa1ac2bd09f13e1d44f35c3aad` | 249 |
| framework/foldability/metrics_summary.json | `2b36d588485d40dd65add5af3b4f5775a0536df5a21a2033157f3afe31839e3e` | 304 |
| framework/foldability/foldability.jsonl | `b608edfb0f13a39bde5a06c3d16ccc94aa98f90db5434411cefe2f647574fc85` | 266738 |
| framework/foldability/self_consistency.jsonl | `bbd7ca13b46eb81a4d72fa5a7da25c095f0751b81eead315de5d2cdcb0a1d34b` | 186491 |
| framework/foldability/metrics.jsonl | `92c4399987efc8169859863f4095a6a5871dcb36e39a0011cc2204e038850162` | 345019 |

All JSONL files contain exactly **1000** records per arm (verified via `wc -l`).

### 8.2 Headline metric — foldability_pLDDT (higher is better)

| arm        | n   | pLDDT mean | pLDDT median | p10     | p90     |
|------------|----:|-----------:|-------------:|--------:|--------:|
| baseline   |1000 | 42.07      | 40.36        | 27.77   | 59.08   |
| framework  |1000 | **43.20**  | **41.30**    | 30.16   | 57.90   |

```
delta_pLDDT_pct = (43.1956 − 42.0725) / 42.0725 × 100 = +2.6748 %
```

Both arms scored 1000/1000 records (no skips, no errors).

### 8.3 Headline metric — ssc_scPerplexity (lower is better)

| arm        | n   | sc_perplexity mean | median  | p10     | p90     |
|------------|----:|-------------------:|--------:|--------:|--------:|
| baseline   |1000 | 17.88              | 17.57   | 13.77   | 22.18   |
| framework  |1000 | **13.96**          | **13.77**| 11.90  | 16.53   |

```
delta_sc_perplexity_pct = (13.9584 − 17.8751) / 17.8751 × 100 = −21.91 %
```

Both arms scored 1000/1000 records (0 errors; `n_errors=0`, `top_errors=[]`).

### 8.4 Headline metric — combined (corr pLDDT vs scPerplexity)

| arm        | corr_plddt_vs_sc | n_with_both |
|------------|-----------------:|------------:|
| baseline   | +0.171           | 1000        |
| framework  | **−0.132**       | 1000        |

The sign-flip from positive (baseline) to negative (framework) means the
framework arm produces sequences where better folding (higher pLDDT) actually
correlates with better inverse-folding perplexity (lower sc) — i.e. the two
quality axes **align** under the framework, whereas the baseline has them
weakly anti-aligned.

## 9. Step 8 — Verification artifact copies

All on-disk artifacts copied to `verification_outputs/`:

```
verification_outputs/k6_foldability_n1000_w160_q3_2026/
├── baseline/    (10 files: 4 summary jsons + 3 jsonl + queries.fasta + sweep.log + foldability.log + run_manifest.json)
└── framework/   (10 files, mirror)

verification_outputs/k6_foldability_sanity_w160_q3_2026/
├── baseline/    (foldability dir from N=5 sanity + sanity log)
└── framework/   (foldability dir from N=5 sanity + sanity log)
```

## 10. Step 9 — Gates verification (PRESERVED)

| gate | command | result |
|------|---------|--------|
| **ruff** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | `All checks passed!` |
| **claims** | `python tools/check_claims_consistency.py` | `No drift detected.` (39 active claims, 0 provisional) |
| **pytest -k d4** | `pytest tests/ -k "d4" -q` | `33 passed, 30 skipped, 5028 deselected` (D4 spec-literal regression suite) |

Full `pytest tests/` returns **4876 passed + 214 skipped + 1 failed**.
The single failure (`tests/test_tools/test_check_docs_against_code.py::
test_no_false_positives_on_current_repo`) is a **PRE-EXISTING** doc-consistency
check failure (9 inline-symbol references in `README.md` / `CONSOLIDATED_RESULTS.md`
/ `baseline-audit-report.md` / `paper-draft.md` — `Path`, `Invalid`, `TypeAlias`).
Not introduced by Wave 160 (additive only); same failure observed on Wave 159.

## 11. K6 status — RESOLVED

Wave 160 produced the first-ever on-disk N=1000 foldability + ssc results
for LineageFlow. K6 ("N=1000 foldability + self-consistency on baseline and
framework") is now **RESOLVED**. Headline outcomes:

| metric                | baseline | framework | delta | direction |
|-----------------------|---------:|----------:|------:|-----------|
| foldability_pLDDT ↑   | 42.07    | 43.20     | +2.67% | framework wins |
| ssc_scPerplexity ↓    | 17.88    | 13.96     | −21.91% | framework wins |
| corr(pLDDT, sc)       | +0.171   | −0.132    | sign-flip | framework aligns axes |

## 12. Wave 160 P1 outputs

- `docs/audit/wave160-k6-sweep-launch.md` (this doc)
- `verification_outputs/k6_foldability_n1000_w160_q3_2026/{baseline,framework}/`
- `verification_outputs/k6_foldability_sanity_w160_q3_2026/{baseline,framework}/`

P2/P3 will pick up these results for paper sections, claims registry updates,
and headline evidence consolidation. P1 is additive only; no source files in
`adaptive_reflow/` / `tests/` were modified.

## 13. Honesty disclosures

- **stub disclosure**: The Wave 160 sweep used a small native-torch stub for
  `torch_scatter` because the upstream PyG wheels do not yet cover
  torch 2.14 / CUDA 13.0. The stub implements only the small subset of
  `torch_scatter` actually called by the ESM-IF GVP module (1 `scatter_add`
  call site, signature `scatter_add(src, index, dim_size)`). Equivalent in
  behavior to the upstream PyG implementation for that signature; verified
  with a 4-element unit test against the canonical PyG reference output.
- **first-record inference time**: First PDB of each arm takes ~5-10 min
  (OmegaFold weight load + compile) then amortizes to <2 s/record. With
  ESM-IF + GVP on top, end-to-end per-record wallclock is ~3-4 s on RTX 5090
  and ~2 s on RTX PRO 6000 Blackwell.
- **ESM-IF model weights**: Downloaded once into the sidecar venv
  (`/home/hugo/.cache/torch/hub/checkpoints/esm_if1_*`) at first sanity run;
  reused for the full N=1000 sweep.
