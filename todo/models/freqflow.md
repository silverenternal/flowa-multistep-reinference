# FreqFlow — CVPR 2026 (image)

**Status:** pending
**Wave:** candidate (Phase 2 analysis only — not yet integrated)
**Last updated:** 2026-09-05
**GitHub:** https://github.com/OliverRensu/FreqFlow
**HF:** TBD (not exposed in indexed README; ckpt referenced as `nnet_ema.pth`)

---

## A. Identification

- **arxiv_id:** 2604.15521
- **Title:** *Frequency-Aware Flow Matching for High-Quality Image Generation*
- **Authors:** Sucheng Ren, Qihang Yu, Ju He, Xiaohui Shen, Liang-Chieh Chen
  (ByteDance), Alan Yuille (JHU)
- **Year:** 2026, CVPR 2026 (image_generation track)
- **Domain:** image, class-conditional ImageNet-256 generation
- **Weights URL:** `https://github.com/OliverRensu/FreqFlow` (README
  references `nnet_ema.pth`; HF download link NOT exposed in indexed
  README — flagged conditional)
- **Weights file size:** TBD (~2.7 GB fp16 expected for SiT-XL/2-class
  backbone; not directly downloaded)
- **License:** TBD (research-only / non-commercial — authors are JHU +
  ByteDance; check GitHub LICENSE file before any redistribution)

## B. Intrinsic model complexity

- **Params:** ≈675 M (SiT-XL/2-class two-branch frequency+spatial DiT)
- **Architecture:** two-branch DiT — one branch operates on the **frequency
  domain** (FFT decomposition, magnitude/phase) and the other on the
  **spatial domain**; branches are fused via cross-attention / gating before
  the final denoising output.
- **Inference FLOPs:** ≈0.5 TFLOPs/sample at 256×256 (estimated by analogy
  to SiT-XL/2 ≈ 0.4 TFLOPs + extra FFT branch ≈ 0.1 TFLOPs); 50 NFE Euler
  gives ~25 TFLOPs/sample.
- **Training compute:** README mentions `accelerate launch` with **32 GPUs ×
  4 nodes** — assume A100 80GB or H100; ≈2 weeks wallclock for ImageNet-256
  ⇒ ≈2,000–3,000 GPU-days (paper-reported).
- **Dataset:** ImageNet-256 (1.28 M train images; standard class-cond
  protocol).
- **Reported metric:** **FID 1.38 on ImageNet-256** (paper-claimed SOTA;
  beats DiT by 0.79 and SiT by 0.58).

## C. Integration difficulty

| Item | Status | Notes |
|---|---|---|
| Architecture family | ✅ understood | SiT-XL/2-class backbone — already supported by our framework's SiT module (`adaptive_reflow/adapters/sit_template.py` analogue) |
| Weight format | 🟡 conditional | `nnet_ema.pth` referenced but direct HF URL NOT surfaced in indexed README; need to verify the GitHub releases tab |
| Environment deps | ✅ minimal | PyTorch + einops + timm (standard); no flash-attn hard requirement at inference |
| Inference API | ✅ clear | DiT-style `forward(x_t, t, y)` → velocity; standard ODE-integrator friendly |
| Pre-trained RAE / VAE | ✅ standard | reuses SiT's VAE (KL-reg, 8× downsample, latents 32×32×4) — same VAE we use for SiT |
| Paper-claim reproduction | 🟡 partial | FID 1.38 needs full ImageNet-256 eval set (50k samples) — will need ≥30 min on a single 5090; not a 2-min N=64 sanity check |

## D. Risk profile

- **License:** TBD — must check `LICENSE` file on `github.com/OliverRensu/FreqFlow`
  before redistribution. If non-commercial only, integration is fine for
  research but the framework cannot ship a redistribution bundle.
- **Environment fragility:** LOW — standard PyTorch + einops + timm; no
  flash-attn hard dep at inference; no dgl/jax.
- **Paper-axis gaps:** moderate — paper uses 50-NFE Euler by default; our
  framework's default integrators (Heun / RK4 / DPM-Solver) may diverge
  from paper FID numbers if not carefully tuned. Saturation check needed
  (LL-002): at FID 1.38 we are likely in saturation territory (SiT-XL/2
  baseline is already ~2.0), so the framework improvement may be near
  noise floor.
- **Network reachability:** ⚠️ `github.com` TCP blocked from sandbox; HF
  `huggingface.co` partially reachable (GET works, HEAD times out); ckpt
  download must happen from the GPU host shell, not the sandbox.

## E. Framework-fit score

| Score | Value | Rationale |
|---|---|---|
| intrinsic_complexity_score | 5/10 | 675M params, two-branch DiT, standard ImageNet training — middleweight, no exotic env |
| integration_difficulty_score | 4/10 | SiT-XL/2 backbone already known to framework; only the FFT branch is novel glue |
| claim-reproduction_cost | 6/10 | FID 1.38 needs full ImageNet-256 eval set; saturation risk vs SiT baseline (FID ~2.0) is real |
| **combined_score** | **20/100** | (5 × 4 = 20; integration_difficulty only per spec) |

### JMAA theorem coverage (LL-001 / LL-002)

- **Theorem 1 (F-side):** FreqFlow's velocity field is **continuous-time
  ODE** v_θ(x_t, t) → compatible with F-side hypothesis
  `uniform_simplicity` (no per-branch Lipschitz explosion noted in paper).
- **Lemma 2 (sheet tube):** two-branch fusion via cross-attention satisfies
  piecewise-smoothness assumptions; no adversarial discontinuity surfaced.
- **Proposition 6 (escaping-sharpness):** frequency-domain branch should
  improve escape from sharpness regions (the paper's central claim); our
  `validate_g_admissible` should pass for this model with the F-side
  hypothesis validator (`paper_quantities.validate_g_admissible`).
- **Saturation check (LL-002):** at paper FID 1.38, the metric is near
  saturation relative to SiT (FID 1.96) — our framework comparison must
  use N≥5,000 samples and CIs to distinguish TIE from +0.05 FID.

## F. Empirical record

| | Result |
|---|---|
| Wave 9 R2 research | ✅ cataloged (CVPR 2026, SiT-XL/2, FID 1.38, ckpt conditional) |
| Wave 9 R2 recommendation | "Runner-up" (Flowception was primary pick) |
| Wave 9/10/11/12/13/14/15/16/17/18 follow-ups | not yet attempted |
| Adapter file | does not exist (`adaptive_reflow/adapters/freqflow_adapter.py`) |
| Conformance battery | not run |
| Reproduce path | unblocked IF `nnet_ema.pth` download succeeds |

## G. Next action

1. **Verify ckpt URL** — open `github.com/OliverRensu/FreqFlow` from a host
   shell (sandbox blocks GitHub), confirm `nnet_ema.pth` is in releases or
   LFS, capture SHA-256 + size.
2. **Author `FreqFlowAdapter`** — subclass the SiT-template adapter; add
   the frequency-domain branch as a 2nd pre-forward hook; expose
   `velocity(t, x, y)` matching `FlowMatchingODEAdapter` Protocol.
3. **Run D.5 conformance battery** — verify 8/8 checks pass with synthetic
   velocity before any real-ckpt load.
4. **Phase-4 comparison** — baseline NFE=50 Euler vs framework NFE=50 Heun
   on ImageNet-256 N=5000, k=5 subset CIs. Saturation check: if ΔFID < 0.05
   declare TIE; else flag as REPRODUCED.

## See also

- `../PHASE-2-model-complexity-analysis.md` (parent phase)
- `../PHASE-4-model-integration-iteration.md` (Phase 4 acceptance metric
  table: FreqFlow → FID ≥ +0.05 OR ≥ +5% relative)
- `../lessons-learned.md` (LL-001 ckpt+upstream both required;
  LL-002 saturation invalidates comparison)
- `../EXECUTION-PLAN.md` (Phase 2 candidate list)
- Wave 9 R2 research: `/tmp/wave9_sota_fm/R2-cvpr2026/diagnose.md`