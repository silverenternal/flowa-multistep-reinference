# Wave 297 P3 — §1 Introduction + Abstract re-anchored per Wave 297 P2 design

**Date:** 2026-09-23
**Branch:** main
**Prior docs:**
- `docs/audit/wave297-p1-paper-inventory.md` (P1 — current structure, 6 JMAA-prominent sections)
- `docs/audit/wave297-p2-paper-design.md` (P2 — new structure + §1 prose draft)
- `docs/audit/wave296-p1-architecture.md` (W296 P1 — JMAA theory integration architecture)
- `docs/audit/wave296-p2-cache.md` (W296 P2 — PaperQuantitiesCache design)
**Source paper (legacy):** `docs/drafts/paper-flat-flattened.md` (pre-edit, 445 lines, post-Wave-294, 19 sections)
**Target paper (post-edit):** `docs/drafts/paper-flat-flattened.md` (484 lines, +39 lines, ADDITIVE edits only)
**Purpose:** Apply the Wave 297 P2 §1 Introduction + Abstract re-anchor to the canonical paper draft per the Phase 2 design directive. Wave 268 strict-clean rule honoured: **never replace existing text, append correction notes (e.g., "(re-anchored per Wave 297 — ...)") next to old paragraphs**.

---

## 0. TL;DR

- **Mode:** ADDITIVE paper-edit pass per Wave 268 strict-clean rule. Legacy §1 + Abstract preserved verbatim; re-anchor notes appended next to each old paragraph; new §1 + Abstract appended at end of section.
- **Files modified:** `docs/drafts/paper-flat-flattened.md` (+39 lines, 0 deletions).
- **Title re-anchor:** Title note appended at line 3; new title "FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints" appended at line 13-15 as "### New title (Wave 297 P2 proposal)".
- **Abstract re-anchor:** Legacy abstract preserved at line 9; re-anchor note appended at line 11; new abstract appended at line 17-19 as "### New abstract (Wave 297 P2 proposal)".
- **§1 Introduction re-anchor:** All 4 legacy paragraphs preserved at lines 25, 29, 33, 37 with re-anchor notes appended at lines 27, 31, 35, 39; new 4-paragraph §1 appended at lines 52-60 as "### New §1 Introduction (Wave 297 P2 proposal)".
- **Contributions re-anchor:** Legacy 6-item contributions preserved at lines 43-48 with re-anchor note appended at line 50; new 4-item "### Our contributions (Wave 297 P2 proposal)" appended at lines 62-67.
- **D.4 30/30 PASS:** 95 passed (30 D.4 vector tests + 65 paper-grounded scheduler tests), 59 warnings (all pre-existing DeprecationWarnings, not new issues).
- **ruff 0 PASS:** "All checks passed!" (no new errors).
- **mkdocs 0 warnings PASS:** exit_code=0, 0 project warnings (Material upstream chatter filtered per Wave 294 P4 precedent).
- **vendored NOT touched:** verified by `git diff --stat` (no vendored paths in modifications).

---

## 1. Diff stat

```
$ git diff --stat docs/drafts/paper-flat-flattened.md
 docs/drafts/paper-flat-flattened.md | 39 +++++++++++++++++++++++++++++++++++++
 1 file changed, 39 insertions(+)
```

**ADDITIVE ONLY:** 39 insertions, 0 deletions. Legacy content preserved verbatim per Wave 268 strict-clean rule.

The 39 inserted lines distribute across:
- 1 title re-anchor note (line 3)
- 1 new title block (lines 13-15)
- 1 abstract re-anchor note (line 11)
- 1 new abstract block (lines 17-19)
- 4 §1 paragraph re-anchor notes (lines 27, 31, 35, 39)
- 1 contributions re-anchor note (line 50)
- 1 new §1 4-paragraph block (lines 52-60)
- 1 new 4-contribution list (lines 62-67)
- Plus surrounding `---` horizontal rules and blank-line spacing (no semantic content).

---

## 2. Section-by-section re-anchor mapping

### 2.1 Title (line 1, legacy; new block at lines 13-15)

**Legacy:** `# FlowA: Paper-Quantity-Driven Re-Inference for Frozen Flow Matching Checkpoints` (line 1, verbatim, unchanged).

**New (appended at line 13-15):** `### New title (Wave 297 P2 proposal)` block:
```
**FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints.**
```

**Re-anchor note (line 3):** Explains the Wave 297 P2 §2.1 proposal to drop "Paper-Quantity-Driven" (paper quantities are a §6 enrichment, not the framework's identity) and replace with "Training-Free Re-Inference Framework". Legacy title preserved verbatim per Wave 268 strict-clean.

### 2.2 Abstract (line 9, legacy; new block at lines 17-19)

**Legacy:** Single-paragraph DeepSeek F3-framed abstract (line 9, verbatim, unchanged; 225 words / 5 sentences per Wave 209 P7).

**New (appended at line 17-19):** `### New abstract (Wave 297 P2 proposal)` block with 5 sentences matching the Wave 297 P2 §2.2 design:
1. **Problem sentence (no theorem):** "We reconstruct the inference pipeline for flow matching models by inserting an adaptive, multi-round re-inference layer..."
2. **Framework primary sentence:** "...exposing a typed four-port control surface (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) partitioned over three domains (algorithm layer, evaluation layer, adapter layer)..."
3. **Empirical primary sentence:** "We validate FlowA across 7 R-level cells... and 4 K-cells... at paired sample sizes of N = 1000 with 3-seed (seeds 0, 1, 2) Bonferroni-corrected significance tests and a D.4 byte-stable 30/30 regression suite..."
4. **Theoretical enrichment sentence:** "As one theoretical companion, FlowA derives a closed-form upper bound on the bounded-Lipschitz distance..."
5. **Positioning sentence:** "The framework repositions inference-time control as a typed-contracts scheduling problem, structurally disjoint from solver-level, trajectory-level, and re-inference alpha-blending acceleration, and ships with full SHA-256-pinned checkpoints..."

**Re-anchor note (line 11):** Explains the Wave 297 P2 §2.2 proposal to lead with framework reconstruction paradigm, follow with 11-cell empirical significance, and close with JMAA enrichment sentence.

### 2.3 §1 Introduction (lines 25-39, legacy; new block at lines 52-60)

**Legacy:** Four paragraphs at lines 25, 29, 33, 37 preserved verbatim (legacy Wave 211 P2 framing, 4-paragraph theorem-primary structure).

**Re-anchor notes:** Four notes appended at lines 27, 31, 35, 39 — one per legacy paragraph. Each note explains:
- Which W297 P2 design paragraph replaces it
- What framing shift the W297 P2 design applies
- Where to find the new paragraph (below, in "### New §1 Introduction (Wave 297 P2 proposal)")

**New (appended at lines 52-60):** `### New §1 Introduction (Wave 297 P2 proposal)` block with 4 paragraphs:
1. **¶1 Framework lead:** "We reconstruct the inference pipeline for flow matching models by inserting an adaptive, multi-round re-inference layer..." + typed four-port surface + three-domain split + state bundle + latent-distribution-gap motivation reframed as framework-architecture motivation.
2. **¶2 Related work:** Three-layer prior-work framing (solver-level / trajectory-level / re-inference α-blending) + FlowA-as-typed-contracts-framework framing ("occupies a fourth position: a typed-contracts framework that exposes the inference loop as a composable surface").
3. **¶3 Theoretical companion (demoted):** "FlowA is also accompanied by a theoretical lens (one companion among several possible)..." + compressed Theorem 1 statement (1 paragraph, vs legacy ~12-line dense exposition) + CodimensionSheetScheduler partial R6 validation + Wave 296 in-progress.
4. **¶4 Validation:** 7 R-cells + 4 K-cells framing (was: 6 R-cells) + 3-seed (seeds 0, 1, 2) + 4 Bonferroni families + D.4 byte-stable 30/30 + Wave 286 FID GPU fixpoint + CIFAR-10 RF NFE=50 honest -10.7% boundary.

### 2.4 §1 Contributions (lines 43-48, legacy; new block at lines 62-67)

**Legacy:** 6-item contributions list at lines 43-48 preserved verbatim (Wave 211 P2 + Wave 232 P2 list).

**Re-anchor note (line 50):** Explains the W297 P2 §4.1 proposal to reduce from 6 to 4 items and re-anchor: (i) typed-contracts framework architecture (primary), (ii) vendor-friendly integration (primary), (iii) systematic empirical significance (primary), (iv) theoretical companion (demoted).

**New (appended at lines 62-67):** `### Our contributions (Wave 297 P2 proposal)` block with 4 items:
- **(i)** typed-contracts framework — 13 schedulers (9 baselines + 4 paper-quantity-driven) + four-port control surface
- **(ii)** vendor-friendly integration — 5 vendored checkpoints, **zero-line changes to vendored code**
- **(iii)** systematic empirical significance — 7 R-cells + 4 K-cells with 3-seed × 4 Bonferroni families × D.4 byte-stable
- **(iv)** theoretical companion (not framework identity) — JMAA 16-site framework with CodimensionSheetScheduler partial R6 validation + Wave 296 in-progress

---

## 3. Edit discipline + invariants

Per the Wave 297 P3 task scope:

| Invariant | Status | Evidence |
|---|---|---|
| D.4 30/30 | **YES** | `python3 -m pytest tests/test_d4_regression_vectors.py tests/test_paper_grounded_schedulers.py -q` → 95 passed (30 D.4 + 65 paper-grounded scheduler tests), 59 warnings (all pre-existing DeprecationWarning from `default_cosine_scheduler()` factory, not new issues introduced by W297 P3) |
| claims no drift | **YES** | All 6 legacy contributions (i)–(vi) preserved verbatim; all 4 legacy §1 paragraphs preserved verbatim; legacy abstract preserved verbatim; legacy title preserved verbatim. New content is APPENDED only. |
| ruff 0 | **YES** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → "All checks passed!" (no new errors; the paper edit is in `docs/`, which is excluded from ruff per `pyproject.toml [tool.ruff] extend-exclude = ["docs", ...]`) |
| mkdocs 0 warnings | **YES** | `mkdocs build --strict` → exit_code=0, 0 project warnings (Material upstream chatter filtered per Wave 294 P4 precedent; `docs/audit/` is `not_in_nav` per `mkdocs.yml:239`) |
| vendored NOT touched | **YES** | `git diff --stat` shows no vendored paths in modifications; `git status` shows only framework code (runner/engine.py) and `docs/` files modified (consistent with the pre-existing W297 working tree, no new vendored edits) |
| ADDITIVE only | **YES** | `git diff --stat docs/drafts/paper-flat-flattened.md` → 39 insertions, 0 deletions. Wave 268 strict-clean rule honoured. |

---

## 4. New section structure (Wave 297 P2 design, post-edit)

Per `docs/audit/wave297-p2-paper-design.md` §1, the new 11-section structure is:

| # | Section | Status | Re-anchor scope |
|---:|---|---|---|
| 1 | §1 Introduction | **EDITED (P3)** | Re-anchored to framework-primary narrative; legacy preserved verbatim; new appended below |
| 2 | §2 Related Work | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 3 | §3 Framework (typed contracts + three-domain split + adapter protocol + state bundle) | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 4 | §4 Scheduler Family (13 schedulers — 9 without paper quantities, 4 with paper quantities) | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 5 | §5 Adapter Protocol | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 6 | §6 Theoretical Lenses | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 7 | §7 Empirical Results (7 R-cells + 4 K-cells with d_z, p, status) | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 8 | §8 Reproducibility | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 9 | §9 Limitations | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 10 | §10 Future Work | NOT EDITED (P3) | Pending Wave 297 P4+ |
| 11 | §11 Conclusion | NOT EDITED (P3) | Pending Wave 297 P4+ |

**Wave 297 P3 scope:** Section 1 + Abstract + Title only. Sections 2-11 are deferred to Wave 297 P4+ per the W297 P2 design's section-by-section re-anchor directive.

---

## 5. JMAA prominence (post-Wave 297 P3 §1 + Abstract edit)

The legacy paper has JMAA Theorem 1 promoted in 6 sections (Title, Abstract, §1 ¶3, §2.1, §2.6, §2.8 per Wave 297 P1 inventory). The Wave 297 P3 + P2 design reduces JMAA prominence to:

- **Title:** **low** (drops "Paper-Quantity-Driven" from new title; legacy title preserved verbatim per strict-clean)
- **Abstract:** **low** (theorem demoted to one theoretical companion sentence in new abstract; legacy abstract preserved verbatim per strict-clean)
- **§1 Introduction:** **low** (theorem demoted to one theoretical companion paragraph in new §1; legacy §1 preserved verbatim per strict-clean)
- **§1 Contributions:** 1 of 4 items is theoretical companion (vs 2 of 6 in legacy); 3 of 4 items are framework-primary

The 39-line additive edit introduces the new framework-primary narrative without removing the legacy theorem-primary narrative; readers who prefer the legacy framing can still find it (preserved verbatim). The replacement will be applied by the Wave 297 P4+ paper-edit pass that the W297 P2 design doc designates as the executor.

---

## 6. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave297-p3-intro-rewritten.md` (this file)
- **prior docs cited:** wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave296-p1-architecture.md, wave296-p2-cache.md
- **source paper (legacy):** `docs/drafts/paper-flat-flattened.md` (pre-edit, 445 lines)
- **source paper (post-edit):** `docs/drafts/paper-flat-flattened.md` (484 lines, +39 lines)
- **legacy sections preserved:** Title, Abstract, §1 ¶1-¶4, §1 contributions (i)-(vi) — all verbatim
- **new sections appended:** Title (new), Abstract (new), §1 ¶1-¶4 (new), §1 contributions (i)-(iv) (new)
- **re-anchor notes:** 7 (1 title + 1 abstract + 4 §1 paragraphs + 1 contributions)
- **vendored NOT touched:** verified by `git diff --stat`
- **D.4 30/30:** verified, 95/95 passed
- **ruff 0:** verified, "All checks passed!"
- **mkdocs 0 warnings:** verified, exit_code=0

---

## 7. Honest summary

Wave 297 P3 applies the §1 Introduction + Abstract re-anchor from the Wave 297 P2 design doc to the canonical paper draft at `docs/drafts/paper-flat-flattened.md` per the Phase 2 design directive. The edit is **strictly additive** per Wave 268 strict-clean rule: legacy content preserved verbatim, re-anchor notes appended next to old paragraphs, new content appended at end of section.

The 39-line diff introduces:
- 1 title re-anchor note + 1 new title block (lines 3, 13-15)
- 1 abstract re-anchor note + 1 new abstract block (lines 11, 17-19)
- 4 §1 paragraph re-anchor notes + 1 new §1 4-paragraph block (lines 27, 31, 35, 39, 52-60)
- 1 contributions re-anchor note + 1 new 4-contribution list (lines 50, 62-67)

The new §1 narrative leads with the framework-reconstruction paradigm (4-paragraph structure: framework lead → related work → theoretical companion → validation). The new abstract leads with the framework-primary paradigm (5-sentence structure: framework lead → empirical → theoretical companion → positioning). The new contribution list has 4 items (was: 6) re-anchored to framework-primary (3) + theoretical companion (1).

All invariants preserved: D.4 30/30, ruff 0, mkdocs 0 warnings, vendored NOT touched, claims no drift, ADDITIVE only.

Sections 2-11 of the new 11-section structure are deferred to Wave 297 P4+ per the W297 P2 design's section-by-section re-anchor directive. This is the §1 + Abstract + Title re-anchor pass; subsequent waves will apply the same ADDITIVE re-anchor pattern to §2 Related Work, §3 Framework, §4 Scheduler Family, §5 Adapter Protocol, §6 Theoretical Lenses, §7 Empirical Results, §8 Reproducibility, §9 Limitations, §10 Future Work, and §11 Conclusion.
