#!/usr/bin/env python3
"""Wave 52 Agent C — LineageFlow baseline #1: plain Euler integration.

The most basic possible baseline: take the real LineageFlow denoiser
+ real ``compute_family_vector_field`` and integrate with
``steps=N`` Euler steps from ``t0`` to ``t1``. No framework scheduler,
no restart-blend, no paper-quantity-aware adaptive control.

This is the *same* path the framework's "baseline arm" runs in
``tools/run_real_ckpt_eval.py`` when ``--force-mode real`` + the
codimension-sheet scheduler is disabled, so a direct composite-vs-
composite comparison is meaningful.

Run with::

    .venvs/lineageflow_venv/bin/python scripts/baselines/run_lineageflow_baseline_euler.py \\
        --nfe-list 10,50,100 --output verification_outputs/lineageflow_baseline_euler_q4_2026.json

The composite (3-term Wave 47) is computed *as a self-comparison*:
starting simplex → endpoint. ``phi1 > 0`` ⇒ Euler concentrates;
``phi2 > 0`` ⇒ Euler sharpens; ``phi3 ≈ +1`` ⇒ Euler produces a lot of
argmax turnover (this is the regime the framework restart-blend is
designed to exploit).
"""
from __future__ import annotations

import argparse
import json
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
            / "lineageflow_baseline_euler_q4_2026.json"
        ),
        help="Where to write the JSON record.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    nfe_list = [int(x) for x in args.nfe_list.split(",") if x.strip()]
    out_path = Path(args.output)

    # --- (1) Load real LineageFlow denoiser (real ESM-2-650M + real ckpt).
    print("[BASELINE 1/3] Plain Euler on real LineageFlow ckpt")
    print("loading ckpt + building model...")
    model, n_params, t_build, t_load, ckpt_keys_matched = load_lineageflow_model()
    print(f"  model: {n_params:,} params, build={t_build:.1f}s, load={t_load:.1f}s")
    print(f"  ckpt keys matched: {ckpt_keys_matched}")
    print(f"  geometry: B={args.batch_size} L={args.seq_len} K={args.aa_vocab}")

    # Upstream integrate_base_flow lives in inference/inference.py.
    from inference.inference import integrate_base_flow  # noqa: E402

    # --- (2) Standard inputs at the requested geometry.
    x_start, pad_mask, gap_mask, alpha_h, t_vec0 = make_inputs(
        batch_size=args.batch_size,
        seq_len=args.seq_len,
        aa_vocab=args.aa_vocab,
        seed=args.seed,
    )
    x_start_np = x_start.detach().cpu().numpy().astype(np.float64)

    # --- (3) Per-NFE Euler run + composite (self: x_start vs x_end).
    cells: list[dict] = []
    for nfe in nfe_list:
        t0 = time.time()
        with torch.no_grad():
            x_end = integrate_base_flow(
                model=model,
                x0=x_start,
                alpha_h=alpha_h,
                t0=args.t0,
                t1=args.t1,
                pad_mask=pad_mask,
                gap_mask=gap_mask,
                family_id=None,
                steps=nfe,
                method="euler",
            )
        elapsed = time.time() - t0
        x_end_np = x_end.detach().cpu().numpy().astype(np.float64)

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
        cells.append(
            {
                "nfe_budget": nfe,
                "method": "euler",
                "elapsed_seconds": round(elapsed, 2),
                "start_entropy": start_H,
                "end_entropy": end_H,
                "entropy_delta": end_H - start_H,
                "argmax_change_rate": argmax_change_rate,
                **comp,
            }
        )
        print(
            f"  NFE={nfe:3d}  time={elapsed:6.2f}s  "
            f"H: {start_H:.4f}->{end_H:.4f}  "
            f"argmax_turnover={argmax_change_rate:.3f}  "
            f"composite={comp['composite']:+.4f}"
        )

    record = {
        "schema": "lineageflow_baseline_report.v1",
        "baseline": "plain_euler",
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
            "note": (
                "Wave 47 composite measures framework-vs-baseline (not "
                "baseline self-quality). Higher framework composite ⇒ "
                "framework improves the flow bundle more than the "
                "baseline it was compared against."
            ),
        },
        "limitations": [
            "Family prior alpha_h is synthetic (Dirichlet concentration 10 "
            "per position) — the real Pfam priors ship as separate JSON "
            "assets not in this repo.",
            "Composite is computed as a self-comparison (starting simplex "
            "→ endpoint) rather than as a delta vs the framework's "
            "endpoint. The framework composite of 0.211 is paired with "
            "this baseline's NFE=10 cell in the audit doc for direct "
            "comparison.",
            "CPU only — no CUDA kernels were exercised.",
        ],
    }

    write_json(out_path, record)
    print(f"wrote: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
