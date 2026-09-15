#!/usr/bin/env python3
"""Wave 84 Agent B — Run LineageFlow foldability + self_consistency sweep.

Orchestrates the upstream `run_foldability.py` (which itself calls
`foldability_omegafold.py` + `self_consistency_esmif.py`) on the
N=1000 baseline + framework FASTAs.

Pipeline per arm:
  1. run_foldability.py --fasta <arm.fasta> --outdir <arm>/foldability
       (Stage A: OmegaFold pLDDT, Stage B: ESM-IF scPerplexity)
  2. Parse metrics_summary.json → foldability_pLDDT mean
  3. Parse self_consistency_summary.json → self_consistency_scPerplexity mean

Usage:
    .venvs/omegafold_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py \\
        --baseline-fasta data/lineageflow_n1000/baseline.fasta \\
        --framework-fasta data/lineageflow_n1000/framework.fasta \\
        --output-dir verification_outputs/lineageflow_n1000_omegafold \\
        --max-seqs 1000
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EVAL_DIR = _REPO_ROOT / "data" / "lineageflow_upstream" / "evaluation"


def _run(cmd, **kwargs):
    print(" ".join(cmd))
    return subprocess.run(cmd, **kwargs)


def _parse_summary(outdir: Path) -> dict:
    foldability_summary = outdir / "metrics_summary.json"
    sc_summary = outdir / "self_consistency_summary.json"
    out = {
        "outdir": str(outdir),
        "foldability": None,
        "self_consistency": None,
    }
    if foldability_summary.exists():
        out["foldability"] = json.loads(foldability_summary.read_text())
    if sc_summary.exists():
        out["self_consistency"] = json.loads(sc_summary.read_text())
    return out


def _summarize_arm(arm_name: str, outdir: Path) -> dict:
    s = _parse_summary(outdir)
    fold = s["foldability"] or {}
    sc = s["self_consistency"] or {}
    return {
        "arm": arm_name,
        "outdir": str(outdir),
        "foldability_pLDDT_mean": float(fold.get("plddt_mean_mean", float("nan"))),
        "foldability_pLDDT_median": float(fold.get("plddt_mean_median", float("nan"))),
        "foldability_pLDDT_p10": float(fold.get("plddt_mean_p10", float("nan"))),
        "foldability_pLDDT_p90": float(fold.get("plddt_mean_p90", float("nan"))),
        "foldability_n_total": int(fold.get("n_total", 0)),
        "foldability_n_with_plddt": int(fold.get("n_with_plddt", 0)),
        "self_consistency_scPerplexity_mean": float(sc.get("sc_perplexity_mean", float("nan"))),
        "self_consistency_scPerplexity_median": float(sc.get("sc_perplexity_median", float("nan"))),
        "self_consistency_n_total": int(sc.get("n_total", 0)),
        "self_consistency_n_scored": int(sc.get("n_scored", 0)),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-fasta", type=Path, required=True)
    p.add_argument("--framework-fasta", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--max-seqs", type=int, default=None)
    p.add_argument("--omegafold-bin", type=str, default="omegafold")
    p.add_argument("--skip-fold", action="store_true", help="Skip OmegaFold stage (assume PDBs exist)")
    p.add_argument("--skip-sc", action="store_true", help="Skip self-consistency stage")
    p.add_argument("--plots", action="store_true")
    args = p.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(_EVAL_DIR))
    os.environ.setdefault("PYTHONPATH", str(_EVAL_DIR))

    runner = _EVAL_DIR / "run_foldability.py"
    aggregate: dict = {
        "wave": "84",
        "agent": "B",
        "model": "lineageflow",
        "sweep_target_n_per_arm": int(args.max_seqs) if args.max_seqs else None,
        "omegafold_bin": args.omegafold_bin,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "per_arm": {},
    }

    for arm_name, fasta in [("baseline", args.baseline_fasta), ("framework", args.framework_fasta)]:
        arm_outdir = args.output_dir / arm_name
        arm_outdir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable,
            str(runner),
            "--fasta", str(fasta),
            "--outdir", str(arm_outdir),
            "--omegafold-bin", args.omegafold_bin,
            "--log-every", "60",
        ]
        if args.max_seqs:
            cmd += ["--max-seqs", str(args.max_seqs)]
        if args.skip_fold:
            cmd += ["--skip-fold"]
        if args.skip_sc:
            cmd += ["--skip-sc"]
        if not args.plots:
            cmd += ["--no-plots"]
        t0 = time.time()
        rc = _run(cmd, check=False).returncode
        elapsed = time.time() - t0
        agg = _summarize_arm(arm_name, arm_outdir)
        agg["wallclock_s"] = float(elapsed)
        agg["run_foldability_returncode"] = int(rc)
        aggregate["per_arm"][arm_name] = agg
        print(f"[done] {arm_name}: rc={rc} elapsed={elapsed:.1f}s")
        print(json.dumps(agg, indent=2))

    # Aggregate stats
    f_base = aggregate["per_arm"].get("baseline", {}).get("foldability_pLDDT_mean", float("nan"))
    f_fw = aggregate["per_arm"].get("framework", {}).get("foldability_pLDDT_mean", float("nan"))
    s_base = aggregate["per_arm"].get("baseline", {}).get("self_consistency_scPerplexity_mean", float("nan"))
    s_fw = aggregate["per_arm"].get("framework", {}).get("self_consistency_scPerplexity_mean", float("nan"))

    aggregate["delta"] = {
        "foldability_pLDDT_baseline_minus_framework": float(f_base - f_fw) if (np.isfinite(f_base) and np.isfinite(f_fw)) else float("nan"),
        "self_consistency_scPerplexity_framework_minus_baseline": float(s_fw - s_base) if (np.isfinite(s_base) and np.isfinite(s_fw)) else float("nan"),
    }
    aggregate["verdict"] = (
        "framework_improves_foldability" if aggregate["delta"]["foldability_pLDDT_baseline_minus_framework"] > 0
        else "framework_ties_or_worse_foldability" if np.isfinite(f_base) and np.isfinite(f_fw)
        else "skipped_or_incomplete"
    )

    out_json = args.output_dir / "sweep_summary.json"
    out_json.write_text(json.dumps(aggregate, indent=2))
    print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
