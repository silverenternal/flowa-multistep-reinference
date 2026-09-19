#!/usr/bin/env python3
"""Wave 197 P2 — Eval driver for n=100 FASTAs (parallelized across 2 GPUs).

Reuses Wave 196 P2's eval logic but reads from /tmp/w197/track_b/fastas/ and
writes to /tmp/w197/track_b/eval/. Runs cells in parallel across 2 GPUs.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
LINEAGEFLOW_EVAL_DIR = REPO_ROOT / "data" / "lineageflow_upstream"
EVAL_BIN_PYTHON = "/home/hugo/.conda/envs/omegafold_py310/bin/python"
OMEGAFOLD_BIN = "/home/hugo/.conda/envs/omegafold_py310/bin/omegafold"

FASTAS_DIR = Path("/tmp/w197/track_b/fastas")
EVAL_DIR = Path("/tmp/w197/track_b/eval")
LOGS_DIR = Path("/tmp/w197/track_b/logs")


def fasta_path_for(arm: str, nfe: int, seed: int) -> Path:
    if arm == "flowa":
        return FASTAS_DIR / f"flowa_nfe{nfe}_seed{seed}" / "framework.fasta"
    return FASTAS_DIR / f"{arm}_lineageflow_nfe{nfe}_seed{seed}.fasta"


def eval_outdir_for(arm: str, nfe: int, seed: int) -> Path:
    return EVAL_DIR / f"{arm}_nfe{nfe}_seed{seed}"


def run_eval_cell(arm: str, nfe: int, seed: int, gpu: str, max_seqs: int) -> dict:
    fasta = fasta_path_for(arm, nfe, seed)
    outdir = eval_outdir_for(arm, nfe, seed)
    summary = outdir / "summary.json"
    if summary.exists():
        try:
            d = json.loads(summary.read_text())
            f = d.get("foldability", {})
            return {
                "arm": arm, "nfe": nfe, "seed": seed, "gpu": gpu,
                "status": "cached",
                "plddt_mean": f.get("plddt_mean_mean"),
                "sc_perplexity_mean": f.get("sc_perplexity_mean"),
            }
        except Exception:
            pass
    if not fasta.exists():
        return {"arm": arm, "nfe": nfe, "seed": seed, "status": "no_fasta"}
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"eval_{arm}_nfe{nfe}_seed{seed}.log"
    cmd = [
        EVAL_BIN_PYTHON,
        str(LINEAGEFLOW_EVAL_DIR / "evaluation/evaluate_all.py"),
        "--fasta", str(fasta),
        "--outdir", str(outdir),
        "--metrics", "foldability", "self_consistency",
        "--max-seqs", str(max_seqs),
        "--fold-gpus", gpu,
        "--sc-gpus", gpu,
        "--omegafold-bin", OMEGAFOLD_BIN,
        "--no-plots",
    ]
    env = os.environ.copy()
    env["PATH"] = f"/home/hugo/.conda/envs/omegafold_py310/bin:{env.get('PATH', '')}"
    t0 = time.time()
    with log_path.open("w") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        rc = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    wall = time.time() - t0
    if rc != 0 or not summary.exists():
        return {"arm": arm, "nfe": nfe, "seed": seed, "gpu": gpu,
                "status": "fail", "rc": rc, "wall_s": wall}
    d = json.loads(summary.read_text())
    f = d.get("foldability", {})
    return {
        "arm": arm, "nfe": nfe, "seed": seed, "gpu": gpu,
        "status": "ok", "wall_s": wall,
        "plddt_mean": f.get("plddt_mean_mean"),
        "sc_perplexity_mean": f.get("sc_perplexity_mean"),
        "n_records": f.get("n_total"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--arms", nargs="+", default=["vanilla", "fastdllm", "abcache", "lediflow", "flowa"])
    p.add_argument("--nfe", nargs="+", type=int, default=[50, 100])
    p.add_argument("--seeds", nargs="+", type=int, default=list(range(42, 72)))
    p.add_argument("--max-seqs", type=int, default=100)
    p.add_argument("--workers-per-gpu", type=int, default=1)
    p.add_argument("--gpus", default="0,1")
    args = p.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    gpus = args.gpus.split(",")
    cells = [(arm, nfe, seed) for arm in args.arms for nfe in args.nfe for seed in args.seeds]
    print(f"Total cells: {len(cells)} (gpus={gpus}, workers_per_gpu={args.workers_per_gpu}, max_seqs={args.max_seqs})")

    t0 = time.time()
    cell_idx = 0
    failed = 0
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(gpus) * args.workers_per_gpu) as exe:
        futures = {}
        for arm, nfe, seed in cells:
            gpu = gpus[(cell_idx // args.workers_per_gpu) % len(gpus)] if args.workers_per_gpu > 1 else gpus[cell_idx % len(gpus)]
            f = exe.submit(run_eval_cell, arm, nfe, seed, gpu, args.max_seqs)
            futures[f] = (arm, nfe, seed, gpu)
            cell_idx += 1
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            results.append(r)
            if r["status"] not in ("ok", "cached"):
                failed += 1
            if r.get("plddt_mean") is not None:
                print(f"[{len(results)}/{len(cells)}] {r['arm']} nfe={r['nfe']} seed={r['seed']} "
                      f"gpu={r.get('gpu')} status={r['status']} "
                      f"plddt={r.get('plddt_mean', 'nan'):.3f} "
                      f"scperp={r.get('sc_perplexity_mean', 'nan'):.3f}")
            else:
                print(f"[{len(results)}/{len(cells)}] {r['arm']} nfe={r['nfe']} seed={r['seed']} "
                      f"status={r['status']}")
    wall_total = time.time() - t0
    print(f"\nDONE: {len(cells) - failed}/{len(cells)} cells in {wall_total:.1f}s ({wall_total/60:.1f} min)")
    print(f"FAILED: {failed}")
    results_path = EVAL_DIR / "eval_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    print(f"Results written to {results_path}")


if __name__ == "__main__":
    main()