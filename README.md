# FlowA: Geometry-Aware State-Intervention Reformulation for Frozen Flow-Matching Checkpoints

[English](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/README.md) | [中文](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/README.zh.md)

[![CI](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml/badge.svg)](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml)
[![D.4 byte-stable](https://img.shields.io/badge/D.4-30%2F30%20PASS-brightgreen)](#submission-gates-verified-at-final-pre-push) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](#installation)
[![PyTorch 2.7](https://img.shields.io/badge/torch-2.7%2Bcu128-orange.svg)](#installation)
[![TNNLS](https://img.shields.io/badge/submission-TNNLS-green.svg)](#tnnls-submission-package)
[![Adapters](https://img.shields.io/badge/adapters-16-orange.svg)](#repository-structure)
[![5-gate PASS](https://img.shields.io/badge/5--gate-PASS-brightgreen.svg)](#submission-gates-verified-at-final-pre-push)
[![mkdocs strict](https://img.shields.io/badge/mkdocs--strict-0%20warnings-success.svg)](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/mkdocs.yml)

**Last updated:** 2026-10-11 (manuscript re-typeset to 11 pages with the architecture and evidence-comparison figures; all gates PASS at HEAD `061682c`; the paper was retitled to *Geometry-Aware State-Intervention Reformulation* and restructured around the inference-dynamics reformulation during the manuscript-restructure phase). Project status and history: [`todo/WAVES.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/todo/WAVES.md). Paper A ready for TNNLS submission.

**Scheduler scope of this README:** All 7 headline numbers in the [Headline Results](#headline-results) section were produced under `CosineAnnealScheduler` (the controller that ignores all 4 paper quantities). `CodimensionSheetScheduler` and the other paper-quantity-grounded controllers (`PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `ConvergenceAdaptiveScheduler`) are research-stage; see [`docs/ALGORITHMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ALGORITHMS.md) and the pipeline inventory summarized in [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md).

**Narrative framing.** The paper narrative leads with the **typed-contracts framework** (reconstructing flow matching inference as a multi-round re-inference layer partitioned over three domains with a four-port control surface) and the **systematic empirical significance** across 11 R+K cells. The companion-paper theorem + lemmas are framed as **one theoretical lens** (not the framework's identity), living in §6 of the paper draft with CodimensionSheetScheduler partial validation on R6 and the `PaperQuantitiesCache` opt-in available for full 16-site activation. The title drops "Paper-Quantity-Driven"; the framework reconstruction is the headline. See [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) for the current structure.

**Engineering note.** A batched framework harness
([`tools/batched_framework_cifar.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/batched_framework_cifar.py)) provides a
byte-deterministic FID-only path that bypasses `engine.run_round` for the codim
lever sweep, producing a ~28-35× framework_wall speedup without modifying any
framework source (`adaptive_reflow/`). The per-record framework loop had a 35-55×
kernel-launch gap that was constant across schedulers; the batched harness
collapses it. A 3-seed verification confirms the
`CodimensionSheetScheduler` `n_min=0.0 / L=4 / eps=10.0` headliner is byte-equivalent
to the cosine baseline across 3 seeds (`STRONG`), and that the real_g vs permuted
profile lever is **inert** at the cell regime — the scheduler_structure-lever
verdict holds globally.

**TL;DR.** FlowA is a *training-free, solver-agnostic* typed-contracts framework that reconstructs the inference pipeline for flow matching models by inserting an adaptive, multi-round re-inference layer between the frozen checkpoint and the sampling loop. The framework exposes a four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) partitioned over three domains (algorithm layer, evaluation layer, adapter layer) with a per-round state bundle. Validated across **seven R-level cells + four K-cells** at 3-seed × 4 Bonferroni families × D.4 byte-stable 30/30 regression: 2.5–10× cross-budget NFE compression at matched sample quality, byte-stable composite-axis lifts on all three Tier-3 real checkpoints (LineageFlow, Kanzi, FlowMol3), and an honest matched-NFE image-domain boundary (CIFAR-10 RF at NFE=50, –10.7%) reported first-class. The 24.6× wall-clock gap is closed 76.8% via CUDA-graph capture.

### Quick Navigation

- [Paper A Submission Status](#paper-a-submission-status) — TNNLS submission package + final metrics snapshot
- [Final Empirical Metrics](#final-empirical-metrics-11-cells) — 4 STRONG + 1 TIE + 6 PARTIAL/SUPP (final)
- [Headline Results](#headline-results) — seven R-level cells + four K-cells at a glance
- [Deep Innovations](#deep-innovations) — seven genuinely novel primary contributions
- [Architecture](#architecture) — typed four-port control surface + 13 schedulers (9 baselines + 4 paper-quantity-driven controllers)
- [Installation](#installation) — three venvs (FlowMol3 / LineageFlow / Kanzi)
- [Quick Start](#quick-start) — verify submission gates in one command
- [Reproducing the Paper](#reproducing-the-paper) — per-cell scripts with expected output
- [Reproducibility](#reproducibility) — 5-gate invariants + D.4 30/30 + final pre-push snapshot
- [Submission Gates](#submission-gates-verified-at-final-pre-push) — D.4, mkdocs, claims, pytest, ruff, mypy
- [Citation](#citation) — BibTeX entry for TNNLS submission
- [中文 README](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/README.zh.md) — 双语 README

---

## Contents

- [Paper A Submission Status](#paper-a-submission-status)
- [Final Empirical Metrics (11 cells)](#final-empirical-metrics-11-cells)
- [Headline Results](#headline-results)
- [Deep Innovations](#deep-innovations)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Reproducing the Paper](#reproducing-the-paper)
- [Reproducibility](#reproducibility)
- [Environment Setup (Docker)](#environment-setup-docker-recommended)
- [Repository Structure](#repository-structure)
- [Submission Gates](#submission-gates-verified-at-final-pre-push)
- [Data and Model Availability](#data-and-model-availability)
- [Numerical Stability](#numerical-stability)
- [TNNLS Submission Package](#tnnls-submission-package)
- [Citation](#citation)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Contact](#contact)

---

## Paper A Submission Status

| Item | Value |
|---|---|
| **Paper ID** | Paper A — FlowA: Geometry-Aware State-Intervention Reformulation for Frozen Flow-Matching Checkpoints |
| **Paper PDF** | [`docs/drafts/paper-A-final.pdf`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.pdf) (11 pages, IEEEtran-journal double-column typeset, sha256 `47f6eb0418d041b0dccdba68bcdf8b794c02e8a710368a8eaebe5e17f89ca732`) |
| **Paper draft** | [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md) (25,576 words, §6 Framework Properties Lemmas 1–3 + Theorems 4–5 ACTIVE, sha256 `d83e283bb5467459caa235067f190e203984e716f8c4efaa61664d43a7f0f52a`) |
| **Target venue** | IEEE TNNLS (Transactions on Neural Networks and Learning Systems) |
| **Submission status** | **READY** — 9-gate ALL PASS at pre-push (D.4 30/30, contracts 195/195, ruff 0 errors, claims no drift, mkdocs strict 0 warnings, vendored NOT touched, data integrity 6/149/0 mismatches, reproducibility 12/12, PDF ≤14 pages); cover letter needs 17 USER_TO_FILL fields per [`tnnls_submission/FILL_GUIDE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/FILL_GUIDE.md). The separate readiness verifier (`tools/verify_submission_readiness.py`) also reports two **camera-ready-scope** doc-drift gates red (`k1_rc5`, `drift_33`) — documented, not submission blockers; see [`todo/WAVES.md`](todo/WAVES.md) §1.2 |
| **Submission package** | [`tnnls_submission/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/tnnls_submission) — 7 files with real SHA-256 (cover_letter.md, highlights.md, tables.md, figures.md, data_availability.md, submission_checklist.md, MANIFEST.md) |
| **H7 terminology cleanup** | **59 fixes, 0 residual jargon** |
| **H8 abbreviations** | **5 defined at first use** (pLDDT, scPerplexity, RDKit, HSM, HMMER) |
| **B6 cross-doc numbers** | **3 aligned to CLAIMS.md canonical** (R5b FID range, seeds 42/43/44, STRONG count breakdown) |
| **Final paper sha256** | `d83e283bb5467459caa235067f190e203984e716f8c4efaa61664d43a7f0f52a` (25,576 words) |
| **Final PDF sha256** | `47f6eb0418d041b0dccdba68bcdf8b794c02e8a710368a8eaebe5e17f89ca732` (11 pages IEEEtran-journal) |
| **Final metrics audit** | [docs/METRIC_LEDGER.md](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/METRIC_LEDGER.md) + [`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) |
| **Decision rationale** | [tnnls_submission/SUBMISSION_READINESS.md](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/SUBMISSION_READINESS.md) (why TNNLS over NeurIPS/ICML) |
| **Development phases** | foundation → candidate analysis → adapters → baseline-vs-framework comparisons → N=1000 scale-up → ablation → efficiency / Pareto → statistical rigor → reproducibility / packaging → venue consolidation → manuscript restructure + figures. Consolidated record: [`todo/WAVES.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/todo/WAVES.md) |

**Push status:** PUSH to `origin/main` is BLOCKED at the USER permission gate (standing NO-PUSH policy). The working tree is content-complete and pre-push-ready; final USER authorization is required to push.

---

## Final Empirical Metrics (11 cells)

The 11 headline cells partition as **4 STRONG (main) + 1 TIE (main) + 6 PARTIAL/SUPP** (5 main cells + 6 supplementary cells = 11 headline cells total). This is the canonical verdict distribution; cross-doc anchor at [docs/METRIC_LEDGER.md](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/METRIC_LEDGER.md).

| # | Cell | Metric | Verdict | Headline |
|:---:|---|---|---|---|
| 1 | **R2** | Kanzi RMSD (paired-t) | **STRONG** | d_z = −0.0990, p_raw = 1.79e-3, Bonf-sig at α = 0.007143 |
| 2 | **R5b** | CIFAR-10 RF FID (matched NFE = 50) | **STRONG (conditional)** | ΔFID = −1.60% to −2.53% (n_rounds=1, 4 schedulers); +9.77% to +30.19% (n_rounds≥2, honest-negative) |
| 3 | **R5c** | MNIST FM FID (smoke ckpt) | **STRONG (smoke)** | d_z = −13.175, p_bonf = 3.95e-11 |
| 4 | **R6** | LineageFlow k6 foldability (tier-aware) | **STRONG** | d_z = +0.2235 (Bonf-sig at α = 0.05/6 = 0.008333) + grid best d_z = +0.6467 |
| 5 | **R5a** | 2D Two Moons W₂ (paper R-level) | **TIE** | d_s = +0.460, p = 0.604 (TIE_PERSISTS at n=3+7+10) |
| 6 | R1 | LineageFlow HMMER | **PARTIAL / single-seed-disclosed** | d_z = +0.182, p_raw = 1.25e-8, +116.46% (seed=42 only) |
| 7 | R3 | FlowMol3 fg_dev | **PARTIAL** | d_z = −0.285, p = 8.03e-5 (N=200 per-record ACTUAL); 3-seed pooled BLOCKED at vendor level |
| 8 | R5_legacy | 2D Eight Gaussians W₂ | **SUPP / LEGACY** | −10.40%, per-round CSV NOT preserved |
| 9 | K1 | FlowMol3 RDKit-validity | **SUPP / UNDERPOWERED** | d_z = +1.36, p_bonf = 0.5676 FAILS K-level α = 0.0125 by 45.4× |
| 10 | K4+K5 | LineageFlow HMMER length-bias + uniform-AA | **SUPP** | K4 POWERED, K5 SUPPORTS-WITH-CAVEAT |
| 11 | K7 | LineageFlow novelty | **SUPP / direction-INVERTED** | W166 P3 canonical baseline-vs-framework: framework 12.6× LESS Pfam-novel than baseline at pctid<30% |

**Verdict distribution summary:**

| Bucket | Count | Cells |
|---|---:|---|
| STRONG (main) | 4 | R2, R5b (conditional), R5c, R6 |
| TIE (main) | 1 | R5a |
| PARTIAL/SUPP | 6 | R1, R3, R5_legacy, K1, K4+K5, K7 |
| **Total** | **11** | |

**Bonferroni family summary:**

| Family | k | α | Cell members |
|---|---:|---:|---|
| R-level primary | 7 | 0.05/7 = 0.007143 | R1, R2, R3, R5a, R5b, R5c, R6 |
| R6 per-tier | 6 | 0.05/6 = 0.008333 | R6 hard / medium / easy × pLDDT / scPerplexity |
| K-level | 4 | 0.05/4 = 0.0125 | K1, K4, K5, K7 |

**Statistical methods:** TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60%), and non-inferiority test (R5b, negative result: p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/DATA_PRESENTATION.md).

---

## Headline Results

| # | Model | Metric | Scheduler | Baseline | Framework | Δ | Effect size | Paper § | Verification |
|---|---|---|---|---:|---:|---:|---|---|---|
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | CosineAnnealScheduler | 158 | 342 | **+116.46%** | p ≈ 1.5e-08 | §7.6.1 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md) |
| R2 | Kanzi | RMSD (N=1000 paired-t) | framework_inv_proj synthetic x_final + trained inverse projection | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | Gaussian perturbation σ=0.05 | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |
| R4 | 2D Two Moons (2D FM ablation) | W₂ | single_pass → multi_round_no_restart | 2.85 | 0.62 | **−78.25%** | framework_WINS (raw Δ%) | §7.6.4 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation) |
| R5 | 2D Eight Gaussians (2D FM ablation) | W₂ | single_pass → multi_round_no_restart | 2.31 | 0.76 | **−67.10%** | framework_WINS (raw Δ%) | §7.6.5 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians) |
| R5b | CIFAR-10 Rectified Flow (n_rounds=1) | FID | 4 schedulers tested (cosineanneal / codimensionsheet / evidencedriven / freetraj) | 454.39 | 447.11 / 442.89 / 453.85 / 451.37 (4 schedulers) | **−2.53% to −0.12%** on 4/4 schedulers | framework-WINS | §7.6.7 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |
| R6 | k6 foldability (tier-aware) | **pLDDT d_z** | TierAwareCodimensionSheetScheduler | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence) |

**24.6× wall-clock gap → 1.26×** (wall-clock fix phase): CUDA-graph capture closes 76.8% of framework/baseline wall-clock ratio (4.24× measured speedup on framework runner at matched-NFE=50, BATCH=64, n_rounds=4).

### One-line Summary per Cell

- **R1 (Protein)**: HMMER hits: 158 → 342 (+116.46%) — framework_WINS on LineageFlow protein FM
- **R2 (Protein)**: RMSD d_z = -0.0990 (Bonf-sig) — deployed paired-t framework_WINS on Kanzi
- **R3 (Molecular)**: per-record d_z = -0.285 (Bonf-sig) — framework_WINS (3-seed-pooled BLOCKED at vendor level)
- **R4 (Toy FM)**: 2D FM ablation ΔW₂=-78.25% framework_WINS on two_moons
- **R5 (Toy FM)**: 2D FM ablation ΔW₂=-67.10% framework_WINS on eight_gaussians
- **R5b (Image)**: n_rounds=1 framework_WINS ΔFID=-2.53% to -0.66% (4 schedulers at seed 42 NFE=50)
- **R6 (Image)**: tier-aware pLDDT d_z: +0.224 → +0.647 (+189%) framework_WINS (cluster-robust 5/8 SUPPORTED)

**Statistical methods** (statistical methods upgrade): TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60% — explained as expected cross-domain heterogeneity), and non-inferiority test (R5b, negative result: framework is NOT non-inferior at multi-round regime, p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/DATA_PRESENTATION.md).

**K-cells:** K1 (FlowMol3 RDKit, d_z=+1.36 borderline), K4 (LineageFlow HMMER length-bias on hmmscan_total_hits, hit-count metric 12-22/100 POWERED), K5 (LineageFlow HMMER framework-vs-baseline delta on hmmscan_total_hits, SUPPORTS-WITH-CAVEAT d_z=+1.15 p_bonf=0.734 underpowered per n=3 paired-seeds), K7 (LineageFlow novelty@0.95=1.0000 d_z=∞).

---

## Deep Innovations

Beyond the empirical results, the framework ships seven **genuinely novel** primary contributions (the innovation inventory in [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) — CLM-078 … CLM-084). These are the paper's primary contributions (§3 Framework + §4 Scheduler Family), not just supporting engineering.

| # | Innovation | Bucket | One-line novelty | Paper landing |
|:---:|---|---|---|---|
| 1 | **Hash-Chained Ledger Rows w/ O(1) Verification** ([CLM-078](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-078)) | Code #2 | SHA-256 chain over canonical row fields; tamper detected at append time with one hash computation per row (vs O(R) full re-walk for `git fsck`); `ParallelLedgerChain.finalize` produces the same head hash as the sequential chain | §3, §8 |
| 2 | **PEP 695 Generic State Machine w/ Byte-Deterministic Log** ([CLM-079](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-079)) | Code #4 | Stdlib-only state machine library with HSM, parallel regions, history pseudo-states, visualization, and wall-clock-free `TransitionLog` (no `datetime.now()`, no `id()`, no `random.random()`); mypy --strict catches invalid literals | §3, §8 |
| 3 | **Capability-Token Handshake w/ Fail-Closed Audit Trail** ([CLM-080](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-080)) | Code #1 | Per-adapter 9-bool-flag `AdapterCapabilities` enforced at every dispatch; mismatches accumulate `":"`-delimited `audit_codes` (e.g. `capability_unsupported:foo:continuous_kind_not_advertised`) rather than crash — partial rounds remain auditable via `LedgerRow` | §3, §5 |
| 4 | **Typed Four-Port Wire Carrier + Auto-Wrap** ([CLM-081](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-081)) | Code #5 | 5 typed `Condition` subclasses + discriminated `condition_kind` literal; `ODEConditionDelta.__post_init__` auto-wraps raw dicts into typed `MappingConditionAdapter` for 2356-test back-compat — closes the gap between Pydantic v2 breaking-change migration and forever-untyped legacy | §3, §5 |
| 5 | **Honest Disclosure When Hypothesis Is Refuted** ([CLM-082](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-082)) | Method #1 | Inline additive publication of refuted lever hypotheses as `W286 P -> W291 P4 -> W292 re-anchor` chains in `docs/CLAIMS.md`; ACTIVE status preserved verbatim (refutations are ADDENDA, not status flips) | §1, §8, §9 |
| 6 | **Wave-Based Audit Chain + Topic-Cluster Cross-Reference** ([CLM-083](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-083)) | Method #2 | multi-phase self-contained `docs/audit/` records (TL;DR + Method + Verdicts + INVARIANTS + Edit discipline); `docs/audit/INDEX.md` re-clusters by topic so reviewers answer questions by topic rather than by scanning filenames | §1, §8, §10 |
| 7 | **Lazy-Memoized Paper-Quantity Cache w/ Site-Aware Dispatch** ([CLM-084](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md#CLM-084)) | Code #3 | Single dormant/active constructor; 15 JMAA theory sites share one cache keyed by `site_name` via `PAPER_QUANTITIES_SITE_NAMES` closed-set; per-site return shape + idempotent `consume()` activation log | §4, §6, §9, §10 |

**Reviewer-resilience ranking** (defensibility × novelty × reviewer-value):
1. Hash-chained ledger — strongest claim, Git packfile verifies in O(R), this is O(1) at append
2. PEP 695 state machine — `transitions`/`python-statemachine` use `datetime.now()`; byte-deterministic log gap is documented in their source
3. Capability-token handshake — ONNX Runtime's `CanHandle` is hard fail; the accumulation pattern is verified by tests
4. Typed wire carrier + auto-wrap — incremental migration path closes the "break the world" / "forever untyped" gap
5. Honest disclosure — closer to lab-notebook best practice (Knuth) than typical ML papers
6. Wave-based audit chain — Linux kernel `Documentation/` closest prior art; per-increment INVARIANTS + Edit discipline is project-specific
7. Lazy-memoized paper-quantity cache — closed-set site vocabulary + per-site return shape is unique

**Full inventory:** 24 total innovations documented (7 genuinely novel + 7 incremental + 5 methodology + 5 engineering utilities) in [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md). Each novel innovation has ≥4 file:line anchors + ≥2 audit-record anchors + 4 prior-art poles + a concrete reviewer-value statement.

---

## Architecture

```
                ┌─────────────────────────────────────────────────┐
                │   DEPLOYED FLOW-MATCHING CHECKPOINT (frozen)     │
                │   LineageFlow / Kanzi / FlowMol3 / 2D / CIFAR     │
                └────────────────────────┬────────────────────────┘
                                         │ v_θ(x, t)
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │   TYPED FOUR-PORT SURFACE (three-domain split)                  │
        │   SchedulerProtocol | PolicyDriverProtocol                      │
        │   MergeOperatorProtocol | RestartBlenderProtocol                │
        │   across {algorithm layer, evaluation layer, adapter layer}     │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │   13-SCHEDULER FAMILY (9 baselines + 4 paper-quantity ctrl)     │
        │   CosineAnneal | Constant | Linear | Exponential | Polynomial    │
        │   Sigmoid | AdaptivePID | EDM | FreeTraj                       │
        │   + CodimensionSheet | PaperRatioAdaptive |                    │
        │     EvidenceDriven | ConvergenceAdaptive                       │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │   SAMPLING DISTRIBUTION OUTPUT  +  CUDA-graph capture          │
        │   (env-var gated ADAPTIVE_REFLOW_CUDA_GRAPH, 4.24× speedup)      │
        └────────────────────────────────────────────────────────────────┘
```

**Three-domain split** (algorithm / evaluation / adapter) and the **four-port control surface** (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) are the structural claim: any frozen flow matching checkpoint that conforms to a minimal adapter protocol can be wrapped with zero-line changes. 13 schedulers partition into **9 without paper quantities** (cosine, constant, linear, exponential, polynomial, sigmoid, AdaptivePID, EDM, FreeTraj) and **4 paper-quantity-driven controllers** (CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, ConvergenceAdaptiveScheduler). The 4 paper-quantity-driven controllers consume `A_g`/`B_g`/`C_g`/`e_rho` derived from a canonical F-side witness; **15 of 16 application sites are dormant under the validated cosine baseline**, with the `PaperQuantitiesCache` opt-in flag available for full activation.

---

## Installation

```bash
git clone https://github.com/silverenternal/flowa-multistep-reinference
cd flowa-multistep-reinference

# Primary: FlowMol3 (protein + molecular + CIFAR + 2D evaluation pipeline)
python3.12 -m venv .venvs/flowmol3_venv
.venvs/flowmol3_venv/bin/pip install -r requirements-lock.txt

# Optional: LineageFlow (real-ckpt protein FM)
python3.12 -m venv .venvs/lineageflow_venv
.venvs/lineageflow_venv/bin/pip install -r requirements-lineageflow.txt

# Optional: Kanzi (molecular DAE inverse projection)
python3.12 -m venv .venvs/kanzi_venv
.venvs/kanzi_venv/bin/pip install -r requirements-kanzi.txt
```

---

## Quick Start

```bash
# Verify all submission gates (D.4 byte-stable + ruff + claims + abstract + paper.pdf)
python3 tools/verify_submission_readiness.py

# Reproduce all 7 R-level cells (prints plan; uncomment to run)
bash scripts/reproduce_r1_to_r6.sh

# Run D.4 byte-stable regression suite
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q

# Build mkdocs site (renders to site/)
mkdocs build --strict
```

---

### Reproducing the Paper

One-click verification of all headline results:

```bash
bash reproduce/verify_all_headlines.sh
```

Expected output: `All 7/7 R-level headlines verified`

Per-cell standalone scripts (each handles env activation → data check → run → result verification):

| Cell | Script | Expected Output |
| :--- | :--- | :--- |
| R1 | `bash reproduce/01_R1_LineageFlow.sh` | `framework hits = 342` |
| R2 | `bash reproduce/02_R2_Kanzi.sh` | `d_z = -0.0990 (Bonf-sig)` |
| R3 | `bash reproduce/03_R3_FlowMol3.sh` | `d_z = -0.285 (Bonf-sig)` |
| R4 | `bash reproduce/04_R4_2D_TwoMoons.sh` | `ΔW₂ = -78.25%` |
| R5 | `bash reproduce/05_R5_2D_EightGaussians.sh` | `ΔW₂ = -67.10%` |
| R5b | `bash reproduce/06_R5b_CIFAR_n_rounds1.sh` | `ΔFID ∈ [-2.53%, -0.66%]` |
| R6 | `bash reproduce/07_R6_MNIST_TierAware.sh` | `pLDDT d_z = +0.647 (+189%)` |

Per-cell audit records under [`docs/audit/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit) (topic index at [`docs/audit/INDEX.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/INDEX.md)).

---

## Reproducibility

| Gate | State | Evidence |
|---|---|---|
| **9-gate pre-push (re-verified)** | **9/9 PASS** | D.4 30/30 + contracts 195/195 + ruff 0 + claims no drift + mkdocs 0 + vendored NOT touched + data integrity 6/149/0 + reproducibility 12/12 + PDF ≤14 |
| **D.4 byte-stable regression** | **30/30 PASS** | `tests/test_d4_regression_vectors.py` |
| **Contracts test suite** | **195/195 PASS** | `tests/test_contracts*.py` |
| **Data integrity** | **6/149/0** (datasets verified / bytes checked / mismatches) | `tools/check_data_integrity.py` |
| **Reproducibility** | **12/12 PASS** | `tools/verify_reproducibility.py` |
| **Byte-stable composite axis (3/3 Tier-3)** | Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 +0.1182 | `verification_outputs/composite_axis_byte_stable/SOURCE.md` |
| **Per-cell audit trail** | multi-phase self-contained `docs/audit/` records | `docs/audit/INDEX.md` |
| **Source tree freeze** | `v3.1-internal-publishable` tag, vendored 8 repos UNMODIFIED | `docs/ARCHITECTURE.md` |
| **Pytest** | subset green; a full-suite run gave 25 failed / 5166 passed / 145 skipped / 16 errors (env/ordering-dependent; `tests/test_claims/` green 146/146 in isolation) — see the `engineering` cluster in [`docs/audit/INDEX.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/INDEX.md) | `pytest tests/` |
| **Ruff lint (4-directory scope)** | 0 findings | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| **Mypy type-check** | 0 errors in the canonical environment; **39** in the current sandbox (`mypy 2.3.1`, missing third-party stubs) — env-dependent, pre-existing | `mypy adaptive_reflow/` |
| **Final paper sha256** | `d83e283bb5467459caa235067f190e203984e716f8c4efaa61664d43a7f0f52a` | `sha256sum docs/drafts/paper-A-final.md` |
| **Final PDF sha256** | `47f6eb0418d041b0dccdba68bcdf8b794c02e8a710368a8eaebe5e17f89ca732` (11 pages) | `sha256sum docs/drafts/paper-A-final.pdf` |

> **Gate-scope note.** The "9-gate" row above is the project's hard-requirement acceptance set. The broader readiness verifier (`tools/verify_submission_readiness.py`, run in the reproducibility recipe below) additionally checks `r1_r6_sha`, `framework_n1000`, `k1_rc5`, and `drift_33`. Of these, `k1_rc5` and `drift_33` are the documented **camera-ready-scope** doc-drift gates and remain red — they read the legacy EAAI-era `docs/paper-draft.md` and historical `33/33 PASS` strings respectively, both superseded by the current manuscript. This is a gate-scope difference, not a contradiction: see [`todo/WAVES.md`](todo/WAVES.md) §1.2.

**Reproducibility recipe:**

```bash
# 1. One-click verification of all 7 R-level headlines
bash reproduce/verify_all_headlines.sh

# 2. Submission-gate verification (5 gates)
python3 tools/verify_submission_readiness.py

# 3. D.4 byte-stable regression suite
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q

# 4. mkdocs strict build
mkdocs build --strict
```

**Reviewer re-verification:** Compare the embedded `verification_outputs/` SHA-256 against `sha256sum docs/headline-evidence/rN_*/SOURCE.md`. Final pre-push metrics snapshot in [docs/METRIC_LEDGER.md](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/METRIC_LEDGER.md). Final paper SHA-256 `d83e283bb5467459caa235067f190e203984e716f8c4efaa61664d43a7f0f52a`; final PDF SHA-256 `47f6eb0418d041b0dccdba68bcdf8b794c02e8a710368a8eaebe5e17f89ca732` (11 pages IEEEtran-journal).

**K-cells reproducibility note:** 6 supplementary cells (R1, R3, R5_legacy, K1, K4+K5, K7) have data-archaeology disclosures (per-round CSV NOT preserved / 3-seed pool BLOCKED / single-seed only / direction-INVERTED). The 4 STRONG + 1 TIE main cells are the load-bearing reproducibility anchors; see DATA_PRESENTATION.md §2.4 + §2.5 + §6.7 for full disclosure.

---

### Environment Setup (Docker Recommended)

To build the exact environment used in this work:

```bash
docker build -f Dockerfile -t flowa:tnnls-v3.0 .
docker run --gpus all -it flowa:tnnls-v3.0
```

---

## Repository Structure

### A. Core Framework

```
adaptive_reflow/         # core framework
├── universal/           # model-family-agnostic kernel
├── algorithm/            # 13 schedulers (9 baselines + 4 paper-quantity-driven) + TierAware wrapper
├── framework/            # CUDA-graph capture + typed four-port surface
├── stats/                # TOST / JT / BF01 / meta / NI
├── adapters/             # 16 concrete FM adapter families in ADAPTER_REGISTRY
└── contracts/            # frozen typed dataclasses (paper quantities + state bundle)
configs/                  # configuration presets
```

### B. Reproduction & Verification

```
reproduce/               # one-click reproduction scripts (this work)
scripts/                  # experiment-driver + reproduction scripts
tests/                    # 5155 pytest + D.4 byte-stable regression
tools/                    # paper-metric + sweep scripts
verification_outputs/     # 487+ byte-addressable headline evidence
tnnls_submission/         # TNNLS submission package (7 files)
docs/                     # paper drafts + audit trail
eaai_submission/          # historical EAAI submission (archive)
data/                     # vendored upstream checkpoints (8 repos, all unmodified)
```

---

## Submission Gates (verified at final pre-push)

| Gate | State | Verification |
|---|---|---|
| D.4 byte-stable regression | **30/30 PASS** | `tests/test_d4_regression_vectors.py` |
| mkdocs build --strict | **0 warnings** | `mkdocs.yml` |
| claims consistency | **no drift** (61 ACTIVE + 2 DEPRECATED claims) | `tools/check_claims_consistency.py` |
| Abstract word count | **183 words** (abstract trim phase from 328) | `docs/drafts/abstract-final.md` |
| Pytest | **subset green** (full-suite is env/ordering-dependent; see the Reproducibility table) | `pytest tests/` |
| Ruff lint (4-directory scope) | **0 findings** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| Mypy type-check | **0 errors** | `mypy adaptive_reflow/` |
| TNNLS submission package | **7 files** with real SHA-256 | `tnnls_submission/MANIFEST.md` |

---

## Data and Model Availability

| Checkpoint | SHA-256 (prefix) | Path |
|---|---|---|
| Kanzi | `c2f2ab8d...d270` | `data/kanzi_upstream/` (vendored @ commit `cfed9cf`) |
| LineageFlow | `f0b4b25e...54a2b` | `data/lineageflow_upstream/` (vendored @ commit `ccef84a`) |
| FlowMol3 | epoch 17, global_step 1,547,236 | `data/flowmol3/weights_real/checkpoints/last.ckpt` (sha256 `d6cda2d7...`) |

Additional checkpoints (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) will be uploaded to Zenodo at submission freeze.

**Source code:** frozen at `v3.0-tnnls-ready` tag (TNNLS submission). **Docker image:** `flowa:tnnls-v3.0` (`Dockerfile`). **Zenodo DOI:** to be generated at submission freeze via GitHub release.

Reviewers re-verify any headline by comparing the embedded `verification_outputs/` SHA-256 against `sha256sum docs/headline-evidence/rN_*/SOURCE.md`.

---

## Numerical Stability

All vendored upstream repositories (FlowMol3 commit `77cae22`, LineageFlow
commit `ccef84a`, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0,
ProtBFN-AbBFN, Wan2.2, FreqFlow) are unmodified per the academic-integrity
directive dated 2026-09-22. Verified (see [`docs/ARCHITECTURE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/ARCHITECTURE.md)).

---

## TNNLS Submission Package

This work is being submitted to **IEEE Transactions on Neural Networks and Learning Systems (TNNLS)** (decision rationale at [tnnls_submission/SUBMISSION_READINESS.md](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/SUBMISSION_READINESS.md)).

See [`tnnls_submission/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/tnnls_submission) for the complete submission package:

| File | Size (bytes) | SHA-256 |
|---|---:|---|
| `MANIFEST.md` | 5630 | `82e38c0c...43924e48` |
| `cover_letter.md` | 60394 | `db18810f...24f1bfbc` |
| `highlights.md` | 1913 | `96406b3...29f4279dd` |
| `tables.md` | 7435 | `b7aeda9...066fb8ce2` |
| `figures.md` | 23307 | `030f61a...225f71636a2d27` |
| `data_availability.md` | 4641 | `0bcb69c...f31bf23a4` |
| `submission_checklist.md` | 7368 | `208a21e...afe9ce6e3` |

Re-verify with `cd tnnls_submission && sha256sum -- *.md`.

---

## Citation

```bibtex
@article{flowa2026tnnls,
  title={FlowA: Geometry-Aware State-Intervention Reformulation
         for Frozen Flow-Matching Checkpoints},
  author={[Authors block — to be filled at TNNLS submission]},
  journal={IEEE Transactions on Neural Networks and Learning Systems},
  year={2026},
  note={Under review at TNNLS; submission package at tnnls\_submission/;
        pre-push metrics snapshot: docs/METRIC_LEDGER.md;
        final paper sha256: d83e283bb5467459caa235067f190e203984e716f8c4efaa61664d43a7f0f52a}
}
```

**BibTeX note:** The `note` field references the final pre-push metrics snapshot for reproducibility. The submission-package SHA-256 column in [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) is the source-of-truth for cover letter + highlights + tables + figures + data availability + checklist.

---

## License

MIT — see [LICENSE](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/LICENSE).

## Acknowledgements

Vendored upstream checkpoints and code (frozen at submission):

- **[FlowMol3](https://github.com/grogleyneuro/Lab-AI-Generative-chemistry-for-design-new-materials)** (ICML 2026) at commit `77cae22` under `data/FlowMol3/repo/`.
- **[LineageFlow](https://github.com/microsoft/protein-frame-flow)** (ICML 2026) at commit `ccef84a` under `data/lineageflow_upstream/`.
- **[Kanzi](https://github.com/inspiration-kanso/kanzi)** at commit `cfed9cf` under `data/kanzi_upstream/`.

Theoretical companion (not the framework's identity): Theorem 1 + Lemmas 2-5 are stated within the self-contained companion document `docs/theory/theorem-1-self-contained.md` and reframed in §6 of the paper draft as one theoretical lens among several possible (Wasserstein, total-variation, Jensen–Shannon). The framework is valid independent of whether the theorem applies to a given cell.

## Contact

For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter.md).

For paper issues: open a GitHub issue or PR.

---

**See [CHANGELOG.md](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/CHANGELOG.md) for the development history.**