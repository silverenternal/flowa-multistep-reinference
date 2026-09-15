# Wave 155 P1: `_make_adapter` Real-Ckpt Wiring Fix

## Problem

`scripts/run_ablation_sweep.py` exposes a CLI flag `--force-mode {synthetic,real}`
(verified in `--help` output) intended to thread through to per-model adapter
factories so that callers could exercise the real-ckpt path on supported
adapters (kanzi, lineageflow).

However, `_make_adapter` at line 320-365 hardcoded `force_mode="synthetic"`
on the `factory(...)` call at line 333 (and `"auto"` on the kanzi
re-instantiation at line 349). This meant **`--force-mode real` was
silently ignored** — the CLI accepted the flag, the argparse plumbing
even wrote `m["force_mode"] = args.force_mode` into the per-model
`model_spec` dict at line 1056, but `_make_adapter` never read
`model_spec["force_mode"]` and always used the literal `"synthetic"`.

This blocked the K1 RC5 full N=1000 5-arm ablation in real-ckpt mode,
because there was no way to actually route the per-cell call to
`default_kanzi_adapter(force_mode="real")` or
`default_lineageflow_adapter(force_mode="real")`.

## Fix

### Line 320-365: `_make_adapter` signature + body

Added `force_mode: str = "synthetic"` kwarg to the `_make_adapter`
signature, with a docstring note explaining the Wave 155 P1 fix.

Changed line 333 (now line 342):
```python
adapter = factory(force_mode=str(force_mode))
```
(was `factory(force_mode="synthetic")`)

Changed line 349 (now line 358) — kanzi re-instantiation:
```python
force_mode=str(force_mode),
```
(was `force_mode="auto"`)

Backward-compat preserved: default is `"synthetic"` so existing
callers and the CI-friendly shim path are unaffected.

### Line 762-766: call site (`_run_single_arm`)

Added `force_mode=str(model_spec.get("force_mode", "synthetic"))`
to the `_make_adapter(...)` call. The value comes from the per-model
`model_spec` dict, which is itself overwritten from the CLI flag
in `main()` at line 1056 (`m["force_mode"] = args.force_mode`).
Falling back to `"synthetic"` if the key is missing keeps the
function self-contained.

### `metric_mode` observation (not yet threaded)

`--metric-mode` IS set on `model_spec["metric_mode"]` at line 1057
(matching the force_mode pattern), but **it is not yet consumed by
the synthetic-mode metric helpers** at lines 708-714 (toy numpy
entropy computation). This is a pre-existing forward-compat hook:
the flag is documented and round-tripped through the model_spec
dict, but the metric helpers unconditionally compute the
stdlib-only synthetic metric. Per the task brief, this is noted
as "documented but not yet threaded" — out of scope for Wave 155
P1 (which targets force_mode wiring only). The flag remains a
no-op pass-through today.

## Verification

### ruff

```
$ ruff check scripts/run_ablation_sweep.py
Found 7 errors.
```

7 pre-existing violations (lines 355, 398, 458, 518, 684, 708, 1089).
**My edit introduces 0 new violations.** Verified by `git stash &&
ruff check` (7 errors both before and after). The first violation
(SIM105) at line 355 is on a `try/except/pass` block whose code
structure I did not change — only the `force_mode="auto"` literal
inside it became `force_mode=str(force_mode)`.

### D.4 regression vectors

```
$ pytest tests/ -k "d4" -q --tb=line
33 passed, 31 skipped, 5020 deselected, 9 warnings in 2.26s
```

All 33 collected d4 tests pass (31 skipped are hypothesis/torch
gated). Gate preserved.

### Backward-compat sanity run (synthetic)

```
$ python scripts/run_ablation_sweep.py --limit 5 \
    --force-mode synthetic --metric-mode synthetic
[DONE] wrote verification_outputs/ablation_q4_2026.json (15 cells)
```

15 cells (5 arms × 3 models), all status=OK, 0 BLOCKED. Matches the
Wave 154b POC baseline. The JSON shows:

```
Total cells: 15
All OK: True
Models: ['kanzi', 'lineageflow', 'twodim_fm']
Arms: [0, 1, 2, 3, 4]
```

## New CLI behavior

| CLI invocation                                    | Before W155 | After W155                       |
|---------------------------------------------------|-------------|----------------------------------|
| `--force-mode synthetic` (default)                | synthetic   | synthetic (unchanged)            |
| `--force-mode real` (kanzi + lineageflow sweep)   | synthetic\* | real (propagated to factories)   |
| `--metric-mode synthetic` (default)               | synthetic   | synthetic (unchanged)            |
| `--metric-mode real`                              | synthetic\* | synthetic (no-op pass-through)   |

\* previously silently ignored — the CLI flag was parsed but did not
reach the adapter factory.

## What this unblocks

**K1 RC5 full N=1000 5-arm ablation in real-ckpt mode** (35h GPU
budget). Operators can now run:

```
python scripts/run_ablation_sweep.py \
    --force-mode real \
    --metric-mode real \
    --model kanzi \
    --output verification_outputs/k1_rc5_real.json
```

and the per-cell adapter instantiation will reach
`default_kanzi_adapter(force_mode="real")` instead of being silently
demoted to `force_mode="synthetic"`.

For lineageflow the same propagation applies. The `cifar10_rf`
model referenced in the `--model` choices is not yet a MODELS entry
(forward-compat hook — sweep currently has twodim_fm/kanzi/lineageflow).

## Gates verified

- ruff 0 NEW violations introduced (7 pre-existing count preserved)
- D.4 regression vectors 33/33 PASS (gate preserved)
- Backward-compat sanity run: 15 cells all OK (matches Wave 154b POC)
- New CLI behavior: `--force-mode real` now actually propagates

## Files modified

- `scripts/run_ablation_sweep.py` (lines 320-365 + 762-766)
- `docs/audit/wave155-make-adapter-fix.md` (this doc)

## Commit hash

`d25208ba2ce17f7c1b9edf5c11cfd951ec134012` — Wave 155 P1.
