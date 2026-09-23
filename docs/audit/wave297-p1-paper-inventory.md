# Wave 297 P1 — Paper Structure Inventory for JMAA Demotion

**Date:** 2026-09-23
**Branch:** main
**Prior docs:** `docs/audit/wave296-p1-architecture.md`, `docs/audit/wave294-final.md`, `docs/audit/wave292-p1-pipeline-inventory.md`, `docs/audit/jmaa-theory-applications.md`, `docs/audit/wave294-p1-re-inventory.md`
**Source paper:** `docs/drafts/paper-flat-flattened.md` (445 lines, post-Wave-294)
**Purpose:** Inventory the current paper structure to identify sections that need re-anchoring. Per the user directive ("我们把 flow matching 这类模型的推理框架重构了并且确实在显著性分析上是有效果的"), JMAA Theorem 1 should be **demoted from main contribution to theoretical enrichment**, and the **re-inference framework architecture** (three-domain split, typed four-port contract, scheduler taxonomy, scheduler protocols, adapter protocol, paper-quantity opt-in) should be elevated to the main contribution.

---

## 0. TL;DR

- **Total sections inventoried:** 19 (title + abstract + §1 + §2 with 8 subsections + §3 with 6 subsections + §4 with 8 K-dimensions + §5 + §5.5 + §6).
- **JMAA-prominent sections (HIGH index):** 6 — Title, Abstract, §1 Introduction lead, §2.1 paper-quantity-driven controllers, §2.6 calibration helper, §2.8 §MS 16-site inventory.
- **Framework-prominent sections (re-inference architecture as primary):** 6 — §1 Introduction (paragraph 3 "FlowA closes this gap"), §3.3 headline results, §3.4 five-arm ablation, §4 K4 port coupling, §5.5 efficiency narrative.
- **Empirical-prominent sections:** 7 — §3.1 setup, §3.2 stats, §3.3 results, §3.4 ablation, §3.5 load-bearing, §3.6 boundary, §5.5 efficiency.

**Re-anchoring priority** (highest first):

1. **Title** — currently names JMAA Theorem 1 quantities in the title; should name the **re-inference framework architecture**.
2. **Abstract** — leads with theorem-driven bound + four quantities; should lead with **training-free re-inference framework + cross-budget compression**.
3. **§1 Introduction, paragraph 1** — currently positions JMAA theorem as the headline contribution; should re-anchor as **framework architecture primary, theorem as convergence-theory companion**.
4. **§2.1 paper-quantity-driven controllers** — currently titled "the controllers the framework was DESIGNED around"; should be reframed as the **theory-driven controller sub-family** within a larger framework.
5. **§2.8 §MS 16-site inventory** — currently enumerates 16 JMAA Theorem 1 application sites; should be reframed as **theory-enrichment sites within the framework's algorithm layer**.
6. **§1 paragraph 3** — currently ends the introduction with the four-port typed contract as one sentence after the theorem statement; should be **elevated to a structural overview before the theorem restatement**.

---

## 1. Section-by-section inventory

| # | Section | Lines | Current positioning | JMAA prominence | Framework prominence | Empirical prominence | Re-anchor priority |
|---:|---|---:|---|:---:|:---:|:---:|:---:|
| 1 | **Title** — *FlowA: Paper-Quantity-Driven Re-Inference for Frozen Flow Matching Checkpoints* | 1 | JMAA-centric (paper-quantity in title) | **HIGH** | medium | low | **P0** (highest) |
| 2 | **Abstract** | 5–7 | JMAA-centric (theorem bound + closed forms + four quantities as primary) | **HIGH** | medium | medium | **P0** |
| 3 | **§1 Introduction, paragraph 1** (FM + frozen ckpt + gap statement) | 13 | Framework-centric (gap structural, no convergence-theory witness) | medium | **HIGH** | low | medium |
| 4 | **§1 Introduction, paragraph 2** (prior-work taxonomy: solver / trajectory / re-inference α-blend) | 15 | Framework-centric (positions FlowA relative to 3 disjoint layers) | low | **HIGH** | low | medium |
| 5 | **§1 Introduction, paragraph 3** (FlowA closes the gap + Theorem 1 + four quantities + four-port contract) | 17 | JMAA-centric (theorem inline + four closed forms + secondary four-port sentence) | **HIGH** | medium (one sentence) | low | **P0** (this is the load-bearing intro paragraph) |
| 6 | **§1 Introduction, paragraph 4** (validation summary) | 19 | Empirical-centric (six R-cells + 2.5–10× headline) | low | medium | **HIGH** | low (already narrative) |
| 7 | **§1 Introduction, contributions (i)–(vi)** | 23–28 | JMAA-centric (contribution (i) cites Bolley–Guilin–Villani concentration bound; (ii) names the paper-quantity scheduler) | **HIGH** (i, ii) | medium (i, vi) | medium (iii, iv, v) | **P1** |
| 8 | **§2 Algorithm preamble + scheduler taxonomy (paper §2)** | 32–36 | Mixed: framework-centric (4-port contract, scheduler taxonomy, 19 families) + JMAA-centric (paper-quantity organisation) | medium | **HIGH** | low | **P1** |
| 9 | **§2.1 Paper-quantity-driven controllers** (5 families) | 38–56 | JMAA-centric (the framework's "primary contribution" per the preamble) | **HIGH** | medium (registry pattern) | low | **P0** (re-anchor as sub-family, not as primary) |
| 10 | **§2.2 Cosine ramp + simple baselines** (6 families) | 58–76 | Empirical-centric (13/13 R-cells use cosine; CLM-018 ablation history) | medium (cosine IS paper-Lemma-2 closed form, per §2.2 NOTE) | low | medium | low |
| 11 | **§2.3 Composite / sequential schedulers** (2 families) | 78–87 | Framework-centric (SchedulerProtocol composition) | low | **HIGH** | low | low |
| 12 | **§2.4 NFE-aware and trajectory-aware schedulers** (2 families) | 89–96 | Mixed: framework-centric (NFE budget) + JMAA-adjacent (A_g via FreeTraj wrapper) | low | **HIGH** | low | low |
| 13 | **§2.5 Related-work and ablation extras** (4 families) | 98–109 | Framework-centric (registry, related-work baselines) | low | medium | low | low |
| 14 | **§2.6 Paper-quantity-driven calibration helper** (`paper_quantity_driven_beta`) | 111–113 | JMAA-centric (re-derives A_g, B_g, C_g, e_rho at call time) | **HIGH** | low | low | **P1** (small but JMAA-centric) |
| 15 | **§2.7 Discussion: scope of paper-quantity controllers + historical cosine usage** | 115–131 | Mixed: JMAA-centric (5 paper-grounded controllers) + empirical-centric (13/13 cosine history + W281 plan) | medium | medium | medium (W290/291 verdict) | medium (re-anchor as framework-architecture context) |
| 16 | **§2.8 §MS.theorem1_data_pipeline_entry_points — 16 sites** | 133–157 | JMAA-centric (enumeration of 16 JMAA Theorem 1 sites with data-pipeline entry points) | **HIGH** | medium (registry mapping) | low | **P0** (largest JMAA-prominent block in §2; re-anchor as theory-enrichment inventory) |
| 17 | **§2.9 §MS.config_genealogy — per-cell provenance** | 159–184 | Empirical-centric (13 headline cells with full provenance) | medium (sites active / 16 column) | low | **HIGH** | low |
| 18 | **§2.10 §MS.claim_audit — paper §MS cross-check** | 186–216 | JMAA-centric (47-claim audit of §2; 6 mismatches + 3 gaps) | **HIGH** (paper vs code cross-check) | medium | low | **P1** (re-anchor as paper-architecture audit, not JMAA audit) |
| 19 | **§3.1 Experimental setup** (6 R-cells + head-to-head) | 223–245 | Framework-centric (FlowA architecture instantiated across adapters) | low | **HIGH** (architecture instantiated) | **HIGH** | low |
| 20 | **§3.2 Statistical methodology** (twelve-column audit row, Bonferroni families, cluster-robust) | 247–270 | Empirical-centric | low | low | **HIGH** | low |
| 21 | **§3.3 Headline results (Table 3.2)** | 272–301 | Empirical-centric (12 cells × 13 columns; cross-budget + per-tier framing + cross-adapter replication) | low | medium | **HIGH** | low (results are framework-architecture-validated, no re-anchor needed) |
| 22 | **§3.4 Five-arm ablation (Table 3.3)** | 303–325 | Mixed: empirical-centric (cumulative-add A0–A4) + JMAA-centric (A2 = CodimensionSheetScheduler, A3 = BoundedMergeOperator, A4 = EvidenceDrivenScheduler; selection_ratio axis load-bearing) | medium | medium | **HIGH** | medium (re-anchor: ablation isolates the framework's value-add, not the theorem's value-add) |
| 23 | **§3.5 Why paper quantities are load-bearing on selection_ratio** | 328–333 | JMAA-centric (load-bearing test as theorem validation) | **HIGH** (entirely about theorem 1 stabilisation) | medium | medium | **P1** (re-anchor as framework-architecture observation: regulariser on cosine ramp's perturbation) |
| 24 | **§3.6 NFE-matched boundary (Figure 4)** | 335–355 | Empirical-centric (3 regimes; head-to-head Table B) | low | medium | **HIGH** | low |
| 25 | **§4 Limitations** (K1–K8) | 362–381 | K1 Kanzi framework-scope; K2 NFE-regime; K3 stratification; K4 port coupling; K5 cluster; K6 freq/multi-modal; K7 multi-round vs restart-blend; K8 compute-budget | mixed: K1, K4 framework-centric; K5 empirical-centric; rest mixed | K1, K4 **HIGH**; K2, K3, K7 medium | K5, K8 **HIGH** | medium (each K needs individual re-anchor; K1 + K4 framework-prominent, K3 + K5 + K7 empirical-prominent) |
| 26 | **§5 Flattening Checklist** | 384–400 | Meta (checklist) | low | low | low | low |
| 27 | **§5.5 Efficiency narrative: wall-clock, FLOPs, matched-compute** | 401–422 | Empirical-centric (per-cell efficiency table; reviewer-question answered) | low (paper quantities mentioned as overhead) | medium (engineering roadmap: cache scheduler state, parallelise paper-quantity, torch.compile) | **HIGH** | medium (re-anchor: efficiency narrative IS framework architecture; paper quantities are a sub-component) |
| 28 | **§6 Reviewer-Facing Static Reference Labels** | 425–446 | Meta (R-level cells, Tier-3 checkpoints, D.4) | low | low | low | low |

---

## 2. JMAA-prominent sections (HIGH index)

The following 6 sections are JMAA-centric in current framing and require re-anchoring:

| # | Section | Current JMAA content | Required re-anchoring |
|---:|---|---|---|
| 1 | **Title** (line 1) | "Paper-Quantity-Driven" in title | Reframe title to **framework-centric**; e.g. *FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints* (drop "Paper-Quantity-Driven"). |
| 2 | **Abstract** (lines 5–7) | First sentence leads with "derives a closed-form upper bound on the bounded-Lipschitz distance … through four paper quantities $(A_g, B_g, C_g, e_\rho)$" | Reorder so the **framework architecture** (three-domain split + four-port contract + scheduler taxonomy + adapter protocol + scheduler protocols) leads, and the **theorem bound** is moved to the "convergence-theory companion" sentence near the end. |
| 3 | **§1 paragraph 3** (line 17) | "FlowA closes this gap through a single theorem-driven interface. We state Theorem 1 within this paper …" → restates theorem + four quantities + secondary four-port contract | Restructure: **first** describe the framework architecture (three-domain split + four-port contract), **then** state Theorem 1 as convergence-theory enrichment that bounds the framework's sampling distribution. |
| 4 | **§2.1 Paper-quantity-driven controllers** (lines 38–56) | Title + preamble: "the framework's primary contribution" + "the controllers the framework was DESIGNED around" | Reframe: §2.1 is the **theory-driven controller sub-family** (5 of 19 families); §2.2–§2.5 are the **empirical baselines** + **framework-architecture extras**; the framework as a whole is the primary contribution. |
| 5 | **§2.6 Calibration helper** (lines 111–113) | Entirely about `paper_quantity_driven_beta()` consuming A_g, B_g, C_g, e_rho at call time | Reframe as **theory-enrichment helper** for protein-reconstruction use cases (a sub-component of the framework's calibration layer). |
| 6 | **§2.8 §MS 16-site inventory** (lines 133–157) | Entirely enumerates 16 JMAA Theorem 1 sites with data-pipeline entry points | Reframe as **theory-enrichment inventory**: list the 16 sites as places where JMAA Theorem 1 quantities enter the framework's algorithm layer; the framework architecture (sites 1–8 algorithm-layer + sites 9–16 evaluator-layer) is the primary, the theorem is the enrichment. |

---

## 3. Framework-prominent sections

The following 4 sections are framework-architecture-prominent and should be **elevated** (not demoted):

| # | Section | Framework content | Required elevation |
|---:|---|---|---|
| 1 | **§1 paragraph 2** (line 15) | Three disjoint layers of prior work (solver / trajectory / re-inference α-blend); FlowA occupies a fourth | Elevate to **sub-frame schematic** in the introduction: the framework's three-domain split + four-port contract is the structural position that no prior work occupies. |
| 2 | **§2 §2 Algorithm preamble** (lines 32–36) | 19 families partitioned into 5 groups; four-port control surface; SchedulerProtocol conformance | Elevate to **architectural overview** of the framework: the 5 groups partition into **framework-architecture families** (groups iii, iv) + **theory-enrichment families** (group i) + **baseline families** (groups ii, v). |
| 3 | **§4 K4 Scheduler-port coupling** (line 372) | Three scheduler implementations as a coupled triplet | Already framework-prominent; **lift this K4 to the abstract's last sentence** as the framework's structural uniqueness claim. |
| 4 | **§5.5 Efficiency narrative** (lines 401–422) | Per-cell efficiency table + reviewer-question answered | Already framework-architecture-prominent; **add a sentence** noting the framework's value-add lives on cross-budget + protein hard tier, and the theorem quantities are a sub-component of the overhead. |

---

## 4. Empirical-prominent sections

The following 7 sections are empirically-prominent and require no re-anchoring (results are framework-architecture-validated, not theorem-validated):

| # | Section | Empirical content |
|---:|---|---|
| 1 | **§3.1 Experimental setup** | 6 R-cells + head-to-head |
| 2 | **§3.2 Statistical methodology** | Twelve-column audit row + 4 Bonferroni families |
| 3 | **§3.3 Headline results (Table 3.2)** | 12 cells × 13 columns; cross-budget + per-tier + cross-adapter |
| 4 | **§3.4 Five-arm ablation (Table 3.3)** | A0–A4 cumulative-add on 2D RF + CIFAR-10 RF + LineageFlow |
| 5 | **§3.5 Why paper quantities are load-bearing on selection_ratio** | Load-bearing test result (Kanzi L2 dampening) — **note**: this is JMAA-prominent content (re-anchor in §3.5) |
| 6 | **§3.6 NFE-matched boundary (Figure 4)** | 3 regimes + head-to-head Table B |
| 7 | **§5.5 Efficiency narrative** | Per-cell efficiency table + reviewer question |

**Note:** §3.5 is empirical in content but JMAA-prominent in framing. Re-anchor §3.5's heading to "Why the framework's value-add is joint cosine + theory enrichment" (drop "paper quantities" from the heading).

---

## 5. Re-anchoring priority list

### P0 (highest priority — must re-anchor for §1 + §2 consistency)

1. **Title (line 1)** — reframe to framework-architecture-primary.
2. **Abstract (lines 5–7)** — reorder so framework architecture is the primary, theorem is the convergence-theory companion.
3. **§1 paragraph 3 (line 17)** — restructure: framework architecture first, theorem enrichment second.
4. **§2.1 Paper-quantity-driven controllers (lines 38–56)** — reframe as theory-driven controller sub-family.
5. **§2.8 §MS 16-site inventory (lines 133–157)** — reframe as theory-enrichment inventory.

### P1 (high priority — secondary framing)

6. **§2 preamble (lines 32–36)** — reframe 5-group partition as framework-architecture-primary + theory-enrichment-secondary.
7. **§2.6 Calibration helper (lines 111–113)** — reframe as theory-enrichment helper.
8. **§2.10 §MS.claim_audit (lines 186–216)** — reframe as paper-architecture audit (not JMAA audit).
9. **§3.5 Why paper quantities are load-bearing (lines 328–333)** — reframe heading as framework-architecture observation.
10. **§1 contributions (i)–(vi) (lines 23–28)** — contributions (i) and (ii) cite the theorem; should cite the framework architecture.

### P2 (medium priority — content review, no structural change)

11. **§2.7 Discussion (lines 115–131)** — reframe scope statement: framework controls 5 theory-driven controllers, the framework as a whole is the primary contribution.
12. **§4 K4 Scheduler-port coupling (line 372)** — already framework-prominent; lift the structural uniqueness claim.
13. **§5.5 Efficiency narrative (lines 401–422)** — add a sentence noting framework value-add + theorem quantities as sub-component.

### P3 (low priority — no change)

14. **§1 paragraph 1, paragraph 2, paragraph 4** — already framework-prominent.
15. **§2.2, §2.3, §2.4, §2.5** — already framework-architecture-secondary; no re-anchor.
16. **§2.9 §MS.config_genealogy** — already empirical-prominent; the "sites active / 16" column is a JMAA reference but the section is empirical.
17. **§3.1, §3.2, §3.3, §3.4, §3.6** — already empirical-prominent.
18. **§4 K1, K2, K3, K5, K6, K7, K8** — individual re-anchor in their respective P2 entries.
19. **§5 Flattening Checklist, §6 Static Reference Labels** — meta; no re-anchor.

---

## 6. Invariants preserved

- **D.4 30/30:** unchanged. No code edited; this is a read-only inventory.
- **Claims no drift:** unchanged. The cosine baseline R-cell FID achievement, the cross-budget 2.5–10× NFE compression, and the protein hard-tier pLDDT win are all preserved.
- **ruff 0:** unchanged. No `.py` file modified.
- **mkdocs 0 warnings:** unchanged. `docs/audit/` is `not_in_nav` per `mkdocs.yml:239` (W292 P1 §6 invariant).
- **vendored NOT touched:** unchanged. No edits under `vendored/`, `.venvs/`, `data/`.
- **framework source minimal change:** unchanged. This is a structural inventory, not a code change.

---

## 7. Honest summary

The Wave 297 P1 inventory identifies 19 sections in `docs/drafts/paper-flat-flattened.md`, of which **6 are JMAA-prominent** (Title, Abstract, §1 paragraph 3, §2.1, §2.6, §2.8), **6 are framework-prominent** (§1 paragraph 2, §2 preamble, §4 K4, §5.5, etc.), and **7 are empirical-prominent** (§3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §5.5).

Per the user directive ("我们把 flow matching 这类模型的推理框架重构了并且确实在显著性分析上是有效果的"), JMAA Theorem 1 should be demoted from main contribution to theoretical enrichment, and the re-inference framework architecture (three-domain split + four-port typed contract + scheduler taxonomy + adapter protocol) should be elevated to the main contribution.

The **5 P0 sections** that require immediate re-anchoring are: Title, Abstract, §1 paragraph 3, §2.1 paper-quantity-driven controllers, §2.8 §MS 16-site inventory. These sections currently lead with theorem-driven framing; they should be reframed to lead with framework-architecture framing and treat the theorem as convergence-theory enrichment.

The **5 P1 sections** require secondary framing updates: §2 preamble, §2.6 calibration helper, §2.10 claim audit, §3.5 load-bearing discussion, §1 contributions (i)–(vi).

The **remaining 9 sections** require no re-anchoring (already empirical-prominent or already framework-prominent).

This is a **structural inventory only** — no paper edits applied. The Wave 297 P2+ waves will apply the re-anchoring on a per-section basis, per the Wave 268 strict-clean additive-only directive.

---

## 8. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave297-p1-paper-inventory.md` (this file)
- **prior docs cited:** wave296-p1-architecture.md, wave294-final.md, wave292-p1-pipeline-inventory.md, jmaa-theory-applications.md, wave294-p1-re-inventory.md
- **paper sections inventoried:** 19 (Title, Abstract, §1.1–§1.5, §2.0–§2.10, §3.1–§3.6, §4.1–§4.8, §5.0, §5.5, §6)
- **re-anchor priority count:** 5 P0 + 5 P1 + 3 P2 + 9 P3 = 22 (with overlap)
- **vendored NOT touched:** verified by `git diff --stat vendored/` (no diff)