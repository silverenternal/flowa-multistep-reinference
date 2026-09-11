#!/usr/bin/env python3
"""Wave 95 Phase 3.C — N=1000 framework paper-metric sweep via project_out⁻¹ bridge.

Mirrors :func:`tools.sweep_kanzi_n1000_framework_paper_metrics.main` but
**feeds the bridge a 512-d ``x_final``** (the framework trajectory endpoint
geometry — ``n_channels_decoder=512``, the post-``project_out`` space)
instead of the 64-d noise that the Wave 91 driver synthesises.

The Phase 3.B bridge (`tools.kanzi_latent_to_coord.kanzi_latent_to_coords`)
now strictly requires 512-d input because it routes through a *trained*
``Linear(512 → 4)`` inverse of ``project_out`` (see commit 378dc4a and
``tools/_kanzi_project_out_inv_train.py``). The Wave 91 sweep driver's
64-d noise synthesis pre-dates that wire — running it unchanged triggers
``RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x64 and 512x4)``
on every record.

This driver keeps the bridge + paper-metric + per-record logic identical
to the Wave 91 driver (so the only variable is the x_final shape, 64→512);
the change is local to this script and never touches
``tools/kanzi_latent_to_coord.py`` (Phase 3.B owns that file).

Output JSON mirrors
``verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json``
(per-arm Δ vs Wave 88 N=1000 baseline arm).

Wave 105 P1-A — the inner sweep loop is delegated to
:func:`tools._kanzi_sweep_runner.run_kanzi_sweep` (mode="framework_inv_proj",
projector="project_out_inv"). CLI surface (--help + JSON output contract)
is unchanged.

Run from the repo root with the kanzi sidecar venv::

    .venvs/kanzi_venv/bin/python \\
        tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \\
        --input verification_outputs/kanzi_n1000_coords.txt \\
        --ckpt data/kanzi_ckpt/cleaned_model.pt \\
        --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics_inv_proj
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root must be on sys.path so ``tools.*`` imports resolve when the
# driver is invoked as a top-level script (mirrors the Wave 95 preamble).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools._kanzi_sweep_runner import run_kanzi_sweep  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--ckpt", type=Path,
                   default=Path(__file__).resolve().parent.parent
                                  / "data" / "kanzi_ckpt" / "cleaned_model.pt")
    p.add_argument("--output-dir", type=Path,
                   default=Path(__file__).resolve().parent.parent
                                  / "verification_outputs"
                                  / "kanzi_n1000_framework_paper_metrics_inv_proj")
    p.add_argument("--n-steps-decoder", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--limit", type=int, default=1000)
    args = p.parse_args(argv)

    run_kanzi_sweep(
        mode="framework_inv_proj",
        projector="project_out_inv",
        output_dir=str(args.output_dir),
        seed=int(args.seed),
        max_records=int(args.limit),
        nfe_steps=int(args.n_steps_decoder),
        input_path=args.input,
        ckpt_path=args.ckpt,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
