"""SOTA GraphBFN (Bayesian Flow Network on graphs) experiment harness — STUB.

This is a **placeholder stub** for the GraphBFN molecular-graph
SOTA harness described in the design spec. The full harness (4
schedulers x N rounds, RDKit-based validity / FCD / NSPDK
evaluators, comparison.md + summary.json output) is gated on:

1. The published GraphBFN weights landing in ``data/graphbfn/`` (per
   design spec: ``paper.pdf`` + ``weights`` status='failed' in
   ``data/graphbfn/paper_metadata.json`` /
   ``weights_metadata.json``).
2. The RDKit + ChemNet evaluator dependencies landing in
   ``/tmp/flowa_rdkit_env`` (the same isolated-venv pattern as
   ``tools/run_sota_cifar_experiment.py``'s FID env).

Until both gate items land, the adapter runs in ``synthetic`` mode
and there is no production graph to evaluate. The stub here exists
only to document the intended harness surface so future agents can
land the full implementation; running ``python
tools/run_sota_graphbfn_experiment.py --help`` prints the planned
CLI and exits with a non-zero status.

To run once the gates above are met::

    python tools/run_sota_graphbfn_experiment.py \\
        --checkpoint data/graphbfn_qm9.pt \\
        --dataset qm9 \\
        --output-dir data/graphbfn_out_qm9 \\
        --n-samples 10000 \\
        --n-rounds 20 \\
        --framework-samples 500

Tasks satisfied:

* ``DTB-M7-STUB`` — molecule SOTA harness stub for GraphBFN.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Make the project importable when running as
# ``python tools/run_sota_graphbfn_experiment.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI parser mirroring the planned harness surface."""
    parser = argparse.ArgumentParser(
        prog="run_sota_graphbfn_experiment",
        description=(
            "GraphBFN SOTA experiment harness (STUB). Mirrors "
            "tools/run_sota_cifar_experiment.py but for molecular "
            "graph generation: RDKit-based validity / FCD / NSPDK "
            "evaluators on QM9 / ZINC250k graphs."
        ),
        epilog=(
            "TODO: full implementation gated on data/graphbfn/weights "
            "landing and the RDKit + ChemNet evaluator env "
            "(/tmp/flowa_rdkit_env). See the design spec."
        ),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("data/graphbfn_qm9.pt"),
        help="Path to the published GraphBFN state_dict checkpoint.",
    )
    parser.add_argument(
        "--dataset",
        choices=("qm9", "zinc250k"),
        default="qm9",
        help="Canonical benchmark dataset (default: qm9).",
    )
    parser.add_argument(
        "--variant",
        choices=("iclr2025", "hierarchical"),
        default="iclr2025",
        help="GraphBFN variant (ICLR-2025 or Hierarchical BFN).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/graphbfn_out"),
        help="Directory for baseline_graphs.npz, "
        "{scheduler}_graphs.npz, comparison.md, summary.json.",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=10_000,
        help="Number of baseline graphs (default: 10000).",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=20,
        help="Number of multi-round re-inference rounds (default: 20).",
    )
    parser.add_argument(
        "--framework-samples",
        type=int,
        default=500,
        help="Number of framework chains per scheduler (default: 500).",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=1_000,
        help="Number of BFN update steps per sample (paper: ~1000 "
        "on QM9, ~500 on ZINC250k for the 1-RF equivalent).",
    )
    parser.add_argument(
        "--condition-kind",
        choices=("unconditional", "property_logp", "property_qed", "property_sa"),
        default="unconditional",
        help="Generation condition kind (default: unconditional).",
    )
    parser.add_argument(
        "--property-value",
        type=float,
        default=None,
        help="Target property scalar for property-conditioned generation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Stub entry point: print the planned CLI and bail."""
    parser = _build_arg_parser()
    # Parse-only path: ``--help`` and friends. We do NOT execute any
    # orchestration until the gates above are met.
    args = parser.parse_args(argv)

    print(
        "GraphBFN SOTA harness is a STUB (DTB-M7-STUB).",
        file=sys.stderr,
    )
    print(
        "Full implementation gated on:",
        file=sys.stderr,
    )
    print(
        "  1. data/graphbfn/weights landing (paper.pdf + state_dict)",
        file=sys.stderr,
    )
    print(
        "  2. /tmp/flowa_rdkit_env RDKit + ChemNet evaluator env",
        file=sys.stderr,
    )
    print(
        "  3. RDKit >= 2024.3.3 + chemnet-pretrained-weights",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print(
        "Planned CLI surface (parsed but unused): "
        f"checkpoint={args.checkpoint}, dataset={args.dataset}, "
        f"variant={args.variant}, output_dir={args.output_dir}, "
        f"n_samples={args.n_samples}, n_rounds={args.n_rounds}, "
        f"framework_samples={args.framework_samples}, num_steps={args.num_steps}, "
        f"condition_kind={args.condition_kind}, "
        f"property_value={args.property_value}",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print(
        "Until the gates land, run the GraphBFN adapter directly via:",
        file=sys.stderr,
    )
    print(
        "  python -c 'from adaptive_reflow.adapters.graphbfn import default_graphbfn_adapter; "
        "a = default_graphbfn_adapter(); out = a.batched_inference(n_samples=10, "
        "num_steps=8, seed=0); print(len(out), out[0])'",
        file=sys.stderr,
    )
    return 2  # EX_USAGE — matches the harness convention.


if __name__ == "__main__":
    raise SystemExit(main())