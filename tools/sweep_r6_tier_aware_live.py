#!/usr/bin/env python3
"""GAP-01 R6 tier-aware live sweep driver (3 seeds x N=1000, cuda:0 ONLY).

Materializes the Wave 225 P4 / Wave 233 P3 k6 tier-aware counterfactual as a
real in-loop scheduler choice (the ``--tier-aware-n-cap 0.5`` flag now takes
effect on the LineageFlow constant-β path; see
``docs/audit/gap01-r6-live-wiring.md``).

Per seed in {42, 43, 44}:

  1. Generate baseline + framework FASTA (N=1000, ``--upstream-eval-len-bias
     short`` 30-150 AA, ``--nfe 10 --n-rounds 3 --temperature 1.0``) with the
     tier-aware reduction active. The baseline arm is bare-RNG and is verified
     byte-identical to the frozen Wave 161 baseline (so the frozen baseline
     folds are reusable).
  2. Fold ONLY the framework arm with OmegaFold on cuda:0 (``--skip-sc``;
     the ESM-IF self-consistency stage is out of scope for the pLDDT
     acceptance).
  3. Pair the fresh framework pLDDT against the frozen Wave 161 baseline
     pLDDT by ``qid``.

Aggregation: per-seed + pooled per-record paired Cohen's ``d_z`` (framework
minus baseline), plus per-tier (hard / medium / easy, frozen 34.56 / 46.13
boundaries) decomposition.

HARD CONSTRAINT: cuda:0 ONLY (user directive "只能用GPU0"). The driver pins
``CUDA_VISIBLE_DEVICES=0`` on every subprocess.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
FROZEN_BASELINE = (
    REPO
    / "verification_outputs/k6_foldability_n1000_w161_q3_2026"
    / "baseline/foldability/foldability.jsonl"
)
FROZEN_BASELINE_FASTA = (
    REPO
    / "verification_outputs/k6_foldability_n1000_w161_q3_2026"
    / "baseline/foldability/queries.fasta"
)
GEN = REPO / "tools/gen_lineageflow_n1000_fastas.py"
RUN_FOLD = REPO / "data/lineageflow_upstream/evaluation/run_foldability.py"
LIN_VENV = REPO / ".venvs/lineageflow_venv/bin/python"
OMEGAFOLD_PY = Path("/home/hugo/.conda/envs/omegafold_py310/bin/python")
OMEGAFOLD_BIN = "/home/hugo/.conda/envs/omegafold_py310/bin/omegafold"

TIER_LOW = 34.560125471956226
TIER_HIGH = 46.129279241102346


def _read_fasta(path: Path) -> dict[str, str]:
    d: dict[str, str] = {}
    h = None
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            h = line[1:]
            d[h] = ""
        elif h is not None:
            d[h] += line
    return d


def _load_jsonl(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        out[str(r["qid"])] = float(r["plddt_mean"])
    return out


def _run(cmd: list[str], *, env: dict[str, str], log: Path) -> int:
    print(" ".join(cmd), flush=True)
    with log.open("a") as fh:
        fh.write(" ".join(cmd) + "\n")
        proc = subprocess.run(cmd, env=env, stdout=fh, stderr=subprocess.STDOUT)
    return int(proc.returncode)


def _paired(b: np.ndarray, f: np.ndarray) -> dict[str, float]:
    diff = f - b
    n = int(len(diff))
    if n < 2:
        return {"n": n, "mean_diff": float("nan"), "d_z": float("nan")}
    sd = float(np.std(diff, ddof=1))
    md = float(np.mean(diff))
    return {
        "n": n,
        "mean_baseline": float(np.mean(b)),
        "mean_framework": float(np.mean(f)),
        "mean_diff": md,
        "sd_diff": sd,
        "cohens_d_z": md / sd if sd > 0 else float("nan"),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", type=Path,
                   default=REPO / "verification_outputs/gap01-r6-tier-aware-live")
    p.add_argument("--seeds", type=str, default="42,43,44")
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--tier-aware-n-cap", type=float, default=0.5)
    p.add_argument("--gpu", type=str, default="0")
    p.add_argument("--skip-generate", action="store_true")
    p.add_argument("--skip-fold", action="store_true")
    args = p.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    base_plddt = _load_jsonl(FROZEN_BASELINE)
    print(f"frozen baseline records: {len(base_plddt)}")

    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env["PYTHONPATH"] = str(REPO)

    results: dict[str, dict] = {}
    for seed in seeds:
        sdir = outdir / f"seed{seed}"
        sdir.mkdir(parents=True, exist_ok=True)
        log = sdir / "sweep.log"

        # ---- 1. generate FASTA ----
        if not args.skip_generate:
            cmd = [
                str(LIN_VENV), str(GEN),
                "--outdir", str(sdir / "fasta"),
                "--n", str(args.n), "--seed", str(seed),
                "--upstream-eval-len-bias", "short",
                "--nfe", "10", "--n-rounds", "3", "--temperature", "1.0",
                "--tier-aware-n-cap", str(args.tier_aware_n_cap),
                "--tier-aware-baseline-metrics-jsonl", str(FROZEN_BASELINE),
            ]
            rc = _run(cmd, env=env, log=log)
            if rc != 0:
                print(f"[seed {seed}] generation failed rc={rc}")
                return 1

        # ---- verify baseline byte-identity vs frozen ----
        new_base = _read_fasta(sdir / "fasta" / "baseline.fasta")
        frozen_base = _read_fasta(FROZEN_BASELINE_FASTA)
        fseq = list(frozen_base.values())
        nseq = list(new_base.values())
        base_identical = (len(fseq) == len(nseq) and fseq == nseq)
        print(f"[seed {seed}] baseline byte-identical to frozen: {base_identical}")

        # ---- 2. fold framework arm ----
        fw_fold_dir = sdir / "framework" / "foldability"
        if not args.skip_fold:
            cmd = [
                str(OMEGAFOLD_PY), str(RUN_FOLD),
                "--fasta", str(sdir / "fasta" / "framework.fasta"),
                "--outdir", str(fw_fold_dir),
                "--omegafold-bin", OMEGAFOLD_BIN,
                "--fold-gpus", str(args.gpu), "--sc-gpus", str(args.gpu),
                "--max-seqs", str(args.n),
                "--skip-sc", "--no-plots", "--log-every", "60",
            ]
            rc = _run(cmd, env=env, log=log)
            if rc != 0:
                print(f"[seed {seed}] fold failed rc={rc}")
                return 1

        fw_plddt = _load_jsonl(fw_fold_dir / "foldability.jsonl")
        common = sorted(set(base_plddt) & set(fw_plddt),
                        key=lambda q: int(q[1:]))
        b = np.array([base_plddt[q] for q in common], dtype=float)
        f = np.array([fw_plddt[q] for q in common], dtype=float)
        res = _paired(b, f)
        res["seed"] = seed
        res["baseline_byte_identical"] = bool(base_identical)
        res["n_framework_folded"] = int(len(fw_plddt))
        res["tier_aware_n_cap"] = float(args.tier_aware_n_cap)

        # per-tier
        tiers = {}
        for label, mask in (
            ("hard", b <= TIER_LOW),
            ("medium", (b > TIER_LOW) & (b <= TIER_HIGH)),
            ("easy", b > TIER_HIGH),
        ):
            tiers[label] = _paired(b[mask], f[mask])
        res["per_tier"] = tiers
        results[str(seed)] = res
        print(f"[seed {seed}] d_z={res['cohens_d_z']:+.4f} "
              f"mean_diff={res['mean_diff']:+.4f} n={res['n']}")

    # ---- pooled ----
    all_b, all_f = [], []
    for seed in seeds:
        sdir = outdir / f"seed{seed}"
        fw_plddt = _load_jsonl(sdir / "framework" / "foldability" / "foldability.jsonl")
        common = sorted(set(base_plddt) & set(fw_plddt), key=lambda q: int(q[1:]))
        all_b.extend(base_plddt[q] for q in common)
        all_f.extend(fw_plddt[q] for q in common)
    pooled = _paired(np.array(all_b), np.array(all_f))

    summary = {
        "kind": "gap01_r6_tier_aware_live_sweep",
        "seeds": seeds,
        "n_per_seed": int(args.n),
        "tier_aware_n_cap": float(args.tier_aware_n_cap),
        "gpu": str(args.gpu),
        "baseline_source": str(FROZEN_BASELINE.relative_to(REPO)),
        "per_seed": results,
        "pooled": pooled,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (outdir / "sweep_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\npooled d_z = {pooled['cohens_d_z']:+.4f} "
          f"(n={pooled['n']}, mean_diff={pooled['mean_diff']:+.4f})")
    print(f"wrote {outdir / 'sweep_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
