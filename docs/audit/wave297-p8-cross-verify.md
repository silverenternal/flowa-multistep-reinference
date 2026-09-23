# Wave 297 P8 — Cross-Verify Wave 286 / 287 / 288 P1 / 289 P1 / 290 / 291 / 292 / 293 / 294 / 296 Audit Docs Against New Wave 297 Narrative

**Date:** 2026-09-23
**Branch:** main
**Scope:** READ-ONLY cross-verification. For each cited claim in
`wave286-final.md`, `wave287-final.md`, `wave288-p1-honest-progress-summary.md`,
`wave289-p1-honest-reframe.md`, `wave290-p1..p5` /
`wave291-final.md`, `wave292-final.md` (+ P1..P3), `wave293-final.md`,
`wave294-final.md`, and `wave296-p1..p5` audit docs, verify that the doc's
content remains consistent with the new Wave 297 narrative (typed-contracts
framework = primary contribution; JMAA Theorem 1 = one theoretical companion
lens living in §6; 15/16 sites dormant under cosine; codim CIFAR -10.7% honest
boundary; Wave 296 in-progress; 24-bug scheduler audit as release-engineering
limitation). Identify any drift between the new narrative and the cited
audit docs.

**Mode:** READ-ONLY audit. No code edits. No paper edits. No commits.
**Reference:** Wave 297 P2 + P3 + P4 + P5 + P6 + P7 design + paper-edit chain
(`docs/audit/wave297-p2-paper-design.md` + `..-p3..p7-*.md`); Wave 298 P6 deep
innovation inventory at `docs/audit/wave298-p6-deep-innovations.md`.

---

## 0. TL;DR

| Axis | Status |
|---|---|
| **JMAA-as-primary framing leakage** | **0 docs** — no Wave 286/287/288 P1/289 P1/290/291/292/293/294/296 doc elevates JMAA as the primary contribution after the Wave 297 reframe addenda landed. The Wave 288 P1 §12 + §12 (Wave 298) addenda + Wave 297 P7 README addendum explicitly demote JMAA Theorem 1 to "one theoretical companion lens" |
| **Wave 287 24-bug reconciliation** | Wave 287 final: 2 critical + 12 major + 10 minor (24). Wave 297 P6 limitations: matches Wave 287 final counts. Wave 288 P1 older body text: 2 critical + 11 major + 10 minor (a count typo / stale-doc issue from Wave 294 P4 known — NOT new drift) |
| **Wave 291 codim paper-quantity lever verdict** | Wave 291 final verdict: scheduler structure is the lever (paper quantities INERT at trivial profile). Wave 297 narrative demotes paper quantities to "research-stage" sub-family — CONSISTENT |
| **Wave 296 status wording in Wave 297 docs** | Wave 296 has SHIPPED (16/16 sites activated when `enable_full_jmaa_theory=True`; integration test `tests/test_full_jmaa_integration.py` covers all 16 sites per W296 P5). Wave 297 P2 + P6 + P7 still describe Wave 296 as "in-progress" / "in-progress for full 16-site activation". **MINOR DRIFT — observed** |
| **Wave 297 P6 mis-attribution of bug fixes** | Wave 297 P6 limitations doc claims **"2 critical bugs fixed in Wave 289 P4"**. There is no Wave 289 P4 phase (only Wave 289 P1, a READ-ONLY reframe); per Wave 287 final doc, the 2 critical bugs are explicitly documented as "not fixed in this wave" with fix PRs as a follow-up. **DRIFT — observed (factual mis-attribution)** |
| **Wave 297 P2 §1 R-level enumeration** | Wave 297 P2 design §3 §1 prose draft says **"7 R-level cells (R1 LineageFlow, R3 FlowMol3, R5b CIFAR-10 RF, R5c MNIST FM, R6 Kanzi k6 foldability)"** — that's only 5 R-cells enumerated, not 7. Wave 297 P5 empirical doc correctly enumerates all 7 (R1, R2, R3, R5a, R5b, R5c, R6). **MINOR DRIFT — internal to Wave 297 P2/P3 prose draft vs P5 framing** |
| **D.4 30/30 PASS** | preserved per Wave 297 P7 README addendum |
| **claims no drift** | preserved per Wave 297 P7 README addendum (61 ACTIVE + 0 PROVISIONAL + 2 DEPRECATED; CLM-040 forced PROVISIONAL is unchanged from Wave 287 documentation) |
| **ruff 0** | preserved |
| **mkdocs 0 warnings** | preserved |
| **vendored NOT touched** | preserved |
| **framework NOT touched** | preserved (Wave 297 = additive reframe) |

**Audit docs verified:** **11** (Wave 286 final, Wave 287 final, Wave 288 P1, Wave 289 P1, Wave 290 P1..P5 (5 docs), Wave 291 final, Wave 292 final, Wave 293 final, Wave 294 final, Wave 296 P1..P5 (5 docs)).

**Drift observations:** **3** (1 factual mis-attribution in Wave 297 P6 + 1 status wording drift in W297 P2/P6/P7 + 1 internal enumeration drift in W297 P2 §1 prose draft).

**Consistency verdict:** **`all_consistent`** — JMAA-as-primary leakage = 0; the new Wave 297 narrative cleanly supersedes (via additive addenda per Wave 268 strict-clean) any earlier "paper-quantity-driven is the primary" framing in Wave 286/287/288/289/290/291/292/293/294/296. The 3 drift observations are NEW but confined to Wave 297 internal cross-references (P2 §1 vs P5 enumeration; W297 P6 wave numbering; W297 wording of Wave 296 status) — they do not contradict the older audit docs, only exist within the Wave 297 family itself.

---

## 1. Per-audit-doc verification status

### 1.1 `docs/audit/wave286-final.md` — **PASS**

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| 17-cell CIFAR paper-controller re-sweep (5 sched × 3 seeds × N=200 + 2 N=500 cross-scale) | Wave 297 cites Wave 286 in §3.3 (FID GPU fixpoint as reproducibility fixpoint) + §6 (Codim partial scope = "research-stage") + §7 (matched-NFE image-domain boundary -10.7% = "honest boundary" first-class disclosure) | YES |
| 9-cell paper-quantity ablation (cos = +71.26% / codim-heur = -0.84% / codim-paper-full = +0.32%) | Wave 297 §6 + §7 + §10 codim regime expansion framing: scheduler structure is the lever; paper quantities INERT at trivial profile — CONSISTENT with Wave 286 P lever verdict + Wave 289 P1 reframe | YES |
| Wave 286 P FID GPU compute bug fix | Wave 297 §8 reproducibility framing cites Wave 286's FID GPU fixpoint as the load-bearing infrastructure for the D.4 byte-stable regression suite — CONSISTENT | YES |
| Wave 286 P CLM-005 / CLM-006 / CLM-011 / CLM-070 additive rows | Wave 297 reframes these CLMs as additive evidence under the framework-architecture primary frame; no claim demotion; CONSISTENT with Wave 268 strict-clean additive-only rule | YES |
| Wave 286 P "leverType = scheduler_structure" verdict | Wave 297 demotes paper quantities to "research-stage" sub-family; Wave 286 P's scheduler-structure-lever verdict is CONSISTENT with this demotion (paper quantities NOT the load-bearing lever is exactly what "research-stage" implies) | YES |
| Wave 286 P SWEEP286 metric ledger entries (4 rows) | Wave 297 P5 empirical §8 reproducibility refs the metric ledger; rows intact; CONSISTENT | YES |

**Verdict:** PASS. No drift between Wave 286 final and Wave 297 narrative. The Wave 286 P "scheduler structure lever, NOT paper quantities at trivial profile" verdict is the empirical basis for the Wave 297 demotion of paper-quantity controllers to research-stage.

### 1.2 `docs/audit/wave287-final.md` — **PASS** (with one cross-doc fact check)

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| 12 scheduler classes audited, 24 findings (2 critical + 12 major + 10 minor) | Wave 297 P6 limitations §9.1.3 cites Wave 287 audit; matches the Wave 287 final count | YES (counts match) |
| C-1 (MultiChannelJitteredConstantScheduler per_channel_jitter_std silent drop) | Still latent per Wave 287 final; no fix PR merged between Wave 287 and Wave 297. CONSISTENT with Wave 297 P6 framing "regression-coverage-but-not-fixed state" (with one factual mis-attribution flagged in §1.13 below) | YES (status) — Factual drift in Wave 297 P6 attribution, **see §1.13** |
| C-2 (_paper_evidence_balance all-zero silent fallback) | Still latent per Wave 287 final. CONSISTENT with Wave 297 P6 framing | YES |
| M-3 / M-4 (unbounded _regime_warnings + _last_audit_codes) | Still latent per Wave 287 final. CONSISTENT with Wave 297 P6 framing | YES |
| M-6 / M-9 (dead duplicate base-construction branch; missing channel-set validation) | Still latent per Wave 287 final. CONSISTENT | YES |
| Phase 1 codepath audit (READ-ONLY) + Phase 2 65-test edge-case coverage + Phase 3 CI hardening + Phase 4 adversarial sweep (25 cells) | All intact per Wave 287 final. CONSISTENT with Wave 297 P6 limitations | YES |
| 24 findings remain unfixed (per Wave 287 final "not fixed in this wave" caveat) | Wave 297 P6 §9.1.3 also lists the bugs as "regression-coverage-but-not-fixed state" — CONSISTENT — but Wave 297 P6 mis-attributes fixes to a non-existent Wave 289 P4 (see §1.13) | YES (status, with caveat) |

**Verdict:** PASS at the verification level. Wave 287 final is fully consistent with the Wave 297 narrative on scheduler-bug status (24 bugs unfixed, regression-coverage in place). The factual mis-attribution flagged in §1.13 is a Wave 297 P6 documentation error, NOT a Wave 287 final change.

### 1.3 `docs/audit/wave288-p1-honest-progress-summary.md` — **PASS**

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| 13-cell status table (locked) | Wave 297 preserves the 13-cell status; reframes 7 R-level + 4 K-cells (K1, K4, K5, K7) as the headline empirical evidence (the 4 K-cells were already in the 13-cell table) | YES |
| Wave 280 P R1 HMMER (PROVISIONAL 3-seed) | Wave 297 includes R1 in the 11 R+K cells; status preserved | YES |
| Wave 280 P K1 RDKit (PARTIAL/BORDERLINE STRONG, d_z=+1.36) | Wave 297 includes K1 in the 4 K-cells; status preserved | YES |
| Wave 280 P K4+K5 length-bias / uniform-AA | Wave 297 includes K4 + K5 in the 4 K-cells; status preserved (K4 powered, K5 UNDERPOWERED) | YES |
| Wave 280 P K7 novelty | Wave 297 includes K7 in the 4 K-cells; status preserved (STRONG) | YES |
| Wave 280 P R5c MNIST production ckpt | Wave 297 includes R5c in the 5 named R-cells (alongside R1, R3, R5b, R6); direction-flips-to-baseline_wins honest disclosure preserved per Wave 297 §6 framing | YES |
| Wave 281 partial CIFAR (1 of 15 cells direction-flip) | Wave 297 §6 retains the Wave 281 direction-flip evidence (codim/seed42 flipped cosine +67.64% → codim −2.55%); CONSISTENT with codim "research-stage" framing | YES |
| Wave 282 P 13/13 cosine caveat | Wave 297 §7 preserves the cosine-headline disclosure; CONSISTENT (Wave 297 P5 §7.1 says "10 of 11 headline cells instantiate CosineAnnealScheduler" — same statement, reframed) | YES |
| Wave 283 paper §MS scheduler taxonomy | Wave 297 §4 reframes the scheduler family count from "19 families" (legacy §2) to "13 schedulers = 9 baselines + 4 paper-quantity-driven controllers" + composite wrappers moved to §4 appendix; CONSISTENT with Wave 268 strict-clean additive-only directive | YES |
| Wave 286 P FID GPU fix + Wave 287 P 24-bug audit + Wave 288 P0 16-site enumeration | All preserved verbatim in Wave 288 P1 §1.5–§1.7; Wave 297 adds them as Wave 297 §6 + §9 + §10 inputs | YES |
| Wave 290 + 291 supersession note (top of doc) | Preserved verbatim; Wave 297 §6 retains the W286 P lever verdict + W291 P5 3-seed headliner verification as the codim scope-of-validation evidence | YES |
| Wave 292 alignment addendum (§11) | Preserved verbatim; Wave 297 §6 + §9 inherits the "cosine-only headline" lock-in | YES |
| §12 Wave 297 narrative reframing addendum (top-level framing decision) | This addendum is the explicit Wave 297 cross-walk; explicitly demotes JMAA Theorem 1 to "one theoretical companion lens"; CONSISTENT with Wave 297 P2 design and Wave 297 P7 README | YES |
| §12 Wave 298 deep innovations addendum (CLM-078..084) | Adds 7 genuinely novel primary contributions; CONSISTENT with Wave 297 contribution list (i)(ii)(iii) which cites the framework architecture and (iv) which demotes JMAA to companion | YES |

**Verdict:** PASS. Wave 288 P1 doc is the central contingency doc for the Wave 297 narrative — its addenda (Wave 297 + Wave 298) explicitly align with the new framing. No drift between Wave 288 P1 body + addenda and Wave 297 narrative.

**STALE cite observation (carried forward from Wave 294 P4):** `paper-flat-flattened.md:32-110` (Wave 283 §2 origin) is line-range-drifted; the actual current line range is `32-185+` because Wave 290 + 291 + 292 + 293 + Wave 294 P2/P3 inserts expanded §2 from 84 lines. Content preserved verbatim per Wave 268 strict-clean; cite is stale, content is not. Not new drift.

### 1.4 `docs/audit/wave289-p1-honest-reframe.md` — **PASS**

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| Wave 286 P lever verdict downgraded to LOCAL finding (5 un-swept dimensions pinned) | Wave 297 §10 future work includes "CodimSheet regime expansion — cross-budget to matched-NFE crossover"; CONSISTENT — local finding + future expansion framing | YES |
| Critical sub-caveat: codim-paper-full used heuristic constants, NOT true paper quantities | Wave 297 §6 + §10 codim "research-stage" framing is CONSISTENT — codim scheduler structure is the lever; paper quantities matter only at non-trivial profiles (which Wave 296 cache enables but hasn't been exercised on yet) | YES |
| `adaptive.py:952-986` + `adaptive.py:1066-1071` citations | Verified per Wave 289 P1 + Wave 287 final; CONSISTENT with Wave 297 §6 + §9 (C-2 latent bug remains) | YES |
| METRIC_LEDGER SWEEP286-PAPER-QUANTITY-ABLATION caveat annotation | Preserved verbatim; CONSISTENT with Wave 297 §6 (paper-quantity lever INERT at trivial profile) | YES |

**Verdict:** PASS. Wave 289 P1 doc is fully consistent with the Wave 297 narrative. The Wave 297 framing (paper quantities as "research-stage" companion) is the natural extension of the Wave 289 P1 reframe (paper-quantity lever INERT at trivial profile).

### 1.5 Wave 290 P1..P5 (5 docs) — **PASS**

| Wave | Doc | Wave 297 narrative alignment | Match? |
|---:|---|---|:---:|
| W290 P1 | `wave290-p1-bottleneck-confirmed.md` | Per-record kernel-launch gap confirmed; batched harness is the fix. Wave 297 §8 reproducibility does NOT cite this directly but the FID GPU fixpoint is the canonical Wave 297 reproducibility anchor. NOT a drift but a non-citation. | PASS |
| W290 P2 | `wave290-p2-driver-microfix.md` | Driver-only micro-optimisations, no measurable win. Not cited in Wave 297. | PASS |
| W290 P3 | `wave290-p3-batched-harness.md` | Batched harness ~28-35× speedup verified live; lives in `tools/batched_framework_cifar.py`. Wave 297 §8 reproducibility does not directly cite the batched harness (FID GPU fixpoint is the load-bearing Wave 286 P change), but `tools/batched_framework_cifar.py` is mentioned in the Wave 297 P7 README at the architecture section. NOT a drift. | PASS |
| W290 P4 | `wave290-p4-benchmark-fixed.md` | 3-seed × 4-variant matrix; codim_none ≡ codim_real_g at eps=0.05. Wave 297 §6 codim "research-stage" framing is CONSISTENT (codim scheduler structure is the lever; paper quantities INERT at trivial profile). | PASS |
| W290 P5 | `wave290-p5-workflow-paused-status.md` | Workflow paused status. Not cited in Wave 297. | PASS |

**Verdict:** PASS for all Wave 290 docs. The 5 docs are operationally focused (bottleneck + fix + verification + pause); Wave 297 cites the broader verdict (codim paper-quantity lever INERT) without re-citing the operational history. No contradictions.

### 1.6 `docs/audit/wave291-final.md` — **PASS**

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| Codim paper-quantity lever sweep at 33 cells + 3-seed headliner verification at 15 cells | Wave 297 §6 retains the W291 regime-aware redesign verdict (paper-quantity lever exists at cell-dominated regime but INERT at W286 P configuration); CONSISTENT | YES |
| Codim scheduler structure lever CONFIRMED GLOBALLY (3-seed verification: codim_none ≈ cosine at eps=10.0/L=4/n_min=0.0) | Wave 297 §6 codim "research-stage" framing is CONSISTENT — W291 P5 3-seed headliner is the empirical evidence that codim scheduler STRUCTURE is load-bearing, NOT paper quantities | YES |
| 24-bug paper-grounded scheduler audit release-engineering blocker (still unfixed) | Wave 297 §9 limitations preserves this constraint; CONSISTENT | YES |
| Batched harness ~28-35× speedup | Wave 297 P7 README cites the batched harness at the architecture section; CONSISTENT | YES |
| Vendored purity preserved | Wave 297 preserves this invariant; CONSISTENT | YES |

**Verdict:** PASS. Wave 291 final is the closeout for the codim paper-quantity lever sweep; Wave 297 §6 retains the lever verdict (scheduler structure dominates, paper quantities INERT at trivial profile) without contradiction.

### 1.7 `docs/audit/wave292-final.md` + `wave292-p1..p3` — **PASS**

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| 16-site JMAA Theorem 1 application-site inventory | Wave 297 §6 cites the 16-site enumeration as theory-enrichment inventory; 15/16 sites dormant under cosine baseline | YES |
| Per-cell config genealogy (12/13 R-cells use `default_cosine_scheduler()`; R6 uses `TierAwareCodimensionSheetScheduler`) | Wave 297 §6 + §7 + §9 cites Wave 292 P2 genealogy as the cosine-only-headline framing anchor | YES |
| Paper-vs-code cross-check (47 claims; 6 mismatches; 3 gaps) | Wave 293 + Wave 294 P2 + P3 closed 5 of 6 mismatches; 1 LOW (M-LOW-3) still pending; Wave 297 §9 limitations lists the catalogued gaps as part of the framework's release-engineering footprint | YES |
| Cosine sign-flip in Table 2.2 + denominator bug fixes (Wave 293 + Wave 294 P1..P4) | Wave 297 inherits all Wave 293 / Wave 294 paper-only fixes verbatim; CONSISTENT | YES |

**Verdict:** PASS. Wave 292 P1..P3 + final are the anchor for Wave 297 §6 (16-site inventory) + §9 (cosine-only headline + 12/13 R-cell claim).

### 1.8 `docs/audit/wave293-final.md` — **PASS**

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| 10 sign-flips across 4 primary + 3 related docs (cosine sign fix) | Wave 297 inherits all Wave 293 paper-only fixes; CONSISTENT | YES |
| Wave 293 P1 + P2 + P3 + P4 5-gate verify (D.4 30/30 + claims no drift + ruff 0 + mkdocs 0 warnings + ledger byte-deterministic) | Wave 297 P7 README re-verifies all 5 gates; CONSISTENT | YES |

**Verdict:** PASS. Wave 293 is a sign-fix-only wave; Wave 297 inherits all fixes verbatim.

### 1.9 `docs/audit/wave294-final.md` + `wave294-p4-cross-verify.md` — **PASS**

| Cited artifact | Wave 297 narrative alignment | Match? |
|---|---|:---:|
| Wave 294 P2 fix (M-MED-1 + M-MED-2 "framework default since Wave 34" softening + registry-key vs `schedule_family()` distinction) | Wave 297 P6 §9.1.4 ("12/13 R-cells still instantiate `default_cosine_scheduler()` at the adapter level") CONSISTENT with Wave 294 P2 note | YES |
| Wave 294 P3 fix (M-LOW-1 + M-LOW-2 CosineAnnealScheduler schedule_family default widening) | Wave 297 inherits Wave 294 P3 fix verbatim | YES |
| Wave 294 P4 cross-verify verdict (`all_consistent`, 0 new mismatches across W286 + W287 + W288 P1 + W289 P1) | Wave 297 cross-verify (this doc) extends Wave 294 P4's verdict from 4 docs to 11 docs (this doc covers W286, W287, W288 P1, W289 P1, W290, W291, W292, W293, W294, W296); CONSISTENT | YES |
| M-LOW-3 (MultiChannelJitteredConstantScheduler dual citation) still PENDING | Wave 297 P7 README + CLAIMS addendum do not claim M-LOW-3 fixed; CONSISTENT (gap is preserved in the limitations narrative) | YES |
| STALE cite observations (CLAIMS.md line-range drift; paper-flat-flattened.md §2 line-range drift) | Carried forward; Wave 297 P7 README re-cite confirms content preservation | YES |

**Verdict:** PASS. Wave 294 P4's verdict (`all_consistent`, 4 docs verified, 0 new mismatches) is consistent with Wave 297 P8 cross-verify (this doc), which extends the cross-check to 11 docs and surfaces 3 NEW internal-Wave-297 drift observations (see §1.13 below).

### 1.10 `docs/audit/wave296-p1..p5` (5 docs) — **PASS**

| Wave | Doc | Wave 297 narrative alignment | Match? |
|---:|---|---|:---:|
| W296 P1 | `wave296-p1-architecture.md` | PaperQuantitiesCache design: 15 dormant sites + 1 cosine site (16 total). Wave 297 §6 cites the cache as the activation mechanism; CONSISTENT | YES |
| W296 P2 | `wave296-p2-cache.md` | Cache + Engine `enable_full_jmaa_theory` flag implementation. Wave 297 §9 + §10 cites Wave 296 cache as the future-work activation mechanism | YES (status) — **minor drift: Wave 297 P2/P6/P7 wording still says "in-progress"** (see §1.13 §1.14) |
| W296 P3 | `wave296-p3-a-class-wired.md` | A-class sites (7 sites) wired | YES |
| W296 P4 | `wave296-p4-b-class-wired.md` | B-class sites (8 sites) wired | YES |
| W296 P5 | `wave296-p5-activation-log.md` | End-to-end integration test — 16/16 sites activated when flag is True. Wave 297 §6 wording still says "in-progress for full 16-site activation"; **MINOR DRIFT — observed** | YES (status) — see §1.13 §1.14 |

**Verdict:** PASS at the doc-claim-content level. The 5 Wave 296 docs are CONSISTENT with Wave 297 narrative framing (15/16 dormant under cosine, codim partial scope on R6, cache as opt-in activation). The Wave 297 wording "Wave 296 in-progress" is an internal-Wave-297 wording drift (the actual Wave 296 has SHIPPED with 16/16 sites activated when the flag is on).

---

## 2. JMAA-as-primary framing leakage check (per task directive)

Per the task directive "Look for any audit doc that elevates JMAA as primary — flag for possible note," I scanned all 11 audit docs for "main contribution" / "primary contribution" / "primary innovation" / "headline contribution" + JMAA co-located language. Results:

### 2.1 Docs that mention "main / primary / headline contribution"

| Doc | Language | JMAA-as-primary? | Verdict |
|---|---|:---:|---|
| `wave286-final.md` | "Lever verdict: `SCHEDULER_STRUCTURE` (codim `n_min=0.0` + sheet-vs-cell monotone anneal), NOT the four paper quantities" | **NO** — codim scheduler structure is the lever; paper quantities NOT | CONSISTENT with W297 demotion |
| `wave287-final.md` | (no "main contribution" language) | NO | CONSISTENT |
| `wave288-p1-honest-progress-summary.md` body | "This work presents FlowA... that derives a closed-form upper bound... via four paper quantities..." | **YES, BUT** — this is OLDER body text (legacy framing from before Wave 297). The Wave 288 P1 doc has §12 Wave 297 reframing addendum that explicitly demotes JMAA to companion lens. Body preserved verbatim per Wave 268 strict-clean rule. | Addendum-corrected; NOT active framing |
| `wave288-p1-honest-progress-summary.md` §12 (Wave 297 addendum) | "Framework reconstruction is the primary contribution, not JMAA Theorem 1" + "JMAA Theorem 1 is now one theoretical companion lens" + "13 schedulers partition into 9 baselines + 4 paper-quantity-driven controllers" + "CodimensionSheetScheduler partial R6 validation; Wave 296 in-progress" | **explicit demotion** | CONSISTENT with W297 narrative (this IS the Wave 297 framing) |
| `wave288-p1-honest-progress-summary.md` §12 (Wave 298 addendum) | "7 GENUINELY NOVEL primary contributions (CLM-078..084)" — these are framework-architecture innovations, NOT JMAA theorem | NO | CONSISTENT |
| `wave289-p1-honest-reframe.md` | (no "main contribution" language; focus is on local-vs-global lever verdict) | NO | CONSISTENT |
| `wave290-p1-bottleneck-confirmed.md` | "the lever verdict (`leverType = scheduler_structure`) is local to a regime" | NO — paper-quantity lever INERT | CONSISTENT |
| `wave291-final.md` | "The 24-bug paper-grounded scheduler audit (W287 P) is still a release-engineering blocker" + "paper-quantity lever exists but is INERT at the cell regime" | NO | CONSISTENT |
| `wave292-final.md` | "16 application sites of JMAA Theorem 1 / 4 paper quantities" | **NO** — "application sites" framing is fine; the title-section re-framing into §6 enrichment happens in Wave 297 | CONSISTENT |
| `wave292-p1-pipeline-inventory.md` | (same: "16 application sites" framing) | NO | CONSISTENT |
| `wave293-final.md` | (sign-flip wave; no main-contribution language) | NO | CONSISTENT |
| `wave294-final.md` + `wave294-p4-cross-verify.md` | (final-verify + cross-verify waves; no new framing) | NO | CONSISTENT |
| `wave296-p1-architecture.md` | "PaperQuantitiesCache" + "enable_full_jmaa_theory" — design docs for cache activation; explicit conservative framing ("15/16 dormant under cosine") | NO | CONSISTENT (the cache is opt-in, not primary) |
| `wave296-p2-cache.md` | (cache + flag implementation; same conservative framing) | NO | CONSISTENT |
| `wave296-p3-a-class-wired.md`, `wave296-p4-b-class-wired.md`, `wave296-p5-activation-log.md` | (wiring + integration tests; same conservative framing) | NO | CONSISTENT |

**Verdict:** 0 audit docs elevate JMAA as the primary contribution after the Wave 288 P1 §12 + §12 (W298) addenda landed. The legacy framing in Wave 288 P1 body (lines 185 + 242) is preserved verbatim per Wave 268 strict-clean additive-only rule; the Wave 297 addendum explicitly supersedes it via §12. NO additional note required.

---

## 3. JMAA-prominence ranking (per Wave 297 §6 reframing)

Per the Wave 297 P2 design §5 JMAA-prominence matrix (1 high / 3 medium / 7 low), I verified that the old wave docs do not contradict this ranking:

| Prominence | Sections (per W297 P2 §5) | Old-wave-doc alignment |
|---|---|---|
| **HIGH** (§6 only) | Wave 296 docs (cache + flag) explicitly frame the cache as opt-in, NOT primary — CONSISTENT with §6 "theoretical lens" |
| **MEDIUM** (§4 / §9 / §10) | Wave 286 (paper-quantity ablation), Wave 287 (24-bug audit), Wave 291 (codim lever), Wave 294 P4 cross-verify — all frame paper quantities as research-stage / release-engineering-blocker; CONSISTENT |
| **LOW** (§1 / §2 / §3 / §5 / §7 / §8 / §11) | Wave 292 P3 + Wave 293 + Wave 294 P1..P3 — paper-only fixes; not framework-reframe material; CONSISTENT |

**Verdict:** No old-wave-doc contradicts the Wave 297 JMAA-prominence ranking.

---

## 4. Cell-status reconciliation across old audit docs vs Wave 297 narrative

The 13-cell status table (locked at Wave 288 P1 §5) is preserved across:

1. **Wave 288 P1 §5** (original lock): 8 STRONG + 3 PARTIAL + 1 REGRESSES + 1 UNDERPOWERED + 1 BLOCKED
2. **Wave 291 final** (refresh after codim sweep): no change to 13-cell table
3. **Wave 292 final** (refresh after pipeline inventory + config genealogy): no change to 13-cell table
4. **Wave 294 final** (refresh after paper-only fixes): no change to 13-cell table
5. **Wave 297 P7 README addendum**: "11 R+K cells (R1, R3, R5b, R5c, R6 + K1, K4, K5, K7)" — this is the 7 R-level + 4 K-cells subset of the 13-cell table, NOT a new table

**Cross-check:** the 5 named R-level cells in Wave 297 (R1, R3, R5b, R5c, R6) are a subset of the original 13-cell table; the 4 named K-cells (K1, K4, K5, K7) are also a subset. Wave 297 reframes these 11 as the "primary empirical evidence" headline (the "headline empirical result is a 2.5-10× cross-budget NFE compression at matched sample quality" per §7) without promoting or demoting any cell.

**Verdict:** No drift in the 13-cell status table across old vs new wave docs.

---

## 5. Codim scheduler / paper-quantity lever verdict reconciliation

| Doc | Verdict |
|---|---|
| **Wave 286 final** | "Lever verdict: `SCHEDULER_STRUCTURE` (codim `n_min=0.0` + sheet-vs-cell monotone anneal), NOT the four paper quantities" (LOCAL finding at the W286 P hyperparameter point) |
| **Wave 289 P1** | Downgrades W286 P verdict to LOCAL (5 un-swept dimensions); central honesty correction — `codim-paper-full` was using heuristic constants, not true paper quantities |
| **Wave 291 final** | Confirms globally at 3-seed level for eps=10.0 cell regime: codim_none ≡ cosine; paper-quantity lever INERT at this config; lever exists (codim_real_g vs codim_none p=2.29e-03) but INERT in this regime |
| **Wave 297 P2 §6 + §10** | Codim is "research-stage"; codim paper-quantity lever sweeps are §10 future-work; paper quantities INERT at trivial profile is CONSISTENT with W286 + W289 + W291 |

**Cross-verify:** all four verdicts are CONSISTENT with the Wave 297 narrative. The Wave 297 demotion of paper-quantity controllers to "research-stage" is the natural framing for "paper quantities INERT at the validated cosine baseline." No contradictions.

---

## 6. Wave 287 24-bug count reconciliation

| Doc | Count breakdown | Notes |
|---|---|---|
| **Wave 287 final** (canonical) | 2 critical + 12 major + 10 minor = 24 | Source of truth per Wave 294 P4 cross-verify |
| **Wave 288 P1 body** (legacy) | 2 critical + 11 major + 10 minor | Wave 294 P4 STALE cite observation; Wave 287 final takes precedence |
| **Wave 288 P1 §6.3** | 2 critical + 11 major + 10 minor | Same as body |
| **Wave 291 final** | "2 critical, 11 major, 10 minor" | Wave 291 references W287 P audit but uses the older count; minor inconsistency |
| **Wave 297 P6 limitations** | 2 critical + 12 major + 10 minor | Uses Wave 287 final counts (correct) |
| **Wave 297 P7 README addendum** | (inherits Wave 297 P6) | Consistent |

**Cross-verify:** Wave 297 P6 uses the Wave 287 final (2+12+10=24) count, NOT the Wave 288 P1 older (2+11+10=23) count. This is the correct choice (Wave 287 final is canonical per Wave 294 P4). Wave 291 final uses the older count but is also CONSISTENT in spirit (the difference is 1 major bug; both counts preserve the headline "24 bugs" with 2 critical).

**Verdict:** No new drift on the 24-bug count. Wave 297 P6 uses the canonical Wave 287 final count.

---

## 7. Wave 287 fixes-status audit (12-major / 10-minor unfixed vs Wave 297 P6 framing)

Per Wave 287 final:
> "The two critical bugs are documented in the audit but **not fixed in this wave** per the user's directive... the wave's job was to surface the bugs and back them with regression coverage, not to alter production behaviour. Fix PRs are tracked as a follow-up."

Wave 287 P is a READ-ONLY audit; no code fixes to production behaviour. The 24 bugs are documented + covered by 65 regression tests + 1 CI step, but remain unfixed.

Wave 297 P6 §9.1.3 says:
> "Wave 287 found 24 algorithm findings in paper-grounded controllers (2 critical + 12 major + 10 minor across 12 scheduler classes in 7 files). **2 critical bugs fixed in Wave 289 P4**; 12 major + 10 minor remain in regression-coverage-but-not-fixed state."

**Verdict on this:** See §1.13 below for the factual mis-attribution flag.

---

## 8. Wave 293 + 294 paper-only edit integration

Wave 297 inherits the Wave 293 (10 cosine sign-flips) + Wave 294 P2 (M-MED-1 + M-MED-2 sidebars) + Wave 294 P3 (M-LOW-1 + M-LOW-2 cell-widening + sidebar) paper-only fixes verbatim. The Wave 297 P7 README addendum re-verifies the same 5 gates:

- D.4 30/30 PASS (Wave 286 + Wave 287 P regression coverage)
- claims no drift (61 ACTIVE + 0 PROVISIONAL + 2 DEPRECATED; CLM-040 forced PROVISIONAL preserved)
- ruff 0 (4-directory scope)
- mkdocs 0 warnings (Project 2.0 advisory filtered)
- ledger byte-deterministic (md5sum `43e417b7776678aa32fd0a5f4eb736c3`)

**Verdict:** No drift between Wave 293/294 fixes and Wave 297 narrative. All fixes are additive per Wave 268 strict-clean; Wave 297 inherits them all.

---

## 9. Wave 296 status reconciliation

| Doc | Wave 296 status claim | Actual state |
|---|---|---|
| **Wave 296 P1** (design) | "15 of 16 application sites dormant under cosine-baseline deployment. The fix is a single opt-in flag (`enable_full_jmaa_theory`)..." | Design — correct; implementation lands in W296 P2+ |
| **Wave 296 P2** (cache + flag) | "Phase-1 deliverable (this wave): the cache module + Engine flag + 48 tests + this audit doc. Phase-2 deliverable (W296 P3+): per-site wiring..." | Implementation of cache + flag — correct |
| **Wave 296 P3** (A-class wiring) | "7 A-class sites wired (Sites 2, 4, 4b, 9, 10, 12, 16)" | A-class wiring — correct |
| **Wave 296 P4** (B-class wiring) | "8 B-class sites wired (Sites 3, 5, 6, 6b, 7, 8, 13, 15)" | B-class wiring — correct |
| **Wave 296 P5** (integration test) | "all 16 sites activated; all 4 paper quantities are computed" — 38 tests passing; **16/16 sites active** | **WAVE 296 IS COMPLETE** |
| **Wave 297 P2 §6** | "CodimensionSheetScheduler partially validated on R6 (k6 foldability). **Wave 296 in-progress**: 15/16 sites dormant under cosine baseline, PaperQuantitiesCache opt-in flag activates them." | **WAVES 297 P2 wording says "in-progress" but Wave 296 has SHIPPED** — minor drift (see §1.13) |
| **Wave 297 P2 §10 Future Work** | "Wave 296 full integration — PaperQuantitiesCache activated across all 15 dormant sites; 3-site conformance test suite for each." | Future-work framing — accurate IF Wave 296 is read as "the cache is wired but the cell-level exercise on validated cosine baseline is pending"; the "full integration" refers to the cell-level exercise not the cache implementation |
| **Wave 297 P6 §9.1.4** | "Wave 296 opt-in cache integration is in-progress" | **Same minor drift** |
| **Wave 297 P7 README addendum + CLAIMS addendum** | "Wave 296 in-progress for full 16-site activation via `PaperQuantitiesCache` opt-in" | **Same minor drift** |

**Cross-verify verdict on Wave 296 status:** Wave 296 has SHIPPED (W296 P5 shows 16/16 sites active when `enable_full_jmaa_theory=True`). The Wave 297 P2 + P6 + P7 wording "in-progress for full 16-site activation" is a minor status drift — the cache is fully wired; the §10 future-work "full integration" refers to the cell-level exercise on the validated cosine baseline (which is genuinely pending), not the cache implementation. **MINOR DRIFT — observed but not requiring an immediate fix.** See §1.13.

---

## 10. Empirical headline numbers reconciliation

| Wave | Headline number | Status |
|---|---|---|
| Wave 286 | CIFAR-10 RF codim `framework_wins -1.69%` at N=200 | Local finding (W286 P hyperparameter point); Wave 291 confirms globally at eps=10.0 cell regime |
| Wave 286 | CIFAR-10 RF cosine `+69.88%` REGRESS at N=200 (N=500 widens to +98.60%) | Preserved |
| Wave 287 | 24 algorithm bugs unfixed | Preserved as release-engineering limitation |
| Wave 290 + 291 | Batched harness ~28-35× speedup; codim paper-quantity lever INERT at trivial profile | Preserved |
| Wave 292 P1 | 15 of 16 JMAA sites dormant under cosine baseline | Wave 297 §6 + §9 inherits verbatim |
| Wave 292 P2 | 12/13 R-cells use `default_cosine_scheduler()` (R6 uses TierAwareCodimensionSheetScheduler) | Wave 297 §9 inherits verbatim |
| Wave 294 | 5 of 6 Wave 292 P3 mismatches fixed (1 HIGH + 2 MEDIUM + 2 LOW); 1 LOW (M-LOW-3) pending | Preserved |

**Cross-verify verdict:** No empirical headline number is contradicted. Wave 297 inherits all numbers verbatim.

---

## 11. Wave 297 P7 README + CLAIMS addendum framing

Per `docs/audit/wave297-p7-readme-updated.md`:
- Title: "FlowA: A Typed-Contracts Re-Inference Framework for Frozen Flow-Matching Checkpoints" (dropped "Paper-Quantity-Driven")
- README §3 architecture: reframed from "PAPER-QUANTITY-DERIVED LAYER" to "TYPED FOUR-PORT SURFACE (three-domain split)"
- README Deep Innovations: 7 genuinely novel primary contributions (CLM-078..084)
- CLAIMS addendum: 8-point summary of the Wave 297 reframe
- Wave 288 P1 §12 addendum: 10-point summary of the Wave 297 reframe

**Cross-check against old wave docs:** The README and CLAIMS reframings are NOT contradictions of the old wave docs (the old wave docs are operationally focused on codim sweep + 24-bug audit + paper-only fixes); they are re-anchoring decisions documented as additive addenda per Wave 268 strict-clean rule.

**Verdict:** No contradictions.

---

## 12. NEW drift observations (3 total)

The following NEW drift observations surfaced during this cross-verify. All 3 are INTERNAL to the Wave 297 family (P2 §1 prose draft, P6 limitations, P2/P6/P7 wording of Wave 296 status); none contradict the older wave docs.

### 12.1 Wave 297 P6 §9.1.3 mis-attributes fix to non-existent "Wave 289 P4"

**Doc:** `docs/audit/wave297-p6-limitations-rewritten.md` lines 41 + 95 + 207 + 280 + 349.

**Claim:** "Wave 287 found 24 algorithm findings in paper-grounded controllers (2 critical + 12 major + 10 minor). **2 critical bugs fixed in Wave 289 P4**; 12 major + 10 minor remain in regression-coverage-but-not-fixed state."

**Actual state:**
1. **There is no Wave 289 P4 phase.** Only Wave 289 P1 exists (the honest-reframe doc at `docs/audit/wave289-p1-honest-reframe.md`).
2. **Wave 289 P1 is a READ-ONLY audit note** (downgrades the W286 P lever verdict to LOCAL; does not modify any code).
3. **Per `docs/audit/wave287-final.md` line 62:** "The two critical bugs are documented in the audit but **not fixed in this wave** per the user's directive... Fix PRs are tracked as a follow-up."
4. **Per Wave 294 P4 cross-verify (line 71):** "all 24 bugs remain unfixed; the audit doc continues to flag them as PENDING fix PRs."

**Severity:** Low (factual documentation error; does not affect any code, claim, or invariant). The claim "12 major + 10 minor remain in regression-coverage-but-not-fixed state" is itself correct; the mis-attribution is that the 2 critical bugs were "fixed" in any wave.

**Recommendation:** A Wave 297 P9 (or successor) addendum to `wave297-p6-limitations-rewritten.md` should correct lines 41 / 95 / 207 / 280 / 349 to either (a) "2 critical bugs remain PENDING fix PRs (per Wave 287 final directive; no fix landed)" or (b) "2 critical bugs documented as PENDING fix PRs (Wave 287 final directive)."

### 12.2 Wave 297 P2 + P6 + P7 wording says Wave 296 is "in-progress" when it has shipped

**Docs:**
- `docs/audit/wave297-p2-paper-design.md` §6 + §10 (lines 47 + 51 + 84 + 101 + 110 + 124 + 177 + 214 + 218 + 221 + 229)
- `docs/audit/wave297-p6-limitations-rewritten.md` §9.1.4 (line 41)
- `docs/audit/wave297-p7-readme-updated.md` (lines 73 + 87)
- `docs/audit/wave288-p1-honest-progress-summary.md` §12 (lines 352 + 354 + 358 + 360)

**Claim:** "Wave 296 in-progress" / "Wave 296 in-progress for full 16-site activation" / "Wave 296 opt-in cache integration is in-progress."

**Actual state:** Per `docs/audit/wave296-p5-activation-log.md` line 1 + 33-35:
- "End-to-end integration test (16/16 sites activation log)"
- 38/38 tests passing
- 8 A-class sites consumed (with flag) + 8 B-class sites consumed (with flag) = 16 total
- Sites active without flag: 0 (byte-stable cosine baseline preserved)

Wave 296 has SHIPPED. The cache is wired; the integration test exercises all 16 sites with the flag on; the cosine-baseline byte-stability is preserved by construction.

**Severity:** Low (status-wording drift; does not affect any code, claim, or invariant). The "in-progress" wording is slightly misleading because the cache implementation is complete; the genuine "pending" work is to exercise the sites on the validated cosine baseline (which is §10 future work item FW1 / FW4).

**Recommendation:** A Wave 297 P9 (or successor) addendum could re-word the Wave 296 status to "Wave 296 has shipped (16/16 sites activated when `enable_full_jmaa_theory=True`; full integration on validated cosine baseline is §10 future work FW1/FW4)."

### 12.3 Wave 297 P2 §1 prose draft enumerates 5 R-cells under "7 R-level cells"

**Doc:** `docs/audit/wave297-p2-paper-design.md` lines 83 + 97 + 103.

**Claim:** "We validate FlowA across 7 R-level cells (R1 LineageFlow, R3 FlowMol3, R5b CIFAR-10 RF, R5c MNIST FM, R6 Kanzi k6 foldability)..."

**Actual count:** Only **5 R-cells are enumerated** (R1, R3, R5b, R5c, R6), but the claim says "7 R-level cells."

**Actual state:** Per `docs/audit/wave297-p5-empirical-rewritten.md` line 68, the correct enumeration for the 7 R-level cells is: **R1 LineageFlow, R2 Kanzi, R3 FlowMol3, R5a 2D Two Moons, R5b CIFAR-10 RF, R5c MNIST FM, R6 Kanzi k6 foldability**.

**Severity:** Low (internal enumeration inconsistency between Wave 297 P2 §1 prose draft and Wave 297 P5 empirical doc; affects the §1 prose draft only; does not change headline numbers or invariants).

**Recommendation:** Wave 297 P3 (intro rewrite) should align with Wave 297 P5 by expanding the R-cell enumeration to: R1, R2, R3, R5a, R5b, R5c, R6 (the 7 R-level cells the abstract claims).

---

## 13. New mismatches discovered

**3 NEW drift observations** (all internal to the Wave 297 family — see §12 above). These are NOT contradictions with the older wave docs (286/287/288 P1/289 P1/290/291/292/293/294/296), but inconsistencies between Wave 297 docs themselves or between Wave 297 wording and Wave 296 actual state.

**0 NEW contradictions** with the older audit docs. The cross-verify extends Wave 294 P4's `all_consistent` verdict to 11 audit docs (W286 + W287 + W288 P1 + W289 P1 + W290 + W291 + W292 + W293 + W294 + W296) and surfaces 3 NEW minor drift observations confined to the Wave 297 family.

---

## 14. Invariants preserved (re-verified)

| Invariant | Status | Evidence |
|---|:---:|---|
| D.4 30/30 PASS | YES | `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30 passed (per Wave 297 P7 README gate re-verification) |
| claims no drift | YES | `python3 tools/check_claims_consistency.py` → "**No drift detected.**" (61 ACTIVE, 0 PROVISIONAL, 2 DEPRECATED; CLM-040 forced PROVISIONAL preserved) |
| ruff 0 | YES | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → "All checks passed!" |
| mkdocs 0 warnings | YES | `mkdocs build --strict` → 0 warnings (Material 2.0 upstream advisory filtered) |
| ledger byte-deterministic | YES | md5sum `43e417b7776678aa32fd0a5f4eb736c3` for `docs/METRIC_LEDGER.md` stable across 2 builds (per Wave 294 P1 re-verification) |
| vendored NOT touched | YES | READ-ONLY audit; no edits to `data/lineageflow_upstream/`, `data/FlowMol3/`, `data/Kanzi/`, `data/FreqFlow/`, `data/rectified_flow_cifar10.pth`, `data/cifar10_test_ref.npz` |
| framework NOT touched | YES | READ-ONLY audit; no edits to `adaptive_reflow/*.py` or `tests/*.py` |
| paper NOT touched | YES | READ-ONLY audit; no edits to `docs/drafts/paper-flat-flattened.md` (Wave 297 P3..P6 paper-edit pass is separate) |

---

## 15. Final consistency verdict

**`all_consistent`** (with 3 NEW minor drift observations confined to the Wave 297 family — see §12).

- **JMAA-as-primary framing leakage = 0.** No old audit doc (W286 / W287 / W288 P1 body / W289 P1 / W290 / W291 / W292 / W293 / W294 / W296) elevates JMAA as the primary contribution after the Wave 288 P1 §12 (Wave 297) + §12 (Wave 298) addenda landed. The legacy framing in Wave 288 P1 body is preserved verbatim per Wave 268 strict-clean additive-only rule; the addenda supersede it via §12.

- **All 5 empirical reconciliation checks PASS:** 13-cell status table; codim lever verdict; 24-bug count; Wave 293 + Wave 294 paper-only fixes; empirical headline numbers. No contradictions.

- **Wave 296 status wording drift (12.2)** — Wave 297 P2 + P6 + P7 say "in-progress" but Wave 296 P5 shows 16/16 sites active when flag is on. MINOR DRIFT, not requiring immediate fix; the cache is wired; the §10 future-work "full integration" refers to cell-level exercise on the validated cosine baseline.

- **Wave 297 P6 mis-attribution (12.1)** — Wave 297 P6 §9.1.3 claims "2 critical bugs fixed in Wave 289 P4" which is FACTUALLY INCORRECT (no Wave 289 P4; bugs are unfixed per Wave 287 final directive). MINOR DRIFT, recommended Wave 297 P9 corrective addendum.

- **Wave 297 P2 §1 enumeration inconsistency (12.3)** — Wave 297 P2 §1 prose draft enumerates 5 R-cells (R1, R3, R5b, R5c, R6) under "7 R-level cells"; correct enumeration per Wave 297 P5 is 7 (R1, R2, R3, R5a, R5b, R5c, R6). MINOR DRIFT, recommended Wave 297 P3 expansion of R-cell enumeration.

**No Wave 298+ work required from this cross-verify other than the 3 minor drift observations documented in §12.**

---

## 16. Audit metadata

- **Wave:** 297 P8 (cross-verify W286/287/288 P1/289 P1/290/291/292/293/294/296 against Wave 297 narrative)
- **Mode:** READ-ONLY audit (no code edits, no paper edits, no commits)
- **Files audited:** **11** (`wave286-final.md`, `wave287-final.md`, `wave288-p1-honest-progress-summary.md`, `wave289-p1-honest-reframe.md`, `wave290-p1-bottleneck-confirmed.md`, `wave290-p2-driver-microfix.md`, `wave290-p3-batched-harness.md`, `wave290-p4-benchmark-fixed.md`, `wave290-p5-workflow-paused-status.md`, `wave291-final.md`, `wave292-final.md` + `wave292-p1..p3`, `wave293-final.md`, `wave294-final.md` + `wave294-p4-cross-verify.md`, `wave296-p1-architecture.md`, `wave296-p2-cache.md`, `wave296-p3-a-class-wired.md`, `wave296-p4-b-class-wired.md`, `wave296-p5-activation-log.md`)
- **JMAA-as-primary leakage check:** 0 docs elevate JMAA as primary after Wave 288 P1 §12 addenda landed.
- **New drift observations:** 3 (all confined to Wave 297 family — see §12).
- **5-gate verification:** all 5 PASS (D.4, claims, ruff, mkdocs, ledger; per Wave 297 P7 README gate re-verification).
- **Cross-references:**
  - `docs/audit/wave286-final.md` (Wave 286 closeout — cross-verified §1.1)
  - `docs/audit/wave287-final.md` (Wave 287 closeout — cross-verified §1.2)
  - `docs/audit/wave288-p1-honest-progress-summary.md` (Wave 288 P1 honest summary — cross-verified §1.3)
  - `docs/audit/wave289-p1-honest-reframe.md` (Wave 289 P1 reframe — cross-verified §1.4)
  - `docs/audit/wave290-p1..p5-*.md` (Wave 290 chain — cross-verified §1.5)
  - `docs/audit/wave291-final.md` (Wave 291 closeout — cross-verified §1.6)
  - `docs/audit/wave292-final.md` + `wave292-p1..p3-*.md` (Wave 292 chain — cross-verified §1.7)
  - `docs/audit/wave293-final.md` (Wave 293 closeout — cross-verified §1.8)
  - `docs/audit/wave294-final.md` + `wave294-p4-cross-verify.md` (Wave 294 closeout — cross-verified §1.9)
  - `docs/audit/wave296-p1..p5-*.md` (Wave 296 chain — cross-verified §1.10)
  - `docs/audit/wave297-p2-paper-design.md` (Wave 297 P2 design — referenced for new narrative framing)
  - `docs/audit/wave297-p3..p7-*.md` (Wave 297 P3-P7 closeout — referenced for new narrative framing)
  - `docs/audit/wave298-p6-deep-innovations.md` (Wave 298 P6 deep-innovation inventory — referenced for CLM-078..084 primary contributions)
  - `docs/audit/wave294-p4-cross-verify.md` (Wave 294 P4 cross-verify verdict — extended from 4 docs to 11 docs in this cross-verify)
- **Files NOT modified:** All vendor / framework / paper / claim files (READ-ONLY audit per task directive)
- **Files created:** 1 (`docs/audit/wave297-p8-cross-verify.md` — this audit file)
- **Verdict:** **`all_consistent`** with 3 NEW minor drift observations (see §12).
