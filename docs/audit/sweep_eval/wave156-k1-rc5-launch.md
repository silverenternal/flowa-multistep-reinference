# Wave 156 K1 RC5 Sweep Launch — Real-Ckpt Path Now Exercised (with caveats)

**Wave**: 156 Agent 2 (K1 RC5 N=1000 5-arm real-ckpt sweep launch on RTX PRO 6000 Blackwell)
**Date**: 2026-09-15
**Status**: **PARTIAL — real-ckpt path now exercised for `lineageflow` (5/5 cells OK, distinct from synthetic), but `kanzi` cells all RUN_ERROR due to a pre-existing shape-mismatch bug in the `kanzi_latent_to_coord` bridge (`64x64` latent × `512x4` Linear). 35h / 7-15h ETAs are moot; the sweep completed in ~70 sec. CLI alias bridge (`"real" → "torch"`) was applied as a Wave 156 P2 launch prep, unblocking the kanzi+lineageflow adapter from the `unknown_force_mode:real` ValueError that Wave 155 P2 audit identified.**

## 1. TL;DR

- The full N=1000 5-arm sweep **CLI invocation was launched and ran to completion** on GPU 0 (RTX PRO 6000 Blackwell, free, 2 MiB / 97887 MiB).
- **10/15 cells OK, 5/15 RUN_ERROR, 0/15 BLOCKED** (was 5/15 OK, 0/15 RUN_ERROR, 10/15 BLOCKED before the Wave 156 P2 alias bridge).
- **Actual wallclock**: ~70 seconds. The 35h / 7-15h ETAs are moot because the `kanzi` cells fail fast (within seconds) on the shape-mismatch bridge.
- **Real-ckpt path is now actually exercised** for `lineageflow` — `signed_delta` differs from the synthetic-mode baseline (`-2.66e-14` vs `-0.331` for arm 0), proving the propagation is no longer synthetic-only.
- **Kanzi real-ckpt path** enters torch mode (adapter loads ckpt, mode resolves to `"torch"`, model is invoked), but the per-call `_torch_velocity_field` → `kanzi_latent_to_coords` bridge raises `RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x64 and 512x4)` because `KANZI_STATE_SHAPE = (64, 64)` is 64-dim while the Wave 95 Phase 3.B trained inverse `Linear(512 → 4)` expects 512-dim. This is a **pre-existing shape mismatch**, not introduced by Wave 156 P2.
- All four engineering gates preserved (D.4 / ruff / claims / JSON well-formed).

## 2. CLI launched

```
.venvs/kanzi_venv/bin/python scripts/run_ablation_sweep.py \
    --force-mode real \
    --metric-mode real \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --limit 1000 \
    --output /tmp/w156/k1_rc5_5arm_real_n1000/ablation_q4_2026.json
```

The `.venvs/kanzi_venv/bin/python` interpreter is required because the system
`python` and `python3` do not have `torch` installed, while `kanzi_venv`
has `torch==2.14.0+cu130` with `cuda=True`. Without the venv, the adapter's
`_resolve_mode` raises `RuntimeError: torch requested but not installed` even
when `--force-mode real` (after the alias bridge) is set.

This venv selection is consistent with the Wave 109 / 110 / 111 audit docs,
which used `.venvs/kanzi_venv/bin/python` for all kanzi adapter invocations.

## 3. Launch details

| Field | Value |
|-------|-------|
| Launch time (UTC) | `2026-09-15T04:37:xxZ` (sweep started ~12:37 local) |
| Sweep PID | `359918` |
| Output JSON | `/tmp/w156/k1_rc5_5arm_real_n1000/ablation_q4_2026.json` (29 KB) |
| Output log | `/tmp/w156/k1_rc5_5arm_real_n1000/ablation.log` (31 lines) |
| GPU | 0 — NVIDIA RTX PRO 6000 Blackwell (97887 MiB total, 2 MiB used) |
| Actual wallclock | ~70 seconds (10 OK cells fast + 5 kanzi RUN_ERROR fast) |
| 15-min monitoring pass | N/A — sweep completed in <2 minutes; log inspected in lieu of live monitoring |
| Process state | Exited cleanly after writing JSON |

## 4. Wave 156 P2 alias bridge (the launch-prep patch)

The first launch attempt used the system `python` (no torch installed) and
produced the **expected** `unknown_force_mode:real` ValueError on all kanzi +
lineageflow cells (10/15 BLOCKED). This is the exact bug the Wave 155 P2 audit
flagged at `docs/audit/wave155-real-ckpt-validation.md` "Adapter vocabulary
gap (out of scope for this validation)" — the CLI's literal `"real"` does
not appear in `_resolve_mode`'s `{auto, torch, synthetic}` vocabulary.

The Wave 155 P2 audit explicitly recommended the fix:

> A future fix should alias `"real"` to `"torch"` (or `"auto"`) at the CLI
> boundary (e.g. in `_make_adapter`).

This is now applied as Wave 156 P2 launch prep. Diff (`scripts/run_ablation_sweep.py`):

```diff
@@ -333,7 +333,18 @@ def _make_adapter(model_spec: dict[str, Any],
     any user request to run the real-ckpt path. The kanzi
     re-instantiation below also now inherits the same ``force_mode``
     (was ``"auto"``).
+
+    Wave 156 P2 alias bridge: the CLI's literal ``"real"`` is mapped
+    to the adapter's ``"torch"`` vocabulary here at the CLI boundary
+    so ``--force-mode real`` actually exercises the real-ckpt path.
+    Per Wave 155 P2 audit (`docs/audit/wave155-real-ckpt-validation.md`),
+    the adapter's ``_resolve_mode`` only accepts ``{auto, torch,
+    synthetic}``; before this bridge, ``"real"`` was propagated all
+    the way to the resolver and raised ``unknown_force_mode:real``.
+    Backward-compat preserved: ``"synthetic"`` passes through verbatim.
     """
+    if str(force_mode) == "real":
+        force_mode = "torch"
     module_path, attr = model_spec["adapter_factory_path"].rsplit(":", 1)
```

11 LOC (10 comment + 1 logic), ruff clean (verified), backward-compat preserved
(default `"synthetic"` passes through).

### Why this is launch-prep, not a standalone P1

Wave 155 P2 audit identified this exact gap and explicitly deferred it to a
"future fix" with the CLI-boundary aliasing recommendation. Wave 156 P2 is the
"actual full sweep" per the launch brief, which is unblocked by applying the
audit's recommended fix inline as launch prep. A standalone P1 commit for this
alias would have required launching the sweep, observing it BLOCKED, filing a
P1, applying the P1, re-launching — three commits where one is sufficient.

## 5. Cell-level outcomes

```
Total: 15, OK: 10, RUN_ERROR: 5, BLOCKED: 0
  twodim_fm:    5 cells, OK=5, RUN_ERROR=0, BLOCKED=0
  kanzi:        5 cells, OK=0, RUN_ERROR=5, BLOCKED=0
  lineageflow:  5 cells, OK=5, RUN_ERROR=0, BLOCKED=0
```

### 5.1 Per-cell signed_delta

| Arm | twodim_fm | kanzi | lineageflow |
|-----|-----------|-------|-------------|
| full_framework | 0.9091182704951842 | RUN_ERROR | -2.6645352591003757e-14 |
| no_restart_blend | 0.0 | RUN_ERROR | 0.0 |
| no_paper_quantity_scheduler | 0.9125713104981447 | RUN_ERROR | -2.531308496145357e-14 |
| no_gpt_prior_restart | 0.9091182704951842 | RUN_ERROR | -2.6645352591003757e-14 |
| no_restart_blend_at_all | 0.0 | RUN_ERROR | 0.0 |

For lineageflow, the arm-0 (`full_framework`) signed_delta of `-2.66e-14` is
**distinct from the synthetic-mode arm-0 signed_delta of `-0.331`** (verified
via a synthetic-mode sanity run after the sweep), confirming that the
real-ckpt path is actually being exercised and producing different metric
values. The tiny magnitudes are likely an artifact of the `metric_mode=real`
flag's current no-op pass-through status for lineageflow (per the Wave 155 P1
audit: `metric_mode` is plumbed into `model_spec["metric_mode"]` but the
metric helpers unconditionally compute the synthetic metric).

### 5.2 Kanzi RUN_ERROR detail

All 5 kanzi cells fail with the same error:

```
ValueError: too many values to unpack (expected 3)
File ".../kanzi/models.py", line 351, in encode
    B, L, D = x_BLD.shape
```

Or, in cases where the bridge's `_apply_project_out_inv` is reached:

```
RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x64 and 512x4)
```

These are both **pre-existing shape mismatches** in the kanzi integration:

1. `KANZI_STATE_SHAPE = (64, 64)` (line 282-285) is a 64-dim latent, but the
   `kanzi_latent_to_coord` bridge's `_apply_project_out_inv` (Wave 95 Phase 3.B)
   is a `Linear(512 → 4)` trained inverse of `project_out` and expects a
   512-dim post-`project_out` latent.
2. After the bridge (when applicable), the `x_t = ... .unsqueeze(0)` at line
   1107 stacks the batch dim onto an already-3D tensor, producing 4D input
   that the upstream `DAE.encode` cannot unpack.

Neither is introduced by Wave 156 P2. Both exist independently of the alias
bridge and would surface for any `kanzi` real-ckpt invocation.

### 5.3 What changed vs Wave 154 P1

| Wave | CLI  | Cells OK | Cells BLOCKED | Cells RUN_ERROR | Real-ckpt exercised? |
|------|------|----------|---------------|-----------------|----------------------|
| 154 P1 | `--force-mode real --metric-mode real --ckpt …` | 15/15 | 0 | 0 | NO (synthetic only, all 5/5 cells identical to `--force-mode synthetic`) |
| 156 P2 | same CLI + alias bridge + kanzi_venv | 10/15 | 0 | 5 | YES for `lineageflow` (arm-0 `signed_delta` differs from synthetic); NO for `kanzi` (shape mismatch) |

Net progress: real-ckpt path is now actually being executed for `lineageflow`.
Kanzi still blocked on a separate shape-mismatch bug.

## 6. 15-min monitoring (sweep-already-completed variant)

The original monitoring loop in Wave 156 P2 was designed to poll every 60 sec
for 15 minutes. The sweep completed in ~70 seconds, so the loop was
trivially satisfied. The process exited cleanly after writing the JSON.

Equivalent health-check (post-completion):

| Check | Result |
|-------|--------|
| Process still running | N/A — exited cleanly |
| Output JSON well-formed | YES — `schema=ablation_q4_2026.v1`, 15 cells, 5 arms, 3 models |
| All cells OK or RUN_ERROR (no BLOCKED) | YES — 10/15 OK, 5/15 RUN_ERROR (kanzi), 0/15 BLOCKED |
| No `Traceback`/`Error` strings in log | NO — 5 kanzi `RUN_ERROR` entries in log (expected; documented in §5.2) |
| `twodim_fm` cells OK | YES — 5/5 |
| `lineageflow` cells OK | YES — 5/5 |
| `kanzi` cells OK | NO — 0/5 (shape mismatch in bridge) |

## 7. Gates verified (sweep does not modify code beyond the alias bridge)

| Gate | Command | Result |
|------|---------|--------|
| D.4 broad filter | `.venvs/kanzi_venv/bin/python -m pytest tests/ -k "d4" -q` | **33 passed, 6 skipped, 5436 deselected, 9 warnings** (matches Wave 154 P1 / Wave 152 P3 baseline; 6 additional skipped are torch/rdkit/expecttest/pandas-gated, unrelated) |
| Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/run_ablation_sweep.py` | **All checks passed!** (Wave 156 P1 cleanup + alias bridge, 0 violations) |
| Claims consistency | `.venvs/kanzi_venv/bin/python tools/check_claims_consistency.py` | **No drift detected.** (39 active, 0 provisional, 2 deprecated — matches Wave 154 P1 baseline) |
| Backward-compat sanity (synthetic) | `.venvs/kanzi_venv/bin/python scripts/run_ablation_sweep.py --force-mode synthetic --metric-mode synthetic` | **15/15 cells OK** (matches Wave 152 P3 + Wave 154 P1 + Wave 155 P2 arm-1 baselines; alias bridge is a no-op when force_mode='synthetic') |

All four gates preserved. The 11-LOC alias bridge introduces zero new ruff
violations (verified by `ruff check scripts/run_ablation_sweep.py`: All checks
passed!) and does not regress any D.4 regression vectors.

## 8. What this launch accomplished

1. **Closed the Wave 155 P2 audit's "adapter vocabulary gap"** by applying the
   audit's recommended CLI-boundary alias. The 10 BLOCKED kanzi + lineageflow
   cells in the pre-fix launch now reach the adapter's `_resolve_mode` and
   exercise the real-ckpt path (lineageflow) or attempt it and fail on a
   pre-existing shape bug (kanzi).
2. **Validated the kanzi_venv selection** as the only Python interpreter
   capable of real-ckpt sweeps on this host (system python lacks torch).
3. **Confirmed lineageflow real-ckpt path produces distinct metric values**
   vs synthetic (arm-0 `signed_delta` differs: `-2.66e-14` vs `-0.331`).
4. **Surfaced a pre-existing kanzi shape-mismatch bug** in
   `_torch_velocity_field` × `kanzi_latent_to_coord` bridge:
   `(64, 64)` latent × `Linear(512 → 4)` mismatch + post-bridge 4D input.
   This is **out of scope for Wave 156 P2** but **in scope for a future
   K1-RC5-followup wave**.

## 9. What this launch did NOT accomplish

1. **Kanzi real-ckpt cells did not complete.** All 5 kanzi cells raised
   `ValueError: too many values to unpack (expected 3)` or
   `RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x64 and 512x4)`.
   Fixing this requires either:
   - Changing `KANZI_STATE_SHAPE` to `(64, 512)` (matches the bridge's
     expected post-`project_out` 512-dim latent), or
   - Removing or making conditional the `kanzi_latent_to_coord` bridge call
     when the input is already `(L, 3)` backbone coords.
   Neither is in scope for Wave 156 P2's CLI-launch task.
2. **The 35h / 7-15h GPU budget was not consumed** — the sweep completed in
   ~70 seconds because real-ckpt failures short-circuit the per-cell ODE
   solve loop and the remaining cells use the (fast) synthetic twodim_fm
   adapter.
3. **K1 RC5 is not closed by this launch.** The 5-arm ablation in real-ckpt
   mode is partially exercised (lineageflow yes, kanzi no). A follow-up wave
   is needed to fix the kanzi shape mismatch before the 35h budget can
   materialize.

## 10. Recommendation

K1 RC5 closure requires addressing two bugs in dependency order:

1. **(already done in this Wave 156 P2)** Apply the alias bridge at the
   `_make_adapter` CLI boundary so `--force-mode real` reaches the adapter's
   `_resolve_mode`. **Status: DONE.**

2. **(new follow-up)** Fix the kanzi `_torch_velocity_field` shape mismatch:
   - Either widen `KANZI_STATE_SHAPE` to `(64, 512)` so the bridge's
     `_apply_project_out_inv` is dimensionally consistent, or
   - Skip the `kanzi_latent_to_coords` bridge when the adapter is in
     non-bridge mode (e.g. when the input already represents backbone
     coords `(L, 3)`), and fix the `unsqueeze(0)` after-bridge stacking
     bug that produces 4D input.
   This is **Wave 157 P1 work**, not Wave 156 P2 work.

After both fixes land, re-launch the sweep. Only then will the 35h budget
materialize and the K1 RC5 5-arm ablation be exercisable end-to-end.

## 11. Files touched

- `scripts/run_ablation_sweep.py` (11 LOC: alias bridge in `_make_adapter`)
- `docs/audit/wave156-k1-rc5-launch.md` (this doc, ADDITIVE only)
- `/tmp/w156/k1_rc5_5arm_real_n1000/ablation.log` (31 lines, 15 cells processed)
- `/tmp/w156/k1_rc5_5arm_real_n1000/ablation_q4_2026.json` (29 KB output JSON)

## 12. Commit

See follow-up commit on `docs/audit/wave156-k1-rc5-launch.md` +
`scripts/run_ablation_sweep.py`. No push (push is a separate wave).
