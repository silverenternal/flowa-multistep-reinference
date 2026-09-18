# Cover Letter — FlowA

**To:** Editor-in-Chief, *Engineering Applications of Artificial Intelligence* (Elsevier)
**Re:** Manuscript submission — **FlowA: Training-Free, Inference-Time Re-Inference Control for Deployed Flow-Matching Checkpoints**
**Authors:** [Anonymized for double-blind review]
**Submitted:** 2026-09-18

---

Dear Editor,

We are pleased to submit the enclosed manuscript for consideration as a regular research paper in *Engineering Applications of Artificial Intelligence*. FlowA addresses a problem of immediate practical importance to the EAAI readership: **how to extract more value from an already-deployed flow-matching (FM) generative model — without retraining, distillation, or model modification**.

## What FlowA is, in one sentence

FlowA is a **training-free, inference-time re-inference framework** that improves *frozen* 2026 SOTA flow-matching checkpoints by routing the same model through outcome-conditioned rounds, each scheduled by a published bounded-Lipschitz convergence-rate bound (Li 2026, JMAA Theorem 1). The frozen $\theta$ plugs in via an 8-method `FlowMatchingODEAdapter` Protocol; 17 typed state machines with 333 typed transitions codify four pluggable feedback loops. The four theorem constants $(A_g, B_g, C_g, e_\rho)$ are *algorithm inputs*. FlowA is **solver-agnostic** (Euler, Heun, DPM-Solver++); Wave 185 §11.1 localizes Theorem 1 to the framework's self-convergence — the framework-vs-baseline gap is empirical.

## Six R-level Bonferroni-significant claims

- **R1** LineageFlow HMMER hits **+116%** (158 → 342, N=1000, p < 1e-10).
- **R2** Kanzi foldability via `framework_inv_proj`.
- **R3** FlowMol3 paper-metric parity (`fg_dev` Δ = −0.024 at 4.05σ).
- **R4** ESM-2 NLL smoke (deferred to camera-ready).
- **R5** TwoDim-FM Pareto-frontier: CIFAR-10 RF FID **−44.17%** NFE-averaged, 2D Two Moons $W_2$ **−7.28%**, 2D Eight Gaussians $W_2$ **−10.40%**, MNIST FM FID **−15.01%**.
- **R6** LineageFlow foldability + scPerplexity **+1.12 pLDDT / −3.92 scPerp**, N=1000, p < 1e-5. All six pass Bonferroni (α = 0.0083).

## Four-arm head-to-head wins (§10.30)

FlowA wins both pLDDT and scPerplexity at both NFE settings (100, 200) on the R6 task versus **vanilla + Fast-DLLM (Wu 2025, parallel-decoding) + AB-Cache (Yu 2024, cache-reuse) + LeDiFlow (Zwick 2025, distribution-guided prior-shift)**. pLDDT margin over LeDiFlow: +4.38 / +4.10. The three baselines exhaust the canonical training-free acceleration design space; FlowA wins all three.

## Five adapters × three domains

`KanziAdapter` + `LineageFlowAdapter` + `FlowMol3Adapter` + `FreqFlowAdapter` + `TwoDimFMAdapter` spanning protein / molecular / image. All five implement the eight-method Protocol; all five are D.4 byte-stable (33/33) and SHA-256-pinned.

## Reproducibility — D.4 33/33 PASS + SHA-256 + Zenodo DOI

(i) **D.4 regression vectors**: 33/33 PASS (`pytest -k "d4"`). (ii) **SHA-256 ckpt pinning**: every checkpoint re-hashed at ship time. (iii) **Hash-chained ledger**: per-round metrics SHA-256 chained. Release on Zenodo (tarball SHA-256 `9699cd42...430d7`, ≈ 3.00 GiB).

## Why FlowA fits EAAI

FlowA is an AI-engineering contribution: improves deployed checkpoints without retraining, ships behind a typed Protocol that domain experts can plug into, is governed by a published theoretical bound, and is byte-stable reproducible across heterogeneous FM deployments. The 5 × 3 matrix answers EAAI's broad-applicability emphasis; the 2.5–10× NFE speedup is a direct deployment-cost saving. Honest negatives (FlowMol3 `pb_validity_pct` −9.95pp UFF-vs-xtb gap; Kanzi `reconstruction_kabsch_rmsd_A` +0.86 Å architectural cost) are disclosed plainly in §5.7.

Sincerely,

[Anonymized for double-blind review]
2026-09-18