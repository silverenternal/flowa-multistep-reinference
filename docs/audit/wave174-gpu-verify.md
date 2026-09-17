# Wave 174 P1: GPU Verification Audit

**Date**: 2026-09-17
**Branch**: main
**Goal**: Verify GPU is available and OmegaFold + ESM-IF actually use it (not CPU fallback).
**User context**: "上次特别慢是不是没用GPU" — verify whether GPU was actually used in prior eval runs.

---

## TL;DR

- **Hardware**: 2 GPUs detected (PRO 6000 Blackwell 98 GB + RTX 5090 32 GB). Driver 595.71.05, CUDA 13.2.
- **GPU usage by eval pipeline**: **NOT confirmed — the active `omegafold_venv` ships CPU-only `torch 1.13.1+cpu`**, so `_parse_gpus()` in `foldability_omegafold.py` returns `[]` (no CUDA), and both OmegaFold and ESM-IF run on CPU.
- **Live evidence (during a small N=5 fold run)**: GPU 0 utilization = 0%, GPU memory = 2 MiB while OmegaFold process used 2221% CPU and 6.8 GB RAM.
- **Root cause**: PyTorch was installed as the CPU-only wheel (`+cpu`) when `omegafold_venv` was built. The eval pipeline *requests* GPU via `--gpus all` + `CUDA_VISIBLE_DEVICES`, but the underlying torch has no CUDA — so it silently falls back to CPU.
- **Fix options** (out of scope here, see `fix_options.md` below): install `torch` with CUDA in `omegafold_venv`, or run the eval from a venv that already has CUDA torch (e.g., `lineageflow_venv` 2.7.0+cu128 or `micromamba/envs/pocket311` 2.11.0+cu128).

---

## Step 1 — GPU hardware

Command: `nvidia-smi | head -20`

```
| GPU  Name                          Memory-Usage |
|   0  NVIDIA RTX PRO 6000 Blackwell 2MiB/97887MiB |
|   1  NVIDIA GeForce RTX 5090       2MiB/32607MiB |
| Driver: 595.71.05, CUDA: 13.2 |
```

- **gpu_count**: 2
- **vram_per_gpu_gb**: ~98 (GPU 0) and ~32 (GPU 1) — heterogeneous. Pipeline should shard accordingly.

---

## Step 2 — OmegaFold venv torch (the one that matters)

Command:
```
source /home/hugo/.venvs/omegafold_venv/bin/activate
python -c "import torch; ..."
```

Output:

```
torch version: 1.13.1+cpu
torch cuda compiled: None
CUDA available: False
CUDA device count: 0
```

**`torch_cuda_available` = False** for the venv that runs `evaluate_all.py`.

The same venv has `omegafold` (from `/home/hugo/OmegaFold/omegafold/__init__.py`) and `esm 2.0.0`.

---

## Step 3 — ESM-IF check in omegafold_venv

```
import esm.inverse_folding
# ImportError: cannot import name 'filter_backbone' from 'biotite.structure'
# (the upstream fair-esm 2.0.0 install ships ESM2 only; ESM-IF / inverse_folding
# is gated by biotite compat — and the installed biotite lacks `filter_backbone`)
```

`self_consistency_esmif.py` has a `_patch_biotite_filter_backbone()` shim, so the
import *can* succeed at runtime once the patch is applied (it tries
`biotite.structure.filter` / `biotite.structure.filters` then a fallback numpy
mask). On this venv the shim does NOT rescue the import — there is no
`filter_backbone` at any of the candidate locations. **ESM-IF in this venv will
fail to import even with the shim**.

Direct check (shimmed): `esm.pretrained.esm_if1_gvp4_t16_142M_UR50` exists as a
callable, but invoking it triggers the biotite import chain above.

So even if we fixed the CUDA issue, ESM-IF would still error out on this venv
without a biotite downgrade / patch.

---

## Step 4 — Pipeline architecture

`data/lineageflow_upstream/evaluation/foldability_omegafold.py::_parse_gpus()`:

```python
def _parse_gpus(spec: str) -> List[int]:
    spec = spec.strip()
    if not spec or spec.lower() in {"cpu", "none"}:
        return []
    if spec.lower() == "all":
        cvd = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
        if cvd and cvd != "-1":
            ...
            return [int(p) for p in parts]
        try:
            import torch
            if not torch.cuda.is_available():
                return []                # <-- hits here
            return list(range(int(torch.cuda.device_count())))
        except Exception:
            return []
    ...
```

`self_consistency_esmif.py::_parse_gpus()` is identical. When `torch.cuda.is_available()` returns False, both stages fall into the "no GPU sharding" single-process path:

- `foldability_omegafold.py` runs OmegaFold as `subprocess.run(omegafold_cmd, env=env)` with `gpu=None` — so no `CUDA_VISIBLE_DEVICES` is set in the subprocess either.
- `self_consistency_esmif.py` similarly runs without `CUDA_VISIBLE_DEVICES` and with `device="cpu"`.

Even though the user (or the launch script) sets `CUDA_VISIBLE_DEVICES=0,1` in the wrapper shell, **`os.environ` in the parent process never sees `torch.cuda.is_available()==True`**, so the spec-resolution path takes the empty-list branch.

The sharding-by-length code path is exercised in `run_omegafold_sharded` only when `gpus` is non-empty. With `gpus = []`, it falls into the single-process `_run_one_omegafold(..., gpu=None, ...)` branch.

`evaluate_all.py` itself just spawns `sys.executable ... run_foldability.py` — it has no GPU handling of its own.

---

## Step 5 — Live evidence (N=5 sanity run)

Command:
```
source /home/hugo/.venvs/omegafold_venv/bin/activate
python data/lineageflow_upstream/evaluation/evaluate_all.py \
  --metrics foldability self_consistency \
  --max-seqs 5 \
  --fasta /tmp/w158/lineageflow_real_fastas/baseline.fasta \
  --outdir /tmp/w174/sanity/test/
```

After ~30 s of wall time (process tree shown via `ps aux`):

```
hugo  2445917 ... run_foldability.py ... --fold-gpus all --sc-gpus all ...
hugo  2445949 ... foldability_omegafold.py ... --gpus all ...
hugo  2445981 ... omegafold ... queries_20260917_162237.fasta ... pdb
                              CPU=2221%  MEM=6.7 GB
```

`nvidia-smi --query-gpu=index,memory.used,utilization.gpu` returned:

```
index, memory.used [MiB], utilization.gpu [%]
0, 2 MiB, 0 %
1, 2 MiB, 0 %
```

So while the eval was actively running, both GPUs sat idle at 0% utilization
with 2 MiB memory each. OmegaFold was chewing 22 CPU cores and 6.7 GB of RAM
on the protein — classic CPU-only path.

**`eval_pipeline_uses_gpu` = false** (under the current `omegafold_venv`).

The eval was killed (pkill) after ~30 s because on CPU 5 proteins would have
taken many minutes; the goal was to *observe* GPU usage, which we did.

---

## VRAM-per-GPU note

GPUs are heterogeneous: GPU 0 has 98 GB, GPU 1 has 32 GB. The
`_parse_gpus("all")` path does `[int(p) for p in cvd.split(",")]` from
`CUDA_VISIBLE_DEVICES`, which (when torch can see CUDA) preserves the
heterogeneous list — OmegaFold will shard by record count, not VRAM. For
LineageFlow's ~64–256 residue proteins the 5090 is plenty; the PRO 6000 is
overkill but unused capacity. No correctness issue, just inefficient utilization.

---

## Sanity pLDDT

`sanity_N_5_results_pLDDT`: **not collected** — the N=5 fold run was CPU-bound
and would not have produced a stable pLDDT within a reasonable budget
(killed at ~30 s before OmegaFold even finished its first forward pass on CPU;
estimated remaining time: tens of minutes per protein). The point of Step 5 was
to observe GPU telemetry, not to collect stats.

---

## Step 6 — Gates

```
pytest tests/ -k d4 -q --tb=line        → 33 passed, 31 skipped, 5020 deselected, 9 warnings
ruff check adaptive_reflow/ tests/ scripts/ tools/  → All checks passed!
python tools/check_claims_consistency.py  → No drift detected.
```

- `d4_pass` = True (33 passed)
- `ruff_count` = 0
- `claims_pass` = True

**No source code changed in this wave.** Audit-only.

---

## Root-cause summary

The "上次特别慢" (last time was very slow) feedback is **fully explained** by
this audit: the eval was running on CPU. Two issues, in order of severity:

1. **(blocking, explains the speed)** `omegafold_venv` has `torch 1.13.1+cpu`.
   `CUDA_VISIBLE_DEVICES=0,1` is set in the wrapper shell but
   `torch.cuda.is_available()` returns False inside the venv, so
   `_parse_gpus("all")` returns `[]` and the eval proceeds single-process on
   CPU. OmegaFold on CPU for even one ~120-residue protein takes several
   minutes; with 1000 records (Wave 158) the per-shard wall time was ~hours.
2. **(secondary, latent ESM-IF failure)** Even if CUDA were fixed,
   `fair-esm 2.0.0` + a Biotite that does not expose `filter_backbone` means
   the `_patch_biotite_filter_backbone()` shim does not rescue the
   `import esm.inverse_folding` chain. Self-consistency scoring would still
   fail unless the biotite version is fixed (e.g., pinned to a version that
   exports `filter_backbone`, or the shim is hardened to actually install the
   fallback).

### Fix options (for a follow-up wave, not this one)

| Option | Effort | Notes |
|---|---|---|
| A. Reinstall `torch` with CUDA in `omegafold_venv` | small | `pip install --upgrade torch==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128` |
| B. Move eval to `lineageflow_venv` (already has CUDA torch + ESM 2.0) | small | also need to verify OmegaFold is importable there (currently it is not — would need `pip install -e /home/hugo/OmegaFold`) |
| C. Move eval to `micromamba/envs/pocket311` | small | CUDA torch present; needs OmegaFold + esm.inverse_folding installs; biotite compat TBD |
| D. Hard-bake `--gpus ""` semantics + add a clear "GPU not available — running on CPU" warning to the pipeline | trivial | cosmetic; doesn't fix speed but makes the issue visible |

Recommend **A** for the fastest path: just upgrade torch in the existing venv
and verify `_parse_gpus("all")` returns `[0, 1]`. ESM-IF failure is independent
and should be tracked as a separate wave.

---

## Files referenced

- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/evaluate_all.py` (lines 167-168, 232-233, 300-336)
- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/run_foldability.py` (lines 130-220)
- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/foldability_omegafold.py` (lines 40-78, 180-310)
- `/home/hugo/codes/flowa-multistep-reinference/data/lineageflow_upstream/evaluation/self_consistency_esmif.py` (lines 42-60, 90-200, 252-280)
- `/home/hugo/OmegaFold/omegafold/__main__.py` (line 55: `model.to(args.device)`)
