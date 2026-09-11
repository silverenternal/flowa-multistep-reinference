# Environments (1 project venv + 4 model venvs)

Last verified: 2026-09-03 (post-r17 cleanup).

The repository uses a **two-tier venv layout**: one `flowa-multistep-reinference`
project venv for framework dev/test/docs, and four model-specific venvs
that each mirror the corresponding upstream repo's `requirements.txt` /
`environment.yml`. Long-term the framework itself is targeted for a
PyO3 → Rust rewrite (see `ROADMAP.md` later), so the project venv is kept
minimal and torch-free; heavy model runtimes live in the per-model venvs
and are pinned per-driver.

## Paper grounding (where correctness lives)

The framework's correctness proofs (which this two-tier layout exists to
keep reproducible) cite the underlying JMAA paper (Li 2026). In
particular:

* **Theorem 1** (BL-convergence of `mu_{g,eps}` to `nu_g`, `paper section 3.1`)
  is the per-algorithm convergence target the framework's
  `adaptive_reflow/theory/rate_bound.py` materialises as an explicit
  constant `rate_bound_C(eps)`. This lives in the stdlib-only project
  venv and is part of the F.5 env_hash coverage.
* **Lemma 2**, **Lemma 4**, **Lemma 5** (sheet evidence `A_g`,
  physical-complement suppression, root-cell packing) ground the
  per-round scheduler choices (`adaptive_reflow/algorithm/scheduler.py`).
* **Proposition 3** (selection-mechanism display, `paper section 4.2`)
  grounds the per-round restart distribution.

None of these require torch / numpy / scipy at the source level (the
theory package is stdlib-only by design — see
`tests/test_universal/test_no_molecular_import.py`), which is why the
project venv can stay torch-free while still hosting the paper-anchored
correctness proofs.

## Layout (frozen 2026-09-03)

| Tier | Name | Path | Python | torch | CUDA build | sm_120 |
|---|---|---|---|---|---|---|
| project | **`.venv`** | `<repo>/.venv` | 3.12.13 | (none — stdlib-only framework) | — | n/a |
| model | **`.venvs/flowmol3_venv`** | `<repo>/.venvs/flowmol3_venv` | 3.12.13 | 2.2.0+cu121 | cu121 | ❌ (sm_90 max; venv does NOT support sm_120) |
| model | **`.venvs/hidream_venv`** | `<repo>/.venvs/hidream_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | ✅ |
| model | **`.venvs/lumina_venv`** | `<repo>/.venvs/lumina_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | ✅ |
| model | **`.venvs/wan2_2_venv`** | `<repo>/.venvs/wan2_2_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | ✅ |
| model | **`.venvs/protbfn_venv`** | `<repo>/.venvs/protbfn_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | ✅ |

Driver / hardware:
- Driver **595.71.05**, CUDA Version 13.2 (driver-level cap).
- GPU 0: NVIDIA RTX PRO 6000 Blackwell, **sm_120**, 98 GB.
- GPU 1: NVIDIA GeForce RTX 5090, **sm_120**, 32 GB.
- `.venvs/{hidream,lumina,wan2_2,protbfn}_venv` report
  `torch.cuda.get_device_capability(0) == (12, 0)` and have
  `arch_list` containing `sm_120, compute_120` (cu128 torch 2.7.0+).
- **`.venvs/flowmol3_venv` is the exception**: installed torch is
  `2.2.0+cu121` with `arch_list` capped at `sm_50 sm_60 sm_70 sm_75
  sm_80 sm_86 sm_90` (no sm_120). `torch.cuda.is_available()` returns
  True (driver-level), and `get_device_capability(0)` reports `(12, 0)`
  for the sm_120 GPU, **but** any kernel-launched op on the sm_120
  devices will fail with `RuntimeError: no kernel image is available`
  unless the kernel was JIT-compiled for sm_120. Closing this gap
  requires a `uv pip install --upgrade torch==2.7.0+cu128 ...` rerun.
- Venv torch-build policy: every model venv installs **GPU torch**
  (`+cuX` wheels); **no `+cpu` torch** is permitted anywhere in the
  tree. (Note: flowmol3_venv's binary still binds to cu121 even though
  the driver is at cu13x; binary use is unaffected because cu121 is
  forward-compatible with cu13x-only driver forward.)

## Model → Venv → Source Map

| Model | Source | Venv | Strategy |
|---|---|---|---|
| **Lumina-Image 2.0** | HuggingFace `Alpha-VLLM/Lumina-Image-2.0` (~52 GB LFS) | `.venvs/lumina_venv` | diffusers + fairscale + torchdiffeq |
| **HiDream-I1 (Dev)** | HuggingFace `HiDream-ai/HiDream-I1-Full` (17 B, 44 GB safetensors) | `.venvs/hidream_venv` | diffusers; flash-attn optional |
| **Wan2.2-T2V-A14B** | HuggingFace `Wan-AI/Wan2.2-T2V-A14B` (~130 GB LFS stubs) | `.venvs/wan2_2_venv` | diffusers; transformers ≤4.51.3; numpy<2 |
| **FlowMol3 (FlowMol)** | Pitt pretrained (bits.csb.pitt.edu, ~5 GB) | `.venvs/flowmol3_venv` | pytorch-lightning 2.1.3 + rdkit + wandb; **adapter is self-contained** (numpy/torch on GPU; no FlowMol3 upstream import) |
| **ProtBFN / AbBFN** | HuggingFace `InstaDeepAI/protein-sequence-bfn` (6.4 MB) | `.venvs/protbfn_venv` | transformers + biopython; BFN refiner is framework-internal |
| **GraphBFN** | N/A (HTTP 401 from HF; AlgoMole/GraphBFN GitHub-only) | — | deferred per P-10 |

## Venv Activation Matrix (frozen 2026-09-11, Wave 102)

Eleven sidecar venvs plus the project venv (12 total). Each row
identifies which venv a given workflow MUST be launched from; cross-
venv launches break because the upstream deps (torch, mmcv-full,
biotite, transformers, jax) are not installed in the project venv.

Activation pattern: source the bin/activate (or call the venv's
`bin/python` directly to avoid shell state pollution). Each row also
lists a representative `tools/<X>.py` invocation so the reader does
not have to grep.

| Venv | Owner model | Purpose | Activate with | Example tool to invoke |
|---|---|---|---|---|
| `.venv` | project | framework dev/test/docs (stdlib-only by design — `tests/test_universal/test_no_molecular_import.py` guards `universal/` ⊄ molecules) | `source .venv/bin/activate` | `pytest tests/`, `mkdocs build --strict`, `python -m adaptive_reflow` |
| `.venvs/flowmol3_venv` | FlowMol3 (Pitt pretrained, partial-fidelity GVP) | molecule FM eval + paper-metric PB-xtb + posebusters | `source .venvs/flowmol3_venv/bin/activate` | `.venvs/flowmol3_venv/bin/python tools/run_mol_eval.py` · `tools/paper_metrics.py` · `tools/flowmol3_xtb_bridge.py` |
| `.venvs/kanzi_venv` | Kanzi (ICLR 2026 protein flow-AE) | protein FM real-ckpt forward + N=1000 sweeps + GPT-prior restart | `source .venvs/kanzi_venv/bin/activate` | `.venvs/kanzi_venv/bin/python tools/run_kanzi_real_ckpt.py` · `tools/run_kanzi_gpt_prior.py` · `tools/sweep_kanzi_n1000_*.py` |
| `.venvs/lineageflow_venv` | LineageFlow (ICML 2026 protein) | protein FM real-ckpt forward + N=1000 upstream eval + foldability | `source .venvs/lineageflow_venv/bin/activate` | `.venvs/lineageflow_venv/bin/python tools/run_lineageflow_real_ckpt.py` · `tools/run_lineageflow_n1000_foldability_omegafold.py` · `tools/upstream_eval.py` (LineageFlow branch) |
| `.venvs/hidream_venv` | HiDream-I1 (17B Dev, HF safetensors) | image FM diffusion — SOTA-2 / framework-arm experiments | `source .venvs/hidream_venv/bin/activate` | `.venvs/hidream_venv/bin/python tools/run_sota_hidream_i1_experiment.py` |
| `.venvs/lumina_venv` | Lumina-Image 2.0 (HF LFS, ~52 GB) | image FM diffusion — SOTA-2 / framework-arm experiments | `source .venvs/lumina_venv/bin/activate` | `.venvs/lumina_venv/bin/python tools/run_sota_lumina_image_2_0_experiment.py` |
| `.venvs/wan2_2_venv` | Wan2.2-T2V-A14B (HF LFS, ~130 GB) | video FM diffusion — SOTA-2 / framework-arm experiments | `source .venvs/wan2_2_venv/bin/activate` | `.venvs/wan2_2_venv/bin/python tools/run_sota_wan2_2_video_experiment.py` |
| `.venvs/protbfn_venv` | ProtBFN / AbBFN (InstaDeep JAX shim + framework torch reimpl) | protein BFN — JAX upstream-shim route + torch adapter path | `source .venvs/protbfn_venv/bin/activate` | `.venvs/protbfn_venv/bin/python tools/run_sota_protbfn_abbfn_adapter_experiment.py` · `tools/upstream_eval.py` (ProtBFN branch) |
| `.venvs/geva_venv` | GEVA / djghosh13/geneval (mmcv-full + mmdet + Mask2Former Swin-S) | Tier-2 image-eval: GenEval harness (CPU-only inference path, slow but correct) | `source .venvs/geva_venv/bin/activate` | `python tools/run_image_eval.py --geneval-binary .venvs/geva_venv/bin/python …` |
| `.venvs/hpsv2_venv` | HPSv2 (human preference score v2) | Tier-2 image-eval: HPSv2 scorer on `(image, prompt)` pairs | `source .venvs/hpsv2_venv/bin/activate` | `python tools/run_image_eval.py --hpsv2-binary .venvs/hpsv2_venv/bin/python …` |
| `.venvs/image_reward_venv` | ImageReward (BLIP + MedBLIP reward model) | Tier-2 image-eval: BLIP-anchored reward score | `source .venvs/image_reward_venv/bin/activate` | `python tools/run_image_eval.py --image-reward-binary .venvs/image_reward_venv/bin/python …` |
| `.venvs/dpg_venv` | DPG / MiniCPM-V judge model | dp-not-diffusion judge model (NOT YET PROVISIONED — see `docs/r17-survey/dpg-bench-judge-decision.md`) | (none — install deferred) | reserved for `tools/run_dpg_bench_metric()` once Q1 in `dpg-bench-judge-decision.md` is resolved |

Notes on the matrix:

- The five **GPU model venvs** (flowmol3, hidream, lumina, wan2_2,
  protbfn) ship with `torch` and run on the sm_120 GPUs; flowmol3 is
  pinned to cu121 torch 2.2.0 (see top-of-page table + "Open venv
  limitations" section).
- The two **protein paper-metric venvs** (kanzi, lineageflow) ship
  with `biotite + esm + torchdiffeq`; lineageflow additionally has
  `fair-esm` and OmegaFold in `repo/`; kanzi has `jaxtyping + loguru
  + timm + fastpdb` and an xTB bridge for energy evaluation.
- The three **Tier-2 image-eval venvs** (geva, hpsv2, image_reward)
  are invoked as subprocesses from the project venv via
  `tools/run_image_eval.py`; the `DEFAULT_*_VENV_PYTHON` constants
  in that file pin the interpreter path. Each venv is CPU-only
  inference at present (geva is mmcv-full 1.7.2 CPU path; hpsv2 and
  image_reward are CPU by design).
- The `.venvs/dpg_venv` row is reserved but currently unprovisioned;
  install attempts were paused pending the judge-model decision in
  `docs/r17-survey/dpg-bench-judge-decision.md`. See that doc for
  the exact `uv venv --python 3.12 .venvs/dpg_venv --seed` recipe
  once Q1 is resolved.

If a tool is not listed above, grep its header docstring for
`.venvs/<name>_venv/bin/python` to confirm which interpreter to use;
each per-venv tool explicitly names its required venv at the top of
its file (e.g., `tools/run_kanzi_real_ckpt.py` line 1 says
"runs inside the `.venvs/kanzi_venv` sidecar (created in this wave)").

## Why each model has its own venv

The five families of upstream SOTA models have incompatible dependency
graphs that cannot be merged into one venv:

- **FlowMol3 / HiDream / Lumina / Wan2.2 / ProtBFN** — each upstream
  pins different `torch` versions, transformers upper bounds, flash-attn
  builds, and numpy ranges. The framework's adapters do not import the
  upstream model code (they implement the channel vocabulary and
  protocol surface in `adaptive_reflow/adapters/` directly), so per-model
  venvs are sized only to the model's own deps.

- **transformers** upper-bounds conflict (`<=4.51.3` for Wan2.2 vs no
  cap for HiDream/Lumina/ProtBFN). Wan2.2 gets the pin; the others
  ride the latest.

- **numpy** range conflicts (`<2` for Wan2.2, `<2.5` for the framework's
  `flow_matching` extra, no pin for HiDream/Lumina/ProtBFN).

- **flash-attn** — Wan2.2 `pyproject.toml` declares `flash_attn` as a
  required dep at install time, but PyPI has no cu128 manylinux wheel
  for it (verified 2026-09-03) and source build needs the CUDA toolkit.
  The framework's adapter for Wan2.2 uses diffusers and does not require
  flash-attn at import time, so we install with `--no-deps` for the
  upstream repo and skip flash-attn (re-enable when source-build
  tooling lands).

## Project venv (`.venv`) — what it carries and what it doesn't

The project venv is the framework's own. It is **not** meant to host
SOTA model runtimes. Contents (post-r17 cleanup):

- **Editable install** of the framework itself:
  `uv pip install -e ".[test,dev,flow_matching]"`
  (test = pytest + hypothesis + pytest-benchmark;
  dev = mkdocs + mkdocstrings + griffe;
  flow_matching = numpy<2.5 + scipy).
- **No torch, no diffusers, no transformers, no accelerate, no bitsandbytes,
  no nvidia-*, no cuda-*.**
- The framework's `universal/`, `contracts/`, `frame/`, `algorithm/`,
  `policy/`, `schedule/`, `writer/`, `eval/`, `diagnostics/`,
  `envelope/` are stdlib-only by design; the AST-level test guard
  `tests/test_universal/test_no_molecular_import.py` enforces
  `universal/` ⊄ molecules.
- Total size: ~780 MB (mkdocs + griffe + dev tooling dominate).
- Adapter modules in `adaptive_reflow/adapters/` that need torch /
  diffusers are imported only inside their per-model venv at runtime.

## Per-model venv recipes (reproducible with `uv`)

All five model venvs were created with the same recipe:

```bash
# 1. Create the venv at the matching Python (uv 0.11.8):
uv venv --python 3.12 .venvs/<name>_venv     # or 3.10/3.11 if upstream pins

# 2. Install torch from the PyTorch cu128 (sm_120) index first:
uv pip install --python .venvs/<name>_venv \
  --index-url https://download.pytorch.org/whl/cu128 \
  torch==2.7.0 torchvision==0.22.0          # or torchaudio where needed

# 3. Pin numpy/scipy to match the framework's <2.5 cap (or the upstream
#    pin, e.g. Wan2.2's <2):
uv pip install --python .venvs/<name>_venv \
  "numpy<2.5" "scipy>=1.10"                  # Wan2.2 uses "numpy>=1.23.5,<2"

# 4. Install the per-model deps from the upstream requirements.txt /
#    environment.yml (see table below).

# 5. Verify (must print cuda=True cap=(12,0) on this rig):
.venvs/<name>_venv/bin/python -c \
  "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability(0))"
```

Per-model dep lists:

- **`flowmol3_venv`** (translates `data/FlowMol3/repo/environment.yml`,
  pre-r17 legacy torch pin: `torch==2.2.0+cu121`):
  ```
  pytorch-lightning==2.1.3 rdkit pystow einops wandb
  useful-rdkit-utils py3Dmol torch-ema biopython
  networkx<3.3 setuptools<81
  ```
  DGL is **not** installed (the conda-only `dglteam/label/cu121`
  wheel tops out at sm_86 max and is incompatible with the install
  of torch 2.2.0+cu121 on this rig). `torch_scatter` is installed
  but is the **CPU-only** build (`torch_scatter-2.1.2`,
  `v221_pt22cpu` suffix in `site-packages/`; only `_scatter_cpu.so`,
  `_segment_coo_cpu.so`, `_segment_csr_cpu.so` are present — no
  `_scatter_cuda.so`). The framework's `flowmol3_v2_adapter.py`
  implements the partial-fidelity path in numpy/torch and does not
  need DGL or torch_scatter at runtime; if/when full-fidelity
  GVP-on-GPU is required, the venv needs to be rebuilt on the
  cu128 torch 2.7.0 baseline with a GPU torch_scatter wheel, then
  DGL rebuilt from source against torch 2.7+cu128.

- **`hidream_venv`** (from `data/HiDream-I1/repo/requirements.txt`):
  ```
  diffusers>=0.32.1 transformers>=4.47.1 accelerate>=1.2.1 einops>=0.7.0
  ```
  `flash-attn` is recommended by HiDream but skipped for now (no cu128
  prebuilt wheel + no source-build tooling). The framework's
  `hidream_i1.py` adapter uses diffusers directly.

- **`lumina_venv`** (from `data/lumina_image_2_0/repo/requirements.txt`):
  ```
  diffusers fairscale accelerate tensorboard transformers
  torchdiffeq gradio click sentencepiece
  ```

- **`wan2_2_venv`** (from `data/wan2_2/repo/pyproject.toml [project.dependencies]`,
  minus `flash_attn`):
  ```
  diffusers>=0.31.0 "transformers>=4.49.0,<=4.51.3" "tokenizers>=0.20.3"
  accelerate>=1.1.1 opencv-python>=4.9.0.80 easydict ftfy
  "imageio[ffmpeg]" imageio-ffmpeg "numpy>=1.23.5,<2" tqdm
  ```

- **`protbfn_venv`** (project-internal BFN refiner; upstream uses jax but
  the framework's torch reimplementation doesn't):
  ```
  transformers einops biopython
  # JAX stack (for upstream-shim routing only — the framework's torch
  # adapter is the canonical path):
  dm-haiku==0.0.17 flax==0.12.9 jax==0.11.1 jaxlib==0.11.1 optax==0.2.8
  ```
  `torch_scatter` is **not** installed — PyG's prebuilt index
  (`data.pyg.org/whl/torch-2.7.0+cu128.html`) is DNS-blocked from this
  rig and PyPI has no source-built wheel for cu128. The BFN refiner's
  `segment_csr` op is implemented as a torch-native scatter
  (`torch.zeros(...).index_add_(0, idx, src)`) in
  `adaptive_reflow/adapters/protbfn_abbfn_model.py` — see `Loss
  Definitions` in that file. The JAX/Haiku/Flax/Optax stack above is
  installed only so the upstream shim
  (`adaptive_reflow/adapters/protbfn_abbfn_upstream_shim.py`,
  `force_mode="upstream_jax"`) can import
  `data/protbfn_abbfn/repo/{model,sample,inpaint,loss}.py`; the
  framework's JAX-free pytree loader
  (`protbfn_abbfn_jax_loader.py`) does the actual weight materialisation
  and does not need JAX. See **ProtBFN / JAX pin decision** below for
  the pin rationale; the resolved set is recorded in
  `requirements/protbfn.lock`.

  **External binaries staged in `bin/`:**
  - `mmseqs` — MMseqs2 8cc5ce367b5638c4306c2d7cfc652dd099a4643f
    (release 18-8cc5c, 2025-07-27), Linux x86_64 AVX2 static build,
    downloaded from
    `https://github.com/soedinglab/MMseqs2/releases/download/18-8cc5c/mmseqs-linux-avx2.tar.gz`.
    SHA-256 of tarball: `bd9b0234da5949ad528d5b5f9ea4cda9c1e23dce14b46c0791d4d919a76e61ce`.
    Statically linked (`ldd` reports "not a dynamic executable"), no
    glibc / MPI / libgomp system dependencies. Required by downstream
    `protbfn_eval_venv` for the cluster-hit / coverage / CATH-S40
    structural metrics; staged here so the venv is self-contained.
    License: GPLv3 (open-source, no license gate).

## Quick check of all venvs

```bash
for v in .venv .venvs/*/; do
    echo "=== $v ==="
    $v/bin/python -c "import torch; print(f'  torch={torch.__version__}, cuda={torch.cuda.is_available()}, cap={torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None}')" 2>/dev/null \
      || $v/bin/python -c "import sys; print(f'  py={sys.version_info.major}.{sys.version_info.minor}, framework (no torch)')"
done
```

Expected output (2026-09-03):

```
- .venv/                : framework (no torch)
- .venvs/flowmol3_venv/ : torch=2.2.0+cu121, cuda=True, cap=(12, 0), arch_list max=sm_90 (no sm_120 support)
- .venvs/hidream_venv/  : torch=2.7.0+cu128, cuda=True, cap=(12, 0)
- .venvs/lumina_venv/   : torch=2.7.0+cu128, cuda=True, cap=(12, 0)
- .venvs/wan2_2_venv/   : torch=2.7.0+cu128, cuda=True, cap=(12, 0)
- .venvs/protbfn_venv/  : torch=2.7.0+cu128, cuda=True, cap=(12, 0)
```

Note on the `flowmol3_venv` line: `cuda=True` and `cap=(12, 0)` come
from the driver / device query and are **not** a statement that GPU
ops will execute on sm_120 hardware. The installed torch 2.2.0+cu121
binary has `arch_list` = `['sm_50','sm_60','sm_70','sm_75','sm_80',
'sm_86','sm_90']`; running an op that needs JIT compilation against
the sm_120 GPUs will raise
`RuntimeError: no kernel image is available for execution on the
device`. Imports succeed and CPU ops work; GPU ops fall back through
PyTorch's existing JIT path or fail with the above error.

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

The FlowMol3 ckpt at `weights_real/checkpoints/last.ckpt` is
`epoch=17 step=1547236` from the Pitt pretrained model (not a locally
re-trained model: it was never opened by any local training job —
local training jobs would have been invoked via
`python flowmol/train.py`, which is on disk in
`data/FlowMol3/repo/flowmol/train.py`, but the framework never runs that
script).

To prevent future "is this our weights or upstream's?" confusion, all
`weights/` and `weights_real/` directories are `chmod 444` (read-only for
owner, group, other). Any new model training would need to write to a
separate path (e.g. `weights_local/`) so it cannot silently overwrite
upstream.

## Open venv limitations

- **FlowMol3 / DGL + torch**: the `.venvs/flowmol3_venv` predates the
  cu128 upgrade (still on torch 2.2.0+cu121 with `arch_list` capped
  at sm_90 — see top-of-page table) and additionally has no GPU DGL
  wheel available. The framework's FlowMol3 path is
  partial-fidelity (444/475 GVP tensors) implemented in numpy/torch
  on CPU/GPU (JIT-compiled sm_120 ops via PyTorch's runtime). To
  bring flowmol3_venv back in line with the other four model venvs
  (torch 2.7.0+cu128 with sm_120 in `arch_list`), rerun:

  ```bash
  /home/hugo/codes/flowa-multistep-reinference/.venvs/flowmol3_venv/bin/python -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu128 torch==2.7.0
  ```

  then re-verify `torch.cuda.get_arch_list()` includes
  `sm_120, compute_120`. Closing the GVP-on-GPU gap (full DGL +
  GPU torch_scatter) additionally requires building DGL and a GPU
  torch_scatter wheel against torch 2.7+cu128.

- **Wan2.2 / flash-attn**: PyPI has no cu128 manylinux wheel for
  `flash-attn`. The framework's Wan2.2 adapter uses diffusers and runs
  fine without flash-attn. Re-enable when a prebuilt cu128 wheel ships
  or when source-build tooling lands.

- **ProtBFN / torch_scatter**: PyG's wheel index is DNS-blocked and
  PyPI has no source wheel for cu128. The BFN refiner uses a
  torch-native scatter instead; the pre-2.6 ABI fallback in the
  previous docs is no longer needed.

## Driver ↔ venv coupling

| Driver | CUDA Version | Compatible torch cuX | venv torch build |
|---|---|---|---|
| 595.71.05 (this rig) | 13.2 | cu128 / cu132 | cu128 (chosen for cross-model uniformity) |

If the driver is downgraded below 525.xx (CUDA 12.0 cut-off), torch
will need to drop to cu118 or cu121 and the `arch_list` will lose
sm_120 support. If a future driver adds sm_130 / sm_140 GPU support,
torch must be upgraded to a cuX build whose `arch_list` includes the
new compute capability.

## ProtBFN / JAX pin decision (recorded 2026-09-03)

`protbfn_venv` ships the JAX/Haiku/Flax/Optax stack only so the
upstream-shim route
(`adaptive_reflow.adapters.protbfn_abbfn_upstream_shim`,
`force_mode="upstream_jax"`) can import
`data/protbfn_abbfn/repo/{model,sample,inpaint,loss}.py` from the
cloned InstaDeep repo. The framework's torch re-implementation in
`adaptive_reflow.adapters.protbfn_abbfn_model.ProtBFNAbBFNModel` is the
canonical adapter path, and the JAX-free pytree loader
(`protbfn_abbfn_jax_loader.py`) reconstructs the Haiku param tree
without importing JAX. JAX is therefore an *opt-in optional
dependency* of the framework, not a measurement dependency.

Two pin sets were considered:

| | Original (paper-fidelity) | Current (in-tree, 2026-09-03) |
|---|---|---|
| `dm-haiku` | `0.0.9` | `0.0.17` |
| `flax` | `0.7.2` | `0.12.9` |
| `jax` / `jaxlib` | `0.4.13` | `0.11.1` |
| `numpy` | `1.24` | `>=1.23,<3` (project venv caps `<2.5`) |
| `python` | `3.9` | `3.12.13` |
| Source | `data/protbfn_abbfn/repo/environment.yaml` | `protbfn_venv` resolved set |

**Original pin set cannot be installed on this rig:**

- `dm-haiku 0.0.9` calls `jax.linear_transpose` (removed in jax≥0.5)
  and `jax.experimental.optimizers` (removed in jax≥0.4.30). The
  0.0.9/0.7.2/0.4.13 triple is internally consistent on jax 0.4.x,
  but jax 0.4.x pre-dates the modern wheel format: the
  `jax[cuda12]==0.4.13` release on the JAX release channel only
  publishes cp39/cp40 wheels, **not cp312**. Installing on Python 3.12
  would require building jaxlib from source against the CUDA 12.8
  toolchain — multi-hour and out of scope.
- `flax 0.7.2` imports `flax.linen` from a module layout that was
  reorganised in flax 0.8+; on Python 3.12, `flax 0.7.2` raises
  `TypeError: 'type' object is not subscriptable` at import time (it
  still uses PEP-585 generics that landed in 3.9 but were removed
  from flax 0.8's pre-3.10 compat shim path).
- The framework's project venv requires `numpy<2.5`; the upstream
  `environment.yaml` pins `numpy==1.24`, which the project's
  `protbfn_abbfn_jax_loader` cannot tolerate (it uses the
  `numpy._core.multiarray._reconstruct` path that landed in numpy
  2.0+).
- InstaDeep's upstream does **not** publish new pins. Their
  `environment.yaml` (the file at `data/protbfn_abbfn/repo/`) is the
  original 0.0.9/0.7.2/0.4.13 set with no later commit; they ship
  the **Dockerfile** as the reproducibility mechanism. The
  Dockerfile pins `nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04` and
  micromamba-installs the pins above; reproducing that Docker build
  on a current rig is a separate multi-hour effort and is not in
  scope for this task.

**Current pins work** (verified 2026-09-03 by importing
`data.protbfn_abbfn.repo.model.get_transformer_fn` and `sample.py`
from `protbfn_venv`; both succeed and `hk.transform(fn).init(rng)`
runs for `model_size="ProtBFN"`).

**Recommendation (research-only, no install):**

> Keep the current 0.0.17 / 0.12.9 / 0.11.1 set as the installed
> `protbfn_venv` baseline. Treat the original 0.0.9/0.7.2/0.4.13 pins
> as a "paper-fidelity" alternative that is reproducible **only via
> the upstream Dockerfile on CUDA 11.8 + Python 3.9**, not as an
> in-tree install target. If a future project wants paper-fidelity
> numbers, it should build the InstaDeep Docker image and run
> `sample.py` inside that container; the framework's metrics are
> produced outside that environment.

The full reasoning, the reproducer, and the resolved set are recorded
in `requirements/protbfn.lock` (a documentation-only artefact, not a
uv/pip-installable lockfile — the JAX stack is not a transitive
project dependency and is not present in `pyproject.toml`).