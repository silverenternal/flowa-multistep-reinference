# Wave 293 P4 — Related-docs audit (additional sign fixes)

**Date:** 2026-09-23
**Scope:** audit the 7 docs flagged by Wave 293 P1 §6 + Wave 293 P3 §5 + the explicit task list (STRATEGY_FRAMEWORK_SCOPE.md, ARCHITECTURE.md, TESTING_STRATEGY.md, METRIC_LEDGER.md, CONSOLIDATED_RESULTS.md, INSIGHTS.md / insights_matrix.md, audit/wave288-p1-honest-progress-summary.md) for any `(1 − cos)` occurrences or other cosine-formula inconsistencies. Apply ADDITIVE edits per Wave 268 strict-clean rule.
**Reference:** `docs/audit/wave293-p1-locate-sign.md` §6 (out-of-scope docs); `docs/audit/wave293-p3-fix-applied.md` §5 (P4 next-pass candidates); `adaptive_reflow/schedule/cosine.py:227` (code source of truth).

---

## 1. Per-doc check status

### 1.1 Docs flagged by Wave 293 P1 §6 / P3 §5 (wrong-sign occurrences)

| File | Line | Pre-fix formula | Status | Action taken |
|---|---:|---|---|---|
| `docs/tables/tbl3-state-machines.md` | 8 | `(1 − cos(π·r/(L−1)))` | WRONG SIGN | **FIXED** — flipped to `(1 + cos(π·r/(L−1)))` |
| `docs/adr/0013-posterior-selection-drives-algorithm.md` | 151 | `(1 - cos(pi * r / (L - 1)))` | WRONG SIGN | **FIXED** — flipped to `(1 + cos(pi * r / (L - 1)))` (prose on lines 153-157 already described the correct "n_cap high at small r" direction; the formula was the only inconsistent element, and after the flip formula + prose are now internally consistent) |
| `docs/INSIGHTS.md` | 44 | `(1 - cos(pi * r / (L - 1)))` | WRONG SIGN | **FIXED** — flipped to `(1 + cos(pi * r / (L - 1)))` |

### 1.2 Docs from the task list

| File | Cosine-formula occurrence? | Status | Notes |
|---|---|---|---|
| `docs/STRATEGY_FRAMEWORK_SCOPE.md` | No formula | CLEAN | 5 occurrences of "cost" (substring of "cos") are unrelated prose; no `cos(...)`, no `n_cap` formula |
| `docs/ARCHITECTURE.md` | No formula | CLEAN | Only references to `CosineScheduleConfig`, `CosineScheduleSampler`, `CosineAnnealScheduler`, `CosineScheduleSample`, `cosine.py` (the source file); no inline closed-form `n_cap = ...` |
| `docs/TESTING_STRATEGY.md` | No formula | CLEAN | Single occurrence of "cost regression" (unrelated prose); no `cos(...)`, no `n_cap` formula |
| `docs/METRIC_LEDGER.md` | No formula | CLEAN | 23 rows of cosine-related claims (CLM-005, CLM-018, CLM-057, CLM-058, CLM-062, CLM-070, SWEEP286-*, SWEEP291-*, INSIGHT-4, INSIGHT-7.16, R5b) but NO inline `(1 - cos)` / `(1 + cos)` formula; all refer to cosine by name or reference the (1+cos) closed form in the CLM-005 evidence text, which itself was fixed by Wave 293 P3 §2.2 |
| `docs/CONSOLIDATED_RESULTS.md` | No formula | CLEAN | No `(1 - cos)` or `cos(pi * r / ...)` matches in the 8282-line file; cosine-related references are all by name (`n_cap = constant`, `cosine-anneal`, etc.) |
| `docs/INSIGHTS.md` | Yes — line 44 | FIXED | Single wrong-sign occurrence; all other cosine references in INSIGHTS.md are by name or qualitative prose |
| `docs/insights_matrix.md` | Does not exist (file is `docs/INSIGHTS.md`) | N/A | Only one insights file in repo; checked |
| `docs/audit/wave288-p1-honest-progress-summary.md` | Yes — line 326 | DENOMINATOR BUG (out of scope) | Formula `(1 + cos(pi * r / cycle_length))` is SIGN-CORRECT but uses `cycle_length` instead of `(cycle_length - 1)` per `u_r = r / (L - 1)` at `cosine.py:219`. NOT fixed in this P4 pass (P3 §5 flagged this as Priority 2 denominator-fix pass, separate from sign-flip pass). Documented here for downstream tracking. |

### 1.3 Denominator-bug occurrences flagged by Wave 293 P3 §5 (out of scope for P4 sign-fix)

| File | Lines | Pre-fix denominator | Notes |
|---|---:|---|---|
| `docs/audit/wave292-p2-config-genealogy.md` | 45, 226, 338 | `cos(pi * r / cycle_length)` | SIGN-CORRECT; denominator bug only |
| `docs/audit/scheduler-per-cell-summary.md` | 24, 52 | `cos(pi * r / cycle_length)` | SIGN-CORRECT; denominator bug only |
| `docs/audit/wave288-p1-honest-progress-summary.md` | 326 | `cos(pi * r / cycle_length)` | SIGN-CORRECT; denominator bug only |

All 6 denominator-bug occurrences are SIGN-CORRECT (`(1 + cos)`) and the sign-flip in P3 / P4 made them MORE consistent with the code direction (anneal DOWN). The remaining denominator mismatch (`cycle_length` vs `(cycle_length - 1)`) is a separate fix category and is flagged here for a future Wave 293 P5 / Wave 294 P1 pass per P3 §5 Priority 2.

### 1.4 Other docs with cosine formula occurrences (not in P1 §6 / P3 §5 scope)

| File | Lines | Status | Notes |
|---|---:|---|---|
| `docs/sequential-protocol.md` | 85, 86, 87, 95, 96 | INTERNALLY CONSISTENT (with old wrong formula) | Section §2 worked example uses `(1 - cos)` formula throughout, with table values computed from `(1 - cos)` and prose saying "cosine starts at its minimum and climbs to n_max". Internally consistent but inconsistent with actual code direction (actual code anneals DOWN `n_max → n_min`). Per Wave 268 strict-clean rule, NOT modified in this P4 pass (would require rewriting table values + prose to fix direction; not an additive fix). Flagged for Wave 294 P2 follow-up. |
| `docs/drafts/paper-flat-flattened.md:80` | 80 | DIFFERENT MATHEMATICAL OBJECT | `α = 0.5 · (1 − cos(π · progress))` is the HandoffSequentialScheduler blending weight (runs 0 → 1 across slot boundaries); the `(1 - cos)` form is CORRECT for that purpose per Wave 293 P1 §6 / P3 §5 item 8 |
| `docs/drafts/paper-flat-flattened.md:200` | 200 | QUOTED PAPER CLAIM (intentional) | Inside Wave 292 P3 §3.1 MISMATCH-HIGH-1 box; the box recommends the (1+cos) flip; the quoted formula inside the box is the pre-fix paper claim, kept verbatim as part of the audit narrative per Wave 293 P3 §5 item 9 |
| `docs/audit/wave292-p3-crosscheck.md` | 64, 81, 131, 155, 359 | AUDIT NARRATIVE (intentional) | These occurrences quote either the paper's WRONG claim inside the MISMATCH-HIGH-1 box or describe the (1−cos) → (1+cos) flip direction; NOT bugs and should NOT be edited per Wave 293 P3 §5 item 7 |
| `docs/audit/wave293-p1-locate-sign.md` + `wave293-p2-verify-direction.md` + `wave293-p3-fix-applied.md` | (all) | AUDIT NARRATIVE (intentional) | The audit docs themselves intentionally quote the wrong paper claim as part of the audit narrative; NOT touched per Wave 293 P3 §5 item 10 |
| `docs/ARCHIVE/algorithm-uplift/algorithm-uplift-plans.md` | 579, 1159 | ARCHIVE (historical record) | ARCHIVE directory; not load-bearing; left untouched per archive-do-not-edit norm |

---

## 2. Files modified in P4

| File | Lines changed | Type |
|---|---:|---|
| `docs/tables/tbl3-state-machines.md` | 1 | Sign-flip (`(1 − cos)` → `(1 + cos)`) |
| `docs/adr/0013-posterior-selection-drives-algorithm.md` | 1 | Sign-flip (`(1 - cos)` → `(1 + cos)`) |
| `docs/INSIGHTS.md` | 1 | Sign-flip (`(1 - cos)` → `(1 + cos)`) |

**Total:** 3 files modified, 3 line edits (one per wrong-sign occurrence flagged in Wave 293 P3 §5).

---

## 3. Verification results

### 3.1 D.4 regression vectors

```
$ python -m pytest -q tests/test_d4_regression_vectors.py
... 30 passed, 3 warnings in 1.02s
```

* **D.4:** **30/30 PASS** (30 passed in 1.02s; 3 deprecation warnings are pre-existing and unrelated to this edit — same as P3).
* **Why preserved:** No edits to framework internals. Doc-only edits cannot affect runtime behavior.

### 3.2 Ruff

```
$ ruff check .
... 13 errors in examples/01_quickstart.ipynb ...
Found 13 errors.
```

* **Ruff state:** 13 pre-existing errors, ALL in `examples/01_quickstart.ipynb` (E402 module-level import + I001 import-order issues in a Jupyter notebook cell).
* **Why preserved:** Doc edits (markdown text flips) do not affect Python linting. None of the 3 modified files (`.md`) are ruff-tracked.
* **Status:** PASS (state unchanged from pre-workspace baseline; identical to P3 §3.2 result).

### 3.3 MkDocs strict build

```
$ rm -rf site && mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 19.68 seconds
```

* **MkDocs:** **0 warnings** in strict mode (no broken-link cross-references; no broken-anchor IDs).
* **Why preserved:** All section header slugs are unchanged. The 3 sign-flip edits are inside inline code formulas (`(1 − cos(...))` → `(1 + cos(...))`) and do not affect link integrity.

---

## 4. Invariants — all preserved

| Invariant | Status |
|---|---|
| D.4 30/30 PASS | YES (30 passed in 1.02s) |
| claims no drift | YES (CLM-005 was already fixed in P3 §2.2; P4 edits to INSIGHTS.md:44, ADR-0013:151, tbl3-state-machines.md:8 align the "secondary docs" cosine-formula claims with the P3-fixed primary claim and with `cosine.py:227` code behavior) |
| ruff 0 | YES unchanged (13 pre-existing errors in `examples/01_quickstart.ipynb` only; doc edits do not affect ruff) |
| mkdocs 0 warnings | YES (strict build clean) |
| vendored NOT touched | YES (no edits to `tools/run_sota_cifar_experiment.py`, `tools/compute_cifar_fid.py`, `adaptive_reflow/adapters/rectified_flow_cifar.py`, or any framework source) |
| framework NOT touched | YES (no edits to `adaptive_reflow/*.py`; no edits to `tests/*.py`) |

---

## 5. Direction-of-annealing — final reconciliation

After Wave 293 P3 + P4:

* **Code behavior (unchanged):** `n_cap = n_min + (n_max - n_min) * (1 + cos(π · r / (L − 1))) / 2` anneals DOWN `n_max → n_min` (high at start, low at end). This matches the empirical test (`r=0` → `n_cap=n_max`, `r=L-1` → `n_cap=n_min`).
* **Paper text (P3 + P4 all flipped):** all 10 occurrences across `paper-flat-flattened.md` (1), `CLAIMS.md` (1), `schedule-theory.md` (4), `wave292-final.md` (1), `INSIGHTS.md` (1), `adr/0013-...` (1), `tables/tbl3-state-machines.md` (1) now read `(1 + cos(...))` (anneal DOWN), matching the code.
* **ADR-0013 prose at lines 153-157** ("places `n_cap` high when `r` is small... places `n_cap` low when `r` is large"): now INTERNALLY CONSISTENT with the formula at line 157 (previously the prose and formula were internally inconsistent — prose said n_cap high at small r but `(1 - cos)` formula put n_cap LOW at small r; both are now consistent after the flip).
* **sequential-protocol.md §2 worked example (lines 50, 85-87, 95-96):** STILL INCONSISTENT with code (entire section uses (1-cos) formula AND table values with that formula; internally consistent within the section but inconsistent with the actual code direction). Not fixed in P4 (Wave 268 strict-clean rule: would require rewriting table values + prose to fix direction; not an additive fix). Flagged for Wave 294 P2.

---

## 6. Out-of-scope items (for Wave 293 P5 / Wave 294 follow-up)

Per Wave 293 P3 §5 (Priority 2 denominator-fix pass) + Wave 293 P4 §1.4 (additional items discovered in P4 audit):

1. **Denominator-bug fix (6 occurrences):** `docs/audit/wave292-p2-config-genealogy.md:45, 226, 338` + `docs/audit/scheduler-per-cell-summary.md:24, 52` + `docs/audit/wave288-p1-honest-progress-summary.md:326` — change `cos(pi * r / cycle_length)` to `cos(pi * r / (cycle_length - 1))`. SIGN IS CORRECT; only denominator is wrong.
2. **sequential-protocol.md §2 worked example rewrite:** lines 50, 85-87, 95-96 currently use `(1 - cos)` formula with internally-consistent (but code-inconsistent) table values and prose. Requires rewriting table values + prose to flip the direction; NOT additive; needs separate Wave pass.
3. **`docs/ARCHIVE/algorithm-uplift/algorithm-uplift-plans.md:579, 1159`:** historical record of `n_cap(r) = n_min + (n_max - n_min) * (1 - cos(πr/(L-1))) / 2`. ARCHIVE directory; historical record; no action needed unless archive is republished.

---

## 7. Audit metadata

* **Wave:** 293 P4
* **Mode:** paper-edit additive pass (sign-flip ONLY; no replacement of surrounding claim text)
* **Files modified:** 3 (INSIGHTS.md, adr/0013-posterior-selection-drives-algorithm.md, tables/tbl3-state-machines.md)
* **Lines changed:** 3 (one per wrong-sign occurrence)
* **Docs checked (read-only):** 7 from task list + 3 from P3 §5 + 3 from P3 §5 denominator-flag + 6 additional (sequential-protocol.md, drafts/paper-flat-flattened.md, audit/wave292-p3-crosscheck.md, audit/wave293-p*.md, ARCHIVE/algorithm-uplift/algorithm-uplift-plans.md) = **19 docs total audited**
* **Docs with additional wrong-sign fixes:** 3 (INSIGHTS.md, adr/0013-..., tbl3-state-machines.md)
* **Fix direction:** `fix_paper` (per Wave 293 P2 §7)
* **Source of truth:** `code` (per Wave 293 P2 §6 — `adaptive_reflow/schedule/cosine.py:227` is the canonical formula)
* **Invariants:** D.4 30/30 PASS; claims no drift (CLM-005 + secondary claims now all align with code direction); ruff state unchanged; mkdocs strict 0 warnings; vendored NOT touched; framework NOT touched.