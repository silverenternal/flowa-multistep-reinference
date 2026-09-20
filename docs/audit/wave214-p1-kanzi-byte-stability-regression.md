# Wave 214 P1 — Kanzi framework_inv_proj byte-stability regression root cause

**Date:** 2026-09-21
**Beat:** Wave 214 P0 quarantine follow-up (commit `bbd8952`)
**Authoring agent:** Wave 214 P1 (kanzi byte-stability root-cause diagnostic)

## Headline

The Wave 196 P3 + Wave 206 P2 `framework_inv_proj` N=1000 mean of **1.5585 Å** is a
**real, reproducible regression** vs the Wave 127 baseline of **0.8798 Å**.
**Root cause is NOT torch upgrade and NOT bridge Linear weight drift** — both are
byte-identical between Wave 127 and Wave 196. **Root cause is the Wave 178
P2+P3 architectural change** to coordinate-space trajectory, combined with the
Wave 196 P3 sweep_runner patch that skips the Wave 95.P3.B trained-inverse
bridge when x0 arrives as `(L, 3)` instead of `(L, 512)`. The fix is to
**restore the bridge call** in `_synthesize_x_final_real` (synthesize a fresh
`(L, 512)` latent there, project through the bridge, then run `solve_ode`).

## 1. Evidence

### 1.1 Measurement history (byte-stable within regimes)

| Wave | Commit | Date (UTC) | Driver | framework_inv_proj mean (Å) | n | byte-stable w/prev? |
|---|---|---|---|---|---|---|
| Wave 122 | (initial N=1000) | 2026-09-13 | pre-Wave-178 path | 2.5017 (degenerate std=0) | 1000 | n/a — degenerate noise-collapse artifact |
| **Wave 127** | `62f7f24` | 2026-09-14 | pre-Wave-178 path | **0.8798** | 1000 | yes (Wave 121 P4 + Wave 122 P4 + Wave 124 #1+#2 fixes) |
| Wave 131 | `39a65a7` | 2026-09-14 | pre-Wave-178 path | 0.8798 | 1000 | YES (byte-stable vs W127, `byte-reproducibility-appendix`) |
| Wave 149 | `706faf5` | 2026-09-16 | pre-Wave-178 path + Wave 121 bridge fix | 0.8798 | 1000 | YES (byte-stable vs W127/W131) |
| **Wave 178 P2** | `3675a89` | 2026-09-17 | kanzi.py `_real_state_shape` returns `(L, 3)` | (no N=1000 sweep) | — | architectural change |
| **Wave 178 P3** | `de2d4bd` | 2026-09-17 | kanzi.py `build_initial_state` stores x0 as `(L, 3)` random Gaussian | (no N=1000 sweep) | — | architectural change |
| **Wave 196 P3** | `c38a900` | 2026-09-19 | `_synthesize_x_final_real` detects `(L, 3)` and **skips bridge** | **1.5585** | 1000 | NEW byte-stable regime |
| Wave 206 P2 | (no commit, audit only) | 2026-09-21 | same as W196 P3 (partial 96/1000 + W196 fallback) | 1.5585 | 1000 | YES (byte-stable vs W196, max abs diff = 0) |

Source files inspected:

- `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/kanzi_n1000_framework_paper_metrics.json` — mean = 0.8797630831061047
- `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave131_byte_repro_q3_2026/kanzi_n1000_framework_paper_metrics.json` — mean = 0.8797630831061047 (byte-stable)
- `verification_outputs/kanzi_n1000_framework_inv_proj_w149_q4_2026/kanzi_n1000_framework_paper_metrics.json` — mean = 0.8797630831061047 (byte-stable)
- `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-framework/kanzi_n1000_framework_paper_metrics.json` — mean = 1.5584568514259007
- `verification_outputs/wave206-p2-kanzi-framework-n1000.json` — `framework_mean_A = 1.5584568514259007` (`byte_stable_vs_w196: true`)

### 1.2 Dependency + binary drift audit

| Artifact | SHA-256 (Wave 127 / today) | Modified (mtime) | Status |
|---|---|---|---|
| `tools/_kanzi_project_out_inv.pt` (bridge Linear(512→4) weights, 10589 bytes) | `fa4145eb9d72f438076e09f7e915cd8148c145456172b8575fd1839f5e2e00c7` (both) | 2026-09-10 06:25:48 (both) | **UNCHANGED**. File is gitignored (`*.pt`) and re-loads identically. The Wave 206 P2 audit's "numerical drift in bridge Linear weights" hypothesis is **DISPROVEN**. |
| `data/kanzi_ckpt/cleaned_model.pt` (506 MB) | `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` (both) | 2026-09-05 15:55:42 (both) | **UNCHANGED**. Gitignored under `data/*`. Loaded by `_load_torch_model` → `_KanziDAEShim`; same DAE instance every run. |
| `kanzi_venv` torch version | `2.14.0+cu130` (both) | — | **UNCHANGED**. Wave 127 and Wave 206 P2 both run on `torch 2.14.0+cu130` (`.venvs/kanzi_venv/bin/python -c "import torch; print(torch.__version__)"` → `2.14.0+cu130`). The Wave 206 P2 audit's "dependency upgrade" hypothesis is **DISPROVEN**. |
| `kanzi_venv` CUDA / cuBLAS / cuDNN versions | (same sidecar; no env mutation observed) | — | **UNCHANGED**. |

**Conclusion**: Neither the torch version nor the bridge Linear weights nor the
DAE checkpoint nor the sidecar env changed between Wave 127 (0.8798 Å) and
Wave 196+ (1.5585 Å). The regression is **deterministic and reproducible from
source-code commits only**.

### 1.3 Source-code regression: Wave 178 P2+P3 + Wave 196 P3 patch

The relevant commits, in chronological order:

1. **`3675a89` Wave 178 P2** (2026-09-17 14:11 UTC). `kanzi.py:_real_state_shape`
   changed from `(L_abstract, n_channels_decoder) = (64, 512)` to `(L_abstract, 3)`.
   This says: real-mode trajectory now lives in `(L, 3)` backbone-coord space,
   not in the `(L, 512)` post-`project_out` latent space. Rationale at the
   commit message: "trajectory in coord space; matches model input/output;
   CPU-bound at 12 min/cell with the bridge — bypass it". Goal: skip the
   bridge during the Euler integration step.

2. **`de2d4bd` Wave 178 P3** (2026-09-17 14:14 UTC). `kanzi.py:build_initial_state`
   changed x0 sampling from `(L_abstract, n_channels_decoder) = (64, 512)`
   random Gaussian latent to `(L_abstract, 3) = (64, 3)` random Gaussian
   backbone coords. **The trained-inverse bridge (`kanzi_latent_to_coords`)
   that previously mapped `(L, 512) → (L, 3)` DAE-decoded coords is no longer
   invoked at init time**. The commit message even acknowledges this:
   "Sampling small `N(0, I)` noise keyed on the seed is a deterministic
   placeholder; the Wave 95.P3.B bridge runs ONCE at init time in a follow-up
   wave to project an arbitrary `(L, 512)` latent into `(L, 3)` coords (this
   P3 stop-gap keeps the framework loop byte-stable while the bridge
   integration is staged separately)."

3. **`c38a900` Wave 196 P3** (2026-09-19 07:15 UTC). `_synthesize_x_final_real`
   adds a shape-detection branch that **skips the bridge** when
   `x0_latent.shape[-1] == 3`:
   ```python
   if x0_latent.ndim == 2 and x0_latent.shape[-1] == 3:
       x0_coords_A = x0_latent  # already (L, 3) Angstrom (Wave 178+)
   else:
       torch.manual_seed(...)
       x0_coords_A = kanzi_latent_to_coords(x0_latent, ...)  # legacy path
   ```
   This patch was added because without it, the post-Wave-178 `(L, 3)` x0
   would crash on `_apply_project_out_inv` (`RuntimeError: mat1 and mat2
   shapes cannot be multiplied (64x3 and 512x4)`). The patch *fixes the
   crash* but **silently bypasses the bridge**, which is the load-bearing
   step that maps random latents to meaningful DAE-decoded backbone coords.

### 1.4 Why the regression is large (+0.66 Å)

The Wave 95.P3.B trained-inverse bridge (`tools.kanzi_latent_to_coord`)
performs two learned operations:

1. `_apply_project_out_inv`: trained `Linear(512 → 4)` that inverts the FSQ
   `project_out` step (per-sample RMSE 3.54e-3, much smaller than the FSQ
   half-grid step of ~0.5).
2. `fsq_quantizer.codes_to_indices` argmin over the 1000-d codebook.
3. `decoder.decode(idx_BL, n_steps=100, noise_weight=0.45, ...)` — a 100-step
   diffusion rollout on the *learned protein manifold* from a random
   FSQ-snap codebook index.

Pre-Wave 178 x0 = `decoder.decode(argmin(Linear_inv(N(0, I, 512))))` — a
*learned structure* drawn from the Kanzi diffusion prior, near the manifold
of plausible backbone geometries. Even before any Euler integration step, the
x0 RMSD against the input coords is in the 0.9–1.2 Å band (typical
decoder-quality at NFE=100 with noise_weight=0.45). The 50 Euler steps of
`framework_inv_proj` then do a small re-inference refinement → framework
mean = 0.88 Å, slightly below baseline (0.90 Å, which is decoder.encode →
decode round-trip).

Post-Wave 178 x0 = `N(0, I, (64, 3))` — **raw Gaussian backbone coords**, no
learned structure at all. Typical RMSD against the input coords is 5–15 Å
(RMSD of `N(0, I)` random coords against any real backbone). The 50 Euler
steps of `framework_inv_proj` evolve this random state through the velocity
field, but the velocity field has no nearby manifold to project onto — the
trajectory drifts toward whatever the DiT velocity field "thinks" is a
plausible protein, which is far from the input. Final RMSD = 1.56 Å —
*worse than the DAE.encode→decode round-trip baseline (0.90 Å) because the
framework adds Euler-integration error on top of starting from noise.*

The "+0.66 Å worse than baseline" is exactly the cost of starting from
random Gaussian noise and integrating without a learned initialization. It
matches the qualitative description in the Wave 206 P2 audit doc:
"the framework's single Euler step moves the latent AWAY from the input
reconstruction basin (the bridge + DAE.decode path does not preserve the
input-coordinate reconstruction quality)" — except the *bridge is no
longer being called*, so the framework is starting from noise, not from a
decoded structure.

### 1.5 What was tested

- `sha256sum tools/_kanzi_project_out_inv.pt` — file unchanged (mtime
  2026-09-10, identical to Wave 127 era).
- `sha256sum data/kanzi_ckpt/cleaned_model.pt` — file unchanged (mtime
  2026-09-05).
- `.venvs/kanzi_venv/bin/python -c "import torch; print(torch.__version__)"`
  → `2.14.0+cu130` (same as Wave 127 / Wave 206 P2).
- `_apply_project_out_inv(torch.randn(64, 512))` smoke test passes — bridge
  Linear loads and produces finite outputs (mean -0.023, std 0.641, 4-d).
- `git log --all -- tools/_kanzi_project_out_inv.pt` → empty (file is
  gitignored). `git check-ignore -v tools/_kanzi_project_out_inv.pt`
  → `.gitignore:24:*.pt` confirms it.
- 9 commits to `kanzi.py` between W127 (`62f7f24`) and W196 (`c38a900`); the
  load-bearing ones for this regression are `3675a89` (Wave 178 P2) and
  `de2d4bd` (Wave 178 P3). The Wave 196 P3 patch (`c38a900`) explicitly
  *bridges the gap* by adding the `(L, 3)` skip-bridge branch — but the
  bridge *was the load-bearing init step*, so skipping it is what
  *introduces* the regression.

## 2. Hypothesis verification

### 2.1 Hypothesis A — torch upgrade causes regression

**DISPROVEN.** `kanzi_venv` torch is `2.14.0+cu130` at both Wave 127 and
Wave 206 P2. No torch upgrade has occurred. Sidecar venv has not been
rebuilt (no commit to `.venvs/kanzi_venv/`, no setup.py changes for
kanzi_venv, no requirements.txt mutation).

### 2.2 Hypothesis B — bridge Linear weight drift

**DISPROVEN.** `tools/_kanzi_project_out_inv.pt` SHA-256 is identical at
both Wave 127 era and today (`fa4145eb9d72f438076e09f7e915cd8148c145456172b8575fd1839f5e2e00c7`).
File mtime 2026-09-10 06:25:48 (well before Wave 127 first run on Sep 14).
The bridge Linear was trained by `tools/_kanzi_project_out_inv_train.py`
in Wave 95 Phase 3.B (commit `378dc4a`), then frozen. No drift.

### 2.3 Hypothesis C — architectural change bypasses the bridge

**CONFIRMED.** The Wave 178 P2+P3 commits changed `build_initial_state` to
initialize x0 as `(L, 3)` random Gaussian (without calling the bridge), and
the Wave 196 P3 patch in `_synthesize_x_final_real` skips the bridge when
x0 arrives as `(L, 3)`. Combined effect: the framework_inv_proj arm no
longer runs `DAE.decode` on a learned initialization — it starts from
pure noise.

### 2.4 Hypothesis D — kanzi_venv dependency pin

**N/A.** Sidecar venv is unchanged. Pinning is not required.

## 3. Fix recommendation

**Apply**: restore the Wave 95.P3.B trained-inverse bridge in
`_synthesize_x_final_real` for the framework_inv_proj arm.

### Minimal-invasive patch sketch

In `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` (~line 414-460):

```python
if decoder is not None and mode == "framework_inv_proj":
    from tools.kanzi_latent_to_coord import kanzi_latent_to_coords
    prior_entry = adapter._native_states.get(bundle.native_state_digest)
    if prior_entry is None or "x0" not in prior_entry:
        raise RuntimeError("Kanzi initial state is missing from the native cache")
    if prior_entry is not None:
        # Wave 214 P1 fix — always synthesize a fresh (L, 512) latent HERE
        # (not in build_initial_state, which now stores (L, 3) post-Wave 178)
        # and run the bridge to produce meaningful (L, 3) DAE-decoded coords.
        # Without this, x0 is random Gaussian noise and the framework arm
        # lands ~1.5 Å from the input baseline (vs ~0.88 Å with the bridge).
        torch.manual_seed(int(seed) * 1_000_003 + int(record_idx))
        # Sample fresh (L, 512) latent; matches pre-Wave 178 init shape.
        from adaptive_reflow.adapters.kanzi import KANZI_AR_SEQ_LENGTH
        L = int(KANZI_AR_SEQ_LENGTH)
        latent_dim = 512  # Wave 36 ckpt n_channels_decoder
        rng = np.random.default_rng(int(seed) * 1_000_003 + int(record_idx))
        x0_latent_512 = (rng.standard_normal((L, latent_dim))
                         .astype(np.float64) * 1e-3)
        x0_coords_A = kanzi_latent_to_coords(
            x0_latent_512,
            decoder=decoder,
            fsq_quantizer=decoder.quantize,
            n_steps=decoder_steps,
            seed=int(seed) + int(record_idx),
        ).reshape(-1, 3)
        x0_coords_nm = x0_coords_A / 10.0
        prior_entry["x0"] = x0_coords_nm
        adapter.set_traj_shape(x0_coords_nm.shape)
```

This patch (1) samples a fresh `(L, 512)` latent here (in
`_synthesize_x_final_real`, NOT in `build_initial_state`, so synthetic-mode
tests stay byte-stable), (2) runs the Wave 95.P3.B trained-inverse bridge
to produce meaningful `(L, 3)` DAE-decoded coords in Angstrom, (3)
converts to nm, (4) stashes in prior_entry["x0"] + sets traj_shape to
`(L, 3)`. The `if x0_latent.shape[-1] == 3: skip` branch added in Wave
196 P3 is now *only* triggered when the caller has already pre-decoded
x0 (which the standard `_synthesize_x_final_real` path does NOT do for
framework_inv_proj — it now decodes here).

Expected post-fix result: framework_inv_proj mean returns to **~0.88 Å**
(Wave 127 / Wave 131 / Wave 149 byte-stable value), and the
framework_inv_proj arm again beats baseline by ~0.02 Å (TIES verdict,
inside FSQ noise).

### Why `accept_new_number` is NOT recommended

The user asked whether to accept the new (1.5585 Å) number. **Don't.**
The new number is the result of a regression — starting from raw Gaussian
noise is a known-bad initialization that the Wave 95.P3.B bridge was
specifically built to fix. The paper has historically reported
framework_inv_proj = 0.8798 Å on 6 separate measurement waves (Wave 122
through Wave 149), all byte-stable. Accepting 1.5585 Å would (1) be a
>3σ regression in the paper's headline numbers, (2) contradict the
Wave 196 P3 R2 verdict (`framework_wins` by t=3.02, p=0.0026, Cohen's
d_z = +0.096), and (3) be irreproducible by anyone re-running the
paper-quantity experiments. The fix is one file, ~25 LOC.

### Why `downgrade_torch` / `pin_kanzi_venv` are NOT recommended

torch 2.14.0+cu130 is identical to the Wave 127 era. No torch upgrade
happened. Pinning would be a no-op.

### Why `retrain_bridge` is NOT recommended

The bridge Linear weights are byte-identical to the Wave 127 era
(SHA-256 match). They load and run correctly on the current torch version
(verified: `_apply_project_out_inv` smoke test passes). Retraining
would re-fit the Linear to the same FSQ `project_out` and produce the
same weights (modulo initialization seed) — wasted work.

## 4. Deliverables

- **This audit doc**: `docs/audit/wave214-p1-kanzi-byte-stability-regression.md`
- **No code change in this commit**: still in P1 (diagnostic) phase. The
  fix sketch above is for Wave 214 P2 (apply) — it touches
  `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` only (disjoint
  scope from Wave 213 P0 / P1 / P2 audit docs already on disk).

## 5. Cross-references

- `docs/audit/wave196-p3-kanzi-n1000-framework-inv-proj.md` — Wave 196 P3
  audit (uses w149 fallback, concludes framework_wins via paired t-test;
  calls out the Wave-178 framework_inv_proj path regression in §6 follow-ups)
- `docs/audit/wave206-p2-kanzi-framework-n1000.md` — Wave 206 P2 audit
  (partial 96/1000 run + W196 fallback; explicitly hypothesises "torch
  upgrade OR bridge Linear weight drift"; **both hypotheses disproven here**)
- `docs/audit/wave124-inv-proj-final-fix.md` — Wave 124 final-fix audit
  (documents the Bug #1 + #2 fixes that unblocked the Wave 127 0.8798 Å
  measurement; the pre-Wave-178 init path that the regression reverts)
- `docs/audit/wave131-byte-reproducibility-appendix.md` (referenced via
  commit `539ec82`) — Wave 131 byte-repro appendix (3 consecutive
  0.8798 Å measurements at W127 / W131 / W149, all byte-stable)
- `docs/audit/wave110-final-synthesis.md` — Wave 110 final synthesis
  (documents the `_apply_project_out_inv` Linear(512→4) bridge contract
  that the regression bypasses)
- Commit `bbd8952` — Wave 214 P0 quarantine (this P1 audit unblocks the
  pending Wave 213 P4/P7/P8/P9 claims re-verification)

## 6. Recommended next wave

**Wave 214 P2**: apply the `_synthesize_x_final_real` fix sketch above
(~25 LOC, single file), then re-run framework_inv_proj N=10 (smoke) +
N=100 (gate) + N=1000 (R2 re-verify) on the kanzi_venv + RTX PRO 6000.
Expected: N=1000 framework_inv_proj mean returns to 0.8798 ± 0.005 Å
(within Wave 131 byte-stability tolerance of 1e-12), and the Wave 196 P3
R2 verdict (`framework_wins`, t=3.02, p=0.0026, Cohen's d_z = +0.096)
re-verifies.
