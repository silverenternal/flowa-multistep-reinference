# Model Card — self_flow (SelfFlowAdapter)

**Schema:** Mitchell/Gebru, 8 required fields (F.4 metric).
**Adapter key:** `self_flow`
**Card status:** COMPLETE (8/8 fields populated; production torch-mode
is a design-skeleton release gated on user-supplied ckpt + CUDA host;
synthetic-mode Protocol surface is fully wired and tested).
**Last updated:** 2026-09-05.
**F.4 gate:** PASS (≥ 0.8 per-model target met).

---

## 1. Intended Use

- **Primary use.** Wire the published Self-Flow latent FM model
  (Hila et al. 2026, ICML 2026, `arXiv:2603.06507`) into the
  framework's `FlowMatchingODEAdapter` Protocol so the same
  algorithm-layer code that drives 2D FM and CIFAR-10 RF also
  drives a SiT-XL/2 self-supervised flow matching backbone on
  ImageNet-256 latents. Validates the "any FM model, when
  integrated into the framework, improves" claim as the **first**
  SOTA 2026 model integrated (image axis).
- **Primary users.** Framework algorithm-layer developers; paper
  authors writing the `docs/paper-draft.md` §4 SOTA-image record;
  users running `tools/run_sota_self_flow_experiment.py` (currently
  a stub returning `75` `EX_TEMPFAIL`).
- **Out-of-scope uses.** Other image resolutions (ImageNet-512,
  CIFAR-100), non-image modalities, downstream fine-tuning, or any
  production deployment. The adapter is gated on a CUDA host with
  enough HBM for the 680 M parameter fp32 weights (~2.7 GB) plus
  the trajectory buffer.
- **Decision-support / safety.** Not a decision-support model. The
  adapter generates 256×256 RGB images for a published FID
  reproduction; it is not a safety-relevant system.

## 2. Training Data

- **Source.** ImageNet-1k (Russakovsky et al. 2015, ILSVRC). 1.28 M
  training images, 50 000 validation images, 1000 classes. Encoded
  via DC-AE / SD-VAE to a `(4, 32, 32)` float32 latent (32× downsample
  from 256×256 RGB).
- **Size.** 1.28 M train / 50 000 val; 1000 classes + 1 unconditional
  token (1001-dim `y_embedder.embedding_table.weight`).
- **Pre-processing.** Standard ImageNet preprocessing (resize +
  center-crop 256×256 → DC-AE encode → `(4, 32, 32)` float32 latent).
- **Train / val / test split.** ImageNet-1k canonical train / val
  partition; the published checkpoint uses ImageNet-256
  (downsampled) per Hila et al. 2026.
- **Provenance.** The adapter does not retrain — it consumes the
  published `selfflow_imagenet256.pt` checkpoint from
  `huggingface.co/Hila/Self-Flow`. The published training protocol
  uses ~50× fewer training steps than vanilla flow matching
  (paper Table 1).

## 3. Evaluation Data

- **Held-out reference.** ImageNet-256 validation set (50 000
  images), encoded to `(4, 32, 32)` latents; FID-50K against the
  paper's published reference batch.
- **Evaluator.** Standard FID-50K (Heusel et al. 2017) against
  InceptionV3 features, computed on the 50 000 generated latents
  decoded back to 256×256 RGB. Same evaluator for baseline +
  framework, matched-NFE.
- **Sample budget.** 50 000 samples for the headline FID-50K
  reproduction; smaller budgets (1 000-5 000) for the ablation.
- **Why this is the right eval.** FID-50K is the canonical metric
  for ImageNet-256 generation and matches the published Self-Flow
  headline number (FID 5.70 per the paper).
- **Note:** the InceptionV3 features must be produced on the same
  InceptionV3 weights + preprocessing as the user's reference
  batch; the 3-channel 299×299 RGB normalisation is the canonical
  FID pipeline.

## 4. Quantitative Analyses

| Metric | Baseline (Self-Flow 1-pass, 50 NFE, CFG 1.0) | Framework (4 schedulers, matched NFE) | Δ | Source |
|---|---:|---:|---:|---|
| Published FID-50K (ImageNet-256) | 5.70 | n/a (paper's 1-pass baseline) | reference | paper Table 1 |
| Adapter synthetic-mode W2 / Protocol coverage | byte-stable | n/a | placeholder | `tests/test_adapters/test_self_flow.py` 22/22 pass |
| Framework vs baseline (real ckpt) | TBD | TBD | TBD | **PENDING** user-side ckpt + CUDA host |

Honest framing (per `docs/PLUG_IN_YOUR_MODEL.md` §Self-Flow): the
production torch-mode FID numbers **cannot be measured in this
sandbox** — the 1.4 GB `selfflow_imagenet256.pt` checkpoint is not
present and a CUDA host is not available. The synthetic-mode
Protocol surface is fully wired (22 tests pass) so the head-line
`+0% to +5%` framework uplift on ImageNet-256 is a **claim
prediction**, not an empirical result. The harness stub
`tools/run_sota_self_flow_experiment.py` returns `75`
`EX_TEMPFAIL` until the ckpt + FID pipeline are available.

## 5. Ethical Considerations

- **Dataset ethics.** ImageNet-1k has documented demographic and
  representation biases (Shankar et al. 2017, Stock & Cisse 2018).
  The adapter consumes the published checkpoint trained on this
  data; downstream users should be aware that 1000-class
  ImageNet inherits these biases.
- **No PII.** ImageNet has been audited for faces / names;
  generated images are 256×256 RGB and cannot resolve identity.
- **Dual-use risk.** Moderate. Self-Flow generates 256×256 RGB
  images at a resolution where image synthesis can produce
  deceptive content. Downstream use should consider content
  provenance and disclosure (e.g. C2PA).
- **Environmental cost.** GPU-bound. Published Self-Flow protocol
  on RTX-class GPU is reported at ≈ 1-2 days for FID-50K + 20-round
  ablation. The framework-side wall-clock budget is comparable.
- **Bias / fairness.** The 1000-class ImageNet labels are not
  demographically protected categories; bias axes are object-level
  (e.g. wedding vs funeral asymmetry in event classes). Downstream
  use should not deploy the model as a fairness-relevant system.
- **Mitigations.** Class-label cache is preserved across rounds so
  re-inference does not re-encode (a small efficiency win, not a
  bias mitigation). Generated images should be watermarked or
  provenance-marked before any external distribution.

## 6. Caveats

- **Production torch-mode gated** on:
  1. `selfflow_imagenet256.pt` (1.4 GB published checkpoint) —
     not present in this sandbox.
  2. CUDA host with ≥ 32 GB HBM (680 M fp32 params + trajectory
     buffer).
  3. InceptionV3 FID pipeline + reference batch.
  None of the three are available; the synthetic-mode Protocol
  surface is the only forward path that runs today.
- **Synthetic-mode is not a baseline reproduction.** When torch is
  missing or the weights file is absent, the adapter falls back to
  a deterministic NumPy latent velocity field (`random_init=True`).
  The synthetic path produces a well-formed but **non-trained** FM
  model so the Protocol conformance tests can run without the heavy
  dependency. **Synthetic-mode results must NOT be cited as
  baseline reproductions of Self-Flow.**
- **Harness stub.** `tools/run_sota_self_flow_experiment.py` exits
  with `75` `EX_TEMPFAIL`. The full harness depends on the
  reference batch + CUDA host + InceptionV3 FID pipeline.
- **CFG 1.0 only.** The published Self-Flow checkpoint is
  guidance-distilled, so CFG 1.0 is the default. Higher CFG values
  are not supported.
- **D.5 auto-battery result:** 8/8 conformance checks pass;
  22/22 hand-written tests pass (`baseline-audit-report.md`
  §D.3 row `test_self_flow`).
- **No new claims.** This card documents an existing adapter
  under the Mitchell/Gebru schema; it does not introduce new
  empirical results.

## 7. Paper-Equation Provenance

- **Primary paper:** Hila et al. (2026). *Self-Flow: Self-Supervised
  Flow Matching for Scalable Multi-Modal Synthesis*. ICML 2026,
  `arXiv:2603.06507`. Integrated via `SelfFlowAdapter` in
  `adaptive_reflow/adapters/self_flow.py`.
- **Equations used:**
  - Linear interpolation `X_t = (1 − t) X_0 + t X_1` (Self-Flow
    §3.1).
  - Latent flow matching with MSE between predicted and target
    velocity fields (Self-Flow §3.2).
  - Per-token dual-timestep scheme (Self-Flow §4, central
    innovation).
  - EMA teacher-student (Self-Flow §3.3).
  - SiT adaLN class embedding (1001-dim `y_embedder`).
- **Architecture:** SiT-XL/2 (28-block DiT, adaLN-zero modulation,
  1152 hidden, 16-head attention) at the `/2` patch resolution.
  296 tensors, ~680 M parameters.
- **Framework theorems instantiated:**
  - **Theorem 1** (selection ratio) — `EvidenceScaleGapMetric`.
  - **Proposition 3** (selection mechanism) — `BoundedMergeOperator`.
  - **Theorem 1 rate bound** — `adaptive_reflow/theory/rate_bound.py`.
- **Cross-references:**
  `docs/paper-draft.md` §4,
  `docs/PLUG_IN_YOUR_MODEL.md` §Self-Flow,
  `docs/CONSOLIDATED_RESULTS.md` §2,
  `docs/CLAIMS.md` (Self-Flow claim ledger entry pending Wave 9).

## 8. Known Failure Modes

- **Saturation regime.** Self-Flow's headline FID 5.70 is near the
  saturation regime relative to SiT baseline FID ~2.0; the
  framework's value-add may not be observable at this saturation
  (per `docs/lessons-learned.md` LL-002). Saturation check is
  needed before any framework uplift claim is published.
- **CFG-distilled checkpoint.** The published ckpt is
  guidance-distilled; CFG > 1.0 is not supported and re-enabling
  CFG would require an un-distilled checkpoint.
- **Per-token dual-timestep schema.** The published checkpoint
  uses a per-token dual-timestep scheme (Self-Flow §4, central
  innovation); the adapter does not need the projector for
  Protocol-surface exercise but a real framework-vs-baseline
  comparison must route the per-token timesteps through the engine.
- **Single-channel latent.** `state_shape=(4, 32, 32)` is the
  only exposed channel; `image_latent` (latent domain). No
  text-encoder side-channel; class-label only.
- **D.5 conformance battery edge case.** The
  `solve_ode` step assembly can drift on the synthetic-mode path
  if `num_steps` exceeds 100; the adapter clamps and returns the
  endpoint, which is documented behaviour but may obscure a real
  divergence.
- **No ImageNet-512 / ImageNet-64.** The adapter is hard-coded to
  the ImageNet-256 latent shape; ImageNet-512 would require a
  new checkpoint + new state-shape registration.

---

**See also:** `adaptive_reflow/adapters/self_flow.py`,
`docs/PLUG_IN_YOUR_MODEL.md` §Self-Flow,
`docs/CONSOLIDATED_RESULTS.md` §2,
`tools/run_sota_self_flow_experiment.py` (stub),
`tests/test_adapters/test_self_flow.py` (22/22 pass).
