#!/usr/bin/env python3
"""GAP-84 — turn the MNIST grid cells into a ``frontier_input_v1`` spec.

Input: the per-cell `sweep_summary.json` files written by
`reproduce/gap84_mnist_frontier.sh` (one directory per checkpoint, seed, NFE).

Output: one spec per (checkpoint, framework arm), ready for
`tools/frontier_report.py`.

Pairing unit is the **seed**. The artifact carries chunk-level FIDs too, but a
chunk FID is on a different scale from the headline FID (e.g. 30.9 vs 21.4 on
`w16e1_5k` at NFE=50), and `frontier_report` divides the unit-level CI by the
headline baseline value. Mixing the two would make the delta and its CI disagree
by ~30 %, so the seed-level headline values are the only self-consistent unit
here. `n_units = 3` is reported as such, per §0.3.

Usage
-----
    python3 tools/gap84_mnist_frontier_input.py \
        --root verification_outputs/gap84-mnist-frontier \
        --ckpt w16e1_5k --arm evidence_driven \
        --out verification_outputs/gap84-mnist-frontier/frontier_input_w16e1_5k_evidence_driven.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "frontier_input_v1"


def cell_paths(root: Path, ckpt: str) -> dict[int, dict[int, Path]]:
    """``{nfe: {seed: path}}`` for one checkpoint, read off the directory names."""
    out: dict[int, dict[int, Path]] = {}
    for d in sorted(root.glob(f"{ckpt}_nfe*_s*")):
        name = d.name
        try:
            head, seed_part = name.rsplit("_s", 1)
            nfe = int(head.rsplit("_nfe", 1)[1])
            seed = int(seed_part)
        except (IndexError, ValueError):
            continue
        summary = d / "sweep_summary.json"
        if summary.exists():
            out.setdefault(nfe, {})[seed] = summary
    return out


def collect(root: Path, ckpt: str, arm: str) -> dict:
    by_rung = cell_paths(root, ckpt)
    if not by_rung:
        raise SystemExit(f"no_cells:{root}/{ckpt}_nfe*_s*")

    grid = sorted(by_rung)
    n_records: int | None = None
    baseline: dict[str, dict] = {}
    framework: dict[str, dict] = {}
    per_seed: dict[str, dict] = {}
    missing: list[int] = []

    seeds_all = sorted({s for r in by_rung.values() for s in r})
    for nfe in grid:
        seeds_here = by_rung[nfe]
        if sorted(seeds_here) != seeds_all:
            missing.append(nfe)
            continue
        b_vals, f_vals = [], []
        for seed in seeds_all:
            spec = json.loads(seeds_here[seed].read_text())
            if arm not in spec.get("framework_arms", {}):
                raise SystemExit(f"arm_missing:{arm} in {seeds_here[seed]}")
            if n_records is None:
                n_records = int(spec["n_records"])
            elif int(spec["n_records"]) != n_records:
                raise SystemExit(f"n_records_mismatch:{seeds_here[seed]}")
            b_vals.append(float(spec["baseline_fid"]))
            f_vals.append(float(spec["framework_arms"][arm]["fid_headline"]))
        baseline[str(nfe)] = {"value": sum(b_vals) / len(b_vals), "units": b_vals}
        framework[str(nfe)] = {"value": sum(f_vals) / len(f_vals), "units": f_vals}
        per_seed[str(nfe)] = {
            str(s): {"baseline": b, "framework": f}
            for s, b, f in zip(seeds_all, b_vals, f_vals, strict=True)
        }

    return {
        "schema": SCHEMA,
        "model": "mnist_fm",
        "cell": "R5c",
        "checkpoint": ckpt,
        "framework_arm": arm,
        "metric": {"name": "projection_fid", "direction": "lower_is_better"},
        "n_records": int(n_records or 0),
        "grid": grid,
        "units_kind": "seed",
        "seeds": seeds_all,
        "baseline": baseline,
        "framework": framework,
        "per_seed": per_seed,
        "missing_rungs": missing,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--arm", default="evidence_driven")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    spec = collect(args.root, args.ckpt, args.arm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(spec, indent=2) + "\n")
    print(json.dumps({
        "grid": spec["grid"],
        "n_records": spec["n_records"],
        "units_kind": spec["units_kind"],
        "seeds": spec["seeds"],
        "missing_rungs": spec["missing_rungs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
