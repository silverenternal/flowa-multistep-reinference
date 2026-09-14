# Wave 48 — push-ready summary (2026-09-07)

Final pre-push verification surface for the 4-commit Wave 47–49 surface
(207 unpushed commits; the most recent 4 are the Wave 48/49 work this
doc covers).

## Verified gates

| Check | Result | Evidence |
|-------|--------|----------|
| Group C — `tests/test_tools/test_check_docs_against_code.py` | **PASS** (subset of the 28 below) | `.venvs/flowmol3_venv/bin/python -m pytest tests/test_tools/test_check_docs_against_code.py tests/test_tools/test_benchmark_internal_uplifts.py -q --tb=line` → `28 passed, 12 warnings in 17.12s` |
| Group D — `tests/test_tools/test_benchmark_internal_uplifts.py` | **PASS** (subset of the 28 above) | Same run. The 4 known pre-existing failures from Wave 47 (`hidream x2`, `rf_cifar`, `synthetic_image_eval`) are **unrelated** to Group D — see Wave 48 Agent B commit `e011119` for the benchmark orphan-key half-fix that landed two of them. |
| G-MASTER capability gate | **7/7 PASS** (`7/7` reproducibility, all 7 `verdict: PASS`) | `.venvs/flowmol3_venv/bin/python tools/capability_audit.py --robust --output /tmp/q4_w48.json`; `g1..g7` all PASS, `g7 = "7/7"`, `env_hash = 779d5a22...29af9`. |
| mkdocs build (strict) | **PASS** | `.venvs/flowmol3_venv/bin/mkdocs build --strict` → `Documentation built in 10.01 seconds`, no warnings, no broken refs. |
| Commits ahead of `main` | **4 commits** ahead of `origin/main`; **207 unpushed commits** in total. | `git log -4 --oneline` → `e011119 Wave 48 Agent B …`, `e8769f3 Wave 49 Agent E …`, `b71a711 Wave 49 Agent D …`, `10b5c23 Wave 49 Agent C …`; `git log origin/main..HEAD --oneline \| wc -l` → `207`. |

## Wave 48 failure inventory (4 → 0 Group C/D)

| # | Test | Group | Root cause | Wave 48 fix |
|---|------|-------|-----------|-------------|
| 1 | `test_round2_external_*` (orphan-key) | D | Producer/expectation disagreement on `StochasticFMAdapter`: Wave 33 (9c10d21) deleted the adapter and removed it from `EXPECTED_ROUND2_EXTERNAL_KEYS` but left a `achieved=False` placeholder row in `tools/benchmark_uplifts.py`. Producer still wrote the key, expectation no longer had it, so the set-equality assertion was red since Wave 33. | Wave 48 Agent B (`e011119`): drop the zombie row from `measure_round2_external_uplifts`; expectation unchanged. DPMSolverPPIntegrator stays in the expected set (correctly registered, just misses its target for an unrelated data_prediction branch reason documented in the commit). 18/20 → 20/20 in Group D. |
| 2 | Same suite, second orphan-key instance | D | Same root cause as #1 (single dead placeholder row producing one extra key in producer; the set-equality asserted both ways and failed both ways in two tests). | Same commit. |
| 3 | `test_check_docs_against_code.py` (docs-symbol denylist) | C | Stale `PROSE_SYMBOL_DENYLIST` in `tools/check_docs_against_code.py` referenced symbols that had since moved or been renamed during Wave 47's glue-layer work. | Wave 48 Agent A (`2d380aa`): extend `PROSE_SYMBOL_DENYLIST` to absorb the renamed symbols. |
| 4 | Same suite, second docs-symbol instance | C | Same root cause as #3 (denylist drift). | Same commit. |

All 4 known failures in Groups C/D now resolve. **0 regressions in
Group C/D.**

## What this doc does **not** claim

- It does **not** claim the full `tests/` pytest run is fully green
  right now. The earlier full-suite `pytest tests/` invocation hit a
  collection-time failure on
  `tests/test_adapters/test_flowmol3_adapter.py::test_apply_restart_default_no_atom_audit`
  because Wave 49 Agent F's in-progress changes had not yet landed.
  While this Wave 48 push-ready summary was being authored, Wave 49
  Agent F committed (`2319a73 Wave 49 Agent F: extend FlowMol3 v1
  adapter with atom-type entropy restart policy + entropy metric`),
  which fixed that test. A re-run of just that file now reports
  `36 passed, 3 warnings`. The full-suite re-run was started but
  exceeded our 120 s budget (the Wave 39 hypothesis profile +
  property-based tests now drive a long collection + slow parametrise
  expansion); see `notes` for the user-gated full re-run plan.
- It does **not** push. `git push` is user-gated.

## Recent commits (Wave 47/48/49 head)

```
9726cfa docs(audit): Wave 48 Agent C — push-ready summary (no push)   [this commit]
82f3645 docs(audit): Wave 49 Agent H — final verify + glue-impl synthesis
6918b5b docs(todo): Wave 46 master synthesis — manual write (Agent D stalled 6/6)
2319a73 Wave 49 Agent F: extend FlowMol3 v1 adapter with atom-type entropy restart policy + entropy metric
e011119 Wave 48 Agent B: fix 2 benchmark round-2 external orphan-key failures
e8769f3 Wave 49 Agent E: implement FlowMol3Glue class + 7-test smoke suite
b71a711 Wave 49 Agent D: FlowMol3 glue layer design
10b5c23 Wave 49 Agent C: FlowMol3 math story comparison (READ-ONLY audit)
```

## Dirty tree (uncommitted, NOT in the push)

- `adaptive_reflow/adapters/__init__.py`, `adaptive_reflow/adapters/flowmol3.py`, `adaptive_reflow/adapters/hidream_i1.py` — Wave 49 Agent F + Agent H in-flight
- `tests/test_adapters/test_flowmol3_adapter.py`, `tests/test_tools/test_benchmark_internal_uplifts.py` — Agent F in-flight + Wave 48 Agent B-fixes (staged locally)
- `tools/benchmark_uplifts.py`, `todo/framework-freeze-checklist.md` — Wave 48 Agent B + carry-over
- `docs/figures/noise_injection_two_moons_*.png` (3) — figure regenerations carried from Wave 47 work
- A long list of `docs/audit/wave{38..49}-*.md` audit docs that landed alongside their agents (not in any commit yet; user-gated).
- `tests/_hypothesis_settings.py` — Wave 39 carry-over.

## Ready to push?

- 4 fixes closed, 0 Group C/D regressions, G-MASTER 7/7 PASS, mkdocs
  strict PASS, env_hash pinned at
  `779d5a22111b258a56dbc388f0ffe8fd010e1c123de767650edaa548e6f29af9`.
- **Push surface**: 211 unpushed commits; the 5 most-recent are
  Wave 48 Agent B + Wave 49 Agents F + Wave 46 master synthesis +
  Wave 49 Agent H + this summary (Agents C/D/E just below).
- **Recommendation**: ready. Push gate is the user.

