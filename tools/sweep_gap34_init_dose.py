#!/usr/bin/env python3
"""GAP-34 — R1 init-dose-response mechanism experiment.

Motivation
----------

GAP-25 / D-004B-ATTRIBUTION showed the R1 real-forward win is carried by the
**per-record random initial state**, not the multi-round restart-blend (init-only
≈ framework ≫ baseline). That leaves an open question for GAP-34: is the init a
*legitimate, load-bearing* part of the mechanism, or a tool artifact?

This driver runs a **dose-response**: it varies the AA-logit temperature ``tau``
of the per-record init simplex (``softmax(randn * tau)``), holding the
length/family RNG stream and the per-record solver seeds fixed, and measures the
HMMER hit count of the single-pass init-only arm at each ``tau``.

* ``tau <= 0`` → canonical near-uniform init (the D-004 collapse anchor);
* ``tau = 1`` → the canonical D-004b ``softmax(randn)`` convention;
* ``tau > 1`` → a sharper (lower-entropy) per-record init.

Either a monotone rise in hits with ``tau``, or an interior optimum with
``tau = 0`` reproducing the collapse, means the init is a **load-bearing causal
knob** and the win is **model-mediated** (without the model, a random init could
not raise family-consistent hits) — i.e. a legitimate framework component (the
restart step must supply per-record diversity, which the near-uniform canonical
init cannot). Both extremes (too uniform, too peaked) collapsing would make the
init an *interior*-optimum knob rather than a monotone one; the observed shape is
reported as-is by ``tools/gap34_dose_analysis.py``.

The per-family adapters are built **once per seed** and reused across ``tau`` so
the model loads once per seed, not once per cell.

Usage
-----

    .venvs/lineageflow_venv/bin/python tools/sweep_gap34_init_dose.py \
        --outdir verification_outputs/gap34-r1-init-dose \
        --taus 0.0 0.25 0.5 1.0 2.0 --seeds 42 43 44 --n 1000 --nfe 10

Writes ``dose_response.json`` + ``dose_response.csv`` and per-(tau,seed) dirs.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

HMMSCAN = "/home/hugo/hmmer_build/bin/hmmscan"
PFAM = REPO_ROOT / "data" / "lineageflow_upstream" / "databases" / "pfam35" / "Pfam-A.hmm"

#: Canonical baseline totals (arm A) for the same seeds — from
#: verification_outputs/r1_3seed_d004b_q4_2026 (byte-stable).
BASELINE_TOTALS = {42: 158, 43: 159, 44: 174}


def _count_hits(tblout: Path) -> int:
    return sum(1 for ln in tblout.read_text().splitlines() if ln and not ln.startswith("#"))


def _hmmer(fasta: Path, tblout: Path) -> int:
    cmd = [
        HMMSCAN, "--noali", "--cpu", "32", "--tblout", str(tblout), "--acc",
        str(PFAM), str(fasta),
    ]
    print(f"[hmmer] {fasta}", flush=True)
    with tblout.open("w") as fh:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=fh)
    return _count_hits(tblout)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outdir", type=Path,
                    default=REPO_ROOT / "verification_outputs" / "gap34-r1-init-dose")
    ap.add_argument("--taus", type=float, nargs="+", default=[0.0, 0.25, 0.5, 1.0, 2.0])
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--nfe", type=int, default=10)
    ap.add_argument("--min-len", type=int, default=30)
    ap.add_argument("--max-len", type=int, default=150)
    ap.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Skip (tau, seed) cells whose FASTA and HMMER tblout already exist, "
            "reusing their hit counts. Useful after a partial run."
        ),
    )
    args = ap.parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)

    from tools.gen_lineageflow_n1000_fastas import FAMILY_PROFILES
    from tools.r1_d004b_attribution import _build_adapter, generate_init_only

    family_ids = list(FAMILY_PROFILES.keys())

    rows: list[dict] = []
    t0 = time.perf_counter()
    for seed in args.seeds:
        # Build the per-family adapters once and reuse across tau (model loads once).
        adapters = {fam: _build_adapter(fam, int(seed), int(args.nfe)) for fam in family_ids}
        for tau in args.taus:
            cell = args.outdir / f"tau{tau:g}" / f"seed{seed}"
            fasta = cell / "init_only.fasta"
            tbl = cell / "init_only_hits.tbl"
            if args.resume and fasta.exists() and tbl.exists():
                hits = _count_hits(tbl)
                print(f"  [resume] tau={tau} seed={seed}: {hits} hits", flush=True)
            else:
                generate_init_only(
                    cell, n=int(args.n), seed=int(seed), nfe=int(args.nfe),
                    min_len=int(args.min_len), max_len=int(args.max_len),
                    init_source="random-simplex", init_tau=float(tau),
                    adapters=adapters,
                )
                hits = _hmmer(fasta, tbl)
            rows.append({
                "tau": float(tau),
                "seed": int(seed),
                "hits": int(hits),
                "baseline_hits": int(BASELINE_TOTALS.get(int(seed), -1)),
                "delta_vs_baseline": int(hits) - int(BASELINE_TOTALS.get(int(seed), 0)),
                "n": int(args.n),
                "nfe": int(args.nfe),
            })
            print(f"  tau={tau} seed={seed}: {hits} hits "
                  f"(baseline {BASELINE_TOTALS.get(int(seed))})", flush=True)

    # Per-tau aggregation.
    agg = []
    for tau in args.taus:
        rs = [r for r in rows if r["tau"] == float(tau)]
        mean_hits = sum(r["hits"] for r in rs) / len(rs)
        mean_delta = sum(r["delta_vs_baseline"] for r in rs) / len(rs)
        agg.append({
            "tau": float(tau),
            "mean_hits": mean_hits,
            "mean_delta_vs_baseline": mean_delta,
            "per_seed_hits": {r["seed"]: r["hits"] for r in rs},
        })

    wall_s = round(time.perf_counter() - t0, 1)
    payload = {
        "kind": "gap34_r1_init_dose",
        "taus": [float(t) for t in args.taus],
        "seeds": [int(s) for s in args.seeds],
        "n_per_seed": int(args.n),
        "nfe": int(args.nfe),
        "baseline_totals": BASELINE_TOTALS,
        "rows": rows,
        "aggregate": agg,
        "wall_s": wall_s,
        "note": (
            "Single-pass init-only arm; tau is the AA-logit temperature of the "
            "per-record softmax(randn*tau) init. tau<=0 = canonical near-uniform "
            "(D-004 collapse anchor); tau=1 = canonical D-004b."
        ),
    }
    (args.outdir / "dose_response.json").write_text(json.dumps(payload, indent=2))
    with (args.outdir / "dose_response.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\n=== dose-response (mean hits over seeds) ===")
    for a in agg:
        print(f"  tau={a['tau']:<5g} mean_hits={a['mean_hits']:.1f} "
              f"mean_delta_vs_baseline={a['mean_delta_vs_baseline']:+.1f}")
    print(f"\nwrote {args.outdir / 'dose_response.json'} (wall {wall_s}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
