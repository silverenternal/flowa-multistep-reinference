# Wave 56 Agent C — test_run_rf_cifar_ablation.py fix

## Scope

Re-do Wave 51 Agent B's failed task: fix the failing
`tests/test_tools/test_run_rf_cifar_ablation.py` pytest so that
`run_baseline` honours the smoke test's "synthetic mode" expectation.

The task spec named `tools/run_sota_rf_cifar_ablation.py` as the
modification target — that file does not exist in the repo. The
actual failing test (`test_eval_rf_cifar_synthetic_smoke`) drives
`tools.eval_rf_cifar.run_baseline` in-process; the prior
Wave-51 audit doc (`wave51-rf-cifar-fix.md`) was never written because
Wave 51 Agent B was lost to a token-plan overrun.

## Root cause

`test_eval_rf_cifar_synthetic_smoke` (line 149) calls
`_drive_eval_rf_cifar(tmp_path, num_samples=8, nfe=2, batch_size=4)`
which invokes `tools.eval_rf_cifar.run_baseline(...)` with
`weights_path=None` and asserts:

```python
assert summary["mode"] == "synthetic"
```

`tools/eval_rf_cifar.py:run_baseline` was constructing the
`RectifiedFlowCIFARAdapter` with `force_mode="auto"`. The adapter's
"auto" branch (`adaptive_reflow/adapters/rectified_flow_cifar.py:652`)
auto-resolves a weights file at `data/cifar10_rf.pth` and switches to
torch mode whenever that file exists AND torch is importable. With
torch 2.7.0 installed in the venv AND the vendored checkpoint
`data/cifar10_rf.pth` on disk, the adapter picks `mode="torch"` — and
the smoke test fails:

```
E   AssertionError: assert 'torch' == 'synthetic'
```

This is unrelated to the `PosixPath → features` coercion at
`adaptive_reflow/eval/run_eval.py:436` named in the original task
spec. That coercion bug was already addressed by Wave 51 (see the
in-line comment at `tools/eval_rf_cifar.py:298-310`). The current
failure is a contract drift between the smoke test (which expects
synthetic mode when no weights are passed) and the adapter's "auto"
fallback (which opportunistically loads whatever checkpoint sits on
disk).

## Fix

`tools/eval_rf_cifar.py:run_baseline` (single call site, line 231):

```python
adapter = RectifiedFlowCIFARAdapter(
    weights_path=weights_path,
    force_mode=("auto" if weights_path is not None else "synthetic"),
    num_steps=int(nfe),
)
```

When the caller passes `weights_path=None` the adapter now forces
`synthetic` mode. When the caller passes an explicit `weights_path`,
`force_mode="auto"` is preserved (an explicit path that doesn't exist
will still raise the adapter's FileNotFoundError — the loader-side
contract is unchanged for real-reproduction workflows).

The smoke test (`weights_path=None`) now lands in synthetic mode and
the assertion passes. Real reproduction (`python -m tools.eval_rf_cifar
--weights-path data/cifar10_rf.pth`) keeps its "auto" behaviour and
still loads the published UNet.

## Verification

```
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_tools/test_run_rf_cifar_ablation.py::test_eval_rf_cifar_synthetic_smoke \
    -v --tb=long
...
PASSED [100%]
1 passed, 4 warnings in 33.14s
```

The remaining 5 tests in the file (`test_plot_rf_cifar_load_ablation`,
`test_plot_rf_cifar_load_ablation_missing`,
`test_eval_rf_cifar_fid_formula_correct`,
`test_run_rf_cifar_ablation_synthetic_smoke`,
`test_run_rf_cifar_ablation_table_layout`) were spot-checked in
isolation and pass. The two slow ablation tests re-instantiate the
adapter with `force_mode="synthetic"` directly (see the test helper
`_drive_run_rf_cifar_ablation` at line 74), so the new behaviour is
consistent with their existing expectations.

## Files touched

- `tools/eval_rf_cifar.py` — single-call-site fix in `run_baseline`,
  with a clarifying comment explaining why `force_mode` is conditional
  on `weights_path is not None`.
- `docs/audit/wave51-rf-cifar-fix.md` — this audit doc.

No changes to `tests/test_tools/test_run_rf_cifar_ablation.py`
(READ-ONLY per the disjoint file scope), to
`adaptive_reflow/eval/run_eval.py` (READ-ONLY — the line-436
PosixPath bug is already mitigated at the call site in
`tools/eval_rf_cifar.py:311-320`), or to any other framework module.

## Notes for downstream

- The CLI default `--weights-path` is `None`. With this fix, a bare
  `python -m tools.eval_rf_cifar` invocation now uses synthetic mode
  even when `data/cifar10_rf.pth` is present. This matches the
  module docstring's "When any of the three is missing the script
  falls back to a synthetic baseline" promise — the CLI was previously
  silently violating that contract.
- Callers that actually want the published-UNet reproduction must
  pass `--weights-path data/cifar10_rf.pth` explicitly. This was
  already required for the `--reference-features` path; the weights
  path now matches the same "explicit = real, implicit = synthetic"
  convention.
