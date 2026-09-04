# MM-FM — CVPR 2026 (image)

**Status:** pending
**Wave:** candidate (Phase 2 analysis only — not yet integrated)
**Last updated:** 2026-09-05
**GitHub:** https://github.com/GaoxiangLuo/MM-FM
**HF:** https://huggingface.co/luo00042/mm-fm

---

## A. Identification

- **arxiv_id:** (CVF Open Access pp. 23260–23271; CVPR 2026
  image_generation track — arxiv_id TBD, will surface via
  `mm-flow.github.io` project page)
- **Title:** *Flow Matching for Multimodal Distributions*
- **Authors:** Gaoxiang Luo, Frank Cole, ..., Lu, Sun (Univ. of Minnesota)
- **Year:** 2026, CVPR 2026
- **Domain:** image, class-conditional ImageNet-256 generation
  (specifically: multimodal target distributions — mixtures of low-density
  modes — which classical FM struggles to cover)
- **Weights URL:** `https://huggingface.co/luo00042/mm-fm`
- **Weights files:**
  - DiT-XL/2 ckpts: `uncond-gmm` / `mode-gmm` (≈2.7 GB fp16 each)
  - Trained GMMs (Gaussian mixture components for the synthetic eval set)
  - Pretrained RAE decoder (Representation Auto-Encoder — analogous to
    a VAE but trained with a different reconstruction objective)
  - Norm stats, FID reference batch
  - **Full repo: ≈160 GB total** (per-checkpoint download 2–5 GB)
- **License:** TBD (academic, Univ. of Minnesota; check HF model card)

## B. Intrinsic model complexity

- **Params:** DiT-XL/2 backbone ≈675 M + small GMM-mode-selector head
  (≈few M)
- **Architecture:** DiT-XL/2 (Peebles' 2023 DiT, 28 layers, hidden=1152,
  16 heads) operating on latents produced by a **Representation
  Auto-Encoder (RAE)** — analogous to a VAE but trained with a
  representation-learning objective that better preserves multimodal
  structure. Plus a GMM-mode-selector that picks which mode(s) of the
  target mixture to sample from.
- **Inference FLOPs:** ≈0.4 TFLOPs/sample at 256×256 (standard DiT-XL/2);
  50 NFE Euler ~20 TFLOPs/sample.
- **Training compute:** paper uses 80 epochs on 8× A100 80GB for the GMM
  experiments + standard ImageNet-256 training for the DiT ckpts
  (≈1,000–2,000 GPU-days aggregate, paper-reported).
- **Dataset:**
  - Synthetic GMM toy (for multimodal FM validation)
  - ImageNet-256 (1.28 M train images, for real-image FID)
- **Reported metric:**
  - Uncond-GMM: FID 3.82 in 80 epochs
  - **AutoGuidance: FID 2.74 on ImageNet-256** (SOTA at submission time,
    pre-FreqFlow 1.38)

## C. Integration difficulty

| Item | Status | Notes |
|---|---|---|
| Architecture family | ✅ understood | DiT-XL/2 — already supported by our framework (`flowmol3_v2_adapter` analogue) |
| Weight format | ✅ HF Hub | `luo00042/mm-fm` is publicly listed; per-checkpoint 2–5 GB |
| Repo size | 🔴 **large** | full HF repo is **160 GB** (FID reference batch + RAE decoder + multiple ckpts); need to cherry-pick only the 2 DiT ckpts (~5 GB total) |
| Environment deps | ✅ minimal | PyTorch + einops + diffusers (for RAE decoder); no flash-attn hard requirement at inference |
| Inference API | ✅ clear | DiT-style `forward(x_t, t, y)` → velocity; AutoGuidance is an extra hook that combines two velocity predictions |
| RAE decoder | 🟡 novel | the "Representation Auto-Encoder" is the paper's contribution; framework must wrap it as a `decode(latents) → image` adapter hook |
| AutoGuidance head | 🟡 novel | the paper's "mode-gmm" ckpt is used at inference to bias the velocity toward a specific mode; needs a new glue hook |
| Paper-claim reproduction | 🟡 partial | FID 2.74 needs full ImageNet-256 eval set; AutoGuidance needs both ckpts loaded |

## D. Risk profile

- **License:** TBD — must check HF model card. Univ. of Minnesota
  academic; likely research-only.
- **Environment fragility:** LOW–MEDIUM — DiT-XL/2 is well-known but the
  RAE decoder and AutoGuidance head are paper-specific and need exact
  config files from the upstream repo.
- **Paper-axis gaps:** moderate — paper uses 250-NFE Euler by default for
  AutoGuidance; our framework's default 50-NFE Heun may diverge. The
  AutoGuidance mode-selector assumes a specific GMM fit that the paper
  ships with the ckpt, but its exact sampling schedule must be mirrored.
- **Network reachability:** ⚠️ HF `luo00042/mm-fm` is reachable (per
  Wave 9 R2 head verification via indexed search); `github.com`
  `GaoxiangLuo/MM-FM` blocked from sandbox.
- **Saturation check (LL-002):** at paper FID 2.74 vs SiT-XL/2 baseline
  ~1.96–2.0, we are NOT in saturation territory (ΔFID ≥ 0.7) — framework
  comparison has room to demonstrate improvement, but beating both paper
  AND framework in the same direction requires careful setup.

## E. Framework-fit score

| Score | Value | Rationale |
|---|---|---|
| intrinsic_complexity_score | 5/10 | 675M DiT-XL/2 + small GMM head — same middleweight tier as FreqFlow |
| integration_difficulty_score | 6/10 | DiT-XL/2 is known; RAE decoder + AutoGuidance are novel glue; HF repo 160 GB requires cherry-pick |
| claim-reproduction_cost | 7/10 | FID 2.74 needs full ImageNet-256 eval; AutoGuidance requires both ckpts + GMM stats |
| **combined_score** | **30/100** | (5 × 6 = 30; integration_difficulty only per spec) |

### JMAA theorem coverage (LL-001 / LL-002)

- **Theorem 1 (F-side):** DiT-XL/2 velocity field is **continuous-time ODE**
  v_θ(x_t, t); AutoGuidance adds an additive correction term that
  preserves continuity. F-side hypothesis
  `uniform_simplicity` should hold (DiT is well-behaved).
- **Lemma 2 (sheet tube):** DiT-XL/2 attention is piecewise-smooth on
  standard inputs; GMM-mode-selector adds a discrete mode index but does
  not introduce a discontinuous jump in the velocity field at the ODE
  trajectory level.
- **Proposition 6 (escaping-sharpness):** the central MM-FM claim is that
  FM on multimodal distributions escapes sharpness via the GMM-mode
  selector — directly applicable. `validate_g_admissible` should pass.
- **Saturation check (LL-002):** ΔFID vs SiT baseline ≥ 0.7, so
  saturation is NOT a concern here; framework improvement has clear
  room to surface.

## F. Empirical record

| | Result |
|---|---|
| Wave 9 R2 research | ✅ cataloged (CVPR 2026, DiT-XL/2, FID 2.74 AutoGuidance) |
| Wave 9 R2 recommendation | "Runner-up to Flowception"; "most drop-in CVPR 2026 addition" |
| Wave 9/10/11/12/13/14/15/16/17/18 follow-ups | not yet attempted |
| Adapter file | does not exist (`adaptive_reflow/adapters/mm_fm_adapter.py`) |
| Conformance battery | not run |
| Reproduce path | unblocked; ckpt URLs known, 5 GB cherry-pick |

## G. Next action

1. **Cherry-pick 2 DiT ckpts** from `luo00042/mm-fm` — do NOT download the
   full 160 GB repo; pull only `uncond-gmm` + `mode-gmm` (~5 GB total) +
   the GMM stats + RAE decoder config files.
2. **Author `MMFMAdapter`** — subclass the DiT-template adapter; add the
   RAE decoder wrapper as a post-velocity hook; add AutoGuidance as a
   conditional velocity-blend when both ckpts are loaded.
3. **Run D.5 conformance battery** — verify 8/8 checks pass with synthetic
   velocity before any real-ckpt load.
4. **Phase-4 comparison** — baseline 250-NFE Euler AutoGuidance vs
   framework 50-NFE Heun AutoGuidance on ImageNet-256 N=5000, k=5 subset
   CIs. Saturation check: should NOT trigger (ΔFID vs SiT ≥ 0.7).

## See also

- `../PHASE-2-model-complexity-analysis.md` (parent phase)
- `../PHASE-4-model-integration-iteration.md` (Phase 4 acceptance metric
  table: MM-FM → FID ≥ +0.1 OR ≥ +5% relative; TIE if FID < 3.0)
- `../lessons-learned.md` (LL-001, LL-002)
- `../EXECUTION-PLAN.md` (Phase 2 candidate list)
- Wave 9 R2 research: `/tmp/wave9_sota_fm/R2-cvpr2026/diagnose.md`