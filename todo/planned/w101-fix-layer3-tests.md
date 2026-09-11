# Wave 101 — Layer-3 Tests Hygiene Fix Plan

Companion to `docs/audit/wave101-review-layer3-tests.md`. READ-ONLY audit
identified 6 issues; this plan describes the **execution order** to close them.

## Section 1 — Goal

Split 4 monolithic test files (>1000 LOC each) into smaller files (~400-500 LOC each)
to improve navigation + parallel CI granularity, while preserving **byte-stability**
of D.4 + G-MASTER + the same number of collected tests.

Constraints:
* **No test is lost** — `pytest --collect-only` must show the same number of test items before and after
* **No D.4 byte-stable vector changes**
* **No behaviour change** in any test (only file organization)
* All new test files preserve the same `def test_*` naming convention

## Section 2 — Priorities

### P0 (must-do, lowest risk)
* **P0-A**: Fix #5 — extract `tests/test_claims/_claim_template.py`. ~50 LOC saved. Very low risk.
* **P0-B**: Fix #6 — audit + merge 2-3 duplicate fixtures. ~50 LOC saved. Very low risk.

### P1 (high impact, low risk)
* **P1-A**: Fix #3 — extract cross-adapter Protocol tests from per-adapter files. ~900 LOC removed. Very low risk (test functions are independent).
* **P1-B**: Fix #4 — split 5 adapter test files > 1000 LOC. ~1000 LOC removed. Low risk.

### P2 (large refactor, medium risk)
* **P2-A**: Fix #2 — split `tests/test_tools/test_run_real_ckpt_eval.py` (2409 LOC) into 6 sub-files mirroring `tools/eval/`. ~1500 LOC removed. Low risk.
* **P2-B**: Fix #1 — split `tests/test_algorithm/test_scheduler.py` (2549) + `test_runner.py` (2586) into per-class sub-files. ~3000 LOC removed. Low risk.

## Section 3 — Fix order (EXTRACT template first, SPLIT files last)

1. **P0-A** (extract `_claim_template.py`). D.4 must pass.
2. **P0-B** (audit fixture dupes). D.4 must pass.
3. **P1-A** (extract Protocol tests). D.4 must pass.
4. **P1-B** (split 5 adapter test files). D.4 must pass for each.
5. **P2-A** (split `test_run_real_ckpt_eval.py`). D.4 must pass.
6. **P2-B** (split `test_scheduler.py` + `test_runner.py`). D.4 must pass.

**Rationale**:
* P0 is no-brainer (extract template + audit dupes).
* P1-A is mechanical (move tests to a single deep-audit file).
* P1-B is mechanical (split a 1500-LOC file into 3 × 500-LOC files; pure file-system refactor).
* P2 is the largest change but is still pure file-system.

## Section 4 — Acceptance checklist

Per-commit:
- [ ] `pytest tests/ --collect-only -q` → same number of test items as before
- [ ] `pytest tests/ -k "d4" -q` → 33/33 PASS
- [ ] `pytest tests/test_algorithm/ tests/test_tools/ tests/test_adapters/ -q` → no new failures
- [ ] `python tools/capability_audit.py` → G-MASTER 7/7 unchanged
- [ ] `mkdocs build --strict` → exits 0

Per-fix additional:
- [ ] **P1-A**: After Protocol test extraction, `pytest tests/test_adapters/test_protocol_deep_audit.py -q` collects all cross-adapter Protocol tests; each per-adapter test file has ~300 fewer LOC.
- [ ] **P1-B**: After adapter file split, each per-adapter file is ≤ 600 LOC.
- [ ] **P2-A**: After `test_run_real_ckpt_eval.py` split, `tests/test_tools/test_run_real_ckpt_eval.py` is the 96-LOC shim test; the 6 module tests live in `tests/test_tools/eval/`.
- [ ] **P2-B**: After scheduler / runner split, each sub-file is ≤ 700 LOC.

## Section 5 — Do NOT do (scope guard)

1. **DO NOT delete any `def test_*` function** — even if it appears redundant. The user previously chose "byte-stable preservation" over "test deduplication" (Wave 60 / 62).
2. **DO NOT consolidate `test_claims/*.py` into a single file** — the per-claim file structure is for traceability (Wave 26 design choice).
3. **DO NOT touch `tests/_hypothesis_settings.py`** — Wave 38 deliverable.
4. **DO NOT touch `tests/conftest.py` `serial_tool` fixture** — Wave 60 deliverable.
5. **DO NOT add new tests** — scope is file organization only. New tests would require new fixtures, which is out of scope.
6. **DO NOT rename any test function** — downstream tools (e.g., `tools/run_sbc_audit.py`, `scripts/api_churn_report.py`) may filter by test name.
7. **DO NOT touch `tests/test_d4_regression_vectors.py`** — D.4 is the byte-stable contract; file organization of D.4 vectors is out of scope.
8. **DO NOT touch `tests/test_docs/`** — meta-tests for docs ↔ code consistency are separately maintained.

## Section 6 — Estimated effort

* P0-A: 10 minutes (extract template, update 22 imports)
* P0-B: 15 minutes (audit 6 conftest.py, merge 2-3 dupes)
* P1-A: 60 minutes (extract ~30 test functions from 5 adapter files into `test_protocol_deep_audit.py`)
* P1-B: 90 minutes (split 5 files × 18 min each)
* P2-A: 90 minutes (split `test_run_real_ckpt_eval.py` into 6 sub-files)
* P2-B: 120 minutes (split `test_scheduler.py` + `test_runner.py` into ~7 sub-files)

**Total**: ~6.5 hours across 6 commits.

## Section 7 — Commit plan

1. `wave101-p0a-claim-template` (P0-A)
2. `wave101-p0b-conftest-fixture-merge` (P0-B)
3. `wave101-p1a-protocol-deep-audit-extract` (P1-A)
4. `wave101-p1b-adapter-test-split` (P1-B)
5. `wave101-p2a-eval-pipeline-test-split` (P2-A)
6. `wave101-p2b-scheduler-runner-test-split` (P2-B, the largest)

Each commit has a single audit-doc reference in its body and a `D.4 byte-stable: PASS` footer.

---

Status: PLANNED. Awaiting execution kickoff.
