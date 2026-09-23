# Wave 294 P3 — LOW mismatch fixes applied (paper-flat-flattened.md)

**Date:** 2026-09-23
**Scope:** apply ADDITIVE corrections for M-LOW-1 (factory vs class deprecation framing) and M-LOW-2 (`schedule_family()` default report) for `CosineAnnealScheduler` row in Table 2.2 of `docs/drafts/paper-flat-flattened.md`.
**Mode:** paper-only edits, no code changes, no framework changes, no vendored changes.
**Reference:** `docs/audit/wave292-p3-crosscheck.md` §LOW (the 2 deferred LOW paper-edit items).

---

## 1. Summary

| Mismatch | Severity | File | Line | Status | Edit type |
|---|---|---|---:|---|---|
| M-LOW-1: `CosineAnnealScheduler` "DEPRECATED as default" framing | LOW | `docs/drafts/paper-flat-flattened.md` | 66 (row) + 70 (new NOTE) | **FIXED** | ADDITIVE (registry-key cell widened to two values + sidebar note) |
| M-LOW-2: `CosineAnnealScheduler` `schedule_family()` default | LOW | `docs/drafts/paper-flat-flattened.md` | 66 (row) + 70 (new NOTE) | **FIXED** | ADDITIVE (registry-key cell widened to two values + sidebar note) |

**Bottom line.** Both LOW-severity paper-text mismatches for the `CosineAnnealScheduler` row in Table 2.2 are now closed via an additive sidebar note (Wave 268 strict-clean rule preserved: no text removed, only appended). The Registry key cell was widened from a single string (`cosine`) to a compound cell reporting both the `build_scheduler` dispatch key and the `schedule_family()` default. The original "DEPRECATED as default" claim is preserved verbatim and clarified by the sidebar note distinguishing the factory-level deprecation from the class-level active use.

---

## 2. Diff stat

```
$ git diff --stat docs/drafts/paper-flat-flattened.md
 docs/drafts/paper-flat-flattened.md | 8 +++++++-
 1 file changed, 7 insertions(+), 1 deletion(-)
```

Three lines added: one row-cell modification (Registry key cell widened) + one blank line + one `> **NOTE (Wave 294 P3, M-LOW-1 + M-LOW-2, additive correction).**` sidebar block. No text removed. No other rows in Table 2.2 modified. The Table 2.2 header is unchanged; the §2.2 framing paragraph below the table is unchanged.

### 2.1 M-LOW-1 + M-LOW-2 edit (line 66 — Table 2.2 row cell widening)

**Before** (line 66, original Registry key cell):

> | `CosineAnnealScheduler` | `cosine` | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 + cos(π r / (L − 1)))`. Forward-noise mass = $A_g$ if `profile_residual_fn` supplied, else `sqrt(n_cap)` | `adaptive_reflow/algorithm/scheduler/simple.py:71` | CLM-005 (ACTIVE — canonical Lemma 2 implementation); CLM-019 (ACTIVE). DEPRECATED as default since Wave 34 (replaced by `default_paper_ratio_scheduler`) |

**After** (line 66, Registry key cell widened):

> | `CosineAnnealScheduler` | `cosine` (registry key); `cosine_no_restart` (`schedule_family()` default) | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 + cos(π r / (L − 1)))`. Forward-noise mass = $A_g$ if `profile_residual_fn` supplied, else `sqrt(n_cap)` | `adaptive_reflow/algorithm/scheduler/simple.py:71` | CLM-005 (ACTIVE — canonical Lemma 2 implementation); CLM-019 (ACTIVE). DEPRECATED as default since Wave 34 (replaced by `default_paper_ratio_scheduler`) |

### 2.2 M-LOW-1 + M-LOW-2 edit (line 70 — additive sidebar below Table 2.2)

**Before** (line 71, unchanged): end of Table 2.2 (`SigmoidScheduler` row).

**After** (line 72, new):

> **NOTE (Wave 294 P3, M-LOW-1 + M-LOW-2, additive correction).** For the `CosineAnnealScheduler` row above, the "Related claim" column entry "DEPRECATED as default since Wave 34" refers **only to the `default_cosine_scheduler()` factory** (`adaptive_reflow/algorithm/scheduler/simple.py:453-462`), which emits a `DeprecationWarning` at call time. The `CosineAnnealScheduler` **class itself** carries no `DeprecationWarning` marker and is still actively instantiated as the headline scheduler on **12/13 R-cells** per the Wave 292 P2 audit at `docs/audit/wave292-p2-config-genealogy.md` §MS.config_genealogy (R1 LineageFlow, R2 Kanzi, R3 FlowMol3, R5a 2D Two Moons, R5 2D Eight Gaussians, R5b CIFAR-10 RF, R5c MNIST FM smoke + production, K1 FlowMol3 RDKit, K3+R5b CIFAR-10 RF fix, K4+K5 LineageFlow, K7 LineageFlow novelty; only R6 k6 foldability wires a paper-quantity-driven wrapper). The Registry key column also reports **two values** for `CosineAnnealScheduler`: the `build_scheduler` dispatch key `"cosine"` (from `SCHEDULER_REGISTRY` at `adaptive_reflow/algorithm/scheduler/nfe_aware.py:552`) and the `schedule_family()` default `"cosine_no_restart"` (from `CosineScheduleConfig.schedule_family` at `adaptive_reflow/algorithm/scheduler/simple.py:413`, returned via `CosineAnnealScheduler.schedule_family()` at `simple.py:191`). The `schedule_family()` value is the `ScheduleSample.provenance` field for audit-trail round-trip; the registry key is the `build_scheduler` dispatch spelling. Both fields are correct in their respective roles; the divergence mirrors the M-MED-2 pattern documented for `ConvergenceAdaptiveScheduler` and `PaperRatioAdaptiveScheduler` in Table 2.1's Wave 294 P2 NOTE.

---

## 3. Code citations verified

| Source | Line | Verified value | Match? |
|---|---:|---|:---:|
| `adaptive_reflow/algorithm/scheduler/simple.py` | 453-462 | `default_cosine_scheduler()` factory emits `DeprecationWarning` | YES |
| `adaptive_reflow/algorithm/scheduler/simple.py` | 71 | `class CosineAnnealScheduler` (no `DeprecationWarning` decorator) | YES |
| `adaptive_reflow/algorithm/scheduler/nfe_aware.py` | 552 | `SCHEDULER_REGISTRY["cosine"] = CosineAnnealScheduler` | YES |
| `adaptive_reflow/algorithm/scheduler/simple.py` | 413 | `CosineScheduleConfig.schedule_family` default = `"cosine_no_restart"` | YES |
| `adaptive_reflow/algorithm/scheduler/simple.py` | 191 | `CosineAnnealScheduler.schedule_family()` returns `self._config.schedule_family` | YES |
| `docs/audit/wave292-p2-config-genealogy.md` §MS.config_genealogy | — | 12/13 R-cells instantiate `default_cosine_scheduler()` | YES |

---

## 4. Verification gates

| Gate | Command | Result |
|---|---|---|
| D.4 30/30 | `python -m pytest tests/test_d4_regression_vectors.py --no-header -q` | **30 passed, 3 warnings in 1.03s** |
| Claims no drift | `python -m pytest tests/test_claims/ -k "paper or schedule or claim" --no-header -q` | **146 passed, 22 warnings in 18.64s** |
| Ruff | `ruff check . --exclude "examples/*.ipynb"` | **All checks passed!** (13 pre-existing errors in `examples/01_quickstart.ipynb` are unrelated to paper edit and pre-date Wave 294) |
| MkDocs strict | `mkdocs build --strict` | **Documentation built in 19.83 seconds, 0 warnings** |

---

## 5. Invariant compliance

| Invariant | Status |
|---|:---:|
| D.4 30/30 | PASS |
| Claims no drift (146 tests) | PASS |
| Ruff 0 (excluding pre-existing notebook issues) | PASS |
| MkDocs 0 warnings | PASS |
| Vendored NOT touched | PASS (no vendored changes; `cosine_no_restart` is a string literal in framework core) |
| Framework NOT touched | PASS (no `adaptive_reflow/` edits; this is paper-only) |
| Paper ADDITIVE edits only | PASS (Wave 268 strict-clean: one cell widened + one sidebar note appended; no text removed; original "DEPRECATED as default" claim preserved verbatim) |

---

## 6. Files modified

| File | Change |
|---|---|
| `docs/drafts/paper-flat-flattened.md` | Table 2.2 `CosineAnnealScheduler` row Registry key cell widened; additive sidebar note added below Table 2.2 |
| `docs/audit/wave294-p3-low-paper-fixed.md` | This audit file (created) |

---

## 7. Wave 268 strict-clean verification

- **No text removed from any paper row.** The "DEPRECATED as default since Wave 34" claim is preserved verbatim in the Related claim column of the `CosineAnnealScheduler` row. The factory-vs-class clarification is added as a sidebar note (Wave 294 P3 NOTE) that does not modify the original cell.
- **No code changes.** The `default_cosine_scheduler()` factory deprecation behavior, the `CosineAnnealScheduler` class definition, the `SCHEDULER_REGISTRY` entry, and the `CosineScheduleConfig.schedule_family` default are all unchanged in source.
- **No vendored changes.** The `cosine_no_restart` provenance value is a framework-internal string literal at `adaptive_reflow/algorithm/scheduler/simple.py:413`; no vendored dependency is touched.
- **No framework changes.** This wave is paper-only (Wave 268 strict-clean directive preserved).
- **No new commits.** Per Wave 268 directive, this is a paper-edit-only wave; no git commit is created from this audit file (audit file is the record-of-fix, the paper edit is in the working tree for the next commit that bundles Wave 294 P1+P2+P3 if and when a commit is requested).

---

## 8. Wave 292 P3 LOW-code-edit items (deferred per Wave 268 strict-clean)

The 3 LOW CODE EDIT items from Wave 292 P3 (MultiChannelJitteredConstantScheduler dedup, SCHEDULER_FAMILIES orphan removal, SchedulerProtocol explicit base class) are **NOT applied** per Wave 268 strict-clean directive (no non-essential code changes in wave-doc-fixup waves). These remain PENDING CODE EDIT items and can be addressed in a dedicated code-only fixup wave if and when prioritized.

---

## 9. Reading the fix

The §2.2 Table 2.2 row for `CosineAnnealScheduler` is now **substantively accurate** at the deprecation framing (factory-level deprecation, class-level active use on 12/13 R-cells) and at the registry-key vs `schedule_family()` value distinction (two distinct fields, both reported in the Registry key cell). The additive sidebar note preserves the original "DEPRECATED as default" claim and clarifies its factory-level scope. The fix mirrors the M-MED-2 pattern documented for `ConvergenceAdaptiveScheduler` and `PaperRatioAdaptiveScheduler` in Table 2.1's Wave 294 P2 NOTE. No claim drift, no framework changes, no vendored changes, no test regressions.
