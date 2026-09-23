# Wave 294 P1 — re-inventory: paper/code mismatches after Wave 293

**Date:** 2026-09-23
**Scope:** re-inventory the 6 Wave 292 P3 mismatches after the Wave 293 paper-fix pass. Verify the 7 Wave 293 sign-flip edits landed; identify remaining work for Wave 294 P2+.
**Mode:** READ-ONLY audit. No code edits. No paper edits. No commits.
**Reference:** `docs/audit/wave292-p3-crosscheck.md` (6 mismatches) + `docs/audit/wave293-final.md` (P5 final verify) + `docs/audit/wave293-p3-fix-applied.md` (primary 7-flip patch) + `docs/audit/wave293-p4-related-docs.md` (3 related-docs flips).

---

## 1. Summary

| Bucket | Count |
|---|---:|
| Wave 293 sign fixes landed | **7 / 7** |
| Wave 292 P3 mismatches FIXED | **1 / 6** (the HIGH-severity cosine sign) |
| Wave 292 P3 mismatches REMAINING | **5 / 6** (1 MEDIUM + 1 MEDIUM + 3 LOW) |
| Outstanding items from Wave 293 P3/P4 §6 | 2 (denominator-bug fixes + sequential-protocol §2 rewrite) |
| New findings this audit | 1 (M-LOW-3 row already present in Wave 292 P3 but unresolved — see §4 below) |

**Bottom line.** The HIGH-severity cosine sign mismatch (Wave 292 P3 M-HIGH-1, Wave 293 P3 fix #1) is closed across 4 load-bearing docs + 3 related docs (10 flips total per Wave 293 P4). The 5 remaining mismatches from Wave 292 P3 are **all PENDING** for Wave 294 P2/P3: they are MEDIUM-severity framing fixes (factory-default claim softening, registry-key vs schedule_family() distinction) and LOW-severity presentation fixes (DeprecationWarning note, schedule_family() default, MultiChannelJitteredConstantScheduler duplicate citation). None of the 5 are blocking, but all 5 are recommended for closure before push.

---

## 2. Wave 293 sign-fix verification (7/7 landed)

| # | File | Line | Pre-edit formula | Post-edit formula | Status |
|---:|---|---:|---|---|:---:|
| 1 | `docs/drafts/paper-flat-flattened.md` | 62 | `(1 − cos(π r / (L − 1)))` | `(1 + cos(π r / (L − 1)))` | **FIXED** |
| 2 | `docs/CLAIMS.md` | 110 | `(1 - cos(pi * r / (L - 1)))` | `(1 + cos(pi * r / (L - 1)))` | **FIXED** |
| 3 | `docs/schedule-theory.md` | 15 | `(1 − cos(π · r / (L − 1)))` | `(1 + cos(π · r / (L − 1)))` | **FIXED** |
| 4 | `docs/schedule-theory.md` | 178 | `(1 - cos(pi * r / (L - 1)))` | `(1 + cos(pi * r / (L - 1)))` | **FIXED** |
| 5 | `docs/schedule-theory.md` | 207 | `(1 - cos(pi * r / (L - 1)))` | `(1 + cos(pi * r / (L - 1)))` | **FIXED** |
| 6 | `docs/schedule-theory.md` | 208 | `(1 - cos(pi * r / (L - 1)))` | `(1 + cos(pi * r / (L - 1)))` | **FIXED** |
| 7 | `docs/audit/wave292-final.md` | 47 | `(1 − cos(π r / L))` | `(1 + cos(π r / (L − 1)))` | **FIXED** (+ denominator bug fix `r / L` → `r / (L − 1)`) |

### 2.1 Verification commands run

```
$ grep -n "(1 + cos\|(1 - cos" docs/drafts/paper-flat-flattened.md
... 7 matches, all `(1 + cos)` (post-fix state)

$ grep -n "(1 + cos\|(1 - cos" docs/CLAIMS.md
... 1 match at line 110: `(1 + cos(pi * r / (L - 1)))` (post-fix state)

$ grep -n "(1 + cos\|(1 - cos" docs/schedule-theory.md
... 4 matches at lines 15, 178, 207, 208, all `(1 + cos)` (post-fix state)

$ grep -n "(1 + cos\|(1 - cos" docs/audit/wave292-final.md
... 2 matches at lines 47, both `(1 + cos)` (post-fix state)
```

### 2.2 Remaining `(1 - cos)` occurrences in paper-facing files

| File | Line | Occurrence | Action |
|---|---:|---|---|
| `docs/drafts/paper-flat-flattened.md` | 80 | `α = 0.5 · (1 − cos(π · progress))` (HandoffSequentialScheduler blend weight) | **KEEP** — different mathematical object (slot-boundary blend weight, not CosineAnnealScheduler closed form); verified against `sequential_handoff.py:46`. Per Wave 293 P1 §6 + P3 §5 item 8, the `(1 - cos)` form is CORRECT for this purpose. |
| `docs/drafts/paper-flat-flattened.md` | 200 | `n_cap(r) = n_min + 0.5·(n_max−n_min)·(1 − cos(π r / (L − 1)))` (inside the Wave 292 P3 crosscheck audit table) | **KEEP** — this is the documented PRE-fix state inside the audit table; it correctly quotes the (now-historical) wrong claim and identifies the sign as MISMATCH-HIGH-1 in the adjacent verdict column. Per Wave 268 strict-clean rule, audit tables that document the prior state are preserved. |
| `docs/sequential-protocol.md` | 50, 85-87, 95-96 | Worked example uses `(1 - cos)` formula with internally-consistent table values | **FLAGGED for Wave 294 P2** — per Wave 293 P4 §3 + Wave 293 final §6.2, this is internally consistent but inconsistent with code direction; requires non-additive edit (rewriting table values + prose); deferred to Wave 294 P2 follow-up. |

### 2.3 No remaining `(1 - cos)` in the 4 primary Wave 293 fix targets

All 7 primary sign-flip edits (P3 §2.2 + P4 §1.1) are in the post-fix `(1 + cos)` state. **No remaining `(1 - cos)` for `CosineAnnealScheduler` closed form** in `paper-flat-flattened.md`, `CLAIMS.md`, `schedule-theory.md`, or `wave292-final.md`.

---

## 3. Wave 292 P3 mismatch status (1/6 FIXED, 5/6 PENDING)

### 3.1 M-HIGH-1: CosineAnnealScheduler closed-form sign (Table 2.2) — **FIXED**

**Source:** Wave 292 P3 §3.1 (HIGH severity, load-bearing on §3 empirical reading).
**Wave 293 fix:** P3 §2.2 + P4 §1.1 — 10 sign-flips across 4 primary + 3 related docs.
**Verification:** §2 above. All 7 primary + 3 related flips landed in `(1 + cos)` form.
**Status:** **FIXED** — load-bearing sign inversion resolved; paper, CLAIMS, schedule-theory, and wave292-final all now align with code direction (anneal DOWN `n_max → n_min`).

### 3.2 M-MED-1: "Framework default since Wave 34" — factory-level only — **PENDING**

**Source:** Wave 292 P3 §3.2 (MEDIUM severity).
**Paper location:** `docs/drafts/paper-flat-flattened.md:52` (the §2.1 framing paragraph) + `paper-flat-flattened.md:201` (the Wave 292 P3 crosscheck audit table that documents the mismatch).
**Current state at line 52:**

> "The `CodimensionSheetScheduler` is the framework default since Wave 34 (replacing the legacy cosine default) and is the closed-form implementation of paper Lemma 2 + Lemma 3 + Lemma 5 (CLM-006, ACTIVE). It is also the only family exposed by the `default_paper_ratio_scheduler()` factory at `adaptive_reflow/algorithm/scheduler/simple.py:307-405`. The corresponding legacy factory `default_cosine_scheduler()` emits a `DeprecationWarning` but is retained for repro baselines."

**Why not fixed in Wave 293:** Wave 293 P3 §2.2 was scoped to sign-flip ONLY (per Wave 296 strict-clean additive rule). The "framework default" framing claim is a separate text-softening fix that requires adding a caveat sentence about 12/13 R-cells using `default_cosine_scheduler()` per Wave 292 P2.
**Recommendation:** PAPER EDIT — change "is the framework default since Wave 34" to "is the framework factory default since Wave 34" and add a one-sentence caveat: "12/13 R-cells (R1, R2, R3, R5a, R5, R5b, R5c, K1, K4+K5, K7, R5c-production) still instantiate `default_cosine_scheduler()` at the adapter level per Wave 292 P2 §MS.config_genealogy; migration is forthcoming in Wave 281+ paper-quantity-driven sweeps." Source: `docs/audit/wave292-p2-config-genealogy.md`.
**Status:** **PENDING** for Wave 294 P2.

### 3.3 M-MED-2: ConvergenceAdaptiveScheduler / PaperRatioAdaptiveScheduler registry key vs `schedule_family()` — **PENDING**

**Source:** Wave 292 P3 §3.3 (MEDIUM severity, affects audit-trail provenance and config round-trip).
**Paper location:** `docs/drafts/paper-flat-flattened.md:202` (the Wave 292 P3 crosscheck audit table).
**Current state at line 202:**

> "M-MED-2 | `ConvergenceAdaptiveScheduler` registry key vs `schedule_family()` value | Table 2.1 registry key `convergence_adaptive` | Registry key in `SCHEDULER_REGISTRY` (nfe_aware.py:558): `"convergence_adaptive"`; but `ConvergenceAdaptiveScheduler.schedule_family()` returns `"convergence_adaptive_cosine"` (`adaptive.py:531`). Same pattern for `paper_ratio_adaptive` → `"paper_ratio_adaptive_codimension"` (`adaptive.py:2297`). | **MEDIUM** | PAPER EDIT: in Table 2.1, distinguish the `build_scheduler` dispatch key from the `ScheduleSample` provenance field. CODE EDIT (optional, `adaptive.py:531, 2297`): normalise the `schedule_family()` return values to match the registry keys."

**Why not fixed in Wave 293:** Same Wave 296 additive rule; this is a paper-Table 2.1 + Table 2.5 clarification, not a sign-flip.
**Recommendation:** PAPER EDIT — in Table 2.1 (`docs/drafts/paper-flat-flattened.md:47` and `:49`), add a column "ScheduleSample provenance" alongside "Registry key" with values `"convergence_adaptive_cosine"` and `"paper_ratio_adaptive_codimension"` respectively. Source: `adaptive_reflow/algorithm/scheduler/adaptive.py:531, 2297`. Optional CODE EDIT — normalise the two `schedule_family()` return values to match registry keys for one-to-one provenance.
**Status:** **PENDING** for Wave 294 P2.

### 3.4 M-LOW-1: DeprecationWarning factory-vs-class — **PENDING**

**Source:** Wave 292 P3 §3.4 (LOW severity, paper wording conflates factory deprecation with class deprecation).
**Paper location:** `docs/drafts/paper-flat-flattened.md:62` (Table 2.2 row for `CosineAnnealScheduler`) + `paper-flat-flattened.md:203` (the Wave 292 P3 crosscheck audit table).
**Current state at line 62:**

> "`CosineAnnealScheduler` | `cosine` | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 + cos(π r / (L − 1)))`. Forward-noise mass = $A_g$ if `profile_residual_fn` supplied, else `sqrt(n_cap)` | `adaptive_reflow/algorithm/scheduler/simple.py:71` | CLM-005 (ACTIVE — canonical Lemma 2 implementation); CLM-019 (ACTIVE). DEPRECATED as default since Wave 34 (replaced by `default_paper_ratio_scheduler`)"

**Why not fixed in Wave 293:** Same additive rule; the change is to the "DEPRECATED as default" phrasing, not to the formula.
**Recommendation:** PAPER EDIT — replace "DEPRECATED as default since Wave 34 (replaced by `default_paper_ratio_scheduler`)" with "`default_cosine_scheduler()` factory emits `DeprecationWarning`; the `CosineAnnealScheduler` class is still actively used as headline on 12/13 R-cells per Wave 292 P2 §MS.config_genealogy." Source: `simple.py:453-462` (factory DeprecationWarning) + `wave292-p2-config-genealogy.md` (12/13 R-cells).
**Status:** **PENDING** for Wave 294 P3.

### 3.5 M-LOW-2: `CosineAnnealScheduler` schedule_family() default — **PENDING**

**Source:** Wave 292 P3 §3.5 (LOW severity, audit-trail provenance).
**Paper location:** `docs/drafts/paper-flat-flattened.md:62` (Table 2.2 row) + `paper-flat-flattened.md:134` (Table 2.x reference row) + `paper-flat-flattened.md:204` (the Wave 292 P3 crosscheck audit table).
**Current state at line 62:**

> "Family: `CosineAnnealScheduler` | Registry key: `cosine`" — does not mention `schedule_family()` default.

**Current state at line 134:**

> "`family=cosine_no_restart`; `profile_residual_fn=None`" — references the default but does not label it as "schedule_family() default".

**Why not fixed in Wave 293:** Same additive rule; this is a Table 2.2 + Table 2.x clarification.
**Recommendation:** PAPER EDIT — in Table 2.2 row at line 62, add a column "ScheduleSample provenance" with value `"cosine_no_restart"` (the `CosineScheduleConfig.schedule_family` default at `simple.py:413`). Source: `adaptive_reflow/algorithm/scheduler/simple.py:191, 413`.
**Status:** **PENDING** for Wave 294 P3.

### 3.6 M-LOW-3: MultiChannelJitteredConstantScheduler duplicate at `scheduler_extra.py:999` — **PENDING**

**Source:** Wave 292 P3 §3.6 (LOW severity, dead-code overlap, not behavioural).
**Paper location:** `docs/drafts/paper-flat-flattened.md:102` (Table 2.5 row) + `paper-flat-flattened.md:205` (the Wave 292 P3 crosscheck audit table).
**Current state at line 102:**

> "`MultiChannelJitteredConstantScheduler` | `multi_channel_jittered` | None | Per-channel `n_cap = base_n_cap + jitter_std · N(0,1)` clipped to `[0,1]` with per-channel rng. Family name `multi_channel_jittered`. **NOTE:** registered ONLY via `build_scheduler_from_config` dispatch (not in `SCHEDULER_REGISTRY` dict at `adaptive_reflow/algorithm/scheduler/nfe_aware.py:551`) — subtle discoverability gap | `adaptive_reflow/algorithm/scheduler_r2.py:30`"

**Why not fixed in Wave 293:** Same additive rule; this is a Table 2.5 citation clarification.
**Recommendation:** PAPER EDIT — add `(also declared at scheduler_extra.py:999 as dead code; not dispatched by `build_scheduler_from_config`)` to the Table 2.5 row's code citation column. OR CODE EDIT (small, optional) — remove the duplicate class at `scheduler_extra.py:999` to deduplicate. Source: `adaptive_reflow/algorithm/scheduler_r2.py:30` + `adaptive_reflow/algorithm/scheduler_extra.py:999` + `nfe_aware.py:762-766`.
**Status:** **PENDING** for Wave 294 P3.

---

## 4. New findings this audit

### 4.1 FINDING-NEW-1: Wave 292 P3 GAP-LOW-3 (`MultiChannelJitteredConstantScheduler` structural conformance) overlaps with M-LOW-3

While re-reading `paper-flat-flattened.md:208`, noticed that Wave 292 P3 GAP-LOW-3 ("`MultiChannelJitteredConstantScheduler` does not explicitly extend `SchedulerProtocol`") is documented in the same crosscheck audit table but **not separately flagged as PENDING for Wave 294**. This is a CODE EDIT (trivial) — add `SchedulerProtocol` as the explicit base class at `scheduler_r2.py:30` to make the §2 CLM-019 conformance claim literal rather than structural. Flagged here for Wave 294 P3 inventory.

### 4.2 FINDING-NEW-2: Sequential-protocol.md §2 worked example rewrite is the largest PENDING item

`docs/sequential-protocol.md:50, 85-87, 95-96` uses the `(1 - cos)` formula throughout with internally-consistent table values and prose that says "cosine starts at its minimum and climbs to n_max". Per Wave 293 P4 §3 row + Wave 293 final §6.2, this is a non-additive edit (would require rewriting table values + prose to flip direction). This is the largest of the 3 outstanding items from Wave 293 and was originally deferred to "Wave 294 P2". Recommend Wave 294 P2 budget ≥ 30 min for this rewrite.

---

## 5. Remaining work for Wave 294

### 5.1 Wave 294 P2 — MEDIUM-severity paper-text fixes (recommended first)

| Item | File | Line | Type | Severity | Effort |
|---|---|---:|---|:---:|---:|
| M-MED-1: "framework default" framing softening | `docs/drafts/paper-flat-flattened.md` | 52 | PAPER EDIT (1 sentence add + 1 sentence rephrase) | MEDIUM | 10 min |
| M-MED-2: Registry key vs `schedule_family()` distinction in Table 2.1 | `docs/drafts/paper-flat-flattened.md` | 47, 49 (Table 2.1) | PAPER EDIT (add column or add note) | MEDIUM | 15 min |
| Sequential-protocol §2 worked example rewrite (Wave 293 P4 outstanding) | `docs/sequential-protocol.md` | 50, 85-87, 95-96 | PAPER EDIT (non-additive; rewrite table values + prose) | MEDIUM | 30 min |

### 5.2 Wave 294 P3 — LOW-severity presentation fixes (optional)

| Item | File | Line | Type | Severity | Effort |
|---|---|---:|---|:---:|---:|
| M-LOW-1: DeprecationWarning factory-vs-class note | `docs/drafts/paper-flat-flattened.md` | 62 (Table 2.2 row) | PAPER EDIT (replace "DEPRECATED as default" with factory-only note) | LOW | 5 min |
| M-LOW-2: `schedule_family()` default in Table 2.2 | `docs/drafts/paper-flat-flattened.md` | 62 (Table 2.2 row) | PAPER EDIT (add "ScheduleSample provenance: `cosine_no_restart`") | LOW | 5 min |
| M-LOW-3: MultiChannelJitteredConstantScheduler dual citation | `docs/drafts/paper-flat-flattened.md` | 102 (Table 2.5 row) | PAPER EDIT (add dead-code note) OR CODE EDIT (deduplicate scheduler_extra.py:999) | LOW | 5-15 min |
| GAP-LOW-3 (Wave 292 P3): MultiChannelJitteredConstantScheduler structural conformance | `adaptive_reflow/algorithm/scheduler_r2.py` | 30 | CODE EDIT (add `SchedulerProtocol` explicit base) | LOW | 5 min |
| GAP-LOW-1 (Wave 292 P3): Orphan `SCHEDULER_FAMILIES` entries | `adaptive_reflow/algorithm/protocol_registry.py` | 53-74 | CODE EDIT (remove `warmup_linear`, `geometric`, `piecewise_sigmoid`, `handoff`) | LOW | 10 min |
| Denominator-bug fix (Wave 293 final §6.2 outstanding) | `docs/audit/wave292-p2-config-genealogy.md`, `docs/audit/scheduler-per-cell-summary.md`, `docs/audit/wave288-p1-honest-progress-summary.md` | 6 lines | PAPER EDIT (additive; `cycle_length` → `(cycle_length - 1)`) | LOW | 15 min |

### 5.3 No action required

- All 19 scheduler families cited in §2 exist at the cited line numbers (verified Wave 292 P3).
- All defaults (kp, kd, ki, max_step, target_ratio, threshold, sigma_min, sigma_max, rho, ema, integral_window, handoff_window) match the paper's stated values (verified Wave 292 P3).
- §2.6 calibration helper `paper_quantity_driven_beta()` is at `adaptive.py:2576` as cited (verified Wave 292 P3).
- §1 four-port surface classes all exist (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) (verified Wave 292 P3).

---

## 6. Invariants — all preserved

| Invariant | Status |
|---|---|
| D.4 30/30 PASS | YES (per Wave 293 P5 §3.1; no edits this audit) |
| claims no drift | YES (per Wave 293 P5 §3.2; this audit is READ-ONLY) |
| ruff 0 | YES (per Wave 293 P5 §3.3; this audit is READ-ONLY) |
| mkdocs 0 warnings | YES (per Wave 293 P5 §3.4; this audit is READ-ONLY) |
| ledger byte-deterministic | YES (per Wave 293 P5 §3.5; no edits this audit) |
| vendored NOT touched | YES (READ-ONLY audit; no edits to vendored adapters or tools) |
| framework NOT touched | YES (READ-ONLY audit; no edits to `adaptive_reflow/*.py` or `tests/*.py`) |

---

## 7. Audit metadata

- **Wave:** 294 P1 (re-inventory after Wave 293 fix)
- **Mode:** READ-ONLY audit (no code edits, no paper edits, no commits)
- **Files audited:** 7 (4 primary Wave 293 fix targets + 3 related docs)
- **Cross-references:** `docs/audit/wave292-p3-crosscheck.md` (source of 6 mismatches) + `docs/audit/wave293-final.md` (Wave 293 final verify) + `docs/audit/wave293-p3-fix-applied.md` (primary 7-flip patch) + `docs/audit/wave293-p4-related-docs.md` (3 related-docs flips)
- **Code citations re-verified:** `adaptive_reflow/schedule/cosine.py:159, 227` + `adaptive_reflow/algorithm/scheduler/simple.py:71, 191, 413, 453-462` + `adaptive_reflow/algorithm/scheduler/adaptive.py:531, 2297` + `adaptive_reflow/algorithm/scheduler_r2.py:30` + `adaptive_reflow/algorithm/scheduler_extra.py:999` + `adaptive_reflow/algorithm/scheduler/nfe_aware.py:551, 558, 762-766` + `adaptive_reflow/algorithm/sequential_handoff.py:46`
- **Paper section re-audited:** §2 (Algorithm: Framework scheduler taxonomy — Table 2.1 / 2.2 / 2.5) + §1 Introduction (4-port surface list, unchanged from Wave 292 P3)
- **Invariants:** vendored NOT touched (no edits); framework NOT touched (no edits); all 5 Wave 293 gates verified clean per Wave 293 P5.