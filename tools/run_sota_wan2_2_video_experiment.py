#!/usr/bin/env python3
"""Wan2.2 video Flow Matching ODE adapter — SOTA experiment harness (STUB).

This is a **stub** for the SOTA experiment harness that would compare
the Wan2.2 video adapter's framework-driven multi-round re-inference
against a single-pass DPM++ baseline on the Wan-Bench 2.0 / FVD
benchmark.

The full harness is BLOCKED on the dependency blockers listed in the
design spec:

* Wan2.2 paper PDF (data/wan2_2/paper_metadata.json is
  status=metadata_only with URL containing 'undefined'; needs a real
  arXiv ID).
* Wan2.2 model weights (Wan-AI/Wan2.2-T2V-A14B or
  Wan-AI/Wan2.2-TI2V-5B-Diffusers safetensors checkpoint, ~28 GB for
  A14B and ~10 GB for TI2V-5B).
* Wan2.2-VAE weights (separate from the DiT weights; needed for the
  ``vae_pixel_video`` materialization channel).
* umT5-XXL text encoder weights (~10 GB; either from
  google/umt5-xxl or packaged inside the Wan2.2 release).
* diffusers >= 0.30 (or the official Wan-Video/Wan2.2 codebase) for
  the MoE routing primitives.
* flash-attn 2 or 3 (required for DiT attention to fit in GPU memory
  at 14 B-param scale).
* I3D model weights for FVD computation (torch.hub 'kornia/i3d' or
  facebookresearch/vbench).
* GPU hardware: NVIDIA GPU with >=40 GB VRAM (A100/H100) for the
  A14B MoE variant at 480P.

The adapter module
(:mod:`adaptive_reflow.adapters.wan2_2_video`)
implements the full
:class:`adaptive_reflow.universal.adapter.FlowMatchingODEAdapter`
Protocol surface — the test suite at
``tests/test_adapters/test_wan2_2_video.py``
covers all 18 contract points in ``synthetic`` mode and exits 0/18
green today.

Once the dependency blockers are resolved, this harness should be
extended to follow the seven-step protocol in
``docs/r4-survey/07-sota-experiment-protocol.md`` plus the
video-specific extension (Wan-Bench 2.0, FVD on a 2048-prompt held-
out subset, GPU VRAM budget, I3D feature extraction).

CLI (planned)
-------------

::

    PYTHONPATH=. python tools/run_sota_wan2_2_video_experiment.py \\
        --variant t2v_a14b \\
        --resolution 480p \\
        --n-videos 128 \\
        --n-rounds 20 \\
        --framework-videos 256 \\
        --output-dir ./data/wan_video_out

Planned outputs under ``<output-dir>/``:

* ``baseline_videos.npz`` — ``(N, T, 3, H, W)`` pixel videos from the
  single-pass DPM++ baseline (post Wan2.2-VAE decode).
* ``<scheduler>_videos.npz`` — framework-driven per-scheduler
  pixel videos (post Wan2.2-VAE decode).
* ``comparison.md`` — Wan-Bench 2.0 + FVD comparison table.
* ``summary.json`` — full per-round metrics + audit hashes.

Tasks satisfied
---------------

* R5 (CLM-046) — stub scaffold for the Wan2.2 SOTA experiment.

Notes
-----

The harness deliberately exits with code 1 (and prints this banner)
to surface the unblocking checklist. Once the dependency blockers
are resolved, replace ``main()`` with the full implementation per
the protocol design.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


_TODO = """\
[Wan2.2 video Flow Matching ODE adapter] SOTA experiment harness NOT
IMPLEMENTED — blocked on the dependency blockers listed in the design
spec.

Dependency blockers (must be resolved before authoring the executable
harness):

  1. Wan2.2 paper PDF (data/wan2_2/paper_metadata.json is
     status=metadata_only with URL containing 'undefined'; needs a
     real arXiv ID, most likely 2503.20314 for the Wan technical
     report or a dedicated Wan2.2-only paper).
  2. Wan2.2 model weights (Wan-AI/Wan2.2-T2V-A14B or
     Wan-AI/Wan2.2-TI2V-5B-Diffusers safetensors checkpoint, ~28 GB
     for A14B and ~10 GB for TI2V-5B).
  3. Wan2.2-VAE weights (separate from the DiT weights; needed for
     the vae_pixel_video materialization channel).
  4. umT5-XXL text encoder weights (~10 GB; either from
     google/umt5-xxl or packaged inside the Wan2.2 release).
  5. diffusers >= 0.30 (or the official Wan-Video/Wan2.2 codebase)
     for the MoE routing primitives.
  6. flash-attn 2 or 3 (required for DiT attention to fit in GPU
     memory at 14 B-param scale; without it the adapter cannot run
     on a single consumer GPU).
  7. I3D model weights for FVD computation (torch.hub 'kornia/i3d'
     or facebookresearch/vbench).
  8. GPU hardware: NVIDIA GPU with >=40 GB VRAM (A100/H100) for the
     A14B MoE variant at 480P; TI2V-5B fits on a 16 GB consumer GPU
     but is still not CPU-feasible.
  9. Re-derivation of the Wan2.2 noise schedule as a flow-matching
     schedule: the published sigma(t) and t_moe threshold must be
     sourced from the Wan-Video reference code.
 10. xformers or sage-attention as a flash-attn alternative.

Until these are resolved, the adapter remains in ``synthetic`` mode
and the harness has no executable path.

The Protocol surface is fully implemented and the test suite at
tests/test_adapters/test_wan2_2_video.py
exits 0/18 green today. The protocol design is captured in
docs/r4-survey/07-sota-experiment-protocol.md §8 (video extension).
"""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the planned CLI; accepted but currently a no-op."""
    parser = argparse.ArgumentParser(
        description=(
            "Wan2.2 video Flow Matching ODE adapter — SOTA experiment "
            "harness (STUB; blocked on dependency blockers)."
        ),
    )
    parser.add_argument(
        "--variant",
        choices=("t2v_a14b", "ti2v_5b", "i2v_a14b"),
        default="t2v_a14b",
        help="Wan2.2 variant (default: t2v_a14b).",
    )
    parser.add_argument(
        "--resolution",
        choices=("480p", "720p"),
        default="480p",
        help="Wan2.2 output resolution (default: 480p).",
    )
    parser.add_argument(
        "--n-videos",
        type=int,
        default=128,
        help="Number of videos per scheduler (default: 128).",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=20,
        help="Number of multi-round re-inference rounds (default: 20).",
    )
    parser.add_argument(
        "--framework-videos",
        type=int,
        default=256,
        help="Number of framework-driven videos per scheduler (default: 256).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/wan_video_out"),
        help="Output directory for baseline + framework + comparison.md.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Print the stub banner; return 1 to surface the unblocking checklist.

    The harness is intentionally non-zero exit because it is not yet
    executable. Once the dependency blockers are resolved, this
    ``main()`` should be replaced with the full SOTA experiment driver
    per the protocol design in
    ``docs/r4-survey/07-sota-experiment-protocol.md`` §8.
    """
    args = _parse_args(argv)
    print(_TODO, file=sys.stderr)
    print(
        "[Wan2.2 video Flow Matching ODE adapter] "
        f"variant={args.variant} resolution={args.resolution} "
        f"n_videos={args.n_videos} n_rounds={args.n_rounds} "
        f"framework_videos={args.framework_videos} "
        f"output_dir={args.output_dir}",
        file=sys.stderr,
    )
    print(
        "[Wan2.2 video Flow Matching ODE adapter] STUB HARNESS — "
        "exit 1 (no executable path until dependency blockers resolve).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
