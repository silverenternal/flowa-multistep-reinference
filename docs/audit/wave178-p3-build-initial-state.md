# Wave 178 P3 — `build_initial_state` initializes `x0` as `(L, 3)` in real mode

**Date:** 2026-09-17
**Branch:** main (HEAD `de2d4bd`, post-Wave 178 P2 `3675a89`)
**Scope:** P3 follow-up to Wave 178 P1's redesign audit and P2's
`_real_state_shape = (L, 3)` change. Re-architect
`KanziAdapter.build_initial_state` to produce an `(L, 3)` x0 in real
mode (instead of implicitly relying on `_real_state_shape`); preserve
the synthetic-mode `(L, 64)` initialization byte-identically so the
D.4 vector suite stays 33/33 PASS.

---

## 1. Why this change is load-bearing

After Wave 178 P2 (commit `3675a89`), `KanziAdapter._real_state_shape`
returns `(KANZI_ABSTRACT_AR_SEQ_LENGTH, 3) = (64, 3)` in real mode.
The pre-P3 `build_initial_state` called
`_synthesize_latent_like_tensor(rng, shape=self._real_state_shape)`,
which **functionally** already sampled `(64, 3)` noise in real mode
(because `_real_state_shape` was `(64, 3)`). The implicit chain was:

```
build_initial_state
  -> _real_state_shape = (64, 3)            [post-P2]
  -> _synthesize_latent_like_tensor((64,3))
  -> x0.shape == (64, 3)
```

This worked at runtime but was **fragile**: a future refactor of
`_real_state_shape` (e.g. for a per-record backbone-length change in
a later wave) would silently shift `build_initial_state`'s x0 shape
without any local change to the function. The P3 change makes the
shape selection **explicit** and **branch-on-mode** inside
`build_initial_state`, decoupling it from `_real_state_shape`'s
evolution.

The post-P3 chain is:

```
build_initial_state
  -> if _abstract_mode: x0_shape = KANZI_ABSTRACT_STATE_SHAPE  # (64, 64)
  -> else:              x0_shape = (KANZI_ABSTRACT_AR_SEQ_LENGTH, 3)
  -> _synthesize_latent_like_tensor(x0_shape)
  -> x0.shape == x0_shape (explicit)
```

`_real_state_shape` is now **read-only** by `build_initial_state`'s
own shape selection; only the downstream `_effective_traj_shape`
(used by `solve_ode`, `apply_restart_distribution`,
`observe_endpoint`) reads it. This makes the contract:

* `build_initial_state` produces `(64, 64)` (synthetic) or `(64, 3)`
  (real), unconditionally.
* `solve_ode` / `apply_restart_distribution` / `observe_endpoint`
  operate on whatever shape `build_initial_state` produced (via
  `_effective_traj_shape()`'s fallback to `_real_state_shape`).

The two contracts stay synchronized because both are now consistent
with `_real_state_shape`'s `(64, 3)` / `(64, 64)` return, but
`build_initial_state`'s shape is **directly** asserted at the call
site rather than implicitly derived.

---

## 2. The change (specific file:line targets)

### 2.1 `KanziAdapter.build_initial_state` — explicit branch-on-mode

**File:** `adaptive_reflow/adapters/kanzi.py:1831-1956`
**Lines touched:** `1842-1882` (sampling block) + `1921-1940`
(storage block).

**Before (P2 state):**

```python
rng = np.random.default_rng(seed)
# Wave 92 — in real mode the latent has shape
# ``(L_abstract, n_channels_decoder)`` instead of the
# abstract ``(64, 64)``. This ensures the trajectory the
# solver produces matches the upstream DAE decoder input.
# Wave 124 Agent 5 — ``build_initial_state`` always produces the
# canonical ``_real_state_shape`` latent (``(64, 512)`` in real
# mode). ... [30 more lines of comment]
x0 = _synthesize_latent_like_tensor(
    rng, shape=self._real_state_shape,
)
# ... [later in the function]
self._native_states.put(
    digest,
    {
        # Wave 124 Agent 5 — always store ``x0`` in the canonical
        # ``_real_state_shape`` (``(64, 512)`` in real mode). ...
        "x0": np.asarray(x0, dtype=np.float64).reshape(
            self._real_state_shape,
        ),
        ...
    }
)
```

**After (P3 state):**

```python
rng = np.random.default_rng(seed)
# Wave 178 P3 — initialize ``x0`` in the trajectory's NATIVE
# shape so the integrator's ``x_cur + dt * v1`` broadcast is
# shape-safe end-to-end:
#
# * real mode (``torch`` ckpt loaded) — ``(L_abstract, 3)``
#   backbone coords in nm. ... [comment block]
# * synthetic / abstract mode — ``(L_abstract, d) = (64, 64)``
#   ... [comment block]
#
# Wave 124 Agent 5 — the per-call ``_traj_shape_override``
# (set by the framework_inv_proj arm ...) ... [comment block]
if self._abstract_mode:
    x0_shape: tuple[int, ...] = KANZI_ABSTRACT_STATE_SHAPE
else:
    # Real mode — backbone coords (L, 3) in nm.
    x0_shape = (int(KANZI_ABSTRACT_AR_SEQ_LENGTH), 3)
x0 = _synthesize_latent_like_tensor(rng, shape=x0_shape)
# ... [later in the function]
self._native_states.put(
    digest,
    {
        # Wave 178 P3 — store ``x0`` in the same shape we sampled
        # it in (``x0_shape``: ``(64, 3)`` in real mode,
        # ``(64, 64)`` in synthetic mode). ...
        "x0": np.asarray(x0, dtype=np.float64).reshape(
            x0_shape,
        ),
        ...
    }
)
```

**Net diff:** 48 insertions, 25 deletions in
`adaptive_reflow/adapters/kanzi.py`. The branch is a single
`if self._abstract_mode:` with two tuple-shape assignments.

### 2.2 Why we sample noise directly (no bridge call)

The Wave 178 P1 design doc (§2.2) proposed a two-stage init:
sample `(L, 512)` latent, then run the Wave 95.P3.B bridge
(`kanzi_latent_to_coords`) to project to `(L, 3)` backbone coords.
**P3 defers the bridge call** — the sampled `(L, 3)` array is just
small `N(0, I)` noise keyed on the seed. Rationale:

1. **D.4 preservation** — the D.4 vector suite is synthetic-only and
   must stay 33/33 PASS byte-identically. A bridge call inside
   `build_initial_state` would have to gate on `_abstract_mode` to
   preserve synthetic behavior, and the bridge is not exercised in
   synthetic mode (the synthetic velocity field takes `(L, 64)`
   input, not `(L, 3)`).

2. **CPU cost** — `kanzi_latent_to_coords` is a 100-NFE diffusion
   rollout (~12 min/cell on CPU). Moving it from inside the
   per-`_velocity_field` invocation (Wave 177 P1's zero-pad patch)
   to inside `build_initial_state` reduces it from `NFE * 12
   min/cell` to `12 min/cell` per record. **P3 doesn't yet wire the
   bridge** because the existing CPU ckpt-loading path is gated on
   `_model is not None` and is not exercised in the regression
   vector suite.

3. **Determinism** — `np.random.default_rng(seed)` with the same
   `seed_from_ids(batch_id, sample_id)` produces deterministic noise
   regardless of mode. The D.4 vector suite exercises synthetic mode
   with a fixed seed; the noise byte-stream is reproducible.

4. **Forward-compatible** — a follow-up wave (Wave 178 P5 or later)
   can add the bridge call behind the `if not self._abstract_mode:`
   guard once the per-cell CPU cost is budgeted for the real-ckpt
   validation runs. The P3 stop-gap keeps the architecture
   byte-stable while the bridge integration is finalized separately.

### 2.3 Why `_real_state_shape` stays unchanged

`_real_state_shape` continues to return `(64, 3)` in real mode (P2
contract). It is consumed by:

* `solve_ode` (line 2364-2366 + 2382-2384): trajectory shape for the
  integrator's `np.empty((T+1, *_effective_traj_shape()))` and the
  per-step `x_cur.reshape(self._effective_traj_shape())`.
* `apply_restart_distribution` (line 2014-2016 + 2078-2079):
  `prior_x.reshape(self._effective_traj_shape())` and the
  `m_vec_full` broadcast target.
* `observe_endpoint` (line 2525-2527): trajectory endpoint reshape.
* `inject_forward_noise` (line 3052-3057): prior and injected
  reshape.

After P3, all 4 downstream sites still resolve to `(64, 3)` in real
mode (via `_effective_traj_shape()` -> `_real_state_shape`). The
trajectory stays in `(L, 3)` coord space throughout. **No
downstream change required** — P3 only touches `build_initial_state`'s
sampling + storage blocks.

---

## 3. D.4 preservation strategy

The D.4 regression vectors at `regression-vectors/kanzi.json` cover
synthetic mode only (the vector generator at
`tools/run_regression_vector_audit.py:537-539` instantiates
`KanziAdapter(force_mode="synthetic", num_steps=10)` — no real ckpt).
The synthetic-mode branch in P3's `build_initial_state` is:

```python
if self._abstract_mode:
    x0_shape: tuple[int, ...] = KANZI_ABSTRACT_STATE_SHAPE
```

`KANZI_ABSTRACT_STATE_SHAPE = (KANZI_ABSTRACT_AR_SEQ_LENGTH,
KANZI_ABSTRACT_LATENT_DIM) = (64, 64)` — **byte-identical to the
pre-P3 `_real_state_shape` return in synthetic mode**. The sampling
call is `_synthesize_latent_like_tensor(rng, shape=(64, 64))` with
the same `seed_from_ids(batch_id, sample_id, seed_offset+0)` RNG
seed, advancing the same `rng.standard_normal((64, 64))` call. The
digest is computed from `x0.shape` (which is still `(64, 64)`) plus
the same `latent_first`, `discrete_first`, and
`conditioning_hash` fields.

**Net result:** byte-identical x0, byte-identical digest,
byte-identical native-state cache entry, byte-identical
`StateBundle`, byte-identical downstream trajectory. The 33 D.4
vectors regenerate identically.

### 3.1 D.4 test command

```bash
PYTHONPATH=. python -m pytest tests/ -k "d4" -q
```

**Result (post-P3):** `33 passed, 30 skipped, 5028 deselected`
(skip count is for unrelated torch-availability + hypothesis-availability
gates, identical to pre-P3).

### 3.2 Synthetic-mode contract preservation

The 18+ existing synthetic-mode tests at
`tests/test_adapters/test_kanzi_smoke.py` assert:

| Line | Property | Pre-P3 | Post-P3 |
| --- | --- | --- | --- |
| 201 | `x0.shape == KANZI_STATE_SHAPE` | `(64, 64)` PASS | `(64, 64)` PASS |
| 223 | `traj.shape == (5, *KANZI_STATE_SHAPE)` | `(5, 64, 64)` PASS | `(5, 64, 64)` PASS |
| 245 | `x_final.shape == KANZI_STATE_SHAPE` | `(64, 64)` PASS | `(64, 64)` PASS |

All pass byte-identically. **No test changes required.**

---

## 4. Verification results

### 4.1 D.4 vector suite

```text
PYTHONPATH=. python -m pytest tests/ -k "d4" -q
33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.53s
```

33/33 PASS, byte-identical to Wave 178 P2 / Wave 177.

### 4.2 Kanzi smoke + main kanzi tests

```text
PYTHONPATH=. python -m pytest tests/test_adapters/test_kanzi_smoke.py \
    tests/test_adapters/test_kanzi.py -q
27 passed, 2 skipped, 3 warnings in 0.34s
```

27/27 PASS (2 skipped due to torch-availability, identical to pre-P3).

### 4.3 Combined kanzi + D.4 suite

```text
PYTHONPATH=. python -m pytest tests/test_adapters/test_kanzi_smoke.py \
    tests/test_adapters/test_kanzi.py \
    tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q
99 passed, 2 skipped, 3 warnings in 39.32s
```

99/99 PASS (2 skipped due to torch-availability).

### 4.4 Ruff

```text
ruff check adaptive_reflow/ tools/ docs/
Found 6 errors.
```

The 6 errors are pre-existing in `docs/build_pdf/md_to_tex.py`
(unrelated `md_to_tex` import-sorting + UP015 + F841 warnings),
verified by running `git stash && ruff check ...` on the
pre-P3 tree (same 6 errors found). **My change introduces 0 ruff
errors.**

### 4.5 Claims consistency

```text
PYTHONPATH=. python tools/check_claims_consistency.py
# Claims consistency report
- Active claims: **39**
- Provisional claims: **0**
- Deprecated claims: **2**
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, ..., CLM-047
**No drift detected.**
```

Claims PASS. CLM-040 (FlowMol3 framework 0/0) is unchanged
provisional, identical to Wave 177 / Wave 178 P2.

---

## 5. Commit

```text
commit de2d4bdfd8fb094b6cc5f47d376a6561d9011ab1
Author: Claude Code <claude@anthropic.com>
Date:   Thu Sep 17 22:30:00 2026 +0800

    Wave 178 P3: build_initial_state initializes x0 as (L, 3) in real
    mode (synthetic mode unchanged for D.4 preservation)

    Co-Authored-By: Claude Code <noreply@anthropic.com>
```

1 file changed, 48 insertions(+), 25 deletions(-).

---

## 6. References

* Wave 178 P1 audit: `docs/audit/wave178-p1-design.md` §2.2 (the
  proposed `build_initial_state` change), §3 (D.4 preservation
  strategy).
* Wave 178 P2 commit: `3675a89` (`_real_state_shape` returns
  `(L_abstract, 3)` in real mode).
* Wave 177 P1 zero-pad workaround: `kanzi.py:1086-1181` (the
  per-`_velocity_field` bridge call that P3's
  `build_initial_state` makes redundant in real mode — bridge now
  runs ONCE at init time, deferred to a follow-up wave).
* Wave 121 P4 bridge origin: `tools/kanzi_latent_to_coord.py`
  (the diffusion-decode bridge that P3 defers).
* Wave 124 Agent 1 `set_traj_shape` API: `kanzi.py:1697-1737`
  (kept for backwards compat; default is now `(L, 3)` in real mode).
* D.4 byte-stable regression vectors: `regression-vectors/kanzi.json`
  (synthetic-mode only; unaffected by Wave 178 P3).