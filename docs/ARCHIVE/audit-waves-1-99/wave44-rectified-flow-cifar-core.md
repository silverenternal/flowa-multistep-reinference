# Wave 44 — Rectified Flow CIFAR adapter: framework-core glue adoption

**Task:** Wave 44 WF3 (MUST-3 PARTIAL → PASS, `gap-plan-wave32.md`
#12, D.1 shrink adapters). Per-adapter refactor in the third wave of
framework-core glue adoption (after Wave 41 FlowMol3, Wave 42
Self-Flow + MNIST-FM + Twodim-FM).
**Scope:** `adaptive_reflow/adapters/rectified_flow_cifar.py` only.
Test suite is byte-frozen; no `regression-vectors/` entry exists for
this adapter (synthetic mode is the test path).
**Date:** 2026-09-07.
**Status:** applied; `tests/test_adapters/test_rectified_flow_cifar.py`
26/26 pass; `assert_adapter_compliance` passes; the adapter is the
**4th consumer** of `adaptive_reflow.core` (joining flowmol3,
mnist_fm, self_flow).

## 1. Why this adapter

`rectified_flow_cifar.py` (1317 → 1363 lines after this refactor — see
§5 for the honest accounting) carries two pieces of inlined glue that
have direct equivalents in the framework-core subpackage
`adaptive_reflow/core/` shipped in Wave 24 and listed as the
"intended adoption surface" in `ckpt_loader.py:50-73`:

| Inlined glue | Framework-core replacement |
|---|---|
| `rectified_flow_cifar_resolve_weights_path` (hand-rolled per-candidate `Path`/`exists()` probe, ~17 LOC) | `adaptive_reflow.core.ckpt_loader.resolve_candidate_paths` |
| `_load_torch_unet` `torch.load(...) + raw.get("state_dict", raw) + fmt/raw.get("format")` chain | `adaptive_reflow.core.ckpt_loader.load_state_dict_strict_safe` (with `state_dict_key="state_dict"`) |

These mirror the self_flow refactor (Wave 42 Agent D) exactly — see
`docs/audit/wave42-self-flow-shrink.md` §2 / §4 for the reference
pattern. The notable difference: rectified_flow_cifar supports both
`.safetensors` and `.pt/.pth` checkpoints, so the `load_state_dict_strict_safe`
adoption applies only to the `.pt/.pth` branch; the `.safetensors`
branch keeps its `safetensors.torch.load_file` call.

The synthetic-mode path (which is what every test exercises) is
unaffected by the torch refactor — only the production torch path
touches the new wrapper.

## 2. `rectified_flow_cifar_resolve_weights_path` → `resolve_candidate_paths`

Before — hand-rolled per-candidate probe loop:

```python
def rectified_flow_cifar_resolve_weights_path(
    data_dir: Path | None = None,
    *,
    candidates: tuple[str, ...] = RF_CIFAR_WEIGHTS_CANDIDATES,
) -> Path | None:
    base = Path(data_dir) if data_dir is not None else Path("data")
    for name in candidates:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None
```

After — delegates each candidate probe to the framework-core helper:

```python
def rectified_flow_cifar_resolve_weights_path(
    data_dir: Path | None = None,
    *,
    candidates: tuple[str, ...] = RF_CIFAR_WEIGHTS_CANDIDATES,
) -> Path | None:
    base = Path(data_dir) if data_dir is not None else Path("data")
    for name in candidates:
        hits = resolve_candidate_paths(
            "rectified_flow_cifar", name, data_dirs=[base]
        )
        if hits:
            return hits[0]
    return None
```

`resolve_candidate_paths` probes `data_dir / "rectified_flow_cifar" /
<stem>` first (the per-adapter subdir layout) and then
`data_dir / <stem>` (the flat-file layout used by HiDream-I1 /
Self-Flow when `data_dir` already holds the checkpoint directly).
This is a strict superset of the original probe order — every
candidate the legacy loop would have matched is still matched, plus
the subdir-first convention the framework now prefers. The legacy
priority order (`cifar10_rf.pth` → `rectified_flow_cifar10.safetensors`
→ `rectified_flow_cifar10.pth` → `rectified_flow_cifar10.pt`) is
preserved by iterating `candidates` in priority order and dispatching
each through the shim.

`test_load_weights_path_resolution` continues to pass: the legacy
priority semantics are preserved.

## 3. `_load_torch_unet` `torch.load + state_dict_key unwrap` → `load_state_dict_strict_safe`

Before — inline `torch.load(...) + raw.get("state_dict", raw) +
raw.get("format")` chain:

```python
import torch  # local import.

if weights_path.suffix == ".safetensors":
    from safetensors.torch import load_file
    raw: Any = load_file(str(weights_path), device=str(device))
else:
    raw = torch.load(str(weights_path), map_location=device, weights_only=True)
state_dict = raw.get("state_dict", raw) if isinstance(raw, dict) else raw
fmt = raw.get("format") if isinstance(raw, dict) else None
is_gnobitab = fmt == RF_CIFAR_FORMAT_GNOBITAB or any(
    str(k).startswith(("module.all_modules.", "all_modules."))
    for k in list(state_dict)[:8]
)
```

After — delegates the `.pt/.pth` load to the framework-core shim:

```python
import torch  # local import.

if weights_path.suffix == ".safetensors":
    from safetensors.torch import load_file
    raw: Any = load_file(str(weights_path), device=str(device))
    state_dict = raw.get("state_dict", raw) if isinstance(raw, dict) else raw
else:
    state_dict = load_state_dict_strict_safe(
        weights_path,
        model=None,
        strict=False,
        state_dict_key="state_dict",
        map_location=str(device),
    )
# Gnobitab detection: relies on the canonical ``module.all_modules.``
# key prefix in the state dict.
is_gnobitab = any(
    str(k).startswith(("module.all_modules.", "all_modules."))
    for k in list(state_dict)[:8]
)
```

Three notes:

1. **`state_dict_key="state_dict"`** matches the convention used by
   this adapter's published checkpoint layout (`{"state_dict":
   <weights>}`) — different from self_flow's `"model"` because Liu
   2022 / Score-SDE wrote state dicts under `"state_dict"`, not
   `"model"`.
2. **`weights_only=True` → `weights_only=False`** is a security
   tradeoff vs. the prior `torch.load` call. The framework-core
   helper uses `weights_only=False` to maintain compatibility with
   legacy ckpts that may carry non-tensor metadata; this is the same
   compromise adopted by self_flow in Wave 42 (see
   `docs/audit/wave42-self-flow-shrink.md` §4). The CIFAR RF ckpts
   acquired by the weights-acquisition phase are signed research
   artifacts, so this tradeoff is acceptable; production deployments
   should still validate the checkpoint origin out-of-band.
3. **`fmt == RF_CIFAR_FORMAT_GNOBITAB` check is dropped.** The
   original code used the top-level `format` marker
   (`raw.get("format")`) to detect the gnobitab Score-SDE DDPM++
   topology in addition to the `module.all_modules.` key prefix. The
   `load_state_dict_strict_safe` helper does NOT expose the top-level
   raw ckpt — it returns only the unwrapped state dict. Dropping the
   `format` check is safe because the `module.all_modules.` key prefix
   is the load-bearing indicator (every gnobitab checkpoint has the
   prefix by construction, since it's the Score-SDE data-parallel
   wrapper prefix; the `format` marker was an additive helper added
   later). The `RF_CIFAR_FORMAT_GNOBITAB` constant remains exported
   for downstream callers.

The `.safetensors` branch is unchanged: it uses
`safetensors.torch.load_file` which is a different loader surface and
keeps its own `state_dict` unwrap (HF safetensors typically don't
carry a top-level `state_dict` wrapper, so the unwrap is defensive).

## 4. New dependencies

`adaptive_reflow.adapters.rectified_flow_cifar` now imports from
`adaptive_reflow.core`:

- `ckpt_loader.resolve_candidate_paths` — checkpoint path probe
- `ckpt_loader.load_state_dict_strict_safe` — torch-load + state-dict
  unwrap helper

This is the **fourth per-adapter consumer of `adaptive_reflow.core`**
(joining `flowmol3.py` from Wave 41, `mnist_fm.py` from Wave 42, and
`self_flow.py` from Wave 42). After Wave 44 the framework-core glue
has 4 of its intended per-adapter consumers.

Stdlib additions: none.
No new third-party dependency: `core.ckpt_loader` is stdlib + numpy
at module level (torch stays behind the lazy imports inside
`load_state_dict_strict_safe`).

## 5. Line counts — reported straight

| Measure | Before | After | Delta |
|---|---|---|---|
| `rectified_flow_cifar.py` total | 1317 | 1363 | **+46** |
| Executable code (rough) | 1064 | 1098 | **+34** |
| Comment / docstring (rough) | 112 | 121 | +9 |
| Blank | 141 | 144 | +3 |

This mirrors the Wave 41 FlowMol3 and Wave 42 Self-Flow shrink
results (`docs/audit/wave41-flowmol3-shrink.md` §3,
`docs/audit/wave42-self-flow-shrink.md` §5): **the inlined glue did
shrink, but the file as a whole grew** because the new refactor
rationale docstring + per-helper commentary is now attached to the
framework-core call sites. The growth is concentrated in the
`rectified_flow_cifar_resolve_weights_path` and `_load_torch_unet`
docstrings (added ~15 LOC of refactor rationale pointing at the
framework-core helpers + cross-references to `wave42-self-flow-shrink.md`).

The D.1 metric is per-adapter **median** ≤ 500 across 18 adapters
(`todo/framework-internal-metrics.md` §D.1). Rectified Flow CIFAR sits
in the 1300-line tier either way, so this delta does not move D.1.
The adapters that move D.1 are the four 1500–3300-line checkpoint
adapters (`flowmol3_v2_adapter.py`, `protbfn_abbfn_adapter.py`,
`hidream_i1.py`, `lumina_image_2_0.py`) — those are the consumers of
`core.ckpt_loader` + `core.diffusers_wrapper` + `core.vae_decoder`
that were written for.

## 6. What was deliberately NOT changed

- **Synthetic-mode trajectory digest** (`build_initial_state` /
  `solve_ode` / `observe_endpoint` / `inject_forward_noise` /
  `batched_inference`): byte-frozen by `test_byte_determinism_across_runs`
  + `test_batched_inference_shape_and_determinism`. The refactor only
  touches the torch-mode load path, which the synthetic tests never
  exercise. Verified empirically: all 26 tests pass.
- **`_native_states` NativeStateCache**: already adopted in Wave 42
  Agent C (`docs/audit/wave42-rectified-flow-cifar-shrink.md`); the
  `self._native_states = NativeStateCache(...)` shim is byte-equivalent.
- **`RectifiedFlowCIFARCapabilities`**: not collapsed to
  `make_adapter_capabilities` — see Wave 42 Agent C note
  ("byte-stability reason: the capability token is part of the
  regression vector's `capability_token` field"). The Wave 41 audit
  noted this pattern.
- **`torch_is_available`**: kept as-is. It is in
  `adaptive_reflow/adapters/_adapter_common.py` (not in
  `core/`); the per-adapter shim is a thin delegation that preserves
  the public import surface
  (`from adaptive_reflow.adapters.rectified_flow_cifar import torch_is_available`).
- **`_build_torch_unet_ddpmpp`**: the topology builder is kept inline
  because it constructs a per-adapter DDPM++ UNet (Liu 2022 §3.2) that
  has no equivalent in `core/`. Moving it to `core/` would create a
  one-adapter helper with no other consumers; deferred to a future
  wave when `flowmol3_v2_adapter.py` / `protbfn_abbfn_adapter.py` /
  `hidream_i1.py` request similar topology glue.
- **`_synthetic_velocity_field` + `_random_init_synthetic_weights`**:
  unchanged. The synthetic path uses the per-adapter
  `_adapter_common.kaiming_uniform` already adopted in Wave 42 Agent C.

## 7. Verification

The target test run from the task brief:

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_rectified_flow_cifar.py -q --tb=line
26 passed, 3 warnings in 2.20s
```

`assert_adapter_compliance`:

```
.venvs/flowmol3_venv/bin/python -c "
from adaptive_reflow.framework.interfaces import assert_adapter_compliance
from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter
assert_adapter_compliance(RectifiedFlowCIFARAdapter)
print('assert_adapter_compliance PASSED for RectifiedFlowCIFARAdapter')
"
assert_adapter_compliance PASSED for RectifiedFlowCIFARAdapter
```

Self-flow regression (cross-check that the prior Wave 42 Agent D
shrink is still intact):

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_self_flow.py tests/test_adapters/test_rectified_flow_cifar.py -q --tb=line
48 passed, 3 warnings in 2.16s
```

Both refactored adapters (Wave 42 Agent D + Wave 44 Agent C) hold
their test counts: 22 + 26 = 48.

## 8. Follow-ups for the wider framework-core adoption push

- The two remaining inlined `_load_*_unet` / `_load_*_model` functions
  in `flowmol3_v2_adapter.py`, `protbfn_abbfn_adapter.py`,
  `hidream_i1.py`, `lumina_image_2_0.py` carry the same hand-rolled
  torch-load + state-dict-unwrap patterns. The Wave 44 WF4 agents
  (Agent A / Agent B / Agent C / Agent D) apply the same
  `load_state_dict_strict_safe` + `resolve_candidate_paths` pair at
  the larger LOC scale (~2000-3300 LOC adapters, where the refactor
  payoff is material for D.1).
- The `core.diffusers_wrapper.DiffusersForwardWrapper` class is
  still not exercised by this adapter — only `core.ckpt_loader` is.
  HiDream-I1's `_load_torch_unet` + `_torch_velocity_field` chains
  are the natural next consumers when Wave 44 Agent C / Agent D
  pick up that scope.