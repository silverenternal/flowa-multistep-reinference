#!/usr/bin/env python3
"""Wave 197 P2 — Parallelized FASTA generation at n=100 records/seed.

Uses ThreadPoolExecutor (subprocess releases GIL, so this gives true parallelism)
to fan out across cells. Each cell is a subprocess invocation of the per-arm
gen script; cells are independent so workers can be saturated.

Outputs FASTAs to /tmp/w197/track_b/fastas/ for:
- 4 baseline arms: vanilla, fastdllm, abcache, lediflow
- 1 framework arm: flowa (FlowA multi-round restart-blend)
- NFE ∈ {50, 100}
- seeds 42..71 (30 seeds)
- n=100 records per seed (10× Wave 196 P2's n=30)

Wall time per cell (from P1 estimate at n=100):
- fastdllm NFE=50: ~21 s; NFE=100: ~930 s
- abcache NFE=50: ~55 s; NFE=100: ~94 s
- lediflow NFE=50: ~219 s; NFE=100: ~166 s
- flowa NFE=50: ~470 s; NFE=100: ~920 s
- vanilla NFE=50/100: ~30 s
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
PYTHON_BIN = "/home/hugo/codes/flowa-multistep-reinference/.venvs/lineageflow_venv/bin/python"

ARMS = ["vanilla", "fastdllm", "abcache", "lediflow", "flowa"]
NFES = [50, 100]
SEEDS = list(range(42, 72))
N_RECORDS_PER_SEED = 100
MIN_LEN = 30
MAX_LEN = 150


def gen_fastdllm_fasta(outdir: Path, nfe: int, seed: int, n: int, log_dir: Path) -> Path:
    fasta = outdir / f"fastdllm_lineageflow_nfe{nfe}_seed{seed}.fasta"
    if fasta.exists() and fasta.stat().st_size > 0:
        return fasta
    cmd = [
        PYTHON_BIN, str(REPO_ROOT / "tools/w180_gen_fastdllm_fastas.py"),
        "--outdir", str(outdir),
        "--n", str(n),
        "--seed", str(seed),
        "--nfe", str(nfe),
        "--min-len", str(MIN_LEN),
        "--max-len", str(MAX_LEN),
    ]
    log = log_dir / f"gen_fastdllm_nfe{nfe}_seed{seed}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=False)
    return fasta


def gen_abcache_fasta(outdir: Path, nfe: int, seed: int, n: int, log_dir: Path) -> Path:
    fasta = outdir / f"abcache_lineageflow_nfe{nfe}_seed{seed}.fasta"
    if fasta.exists() and fasta.stat().st_size > 0:
        return fasta
    cmd = [
        PYTHON_BIN, str(REPO_ROOT / "tools/w181_gen_abcache_fastas.py"),
        "--outdir", str(outdir),
        "--n", str(n),
        "--seed", str(seed),
        "--nfe", str(nfe),
        "--min-len", str(MIN_LEN),
        "--max-len", str(MAX_LEN),
    ]
    log = log_dir / f"gen_abcache_nfe{nfe}_seed{seed}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=False)
    return fasta


def gen_lediflow_fasta(outdir: Path, nfe: int, seed: int, n: int, log_dir: Path) -> Path:
    fasta = outdir / f"lediflow_lineageflow_nfe{nfe}_seed{seed}.fasta"
    if fasta.exists() and fasta.stat().st_size > 0:
        return fasta
    cmd = [
        PYTHON_BIN, str(REPO_ROOT / "tools/w182_gen_lediflow_fastas.py"),
        "--outdir", str(outdir),
        "--n", str(n),
        "--seed", str(seed),
        "--nfe", str(nfe),
        "--min-len", str(MIN_LEN),
        "--max-len", str(MAX_LEN),
    ]
    log = log_dir / f"gen_lediflow_nfe{nfe}_seed{seed}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=False)
    return fasta


def gen_vanilla_fasta(outdir: Path, nfe: int, seed: int, n: int, log_dir: Path) -> Path:
    """Bare RNG draws over each family's Pfam AA bias. NFE-independent (in-process)."""
    fasta = outdir / f"vanilla_lineageflow_nfe{nfe}_seed{seed}.fasta"
    if fasta.exists() and fasta.stat().st_size > 0:
        return fasta

    AA_SET = "ACDEFGHIKLMNPQRSTVWY"
    FAMILY_PROFILES = {
        "PF00005.27": {"bias": {"A": 0.10, "L": 0.12, "V": 0.10, "G": 0.10, "I": 0.08, "S": 0.07, "K": 0.06, "T": 0.06}},
        "PF00072.24": {"bias": {"D": 0.12, "E": 0.10, "L": 0.08, "V": 0.08, "A": 0.08, "K": 0.07, "T": 0.07, "G": 0.07}},
        "PF00183.19": {"bias": {"L": 0.10, "E": 0.10, "V": 0.08, "K": 0.08, "A": 0.08, "G": 0.07, "D": 0.07, "I": 0.06}},
        "PF02517.18": {"bias": {"E": 0.14, "K": 0.12, "A": 0.10, "D": 0.08, "L": 0.07, "G": 0.07, "V": 0.06, "T": 0.06}},
    }
    family_ids = list(FAMILY_PROFILES.keys())
    rng = random.Random(int(seed))
    fasta.parent.mkdir(parents=True, exist_ok=True)
    with fasta.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = rng.randint(MIN_LEN, MAX_LEN)
            bias = FAMILY_PROFILES[family_id]["bias"]
            pairs = []
            for aa in AA_SET:
                w = bias.get(aa, 1.0)
                pairs.append((aa, float(w)))
            total = sum(w for _, w in pairs)
            weights = [w / total for _, w in pairs]
            aas = [aa for aa, _ in pairs]
            seq = "".join(rng.choices(aas, weights=weights, k=length))
            f.write(f">vanilla_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
    return fasta


def gen_flowa_fasta(outdir: Path, nfe: int, seed: int, n: int, log_dir: Path) -> Path:
    """FlowA framework arm: --n-rounds 3 restart-blend."""
    cell_dir = outdir / f"flowa_nfe{nfe}_seed{seed}"
    fasta = cell_dir / "framework.fasta"
    if fasta.exists() and fasta.stat().st_size > 0:
        return fasta
    cmd = [
        PYTHON_BIN, str(REPO_ROOT / "tools/gen_lineageflow_n1000_fastas.py"),
        "--outdir", str(cell_dir),
        "--n", str(n),
        "--seed", str(seed),
        "--nfe", str(nfe),
        "--n-rounds", "3",
        "--temperature", "1.0",
        "--min-len", str(MIN_LEN),
        "--max-len", str(MAX_LEN),
    ]
    log = log_dir / f"gen_flowa_nfe{nfe}_seed{seed}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=False)
    return fasta


def gen_one_cell(arm: str, nfe: int, seed: int, n: int, outdir: Path, log_dir: Path) -> tuple:
    """Gen one (arm, nfe, seed) cell. Returns (arm, nfe, seed, ok, wall)."""
    t0 = time.time()
    try:
        if arm == "vanilla":
            f = gen_vanilla_fasta(outdir, nfe, seed, n, log_dir)
        elif arm == "fastdllm":
            f = gen_fastdllm_fasta(outdir, nfe, seed, n, log_dir)
        elif arm == "abcache":
            f = gen_abcache_fasta(outdir, nfe, seed, n, log_dir)
        elif arm == "lediflow":
            f = gen_lediflow_fasta(outdir, nfe, seed, n, log_dir)
        elif arm == "flowa":
            f = gen_flowa_fasta(outdir, nfe, seed, n, log_dir)
        else:
            return (arm, nfe, seed, False, 0.0)
        wall = time.time() - t0
        ok = f.exists() and f.stat().st_size > 0
        return (arm, nfe, seed, ok, wall)
    except Exception as e:
        wall = time.time() - t0
        print(f"[error] {arm} nfe={nfe} seed={seed}: {e}", file=sys.stderr)
        return (arm, nfe, seed, False, wall)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path, default=Path("/tmp/w197/track_b/fastas"))
    p.add_argument("--log-dir", type=Path, default=Path("/tmp/w197/track_b/logs"))
    p.add_argument("--n-records", type=int, default=N_RECORDS_PER_SEED)
    p.add_argument("--nfe", type=int, nargs="+", default=NFES)
    p.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    p.add_argument("--arms", type=str, nargs="+", default=ARMS)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--progress-json", type=Path, default=Path("/tmp/w197/track_b/progress.json"))
    args = p.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.log_dir.mkdir(parents=True, exist_ok=True)

    cells = [
        (arm, nfe, seed, args.n_records, args.outdir, args.log_dir)
        for arm in args.arms
        for nfe in args.nfe
        for seed in args.seeds
    ]
    total = len(cells)
    print(f"Total cells: {total} (arms={args.arms}, nfe={args.nfe}, seeds={len(args.seeds)}, workers={args.workers})")

    progress = {
        "started_at": time.time(),
        "total_cells": total,
        "completed": 0,
        "failed": 0,
        "wall_min": 0.0,
        "cells_completed": [],
    }

    t_total = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as exe:
        futures = {
            exe.submit(gen_one_cell, arm, nfe, seed, n, args.outdir, args.log_dir): (arm, nfe, seed)
            for arm, nfe, seed, n, _, _ in cells
        }
        for fut in as_completed(futures):
            arm, nfe, seed, ok, wall = fut.result()
            progress["completed"] += 1
            if not ok:
                progress["failed"] += 1
            progress["cells_completed"].append({
                "arm": arm, "nfe": nfe, "seed": seed,
                "ok": ok, "wall_s": wall,
            })
            progress["wall_min"] = (time.time() - t_total) / 60.0
            if progress["completed"] % 5 == 0 or progress["completed"] == total:
                ckpt = {**progress, "cells_completed": progress["cells_completed"][-30:]}
                args.progress_json.write_text(json.dumps(ckpt, indent=2))
                rate = progress["completed"] / max(0.001, progress["wall_min"])
                eta_min = (total - progress["completed"]) / max(0.001, rate)
                print(
                    f"[{progress['completed']}/{total}] "
                    f"last={arm}/nfe{nfe}/seed{seed} ok={ok} wall={wall:.1f}s | "
                    f"elapsed={progress['wall_min']:.1f}min rate={rate:.2f}/min ETA={eta_min:.0f}min",
                    flush=True,
                )

    wall_total = time.time() - t_total
    print(f"\nDONE: {total - progress['failed']}/{total} cells in {wall_total:.1f}s ({wall_total/60:.1f} min)")
    print(f"FAILED: {progress['failed']}")
    args.progress_json.write_text(json.dumps(progress, indent=2))


if __name__ == "__main__":
    main()
