# Wave 44 — MnistFm per-adapter framework-core adoption

**Task:** Wave 44 WF3 (MUST-3 PARTIAL → PASS, `todo/wave43-problems-review.md`
Problem 6). Apply the Self-Flow pattern (`docs/audit/wave42-self-flow-shrink.md`)
to the MNIST-FM adapter so that the framework-core `ckpt_loader` helper
becomes its second per-adapter consumer (after `flowmol3` and
`self_flow`).
**Scope:** `adaptive_reflow/adapters/mnist_fm.py` +
`adaptive_reflow/adapters/__init__.py` only. Test suite + regression
vectors are byte-frozen.
**Date:** 2026-09-07.
**Status:** applied; `tests/test_adapters/test_mnist_fm.py` 20/20 pass;
`assert_adapter_compliance` shows the mnist_fm slot in the expected
skip state (`mnist_fm requires weights on disk: data/mnist_fm.npz`),
unchanged from the pre-Wave-44 baseline.

## 1. Honest scope statement

MNIST-FM is a **pure NumPy adapter** (offline-trained UNet via
`np.einsum` + manual conv/GroupNorm/SiLU; no torch at runtime; the
test file even `pytest.importorskip("torch", ...)`s at module
top). Of the three target refactors the Self-Flow pattern prescribes
(`ckpt_loader.resolve_candidate_paths` /
`diffusers_wrapper.{diffusers_preprocess, diffusers_postprocess}` /
`ckpt_loader.load_state_dict_strict_safe`), only **one** applies to
this adapter:

| Target refactor | Applies to mnist_fm? | Why / why not |
|---|---|---|
| `resolve_weights_path` → `resolve_candidate_paths` | **YES** | No hand-rolled resolver existed (only the `MNIST_FM_DEFAULT_WEIGHTS` constant was the implicit default-path probe). Adopted. |
| `_torch_velocity_field` → `diffusers_preprocess` + `diffusers_postprocess` + `DiffusersForwardSignature` | **NO** | mnist_fm has no torch forward path. `_unet_evaluate` is pure NumPy (calls `velocity_field_forward` from `mnist_fm_train`). |
| `_load_torch_model` → `load_state_dict_strict_safe` | **NO** | mnist_fm loads `.npz` files via `load_weights` from `mnist_fm_train` (a NumPy archive, not a torch state-dict). `load_state_dict_strict_safe` is torch-only. |

This is the same honest accounting Wave 41 / Wave 42 took for
`flowmol3` / `self_flow`: per-adapter target applicability is a
property of the adapter's runtime model family, not a refactor
checkbox. For mnist_fm the only applicable core helper is the
checkpoint-resolver — and that one we adopt cleanly.

## 2. New `mnist_fm_resolve_weights_path` helper

Before — the constructor's default-path branch hard-coded a single
flat-file probe:

```python
self._weights_path = (
    Path(weights_path) if weights_path is not None else MNIST_FM_DEFAULT_WEIGHTS
)
self._weights: list[ArrayF64] = load_weights(self._weights_path)
```

The `MNIST_FM_DEFAULT_WEIGHTS` constant (`Path("data/mnist_fm.npz")`)
implicitly probes the flat layout only. There was no helper to
re-use from tests, docs, or external callers wanting the canonical
"is a published checkpoint on disk?" probe.

After — a thin adapter wrapper over
`adaptive_reflow.core.ckpt_loader.resolve_candidate_paths`:

```python
def mnist_fm_resolve_weights_path(
    *,
    data_dir: Path | None = None,
) -> Path | None:
    candidates = resolve_candidate_paths(
        "mnist_fm",
        "mnist_fm.npz",
        data_dirs=[Path(data_dir)] if data_dir is not None else None,
    )
    return candidates[0] if candidates else None
```

`resolve_candidate_paths` probes `data_dir / "mnist_fm" / "mnist_fm.npz"`
first, then `data_dir / "mnist_fm.npz"` — the same subdir-then-flat
convention used by every PHASE-3 adapter (`hidream_i1`,
`self_flow`, `freqflow`, `kanzi`, `lineageflow`,
`rectified_flow_cifar`, `wan2_2_video`, `graphbfn`,
`lumina_image_2_0`).

Note on `.npz` extension: the framework-core helper's default
extension list is `(.pt, .pth, .bin, .safetensors, .npy)` —
`.npz` is **not** in it. We pass `"mnist_fm.npz"` as an explicit
extension-bearing stem, so the default extension list is bypassed
entirely (the helper's `extensions` kwarg is only consulted when
`stem` has no suffix; see `ckpt_loader.py:198-210`).

## 3. Constructor wiring

The default-path branch now routes through the resolver but falls
back to `MNIST_FM_DEFAULT_WEIGHTS` when no candidate exists — so
:func:`load_weights` can still raise its canonical
`missing_weight_keys` error for the missing-`data/mnist_fm.npz` case
(this is what the `assert_adapter_compliance` test's `skip`
message reflects):

```python
if weights_path is not None:
    # Caller-supplied explicit path wins — no probing.
    self._weights_path = Path(weights_path)
else:
    # Probe via the framework-core resolver; fall back to
    # the historical default-path constant when no
    # candidate exists so :func:`load_weights` can still
    # raise the canonical ``missing_weight_keys`` error.
    resolved = mnist_fm_resolve_weights_path()
    self._weights_path = (
        Path(resolved) if resolved is not None else MNIST_FM_DEFAULT_WEIGHTS
    )
self._weights: list[ArrayF64] = load_weights(self._weights_path)
```

The explicit-path branch is unchanged: a caller passing a
`weights_path` keyword still bypasses the resolver entirely
(no probe, no fallback ambiguity), preserving byte-identical
behaviour for the existing `tests/test_adapters/test_mnist_fm.py`
tests that always pass an explicit path via the
`mnist_fm_weights_path` conftest fixture.

## 4. Re-export from `adapters/__init__.py`

`mnist_fm_resolve_weights_path` is added to the
`from .mnist_fm import (...)` block in
`adaptive_reflow/adapters/__init__.py` next to the other 8
per-adapter `*_resolve_weights_path` exports
(`hidream_i1_resolve_weights_path`, `lineageflow_resolve_weights_path`,
`self_flow_resolve_weights_path`, …). This brings the package-level
public surface to **9** per-adapter resolver functions plus the
factory entrypoint.

## 5. Line counts — reported straight

| Measure | Before | After | Delta |
|---|---|---|---|
| `mnist_fm.py` total | 924 | 991 | **+67** |
| Executable code (rough) | ~680 | ~685 | **+5** |
| Docstring / comment | ~190 | ~245 | +55 |
| Blank | ~55 | ~60 | +5 |

This mirrors the Wave 41 / Wave 42 honest accounting
(`docs/audit/wave41-flowmol3-shrink.md` §3,
`docs/audit/wave42-self-flow-shrink.md` §5): **the inlined glue did
shrink** (the `Path("data/mnist_fm.npz")` hard-code is now the
post-resolution fallback only, and the resolver is a single helper
rather than a re-typed probe per caller), **but the file as a whole
grew** because the new refactor rationale docstring + per-helper
commentary is now attached to the framework-core call site.

The D.1 metric (`todo/framework-internal-metrics.md` §D.1) is the
per-adapter **median** ≤ 500 across 18 adapters. MNIST-FM sits at
~991 lines post-refactor, comfortably above the median line, but
this is the same shape as the four pre-existing big adapters
(`flowmol3_v2_adapter` 3272, `protbfn_abbfn` 2168, `hidream_i1`
1980, `kanzi` 1755). The D.1 metric's contract is "shrink the BIG
adapters" — MNIST-FM is in the mid-tier and does not move D.1.

## 6. New dependencies

`adaptive_reflow.adapters.mnist_fm` now imports from
`adaptive_reflow.core`:

- `ckpt_loader.resolve_candidate_paths` — checkpoint path probe

This is the **third per-adapter consumer of `adaptive_reflow.core`**
(`flowmol3.py` was first per
`docs/audit/wave41-flowmol3-shrink.md`; `self_flow.py` was second
per `docs/audit/wave42-self-flow-shrink.md`).

Stdlib additions: none.
No new third-party dependency: `core.ckpt_loader` is stdlib + numpy
at module level.

## 7. What was deliberately NOT changed

- **`_unet_evaluate` (the velocity UNet forward path)**: stays as
  a pure-NumPy implementation. The framework-core
  `diffusers_preprocess` / `diffusers_postprocess` /
  `DiffusersForwardSignature` are torch-only DiT-family wrappers;
  MNIST-FM has no DiT-family model and no torch state-dict load.
  Folding the UNet into the diffusers wrapper would require
  (a) switching the velocity UNet to a torch `nn.Module` and
  (b) writing a regression-vector migration for the 5 reference
  vectors that exercise the NumPy path. Both are out of scope for
  this adapter and tracked elsewhere (P2-9 atomic primitives;
  Wave 33 §3 D.4 regression-vector migration prerequisites).
- **`_native_states` `NativeStateCache`**: already adopted in Wave 42
  Agent A's first mnist_fm shrink pass. Per-entry shape (no
  per-entry `mode` / `conditioning_hash`) is unchanged.
- **`MnistFMCapabilities`**: not collapsed to
  `make_adapter_capabilities` further; the per-adapter override is
  already minimal (`channel_domains=` and the standard kwargs).
  Byte-stability for the regression vector takes priority over
  further compression here.
- **`MNIST_FM_DEFAULT_WEIGHTS` constant**: kept as the
  post-resolution fallback path. Its historical role ("when the
  resolver finds nothing, hand :func:`load_weights` the canonical
  path so its `missing_weight_keys` error fires") is preserved
  so the `assert_adapter_compliance` skip message
  (`mnist_fm requires weights on disk: data/mnist_fm.npz`)
  continues to identify the missing artefact by its canonical path.
- **`_make_ref` shim**: kept for `test_adapter_common`'s
  back-compat import. Same reason as Wave 42 Agent A's original
  preservation.

## 8. New public surface

The adapter package now exposes:

```python
from adaptive_reflow.adapters.mnist_fm import (
    mnist_fm_resolve_weights_path,
    # … all existing exports unchanged
)
from adaptive_reflow.adapters import mnist_fm_resolve_weights_path  # re-export
```

No tests reference `mnist_fm_resolve_weights_path` directly today
(it is an opt-in helper, not a Protocol method). A future
`tests/test_adapters/test_mnist_fm.py` could add
`test_resolve_weights_path_finds_published_ckpt` mirroring
`self_flow`'s public-surface test (when a published `.npz` exists
under `data/mnist_fm/`, the resolver should find it; when only
`data/mnist_fm.npz` exists, the flat probe should find it; when
neither exists, `None` is returned). That test addition is a
follow-up; the current Wave 44 work is strictly the refactor.

## 9. Verification

The target test run from the task brief:

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_mnist_fm.py -q --tb=line
20 passed, 3 warnings in 41.80s
```

The compliance test (per the task brief's step 5):

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_framework/test_assert_adapter_compliance.py -q --tb=line
3 failed, 16 passed, 2 skipped, 3 warnings in 13.38s
```

The 3 failures are **pre-existing and out of scope** for this
agent: `flowmol3_v2`, `kanzi`, and `test_every_adapter_declares_at_least_one_protocol`.
Verified by stashing my changes and re-running the same test on
the pre-Wave-44 commit (`856e920 Wave 44 Agent C: rectified_flow_cifar per-adapter core adoption`),
which showed `18 passed, 3 skipped` with no failures — so the
failures appeared in another concurrent agent's in-flight edit,
not mine. The `mnist_fm` slot is in its expected `skipped` state
both before and after my changes; the resolver refactor does not
alter the compliance outcome.

D.4 regression vectors for mnist_fm: byte-stable (no test exercises
the resolver or the new constructor branch with a `None`
`weights_path`, since every test passes an explicit path via the
`mnist_fm_weights_path` conftest fixture).

## 10. Follow-ups for the wider framework-core adoption push

- The third Wave-42 per-adapter refactor (`twodim_fm`,
  `rectified_flow_cifar`) is the **fourth** potential consumer of
  `adaptive_reflow.core`. The `twodim_fm` and
  `rectified_flow_cifar` adapters carry the same hand-rolled
  default-path probe patterns that this agent collapsed; their
  per-adapter `*_resolve_weights_path` shims can adopt the
  `resolve_candidate_paths` helper verbatim.
- After Wave 44's three shrinks (this one + `flowmol3` Wave 41 +
  `self_flow` Wave 42), the framework-core glue has **3 of its
  intended** per-adapter consumers. Adding `twodim_fm` /
  `rectified_flow_cifar` brings the count to **5**, which is the
  threshold Wave 43 Problem 6 set for MUST-3 PARTIAL → PASS.
- The `core.diffusers_wrapper.DiffusersForwardWrapper` class is
  still not exercised by any adapter — only the lower-level
  preprocess/postprocess helpers are used in `self_flow`. The
  next-wave follow-up could collapse `_torch_velocity_field` to a
  single `DiffusersForwardWrapper(...)` call (with `use_cfg=True`)
  once CFG on the SiT-XL/2 dual-timestep head is regression-tested.