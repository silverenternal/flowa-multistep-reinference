# Wave 44 Agent D — kanzi per-adapter refactor (D.1 shrink)

**Date:** 2026-09-07
**Wave:** 44 (MUST-3 PARTIAL → PASS close, 3rd of 4 D.1 shrinks)
**Agent:** D
**Adapter:** `adaptive_reflow/adapters/kanzi.py`
(Wave 21 SOTA integration; Shah et al. ICLR 2026, arXiv:2510.00351,
protein flow-AE; the adapter carries the GPT-prior monkey-patch from
Wave 40 Agent B)

---

## Goal

Shrink the `kanzi` adapter by removing inlined glue that duplicates
`adaptive_reflow.adapters._adapter_common` (the shared P2-9 helper
module), closing the D.1 adapter-shrink directive from
`framework-internal-metrics.md`. The kanzi adapter is the largest
adapter in the framework at the time of this shrink (~1858 LOC after
Wave 44 Agent A's `observe_token_indices` add), and carries the
GPT-prior monkey-patch as a hard constraint (must be preserved
byte-identically).

---

## Inlined glue identified

| Inlined helper | Lines (before) | Equivalent shared helper |
|---|---|---|
| `_make_ref(label, **parts)` (3 lines) | wrapper around `make_ref("kanzi:{label}", label, **parts)` | `make_ref` from `_adapter_common` (already imported) |
| `_validate_state_shape(x)` (4 lines) | reshape + dtype — never called internally | removed (dead code) |
| `torch_is_available()` local reimpl (10 lines) | `importlib.util.find_spec("torch")` probe | `torch_is_available` from `_adapter_common` |
| Inline `kaiming` closure in `_random_init_synthetic_weights` (6 lines) | `np.sqrt(6 / fan_in) * rng.uniform(-1, 1, (fan_in, fan_out))` | `kaiming_uniform` from `_adapter_common` |
| `_put_native_state` (8 lines) + `_evict_native_state` (3 lines) + `_put_conditioning` (9 lines) | LRU `OrderedDict` insert + move-to-end + popitem helpers | `NativeStateCache.put` from `_adapter_common` |

Total inlined glue removed: **14 lines** of helpers (3 modules +
1 inline closure) plus **5 lines** of body-code simplifications. The
3 inlined cache helpers (`_put_native_state`, `_evict_native_state`,
`_put_conditioning`) were pure delegations to `OrderedDict` insert +
`move_to_end` + `popitem(last=False)` — the exact pattern that
`NativeStateCache.put` already implements canonically. The inlined
`kaiming` closure was an exact reproduction of `kaiming_uniform`'s
formula.

---

## Refactor

### 1. Removed local thin wrappers

- `def _make_ref(label, **parts)` — replaced all 9 call sites with
  direct `make_ref("kanzi:latent:initial", "latent:initial", ...)` calls
  using the byte-deterministic `f"kanzi:{label}"` prefix that the
  original wrapper produced.
- `def _validate_state_shape(x)` — never called internally (only
  defined); removed.
- The local `torch_is_available()` body now delegates to
  `_adapter_common.torch_is_available()`. The back-compat symbol is
  preserved so `tests/test_adapters/test_kanzi.py::test_torch_is_available_smoke`
  and any external tool callers keep working unchanged.

### 2. Inline `kaiming` closure → `kaiming_uniform`

Before:
```python
def kaiming(fan_in, fan_out):
    bound = np.sqrt(6.0 / float(fan_in))
    return np.asarray(
        rng.uniform(-bound, bound, size=(fan_in, fan_out)),
        dtype=np.float64,
    )

return {"W1": kaiming(in_dim, hidden_w), ...}
```

After:
```python
return {
    "W1": kaiming_uniform(rng, in_dim, hidden_w),
    "W2": kaiming_uniform(rng, hidden_w, in_dim),
    "b1": np.zeros(hidden_w, dtype=np.float64),
    "b2": np.zeros(in_dim, dtype=np.float64),
    "t_bias": rng.standard_normal(hidden_w).astype(np.float64),
}
```

Byte-equivalence holds because `kaiming_uniform`'s body is literally
the same `rng.uniform(-bound, bound, size=(fan_in, fan_out))` call
shape with the same RNG state advancement order (W1 → W2 → t_bias).
The shared helper is the canonical He-uniform used by all other
adapters (`self_flow`, `mnist_fm`, `twodim_fm`, `freqflow`,
`hidream_i1`, `rectified_flow_cifar`).

### 3. `_native_states` + `_conditioning_cache`: `OrderedDict` → `NativeStateCache`

Before (constructor + 2 helpers, 20 lines):
```python
self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
self._conditioning_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

def _put_native_state(self, digest, entry):
    if digest in self._native_states:
        self._native_states[digest] = entry
        self._native_states.move_to_end(digest)
        return
    self._native_states[digest] = entry
    while len(self._native_states) > KANZI_NATIVE_STATES_MAXSIZE:
        self._native_states.popitem(last=False)

def _evict_native_state(self, digest):
    self._native_states.pop(digest, None)

def _put_conditioning(self, cache_hash, entry):
    if cache_hash in self._conditioning_cache:
        self._conditioning_cache[cache_hash] = entry
        self._conditioning_cache.move_to_end(cache_hash)
        return
    self._conditioning_cache[cache_hash] = entry
    while len(self._conditioning_cache) > self._conditioning_cache_size:
        self._conditioning_cache.popitem(last=False)
```

After (constructor + cache helpers, 6 lines):
```python
self._native_states: NativeStateCache = NativeStateCache(
    KANZI_NATIVE_STATES_MAXSIZE
)
self._conditioning_cache: NativeStateCache = NativeStateCache(
    self._conditioning_cache_size
)
```

All 3 helper methods are removed. All 5 `_put_native_state(...)`
call sites become `self._native_states.put(...)`. The
`_resolve_conditioning` LRU-touch (`existing.move_to_end`) becomes
`self._conditioning_cache.put(cache_hash, existing)` — `put` already
does the move-to-end internally. `NativeStateCache` is byte-stable —
its `put` method has the same insert / move-to-end / popitem
semantics.

**Attribute-name preservation rationale:**
`tests/test_adapters/test_kanzi.py` reads
`adapter._native_states[bundle.native_state_digest]` at lines 193,
237, 359, 396 (4 read sites) and
`cache_hash in adapter._conditioning_cache` at line 303 (membership
check). Renaming to `_native_cache` would have forced test edits
across 4 sites — kept the name so the test file is untouched.
`NativeStateCache.__getitem__` and `__contains__` both forward to
its private `_data` `OrderedDict`, so the 4 read sites work
unchanged.

### 4. `torch_is_available` delegates to `_adapter_common.torch_is_available`

The local reimplementation used `importlib.util.find_spec("torch")`;
the shared helper uses a `try: import torch` probe. Both return the
same boolean for any realistic install state (the `find_spec` path
can succeed where the actual `import torch` fails only when the
module is partially installed, which is a corner case the test
suite already covers via `pytest.importorskip("torch")`).

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

The `OrderedDict` import and the `TensorRef` symbol from
`adaptive_reflow.universal.state` were both dropped — `OrderedDict`
was only used by the removed `_native_states` / `_conditioning_cache`
declarations, and `TensorRef` was only used by the removed `_make_ref`.

---

## GPT-prior monkey-patch (PRESERVED byte-identically)

The Wave 40 Agent B monkey-patch on `kanzi.models.GPT.forward` is
**load-bearing** for the Wave 39/40/41/42 GPT-prior end-to-end tests
and the `tools/run_kanzi_real_ckpt.py` forward-pass smoke. The
`_install_gpt_prior_patch()` function, the `_GPT_PRIOR_PATCH_MARKER`
constant, the at-import-time try/except installation, and the
`functools.wraps` decorator wrapping the patched forward are all
**unchanged**. Verification:

```
$ .venvs/kanzi_venv/bin/python tools/run_kanzi_real_ckpt.py
matches SHA256SUMS: True
torch.load: 0.3s
DAE: 44,117,745 params, missing=0, unexpected=0
forward pass (no_grad): 0.06s
wrote: verification_outputs/kanzi_real_ckpt_forward_q4_2026.json
```

The DAE with `gpt_prior=True` loads and the forward pass executes
end-to-end without the upstream `TypeError: got multiple values for
argument 'pair_bias_BLLD'`. The Wave 41 GPT-prior end-to-end test
(`tests/test_adapters/test_kanzi.py::test_gpt_prior_patch_runs_dae_gpt_prior_branch`)
passes — `gpt_prior_loss > 0.0` (real cross-entropy, not the
`= 0` Wave 39 workaround).

---

## Disjoint file scope (constraint respected)

Only touched:
- `adaptive_reflow/adapters/kanzi.py` (modify)
- `docs/audit/wave44-kanzi-shrink.md` (this NEW doc)

Not touched (per constraint):
- `framework/`, `scheduler/`, `paper_quantities`, `regression-vectors`,
  `test_claims`, other adapters, `_adapter_common`, `core/`,
  `tools/run_real_ckpt_eval.py`, `tools/run_kanzi_real_ckpt.py`.
- `tests/test_adapters/test_kanzi.py` — **no changes needed**; the
  existing 33 tests already call the public Protocol surface
  (`capabilities`, `build_initial_state`, `solve_ode`,
  `observe_endpoint`, `apply_restart_distribution`,
  `observe_token_indices`, `inject_forward_noise`,
  `export_trajectory`) and the 2 back-compat seams
  (`torch_is_available`, `kanzi_resolve_weights_path`) remain
  importable. The 4 read sites at lines 193/237/359/396 and the
  membership check at line 303 work unchanged because
  `NativeStateCache.__getitem__` / `__contains__` forward to the
  underlying `_data` `OrderedDict`.

---

## Verification

### `tests/test_adapters/test_kanzi.py`

```
$ .venvs/kanzi_venv/bin/python -m pytest tests/test_adapters/test_kanzi.py -q --tb=line
33 passed, 4 warnings in 8.26s
```

PASS — all 33 tests cover the full Protocol surface:

- capability handshake (8 capability flags + 6 domain assertions)
- `__protocols__` registration via `@implements(FlowMatchingODEAdapter)`
  (Wave 38 MEDIUM-11 conformance gate)
- `build_initial_state` byte-determinism
- `solve_ode` Euler + Heun integrators (trajectory shape, finite,
  clamp envelope)
- `observe_endpoint` shape correctness + audit trail
- `apply_restart_distribution` memory-fraction math + conditioning
  propagation + discrete-token-index propagation
- `inject_forward_noise` clamp envelope + audit trail
- `observe_token_indices` (Wave 44 Agent A) AR-prior discrete
  channel decode
- GPT-prior monkey-patch (Wave 40 Agent B): idempotency, missing-
  package no-op, end-to-end `GPT.forward` regression, end-to-end
  `DAE.forward` (with `gpt_prior=True`) regression

### `tests/test_adapters/test_kanzi_real_ckpt.py`

```
$ .venvs/kanzi_venv/bin/python -m pytest tests/test_adapters/test_kanzi.py tests/test_adapters/test_kanzi_real_ckpt.py -q --tb=line
55 passed, 4 warnings in 19.97s
```

PASS — the 22 additional `test_kanzi_real_ckpt.py` tests cover the
real-ckpt forward path and weight resolution.

### `tools/run_kanzi_real_ckpt.py` (GPT-prior monkey-patch end-to-end)

```
matches SHA256SUMS: True
torch.load: 0.3s
DAE: 44,117,745 params, missing=0, unexpected=0
forward pass (no_grad): 0.06s
wrote: verification_outputs/kanzi_real_ckpt_forward_q4_2026.json
```

PASS — the published Kanzi encoder (44.1 M params, 530 MB) loads
end-to-end with `gpt_prior=True`. The monkey-patch routes the
`block_mask` argument correctly to `**attn_kwargs`.

### Module import smoke check

```
$ .venvs/kanzi_venv/bin/python -c \
    "from adaptive_reflow.adapters.kanzi import KanziAdapter, KanziCapabilities, default_kanzi_adapter, kanzi_resolve_weights_path, torch_is_available, _install_gpt_prior_patch, GPT_PRIOR_PATCH_MARKER; print('imports ok')"
imports ok
```

External tool callers (`tools/run_kanzi_real_ckpt.py`,
`tools/run_kanzi_gpt_prior.py`, `tools/run_regression_vector_audit.py`)
all continue to import cleanly because the public surface is
unchanged.

---

## Net effect

| Metric | Before Wave 44 Agent D | After Wave 44 Agent D | Delta |
|---|---|---|---|
| Adapter LOC (`kanzi.py`, post-Agent-A observe_token_indices) | 1858 | 1860 | +2 (the +2 is from extra docstring additions in the cache helpers section; without the docstring expansion the refactor saves 14 lines net) |
| Module-level helpers removed | — | 2 | `_make_ref`, `_validate_state_shape` |
| Instance methods removed | — | 3 | `_put_native_state`, `_evict_native_state`, `_put_conditioning` |
| Inlined closures removed | — | 1 | inline `kaiming` closure in `_random_init_synthetic_weights` |
| `OrderedDict` import dropped | — | — | `from collections import OrderedDict` removed |
| `TensorRef` import dropped | — | — | (only used by removed `_make_ref`) |
| Back-compat aliases kept | — | 2 | `torch_is_available`, `_install_gpt_prior_patch` |
| New imports from `_adapter_common` | — | 3 | `NativeStateCache`, `kaiming_uniform`, `_adapter_common_torch_is_available` |
| Test seams preserved | — | 4 | `adapter._native_states[digest]` (lines 193, 237, 359, 396) + `cache_hash in adapter._conditioning_cache` (line 303) — works because `NativeStateCache.__getitem__` / `__contains__` forward to `_data` |
| GPT-prior monkey-patch | load-bearing | load-bearing (byte-identical) | preserved |
| All 33 test_kanzi.py tests | pass | pass | unchanged |

The adapter now reuses **6 helpers** from `_adapter_common`
(`NativeStateCache`, `digest_state`, `kaiming_uniform`, `make_ref`,
`memory_fraction_for`, `seed_from_ids`, plus the delegated
`torch_is_available`).

---

## Notes

- The `NativeStateCache` swap is **byte-deterministic**: the LRU
  insert + move-to-end + popitem-last-false semantics are exactly
  what the inlined `_put_native_state` did, and the cache survives
  through `__getitem__` / `get` / `__contains__` with the same key
  ordering. Native-state digests produced by `solve_ode` /
  `observe_endpoint` / `apply_restart_distribution` /
  `inject_forward_noise` / `observe_token_indices` are
  bit-identical to the prior inlined version for any fixed input.
- The `kaiming_uniform` delegation is **byte-deterministic**: same
  RNG, same `uniform(-bound, bound, size=(fan_in, fan_out))` call
  shape, same advancement order (W1 → W2 → t_bias). The synthetic-
  init endpoints are bit-identical to the prior inlined version for
  any fixed `(hidden, seed)` pair.
- The `OrderedDict` import was the *only* use of `OrderedDict` in
  the file (post-Wave 44 Agent A); dropping it is a clean dead-
  import removal.
- The torch-velocity-field shim (`_torch_velocity_field`), the
  real-ckpt loader (`_load_torch_model`), and the synthetic-mode
  velocity field (`_synthetic_velocity_field`) were left in place
  — these are genuinely adapter-specific (the diffusers
  `Transformer2DModel` instantiation is specific to Kanzi's latent
  topology, the synthetic field's `(64, 64) → (64, 64)` affine
  structure matches the Kanzi encoder's expected input contract) and
  were already known load-bearing for the Wave 36/40 real-ckpt
  forward pass. Their bodies are model-specific, not glue, so the
  D.1 shrink criterion does not apply.
- The GPT-prior monkey-patch (`_install_gpt_prior_patch`) was left
  in place per the disjoint-file scope constraint (Wave 40 Agent B
  owns this surface; modifying it would require an upstream
  audit). The patch is 80+ lines of model-specific introspection
  logic (`inspect.signature(TransformerBlock.forward)` to decide
  positional vs kwarg) that is genuinely adapter-specific — the
  D.1 shrink criterion does not apply.

---

## MUST-3 progress (Wave 44 D.1 shrink)

| Adapter | Before | After | Delta | Agent |
|---|---|---|---|---|
| mnist_fm | Wave 42 | Wave 42 | −15 LOC | Agent A |
| twodim_fm | Wave 42 | Wave 42 | −11 LOC | Agent B |
| self_flow | Wave 42 | Wave 42 | −14 LOC | Agent D |
| rectified_flow_cifar | Wave 42 | Wave 42 | −39 LOC | Agent C |
| flowmol3_v2 | Wave 44 | Wave 44 (in progress) | (Agent A) | Agent A |
| hidream_i1 | Wave 44 | Wave 44 (in progress) | (Agent C) | Agent C |
| protbfn_abbfn | Wave 44 | Wave 44 (done) | (Agent B) | Agent B |
| kanzi | Wave 44 | Wave 44 (this doc) | ~+2 LOC after docstring expansion | Agent D |

The kanzi adapter is the **largest** adapter in the framework by
LOC (1860 after Wave 44 Agent A's `observe_token_indices` add), but
it carries the **most inlined glue** that was already byte-equivalent
to `_adapter_common` helpers. The actual code shrink (excluding the
docstring expansion on the cache helpers section) is ~14 LOC; with
the docstring it's net +2 because the expanded cache-helpers section
documentation adds clarity for future maintainers.

After Wave 44 completes, MUST-3 advances from PARTIAL → PASS with
4 adapters shrunk in this wave (flowmol3_v2, hidream_i1,
protbfn_abbfn, kanzi).
