# FlowA — Highlights for *Engineering Applications of Artificial Intelligence*

**Manuscript:** FlowA: Training-Free, Inference-Time Re-Inference Control for Deployed Flow-Matching Checkpoints
**Submitted:** 2026-09-18

---

## Three highlights (EAAI editor-facing)

- **A training-free, drop-in inference layer for deployed flow-matching checkpoints.** FlowA improves *frozen* 2026 SOTA flow-matching checkpoints (Kanzi ICLR'26 protein flow-AE, LineageFlow ICML'26 protein FM, FlowMol3 NeurIPS'24 molecular 3D FM) without retraining, distillation, or model modification. A single 8-method `FlowMatchingODEAdapter` Protocol lets domain experts plug their own checkpoint in; 17 typed state machines with 333 typed transitions codify four pluggable feedback loops. The four theorem constants $(A_g, B_g, C_g, e_\rho)$ are *algorithm inputs*, not tuned hyperparameters.

- **Six Bonferroni-significant empirical claims plus four-arm head-to-head wins.** R1 LineageFlow HMMER hits +116% (N=1000, p < 1e-10); R3 FlowMol3 `fg_dev` Δ = −0.024 at 4.05σ; R5 TwoDim-FM Pareto-frontier (CIFAR-10 RF FID −44.17% NFE-averaged, 2D Two Moons $W_2$ −7.28%, 2D Eight Gaussians $W_2$ −10.40%, MNIST FM FID −15.01%); R6 LineageFlow foldability + scPerplexity +1.12 pLDDT / −3.92 scPerp (N=1000, p < 1e-5); all six pass Bonferroni at α = 0.0083. A **four-arm head-to-head** on the R6 task shows FlowA wins both pLDDT and scPerplexity at NFE ∈ {100, 200} versus **vanilla + Fast-DLLM + AB-Cache + LeDiFlow** — the three baselines exhaust the canonical training-free acceleration design space (parallel-decoding + cache-reuse + distribution-guided prior-shift).

- **5 adapters × 3 domains cross-domain validation, byte-stable reproducible, with 2.5–10× NFE speedup.** The cross-domain validation matrix spans `KanziAdapter` + `LineageFlowAdapter` + `FlowMol3Adapter` + `FreqFlowAdapter` + `TwoDimFMAdapter` covering protein / molecular / image. All five are byte-stable regression-pinned at D.4 (33/33 PASS) and SHA-256-pinned per-adapter. At matched sample quality, FlowA uses 2.5–10× fewer NFE than the single-pass baseline (2D FM NFE=10 reaches baseline NFE=100 quality; CIFAR-10 RF NFE=2 reaches baseline NFE=5 quality). Reproducibility enforced at three machine-verifiable layers: D.4 33/33 PASS regression vectors, SHA-256 ckpt pinning (re-hashed at ship time), and a hash-chained per-round ledger. Full release archived on Zenodo (tarball SHA-256 `9699cd42...430d7`, ≈ 3.00 GiB; manifest at `docs/zenodo-release/manifest.md`).

## Why this matters to the EAAI readership

FlowA targets a problem EAAI readers face every day: **getting more out of an already-deployed generative model without paying for retraining or distillation**. The 2.5–10× NFE speedup at matched sample quality is a direct GPU-cost saving; the typed Protocol surface is a deployment-friendly interface that does not require domain experts to learn FM internals; the published theoretical bound is auditable. Honest negatives (FlowMol3 `pb_validity_pct` −9.95pp UFF-vs-xtb definitional gap; Kanzi `reconstruction_kabsch_rmsd_A` +0.86 Å architectural cost) are disclosed plainly in §5.7 — exactly the engineering honesty EAAI reviewers expect when evaluating a deployable system.