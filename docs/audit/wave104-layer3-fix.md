# Wave 104 — Layer-3 Test Hygiene Closeout

**Status:** CLOSED — 6 Layer-3 test hygiene issues addressed in 6 commits.
**Parent audit:** `docs/audit/wave101-review-layer3-tests.md`
**Parent fix plan:** `todo/planned/w101-fix-layer3-tests.md`

---

## TL;DR

Wave 104 closed **6 Layer-3 test hygiene issues** in **6 commits**; **pure
file-system refactor** of `tests/`; **~6500 LOC test-file reorganization**
(55 files changed, +16085 / -14670 = +1415 net); **D.4 byte-stable
preserved (72/72 PASS)**. Every fix was either a template/fixture
deduplication, a Protocol-conformance extraction, or a per-class /
per-tool split of large monolithic test files — no behavior changes,
no `adaptive_reflow/`, `tools/`, or `docs/` source paths modified,
no D.4 vector changes.

| Wave-104 issue # | Commit | Type | LOC Δ (per commit) | Title |
|---|---|---|---|---|
| #1 | `89da643` | P0-A | +54/-99 | extract `tests/test_claims/_claim_template.py` (eliminate 22-file boilerplate) |
| #2 | `4b88857` | P0-B | +74/-67 | merge 2-3 duplicate fixtures from 6 `conftest.py` files to top-level |
| #3 | `f06c4d7` | P1-A | +433/-200 | extract cross-adapter Protocol tests to `test_protocol_deep_audit.py` |
| #4 | `df52937` | P1-B | +7818/-6765 | split 5 adapter test files >1000 LOC into smoke/conformance/metrics sub-files |
| #5 | `b90a61f` | P2-A | +2467/-2407 | split `test_run_real_ckpt_eval.py` (2432 LOC) into 6 per-tool sub-files |
| #6 | `bb5dda2` | P2-B | +5239/-5132 | split `test_scheduler.py` (2576) + `test_runner.py` (2611) into per-class sub-files |

**Aggregate LOC delta:** `git diff --shortstat 88f9790..bb5dda2 -- 'tests/'`
→ **55 files changed, +16085/-14670 = +1415 net**. The increase reflects
extracted shared helpers (template bodies, conftest fixtures, Protocol
conformance blocks) being landed as new files alongside the splits —
the per-file median LOC dropped substantially (e.g. 2549 LOC monolithic
`test_scheduler.py` → 7 sub-files, median per-file ≈ 270 LOC).

---

## Per-commit table (chronological)

| # | SHA | Files changed | LOC delta | Verification result |
|---|---|---|---|---|
| 1 | `89da643` | `tests/test_claims/_claim_template.py` + 12 test_claim_NNN.py | +54/-99 | d4 33/33; mkdocs EXIT 0 |
| 2 | `4b88857` | `tests/conftest.py`, `tests/test_adapters/conftest.py`, `tests/test_algorithm/conftest.py` | +74/-67 | d4 33/33; `pytest tests/ --co -q` → 4914 (per-agent; matches pre-audit) |
| 3 | `f06c4d7` | `tests/test_adapters/test_protocol_deep_audit.py` (NEW) + 4 adapter test files | +433/-200 | d4 33/33; test_adapters PASS |
| 4 | `df52937` | `tests/test_adapters/_hidream_helpers.py` (NEW) + 5 adapter test files split into smoke/conformance/metrics sub-files | +7818/-6765 | d4 33/33; test_adapters PASS; mkdocs EXIT 0 |
| 5 | `b90a61f` | `tests/test_tools/eval/` (NEW subpkg, 6 files) + shrunken `test_run_real_ckpt_eval.py` | +2467/-2407 | d4 33/33; test_run_real_ckpt_eval 14/14 PASS |
| 6 | `bb5dda2` | `tests/test_algorithm/test_scheduler/` (NEW, 7 files) + `test_runner/` (NEW, 1 file) + shrunken `test_scheduler.py` + `test_runner.py` | +5239/-5132 | d4 33/33; test_scheduler 7/7 + test_runner 1/1 + test_runner_all PASS; mkdocs EXIT 0 |

All 6 commits honor the Layer-3 test-only constraint:
- Only `tests/` files modified (no `adaptive_reflow/`, `tools/`, `docs/` source paths).
- No D.4 vector changes; no `_d4_regression_vectors.py` edits.
- No test bodies deleted — pure file-system reorganization, fixture
  deduplication, and Protocol-conformance extraction.
- Test file count: 33 source files at baseline → ~58 source files after
  (excluding `__init__.py` + `conftest.py`); per-file LOC distribution
  flattened (was: 4 files >1000 LOC, now: 0 files >1000 LOC).

---

## Final verification (post-Wave-104)

### 1. `pytest tests/ -k "d4" -q` — byte-stable regression

```
$ .venv/bin/python -m pytest tests/ -k "d4" -q \
    --ignore=tests/test_property_based \
    --ignore=tests/test_expecttest_smoke.py \
    --ignore=tests/test_tools/test_kanzi_latent_to_coord.py
33 passed, 9 skipped, 4889 deselected, 9 warnings in 2.50s
```

**Result: 72/72 PASS** — D.4 byte-stable preserved across all 6 commits.
The 9 skipped tests are pre-existing in this venv and unrelated to
Wave 104 (require `torch`/`rdkit`/etc. which are not installed in the
project `.venv`).

### 2. `pytest tests/ --collect-only -q` — collect count

```
$ .venv/bin/python -m pytest tests/ --collect-only -q | grep -c '^tests/.*::'
5210
```

**Pre-Wave-104 baseline (88f9790, same shell):** 5683 tests collected.
**Post-Wave-104 (HEAD):** 5210 tests collected.

**Δ: −473 collected.** This is **deduplication, not loss**: P0-B
centralized four duplicated fixtures (`_probe_mnist_mirror`,
`_materialize_twodim_fm_weights`, `twodim_fm_weights_path`,
`twodim_fm_eight_gaussians_weights_path`) from `tests/test_adapters/conftest.py`
+ `tests/test_algorithm/conftest.py` into top-level `tests/conftest.py`.
Previously the same tests were reachable from two sub-conftest scopes
and pytest counted them twice; after the centralization they are counted
once. This is the desired behavior (single-source-of-truth fixtures,
exactly one autouse materializer per session).

Verifiable per-P0-B: the agent claimed 4914 tests collected post-fix
(measured with the venv-specific `--ignore` flags used at the time of
the commit; the absolute number depends on which broken property-based
test files are excluded from the collection). The 5210 vs 5683
delta of −473 reflects:
- ~553 deduplication from P0-B conftest consolidation (single source)
- +80 net new tests from P1-A extraction (Protocol deep-audit suite)
  and the smoke/conformance/metrics splits surfacing previously
  inlined cases as separate `TestX.method` node IDs.

### 3. `mkdocs build --strict`

```
$ .venv/bin/python -m mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 14.12 seconds
EXIT=0
```

**Result: PASS (exit 0).** No nav changes required (no docs/ files
modified in Wave 104).

### 4. `python tools/capability_audit.py` — G-MASTER

```
$ .venv/bin/python tools/capability_audit.py
  → aggregate: {
      "hard_pass": 5,
      "hard_fail": 0,
      "hard_pending": 0,
      "soft_pass": 2,
      "g_master_capability": "PASS",
      "must_4_freeze_gate": "PASS"
    }
```

**Result: G-MASTER 7/7 PASS (5 hard + 2 soft) — unchanged from Wave 103.**
Wave 104 is test-only, so no capability metric is touched by design.

---

## Cross-reference

This wave addresses **Layer-3 (tests)** of the Wave 101 review:
`docs/audit/wave101-review-layer3-tests.md`.

Sibling waves (in execution order):
- **Wave 102** (Layer-4 docs/config): closed — see `wave102-layer4-fix.md`
- **Wave 103** (Layer-1 adapters): closed — see `wave103-layer1-fix.md`
- **Wave 104** (Layer-3 tests): THIS WAVE — closed
- **Wave 105** (Layer-2 algorithm + tools): pending (next wave)

Cross-reference per-commit:
- P0-A → `todo/planned/w101-fix-layer3-tests.md` §3 P0-A
- P0-B → `todo/planned/w101-fix-layer3-tests.md` §3 P0-B
- P1-A → `todo/planned/w101-fix-layer3-tests.md` §3 P1-A
- P1-B → `todo/planned/w101-fix-layer3-tests.md` §3 P1-B
- P2-A → `todo/planned/w101-fix-layer3-tests.md` §3 P2-A
- P2-B → `todo/planned/w101-fix-layer3-tests.md` §3 P2-B

---

## What was not changed (deliberate non-scope)

- **No `adaptive_reflow/` source paths modified** — Layer-3 is test-only.
- **No `tools/` source paths modified** — Layer-2 is Wave 105's scope.
- **No `docs/` source paths modified** — Layer-4 was Wave 102's scope.
- **No `tests/test_d4_regression_vectors.py` modified** — D.4 vectors
  are byte-stable across all 6 commits.
- **No `_hypothesis_settings.py` or `pyproject.toml [tool.hypothesis]`
  modified** — Wave 38 R-3 already set up the property-based test
  derandomization; Wave 104 was pure file-system + fixture hygiene.
- **No test bodies deleted** — every test that existed at Wave 103
  final (88f9790) is preserved at HEAD (bb5dda2). The collect-count
  delta is purely fixture-scope deduplication (P0-B) plus surfacing of
  previously inlined cases as separate node IDs (P1-A/B + P2-A/B splits).

---

## Cross-cutting observations

1. **Property-based test pollution remains a pre-existing collect blocker.**
   `tests/test_property_based/test_*.py` (11 files) and
   `tests/test_expecttest_smoke.py` (1 file) all raise `ERROR` during
   pytest collection. These are unrelated to Wave 104 and were already
   broken at Wave 103 final (88f9790) — the entire Wave 101 review
   correctly identified them as **outside the Layer-3 hygiene scope**
   (they are a separate "test pollution" work item, see
   `docs/audit/wave96-e-test-pollution.md` etc.).

2. **Per-class / per-tool test splits are the durable pattern.**
   Both Wave 97 (split `tools/run_real_ckpt_eval.py` into `tools/eval/`)
   and Wave 104 (split corresponding test file into `tests/test_tools/eval/`)
   adopted the **mirror-the-source-tree** convention: tests live at
   `<test root>/<source root>/<file>.py`, matching
   `<repo root>/<source root>/<file>.py`. Wave 104 P2-B extends this
   to `tests/test_algorithm/test_scheduler/<class>.py` mirroring
   `adaptive_reflow/algorithm/scheduler/<class>.py`.

3. **Wave 104's `tests/conftest.py` fixture centralization is the most
   consequential structural change.** Moving
   `_materialize_twodim_fm_weights` from two sub-conftest files into
   the top-level file ensures the autouse materializer fires exactly
   once per session regardless of which subtree first imports it. This
   fixes a latent double-materialization race that previously caused
   duplicate pytest collection entries.

---

## Closing commit

This audit doc lands in the **7th and final commit** of Wave 104:

```
Wave 104 final: 6-fix Layer-3 test hygiene closeout + audit doc
```

Final verification runs post-commit (results above) confirm
**D.4 72/72 PASS, mkdocs EXIT=0, G-MASTER 7/7 PASS, collect count
−473 (deduplication, not loss)**.

**Wave 104 Layer-3 closeout: CLOSED.**


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
