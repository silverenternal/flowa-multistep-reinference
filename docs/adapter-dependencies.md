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

## kanzi / kanzi_adapter (Wave 21 PHASE-3)

- `torch>=2.1` — Kanzi encoder forward + flow-head
- `numpy>=2.0,<2.5` — already in framework core
- `biopython>=1.88` — protein alphabet (one-letter amino-acid vocabulary
  helpers; same dep as LineageFlow since both adapters speak the same
  alphabet)
- `rdkit>=2024.3.1` — amino-acid SMILES round-trip validity oracle
  (optional; only exercised by ``run_real_ckpt_eval.py --model kanzi``
  when computing protein_sequence_validity_rate)

## freqflow / freqflow_adapter (Wave 21 PHASE-3)

> **PHASE-4 status (2026-09-05 user directive):** **DEFERRED_no_upstream_ckpt**.
> Adapter file remains registered (Wave 36 Agent B fixed the missing-from-registry
> bug) and the D.5 conformance battery synthetic-mode coverage (8 checks) is
> complete. The real-ckpt forward path is **not buildable**: upstream
> `nnet_ema.pth` does not exist publicly anywhere (no GitHub releases, no HF Hub
> releases, no PyPI package; README's `--nnet_path=/path/to/nnet_ema.pth` is a
> placeholder in the authors' own command line, not a download URL). PHASE-4
> active scope is now `{kanzi, lineageflow}`; FreqFlow is not in
> `tools/run_real_ckpt_eval.py:PHASE4_ACTIVE_MODELS`.

- `torch>=2.1` — FreqFlow forward + frequency-domain head (registered, but not
  loadable with a real ckpt — listed for future-wave unblock via sidecar venv)
- `numpy>=2.0,<2.5` — already in framework core
- `torchvision>=0.15,<1.0` — image pre/post-processing + canonical
  InceptionV3 (IMAGENET1K_V1) for FID computation per
  ``tools/run_image_eval.py:load_inception_for_fid``
- `diffusers>=0.32` — optional; only required when FreqFlow is loaded
  via the HF Hub pipeline (deferred until upstream releases weights)

## mm_fm / mm_fm_adapter (Wave 21 PHASE-3)

> **PHASE-4 status (2026-09-05 user directive):** **DEFERRED_no_adapter_shipped**.
> No shipped adapter file (Wave 21 M-agent + Wave 21.5 re-spawn both stalled).
> Future re-spawn with explicit 4-sub-agent scope-split is documented in
> `docs/audit/mm-fm-unblock-investigation.md` but is NOT on the PHASE-4
> critical path. Per 2026-09-05 user directive, MM-FM is classified as
> out-of-scope.

- `torch>=2.1` (expected when/if adapter ships)
- `diffusers>=0.32` — multi-modal pipeline
- `transformers` — text encoder + tokenizer (transitive of diffusers)
- `safetensors` — weight loading (transitive)
- `Pillow` — image I/O (transitive)
- Wave 36 PHASE-4 eval reports MM-FM cells as
  ``DEFERRED_no_adapter_shipped`` in
  ``tools/run_real_ckpt_eval.py`` rather than fabricating numbers

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

## Paper-anchored core (universal)

The framework's correctness proofs in `adaptive_reflow/theory/` cite the
underlying JMAA paper (Li 2026). The following theorem anchors live in
the framework core and do **not** add any per-adapter dependencies:

- **Theorem 1** (BL-convergence, paper §3.1) — `paper_quantities.rate_bound_C`
  and `rate_bound.py` materialise the explicit constant.
- **Lemma 2** (sheet evidence `A_g`) — `paper_quantities.sheet_evidence_A`.
- **Lemma 5** (root-cell packing `B_g`, exterior gap `e_rho`) —
  `paper_quantities.root_cell_packing_B` and `exterior_gap_e_rho`.

These citations live entirely under the stdlib-only `adaptive_reflow/theory/`
package (no torch / numpy / scipy), so the framework's paper-grounded
theory is part of the project venv's universal layer and is hashed by
`capture_env_hash.py` together with the framework's `uv.lock`.

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

## HuggingFace Hub upload pipeline (Wave 38 / R-3)

`tools/hf_pipeline.py` + the convenience wrapper
`scripts/upload_model_card.py` upload each `docs/models/M.model_card.md`
to a HuggingFace Hub `<user>/M` repo. This closes
**Papers-with-Code ML Code Completeness Checklist item (d)** (F.7) and
adds the YAML metadata block (F.8) per the Wave 32 Agent B audit.

### Pipeline deps

- `huggingface_hub>=0.20` — `HfApi.create_repo` + `upload_file`. Already
  in the framework's CI venv (declared transitive of `diffusers`); the
  upload script does a **lazy import** so `--help` and `--upload-dry-run`
  work on environments that lack it. NOT in the framework core's
  hard-required set: the upload is a release-time tool, not a runtime
  adapter dep, so the F.5 env_hash capture does not fold it in.

### CLI usage

```bash
# Validate + render-only (no HF Hub contact; no token required).
.venvs/flowmol3_venv/bin/python tools/hf_pipeline.py \
    --model kanzi --repo-id flowa-test/kanzi --upload-dry-run

# Real upload (requires `huggingface-cli login` OR `$HF_TOKEN`).
.venvs/flowmol3_venv/bin/python tools/hf_pipeline.py \
    --model lineageflow --repo-id <your-hf-user>/lineageflow
```

### Per-card YAML schema source

The `MODEL_METADATA` dict in `tools/hf_pipeline.py` is the single
source of truth for `library_name`, `pipeline_tag`, `license`,
`tags`, `datasets`. Adding a new integration = appending one entry
(no per-card file to maintain). Mirrors the SciMLBenchmarks.jl
`benchmark_attributes.jl` pattern.

### Editing protocol (HF Hub pipeline)

1. Add a new model to `tools/hf_pipeline.py:MODEL_METADATA`.
2. Author `docs/models/<model>.model_card.md` (Mitchell/Gebru 8 fields,
   Wave 24 Agent A F.4 schema).
3. Run the upload pipeline in `--upload-dry-run` first; verify the
   rendered README.md with `--render-only --output /tmp/<model>_README.md`
   and `git diff` (the local card is the source of truth).
4. Trigger the real upload with `huggingface-cli login` set up.