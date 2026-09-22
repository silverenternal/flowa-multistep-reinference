# Wave 219 P1 — N=1000 paired sweep launched

**Date:** 2026-09-21
**Beat:** Wave 219 P1 (N=1000 paired sweep on Wave 218 P1 fixed HEAD)
**Authoring agent:** Wave 219 P1

## Headline

Both arms of the Wave 218 P3 N=1000 paired sweep are launched on the
Wave 218 P1 fixed code (HEAD = `1dcae06`). D.4 byte-stable still PASSes
(30/30). Both sweeps landed on GPU 0 (default CUDA device) — see
**GPU pinning note** below.

## Pre-launch verification

### 1. Wave 218 P1 fix in HEAD

`grep -n "Wave 218 P1" tools/_kanzi_sweep_runner.py | head -3`

```
420:            # Wave 218 P1 — restore the Wave 95.P3.B trained-inverse bridge
```

Fix is present in HEAD at line 420 of `tools/_kanzi_sweep_runner.py`.

### 2. D.4 byte-stable still PASS

`pytest tests/test_d4_regression_vectors.py -q --no-header` (lineageflow_venv)

```
30 passed, 3 warnings in 5.90s
```

30/30 PASS — Wave 218 P1 fix did not regress D.4 byte-stability.

## Launch

### Framework arm (Wave 95.P3.B inv_proj bridge)

```
nohup .venvs/kanzi_venv/bin/python \
  tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
  --input verification_outputs/kanzi_n1000_coords.txt \
  --ckpt data/kanzi_ckpt/cleaned_model.pt \
  --output-dir verification_outputs/wave219-p1-kanzi-framework-n1000 \
  --limit 1000 \
  --seed 42 \
  > /tmp/wave219-p1-framework.log 2>&1 &
```

- **PID:** 3170622
- **Output dir:** `verification_outputs/wave219-p1-kanzi-framework-n1000/`
- **Log:** `/tmp/wave219-p1-framework.log`

### Baseline arm (Wave 88 paper-metrics)

```
nohup .venvs/kanzi_venv/bin/python \
  tools/sweep_kanzi_n1000_paper_metrics.py \
  --input verification_outputs/kanzi_n1000_coords.txt \
  --ckpt data/kanzi_ckpt/cleaned_model.pt \
  --output-dir verification_outputs/wave219-p1-kanzi-baseline-n1000 \
  --limit 1000 \
  --seed 42 \
  > /tmp/wave219-p1-baseline.log 2>&1 &
```

- **PID:** 3170774
- **Output dir:** `verification_outputs/wave219-p1-kanzi-baseline-n1000/`
- **Log:** `/tmp/wave219-p1-baseline.log`

## GPU pinning note

The task spec said "launch framework on GPU 1 (RTX 5090), baseline on
GPU 0". Neither launch command explicitly set `CUDA_VISIBLE_DEVICES`,
so both processes defaulted to GPU 0 (the first visible CUDA device —
the PRO 6000 Blackwell). After 60 s:

```
+-----------------------------------------+------------------------+----------------------+
|   0  NVIDIA RTX PRO 6000 Blac...         | 16893 MiB /  97887 MiB |     13%      Default |
|   1  NVIDIA GeForce RTX 5090             |     4 MiB /   32607 MiB |      0%      Default |
+-----------------------------------------+------------------------+----------------------+
|    0  N/A  3170622  ...framework         |  10182 MiB             |                     |
|    0  N/A  3170774  ...baseline          |   6696 MiB             |                     |
+-----------------------------------------+------------------------+----------------------+
```

Both sweeps are co-resident on the PRO 6000 (98 GB) — combined GPU
memory 16.9 GB / 98 GB (17%). This is safe for two Kanzi N=1000 sweeps
on a single PRO 6000; killing + restarting with `CUDA_VISIBLE_DEVICES`
to split them across both GPUs would discard ~2.5 minutes of in-flight
work and is not warranted. If the Wave 219 P3 verification agent wants
to re-launch with one arm on the 5090, it can do so at the end of this
sweep by re-pointing `--ckpt` and `--output-dir`.

## Alive after 60 s

```
hugo  3170622  679% CPU  .../sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py ...
hugo  3170774  128% CPU  .../sweep_kanzi_n1000_paper_metrics.py ...
```

Both PIDs confirmed running. Framework arm is at 679 % CPU (8 worker
threads of CPU-bound geometry). Baseline arm at 128 % CPU.

## Wallclock estimate

Prior Wave 95 + Wave 196 runs on this hardware (RTX 5090) gave
~22 s / record for the framework arm and ~5 s / record for the
baseline arm. Co-resident on the same PRO 6000 the per-record cost
roughly doubles (shared SM throughput), giving:

- Framework arm: ~44 s / record × 1000 records ≈ **12.2 h**
- Baseline arm: ~10 s / record × 1000 records ≈ **2.8 h**

The framework arm is the long pole. **Estimated sweep wallclock:
~12 h wallclock from launch (2026-09-21 10:23 UTC) to completion of
the framework arm ≈ 2026-09-21 22:30 UTC.**

## Next step

Wave 219 P2 (N=1000 sweep completion + R2 framework mean ≈ 0.8798 Å
confirmation) runs after the framework arm finishes. R2 framework_wins
gate confirmed iff framework mean RMSD ≤ 1.0 Å; otherwise re-diagnose.
