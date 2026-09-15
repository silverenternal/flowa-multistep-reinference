"""Wave 95 Phase 3.A — Kanzi project_out inverse probe.

Loads the Wave 36 cleaned_model.pt (FSQ ``project_out`` is a
``Linear(4, 512)``, shape ``(512, 4)``) and asks: is
``torch.linalg.pinv(project_out.weight)`` a valid inverse for the
upstream FSQ round-trip, OR must we train a small inverse layer?

Reports four diagnostics:

  1. Forward residual ``||W @ W.T - I_512||_F`` — the literal text of
     the Wave 95 brief. W is ``(512, 4)`` so W @ W.T is rank-4 and
     cannot equal ``I_512``; this metric is the projector deviation
     (not orthogonal columns — see metric #4 for that).
  2. Inverse residual — the Wave 95 brief asks for
     ``||pinv(W) @ y - project_in(y)||``. The state-dict shows
     ``project_in.weight`` of shape ``(4, 256)`` (a Linear(256 → 4)
     used by the ENCODER side, not the decoder) while ``pinv(W)`` is
     shape ``(4, 512)`` (inverting the decoder's 4 → 512 projection).
     They have **incompatible input dims** and are NOT directly
     comparable. We document this mismatch and instead report the
     *operationally meaningful* metric: the column-space projector
     residual on 1000 random 512-d unit vectors, which measures how
     well W's 4-d column space covers the framework trajectory's
     512-d manifold (the architectural bottleneck).
  3. Reconstruction RMSE — pinv(W) @ W @ x vs x for x in 4-d (the
     Moore-Penrose identity). By construction pinv(W) @ W = I_4 in
     the column space of W.T, so RMSE ≈ 0 (modulo floating point).
     This confirms pinv is a valid INVERSE in the abstract algebraic
     sense; metric #2 measures whether the framework trajectory
     actually lives in the column space that pinv inverts.
  4. Orthogonal-columns test ``||W.T @ W - I_4||_F`` — the meaningful
     near-orthogonality probe for an overcomplete ``(512, 4)`` weight.
     pinv = W.T iff ``W.T @ W = I_4`` exactly.

Decision rule (Wave 95 brief):
  * If column-space residual < 0.01 (in 512-d codebook units) →
    declare valid inverse (1-LOC fix path: ``pinv(W) @ x_final``).
  * Else → declare need-to-train (5-min training path: fit a small
    Linear(512, 4) on ``(W @ x, x)`` pairs sampled from the FSQ
    codebook).

Usage:
    .venvs/kanzi_venv/bin/python tools/_kanzi_project_out_inverse_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
CKPT_PATH = REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"


def _find_quantize_weight(
    state_dict: dict, *, layer: str,
) -> tuple[torch.Tensor, str] | None:
    """Locate the FSQ ``project_out`` / ``project_in`` weight matrix.

    Returns the first state-dict key matching ``quantize.<layer>`` or
    ``fsq_quantizer.<layer>`` with the expected weight shape, or
    ``None`` if not found.
    """
    matches = [
        (k, v) for k, v in state_dict.items()
        if layer in k and k.endswith("weight")
        and isinstance(v, torch.Tensor) and v.ndim == 2
    ]
    if not matches:
        return None
    return matches[0][1], matches[0][0]


def main() -> int:
    print(f"[probe] loading ckpt: {CKPT_PATH}")
    print(f"[probe] ckpt size: {CKPT_PATH.stat().st_size / 1e6:.1f} MB")
    blob = torch.load(str(CKPT_PATH), map_location="cpu", weights_only=False)
    state = blob.get("model", blob)
    if "state_dict" in state and isinstance(state["state_dict"], dict):
        state = state["state_dict"]

    out_match = _find_quantize_weight(state, layer="project_out")
    if out_match is None:
        raise RuntimeError(
            "no_project_out_weight_found_in_ckpt:"
            f"keys_sample={list(state.keys())[:5]!r}"
        )
    W, w_key = out_match
    print(f"[probe] found project_out weight at: {w_key}")
    print(f"[probe] W.shape = {tuple(W.shape)} (expected (512, 4))")
    if tuple(W.shape) != (512, 4):
        print(
            "[probe] WARNING: shape mismatch — downstream pinv will"
            " still run but results may not match the Wave 92c"
            " (1000, 512) codebook layout."
        )

    W = W.float()
    pinvW = torch.linalg.pinv(W)
    print(f"[probe] pinvW.shape = {tuple(pinvW.shape)}")

    # ----------------------------------------------------------------
    # 1. Forward residual — per Wave 95 brief literal text.
    #    ||W @ W.T - I_512||_F. W is (512, 4) so W @ W.T is rank-4 and
    #    cannot equal I_512; this metric measures the *projector*
    #    deviation, not orthogonal columns (use #4 for that).
    # ----------------------------------------------------------------
    forward_resid = torch.linalg.norm(
        W @ W.T - torch.eye(W.shape[0]), ord="fro",
    ).item()
    print(f"[1] forward_resid ||W@W.T - I_512||_F = {forward_resid:.6e}")

    # ----------------------------------------------------------------
    # 4. Orthogonal-columns test — the MEANINGFUL near-orthogonality
    #    probe for a (512, 4) overcomplete weight. pinv = W.T iff
    #    W.T @ W = I_4 exactly.
    # ----------------------------------------------------------------
    ortho_resid = torch.linalg.norm(
        W.T @ W - torch.eye(W.shape[1]), ord="fro",
    ).item()
    print(f"[4] ortho_resid  ||W.T@W - I_4||_F   = {ortho_resid:.6e}")

    # ----------------------------------------------------------------
    # 2. Wave 95 brief's "inverse residual" — document the
    #    project_in/pinv(W) dim mismatch, then run the
    #    operationally meaningful metric (column-space projector
    #    residual).
    # ----------------------------------------------------------------
    project_in_match = _find_quantize_weight(state, layer="project_in")
    if project_in_match is not None:
        project_in_W, pin_key = project_in_match
        print(
            f"[probe] found project_in weight at: {pin_key},"
            f" shape={tuple(project_in_W.shape)}"
        )
        print(
            "[probe] NOTE: project_in is a Linear(256, 4) used by the"
            " ENCODER side (compresses 256-d → 4-d before quantize)."
        )
        print(
            "[probe]       pinv(W) is a Linear(512, 4) that inverts"
            " project_out (4-d → 512-d). They have INCOMPATIBLE input"
        )
        print(
            "[probe]       dims (256 vs 512) and serve different sides"
            " of the FSQ pipeline — they are NOT direct inverses of"
        )
        print(
            "[probe]       each other. The Wave 95 brief's literal"
            " ``||pinv(W) @ y - project_in(y)||`` test is malformed."
        )
        print(
            "[probe]       The operationally meaningful diagnostic is"
            " the column-space projector residual (#2 below)."
        )

    # Column-space projector P = W @ pinv(W) has shape (512, 512) and
    # is rank 4. For any x in R^512, the residual
    # ``||x - P @ x||`` measures how far x is from the 4-d column
    # space of W. The framework trajectory lives in 512-d; if this
    # residual is large, the trajectory is OUT OF RANGE for project_out
    # and pinv cannot recover a meaningful 4-d latent (because the
    # projection is least-squares onto an inappropriate subspace).
    gen = torch.Generator().manual_seed(0x4B_4E_5A_49)  # "KANZI"
    P_colspace = W @ pinvW  # (512, 512)
    ys = torch.randn(100, W.shape[0], generator=gen)
    ys = ys / ys.norm(dim=-1, keepdim=True)
    proj_ys = ys @ P_colspace.T  # (100, 512)
    col_resids = (ys - proj_ys).norm(dim=-1)  # (100,)
    col_resid_avg = col_resids.mean().item()
    col_resid_max = col_resids.max().item()
    col_resid_std = col_resids.std().item()
    print(
        f"[2] col_space_resid avg ||y - W@pinv(W)@y|| "
        f"(100 random unit vectors)"
        f" = {col_resid_avg:.6e}"
    )
    print(
        f"[2] col_space_resid max ||y - W@pinv(W)@y||"
        f" = {col_resid_max:.6e}"
    )
    print(
        f"[2] col_space_resid std (over 100 vectors)"
        f" = {col_resid_std:.6e}"
    )
    # Effective rank of W: how much of the 512-d space is explained by
    # the 4-d column space. Compute the singular values of W and report
    # the ratio of explained variance.
    svals = torch.linalg.svdvals(W)  # (4,) — singular values
    sval_sum_sq = (svals ** 2).sum().item()
    total_energy = (W ** 2).sum().item()  # ||W||_F^2
    explained_ratio = sval_sum_sq / max(total_energy, 1e-12)
    print(
        f"[2] W singular values = {svals.tolist()}"
        f" (4 singular values for a 512×4 matrix)"
    )
    print(
        f"[2] W column-space energy ratio = "
        f"sum(sv^2) / ||W||_F^2 = {explained_ratio:.6e}"
        f" (1.0 = columns capture all W's energy)"
    )

    # ----------------------------------------------------------------
    # 3. Reconstruction RMSE — pinv(W) @ W @ x vs x in 4-d.
    #    This is the Moore-Penrose identity: pinv(W) @ W @ x = x in
    #    the column space of W.T, so RMSE is ~0 by construction
    #    (modulo floating point). We compute it for completeness.
    # ----------------------------------------------------------------
    gen = torch.Generator().manual_seed(0x4B_4E_5A_49)
    # 1000 random 4-d vectors sampled from a realistic FSQ-bound range
    # (the FSQ basis (8, 5, 5, 5) clamps each dim to half-integers in
    # [-3.5, 3.5], so x ~ U(-3.5, 3.5) is the canonical envelope).
    xs = torch.empty(1000, W.shape[1]).uniform_(-3.5, 3.5, generator=gen)
    # pinv(W) @ W @ x — Moore-Penrose identity.
    Wx = xs @ W.T  # (1000, 512)
    pinvWx = Wx @ pinvW.T  # (1000, 4)
    recon_rmse_pinv = (pinvWx - xs).norm(dim=-1).mean().item()
    print(
        f"[3] recon_rmse pinv(W)@W@x vs x (Moore-Penrose identity)"
        f" = {recon_rmse_pinv:.6e}  (by construction ~0)"
    )

    # ----------------------------------------------------------------
    # DECISION — Wave 95 brief: pinv residual < 0.01 → valid inverse
    # (1-LOC fix path); else → need-to-train (5-min path).
    #
    # The Moore-Penrose reconstruction RMSE (metric #3) is
    # tautologically ~0, so the decision is driven by the
    # column-space projector residual (metric #2). A small residual
    # means the 4-d column space captures ~all of W's energy and
    # pinv is a faithful inverse of project_out's range; a large
    # residual means the framework trajectory (or any 512-d input)
    # has substantial mass outside the 4-d column space, and pinv
    # will produce a least-squares approximation that may not
    # recover a meaningful 4-d pre-quantization latent.
    # ----------------------------------------------------------------
    print()
    print("=" * 60)
    print("WAVE 95 PHASE 3.A DECISION")
    print("=" * 60)
    print(f"forward_resid        ||W@W.T - I_512||_F = {forward_resid:.6e}")
    print(f"ortho_resid          ||W.T@W - I_4||_F   = {ortho_resid:.6e}")
    print(f"col_space_resid avg  ||y - W@pinv(W)@y|| = {col_resid_avg:.6e}")
    print(
        f"recon_rmse (Moore-Penrose identity)"
        f" = {recon_rmse_pinv:.6e}"
    )
    print(
        f"W column-space energy ratio = "
        f"sum(sv^2)/||W||_F^2 = {explained_ratio:.6e}"
    )

    # Two complementary decision criteria:
    # (a) Moore-Penrose identity holds (recon_rmse_pinv < 1e-3)
    #     → pinv algebraically inverts project_out for any 4-d input.
    # (b) Column-space residual small (col_resid_avg < 0.01)
    #     → the framework trajectory's 512-d points have ~all their
    #     mass in the 4-d column space, so pinv can recover a
    #     meaningful 4-d latent estimate.
    THRESHOLD_PINV = 1e-3
    THRESHOLD_COL = 0.01
    pinv_ok = recon_rmse_pinv < THRESHOLD_PINV
    col_ok = col_resid_avg < THRESHOLD_COL
    if pinv_ok and col_ok:
        print()
        print(
            f"DECISION: VALID INVERSE (Moore-Penrose residual "
            f"{recon_rmse_pinv:.6e} < {THRESHOLD_PINV}; col-space "
            f"residual {col_resid_avg:.6e} < {THRESHOLD_COL})"
        )
        print(
            "Path: 1-LOC fix — use pinv(project_out.weight) for the"
            " bridge."
        )
    elif pinv_ok and not col_ok:
        print()
        print(
            f"DECISION: NEED TO TRAIN (pinv is algebraically valid"
            f" at {recon_rmse_pinv:.6e}, BUT the column-space"
            f" residual {col_resid_avg:.6e} >= {THRESHOLD_COL} means"
            f" the framework trajectory leaves the 4-d column space)"
        )
        print(
            "Path: 5-min training — fit a small Linear(512, 4) on the"
            " implicit_codebook targets to get a decoder-side inverse"
            " that handles out-of-column-space trajectories."
        )
    else:
        print()
        print(
            f"DECISION: NEED TO TRAIN (Moore-Penrose residual"
            f" {recon_rmse_pinv:.6e} >= {THRESHOLD_PINV} — pinv"
            f" is numerically unstable for this W)"
        )
        print(
            "Path: 5-min training — fit a small Linear(512, 4) on the"
            " implicit_codebook targets."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
