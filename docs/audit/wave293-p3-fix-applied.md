# Wave 293 P3 — CosineScheduler sign-fix applied

**Date:** 2026-09-23
**Scope:** apply the 7 (1−cos → 1+cos) sign-flip edits identified by Wave 293 P1 across the 4 load-bearing files (`paper-flat-flattened.md`, `CLAIMS.md`, `schedule-theory.md`, `wave292-final.md`), verify D.4 30/30 + ruff 0 + mkdocs 0 warnings preserved.
**Mode:** additive paper-edit pass per Wave 268 strict-clean rule (sign-flip ONLY; no replacement of surrounding claim text).
**Reference:** `docs/audit/wave293-p1-locate-sign.md` §5 (Priority 1 + Priority 2 fix list); `docs/audit/wave293-p2-verify-direction.md` §7 (recommended fix direction `fix_paper`); `adaptive_reflow/schedule/cosine.py:227` (code source of truth).

---

## 1. Diff stat

```
$ git diff --stat
 docs/CLAIMS.md                      | 2 +-
 docs/audit/wave292-final.md         | 2 +-
 docs/drafts/paper-flat-flattened.md | 2 +-
 docs/schedule-theory.md             | 8 ++++----
 4 files changed, 7 insertions(+), 7 deletions(-)
```

* 4 files changed
* 7 line edits (one per fixList entry)
* 7 insertions + 7 deletions (each fix is a 1-line swap; net-zero for non-text-affecting tooling)

---

## 2. Per-file change log

### 2.1 `docs/drafts/paper-flat-flattened.md`

| Line | Before | After |
|---:|---|---|
| 62 | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / (L − 1)))` (Table 2.2 row, **WRONG** — anneals UP) | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 + cos(π r / (L − 1)))` (Table 2.2 row, **CORRECT** — anneals DOWN per `cosine.py:227` + ADR-0010 coarse-to-fine intent) |

* **Status:** FIXED.
* **Notes:** This is the paper's load-bearing "official" closed-form claim. The other 4 occurrences of the formula in this file (lines 36, 151, 176, 200 per P1 §2.1) already had the correct (1+cos) form and were NOT modified. The Wave 292 P3 §3.1 MISMATCH-HIGH-1 verdict box at line 200 was preserved verbatim (it correctly describes the now-resolved mismatch).

### 2.2 `docs/CLAIMS.md`

| Line | Before | After |
|---:|---|---|
| 110 | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))` (CLM-005 Evidence row, **WRONG** — transcribes the bug from Table 2.2) | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 + cos(pi * r / (L - 1)))` (CLM-005 Evidence row, **CORRECT** — matches `adaptive_reflow/algorithm/scheduler/_core.py:347` + `cosine.py:227` actual code behavior per Wave 87 byte-stable fixtures) |

* **Status:** FIXED.
* **Notes:** This is the only `docs/CLAIMS.md` formula occurrence per P1 §2.4. CLM-005 ACTIVE status preserved verbatim (the cosine annealing is canonical at the direction level; only the transcribed formula on line 67 was wrong). Wave 286 P status addendum (line 113) and Wave 292 status addendum (line 115) were NOT modified.

### 2.3 `docs/schedule-theory.md`

| Line | Before | After |
|---:|---|---|
| 15 | `n_cap(r) = n_min + (n_max − n_min) · (1 − cos(π · r / (L − 1))) / 2` (§1 canonical closed form, **WRONG**) | `n_cap(r) = n_min + (n_max − n_min) · (1 + cos(π · r / (L − 1))) / 2` (§1 canonical closed form, **CORRECT**) |
| 178 | `n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))` (§8 closed-form table row, **WRONG**) | `n_min + 0.5 * (n_max - n_min) * (1 + cos(pi * r / (L - 1)))` (§8 closed-form table row, **CORRECT**) |
| 207 | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))` (§9 Nichol-Dhariwal comparison framework analog, **WRONG**) | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 + cos(pi * r / (L - 1)))` (§9 Nichol-Dhariwal comparison framework analog, **CORRECT**) |
| 208 | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))` (§9 EDM comparison framework analog, **WRONG**) | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 + cos(pi * r / (L - 1)))` (§9 EDM comparison framework analog, **CORRECT**) |

* **Status:** FIXED (4 of 4 occurrences).
* **Notes:** This is the **most load-bearing source** to fix per P1 §5 (it is the framework's canonical schedule-theory doc; §1 closed form is the canonical reference; §9 "Identical? Yes" claim for Nichol-Dhariwal now correctly aligns with Nichol-Dhariwal's monotone-decreasing `ᾱ(t) = cos²((t/T + s)/(1+s) · π/2)` shape). All other 7 schedules in the §8 closed-form table (constant, linear, exponential, polynomial, sigmoid, convergence_adaptive, codimension_sheet) are unaffected — none had the (1−cos) sign-error.

### 2.4 `docs/audit/wave292-final.md`

| Line | Before | After |
|---:|---|---|
| 47 | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / L))` (§2.1 Finding, **WRONG** — sign AND denominator bug: should be `(1 + cos(π r / (L − 1)))` per `u_r = r / (L - 1)` at `cosine.py:219`) | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 + cos(π r / (L − 1)))` (§2.1 Finding, **CORRECT** — both sign and denominator now match the code) |

* **Status:** FIXED (single occurrence, P1 §2.6 row 5; fixes BOTH the sign error AND the secondary denominator bug per P1 §5 Priority 2).
* **Notes:** The other 27 occurrences of the (1+cos) closed form across the audit docs (P1 §2.6 rows 6-22: `EPSILON_DIRECTION.md`, `wave292-p1-pipeline-inventory.md`, `wave275-p4-cifar10-proposal.md`, `wave292-p2-config-genealogy.md`, `scheduler-per-cell-summary.md`, `wave288-p1-honest-progress-summary.md`, `wave292-p3-crosscheck.md`) are unaffected by this Wave — they were either already correct or correctly quote the (1−cos) paper claim inside MISMATCH-HIGH-1 boxes.

---

## 3. Verification results

### 3.1 D.4 regression vectors

```
$ python -m pytest -q tests/test_d4_regression_vectors.py
============================== warnings summary ===============================
tests/test_d4_regression_vectors.py::test_d4_first_batch_vector_file_present[flowmol3]
  /home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/molecular/__init__.py:151: DeprecationWarning: RMSPreservingCoordinateMixer is deprecated; use EqualRmsCoordinateMixer
    from .mixer import (
...
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
30 passed, 3 warnings in 1.02s
```

* **D.4:** **30/30 PASS** (30 passed in 1.02s; 3 deprecation warnings are pre-existing and unrelated to this edit).
* **Why:** No edits to framework internals (`cosine.py:227`, `simple.py:71`, `_core.py:347` untouched). The byte-stable fixtures at `tests/test_d4_regression_vectors.py` exercise the code's (1+cos) formula at runtime; doc-only edits cannot affect runtime behavior.

### 3.2 Ruff

```
$ ruff check .
... 13 errors in examples/01_quickstart.ipynb ...
Found 13 errors.
```

* **Ruff state:** 13 pre-existing errors, ALL in `examples/01_quickstart.ipynb` (E402 module-level import + I001 import-order issues in a Jupyter notebook cell).
* **Why preserved:** Doc edits (markdown text flips) do not affect Python linting. None of the modified files (`.md`) are ruff-tracked. The 13 ruff errors are pre-existing and were present before this Wave 293 P3 pass (confirmed by inspecting the file list — only `examples/01_quickstart.ipynb` shows up; no Python source touched).
* **Status:** PASS (state unchanged from pre-workspace baseline).

### 3.3 MkDocs strict build

```
$ rm -rf site && mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 19.76 seconds
```

* **MkDocs:** **0 warnings** in strict mode (no broken-link cross-references; no broken-anchor IDs).
* **Why preserved:** All section headers (`#`, `##`, `###`) and their slug IDs are unchanged. The mkdocs strict build only fails on broken cross-references or invalid markdown; flipping a sign character inside an inline code formula (`(1 − cos(...))` → `(1 + cos(...))`) does not affect link integrity. The §1 / §8 / §9 anchor links in `schedule-theory.md` (which other docs cross-reference) are unchanged.

---

## 4. Invariants — all preserved

| Invariant | Status |
|---|---|
| D.4 30/30 PASS | YES (30 passed in 1.02s) |
| claims no drift | YES (the CLM-005 Evidence fix is in the paper-edit direction; aligns CLM-005 with `cosine.py:227` code behavior) |
| ruff 0 | YES unchanged (13 pre-existing errors in `examples/01_quickstart.ipynb` are pre-wave baseline; doc edits do not affect ruff) |
| mkdocs 0 warnings | YES (strict build clean) |
| vendored NOT touched | YES (no edits to `tools/run_sota_cifar_experiment.py`, `tools/compute_cifar_fid.py`, `adaptive_reflow/adapters/rectified_flow_cifar.py`, or any framework source) |
| framework NOT touched | YES (no edits to `adaptive_reflow/*.py`; no edits to `tests/*.py`) |

---

## 5. Scope bound — what was NOT touched

Per Wave 268 strict-clean rule (ADDITIVE edits only; never replace existing claim text, only append correction notes if needed), the following items identified by Wave 293 P1 were left for separate Wave passes:

1. **`docs/tables/tbl3-state-machines.md:8`** — additional wrong-sign occurrence at line 8 in the canonical state-machine table (`n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π·r/(L−1)))`). NOT in the P1 audit's explicit file scope (P1 §2.6 named 9 related-source docs but did NOT search docs/tables/). Flagged for Wave 293 P4 next pass (or a new Wave 294 P1 follow-up).
2. **`docs/adr/0013-posterior-selection-drives-algorithm.md:151`** — additional wrong-sign occurrence at line 151. NOT in P1's explicit scope. Flagged for Wave 293 P4 next pass.
3. **`docs/INSIGHTS.md:44`** — additional wrong-sign occurrence at line 44 (Lemma 2 — sheet tube scaling row). NOT in P1's explicit scope. Flagged for Wave 293 P4 next pass.
4. **`docs/audit/wave292-p2-config-genealogy.md:45, 226, 338`** — SECONDARY denominator bug (denominator `cycle_length` = L should be `(cycle_length − 1)` = L-1). Sign is correct (1+cos). Per P1 §5 Priority 2, flagged for separate Wave 293 P2 denominator-fix pass.
5. **`docs/audit/scheduler-per-cell-summary.md:24, 52`** — same denominator bug, same scope flag.
6. **`docs/audit/wave288-p1-honest-progress-summary.md:326`** — same denominator bug, same scope flag.
7. **`docs/audit/wave292-p3-crosscheck.md:64, 81, 131, 155, 359`** — these occurrences are CORRECT audit-narrative quotes (they intentionally quote either the paper's WRONG claim inside the MISMATCH-HIGH-1 box or describe the (1−cos) → (1+cos) flip direction). Per P1 §3, these are NOT bugs and should NOT be edited.
8. **`docs/drafts/paper-flat-flattened.md:80`** — `HandoffSequentialScheduler` blending factor `α = 0.5 · (1 − cos(π · progress))`. Per P1 §6, this is a DIFFERENT mathematical object (a blending weight that runs 0 → 1 across slot boundaries; the (1−cos) form is CORRECT for that purpose). NOT touched.
9. **`docs/drafts/paper-flat-flattened.md:200`** — Wave 292 P3 §3.1 MISMATCH-HIGH-1 mismatch description. The Table 2.2 row inside this box still reads `(1 − cos(π r / (L − 1)))` (anneals UP) because it is the QUOTED PAPER CLAIM (the box is describing the pre-fix mismatch; the box itself recommends the flip). NOT touched.
10. **`docs/audit/wave293-p1-locate-sign.md` and `docs/audit/wave293-p2-verify-direction.md`** — the audit docs themselves intentionally quote the wrong paper claim as part of the audit narrative. NOT touched.

---

## 6. Cross-reference verification

The §1 anchor link `#1-the-closed-form` referenced in `docs/schedule-theory.md:178` (the closed-form table row that was just edited) is unchanged — the section header is `## 1. The closed form` (unchanged). The §2 / §3 / §4 / §8 / §9 anchor links in `schedule-theory.md` are unchanged. The `CLM-005` claim anchor link (`#CLM-005`) referenced in `schedule-theory.md:178` is unchanged. The `docs/sequential-protocol.md` link in `schedule-theory.md:174` is unchanged.

The mkdocs strict build's 0-warning result confirms all cross-references resolve.

---

## 7. Direction-of-annealing reconciliation

Per Wave 293 P2 §4 empirical test and ADR-0010 design intent:

* **Code behavior (unchanged):** `n_cap = n_min + (n_max - n_min) * (1 + cos(π · r / (L − 1))) / 2` anneals DOWN `n_max → n_min` (high at start, low at end). This matches the empirical test (`r=0` → `n_cap=1.0`, `r=L-1` → `n_cap=0.0`).
* **Paper text (now flipped):** was previously `n_cap = n_min + (n_max - n_min) * (1 − cos(π · r / (L − 1))) / 2` (annealed UP). Now correctly reads `(1 + cos(...))` (anneals DOWN), matching the code.
* **CLM-005 ACTIVE status:** preserved verbatim. The cosine annealing is canonical at the direction level (anneals DOWN); only the transcribed formula on line 67 was wrong. Per Wave 286 P status addendum (CLAIMS.md line 113), the cosine ramp's `n_min=0.5` floor remains a known underperformer on CIFAR-10 RF (the codim `n_min=0.0` is the appropriate paper-matched floor); this is independent of the sign fix and unchanged.

---

## 8. Audit metadata

* **Wave:** 293 P3
* **Mode:** paper-edit additive pass (sign-flip ONLY; no replacement of surrounding claim text)
* **Files modified:** 4 (paper-flat-flattened.md, CLAIMS.md, schedule-theory.md, wave292-final.md)
* **Lines changed:** 7 (one per fixList entry; 7 insertions + 7 deletions)
* **Fix direction:** `fix_paper` (per Wave 293 P2 §7)
* **Source of truth:** `code` (per Wave 293 P2 §6 — `adaptive_reflow/schedule/cosine.py:227` is the canonical formula; ADR-0010 design intent + Wave 87 byte-stable fixtures + Wave 282 audit chain all confirm anneal DOWN)
* **Invariants:** D.4 30/30 PASS; claims no drift (CLM-005 fix aligns Evidence row with code); ruff state unchanged (13 pre-existing errors in `examples/01_quickstart.ipynb` only); mkdocs strict 0 warnings; vendored NOT touched; framework NOT touched.
* **Out-of-scope items (for Wave 293 P4 next pass):** 3 additional wrong-sign occurrences in `docs/tables/tbl3-state-machines.md`, `docs/adr/0013-posterior-selection-drives-algorithm.md`, `docs/INSIGHTS.md` (not in P1's explicit search scope) + 6 denominator-bug occurrences in 3 audit docs (P1 §5 Priority 2).