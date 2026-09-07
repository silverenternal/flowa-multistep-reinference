# Wave 69 Agent 4 — CUDA torch upgrade for lineageflow_venv

**Date:** 2026-09-07
**Wave:** 69 (Phase 4, Agent 4)
**Role:** Upgrade `.venvs/lineageflow_venv` from CPU-only `torch 2.5.1+cpu` to CUDA `torch 2.7.0+cu128` to unblock 8 pending LineageFlow NFE-scan cells.
**Scope:** `.venvs/lineageflow_venv` only. NO framework code, NO push, NO other venvs.

---

## 1. Before / after torch version

| State | torch version | CUDA available |
|---|---|---|
| **Before** | `2.5.1+cpu` | False |
| **After**  | `2.7.0+cu128` | True (2 devices) |

Target CUDA build: `torch==2.7.0+cu128` (matches `flowmol3_venv`, proven working).

## 2. CUDA verification

```text
$ .venvs/lineageflow_venv/bin/python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('devices:', torch.cuda.device_count())"
torch: 2.7.0+cu128
cuda: True
devices: 2
```

```text
$ .venvs/lineageflow_venv/bin/python -c "import torch; print('CUDA capability:', torch.cuda.get_device_capability(0)); print('Device name 0:', torch.cuda.get_device_name(0)); print('Device name 1:', torch.cuda.get_device_name(1))"
CUDA capability: (12, 0)
Device name 0: NVIDIA RTX PRO 6000 Blackwell Workstation Edition
Device name 1: NVIDIA GeForce RTX 5090
```

Both GPUs are visible:
- Device 0: RTX PRO 6000 Blackwell (compute capability 12.0, 97GB)
- Device 1: RTX 5090

## 3. End-to-end GPU tensor test

```text
$ .venvs/lineageflow_venv/bin/python -c "import torch; x = torch.zeros(3, 3).cuda(); print('GPU tensor OK:', x.device); y = x + 1; print('GPU add OK:', y.sum().item())"
GPU tensor OK: cuda:0
GPU add OK: 9.0
```

GPU tensor allocation + arithmetic + `.item()` round-trip all succeed.

## 4. LineageFlow adapter test result

```text
$ .venvs/lineageflow_venv/bin/python -m pytest tests/test_adapters/test_lineageflow.py -q --tb=line -x
.....................................................                    [100%]
=============================== warnings summary ===============================
adaptive_reflow/molecular/__init__.py:151
  /home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/molecular/__init__.py:151: DeprecationWarning: RMSPreservingCoordinateMixer is deprecated; use EqualRmsCoordinateMixer
    from .mixer import (
...
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
53 passed, 3 warnings in 14.19s
```

**53/53 tests pass.** The 3 warnings are pre-existing deprecation notices from the contracts/molecular modules, NOT introduced by this upgrade.

## 5. Package changes (diff)

```diff
14a15,28
> nvidia-cublas-cu12==12.8.3.14
> nvidia-cuda-cupti-cu12==12.8.57
> nvidia-cuda-nvrtc-cu12==12.8.61
> nvidia-cuda-runtime-cu12==12.8.57
> nvidia-cudnn-cu12==9.7.1.26
> nvidia-cufft-cu12==11.3.3.41
> nvidia-cufile-cu12==1.13.0.11
> nvidia-curand-cu12==10.3.9.55
> nvidia-cusolver-cu12==11.7.2.55
> nvidia-cusparse-cu12==12.5.7.53
> nvidia-cusparselt-cu12==0.6.3
> nvidia-nccl-cu12==2.26.2
> nvidia-nvjitlink-cu12==12.8.61
> nvidia-nvtx-cu12==12.8.55
28c42
< sympy==1.13.1
---
> sympy==1.14.0
30c44
< torch==2.5.1+cpu
---
> torch==2.7.0+cu128
32a47
> triton==3.3.0
```

| Change | Reason |
|---|---|
| torch 2.5.1+cpu → 2.7.0+cu128 | PRIMARY UPGRADE — GPU support |
| sympy 1.13.1 → 1.14.0 | Required by torch 2.7.0 (`sympy>=1.13.3` dep) |
| triton 3.3.0 NEW | Required by torch 2.7.0 (`triton==3.3.0` dep) |
| 14× nvidia-*-cu12 NEW | CUDA runtime libraries pulled in by torch+cu128 wheel |
| biopython, esm, transformers, huggingface_hub, safetensors, etc. | UNCHANGED — lineageflow-specific deps preserved |

No package conflicts. No downgrade. No non-lineageflow packages touched.

## 6. nvidia-cuda-runtime/cublas follow-up step

The task plan suggested running `.venvs/lineageflow_venv/bin/pip install nvidia-cuda-runtime-cu12==12.8.* nvidia-cublas-cu12==12.8.* 2>&1 | head -5` after the torch upgrade. This was **NOT NEEDED** — both libraries (and 12 other nvidia-*-cu12 libraries) were pulled in automatically by the `torch==2.7.0+cu128` wheel from the official PyTorch index. Verified: `nvidia-cuda-runtime-cu12==12.8.57` and `nvidia-cublas-cu12==12.8.3.14` are already installed.

## 7. Constraint compliance

| Constraint (LOCKED) | Status | Evidence |
|---|---|---|
| Minimum upgrade: torch → CUDA build | PASS | torch 2.5.1+cpu → 2.7.0+cu128 |
| DO NOT touch other packages | PASS | Only torch + sympy (forced) + 14× nvidia-cu12 (forced) + triton (forced) added — no removals of lineageflow deps |
| Verify CUDA visible AFTER upgrade | PASS | `cuda: True`, 2 devices visible |
| NO framework code change | PASS | Only `.venvs/lineageflow_venv` and this audit doc |
| NO push | PASS | Local commit only |

## 8. Impact on the 8 pending NFE-scan cells

`verification_outputs/lineageflow_real_force_mode_q4_2026.json` currently shows:
- 1/9 cells: `seed=42, nfe=10, status=TIE_AT_SATURATION` (executed on CPU)
- 8/9 cells: `status=PENDING, status_detail="cell skipped due to host-CPU bandwidth: each 657 M-param forward pass takes ~60 s on CPU; 9-cell × 4-solve-per-cell sweep would have exceeded the agent time budget"`

Now that `lineageflow_venv` has CUDA, the 657 M-param forward pass should run ~50-100× faster on GPU than the ~60 s on CPU — making the 9-cell sweep feasible. A future agent (Wave 69+ or Phase 4 closure) can re-run `tools/run_real_ckpt_eval.py --model lineageflow --force-mode real --nfe-budgets 10,50,200 --seeds 42,43,44` to fill in the 8 pending cells.

## 9. Files written

| Path | Purpose |
|---|---|
| `/tmp/lineageflow_venv_before.txt` | Pre-upgrade `pip freeze` snapshot (34 packages) |
| `/tmp/lineageflow_venv_after.txt` | Post-upgrade `pip freeze` snapshot (47 packages) |
| `docs/audit/wave69-phase4-cuda-upgrade.md` | This audit doc |