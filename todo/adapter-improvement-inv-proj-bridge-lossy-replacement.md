# Adapter improvement — Kanzi framework_inv_proj bridge (lossy replacement + non-degenerate endpoint)

**Date:** 2026-09-12
**Author:** Wave 123 Agent 6 (READ-ONLY synthesis; no implementation in Wave 123)
**Status:** DONE (implementation landed in Waves 122–125; see `docs/audit/kanzi-inv-proj-bridge-followup-2026-09-13.md`)
**Wave:** Wave 123+ candidate (this plan is detailed enough that a future
wave can pick it up and ship)
**Closes:** Wave 92c §5 (Kanzi framework arm NOT_MEASURABLE due to lossy
L2 nearest-neighbour bridge) + Wave 95 P3.B/C RETRY (trained inverse
bridge tested FAILED on a degenerate synthetic endpoint) + Wave 121
Phase 4 NEW bug (DAE.up mat1×mat2 shape mismatch in framework_inv_proj).
**Companion synthesis doc:** `todo/algo-improvement-framework-vs-model-metrics-gap.md` §2
(hypothesis H5 NEGATIVE) + §3 (8-adapter structural gap, Kanzi row #1) + §4 (rank #3).

> **Why this matters:** The Kanzi framework arm currently regresses by
> **+0.86 Å** on `reconstruction_kabsch_rmsd_A` at N=10 framework
> arm (Wave 99.B, Bonferroni p=4.6e-7) vs baseline. At N=1000
> framework_synth the regression is +1.65 Å (Wave 121 Phase 3); at
> N=1000 framework_inv_proj (Wave 95 historical) it is +1.60 Å.
> The +0.86 Å is the largest single gap between framework and
> baseline on any Tier 3 paper metric, and it is the ONLY Tier 3
> paper metric where the framework REGRESSES with statistical
> significance after Bonferroni correction. Closing this gap is
> the highest-priority paper-axis fix.

---

## 1. Background

### 1.1 The Kanzi framework arm architecture

The Kanzi paper-AE architecture (ICLR 2026 protein) is a flow-AE
encoder-decoder:

```
AA sequence (canonical) →
  DAE.encode → (B, L, d_z) continuous latent →
  FSQ.project_out → (B, L, n_channels_decoder=512) post-FSQ latent →
  DAE.decode → reconstructed 3D coords
```

The **framework arm** trajectory endpoint lives in post-`project_out`
(512-d) continuous space. To convert this back to a reconstructed
3D coords, the framework needs a **bridge**: `post-project_out →
FSQ.implicit_codebook → DAE.decode`.

### 1.2 The 3 attempted bridges (all lossy)

| Wave | Bridge | Result | Reason |
|---|---|---|---|
| **Wave 92c** | L2 nearest-neighbour in 512-d (`argmin(cdist(x_flat_512d, codes_512d_1000))`) | +1.63 Å regression at N=10 (framework_synth) | The 512-d L2 distance picks a codebook entry **distant** from the canonical `DAE.encode→DAE.decode` path because the FSQ `implicit_codebook` is indexed in 4-d space, not 512-d |
| **Wave 95 P3.B** | Trained Linear(512→4) inverse of `project_out` | +2.28 Å at N=10 framework_inv_proj (worse than Wave 92c!) | Bridge is algebraically faithful (per-sample RMSE 3.54e-3 ≪ FSQ half-grid 0.5) BUT the synthetic `x_final = N(0, σ=1e-3)` over 512-d **collapses every record to the same codebook index** — the framework cannot now measure its re-inference value-add with this degenerate endpoint |
| **Wave 95 P3.C RETRY** | (same bridge as P3.B; re-run with bigger N) | Same +2.28 Å (degenerate) | Confirms the bridge is necessary but not sufficient; the **endpoint synthesis** is the blocker |

### 1.3 The Wave 121 NEW bug (framework_inv_proj path)

After Wave 122 P2 wired the Wave 95 P3.B bridge into
`_synthesize_x_final_real`, the framework_inv_proj sweep FAILED at
record 0 with `RuntimeError: mat1 and mat2 shapes cannot be multiplied
(64x512 and 3x256)` at `DAE.encode(self.up)`. The bridge path now
passes the per-call `_validate_state_shape` validator at
`kanzi.py:1073-1085` (Wave 121 Phase 1 fix), but the model's actual
`forward` calls `self._dae.encode(x)` where `x` has shape `(64, 512)`
and the upstream `DAE.up` expects `(3, 256)` raw 3-channel coords.

**The framework_inv_proj path needs an inverse-projection step
BEFORE the solve_ode loop** (post-`project_out` (64, 512) → raw
(3, 256)) that is not yet implemented. The Wave 95 Linear(512→4)
bridge runs AFTER the solve_ode (in the bridge path), not before; the
inv_proj path needs an analogous **pre-loop** bridge.

### 1.4 Cross-references

- `docs/audit/wave92c-n1000-sweep-real.md` §5 (architectural explanation)
- `docs/audit/wave95-phase3-kanzi-inverse-rerun.md` §4 (degenerate endpoint analysis)
- `docs/audit/wave95-phase3-kanzi-inverse-rerun.md` (full RETRY audit)
- `docs/audit/wave99b-n1000-verdict.md` (N=10 Bonferroni p=4.6e-7)
- `docs/audit/wave121-shape-fix-resweep.md` Phase 4 (NEW bug)
- Wave 122 P2: `ae76508` (bridge wired into `_synthesize_x_final_real`)
- Wave 121 Phase 1: `a90485b` (shape validator fix)
- Wave 95 P3.B: `378dc4a` (trained Linear(512→4) inverse; commit SHAs `data/_kanzi_project_out_inv.pt`)

---

## 2. Goal

Three independent fixes that, together, are predicted to close the
+0.86 Å Kanzi framework-arm regression to TIE-or-framework_improves:

1. **Pre-loop inverse-projection bridge** (~30 LOC in
   `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real`): before
   the solve_ode loop, project the post-`project_out` (64, 512)
   trajectory endpoint back to raw 3-channel coords using a trained
   Linear(512→3×256) inverse — analogous to the Wave 95 P3.B
   Linear(512→4) inverse but going all the way to raw coords.
2. **Non-degenerate `x_final` synthesis** (~20 LOC in
   `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real`): replace
   the degenerate `N(0, σ=1e-3)` over 512-d with a **calibrated**
   `x_final` that spans the FSQ vocabulary — e.g. `N(0, σ)` where
   `σ` is chosen so the projected 4-d norm matches the average
   per-record 4-d norm of the training set (predicted σ ≈ 0.3-1.0
   vs current 1e-3 = 100-300× larger).
3. **Verification sweep** at N=1000 framework_inv_proj with the
   fixed bridge + non-degenerate endpoint.

**Target metric improvement:**
- `reconstruction_kabsch_rmsd_A` at N=1000 framework_inv_proj:
  from +1.60 Å regression (Wave 95 historical) → TIE within ±0.05 Å
  of baseline OR framework_improves (-0.05 to -0.20 Å). **Predicted
  outcome is uncertain** because the bridge alone did not close the
  gap in Wave 95 P3.C; the non-degenerate endpoint is the critical
  fix.

---

## 3. Approach

### 3.1 Pre-loop inverse-projection bridge (~30 LOC)

**File:** `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` (~line 358)

**Pseudocode:**

```python
def _synthesize_x_final_real(
    adapter: "KanziAdapter",
    record_idx: int,
    seed: int,
    nfe_budget: int,
) -> np.ndarray:
    """Synthesize the framework trajectory endpoint in raw 3-channel coords.

    Wave 123+ Plan #4 (rank #3) — pre-loop inverse-projection bridge:
    project the post-`project_out` (64, 512) latent back to raw (3, 256)
    coords BEFORE the solve_ode loop, so the model's `DAE.up` receives
    the expected shape. (Wave 121 NEW bug resolution + Wave 95 P3.B analog)
    """
    # Step 1: synthesize post-project_out (64, 512) latent
    # (non-degenerate σ chosen per Step 3.2 below)
    x_final_post = _synthesize_x_final_post_proj(
        adapter=adapter,
        record_idx=record_idx,
        seed=seed,
        sigma=_NON_DEGENERATE_SIGMA,  # 0.3-1.0, not 1e-3
    )  # shape (64, 512)

    # Step 2: pre-loop inverse-projection bridge (NEW)
    # Trained Linear(512 → 3*256) inverse of `project_out → up`.
    # Modeled on Wave 95 P3.B (Linear(512→4)) but going all the way to raw coords.
    inv_proj = _load_kanzi_pre_loop_inv_proj()  # trained offline; cached
    x_final_raw = inv_proj(x_final_post.flatten())  # shape (3*256,)
    x_final_raw = x_final_raw.reshape(3, 256)

    # Step 3: run solve_ode in raw coord space
    bundle = adapter.build_initial_state(
        x_final_raw,  # shape (3, 256) — DAE.up expects this
        nfe_budget=nfe_budget,
    )
    trace = adapter.solve_ode(bundle, cond=None, seed=seed)
    return trace.x_final  # shape (3, 256)
```

### 3.2 Non-degenerate `x_final` synthesis (~20 LOC)

**File:** `tools/_kanzi_sweep_runner.py` (new helper)

**Pseudocode:**

```python
def _compute_non_degenerate_sigma(
    adapter: "KanziAdapter",
    calibration_records: int = 50,
) -> float:
    """Calibrate the post-project_out `x_final` synthesis σ so the
    framework-arm trajectory explores a meaningful neighborhood of
    the FSQ vocabulary. Avoid the Wave 95 P3.C degeneracy where
    σ=1e-3 collapses every record to the same codebook index.

    Approach: compute the average per-record 4-d FSQ latent norm
    across `calibration_records` records from the canonical
    DAE.encode path. Set σ so the projected 4-d norm of the synthetic
    x_final matches this average.
    """
    norms = []
    for record_idx in range(calibration_records):
        coords = load_record_coords(record_idx)
        z_4d = adapter._dae.encode(coords)[..., :4]  # (L, 4) FSQ latent
        norms.append(float(np.linalg.norm(z_4d, axis=-1).mean()))
    avg_norm = float(np.mean(norms))
    # σ such that projected 4-d norm from N(0, σ) over 512-d matches avg_norm
    # Linear(512→4) is approximately orthogonal, so projected norm ≈ σ * sqrt(4)
    sigma = avg_norm / np.sqrt(4)
    return sigma


_NON_DEGENERATE_SIGMA: float | None = None  # lazy-init

def _get_non_degenerate_sigma(adapter: "KanziAdapter") -> float:
    global _NON_DEGENERATE_SIGMA
    if _NON_DEGENERATE_SIGMA is None:
        _NON_DEGENERATE_SIGMA = _compute_non_degenerate_sigma(adapter)
    return _NON_DEGENERATE_SIGMA
```

### 3.3 Trained pre-loop inverse model (~separate training step)

**New artifact:** `data/_kanzi_pre_loop_inv_proj.pt` (Linear(512→3*256)
weights, trained offline via MSE on canonical `DAE.encode→DAE.decode`
pairs).

**Training script:** `tools/train_kanzi_pre_loop_inv_proj.py` (NEW, ~30 LOC)

**Pseudocode:**

```python
"""Train the pre-loop inverse-projection bridge for Kanzi framework_inv_proj.

Per Wave 123+ Plan #4 (rank #3), the framework_inv_proj path needs
a pre-loop inverse projection that maps post-`project_out` (64, 512)
back to raw (3, 256) coords BEFORE the solve_ode loop.

Training data: canonical (post-project_out, raw-coords) pairs from
the Wave 36 DAE ckpt on N=1000 calibration records.

Loss: MSE on the projected raw coords.

Output: `data/_kanzi_pre_loop_inv_proj.pt` (Linear weights).
"""
import torch
from torch import nn

class PreLoopInvProj(nn.Module):
    def __init__(self, in_dim: int = 64 * 512, out_dim: int = 3 * 256):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim)
    def forward(self, x):
        return self.linear(x)

def train(...):
    # 1. Load DAE ckpt
    # 2. For N=1000 calibration records:
    #    a. coords = load_record(idx)
    #    b. z_continuous = DAE.encode(coords)[..., :512]  # post-project_out
    #    c. targets.append(coords.flatten())
    #    d. inputs.append(z_continuous.flatten())
    # 3. Train PreLoopInvProj for 50 epochs with Adam(lr=1e-3)
    # 4. Save to data/_kanzi_pre_loop_inv_proj.pt
```

**Training time:** ~5 minutes on GPU (N=1000 records × 50 epochs).

### 3.4 Test plan

Add 5 unit tests to `tests/test_tools/test_kanzi_sweep_runner.py`:

1. **Test 1 — pre-loop bridge shape**: `_synthesize_x_final_real`
   returns shape `(3, 256)` (raw coords), not `(64, 512)` (post-project_out).
2. **Test 2 — non-degenerate σ**: `_compute_non_degenerate_sigma`
   returns σ ∈ [0.1, 2.0] (the calibrated range), not 1e-3.
3. **Test 3 — codebook coverage**: after `_synthesize_x_final_real`,
   the framework-arm `codebook_utilization` is ≥ 0.3 (not the
   Wave 95 P3.C degenerate 0.049).
4. **Test 4 — bridge fidelity**: the trained pre-loop inv_proj
   produces per-sample RMSE ≤ 0.1 on a held-out validation set
   (canonical path).
5. **Test 5 — DAE.up shape**: the solve_ode loop accepts the
   raw-coords input without the Wave 121 NEW `mat1×mat2` bug.

### 3.5 Verification sweep

After the bridge + non-degenerate endpoint + unit tests pass, run
the full **N=1000 framework_inv_proj** sweep on the kanzi sidecar:

```
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
    --config configs/kanzi_framework_inv_proj.yaml --seed 42 --limit 1000 \
    --output-dir /tmp/w123/
```

**Acceptance:** `reconstruction_kabsch_rmsd_A` framework_inv_proj mean
within ±0.10 Å of baseline_seed42 mean (0.9046 Å) OR framework_improves
by ≥0.05 Å.

**Wall-clock:** ~50 minutes on CPU (1.5 s/rec × 1000 = 25 min for
solve_ode + ~25 min for the bridge + DAE.decode).

---

## 4. Acceptance criteria

- [ ] `data/_kanzi_pre_loop_inv_proj.pt` (NEW artifact; Linear 512→3*256
  weights; MSE ≤ 0.01 on a held-out validation set).
- [ ] `tools/train_kanzi_pre_loop_inv_proj.py` (NEW; training script
  with reproducibility via `--seed 42`).
- [ ] `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` updated
  to use the pre-loop bridge + non-degenerate σ.
- [ ] Wave 121 NEW `mat1×mat2` bug resolved (the solve_ode loop
  accepts the raw-coords input).
- [ ] Unit tests pass (5 new tests; existing tests unchanged).
- [ ] `pytest tests/ -k "d4" -q` → 33/33 PASS (byte-stable preserved).
- [ ] `codebook_utilization` on framework_inv_proj arm ≥ 0.3 (not
  the Wave 95 P3.C degenerate 0.049).
- [ ] `reconstruction_kabsch_rmsd_A` framework_inv_proj mean within
  ±0.10 Å of baseline_seed42 (currently +1.60 Å regression).
- [ ] Determinism assertion: 3 baseline anchors (Wave 88 + Wave 121 + Wave 123)
  within ±0.007 Å mean Δ, ±0.0065 Å std Δ.
- [ ] `mkdocs build --strict` → EXIT=0.
- [ ] Single atomic commit, no push (user-gated).

---

## 5. Risk

| Risk | Severity | Mitigation |
|---|---|---|
| **Bridge training data is canonical-path-only** (the framework arm may produce latents OUT of distribution; the trained bridge may be lossy on OOD inputs) | P1 | Train on a MIX of canonical + framework-arm latents (rejection-sample from the framework arm at σ=0.3, σ=0.5, σ=1.0); if the bridge fails OOD, fall back to the Wave 95 P3.B Linear(512→4) bridge (with non-degenerate σ) |
| **Non-degenerate σ may over-correct** (σ=0.5 may produce framework outputs that are too far from the canonical path; the +0.86 Å regression could reverse sign) | P1 | Smoke test at N=20 before N=1000; if the smoke is outside [-0.5, +1.5] Å range, halve σ and retry |
| **Wave 122 P2 wire may be reverted** (the `_synthesize_x_final_real` function is the merge point; if a future wave reverts Wave 122 P2, this plan's deliverable is invalid) | P1 | Pre-flight check: `git log --oneline -- tools/_kanzi_sweep_runner.py | grep ae76508` confirms Wave 122 P2 is in place; if not, refuse to start |
| **Wave 121 NEW bug has more than one manifestation** (the `mat1×mat2` is one symptom; there may be other shape mismatches in the path that surface only on real data) | P1 | Add try/except + diagnostic logging to the pre-loop bridge; log all intermediate shapes; smoke test on N=20 first |
| **CPU N=1000 wallclock is ~50 min** (the kanzi sidecar is CPU-only per the Wave 36 ckpt constraints; the new bridge adds compute) | P2 | Use `--max-records 100` for the smoke; only run N=1000 if smoke is positive |
| **D.4 byte-stable regression vectors change** (the Kanzi adapter's byte-stability is preserved per Wave 95 P3.B; the pre-loop bridge is a NEW path, not a modification of the canonical path) | P1 | Verify D.4 still 33/33 PASS; the pre-loop bridge is a separate code path that does NOT touch the canonical DAE.encode→DAE.decode flow |

---

## 6. Effort estimate

| Phase | Effort | Wall-clock | GPU hours |
|---|---|---:|---:|
| Trained pre-loop inv_proj model (~30 LOC training script + 5 min GPU training) | 0.25 day | 2 hours | 0.1 |
| Pre-loop bridge wiring (~30 LOC in `_synthesize_x_final_real`) | 0.25 day | 2 hours | 0 |
| Non-degenerate σ calibration (~20 LOC) | 0.15 day | 1 hour | 0 |
| Unit tests (~50 LOC × 5 tests) | 0.25 day | 2 hours | 0 |
| N=20 smoke test (CPU) | 0.1 day | 0.5 hours | 0 |
| N=1000 framework_inv_proj sweep (CPU) | 1.0 day | 8 hours (50 min compute + wait) | 0 |
| Determinism cross-check + paper §7.3 update + commit | 0.25 day | 2 hours | 0 |
| **Total** | **~2.25 days** | **~17.5 hours** | **0.1 GPU-hours** |

**LOC budget:** ~80 LOC code + ~50 LOC tests + ~30 LOC training script
+ ~50 LOC docs = ~210 LOC total.

---

## 7. Follow-up

After this plan ships:

1. Re-run Wave 99.B Kanzi N=10 framework paper-metric to verify the
   Bonferroni verdict evolution (currently `REGRESSES_BY_+0.86_Å`;
   target `TIE` or `framework_improves`).
2. Update `docs/paper-draft.md` §7.3 with the new framework_inv_proj
   numbers (additive only; Wave 95 historical numbers preserved).
3. Update `docs/CONSOLIDATED_RESULTS.md` §15.23 (Wave 123 row).
4. Update `todo/STATUS.md` to mark W2 PARTIALLY CLOSED → CLOSED
   (the magnitude claim is now defensible).
5. Consider extending the same pre-loop bridge pattern to other
   Tier 3 adapters with post-latent bottlenecks (none currently;
   all other adapters operate in raw coord / pixel / token space).

---

## 8. Cross-references

- `docs/audit/wave92c-n1000-sweep-real.md` §5 (Kanzi architectural explanation)
- `docs/audit/wave95-phase3-kanzi-inverse-rerun.md` §4 (degenerate endpoint)
- `docs/audit/wave99b-n1000-verdict.md` (Bonferroni p=4.6e-7)
- `docs/audit/wave121-shape-fix-resweep.md` Phase 4 (NEW bug)
- Wave 122 P2: `ae76508` (bridge wire)
- Wave 121 P1: `a90485b` (shape validator fix)
- Wave 95 P3.B: `378dc4a` (trained Linear(512→4) inverse)
- `todo/algo-improvement-framework-vs-model-metrics-gap.md` (this wave's synthesis; rank #3)
- `todo/planned/w2-kanzi-latent-coord-bridge.md` (Wave 91 plan; this plan extends Wave 91's work)
- `todo/planned/w2b-kanzi-adapter-refactor.md` (Wave 92 plan; this plan builds on Wave 92's adapter constants fix)

---

## 9. Wave 123 close-out (placeholder)

This plan is authored in Wave 123 but NOT executed. Status:
**PLANNED, waiting for user approval**. To execute:

1. Read this plan end-to-end (already done if you're the executor).
2. Read Wave 92c §5 + Wave 95 P3.C + Wave 121 Phase 4 audit docs
   to understand the prior attempts.
3. Pre-flight check: confirm Wave 122 P2 wire (`ae76508`) is in
   place; confirm the Kanzi adapter exposes `_dae.encode` and
   `_dae.up` (needed for the bridge training); confirm the kanzi
   sidecar is available.
4. Train the pre-loop inv_proj model (~5 min GPU).
5. Apply the bridge + non-degenerate σ + unit tests.
6. Run N=20 smoke + N=1000 full sweep.
7. Single atomic commit; do NOT push (user-gated).
8. Author `docs/audit/waveN-phaseM-plan4-kanzi-bridge.md` audit doc.
9. Update `todo/STATUS.md` + `docs/paper-draft.md` §7.3 + `docs/CONSOLIDATED_RESULTS.md` §15.23.
10. Move this plan doc to `todo/completed/adapter-improvement-inv-proj-bridge-lossy-replacement.md`.
