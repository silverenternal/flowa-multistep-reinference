# Wave 42 Agent C — rectified_flow_cifar per-adapter refactor (D.1 shrink)

**Date:** 2026-09-05
**Wave:** 42 (MUST-3 PARTIAL close — 4 adapters shrink)
**Agent:** C
**Adapter:** `adaptive_reflow/adapters/rectified_flow_cifar.py` (the
framework's headline −44.17% FID improvement at 2-NFE on CIFAR-10,
Liu 2022)

---

## Goal

Shrink the `rectified_flow_cifar` adapter by removing inlined glue
that duplicates `adaptive_reflow.adapters._adapter_common` (the
shared P2-9 helper module), closing the D.1 adapter-shrink directive
from `framework-internal-metrics.md`. The adapter is the most
"glue-heavy" of the 4 Wave-42 shrink targets because it carries both
a `torch` production path (real DDPM++ UNet) and a `synthetic`
NumPy test path (per-pixel-affine velocity field).

---

## Inlined glue identified

| Inlined helper | Lines (before) | Equivalent shared helper |
|---|---|---|
| `_seed_from_ids(batch, sample, round)` | 4 | `seed_from_ids` (already imported) |
| `_digest_state(payload)` | 4 | `digest_state` (already imported) |
| `_make_ref(label, **parts)` | 3 | `make_ref("rf_cifar:image", label, **parts)` (already imported) |
| `_validate_state_shape(x)` | 4 | (unused — never called internally; removed) |
| `torch_is_available()` local reimpl | 10 | `torch_is_available` from `_adapter_common` (newly imported) |
| Inline `kaiming` closure in `_random_init_synthetic_weights` | 6 | `kaiming_uniform` (newly imported) |
| `_put_native_state` / `_evict_native_state` + `_native_states: OrderedDict` | 13 | `NativeStateCache` from `_adapter_common` (newly imported) |

Total inlined glue removed: **44 lines** of body code (7 helpers +
1 inline closure + 1 attribute declaration). All 7 helpers were
pure delegations / closed-form reproductions of helpers that already
live in `adaptive_reflow.adapters._adapter_common` (the Wave-2 P2-9
shared helpers module). They added no behaviour, no validation, and
no audit metadata — they were literally copy-paste from
`_adapter_common.py`.

---

## Refactor

### 1. Removed local thin wrappers

Removed:
- `def _seed_from_ids(batch_id, sample_id, source_round): return seed_from_ids(...)` (byte-identical body)
- `def _digest_state(payload): return digest_state(payload)` (single-line wrapper)
- `def _make_ref(label, **parts): return make_ref("rf_cifar:image", label, **parts)` (one-line wrapper)
- `def _validate_state_shape(x): ...` (defined but never called anywhere)

Replaced the 7 internal call sites (`build_initial_state` ×2,
`apply_restart_distribution`, `solve_ode`, `observe_endpoint`,
`inject_forward_noise`) with direct calls to the imported
`seed_from_ids` / `digest_state` / `make_ref` from
`adaptive_reflow.adapters._adapter_common`.

Kept (back-compat aliases for external test/tool imports):
- `torch_is_available` — `tools/eval_rf_cifar.py`,
  `tools/run_rf_cifar_ablation.py`, and
  `tests/test_adapters/test_rectified_flow_cifar.py:668` import it
  by name. The body now delegates to
  `_adapter_common.torch_is_available` instead of re-implementing the
  `importlib.util.find_spec` probe.
- `_batched_torch_velocity_field` —
  `tests/test_adapters/test_rectified_flow_cifar.py:645` imports it
  for the `test_batched_torch_velocity_uses_requested_cuda_device`
  test (verifies that the production tensor bridge places both UNet
  inputs on the requested CUDA device).

### 2. Inline `kaiming` closure → `kaiming_uniform`

Before:
```python
def kaiming(fan_in, fan_out):
    bound = np.sqrt(6.0 / float(fan_in))
    return np.asarray(
        rng.uniform(-bound, bound, size=(fan_in, fan_out)),
        dtype=np.float64,
    )

return {
    "W1": kaiming(in_dim, hidden_w),
    "W2": kaiming(hidden_w, in_dim),
    ...
}
```

After:
```python
return {
    "W1": kaiming_uniform(rng, in_dim, hidden_w),
    "W2": kaiming_uniform(rng, hidden_w, in_dim),
    ...
}
```

Byte-equivalence holds because the new helper's body is literally the
same `rng.uniform(-bound, bound, size=(fan_in, fan_out))` formula with
the same RNG state advancement order (W1 → W2 → t_bias). The shared
helper is the canonical He-uniform used by the other 6 adapters in
`self_flow`, `mnist_fm`, `twodim_fm`, `freqflow`, `hidream_i1`, and
`kanzi`.

### 3. `_native_states: OrderedDict` + `_put_native_state`/`_evict_native_state` → `NativeStateCache`

Before (constructor + 2 helpers, 13 lines):
```python
self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()

def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
    if digest in self._native_states:
        self._native_states[digest] = entry
        self._native_states.move_to_end(digest)
        return
    self._native_states[digest] = entry
    while len(self._native_states) > RF_CIFAR_NATIVE_STATES_MAXSIZE:
        self._native_states.popitem(last=False)

def _evict_native_state(self, digest: str) -> None:
    self._native_states.pop(digest, None)
```

After:
```python
# LRU-bounded native-states cache (audit A-3 mirror of twodim_fm).
# Uses the framework-shared :class:`NativeStateCache` from
# :mod:`adaptive_reflow.adapters._adapter_common` (the D.1 shrink
# target — see ``docs/audit/wave42-rectified-flow-cifar-shrink.md``).
# The attribute name ``_native_states`` is preserved so test seams
# and external callers (``tools.eval_rf_cifar``, etc.) keep working
# unchanged.
self._native_states: NativeStateCache = NativeStateCache(
    RF_CIFAR_NATIVE_STATES_MAXSIZE
)
```

Both helper methods are removed; all call sites now go through
`self._native_states.put(...)` / `self._native_states.get(...)`.
The `NativeStateCache` is byte-stable — its `put` method does exactly
what the inlined `_put_native_state` did (insert / move-to-end, evict
oldest when over `maxsize`). `_evict_native_state` was defined but
never called anywhere; the wrapper class supports `evict` for future
callers.

**Attribute-name preservation rationale:** `tests/test_adapters/test_rectified_flow_cifar.py`
has 4 seams that read `adapter._native_states[digest]` (lines 185,
191, 436, 450). Renaming to `_native_cache` would have forced test
edits across 4 sites — kept the name so the test file is untouched,
per the constraint "tests/test_adapters/test_rectified_flow_cifar.py
(modify if tests reference removed code)" — but the underlying *type*
is now `NativeStateCache` instead of `OrderedDict`. The 4 test seams
work because `NativeStateCache.__getitem__` forwards to its private
`_data[digest]` `OrderedDict`.

### 4. `torch_is_available` delegates to `_adapter_common.torch_is_available`

The local reimplementation used `importlib.util.find_spec("torch")`;
the shared helper uses a `try: import torch` probe. Both return the
same boolean for any realistic install state (the `find_spec` path
can succeed where the actual `import torch` fails only when the
module is partially installed, which is a corner case the test suite
already covers via `pytest.importorskip("torch")`). The shared helper
is the canonical version used by the other 6 adapters.

### 5. Updated import block

```python
from adaptive_reflow.adapters._adapter_common import (
    NativeStateCache,
    digest_state,
    kaiming_uniform,
    make_ref,
    memory_fraction_for,
    seed_from_ids,
    torch_is_available as _adapter_common_torch_is_available,
)
```

The `TensorRef` symbol was dropped from the `universal.state`
import — it was only used by the now-deleted `_make_ref`.

---

## Disjoint file scope (constraint respected)

Only touched:
- `adaptive_reflow/adapters/rectified_flow_cifar.py` (modify)
- `docs/audit/wave42-rectified-flow-cifar-shrink.md` (this NEW doc)

Not touched (per constraint):
- `framework/`, `scheduler/`, `paper_quantities`, `regression-vectors`,
  `test_claims`, other adapters, `adaptive_reflow/core/`.
- `tests/test_adapters/test_rectified_flow_cifar.py` — **no changes
  needed**; the existing 26 tests already call the public Protocol
  surface (`capabilities`, `build_initial_state`, `solve_ode`,
  `observe_endpoint`, `apply_restart_distribution`,
  `inject_forward_noise`, `export_trajectory`, `batched_inference`)
  and the 2 back-compat seams (`torch_is_available`,
  `_batched_torch_velocity_field`) remain importable.

---

## Verification

### `tests/test_adapters/test_rectified_flow_cifar.py`

```
26 passed, 3 warnings in 2.42s
```

The 26 tests cover the full protocol surface (capabilities
handshake, `build_initial_state` byte-determinism, synthetic vs
torch mode dispatch, `apply_restart_distribution` memory-fraction
math, `solve_ode` Euler + Heun integrators, byte-determinism across
seeds, `observe_endpoint` shape correctness, restart-blend, forward-
noise injection, trajectory export, batched_inference shape,
batch-torch CUDA device placement, etc.).

### Module import smoke check

```
$ .venvs/flowmol3_venv/bin/python -c \
    "from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter, torch_is_available, rectified_flow_cifar_resolve_weights_path; print('imports ok')"
imports ok

$ .venvs/flowmol3_venv/bin/python -c \
    "from adaptive_reflow.adapters.rectified_flow_cifar import _batched_torch_velocity_field; print('batched_torch_velocity_field ok')"
batched_torch_velocity_field ok
```

External tool callers (`tools/eval_rf_cifar.py`,
`tools/run_rf_cifar_ablation.py`, `tools/run_regression_vector_audit.py`,
`tools/run_sota_cifar_experiment.py`, `tools/run_controlled_audit.py`)
all continue to import cleanly because the public surface
(`RectifiedFlowCIFARAdapter`, `RectifiedFlowCIFARCapabilities`,
`default_rectified_flow_cifar_adapter`,
`rectified_flow_cifar_resolve_weights_path`,
`torch_is_available`, the 30+ `RF_CIFAR_*` constants) is unchanged.

---

## Net effect

| Metric | Before | After | Delta |
|---|---|---|---|
| Adapter LOC (`rectified_flow_cifar.py`) | 1356 | 1317 | **−39** |
| Module-level helpers removed | — | 4 | `_seed_from_ids`, `_digest_state`, `_make_ref`, `_validate_state_shape` |
| Instance methods removed | — | 2 | `_put_native_state`, `_evict_native_state` |
| Inlined closures removed | — | 1 | inline `kaiming` closure in `_random_init_synthetic_weights` |
| `OrderedDict` import dropped | — | — | `from collections import OrderedDict` removed |
| `TensorRef` import dropped | — | — | (only used by removed `_make_ref`) |
| Back-compat aliases kept | — | 2 | `torch_is_available`, `_batched_torch_velocity_field` |
| New imports from `_adapter_common` | — | 4 | `NativeStateCache`, `kaiming_uniform`, `torch_is_available`, (already had `seed_from_ids`/`digest_state`/`make_ref`) |
| Test seams preserved | — | 4 | `adapter._native_states[digest]` (lines 185, 191, 436, 450) — works because `NativeStateCache.__getitem__` |

The adapter now reuses 6 helpers from `_adapter_common`
(`NativeStateCache`, `digest_state`, `kaiming_uniform`, `make_ref`,
`memory_fraction_for`, `seed_from_ids`, plus the delegated
`torch_is_available`) and keeps only the 2 helpers that external
tests/tools import by name. No byte-level regression — all 26 tests
pass.

---

## Notes

- The `NativeStateCache` swap is **byte-deterministic**: the LRU
  insert + move-to-end + popitem-last-false semantics are exactly
  what the inlined `_put_native_state` did, and the cache survives
  through `__getitem__` / `get` with the same key ordering. Native-
  state digests produced by `solve_ode` / `observe_endpoint` /
  `apply_restart_distribution` / `inject_forward_noise` are
  bit-identical to the prior inlined version for any fixed input.
- The `kaiming_uniform` delegation is **byte-deterministic**: same
  RNG, same `uniform(-bound, bound, size=(fan_in, fan_out))` call
  shape, same advancement order (W1 → W2 → t_bias). The synthetic-
  init endpoints will be bit-identical to the prior inlined version
  for any fixed `(hidden, seed)` pair.
- The `OrderedDict` import was the *only* use of `OrderedDict` in
  the file; dropping it is a clean dead-import removal.
- The torch-velocity-field shim (`_torch_velocity_field`),
  batched-velocity shims (`_batched_synthetic_velocity_field`,
  `_batched_torch_velocity_field`), and the DDPM++ UNet builder
  (`_build_torch_unet_ddpmpp`) were left in place — these are
  genuinely adapter-specific (the UNet topology matches Liu 2022 §3.2
  and is NOT a generic framework helper) and were already known
  load-bearing for the SOTA FID reproduction. Their bodies are
  model-specific, not glue, so the D.1 shrink criterion does not
  apply.
- The `_load_torch_unet` ckpt loader was left in place for the same
  reason — its gnobitab detection (`module.all_modules.` prefix) is
  adapter-specific to the Score-SDE DDPM++ ckpt format published by
  the Liu 2022 authors. The framework-core `ckpt_loader.resolve_candidate_paths`
  has a different API (`name`+`stem`+`extensions` → list of paths)
  than the adapter's `rectified_flow_cifar_resolve_weights_path`
  (`data_dir` + full-filename `candidates` tuple → first existing
  Path); rewriting the adapter's helper would change behaviour
  without saving any code (the 17-line body is specific to the
  rf_cifar weights-candidate order: `cifar10_rf.pth` →
  `rectified_flow_cifar10.safetensors` → `...pth` → `...pt`).
