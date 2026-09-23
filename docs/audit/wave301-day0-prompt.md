# Wave 301 — Day 0 Prompt: User Authorization for RESOLUTION Pass + Venue Lock

**Date:** 2026-09-23
**Mode:** READ-ONLY (no edits to `paper-flat-flattened.md` per Wave 268 strict-clean)
**Estimated user time:** 2-3 hours
**Author:** Wave 301 Day 0 prompt assembly agent
**Source-of-truth:** `docs/audit/wave300-p3-resolution-plan.md` (Wave 300 P3 RESOLUTION plan)
**Gate baseline:** All 5 gates PASS on current unchanged paper (D.4 30/30, ruff 0, claims no-drift, mkdocs strict 0 warnings, vendored untouched)

---

## 0. TL;DR (read once, then act)

You are about to do the ONLY user-input phase of the entire Wave 301 multi-day workflow. Three things require your explicit authorization before Days 1-3 (and beyond) can proceed:

1. **Confirm 6 dual-present pair decisions** in §1 below (each pair has a recommended canonical version; you confirm or override).
2. **Authorize Wave 268 strict-clean break** (the destructive-deletion gate that has blocked this work for weeks).
3. **Lock the venue decision** to TNNLS (with the reasoning the workflow agent added beyond the deepseek teacher's note).

After you sign off, the workflow agent takes over Days 1-3 and beyond without further user review except at the boundary-clearness check on Day 3 (Contributions + Abstract sanity check).

**Total wall-clock estimate after Day 0:** 8-10 days for 70-80% confidence submission-ready Paper A (compressed first draft by Day 3, full Path A prose-proofs in supplementary, IEEEtran polish Days 4-8) OR 12-15 days for 90%+ confidence with full Path A in main text. The teacher's "3-day submission-ready" framing is REJECTED as unrealistic — see §3 below.

---

## 1. RESOLUTION Decisions: 6 Dual-Present Topic Pairs (User Authorization Required)

The paper `docs/drafts/paper-flat-flattened.md` is currently in a **dual-present state** (1404 lines, legacy 19-section structure + 4 additive Wave 297/298 appendices + Wave 300 P5 fold-in draft). The Wave 297 P2 paper design specifies an **11-section canonical target structure** (14.0 pages, TNNLS-compatible).

The 6 dual-present topic pairs each have a recommended canonical version (legacy → delete, additive → promote, or merge). Please **confirm or override** each decision in the table below.

### Decision Table

| # | Pair | Lines | Recommended canonical | User decision |
|---:|---|---|---|---|
| 1 | **TITLE** | legacy lines 1-4 vs additive lines 13-15 | **Adopt Wave 297 additive**: "FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints." Drop legacy title + RE-ANCHOR note (−4 lines). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 2 | **ABSTRACT** | legacy lines 7-12 vs additive lines 17-19 | **Adopt Wave 297 additive** 5-sentence abstract (framework-reconstruction primary, JMAA as one theoretical companion). Drop legacy 9-line theorem-first abstract + RE-ANCHOR NOTE (−10 lines). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 3 | **§1 INTRODUCTION** | legacy lines 23-67 vs additive lines 52-67 (4-item contributions) | **Adopt additive** 4-paragraph framework-reconstruction opening + 4-item contributions list. Drop legacy 4-paragraph theorem-first intro + 6-item contributions list + RE-ANCHOR NOTE blocks (−23 lines net). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 4 | **§2 ALGORITHM** | legacy lines 71-258 vs additive Appendix A.1-A.4 lines 488-620 | **Adopt additive as canonical §3 Framework + §4 Scheduler Family + §5 Adapter Protocol** per Wave 297 P2 11-section structure. Drop legacy §2.1-§2.10 tables + discussion + audit sub-sections (~−55 lines net). **SPECIAL**: FLIP cosine closed-form sign in Table 2.2 from (1 − cos) to (1 + cos)/2 per Wave 294 P2 M-HIGH-1 (CRITICAL — currently mis-aligned with code). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 5 | **§3 EXPERIMENTS** | legacy lines 259-400 vs additive Appendix W297 P5 §7 lines 624-755 | **Adopt additive** 6-column systematic-evidence status table (STRONG/PARTIAL/UNDERPOWERED/BLOCKED/REGRESSES rubric) as canonical §7 Empirical Results. Drop legacy 12-column audit-row §3.1-§3.6 + Figure 4 + head-to-head narrative (~−10 lines net). Preserve legacy §3.4 5-arm ablation verbatim, fold into additive §7.3 statistical methodology block. | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 6 | **§4 LIMITATIONS** | legacy lines 401-422 K1-K8 vs additive Appendix W297 P6 §9+§10 lines 758-841 | **Adopt additive** §9 Limitations + §10 Future Work per Wave 297 P6 design. Drop legacy 8 K-dimensions K1-K8 narrative (~22 lines). Preserve additive 6-disclosure §9.1.1-§9.1.6 + 4-item roadmap §10.1.1-§10.1.4 (+62 lines net, the only expansion in the plan). | ☐ CONFIRM / ☐ OVERRIDE: __________ |

### Special sub-decisions (also require your authorization):

| Decision | Default recommendation | User decision |
|---|---|---|
| **§6 Theoretical Lenses** (current lines 1238-1263) | **DROP entirely** — keeps Paper A boundary clean for Paper B. Per teacher "Paper A 不包含 JMAA" rule. Alternatively fold into §1 as one companion paragraph. | ☐ DROP entirely / ☐ Fold into §1 as companion paragraph |
| **§10 Future Work** (current lines 1344-1366) | **DROP entirely** — teacher dropped it. Fold into §8 Limitations instead. | ☐ DROP / ☐ Fold into §8 Limitations |
| **Figure count for Paper A** | **3-4 figures + 2-3 tables** (stays within TNNLS 14-page budget). Alternatives: 5-6 figures (exceeds budget). | ☐ 3-4 figures + 2-3 tables / ☐ Other: __________ |
| **Path A prose-proof depth** | **3 prose-proof sketches in main text** (protocol algebra closure + SM byte-determinism + ledger integrity); full 6-8 lemma proofs in supplementary. Alternatively: full Path A in main text (adds 6-10 days to timeline). | ☐ 3 sketches main + full proofs supplementary / ☐ Full proofs main text |

### Cumulative deletion count (if all 6 confirmed as recommended)

- **Total lines deleted:** 483 (legacy blocks)
- **Total lines preserved:** 469 (additive promotions)
- **Net-new sections added:** +95 (§2 Related Work 40 + §8 Reproducibility 40 + §11 Conclusion 15)
- **Net delta:** −14 lines (1083 → 1069, but accounting for Wave 297/298 additions now in canonical position)
- **Current actual paper length:** 1404 lines (includes Wave 298 P7 + Wave 300 P5 fold-in content)
- **Expected post-RESOLUTION length:** ~1069 lines (legacy gone, additive promoted, fresh sections added)

---

## 2. Wave 268 Strict-Clean Break: User Authorization

Per `docs/audit/wave300-p3-resolution-plan.md` §9, the RESOLUTION execution pass **CANNOT begin** until you explicitly authorize the Wave 268 strict-clean break. This unlocks **8 destructive deletion steps** (one per audit-doc fingerprint):

1. **Title legacy block deletion** (4 lines)
2. **Abstract legacy block deletion** (11 lines)
3. **§1 Introduction legacy 4 paragraphs + 6-item contributions deletion** (44 lines)
4. **§2 Algorithm legacy 10 sub-sections deletion** (~190 lines)
5. **§3 Experiments legacy 6 sub-sections deletion** (~140 lines)
6. **§4 Limitations legacy K1-K8 deletion** (22 lines)
7. **§5 Flattening Checklist deletion** (18 lines, workflow-internal)
8. **§5.5 Efficiency narrative + §6 Static Reference Labels deletion** (45 lines, workflow-internal artifacts)

**Without your explicit authorization, no edits to `paper-flat-flattened.md` are performed** — the entire Days 1-3 (and beyond) workflow is blocked at step 0.

### Authorization prompt:

> **I, [your name], authorize the Wave 268 strict-clean break for the Wave 301 RESOLUTION pass on `docs/drafts/paper-flat-flattened.md`. I confirm the 6 dual-present pair decisions in §1 above (or have specified overrides). I understand that 483 lines will be deleted, 469 lines promoted to canonical position, and 95 lines of fresh content added (3 new sections). The destructive deletions are irreversible without git history; I have reviewed the Wave 300 P3 RESOLUTION plan and accept the cumulative risk. I authorize the workflow agent to execute Days 1-3 per the Wave 300 P3 §8 sequencing without further user review except at the Day 3 boundary-clearness check.**
>
> Signature: _____________________ Date: 2026-09-23

(Please copy this into a confirmation message and add your name/signature, OR provide equivalent text-based authorization in your reply.)

---

## 3. Venue Decision: TNNLS (with extended reasoning)

The deepseek teacher's note said: "target TNNLS, not ICLR, because ICLR有互审要求 and you're an undergraduate who likely doesn't qualify." The workflow agent has verified the teacher's recommendation is **correct**, but the reasoning is stronger than the teacher stated. Here are the **three ICLR 2027 blockers the teacher missed**:

1. **ICLR 2027 abstract deadline was Sep 18, 2026 AOE** — already lapsed 5 days ago. Official policy: "no exceptions for missing the abstract deadline." Without prior abstract registration on OpenReview, you cannot submit a paper even if you meet the Sep 25 full-paper deadline.
2. **ICLR 2027 reciprocal-reviewing is stricter than stated** — requires an accepted full paper at ICLR/NeurIPS/ICML/CVPR/ICCV/ECCV/etc as co-author. Workshops, tiny papers, blog posts, system demos, industry papers, position papers do NOT qualify. "New author" exemption caps at 1 submission; last cycle 25% of "no-reviewer" submissions were desk-rejected and acceptance rate was ~50% of full-PC-author baseline.
3. **All authors need OpenReview profiles by Sep 18, 2026** — new profiles without institutional email "can take up to two weeks to be moderated." Separate risk layer.

**Net assessment:** ICLR 2027 is effectively unreachable from this starting point because (a) the Sep 18 abstract deadline has already lapsed and (b) the reciprocal-reviewing qualification is unlikely to be met by an undergraduate with no accepted papers at qualifying venues.

### Venue Lock (please confirm):

| Decision | Recommendation | User decision |
|---|---|---|
| **Primary target** | **TNNLS** (IEEE Transactions on Neural Networks and Learning Systems) — rolling submission via ScholarOne, no abstract gate, no reciprocal-review requirement, 14-page total limit that fits the 11-section outline. Recent LetPub data: 3-5 months to first decision (Q4 2026 submit → Q1-Q2 2027 first decision realistic). | ☐ CONFIRM TNNLS / ☐ Other: __________ |
| **Backup target** | **ICLR 2028** (Sept 2027 deadline assumed) — realistic ICLR target once you graduate or add a PC-affiliated co-author. Building a TNNLS publication first is the prerequisite for ICLR reciprocity. | ☐ CONFIRM ICLR 2028 as backup / ☐ Other: __________ |
| **ICLR 2027** | **DROP entirely** — abstract deadline already past, reciprocal-review gate blocks single-author undergraduate submission. Stop ALL ICLR 2027 preparation work immediately. | ☐ CONFIRM drop ICLR 2027 / ☐ Other: __________ |

### Important correction to the teacher's framing:

The teacher stated the paper is "6475 words in 10 sections." The **actual paper state** is:
- `docs/drafts/paper-flat-flattened.md`: **1404 lines / ~36027 words / 19 legacy sections + 4 additive appendices + Wave 300 P5 fold-in draft**
- This is **~5x larger** than the teacher's stated 6475 words
- Every page-budget calculation in the teacher's 3-day plan is off by ~5x
- Wave 300 P3 self-estimates 8 weeks for the RESOLUTION + fresh-writing load; 3 days is not feasible as "submission-ready"

This affects your decision-making on the **timeline feasibility** question — see §4 below.

---

## 4. Timeline Reality Check: 3-Day vs 8-10 Day vs 12-15 Day

The deepseek teacher proposed a 3-day wall-clock: Day 0 user decision + Day 1 RESOLUTION + Day 2 Path A theory + Day 3 Paper A full draft. **The workflow agent has REJECTED this as "submission-ready Paper A"** based on the following evidence:

| Factor | Teacher's claim | Actual state |
|---|---|---|
| Paper word count | "6475 words / 10 sections" | 36027 words / 1404 lines / 19+4+fold-in sections |
| Day 1 RESOLUTION | 8-10 hours | Wave 300 P3 self-estimates 8 weeks for full RESOLUTION + fresh-writing + typesetting |
| Day 2 Path A theory | 10-12 hours | Wave 300 P2 self-estimates 12 working days for 6-8 Path A lemmas |
| Day 3 IEEEtran typesetting | "8-10 hours" | Typical IEEEtran conversion is 14-22 hours; 8-10h slot leaves zero margin |
| Path B appendix | "Day 9 only" | Wave 300 P3 self-estimates 5-7 days for Path B conditional appendix |
| User authorizations | "1 Day 0 sign-off" | Wave 268 strict-clean requires 8 destructive-deletion authorizations |
| Fresh-writing load | "All sections ready" | 3 sections (§2 Related Work 600-800w + §8 Reproducibility 600-800w + §11 Conclusion 200-300w = 1400-1900w) need fresh-writing |

### Recommended realistic timeline (8-10 days for 70-80% confidence submission-ready):

| Day | Deliverable | User review |
|:---:|---|---|
| 0 (today, 2-3h) | **You**: Confirm 6 dual-present pair decisions + authorize Wave 268 strict-clean break + lock TNNLS venue | **YES — Day 0 sign-off** |
| 1 | Agent: RESOLUTION pass executed; paper collapses from 1404 → ~1069 lines; 5-gate verification re-run | None |
| 2 | Agent: §2 Related Work + §8 Reproducibility + §11 Conclusion fresh-writing (1400-1900 words); Path A 3 prose-proof sketches | None |
| 3 | Agent: Structure lock + §1+§3-§7 prose edit pass; §6 Theoretical Lenses dropped (per teacher rule); CLAIMS.md re-anchored | **YES — boundary-clearness check on Contributions + Abstract** |
| 4 | Agent: IEEEtran (TNNLS template) conversion; bibliography.bib | None |
| 5 | Agent: Figure/table polish + supplementary material (full Path A prose-proofs, §6 Theoretical Lenses as appendix only, all clearly labeled "not main contribution") | None |
| 6 | Agent: Reference list finalization + cover letter + author bios template | **YES — author bio background input** |
| 7 | Agent: 5-gate final verification + Wave 268 strict-clean audit + final commit | None |
| 8 | Agent: ScholarOne submission package assembly + dry-run upload | **YES — final submission-readiness check + copyright/DORA workflow** |
| 9 | Agent: Paper B skeleton (separate directory, §1 Introduction + 10-experiment list, no Paper B prose) | None |
| 10 | Agent: TNNLS first-decision timeline planning + Paper B authorization queue | None |

### Alternative 12-15 day timeline (90%+ confidence with full Path A in main text):

Same as above but Days 2-5 swap Path A sketches for full Path A in main text (adds 6-10 days).

### Timeline selection (please confirm):

| Decision | Recommendation | User decision |
|---|---|---|
| **Timeline** | **8-10 day plan** — 70-80% confidence submission-ready; 3 Path A sketches in main text + full proofs in supplementary | ☐ 8-10 day plan / ☐ 12-15 day plan / ☐ Other: __________ |

---

## 5. STOP POINT (after Day 0 sign-off)

After you complete §1 (6 pair table) + §2 (Wave 268 authorization) + §3 (venue lock) + §4 (timeline selection), the workflow agent takes over Days 1-3+ without further user review. The agent will:

1. **Wait** for your Day 0 sign-off message before any edits to `paper-flat-flattened.md`.
2. **Execute** Days 1-3 per the timeline selected in §4.
3. **Re-engage** you at Day 3 for the boundary-clearness check on Contributions + Abstract.
4. **Re-engage** you at Day 6 for author bio background input.
5. **Re-engage** you at Day 8 for final submission-readiness check.

**If you do NOT sign off Day 0, the entire workflow is blocked at step 0.** No edits will be made; the agent will not proceed.

---

## 6. Baseline 5-Gate Status (Current Unchanged Paper)

| Gate | Command | Result | Status |
|---|---|---|:---:|
| 1. D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 warnings (pre-existing DeprecationWarnings), 6.80s | **PASS** |
| 2. ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | **PASS** |
| 3. mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code=0, 0 project warnings (Documentation built in 21.82s) | **PASS** |
| 4. claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL by Disputed by; **No drift detected** | **PASS** |
| 5. vendored/data NOT touched | `git diff --stat -- vendored/ data/` | (empty) | **PASS** |

**Baseline status:** All 5 gates **PASS** on the CURRENT (unchanged) paper-flat-flattened.md. The baseline establishes that the dual-present state is currently verifiable and that any RESOLUTION-pass execution must maintain all 5 gates per commit.

**Paper state snapshot:**
- File: `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-flat-flattened.md`
- Length: 1404 lines (vs teacher's stated equivalent of ~6475 words = ~1083 lines at 6 words/line)
- Sections: 23 H2 sections (19 legacy + 4 additive appendices W297 P4/P5/P6 + W298 P7 + Wave 300 P5 fold-in §1-§10)
- Dual-present pairs: 6 (Title, Abstract, §1 Intro, §2 Algorithm, §3 Experiments, §4 Limitations)
- Wave 268 strict-clean: ACTIVE — no edits to paper-flat-flattened.md without explicit user authorization

---

## 7. Files referenced (READ-ONLY)

- **Source-of-truth for RESOLUTION plan:** `docs/audit/wave300-p3-resolution-plan.md` (320 lines)
- **Source-of-truth for canonical structure:** `docs/audit/wave299-paper-a-outline.md` §3 (11-section target)
- **Source-of-truth for §1 prose:** `docs/audit/wave297-p3-intro-rewritten.md` (apply verbatim)
- **Source-of-truth for §3 Framework:** `docs/audit/wave297-p4-framework-rewritten.md`
- **Source-of-truth for §7 Empirical Results:** `docs/audit/wave297-p5-empirical-rewritten.md`
- **Source-of-truth for §9+§10 Limitations+Future Work:** `docs/audit/wave297-p6-limitations-rewritten.md`
- **Source-of-truth for deep innovations:** `docs/audit/wave298-p7-paper-append.md` (Code #1-#5 + Method #1-#2)
- **Source-of-truth for inline fixes:** `docs/audit/wave294-p2-medium-fixed.md` (1 HIGH + 2 MEDIUM)
- **Source-of-truth for venue decision:** ICLR 2027 Author Guidelines (iclr.cc/Conferences/2027/AuthorGuidelines); ICLR 2027 Submission Policies Blog (blog.iclr.cc/2026/09/02/submission-policies-for-iclr-2027); TNNLS ScholarOne portal (mc.manuscriptcentral.com/tnnls)

---

**End of Wave 301 Day 0 Prompt.** Awaiting your confirmation of §1 (6 pair decisions) + §2 (Wave 268 authorization) + §3 (venue lock) + §4 (timeline selection). The workflow agent will not proceed without Day 0 sign-off.