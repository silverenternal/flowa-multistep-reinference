"""GAP-64: consolidated R5c operating-regime census.

Reads every ``sweep_summary.json`` produced by
``scripts/wave191_p3_mnist_sweep.py`` for the MNIST-FM cell (R5c) and prints
one table keyed by the framework's *control axes*:

    beta_total (fresh-noise budget), beta_schedule, restart_t0_mode,
    nfe_allocation, total_nfe, checkpoint, N, seed

The point estimate is always ``fid_headline`` (full 10k reference). The
driver's own ``delta_vs_baseline_pct`` is deliberately **not** used: it is
computed from the 10 x 20-image chunk means, whose Fréchet bias is
arm-dependent and can flip the sign of the delta (see
``tools/gap56_r5c_report.py``).

No GPU, no sampling: this is a pure re-read of recorded artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ARMS = ("cosine", "codimension_sheet", "evidence_driven")


def _row(run: Path) -> dict | None:
    p = run / "sweep_summary.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    base = float(d["baseline_fid"])
    arms = {}
    for a in ARMS:
        v = d.get("framework_arms", {}).get(a)
        if v is None:
            continue
        f = float(v["fid_headline"])
        arms[a] = (f, (f / base - 1.0) * 100.0)
    return {
        "run": run.name,
        "base": base,
        "arms": arms,
        "beta_total": d.get("beta_total"),
        "beta_schedule": d.get("beta_schedule"),
        "t0": d.get("restart_t0_mode"),
        "alloc": d.get("nfe_allocation_mode"),
        "nfe": d.get("nfe"),
        "n": d.get("n_records"),
        "ckpt": Path(str(d.get("checkpoint"))).name,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roots", nargs="+", type=Path, default=[
        Path("verification_outputs/gap56-r5c-memory-t0"),
        Path("verification_outputs/gap64-evidence-allocation"),
    ])
    args = ap.parse_args(argv)

    rows: list[dict] = []
    for root in args.roots:
        if not root.exists():
            continue
        for run in sorted(p for p in root.iterdir() if p.is_dir()):
            r = _row(run)
            if r is not None:
                r["root"] = root.name
                rows.append(r)

    hdr = ("run", "ckpt", "N", "nfe", "beta", "sched", "t0", "alloc",
           "base", "cosi%", "codi%", "evid%")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "|".join(["---"] * len(hdr)) + "|")
    for r in rows:
        cells = [
            r["run"], r["ckpt"] or "?", str(r["n"]), str(r["nfe"]),
            f"{r['beta_total']:.2f}" if isinstance(r["beta_total"], (int, float)) else "?",
            str(r["beta_schedule"]), str(r["t0"]), str(r["alloc"]),
            f"{r['base']:.3f}",
        ]
        for a in ARMS:
            if a in r["arms"]:
                cells.append(f"{r['arms'][a][1]:+.2f}")
            else:
                cells.append("—")
        print("| " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
