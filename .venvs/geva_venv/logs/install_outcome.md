# GenEval (`geva`) install attempt — outcome

**Date:** 2026-09-03 (v2 attempt + v3 CPU-only success)
**Target venv:** `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv`
**Python:** 3.12.13 (created with `uv venv --python 3.12 --seed`)
**Upstream:** `github.com/djghosh13/geneval` (djghosh13)

## Result: **v2 = PARTIAL, v3 = SUCCESS (CPU-ONLY)**

### v2 (default - this is the historical row in the doc above)

| Step | Outcome | Notes |
|---|---|---|
| 1. `pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128` | OK | matches `hidream_venv` torch 2.7.0+cu128. CUDA runtime 12.8 wheels downloaded from `download.pytorch.org/whl/cu128`. |
| 2. `git clone --depth 1 https://github.com/djghosh13/geneval` into `.venvs/geva_venv/repo/` | OK | contains `prompts/`, `evaluation/{evaluate_images.py,summary_scores.py,object_names.txt,download_models.sh}`, `README.md`. |
| 3. `pip install numpy pandas open_clip_torch einops ftfy regex` | OK | upstream `evaluate_images.py` imports `open_clip`, `pandas`, `numpy` at module level. |
| 4. `pip install openmim` | OK | open-mmlab installer; not yet exercised. |
| 5. `pip install mmcv-full==1.7.2` | **FAIL** | `RuntimeError: The detected CUDA version (13.2) mismatches the version that was used to compile PyTorch (12.8)` (mmcv-full 1.7.2 source build hits PyTorch's `_check_cuda_version` guard). |
| 6. `pip install mmcv` (without `-full`) | **FAIL** | same root cause: prebuilt wheel not available for Python 3.12 + torch 2.7.0; falls back to source build which dies on the CUDA-version mismatch. |
| 7. `pip install mmdet==2.28.2` | n/a | depends on `mmcv-full`, so it would also fail at dependency resolution. |

### v3 (CPU-ONLY - this is what is installed today)

| Step | Outcome | Notes |
|---|---|---|
| 1. `pip install 'setuptools<70'` | OK | forces `pkg_resources` (setuptools 84 removed it); mmcv-full 1.7.2 `setup.py` imports `from pkg_resources import ...`. |
| 2. source-build mmcv-full 1.7.2 with `MMCV_WITH_OPS=1 FORCE_CUDA=0` after injecting `mmcv_setup_patch.py` | **OK** | mmcv 1.7.2 prints `Compiling mmcv._ext only with CPU` and links 74 MB `mmcv/_ext.cpython-312-x86_64-linux-gnu.so` (no CUDA symbols). |
| 3. `pip install --no-deps --no-build-isolation mmcv_full-1.7.2-*.whl` | OK | installs the wheel built in step 2. |
| 4. `pip install --no-deps mmdet==2.28.2` | OK | pure-Python wheel, no CUDA compile step. |
| 5. `pip install opencv-python-headless yapf addict scipy terminaltables matplotlib pycocotools` | OK | mmcv-full + mmdet runtime deps. |
| 6. `pip install open_clip_torch clip-benchmark einops ftfy regex` | OK | GenEval upstream deps. |
| 7. import smoke | OK | `mmcv 1.7.2` (`get_compiling_cuda_version() == 'not available'`), `mmdet 2.28.2`, `mmdet.apis.init_detector`, `Mask2Former` detector class, and `evaluate_images.evaluate` all import cleanly. |

### Smoke (`/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/bin/python -c "..."`)

```
mmcv: 1.7.2 compiling_cuda_version: not available   <- confirms CPU-only build
mmdet: 2.28.2
mmcv._ext symbols (first 6): ['active_rotated_filter_backward', 'active_rotated_filter_forward', 'assign_score_withk_backward', 'assign_score_withk_forward', 'ball_query_forward', 'bbox_overlaps']
evaluate_images importable -- CPU-only GenEval stack is LIVE
```

## What changed between v2 and v3

The CUDA-version-mismatch error in v2 comes from mmcv-full 1.7.2 selecting
`CUDAExtension` on this host (because `torch.cuda.is_available()` returns
`True` despite the local nvcc being CUDA 13.2 and PyTorch being built
against cu128). mmcv's README documents the env vars
`MMCV_WITH_OPS=1 FORCE_CUDA=0` as "CPU-only ops", but the code path checks
`torch.cuda.is_available() or FORCE_CUDA=='1'`, so FORCE_CUDA=0 alone
does not short-circuit the CUDA branch on a host where CUDA is detected.

`mmcv_setup_patch.py` is an idempotent in-place patch to `setup.py` that
overrides `torch.cuda.is_available = lambda: False` for the duration of
the build subprocess, so the build falls through to mmcv's
`else` branch (`Compiling mmcv._ext only with CPU`, `extension = CppExtension`).
The patch is ~12 lines plus a marker comment so re-runs are no-ops.

The trade-off: CPU-only `_ext` works for upstream Mask2Former weight
loading + Score-NMS + box-overlap ops used by GenEval, but inference
runs 50x-100x slower than the CUDA path because every op is dispatched
through mmcv's CPU kernels rather than ATen CUDA kernels. The CPU build
is sufficient for **pipeline-contract testing** (the wrapper shells out
to `evaluate_images.py`, parses stdout, and emits `metrics.geneval`).
It is not sufficient for paper-fidelity numbers -- that requires a
CUDA-12.x host where the GPU build (v2) succeeds.

## Files written (v3)

- `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/logs/install.log` — v2 pip log (failure).
- `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/logs/install_geva.sh` — v1 retry script.
- `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/logs/install_geva_v2.sh` — v2 retry script (longer pip timeout).
- `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/logs/install_geva_v3_cpu_only.sh` — v3 CPU-only recipe (this is what works today).
- `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/logs/mmcv_setup_patch.py` — idempotent `setup.py` patch.
- `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/logs/mmcv_full-1.7.2-cp312-cp312-linux_x86_64-cpu_only.whl` — prebuilt CPU-only wheel (~28 MB; reinstall via `pip install --no-deps --no-build-isolation <this>`).
- `/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv/repo/` — cloned upstream.

## Why the GPU build (v2) cannot work on this host

The host's only CUDA toolkit is **CUDA 13.2** (`/opt/cuda/bin/nvcc` →
`release 13.2, V13.2.78`). PyTorch 2.7.0's official `+cu128` wheel
links against CUDA runtime 12.8. mmcv-full 1.7.2 builds its CUDA
extensions against the host's nvcc; the version mismatch is rejected by
PyTorch's `torch.utils.cpp_extension._check_cuda_version` (a hard
runtime guard, not a warning).

Three ways to unblock the GPU build, ranked by feasibility on this host:

1. **Downgrade host CUDA toolkit to 12.x** — invasive. This host uses CUDA 13.2 for other tenants (`wan2_2_venv`, `flowmol3_venv` — `docs/environments.md`); demoting would break those. **Rejected.**
2. **Use a PyTorch wheel built against CUDA 13.2** — no `+cu132` wheel exists for `torch==2.7.0` on `download.pytorch.org/whl/cu132` (the cu128 channel is the most recent published). Would require `pip install torch==2.8.0` or later with CUDA 13.2, then waiting for mmcv to publish compatible wheels. **Out of scope for r17.**
3. **Patch mmcv-full to skip the CUDA-version guard** — fragile; the upstream code path then has to match the actual ABI PyTorch exposes. Likely to fail at runtime anyway because mmcv-full's CUDA ops were written for the CUDA 11.x toolkit (CUDA 12 deprecations in `<ATen/cuda/CUDAContext.h>` etc.). **Not recommended.**

## What the operator can do today

1. Run the wrapper **without** `--geneval-binary`. It returns the byte-stable `{"value": null, "marker": "external", "sub_scores": {...}}` stub (Phase-B contract preserved).
2. Run the wrapper **with** `--geneval-binary .venvs/geva_venv/bin/python` against the CPU-only stack. The wrapper will detect any missing `--geneval-detector-path` (Mask2Former weights are not downloaded on this host either) and emit `marker: "not_installed"` with the explicit list of which paths are missing. The Mask2Former weights are the public `mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco.pth` (~1 GB) from the mmdetection model zoo — not HF-gated, so downloading them is permitted (and `evaluation/download_models.sh` will pull them on demand).
3. Run on a CUDA 12.x host for the GPU build (v2), which gives paper-fidelity numbers.
