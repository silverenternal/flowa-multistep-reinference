# Wave 42 Agent B — twodim_fm per-adapter refactor (D.1 shrink)

**Date:** 2026-09-05
**Wave:** 42 (MUST-3 PARTIAL close — 4 adapters shrink)
**Agent:** B
**Adapter:** `adaptive_reflow/adapters/twodim_fm.py` (the framework's headline
4.6x W2 improvement on Two Moons)

---

## Goal

Shrink the `twodim_fm` adapter by removing inlined glue that duplicates
`adaptive_reflow.adapters._adapter_common` (the shared P2-9 helper module),
closing the D.1 adapter-shrink directive from `framework-internal-metrics.md`.

---

## Inlined glue identified

| Inlined helper | Lines (before) | Equivalent shared helper |
|---|---|---|
| `_seed_from_ids(batch, sample, round)` | 3 | `seed_from_ids` (already imported) |
| `_digest_state(payload)` | 4 | `digest_state` (already imported) |
| `_random_init_weights` inline `kaiming` closure | 8 | `kaiming_uniform` (newly imported) |

All three were pure delegations / closed-form reproductions of helpers that
already live in `adaptive_reflow.adapters._adapter_common` (the Wave-2 P2-9
shared helpers module). They added no behaviour, no validation, and no audit
metadata — they were literally copy-paste from `_adapter_common.py`.

---

## Refactor

### 1. Removed local thin wrappers

Removed:
- `def _seed_from_ids(batch_id, sample_id, source_round): return seed_from_ids(...)`
- `def _digest_state(payload): return digest_state(payload)`

Replaced the 3 internal call sites (`build_initial_state`,
`apply_restart_distribution`, `solve_ode`, `observe_endpoint`) with direct
calls to the imported `seed_from_ids` / `digest_state` from
`adaptive_reflow.adapters._adapter_common`.

Kept (back-compat aliases for external test imports):
- `_make_ref` — `tests/test_adapters/test_adapter_common.py:32` imports it
  as `td_ref` to verify the adapter's historical TensorRef namespace
  (`"twodim:xy:"`) is preserved verbatim.
- `_batched_integrate_rk4` — `tests/test_algo_uplifts/test_noise_injection.py:64`
  imports it for the C.5 controlled-noise-injection Pareto sweep.
- `_blend_endpoint_with_prior` — `tests/test_algorithm/test_blender.py:36`
  and `tests/test_algorithm/test_blender_delegation.py:394` import it as a
  byte-exact reference for the LinearBlender delegation tests.

### 2. `_random_init_weights` delegates to `kaiming_uniform`

Before:
```python
def kaiming(fan_in, fan_out):
    bound = np.sqrt(6.0 / float(fan_in))
    return np.asarray(rng.uniform(-bound, bound, size=(fan_in, fan_out)), dtype=np.float64)

return {
    "W1": kaiming(3, hidden),
    ...
}
```

After:
```python
return {
    "W1": kaiming_uniform(rng, 3, hidden),
    ...
}
```

Byte-equivalence holds because the new helper's body is literally the same
``rng.uniform(-bound, bound, size=(fan_in, fan_out))`` formula with the
same RNG state advancement order (`W1`, `W2`, `W3` are drawn in sequence).
The shared helper is the canonical He-uniform used by the other 6
adapters in `self_flow`, `mnist_fm`, `rectified_flow_cifar`, `freqflow`,
`hidream_i1`, and `kanzi`.

### 3. Updated import block

Added `kaiming_uniform` to the existing `_adapter_common` import block:
```python
from adaptive_reflow.adapters._adapter_common import (
    digest_state,
    kaiming_uniform,   # NEW (D.1 shrink)
    make_ref,
    memory_fraction_for,
    seed_from_ids,
)
```

---

## Disjoint file scope (constraint respected)

Only touched:
- `adaptive_reflow/adapters/twodim_fm.py` (modify)
- `docs/audit/wave42-twodim-fm-shrink.md` (this NEW doc)

Not touched (per constraint):
- `framework/`, `scheduler/`, `paper_quantities`, `regression-vectors`,
  `test_claims`, other adapters, `adaptive_reflow/core/`.
- `tests/test_adapters/test_twodim_fm.py` — **no changes needed**; the
  existing tests already call `digest_state` / `seed_from_ids` /
  `kaiming_uniform` semantics through the public `TwoDimFMAdapter`
  surface and the 3 back-compat wrappers remain available.

---

## Verification

### `tests/test_adapters/test_twodim_fm.py`

```
17 passed, 3 warnings in 7.54s
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
72 passed, 24 warnings in 20.82s
```

All pass — the back-compat `_make_ref`, `_batched_integrate_rk4`, and
`_blend_endpoint_with_prior` aliases are still importable from
`adaptive_reflow.adapters.twodim_fm` and produce byte-identical output
to the legacy inline implementations.

---

## Net effect

| Metric | Before | After | Delta |
|---|---|---|---|
| Adapter LOC (`twodim_fm.py`) | 1473 | 1466 | **−7** |
| Module-level helpers removed | — | 2 | `_seed_from_ids`, `_digest_state` |
| Inlined closures removed | — | 1 | `_random_init_weights` inline `kaiming` |
| Back-compat aliases kept | — | 3 | `_make_ref`, `_batched_integrate_rk4`, `_blend_endpoint_with_prior` |
| New imports from `_adapter_common` | — | 1 | `kaiming_uniform` |

The adapter now reuses 5 helpers from `_adapter_common`
(`digest_state`, `kaiming_uniform`, `make_ref`, `memory_fraction_for`,
`seed_from_ids`) and keeps only the 3 helpers that external tests
import by name. No byte-level regression — all 89 dependent tests
(17 + 72) pass.

---

## Notes

- The kaiming_uniform delegation is **byte-deterministic**: same RNG,
  same `uniform(low, high, size=(fan_in, fan_out))` call shape, same
  advancement order (W1 → W2 → W3). The synthetic-init endpoints will
  be bit-identical to the prior inlined version for any fixed
  `(hidden, seed)` pair.
- The refactor does NOT touch the `_native_states` LRU cache — the
  `test_native_states_cache_is_ordered_dict` test asserts
  `isinstance(adapter._native_states, OrderedDict)`, which forbids
  swapping the OrderedDict for the `NativeStateCache` wrapper object
  that `_adapter_common` also provides. The LRU `_put_native_state` /
  `_evict_native_state` methods therefore stay as-is.
- The `inject_forward_noise` indirection already goes through
  `adaptive_reflow.adapters._inject_forward_noise` (a separate P1-8
  helper) — no change.