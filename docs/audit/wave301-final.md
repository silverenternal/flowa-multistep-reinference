# Wave 301 — Final Verification + 3-Day Execution Plans

**Date:** 2026-09-23
**Mode:** READ-ONLY verification + READY-TO-EXECUTE plans (no destructive edits without user authorization)
**Author:** Wave 301 final verification + commit agent
**Status:** All 5 gates **PASS** on current unchanged repo + ruff regression in new test file **FIXED**; **NO PUSH** per "暂不 push" directive
**Predecessor:** `4df5ae2` Wave 300 — paper-A 8-week strategy (RESOLUTION plan + Path A theorems + paper-A fold-in draft)

---

## 0. TL;DR

The user (deepseek老师) has now provided a corrected 3-day plan that:
- **Targets TNNLS** (not ICLR — abstract deadline already past + reciprocal-review gate unsatisfied for undergraduate author)
- **Sets the boundary clearly**: Paper A = framework + 7 contributions + 11-cell empirical (NO JMAA); Paper B = JMAA theory + scheduler experiments + convergence (cites Paper A as framework base)
- **Authorizes a workflow that is gated on user sign-off**: Day 0 (user only) + Days 1-3 (agent-driven)
- **Instructs**: "暂不 push" = NO PUSH this wave

This document:
1. Verifies the 5 gates on the **current unchanged repo** (the new wave-301 outputs are NOT destructive; they are 4 audit-doc READ-ONLY plans + 1 property test file + 3 paper-B plans)
2. **Fixes** a ruff regression in the new property test file (5 violations; non-destructive cosmetic + idiomatic fix)
3. Documents the **3 ready-to-execute plans** (gated on user authorization)
4. Lists **open questions for user** blocking Day 1

---

## 1. 5-Gate Verification (verified PASS after ruff fix)

| # | Gate | Command | Result | Status |
|:--:|---|---|---|:--:|
| 1 | ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! | **PASS** |
| 2 | D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 pre-existing DeprecationWarnings, ~1.4s | **PASS** |
| 3 | claims no drift | `python3 tools/check_claims_consistency.py` | 61 active / 0 provisional / 2 deprecated; CLM-040 forced PROVISIONAL; **No drift detected** | **PASS** |
| 4 | mkdocs strict 0 warnings | `mkdocs build --strict` | exit_code=0, 0 project warnings (Documentation built in 21.28s) | **PASS** |
| 5 | vendored/data NOT touched | `git diff --stat -- vendored/ data/` | (empty) | **PASS** |

### 1.1 Ruff regression found and fixed in new file

The newly-added `tests/property/test_state_machine_byte_determinism.py` (Wave 300 P4 gap closure for ADR-0006 §3.2) had **5 ruff violations** on first run:

| # | Code | Location | Fix |
|:--:|---|---|---|
| 1 | SIM105 | line 216 | Replaced `try/except Exception/pass` with `contextlib.suppress(Exception)` |
| 2 | SIM105 | line 277 | Same fix |
| 3 | SIM105 | line 325 | Same fix |
| 4 | SIM105 | line 389 | Same fix |
| 5 | W292 | line 462 | Added trailing newline |

**Imports added:** `import contextlib`
**No noqa comments removed** (the `BLE001` noqa was on the previous `except Exception` clauses; `contextlib.suppress(Exception)` does not need it).

After fix: `ruff check adaptive_reflow/ tests/ scripts/ tools/` returns "All checks passed!" — gate 1 back to green.

### 1.2 Hypothesis import skip (informational, not a gate failure)

Running `pytest tests/property/test_state_machine_byte_determinism.py` triggers a `pytest.importorskip("hypothesis")` skip in `tests/property/conftest.py` (line 38) — the `hypothesis` package is not installed in this venv. The conftest is **designed to skip the entire property subtree** if `hypothesis` is unavailable. This matches Wave 286 precedent: `test_engine_round_determinism.py` has the same gating and is committed but never executed in this venv. **Not a gate failure**; gate 2 is `tests/test_d4_regression_vectors.py` specifically.

---

## 2. Files committed (this wave)

All files are READ-ONLY audit/plan docs (no destructive edits) + 1 property test file (with ruff fix applied) + 3 paper-B READ-ONLY plan docs:

| File | Lines | Type | Purpose |
|---|--:|---|---|
| `docs/audit/wave301-day0-prompt.md` | 208 | READ-ONLY plan | User authorization prompt: 6 dual-present pair decisions + Wave 268 strict-clean break + venue lock + timeline selection |
| `docs/audit/wave301-day1-execution-plan.md` | 538 | READ-ONLY plan | Day 1 RESOLUTION pass execution plan (gated on Day 0 user sign-off) |
| `docs/audit/wave301-day2-execution-plan.md` | 426 | READ-ONLY plan | Day 2 Path A prose-proofs + §2/§8/§11 fresh-writing + boundary-clearness user review |
| `docs/audit/wave301-day3-execution-plan.md` | 731 | READ-ONLY plan | Day 3 IEEEtran typesetting + submission package + Paper B skeleton |
| `docs/audit/wave302-p1-regime-sweep-design.md` | 426 | READ-ONLY plan | Wave 302 Paper-B experiment design: regime-sweep prerequisite |
| `docs/audit/wave302-p2-exp-b1-smoke.md` | 275 | READ-ONLY plan | Wave 302 Exp B1: smoke test for paper-quantity scheduler |
| `docs/audit/wave302-p4-r6-replication.md` | 157 | READ-ONLY plan | Wave 302 R6 replication design (CIFAR-10) |
| `tests/property/test_state_machine_byte_determinism.py` | 454 | NEW TEST | State-machine byte-determinism property test (Wave 300 P4 gap closure; ruff-fixed in this commit) |

**Total:** 8 new files / **3,215 lines** added; **0 deletions**.

**No edits to** `docs/drafts/paper-flat-flattened.md` — Wave 268 strict-clean holds; destructive edits gated on Day 0 user authorization.

---

## 3. Decision Tree for Target Journal

The user's deepseek teacher note proposed "3 days to write + submit". The workflow agent added three ICLR 2027 blockers the teacher missed. Here is the **decision tree** as executed by the verification pass:

```
Q1: Has ICLR 2027 abstract deadline already passed?
    YES (Sep 18, 2026 AOE — 5 days lapsed) ───→ ELIMINATE ICLR 2027
    NO                                       ───→ continue
                                                │
Q3: Does author meet ICLR reciprocal-reviewing gate?
    (co-author on accepted ICLR/NeurIPS/ICML/CVPR/ICCV/ECCV/etc paper)
    YES                                       ───→ ICLR 2027 viable
    NO (undergraduate, no qualifying pubs)    ───→ ELIMINATE ICLR 2027
                                                │
Q4: Are all authors OpenReview profiles moderated?
    YES                                       ───→ (already eliminated by Q1)
    NO (new profile, 2-week moderation)       ───→ ELIMINATE ICLR 2027
                                                │
Q5: Does author need a venue that doesn't require abstract pre-registration?
    YES (TNNLS via ScholarOne, rolling)       ───→ **TNNLS = PRIMARY**
    NO                                        ───→ ICLR 2028 as backup
                                                │
Q6: Does author accept 3-5 month first-decision timeline?
    YES (Q4 2026 submit → Q1-Q2 2027 first decision) ───→ **TNNLS = PRIMARY**
    NO (need faster turnaround)              ───→ consider workshop venues (NeurIPS workshop Dec 2026)
                                                │
Q7: Does author accept 14-page TOTAL limit?
    YES (matches current 1069-line outline)   ───→ **TNNLS = PRIMARY**
    NO                                        ───→ TVCG / TOCHI alt
```

**Recommendation locked in by the decision tree:** **TNNLS (IEEE Transactions on Neural Networks and Learning Systems)** as primary; **ICLR 2028** as backup target once publication history allows.

---

## 4. Day 0 Prompt Reference

The full user-authorization prompt is at:

**`docs/audit/wave301-day0-prompt.md`** (208 lines)

It contains:
1. **§1 RESOLUTION Decisions** — 6 dual-present pair decisions + 4 special sub-decisions (each with CONFIRM / OVERRIDE checkbox)
2. **§2 Wave 268 Strict-Clean Break Authorization** — destructive-deletion authorization prompt with signature line
3. **§3 Venue Decision** — TNNLS primary / ICLR 2028 backup / ICLR 2027 dropped
4. **§4 Timeline Selection** — 8-10 day plan (70-80% confidence) vs 12-15 day plan (90%+ confidence)
5. **§6 Baseline 5-Gate Status** — current repo passes all 5 gates (verified again this wave)

**Total user time:** 2-3 hours.

---

## 5. Day 1/2/3 Ready-to-Execute Plans (GATED ON USER AUTHORIZATION)

### 5.1 Day 1 — RESOLUTION + Structure Lock

**Source-of-truth:** `docs/audit/wave301-day1-execution-plan.md` (538 lines)

**Trigger:** Day 0 user sign-off on 6 dual-present pair decisions + Wave 268 strict-clean break + venue lock + timeline selection.

**Execution summary:**
- 8 destructive deletion steps (one per dual-present pair + workflow-internal artifacts)
- 3 fresh-section insertions (§2 Related Work, §8 Reproducibility, §11 Conclusion) — total ~1400-1900 words
- Net delta: paper-flat-flattened.md 1404 → ~1069 lines
- 5-gate baseline re-established after each deletion step
- End state: 11-section canonical Wave 299 structure

**User review at end of Day 1:** None (only structure sanity check by agent).

### 5.2 Day 2 — Path A Theory + Paper A Full Draft

**Source-of-truth:** `docs/audit/wave301-day2-execution-plan.md` (426 lines)

**Trigger:** Day 1 RESOLUTION pass complete + 5-gate baseline re-established + Day 1 sanity check passed.

**Execution summary:**
- 6 Path A prose-proof lemmas (SchedulerProtocol closure, PolicyDriverProtocol, MergeOperator, RestartBlenderProtocol, CapabilityToken handshake, Typed four-port auto-wrap)
- 3 Path A proof sketches (SM byte-determinism, Ledger integrity, CapabilityToken handshake error diagnosability)
- 3 fresh sections (§2 Related Work 600-800w, §8 Reproducibility 600-800w, §11 Conclusion 200-300w)
- Abstract rewrite: emphasize "typed-contracts framework + 11-cell empirical validation" (NO JMAA)
- Contributions rewrite: 4 contributions

**User review at end of Day 2:** YES — boundary-clearness check on Contributions + Abstract + §6 Theoretical Lenses removal.

### 5.3 Day 3 — IEEEtran Typesetting + Submission Package + Paper B Skeleton

**Source-of-truth:** `docs/audit/wave301-day3-execution-plan.md` (731 lines)

**Trigger:** Day 2 prose complete + boundary-clearness user review PASSED + Day 0 §6/§10/figure-count decisions recorded + venue lock confirmed.

**Execution summary:**
- Phase A — Convert `paper-flat-flattened.md` → `paper.tex` with `\documentclass[journal]{IEEEtran}`; 6 lemmas + 3 sketches as LaTeX environments; 4 tables + 4 figures; bibliography.bib
- Phase B — Update audit-doc cross-references to post-RESOLUTION line numbers (~15 audit docs); maintain claims no-drift + mkdocs 0-warnings
- Phase C — TNNLS submission package refresh (`tnnls_submission/MANIFEST.md` SHA-256, cover_letter.md, highlights.md, tables.md, figures.md, data_availability.md, submission_checklist.md, source.zip, paper.pdf, highlight_blurb.pdf)
- Phase D — `docs/drafts/paper-b-jmaa/skeleton.md` + 10-experiment list + regime-sweep prerequisite + Paper B 4-6 primary contributions list + git branch `paper-b-skeleton` (no merge)

**User review at end of Day 3:** YES — Paper A final-version readiness check + Paper B skeleton sanity check.

### 5.4 Common gating across all 3 days

Every day is **gated** on:
1. Day 0 user sign-off message confirming 6 pair decisions + Wave 268 strict-clean break + venue lock + timeline
2. Prior day's 5-gate baseline re-established (D.4 30/30 + ruff 0 + claims no-drift + mkdocs strict 0 + vendored untouched)
3. Prior day's user review (if applicable) PASSED

**Without Day 0 sign-off, no edits to `paper-flat-flattened.md` are performed** — Wave 268 strict-clean holds.

---

## 6. Open Questions for User (blocking Day 1)

The Day 0 prompt `docs/audit/wave301-day0-prompt.md` §1-§4 contains the full authorization tables. Here is the **compact open-question list** the user must answer before Day 1 can begin:

### 6.1 Six dual-present pair decisions (§1)

| # | Pair | Recommended canonical | Awaiting |
|:--:|---|---|---|
| 1 | TITLE | Wave 297 additive ("FlowA: A Training-Free Re-Inference Framework...") | CONFIRM / OVERRIDE |
| 2 | ABSTRACT | Wave 297 additive 5-sentence abstract | CONFIRM / OVERRIDE |
| 3 | §1 INTRODUCTION | Additive 4-paragraph framework-reconstruction + 4-item contributions | CONFIRM / OVERRIDE |
| 4 | §2 ALGORITHM | Additive as canonical §3+§4+§5 per Wave 297 P2 (with cosine sign flip 1+cos) | CONFIRM / OVERRIDE |
| 5 | §3 EXPERIMENTS | Additive 6-column systematic-evidence status table | CONFIRM / OVERRIDE |
| 6 | §4 LIMITATIONS | Additive §9+§10 per Wave 297 P6 | CONFIRM / OVERRIDE |

### 6.2 Special sub-decisions (§1)

| Decision | Default | Awaiting |
|---|---|---|
| §6 Theoretical Lenses | DROP entirely (keeps Paper A boundary clean for Paper B) | DROP / Fold into §1 |
| §10 Future Work | DROP entirely | DROP / Fold into §8 |
| Figure count | 3-4 figures + 2-3 tables | Confirm / Other |
| Path A prose-proof depth | 3 sketches main + full proofs supplementary | 3 sketches + supp / Full main text |

### 6.3 Wave 268 strict-clean break authorization (§2)

**Required text:** explicit written authorization to perform 8 destructive deletion steps (483 legacy lines removed, 469 additive lines promoted, 95 fresh-section lines added = net −14 lines).

**Awaiting:** copy-paste of the authorization template in `wave301-day0-prompt.md` §2 with name/signature/date, OR equivalent explicit text.

### 6.4 Venue lock (§3)

| Decision | Recommendation | Awaiting |
|---|---|---|
| Primary target | TNNLS | CONFIRM / Other |
| Backup target | ICLR 2028 | CONFIRM / Other |
| ICLR 2027 | DROP entirely (abstract deadline already lapsed) | CONFIRM / Other |

### 6.5 Timeline selection (§4)

| Decision | Recommendation | Awaiting |
|---|---|---|
| Timeline | 8-10 day plan (70-80% confidence submission-ready) | 8-10 day / 12-15 day / Other |

### 6.6 Important corrections to user's framing

The user's deepseek teacher note stated:
- "6475 words / 10 sections"
- "3-day submission-ready"

**Actual repo state** (verified by Wave 300 P3 + this verification pass):
- `paper-flat-flattened.md`: **1404 lines / ~36027 words / 23 H2 sections** (19 legacy + 4 additive + Wave 300 P5 fold-in)
- This is **~5x larger** than the teacher's stated equivalent
- **3-day submission-ready is unrealistic**; Wave 300 P3 self-estimates 8 weeks for full RESOLUTION + fresh-writing + typesetting

**Recommended adjustment:** treat 3 days as "compressed first draft" (8-10 day plan) rather than "submission-ready". Full Path A in main text requires 12-15 day plan.

---

## 7. Files referenced (READ-ONLY this wave)

- **Source-of-truth for RESOLUTION plan:** `docs/audit/wave300-p3-resolution-plan.md` (320 lines)
- **Source-of-truth for canonical structure:** `docs/audit/wave299-paper-a-outline.md` §3 (11-section target)
- **Source-of-truth for §1 prose:** `docs/audit/wave297-p3-intro-rewritten.md` (apply verbatim)
- **Source-of-truth for §3 Framework:** `docs/audit/wave297-p4-framework-rewritten.md`
- **Source-of-truth for §7 Empirical Results:** `docs/audit/wave297-p5-empirical-rewritten.md`
- **Source-of-truth for §9+§10 Limitations+Future Work:** `docs/audit/wave297-p6-limitations-rewritten.md`
- **Source-of-truth for deep innovations:** `docs/audit/wave298-p7-paper-append.md` (Code #1-#5 + Method #1-#2)
- **Source-of-truth for inline fixes:** `docs/audit/wave294-p2-medium-fixed.md` (1 HIGH + 2 MEDIUM)
- **Source-of-truth for venue decision:** ICLR 2027 Author Guidelines; TNNLS ScholarOne portal

---

## 8. Commit + Push Status

**Commit:** All 8 new files + 1 ruff-fixed test file staged and committed as a single commit.

**Commit message:**
```
Wave 301: paper-A 3-day strategy verification — RESOLUTION plan + Day 1/2/3 ready-to-execute plans (NO PUSH, NO destructive edits without user auth)
```

**Push status:** **NOT PUSHED** per "暂不 push" directive.

**Repository state:** working tree clean after commit; remote `origin` (silverenternal/flowa-multistep-reinference) unchanged.

---

**End of Wave 301 Final Verification.** Awaiting user Day 0 sign-off on the 6 questions in §6 before any destructive edits to `paper-flat-flattened.md` proceed.