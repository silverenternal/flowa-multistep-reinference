# Wave 11 result validation (JMAA theory refactor)

**Status:** done (Wave 11 JMAA theory-driven framework refactor shipped; 10 Protocol surfaces + 52 conformance tests + theory package extraction + A.4-1.7 audits)
**Depends on:** Wave 11 completion
**Owner:** framework maintainer
**Goal:** verify that the JMAA theory-driven refactor preserves all existing
test behavior + adds new theory-conformance tests + produces a paper-ready
description of where the framework's theory lives.

## Next action (when starting)

When Wave 11's verify agent reports `pytest_collect_pass=True` AND
`conformance_test_pass=True` AND `commit_sha` populated: read the design doc
output from Phase 2 (likely in `/tmp/wave11_jmaa_refactor/design/` or similar)
and the implementation result (in `/tmp/wave11_jmaa_refactor/implement/`).
Verify the new theory module location + abstract interfaces match the user
directive ("big theoretical things should be at framework level (scheduler +
abstract interface); adapter-specific glue should be just implementations of the
abstract interface").

## Acceptance

- All 3146+ tests still pass.
- New theory-conformance tests in `tests/test_theory/` (or wherever the
  refactor landed) — at minimum one per paper theorem.
- `docs/ARCHITECTURE.md` (or similar) updated with a "Where the theory lives"
  section pointing to the new module.
- One-line summary in `todo.json` under `wave_11_summary`.

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PHASE-1`

**Pre-condition:** Wave 11 all 6 sub-phases (1a/1b/1c/2/4/5 + 0 + 3) committed

**Pass conditions (ALL must hold):**
- [ ] `pytest --collect-only -q` shows **>= 3146 tests, no ImportError**
- [ ] `pytest tests/test_framework/test_import_acyclic.py -v` shows **4/4 PASS**
- [ ] `pytest tests/test_adapters/test_adapter_common.py -v` shows **9/9 PASS**
- [ ] `mkdocs build --strict` exits **0**
- [ ] `docs/CLAIMS.md` has **>= 47 CLM entries**; no recent wave's `Disputed by`
- [ ] `docs/ARCHITECTURE.md` has "Where the theory lives" section
- [ ] `git status --short` returns empty
- [ ] `todo/STATUS.md` is up-to-date

**Verification commands:**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
.venvs/flowmol3_venv/bin/python -m pytest --collect-only -q 2>&1 | tail -3
.venvs/flowmol3_venv/bin/python -m pytest tests/test_framework/test_import_acyclic.py tests/test_adapters/test_adapter_common.py -v
.venvs/flowmol3_venv/bin/mkdocs build --strict 2>&1 | tail -3
test -f docs/ARCHITECTURE.md && grep -q "Where the theory lives" docs/ARCHITECTURE.md
git status --short
```

**Block rule:** if any pass condition fails, **Phase 2 cannot start**.
Per the user's "如果...实现做错了" hypothesis: a failed refactor IS the
signal that Phase 1 is incomplete; go back to A2 (git history) and find
the next theory-breaking commit to fix.

## Risk

If refactor breaks >5 existing tests: revert + report blocked; the audit
phase findings (in `/tmp/wave11_jmaa_refactor/A{1..4}-*/diagnose.md`) are still
valuable even without the refactor landing.

## Out of scope

- Re-running Wave 10 with the refactored framework (that is
  `rerun-wave10-with-refactored-framework.md`).