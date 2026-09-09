# Wave 95 Phase 3.A — Kanzi `project_out` inverse probe

**Date:** 2026-09-10
**Agent:** Wave 95 Phase 3.A
**Status:** Probe complete; decision documented.

## TL;DR

`torch.linalg.pinv(project_out.weight)` is **algebraically a valid
inverse** of the FSQ `project_out` Linear (Moore-Penrose identity
holds with RMSE 1.58e-6, far below the 0.01 threshold). The 1-LOC fix
path (just use `pinv(W)` in the bridge) is correct from a
linear-algebra standpoint.

However, the brief's literal `||pinv(W) @ y - project_in(y)||` test is
**malformed** — `project_in.weight` is `(4, 256)` (encoder-side
Linear(256→4)) while `pinv(W)` is `(4, 512)` (decoder-side inversion
of 4→512). They have incompatible input dims (256 vs 512) and serve
different sides of the FSQ pipeline; they are NOT direct inverses of
each other. The Wave 92c root-cause note (that `project_in` and
`project_out` are independent learned mappings — not inverses)
extends to `pinv(W)`: pinv is the *algebraic* inverse of `project_out`
but that does not make it equivalent to `project_in`, because
`project_in` is a different linear map (256→4) from a different
training objective.

The bridge's +1.63 Å regression comes from the FSQ's 4-d bottleneck
lossy round-trip (256→4→quantize→4→512) — replacing the existing
NN-based bridge with a `pinv(W)`-based bridge would not close this gap
because the gap is in the *forward* direction (project_out is lossy),
not the *inverse* direction. The next-step recommendation is a small
empirical bridge comparison rather than a blind 1-LOC swap.

## Probe results

Wave 36 ckpt `data/kanzi_ckpt/cleaned_model.pt`
(SHA-256: `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270`,
529.6 MB) loaded successfully via
`torch.load(ckpt_path, map_location="cpu", weights_only=False)` —
matches the Wave 92a pattern.

Located weights (mirroring Wave 92a's `quantize.*` namespace):

| weight | shape | role |
| --- | --- | --- |
| `quantize.project_out.weight` | `(512, 4)` | decoder projection 4-d → 512-d (the W under test) |
| `quantize.project_in.weight`  | `(4, 256)` | encoder projection 256-d → 4-d |

Singular values of W: `[7.446, 6.112, 6.035, 5.819]`.
Max/min ratio = 1.28 — W is well-conditioned; numerical pinv is
stable. Column-space energy ratio
`sum(sv^2) / ||W||_F^2 = 1.0` (W has rank 4 and captures all its own
energy — expected for a 512×4 matrix).

### Metric 1: Forward residual `||W @ W.T - I_512||_F`

```
forward_resid = 8.443119e+01
```

W is `(512, 4)`, so `W @ W.T` is rank-4 and cannot equal `I_512`. The
metric measures the deviation of the rank-4 projector from the
512-d identity. Per closed-form:
`||W @ W.T - I_512||_F^2 = sum(sv(W)^4) - 2*sum(sv(W)^2) + 512 ≈ 7135`,
giving `84.47` — matches the probe's `84.43` to within float tolerance.

**Interpretation:** not meaningful for orthogonality testing on an
overcomplete W; use metric #4.

### Metric 4: Orthogonal columns test `||W.T @ W - I_4||_F`

```
ortho_resid = 8.136737e+01
```

W's columns are far from orthogonal — `W.T @ W` deviates from `I_4`
by `81.37` Frobenius. This is expected for a learned linear (Kanzi's
FSQ was not trained with an orthogonality regularizer). It does NOT
mean pinv fails — pinv is computed via SVD and is numerically stable
for any well-conditioned W (which W is, per singular-value ratio
1.28).

**Interpretation:** W is not orthogonal, but pinv still inverts W
correctly in the Moore-Penrose sense.

### Metric 2: Wave 95 brief's literal "inverse residual"

The brief asks for
`||pinv(W) @ x - project_in(x)||_F` averaged over 100 random unit
vectors. **This test is malformed**:

* `project_in.weight` is `(4, 256)`. `project_in(x)` is only defined
  for `x ∈ R^256`.
* `pinv(W)` is `(4, 512)`. `pinv(W) @ y` is only defined for
  `y ∈ R^512`.

Even ignoring the dim mismatch, the two operations serve different
sides of the FSQ pipeline:

```
encoder (256-d) → project_in (256→4) → quantize → project_out (4→512) → decoder (512-d)
                 ^^^^^^^^^^^^^^^^^^^^^                            ^^^^^^^^^^^^^^^^^^^^^
                 ENCODER side                                     DECODER side
```

`project_in` compresses encoder features into the 4-d FSQ basis;
`project_out` expands quantized 4-d codes into decoder features. They
are *not* inverses of each other (the Wave 92c root-cause explicitly
notes this — `project_in` and `project_out` are independent learned
mappings from different training objectives).

**Resolution:** we report the column-space projector residual as the
operationally meaningful diagnostic:

```
col_space_resid  ||y - W @ pinv(W) @ y||   (avg, 100 unit vectors) = 9.96e-01
col_space_resid  ||y - W @ pinv(W) @ y||   (max, 100 unit vectors) = 1.00e+00
col_space_resid  ||y - W @ pinv(W) @ y||   (std, 100 unit vectors) = 2.57e-03
```

This number is **~0.99 for any 4-d column space in 512-d** — it is a
geometric tautology. A random unit vector in R^512 makes a near-90°
angle with any 4-d subspace, so the projection residual is ~1.0
regardless of W's structure. This metric does NOT indicate whether the
framework trajectory leaves the column space — random unit vectors
are not representative of the framework's continuous-latent
manifold.

The correct diagnostic would be `col_space_resid` on actual
framework trajectory points (`x_final` from the Wave 92c N=1000
sweep). That comparison is out of scope for this probe (requires
GPU integration to reproduce the framework trajectory).

### Metric 3: Reconstruction RMSE (Moore-Penrose identity)

```
recon_rmse pinv(W) @ W @ x vs x (1000 random samples, x ~ U(-3.5, 3.5)^4) = 1.576e-06
```

By the Moore-Penrose construction,
`pinv(W) @ W @ x = x` for any `x ∈ R^4` (modulo floating-point
epsilon). The probe confirms this with RMSE = 1.58e-6 — well below
the brief's 0.01 threshold.

**Interpretation:** pinv(W) is a **faithful algebraic inverse** of
project_out's column space. For any 4-d input in `R^4`,
`pinv(W) @ (W @ x) = x` to floating-point precision.

## Decision tree (per brief)

| Threshold | pinv metric | col-space metric | Decision | Path |
| --- | --- | --- | --- | --- |
| `recon_rmse_pinv < 1e-3` AND `col_resid_avg < 0.01` | ✓ (1.58e-6) | ✗ (0.996) | Conditional | 5-min training |
| `recon_rmse_pinv < 1e-3` only | ✓ | — | Algebraically valid | 1-LOC fix |

The probe declares **NEED TO TRAIN** per the probe's literal decision
logic (col-space residual on random vectors exceeds the 0.01
threshold). However, the col-space residual on random unit vectors is
**not the meaningful diagnostic** — it's a geometric tautology for
any overcomplete W. The Moore-Penrose reconstruction RMSE of 1.58e-6
is the correct algebraic metric, and it declares **VALID INVERSE**.

**Reconciling:** the probe's automated decision rule flagged
NEED-TO-TRAIN based on the malformed col-space threshold. The
algebraically meaningful metric (metric #3, Moore-Penrose identity)
holds with 6-orders-of-magnitude headroom, declaring VALID INVERSE.

## Why a 1-LOC fix is risky despite algebraic validity

Even though `pinv(W)` is an algebraic inverse of `project_out`, the
bridge use case has a **separate, larger architectural cost** that
pinv cannot close:

The Wave 92c §5 root-cause analysis (§5, page 99-137) states:

> the FSQ's `project_in` (Linear(256→4)) and `project_out`
> (Linear(4→512)) are independent learned mappings — they are not
> inverses of each other.

The +1.63 Å regression comes from the **forward** direction
(`project_out`'s 4-d bottleneck is lossy), not from the **inverse**
direction (which the existing NN-based bridge does not need — NN
against the (1000, 512) `implicit_codebook` does not invert
project_out at all).

Replacing NN with a `pinv(W) → quantize → implicit_codebook → decoder`
pipeline would NOT close the +1.63 Å gap because:

1. `pinv(W) @ x_final` gives the least-squares 4-d approximation
   when `x_final` is not in `project_out`'s column space. The
   framework trajectory lives in 512-d (post-project_out space) but
   may leave the column space under framework perturbation (this is
   the whole point of the re-inference value-add).
2. Even if `x_final` IS in the column space, the resulting 4-d
   latent must be quantized to a codebook entry, then re-projected
   to 512-d via `project_out` to get a coherent decoder input. The
   quantization step introduces round-trip loss identical to the
   existing NN path.
3. The NN path already gets the exact same quantization loss
   (both paths end at a codebook index). The only difference is
   *how* the index is selected: NN against the 1000-entry
   codebook vs. round-trip through `pinv → quantize → project_out`.

## Recommended next-step path (Agent B handoff)

Given the probe results, the path forward is **not a blind 1-LOC fix**
and **not a blind 5-min training**. Instead:

1. **Empirical bridge comparison** (small, GPU-fast): run the
   existing framework integration on ~100 trajectories, decode each
   via both bridges (NN vs `pinv → quantize → decode`), measure
   kabsch-RMSD per arm. This is a 5-10 min GPU job.
2. If `pinv` matches or beats NN → adopt the 1-LOC fix.
3. If `pinv` is worse → the +1.63 Å is intrinsic to the FSQ
   forward bottleneck; pinv-based bridge cannot close it; either
   accept the gap or train a richer decoder-side inverse (full
   5-min training path: Linear(512, 4) on `(implicit_codebook[i],
   4-d-codes-for-i)` pairs, 200 samples, MSE loss, ~5 min on CPU).

## Output

* **New probe script:** `tools/_kanzi_project_out_inverse_probe.py`
  (152 LOC including comments). Self-contained, ~5s runtime, no GPU.
* **This audit doc:** `docs/audit/wave95-phase3-pin-probe.md`.
* **No code changes to `tools/kanzi_latent_to_coord.py`** — Agent B
  owns that file.

## Reproduction

```bash
.venvs/kanzi_venv/bin/python tools/_kanzi_project_out_inverse_probe.py
```

Runtime: ~10 s end-to-end (mostly the 530 MB ckpt load).

## Co-author

Co-Authored-By: Claude Code <noreply@anthropic.com>
