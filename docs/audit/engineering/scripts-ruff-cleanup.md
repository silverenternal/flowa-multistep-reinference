# Wave 158 P1 — scripts/ ruff cleanup

## Goal

Reduce ruff errors in `scripts/` from a pre-existing baseline of **34** toward 0,
widening the gate scope further. After Wave 157 P3 the gate covered
`adaptive_reflow/`, `tests/`, and `tools/`; this P1 extends it to `scripts/`.

## Before / After

| Scope       | ruff errors before | ruff errors after |
|-------------|--------------------|-------------------|
| `scripts/`  | 34                 | 0                 |

`ruff check scripts/` returns `All checks passed!` after the fix.

## Per-category fix breakdown

The 34 pre-existing errors fell into these ruff codes:

| Code    | Count | Fix path                                                |
|---------|-------|---------------------------------------------------------|
| `F841`  | 10    | Manually prefixed unused vars with `_` (e.g. `x0`→`_x0`, `e_end`→`_e_end`, `e_idx`→`_e_idx`, `n_missing`→`_n_missing`, `h`→`_h`, `eps`→`_eps`, `adapter`→`_adapter`) |
| `W292`  |  8    | `ruff check --fix` (missing newline at end of file)     |
| `I001`  |  6    | `ruff check --fix` (import sorting)                     |
| `B007`  |  2    | `s` → `_s` for unused loop control variables in flowmol3 baseline runners |
| `E402`  |  2    | Added `# noqa: E402` to documented late imports (host-fingerprint shim) |
| `SIM108`|  2    | Converted `if/else` blocks to ternary expressions (`_flowmol3_helpers.py`, `run_baselines.py`) |
| `E401`  |  1    | `ruff check --fix` (split `import a, b, c` into one per line) |
| `E702`  |  1    | Split `print(...); sys.exit(2)` onto two lines          |
| `SIM103`|  1    | Replaced `if name.startswith("_"): return False; return True` with `return not name.startswith("_")` in `run_mypy_audit.py` |
| `UP035` |  1    | `ruff check --fix` (`from typing import Callable` → `from collections.abc import Callable`) |

**Auto-fixed total:** 16 (W292 × 8 + I001 × 6 + E401 × 1 + UP035 × 1).
**Manually fixed total:** 18 (F841 × 10 + B007 × 2 + E402 × 2 + SIM108 × 2 + E702 × 1 + SIM103 × 1).

Net: 34 → 0.

## Files touched

14 files modified (see `git diff --stat scripts/`):

```
 scripts/api_churn_report.py                        |  2 +-
 scripts/baselines/_flowmol3_helpers.py             |  7 +---
 scripts/baselines/_lineageflow_helpers.py          |  4 +-
 scripts/baselines/dpm_solver_plus_plus.py          |  2 +-
 scripts/baselines/rectified_flow_reflow.py         |  2 +-
 scripts/baselines/run_baselines.py                 | 45 +++++++++++-----------
 scripts/baselines/run_flowmol3_baseline_equifm.py  |  6 +--
 scripts/baselines/run_flowmol3_baseline_moldiff.py |  8 ++--
 scripts/baselines/run_lineageflow_baseline_euler.py    |  4 +-
 scripts/baselines/run_lineageflow_baseline_heun.py |  6 +--
 scripts/baselines/run_lineageflow_baseline_rk4.py  |  4 +-
 scripts/capture_env_hash.py                        | 10 ++++-
 scripts/run_mypy_audit.py                          |  6 +--
 scripts/upload_model_card.py                       |  1 -
 14 files changed, 53 insertions(+), 54 deletions(-)
```

Notable edits:

* `scripts/api_churn_report.py:115` — added `# noqa: E402` to the late
  `with_host_fingerprint` import (after `sys.path.insert(0, ...)`).
* `scripts/baselines/_flowmol3_helpers.py:390` — collapsed `if target_p is
  None / else` to ternary per ruff's exact suggestion.
* `scripts/baselines/_lineageflow_helpers.py:73` — `n_missing` is
  intentionally unused; renamed to `_n_missing` (the `n_unexpected` is
  consumed downstream for the `len(state) - n_unexpected` return value).
* `scripts/baselines/dpm_solver_plus_plus.py:127` — `h` was assigned but
  never referenced; renamed to `_h` (the code path uses `t_hi - t_lo`
  directly on subsequent lines).
* `scripts/baselines/run_baselines.py` — split the auto-sort of
  `from adaptive_reflow.adapters.twodim_fm import (...)` into three
  import blocks (one for plain symbols, one for `_batched_integrate_rk4`,
  one for `_velocity_field`); each gets `# noqa: E402` to match the
  existing convention. Renamed the 5 dead `x0`/`adapter` assignments to
  `_x0`/`_adapter` in the velocity-batch and reflow helper functions.
  The 2D-twodim `x0` assignments and MNIST/RF-CIFAR `adapter`
  instantiations are immediately followed by documentation comments
  explaining the approximation; the variables are intentionally
  non-binding. Collapsed the `args.quick` if/else into a ternary.
* `scripts/baselines/run_flowmol3_baseline_{equifm,moldiff}.py` —
  `s` → `_s` for unused loop counter; `e_end`/`e_idx` → `_e_end`/`_e_idx`
  for variables that are assigned and then never read.
* `scripts/baselines/run_lineageflow_baseline_heun.py:119` — `eps` →
  `_eps` (the local is dead; `uniform` is the actual renormalisation
  vector).
* `scripts/capture_env_hash.py:138` — split the
  `print(...); sys.exit(2)` on one line into two statements.
* `scripts/run_mypy_audit.py:59` — added `# noqa: E402` to the late
  host-fingerprint import.
* `scripts/run_mypy_audit.py:119` — replaced the three-line
  `if startswith("__") ... / if startswith("_") ... / return True`
  block with the direct `return not name.startswith("_")` per ruff's
  SIM103 suggestion.

## Gate verification

* `ruff check scripts/` → **All checks passed!**
* `ruff check adaptive_reflow/ tests/ scripts/ tools/` →
  **All checks passed!** (gate now covers all four directories.)
* `pytest tests/test_d4_regression_vectors.py
   tests/test_adapters/test_regression_vectors.py -q --tb=line` →
  **72 passed, 0 failed** (D.4 72/72 PASS preserved per Wave 106.C.3
  standardisation).
* `python tools/check_claims_consistency.py` →
  **"No drift detected."** (claims gate preserved).

## Script CLI sanity run

```text
$ python scripts/run_ablation_sweep.py --help 2>&1 | head -5
usage: scripts.run_ablation_sweep [-h] [--output OUTPUT] [--seed SEED]
                                  [--nfe-budgets NFE_BUDGETS]
                                  [--force-mode {synthetic,real}]

$ python scripts/capture_env_hash.py --help 2>&1 | head -5
Traceback (most recent call last):
  File ".../scripts/capture_env_hash.py", line 38, in <module>
    from adaptive_reflow.util.host_fingerprint import with_host_fingerprint
ModuleNotFoundError: No module named 'adaptive_reflow'
```

The `capture_env_hash.py --help` failure is **pre-existing** (verified
by `git stash` + re-running the command on the unmodified main HEAD —
identical error). The script imports `adaptive_reflow` at the top of
the file and does not insert the repo root into `sys.path`; it relies
on the calling environment having `adaptive_reflow` already on the
import path (e.g. `pip install -e .` or a pytest context). The ruff
fixes do not change this behaviour — there is no regression introduced
by this P1.

## Notes / known limitations

* This P1 is the bonus widening the task explicitly called out. The
  ruff gate coverage now spans all four top-level code directories
  (`adaptive_reflow/`, `tests/`, `tools/`, `scripts/`). The CI gate
  surface in `verify_submission_readiness.py` still inspects only
  `adaptive_reflow/` + `tests/` per Wave 153 design; extending the
  gate surface to include `tools/` + `scripts/` is a separate work item
  if desired (it would require updating the `ruff_0` gate's path list).
* The 2 new `E402` errors that briefly surfaced after `ruff check
  --fix` split the `twodim_fm` import into three were the only
  side-effect of the auto-fix. Both were resolved by adding
  `# noqa: E402` to each new import block, matching the existing
  convention used by every other import in the file.
* No semantic behaviour was changed. Every fix is a no-op rename
  (`x0`→`_x0`, `h`→`_h`, etc.), a comment addition (`# noqa: E402`),
  a mechanical style change (ternary / import sort / newline at EOF),
  or a clearly-equivalent refactor (SIM103's `if-return True / return
  False` → `return condition` in `_is_public`).
