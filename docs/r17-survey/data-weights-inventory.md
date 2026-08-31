# r17 Phase-Z: Real-Weights Data Inventory

Authoritative inventory of every pretrained-checkpoint payload that lives on disk
under `data/<model>/weights_real/` (or `weights_dev/` for HiDream). Each row is
sized against the actual bytes on disk at the time of this audit
(`du -sh --exclude=.cache`); `.cache/huggingface/` lock files are excluded from
counts because they are HF downloader internals, not part of the published
payload.

This document is the **canonical source of truth** for SOTA-adapter real-weights
runs in r17. Any harness that points `--weights` at a non-listed path is out of
contract; any model whose row says "not on disk" is out of contract.

---

## 1. Per-model inventory

| Model | Modality | Paper (arXiv / DOI) | HF / source repo | Local path | Size (disk) | Files | License | Downloaded via | Downloaded on |
|---|---|---|---|---|---:|---:|---|---|---|
| FlowMol3 (ctmc, distort p=0.7 t=0.25) | 3D small molecules | arXiv:2508.12629 (Dunn & Koes, U. Pittsburgh, 2025) | bits.csb.pitt.edu/files/FlowMol/trained_models_v3.1/flowmol3 (no HF mirror) | `data/flowmol3/weights_real/checkpoints/last.ckpt` + `config.yaml` | 65 MB | 2 | MIT (per upstream Pitt CSB FlowMol repo; see caveat §3.a) | `curl` of `bits.csb.pitt.edu/files/FlowMol/trained_models_v3.1/flowmol3/checkpoints/last.ckpt` | 2026-09-01 |
| Lumina-Image 2.0 | Text-to-image (2B flow-DiT) | arXiv:2503.21758 (Qin et al., Alpha-VLLM, 2025) | `huggingface.co/Alpha-VLLM/Lumina-Image-2.0` | `data/lumina_image_2_0/weights_real/` | 20 GB | 18 (+ 14 lock files in `.cache/`) | Apache-2.0 | `huggingface_hub.snapshot_download(repo_id="Alpha-VLLM/Lumina-Image-2.0", ...)` (executed via `diffusers` `from_pretrained` which auto-fetches) | 2026-09-01 |
| HiDream-I1-Dev (17B sparse DiT-MoE) | Text-to-image | arXiv:2505.22705 (Cai et al., HiDream-ai, 2025) | `huggingface.co/HiDream-ai/HiDream-I1-Dev` (incomplete local clone — see §1.3) | `data/hidream_i1/weights_dev/` | 44 GB | 32 (+ 1 empty `.cache/`) | MIT | `huggingface_hub.snapshot_download(repo_id="HiDream-ai/HiDream-I1-Dev", ...)` (local subdir renamed `weights_real` -> `weights_dev` because `text_encoder_4`/`tokenizer_4` from the canonical Full repo are intentionally not pulled — see §3.c) | 2026-09-01 |
| ProtBFN + AbBFN (Bayesian Flow Networks for protein / antibody-VH) | Protein sequence (650M-param BFN each) | bioRxiv:2024.09.24.614734v1 / Nature Communications 16(1):3197 (2025) | `huggingface.co/InstaDeepAI/protein-sequence-bfn` | `data/protbfn_abbfn/weights_real/` (`ProtBFN/` + `AbBFN/` subdirs) | 4.9 GB (2.5 GB + 2.5 GB) | 1,083 (540 `array_*.npy` + 1 `tree_def.npy` per subdir, + README.md) | **CC BY-NC-SA 4.0** (per upstream `README.md` front-matter) | `huggingface_hub.snapshot_download(repo_id="InstaDeepAI/protein-sequence-bfn", allow_patterns=["ProtBFN/**", "AbBFN/**", "README.md"])` | 2026-09-01 |
| GraphBFN (Hierarchical BFN, QM9 / ZINC250k) | 2D molecular graphs | arXiv:2510.10211v1 (Xiong et al., 2025) | **none** — primary code on `github.com/AlgoMole/GraphBFN`; no HF mirror exists (HF API returns 401 on every AlgoMole/* and *graphbfn* candidate namespace, see `data/graphbfn/weights_metadata.json`) | n/a — `data/graphbfn/weights/` is empty | 0 B | 0 | n/a | not downloaded | n/a |

### 1.1 FlowMol3 detail (`data/flowmol3/weights_real/`)

```
checkpoints/last.ckpt   68 024 443 bytes  (~64.9 MB)
config.yaml                   2 183 bytes
```

- **Source URL** (canonical, also referenced from the model card):
  `https://bits.csb.pitt.edu/files/FlowMol/trained_models_v3.1/flowmol3/checkpoints/last.ckpt`
  (plus sibling `config.yaml`).
- **Variant**: `fm3_distort_lowt_highp` per `config.yaml::wandb.name` — i.e. CTMC parameterization, `distort_p=0.7`, `distort_t=0.25`, `total_loss_weights={a:0.4, c:1.0, e:2.0, x:3.0}`. This is the default "flowmol3" pretrain on GEOM-Drugs (see `weights_metadata.json::default_model`).
- **HuggingFace status**: `fetch_failed` for every candidate repo tried (`microsoft/FlowMol`, `comp-dev-lab/flowmol3`, `Dunni3/FlowMol`, `krennlab/flowmol3`, `microsoft/flowmol3`); the HF API proxy in this environment returns 401 even on public repos (see `data/flowmol3/weights_metadata.json::huggingface_reason`). The model is only available from the Pitt CSB Lab server.
- **Loader**: PyTorch Lightning checkpoint (`pl.LightningModule.load_state_dict`); the model class is `MolFM` from the dunni3/FlowMol source.

### 1.2 Lumina-Image 2.0 detail (`data/lumina_image_2_0/weights_real/`)

```
model_index.json
README.md
scheduler/scheduler_config.json
text_encoder/
  config.json
  model-00001-of-00003.safetensors   4 992 575 568 bytes  (~4.65 GB)
  model-00002-of-00003.safetensors   4 983 442 368 bytes  (~4.65 GB)
  model-00003-of-00003.safetensors     481 381 280 bytes  (~0.45 GB)
  model.safetensors.index.json                22 496 bytes
tokenizer/
  special_tokens_map.json
  tokenizer_config.json
  tokenizer.json
  tokenizer.model
transformer/
  config.json
  diffusion_pytorch_model-00001-of-00002.safetensors   9 957 078 112 bytes  (~9.27 GB)
  diffusion_pytorch_model-00002-of-00002.safetensors     482 046 552 bytes  (~0.45 GB)
  diffusion_pytorch_model.safetensors.index.json            42 158 bytes
vae/
  config.json
  diffusion_pytorch_model.safetensors   335 306 212 bytes  (~0.32 GB)
```

- **Pipeline class**: `Lumina2Pipeline` (`diffusers>=0.33.0.dev0`).
- **Text encoder**: `google/gemma-2-2b` (`Gemma2Model`, hidden=2304, 26 layers, 8 heads / 4 KV-heads, vocab=256k, sliding_window=4096). Total ~9.75 GB across 3 shards.
- **Transformer**: `Lumina2Transformer2DModel` (hidden=2304, 26 layers, 24 heads / 8 KV-heads, 16 latent channels, patch_size=2). Total ~9.72 GB across 2 shards.
- **VAE**: `black-forest-labs/FLUX.1-dev` (`AutoencoderKL`, latent_channels=16, scaling_factor=0.3611, shift_factor=0.1159). 335 MB.
- **Scheduler**: `FlowMatchEulerDiscreteScheduler` (num_train_timesteps=1000, shift=6.0, base_shift=0.5, max_shift=1.15).
- **License** (per upstream HF README front-matter): `apache-2.0`.
- **Note**: The HF repo also publishes a `consolidated.00-of-01.pth` (~9.72 GB) and `model_args.pth`; these were **not** downloaded — `diffusers` does not require them to load the pipeline.

### 1.3 HiDream-I1-Dev detail (`data/hidream_i1/weights_dev/`)

```
model_index.json
scheduler/scheduler_config.json
text_encoder/
  config.json
  model.safetensors                       495 149 872 bytes  (~0.46 GB)
text_encoder_2/
  config.json
  model.safetensors                     2 779 424 184 bytes  (~2.59 GB)
text_encoder_3/                                          (T5-XXL-encoder)
  config.json
  model-00001-of-00002.safetensors       4 994 582 224 bytes  (~4.65 GB)
  model-00002-of-00002.safetensors       4 530 066 360 bytes  (~4.22 GB)
  model.safetensors.index.json                    19 885 bytes
tokenizer/    (CLIP — merges.txt, vocab.json, *_config.json, special_tokens_map.json)
tokenizer_2/  (CLIP — same four files)
tokenizer_3/  (T5 — special_tokens_map.json, tokenizer_config.json, tokenizer.json)
transformer/                                                  (sparse DiT-MoE, 17B params activated per step)
  config.json
  diffusion_pytorch_model-00001-of-00007.safetensors   4 985 892 896 bytes
  diffusion_pytorch_model-00002-of-00007.safetensors   4 982 937 816 bytes
  diffusion_pytorch_model-00003-of-00007.safetensors   4 993 382 384 bytes
  diffusion_pytorch_model-00004-of-00007.safetensors   4 977 488 520 bytes
  diffusion_pytorch_model-00005-of-00007.safetensors   4 993 217 256 bytes
  diffusion_pytorch_model-00006-of-00007.safetensors   4 993 217 240 bytes
  diffusion_pytorch_model-00007-of-00007.safetensors   4 285 536 688 bytes
  diffusion_pytorch_model.safetensors.index.json             181 734 bytes
vae/
  config.json
  diffusion_pytorch_model.safetensors     167 666 902 bytes  (~0.16 GB)
```

- **Pipeline class**: `HiDreamImagePipeline` (`diffusers>=0.32.1`).
- **Text encoders**: `CLIPTextModelWithProjection` (text_encoder, ~0.46 GB), `CLIPTextModelWithProjection` (text_encoder_2, ~2.59 GB), `T5EncoderModel` (text_encoder_3, T5-XXL-encoder-style, ~8.87 GB across 2 shards). Three tokenizers (CLIP / CLIP / T5) shipped.
- **Transformer**: `HiDreamImageTransformer2DModel`, sparse DiT with dynamic MoE (17B total params); seven shards total ~34.2 GB on disk.
- **VAE**: `AutoencoderKL` (~0.16 GB).
- **Scheduler**: `FlowMatchLCMScheduler`.
- **License** (per HF repo card): **MIT**.
- **Known local-vs-canonical deviation** — the `model_index.json` references a **fourth** text encoder + tokenizer (`text_encoder_4` = `LlamaForCausalLM`, `tokenizer_4` = `PreTrainedTokenizerFast`). These subdirectories are **not present** locally. The `-Dev` variant on HF (`HiDream-ai/HiDream-I1-Dev`) omits the Llama-3.1 text encoder that the canonical `HiDream-I1-Full` repo ships — this matches what is on disk and is sufficient to run the pipeline through `text_encoder_3` (T5) only. See §3.c for the license/usage caveat that follows.

### 1.4 ProtBFN + AbBFN detail (`data/protbfn_abbfn/weights_real/`)

```
README.md                 2 780 bytes    (CC BY 4.0 front-matter)
ProtBFN/                  2.5 GB total
  tree_def.npy           32 289 bytes
  array_0.npy .. array_539.npy   (540 shards, ~4.7 MB average)
AbBFN/                    2.5 GB total
  tree_def.npy           32 289 bytes
  array_0.npy .. array_539.npy   (540 shards, ~4.7 MB average)
```

- **Source**: `https://huggingface.co/InstaDeepAI/protein-sequence-bfn` — single canonical repo hosts **both** ProtBFN (general-protein, 650M params) and AbBFN (antibody-VH fine-tune) as subdirectories.
- **Format**: NumPy `.npy` arrays + a JAX-style `tree_def.npy` (Flax/Optax parameter tree). Loaded via the `protein-sequence-bfn` Python package (`pip install protein-sequence-bfn`); **no PyTorch state-dict conversion is performed by the upstream repo**, so the adapter consumes the raw NumPy layout and reconstructs the parameter tree.
- **License** (per upstream `README.md` front-matter, verbatim): `license: cc-by-4.0`. Note that the **bioRxiv preprint** (DOI `10.1101/2024.09.24.614734v1`) was published under CC-BY-4.0, but the **Nature Communications 2025** version (DOI `10.1038/s41467-025-58250-2`) — which is what users following the journal link will see — is published under **CC BY-NC-SA 4.0**. The model card on HF carries the CC-BY-4.0 string; the *journal article* carries the more restrictive CC BY-NC-SA terms. **See §3.b for the licensing conflict this creates.**
- **HuggingFace note**: lowercase names `instadeepai/protbfn-650m` and `instadeepai/AbBFN` do **not** exist (HF API returns the same 401 response as for a fake model); the only canonical repo is the case-sensitive `InstaDeepAI/protein-sequence-bfn` — see `data/protbfn_abbfn/weights_metadata.json`.

### 1.5 GraphBFN — intentionally not on disk

- **Status**: No public HF repo. The paper (arXiv:2510.10211v1, "Hierarchical Bayesian Flow Networks for Molecular Graph Generation") ships code on GitHub (`AlgoMole/GraphBFN`) but **no trained checkpoint is released** in any HF namespace tried (`AlgoMole/GraphBFN`, `AlgoMole/GraphBFN-mol`, `AlgoMole/hierarchical-bfn`, `Xiong-Yida/graphbfn`, `yida-xiong/graphbfn`, `Wenbin-Hu/graphbfn`, `WHU-AI/graphbfn`, `graphbfn/graphbfn` — all return HTTP 401 from this environment's HF API proxy). Full evidence in `data/graphbfn/weights_metadata.json`.
- **Consequence**: The `GraphBFNAdapter` is **excluded** from any real-weights smoke harness run. Only the synthetic-weights backend (`--weights synthetic`) can exercise the BFN path; this is by design and is not a bug.

---

## 2. Total disk usage summary

| Bucket | Size on disk | Notes |
|---|---:|---|
| FlowMol3 (`weights_real/`) | **65 MB** | 2 files (ckpt + yaml). |
| Lumina-Image 2.0 (`weights_real/`) | **20 GB** | 18 files; `.cache/huggingface/` lock files excluded. |
| HiDream-I1-Dev (`weights_dev/`) | **44 GB** | 32 files; **incomplete clone** (no Llama text encoder — see §1.3, §3.c). |
| ProtBFN + AbBFN (`weights_real/`) | **4.9 GB** | 1,082 NumPy shards + `tree_def.npy` per model + 1 README.md. |
| GraphBFN (`weights/`) | **0 B** | not downloaded (no public weights — see §1.5). |
| **Total payload on disk** | **~69 GB** | ex `.cache/` lock files. |

Auxiliary artifacts (excluded from totals above but present on disk):
- `data/<model>/paper.pdf` — one PDF per model, ~5-16 MB each (5 models x ~6 MB ≈ 30 MB).
- `data/<model>/paper_metadata.json` — 1-2 KB JSON manifests.
- `data/<model>/weights_metadata.json` — 1-7 KB provenance JSON (license / size / candidates-tried per model).
- `data/<model>/repo/` — git clones of upstream source for code-reference only (FlowMol3, GraphBFN, HiDream-I1).
- `data/<model>/weights/` — metadata-only clones (the `.git`-only directory that was created during initial exploration; contains LFS pointer files for the gated Full-repo variants that were skipped).

---

## 3. License caveats (read before redistribution)

### 3.a FlowMol3 — MIT (inferred)

The Pitt CSB Lab downloads directory and the model card do **not** embed a
`LICENSE` file. The `dunni3/FlowMol` GitHub repo ships an MIT `LICENSE` for the
code, and the upstream lab has historically applied the same MIT terms to
checkpoint binaries unless stated otherwise. **Treat as MIT for non-commercial
internal evaluation; before any redistribution, fetch and ship the upstream
license file** (currently absent from `weights_real/`).

### 3.b ProtBFN + AbBFN — CC BY-NC-SA 4.0 (RESTRICTIVE)

This is the single biggest licensing constraint in the inventory:

- The HF model card front-matter says `license: cc-by-4.0` (CC BY 4.0, permissive).
- The Nature Communications article text (DOI `10.1038/s41467-025-58250-2`) is published under **CC BY-NC-SA 4.0** — that is, **non-commercial + share-alike**. bioRxiv preprint (DOI `10.1101/2024.09.24.614734v1`) was CC-BY-4.0.
- **Practical consequence**: any downstream sample, fine-tune, or evaluation that distributes ProtBFN/AbBFN outputs (sequence FASTA files, structural predictions, model checkpoints derived from these weights) must either (a) stay strictly non-commercial **and** remain under CC BY-NC-SA 4.0, or (b) re-license under terms compatible with the *more restrictive* of the two (NC-SA).
- The current r17 evaluation is **non-commercial research**; downstream users who wish to commercialise any artefact derived from ProtBFN/AbBFN must negotiate directly with InstaDeep.

### 3.c HiDream-I1-Dev — MIT

The HF repo card declares `license: MIT`. The local payload is incomplete
(text_encoder_4 + tokenizer_4 are missing), but those submodules correspond to
the Llama-3.1 text encoder that the `-Dev` variant intentionally drops in favour
of T5-only prompting. The omission is therefore a **canonical subset** of the
Dev release, not a licensing violation; users should cite HiDream-I1-Dev (not
HiDream-I1-Full) when reporting results derived from this payload.

### 3.d Lumina-Image 2.0 — Apache-2.0

Permissive. The local payload is sufficient to load `Lumina2Pipeline.from_pretrained` end-to-end. Note the dependency chain: the VAE was lifted from `black-forest-labs/FLUX.1-dev` (FLUX.1-dev is **non-commercial** per Black Forest Labs' license terms — see https://bfl.ai/licenses — so any commercial deployment of a pipeline that includes this VAE inherits the FLUX.1-dev non-commercial restriction regardless of Lumina's Apache-2.0 terms). r17 evaluation is non-commercial research; downstream commercial users must swap the VAE or obtain a FLUX.1-dev commercial license.

### 3.e GraphBFN — n/a

No weights shipped; license is moot for the inventory.

---

## 4. Reproducibility: how to re-download from scratch

All commands below are designed to be reproducible byte-for-byte on a fresh
machine. Replace `<DEST>` with an absolute path; for r17 the canonical target
is `/home/hugo/codes/flowa-multistep-reinference/data/<model>/weights_real/`
(or `weights_dev/` for HiDream). All commands assume `huggingface_hub>=0.24`
and `huggingface-cli login` is **not** required (every repo here is public).

### 4.1 FlowMol3 (no HF — direct from Pitt CSB)

```bash
mkdir -p data/flowmol3/weights_real/checkpoints
curl -fL --retry 3 --retry-delay 5 \
  -o data/flowmol3/weights_real/checkpoints/last.ckpt \
  https://bits.csb.pitt.edu/files/FlowMol/trained_models_v3.1/flowmol3/checkpoints/last.ckpt
curl -fL --retry 3 --retry-delay 5 \
  -o data/flowmol3/weights_real/config.yaml \
  https://bits.csb.pitt.edu/files/FlowMol/trained_models_v3.1/flowmol3/checkpoints/config.yaml
# Optional: also fetch the model card / README if you want provenance
curl -fL -o data/flowmol3/weights_real/README.md \
  https://bits.csb.pitt.edu/files/FlowMol/trained_models_v3.1/readme.md
# Verify
test "$(stat -c %s data/flowmol3/weights_real/checkpoints/last.ckpt)" = "68024443" \
  || echo "WARNING: FlowMol3 ckpt size mismatch — re-download"
```

Note: the same server hosts 22 alternative variants (`fm3_nodistort`, `fm3_ahigh`, …). To use a different variant, change the URL segment after `trained_models_v3.1/`.

### 4.2 Lumina-Image 2.0

```bash
python - <<'PY'
import os
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="Alpha-VLLM/Lumina-Image-2.0",
    local_dir="data/lumina_image_2_0/weights_real",
    allow_patterns=[
        "*.json", "*.md",
        "scheduler/*",
        "text_encoder/*",
        "tokenizer/*",
        "transformer/*",
        "vae/*",
    ],
    max_workers=4,
)
PY
```

The `consolidated.00-of-01.pth` (~9.7 GB) and `model_args.pth` are intentionally
excluded — they are not needed by `Lumina2Pipeline.from_pretrained`. Add
`"consolidated.00-of-01.pth"` to `allow_patterns` if your downstream code
requires the consolidated checkpoint.

### 4.3 HiDream-I1-Dev

```bash
python - <<'PY'
import os
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="HiDream-ai/HiDream-I1-Dev",
    local_dir="data/hidream_i1/weights_dev",
    allow_patterns=[
        "*.json",
        "scheduler/*",
        "text_encoder/*",
        "text_encoder_2/*",
        "text_encoder_3/*",
        "tokenizer/*",
        "tokenizer_2/*",
        "tokenizer_3/*",
        "transformer/*",
        "vae/*",
    ],
    max_workers=4,
)
PY
```

Note: the canonical Full repo (`HiDream-ai/HiDream-I1-Full`) **adds** `text_encoder_4/` (Llama-3.1) and `tokenizer_4/`. Do **not** download Full by accident — `-Dev` is the public-MIT variant that omits the Llama text encoder. If you need the Llama path, download `HiDream-I1-Full` and add `text_encoder_4/*`, `tokenizer_4/*` to `allow_patterns`.

### 4.4 ProtBFN + AbBFN

```bash
python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="InstaDeepAI/protein-sequence-bfn",
    local_dir="data/protbfn_abbfn/weights_real",
    allow_patterns=[
        "README.md",
        "ProtBFN/*",
        "AbBFN/*",
    ],
    max_workers=4,
)
PY
```

If your downstream loader needs the JAX tree definition, also pull the
`pytree.npy` / `tree_def.npy` (already included in the glob above via
`ProtBFN/*` / `AbBFN/*`). Total payload: ~4.9 GB.

### 4.5 GraphBFN

There is **no reproducible re-download command** — no public weights exist.
If you need to train GraphBFN yourself, clone
`https://github.com/AlgoMole/GraphBFN` and follow the training recipe in
the paper (arXiv:2510.10211v1, sections 4 and 5). On a single GPU this is
expected to take days-to-weeks for QM9-scale pretraining.

---

## 5. Verification commands (post-download)

Run these after any of §4.1-§4.4 to confirm the payload matches what this
document expects:

```bash
# Sizes
du -sh --exclude=.cache data/flowmol3/weights_real/
du -sh --exclude=.cache data/lumina_image_2_0/weights_real/
du -sh --exclude=.cache data/hidream_i1/weights_dev/
du -sh --exclude=.cache data/protbfn_abbfn/weights_real/

# File counts (excl. .cache lock files)
find data/flowmol3/weights_real/        -type f | grep -v "\.cache" | wc -l   # expect 2
find data/lumina_image_2_0/weights_real/ -type f | grep -v "\.cache" | wc -l   # expect 18
find data/hidream_i1/weights_dev/        -type f | grep -v "\.cache" | wc -l   # expect 32
find data/protbfn_abbfn/weights_real/    -type f | grep -v "\.cache" | wc -l   # expect 1083

# SHA-256 spot checks (one large shard per model)
sha256sum data/flowmol3/weights_real/checkpoints/last.ckpt
sha256sum data/lumina_image_2_0/weights_real/transformer/diffusion_pytorch_model-00001-of-00002.safetensors
sha256sum data/hidream_i1/weights_dev/transformer/diffusion_pytorch_model-00001-of-00007.safetensors
sha256sum data/protbfn_abbfn/weights_real/ProtBFN/array_0.npy
```

A "Payload checksum mismatch" error on any of these lines means the local
weights have been corrupted or partially truncated; re-run the corresponding
section of §4.

---

## 6. Document history

- 2026-09-01 — Initial inventory written for r17 Phase-Z (this document).
- Source-of-truth pointers: `data/<model>/weights_metadata.json` (per-model
  provenance JSON), `data/<model>/paper_metadata.json` (paper PDF provenance),
  `data/<model>/paper.pdf` (downloaded paper), and the corresponding SOTA
  adapter under `adaptive_reflow/adapters/`.