# Wave 299 — Paper B Deferred Work (Standalone)

**Date:** 2026-09-23
**Branch:** main
**Parent doc:** `docs/audit/wave299-final-verification.md`
**Companion doc:** `docs/audit/wave299-paper-a-outline.md` (priority, ready to execute).
**Purpose:** Standalone, deferred-work spec for **Paper B** (JMAA theory + paper-quantity-driven scheduler family + 16-site theoretical integration). This doc enumerates the experiments, theoretical work, and architectural choices that must be completed **before** Paper B can be submitted. The 5 items below are gated on prerequisite work (Wave 300+ regime-sweep design).

**Trigger:** DeepSeek老师 feedback (relayed verbatim by user) recommended splitting the project into two papers. This doc operationalizes the Paper B half of that split as deferred future work.

---

## 0. TL;DR

| Aspect | Value |
|---|---|
| **Title (proposed)** | Paper-Quantity-Driven Scheduling for Flow Matching Re-Inference: Theory and Empirical Validation |
| **Target venue (proposed)** | IEEE TNNLS or TKDE (theory + scheduler match) / Knowledge-Based Systems (backup, knowledge-driven) |
| **Status** | **DEFERRED** (gated on Wave 300+ regime-sweep design + ~6 GPU hours) |
| **Core contributions (planned)** | 5 (per §3 below) |
| **Required experiments** | 3 (EXP-1, EXP-2, EXP-3; ~6 GPU hours total) |
| **Critical caveat** | Paper-quantity lever is INERT at Wave 286 P headline config (Wave 291 P5 §5); regime sweep is prerequisite |
| **Dependency** | Must run AFTER Paper A is submitted (so framework-not-theory verdict is reviewer-validated) |
| **Push status** | NOT PUSHED (per "暂不 push" directive) |

---

## 1. Critical Caveat (read this first)

**Per Wave 291 P5 §5 (3-seed verification):**

> "codim_none at eps=10.0 / L=4 / n_min=0.0 is byte-equivalent to cosine at the 3-seed level (STRONG headliner verdict) — `mean Δ% vs cosine = +0.000% σ=0%`, paired-t t=nan, p=nan"

This means: at the Wave 286 P headline configuration, **the paper-quantity-driven scheduler does not differ from the cosine baseline**. The +10.721% delta reported in Wave 290 P3 was driven by scheduler **structure** (codim vs cosine), not by paper-quantity **values**.

Furthermore:

> "codim_real_g vs codim_permuted are byte-identical at eps=10.0 (paper-quantity profile lever INERT in the cell regime — the +10.721% delta vs cosine is driven by scheduler structure, not paper-quantity values)"

**Implication for Paper B:** running the Wave 286 P headline configuration (CodimensionSheetScheduler at eps=10.0/L=4/n_min=0.0 with `profile_residual_fn=real_g`) will produce **byte-equivalent** samples to cosine, regardless of the profile. Paper B's experiments **must either**:

- **(a) Sweep `eps ∈ {0.5, 2.0, 10.0} × L ∈ {4, 8, 16} × profile_residual_fn ∈ {None, real_g, perm_g}`** to map the paper-quantity lever's active regime, OR
- **(b) Explicitly disclose this as the framework's paper-quantity activation boundary** (alternative framing).

The current `CosineAnnealScheduler` cosine sigma noise band (0.755% relative at N=200, 3 seeds) is the canonical noise floor; Paper B must establish that the paper-quantity lever's delta exceeds 2σ of this band to claim "active regime".

This caveat is **the single most important fact** about Paper B; without addressing it, the experiments will not yield a publishable delta.

---

## 2. Title (proposed)

> **Paper-Quantity-Driven Scheduling for Flow Matching Re-Inference: Theory and Empirical Validation**

**Rationale:**
- **"Paper-Quantity-Driven Scheduling"** — surfaces the JMAA Theorem 1 paper quantities $(A_g, B_g, C_g, e_\rho)$ as the scheduler's first-class inputs.
- **"Theory and Empirical Validation"** — preserves the theory + empirical dual contribution pattern.
- **"Flow Matching Re-Inference"** — preserves the re-inference loop framing (same as Paper A).

---

## 3. Target Venue (proposed)

| Venue | Match | Acceptance rate (estimated) | Backup priority |
|---|---|---|---|
| **IEEE TNNLS** | Theory + scheduler family + framework rigor | 35-45% | Primary |
| **IEEE TKDE** | Theory + scheduler family + framework rigor | 40-50% | Primary (alternative) |
| **Knowledge-Based Systems** | Knowledge-driven scheduler framing | 60-70% | Backup |

**Recommendation:** Target TNNLS as primary; submit to TKDE if TNNLS rejects.

---

## 4. Core Contributions (planned, 5 items)

| # | Contribution | Evidence (Wave doc) | Status |
|:-:|---|---|---|
| (i) | **JMAA Theorem 1 + Lemmas 2-5 as scheduler input contract.** Four paper quantities $(A_g, B_g, C_g, e_\rho)$ exposed as typed scheduler inputs via `PaperQuantitiesCache`. | Wave 296 P5 + Wave 298 P6 §A.7 | Cache shipped (38/38 tests); cell-level exercise pending |
| (ii) | **16-site theoretical integration.** Algorithm-layer (8 A-class sites) + evaluator-layer (8 B-class sites) all wired through `enable_full_jmaa_theory` flag. | Wave 296 P5 + Wave 296 P3-P4 | Shipped; cell-level exercise pending |
| (iii) | **Scheduler family comparison at theory-scheduler configuration.** CodimensionSheetScheduler vs CosineAnneal vs FreeTraj vs PaperRatioAdaptiveScheduler vs EvidenceDrivenScheduler vs ConvergenceAdaptiveScheduler at matched eps × L × profile_residual_fn. | Wave 286 P + Wave 290 P + Wave 291 P | Partial (Wave 291 P5 3-seed at eps=10.0/L=4/n_min=0.0); regime sweep pending |
| (iv) | **Theoretical analysis.** BL bound derivation from Theorem 1 + Lemmas 2-5; regime-aware behaviour (eps × L sweep maps the lever's active regime); connection to bounded-Lipschitz theory (Sriperumbudur 2012). | Wave 296 P7 + Wave 297 P2 §6 + `docs/theory/theorem-1-self-contained.md` | Partial; full derivation pending |
| (v) | **Honest FID Δ=0% disclosure.** Theory is dormant under cosine baseline (Wave 296 P7); dedicated scheduler + non-trivial profile required to activate. | Wave 296 P7 §3 | Disclosed in Paper A §6; Paper B will extend with regime-sweep evidence |

---

## 5. Required Experiments (deferred)

### 5.1 EXP-1: Theory-Scheduler Regime Sweep

**Goal:** Map the paper-quantity lever's active regime across `eps × L × profile_residual_fn`.

**Configuration:**
- Cells: R1 (LineageFlow), R3 (FlowMol3), R5b (CIFAR-10 RF), R6 (Kanzi k6 foldability) — 4 cells.
- `eps_implicit ∈ {0.5, 2.0, 10.0}` — 3 values (the three regimes where sheet and cell evidence actually compete per `eps^{+1}` vs `eps^{+2}` scaling split, per Wave 291 P1 hypothesis redesign).
- `L ∈ {4, 8, 16}` — 3 values (cycle length parameter).
- `profile_residual_fn ∈ {None, real_g, perm_g}` — 3 values (None = framework heuristic; real_g = paper-quantity profile; perm_g = permuted control).
- Seeds: 3 (0, 1, 2).
- Scheduler: `CodimensionSheetScheduler` with `eps_implicit` parameter swept.
- Metrics: framework_fid + cosine sigma noise band (0.755% relative at N=200).

**Total runs:** 4 cells × 18 configs × 3 seeds = 216 runs.

**GPU budget:** ~5 GPU hours on PRO 6000 (sequential per Wave 291 P5 pattern; each run ~80 seconds).

**Success criterion:** at least 1 configuration produces a delta > 2σ of the cosine sigma noise band, with byte-stability preserved under profile_residual_fn swap (real_g vs perm_g).

### 5.2 EXP-2: 16-Site Cell-Level Exercise

**Goal:** Exercise the 16-site PaperQuantitiesCache on R-cells with paper-quantity-driven schedulers end-to-end (not just cache activation log, but actual adapter-level integration).

**Configuration:**
- Cells: R1, R3, R5b, R6 — 4 cells.
- Scheduler: `CodimensionSheetScheduler` with active cache.
- `enable_full_jmaa_theory=True` with `PaperQuantitiesCache(profile_residual_fn=real_g)`.
- Sites consumed: 16/16 (per Wave 296 P5).
- Seeds: 3.

**Total runs:** 4 cells × 1 config × 3 seeds = 12 runs.

**GPU budget:** ~30 GPU minutes on PRO 6000.

**Success criterion:** byte-stability preserved at all 16 sites (no regression on D.4 30/30); per-cell framework_fid delta vs cosine baseline within expected bounds.

### 5.3 EXP-3: Cosine Sigma Noise Band Recalibration

**Goal:** Re-measure the framework_fid sigma across 3 seeds with CodimensionSheetScheduler at the regime-sweep-identified active configuration, to establish a new sigma noise band at the theoretical-scheduler regime.

**Configuration:**
- Cell: R5b (CIFAR-10 RF) — most sensitive to scheduler choice.
- Scheduler: CodimensionSheetScheduler at the EXP-1 identified active configuration.
- Seeds: 3.
- N: 200, 1000.

**Total runs:** 12 runs.

**GPU budget:** ~20 GPU minutes on PRO 6000.

**Success criterion:** sigma noise band at the theoretical-scheduler regime is comparable to the cosine sigma (0.755% relative at N=200) within 50%, validating that the framework_fid metric is meaningful at the theoretical-scheduler regime.

**Total GPU budget across EXP-1 + EXP-2 + EXP-3:** ~6 hours on PRO 6000.

---

## 6. Theoretical Work (deferred)

### 6.1 BL Bound Derivation

**Goal:** State and prove Theorem 1's BL bound $(d_{BL}(\mu_{g,\varepsilon}, \nu_g) \le A_g e^{-\mathrm{NFE}/B_g} + C_g e_\rho)$ in a self-contained proof sketch suitable for journal submission.

**Source-of-truth:** `docs/theory/theorem-1-self-contained.md` (already written).

**Action:** Extract the proof sketch into Paper B §3 (Theoretical Framework); verify the four-lemma path (Lemma 2 sheet, Lemma 3 cell, Lemma 4 complement, Lemma 5 packing) against the framework's `paper_quantities.py` materializers.

### 6.2 Regime-Aware Behaviour

**Goal:** Characterize the paper-quantity lever's active regime as a function of `eps_implicit × L × profile_residual_fn`.

**Action:** EXP-1 results feed into Paper B §4 (Empirical Validation of the Lever). Plot the lever's delta as a heatmap over `eps × L`; identify the active region.

### 6.3 Connection to Bounded-Lipschitz Theory

**Goal:** Connect the framework's BL distance (`adaptive_reflow/eval/lipschitz_diagnostic.py`) to Sriperumbudur et al. 2012 B-L theory.

**Source-of-truth:** Wave 298 P6 §B.3 + `adaptive_reflow/eval/lipschitz_diagnostic.py:106-253, 256-321`.

**Action:** Paper B §5 (Related Theory) cites Sriperumbudur 2012 + Villani 2003 Kantorovich-Rubinstein duality as the framework's theoretical foundation.

---

## 7. Architectural Choices (deferred)

### 7.1 Scheduler Family Comparison Methodology

**Choice:** Head-to-head scheduler comparison at matched `eps × L × profile_residual_fn` configuration.

**Rationale:** Eliminates the "comparing apples to oranges" objection that plagues Wave 286 P's `cosine vs codim at default config` reading.

### 7.2 FID Path

**Choice:** Reuse `tools.batched_framework_cifar.run_batched_records` (Wave 290 P3 harness, 28-35× speedup) + subprocess to `tools.compute_cifar_fid.py` (torchvision IMAGENET1K_V1 extractor).

**Caveat:** FID path is byte-stable for byte-comparable extractors only; do NOT mix `inceptionv3_torchvision_IMAGENET1K_V1` and `inceptionv3_tfport` across cells (Wave 1 P0-1 caveat).

### 7.3 3-Seed Pool

**Choice:** Seeds 0, 1, 2 (per Wave 280 P 3-seed pool).

**Caveat:** Cells with seed pool = 1 (R5a, R5 Eight Gaussians, R5c smoke ckpt, K7 saturated) must be flagged as "legacy single-seed canonical" in Paper B.

### 7.4 Statistical Methodology

**Choice:** Pre-register 4 Bonferroni families (same as Paper A):
- Theory-scheduler primary family (k = ?) — α = 0.05/? = ?
- R-level family (k = 7) — α = 0.05/7 = 0.007143.
- Per-tier family (k = 6) — α = 0.05/6 = 0.008333.
- Table B family (k = 16) — α = 0.05/16 = 0.003125.

**Note:** The k-count for the theory-scheduler primary family will be set AFTER the regime sweep identifies the active configuration count.

---

## 8. Dependency on Paper A

Paper B **must run AFTER Paper A is submitted** because:

1. **Framework-not-theory verdict validation:** Paper A's §7.4 establishes that the cosine baseline (not paper-quantity schedulers) drives the headline empirical results. This verdict is the foundation of Paper B's contribution: if Paper A's reviewers accept this framing, Paper B's contribution is "we now know the framework is module-independent; here is the dedicated theory-scheduler regime that activates the JMAA bound".
2. **Reviewer feedback gating:** Paper A's reviewer feedback may refine the framework-not-theory verdict (e.g., "you haven't demonstrated the theory-scheduler is necessary; here is an experiment you should run"). Paper B should incorporate this feedback.
3. **Headline numbers reuse:** Paper B cites Paper A's headline numbers (2.5-10× cross-budget NFE compression, byte-stable composite-axis lifts, matched-NFE=50 boundary) as the framework-level evidence; the dedicated theory-scheduler results extend this evidence.

**Recommended timeline:**
- Wave 300: Paper A finalization fold-in (per `wave299-paper-a-outline.md` §6).
- Wave 301: Paper A submission (user action).
- Wave 302-304 (3-6 months later): Paper A review period.
- Wave 305+ (after Paper A reviewer feedback received): Paper B regime-sweep design + EXP-1/2/3.
- Wave 310+: Paper B writeup + submission.

---

## 9. INVARIANTS (preserved by this plan)

| Invariant | Status |
|---|---|
| D.4 30/30 byte-stability | **PASS** (preserved by all experiments; each EXP must maintain D.4 30/30) |
| Claims no drift | **PASS** (no claim changes until EXP-1 results land) |
| Ruff 0 diagnostics | **PASS** (no new code edits in this deferred plan) |
| mkdocs 0 warnings | **PASS** (no mkdocs.yml changes) |
| Vendored NOT touched | **PASS** (all experiments use existing vendored checkpoints) |
| Wave 268 strict-clean | **PASS** (additive only) |
| Push status | **NOT PUSHED** (per "暂不 push" directive) |

---

## 10. Open Questions for the User

The following 5 questions require user input before Wave 300+ (Paper B regime-sweep design) or Wave 301+ (Paper B planning).

| # | Question | Context | Recommended default |
|:-:|---|---|---|
| 1 | Should EXP-1 (regime sweep) be the priority, or EXP-2 (16-site cell-level exercise) first? | EXP-1 maps the lever's active regime (prerequisite for any meaningful Paper B); EXP-2 verifies the 16-site integration works at cell level. | EXP-1 first (prerequisite). |
| 2 | Should Paper B target TNNLS (primary) or TKDE (alternate primary) as the target venue? | Both match theory + scheduler + framework rigor. | Default to TNNLS (broader readership); submit to TKDE if TNNLS rejects. |
| 3 | Should the paper-quantity lever's INERT status at the W286 P headline config be characterized as "framework boundary" or "scheduler configuration artefact"? | Wave 291 P5 §5 says "scheduler structure drives the +10.721% delta, not paper-quantity values"; this could be framed as a framework-level finding (paper quantities are not load-bearing at headline config) or as a scheduler-level finding (need higher-dimensional sweep). | Default to "framework boundary" (more honest; matches Paper A's framework-not-theory verdict). |
| 4 | Should Paper B's title include "JMAA" or remain neutral ("Paper-Quantity-Driven")? | "JMAA" surfaces the theorem provenance; "Paper-Quantity-Driven" is more descriptive. | Default to "Paper-Quantity-Driven" (descriptive; matches the Wave 297 P2 §4.4 scheduler taxonomy). |
| 5 | Should the regime-sweep be expanded to cover `profile_residual_fn ∈ {real_g, perm_g, line_g, sin_g, ...}` to map the lever across multiple adapter types? | Wave 291 P5 used `real_g vs perm_g`; expanding to more profiles would add GPU hours but improve generalizability. | Default to `{None, real_g, perm_g}` for Paper B v1; expand in v2 if reviewer requests. |

---

## 11. Files referenced (NOT modified by this plan)

- `docs/drafts/paper-flat-flattened.md` — byte-unchanged (per Wave 299 task scope).
- `adaptive_reflow/**/*.py` — byte-unchanged (until EXP-1/2/3 implementation).
- `tests/**/*.py` — byte-unchanged (until EXP-1/2/3 conformance tests).
- `tools/**/*.py` — byte-unchanged (until EXP-1/2/3 sweep drivers).

## 12. Files to be created/modified by Paper B execution (Wave 305+)

```
docs/audit/wave305-paper-b-regime-sweep-design.md     (regime sweep design doc)
docs/audit/wave306-paper-b-exp1-results.md            (EXP-1 results)
docs/audit/wave307-paper-b-exp2-results.md            (EXP-2 results)
docs/audit/wave308-paper-b-exp3-results.md            (EXP-3 results)
docs/drafts/paper-b-flat-flattened.md                 (Paper B draft; new file, not Paper A's)
```

(Approx. 5 new audit docs + 1 new draft; 0 modifications to existing files until Paper B writeup begins.)

---

## 13. Honest summary

Paper B is the **JMAA theory + paper-quantity-driven scheduler family + 16-site theoretical integration**. It is **deferred** until Paper A is submitted AND a regime-sweep design identifies the paper-quantity lever's active configuration space. The single most critical fact is that the paper-quantity lever is **INERT at the Wave 286 P headline configuration** (Wave 291 P5 §5): codim_none at eps=10.0/L=4/n_min=0.0 is byte-equivalent to cosine at the 3-seed level, and codim_real_g vs codim_permuted is byte-identical at this config. Paper B's experiments must sweep `eps × L × profile_residual_fn` to find the lever's active regime before any meaningful cell-level exercise. The 16-site cache is shipped (Wave 296 P5: 38/38 tests, 16/16 sites) but cell-level exercise is pending. Total GPU budget: ~6 hours on PRO 6000. Target venue: IEEE TNNLS or TKDE. Timeline: Wave 305+ (after Paper A submission + reviewer feedback). Push remains deferred per user directive.

This doc + the parent doc (`wave299-final-verification.md`) + the companion doc (`wave299-paper-a-outline.md`) constitute the single audit trail for the Wave 299 paper-split decision.
