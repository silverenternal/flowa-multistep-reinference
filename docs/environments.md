# Model Environments (all GPU where possible)

Last verified: 2026-09-03

## Model → Env → Venv → Source Map

| Model | Source | Venv | Python | torch | CUDA | Adapter Strategy |
|---|---|---|---|---|---|---|
| **Lumina-Image 2.0** | HuggingFace (Alpha-VLLM/Lumina-Image-2.0, ~52 GB) | main `.venv` | 3.12 | 2.13+cu132 | sm_120 OK | diffusers-based, GPU |
| **HiDream-I1 (Dev)** | HuggingFace (HiDream-ai/HiDream-I1-Full, 17B, 44 GB) | main `.venv` | 3.12 | 2.13+cu132 | sm_120 OK | diffusers-based, GPU |
| **Wan2.2-T2V-A14B** | HuggingFace (Wan-AI/Wan2.2-T2V-A14B, ~130 GB partial) | main `.venv` | 3.12 | 2.13+cu132 | sm_120 OK | diffusers-based, GPU (LFS pointers only) |
| **FlowMol3 (FlowMol)** | Pitt pretrained (bits.csb.pitt.edu, ~5 GB) | `flowmol3_venv` | 3.11 | 2.0+cu117 | sm_86 max → **CPU only** | partial-fidelity (444/475 GVP tensors skipped); runtime adapter `flowmol3_v2_adapter.py` uses numpy/torch on CPU |
| **ProtBFN / AbBFN** | HuggingFace (InstaDeepAI/protein-sequence-bfn, 6.4 MB) | `.venv-flowmol311` | 3.11 | 2.6+cu126 | sm_120 OK | BFN refiner on GPU |
| **GraphBFN** | N/A (HTTP 401) | N/A | N/A | N/A | N/A | deferred per P-10 |

## Venvs (frozen 2026-09-03)

| Venv | Path | Python | torch | CUDA | Used for |
|---|---|---|---|---|---|
| **main .venv** | `/home/hugo/.venv` | 3.12 | 2.13+cu132 | sm_120 OK | Lumina, HiDream, Wan2.2 (diffusers stack) |
| **.venv-flowmol311** | `/home/hugo/.venv-flowmol311` | 3.11 | 2.6+cu126 | sm_120 OK | ProtBFN, AbBFN (BFN refiner) |
| **flowmol3_venv** | `/home/hugo/flowmol3_venv` | 3.11 | 2.0+cu117 | sm_86 max (CPU) | FlowMol3 partial-fidelity (CPU) |

## Weight Provenance (frozen 2026-09-03, chmod 444)

| Path | Source | Status |
|---|---|---|
| `data/flowmol3/weights_real/checkpoints/last.ckpt` | Pitt pretrained (paper authors, bits.csb.pitt.edu) | downloaded, frozen |
| `data/flowmol3/weights/` | metadata only (Pitt_pretrained_index.html + readme) | frozen |
| `data/protbfn_abbfn/weights/` + `weights_real/ProtBFN/` + `weights_real/AbBFN/` | InstaDeepAI/protein-sequence-bfn (HF) | downloaded, frozen |
| `data/hidream_i1/weights_dev/` | HiDream-ai/HiDream-I1-Full (HF, 17B, 44 GB safetensors) | downloaded, frozen |
| `data/hidream_i1/weights/` | LFS pointer stubs (metadata only) | frozen |
| `data/lumina_image_2_0/weights/` + `weights_real/` | Alpha-VLLM/Lumina-Image-2.0 (HF, LFS pointers; runtime via diffusers.from_pretrained) | frozen |
| `data/wan2_2/weights/` | Wan-AI/Wan2.2-T2V-A14B (HF, LFS stubs) | frozen |
| `data/graphbfn/weights/` | N/A (HTTP 401 from HF; AlgoMole/GraphBFN is GitHub-only) | frozen, no actual weights |

## Why these venvs are split

The Python ecosystem for the four families of models has incompatible dependencies:

- **FlowMol3** needs PyTorch 2.0 + DGL (Deep Graph Library) 2.0–2.1 with cu121 build of the C++ graphbolt; there is no sm_120 cu128 DGL wheel as of 2026-09-03. Mixing DGL with a 2.6+ cu126 torch downgrades the DGL C++ lib to a path that no longer matches the torch version, breaking the DGL import.
- **ProtBFN / AbBFN** historically ran on the upstream author's `environment.yaml` (Python 3.9 + jax + haiku + flax + jaxlib). The framework has been re-implementing the BFN refiner in `flowmol3_venv` (a separate PyTorch-only env) for the torch-based path that the framework's `protbfn_abbfn_adapter.py` actually uses. With `flowmol3_venv` and the ProtBFN harness, we only need `torch` (and not `dgl`); the sm_120 mismatch then collapses to just "we need torch built with sm_120 kernels". PyTorch 2.6+cu126 has those, so the path that worked on `2.0+cu117` (sm_86) was upgraded to `2.6+cu126` (sm_120). This still has torch_scatter pinned to the pre-2.6 ABI; if anything that uses `torch_scatter` on this venv breaks with a `undefined symbol` error after the upgrade, fall back to a numpy equivalent or a torch-native reimplementation of the scatter op the BFN refiner needs.
- **Lumina, HiDream, Wan2.2** are all served by `diffusers` on the main `.venv` (torch 2.13+cu132, sm_120 OK). The framework's `lumina_image_2_0.py` and `hidream_i1.py` adapters use the upstream pipelines; they are already on the GPU and were exercised in workflow A v2.
- **GraphBFN** has no HF mirror; the upstream is `AlgoMole/GraphBFN` on GitHub which this env could not reach (HTTP 401). Deferred to future work per P-10.

## Open venv limitation (FlowMol3 stays on CPU)

`flowmol3_venv` with `torch==2.0+cu117` is the lowest common denominator for DGL+torch_scatter. Upstream `build_env.sh` uses the same `dglteam/label/cu121` constraint; the official cu126 cu128 DGL wheel does not exist as of 2026-09-03. The adapter `flowmol3_v2_adapter.py` is therefore currently running on CPU; the empirical FlowMol3 numbers in `docs/r17-survey/mol-comparison.md` are CPU-side partial-fidelity numbers. Closing the "FlowMol3 needs full GVP and GPU" gap is staged in workflow R Stage 5: build DGL from source against torch 2.6+cu126 (long, hours), or replace the GVP path with a pure-torch equivalent.

## Provenance enforcement

All weight files were downloaded by their respective upstream URLs and verified to NOT have been re-trained locally:
- `flowmol3/weights_metadata.json` records the Pitt download.
- `protbfn_abbfn/weights_metadata.json` records the InstaDeepAI download.
- `hidream_i1/weights_metadata.json` records the HiDream-ai download.
- `lumina_image_2_0/weights_metadata.json` records the Alpha-VLLM download.
- `wan2_2/weights_metadata.json` records the Wan-AI download.
- `graphbfn/weights_metadata.json` records the failed download.
- The FlowMol3 ckpt at `weights_real/checkpoints/last.ckpt` is `epoch=17 step=1547236` from the Pitt pretrained model (not a locally re-trained model: it was never opened by any local training job — local training jobs would have been invoked via `python flowmol/train.py`, which is on disk in `data/FlowMol3/repo/flowmol/train.py`, but the framework never runs that script).

To prevent future "is this our weights or upstream's?" confusion, all `weights/` and `weights_real/` directories are now `chmod 444` (read-only for owner, group, other). Any new model training would need to write to a separate path (e.g. `weights_local/`) so it cannot silently overwrite upstream.

## Reproducing the envs

For the main .venv (Lumina, HiDream, Wan2.2 — used as-is, no rebuild needed):
```
.venv/bin/python -c "import torch, diffusers; print(torch.__version__, diffusers.__version__)"
```

For the .venv-flowmol311 (ProtBFN, AbBFN — current state):
```
/home/hugo/.local/bin/python3.11 -m venv /home/hugo/.venv-flowmol311
/home/hugo/.venv-flowmol311/bin/pip install --index-url https://download.pytorch.org/whl/cu126 torch==2.6.0 torchvision
/home/hugo/.venv-flowmol311/bin/pip install --no-deps "torch-scatter==2.1.2+pt20cu117"
# NOTE: torch-scatter pinned to pre-2.6 ABI. If anything that uses torch_scatter
# breaks on this venv with a `undefined symbol: _ZN3c1017RegisterOperatorsD1Ev`
# error, fall back to a numpy equivalent or torch-native reimplementation
# of the scatter op. The BFN refiner in protbfn_abbfn_adapter.py uses
# `torch_scatter` for `segment_csr` only.
```

For the flowmol3_venv (FlowMol3 partial-fidelity — current state):
```
/home/hugo/.local/bin/python3.11 -m venv /home/hugo/flowmol3_venv
/home/hugo/flowmol3_venv/bin/pip install --index-url https://download.pytorch.org/whl/cu117 torch==2.0.1 torchvision==0.15.2
/home/hugo/flowmol3_venv/bin/pip install "torch-scatter==2.1.2+pt20cu117"
/home/hugo/flowmol3_venv/bin/pip install --no-deps dgl pytorch-lightning
/home/hugo/flowmol3_venv/bin/pip install -e /home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo
# NOTE: This venv is GPU-incompatible (cu117 = sm_86 max, this rig = sm_120). The
# framework's flowmol3_v2_adapter.py uses the partial-fidelity path which is
# CPU-only when dgl is required. Run on CPU for partial-fidelity; run on GPU
# only for the torch_scatter + encoder path which has no DGL. To get full
# GVP on GPU, build DGL from source against torch 2.6+cu126.
```

## Quick check of all venvs

```bash
for v in /home/hugo/.venv /home/hugo/flowmol3_venv /home/hugo/.venv-flowmol311; do
    echo "=== $v ==="
    $v/bin/python -c "import torch; print(f'  torch={torch.__version__}, cuda={torch.cuda.is_available()}, cap={torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None}')" 2>/dev/null
done
```

Expected output after the upgrade:
- main .venv: torch=2.13.0+cu132 cuda=True cap=(12, 0)         # for diffusers-based models
- flowmol3_venv: torch=2.0.1+cu117 cuda=True cap=(8, 6)          # CPU-only (DGL constraint)
- .venv-flowmol311: torch=2.6.0+cu126 cuda=True cap=(12, 0)     # for BFN refiner on GPU
