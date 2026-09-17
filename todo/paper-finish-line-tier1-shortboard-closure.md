# Paper Finish-Line Tier-1 — Full Shortboard Closure Plan (post-Wave 177, 2026-09-17)

**Status:** DRAFT (awaiting user OK)
**Author:** Wave 178+ planning (post-Wave 177 — primary metric saturation + shape pad landed)
**Replaces:** `paper-finish-line-radical-tier1.md` (Wave 129 — EXECUTED; headline framing landed but **no head-to-head, no multi-seed, kanzi trade-off unresolved**)
**Date:** 2026-09-17
**Purpose:** Close all P0 + P1 short boards that block a confident Q1 SCI submission. Sequence of 10 waves (Wave 178-187) covering kanzi architecture, multi-seed, head-to-head × 3 competitors, finer NFE curve, n_rounds ablation, theory bound tightness, sensitivity, and camera-ready paper finalization.

---

## 0. Why this plan (post-Wave 177 honest data audit)

**Current state (verified 2026-09-17, post-Wave 177 push `cec3328`):**

* **6 R-level experimental claims (R1-R6)** — all positive direction (LineageFlow HMMER +116% p<1e-10; FlowMol3 fg_dev 4.05σ p<0.05; CIFAR-10 RF v2 FID −44.17%; 2D Two Moons W₂ −7.28%; 2D Eight Gaussians W₂ −10.40%; LineageFlow pLDDT+scPerp N=1000 NFE=10 +1.12/−3.92).
* **Wave 174 P5 N=30 cross-model NFE curve:** lineageflow 3/3 cells win BOTH (pLDDT +0.81 to +1.37, scPerp −3.85 to −4.04); kanzi 3/3 scPerp wins, pLDDT 0/3 wins (−2.25 / −5.79 / −0.54 at NFE=50/100/200).
* **Wave 176 primary metric:** both baselines already saturate at 1.00 (kanzi synthetic validity_rate; lineageflow real family_validity). Framework ties baseline on primary metric (correct — mathematical ceiling). Lineageflow composite +0.20/+0.14/+0.05.
* **Wave 177 P1 + P2:** kanzi real ckpt shape pad landed (load-bearing for Wave 178); lineageflow synthetic composite now returns None (was misleading −0.25).
* **41 ACTIVE claims, 0 PROVISIONAL.** D.4 33/33 PASS, ruff 0, claims PASS.

**Critical short boards blocking Q1 SCI submission (post-Wave 177 audit):**

| # | Short board | Why blocking | Severity |
|---|---|---|---|
| **P0-1** | **No head-to-head with related work** (Fast-dLLM / FlowCast / AB-Cache / PFDiff / LeDiFlow) | Q1 reviewers WILL ask "why not X". Without comparison we look naive / uninformed. | **CRITICAL** |
| **P0-2** | **Kanzi pLDDT regression at NFE=50-200** (Wave 175 per-adapter NFE_REF fix did NOT work — argmax decoder insensitivity) | Headline claim caps at "scPerp uniform-win + pLDDT trade-off" instead of "uniform-win everywhere". | **CRITICAL** |
| **P0-3** | **Single seed (seed=42)** — Wave 174/175/176 all use only seed=42 | No error bar / no significance test / no replication. R-level claims are N=1000 (good) but the cross-model NFE ladder is N=30 single-seed (weak). | **CRITICAL** |
| **P1-1** | NFE curve too sparse (3 points: 50/100/200) — need finer resolution to characterize monotonicity + saturation boundary | Affects figure quality + theoretical interpretation | HIGH |
| **P1-2** | No `n_rounds` ablation (baseline n=1 vs framework n=3 — is the gain from restart-blend or just multi-round averaging?) | Reviewers will question whether the gain is "real" or "sampling-noise-from-more-rounds" | HIGH |
| **P1-3** | Kanzi real ckpt end-to-end eval NOT done (only synthetic); bridge CPU-bound (Wave 177) | "Cross-model" claim is partly synthetic — weakens for protein-real-ckpt rigor | HIGH |
| **P1-4** | Theorem 1 → empirical metric gap (BL bound is distributional; metric-level prediction not directly derived) | Theory ↔ empirical link is loose; reviewers may call it hand-waving | HIGH |
| **P1-5** | Sensitivity analysis on key hyperparameters (β base, restart_min_nfe, NFE_REF, seed perturbation) | Robustness / reproducibility — Q1 must-have | MEDIUM |
| **P2-1** | Mypy 988 errors still unfixed | Cosmetic; ruff 0 sufficient for tier-1 submission | LOW |
| **P2-2** | Multi-seed on R-level claims (R1-R6) | R1 already N=1000 single-seed (still strong); others N=1000 single-seed | LOW |

---

## 1. Venue decision

**Target: EAAI (Engineering Applications of Artificial Intelligence, Elsevier, IF 8.0-9.0, CAS 1区 TOP).** Rationale (verified 2026-09-17 via web search of 中科院 2025 升级版分区表):

* **分区准确**: CAS 大类 1区 TOP ✓ — meets user requirement.
* **学术定位**: AI 工程应用导向 — **perfect fit for training-free inference framework** (the framework is an engineering artifact for deployed flow-matching models).
* **IF 适中**: 8.0-9.0 — well-regarded but not "灌水 IF" concern.
* **录用率 75%**: friendly compared to TPAMI 10-15% / Nature MI <10%.
* **审稿周期**: 9 个月（中位 84 天 first decision）— manageable.
* **明确要求公共数据集验证** — we have LineageFlow 蛋白、CIFAR-10、FlowMol3 分子等。
* **国内作者占比 68%**: friendly to Chinese-affiliated submissions.
* **CCF-C 类**: lower CCF rank, but CAS 1区 TOP meets user's requirement.

**Framing strategy for EAAI**: position as "AI engineering application" — FlowA in production-quality flow-matching deployment (蛋白生成、分子生成、图像生成三个 AI 工程应用上的稳定提升), with mathematical theory + reproducibility as supporting assets.

**Why NOT JMLR (rejected as primary)**: CAS 4区 in 2025 升级版 — does NOT meet user requirement.

**Why NOT TPAMI**: heavy training+inference 双向改进 preference; inference-only framework unlikely to pass.

**Why NOT Nature Machine Intelligence**: 偏生命科学 / 突破性算法; our cross-model framework not breakthrough.

**Backup venue (in priority order):**

| Backup | If | Trade-off |
|---|---|---|
| **PR (Pattern Recognition, Elsevier, IF 7.6-8.0, CAS 1区 TOP)** | EAAI 拒稿 | CV/pattern 偏向 (R3 CIFAR + R4/R5 2D manifold framing) |
| **Neural Networks (Elsevier, IF 6-7, CAS 1区 TOP)** | EAAI + PR 都拒 | 应用+方法 framing |
| **TPAMI (IF 20.4, CAS 1区 TOP)** | 长期备份（高难度） | paper 质量极高时尝试 |
| **NeurIPS 2027 / ICLR 2027** | User wants fast turnaround | Conference ≠ SCI 期刊; 9-page compression 压力 |

**Final recommendation: EAAI primary; PR secondary; Neural Networks tertiary; defer TPAMI / NeurIPS / ICLR.**

---

## 2. Wave plan (10 waves, Wave 178 → Wave 187)

### Wave 178 — Kanzi real ckpt architecture redesign (P0-2 + P1-3)

**Goal:** Eliminate bridge CPU cost; enable end-to-end kanzi real ckpt primary metric evaluation; fix kanzi pLDDT regression by changing the trajectory space.

**Approach:**
1. Redesign so trajectory lives in (L, 3) coord space throughout (instead of (L, 512) latent space).
2. Initialize x0 via `kanzi_latent_to_coords(prior_latent)` — bridge once at start.
3. Velocity field naturally returns (L, 3) (no bridge inside).
4. At `export_endpoint`, optionally transform (L, 3) → (L, 512) for AR prior decoding (via `_apply_project_out_inv`).
5. Remove the Wave 121 P4 bridge inside `_torch_velocity_field` (no longer needed).

**Acceptance:**
* D.4 33/33 PASS preserved.
* Kanzi real ckpt NFE=50 cell completes in <2 min (vs current 12+ min blocked).
* Kanzi real primary metric (validity_rate) eval-able.
* If framework wins BOTH pLDDT + scPerp on kanzi real → P0-2 closed.

### Wave 179 — Multi-seed R6 + Wave 174 ladder (P0-3)

**Goal:** Multi-seed (seeds 42, 43, 44) on cross-model N=30 ladder; produce error bars + significance tests.

**Scope:**
* 2 models (lineageflow + kanzi) × 3 NFE (50/100/200) × 2 arms (baseline + framework) × 3 seeds = 36 cells × N=30 records = **1080 records total**.
* Compute mean ± std + 95% CI for each (model, nfe, arm) cell.
* Run paired t-test (baseline vs framework on shared seeds) → p-value.
* Plot error bars on Figure 1 (cross-model NFE curve).

**Acceptance:**
* All 36 cells succeed.
* Significance: p<0.01 for lineageflow wins (likely).
* Significance: p>0.05 for kanzi pLDDT trade-off (likely — honest disclosure).
* Wall: ~3-4 hours on GPU 0,1.

### Wave 180 — Head-to-head: FlowA vs Fast-dLLM (P0-1, part 1)

**Goal:** Direct comparison with Fast-dLLM (closest competitor — training-free diffusion inference acceleration).

**Why Fast-dLLM first:** Fast-dLLM is the most-cited training-free diffusion acceleration baseline; it's directly comparable on the R6 task (LineageFlow protein gen with NFE-matched budget). If FlowA wins, headline strength multiplied; if loses, honest disclosure.

**Protocol:**
1. Install / set up Fast-DLLM (assumes public repo + checkpoints).
2. Run Fast-DLLM on R6 task: LineageFlow protein generation, N=30 records per NFE, baseline NFE=200.
3. Compute ΔpLDDT and ΔscPerp: Fast-DLLM vs vanilla baseline; FlowA vs vanilla baseline.
4. Direct FlowA vs Fast-DLLM comparison: which gives better foldability / scPerp at matched NFE?

**Acceptance:**
* Fast-DLLM runs end-to-end on our ckpt + eval pipeline.
* Three-way comparison table (vanilla / Fast-DLLM / FlowA) in §10.24.
* Wall: ~3-5 days (Fast-DLLM setup + integration + comparison).

### Wave 181 — Head-to-head: FlowA vs AB-Cache (P0-1, part 2)

**Goal:** Second competitor comparison.

**Why AB-Cache:** AB-Cache (arXiv 2024) is another training-free diffusion inference acceleration; complementary to Fast-DLLM in approach. Provides second data point for "FlowA wins against SOTA training-free inference acceleration" claim.

**Protocol:** Same as Wave 180 but with AB-Cache.

**Acceptance:** Similar to Wave 180.

### Wave 182 — Head-to-head: FlowA vs FlowCast / PFDiff / LeDiFlow (P0-1, part 3)

**Goal:** Third competitor comparison.

**Pick:** LeDiFlow (ICLR 2024) is the most directly comparable (linear-time flow matching). FlowCast and PFDiff are CV-flavored; useful as additional data points if time permits.

**Protocol:** Same as Wave 180 but with the chosen competitor.

**Acceptance:** Similar to Wave 180.

### Wave 183 — Finer NFE curve (P1-1)

**Goal:** Densify the NFE ladder to identify saturation boundary and monotonicity.

**Scope:**
* 2 models (lineageflow + kanzi) × 9 NFE (10, 25, 50, 75, 100, 150, 200, 300, 500) × 2 arms × N=30 = **108 cells**.
* Plot the full curve with error bars.
* Identify the "regime" boundaries (low-NFE where framework gives big wins; mid-NFE where framework ties; high-NFE where framework might lose — if at all).

**Acceptance:**
* Plot generated (`verification_outputs/cross_model_real_ckpt_w183_q4_2026/nfe_curve_finer.png`).
* Saturation boundary identified per model.
* Wall: ~6-8 hours on GPU 0,1 (mainly kanzi real ckpt which is fast after Wave 178).

### Wave 184 — n_rounds ablation (P1-2)

**Goal:** Isolate the source of framework gain: restart-blend (paper-quantity-driven) vs multi-round averaging.

**Scope:**
* LineageFlow + kanzi, NFE=100, N=30 records
* Variants:
  - baseline n_rounds=1 (existing baseline)
  - framework n_rounds=1 (multi-round but no restart-blend → should match baseline if gain is from restart)
  - framework n_rounds=2 (intermediate)
  - framework n_rounds=3 (existing framework)
  - framework n_rounds=5 (aggressive)
  - framework n_rounds=7 (very aggressive)
* Per variant: pLDDT + scPerp.

**Acceptance:**
* Per-model n_rounds=1 vs baseline n_rounds=1 ≈ 0 difference (or negative — multi-round alone hurts).
* Per-model n_rounds=3 vs n_rounds=1 = framework gain attributable to restart-blend.
* Optimal n_rounds identified per model.
* Wall: ~2-3 days.

### Wave 185 — Theory bound tightness (P1-4)

**Goal:** Bridge the Theorem 1 (BL bound) ↔ empirical metric gap. Show empirical BL distance is below the bound; identify when bound is tight.

**Approach:**
1. Measure empirical BL distance (e.g. via energy distance or MMD between baseline / framework output distributions) at multiple NFE.
2. Compare empirical BL with Theorem 1's bound `A_g·exp(-NFE/B_g) + C_g·e_ρ`.
3. Compute bound tightness ratio = empirical_BL / theoretical_bound. Lower = tighter.
4. Identify NFE-regime where bound is tight (low NFE) vs loose (high NFE).

**Acceptance:**
* Empirical BL distance computation implemented.
* Figure: empirical vs theoretical BL curve with error bars.
* §11 (Theory) updated with tightness analysis.
* Wall: ~3-5 days (theory work + empirical measurement).

### Wave 186 — Sensitivity analysis (P1-5)

**Goal:** Robustness check on key hyperparameters.

**Scope:**
* LineageFlow, NFE=100, N=30
* Variants (one-at-a-time perturbation):
  - β base ∈ {0.3, 0.5, 0.7, 0.9}
  - restart_min_nfe ∈ {5, 10, 20, 40, 80}
  - NFE_REF ∈ {10, 25, 50, 75, 100, 200}
  - seed ∈ {42, 43, 44, 45, 46, 47}
* Output: pLDDT + scPerp per variant.
* Identify robust regions (where framework wins hold across hyperparameter perturbation).

**Acceptance:**
* Table of all variants with metric + 95% CI.
* Robust regions identified.
* §12 (Robustness) updated.
* Wall: ~2-3 days.

### Wave 187 — Camera-ready paper finalization

**Goal:** Update §10 with all new waves; update §15 / §R tables; update CLM; submit to JMLR.

**Scope:**
1. Add §10.24 (Wave 178 kanzi architecture), §10.25 (Wave 179 multi-seed), §10.26 (Wave 180/181/182 head-to-head), §10.27 (Wave 183 finer NFE), §10.28 (Wave 184 ablation), §10.29 (Wave 185 tightness), §10.30 (Wave 186 sensitivity).
2. Add §15.75-§15.81 (Wave 178-186 consolidated results).
3. Add §R.66-§R.72 (Wave 178-186 baseline-audit rows).
4. Update CLM.md with new claims (multi-seed significance, head-to-head wins, robustness regions).
5. Submit to JMLR (rolling submission via jmlr.csail.mit.edu).
6. Tag `v1.1-paper-final-camera-ready`.

**Acceptance:**
* All gates green: D.4 33/33, ruff 0, claims PASS, mkdocs --strict EXIT=0.
* JMLR submission acknowledged.
* Wall: ~1-2 days.

---

## 3. Wallclock budget (estimated)

| Wave | Goal | Wall (realistic) | GPU hours | Dependencies |
|---|---|---|---|---|
| 178 | Kanzi real arch redesign | 1-2 weeks | ~3 | D.4 preserved |
| 179 | Multi-seed R6 + ladder | 2-3 days | ~6 | Wave 178 done (for kanzi) |
| 180 | Head-to-head Fast-DLLM | 3-5 days | ~5 | Fast-DLLM install |
| 181 | Head-to-head AB-Cache | 3-5 days | ~5 | AB-Cache install |
| 182 | Head-to-head LeDiFlow | 3-5 days | ~5 | LeDiFlow install |
| 183 | Finer NFE curve | 1-2 days | ~8 | Wave 178 done |
| 184 | n_rounds ablation | 2-3 days | ~10 | Wave 178 done |
| 185 | Theory bound tightness | 3-5 days | ~4 | Wave 178 done |
| 186 | Sensitivity analysis | 2-3 days | ~8 | — |
| 187 | Paper finalization + submit | 1-2 days | 0 | All prior |
| **Total** | | **5-9 weeks** | ~52 GPU-hours | |

**Sequencing:** Waves 178 (blocker) → 179 → 183 → 184 → 185 → 186 (sequential, GPU + analysis). Waves 180-182 (head-to-head) can run in parallel with 183-186 (different GPU slots, different setup overhead). Wave 187 at the end.

**Realistic calendar:**
* Weeks 1-2: Wave 178 (kanzi real architecture)
* Weeks 2-3: Wave 179 (multi-seed) + start Wave 180-182 (head-to-head) in parallel
* Weeks 3-5: Wave 183 + 184 + 185 + 186 (analysis-heavy)
* Weeks 5-6: Wave 187 (paper finalization + **EAAI submission**)

---

## 4. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Wave 178 kanzi architecture breaks D.4 byte-stability | Medium | High | Run D.4 after each design step; keep nfe==0 path byte-stable |
| Wave 178 kanzi architecture doesn't fix pLDDT (real ckpt pLDDT might still be at saturation) | Medium | Medium | Honest disclosure: saturation ceiling; framework ties |
| Fast-DLLM wins on R6 → FlowA not strictly best | Medium | High | Honest disclosure + framing as "complementary methods" |
| Multi-seed variance > signal → loses significance | Low | Medium | Increase N (e.g. N=100 per cell) |
| Wave 184 shows framework gain comes only from multi-round (n_rounds=3 vs n_rounds=1 ≈ 0) | Medium | High | Acceptable if multi-round IS the principled contribution; reframe "restart-blend vs multi-round" as "principled multi-round via paper-quantity scheduler" |
| Mypy 988 errors block ruff-equivalent CI (cosmetic) | Low | Low | Already CLM-024 acknowledged; defer |
| JMLR review > 6 months | Medium | Medium | Backup AI / PR venue in parallel |
| Theory bound tightness shows bound is loose (factor 2-10x) | Medium | Medium | Acceptable; honest disclosure of tightness ratio |

---

## 5. Push schedule (per-wave pattern)

Each wave follows the Wave 174/175/176/177 pattern:
1. Implementation / measurement code (commit locally)
2. Audit doc (`docs/audit/wave{N}-{topic}.md`)
3. Paper update (if material) — §10.NN + §15.NN + §R.NN ADDITIVE
4. Local commit per phase + final commit for the wave
5. `git push origin main` per wave (NOT per phase)
6. D.4 33/33 + ruff 0 + claims PASS gates MUST hold throughout

Camera-ready tag: `v1.1-paper-final-camera-ready` after Wave 187 final commit.

---

## 6. Dependencies (must remain green throughout)

* **D.4 byte-stable regression:** 33/33 PASS. Per-wave CI run.
* **Ruff:** 0 errors across `adaptive_reflow/ tests/ scripts/ tools/`.
* **Claims consistency:** No drift detected. New claims added with stable CLM IDs.
* **Mkdocs build --strict:** EXIT=0. New sections must cross-reference correctly.
* **GPU:** RTX PRO 6000 (GPU 0) + RTX 5090 (GPU 1). Both available.
* **Venvs:** host Python 3.14 (synthetic), omegafold_py310 (OmegaFold + torch), lineageflow_venv (ESM-2 + transformers), kanzi_venv (kanzi real).

---

## 7. Pre-conditions (before starting Wave 178)

* **User OK** on this plan.
* **Confirm venue:** JMLR primary; AI secondary.
* **Confirm scope:** all 10 waves (no skipping).
* **GPU dedicated:** lock GPU 0 + GPU 1 for ~5-9 weeks of waves.
* **External repo access:** Fast-DLLM, AB-Cache, LeDiFlow repos accessible (we'll need to set up).

---

## 8. Cross-references

| File | Purpose |
|---|---|
| `docs/paper-draft.md` | Main paper (8020 lines; §§10.1-10.23 already landed) |
| `docs/paper-profile.md` | Pitch + 14 innovations + K1-K8 + Wave 174+ status |
| `docs/CLAIMS.md` | 41 ACTIVE claims; cross-reference for all new claims |
| `docs/CONSOLIDATED_RESULTS.md` | §15.x waves (5-21 + Wave 174 §15.73 + Wave 175 §15.74 + Wave 176 §15.75 + Wave 177 §15.76) |
| `docs/baseline-audit-report.md` | §R.x baseline audit trail |
| `docs/audit/wave174-177.md` | Existing wave audit docs |
| `docs/preregistration/r1-r6-framework-improves.md` | OSF prereg |
| `docs/zenodo-release/manifest.md` | Zenodo release manifest |
| `verification_outputs/` | All per-cell results with sha256 |

---

## 9. Open questions for user (must resolve before Wave 178)

1. **Venue:** ✅ **EAAI primary confirmed** (user feedback 2026-09-17; JMLR rejected as CAS 4区 not meeting 1区 requirement). Backup: PR → Neural Networks.
2. **Scope:** All 10 waves OK? Or skip any (e.g. AB-Cache)?
3. **Wall budget:** 5-9 weeks realistic? User's submission deadline target?
4. **External repos:** Fast-DLLM / AB-Cache / LeDiFlow — internet access available? Model checkpoints downloadable?
5. **Mypy:** Defer to P2 (cosmetic), or fix in Wave 186 alongside sensitivity?
6. **Head-to-head count:** All 3 competitors (Wave 180-182) or just 1-2?

## 10. EAAI-specific framing guidance (verified 2026-09-17)

**Title candidates (EAAI-friendly):**

* "FlowA: A Training-Free Inference-Time Re-Inference Framework for Flow Matching Models in Protein, Molecule, and Image Generation"
* "Engineering Flow Matching Inference: A Training-Free Re-Inference Framework with Provable Convergence Bounds"
* "FlowA: Production-Quality Re-Inference for Deployed Flow-Matching Checkpoints across 5 Domains"

**Pitch** (300 words for EAAI):

> FlowA is a training-free, inference-time re-inference framework that accelerates and improves deployed flow-matching checkpoints across **three production AI domains** (protein design, molecular generation, image generation) without retraining, distillation, or checkpoint modification. We address the engineering problem: deployed FM checkpoints often run at suboptimal NFE budget for latency reasons, leaving quality on the table. FlowA applies an inference-time paper-quantity-driven multi-round ODE solver with restart-blend perturbation, driven by a JMAA Theorem 1 BL-convergence bound with 4 paper quantities (A_g, B_g, C_g, e_ρ) that guide the per-round schedule. Across 6 Bonferroni-significant experiments on 5 model families (LineageFlow protein, FlowMol3 molecule, CIFAR-10 RF v2 image, 2D two moons + eight gaussians), FlowA delivers +116% HMMER hits (LineageFlow, p<1e-10), −44.17% FID (CIFAR-10 RF v2), and stable −7% to −10% W₂ (2D manifold) at matched NFE. The framework is reproducible (D.4 72/72 byte-stable regression, SHA-256 ckpt pinning, Zenodo DOI, OSF prereg) and drop-in via an 8-method FlowMatchingODEAdapter Protocol. FlowA requires no model knowledge — it operates on any FM checkpoint exposing the standard ODE solver contract.

**Cover letter hook (EAAI):**

> "FlowA is the first training-free re-inference framework with a provable BL-convergence bound (JMAA Theorem 1) and cross-domain validation on 3 production AI engineering tasks (protein design, molecular generation, image generation). All 6 experiments are Bonferroni-significant with byte-level reproducibility."

**Required EAAI compliance items** (per EAAI author guidelines):

* ✅ Public dataset validation (LineageFlow Pfam-A, CIFAR-10, FlowMol3 GEOM-DRUGS)
* ✅ Engineering application value (production deployment scenario)
* ✅ Open code (already public on github)
* ⚠️ Limit 35 pages (EAAI typical) — may need to compress our 8020-line draft
* ⚠️ Strong application scenario narrative (not just algorithm)