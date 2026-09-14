# Wave 44 Agent A — flowmol3_v2_adapter per-adapter shrink (D.1)

**Date:** 2026-09-07
**Wave:** 44 (D.1 partial close — biggest adapter shrink)
**Agent:** A
**Adapter:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (the FlowMol3 3D
molecule generator adapter, 3272 → 3257 LOC).

---

## Goal

Apply the Wave 42 shrink pattern (mnist_fm, rectified_flow_cifar) to
flowmol3_v2_adapter: remove inlined glue that duplicates
`adaptive_reflow.adapters._adapter_common` and adopt the shared LRU cache
class. The adapter was the largest in the codebase so the absolute LOC
reduction has the most impact for the D.1 metric.

---

## Inlined glue identified

| Inlined helper | Lines (before) | Equivalent shared helper |
|---|---|---|
| `_seed_from_ids(batch, sample, round)` | 4 | `seed_from_ids` from `_adapter_common` |
| `_digest_state(payload)` | 6 | `digest_state` from `_adapter_common` |
| `_make_ref(label, **parts)` | 6 | `make_ref` from `_adapter_common` (with `prefix="flowmol3adapter"`) |
| `_torch_is_available()` | 5 | `torch_is_available` from `_adapter_common` |
| `_put_native_state(digest, entry)` LRU body | 8 | `NativeStateCache.put` (P2-9 LRU) |
| `kaiming(fan_in, fan_out)` closure | 6 | `kaiming_uniform(rng, fan_in, fan_out)` from `_adapter_common` |

All six were either verbatim copies of `_adapter_common` helpers, or
shaped their behaviour to match the `_adapter_common` API exactly.

---

## Refactor

### 1. Removed local helpers

Removed:
- `def _seed_from_ids(...)` — pure SHA-256-seed-from-ids, byte-identical to
  `_adapter_common.seed_from_ids`.
- `def _digest_state(payload)` — pure SHA-256-digest-of-payload, byte-identical
  to `_adapter_common.digest_state`.
- `def _torch_is_available()` — pure `importlib.util.find_spec("torch")` probe.
  Replaced with `from _adapter_common import torch_is_available as
  _torch_is_available`. The new helper does an actual `import torch` (stricter
  semantics — catches broken torch installs that pass `find_spec`).

The 1 internal call site for `_seed_from_ids` (build_initial_state) and the
6 call sites for `_digest_state` (build_initial_state,
apply_restart_distribution, _solve_ode_upstream, _solve_ode_linear,
_solve_ode_ctmc, observe_endpoint, inject_forward_noise) now use the
imported names without the underscore prefix.

### 2. New `_make_ref` wrapper (preserves byte-stable TensorRef namespace)

The original `_make_ref` hardcoded the `"flowmol3adapter:"` namespace prefix.
The shared `_adapter_common.make_ref(prefix, label, **parts)` takes the
prefix as a parameter. To keep the existing constructor's namespace
byte-stable (the prior `_make_ref("initial", ...)` calls produced
`flowmol3adapter:<hash>` strings), the wrapper now reads:

```python
def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic TensorRef in the flowmol3adapter namespace."""
    return make_ref("flowmol3adapter", label, **parts)
```

This is a 4-line wrapper (with docstring) instead of the previous 6-line
inline implementation. All 9 call sites (`build_initial_state` and
`apply_restart_distribution`) continue to call `_make_ref(...)` and the
resulting TensorRef digests are byte-identical to before.

### 3. `_native_states` LRU cache adopts `NativeStateCache`

Before:
```python
self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()

def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
    if digest in self._native_states:
        self._native_states[digest] = entry
        self._native_states.move_to_end(digest)
        return
    self._native_states[digest] = entry
    while len(self._native_states) > FLOWMOL3ADAPTER_NATIVE_STATES_MAXSIZE:
        self._native_states.popitem(last=False)
```

After:
```python
self._native_states: NativeStateCache = NativeStateCache(
    maxsize=FLOWMOL3ADAPTER_NATIVE_STATES_MAXSIZE,
)

def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
    """Thin delegation to NativeStateCache (P2-9 shared LRU)."""
    self._native_states.put(digest, entry)
```

The `NativeStateCache` from `_adapter_common` provides an
OrderedDict-compatible surface (`__getitem__`, `__setitem__`,
`__contains__`, `__len__`, `get`, `pop`, `put`, `evict`) so:

* `tests/test_adapters/test_flowmol3_v2_adapter.py` (8 sites) accesses
  `adapter._native_states[...]` / `adapter._native_states.get(...)` and
  works unchanged because the `NativeStateCache`'s `__getitem__` / `get`
  matches the OrderedDict surface.

The 7 internal `self._put_native_state(digest, entry)` call sites now
delegate to `self._native_states.put(digest, entry)` — same eviction
order, same maxsize semantics.

### 4. Kaiming closure replaced

Before:
```python
def kaiming(fan_in: int, fan_out: int) -> ArrayF64:
    bound = np.sqrt(6.0 / float(fan_in))
    return np.asarray(
        rng.uniform(-bound, bound, size=(fan_in, fan_out)),
        dtype=np.float64,
    )
```

After (inlined at call sites, closure removed):
```python
"W_x": kaiming_uniform(rng, in_dim_x, in_dim_x),
```

This is identical to `_adapter_common.kaiming_uniform(rng, fan_in, fan_out)`
(verified line-by-line). The closure captured `rng` from the enclosing
function; the new code passes `rng` explicitly. Same He-uniform init
math, byte-identical output for fixed seed.

### 5. Dropped `from collections import OrderedDict`

The previous `OrderedDict` annotation was a latent bug — the import was
unused after `NativeStateCache` replaced the bare `OrderedDict`. Removing
the import makes the type-annotation-vs-runtime-state invariant trivially
satisfiable.

---

## Disjoint file scope (constraint respected)

Only touched:
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (modify)
- `docs/audit/wave44-flowmol3-v2-shrink.md` (NEW this file)

Not touched (per constraint):
- `framework/`, `scheduler`, `paper_quantities`, `regression-vectors`,
  `test_claims`, other adapters, `_adapter_common`, `core/`,
  `run_real_ckpt_eval.py`.
- `tests/test_adapters/test_flowmol3_v2_adapter.py` — **no changes needed**;
  the existing tests access `_native_states` via the public `__getitem__` /
  `get` surface that `NativeStateCache` supports, and the 8 byte-stability
  anchors (`_make_ref` namespace, `FLOWMOL3ADAPTER_CONFIG_HASH`,
  `FLOWMOL3ADAPTER_PINNED_COMMIT`, `FLOWMOL3ADAPTER_STATE_SHAPE`) are
  unchanged.

---

## Verification

### `tests/test_adapters/test_flowmol3_v2_adapter.py`

```
15 passed, 3 warnings in 0.29s
```

All 15 tests pass:

* `test_capabilities_handshake`
* `test_build_initial_state_returns_correct_shape`
* `test_solve_ode_returns_finite_trace`
* `test_endpoint_round_trip`
* `test_determinism` (byte-identical digests across two adapter instances)
* `test_velocity_field_lazy_loads_torch_if_required` (monkey-patches
  `_torch_is_available` via the module-level binding; the new alias
  preserves the test patching surface)
* `test_protocol_conformance`
* `test_restart_blend_channel_aware`
* `test_apply_restart_distribution_rejects_missing_channel_with_clear_error`
* `test_apply_restart_distribution_happy_path_all_channels`
* `test_compose_condition_rejects_channel_keys`
* `test_export_trajectory_returns_lineage`
* `test_mechanism_id_advertised`
* `test_pinned_commit_matches_registry`
* `test_default_factory`

---

## Net effect

| Metric | Before | After | Delta |
|---|---|---|---|
| Adapter LOC (`flowmol3_v2_adapter.py`) | 3272 | 3257 | **−15** |
| Module-level helpers removed | — | 5 | `_seed_from_ids`, `_digest_state`, `_torch_is_available`, inline `kaiming`, inline `_make_ref` body |
| Module-level helpers added | — | 1 | `_make_ref` (4-line wrapper) |
| Instance methods removed | — | 0 | `_put_native_state` kept as 2-line delegation |
| New `_adapter_common` imports | — | 5 | `NativeStateCache`, `digest_state`, `kaiming_uniform`, `make_ref`, `seed_from_ids`, `torch_is_available as _torch_is_available` |
| Removed stdlib imports | — | 1 | `from collections import OrderedDict` |

The adapter now reuses 6 helpers from `_adapter_common`
(`NativeStateCache`, `digest_state`, `kaiming_uniform`, `make_ref`,
`seed_from_ids`, `torch_is_available`) and keeps only 1 local helper
(`_make_ref`) that pre-bakes the `flowmol3adapter` namespace prefix.

---

## Honest scope assessment

The D.1 shrink for flowmol3_v2 is modest (−15 LOC) because the bulk of
the 3272-line adapter is *real, molecule-specific chemistry code* that has
no shared equivalent:

* `_load_flowmol3_config` + `_load_flowmol3_state_dict` (~70 LOC) —
  FlowMol3 YAML + Lightning checkpoint loader; no other adapter loads a
  PyTorch Lightning ckpt.
* `_build_flowmol3_velocity_module` + `_FlowMol3ReadoutHead` (~120 LOC) —
  GVP-graph read-out reconstruction (the 444 conv tensors are NOT applied
  per the fidelity boundary, so this is the partial-fidelity path).
* `_install_upstream_stubs` (~60 LOC) — installs pure-Python stubs for
  `torch_scatter.segment_csr` and `posebusters.PoseBusters` so the
  upstream `flowmol` package is importable on the project's venv.
* `_try_import_upstream_flowmol` (~45 LOC) — lazy import of the upstream
  GVP graph-velocity-field code via `sys.path.insert`.
* `_real_velocity_field` + `_ctmc_real_velocity_field_ex` (~280 LOC) —
  torch + numpy plumbing for the real-weight forward + CTMC-flavored
  marginal extraction (atom-type, charge, bond marginals).
* `_channel_aware_blend` (~177 LOC) — heterogeneous-native-state blend
  math that handles molecule-size mismatch (prior/fresh can have different
  `n_atoms`). The shared `CategoricalAwareBlender` only handles
  per-channel categorical resampling, not size-mismatched heterogeneous
  states, so it does not fit.
* `_solve_ode_upstream` + `_solve_ode_linear` + `_solve_ode_ctmc` (~670 LOC) —
  three solve_ode paths with distinct maths (upstream end-to-end GVP,
  linear interpolant Euler, CTMC rate matrix per-position). The CTMC path
  is paper-specific to FlowMol3; the linear path is the pre-Stage-3
  ablation; the upstream path is the §3.4 repair-plan hook.
* Per-channel documentation, fidelity-boundary annotations, upstream-stub
  rationale comments (~400 LOC) — these are load-bearing for the
  Wave-42 audit trail and the §3.4 fidelity disclosure in the paper.

So the realistic D.1 win for this adapter was ~15 LOC, not the
multi-hundred-LOC target the brief alluded to. The other D.1 wins
(mnist_fm, rectified_flow_cifar, self_flow, twodim_fm, kanzi,
hidream_i1, protbfn_abbfn) are delivering the multi-hundred reductions
in the Wave 44 parallel workstreams; flowmol3_v2's win is smaller but
byte-stable.

---

## Files changed

- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py`
  (modify; −15 LOC)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave44-flowmol3-v2-shrink.md`
  (NEW this file)
