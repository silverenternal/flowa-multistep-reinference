# Wave 177 — kanzi real ckpt shape fix + lineageflow synthetic composite fix

**Date:** 2026-09-17
**Branch:** main
**Scope:** Two additive fixes from the Wave 176 §8 follow-up list.

---

## 1. P1 — Kanzi real ckpt shape fix (PATCH APPLIED; full ODE blocked by bridge CPU cost)

### 1.1 Root cause

`tools/eval/baseline.py:90` calls `adapter.solve_ode(bundle, condition, seed=int(seed))`
which routes to `KanziAdapter.solve_ode → _velocity_field → _torch_velocity_field`.
Inside `_torch_velocity_field` (kanzi.py:1030+), when the state shape's last
dim is not 3 (real mode → `(L=64, n_channels_decoder=512)`), the Wave 121
P4 bridge collapses the input to `(L, 3)` backbone coords for the model
forward — but the velocity field returns `(L, 3)`. The integrator at
`x_cur + dt * v1` (kanzi.py:2380) then raises:

```
ValueError: operands could not be broadcast together with shapes (64, 512) (64, 3)
```

### 1.2 Fix (kanzi.py Wave 177 P1)

Capture `original_state_shape = state_shape` **before** the Wave 121 P4
bridge mutates it. After the model forward, if `state_shape !=
original_state_shape` (i.e. the bridge ran), pad the `(L, 3)` velocity
back to `(L, original_n_channels)` with zeros in channels 3:N. The
model velocity lives in coord space (first 3 channels); the remaining
N-3 channels are held at zero velocity, so the trajectory's N-3 latent
channels stay frozen at their initialization.

```python
# Wave 177 P1 — captured BEFORE the bridge mutates state_shape
original_state_shape = state_shape

if state_shape[-1] != 3:
    bridge_decoder = ...
    state_shape = (*state_shape[:-1], 3)

# ... model forward returns out of shape (L, 3) ...

# Wave 177 P1 — pad velocity back to original (L, N) shape
if state_shape != original_state_shape and original_state_shape[-1] > 3:
    v_3d = out.reshape(state_shape)
    v_padded = np.zeros(original_state_shape, dtype=np.float64)
    v_padded[..., :3] = v_3d[..., :3]
    return v_padded
return out.reshape(state_shape)
```

### 1.3 Mathematical honesty

The fix is **mathematically lossy** — the (L, N) trajectory's first 3
channels carry the model velocity; channels 3:N are held at zero
velocity so they stay frozen at initialization. This is a **temporary
workaround** that unblocks the integrator. The principled fix (Wave 178)
is to redesign the architecture so the trajectory lives in (L, 3) coord
space throughout (initialize x0 as 3D coords; integrate in 3D; export
as 3D for downstream AR prior).

### 1.4 Bridge CPU cost — full ODE blocked

The bridge (`kanzi_latent_to_coords` → `DAE.decode`) is a CPU-bound
diffusion rollout invoked **per velocity field call**. With NFE=10 and
n_rounds=3, the integrator makes ~30 velocity field calls per arm
(baseline + framework) → ~60 bridge invocations per cell → ~12 min wall
on a single CPU core. Each invocation does ~50 DAE.decode denoising
steps → 3000 numpy ops per cell. This is **fundamentally too slow** for
a single-cell sanity check, let alone a 6-cell sweep.

**Decision**: document the shape fix as a source-code change that
unblocks the architecture but is **not exercised end-to-end** due to
bridge CPU cost. The Wave 176 §10.22 paper claim (both baselines saturate
at 100% on primary metric, framework correctly ties) is unchanged
because kanzi synthetic primary metric evaluation does NOT use the
bridge (synthetic adapter is NumPy-only). The shape fix is load-bearing
infrastructure for Wave 178 architectural redesign.

---

## 2. P2 — Lineageflow synthetic composite fix

### 2.1 Root cause

`_compute_lineageflow_composite` (tools/eval/metrics.py) computes a
3-term weighted scalar from `baseline_trace` vs `framework_trace`. In
**synthetic** mode, the LineageFlow adapter uses a deterministic NumPy
velocity field — the baseline and framework trajectories have near-zero
entropy reduction (phi1 ≈ 0) and near-zero argmax turnover (phi3 ≈ -1),
collapsing the composite to ~−0.25 (fallback-equivalent). This is a
**real measurement**, not a bug, but it misleads the reader: −0.25
suggests framework hurts lineageflow, when in fact the synthetic
trajectories don't differ enough to give a meaningful composite.

### 2.2 Fix (metrics.py Wave 177 P2)

Add a synthetic-mode early-return:

```python
# Wave 177 P2 — synthetic-mode lineageflow composite is
# meaningless because synthetic trajectories have near-zero
# entropy + near-zero turnover (deterministic NumPy field), so
# phi1/phi3 collapse and the composite degenerates to a
# hard-coded −0.25 fallback (Wave 176 §2.3). Return ``None``
# instead so the eval pipeline doesn't report a misleading
# negative composite for synthetic lineageflow. Real ckpt
# lineageflow gives meaningful +composite (Wave 176: +0.20 /
# +0.14 / +0.05 at NFE=50/100/200).
adapter_mode = getattr(adapter, "_mode", None)
if adapter_mode == "synthetic":
    debug["reason"] = (
        "synthetic_mode_composite_not_meaningful "
        "(deterministic NumPy field; use real ckpt)"
    )
    return None, "blocked_synthetic_mode", debug
```

### 2.3 Verification

`python3 -c "..."` with `force_mode="synthetic"` returns
`composite=None, composite_marker="blocked_synthetic_mode"`. Real ckpt
mode is unaffected (composite = +0.2031 at NFE=50, identical to Wave
176 evidence).

---

## 3. Lineageflow real re-run (Wave 177 P3)

Re-ran the Wave 176 lineageflow real ladder to confirm the synthetic-mode
composite fix doesn't perturb real-ckpt behavior:

| NFE | baseline primary | framework primary | composite | status |
|----:|-----------------:|------------------:|----------:|--------|
|  50 |          **1.00** |          **1.00** | **+0.2031** | TIE_AT_SATURATION |
| 100 |          **1.00** |          **1.00** | **+0.1426** | TIE_AT_SATURATION |
| 200 |          **1.00** |          **1.00** | **+0.0488** | TIE_AT_SATURATION |

**Bit-identical to Wave 176** (composite values match to 4 decimal
places: +0.2031249, +0.1425780, +0.0488280). The synthetic-mode early
return is a pure addition that doesn't perturb real-ckpt behavior.

---

## 4. Verification gates

- `pytest tests/ -k "d4" -q` → **33 passed, 30 skipped** (D.4 33/33 PASS).
- `ruff check tools/eval/metrics.py adaptive_reflow/adapters/kanzi.py`
  → **All checks passed!**
- `python tools/check_claims_consistency.py` → **No drift detected.**

---

## 5. Honest disclosure

* **Kanzi real ckpt shape fix is a source-code change that is NOT
  exercised end-to-end** — bridge CPU cost (~12 min/cell) blocks the
  N=30 sweep. The shape fix is load-bearing infrastructure for Wave
  178 architectural redesign.
* **Lineageflow synthetic composite of −0.25 was a real measurement,
  not a bug** — it correctly reflected that synthetic trajectories
  don't differ enough. The Wave 177 P2 fix replaces this misleading
  reading with `None` + "blocked_synthetic_mode" marker.
* **Wave 176 §10.22 paper claim is unchanged** — both baselines saturate
  at 100% on primary metric, framework ties, wins on secondary metrics
  with headroom. Wave 177 P2 just cleans up the lineageflow synthetic
  composite display.

---

## 6. File paths (absolute)

* `<repo_root>/adaptive_reflow/adapters/kanzi.py`
  — Wave 177 P1 shape pad (lines ~1102-1179).
* `<repo_root>/tools/eval/metrics.py`
  — Wave 177 P2 synthetic-mode early return (lines ~1543-1554).
* `<repo_root>/docs/audit/wave177-shape-composite-fixes.md`
  — this audit document.

## 7. Wall-clock timing

| Stage | dt |
|-------|----|
| Kanzi real NFE=50 sanity (killed — bridge CPU bound) | ~7 min before kill |
| Kanzi real NFE=10 sanity (killed — bridge CPU bound) | ~12 min before kill |
| Lineageflow real 3-cell re-run (Wave 177 P3) | 85 + 143 + 277 = 505 s (~8.5 min) |
| Total session wall | ~30 min |

## 8. Follow-up (Wave 178 flagged)

1. Kanzi real ckpt architecture redesign — trajectory in (L, 3) coord
   space throughout (eliminate bridge CPU cost + mathematical lossiness).
2. Kanzi real primary metric (validity_rate) end-to-end sweep on
   GPU-backed bridge (currently bridge is CPU-only).