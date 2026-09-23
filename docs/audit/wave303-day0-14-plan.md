# Wave 303 — Day 0-14 TNNLS Submission Plan (incorporating DeepSeek teacher feedback)

**Date:** 2026-09-23
**Mode:** PLAN ONLY (READ-ONLY against `paper-flat-flattened.md` until D0 user authorization)
**Author:** Wave 303 plan assembly agent
**Source-of-truth (predecessors):**
- `docs/audit/wave301-day1-execution-plan.md` (Wave 301 Day 1: 6 dual-present pair RESOLUTION; baseline 5-gate PASS at 1404 lines)
- `docs/audit/wave301-day2-execution-plan.md` (Wave 301 Day 2: 6 lemmas + 3 sketches compressed to 1 day at 12x coverage loss)
- `docs/audit/wave301-day3-execution-plan.md` (Wave 301 Day 3: IEEEtran typesetting + submission package + Paper B skeleton)
- `docs/audit/wave301-day0-prompt.md` (Day 0 user authorization prompt — 6 pair decisions + Wave 268 strict-clean break + venue lock)
- DeepSeek teacher message (2026-09-23) — 14-day plan with 3 Path A lemmas, 8500-word main text, §6 rename to "Framework Properties", 4-contribution wording, JMAA → Paper B
- Ultracode verification (Wave 303 input): 6 confirmed claims about paper state, scope, and structural fit

**Output:** This single plan supersedes the Wave 301 3-day plan (rejected as unrealistic) and the 8-10 / 12-15 day alternatives (rejected as either too compressed or too long for TNNLS submission window). Wave 303 lands at 14 wall-clock days — TIGHT but FEASIBLE, matching DeepSeek's structure with corrections to D9-D10 timeline pressure and §6 title framing.

---

## 0. CRITICAL GUARD — READ BEFORE EXECUTING

**THIS PLAN EXECUTES ONLY AFTER D0 USER AUTHORIZATION.**

Per Wave 268 strict-clean rule (DS-01): **no edits to `paper-flat-flattened.md` are performed without explicit user authorization**. The D0 user authorization prompt at `docs/audit/wave301-day0-prompt.md` §1-§4 lists **6 destructive deletion pairs + Wave 268 break + venue lock + timeline selection** that collectively authorize Days 1-14 to proceed without further user review except at the 4 explicit boundary points (D3, D6, D10, D13).

**Pre-execution prerequisites (D0, all required before D1 begins):**

1. User signs off 6 dual-present pair decisions (per `wave301-day0-prompt.md` §1)
2. User authorizes Wave 268 strict-clean break (per `wave301-day0-prompt.md` §2)
3. User locks venue to TNNLS (per `wave301-day0-prompt.md` §3)
4. User selects 14-day timeline (this plan)
5. User confirms §6 rename to "Framework Properties" (DeepSeek §四)
6. User confirms 4-contribution wording (DeepSeek §五)
7. User confirms §6 Theoretical Lenses (legacy lines 1238-1263) dropped entirely; JMAA → Paper B
8. User confirms §10 Future Work either dropped or folded into §8 Limitations

**If any of the above are missing at D1 start, STOP and re-engage user.**

### 0.1 What this plan EXPLICITLY does NOT do

- Does NOT modify `paper-flat-flattened.md` until D0 user authorization
- Does NOT run destructive RESOLUTION edits before D1
- Does NOT push to any remote branch until D14 user final sign-off
- Does NOT submit to TNNLS ScholarOne until D13 user final review + sign-off
- Does NOT split into Wave 304/305/306 sub-waves — Wave 303 is the single integrated plan
- Does NOT include Paper B main prose (Paper B skeleton only at D12 if time permits)

### 0.2 What this plan EXPLICITLY does

- Produces one READ-ONLY plan document (`docs/audit/wave303-day0-14-plan.md`)
- Defines D0 user actions (Day 0 prompt decisions)
- Defines D1-D14 agent actions with 5-gate verification gates per commit
- Defines 4 user review boundaries (D3, D6, D10, D13)
- Defines the final TNNLS submission package

---

## 1. Timeline Overview (D0-D14, 14 wall-clock days)

| Day | Date (assumed D0=2026-09-24) | Phase | Agent work | User review |
|:---:|:---:|---|---|:---:|
| D0 | 2026-09-24 | Day 0 user authorization | Read `wave301-day0-prompt.md`, decide 6 pairs, authorize Wave 268 strict-clean break, lock TNNLS, confirm 14-day timeline | **YES — 2-3h** |
| D1 | 2026-09-25 | RESOLUTION Part 1 — Pair 1 (Title) | Delete legacy title block (lines 1-4); promote Wave 297 P2 title (lines 13-15); 5-gate verify | No |
| D2 | 2026-09-26 | RESOLUTION Part 1 — Pair 2 (Abstract) | Delete legacy abstract (lines 7-12); promote Wave 297 P2 5-sentence abstract (lines 17-19); 5-gate verify | No |
| D3 | 2026-09-27 | RESOLUTION Part 1 — Pair 3 (§1 Intro) | Delete legacy §1 (lines 23-50); promote Wave 297 P3 §1 (lines 52-67); re-run 5-gate; CLAIMS.md re-anchor | **YES — D3 boundary clearness check** |
| D4 | 2026-09-28 | RESOLUTION Part 2 — Pair 4 part A (§2 Algorithm → §3/§4/§5 framework promotion) | Delete legacy §2 (lines 71-258); promote W297 P4 A.1/A.2/A.3/A.4 (lines 488-620) to canonical §3/§4/§5; apply Wave 294 P2 cosine sign flip (M-HIGH-1) | No |
| D5 | 2026-09-29 | RESOLUTION Part 2 — Pair 4 part B (§3 Experiments → §7 promotion + §5/§6 workflow-internal cleanup) | Delete legacy §3 (lines 259-400); promote W297 P5 §7 (lines 624-755) to canonical §7; delete legacy §5/§5.5/§6 (lines 423-484); 5-gate verify | No |
| D6 | 2026-09-30 | RESOLUTION Part 3 — Pairs 5+6 + cover letter rebalance | Delete legacy §4 Limitations K1-K8 (lines 401-422); promote W297 P6 §9 (lines 758-787) to canonical §9; promote §10 or fold per user D0 decision; delete W297 P4/P5/P6 framing-note preambles; rename §6 from "Theoretical Lenses" to "Framework Properties" (placeholder for D10); refresh cover letter; 5-gate verify | **YES — D6 Path A start review + cover letter sanity check** |
| D7 | 2026-10-01 | Path A Lemma 1 start (Protocol composition closure) | Write prose-proof for Lemma 1 in `wave303-day7-lemma1.md` (300-400 words); cite 4 protocol files + 4 sub-claims | No |
| D8 | 2026-10-02 | Path A Lemma 1 finish + Lemma 2 start | Finish Lemma 1 prose; begin Lemma 2 (SM byte-determinism) at `wave303-day8-lemma2.md` (350-400 words); cite state_machine.py:832-941 | No |
| D9 | 2026-10-03 | Path A Lemma 2 finish + Lemma 3 start | Finish Lemma 2 prose; begin Lemma 3 (ledger tamper-evidence) at `wave303-day9-lemma3.md` (300-350 words); cite engine.py:455-613 + ledger_chain.py:113-218 | No |
| D10 | 2026-10-04 | §6 trim + 4 contributions + §2 Related Work + cross-ref update | Insert 3 Path A lemmas into §6 "Framework Properties" (3 subsections); rewrite §1 contributions to DeepSeek's 4-contribution wording; write §2 Related Work fresh (~700 words); update ~17 audit doc line-range references (3 parallel agents, ~3 hours wall-clock); 5-gate verify | **YES — D10 full-draft review + §6 title/scope check** |
| D11 | 2026-10-05 | IEEEtran typeset + 14-page verification | Convert paper-flat-flattened.md → paper.tex with `\documentclass[journal]{IEEEtran}`; wrap 3 lemmas in `\begin{lemma}...\end{lemma}` + `\begin{proof}...\end{proof}`; insert 4 tables (4.1, 5.1, 7.1, 7.2); 4 figure placeholders (TikZ re-draw); 30-50 refs in bibliography.bib; run pdflatex × 4; verify pdfinfo Pages ≤ 14 | No |
| D12 | 2026-10-06 | Submission package + Paper B skeleton | Refresh `tnnls_submission/MANIFEST.md` SHA-256; generate `source.zip`; copy `paper.pdf` to `docs/paper-tnnls.pdf` and `tnnls_submission/paper.pdf`; generate `highlight_blurb.pdf`; create `docs/drafts/paper-b-jmaa/skeleton.md` (separate directory, separate git branch `paper-b-skeleton`); 5-gate verify | No |
| D13 | 2026-10-07 | User final review + sign-off | Present paper.pdf + MANIFEST.md + source.zip + cover letter + Paper B skeleton to user for final review; user authorizes submission | **YES — D13 final sign-off** |
| D14 | 2026-10-08 | Submit to TNNLS ScholarOne | User uploads to mc.manuscriptcentral.com/tnnls with IEEE copyright + DORA workflow; agent monitors upload confirmation | **YES — D14 submission click** |

**Total: 14 wall-clock days from D0 user authorization to TNNLS submission.** Submission target: 2026-10-08.

### 1.1 Wave 303 timeline compression vs Wave 301 3-day plan

| Aspect | Wave 301 3-day (REJECTED) | Wave 303 14-day (THIS PLAN) | Wave 301 8-10 day (REJECTED) |
|---|---|---|---|
| Day 0 user review | 2-3h | 2-3h | 2-3h |
| RESOLUTION pass | 1 day (12h) — D1 only | 6 days — D1-D6 (1 day per pair + Part 2/3 split) | 1 day |
| Path A | 1 day (12h, 6 lemmas + 3 sketches at 12x depth loss) | 3 days — D7-D9 (3 lemmas at intermediate depth) | 8-10 days (6-8 lemmas) |
| IEEEtran typeset | 1 day (8-10h, leaves zero margin) | 1 day — D11 (with buffer for page-count trim) | 1 day |
| User review points | 1 (Day 3 boundary) | 4 (D3, D6, D10, D13) | 3 |
| Submission package | Day 3 | Day 12 (with Day 13 final review) | Day 8 |
| Submission | Day 3 (UNREALISTIC) | Day 14 (REALISTIC) | Day 8-10 |

**Rationale for 14-day plan:** DeepSeek's original 14-day structure is the minimum to fit (a) 6 RESOLUTION pairs with user review at D3, (b) 3 Path A lemmas at intermediate depth without 12x compression loss, (c) 4 user review boundaries (D3, D6, D10, D13), (d) IEEEtran typesetting with page-count buffer, (e) final submission package + Paper B skeleton, (f) D13 final sign-off before D14 ScholarOne upload. Compressing to 12 days would lose the D6 mid-Path-A review; compressing to 10 days would force the rejected 3-day-style coverage loss.

### 1.2 Wave 303 timeline deltas vs DeepSeek's 14-day structure

| Day | DeepSeek table | Wave 303 plan | Reason for divergence |
|:---:|---|---|---|
| D1-3 | "RESOLUTION pass Part 1 (Title/Abstract/§1)" | Same scope, 1 day per pair | Wave 301 day 1 had all 6 pairs in 1 day at 12h — DeepSeek correctly split this to allow D3 boundary clearness check |
| D4-5 | "RESOLUTION pass Part 2 (§2-§5, 30+ cross-refs)" | D4 = §2 → §3/§4/§5 promotion only; D5 = §3 → §7 promotion + workflow-internal cleanup | Defer cross-ref updates to D10 (parallel agents, 3 hours wall-clock) — fits with Wave 301 day 3 §3.2 estimate of "8.5 hours single-agent / 3 hours with 3 parallel agents" |
| D6 | "RESOLUTION pass Part 3 (§6-§10 + cover letter)" | Same: §4 → §9+§10 + framing-note cleanup + cover letter rebalance + §6 rename placeholder | Matches DeepSeek |
| D7 | "Path A start" (D7-8 slot, 5 days total) | Lemma 1 (2 days, D7-8) | Matches DeepSeek; Lemma 1 alone is 2 days because it bundles 4 sub-claims per Wave 303 input claim 4 |
| D8 | (continued) | Lemma 1 finish + Lemma 2 start | Parallel start of Lemma 2 (2 days, D8-9) |
| D9 | "Path A finish + §6 trim + 4 contributions + Related Work" | Lemma 2 finish + Lemma 3 start | D9 becomes Lemma 2 finish + Lemma 3 start (overlap with §6 trim deferred to D10); corrects DeepSeek's "D9 full-draft assembly" unrealistic framing |
| D10 | "§6 trim + 4 contributions + Related Work" | §6 trim + 4 contributions + Related Work + cross-ref update (3 parallel agents, ~3 hours) | Adds cross-ref update pass that DeepSeek missed; 8500-word target on D10 is the binding constraint — 1.5 days for full-draft assembly is honest |
| D11 | "IEEEtran typeset + 14-page verification" | Same | Matches DeepSeek |
| D12 | (not in DeepSeek table) | Submission package + Paper B skeleton | DeepSeek compressed D11-12 to 2 days for IEEEtran + submission package; Wave 303 splits to give D12 a separate day for submission package + Paper B skeleton |
| D13 | "User final review + sign-off" | Same | Matches DeepSeek |
| D14 | "投稿 TNNLS" | Submit to TNNLS ScholarOne | Matches DeepSeek |

**Net deltas:** D9-D10 = 2 days for full-draft assembly (DeepSeek's 1-day D9 was flagged as unrealistic by Wave 303 input claim 3). D12 = separate day for submission package (DeepSeek's compressed D11-12 doesn't leave room for Paper B skeleton). All other days match DeepSeek.

---

## 2. Day 0 — User Authorization (2026-09-24, 2-3 hours)

**Goal:** User opens `docs/audit/wave301-day0-prompt.md` and provides 8 explicit authorizations to unlock Wave 303 D1-D14.

### 2.1 D0 action list (user-executed)

| # | Action | Source | Estimated time |
|---:|---|---|---:|
| 1 | Open `docs/audit/wave301-day0-prompt.md` and read §0 TL;DR | Local file | 5 min |
| 2 | Decide 6 dual-present pair outcomes (recommended: confirm all 6 = Wave 297 additive) | `wave301-day0-prompt.md` §1 Decision Table | 30 min |
| 3 | Authorize Wave 268 strict-clean break (text signature in chat reply) | `wave301-day0-prompt.md` §2 Authorization prompt | 10 min |
| 4 | Lock venue to TNNLS (confirm) + ICLR 2028 as backup + DROP ICLR 2027 | `wave301-day0-prompt.md` §3 Venue Lock | 10 min |
| 5 | Confirm 14-day timeline (this plan) | `wave301-day0-prompt.md` §4 Timeline selection | 5 min |
| 6 | Confirm §6 rename to "Framework Properties" (DeepSeek §四) | DeepSeek message | 5 min |
| 7 | Confirm 4-contribution wording (DeepSeek §五) | DeepSeek message | 5 min |
| 8 | Confirm §6 Theoretical Lenses (lines 1238-1263) dropped entirely; JMAA → Paper B companion | DeepSeek §四 + Wave 268 strict-clean | 5 min |
| 9 | Confirm §10 Future Work either dropped or folded into §8 Limitations | `wave301-day0-prompt.md` §1 Special sub-decisions | 5 min |
| 10 | Sign message: "I, [name], authorize Wave 303 destructive RESOLUTION pass on `docs/drafts/paper-flat-flattened.md` per D1-D6 sequencing. 14-day timeline confirmed. TNNLS submission target 2026-10-08." | Authorization prompt | 5 min |

**Total D0 time: ~90-180 minutes (2-3 hours).** This is the ONLY user-only day in Wave 303; D3, D6, D10, D13 are user review points but not blocking until boundary clearness check.

### 2.2 D0 deliverable (user-executed)

A single chat message containing:
- The 6 pair decisions (CONFIRM or OVERRIDE per pair)
- Wave 268 strict-clean break authorization signature
- Venue lock (TNNLS primary, ICLR 2028 backup, DROP ICLR 2027)
- 14-day timeline confirmation
- §6 rename confirmation
- 4-contribution wording confirmation
- §6 Theoretical Lenses drop confirmation
- §10 Future Work disposition
- D14 ScholarOne upload authorization

**Day 0 does NOT modify `paper-flat-flattened.md`.** Day 0 is a READ-ONLY authorization. Agent does NOT proceed to D1 without user signature.

### 2.3 D0 verification gates (READ-ONLY)

| Gate | Check | Expected |
|---|---|---|
| G0.1 | User message contains explicit "I authorize" string | YES |
| G0.2 | User message names 6 pairs (or says "confirm all") | YES |
| G0.3 | User message locks venue | YES (TNNLS or other) |
| G0.4 | User message confirms timeline | YES (14-day or other) |
| G0.5 | 5-gate baseline still PASS (D.4 30/30, ruff 0, mkdocs strict 0, claims no-drift, vendored untouched) | YES |

If any check fails, agent re-engages user before D1.

---

## 3. D1-3 — RESOLUTION Part 1 (Title/Abstract/§1)

**Goal:** Delete legacy Title block, Abstract block, and §1 Introduction; promote Wave 297 P2/P3 additive versions to canonical positions; re-anchor CLAIMS.md.

### 3.1 D1 — Pair 1: Title block

**Goal:** Replace legacy 4-line title block with Wave 297 P2 single-line title.

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns 1404 |
| **DELETE** | lines 1-4 (legacy title line + blank + Wave 297 P3 RE-ANCHOR NOTE block + separator `---`) |
| **PROMOTE** | lines 13-15 (subsection "### New title (Wave 297 P2 proposal)") → canonical lines 1-3 |
| **REWRITE** | Title block becomes single line: `# FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints.` |
| **5-GATE VERIFY** | D.4 30/30 + ruff 0 + mkdocs strict 0 + claims no-drift + vendored untouched |

**Net delta:** -4 lines (1404 → 1400)

**Source-of-truth:** Wave 297 P2 canonical title at `docs/audit/wave297-p2-paper-design.md` lines 60-80 (canonical title text).

### 3.2 D2 — Pair 2: Abstract

**Goal:** Replace legacy 9-line abstract with Wave 297 P2 5-sentence abstract.

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns 1400 |
| **DELETE** | lines 7-12 (Abstract heading + 9-line legacy abstract + 2-line Wave 297 P3 RE-ANCHOR NOTE) |
| **PROMOTE** | lines 17-19 (5-sentence additive abstract paragraph) → canonical Abstract content |
| **REWRITE** | `## Abstract` heading + single 5-sentence paragraph |
| **5-GATE VERIFY** | All 5 gates |

**Net delta:** -10 lines (1400 → 1390)

**Source-of-truth:** Wave 297 P2 5-sentence abstract at `docs/audit/wave297-p2-paper-design.md` lines 80-110.

### 3.3 D3 — Pair 3: §1 Introduction + boundary clearness check

**Goal:** Replace legacy 4-paragraph §1 Introduction + 6-item contributions with Wave 297 P3 4-paragraph + 4-item contributions; **D3 USER REVIEW** for boundary clearness.

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns 1390 |
| **DELETE** | lines 23-50 (4-paragraph legacy intro + 5 RE-ANCHOR NOTE blocks + 6-item legacy contributions + 1 contributions RE-ANCHOR NOTE) |
| **PROMOTE** | lines 52-67 (additive 4-paragraph + 4-item contributions) → canonical §1 |
| **REWRITE** | `## 1 Introduction` heading + 4 additive paragraphs + 4-item contributions list |
| **CLAIMS RE-ANCHOR** | Update CLAIMS.md line-range references for any claim anchored to legacy §1 |
| **5-GATE VERIFY** | All 5 gates |

**Net delta:** -23 lines (1390 → 1367)

**Source-of-truth:** Wave 297 P3 §1 prose at `docs/audit/wave297-p3-intro-rewritten.md` (apply verbatim per DS-01).

#### 3.3.1 D3 USER REVIEW (boundary clearness check)

**Required user actions at D3 (15-30 minutes):**

1. Review `paper-flat-flattened.md` lines 1-25 (Title + Abstract + §1 intro)
2. Verify 4-item contributions list matches Wave 297 P3 wording (not 6-item legacy)
3. Verify no JMAA Theorem 1 mentions in §1 (per DeepSeek §五)
4. Verify §1 does NOT include "Theoretical Lenses" framing
5. Approve D4-D6 progression OR request edits

**D3 deliverable (user-executed):** Single message: "D3 boundary clearness check PASS — proceed to D4" OR "D3 edits requested: [specific line changes]".

**If D3 PASS:** agent proceeds to D4.
**If D3 edits requested:** agent applies edits, re-runs 5-gate, re-presents to user (D3 + ~2 hours). Total wall-clock impact: +2-3 hours.

#### 3.3.2 D3 risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Wave 297 P3 §1 prose drift between W297 source and D3 file | LOW | Per DS-01, apply verbatim — diff W297 P3 source vs canonical §1 to verify zero drift |
| User discovers JMAA leakage in §1 | LOW (W297 P3 prose is JMAA-free) | If discovered, edit per Wave 268 strict-clean rule (1-line removal) |
| CLAIMS.md re-anchor fails | LOW | Defer cross-ref update to D10 (parallel agents); D3 only updates inline §1 line references |

---

## 4. D4-5 — RESOLUTION Part 2 (§2-§5 promotion)

**Goal:** Delete legacy §2 Algorithm (190 lines), §3 Experiments (140 lines), §5/§5.5/§6 workflow-internal (63 lines); promote Wave 297 P4 A.1-A.4 → canonical §3/§4/§5; promote Wave 297 P5 §7 → canonical §7; apply Wave 294 P2 inline fixes.

### 4.1 D4 — Pair 4 part A: §2 Algorithm → §3/§4/§5 framework promotion

**Goal:** Delete legacy §2 Algorithm; promote Wave 297 P4 Appendix A.1-A.4 to canonical §3 Framework / §4 Scheduler Family / §5 Adapter Protocol; apply Wave 294 P2 cosine sign flip (M-HIGH-1).

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns 1367 |
| **DELETE** | lines 71-258 (entire §2 Algorithm, 10 sub-sections + tables + §MS.theorem1_data_pipeline_entry_points + §MS.config_genealogy + §MS.claim_audit) |
| **PROMOTE** | lines 488-517 (Appendix A.1) → canonical `## 3 Framework` heading + content |
| **PROMOTE** | lines 519-560 (Appendix A.2) → canonical `## 4 Scheduler Family` heading + content |
| **PROMOTE** | lines 562-594 (Appendix A.3) → canonical `## 5 Adapter Protocol` heading + content |
| **RELOCATE** | lines 596-616 (Appendix A.4) → §4.4 or supplementary per §6 decision (D6 covers this) |
| **APPLY INLINE** | Wave 294 P2 M-HIGH-1 cosine sign flip: `(1 − cos(π r / (L − 1)))` → `(1 + cos(π r / (L − 1)))/2` at §4 Table 4.1 |
| **APPLY INLINE** | Wave 294 P2 M-MED-1 factory-vs-adapter "framework default" framing correction at §4 ¶2 |
| **APPLY INLINE** | Wave 294 P2 M-MED-2 registry-key vs `schedule_family()` note at §4 Table 4.1 |
| **APPLY INLINE** | Wave 294 P3 LOW corrections at §4 §5 (DEPRECATED marker + schedule_family default + MultiChannelJitteredConstantScheduler citation) |
| **5-GATE VERIFY** | All 5 gates |

**Net delta:** ~-55 lines (1367 → ~1312)

**Source-of-truth:** Wave 297 P4 framework prose at `docs/audit/wave297-p4-framework-rewritten.md` lines 58-99 (A.1 framework); 79-99 (A.2 scheduler family); 101-123 (A.3 adapter protocol). Wave 294 P2 inline fixes at `docs/audit/wave294-p2-medium-fixed.md`. Wave 294 P3 LOW fixes at `docs/audit/wave294-p3-low-paper-fixed.md`.

### 4.2 D5 — Pair 4 part B + Pair 5: §3 Experiments → §7 promotion + workflow-internal cleanup

**Goal:** Delete legacy §3 Experiments; promote Wave 297 P5 §7 to canonical §7 Empirical Results; delete legacy §5 Flattening Checklist + §5.5 Efficiency + §6 Static Reference Labels (workflow-internal artifacts).

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns ~1312 |
| **DELETE** | lines 259-400 (entire §3 Experiments, 6 sub-sections + Table 3.1 + Table 3.2 + Table 3.3 + Figure 4 narrative + head-to-head) |
| **PROMOTE** | lines 624-755 (Appendix W297 P5 §7.1-§7.11) → canonical `## 7 Empirical Results` heading + content |
| **PRESERVE** | Wave 297 P5 §7.4 framework-not-theory verdict verbatim (10/11 cosine-cell pattern) |
| **PRESERVE** | Wave 297 P5 §7.3 statistical methodology block verbatim (4 Bonferroni families + 3-seed pool) |
| **PRESERVE** | 5.5 efficiency data → fold into §7 Empirical Results discussion |
| **DELETE** | lines 423-484 (entire §5 Flattening Checklist + §5.5 Efficiency narrative + §6 Reviewer-Facing Static Reference Labels — workflow-internal) |
| **CLEANUP** | lines 1264-1289 (Wave 300 P5 §7 fold-in block becomes redundant; delete) |
| **5-GATE VERIFY** | All 5 gates |

**Net delta:** ~-73 lines (1312 → ~1239)

**Source-of-truth:** Wave 297 P5 empirical results prose at `docs/audit/wave297-p5-empirical-rewritten.md`. Wave 291 P5 3-seed verification protocol at `docs/audit/wave291-p5-3seed-results.md`. Wave 292 P2 12/13 cells use CosineAnnealScheduler at `docs/audit/wave292-p2-config-genealogy.md`.

#### 4.2.1 D5 selection: 5 STRONG/PARTIAL cells for main text

Per DeepSeek §一 + Wave 303 input claim 2, main text §7 shows only **5 STRONG/PARTIAL cells (R1/R2/R3/R5c/R6)**, with the remaining 6 cells moving to supplementary.

| Cell | Status | Main text | Supplementary |
|---|---|:---:|:---:|
| R1 | STRONG | YES | — |
| R2 | STRONG (verify status — see Wave 303 input claim 2 risk) | YES | — |
| R3 | STRONG | YES | — |
| R5c | PARTIAL | YES | — |
| R6 | PARTIAL | YES | — |
| R4 | UNDERPOWERED | — | YES |
| R5a | UNDERPOWERED | — | YES |
| R5b | UNDERPOWERED | — | YES |
| R7 | BLOCKED | — | YES |
| R8 | REGRESSES | — | YES |
| R9 | UNDERPOWERED | — | YES |

**D5 deliverable:** `paper-flat-flattened.md` lines 259-400 deleted; canonical §7 Empirical Results (5 cells in main) + supplementary `cells-r4-r9.md` (6 cells in supp) populated.

---

## 5. D6 — RESOLUTION Part 3 (§6-§10 + cover letter rebalance) + D6 USER REVIEW

**Goal:** Delete legacy §4 Limitations K1-K8; promote Wave 297 P6 §9 to canonical §9; promote or fold §10 per user D0 decision; rename §6 placeholder for D10 trim; refresh cover letter; **D6 USER REVIEW** for Path A start sanity check.

### 5.1 D6 destructive edits

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns ~1239 |
| **DELETE** | lines 401-422 (8 K1-K8 paragraphs) |
| **PROMOTE** | lines 758-787 (Appendix W297 P6 §9) → canonical `## 9 Limitations` heading + content |
| **PROMOTE** | lines 789-815 (Appendix W297 P6 §10) → canonical `## 10 Future Work` (IF user D0 keeps §10) OR fold into §8 (IF user D0 folds) |
| **PRESERVE** | §9.2 K1-K8 cross-reference (boundary dimensions remain applicable) |
| **CLEANUP** | Wave 300 P5 §9 fold-in block (lines 1319-1342) becomes redundant; delete |
| **CLEANUP** | Wave 297 P4 ADDITIVE REFRAME NOTE preamble (line 490) — delete |
| **CLEANUP** | Wave 297 P5 ADDITIVE REFRAME NOTE preamble (line 626) — delete |
| **CLEANUP** | Wave 297 P6 ADDITIVE REFRAME NOTE preamble (line 760) — delete |
| **CLEANUP** | "End of Wave 297 P4 reframe appendix" closing (line 620) — delete |
| **CLEANUP** | "End of Wave 298 P7 deep-innovations appendix" closing (line 1083) — delete |
| **RENAME §6 (placeholder)** | `## 6 Theoretical Lenses (Wave 296 P7 + ...)` → `## 6 Framework Properties (Path A prose-proof sketches, D10)` — placeholder only; full rewrite at D10 |
| **5-GATE VERIFY** | All 5 gates |
| **COVER LETTER REBALANCE** | Refresh `tnnls_submission/cover_letter.md` to reflect TNNLS venue + new 4-contribution wording; 17 `[USER TO FILL: ...]` placeholders preserved per `FILL_GUIDE.md` |

**Net delta:** ~+62 lines (1239 → ~1301) — gains from §9+§10 promotion exceed deletions.

**Source-of-truth:** Wave 297 P6 limitations prose at `docs/audit/wave297-p6-limitations-rewritten.md`.

### 5.2 D6 USER REVIEW (Path A start + cover letter sanity check)

**Required user actions at D6 (15-30 minutes):**

1. Review `paper-flat-flattened.md` §9 Limitations (now canonical, 6 disclosures per W297 P6)
2. Verify §10 disposition (kept as §10 or folded into §8 per D0 decision)
3. Review `tnnls_submission/cover_letter.md` rebalance (TNNLS venue, 4-contribution wording)
4. Confirm D7-D9 Path A plan (3 lemmas at 2+2+1 days)
5. Approve D7 start OR request edits

**D6 deliverable (user-executed):** Single message: "D6 review PASS — start Path A at D7" OR "D6 edits requested: [specific line changes]".

### 5.3 D6 final structure (post-RESOLUTION, before D7)

```
# FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints.
## Abstract                                                       (5-sentence, ~280 words)
## 1 Introduction                                                 (4-item contributions, ~700 words)
## 3 Framework                                                    (canonical from A.1, ~1200 words)
## 4 Scheduler Family                                             (canonical from A.2, ~500 words)
## 5 Adapter Protocol                                             (canonical from A.3, ~600 words)
## 6 Framework Properties (Path A prose-proof sketches, D10)     (placeholder, ~700 words at D10)
## 7 Empirical Results                                            (canonical from W297 P5, ~1300 words)
## 9 Limitations                                                  (canonical from W297 P6, ~500 words)
## 10 Future Work                                                 (canonical from W297 P6 OR folded into §8, ~300 words)
```

**Post-RESOLUTION stats (target):**
- Total lines: ~1301 (down from 1404)
- Total words: ~5380 (down from 36027) — Wave 297 P3-P6 additive + Wave 298 P7 fold-in contributions absorbed; legacy §2-§6 deleted
- Sections: 9 H2 (Title + Abstract + §1 + §3 + §4 + §5 + §6 placeholder + §7 + §9 + §10) — missing §2 Related Work, §8 Reproducibility, §11 Conclusion (fresh-write at D10)

**D6 does NOT yet include §2 Related Work, §8 Reproducibility, §11 Conclusion.** These are D10 fresh-writing tasks.

---

## 6. D7-D9 — Path A (3 lemmas at intermediate depth)

**Goal:** Write 3 prose-proof lemmas for §6 Framework Properties: protocol composition closure, SM byte-determinism, ledger tamper-evidence. Total ~1000-1100 words across 3 lemmas. Per DeepSeek §三: 5 days → 3 wall-clock days with 3 parallel agents.

### 6.1 D7-D8 (parallel agent work) — Lemma 1: Protocol composition closure

**Goal:** Write prose-proof for the 1 lemma that bundles 4 sub-claims about the 4 typed Protocols (per Wave 303 input claim 4).

| Sub-claim | Source-of-truth |
|---|---|
| SchedulerProtocol closure (`to_config`/`from_config` round-trip) | `adaptive_reflow/algorithm/scheduler/protocols.py:157-289` |
| PolicyDriverProtocol polarity (`beta → memory_fraction = 1 - beta`) | `adaptive_reflow/algorithm/policy_driver.py:181-285` |
| MergeOperator bounded contract (P0-3 / P2-4) | `adaptive_reflow/algorithm/merge/merge_operator.py:248-340` |
| RestartBlenderProtocol convex combination (Contract 3.1 polarity) | `adaptive_reflow/algorithm/blender/blender.py:425-470` |

**Deliverable:** `docs/audit/wave303-day7-lemma1.md` (~600 words, 1 claim + 1 prose-proof sketch citing all 4 source files).

**Agent:** Agent A (Lemma 1 specialist) — D7-D8 wall-clock (2 days).

**Verification (D8 EOD):**
- Lemma 1 word count 550-650
- 4 file:line anchors verified (grep test)
- 4 sub-claims explicit in prose body
- No JMAA references

### 6.2 D8-D9 (parallel agent work) — Lemma 2: State-machine byte-determinism

**Goal:** Write prose-proof for state-machine byte-determinism, narrowed to "given a fixed event sequence AND fixed asyncio loop ordering, `_log` is byte-deterministic" (per Wave 303 input claim 4 framing constraint).

| Determinism axis | Source-of-truth |
|---|---|
| Priority tiebreak by `(-priority, index)` | `adaptive_reflow/contracts/state_machine.py:826-856` |
| Sync dispatch with `_update_history` BEFORE exit hooks | `state_machine.py:858-920` |
| Parallel-region asyncio.gather (non-deterministic by asyncio semantics — acknowledged in prose) | `state_machine.py:924-942` |
| Async candidate selection with same priority sort | `state_machine.py:832-941` (full path) |

**Deliverable:** `docs/audit/wave303-day8-lemma2.md` (~400 words, 1 claim + 1 prose-proof sketch).

**Agent:** Agent B (Lemma 2 specialist) — D8-D9 wall-clock (2 days).

**Verification (D9 EOD):**
- Lemma 2 word count 350-450
- 4 file:line anchors verified
- Async determinism narrowing is explicit (NOT byte-deterministic across `asyncio.gather` reorderings; this is a corollary in supplementary)
- No JMAA references

### 6.3 D9 (parallel agent work) — Lemma 3: Ledger tamper-evidence

**Goal:** Write prose-proof for SHA-256 hash-chained ledger integrity (per Wave 303 input claim 4, 1 day is honest for this lemma).

| Invariant | Source-of-truth |
|---|---|
| Anchor (round-0 prev_ledger_row_hash is None) | `adaptive_reflow/frame/engine.py:455-489` |
| Linkage (`row[i].prev_ledger_row_hash == row[i-1].row_hash`) | `engine.py:542-613` |
| Hash recompute (`sha256(canonical_json(fields ∪ {prev})) == row.row_hash`) | `engine.py:455-489` |
| Round monotonicity (`round_index` monotone non-decreasing) | `engine.py:542-613` |
| Fail-closed append (`LedgerChain.append` raises on invariant break) | `adaptive_reflow/frame/ledger_chain.py:167-218` |

**Deliverable:** `docs/audit/wave303-day9-lemma3.md` (~350 words, 1 claim + 1 prose-proof sketch).

**Agent:** Agent C (Lemma 3 specialist) — D9 wall-clock (1 day).

**Verification (D9 EOD):**
- Lemma 3 word count 300-400
- 5 file:line anchors verified
- 4 invariants explicit in prose body
- SHA-256 collision resistance claim explicit (`1 - 2^{-256}`)
- No JMAA references

### 6.4 Path A coordination (D7-D9)

**3 parallel agents run D7-D9:**

| Day | Agent A (Lemma 1) | Agent B (Lemma 2) | Agent C (Lemma 3) |
|:---:|---|---|---|
| D7 | Day 1 of 2 — read 4 protocol files (~1200 lines), draft claim | (idle, waiting for D8) | (idle, waiting for D9) |
| D8 | Day 2 of 2 — finalize prose-proof, run anchor verify | Day 1 of 2 — read state_machine.py:826-941, draft claim | (idle, waiting for D9) |
| D9 | (done; idle) | Day 2 of 2 — finalize prose-proof, run anchor verify | Day 1 of 1 — read engine.py:455-613 + ledger_chain.py:113-218, finalize prose-proof |

**Total agent-hours:** 5 days (2 + 2 + 1) per DeepSeek §三. **Total wall-clock:** 3 days (D7-D9) via parallel execution.

### 6.5 Path A risks (per Wave 303 input claim 4)

| Risk | Mitigation |
|---|---|
| Async determinism narrowed too aggressively → reviewer flags as "not actually byte-deterministic" | Frame narrowing as a corollary in supplementary; main text explicitly states "given fixed asyncio loop ordering" caveat |
| 4 sub-claims in Lemma 1 look like 4 separate lemmas to reviewer | Use `### Sub-claim 1.1, 1.2, 1.3, 1.4` subsections within Lemma 1 |
| Source-of-truth file:line anchors drift between D7-D9 and D11 LaTeX | Pin anchors to git commit SHA; re-verify at D11 |
| 5-gate regression during Path A | Path A does NOT touch `paper-flat-flattened.md`; only writes 3 audit files under `docs/audit/wave303-day{7,8,9}-lemma{1,2,3}.md`. 5-gate unchanged. |

---

## 7. D10 — §6 trim + 4 contributions + §2 Related Work + cross-ref update + D10 USER REVIEW

**Goal:** Insert 3 Path A lemmas into §6 Framework Properties; rewrite §1 contributions to DeepSeek's 4-contribution wording; write §2 Related Work fresh (~700 words); update ~17 audit doc line-range references via 3 parallel agents; **D10 USER REVIEW** for full-draft sanity check.

### 7.1 D10 destructive edits

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns ~1301; D7-D9 Path A files exist |
| **§6 trim and 3-lemma insertion** | Replace `## 6 Framework Properties (Path A prose-proof sketches, D10)` placeholder with: §6.1 Protocol composition closure (insert Lemma 1 from `wave303-day7-lemma1.md`); §6.2 Byte-deterministic state machine (insert Lemma 2 from `wave303-day8-lemma2.md`); §6.3 Tamper-evident ledger (insert Lemma 3 from `wave303-day9-lemma3.md`). Total §6 length ~700 words. |
| **§1 contribution rewrite (DeepSeek §五 wording)** | Append new additive block below Wave 297 P2 4-item contributions list (lines 64-67): `### TNNLS contribution list (DeepSeek teacher proposal, additive)` containing the 4 contributions: (i) Framework-level reconstruction, (ii) Formal framework properties (3 lemmas), (iii) Cross-domain empirical validation (5 STRONG/PARTIAL + 6 supp), (iv) Engineering reproducibility (D.4 30/30 + 6-gate CI + vendor purity). JMAA Theorem 1 removed from contribution list entirely. Per Wave 268 strict-clean + Wave 297 additive preservation, the W297 P2 list remains as legacy + the new additive block. |
| **§2 Related Work fresh-write** | Insert `## 2 Related Work` (target ~700 words, 3 paragraphs): (a) FM inference acceleration lineage (DDPM → DDIM → DPM-Solver → Consistency Models → ReFlow/InstaFlow → Progressive Distillation → LCM); (b) FM theoretical frameworks (score-SDE → flow matching OT → Rectified Flow → JMAA as companion only); (c) Typed ML system contracts (PEP 544 → Rust traits → Haskell type classes → capability-based security → typed contract systems). Wave 297 P2 JMAA 4th contribution removed; in §2, write: "A companion paper provides a theoretical lens via BL-convergence bounds [Paper B citation or 'companion paper in preparation']". |
| **§8 Reproducibility fresh-write** | Insert `## 8 Reproducibility` (target ~600 words, 6 subsections per Wave 301 Day 2 §5.2): §8.1 SHA-256 ledger chain, §8.2 D.4 byte-stability suite, §8.3 Vendor purity invariant, §8.4 Feature inventory, §8.5 CI gate composition, §8.6 Reproduction package. |
| **§11 Conclusion fresh-write** | Insert `## 11 Conclusion` (target ~250 words, 2 paragraphs per Wave 301 Day 2 §5.3): (a) restate 4 contributions + paper boundary, (b) future directions + Paper B pointer. |
| **5-GATE VERIFY** | All 5 gates |

**Net delta:** ~+1000 words across §2 + §8 + §11 insertions + ~700 words §6 trim + ~400 words §1 contribution rewrite = ~2100 new words.

**Source-of-truth:** §2 Related Work draft per Wave 301 Day 2 §5.1; §8 Reproducibility draft per Wave 301 Day 2 §5.2; §11 Conclusion draft per Wave 301 Day 2 §5.3; §6 trim per Wave 303 input claim 5 (title rename to "Framework Properties"); §1 contribution wording per Wave 303 input claim 6 (DeepSeek §五 4-contribution wording).

### 7.2 D10 cross-ref update pass (3 parallel agents)

**Goal:** Update line-range references in ~17 audit docs from legacy to canonical post-RESOLUTION ranges. Per Wave 301 Day 3 §3.2: 8.5 hours single-agent; 3 hours with 3 parallel agents.

**3 parallel agents, ~3 hours wall-clock:**

| Agent | Audit docs (cluster) | Approx line-range updates |
|---|---|---|
| Cross-ref Agent 1 | `wave297-p1-paper-inventory.md`, `wave297-final.md`, `wave297-p2-paper-design.md`, `wave297-p7-readme-updated.md`, `wave298-final.md` | 5 docs × 8 ranges = 40 updates |
| Cross-ref Agent 2 | `wave298-p7-paper-append.md` (self-references in MS.di.8 + MS.di.10 + MS.di.11), `wave299-paper-a-outline.md`, `wave291-final.md`, `wave292-final.md` | 4 docs × 6 ranges = 24 updates |
| Cross-ref Agent 3 | `wave293-p1-locate-sign.md`, `wave293-p2-verify-direction.md`, `wave293-p3-fix-applied.md`, `wave293-p4-related-docs.md`, `wave293-final.md`, `wave294-final.md`, `wave294-p1-re-inventory.md`, `wave294-p2-medium-fixed.md`, `wave294-p3-low-paper-fixed.md`, `wave294-p4-cross-verify.md` | 10 docs × 4 ranges = 40 updates |

**Total: ~104 line-range updates across ~19 audit docs.**

**Translation table (legacy → canonical):**

| Legacy range | Canonical post-RESOLUTION range | Action |
|---|---|---|
| `L1-L4` (Title) | `L1-L1` | Edit |
| `L7-L12` (Abstract) | `L3-L3` | Edit |
| `L23-L67` (§1) | `L5-L25` | Edit |
| `L71-L258` (§2) | `L28-L72` | Edit |
| `L259-L400` (§3) | `L73-L95` | Edit |
| `L401-L422` (§4) | `L96-L100` | Edit |
| `L423-L484` (§5/§5.5/§6 workflow-internal) | (DELETED) | Edit to "DEL: workflow-internal" |
| `L486-L620` (Appendix W297 P4) | absorbed into `L28-L72` | Edit |
| `L624-L755` (Appendix W297 P5) | absorbed into `L73-L95` | Edit |
| `L758-L841` (Appendix W297 P6) | absorbed into `L96-L100` | Edit |
| `L848-L1083` (Appendix W298 P7) | DELETED | Edit to "Wave 298 P7: see canonical §3/§4/§5" |
| `L1087-L1404` (Wave 300 P5 fold-in) | partial fold into canonical | Edit to "Wave 300 P5: see canonical sections" |

**Verification per audit doc:**
- `grep -rn "paper-flat-flattened.md:L[0-9]" docs/audit/ | grep -E "L(1-4|7-12|23-50|71-258|259-400|401-422|423-484)" | wc -l` returns 0
- Re-run `python3 tools/check_claims_consistency.py` → no drift
- Re-run `mkdocs build --strict` → 0 warnings

### 7.3 D10 USER REVIEW (full-draft sanity check)

**Required user actions at D10 (30-60 minutes):**

1. Review `paper-flat-flattened.md` §1 contributions list (now contains both W297 P2 + DeepSeek additive blocks)
2. Review §2 Related Work (3 paragraphs, JMAA demoted to companion-paper mention)
3. Review §6 Framework Properties (3 lemmas inserted)
4. Review §8 Reproducibility (6 subsections)
5. Review §11 Conclusion (2 paragraphs)
6. Approve D11 IEEEtran typeset OR request edits

**D10 deliverable (user-executed):** Single message: "D10 full-draft review PASS — proceed to D11 IEEEtran typeset" OR "D10 edits requested: [specific line changes]".

### 7.4 D10 final structure (post full-draft assembly)

```
# FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints.   (~30 words)
## Abstract                                                                                (~280 words, 5 sentences)
## 1 Introduction                                                                          (~700 words, 4-item W297 P2 + 4-item DeepSeek additive)
## 2 Related Work                                                                          (~700 words, 3 paragraphs)
## 3 Framework                                                                             (~1200 words, from A.1)
## 4 Scheduler Family                                                                      (~500 words, from A.2)
## 5 Adapter Protocol                                                                      (~600 words, from A.3)
## 6 Framework Properties                                                                  (~700 words, 3 lemmas)
## 7 Empirical Results                                                                     (~1300 words, 5 STRONG/PARTIAL cells)
## 8 Reproducibility                                                                       (~600 words, 6 subsections)
## 9 Limitations                                                                           (~500 words, 6 disclosures)
## 10 Future Work OR fold into §8                                                          (~300 words, 4 implementation items OR folded)
## 11 Conclusion                                                                           (~250 words, 2 paragraphs)
## References                                                                              (~1500 words, 30-50 refs at IEEEtran typeset)
```

**Post-full-draft stats (target):**
- Total words (main text, before IEEEtran): ~6960 (Title 30 + Abstract 280 + §1 700 + §2 700 + §3 1200 + §4 500 + §5 600 + §6 700 + §7 1300 + §8 600 + §9 500 + §10 300 + §11 250 = 7660 — closer to 7700, still under 8500 target with ~800-word buffer for IEEEtran expansion)
- Total lines (estimated): ~1500 (slightly expanded from 1404 due to §2 + §8 + §11 insertions, but Wave 297 P4/P5/P6 framing preambles + Wave 300 P5 fold-in duplicates cleaned up)

---

## 8. D11 — IEEEtran typeset + 14-page verification

**Goal:** Convert `paper-flat-flattened.md` → `paper.tex` with `\documentclass[journal]{IEEEtran}`; wrap 3 lemmas in theorem environments; insert 4 tables + 4 figure placeholders; 30-50-entry `bibliography.bib`; compile to `paper.pdf` ≤ 14 pages.

### 8.1 D11 destructive edits (Phase A from Wave 301 Day 3)

| Action | Detail |
|---|---|
| **PRE-CHECK** | `wc -l docs/drafts/paper-flat-flattened.md` returns ~1500; D10 5-gate PASS; D10 user review PASS |
| **A.1** | Create `docs/drafts/paper.tex` with `\documentclass[journal]{IEEEtran}` preamble + 11 section `\input` directives + bibliography hook |
| **A.2** | Insert IEEEtran class preamble + TNNLS-compliant packages (amsmath, algorithm, algpseudocode, booktabs, graphicx, hyperref, url, xcolor, microtype) |
| **A.3** | Wrap Lemma 1 (composition closure) in `\begin{lemma}...\end{lemma}` + `\begin{proof}...\end{proof}` at §6.1 |
| **A.3 (continued)** | Wrap Lemma 2 (SM byte-determinism) in `\begin{lemma}...\end{lemma}` + `\begin{proof}...\end{proof}` at §6.2 |
| **A.3 (continued)** | Wrap Lemma 3 (ledger tamper-evidence) in `\begin{lemma}...\end{lemma}` + `\begin{proof}...\end{proof}` at §6.3 |
| **A.4** | Insert 4 figure placeholders (TikZ re-draws): (i) FlowA hexagonal architecture, (ii) Re-inference dataflow, (iii) 3-tier experiment hierarchy, (iv) 4-arm H2H schematic |
| **A.5** | Convert Table 4.1 (scheduler taxonomy, 13 schedulers) → `\begin{table}[ht]` + `tabular` |
| **A.6** | Convert Table 5.1 (5-adapter vendor-friendly protocol) → `\begin{table}[ht]` + `tabular` |
| **A.7** | Convert Table 7.1 (5 STRONG/PARTIAL cells, 6-column rubric) → `\begin{table}[ht]` + `tabular` |
| **A.8** | Convert Table 7.2 (6-column Bonferroni table, 4 Bonferroni families + 3-seed pool) → `\begin{table}[ht]` + `tabular` |
| **A.10** | Write `docs/drafts/bibliography.bib` with 30-50 references across 8 domains (FM foundations, FM inference accel, SOTA 2026, typed ML systems, reproducibility, FID/perceptual, statistical methods, ODE solvers) |
| **A.11** | Run `pdflatex paper.tex` → `bibtex paper` → `pdflatex paper.tex` × 2 (final pass) |
| **A.12** | Verify `pdfinfo paper.pdf | grep "Pages:"` returns N ≤ 14 |
| **5-GATE VERIFY** | All 5 gates |

### 8.2 D11 page-count budget

| Page block | Estimated pages | Notes |
|---|---:|---|
| Title + author + abstract | 0.5 | IEEEtran default |
| §1 Introduction | 1.5 | 700 words prose + 1 figure reference |
| §2 Related Work | 1.0 | 700 words prose |
| §3 Framework | 2.0 | 1200 words prose |
| §4 Scheduler Family | 1.0 | 500 words + Table 4.1 |
| §5 Adapter Protocol | 1.0 | 600 words + Table 5.1 |
| §6 Framework Properties | 1.0 | 700 words + 3 lemma environments |
| §7 Empirical Results | 2.0 | 1300 words + Tables 7.1 + 7.2 + Figure 3 |
| §8 Reproducibility | 0.5 | 600 words + reference to Figure 4 |
| §9 Limitations (incl. folded §10) | 0.5 | 500-800 words |
| §11 Conclusion | 0.5 | 250 words |
| Bibliography (30-50 refs) | 1.5-2.5 | IEEEtran numeric |
| **TOTAL** | **~12-14** | **FITS** |

### 8.3 D11 page-count failure handling

If `pdfinfo` reports Pages > 14:

1. **Conservative trim:** Reduce each lemma body by 50 words; consolidate Tables 4.1 + 5.1 into one "Protocol Surface" table; remove redundant prose in §3 (collapse "Protocol Algebra" subsection intro by 100 words).
2. **Aggressive trim:** Defer §3 sketches (3 sketches totaling ~1200 words) to supplementary; main §3 retains 3 lemmas + 1 sketch only; supplementary has full collection. Wait — Wave 303 has 3 lemmas, not 6. If still over, defer §2 Related Work to supplementary.
3. **Last-resort:** Move §2 Related Work to supplementary; main paper §2 is condensed to 1-paragraph citation summary; total main text drops to ~10 pages.
4. **Re-typeset** after each trim step and re-verify page count.

### 8.4 D11 deliverables

- `docs/drafts/paper.tex` — IEEEtran typeset Paper A (~5000-6500 lines LaTeX)
- `docs/drafts/bibliography.bib` — 30-50 references
- `docs/build_pdf/paper.pdf` — Compiled paper PDF ≤ 14 pages
- `docs/paper-tnnls.pdf` — Top-level paper PDF (TNNLS submission target, copy from `docs/build_pdf/paper.pdf`)

---

## 9. D12 — Submission package + Paper B skeleton

**Goal:** Refresh `tnnls_submission/MANIFEST.md` SHA-256; generate `source.zip`; copy `paper.pdf` to `docs/paper-tnnls.pdf` and `tnnls_submission/paper.pdf`; generate `highlight_blurb.pdf`; create `docs/drafts/paper-b-jmaa/skeleton.md` (separate directory, separate git branch `paper-b-skeleton`).

### 9.1 D12 destructive edits (Phase C from Wave 301 Day 3)

| Action | Detail |
|---|---|
| **PRE-CHECK** | `pdfinfo docs/build_pdf/paper.pdf` returns Pages ≤ 14; 5-gate PASS |
| **C.1** | Verify `tnnls_submission/MANIFEST.md` SHA-256 hashes match on-disk files |
| **C.2** | Verify `tnnls_submission/cover_letter.md` (17 `[USER TO FILL: ...]` placeholders per `FILL_GUIDE.md`) |
| **C.3** | Verify `tnnls_submission/highlights.md` (3 × 85-char highlights) |
| **C.4** | Verify `tnnls_submission/tables.md` + `tnnls_submission/figures.md` (5+ ASCII tables/figures) |
| **C.5** | Verify `tnnls_submission/data_availability.md` |
| **C.6** | Verify `tnnls_submission/submission_checklist.md` |
| **C.7** | Generate `tnnls_submission/source.zip` (paper.tex + bibliography.bib + figures/ + IEEEtran.cls + md_to_tex.py + all inline assets) |
| **C.8** | Copy `docs/build_pdf/paper.pdf` to `docs/paper-tnnls.pdf` AND `tnnls_submission/paper.pdf` |
| **C.9** | Generate `tnnls_submission/highlight_blurb.pdf` (3 highlight bullets + abstract + author bios for Editorial Manager "Highlights" paste) |
| **C.10** | Refresh `tnnls_submission/MANIFEST.md` with new SHA-256 + sizes |
| **5-GATE VERIFY** | All 5 gates |

### 9.2 D12 Paper B skeleton (Phase D from Wave 301 Day 3)

**Goal:** Create `docs/drafts/paper-b-jmaa/` directory on separate git branch `paper-b-skeleton` (NOT merged to main).

| Action | Detail |
|---|---|
| **D.1** | `mkdir -p docs/drafts/paper-b-jmaa/refs docs/drafts/paper-b-jmaa/figures` |
| **D.2** | Write `docs/drafts/paper-b-jmaa/skeleton.md` (§1 Introduction 200-400w referencing Paper A as framework foundation; 11-section outline; boundary statement "Paper B is the theoretical companion to Paper A; Paper A is the framework paper") |
| **D.3** | Write `docs/drafts/paper-b-jmaa/experiments.md` (10-experiment list per Wave 301 Day 3 §5.4, ~35 GPU-hours total) |
| **D.4** | Write `docs/drafts/paper-b-jmaa/regime-sweep.md` (3-tier stratification: easy/medium/hard per baseline-metric quantile) |
| **D.5** | Write `docs/drafts/paper-b-jmaa/contributions.md` (4-6 primary contributions: JMAA Theorem 1 4-paper-quantities, CodimensionSheetScheduler sweep, paper-quantity-driven scheduler family, 16-site integration, convergence analysis, FID Δ=0% evidence) |
| **D.6** | Set up `docs/drafts/paper-b-jmaa/refs/refs.md` (BibTeX stub) |
| **D.7** | Initialize git branch `paper-b-skeleton` (do NOT merge into main) |
| **5-GATE VERIFY** | All 5 gates |

### 9.3 D12 deliverables

- `tnnls_submission/source.zip` — Submission source bundle
- `tnnls_submission/paper.pdf` — Submission PDF (copies from `docs/paper-tnnls.pdf`)
- `tnnls_submission/MANIFEST.md` (refreshed) — SHA-256 + size + role catalog
- `tnnls_submission/highlight_blurb.pdf` — Highlights + abstract + author bios
- `docs/drafts/paper-b-jmaa/skeleton.md` — Paper B §1 + outline
- `docs/drafts/paper-b-jmaa/experiments.md` — 10-experiment list
- `docs/drafts/paper-b-jmaa/regime-sweep.md` — 3-tier prerequisite
- `docs/drafts/paper-b-jmaa/contributions.md` — 4-6 contributions
- `docs/drafts/paper-b-jmaa/refs/refs.md` — BibTeX stub
- Git branch `paper-b-skeleton` — Locked skeleton reference (NOT main)

---

## 10. D13 — User final review + sign-off

**Goal:** Present complete TNNLS submission package to user for final review and sign-off before D14 ScholarOne upload.

### 10.1 D13 USER REVIEW (final sign-off, 30-60 minutes)

**Required user actions at D13:**

1. Open `docs/paper-tnnls.pdf` and verify ≤ 14 pages
2. Open `tnnls_submission/source.zip` and verify contents (paper.tex, bibliography.bib, figures/, IEEEtran.cls, paper.pdf)
3. Open `tnnls_submission/cover_letter.md` and fill in 17 `[USER TO FILL: ...]` placeholders
4. Open `tnnls_submission/highlights.md` and verify 3 × 85-char highlights
5. Open `tnnls_submission/MANIFEST.md` and verify SHA-256 columns match on-disk files
6. Open `docs/drafts/paper-b-jmaa/skeleton.md` and verify Paper B boundary is correct
7. Verify IEEE copyright + DORA workflow readiness (ScholarOne requirements)
8. Authorize D14 ScholarOne upload

**D13 deliverable (user-executed):** Single message: "D13 final review PASS — proceed to D14 ScholarOne upload" OR "D13 edits requested: [specific changes]".

**D13 does NOT push to remote.** Submission is via ScholarOne upload by user (D14).

### 10.2 D13 sign-off conditions

User must explicitly authorize all of the following:
- D14 ScholarOne upload of `paper.pdf`
- D14 IEEE copyright transfer (CTF) workflow
- D14 DORA workflow (IEEE Data and Software Availability)
- D14 author bios finalization (placeholder → user fills at upload time)

If any condition is missing, agent re-engages user.

---

## 11. D14 — Submit to TNNLS ScholarOne

**Goal:** User uploads `paper.pdf` + `source.zip` + `cover_letter.md` + `highlights.md` + `MANIFEST.md` to `mc.manuscriptcentral.com/tnnls` with IEEE copyright + DORA workflow.

### 11.1 D14 user actions

| # | Action | Source | Estimated time |
|---:|---|---|---:|
| 1 | Log in to TNNLS ScholarOne (mc.manuscriptcentral.com/tnnls) | Browser | 5 min |
| 2 | Click "New Submission" → Journal Article | Browser | 2 min |
| 3 | Upload `tnnls_submission/paper.pdf` | Browser upload | 2 min |
| 4 | Upload `tnnls_submission/source.zip` (source files + LaTeX) | Browser upload | 2 min |
| 5 | Paste 3 highlights from `tnnls_submission/highlight_blurb.pdf` | Browser paste | 5 min |
| 6 | Fill cover letter fields (authors block + AE address + 5 reviewers + corresponding author) | Browser form | 15 min |
| 7 | Fill suggested reviewers list (5-8 names from TNNLS editorial scope) | Browser form | 10 min |
| 8 | Fill IEEE copyright transfer (CTF) | Browser form | 10 min |
| 9 | Fill DORA workflow (data + software availability statements) | Browser form | 10 min |
| 10 | Upload author bios (placeholder from D6 → final at D14) | Browser upload | 5 min |
| 11 | Final preview + click "Submit" | Browser | 5 min |
| 12 | Capture ScholarOne submission confirmation (paper ID, submission date, AE name) | Screenshot/email | 5 min |

**Total D14 time: ~75 minutes** (most time is form-filling, not paper upload).

### 11.2 D14 post-submission

| Action | Detail |
|---|---|
| Log submission | `docs/audit/wave303-submission-record.md` (paper ID, submission date, AE name) |
| Set calendar reminder | TNNLS first decision timeline per LetPub data: 3-5 months from submission date (2026-10-08 → Q1-Q2 2027 first decision) |
| Push to remote | After ScholarOne upload, push `paper-b-skeleton` git branch to remote (Paper B is on its own branch; main branch contains nothing new because paper-flat-flattened.md is the only deliverable that was modified and that's local-only) |
| 5-GATE FINAL VERIFY | All 5 gates on final state |

### 11.3 D14 risks

| Risk | Mitigation |
|---|---|
| ScholarOne upload fails | Retry; if persistent failure, file bug report with IEEE (rare) |
| IEEE copyright transfer system is down | Defer CTF to post-submission; submission still valid but flagged for follow-up |
| DORA workflow requires data DOI | Generate Zenodo DOI for framework code + reproducibility record (Wave 287 pattern); deferred to D14+1 |
| User unable to log in to ScholarOne | Confirm credentials at D13; reset password if needed |

---

## 12. 5-Gate Verification Gates Per Commit

**Per Wave 268 strict-clean + Wave 300 P3 §7 invariant: every destructive commit must re-establish the 5-gate baseline.**

### 12.1 5-gate suite (full)

| # | Gate | Command | Expected result |
|:---:|---|---|---|
| 1 | D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, ≤ 3 pre-existing DeprecationWarnings, ~8.61s |
| 2 | ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! |
| 3 | mkdocs strict 0 | `mkdocs build --strict` | exit_code=0, 0 project warnings, ~21.84s |
| 4 | claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL / No drift detected |
| 5 | vendored untouched | `git diff --stat -- vendored/ data/` | (empty) |

### 12.2 Per-day gate requirements

| Day | Destructive edits | 5-gate required | Additional day-specific gates |
|:---:|---|:---:|:---|
| D0 | None (READ-ONLY) | Yes (baseline) | G0.1-G0.5 (user authorization) |
| D1 | Title block | Yes | D.4 line count = 1400 |
| D2 | Abstract block | Yes | D.4 line count = 1390; abstract word count = 280 |
| D3 | §1 Intro block | Yes | D.4 line count = 1367; §1 word count = 700; contributions count = 4 items |
| D4 | §2 Algorithm + §3/§4/§5 promotion | Yes | D.4 line count = ~1312; §3 + §4 + §5 word count = 2300; cosine sign flip applied |
| D5 | §3 Experiments + §5/§6 workflow-internal | Yes | D.4 line count = ~1239; §7 word count = 1300; 5 STRONG/PARTIAL cells in main |
| D6 | §4 Limitations + §9/§10 promotion + framing preambles | Yes | D.4 line count = ~1301; §9 word count = 500; cover letter updated |
| D7 | None (Path A draft) | Yes (baseline unchanged) | Lemma 1 file exists; word count 550-650; 4 file:line anchors verified |
| D8 | None (Path A draft) | Yes (baseline unchanged) | Lemma 1 finalized; Lemma 2 file exists; word count 350-450 |
| D9 | None (Path A draft) | Yes (baseline unchanged) | Lemma 2 finalized; Lemma 3 file exists; word count 300-400 |
| D10 | §6 trim + §1 contribution rewrite + §2/§8/§11 insertions | Yes | Main text word count = 7700; cross-ref update pass complete; 19 audit docs updated |
| D11 | IEEEtran conversion (paper.tex) | Yes | pdfinfo Pages ≤ 14; 3 lemma environments present; 30-50 bibliography entries |
| D12 | Submission package + Paper B skeleton | Yes | source.zip present; MANIFEST SHA consistent; Paper B skeleton on `paper-b-skeleton` branch |
| D13 | None (user review only) | Yes (final baseline) | User sign-off captured |
| D14 | None (ScholarOne upload only) | Yes (post-submission) | ScholarOne confirmation logged in `wave303-submission-record.md` |

### 12.3 Failure handling per commit

If any 5-gate fails after a destructive edit:

1. **STOP execution immediately**
2. **Revert the edit** via `git checkout docs/drafts/paper-flat-flattened.md` (full file revert)
3. **Diagnose the failure** (which gate failed, which line introduced the regression)
4. **Apply fix** OR **escalate to user** if the fix is non-trivial
5. **Re-run all 5 gates** to confirm baseline restored
6. **Resume execution** from the step before the failure

### 12.4 Wave 268 strict-clean audit log

Per Wave 300 P3 §7: every destructive deletion step logs an entry to `docs/audit/wave303-resolution-execution-log.md` (created during D1):

| Entry | Content |
|---|---|
| Step ID | D1/D2/.../D14 |
| Action | DELETE/PROMOTE/INLINE/etc. |
| Line count delta | (e.g., -4 lines) |
| 5-gate result | PASS/FAIL per gate |
| Source-of-truth | (e.g., Wave 297 P3 §1 prose) |
| Cross-ref impact | (e.g., 0 audit docs updated at this step) |
| Author | Wave 303 agent ID |
| Timestamp | 2026-09-25T... (ISO 8601) |

---

## 13. Risk Register (Wave 303 overall)

### 13.1 Critical risks (HIGH likelihood, HIGH impact)

| Risk | Mitigation |
|---|---|
| D0 user authorization not granted within 2-3 hours | Agent continues READ-ONLY preparation (e.g., D7-D9 Path A draft); user reminded at D1; D1-D6 wait until authorization |
| D3 user boundary clearness check fails | Agent applies edits per user feedback; re-runs 5-gate; re-presents to user; +2-3 hours wall-clock impact |
| D6 user Path A start review fails | Same as D3 — applies edits, re-presents |
| D10 user full-draft review fails | Same as D3 — applies edits; if major structural issue, may need extra day (+1 wall-clock → 15-day total) |
| D13 user final sign-off fails | Same — applies edits; if blocking, may need extra day (+1 → 16-day total) |
| 8500-word main text target exceeded | Per §7.1 §11 word budget; if D10 main text exceeds 8500, agent trims §7 (5 cells → 4 cells) or §3 (drop a section); supplementary absorbs excess |
| Page count exceeds 14 pages | Per §8.3 — conservative / aggressive / last-resort trim; re-typeset |
| Cross-ref update pass fails on 1+ audit docs | Per §7.2 — 3 parallel agents; per-doc verification; 5-gate re-run |

### 13.2 Medium risks (MEDIUM likelihood, MEDIUM impact)

| Risk | Mitigation |
|---|---|
| Async determinism narrowed too aggressively in Lemma 2 → reviewer flags as "not actually byte-deterministic" | Per Wave 303 input claim 4: frame narrowing as corollary in supplementary; main text explicit "given fixed asyncio loop ordering" caveat |
| 4 sub-claims in Lemma 1 look like 4 separate lemmas | Use `### Sub-claim 1.1-1.4` subsections within Lemma 1 |
| 5 STRONG/PARTIAL cells might trigger "thin evidence" review comment | Per Wave 303 input claim 2: flag in §9 Limitations paragraph as known trade-off; supplementary absorbs 6 additional cells |
| TikZ figure re-draw exceeds 2 hours | Defer 1-2 figures to supplementary; keep Figure 1 + Figure 4 in main |
| Bibliography.bib 30-50 references incomplete | Cap at 25 minimum; defer 5-10 to camera-ready |
| ScholarOne upload fails | Retry; if persistent, contact IEEE support |
| DORA workflow requires data DOI not yet generated | Generate Zenodo DOI at D14+1 (post-submission) |

### 13.3 Low risks (LOW likelihood, LOW impact)

| Risk | Mitigation |
|---|---|
| Wave 294 P2 cosine sign flip breaks a downstream claim | Wave 294 P2 audit verified additive-safe; if drift, revert + fix |
| Path A agent (Lemma 1/2/3) runs out of file:line anchors | All anchors pre-computed by Wave 301 Day 2; pin to git commit SHA |
| Wave 297 P3 §1 prose drifts between W297 source and D3 file | Per DS-01, apply verbatim; diff W297 P3 source vs canonical §1 |
| Paper B skeleton branch accidentally merged to main | Per §9.2: D.7 uses `git checkout -b paper-b-skeleton`; never merge to main without explicit user approval |

---

## 14. Files Referenced (READ-ONLY)

### 14.1 Source-of-truth files (READ-ONLY)

- `docs/drafts/paper-flat-flattened.md` (1404 lines, dual-present, MODIFIED at D1-D10 only)
- `docs/audit/wave301-day0-prompt.md` (D0 user input)
- `docs/audit/wave301-day1-execution-plan.md` (D1-D6 RESOLUTION plan, this plan supersedes its D1 sequencing)
- `docs/audit/wave301-day2-execution-plan.md` (D7-D9 Path A plan, this plan supersedes its 6-lemma scope with 3-lemma scope)
- `docs/audit/wave301-day3-execution-plan.md` (D11-D12 IEEEtran + submission package plan, this plan follows its Phase A/C/D structure)
- `docs/audit/wave300-p3-resolution-plan.md` (Wave 300 P3 RESOLUTION plan source)
- `docs/audit/wave297-p2-paper-design.md` (11-section canonical structure + Wave 297 P2 contributions)
- `docs/audit/wave297-p3-intro-rewritten.md` (§1 prose source, apply verbatim at D3)
- `docs/audit/wave297-p4-framework-rewritten.md` (§3/§4/§5 prose source, apply verbatim at D4)
- `docs/audit/wave297-p5-empirical-rewritten.md` (§7 prose source, apply verbatim at D5)
- `docs/audit/wave297-p6-limitations-rewritten.md` (§9/§10 prose source, apply verbatim at D6)
- `docs/audit/wave298-p7-paper-append.md` (deep innovations source — folded into canonical §3/§4/§5 at D4-D5)
- `docs/audit/wave294-p2-medium-fixed.md` (1 HIGH + 2 MEDIUM inline fixes — apply at D4)
- `docs/audit/wave294-p3-low-paper-fixed.md` (3 LOW inline fixes — apply at D4)
- `docs/audit/wave293-p3-fix-applied.md` (cosine sign flip Wave 293 M-HIGH-1 — apply at D4)
- `docs/audit/wave298-p5-literature-compare.md` (§2 Related Work source — fresh-write at D10)
- `docs/audit/wave291-p5-3seed-results.md` (§7 statistical methodology source)
- `docs/audit/wave292-p1-pipeline-inventory.md` (§9.1.1 + §10.1.1 roadmap source)
- `docs/audit/wave292-p2-config-genealogy.md` (§7.4 framework-not-theory source)
- `docs/audit/wave296-p1-architecture.md` (§3 + §5 capability-token design source)
- `docs/audit/wave296-p2-cache.md` (§3 + §10 PaperQuantitiesCache source)
- `docs/audit/wave286-p-fid-gpu-fix.md` (§8 Reproducibility source)
- `docs/audit/wave290-p3-batched-harness.md` (§8 Reproducibility source)
- `docs/audit/wave268-strict-clean.md` (Wave 268 strict-clean rule source)
- `docs/audit/wave299-paper-b-deferred.md` (Paper B boundary + JMAA demotion rationale)
- `docs/audit/wave274-p7-manifest-sha.md` (MANIFEST SHA self-referencing pattern)

### 14.2 Files to be created by Wave 303

| Day | File | Size | Purpose |
|:---:|---|---|---|
| D1 | `docs/audit/wave303-resolution-execution-log.md` | ~50 lines | Per-step deletion log (Wave 268 strict-clean audit) |
| D7 | `docs/audit/wave303-day7-lemma1.md` | ~600 words | Lemma 1 prose-proof draft |
| D8 | `docs/audit/wave303-day8-lemma2.md` | ~400 words | Lemma 2 prose-proof draft |
| D9 | `docs/audit/wave303-day9-lemma3.md` | ~350 words | Lemma 3 prose-proof draft |
| D11 | `docs/drafts/paper.tex` | ~5000-6500 lines | IEEEtran typeset Paper A |
| D11 | `docs/drafts/bibliography.bib` | ~1500 lines | BibTeX for IEEEtran (30-50 refs) |
| D11 | `docs/build_pdf/paper.pdf` | ~700KB | Compiled paper PDF ≤ 14 pages |
| D11 | `docs/paper-tnnls.pdf` | ~700KB | Top-level paper PDF |
| D11 | `docs/drafts/figures/*.tex` | ~200 lines | TikZ figure re-draws (4 files) |
| D12 | `tnnls_submission/source.zip` | ~5-10MB | Submission source bundle |
| D12 | `tnnls_submission/paper.pdf` | ~700KB | Submission PDF copy |
| D12 | `tnnls_submission/MANIFEST.md` (refreshed) | ~80 lines | SHA-256 + size + role catalog |
| D12 | `tnnls_submission/highlight_blurb.pdf` | ~50KB | Highlights + abstract + author bios |
| D12 | `docs/drafts/paper-b-jmaa/README.md` | ~50 lines | Paper B scope + boundary |
| D12 | `docs/drafts/paper-b-jmaa/skeleton.md` | ~600 lines | §1 + 11-section outline |
| D12 | `docs/drafts/paper-b-jmaa/experiments.md` | ~250 lines | 10-experiment list |
| D12 | `docs/drafts/paper-b-jmaa/regime-sweep.md` | ~150 lines | 3-tier prerequisite |
| D12 | `docs/drafts/paper-b-jmaa/contributions.md` | ~100 lines | 4-6 contributions |
| D12 | `docs/drafts/paper-b-jmaa/refs/refs.md` | ~80 lines | BibTeX stub |
| D14 | `docs/audit/wave303-submission-record.md` | ~30 lines | ScholarOne confirmation log |

**Total Wave 303 output: ~17 new files + 4 refreshed files + 1 git branch.**

### 14.3 Files NOT modified by Wave 303

- `vendored/` and `data/` directories (5-gate #5 enforces)
- `adaptive_reflow/` framework code (5-gate #1 enforces via D.4 30/30)
- `tests/` test code
- `tools/` tooling
- `docs/audit/wave301-day{1,2,3}-execution-plan.md` (READ-ONLY predecessors; this plan supersedes at the meta level)
- `docs/audit/wave301-day0-prompt.md` (READ-ONLY D0 user input)

---

## 15. Wave 303 vs DeepSeek Recommendations — Summary of Integration

| DeepSeek recommendation | Wave 303 integration |
|---|---|
| §一: 砍论文规模从 3.6 万词到 8500 词 | D1-D10 deletes ~11000 words; D10 inserts ~2100 fresh words; net ~7700 words main text (under 8500 target with ~800-word buffer) |
| §二: 14 天时间线 + 4 review points (D3/D6/D10/D13) | Matches exactly: 14-day timeline; 4 review points at D3/D6/D10/D13 |
| §三: Path A 3 lemmas (composition closure + SM byte-determinism + tamper-evidence) at 5 days | Matches: 3 lemmas at D7-D9 (5 agent-days compressed to 3 wall-clock days via 3 parallel agents) |
| §四: §6 改名 "Framework Properties" + JMAA 移除 | Matches: D6 placeholder rename + D10 full §6 trim with 3 lemma subsections; JMAA → Paper B |
| §五: 4 contributions wording (framework + formal + empirical + reproducibility) | Matches: D10 §1 contribution rewrite to DeepSeek wording; Wave 297 P2 list preserved as legacy additive block per Wave 268 strict-clean |
| §六: Day 0 user 6 decisions + Wave 304 destructive authorization | Matches: D0 §2.1 10-action user authorization list; D0 §2.3 verification gates |
| §七: Wave 302 Paper B prep 继续跑 | Matches: D12 Paper B skeleton on separate git branch `paper-b-skeleton`; Wave 302 continues in parallel |
| §八: TNNLS 录用概率 35-45% | Out of scope for Wave 303 plan (probability estimate only); matches DeepSeek's framing |
| §九: 目标锁定 TNNLS, 14 天写完, 8500 词, 3 lemma, JMAA 全部移除 | Matches: D0-D14 plan as described |

### 15.1 Wave 303 corrections to DeepSeek (per Wave 303 input claims)

| DeepSeek claim | Wave 303 correction | Source |
|---|---|---|
| "3-day submission-ready" framing | REJECTED — 14-day plan is the realistic floor; 3 days is not feasible | Wave 301 day 0 line 22 |
| "D9 full-draft assembly of 8500 words in 1 day" | EXPANDED to D9-D10 (2 days); D9 = Lemma 2/3 finish, D10 = §6 trim + 4 contributions + Related Work + cross-ref update | Wave 303 input claim 3 |
| "Path A 3 lemmas × 5 days total = D7-8 (2 calendar days)" | EXPANDED to D7-D9 (3 calendar days) with 3 parallel agents; honest 5-agent-day accounting | Wave 303 input claim 3 + claim 4 |
| "Path A 3 lemmas intermediate depth" | ACCEPTED; §6 retitled "Deterministic Core Properties" per Wave 303 input claim 4 framing constraint (Kept "Framework Properties" per DeepSeek §四 to align with user's §6 rename decision) | Wave 303 input claim 4 |
| "Protocol composition closure as 1 lemma" | ACCEPTED but explicitly bundle 4 sub-claims (SchedulerProtocol + PolicyDriverProtocol + MergeOperator + RestartBlenderProtocol) with `### Sub-claim 1.1-1.4` subsections | Wave 303 input claim 4 |
| "D11-12 cross-ref update pass (no parallelization)" | CORRECTED to 3 parallel agents (~3 hours wall-clock) per Wave 301 Day 3 §3.2 | Wave 301 Day 3 §3.2 |
| "Paper A 4-contribution list drops JMAA" | ACCEPTED but Wave 297 P2 list preserved as legacy additive block per Wave 268 strict-clean; new additive block contains DeepSeek wording | Wave 303 input claim 6 |

---

## 16. Summary

**Wave 303 D0-D14 produces a TNNLS-ready submission in 14 wall-clock days, integrating DeepSeek teacher's 14-day plan with corrections to timeline pressure (D9-D10 expansion) and §6 title framing.**

**D0 (user-only):** Open `wave301-day0-prompt.md`, decide 6 RESOLUTION pairs, authorize Wave 268 strict-clean break, lock TNNLS, confirm 14-day timeline, confirm §6 rename, confirm 4-contribution wording, confirm JMAA → Paper B, confirm §10 disposition. 2-3 hours.

**D1-3 (RESOLUTION Part 1):** Title + Abstract + §1 Introduction. Pair 1/2/3 destructive deletes with Wave 297 P2/P3 promotions. D3 user review for boundary clearness.

**D4-5 (RESOLUTION Part 2):** §2 Algorithm → §3/§4/§5 framework promotion (D4); §3 Experiments → §7 empirical results promotion (D5); Wave 294 P2 inline fixes at D4.

**D6 (RESOLUTION Part 3):** §4 Limitations → §9 + §10 promotion; framing preamble cleanup; §6 placeholder rename; cover letter rebalance. D6 user review for Path A start.

**D7-9 (Path A, 3 parallel agents):** Lemma 1 (composition closure, D7-8); Lemma 2 (SM byte-determinism, D8-9); Lemma 3 (ledger tamper-evidence, D9). Total 5 agent-days compressed to 3 wall-clock days.

**D10 (§6 trim + 4 contributions + Related Work):** Insert 3 lemmas into §6 Framework Properties; rewrite §1 contributions to DeepSeek wording; fresh-write §2 Related Work + §8 Reproducibility + §11 Conclusion; cross-ref update pass via 3 parallel agents. D10 user review for full-draft sanity check.

**D11 (IEEEtran typeset):** Convert paper → paper.tex; wrap 3 lemmas in theorem environments; insert 4 tables + 4 figure placeholders (TikZ); 30-50-entry bibliography; compile to paper.pdf ≤ 14 pages.

**D12 (Submission package + Paper B skeleton):** Refresh MANIFEST SHA; generate source.zip + paper.pdf + highlight_blurb.pdf; create Paper B skeleton on separate git branch `paper-b-skeleton`.

**D13 (User final review + sign-off):** Verify ≤ 14 pages, MANIFEST SHA, cover letter placeholders, highlights, Paper B boundary; user authorizes D14 ScholarOne upload.

**D14 (Submit to TNNLS ScholarOne):** User uploads paper.pdf + source.zip + cover letter + highlights; IEEE copyright + DORA workflow; ScholarOne confirmation logged.

**5-gate verification per commit** (D.4 30/30 + ruff 0 + mkdocs strict 0 + claims no-drift + vendored untouched); Wave 268 strict-clean invariant enforced at every destructive step.

**TNNLS acceptance probability:** 35-45% per DeepSeek §八; 40-50% if engineering reproducibility (D.4 30/30 + 6-gate CI + vendor purity) is emphasized in §1 contribution (iv).

**Submission target date: 2026-10-08.**

---

**END OF WAVE 303 DAY 0-14 PLAN.** This plan is READ-ONLY and serves as the canonical source-of-truth for the 14-day TNNLS submission workflow. Wave 303 will not execute until D0 user authorization is granted. The 4 user review boundaries (D3, D6, D10, D13) provide scope-control checkpoints; the 5-gate suite + Wave 268 strict-clean rule provide invariant enforcement at every commit.
