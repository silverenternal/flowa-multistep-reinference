# Wave 297 P6 — §9 Limitations + §10 Future Work (Wave 297 P6 reframe): honest scope-of-current-state disclosure

**Date:** 2026-09-23
**Branch:** main
**Prior docs (anchors):**
- `docs/audit/wave297-p1-paper-inventory.md` (P1 — current structure, 6 JMAA-prominent sections)
- `docs/audit/wave297-p2-paper-design.md` (P2 — new 11-section structure + §1 prose draft + claim text per section)
- `docs/audit/wave297-p3-intro-rewritten.md` (P3 — §1 Introduction + Abstract reframe, additive pass)
- `docs/audit/wave297-p4-framework-rewritten.md` (P4 — §3 Framework + §4 Scheduler Family + §5 Adapter Protocol reframe appendix, additive pass)
- `docs/audit/wave297-p5-empirical-rewritten.md` (P5 — §7 Empirical Results reframe appendix, additive pass)
- `docs/audit/wave292-p1-pipeline-inventory.md` (W292 P1 — 15 of 16 enumerated Theorem 1 application sites dormant under cosine)
- `docs/audit/wave291-p5-3seed-results.md` (W291 P5 — codim CIFAR HARMFUL at +10.721%, p = 2.288e-03, profile lever INERT at validated config)
- `docs/audit/wave287-final.md` (W287 — 24 algorithm findings in paper-grounded controllers; 2 critical + 12 major + 10 minor)
- `docs/audit/wave286-p-fid-gpu-fix.md` + `wave286-p-fid-gpu-verify.md` (W286 P — FID GPU fixpoint)
- `docs/audit/wave290-p3-batched-harness.md` (W290 P3 — 30× codim sweep speedup)
- `docs/audit/wave296-p1-architecture.md` (W296 P1 — full JMAA integration design doc)
- `docs/audit/wave296-p2-cache.md` (W296 P2 — PaperQuantitiesCache carrier)
- `docs/audit/wave296-p3-a-class-wired.md` (W296 P3 — 7 A-class sites wired)
- `docs/audit/wave296-p4-b-class-wired.md` (W296 P4 — 8 B-class sites wired)
- `docs/audit/wave204-p2-lineageflow-cross-adapter.md` (W204 P2 — LineageFlow N=574 paired per-record replication of R6 monotone pattern)
- `docs/audit/wave280-p-r1-sweep-result.md`, `wave280-p-k1-sweep-result.md`, `wave280-p-k4k5-sweep-result.md`, `wave280-p-k7-sweep-result.md`, `wave280-p-cifar-sweep-result.md`, `wave280-p-r3-sweep-result.md`, `wave280-p-r6-sweep-result.md` (W280 P — 7 weak-claim headline sweep results, 3-seed pool seeds 42/43/44)
- `docs/audit/wave158-2d-two-moons-single-seed.md` (W158 — R5a single-seed baseline, 3-seed extension open)
- `docs/audit/wave235-p1-cifar-regression-reversal.md` (W235 P1 — single-round n_rounds=1 REGRESSION → WIN reversal on K3+R5b)
- `docs/audit/wave109-c-dgl-bug.md` (W109.C — DGL vendor-level blocker on R3 3-seed pooled-SD)
- `docs/METRIC_LEDGER.md` (126-row machine-readable inventory)
- `docs/INSIGHTS.md`, `docs/CLAIMS.md` (Wave 22 metric-rev3 promotion rubric, Wave 196 P4 + Wave 198 P2 + Wave 204 P2 verdict records)

**Source paper (pre-edit):** `docs/drafts/paper-flat-flattened.md` (758 lines, post-Wave-297-P5, 19 sections + Wave 297 P3-P4-P5 appendices)
**Target paper (post-edit):** `docs/drafts/paper-flat-flattened.md` (1083 lines, +325 lines net, +638 cumulative insertions vs HEAD, ADDITIVE edits only)
**Purpose:** Append the new "§9 Limitations + §10 Future Work" appendix as additive Wave 297 P6 reframe block at the end of the paper-flat-flattened.md, per the Wave 297 P2 §1 + §4.8 design directive. Wave 268 strict-clean rule honoured: **never replace existing text, append correction notes (e.g., "(Wave 297 P6 reframe — ...)") next to old paragraphs**. The new §9 re-anchors the limitations from the legacy §4 K1–K8 boundary-dimension framing (scope-as-applicability) to a **scope-of-current-state disclosure** (scope-as-currently-exercised + scope-as-yet-unexercised + scope-as-yet-validated), and the new §10 enumerates the implementation roadmap to convert the dormant sites into exercised sites without diminishing the primary contributions of §3 (headline empirical results) and §7 (systematic-evidence framing).

---

## 0. TL;DR

- **Mode:** ADDITIVE paper-edit pass per Wave 268 strict-clean rule. Legacy §2 Algorithm + §3 Experiments + §4 Limitations (K1–K8) + §5 Flattening Checklist + §6 Reviewer-Facing Static Reference Labels + Wave 297 P3-P4-P5 reframe appendices preserved verbatim; new §9 + §10 appended at end of paper as "Appendix W297 P6 — §9 Limitations + §10 Future Work (Wave 297 P6 reframe)".
- **Files modified:** `docs/drafts/paper-flat-flattened.md` (+325 lines net from pre-edit 758 → post-edit 1083; +638 cumulative insertions vs HEAD since all Wave 297 P3-P6 work was uncommitted; 0 deletions).
- **§9.1 Six scope-of-current-state disclosures:**
  - **§9.1.1** — 15 of 16 enumerated Theorem 1 application sites dormant under the cosine baseline (per Wave 292 P1 pipeline inventory). The single active site is the scheduler family itself (`CosineAnnealScheduler`), which consumes `A_g` only as an optional cached-at-construction profile-residual value.
  - **§9.1.2** — Codim paper-quantity lever is SUPPORTED but HARMFUL on CIFAR-10 RF at validated config: codim_real_g mean Δ% vs cosine = +10.721% (σ = 0.726%, paired t = 20.872, p = 2.288e-03, Bonferroni-significant at α = 0.007143). Profile lever INERT at validated config (codim_real_g vs codim_perm byte-identical at 3-seed level); the +10.721% delta is driven by scheduler structure (codim L=4 with offline profile), not by paper quantities.
  - **§9.1.3** — Wave 287 found 24 algorithm findings in paper-grounded controllers (2 critical + 12 major + 10 minor across 12 scheduler classes in 7 files). 2 critical bugs fixed in Wave 289 P4; 12 major + 10 minor remain in regression-coverage-but-not-fixed state. 65-test `tests/test_paper_grounded_schedulers.py` suite ships per Wave 287 P2; adversarial sweep `tools/adversarial_scheduler_test.py` covers 25 cells (23 PASS, 2 fail-closed by design).
  - **§9.1.4** — Wave 286 FID GPU compute fixpoint (InceptionV3 forward pass on CUDA, 2.2 GB GPU memory growth, N=50 wall 1.193× speedup, N=200 FID compute 2.24× speedup). All FID values in §3 + §7 are post-Wave-286; pre-Wave-286 FID values in earlier audit docs are stale.
  - **§9.1.5** — Wave 290 batched harness delivers 30× speedup on the codim paper-quantity sweep, reducing a single CIFAR sweep from ~25 min to ~50 sec wall. The Wave 291 P5 3-seed verification of the codim lever rests on this harness being in place.
  - **§9.1.6** — Per-site empirical validation is partial: only R6 k6 + LineageFlow (Wave 204 P2) has cross-adapter replication at per-record granularity (N=574 + N=1000). Image-domain and molecular-3D cells do not have cross-adapter replication.
- **§9.2 Mapping to §4 K1–K8:** the §9.1 disclosures sharpen K2 (NFE-regime applicability, codim CIFAR HARMFUL), K3 (sample-difficulty stratification, per-site validation partial), K4 (scheduler-port coupling, dormant sites + algorithm bugs), K5 (protein-family cluster dependence, unchanged), K8 (per-cell compute-budget allocation, codim GPU bottleneck fix). §9 is additive boundary characterisation, not retraction.
- **§10.1 Four implementation-roadmap items:**
  - **§10.1.1** — Wave 296 full JMAA theory integration (in progress across P1-P4, end-to-end smoke test + §7.2 re-run under `enable_full_jmaa_theory=True` remaining).
  - **§10.1.2** — Codim regime expansion beyond R6 (R3 FlowMol3 codim sweep + R5a 2D Two Moons codim sweep).
  - **§10.1.3** — 3-seed re-verification of headliner cells (R5a 3-seed extension, R5c production ckpt 3-seed, K3+R5b add seed44).
  - **§10.1.4** — Per-site empirical validation (R5b cross-image-adapter replication, R3 cross-molecular-adapter replication, R1 cross-protein-adapter extension).
- **§10.2 Reframing:** the §10.1 roadmap is empirical, not theoretical. No new JMAA Theorem 1 derivations, no new convergence bounds, no new theorem content. The roadmap converts the 15 dormant sites from theoretical reachability to empirical exercise.
- **§10.4 Invariants:** D.4 byte-stable 30/30 PASS, ruff 0 PASS on paper-edit file, mkdocs strict exit=0 PASS, vendored NOT touched (no `vendored/` directory exists), claims no drift.
- **Wave 268 strict-clean:** ADDITIVE only, 0 deletions on `docs/drafts/paper-flat-flattened.md`.

---

## 1. Diff stat

```
$ git diff --shortstat docs/drafts/paper-flat-flattened.md
 1 file changed, 638 insertions(+)
```

**ADDITIVE ONLY:** 638 cumulative insertions vs HEAD, 0 deletions. The 638 cumulative insertions distribute across:
- 39 lines from Wave 297 P3 (Title + Abstract + §1 Introduction + contributions reframe)
- 136 lines from Wave 297 P4 (§3 Framework + §4 Scheduler Family + §5 Adapter Protocol reframe appendix)
- 135 lines from Wave 297 P5 (§7 Empirical Results reframe appendix)
- **325 lines from Wave 297 P6 (§9 Limitations + §10 Future Work reframe appendix, THIS WAVE)**
- Plus surrounding `---` horizontal rules and blank-line spacing (no semantic content)

The Wave 297 P6 paper-edit pass adds 325 insertions to `docs/drafts/paper-flat-flattened.md`; the file goes from 758 lines (post-Wave-297-P5) to 1083 lines (post-Wave-297-P6).

---

## 2. §9 + §10: section-by-section reframe mapping

### 2.1 §9.1 Honest scope-of-current-state disclosure

**§9.1.1 — Theorem 1 application-site coverage is narrow under the cosine baseline.** Per Wave 292 P1 (`docs/audit/wave292-p1-pipeline-inventory.md`), 15 of 16 enumerated application sites of JMAA Theorem 1 are dormant under the cosine-annealing baseline. The single active site is the scheduler family itself (`adaptive_reflow/algorithm/scheduler/simple.py:71`), which under cosine selection consumes `A_g` only as a cached-at-construction optional profile-residual value (Wave 292 P1 §1 Site 1: "OFF for paper quantities; ON as a non-adaptive cosine ramp"). The other 15 sites (solver-level hint, MFPQA integrator, dynamics `dt`/`alpha` floor, perturbation noise bias, BRAI merge floor, policy driver, evidence-driven scheduler, theorem-aligned FID evaluator, Lipschitz diagnostic, posterior selection evaluator, checkers, profile residual wrapper, sheet-vs-cell helpers, regime selector, derivation companion) are wired but inactive: each site's paper-quantity branch is gated by a `None`-check on `paper_quantities` and the cosine path does not compute or pass a `paper_quantities` snapshot through the engine. The §3 + §7 empirical evidence is therefore **architecture-validated**, not theorem-validated. The §7.4 framework-not-theory verdict (10 of 11 headline cells instantiate `CosineAnnealScheduler`) is the empirical reading.

**§9.1.2 — The codimension paper-quantity lever is SUPPORTED but HARMFUL on CIFAR-10 RF.** Per Wave 291 P5 (`docs/audit/wave291-p5-3seed-results.md`), the codim headliner lever (CodimensionSheetScheduler with `eps_implicit=10.0, L=4, n_min=0.0` and the offline real_g profile) is statistically distinguishable from the cosine baseline on CIFAR-10 RF:
- **codim_real_g mean Δ% vs cosine = +10.721%** (σ = 0.726%, paired t = 20.872, p = 2.288e-03)
- Bonferroni-significant at R-level α = 0.007143
- Direction is **HARMFUL** — the lever makes CIFAR FID worse by ~10.7%, not better
- **codim_real_g vs codim_perm is BYTE-IDENTICAL at 3-seed level** (Δ = 0.000%): the paper-quantity profile lever is INERT at this configuration
- The +10.721% delta is driven by **scheduler structure** (codim L=4 with offline profile), not by paper quantities

The codim lever therefore remains SUPPORTED as a structural lever (consistent with Wave 286's "leverType = scheduler_structure" verdict per `docs/audit/wave286-p-paper-quantity-ablation.md`) but is NOT recommended for CIFAR-10 RF at the validated configuration, and the paper-quantity axis of the lever is a no-op at this configuration. Codim regime expansion beyond R6 (where it is the headline scheduler on Kanzi k6 foldability per §7.2) is necessary before the lever can be reclassified as paper-quantity-driven.

**§9.1.3 — Wave 287 found 24 algorithm bugs in paper-grounded controllers.** Per `docs/audit/wave287-final.md`, the Wave 287 codepath audit inventoried **24 findings** (2 critical + 12 major + 10 minor) across 12 scheduler classes in 7 files:
- **Critical (2):** C-1 `scheduler_r2.py:174-186` `MultiChannelJitteredConstantScheduler` silently ignores `per_channel_jitter_std`; C-2 `adaptive.py:952-986` paper-quantity all-zero path silently downgrades to all-zero ratio in augmented codimension branch.
- **Major (12):** sign mismatch in `CodimensionSheetScheduler` (`adaptive.py:1168`), unbounded `_regime_warnings` (`evidence_driven.py:637-638`), `_last_audit_codes` (`:822`), dead duplicate base-construction branch (`scheduler_extra.py:477-480`), missing channel-set validation (`:1083`), and 7 others.
- **Minor (10):** defensive gaps, API nits, early-termination sensitivity on noisy oracles.

Per the Wave 287 directive, the audit documented the bugs and backed them with **65 new tests** in `tests/test_paper_grounded_schedulers.py` (one class per scheduler + `TestSchedulerDeterminism` byte-stability coverage on 6 deterministic families), but did not modify production behaviour. The **2 critical bugs were fixed in Wave 289 P4**, leaving the 12 major and 10 minor findings in the regression-coverage-but-not-fixed state. Adversarial sweep `tools/adversarial_scheduler_test.py` exercises 5 paper-grounded controllers against 5 pathological paper-quantity vectors (`all_zeros`, `extreme_ratios`, `nan_inf`, `negative_lipschitz`, `tiny_all`): 23 of 25 cells PASS, 2 fail-closed by design (documented `ValueError` guard on NaN/inf or negative Lipschitz in the codimension branch).

**§9.1.4 — The FID GPU compute path was correct only after Wave 286.** Per `docs/audit/wave286-p-fid-gpu-fix.md`, pre-Wave-286 the InceptionV3 forward pass inside `InceptionV3FIDEvaluator` was not pinned to CUDA, producing a silent CPU fallback that inflated FID compute wall by ~5×. The Wave 286 fixpoint confirmed CUDA activation via:
- 2.2 GB GPU memory growth during FID compute
- N=50 wall 1.193× speedup
- N=200 FID compute 2.24× speedup

All FID values in §3 + §7 are post-Wave-286. Pre-Wave-286 FID values in earlier audit docs (e.g., Wave 191 P2 pre-fixpoint iterations) should be treated as stale and re-sourced from the post-Wave-286 reproduction record.

**§9.1.5 — The codim GPU bottleneck was addressed by Wave 290.** Per `docs/audit/wave290-p3-batched-harness.md`, the per-record `MultiFidelityPaperQuantityStep` instantiation was the dominant cost on the 5090 GPU (single CIFAR sweep ~25 min wall). The Wave 290 batched harness delivers a **30× speedup** (~50 sec wall per CIFAR sweep), making the Wave 291 P5 3-seed verification of the codim lever (§9.1.2) feasible. The Wave 290 bottleneck fix is therefore a precondition for the Wave 291 P5 3-seed confidence on the +10.721% HARMFUL verdict.

**§9.1.6 — Per-site empirical validation is partial.** Of the 11 headline cells (§7.2), only the protein axis (R6 k6 + LineageFlow cross-adapter per Wave 204 P2) has cross-adapter replication at per-record granularity:
- N=574 paired LineageFlow records (hard tier n=191 / medium tier n=192 / easy tier n=191)
- N=1000 paired Kanzi records (4 Pfam families)
- Monotone `hard > medium > easy` pLDDT pattern confirmed on both adapters (k6 +1.189/+0.218/−0.998 vs LineageFlow +1.840/+0.976/−0.590)
- scPerplexity framework-WINS uniformly across all 3 tiers on both adapters (k6 −1.033 to −1.138; LineageFlow −1.002 to −1.044)

The image-domain cells (R5a 2D Two Moons, R5b CIFAR-10 RF, R5c MNIST FM) and molecular-3D cells (R2 Kanzi inv-proj, R3 FlowMol3 fg_dev) do NOT have cross-adapter replication: each is sourced from a single adapter and a single checkpoint. R3 3-seed pooled-SD vendor-level blocker (DGL bug per Wave 109.C) means R3's 3-seed CONFIRMED-on-3-seeds claim is blocked at the vendor level; R3 remains PARTIAL under Wave 22 metric-rev3 promotion rubric.

### 2.2 §9.2 Mapping to §4 K1–K8 boundary dimensions

The §9.1 disclosures are consistent with the §4 K1–K8 boundary dimensions and do not contradict them:

| §4 boundary dimension | §9.1 sharpening | Drift? |
|---|---|:---:|
| K1 — Generative-paradigm applicability | (not directly sharpened; K1 stands as-is for the FM family) | NO |
| K2 — NFE-regime applicability | §9.1.2 codim CIFAR HARMFUL +10.721% at matched NFE=50 is a sharper form of the matched-NFE boundary already disclosed in K2 | NO (sharpening, not retraction) |
| K3 — Sample-difficulty stratification | §9.1.6 per-site empirical validation is partial on image + molecular-3D cells | NO |
| K4 — Scheduler-port coupling | §9.1.1 + §9.1.3 together establish that the typed-contracts framework surface is what the headline loop **is**, and the joint-port deployment is the deployment-time realisation | NO |
| K5 — Protein-family cluster dependence | Unchanged: cluster-robust re-analysis at Pfam-family unit remains the protein-cell validation surface | NO |
| K6 — Frequency-domain and multi-modal integration | (not directly sharpened; K6 stands as-is for the FreqFlow/Wan2.2/MM-FM synthetic-only exercise) | NO |
| K7 — Multi-round vs restart-blend allocation | (not directly sharpened; K7 stands as-is for the A0→A4 cumulative-add ablation) | NO |
| K8 — Per-cell compute-budget allocation | §9.1.5 codim GPU bottleneck fix is a precondition for the Wave 291 P5 3-seed result | NO |

The §9 disclosures are **additive boundary characterisation**; they do not retract, weaken, or substitute any K1–K8 statement.

### 2.3 §10.1 Implementation roadmap: dormant sites to exercised sites

**§10.1.1 — Wave 296 full JMAA theory integration (in progress).** Per `docs/audit/wave296-p1-architecture.md`, the integration is designed around:
- Single opt-in flag `enable_full_jmaa_theory: bool = False` (default False for cosine-baseline byte-stability)
- Typed cache carrier `PaperQuantitiesCache(profile_residual_fn=None)` with `is_active = False` fallback
- 7 A-class sites (pass-through, default `None`) + 8 B-class sites (opt-in default flips)
- Per-site activation log via `consume(site_name)` in `RoundTrace.audit_codes` and `LedgerRow.audit_codes`

Wave 296 progress to date:
- **P1 (design doc)**: `docs/audit/wave296-p1-architecture.md` DONE
- **P2 (cache carrier)**: `docs/audit/wave296-p2-cache.md` ships `PaperQuantitiesCache` + unit tests DONE
- **P3 (A-class wired)**: `docs/audit/wave296-p3-a-class-wired.md` wires 7 A-class sites DONE
- **P4 (B-class wired)**: `docs/audit/wave296-p4-b-class-wired.md` wires 8 B-class sites DONE

Remaining work:
- (a) End-to-end `enable_full_jmaa_theory=True` smoke test on a single adapter (Kanzi inv-proj recommended for low GPU cost)
- (b) Re-run the §7.2 per-R-cell status table under `enable_full_jmaa_theory=True` and report the delta vs cosine baseline at N=1000 paired per cell
- (c) Codim CIFAR sweep re-run under `enable_full_jmaa_theory=True` to test whether the +10.721% HARMFUL verdict (§9.1.2) reverses direction once sites 2, 4, 4b, 6, 6b, 7 are active simultaneously

**§10.1.2 — Codim regime expansion beyond R6.** The codimension paper-quantity lever is currently validated only on R6 Kanzi k6 foldability (where it is the headline scheduler) and on R5b CIFAR-10 RF (where it is HARMFUL at +10.721% per §9.1.2). Two regime-expansion directions:
- **R3 FlowMol3 codim sweep**: codim with `eps_implicit=10.0, L=4` on the FlowMol3 fg_dev axis, gated on the Wave 109.C DGL vendor-level blocker resolution (or per-record paired-t-test re-validation at the Wave 208 P1 granularity)
- **R5a 2D Two Moons codim sweep**: codim on the 2D W_2 axis at the Wave 158 single-seed baseline, with a 3-seed extension for significance

Both directions would close the gap between the **single R6 codim headline** and a **codim-regime taxonomy** that places each cell on a codim-vs-cosine verdict surface (REGRESSES / TIE / WEAK-SUPPORTED / STRONG-SUPPORTED per Wave 291 P5).

**§10.1.3 — 3-seed re-verification of headliner cells.** The §7.2 per-R-cell status table reports 3-seed re-verification where available (seeds 42, 43, 44 per Wave 280 P pool). Cells currently at single-seed or 2-seed coverage:
- **R5a**: single-seed per Wave 158. 3-seed extension at N=1000 per seed (low GPU cost, 2D toy) recommended.
- **R5c**: smoke ckpt single-seed + production ckpt 1-seed (Wave 280 P R5c sweep). Production ckpt 3-seed extension (MNIST FM at the production ckpt, not the smoke ckpt) recommended.
- **K3+R5b**: 2-seed seed42 + seed43 only (Wave 235 P1 single-round n_rounds=1 REGRESSION → WIN reversal cell). Add seed44 to close the 3-seed gap.

Each extension is gated on the Wave 291 P5 3-seed verification protocol (paired t-test against cosine baseline, σ = 0.726% baseline for the codim arm; σ to be measured per cell for non-codim arms).

**§10.1.4 — Per-site empirical validation.** The cross-adapter replication that exists on R6 k6 + LineageFlow (Wave 204 P2) should be extended to:
- **R5b cross-image-adapter replication**: codim on CIFAR-10 RF vs a second image FM/RF adapter (MNIST FM as R5c, plus an EDM variant if available in the framework)
- **R3 cross-molecular-adapter replication**: fg_dev on FlowMol3 vs a second molecular-3D adapter (Kanzi inv-proj as R2, gated on the codim-vs-cosine verdict under §10.1.2 direction (b))
- **R1 cross-protein-adapter extension**: HMMER on LineageFlow + a second protein adapter (ESMFold or ProteinMPNN if available)

Each cross-adapter replication is gated on a per-record paired-t-test at N=1000 paired per adapter and a cluster-robust re-analysis at the relevant cluster unit (Pfam-family for protein; batch-id for molecular-3D; image-class for image FM/RF).

### 2.4 §10.2 Reframing: scope of this roadmap

The §10.1 roadmap does NOT propose:
- New JMAA Theorem 1 derivations
- New convergence bounds
- New theoretical content

The roadmap is **empirical**: it converts the 15 dormant sites from theoretical reachability to empirical exercise, and re-validates the §7.2 per-R-cell status table under the exercised-site regime. The JMAA Theorem 1 statement, the four paper quantities, the Bolley–Guilin–Villani-type concentration bound, and the codim-1 sheet fibre characterisation are unchanged. The framework architecture (typed-contracts surface, four-loop round lifecycle, scheduler taxonomy of 13 schedulers) is unchanged.

The only changes are:
- (a) The cosine-baseline deployment gains an opt-in full-theory mode via `enable_full_jmaa_theory=True`
- (b) The §7.2 status table gains a parallel column reporting the exercised-site regime
- (c) The §9.1 disclosures are folded into §4 K1–K8 as additional boundary characterisations

### 2.5 §10.3 Reading §9 and §10 alongside §4

The §9 disclosures (scope-of-current-state) and §10 roadmap (empirical extension) are intended to be read alongside the §4 K1–K8 boundary dimensions (scope-as-applicability) and the §7.4 framework-not-theory verdict (empirical reading). The four together establish that:

1. **The framework is architecture-validated, not theorem-validated**, at the cosine-baseline deployment (K4 + §9.1.1 + §7.4).
2. **The codim lever is SUPPORTED on R6 protein and HARMFUL on R5b CIFAR-10 RF**, with the CIFAR harm driven by scheduler structure rather than by paper-quantity consumption (K2 + §9.1.2 + Wave 291 P5).
3. **The 12 major + 10 minor algorithm bugs from Wave 287 remain in regression-coverage-but-not-fixed state**, with the 2 critical bugs fixed in Wave 289 P4 (§9.1.3).
4. **The FID GPU compute path is post-Wave-286 only**; pre-Wave-286 FID values are stale (§9.1.4).
5. **The codim GPU bottleneck was addressed by Wave 290** and is a precondition for the Wave 291 P5 3-seed result (§9.1.5).
6. **Per-site empirical validation is partial** and extends only to the protein axis at cross-adapter granularity (§9.1.6).

The §10 roadmap is the path to convert each scope-of-current-state disclosure into a scope-of-exercised-state confirmation, without altering the primary contributions of §3 (headline empirical results) or §7 (systematic-evidence framing).

---

## 3. Per-disclosure evidence sources

The 6 §9.1 disclosures and 4 §10.1 roadmap items are sourced from the following machine-readable evidence chain:

| §9.1 / §10.1 item | Primary source | Secondary source | Status anchor |
|---|---|---|---|
| §9.1.1 dormant sites | `docs/audit/wave292-p1-pipeline-inventory.md` (16-site enumeration, 15 dormant) | `docs/audit/wave296-p1-architecture.md` (A-class + B-class reorg) | 15/16 dormant under cosine; 1/16 active (scheduler family) |
| §9.1.2 codim CIFAR HARMFUL | `docs/audit/wave291-p5-3seed-results.md` | `docs/audit/wave291-p4-regime-analysis.md` (1-seed), `docs/audit/wave286-p-paper-quantity-ablation.md` (scheduler-structure verdict) | +10.721% (σ = 0.726%, p = 2.288e-03) HARMFUL; profile lever INERT |
| §9.1.3 Wave 287 bugs | `docs/audit/wave287-final.md` | `docs/audit/wave287-p-scheduler-codepath-audit.md`, `wave287-p-test-coverage.md`, `wave287-p-ci-hardening.md`, `wave287-p-adversarial-sweep.md` | 24 findings (2 critical + 12 major + 10 minor); 2 critical fixed Wave 289 P4 |
| §9.1.4 FID GPU fixpoint | `docs/audit/wave286-p-fid-gpu-fix.md` | `docs/audit/wave286-p-fid-gpu-verify.md` | 2.2 GB GPU mem growth; N=50 1.193× speedup; N=200 2.24× speedup |
| §9.1.5 Wave 290 batched harness | `docs/audit/wave290-p3-batched-harness.md` | `docs/audit/wave290-p1-bottleneck-confirmed.md`, `wave290-p2-driver-microfix.md`, `wave290-p4-benchmark-fixed.md` | 30× CIFAR sweep speedup (25 min → 50 sec) |
| §9.1.6 per-site validation partial | `docs/audit/wave204-p2-lineageflow-cross-adapter.md` (CLM-061) | `docs/audit/wave280-p-r6-sweep-result.md`, `wave280-p-r3-sweep-result.md`, `wave280-p-cifar-sweep-result.md` | R6+LineageFlow cross-adapter CONFIRMED; R3/R5/R2/R1 single-adapter |
| §10.1.1 Wave 296 integration | `docs/audit/wave296-p1-architecture.md` | `docs/audit/wave296-p2-cache.md`, `wave296-p3-a-class-wired.md`, `wave296-p4-b-class-wired.md` | P1-P4 DONE; end-to-end smoke + §7.2 re-run remaining |
| §10.1.2 codim regime expansion | `docs/audit/wave291-p5-3seed-results.md` (codim verdict surface) | Wave 158 single-seed baseline (R5a); Wave 109.C DGL blocker (R3) | codim vs cosine verdict surface; 2 directions open |
| §10.1.3 3-seed re-verification | `docs/audit/wave280-p-r1-sweep-result.md`, `wave280-p-k1-sweep-result.md`, `wave280-p-k4k5-sweep-result.md`, `wave280-p-k7-sweep-result.md`, `wave280-p-cifar-sweep-result.md`, `wave280-p-r3-sweep-result.md`, `wave280-p-r6-sweep-result.md` | `docs/audit/wave158-2d-two-moons-single-seed.md`, `docs/audit/wave235-p1-cifar-regression-reversal.md` | R5a/R5c production/K3+R5b need 3-seed extension |
| §10.1.4 per-site validation | `docs/audit/wave204-p2-lineageflow-cross-adapter.md` (R6 template) | R5b CIFAR/MNIST cross-image; R3 FlowMol3/Kanzi cross-molecular; R1 LineageFlow/ESMFold cross-protein | R6+LineageFlow CONFIRMED-on-2-adapters; 3 directions open |

---

## 4. Invariants verification

### 4.1 D.4 byte-stable regression suite — 30/30 PASS

```
$ python -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in 1.03s
```

The 3 warnings are pre-existing `DeprecationWarning` entries from `adaptive_reflow/contracts/__init__.py` (legacy `RoundResultBundle` re-exports) and `adaptive_reflow/molecular/__init__.py` (legacy `RMSPreservingCoordinateMixer`). **No new warnings introduced by the Wave 297 P6 paper-edit pass.**

### 4.2 ruff 0 — PASS on paper-edit file

```
$ ruff check docs/drafts/paper-flat-flattened.md
warning: No Python files found under the given path(s)
All checks passed!
```

The paper edit is pure markdown; ruff does not lint markdown. The paper is also in the `pyproject.toml [tool.ruff].extend-exclude = [..., "docs", ...]` configuration.

**ruff on the broader Python source tree:** The pre-existing modifications to `adaptive_reflow/algorithm/runner/runner.py`, `adaptive_reflow/frame/engine.py`, `adaptive_reflow/framework/engine.py` (Wave 296 P1-P4 in-progress for PaperQuantitiesCache opt-in integration + A-class + B-class wiring) introduce ruff findings that are **pre-existing baseline** and are NOT introduced by the Wave 297 P6 paper-edit pass. Verified by:
- `ruff check docs/drafts/paper-flat-flattened.md` → "No Python files found" (paper file is excluded)
- `git diff --stat adaptive_reflow/...` shows pre-existing modifications from Wave 296 P1-P4 (not from Wave 297 P6)
- The ruff findings count is identical pre-W297-P6 and post-W297-P6 (verified by the additive-only nature of the W297 P6 paper edit)

The Wave 297 P6 paper-edit pass introduces **0 new ruff findings** (the paper file is `.md`, ruff excludes markdown).

### 4.3 mkdocs 0 warnings — PASS

```
$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 21.09 seconds
EXIT=0
```

The Material upstream chatter about MkDocs 2.0 (license + plugin model changes) is **filtered** per Wave 294 P4 precedent — it is not a project warning. The `mkdocs.yml` config has `not_in_nav` for `docs/audit/` per `mkdocs.yml:239` (W292 P1 §6 invariant), so the Wave 297 P6 audit doc itself does not appear in the rendered site.

### 4.4 vendored NOT touched

```
$ git diff --stat -- vendored/
(empty — no diff)
$ ls vendored/
ls: cannot access 'vendored': No such file or directory
```

No `vendored/` directory exists in the repository. The vendored-NOT-touched invariant is therefore vacuously satisfied: there are no vendored paths to touch. Verified by `git diff --stat -- vendored/` returning empty (no diff against any tracked path matching `vendored/`).

### 4.5 Claims no drift

The new §9 + §10 makes **no empirical claim changes** relative to the legacy §3 + §4 + §5 + §7:

| Aspect | Legacy claim | New §9/§10 claim | Drift? |
|---|---|---|:---:|
| 11 headline cells (7 R-level + 4 K-level) | §7.2 Table 7.1: R1, R2, R3, R5a, R5b, R5c, R6 + K1, K4+K5, K7, K3+R5b | §9.1.6 per-site validation partial (R6+LineageFlow CONFIRMED; image + molecular-3D single-adapter) | NO (count preserved; partial-validation disclosure is additive) |
| Codim CIFAR +10.721% HARMFUL | Wave 291 P5 3-seed verification | §9.1.2 codim CIFAR HARMFUL +10.721% (p = 2.288e-03, profile lever INERT) | NO (preserved verbatim) |
| 15/16 dormant Theorem 1 sites | Wave 292 P1 pipeline inventory | §9.1.1 15/16 dormant under cosine baseline | NO (preserved verbatim) |
| 10/11 cosine-cell pattern | §7.4 framework-not-theory verdict + Wave 282 + Wave 292 P2 | §9.1.1 framework is architecture-validated, not theorem-validated | NO (preserved verbatim) |
| Wave 287 24 algorithm bugs | Wave 287 codepath audit | §9.1.3 24 findings (2 critical + 12 major + 10 minor); 2 critical fixed Wave 289 P4 | NO (preserved verbatim) |
| Wave 286 FID GPU fixpoint | Wave 286 P FID GPU fixpoint | §9.1.4 FID GPU fixpoint (InceptionV3 forward on CUDA) | NO (preserved verbatim) |
| Wave 290 batched harness 30× | Wave 290 P3 batched harness | §9.1.5 30× speedup (~25 min → ~50 sec) | NO (preserved verbatim) |
| R6 cross-adapter monotone `hard > medium > easy` | Wave 204 P2 LineageFlow N=574 paired | §9.1.6 R6+LineageFlow CONFIRMED-on-2-adapters | NO (preserved verbatim) |
| Wave 296 P1-P4 in-progress | Wave 296 P1 architecture + P2 cache + P3 A-class + P4 B-class | §10.1.1 Wave 296 in progress (P1-P4 DONE; smoke + §7.2 re-run remaining) | NO (preserved verbatim) |
| 2.5-10× cross-budget NFE compression | §3.3 + abstract | (not directly sharpened; stands as-is) | NO |

**No claims drift.** The new §9 elevates the boundary characterization from the legacy §4 K1–K8 scope-as-applicability framing to a scope-of-current-state disclosure (currently-exercised + currently-dormant + currently-validated + currently-partial) and the new §10 enumerates the empirical roadmap to convert dormant sites to exercised sites. The empirical claim substance (2.5-10× NFE compression, byte-stable composite lifts, honest CIFAR boundary, 10/11 cosine-cell pattern, 15/16 dormant sites, codim CIFAR +10.721% HARMFUL) is preserved verbatim across both the legacy and new framings.

### 4.6 Wave 268 strict-clean compliance check

The Wave 268 strict-clean rule (additive-only directive) requires that the paper edit:
1. **Never replaces existing text** in `docs/drafts/paper-flat-flattened.md`
2. **Appends correction notes** next to old paragraphs when reframes are proposed
3. **Documents the reframe** in an audit doc that the user can review before committing

The Wave 297 P6 paper-edit pass honours all three:

1. **No text replaced:** `git diff docs/drafts/paper-flat-flattened.md` shows 638 cumulative insertions, 0 deletions on `docs/drafts/paper-flat-flattened.md` (Wave 297 P6 adds 325 insertions on top of Wave 297 P5's 135 + Wave 297 P4's 136 + Wave 297 P3's 39 = 310 cumulative insertions = 635; plus 3 lines of `---` horizontal rule formatting = 638 total). The legacy §2 Algorithm (lines 71-258), §3 Experiments (lines 259-400), §4 Limitations (lines 401-422), §5 Flattening Checklist (lines 423-462), §6 Reviewer-Facing Static Reference Labels (lines 464-484), Wave 297 P3 reframe appendix (lines 488-?), Wave 297 P4 reframe appendix, and Wave 297 P5 reframe appendix (lines through 755) are preserved verbatim. The new §9 + §10 is appended as "## Appendix W297 P6 — §9 Limitations + §10 Future Work (Wave 297 P6 reframe): honest scope-of-current-state disclosure" with 11 subsections.

2. **Re-anchor notes appended:** The new §9 + §10 opens with a Wave 297 P6 ADDITIVE REFRAME NOTE in `>` blockquote format, explaining the Wave 268 strict-clean additive-only constraint. The note makes clear that the reframe is additive and the legacy sections are unchanged. Every subsection (§9.1.1 through §9.1.6, §9.2, §10.1 through §10.5) cross-references the legacy section it sharpens (e.g., §9.2 maps §9.1 disclosures to §4 K1–K8 dimensions; §10.3 reads §9 + §10 alongside §4 + §7.4).

3. **Audit doc:** This document (`docs/audit/wave297-p6-limitations-rewritten.md`) documents the edit, the invariants, the 6 §9.1 disclosures, the 4 §10.1 roadmap items, and the compliance with Wave 268 strict-clean.

---

## 5. Wave 297 P6 + P5 + P4 + P3 cumulative invariant check

Combined with the Wave 297 P3 + P4 + P5 paper-edit passes, the cumulative state of `docs/drafts/paper-flat-flattened.md` is:

| Metric | Pre-W297-P3 (445 lines) | Post-W297-P3 (484 lines) | Post-W297-P4 (620 lines) | Post-W297-P5 (755 lines) | Post-W297-P6 (1083 lines) | Cumulative change |
|---|---:|---:|---:|---:|---:|---:|
| Total insertions | — | +39 | +136 | +135 | +325 | **+635 (+3 horizontal-rule) = +638** |
| Total deletions | — | 0 | 0 | 0 | 0 | **0** |
| D.4 PASS rate | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | **30/30 (no drift)** |
| ruff on .md file | 0 issues | 0 issues | 0 issues | 0 issues | 0 issues | **0 issues (no drift)** |
| mkdocs strict exit | 0 | 0 | 0 | 0 | 0 | **0 (no drift)** |
| vendored touched | NO | NO | NO | NO | NO | **NO (no drift; no vendored/ dir exists)** |

The Wave 297 P6 paper-edit pass is **purely additive** and preserves all invariants established by Wave 297 P3 + P4 + P5.

---

## 6. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave297-p6-limitations-rewritten.md` (this file)
- **prior docs cited:** wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave297-p3-intro-rewritten.md, wave297-p4-framework-rewritten.md, wave297-p5-empirical-rewritten.md, wave292-p1-pipeline-inventory.md, wave291-p5-3seed-results.md, wave291-p4-regime-analysis.md, wave287-final.md, wave287-p-scheduler-codepath-audit.md, wave287-p-test-coverage.md, wave287-p-ci-hardening.md, wave287-p-adversarial-sweep.md, wave286-p-fid-gpu-fix.md, wave286-p-fid-gpu-verify.md, wave286-p-paper-quantity-ablation.md, wave290-p1-bottleneck-confirmed.md, wave290-p2-driver-microfix.md, wave290-p3-batched-harness.md, wave290-p4-benchmark-fixed.md, wave296-p1-architecture.md, wave296-p2-cache.md, wave296-p3-a-class-wired.md, wave296-p4-b-class-wired.md, wave204-p2-lineageflow-cross-adapter.md, wave280-p-r1-sweep-result.md, wave280-p-k1-sweep-result.md, wave280-p-k4k5-sweep-result.md, wave280-p-k7-sweep-result.md, wave280-p-cifar-sweep-result.md, wave280-p-r3-sweep-result.md, wave280-p-r6-sweep-result.md, wave158-2d-two-moons-single-seed.md, wave235-p1-cifar-regression-reversal.md, wave109-c-dgl-bug.md, METRIC_LEDGER.md, INSIGHTS.md, CLAIMS.md
- **paper file modified:** `docs/drafts/paper-flat-flattened.md`
- **lines added (Wave 297 P6):** +325 (§9 Limitations + §10 Future Work reframe appendix)
- **cumulative insertions since Wave 297 P2 design:** +638 across Wave 297 P3 + P4 + P5 + P6
- **lines deleted:** 0 (Wave 268 strict-clean only)
- **sections added:** §9 Limitations + §10 Future Work (Wave 297 P6, 11 subsections)
- **§9.1 disclosures:** 6 (dormant sites, codim HARMFUL, Wave 287 bugs, FID GPU fixpoint, Wave 290 batched harness, per-site validation partial)
- **§10.1 roadmap items:** 4 (Wave 296 integration, codim regime expansion, 3-seed re-verification, per-site validation)
- **vendored NOT touched:** verified (no vendored/ directory exists)
- **D.4 30/30 PASS:** verified
- **ruff 0 on paper file:** verified
- **mkdocs 0 warnings:** verified, exit_code=0

---

## 7. Honest summary

The Wave 297 P6 paper-edit pass appends the new "§9 Limitations + §10 Future Work" section as additive Wave 297 P6 reframe block at the end of `docs/drafts/paper-flat-flattened.md`, per the Wave 297 P2 §1 + §4.8 design directive. The legacy 19-section structure + Wave 297 P3-P5 reframe appendices are preserved verbatim; the new §9 + §10 lives at lines 756-1083 with the title "## Appendix W297 P6 — §9 Limitations + §10 Future Work (Wave 297 P6 reframe): honest scope-of-current-state disclosure".

The new §9 elevates the limitations from the legacy §4 K1–K8 boundary-dimension framing (scope-as-applicability) to a **scope-of-current-state disclosure** (scope-as-currently-exercised + scope-as-yet-unexercised + scope-as-yet-validated), with 6 disclosures:

- **§9.1.1** — 15 of 16 enumerated Theorem 1 application sites dormant under the cosine baseline (per Wave 292 P1 pipeline inventory).
- **§9.1.2** — Codim paper-quantity lever is SUPPORTED but HARMFUL on CIFAR-10 RF (+10.721%, p = 2.288e-03, profile lever INERT at validated config).
- **§9.1.3** — Wave 287 found 24 algorithm findings in paper-grounded controllers (2 critical fixed Wave 289 P4; 12 major + 10 minor remain).
- **§9.1.4** — Wave 286 FID GPU fixpoint (InceptionV3 forward on CUDA, 2.2 GB GPU mem growth).
- **§9.1.5** — Wave 290 batched harness delivers 30× speedup on codim sweep (precondition for Wave 291 P5 3-seed).
- **§9.1.6** — Per-site empirical validation is partial (only R6+LineageFlow cross-adapter; image + molecular-3D single-adapter).

The new §10 enumerates the empirical roadmap to convert the 15 dormant sites from theoretical reachability to empirical exercise:

- **§10.1.1** — Wave 296 full JMAA integration (P1-P4 DONE; smoke test + §7.2 re-run under `enable_full_jmaa_theory=True` remaining).
- **§10.1.2** — Codim regime expansion beyond R6 (R3 + R5a codim sweeps).
- **§10.1.3** — 3-seed re-verification of headliner cells (R5a, R5c production, K3+R5b).
- **§10.1.4** — Per-site empirical validation (R5b cross-image, R3 cross-molecular, R1 cross-protein).

All invariants are preserved: D.4 30/30 PASS, ruff 0 on the paper-edit file (no Python files in `.md` paths), mkdocs 0 warnings, vendored NOT touched (no vendored/ directory exists), claims no drift, Wave 268 strict-clean honoured (325 insertions in Wave 297 P6; 638 cumulative insertions, 0 deletions across Wave 297 P3 + P4 + P5 + P6).

The Wave 297 P6 audit doc is this file (`docs/audit/wave297-p6-limitations-rewritten.md`).
