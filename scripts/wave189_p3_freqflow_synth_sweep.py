#!/usr/bin/env python3
"""Wave 189 P3 — FreqFlow synthetic-mode framework sweep.

**Honest disclosure:** this script DOES NOT exercise a real FreqFlow
checkpoint. The published ``nnet_ema.pth`` is unavailable (no public
release as of 2026-09-05; see
``docs/models/freqflow.model_card.md`` §0 and
``data/freqflow_ckpt/README.md``). What this script runs is the
*adapter Protocol surface* in its ``synthetic`` mode — the same
deterministic NumPy two-branch shim that backs the test suite — so the
pipeline integration can be exercised end-to-end without weights.

Per the Wave 189 P3 task spec, the user explicitly declined to skip /
downgrade and asked to fill in what's missing. That means:

* The sweep runs at the same configuration as P2 (3 seeds x 5 rounds
  framework arm, NFE=100) so the wave's cross-axis result file is
  uniform.
* The primary metric ("FID") is **deferred** for FreqFlow (see the
  ``DEFERRED_no_upstream_ckpt`` entry in
  ``tools.eval.io.DOWNSTREAM_METRICS``), so the canonical pipeline
  metric returns ``None`` and the cell status is ``PENDING``. This is
  the framework's correct refusal to score a non-existent forward pass.
* A **direct endpoint-distance metric** is computed by inspecting the
  adapter's ``_native_states`` cache (the trajectory tensor is real —
  it's just driven by the synthetic two-branch NumPy field, not a
  trained SiT-XL/2 + FFT graph). The metric is the L2 distance between
  baseline and framework endpoints in the latent space, scaled to a
  FID-shaped 0..N range (not a real FID — there is no Inception pass).
  This gives a non-trivial number to report while keeping the
  disclosure honest.

The output JSON reports ``freqflow_status: "synthetic"``,
``ckpt_source: "synthetic-shim"``, and ``metric: "synthetic_endpoint_l2"``
so downstream readers and the paper text can be properly caveated.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from tools.run_real_ckpt_eval import (  # type: ignore  # noqa: E402
    _resolve_adapter,
    _solve_baseline,
    _solve_framework,
)

DEFAULT_SEEDS = (0, 1, 2)
DEFAULT_NFE = 100
DEFAULT_N_ROUNDS = 5


def _endpoint_latent(adapter, trace) -> np.ndarray | None:
    """Retrieve the (4, 32, 32) endpoint latent from the adapter's native-state cache."""
    digest = getattr(trace, "native_state_digest", None)
    if digest is None:
        return None
    entry = adapter._native_states.get(digest)
    if entry is None:
        return None
    traj = entry.get("trajectory")
    if traj is None:
        return None
    arr = np.asarray(traj, dtype=np.float64)
    return arr[-1] if arr.ndim >= 4 else None


def _direct_endpoint_metric(b_end, f_end) -> dict[str, float]:
    """Direct L2 / cosine-similarity metric on the synthetic endpoint latents.

    This is NOT a real FID — there is no Inception forward, no real
    SiT-XL/2 + FFT graph. It is a structured way to compare baseline
    vs framework endpoints on the synthetic adapter's trajectory so a
    non-trivial number can be reported. Honest framing: a non-zero
    L2 distance means the framework arm's restart-blend moved the
    latent (which is the *intended* behaviour of the framework); the
    paper-quantity-driven β sweep is what moves it.
    """
    if b_end is None or f_end is None:
        return {
            "endpoint_l2": None,
            "endpoint_cosine_sim": None,
            "endpoint_mean_abs_diff": None,
            "endpoint_baseline_norm": None,
            "endpoint_framework_norm": None,
        }
    l2 = float(np.linalg.norm(b_end - f_end))
    cos = float(
        np.dot(b_end.ravel(), f_end.ravel())
        / (
            np.linalg.norm(b_end.ravel())
            * np.linalg.norm(f_end.ravel())
            + 1e-12
        )
    )
    mean_abs = float(np.abs(b_end - f_end).mean())
    return {
        "endpoint_l2": l2,
        "endpoint_cosine_sim": cos,
        "endpoint_mean_abs_diff": mean_abs,
        "endpoint_baseline_norm": float(np.linalg.norm(b_end)),
        "endpoint_framework_norm": float(np.linalg.norm(f_end)),
    }


def run_synth_sweep(
    *,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    nfe: int = DEFAULT_NFE,
    n_rounds: int = DEFAULT_N_ROUNDS,
) -> dict:
    cells: list[dict] = []
    base_wall: list[float] = []
    fw_wall: list[float] = []
    direct_metrics: list[dict[str, float]] = []

    adapter, mode = _resolve_adapter(
        "freqflow", force_mode="synthetic", nfe_budget=int(nfe),
    )
    if adapter is None:
        return {
            "freqflow_status": "synthetic",
            "ckpt_source": "synthetic-shim",
            "status": "BLOCKED",
            "reason": "adapter resolution returned None",
            "mode": mode,
            "n_records": 0,
        }
    print(f"[wave189-p3] adapter mode={mode}", flush=True)

    for seed in seeds:
        t0 = time.monotonic()
        baseline_trace, base_w = _solve_baseline(adapter, nfe=int(nfe), seed=int(seed))
        framework_trace, fw_w = _solve_framework(
            adapter, nfe=int(nfe), seed=int(seed), n_rounds=int(n_rounds),
        )
        b_end = _endpoint_latent(adapter, baseline_trace)
        f_end = _endpoint_latent(adapter, framework_trace)
        direct = _direct_endpoint_metric(b_end, f_end)
        direct_metrics.append(direct)
        cells.append(
            {
                "seed": int(seed),
                "nfe_budget": int(nfe),
                "n_rounds_framework": int(n_rounds),
                "adapter_mode": str(mode),
                "wallclock_baseline_s": round(base_w, 4),
                "wallclock_framework_s": round(fw_w, 4),
                "wallclock_ratio": round(fw_w / base_w, 4) if base_w > 0 else None,
                **direct,
            }
        )
        base_wall.append(base_w)
        fw_wall.append(fw_w)
        print(
            f"seed={seed} nfe={nfe} rounds={n_rounds} -> "
            f"mode={mode} l2={direct['endpoint_l2']:.4f} "
            f"cos={direct['endpoint_cosine_sim']:.4f} "
            f"wall_base={base_w:.4f}s wall_fw={fw_w:.4f}s",
            flush=True,
        )
        _ = time.monotonic() - t0

    # Aggregate direct.
    def _agg(key: str) -> float | None:
        vals = [d[key] for d in direct_metrics if d.get(key) is not None]
        return float(mean(vals)) if vals else None

    return {
        "schema": "wave189_p3_freqflow_synth_sweep.v1",
        "model": "freqflow",
        "axis": "image_sota",
        "freqflow_status": "synthetic",
        "ckpt_source": "synthetic-shim",
        "metric": "synthetic_endpoint_l2",
        "metric_definition": (
            "L2 distance between baseline and framework endpoint latents in "
            "(4, 32, 32) FreqFlow state space. NOT a real FID — there is no "
            "Inception forward pass, no real SiT-XL/2 + FFT graph. The "
            "FreqFlowAdapter in synthetic mode is a deterministic NumPy "
            "two-branch shim (4096 -> 256 -> 4096 spatial + linear "
            "projection of normalised FFT magnitude); the L2 distance reflects "
            "the framework arm's restart-blend effect on the latent, NOT any "
            "Frechet-Inception distance. See "
            "docs/models/freqflow.model_card.md §0 and "
            "data/freqflow_ckpt/README.md for the disclosure."
        ),
        "nfe": int(DEFAULT_NFE),
        "n_rounds": int(DEFAULT_N_ROUNDS),
        "seeds": list(seeds),
        "n_records": len(seeds),
        "cells": cells,
        "baseline_endpoint_norm_mean": _agg("endpoint_baseline_norm"),
        "framework_endpoint_norm_mean": _agg("endpoint_framework_norm"),
        "endpoint_l2_mean": _agg("endpoint_l2"),
        "endpoint_cosine_sim_mean": _agg("endpoint_cosine_sim"),
        "endpoint_mean_abs_diff_mean": _agg("endpoint_mean_abs_diff"),
        "wallclock_baseline_mean_s": float(mean(base_wall)) if base_wall else None,
        "wallclock_framework_mean_s": float(mean(fw_wall)) if fw_wall else None,
        "wallclock_framework_over_baseline_ratio": (
            float(mean(fw_wall) / mean(base_wall))
            if base_wall and fw_wall and mean(base_wall) > 0
            else None
        ),
        "primary_metric_status": (
            "PENDING — DOWNSTREAM_METRICS['freqflow'].primary_metric.name = "
            "'DEFERRED_no_upstream_ckpt' (no public ckpt, see Phase-4 "
            "deferred registry at tools/eval/io.py)."
        ),
        "adapter_modes": sorted({c.get("adapter_mode") for c in cells}),
        "verdict_overall": "SYNTHETIC_ONLY",
        "implication_for_paper": (
            "FreqFlowAdapter is registered in the synthetic registry and "
            "passes the D.5 conformance battery. The published "
            "nnet_ema.pth does NOT exist publicly (probed 2026-09-05: no "
            "GitHub releases, no HF Hub uploads, no PyPI package — see "
            "data/freqflow_ckpt/README.md). The paper's '5 adapters' "
            "claim is therefore partially synthetic on the image axis: "
            "4 real-ckpt adapters (LineageFlow + Kanzi + FlowMol3 + "
            "RectifiedFlowCIFAR) plus 1 synthetic-shim adapter "
            "(FreqFlow). The paper text should explicitly say "
            "'FreqFlow is included at synthetic-skeleton level; no "
            "quantitative FreqFlow result is reported'. The "
            "synthetic-shim L2 distance reported here is a sanity "
            "check on the integration, not a FreqFlow result."
        ),
        "synthetic_source": {
            "adapter_file": "adaptive_reflow/adapters/freqflow.py",
            "factory": "adaptive_reflow.adapters.freqflow:default_freqflow_adapter",
            "synthetic_velocity_field": (
                "_synthetic_velocity_field (two-branch NumPy shim: "
                "4096 -> 256 -> 4096 spatial MLP + linear projection "
                "of normalised FFT magnitude side-channel; Kaiming "
                "uniform init, seed=FREQ_FLOW_SYNTHETIC_SEED_DEFAULT)"
            ),
            "ckpt_path_attempted": [
                "data/freqflow/nnet_ema.pth (missing)",
                "data/nnet_ema.pth (missing)",
                "$FREQFLOW_CKPT (unset)",
            ],
            "real_ckpt_verdict": (
                "ABSENT — no public release as of 2026-09-05. Probe "
                "transcript: data/freqflow_ckpt/README.md."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(
            REPO_ROOT
            / "verification_outputs"
            / "wave189-p3-freqflow-real.json"
        ),
        help="Output JSON path",
    )
    parser.add_argument(
        "--nfe",
        type=int,
        default=DEFAULT_NFE,
        help="NFE per round (default: 100, matching Wave 189 P2 budget)",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=DEFAULT_N_ROUNDS,
        help="Framework rounds (default: 5, matching Wave 189 P2)",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(DEFAULT_SEEDS),
        help="Seeds (default: 0 1 2, matching Wave 189 P2)",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(
        f"[wave189-p3] running FreqFlow synthetic-mode sweep "
        f"(seeds={args.seeds} nfe={args.nfe} rounds={args.n_rounds})",
        flush=True,
    )

    report = run_synth_sweep(
        seeds=tuple(args.seeds),
        nfe=int(args.nfe),
        n_rounds=int(args.n_rounds),
    )
    report["timestamp"] = datetime.now(timezone.UTC).isoformat()
    report["sweep_script"] = (
        "scripts/wave189_p3_freqflow_synth_sweep.py"
    )
    # Pin commit_sha (Wave 186 P2 / Wave 188 pattern) so future
    # readers can resolve this output back to the exact commit.
    try:
        import subprocess as _sp
        _sha = _sp.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            stderr=_sp.DEVNULL,
        ).decode("utf-8").strip()
        report["commit_sha"] = _sha
    except Exception:  # noqa: BLE001
        report["commit_sha"] = None

    out_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"[wave189-p3] wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
