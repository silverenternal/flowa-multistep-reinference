# Wave 178 P1 — Kanzi real ckpt architecture redesign (trajectory in `(L, 3)` coord space throughout)

**Date:** 2026-09-17
**Branch:** main (HEAD `beb2440`, post-Wave 177 `cec3328`)
**Scope:** P1 follow-up to Wave 177 P1's zero-pad workaround. Re-architect
the real-mode trajectory shape so the bridge runs **ONCE at init time**
(not per velocity-field call) and the integrator never sees mismatched
shapes.

---

## 1. Root cause confirmation (Wave 177 P1 limitation)

The Wave 177 P1 patch (kanzi.py:1102-1180) is a temporary workaround that
unblocks the kanzi real ckpt full ODE integration path but is
**mathematically lossy**: the trajectory's N-3 latent channels stay
frozen at initialization because the model velocity lives in coord
space (first 3 channels) and channels 3:N are held at zero velocity.

### 1.1 Three load-bearing facts the Wave 178 P1 redesign must honour

1. **The model input/output is `(B, L, 3)` backbone coords in nm.**
   `_KanziDAEShim.forward` (kanzi.py:1246-1272) calls
   `self._dae.encode(x)` which feeds `_dae.up` (`nn.Linear(3, 256)` —
   the upstream `DAE.up` at `data/kanzi_upstream/src/kanzi/models.py:292`)
   that requires `(B, L, 3)` backbone coords. The output of
   `self._dae.net(x, t, z_BLD=z)` is a velocity field in **the same
   `(B, L, 3)` coord space**.

2. **The bridge is per-(L, N) row → (L, 3) coord conversion.** The
   `kanzi_latent_to_coords` function (`tools/kanzi_latent_to_coord.py:75+`)
   currently ingests a `(L, n_channels_decoder=512)` latent, applies the
   trained `Linear(512 → 4)` inverse (`_apply_project_out_inv` at line
   293+), argmin-over-codebook, then runs `DAE.decode(idx_BL)` — a 100-NFE
   diffusion rollout that costs ~12 min/cell on CPU. The output is the
   `(L, 3)` backbone coords in Å (×10 from nm).

3. **The framework_inv_proj arm already runs the bridge ONCE at init
   time** (tools/_kanzi_sweep_runner.py:414-441 — `_synthesize_x_final_real`),
   then calls `adapter.set_traj_shape((64, 3))` (line 449) so
   `solve_ode` operates on `(L, 3)` x0 throughout. This is the
   end-to-end pattern that works; the Wave 177 P1 zero-pad is a
   degraded re-implementation of the same idea (with a per-step bridge
   call instead of a single init-time call).

### 1.2 Why the zero-pad workaround is unfixable as-is

The Wave 177 P1 fix calls the bridge **inside every `_velocity_field`
invocation** (kanzi.py:1116). At NFE=10 the integrator calls the
velocity field 10 times per cell → 10× bridge calls per cell → 10×
~12 min/cell on CPU. This is the load-bearing cause of the
"12 min/cell" cost surfaced in Wave 174-177 evidence. The bridge is
per-(L, N) row → (L, 3) coord conversion; once the trajectory is in
coord space, **no further bridge calls are needed** for the velocity
field to operate on `(L, 3)` input.

The fundamental fix: do the bridge projection **ONCE at
`build_initial_state` time**, then run `solve_ode` on `(L, 3)`
throughout. The framework_inv_proj arm already proves this works
end-to-end (the `_synthesize_x_final_real` path uses `set_traj_shape`
to honor the post-bridge shape).

---

## 2. Proposed changes (specific file:line targets)

### 2.1 `_real_state_shape` — return `(L_abstract, 3)` in real mode

**File:** `adaptive_reflow/adapters/kanzi.py:1680-1695`

**Before:**
```python
@property
def _real_state_shape(self) -> tuple[int, ...]:
    if self._abstract_mode or self._real_latent_dim is None:
        return KANZI_ABSTRACT_STATE_SHAPE  # (64, 64)
    return (
        int(KANZI_ABSTRACT_AR_SEQ_LENGTH),  # 64
        int(self._real_latent_dim),         # 512
    )
```

**After:**
```python
@property
def _real_state_shape(self) -> tuple[int, ...]:
    """Real-mode trajectory lives in (L_abstract, 3) COORD SPACE.

    The trajectory shape matches the upstream DAE's input/output
    shape ((B, L, 3) backbone coords in nm) so the velocity field
    shim's `DAE.encode(x)` -> `DAE.up` (Linear(3, 256)) matmul does
    not crash and the bridge runs ONCE at init time instead of per
    velocity-field call.

    `L_abstract = 64` is a placeholder matching the abstract default;
    per-record `solve_ode` overrides `L` from the prior entry if the
    per-record backbone length is stashed there (a Wave 92+
    follow-up — currently all real-mode integrations run with
    `L = L_abstract`).
    """
    if self._abstract_mode or self._real_latent_dim is None:
        return KANZI_ABSTRACT_STATE_SHAPE
    return (
        int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
        3,  # backbone coord dim (was self._real_latent_dim=512 in Wave 177)
    )
```

**Compatibility:** Synthetic-mode byte-stability preserved
(`KANZI_ABSTRACT_STATE_SHAPE = (64, 64)` unchanged). The 18+ existing
synthetic-mode tests at `tests/test_adapters/test_kanzi*.py` continue
to pass because they assert on `KANZI_STATE_SHAPE == (64, 64)`, NOT
on `_real_state_shape`.

**Tests that explicitly check `real.state_shape == (64, 512)`:**
- `tests/test_adapters/test_kanzi_real_ckpt.py:351` (`assert caps.state_shape == (64, 512)`)
- `tests/test_adapters/test_kanzi_real_ckpt.py:608` (`assert real.state_shape == (64, 512)`)
- `tests/test_adapters/test_kanzi_real_ckpt.py:697` (`assert real._real_state_shape == (64, 512)`)

These three assertions must change from `(64, 512)` → `(64, 3)` after
the Wave 178 P1 redesign. The capability surface assertion
(`caps.state_shape == (64, 3)`) becomes the new real-mode contract.

### 2.2 `build_initial_state` — produce `(L, 3)` x0

**File:** `adaptive_reflow/adapters/kanzi.py:1862-1916`

**Before:** `build_initial_state` samples a latent from
`_synthesize_latent_like_tensor(rng, shape=self._real_state_shape)`
(line 1862-1864) — currently `(64, 512)`.

**After:** Two-stage init.

1. Sample the canonical latent from
   `_synthesize_latent_like_tensor(rng, shape=(L, _real_latent_dim))`
   (the existing `(64, 512)` path — moved out of `_real_state_shape`
   into a new `_real_latent_shape` property for the latent-sampling
   step).
2. Run the Wave 95.P3.B bridge ONCE to project `(L, 512)` →
   `(L, 3)` backbone coords in nm:
   ```python
   if not self._abstract_mode:
       bridge_decoder = self._resolve_bridge_decoder()  # cached at init
       x0_coords_nm = kanzi_latent_to_coords(
           x0, decoder=bridge_decoder,
           fsq_quantizer=bridge_decoder.quantize,
           n_steps=self._decoder_nfe_steps,
           seed=int(seed),
       ).reshape(-1, 3) / 10.0  # (B, L, 3) Å → (L, 3) nm
   else:
       x0_coords_nm = x0  # synthetic-mode (no bridge)
   ```
3. Store the bridged `(L, 3)` x0 in the native-state cache; subsequent
   `solve_ode` operates on this `(L, 3)` trajectory throughout.

**Bridge caching:** The bridge decoder must be cached at adapter init
time (currently injected as `conditioning["latent_to_coord_decoder"]`
per call — Wave 121 P4 contract). New private attribute
`self._bridge_decoder: Any | None` is populated when the real ckpt
loads (mirrors `self._model = _load_torch_model(...)` at line 1599).

**The existing framework_inv_proj arm**
(`tools/_kanzi_sweep_runner.py:414-441`) already does this dance
externally — the Wave 178 P1 design moves it INSIDE
`build_initial_state` so all callers (sweep runner, eval driver,
reproduction scripts) get it for free.

### 2.3 `solve_ode` — no shape mutation; velocity field receives `(L, 3)`

**File:** `adaptive_reflow/adapters/kanzi.py:2368-2422`

**Before:** `x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(self._effective_traj_shape())` (line 2368-2370). Trajectory array has shape `(num_steps+1, *self._effective_traj_shape())` (line 2385-2388).

**After:** Same shape math; the only change is that `prior_entry["x0"]`
arrives already in `(L, 3)` shape (from §2.2's `build_initial_state`).
`self._effective_traj_shape()` returns `(L_abstract, 3)` in real mode
via §2.1. The `_velocity_field` call at line 2395-2397 sees `(L, 3)`
input throughout; the integrator's `x_cur + dt * v1` (line 2420) is
shape-safe `(L, 3) + dt * (L, 3)`.

### 2.4 `_torch_velocity_field` — REMOVE bridge call, REMOVE zero-pad

**File:** `adaptive_reflow/adapters/kanzi.py:1086-1181`

**Before:** Lines 1110-1124 (bridge call + shape collapse) and lines
1176-1180 (zero-pad velocity back to `(L, N)`). Both blocks are the
Wave 121 P4 bridge and the Wave 177 P1 zero-pad workaround.

**After:** Delete both blocks. The function becomes:
```python
def _torch_velocity_field(
    model, x, t, *, dtype, cache, guidance_scale,
    state_shape=...,  # (L, 3) in real mode; (64, 64) in synthetic
):
    x = make_validate_state_shape(state_shape)(np.asarray(x, dtype=np.float64))
    import torch
    with torch.no_grad():
        device = next(model.parameters()).device
        x_t = torch.as_tensor(x, dtype=dtype, device=device).unsqueeze(0)
        t_t = torch.tensor([float(t)], dtype=dtype, device=device)
        family_t = torch.as_tensor(
            cache.get("family_embed", np.zeros(1152, dtype=np.float64)),
            dtype=dtype, device=device,
        ).unsqueeze(0)
        v = model(x_t, t_t, family=family_t)
        out = np.asarray(v.squeeze(0).detach().cpu().numpy(), dtype=np.float64)
    return out.reshape(state_shape)  # (L, 3)
```

**Net change:** ~70 LOC deletion (kanzi.py:1102-1181). The bridge
function `kanzi_latent_to_coords` is **only called once** at
`build_initial_state` time (per §2.2), not per velocity-field call.

### 2.5 `_velocity_field` — no override logic needed

**File:** `adaptive_reflow/adapters/kanzi.py:2282-2317`

**Before:** Line 2314 reads `state_shape=self._effective_traj_shape()` —
the per-call override is required because the framework_inv_proj arm
overwrites `prior_entry["x0"]` to `(L, 3)` at runtime
(`tools/_kanzi_sweep_runner.py:441`) and `set_traj_shape((64, 3))`
follows at line 449.

**After:** Same `state_shape=self._effective_traj_shape()` call; the
override is still needed (it remains the per-call shape override for
the sweep runner pattern), but **the default** (no override) is now
already `(L, 3)` in real mode via §2.1's `_real_state_shape` change.
The sweep runner's external bridge call
(`_synthesize_x_final_real` at line 414-441) can be **deleted** because
`build_initial_state` now handles it internally — but this is an
optional cleanup, not a Wave 178 P1 requirement.

### 2.6 `export_endpoint` — return `(L, 3)` trajectory endpoint

**File:** `adaptive_reflow/adapters/kanzi.py:2506-2598`

**Before:** Line 2529-2531 reshapes `trajectory[-1]` to
`self._effective_traj_shape()` (currently `(L, 512)` in real mode
without override; `(L, 3)` with the framework_inv_proj override).

**After:** Same `.reshape(self._effective_traj_shape())` call. With
§2.1's `_real_state_shape = (L, 3)`, the endpoint arrives as `(L, 3)`
backbone coords in nm without needing the per-call override.

**The downstream consumer chain is also `(L, 3)`-native:**
- The bridge function `kanzi_latent_to_coords` (consumed by
  `tools/_kanzi_sweep_runner.py:835` for the `framework_synthetic`
  arm) currently expects `(L, 512)` and returns `(L, 3)` after
  diffusion decode. Post-Wave 178 P1 the `framework_synthetic` arm
  keeps this bridge (its x0 is synthetically synthesized in
  `(L, 512)` latent space); the `framework_inv_proj` arm collapses
  to `build_initial_state`-internal bridge use.
- The sweep runner's outer nm→Å conversion
  (`coords_pred_A = (x_final * 10.0).reshape(-1, 3)` at line 805)
  is already `(L, 3)`-aware. No change needed.

### 2.7 AR prior decoder in `observe_token_indices`

**File:** `adaptive_reflow/adapters/kanzi.py:2618-2715`

The AR prior decoder is independent of the trajectory shape — it walks
the native-state chain via `src_digest` and returns the discrete-token
indices which have shape `(L_z,)`, NOT `(L, d)`. The
`(L, 3)` → `(L, 512)` conversion is irrelevant here. **No change
needed.**

### 2.8 `observe_entropy_reduction` (per-position Mahalanobis)

**File:** `adaptive_reflow/adapters/kanzi.py:2721-2885`

The function consumes `trajectory[-1]` of shape `(T+1, L_z, d)` and
computes per-position empirical covariance. The covariance math is
shape-agnostic in `d` — `(L, 3)` instead of `(L, 512)` is a smaller,
more numerically stable Mahalanobis distance (the d×d covariance is
3×3 instead of 512×512). **No change needed; the metric becomes more
robust by side-effect.**

### 2.9 Downstream frame validators

`tools/paper_metrics_kanzi.py` and `tools/sweep_kanzi_n1000_*.py`
consume the trajectory's last-step endpoint. The Wave 174-177 evidence
shows the framework_inv_proj arm **already produces `(L, 3)` endpoint**
via `_synthesize_x_final_real`'s bridge call at line 428-441. The
sweep runner's outer `coords_pred_A = (x_final * 10.0).reshape(-1, 3)`
(line 805) is `(L, 3)`-native. **No change needed** in these
consumers — the Wave 178 P1 design aligns the adapter's internal
trajectory shape with what the sweep runner's framework_inv_proj arm
already produces.

---

## 3. D.4 preservation strategy

**The D.4 regression vectors at `regression-vectors/kanzi.json`
cover SYNTHETIC MODE ONLY** (the vector generator at
`tools/run_regression_vector_audit.py:537-539` instantiates
`KanziAdapter(force_mode="synthetic", num_steps=10)` — no real ckpt).
The synthetic-mode trajectory shape is `(64, 64)`, which Wave 178 P1
preserves byte-identically:
- `_real_state_shape` returns `(L_abstract, 3)` **only** in real mode
  (`self._abstract_mode is False`); synthetic mode returns
  `KANZI_ABSTRACT_STATE_SHAPE = (64, 64)` unchanged (line 1690-1691).
- `build_initial_state` runs the bridge **only** in real mode
  (`if not self._abstract_mode:` guard at the bridge call site).
- `solve_ode` calls `_velocity_field` → `_torch_velocity_field` in
  synthetic mode via `_synthetic_velocity_field`
  (kanzi.py:2316-2317), which is unaffected by the
  `(L, 512) → (L, 3)` change.

**Verification command (unchanged from Wave 177):**
```bash
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q
```
Expected: 72/72 PASS, byte-identical to Wave 177 (the trajectory
endpoint, kabsch metrics, FASTA bytes, GPT-prior indices all derive
from the same `(64, 64)` synthetic trajectory).

**Synthetic-mode tests at `tests/test_adapters/test_kanzi_smoke.py`
that explicitly assert `KANZI_STATE_SHAPE = (64, 64)`:**
- Line 129: `assert caps.state_shape == KANZI_STATE_SHAPE`
- Line 150-152: `assert adapter.state_shape == KANZI_STATE_SHAPE`
- Line 201: `assert x0.shape == KANZI_STATE_SHAPE`
- Line 223: `assert traj.shape == (5, *KANZI_STATE_SHAPE)`
- Line 245: `assert x_final.shape == KANZI_STATE_SHAPE`
- Line 344: `assert blended.shape == KANZI_STATE_SHAPE`

All continue to PASS because `KANZI_STATE_SHAPE` is unchanged.

**Tests that REQUIRE updates** (real-mode only):
- `tests/test_adapters/test_kanzi_real_ckpt.py:351` →
  `assert caps.state_shape == (64, 3)` (was `(64, 512)`)
- `tests/test_adapters/test_kanzi_real_ckpt.py:608` →
  `assert real.state_shape == (64, 3)` (was `(64, 512)`)
- `tests/test_adapters/test_kanzi_real_ckpt.py:697` →
  `assert real._real_state_shape == (64, 3)` (was `(64, 512)`)

---

## 4. Risk register

### 4.1 HIGH — Bridge decoder caching at adapter init

**Risk:** The bridge decoder is currently injected per call via
`conditioning["latent_to_coord_decoder"]` (kanzi.py:1111). Moving it
to adapter init time requires loading `DAE.from_pretrained(ckpt_path)`
twice (once for the velocity field shim, once for the bridge decoder),
or sharing a single `DAE` instance between the shim and the bridge.

**Mitigation:** Share the loaded `DAE` instance between `_load_torch_model`
and the bridge decoder. The DAE load is the expensive step (~3 GB
fp16 weights); reusing the in-memory instance is a 1-LOC change in
`_load_torch_model`'s `_builder` closure (kanzi.py:1274-1298) to
return both the shim and the underlying DAE. Store as
`self._bridge_decoder: Any` alongside `self._model`.

### 4.2 MEDIUM — Bridge CPU cost at init

**Risk:** `build_initial_state` becomes 12 min/cell slow (the
single-shot bridge call) instead of 12 min/cell slow (the per-NFE
bridge call). Total wall-clock is the same, but the timing moves
from inside `solve_ode` to inside `build_initial_state`.

**Mitigation:** This is exactly the desired behaviour — the bridge
runs ONCE per record, not ONCE per NFE per record. The
`tools/run_regression_vector_audit.py` runs the bridge at most once
per (seed, NFE) pair (9 conditions × 1 bridge call = 9 bridge calls
for D.4 kanzi vector regeneration; same as today). Document the
new init cost in the adapter docstring.

### 4.3 MEDIUM — `set_traj_shape` override path becomes redundant

**Risk:** The framework_inv_proj arm's `set_traj_shape((64, 3))` call
(`tools/_kanzi_sweep_runner.py:449`) was added to handle the case
where `prior_entry["x0"]` is overwritten post-init. With Wave 178 P1
the adapter's default `_real_state_shape` is already `(64, 3)`, so
the override is a no-op.

**Mitigation:** Keep the `set_traj_shape` API for backwards compat
with existing sweep runners that may rely on it; the default is now
correct. Optionally delete `_synthesize_x_final_real`'s external
bridge call (lines 414-441) and the `set_traj_shape` call (line 449)
in a follow-up cleanup wave — these become dead code post-Wave 178.

### 4.4 LOW — `framework_synthetic` arm bridge is still external

**Risk:** The `framework_synthetic` arm
(`tools/_kanzi_sweep_runner.py:761-764`) synthesizes `(L, 512)`
latent x0 and then calls the outer bridge
(`kanzi_latent_to_coords` at line 835-841). This is unchanged by
Wave 178 P1.

**Mitigation:** None needed — the synthetic arm's external bridge
call is the existing contract.

### 4.5 LOW — Kabsch RMSD metric assumes `(L, 3)` backbone coords

**Risk:** `tools/paper_metrics_kanzi.py` consumes the trajectory
endpoint for Kabsch RMSD. The framework_inv_proj arm's `(L, 3)`
endpoint is in nm (multiply by 10 for Å). The framework_synthetic
arm's bridge-decoded endpoint is in Å.

**Mitigation:** Already handled by the existing `coords_pred_A = (x_final * 10.0).reshape(-1, 3)` conversion at `_kanzi_sweep_runner.py:805`.

### 4.6 LOW — Test value mismatches from `_real_state_shape` change

**Risk:** Tests that assert `real.state_shape == (64, 512)` will FAIL
after the change.

**Mitigation:** Three tests at `tests/test_adapters/test_kanzi_real_ckpt.py:351,608,697` need to be updated to `(64, 3)`. The synthetic-mode tests are unaffected (they assert `(64, 64)` which is `KANZI_STATE_SHAPE` unchanged).

### 4.7 LOW — Wave 177 zero-pad test assertions

**Risk:** Any test that explicitly asserts the Wave 177 P1 zero-pad
behaviour (e.g. trajectory channels 3:N frozen at init) will FAIL
after Wave 178 P1 (the channels no longer exist — trajectory IS
`(L, 3)`).

**Mitigation:** Search the test suite for "frozen", "channels 3:N",
"zero pad", "kanzi.py:1180", etc. Update to reflect the new
architecture.

---

## 5. Recommended implementation order

1. **Step 1 — Audit doc + D.4 baseline.** Land this audit doc
   (kanzi.py:2282-2317 → `docs/audit/wave178-p1-design.md`).
   Re-run D.4 72/72 baseline to confirm the audit is non-destructive:
   ```bash
   PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
       tests/test_adapters/test_regression_vectors.py -q
   ```
   Expected: 72/72 PASS.

2. **Step 2 — Bridge decoder caching.** Add
   `self._bridge_decoder: Any | None` to `KanziAdapter.__init__`
   (kanzi.py:1459+). Modify `_load_torch_model._builder` closure
   (kanzi.py:1274-1298) to return BOTH the `_KanziDAEShim` AND the
   underlying `dae` instance. Re-run D.4 — synthetic-mode path is
   untouched (real ckpt not loaded in synthetic mode).

3. **Step 3 — `_real_state_shape` returns `(L, 3)`.** Edit
   `kanzi.py:1680-1695` per §2.1. Update the 3 real-mode test
   assertions at `tests/test_adapters/test_kanzi_real_ckpt.py:351,608,697`
   to `(64, 3)`. Re-run D.4 — synthetic-mode tests pass
   byte-identically; real-mode tests with no ckpt skip.

4. **Step 4 — `build_initial_state` runs bridge once.** Edit
   `kanzi.py:1835-1956` per §2.2. Add bridge invocation behind the
   `if not self._abstract_mode:` guard. Re-run D.4 — synthetic path
   unchanged.

5. **Step 5 — `_torch_velocity_field` removes bridge + zero-pad.**
   Delete `kanzi.py:1110-1124` (bridge) and `kanzi.py:1176-1180`
   (zero-pad). The function becomes a clean `(L, 3) → (L, 3)`
   velocity field call. Re-run D.4 — synthetic path unchanged.

6. **Step 6 — Verify `solve_ode` and `export_endpoint` are
   shape-clean.** Trace `kanzi.py:2368-2500` end-to-end to confirm
   the trajectory array is `(T+1, L, 3)` throughout. Trace
   `kanzi.py:2529-2550` to confirm the endpoint reshape to `(L, 3)`
   matches the new `_effective_traj_shape()` default.

7. **Step 7 — Run real ckpt smoke test (GPU).** Run
   `tools/run_kanzi_real_ckpt.py` with NFE=2, N=3 records to confirm
   the per-cell cost drops from ~24 min (2 NFE × 12 min/bridge) to
   ~12 min (1 bridge call at init).

8. **Step 8 — Run D.4 + full pytest.** Re-run
   `PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
       tests/test_adapters/test_regression_vectors.py -q` (expect
   72/72 PASS) and `pytest tests/ -q` (expect same 5155/5012 pass +
   same 3 pre-existing unrelated FAILED tests as Wave 177).

9. **Step 9 — Commit.** Single atomic commit:
   `Wave 178 P1: kanzi real arch redesign (trajectory in (L,3) coord space throughout)` —
   matches the Wave 177 commit convention.

---

## 6. References

- Wave 177 P1 audit: `docs/audit/wave177-shape-composite-fixes.md` §1
- Wave 121 P4 bridge origin: kanzi.py:1102-1116 (deleted in Wave 178)
- Wave 95.P3.B bridge: `tools/kanzi_latent_to_coord.py` §3 (moved into
  `build_initial_state` in Wave 178)
- Wave 122 P2 framework_inv_proj arm: `tools/_kanzi_sweep_runner.py:414-441`
  (becomes dead code post-Wave 178; can be cleaned up in follow-up)
- Wave 124 Agent 1 `set_traj_shape` API: kanzi.py:1701-1737 (retained
  for backwards compat; default is now `(L, 3)` in real mode)
- Wave 92 + Wave 174 `kanzi_latent_to_coord` linear(512→4) inverse:
  `tools/_kanzi_project_out_inv.pt`
- D.4 byte-stable regression vectors: `regression-vectors/kanzi.json`
  (synthetic-mode only; unaffected by Wave 178)
