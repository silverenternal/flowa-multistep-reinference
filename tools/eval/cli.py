"""CLI argument parsing + entry point.

OWNER: Wave 97 Agent B — tools/eval/ subpackage split (single responsibility:
argparse construction + ``main()`` entry point + ``__main__`` guard).
Re-exports ``build_argparser`` + ``main`` for the
``tools/run_real_ckpt_eval.py`` shim.

This module is byte-stable against `tools/run_real_ckpt_eval.py` pre-split:
every CLI flag + every default + the ``--help`` string + the exit codes
match the pre-Wave-97 contract.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

from tools.eval.io import (  # type: ignore
    VALID_MODELS,
    _capture_env_hash_lightweight,
    build_report,
)
from tools.eval.sweep import _run_cell  # type: ignore


def build_argparser() -> argparse.ArgumentParser:
    """Return the canonical CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="tools.run_real_ckpt_eval",
        description=(
            "PHASE-4 real-ckpt baseline-vs-framework evaluation harness. "
            "Per-cell value surface for G-MASTER-CAPABILITY extension."
        ),
    )
    p.add_argument(
        "--model", type=str, required=True, choices=VALID_MODELS,
        help=f"Model family to evaluate. One of: {', '.join(VALID_MODELS)}.",
    )
    p.add_argument(
        "--seeds", type=str, required=True,
        help="Comma-separated list of integer seeds (e.g. '42' or '42,43,44').",
    )
    p.add_argument(
        "--nfe-budgets", type=str, required=True,
        help="Comma-separated list of integer NFE budgets (e.g. '50,100,250').",
    )
    p.add_argument(
        "--n-rounds", type=int, default=3,
        help="Number of framework rounds per cell (default 3). Total framework "
        "NFE budget is matched to baseline NFE, so n-rounds=3 means each round "
        "uses ceil(NFE/3) steps.",
    )
    p.add_argument(
        "--output", type=pathlib.Path, required=True,
        help="Output JSON path. Parent directories are created.",
    )
    p.add_argument(
        "--print-only", action="store_true",
        help="Print the report JSON to stdout instead of writing to disk.",
    )
    p.add_argument(
        "--force-mode", type=str, default="synthetic",
        choices=("synthetic", "real", "auto"),
        help=(
            "Adapter operating mode. 'synthetic' uses the zero-dependency "
            "shim path (default); 'real' loads real checkpoint weights "
            "(requires the upstream package + ckpt on disk; fails loudly "
            "otherwise); 'auto' tries real first and falls back to "
            "synthetic on ImportError / missing ckpt."
        ),
    )
    p.add_argument(
        "--metric-mode", type=str, default="synthetic",
        choices=("synthetic", "real", "auto"),
        help=(
            "Per-cell downstream-metric mode. 'synthetic' (default) keeps "
            "the Wave 36 hard-wired saturation-threshold fallback (zero "
            "upstream deps, CI-friendly). 'real' runs the per-model real "
            "downstream metric (protein_sequence_validity_rate for kanzi; "
            "family_validity_rate for lineageflow) via the upstream "
            "package + Bio.SeqIO. 'auto' tries 'real' first and falls back "
            "to 'synthetic' on ImportError / missing ckpt. See "
            "docs/audit/wave43-metric-layer-fix.md for the dispatch "
            "implementation."
        ),
    )
    p.add_argument(
        "--restart-min-nfe", type=int, default=20,
        help=(
            "NFE-adaptive restart-blend gate threshold (Wave 58 Agent 1, "
            "wired in Wave 61 Agent 1). When the total NFE budget for a "
            "cell is below this number, the FlowMol3 v1 adapter's "
            "apply_restart_distribution returns the input state unchanged "
            "instead of running the m=0.5 graph blend. Total NFE (not "
            "per-round) — see docs/audit/wave58-nfe-adaptive-gate-impl.md "
            "§3 for the per-round trap. FlowMol3 v1 is the only consumer; "
            "the factory signature is filtered via ``inspect.signature`` "
            "so other adapters silently ignore this knob. Default 20 "
            "matches Wave 58's published threshold. "
            "``--restart-min-nfe 0`` disables the gate (restores "
            "pre-Wave-58 behaviour)."
        ),
    )
    p.add_argument(
        "--composite-metric", type=str, default="auto",
        choices=("synthetic", "real", "auto"),
        help=(
            "Composite metric mode for supported models. 'synthetic' "
            "(default for unsupported models) skips the composite "
            "computation. 'real' forces the composite to be computed "
            "when --model kanzi, lineageflow, flowmol3, or flowmol3_v2. "
            "'auto' enables the composite for those four models and "
            "skips otherwise. The LineageFlow composite (Wave 47) is "
            "a 100% flow-component 3-term scalar in [-1, 1]; positive "
            "= framework improves the flow bundle. The FlowMol3 "
            "composite (Wave 49 Agent D) is a 5-axis chemistry+geometry "
            "scalar in [-1, +1]; the geometry axis is dropped when "
            "xtb is not on $PATH. The Kanzi composite (Wave 52 "
            "Agent A) is a 100% flow-component 3-term scalar in "
            "[-1, 1] on Kanzi's continuous latent (NOT the AR-prior "
            "discrete categorical); K_lf = KANZI_LATENT_DIM = 64. "
            "See docs/audit/wave47-eval-pipeline-design.md, "
            "docs/audit/wave47-eval-pipeline-integration.md, "
            "docs/audit/wave49-glue-design.md §3C, "
            "docs/audit/wave49-eval-pipeline-integration.md, and "
            "docs/audit/wave52-kanzi-composite.md."
        ),
    )
    p.add_argument(
        "--n-molecules", type=int, default=1,
        help=(
            "Number of molecules sampled per cell (Wave 74 F1, "
            "opt-in). When > 1, the adapter's ``solve_ode`` generates "
            "``n_molecules`` independent trajectories and the eval "
            "pipeline's FlowMol3 composite consumes the batch via "
            "``adapter.export_sampled_molecules(trace)``. Currently "
            "honoured by the FlowMol3 v2 adapter only; other "
            "adapters ignore the kwarg (legacy callers are "
            "byte-stable). Default 1 preserves the legacy "
            "single-molecule-cell contract."
        ),
    )
    p.add_argument(
        "--paper-metrics", action="store_true",
        help=(
            "Wave 75: opt-in flag that adds the 4 paper-parity metrics "
            "(paper_validity_pct / paper_pb_validity_pct / "
            "paper_fg_deviation / paper_ood_ring_rate) to each "
            "FlowMol3 / FlowMol3 v2 cell's debug dict. Computed via "
            "tools.paper_metrics.compute_all_paper_metrics on the "
            "sampled_molecules returned by adapter.export_sampled_molecules. "
            "Off by default to preserve byte-stability for legacy "
            "callers. Requires --force-mode real (or auto with a real "
            "ckpt) and at least one sampled molecule. See "
            "docs/audit/wave75-phase1-audit.md + "
            "docs/audit/wave75-phase2-paper-metrics.md for the audit "
            "and the implementation."
        ),
    )
    p.add_argument(
        "--paper-reference", type=str, default="GEOM_DRUGS",
        choices=("GEOM_DRUGS", "NCI_first_5K_proxy"),
        help=(
            "Wave 75: reference distribution for paper_fg_deviation "
            "+ paper_ood_ring_rate. 'GEOM_DRUGS' (default, paper "
            "parity) reads the canonical "
            "data/geom_full_kekulized/train_reos_ring_counts.pkl "
            "(187 MB, vendored Wave 70+); 'NCI_first_5K_proxy' uses "
            "the Wave 49 5K-mol NCI fallback (smaller reference, "
            "different fg_dev number). Only consulted when "
            "--paper-metrics is set."
        ),
    )
    # ------------------------------------------------------------------
    # Wave 79 — per-model upstream-eval subprocess flags (opt-in).
    # ------------------------------------------------------------------
    p.add_argument(
        "--lineageflow-upstream-eval", action="store_true",
        help=(
            "Wave 79: opt-in flag. After each lineageflow cell, dump "
            "the baseline + framework ODE endpoint to a FASTA file "
            "(decoded via mod-20 over K=33) and invoke the upstream "
            "data/lineageflow_upstream/evaluation/evaluate_all.py "
            "orchestrator as a subprocess. The orchestrator writes a "
            "summary.json with the family_validity / foldability / "
            "self_consistency / novelty metrics; we surface those "
            "values on the cell's upstream_eval_metrics dict. "
            "Requires HMMER + MMseqs2 + OmegaFold + ESM-IF binaries "
            "on $PATH (per docs/audit/wave79-phase1-audit.md §1.3) "
            "+ the Pfam-A.hmm + MMseqs2 target DB on disk. Off by "
            "default; the internal observer path is the legacy default."
        ),
    )
    p.add_argument(
        "--kanzi-upstream-eval", action="store_true",
        help=(
            "Wave 79: opt-in flag. After each kanzi cell, dump the "
            "baseline + framework ODE endpoint to a per-sequence "
            "comma-separated Å-coordinate file and invoke Kanzi's "
            "upstream DAE.encode + DAE.decode + kabsch_rmsd as a "
            "subprocess (the README quick-start's eval surface; "
            "Kanzi upstream has NO evaluation/ directory per Phase 1 "
            "§2.3). Surfaces the per-sequence + mean Kabsch RMS "
            "on the cell's upstream_eval_metrics dict. Requires torch "
            "+ the published cleaned_model.pt (data/kanzi_ckpt/). "
            "Off by default."
        ),
    )
    p.add_argument(
        "--kanzi-framework-paper-metrics", action="store_true",
        help=(
            "Wave 91 Phase 3 (retry): opt-in flag. After each "
            "kanzi cell, run the framework arm through the Wave 91 "
            "Phase 2 latent->coord bridge (tools/kanzi_latent_to_coord.py) "
            "and compute the 6-metric Kanzi paper suite "
            "(reconstruction_kabsch_rmsd_A + 5 codebook metrics) "
            "via tools.paper_metrics_kanzi.compute_all_paper_metrics. "
            "This is the framework-arm complement to "
            "--kanzi-upstream-eval (which only emits the baseline "
            "arm's reading). Requires torch + the published "
            "cleaned_model.pt (data/kanzi_ckpt/) + the kanzi Python "
            "package on sys.path (the .venvs/kanzi_venv sidecar). "
            "Off by default; --kanzi-upstream-eval is the legacy "
            "default for backward compat (Phase 4 ran with that "
            "flag and produced a n=2 framework-arm proxy at "
            "+0.77 Angstrom -- see docs/audit/wave91-phase4-eval.md)."
        ),
    )
    p.add_argument(
        "--flowmol3-upstream-eval", action="store_true",
        help=(
            "Wave 79: opt-in flag. After each flowmol3 / flowmol3_v2 "
            "cell, write the sampled_molecules (already exported by "
            "Wave 70 Phase 3 export_sampled_molecules) to a SMILES "
            "list file and invoke the vendored flowmol "
            "SampleAnalyzer.analyze as a subprocess (paper-parity "
            "validity + pb_valid + reos + ood_rate). Equivalent to "
            "the Wave 75 --paper-metrics path but invoked via the "
            "upstream SampleAnalyzer directly (no in-process wrapper). "
            "Off by default; --paper-metrics is the Wave 75 default "
            "for backward compat."
        ),
    )
    p.add_argument(
        "--upstream-n-samples", type=int, default=1000,
        help=(
            "Wave 79: number of sequences / molecules / SMILES to "
            "feed into the upstream eval per cell. Default 1000 "
            "(matches Wave 76 paper-claim protocol). Ignored when "
            "no --*-upstream-eval flag is set. Large values slow "
            "the cell down by the upstream eval wallclock (~1.5-4 "
            "h per 1000 PDBs for Kanzi; ~1.5-3.5 h per 1000 seqs "
            "for LineageFlow)."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on per-cell error, 2 on tool error."""
    args = build_argparser().parse_args(argv)
    if args.n_rounds <= 0:
        print("[ERROR] --n-rounds must be positive", file=sys.stderr)
        return 2
    if int(args.n_molecules) < 1:
        print("[ERROR] --n-molecules must be >= 1", file=sys.stderr)
        return 2
    try:
        seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    except ValueError as exc:
        print(f"[ERROR] --seeds parse failed: {exc}", file=sys.stderr)
        return 2
    try:
        nfe_budgets = [int(s.strip()) for s in args.nfe_budgets.split(",") if s.strip()]
    except ValueError as exc:
        print(f"[ERROR] --nfe-budgets parse failed: {exc}", file=sys.stderr)
        return 2
    if not seeds or not nfe_budgets:
        print("[ERROR] --seeds and --nfe-budgets must be non-empty", file=sys.stderr)
        return 2
    env_hash = _capture_env_hash_lightweight()
    cells: list[dict[str, Any]] = []
    for seed in seeds:
        for nfe in nfe_budgets:
            cell = _run_cell(
                args.model, seed=int(seed), nfe=int(nfe), n_rounds=int(args.n_rounds),
                force_mode=args.force_mode, metric_mode=args.metric_mode,
                composite_metric=args.composite_metric,
                restart_min_nfe=args.restart_min_nfe,
                n_molecules=int(args.n_molecules),
                paper_metrics_flag=bool(getattr(args, "paper_metrics", False)),
                paper_reference=str(getattr(args, "paper_reference", "GEOM_DRUGS")),
                lineageflow_upstream_eval=bool(
                    getattr(args, "lineageflow_upstream_eval", False),
                ),
                kanzi_upstream_eval=bool(
                    getattr(args, "kanzi_upstream_eval", False),
                ),
                flowmol3_upstream_eval=bool(
                    getattr(args, "flowmol3_upstream_eval", False),
                ),
                kanzi_framework_paper_metrics=bool(
                    getattr(args, "kanzi_framework_paper_metrics", False),
                ),
                upstream_n_samples=int(
                    getattr(args, "upstream_n_samples", 1000),
                ),
            )
            cells.append(cell)
            print(
                f"[CELL] model={args.model} seed={seed} nfe={nfe} "
                f"status={cell.get('status')} marker={cell.get('marker')} "
                f"baseline={cell.get('baseline_metric')} "
                f"framework={cell.get('framework_metric')} "
                f"delta_pct={cell.get('delta_pct')}",
                file=sys.stderr,
            )
    report = build_report(
        args.model, seeds, nfe_budgets, cells,
        env_hash=env_hash, n_rounds=int(args.n_rounds),
        force_mode=args.force_mode,
        metric_mode=args.metric_mode,
        restart_min_nfe=args.restart_min_nfe,
        n_molecules=int(args.n_molecules),
    )
    out_json = json.dumps(report, indent=2, sort_keys=False, ensure_ascii=False)
    if args.print_only:
        print(out_json)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(out_json + "\n", encoding="utf-8")
    print(f"[DONE] wrote {args.output} ({report['aggregate']['n_cells']} cells)", file=sys.stderr)
    agg = report["aggregate"]["verdict_overall"]
    if agg in ("RUN_ERROR", "REGRESSION", "EMPTY"):
        return 1
    return 0


__all__ = ["build_argparser", "main"]