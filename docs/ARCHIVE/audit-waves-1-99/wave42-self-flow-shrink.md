# Wave 42 — Self-Flow adapter: framework-core glue adoption

**Task:** Wave 42 WF2 (MUST-3 PARTIAL close, `gap-plan-wave32.md` #12, D.1
shrink adapters). One of the four per-adapter refactors in this wave
(twodim_fm, self_flow, mnist_fm, rectified_flow_cifar).
**Scope:** `adaptive_reflow/adapters/self_flow.py` only. Test
suite + D.4 regression vector are byte-frozen.
**Date:** 2026-09-05.
**Status:** applied; `tests/test_adapters/test_self_flow.py` 22/22 pass;
`regression-vectors/self_flow.json` 2/2 vectors match.

## 1. Why this adapter

`self_flow.py` (1449 → 1488 lines after this refactor — see §5 for the
honest accounting) carries three pieces of inlined glue that have a
direct equivalent in the framework-core subpackage `adaptive_reflow/core/`
that MUST-3 shipped in Wave 24:

| Inlined glue | Framework-core replacement |
|---|---|
| `self_flow_resolve_weights_path` (hand-rolled `Path`/`exists()` probe, ~20 LOC) | `adaptive_reflow.core.ckpt_loader.resolve_candidate_paths` |
| `_torch_velocity_field` (NumPy ↔ torch convert + 8→4 channel slice) | `adaptive_reflow.core.diffusers_wrapper.{diffusers_preprocess,diffusers_postprocess}` |
| `_load_torch_model` (`torch.load(...)` + `state.get("model", state)` + `model.load_state_dict(..., strict=False)`) | `adaptive_reflow.core.ckpt_loader.load_state_dict_strict_safe` |

These are the exact per-adapter targets the core/ docstrings call out
(`ckpt_loader.py:53` lists `*_resolve_weights_path` / `torch_is_available` /
`_load_torch_model` boilerplate as the intended adoption surface).

Self-Flow is a particularly good fit because the **synthetic** mode
path (which is what every test exercises) is unaffected by the torch
refactor — only the production torch path touches the new wrappers.
That means the D.4 regression vector
(`regression-vectors/self_flow.json`) is byte-stable.

## 2. `self_flow_resolve_weights_path` → `resolve_candidate_paths`

Before — hand-rolled 2-candidate probe:

```python
def self_flow_resolve_weights_path(*, data_dir: Path | None = None) -> Path | None:
    base = Path(data_dir) if data_dir is not None else Path("data")
    candidate = base / "self_flow" / "selfflow_imagenet256.pt"
    if candidate.exists():
        return candidate
    flat = base / "selfflow_imagenet256.pt"
    if flat.exists():
        return flat
    return None
```

After — thin adapter wrapper over the framework-core helper:

```python
def self_flow_resolve_weights_path(*, data_dir: Path | None = None) -> Path | None:
    candidates = resolve_candidate_paths(
        "self_flow", "selfflow_imagenet256.pt",
        data_dirs=[Path(data_dir)] if data_dir is not None else None,
    )
    return candidates[0] if candidates else None
```

`resolve_candidate_paths` (in `core/ckpt_loader.py`) probes the same two
locations in the same order (subdir first, then flat), and additionally
walks the `.pt / .pth / .bin / .safetensors / .npy` extension list —
strictly more candidates, never fewer, so the public surface
`test_resolve_weights_path_finds_published_ckpt` continues to pass.

## 3. `_torch_velocity_field` → `diffusers_preprocess` + `diffusers_postprocess`

The hand-rolled forward path:

```python
x_t = torch.as_tensor(x, dtype=dtype).unsqueeze(0)
t_t = torch.tensor([float(t)], dtype=dtype)
y_t = torch.as_tensor(cache.get("y_embed", np.zeros(1152, dtype=np.float64)),
                       dtype=dtype).unsqueeze(0)
v = model(x_t, t_t, y=y_t)
v = v[:, :4]
out = np.asarray(v.squeeze(0).detach().cpu().numpy(), dtype=np.float64)
```

After — delegates to the framework-core DiT glue:

```python
sig = DiffusersForwardSignature(
    in_channels=4, out_channels=8,  # dual-timestep head broadcasts 8 → 4
    patch_size=2, sample_size=16, dtype="float32",
    use_cfg=False,  # legacy behaviour: CFG not interpolated
    conditioning_dim=1152,
)
with torch.no_grad():
    x_t = diffusers_preprocess(x, signature=sig, add_batch_dim=True)
    t_t = torch.tensor([float(t)], dtype=dtype)
    y_arr = np.asarray(
        cache.get("y_embed", np.zeros(sig.conditioning_dim, dtype=np.float64)),
        dtype=np.float64,
    ).reshape(-1)
    y_t = torch.as_tensor(y_arr, dtype=dtype).unsqueeze(0)
    v = model(x_t, t_t, y=y_t)
    out = diffusers_postprocess(
        v, signature=sig, take_first_n_channels=int(SELF_FLOW_STATE_SHAPE[0]),
    )
```

The `DiffusersForwardSignature` carries the per-adapter constants the
core wrapper needs (`in_channels=4`, `patch_size=2`, `sample_size=16`,
`dtype="float32"`, `conditioning_dim=1152`) — these match what the SiT-XL/2
checkpoint inspects in `_load_torch_model`.

`use_cfg=False` preserves the prior behaviour: the previous implementation
accepted `guidance_scale` but did not actually apply CFG interpolation, so
the framework's per-round `delta_spec["guidance_scale"]` is **accepted but
ignored** in this path. (The framework's default `cfg_scale=1.0` already
equals the unconditional pass, so this is byte-equivalent.) A future
refactor can flip `use_cfg=True` once the framework's CFG integration is
re-tested on the SiT-XL/2 dual-timestep head.

The 8→4 channel slice is moved from inline `v[:, :4]` to
`diffusers_postprocess(take_first_n_channels=4)` — semantically identical,
because the core helper applies `take_first_n` after the batch-dim
squeeze, which is the same permutation as the legacy code.

## 4. `_load_torch_model` → `load_state_dict_strict_safe`

Before — inline `torch.load(...) + state.get("model", state)`:

```python
state = torch.load(str(weights_path), map_location="cpu", weights_only=False)
sd = state.get("model", state)
```

After — delegates to the framework-core shim:

```python
sd = load_state_dict_strict_safe(
    weights_path, model=None,
    strict=False, state_dict_key="model", map_location="cpu",
)
```

`load_state_dict_strict_safe` (in `core/ckpt_loader.py`) handles the
`torch.load + state_dict_key unwrap + model.load_state_dict(strict=False)`
chain that every PHASE-3 adapter re-typed. The `model=None` kwarg is
safe — the helper only calls `model.load_state_dict` when `model`
has that method (`hasattr(model, "load_state_dict")`), so passing
`None` here simply skips that branch and returns the unwrapped state
dict, which is exactly what the downstream `sd["pos_embed"]` /
`sd["x_embedder.proj.weight"]` / etc. probes need.

## 5. Line counts — reported straight

| Measure | Before | After | Delta |
|---|---|---|---|
| `self_flow.py` total | 1449 | 1488 | **+39** |
| Executable code (rough) | ~870 | ~855 | **−15** |
| Docstring / comment | ~530 | ~595 | +65 |
| Blank | ~50 | ~40 | −10 |

This mirrors the Wave 41 FlowMol3 shrink result (`docs/audit/wave41-flowmol3-shrink.md` §3):
**the inlined glue did shrink, but the file as a whole grew** because
the new refactor rationale docstring + per-helper commentary is now
attached to the framework-core call sites.

The D.1 metric is per-adapter **median** ≤ 500 across 18 adapters
(`todo/framework-internal-metrics.md` §D.1). Self-Flow sits in the
1400-line tier either way, so this delta does not move D.1. The
agents that move D.1 are the four 1500–3300-line checkpoint adapters
(`flowmol3_v2_adapter.py`, `protbfn_abbfn_adapter.py`, `hidream_i1.py`,
`lumina_image_2_0.py`) — those are the consumers of `core.ckpt_loader`
+ `core.diffusers_wrapper` + `core.vae_decoder` that were written for.

## 6. New dependencies

`adaptive_reflow.adapters.self_flow` now imports from
`adaptive_reflow.core`:

- `ckpt_loader.resolve_candidate_paths` — checkpoint path probe
- `ckpt_loader.load_state_dict_strict_safe` — state-dict load helper
- `diffusers_wrapper.DiffusersForwardSignature` — per-call signature envelope
- `diffusers_wrapper.diffusers_preprocess` — NumPy → torch
- `diffusers_wrapper.diffusers_postprocess` — torch → NumPy

This is the **second per-adapter consumer of `adaptive_reflow.core`**
(`flowmol3.py` was the first; see `docs/audit/wave41-flowmol3-shrink.md`).
After Wave 42 the framework-core glue has 2 of its 4 intended
per-adapter consumers.

Stdlib additions: none.
No new third-party dependency: `core.ckpt_loader` and
`core.diffusers_wrapper` are stdlib + numpy at module level (torch
stays behind lazy imports).

## 7. What was deliberately NOT changed

- **Synthetic-mode trajectory digest** (`build_initial_state` /
  `solve_ode` / `observe_endpoint` / `inject_forward_noise`):
  byte-frozen by `regression-vectors/self_flow.json`. The refactor
  only touches the torch-mode `_torch_velocity_field` path, which the
  regression vector never exercises. Verified empirically: the
  `test_regression_vector_matches[self_flow]` test passes both before
  and after.
- **`_native_states` OrderedDict LRU**: this is an
  `_adapter_common.NativeStateCache`-shaped structure, but the
  per-adapter custom dict-with-mode/conditioning_hash entries are
  load-bearing for the D.4 audit chain. Adopting `NativeStateCache`
  wholesale would change the byte-level entry layout and break the
  regression vector. Deferred — `NativeStateCache` adoption is a
  separate, future-wave decision per Wave 33 §3 ("the actual
  replacement requires paired-regression-vectors for these 5 NEW
  adapters — a precondition that the existing regression-vector
  infrastructure does not yet provide").
- **`SelfFlowCapabilities`**: not collapsed to `make_adapter_capabilities`
  for the same byte-stability reason (the capability token is part of
  the regression vector's `capability_token` field). The Wave 41
  audit noted this pattern.
- **`torch_is_available`**: kept as-is. It is **not** in
  `adaptive_reflow/core/` — it lives in `adapters/_adapter_common.py`.
  A future consolidation could move it into `core/ckpt_loader.py`,
  but that's a separate refactor.

## 8. Verification

The target test run from the task brief:

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_self_flow.py -q --tb=line
22 passed, 3 warnings in 1.04s
```

D.4 regression vector:

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_regression_vectors.py -q -k self_flow
2 passed, 40 deselected in 90.70s (0:01:30)
```

The full adapter test directory was **not** exercised — a concurrent
agent's edit to `rectified_flow_cifar.py` broke an unrelated
`_make_ref` import in `tests/test_adapters/test_adapter_common.py`,
which fails on import. That test is in the disjoint scope of Wave 42
Agent C and out of scope for this agent.

## 9. Follow-ups for the wider framework-core adoption push

- The other two NEW adapters (`mnist_fm.py`, `rectified_flow_cifar.py`)
  carry the same `*_resolve_weights_path` / hand-rolled torch-state-load
  patterns that this agent collapsed. Their Wave 42 agents (Wave 42
  Agent A / Wave 42 Agent C respectively) can apply the same
  `resolve_candidate_paths` + `load_state_dict_strict_safe` pair.
- `mnist_fm.py`'s `_native_states` OrderedDict is a closer
  `NativeStateCache` fit than Self-Flow's (no per-entry `mode` /
  `conditioning_hash` keys) and would adopt cleanly if paired with a
  regression-vector migration.
- The `core.diffusers_wrapper.DiffusersForwardWrapper` class
  (which `diffusers_preprocess`/`_postprocess` are part of) is still
  not exercised by any adapter — only the lower-level preprocess/
  postprocess helpers are used here. A future wave could collapse
  `_torch_velocity_field` to a single `DiffusersForwardWrapper(...)`
  call (with `use_cfg=True`) once CFG on the SiT-XL/2 dual-timestep
  head is regression-tested.
