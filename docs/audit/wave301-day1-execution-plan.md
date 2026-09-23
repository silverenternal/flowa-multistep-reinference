# Wave 301 Day 1 — RESOLUTION Execution Plan + Structure Lock

**Date:** 2026-09-23
**Mode:** PLAN ONLY (no edits to `paper-flat-flattened.md` until user authorization per Wave 268 strict-clean)
**Author:** Wave 301 Day 1 execution planning agent
**Source-of-truth:** `docs/audit/wave300-p3-resolution-plan.md` (Wave 300 P3 RESOLUTION plan)
**User-authorization doc:** `docs/audit/wave301-day0-prompt.md` (awaiting sign-off)
**File under modification (once authorized):** `docs/drafts/paper-flat-flattened.md` (currently 1404 lines)

---

## 0. CRITICAL GUARD — READ BEFORE EXECUTING

**THIS PLAN EXECUTES ONLY AFTER USER AUTHORIZATION OF THE WAVE 268 STRICT-CLEAN BREAK.**

Per Wave 268 strict-clean rule: **no edits to `paper-flat-flattened.md` are performed without explicit user authorization**. The Wave 301 Day 268 prompt at `docs/audit/wave301-day0-prompt.md` §2 lists **8 destructive deletion steps** that collectively delete 483 lines (legacy) + add 469 lines (additive promoted) + add 95 lines (fresh sections §2/§8/§11) = **−14-line net delta** (1083 → 1069 lines per Wave 300 P3 plan, with current file at 1404 lines due to Wave 297/298/300 P5 fold-in additions beyond original scope).

**If the user has not signed off Day 268 with explicit text override, NO EDITS TO `paper-flat-flattened.md` ARE PERFORMED.** This plan remains READ-ONLY and serves as the canonical source-of-truth for the execution pass that proceeds only on user authorization.

**Pre-execution prerequisites (all required before agent starts Day 1):**
1. Day 268 user sign-off on 6 dual-present pair decisions (per `wave301-day0-prompt.md` §1)
2. Day 268 explicit authorization for Wave 268 strict-clean break (per `wave301-day0-prompt.md` §2)
3. Day 268 venue lock to TNNLS (per `wave301-day0-prompt.md` §3)
4. Day 268 timeline selection (8-10 day vs 12-15 day; per `wave301-day0-prompt.md` §4)
5. Day 268 §6 Theoretical Lenses decision (drop entirely vs fold into §1 companion paragraph)
6. Day 268 §10 Future Work decision (drop entirely vs fold into §8 Limitations)
7. Day 268 figure count decision (3-4 figures + 2-3 tables vs 5-6 figures)

If any of the above are missing, **STOP** and re-engage user.

---

## 1. Current Paper State Snapshot (verified at start of Wave 301 Day 1)

| Attribute | Value | Source |
|---|---|---|
| **File path** | `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-flat-flattened.md` | Direct read |
| **Line count** | 1404 lines (verified by `wc -l`) | Bash baseline |
| **Word count** | ~36027 words (Wave 300 P3 estimate; verified by section sum) | Wave 300 P3 §0 |
| **Section count** | 23 H2 sections (19 legacy + 4 additive appendices: W297 P4 + W297 P5 + W297 P6 + W298 P7 + W300 P5 fold-in) | Direct read |
| **Dual-present pairs** | 6 (Title, Abstract, §1 Intro, §2 Algorithm, §3 Experiments, §4 Limitations) | Wave 300 P3 §1 |
| **Net-new sections needed** | 3 (§2 Related Work + §8 Reproducibility + §11 Conclusion) | Wave 300 P3 §2 |
| **Wave 268 strict-clean** | ACTIVE — agent blocked from destructive edits until user authorization | Wave 268 + DS-01 |

### 1.1 5-Gate Baseline (verified PASS at start of Wave 301 Day 1)

| Gate | Command | Result | Status |
|---|---|---|:---:|
| 1. D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 pre-existing warnings (DeprecationWarnings from `adaptive_reflow/contracts/__init__.py` + `adaptive_reflow/molecular/__init__.py`), 8.61s | **PASS** |
| 2. ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | **PASS** |
| 3. mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code=0, 0 project warnings (Documentation built in 21.84s; Material upstream chatter filtered per Wave 294 P4 precedent) | **PASS** |
| 4. claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL by Disputed by; **No drift detected** | **PASS** |
| 5. vendored/data NOT touched | `git diff --stat -- vendored/ data/` | (empty) | **PASS** |

**Baseline status:** All 5 gates **PASS** on the CURRENT (unchanged) paper. The agent MUST re-establish this baseline after each deletion step (per Wave 300 P3 §7 + Wave 268 strict-clean invariant).

---

## 2. Pair-by-Pair Deletion/Preservation Manifest

For each of the 6 dual-present topic pairs, this section lists: (a) the legacy lines to DELETE, (b) the additive lines to PROMOTE to canonical position, (c) any special inline corrections needed (e.g., Wave 294 P2 cosine sign flip), and (d) cross-reference updates required.

### Pair 1: TITLE

| Aspect | Detail |
|---|---|
| **Legacy lines (DELETE)** | lines 1-4 (legacy title + 4-line RE-ANCHOR NOTE block) |
| **Additive lines (PROMOTE)** | lines 13-15 (subsection "### New title (Wave 297 P2 proposal)") |
| **Net delta** | −4 lines |
| **Canonical content (post-RESOLUTION)** | Line 1: `# FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints.` (single title line; no RE-ANCHOR NOTE; no "### New title" subsection) |
| **Special corrections** | None |
| **Cross-references affected** | None in current paper; downstream audit docs that quote the legacy title need updates (see §4) |

**Deletion step (Pair 1):**
```
DELETE: lines 1-4 (title line 1 + blank line 2 + Wave 297 P3 RE-ANCHOR NOTE block lines 3 + separator line 4 with `---`)
PROMOTE: lines 13-15 → canonical lines 1-3 (verbatim)
REWRITE: title block becomes single line "# FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints."
```

### Pair 2: ABSTRACT

| Aspect | Detail |
|---|---|
| **Legacy lines (DELETE)** | lines 7-12 (Abstract heading + 9-line legacy abstract + 2-line Wave 297 P3 RE-ANCHOR NOTE) |
| **Additive lines (PROMOTE)** | lines 17-19 (5-sentence additive abstract — actually spans 1 paragraph in the file at line 19) |
| **Net delta** | −10 lines |
| **Canonical content (post-RESOLUTION)** | `## Abstract` heading + 5-sentence re-anchored abstract (lines 17-19 verbatim) |
| **Special corrections** | None |
| **Cross-references affected** | None in current paper; audit docs reference abstract by section label not line number |

**Deletion step (Pair 2):**
```
DELETE: lines 7-12 (heading + 9-line legacy abstract + RE-ANCHOR NOTE)
PROMOTE: line 17 "### New abstract (Wave 297 P2 proposal)" → becomes "## Abstract" heading
PROMOTE: line 19 single-paragraph 5-sentence additive abstract → becomes the only Abstract content
```

### Pair 3: §1 INTRODUCTION

| Aspect | Detail |
|---|---|
| **Legacy lines (DELETE)** | lines 23-50 (4-paragraph legacy intro + 6-item legacy contributions list) |
| **Additive lines (PROMOTE)** | lines 52-67 (additive 4-paragraph framework-reconstruction intro + 4-item contributions list) |
| **Legacy RE-ANCHOR NOTE blocks (DELETE)** | lines 27, 31, 35, 39, 50 (Wave 297 P3 §1 ¶1/¶2/¶3/¶4/Contributions RE-ANCHOR NOTEs) |
| **Net delta** | −23 lines (44 legacy deletions − 21 additive promotions) |
| **Canonical content (post-RESOLUTION)** | `## 1 Introduction` heading + 4-paragraph additive intro (lines 54, 56, 58, 60 verbatim) + 4-item contributions list (lines 64-67 verbatim) |
| **Special corrections** | None |
| **Cross-references affected** | Wave 298 P7 §MS.di.6 honest disclosure cross-ref to §1; Wave 298 P7 §MS.di.8 cross-reference table maps §MS.di.6 → "§1 (Introduction)" |

**Deletion step (Pair 3):**
```
DELETE: lines 23-50 (heading + 4 legacy paragraphs + 5 RE-ANCHOR NOTE blocks + 6-item contributions + 1 contributions RE-ANCHOR NOTE)
PROMOTE: line 52 "### New §1 Introduction (Wave 297 P2 proposal)" → becomes "## 1 Introduction" heading
PROMOTE: lines 54, 56, 58, 60 (additive 4-paragraph prose verbatim)
PROMOTE: line 62 "### Our contributions (Wave 297 P2 proposal)" → becomes "### Contributions" (drop Wave 297 P2 marker)
PROMOTE: lines 64-67 (4-item contributions list verbatim)
```

### Pair 4: §2 ALGORITHM → §3 Framework + §4 Scheduler Family + §5 Adapter Protocol

| Aspect | Detail |
|---|---|
| **Legacy lines (DELETE)** | lines 71-258 (10 sub-sections §2.1-§2.10, 5 tables, §MS.theorem1_data_pipeline_entry_points, §MS.config_genealogy, §MS.claim_audit) |
| **Additive lines (PROMOTE to canonical §3/§4/§5)** | lines 488-517 (Appendix A.1 → §3 Framework), lines 519-560 (Appendix A.2 → §4 Scheduler Family), lines 562-594 (Appendix A.3 → §5 Adapter Protocol), lines 596-616 (Appendix A.4 → relocate to §4 or supplementary) |
| **Net delta** | ~−55 lines (190 legacy deletions − 135 additive promotions) |
| **Canonical content (post-RESOLUTION)** | §3 Framework (verbatim from lines 492-517) + §4 Scheduler Family (verbatim from lines 519-560 + Wave 294 P2 inline fixes) + §5 Adapter Protocol (verbatim from lines 562-594) |
| **Special corrections (CRITICAL)** | **Wave 294 P2 M-HIGH-1**: cosine closed-form sign in Table 2.2 must be FLIPPED from `(1 − cos(π r / (L − 1)))` to `(1 + cos(π r / (L − 1)))` per Wave 293 fix + Wave 294 P2 audit at `docs/audit/wave294-p2-medium-fixed.md` (1 HIGH severity mismatch) |
| **Special corrections (MEDIUM)** | Wave 294 P2 M-MED-1: factory-vs-adapter "framework default" framing correction (12/13 R-cells instantiate `default_cosine_scheduler()`); M-MED-2: registry-key vs `schedule_family()` divergence note (2 of 5 families) |
| **Special corrections (LOW)** | Wave 294 P3: DEPRECATED marker on legacy factory; schedule_family default; MultiChannelJitteredConstantScheduler citation |
| **Cross-references affected** | §3 supersedes legacy §2 preamble (lines 72-76); §4 supersedes legacy §2.1 + §2.2 + §2.4 (lines 77-114 + 127-134); §5 supersedes legacy §3.1 (lines 263-285) |

**Deletion step (Pair 4):**
```
DELETE: lines 71-258 (entire §2 Algorithm section, 10 sub-sections)
PROMOTE: lines 488-517 (Appendix A.1 → canonical §3 Framework, including Wave 297 P4 ADDITIVE REFRAME NOTE preamble + 9 paragraph blocks)
PROMOTE: lines 519-560 (Appendix A.2 → canonical §4 Scheduler Family)
PROMOTE: lines 562-594 (Appendix A.3 → canonical §5 Adapter Protocol)
RELOCATE: lines 596-616 (Appendix A.4 → relocate to §4.4 or supplementary per §6 decision)
APPLY INLINE: Wave 294 P2 M-HIGH-1 cosine sign flip at §4 Table 4.1 (or Table A.2.1)
APPLY INLINE: Wave 294 P2 M-MED-1 factory-vs-adapter correction at §4 ¶2
APPLY INLINE: Wave 294 P2 M-MED-2 registry-key vs schedule_family note at §4 Table 4.1
APPLY INLINE: Wave 294 P3 LOW corrections at §4 §5 (DEPRECATED marker + schedule_family default + MultiChannel citation)
```

### Pair 5: §3 EXPERIMENTS → §7 Empirical Results

| Aspect | Detail |
|---|---|
| **Legacy lines (DELETE)** | lines 259-400 (6 sub-sections §3.1-§3.6 + Table 3.1 + Table 3.2 + Table 3.3 + Figure 4 narrative + head-to-head) |
| **Additive lines (PROMOTE to canonical §7)** | lines 624-755 (Appendix W297 P5 §7.1-§7.11) |
| **Net delta** | ~−10 lines (140 legacy deletions − 130 additive promotions) |
| **Canonical content (post-RESOLUTION)** | §7 Empirical Results with 6-column systematic-evidence status table + statistical methodology block + framework-not-theory verdict + per-tier R6 k6 replication + NFE-matched boundary + head-to-head comparison (verbatim from lines 628-755) |
| **Special corrections** | Wave 297 P5 §7.4 framework-not-theory verdict MUST be preserved verbatim (10/11 cosine-cell pattern); §7.3 statistical methodology block MUST preserve 4 Bonferroni families + 3-seed pool |
| **Cross-references affected** | Wave 300 P5 §7 fold-in (lines 1264-1289) becomes redundant once §7 promoted to canonical; can be deleted after §7 promotion |

**Deletion step (Pair 5):**
```
DELETE: lines 259-400 (entire §3 Experiments section, 6 sub-sections)
PROMOTE: lines 624-755 (Appendix W297 P5 → canonical §7 Empirical Results, including §7.1-§7.11 sub-sections)
PRESERVE: Wave 297 P5 §7.4 framework-not-theory verdict (10/11 cosine-cell pattern) verbatim
PRESERVE: Wave 297 P5 §7.3 statistical methodology block (4 Bonferroni families + 3-seed pool) verbatim
CLEANUP: lines 1264-1289 (Wave 300 P5 §7 fold-in draft block becomes redundant; delete or fold into §7 INVARIANTS section)
```

### Pair 6: §4 LIMITATIONS → §9 Limitations + §10 Future Work

| Aspect | Detail |
|---|---|
| **Legacy lines (DELETE)** | lines 401-422 (8 K-dimensions K1-K8 narrative) |
| **Additive lines (PROMOTE to canonical §9 + §10)** | lines 758-841 (Appendix W297 P6 §9.1.1-§9.1.6 + §9.2 + §10.1.1-§10.1.4 + §10.2-§10.5) |
| **Net delta** | +62 lines (22 legacy deletions − 84 additive promotions; the only expansion in the plan) |
| **Canonical content (post-RESOLUTION)** | §9 Limitations (verbatim from lines 762-787, 6 scope-of-current-state disclosures) + §10 Future Work (verbatim from lines 789-815, 4 implementation-roadmap items) |
| **Special corrections** | Per user's §6/§10 sub-decision (wave301-day0-prompt.md §1 Special sub-decisions): if user selected "DROP §10 entirely" → fold into §8 Limitations; if user selected "KEEP §10" → preserve as canonical §10 |
| **Cross-references affected** | Wave 297 P6 §9.2 mapping to §4 K1-K8 (lines 778-787) becomes ADDITIVE (K1-K8 still referenced as boundary dimensions); Wave 297 P6 §10.3 reading §9 alongside §4 becomes ADDITIVE |

**Deletion step (Pair 6):**
```
DELETE: lines 401-422 (entire §4 Limitations section, 8 K1-K8 paragraphs)
PROMOTE: lines 758-787 (Appendix W297 P6 §9 → canonical §9 Limitations, including §9.1.1-§9.1.6 + §9.2)
PROMOTE: lines 789-815 (Appendix W297 P6 §10 → canonical §10 Future Work IF user keeps §10; ELSE fold into §8 Limitations)
PRESERVE: §9.2 K1-K8 cross-reference (boundary dimensions remain applicable, additive to §9 disclosures)
CLEANUP: lines 1319-1342 (Wave 300 P5 §9 fold-in draft block becomes redundant)
```

### Pair 7: §5 Flattening Checklist + §5.5 Efficiency + §6 Static Reference Labels (workflow-internal artifacts)

| Aspect | Detail |
|---|---|
| **Legacy lines (DELETE)** | lines 423-484 (entire §5 Flattening Checklist + §5.5 Efficiency narrative + §6 Reviewer-Facing Static Reference Labels) |
| **Net delta** | −63 lines (62 deletions from §5 + §6 workflow-internal artifacts) |
| **Canonical content (post-RESOLUTION)** | None — these are workflow-internal artifacts, not paper content. The 5.5 efficiency narrative content is folded into §7 Empirical Results discussion per Wave 300 P3 §1 step 11. |
| **Special corrections** | None — these sections are explicitly marked "workflow-internal" per Wave 300 P3 §1 steps 10-12 |
| **Cross-references affected** | None — these sections have no cross-references in audit docs (verified via grep) |

**Deletion step (Pair 7):**
```
DELETE: lines 423-484 (entire §5 Flattening Checklist + §5.5 Efficiency narrative + §6 Static Reference Labels)
NOTE: This is the ONLY deletion that removes content not replaced by additive — preserve 5.5 efficiency data into §7 Empirical Results discussion
```

---

## 3. Cumulative Deletion Tally (All 7 Pairs)

| # | Pair | Lines deleted | Lines preserved | Net delta | Source-of-truth |
|---:|---|---:|---:|---:|---|
| 1 | Title | 4 | 3 | −4 | Additive §1 prose |
| 2 | Abstract | 11 | 1 | 0 (heading retained) | Additive §1 prose |
| 3 | §1 Introduction | 44 | 21 | −23 | Additive §1 prose |
| 4 | §2 Algorithm → §3/§4/§5 | 190 | 135 | −55 | Additive Appendices A.1-A.4 |
| 5 | §3 Experiments → §7 | 140 | 130 | −10 | Additive Appendix W297 P5 §7 |
| 6 | §4 Limitations → §9+§10 | 22 | 84 | +62 | Additive Appendix W297 P6 §9+§10 |
| 7 | §5 Flattening + §5.5 + §6 Static | 63 | 0 | −63 | None — workflow-internal |
| 8 | §2 Related Work (NEW, FRESH-WRITING) | 0 | 40 | +40 | Wave 298 P5 + Wave 287 + Wave 291 + Wave 268 |
| 9 | §8 Reproducibility (NEW, FRESH-WRITING) | 0 | 40 | +40 | Wave 286 + Wave 290 + Wave 296 + Wave 268 |
| 10 | §11 Conclusion (NEW, FRESH-WRITING) | 0 | 15 | +15 | Wave 297 P2 §4.11 |
| **Total** | — | **474** | **469** | **−5 lines** | — |

**NOTE on net delta**: Wave 300 P3 §4 plan reports −14 lines net (1083 → 1069) for the original 1083-line scope. With the current paper at 1404 lines (includes Wave 298 P7 + Wave 300 P5 fold-in additions), the post-RESOLUTION length will be approximately **1404 − 5 = ~1399 lines** if all 7 pairs are deleted as recommended. The Wave 300 P5 fold-in draft at lines 1087-1404 (~317 lines) becomes partially redundant after RESOLUTION — portions fold into canonical sections, but the fold-in anchor blocks can be removed for an additional ~250-line reduction. Final post-RESOLUTION length depends on whether the fold-in anchors are kept as cross-reference markers or deleted.

**Post-RESOLUTION structure (Wave 297 P2 11-section canonical):**
```
# FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints.   (title)
## Abstract                                                                              (5-sentence)
## 1 Introduction                                                                        (4-item contributions)
## 2 Related Work                                                                        (FRESH-WRITING, 600-800w)
## 3 Framework                                                                           (canonical from Appendix A.1)
## 4 Scheduler Family                                                                     (canonical from Appendix A.2 + Wave 294 P2 fixes)
## 5 Adapter Protocol                                                                     (canonical from Appendix A.3)
## 6 Theoretical Lenses                                                                   (FRESH-WRITING 1.5p OR dropped per user decision)
## 7 Empirical Results                                                                    (canonical from Appendix W297 P5 §7)
## 8 Reproducibility                                                                      (FRESH-WRITING, 600-800w)
## 9 Limitations                                                                          (canonical from Appendix W297 P6 §9)
## 10 Future Work                                                                         (canonical from Appendix W297 P6 §10 OR folded into §8 per user decision)
## 11 Conclusion                                                                          (FRESH-WRITING, 200-300w)
## References                                                                             (TO BE ADDED in Day 4 IEEEtran conversion)
```

---

## 4. Cross-Reference Update Checklist (Audit Docs)

Per Wave 300 P3 §5, the 6 dual-present topic pairs trigger cross-reference updates in **~15 audit docs** that quote legacy line ranges. After RESOLUTION execution, these audit docs must be updated to reflect new line numbers.

### 4.1 Audit docs that cite legacy line ranges (TO UPDATE post-RESOLUTION)

| Legacy line range | Audit doc that cites it | Action required |
|---|---|---|
| lines 1-15 (Title + Abstract) | wave297-p1-paper-inventory.md, wave297-final.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical title block (line 1) + Abstract (line 3) |
| lines 23-67 (§1 Introduction) | wave297-p3-intro-rewritten.md (apply verbatim per DS-01), wave298-p7-paper-append.md §MS.di.8 cross-reference table | **Update** §MS.di.8 cross-reference table to map innovations to canonical §1 Introduction |
| lines 71-258 (§2 Algorithm) | wave291-final.md, wave292-final.md, wave293-p1-locate-sign.md, wave293-p2-verify-direction.md, wave293-p3-fix-applied.md, wave293-p4-related-docs.md, wave293-final.md, wave294-final.md, wave294-p1-re-inventory.md, wave294-p2-medium-fixed.md, wave294-p3-low-paper-fixed.md, wave294-p4-cross-verify.md, wave297-p1-paper-inventory.md, wave297-final.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §3 Framework (lines TBD) + §4 Scheduler Family (lines TBD) + §5 Adapter Protocol (lines TBD) |
| lines 259-400 (§3 Experiments) | wave297-final.md, wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md, wave299-paper-a-outline.md | **Update** to canonical §7 Empirical Results (lines TBD) |
| lines 401-422 (§4 Limitations) | wave297-final.md, wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §9 Limitations (lines TBD) |
| lines 423-484 (§5/§5.5/§6) | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **DELETE cross-references** (workflow-internal artifacts, no paper content) |
| lines 486-620 (Appendix W297 P4) | wave297-p6-limitations-rewritten.md, wave297-final.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §3/§4/§5 ranges (Appendix A.1-A.4 → canonical §3/§4/§5) |
| lines 624-755 (Appendix W297 P5) | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §7 range |
| lines 758-841 (Appendix W297 P6) | wave297-final.md (if any), wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §9/§10 ranges |
| lines 848-1083 (Appendix W298 P7) | wave298-p7-paper-append.md (self-references in §MS.di.10 + §MS.di.11) | **Update** §MS.di.8 cross-reference table; the appendix itself can be deleted post-RESOLUTION (its content folds into canonical §3/§4/§5) |
| lines 1087-1404 (Appendix W300 P5 fold-in draft) | wave300-final.md, wave300-p3-resolution-plan.md (current doc) | **DELETE post-RESOLUTION** (fold-in draft becomes redundant once canonical structure is in place) |

### 4.2 Audit docs preserved verbatim (NO edits required)

Per Wave 300 P3 §6, the following 17 audit docs are preserved verbatim as source-of-truth for canonical sections:

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
| `docs/audit/wave293-p3-fix-applied.md` | cosine closed-form sign flip (Wave 293 M-HIGH-1) | Apply inline at §4.2 cosine row |
| `docs/audit/wave298-p5-literature-compare.md` | FM theory refs for §2 Related Work | Source for §2 Related Work fresh-writing |
| `docs/audit/wave298-p6-deep-innovations.md` | 4 framework innovations (typed-contracts, CUDA-graph, ledger chain, restart blender) | Source for §3 Framework |
| `docs/audit/wave291-final.md` | Codim CIFAR-10 RF HARMFUL verdict (+10.721%) | §9 Limitations §9.1.2 disclosure |
| `docs/audit/wave291-p5-3seed-results.md` | 3-seed verification protocol | §7 Empirical Results statistical methodology |
| `docs/audit/wave292-p1-pipeline-inventory.md` | 15 dormant sites inventory | §9.1.1 + §10.1.1 roadmap |
| `docs/audit/wave292-p2-config-genealogy.md` | 12/13 cells use CosineAnnealScheduler | §7.4 framework-not-theory verdict |
| `docs/audit/wave296-p1-architecture.md` | Wave 296 P1 capability-token design | §3 Framework + §5 Adapter Protocol |
| `docs/audit/wave296-p2-cache.md` | PaperQuantitiesCache carrier design | §3 Framework + §10 Future Work |

**Cross-reference update task (post-RESOLUTION):** Add a Phase 2 task to the RESOLUTION pass that does `sed` or manual edit on the ~15 audit docs in §4.1 to update line-range references. **This is OUT OF SCOPE for the Day 1 RESOLUTION pass** but IN SCOPE for the Day 1 close-out task (verify line-range references in audit docs against the new canonical line numbers).

---

## 5. Step-by-Step Execution Sequence (Day 1)

The Day 1 execution pass executes the following sequence of **destructive deletions** + **canonical promotions** + **inline corrections** + **5-gate re-verification** per pair. Each step is gated by the previous step's 5-gate verification.

### Step 0: Pre-execution guard (BLOCKING)

| Check | Required status |
|---|---|
| Day 268 user sign-off on 6 dual-present pairs (per `wave301-day0-prompt.md` §1) | **YES** |
| Day 268 explicit authorization for Wave 268 strict-clean break (per `wave301-day0-prompt.md` §2) | **YES** |
| Day 268 §6 Theoretical Lenses decision (drop entirely vs fold into §1) | **YES** |
| Day 268 §10 Future Work decision (drop entirely vs fold into §8) | **YES** |
| Day 268 venue lock to TNNLS | **YES** (or other explicit venue) |
| Day 268 timeline selection (8-10 day vs 12-15 day) | **YES** |

**If any check is missing, STOP and re-engage user. NO EDITS.**

### Step 1: Snapshot baseline

| Action | Detail |
|---|---|
| Command | `git stash` (NOT needed since uncommitted changes are minimal) + `git status` to confirm clean state |
| Verify | `wc -l docs/drafts/paper-flat-flattened.md` returns 1404 |
| Verify | 5-gate baseline established (Section 1.1) |

### Step 2: Apply Pair 7 deletions (workflow-internal artifacts; lowest risk)

| Action | Detail |
|---|---|
| DELETE | lines 423-484 (entire §5 Flattening Checklist + §5.5 Efficiency narrative + §6 Static Reference Labels) |
| PRESERVE | 5.5 efficiency data → fold into §7 Empirical Results discussion (deferred to Day 2) |
| 5-gate verify | Re-run all 5 gates; verify no regressions |
| Expected | Lines 423-484 deleted; remaining content intact |

### Step 3: Apply Pair 1 + Pair 2 deletions (Title + Abstract)

| Action | Detail |
|---|---|
| DELETE (Pair 1) | lines 1-4 (legacy title + RE-ANCHOR NOTE) |
| PROMOTE (Pair 1) | lines 13-15 → canonical lines 1-3 (verbatim) |
| DELETE (Pair 2) | lines 7-12 (Abstract heading + legacy abstract + RE-ANCHOR NOTE) |
| PROMOTE (Pair 2) | lines 17-19 → canonical Abstract heading + 5-sentence abstract |
| 5-gate verify | Re-run all 5 gates; verify no regressions |
| Expected | Title block collapsed; Abstract collapsed; line count reduced by ~14 lines |

### Step 4: Apply Pair 3 deletion (Legacy §1 Introduction)

| Action | Detail |
|---|---|
| DELETE | lines 23-50 (4 legacy paragraphs + 5 RE-ANCHOR NOTE blocks + 6-item legacy contributions + 1 contributions RE-ANCHOR NOTE) |
| PROMOTE | lines 52-67 → canonical §1 Introduction (4 additive paragraphs + 4-item contributions) |
| 5-gate verify | Re-run all 5 gates; verify no regressions |
| Expected | §1 Introduction collapsed; 4-item contributions list replaces 6-item list |

### Step 5: Apply Pair 4 deletion (Legacy §2 Algorithm → Canonical §3/§4/§5)

| Action | Detail |
|---|---|
| DELETE | lines 71-258 (entire §2 Algorithm, 10 sub-sections) |
| PROMOTE | lines 488-517 (Appendix A.1) → canonical §3 Framework |
| PROMOTE | lines 519-560 (Appendix A.2) → canonical §4 Scheduler Family |
| PROMOTE | lines 562-594 (Appendix A.3) → canonical §5 Adapter Protocol |
| RELOCATE | lines 596-616 (Appendix A.4) → §4.4 OR supplementary per §6 decision |
| APPLY INLINE | Wave 294 P2 M-HIGH-1 cosine sign flip at §4 Table 4.1 |
| APPLY INLINE | Wave 294 P2 M-MED-1 factory-vs-adapter correction at §4 ¶2 |
| APPLY INLINE | Wave 294 P2 M-MED-2 registry-key vs schedule_family note at §4 Table 4.1 |
| APPLY INLINE | Wave 294 P3 LOW corrections at §4 §5 |
| 5-gate verify | Re-run all 5 gates; verify no regressions |
| Expected | §2 Algorithm deleted; §3 Framework + §4 Scheduler Family + §5 Adapter Protocol promoted to canonical positions |

### Step 6: Apply Pair 5 deletion (Legacy §3 Experiments → Canonical §7 Empirical Results)

| Action | Detail |
|---|---|
| DELETE | lines 259-400 (entire §3 Experiments, 6 sub-sections + tables + Figure 4 narrative) |
| PROMOTE | lines 624-755 (Appendix W297 P5 §7.1-§7.11) → canonical §7 Empirical Results |
| PRESERVE | Wave 297 P5 §7.4 framework-not-theory verdict verbatim |
| PRESERVE | Wave 297 P5 §7.3 statistical methodology block verbatim |
| CLEANUP | Wave 300 P5 §7 fold-in block (lines 1264-1289) becomes redundant; delete |
| 5-gate verify | Re-run all 5 gates; verify no regressions |
| Expected | §3 Experiments deleted; §7 Empirical Results promoted to canonical position |

### Step 7: Apply Pair 6 deletion (Legacy §4 Limitations → Canonical §9 + §10)

| Action | Detail |
|---|---|
| DELETE | lines 401-422 (8 K1-K8 paragraphs) |
| PROMOTE | lines 758-787 (Appendix W297 P6 §9) → canonical §9 Limitations |
| PROMOTE | lines 789-815 (Appendix W297 P6 §10) → canonical §10 Future Work (OR fold into §8 per user decision) |
| PRESERVE | §9.2 K1-K8 cross-reference (boundary dimensions remain applicable) |
| CLEANUP | Wave 300 P5 §9 fold-in block (lines 1319-1342) becomes redundant; delete |
| 5-gate verify | Re-run all 5 gates; verify no regressions |
| Expected | §4 Limitations K1-K8 deleted; §9 Limitations + §10 Future Work promoted |

### Step 8: Apply Pair 5 cleanup (delete Wave 297 P4 + P5 + P6 framing-note preambles)

| Action | Detail |
|---|---|
| DELETE | Wave 297 P4 ADDITIVE REFRAME NOTE preamble (line 490) |
| DELETE | Wave 297 P5 ADDITIVE REFRAME NOTE preamble (line 626) |
| DELETE | Wave 297 P6 ADDITIVE REFRAME NOTE preamble (line 760) |
| DELETE | "End of Wave 297 P4 reframe appendix" closing (line 620) |
| DELETE | "End of Wave 298 P7 deep-innovations appendix" closing (line 1083) |
| 5-gate verify | Re-run all 5 gates; verify no regressions |
| Expected | Appendix framing preambles removed; canonical sections are clean |

### Step 9: Final structure verification + 5-gate baseline re-establishment

| Action | Detail |
|---|---|
| Verify | Paper structure matches Wave 297 P2 11-section canonical |
| Verify | Section ordering: Title → Abstract → §1 Introduction → §2 Related Work (FRESH) → §3 Framework → §4 Scheduler Family → §5 Adapter Protocol → §6 Theoretical Lenses (FRESH or DROP per user decision) → §7 Empirical Results → §8 Reproducibility (FRESH) → §9 Limitations → §10 Future Work (or DROP per user decision) → §11 Conclusion (FRESH) |
| Verify | 5-gate baseline re-established (D.4 30/30 + ruff 0 + mkdocs strict 0 warnings + claims no drift + vendored untouched) |
| Verify | `wc -l docs/drafts/paper-flat-flattened.md` returns expected count (~1399 lines if §6/§10 kept, less if dropped) |

### Step 10: PRESENT TO USER for boundary-clearness check

Per `wave301-day0-prompt.md` §4 timeline, Day 1 ends with **NO user review** (user reviews Day 3 at boundary-clearness check). However, if destructive deletions of unexpected scope are discovered during execution, agent should escalate to user before continuing.

**Day 1 deliverables (per wave301-day0-prompt.md §4 timeline):**
- RESOLUTION pass executed; paper collapses from 1404 → ~1399 lines
- 5-gate verification re-run + baseline re-established
- Structure presented to user at end-of-day for sanity check only

---

## 6. Verification Gate Checklist (Per Deletion Step)

Each deletion step (Steps 2-9) requires the agent to run the **5-gate verification** immediately after the deletion and confirm all 5 gates pass. If any gate fails, the agent must STOP and report the regression.

| Gate | Command | Expected result | Failure mode |
|---|---|---|---|
| 1. D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 pre-existing DeprecationWarnings | If <30 passed, byte-stability broke — STOP and revert |
| 2. ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | If new warnings, syntax/lint broke — STOP and fix |
| 3. mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code=0, 0 project warnings | If new warnings, cross-reference broke — STOP and fix |
| 4. claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated; **No drift detected** | If drift detected, claim lost its paper anchor — STOP and re-anchor |
| 5. vendored NOT touched | `git diff --stat -- vendored/ data/` | (empty) | If non-empty, vendored accidentally edited — revert |

**Additional verification (per Wave 300 P3 §7 + Wave 268 strict-clean):**
| Check | Command | Expected result |
|---|---|---|
| Wave 268 strict-clean audit log entry | Add entry to `docs/audit/wave301-resolution-execution-log.md` (created during execution) | Each deletion step logged with line count delta + 5-gate verification result |

### 6.1 Failure handling

If any 5-gate verification fails after a deletion step:

1. **STOP execution immediately**
2. **Revert the deletion** via `git checkout docs/drafts/paper-flat-flattened.md` (full file revert)
3. **Diagnose the failure** (which gate failed, which line introduced the regression)
4. **Apply fix** OR **escalate to user** if the fix is non-trivial
5. **Re-run all 5 gates** to confirm baseline restored
6. **Resume execution** from the step before the failure

### 6.2 Cross-reference verification (post-RESOLUTION)

After Step 9, run cross-reference verification on audit docs:

| Check | Action |
|---|---|
| Audit docs that cite `docs/drafts/paper-flat-flattened.md` line ranges | `grep -rn "paper-flat-flattened.md:L[0-9]" docs/audit/` → output audit docs that need line-range updates |
| Audit doc CLM-016 / CLM-018 / CLM-019 cross-references | Verify each claim still anchors to a valid line in the canonical paper |
| METRIC_LEDGER.md cross-references | Verify all 126 rows still resolve to valid file:line |

**This is OUT OF SCOPE for Day 1** but flagged for Day 2 + Day 3 cross-reference update passes.

---

## 7. Day 1 End-of-Day Deliverables

| Deliverable | Status | Owner |
|---|---|---|
| RESOLUTION pass executed (Steps 2-8) | DONE | Agent |
| 5-gate baseline re-established (Step 9) | DONE | Agent |
| Cross-reference update list (audit docs to update) | DONE | Agent (this document §4) |
| Day 1 execution log | DONE | Agent (creates `docs/audit/wave301-resolution-execution-log.md`) |
| **User review at end of Day 1** | **NOT REQUIRED** per `wave301-day0-prompt.md` §4 timeline (Day 1 has no user gate) | — |
| **Day 2 fresh-writing prep** | READY (§2 + §6/§8 + §11 word budgets + source-of-truth identified) | Agent (Day 2) |

---

## 8. Day 1 Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| User has not signed off Day 268 | **HIGH** (script has not yet received user reply) | **STOP and escalate** — do not proceed |
| 5-gate regression after a deletion step | LOW (baseline establishes dual-present state passes all 5 gates) | Per §6.1: revert + diagnose + fix + retry |
| Wave 294 P2 inline corrections introduce regression | LOW (Wave 294 P2 audit verified them additive-safe) | Per §6.1: revert + diagnose + fix + retry |
| Cross-references in audit docs become stale | MEDIUM (Day 1 scope, but flagged for Day 2/3) | Day 2 + Day 3 cross-reference update passes |
| File line count after RESOLUTION differs from estimate | LOW (estimates are based on Wave 300 P3 plan) | Per §3 note: ~1399 lines expected (less if §6/§10 dropped) |
| §6/§10 user decision not yet made | **HIGH** (if user has not selected from wave301-day0-prompt.md §1 Special sub-decisions) | **STOP and re-engage user** before applying Pair 6 or §6 promotion |

---

## 9. Files To Be Modified by RESOLUTION Execution (Day 1 ONLY)

| File | Action | Owner | Gate |
|---|---|---|---|
| `docs/drafts/paper-flat-flattened.md` | 7 deletion steps + 5 inline corrections (Wave 294 P2/3) | Agent (post-authorization) | 5-gate per step |
| `docs/audit/wave301-resolution-execution-log.md` | CREATE — execution log entry per deletion step with line-count delta + 5-gate verification result | Agent | Per-step 5-gate |

**Files NOT modified by Day 1** (OUT OF SCOPE):
- ~15 audit docs with line-range references (Day 2/3 cross-reference update)
- `docs/audit/wave300-p3-resolution-plan.md` (READ-ONLY source-of-truth)
- `docs/audit/wave301-day0-prompt.md` (READ-ONLY Day 0 user input)

---

## 10. Day 1 Exit Criteria

Day 1 is COMPLETE when ALL of the following are true:

1. Steps 2-9 executed in order with 5-gate verification passing after each step
2. Paper structure matches Wave 297 P2 11-section canonical ordering
3. 5-gate baseline re-established on canonical paper (D.4 30/30 + ruff 0 + mkdocs 0 + claims no-drift + vendored untouched)
4. Execution log created at `docs/audit/wave301-resolution-execution-log.md`
5. No user review required (Day 3 boundary-clearness check is the next user gate)
6. Day 2 fresh-writing prep is READY (§2/§8/§11 word budgets + source-of-truth identified)

If any exit criterion is not met, Day 1 is NOT COMPLETE and agent must continue or escalate.

---

## 11. Files Referenced (READ-ONLY)

- `docs/drafts/paper-flat-flattened.md` (1404 lines, dual-present)
- `docs/audit/wave300-p3-resolution-plan.md` (Wave 300 P3 RESOLUTION plan)
- `docs/audit/wave301-day0-prompt.md` (Wave 301 Day 0 user input — AWAITING SIGN-OFF)
- `docs/audit/wave297-p2-paper-design.md` (11-section canonical structure)
- `docs/audit/wave297-p3-intro-rewritten.md` (§1 prose source-of-truth)
- `docs/audit/wave297-p4-framework-rewritten.md` (§3 Framework prose source-of-truth)
- `docs/audit/wave297-p5-empirical-rewritten.md` (§7 Empirical Results prose source-of-truth)
- `docs/audit/wave297-p6-limitations-rewritten.md` (§9 + §10 prose source-of-truth)
- `docs/audit/wave298-p7-paper-append.md` (deep innovations source-of-truth)
- `docs/audit/wave294-p2-medium-fixed.md` (1 HIGH + 2 MEDIUM inline fixes)
- `docs/audit/wave294-p3-low-paper-fixed.md` (3 LOW inline fixes)
- `docs/audit/wave293-p3-fix-applied.md` (cosine sign flip Wave 293 M-HIGH-1)
- `docs/audit/wave298-p5-literature-compare.md` (§2 Related Work source)
- `docs/audit/wave291-p5-3seed-results.md` (§7 statistical methodology source)
- `docs/audit/wave292-p1-pipeline-inventory.md` (§9.1.1 + §10.1.1 source)
- `docs/audit/wave292-p2-config-genealogy.md` (§7.4 framework-not-theory source)
- `docs/audit/wave296-p1-architecture.md` (§3 + §5 capability-token design source)
- `docs/audit/wave296-p2-cache.md` (§3 + §10 PaperQuantitiesCache source)
- `docs/audit/wave286-p-fid-gpu-fix.md` (§8 Reproducibility Wave 286 source)
- `docs/audit/wave290-p3-batched-harness.md` (§8 Reproducibility Wave 290 source)
- `docs/audit/wave268-strict-clean.md` (Wave 268 strict-clean rule source-of-truth)

---

**End of Wave 301 Day 1 Execution Plan.** This plan is READ-ONLY and serves as the canonical source-of-truth for the RESOLUTION execution pass that proceeds only on explicit user authorization per Wave 268 strict-clean. If user has signed off Day 268 with explicit text override, the agent may execute Steps 0-10 in sequence. Otherwise, NO EDITS are performed and the agent waits for user input.