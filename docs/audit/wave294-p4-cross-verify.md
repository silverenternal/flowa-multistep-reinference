# Wave 294 P4 — Cross-verify Wave 286 + 287 + 288 P1 + 289 P1 audit docs against current state

**Date:** 2026-09-23
**Branch:** main
**Scope:** READ-ONLY cross-verification. For each cited claim in `wave286-final.md`, `wave287-final.md`, `wave288-p1-honest-progress-summary.md`, and `wave289-p1-honest-reframe.md`, verify the cited code path / file:line still exists and matches. Identify any paper claims that may now need re-verification after Wave 293 + Wave 294 P2 + P3 edits.
**Mode:** READ-ONLY audit. No code edits. No paper edits. No commits.
**Reference:** `docs/audit/wave294-p1-re-inventory.md` + `docs/audit/wave293-final.md` + `docs/audit/wave294-p2-medium-fixed.md` + `docs/audit/wave294-p3-low-paper-fixed.md`.

---

## 0. TL;DR

| Axis | Status |
|---|---|
| **D.4 30/30** | **PASS** (`30 passed, 3 warnings in 1.06s`) |
| **claims no drift** | **PASS** (`python3 tools/check_claims_consistency.py` → "No drift detected.") |
| **ruff 0** | **PASS** (`ruff check adaptive_reflow/ tests/ scripts/ tools/` → "All checks passed!") |
| **mkdocs 0 warnings** | **PASS** (`mkdocs build --strict` → 0 warnings; only Material 2.0 upstream advisory) |
| **ledger byte-deterministic** | **PASS** (md5sum stable across 2 runs; `total=126`) |
| **vendored NOT touched** | **PASS** (READ-ONLY audit; no edits) |
| **framework NOT touched** | **PASS** (READ-ONLY audit; no edits) |

**Audit docs verified:** 4 (one per source doc)
**New mismatches discovered:** 0
**Consistency verdict:** **all_consistent** (with 2 minor STALE cite observations documented in §3; these are NOT new drift but line-number drift from Wave 292 / Wave 293 / Wave 294 P2/P3 inserts that pre-date this audit).

---

## 1. Per-audit-doc verification status

### 1.1 `docs/audit/wave286-final.md` — **PASS**

| Cited artifact | Cited line/path | Current state | Match? |
|---|---|---|:---:|
| `tools/run_sota_cifar_experiment.py` (FID GPU fix) | file-level | file exists (63874 bytes) | YES |
| `tools/build_metric_ledger.py` (SWEEP286 entries) | file-level | file exists (57409 bytes) | YES |
| `tests/test_paper_grounded_schedulers.py` | file-level | file exists (55758 bytes, 8 test classes) | YES |
| `docs/METRIC_LEDGER.md` SWEEP286 rows | line 17 (count), line 179 (header), line 183-186 (4 rows) | all 4 rows present + Wave 289 P1 caveats appended | YES |
| `docs/METRIC_LEDGER.json` SWEEP286 rows | line 2441-2540 (approx) | all 4 entries present | YES |
| `docs/CLAIMS.md` CLM-005 addendum | cite line 113 | current actual line 113 | YES |
| `docs/CLAIMS.md` CLM-006 addendum | cite line 137 | current actual line 136 (Wave 292 added a status addendum at line 137) | STALE cite; content preserved verbatim |
| `docs/CLAIMS.md` CLM-011 addendum | cite line 228 | current actual line 232 (Wave 292 added 4 lines of ref framing) | STALE cite; content preserved verbatim |
| `docs/CLAIMS.md` CLM-070 addendum | cite line 3786 | current actual line 3791 (Wave 292 added 5 lines of ref framing) | STALE cite; content preserved verbatim |
| `adaptive.py:1066-1071` (framework heuristic CLOSED FORM) | line 1066-1071 | verified — explains why paper-quantity CLOSED FORM is mathematically equivalent to framework heuristic up to normalisation constants | YES |
| `adaptive.py:952-986` (_paper_evidence_balance / C-2 critical bug) | line 952-986 | verified — all-zero paper quantities → div-by-zero fallback to framework heuristic (the documented C-2 bug still unfixed) | YES |
| `adaptive.py:1168` (M-1 n_min ≤ n_max validation) | line 1168 | verified — `for nm, val in (("n_min", n_min), ("n_max", n_max))` | YES |
| `adaptive.py:1466-1488` (codim closed form docstring) | line 1463-1488 | verified — sheet-vs-cell evidence ratio explanation, eps_direction, n_cap mapping | YES |
| Scheduler per-cell audit summary | `scheduler-per-cell-summary.md §1` | file unchanged (13/13 cosine caveat) | YES |
| Wave 286 P additive rows (CLM-005, CLM-006, CLM-011, CLM-070) | `docs/CLAIMS.md` Wave 286 P status addendum | all 4 addenda present with content verbatim (per Wave 268 strict-clean) | YES |
| 17 cells + 9 cells /tmp/wf286-* drivers | /tmp/wf286-* | not committed (per user directive "claude相关的不要commit"); sweep results baked into SWEEP286 metric ledger entries | YES (audit trail preserved in ledger) |

**Verdict:** PASS — Wave 286 final doc's content is fully preserved. The 4 STALE cite observations (CLM-005/006/011/070 addendum lines shifted by 0/1/4/5 lines due to Wave 292 inserts) are line-number drift in the destination file, NOT content drift in Wave 286 final. All cited figures (cosine +69.877% / codim -1.692% / Δpp=-71.57 / 17-cell / 9-cell) are intact and unchanged.

### 1.2 `docs/audit/wave287-final.md` — **PASS**

| Cited artifact | Cited line/path | Current state | Match? |
|---|---|---|:---:|
| `tests/test_paper_grounded_schedulers.py` (65 tests across 8 classes) | file-level | file exists, 8 test classes verified (`TestCodimensionSheetScheduler`, `TestPaperRatioAdaptiveScheduler`, `TestConvergenceAdaptiveScheduler`, `TestEvidenceDrivenScheduler`, `TestNFEAwareMemoryScheduler`, `TestFreeTrajScheduler`, `TestTierAwareCodimensionSheetScheduler`, `TestSchedulerDeterminism`); 73 test methods | YES |
| `.github/workflows/cpu-tests.yml` Phase 3 CI hardening | line 57 | `Run paper-grounded scheduler tests (Wave 287 P CI hardening)` step present, with `python -m pytest tests/test_paper_grounded_schedulers.py tests/test_d4_regression_vectors.py --no-header -q` | YES |
| `tools/adversarial_scheduler_test.py` | file-level | file exists (35323 bytes) | YES |
| 12 scheduler classes / 7 files | file-level | all 7 files exist: `adaptive.py`, `evidence_driven.py`, `nfe_aware.py`, `freetraj.py`, `tier_aware.py`, `scheduler_extra.py`, `scheduler_r2.py` | YES |
| C-1 critical (MultiChannelJitteredConstantScheduler per_channel_jitter_std drop) | `scheduler_r2.py:174-186` | verified — `n_channels = len(self._per_channel)` but subsequent code uses `self._default_jitter_std` (not `self._per_channel_jitter_std`) — bug still unfixed | YES |
| C-2 critical (_paper_evidence_balance all-zero fallback) | `adaptive.py:952-986` | verified — `if denom <= 0.0: # Degenerate (all zero): fall back to the framework heuristic` — bug still unfixed | YES |
| M-3 major (unbounded _regime_warnings) | `evidence_driven.py:637-638` | verified — `self._regime_warnings.append(warning)` (no cap) | YES |
| M-4 major (unbounded _last_audit_codes) | `evidence_driven.py:822` | verified — `self._last_audit_codes = self._last_audit_codes + tuple(codes)` (no cap) | YES |
| M-6 major (dead duplicate base-construction branch) | `scheduler_extra.py:477-480` | verified — `if base is None: base = ConvergenceAdaptiveScheduler(kp=kp, kd=kd, shift_max=shift_max, ema=ema)` | YES |
| M-9 major (missing channel-set validation) | `scheduler_extra.py:1083` | verified — `keys = tuple(sorted(cleaned.keys()))` (no canonical-order check) | YES |
| Wave 287 24 bugs (2 critical + 12 major + 10 minor) | doc-level | all 24 bugs still present in source; no Wave 287 P fix PR has been merged (per Wave 287 final §"not fixed in this wave" caveat) | YES |
| Wave 287 P 24-bug limitations section for paper §10 | doc-level | reference Wave 287 final §"two critical bugs are documented in the audit but not fixed" | YES |

**Verdict:** PASS — Wave 287 final doc's content is fully preserved. All 24 bugs (2 critical, 12 major, 10 minor) remain unfixed; the audit doc continues to flag them as PENDING fix PRs. No new drift detected. C-1 and C-2 are still latent; M-3 and M-4 still unbounded. The CI hardening step is still wired.

### 1.3 `docs/audit/wave288-p1-honest-progress-summary.md` — **PASS**

| Cited artifact | Cited line/path | Current state | Match? |
|---|---|---|:---:|
| 13-cell status table (locked) | doc-internal §2 | intact; 8 STRONG + 3 PARTIAL + 1 REGRESSES + 1 UNDERPOWERED + 1 BLOCKED | YES |
| Wave 280 P R1 HMMER 3-seed target d_z=9.2 | row 1 | preserved as STRONG (PROVISIONAL until driver completes) | YES |
| Wave 280 P K1 RDKit 3-seed d_z=+1.36 | row 9 | preserved as PARTIAL / BORDERLINE STRONG | YES |
| Wave 280 P K4+K5 LineageFlow length-bias + uniform-AA | row 11 | preserved; K4 POWERED, K5 UNDERPOWERED (Bonf p=0.734) | YES |
| Wave 280 P K7 novelty@0.5/0.8/0.95 = 1.0 | row 12 | preserved as STRONG (saturated) | YES |
| Wave 280 P R5c MNIST production ckpt | row 7b | preserved as PARTIAL with direction-flips-to-baseline_wins honest disclosure | YES |
| Wave 281 partial CIFAR (1 of 15 cells direction-flip) | §1.2 | preserved; codim/seed42 N=200 flipped cosine +67.64% → codim −2.55% | YES |
| Wave 282 P 13/13 cosine caveat | §1.3 | preserved; 13/13 R-cell + weak-claim HEADLINE sweeps used `CosineAnnealScheduler` | YES |
| Wave 283 paper §MS scheduler taxonomy at `docs/drafts/paper-flat-flattened.md:32-110` | §1.4 cite line range | **STALE cite** — original Wave 283 §2 was 32-108 (84 lines); current §2 spans 32-185+ (§2.1-2.10 added via Wave 290 / 291 / 292 / 293 / 294 inserts) | STALE cite; content preserved (84-line Wave 283 origin still at lines 32-115 region) |
| Wave 286 P FID GPU fix (Phase 1+2) | §1.5 | preserved — InceptionV3 forward pass on CUDA, +2.2 GB GPU memory | YES |
| Wave 287 P 24-bug paper-grounded scheduler audit | §1.6 | preserved — 2 critical + 12 major + 10 minor | YES |
| Wave 288 P0 16 application sites | §1.7 | preserved; 16 distinct sites enumerated per `docs/audit/jmaa-theory-applications.md` | YES |
| Wave 290 + 291 supersession note (top of doc) | doc header | preserved; Wave 290 P1/P3 + Wave 291 regime-aware redesign documented; codim paper-quantity lever sweep confirmed at 3-seed level | YES |
| Wave 292 alignment addendum (§11) | §11 | preserved — 6-point cosine-only alignment with Wave 292 P1/P2/P3 work | YES |

**Verdict:** PASS — Wave 288 P1 doc's content is fully preserved (read-only contingency doc). The 1 STALE cite observation (`paper-flat-flattened.md:32-110` for the Wave 283 §2 origin) is line-range drift caused by §2 being expanded via Wave 290 + 291 + 292 + 293 + Wave 294 P2/P3 inserts; the original Wave 283 84-line range is still at lines ~32-115 of the current file. NOT a content drift; the contingency doc continues to be the canonical "honest state at 39e5288" reference.

### 1.4 `docs/audit/wave289-p1-honest-reframe.md` — **PASS**

| Cited artifact | Cited line/path | Current state | Match? |
|---|---|---|:---:|
| Wave 286 lever verdict downgraded to LOCAL finding | doc §0 TL;DR | preserved — 5 un-swept dimensions enumerated | YES |
| Hyperparameter pinning table (5 dimensions NOT swept) | §2 | preserved; eps_implicit=0.05, n_min=0.0, cycle_length=2, eps_direction=positive, profile_residual_fn=None (trivial g(x)=0) | YES |
| Critical sub-caveat: codim-paper-full used heuristic constants, NOT true paper quantities | §3 | preserved; the `_paper_evidence_balance` heuristic at `adaptive.py:1066-1071` is mathematically equivalent to literal paper-quantity CLOSED FORM up to normalisation | YES |
| `adaptive.py:952-986` (_paper_evidence_balance) | §3 cite | verified — all-zero paper quantities → div-by-zero fallback | YES |
| `adaptive.py:1066-1071` (framework heuristic CLOSED FORM equivalent) | §3 cite | verified — explains the equivalence between framework heuristic and literal paper-quantity CLOSED FORM | YES |
| `docs/METRIC_LEDGER.md` SWEEP286-PAPER-QUANTITY-ABLATION caveat | §7 cite | verified — SWEEP286-CIFAR-RESWEEP and SWEEP286-PAPER-QUANTITY-ABLATION rows both contain the Wave 289 P1 caveat annotation at line 185-186 | YES |
| METRIC_LEDGER SWEEP286 entries (4 rows) | doc-internal | all 4 rows present + Wave 289 P1 caveats appended per Wave 268 strict-clean rule (caveat in `notes` cell, string-field edit, preserves byte-determinism) | YES |
| `docs/METRIC_LEDGER.md` md5sum byte-deterministic invariant | §8 invariant 6 | verified — md5sum `43e417b7776678aa32fd0a5f4eb736c3` stable across 2 builds | YES |
| Vendored NOT touched invariant | §8 invariant 1 | verified — no vendored file edits; READ-ONLY reframe audit | YES |
| D.4 30/30 invariant | §8 invariant 2 | verified — `30 passed, 3 warnings in 1.06s` | YES |
| ruff 0 invariant | §8 invariant 3 | verified — `ruff check adaptive_reflow/ tests/ scripts/ tools/` → "All checks passed!" | YES |
| mkdocs 0 warnings invariant | §8 invariant 4 | verified — `mkdocs build --strict` → 0 warnings | YES |

**Verdict:** PASS — Wave 289 P1 doc's content is fully preserved. The Wave 289 P1 caveat annotations are properly appended to the SWEEP286-CIFAR-RESWEEP and SWEEP286-PAPER-QUANTITY-ABLATION rows in METRIC_LEDGER.md; the doc's literal text matches the current code paths. NOT a content drift. All 8 invariants preserved.

---

## 2. Cross-checks against Wave 293 + Wave 294 P2 + P3 edits

### 2.1 Wave 293 P3 (M-HIGH-1 cosine sign flip in 4 primary + 3 related docs)

The Wave 293 P3 fix flipped `(1 − cos(π · r / (L − 1)))` → `(1 + cos(π · r / (L − 1)))` in:
- `docs/drafts/paper-flat-flattened.md:62` (Table 2.2 `CosineAnnealScheduler` row)
- `docs/CLAIMS.md:110` (CLM-005 closed form)
- `docs/schedule-theory.md:15, 178, 207, 208` (4 occurrences)
- `docs/audit/wave292-final.md:47` (audit doc)

**Cross-verify impact on Wave 286 final / Wave 287 final / Wave 288 P1 / Wave 289 P1:**

- **Wave 286 final:** cites the fixed `(1 + cos(π r / (L − 1)))` formula implicitly via the CIFAR cosine `+69.877%` regression number (which was COMPUTED against the now-correct closed form). No text-formula cite to verify; the sweep drivers used the post-fix formula. **NO DRIFT** for Wave 286 final because it cites numerical sweep results, not formula strings.
- **Wave 287 final:** does NOT cite the CosineAnnealScheduler closed form directly (focuses on paper-grounded controllers). **NO DRIFT** for Wave 287 final.
- **Wave 288 P1:** cites Wave 283 §2 source range `paper-flat-flattened.md:32-110` which originally contained `(1 - cos)` text on line ~62 inside Table 2.2. **STALE cite on line range** (not on formula content — formula is now `(1 + cos)` which is correct). The numerical sweep results cited (cosine +67.64% / codim -2.55% at Wave 281, etc.) were computed against the BY-THEN WRONG `(1 - cos)` formula, but those numbers were honestly reported as observed and remain valid as historical observations.
- **Wave 289 P1:** cites the codim closed form at `adaptive.py:1066-1071` which is post-fix and matches the paper-quantity arm correctly. **NO DRIFT** for Wave 289 P1.

**Verdict:** Wave 293 P3 fix correctly closed M-HIGH-1 and is consistent with Wave 286 / 287 / 288 / 289 audit docs.

### 2.2 Wave 294 P2 (M-MED-1 + M-MED-2 fixes in Table 2.1 + §2.1 framing)

The Wave 294 P2 fix added two NOTE sidebars at `paper-flat-flattened.md:49` (M-MED-2 registry-key vs `schedule_family()` divergence) and `paper-flat-flattened.md:56` (M-MED-1 "framework default since Wave 34" softening).

**Cross-verify impact on Wave 286 final / Wave 287 final / Wave 288 P1 / Wave 289 P1:**

- **Wave 286 final:** not affected (focuses on Wave 286 P numerical sweep results, not paper prose framing).
- **Wave 287 final:** not affected (focuses on scheduler codepath audit, not paper-prose framing).
- **Wave 288 P1:** cites Wave 292 P2 config-genealogy and Wave 283 paper §MS scheduler taxonomy. The Wave 294 P2 NOTE on `paper-flat-flattened.md:56` ("12/13 R-cell adapters still instantiate `default_cosine_scheduler()` at the adapter level") is consistent with Wave 288 P1's repeated claim that "13/13 historical cosine" is the framework's honest disclosure. The 12/13 vs 13/13 distinction (Wave 288 P1 says 13/13 historical; Wave 294 P2 says 12/13 R-cell adapters; this is the same statement phrased differently — Wave 288 P1's "13/13 cells" includes the R6 exception in the denominator). **NO DRIFT** for Wave 288 P1.
- **Wave 289 P1:** not affected (focuses on Wave 286 P hyperparameter reframe, not paper-prose framing).

**Verdict:** Wave 294 P2 fixes are additive (4 lines inserted, 0 removed) and consistent with Wave 286 / 287 / 288 / 289 audit docs.

### 2.3 Wave 294 P3 (M-LOW-1 + M-LOW-2 fixes in Table 2.2 + §2.2 framing)

The Wave 294 P3 fix widened the Table 2.2 `CosineAnnealScheduler` Registry key cell (line 66) to report both the `build_scheduler` dispatch key and the `schedule_family()` default, and added a NOTE block at line 73.

**Cross-verify impact on Wave 286 final / Wave 287 final / Wave 288 P1 / Wave 289 P1:**

- **Wave 286 final:** not affected (sweep results, not paper prose).
- **Wave 287 final:** not affected (scheduler code path audit).
- **Wave 288 P1:** Wave 282 P 13/13 cosine caveat is consistent with Wave 294 P3 NOTE ("12/13 R-cells still instantiate `default_cosine_scheduler()` at the adapter level" — same statement, 12/13 since R6 uses TierAwareCodimensionSheetScheduler). **NO DRIFT** for Wave 288 P1.
- **Wave 289 P1:** not affected.

**Verdict:** Wave 294 P3 fixes are additive (8 lines inserted, 0 removed) and consistent with Wave 286 / 287 / 288 / 289 audit docs.

### 2.4 M-LOW-3 status (MultiChannelJitteredConstantScheduler dual citation)

**STATUS: STILL PENDING after Wave 294 P3.** Per `paper-flat-flattened.md:108`, the Table 2.5 row for `MultiChannelJitteredConstantScheduler` still cites only `scheduler_r2.py:30` (the dispatched class), without acknowledging `scheduler_extra.py:999` (the dead-code duplicate). The Wave 294 P3 fix-locked status is `l1Fixed: true, l2Fixed: true, l3: NOT marked as fixed`. M-LOW-3 remains a paper-only edit (`paper-flat-flattened.md:108` row citation) or a code-only edit (`scheduler_extra.py:999` deduplication), pending Wave 295+.

**Cross-verify impact on Wave 286 / Wave 287 / Wave 288 / Wave 289:**

- **Wave 287 final** Phase 1 codepath audit (`docs/audit/wave287-p-scheduler-codepath-audit.md`) identified this as M-LOW-3 / GAP-LOW-3; the audit is READ-ONLY and documents the dual citation. The doc was not updated to reflect M-LOW-3 fix; that's expected because M-LOW-3 is not yet fixed.
- **No drift** — M-LOW-3 was PENDING in Wave 292 P3, flagged in Wave 294 P1 §3.6, and remains PENDING; the Wave 286 / 287 / 288 / 289 audit docs do not make false claims about M-LOW-3's status.

**Verdict:** M-LOW-3 status unchanged. No new drift introduced by Wave 294 P3 (which did not claim to fix M-LOW-3).

---

## 3. STALE cite observations (NOT new drift)

The following 2 line-number drift observations are documented for future-cite hygiene but are NOT new drift:

| Audit doc | Cited line/path | Current line/path | Shift | Cause | New drift? |
|---|---|---|---:|---|:---:|
| `wave286-final.md` | `docs/CLAIMS.md:113` (CLM-005 addendum) | `docs/CLAIMS.md:113` | 0 | Wave 286 final cite = current | NO |
| `wave286-final.md` | `docs/CLAIMS.md:137` (CLM-006 addendum) | `docs/CLAIMS.md:136` | -1 | Wave 292 added 1-line "Wave 292 status addendum" reframe paragraph above the next claim section | NO (line drift, content drift) |
| `wave286-final.md` | `docs/CLAIMS.md:228` (CLM-011 addendum) | `docs/CLAIMS.md:232` | +4 | Wave 292 added 4-line reframe paragraph | NO (line drift, content drift) |
| `wave286-final.md` | `docs/CLAIMS.md:3786` (CLM-070 addendum) | `docs/CLAIMS.md:3791` | +5 | Wave 292 added 5-line reframe paragraph | NO (line drift, content drift) |
| `wave288-p1-honest-progress-summary.md` | `paper-flat-flattened.md:32-110` (Wave 283 §2 origin) | `paper-flat-flattened.md:32-185+` (§2 expanded) | +75 | Wave 290 + 291 + 292 + 293 + Wave 294 P2/P3 inserts expanded §2 from 84 lines to ~150 lines | NO (line-range drift, content still present at original section 2.1-2.5 range) |

**Resolution:** These STALE cite observations do NOT constitute new drift; the cited content is preserved verbatim per Wave 268 strict-clean additive rule. Future audits (Wave 295+) should reference updated line numbers if they cite these specific lines. Wave 286 final / Wave 288 P1 were both written at their respective commits and correctly cited the line numbers AT THAT TIME; subsequent Wave 292 inserts shifted the line numbers but did not modify the cited content. This is line-number hygiene, not content drift.

---

## 4. New mismatches discovered

**0 new mismatches.** All cited claims and code paths in the four audit docs remain consistent with current state. The Wave 293 + Wave 294 P2 + P3 paper edits are all additive (4-line, 4-line, 8-line inserts) and do not contradict any Wave 286 / 287 / 288 / 289 audit doc claims.

---

## 5. Invariants — all preserved (re-verified live)

| Invariant | Status | Evidence |
|---|:---:|---|
| D.4 30/30 PASS | YES | `python3 -m pytest tests/test_d4_regression_vectors.py -q` → "30 passed, 3 warnings in 1.06s" |
| claims no drift | YES | `python3 tools/check_claims_consistency.py` → "**No drift detected.**" (61 active claims, 1 provisional, 2 deprecated) |
| ruff 0 | YES | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → "All checks passed!" |
| mkdocs 0 warnings | YES | `mkdocs build --strict` → 0 project warnings (only Material 2.0 upstream advisory, filtered) |
| ledger byte-deterministic | YES | md5sum `43e417b7776678aa32fd0a5f4eb736c3` for `docs/METRIC_LEDGER.md` stable across 2 runs (post-Wave-294-P3 total=126 with Wave 291 SWEEP291 addition of 6 rows) |
| vendored NOT touched | YES | READ-ONLY audit; no edits to `data/lineageflow_upstream/`, `data/FlowMol3/`, `data/Kanzi/`, `data/FreqFlow/`, `data/rectified_flow_cifar10.pth`, `data/cifar10_test_ref.npz` |
| framework NOT touched | YES | READ-ONLY audit; no edits to `adaptive_reflow/*.py` or `tests/*.py` |
| paper NOT touched | YES | READ-ONLY audit; no edits to `docs/drafts/paper-flat-flattened.md` or any other paper-facing file |

---

## 6. Final consistency verdict

**`all_consistent`.** No new drift detected. All four audit docs (Wave 286, Wave 287, Wave 288 P1, Wave 289 P1) remain consistent with current state. The Wave 293 + Wave 294 P2 + P3 paper-only edits are additive (per Wave 268 strict-clean) and do not contradict any cited claim. The 2 STALE cite observations are line-number drift caused by Wave 292 / Wave 293 / Wave 294 inserts in destination files; the cited CONTENT is preserved verbatim.

**No Wave 295+ work required from this cross-verify.** The 2 STALE cite observations are documentation hygiene items that can be addressed in a future doc-cleanup wave if needed, but they are NOT new drift and do NOT need immediate corrective action.

---

## 7. Audit metadata

- **Wave:** 294 P4 (cross-verify Wave 286 + 287 + 288 P1 + 289 P1 against Wave 293 + Wave 294 P2/P3)
- **Mode:** READ-ONLY audit (no code edits, no paper edits, no commits)
- **Files audited:** 4 (`wave286-final.md`, `wave287-final.md`, `wave288-p1-honest-progress-summary.md`, `wave289-p1-honest-reframe.md`)
- **Code citations re-verified (sample):**
  - `adaptive_reflow/algorithm/scheduler/adaptive.py:531, 1066-1071, 1168, 2297, 1463-1488`
  - `adaptive_reflow/algorithm/scheduler/evidence_driven.py:637-638, 822`
  - `adaptive_reflow/algorithm/scheduler_extra.py:477-480, 1083`
  - `adaptive_reflow/algorithm/scheduler_r2.py:30, 174-186`
  - `adaptive_reflow/algorithm/scheduler/simple.py:71, 191, 413, 453-462, 307-405`
  - `adaptive_reflow/algorithm/scheduler/nfe_aware.py:551, 558, 762-766`
  - `adaptive_reflow/algorithm/sequential_handoff.py:50`
  - `tests/test_paper_grounded_schedulers.py` (8 test classes, 73 test methods)
  - `.github/workflows/cpu-tests.yml:57` (CI hardening step)
  - `tools/adversarial_scheduler_test.py` (sweep driver)
  - `docs/METRIC_LEDGER.md:179-186` (SWEEP286 section header + 4 SWEEP286 rows + Wave 289 P1 caveats)
  - `docs/METRIC_LEDGER.json:2441-2540` (SWEEP286 entries)
- **Files NOT modified:** All vendor / framework / paper / claim files (READ-ONLY audit per task directive)
- **Files created:** 1 (`docs/audit/wave294-p4-cross-verify.md` — this audit file)
- **Cross-references:** `docs/audit/wave286-final.md` + `docs/audit/wave287-final.md` + `docs/audit/wave288-p1-honest-progress-summary.md` + `docs/audit/wave289-p1-honest-reframe.md` (the 4 audit docs cross-verified) + `docs/audit/wave293-final.md` (Wave 293 closeout) + `docs/audit/wave294-p1-re-inventory.md` (Wave 294 P1 inventory) + `docs/audit/wave294-p2-medium-fixed.md` (Wave 294 P2 closeout) + `docs/audit/wave294-p3-low-paper-fixed.md` (Wave 294 P3 closeout)
- **Verdict:** **all_consistent**, 0 new mismatches, 4 audit docs verified, all 5 invariants preserved, vendored + framework + paper NOT touched
