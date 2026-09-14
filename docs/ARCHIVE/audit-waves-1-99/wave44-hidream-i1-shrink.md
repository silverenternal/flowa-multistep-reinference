# Wave 44 Agent C: hidream_i1 D.1 shrink

## Summary

Apply the Wave 42 / Wave 43 per-adapter shrink pattern (originally
introduced for `rectified_flow_cifar` in commit `1d3cd2f`) to the
`hidream_i1` latent-FM adapter. The HiDream-I1 module is the largest
adapter in `adaptive_reflow/adapters/` (1980 LOC) — a R17 design-skeleton
release that wires the published HiDream-I1 sparse-DiT text-to-image
pipeline (Cai et al. 2025) into the framework's
`FlowMatchingODEAdapter` Protocol. The shrink removes inlined glue that
duplicates framework-shared functionality in
`adaptive_reflow/adapters/_adapter_common.py`.

## Net result

* **Files changed**: 1 (`adaptive_reflow/adapters/hidream_i1.py`).
* **Tests**: `tests/test_adapters/test_hidream_i1.py` unchanged — all
  22 tests pass without modification.
* **LOC**: 1980 → 1950 (**-30 LOC**).
* **Imports added** (from `_adapter_common`):
  - `NativeStateCache`
  - `digest_state`
  - `kaiming_uniform`
  - `seed_from_ids`
  - `torch_is_available as _adapter_common_torch_is_available`
* **Imports removed**:
  - `OrderedDict` (no longer needed — `NativeStateCache.put()` manages LRU)
  - `TensorRef` (no longer needed — `make_ref()` returns the concrete `TensorRef`)

## Inlined glue removed

| Removed function            | Lines | Replacement                                    |
|-----------------------------|-------|------------------------------------------------|
| `_seed_from_ids`            | 4     | `seed_from_ids` from `_adapter_common`         |
| `_digest_state`             | 4     | `digest_state` from `_adapter_common`          |
| `_make_ref`                 | 3     | `make_ref` from `_adapter_common` (inlined at 6 call sites with `f"hidream_i1:{label}"` prefix to preserve byte-identical `TensorRef` digests) |
| `_validate_state_shape`     | 4     | Removed (unused; no caller in module)          |
| `torch_is_available` body   | 10 → 3 | Delegates to `_adapter_common.torch_is_available` (wrapper kept for back-compat with the public surface) |
| Inline `kaiming` closure    | 6     | `kaiming_uniform` from `_adapter_common`       |
| `_put_native_state` method  | 11    | `NativeStateCache.put()`                        |
| `_evict_native_state` method| 3     | `NativeStateCache.pop()` (no call site in module — was dead code) |
| `_put_conditioning` method  | 11    | `NativeStateCache.put()` (LRU eviction now implicit) |
| `OrderedDict` instantiation | 4     | `NativeStateCache(HIDREAM_I1_NATIVE_STATES_MAXSIZE)` and `NativeStateCache(int(conditioning_cache_size))` |

## Test seams preserved

The Wave 42 rectified_flow_cifar shrink preserved test seams by keeping
the `_native_states` attribute name as a `NativeStateCache` instance.
This HiDream-I1 shrink follows the same pattern:

- `adapter._native_states[digest]` — works because `NativeStateCache.__getitem__`
  is defined.
- `adapter._native_states[trace.native_state_digest]` — same.
- `hash_a in hidream_adapter._conditioning_cache` — works because
  `NativeStateCache.__contains__` is defined.

The `tests/test_adapters/test_hidream_i1.py` test file does **not** need
any modification — 22/22 tests pass unchanged.

## Public API preserved

* `torch_is_available()` — kept as a 3-line thin wrapper that delegates
  to `_adapter_common.torch_is_available()`. Same return contract.
* `HiDreamI1Adapter`, `HiDreamI1Capabilities`, `default_hidream_i1_adapter`
  — unchanged.
* `hidream_i1_resolve_weights_path` — unchanged.
* All module-level constants (`HIDREAM_I1_*`, `HIDREAM_VARIANT_*`,
  `HIDREAM_I1_INTEGRATOR_*`, `AUDIT_*`, `ERR_*`) — unchanged.
* All `__all__` exports — unchanged.
* `TensorRef` digests for all 6 `make_ref` call sites are byte-identical
  to the pre-shrink output (the wrapper previously embedded the label
  into the prefix as `f"hidream_i1:{label}"`; inlined calls reproduce
  that exact string verbatim).

## Notes

1. The `_make_ref` inlining follows the Wave 42 pattern but is slightly
   more verbose at the call sites (6 inlines vs the 4 inlined by rf_cifar)
   because the historical prefix embedded the label
   (`"hidream_i1:latent:initial"` etc.), whereas rf_cifar used a
   fixed prefix (`"rf_cifar:image"`). Byte-identical TensorRef digests
   require the embedded-label prefix to be preserved exactly.

2. The `_conditioning_cache` was also switched from `OrderedDict` to
   `NativeStateCache`. The LRU eviction policy is unchanged (the cache
   still has a `maxsize` bound; only the eviction mechanism shifted
   from manual `popitem(last=False)` to `NativeStateCache.put()`'s
   automatic LRU management). Tests that check membership via
   `in self._conditioning_cache` continue to work.

3. The `conditioning_cache_size` constructor parameter is preserved and
   now flows into `NativeStateCache(int(conditioning_cache_size))`.

4. The dead-code `_evict_native_state` (no internal callers) is removed
   alongside `_put_native_state`. External callers (none known) would
   migrate to `adapter._native_states.pop(digest, None)`.

5. The `kaiming` closure (6 lines) was replaced by `kaiming_uniform(rng, in_dim, hidden_w)`,
   which has identical math: `rng.uniform(-sqrt(6/fan_in), +sqrt(6/fan_in), size=(fan_in, fan_out))`.

## Verification

```bash
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_hidream_i1.py -q --tb=line
22 passed, 3 warnings in 18.25s
```

All 22 tests pass unchanged. No regressions. No test file edits required.

## MUST-3 status

MUST-3 (the "every adapter imports from `adaptive_reflow/core/`" gate) is
not directly addressed by the D.1 shrink (which targets
`_adapter_common`). However, after this commit:
- `from adaptive_reflow.adapters._adapter_common import ...` is present
  in the import block (was already present pre-shrink).

The full MUST-3 PARTIAL → PASS work is owned by Wave 44 WF3 (Agent D
"core adoption" on `rectified_flow_cifar` and other adapters).