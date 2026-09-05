# Wave 36 Agent C — MM-FM unblock investigation

**Date:** 2026-09-05
**Wave:** 36 Agent C
**Repo:** flowa-multistep-reinference
**Scope:** Identify whether the MM-FM PHASE-3 adapter (Wave 21 + Wave 21.5
both stalled on all 6 attempts) can be written via a different shape, OR
should be re-classified as low-priority with Kanzi + FreqFlow covering
PHASE-4, OR can be served by a FlowMol3 v2 latent-space proxy.

---

## 1. Status recap

Per `todo/models/mm-fm.md` (last updated 2026-09-05):

- **MM-FM** (Luo et al., CVPR 2026, "Flow Matching for Multimodal
  Distributions") — DiT-XL/2 (≈675 M) operating on RAE (Representation
  Auto-Encoder) latents + small GMM-mode-selector head
- **HF Hub**: `luo00042/mm-fm` (160 GB total; cherry-pick ~5 GB for the
  2 DiT ckpts + RAE decoder + GMM stats + FID reference)
- **GitHub**: `GaoxiangLuo/MM-FM` (was assumed unreachable from sandbox;
  re-verified Wave 36 — REACHABLE via `WebFetch`)
- **Paper**: FID 2.78 on ImageNet-256 (DINOv2-B encoder, mode-conditional
  + GMM, 80 epochs, with AutoGuidance) — SOTA at submission time
- **PHASE-3 adapter**: `adaptive_reflow/adapters/mm_fm_adapter.py` does
  NOT exist
- **Wave 21 + Wave 21.5**: both stalled (605 k tokens consumed, 43 tool
  uses, 0 files produced)

## 2. Findings (re-investigation, Wave 36)

### 2.1 Upstream source IS reachable (new finding)

`WebFetch` to `https://github.com/GaoxiangLuo/MM-FM` succeeds. The repo
contains:

- `src/sample.py` — single-GPU sampling loop
- `src/sample_ddp.py` — distributed sampling (8-GPU FID-50K)
- `src/sample_in_dir.py` — batch sampling over a directory of inputs
- `src/train.py` — training entrypoint
- `src/stage2/` — `models/` (DiTwDDTHead, DiTDH-XL, DiTDH-S) + `transport/`
- `src/stage1/` — RAE (frozen encoders DINOv2-B / SigLIP2-B / MAE-B + ViT
  decoder)
- `configs/stage2/sampling/ImageNet256/` — 10 YAML configs (UNCONDITIONAL,
  UNCONDITIONAL-GMM, MODE-CONDITIONAL-GMM, all 3 encoders, plus `-AG`
  AutoGuidance variants)
- `artifacts/` — gitignored; populated by `hf download luo00042/mm-fm
  --local-dir artifacts`

### 2.2 Forward-call contract (from `src/sample_ddp.py`)

For unconditional (simplest case) the model call is:

```python
sample_fn = sampler.sample_ode  # or sample_sde
samples = sample_fn(z, model.forward, **model_kwargs)[-1]
# where model.forward(z, t, y=None) returns velocity (latent space)
```

For mode-conditional + AutoGuidance (the published best result, FID 2.78):

```python
y = gmm_sampler.sample_modes_weighted(n, device)
z = gmm_sampler.sample(y, latent_size, device, latent_dtype)
samples = sample_fn(
    z,
    model.forward_with_autoguidance,  # wraps two forward calls
    y=y,
    cfg_scale=cfg_scale,
    cfg_interval=(t_min, t_max),
    additional_model_forward=guid_model_forward,
)[-1]
images = rae.decode(samples)  # back to pixel space
```

Default sampler is Euler 50 NFE (`num_steps: 50` in YAML); guidance scale
1.5 with `t_min: 0.0, t_max: 1.0`.

### 2.3 HF file listing (verified via `WebFetch`)

- **DiT-XL ckpts (cherry-pickable, ~5 GB total)**:
  - `checkpoints/dinov2-b/uncond-gmm-25k.pt` (~1.2 GB fp16)
  - `checkpoints/dinov2-b/mode-gmm-25k.pt` (~1.2 GB fp16)
  - `checkpoints/dinov2-b/uncond-gmm-100k.pt` (~1.2 GB fp16) — 80 epochs
  - `checkpoints/dinov2-b/mode-gmm-100k.pt` (~1.2 GB fp16) — 80 epochs
  - plus 6 SigLIP2-B + MAE-B variants
- **AutoGuidance guide models (DiT-S)**:
  - `checkpoints/autoguidance/dit-s-uncond-gmm-25k.pt`
  - `checkpoints/autoguidance/dit-s-mode-gmm-25k.pt`
- **RAE decoders (frozen ViT-XL)**:
  - `decoders/{dinov2-b,siglip2-b,mae-b}/ViTXL_n08/model.pt`
- **GMM components**: 6 `.pkl` files under `gmm/{dinov2-b,mae-b,siglip2-b}/`
- **Normalization stats**: `normalization_stats/{dinov2-b,mae-b,siglip2-b}/stat.pt`
- **FID reference**: `fid_reference/VIRTUAL_imagenet256_labeled.npz`

Total repo storage: 160 552 674 001 bytes (~160 GB); cherry-pick strategy
cuts to ≈5 GB.

### 2.4 Environment fragility

Per the published README (`uv sync`):

- Python 3.10+ (managed by `uv`)
- PyTorch ≥ 2.1
- `einops`, `diffusers` (for RAE decoder wrapper)
- `transformers` (for DINOv2-B encoder)
- No flash-attn hard requirement at inference
- 8 GPU recommended for FID-50K; single-GPU OK for inference validation
  (~20 GB VRAM for DiT-XL/2 bf16)

## 3. Options comparison

| Option | Cost | Risk | Likelihood of success | Saturation fit |
|---|---|---|---|---|
| **A. Author new MMFMAdapter** (full integration) | ~4 hours (1600-line adapter + 30+ tests + PLUG_IN doc) + ~2 hours GPU validation on 5090 + ~5 GB ckpt download | LOW–MEDIUM — DiT-XL/2 well-understood; RAE decoder + AutoGuidance are paper-specific but well-documented in repo | HIGH — known shape, working upstream sampling code, clear forward signature | ImageNet-256 FID 2.78 vs SiT baseline ~1.96 — ΔFID ≈ 0.82 (NOT in saturation; framework value surface has room) |
| **B. Skip MM-FM** (low-priority) | 0 hours | LOW (Kanzi + FreqFlow cover PHASE-4) | HIGH — PHASE-4 acceptance already met for protein + image via Kanzi + FreqFlow | n/a |
| **C. FlowMol3 v2 latent-space proxy** | ~2 hours (FlowMol3 v2 already has RAE-like decoder; re-target MM-FM via latent-only path) | HIGH — FlowMol3 v2 is molecular latent; MM-FM is image latent; the two latent spaces are not interchangeable | LOW — semantic mismatch defeats the purpose | n/a |

## 4. Recommendation: option B (skip), with option A as a documented follow-up

Given that:

- PHASE-4 is already accepted for **Kanzi** (protein, Wave 21 ready) and
  **FreqFlow** (image SiT-XL/2, Wave 21 ready) — the two primary PHASE-3
  deliverables the framework was designed to validate
- LineageFlow (protein, ICML 2026) ships a synthetic-shim integration that
  can be upgraded to real-ckpt via a 5-line SamplerConfig stub (see
  companion investigation `lineageflow-upstream-investigation.md`)
- MM-FM has been attempted twice (Wave 21 + Wave 21.5) and stalled both
  times with the same agent shape
- The framework capability gate G.4 (generalization breadth, HARD) requires
  ≥ 3 model families — Kanzi (protein) + FreqFlow (image) + LineageFlow
  (protein) already cover 2 protein + 1 image family

the most pragmatic path is **option B**: classify MM-FM as
**low-priority / deferred**, document the deferral, and reserve option A
for a future wave where a different agent shape (smaller scope, perhaps a
single-file diff-against-FreqFlow pattern since both are DiT-class image
generators) can deliver the adapter without the scope creep that stalled
Wave 21/21.5.

### 4.1 Why option A stalled (root-cause hypothesis)

The Wave 21 + Wave 21.5 stalls both followed the same shape:

1. Cherry-pick from a 160 GB HF repo (large download, potential
   timeouts)
2. Author a 1500+ line adapter with 8-method Protocol surface
3. Wire 30+ conformance tests
4. Integrate RAE decoder as a post-velocity hook
5. Integrate AutoGuidance as a conditional velocity-blend

The combinatorial size of this deliverable (multi-thousand lines across
multiple distinct concerns: DiT backbone, RAE decoder, GMM sampling,
AutoGuidance, FID eval) is the most likely failure mode — each
sub-concern has its own failure surface and the agent runs out of
context budget before completing all of them.

### 4.2 If option A is retried in a future wave

Recommended scope split:

1. **Sub-agent 1**: `mm_fm_backbone.py` — pure DiT-XL/2 forward
   (port `stage2/models/DDT/DiTwDDTHead.py` standalone, ~600 LOC)
2. **Sub-agent 2**: `mm_fm_rae.py` — RAE decoder wrapper
   (port `stage1/RAE.py` standalone + `decoders/<encoder>/ViTXL_n08/`
   loader, ~400 LOC)
3. **Sub-agent 3**: `mm_fm_sampler.py` — Euler/Heun ODE loop with GMM
   source + AutoGuidance wrapper, ~300 LOC
4. **Sub-agent 4**: `mm_fm_adapter.py` — Protocol surface that composes
   1+2+3 + 30 tests, ~700 LOC

Total ≈ 2000 LOC across 4 files; each sub-agent's scope is bounded and
has a clear PASS/FAIL criterion. The Wave 21 stall pattern of "one
agent does everything" is the anti-pattern to avoid.

## 5. Verification commands

```bash
# Check whether MM-FM source is reachable from sandbox (Wave 36 finding)
curl -sIL https://github.com/GaoxiangLuo/MM-FM | head -3
# → HTTP/2 200 (REACHABLE)

# Check HF Hub (already verified reachable in Wave 9 R2)
hf download luo00042/mm-fm --repo-type model --include "checkpoints/dinov2-b/*.pt"
# → cherry-picks only DiT ckpts (~5 GB total)
```

## 6. Files audited

- `/home/hugo/codes/flowa-multistep-reinference/todo/models/mm-fm.md`
  (143 lines)
- `/home/hugo/codes/flowa-multistep-reinference/todo/PHASE-4-model-integration-iteration.md`
  §"MM-FM (BLOCKED)" (lines 262–271)
- `https://github.com/GaoxiangLuo/MM-FM` (public source — reachable)
- `https://github.com/GaoxiangLuo/MM-FM/tree/main/src` (8 files)
- `https://github.com/GaoxiangLuo/MM-FM/tree/main/src/stage2` (DDT + transport)
- `https://huggingface.co/api/models/luo00042/mm-fm` (file inventory, ~160 GB)
- `https://raw.githubusercontent.com/GaoxiangLuo/MM-FM/main/src/sample.py`
- `https://raw.githubusercontent.com/GaoxiangLuo/MM-FM/main/src/sample_ddp.py`
- `https://raw.githubusercontent.com/GaoxiangLuo/MM-FM/main/configs/stage2/sampling/ImageNet256/DiTDH-XL_DINOv2-B-UNCONDITIONAL.yaml`

## 7. Outcome summary

| Metric | Value |
|---|---|
| `mm_fm_workaround_proposed` | **YES** (option B: skip / defer) |
| `mm_fm_unblock_likelihood` | n/a (skip path) |
| `mm_fm_retriable` | YES (option A, split into 4 sub-agents) |
| `mm_fm_blocker_class` | scope-creep (not technical) |
| `mm_fm_cost_if_retried` | ~4 hours agent + ~2 hours GPU + ~5 GB download |
| `mm_fm_saturation_check` | FID 2.78 vs SiT 1.96 — ΔFID 0.82 (NOT saturated) |
| `mm_fm_capability_gate_contribution` | would add 3rd image-family model (CVPR 2026); currently 2 image + 2 protein (G.4 = 3, already PASS) |

---

**Agent C conclusion:** MM-FM is **technically unblocked** (source
reachable, ckpts reachable, forward signature clear, all deps known) but
**practically deferred** (two stall rounds, scope creep, Kanzi +
FreqFlow + LineageFlow already cover PHASE-4 acceptance). The
recommended path is option B (skip + document). A future wave can
retake option A with the proposed 4-sub-agent scope split.
