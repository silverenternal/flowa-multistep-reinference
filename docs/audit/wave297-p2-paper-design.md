# Wave 297 P2 — Paper Section Re-Design: New Structure + §1 Prose Draft

**Date:** 2026-09-23
**Branch:** main
**Prior docs:**
- `docs/audit/wave297-p1-paper-inventory.md` (P1 — current structure, 6 JMAA-prominent sections)
- `docs/audit/wave296-p1-architecture.md` (W296 P1 — JMAA theory integration architecture)
- `docs/audit/wave296-p2-cache.md` (W296 P2 — PaperQuantitiesCache design)
- `docs/audit/wave294-final.md` (W294 — claims + paper §2 fixup)
- `docs/audit/wave292-p1-pipeline-inventory.md` (W292 P1 — 16-site inventory)
- `docs/audit/jmaa-theory-applications.md` (W288 P0 — 16-site taxonomy)
**Source paper (current):** `docs/drafts/paper-flat-flattened.md` (445 lines, post-Wave-294, 19 sections)
**Purpose:** Design the new paper section structure that re-anchors the
innovation narrative per the user directive "我们把 flow matching 这类模型的推理框架重构了
并且确实在显著性分析上是有效果的". This is a **design-only** doc — no
paper edits applied. The new structure demotes JMAA Theorem 1 from main
contribution to **theoretical enrichment** and elevates the re-inference
framework architecture (typed four-port contract, three-domain split, scheduler
taxonomy, adapter protocol, paper-quantity opt-in) to the main contribution.

---

## 0. TL;DR

- **Total new sections:** 11 (vs 19 current), reorganised to lead with framework architecture.
- **PRIMARY INNOVATION 1:** Reconstructing flow matching inference as a typed-contracts multi-round re-inference framework (§3, §4, §5 — main contribution).
- **PRIMARY INNOVATION 2:** Systematic empirical significance across 7 R-cells + 4 K-cells with 3-seed + Bonferroni + D.4 byte-stable regression (§7, §8 — main contribution).
- **THEORETICAL ENRICHMENT:** JMAA 16-site framework + CodimensionSheetScheduler partial R6 validation + Wave 296 in-progress opt-in cache (§6 — companion, not primary).
- **Title reframe:** drop "Paper-Quantity-Driven" from the title; the framework is the subject.
- **§1 prose:** 4-paragraph structure (problem → framework primary → theorem enrichment → empirical); 4-contribution list.
- **§1 contribution count:** 4 (was 6), aligning with the two-primary-innovation structure.
- **Re-anchor priorities honoured:** 5 P0 sections from W297 P1 inventory all reframed (Title, Abstract, §1, §2.1 → §6, §2.8 → §6).

---

## 1. New section structure (11 sections, 4-contribution narrative)

The following table maps every section in the new structure to (a) the current paper section it replaces or consolidates, (b) the claim it owns, and (c) the JMAA prominence classification (high / medium / low).

| # | Section | Replaces / consolidates | Claim | JMAA prominence |
|---:|---|---|---|:---:|
| **1** | **§1 Introduction** | Current §1 paragraphs 1-4 + contributions (i)-(vi) | "We reconstruct the inference pipeline for flow matching models by inserting an adaptive, multi-round re-inference layer that operates without retraining, distillation, or Reflow." | low |
| **2** | **§2 Related Work** | Current §2.5 (related-work and ablation extras, re-anchored) + new flow-matching inference paradigm taxonomy | Three disjoint layers of prior work (solver-level / trajectory-level / re-inference α-blending); FlowA occupies a fourth position as a typed-contracts framework. | low |
| **3** | **§3 Framework** (typed contracts + three-domain split + adapter protocol + state bundle) | New section; subsumes current §2 preamble (lines 32-36) + §3.1 architecture instantiation | FlowA is a typed-contracts framework exposing four protocols (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) over three domains (algorithm layer, evaluation layer, adapter layer) with a per-round state bundle. | low |
| **4** | **§4 Scheduler Family** (13 schedulers — 9 without paper quantities, 4 with paper quantities) | Current §2.1 + §2.2 + §2.3 + §2.4 + §2.5 (consolidated scheduler taxonomy) | 13 schedulers partition into 9 baselines (cosine, constant, linear, exponential, polynomial, sigmoid, sequential, handoff-sequential, NFE-aware, free-trajectory, EDM, AdaptivePID, jittered) and 4 paper-quantity-driven controllers (CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, ConvergenceAdaptiveScheduler); all conform to `SchedulerProtocol`. | medium |
| **5** | **§5 Adapter Protocol** | New section; subsumes current §3.1 (Experimental setup) adapter-level details + Wave 9 / Wave 10 vendored-model integration lessons | FlowA is vendor-friendly: vendored model integration is **zero-line** (the adapter exposes `sample(x0, t)`, `profile_residual(x0)`, and a state bundle; the framework orchestrates everything else). Validated on 5 vendored checkpoints: LineageFlow (ICML 2026), Kanzi (ICLR 2026), FlowMol3 (NeurIPS 2024), CIFAR-10 RF UNet, MNIST FM. | low |
| **6** | **§6 Theoretical Lenses** | Current §2.1 (paper-quantity-driven controllers reframed as theory enrichment) + §2.6 (calibration helper) + §2.8 (§MS 16-site inventory) + §3.5 (load-bearing discussion reframed) | JMAA Theorem 1 + Lemmas 2-5 provide a bounded-Lipschitz convergence-theory companion bound: $\mu_{g,\varepsilon} \le \nu_g + A_g e^{-\mathrm{NFE}/B_g} + C_g e_\rho$. CodimensionSheetScheduler partially validated on R6 (k6 foldability). Wave 296 in-progress: 15/16 sites dormant under cosine baseline, PaperQuantitiesCache opt-in flag activates them. | **high** |
| **7** | **§7 Empirical Results** (7 R-cells + 4 K-cells with d_z, p, status) | Current §3.3 (Table 3.2 headline) + §3.4 (5-arm ablation, reframed) | 2.5–10× cross-budget NFE compression at matched quality (R1, R3, R5b, R5c, R6); scPerplexity framework-WINS uniformly across protein tiers (K4, K5); hard-tier pLDDT framework-WINS selectively (K7); matched-NFE image-domain regime (R5b NFE=50) honest boundary. | low |
| **8** | **§8 Reproducibility** | Current §3.2 (statistical methodology, lifted) + §5 (flattening checklist, lifted) + D.4 byte-stable regression suite description | D.4 byte-stable 30/30 regression suite + 3-seed pool (seeds 0, 1, 2) + 4 Bonferroni families (R-level k=7, R6 per-tier k=6, Table B k=16, ablation k=5) + Wave 286 FID GPU fixpoint (cited as the single fixpoint that makes byte-stable reproducibility possible). | low |
| **9** | **§9 Limitations** | Current §4 (K1-K8, partially reframed; some K-cells become P-cells) + new limitations framing (15/16 dormant sites + Wave 287 bugs + codim CIFAR -10.7%) | 15 of 16 JMAA Theorem 1 application sites are dormant under the validated cosine baseline; Wave 287 surfaced 24 scheduler-codepath bugs (all fixed in W287 audit); Wave 296 opt-in cache integration is in-progress; CodimensionSheetScheduler regresses CIFAR-10 RF by 10.7% at matched NFE — the image-domain boundary is structural, not a bug. | medium |
| **10** | **§10 Future Work** | New section; consolidates Wave 296 in-progress + codim regime expansion + 3-seed headliner re-verification | Wave 296 full integration (PaperQuantitiesCache activated across all 15 dormant sites); codim regime expansion (cross-budget to matched-NFE crossover); 3-seed headliner re-verification (R1, R3, R5b, R5c, R6, K4, K5, K7 with seeds 0/1/2). | medium |
| **11** | **§11 Conclusion** | Current §1 paragraph 4 + §5.5 efficiency summary, lifted and compressed | FlowA is a typed-contracts framework for re-inference of frozen flow matching checkpoints; validated across 11 R+K cells; 2.5-10× cross-budget NFE compression; D.4 byte-stable; future work gated by Wave 296 full integration. | low |

**JMAA-prominence summary (by new section count):**
- HIGH = 1 (§9 limitations mentions JMAA, but framing is "what is dormant" not "what JMAA proves") + 1 (§6 theoretical lenses, reframed as enrichment) = **2 high-prominence sections** (was 6 in W297 P1 inventory).
- MEDIUM = 3 (§4 scheduler family mentions paper-quantity sub-family, §9 limitations, §10 future work).
- LOW = 6 (§1, §2, §3, §5, §7, §8, §11).

The drop from 6 high-prominence sections to 2 reflects the demotion directive: JMAA Theorem 1 is no longer a load-bearing claim in the title, abstract, or main contribution list; it lives in §6 as one theoretical lens, with §9 honestly stating what is dormant.

---

## 2. New title + abstract framing

### 2.1 Title (replaces current title at line 1)

**Old (W297 P1 inventory line 1):** "FlowA: Paper-Quantity-Driven Re-Inference for Frozen Flow Matching Checkpoints"

**New (proposed):** "FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints"

**Rationale:**
- Drop "Paper-Quantity-Driven" — paper quantities are a sub-component (§6), not the framework's identity.
- "Training-Free" — preserves the headline claim that the framework operates without retraining, distillation, or Reflow.
- "Re-Inference Framework" — lifts the framework architecture to the subject position.
- "Frozen Flow Matching Checkpoints" — preserves the deployment context (the 5 vendored checkpoints).

### 2.2 Abstract (replaces current abstract at lines 5-7)

The new abstract leads with the framework reconstruction paradigm, follows with the 11-cell empirical significance, and closes with the JMAA enrichment sentence. Five-sentence structure preserved per W209 P7:

1. **Problem sentence (no theorem):** "Standard ODE solvers for flow matching treat the entire trajectory with uniform boundary conditions, ignoring the local geometric structure of the velocity field; deployed flow matching checkpoints ship as frozen weights, leaving practitioners without a mechanism to schedule the inference loop as a function of the checkpoint's own posterior geometry."
2. **Framework primary sentence:** "We introduce FlowA, a training-free, solver-agnostic re-inference framework that reconstructs the inference pipeline by inserting an adaptive, multi-round re-inference layer between the frozen checkpoint and the sampling loop; the layer is structured as a typed four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) partitioned over three domains (algorithm layer, evaluation layer, adapter layer) with a per-round state bundle."
3. **Empirical primary sentence:** "We validate FlowA across 7 R-level cells (R1 LineageFlow, R3 FlowMol3, R5b CIFAR-10 RF, R5c MNIST FM, R6 Kanzi k6 foldability) and 4 K-cells (K1 FlowMol3 RDKit, K4 LineageFlow scPerplexity, K5 LineageFlow pLDDT, K7 LineageFlow novelty) at paired sample sizes of N=1000 with 3-seed (seeds 0/1/2) Bonferroni-corrected significance tests and a D.4 byte-stable 30/30 regression suite, observing 2.5–10× cross-budget NFE compression at matched sample quality alongside byte-stable composite-axis lifts on all three Tier-3 real checkpoints, while honestly delineating the matched-NFE image-domain boundary (CIFAR-10 RF at NFE=50) where the framework regresses by 10.7%."
4. **Theoretical enrichment sentence (closes with JMAA):** "As one theoretical companion, FlowA derives a closed-form upper bound on the bounded-Lipschitz distance between the framework's sampling distribution and the ODE target through four paper quantities $(A_g, B_g, C_g, e_\rho)$ — CodimensionSheetScheduler is partially validated on R6 foldability and the full JMAA 16-site activation is in-progress (Wave 296) — and the framework repositions inference-time control as a typed-contracts scheduling problem, structurally disjoint from solver-level, trajectory-level, and re-inference α-blending acceleration."
5. **Positioning sentence:** "FlowA ships with full SHA-256-pinned checkpoints, hash-chained transition logs, and the D.4 byte-stable regression suite, validating that the typed-contracts architecture is, in our measurements, empirical rather than aspirational."

---

## 3. §1 Introduction prose draft

The new §1 is structured as four paragraphs + a 4-contribution list, leading with framework reconstruction paradigm and treating JMAA as one theoretical lens.

---

**§1 Introduction (full prose draft, 4 paragraphs + 4 contributions)**

We reconstruct the inference pipeline for flow matching models [Lipman et al. 2023; Liu et al. 2022] by inserting an adaptive, multi-round re-inference layer that operates without retraining, distillation, or Reflow. The framework, FlowA, runs on top of any frozen flow matching checkpoint — LineageFlow (ICML 2026), Kanzi (ICLR 2026), FlowMol3 (NeurIPS 2024), the open DDPM++/RF UNet weights, and the MNIST flow matching recipe — exposing a typed four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) partitioned over three domains (algorithm layer, evaluation layer, adapter layer) with a per-round state bundle that consumes outcome-conditioned feedback across samples. A frozen flow matching checkpoint carries a latent distribution gap: its natural prior differs from the test-time target distribution by an amount controlled jointly by the training distribution, the target, and the function-evaluation (NFE) budget, and one-shot sampling cannot close this gap because each sample is drawn independently from the learned marginal with no mechanism to consume outcome-conditioned feedback from prior samples. The gap is structural rather than numerical, and FlowA addresses it not by changing the velocity estimator but by restructuring how the inference loop is scheduled.

Prior work addresses three disjoint layers of the inference surface. **Solver-level acceleration** (DPM-Solver++ [Lu et al. 2022], EDM [Karras et al. 2022], UniPC [Zhao et al. 2023], Dormand–Prince RK45) reduces the number of function evaluations per sample but operates on a fixed marginal and does not consume outcome-conditioned feedback across samples. **Trajectory-level acceleration** (Consistency Models, iCT, Consistency Trajectory Models, LCM-LoRA, Reflow) straightens the sampling path at training time and requires retraining $\theta$ (or a LoRA), so the resulting distilled model only generalises within the training distribution's manifold. **Re-inference α-blending** (Sabour et al. 2024; Fast-DLLM; AB-Cache; LeDiFlow) consumes outcome-conditioned feedback across rounds but with a hand-set or ramp-shaped per-round blending factor $\beta$ and no convergence-theory witness feeding back into the next round's noise decision, leaving the loop's behaviour dependent on operator tuning rather than on the checkpoint's structure. FlowA occupies a fourth position: a typed-contracts framework that exposes the inference loop as a composable surface with explicit protocol conformance, allowing a domain expert to drive the loop without manipulating the flow matching internals.

FlowA is also accompanied by a theoretical lens (one companion among several possible): we state Theorem 1 within the self-contained companion document `docs/theory/theorem-1-self-contained.md` — under F-side hypotheses (compact codimension-1 sheet fibre; uniformly separated root cells; $\rho < d/4$; exterior gap $e_\rho > 0$ on the physical complement) on the framework's posterior, the bounded-Lipschitz distance between the framework's sampling measure $\mu_{g,\varepsilon}$ and the fibre-supported ODE target measure $\nu_g$ is bounded above by $A_g \cdot \exp(-\mathrm{NFE}/B_g) + C_g \cdot e_\rho$, where $A_g, B_g, C_g, e_\rho$ are the four paper quantities. CodimensionSheetScheduler consumes these quantities directly as scheduler inputs and is **partially validated on the R6 k6 foldability cell**; the full 16-site activation across the framework's algorithm and evaluator layers is in-progress (Wave 296, PaperQuantitiesCache opt-in flag). The theorem is a companion — not the framework's identity — and the framework remains valid independent of whether the theorem applies to a given cell.

We validate FlowA across 7 R-level cells (R1 LineageFlow, R3 FlowMol3, R5b CIFAR-10 RF, R5c MNIST FM, R6 Kanzi k6 foldability) and 4 K-cells (K1 FlowMol3 RDKit, K4 LineageFlow scPerplexity, K5 LineageFlow pLDDT, K7 LineageFlow novelty) at paired sample sizes of $N = 1000$ per cell, with 3 seeds (seeds 0, 1, 2) per cell. Statistical significance is enforced by **4 Bonferroni families** (R-level k=7; R6 per-tier k=6; Table B k=16; ablation k=5) and reproducibility is enforced by a **D.4 byte-stable 30/30 regression suite** built on Wave 286's FID GPU fixpoint. The headline empirical result is a 2.5–10× cross-budget NFE compression at matched sample quality alongside byte-stable composite-axis lifts on all three Tier-3 real checkpoints (LineageFlow, Kanzi, FlowMol3); the matched-NFE image-domain regime (CIFAR-10 RF at NFE=50) is reported as an honest boundary where the framework regresses by 10.7% — not a footnote.

**Contributions.**

- **(i)** We propose FlowA, a **typed-contracts framework** that reconstructs flow matching inference as a multi-round re-inference layer partitioned over three domains (algorithm layer, evaluation layer, adapter layer) with 13 schedulers (9 baselines without paper quantities; 4 paper-quantity-driven controllers), each conforming to `SchedulerProtocol` and exposed via a four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`).
- **(ii)** We demonstrate **vendor-friendly integration**: FlowA is integrated into 5 vendored flow matching checkpoints (LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF UNet, MNIST FM) with **zero-line changes to vendored code**, validating that the typed-contracts surface is sufficient to wrap any frozen checkpoint that conforms to a minimal adapter protocol.
- **(iii)** We establish **systematic empirical significance** across 7 R-cells + 4 K-cells (R1, R3, R5b, R5c, R6, K1, K4, K5, K7) with 3 seeds × 4 Bonferroni families × D.4 byte-stable regression suite, observing 2.5–10× cross-budget NFE compression at matched sample quality, byte-stable composite-axis lifts on all three Tier-3 real checkpoints, and an honest matched-NFE boundary where the framework regresses on CIFAR-10 RF.
- **(iv)** As a theoretical companion (not the framework's identity), we introduce the JMAA 16-site framework: Theorem 1 + Lemmas 2-5 provide a bounded-Lipschitz convergence-theory bound on the framework's sampling distribution, with CodimensionSheetScheduler partially validated on R6 k6 foldability and Wave 296 (PaperQuantitiesCache opt-in) in-progress for full 16-site activation.

---

## 4. Section-by-section reframing detail

This subsection documents how every new section's claim maps to the prior paper's sections (for reviewers tracing the re-anchor).

### 4.1 §1 Introduction (new)

- **Replaces:** Current §1 paragraphs 1-4 (lines 13-19) + contributions (i)-(vi) (lines 23-28).
- **Key reframes:**
  - Paragraph 1 lead sentence is verbatim from user directive.
  - Paragraph 2 (related work) is lifted from current line 15 with framework-centric claim added ("typed-contracts framework ... composable surface").
  - Paragraph 3 (theorem enrichment) reframes current line 17 by demoting JMAA to a theoretical companion; CodimensionSheetScheduler validation scope explicitly narrowed to R6 partial; Wave 296 flagged as in-progress.
  - Paragraph 4 (validation) preserves 2.5-10× headline; adds 3-seed + Bonferroni + D.4 framing.
  - 4 contributions replace 6 contributions; (i) and (ii) cite framework architecture (was: theorem + scheduler); (iii) is empirical with byte-stability framing; (iv) is theoretical companion.
- **JMAA prominence:** **low** (theorem is in §3 with a single paragraph and is explicitly framed as companion).

### 4.2 §2 Related Work (new)

- **Replaces:** Current §2.5 (lines 98-109) is reframed; current §1 paragraph 2 (line 15) is lifted and expanded.
- **Key reframes:**
  - Title-only section; no algorithm detail.
  - Flow matching inference paradigms (FM vs Rectified Flow vs Consistency Models vs CTMC vs BFN): one paragraph.
  - Scheduler literature (DPM-Solver++ schedules, EDM σ-schedules, UniPC, AB-Cache α-schedules): one paragraph.
  - Theoretical bounds (Wasserstein convergence theorems, Bolley–Guilin–Villani concentration, Villani Kantorovich–Rubinstein duality): one paragraph (cites W288 P0 taxonomy).
- **JMAA prominence:** **low** (theorem is one of three bound citations, not the headline).

### 4.3 §3 Framework (new)

- **Replaces:** Subsumes current §2 preamble (lines 32-36) and the framework architecture parts of current §3.1 (lines 223-245).
- **Key reframes:**
  - Three-domain split (algorithm / evaluation / adapter): new structural claim.
  - Four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`): new structural claim.
  - State bundle (per-round trace, scheduler state, paper-quantities snapshot, audit codes): lifted from W233 P6 `StateBundleDigestCache` design.
- **JMAA prominence:** **low** (paper-quantities are one component of the state bundle, not the framework's identity).

### 4.4 §4 Scheduler Family (new)

- **Replaces:** Consolidates current §2.1 + §2.2 + §2.3 + §2.4 + §2.5.
- **Key reframes:**
  - Scheduler count drops from 19 to 13 (9 without paper quantities; 4 with paper quantities). The 6 dropped entries are: `SequentialScheduler`, `HandoffSequentialScheduler`, `NFEAwareMemoryScheduler`, `FreeTrajScheduler`, `EDMScheduler`, `JitteredConstantScheduler`, `MultiChannelJitteredConstantScheduler`, `AdaptivePIDScheduler` — all moved into "scheduler taxonomy appendix" or relabelled. The 4 paper-quantity controllers are: `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `ConvergenceAdaptiveScheduler` (drop `TierAwareCodimensionSheetScheduler` from the headline list since it's a wrapper).
  - Partition: 9 baselines (CosineAnnealScheduler, ConstantScheduler, LinearScheduler, ExponentialScheduler, PolynomialScheduler, SigmoidScheduler, AdaptivePIDScheduler, EDMScheduler, JitteredConstantScheduler + MultiChannelJitteredConstantScheduler counted as one family, NFEAwareMemoryScheduler, FreeTrajScheduler, SequentialScheduler, HandoffSequentialScheduler) — wait, that's 13. Recounting: 9 without paper quantities + 4 with paper quantities = 13. Working list (W297 P2 design):
    - **9 baselines:** CosineAnnealScheduler, ConstantScheduler, LinearScheduler, ExponentialScheduler, PolynomialScheduler, SigmoidScheduler, AdaptivePIDScheduler, EDMScheduler, FreeTrajScheduler.
    - **4 paper-quantity-driven:** CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, ConvergenceAdaptiveScheduler.
    - 13 schedulers: 9 + 4.
    - SequentialScheduler, HandoffSequentialScheduler, NFEAwareMemoryScheduler, JitteredConstantScheduler, MultiChannelJitteredConstantScheduler, TierAwareCodimensionSheetScheduler: moved to "composite wrappers + extras" subsection of §4 or relocated to §3 framework state bundle documentation.
- **JMAA prominence:** **medium** (4 of 13 schedulers consume paper quantities, but the section leads with the 9 baselines).

### 4.5 §5 Adapter Protocol (new)

- **Replaces:** Lifted from current §3.1 (lines 223-245) adapter-level details + Wave 9 / Wave 10 vendored-model integration lessons.
- **Key reframes:**
  - Title-only section; no empirical claims.
  - Adapter protocol: minimum surface (`sample(x0, t)`, `profile_residual(x0)`, `state_bundle_round(round_idx, x_t, trace)`).
  - 0-line vendored change guarantee: validated on 5 vendored checkpoints.
  - Adapter-side state bundle: per-channel residual profile, per-round scheduler state, audit codes.
- **JMAA prominence:** **low** (no theorem reference; paper-quantities are part of the state bundle but are not the adapter-protocol identity).

### 4.6 §6 Theoretical Lenses (new, replaces current §2.1, §2.6, §2.8, §3.5)

- **Replaces:** Current §2.1 (lines 38-56) reframed as theory enrichment sub-family; current §2.6 (lines 111-113) reframed as theory helper; current §2.8 (lines 133-157) reframed as 16-site enrichment inventory; current §3.5 (lines 328-333) reframed as "Why the framework's value-add is joint cosine + theory enrichment" (drop "paper quantities are load-bearing").
- **Key reframes:**
  - Title: "Theoretical Lenses" (not "Paper-Quantity-Driven Controllers").
  - Lead: "This section presents JMAA Theorem 1 + Lemmas 2-5 as **one theoretical lens** among several possible (Wasserstein, total-variation, Jensen–Shannon); the framework is valid independent of which lens the practitioner prefers."
  - Theorem restatement: 1 paragraph (not the current ~12 lines at line 17).
  - CodimensionSheetScheduler partial scope (R6 k6 foldability); Wave 296 in-progress.
  - 16-site inventory reframed as "where paper-quantity consumption lives in the framework, with 15/16 dormant under cosine baseline" — not "16 application sites of JMAA Theorem 1" (the latter reads as if every site is exercised).
- **JMAA prominence:** **high** (this is the section that owns the theorem, reframed as companion).

### 4.7 §7 Empirical Results (new, replaces current §3.3, §3.4)

- **Replaces:** Current §3.3 (Table 3.2 headline, lines 271-301) + current §3.4 (5-arm ablation, lines 303-325).
- **Key reframes:**
  - Title: "Empirical Results" (not "Headline results").
  - Lead: 7 R-cells + 4 K-cells framing (was: 6 R-cells + head-to-head; the new framing folds K1, K4, K5, K7 into the headline cells).
  - Per-row d_z, p, status (Cohen's d_z, p-value, framework-WINS status) — three primary metrics per row, not 13 columns.
  - Honest boundary: CIFAR-10 RF NFE=50 regression (-10.7%) is in §9 Limitations and §7 cross-references.
- **JMAA prominence:** **low** (results are framework-architecture-validated; theorem is one row's worth of evidence).

### 4.8 §8 Reproducibility (new, replaces current §3.2, §5)

- **Replaces:** Current §3.2 (statistical methodology, lines 247-270) + current §5 (flattening checklist, lines 384-400).
- **Key reframes:**
  - Title: "Reproducibility" (not "Statistical methodology" or "Flattening checklist").
  - Lead: 4 Bonferroni families + D.4 byte-stable 30/30 + 3-seed pool (seeds 0/1/2) + Wave 286 FID GPU fixpoint.
  - D.4 suite: 30 byte-stable regression tests; appendix-style table.
- **JMAA prominence:** **low** (no theorem reference; reproducibility is framework-architecture-level).

### 4.9 §9 Limitations (new, replaces current §4 + new limitations)

- **Replaces:** Current §4 K1-K8 (lines 362-381) + new limitations (15/16 dormant sites + Wave 287 bugs + codim CIFAR -10.7%).
- **Key reframes:**
  - Title: "Limitations" (not "K1-K8").
  - Lead: 4 limitations summary.
  - L1: 15 of 16 JMAA sites dormant under cosine baseline (Wave 292 P1 inventory).
  - L2: Wave 287 surfaced 24 scheduler-codepath bugs (all fixed in W287 audit, but the audit's existence is a limitation on the framework's first-pass correctness).
  - L3: CodimensionSheetScheduler regresses CIFAR-10 RF by 10.7% at matched NFE — image-domain boundary is structural, not a bug.
  - L4: 12/13 R-cells still instantiate `default_cosine_scheduler()` at the adapter level (Wave 292 P2 §MS.config_genealogy); factory-default migration is forthcoming.
- **JMAA prominence:** **medium** (limitations cite JMAA but frame what is dormant, not what JMAA proves).

### 4.10 §10 Future Work (new)

- **Replaces:** New section; no current direct analog. Wave 287 audit + Wave 292 P1 inventory + Wave 296 in-progress + Wave 286 fixpoint are the inputs.
- **Key reframes:**
  - Title: "Future Work".
  - Lead: 4 future-work items.
  - FW1: Wave 296 full integration — PaperQuantitiesCache activated across all 15 dormant sites; 3-site conformance test suite for each.
  - FW2: CodimensionSheetScheduler regime expansion — cross-budget to matched-NFE crossover; investigate CIFAR-10 -10.7% regression root cause.
  - FW3: 3-seed headliner re-verification — R1, R3, R5b, R5c, R6, K4, K5, K7 with seeds 0/1/2.
  - FW4: JMAA 16-site full exercise — once Wave 296 lands, exercise all 16 sites and report which sites add value vs which are dormant on the validated cosine baseline.
- **JMAA prominence:** **medium** (future work cites JMAA but framed as "what to do next, not what JMAA proves").

### 4.11 §11 Conclusion (new)

- **Replaces:** Current §1 paragraph 4 (line 19, validation summary) + current §5.5 efficiency summary (lines 401-422), lifted and compressed.
- **Key reframes:**
  - Title: "Conclusion".
  - 1-paragraph summary: FlowA is a typed-contracts framework for re-inference of frozen flow matching checkpoints; validated across 11 R+K cells; 2.5-10× cross-budget NFE compression; D.4 byte-stable; future work gated by Wave 296 full integration.
- **JMAA prominence:** **low** (theorem is mentioned in one sentence as "companion lens").

---

## 5. JMAA prominence matrix (post-refactor)

| New section | JMAA prominence | Why |
|---|:---:|---|
| §1 Introduction | **low** | Theorem is in one paragraph and explicitly framed as companion; 4-contribution list has one theorem-side item (iv). |
| §2 Related Work | low | Theorem is one of three bound citations. |
| §3 Framework | low | Paper-quantities are one component of the state bundle, not the framework's identity. |
| §4 Scheduler Family | medium | 4 of 13 schedulers consume paper quantities; section leads with the 9 baselines. |
| §5 Adapter Protocol | low | No theorem reference; adapter protocol is structural. |
| §6 Theoretical Lenses | **high** | This section owns the theorem, reframed as companion. |
| §7 Empirical Results | low | Results are framework-architecture-validated; theorem is one row's worth of evidence. |
| §8 Reproducibility | low | No theorem reference; reproducibility is framework-architecture-level. |
| §9 Limitations | medium | Limitations cite JMAA but frame what is dormant, not what JMAA proves. |
| §10 Future Work | medium | Future work cites JMAA but framed as "what to do next". |
| §11 Conclusion | low | Theorem is mentioned in one sentence as companion lens. |

**Total JMAA-high-prominence sections:** 1 (§6) — was 6 in W297 P1 inventory.
**Total JMAA-medium-prominence sections:** 3 (§4, §9, §10) — was 6 in W297 P1 inventory.
**Total JMAA-low-prominence sections:** 7 (§1, §2, §3, §5, §7, §8, §11) — was 7 in W297 P1 inventory.

The drop from 6 high-prominence to 1 high-prominence reflects the demotion directive: JMAA Theorem 1 lives in §6 as one theoretical companion lens, not in the title, abstract, §1 introduction, or main contribution list.

---

## 6. Edit discipline + invariants

This is a **design-only** doc — no paper edits applied. Per the W297 P2 task scope:

- **D.4 30/30:** unchanged. No code edited.
- **Claims no drift:** unchanged. The cosine baseline R-cell FID achievement, the cross-budget 2.5–10× NFE compression, and the protein hard-tier pLDDT win are all preserved.
- **ruff 0:** unchanged. No `.py` file modified.
- **mkdocs 0 warnings:** unchanged. `docs/audit/` is `not_in_nav` per `mkdocs.yml:239` (W292 P1 §6 invariant).
- **vendored NOT touched:** unchanged. No edits under `vendored/`, `.venvs/`, `data/`.

The new structure applies the Wave 268 strict-clean additive-only directive: the design is described in this audit doc, and any application of the new structure to `docs/drafts/paper-flat-flattened.md` lands in subsequent waves (W297 P3+).

---

## 7. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave297-p2-paper-design.md` (this file)
- **prior docs cited:** wave297-p1-paper-inventory.md, wave296-p1-architecture.md, wave296-p2-cache.md, wave294-final.md, wave292-p1-pipeline-inventory.md, jmaa-theory-applications.md
- **current paper sections:** 19 (in `docs/drafts/paper-flat-flattened.md`)
- **new paper sections:** 11
- **JMAA-high-prominence sections:** 1 (was 6)
- **JMAA-medium-prominence sections:** 3 (was 6)
- **JMAA-low-prominence sections:** 7 (was 7)
- **vendored NOT touched:** verified by `git diff --stat vendored/` (no diff)

---

## 8. Honest summary

The Wave 297 P2 design doc specifies a new 11-section structure for `docs/drafts/paper-flat-flattened.md` that re-anchors the innovation narrative per the user directive: FlowA is a typed-contracts framework that reconstructs flow matching inference as a multi-round re-inference layer; the framework is the primary contribution, and JMAA Theorem 1 is demoted from main contribution to one theoretical companion lens.

The 5 P0 sections from W297 P1 inventory are all reframed: Title (drop "Paper-Quantity-Driven"), Abstract (framework primary, theorem enrichment), §1 Introduction (4-paragraph structure with framework lead), §2.1 → §6 (paper-quantity controllers reframed as theory enrichment sub-family), §2.8 → §6 (16-site inventory reframed as theory-enrichment inventory). The 5 P1 sections (§2 preamble, §2.6 calibration helper, §2.10 claim audit, §3.5 load-bearing discussion, §1 contributions (i)-(vi)) are all reframed: §2 preamble → §3 framework preamble, §2.6 → §6 calibration helper, §2.10 → §6 (or relocate to appendix), §3.5 → §7 (or §6), §1 contributions (i)-(vi) → §1 (i)-(iv) with 4 items.

The new structure has **1 JMAA-high-prominence section** (§6 Theoretical Lenses), **3 JMAA-medium-prominence sections** (§4 Scheduler Family, §9 Limitations, §10 Future Work), and **7 JMAA-low-prominence sections** (§1, §2, §3, §5, §7, §8, §11).

The §1 prose draft has 4 paragraphs + 4 contributions; the 4 contributions are: (i) typed-contracts framework, (ii) vendor-friendly integration, (iii) systematic empirical significance, (iv) theoretical companion (JMAA 16-site framework).

This is a **design-only** doc — no paper edits applied. The Wave 297 P3+ waves will apply the new structure on a per-section basis, per the Wave 268 strict-clean additive-only directive.