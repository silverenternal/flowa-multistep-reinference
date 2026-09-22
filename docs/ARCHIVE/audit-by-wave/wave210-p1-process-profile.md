# Wave 210 P1 — Current Process Profile

**Captured**: 2026-09-21 01:52 UTC
**Host**: `47.110.35.232` (single-node)
**Read-only audit**: no source code modified
**Verdict**: CPU hot-path is the Wave 206 P5 FreqFlow N=1000 synthetic sweep; not GPU-acceleratable in its current form.

---

## 1. Host capability

| Field | Value |
|---|---|
| CPU model | Intel(R) Core(TM) i9-14900K |
| Sockets | 1 |
| Cores / socket | 24 |
| Threads / core | 2 |
| Logical CPUs (`lscpu` `CPU(s)`) | 32 |
| CPU max MHz | 4500 |
| NUMA nodes | 1 (CPU 0–31) |
| Load average (1/5/15) | 36.99 / 33.02 / 23.38 |
| Total RAM (free) | n/a this report (not measured) |

Load >32 = oversubscribed; the 24-core/32-thread host has at minimum **~5 processes ahead in the run queue** waiting for a CPU. The FreqFlow sweep alone consumes ~28 of 32 logical CPUs.

GPU 0 = RTX PRO 6000 (98 GB), currently **100 % SM, 8 GB used** by OmegaFold shards.
GPU 1 = RTX 5090 (32 GB), currently **60 % SM, 1.6 GB used** by a one-off NFE scan.

---

## 2. Top CPU consumers (5 %+ only)

| PID | PPID | %CPU | %MEM | Threads | Elapsed | Command (truncated) |
|---:|---:|---:|---:|---:|---:|---|
| 3119617 | 1 | 2810 | 0.2 | 63 | 10:05 | `python3 scripts/wave206_p5_freqflow_n1000_audit.py --ckpt-probe` |
| 3123378 | 3123376 | 569 | 1.5 | 59 | 00:08 | `.venvs/flowmol3_venv/bin/python -c …RectifiedFlowCIFARAdapter NFE scan…` |
| 3120336 | 3120303 | 116 | 5.0 | 59 | 08:43 | `omegafold … shard_01/queries.fasta` |
| 3120335 | 3120303 | 114 | 5.0 | 59 | 08:43 | `omegafold … shard_00/queries.fasta` |
| 3069843 | 3069622 | 99.6 | 0.0 | 1 | 13:56:53 | `nvtop` (monitoring) |

Below 5 % CPU: the OmegaFold driver (PID 3120303), the foldability harness (PID 3120271), the Wave 206 P1 top-level launcher (PID 3106950), Claude Code (PID 1578207), sshd, containerd, dockerd, v2ray, and a pile of `btrfs-endio` kworkers.

---

## 3. Deep dive — the dominant hot path (PID 3119617)

### 3.1 What it is

`scripts/wave206_p5_freqflow_n1000_audit.py --ckpt-probe` is running the **Wave 206 P5 FreqFlow N=1000 paired-record 12-col audit** in **synthetic mode** (FreqFlow's `nnet_ema.pth` ckpt remains **NOT publicly released** as of 2026-09-21; re-probed this run; verdict `VERDICT: ckpt ABSENT — synthetic mode mandatory`).

### 3.2 Hot functions (from `adaptive_reflow/adapters/freqflow.py:376` and `tools/run_real_ckpt_eval.py`)

```python
def _synthetic_velocity_field(x, t, *, weights, freq_mix=...):
    flat  = np.asarray(x, dtype=np.float64).reshape(-1)            # (4096,)
    h     = np.tanh(flat @ w1_s + b1_s + float(t) * t_bias)        # (4096,256) @ (256,) + bias
    v_spatial = (h @ w2_s + b2_s).reshape(FREQ_FLOW_STATE_SHAPE)   # (256,4096) @ (4096,) + bias
    mag = _fft_magnitude(x).reshape(-1)                            # np.fft.fft2 + abs + norm
    v_freq    = (mag @ w_freq + b_freq).reshape(...)
    return ((1.0 - mix) * v_spatial + mix * v_freq).astype(np.float64)
```

Per seed (loop at `scripts/wave206_p5_freqflow_n1000_audit.py:240`):
- `_solve_baseline(adapter, nfe=50, seed=s)` — 50 NFE steps, each calls `_synthetic_velocity_field` once → 50 × 2 matmuls (4096×256 and 256×4096) + 1 FFT
- `_solve_framework(adapter, nfe=50, seed=s, n_rounds=3)` — 3 rounds of 50 NFE each → 150 × 2 matmuls + 3 FFTs
- `_paired_metrics`, `_endpoint_latent` — small NumPy ops

Total per seed: **200 matmuls of size 4096×256 + 200 matmuls of 256×4096 + 4 FFTs** + a paired L2/cosine/MAB reduction. With 1000 seeds and the seed-loop fully serialised inside the script, that is **400 000 matmuls** in float64.

### 3.3 Why 63 threads and 2810 % CPU?

The script does not configure `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS`, so NumPy/OpenBLAS defaults to 32 threads (matching logical CPUs). The NumPy matmul `@` operator dispatches through OpenBLAS's OpenMP layer, so each seed's matmuls run across all logical CPUs in parallel. The 63-thread count is OpenMP master (1) + 32 OpenMP workers + a Python interpreter per worker + a couple of I/O threads for the JSON flush.

Observed wall-clock from `/tmp/w206-p5-full.log` (just before this profile):

```
[ 100/1000] seed=99   mode=synthetic l2=76.6157 cos=0.2973 wall_base=0.4563s wall_fw=0.4573s elapsed=166.9s
[ 200/1000] seed=199  mode=synthetic l2=76.6555 cos=0.3029 wall_base=0.4544s wall_fw=0.4533s elapsed=315.3s
[ 300/1000] seed=299  mode=synthetic l2=75.8994 cos=0.3109 wall_base=0.5795s wall_fw=0.5910s elapsed=461.5s
```

≈1.48 s/seed observed → estimated finish at seed 1000 ≈ **~24 min total**. The script started 01:42, ETA ≈ 02:06. This is the only consumer hot enough to dominate load average.

### 3.4 Can it use GPU? — **No, not in its current form.**

- The script is in **synthetic mode by disclosure** — FreqFlow's upstream ckpt is absent, so the adapter deliberately bypasses any torch model. The whole point is to exercise the **Protocol surface** (adapter / integrator / re-inference scheduling) against a deterministic NumPy field, not to test the real FM model. The script header states: *"This script therefore runs in synthetic mode only … the deterministic NumPy two-branch shim that backs the Protocol surface."*
- The hot loops are NumPy, not PyTorch. Moving them to a GPU tensor would require rewriting the whole adapter surface (and would defeat the byte-determinism guarantee that the audit relies on).
- The workload is already highly parallel on CPU (OpenMP across 32 logical CPUs ≈ linear speedup until memory bandwidth becomes the bottleneck). GPU offload would require shipping 4096×256 weights (×8 bytes in float64 = 8 MiB) and one matrix-vector product per step — well below the GPU's break-even cost, so launch overhead dominates.

**Realistic acceleration paths (CPU, no GPU):**
- Halve the matmul cost by dropping to **float32** (`np.float32` instead of `np.float64` in `_synthetic_velocity_field`) — `flat @ w1_s` becomes 2× faster and memory-bandwidth-bound work halves. **Risk**: changes the per-record L2 / cosine values, so the 12-col audit must be regenerated; the `freqflow_mode` field and `verdict_overall` already disclose synthetic, so this is a one-line edit + re-run.
- **Reduce N**: 1000 seeds → 500 (paired-t df 499 vs 999, still plenty for Bonferroni α=0.025).
- **Lower `--nfe`** (default 50) for this R-level cell. Wave 206 P4 already verified R-level N=1000 sf fix at NFE=50 with a fixed seed; this re-sweep's marginal information is small once the per-record scalar distribution is stable.

None of these require touching real model code.

---

## 4. Other hot PIDs

### 4.1 PID 3123378 — RectifiedFlowCIFAR NFE scan (569 % CPU, GPU 1)

Ad-hoc `-c` one-liner pasted into a shell:

```python
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter
for nfe in [10, 20, 50, 100, 200, 500]:
    adapter = RectifiedFlowCIFARAdapter(num_steps=nfe, device='cuda')
    samples = adapter.batched_inference(n_samples=200, num_steps=nfe, seed=0)  # twice (warmup + timed)
    ...
    print(f'NFE={nfe}: ...')
```

6 configs × 200 samples = 1200 inferences + 6 adapter constructions. PyTorch CUDA uses 1 GPU SM stream + CPU dataloader workers → 569 % CPU during eager-mode init and CUDA upload. Currently **GPU 1, 1.6 GB**, 60 % SM.

This is a benchmarking probe, not a long-running job. It will exit on its own.

### 4.2 PIDs 3120335 / 3120336 — OmegaFold shards (114 % + 116 % CPU, GPU 0)

Wave 206 P1 lineageflow N=1000 foldability sweep, split across 2 shards:
- `shard_00`: PID 3120335, 59 threads, 114 % CPU, GPU 0 SM 50 %, 3.98 GiB
- `shard_01`: PID 3120336, 59 threads, 116 % CPU, GPU 0 SM 36 %, 4.04 GiB
- Driver: PID 3120303 (`foldability_omegafold.py --workers-per-gpu 2`), idle-waiter

OmegaFold inference is **single-stream GPU-bound** (SM 36–50 % on a 100+ SM RTX PRO 6000). The 114–116 % CPU is the PyTorch intra-op CPU thread + the OmegaFold preprocessing (sequence parsing, MSA search, secondary-structure prep). 5 GB RAM each is the small MSA / structure cache.

This is already on GPU 0 by design and is correctly using it.

### 4.3 PID 3069843 — nvtop (99.6 %, 1 thread, no GPU)

Monitoring TUI. Pinned to a single core by the kernel scheduler. No user action needed; if load gets critical, kill this — Claude Code will re-spawn it when needed.

---

## 5. GPU state (nvidia-smi at profile time)

| GPU | Model | Util | Mem used | Process |
|---|---|---:|---:|---|
| 0 | RTX PRO 6000 | 100 % | 8037 MiB | omegafold shard_00, shard_01 |
| 1 | RTX 5090 | 60 % | 1660 MiB | one-off NFE scan (3123378) |

GPU 0 is fully booked by OmegaFold (Wave 206 P1). GPU 1 has headroom (60 % util, 1.6 / 32 GB) but is **already taken by the NFE scan one-liner**; once that finishes (~minutes), GPU 1 is free.

**Conflict check for an extra GPU job**: do NOT start a new job on **GPU 0** — would steal SM time from the OmegaFold shards and corrupt the Wave 206 P1 foldability sweep. GPU 1 is safe after PID 3123378 exits.

---

## 6. CPU vs GPU recommendation

The user's question was: "where is the CPU hot path, can it use GPU, can it default to GPU?"

1. **CPU hot path**: PID 3119617, `wave206_p5_freqflow_n1000_audit.py`, ~28 of 32 logical CPUs. Hot functions are NumPy matmul + FFT in `_synthetic_velocity_field`.
2. **GPU for it?**: No, not without violating the script's stated synthetic-mode guarantee and breaking byte-determinism. The protocol-surface audit is intentionally NumPy.
3. **Default-to-GPU acceleration of the audit as a whole**: not applicable — the R-level cell is CPU-bound by design. If the user wants the audit to *finish* (instead of being killed) the practical levers are:
   - reduce N to 500, **or**
   - drop the field to `np.float32` (≈2× speedup, ~1× change in audit scalars, must regenerate the 12-col CSV), **or**
   - lower `--nfe` from 50 → 25 (~2× speedup; reduces the **R-level** per-record L2 precision).
4. **GPU 1 is free** after the NFE scan exits. Any new GPU work should land there, not on GPU 0.

---

## 7. Artefacts

- CSV: `verification_outputs/wave210-p1-process-profile.csv` (12 rows: top-10 PIDs + 2 helpers)
- This doc: `docs/audit/wave210-p1-process-profile.md`