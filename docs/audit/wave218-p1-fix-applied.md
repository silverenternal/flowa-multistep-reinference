# Wave 218 P1 — restore Wave 214 P2 Kanzi R2 bridge fix (was uncommitted + discarded)

**Date:** 2026-09-21
**Beat:** Wave 218 P1 (URGENT fix restore per DeepSeek teacher audit)
**Authoring agent:** Wave 218 P1

## Headline

Apply the Wave 214 P2 bridge restore patch to
`tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` (was lost during
Wave 215 P1 ruff test-and-revert cycle) and re-verify byte-stability.

The Wave 196 P3 patch (`c38a900`) introduced a shape-detection
skip-bridge branch in `_synthesize_x_final_real` that detected
`x0_latent.shape[-1] == 3` and **skipped** the Wave 95.P3.B
trained-inverse bridge. Wave 178 P2+P3 changed `build_initial_state` to
emit `(L, 3)` random Gaussian (no longer `(L, n_channels_decoder=512)`),
so this skip-bridge branch always triggered in `framework_inv_proj`.
Combined effect: the framework arm no longer ran `DAE.decode` on a
learned initialization — it started from pure noise. Framework mean
RMSD jumped from the Wave 127 byte-stable **0.8798 Å** to **1.5585 Å**
(+0.66 Å regression, falsely reported as R2 baseline_wins verdict in
Wave 196 + Wave 206 P2).

## What Wave 218 P1 changed

In `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` lines 414-473:

1. **Removed** the Wave 196 P3 skip-bridge if-branch:
   ```python
   if x0_latent.ndim == 2 and x0_latent.shape[-1] == 3:
       x0_coords_A = x0_latent  # already (L, 3) Angstrom (Wave 178+)
   else:
       ...
   ```
2. **Removed** the corresponding `else:` branch (the legacy
   `(B, L, 512)` latent path that called `kanzi_latent_to_coords`).
3. **Added** a fresh synthesis step that samples a `(L=64,
   n_channels_decoder=512)` latent from `N(0, I)` with **σ=1.0**
   (matches pre-Wave 178 `KanziAdapter._synthesize_latent_like_tensor`
   path). σ=1e-3 was tested and found to collapse to the same FSQ
   codebook index (per Wave 214 P2 audit, σ=1e-3 produced mean=1.0222 Å).
4. **Unconditionally calls** `kanzi_latent_to_coords(x0_latent_512,
   decoder=..., fsq_quantizer=..., n_steps=..., seed=...)` on the
   freshly synthesized latent. This restores the Wave 95.P3.B
   trained-inverse bridge path:
   - `_apply_project_out_inv` (Linear 512→4)
   - `fsq_quantizer.codes_to_indices` argmin over the 1000-d codebook
   - `DAE.decode` (100-step diffusion rollout)
5. **Reshapes** to `(L, 3)`, converts to nm (Angstrom / 10.0), stashes
   in `prior_entry["x0"]` and calls `adapter.set_traj_shape((L, 3))`.

Diff stat:
```
 tools/_kanzi_sweep_runner.py | 74 ++++++++++++++++++++++++++------------------
 1 file changed, 44 insertions(+), 30 deletions(-)
```

## Why the fix is safe for synthetic-mode / D.4 byte-stability

The fresh latent synthesis is gated on
`decoder is not None and mode == "framework_inv_proj"`, identical to the
Wave 122 Phase 2 guard. Other call sites (synthetic-mode tests, the
baseline arm that calls `_synthesize_x_final_real` with default
`decoder=None, mode=None`) are **byte-identical** because the entire
fresh-latent synthesis + bridge invocation is gated out for them.

The Wave 178 `(L, 3)` random Gaussian in `build_initial_state` is left
in place for callers that don't go through this path.

## Verification

- **Syntax**: `python3 -c "import ast; ast.parse(open('tools/_kanzi_sweep_runner.py').read()); print('OK')"`
  → OK.
- **Import**: `python3 -c "from tools._kanzi_sweep_runner import _synthesize_x_final_real; print('Import OK')"`
  → OK.
- **D.4 byte-stability**: `.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header`
  → **30/30 PASS** (matches Wave 196 P3 / Wave 215 P3 baseline).
- **Kanzi runner tests** (`tests/test_tools/test_kanzi_sweep_runner.py`):
  7/9 PASS; 2 environment-dependent failures pre-existing on clean main
  (no `kanzi` module in `lineageflow_venv`; same failures were noted in
  Wave 122 Phase 2 + Wave 196 P3 commit messages — they require the
  `kanzi_venv` sidecar to import the upstream `kanzi` package).

## Expected post-fix result

`framework_inv_proj` mean RMSD returns to **~0.88 Å** (Wave 127 / Wave
131 / Wave 149 byte-stable value), and the framework_inv_proj arm again
beats baseline by ~0.02 Å (TIES verdict, inside FSQ noise band).
Full N=1000 verification deferred to Wave 218 P3 (same 4h sweep cost
as Wave 214 P2).

## Cross-references

- `docs/audit/wave214-p1-kanzi-byte-stability-regression.md` — root-cause
  diagnosis (the source of the fix).
- `docs/audit/wave214-p2-kanzi-rerun.md` — Wave 214 P2 audit describing
  the uncommitted fix (N=10 smoke test mean = 0.8758 Å).
- `docs/audit/wave214-p3-clm057-update.md` — Wave 214 P3 verdict
  correction (CLM-057 PROVISIONAL removed, CLM-060 R2 verdict upgraded
  to SUPPORTED framework_wins Cohen's d_z = -0.16, p_bonf = 2.44e-6).
- `docs/audit/wave196-p3-kanzi-n1000-framework-inv-proj.md` — Wave 196
  P3 audit (source of the skip-bridge branch this commit removes).
- `docs/audit/wave206-p2-kanzi-framework-n1000.md` — Wave 206 P2 audit
  (also affected by the same regression, both torch-upgrade and
  bridge-weight-drift hypotheses disproven in Wave 214 P1).

## Incident context

Wave 214 P2 (attempted) applied this same fix as an uncommitted patch
that was discarded by Wave 215 P1 ruff test-and-revert cycle. This commit
(Wave 218 P1) is the FIRST commit that actually persists the fix to git
history. Future R2 framework_wins reproducibility requires git checkout
of this commit or later.

**Note on commit attribution:** the `_kanzi_sweep_runner.py` diff and
this audit doc were both added in commit `e3d1c01` ("Wave 217 P5: E3
reviewer template") because that commit was the bulk-operation window
in which Wave 218 P1 work landed. `e3d1c01` is already pushed to
`origin/main`, so this annotation is delivered as a NEW commit (Wave
218 P4) rather than via `git commit --amend`. The fix byte-content is
unchanged from the bulk commit — only this annotation paragraph is new.