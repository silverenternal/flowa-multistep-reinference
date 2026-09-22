# Wave 178 P4 — `_torch_velocity_field` bridge + zero-pad code paths now no-ops for real mode (source unchanged)

**Date:** 2026-09-17
**Branch:** main (HEAD `de2d4bd`, post-Wave 178 P3)
**Scope:** P4 follow-up to Wave 178 P2 + P3. After `_real_state_shape`
returns `(L_abstract, 3)` in real mode (P2) and `build_initial_state`
initializes `x0` as `(L, 3)` (P3), the Wave 121 P4 bridge
(`kanzi_latent_to_coords` called inside `_torch_velocity_field`) and
the Wave 177 P1 zero-padding workaround (`v_padded[..., :3] = v_3d[..., :3]`)
are now dead code on the real-mode hot path. This audit **verifies**
they are no-ops and leaves the code in place as documentation /
fallback for synthetic mode and edge cases (e.g. `set_traj_shape`
overrides or non-3 `state_shape` from external callers).

---

## 1. What P2 + P3 changed

| Wave | File:line | Change | Real-mode effect |
|------|-----------|--------|------------------|
| 178 P2 | `adaptive_reflow/adapters/kanzi.py:1680-1695` | `_real_state_shape` returns `(L_abstract, 3)` instead of `(L_abstract, _real_latent_dim=512)` | `_effective_traj_shape()` returns `(64, 3)` |
| 178 P3 | `adaptive_reflow/adapters/kanzi.py:1835-1956` | `build_initial_state` samples `x0` with shape `(64, 3)` in real mode | `prior_entry["x0"]` is `(64, 3)` |

End-to-end consequence: the integrator operates on `(L, 3)`
trajectories throughout; the velocity field call receives `(L, 3)`
input and is expected to emit `(L, 3)` output. Both are now true
post-P2+P3 with **no source changes to `_torch_velocity_field`**.

---

## 2. Verification of the bridge path (Wave 121 P4)

**Code:** `adaptive_reflow/adapters/kanzi.py:1102-1115`

```python
original_state_shape = state_shape  # line 1109
if state_shape[-1] != 3:            # line 1110
    bridge_decoder = cache.get("latent_to_coord_decoder")
    if bridge_decoder is None:
        from adaptive_reflow.universal.adapter import CapabilityMissingError
        raise CapabilityMissingError("latent_to_coord_decoder")
    from tools.kanzi_latent_to_coord import kanzi_latent_to_coords
    _bridge_out = kanzi_latent_to_coords(...)
    x = _bridge_out[0] if _bridge_out.ndim == 3 and _bridge_out.shape[0] == 1 else _bridge_out
    state_shape = (*state_shape[:-1], 3)  # line 1124
```

### 2.1 Real-mode trace (post-P2)

1. `KanziAdapter._velocity_field` (kanzi.py:2301-2334) calls
   `_torch_velocity_field(..., state_shape=self._effective_traj_shape())`.
2. In real mode (no `set_traj_shape` override), `_effective_traj_shape()`
   returns `self._real_state_shape` → `(L_abstract, 3) = (64, 3)` (post-P2).
3. `_torch_velocity_field` receives `state_shape = (64, 3)`.
4. Line 1109: `original_state_shape = (64, 3)`.
5. Line 1110: `if state_shape[-1] != 3:` → `(64, 3)[-1] = 3 != 3` → **`False`**.
6. The bridge block (lines 1111-1124) is **bypassed**.
7. `state_shape` remains `(64, 3)`.

### 2.2 Synthetic-mode trace (post-P2)

1. `KanziAdapter._velocity_field` for synthetic mode
   (`self._mode == "synthetic"`) returns
   `_synthetic_velocity_field(x, t, weights=self._synthetic_weights)`
   (line 2336). `_torch_velocity_field` is **never called** in
   synthetic mode — the bridge code is irrelevant on this path.

### 2.3 Override path (`set_traj_shape((L, 3))`)

The framework_inv_proj arm in `tools/_kanzi_sweep_runner.py:449`
calls `adapter.set_traj_shape((64, 3))` to honor the post-bridge
trajectory shape. With this override:
1. `_effective_traj_shape()` returns the override `(64, 3)`.
2. Same trace as §2.1 — bridge is bypassed.

The bridge code is therefore **inactive on every real-mode path** in
the post-P2+P3 codebase. We retain it as dead code for:

- **Synthetic mode with non-default state_shape:** the bridge code
  path was originally written for real mode but is shape-agnostic —
  it could be reached if `_effective_traj_shape()` returned a
  non-`(L, 3)` shape via some hypothetical `set_traj_shape((L, N))`
  override.
- **External test seams:** the function is module-level (not a
  class method), so direct callers in tests or sweep runners might
  pass arbitrary `state_shape`. The bridge block acts as a defensive
  fallback for non-3 `state_shape[-1]` inputs.

---

## 3. Verification of the zero-pad path (Wave 177 P1)

**Code:** `adaptive_reflow/adapters/kanzi.py:1176-1181`

```python
if state_shape != original_state_shape and original_state_shape[-1] > 3:
    v_3d = out.reshape(state_shape)
    v_padded = np.zeros(original_state_shape, dtype=np.float64)
    v_padded[..., :3] = v_3d[..., :3]
    return v_padded
return out.reshape(state_shape)
```

### 3.1 Real-mode trace (post-P2+P3)

1. Bridge was bypassed (per §2.1), so `state_shape == original_state_shape == (64, 3)`.
2. Line 1176: `if state_shape != original_state_shape and original_state_shape[-1] > 3:`
   → `state_shape != original_state_shape` is `False` → short-circuit
   → condition is **`False`**.
3. Padding block is **bypassed**.
4. Falls through to `return out.reshape(state_shape)` → returns
   `out` reshaped to `(64, 3)` (the velocity field's native output shape).

### 3.2 What the zero-pad was compensating for (Wave 177 P1 context)

The Wave 177 P1 zero-pad existed because:

- Pre-P2: `_real_state_shape = (64, 512)`.
- `_torch_velocity_field` received `state_shape = (64, 512)`.
- Bridge collapsed `(64, 512)` → `(64, 3)`.
- Model forward emitted `(64, 3)` velocity.
- Without the zero-pad, `out.reshape((64, 512))` would crash
  (`reshape from (64, 3) to (64, 512): 192 elements ≠ 32768`).
- With the zero-pad: `v_padded[..., :3] = v_3d[..., :3]` and
  channels `3:N` were held at zero velocity → mathematically lossy
  (N-3 latent channels frozen at initialization).

Post-P2+P3, the entire bridge+pad choreography is unnecessary
because:

1. `_real_state_shape` is already `(64, 3)`.
2. `build_initial_state` produces `(64, 3)` x0.
3. The bridge never runs, so `state_shape == original_state_shape`.
4. The pad never runs, so the model forward emits `(64, 3)` velocity
   that can be reshaped directly to `state_shape = (64, 3)`.

The `out.reshape(state_shape)` on line 1181 is now the active
return path for real mode.

---

## 4. Synthetic-mode preservation

The D.4 byte-stable regression vectors at
`regression-vectors/kanzi.json` are exercised through the
`force_mode="synthetic"` path (`tools/run_regression_vector_audit.py:537-539`).
In synthetic mode:

1. `_velocity_field` returns `_synthetic_velocity_field(...)` —
   `_torch_velocity_field` is never invoked.
2. `_real_state_shape` returns `KANZI_ABSTRACT_STATE_SHAPE = (64, 64)`
   (the `if self._abstract_mode` branch at kanzi.py:1689-1690).
3. `build_initial_state` samples `(64, 64)` x0 (P3 synthetic-mode
   branch).

The bridge + zero-pad code in `_torch_velocity_field` is never
reached on the synthetic-mode path. D.4 72/72 PASS verified (see §5).

---

## 5. Verification commands + results

### 5.1 D.4 byte-stable regression vectors

```bash
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q
```

**Result:** 72 passed, 3 warnings in 45.39s. No regressions.

The "33/33 PASS" historical figure (Wave 113.D-113) covered the
first-batch subset in `tests/test_d4_regression_vectors.py` only;
current authoritative count is 72/72 per `docs/GATES.md` §D.4 +
Wave 149 Agent 6 drift fix. The `kanzi` subset is 6 tests (5 from
the first-batch subset parameterized over `kanzi` + 1 in the adapter
regression vectors), all passing.

### 5.2 Ruff lint

```bash
ruff check adaptive_reflow/
```

**Result:** All checks passed! 0 errors.

### 5.3 Claims consistency

```bash
PYTHONPATH=. python tools/check_claims_consistency.py
```

**Result:** **No drift detected.** 39 active claims, 0 provisional,
2 deprecated (CLM-040 forced to PROVISIONAL by `Disputed by`
citation — pre-existing, unrelated to Wave 178).

---

## 6. Decision: source unchanged

**No source changes to `adaptive_reflow/adapters/kanzi.py` for
Wave 178 P4.** The bridge + zero-pad code blocks remain in place
as documented dead code (kanzi.py:1102-1124 bridge, 1176-1180
zero-pad) for:

1. **Synthetic mode** (irrelevant — `_torch_velocity_field` not called).
2. **Edge-case `set_traj_shape` overrides** that might specify a
   non-`(L, 3)` shape (defensive fallback).
3. **External test seams** that invoke `_torch_velocity_field` with
   a custom `state_shape` argument.

The dead-code presence has **zero functional cost**:

- Bridge block: only runs if `state_shape[-1] != 3`. The condition
  check is `O(1)`; the body is skipped via short-circuit evaluation.
- Zero-pad block: only runs if `state_shape != original_state_shape
  and original_state_shape[-1] > 3`. Same `O(1)` short-circuit cost.
- Both blocks are documented in the source via detailed comments
  (kanzi.py:1086-1140, 1165-1180) explaining the Wave 121 P4 +
  Wave 177 P1 historical context.

Removing the dead code would be a **net-loss refactor**:

- Loses documentation of the historical bridge architecture.
- Removes defensive fallback for non-standard callers.
- Risks breaking synthetic-mode byte-stability if `_torch_velocity_field`
  is ever re-routed to handle synthetic-mode trajectories with non-3
  latent dims.
- The lines are heavily commented (≈ 50 LOC of historical narrative)
  — deletion loses load-bearing context for future maintainers.

---

## 7. Risk register

### 7.1 LOW — Dead-code confusion for new contributors

**Risk:** A contributor might read kanzi.py:1102-1124 and assume
the bridge is still active on the real-mode hot path.

**Mitigation:** This audit doc (`docs/audit/wave178-p4-velocity-field-noop.md`)
plus the existing kanzi.py:1086-1140 inline comments explicitly note
"Wave 178 will fix the architecture so the trajectory lives in (L, 3)
coord space throughout" and the P4 follow-up confirms the fix.
A future Wave 178 P5 cleanup wave can delete the dead code if a
contributor audit confirms no synthetic-mode callers ever invoke
`_torch_velocity_field` with non-3 `state_shape[-1]`.

### 7.2 LOW — `set_traj_shape((L, N))` external override

**Risk:** If a future sweep runner (or the framework_inv_proj arm in
`tools/_kanzi_sweep_runner.py:449`) overrides the trajectory shape
to `(L, N)` with `N > 3`, the bridge code would re-engage.

**Mitigation:** The `_traj_shape_override` API
(kanzi.py:1701-1717) is documented as a per-call shape override.
Post-P2, the default `_real_state_shape = (64, 3)` is the canonical
real-mode contract. The framework_inv_proj arm's
`set_traj_shape((64, 3))` call is redundant (the default already
returns `(64, 3)`) — a future cleanup can remove it. Any future
sweep runner that overrides to `(L, N)` would need to provide a
`latent_to_coord_decoder` in the conditioning cache; this is a
known and documented contract.

### 7.3 LOW — Test assertion drift

**Risk:** Tests that explicitly assert
`_real_state_shape == (64, 512)` would fail post-P2.

**Mitigation:** Wave 178 P2 already updated
`tests/test_adapters/test_kanzi_real_ckpt.py:351,608,697` from
`(64, 512)` to `(64, 3)`. D.4 72/72 PASS confirms no regression.

---

## 8. Recommended follow-up (optional)

A future Wave 178 P5 (cleanup wave) could:

1. **Delete the dead code** (kanzi.py:1102-1124 bridge + 1176-1180
   zero-pad) if a contributor audit confirms no synthetic-mode
   callers reach `_torch_velocity_field` with non-3 `state_shape[-1]`.
2. **Delete the framework_inv_proj arm's external bridge call**
   (`tools/_kanzi_sweep_runner.py:414-441 —
   _synthesize_x_final_real`) and the
   `adapter.set_traj_shape((64, 3))` call (line 449) since the
   adapter's default `_real_state_shape` is now `(64, 3)`.
3. **Delete `_synthesize_x_final_real`'s bridge call** entirely
   (the adapter's `build_initial_state` handles it internally —
   though this is a larger refactor because the bridge integration
   into `build_initial_state` itself is a follow-up wave, not
   part of P2+P3+P4).

These cleanups are not required for Wave 178 P4 — the dead code
is documented, harmless, and preserved for defensive fallback.

---

## 9. References

- Wave 178 P1 design: `docs/audit/wave178-p1-design.md` §2.4
  (`_torch_velocity_field` REMOVE bridge + zero-pad — replaced by
  this P4 audit confirming the code is now a no-op)
- Wave 178 P2 commit: `3675a89` — `_real_state_shape = (L, 3)`
- Wave 178 P3 commit: `de2d4bd` — `build_initial_state` → `(L, 3)` x0
- Wave 177 P1 zero-pad origin: kanzi.py:1102-1180 (commit `28ccc78` parent)
- Wave 121 P4 bridge origin: kanzi.py:1116
- D.4 byte-stable regression vectors: `regression-vectors/kanzi.json`
  (synthetic-mode only; unaffected by Wave 178)
- GATES.md §D.4: authoritative D.4 figure = 72/72