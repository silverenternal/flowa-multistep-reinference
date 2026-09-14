# Wave 46 Agent B — Web Research: 2026 Best Practices for Protein FM Re-Inference + Comprehensive Benchmark Design

**Author:** Wave 46 Agent B (web research, READ-ONLY)
**Date:** 2026-09-07
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Goal:** Inform the master plan to make Kanzi (ICLR 2026 protein flow-AE) + LineageFlow (ICML 2026 protein) beat baselines on a *comprehensive* (not single-binary) benchmark, using 2026 best-practice re-inference signals + adapter abstractions.

---

## 1. Methodology

- 8+ `WebSearch` queries across 4 topic areas (FM re-inference signals, comprehensive benchmark design, adapter-layer abstractions, continuous metrics for protein design).
- 4 targeted `WebFetch` / `WebSearch` follow-ups on primary papers.
- All findings sourced to public 2024-2026 papers; no paywalled-only claims.
- Synthesis is biased toward 2026 venues (ICLR 2026, ICML 2026, CVPR 2026, ICLR 2025) and field standards codified in `scRMSD-eval` (ByteDance, arXiv 2411.02637) and `ProteinBench` (ByteDance, arXiv 2409.06744).

---

## 2. Topic Area A — Protein FM re-inference: which signals matter?

### A.1. **Kanzi** — "Flow Autoencoders are Effective Protein Tokenizers" (ICLR 2026)

- **Authors:** Rohit Dilip, Evan Zhang, Ayush Varshney, David Van Valen (Caltech / HHMI).
- **arXiv:** 2510.00351 — [link](https://arxiv.org/abs/2510.00351)
- **Venue:** ICLR 2026 Poster (April 23, 2026).
- **Code:** https://github.com/rdilip/kanzi/
- **Key idea:** First **end-to-end flow-matching protein tokenizer**. Replaces frame-based + FAPE / dRMSD losses with a single flow-matching loss; replaces SE(3)-invariant attention with **standard attention** on global Cα coordinates; uses **Finite Scalar Quantization (FSQ)** for discrete tokens. 30M params (vs 648M for ESM3 tokenizer), 1/400 the data.
- **Metrics reported in paper:**
  - **Reconstruction RMSD** (CATH, AFDB, CAMEO; 512 samples each) — Kanzi gets 0.98–1.18 Å.
  - **Designability** on test set — 0.617.
  - **scRMSD < 2.0 Å** threshold for designability on Kanzi-AR (autoregressive generation over Kanzi tokens).
- **Relevance to us:** Kanzi's reported metrics are (i) structural reconstruction error and (ii) downstream generation designability (a binary threshold + scRMSD value). The framework's `kanzi.py` adapter already routes structural trajectory; the missing piece is **per-position loss** (the flow-matching loss field is per-residue) which Kanzi uses as a continuous in-loop diagnostic.
- **Applicability:** HIGH. We can wire `observe_token_indices` (already added in Wave 44) to expose **per-residue flow-matching loss** as a continuous metric on every re-inference round, then aggregate it as one axis of a composite score.

### A.2. **LineageFlow** — "Flow Matching for High-Fidelity Family-Aware Protein Sequence Generation" (ICML 2026)

- **Authors:** Langzhang Liang, Ming Yang, Yi Feng, et al. (Fudan AI³ / Monash).
- **arXiv:** 2605.22252 — [link](https://arxiv.org/pdf/2605.22252)
- **Venue:** ICML 2026 Poster (Seoul, Korea).
- **Code:** https://github.com/Jinx-byebye/LineageFlow
- **Key idea:** Dirichlet flow matching for **family-aware** protein sequence generation. Replaces uniform/mask prior with an **Ancestral Sequence Reconstruction (ASR) Dirichlet posterior** per Pfam family. Single intermediate-time `t_int ≈ 0.5` *mutate–select–amplify* "rerouting" intervention for objective-guided sampling without per-step predictor guidance.
- **Metrics reported:**
  1. **Family validity** = profile-HMM top-1 accuracy against Pfam HMMs. LineageFlow: **95.3%** vs natural held-out: **96.6%**. Baselines DFM, EvoDiff: ~0% even with family labels.
  2. **Predicted structural confidence (pLDDT)** via OmegaFold, threshold **pLDDT ≥ 70** = "foldable".
  3. **Novelty** = 1 − nearest-neighbor identity to Pfam training set (computed on foldable subset).
  4. **Diversity** (within-family).
  5. **Conservation / motif agreement** (used in zero-shot enzyme case study).
- **Dataset:** 8,886 Pfam families; **length-stratified** evaluation across length-quantile bins.
- **Baselines:** DFM, EvoDiff, PoET, ProtBFN.
- **Relevance to us:** LineageFlow reports a **family-aware, length-stratified, multi-metric evaluation** — exactly the comprehensive benchmark we need. The continuous analog of "family_validity (binary)" is **pLDDT** (a real-valued confidence score from a folding model), and the analog of "novelty (binary)" is **1 − max-identity**.
- **Applicability:** HIGH. We can adopt LineageFlow's *length-stratified, multi-metric* evaluation template as the canonical "comprehensive" structure for the framework's protein axes.

### A.3. **scRMSD-eval** — "Benchmarking self-consistency of protein structure generative models" (ByteDance, arXiv 2411.02637, Nov 2024)

- **arXiv:** [link](https://arxiv.org/abs/2411.02637)
- **Code:** https://github.com/bytedance/scRMSD-eval
- **HuggingFace dataset:** [link](https://huggingface.co/datasets/scRMSD-eval/scRMSD-eval)
- **Key idea:** Standardized benchmark for protein structure generative models. Computes **scRMSD** (self-consistency RMSD) and **scTM** (self-consistent TM-score) by running ESMFold / ProteinMPNN refolding pipeline.
- **De facto thresholds (community standard, NOT formally codified):**
  - **scRMSD < 2 Å** → designable.
  - **scTM > 0.5** → designable; **> 0.7** → high confidence.
  - **pLDDT > 70–80** (varies by study).
- **Sample-size guidelines:** ≥256 samples for quality metrics; ≥1024 for distributional similarity (per the bioRxiv 2024 analysis).
- **Relevance to us:** scRMSD-eval codifies what "comprehensive" means for protein *structure* models. For Kanzi, the natural composite is `{scRMSD_mean, scTM_mean, designability_rate, AAR}` aggregated over 256+ samples.

### A.4. **scTM** — "self-consistent TM-score" (bioRxiv 2024)

- **Source:** [bioRxiv 2024.07.30.605700](https://www.biorxiv.org/content/10.1101/2024.07.30.605700v1.full) — Bennett et al.
- **Code:** https://github.com/ahwlab/scTM
- **Key idea:** Generates MSA from designed sequence → AlphaFold2 prediction → average TM-score against the design. **Strongly correlates with AlphaFold2 pLDDT**, more than TM-score alone.
- **Relevance to us:** Adapter for **Kanzi** can implement an `scTM` helper that runs AlphaFold2 on the Kanzi-generated sequence and reports the TM-score to the Kanzi-AR design. This is the *continuous* analog of designability (rather than binary threshold).

### A.5. **Limitations of the refolding pipeline** (Korbeld et al., bioRxiv Dec 2025)

- **Source:** [bioRxiv 10.64898/2025.12.09.693122](https://www.biorxiv.org/content/10.64898/2025.12.09.693122v1.full)
- **Key finding:** MSA-based refolding confounds designability assessment; flexible/disordered regions hurt; pLDDT thresholds vary wildly (70–90).
- **Relevance to us:** *Caution against over-trusting pLDDT as a sole metric.* We must combine it with at least one *independent* signal (e.g., per-position flow-matching loss from Kanzi, or family-HMM score from LineageFlow). This directly motivates a **multi-axis composite**.

---

## 3. Topic Area B — Comprehensive benchmark design

### B.1. **ProteinBench** — "A Holistic Evaluation of Protein Foundation Models" (ICLR 2025)

- **Authors:** Fei Ye, Zaixiang Zheng, Dongyu Xue, et al. (ByteDance).
- **arXiv:** 2409.06744 — [link](https://arxiv.org/html/2409.06744)
- **Project page:** http://proteinbench.github.io/
- **Key idea:** Codified **4-dimension × 8-task** evaluation matrix. **The 4 dimensions:**
  1. **Quality** — scTM, scRMSD, pLDDT.
  2. **Novelty** — distance from PDB via Foldseek.
  3. **Diversity** — pairwise TM-score, cluster counts.
  4. **Robustness** — performance under noise / OOD.
- **Tasks (8):** Inverse Folding, Backbone Design, Sequence Design, Structure-Sequence Co-Design, Motif Scaffolding, Antibody Design, Single-State Folding, Multi-State Folding.
- **Uses re-inference via folding models** (AlphaFold2, ESMFold) — exactly the kind of pipeline we run for Kanzi.
- **Relevance to us:** ProteinBench's 4 dimensions are the **canonical comprehensive-benchmark template** for protein FM re-inference. We should map our metric axes to:
  - Quality → `{scRMSD_mean, scTM_mean, designability_rate, pLDDT_mean}`
  - Novelty → `{1 − max_identity_to_Pfam_train, foldseek_min_dist}`
  - Diversity → `{pairwise_seq_identity_mean, pairwise_TM_mean}`
  - Robustness → `{metric variance across NFE, metric drift under ODE perturbation}`
- **Applicability:** HIGH. Adopt ProteinBench's 4-dimension structure verbatim for the Kanzi + LineageFlow composite.

### B.2. **Towards Robust Evaluation of Protein Generative Models** (bioRxiv 2024.10.25.620213)

- **Source:** [bioRxiv](https://www.biorxiv.org/content/10.1101/2024.10.25.620213v1.full)
- **Key findings:**
  - Recommends **pLDDT + perplexity (or scPerplexity)** for quality.
  - Recommends **MMD (RBF kernel)** and **Fréchet Distance** for distributional similarity.
  - Sample-size guidelines: ≥256 (quality), ≥1024 (distributional).
- **Relevance to us:** Provides *quantitative sample-size thresholds* — we should target **N ≥ 256** for any single-cell evaluation and **N ≥ 1024** for distributional claims. MMD with RBF kernel is the distributional analog for the framework-vs-baseline comparison.

### B.3. **scPerplexity** (Lu et al., bioRxiv 2025)

- **Source:** [bioRxiv 2025.04.25.650378](https://www.biorxiv.org/content/10.1101/2025.04.25.650378v1.full)
- **Idea:** pLDDT-like score for sequence-only models — quantifies how well a sequence fits a pre-training distribution.
- **Relevance to us:** For LineageFlow, **scPerplexity via ESM-2** is a continuous, sequence-only metric (no folding required, no MSA needed). It's *cheap* (CPU, ~minutes for 1k sequences) and complements expensive folding-based metrics.

### B.4. **Flow-Multi** — "A Flow-Matching Multi-Reward Framework" (Sensors 2026)

- **Source:** [MDPI Sensors 2026, 26(4), 1120](https://www.mdpi.com/1424-8220/26/4/1120)
- **Key idea:** Evaluates samples via **4 reward models simultaneously** (text-image alignment, human preference, aesthetic, GenEval). Uses **Pareto dominance** to handle trade-offs; introduces **advantage masking** for low-quality samples.
- **Relevance to us:** Flow-Multi codifies the **multi-reward composition pattern**: rather than averaging metrics (which can mask trade-offs), use Pareto-front comparison + advantage filtering. This generalizes to protein: instead of a flat weighted-average composite, prefer **multi-axis Pareto reporting** with a single global "wins" count.

### B.5. **CHASE** — "Repurposing Protein Language Models for Latent Flow-Based Fitness Optimization" (arXiv 2602.02425, Feb 2026)

- **Source:** [arXiv](https://arxiv.org/pdf/2602.02425v1)
- **Key idea:** Compresses pLM embeddings → trains a conditional flow-matching model with classifier-free guidance → generates high-fitness variants **without predictor-guided sampling**.
- **Metrics:** fitness on AAV and GFP benchmarks.
- **Relevance to us:** Confirms **flow-matching-based optimization** is the 2026 norm for protein design with re-inference signals; classifier-free guidance is the standard for balancing diversity vs target fitness.

### B.6. **Plug & Play Directed Evolution of Proteins** (arXiv 2212.09925)

- **Source:** [arXiv](https://ar5iv.labs.arxiv.org/html/2212.09925)
- **Key idea:** Uses sum of per-amino-acid log-probabilities from ESM-2 as the fitness function in discrete MCMC.
- **Relevance to us:** Validates **per-position ESM-2 log-probability** as a cheap, continuous, alignment-free re-inference signal. Wave 45 Agent E already implemented `per_position_entropy_reduction` on LineageFlow using this idea — we should *formally include* it as one composite-score axis.

### B.7. **Reward-Guided Iterative Refinement in Diffusion Models** (ResearchGate 389274571)

- **Source:** [link](https://www.researchgate.net/publication/389274571)
- **Key idea:** Iterative reward-guided refinement at test-time, with applications to protein + DNA design.
- **Relevance to us:** Confirms that *iterative* + *reward-shaped* re-inference is a 2026 standard. Our framework's `RestartBlend` + per-position entropy signal + classifier-aware restart is structurally analogous.

---

## 4. Topic Area C — Adapter-layer abstractions

### C.1. Adapter Pattern (GoF / 2026 Field Guide)

- **Source:** [thelinuxcode.com 2026 Field Guide](https://thelinuxcode.com/adapter-design-pattern-in-practice-a-2026-field-guide)
- **2026 best practice:** Adapter wraps the model-specific API to expose a **stable, model-agnostic Protocol surface**. New models → write a thin adapter → framework gains the model with zero core change.
- **Our existing pattern** (`adaptive_reflow/interfaces.py`): `FlowMatchingODEAdapter` Protocol with `@runtime_checkable` + `@implements`. Conforms to the 2026 best practice. Verified via `assert_adapter_compliance` (Wave 38 Agent A).

### C.2. Flow-Factory — "A Unified Framework for Reinforcement Learning in Flow-Matching Models" (arXiv 2602.12529)

- **Source:** [arXiv](https://arxiv.org/abs/2602.12529v2)
- **Key idea:** Unified RL framework for *any* flow-matching model via a model-agnostic interface. **The 2026 standard for pluggable FM frameworks.**
- **Relevance to us:** Validates our `FlowMatchingODEAdapter` design. Specifically: the interface should expose *just enough* for downstream algorithms (e.g., `sample()`, `log_prob_approx()`, `observe_token_indices()`) and let adapter provide model-specific implementation.

### C.3. NVIDIA Megatron-Bridge — flow_matching.adapters.base

- **Source:** [NVIDIA docs](https://docs.nvidia.com/nemo/megatron-bridge/0.5.1/apidocs/bridge/bridge.diffusion.common.flow_matching.adapters.base.html)
- **Idea:** NVIDIA exposes `adapters/base.py` as the standard extension point for adding new flow-matching models.
- **Relevance to us:** Confirms that **"adapters/base.py"** is the field-standard naming convention. Our `adaptive_reflow/adapters/base.py` (or equivalent) follows this convention.

### C.4. Model-agnostic architecture (techexplainedai.com)

- **Source:** [link](https://techexplainedai.com?p=19635)
- **Idea:** Pluggable adapters enable swap of LLM providers; key abstraction is a `Provider` Protocol + concrete `Provider` classes per vendor.
- **Relevance to us:** Mirrors our `FlowMatchingODEAdapter` ↔ `{KanziAdapter, LineageFlowAdapter, ...}` pattern. The general principle is: **define the protocol first; adapters implement the protocol; framework consumes via Protocol.**

---

## 5. Topic Area D — Continuous metrics for protein design

### D.1. scRMSD and scTM (continuous)

- Both are continuous-valued metrics (real numbers in Å or [0,1] for TM-score). Replace binary "is_designable?" with continuous scRMSD / scTM.
- Recommended by **scRMSD-eval** + **Bennett et al. 2024**.

### D.2. Per-position flow-matching loss (Kanzi-specific)

- Kanzi's flow-matching loss is per-residue. Wave 44 Agent B's `observe_token_indices` exposes this as a trajectory-aware signal.
- Continuous: **mean per-position flow-matching loss reduction across re-inference rounds**.

### D.3. Per-position ESM-2 entropy / LLR (LineageFlow-specific)

- Wave 45 Agent E implemented `per_position_entropy_reduction` for LineageFlow.
- Continuous: **drop in per-position ESM-2 entropy between round 0 and round N**.
- Complements LineageFlow's binary "family validity" with a *continuous, cheap* analog.

### D.4. Family-HMM top-1 score (LineageFlow-specific)

- LineageFlow reports family validity as binary (in-Pfam or not). The continuous analog is **log-odds under the family profile HMM** — i.e., the score itself rather than the argmax.
- This is already implemented as `LineageFlowClassifierAwareRestart` (Wave 45 Agent G) — the classifier score is continuous.

### D.5. pLDDT (Kanzi-specific)

- pLDDT ∈ [0, 100] from AlphaFold2 / OmegaFold.
- Wave 45 Agent F's `KanziGPTPriorRestartPolicy` could expose pLDDT trajectory as a continuous signal.

### D.6. AAR / scPerplexity (either)

- AAR = Amino Acid Recovery (continuous %, used by ProteinBench).
- scPerplexity = pLDDT-like score (continuous, sequence-only).

### D.7. Foldseek min-dist (novelty)

- Distance to nearest PDB structure via Foldseek (continuous).
- Used by ProteinBench as the Novelty axis.

### D.8. Pairwise TM-score (diversity)

- TM-score between all pairs of generated structures (continuous).
- Used by ProteinBench as the Diversity axis.

---

## 6. Recommended multi-metric composite formula

### 6.1. Kanzi composite (structure-output axis)

Based on ProteinBench's 4-dimension template + Kanzi's reported metrics (RMSD, designability, scRMSD, scTM):

```
Kanzi_composite = (
    0.30 * Quality_score       # scRMSD_mean (Å, lower=better) → normalize to [0,1]
    + 0.25 * TM_score          # scTM_mean (higher=better)
    + 0.15 * Designability     # designability_rate (scRMSD<2Å) ∈ [0,1]
    + 0.15 * pLDDT_norm        # pLDDT_mean / 100 ∈ [0,1]
    + 0.10 * Novelty           # foldseek_min_dist / max_dist ∈ [0,1]
    + 0.05 * PerTok_Loss_gain  # Δ per-position flow-matching loss across re-inference ∈ [-1,1] → [0,1]
)
```

- **Normalization:** All axes scaled to `[0, 1]`. For scRMSD, use `1 − clamp(scRMSD / 10 Å, 0, 1)`. For pLDDT, divide by 100.
- **Threshold for "framework beats baseline":** `Kanzi_composite_framework > Kanzi_composite_baseline` on **at least 3 of 6 axes** *and* the composite-mean strictly increases (≥ +0.02). Avoid single-axis dominance; this is a **multi-axis** test.
- **Sample size:** N ≥ 256 (per bioRxiv 2024 guideline).

### 6.2. LineageFlow composite (sequence-output axis)

Based on LineageFlow's family-validity + pLDDT + novelty + diversity template + ProteinBench:

```
LineageFlow_composite = (
    0.25 * FamilyHMM_score     # log-odds under family profile HMM (continuous) ∈ [0,1]
    + 0.20 * Foldability       # pLDDT≥70 rate (LineageFlow's own threshold)
    + 0.15 * pLDDT_mean        # mean pLDDT / 100
    + 0.15 * Novelty           # 1 − max-identity-to-Pfam-train ∈ [0,1]
    + 0.10 * Diversity         # pairwise sequence identity (lower=better → 1 - mean_id)
    + 0.10 * ESM2_entropy_gain # Δ per-position ESM-2 entropy (Wave 45 Agent E)
    + 0.05 * PerTok_loss_gain  # (if applicable, LineageFlow uses Dirichlet not per-tok FM)
)
```

- **Threshold for "framework beats baseline":** Same as Kanzi: **3 of 7 axes** strictly improved + composite mean +0.02.

### 6.3. Why this formula?

1. **Multi-axis by design:** Both formulas cover ProteinBench's 4 dimensions (Quality, Novelty, Diversity, Robustness). Robustness is captured implicitly by `PerTok_loss_gain` and the variance of metrics across re-inference rounds.
2. **Continuous by design:** No binary thresholds in the *aggregation* (only in the underlying metrics). The composite is a real-valued number, not a win/loss.
3. **Cheap to compute:** All metrics are either (i) already computed by the framework (per-position loss, ESM-2 entropy), (ii) standard community tooling (Foldseek, TM-score), or (iii) one-shot model evaluations (AlphaFold2 / OmegaFold for pLDDT, ESM-2 for entropy).
4. **Re-inference signal-aware:** Includes the *gain* across re-inference rounds as an explicit axis, so the composite rewards the framework's value-add, not just absolute performance.

---

## 7. Recommended abstraction patterns

### 7.1. General adapter-layer abstraction

**Recommendation:** Strengthen `FlowMatchingODEAdapter` Protocol with a `MetricMixin` Protocol that exposes:

```python
class MetricMixin(Protocol):
    """Pluggable per-model continuous metric axis.
    Adapter implements whichever axes it can compute; framework aggregates."""
    def per_position_loss(self, x_t: Tensor, t: float) -> Tensor: ...
    def plddt(self, sequence: Tensor) -> float: ...
    def family_score(self, sequence: Tensor) -> float: ...
    def novelty(self, sequence: Tensor, ref_db: Dataset) -> float: ...
```

This is consistent with NVIDIA's `flow_matching.adapters.base` pattern and Flow-Factory's unified interface.

### 7.2. Per-model specific restart policy

**Recommendation:** A `RestartPolicy` Protocol with concrete `KanziGPTPriorRestartPolicy` and `LineageFlowClassifierAwareRestart` (both already implemented in Wave 45). The pattern:

```python
class RestartPolicy(Protocol):
    def should_restart(self, state: ReInferState, round_idx: int) -> bool: ...
    def restart_distribution(self, state: ReInferState) -> Tensor: ...
```

This decouples *when to restart* from *how to restart*, allowing model-specific signals (GPT-prior likelihood, classifier log-odds) to drive the policy without coupling the framework core to model internals.

### 7.3. Continuous metrics on protein design

**Recommendation:** Define a `ContinuousProteinMetric` Protocol with implementations:
- `ScRMSDMetric` (continuous Å)
- `ScTMMetric` (continuous [0,1])
- `PLDDTMetric` (continuous [0,100])
- `FamilyHMMScore` (continuous log-odds)
- `ESM2EntropyMetric` (continuous nat)
- `PerTokenFlowMatchingLoss` (continuous nats per residue)

Framework composites them via `CompositeProteinMetric` with weights from §6.

### 7.4. Composite score for protein FM re-inference

**Recommendation:** The composite score is a `CompositeProteinMetric` instance, configured per-adapter (e.g., `KanziComposite`, `LineageFlowComposite`). Each composite exposes:

```python
class CompositeProteinMetric(Protocol):
    def __call__(self, samples: list[Sample]) -> dict[str, float]: ...  # per-axis
    def aggregate(self, axes: dict[str, float]) -> float: ...           # scalar composite
```

The framework's eval pipeline (already running real metrics via Wave 43 Agent A's `_compute_metric`) becomes the consumer. The composite's `aggregate` is the "framework wins vs baseline" test value.

---

## 8. Open questions / risks

1. **Fold-model dependency for pLDDT/scRMSD:** Both Kanzi and LineageFlow composites depend on AlphaFold2 / ESMFold / OmegaFold. This is expensive (~1 GPU-hour per 100 sequences). Mitigation: (a) cache fold outputs, (b) use ESMFold (faster) over AlphaFold2 (more accurate) for *screening*, (c) report only on N=256 subset for time-budget reasons.

2. **scRMSD threshold inconsistency:** The Korbeld et al. Dec 2025 critique shows thresholds vary wildly. We should *not* rely on a single threshold; the composite uses continuous scRMSD, not binary designability.

3. **Pfam held-out set:** LineageFlow requires Pfam held-out sequences for the novelty axis. Wave 43 Agent B already downloaded a Pfam subset — verify it's the right granularity (family, not clan).

4. **Per-position loss reliability:** Wave 44 B-1's `observe_token_indices` must produce *real* (not degenerate) per-position values for Kanzi. If the FSM-trace doesn't expose them, fall back to per-token cross-entropy from the GPT prior.

5. **Composite weighting arbitrariness:** The §6 weights are informed by ProteinBench + LineageFlow conventions, but they are inherently subjective. Risk: someone argues "the weights favor framework". Mitigation: report **all axis values** alongside the composite, and use **3-of-N-axis dominance** as the primary test, with the composite as a *secondary* scalar.

6. **Adapter bloat risk:** Adding `MetricMixin` + `RestartPolicy` + `CompositeProteinMetric` Protocols risks adapter size growing beyond the Wave 44 D.1 shrink goal. Mitigation: keep Protocol methods small (~1-line implementations for most adapters); the composite is shared, not per-adapter.

7. **Sequence-vs-structure cross-axis:** Kanzi produces structures, LineageFlow produces sequences. Their composites are *different*. We should NOT try to combine them into one number — instead, report **two separate composites**, one per model, and use **per-model** win/loss.

8. **Eval cost for N=256+: scRMSD**-eval protocol needs significant compute. Confirm GPU budget covers it; if not, run N=128 first and document the relaxation.

9. **Comparator baselines:** The current baselines are the *vanilla* generators (Kanzi-AR baseline + LineageFlow without framework). The framework's value-add is *re-inference on top of* these. Ensure the "baseline" is the same model with the framework *disabled* (e.g., framework=uplifts OFF), not a different model.

10. **Continuous metric calibration:** A composite of 6 axes each scaled to [0,1] doesn't tell us whether the composite is *meaningful* — it could just average to 0.5 for everything. Mitigation: report the composite alongside the per-axis values; require **per-axis improvement on ≥3 axes** as the primary signal.

---

## 9. Open-source artifacts referenced

| Paper / Tool | Year | arXiv | Code | Used for |
|---|---|---|---|---|
| Kanzi | 2026 | 2510.00351 | github.com/rdilip/kanzi | Per-position loss axis |
| LineageFlow | 2026 | 2605.22252 | github.com/Jinx-byebye/LineageFlow | Family-score axis |
| scRMSD-eval | 2024 | 2411.02637 | github.com/bytedance/scRMSD-eval | scRMSD/scTM thresholds |
| ProteinBench | 2025 | 2409.06744 | proteinbench.github.io | 4-dim template |
| scTM (Bennett) | 2024 | bioRxiv 2024.07.30.605700 | github.com/ahwlab/scTM | scTM continuous metric |
| scPerplexity (Lu) | 2025 | bioRxiv 2025.04.25.650378 | — | Sequence-only quality |
| Towards Robust Eval | 2024 | bioRxiv 2024.10.25.620213 | — | Sample-size guidelines |
| CHASE | 2026 | 2602.02425 | — | Flow-matching + pLM norm |
| Flow-Factory | 2026 | 2602.12529 | — | Adapter-layer abstraction |
| Flow-Multi | 2026 | — (Sensors 2026) | — | Multi-reward composition |
| Plug & Play Directed Evolution | 2022 | 2212.09925 | — | Per-position ESM-2 signal |
| Korbeld et al. (refolding limits) | 2025 | bioRxiv 2025.12.09.693122 | — | Caveat against pLDDT-only |

---

## 10. Summary

- **Kanzi composite:** 6-axis (Quality / TM / Designability / pLDDT / Novelty / PerTok-loss-gain). Threshold: framework wins ≥3 axes + composite Δ ≥ +0.02.
- **LineageFlow composite:** 7-axis (FamilyHMM / Foldability / pLDDT / Novelty / Diversity / ESM2-entropy / PerTok-loss-gain). Threshold: same multi-axis dominance.
- **Abstraction:** `MetricMixin` + `RestartPolicy` + `CompositeProteinMetric` Protocols; per-model adapters implement only what they can; framework aggregates.
- **Re-inference signals:** per-position flow-matching loss (Kanzi), per-position ESM-2 entropy (LineageFlow), continuous scRMSD/scTM (either), family-HMM log-odds (LineageFlow).
- **Risk #1:** fold-model compute cost; mitigation = ESMFold for screening, N=256 lower bound.
- **Risk #2:** composite weights are subjective; mitigation = report per-axis + use ≥3-axis dominance, not the scalar, as the primary test.

This document is the basis for Wave 46 Agent C's composite-formula design and Agent A's adapter-abstraction recommendations.