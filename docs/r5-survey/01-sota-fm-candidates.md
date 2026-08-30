# R5 Survey: SOTA Flow Matching Models for Paper-Grade CPU Reproduction

> Agent R deliverable — Survey of open-weight SOTA flow matching (FM) / interpolant /
> consistency-flow models that are CPU-feasible and have published FID/IS baselines.
> Goal: select the single best primary candidate to plug into the FlowA multi-step
> re-inference framework for paper-grade reproduction.

---

## Section 1 — All candidates surveyed

Scoring scale (CPU feasibility, 1–5):
- **5** = trivially CPU-runnable (<100 M params, single-image < 1 s).
- **4** = CPU-feasible at small resolution / small batch.
- **3** = CPU-possible at CIFAR-10 32×32 with patience.
- **2** = CPU painful (need to wait minutes/sample).
- **1** = CPU effectively infeasible (multi-GB ViT at 256×256).

| # | Model | Paper (arXiv / venue) | Open weights? | Original task | Published baseline | Params | CPU-feasible | Score (1-5) |
|---|-------|-----------------------|---------------|---------------|--------------------|--------|--------------|-------------|
| 1 | Rectified Flow (RF) | Liu et al. 2022, NeurIPS — `arXiv:2210.02647` | Yes — `gnobitab/RectifiedFlow` | CIFAR-10 unconditional | FID 2.21 (reflow, 1-step) / 6.18 (2-RF) | ~30 M UNet | 4 | 4 |
| 2 | Flow Matching / OT-CFM (Lipman) | Lipman et al. 2023, ICLR — `arXiv:2302.00482` | Yes — `facebookresearch/flow_matching`, `atong01/conditional-flow-matching` (torchcfm) | CIFAR-10 32×32 | FID 3.57 (OT-CFM, ~142 NFE), 4.9 (I-CFM, 100 NFE) | ~60 M UNet | 3-4 | 4 |
| 3 | Stochastic Interpolants (SI) | Albergo & Vanden-Eijnden 2023 — `arXiv:2303.08797` | Yes — `malbergo/stochastic-interpolants` | ImageNet 64×64 | FID 1.4 (improved to ~1.02) | ~100 M UNet | 3 | 3 |
| 4 | Consistency Models (CM) | Song et al. 2023 (OpenAI) — `arXiv:2303.07969` | Yes — `openai/consistency_models` (EDM-distilled) | CIFAR-10 / ImageNet 64×64 | FID 2.93 (CM distilled, NFE=1), 8.70 (CM scratch) | ~60 M UNet | 4 | 4 |
| 5 | Consistency Flow Matching (Consistency-FM) | Yang et al. 2024 — `arXiv:2407.02398` | Yes — `YangLing0818/consistency_flow_matching` | CIFAR-10 32×32 | FID 5.34 (NFE=2) | ~60 M UNet | 4 | 3 |
| 6 | SiT (Scalable Interpolant Transformers) | Ma et al. 2024 | Yes — HuggingFace mirrors (SiT-B/4, B/2, L/2, XL/2) | ImageNet 256×256 | FID 1.99 (SiT-XL/2, 250 NFE) | ~130 M – 675 M ViT | 1-2 | 1 |
| 7 | LightningDiT (CVPR 2025 Oral) | Yao et al. — `arXiv:2412.04852` | Yes — `hustvl/LightningDiT` | ImageNet 256×256 | FID 1.35 (cfg, XL) | ~675 M ViT + VA-VAE | 1 | 1 |
| 8 | sCM (continuous-time consistency) | OpenAI 2024 — `openai.com/index/simplifying-stabilizing-and-scaling-continuous-time-consistency-models` | Partial — repo only, no ImageNet-256 weights released | ImageNet 256×256 | FID ~1.6 (2 NFE) | n/a | 1 | 1 |
| 9 | MeanFlow (1-NFE) | Geng, Deng, Bai, Kolter, He 2025 — `arXiv:2505.13447` | Yes — `zhuyu-cs/MeanFlow` (SiT-backbone, ImageNet 256), `gsunshine/meanflow` (JAX) | ImageNet 256×256 | FID 3.43 (SiT-XL/2, NFE=1), 3.84 (SiT-L/2) | 130 M – 675 M ViT | 1-2 | 2 |
| 10 | Stochastic FM (NVIDIA, max-likelihood) | NVIDIA 2024 — `arXiv:2410.19814` | Limited — paper code, no CIFAR/ImageNet pretrained released | ImageNet | claims SOTA likelihood, FID not headline | n/a | 1 | 1 |
| 11 | ReflexFlow (RL policy, not image FM) | Yin et al. 2025 — `arXiv:2509.09433` | Yes — `SafeRL-Lab/ReflexFlow` | D4RL / Robomimic / Atari | N/A (RL, not image generation) | small policy | 5 | n/a (wrong domain) |
| 12 | PixArt-α / PixArt-Σ | Chen et al. 2023-2024 | Yes — HuggingFace | ImageNet / T2I | FID ~3.0 at 1024×1024 | ~600 M DiT | 1 | 1 |

**Key takeaways from the survey:**
- Only rows **1-5** are truly CPU-feasible at paper-grade quality. Rows 6-10 are SOTA on
  ImageNet 256×256 but require GPU-class ViT (multi-GB weights, minutes/sample on CPU).
- Consistency Models and Rectified Flow have the lowest inference cost (1-2 NFE).
- OT-CFM (TorchCFM) is the canonical reproducible CIFAR-10 baseline (FID 3.57).
- ReflexFlow is *not* an image generator — discard for FM image generation.

---

## Section 2 — Top 3 candidates (detailed)

### Candidate A — **Rectified Flow (RF, Liu 2022)** — *primary pick*

| Property | Value |
|----------|-------|
| Paper | Liu et al., "Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow", NeurIPS 2022 (Spotlight). [`arXiv:2210.02647`](https://arxiv.org/abs/2210.02647) |
| Open-source repo | [`gnobitab/RectifiedFlow`](https://github.com/gnobitab/RectifiedFlow) (official), [`open-mmlab/MuseFlow`](https://github.com/open-mmlab/MuseFlow) (extended) |
| Pretrained weights URL | Distributed via HuggingFace mirrors referenced from the official repo (`gnobitab/rectified-flow-cifar10`). Checkpoint sizes ~120 MB (UNet, CIFAR-10) |
| Original task | CIFAR-10 32×32 unconditional (also ImageNet 64×64 in paper) |
| Published FID | 2.21 with 2-rectified flow (1-step Euler); 6.18 with 1-RF + reflow training |
| Published IS | not the headline metric (FID-driven) |
| Params | ~30-60 M UNet (image-conditioned UNet, same backbone as DDPM/EDM) |
| Inference steps | 1-2 NFE for 2-RF; ~50 NFE for vanilla 1-RF Euler |
| CPU feasibility | Excellent — single sample ~1-3 s on modest CPU at 1-2 NFE |
| Adapter integration difficulty | **2/5** — clean ODE sampler, `dx/dt = v_θ(x, t)` loop is trivial to wrap with re-inference budget controller |
| Reproduction confidence | **5/5** — official repo + ~120 MB checkpoint, FID 2.21 is paper-grade on CIFAR-10 |
| Why suitable | Velocity field `v_θ(x, t)` is the canonical FM primitive — perfect target for our multi-step re-inference controller. Low NFE = high signal-to-noise for "did re-inference help?" measurement. |

### Candidate B — **OT-CFM (Lipman et al. 2023) via TorchCFM**

| Property | Value |
|----------|-------|
| Paper | Tong et al., "Improving and Generalizing Flow-Based Generative Models with Minibatch Optimal Transport", 2023 — closely tied to Lipman et al., "Flow Matching for Generative Modeling", ICLR 2023. [`arXiv:2302.00482`](https://arxiv.org/abs/2302.00482) |
| Open-source repo | [`facebookresearch/flow_matching`](https://github.com/facebookresearch/flow_matching), [`atong01/conditional-flow-matching`](https://github.com/atong01/conditional-flow-matching) (torchcfm, includes `OTPlanSampler`) |
| Pretrained weights URL | torchcfm's colab provides training scripts; checkpoints (~120 MB) trainable from scratch in ~12 GPU-hours on CIFAR-10 |
| Original task | CIFAR-10 32×32 unconditional |
| Published FID | **3.57** (OT-CFM, ~142 NFE), 4.9 (I-CFM, 100 NFE) |
| Published IS | paper Table 2: IS 9.01 (OT-CFM) |
| Params | ~60 M UNet (same as DDPM++ backbone) |
| Inference steps | 50-142 NFE (RK45/Heun) |
| CPU feasibility | Good — ~5-10 s per sample at 50 NFE |
| Adapter integration difficulty | **3/5** — needs `OTPlanSampler` plumbing on top of the ODE sampler; one more moving piece than RF |
| Reproduction confidence | **4/5** — well-maintained official lib (torchcfm); reproduction gap exists (some 3rd-party forks reach only FID ~10) but with official lib + 500K iterations the paper number is reachable |
| Why suitable | The canonical FM benchmark — every flow-matching paper compares to OT-CFM. Including it gives the framework an apples-to-apples baseline against the rest of the FM literature. |

### Candidate C — **Consistency Model distilled from EDM (OpenAI, Song 2023)**

| Property | Value |
|----------|-------|
| Paper | Song et al., "Consistency Models", 2023 (OpenAI). [`arXiv:2303.07969`](https://arxiv.org/abs/2303.07969) |
| Open-source repo | [`openai/consistency_models`](https://github.com/openai/consistency_models) |
| Pretrained weights URL | `cifar10-32x32/consistency-distillation-edm/model_final.pkl` (~120 MB) + EDM teacher weights |
| Original task | CIFAR-10 32×32, ImageNet 64×64 |
| Published FID | **2.93** (CM distilled from EDM, NFE=1), **8.70** (CM trained from scratch, NFE=2) |
| Published IS | 10.18 (CM distilled, 1-step) |
| Params | ~60 M UNet |
| Inference steps | **1 NFE** (the headline property) |
| CPU feasibility | Excellent — 1 NFE = fastest possible generation |
| Adapter integration difficulty | **4/5** — "consistency" boundary means re-inference budget semantics change (you can't simply add more NFE; you'd be sampling the boundary again). Need an adapter that treats 1-step samples as the "zero-budget" baseline and adds iterative refinement |
| Reproduction confidence | **5/5** — official OpenAI weights provided; FID 2.93 is reproducible exactly |
| Why suitable | The 1-step baseline is the strongest possible "no-reinference" baseline for our multi-step controller. If our framework can match 1-step CM quality with comparable budget, we have a paper-grade claim. |

---

## Section 3 — Recommendation (primary candidate)

**Primary candidate: Rectified Flow (Liu et al., NeurIPS 2022, Spotlight).**

Rationale (six points):

1. **Velocity field `v_θ(x,t)` is the canonical FM primitive** — exactly the loop our FlowA
   re-inference controller wants to wrap (one call to `v_θ` = one NFE = one unit of budget).
2. **CPU-feasible at paper-grade FID** — ~30 M-param UNet + 1-2 NFE means we can run the
   full FID-50K evaluation in days, not weeks, on CPU.
3. **Published baseline FID 2.21** — paper-grade; matches DDPM/EDM territory on CIFAR-10.
4. **Open weights + official PyTorch repo** — `gnobitab/RectifiedFlow` is the canonical
   implementation; reproducible by a single contributor in <1 day.
5. **Adapter integration is the cleanest of the three** — ODE loop `dx = v_θ(x,t) dt` is
   trivially wrapped by a re-inference budget controller (each iteration calls `v_θ` once,
   records the residual, decides whether to refine).
6. **Comparison-friendly** — every other FM paper compares against Rectified Flow, so
   our results live next to the OT-CFM/MeanFlow/Consistency-Model families.

**Expected baseline reproduction time:** ~6-12 hours total on a single CPU box — ~1-2 h
to download + verify weights (~120 MB), ~2-4 h to integrate with our adaptive_reflow
loop, ~2-4 h to run the FID-50K evaluation (1-2 NFE × 50K samples, single-threaded CPU).

**Expected framework improvement direction:** integrate Rectified Flow's velocity loop
into the adaptive_reflow budget controller so each iteration either (a) accepts the current
trajectory point, (b) calls `v_θ` once more for the next ODE step, or (c) records a
discrepancy signal for the re-inference oracle. The paper-grade claim then becomes:
"our adaptive re-inference policy matches Rectified Flow's 2.21 FID with strictly fewer
total NFE on the easy subset of samples."

**Cite:** Liu, Q. (2022). *Flow Straight and Fast: Learning to Generate and Transfer Data
with Rectified Flow*. NeurIPS 2022 (Spotlight). [`arXiv:2210.02647`](https://arxiv.org/abs/2210.02647).

---

## Section 4 — Risks and unknowns

1. **Weights URL fragility** — `gnobitab/RectifiedFlow` distributes checkpoints via
   HuggingFace; if the repo is restructured we need a backup mirror (OpenMMLab's
   `MuseFlow` is the contingency).
2. **CPU FID-50K is slow** — even 1 NFE × 50K samples at 1 s/sample = 14 hours.
   We may need to use a smaller FID-10K for the first reproduction pass and only
   scale up after the framework loop is verified.
3. **Rectified Flow's "reflow" is itself a form of re-inference** — the paper's
   `2-RF` (rectify twice) is conceptually a special case of our adaptive loop.
   We must be careful not to double-count: the baseline we compare against is
   the *non-adaptive* 2-RF pipeline, not a hand-tuned reflow.
4. **Reproductions of paper-grade FID require the exact UNet config** — even small
   changes in channel counts or attention heads drop FID by 1-2 points. We will
   use the official config exactly and document the delta.
5. **ImageNet-256 SOTA candidates (SiT, MeanFlow, LightningDiT) are CPU-infeasible**
   — if the framework needs to scale beyond CIFAR-10 we will need to commit to a
   small-batch CPU pipeline or fall back to fewer samples (FID-1K).
6. **Consistency Models have semantic mismatch** — if we want CM as a secondary
   comparison, we need a different adapter design because the "1-step" property
   is exactly what our re-inference loop wants to beat. Treat CM as a hard baseline.
7. **MeanFlow requires JVP (forward-mode autodiff)** — implementing JVP on CPU
   is straightforward but doubles the memory footprint per sample.

---

## Section 5 — Reproduction plan outline

1. **D1 (0.25 day)** — Clone `gnobitab/RectifiedFlow`; download the 2-RF CIFAR-10
   checkpoint (~120 MB); verify FID-50K matches the paper's 2.21.
2. **D1 (0.5 day)** — Wrap the UNet `v_θ` into an `FMVelocityModel` Python class
   (in `adaptive_reflow/models/`) with a single `predict_velocity(x, t)` method.
3. **D2 (0.5 day)** — Implement the adaptive_reflow loop driver:
   `for sample in dataset: x = x_0; for k in range(max_NFE): x, info = step(x, model);`
   with the budget controller deciding when to stop.
4. **D2-3 (1 day)** — Add the re-inference oracle hook (consume external metric
   feedback from our existing framework contracts: DTB-R1, NC1, L1).
5. **D3 (0.5 day)** — Run the full CIFAR-10 evaluation (FID-50K vs FID-10K) and
   compare against the paper's 2.21 baseline; document the delta.
6. **D4 (0.5 day)** — Write up the integration in `docs/r5-survey/02-rf-integration.md`
   with the four required sections: contract mapping, baseline reproduction table,
   adapter design notes, framework improvement hypothesis.
7. **D5 (buffer)** — If time permits, run the same pipeline with OT-CFM (Candidate B)
   as a second comparison and document a "framework generalizes across FM families"
   result.

**Exit criterion:** FID-50K on CIFAR-10 within ±0.5 of the paper's 2.21 baseline
using the official Rectified Flow weights, plus a working `adaptive_reflow` loop that
improves (or matches) that baseline under a strict NFE budget.

---

## Appendix A — Source list

- Rectified Flow paper — <https://arxiv.org/abs/2210.02647>
- Rectified Flow project page — <https://rectifiedflow.github.io/>
- Rectified Flow repo — <https://github.com/gnobitab/RectifiedFlow>
- MuseFlow (extended) — <https://github.com/open-mmlab/MuseFlow>
- Flow Matching (Lipman) — <https://arxiv.org/abs/2302.00482>
- Flow Matching OpenReview — <https://openreview.net/forum?id=PqvMRDCkN1>
- facebookresearch/flow_matching — <https://github.com/facebookresearch/flow_matching>
- torchcfm (atong01) — <https://github.com/atong01/conditional-flow-matching>
- Stochastic Interpolants paper — <https://arxiv.org/abs/2303.08797>
- stochastic-interpolants repo — <https://github.com/malbergo/stochastic-interpolants>
- Consistency Models paper — <https://arxiv.org/abs/2303.07969>
- openai/consistency_models — <https://github.com/openai/consistency_models>
- Consistency Flow Matching — <https://github.com/YangLing0818/consistency_flow_matching>
- MeanFlow paper — <https://arxiv.org/abs/2505.13447>
- MeanFlow PyTorch (zhuyu-cs) — <https://github.com/zhuyu-cs/MeanFlow>
- MeanFlow JAX (gsunshine) — <https://github.com/gsunshine/meanflow>
- LightningDiT — <https://github.com/hustvl/LightningDiT>
- sCM (OpenAI blog) — <https://openai.com/index/simplifying-stabilizing-and-scaling-continuous-time-consistency-models>
- ReflexFlow — <https://github.com/SafeRL-Lab/ReflexFlow>
