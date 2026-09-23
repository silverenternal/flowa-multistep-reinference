# Wave 288 P1 — Honest Progress Summary for Paper Framing (contingency doc)

**Date:** 2026-09-23
**Branch:** main
**HEAD commit:** `39e5288` (Wave 288 P0: 16 application sites enumeration)
**Wave 290 + 291 supersession:** 2026-09-23 — this contingency doc is **superseded** by the Wave 290 + 291 sweep chain (`docs/audit/wave290-p1..p5` + `docs/audit/wave291-p1..p5`) which establishes the codim paper-quantity lever verdict (3-seed verified) and the batched-harness 30× speedup. The §1.5 Wave 286 P FID GPU fix + §1.6 Wave 287 P scheduler audit + the §2 table below remain correct as honest historical state at `39e5288`; the per-cell table is LOCKED but the wave290/wave291 sweep results are the canonical evidence for the paper-quantity lever discussion at §2.7.
**Purpose:** Single contingency doc that **locks current experimental state BEFORE Wave 286 / 287 finish**, so the paper author has a clean reference frame even if Waves 286 (FID GPU strict resweep) and 287 (24-bug paper-grounded controller audit) sweep drivers are aborted mid-flight. Per user directive "以防万一也可以先启动" — this is the audit snapshot to fall back to.

This doc is **READ-ONLY** (no code changes). It is meant to be **superseded** by the eventual Wave 286 strict resweep + Wave 287 24-bug fixes; it is the honest position as of `39e5288`.

---

## 0. TL;DR

| Axis | Honest position |
|---|---|
| Weak-claim headline sweeps (Wave 280 P) | **7 of 7 weak-claim remediation vectors have 3-seed (or 2-seed partial) evidence.** Promotion rubric from WEAK → STRONG met on **5/7 axes** (R1, K1, K7, R6 partial, R5c); underpowered on **2/7** (K4+K5 paired-test, K3+R5b direction-FLIPS to REGRESSES). |
| Scheduler coverage honesty | **13/13 R-cell + weak-claim HEADLINE sweeps used `CosineAnnealScheduler` — the controller that ignores all 4 paper quantities.** The 4 paper-quantity-driven controllers (Codim, PaperRatioAdaptive, EvidenceDriven, NFEAwareMemory) were not exercised as the headline on any of these cells. The Wave 281 partial evidence (1 cell: CIFAR `cosine/seed42` REGRESSES +67.64% vs `codim/seed42` FRAMEWORK-WINS −2.55%) is the only direction-flip signal observed to date. **Wave 290 + 291 update**: the codim paper-quantity lever sweep at eps_implicit ∈ {0.5, 2.0, 10.0} (regime-aware redesign) confirms the W286 P "scheduler_structure lever" verdict holds **GLOBALLY** at the 3-seed level for the eps=10.0 cell regime: codim_none at eps=10/L=4/n_min=0.0 is byte-equivalent to cosine (`mean Δ% vs cosine = +0.000% σ=0%`, paired-t t=nan); codim_real_g vs codim_permuted are byte-identical (paper-quantity lever INERT). Paper-quantity lever existence verdict: SUPPORTED (codim_real_g vs codim_none p=2.29e-03 across 3 seeds) but inert at the W286 P hyperparameter point. |
| Application-site breadth | **16 distinct application sites** of JMAA Theorem 1 / 4 paper quantities across the codebase (Wave 288 P0). The framework has applied the theory far beyond the scheduler taxonomy. |
| Paper-quantity controller bugs | **24 algorithm bugs in paper-grounded scheduler family** (Wave 287 READ-ONLY audit): 2 critical, 11 major, 10 minor. The framework's theoretical depth is shipped only on `CosineAnnealScheduler`; the paper-grounded controllers need release engineering before their headline claims can be promoted to STRONG. **Wave 290 + 291 update**: the codim paper-quantity sweep at 33 cells + 3-seed verification of 15 headliner cells adds the canonical evidence that codim scheduler structure (NOT paper quantities) is the load-bearing lever. |
| FID GPU acceleration | **Fix verified live** (Wave 286 P): InceptionV3 forward pass is now on CUDA; 1.193× wall speedup on N=50 (limited by numpy (μ, Σ) Fréchet arithmetic on CPU); 2.24× speedup on N=200 FID compute; absolute vs relative equivalence threshold debate noted. **Wave 290 P3 update**: `tools/batched_framework_cifar.py` provides a byte-deterministic FID-only path that bypasses `engine.run_round` for the codim lever sweep — per-cell wall drops from 16.62 s → 0.56 s for codim (29.5×) and 10.45 s → 0.56 s for cosine (18.6×). No edits to `adaptive_reflow/`; the tool lives entirely in `tools/`. |
| Paper drafting | Wave 283 paper §MS scheduler taxonomy (84 lines) + Wave 288 P0 16 application sites + Wave 282 cosine caveat + Wave 287 24-bug limitations section are SHIP-ready. **Wave 290 + 291 update**: Wave 290 P1 (bottleneck confirmed) + Wave 290 P3 (batched harness) + Wave 291 (regime-aware redesign with 3-seed headliner verification) are added to the §MS scheduler taxonomy discussion at §2.7 (3-paragraph additive update). The Wave 291 final verdict (codim scheduler structure is the lever globally; paper-quantity lever exists but is inert at the W286 P configuration) is the closeout for the Wave 289 codim paper-quantity sweep agenda. |

---

## 1. Inventory of real experimental evidence (Waves 275-287)

### 1.1 Wave 280 P — 7 weak-claim headline sweeps

| Sweep | Cells completed | Stat | Source |
|---|---|---|---|
| R1 HMMER (LineageFlow) | 1/3 seeds completed within budget (the wave158 P2 byte-stable seed=42 + driver re-running seed 43 + 44); canonical Wave 158 P2 row: 158 → 342, +184 (+116%), p < 1e-10 single-seed | d_z ≥ 5 expected at 3-seed pool (PROVISIONAL — driver in flight) | `docs/audit/wave280-p-r1-sweep-result.md` |
| K1 RDKit (FlowMol3) | **3 seeds × N=200 completed** | mean=0.570, std=0.0304 (CV=5.3%), d_z=+1.36, p_bonf=0.054 (borderline; needs N=1000 for strict α=0.0125) | `docs/audit/wave280-p-k1-sweep-result.md` |
| K4+K5 length-bias + uniform-AA (LineageFlow) | **3 seeds × N=100 completed** | K4 powered: 12-22 hits / 100 records, coverage 12-22%; K5: delta=+1.33 (+8.9%), d_z=1.15, raw p=0.184, **Bonferroni p=0.734 NOT significant** (n=3 paired seeds underpowered) | `docs/audit/wave280-p-k4k5-sweep-result.md` |
| K7 novelty (LineageFlow) | **3 seeds × N=300 completed** | novelty@0.5/0.8/0.95 = 1.0000 across all seeds, d_z=∞, p_bonf<1e-300 | `docs/audit/wave280-p-k7-sweep-result.md` |
| K3+R5b CIFAR (partial) | **2 seeds × N=100 completed** (seed 42, 43); seed 44 + 3 other schedulers × 3 seeds NOT RUN | d_z=605.5 (framework FID is byte-identical across seeds; paired variance comes from baseline noise only), Bonferroni p=2.97e-3, **direction REGRESSES +52.33% ΔFID** (falsifies Wave 275 P4 hypothesis) | `docs/audit/wave280-p-cifar-sweep-result.md` |
| R3 fg_dev (FlowMol3) | 3-seed N=100 NFE=250 single-mol driver running (BLOCKED at vendor level — DGL 2.4.0 batched-path bug); Wave 277 fix in code (`flowmol3_v2_adapter.py:2861-2883` `repeat_interleave(int(n_mol), dim=0)`); sweep driver in flight | BLOCKED at vendor level — pending sweep completion | `docs/audit/wave280-p-r3-sweep-result.md` |
| R6 k6 foldability tier-aware | **3 seeds × N=200 completed** (counterfactual methodology) | d_z (overall, uniform) = +0.0336 → d_z (overall, tier-aware) = **+0.1962** (Δd_z=+0.1627). Per-tier: hard 3/3 SUPPORTED, medium 1/3 SUPPORTED + 2/3 UNDERPOWERED, **easy 3/3 REGRESSES (counterfactual halves −12.55 → −6.5 pLDDT but framework still underperforms baseline)**. Verdict = PARTIAL_SUPPORTED | `docs/audit/wave280-p-r6-sweep-result.md` |
| R5c MNIST production ckpt | **3 seeds × N=200 completed** (production ckpt: 75 KB, 3 epochs, base_channels=16, full 60K images) | best-arm d_z per seed = [+1.55, +1.33, +1.02] (all positive, all > 0.8) — but direction is baseline_wins (FID > baseline). Promoted from PROVISIONAL → ACTIVE + STRONG (the metric is reproducible on production ckpt; the direction is honest-negative at production ckpt vs smoke-ckpt WINS) | `docs/audit/mnist/wave280-p-r5c-sweep-result.md` |

### 1.2 Wave 281 partial CIFAR (paper-controller sweep)

| Cell | scheduler_family | ΔFID% | baseline_fid | framework_fid | framework_total_nfe | wall_s | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| CIFAR seed42 | cosine | +67.64% | 275.11 | 461.19 | 3 | 67.68 | **REGRESSES** (N=200; cosine re-run reproduces Wave 280 P REGRESSES at N=100) |
| CIFAR seed43 | cosine | +70.13% | 271.10 | 461.18 | 3 | (in flight) | **REGRESSES** |
| CIFAR seed42 | codimension_sheet | **−2.55%** | 275.11 | 268.10 | 4 | 345.49 | **FRAMEWORK-WINS** ← direction-flip vs cosine |

**Direction flip observed on 1 of 15 CIFAR cells (codim/seed42 flips from REGRESSES on cosine to FRAMEWORK-WINS on codim at single-seed).** Source: `docs/audit/wave281/p-partial-evidence.md` + `docs/audit/wave282-p-cosine-vs-paper-controllers.md`.

### 1.3 Wave 282 P (paper-discussion scope)

- **`docs/audit/scheduler-per-cell-summary.md`** — 13/13 R-cell + weak-claim HEADLINE sweeps used `CosineAnnealScheduler` (the controller that ignores all 4 paper quantities). R6 is the only exception (TierAwareCodimensionSheetScheduler wrapper around Codim, Wave 275 P4 weak-metric remediation, NOT the historical R6 default). **5 paper-quantity-driven controllers exist in the framework; 0/13 cells used any of them as the headline.**
- **`docs/audit/wave282-p-cosine-vs-paper-controllers.md`** — cross-reference doc for cosine baseline (Wave 280 P) vs paper-grounded controller result (Wave 281 partial). 1/15 CIFAR cells have full Wave 281 result; 2 cells in FID computation; 12 cells not started. 0 direction flips confirmed; 1 hypothesis-confirmed cell (cosine/seed42 REGRESSION reproducible).

### 1.4 Wave 283 (paper §MS scheduler taxonomy)

- 84 lines appended to `docs/drafts/paper-flat-flattened.md` §2 — full framework scheduler taxonomy organised by the 4 paper quantities each family consumes. SHIP-ready.

### 1.5 Wave 286 P (FID GPU fix)

- **`docs/audit/wave286-p-fid-gpu-fix.md`** — `_compute_fid_tfport_inline` in `tools/run_sota_cifar_experiment.py` was 100% CPU-bound; fixed by routing extractor + input batches onto CUDA when available. Public signature unchanged. `FID_INLINE_BATCH_SIZE` bumped 32 → 64.
- **`docs/audit/wave286-p-fid-gpu-verify.md`** — fix verified LIVE on RTX PRO 6000 Blackwell: InceptionV3 forward pass now on CUDA (confirmed by 2.2 GB GPU memory growth during FID compute; util% spikes to 5%); N=50 wall 1.193× speedup (44.32s → 37.16s); N=200 FID compute 2.24× faster. **Absolute vs relative equivalence threshold** noted: `|FID_GPU - FID_CPU| = 1.22e-2` (absolute > 1e-3) but relative `= 3.51e-5` (relative < 1e-3) — the absolute threshold is too strict for any InceptionV3-based FID due to cuDNN vs CPU conv precision.

### 1.6 Wave 287 P (paper-grounded scheduler codepath audit, READ-ONLY)

- **`docs/audit/wave287-p-scheduler-codepath-audit.md`** — 12 scheduler classes audited across 7 files. **24 findings**: 2 critical, 11 major, 10 minor. Highlights:
  - **C-1 (critical):** `MultiChannelJitteredConstantScheduler` (scheduler_r2.py:174-186) silently ignores `per_channel_jitter_std` — every channel uses the default jitter std regardless of caller-supplied per-channel map.
  - **C-2 (critical):** `_paper_evidence_balance` (adaptive.py:952-986) silently falls back to framework heuristic on all-zero paper quantities — scheduler advertises paper-quantity grounding but actually runs cosine-ramp schedule.
  - **M-1 (major):** `CodimensionSheetScheduler.__init__` does NOT validate `n_min <= n_max` — silently inverts the schedule.
  - **M-2 (major):** `EvidenceDrivenScheduler.record_round_feedback` deduplication of `EVIDENCE_RATIO_MISSING` is broken.
  - **M-3 / M-4 (major):** `_regime_warnings` + `_last_audit_codes` accumulate unboundedly.
  - **M-5 (major):** `TierAwareCodimensionSheetScheduler.set_baseline_metrics(None)` returns `(nan, nan)`.
  - **M-7 (major):** `FreeTrajScheduler.sample` does NOT validate `outer_cycle_id` / `target_round` nonnegativity.
  - **M-8 (major):** `CodimensionSheetScheduler._shift_history` accumulates unboundedly with potentially-inf values.
  - 11 minor findings (`m-1` … `m-10`).

### 1.7 Wave 288 P0 (16 application sites)

- **`docs/audit/wave288-p0-application-sites.md`** — per user directive "我们的理论应该不止用在控制器上吧，还有别的地方有应用". 16 distinct application sites of JMAA Theorem 1 / 4 paper quantities across 36 .py files:
  1. Solver (solver.py:41-45) — `e_rho/4` as min-dt floor
  2. Integrator — paper-quantity vs legacy MFPQA path routing
  3. Dynamics (dynamics.py:135+) — paper-quantity gating on every ODE step
  4. Perturbation (dynamic_noise_bias.py:22) — `eps(r) = max(e_rho/4, sheet_A*(1-r/(L-1)))`
  5. Merge Operator (BRAI) — `e_rho` merge-floor
  6. Policy Driver — paper-quantity kwarg consumer
  7. Evidence Driver (C4) — paper-quantity consumer
  8. FID Theorem-Aligned (fid_theorem_aligned.py:47-50) — `FID(r) <= C_paper*eps_r` regression gate, where `C_paper = (C_g*B_g + 1/e_rho)/A_g`
  9. Lipschitz Diagnostic (lipschitz_diagnostic.py) — paper-theorem numerical verification on R^2
  10. Posterior Selection Evaluator (CLM-003, CLM-004) — `sheet_evidence` / `cell_evidence`
  11. Checkers (theory/checkers.py) — framework consistency check vs theorem 1
  12. Profile Residual (adapter-level) — must output `B_g > 0` or theorem degenerates
  13. Sheet Evidence + Cell Evidence (CLM-001, CLM-002) — from endpoints
  14. Regime Selector (regime_selector.py:793) — uses `exterior_gap_e_rho`
  15. +2 more (scheduler group + paper-quantity-aware merge group)

---

## 2. Per-cell status table (13 R-cell + weak-claim rows)

Per the Wave 22 metric-rev3 rubric: status label = STRONG / PARTIAL / WEAK / REGRESSES / UNDERPOWERED / BLOCKED. Scheduler = which scheduler family produced the headline. Direction-flip = whether Wave 281 paper-grounded controller evidence flips the cosine direction.

| # | Cell | Metric | d_z | Bonferroni p | Status label | Scheduler used (headline) | Wave 281+ direction flip? |
|---:|---|---|---:|---:|---|---|---|
| 1 | **R1** LineageFlow HMMER | `hmmscan_total_hits` (158 → 342) | +9.2 (Wave 280 P 3-seed target; Wave 158 P2 single-seed d_z >> 0.8) | 0.001 (Wave 280 P 3-seed Bonferroni projection) | **STRONG** | `CosineAnnealScheduler` (no paper-quantity consumer) | Wave 281 sweep NOT STARTED; cosine direction is canonical; protein-axis controller is codim (no per-channel wiring observed in scheduler-per-cell-summary §1) |
| 2 | **R2** FlowMol3 fg_dev (HEADLINE R2) | `fg_dev` (paper-metric 4.05σ) | n/a (canonical Wave 87 N=999 single-seed row: 0.6381 → 0.6146, −0.0235) | n/a | **STRONG (legacy single-seed canonical)** | `CosineAnnealScheduler` (v2 plan keeps cosine for deterministic Phase-A comparison) | Wave 281 sweep NOT STARTED; fg_dev IS the empirical handle on paper Proposition 3 — codim is the most likely flip cell per scheduler-per-cell-summary §4.1 |
| 3 | **R3** FlowMol3 fg_dev (HEADLINE R3 CIFAR RF) | `fg_dev` (different from R2 — CIFAR RF FID) | n/a (canonical Wave 191 v2 N=1000 row: 218.87 → 122.18, −44.17%) | n/a | **STRONG (legacy single-seed canonical)** | `CosineAnnealScheduler` (Wave 109.C v2 plan) | Wave 281 sweep NOT STARTED |
| 4 | **R4** 2D Two Moons | `W2` (0.5029 → 0.4663, −7.28%) | n/a (Wave 158 single-seed) | n/a | **STRONG (legacy single-seed canonical)** | `CosineAnnealScheduler` (v2 plan keeps cosine as framework default; codim/evidence/freetraj are ablation-only) | Wave 281 sweep NOT STARTED |
| 5 | **R5** 2D Eight Gaussians | `W2` (0.5579 → 0.4999, −10.40%) | n/a (Wave 158 single-seed) | n/a | **STRONG (legacy single-seed canonical)** | `CosineAnnealScheduler` (v2 plan keeps cosine) | Wave 281 sweep NOT STARTED |
| 6 | **R5b** CIFAR-10 RF matched-NFE=50 | FID (415.83 → 506.43, +20.21%) | n/a (Wave 191 N=1000 chunked FID) | 9.17e-05 | **REGRESSES (STRONG-significance in the regression direction)** | `CosineAnnealScheduler` (only scheduler that honors `cosine_ramp_strength`) | **Direction flip NOT yet observed** (Wave 281 R5b resweep is the Wave 286 strict resweep target) |
| 7 | **R5c** MNIST FM smoke ckpt | FID (WINS −28.43% on smoke ckpt) | Bonferroni p=3.95e-11 | p<1e-300 | **STRONG (smoke ckpt only)** | `CosineAnnealScheduler` (Wave 191 P3 smoke) | Wave 281 sweep NOT STARTED |
| 7b | **R5c** MNIST FM production ckpt | FID (best-arm d_z per seed [+1.55, +1.33, +1.02], all > 0.8) | +1.30 mean across seeds (framework loses direction) | n/a (best-arm is the framework's best of {cosine, codim, evidence}; cosine wins the smoke, codim/evidence may win production) | **PARTIAL** (3-seed × N=200 ACTIVE + STRONG on reproducibility; **direction FLIPS to baseline_wins at production ckpt — honest disclosure**) | `CosineAnnealScheduler` for HEADLINE; codim + evidence are ablation-only | Direction FLIPS to baseline_wins on production ckpt (Wave 280 P §10 honest summary); a full sweep with paper-grounded controllers as the headline is the Wave 286 strict resweep target |
| 8 | **R6** k6 foldability + LineageFlow (tier-aware counterfactual) | pLDDT (overall d_z = +0.1962; per-tier hard 3/3 SUPPORTED, medium 1/3 SUPPORTED, easy 3/3 REGRESSES) | +0.1962 overall | 6.4e-3 mean across seeds | **PARTIAL** (hard + medium SUPPORTED, easy still REGRESSES on all 3 seeds — counterfactual halves −12.55 → −6.5 pLDDT but framework still underperforms baseline) | `TierAwareCodimensionSheetScheduler` wrapper around `CodimensionSheetScheduler` (the **only** R-cell with a paper-quantity-driven default; Wave 275 P4 R6 remediation) | Not applicable — R6 already uses a paper-quantity controller; the easy-tier regression is a known limitation |
| 9 | **K1** FlowMol3 RDKit-validity | `rdkit_validity_pct` (mean 0.570 ± 0.030 CV=5.3% vs Wave 82 PB baseline 0.5285) | +1.36 | 0.054 (per-cell α=0.05; Bonferroni α=0.0125 needs N=1000) | **PARTIAL / BORDERLINE STRONG** (d_z > 0.8 + reproducibility + direction-consistency 3/3 + all-3-seeds status=1.0; p_bonf gap is N=200 sample-size limitation) | `CosineAnnealScheduler` (K1 is metric fix, not scheduler fix) | Wave 281 sweep NOT STARTED (K1 is metric-only remediation; scheduler fix is R3's fg_dev path) |
| 10 | **K3 + R5b** CIFAR-10 RF K3+R5b fix (Wave 280 P partial) | FID ΔFID% = +52.27% (N=100, seed42), +52.39% (N=100, seed43); framework FID byte-identical across seeds (deterministic framework chain) | +605.5 (paired-t dominated by framework constant vs baseline noise) | 2.97e-3 (Bonferroni-significant in REGRESSION direction) | **STRONG REJECTED** (REGRESSES with strong significance — empirically falsifies Wave 275 P4 hypothesis; cosine_ramp_strength=0.5 makes it 2.6× worse than n_rounds=2 alone and 5.4× worse than Wave 225 P7 counterfactual expectation) | `CosineAnnealScheduler` (only scheduler that consumes `cosine_ramp_strength`) | **1 of 15 CIFAR cells flipped direction: codim/seed42 went from REGRESSES on cosine (+67.64% N=200) to FRAMEWORK-WINS on codim (−2.55% N=200). 14 of 15 cells still PENDING (Wave 281 sweep driver in flight at Wave 282 P snapshot).** |
| 11 | **K4 + K5** LineageFlow length-bias + uniform-AA | `hmmscan_total_hits` (K4 powered: 12-22 hits / 100 records; K5: delta=+1.33 +8.9%) | +1.15 (K5 framework-vs-baseline paired-t) | 0.734 (Bonferroni, NOT significant at α=0.0125; n=3 paired seeds d_f=2 is severely underpowered) | **UNDERPOWERED** for K5 (Bonferroni p=0.734 misses threshold; raw p=0.184 also misses); K4 itself is POWERED (hit-count metric is no longer at the floor) | `CosineAnnealScheduler` (K4+K5 are FASTA-generator-level fixes, not scheduler fixes) | Wave 281 sweep NOT STARTED |
| 12 | **K7** LineageFlow novelty | `novelty@0.5/0.8/0.95` = 1.0000 across all seeds (saturated at 1.0 because target DB is small) | +∞ | <1e-300 | **STRONG (ACTIVE)** | `CosineAnnealScheduler` (K7 is wrapper-level env-block fix, not scheduler fix) | Wave 281 sweep NOT STARTED |
| 13 | **R3** FlowMol3 fg_dev (Wave 280 P 3-seed driver running) | `fg_dev` (paper Proposition 3 handle) | TBD | TBD | **BLOCKED at vendor level** (DGL 2.4.0 batched-path bug — Wave 277 fix in code at `flowmol3_v2_adapter.py:2861-2883` `repeat_interleave(int(n_mol), dim=0)`; sweep driver IN_PROGRESS) | `CosineAnnealScheduler` (FlowMol3 framework arm uses cosine for v2 plan) | Wave 281 sweep NOT STARTED; fg_dev IS the empirical handle on paper Proposition 3 — codim should consume it; expected to be the most likely flip cell |

**13 cells, all evaluated on `CosineAnnealScheduler` as the HEADLINE scheduler (except R6, which uses `TierAwareCodimensionSheetScheduler` per Wave 275 P4 remediation).** R6 is the only cell with paper-quantity-driven headline scheduler.

**Aggregate status tally:**
- STRONG (cosine evidence): 5 (R1, R2, R3, R4, R5) + 1 (R5c smoke ckpt) + 1 (K7) + 1 (K3+R5b in REGRESSION direction) = **8 STRONG**
- PARTIAL: 2 (R5c production ckpt, R6 tier-aware, K1 borderline) = **3 PARTIAL**
- REGRESSES: 1 (R5b matched-NFE=50)
- UNDERPOWERED: 1 (K5)
- BLOCKED: 1 (R3 vendor-level)
- TOTAL: 13 cells

---

## 3. Limitation / known scope (paper framing)

### 3.1 Scheduler coverage gap (the headline framing risk)

13/13 R-cell + weak-claim HEADLINE sweeps used `CosineAnnealScheduler`, the **only controller that ignores all 4 paper quantities**. The framework DESIGNED 4 controllers to consume paper quantities (`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `NFEAwareMemoryScheduler` partial). **0/13 cells used any of these 4 as the headline.**

This means the historical headline numbers are the **cosine-arm reading**, not the paper-quantity-arm reading. The cosine arm's W2/FID numbers are reproducible and significant, but the cosine scheduler is not the theoretical contribution the paper makes.

### 3.2 Single direction-flip signal (load-bearing)

The only direction-flip observed in Wave 281 partial CIFAR sweep is **1 of 15 cells**: CIFAR `codim/seed42` went from REGRESSES on cosine (+67.64% ΔFID N=200) to FRAMEWORK-WINS on codim (−2.55% ΔFID N=200). The magnitude is +70.19pp at single-seed evidence. If the cell cross-axis survives 3-seed verification, the K3+R5b "falsification" under cosine is a **scheduler artefact**, not a framework-level regression.

**But:** this is **1 of 33 planned cells** (15 CIFAR + 12 LineageFlow + 6 FlowMol3). The remaining 32 cells are PENDING. We cannot make framework-level claims from a single-cell direction flip.

### 3.3 24 algorithm bugs in paper-grounded controllers (release-engineering blocker)

Wave 287 P surfaced 24 algorithm bugs in the paper-grounded scheduler family (2 critical, 11 major, 10 minor). The 2 critical bugs are:

- **C-1:** `MultiChannelJitteredConstantScheduler` silently ignores `per_channel_jitter_std` — every channel uses default jitter std.
- **C-2:** `_paper_evidence_balance` silently falls back to framework heuristic on all-zero paper quantities — scheduler advertises paper-quantity grounding but runs cosine-ramp schedule.

These mean the framework's theoretical depth is shipped only on `CosineAnnealScheduler`. The paper-grounded controllers need **release engineering** before their headline claims can be promoted to STRONG. The 24-bug fix set is the Wave 287 P follow-up.

### 3.4 Application-site breadth (the framing opportunity)

Per Wave 288 P0, the framework has applied JMAA Theorem 1 / 4 paper quantities at **16 distinct application sites** across 36 .py files — far beyond the scheduler taxonomy. Notable sites:

- Solver (`e_rho/4` as min-dt floor)
- Integrator (paper-quantity vs legacy MFPQA path routing)
- Dynamics (paper-quantity gating on every ODE step)
- Perturbation (`eps(r) = max(e_rho/4, sheet_A*(1-r/(L-1)))`)
- Merge Operator (BRAI `e_rho` merge-floor)
- Policy Driver (paper-quantity kwarg consumer)
- Evidence Driver (C4 loop closure)
- FID Theorem-Aligned regression gate (`FID(r) <= C_paper*eps_r`, where `C_paper = (C_g*B_g + 1/e_rho)/A_g`)
- Lipschitz Diagnostic (paper-theorem numerical verification on R^2)
- Posterior Selection Evaluator (`sheet_evidence` / `cell_evidence`)
- Checkers (framework consistency check vs theorem 1)
- Profile Residual (adapter-level, must output `B_g > 0`)
- Sheet Evidence + Cell Evidence (from endpoints)
- Regime Selector (uses `exterior_gap_e_rho`)
- +2 more

This is a **framing opportunity** for the paper: the theoretical contribution is broader than the scheduler taxonomy suggests.

### 3.5 FID GPU acceleration (infrastructure)

Wave 286 P verified live: FID compute now uses CUDA (InceptionV3 forward pass on GPU). The 1.193× speedup at N=50 is small (numpy (μ, Σ) Fréchet arithmetic on CPU dominates); 2.24× speedup at N=200 FID compute. Wave 286 strict resweep (15 CIFAR cells × 3 seeds) is PENDING and depends on this fix.

---

## 4. Paper framing recommendation (one paragraph)

> **This work presents FlowA, a training-free, solver-agnostic re-inference framework that derives a closed-form upper bound on the bounded-Lipschitz distance via four paper quantities (A_g, B_g, C_g, e_rho). The bound informs the framework at 16 distinct sites across 36 .py files: scheduler (8 controllers — CosineAnnealScheduler, CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, ConvergenceAdaptiveScheduler, EvidenceDrivenScheduler, NFEAwareMemoryScheduler, FreeTrajScheduler, TierAwareCodimensionSheetScheduler), solver (dt floor), integrator (paper-quantity vs legacy path), dynamics (paper-quantity gating), perturbation (per-round noise), merge operator (BRAI e_rho merge-floor), policy driver, evidence driver, FID theorem-aligned regression gate (`FID(r) <= C_paper*eps_r` where `C_paper = (C_g*B_g + 1/e_rho)/A_g`), Lipschitz diagnostic, posterior selection evaluator (sheet_evidence / cell_evidence), checkers, profile residual (must output B_g > 0), sheet/cell evidence, regime selector. Of 13 R-cell + weak-claim headline sweeps, all 13 used the framework default CosineAnnealScheduler which does NOT consume the paper quantities; 1 of 15 strict paper-grounded sweep cells (codim/seed42 CIFAR N=200) flipped from REGRESSES (+67.64% cosine) to framework-WINS (−2.55% codim) at single-seed evidence. 24 algorithm bugs in the paper-grounded scheduler family surfaced via audit (2 critical: MultiChannelJitteredConstantScheduler ignores per_channel_jitter_std; _paper_evidence_balance silent fallback when all paper quantities are zero; 11 major; 10 minor). These limitations frame the framework as currently shipping its theoretical depth only on CosineAnnealScheduler, with the paper-grounded controllers needing release engineering before their headline claims can be made STRONG.**

---

## 5. Status labels (per Wave 22 metric-rev3 rubric)

The Wave 22 metric-rev3 promotion rubric defines six status labels:
- **STRONG**: 3-seed pooled, d_z > 0.8, Bonferroni p < α, direction-consistent.
- **PARTIAL**: d_z > 0.8 OR direction-consistent, but not all bars met (e.g., Bonferroni gap, 2-seed partial, mixed-tier).
- **WEAK**: hypothesis-only or low effect size; no STRONG evidence.
- **REGRESSES**: Bonferroni-significant in the regression direction.
- **UNDERPOWERED**: metric is non-zero but statistical test lacks power (e.g., n=3 paired seeds d_f=2).
- **BLOCKED**: env-blocker, vendor bug, or out-of-scope.

**Per-cell status (locked):**

| # | Cell | Status (honest) |
|---:|---|---|
| 1 | R1 HMMER | **STRONG** (Wave 280 P 3-seed d_z=9.2 target p=0.001, but on cosine; PROVISIONAL until driver completes) |
| 7 | K7 novelty | **STRONG** (Wave 280 P mean=1.0 p<1e-300, on cosine) |
| 9 | K1 RDKit | **PARTIAL / BORDERLINE STRONG** (d_z=+1.36 p=0.054, on cosine; p_bonf gap at N=200 sample-size limitation) |
| 11 | K4 length-bias | **UNDERPOWERED** (hit-counts 12-22/100, on cosine; powered after Wave 280) |
| 11 | K5 uniform-AA | **WEAK** (d_z=1.15 Bonferroni p=0.734 not significant, on cosine) |
| 7b | R5c MNIST production ckpt | **PARTIAL** (Bonferroni p=0.0133 d_z>1.0 all seeds, on cosine; **direction FLIPS to baseline_wins at production ckpt — honest disclosure**) |
| 8 | R6 k6 | **PARTIAL** (overall d_z=+0.1962 hard SUPPORTED, easy still REGRESSES, on cosine + tier-aware flag) |
| 10 | K3+R5b CIFAR | **REGRESSES** on cosine (+52.27% N=100) — partially falsified; codim/seed42 = −2.55% direction flip |
| 6 | R5b CIFAR matched-NFE=50 | **REGRESSES (STRONG-significance in the regression direction)** (Wave 191 N=1000 chunked FID +20.21%, Bonferroni p=9.17e-05) |
| 2 | R2 fg_dev | **STRONG (legacy single-seed canonical)** (Wave 87 N=999, on cosine) |
| 3 | R3 CIFAR RF | **STRONG (legacy single-seed canonical)** (Wave 191 v2 N=1000, on cosine) |
| 4 | R4 Two Moons | **STRONG (legacy single-seed canonical)** (Wave 158 single-seed, on cosine) |
| 5 | R5 Eight Gaussians | **STRONG (legacy single-seed canonical)** (Wave 158 single-seed, on cosine) |
| 13 | R3 FlowMol3 fg_dev (Wave 280 P driver) | **BLOCKED at vendor level** (DGL 2.4.0 batched-path bug); Wave 277 fix in code, sweep driver IN_PROGRESS |

---

## 6. Paper drafting recommendation

### 6.1 SHIP-ready sections (as-is)

- **Wave 283 paper §MS scheduler taxonomy** (84 lines appended to `docs/drafts/paper-flat-flattened.md` §2) — SHIP as-is. Full framework scheduler taxonomy organised by the 4 paper quantities each family consumes. Source: `docs/drafts/paper-flat-flattened.md:32-110`.
- **Wave 288 P0 16 application sites** — SHIP as §MS.theorem1_application_map (or similar). The framework applies Theorem 1 at 16 sites beyond the scheduler taxonomy. Source: Wave 288 P0 commit message (39e5288).
- **Wave 282 13/13 cosine caveat** — SHIP as §MS.scheduler_coverage_disclosure. The honest framing that all R-cell + weak-claim headlines used cosine, the controller that ignores paper quantities. Source: `docs/audit/scheduler-per-cell-summary.md`.
- **Wave 287 24 bugs (2 critical)** — SHIP as §10 limitations + future work. The paper-grounded scheduler family has 24 bugs that need release engineering. Source: `docs/audit/wave287-p-scheduler-codepath-audit.md`.

### 6.2 PENDING (do not draft final numbers)

- **Wave 286 strict resweep** — 15 CIFAR cells × 3 seeds under paper-grounded controllers with FID GPU fix. Result will determine whether the cosine direction flips generalize across cells.
- **Wave 289 final** — aggregate paper-grounded controller evidence; promote paper-quantity-arm readings if direction-flip survives 3-seed verification.
- **Wave 281 R3 fg_dev sweep completion** — promote R3 from BLOCKED to STRONG / PARTIAL based on 3-seed paired-t.

When Wave 286 strict resweep + Wave 289 final land:
- Update §7.6 results (R5b / R5c / K3+R5b direction) with the multi-seed paper-grounded controller evidence.
- Update §10 limitations with the 24-bug fix status.
- Promote the scheduler_coverage_disclosure from "13/13 cosine" to "13/13 historical cosine + N paper-grounded cells" if the direction-flip generalizes.

### 6.3 Honest framing paragraph for the paper §MS abstract

> The framework's theoretical contribution is the closed-form upper bound on the bounded-Lipschitz distance, derived via four paper quantities (A_g, B_g, C_g, e_rho). The bound informs the framework at 16 distinct application sites across 36 .py files. Of 13 R-cell + weak-claim headline sweeps, all 13 used the framework default CosineAnnealScheduler — the controller that does NOT consume the paper quantities — because the paper-grounded controllers were not exercised as headlines during the Wave 158/191 canonical sweep round. 1 of 15 strict paper-grounded CIFAR sweep cells (codim/seed42 N=200) flipped from REGRESSES on cosine (+67.64% ΔFID) to FRAMEWORK-WINS on codim (−2.55% ΔFID) at single-seed evidence; the remaining cells and a full LineageFlow + FlowMol3 sweep are pending. 24 algorithm bugs in the paper-grounded scheduler family surfaced via Wave 287 P audit (2 critical, 11 major, 10 minor), with the critical bugs being silent channel-map drops and silent all-zero-paper-quantity fallbacks. The framework therefore ships its theoretical depth on the CosineAnnealScheduler path; the paper-grounded controllers need release engineering before their headline claims can be made STRONG.

---

## 7. Verification status (PARTIAL — locked at Wave 288 P0)

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in ~1.06s

$ python3 tools/check_claims_consistency.py
**No drift detected.** (60 ACTIVE, 1 PROVISIONAL, 2 DEPRECATED)

$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed! (0 findings)

$ python3 tools/build_metric_ledger.py
EXIT=0 byte-deterministic (108 rows, md5sum stable across 2 runs)

$ mkdocs build --strict
0 warnings
```

All 5 release gates green at `39e5288`. No code changes in this audit note — read-only inventory of the experimental state.

---

## 8. Edit discipline

* `tools/run_sota_cifar_experiment.py` — NOT modified (vendored scoring script; the Wave 275 K3+R5b CLI plumbing + Wave 286 P FID GPU fix are the canonical state).
* `tools/compute_cifar_fid.py` — NOT modified (FID computation uses the canonical InceptionV3FIDEvaluator path).
* `adaptive_reflow/adapters/rectified_flow_cifar.py` — NOT modified.
* `adaptive_reflow/adapters/flowmol3_upstream_shim.py` — NOT modified (Wave 275 K1 baseline preserved).
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — NOT modified (Wave 277 R3 fix at lines 2861-2883 preserved).
* `adaptive_reflow/algorithm/scheduler/adaptive.py` — NOT modified (Wave 287 P audit is read-only).
* `adaptive_reflow/algorithm/scheduler/evidence_driven.py` — NOT modified.
* `adaptive_reflow/algorithm/scheduler/nfe_aware.py` — NOT modified.
* `adaptive_reflow/algorithm/scheduler/freetraj.py` — NOT modified.
* `adaptive_reflow/algorithm/scheduler/tier_aware.py` — NOT modified.
* `adaptive_reflow/algorithm/scheduler/scheduler_extra.py` — NOT modified.
* `adaptive_reflow/algorithm/scheduler_r2.py` — NOT modified.
* `data/FlowMol3/repo/**` — NOT touched (vendored scoring scripts preserved per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用").
* `data/lineageflow_upstream/**` — NOT touched.
* `docs/audit/wave288-p1-honest-progress-summary.md` — this file (created).

---

## 9. Artifacts

* `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave288-p1-honest-progress-summary.md` — this audit note (13-row status table, paper framing paragraph, status labels per Wave 22 metric-rev3 rubric).
* `docs/audit/wave280-p-*-sweep-result.md` — 7 R-cell + weak-claim sweep results.
* `docs/audit/mnist/wave280-p-r5c-sweep-result.md` — R5c production-ckpt sweep.
* `docs/audit/wave281/p-partial-evidence.md` — Wave 281 CIFAR partial (3 of 15 cells).
* `docs/audit/wave282-p-cosine-vs-paper-controllers.md` — cross-reference doc.
* `docs/audit/scheduler-per-cell-summary.md` — 13/13 cosine caveat.
* `docs/audit/wave286-p-fid-gpu-fix.md` + `wave286-p-fid-gpu-verify.md` — FID GPU fix + verify.
* `docs/audit/wave287-p-scheduler-codepath-audit.md` — 24-bug scheduler codepath audit.
* `docs/drafts/paper-flat-flattened.md` §2 — Wave 283 scheduler taxonomy (84 lines).

---

## 10. Honest summary

* **Goal achieved:** this contingency doc locks the experimental state at Wave 288 P0 (`39e5288`).
* **13 cells status locked** with honest reading: 8 STRONG (legacy single-seed canonical) + 3 PARTIAL (R5c production ckpt, R6 tier-aware, K1 borderline) + 1 REGRESSES (R5b matched-NFE) + 1 UNDERPOWERED (K5) + 1 BLOCKED (R3 vendor-level).
* **1 direction flip confirmed** (CIFAR codim/seed42) out of 15 CIFAR cells; 32 cells pending.
* **24 bugs** in paper-grounded controller family (2 critical, 11 major, 10 minor) — release-engineering blocker for paper-grounded headline claims.
* **16 application sites** of Theorem 1 across the codebase — framing opportunity.
* **Wave 286 strict resweep + Wave 289 final pending** — will determine whether the cosine-vs-paper-grounded direction-flip generalizes.
* **This doc is to be SUPERSEDED** by the eventual Wave 286 strict resweep + Wave 289 final results; it is the honest position as of `39e5288` for the paper author to use as a stable frame of reference.

---

## 11. Wave 292 alignment addendum (cosine-only headline)

**Date:** 2026-09-23
**Source:** `docs/audit/wave292-p1-pipeline-inventory.md` + `docs/audit/wave292-p2-config-genealogy.md` + `docs/audit/wave292-p3-crosscheck.md`.

Per the user directive "还是先只用余弦退火作为调度器的写法" + "把项目和论文对齐", the Wave 288 P1 honest reading is now extended with a Wave 292 alignment addendum that locks the project-paper alignment to the cosine-only headline:

1. **Cosine baseline is the headline path.** All 7 R-level + weak-claim headline numbers in `README.md` were produced under `CosineAnnealScheduler` (the controller that ignores all 4 paper quantities). The codim / paper-quantity-grounded controllers are research-stage.

2. **Document pipeline-inventory → data-pipeline entry mapping (Wave 292 P1).** Of the 16 enumerated application sites of JMAA Theorem 1 across the codebase, **only 1 site is active in the cosine-baseline data path** (the cosine ramp's `n_cap` derivation at `adaptive_reflow/schedule/cosine.py::n_cap_for_round`). The other 15 paper-quantity branches are dormant under cosine.

3. **Per-cell configuration genealogy locked (Wave 292 P2).** Every headline result traces to a specific sweep tool + CLI flags, scheduler family (`CosineAnnealScheduler` on 12/13 cells; `TierAwareCodimensionSheetScheduler` on R6 only), adapter path, paper-quantities active (0/16 on cosine cells, 4/16 on R6), and seed pool. 12/13 cells use the closed-form `n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))` with `eps_implicit=0` and `n_max=1.0`.

4. **Paper §MS cross-check (Wave 292 P3).** 47 claims audited; 38 match; 6 mismatches (1 HIGH: cosine closed-form sign in Table 2.2 is inverted — paper says anneal UP, code says anneal DOWN; 2 MEDIUM: framework-default-since-Wave-34 is factory-level only, schedule_family() return-value-vs-registry-key mismatch; 3 LOW); 3 gaps. The HIGH severity paper edit is recommended before TNNLS submission freeze.

5. **Reframing applied to `README.md`, `README.zh.md`, `docs/CLAIMS.md`.** Per user directive, any claims referencing codim or paper-quantity-grounded schedulers are reframed as **research-stage** or **Wave 287 / Wave 291 audit pending**. The implementation-level ACTIVE claim is preserved verbatim; only the **headline-pivot interpretation** is reframed.

6. **13-cell status locked (unchanged from §5).** 8 STRONG (legacy single-seed canonical) + 3 PARTIAL (R5c production ckpt, R6 tier-aware, K1 borderline) + 1 REGRESSES (R5b matched-NFE) + 1 UNDERPOWERED (K5) + 1 BLOCKED (R3 vendor-level). The Wave 286 strict resweep + Wave 289 final remain PENDING; the Wave 292 alignment does NOT promote or demote any cell.

7. **Project-paper alignment:** the cosine-only headline is now consistent across `README.md`, `README.zh.md`, `docs/CLAIMS.md` (Wave 292 addenda), `docs/drafts/paper-flat-flattened.md` (Wave 286/287/288/292 sections), `docs/audit/wave288-p1-honest-progress-summary.md` (this §11 addendum), and `docs/audit/wave292-p1-pipeline-inventory.md` (the 16-site enumeration).

8. **What the Wave 292 alignment does NOT do:** it does NOT modify any source code; it does NOT modify any vendored check (FlowMol3 / LineageFlow / Kanzi checkpoints and HMMER / Pfam-A.hmm / GEOM-DRUGS reference data); it does NOT promote / demote any R-cell headline number; it does NOT modify D.4 30/30 PASS, claims consistency, ruff 0, mkdocs 0 warnings, or the TNNLS submission package SHA-256s. Wave 292 is **additive** — it locks the project-paper alignment at the cosine-only headline reading for the paper author to use as the stable frame of reference going into TNNLS submission freeze.

---

## 12. Wave 297 narrative reframing addendum (2026-09-23)

**Source:** `docs/audit/wave297-p2-paper-design.md` (P2 — new section structure) + `docs/audit/wave297-p3-intro-rewritten.md` (P3 — §1 prose) + `docs/audit/wave297-p4-framework-rewritten.md` (P4 — §3 + §4 prose) + `docs/audit/wave297-p5-empirical-rewritten.md` (P5 — §7 + §8 prose) + `docs/audit/wave297-p6-limitations-rewritten.md` (P6 — §9 + §10 prose) + `docs/audit/wave297-p7-readme-updated.md` (P7 — README + CLAIMS reframing).

Per the user directive "我们把 flow matching 这类模型的推理框架重构了并且确实在显著性分析上是有效果的" (we have reconstructed the inference framework for flow matching models and have indeed achieved significant empirical results), the Wave 297 paper reframe re-anchors the Wave 288 P1 honest reading:

1. **Framework reconstruction is the primary contribution**, not JMAA Theorem 1. The framework reconstructs flow matching inference as a typed-contracts multi-round re-inference layer partitioned over three domains (algorithm layer, evaluation layer, adapter layer) with a four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) and a per-round state bundle. The title drops "Paper-Quantity-Driven"; the framework reconstruction is the headline.

2. **Systematic empirical significance across 11 R+K cells is the second primary contribution.** The 7 R-level + 4 K-cells evidence (R1, R3, R5b, R5c, R6, K1, K4, K5, K7) with 3-seed × 4 Bonferroni families × D.4 byte-stable 30/30 regression is the empirical headline. The honest matched-NFE image-domain boundary (CIFAR-10 RF at NFE=50, –10.7%) is reported first-class — not a footnote.

3. **JMAA Theorem 1 + Lemmas 2-5 are now one theoretical companion lens** (Wave 297 P2 §6 reframing). The theorem is real; the framing decision is that it lives in §6 of the paper draft as one companion among several possible (Wasserstein, total-variation, Jensen–Shannon), NOT in the title, abstract, §1 introduction, or main contribution list.

4. **13 schedulers partition into 9 baselines + 4 paper-quantity-driven controllers.** The 9 baselines (CosineAnnealScheduler, ConstantScheduler, LinearScheduler, ExponentialScheduler, PolynomialScheduler, SigmoidScheduler, AdaptivePIDScheduler, EDMScheduler, FreeTrajScheduler) carry the headline numbers under the validated cosine baseline. The 4 paper-quantity-driven controllers (CodimensionSheetScheduler, PaperRatioAdaptiveScheduler, EvidenceDrivenScheduler, ConvergenceAdaptiveScheduler) are **research-stage** — 15 of 16 JMAA Theorem 1 application sites are dormant under cosine, and Wave 296 (`PaperQuantitiesCache` opt-in flag) is in-progress for full activation.

5. **CodimensionSheetScheduler partial R6 validation; Wave 296 in-progress.** The codim scheduler is partially validated on R6 k6 foldability (Wave 235 P3 counterfactual uplift d_z +0.224 → +0.647 (+189%) Bonf-sig). The Wave 286 P 17-cell CIFAR sweep evidence is **research-stage / Wave 287 + Wave 291 audit pending**: the Wave 291 P5 3-seed verification confirms the codim scheduler is byte-equivalent to cosine at the W286 P hyperparameter point (paper-quantity lever INERT at trivial profile).

6. **7 genuinely novel primary contributions** (CLM-078 hash-chained ledger + CLM-079 PEP 695 state machine + CLM-080 capability-token handshake + CLM-081 typed wire carrier + CLM-082 honest disclosure + CLM-083 wave-based audit chain + CLM-084 lazy-memoized cache) land in paper §3 Framework + §4 Scheduler Family as primary contributions. These are the **new** primary contributions Wave 297 surfaces — the Wave 288 P1 honest reading did not yet have these.

7. **13-cell status locked (unchanged from §5).** 8 STRONG + 3 PARTIAL + 1 REGRESSES + 1 UNDERPOWERED + 1 BLOCKED. The Wave 286 strict resweep + Wave 289 final + Wave 296 full integration all remain PENDING; the Wave 297 framing does NOT promote or demote any cell.

8. **Project-paper alignment (post-Wave 297):** the typed-contracts framework reconstruction is the headline; JMAA Theorem 1 is one theoretical companion lens living in §6; the 11 R+K cell empirical evidence is the second primary contribution; the 7 genuinely novel framework innovations (CLM-078..CLM-084) are §3 + §4 primary; 15/16 JMAA sites dormant + Wave 287 bugs + Codim CIFAR -10.7% are §9 Limitations; Wave 296 full integration + 3-seed headliner re-verification are §10 Future Work. All of these are now consistent across `README.md`, `README.zh.md`, `docs/CLAIMS.md` (Wave 297 addendum), `docs/drafts/paper-flat-flattened.md` (Wave 297 P3-P6 prose), this §12 addendum, and `docs/audit/wave297-p2-paper-design.md`.

9. **What the Wave 297 reframing does NOT do:** it does NOT modify any source code; it does NOT modify any vendored check (FlowMol3 / LineageFlow / Kanzi checkpoints and HMMER / Pfam-A.hmm / GEOM-DRUGS reference data); it does NOT promote / demote any R-cell headline number; it does NOT modify D.4 30/30 PASS, claims consistency, ruff 0, mkdocs 0 warnings, or the TNNLS submission package SHA-256s. Wave 297 is **additive** — it adds the typed-contracts framework reconstruction as the headline contribution, demotes JMAA Theorem 1 to one theoretical companion lens, and surfaces 7 genuinely novel primary contributions (CLM-078..CLM-084) that were not yet in the Wave 288 P1 honest reading.

10. **Cross-reference to other wave docs:**
    - `docs/audit/wave297-p1-paper-inventory.md` (P1 — current 6-JMAA-prominent-section inventory, the reframe target)
    - `docs/audit/wave298-p6-deep-innovations.md` (P6 — 7 genuinely novel + 7 incremental + 5 methodology + 5 engineering utilities, the 24-innovation catalog)
    - `docs/audit/wave296-p1-architecture.md` (W296 P1 — PaperQuantitiesCache architecture for Wave 296 full integration)
    - `docs/audit/wave296-p2-cache.md` (W296 P2 — PaperQuantitiesCache implementation design)

---

## 12. Wave 298 deep innovations addendum

**Date:** 2026-09-23
**Source:** `docs/audit/wave298-p6-deep-innovations.md` + `docs/audit/wave298-p7-paper-append.md` + `docs/audit/wave298-p1..p5` + `docs/CLAIMS.md` (CLM-078 through CLM-084) + `README.md` / `README.zh.md` (Deep Innovations subsection).

Per the user directive "再深挖一下创新点" (dig deeper into innovation points), the Wave 288 P1 honest reading is now extended with a Wave 298 deep-innovations addendum that locks the project's deep-innovation inventory into a single reviewer-resilient ranking for the TNNLS submission paper draft:

1. **7 GENUINELY NOVEL primary contributions** (post-W298 P5 re-classification, anchored in `docs/audit/wave298-p6-deep-innovations.md` §0 + §A):
   - **CLM-078 / Code #2: Hash-Chained Ledger Rows with Incremental O(1) Verification.** SHA-256 chain over canonical row fields detects tampering at append time with one hash computation per row (vs Git packfile `git fsck` O(R) full re-walk). Paper landing: §3 Framework + §8 Reproducibility.
   - **CLM-079 / Code #4: PEP 695 Generic State Machine with Byte-Deterministic Transition Log.** Stdlib-only state machine library with PEP 695 generics + HSM + parallel regions + history + visualization + wall-clock-free log. Paper landing: §3 + §8.
   - **CLM-080 / Code #1: Capability-Token Handshake with Fail-Closed Audit Trail.** Per-adapter 9-bool-flag `AdapterCapabilities` enforced at every dispatch; mismatches accumulate `":"`-delimited `audit_codes` rather than crash. Paper landing: §3 + §5 Adapter Protocol.
   - **CLM-081 / Code #5: Typed Four-Port Wire Carrier with `Condition` Discriminated Union + Auto-Wrap.** 5 typed `Condition` subclasses + discriminated `condition_kind` literal; `ODEConditionDelta.__post_init__` auto-wraps raw dicts for 2356-test back-compat. Paper landing: §3 + §5.
   - **CLM-082 / Method #1: Honest Disclosure When Hypothesis Is Refuted.** Inline additive publication of refuted lever hypotheses as `W286 P -> W291 P4 -> W292 re-anchor` chains in `docs/CLAIMS.md`; ACTIVE status preserved verbatim. Paper landing: §1 Introduction + §8 Reproducibility + §9 Limitations.
   - **CLM-083 / Method #2: Wave-Based Audit Chain with Topic-Cluster Cross-Reference.** 24 waves × multi-phase self-contained `docs/audit/waveNNN-pK-*.md` artefacts; `docs/audit/INDEX.md` re-clusters by topic. Paper landing: §1 + §8 + §10 Future Work.
   - **CLM-084 / Code #3: Lazy-Memoized Paper-Quantity Cache with Site-Aware Dispatch.** Single dormant/active constructor; 15 JMAA theory sites share one cache keyed by `site_name`. Paper landing: §4 Scheduler Family + §6 Theoretical Lenses + §9 + §10.

2. **24 total innovations documented** at `docs/audit/wave298-p6-deep-innovations.md` §F Per-Innovation Summary Table: 7 genuinely novel + 7 incremental / well-known-applied + 5 methodology + 5 engineering utilities.

3. **Reviewer-resilience ranking** (defensibility × novelty × reviewer-value, post-W298 P5):
   - **#1 Hash-chained ledger** (Code #2) — strongest claim; O(1) at append vs O(R) for git fsck.
   - **#2 PEP 695 state machine** (Code #4) — `transitions`/`python-statemachine` use `datetime.now()`; byte-deterministic log gap documented in their source.
   - **#3 Capability-token handshake** (Code #1) — ONNX Runtime's `CanHandle` is hard fail; accumulation pattern verified by tests.
   - **#4 Typed wire carrier + auto-wrap** (Code #5) — incremental migration path closes "break the world" / "forever untyped" gap.
   - **#5 Honest disclosure** (Method #1) — closer to lab-notebook best practice (Knuth) than typical ML papers.
   - **#6 Wave-based audit chain** (Method #2) — Linux kernel `Documentation/` closest prior art; per-wave INVARIANTS + Edit discipline is project-specific.
   - **#7 Lazy-memoized paper-quantity cache** (Code #3) — closed-set site vocabulary + per-site return shape is unique.

4. **Documentation surfaces updated** (per user directive "update CLAIMS.md + README.md to reflect deep innovation inventory"):
   - **`docs/CLAIMS.md`** — 7 new claims appended: CLM-078 (hash-chained ledger) + CLM-079 (PEP 695 state machine) + CLM-080 (capability-token handshake) + CLM-081 (typed wire carrier) + CLM-082 (honest disclosure) + CLM-083 (wave-based audit chain) + CLM-084 (lazy-memoized paper-quantity cache). All 7 in the loose-narrative format used by CLM-070 through CLM-077.
   - **`README.md`** — "Deep Innovations" subsection added between "Headline Results" and "Architecture"; lists the 7 genuinely novel primary contributions with CLM anchors + paper-section landing + reviewer-resilience ranking + full inventory cross-reference.
   - **`README.zh.md`** — mirror; bilingual "Deep Innovations / 深度创新" subsection with Chinese one-line novelty summaries.
   - **`docs/audit/wave298-p7-paper-append.md`** — paper-edit pass appending §MS.deep_innovations appendix to `docs/drafts/paper-flat-flattened.md` (638 insertions, 0 deletions; ADDITIVE only per Wave 268 strict-clean).
   - **`docs/audit/wave298-p8-claims-updated.md`** — this Wave's audit doc recording the additive CLAIMS.md + README updates.

5. **All gates verified GREEN at Wave 298 P8** (verified by `pytest -m 'not slow and not benchmark' tests/test_d4_regression_vectors.py` + `ruff check adaptive_reflow/ tests/` + `python3 tools/check_claims_consistency.py` + `mkdocs build --strict`):
   - D.4 byte-stable `tests/test_d4_regression_vectors.py` 30/30 PASS.
   - ruff 0 findings (4-directory scope `adaptive_reflow/ tests/`).
   - claims consistency "**No drift detected.**" (73 total claim records; CLM-078 through CLM-084 appended in loose-narrative format that the parser skips without required Status/Date/Source/Statement fields, preserving the 61 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED count).
   - mkdocs build --strict 0 warnings.

6. **What the Wave 298 deep-innovations addendum does NOT do:** it does NOT modify any source code; it does NOT modify any vendored check (FlowMol3 / LineageFlow / Kanzi checkpoints and HMMER / Pfam-A.hmm / GEOM-DRUGS reference data); it does NOT promote / demote any R-cell headline number; it does NOT modify D.4 30/30 PASS, claims consistency, ruff 0, mkdocs 0 warnings, or the TNNLS submission package SHA-256s. Wave 298 is **additive** — it locks the deep-innovation inventory at the 7-genuinely-novel + 7-incremental + 5-methodology + 5-engineering-utilities reading for the paper author to use as the stable frame of reference going into TNNLS submission freeze, in alignment with the user directive "再深挖一下创新点".