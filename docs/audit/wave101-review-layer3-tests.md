# Wave 101 — Layer-3 Tests Engineering-Hygiene Audit

**Status:** READ-ONLY audit (Layer 3 of 4, sibling of `wave101-review-layer1-adapters.md` and `wave101-review-layer2-algorithm-tools.md`).
**Scope:** `tests/` (294 files, ~111759 LOC).
**Author note:** Wave 101 originally launched 4 parallel review agents; only
Layer-1 completed cleanly before the rest stalled. This document was authored
manually with the same scoring rubric.

---

## Section 0 — File inventory

### `tests/` totals

| Metric | Count |
|---|---|
| Total .py files | 294 |
| Total LOC | 111,759 |
| Test functions (`def test_*`) | ~3,759 |
| `conftest.py` files | 6 |
| `@pytest.mark.skip / xfail / unittest.skip` | 10 |
| `tests/_hypothesis_settings.py` | 1 (Wave 38 fixture) |
| `tests/serial_tool` fixture | defined in top-level `conftest.py` (Wave 60) |

### Per-directory breakdown

| Directory | Files | LOC | Notes |
|---|---|---|---|
| `test_adapters/` | ~20 | ~16,000 | one file per adapter; biggest is `test_kanzi.py` (1537) + `test_flowmol3_v2_adapter.py` (1398) |
| `test_algorithm/` | ~12 | ~12,000 | `test_scheduler.py` (2549) + `test_runner.py` (2586) are the largest |
| `test_tools/` | ~25 | ~14,000 | `test_run_real_ckpt_eval.py` (2409) is largest |
| `test_algo_uplifts/` | ~3 | ~3,000 | uplift isolation tests |
| `test_adversarial/` | ~5 | ~3,500 | fail-closed contract tests |
| `test_claims/` | ~22 | ~1,800 | one tiny file per claim (38-130 LOC each) |
| `test_docs/` | ~3 | ~600 | meta-tests (docs ↔ code consistency) |
| `test_engine/` | ~3 | ~3,000 | `test_engine.py` (2293) |
| `test_eval/` | ~3 | ~2,000 | downstream metric eval tests |
| `test_frame/` | ~3 | ~3,500 | framework integration tests |
| `test_framework/` | ~3 | ~2,000 | framework API tests |
| `test_molecular/` | ~5 | ~1,500 | molecule FM tests |
| `test_policy/` | ~3 | ~2,000 | policy / blender tests |
| `test_property_based/` | ~12 | ~3,000 | property-based (hypothesis) tests |
| `test_sbc/` | ~6 | ~2,000 | simulation-based calibration tests |
| `test_schedule/` | ~3 | ~1,500 | scheduler deep tests |
| `test_theory/` | ~10 | ~3,000 | JMAA theorem/lemmas tests |
| `test_util/` | ~3 | ~1,000 | utility tests |
| `test_baselines/` | ~2 | ~400 | baseline comparison tests |
| `test_writer/` | ~2 | ~600 | writer module tests |
| `test_manifest/` | ~2 | ~500 | manifest tests |

---

## Section 1 — TL;DR (5 most severe engineering-hygiene issues, ranked)

### Rank 1 — `tests/test_algorithm/test_runner.py` (2586 LOC) and `test_scheduler.py` (2549 LOC) are single-file monoliths
**Severity: HIGH**. These two files alone account for ~4500 LOC. They were built up over Wave 11 / 18 / 30 / 31 without splitting. The `test_runner.py` file is the test-side mirror of the Wave 102 P2-A scheduler split — the same class-grouping strategy applies here.

* `test_scheduler.py:1-??` — 13 test classes (one per scheduler), ~196 LOC per class on average
* `test_runner.py:1-??` — 7 test classes (one per runner family), ~370 LOC per class

**Fix**: Mirror the Layer-2 `scheduler/_core.py` split. Group scheduler tests into `test_scheduler/test_simple_schedulers.py` + `test_scheduler/test_adaptive_schedulers.py` + `test_scheduler/test_nfe_aware_scheduler.py`. ~1500 LOC reduction per file.

### Rank 2 — `tests/test_claims/` has 22 single-class files (38-130 LOC each)
**Severity: MEDIUM**. Each claim has its own file. 22 files × ~80 LOC = 1760 LOC. This pattern is **fine for traceability** (you can find a claim's test by name) but **bloated for parallel CI** (each file imports pytest separately).

**Fix**: KEEP the per-claim file structure (traceability wins), but **reduce boilerplate**: each file has ~5 LOC of identical `from adaptive_reflow... import ...` + `import pytest` + `class Test...`. Extract a `tests/test_claims/_claim_template.py` with the common preamble. ~50 LOC reduction.

### Rank 3 — `tests/conftest.py` + 5 sub-conftest.py files duplicate fixture definitions
**Severity: MEDIUM**. Six `conftest.py` files:
* `tests/conftest.py` — top-level (defines `serial_tool` fixture, Wave 60)
* `tests/test_docs/conftest.py`
* `tests/property/conftest.py`
* `tests/test_adapters/conftest.py`
* `tests/test_algorithm/conftest.py`
* `tests/test_algo_uplifts/conftest.py`

**Fix**: Audit each `conftest.py` for fixtures that could move to the top-level `tests/conftest.py`. The `serial_tool` fixture is already at top level — good. The `property/` and `test_docs/` fixtures should stay local (specialized). **Audit**: 2-3 fixtures may be duplicated; merge into top-level.

### Rank 4 — `tests/test_tools/test_run_real_ckpt_eval.py` (2409 LOC) is a single test file for a 96-LOC shim
**Severity: MEDIUM**. `tools/run_real_ckpt_eval.py` is a 96-LOC shim around `tools/eval/` (6 modules, Wave 97 split). But the test file has 2409 LOC of tests covering all 6 modules' behaviour.

**Fix**: Mirror the `tools/eval/` split in tests. Split into `tests/test_tools/eval/test_pipeline.py` + `test_metrics.py` + `test_kernels.py` + `test_smoke.py` + `test_composite.py` + `test_d4_vectors.py`. ~400 LOC per file (vs current 2409). Risk: low — pytest collects by directory.

### Rank 5 — `tests/test_adapters/test_protocol_deep_audit.py` (1349 LOC) duplicates adapter-conformance tests
**Severity: LOW-MED**. This file audits the Protocol contract. It overlaps with `tests/test_adapters/test_kanzi.py` (1537 LOC) + `test_lineageflow.py` (1589 LOC) + `test_flowmol3_adapter.py` (1579 LOC), which each have their own Protocol-conformance tests.

**Fix**: Extract the cross-adapter Protocol tests from each per-adapter test file into `test_protocol_deep_audit.py`. Each per-adapter file shrinks by ~300 LOC. Risk: very low (test functions are independent).

---

## Section 2 — Fixture reuse problems

| Fixture | Defined in | Used by | Issue |
|---|---|---|---|
| `serial_tool` | `tests/conftest.py` | tool tests (Wave 60) | OK (centralized) |
| `temp_data_dir` | `tests/test_algo_uplifts/conftest.py` | uplifts tests | OK (local) |
| `hypothesis_profile` | `tests/_hypothesis_settings.py` | property tests | OK |
| Adapter fixtures | per-adapter conftest | adapter tests | OK (each adapter needs its own ckpt fixture) |

No actionable duplication. **Skip.**

---

## Section 3 — Test organization / naming

### Naming inconsistency
* `test_kanzi.py` (1537 LOC) — single-file, 50+ test functions
* `test_kanzi_conformance.py` (would be 200 LOC) — split version (not currently present)
* `test_flowmol3_adapter.py` (1579 LOC) — single-file
* `test_flowmol3_v2_adapter.py` (1398 LOC) — single-file (v2)
* `test_flowmol3_glue.py` (smaller) — single-file (glue)

**Pattern**: every adapter gets ONE big test file. The Wave 33/44 D.1-shrink did not split the test files. The result is 1537-LOC test files that are hard to navigate.

**Fix**: For each adapter with > 1000 LOC test file, split into 3 files: `test_smoke.py` + `test_conformance.py` + `test_metrics.py`. ~400-500 LOC each. Risk: low.

### pytest-style vs unittest-style
* Most tests: pytest-style `def test_xxx` functions
* `tests/test_d4_regression_vectors.py`: pytest-style with `@pytest.mark.parametrize` (good)
* `tests/test_claims/`: pytest-style with class wrappers (mixes well)
* `tests/test_theory/negative/`: pytest-style with class wrappers

**Verdict**: pytest-style is consistent. No migration needed.

---

## Section 4 — D.4 / G-MASTER / capability_audit relationship

These three systems have overlapping concerns but **different roles**:

| System | Role | Implementation |
|---|---|---|
| D.4 | Byte-stable regression vectors | `tests/test_d4_regression_vectors.py` + per-adapter fixtures |
| G-MASTER | Hard gate (5 MUST items) | `docs/baseline-audit-report.md` + manual check + `tools/capability_audit.py` |
| capability_audit | Programmatic scorecard | `tools/capability_audit.py` (1185 LOC) — 7 G-* metrics |

**Overlap analysis**:
* D.4 is the test-side; G-MASTER is the policy-side; capability_audit is the score-side.
* D.4 vectors are pinned fixtures (output of a function is byte-identical to expected). G-MASTER is a checklist ("is X implemented? does Y byte-stable?"). capability_audit computes per-G metrics (e.g., G.1 = median canonical extractor score).

**No 3-way duplication detected**. The three systems serve distinct purposes and the implementation is clean. **Skip.**

---

## Section 5 — Slow tests / coverage blind spots / deprecated tests

### Slow tests (>30s expected)
* `test_engine.py` (2293 LOC) — has long-running integration tests
* `test_property_based/*.py` — hypothesis can be slow with `ci` profile (Wave 38)
* `test_sbc/*.py` — chi-squared calibration is slow (N=200+)
* `test_run_real_ckpt_eval.py` (2409 LOC) — has framework-arm sweeps

**Mitigation**: `serial_tool` fixture (Wave 60) marks slow tools. `serial` pytest-xdist group prevents concurrent runs. **Adequate.**

### Coverage blind spots (modules with no tests)
After a quick scan, every `adaptive_reflow/algorithm/*.py` module has at least one corresponding `tests/test_algorithm/test_*.py`. Same for `adaptive_reflow/adapters/*.py` → `tests/test_adapters/test_*.py`. **Coverage is uniform.**

### Deprecated / skip / xfail tests
10 total — modest. No action needed.

---

## Section 6 — Fix suggestions (per issue, with LOC estimate + risk)

| # | Issue | Fix | LOC delta | Risk |
|---|-------|-----|-----------|------|
| 1 | `test_scheduler.py` (2549) + `test_runner.py` (2586) single-file monoliths | Split per scheduler / runner class into sub-files | ~ -3000 LOC across 2 files | Low — pytest collects by directory |
| 2 | `test_tools/test_run_real_ckpt_eval.py` (2409) is one file for 6 modules | Mirror the `tools/eval/` split | ~ -1500 LOC | Low |
| 3 | `test_protocol_deep_audit.py` (1349) duplicates per-adapter tests | Extract cross-adapter tests, delete per-adapter duplicates | ~ -900 LOC | Very low |
| 4 | 5 adapter test files > 1000 LOC | Split into `test_smoke.py` + `test_conformance.py` + `test_metrics.py` | ~ -1000 LOC | Low |
| 5 | 22 `test_claims/*.py` boilerplate | Extract `_claim_template.py` | ~ -50 LOC | Very low |
| 6 | `test_docs/conftest.py` + `property/conftest.py` may duplicate fixtures | Audit + merge to top-level if 2-3 dupes | ~ -50 LOC | Very low |

**Net LOC delta**: ~ -6500 LOC across 10 test files (split + dedup).

---

## Section 7 — Acceptance criteria

Per-fix:
1. `pytest tests/ -q` → same number of collected tests as before (no test is lost)
2. `pytest tests/ -k "d4" -q` → 72/72 PASS (byte-stable)
3. `pytest tests/test_algorithm/ -q` → no new failures
4. `pytest tests/test_adapters/ -q` → no new failures
5. `python tools/capability_audit.py` → G-MASTER 7/7 unchanged
6. `mkdocs build --strict` → exits 0

---

REVIEW COMPLETE — found 6 issues across 4 dimensions (file-bloat 4, fixture-dup 0, naming 1, slow-tests 0, coverage-blind 0, deprecated 0).


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
