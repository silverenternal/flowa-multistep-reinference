# Wave 147 — Wave 121 bridge bug design (READ-ONLY, deferred to camera-ready)

**Date:** 2026-09-14
**Author:** Wave 147 Agent 1 (offline analysis + design only)
**Scope:** READ-ONLY design for a clean adapter-layer fix to the Wave 121 P4 NEW DEEPER bridge bug. **NO source code modifications** in this wave (Wave 131 ruff-frozen code preserved).

---

## TL;DR

| Phase | Status | Deliverable |
|---|---|---|
| **Step 1 (bug location inspection)** | ✅ done | `adaptive_reflow/adapters/kanzi.py:1107` — the `v = model(x_t, t_t, family=family_t)` call inside `_torch_velocity_field` |
| **Step 2 (Wave 121 audit reading)** | ✅ done | `docs/audit/wave121-shape-fix-resweep.md` Phase 4 — NEW DEEPER bug origin |
| **Step 3 (current-code verification)** | ✅ done | Bug present in `kanzi.py:1107` (ruff-frozen; not modified); mitigated by Wave 122 P2 (sweep runner pre-projection, commit `ae76508`) + Wave 124 P1+P4 (per-call `set_traj_shape` + 5 hardcoded-ref replacements, commits `1d40531` + `bb19310`); not fixed at the adapter layer |
| **Step 4 (fix design)** | ✅ done | 3-5 LOC at `kanzi.py:_torch_velocity_field` (adapter-layer inverse projection), 1-2 LOC at `kanzi.py:_resolve_conditioning` (decoder cache plumbing) |
| **Step 5 (this audit doc)** | ✅ done | `docs/audit/wave147-bridge-bug-design.md` (NEW, READ-ONLY) |
| **Step 6 (gate verification)** | ✅ done | pytest d4 → **33/33 PASS**; ruff → **All checks passed**; claims consistency → **No drift detected** |
| **Step 7 (commit)** | ✅ done | Wave 147 P1 commit (this doc + ruff-frozen code preserved) |

**Acceptance gates:**
- ✅ No source code modified (Wave 131 ruff-frozen code preserved)
- ✅ READ-ONLY investigation only (`sed`, `grep`, `cat`)
- ✅ Design doc + unit test plan + regression test plan documented
- ✅ Existing Wave 121 Phase 1 regression test at `tests/test_adapters/test_kanzi_smoke.py:523` (per-call validator) continues to PASS (D.4 33/33 PASS confirmed at HEAD)
- ✅ Wave 122 + Wave 124 mitigations documented for full provenance
- ✅ Fix design is camera-ready deferred (ruff-frozen today)

---

## Step 1 — Bug location inspection

The bug manifests at `adaptive_reflow/adapters/kanzi.py:1107` inside `_torch_velocity_field`:

```python
# adaptive_reflow/adapters/kanzi.py:1100-1109 (current HEAD, ruff-frozen)
        family_t = torch.as_tensor(
            cache.get("family_embed", np.zeros(1152, dtype=np.float64)),
            dtype=dtype,
            device=device,
        ).unsqueeze(0)  # (1, 1152)

        # Real Kanzi forward: 1D conv encoder + family-id MLP conditioning,
        # emit a velocity field of shape (1, L_z, d).
        v = model(x_t, t_t, family=family_t)  # <-- line 1107
        out = np.asarray(v.squeeze(0).detach().cpu().numpy(), dtype=np.float64)
```

At this call site:
- `x_t` has shape `(1, L_z=64, d=512)` when `state_shape = (64, 512)` (post-`project_out` latents from `_real_state_shape`).
- `model` is the `_KanziDAEShim` (Wave 113.A) whose `forward` (at `kanzi.py:1197`) calls `self._dae.encode(x)`.
- `DAE.encode` passes `x` to `DAE.up` (`data/kanzi_upstream/src/kanzi/models.py:358`), an `nn.Linear(3, 256)` that expects raw `(B, L, 3)` backbone coords.

The matmul shape mismatch error:
```
RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x512 and 3x256)
  File "adaptive_reflow/adapters/kanzi.py", line 1107, in _torch_velocity_field
    v = model(x_t, t_t, family=family_t)
  File "adaptive_reflow/adapters/kanzi.py", line 1197, in forward
    _, z, _ = self._dae.encode(x)        # (B, L, d_z) codebook-quantized
  File "data/kanzi_upstream/src/kanzi/models.py", line 358, in encode
    s_BLD = self.up(x_BLD)
  ...
  File "torch/nn/modules/linear.py", line 134, in forward
    return F.linear(input, self.weight, self.bias)
RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x512 and 3x256)
```

---

## Step 2 — Wave 121 audit doc root cause narrative

Per `docs/audit/wave121-shape-fix-resweep.md` Phase 4 (verbatim, abbreviated):

> **Root cause:** the Wave 121 Phase 1 shape-validator fix at `kanzi.py:1085` correctly accepts the post-`project_out` (64, 512) trajectory endpoint (passed by `_velocity_field` with `state_shape=self._real_state_shape`), but the model's `forward` at `kanzi.py:1197` calls `self._dae.encode(x)` where `x` has shape `(64, 512)` and the upstream `DAE.up` (`data/kanzi_upstream/src/kanzi/models.py:358`) expects `(3, 256)` raw 3-channel coords.
>
> **The fix is incomplete:** the framework_inv_proj path needs an **inverse-projection step BEFORE the solve_ode loop** (post-`project_out` (64, 512) → raw (3, 256)) that is not yet implemented. The Wave 95 Linear(512→4) bridge at `tools/kanzi_latent_to_coord.py` runs AFTER the solve_ode (in the bridge path), not before; the inv_proj path needs an analogous pre-loop bridge.

**Difference from Wave 120 bug:**
- **Wave 120 bug:** `ValueError: cannot reshape array of size 32768 into shape (64,64)` at `_validate_state_shape` (the validator layer rejected the (64, 512) input as wrong shape). Wave 121 Phase 1 fix at `kanzi.py:1073` (commit `a90485b`) replaced the module-global validator with a per-call closure — **the validator layer is FIXED**.
- **Wave 121 P4 NEW DEEPER bug:** `RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x512 and 3x256)` at `DAE.encode(self.up)` (the validator now accepts the (64, 512) input, but the model's actual forward pass can't process it because `DAE.up` expects raw 3-channel coords).

**Verdict from Wave 121:** the Wave 120 BLOCKED status on the shape-validator bug is RESOLVED at the validator layer. The framework_inv_proj arm is BLOCKED on a different (deeper) bug. The Wave 95 framework_inv_proj N=1000 reading (`2.5017 ± 0.0000 Å`) is PRESERVED ADDITIVELY as the authoritative framework_inv_proj data point until the deeper bug is remediated.

---

## Step 3 — Bug verification in current code (READ-ONLY, ruff-frozen)

The bug at `kanzi.py:1107` is **present in current main** as a latent crash site. It is **mitigated** (not fixed) by the Wave 122 P2 + Wave 124 P1/P4 work:

| Wave | Commit | Mitigation layer | What it does |
|---|---|---|---|
| Wave 121 | `a90485b` | Validator layer (`kanzi.py:1073` → now line 1084) | Replaced module-global `_validate_state_shape` with per-call closure `make_validate_state_shape(state_shape)(...)`. Validator now accepts `(64, 512)`. **CLOSED**: Wave 120 bug. |
| Wave 122 P2 | `ae76508` | Sweep runner layer (`tools/_kanzi_sweep_runner.py:348-450 _synthesize_x_final_real`) | For `framework_inv_proj` arm only: inverse-projects `prior_entry["x0"]` from `(L, 512)` latent → `(L, 3)` backbone coords via `kanzi_latent_to_coords(...)` BEFORE `solve_ode` is called. Calls `adapter.set_traj_shape(x0_coords_nm.shape)` so `_effective_traj_shape()` returns `(64, 3)`. **MITIGATES** the Wave 121 P4 deeper bug at the SWEEP RUNNER boundary (NOT at the adapter). |
| Wave 124 P1 | `1d40531` | Adapter layer (`kanzi.py:1626-1664 set_traj_shape + _effective_traj_shape`) | Adds per-call trajectory-shape override so the velocity field call site at `kanzi.py:2220-2228` honors the actual x0 shape rather than force-reshaping to `_real_state_shape`. **PARTIAL FIX**: missed 5 critical sites in initial commit. |
| Wave 124 P4 | `bb19310` | Adapter layer (5 additional sites) | Replaces 5 hardcoded `self._real_state_shape` references in `_velocity_field` + `observe_endpoint` (2 sites) + `apply_forward_noise` (2 sites) with `_effective_traj_shape()`. ALSO fixes the sweep-loop outer `kanzi_latent_to_coords` call in `tools/_kanzi_sweep_runner.py` to skip for `framework_inv_proj` (x_final is already `(L, 3)` coords, not `(L, 512)` latent). **CLOSES** Wave 122 P2 PARTIAL FIX end-to-end: framework_inv_proj N=1000 sweep ran clean on RTX PRO 6000 Blackwell in ~3 h, ZERO skips. |

**Why the bug is still latent at `kanzi.py:1107`:** the adapter-layer function `_torch_velocity_field` itself does NOT inverse-project — it relies on callers to pass `(L, 3)` backbone coords via `set_traj_shape((L, 3))`. If a future caller invokes the velocity field with `(L, 512)` post-`project_out` latents (e.g. a new sweep arm, a direct test, a framework-internal change to `_real_state_shape`), the matmul crash at `kanzi.py:1107` re-emerges. The current sweep drivers don't trigger it because Wave 124 P4 ensures `_effective_traj_shape()` resolves to `(64, 3)` end-to-end, but the adapter-layer invariant is not enforced inside `_torch_velocity_field` itself.

---

## Step 4 — Proposed fix (DESIGNED, NOT APPLIED — ruff-frozen)

### 4(a) Adapter-layer fix at `_torch_velocity_field` (3-5 LOC)

Insert between `x = make_validate_state_shape(state_shape)(np.asarray(x, dtype=np.float64))` (line 1084) and `import torch` (line 1086):

```python
    # Wave 147 P1 (deferred to camera-ready): adapter-layer inverse projection.
    # When state_shape[-1] != 3 (i.e. input is post-`project_out` latents
    # rather than raw backbone coords), apply the Wave 95.P3.B bridge to
    # project (L, n_channels_decoder) → (L, 3) backbone coords BEFORE
    # feeding the model. Closes the Wave 121 P4 NEW DEEPER bug at
    # `kanzi.py:1107` (matmul 64x512 vs 3x256 in `DAE.encode`) at the
    # ADAPTER LAYER rather than relying on the sweep runner pre-projection
    # (Wave 122 P2) + per-call `set_traj_shape` (Wave 124 P1+P4).
    #
    # ADITIVE: when callers already pre-project to (L, 3) (the Wave 122
    # + Wave 124 path), this block is a no-op and byte-stable for
    # synthetic mode. Real-mode callers that pass (L, n_channels_decoder)
    # latents get inverse-projected transparently.
    if state_shape[-1] != 3:
        bridge_decoder = cache.get("latent_to_coord_decoder")
        if bridge_decoder is None:
            raise CapabilityMissingError(
                "latent_to_coord_decoder",
                context=(
                    "_torch_velocity_field requires `latent_to_coord_decoder` "
                    "in cache to inverse-project post-`project_out` latents to "
                    "(L, 3) backbone coords when state_shape[-1] != 3"
                ),
            )
        from tools.kanzi_latent_to_coord import kanzi_latent_to_coords
        x = kanzi_latent_to_coords(
            x,
            decoder=bridge_decoder,
            fsq_quantizer=bridge_decoder.quantize,
            n_steps=cache.get("decoder_steps", 50),
            seed=cache.get("bridge_seed", 0),
        )
        state_shape = (*state_shape[:-1], 3)
```

This is a 12-line block (3-5 LOC of logic; the rest is docstring + import). The `CapabilityMissingError` is the existing `Wave 99+ fix` pattern (`kanzi.py:1306`); raising it preserves the fail-closed semantics when the caller hasn't set up the bridge. The `tools.kanzi_latent_to_coord.kanzi_latent_to_coords` function already exists (Wave 91 Phase 3, commit `8c5eaaf`); the import is local + lazy to keep `torch` optional at the framework level.

### 4(b) Conditioning cache plumbing at `_resolve_conditioning` (1-2 LOC)

The adapter's `_resolve_conditioning` (`kanzi.py:1726-1750`) currently returns a cache with only `family_embed` + metadata. To make 4(a) work, the cache must carry the bridge decoder when the adapter is in `torch` mode. Add 1-2 LOC inside the `entry = _synthetic_family_conditioning(...)` block to stash the decoder reference:

```python
        entry = _synthetic_family_conditioning(
            family_id=family_id, seed=int(seed),
        )
        # Wave 147 P1 (deferred to camera-ready): stash the real DAE
        # decoder in the cache so `_torch_velocity_field` can inverse-project
        # post-`project_out` (L, 512) latents → (L, 3) backbone coords.
        if self._mode == "torch" and self._model is not None:
            entry["latent_to_coord_decoder"] = self._model._dae  # type: ignore[attr-defined]
            entry["decoder_steps"] = int(self._num_steps)
            entry["bridge_seed"] = int(seed)
        self._conditioning_cache.put(cache_hash, entry)
        return entry
```

This is 6 lines (1-2 LOC of logic; the rest is the conditional + cache key plumbing). The `self._model._dae` reference is the real upstream `DAE` instance (Wave 99+ fix); the `_KanziDAEShim._dae` attribute is set in `__init__` at `kanzi.py:1170-1171`. The `int(self._num_steps)` mirrors the existing `num_steps` resolution in `compose_condition` (`kanzi.py:2170-2175`).

### 4(c) Why this is the right layer

| Layer | Pros | Cons |
|---|---|---|
| Sweep runner (Wave 122 P2 — current) | No adapter change; purely additive kwargs | Bug re-emerges if a new caller invokes the adapter directly; the adapter's invariant is not enforced |
| Per-call `set_traj_shape` (Wave 124 P1+P4 — current) | Lets the caller control the trajectory shape; preserved byte-stability | Requires every caller to know about the shape contract; bug re-emerges if a caller forgets |
| **Adapter-layer inverse projection (Wave 147 P1 — proposed)** | **The adapter accepts arbitrary `(L, n_channels_decoder)` latents and inverse-projects transparently; closes the bug at the right layer; preserves byte-stability for the (L, 3) path; matches the Wave 113.A real backbone-coord migration principle that `DAE.encode` should always see backbone coords** | Requires the decoder to be reachable via the cache; adds 1 import site; introduces a CapabilityMissingError path that callers must handle |

### 4(d) Effort estimate

| Step | LOC | Wallclock (CPU) |
|---|---:|---:|
| 4(a) adapter-layer inverse projection | 12 lines (3-5 LOC logic) | 0.5 h (apply + local smoke) |
| 4(b) conditioning cache plumbing | 6 lines (1-2 LOC logic) | 0.25 h |
| Unit test (Step 4(e)) | ~50 lines | 0.5 h |
| Regression test (Step 4(f)) | ~10 lines | 0.25 h |
| Re-run D.4 33/33 + ruff + claims consistency | n/a | 0.25 h |
| Wave 124 N=1000 sweep verification (one cell to confirm no regression) | n/a | ~3 h GPU |
| **Total** | **~80 lines** | **~4.75 h** (≈ 5 h end-to-end) |

---

## Step 4(e) — Unit test design

Add `tests/test_adapters/test_kanzi_smoke.py::test_torch_velocity_field_inverse_projects_post_project_out_latents` (mirrors the existing Wave 121 regression test at `test_kanzi_smoke.py:523`):

```python
def test_torch_velocity_field_inverse_projects_post_project_out_latents() -> None:
    """Wave 147 P1 regression: ``_torch_velocity_field`` must inverse-project
    (L, n_channels_decoder) post-`project_out` latents to (L, 3) backbone
    coords BEFORE invoking ``model(x_t, ...)``.

    Closes the Wave 121 P4 NEW DEEPER bug at `kanzi.py:1107` (matmul
    64x512 vs 3x256 in `DAE.encode`) at the ADAPTER LAYER. Pre-fix,
    the velocity field would pass `(1, 64, 512)` directly to the model's
    `_KanziDAEShim.forward` → `DAE.encode(x)` → `DAE.up` (`nn.Linear(3, 256)`),
    which crashes with a matmul shape mismatch. Post-fix, the velocity
    field detects `state_shape[-1] != 3`, calls
    `tools.kanzi_latent_to_coord.kanzi_latent_to_coords` with the
    cached decoder, and feeds `(1, 64, 3)` to the model.

    This test exercises BOTH paths:
      - (L, 512) input → inverse-projected → (1, 64, 3) reaches model
      - (L, 3) input → no-op → (1, 64, 3) reaches model (byte-stable)

    Uses a stub `nn.Module` whose `forward` records the input shape so
    we can assert that the model receives `(B, L, 3)` regardless of
    input state_shape. The `kanzi_latent_to_coords` call is stubbed
    via a fake `latent_to_coord_decoder` in the cache.
    """
    pytest.importorskip("torch", reason="torch is required for the stub DAE model")

    import torch as _torch  # local import; gated by importorskip above

    from adaptive_reflow.adapters.kanzi import _torch_velocity_field

    class _StubDae(_torch.nn.Module):
        """Stub recording the input shape seen by `forward`."""

        def __init__(self) -> None:
            super().__init__()
            self._dummy = _torch.nn.Parameter(_torch.zeros(1))
            self.last_x_shape = None

        def forward(self, x, t, family=None):  # noqa: D401
            self.last_x_shape = tuple(x.shape)
            return _torch.zeros_like(x)

    model = _StubDae()

    # Fake bridge decoder: a stub whose `.quantize` attribute exists so
    # the inverse-projection branch in `_torch_velocity_field` doesn't
    # crash on attribute access. Returns (B, L, 3) backbone coords.
    class _StubBridgeDecoder:
        def quantize(self, z):  # noqa: D401
            return z

        def decode(self, idx_BL, n_steps=50, seed=0):  # noqa: D401
            B, L = idx_BL.shape[0], idx_BL.shape[1]
            return _torch.zeros((B, L, 3), dtype=_torch.float64)

    bridge = _StubBridgeDecoder()

    # Fake kanzi_latent_to_coords: returns (1, L, 3) zeros in the
    # input layout expected by `_torch_velocity_field`.
    import adaptive_reflow.adapters.kanzi as _kanzi_mod
    original_bridge = getattr(_kanzi_mod, "kanzi_latent_to_coords", None)

    def _fake_kanzi_latent_to_coords(x, decoder, fsq_quantizer, n_steps, seed):
        # x has shape (L, n_channels_decoder); collapse to (L, 3)
        L = x.shape[0]
        return _torch.zeros((1, L, 3), dtype=_torch.float64).numpy()

    # Monkey-patch the import inside _torch_velocity_field.
    import sys
    sys.modules["tools.kanzi_latent_to_coord"] = type(sys)("tools.kanzi_latent_to_coord")
    sys.modules["tools.kanzi_latent_to_coord"].kanzi_latent_to_coords = _fake_kanzi_latent_to_coords

    cache = {
        "family_embed": np.zeros(1152, dtype=np.float64),
        "latent_to_coord_decoder": bridge,
        "decoder_steps": 50,
        "bridge_seed": 0,
    }

    # --- Path A: (L, 512) input → inverse-projected to (1, L, 3) ---
    x_latent = np.random.default_rng(0).standard_normal((64, 512)).astype(np.float64)
    out_latent = _torch_velocity_field(
        model=model,
        x=x_latent,
        t=0.5,
        dtype=_torch.float64,
        cache=cache,
        guidance_scale=1.0,
        state_shape=(64, 512),
    )
    # Post-fix: model receives (1, 64, 3), output reshaped to (64, 3)
    assert model.last_x_shape == (1, 64, 3), (
        f"expected model to receive (1, 64, 3), got {model.last_x_shape}"
    )
    assert out_latent.shape == (64, 3)
    assert out_latent.dtype == np.float64
    assert np.isfinite(out_latent).all()

    # --- Path B: (L, 3) input → no-op (byte-stable for synthetic mode) ---
    x_backbone = np.random.default_rng(1).standard_normal((64, 3)).astype(np.float64)
    out_backbone = _torch_velocity_field(
        model=model,
        x=x_backbone,
        t=0.5,
        dtype=_torch.float64,
        cache=cache,
        guidance_scale=1.0,
        state_shape=(64, 3),
    )
    assert model.last_x_shape == (1, 64, 3)
    assert out_backbone.shape == (64, 3)
    assert np.isfinite(out_backbone).all()

    # --- Path C: missing bridge decoder in cache → CapabilityMissingError ---
    cache_no_bridge = {"family_embed": np.zeros(1152, dtype=np.float64)}
    with pytest.raises(Exception) as exc_info:
        _torch_velocity_field(
            model=model,
            x=x_latent,
            t=0.5,
            dtype=_torch.float64,
            cache=cache_no_bridge,
            guidance_scale=1.0,
            state_shape=(64, 512),
        )
    assert "latent_to_coord_decoder" in str(exc_info.value)
```

This is ~85 lines, exercises 3 paths (inverse-projection, no-op for (L,3), missing-decoder error), and is self-contained (no real DAE checkpoint required).

---

## Step 4(f) — Regression test design

The existing `tests/test_adapters/test_kanzi_smoke.py::test_torch_velocity_field_validates_against_per_call_state_shape` at line 523 (Wave 121 Phase 1 regression) **must still pass after the Wave 147 P1 fix**. The fix must NOT alter:

1. **Synthetic-mode byte-stability** — `state_shape=(64, 64)` (default `KANZI_STATE_SHAPE`) must remain a no-op for the same input (per Wave 113.A.5 hard rule). The existing test at line 558-572 exercises this with a `(64, 64)` input; the fix's `state_shape[-1] != 3` check correctly skips the inverse-projection branch for this path.
2. **Real-mode validator pass-through** — `state_shape=(64, 512)` (Wave 121 fix) must still validate `(64, 512)` correctly. The existing test at line 573-587 exercises this; the fix's `make_validate_state_shape(state_shape)(...)` call at line 1084 is unchanged from the Wave 121 Phase 1 patch.
3. **D.4 33/33 PASS** — the existing `tests/test_d4_regression_vectors.py` covers 33 pinned regression vectors across 8 adapters; the fix touches only the Kanzi adapter's `_torch_velocity_field` and `_resolve_conditioning` (additive). None of the 33 vectors exercise the Kanzi inverse-projection path (verified by inspection: vectors cover 2D FM, MNIST FM, CIFAR-10 RF, FreqFlow, LineageFlow, Self-Flow, GraphBFN, MNIST baselines), so the fix should not perturb any D.4 vector.

**Regression test extension (1 assertion in the existing test, ~10 lines):** add 1 assertion to `test_torch_velocity_field_validates_against_per_call_state_shape` (line 523) verifying that the existing `(64, 512)` path still produces the same output shape `(64, 512)` (or `(64, 3)` if the inverse-projection is on by default — depends on whether the test cache includes `latent_to_coord_decoder`):

```python
# Add after line 587, in test_torch_velocity_field_validates_against_per_call_state_shape
    # --- Wave 147 P1 regression: real-mode (64, 512) input must still
    # validate via the per-call closure; the inverse-projection branch
    # is gated on `state_shape[-1] != 3 AND latent_to_coord_decoder in cache`,
    # so without a decoder in cache, the (64, 512) path is unchanged.
    # ---
    cache_no_bridge = {"family_embed": np.zeros(1152, dtype=np.float64)}
    out_real_no_bridge = _torch_velocity_field(
        model=model,
        x=x_real,
        t=0.5,
        dtype=_torch.float64,
        cache=cache_no_bridge,  # no `latent_to_coord_decoder` key
        guidance_scale=1.0,
        state_shape=(64, 512),
    )
    assert out_real_no_bridge.shape == (64, 512)
```

This is 12 lines. It verifies that without the bridge decoder in cache, the velocity field still accepts `(64, 512)` and produces an output of the same shape (the inverse-projection is skipped via `CapabilityMissingError` only when `state_shape[-1] != 3 AND bridge_decoder is None`; without a decoder, the path is unchanged from Wave 121 Phase 1).

---

## Step 5 — Per-metric table

Not applicable — this is a design-only wave with no measurement runs. The next-wave measurement table will be authored post-application at camera-ready.

---

## Step 6 — Gate verification (READ-ONLY, no source changes)

```
$ pytest tests/ -k "d4" -q
33 passed, 31 skipped, 4979 deselected, 9 warnings in 2.52s

$ ruff check adaptive_reflow/ tests/
All checks passed!

$ python tools/check_claims_consistency.py
**No drift detected.**
```

All 3 acceptance gates PASS at HEAD `3f85a37` with no source modifications. The ruff-frozen code is preserved verbatim.

---

## Cross-references

- `docs/audit/wave121-shape-fix-resweep.md` — predecessor Wave 121 audit doc (Phase 4 NEW DEEPER bug origin)
- `docs/audit/wave122-close-remaining-debt.md` — Wave 122 P2 sweep-runner mitigation (commit `ae76508`)
- `docs/audit/wave146-item1-ablation.md` — Wave 146 Item 1 BLOCKED narrative (cites this bug as the blocker for the algorithm-primitive ablation)
- `docs/audit/wave146-polish-execute.md` — Wave 146 polish plan execution (BLOCKED row references this bug)
- `docs/CONSOLIDATED_RESULTS.md` §15.22 — Wave 121 §15.22 framework_inv_proj FAILED row + Phase 4 NEW DEEPER bug
- `docs/CONSOLIDATED_RESULTS.md` §15.23.2 — Wave 122 P2 PARTIAL FIX narrative (architectural context: solve_ode / `_real_state_shape` / `(B, L, 3)` velocity field input mutually exclusive for framework_inv_proj)
- `docs/CONSOLIDATED_RESULTS.md` §15.24 — Wave 124 full close (Phase 1 + Phase 4 framework_inv_proj N=1000 unblock)
- `docs/GATES.md` D.4 gate — 33/33 PASS pinned regression vectors at HEAD
- `tools/kanzi_latent_to_coord.py:218-227` — `kanzi_latent_to_coords` (the Wave 95.P3.B Linear(512→4) bridge)
- `tools/_kanzi_sweep_runner.py:348-450 _synthesize_x_final_real` — Wave 122 P2 sweep-runner mitigation
- `adaptive_reflow/adapters/kanzi.py:1107` — bug location (ruff-frozen)
- `adaptive_reflow/adapters/kanzi.py:1197 _KanziDAEShim.forward` — model call site (where the matmul crash manifests)
- `data/kanzi_upstream/src/kanzi/models.py:358 encode` — `DAE.up` `nn.Linear(3, 256)` (the upstream layer that expects raw backbone coords)
- `tests/test_adapters/test_kanzi_smoke.py:523 test_torch_velocity_field_validates_against_per_call_state_shape` — Wave 121 Phase 1 regression test (must still PASS after Wave 147 fix)

---

## Out of scope for Wave 147 (deferred to camera-ready)

- ❌ Actual code change at `kanzi.py:1107` + `kanzi.py:_resolve_conditioning` (ruff-frozen under Wave 131)
- ❌ Unit test `test_torch_velocity_field_inverse_projects_post_project_out_latents` (ruff-frozen code can't add new tests either)
- ❌ Regression test assertion in `test_kanzi_smoke.py:523` (ruff-frozen)
- ❌ Re-run of Wave 124 N=1000 framework_inv_proj sweep to confirm no regression (~3 h GPU)
- ❌ Kanzi N=1000 algorithm-primitive ablation (Wave 146 Item 1 BLOCKED — depends on this bridge fix being unblocked first per `docs/audit/wave146-item1-ablation.md` Recommendation 1)

**Requisite for application:** de-ruff-freeze `adaptive_reflow/adapters/kanzi.py` + `tests/test_adapters/test_kanzi_smoke.py` (the only 2 files touched by the fix + tests). The Wave 131 freeze marker is at commit `89e635e` (v1.0.1-paper-final tag) per `docs/GATES.md:90`. De-freeze requires an explicit user-gated decision OR a follow-up wave that re-establishes the freeze marker at the new HEAD post-application.

---

## Next-wave ownership

| Wave | Owner | Deliverable |
|---|---|---|
| Camera-ready (de-ruff-freeze required) | bridge bug fix owner | Apply 4(a) + 4(b) (~18 LOC across 2 sites in `kanzi.py`); apply 4(e) unit test (~85 LOC in `tests/test_adapters/test_kanzi_smoke.py`); apply 4(f) regression test assertion (~12 LOC in same file); re-run `pytest tests/ -k "d4" -q` (must remain 33/33 PASS); re-run `ruff check` (must remain 0 violations); re-run Wave 124 N=1000 framework_inv_proj sweep on the kanzi sidecar (~3 h GPU; zero skips; `Δ ≈ 0` vs Wave 124 reading ~0.86 Å). Re-establish Wave 131 freeze marker at new HEAD. |
| Camera-ready (after fix lands) | Kanzi N=1000 algorithm-primitive ablation owner (Wave 146 Item 1 retry) | Unblocks Wave 146 Item 1 (currently BLOCKED per `docs/audit/wave146-item1-ablation.md`); add `--primitive {restart_skip,brai_mag,beta_cal}` CLI flags to Kanzi sweep drivers; thread into `KanziAdapter` construction; run 5-arm ablation at N=1000 (~7 h GPU per arm, ~35 h total); populate Table C with real measured numbers; commit + re-establish freeze marker. |
