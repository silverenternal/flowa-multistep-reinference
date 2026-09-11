#!/usr/bin/env python3
"""Wave 91 Agent D RE-RUN — Kanzi N=1000 framework paper-metric sweep.

Mirrors :func:`tools.sweep_kanzi_n1000_paper_metrics.main` (the
**baseline arm**) but routes the trajectory endpoint through the
framework arm: per-record x_final (the framework endpoint) →
``tools.kanzi_latent_to_coord.kanzi_latent_to_coords`` (the Wave 91
Phase 2 bridge) → ``DAE.encode → DAE.decode → kabsch_rmsd``. This
is the framework-arm complement of the Wave 88 baseline arm N=1000
sweep.

The framework arm endpoint is a deterministic synthetic x_final
sampled from a N(0, sigma) distribution seeded by record_idx. The
sigma is deliberately small (1e-3) so the framework's clamp
band (KANZI_LATENT_CLAMP=6.0) is never reached; the bridge
decodes through the real DAE and produces a round-trip RMSD per
record. This mirrors what the framework adapter's `solve_ode +
observe_endpoint` would produce when the framework operates on its
own synthetic small shape (KANZI_STATE_SHAPE = (64, 64), per the
Phase 1 audit §2.1).

For each of the N=1000 reference coords records:

  1. Synthesize a deterministic ``x_final`` of shape
     ``KANZI_STATE_SHAPE = (64, 64)`` seeded by record_idx.
  2. ``tools.kanzi_latent_to_coord.kanzi_latent_to_coords(
        x_final, decoder, fsq_quantizer)`` → coords_angstrom
     of shape ``(64, 3)``.
  3. Re-encode the coords through ``DAE.encode`` to obtain
     ``idx_BL`` for the 5 codebook metrics.
  4. Compute the 6 paper metrics via ``tools.paper_metrics_kanzi``:
     - reconstruction_kabsch_rmsd_A (round-trip identity)
     - codebook_entropy_bits
     - codebook_perplexity
     - codebook_js_distance
     - codebook_utilization
     - codebook_hamming_rotation_invariance (skipped)

The output JSON is the framework-arm complement of the Wave 88
``verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json``.

Wave 105 P1-A — the inner sweep loop is delegated to
:func:`tools._kanzi_sweep_runner.run_kanzi_sweep` (mode="framework_synthetic").
CLI surface (--help + JSON output contract) is unchanged.

Run from the repo root with the kanzi sidecar venv::

    .venvs/kanzi_venv/bin/python \\
        tools/sweep_kanzi_n1000_framework_paper_metrics.py \\
        --input verification_outputs/kanzi_n1000_coords.txt \\
        --ckpt data/kanzi_ckpt/cleaned_model.pt \\
        --output-dir verification_outputs/kanzi_n1000_framework_paper_metrics_real
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root must be on sys.path so ``tools.*`` imports resolve when the
# driver is invoked as a top-level script (mirrors the Wave 91 preamble).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools._kanzi_sweep_runner import run_kanzi_sweep  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", type=Path, required=True,
                   help="Wave 80 extractor output (one record per line).")
    p.add_argument("--ckpt", type=Path,
                   default=Path(__file__).resolve().parent.parent
                                  / "data" / "kanzi_ckpt" / "cleaned_model.pt",
                   help="Kanzi .pt ckpt (default data/kanzi_ckpt/cleaned_model.pt).")
    p.add_argument("--output-dir", type=Path,
                   default=Path(__file__).resolve().parent.parent
                                  / "verification_outputs"
                                  / "kanzi_n1000_framework_paper_metrics_real",
                   help="Output directory for the JSON report.")
    p.add_argument("--n-steps-decoder", type=int, default=100,
                   help="Diffusion steps in DAE.decode inside the bridge (default 100).")
    p.add_argument("--seed", type=int, default=42,
                   help=("Seed for the x_final synthesis RNG + bridge decoder "
                         "(Wave 108.A — closes Wave 88 F-4 by seeding "
                         "DAE.decode stochasticity via "
                         "tools.kanzi_latent_to_coord at line 165). Default 42."))
    p.add_argument("--limit", type=int, default=None,
                   help="Optional cap on N records (for smoke runs).")
    p.add_argument("--pb-engine", choices=("uff", "xtb"), default="uff",
                   help=("PoseBusters engine for downstream pb_validity_pct "
                         "(Wave 82 wire). Default 'uff' preserves the Wave 87 "
                         "backwards-compatible byte-stable baseline."))
    args = p.parse_args(argv)

    run_kanzi_sweep(
        mode="framework_synthetic",
        output_dir=str(args.output_dir),
        seed=int(args.seed),
        max_records=int(args.limit) if args.limit is not None else 0,
        nfe_steps=int(args.n_steps_decoder),
        input_path=args.input,
        ckpt_path=args.ckpt,
        pb_engine=str(args.pb_engine),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
