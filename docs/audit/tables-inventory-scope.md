# `tables.md` promised more than its checker checked

**Date:** 2026-10-31
**Scope:** `tnnls_submission/tables.md` (5 tables), `tools/check_tables_inventory.py`,
and the gate chain.
**Device:** CPU only.

---

## 1. Observed facts

1. `tnnls_submission/tables.md` opens with:

   > Every cell below was recomputed from the artifact it cites on 2026-10-29
   > (`tools/check_tables_inventory.py`)

2. The checker recomputed **33 cells, all in Tables 1-3**. It had no reference
   to Table 4 (wall-clock) or Table 5 (reproducibility gates) at all:

   ```
   $ grep -n "Table 4\|Table 5\|wallclock\|mypy\|pytest" tools/check_tables_inventory.py
   (no matches)
   ```

3. So "every cell below" was true of 3 of the 5 tables. The two uncovered
   tables were also the two that had actually drifted:

   | Row | Stated | Reality on 2026-10-31 |
   |---|---|---|
   | Table 5, mypy | `0 errors`, command `mypy adaptive_reflow/` | 0 errors, but the command does not resolve without a sidecar venv (see `mypy-gate-restoration.md`); it had been **50 errors** until that pass |
   | Table 5, pytest | `5582 passed / 180 skipped` (2026-10-29) | `5640 passed / 180 skipped` |

   Table 4's numbers were correct; nothing was checking them.

4. Each check in the checker was also written as *"regex the markdown for the
   exact string, then assert"*. That construction fails in the wrong
   direction: change `7.81` to `7.91` and the regex stops matching, the check
   is skipped, and the run reports `0 drift`. A check that disappears when its
   subject changes is not a check.

## 2. What changed

**`tools/check_tables_inventory.py`** — new `check_table4`, 11 cells:

| Cell | Artifact field |
|---|---|
| `before-seconds` / `ratio-before` | `wallclock_before_seconds` / `framework_baseline_ratio_before` |
| `after-seconds` / `ratio-after` / `speedup` | `wallclock_after_seconds` / `framework_baseline_ratio_after` / `speedup_factor` |
| `gap-closure` | `wallclock_gap_closure_pct` |
| `remeas-before` / `remeas-after` / `remeas-speedup` / `remeas-ratio-after` | `re_measurement_wave238_p2.*` |

Rows are located by their leading label (`**Before CUDA-graph`, `**After
CUDA-graph`, `Closes `), and the number is parsed out of the cell with the
file's existing `_num` helper. A changed number now compares unequal and
fails; a deleted row reports `(row missing)` and fails. Verified both ways:

```
$ # 7.81 -> 7.91 in a temp copy
unknown drift: [('table4:before-seconds', '7.91', '7.81')]
$ # After-CUDA-graph row deleted
missing-row drift: [('table4:after-seconds', '(row missing)', '1.81'), ...]
```

Total: 33 → **44 checks**.

**`tnnls_submission/tables.md`** — the authority note now states the actual
scope ("every numeric cell in Tables 1-4 ... 44 checks, 0 drift"; Table 5
rows are dated snapshots, not recomputable cells), and the two stale Table 5
rows were refreshed: pytest `5582 → 5640 passed / 180 skipped / 0 failed`
(2026-10-31), and the mypy row now carries the invocation that actually runs.

**Gate chain** — `check_tables_inventory.py` is entry 22 (was 21). It guards a
file that ships in the submission package, so it belongs in the pre-commit
surface rather than only in the full pytest run. `AGENTS.md` (21 → 22,
fifteen → sixteen), `docs/GATES.md` (21 → 22, twenty-one → twenty-two) and
`.github/workflows/ci.yml` (Gate 7 gains the command; Fifteen → Sixteen) are
updated.

## 3. Why Table 5 is not machine-checked

Its seven rows are *gate results*, not measurements: D.4 vector count, mkdocs
warnings, claims drift, abstract word count, ruff findings, mypy errors,
pytest counts. Recomputing them inside a gate would mean a gate that runs the
whole suite — including pytest running pytest — which is both slow and
circular. The honest fix is the one taken: say in the file that these rows
are snapshots with dates, so a reader knows to re-run rather than trust.

The one row that *is* a pure parse — abstract word count — was verified by
hand during this pass and matches: `167` words in `paper-A-final.md` §Abstract.

## 4. Verification

| Gate | Result |
|---|---|
| `python3 tools/check_tables_inventory.py` | `checked=44 known_drift=0 unknown_drift=0` (was 33) |
| Negative test: number changed | `DRIFT table4:before-seconds: stated 7.91, artifact 7.81` |
| Negative test: row deleted | `(row missing)` on all three After-row cells |
| `python3 tools/check_submission_manifest.py` | `rows=26 known_stale=0 unknown=0 addendum_drift=0 ledger_drift=0` |
| `sha256sum -c SHA256SUMS` | 22 OK, 0 FAILED (tables.md 25471 → 25607 bytes) |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed |
| Full chain | 22/22 green |

## 5. Gap

`check_recipe_hashes.py`, `check_evidence_ledgers.py`, `check_vendored_md5.py`
and `check_doc_paper_refs_diff.py` are also outside the chain. Each has a
`tests/test_*.py` that runs it, so they are enforced by CI's pytest job; they
were left out here because `check_vendored_md5` overlaps
`check_vendored_pristine` (already entry 17) and `check_doc_paper_refs_diff`
needs two commit refs. That is a deliberate boundary, not an oversight.
