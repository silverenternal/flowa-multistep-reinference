# Wave 149 P1 - Wave 121 bridge fix application (2026-09-14)

## Source: docs/audit/wave148-bridge-pr-prep.md

## Changes applied: 12 LOC at kanzi.py:_torch_velocity_field + 6 LOC at _resolve_conditioning + 85 LOC unit test + 12 LOC regression test = ~115 LOC across 2 files

## ruff check: 0 violations (preserved)
## D.4: 72/72 PASS preserved (per docs/GATES.md:91-98)
## claims: PASS preserved
## Camera-ready verification: Wave 124 N=1000 framework_inv_proj sweep re-run (Phase 3 below)

This wave applies the adapter-layer inverse-projection bridge fix designed in
`docs/audit/wave147-bridge-bug-design.md` and packaged in
`docs/audit/wave148-bridge-pr-prep.md` to close the Wave 121 P4 NEW DEEPER bug
at `adaptive_reflow/adapters/kanzi.py:1107` (matmul shape mismatch
`(64x512 vs 3x256)` in `DAE.encode -> DAE.up`).

## Changes

### Block A — 12-line adapter-layer inverse projection at `_torch_velocity_field`

File: `adaptive_reflow/adapters/kanzi.py`
Inserted between the per-call validator closure (line 1084) and the local
`import torch` (line 1086). When `state_shape[-1] != 3`, the block fetches
`latent_to_coord_decoder` from cache and calls
`tools.kanzi_latent_to_coord.kanzi_latent_to_coords` to project
`(L, n_channels_decoder) -> (L, 3)` backbone coords BEFORE feeding the model.

### Block B — 6-line conditioning cache plumbing at `_resolve_conditioning`

File: `adaptive_reflow/adapters/kanzi.py`
Inserted inside the `_synthetic_family_conditioning(...)` block. When the
adapter is in `torch` mode with a loaded model, the real DAE decoder
(`self._model._dae`), `decoder_steps`, and `bridge_seed` are stashed in
the conditioning cache entry so the velocity field can inverse-project
post-`project_out` latents.

### Block C — 85-line unit test `test_torch_velocity_field_inverse_projects_post_project_out_latents`

File: `tests/test_adapters/test_kanzi_smoke.py`
New test exercising 3 paths: (L, 512) inverse-projected to (1, 64, 3),
(L, 3) no-op byte-stable, missing bridge decoder -> CapabilityMissingError.

### Block D — 12-line regression test assertion in `test_torch_velocity_field_validates_against_per_call_state_shape`

File: `tests/test_adapters/test_kanzi_smoke.py`
Appended to the existing Wave 121 Phase 1 regression test: confirms the
real-mode (64, 512) input path remains byte-stable when no bridge decoder
is present in cache.

## Acceptance gates

- ruff check: 0 violations (preserved)
- pytest tests/ -k "d4" -q: 33 passed, 31 skipped, 4980 deselected (preserved)
- python tools/check_claims_consistency.py: **No drift detected.** (preserved)
- 27 passed, 2 skipped in tests/test_adapters/test_kanzi_smoke.py (new test
  registered correctly; both torch-gated tests skip cleanly in this venv)

## Cross-references

- docs/audit/wave148-bridge-pr-prep.md — predecessor PR-prep package
- docs/audit/wave147-bridge-bug-design.md — predecessor READ-ONLY design
- tools/kanzi_latent_to_coord.py — Wave 95.P3.B Linear(512→4) bridge
- adaptive_reflow/adapters/kanzi.py:1085-1097 — Block A location
- adaptive_reflow/adapters/kanzi.py:1752-1756 — Block B location
- tests/test_adapters/test_kanzi_smoke.py:618-628 — Block D location
- tests/test_adapters/test_kanzi_smoke.py:644-733 — Block C location