"""Score LineageFlow R1 FASTA pairs with the upstream HMMER pipeline.

Thin CLI over :func:`tools.upstream_eval.run_lineageflow_upstream_eval` so an
already-generated FASTA pair can be scored without regenerating samples.
Writes one JSON per arm plus a combined ``upstream_eval.json``.

Usage
-----
    python3 tools/gap55_r1_score_fastas.py \
        --run-dir verification_outputs/gap55-r1-nfe150-n1000/seed42 \
        --length-bias short
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.upstream_eval import run_lineageflow_upstream_eval  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--arms", nargs="+", default=["baseline", "framework"])
    ap.add_argument("--length-bias", choices=("short", "long"), default="short")
    ap.add_argument("--timeout-s", type=int, default=5400)
    ap.add_argument("--metrics", nargs="+", default=["family_validity", "novelty"])
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir).resolve()
    out: dict[str, object] = {
        "run_dir": str(run_dir),
        "length_bias": str(args.length_bias),
        "metrics_requested": list(args.metrics),
        "arms": {},
    }
    for arm in args.arms:
        fasta = run_dir / f"{arm}.fasta"
        if not fasta.exists():
            raise SystemExit(f"missing_fasta:{fasta}")
        outdir = run_dir / f"upstream_{arm}"
        outdir.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        print(f"[score] {arm}: {fasta.name} -> {outdir}", flush=True)
        res = run_lineageflow_upstream_eval(
            fasta_path=fasta,
            output_dir=outdir,
            metrics=tuple(args.metrics),
            timeout_s=int(args.timeout_s),
            length_bias=str(args.length_bias),
        )
        wall = time.perf_counter() - t0
        out["arms"][arm] = {  # type: ignore[index]
            "fasta": str(fasta),
            "wall_s": float(wall),
            "metrics": res,
        }
        print(f"[score] {arm}: status={res.get('status')} wall={wall:.0f}s "
              f"{ {k: v for k, v in res.items() if k != 'status'} }", flush=True)

    path = run_dir / "upstream_eval.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"[score] wrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
