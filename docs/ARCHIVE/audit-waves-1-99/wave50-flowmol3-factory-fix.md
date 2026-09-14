# Wave 50 Agent A — flowmol3 factory `force_mode` fix + real-ckpt loader

## Problem (Wave 49 fallout)

`tools.run_real_ckpt_eval._resolve_adapter` translates the CLI's
`--force-mode` token into an adapter-specific call:

```python
adapter_force_mode = "torch" if force_mode == "real" else force_mode
adapter = factory(force_mode=adapter_force_mode)
```

For the `flowmol3` model key the registry wires
`adaptive_reflow.adapters.flowmol3:default_flowmol3_adapter`. Pre-Wave-50
that factory only accepted `atom_type_entropy_restart_policy=`, so any
real-ckpt eval against `flowmol3` crashed with:

```
TypeError: default_flowmol3_adapter() got an unexpected keyword
argument force_mode
```

The same wall hit `flowmol3_v2` (via `default_flowmol3adapter`), but that
adapter already accepted `weights_path=` / `backend=`. The `flowmol3`
placeholder did not.

## Fix (this wave)

`adaptive_reflow.adapters.flowmol3.default_flowmol3_adapter` now
accepts the same shape every other top-model adapter accepts:

* `force_mode: str = "synthetic"` — `"synthetic"` / `"real"` / `"auto"`
* `weights_path: str | None = None` — explicit override of
  `FLOWMOL3_REAL_CKPT_PATH` (for tests + ablation)

`FlowMol3Adapter.__init__` accepts `force_mode=` + `real_ckpt_meta=` and
exposes them as `_force_mode` / `_real_ckpt_meta`. The default
`"synthetic"` is byte-identical to the pre-Wave-50 behaviour — the
placeholder state materializer is unchanged, the protocol surface is
unchanged, and the existing 36 tests in
`tests/test_adapters/test_flowmol3_adapter.py` still pass unmodified.

`_try_load_real_ckpt(path)` is a small lazy helper:

```python
def _try_load_real_ckpt(weights_path: str) -> tuple[Mapping | None, str | None]:
    if not os.path.isfile(weights_path):
        return None, "ckpt_missing"
    try:
        import torch
    except Exception:
        return None, "torch_not_installed"
    try:
        blob = torch.load(weights_path, map_location="cpu", weights_only=False)
    except Exception:
        return None, "ckpt_load_failed"
    if not isinstance(blob, dict):
        return None, "ckpt_unexpected_shape"
    raw_sd = blob.get("state_dict", blob)
    if not isinstance(raw_sd, dict):
        return None, "ckpt_unexpected_shape"
    return {"path": ..., "n_tensors": ..., "epoch": ..., ...}, None
```

It never raises; failures return `(None, reason)`. The factory then:

| `force_mode` | ckpt load outcome | result |
| --- | --- | --- |
| `"synthetic"` | (skipped) | placeholder adapter, `_real_ckpt_meta=None` |
| `"real"` | success | placeholder adapter, `_real_ckpt_meta={...}` |
| `"real"` | failure | `FileNotFoundError` (loud — caller can BLOCK the cell) |
| `"auto"` | success | placeholder adapter, `_real_ckpt_meta={...}` |
| `"auto"` | failure | placeholder adapter, `_real_ckpt_meta=None` (graceful) |

The "real" path is loud because `_resolve_adapter` already wraps it in
`return None, f"IMPORT_FAILED:{type(exc).__name__}:{exc}"` for any
exception — the framework eval harness already knows how to translate
`FileNotFoundError` into a BLOCKED cell.

## What this does NOT do (intentional)

The `flowmol3` placeholder adapter still does not run inference through
the real FlowMol3 stack. The reason: the placeholder deliberately keeps
the v1 DTB-G2 boundary (no FlowMol3 source import) so the public engine
+ Protocol surface stays free of any FlowMol3-specific dependency. The
real-stack inference lives in
`adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter`,
which already loads `last.ckpt` via its own `_load_model()` + DGL path
and is the adapter the eval pipeline uses for the `'flowmol3_v2'`
model key.

What this Wave 50 fix DOES unblock: the eval pipeline's
`factory(force_mode=...)` call no longer crashes for the `'flowmol3'`
key. The placeholder records whether a real ckpt load succeeded (via
`_real_ckpt_meta`) so downstream audit reports can surface a
`real_ckpt_loaded` marker — this is the same audit hook Wave 43 Agent A
added for the real-metric layer in `tools/run_real_ckpt_eval.py`. The
v2 adapter is the one that produces real chemistry numbers; the v1
placeholder records the audit trail.

## Files changed

| File | Change |
| --- | --- |
| `adaptive_reflow/adapters/flowmol3.py` | Add `FLOWMOL3_REAL_CKPT_PATH`, `FLOWMOL3_REAL_CKPT_LOADED_MARKER`, `_try_load_real_ckpt()`, extend `FlowMol3Adapter.__init__` + `default_flowmol3_adapter` with `force_mode` / `weights_path`. Update `__all__`. |
| `tests/test_adapters/test_flowmol3_adapter.py` | Add `TestFlowMol3ForceModeFactory` (13 tests). Existing 36 tests byte-stable. |
| `docs/audit/wave50-flowmol3-factory-fix.md` | This file. |

## Constants

```python
FLOWMOL3_REAL_CKPT_PATH: str = (
    "<repo-root>/data/flowmol3/weights_real/checkpoints/last.ckpt"
)
FLOWMOL3_REAL_CKPT_LOADED_MARKER: str = "flowmol3_real_ckpt_loaded"
```

The shipped 65 MB checkpoint (`epoch=17`, `global_step=1547236`,
`n_tensors=475`, `pytorch-lightning_version=2.1.3`) lives at the path
above and is loaded by the factory when `force_mode in {"real", "auto"}`.

## Test results

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_flowmol3_adapter.py -q --tb=line
49 passed, 3 warnings in 2.55s
```

Of the 49 tests, 36 are pre-Wave-50 (byte-identical placeholder surface)
and 13 are new in `TestFlowMol3ForceModeFactory`:

1. `test_default_factory_is_synthetic` — default kwarg → synthetic
2. `test_factory_explicit_synthetic_no_load` — `force_mode='synthetic'` → no ckpt I/O
3. `test_factory_real_loads_published_ckpt` — `force_mode='real'` → loads shipped ckpt
4. `test_factory_auto_loads_real_when_available` — `force_mode='auto'` → loads shipped ckpt
5. `test_factory_auto_falls_back_to_synthetic_when_ckpt_missing` — `auto` graceful fallback
6. `test_factory_real_raises_when_ckpt_missing` — `real` is loud
7. `test_factory_rejects_unknown_force_mode` — bogus token → `ValueError`
8. `test_constructor_rejects_unknown_force_mode_directly` — also enforced in `__init__`
9. `test_loaded_marker_constant_is_defined` — `FLOWMOL3_REAL_CKPT_LOADED_MARKER` exported
10. `test_ckpt_path_constant_points_at_shipped_artifact` — path resolves correctly
11. `test_try_load_real_ckpt_helper_returns_meta_on_success` — direct helper test
12. `test_try_load_real_ckpt_helper_returns_reason_on_missing` — direct helper test
13. `test_real_ckpt_adapter_is_still_a_valid_adapter` — real-ckpt adapter still produces placeholder state

## Backward compatibility

* `default_flowmol3_adapter()` with no kwargs → byte-identical to pre-Wave-50
* `default_flowmol3_adapter(atom_type_entropy_restart_policy=...)` → byte-identical
* New kwargs (`force_mode`, `weights_path`) are keyword-only with defaults
* No state shape change; `_force_mode` + `_real_ckpt_meta` are new attrs on the adapter instance

## Next step (Wave 50 Agent B)

Re-run `tools/run_real_ckpt_eval.py --model flowmol3 --force-mode real
--composite-metric flowmol3_composite` with the now-fixed factory. The
`'flowmol3'` cell should report `real_ckpt_loaded=True` (instead of
`BLOCKED:TypeError`). The `flowmol3_v2` cell runs through the v2
adapter unchanged.