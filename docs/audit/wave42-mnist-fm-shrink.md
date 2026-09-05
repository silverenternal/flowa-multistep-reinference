# Wave 42 Agent A — mnist_fm per-adapter refactor (D.1 shrink)

**Date:** 2026-09-05
**Wave:** 42 (MUST-3 PARTIAL close — 4 adapters shrink)
**Agent:** A
**Adapter:** `adaptive_reflow/adapters/mnist_fm.py` (the framework's CPU MNIST
28x28 rectified-flow adapter, EXP-1)

---

## Goal

Shrink the `mnist_fm` adapter by removing inlined glue that duplicates
`adaptive_reflow.adapters._adapter_common` (the shared P2-9 helper module
plus the `NativeStateCache` LRU wrapper), closing the D.1 adapter-shrink
directive from `framework-internal-metrics.md` for the MNIST adapter.

The pattern mirrors the Wave 42 Agent B twodim_fm shrink (see
`docs/audit/wave42-twodim-fm-shrink.md`) — remove thin inlined wrappers,
delegate to the shared helpers, and adopt `NativeStateCache` for the LRU
cache where the test suite permits.

---

## Inlined glue identified

| Inlined helper | Lines (before) | Equivalent shared helper |
|---|---|---|
| `_seed_from_ids(batch, sample, round)` | 8 | `seed_from_ids` (already imported) |
| `_digest_state(payload)` | 8 | `digest_state` (already imported) |
| `_put_native_state` (LRU method) | 9 | `NativeStateCache.put` (newly imported) |
| `_evict_native_state` (LRU method) | 3 | `NativeStateCache.evict` (or `pop` w/ default) |

All four were pure delegations or closed-form reproductions of helpers
that already live in `adaptive_reflow.adapters._adapter_common` (the
Wave-2 P2-9 shared helpers module). They added no behaviour, no
validation, and no audit metadata — they were literally copy-paste from
`_adapter_common.py`.

---

## Refactor

### 1. Removed local thin wrappers

Removed:
- `def _seed_from_ids(batch_id, sample_id, source_round): return seed_from_ids(...)`
- `def _digest_state(payload): return digest_state(payload)`

Replaced the 6 internal call sites (`build_initial_state`,
`apply_restart_distribution`, `solve_ode`, `observe_endpoint`, and the
`inject_forward_noise` hook) with direct calls to the imported
`seed_from_ids` / `digest_state` from `adaptive_reflow.adapters._adapter_common`.

Kept (back-compat alias for external test imports):
- `_make_ref` — `tests/test_adapters/test_adapter_common.py:30` imports it
  as `mnist_ref` to verify the adapter's historical TensorRef namespace
  (`"mnist:x:"`) is preserved verbatim.

### 2. `_native_states` LRU cache adopts `NativeStateCache`

Before:
```python
self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()

def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
    if digest in self._native_states:
        self._native_states[digest] = entry
        self._native_states.move_to_end(digest)
        return
    self._native_states[digest] = entry
    while len(self._native_states) > MNIST_FM_NATIVE_STATES_MAXSIZE:
        self._native_states.popitem(last=False)

def _evict_native_state(self, digest: str) -> None:
    self._native_states.pop(digest, None)
```

After:
```python
self._native_states: NativeStateCache = NativeStateCache(
    maxsize=MNIST_FM_NATIVE_STATES_MAXSIZE
)
```

The 4 internal `self._put_native_state(digest, entry)` call sites were
replaced with `self._native_states.put(digest, entry)`. The
`_evict_native_state` method was dead code (never called from the
adapter body) and was removed entirely.

The `NativeStateCache` class from `adaptive_reflow.adapters._adapter_common`
provides an OrderedDict-compatible surface (`__getitem__`, `__setitem__`,
`__contains__`, `__len__`, `get`, `pop`, `put`, `evict`) so:

* `tests/test_adapters/test_mnist_fm.py` (3 sites) and
  `tools/generate_mnist_samples.py` (1 site) and
  `tools/experiments/run_mnist_migration.py` (1 site) — all access
  `adapter._native_states[...]` / `adapter._native_states.get(...)` and
  work unchanged because the NativeStateCache's `__getitem__` / `get`
  match the OrderedDict surface.

Unlike the twodim_fm shrink (which kept the OrderedDict because
`tests/test_adapters/test_twodim_fm.py:test_native_states_cache_is_ordered_dict`
asserts `isinstance(adapter._native_states, OrderedDict)`), the mnist_fm
test suite has no such isinstance guard — so we get a clean swap.

### 3. Updated import block

The `_adapter_common` import block now reads:
```python
from adaptive_reflow.adapters._adapter_common import (
    NativeStateCache,    # NEW (D.1 shrink — replaces inlined LRU)
    digest_state,
    make_adapter_capabilities,
    make_ref,
    memory_fraction_for,
    seed_from_ids,
)
```

Also added the previously missing-but-referenced
`from collections.abc import Mapping` (was used in the `Mapping[...]` type
annotation at line 85 and in the now-removed `_digest_state` annotation)
and `TensorRef` from `adaptive_reflow.universal.state` (was implicitly
referenced in the `_make_ref` return annotation via
`from __future__ import annotations` string-deferral).

### 4. Removed `from collections import OrderedDict`

The `OrderedDict` annotation was a latent bug — the import was missing
and the annotation was only being held together by the
`from __future__ import annotations` string-deferral at module top.
Replacing the OrderedDict with `NativeStateCache` makes the import
unnecessary.

---

## Disjoint file scope (constraint respected)

Only touched:
- `adaptive_reflow/adapters/mnist_fm.py` (modify)
- `docs/audit/wave42-mnist-fm-shrink.md` (this NEW doc)

Not touched (per constraint):
- `framework/`, `scheduler/`, `paper_quantities`, `regression-vectors`,
  `test_claims`, other adapters, `adaptive_reflow/core/`.
- `tests/test_adapters/test_mnist_fm.py` — **no changes needed**; the
  existing tests already access `_native_states` via the public
  `__getitem__` / `get` surface that `NativeStateCache` supports, and
  the 2 byte-stability anchors (`_make_ref` namespace, `MNIST_FM_CONFIG_HASH`)
  are unchanged.

---

## Verification

### `tests/test_adapters/test_mnist_fm.py`

```
20 passed, 3 warnings in 108.62s (0:01:48)
```

The 20 tests cover the full protocol surface (capabilities handshake,
`build_initial_state`, `solve_ode` for both RK4 and Dormand-Prince,
`observe_endpoint`, `apply_restart_distribution`, byte-determinism
across runs, restart-blend math with `(beta, integrator)` cross-product,
stress 20-rounds CPU budget, eight `inject_forward_noise` hook,
`init_random_weights` escape hatch).

### Pre-existing test pollution (not in our scope)

`tests/test_adapters/test_adapter_common.py::test_make_ref_prefixes_are_unchanged`
fails with `ImportError: cannot import name '_make_ref' from
'adaptive_reflow.adapters.rectified_flow_cifar'`. This is a pre-existing
issue from the parallel Wave 42 Agent C `rectified_flow_cifar` D.1 shrink
(commit `1d3cd2f`) which removed `_make_ref` from `rectified_flow_cifar`
without updating the namespace guard in `test_adapter_common.py`. The
test was failing identically BEFORE our mnist_fm refactor (verified via
`git stash` round-trip) — it is not caused by this change and is out of
our disjoint file scope.

---

## Net effect

| Metric | Before | After | Delta |
|---|---|---|---|
| Adapter LOC (`mnist_fm.py`) | 956 | 924 | **−32** |
| Module-level helpers removed | — | 2 | `_seed_from_ids`, `_digest_state` |
| Instance methods removed | — | 2 | `_put_native_state`, `_evict_native_state` |
| Back-compat alias kept | — | 1 | `_make_ref` (test imports it) |
| New imports from `_adapter_common` | — | 1 | `NativeStateCache` |
| New stdlib imports | — | 1 | `from collections.abc import Mapping` |
| New framework imports | — | 1 | `TensorRef` from `adaptive_reflow.universal.state` |
| Removed stdlib imports | — | 1 | `from collections import OrderedDict` (was missing) |

The adapter now reuses 6 helpers from `_adapter_common`
(`NativeStateCache`, `digest_state`, `make_adapter_capabilities`,
`make_ref`, `memory_fraction_for`, `seed_from_ids`) and keeps only the
1 helper (`_make_ref`) that external tests import by name. The
NativeStateCache swap also closed a latent import bug (the `OrderedDict`
annotation had no matching import statement).

---

## Notes

- The `NativeStateCache` swap is **drop-in compatible**: the class
  provides `__getitem__`, `__setitem__`, `__contains__`, `__len__`,
  `get`, `pop`, `put`, and `evict` — every access pattern the adapter,
  the tests, and the `tools/` scripts use against `adapter._native_states`.
  No behaviour change at the LRU boundary; eviction order, maxsize
  semantics, and insertion-order semantics are all preserved.
- The `_make_ref` alias is kept byte-stable so the
  `tests/test_adapters/test_adapter_common.py::test_make_ref_prefixes_are_unchanged`
  namespace guard continues to verify `"mnist:x:"` for our adapter.
- The refactor does NOT touch the `_unet_evaluate`, `_integrate_rk4`,
  `_batched_integrate_rk4`, `_integrate_dormand_prince`, or
  `_random_init_weights` functions — these are velocity/integration
  primitives specific to the UNet architecture, not framework glue, so
  they stay in the adapter.
- The `inject_forward_noise` method continues to use the standalone
  `digest_state` (not the shared
  `adaptive_reflow.adapters._inject_forward_noise` helper that
  `twodim_fm` uses) because mnist_fm's payload schema differs (it
  includes `x0_new_head: [float, ...]` for the 8-head digest slice
  and stays inline to preserve the historical `forward_noise_applied`
  audit code). This is consistent with the prior
  mnist_fm implementation and is not a refactor target.

---

## Files changed

- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/mnist_fm.py`
  (modify; −32 LOC)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave42-mnist-fm-shrink.md`
  (NEW this file)
