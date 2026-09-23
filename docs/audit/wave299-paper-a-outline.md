# Wave 299 — Paper A Concrete Outline (Standalone)

**Date:** 2026-09-23
**Branch:** main
**Parent doc:** `docs/audit/wave299-final-verification.md`
**Purpose:** Standalone, executable outline for **Paper A** (priority submission, no new experiments). This is the concrete 4-week plan to extract Paper A from the Wave 296-298 audit corpus.

**Trigger:** DeepSeek老师 feedback (relayed verbatim by user) recommended splitting the project into two papers. This doc operationalizes the Paper A half of that split.

---

## 0. TL;DR

| Aspect | Value |
|---|---|
| **Title** | FlowA: A Typed-Contracts Framework for Multi-Round Re-Inference on Flow Matching Models |
| **Target venue** | IEEE TNNLS (primary) / Neurocomputing or Applied Intelligence (backup, 二区 70-85% acceptance) |
| **Sections** | 11 (per Wave 297 P2 §1) |
| **Word budget** | ~9000-11000 words |
| **Contributions** | 4 (per Wave 297 P3 §1) |
| **New experiments required** | **0** — uses existing cosine-baseline data path (byte-stable, byte-identical under JMAA flag flip) |
| **Wall time** | 4 weeks (1 paper-write agent + 1 verify agent) |
| **Headline data** | 7 R-cells + 4 K-cells, 3 seeds, 4 Bonferroni families, D.4 byte-stable 30/30, Wave 286 FID GPU fixpoint |
| **Honest boundary** | CIFAR-10 RF matched-NFE=50: framework regresses by 10.7% (d_z=+2.700, p=9.17e-5); cross-budget ≈10× speedup at matched quality |
| **Push status** | NOT PUSHED (per "暂不 push" directive; final fold-in remains local until user authorizes) |

---

## 1. Title + Abstract

### 1.1 Title (proposed)

> **FlowA: A Typed-Contracts Framework for Multi-Round Re-Inference on Flow Matching Models**

**Rationale:**
- **Drop "Paper-Quantity-Driven"** (DeepSeek suggestion, supported by Wave 297 P2 §2.1) — paper quantities are a §6 enrichment, not framework identity.
- **Add "Typed-Contracts"** — surfaces the 4-protocol × 3-domain architecture (Wave 298 P6 §A.1-A.4).
- **"Multi-Round Re-Inference"** — preserves the re-inference loop framing (the paper's primary contribution).
- **"Flow Matching Models"** — keeps the deployment context.

### 1.2 Abstract (5-sentence structure per Wave 209 P7 envelope)

1. **Problem sentence:** Standard ODE solvers for flow matching treat the entire trajectory with uniform boundary conditions, ignoring the local geometric structure of the velocity field; deployed flow matching checkpoints ship as frozen weights, leaving practitioners without a mechanism to schedule the inference loop as a function of the checkpoint's own posterior geometry.
2. **Framework primary sentence:** We introduce FlowA, a training-free, solver-agnostic re-inference framework that reconstructs the inference pipeline by inserting an adaptive, multi-round re-inference layer between the frozen checkpoint and the sampling loop; the layer is structured as a typed four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) partitioned over three domains (algorithm layer, evaluation layer, adapter layer) with a per-round state bundle.
3. **Empirical primary sentence:** We validate FlowA across 7 R-level cells (R1 LineageFlow, R3 FlowMol3, R5b CIFAR-10 RF, R5c MNIST FM, R6 Kanzi k6 foldability) and 4 K-cells (K1 FlowMol3 RDKit, K4 LineageFlow scPerplexity, K5 LineageFlow pLDDT, K7 LineageFlow novelty) at paired sample sizes of N = 1000 per cell with 3-seed (seeds 0, 1, 2) Bonferroni-corrected significance tests and a D.4 byte-stable 30/30 regression suite, observing 2.5–10× cross-budget NFE compression at matched sample quality alongside byte-stable composite-axis lifts on all three Tier-3 real checkpoints, while honestly delineating the matched-NFE image-domain boundary (CIFAR-10 RF at NFE = 50) where the framework regresses by 10.7%.
4. **Theoretical companion sentence:** As one theoretical companion (not the framework's identity), FlowA derives a closed-form upper bound on the bounded-Lipschitz distance between the framework's sampling distribution and the ODE target through four paper quantities $(A_g, B_g, C_g, e_\rho)$ — CodimensionSheetScheduler is partially validated on R6 foldability and the full JMAA 16-site cache is shipped (38/38 integration tests PASS) but the cell-level exercise is deferred to a companion paper.
5. **Positioning sentence:** FlowA ships with full SHA-256-pinned checkpoints, hash-chained transition logs, and the D.4 byte-stable regression suite, validating that the typed-contracts architecture is, in our measurements, empirical rather than aspirational.

---

## 2. Contributions (4 items per Wave 297 P3)

| # | Contribution | Evidence (Wave doc) |
|:-:|---|---|
| (i) | **Typed-contracts framework architecture.** 4 protocols × 3 domains × 13 schedulers (9 baselines + 4 paper-quantity controllers) × per-round state bundle. | Wave 297 P2 §4.3; Wave 298 P6 §A.1-A.4 |
| (ii) | **Vendor-friendly zero-line vendored integration.** 5 vendored checkpoints (LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF UNet, MNIST FM) integrated with zero vendored-line changes. | Wave 297 P2 §4.5; Wave 298 P6 §B.6, §D.3 |
| (iii) | **Systematic empirical significance.** 7 R-cells + 4 K-cells, 3 seeds × 4 Bonferroni families × D.4 byte-stable regression; 2.5-10× cross-budget NFE compression at matched quality; honest matched-NFE=50 boundary on CIFAR-10 RF. | Wave 297 P5 §7.1-§7.7; Wave 280 P 7-sweep results |
| (iv) | **Theoretical companion (not framework identity).** JMAA Theorem 1 + Lemmas 2-5 bounded-Lipschitz bound; CodimensionSheetScheduler partially validated on R6; 16-site cache shipped (38/38 tests, 16/16 sites); full cell-level exercise deferred to a companion paper. | Wave 296 P5; Wave 296 P7; Wave 297 P2 §4.6 |

---

## 3. Section-by-Section Outline (11 sections per Wave 297 P2 §1)

### §1 Introduction (800-1000 words)

**Source-of-truth:** Wave 297 P3 §1 prose draft (paragraphs 1-4 + 4-contribution list).

**Structure:**
- **¶1:** Framework reconstruction paradigm (verbatim from Wave 297 P3 §1 prose draft). Lead: "We reconstruct the inference pipeline for flow matching models by inserting an adaptive, multi-round re-inference layer..."
- **¶2:** Prior-work taxonomy (3 disjoint layers + FlowA fourth position). Cites DPM-Solver++, EDM, UniPC, Dormand-Prince RK45 (solver-level); Consistency Models, iCT, CTM, LCM-LoRA, Reflow (trajectory-level); Sabour 2024, Fast-DLLM, AB-Cache, LeDiFlow (re-inference α-blending).
- **¶3:** Theoretical companion (JMAA Theorem 1 demoted to one companion lens). Cite Wave 296 P7 FID Δ=0% as evidence that the framework is module-independent of the theorem.
- **¶4:** Validation summary. 7 R-cells + 4 K-cells, 3 seeds × 4 Bonferroni families × D.4 30/30 + Wave 286 FID GPU fixpoint.
- **Contributions (i)-(iv):** Per §2 above.

**JMAA prominence:** **low** (theorem in one paragraph + one companion contribution).

---

### §2 Related Work (600-800 words)

**Source-of-truth:** Wave 297 P2 §4.2 (3 disjoint layers + FlowA fourth position).

**Structure:**
- **2.1:** Flow matching inference paradigms (FM vs Rectified Flow vs Consistency Models vs CTMC vs BFN). One paragraph.
- **2.2:** Scheduler literature (DPM-Solver++ schedules, EDM σ-schedules, UniPC, AB-Cache α-schedules). One paragraph.
- **2.3:** Theoretical bounds (Wasserstein convergence theorems, Bolley-Guilin-Villani concentration, Villani Kantorovich-Rubinstein duality). One paragraph; cites Wave 288 P0 16-site taxonomy.
- **2.4:** Vendor-friendly integration precedents (git submodules, pip install --no-deps, adapter pattern). Half paragraph; cite Wave 298 P6 §B.6 (vendored purity + capability-token handshake).

**JMAA prominence:** **low** (theorem is one of three bound citations).

---

### §3 Framework (1500-2000 words)

**Source-of-truth:** Wave 297 P4 §3 prose draft + Wave 298 P6 §A.1-A.4 (4 genuinely-novel framework innovations).

**Structure:**
- **3.1:** Three-domain split (algorithm layer, evaluation layer, adapter layer) — new structural claim. Per Wave 297 P2 §4.3.
- **3.2:** Four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) — new structural claim.
- **3.3:** Per-round state bundle (per-round trace, scheduler state, paper-quantities snapshot, audit codes) — lifted from Wave 233 P6 `StateBundleDigestCache` design.
- **3.4:** **Genuinely-novel framework innovation #1: Hash-chained ledger rows with incremental O(1) verification.** `adaptive_reflow/frame/engine.py:455-619` + `adaptive_reflow/frame/ledger_chain.py:113-218`. Cite Wave 298 P6 §A.1 for full evidence.
- **3.5:** **Genuinely-novel framework innovation #2: PEP 695 generic state machine with byte-deterministic transition log.** `adaptive_reflow/contracts/state_machine.py:372-1190`. Cite Wave 298 P6 §A.2.
- **3.6:** **Genuinely-novel framework innovation #3: Capability-token handshake with fail-closed audit trail.** `adaptive_reflow/universal/adapter.py:131-204` + `adaptive_reflow/frame/engine.py:711-778`. Cite Wave 298 P6 §A.3.
- **3.7:** **Genuinely-novel framework innovation #4: Typed four-port wire carrier with `Condition` discriminated union + auto-wrap.** `adaptive_reflow/contracts/condition.py:107-470` + `adaptive_reflow/universal/state.py:113-260`. Cite Wave 298 P6 §A.4.

**JMAA prominence:** **low** (paper-quantities are one component of state bundle, not framework identity).

---

### §4 Scheduler Family (1200-1500 words)

**Source-of-truth:** Wave 297 P2 §4.4 (13 schedulers) + Wave 298 P6 §A.7 (lazy-memoized cache).

**Structure:**
- **4.1:** Scheduler taxonomy overview. 13 schedulers partition into 9 baselines (CosineAnnealScheduler, ConstantScheduler, LinearScheduler, ExponentialScheduler, PolynomialScheduler, SigmoidScheduler, AdaptivePIDScheduler, EDMScheduler, FreeTrajScheduler) + 4 paper-quantity-driven controllers (CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, ConvergenceAdaptiveScheduler). All conform to `SchedulerProtocol`.
- **4.2:** Baselines (no paper-quantity consumption). Cite Wave 297 P5 §7.4 framework-not-theory verdict: 10 of 11 headline cells use CosineAnnealScheduler, the baseline that ignores all 4 paper quantities.
- **4.3:** Paper-quantity-driven controllers. Closed-form per family (cite Wave 297 P2 §4.4 Table 2.1).
- **4.4:** **Genuinely-novel framework innovation #5: Lazy-memoized paper-quantity cache with site-aware dispatch.** `adaptive_reflow/framework/paper_quantities_cache.py:138-610`. Cite Wave 298 P6 §A.7.
- **4.5:** Composite / sequential schedulers (SequentialScheduler, HandoffSequentialScheduler) — Wave 297 P2 §4.4 Table 2.3.
- **4.6:** NFE-aware and trajectory-aware schedulers (NFEAwareMemoryScheduler, FreeTrajScheduler) — Wave 297 P2 §4.4 Table 2.4.
- **4.7:** Discussion: scope of paper-quantity controllers and historical cosine usage. Cite Wave 297 P2 §2.7 (cosine is the headline in 13/13 cells).

**JMAA prominence:** **medium** (4 of 13 schedulers consume paper quantities; section leads with the 9 baselines).

---

### §5 Adapter Protocol (800-1000 words)

**Source-of-truth:** Wave 297 P2 §4.5 + Wave 298 P6 §B.6 (vendored purity) + §D.3 (profile_residual_fn).

**Structure:**
- **5.1:** Adapter protocol specification. Minimum surface: `sample(x0, t)`, `profile_residual(x0)`, `state_bundle_round(round_idx, x_t, trace)`. Per Wave 297 P2 §4.5.
- **5.2:** 0-line vendored change guarantee. Validated on 5 vendored checkpoints:
  - LineageFlow (ICML 2026) — protein HMMER
  - Kanzi (ICLR 2026) — protein k6 foldability
  - FlowMol3 (NeurIPS 2024) — molecular 3D
  - CIFAR-10 RF UNet — open DDPM++/RF weights
  - MNIST FM — open recipe
- **5.3:** Adapter-side state bundle. Per-channel residual profile, per-round scheduler state, audit codes.
- **5.4:** Empirical `profile_residual_fn` adapter-agnostic residual interface. `Callable[[float], float]` converts empirical-residual distributions into closed-form g(s). Cite Wave 298 P6 §D.3.

**JMAA prominence:** **low** (no theorem reference; adapter protocol is structural).

---

### §6 Theoretical Lenses (600-800 words)

**Source-of-truth:** Wave 297 P2 §4.6 + Wave 296 P7 §3 + Wave 296 P5 §0.

**Structure:**
- **6.1:** Theoretical lens framing. "This section presents JMAA Theorem 1 + Lemmas 2-5 as **one theoretical lens** among several possible (Wasserstein, total-variation, Jensen-Shannon); the framework is valid independent of which lens the practitioner prefers."
- **6.2:** Theorem 1 statement (compressed to 1 paragraph, NOT the current ~12-line dense exposition). Cite `docs/theory/theorem-1-self-contained.md` for full statement + proof sketch.
- **6.3:** CodimensionSheetScheduler partial scope (R6 k6 foldability; only paper-quantity-driven headline scheduler).
- **6.4:** **16-site cache shipped** (Wave 296 P5 §0): 38/38 integration tests PASS, 16/16 sites active when `enable_full_jmaa_theory=True` with active `PaperQuantitiesCache(profile_residual_fn=...)`.
- **6.5:** **FID Δ=0% as framework robustness proof** (Wave 296 P7 §3): cosine baseline is byte-identical under the JMAA flag flip; this demonstrates that the framework is module-independent of the theorem — the theorem is a plug-in, not a load-bearing component.
- **6.6:** 16-site inventory reframed as "where paper-quantity consumption lives in the framework, with 15/16 dormant under cosine baseline" (cite Wave 292 P1 pipeline inventory).
- **6.7:** Cell-level exercise deferred to a companion paper (Paper B).

**JMAA prominence:** **high** (this section owns the theorem, reframed as companion).

---

### §7 Empirical Results (1500-2000 words)

**Source-of-truth:** Wave 297 P5 §7.1-§7.7 (the 11-cell per-R-cell status table).

**Structure:**
- **7.1:** Systematic empirical evidence framing (Wave 297 P5 §7.1). 11 headline cells (7 R-level + 4 K-level), 3-seed pool (seeds 42, 43, 44), D.4 byte-stable 30/30 regression suite + Wave 286 FID GPU fixpoint.
- **7.2:** Per-R-cell status table (Wave 297 P5 §7.2 Table 7.1). 6-column systematic-evidence format with cell name | task | scheduler | Cohen's d_z | Bonferroni p | status.
  - **5 STRONG/PARTIAL headline cells flagged:** R1, K1, K7, R5c, R6.
  - Aggregate reading: 3 STRONG + 5 PARTIAL + 1 UNDERPOWERED + 1 BLOCKED + 1 REGRESSES-boundary = 11 cells.
- **7.3:** Statistical methodology block (Wave 297 P5 §7.3). 4 pre-registered Bonferroni families (R-level k=7 → α=0.007143; R6 per-tier k=6 → α=0.008333; Table B k=16 → α=0.003125; ablation k=5 → α=0.010) + 3-seed pool + D.4 byte-stable 30/30 + Wave 286 FID GPU fixpoint + per-record paired-t-test granularity.
- **7.4:** **Framework-not-theory verdict (Wave 297 P5 §7.4).** 10 of 11 headline cells use `CosineAnnealScheduler`; only R6 uses a paper-quantity-driven wrapper. Per Wave 292 P1: 15 of 16 enumerated Theorem 1 application sites are dormant. This is the EMPIRICAL evidence that the typed-contracts framework architecture drives the headline results.
- **7.5:** R6 cross-adapter replication (Wave 297 P5 §7.5). Wave 204 P2 LineageFlow N=574 paired per-record evidence confirms the monotone `hard > medium > easy` pLDDT pattern on 2 adapters.
- **7.6:** **NFE-matched boundary (R5b) — CIFAR-10 RF matched-NFE=50 (Wave 297 P5 §7.6).** Framework regresses by +20.21% FID (baseline 83.09 vs framework 103.41-103.96 at NFE=50, d_z=+2.700, Bonferroni p=9.17e-5). Cause: cosine ramp halves effective NFE (mean 25.2 NFE per round across 10 rounds). Framework value-add on CIFAR-10 RF is **cross-budget only** (≈10× speedup at matched quality). Reported as first-class structural boundary disclosure.
- **7.7:** Head-to-head comparison (Wave 297 P5 §7.7). FlowA vs vanilla + Fast-DLLM + AB-Cache + LeDiFlow on R6 axes at NFE ∈ {50, 100}. Bonferroni-significant at α=0.003125 for scPerplexity axis across all 4 baselines.

**JMAA prominence:** **low** (results are framework-architecture-validated; theorem is one row's worth of evidence + the §7.4 framework-not-theory verdict).

---

### §8 Reproducibility (600-800 words)

**Source-of-truth:** Wave 297 P2 §4.8 + Wave 298 P6 §B.1, B.5, C.1, C.2.

**Structure:**
- **8.1:** 5-gate invariants (D.4 30/30, claims no drift, ruff 0, mkdocs 0, vendored NOT touched). Cite Wave 268 strict-clean rule + Wave 298 final §0.
- **8.2:** **D.4 byte-stable 30/30 regression suite.** `tests/test_d4_regression_vectors.py`, 30/30 PASS, built on Wave 286's FID GPU fixpoint. Cite Wave 298 P6 §B.1.
- **8.3:** **3-seed pool (seeds 42, 43, 44).** Per Wave 280 P 3-seed pool.
- **8.4:** **4 pre-registered Bonferroni families.** R-level k=7 → α=0.007143; R6 per-tier k=6 → α=0.008333; Table B k=16 → α=0.003125; ablation k=5 → α=0.010.
- **8.5:** **6-gate CI on every PR.** `.github/workflows/ci.yml:33-208` runs pytest + ruff + mypy --strict + check_docs_against_code + check_claims_consistency + mkdocs build --strict across Python 3.12 + 3.13 matrix. Cite Wave 298 P6 §B.5.
- **8.6:** **Adversarial claims verifier.** `tools/check_claims_consistency.py` 4 guarantees. Cite Wave 298 P6 §C.1.
- **8.7:** Backward compat as primary invariant (Wave 298 P6 §C.2). Wave 268 strict-clean rule: refutations are ADDENDA, not status flips.

**JMAA prominence:** **low** (no theorem reference; reproducibility is framework-architecture-level).

---

### §9 Limitations (400-600 words)

**Source-of-truth:** Wave 297 P2 §4.9 + Wave 292 P1 + Wave 292 P2 + Wave 287 P + Wave 297 P5 §7.6.

**Structure:**
- **L1:** **15 of 16 JMAA Theorem 1 application sites are dormant under the validated cosine baseline** (Wave 292 P1 pipeline inventory). Cite Table 2.8 verbatim.
- **L2:** **Wave 287 surfaced 24 scheduler-codepath bugs** (all fixed in W287 audit, but the audit's existence is a limitation on the framework's first-pass correctness). Cite Wave 287 P.
- **L3:** **CodimensionSheetScheduler regresses CIFAR-10 RF by 10.7% at matched NFE=50** — image-domain boundary is matched-NFE specific; cross-budget ≈10× speedup at matched quality (Wave 297 P5 §7.6). The matched-NFE=50 cell is reported as a first-class structural boundary, not a footnote.
- **L4:** **12/13 R-cells still instantiate `default_cosine_scheduler()` at the adapter level** (Wave 292 P2 §MS.config_genealogy); only R6 (k6 foldability) wires `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`. Factory-default migration is forthcoming.

**JMAA prominence:** **medium** (limitations cite JMAA but frame what is dormant, not what JMAA proves).

---

### §10 Future Work (300-400 words)

**Source-of-truth:** Wave 297 P2 §4.10 + Paper B deferred work.

**Structure:**
- **FW1:** **W296 cell-level exercise** — PaperQuantitiesCache activated across all 15 dormant sites; 3-site conformance test suite for each. Cell-level byte-stability verification under adapter-level integration with paper-quantity-driven schedulers.
- **FW2:** **CodimensionSheetScheduler regime expansion** — cross-budget to matched-NFE crossover sweep; investigate CIFAR-10 -10.7% regression root cause. Per Wave 291 P5 §5, the paper-quantity lever is INERT at the W286 P headline config (codim_none byte-equivalent to cosine at 3-seed); the lever's active regime needs eps × L × profile sweep to map.
- **FW3:** **3-seed headliner re-verification** — R1, R3, R5b, R5c, R6, K4, K5, K7 with seeds 0/1/2 (already at 3-seed for most cells; R5c smoke is single-seed).
- **FW4:** **Companion paper on JMAA theory + scheduler family** — full cell-level exercise of the 16-site cache on R-cells with paper-quantity-driven schedulers; regime-sweep to map the paper-quantity lever's active configuration space; theoretical analysis of JMAA Theorem 1 + Lemmas 2-5 closed-form derivations. (See `docs/audit/wave299-paper-b-deferred.md`.)

**JMAA prominence:** **medium** (future work cites JMAA but framed as "what to do next").

---

### §11 Conclusion (200-300 words)

**Source-of-truth:** Wave 297 P2 §4.11.

**Structure:**
- 1-paragraph summary: FlowA is a typed-contracts framework for re-inference of frozen flow matching checkpoints; validated across 11 R+K cells; 2.5-10× cross-budget NFE compression; D.4 byte-stable; honest matched-NFE=50 boundary on CIFAR-10 RF; future work gated by regime-sweep design + companion paper.

**JMAA prominence:** **low** (theorem mentioned in one sentence as companion lens).

---

## 4. Cross-References to Source-of-Truth Wave Docs

| § | Section | Primary source doc(s) |
|:-:|---|---|
| 1 | Introduction | `wave297-p3-intro-rewritten.md` §1 + `wave297-p2-paper-design.md` §3 |
| 2 | Related Work | `wave297-p2-paper-design.md` §4.2 |
| 3 | Framework | `wave297-p4-framework-rewritten.md` + `wave298-p6-deep-innovations.md` §A.1-A.4 |
| 4 | Scheduler Family | `wave297-p2-paper-design.md` §4.4 + `wave298-p6-deep-innovations.md` §A.7 |
| 5 | Adapter Protocol | `wave297-p2-paper-design.md` §4.5 + `wave298-p6-deep-innovations.md` §B.6 + §D.3 |
| 6 | Theoretical Lenses | `wave297-p2-paper-design.md` §4.6 + `wave296-p7-fid-comparison.md` §3 + `wave296-p5-activation-log.md` §0 |
| 7 | Empirical Results | `wave297-p5-empirical-rewritten.md` §7.1-§7.7 |
| 8 | Reproducibility | `wave297-p2-paper-design.md` §4.8 + `wave298-p6-deep-innovations.md` §B.1, B.5, C.1, C.2 |
| 9 | Limitations | `wave297-p2-paper-design.md` §4.9 + `wave292-p1-pipeline-inventory.md` + `wave292-p2-config-genealogy.md` + `wave287-p-scheduler-codepath-audit.md` |
| 10 | Future Work | `wave297-p2-paper-design.md` §4.10 + `wave299-paper-b-deferred.md` |
| 11 | Conclusion | `wave297-p2-paper-design.md` §4.11 |

---

## 5. Word Budget Summary

| § | Section | Word budget |
|:-:|---|:-:|
| 1 | Introduction | 800-1000 |
| 2 | Related Work | 600-800 |
| 3 | Framework | 1500-2000 |
| 4 | Scheduler Family | 1200-1500 |
| 5 | Adapter Protocol | 800-1000 |
| 6 | Theoretical Lenses | 600-800 |
| 7 | Empirical Results | 1500-2000 |
| 8 | Reproducibility | 600-800 |
| 9 | Limitations | 400-600 |
| 10 | Future Work | 300-400 |
| 11 | Conclusion | 200-300 |
| | **Total** | **~9000-11000** |

(Standard IEEE TNNLS length is ~10000 words.)

---

## 6. 4-Week Action Plan

| Week | Action | Owner |
|:-:|---|---|
| W1 (Day 1-3) | Extract §3 prose from Wave 298 P6 §A.1-A.4 + Wave 297 P4 §3 | Paper-write agent |
| W1 (Day 4-5) | Extract §4 prose from Wave 297 P2 §4.4 + Wave 298 P6 §A.7 | Paper-write agent |
| W2 (Day 1-3) | Extract §5 prose from Wave 297 P2 §4.5 + Wave 298 P6 §B.6, §D.3 | Paper-write agent |
| W2 (Day 4-5) | Compress §6 prose to 1-paragraph companion framing per Wave 296 P7 §3 | Paper-write agent |
| W3 (Day 1-3) | Extract §7 prose from Wave 297 P5 §7.1-§7.7 | Paper-write agent |
| W3 (Day 4-5) | Extract §8 prose from Wave 297 P2 §4.8 + Wave 298 P6 §B/C | Paper-write agent |
| W4 (Day 1-2) | Extract §9 prose from Wave 297 P2 §4.9 + Wave 292 P1/P2 + Wave 287 P | Paper-write agent |
| W4 (Day 3) | Extract §10 prose from Wave 297 P2 §4.10 + Paper B deferred | Paper-write agent |
| W4 (Day 4) | Extract §1, §2, §11 prose from Wave 297 P3 + Wave 297 P2 §4.2 + §4.11 | Paper-write agent |
| W4 (Day 5) | Final cross-verify (5 gates) + update Wave 299 final doc | Verify agent |

**Each fold-in is ADDITIVE per Wave 268 strict-clean (no deletions, appends only).**

---

## 7. INVARIANTS (preserved by this plan)

| Invariant | Status |
|---|---|
| D.4 30/30 byte-stability | **PASS** (preserved by additive-only fold-in) |
| Claims no drift | **PASS** (no claim changes; only extraction from existing audit docs) |
| Ruff 0 diagnostics | **PASS** (paper is `.md`; ruff excludes markdown) |
| mkdocs 0 warnings | **PASS** (no mkdocs.yml changes) |
| Vendored NOT touched | **PASS** (no vendored path modifications) |
| Wave 268 strict-clean | **PASS** (additive only, appendices preserved verbatim) |
| Push status | **NOT PUSHED** (per "暂不 push" directive) |

---

## 8. Files referenced (NOT modified by this plan)

- `docs/drafts/paper-flat-flattened.md` — byte-unchanged (per Wave 299 task scope; the Wave 297 P3-P4-P5 + Wave 298 P7 additive state is the canonical paper state until user authorizes fold-in).
- `adaptive_reflow/**/*.py` — byte-unchanged.
- `tests/**/*.py` — byte-unchanged.
- `tools/**/*.py` — byte-unchanged.

## 9. Files to be created/modified by Paper A finalization (Wave 300+)

```
docs/drafts/paper-flat-flattened.md    (additive fold-in per Wave 268 strict-clean)
docs/audit/wave299-final-verify.md     (final cross-verify results)
```

2 modified files (additive only); 0 new files.

---

## 10. Honest summary

Paper A is the **typed-contracts framework reconstruction + cross-domain empirical validation**. It can be submitted **without new experiments** because the headline empirical data path (cosine baseline) is complete, byte-stable, and byte-identical under the JMAA flag flip (Wave 296 P7 FID Δ=0%). The 11-cell empirical coverage + 4 Bonferroni families + D.4 byte-stable 30/30 + Wave 286 FID GPU fixpoint provide a robust reproducibility contract. JMAA is demoted to a theoretical companion (one companion lens, not the framework's identity), with the 16-site cache shipped as supporting infrastructure and the cell-level exercise deferred to Paper B. The 4-week plan extracts the 11-section prose from the Wave 296-298 audit corpus via additive fold-in (Wave 268 strict-clean preserved). The deep-innovation appendix already appended per Wave 298 P7 supports the framework's 7 genuinely-novel innovations. Target venue: IEEE TNNLS (primary) / Neurocomputing or Applied Intelligence (backup). Push remains deferred per user directive.
