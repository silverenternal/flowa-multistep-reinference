# Wave 101 — Layer-2 Algorithm + Tools Engineering-Hygiene Audit

**Status:** READ-ONLY audit (Layer 2 of 4, sibling of `wave101-review-layer1-adapters.md`).
**Scope:** `adaptive_reflow/algorithm/` + `tools/`.
**Author note:** Wave 101 originally launched 4 parallel review agents; only
Layer-1 completed cleanly before the rest stalled. This document was authored
manually with the same scoring rubric as Layer-1 to preserve format parity.

---

## Section 0 — File inventory

### `adaptive_reflow/algorithm/` (33 files, ~15K LOC total)

| Subpackage | Files | Total LOC | Notes |
|---|---|---|---|
| `scheduler/` | `_core.py` (5227) + `evidence_driven.py` + `freetraj.py` + `regime_selector.py` + `__init__.py` | ~6500 | `_core.py` is the dominant file |
| top-level | `batched_runner.py`(1094) + `blender.py`(789) + `perturbation.py`(1103) + `sequential.py` + `policy_driver.py` + `solver.py` + `integrator.py` + `runner.py` + `runner_registry.py` + `protocol_registry.py` + `evidence_driver.py` + `handoff.py` + `dynamics.py` + `state_machine_integration.py` + `nfe_allocation.py` + `dynamic_noise_bias.py` + `rotation_policy.py` + `categorical_blender.py` + `per_channel_blender.py` + `merge_operator.py` + `merge_operator_v3.py` + `merge_r2.py` + `_derivation.py` + `_synthetic_oracle.py` + `sequential_handoff.py` | ~8000 | top-level growing |
| `_extra` / `_r2` companions | `blender_extra.py` + `merge_operator_extra.py` + `round2_extra.py` + `scheduler_extra.py` + `scheduler_r2.py` | ~3500 | **candidates for merge or delete** |

### `tools/` (~80 Python files, ~17K LOC)

| Cluster | Files | Notes |
|---|---|---|
| Eval pipeline | `run_real_ckpt_eval.py` (96, shim) → `tools/eval/` (Wave 97 split: 6 modules) | clean post-Wave 97 |
| Sweep drivers | `sweep_kanzi_n1000_*.py` × 4 + `sweep_nfe_scan.py` + `gen_lineageflow_n1000_fastas.py` | overlapping |
| Paper metrics | `paper_metrics.py` + `paper_metrics_kanzi.py` + `flowmol3_xtb_bridge.py` | partial overlap |
| Bridges | `kanzi_latent_to_coord.py` + `_kanzi_project_out_*.py` | duplicate `_project_out_inv` workflow |
| Audit / capability | `capability_audit.py` (1185) + `run_sbc_audit.py` + `run_mutation_audit.py` | large but each justified |
| CLI scripts | `run_sota_*.py` × 8 | identical patterns |
| Helper modules | `_sweep_assertion.py` + `_gpu_watchdog.py` + `statistical_power_analysis.py` + `check_*.py` × 3 | clean |

---

## Section 1 — TL;DR (5 most severe engineering-hygiene issues, ranked)

### Rank 1 — `scheduler/_core.py` is a 5227-LOC monolith
**Severity: HIGH**. Holds 13 classes (`ScheduleSample`, `SchedulerProtocol`, `CosineAnnealScheduler`, `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler`, `ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `NFEAwareMemoryScheduler`) plus their per-class methods. Wave 95 / 96 / 31 added 3 new schedulers (codimension_sheet, paper_ratio_adaptive, nfe_aware_memory) without splitting.

* `scheduler/_core.py:73-310` — 3 Protocols / dataclasses (`ScheduleSample`, `ScheduleSampleProtocol`, `SchedulerProtocol`) — **could move to `scheduler/protocols.py`**
* `scheduler/_core.py:310-1895` — 6 "simple" schedulers (`CosineAnnealScheduler` through `SigmoidScheduler`) — **could move to `scheduler/simple.py`** (single file)
* `scheduler/_core.py:1896-4250` — 3 "adaptive" schedulers (`ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`) — **could move to `scheduler/adaptive.py`**
* `scheduler/_core.py:4251-5227` — `NFEAwareMemoryScheduler` + utilities — **could move to `scheduler/nfe_aware.py`**

**Fix**: 4-way split into submodules (4 files of ~1200 LOC each, vs current 1×5227). Risk: medium — must preserve the `_core.py` re-export contract (24+ downstream `from .scheduler._core import` sites). **Effort**: ~1.5h + 8 verification scripts.

### Rank 2 — `_extra` / `_r2` companion files (5 files, ~3500 LOC) are split-extracted growth
**Severity: MEDIUM**. Wave 18 / 19 / 30 split large scheduler + merge-operator + blender files into `_extra.py` + `_r2.py` companions. These are now candidates for **merging back** into the canonical module:
* `blender_extra.py` (likely from Wave 18 / 19 B-extensions)
* `merge_operator_extra.py` + `merge_r2.py` (Wave 18 merge-operator-v2 split)
* `round2_extra.py` (Wave 30 round-2 perturbation extensions)
* `scheduler_extra.py` + `scheduler_r2.py` (Wave 18 / 19 scheduler v2 split)

Each `_extra` / `_r2` companion is 200-700 LOC of related logic that has been stable since Wave 30 (~3 months). The split was for "blast radius" reasons but the cost is now the navigation overhead.

**Fix**: For each pair (`X.py` + `X_extra.py` / `X_r2.py`), audit usage: if `_extra` exports are all used in `X.py` OR by ≥2 external modules, merge back. Risk: low — already byte-stable across 30+ waves.

### Rank 3 — `tools/sweep_kanzi_n1000_*.py` (3 nearly-identical files) duplicate framework setup
**Severity: MEDIUM**. Three sweep drivers all do the same preamble:
* `sweep_kanzi_n1000_framework_paper_metrics.py`
* `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py`
* `sweep_kanzi_n1000_paper_metrics.py` (baseline arm)

Each duplicates: imports, argparse, Kanzi adapter construction, sweep loop body, output JSONL writer. ~120 LOC duplicated per copy × 3 = ~360 LOC.

**Fix**: Extract the common `run_kanzi_sweep(mode: str, *, projector: str | None = None) -> None` into a shared module (e.g., `tools/_kanzi_sweep_runner.py`). Each driver becomes a 30-LOC shim that sets argv flags and calls the shared function. Risk: very low (no behaviour change). ~300 LOC removed.

### Rank 4 — `tools/paper_metrics.py` and `tools/paper_metrics_kanzi.py` overlap on `compute_pb_validity_pct`
**Severity: MEDIUM**. Both files export `compute_pb_validity_pct`. `paper_metrics_kanzi.py` (Wave 83) was extracted from `paper_metrics.py` to add Kanzi-specific codebook metrics, but the `pb_validity_pct` function still lives in both. The Wave 82 YAML vendor + xtb wiring is split across both files.

* `tools/paper_metrics.py:294-309` — `compute_pb_validity_pct` (UFF default, Wave 82 xtb wire)
* `tools/paper_metrics_kanzi.py:??` — `compute_pb_validity_pct` (Kanzi-specific xtb default)

**Fix**: Pick one canonical location (`tools/paper_metrics.py` is the canonical one), have `paper_metrics_kanzi.py` import + re-export with the Kanzi-specific default. ~30 LOC removed. Risk: low — both are tested independently (Wave 82 + 83 verification).

### Rank 5 — `tools/_kanzi_project_out_inv*.py` (3 files) is a partial-fidelity pattern that should consolidate
**Severity: LOW-MED**. Three files implement the same `project_out` inverse pattern:
* `_kanzi_project_out_inverse_probe.py` — Wave 95 Phase 3 probe
* `_kanzi_project_out_inv_train.py` — Wave 95 inverse trainer
* `_kanzi_project_out_inv.pt` — the trained inverse tensor (binary)

`kanzi_latent_to_coord.py:194-228` consumes the `.pt` file. The probe + trainer files were one-time verification scripts that should be **moved to `tools/archive/wave95-kanzi-inv/`** or merged into a single `tools/kanzi_project_out.py` module that exposes: `probe_reconstruction_error()`, `train_inverse()`, `load_inverse()`.

**Fix**: Move 2 helper scripts to `tools/archive/` (read-only after Wave 95), keep only the load path. ~150 LOC archived. Risk: zero.

---

## Section 2 — `algorithm/` subpackage structure (top-level vs `scheduler/`)

The `adaptive_reflow/algorithm/` directory has 33 top-level files. Many are conceptually related but not co-located:
* `batched_runner.py` (1094) + `sequential.py` + `runner.py` + `runner_registry.py` — **all "runners"**
* `blender.py` + `categorical_blender.py` + `per_channel_blender.py` + `blender_extra.py` — **all "blenders"**
* `merge_operator.py` + `merge_operator_v3.py` + `merge_operator_extra.py` + `merge_r2.py` — **all "merge operators"**
* `dynamic_noise_bias.py` + `perturbation.py` + `round2_extra.py` + `rotation_policy.py` — **all "perturbation"**

**Fix**: Group these into subpackages:
* `algorithm/runner/` — `batched_runner.py` + `sequential.py` + `runner.py` + `runner_registry.py` + `__init__.py` (re-exports)
* `algorithm/blender/` — 4 files + `__init__.py`
* `algorithm/merge/` — 4 files + `__init__.py`
* `algorithm/perturbation/` — 4 files + `__init__.py`

Top-level `algorithm/` keeps only: `dynamics.py`, `solver.py`, `evidence_driver.py`, `nfe_allocation.py`, `policy_driver.py`, `state_machine_integration.py`, `protocol_registry.py`, `_derivation.py`, `_synthetic_oracle.py`, `handoff.py`, `sequential_handoff.py`, `integrator.py`, `__init__.py`.

Risk: medium — 24+ downstream `from adaptive_reflow.algorithm.X import ...` sites. Need to keep `__init__.py` re-exports stable.

---

## Section 3 — `scheduler/_core.py` 5227-LOC split recommendation

The 4-way split (Rank 1) is the highest-leverage single change. Per-class split plan:

| File | LOC (approx) | Contents |
|---|---|---|
| `scheduler/protocols.py` | ~240 | `ScheduleSample`, `ScheduleSampleProtocol`, `SchedulerProtocol` |
| `scheduler/simple.py` | ~1600 | `CosineAnnealScheduler`, `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler` |
| `scheduler/adaptive.py` | ~2350 | `ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler` |
| `scheduler/nfe_aware.py` | ~980 | `NFEAwareMemoryScheduler` + utilities |
| `scheduler/_core.py` (slimmed) | ~60 | Re-export shim: `from .protocols import *; from .simple import *; from .adaptive import *; from .nfe_aware import *` |

Risk: **medium** — `_core.py` has 24+ downstream `from adaptive_reflow.algorithm.scheduler._core import` sites. The re-export shim preserves all imports. **Verification**: each import site must continue to find the symbol; `pytest tests/test_algorithm/ -q` should stay green.

---

## Section 4 — `tools/` single-file / single-pattern issues

| Issue | File(s) | LOC delta | Risk |
|---|---|---|---|
| 3 Kanzi sweep drivers share preamble | `tools/sweep_kanzi_n1000_*.py` × 3 | ~ -300 LOC | very low |
| `paper_metrics_kanzi.py` re-defines `compute_pb_validity_pct` | `tools/paper_metrics.py` + `tools/paper_metrics_kanzi.py` | ~ -30 LOC | low |
| `tools/_kanzi_project_out_inv*.py` × 3 partial-fidelity | archive to `tools/archive/wave95-kanzi-inv/` | ~ -150 LOC | zero |
| `tools/run_sota_*.py` × 8 share argparse preamble | extract `tools/_sota_common.py` | ~ -200 LOC | low |
| `tools/_make_*.py` × 6 figure scripts share matplotlib preamble | extract `tools/_figures_common.py` | ~ -60 LOC | very low |

Total: ~ -740 LOC across `tools/`.

---

## Section 5 — Import / CLI hygiene

### Import direction check
Tools import direction is correct: `tools/ → adaptive_reflow/` (no reverse). Verified by `grep -r "from tools\." adaptive_reflow/` → 0 results. **Clean.**

### CLI consistency
* `--force-mode {auto,torch,synthetic}` — present in 4 tools (kanzi eval, lineageflow eval, flowmol3 eval, hidream eval)
* `--max-records N` — present in 8 tools (uniform naming)
* `--seed N` — present in 7 tools (uniform)
* `--output-dir DIR` — present in 6 tools (uniform)
* `--nfe-steps N` — present in 4 tools (uniform)
* `--pb-engine {uff,xtb}` — present in 2 tools (Wave 82 add); should be in all 4 paper-metric tools

**Inconsistency**: `--pb-engine` is missing from `tools/sweep_kanzi_n1000_paper_metrics.py` (baseline arm) and `tools/sweep_kanzi_n1000_framework_paper_metrics.py` (framework arm). Should be added.

### Circular imports
None detected in the new audit. Wave 41 Agent C fixed the previous test_algo_uplifts circular import.

---

## Section 6 — Dead / deprecated code

| Item | Location | Notes |
|---|---|---|
| `CosineAnnealScheduler` (310-727) | `scheduler/_core.py` | DEPRECATED per docstring at line 651; still imported by `sequential.py:13` (test fixture). Keep but mark with `@deprecated` decorator. |
| `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler` | `scheduler/_core.py` | Used in tests; not removed. |
| `StochasticFMAdapter` enum | removed Wave 33 | ✓ |
| `tools/run_sota_wan2_2_video_experiment.py:89 _TODO` | `tools/` | Explicit placeholder, not dead code. |
| `tools/check_docs_against_code.py:103 TODO` | `tools/` | In denylist (acceptable). |

No actionable dead code beyond Rank 5 (`_kanzi_project_out_inv*.py` archives).

---

## Section 7 — Fix suggestions (per issue, with LOC estimate + risk)

| # | Issue | Fix | LOC delta | Risk |
|---|-------|-----|-----------|------|
| 1 | `scheduler/_core.py` 5227-LOC monolith | 4-way split (`protocols.py` + `simple.py` + `adaptive.py` + `nfe_aware.py`) + slim re-export shim | ~ +60 shim, ~ -5167 internal | Medium — verify all 24+ import sites |
| 2 | `_extra` / `_r2` 5 companion files | Merge back into canonical modules where usage ≥ 2 sites | ~ -1500 LOC | Low — 30+ waves stable |
| 3 | 3 Kanzi sweep drivers share preamble | Extract `tools/_kanzi_sweep_runner.py` | ~ -300 LOC | Very low |
| 4 | `paper_metrics_kanzi.py` redefines `compute_pb_validity_pct` | Re-export from canonical | ~ -30 LOC | Low |
| 5 | `_kanzi_project_out_inv*.py` × 3 partial-fidelity | Archive to `tools/archive/wave95-kanzi-inv/` | ~ -150 LOC | Zero |
| 6 | 8 `run_sota_*.py` share argparse preamble | Extract `tools/_sota_common.py` | ~ -200 LOC | Low |
| 7 | 6 figure scripts share matplotlib preamble | Extract `tools/_figures_common.py` | ~ -60 LOC | Very low |
| 8 | Algorithm/ top-level 33 files | Group into `runner/` + `blender/` + `merge/` + `perturbation/` subpackages | ~ -200 LOC re-export surface | Medium — verify imports |
| 9 | `--pb-engine` flag missing on 2 Kanzi sweep drivers | Add the flag | +20 LOC | Very low |

**Net LOC delta**: ~ -7400 LOC across algorithm/ + tools/, +260 LOC re-export shims. Net: -7100 LOC.

---

## Section 8 — Acceptance criteria

Per-fix:
1. `pytest tests/ -k "d4" -q` → 72/72 PASS (no D.4 vector changes)
2. `pytest tests/test_algorithm/ tests/test_tools/ -q` → no new failures
3. `python tools/capability_audit.py` → G-MASTER 7/7 unchanged
4. `mkdocs build --strict` → exits 0
5. `python -c "from adaptive_reflow.algorithm.scheduler._core import CosineAnnealScheduler, NFEAwareMemoryScheduler"` → both import successfully (proves re-export shim works)

---

REVIEW COMPLETE — found 9 issues across 5 dimensions (scheduler-bloat 2, runner-bloat 2, glue-bloat 1, import-hygiene 0, dead-code 0, cli-consistency 1, subpackage-grouping 1).


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
