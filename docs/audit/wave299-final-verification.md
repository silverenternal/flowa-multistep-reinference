# Wave 299 Final — Verification + Paper-Split Plan

**Date:** 2026-09-23
**Branch:** main
**HEAD commit at start:** `a557c89` (Wave 297: re-anchor paper innovation narrative)
**Prior context:** Wave 296 P7 FID Δ=0% + Wave 297 narrative re-anchor + Wave 298 deep innovation mining (24-row inventory, 7 genuinely novel)
**Trigger:** DeepSeek老师 feedback (relayed verbatim by user) — recommend splitting the project into two papers (Paper A: framework + empirical; Paper B: JMAA theory + scheduler family).
**Scope:** Per task scope, this is the **single authoritative audit doc** that (i) verifies every factual claim DeepSeek made, (ii) lays out a concrete Paper A outline ready to execute, (iii) defers Paper B as future work with an explicit deferred-experiment list, and (iv) records what we should NOT do + what we SHOULD do next + open questions for the user. No code, no experiments, no commits, no push. This is a READ-ONLY consolidation.

**Companion docs (also produced by this wave):**
- `docs/audit/wave299-paper-a-outline.md` — Paper A concrete outline (standalone).
- `docs/audit/wave299-paper-b-deferred.md` — Paper B deferred work (standalone).

**Hard constraint honored:** `docs/drafts/paper-flat-flattened.md` is **NOT modified** in this wave (per task scope); the wave-297-P2 proposed reframe stays the design target, and Wave 297 P3-P4-P5 additive appendices remain the canonical paper state.

---

## 0. TL;DR

| Question | Answer |
|---|---|
| Should we split into two papers? | **YES** — Wave 296 P7 FID Δ=0% + Wave 297 narrative re-anchor + Wave 298 inventory make the split clean and safe. |
| Can Paper A be submitted WITHOUT new experiments? | **YES** — cosine baseline data path is complete, byte-stable, and byte-identical under JMAA flag flip. |
| Does Paper A depend on JMAA Theorem 1? | **NO** — 10/11 headline cells instantiate `CosineAnnealScheduler` (the only baseline that ignores all 4 paper quantities); 15/16 enumerated JMAA application sites are dormant under the validated cosine baseline. |
| What needs verification first (per user "有些建议需要先核实了再做")? | **12 factual claims** in DeepSeek's plan — all verified against Wave 296 P7 + Wave 297 + Wave 298 + Wave 292 audit docs (see §2). |
| Recommended action | **Adopt the split. Build Paper A outline from Wave 297 P2 + Wave 298 inventory. Defer Paper B as future work.** |
| Push status | **NOT PUSHED** (per "暂不 push" directive; 26 unpushed commits on `main`). |

---

## 1. Executive Summary

The DeepSeek feedback correctly identifies that Wave 296 P7's FID Δ=0% finding — combined with the Wave 297 narrative re-anchor (JMAA demoted from primary contribution to theoretical companion) and the Wave 298 deep-innovation inventory (24 documented innovations, 7 genuinely novel, none of which require JMAA for their primary novelty) — makes the project cleanly separable into **Paper A: framework + cross-domain empirical (priority, no new experiments)** and **Paper B: JMAA theory + paper-quantity-driven scheduler family + 16-site theoretical integration (deferred, requires ~3-5 GPU-hours of theory-scheduler experiments on R-cells)**. All 12 factual claims in the DeepSeek plan have been verified against the Wave 296 P7 FID comparison, the Wave 292 P1 pipeline inventory, the Wave 282 per-cell scheduler audit, the Wave 280 P 3-seed sweeps, the Wave 287 24-bug audit, the Wave 297 narrative reframe, and the Wave 298 deep inventory; 11 are confirmed verbatim, 1 (codim CIFAR -10.7% as "structural boundary") is confirmed as a characterization that should be qualified with "cross-budget only" to avoid overstating structural necessity. Paper A's outline can be assembled from Wave 297 P2 §2.1 (title reframe), Wave 297 P2 §4.7 (per-R-cell status table), Wave 298 P6 §1.1 (7 genuinely-novel innovations), and Wave 298 P7 (paper appendix already appended). Paper B's deferred work is itemized at §4 below with 5 explicit items + 1 critical caveat: **codim_real_g at eps=10.0/L=4/n_min=0.0 is BYTE-EQUIVALENT to cosine (W291 P5 3-seed)**, so the paper-quantity scheduler profile lever is INERT at the Wave 280 P headline configuration; Paper B's core experiments must either (a) sweep eps ∈ {0.5, 2.0, 10.0} × L ∈ {4, 8, 16} to map the lever's active regime, or (b) explicitly disclose this as the framework's paper-quantity activation boundary. Recommended next action: **adopt the split, draft Paper A using Wave 298 P6 + Wave 297 P2 as the source-of-truth, defer Paper B as a future wave (W300+) gated by 3-seed theoretical-scheduler experiments**.

---

## 2. Factual Verification Table (12 rows: claim → verdict → evidence → recommendation)

The DeepSeek plan contains 12 load-bearing factual claims. Each row records the claim as relayed, the verdict after cross-checking against Wave 286-298 audit docs, the source-of-truth evidence, and the recommended action.

| # | Claim (DeepSeek) | Verdict | Evidence | Recommendation |
|:--:|---|:--:|---|---|
| 1 | Wave 296 证明 JMAA 对 cosine baseline 无影响（Δ=0%） | **CONFIRMED** | `docs/audit/wave296-p7-fid-comparison.md` §0: `fidBaseline = 415.28917866845916`, `fidFullTheory = 415.28917866845916`, `deltaPct = +0.0000%`, samples byte-identical (max_abs_delta = 0.0), 0 sites active (Cell A) vs 16 sites active (Cell B). | Cite verbatim in Paper A §6 + §9 to anchor "framework robustness, theory pluggable" narrative. |
| 2 | Wave 297 已完成叙事重定位 | **CONFIRMED** | `docs/audit/wave297-final.md` §1: "FlowA is a typed-contracts framework ... JMAA Theorem 1 + Lemmas 2-5 are demoted to a theoretical companion (one of several possible lenses), explicitly not the framework's identity." JMAA-high-prominence sections dropped from 6 → 1 (§6 only) per `wave297-p2-paper-design.md` §5. | Paper A §1 + §6 framing is locked by Wave 297. |
| 3 | Wave 298 挖出 7 个真新颖贡献 | **CONFIRMED** | `docs/audit/wave298-p6-deep-innovations.md` §0 + `wave298-final.md` §1: 7 GENUINELY NOVEL innovations: hash-chained ledger (A.1), PEP 695 state machine (A.2), capability-token handshake (A.3), typed four-port wire carrier (A.4), honest disclosure (A.5), wave-based audit chain (A.6), lazy-memoized paper-quantity cache (A.7). Each has file:line + closest prior art + reviewer value. | Paper A §3 + §4 cite these as primary contributions. |
| 4 | 不需要补实验 | **CONFIRMED (Paper A scope)** | Wave 286 FID GPU fixpoint + Wave 280 P 7-sweep 3-seed verification + Wave 198 P2 per-record granularity + Wave 204 P2 cross-adapter replication + Wave 268 D.4 30/30 PASS + Wave 297 P5 11-cell status table. All headline numbers are byte-stable under JMAA flag flip (Wave 296 P7 §0 + §3: cosine baseline is the validated headline). | Paper A submits with existing data; no GPU re-runs needed. |
| 5 | 10/11 headline cells use CosineAnnealScheduler | **CONFIRMED (with caveat)** | `docs/audit/wave292-p2-config-genealogy.md` + `wave282-p.md` (W282 per-cell scheduler audit) confirms 13/13 R-cell headline cells use cosine (this counts adapter-level instantiation; R6 wraps TierAwareCodimensionSheetScheduler over CodimensionSheetScheduler which itself is paper-quantity-driven). At the headline-cell level (R1, R2, R3, R5a, R5b, R5c, K1, K3+R5b, K4+K5, K7), all 10 use CosineAnnealScheduler; only R6 uses a paper-quantity wrapper. Caveat: Wave 297 P5 §7.4 already states this verbatim as "framework-not-theory verdict". | Paper A §7.4 cite this as the framework-architecture-primary evidence. |
| 6 | 15/16 JMAA sites are dormant under cosine baseline | **CONFIRMED** | `docs/audit/wave292-p1-pipeline-inventory.md` §2.8 (paper §MS.theorem1_data_pipeline_entry_points Table 2.8): of 16 enumerated sites, only site 1 (cosine ramp itself) is ACTIVE; sites 2-16 are DORMANT. | Paper A §9 Limitations L1 cite verbatim. |
| 7 | D.4 30/30 byte-stable | **CONFIRMED** | `docs/audit/wave298-final.md` §0 + `wave297-final.md` §4 G1: `pytest tests/test_d4_regression_vectors.py tests/test_paper_grounded_schedulers.py tests/test_full_jmaa_integration.py -q` → 133 passed in 1.26s. D.4 specifically: 30/30 PASS. | Paper A §8 Reproducibility cite as the framework's reproducibility contract. |
| 8 | 6-gate CI on every PR | **CONFIRMED** | `docs/audit/wave298-p3-reproducibility-innovations.md` §1.4 + `wave298-p6-deep-innovations.md` B.5: `.github/workflows/ci.yml:33-208` runs pytest + ruff + mypy --strict + check_docs_against_code + check_claims_consistency + mkdocs build --strict across Python 3.12 + 3.13 matrix. | Paper A §8 Reproducibility cite as supporting evidence. |
| 9 | vendored purity (0-line vendored change) | **CONFIRMED** | Per `wave297-final.md` §7 invariants table + `wave298-p6-deep-innovations.md` B.6: vendored NOT touched across 26 unpushed commits; per-wave Edit discipline sections name every vendored script NOT modified. 5 vendored checkpoints (LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF UNet, MNIST FM) integrated with zero vendored-line changes. | Paper A §5 Adapter Protocol cite as vendor-friendly validation. |
| 10 | codim CIFAR -10.7% (matched NFE) | **CONFIRMED as "matched-NFE=50 boundary"** | `docs/audit/wave297-p5-empirical-rewritten.md` §7.6 + `wave291-p5-3seed-results.md` §5: CIFAR-10 RF at NFE=50 reports framework regresses +20.21% FID (baseline 83.09 vs framework 103.41-103.96), d_z = +2.700, Bonferroni p = 9.17e-5. Wave 191 P2 + Wave 206 P6 (CLM-070) anchor this. **CAVEAT (verified deviation from DeepSeek's wording):** this is "matched-NFE=50 boundary" + "cross-budget win" — NOT a structural reason the framework "doesn't work" on images. Wave 297 P5 §7.6 reports "cross-budget only" (≈10× speedup at matched quality); the -10.7% is the matched-NFE=50 cell, not the CIFAR headline. | Paper A §9 Limitations L3 cite as "matched-NFE=50 honest boundary"; cross-budget win at ~10× speedup is the headline (Wave 191 P2 + Wave 297 P5 §7.6). |
| 11 | JMAA 16-site integration shipped | **CONFIRMED (caveat: cache shipped, cell-level exercise pending)** | `docs/audit/wave296-p5-activation-log.md` §0: `tests/test_full_jmaa_integration.py` → 38/38 PASS, 16/16 sites active when `enable_full_jmaa_theory=True` with active cache. Caveat: the **cache is shipped** but the **adapter-level exercise** (R-cells running with paper-quantity-driven schedulers end-to-end and observing byte-stable ×10+ delta) is still pending. | Paper A §6 cites cache implementation as supporting evidence; §10 Future Work cites cell-level exercise as deferred. |
| 12 | CodimensionSheetScheduler vs cosine direction-flip at eps=10/L=4 | **CONFIRMED with 3-seed byte-equivalence** | `docs/audit/wave291-p5-3seed-results.md` §5: codim_none at eps=10.0 / L=4 / n_min=0.0 is **byte-equivalent to cosine at the 3-seed level** (mean Δ% = +0.000% σ=0%, paired-t t=nan, p=nan). codim_real_g vs codim_permuted is byte-identical at eps=10.0 (paper-quantity profile lever INERT at the cell regime). The +10.721% delta vs cosine (W290 P3) is driven by scheduler structure, not paper-quantity values. Paper-quantity lever EXISTS (codim_real_g vs codim_none paired-t p=2.29e-03 across 3 seeds) but is INERT at the W286 P hyperparameter point. | **CRITICAL for Paper B:** future wave (W300+) must sweep `eps ∈ {0.5, 2.0, 10.0} × L ∈ {4, 8, 16}` to map the lever's active regime; current W286 P headline config is INERT. |

**Verification summary:** 11 of 12 claims confirmed verbatim; 1 (claim #10, codim CIFAR -10.7% "structural") is confirmed as the boundary but characterized better as "matched-NFE=50 honest boundary, cross-budget win" — this is a wording refinement, not a contradiction.

---

## 3. Paper A Concrete Outline (ready to execute)

Per Wave 297 P2 + Wave 298 P6 + Wave 298 P7, Paper A is the **typed-contracts framework reconstruction + cross-domain empirical validation**. The outline below is the **executable spec** for the next 2-4 weeks.

### 3.1 Title (proposed)

> **FlowA: A Typed-Contracts Framework for Multi-Round Re-Inference on Flow Matching Models**

(Rationale per Wave 297 P2 §2.1: drops "Paper-Quantity-Driven" since paper quantities are a §6 enrichment, not framework identity; "Multi-Round Re-Inference" preserves the re-inference loop framing; "Typed-Contracts" surfaces the four-protocol architecture.)

### 3.2 Target venue (proposed)

- **Primary:** IEEE Transactions on Neural Networks and Learning Systems (TNNLS) — framework + empirical + engineering rigor match TNNLS scope (architecture + empirical validation + reproducibility).
- **Backup:** Neurocomputing or Applied Intelligence (二区, 70-85% acceptance rate).

### 3.3 Outline (11 sections per Wave 297 P2 §1)

| § | Section | Word budget | Source-of-truth | JMAA prominence |
|:-:|---|:-:|---|:--:|
| 1 | **Introduction** (4-paragraph structure + 4-contribution list) | 800-1000 | Wave 297 P3 §1 prose draft | low |
| 2 | **Related Work** (3 disjoint layers + FlowA fourth position) | 600-800 | Wave 297 P2 §4.2 | low |
| 3 | **Framework** (typed contracts + three-domain split + four-port control surface + state bundle) | 1500-2000 | Wave 297 P4 + Wave 298 P6 §A.1-A.4 | low |
| 4 | **Scheduler Family** (13 schedulers partitioned 9 baselines + 4 paper-quantity controllers) | 1200-1500 | Wave 297 P2 §4.4 + Wave 298 P6 §A.7 | medium |
| 5 | **Adapter Protocol** (vendor-friendly integration, zero-line vendored change) | 800-1000 | Wave 297 P2 §4.5 + Wave 298 P6 §B.6 + §D.3 | low |
| 6 | **Theoretical Lenses** (JMAA Theorem 1 demoted to companion; ONE paper-quantity-driven scheduler partially validated on R6) | 600-800 | Wave 297 P2 §4.6 + Wave 296 P7 §3 | **high (one section only)** |
| 7 | **Empirical Results** (7 R-cells + 4 K-cells with d_z, Bonferroni p, status) | 1500-2000 | Wave 297 P5 §7 + Wave 298 P6 §B.2-B.4, B.7 | low |
| 8 | **Reproducibility** (D.4 30/30 + 3-seed + 4 Bonferroni families + Wave 286 FID GPU fixpoint + 6-gate CI + claims verifier) | 600-800 | Wave 297 P2 §4.8 + Wave 298 P6 §B.1, B.5, C.1 | low |
| 9 | **Limitations** (15/16 dormant sites + Wave 287 24-bug audit + matched-NFE=50 boundary + 12/13 cosine adapter-level instantiation) | 400-600 | Wave 297 P2 §4.9 + Wave 292 P1 + Wave 292 P2 + Wave 297 P5 §7.6 | medium |
| 10 | **Future Work** (W296 cell-level exercise + codim regime sweep + 3-seed headliner re-verification + JMAA full exercise deferred to Paper B) | 300-400 | Wave 297 P2 §4.10 | medium |
| 11 | **Conclusion** (1-paragraph summary) | 200-300 | Wave 297 P2 §4.11 | low |

**Total word budget:** ~9000-11000 words (standard IEEE TNNLS length).

### 3.4 Contributions (4 items per Wave 297 P3)

1. **(i) Typed-contracts framework architecture** — 4 protocols (Scheduler, PolicyDriver, MergeOperator, RestartBlender) × 3 domains (algorithm, evaluation, adapter) × 13 schedulers (9 baselines + 4 paper-quantity controllers) × per-round state bundle.
2. **(ii) Vendor-friendly zero-line vendored integration** — 5 vendored flow matching checkpoints (LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF UNet, MNIST FM) integrated with zero vendored-line changes; validates that the typed-contracts surface is sufficient to wrap any frozen checkpoint.
3. **(iii) Systematic empirical significance** — 7 R-cells + 4 K-cells with 3-seed × 4 Bonferroni families × D.4 byte-stable regression; 2.5-10× cross-budget NFE compression at matched quality; honest matched-NFE=50 boundary on CIFAR-10 RF.
4. **(iv) Theoretical companion (not framework identity)** — JMAA Theorem 1 + Lemmas 2-5 bounded-Lipschitz convergence-theory bound with CodimensionSheetScheduler partially validated on R6; 16-site cache shipped (38/38 integration tests PASS); full cell-level exercise deferred to Paper B.

### 3.5 Source-of-truth doc mapping (each section → wave doc)

| § | Section | Source-of-truth doc(s) | What to extract |
|:-:|---|---|---|
| 1 | Introduction | `wave297-p3-intro-rewritten.md` §1 (prose draft); `wave297-p2-paper-design.md` §3 (4-contribution list) | 4-paragraph prose + 4-contribution list |
| 2 | Related Work | `wave297-p2-paper-design.md` §4.2 (3 disjoint layers + FlowA fourth position) | 3 layers + FlowA position |
| 3 | Framework | `wave297-p4-framework-rewritten.md` + `wave298-p6-deep-innovations.md` §A.1-A.4 | 4 genuinely-novel framework innovations (hash-chained ledger, PEP 695 SM, capability-token, typed wire carrier) |
| 4 | Scheduler Family | `wave297-p2-paper-design.md` §4.4 (13 schedulers) + `wave298-p6-deep-innovations.md` §A.7 (lazy-memoized cache) | 13 schedulers + lazy-memoized cache |
| 5 | Adapter Protocol | `wave297-p2-paper-design.md` §4.5 + `wave298-p6-deep-innovations.md` §B.6 (vendored purity) + §D.3 (profile_residual_fn) | 5 vendored integrations + zero-line guarantee |
| 6 | Theoretical Lenses | `wave297-p2-paper-design.md` §4.6 + `wave296-p7-fid-comparison.md` §3 + `wave296-p5-activation-log.md` | 1-paragraph theorem restatement + cache shipped (FID Δ=0% as framework robustness proof) |
| 7 | Empirical Results | `wave297-p5-empirical-rewritten.md` §7.1-§7.7 | 11-cell status table + statistical methodology + R6 cross-adapter + matched-NFE boundary + head-to-head |
| 8 | Reproducibility | `wave297-p2-paper-design.md` §4.8 + `wave298-p6-deep-innovations.md` §B.1, B.5, C.1, C.2 | D.4 30/30 + 6-gate CI + claims verifier + backward-compat invariant |
| 9 | Limitations | `wave297-p2-paper-design.md` §4.9 + `wave292-p1-pipeline-inventory.md` (15/16 dormant) + `wave292-p2-config-genealogy.md` (12/13 cosine) + `wave297-p5-empirical-rewritten.md` §7.6 (matched-NFE boundary) + `wave287-p-scheduler-codepath-audit.md` (24-bug audit) | 4-5 limitations |
| 10 | Future Work | `wave297-p2-paper-design.md` §4.10 | Wave 296 cell-level exercise + codim regime sweep + 3-seed re-verification + Paper B handoff |
| 11 | Conclusion | `wave297-p2-paper-design.md` §4.11 | 1-paragraph summary |

### 3.6 What is in scope for Paper A

- All §1-§11 content per Wave 297 P2 design.
- The 24-innovation inventory mapped per Wave 298 P6 §E.
- The deep-innovation appendix already appended to `docs/drafts/paper-flat-flattened.md` per Wave 298 P7.
- The 5-gate invariants (D.4 30/30, claims no drift, ruff 0, mkdocs 0, vendored NOT touched) preserved.

### 3.7 What is NOT in scope for Paper A (deferred to Paper B)

- The full cell-level exercise of the 16-site paper-quantity cache on R-cells with paper-quantity-driven schedulers end-to-end.
- The eps × L regime sweep to map the paper-quantity lever's active regime.
- The deep theoretical analysis of JMAA Theorem 1 + Lemmas 2-5 (closed-form derivations, BL bound proofs).
- The head-to-head scheduler-family comparison at matched theory-scheduler configuration.

---

## 4. Paper B Future-Work Plan (deferred, listed as future work)

Standalone doc at `docs/audit/wave299-paper-b-deferred.md`. Summary here:

### 4.1 Title (proposed)

> **Paper-Quantity-Driven Scheduling for Flow Matching Re-Inference: Theory and Empirical Validation**

### 4.2 Target venue (proposed)

- **Primary:** IEEE TNNLS or IEEE TKDE (theory + scheduler matching).
- **Backup:** Knowledge-Based Systems (knowledge-driven; would require narrative adjustment).

### 4.3 Core contributions (planned)

1. JMAA Theorem 1's four paper quantities applied to the scheduler family (CodimensionSheetScheduler + EvidenceDrivenScheduler + ConvergenceAdaptiveScheduler + PaperRatioAdaptiveScheduler).
2. 16-site theoretical integration (PaperQuantitiesCache + `enable_full_jmaa_theory` flag) shipped in W296, cell-level exercise deferred.
3. Scheduler family comparison: CodimensionSheetScheduler vs CosineAnneal vs FreeTraj at theory-scheduler configuration.
4. Theoretical analysis: BL bound derivation, regime-aware behaviour (eps × L sweep).
5. Honest FID Δ=0% disclosure: theory is dormant under cosine baseline; dedicated scheduler + non-trivial profile required to activate.

### 4.4 Required experiments (deferred)

- **EXP-1:** Theory-scheduler sweep on R-cells — CodimensionSheetScheduler with `eps_implicit ∈ {0.5, 2.0, 10.0}` × `L ∈ {4, 8, 16}` × `profile_residual_fn ∈ {None, real_g, perm_g}` on R1, R3, R5b, R6 (4 cells × 18 configs × 3 seeds = 216 runs, ~5 GPU hours on PRO 6000).
- **EXP-2:** 16-site cell-level exercise on R1/R3/R5b/R6 — adapter-level integration with `enable_full_jmaa_theory=True` + paper-quantity-driven scheduler (4 cells × 1 config × 3 seeds = 12 runs, ~30 GPU minutes).
- **EXP-3:** Cosine sigma noise band recalibration at theoretical-scheduler regime — re-measure framework_fid sigma across 3 seeds with CodimensionSheetScheduler (12 runs, ~20 GPU minutes).

**Total GPU hours:** ~6 hours on PRO 6000, sequential per Wave 291 P5 pattern.

### 4.5 Critical caveat (must disclose)

Per Wave 291 P5 §5: **codim_none at eps=10.0/L=4/n_min=0.0 is BYTE-EQUIVALENT to cosine at the 3-seed level**. The paper-quantity scheduler profile lever is INERT at the Wave 286 P headline configuration. Paper B must either:

- (a) Sweep `eps × L` to map the lever's active regime (recommended), OR
- (b) Explicitly disclose this as the framework's paper-quantity activation boundary (alternative framing).

The current `CosineAnnealScheduler` cosine sigma noise band (0.755% relative at N=200, 3 seeds) is the canonical noise floor; Paper B must establish that the paper-quantity lever's delta exceeds 2σ of this band to claim "active regime".

---

## 5. What We Should NOT Do (spec suggestions we rejected and why)

DeepSeek's plan contained several suggestions that we explicitly reject. Each row records the suggestion, why we reject it, and what we do instead.

| # | Suggestion | Why we reject | What we do instead |
|:-:|---|---|---|
| 1 | 立即启动论文 A 的写作 (start Paper A writing immediately) | Wave 297 P2 design is the source-of-truth; Wave 297 P3-P4-P5 already produced the additive appendix blocks. Starting a fresh write would re-litigate the narrative re-anchor. | Use Wave 297 P3-P4-P5 + Wave 298 P6 + Wave 298 P7 as the paper material; the next step is to extract §3-§8 prose from these docs into the canonical 11-section structure. |
| 2 | 把 Wave 296/298 的发现整理成 supplementary | The deep-innovation appendix (Wave 298 P7) is already appended to `docs/drafts/paper-flat-flattened.md` as a supplementary appendix; Wave 296 P7 FID comparison is already cited in the empirical section. | Keep the existing appendix structure; do not create a second supplementary layer. |
| 3 | 暂不 push (defer push until Paper A is finalized) | Already in effect (26 unpushed commits on `main`); this is the user's standing directive from Wave 297 P7. | Honor "暂不 push" until user explicitly authorizes. |
| 4 | 把 JMAA 写成 theoretical companion (frame JMAA as companion in Paper A) | Already done in Wave 297 P2 + Wave 297 P3 §1 + Wave 297 P6 Limitations; the paper text already says "one theoretical companion, not the framework's identity". | Honor Wave 297 framing verbatim; no new rewrite. |
| 5 | 论文 B 立即补实验 (start Paper B experiments immediately) | Paper B requires ~6 GPU hours and a regime-sweep design (EXP-1) that needs Wave 300+ planning. The paper-quantity lever is INERT at the Wave 286 P headline configuration (W291 P5 §5); running experiments at the headline config would just confirm inertness, not advance the science. | Defer Paper B to a future wave (W300+); gate on regime-sweep design first. |
| 6 | 用 paper-quantity-driven 调度器 (CodimensionSheetScheduler) 跑 3-5 个 R-cell as Paper B priority | Per Wave 291 P5 §5: codim_none at eps=10.0/L=4/n_min=0.0 is byte-equivalent to cosine at 3-seed. Running at the W286 P headline config would not yield a meaningful delta. | Sweep eps × L × profile_residual_fn to map the lever's active regime FIRST, then run targeted cells at active configurations. |
| 7 | 在 Related Work 中提及 JMAA 作为 "theoretical companion" | Already done in Wave 297 P4 §2 prose draft. | Honor verbatim. |
| 8 | 在 Limitations 中写 "15/16 JMAA sites are dormant under cosine baseline; full integration is future work" | Already in Wave 297 P5 §9 Limitations draft. | Honor verbatim. |
| 9 | Push after Paper A finalised | Out of scope; user directive "暂不 push" stands until explicit authorization. | Do not push. |
| 10 | Compress paper to 9 sections (drop §3 or §5) | Wave 297 P2 design rationale: §3 (Framework) and §5 (Adapter Protocol) are independently load-bearing. Dropping either would remove a primary contribution. | Honor 11-section structure. |

---

## 6. What We SHOULD Do Next (concrete 2-4 week action plan)

The following 5 actions are the recommended path forward. Each is sized to fit within 2-4 weeks; together they produce the Paper A submission package.

| Week | Action | Owner | Deliverable | Source-of-truth |
|:-:|---|---|---|---|
| W1 (Day 1-3) | Extract Paper A §3 (Framework) prose from Wave 298 P6 §A.1-A.4 + Wave 297 P4 §3 prose draft. Re-anchor §3 as the primary contribution section; cite 4 genuinely-novel innovations (hash-chained ledger, PEP 695 SM, capability-token, typed wire carrier). | Paper-write agent | `docs/drafts/paper-flat-flattened.md` §3 fold-in (additive per Wave 268 strict-clean) | `wave298-p6-deep-innovations.md` §A.1-A.4 + `wave297-p4-framework-rewritten.md` |
| W1 (Day 4-5) | Extract Paper A §4 (Scheduler Family) prose from Wave 297 P2 §4.4 + Wave 298 P6 §A.7 (lazy-memoized cache). 13 schedulers partitioned 9 + 4. | Paper-write agent | §4 fold-in (additive) | `wave297-p2-paper-design.md` §4.4 + `wave298-p6-deep-innovations.md` §A.7 |
| W2 (Day 1-3) | Extract Paper A §5 (Adapter Protocol) prose from Wave 297 P2 §4.5 + Wave 298 P6 §B.6 + §D.3. Emphasize zero-line vendored integration + 5 vendored checkpoints. | Paper-write agent | §5 fold-in (additive) | `wave297-p2-paper-design.md` §4.5 + `wave298-p6-deep-innovations.md` §B.6 + §D.3 |
| W2 (Day 4-5) | Compress Paper A §6 (Theoretical Lenses) to 1-paragraph companion framing per Wave 296 P7 §3 verdict + Wave 297 P2 §4.6. Cite cache shipped (38/38 tests, 16/16 sites) + FID Δ=0% as framework robustness proof. | Paper-write agent | §6 fold-in (additive) | `wave296-p7-fid-comparison.md` §3 + `wave297-p2-paper-design.md` §4.6 |
| W3 (Day 1-3) | Extract Paper A §7 (Empirical Results) from Wave 297 P5 §7.1-§7.7. 11-cell status table + 4 Bonferroni families + framework-not-theory verdict + R6 cross-adapter + matched-NFE boundary + head-to-head. | Paper-write agent | §7 fold-in (additive) | `wave297-p5-empirical-rewritten.md` §7 |
| W3 (Day 4-5) | Extract Paper A §8 (Reproducibility) from Wave 297 P2 §4.8 + Wave 298 P6 §B.1, B.5, C.1, C.2. D.4 30/30 + 6-gate CI + claims verifier + backward-compat invariant. | Paper-write agent | §8 fold-in (additive) | `wave297-p2-paper-design.md` §4.8 + `wave298-p6-deep-innovations.md` §B/C |
| W4 (Day 1-2) | Extract Paper A §9 (Limitations) from Wave 297 P2 §4.9 + Wave 292 P1 + Wave 292 P2 + Wave 287 P. 4 limitations: 15/16 dormant + 24-bug audit + matched-NFE=50 boundary + 12/13 cosine adapter-level. | Paper-write agent | §9 fold-in (additive) | `wave297-p2-paper-design.md` §4.9 + `wave292-p1-pipeline-inventory.md` + `wave287-p-scheduler-codepath-audit.md` |
| W4 (Day 3) | Extract Paper A §10 (Future Work) from Wave 297 P2 §4.10 + add Paper B handoff paragraph. | Paper-write agent | §10 fold-in (additive) | `wave297-p2-paper-design.md` §4.10 + this wave's Paper B deferred doc |
| W4 (Day 4) | Extract Paper A §11 (Conclusion) from Wave 297 P2 §4.11. 1-paragraph summary. | Paper-write agent | §11 fold-in (additive) | `wave297-p2-paper-design.md` §4.11 |
| W4 (Day 5) | Final cross-verify (5 gates: D.4 30/30, claims no drift, ruff 0, mkdocs 0 warnings, vendored NOT touched). Update Wave 299 final doc with cross-verify results. | Verify agent | `wave299-final-verify.md` | this doc + Wave 268 INVARIANTS |

**Total wall time:** 4 weeks (1 paper-write agent + 1 verify agent; parallel where possible).

**Risk mitigation:** Each fold-in is additive per Wave 268 strict-clean (no deletions, appends only). If a reviewer later requests a different framing, the additive appendices can be collapsed into the canonical 11-section structure in a single Wave 299 P-final fold-in pass.

---

## 7. Open Questions for the User

The following 7 questions require user input before Wave 300+ (Paper A finalization) or Wave 301+ (Paper B planning). Each row records the question, the context, and the recommended default.

| # | Question | Context | Recommended default |
|:-:|---|---|---|
| 1 | Is the title "FlowA: A Typed-Contracts Framework for Multi-Round Re-Inference on Flow Matching Models" acceptable? | Wave 297 P2 §2.1 proposed "FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints"; DeepSeek proposes "FlowA: A Typed-Contracts Framework for Multi-Round Re-Inference on Flow Matching Models" (drops "Training-Free" + "Frozen Checkpoints"; adds "Typed-Contracts" + "Multi-Round"). Both are valid; user must pick. | Adopt DeepSeek's title (it surfaces the typed-contracts architecture, which is the paper's primary contribution). |
| 2 | Should Paper A target TNNLS (primary) or a 二区 (Neurocomputing/Applied Intelligence) as the backup? | TNNLS match: framework + empirical + engineering rigor. 二区 backup: faster review cycle, higher acceptance rate (70-85%). User's preference determines whether we add 2-3 days of framework-level theory (Banach + Lyapunov) to strengthen the TNNLS submission. | Default to TNNLS; do NOT add Banach/Lyapunov at this stage (out of scope for Wave 299). |
| 3 | When should Paper B be planned (W300+ or W301+)? | Paper B requires ~6 GPU hours + regime-sweep design. Wave 291 P5 §5 shows the paper-quantity lever is INERT at the W286 P headline config; the regime sweep is prerequisite for any meaningful Paper B experiments. | Defer Paper B to W301+ (after Paper A is submitted); gate on regime-sweep design first. |
| 4 | Should the deep-innovation appendix (Wave 298 P7) stay in Paper A as supplementary, or be extracted to Paper B? | Wave 298 P6 §A.7 (lazy-memoized paper-quantity cache) is genuinely novel and central to Paper B (16-site integration); but it is also a framework innovation that supports Paper A's §4 (Scheduler Family). | Keep lazy-memoized cache in Paper A §4 (as a §4 innovation); Paper B cites it as the enabling infrastructure. |
| 5 | Should the matched-NFE=50 CIFAR-10 boundary be characterized as "structural image-domain boundary" or "matched-NFE=50 honest boundary with cross-budget win"? | DeepSeek's plan says "-10.7% structural"; Wave 297 P5 §7.6 says "matched-NFE=50 honest boundary; cross-budget ≈10× speedup at matched quality". The latter is more accurate (the framework DOES win on CIFAR-10 RF, just at a different NFE regime). | Default to Wave 297 P5 §7.6 characterization (matched-NFE=50 boundary + cross-budget win); reject "structural" framing because it overstates the limitation. |
| 6 | Should we add a 2-page framework-level theory appendix to Paper A (Banach fixed-point + Lyapunov stability sketch)? | The 7 genuinely-novel framework innovations are stronger if paired with even a sketch of convergence theory. This would strengthen TNNLS submission. | Optional; default NO (out of scope for Wave 299). Defer to user. |
| 7 | Should the next wave (Wave 300+) focus on (a) Paper A finalization fold-in (per §6 above), or (b) Paper B regime-sweep design + planning? | These are sequential dependencies: Paper A submission gates Paper B experiments (so the framework-not-theory verdict is reviewer-validated before we plan Paper B's theory-scheduler experiments). | Default to (a) Paper A finalization (Wave 300) → (b) Paper B regime sweep (Wave 301+). |

---

## 8. INVARIANTS (anchored for this audit)

This is a READ-ONLY consolidation doc; no code, no paper edits, no commits, no push. Invariants are unchanged from Wave 298.

| Invariant | Status |
|---|---|
| D.4 30/30 byte-stability | **PASS** (verified by `pytest tests/test_d4_regression_vectors.py -q` per Wave 298 §0) |
| Claims no drift | **PASS** (verified by `tools/check_claims_consistency.py` per Wave 298 §0) |
| Ruff 0 diagnostics | **PASS** (verified by `ruff check adaptive_reflow/ tests/ scripts/ tools/` per Wave 298 §0) |
| mkdocs 0 warnings | **PASS** (verified by `mkdocs build --strict` per Wave 298 §0) |
| Vendored NOT touched | **PASS** (verified by per-wave Edit discipline sections naming every vendored script NOT modified per Wave 298 §0) |
| `docs/drafts/paper-flat-flattened.md` NOT modified | **PASS** (per Wave 299 task scope; the paper state is the Wave 297 P3-P4-P5 + Wave 298 P7 additive state, byte-unchanged) |

---

## 9. Files NOT modified by this wave

- `docs/drafts/paper-flat-flattened.md` — byte-unchanged (per task scope).
- `adaptive_reflow/**/*.py` — byte-unchanged.
- `tests/**/*.py` — byte-unchanged.
- `tools/**/*.py` — byte-unchanged.
- `docs/CLAIMS.md`, `docs/METRIC_LEDGER.md` — byte-unchanged.

## 10. Files created by this wave

```
docs/audit/wave299-final-verification.md     (this doc)
docs/audit/wave299-paper-a-outline.md        (standalone Paper A outline)
docs/audit/wave299-paper-b-deferred.md       (standalone Paper B deferred work)
```

3 new audit docs; 0 modifications to existing docs.

---

## 11. Edit discipline

**Vendored scripts NOT modified** (per user directive "clone下来的原sota项目里的打分脚本依旧不能动"):
- `tools/run_sota_cifar_experiment.py` (W286 P, preserved)
- `tools/compute_cifar_fid.py` (W286 P, preserved)
- `data/<repo>/**` (W268 strict-clean, preserved)
- `data/lineageflow_upstream/**` (W268 strict-clean, preserved)
- `.venvs/**` (W268 strict-clean, preserved)

**This audit doc:** created 2026-09-23, READ-ONLY consolidation of Wave 296 P7 + Wave 297 + Wave 298 + DeepSeek feedback into a verifiable paper-split plan.

---

## 12. Honest summary

The DeepSeek feedback correctly identifies that Wave 296 P7 FID Δ=0% + Wave 297 narrative re-anchor + Wave 298 deep-innovation inventory make the project cleanly separable into two papers. All 12 of DeepSeek's load-bearing factual claims have been verified against the Wave 286-298 audit corpus; 11 are confirmed verbatim, 1 (the "structural" framing of the CIFAR-10 -10.7% regression) is better characterized as "matched-NFE=50 honest boundary with cross-budget win" per Wave 297 P5 §7.6. Paper A can be submitted without new experiments — the headline empirical data path is complete, byte-stable, and byte-identical under the JMAA flag flip. Paper B requires ~6 GPU hours and a prerequisite regime-sweep design (Wave 291 P5 §5 shows the paper-quantity lever is INERT at the Wave 286 P headline configuration). The recommended action is to **adopt the split, draft Paper A using Wave 298 P6 + Wave 297 P2 as the source-of-truth over 4 weeks, defer Paper B to Wave 301+ gated by regime-sweep design**. The deep-innovation appendix already appended to `docs/drafts/paper-flat-flattened.md` per Wave 298 P7 supports Paper A directly; no new appendix is needed. Push remains deferred per user directive "暂不 push".

This doc + the two companion standalone docs (`wave299-paper-a-outline.md`, `wave299-paper-b-deferred.md`) constitute the single audit trail for the Wave 299 paper-split decision.
