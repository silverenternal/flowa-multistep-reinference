"""SOTA FlowMol3 experiment — baseline vs FlowA framework (STUB).

This is the **stub** harness for the FlowMol3 molecule generation
experiment described in the FlowMol3Adapter design spec. It is
intentionally NOT implemented end-to-end here — the production harness
will be authored in a follow-up turn when:

1. The FlowMol3 paper PDF + abstract are staged under
   ``data/flowmol3/paper.pdf`` (the design spec's dependency blocker).
2. The published FlowMol3 checkpoint is available (the adapter's
   ``backend="torch"`` path lazy-imports torch + the zavalab FlowMol3
   module at commit ``77cae22174b7792b0e25e9e0414038420736d841``).
3. RDKit + the canonical GEOM-DRUGS reference set are reachable from
   the run environment for the validity / QED / SA / logP / atom- and
   bond-stability metric panel.

Design spec (mirrors the 2D / CIFAR runbooks):

* CLI: ``--adapter {flowmol3adapter,reference_flowa}``,
  ``--target {geom_drugs,qm9}``, ``--n-molecules``, ``--framework-rounds``,
  ``--schedulers {cosine,evidence_driven,codim_sheet,free_traj}``,
  ``--baseline-nfe``, ``--output-dir``.
* Pipeline per row:
  (1) baseline = single-pass ``FlowMol3Adapter.solve_ode(num_steps=100, ...)``
      with vanilla ``N(0, I)`` prior;
  (2) framework row = :class:`Engine.run_round` loop over the four
      schedulers, pooling the LAST (round N-1) endpoint of each chain
      into ``--framework-molecules`` SMILES strings.
* Metrics: validity, validity-sanitized, uniqueness, novelty, QED mean,
  SA mean, logP distribution, atom/bond-stability per snapshot (using
  RDKit + the canonical GEOM-DRUGS reference set).
* Output (under ``--output-dir``, default ``data/flowmol3_out/``):
  ``baseline_molecules.smi``, ``{scheduler}_molecules.smi``,
  ``comparison.md`` (5-row metrics table), ``per_round_metrics.csv``,
  ``summary.json``.
* Built-in determinism: ``SHA-256(seed + scheduler config)`` drives
  every RNG draw; mirrored on ``tools/run_sota_cifar_experiment.py``
  (lines 76, 690, 1110-1291).

Until the dependency blockers are cleared, this module's ``main()``
prints a TODO marker and exits non-zero so callers cannot mistake it
for a working pipeline.
"""

from __future__ import annotations

import argparse
import sys


TODO_BANNER: str = (
    "TODO: tools/run_sota_flowmol3adapter_experiment.py is a stub.\n"
    "See the docstring for the design spec and dependency blockers.\n"
    "Implement once (a) the FlowMol3 paper PDF is staged at\n"
    "    data/flowmol3/paper.pdf\n"
    "and (b) the published FlowMol3 checkpoint is reachable for the\n"
    "    backend='torch' lazy-load.\n"
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_sota_flowmol3adapter_experiment",
        description=(
            "SOTA FlowMol3 baseline-vs-FlowA experiment (STUB). "
            "See module docstring for design spec + dependency blockers."
        ),
    )
    parser.add_argument(
        "--adapter",
        choices=("flowmol3adapter", "reference_flowa"),
        default="flowmol3adapter",
    )
    parser.add_argument(
        "--target",
        choices=("geom_drugs", "qm9"),
        default="geom_drugs",
    )
    parser.add_argument("--n-molecules", type=int, default=10000)
    parser.add_argument("--framework-rounds", type=int, default=20)
    parser.add_argument(
        "--schedulers",
        nargs="+",
        default=("cosine", "evidence_driven", "codim_sheet", "free_traj"),
    )
    parser.add_argument("--baseline-nfe", type=int, default=100)
    parser.add_argument("--output-dir", default="data/flowmol3_out")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    print(TODO_BANNER, flush=True)
    print(
        "[run_sota_flowmol3adapter_experiment] parsed args:\n"
        f"  adapter={args.adapter}\n"
        f"  target={args.target}\n"
        f"  n_molecules={args.n_molecules}\n"
        f"  framework_rounds={args.framework_rounds}\n"
        f"  schedulers={args.schedulers}\n"
        f"  baseline_nfe={args.baseline_nfe}\n"
        f"  output_dir={args.output_dir}",
        flush=True,
    )
    return 2  # distinct non-zero code; no working pipeline yet.


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))