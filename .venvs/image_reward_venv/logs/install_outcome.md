# ImageReward venv install outcome (2026-09-03)

## Summary

`image-reward==1.5` (PyPI) installs in `.venvs/image_reward_venv` (Python 3.12.13)
and the module imports cleanly. The wrapper code at `tools/run_image_eval.py::run_image_reward_metric`
is ready to invoke it as a subprocess.

## Install commands

```bash
uv venv --python 3.12 .venvs/image_reward_venv --seed
uv pip install --python .venvs/image_reward_venv/bin/python image-reward
# The setup.py declared `clip @ https://github.com/openai/CLIP/archive/refs/heads/main.zip`
# but uv's resolver did NOT pull it (the dependency_links is a deprecated pip feature,
# ignored by PEP 517 resolvers). Install it explicitly:
uv pip install --python .venvs/image_reward_venv/bin/python "clip @ git+https://github.com/openai/CLIP.git"
# Pin transformers / diffusers / accelerate to ranges compatible with the 2023-era
# vendored BLIP (`transformers.models.bert`) and the AestheticScore module:
uv pip install --python .venvs/image_reward_venv/bin/python "transformers>=4.27.4,<4.40"
uv pip install --python .venvs/image_reward_venv/bin/python "diffusers>=0.16.0,<0.30" "accelerate>=0.16.0,<0.30"
```

## Failure modes encountered (and resolved)

1. **`ModuleNotFoundError: No module named 'clip'`** — the `dependency_links`
   entry in `setup.py` (`clip @ https://github.com/openai/CLIP/archive/refs/heads/main.zip`)
   is a pre-PEP-517 legacy mechanism that uv / pip 25+ ignore. Resolved by
   installing `clip` from `git+https://github.com/openai/CLIP.git` directly
   (resolves to commit `d05afc436d78f1c48dc0dbf8e5980a9d471f35f6`, builds
   `clip==1.0` + the transitive `ftfy` + `wcwidth`).

2. **`ImportError: cannot import name 'apply_chunking_to_forward' from
   'transformers.modeling_utils'`** — the upstream
   `ImageReward/models/BLIP/med.py` imports `apply_chunking_to_forward` which was
   removed in transformers ≥ 5.x (it's still present in 4.x). Resolved by pinning
   `transformers>=4.27.4,<4.40` (resolved to `transformers==4.39.3`, with the
   transitive `huggingface-hub==0.36.2` + `tokenizers==0.15.2`).

3. **`RuntimeError: Failed to import diffusers.models.autoencoders.autoencoder_kl
   because of the following error: cannot import name 'Dinov2WithRegistersConfig' from 'transformers'`** —
   diffusers 0.40 (uv's resolver default) needs a newer transformers. Resolved
   by pinning `diffusers>=0.16.0,<0.30` and `accelerate>=0.16.0,<0.30`
   (resolved to `diffusers==0.29.2`, `accelerate==0.29.3`).

After all three pins, `import ImageReward` succeeds and the API surface
(`ImageReward.load`, `ImageReward.ImageReward`) is available.

## Verification (CPU only — no GPU inference)

```python
>>> import ImageReward as RM
>>> RM.load                       # bound method, callable
>>> RM.ImageReward                # class, instantiable (RM.load constructs it internally)
```

`RM.load("ImageReward-v1.0")` itself downloads ~3.6 GB from
`huggingface.co/THUDM/ImageReward` (`med_config.json`, `blip.pth`, MLP head
weights) on first call. This is gated behind `--image-reward-binary` (the operator
must explicitly opt-in) and is NOT triggered by the smoke-import above. The
wrapper emits a `marker: "not_installed"` block when the binary path is missing
so a fresh checkout stays byte-stable with the legacy stub.

## Pinned versions in this venv

| Package | Resolved version | Why pinned |
|---|---|---|
| `image-reward` | 1.5 | the metric itself |
| `clip` | 1.0 (git+https://github.com/openai/CLIP.git@d05afc...) | AestheticScore submodule import |
| `transformers` | 4.39.3 (`>=4.27.4,<4.40`) | `apply_chunking_to_forward` removed in 5.x |
| `diffusers` | 0.29.2 (`>=0.16.0,<0.30`) | needs transformers ≤ 4.x for Dinov2 compat |
| `accelerate` | 0.29.3 (`>=0.16.0,<0.30`) | matches diffusers 0.29 |
| `torch` | 2.14.0 (resolver default) | not pinned; uv resolved to latest stable |

## CUDA note

The BLIP visual encoder + MLP head (~3.6 GB checkpoint) fit comfortably on GPU 0
(RTX PRO 6000, 98 GB) alongside the InceptionV3 + CLIP backbone + HiDream-I1-Dev
(24 GB). The wrapper passes `--image-reward-gpu-id 0` through `CUDA_VISIBLE_DEVICES`
exactly like the GenEval wrapper does.

## Operator next steps

To use the wrapper:

```bash
# 1. Pre-download the model checkpoint once (one-time, ~3.6 GB)
HF_HUB_OFFLINE=0 .venvs/image_reward_venv/bin/python -c \
  "import ImageReward as RM; m = RM.load('ImageReward-v1.0'); print('loaded')"
#   The download pulls from https://huggingface.co/THUDM/ImageReward.

# 2. Run the image-eval runner with the wrapper enabled
python tools/run_image_eval.py \
  --samples-dir data/lumina_image_2_0/samples \
  --prompts-jsonl data/lumina_image_2_0/prompts.jsonl \
  --output data/lumina_image_2_0/eval_report.json \
  --image-reward-binary .venvs/image_reward_venv/bin/python \
  --image-reward-model ImageReward-v1.0 \
  --image-reward-gpu-id 0 \
  --image-reward-timeout 600

# 3. Inspect
python -c "import json; r=json.load(open('data/lumina_image_2_0/eval_report.json')); print(json.dumps(r['metrics']['image_reward'], indent=2))"
```