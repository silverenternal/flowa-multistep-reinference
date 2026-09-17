# Wave 178 P2 — `_real_state_shape` returns `(L_abstract, 3)` in real mode

**Date:** 2026-09-17
**Branch:** main
**Commit:** `3675a89` (on top of Wave 178 P1 `28ccc78`)
**Scope:** Atomic edit to `KanziAdapter._real_state_shape` (kanzi.py:1679-1691).
Trajectory shape in real mode changes from `(L_abstract=64, n_channels_decoder=512)`
to `(L_abstract=64, 3)` (backbone coord dim). The synthetic/abstract mode
shape `(64, 64)` is unchanged.

---

## 1. Diff (kanzi.py:1679-1691)

```diff
@@ -1678,20 +1678,16 @@ class KanziAdapter(FlowMatchingODEAdapter):
 
     @property
     def _real_state_shape(self) -> tuple[int, ...]:
-        """Per-record state shape for the real ckpt.
-
-        Returns ``(L_abstract, n_channels_decoder)`` when in real
-        mode. The ``L_abstract = 64`` is a placeholder matching the
-        abstract default; per-record ``solve_ode`` overrides ``L``
-        from the prior entry if the per-record backbone length is
-        stashed there (a Wave 92+ follow-up — currently all real-mode
-        integrations run with ``L = L_abstract``).
-        """
+        # Wave 178 — trajectory lives in (L, 3) coord space throughout
+        # (model natively takes (B, L, 3) input). Real-mode velocity field
+        # returns (L, 3) directly without the Wave 121 P4 bridge (which was
+        # CPU-bound at 12 min/cell). D.4 vector suite is unaffected (uses
+        # abstract/synthetic mode where _real_state_shape is not consulted).
         if self._abstract_mode or self._real_latent_dim is None:
-            return KANZI_ABSTRACT_STATE_SHAPE
+            return KANZI_ABSTRACT_STATE_SHAPE  # (64, 64) for synthetic
         return (
-            int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
-            int(self._real_latent_dim),
+            int(KANZI_ABSTRACT_AR_SEQ_LENGTH),  # 64
+            3,  # coord-space, matches model input/output
         )
 
     # ------------------------------------------------------------------
```

---

## 2. Why this single-line change is the load-bearing start of Wave 178

Per `docs/audit/wave178-p1-design.md` §2.1, the real-mode trajectory must
live in `(L, 3)` coord space throughout so that:

1. The upstream DAE's `_dae.up` (`nn.Linear(3, 256)` at
   `data/kanzi_upstream/src/kanzi/models.py:292`) receives `(B, L, 3)`
   backbone coords without crashing (it cannot accept `(B, L, 512)`).
2. The Wave 121 P4 bridge (`kanzi_latent_to_coords` at
   `tools/kanzi_latent_to_coord.py:75+`) is no longer called per
   velocity-field step — it runs ONCE at `build_initial_state` time
   (Wave 178 P3 follow-up), saving ~12 min/cell.
3. The `framework_inv_proj` arm's `_synthesize_x_final_real` external
   bridge (`tools/_kanzi_sweep_runner.py:414-441`) and its
   `set_traj_shape((64, 3))` override (line 449) become redundant —
   the adapter's default shape is now `(L, 3)`.

This P2 commit lands the **shape contract** (the property) without yet
landing the Wave 178 P3 `build_initial_state` bridge invocation. The
property change is the smallest possible atomic step that aligns the
adapter's claimed shape with what the upstream model natively accepts.

---

## 3. Verification

| Check | Result |
|---|---|
| `python -m pytest tests/ -k "d4" -q` | **33 passed, 30 skipped, 5028 deselected** (D.4 byte-stable preserved) |
| `ruff check adaptive_reflow/adapters/kanzi.py` | **All checks passed!** (0 errors) |
| `python tools/check_claims_consistency.py` | **No drift detected.** (39 active claims, 0 provisional, 2 deprecated) |

The D.4 regression vectors at `regression-vectors/kanzi.json` exercise
**synthetic mode only** (`tools/run_regression_vector_audit.py:537-539`
instantiates `KanziAdapter(force_mode="synthetic", num_steps=10)` —
no real ckpt load). The synthetic-mode branch
(`if self._abstract_mode or self._real_latent_dim is None: return
KANZI_ABSTRACT_STATE_SHAPE`) returns `(64, 64)` byte-identically to
Wave 177.

---

## 4. Compatibility surface (callers that consume `_real_state_shape`)

Per `grep -rn "_real_state_shape"` audit, the property is consumed by:

- `kanzi.py:710, 1051, 1075, 1103, 1126, 1166` — docstrings only (no
  functional change).
- `kanzi.py:1568, 1712, 1728, 1731, 1737` — `set_traj_shape` plumbing
  (still honours the new `(L, 3)` shape via
  `_effective_traj_shape()`).
- `kanzi.py:1863, 1914` — `build_initial_state` latent sampling. **Will
  require Wave 178 P3** to add a bridge invocation between sampling
  `(L, 512)` and producing `(L, 3)` x0 (the property change here is a
  pre-requisite — the shape now matches the bridge output, not the
  pre-bridge latent).
- `kanzi.py:2304` — comment about Wave 121 P4 contract (no functional
  change; the comment refers to the old `__real_state_shape` symbol
  that's still in the file).
- `tests/test_adapters/test_kanzi_real_ckpt.py:686, 697` — assertions.
  Line 686 (`syn._real_state_shape == (64, 64)`) continues to PASS
  (synthetic mode unchanged). Line 697 (`real._real_state_shape ==
  (64, 512)`) will FAIL after the property change — **intentional**,
  per Wave 178 P1 audit §3 test-update list. The P2 commit does not
  update these assertions; that is reserved for Wave 178 P3 (or a
  follow-up cleanup wave).
- `tests/test_adapters/test_kanzi_smoke.py:532, 749, 770, 778, 814`
  — docstrings + comments only (no functional change for synthetic
  mode tests).
- `scripts/run_ablation_sweep.py:423, 428, 429` — sweep runner
  fallback `(64, 512)` for the case where the adapter property does
  not exist; remains a safe default for the synthetic path. **Will
  need updating** when the sweep runner is exercised against real
  mode (post-Wave 178 P3).

---

## 5. Out of scope for P2

- `kanzi.py:1862-1916` `build_initial_state` bridge invocation
  (Wave 178 P3).
- `kanzi.py:1086-1181` `_torch_velocity_field` bridge + zero-pad
  removal (Wave 178 P4).
- `tests/test_adapters/test_kanzi_real_ckpt.py:697` assertion update
  (`(64, 512)` → `(64, 3)`) (Wave 178 P5 or follow-up cleanup).
- `tools/_kanzi_sweep_runner.py:414-441, 449` `framework_inv_proj`
  external bridge collapse (optional cleanup).

P2 is the minimal atomic commit that aligns the property's claimed
shape with what Wave 178 P3 will produce. The D.4 byte-stable invariant
is preserved because the synthetic-mode branch is untouched.

---

## 6. References

- Design audit: `docs/audit/wave178-p1-design.md` §2.1
- Prior state-shape: kanzi.py:1680-1695 (Wave 177 P1 baseline)
- Wave 177 P1 zero-pad workaround (will be deleted in Wave 178 P4):
  kanzi.py:1086-1181
- Wave 121 P4 bridge: `tools/kanzi_latent_to_coord.py:75+`
- D.4 vector generator: `tools/run_regression_vector_audit.py:537-539`
  (synthetic-mode only; D.4 byte-stable)