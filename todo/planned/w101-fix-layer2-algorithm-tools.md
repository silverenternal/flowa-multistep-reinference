# Wave 101 — Layer-2 Algorithm + Tools Hygiene Fix Plan

**Current status:** NO-OP / DEFERRED (audit complete; risky structural merges deferred).

Companion to `docs/audit/wave101-review-layer2-algorithm-tools.md`. READ-ONLY audit
identified 9 issues; this plan describes the **execution order** to close them with
minimum risk.

## Section 1 — Goal

Reduce ~7100 LOC of duplication / monolith bloat across `adaptive_reflow/algorithm/`
and `tools/` while preserving **byte-stability** of D.4 + G-MASTER + all algorithm/tool
tests.

Constraints:
* **No D.4 byte-stable vector changes**
* **No public symbol renames** — every existing `from adaptive_reflow.algorithm.X import Y` must continue to work
* **No behaviour change** in scheduler / runner / blender / merge-operator logic
* All new shim files preserve the import surface verbatim

## Section 2 — Priorities

### P0 (must-do, lowest risk)
* **P0-A**: Fix #5 — archive `_kanzi_project_out_inv*.py` × 3 to `tools/archive/wave95-kanzi-inv/`. Zero risk.
* **P0-B**: Fix #9 — add `--pb-engine` flag to 2 Kanzi sweep drivers. +20 LOC, very low risk.

### P1 (high impact, low risk)
* **P1-A**: Fix #3 — extract `tools/_kanzi_sweep_runner.py`. ~-300 LOC, very low risk.
* **P1-B**: Fix #4 — `paper_metrics_kanzi.py` re-export `compute_pb_validity_pct`. ~-30 LOC, low risk.
* **P1-C**: Fix #6 — extract `tools/_sota_common.py` for 8 `run_sota_*.py`. ~-200 LOC, low risk.
* **P1-D**: Fix #7 — extract `tools/_figures_common.py` for 6 `_make_*.py`. ~-60 LOC, very low risk.

### P2 (large refactor, medium risk)
* **P2-A**: Fix #1 — split `scheduler/_core.py` (5227 LOC) into 4 submodules + slim re-export shim. Highest leverage, medium risk.
* **P2-B**: Fix #2 — merge `_extra` / `_r2` companion files into canonical modules. ~-1500 LOC, low risk (post-30-wave stable).
* **P2-C**: Fix #8 — group `algorithm/` top-level into `runner/` + `blender/` + `merge/` + `perturbation/` subpackages. ~-200 LOC re-export surface, medium risk.

## Section 3 — Fix order (DELETE before EXTRACT, EXTRACT before SPLIT)

Following the user's "don't reinvent the wheel" directive, the minimal-risk order is:

1. **P0-A** (archive, no change). Verify pytest still imports.
2. **P0-B** (add 2 CLI flags). D.4 must pass.
3. **P1-D** (smallest extract: `_figures_common.py`). D.4 must pass.
4. **P1-B** (smallest re-export: `paper_metrics_kanzi`). D.4 must pass.
5. **P1-C** (8-script argparse share). D.4 must pass.
6. **P1-A** (3 Kanzi sweep drivers share). D.4 must pass.
7. **P2-B** (merge `_extra` / `_r2` companions back). D.4 must pass per merge.
8. **P2-C** (group `algorithm/` into subpackages). D.4 must pass.
9. **P2-A** (biggest split: `_core.py` → 4 files). D.4 must pass + verify all 24+ import sites.

**Rationale**:
* P0-A + P0-B are no-brainers (zero LOC risk).
* P1-A/B/C/D are mechanical extractions (extract a helper, replace 8-3 call sites, no logic change).
* P2-B is mechanical merging (delete ~1500 LOC after 30 waves of stability).
* P2-C requires re-export shims across `algorithm/__init__.py` and 4 new subpackage `__init__.py` files.
* P2-A is the largest structural change — deferred to the end so all prior extractions are byte-stable first.

## Section 4 — Acceptance checklist

Per-commit:
- [ ] `pytest tests/ -k "d4" -q` → 33/33 PASS (byte-stable)
- [ ] `pytest tests/test_algorithm/ tests/test_tools/ -q` → no new failures
- [ ] `python tools/capability_audit.py` → G-MASTER 7/7 PASS
- [ ] `mkdocs build --strict` → exits 0
- [ ] `python -c "from adaptive_reflow.algorithm.scheduler._core import CosineAnnealScheduler, CodimensionSheetScheduler, NFEAwareMemoryScheduler"` → all import successfully

Per-fix additional:
- [ ] **P2-A**: After split, `wc -l adaptive_reflow/algorithm/scheduler/*.py` shows 4 files each ≤ 2500 LOC; the slim `_core.py` re-export shim is ≤ 80 LOC.
- [ ] **P2-C**: After subpackage grouping, `pytest tests/test_algorithm/ -q` collects the same number of tests (no orphan test files).
- [ ] **P1-A**: After Kanzi sweep extraction, `wc -l tools/sweep_kanzi_n1000_*.py` shows each driver ≤ 60 LOC.
- [ ] **P1-C**: After `_sota_common.py` extraction, each `run_sota_*.py` has ≤ 50 LOC of argparse code.

## Section 5 — Do NOT do (scope guard)

1. **DO NOT change scheduler semantics**. The 13 schedulers are byte-stable. Any logic change would invalidate D.4 + 47 algorithm tests.
2. **DO NOT rename any scheduler class** (e.g., `CosineAnnealScheduler` → `LegacyCosineAnnealScheduler`). Even though it is deprecated, downstream `from .scheduler._core import CosineAnnealScheduler` sites must continue to work.
3. **DO NOT delete `CosineAnnealScheduler`** even though it is marked DEPRECATED. It is used in `sequential.py:13` (test fixture) and `scheduler_extra.py:574, 577, 579`.
4. **DO NOT touch `__init__.py` re-exports without verifying downstream**. `algorithm/__init__.py` exports 28 symbols; every one is consumed by ≥1 downstream module.
5. **DO NOT introduce new `_extra` / `_r2` companion files**. The pattern is being deprecated (P2-B reverses it).
6. **DO NOT change the `tools/eval/` subpackage structure** (Wave 97 split is canonical). Only `tools/*.py` top-level files are in scope.
7. **DO NOT touch the existing `run_real_ckpt_eval.py` shim** (96-LOC re-export of `tools/eval/`). It is the Wave 97 deliverable.
8. **DO NOT add new scheduler types** (out of scope; defer to a future Wave if needed).
9. **DO NOT split `batched_runner.py` (1094 LOC)** or `perturbation.py` (1103 LOC) — they are at the upper bound of manageable single-file size and have stable interfaces. Splitting would require re-verifying all 8 framework round-trip tests.
10. **DO NOT collapse `tools/_make_*.py` × 6 into a single CLI** — each is invoked independently from the docs build pipeline.

## Section 6 — Estimated effort

* P0-A: 5 minutes (git mv + verify imports)
* P0-B: 10 minutes (2 CLI flags × 5 min each)
* P1-D: 15 minutes (extract matplotlib preamble, update 6 scripts)
* P1-B: 10 minutes (delete + re-export, verify 2 test files)
* P1-C: 30 minutes (8 argparse scripts + shared module)
* P1-A: 30 minutes (3 sweep drivers + shared runner)
* P2-B: 90 minutes (5 companion files × 18 min each: read both, verify imports, merge, D.4 verify)
* P2-C: 90 minutes (4 subpackages × 4 files each + re-export shims + 24+ import verification)
* P2-A: 120 minutes (4-file split + re-export shim + verify 24+ import sites + capability audit)

**Total**: ~6.5 hours across 9 commits. Each commit is independently revertable.

## Section 7 — Commit plan

1. `wave101-p0a-archive-project-out-inv-scripts` (P0-A)
2. `wave101-p0b-add-pb-engine-flag-kanzi-sweeps` (P0-B)
3. `wave101-p1d-figures-common-preamble` (P1-D)
4. `wave101-p1b-paper-metrics-kanzi-reexport` (P1-B)
5. `wave101-p1c-sota-common-argparse` (P1-C)
6. `wave101-p1a-kanzi-sweep-runner-shared` (P1-A)
7. `wave101-p2b-merge-extra-r2-companions` (P2-B)
8. `wave101-p2c-algorithm-subpackage-grouping` (P2-C)
9. `wave101-p2a-scheduler-core-4way-split` (P2-A, the big one)

Each commit has a single audit-doc reference in its body and a `D.4 byte-stable: PASS` footer.

---

Status: AUDIT COMPLETE (P0/P1 and structural feasibility verified; risky merges deferred).
