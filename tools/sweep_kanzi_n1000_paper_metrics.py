#!/usr/bin/env python3
"""Wave 83 Agent D — Kanzi N=1000 paper-metric sweep (5 codebook + 1 reconstruction).

Runs the Kanzi upstream DAE ``encode → decode → kabsch_rmsd`` loop on
the Wave 80 N=1000 reference coords file
(``verification_outputs/kanzi_n1000_coords.txt``, 4 vendored demo PDBs
× 250 Gaussian variants, σ=0.10 Å, seed=0 — Wave 80 Agent B contract).

Per record we:
  1. ``DAE.encode(x)`` → ``idx_BL`` (LongTensor of FSQ codebook indices)
  2. ``DAE.decode(idx_BL)`` → reconstruction → ``kabsch_rmsd`` (Å, lower is better)

After the per-record pass we compute the 5 codebook paper metrics from
the aggregated ``idx_BL`` tensor using the Wave 83 Agent B wrapper
``tools.paper_metrics_kanzi.compute_all_codebook_metrics``.

Output JSON layout mirrors the Wave 79 driver report
(``verification_outputs/wave80_kanzi_smoke_eval/reconstruction.json``)
plus the 5 codebook metrics, written to
``verification_outputs/kanzi_n1000_paper_metrics.json``.

NOTE: this is the **baseline arm** (no framework restart-blend). The
framework arm uses the existing ``run_real_ckpt_eval.py --model kanzi
--force-mode real --composite-metric real`` pipeline at the upstream N=2
budget per Wave 79; the framework-vs-baseline reading at N=1000 is
reproduced from that 6-cell sweep and pinned in the audit doc.

Wave 105 P1-A — the inner sweep loop is delegated to
:func:`tools._kanzi_sweep_runner.run_kanzi_sweep` (mode="baseline").
CLI surface (--help + JSON output contract) is unchanged.

Usage:
    .venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \\
        --input verification_outputs/kanzi_n1000_coords.txt \\
        --ckpt data/kanzi_ckpt/cleaned_model.pt \\
        --output-dir verification_outputs/kanzi_n1000_paper_metrics
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root must be on sys.path so ``tools.*`` imports resolve when the
# driver is invoked as a top-level script (mirrors the Wave 83 preamble).
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
                                  / "kanzi_n1000_paper_metrics",
                   help="Output directory for the JSON report.")
    p.add_argument("--limit", type=int, default=None,
                   help="Optional cap on N records (for smoke runs).")
    p.add_argument("--seed", type=int, default=42,
                   help=("Seed for the bridge decoder (Wave 108.A — closes "
                         "Wave 88 F-4 by ensuring DAE.decode stochasticity "
                         "is seeded via tools.kanzi_latent_to_coord at "
                         "kanzi_latent_to_coord.py:165). Default 42."))
    p.add_argument("--pb-engine", choices=("uff", "xtb"), default="uff",
                   help=("PoseBusters engine for downstream pb_validity_pct "
                         "(Wave 82 wire). Default 'uff' preserves the Wave 87 "
                         "backwards-compatible byte-stable baseline."))
    args = p.parse_args(argv)

    run_kanzi_sweep(
        mode="baseline",
        output_dir=str(args.output_dir),
        seed=int(args.seed),
        max_records=int(args.limit) if args.limit is not None else 0,
        nfe_steps=100,
        input_path=args.input,
        ckpt_path=args.ckpt,
        pb_engine=str(args.pb_engine),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
