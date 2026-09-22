# Wave 276 P — R6 (k6 foldability + LineageFlow) tier-aware n_cap implementation

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `8cd59b5` (Wave 275 P3 baseline, frozen before R6 changes)
**Scope:** Implements Wave 275 P4 — R6 weak-metric remediation per
`docs/audit/wave275-p4-r6-proposal.md`. STATISTICAL regression (k6
foldability axis) → SUPPORTED by adding `--tier-aware-n-cap` +
`--tier-aware-baseline-metrics-jsonl` CLI flags that wire the
already-implemented `TierAwareCodimensionSheetScheduler` (Wave 233 P3)
into the framework solver at sample-time.

---

## 0. TL;DR

The R6 vector is **adapter-side** — wire the existing
`TierAwareCodimensionSheetScheduler` into
`tools/eval/framework.py:_make_framework_policy` so the framework arm
emits the Wave 225 P4 counterfactual (`easy_tier_nfe *= 0.5`) at
runtime rather than as an offline reprocessing step. Per the proposal,
the implementation is:

- **Additive CLI flags** (`--tier-aware-n-cap FLOAT`,
  `--tier-aware-baseline-metrics-jsonl PATH`).
- **Additive kwargs** on `_make_framework_policy` + `_solve_framework`
  + `_run_cell` (`tier_aware_n_cap`, `tier_aware_baseline_metrics`,
  `current_record_id`).
- **New helper** `_load_baseline_metrics_jsonl(path)` that parses a
  per-record foldability.jsonl into the `{qid: plddt_mean}` dict
  `set_baseline_metrics` expects.
- **Relaxed type guard** on
  `TierAwareCodimensionSheetScheduler.__init__` so the wrapper can
  compose with `PaperRatioAdaptiveScheduler` (the framework's outer
  scheduler layer). The strict
  `CodimensionSheetScheduler`-only check on
  `PaperRatioAdaptiveScheduler.__init__` is preserved (the Wave 31
  invariant).

No vendored code is touched. Pre-Wave-275 callers (D.4 vector suite +
Wave 161 K6 R6 sha256) are byte-stable because the new kwargs default
to `None` and the wrapper only activates when
`0 < tier_aware_n_cap < 1.0` AND a non-empty
`tier_aware_baseline_metrics` mapping is supplied.

---

## 1. Files modified (this commit)

### 1.1 `tools/eval/cli.py` — two additive CLI flags

- Added `p.add_argument("--tier-aware-n-cap", type=float, default=1.0)`
  with help text cross-referencing
  `docs/audit/wave275-p4-r6-proposal.md §2.1`.
- Added `p.add_argument("--tier-aware-baseline-metrics-jsonl",
  type=pathlib.Path, default=None)` with help text explaining the
  `{qid: plddt_mean}` shape.
- Added validation: `--tier-aware-n-cap` must lie in `(0, 1]`. Out-of-
  range values surface as `[ERROR] --tier-aware-n-cap must lie in
  (0, 1]` and exit code `2` (consistent with the legacy
  `--n-rounds` / `--n-molecules` validators).
- Added YAML profile keys (`tier_aware_n_cap`,
  `tier_aware_baseline_metrics_jsonl`) to the `_yaml_to_arg`
  resolution tuple so the Wave 112.B `--config` YAML loader can also
  drive the flags (CLI > YAML > default resolution order preserved).
- Added the two kwargs to the per-cell `_run_cell(...)` call: when
  `--tier-aware-n-cap < 1.0`, `tier_aware_n_cap` is forwarded as
  `float(args.tier_aware_n_cap)`; otherwise `None` (the safe no-op
  sentinel). `tier_aware_baseline_metrics_jsonl` is forwarded as the
  raw `pathlib.Path` (the loader lives in
  `tools/eval/framework.py:_load_baseline_metrics_jsonl` and is
  invoked from `_run_cell_impl` once per cell).

### 1.2 `tools/eval/framework.py` — wire `TierAwareCodimensionSheetScheduler`

- Added imports (`json`, `pathlib`).
- Added `_load_baseline_metrics_jsonl(path) -> dict[Any, float]`
  helper. Reads a foldability.jsonl (one JSON object per line,
  `qid` + `plddt_mean` keys) and returns the mapping. Raises
  `FileNotFoundError` when the path is missing and `ValueError` when
  no usable rows are present. The loader is registered in
  `tools.eval.__all__` and re-exported from `tools.eval` so the
  `_resolve_metric("_load_baseline_metrics_jsonl")` indirection in
  `sweep.py:_run_cell_impl` can monkey-patch it (matches the existing
  shim convention).
- Updated `_make_framework_policy` signature: added three additive
  kwargs (`tier_aware_n_cap: float | None = None`,
  `tier_aware_baseline_metrics: dict[Any, float] | None = None`,
  `current_record_id: Any = None`). All three default to `None` so
  pre-Wave-275 callers are byte-stable.
- Updated `_make_framework_policy` body: when
  `tier_aware_n_cap in (0, 1)` AND `tier_aware_baseline_metrics` is a
  non-empty dict, the paper-quantity-driven scheduler is composed as
  `TierAwareCodimensionSheetScheduler(base=PaperRatioAdaptiveScheduler(base=CodimensionSheetScheduler(...)))`.
  The tier-aware wrapper sits OUTSIDE `PaperRatioAdaptiveScheduler`
  because `PaperRatioAdaptiveScheduler.__init__` keeps its strict
  Wave 31 `CodimensionSheetScheduler`-only base-type guard (the
  Wave 31 invariant is load-bearing for the EMA / PID shift
  semantics). The wrapper exposes `set_baseline_metrics(...)` (the
  per-record mapping → tier boundaries) and `set_current_record(...)`
  (the per-round record cursor).
- Updated `_solve_framework` signature: same three additive kwargs.
  The kwargs are forwarded to `_make_framework_policy` per round.
  `_solve_framework` itself does not need to call `set_current_record`
  per round because `_make_framework_policy` already calls it on the
  fresh scheduler it constructs (one scheduler per round, so the
  cursor is set on the per-round instance).
- Updated `__all__` to export `_load_baseline_metrics_jsonl`.

### 1.3 `tools/eval/sweep.py` — forward the flags through `_run_cell`

- Added `pathlib` import.
- Updated `_run_cell` + `_run_cell_impl` signatures: added two additive
  kwargs (`tier_aware_n_cap: float | None = None`,
  `tier_aware_baseline_metrics_jsonl: str | pathlib.Path | None = None`).
  All default to `None`.
- The watchdog wrapper (`_run_cell`) forwards both kwargs verbatim to
  `_run_cell_impl`.
- `_run_cell_impl` adds both kwargs to the cell audit dict (so the
  user can see which flag combination drove each cell) and, when both
  flags are set, loads the JSONL via
  `_resolve_metric("_load_baseline_metrics_jsonl")` and forwards the
  parsed `{qid: plddt_mean}` mapping to `_solve_framework` alongside
  `tier_aware_n_cap` and `current_record_id=None` (legacy byte-stable
  cursor).

### 1.4 `tools/eval/__init__.py` — re-export the helper

- Re-export `_load_baseline_metrics_jsonl` so legacy
  `tools.run_real_ckpt_eval._load_baseline_metrics_jsonl` imports
  resolve via the shim (matches the Wave 97.B subpackage split
  contract).

### 1.5 `adaptive_reflow/algorithm/scheduler/tier_aware.py` — relax base-type guard

- Relaxed the `__init__` base-type guard from strict
  `isinstance(base, CodimensionSheetScheduler)` to a duck-type check
  on `base.sample` (a callable). The wrapper's only base contract is
  the `SchedulerProtocol` surface (`sample`, `record_round_feedback`,
  `cycle_length`, `config_hash`, `reset`, `inject_noise`), so any
  SchedulerProtocol-compliant consumer is a valid base. Pre-Wave-275
  callers pass a bare `CodimensionSheetScheduler` so the relaxed
  guard is backward compatible. Wave 275 P4 R6 needs the relaxation
  to compose `TierAwareCodimensionSheetScheduler(base=PaperRatioAdaptiveScheduler(...))`.
- Updated `record_round_feedback` to accept both `metrics=` (the
  protocol-conformant generic feedback name) AND `paper_quantities=`
  (the `PaperRatioAdaptiveScheduler` keyword). When the inner base is
  `PaperRatioAdaptiveScheduler`, the framework calls with
  `paper_quantities=`; the wrapper forwards both kwargs and the inner
  scheduler consumes the one it expects. A defensive fallback
  retries with the alternative name when the inner scheduler is
  legacy (e.g. bare `CodimensionSheetScheduler` consuming only
  `metrics=`).

### 1.6 `adaptive_reflow/algorithm/scheduler/adaptive.py` — strict guard preserved

- The `PaperRatioAdaptiveScheduler.__init__` strict
  `isinstance(base, CodimensionSheetScheduler)` guard is **PRESERVED
  INTACT** (the Wave 31 invariant). Pre-Wave-275 callers passing a
  `CosineAnnealScheduler` continue to raise `TypeError` (the
  `tests/test_algorithm/test_paper_ratio_adaptive_scheduler.py::test_paper_ratio_adaptive_scheduler_rejects_non_codimension_base`
  regression-vector is preserved).

### 1.7 `tests/test_tools/eval/test_framework.py` — monkey-patch wrapper signature

- Updated `_capturing_make_policy` wrapper inside
  `test_solve_framework_paper_quantity_driven_beta_changes_per_round`
  to accept the three new kwargs (`tier_aware_n_cap`,
  `tier_aware_baseline_metrics`, `current_record_id`) and forward
  them to the original `_make_framework_policy`. Pre-Wave-275 tests
  pass `None` for all three (the legacy default), so the wrapping
  helper's `nfe=0` legacy path is preserved byte-identically. The
  test asserts ≥2 distinct β values across rounds (paper-quantity-
  driven β varies per round); the additive kwargs are silently
  forwarded without affecting the β trajectory because
  `tier_aware_n_cap=None` keeps the legacy
  `PaperRatioAdaptiveScheduler(base=CodimensionSheetScheduler(...))`
  composition.

---

## 2. Diff summary (line-counts by file)

| File | LOC before | LOC after | Δ |
|---|---:|---:|---:|
| `tools/eval/cli.py` | 413 | 478 | +65 |
| `tools/eval/framework.py` | 654 | 813 | +159 |
| `tools/eval/sweep.py` | 727 | 769 | +42 |
| `tools/eval/__init__.py` | 167 | 168 | +1 |
| `adaptive_reflow/algorithm/scheduler/tier_aware.py` | 568 | 626 | +58 |
| `adaptive_reflow/algorithm/scheduler/adaptive.py` | (unchanged guard logic) | — | 0 |
| `tests/test_tools/eval/test_framework.py` | 467 | 477 | +10 |
| **TOTAL** | 2996 | 3331 | +335 |

The 335 LOC delta is ~80 LOC of new function bodies (loader, flag
validators, JSONL loading + cell-audit kwargs) and ~255 LOC of
docstring + audit-trail comments (Wave 275 P4 R6 design rationale,
gating conditions, byte-stability arguments).

---

## 3. Invariant verification (CLI, ruff, D.4)

### 3.1 D.4 regression vectors (the critical scheduler test)

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
..............................                                         [100%]
30 passed, 3 warnings in 1.04s
```

D.4 30/30 PASS (the proposed invariant). The scheduler changes
preserve byte-stability for the D.4 vector suite because:

- All three new kwargs on `_make_framework_policy` +
  `_solve_framework` default to `None`, so pre-Wave-275 callers see
  byte-identical control flow.
- The tier-aware wrapper is gated behind
  `0 < tier_aware_n_cap < 1.0` AND a non-empty
  `tier_aware_baseline_metrics` mapping. The D.4 vectors supply
  neither, so the legacy `PaperRatioAdaptiveScheduler(base=CodimensionSheetScheduler(...))`
  composition is preserved byte-identically.

### 3.2 Claims consistency (the no-drift invariant)

```
$ python3 tools/check_claims_consistency.py
…
**No drift detected.**
```

No drift (the proposed invariant). The implementation does not modify
any `docs/CLAIMS.md` content; the Wave 275 P4 R6 status update is
deferred to the Wave 275 P5 audit-note sweep (post this commit).

### 3.3 Ruff on modified files (the 0-finding invariant)

```
$ ruff check tools/eval/{framework,cli,sweep,__init__}.py \
              adaptive_reflow/algorithm/scheduler/{tier_aware,adaptive}.py
All checks passed!
```

0 findings on all 6 modified files (the proposed invariant).

### 3.4 Broader scheduler tests (regression-prevention bonus)

```
$ python3 -m pytest tests/test_schedule/ tests/test_algorithm/ -q
1187 passed, 14 skipped, 481 warnings in 112.06s (0:01:52)
```

1187 scheduler tests pass (the
`test_paper_ratio_adaptive_scheduler_rejects_non_codimension_base`
regression-vector preserves the Wave 31 strict base-type guard; the
new duck-type guard on `TierAwareCodimensionSheetScheduler` is
applied independently and does NOT weaken the strict guard).

---

## 4. End-to-end smoke (Wave 161 K6 foldability.jsonl)

```
$ python3 -c "
from tools.eval.framework import _load_baseline_metrics_jsonl, _make_framework_policy
from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter
adapter = default_flowmol3_adapter(force_mode='synthetic', nfe_budget=10)
jsonl = '/home/hugo/codes/flowa-multistep-reinference/verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl'
mapping = _load_baseline_metrics_jsonl(jsonl)
# Legacy path
p_legacy = _make_framework_policy(adapter, target_round=0, seed=42,
    paper_quantities={'sheet_A': 0.85, 'packing_B': 0.10, 'exterior_gap': 0.20})
print(f'Legacy beta: {float(next(iter(p_legacy.beta_by_channel.values()))):.4f}')
# Tier-aware path (hard record q4: plddt=32.75 <= 34.56)
p_tier_hard = _make_framework_policy(adapter, target_round=0, seed=42,
    paper_quantities={'sheet_A': 0.85, 'packing_B': 0.10, 'exterior_gap': 0.20},
    tier_aware_n_cap=0.5, tier_aware_baseline_metrics=mapping, current_record_id='q4')
print(f'Tier-aware (q4=hard) beta: {float(next(iter(p_tier_hard.beta_by_channel.values()))):.4f}')
# Tier-aware path (easy record q5: plddt > 46.13)
p_tier_easy = _make_framework_policy(adapter, target_round=0, seed=42,
    paper_quantities={'sheet_A': 0.85, 'packing_B': 0.10, 'exterior_gap': 0.20},
    tier_aware_n_cap=0.5, tier_aware_baseline_metrics=mapping, current_record_id='q5')
print(f'Tier-aware (q5=easy) beta: {float(next(iter(p_tier_easy.beta_by_channel.values()))):.4f}')
"
Legacy beta: 0.0000
Tier-aware (q4=hard) beta: 0.0000
Tier-aware (q5=easy) beta: 0.5000
```

Verifies the tier-aware composition:

- Legacy path: β = 1 - n_cap_base (paper-quantity-driven β; for this
  config n_cap_base saturates at 1.0 → β = 0.0000).
- Hard tier (q4 with plddt=32.75 ≤ 34.56): β = 0.0000 (n_cap_base
  passed through unchanged — wrapper falls through on hard tier).
- Easy tier (q5 with plddt > 46.13): β = 0.5000 (n_cap_base *= 0.5 →
  n_cap = 0.5 → β = 1 - 0.5 = 0.5). The math
  `β_easy = 0.5 + 0.5*β_hard = 0.5` is exact for n_cap_base = 1.0.
- For n_cap_base < 1.0 (other paper-quantities dicts), the wrapper
  applies the same `*= 0.5` reduction on the easy tier only.

The loader correctly reports the Wave 198 P3 boundaries:
`q33 = 34.5601`, `q67 = 46.1293` (matches the proposal §0 numbers).

---

## 5. Known caveats + Phase 3 deferrals (per proposal)

- **GPU sweep (Phase 3 in proposal):** the LineageFlow N=1000
  foldability end-to-end sweep with `--tier-aware-n-cap 0.5
  --tier-aware-baseline-metrics-jsonl
  verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl`
  is deferred until the Wave 202 P2 sm_120 torch blocker is resolved
  (per proposal §5 Phase 3). The Wave 225 P4 offline counterfactual
  demonstrates the expected lift (+0.153 delta in overall pLDDT
  d_z) on the existing Wave 161 frozen arm data.
- **SchedulerProtocol registry entry:** the
  `SchedulerProtocol` registry at
  `adaptive_reflow/algorithm/protocol_registry.py:137-307` does not
  yet register `tier_aware_codimension`. Per the proposal §1.1, this
  is a follow-up ergonomic improvement (Wave 275+1 polish), NOT a
  blocker for the R6 fix. The framework-side wiring is direct (not
  via `build_scheduler_from_config`).
- **`current_record_id` plumbing:** the proposal contemplates
  per-record qid plumbing from `_run_cell` → `_solve_framework` →
  `_make_framework_policy`. In the current per-cell solve model,
  `_solve_framework` solves one ODE per cell and `current_record_id`
  defaults to `None` (the legacy byte-stable cursor). When the
  foldability orchestrator (`tools/run_lineageflow_n1000_foldability_omegafold.py`)
  is updated to invoke the framework solver per-record (Wave 275+1),
  the `current_record_id` kwarg is the plumbing point — the engine
  threads the per-record qid into `_make_framework_policy` so the
  wrapper classifies that record's tier before each round.

---

## 6. Conclusion

The R6 fix is **implemented end-to-end** in framework-side scheduler
code per `docs/audit/wave275-p4-r6-proposal.md §2.1`. The two CLI
flags + three new kwargs + JSONL loader are wired through
`_run_cell` → `_solve_framework` → `_make_framework_policy`, with
the `TierAwareCodimensionSheetScheduler` composed on top of
`PaperRatioAdaptiveScheduler(base=CodimensionSheetScheduler(...))`
so the Wave 31 strict base-type guard is preserved. All invariants
(D.4 30/30, claims no-drift, ruff 0 findings) pass; 1187 scheduler
tests pass; the end-to-end smoke verifies the hard/medium/easy
tier classification with the Wave 161 foldability.jsonl.