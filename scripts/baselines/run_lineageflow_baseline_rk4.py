#!/usr/bin/env python3
"""Wave 52 Agent C — LineageFlow baseline #2: classic Runge-Kutta 4.

Same setup as the plain-Euler baseline, but with a fixed-step
Runge-Kutta 4 integrator instead of Euler. RK4 has local error
O(h^5) vs Euler's O(h^2), so at the same NFE it produces a sharper
endpoint concentration (higher phi1, phi2).

Run with::

    .venvs/lineageflow_venv/bin/python scripts/baselines/run_lineageflow_baseline_rk4.py \\
        --nfe-list 10,50 --output verification_outputs/lineageflow_baseline_rk4_q4_2026.json

The RK4 loop calls the real LineageFlow denoiser 4 times per step
(4 network forward passes per integration step vs Euler's 1), so it
is ~4× the wallclock of the Euler baseline at the same NFE — but the
endpoint should be measurably closer to the analytic flow at low NFE.
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
    DEFAULT_SEED,
    DEFAULT_SEQ_LEN,
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
            / "lineageflow_baseline_rk4_q4_2026.json"
        ),
    )
    return p.parse_args()


def rk4_step(
    *,
    model: torch.nn.Module,
    x: torch.Tensor,
    alpha_h: torch.Tensor,
    t: float,
    dt: float,
    pad_mask: torch.Tensor,
    gap_mask: torch.Tensor,
) -> torch.Tensor:
    """One fixed-step RK4 update using the real upstream vector field.

    Returns the new simplex state at ``t + dt``. Mirrors the Euler step
    inside ``inference.inference.integrate_base_flow`` but with 4
    network evaluations per step instead of 1.

    The vector field is computed inside the loop (not via
    ``compute_family_vector_field``) because RK4 needs intermediate
    slopes evaluated at the half-step / full-step perturbations, not
    the same slope evaluated 4 times.
    """
    device = x.device
    dtype = x.dtype
    B = x.size(0)
    t0_vec = torch.full((B,), t, device=device, dtype=dtype)
    t_half_vec = torch.full((B,), t + 0.5 * dt, device=device, dtype=dtype)
    t1_vec = torch.full((B,), t + dt, device=device, dtype=dtype)

    def v(state, t_vec):
        from inference.inference import compute_family_vector_field  # noqa: WPS433
        with torch.no_grad():
            logits = model(
                x_simplex=state, t=t_vec,
                pad_mask=pad_mask, gap_flag=gap_mask, family_id=None,
            )
            return compute_family_vector_field(
                state, t_vec, logits, alpha_h,
                pad_mask=pad_mask, gap_mask=gap_mask,
            )

    k1 = v(x, t0_vec)
    k2 = v(x + 0.5 * dt * k1, t_half_vec)
    k3 = v(x + 0.5 * dt * k2, t_half_vec)
    k4 = v(x + dt * k3, t1_vec)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def main() -> int:
    args = parse_args()
    nfe_list = [int(x) for x in args.nfe_list.split(",") if x.strip()]
    out_path = Path(args.output)

    print("[BASELINE 2/3] Classic RK4 on real LineageFlow ckpt")
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
            x = rk4_step(
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
        # RK4 makes 4 network calls per step
        network_calls = 4 * nfe
        cells.append(
            {
                "nfe_budget": nfe,
                "method": "rk4",
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
        "baseline": "rk4_fixed_step",
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
            "RK4 is implemented inline (the upstream tree has no RK4 "
            "helper). Calls the real denoiser 4× per step; arithmetic "
            "verified against a hand-rolled dy/dt = sin(t) sanity test.",
            "CPU only.",
        ],
    }
    write_json(out_path, record)
    print(f"wrote: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
