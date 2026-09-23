# Wave 300 P3 — RESOLUTION Pass Plan: Eliminate Dual-Present Legacy-vs-Additive State in `paper-flat-flattened.md`

**Date:** 2026-09-23
**Mode:** READ-ONLY PLANNING (no edits to `paper-flat-flattened.md` per Wave 268 strict-clean)
**Author:** Wave 300 P3 planning agent (subagent of `wave32-gap-plan-execute`)
**Source-of-truth for canonical structure:** `docs/audit/wave299-paper-a-outline.md` §3 (11-section target)
**Source-of-truth for legacy text:** `docs/drafts/paper-flat-flattened.md` (1083 lines, dual-present state)
**Source-of-truth for §1 prose:** `docs/audit/wave297-p3-intro-rewritten.md` (Wave 297 P3 §1 prose applied verbatim)
**Source-of-truth for cross-references:** `docs/audit/wave299-final-verification.md` (Wave 299 P5 dual-present fingerprint)

---

## 0. TL;DR

The paper `docs/drafts/paper-flat-flattened.md` is currently in a **dual-present state** (1083 lines, +440 additive Wave 297 P3-P6 lines + +239 Wave 298 P7 lines appended on top of the legacy 19-section structure). The Wave 297 P2 paper design at `docs/audit/wave297-p2-paper-design.md` §1 specifies an **11-section canonical target structure** (1.5+1.0+2.5+1.5+1.0+1.5+3.0+1.0+0.5+0.5 pages = 14.0 pages, TNNLS-compatible). The Wave 297 P3-P6 additive Wave 298 P7 appendices implement the new sections as **appendices** rather than as canonical content per the Wave 268 strict-clean rule.

This plan maps the 6 dual-present topic pairs and 4 net-new sections to **canonical-version decisions** (legacy → delete, additive → promote, or merge), and produces a deletion-count + cross-reference-update manifest. **No edits to `paper-flat-flattened.md` are performed in this pass** — the Wave 268 strict-clean rule requires explicit user authorization before any deletion. This document is the canonical source-of-truth for the eventual RESOLUTION execution pass.

---

## 1. Section-by-Section "Before/After" Plan

### Topic 1: TITLE (lines 1-4 legacy + lines 13-15 additive)

| Aspect | Legacy | Additive | Recommended canonical |
|---|---|---|---|
| **Lines** | 1-4 (1-line title + 4-line RE-ANCHOR note) | 13-15 (subsection "### New title (Wave 297 P2 proposal)") | Single title at line 1 |
| **Content** | "FlowA: Paper-Quantity-Driven Re-Inference for Frozen Flow Matching Checkpoints" + 4-line Wave 297 P3 anchor note | "FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints" | **Adopt additive** ("FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints.") |
| **Lines to delete** | 1 (legacy title) + 3 (RE-ANCHOR NOTE) | 0 (promote to canonical) | **4 lines to delete** |
| **Lines to preserve** | 0 | 3 (the new title block) | **3 lines to preserve** |
| **Net delta** | — | — | **−4 lines (1 title block collapse)** |

**Decision rationale:** Wave 297 P3 §2.1 proposes the new title; Wave 298 P6 §A.1 re-anchors to "framework reconstruction + empirical significance" as primary. The additive title is the canonical form.

### Topic 2: ABSTRACT (lines 7-12 legacy + lines 17-19 additive)

| Aspect | Legacy | Additive | Recommended canonical |
|---|---|---|---|
| **Lines** | 7-12 (abstract + RE-ANCHOR note) | 17-19 (5-sentence abstract) | Single 5-sentence abstract at the Abstract heading |
| **Content** | 9-line legacy abstract (theorem-driven framing) + 2-line Wave 297 P3 RE-ANCHOR NOTE | 5-sentence re-anchored abstract (framework-reconstruction primary, JMAA companion) | **Adopt additive** (5-sentence per Wave 209 P7 envelope) |
| **Lines to delete** | 9 (legacy abstract) + 2 (RE-ANCHOR NOTE) | 0 (promote to canonical) | **11 lines to delete** |
| **Lines to preserve** | 0 | 1 (the new 5-sentence abstract) | **1 line to preserve** (the 5 sentences span 1 paragraph) |
| **Net delta** | — | — | **−10 lines (1 abstract collapse)** |

**Decision rationale:** Wave 297 P3 §2.2 explicitly designates the 5-sentence additive abstract as the canonical form. CLM-018/040 evidence confirms framework-not-theory verdict; the additive abstract correctly demotes JMAA Theorem 1 to one theoretical companion lens.

### Topic 3: §1 INTRODUCTION (lines 23-67 legacy + lines 52-67 additive; lines 41-50 contributions legacy + lines 62-67 contributions additive)

| Aspect | Legacy | Additive | Recommended canonical |
|---|---|---|---|
| **Lines** | 23-50 (4-paragraph legacy intro + 6-item contributions list) | 52-67 (new §1 prose + 4-item contributions list) | Single §1 with framework-reconstruction framing |
| **Content** | 4-paragraph theorem-first opening (Lipman/RF/Liu, FlowA-as-fourth-layer, theorem-driven interface, 6-cell validation) + 6-item contributions | 4-paragraph framework-reconstruction opening + 4-item contributions (i-iv) | **Adopt additive prose verbatim** (Wave 297 P3 §1 prose applied verbatim per DS-01) |
| **Lines to delete** | 27 (legacy intro) + 9 (legacy contributions + 6 sub-bullets) = ~44 lines | 0 (promote to canonical) | **44 lines to delete** (legacy §1 ¶1-4 + legacy contributions list + Wave 297 P3 RE-ANCHOR NOTE blocks) |
| **Lines to preserve** | 0 | 15 (new intro prose) + 6 (new contributions) = 21 lines | **21 lines to preserve** |
| **Net delta** | — | — | **−23 lines (§1 collapse)** |

**Decision rationale:** Per Wave 297 P3 §4.1 + DS-07/DS-08, the framework-reconstruction framing is the primary lens; theorem-first demoted to one theoretical companion. The additive 4-item contributions list is shorter, more accurate, and aligned with Wave 297 P2 §4.1 design.

### Topic 4: §2 ALGORITHM (lines 71-258 legacy; lines 488-620 additive as Appendix A.1-A.4)

| Aspect | Legacy | Additive | Recommended canonical |
|---|---|---|---|
| **Lines** | 71-258 (10 sub-sections, 5 tables, ~30 cross-refs) | 488-620 (Appendix A.1-A.4, 4 sub-sections) | Single §2 with 4 sub-sections (Framework + Scheduler Family + Adapter Protocol) |
| **Content** | §2.1-§2.10 with 5 tables (Table 2.1-2.5, Table 2.8-2.10) + §MS.theorem1_data_pipeline_entry_points + §MS.config_genealogy + §MS.claim_audit | §3 Framework + §4 Scheduler Family + §5 Adapter Protocol + Appendix A.4 (relocated families) | **Adopt additive as §3 (Framework) + §4 (Scheduler Family) + §5 (Adapter Protocol) per Wave 297 P2 11-section structure** |
| **Lines to delete** | ~190 (legacy §2.1-§2.10, leaving only the canonical §3/§4/§5 prose from additive) | 0 (promote to canonical) | **~190 lines to delete** (legacy §2.1-§2.10 tables + discussion + audit sub-sections) |
| **Lines to preserve** | 0 | ~135 (canonical §3/§4/§5 prose from additive) | **~135 lines to preserve** |
| **Net delta** | — | — | **−55 lines (§2 collapse)** |

**Decision rationale:** Wave 297 P2 §1 + Wave 297 P4 designates §3/§4/§5 as the primary sections (NOT §2 Algorithm). The legacy §2.1-§2.10 tables are relocated into the canonical §4 Scheduler Family (which is Appendix A.2 in additive). The §MS.claim_audit (legacy lines 225-258) is removed from the canonical paper and kept only in the audit doc trail. The §MS.config_genealogy (legacy lines 198-223) and §MS.theorem1_data_pipeline_entry_points (legacy lines 171-196) are subsumed by the §9 Limitations + §10 Future Work additive content from Wave 297 P6.

**Special sub-decision: §2.2 cosine closed-form sign (Wave 294 P2 M-HIGH-1).** Per `docs/audit/wave294-p2-medium-fixed.md` and the Wave 293 fix, the legacy Table 2.2 has `(1 − cos(π r / (L − 1)))` (anneals UP `n_min → n_max`) but the code at `adaptive_reflow/schedule/cosine.py:227` is `(1 + cos(π · u_r)) / 2` (anneals DOWN `n_max → n_min`). The sign must be FLIPPED in the canonical §2.2 row during the §2 fold-in pass. **This is the 1 HIGH-severity mismatch from DS-01.**

### Topic 5: §3 EXPERIMENTS (lines 259-400 legacy; lines 624-755 additive as Appendix W297 P5 §7)

| Aspect | Legacy | Additive | Recommended canonical |
|---|---|---|---|
| **Lines** | 259-400 (6 sub-sections, Table 3.1-3.4, Figure 4 narrative) | 624-755 (Appendix W297 P5 §7.1-§7.11) | Single §7 Empirical Results (11-cell systematic-evidence framing) |
| **Content** | §3.1-§3.6 (experimental setup + statistical methodology + Table 3.2 12-column + 5-arm ablation + Figure 4 + NFE boundary + head-to-head) | §7.1-§7.11 (systematic-evidence framing with 6-column status table + statistical methodology block + framework-not-theory verdict) | **Adopt additive as §7 Empirical Results (Wave 297 P2 §1 + §4.7)** |
| **Lines to delete** | ~140 (legacy §3.1-§3.6 + Table 3.1-3.4 + Figure 4 + head-to-head) | 0 (promote to canonical) | **~140 lines to delete** (legacy §3.1-§3.6 content) |
| **Lines to preserve** | 0 | ~130 (canonical §7 prose from additive) | **~130 lines to preserve** |
| **Net delta** | — | — | **−10 lines (§3 collapse)** |

**Decision rationale:** Per Wave 297 P5 §7.1 + DS-07, the 6-column systematic-evidence status table (STRONG/PARTIAL/UNDERPOWERED/BLOCKED/REGRESSES rubric) is the canonical reviewer-facing empirical contribution. The legacy 12-column audit-row format is preserved only in the audit doc trail. The legacy §3.4 5-arm ablation is preserved verbatim and folded into the additive §7.3 statistical methodology block.

### Topic 6: §4 LIMITATIONS (lines 401-422 legacy; lines 758-841 additive as Appendix W297 P6 §9 + §10)

| Aspect | Legacy | Additive | Recommended canonical |
|---|---|---|---|
| **Lines** | 401-422 (K1-K8 boundary dimensions, 22 lines) | 758-841 (Appendix W297 P6 §9 + §10, 84 lines) | Single §9 Limitations + §10 Future Work |
| **Content** | 8 K-dimensions (K1-K8) | §9.1.1-§9.1.6 disclosures + §9.2 mapping + §10.1.1-§10.1.4 roadmap | **Adopt additive as §9 + §10 (Wave 297 P6 design)** |
| **Lines to delete** | 22 (legacy §4 K1-K8) | 0 (promote to canonical) | **22 lines to delete** (legacy §4) |
| **Lines to preserve** | 0 | 84 (canonical §9 + §10 from additive) | **84 lines to preserve** |
| **Net delta** | — | — | **+62 lines (§4 expansion via Wave 297 P6 disclosure)** |

**Decision rationale:** Per Wave 297 P6 + DS-01, the legacy §4 K1-K8 (8 dimensions) is preserved and supplemented by the Wave 297 P6 §9.1.1-§9.1.6 disclosures (6 scope-of-current-state items) + §10.1.1-§10.1.4 roadmap (4 implementation items). The legacy K1-K8 + Wave 297 P6 §9 disclosures together form the canonical §9 Limitations.

---

## 2. Net-New Sections (no legacy equivalent)

### Topic 7: §2 RELATED WORK (FRESH-WRITING, Wave 297 P2 §4.2)

| Aspect | Status | Recommended canonical |
|---|---|---|
| **Lines** | None in current paper | 600-800 words per Wave 299 paper-a-outline.md §3.2 (lines 79-92) |
| **Content** | — | 3-layer structure: (i) Inference optimization (Karras ODE, EDM, Consistency Models, distillation); (ii) FM theory (Lipman FM, BGV12/V03, Liu flow matching); (iii) Typed ML systems (BEAM-style process algebras, capability-based security, contract-driven design) |
| **Lines to delete** | 0 (no legacy) | 0 |
| **Lines to preserve** | 0 | ~40 (fresh §2 Related Work section) |
| **Net delta** | — | **+40 lines (FRESH-WRITING)** |

**Decision rationale:** Per DS-09, no source-of-truth doc exists yet; must be assembled from Wave 298 P5 literature compare (FM theory refs) + Wave 287 + Wave 291 audit docs (inference optimization refs) + Wave 268 contracts design (typed ML systems refs). RECOMMENDED 3-paragraph structure per DS-09. WRITE during W7 fold-in (5-7 hours).

### Topic 8: §8 REPRODUCIBILITY (FRESH-WRITING, Wave 297 P2 §4.8)

| Aspect | Status | Recommended canonical |
|---|---|---|
| **Lines** | None in current paper | 600-800 words per Wave 299 paper-a-outline.md §3.8 (lines 199-211) |
| **Content** | — | SHA-256-pinned checkpoints + hash-chained transition logs + D.4 byte-stable 30/30 regression suite + Wave 286 FID GPU fixpoint + Wave 290 batched harness + Wave 268 strict-clean + Wave 296 PaperQuantitiesCache opt-in flag |
| **Lines to delete** | 0 (no legacy) | 0 |
| **Lines to preserve** | 0 | ~40 (fresh §8 Reproducibility section) |
| **Net delta** | — | **+40 lines (FRESH-WRITING)** |

**Decision rationale:** Per Wave 297 P2 §4.8, §8 Reproducibility is a PRIMARY contribution. Content is sourced from Wave 286 P + Wave 290 + Wave 296 + Wave 268 docs. WRITE during W7 fold-in.

### Topic 9: §11 CONCLUSION (FRESH-WRITING, Wave 297 P2 §4.11)

| Aspect | Status | Recommended canonical |
|---|---|---|
| **Lines** | None in current paper | 200-300 words per Wave 299 paper-a-outline.md §3.11 (lines 227-236) |
| **Content** | — | Framework reconstruction (typed-contracts + 3-domain + state bundle) + 4 contributions recap + future-work pointer to §10 |
| **Lines to delete** | 0 (no legacy) | 0 |
| **Lines to preserve** | 0 | ~15 (fresh §11 Conclusion section) |
| **Net delta** | — | **+15 lines (FRESH-WRITING)** |

**Decision rationale:** Per Wave 297 P2 §4.11 + Wave 299 paper-a-outline.md §3.11, §11 Conclusion is the closing 200-300 word recap. WRITE during W7 fold-in.

---

## 3. Canonical 11-Section Target Structure (Wave 299 paper-a-outline.md §3)

| § | Section | Words | Source | Status |
|---|---|---:|---|---|
| 1 | Introduction | 800-1000 | Wave 297 P3 §4.1 prose (lines 52-67 of additive) | Additive → canonical |
| 2 | Related Work | 600-800 | FRESH-WRITING (Wave 298 P5 + Wave 287 + Wave 291 + Wave 268) | NEW |
| 3 | Framework | 1500-2000 | Wave 297 P4 Appendix A.1 (lines 492-517) | Additive → canonical |
| 4 | Scheduler Family | 1200-1500 | Wave 297 P4 Appendix A.2 (lines 519-560) + Wave 294 P2 inline fixes | Additive → canonical |
| 5 | Adapter Protocol | 800-1000 | Wave 297 P4 Appendix A.3 (lines 562-594) | Additive → canonical |
| 6 | Theoretical Lenses | 600-800 | Wave 297 P2 §4.6 (FRESH-WRITING — JMAA Theorem 1 restated + Path A outline + Path B pointer) | NEW |
| 7 | Empirical Results | 1500-2000 | Wave 297 P5 Appendix W297 P5 §7 (lines 624-755) | Additive → canonical |
| 8 | Reproducibility | 600-800 | Wave 297 P2 §4.8 (FRESH-WRITING) | NEW |
| 9 | Limitations | 400-600 | Wave 297 P6 Appendix W297 P6 §9 (lines 762-787) | Additive → canonical |
| 10 | Future Work | 300-400 | Wave 297 P6 Appendix W297 P6 §10 (lines 789-815) | Additive → canonical |
| 11 | Conclusion | 200-300 | Wave 297 P2 §4.11 (FRESH-WRITING) | NEW |
| **Total** | — | **11.0 pages** | — | — |

**Note on page budget.** Wave 299 paper-a-outline.md §5 (lines 256-275) reports the 11-section word budget as 1.5+1.0+2.5+1.5+1.0+1.5+3.0+1.0+0.5+0.5+0.5 = **14.5 pages** (with figures + tables + references), which is within the TNNLS 14 ± 2 page envelope. DS-06 confirms the 14.5-page structure is REJECTED as "exceeds TNNLS 14-page main-track limit"; the canonical structure is the **14.0-page** version per DS-06 (with §6 trimmed to 1.5 pages).

---

## 4. Section-by-Section Deletion Plan (Cumulative)

| # | Section | Lines deleted | Lines preserved | Net delta | Source-of-truth |
|---:|---|---:|---:|---:|---|
| 1 | Title | 4 | 3 | −4 | Additive §1 prose |
| 2 | Abstract | 11 | 1 | −10 | Additive §1 prose |
| 3 | §1 Introduction | 44 | 21 | −23 | Additive §1 prose |
| 4 | §2 Algorithm | 190 | 135 | −55 | Additive Appendices A.1-A.4 |
| 5 | §3 Experiments | 140 | 130 | −10 | Additive Appendix W297 P5 §7 |
| 6 | §4 Limitations | 22 | 84 | +62 | Additive Appendix W297 P6 §9+§10 |
| 7 | §2 Related Work (NEW) | 0 | 40 | +40 | FRESH-WRITING |
| 8 | §8 Reproducibility (NEW) | 0 | 40 | +40 | FRESH-WRITING |
| 9 | §11 Conclusion (NEW) | 0 | 15 | +15 | FRESH-WRITING |
| 10 | §5 Flattening Checklist | 18 | 0 | −18 | DELETE (workflow-internal, not paper content) |
| 11 | §5.5 Efficiency narrative | 23 | 0 | −23 | DELETE (fold into §7 Empirical Results discussion) |
| 12 | §6 Reviewer-Facing Static Reference Labels | 22 | 0 | −22 | DELETE (internal artifact, not paper content) |
| 13 | §7 Add Appendix W297 P4 framing-note preamble | 4 | 0 | −4 | DELETE (no longer needed when promoted to canonical) |
| 14 | §7 Add Appendix W297 P5 framing-note preamble | 3 | 0 | −3 | DELETE |
| 15 | §7 Add Appendix W297 P6 framing-note preamble | 1 | 0 | −1 | DELETE |
| 16 | §7 Add Appendix W298 P7 framing-note preamble | 1 | 0 | −1 | DELETE |
| **Total** | — | **483** | **469** | **−14 lines** | — |

**Expected post-RESOLUTION paper length:** 1083 − 14 = **1069 lines** (down from current 1083). Note that some sections (§5, §6) are workflow-internal artifacts that should be deleted entirely (not preserved as canonical), while the net-new sections (§2 Related Work, §8 Reproducibility, §11 Conclusion) are FRESH-WRITING that ADD content. The −14-line net delta reflects the balance of legacy deletions vs additive preserves vs fresh additions.

---

## 5. Cross-Reference Update Plan

The 6 dual-present topic pairs and 4 net-new sections trigger cross-reference updates in **~15 audit docs** per DS-01. Per the grep output, the legacy line ranges cited in audit docs are:

| Legacy line range | Cited in audit docs | Action |
|---|---|---|
| lines 71-258 | wave291-final.md, wave292-final.md, wave293-p1-locate-sign.md, wave293-p2-verify-direction.md, wave293-p3-fix-applied.md, wave293-p4-related-docs.md, wave293-final.md, wave294-final.md, wave294-p1-re-inventory.md, wave294-p2-medium-fixed.md, wave294-p3-low-paper-fixed.md, wave294-p4-cross-verify.md, wave297-p1-paper-inventory.md, wave297-final.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update to canonical §3/§4/§5 ranges** (lines TBD post-RESOLUTION) |
| lines 259-400 | wave297-final.md, wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md, wave299-paper-a-outline.md | **Update to canonical §7 Empirical Results range** |
| lines 401-422 | wave297-final.md, wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update to canonical §9 Limitations range** |
| lines 423-462 | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **DELETE cross-reference** (§5 Flattening Checklist is workflow-internal, not paper content) |
| lines 464-484 | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **DELETE cross-reference** (§6 Reviewer-Facing Static Reference Labels is workflow-internal) |
| lines 486-620 | wave297-p6-limitations-rewritten.md, wave297-final.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update to canonical §3/§4/§5 ranges** (Appendix A.1-A.4 → canonical §3/§4/§5) |
| lines 621-755 | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update to canonical §7 range** |
| lines 756-1083 | wave298-p7-paper-append.md | **Update to canonical §10 range** |

**Cross-reference update task:** Add a Phase 2 task to the RESOLUTION pass that does `sed` or manual edit on these ~15 audit docs to update line-range references. **This is OUT OF SCOPE for the planning pass** (DS-01 notes "5-gate verification per commit") but IN SCOPE for the execution pass.

---

## 6. Audit Doc Preservation List

The following audit docs are **preserved verbatim** (no edits required) as the source-of-truth for the canonical sections:

| Audit doc | Preserved as source-of-truth for | Section in canonical |
|---|---|---|
| `docs/audit/wave297-p2-paper-design.md` §1 | 11-section structure | All sections |
| `docs/audit/wave297-p3-intro-rewritten.md` | §1 prose (apply verbatim per DS-01) | §1 Introduction |
| `docs/audit/wave297-p4-framework-rewritten.md` | §3 Framework prose | §3 Framework |
| `docs/audit/wave297-p5-empirical-rewritten.md` | §7 Empirical Results prose | §7 Empirical Results |
| `docs/audit/wave297-p6-limitations-rewritten.md` | §9 + §10 Limitations + Future Work prose | §9 + §10 |
| `docs/audit/wave298-p7-paper-append.md` | §MS.deep_innovations (Code #1-#5 + Method #1-#2) | Folded into §3/§4/§5/§8 |
| `docs/audit/wave294-p2-medium-fixed.md` | 1 HIGH (cosine sign) + 2 MEDIUM (factory-vs-adapter, registry-key vs schedule_family) fixes | Apply inline during §2 fold-in |
| `docs/audit/wave294-p3-low-paper-fixed.md` | 3 LOW fixes (DEPRECATED marker, schedule_family default, MultiChannelJitteredConstantScheduler citation) | Apply inline during §2 fold-in |
| `docs/audit/wave293-p3-fix-applied.md` | cosine closed-form sign flip (Wave 293 M-HIGH-1) | Apply inline at §2.2 |
| `docs/audit/wave298-p5-literature-compare.md` | FM theory refs for §2 Related Work | Source for §2 Related Work fresh-writing |
| `docs/audit/wave298-p6-deep-innovations.md` | 4 framework innovations (typed-contracts, CUDA-graph, ledger chain, restart blender) | Source for §3 Framework |
| `docs/audit/wave291-final.md` | Codim CIFAR-10 RF HARMFUL verdict (+10.721%) | §9 Limitations §9.1.2 disclosure |
| `docs/audit/wave291-p5-3seed-results.md` | 3-seed verification protocol | §7 Empirical Results statistical methodology |
| `docs/audit/wave292-p1-pipeline-inventory.md` | 15 dormant sites inventory | §9.1.1 + §10.1.1 roadmap |
| `docs/audit/wave292-p2-config-genealogy.md` | 12/13 cells use CosineAnnealScheduler | §7.4 framework-not-theory verdict |
| `docs/audit/wave296-p1-architecture.md` | Wave 296 P1 capability-token design | §3 Framework + §5 Adapter Protocol |
| `docs/audit/wave296-p2-cache.md` | PaperQuantitiesCache carrier design | §3 Framework + §10 Future Work |

**All 17 audit docs preserved verbatim** — they are the canonical source-of-truth for the canonical sections.

---

## 7. Baseline 5-Gate Verification (CURRENT UNCHANGED paper)

Per the task directive: "After writing the plan, run 5-gate verification on the CURRENT (unchanged) paper-flat-flattened.md to establish baseline."

| Gate | Command | Result | Status |
|---|---|---|:---:|
| 1. D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 warnings (pre-existing DeprecationWarnings), 1.08s | **PASS** |
| 2. ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | **PASS** |
| 3. mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code=0, 0 project warnings (Documentation built in 20.95s) | **PASS** |
| 4. claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL by Disputed by; **No drift detected** | **PASS** |
| 5. vendored/data NOT touched | `git diff --stat -- vendored/ data/` | (empty) | **PASS** |

**Baseline status:** All 5 gates **PASS** on the CURRENT (unchanged) paper-flat-flattened.md. The baseline establishes that the dual-present state is currently verifiable and that any RESOLUTION-pass execution must maintain all 5 gates per commit per DS-01.

---

## 8. RESOLUTION Execution Pass Sequencing (DS-01)

The 8-week plan (DS-01) calls for a 2-week wall-clock RESOLUTION pass with 6 weekly gates:

| Week | Deliverable | Lines deleted | Cross-refs updated | 5-gate verification |
|:---:|---|---:|---:|---|
| 1 | Title + Abstract + §1 Introduction fold-in (lines 1-67 collapsed) | −37 lines | ~10 audit docs | All 5 gates PASS |
| 2 | §3/§4/§5 fold-in (lines 71-258 + lines 488-620) | −55 lines | ~10 audit docs | All 5 gates PASS |
| 3 | §7 Empirical Results fold-in (lines 259-400 + lines 624-755) + cover letter rebalance (DS-10) | −10 lines | ~5 audit docs | All 5 gates PASS |
| 4 | §9 + §10 Limitations + Future Work fold-in (lines 401-422 + lines 758-841) | +62 lines (expansion, not deletion) | ~5 audit docs | All 5 gates PASS |
| 5 | §2 Related Work fresh-writing (DS-09, 600-800 words) | 0 lines | 0 | All 5 gates PASS |
| 6 | §8 Reproducibility fresh-writing (600-800 words) | 0 lines | 0 | All 5 gates PASS |
| 7 | §6 Theoretical Lenses fresh-writing (DS-06, 1.5 pages) + §11 Conclusion (200-300 words) + 4-contribution list finalization (DS-07) + 7-innovation split (DS-08) | +55 lines (expansion) | 0 | All 5 gates PASS |
| 8 | User final-review + submission authorization (DS-11/DS-12) | 0 lines | 0 | All 5 gates PASS |

**Total expected wall-clock:** 8 weeks (2-week RESOLUTION + 6-week surrounding gates) per DS-01.

---

## 9. CRITICAL: User Authorization Required for Wave 268 Strict-Clean Break

Per DS-01's dependency: **"User authorization for Wave 268 strict-clean break (additive appendices promoted to canonical, legacy deleted)"**. The RESOLUTION execution pass cannot begin until the user explicitly authorizes:
1. **Title re-anchor** (delete legacy title + RE-ANCHOR NOTE, promote additive title).
2. **Abstract re-anchor** (delete legacy abstract + RE-ANCHOR NOTE, promote additive abstract).
3. **§1 Introduction re-anchor** (delete legacy intro + RE-ANCHOR NOTE blocks, promote additive §1 prose verbatim per Wave 297 P3 §4.1).
4. **§2 Algorithm → §3/§4/§5 fold-in** (delete legacy §2.1-§2.10, promote additive Appendix A.1-A.4 with Wave 294 P2 inline fixes).
5. **§3 Experiments → §7 Empirical Results fold-in** (delete legacy §3.1-§3.6, promote additive Appendix W297 P5 §7 with 6-column status table).
6. **§4 Limitations → §9 + §10 fold-in** (delete legacy K1-K8, promote additive Appendix W297 P6 §9 + §10 with 6 disclosures + 4 roadmap items).

**Without explicit user authorization, no edits to paper-flat-flattened.md are performed.** This plan document is the canonical source-of-truth for the eventual RESOLUTION execution pass.

---

## 10. INVARIANTS (Preserved by This Plan)

Per DS-01 5-gate verification:

| Invariant | Status | Evidence |
|---|:---:|---|
| Wave 268 strict-clean | **YES** | This plan does NOT edit `paper-flat-flattened.md`; only writes a new `docs/audit/wave300-p3-resolution-plan.md` |
| D.4 30/30 | **PASS** | Baseline established: 30 passed, 1.08s |
| claims no drift | **PASS** | Baseline established: 61 active / 0 provisional / 2 deprecated / CLM-040 PROVISIONAL |
| ruff 0 | **PASS** | Baseline established: All checks passed |
| mkdocs 0 warnings | **PASS** | Baseline established: exit_code=0 |
| vendored NOT touched | **PASS** | Baseline established: empty diff |

---

## 11. Files referenced (NOT modified by this plan)

- **Source-of-truth (canonical):** `docs/drafts/paper-flat-flattened.md` (1083 lines, dual-present)
- **Source-of-truth (Wave 297 P3 §1 prose):** `docs/audit/wave297-p3-intro-rewritten.md` (apply verbatim per DS-01)
- **Source-of-truth (Wave 297 P2 11-section):** `docs/audit/wave297-p2-paper-design.md` §1
- **Source-of-truth (Wave 299 canonical outline):** `docs/audit/wave299-paper-a-outline.md` §3
- **Source-of-truth (Wave 299 dual-present fingerprint):** `docs/audit/wave299-final-verification.md` §0
- **Source-of-truth (Wave 297 P4 framework reframe):** `docs/audit/wave297-p4-framework-rewritten.md`
- **Source-of-truth (Wave 297 P5 empirical reframe):** `docs/audit/wave297-p5-empirical-rewritten.md`
- **Source-of-truth (Wave 297 P6 limitations reframe):** `docs/audit/wave297-p6-limitations-rewritten.md`
- **Source-of-truth (Wave 298 P7 deep innovations):** `docs/audit/wave298-p7-paper-append.md`
- **Source-of-truth (Wave 294 P2 fixes):** `docs/audit/wave294-p2-medium-fixed.md` (1 HIGH + 2 MEDIUM)
- **Source-of-truth (Wave 294 P3 fixes):** `docs/audit/wave294-p3-low-paper-fixed.md` (3 LOW)

## 12. Files to be created/modified by RESOLUTION execution (NOT this pass)

- **TO MODIFY:** `docs/drafts/paper-flat-flattened.md` (483 lines deleted, 469 lines preserved, 14 net-new sections = 1069 lines post-RESOLUTION; requires explicit user authorization per Wave 268 strict-clean)
- **TO UPDATE:** ~15 audit docs (Wave 280/286/287/297/298 with legacy line-range references)
- **TO CREATE:** None (all content is sourced from existing audit docs + Wave 297 P3-P6 additive appendices)

---

**End of Wave 300 P3 RESOLUTION plan.** This document is the canonical source-of-truth for the eventual RESOLUTION execution pass. No edits to `paper-flat-flattened.md` are performed; the user must explicitly authorize the Wave 268 strict-clean break before the execution pass can begin.