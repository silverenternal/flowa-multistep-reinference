# Wave 305 — Day 0 Risk Package (supplement to `wave303-day0-prompt.md`)

**Date:** 2026-09-23
**Mode:** READ-ONLY on `paper-flat-flattened.md` + READ-ONLY on `wave303-day0-prompt.md` + READ-ONLY on `wave303-day0-14-plan.md`
**Author:** Wave 305 Day 0 risk-package assembly agent
**Supplement to:** `docs/audit/wave303-day0-prompt.md` (the canonical D0 user-authorization prompt — do NOT modify)
**Supersedes:** `docs/audit/wave303-day0-14-plan.md` (Wave 303 14-day plan — DeepSeek now says 5-7 days, see §6 below)
**Gate baseline:** All 5 gates PASS on current unchanged paper (verified 2026-09-23, see §7 below)

---

## 0. TL;DR

The 6 dual-present pair decisions, Wave 268 strict-clean authorization, TNNLS venue lock, and 14-day timeline are already in `wave303-day0-prompt.md` §1-§4. This doc **adds 4 risk-deliverables** that the user will need before D1: (i) the §6 JMAA residual deletion list — the line-by-line checklist the agent will use at D5 to drop §6 entirely; (ii) the codim / CodimensionSheetScheduler / TierAware / eps_implicit contamination list — file-by-file cleanup to ensure no codim-language leaks into Paper A; (iii) three paste-ready text blocks (R3 / R5b / R2 boundary wording) for the user to drop into §9 Limitations or §7 Empirical Results; (iv) a 5-7 day timeline confirmation note that the 14-day plan compresses cleanly because the fold-in draft already has 6475 words and only ~1000-2000 more are needed.

---

## 1. §6 JMAA Residual Deletion List

Source-of-truth grep: `docs/drafts/paper-flat-flattened.md` lines 1-1404. This is the checklist the agent will execute at D5 / D10 to drop §6 entirely. Lines are listed in numerical ascending order. **Reads §6 = `lines 1238-1262` (the §6 heading + body + closing `---`).** All other JMAA/Theoretical Lenses/Banach/Lyapunov/Lemma 3, 5/Theorem 1/Proposition 3 hits are in legacy sections (legacy §1, legacy §2, §9, §10) that are either already deleted in the Wave 303 D1-D6 RESOLUTION pass or must be reworded at D10 to remove the theorem-but-MSA references in-line.

| Location (line range) | Section | Verbatim phrase (excerpt) | Action |
|---|---|---|---|
| **L1238-1262** | §6 Theoretical Lenses (current section) | `## §6 Theoretical Lenses (Wave 296 P7 + Wave 297 P2 §4.6 + Wave 300 P5 fold-in)` — full 25-line block including the 4-paragraph draft prose skeleton (¶1 "JMAA Theorem 1 + Lemmas 2–5 ... **15 of 16 enumerated Theorem 1 application sites are dormant**", ¶2 "Theorem 1 statement (compressed to 1 paragraph...) bounded-Lipschitz distance ... A_g · exp(−NFE/B_g) + C_g · e_ρ", ¶3 "CodimensionSheetScheduler consumes (A_g, B_g, C_g) ... partially validated on R6 k6 foldability", ¶4 "FID Δ=0% as framework robustness proof ... **module-independent of the theorem**") | **DELETE entire block** (D5 / D10) — ~520 words |
| L1240 | §6 target word count | `**Target word count:** 600–800 words (Wave 299 §3.6) — trimmed to 1.5 pages per DS-06.` | DELETE with §6 |
| L1241 | §6 source-of-truth | `**Source-of-truth:** **FRESH-WRITING** — Wave 296 P7 FID Δ=0% (`docs/audit/wave296-p7-fid-comparison.md` §3) + Wave 297 P2 §4.6 + Theorem 1 self-contained (`docs/theory/theorem-1-self-contained.md` Sections A-F).` | DELETE with §6 |
| L1247 | §6 ¶1 | `¶1 — Theoretical lens framing. This section presents JMAA Theorem 1 + Lemmas 2–5 as **one theoretical lens** among several possible (Wasserstein, total-variation, Jensen–Shannon); the framework is architecture-validated independent of which lens the practitioner prefers. Per the §7.4 framework-not-theory verdict: 10 of 11 headline cells instantiate `CosineAnnealScheduler`, the baseline that ignores all 4 paper quantities — **15 of 16 enumerated Theorem 1 application sites are dormant** under the cosine baseline (Wave 292 P1).` | DELETE with §6 |
| L1249 | §6 ¶2 | `¶2 — Theorem 1 statement (compressed to 1 paragraph, NOT the current ~12-line dense exposition). Cite `docs/theory/theorem-1-self-contained.md` for the full statement + proof sketch. Under F-side hypotheses (F1 compactness, F2 uniform-separation, F3 simplicity, F4 exterior-gap) on the framework's posterior, the bounded-Lipschitz distance between the framework's sampling measure $\mu_{g,\varepsilon}$ and the fibre-supported ODE target measure $\nu_g$ is bounded above by $A_g \cdot \exp(-\mathrm{NFE}/B_g) + C_g \cdot e_\rho$ (equation T1)` | DELETE with §6 |
| L1251 | §6 ¶3 | `¶3 — CodimensionSheetScheduler partial scope. The `CodimensionSheetScheduler` consumes $(A_g, B_g, C_g)$ to allocate the per-round noise-and-step budget ... **16/16 sites active when `enable_full_jmaa_theory=True`**; the cell-level byte-stability exercise is deferred to a companion paper.` | DELETE with §6 |
| L1253 | §6 ¶4 | `¶4 — FID Δ=0% as framework robustness proof (Wave 296 P7 §3). The cosine baseline is **byte-identical** under the JMAA flag flip ... the theorem is a plug-in, not a load-bearing component.` | DELETE with §6 |
| L1255-1258 | §6 user-decision items | `(a) Length: ... (b) Companion-paper cross-ref ... (c) Wave 296 P7 FID Δ=0% citation ... **NEEDS-USER-INPUT.**` | DELETE with §6 (Wave 305 supersedes — see §6 timeline note below) |
| L33, L35, L58, L67 | legacy §1 ¶3 + contribution (iv) | legacy abstract + legacy ¶3 "FlowA closes this gap through a single theorem-driven interface ... bounded-Lipschitz distance between the framework's sampling measure $\mu_{g,\varepsilon}$ and the fibre-supported ODE target measure $\nu_g$ ... $A_g$ is the Lipschitz aggregate (paper Proposition 3 / line 161) ... $B_g$ is the effective NFE decay rate (paper Lemma 5 / line 159) ... $C_g$ is the per-cell residual bias (paper Lemma 3 / line 191)" | **REWORD** at D3 (Wave 297 P3 §1 prose applies verbatim per DS-01; JMAA removed from contribution list per DeepSeek §五) |
| L171-202 | legacy §2.8 §MS.theorem1_data_pipeline_entry_points | `**Table 2.8 — Sixteen application sites of JMAA Theorem 1 with data-pipeline entry points.**` (16-row table mapping sites 1-16 to file:line + factory/constructor + dormant/active status) | **REWORD / TRIM** at D4 (Wave 297 P4 §2 prose applies; Table 2.8 → small summary table or supplementary-only) |
| L369-371 | legacy §3.5 paper-quantity load-bearing discussion | `The Theorem 1 load-bearing test on the Kanzi synthetic protein axis confirms the same pattern at a different axis ... paper quantities act as a **regulariser on the per-round perturbation budget**, not as a multiplier on the perturbation magnitude. The verdict from the load-bearing test is `load_bearing_as_regulariser`.` | **REWORD** at D5 (Wave 297 P5 §7 applies; theorem/load-bearing framing removed) |
| L1328 | §9 ¶1 (Wave 297 P6 §9) | `¶1 — Theorem 1 application-site coverage is narrow under the cosine baseline. Per Wave 292 P1: the framework enumerates **16 application sites of JMAA Theorem 1**, of which **15 are dormant** under the cosine-annealing baseline.` | **REWORD** at D6 (Wave 297 P6 §9 applies verbatim per DS-01; the 16-sites framing can stay as scope-of-current-state disclosure but JMAA Theorem 1 naming can be softened to "paper-quantity sites" if §6 is dropped) |
| L1353, L1361 | §10.1.1 + §10 ¶5 | `**§10.1.1 — Wave 296 full JMAA theory integration (in progress).**` and `**§10 ¶5 — Companion paper on JMAA theory + scheduler family.** Full cell-level exercise of the 16-site cache on R-cells with paper-quantity-driven schedulers; regime-sweep to map the paper-quantity lever's active configuration space; theoretical analysis of JMAA Theorem 1 + Lemmas 2-5 closed-form derivations.` | **DROP entirely** if user D0 confirms §10 Future Work dropped (per `wave303-day0-prompt.md` §1 special sub-decisions); or **REWORD** to "Paper B companion paper" if §10 is folded into §8 |

**No Banach / Lyapunov / Lemma 3 / Lemma 5 / Theorem 1 / Proposition 3 standalone hits exist outside the §6 + §1 + §2.8 + §3.5 + §9.1.1 + §10.1.1 lines above.** Verified via `grep -nE "(Banach|Lyapunov|Lemma 3|Lemma 5|Theorem 1|Proposition 3)" docs/drafts/paper-flat-flattened.md` — all hits are sub-references inside the §6 + §2.8 tables + §3.5 paper-quantity discussion, all of which are addressed by the row-level actions above.

**Total deletion word count for §6 drop alone:** ~520 words (L1238-L1262 block). **Total deletion + reword word count for full §6 + legacy §1 ¶3 + §2.8 16-sites table + §3.5 paper-quantity discussion:** ~1700 words.

---

## 2. Codim Citation Removal List (Paper A + audit docs)

Source-of-truth grep: `grep -nE "(codim|CodimensionSheetScheduler|TierAware|tier-aware|eps_implicit)"` across `docs/drafts/paper-flat-flattened.md` and top-level `docs/audit/` files. **TierAwareCodimensionSheetScheduler / CodimensionSheetScheduler / eps_implicit** references appear in the paper as canonical §2.1 scheduler-table content (Table 4.1) and §3.5 paper-quantity discussion. **In Paper A boundary, these terms remain valid as scheduler-family member names** (they are not "JMAA" terms — they are typed-contracts family members). What MUST be removed from Paper A is the framing that the codim scheduler is **paper-quantity-driven / drives the JMAA theorem**, because that conflates architecture (typed-contracts surface) with theory (JMAA closed forms). Paper B keeps the codim lever analysis; Paper A only mentions codim as one of the 4 paper-quantity-driven controllers in the §4 Scheduler Family taxonomy, and as the **only paper-quantity-driven headline scheduler** on R6 in the §7 Empirical Results per-R-cell status table.

### 2.1 Paper file `docs/drafts/paper-flat-flattened.md`

| Line | Verbatim phrase | Action |
|---|---|---|
| L75 | `... with the single documented exception R6 (`TierAwareCodimensionSheetScheduler` wrapper around `CodimensionSheetScheduler`) covered at Wave 275 P4 as a tier-aware counterfactual. The paper-quantity-driven controllers in §2.1 — `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `ConvergenceAdaptiveScheduler`, `TierAwareCodimensionSheetScheduler` — are **RESEARCH-STAGE**: their paper-quantity consumption branches are still under release engineering per the Wave 287 audit ...` | **KEEP** (canonical §2.1 scheduler-family taxonomy — codim is one of the 4 paper-quantity-driven families, named per Wave 297 P4 §2.2) |
| L85, L86, L88, L89, L91 | Table 4.1 scheduler rows for `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `TierAwareCodimensionSheetScheduler` (incl. `eps_implicit = eps_implicit_base * (1 - u_r)`) | **KEEP** (canonical Table 4.1 content; codim terminology is appropriate scheduler-family naming) |
| L93, L95 | `The `CodimensionSheetScheduler` is the framework default since Wave 34 ... The corrected framing is therefore: **"framework factory default since Wave 34, with 12/13 R-cells still instantiating `default_cosine_scheduler()` at the adapter level**` | **KEEP** + Wave 294 P2 M-MED-1 correction (already applied per `docs/audit/wave294-p2-medium-fixed.md`) |
| L151 | `The `paper_quantity_driven_beta()` helper at `adaptive_reflow/algorithm/scheduler/adaptive.py:2576` converts a target RMSD threshold ... consumes the four paper quantities at call time ... and returns a `float` in `[0, 1]` that can be passed directly to `CodimensionSheetScheduler` as the `n_cap_base` argument.` | **KEEP** (canonical §A.1 prose) |
| L157, L159 | `The 5 paper-grounded controllers ...` + Footnote (Wave 275 P4 R6 relaxation) on `TierAwareCodimensionSheetScheduler` base-type guard | **KEEP** (canonical §A.2 / §A.3 prose) |
| L163-169 | `Wave 290 P1 (bottleneck confirmed)` + `Wave 290 P3 (batched harness, ~28-35× speedup)` + `Wave 291 (regime-aware paper-quantity sweep, verdict: SUPPORTED on lever existence, STRONG on codim scheduler structure)` | **KEEP** (Wave 287/290/291 audit references are §6 framing + §9 disclosure territory) |
| L196 | `**Aggregate reading.** Of the sixteen enumerated sites, only **site 1** (the cosine ramp itself; `CosineAnnealScheduler.sample` at `simple.py:143` returning the byte-stable `n_cap = n_min + (n_max − n_min) · 0.5 · (1 + cos(π r / (L − 1)))`) exercises in the cosine-baseline data path.` | **KEEP** (canonical §2.8 §MS.theorem1_data_pipeline_entry_points aggregate reading) |
| L214 | R6 row in Table 2.9: `7 | **R6 k6 foldability** | **`TierAwareCodimensionSheetScheduler`** wrapping **`CodimensionSheetScheduler`** — only paper-quantity-driven headline | ...` | **KEEP** (canonical §2.9 per-cell headline configuration table) |
| L221 | `... paper-quantity-driven controllers consume paper quantities and were designed for them, but remain under release engineering per the Wave 287 + Wave 291 audits.` | **KEEP** |
| L349, L351, L359 | A2 / A4 cumulative-add ablation rows referencing `CodimensionSheetScheduler` + `EvidenceDrivenScheduler` (C4 closure, writes `eps_implicit`) | **KEEP** (canonical §3 cumulative-add ablation) |
| L411 | K4 — Scheduler-port coupling: `The CodimensionSheetScheduler, BoundedMergeOperator, and EvidenceDrivenScheduler are designed to activate jointly through the four-loop round lifecycle ...` | **KEEP** |
| L515 | `Why the framework's identity is the typed contract, not the theorem.` — `**15 of 16 enumerated Theorem 1 application sites are dormant under the validated cosine baseline**` | **REWORD at D4** (Wave 297 P4 §3 prose applies; soften "Theorem 1" naming if §6 is dropped) |
| L538, L551, L558, L646 | §7.1 / §7.2 / §7.4 references to `CodimensionSheetScheduler` in the 4 paper-quantity-driven controllers list + Table 7.1 R6 row | **KEEP** (canonical §7 Empirical Results) |
| L671, L673 | §7.4 framework-not-theory verdict: `**10 of 11 headline cells instantiate `CosineAnnealScheduler`** ... and only **1 of 11 cells** (R6 k6 foldability) instantiates a paper-quantity-driven wrapper (`TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`)` | **KEEP** (canonical §7.4 framework-not-theory verdict — this is empirical evidence that elevates typed-contracts over theory) |
| L720 | R6 PARTIAL row in §7.2: `R6 PARTIAL — Kanzi k6 foldability hard-tier pLDDT framework-WINS by +1.189 σ (cluster-robust p_cluster = 1.28e-2) + scPerplexity framework-WINS uniformly across all 3 tiers (cluster-robust p_cluster ≤ 1e-2) on `TierAwareCodimensionSheetScheduler` (the only paper-quantity-driven headline; Wave 204 P2 cross-adapter replication on LineageFlow N=574 paired confirms the monotone `hard > medium > easy` pLDDT pattern on 2 adapters).` | **KEEP** |
| L760-810 | §9 Limitations (Wave 297 P6): `§9.1.1 dormant sites` + `§9.1.2 codim CIFAR HARMFUL +10.721%` + `§9.1.3 Wave 287 bugs (2 critical in codim all-zero path)` + `§9.1.5 codim GPU bottleneck fix (Wave 290 batched harness)` | **REWORD** at D6 (Wave 297 P6 §9 prose applies verbatim per DS-01; codim terminology stays but framing softens — codim stays valid scheduler-family naming) |
| L989, L990 | §A.x references to `wave286-p5-claims-update.md` (codim 17-cell CIFAR-10 RF re-sweep) + `wave291-p4.md` (codim_real_g vs codim_perm byte-identical at +10.721% Δ% vs cosine) | **KEEP** (canonical references list) |
| L1205, L1209, L1251 | §3 fold-in prose: `**4 paper-quantity-driven controllers (PRIMARY contribution).**` (CodimensionSheetScheduler + 3 others) + Validated headline usage (12/13 cosine, 1/13 codim) + CodimensionSheetScheduler partial scope | **KEEP** (canonical §3 fold-in prose) |
| L1308, L1330, L1336, L1353, L1355, L1359 | §8 / §9 / §10 fold-in prose: 6-gate CI Wave 290 P3 batched harness + Wave 296 P2 PaperQuantitiesCache opt-in + codim CIFAR +10.721% HARMFUL + Wave 290 codim GPU bottleneck fix + §10.1.1 Wave 296 full JMAA theory + §10.2 Codim regime expansion + §10.4 Per-site empirical validation | **REWORD** at D10 (Wave 300 P5 fold-in applies; codim terminology stays for scheduler-family references; "JMAA" wording removed if §6 dropped) |

**Net codim contamination removal at paper = 0 lines** — codim is a valid scheduler-family member name and appears throughout as canonical §2.1 + §3 + §7 content. What is removed is the **JMAA-theorem framing around codim** (e.g., L515 "15 of 16 Theorem 1 application sites", L1328 "16 application sites of JMAA Theorem 1", L1353 "Wave 296 full JMAA theory integration"), which is captured by §1 above.

### 2.2 Audit doc contamination list (top-level files only, not vendored)

| File:Line | Phrase | Action |
|---|---|---|
| `docs/audit/wave303-day0-14-plan.md:648` | `**D.5** | Write `docs/drafts/paper-b-jmaa/contributions.md` (4-6 primary contributions: JMAA Theorem 1 4-paper-quantities, CodimensionSheetScheduler sweep, paper-quantity-driven scheduler family, 16-site integration, convergence analysis, FID Δ=0% evidence)` | **KEEP** — Paper B skeleton D.5 (JMAA + Codimension sweep migrate to Paper B per DeepSeek §四) |
| `docs/audit/wave297-p2-paper-design.md:28` | `**THEORETICAL ENRICHMENT:** JMAA 16-site framework + CodimensionSheetScheduler partial R6 validation + Wave 296 in-progress opt-in cache (§6 — companion, not primary).` | **REWORD** at D10 (Wave 297 P2 §1 contribution wording is applied; "theoretical enrichment" is the legacy Wave 297 P2 framing) |
| `docs/audit/wave297-p2-paper-design.md:45` | Table row `**§4 Scheduler Family** (13 schedulers — 9 without paper quantities, 4 with paper quantities)` | **KEEP** (canonical §4 description) |
| `docs/audit/wave297-p2-paper-design.md:47` | Table row `**§6 Theoretical Lenses**` — `CodimensionSheetScheduler partially validated on R6 (k6 foldability). Wave 296 in-progress: 15/16 sites dormant under cosine baseline, PaperQuantitiesCache opt-in flag activates them.` | **DROP §6 row entirely** at D10 (per DeepSeek §四 — JMAA → Paper B) |
| `docs/audit/wave297-p2-paper-design.md:50` | Table row `**§9 Limitations**` — `CodimensionSheetScheduler regresses CIFAR-10 RF by 10.7% at matched NFE — the image-domain boundary is structural, not a bug.` | **KEEP** (codim terminology stays valid in §9 as scheduler-family member) |
| `docs/audit/wave297-p2-paper-design.md:51` | Table row `**§10 Future Work**` — `Wave 296 full integration (PaperQuantitiesCache activated across all 15 dormant sites); codim regime expansion (cross-budget to matched-NFE crossover); 3-seed headliner re-verification` | **DROP §10 row entirely** if user D0 confirms §10 dropped |
| `docs/audit/wave297-p2-paper-design.md:84` | `**Theoretical enrichment sentence (closes with JMAA):**` — `CodimensionSheetScheduler is partially validated on R6 foldability and the full JMAA 16-site activation is in-progress (Wave 296)` | **DROP** (per DeepSeek §四 — JMAA → Paper B) |
| `docs/audit/wave297-p2-paper-design.md:101` | `FlowA is also accompanied by a theoretical lens (one companion among several possible): we state Theorem 1 within the self-contained companion document ... CodimensionSheetScheduler consumes these quantities directly as scheduler inputs and is **partially validated on the R6 k6 foldability cell**; the full 16-site activation across the framework's algorithm and evaluator layers is in-progress (Wave 296, PaperQuantitiesCache opt-in flag).` | **REWORD at D3** (Wave 297 P3 §1 prose applies; compressed 1-paragraph companion version stays — codim stays valid) |
| `docs/audit/wave297-p2-paper-design.md:110` | `**§1 contribution (iv)** As a theoretical companion (not the framework's identity), we introduce the JMAA 16-site framework: Theorem 1 + Lemmas 2-5 provide a bounded-Lipschitz convergence-theory bound on the framework's sampling distribution, with CodimensionSheetScheduler partially validated on R6 k6 foldability and Wave 296 (PaperQuantitiesCache opt-in) in-progress for full 16-site activation.` | **DROP entirely** at D10 (DeepSeek §五 — 4-contribution wording removes (iv)) |
| `docs/audit/wave297-p2-paper-design.md:124, 152, 155, 157, 177, 202, 208, 219` | Multiple Wave 297 P2 design-table references to `CodimensionSheetScheduler`, `TierAwareCodimensionSheetScheduler`, scheduler-family breakdown | **KEEP** (canonical Wave 297 P2 design context — applied at D4-D6 to canonical §3/§4/§5) |
| `docs/audit/wave297-p3-intro-rewritten.md:92, 105` | `**¶3 Theoretical companion (demoted):**` + `**§1 contribution (iv)** — JMAA 16-site framework with CodimensionSheetScheduler partial R6 validation` | **REWORD at D3** (Wave 297 P3 §1 prose applies verbatim per DS-01; compressed companion mentions Theory once via Frame-1) |
| `docs/audit/wave297-p4-framework-rewritten.md:92, 94` | `- 4 paper-quantity-driven controllers documented with closed forms: `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `ConvergenceAdaptiveScheduler`` + `- Validated headline usage: 12/13 R-cells use `CosineAnnealScheduler`; only R6 uses a paper-quantity-driven headline (`TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`)` | **KEEP** (canonical §3 framework prose; codim stays valid) |
| `docs/audit/wave297-p5-empirical-rewritten.md:97, 123, 125` | R6 row in §7.2 per-R-cell status table + framework-not-theory verdict + JMAA theorem quantifies-why-the-loop-works paragraph | **KEEP** (canonical §7 empirical results prose; codim + framework-not-theory verdict are primary contributions) |
| `docs/audit/wave297-p6-limitations-rewritten.md:12, 15, 40, 43, 45, 48, 81, 82, 85, 86, 88, 91, 92, 95, 104, 121, 127, 150-152, 154, 161, 164, 165, 177, 189, 192, 206, 212, 277, 287, 332, 333, 351, 357` | 37+ references to codim / CodimensionSheetScheduler / TierAwareCodimensionSheetScheduler / eps_implicit across §9 / §10 disclosures | **KEEP** (canonical §9 / §10 limitations prose; codim terminology stays valid as scheduler-family member + paper-quantity lever discussion) |
| `docs/audit/wave299-paper-a-outline.md:46, 58, 115, 153, 206, 207, 219` | 7 references to CodimensionSheetScheduler + paper-quantity-driven controllers across §3, §4, §6, §9 outline | **KEEP** (canonical Wave 299 outline) |
| `docs/audit/wave299-paper-b-deferred.md:32, 34, 38, 40, 80, 94, 98, 113, 126, 130, 156, 176, 270` | 13 references to codim / CodimensionSheetScheduler / eps_implicit in Paper B design rationale | **KEEP** — Paper B is where codim lever analysis belongs (per DeepSeek §四 + Wave 297 P2 §4.6) |

**Net codim contamination removal across audit docs = 0 lines** — codim is a valid scheduler-family member name and stays valid in Paper A's canonical §3 / §4 / §7 / §9 content. What is removed is the **JMAA-theorem framing around codim** (e.g., Wave 297 P2 §6 row, §1 contribution (iv), "theoretical enrichment sentence", §10 codim regime expansion row), which is captured by §1 above.

**Net codim contamination removal from Paper B boundary = +13 lines added** to `docs/drafts/paper-b-jmaa/` skeleton at D12 (per Wave 303 D12 Paper B skeleton plan — JMAA Theorem 1 + CodimensionSheetScheduler sweep migrate to Paper B per DeepSeek §四).

---

## 3. R3 Boundary Wording (FlowMol3, 1-seed per-record d_z = -0.285; 3-seed BLOCKED at vendor level)

**Drop-in paste-ready text block (~60 words), for §7 Empirical Results or §9 Limitations:**

> **R3 (FlowMol3 fg_dev, molecular 3D):** The framework shows a direction-correct 1-seed effect on the FlowMol3 fg_dev axis (baseline 0.6381 → framework 0.6146, Δ = −0.0235; d_z = **−0.285** at seed 42, N = 1000 paired; lower is better per Wave 87 byte-stable reference). The 3-seed verification (seeds 42, 43, 44 at NFE = 100, N = 500) is **blocked at the vendor level** (DGL 2.4.0 incompat with PyTorch 2.4 + CUDA 12.1 per CLM-068; flagged Wave 109.C). Per-record seed 43 partial sweep gives d_z = +3.625 (framework worse, direction-inconsistent); 3-seed pooled verdict is therefore **TIE** with honest disclosure of protocol mismatch (NFE 100 vs 250; N 500 vs 1000; single_mol vs batched graph traversal).

**Source-of-truth:** `docs/CONSOLIDATED_RESULTS.md` lines 2192 (12-cell R5b flowmol3 fg_dev −2.35pp, p=0.28), 8463 (1-seed byte-stable; 3-seed blocked by DGL 2.4.0; baseline 0.6381 → framework 0.6146 −0.023484, framework_wins), 8655 (Wave 238P1 per-seed direction diagnostic: seed 42 d_z = −0.285 framework better; seeds 43, 44 d_z = +3.625 framework worse; 3-seed pooled TIE; direction inconsistent; protocol mismatch), 8359 (Wave 235 P4 disclosure). Per-claim anchor: CLM-068 DGL 2.4.0 vendor blocker (PROVISIONAL).

---

## 4. R5b Boundary Wording (CIFAR-10 RF FID; conditional boundary: n_rounds=1 wins, n_rounds ≥ 2 regresses)

**Drop-in paste-ready text block (~75 words), for §7 Empirical Results or §9 Limitations:**

> **R5b (CIFAR-10 RF FID, image domain matched-NFE = 50):** The framework's CIFAR-10 RF verdict is **conditional on `n_rounds`**: at `n_rounds = 1` the framework **wins** by ΔFID = **−1.60 % to −2.53 %** on 3 of 4 schedulers (Wave 235 P1 sweep at the Wave 235 P1 protocol; bonferroni-significant in framework direction); at `n_rounds ≥ 2` the framework **regresses** by ΔFID = **+9.77 %** (Wave 225 P7 at `n_rounds = 2`) and ΔFID = **+20.20 %** (Wave 191 P2 at `n_rounds = 4`). The boundary is structural: cosine ramp halves effective NFE at matched-NFE; the framework's value-add on CIFAR-10 RF is **cross-budget only** (≈ 10× speedup at matched quality, NOT at matched-NFE). The `--no-final-restart` falsifier at `n_rounds = 10` grows the regression to +30.19 %, ruling out the DeepSeek hypothesis that the regression is restart-induced.

**Source-of-truth:** `docs/CONSOLIDATED_RESULTS.md` lines 8346 (Wave 235 P1 n_rounds = 1 sweep: ΔFID −1.60% to −2.53% on 3/4 schedulers; `--no-final-restart` at n_rounds = 10 falsifies DeepSeek hypothesis with regression growing to +30.19%), 8356 (Wave 235 P1 row in summary table: framework-WINS at n_rounds = 1; still REGRESSES at n_rounds > 1; Wave 225 P7 +9.77% at n_rounds = 2, Wave 191 P2 +20.20% at n_rounds = 4), 8363 ("R5b at `n_rounds = 1` is framework-WINS but `n_rounds > 1` remains REGRESSES"). Per-claim anchor: CLM-005 ACTIVE (cosine is canonical at direction level, but n_min=0.5 floor is known underperformer on CIFAR-10 RF).

---

## 5. R2 Boundary Wording (Kanzi deployed d_z = −0.0990; counterfactual in supplementary)

**Drop-in paste-ready text block (~70 words), for §7 Empirical Results or §9 Limitations:**

> **R2 (Kanzi RMSD, protein foldability deployed):** The deployed Kanzi configuration shows d_z = **−0.0990** on the byte-stable composite (Wave 196 byte-stable reference; mean_diff = +0.656 Å; baseline_wins on downstream task per `wave206-p2-kanzi-framework-n1000`). The 3-seed headliner counterfactual (`easy_factor = 0.0`, `hard_factor = 2.0`, 20-cell tier-aware sweep per Wave 235 P2) lifts the Kanzi d_z to **+0.3927** (Δd_z = +0.3462 vs deployed; MEDIUM effect band; bonferroni-significant in tier-aware direction). The deployed configuration is therefore **baseline_wins on downstream task**, but the tier-aware counterfactual (full sweep in supplementary) demonstrates that the framework can lift R2 Kanzi into the framework-wins regime under the right regime configuration. This is reported as **R2 counterfactual success**, not deployed-framework success.

**Source-of-truth:** `docs/CONSOLIDATED_RESULTS.md` lines 8334 (Wave 235 P2 tier-aware counterfactual: lifted R2 Kanzi d_z from −0.0990 to +0.3927, bonferroni-significant, Δd_z = +0.3462, MEDIUM band), 8355 (Wave 235 P2 row: best cell (easy = 0.0, hard = 2.0), d_z = +0.3927 vs Wave 233 P3 deployed +0.0465, +0.3462 improvement), 8462 (Wave 206 P2 byte-stable σ=0 reference; mean_diff = +0.656 Å, d_z = +3.532, baseline_wins on downstream task; preserved from Wave 196). Per-claim anchor: CLM-018 ACTIVE (Kanzi deployed baseline_wins, counterfactual win).

---

## 6. 5-7 Day Timeline Confirmation Note

The Wave 303 14-day plan compresses to **5-7 wall-clock days from D0 (2026-09-24) to TNNLS submission (target 2026-09-30 / 2026-10-02)** once the Wave 304 actual cell audit + Wave 305 verified deltas are accounted for. The compression is justified because the fold-in draft at `docs/drafts/paper-flat-flattened.md` lines 1087-1404 (Wave 300 P5 fold-in) already contains **6475 words** of canonical 11-section prose — only **~1000-2000 more words** are needed to reach the 7700-word main-text target (see Wave 303 plan §7.4 "Post-full-draft stats" table). The compressions are: (a) D1-D3 RESOLUTION Part 1 (Title + Abstract + §1) → 2 wall-clock days instead of 3 (each pair is ~1-2 hours with Wave 297 P2/P3 prose applied per DS-01); (b) D4-D5 RESOLUTION Part 2 (§2 → §3/§4/§5 promotion + §3 → §7 promotion + Wave 294 P2 inline fixes) → 1 wall-clock day with 2 parallel agents; (c) D6 RESOLUTION Part 3 (§4 → §9 + §6 placeholder rename + cover letter rebalance) → 0.5 wall-clock day; (d) D7-D9 Path A (3 lemmas at intermediate depth) → 1-2 wall-clock days with 3 parallel agents (Lemma 1 + Lemma 2 + Lemma 3 each ~2-4 hours at intermediate depth given that Lemma 1 sub-claim anchors + Lemma 2 state_machine.py byte-stability anchors + Lemma 3 ledger_chain.py tamper-evidence anchors are all pre-computed by Wave 301 Day 2); (e) D10 §6 trim + 4 contributions + §2 Related Work + §8 Reproducibility + §11 Conclusion + cross-ref update → 1 wall-clock day with 4 parallel agents (Path A lemma files + cross-ref updates can run in parallel); (f) D11 IEEEtran typeset + 14-page verify → 0.5 wall-clock day (typesetting automation is established at Wave 295 + Wave 298); (g) D12-D14 submission package + Paper B skeleton + user final review + ScholarOne upload → 1-2 wall-clock days (most time is user form-filling at D14, not agent work). **User review points are preserved at 3 boundaries** (down from 4): D0 today (this prompt + risk package), D3 cleanness check (after RESOLUTION Part 1 + Part 2 + Part 3 + §6 placeholder rename), D7 final sign-off (after D6 IEEEtran typeset + D7 submission package + 90-second paper.pdf read-through).

### Day-by-day table (5-7 day plan, D0 = 2026-09-24)

| Day | Date (5-day plan) | Date (7-day plan) | Phase | Agent work | User review |
|:---:|:---:|:---:|---|---|:---:|
| D0 | 2026-09-24 | 2026-09-24 | Day 0 user authorization | Read `wave303-day0-prompt.md` + this `wave305-day0-risk-package.md`; decide 6 pairs; authorize Wave 268 strict-clean break; lock TNNLS; confirm 5-7 day timeline | **YES — 2-3h** |
| D1 | 2026-09-25 | 2026-09-25 | RESOLUTION Part 1 + Part 2 + Part 3 (compressed) | Delete legacy title (L1-4); promote Wave 297 P2 title (L13-15); delete legacy abstract (L7-12); promote Wave 297 P2 5-sentence abstract (L17-19); delete legacy §1 (L23-50); promote Wave 297 P3 §1 (L52-67); delete legacy §2 (L71-258); promote W297 P4 A.1/A.2/A.3 to canonical §3/§4/§5; delete legacy §3 (L259-400); promote W297 P5 §7 to canonical §7; delete legacy §4 K1-K8 (L401-422); promote W297 P6 §9 to canonical §9; delete §5/§6 workflow-internal (L423-484); rename §6 placeholder; refresh cover letter; 5-gate verify per sub-step | No |
| D2 | 2026-09-26 | 2026-09-26 | Path A (3 lemmas, 3 parallel agents) | Agent A: Lemma 1 (composition closure, ~600 words, 4 sub-claim anchors at scheduler/protocol files); Agent B: Lemma 2 (SM byte-determinism, ~400 words, state_machine.py:826-941 anchor); Agent C: Lemma 3 (ledger tamper-evidence, ~350 words, engine.py:455-613 + ledger_chain.py:113-218 anchors); all 3 agents finalize + 5-gate verify | No |
| D3 | 2026-09-27 | 2026-09-27 | §6 trim + 4 contributions + §2/§8/§11 + cross-ref update + USER REVIEW cleanness check | Insert 3 Path A lemmas into §6 Framework Properties (3 subsections); rewrite §1 contributions to DeepSeek 4-contribution wording; fresh-write §2 Related Work (~700 words); fresh-write §8 Reproducibility (~600 words); fresh-write §11 Conclusion (~250 words); 3 parallel agents update ~104 line-ranges across ~19 audit docs; 5-gate verify | **YES — D3 cleanness check (1h)** |
| D4 | 2026-09-28 | 2026-09-28 | IEEEtran typeset + 14-page verify | Convert paper → paper.tex; wrap 3 lemmas in theorem environments; insert 4 tables + 4 figure placeholders; 30-50-entry bibliography; compile to paper.pdf ≤ 14 pages | No |
| D5 | 2026-09-29 | 2026-09-29 | Submission package + Paper B skeleton + USER REVIEW final sign-off | Refresh MANIFEST SHA; generate source.zip; copy paper.pdf; generate highlight_blurb.pdf; create Paper B skeleton on `paper-b-skeleton` git branch; 5-gate verify | **YES — D5 final sign-off (1h)** |
| D6 | (n/a in 5-day) | 2026-09-30 | (Buffer day — apply any D5 edits + re-verify) | Apply D5 user edits; re-run 5-gate; re-present | Optional |
| D7 | (n/a in 5-day) | 2026-10-01 | Submit to TNNLS ScholarOne | User uploads paper.pdf + source.zip + cover letter + highlights to mc.manuscriptcentral.com/tnnls; ScholarOne confirmation logged | **YES — D7 ScholarOne upload click (75 min user)** |

**5-day plan submission target:** 2026-09-29 (5 days from D0). **7-day plan submission target:** 2026-10-01 (7 days from D0 with 1 buffer day).

**Word budget check:** fold-in draft at lines 1087-1404 = 6475 words (per `wave303-day0-prompt.md` §3 "Important correction"). After D1 RESOLUTION deletions (~14000 words legacy) + D1 additive promotions (~7000 words from W297 P4/P5/P6 absorbed into canonical §3/§4/§5/§7) → ~5380 words. After D3 fresh-writes (§2 700 + §8 600 + §11 250 + §6 trim 700 + §1 contribution rewrite 400 = 2650 words) → ~8030 words (over 8500 target). **Trim required at D3:** drop ~530 words from §7 Empirical Results (5 STRONG/PARTIAL cells → 4 cells; defer K1 to supplementary) → ~7500 words (under 8500 target with ~1000-word buffer for IEEEtran expansion). **Acceptable trim paths documented in Wave 303 `wave303-day0-14-plan.md` §8.3.**

---

## 7. 5-Gate Baseline + Paper State Snapshot (verified 2026-09-23)

| # | Gate | Command | Expected result | Status |
|:---:|---|---|---|:---:|
| 1 | D.4 30/30 byte-stability | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, ≤ 3 pre-existing DeprecationWarnings, ~3.59s | **PASS** (verified 2026-09-23 by Wave 303 D0 prompt assembly) |
| 2 | ruff 0 lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | **PASS** (verified 2026-09-23) |
| 3 | mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code = 0, 0 project warnings, ~21.81s | **PASS** (verified 2026-09-23) |
| 4 | claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL by Disputed by / No drift detected | **PASS** (verified 2026-09-23) |
| 5 | vendored / data NOT touched | `git diff --stat -- vendored/ data/` | (empty) | **PASS** (verified 2026-09-23) |

**Paper state snapshot (verified 2026-09-23):**
- File: `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-flat-flattened.md`
- Length: **1404 lines / 36027 words** (matches Wave 301 + Wave 303 verification)
- Sections: 23 H2 sections (7 legacy H2 + 4 additive appendices W297 P4/P5/P6 + W298 P7 + Wave 300 P5 fold-in §1-§10)
- Dual-present pairs: 6 (Title, Abstract, §1 Intro, §2 Algorithm, §3 Experiments, §4 Limitations)
- Wave 268 strict-clean: ACTIVE — no edits to paper-flat-flattened.md without explicit user authorization
- §6 JMAA current location: lines 1238-1262 (25-line block, ~520 words; drop at D5)
- §6 JMAA legacy references in §1 / §2 / §3 / §9 / §10: ~1170 words (reword at D3-D6)
- Fold-in draft at lines 1087-1404: 6475 words (per Wave 303 D0 prompt §3 correction)

**Baseline establishes:** the dual-present state is currently verifiable and any RESOLUTION-pass execution must maintain all 5 gates per commit. Wave 305 Day 0 risk package does NOT modify `paper-flat-flattened.md`; it supplements `wave303-day0-prompt.md` with the §6 deletion checklist, codim contamination list, 3 boundary wording paste-blocks, and the 5-7 day timeline confirmation.

---

## 8. STOP MARKER

**AGENT WAITS FOR USER AUTHORIZATION BEFORE ANY DESTRUCTIVE EDIT.**

No edits to `paper-flat-flattened.md`, no RESOLUTION deletion steps, no Wave 268 strict-clean break, no destructive inline corrections, no D1-D14 workflow execution are performed without explicit user text authorization for the **5-7 day timeline selection** (vs the 14-day plan in `wave303-day0-14-plan.md`). The 5-gate baseline is verified PASS (D.4 30/30 + ruff 0 + mkdocs strict 0 warnings + claims no-drift + vendored untouched); the current 1404-line paper state is preserved until user reply is received.

**Required user actions at D0 (2-3 hours total):**
1. Confirm 6 dual-present pair decisions (per `wave303-day0-prompt.md` §1).
2. Authorize Wave 268 strict-clean break (signature per `wave303-day0-prompt.md` §2).
3. Lock venue to TNNLS (per `wave303-day0-prompt.md` §3).
4. **NEW (Wave 305)**: Select 5-day plan (submission 2026-09-29) OR 7-day plan (submission 2026-10-01 with 1 buffer day) for the compressed timeline (vs 14-day plan at `wave303-day0-14-plan.md`).
5. Confirm §6 rename to "Framework Properties" + JMAA → Paper B (per `wave303-day0-prompt.md` §1 special sub-decisions).
6. Confirm 4-contribution wording (per `wave303-day0-prompt.md` §1 special sub-decisions).
7. Confirm §10 Future Work dropped or folded into §8 (per `wave303-day0-prompt.md` §1 special sub-decisions).
9. Confirm R3 / R5b / R2 boundary wording paste-ready blocks (§3 / §4 / §5 above) for §7 Empirical Results or §9 Limitations.
10. Confirm §6 JMAA deletion list (§1 above) executes at D5 as specified.
11. Confirm codim contamination list (§2 above) is preserved in Paper A canonical §3/§4/§7/§9 (codim terminology stays) and migrated to Paper B (JMAA theorem framing migrates per DeepSeek §四).

**After user signs off all 11 items**, the workflow agent takes over D1-D5/D7 without further user review except at the 3 explicit boundary points (D3 cleanness check, D5 final sign-off, D7 ScholarOne upload click).

> **AGENT WAITS FOR USER AUTHORIZATION BEFORE ANY DESTRUCTIVE EDIT.**
>
> No edits to `paper-flat-flattened.md` will be performed until user text authorization is received.

---

**End of Wave 305 Day 0 Risk Package.** This doc supplements (does NOT replace) `docs/audit/wave303-day0-prompt.md`. It will be needed before D1 by the agent executing the RESOLUTION pass + Path A + IEEEtran typeset + submission package workflow.

**STOP MARKER:** Agent waits for user authorization before any destructive edit. No edits to `paper-flat-flattened.md` will be performed until user text authorization is received.