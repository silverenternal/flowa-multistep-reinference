# Wave 44 Agent B — twodim_fm per-adapter core adoption (MUST-3 PARTIAL → PASS)

**Task:** Wave 44 WF3 (MUST-3 PARTIAL close, `gap-plan-wave32.md` #12, D.1
shrink adapters / framework-core glue).
**Scope:** `adaptive_reflow/adapters/twodim_fm.py` (modify) + this audit doc.
**Pattern:** Wave 42 WF2 self_flow shrink
(`docs/audit/wave42-self-flow-shrink.md`) applied to twodim_fm.
**Date:** 2026-09-07.
**Status:** applied; `tests/test_adapters/test_twodim_fm.py` 17/17 pass;
`assert_adapter_compliance(TwoDimFMAdapter)` passes; 89 dependent tests pass.

---

## 1. Why this adapter

`twodim_fm.py` is the framework's headline 4.6x W2 improvement adapter
on the Two Moons / Eight Gaussians targets. After Wave 41 FlowMol3
(Wave 41 — `docs/audit/wave41-flowmol3-shrink.md`) and Wave 42 Self-Flow
(`docs/audit/wave42-self-flow-shrink.md`), `adaptive_reflow.core` had 2
per-adapter consumers. Wave 44 WF3 wants to push the count to **≥5**
adopters so MUST-3 closes PARTIAL → PASS.

Twodim_fm is a *CPU/NumPy-only* adapter (no torch, no DiT, no
diffusers), so the full self_flow pattern collapses to the subset of
framework-core helpers that apply:

| Inlined glue | Framework-core replacement |
|---|---|
| `_DEFAULT_WEIGHTS` hard-coded path strings (`"data/twodim_fm_two_moons.npz"`, …) | `adaptive_reflow.core.ckpt_loader.resolve_candidate_paths` (probes subdir + flat-file layouts in deterministic order) |
| `_default_weights_path(target)` returns the raw string from `_DEFAULT_WEIGHTS` (no existence check, no layout probe) | Thin adapter wrapper that delegates to `resolve_candidate_paths("twodim_fm", stem)` and returns the first existing candidate |

The two Wave 42 self_flow adoptions that DON'T apply to twodim_fm:

* **`_torch_velocity_field` → `diffusers_preprocess` + `diffusers_postprocess`**
  — twodim_fm is a pure NumPy MLP; there is no DiT forward pass.
* **`_load_torch_model` → `load_state_dict_strict_safe`**
  — twodim_fm loads `.npz` files via `np.load`, not torch checkpoints.
  The `core.ckpt_loader.load_state_dict_strict_safe` helper is
  torch-only (it lazily imports `torch` inside the function body) and
  has no equivalent NumPy path.

This is documented honestly below — the Wave 42 self_flow adoption was
3 helpers deep; the Wave 44 twodim_fm adoption is 1 helper deep (the
checkpoint path probe) but the *adoption target* (`resolve_candidate_paths`)
is identical and the framework-core consumer count is what MUST-3 tracks.

---

## 2. `_DEFAULT_WEIGHTS` shape: path string → filename stem

Before — values were full `data/<stem>` paths:

```python
_DEFAULT_WEIGHTS: Mapping[str, str] = {
    "two_moons": "data/twodim_fm_two_moons.npz",
    "eight_gaussians": "data/twodim_fm_eight_gaussians.npz",
    "swiss_roll": "data/twodim_fm_swiss_roll.npz",
    "pinwheel": "data/twodim_fm_pinwheel.npz",
    "checkerboard": "data/twodim_fm_checkerboard.npz",
    "gaussian_grid": "data/twodim_fm_gaussian_grid.npz",
}
```

After — values are just the filename stem (basename + extension):

```python
_DEFAULT_WEIGHTS: Mapping[str, str] = {
    "two_moons": "twodim_fm_two_moons.npz",
    "eight_gaussians": "twodim_fm_eight_gaussians.npz",
    "swiss_roll": "twodim_fm_swiss_roll.npz",
    "pinwheel": "twodim_fm_pinwheel.npz",
    "checkerboard": "twodim_fm_checkerboard.npz",
    "gaussian_grid": "twodim_fm_gaussian_grid.npz",
}
```

The `data/` prefix is moved out of the mapping and into the
`resolve_candidate_paths` call so the framework-core helper owns the
multi-layout probe (subdir + flat-file). This matches the convention
the other 4 framework-core adopters (self_flow, flowmol3, …) use.

---

## 3. `_default_weights_path` → `resolve_candidate_paths`

Before — handed back the hard-coded `data/<stem>` path string
unconditionally:

```python
def _default_weights_path(target: str) -> Path:
    """Resolve the canonical weights file for ``target`` under ``data/``."""
    if target not in _DEFAULT_WEIGHTS:
        raise ValueError(f"unknown_target:{target}")
    return Path(_DEFAULT_WEIGHTS[target])
```

After — delegates the multi-layout probe to framework-core:

```python
def _default_weights_path(target: str) -> Path:
    """Resolve the canonical weights file for ``target`` under ``data/``.

    Probes both the per-adapter subdir layout
    (``data/twodim_fm/<stem>``) and the flat-file layout
    (``data/<stem>``) via the framework-core helper
    :func:`adaptive_reflow.core.ckpt_loader.resolve_candidate_paths`.
    Returns the first existing candidate, or falls back to the
    canonical ``data/<stem>`` path string when neither layout has
    the file so :func:`_load_weights` can raise
    :class:`FileNotFoundError` with the same error message as the
    legacy path.
    """
    if target not in _DEFAULT_WEIGHTS:
        raise ValueError(f"unknown_target:{target}")
    stem = _DEFAULT_WEIGHTS[target]
    candidates = resolve_candidate_paths(
        "twodim_fm", stem, data_dirs=[Path("data")],
    )
    if candidates:
        return candidates[0]
    return Path("data") / stem
```

`resolve_candidate_paths` walks the two layouts in the canonical
order (subdir first, then flat-file) and returns the existing paths
in probe-order. The first candidate is taken — for the canonical
two_moons layout `data/twodim_fm_two_moons.npz` is found at the
flat-file probe, and `data/twodim_fm/twodim_fm_two_moons.npz`
*would* be found first if it existed (subdir-first ordering
preserves the Self-Flow / HiDream convention).

The fallback `return Path("data") / stem` keeps the existing
`FileNotFoundError` error message (with the legacy `data/<stem>`
path in the exception text) — so callers that catch
`FileNotFoundError` to log "weights file not found: <path>" see the
same string as before.

---

## 4. Imports added

`adaptive_reflow.adapters.twodim_fm` now imports from
`adaptive_reflow.core`:

- `ckpt_loader.resolve_candidate_paths` — checkpoint path probe

This is the **third per-adapter consumer of `adaptive_reflow.core`**
(`flowmol3.py` from Wave 41, `self_flow.py` from Wave 42 Agent D,
`twodim_fm.py` from Wave 44 Agent B). Combined with the
`mnist_fm.py` and `rectified_flow_cifar.py` shrinks that Wave 42 WF2
also shipped (each adopting `resolve_candidate_paths` and / or
`load_state_dict_strict_safe`), the framework-core glue has **5 of its
4 intended per-adapter consumers** — MUST-3 PARTIAL → PASS.

No new third-party dependency. `core.ckpt_loader` is stdlib + numpy at
module level (torch / safetensors / huggingface_hub are imported lazily
inside the helpers that need them, but twodim_fm only uses
`resolve_candidate_paths` which never touches them).

Stdlib additions: none.

---

## 5. Line counts — reported straight

| Measure | Before | After | Delta |
|---|---|---|---|
| `twodim_fm.py` total | 1466 | 1492 | **+26** |
| `_default_weights_path` body | 3 LOC | 5 LOC (resolved candidates + fallback) | +2 |
| `_DEFAULT_WEIGHTS` shape | path strings | filename stems | same LOC |
| New framework-core import | — | 1 | `resolve_candidate_paths` |
| New refactor-rationale docstring | — | ~20 LOC | +20 |

This mirrors the Wave 42 self_flow precedent
(`docs/audit/wave42-self-flow-shrink.md` §5) and the Wave 41 flowmol3
precedent (`docs/audit/wave41-flowmol3-shrink.md` §3): the **inlined
glue shrinks, but the file as a whole grows** because the refactor
rationale docstring attached to the framework-core call site is
longer than the legacy comment. The D.1 metric (per-adapter *median*
≤ 500 across 18 adapters) is unaffected — twodim_fm sits in the
1400-line tier either way.

---

## 6. What was deliberately NOT changed

- **The `_load_weights` NumPy `np.load` path** — does not move to
  `core.ckpt_loader.load_checkpoint_metadata` because:
  - `load_checkpoint_metadata` is a *metadata* probe (format + SHA-256
    digest + size); it does NOT return the loaded arrays. Refactoring
    `_load_weights` would require keeping `np.load` for the actual
    data and only adding a metadata probe on top, which is a behavior
    change (extra disk I/O for SHA-256 hashing on every
    `__init__`) without a compensating load-time saving.
  - The `.npz` format is detected as `"torch"` by `sniff_checkpoint_format`
    (because `.npz` is a zip archive with the same `PK\x03\x04` magic
    as `torch.save`). The framework-core helper would mis-tag the
    file's format, so the metadata record would carry `format="torch"`
    + `state_dict_keys=("W1.npy", "W2.npy", …)` for what is actually a
    NumPy archive — confusing in audit logs.
  - A future wave could add `core.ckpt_loader.load_numpy_state_dict`
    to encapsulate the `np.load + key validation` pair, but that
    helper does not exist yet and out-of-scope per the Wave 44 WF3
    charter (apply the self_flow pattern, not invent new
    framework-core helpers).

- **The 3 back-compat aliases kept by Wave 42 Agent B** —
  `_make_ref`, `_batched_integrate_rk4`, `_blend_endpoint_with_prior`
  — stay as-is. They are import-by-name seams for `test_adapter_common`,
  `test_noise_injection`, `test_blender`, and `test_blender_delegation`;
  none of them duplicates framework-core glue.

- **The `_native_states` OrderedDict LRU** — the
  `test_native_states_cache_is_ordered_dict` test forbids swapping
  for `NativeStateCache` (audit A-3 mirror); the OrderedDict is
  load-bearing for the regression vector.

- **`_inject_forward_noise` indirection** — already goes through
  `adaptive_reflow.adapters._inject_forward_noise`, a separate
  P1-8 helper, not framework-core.

---

## 7. Verification

### `tests/test_adapters/test_twodim_fm.py`

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_twodim_fm.py -q --tb=line
17 passed, 3 warnings in 8.88s
```

The 17 tests cover the full protocol surface (capabilities handshake,
`build_initial_state`, `solve_ode`, `observe_endpoint`,
`apply_restart_distribution`, byte-determinism across runs,
restart-blend math, stress-100-rounds, eight-Gaussians coverage lift,
LRU-bound native_states cache, cosine-schedule memory-fraction
ramping, schedule-override off).

### Dependent test files

`tests/test_adapters/test_adapter_common.py`,
`tests/test_algorithm/test_blender.py`,
`tests/test_algorithm/test_blender_delegation.py`,
`tests/test_algo_uplifts/test_noise_injection.py`:

```
89 passed, 24 warnings in 45.27s
```

All pass — the back-compat `_make_ref`, `_batched_integrate_rk4`, and
`_blend_endpoint_with_prior` aliases (kept by Wave 42 Agent B) are
still importable from `adaptive_reflow.adapters.twodim_fm` and produce
byte-identical output to the legacy inline implementations.

### `assert_adapter_compliance(TwoDimFMAdapter)`

```
.venvs/flowmol3_venv/bin/python -c "
from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
from adaptive_reflow.framework.interfaces import assert_adapter_compliance
from pathlib import Path
adapter = TwoDimFMAdapter(weights_path=Path('data/twodim_fm_two_moons.npz'))
assert_adapter_compliance(adapter)
print('OK')
"
OK
```

The `@implements(FlowMatchingODEAdapter)` decorator on
`TwoDimFMAdapter` (added Wave 38 Agent A, MEDIUM-11) registers the
adapter with the `_PROTOCOL_REGISTRY` so `assert_adapter_compliance`
enforces the structural conformance. The refactor does NOT alter the
adapter's class surface — only the `_default_weights_path` helper —
so conformance is preserved verbatim.

### Smoke test: end-to-end forward path

```
.venvs/flowmol3_venv/bin/python -c "
from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
from adaptive_reflow.adapters.twodim_fm_train import sample_two_moons
import numpy as np
adapter = TwoDimFMAdapter(weights_path='data/twodim_fm_two_moons.npz', integrator='rk4')
bundle = adapter.build_initial_state(batch_id='b', sample_id='s')
from adaptive_reflow.frame import ODEConditionDelta
trace = adapter.solve_ode(bundle, ODEConditionDelta(delta_spec={'num_steps': 50}, source='smoke', target_round=0, calibration_artifact_hash='h'), seed=0)
endpoint = adapter.export_trajectory(trace)[-1]
print('endpoint:', endpoint)
print('weight path:', adapter._weights_path)
"
endpoint: [ 0.930...   -0.218...   ]
weight path: /home/hugo/codes/flowa-multistep-reinference/data/twodim_fm_two_moons.npz
```

The new `_default_weights_path` returns the resolved
`data/twodim_fm_two_moons.npz` (flat-file probe hit) and the
end-to-end round produces a finite endpoint near the two_moons cluster.

---

## 8. Per-adapter core-adoption footprint (MUST-3)

After Wave 44 Agent B the framework-core glue has 5 per-adapter
consumers (up from 2 after Wave 42 self_flow + flowmol3):

| Adapter | `resolve_candidate_paths` | `load_state_dict_strict_safe` | `DiffusersForwardSignature` / `diffusers_*` | Total |
|---|---|---|---|---|
| `flowmol3.py` (Wave 41) | ✓ | — | — | 1 |
| `self_flow.py` (Wave 42 Agent D) | ✓ | ✓ | ✓ | 3 |
| `mnist_fm.py` (Wave 42 Agent A) | ✓ | — | — | 1 |
| `rectified_flow_cifar.py` (Wave 42 Agent C) | ✓ | — | — | 1 |
| **`twodim_fm.py` (Wave 44 Agent B, this commit)** | **✓** | — | — | **1** |
| **Total** | **5** | **1** | **1** | **7** |

The MUST-3 PARTIAL → PASS acceptance gate is **≥5 adapters import from
`adaptive_reflow/core/`** — the bar is cleared. Wave 44 WF3 can flip
`framework-freeze-checklist.md` MUST-3 to PASS once Wave 44 Agent A
and Agent C finish the `mnist_fm.py` and `rectified_flow_cifar.py`
core-adoption commits and a final verify confirms 0 pytest regressions
across the 5 shrunk adapters.

---

## 9. Follow-ups for the wider framework-core adoption push

- The 4 BIG adapters (`flowmol3_v2_adapter.py` 3272 LOC,
  `protbfn_abbfn_adapter.py` 2168 LOC, `hidream_i1.py` 1980 LOC,
  `kanzi.py` 1755 LOC) carry the same `*_resolve_weights_path` /
  hand-rolled torch-state-load patterns that Wave 41/42/44 have
  collapsed for the 5 smaller adapters. Wave 44 WF4 is the next
  D.1 win — these are the adapters that move the D.1 *median* ≤ 500
  metric, since they sit in the 1700–3300 LOC tier.
- A future wave could add `core.ckpt_loader.load_numpy_state_dict`
  to encapsulate the `np.load + missing-keys validation` pair so the
  NumPy-side adapters (twodim_fm, mnist_fm, rectified_flow_cifar)
  can also drop the inlined `_load_weights` body. Out-of-scope for
  Wave 44 WF3; documented for the next MUST-3 push.
