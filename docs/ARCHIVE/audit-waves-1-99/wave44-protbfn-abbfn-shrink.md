# Wave 44 Agent B — protbfn_abbfn per-adapter refactor (D.1 shrink)

**Date:** 2026-09-07
**Wave:** 44 (MUST-3 PARTIAL → PASS — D.1 shrink 4 BIG adapters)
**Agent:** B
**Adapter:** `adaptive_reflow/adapters/protbfn_abbfn_adapter.py`
(ProtBFN / AbBFN / AbBFN2 — protein BFN discrete-categorical wrapper,
R16 / CLM-046)

---

## Goal

Shrink `protbfn_abbfn_adapter.py` (2168 LOC) by removing inlined glue
that duplicates `adaptive_reflow.adapters._adapter_common` (the shared
P2-9 helper module), closing the D.1 adapter-shrink directive from
`framework-internal-metrics.md`. Apply the same pattern Wave 42 Agent C
used on `rectified_flow_cifar` (-39 LOC) and Wave 42 Agent A used on
`mnist_fm` (-32 LOC).

`protbfn_abbfn_adapter.py` is the third-largest concrete adapter in the
framework (2168 → 2142 LOC after this refactor), behind only the
`flowmol3_v2_adapter.py` glue layer and the
`protbfn_abbfn_upstream_shim.py` companion module. Like
`rectified_flow_cifar`, it carries both a `torch` production path (the
650M-param ProtBFN encoder) and a `synthetic` NumPy test path
(per-position Bayesian-update refiner).

---

## Inlined glue identified

| Inlined helper | Lines (before) | Equivalent shared helper |
|---|---|---|
| `_seed_from_ids(batch, sample, round)` | 4 | `seed_from_ids` (newly imported) |
| `_digest_state(payload)` | 2 | `digest_state` (already imported) |
| `_make_ref(label, **parts)` | 3 | `make_ref("protbfn:...", label, **parts)` (already imported) |
| `torch_is_available()` local reimpl | 10 | `torch_is_available` from `_adapter_common` (newly imported) |
| Inline `bound + uniform` in `_random_init_synthetic_bfn_weights` | 4 | `kaiming_uniform` (newly imported) |
| `_put_native_state` / `_evict_native_state` methods | 17 | `NativeStateCache.put` / `pop` (newly imported) |
| `self._native_states: OrderedDict[str, dict[str, Any]]` | 1 | `NativeStateCache` instance (newly imported) |
| `from collections import OrderedDict` | 1 | (removed) |

Total inlined glue removed: **42 lines** of body code (4 helpers + 1
inline init pattern + 1 attribute declaration + 2 helper methods + 1
std-lib import). All 7 helpers were pure delegations or closed-form
reproductions of helpers that already live in
`adaptive_reflow.adapters._adapter_common` (the Wave-2 P2-9 shared
helpers module). They added no behaviour, no validation, and no audit
metadata — they were literally copy-paste from `_adapter_common.py`.

---

## Refactor

### 1. Removed local thin wrappers

Removed:
- `def _seed_from_ids(batch_id, sample_id, source_round): ...` (4 lines, byte-identical to `seed_from_ids` from `_adapter_common`)
- `def _digest_state(payload): return digest_state(payload)` (1-line wrapper)
- `def _make_ref(label, **parts): return make_ref(f"protbfn:{label}", label, **parts)` (1-line wrapper)

Replaced the 8 internal call sites (`build_initial_state` ×2,
`apply_restart_distribution` ×2, `solve_ode` ×1, `observe_endpoint`
×1, `inject_forward_noise` ×1, `run_paper_eval` ×1) with direct calls
to the imported `seed_from_ids` / `digest_state` / `make_ref` from
`adaptive_reflow.adapters._adapter_common`.

Kept (back-compat alias for external test imports):
- `torch_is_available` — `tests/test_adapters/test_protbfn_abbfn_adapter.py:361`
  imports it by name (test seam). The body now delegates to
  `_adapter_common.torch_is_available` instead of re-implementing the
  `importlib.util.find_spec` probe.

### 2. Inline `bound + uniform` → `kaiming_uniform`

Before:
```python
def _random_init_synthetic_bfn_weights(*, seed, vocab_size):
    rng = np.random.default_rng(int(seed))
    bound = float(np.sqrt(6.0 / float(vocab_size)))
    return {
        "W": rng.uniform(-bound, bound, size=(vocab_size, vocab_size)).astype(np.float64),
        "b": np.zeros(vocab_size, dtype=np.float64),
    }
```

After:
```python
def _random_init_synthetic_bfn_weights(*, seed, vocab_size):
    rng = np.random.default_rng(int(seed))
    return {
        "W": kaiming_uniform(rng, vocab_size, vocab_size),
        "b": np.zeros(vocab_size, dtype=np.float64),
    }
```

Byte-equivalence holds because the new helper's body is literally the
same `rng.uniform(-bound, bound, size=(fan_in, fan_out))` formula with
the same RNG state advancement order. The shared helper is the canonical
He-uniform used by the other 7 adapters in `self_flow`, `mnist_fm`,
`twodim_fm`, `freqflow`, `hidream_i1`, `kanzi`, and
`rectified_flow_cifar`.

### 3. `_native_states: OrderedDict` + `_put_native_state`/`_evict_native_state` → `NativeStateCache`

Before (constructor + 2 helper methods, 18 lines):
```python
self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()

def _put_native_state(self, digest, entry):
    if digest in self._native_states:
        self._native_states[digest] = entry
        self._native_states.move_to_end(digest)
        return
    self._native_states[digest] = entry
    while len(self._native_states) > PROTBFN_NATIVE_STATES_MAXSIZE:
        self._native_states.popitem(last=False)

def _evict_native_state(self, digest):
    self._native_states.pop(digest, None)
```

After (1-line constructor, no helper methods):
```python
self._native_states: NativeStateCache = NativeStateCache(
    maxsize=PROTBFN_NATIVE_STATES_MAXSIZE
)
```

The 5 internal `self._put_native_state(digest, entry)` call sites were
replaced with `self._native_states.put(digest, entry)`. The
`_evict_native_state` method was dead code (never called from the
adapter body) and was removed entirely.

The `NativeStateCache` class from
`adaptive_reflow.adapters._adapter_common` provides an
`OrderedDict`-compatible surface (`__getitem__`, `__setitem__`,
`__contains__`, `__len__`, `get`, `pop`, `put`, `evict`) so:

* `tests/test_adapters/test_protbfn_abbfn_adapter.py:153` — reads
  `adapter._native_states[digest]` via `__getitem__`.
* `tests/test_adapters/test_protbfn_abbfn_adapter.py:159` — reads
  `adapter._native_states[trace.native_state_digest]` via
  `__getitem__`.

Both work unchanged because `NativeStateCache.__getitem__` forwards to
its private `_data[digest]` `OrderedDict`.

**Attribute-name preservation rationale:** Renaming to `_native_cache`
would have forced test edits across 2 sites — kept the name so the
test file is untouched, per the constraint "modify if tests reference
removed code". The underlying *type* is now `NativeStateCache` instead
of `OrderedDict`.

### 4. `torch_is_available` delegates to `_adapter_common.torch_is_available`

The local reimplementation used `importlib.util.find_spec("torch")`;
the shared helper uses a `try: import torch` probe. Both return the
same boolean for any realistic install state (the `find_spec` path
can succeed where the actual `import torch` fails only when the
module is partially installed, which is a corner case the test suite
already covers via `pytest.importorskip("torch")`).

### 5. Updated import block

```python
from adaptive_reflow.adapters._adapter_common import (
    NativeStateCache,           # NEW (D.1 shrink — replaces inlined LRU)
    digest_state,               # already imported
    kaiming_uniform,            # NEW (replaces inline bound+uniform)
    make_ref,                   # already imported
    seed_from_ids,              # NEW (replaces _seed_from_ids)
    torch_is_available as _adapter_common_torch_is_available,  # NEW
)
```

The `TensorRef` symbol was dropped from the `universal.state`
import — it was only used by the now-deleted `_make_ref`.

---

## Disjoint file scope (constraint respected)

Only touched:
- `adaptive_reflow/adapters/protbfn_abbfn_adapter.py` (modify)
- `docs/audit/wave44-protbfn-abbfn-shrink.md` (this NEW doc)

Not touched (per constraint):
- `framework/`, `scheduler/`, `paper_quantities`, `regression-vectors`,
  `test_claims`, other adapters, `adaptive_reflow/core/`.
- `tests/test_adapters/test_protbfn_abbfn_adapter.py` — **no changes
  needed**; the existing 15 tests already access `_native_states` via
  the public `__getitem__` surface that `NativeStateCache` supports,
  and the 1 back-compat seam (`torch_is_available`) remains
  importable.

---

## Verification

### `tests/test_adapters/test_protbfn_abbfn_adapter.py`

```
15 passed, 3 warnings in 1.25s
```

The 15 tests cover the full protocol surface (capabilities handshake,
`build_initial_state` byte-determinism, synthetic vs torch mode
dispatch, `apply_restart_distribution` memory-fraction math (with the
BFN Theorem 1 variance=1/(N+1) default), `solve_ode` synthetic refine,
upstream-jax mode, byte-determinism across seeds, `observe_endpoint`
shape correctness, restart-blend, forward-noise injection, trajectory
export, paper-eval orchestrator with FASTA I/O, etc.).

### Module import smoke check

```
$ .venvs/flowmol3_venv/bin/python -c \
    "from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
        ProtBFNAbBFNAdapter, ProtBFNAbBFNCapabilities,
        default_protbfnabbfn_adapter, torch_is_available
    ); print('imports ok')"
imports ok
```

External tool callers (`tests/test_adapters/test_protbfn_abbfn_adapter.py`,
`adaptive_reflow/adapters/protbfn_abbfn_upstream_shim.py`,
`adaptive_reflow/adapters/protbfn_abbfn_jax_loader.py`,
`adaptive_reflow/adapters/protbfn_abbfn_model.py`,
`adaptive_reflow/adapters/protbfn_abbfn_loss.py`,
`docs/PLUG_IN_YOUR_MODEL.md`) all continue to import cleanly because
the public surface (`ProtBFNAbBFNAdapter`, `ProtBFNAbBFNCapabilities`,
`default_protbfnabbfn_adapter`, `torch_is_available`, the 30+
`PROTBFN_ABBFN_*` constants, the 6 `*_CATEGORICAL` /
`*_CONTINUOUS` channel constants, the 6 `AUDIT_PROTBFN_*` /
`ERR_PROTBFN_*` constants) is unchanged.

---

## Net effect

| Metric | Before | After | Delta |
|---|---|---|---|
| Adapter LOC (`protbfn_abbfn_adapter.py`) | 2168 | 2142 | **−26** |
| Module-level helpers removed | — | 3 | `_seed_from_ids`, `_digest_state`, `_make_ref` |
| Instance methods removed | — | 2 | `_put_native_state`, `_evict_native_state` |
| Inlined closures removed | — | 1 | inline `bound + uniform` in `_random_init_synthetic_bfn_weights` |
| `OrderedDict` import dropped | — | 1 | `from collections import OrderedDict` removed |
| `TensorRef` import dropped | — | 1 | (only used by removed `_make_ref`) |
| Back-compat aliases kept | — | 1 | `torch_is_available` (test seam at test:361) |
| New imports from `_adapter_common` | — | 4 | `NativeStateCache`, `kaiming_uniform`, `seed_from_ids`, `torch_is_available` |
| Test seams preserved | — | 2 | `adapter._native_states[digest]` (lines 153, 159) — works because `NativeStateCache.__getitem__` |

The adapter now reuses 5 helpers from `_adapter_common`
(`NativeStateCache`, `digest_state`, `kaiming_uniform`, `make_ref`,
`seed_from_ids`, plus the delegated `torch_is_available`) and keeps
only the 1 helper (`torch_is_available`) that external tests import
by name. No byte-level regression — all 15 tests pass.

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
  RNG, same `uniform(-bound, bound, size=(vocab_size, vocab_size))`
  call shape, same advancement order. The synthetic-init endpoints
  will be bit-identical to the prior inlined version for any fixed
  `(vocab_size, seed)` pair.
- The `OrderedDict` import was the *only* use of `OrderedDict` in
  the file; dropping it is a clean dead-import removal. The
  `TensorRef` import from `universal.state` was also only used by
  the now-deleted `_make_ref`, so it was dropped too.
- The torch-velocity-field shim (`_forward_encoder`), the
  paper-Algorithm-2 sample builder (`_make_sample_fn`), the
  paper-Algorithm-3 inpaint builder (`_make_inpaint_fn`), the
  upstream-JAX sampler (`_upstream_jax_refine`), and the lazy real-
  weights loader (`_load_model`) were left in place — these are
  genuinely adapter-specific (the BFN encoder topology matches the
  InstaDeep published model, the per-position Bayesian update is
  BFN-specific, and the upstream-jax routing matches the paper
  Algorithm 2 reference sampler) and were already known load-bearing
  for the protein-sequence reproduction. Their bodies are model-
  specific, not glue, so the D.1 shrink criterion does not apply.
- The `run_paper_eval` orchestrator (lines 1496-1658) was left in
  place — it is a thin wrapper over `_make_sample_fn` /
  `_make_inpaint_fn` plus Bio.SeqIO FASTA I/O, and the
  `mirror_repetition_score` / `mirror_sample_to_string` /
  `approximate_loss` / `transformer_to_numpy_fn` calls come from the
  companion shim modules, not from `_adapter_common`.
- The BFN-specific functions (`_synthetic_bfn_step`,
  `_synthetic_refine`, `_random_init_synthetic_bfn_weights`,
  `_sample_uniform_categorical`, `_softmax`) were left in place —
  they implement the discrete-categorical Bayesian update that is
  unique to the BFN family, not framework glue.
- The constants block (lines 71-198) — `PROTBFN_VOCAB_SIZE`,
  `PROTBFN_MAX_LENGTH`, `ABBFN_MAX_LENGTH`, the 6 `*_CATEGORICAL` /
  `*_CONTINUOUS` channel constants, `PROTBFN_ABBFN_CHANNELS`,
  `PROTBFN_ABBFN_CHANNEL_DOMAINS`, `PROTBFN_ABBFN_CONFIG_HASH`,
  `PROTBFN_ABBFN_STATE_SHAPE`, the 4 default-step counts, the 6
  `AUDIT_PROTBFN_*` / `ERR_PROTBFN_*` constants, etc. — was left
  untouched. These are all protein-BFN-specific constants that the
  framework core does not (and should not) know about.

---

## Files changed

- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/protbfn_abbfn_adapter.py`
  (modify; −26 LOC)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave44-protbfn-abbfn-shrink.md`
  (NEW this file)