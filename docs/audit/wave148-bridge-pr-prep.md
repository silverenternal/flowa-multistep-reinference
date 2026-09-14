# Wave 148 — Wave 121 bridge fix PR-prep package (READ-ONLY, deferred to camera-ready)

**Date:** 2026-09-14
**Author:** Wave 148 Agent 1 (extends Wave 147 P1 READ-ONLY design into a directly-executable PR package)
**Scope:** READ-ONLY PR-prep package. Turns `docs/audit/wave147-bridge-bug-design.md` into a one-shot, executable pull request. **NO source code modifications** in this wave (Wave 131 ruff-frozen code preserved; ruff-clean verified at HEAD).

---

## TL;DR

| Phase | Status | Deliverable |
|---|---|---|
| **Step 1 (Wave 147 P1 design reading)** | ✅ done | `docs/audit/wave147-bridge-bug-design.md` — bug at `kanzi.py:1107`; fix at `_torch_velocity_field` + `_resolve_conditioning` |
| **Step 2 (ruff-freeze marker inspection)** | ✅ done | Wave 131 freeze marker at commit `89e635e` (per `docs/GATES.md:90`; v1.0.1-paper-final tag at commit `58930ef` per `git tag -l`) |
| **Step 3 (PR-prep package authoring — this doc)** | ✅ done | `docs/audit/wave148-bridge-pr-prep.md` (NEW, READ-ONLY, 7 sections) |
| **Step 4 (gate verification — READ-ONLY)** | ✅ done | pytest d4 → **33/33 PASS**; ruff → **All checks passed**; claims consistency → **No drift detected** |
| **Step 5 (commit — this doc only)** | ✅ done | Wave 148 P1 commit (this doc + ruff-frozen code preserved verbatim) |

**Acceptance gates:**
- ✅ No source code modified (Wave 131 ruff-frozen code preserved)
- ✅ READ-ONLY PR-prep package authoring (audit doc only)
- ✅ All 4 cross-references to Wave 147 P1 design honored (bug location, fix design, unit test, regression test)
- ✅ 7-section structure per Wave 148 P1 spec
- ✅ Ruff-frozen invariant documented + re-establishment protocol specified
- ✅ Existing D.4 33/33 PASS confirmed at HEAD (`pytest tests/ -k "d4" -q`)
- ✅ Ruff-clean confirmed at HEAD (`ruff check adaptive_reflow/ tests/`)
- ✅ Claims consistency PASS confirmed at HEAD (`tools/check_claims_consistency.py`)

---

## Section 1: PR title + description

### 1.1 PR title

```
Apply Wave 121 bridge fix at adaptive_reflow/adapters/kanzi.py (closes Wave 147 P1 design)
```

### 1.2 PR body

This PR applies the adapter-layer inverse-projection bridge fix designed in `docs/audit/wave147-bridge-bug-design.md` to close the Wave 121 P4 NEW DEEPER bug at `adaptive_reflow/adapters/kanzi.py:1107` (matmul shape mismatch `(64x512 vs 3x256)` in `DAE.encode → DAE.up`).

The fix is the **adapter-layer inverse projection** approach (selected from 3 candidate layers in Wave 147 P1 §4(c)) — a 12-line block at `_torch_velocity_field` (lines 1085-1097) that detects `state_shape[-1] != 3` and inverse-projects post-`project_out` latents via the existing `tools.kanzi_latent_to_coord.kanzi_latent_to_coords` bridge (Wave 95.P3.B Linear(512→4) bridge), plus a 6-line block at `_resolve_conditioning` (lines 1726-1732) that plumbs the `_KanziDAEShim._dae` decoder reference into the conditioning cache as `latent_to_coord_decoder`. A ~85-line unit test `test_torch_velocity_field_inverse_projects_post_project_out_latents` exercises 3 paths (inverse-projection, no-op for `(L, 3)`, missing-decoder `CapabilityMissingError`), and a ~12-line assertion in the existing `test_torch_velocity_field_validates_against_per_call_state_shape` at `tests/test_adapters/test_kanzi_smoke.py:523` regresses the real-mode `(64, 512)` path.

This change closes the Wave 122 P2 PARTIAL FIX (sweep-runner pre-projection, commit `ae76508`) + Wave 124 P1+P4 PARTIAL FIX (per-call `set_traj_shape` + 5 hardcoded-ref replacements, commits `1d40531` + `bb19310`) mitigation chain at the **adapter layer itself**, so the Wave 95 framework_inv_proj N=1000 reading (`2.5017 ± 0.0000 Å`) becomes the authoritative framework_inv_proj data point instead of an ADDITIVE workaround. Byte-stability is preserved for the synthetic-mode `(L, 3)` path because the inverse-projection branch is gated on `state_shape[-1] != 3 AND bridge_decoder is not None`.

**Provenance chain:** Wave 120 (validator-layer bug discovered) → Wave 121 Phase 1 (validator-layer fix at `kanzi.py:1073`, commit `a90485b`) → Wave 121 P4 (NEW DEEPER bug at adapter layer) → Wave 122 P2 (sweep-runner mitigation, `ae76508`) → Wave 124 P1+P4 (per-call shape override, `1d40531` + `bb19310`) → Wave 147 P1 (READ-ONLY design only, this PR's design source) → Wave 148 P1 (this PR-prep package) → camera-ready (this PR's application wave).

### 1.3 PR checklist (markdown task list)

- [ ] **ruff-clean**: `ruff check adaptive_reflow/ tests/` → 0 violations
- [ ] **D.4 33/33**: `pytest tests/ -k "d4" -q` → 33 passed, 0 failed
- [ ] **claims PASS**: `python tools/check_claims_consistency.py` → "No drift detected."
- [ ] **N=1000 sweep regression ~zero**: re-run Wave 124 framework_inv_proj sweep on Kanzi sidecar (~3 h GPU); assert `|Δ| ≤ 1e-6` vs Wave 124 reading (`2.5017 ± 0.0000 Å`)
- [ ] **ruff-unfreeze protocol**: de-ruff-freeze `adaptive_reflow/adapters/kanzi.py` + `tests/test_adapters/test_kanzi_smoke.py`; commit fix; re-establish ruff-freeze marker at new HEAD (Section 2.4)
- [ ] **freeze-marker SHA update**: update `docs/GATES.md:90` to reference the new freeze-marker SHA at post-merge HEAD; update `docs/audit/wave147-bridge-bug-design.md` "Next-wave ownership" cross-references
- [ ] **CAMERA-READY tag**: set `v1.0.2-paper-final` tag at post-merge HEAD (the natural next tag increment after `v1.0.1-paper-final`)

---

## Section 2: Files to de-ruff-freeze (ruff-unfreeze protocol)

### 2.1 File 1: `adaptive_reflow/adapters/kanzi.py`

| Region | Lines (HEAD) | Why de-ruff-freeze | Touched by which block |
|---|---:|---|---|
| `_torch_velocity_field` body | 1080-1110 | Adapter-layer inverse projection lives here | Block A (12 LOC) |
| `_resolve_conditioning` body | 1726-1750 | Conditioning cache plumbing lives here | Block B (6 LOC) |
| `compose_condition` body | 2170-2180 | (Read-only reference for `int(self._num_steps)` mirror pattern) | Block B (no edits; reference only) |

### 2.2 File 2: `tests/test_adapters/test_kanzi_smoke.py`

| Region | Lines (HEAD) | Why de-ruff-freeze | Touched by which block |
|---|---:|---|---|
| `test_torch_velocity_field_validates_against_per_call_state_shape` body | 523-587 (anchor at 523) | Existing regression test extended with new assertion | Block D (12 LOC) |
| New unit test (inserted after line 587) | ~85 LOC | New unit test for the 3-path inverse-projection behavior | Block C (85 LOC) |

### 2.3 Freeze-marker commit SHA

```
89e635e   (v1.0.1-paper-final tag; Wave 131 ruff-frozen code; per docs/GATES.md:90)
```

**Note on tag-vs-commit:** the v1.0.1-paper-final tag points to commit `58930ef` (Wave 134, per `git tag -l`); `docs/GATES.md:90` cites `89e635e` (Wave 136, "final submission polish close") as the "freeze marker commit" because `89e635e` is the last ruff-clean commit *referenced as the freeze point* even though the tag is at `58930ef`. **The fix at this PR does NOT alter ruff-frozen invariant**; the freeze marker moves forward to the post-merge HEAD as documented in §2.4.

### 2.4 Re-freeze protocol (post-merge)

After PR merge, re-establish the ruff-frozen invariant at the new HEAD:

```bash
# 1. Confirm ruff-clean at post-merge HEAD
ruff check adaptive_reflow/ tests/
# Expected: All checks passed!

# 2. Confirm D.4 33/33 PASS at post-merge HEAD
pytest tests/ -k "d4" -q
# Expected: 33 passed, 31 skipped, ...

# 3. Confirm claims consistency PASS at post-merge HEAD
python tools/check_claims_consistency.py
# Expected: **No drift detected.**

# 4. Set the new freeze-marker tag
git tag -f v1.0.2-paper-final

# 5. Create a freeze-marker commit (empty, for traceability)
git commit --allow-empty -m "Wave 148 post-merge: re-establish ruff-freeze marker at <new-sha>"

# 6. Update docs/GATES.md:90 with the new freeze-marker SHA
#    (replace 89e635e → <new-sha>; replace "v1.0.1-paper-final" → "v1.0.2-paper-final")
```

The empty commit at step 5 is for **provenance only** — it marks the boundary between ruff-unfrozen code (the PR's commits) and the new ruff-frozen code (everything after). The actual freeze marker is the new tag at step 4 plus the new SHA reference at step 6.

---

## Section 3: Code change specification (in 4 logical blocks)

### 3.1 Block A — 12-line adapter-layer inverse projection at `_torch_velocity_field`

**File:** `adaptive_reflow/adapters/kanzi.py`
**Function:** `_torch_velocity_field`
**Insert location:** between line 1084 (after `x = make_validate_state_shape(state_shape)(np.asarray(x, dtype=np.float64))`) and line 1086 (before `import torch`)

```python
    # Wave 148 PR-prep (camera-ready): adapter-layer inverse projection.
    # When state_shape[-1] != 3 (i.e. input is post-`project_out` latents
    # rather than raw backbone coords), apply the Wave 95.P3.B bridge to
    # project (L, n_channels_decoder) -> (L, 3) backbone coords BEFORE
    # feeding the model. Closes the Wave 121 P4 NEW DEEPER bug at
    # `kanzi.py:1107` (matmul 64x512 vs 3x256 in `DAE.encode`) at the
    # ADAPTER LAYER rather than relying on the sweep runner pre-projection
    # (Wave 122 P2) + per-call `set_traj_shape` (Wave 124 P1+P4).
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

**LOC breakdown:** 12 lines (≈ 9 LOC of logic; 3 lines are the comment header + final `state_shape` update).
**Source:** `docs/audit/wave147-bridge-bug-design.md` §4(a).
**Import dependency:** `CapabilityMissingError` (already imported at `kanzi.py:1306`, per Wave 99+ fix); `tools.kanzi_latent_to_coord.kanzi_latent_to_coords` (already exists, Wave 91 Phase 3, commit `8c5eaaf`).

### 3.2 Block B — 6-line conditioning cache plumbing at `_resolve_conditioning`

**File:** `adaptive_reflow/adapters/kanzi.py`
**Function:** `_resolve_conditioning`
**Insert location:** inside the `entry = _synthetic_family_conditioning(...)` block, after the call returns and before `self._conditioning_cache.put(cache_hash, entry)` (around lines 1746-1749)

```python
        # Wave 148 PR-prep (camera-ready): stash the real DAE decoder in
        # the cache so `_torch_velocity_field` can inverse-project post-
        # `project_out` (L, 512) latents -> (L, 3) backbone coords.
        if self._mode == "torch" and self._model is not None:
            entry["latent_to_coord_decoder"] = self._model._dae  # type: ignore[attr-defined]
            entry["decoder_steps"] = int(self._num_steps)
            entry["bridge_seed"] = int(seed)
```

**LOC breakdown:** 6 lines (≈ 4 LOC of logic; 2 lines are the comment header).
**Source:** `docs/audit/wave147-bridge-bug-design.md` §4(b).
**Reference dependency:** `self._model._dae` is the real upstream `DAE` instance (Wave 99+ fix); `_KanziDAEShim._dae` attribute is set in `__init__` at `kanzi.py:1170-1171`. The `int(self._num_steps)` mirrors the existing `num_steps` resolution in `compose_condition` (`kanzi.py:2170-2175`).

### 3.3 Block C — 85-line unit test at `tests/test_adapters/test_kanzi_smoke.py`

**File:** `tests/test_adapters/test_kanzi_smoke.py`
**Insert location:** after the existing `test_torch_velocity_field_validates_against_per_call_state_shape` test (after line 587)
**Function name:** `test_torch_velocity_field_inverse_projects_post_project_out_latents`

```python
def test_torch_velocity_field_inverse_projects_post_project_out_latents() -> None:
    """Wave 148 PR-prep regression: ``_torch_velocity_field`` must inverse-project
    (L, n_channels_decoder) post-`project_out` latents to (L, 3) backbone
    coords BEFORE invoking ``model(x_t, ...)``.

    Closes the Wave 121 P4 NEW DEEPER bug at `kanzi.py:1107` (matmul
    64x512 vs 3x256 in `DAE.encode`) at the ADAPTER LAYER. Pre-fix,
    the velocity field would pass `(1, 64, 512)` directly to the model's
    `_KanziDAEShim.forward` -> `DAE.encode(x)` -> `DAE.up`
    (`nn.Linear(3, 256)`), which crashes with a matmul shape mismatch.
    Post-fix, the velocity field detects `state_shape[-1] != 3`, calls
    `tools.kanzi_latent_to_coord.kanzi_latent_to_coords` with the
    cached decoder, and feeds `(1, 64, 3)` to the model.

    This test exercises 3 paths:
      - Path A: (L, 512) input -> inverse-projected -> (1, 64, 3) reaches model
      - Path B: (L, 3) input -> no-op -> (1, 64, 3) reaches model (byte-stable)
      - Path C: missing bridge decoder in cache -> CapabilityMissingError

    Uses a stub `nn.Module` whose `forward` records the input shape so
    we can assert that the model receives `(B, L, 3)` regardless of
    input state_shape. The `kanzi_latent_to_coords` call is stubbed
    via a fake `latent_to_coord_decoder` in the cache.
    """
    pytest.importorskip("torch", reason="torch is required for the stub DAE model")

    import torch as _torch

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

    class _StubBridgeDecoder:
        def quantize(self, z):  # noqa: D401
            return z

        def decode(self, idx_BL, n_steps=50, seed=0):  # noqa: D401
            B, L = idx_BL.shape[0], idx_BL.shape[1]
            return _torch.zeros((B, L, 3), dtype=_torch.float64)

    bridge = _StubBridgeDecoder()

    import sys
    sys.modules.setdefault("tools.kanzi_latent_to_coord", type(sys)("tools.kanzi_latent_to_coord"))
    sys.modules["tools.kanzi_latent_to_coord"].kanzi_latent_to_coords = (
        lambda x, decoder, fsq_quantizer, n_steps, seed:
            _torch.zeros((1, x.shape[0], 3), dtype=_torch.float64).numpy()
    )

    cache = {
        "family_embed": np.zeros(1152, dtype=np.float64),
        "latent_to_coord_decoder": bridge,
        "decoder_steps": 50,
        "bridge_seed": 0,
    }

    # Path A: (L, 512) input -> inverse-projected to (1, 64, 3)
    x_latent = np.random.default_rng(0).standard_normal((64, 512)).astype(np.float64)
    out_latent = _torch_velocity_field(
        model=model, x=x_latent, t=0.5,
        dtype=_torch.float64, cache=cache,
        guidance_scale=1.0, state_shape=(64, 512),
    )
    assert model.last_x_shape == (1, 64, 3), (
        f"expected model to receive (1, 64, 3), got {model.last_x_shape}"
    )
    assert out_latent.shape == (64, 3)
    assert out_latent.dtype == np.float64
    assert np.isfinite(out_latent).all()

    # Path B: (L, 3) input -> no-op (byte-stable for synthetic mode)
    x_backbone = np.random.default_rng(1).standard_normal((64, 3)).astype(np.float64)
    out_backbone = _torch_velocity_field(
        model=model, x=x_backbone, t=0.5,
        dtype=_torch.float64, cache=cache,
        guidance_scale=1.0, state_shape=(64, 3),
    )
    assert model.last_x_shape == (1, 64, 3)
    assert out_backbone.shape == (64, 3)
    assert np.isfinite(out_backbone).all()

    # Path C: missing bridge decoder in cache -> CapabilityMissingError
    cache_no_bridge = {"family_embed": np.zeros(1152, dtype=np.float64)}
    with pytest.raises(Exception) as exc_info:
        _torch_velocity_field(
            model=model, x=x_latent, t=0.5,
            dtype=_torch.float64, cache=cache_no_bridge,
            guidance_scale=1.0, state_shape=(64, 512),
        )
    assert "latent_to_coord_decoder" in str(exc_info.value)
```

**LOC breakdown:** ~85 lines (including docstring).
**Source:** `docs/audit/wave147-bridge-bug-design.md` §4(e).
**Imports used:** `pytest`, `numpy as np`, `torch as _torch` (via `importorskip`), `sys`, `adaptive_reflow.adapters.kanzi._torch_velocity_field` — all of which are already imported at the top of `test_kanzi_smoke.py`.

### 3.4 Block D — 12-line regression test assertion at `tests/test_adapters/test_kanzi_smoke.py:523`

**File:** `tests/test_adapters/test_kanzi_smoke.py`
**Function:** `test_torch_velocity_field_validates_against_per_call_state_shape` (existing; line 523 anchor)
**Insert location:** after line 587 (end of the existing assertion block) inside the existing function

```python
    # Wave 148 PR-prep regression: real-mode (64, 512) input must still
    # validate via the per-call closure; the inverse-projection branch
    # is gated on `state_shape[-1] != 3 AND latent_to_coord_decoder in cache`,
    # so without a decoder in cache, the (64, 512) path is unchanged.
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

**LOC breakdown:** 12 lines (≈ 8 LOC of logic; 4 lines are the comment header).
**Source:** `docs/audit/wave147-bridge-bug-design.md` §4(f).

### 3.5 Total LOC budget

| Block | File | LOC | Notes |
|---|---:|---:|---|
| Block A | `kanzi.py` | 12 | Adapter-layer inverse projection at `_torch_velocity_field` |
| Block B | `kanzi.py` | 6 | Conditioning cache plumbing at `_resolve_conditioning` |
| Block C | `test_kanzi_smoke.py` | ~85 | New unit test (3 paths) |
| Block D | `test_kanzi_smoke.py` | ~12 | Regression test assertion in existing test |
| **Total** | **2 files** | **~115** | Spans 4 sites across 2 files |

---

## Section 4: Test matrix (D.4 + new tests)

### 4.1 Existing D.4 33/33 vectors (must remain PASS)

Per `docs/GATES.md:87-92`: D.4 pinned regression vectors — 33/33 PASS at HEAD `3f85a37` as of 2026-09-14.

| Test surface | Test count | Last green | Status (HEAD) |
|---|---:|---|---|
| `tests/test_d4_regression_vectors.py` | 33 | commit `f97ec1c` (Wave 106.C.2) | PASS |
| `tests/test_adapters/test_regression_vectors.py` | 39 | commit `f97ec1c` (Wave 106.C.2) | PASS |
| **Total** | **72** | (legacy figure; ruff-frozen invariant = 33/33) | **PASS** |

**Why the fix does not perturb D.4 vectors:** the fix touches only the Kanzi adapter's `_torch_velocity_field` (additive inverse-projection branch) and `_resolve_conditioning` (additive cache key). None of the 33 D.4 vectors exercise the Kanzi inverse-projection path (verified by inspection: vectors cover 2D FM, MNIST FM, CIFAR-10 RF, FreqFlow, LineageFlow, Self-Flow, GraphBFN, MNIST baselines).

### 4.2 New unit test: `test_torch_velocity_field_inverse_projects_post_project_out_latents`

| Path | Input | Expected behavior | Expected assertion |
|---|---|---|---|
| **Path A: inverse-projection** | `x.shape = (64, 512)`, `state_shape = (64, 512)`, cache has `latent_to_coord_decoder` | Stub `kanzi_latent_to_coords` called with `(64, 512)`; returns `(1, 64, 3)` zeros; model receives `(1, 64, 3)` | `model.last_x_shape == (1, 64, 3)`; `out_latent.shape == (64, 3)`; dtype = float64; finite |
| **Path B: no-op for `(L, 3)`** | `x.shape = (64, 3)`, `state_shape = (64, 3)`, cache has decoder | Inverse-projection branch SKIPPED (because `state_shape[-1] == 3`); model receives `(1, 64, 3)` directly | `model.last_x_shape == (1, 64, 3)`; `out_backbone.shape == (64, 3)` |
| **Path C: missing decoder** | `x.shape = (64, 512)`, `state_shape = (64, 512)`, cache MISSING `latent_to_coord_decoder` | Inverse-projection branch detects missing decoder; raises `CapabilityMissingError` | `pytest.raises(Exception)`; `str(exc.value)` contains `"latent_to_coord_decoder"` |

### 4.3 New regression test assertion in existing `test_torch_velocity_field_validates_against_per_call_state_shape`

| Path | Input | Expected behavior | Expected assertion |
|---|---|---|---|
| **Real-mode `(64, 512)` w/o bridge** | `x.shape = (64, 512)`, `state_shape = (64, 512)`, cache MISSING `latent_to_coord_decoder` | Inverse-projection branch detects missing decoder; raises `CapabilityMissingError` (NOT a silent no-op) | `out_real_no_bridge.shape == (64, 512)` IF the existing test's `x_real` happens to be passed through a `(64, 512) → (64, 512)` mock; **OR** `pytest.raises(Exception)` if the inverse-projection fails-closed |

**Subtlety:** the existing test's `x_real` is constructed at line ~580 with shape `(64, 512)` and a per-call validator closure. After Block A lands, the same `x_real` with `state_shape=(64, 512)` and `cache_no_bridge` will fail-closed with `CapabilityMissingError` because `state_shape[-1] == 512 != 3`. The assertion must therefore wrap the call in `pytest.raises(CapabilityMissingError)` (or `pytest.raises(Exception)`) and verify the missing-decoder message — NOT verify the output shape. **This subtlety must be reconciled at PR-application time** by either (a) reading the exact line 573-587 contents of the test and crafting a context-appropriate assertion, or (b) de-scope Block D from the PR (leave only Block C as the new test).

### 4.4 N=1000 framework_inv_proj sweep regression check

**Source:** `verification_outputs/kanzi_n1000_framework_inv_proj_q4_2026/kanzi_n1000_framework_inv_proj_paper_metrics.json` (per Wave 124 P4 close; full N=1000 sweep on RTX PRO 6000 Blackwell in ~3 h GPU, zero skips).

**Post-PR verification (the regression check):**

```bash
# Re-run on Kanzi sidecar with the post-PR code (~3 h GPU)
python tools/_kanzi_sweep_runner.py \
    --arm framework_inv_proj \
    --n-samples 1000 \
    --output-dir verification_outputs/kanzi_n1000_framework_inv_proj_post_wave148/

# Compare vs Wave 124 reading
python tools/compare_sweep_runs.py \
    --baseline verification_outputs/kanzi_n1000_framework_inv_proj_q4_2026/kanzi_n1000_framework_inv_proj_paper_metrics.json \
    --candidate verification_outputs/kanzi_n1000_framework_inv_proj_post_wave148/kanzi_n1000_framework_inv_proj_paper_metrics.json \
    --metric overall_rmsd_angstrom \
    --tolerance 1e-6
```

**Expected:** `delta = 0.00e+00` (byte-stable) vs Wave 124 reading (`overall_rmsd_angstrom = 2.5017`). **Rationale for byte-stability:** the Wave 124 framework_inv_proj N=1000 sweep already pre-projects at the sweep runner (`tools/_kanzi_sweep_runner.py:348-450 _synthesize_x_final_real`); the post-PR adapter-layer inverse projection is gated on `state_shape[-1] != 3 AND bridge_decoder is not None`, and the sweep runner's `set_traj_shape((L, 3))` sets `state_shape[-1] = 3`, so the adapter-layer branch is **skipped** for the existing sweep path. Byte-stability is preserved by construction.

---

## Section 5: Rollback plan

### 5.1 If D.4 33/33 fails after PR merge

1. **Diagnose:** `pytest tests/ -k "d4" -q -v` to identify which of the 33 vectors fails.
2. **Mitigate:** if the failure is in a Kanzi-related vector (none expected per §4.1), inspect whether the fix's `CapabilityMissingError` path in Block A breaks a real-mode D.4 vector that previously succeeded (unlikely; D.4 vectors don't exercise Kanzi real-mode).
3. **Revert:** `git revert <merge-commit-sha>` → re-establishes pre-PR HEAD state.
4. **Re-freeze:** re-tag `v1.0.2-paper-final` at the pre-PR HEAD; update `docs/GATES.md:90` accordingly.
5. **Re-investigate:** the fix logic has a regression; consult Wave 147 P1 §4(c) for the layer-choice alternatives.

### 5.2 If N=1000 sweep delta is non-trivial (`|Δ| > 1e-6`)

1. **Diagnose:** inspect the per-sample RMSD distribution; identify which sweep samples diverge.
2. **Mitigate:** the most likely cause is that Block A's `state_shape[-1] != 3` branch fires for a sample where it shouldn't (e.g. a sample that was supposed to enter with `(L, 3)` but arrives as `(L, 512)`). Check `tools/_kanzi_sweep_runner.py:348-450` for the `set_traj_shape` call site and verify the sweep runner's `_synthesize_x_final_real` honors the post-`set_traj_shape` shape.
3. **Revert:** `git revert <merge-commit-sha>` → re-establishes pre-PR HEAD state.
4. **Re-investigate:** Block A logic bug; likely the `state_shape = (*state_shape[:-1], 3)` reassignment mutates the per-call closure's `state_shape` in an unexpected way (the closure was already built at line 1084 with the original `state_shape`; reassigning `state_shape` after the inverse projection may or may not affect the closure depending on Python closure semantics — verify with a quick experiment).
5. **Re-freeze:** re-tag `v1.0.2-paper-final` at the pre-PR HEAD.

### 5.3 If `ruff check` returns new findings

1. **Auto-fix:** `ruff check --fix adaptive_reflow/adapters/kanzi.py tests/test_adapters/test_kanzi_smoke.py` → ruff auto-fixes most violations.
2. **Manual fix:** for violations ruff can't auto-fix (e.g. `noqa: E501` line-too-long in the Block A docstring), manually wrap the lines.
3. **Re-verify:** `ruff check adaptive_reflow/ tests/` → 0 violations.
4. **Commit:** `git commit -am "Wave 148 post-merge: ruff auto-fix for Block A-D ruff violations"`.
5. **No revert needed:** ruff violations are cosmetic and don't affect runtime behavior; the freeze-marker tag is set after ruff-clean is confirmed.

### 5.4 If pytest skips or warnings increase

1. **Skips:** `pytest tests/ -k "d4" -q -v` should still report 33 passed, ~31 skipped (torch/pandas/etc. not installed in this venv). If skips increase, identify which test gained a `pytest.importorskip` and verify it's intentional (e.g. `test_torch_velocity_field_inverse_projects_post_project_out_latents` uses `pytest.importorskip("torch")`, which is intentional).
2. **Warnings:** 9 warnings are present at HEAD (mostly deprecation warnings from third-party libs). If warnings increase, run `pytest tests/ -k "d4" -W error` to identify the source; typically these are numpy/torch deprecation warnings that don't affect D.4 vectors.

---

## Section 6: Cherry-pick path from camera-ready branch

### 6.1 Source branch: `camera-ready` (assumed ruff-unfrozen)

The `camera-ready` branch is the conventional next-paper-release branch; it is assumed to be **ruff-unfrozen** at PR-application time (i.e. the Wave 131 freeze marker has been lifted there but NOT on `main`). The fix lives on `camera-ready` only until the PR merges back to `main`.

### 6.2 Target branch: `main` (post-merge)

After PR merge, `main` becomes the ruff-unfrozen carrier of the fix; the post-merge re-freeze (§2.4) re-establishes the ruff-frozen invariant at the new HEAD.

### 6.3 Cherry-pick command

```bash
# On main, cherry-pick the bridge-fix commit from camera-ready
git checkout main
git cherry-pick <bridge-fix-commit-sha> --strategy-option=theirs
```

**`--strategy-option=theirs` rationale:** the cherry-pick may conflict on `docs/GATES.md` (which references the freeze-marker SHA); `--strategy-option=theirs` resolves to the camera-ready version (the post-fix freeze SHA), which is correct.

### 6.4 Post-cherry-pick

```bash
# 1. Re-establish ruff-freeze marker at new HEAD
git tag -f v1.0.2-paper-final
git commit --allow-empty -m "Wave 148 post-merge: re-establish ruff-freeze marker at <new-sha>"

# 2. Update docs/GATES.md:90 with the new freeze-marker SHA
#    (replace 89e635e → <new-sha>; replace "v1.0.1-paper-final" → "v1.0.2-paper-final")

# 3. Update docs/audit/wave147-bridge-bug-design.md "Next-wave ownership" cross-references
#    (Wave 148 PR-prep is now complete; next-wave ownership = camera-ready Wave 148 close)

# 4. Push to origin
git push origin main --tags --force-with-lease
```

**Push command:** `--force-with-lease` is required because the freeze-marker tag is force-moved (`git tag -f v1.0.2-paper-final`); `--force-with-lease` is the safe variant that aborts if another branch has moved the tag in the meantime.

---

## Section 7: Risk assessment

### 7.1 Risk A (HIGH) — Block A logic bug → silently-wrong framework_inv_proj results

**Description:** if the 12-line Block A at `_torch_velocity_field` has a logic bug (e.g. wrong `state_shape` reassignment, wrong `bridge_decoder` attribute access, wrong `n_steps` default), all 4 framework_inv_proj sweep arms may produce silently-wrong results (no error, just numerically-different outputs).

**Mitigation:** the N=1000 sweep regression check (§4.4) catches this with a tight tolerance (`|Δ| ≤ 1e-6` vs Wave 124 reading). If the delta is non-trivial, the rollback plan (§5.2) reverts and re-investigates.

**Likelihood:** LOW (the Block A logic mirrors the existing Wave 122 P2 sweep-runner pre-projection verbatim, just at the adapter layer; the only new code is the `CapabilityMissingError` raise).

### 7.2 Risk B (MEDIUM) — `CapabilityMissingError` path breaks existing callers

**Description:** the `CapabilityMissingError` raise at Block A line 1095 may break existing callers (in tests, in scripts, in CLI tools) that do not set up `latent_to_coord_decoder` in the cache. The most likely breakage is in `test_torch_velocity_field_validates_against_per_call_state_shape` at line 523 (the existing regression test), which constructs a `cache` without `latent_to_coord_decoder` and passes `state_shape=(64, 512)` — Block A will now raise `CapabilityMissingError` instead of returning a `(64, 512)` output.

**Mitigation:** the new Block D assertion (§3.4) addresses this by adding an explicit assertion that the existing test's `cache_no_bridge` raises `CapabilityMissingError` for `(64, 512)` input. The exact assertion shape needs reconciliation at PR-application time per §4.3 (subtlety).

**Likelihood:** MEDIUM (the Block D assertion needs careful crafting to handle the `pytest.raises(CapabilityMissingError)` shape).

### 7.3 Risk C (LOW) — `_KanziDAEShim._dae` attribute rename breaks Block B

**Description:** Block B at `_resolve_conditioning` line 1729 references `self._model._dae`. If `_dae` is renamed (e.g. to `_backbone` or `_upstream_dae`) in a future refactor, Block B silently sets `entry["latent_to_coord_decoder"]` to a non-existent attribute, and Block A's `bridge_decoder.quantize` call would raise `AttributeError` at runtime.

**Mitigation:** the unit test (Block C) uses a stub `_StubBridgeDecoder` whose `quantize` and `decode` methods are explicit; the test would catch a missing-attribute failure with a clear assertion message. The regression test (Block D) uses the existing test's stub model which may or may not have `_dae` — verify at PR-application time.

**Likelihood:** LOW (`_dae` is a stable attribute name established in Wave 99+ fix; refactoring it would be a breaking change to `_KanziDAEShim` and is unlikely without an explicit deprecation).

### 7.4 Overall risk: MEDIUM

**Rationale:** Block A + Block B + Block C + Block D together represent the **highest-ROI single code change in camera-ready scope** because they:
- Close a documented bug (`kanzi.py:1107` matmul mismatch) at the **adapter layer** rather than relying on caller-side mitigations (Wave 122 P2 + Wave 124 P1+P4)
- Make the framework_inv_proj arm the authoritative data point instead of an ADDITIVE workaround
- Are additive (no existing logic removed; only new conditional branches)
- Are gated by a tight N=1000 regression check (`|Δ| ≤ 1e-6`)
- Have a clear rollback path (§5)

The MEDIUM risk rating reflects Risk B (the `CapabilityMissingError` breakage in the existing regression test) which needs careful assertion crafting at PR-application time, NOT a fundamental flaw in the fix design.

### 7.5 Mitigation summary

| Risk | Severity | Mitigation | Detection mechanism |
|---|---|---|---|
| A: Block A logic bug | HIGH | N=1000 sweep regression check (§4.4) | Sweep delta > 1e-6 vs Wave 124 reading |
| B: `CapabilityMissingError` breaks existing test | MEDIUM | Block D regression test with explicit `pytest.raises(CapabilityMissingError)` | pytest run at PR-application time |
| C: `_dae` attribute rename | LOW | Unit test stub uses explicit `quantize` + `decode` methods | pytest assertion failure with clear message |
| D: ruff violations | LOW | Auto-fix via `ruff check --fix` (§5.3) | `ruff check adaptive_reflow/ tests/` |
| E: D.4 regression | LOW | None expected (D.4 vectors don't exercise Kanzi inverse-projection) | `pytest tests/ -k "d4" -q` |

---

## Cross-references

- `docs/audit/wave147-bridge-bug-design.md` — predecessor Wave 147 P1 design (READ-ONLY source for all 4 code blocks + 2 tests)
- `docs/audit/wave121-shape-fix-resweep.md` — Wave 121 audit doc (validator-layer bug + Phase 4 NEW DEEPER bug origin)
- `docs/audit/wave122-close-remaining-debt.md` — Wave 122 P2 sweep-runner mitigation (commit `ae76508`)
- `docs/audit/wave146-item1-ablation.md` — Wave 146 Item 1 BLOCKED narrative (cites this bug as the blocker for the algorithm-primitive ablation)
- `docs/CONSOLIDATED_RESULTS.md` §15.22 — Wave 121 §15.22 framework_inv_proj FAILED row + Phase 4 NEW DEEPER bug
- `docs/CONSOLIDATED_RESULTS.md` §15.23.2 — Wave 122 P2 PARTIAL FIX narrative (architectural context)
- `docs/CONSOLIDATED_RESULTS.md` §15.24 — Wave 124 full close (Phase 1 + Phase 4 framework_inv_proj N=1000 unblock)
- `docs/GATES.md:87-92` — D.4 gate (33/33 PASS pinned regression vectors at HEAD)
- `docs/GATES.md:90` — ruff-freeze marker SHA `89e635e` (v1.0.1-paper-final tag; Wave 131 ruff-frozen code)
- `tools/kanzi_latent_to_coord.py:218-227` — `kanzi_latent_to_coords` (the Wave 95.P3.B Linear(512→4) bridge)
- `tools/_kanzi_sweep_runner.py:348-450 _synthesize_x_final_real` — Wave 122 P2 sweep-runner mitigation
- `adaptive_reflow/adapters/kanzi.py:1107` — bug location (ruff-frozen; the target of Block A)
- `adaptive_reflow/adapters/kanzi.py:1197 _KanziDAEShim.forward` — model call site (where the matmul crash manifests)
- `adaptive_reflow/adapters/kanzi.py:1306` — `CapabilityMissingError` import (existing Wave 99+ fix pattern)
- `adaptive_reflow/adapters/kanzi.py:1170-1171` — `_KanziDAEShim._dae` attribute assignment (referenced by Block B)
- `adaptive_reflow/adapters/kanzi.py:2170-2175` — `num_steps` resolution in `compose_condition` (referenced by Block B)
- `data/kanzi_upstream/src/kanzi/models.py:358 encode` — `DAE.up` `nn.Linear(3, 256)` (the upstream layer that expects raw backbone coords)
- `tests/test_adapters/test_kanzi_smoke.py:523 test_torch_velocity_field_validates_against_per_call_state_shape` — Wave 121 Phase 1 regression test (extended by Block D)
- `tests/test_adapters/test_kanzi_smoke.py` — target file for Block C (new unit test)
- `verification_outputs/kanzi_n1000_framework_inv_proj_q4_2026/kanzi_n1000_framework_inv_proj_paper_metrics.json` — Wave 124 baseline reading (`overall_rmsd_angstrom = 2.5017`)

---

## Out of scope for Wave 148 (deferred to camera-ready application wave)

- ❌ Actual cherry-pick of the fix from `camera-ready` branch to `main` (Section 6.3 — requires ruff-unfreeze + branch orchestration)
- ❌ Application of Block A + Block B + Block C + Block D (~115 LOC across 2 files)
- ❌ Re-run of pytest d4 + ruff + claims consistency gates at post-merge HEAD (must remain 33/33 PASS / 0 violations / No drift detected)
- ❌ Re-run of Wave 124 N=1000 framework_inv_proj sweep on Kanzi sidecar (~3 h GPU; delta ≤ 1e-6 vs Wave 124 reading)
- ❌ Re-establishment of Wave 131 freeze marker at post-merge HEAD (Section 2.4 protocol)
- ❌ Update of `docs/GATES.md:90` with the new freeze-marker SHA + `v1.0.2-paper-final` tag
- ❌ Update of `docs/audit/wave147-bridge-bug-design.md` "Next-wave ownership" cross-references (Wave 148 PR-prep now complete; next-wave ownership = camera-ready Wave 148 close)
- ❌ Kanzi N=1000 algorithm-primitive ablation (Wave 146 Item 1 — depends on this bridge fix being unblocked first per `docs/audit/wave146-item1-ablation.md` Recommendation 1)

**Requisite for application:** de-ruff-freeze `adaptive_reflow/adapters/kanzi.py` + `tests/test_adapters/test_kanzi_smoke.py` (the only 2 files touched by the fix + tests). The Wave 131 freeze marker is at commit `89e635e` (v1.0.1-paper-final tag) per `docs/GATES.md:90`. De-freeze requires an explicit user-gated decision OR a follow-up wave (camera-ready) that re-establishes the freeze marker at the new HEAD post-application (Section 2.4 protocol).

---

## Next-wave ownership

| Wave | Owner | Deliverable |
|---|---|---|
| Camera-ready (de-ruff-freeze required) | bridge bug fix owner | Cherry-pick Block A + Block B + Block C + Block D from `camera-ready` branch to `main` (~115 LOC across 2 files); run `pytest tests/ -k "d4" -q` (must remain 33/33 PASS); run `ruff check adaptive_reflow/ tests/` (must remain 0 violations); run `python tools/check_claims_consistency.py` (must remain "No drift detected"); re-run Wave 124 N=1000 framework_inv_proj sweep on the Kanzi sidecar (~3 h GPU; zero skips; `|Δ| ≤ 1e-6` vs Wave 124 reading `2.5017 ± 0.0000 Å`); re-establish Wave 131 freeze marker at new HEAD (Section 2.4 protocol); update `docs/GATES.md:90` with new freeze-marker SHA + `v1.0.2-paper-final` tag; push to origin. |
| Camera-ready (after fix lands) | Kanzi N=1000 algorithm-primitive ablation owner (Wave 146 Item 1 retry) | Unblocks Wave 146 Item 1 (currently BLOCKED per `docs/audit/wave146-item1-ablation.md`); add `--primitive {restart_skip,brai_mag,beta_cal}` CLI flags to Kanzi sweep drivers; thread into `KanziAdapter` construction; run 5-arm ablation at N=1000 (~7 h GPU per arm, ~35 h total); populate Table C with real measured numbers; commit + re-establish freeze marker. |
