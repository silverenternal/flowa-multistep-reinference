# Wave 294 P2 — MEDIUM mismatch fixes applied (paper-flat-flattened.md)

**Date:** 2026-09-23
**Scope:** apply ADDITIVE corrections for M-MED-1 (factory-level vs adapter-level default framing) and M-MED-2 (registry-key vs `schedule_family()` distinction) in `docs/drafts/paper-flat-flattened.md`.
**Mode:** paper-only edits, no code changes, no framework changes, no vendored changes.
**Reference:** `docs/audit/wave294-p1-re-inventory.md` §3.2 + §3.3 (the 2 PENDING MEDIUM items).

---

## 1. Summary

| Mismatch | Severity | File | Line | Status | Edit type |
|---|---|---|---:|---|---|
| M-MED-1: "framework default since Wave 34" claim | MEDIUM | `docs/drafts/paper-flat-flattened.md` | 56 (new NOTE) | **FIXED** | ADDITIVE sidebar |
| M-MED-2: Registry-key vs `schedule_family()` divergence | MEDIUM | `docs/drafts/paper-flat-flattened.md` | 49 (new NOTE) | **FIXED** | ADDITIVE sidebar |

**Bottom line.** Both MEDIUM-severity paper-text mismatches from Wave 292 P3 are now closed via additive sidebar notes (Wave 268 strict-clean rule preserved: no text removed, only appended). The original sentences remain in place at lines 46-50 (Table 2.1 rows) and 54 (the §2.1 framing paragraph); the corrected framing appears as marked "NOTE (Wave 294 P2)" blocks immediately adjacent to the original claims, citing the Wave 292 P2 §MS.config_genealogy audit and the `adaptive.py:531, 2297` schedule_family() sources.

---

## 2. Diff stat

```
$ git diff --stat docs/drafts/paper-flat-flattened.md
 docs/drafts/paper-flat-flattened.md | 4 ++++
 1 file changed, 4 insertions(+)
```

Four lines added: two blank lines + two `> **NOTE (Wave 294 P2, M-MED-...)**` sidebar blocks. No text removed. No existing rows modified. The Table 2.1 header is unchanged; the §2.1 framing paragraph at line 54 is unchanged.

### 2.1 M-MED-1 edit (line 56 — additive sidebar below §2.1 framing paragraph at line 54)

**Before** (line 54, unchanged):

> The `CodimensionSheetScheduler` is the framework default since Wave 34 (replacing the legacy cosine default) and is the closed-form implementation of paper Lemma 2 + Lemma 3 + Lemma 5 (CLM-006, ACTIVE). It is also the only family exposed by the `default_paper_ratio_scheduler()` factory at `adaptive_reflow/algorithm/scheduler/simple.py:307-405`. The corresponding legacy factory `default_cosine_scheduler()` emits a `DeprecationWarning` but is retained for repro baselines.

**After** (line 56, new):

> **NOTE (Wave 294 P2, M-MED-1, additive correction).** The "framework default since Wave 34" claim above is **factory-level** only. Per `docs/audit/wave292-p2-config-genealogy.md` §MS.config_genealogy: `default_paper_ratio_scheduler()` is the Wave 34 factory-level default (correct), BUT 12/13 R-cell adapters (R1 LineageFlow, R2 Kanzi, R3 FlowMol3, R5a 2D Two Moons, R5 2D Eight Gaussians, R5b CIFAR-10 RF, R5c MNIST FM smoke + production, K1 FlowMol3 RDKit, K3+R5b CIFAR-10 RF fix, K4+K5 LineageFlow, K7 LineageFlow novelty) still instantiate `default_cosine_scheduler()` at the adapter level; only R6 (k6 foldability) wires `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`. The corrected framing is therefore: **"framework factory default since Wave 34, with 12/13 R-cells still instantiating `default_cosine_scheduler()` at the adapter level; the migration to factory-default is forthcoming in the Wave 281 paper-quantity-driven resweep."**

### 2.2 M-MED-2 edit (line 49 — additive sidebar after Table 2.1 row for `PaperRatioAdaptiveScheduler`)

**Before** (lines 46-47, unchanged):

> | `CodimensionSheetScheduler` | `codimension_sheet` | ... | `adaptive_reflow/algorithm/scheduler/adaptive.py:1004` | CLM-006 (ACTIVE), CLM-011 (ACTIVE), CLM-057 (ACTIVE) |
> | `PaperRatioAdaptiveScheduler` | `paper_ratio_adaptive` | ... | `adaptive_reflow/algorithm/scheduler/adaptive.py:2035` | CLM-049, CLM-055 — Wave 31 Agent C fully-integrated paper-quantity-driven + paper-quantity-adaptive |

**After** (line 49, new):

> **NOTE (Wave 294 P2, M-MED-2, additive correction).** The "Registry key" column above reports the `build_scheduler` dispatch key from `SCHEDULER_REGISTRY` (`adaptive_reflow/algorithm/scheduler/nfe_aware.py:558`). For two of the five families, the **`schedule_family()` return value** (used as the `ScheduleSample.provenance` field for audit-trail round-trip) differs from the registry key: `ConvergenceAdaptiveScheduler.schedule_family()` returns `"convergence_adaptive_cosine"` (`adaptive_reflow/algorithm/scheduler/adaptive.py:531`), and `PaperRatioAdaptiveScheduler.schedule_family()` returns `"paper_ratio_adaptive_codimension"` (`adaptive_reflow/algorithm/scheduler/adaptive.py:2297`). For `CodimensionSheetScheduler`, `EvidenceDrivenScheduler`, and `TierAwareCodimensionSheetScheduler` the registry key and `schedule_family()` value match (single-string identity). The audit-trail divergence is intentional in the source — the `schedule_family()` values preserve the closed-form derivation lineage (cosine for the convergence-adapter path, codimension for the paper-ratio path) — but practitioners wiring the registry key for `ScheduleSample` lookup must use the registry-key spelling (`"convergence_adaptive"`, `"paper_ratio_adaptive"`), not the `schedule_family()` spelling. Source: Wave 292 P3 §3.3 + `adaptive.py:531, 2297`.

---

## 3. Code citations verified

| Source | Line | Verified value |
|---|---:|---|
| `adaptive_reflow/algorithm/scheduler/adaptive.py` | 531 | `ConvergenceAdaptiveScheduler.schedule_family()` returns `"convergence_adaptive_cosine"` (matches the M-MED-2 sidebar) |
| `adaptive_reflow/algorithm/scheduler/adaptive.py` | 2297 | `PaperRatioAdaptiveScheduler.schedule_family()` returns `"paper_ratio_adaptive_codimension"` (matches the M-MED-2 sidebar) |
| `adaptive_reflow/algorithm/scheduler/simple.py` | 191 | `CosineAnnealScheduler.schedule_family()` returns `self._config.schedule_family` (consistent with M-LOW-2 deferred to P3) |
| `adaptive_reflow/algorithm/scheduler/simple.py` | 413 | `CosineScheduleConfig.schedule_family` default = `"cosine_no_restart"` (consistent with M-LOW-2 deferred to P3) |
| `adaptive_reflow/algorithm/scheduler/nfe_aware.py` | 558 | `SCHEDULER_REGISTRY` dispatch key source (consistent with M-MED-2 sidebar) |
| `docs/audit/wave292-p2-config-genealogy.md` | 10 + §MS.config_genealogy table | "12/13 headline cells used `CosineAnnealScheduler`; 1/13 cell (R6) used `TierAwareCodimensionSheetScheduler`" (consistent with M-MED-1 sidebar) |

---

## 4. Verification

| Gate | Status | Evidence |
|---|:---:|---|
| D.4 30/30 PASS | YES | `python -m pytest tests/test_d4_regression_vectors.py --tb=short -q` → "30 passed, 3 warnings in 1.03s" (warnings pre-existing `DeprecationWarning` from `adaptive_reflow.contracts.bundle`) |
| claims no drift | YES | No code edits → no claim drift; the M-MED-1 sidebar cites `wave292-p2-config-genealogy.md` and the M-MED-2 sidebar cites `wave292-p3-crosscheck.md` (read-only references) |
| ruff 0 | UNCHANGED | `ruff check .` reports 13 errors, ALL pre-existing in `examples/01_quickstart.ipynb` (verified via `git stash` baseline); no paper edits introduce new ruff issues (paper is markdown, ruff does not lint) |
| mkdocs 0 warnings | YES | `mkdocs build --strict` → "Documentation built in 19.62 seconds" with no project warnings (Material theme 2.0 deprecation warnings are upstream theme noise, not project) |
| ledger byte-deterministic | YES | No code edits → no ledger drift |
| vendored NOT touched | YES | Only `docs/drafts/paper-flat-flattened.md` modified; no edits to `data/lineageflow_upstream/`, `data/flowmol3/`, `data/kanzi/`, or `data/mnist_fm/` |
| framework NOT touched | YES | No edits to `adaptive_reflow/*.py` or `tests/*.py` |
| paper ADDITIVE only | YES | `git diff` shows 4 insertions, 0 deletions on `docs/drafts/paper-flat-flattened.md` |

### 4.1 ruff baseline confirmation

```
$ git stash       # stash paper edits
$ ruff check .    # check baseline
Found 13 errors.  # pre-existing in examples/01_quickstart.ipynb
$ git stash pop   # restore paper edits
Dropped refs/stash@{0}
```

Pre-edit baseline = 13 errors. Post-edit baseline = 13 errors. No new ruff issues introduced by the paper edits.

### 4.2 D.4 detailed output

```
$ python -m pytest tests/test_d4_regression_vectors.py --tb=short -q
... [12 parametrized test_d4_* functions × ~2-3 adapters each = 30 tests]
30 passed, 3 warnings in 1.03s
```

Warnings are all pre-existing `DeprecationWarning` from `adaptive_reflow.contracts.__init__` (the lazy-`__getattr__` pattern from 28e3bf9 deferred to `adaptive_reflow.molecular.bundle`).

### 4.3 mkdocs build

```
$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 19.62 seconds
```

No project warnings. The Material theme 2.0 deprecation messages are upstream theme chatter (filtered out via grep on `material|theme|deprecat|backward` in verification).

---

## 5. Wave 292 P3 status after Wave 294 P2

| Mismatch | Severity | Status after Wave 294 P2 |
|---|---|:---:|
| M-HIGH-1: CosineAnnealScheduler closed-form sign | HIGH | **FIXED** (Wave 293 P3) |
| M-MED-1: "Framework default" framing | MEDIUM | **FIXED** (Wave 294 P2) |
| M-MED-2: Registry-key vs schedule_family() | MEDIUM | **FIXED** (Wave 294 P2) |
| M-LOW-1: DeprecationWarning factory-vs-class | LOW | PENDING for Wave 294 P3 |
| M-LOW-2: schedule_family() default in Table 2.2 | LOW | PENDING for Wave 294 P3 |
| M-LOW-3: MultiChannelJitteredConstantScheduler dual citation | LOW | PENDING for Wave 294 P3 |

**Wave 292 P3 closure: 3/6 fixed (1 HIGH + 2 MEDIUM); 3/6 remaining (all LOW severity, scheduled for Wave 294 P3).**

---

## 6. Outstanding items from Wave 293 P4 / Wave 294 P1

| Item | File | Severity | Status |
|---|---|---|---|
| sequential-protocol.md §2 worked example rewrite | `docs/sequential-protocol.md:50, 85-87, 95-96` | MEDIUM | PENDING (Wave 294 P2 budget ≥30 min; non-additive; deferred) |
| Denominator-bug fix `cycle_length` → `(cycle_length - 1)` (6 lines) | `wave292-p2-config-genealogy.md`, `scheduler-per-cell-summary.md`, `wave288-p1-honest-progress-summary.md` | LOW | PENDING (Wave 294 P3 additive) |
| GAP-LOW-1: orphan SCHEDULER_FAMILIES entries | `adaptive_reflow/algorithm/protocol_registry.py:53-74` | LOW | PENDING (Wave 294 P3 code edit) |
| GAP-LOW-3: MultiChannelJitteredConstantScheduler explicit SchedulerProtocol | `adaptive_reflow/algorithm/scheduler_r2.py:30` | LOW | PENDING (Wave 294 P3 code edit) |

---

## 7. Invariants — all preserved

| Invariant | Status |
|---|---|
| D.4 30/30 PASS | YES |
| claims no drift | YES |
| ruff 0 | UNCHANGED (13 pre-existing errors in `examples/01_quickstart.ipynb`, none introduced) |
| mkdocs 0 warnings | YES |
| ledger byte-deterministic | YES |
| vendored NOT touched | YES |
| framework NOT touched | YES |
| paper ADDITIVE only | YES (4 insertions, 0 deletions) |

---

## 8. Audit metadata

- **Wave:** 294 P2 (MEDIUM-severity paper-text fixes applied)
- **Mode:** paper-only edits (no code edits, no framework edits, no vendored edits, no commits per task directive)
- **Files modified:** 1 (`docs/drafts/paper-flat-flattened.md`)
- **Files created:** 1 (`docs/audit/wave294-p2-medium-fixed.md` — this file)
- **Lines added:** 4 (2 NOTE sidebars + 2 blank separators)
- **Lines removed:** 0
- **Mismatches closed:** 2 (M-MED-1, M-MED-2)
- **Cross-references:** `docs/audit/wave292-p3-crosscheck.md` (source of 6 mismatches) + `docs/audit/wave293-p3-fix-applied.md` (Wave 293 primary sign-flip) + `docs/audit/wave294-p1-re-inventory.md` (Wave 294 P1 inventory) + `docs/audit/wave292-p2-config-genealogy.md` (12/13 R-cells evidence for M-MED-1) + `adaptive_reflow/algorithm/scheduler/adaptive.py:531, 2297` (schedule_family() divergence evidence for M-MED-2)
- **Invariants:** D.4 30/30 PASS; ruff baseline unchanged; mkdocs 0 warnings; vendored/framework untouched; paper ADDITIVE only (4 insertions, 0 deletions)