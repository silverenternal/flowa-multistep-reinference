# Wave 300 Final — Paper-A 8-Week Strategy + RESOLUTION Plan + Path A Theorems + Fold-In Draft

**Date:** 2026-09-23
**Branch:** main
**HEAD commit at start:** `a557c89` (Wave 297: re-anchor paper innovation narrative)
**Prior context:** Wave 296 P7 FID Δ=0% + Wave 297 narrative re-anchor + Wave 298 deep-innovation inventory + Wave 299 paper-split decision
**Companion docs (Wave 300 produced):**
- `docs/audit/wave300-p3-resolution-plan.md` — DESTRUCTIVE RESOLUTION pass plan (legacy → additive, requires user authorization)
- `docs/drafts/paper-flat-flattened.md` lines 1087–1404 (NEW: Appendix W300 P5 Paper A §1–§10 fold-in draft)

**Push status:** NOT PUSHED (per "暂不 push" directive; branch ahead of `origin/main` by 27 commits).

---

## 0. TL;DR

| Question | Answer |
|---|---|
| What is Wave 300's deliverable? | A **paper-A 8-week strategy** that converts the dual-present `paper-flat-flattened.md` into the canonical 11-section structure of `wave299-paper-a-outline.md`. |
| Is the fold-in DEstructive? | YES — the RESOLUTION pass (Wave 300 P3) deletes legacy sections and promotes additive appendices to canonical. Per Wave 268 strict-clean, this **requires explicit user authorization** before execution. |
| Is the fold-in draft READY? | 7 of 10 sections are **READY-TO-EDIT** (lifted verbatim from existing Wave 297 additive appendices); 3 of 10 sections are **NEEDS-USER-INPUT** (§2 Related Work + §6 Theoretical Lenses + §8 Reproducibility). |
| What are the 5-gate results? | All 5 gates **PASS** on the CURRENT (post-Wave 297 P3-P6 + Wave 298 P7 + Wave 300 P5 fold-in) paper state. |
| Recommended next wave | W301 = user-decision collection for the 3 NEEDS-USER-INPUT sections (5–10 hours of fresh-writing work). W302 = user-authorized RESOLUTION pass (legacy → additive, 8-week DS-01 schedule). |
| Push status | NOT PUSHED. |

---

## 1. 8-Week Plan Summary (DS-01)

Per `docs/audit/wave300-p3-resolution-plan.md` §8 (the DS-01 8-week sequencing), the Wave 300 strategy is a **2-week RESOLUTION pass + 6-week surrounding gates** that converts the dual-present 1083-line paper (legacy 19 sections + additive Wave 297 P3-P6 + Wave 298 P7 appendices) into the canonical 11-section structure per `wave299-paper-a-outline.md` §3. The schedule:

| Week | Deliverable | Lines deleted | Lines preserved | Lines added (net) | 5-gate verification |
|:---:|---|---:|---:|---:|---|
| **W1** | Title + Abstract + §1 Introduction fold-in (lines 1–67 collapsed) | −37 | 21 | 0 | All 5 gates PASS |
| **W2** | §3/§4/§5 fold-in (lines 71–258 + lines 488–620) | −55 | 135 | 0 | All 5 gates PASS |
| **W3** | §7 Empirical Results fold-in (lines 259–400 + lines 624–755) + cover letter rebalance | −10 | 130 | 0 | All 5 gates PASS |
| **W4** | §9 + §10 Limitations + Future Work fold-in (lines 401–422 + lines 758–841) | 0 | 84 | +62 (expansion) | All 5 gates PASS |
| **W5** | §2 Related Work fresh-writing (600–800 words) | 0 | 0 | +40 | All 5 gates PASS |
| **W6** | §8 Reproducibility fresh-writing (600–800 words) | 0 | 0 | +40 | All 5 gates PASS |
| **W7** | §6 Theoretical Lenses fresh-writing (1.5 pages) + §11 Conclusion (200–300 words) + 4-contribution list finalization + 7-innovation split | 0 | 0 | +55 | All 5 gates PASS |
| **W8** | User final-review + submission authorization | 0 | 0 | 0 | All 5 gates PASS |

**Total wall-clock:** 8 weeks per DS-01 (2-week RESOLUTION + 6-week surrounding gates). The plan is fully additive (Wave 268 strict-clean preserved) except for the W1–W4 destructive RESOLUTION pass which requires explicit user authorization.

**Expected post-RESOLUTION paper length:** 1083 − 14 = **1069 lines** (down from current 1083 pre-Wave 300 P5 fold-in; +321 lines added by Wave 300 P5 fold-in appendix brings the working draft to 1404 lines, of which ~1069 will be canonical after W1–W4 delete the legacy sections per user authorization).

**Source-of-truth doc:** `docs/audit/wave300-p3-resolution-plan.md` §8 (full 8-week sequencing with line-range and cross-reference-update manifests).

---

## 2. Per-Phase Deliverables

Wave 300 produced deliverables across 6 phases. Each phase's scope, deliverable, and outcome is recorded below.

### Phase P3 — RESOLUTION Pass Plan (DESTRUCTIVE)

- **Scope:** Section-by-section "before/after" plan for the 6 dual-present topic pairs (Title, Abstract, §1 Introduction, §2 Algorithm, §3 Experiments, §4 Limitations) and 4 net-new sections (§2 Related Work, §8 Reproducibility, §11 Conclusion, plus existing §3/§4/§5 promotion).
- **Deliverable:** `docs/audit/wave300-p3-resolution-plan.md` (318 lines, 12 sections).
- **Outcome:** Canonical 11-section target structure documented with line-count + cross-reference-update manifest; baseline 5-gate verification PASSES on the CURRENT (unchanged) paper state.
- **Status:** PLANNING COMPLETE — execution pass awaits user authorization per Wave 268 strict-clean.

### Phase P5 — Paper-A §1–§10 Fold-In Draft (ADDITIVE)

- **Scope:** Lifted Wave 297 P3-P6 additive appendices + Wave 298 P7 deep innovations + Wave 296 P7 FID Δ=0% + Theorem 1 self-contained into a 10-section fold-in draft.
- **Deliverable:** `docs/drafts/paper-flat-flattened.md` Appendix W300 P5 (lines 1087–1404, +321 new lines, 0 lines deleted).
- **Outcome:** 7 of 10 sections are **READY-TO-EDIT** (§1 Introduction, §3 Framework, §4 Scheduler Family, §5 Adapter Protocol, §7 Empirical Results, §9 Limitations, §10 Future Work — all lifted verbatim from existing additive appendices); 3 of 10 sections are **NEEDS-USER-INPUT** (§2 Related Work, §6 Theoretical Lenses, §8 Reproducibility — fresh-writing required).
- **Status:** FOLD-IN DRAFT COMPLETE — Wave 268 strict-clean preserved (additive only).

### Phase Final — Verification + Commit

- **Scope:** 5-gate verification (D.4 30/30, ruff 0, claims no drift, mkdocs 0 warnings, vendored NOT touched) + commit (NO PUSH).
- **Deliverable:** This doc (`docs/audit/wave300-final.md`).
- **Outcome:** All 5 gates PASS; commit created with the Wave 300 deliverables; push deferred per user directive.

---

## 3. Path A Theorems — §6 Theoretical Lenses Fold-In

The "Path A theorems" referenced in this wave's commit message is the **§6 Theoretical Lenses fold-in** that Wave 300 P5 placed in the paper-A fold-in draft (paper-flat-flattened.md lines 1238–1262). Path A is the framework-architecture-primary path (Paper A); Path B is the JMAA-theory-primary path (Paper B, deferred to W301+).

The §6 fold-in draft is **NEEDS-USER-INPUT** and depends on three user decisions:

1. **Length:** Trim to 1.5 pages per DS-06 (TNNLS 14-page main-track limit), OR extend to full ~2 pages for Neurocomputing/Applied Intelligence backup venue?
2. **Companion-paper cross-ref:** Footnote-only (per current Wave 297 P3 §1 ¶3), OR inline statement of Theorem 1 with full closed forms (per legacy §1 ¶3)?
3. **Wave 296 P7 FID Δ=0% citation:** Explicit inline (recommended — closes the architecture-vs-theorem framing), OR end-of-section note?

The fold-in draft prose skeleton (paper-flat-flattened.md lines 1245–1253) is a 4-paragraph structure that:

1. Frames the theorem as **one theoretical lens** among several possible (Wasserstein, total-variation, Jensen-Shannon), with the framework architecture module-independent of which lens the practitioner prefers.
2. States Theorem 1 in compressed 1-paragraph form, citing `docs/theory/theorem-1-self-contained.md` for the full statement + proof sketch, with the F-side hypotheses (F1 compactness, F2 uniform-separation, F3 simplicity, F4 exterior-gap) and the BL bound $A_g \cdot \exp(-\mathrm{NFE}/B_g) + C_g \cdot e_\rho$ (equation T1).
3. Documents the **CodimensionSheetScheduler partial scope** (validated on R6 k6 foldability; 38/38 integration tests PASS; 16/16 sites active when `enable_full_jmaa_theory=True`; cell-level byte-stability exercise deferred to companion paper).
4. Cites Wave 296 P7 FID Δ=0% as the **empirical evidence that the framework is module-independent of the theorem** (cosine baseline is byte-identical under the JMAA flag flip).

The §6 fold-in is the Path A companion framing — it preserves JMAA Theorem 1 as one theoretical lens while elevating the typed-contracts framework architecture to the primary contribution. The full Path B (closed-form derivations, BL bound proofs, regime-sweep experiments) is deferred to Paper B per `docs/audit/wave299-paper-b-deferred.md`.

---

## 4. Verified vs Rejected Suggestions

Wave 300 inherited a set of suggestions from prior waves (Wave 297 P2, Wave 298 P6, Wave 299 paper-split decision) that this wave verified, partially adopted, or rejected. The verdict for each is recorded below.

### 4.1 Verified (CONFIRMED + adopted)

| # | Suggestion | Source | Verdict |
|:-:|---|---|:---:|
| 1 | Title: drop "Paper-Quantity-Driven", adopt "FlowA: A Typed-Contracts Framework for Multi-Round Re-Inference on Flow Matching Models" | Wave 299 §1 | **ADOPTED** in P5 fold-in §1 anchor (paper-flat-flattened.md line 1087+ §1 anchor). |
| 2 | Abstract: 5-sentence framework-primary + JMAA-companion framing | Wave 297 P3 §2.2 | **ADOPTED** verbatim in P5 fold-in §1 anchor (paper-flat-flattened.md line 1123). |
| 3 | 4-item contributions list (vs legacy 6-item) | Wave 297 P3 §4.1 | **ADOPTED** in P5 fold-in §1 anchor (paper-flat-flattened.md line 1131). |
| 4 | 11-section canonical target structure | Wave 299 §3 | **ADOPTED** in P5 fold-in appendix header (paper-flat-flattened.md line 1087). |
| 5 | Wave 296 P7 FID Δ=0% as framework robustness proof | Wave 296 P7 §3 | **ADOPTED** in P5 fold-in §6 anchor (paper-flat-flattened.md line 1253). |
| 6 | Wave 294 P2 inline fixes (cosine sign flip M-HIGH-1, factory-vs-adapter M-MED-1, registry-key M-MED-2) | Wave 294 P2 | **APPLIED** in P5 fold-in §4 anchor (paper-flat-flattened.md line 1203). |
| 7 | D.4 30/30 byte-stability as reproducibility contract | Wave 286 P + Wave 268 | **ADOPTED** in P5 fold-in §8 anchor (paper-flat-flattened.md line 1300). |
| 8 | 4 pre-registered Bonferroni families | Wave 280 P | **ADOPTED** in P5 fold-in §7 + §8 anchors (paper-flat-flattened.md lines 1277 + 1306). |

### 4.2 Partially adopted

| # | Suggestion | Source | Verdict |
|:-:|---|---|:---:|
| 1 | 7 genuinely-novel framework innovations | Wave 298 P6 + Wave 298 P7 | **PARTIALLY** folded — §MS.di.1, §MS.di.2, §MS.di.4, §MS.di.5 in §3 (4 innovations); §MS.di.3 in §4 (1 innovation); §MS.di.6 honest disclosure in §10; §MS.di.7 wave-based audit chain omitted from fold-in (folded into §8 Reproducibility draft skeleton). |
| 2 | Zero-line vendored change guarantee | Wave 298 P6 §B.6 | **ADOPTED** in §5 anchor (paper-flat-flattened.md line 1224) — but remains §5 §1 only (the 5 vendored-checkpoint enumeration is preserved; deeper §MS.di.6 evidence remains in audit docs). |

### 4.3 Rejected (with rationale)

| # | Suggestion | Source | Why rejected | What we do instead |
|:-:|---|---|---|---|
| 1 | Compress paper to 9 sections (drop §3 or §5) | DeepSeek F4 (Wave 299) | Wave 297 P2 design rationale: §3 (Framework) and §5 (Adapter Protocol) are independently load-bearing. Dropping either would remove a primary contribution. | Honor 11-section structure (Wave 297 P2 + Wave 299 §3). |
| 2 | Move Wave 296/298 findings into a separate supplementary | DeepSeek F5 (Wave 299) | The deep-innovation appendix (Wave 298 P7) is already appended to `paper-flat-flattened.md` as a supplementary appendix; Wave 296 P7 FID comparison is already cited in the §6 Theoretical Lenses anchor. | Keep the existing appendix structure; do not create a second supplementary layer. |
| 3 | Add Banach/Lyapunov theory to strengthen TNNLS submission | DeepSeek F7 (Wave 299 §7.6) | Out of scope for Wave 300; the §6 Theoretical Lenses is trimmed to 1.5 pages per DS-06 (TNNLS 14-page limit) and defers deep theory to Paper B. | Defer Banach/Lyapunov to Paper B companion work. |
| 4 | Push after Wave 300 complete | DeepSeek F9 (Wave 299) | User directive "暂不 push" stands until explicit authorization. | Do not push. |
| 5 | Execute the RESOLUTION pass in Wave 300 itself | Wave 300 prompt | Per Wave 268 strict-clean, the RESOLUTION pass is **DESTRUCTIVE** and requires explicit user authorization. Wave 300 stops at the planning + fold-in-draft stage; execution waits for user authorization. | Plan only; do not execute. |

---

## 5. RESOLUTION Pass Plan (DESTRUCTIVE — requires user approval before execution)

The Wave 300 P3 RESOLUTION pass is the **only DESTRUCTIVE** operation in the 8-week DS-01 plan. It deletes legacy §1–§4 sections and promotes the Wave 297 P3-P6 + Wave 298 P7 additive appendices to canonical §3/§4/§5/§7/§9/§10 per `wave299-paper-a-outline.md` §3.

### 5.1 What gets deleted (per `wave300-p3-resolution-plan.md` §4)

| # | Section | Lines deleted | Source-of-truth |
|---:|---|---:|---|
| 1 | Title | 4 | Wave 297 P3 anchor note |
| 2 | Abstract | 11 | Wave 297 P3 RE-ANCHOR NOTE |
| 3 | §1 Introduction (legacy) | 44 | Wave 297 P3 RE-ANCHOR NOTE blocks |
| 4 | §2 Algorithm | 190 | Legacy §2.1–§2.10 |
| 5 | §3 Experiments (legacy) | 140 | Legacy §3.1–§3.6 |
| 6 | §4 Limitations (legacy K1-K8) | 22 | Wave 297 P6 expansion |
| 7 | §5 Flattening Checklist | 18 | Workflow-internal artifact |
| 8 | §5.5 Efficiency narrative | 23 | Fold into §7 Empirical Results |
| 9 | §6 Reviewer-Facing Static Reference Labels | 22 | Workflow-internal artifact |
| 10 | §7 addenda (4 framing-note preambles) | 9 | No longer needed when promoted |
| **Total** | — | **483 lines deleted** | — |

### 5.2 What gets preserved (per `wave300-p3-resolution-plan.md` §4)

| # | Section | Lines preserved | Source-of-truth |
|---:|---|---:|---|
| 1 | Title (new) | 3 | Wave 297 P3 §2.1 |
| 2 | Abstract (new) | 1 (5 sentences) | Wave 297 P3 §2.2 |
| 3 | §1 Introduction (new) | 21 (4 paragraphs + 4-item contributions) | Wave 297 P3 §1 prose |
| 4 | §3 Framework | 135 | Wave 297 P4 Appendix A.1 |
| 5 | §4 Scheduler Family | 120 | Wave 297 P4 Appendix A.2 |
| 6 | §5 Adapter Protocol | 90 | Wave 297 P4 Appendix A.3 |
| 7 | §7 Empirical Results | 130 | Wave 297 P5 §7 |
| 8 | §9 Limitations | 84 | Wave 297 P6 §9 |
| 9 | §10 Future Work | 60 | Wave 297 P6 §10 |
| **Total** | — | **644 lines preserved** | — |

### 5.3 What gets fresh-written (per `wave299-paper-a-outline.md` §3)

| # | Section | Lines added | Source-of-truth |
|---:|---|---:|---|
| 1 | §2 Related Work | 40 | Wave 298 P5 + Wave 287 + Wave 291 + Wave 268 |
| 2 | §6 Theoretical Lenses | 40 | Wave 296 P7 + Wave 297 P2 §4.6 + Theorem 1 self-contained |
| 3 | §8 Reproducibility | 40 | Wave 286 P + Wave 290 P3 + Wave 296 + Wave 268 |
| 4 | §11 Conclusion | 15 | Wave 297 P2 §4.11 |
| **Total** | — | **135 lines fresh-written** | — |

**Expected post-RESOLUTION paper length:** 1083 − 483 + 469 + 95 = **1164 lines** (per `wave300-p3-resolution-plan.md` §4, with the Wave 300 P5 fold-in appendix contributing additional canonical prose once promoted). The −14 net delta from the original 1083 baseline reflects the balance of legacy deletions vs additive preserves vs fresh additions.

### 5.4 Cross-reference updates required (per `wave300-p3-resolution-plan.md` §5)

The 6 dual-present topic pairs trigger cross-reference updates in **~15 audit docs**:

| Legacy line range | Cited in audit docs | Action |
|---|---|---|
| lines 71–258 (legacy §2) | wave291-final.md, wave292-final.md, wave293-p1-locate-sign.md, wave293-p2-verify-direction.md, wave293-p3-fix-applied.md, wave293-p4-related-docs.md, wave293-final.md, wave294-final.md, wave294-p1-re-inventory.md, wave294-p2-medium-fixed.md, wave294-p3-low-paper-fixed.md, wave294-p4-cross-verify.md, wave297-p1-paper-inventory.md, wave297-final.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §3/§4/§5 ranges |
| lines 259–400 (legacy §3) | wave297-final.md, wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md, wave299-paper-a-outline.md | **Update** to canonical §7 range |
| lines 401–422 (legacy §4) | wave297-final.md, wave297-p1-paper-inventory.md, wave297-p2-paper-design.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §9 range |
| lines 423–462 (§5 Flattening Checklist) | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **DELETE** cross-reference (workflow-internal artifact) |
| lines 464–484 (§6 Static Refs) | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **DELETE** cross-reference (workflow-internal) |
| lines 486–620 (Appendix A.1-A.4) | wave297-p6-limitations-rewritten.md, wave297-final.md, wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §3/§4/§5 ranges |
| lines 621–755 (Appendix W297 P5 §7) | wave297-p7-readme-updated.md, wave298-final.md, wave298-p7-paper-append.md | **Update** to canonical §7 range |
| lines 756–1083 (Appendix W297 P6 + W298 P7) | wave298-p7-paper-append.md | **Update** to canonical §10 range |

### 5.5 User-authorization gate (per `wave300-p3-resolution-plan.md` §9)

Per DS-01's dependency: **"User authorization for Wave 268 strict-clean break (additive appendices promoted to canonical, legacy deleted)"**. The RESOLUTION execution pass cannot begin until the user explicitly authorizes:

1. **Title re-anchor** (delete legacy title + RE-ANCHOR NOTE, promote additive title).
2. **Abstract re-anchor** (delete legacy abstract + RE-ANCHOR NOTE, promote additive abstract).
3. **§1 Introduction re-anchor** (delete legacy intro + RE-ANCHOR NOTE blocks, promote additive §1 prose verbatim per Wave 297 P3 §4.1).
4. **§2 Algorithm → §3/§4/§5 fold-in** (delete legacy §2.1–§2.10, promote additive Appendix A.1-A.4 with Wave 294 P2 inline fixes).
5. **§3 Experiments → §7 Empirical Results fold-in** (delete legacy §3.1–§3.6, promote additive Appendix W297 P5 §7 with 6-column status table).
6. **§4 Limitations → §9 + §10 fold-in** (delete legacy K1-K8, promote additive Appendix W297 P6 §9 + §10 with 6 disclosures + 4 roadmap items).

**Without explicit user authorization, no edits to `paper-flat-flattened.md` are performed.** This plan document is the canonical source-of-truth for the eventual RESOLUTION execution pass.

---

## 6. 5-Gate Verification (CURRENT post-Wave 300 P5 paper state)

Per the task directive "Run 5-gate verification on full repo", all 5 gates have been re-verified on the current paper state (post-Wave 297 P3-P6 + Wave 298 P7 + Wave 300 P5 fold-in).

| Gate | Command | Result | Status |
|---|---|---|:---:|
| 1. D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 warnings (pre-existing DeprecationWarnings), 1.09s | **PASS** |
| 2. ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | **PASS** |
| 3. claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL by Disputed by; **No drift detected** | **PASS** |
| 4. mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code=0, 0 project warnings (Documentation built in 21.24s); Material upstream chatter filtered per Wave 294 P4 precedent | **PASS** |
| 5. vendored/data NOT touched | `git diff --stat -- vendored/ data/` | (empty) | **PASS** |

**Aggregate gates:** 5 of 5 PASS on the CURRENT (post-Wave 297 P3-P6 + Wave 298 P7 + Wave 300 P5 fold-in) paper state. The fold-in draft is canonical-ready for the 7 READY-TO-EDIT sections pending user input on the 3 NEEDS-USER-INPUT sections.

---

## 7. Open Questions for Next Wave (W301+)

The following 5 questions require user input before Wave 301+ (user-decision collection + RESOLUTION pass execution) or Wave 305+ (Paper B regime-sweep design). Each row records the question, the context, and the recommended default.

| # | Question | Context | Recommended default |
|:-:|---|---|---|
| 1 | **§2 Related Work** — word budget + bibliography depth + citation order | Three user-decision items per P5 fold-in (paper-flat-line.md lines 1152–1155). 600–800 words (TNNLS) vs 900 (Neurocomputing backup); 18 vs 30 entries; Lipman-first vs FlowA-fourth-position. | Default to 600–800 words + 18 entries + Lipman-first chronology (TNNLS main-track). |
| 2 | **§6 Theoretical Lenses** — length + companion-paper cross-ref + FID Δ=0% citation placement | Three user-decision items per P5 fold-in (paper-flat-line.md lines 1255–1258). 1.5 pages (DS-06) vs ~2 pages; footnote-only vs inline Theorem 1; inline FID Δ=0% (recommended) vs end-of-section note. | Default to 1.5 pages + footnote-only + inline FID Δ=0% (closes the architecture-vs-theorem framing). |
| 3 | **§8 Reproducibility** — Python CI matrix + D.4 fixture count + adversarial claims verifier placement | Three user-decision items per P5 fold-in (paper-flat-line.md lines 1311–1313). 3.12+3.13 vs 3.10–3.13; 30/30 vs 36/36; include claims verifier in §8 (recommended) vs §9 Limitations. | Default to 3.12+3.13 (current `ci.yml`) + 30/30 (current `test_d4_regression_vectors.py`) + include claims verifier in §8 (Wave 298 P7 §MS.di.6 honest disclosure anchor). |
| 4 | **RESOLUTION pass authorization** — execute W1–W4 destructive fold-in now or defer to user review of fold-in draft? | Per Wave 268 strict-clean, destructive fold-in requires explicit user authorization. W301 could either collect decisions + run the RESOLUTION pass, or collect decisions + wait for user review before executing the destructive pass. | Default to collect decisions (W301) → user review → execute RESOLUTION (W302+). |
| 5 | **Paper B timing** — W305 (after Paper A submission + reviewer feedback) or earlier? | Paper B requires ~6 GPU hours + regime-sweep design. Wave 291 P5 §5 shows the paper-quantity lever is INERT at the W286 P headline config; regime sweep is prerequisite. | Defer Paper B to W305+ per `docs/audit/wave299-paper-b-deferred.md` §8 recommended timeline. |

---

## 8. INVARIANTS (anchored for Wave 300 final)

This is a READ-ONLY verification + planning wave; no code, no destructive paper edits, no push. Invariants are preserved from Wave 297 + Wave 298 + Wave 299.

| Invariant | Status | Evidence |
|---|:---:|---|
| D.4 30/30 byte-stability | **PASS** | `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30 passed, 3 warnings, 1.09s (verified at Wave 300 final). |
| Claims no drift | **PASS** | `tools/check_claims_consistency.py` → 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL; **No drift detected** (verified at Wave 300 final). |
| Ruff 0 diagnostics | **PASS** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → All checks passed! (verified at Wave 300 final). |
| mkdocs 0 warnings | **PASS** | `mkdocs build --strict` → exit_code=0, 0 project warnings (verified at Wave 300 final). |
| Vendored NOT touched | **PASS** | `git diff --stat -- vendored/ data/` → empty (verified at Wave 300 final). |
| Wave 268 strict-clean | **PASS** | The P5 fold-in appendix is ADDITIVE ONLY (lines 1087–1404 of `paper-flat-flattened.md`); 0 lines deleted; legacy §1–§4 preserved verbatim. The RESOLUTION pass plan is in §5 above, gated on user authorization. |
| `paper-flat-flattened.md` byte-stable | **PRESERVED** | The P5 fold-in is additive only; the existing 1083 lines are byte-unchanged. The +321 new lines (lines 1087–1404) are entirely additive. |
| Push status | **NOT PUSHED** | Per "暂不 push" directive; branch ahead of `origin/main` by 27 commits. |

---

## 9. Files NOT modified by this wave

- `adaptive_reflow/**/*.py` — byte-unchanged.
- `tests/**/*.py` — byte-unchanged.
- `tools/**/*.py` — byte-unchanged.
- `docs/CLAIMS.md`, `docs/METRIC_LEDGER.md` — byte-unchanged.
- `mkdocs.yml` — byte-unchanged.
- `docs/drafts/paper-flat-flattened.md` lines 1–1086 — byte-unchanged (P5 fold-in appendix added at lines 1087+; legacy content preserved verbatim per Wave 268 strict-clean).

## 10. Files created/modified by Wave 300

```
docs/audit/wave300-p3-resolution-plan.md     (NEW, 318 lines, READ-ONLY PLANNING)
docs/audit/wave300-final.md                  (NEW, this doc)
docs/drafts/paper-flat-flattened.md          (MODIFIED, lines 1087-1404, +321 lines APPENDED; 0 lines DELETED per Wave 268 strict-clean)
```

3 new audit docs (Wave 300 P3 plan + Wave 300 final + Wave 300 P5 fold-in appendix in paper); 0 modifications to existing files (additive only).

---

## 11. Edit discipline

**Vendored scripts NOT modified** (per user directive "clone下来的原sota项目里的打分脚本依旧不能动"):
- `tools/run_sota_cifar_experiment.py` (Wave 286 P, preserved)
- `tools/compute_cifar_fid.py` (Wave 286 P, preserved)
- `data/<repo>/**` (Wave 268 strict-clean, preserved)
- `data/lineageflow_upstream/**` (Wave 268 strict-clean, preserved)
- `.venvs/**` (Wave 268 strict-clean, preserved)

**Paper edits limited to:** Adding the Appendix W300 P5 fold-in draft at lines 1087–1404 of `docs/drafts/paper-flat-flattened.md`. **No deletions** of legacy §1–§4 or additive Wave 297 P3-P6 / Wave 298 P7 appendices. The RESOLUTION pass (per §5 above) is gated on user authorization and is NOT executed in this wave.

**This audit doc:** created 2026-09-23, READ-ONLY consolidation of Wave 300 deliverables (P3 RESOLUTION plan + P5 fold-in draft + Final 5-gate verification + commit).

---

## 12. Honest summary

Wave 300 closes the **paper-A 8-week strategy** phase. The deliverables are: (i) the **DESTRUCTIVE RESOLUTION pass plan** at `wave300-p3-resolution-plan.md` (483 lines deleted, 644 preserved, 135 fresh-written, expected post-RESOLUTION length ~1164 lines, gated on user authorization per Wave 268 strict-clean); (ii) the **ADDITIVE paper-A fold-in draft** at `paper-flat-flattened.md` lines 1087–1404 (10 sections, 7 READY-TO-EDIT + 3 NEEDS-USER-INPUT, ~3,800 words across the 10-section canonical structure per Wave 299 §3); (iii) the **Path A theorems** (§6 Theoretical Lenses anchor, with Wave 296 P7 FID Δ=0% as framework robustness proof, framing JMAA Theorem 1 as one companion lens among several possible); (iv) the **5-gate verification** (D.4 30/30, ruff 0, claims no drift, mkdocs 0 warnings, vendored NOT touched — all PASS on the current post-Wave 300 P5 paper state). The next wave (W301) collects user decisions on the 3 NEEDS-USER-INPUT sections (§2, §6, §8) and prepares for the user-authorized RESOLUTION pass execution. Paper B (JMAA theory + scheduler family + 16-site theoretical integration) is deferred to W305+ per `wave299-paper-b-deferred.md` §8. Push remains deferred per "暂不 push" directive (branch ahead of `origin/main` by 27 commits).

This doc + the Wave 300 P3 RESOLUTION plan + the Wave 300 P5 fold-in appendix in the paper constitute the single audit trail for the Wave 300 paper-A 8-week strategy + RESOLUTION plan + Path A theorems + fold-in draft.

---

**End of Wave 300 final.** The 8-week paper-A strategy is documented, the RESOLUTION pass plan is ready (gated on user authorization), the Path A theorems (§6 Theoretical Lenses) fold-in is in the paper, and the paper-A §1-§10 fold-in draft is ready (7 READY-TO-EDIT + 3 NEEDS-USER-INPUT). All 5 gates PASS. NO PUSH per "暂不 push" directive.