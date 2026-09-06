#!/usr/bin/env python3
"""Wave 52 Agent C — LineageFlow baseline #3: Heun's method (improved Euler / RK2).

Heun's method is the 2nd-order explicit integrator that uses a
predictor-corrector pair: predict x_{n+1} via Euler, evaluate the
vector field at the predicted point, then correct using the average
of the two slopes. Local truncation error O(h^3), which sits between
Euler (O(h^2)) and RK4 (O(h^5)).

At the same NFE as Euler, Heun produces a noticeably sharper endpoint
concentration (lower entropy, higher max prob). It is also the basis
of the popular ``diffusers.DPMSolver`` Heun variant and is the default
in many diffusion-model samplers.

Run with::

    .venvs/lineageflow_venv/bin/python scripts/baselines/run_lineageflow_baseline_heun.py \\
        --nfe-list 10,50 --output verification_outputs/lineageflow_baseline_heun_q4_2026.json

Makes 2 network calls per step (predict + correct).
"""
from __future__ import annotations

import argparse
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lineageflow_helpers import (  # noqa: E402
    DEFAULT_AA_VOCAB,
    DEFAULT_BATCH_SIZE,
    DEFAULT_NFE_LIST,
    DEFAULT_SEQ_LEN,
    DEFAULT_SEED,
    DEFAULT_T0,
    DEFAULT_T1,
    LINEAGEFLOW_VOCAB_SIZE,
    compute_composite,
    load_lineageflow_model,
    make_inputs,
    per_position_entropy,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--nfe-list", type=str, default=",".join(str(n) for n in DEFAULT_NFE_LIST),
        help="Comma-separated NFE budgets (default: 10,50).",
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--seq-len", type=int, default=DEFAULT_SEQ_LEN)
    p.add_argument("--aa-vocab", type=int, default=DEFAULT_AA_VOCAB)
    p.add_argument("--t0", type=float, default=DEFAULT_T0)
    p.add_argument("--t1", type=float, default=DEFAULT_T1)
    p.add_argument(
        "--output", type=str,
        default=str(
            REPO_ROOT / "verification_outputs"
            / "lineageflow_baseline_heun_q4_2026.json"
        ),
    )
    return p.parse_args()


def heun_step(
    *,
    model: torch.nn.Module,
    x: torch.Tensor,
    alpha_h: torch.Tensor,
    t: float,
    dt: float,
    pad_mask: torch.Tensor,
    gap_mask: torch.Tensor,
) -> torch.Tensor:
    """One Heun (RK2) step using the real upstream vector field."""
    from inference.inference import compute_family_vector_field  # noqa: WPS433
    device = x.device
    dtype = x.dtype
    B = x.size(0)
    t0_vec = torch.full((B,), t, device=device, dtype=dtype)
    t1_vec = torch.full((B,), t + dt, device=device, dtype=dtype)

    with torch.no_grad():
        # Predictor: Euler step from current slope.
        logits0 = model(
            x_simplex=x, t=t0_vec,
            pad_mask=pad_mask, gap_flag=gap_mask, family_id=None,
        )
        v0 = compute_family_vector_field(
            x, t0_vec, logits0, alpha_h,
            pad_mask=pad_mask, gap_mask=gap_mask,
        )
        x_pred = x + dt * v0

        # Corrector: re-evaluate slope at the predicted point.
        logits1 = model(
            x_simplex=x_pred, t=t1_vec,
            pad_mask=pad_mask, gap_flag=gap_mask, family_id=None,
        )
        v1 = compute_family_vector_field(
            x_pred, t1_vec, logits1, alpha_h,
            pad_mask=pad_mask, gap_mask=gap_mask,
        )

        # Heun: average the two slopes.
        x_new = x + 0.5 * dt * (v0 + v1)

    # Renormalise to the simplex (mirrors upstream Euler loop).
    eps = 1e-6
    K = x_new.size(-1)
    uniform = torch.full_like(x_new, 1.0 / K)
    x_new = torch.where(gap_mask[:, :, None], uniform, x_new)
    x_new = torch.where(pad_mask[:, :, None], x_new, uniform)
    sums = x_new.sum(dim=-1, keepdim=True).clamp(min=1e-12)
    return x_new / sums


def main() -> int:
    args = parse_args()
    nfe_list = [int(x) for x in args.nfe_list.split(",") if x.strip()]
    out_path = Path(args.output)

    print("[BASELINE 3/3] Heun (RK2) on real LineageFlow ckpt")
    print("loading ckpt + building model...")
    model, n_params, t_build, t_load, ckpt_keys_matched = load_lineageflow_model()
    print(f"  model: {n_params:,} params, build={t_build:.1f}s, load={t_load:.1f}s")
    print(f"  ckpt keys matched: {ckpt_keys_matched}")
    print(f"  geometry: B={args.batch_size} L={args.seq_len} K={args.aa_vocab}")

    x_start, pad_mask, gap_mask, alpha_h, _ = make_inputs(
        batch_size=args.batch_size,
        seq_len=args.seq_len,
        aa_vocab=args.aa_vocab,
        seed=args.seed,
    )
    x_start_np = x_start.detach().cpu().numpy().astype(np.float64)

    cells: list[dict] = []
    for nfe in nfe_list:
        dt = (args.t1 - args.t0) / float(nfe)
        x = x_start.clone()
        t0 = time.time()
        for s in range(nfe):
            t = args.t0 + s * dt
            x = heun_step(
                model=model, x=x, alpha_h=alpha_h,
                t=float(t), dt=float(dt),
                pad_mask=pad_mask, gap_mask=gap_mask,
            )
        elapsed = time.time() - t0
        x_end_np = x.detach().cpu().numpy().astype(np.float64)

        comp = compute_composite(
            theta_b=x_start_np, theta_f=x_end_np, K=LINEAGEFLOW_VOCAB_SIZE,
        )
        start_H = per_position_entropy(x_start_np)
        end_H = per_position_entropy(x_end_np)
        argmax_change_rate = float(
            np.mean(
                np.argmax(x_start_np, axis=-1) != np.argmax(x_end_np, axis=-1)
            )
        )
        # Heun makes 2 network calls per step
        network_calls = 2 * nfe
        cells.append(
            {
                "nfe_budget": nfe,
                "method": "heun_rk2",
                "network_calls": network_calls,
                "elapsed_seconds": round(elapsed, 2),
                "start_entropy": start_H,
                "end_entropy": end_H,
                "entropy_delta": end_H - start_H,
                "argmax_change_rate": argmax_change_rate,
                **comp,
            }
        )
        print(
            f"  NFE={nfe:3d}  calls={network_calls:4d}  "
            f"time={elapsed:6.2f}s  "
            f"H: {start_H:.4f}->{end_H:.4f}  "
            f"argmax_turnover={argmax_change_rate:.3f}  "
            f"composite={comp['composite']:+.4f}"
        )

    record = {
        "schema": "lineageflow_baseline_report.v1",
        "baseline": "heun_rk2",
        "wave": 52,
        "agent": "C",
        "task": "lineageflow_tier3_baseline_comparison",
        "date": "2026-09-07",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "numpy_version": np.__version__,
            "device_used": "cpu",
            "venv": ".venvs/lineageflow_venv",
        },
        "model": {
            "class": "models.model.LineageFlowClassifier",
            "param_count": int(n_params),
            "ckpt_path": "data/lineageflow/lineageflow-rp55.ckpt",
            "ckpt_keys_matched": int(ckpt_keys_matched),
            "build_seconds": round(t_build, 2),
            "load_seconds": round(t_load, 2),
        },
        "geometry": {
            "batch_size": args.batch_size,
            "seq_len": args.seq_len,
            "aa_vocab": args.aa_vocab,
            "seed": args.seed,
            "t0": args.t0,
            "t1": args.t1,
        },
        "cells": cells,
        "framework_baseline_for_reference": {
            "source": "docs/audit/wave47-eval-pipeline-integration.md §3",
            "framework_composite_at_nfe10": 0.2109374578356829,
            "framework_phi1_at_nfe10": -7.239533882442666e-15,
            "framework_phi2_at_nfe10": -1.2046946911769359e-07,
            "framework_phi3_at_nfe10": 0.84375,
            "framework_composite_weights": [0.40, 0.35, 0.25],
            "framework_K": 33,
            "nfe": 10,
        },
        "limitations": [
            "Family prior alpha_h is synthetic (Dirichlet concentration 10 "
            "per position).",
            "Composite is a self-comparison (starting simplex → endpoint).",
            "Heun is implemented inline (the upstream tree has no Heun "
            "helper). Calls the real denoiser 2× per step.",
            "CPU only.",
        ],
    }
    write_json(out_path, record)
    print(f"wrote: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())