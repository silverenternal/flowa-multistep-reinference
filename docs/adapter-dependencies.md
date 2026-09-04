# Adapter-specific dependency manifest

This document is the canonical source of truth for which packages each
adapter requires **beyond** the framework core (`adaptive_reflow.*`).
Hashed by `scripts/capture_env_hash.py` for the F.5 env_hash gate.

When you add or modify an adapter's non-framework imports, update the
corresponding section below. Bumping a section without re-running
`capture_env_hash.py capture` will trip the F.5 verify gate.

## Framework core (universal)

These are part of the framework proper and are required for any adapter
to import. Tracked via `requirements-lock.txt` only:

- `numpy>=2.0,<2.5` (pinned for mypy 1.x compatibility)
- `scipy>=1.10` (sampling diagnostics, ML eden helpers)

## flowmol3 / flowmol3_v2_adapter

- `torch>=2.0` — UNet backbone + AdamW
- `rdkit>=2024.3.1` — SMILES canonicalisation + validity oracle
- `useful_rdkit_utils>=0.93` — ring-system fingerprint feature
- `dgl>=2.4.0` — graph convolution layers (FlowMol3 upstream hard dep
  at module-scope `import dgl`); Python 3.10-3.12 wheel availability
  varies — investigation needed for non-flowmol3_venv environments
- `torch_scatter` — segment_csr for atom-level aggregation
  (transitive of FlowMol3 upstream; optional when using shim path)
- `pytorch-lightning>=2.1` — FlowMol3 upstream trainer
- `torch_ema` — EMA helper used by FlowMol3 training loop

## twodim_fm / mnist_fm / self_flow / lineageflow / graphbfn

- `numpy>=2.0,<2.5` — already in framework core
- `torch>=2.0` — MLP / velocity-field, optional at framework level but
  required by every model-backed adapter that needs gradient descent
- `scipy>=1.10` — sampling diagnostics
- lineageflow additionally needs `biopython>=1.88` for protein alphabet
  encoding (one-letter amino-acid vocabulary helpers)

## rectified_flow_cifar

- `torch>=2.0`
- `torchvision>=0.15,<1.0` — DDPM++ UNet constructor
- `numpy>=2.0,<2.5`
- `scipy>=1.10`

## hidream_i1 / lumina_image_2_0

- `torch>=2.0`
- `diffusers>=0.32` — pipeline + scheduler (HiDreamImagePipeline /
  FlowMatchEulerDiscreteScheduler / Lumina2Pipeline)
- `transformers` — text encoder + tokenizer (transitive of diffusers)
- `accelerate` — device_map offload (transitive of diffusers >=0.27)
- `safetensors` — weight loading (transitive)
- Pillow — image I/O (transitive)

## wan2_2_video

- `torch>=2.0`
- `diffusers>=0.32` — WanVideoPipeline
- `transformers`, `accelerate`, `safetensors` — transitive of diffusers
- Optional `ftfy` + `bs4` — caption preprocessing for VBench

## protbfn_abbfn / protbfn_abbfn_adapter / protbfn_abbfn_model

- `torch>=2.0`
- `numpy>=2.0,<2.5`
- `biopython>=1.88` — protein alphabet
- JAX loader path (`protbfn_abbfn_jax_loader.py`) additionally needs
  `jax>=0.4` + `jaxlib` matching CUDA version — investigation needed
  whether jax loader path is exercised by current tests; if not, list
  as optional and defer to follow-up

## mnist_fm (TorchFMNIST)

- `torch>=2.0`
- `torchvision>=0.15,<1.0` — MNIST dataset loader
- `numpy>=2.0,<2.5`

## toy_gaussian / toy_linear / synthetic / stochastic_fm

- stdlib + `numpy>=2.0,<2.5` only. No adapter-specific deps.

## reference_flowa

- investigation needed: not yet audited which upstream packages the
  reference FlowA baseline pulls in (likely torch + rdkit by symmetry
  with FlowMol3, but unverified)

## Notes on non-installable / out-of-band deps

- HiDream-I1, Lumina-Image-2.0, Wan2.2 checkpoints are downloaded at
  runtime via `huggingface_hub` — declared transitive of diffusers but
  version-pinning the weight revisions lives in each upstream shim's
  `CHECKPOINT_REV` constant, not here.
- FlowMol3 upstream is imported via `flowmol3_upstream_shim.py`'s
  sys.path injection of `tools/flowmol/`; that vendored copy is part of
  the repo, not PyPI — its own `requirements.txt` is tracked
  separately under `tools/flowmol/requirements.txt`.

## Editing protocol

1. Add/remove a dep above.
2. Re-run: `python scripts/capture_env_hash.py capture`
3. Commit `env_hash.txt` alongside the change.