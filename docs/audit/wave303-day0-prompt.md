# Wave 303 — Day 0 Prompt: User Authorization for 14-Day TNNLS Plan

**Date:** 2026-09-23
**Mode:** READ-ONLY (no edits to `paper-flat-flattened.md` per Wave 268 strict-clean)
**Estimated user time:** 2-3 hours
**Author:** Wave 303 Day 0 prompt assembly agent
**Source-of-truth:** `docs/audit/wave303-day0-14-plan.md` (the 14-day plan this prompt authorizes)
**Gate baseline:** All 5 gates PASS on current unchanged paper (verified 2026-09-23)

---

## 0. TL;DR (read once, then act)

You are about to do the ONLY user-input phase of the entire Wave 303 14-day workflow. Eight things require your explicit authorization before D1-D14 can proceed:

1. **Confirm 6 dual-present pair decisions** in §1 below (each pair has a recommended canonical version; you confirm or override).
2. **Authorize Wave 268 strict-clean break** (the destructive-deletion gate that has blocked this work for weeks).
3. **Lock the venue decision** to TNNLS (with the ICLR 2027 blockers DeepSeek + Wave 301 enumerated).
4. **Confirm the 14-day timeline** (`docs/audit/wave303-day0-14-plan.md`, D0-D14 with 4 review points at D3/D6/D10/D13).
5. **Confirm §6 rename** from "Theoretical Lenses" to "Framework Properties" (DeepSeek §四).
6. **Confirm the 4-contribution wording** (DeepSeek §五: framework reconstruction + formal properties + empirical + reproducibility).
7. **Confirm §6 Theoretical Lenses drop entirely** (JMAA → Paper B companion).
8. **Confirm §10 Future Work disposition** (drop entirely or fold into §8 Limitations).

After you sign off, the workflow agent takes over D1-D14 without further user review except at the 4 explicit boundary points (D3, D6, D10, D13).

**Total wall-clock estimate after D0:** 14 days from D0 (2026-09-24) to TNNLS submission (2026-10-08). TNNLS acceptance probability 35-45% (40-50% if engineering reproducibility contribution is emphasized).

---

## 1. RESOLUTION Decisions: 6 Dual-Present Topic Pairs (User Authorization Required)

The paper `docs/drafts/paper-flat-flattened.md` is currently in a **dual-present state** at **1404 lines / 36027 words / 23 H2 sections** (7 legacy H2 sections + 4 Wave 297/298 additive appendices + Wave 300 P5 fold-in §1-§10). The Wave 303 14-day plan targets an **11-section canonical TNNLS structure** (8500-word main text + supplementary, ≤ 14 IEEEtran pages).

The 6 dual-present topic pairs each have a recommended canonical version (legacy → delete, additive → promote, or merge). Please **confirm or override** each decision in the table below.

### Decision Table

| # | Pair | Lines | Recommended canonical | User decision |
|---:|---|---|---|---|
| 1 | **TITLE** | legacy lines 1-4 vs additive lines 13-15 | **Adopt Wave 297 additive**: "FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints." Drop legacy title + RE-ANCHOR note (−4 lines). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 2 | **ABSTRACT** | legacy lines 7-12 vs additive lines 17-19 | **Adopt Wave 297 additive** 5-sentence abstract (framework-reconstruction primary, JMAA → Paper B per DeepSeek). Drop legacy 9-line theorem-first abstract + RE-ANCHOR NOTE (−10 lines). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 3 | **§1 INTRODUCTION** | legacy lines 23-67 vs additive lines 52-67 (4-item contributions) | **Adopt additive** 4-paragraph framework-reconstruction opening + 4-item contributions list. Drop legacy 4-paragraph theorem-first intro + 6-item contributions list + RE-ANCHOR NOTE blocks (−23 lines net). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 4 | **§2 ALGORITHM** | legacy lines 71-258 vs additive Appendix A.1-A.4 lines 488-620 | **Adopt additive as canonical §3 Framework + §4 Scheduler Family + §5 Adapter Protocol** per Wave 297 P2 11-section structure. Drop legacy §2.1-§2.10 tables + discussion + audit sub-sections (~−55 lines net). **SPECIAL**: FLIP cosine closed-form sign in Table 2.2 from (1 − cos) to (1 + cos)/2 per Wave 294 P2 M-HIGH-1 (CRITICAL — currently mis-aligned with code). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 5 | **§3 EXPERIMENTS** | legacy lines 259-400 vs additive Appendix W297 P5 §7 lines 624-755 | **Adopt additive** 6-column systematic-evidence status table (STRONG/PARTIAL/UNDERPOWERED/BLOCKED/REGRESSES rubric) as canonical §7 Empirical Results. Main text shows only **5 STRONG/PARTIAL cells (R1/R2/R3/R5c/R6)** per DeepSeek §一; remaining 6 cells → supplementary. Drop legacy 12-column audit-row §3.1-§3.6 + Figure 4 + head-to-head narrative (~−10 lines net). | ☐ CONFIRM / ☐ OVERRIDE: __________ |
| 6 | **§4 LIMITATIONS** | legacy lines 401-422 K1-K8 vs additive Appendix W297 P6 §9+§10 lines 758-841 | **Adopt additive** §9 Limitations + §10 Future Work per Wave 297 P6 design. Drop legacy 8 K-dimensions K1-K8 narrative (~22 lines). Preserve additive 6-disclosure §9.1.1-§9.1.6 + 4-item roadmap §10.1.1-§10.1.4 (+62 lines net, the only expansion in the plan). | ☐ CONFIRM / ☐ OVERRIDE: __________ |

### Special sub-decisions (also require your authorization):

| Decision | Default recommendation | User decision |
|---|---|---|
| **§6 Theoretical Lenses** (current lines 1238-1263) | **DROP entirely** — keeps Paper A boundary clean for Paper B. Per DeepSeek §四 "Paper A 不包含 JMAA". JMAA Theorem 1 + 4 closed-form derivations migrate to Paper B companion paper. | ☐ DROP entirely / ☐ Keep as brief "Framework Properties" intro / ☐ Other: __________ |
| **§6 rename** | **RENAME** from "§6 Theoretical Lenses" to "**§6 Framework Properties**" (DeepSeek §四). Holds 3 Path A lemmas: composition closure + byte-deterministic state machine + tamper-evident ledger. | ☐ CONFIRM rename / ☐ Other title: __________ |
| **§10 Future Work** (current lines 1344-1366) | **DROP entirely** — fold into §8 Limitations. Per DeepSeek §一. | ☐ DROP / ☐ Fold into §8 Limitations / ☐ Keep as §10 |
| **§1 contribution wording** (lines 64-67) | **APPEND additive block** below Wave 297 P2 list (preserve verbatim per Wave 268 strict-clean): "### TNNLS contribution list (DeepSeek teacher proposal, additive)" containing 4 contributions — (i) Framework-level reconstruction, (ii) Formal framework properties (3 lemmas), (iii) Cross-domain empirical validation (5 main + 6 supp), (iv) Engineering reproducibility (D.4 30/30 + 6-gate CI + vendor purity). JMAA Theorem 1 removed from §1 contribution list. | ☐ APPEND additive block / ☐ OVERRIDE W297 P2 wording / ☐ Other: __________ |
| **Figure count for Paper A** | **3-4 figures + 2-3 tables** (stays within TNNLS 14-page budget). Alternatives: 5-6 figures (exceeds budget). | ☐ 3-4 figures + 2-3 tables / ☐ Other: __________ |
| **Path A scope** | **3 lemmas at intermediate depth** (composition closure 2 days + SM byte-determinism 2 days + ledger tamper-evidence 1 day = 5 agent-days compressed to 3 wall-clock days via 3 parallel agents). Full 6-8 lemma proofs → supplementary. Per DeepSeek §三. | ☐ 3 lemmas main + full proofs supp / ☐ 6-8 lemmas main (adds 5+ days) / ☐ Other: __________ |

### Cumulative deletion count (if all 6 confirmed as recommended)

- **Total lines deleted:** ~474 (legacy blocks) + ~11000 words (legacy + §6 + workflow-internal)
- **Total lines preserved:** ~469 (additive promotions)
- **Net-new sections added at D10:** ~+2100 words (§2 Related Work 700 + §8 Reproducibility 600 + §11 Conclusion 250 + §6 Framework Properties 700 = 2250, minus trim)
- **Net delta:** ~−139 lines (1404 → ~1301 by D6, ~+200 by D10 → ~1500 by D11)
- **Target main text word count at D10:** ~7700 (under 8500 target with ~800-word buffer for IEEEtran expansion)

---

## 2. Wave 268 Strict-Clean Break: User Authorization

Per `docs/audit/wave300-p3-resolution-plan.md` §9 and Wave 268 strict-clean rule (DS-01), the Wave 303 RESOLUTION execution pass **CANNOT begin** until you explicitly authorize the Wave 268 strict-clean break. This unlocks **6 destructive deletion steps + 5 inline corrections** across D1-D6:

1. **D1 Pair 1 Title deletion** (4 lines)
2. **D2 Pair 2 Abstract deletion** (11 lines)
3. **D3 Pair 3 §1 Introduction deletion** (44 lines)
4. **D4 Pair 4 part A §2 Algorithm + §3/§4/§5 promotion** (190 lines deleted, 135 promoted; Wave 294 P2 inline fixes applied)
5. **D5 Pair 4 part B §3 Experiments + §7 promotion + §5/§6 workflow-internal cleanup** (140 + 63 = 203 lines deleted, 130 promoted)
6. **D6 Pair 5+6 §4 Limitations + §9/§10 promotion + framing preambles + §6 rename placeholder** (22 lines deleted, 84 promoted)
7. **D10 §6 trim + 4 contributions + §2/§8/§11 insertions + cross-ref updates** (~104 line-range updates across ~19 audit docs)

**Without your explicit authorization, no edits to `paper-flat-flattened.md` are performed** — the entire D1-D14 workflow is blocked at step 0.

### Authorization prompt:

> **I, [your name], authorize the Wave 268 strict-clean break for the Wave 303 14-day TNNLS submission plan on `docs/drafts/paper-flat-flattened.md`. I confirm the 6 dual-present pair decisions in §1 above (or have specified overrides). I confirm the 8 sub-decisions (special sub-decisions table). I understand that ~474 legacy lines will be deleted, ~469 additive lines promoted to canonical position, ~2100 words of fresh content added (§2/§8/§11 + §6 trim), and ~104 cross-reference updates applied across ~19 audit docs. The destructive deletions are irreversible without git history; I have reviewed the Wave 303 14-day plan at `docs/audit/wave303-day0-14-plan.md` and accept the cumulative risk. I authorize the workflow agent to execute D1-D14 per the Wave 303 §1 timeline with 4 explicit user review boundaries (D3, D6, D10, D13). TNNLS submission target: 2026-10-08.**
>
> Signature: _____________________ Date: 2026-09-23

(Please copy this into a confirmation message and add your name/signature, OR provide equivalent text-based authorization in your reply.)

---

## 3. Venue Decision: TNNLS (with extended reasoning)

The DeepSeek teacher's note said: "target TNNLS, not ICLR, because ICLR有互审要求 and you're an undergraduate who likely doesn't qualify." The Wave 301 verification confirmed the teacher's recommendation is **correct**, but the reasoning is stronger than the teacher stated. Here are the **three ICLR 2027 blockers the teacher missed**:

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
- `docs/drafts/paper-flat-flattened.md`: **1404 lines / 36027 words / 23 H2 sections** (verified at 2026-09-23 baseline)
- This is **~5x larger** than the teacher's stated 6475 words
- The Wave 303 14-day schedule accounts for this: D1-D6 delete ~14000 words (legacy + workflow-internal), D10 inserts ~2100 fresh words → ~7700 words main text (under 8500 target)

This affects your decision-making on the **timeline feasibility** question — see §4 below.

---

## 4. Timeline Reality Check: Wave 303 14-Day Plan (DeepSeek + Wave 303 corrections)

The Wave 303 14-day plan integrates DeepSeek's 14-day structure with Wave 301 + Wave 303 verification corrections (notably: D9-D10 = 2 days for full-draft assembly, not DeepSeek's 1-day D9). Total: **14 wall-clock days from D0 user authorization to TNNLS submission**.

### Timeline summary (D0-D14):

| Day | Date | Phase | Agent work | User review |
|:---:|:---:|---|---|:---:|
| D0 | 2026-09-24 | Day 0 user authorization | Read this prompt, decide 6 pairs, authorize Wave 268 strict-clean break, lock TNNLS, confirm 14-day timeline, confirm §6 rename, confirm 4-contribution wording, confirm JMAA → Paper B, confirm §10 disposition | **YES — 2-3h** |
| D1 | 2026-09-25 | RESOLUTION Part 1 — Pair 1 (Title) | Delete legacy title (L1-4); promote Wave 297 P2 title (L13-15); 5-gate verify | No |
| D2 | 2026-09-26 | RESOLUTION Part 1 — Pair 2 (Abstract) | Delete legacy abstract (L7-12); promote Wave 297 P2 5-sentence abstract (L17-19); 5-gate verify | No |
| D3 | 2026-09-27 | RESOLUTION Part 1 — Pair 3 (§1 Intro) | Delete legacy §1 (L23-50); promote Wave 297 P3 §1 (L52-67); 5-gate verify | **YES — D3 boundary clearness check** |
| D4 | 2026-09-28 | RESOLUTION Part 2 — Pair 4 part A | Delete legacy §2 (L71-258); promote W297 P4 A.1/A.2/A.3 (L488-594) to §3/§4/§5; Wave 294 P2 cosine sign flip | No |
| D5 | 2026-09-29 | RESOLUTION Part 2 — Pair 4 part B | Delete legacy §3 (L259-400); promote W297 P5 §7 (L624-755) to canonical §7; delete §5/§6 workflow-internal (L423-484); 5 STRONG/PARTIAL cells in main | No |
| D6 | 2026-09-30 | RESOLUTION Part 3 — Pairs 5+6 + cover letter | Delete legacy §4 (L401-422); promote W297 P6 §9+§10 (L758-815); rename §6 placeholder; cover letter rebalance | **YES — D6 Path A start review** |
| D7 | 2026-10-01 | Path A Lemma 1 (composition closure, 2 days) | Write prose-proof for Lemma 1 (~600 words); 4 sub-claims + file:line anchors | No |
| D8 | 2026-10-02 | Path A Lemma 1 finish + Lemma 2 start | Finish Lemma 1; begin Lemma 2 (SM byte-determinism, 2 days, ≈400 words) | No |
| D9 | 2026-10-03 | Path A Lemma 2 finish + Lemma 3 start | Finish Lemma 2; begin Lemma 3 (ledger tamper-evidence, 1 day, ≈350 words) | No |
| D10 | 2026-10-04 | §6 trim + 4 contributions + Related Work + cross-ref | Insert 3 lemmas into §6; rewrite §1 to DeepSeek wording; fresh-write §2 (~700w) + §8 (~600w) + §11 (~250w); 3 parallel agents update ~104 line-ranges across ~19 audit docs | **YES — D10 full-draft review** |
| D11 | 2026-10-05 | IEEEtran typeset + 14-page verify | Convert paper → paper.tex; wrap 3 lemmas in theorem environments; 4 tables + 4 TikZ figures; 30-50-entry bibliography; compile to paper.pdf ≤ 14 pages | No |
| D12 | 2026-10-06 | Submission package + Paper B skeleton | Refresh MANIFEST SHA; source.zip; copy paper.pdf; Paper B skeleton on `paper-b-skeleton` git branch | No |
| D13 | 2026-10-07 | User final review + sign-off | Present paper.pdf + MANIFEST.md + source.zip + cover letter + Paper B skeleton to user for final review | **YES — D13 final sign-off** |
| D14 | 2026-10-08 | Submit to TNNLS ScholarOne | User uploads paper.pdf + source.zip + cover letter to mc.manuscriptcentral.com/tnnls with IEEE copyright + DORA workflow | **YES — D14 submission click** |

### Trim target: 36027 words → ~7700 words (D10)

Per DeepSeek §一 + Wave 303 input claim 2, the main text must shrink from **36027 words (current 1404 lines)** to **~7700 words (target ~1500 lines post-D10 insertions)** to fit TNNLS 14-page limit. The path:

| Source | Words | Action |
|---|---:|---|
| Legacy §1-§6 (L23-484) | ~14000 | D3-D5 RESOLUTION deletes |
| §6 Theoretical Lenses (L1238-1263) | ~520 | D10 trim (move JMAA → Paper B) |
| Wave 297 P4-P6 appendices (L488-1086) | ~13553 | D4-D5 promotion (~7000 absorbed into canonical §3/§4/§5/§7) + ~6500 → supplementary |
| Wave 298 P7 deep innovations (L848-1086) | ~3823 | D4-D5 split (~1000 absorbed into §3/§4/§5/§8) + ~2800 → supplementary |
| Wave 300 P5 fold-in (L1087-1404) | ~6475 | D4-D5 partial fold-in (~600 lines into canonical) + ~5800 → supplementary / partial drop |
| D10 fresh-write (§2 Related Work + §8 Reproducibility + §11 Conclusion + §6 trim) | ~2250 | Insert into main |
| **Main text total at D10** | **~7700** | **FITS** (under 8500 with ~800-word buffer) |

### Timeline selection (please confirm):

| Decision | Recommendation | User decision |
|---|---|---|
| **Timeline** | **14-day plan** (D0-D14, 4 user review points) — TIGHT but FEASIBLE; matches DeepSeek's structure with Wave 303 corrections | ☐ 14-day plan / ☐ Other: __________ |

---

## 5. STOP POINT (after Day 0 sign-off)

After you complete §1 (6 pair table) + §2 (Wave 268 authorization) + §3 (venue lock) + §4 (timeline selection) + 4 sub-decisions (special sub-decisions table), the workflow agent takes over D1-D14 without further user review except at the 4 explicit boundary points:

1. **Wait** for your D0 sign-off message before any edits to `paper-flat-flattened.md`.
2. **Execute** D1-D6 per the timeline in §4 (RESOLUTION pass; 5-gate verification per commit).
3. **Re-engage** you at **D3** for boundary-clearness check on §1 Title + Abstract + Intro.
4. **Re-engage** you at **D6** for Path A start review + cover letter sanity check.
5. **Re-engage** you at **D10** for full-draft sanity check + §6 title/scope review.
6. **Re-engage** you at **D13** for final sign-off on submission package.
7. **Re-engage** you at **D14** for ScholarOne upload click.

**If you do NOT sign off D0, the entire workflow is blocked at step 0.** No edits will be made; the agent will not proceed.

> **AGENT WAITS FOR USER AUTHORIZATION BEFORE ANY DESTRUCTIVE EDIT.**
>
> No edits to `paper-flat-flattened.md`, no RESOLUTION deletion steps, no Wave 268 strict-clean break, no destructive inline corrections are performed without explicit user text authorization. The 5-gate baseline is verified PASS (D.4 30/30 + ruff 0 + mkdocs strict 0 warnings + claims no-drift + vendored untouched); the current 1404-line paper state is preserved until user reply is received.

---

## 6. Baseline 5-Gate Status (Current Unchanged Paper)

Verified 2026-09-23 by Wave 303 Day 0 prompt assembly agent:

| Gate | Command | Result | Status |
|---|---|---|:---:|
| 1. D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 pre-existing DeprecationWarnings, 3.59s | **PASS** |
| 2. ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | **PASS** |
| 3. mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code=0, 0 project warnings (Documentation built in 21.81s) | **PASS** |
| 4. claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL by Disputed by; **No drift detected** | **PASS** |
| 5. vendored/data NOT touched | `git diff --stat -- vendored/ data/` | (empty) | **PASS** |

**Baseline status:** All 5 gates **PASS** on the CURRENT (unchanged) paper-flat-flattened.md. The baseline establishes that the dual-present state is currently verifiable and that any RESOLUTION-pass execution must maintain all 5 gates per commit.

**Paper state snapshot (verified 2026-09-23):**
- File: `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/paper-flat-flattened.md`
- Length: **1404 lines / 36027 words** (matches Wave 301 + Wave 303 verification)
- Sections: 23 H2 sections (7 legacy H2 + 4 additive appendices W297 P4/P5/P6 + W298 P7 + Wave 300 P5 fold-in §1-§10)
- Dual-present pairs: 6 (Title, Abstract, §1 Intro, §2 Algorithm, §3 Experiments, §4 Limitations)
- Wave 268 strict-clean: ACTIVE — no edits to paper-flat-flattened.md without explicit user authorization

---

## 7. Files referenced (READ-ONLY)

### Wave 303 plans (READ-ONLY)

- **Source-of-truth 14-day plan:** `docs/audit/wave303-day0-14-plan.md` (973 lines, 14-day timeline D0-D14)
- **Predecessor Day 0 prompt (superseded by this):** `docs/audit/wave301-day0-prompt.md` (212 lines, Wave 301 3-day + 8-10 day + 12-15 day alternatives)
- **Predecessor Day 1 plan (superseded by Wave 303 §3-§5):** `docs/audit/wave301-day1-execution-plan.md` (538 lines, RESOLUTION execution plan)
- **Predecessor Day 2 plan (superseded by Wave 303 §6):** `docs/audit/wave301-day2-execution-plan.md` (Path A 6 lemmas → Wave 303 3 lemmas)
- **Predecessor Day 3 plan (superseded by Wave 303 §8-§9):** `docs/audit/wave301-day3-execution-plan.md` (IEEEtran + submission package)

### Source-of-truth for canonical sections (READ-ONLY)

- `docs/audit/wave300-p3-resolution-plan.md` (RESOLUTION plan source)
- `docs/audit/wave299-paper-a-outline.md` §3 (11-section target)
- `docs/audit/wave297-p2-paper-design.md` (11-section canonical structure + 4-item W297 contributions)
- `docs/audit/wave297-p3-intro-rewritten.md` (§1 prose, apply verbatim at D3)
- `docs/audit/wave297-p4-framework-rewritten.md` (§3/§4/§5 prose, apply verbatim at D4)
- `docs/audit/wave297-p5-empirical-rewritten.md` (§7 prose, apply verbatim at D5)
- `docs/audit/wave297-p6-limitations-rewritten.md` (§9 + §10 prose, apply verbatim at D6)
- `docs/audit/wave298-p7-paper-append.md` (deep innovations source, folded into canonical §3/§4/§5 at D4-D5)
- `docs/audit/wave294-p2-medium-fixed.md` (1 HIGH + 2 MEDIUM inline fixes, apply at D4)
- `docs/audit/wave294-p3-low-paper-fixed.md` (3 LOW inline fixes, apply at D4)
- `docs/audit/wave293-p3-fix-applied.md` (cosine sign flip Wave 293 M-HIGH-1, apply at D4)
- `docs/audit/wave298-p5-literature-compare.md` (§2 Related Work source, fresh-write at D10)
- `docs/audit/wave298-p6-deep-innovations.md` (4 framework + 3 methodology innovations source)
- `docs/audit/wave299-paper-b-deferred.md` (Paper B boundary + JMAA demotion rationale)
- `docs/audit/wave291-p5-3seed-results.md` (§7 statistical methodology source)
- `docs/audit/wave292-p1-pipeline-inventory.md` (§9.1.1 + §10.1.1 roadmap source)
- `docs/audit/wave292-p2-config-genealogy.md` (§7.4 framework-not-theory verdict source)
- `docs/audit/wave296-p1-architecture.md` (§3 + §5 capability-token design source)
- `docs/audit/wave296-p2-cache.md` (§3 + §10 PaperQuantitiesCache source)
- `docs/audit/wave268-strict-clean.md` (Wave 268 strict-clean rule source)
- `docs/audit/wave286-p-fid-gpu-fix.md` (§8 Reproducibility source)
- `docs/audit/wave290-p3-batched-harness.md` (§8 Reproducibility source)

### External source-of-truth

- **TNNLS ScholarOne portal:** mc.manuscriptcentral.com/tnnls
- **TNNLS author guidelines:** ieee.org/publications/transactions/author-guidelines (14-page limit, IEEEtran.cls)
- **ICLR 2027 Author Guidelines:** iclr.cc/Conferences/2027/AuthorGuidelines (for ICLR 2027 blocker rationale)
- **DeepSeek teacher message:** 2026-09-23 teacher feedback (source of §6 rename, 4-contribution wording, Path A 3-lemma scope, 14-day timeline)

---

**End of Wave 303 Day 0 Prompt.** Awaiting your confirmation of §1 (6 pair decisions) + §2 (Wave 268 authorization) + §3 (venue lock) + §4 (timeline selection) + 4 sub-decisions (special sub-decisions table). The workflow agent will not proceed without D0 sign-off.

**STOP MARKER:** Agent waits for user authorization before any destructive edit. No edits to `paper-flat-flattened.md` will be performed until user text authorization is received.