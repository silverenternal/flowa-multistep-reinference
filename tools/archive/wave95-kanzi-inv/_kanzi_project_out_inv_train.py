"""Wave 95 Phase 3.B — train a small Linear(512 → 4) inverse of Kanzi's FSQ
``project_out`` and save it as ``tools/_kanzi_project_out_inv.pt``.

Probe result (Wave 95 Phase 3.A, ``docs/audit/wave95-phase3-pin-probe.md``):

  * Moore-Penrose identity: ``recon_rmse = 1.58e-6`` (PASS, well below 1e-3).
  * Column-space residual on random 512-d vectors: ``0.996`` (FAIL > 0.01).
  * Literal decision rule: **NEED TO TRAIN** — col-space residual on
    random vectors is a geometric tautology (~1.0 for any overcomplete
    W), but the threshold-based rule fires unconditionally and selects
    the training path.

This script implements Path B (5-min training):

  1. Load the Wave 36 cleaned_model.pt (530 MB) and extract
     ``quantize.project_out.weight`` (shape ``(512, 4)``) + bias
     (shape ``(512,)``).
  2. Instantiate a matching FSQ(levels=[8,5,5,5], dim=256, dim_out=512)
     so we can call ``fsq.indices_to_codes(arange(1000), project_out=...)``
     to build the 1000 (input_512, target_4) pairs from the actual
     learned codebook geometry.
  3. Load the *real* ``project_out.weight`` into the FSQ instance so the
     generated codebook matches the production pipeline exactly.
  4. Train ``Linear(512, 4)`` for 100 Adam(lr=1e-3) steps with MSE loss
     on these 1000 pairs. This is a deterministic closed-form solve for
     a single Linear layer on 1000 samples — 100 steps is plenty.
  5. Save the trained Linear's state_dict + a sidecar metadata dict
     (``codebook_size=1000``, ``levels=[8,5,5,5]``, ``input_dim=512``,
     ``output_dim=4``, ``final_mse``, ``n_steps``) under
     ``tools/_kanzi_project_out_inv.pt``.

Usage::

    .venvs/kanzi_venv/bin/python tools/_kanzi_project_out_inv_train.py

The training is intentionally short (≤30s on CPU) and fully
deterministic (fixed seed). The output ``_kanzi_project_out_inv.pt`` is
~8 KB (4*512 + 4 floats for the Linear weights + small metadata dict)
and is committed to the repo so the bridge at
``tools/kanzi_latent_to_coord.py`` can load it without re-training.

Reproduction: ``python tools/_kanzi_project_out_inv_train.py`` yields
the same ``tools/_kanzi_project_out_inv.pt`` byte-for-byte on every run.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parent.parent
CKPT_PATH = REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"
OUT_PATH = REPO_ROOT / "tools" / "_kanzi_project_out_inv.pt"

# FSQ basis matches the Wave 36 ckpt:
# * levels = [8, 5, 5, 5] → codebook_size = 1000
# * dim = 256 (encoder input)  → project_in Linear(256 → 4)
# * dim_out = 512 (decoder output) → project_out Linear(4 → 512)
LEVELS = (8, 5, 5, 5)
DIM = 256
DIM_OUT = 512
CODEBOOK_SIZE = 1000
N_STEPS = 100
LR = 1e-3
SEED = 0x4B_4E_5A_49  # "KANZI" — same probe seed for reproducibility


def _build_codebook_pairs() -> tuple[torch.Tensor, torch.Tensor]:
    """Return (inputs, targets) where:

      * inputs  : (1000, 512) post-project_out codes from
                  ``fsq.indices_to_codes(arange(1000), project_out=True)``.
      * targets : (1000, 4) 4-d pre-project_out codes from
                  ``fsq.indices_to_codes(arange(1000), project_out=False)``.

    Loaded FSQ uses the real ``project_out`` weights from the Wave 36
    cleaned_model.pt so the produced pairs match the production pipeline
    bit-for-bit.
    """
    # Import locally so this script can run from any CWD.
    sys.path.insert(0, str(REPO_ROOT / "data" / "kanzi_upstream" / "src"))
    from kanzi.fsq import FSQ  # noqa: WPS433 — local import by design

    fsq = FSQ(levels=list(LEVELS), dim=DIM, dim_out=DIM_OUT)

    # Load the real project_out weights from the Wave 36 ckpt.
    blob = torch.load(str(CKPT_PATH), map_location="cpu", weights_only=False)
    state = blob.get("model", blob)
    if "state_dict" in state and isinstance(state["state_dict"], dict):
        state = state["state_dict"]
    fsq.project_out.weight.data = state["quantize.project_out.weight"].float()
    fsq.project_out.bias.data = state["quantize.project_out.bias"].float()

    indices = torch.arange(CODEBOOK_SIZE)
    with torch.no_grad():
        # inputs (1000, 512) — post-project_out
        inputs = fsq.indices_to_codes(indices, project_out=True).float()
        # targets (1000, 4) — pre-project_out (4-d basis codes)
        targets = fsq.indices_to_codes(indices, project_out=False).float()

    assert inputs.shape == (CODEBOOK_SIZE, DIM_OUT), (
        f"expected inputs ({CODEBOOK_SIZE}, {DIM_OUT}); got {tuple(inputs.shape)}"
    )
    assert targets.shape == (CODEBOOK_SIZE, len(LEVELS)), (
        f"expected targets ({CODEBOOK_SIZE}, {len(LEVELS)}); got {tuple(targets.shape)}"
    )
    return inputs, targets


def _train_inverse(
    inputs: torch.Tensor, targets: torch.Tensor,
) -> tuple[nn.Linear, float]:
    """Train a ``Linear(input_dim=512, output_dim=4)`` to map
    ``inputs → targets`` with Adam + MSE for 100 deterministic steps.

    Returns the trained Linear and the final-step MSE loss.
    """
    torch.manual_seed(SEED)
    inv = nn.Linear(DIM_OUT, len(LEVELS), bias=True)
    opt = torch.optim.Adam(inv.parameters(), lr=LR)

    inputs = inputs.detach()
    targets = targets.detach()
    final_loss = float("nan")
    for _step in range(N_STEPS):
        opt.zero_grad()
        pred = inv(inputs)
        loss = nn.functional.mse_loss(pred, targets)
        loss.backward()
        opt.step()
        final_loss = float(loss.detach().item())
    return inv, final_loss


def main() -> int:
    print(f"[train] ckpt: {CKPT_PATH}")
    print(f"[train] ckpt size: {CKPT_PATH.stat().st_size / 1e6:.1f} MB")
    t0 = time.time()
    inputs, targets = _build_codebook_pairs()
    print(
        f"[train] built codebook pairs in {time.time() - t0:.2f}s —"
        f" inputs {tuple(inputs.shape)}, targets {tuple(targets.shape)}"
    )

    t0 = time.time()
    inv, final_mse = _train_inverse(inputs, targets)
    print(f"[train] trained Linear(512, 4) in {time.time() - t0:.2f}s")
    print(f"[train] final MSE = {final_mse:.6e}")

    # Sanity check: at the training points the inverse should be near-
    # perfect (residual ≈ final_mse^0.5 per-dim).
    with torch.no_grad():
        pred = inv(inputs)
        per_sample_rmse = (pred - targets).norm(dim=-1).mean().item()
    print(f"[train] per-sample RMSE on training set: {per_sample_rmse:.6e}")

    payload = {
        # nn.Linear state_dict — keys: weight (4, 512), bias (4).
        "state_dict": inv.state_dict(),
        "input_dim": DIM_OUT,
        "output_dim": len(LEVELS),
        "codebook_size": CODEBOOK_SIZE,
        "levels": list(LEVELS),
        "dim": DIM,
        "dim_out": DIM_OUT,
        "n_steps": N_STEPS,
        "lr": LR,
        "seed": SEED,
        "final_mse": final_mse,
        "per_sample_rmse": per_sample_rmse,
        "schema_version": "kanzi-project-out-inv.v1",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, OUT_PATH)
    print(f"[train] saved → {OUT_PATH}")
    print(f"[train] output file size: {OUT_PATH.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
