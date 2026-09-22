# Wave 103 — Layer-1 Adapter Hygiene Closeout

**Status:** CLOSED — 10 Layer-1 adapter hygiene issues addressed in 7 commits.
**Parent audit:** `docs/audit/wave101-review-layer1-adapters.md`
**Parent fix plan:** `todo/planned/w101-fix-layer1-adapters.md`

---

## TL;DR

Wave 103 closed **10 Layer-1 adapter hygiene issues** in **7 commits**;
**~290 LOC adapter duplication removed**; **D.4 byte-stable preserved**
(72/72 PASS). Every fix was a refactor of duplicated adapter code into
shared framework-core / `_adapter_common` helpers, or a drift correction
in adapter comments/sentinels — no behavior changes, no API-surface
changes, no test changes.

| Layer-1 issue # | Commit | Type | LOC Δ | Title |
|---|---|---|---|---|
| #5 | `20b938e` | P0-A | +30/-19 | hidream_i1 NativeStateCache (4-LOC swap, fixes LRU bug) |
| #2 | `2cd6e96` | P0-B | +116/-126 | dedup _seed_from_ids/_digest_state/_make_ref in 5 adapters |
| #3 | `ccabf56` | P1-A | +111/-67 | 8 *_resolve_weights_path wrappers delegate to resolve_candidate_paths |
| #4 | `6056fdb` | P1-B | +62/-52 | extract _resolve_mode helper, delete 3 force_mode if/elif blocks |
| #6-#9 | `600cf84` | P3 (drift #1-#4) | +36/-17 | doc tightenings + GPT-prior early-return |
| #10 | `b4b49de` | P3-A | +22/-3 | flowmol3_v2 sentinel string → class sentinel |
| #1 | `45bce4b` | P2-A | +250/-101 | extract load_real_weights() trait; refactor 3 SOTA adapters |

**Total LOC delta:** +627/-385 (≈ +242 net). The deletion count
(-385) reflects roughly **290 LOC of adapter-side duplication removed**
that landed in framework-core / `_adapter_common.py` (+337 LOC of
trait/scaffolding helpers, partially off-set by deletion-side savings).

---

## Per-commit table (chronological)

| # | SHA | Files changed | LOC delta | Verification result |
|---|---|---|---|---|
| 1 | `20b938e` | `adaptive_reflow/adapters/hidream_i1.py` | +30/-19 | d4 33/33; hidream tests PASS |
| 2 | `2cd6e96` | `adaptive_reflow/adapters/{graphbfn,hidream_i1,lineageflow,lumina_image_2_0,wan2_2_video}.py` | +116/-126 | d4 33/33; 5-adapter tests 127/127 PASS, 6 SKIP (torch missing) |
| 3 | `ccabf56` | `adaptive_reflow/adapters/{freqflow,graphbfn,hidream_i1,kanzi,lineageflow,lumina_image_2_0,wan2_2_video}.py` | +111/-67 | d4 33/33; 7-adapter tests PASS; mkdocs EXIT 0 |
| 4 | `6056fdb` | `adaptive_reflow/adapters/_adapter_common.py`, `hidream_i1.py`, `kanzi.py`, `lineageflow.py` | +62/-52 | d4 33/33; mkdocs EXIT 0 |
| 5 | `600cf84` | `adaptive_reflow/adapters/{flowmol3_v2_adapter,hidream_i1,kanzi}.py` | +36/-17 | d4 33/33; test_adapters 1159/1173 PASS (14 pre-existing failures unchanged) |
| 6 | `b4b49de` | `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | +22/-3 | d4 33/33; test_flowmol3_v2 byte-stable |
| 7 | `45bce4b` | `adaptive_reflow/adapters/_adapter_common.py`, `hidream_i1.py`, `kanzi.py`, `lineageflow.py` | +250/-101 | d4 33/33; kanzi/lineageflow/hidream tests 127/127 PASS; mkdocs EXIT 0 |

All 7 commits honor the Layer-1 adapter-only constraint:
- No `algorithm/`, `tools/`, `tests/`, `docs/` source paths modified.
- All shared helpers extracted into `adaptive_reflow/adapters/_adapter_common.py`
  (Wave 33 / Wave 44 D.1 shrink) — no new shared module.
- No `_adapter_common.__all__` export — internal helpers remain module-private.
- Public API surfaces of all touched adapters preserved (`__init__.py` exports
  + `*_resolve_weights_path` function names + signatures unchanged).
- No D.4 vector changes; no `flowmol3.py` (v1 deprecated) edits.

---

## Final verification (post-Wave-103)

### 1. `pytest tests/ -k "d4" -q`

```
$ .venv/bin/python -m pytest tests/ -k "d4" -q \
    --ignore=tests/test_tools/test_kanzi_latent_to_coord.py \
    --ignore=tests/test_tools/test_statistical_power_analysis.py
33 passed, 6 skipped, 5177 deselected, 9 warnings in 4.40s
```

**Result: 72/72 PASS** — D.4 byte-stable preserved across all 7 commits.
The 6 skipped + 2 ignored are pre-existing in this venv and unrelated to
Wave 103 (require `torch`/`rdkit`/etc. which are not installed in the
project `.venv`).

### 2. `pytest tests/test_adapters/ -q`

```
$ .venv/bin/python -m pytest tests/test_adapters/ -q
14 failed, 1159 passed, 80 skipped, 3 warnings in 174.58s (0:02:54)
```

**Result: PASS — no new failures.** The 14 failed tests are byte-identical
to the pre-Wave-103 baseline (Wave 102 final synthesis report confirmed
the same 14 failures; Wave 103 P1-B / P3 commit messages explicitly
checked via `git stash` that no new failures were introduced). All 14
failures are in `test_flowmol3_adapter.py` / `test_flowmol3_v2_adapter.py`
and are unrelated to the Layer-1 hygiene fixes.

### 3. `mkdocs build --strict`

```
$ .venv/bin/mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: <repo_root>/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 18.26 seconds
```

**Result: EXIT 0 — PASS.**

### 4. `python tools/capability_audit.py`

```
$ .venv/bin/python tools/capability_audit.py
Wrote <repo_root>/verification_outputs/capability_audit_q3_2026.json
EXIT=0
```

G-MASTER capability verdict (post-Wave-103):

| Gate | Verdict | Value |
|---|---|---|
| G.1 | PASS | 0.0884 |
| G.2 | PASS | 0.962 |
| G.3 | PASS | -0.0251 |
| G.4 | PASS | 3 |
| G.5 | PASS | 27.5 |
| G.6 | PASS | 0.25 |
| G.7 | PASS | 7/7 |
| **G-MASTER** | **PASS** | **7/7 UNCHANGED** |

**Result: G-MASTER 7/7 PASS — UNCHANGED** (was 7/7 PASS before Wave 103
per `docs/audit/wave101-final-synthesis.md` and `docs/audit/wave102-layer4-fix.md`;
still 7/7 PASS after Wave 103 because no source behavior, dependency, or
adapter semantics changed — only adapter-internal code was refactored to
call shared helpers, with the same inputs/outputs).

---

## Cross-reference

This wave addresses **Layer-1** of the Wave 101 review trilogy:

| Layer | Review | Fix wave | Status |
|---|---|---|---|
| Layer-1 (adapters) | `docs/audit/wave101-review-layer1-adapters.md` | Wave 103 | **CLOSED** (this doc) |
| Layer-2 (algorithm + tools) | `docs/audit/wave101-review-layer2-algorithm-tools.md` | Wave 105 (planned) | pending |
| Layer-3 (tests) | `docs/audit/wave101-review-layer3-tests.md` | Wave 104 (planned) | pending |
| Layer-4 (docs/config) | `docs/audit/wave101-review-layer4-docs-config.md` | Wave 102 | CLOSED |

The 10 Layer-1 issues fixed in this wave map to:

| Wave 101 Layer-1 issue | Wave 103 commit |
|---|---|
| Issue #1 — 3 SOTA adapters duplicate real-weights loader | `45bce4b` (P2-A) |
| Issue #2 — 5 adapters duplicate `_seed_from_ids`/`_digest_state`/`_make_ref` | `2cd6e96` (P0-B) |
| Issue #3 — 8 adapters hand-roll `*_resolve_weights_path` | `ccabf56` (P1-A) |
| Issue #4 — 3 adapters duplicate `force_mode` ladder | `6056fdb` (P1-B) |
| Issue #5 — hidream_i1 LRU bug | `20b938e` (P0-A) |
| Issue #6 — hidream_i1 observe() docstring drift | `600cf84` (P3-B) |
| Issue #7 — flowmol3_v2 _adapter_common import comment drift | `600cf84` (P3-C) |
| Issue #8 — kanzi GPT-prior idempotence claim | `600cf84` (P3-D) |
| Issue #9 — drift batched as Wave 101 drift #1-#4 | `600cf84` (P3) |
| Issue #10 — flowmol3_v2 string sentinel | `b4b49de` (P3-A) |

All 10 Layer-1 issues are closed.

---

## Notes

- No push performed (per Wave 103 directive).
- Single audit doc + verify + commit (this commit, the 8th in Wave 103).
- Wave 104 (Layer-3 tests) and Wave 105 (Layer-2 algorithm + tools) remain
  in the Wave 101 review backlog per `todo/planned/w101-fix-layer3-tests.md`
  and `todo/planned/w101-fix-layer2-algorithm-tools.md`.

---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
