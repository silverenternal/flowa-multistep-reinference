#!/usr/bin/env python3
"""GAP-27 — correct the seed-level 95% CI in the committed R3 paired JSONs.

`scripts/wave338_p5_r3_n1000_paired.py` computed the paired-summary CI with a
hard-coded normal multiplier 1.96 while reporting ``df = n_seeds - 1``. At the
canonical n = 3 seeds (df = 2) the correct t multiplier is 4.303, so the
recorded CI was ~2.2x too narrow. This tool re-derives the CI from the recorded
``mean_diff`` / ``se_diff`` / ``df`` (no GPU, no re-run) and rewrites the
``ci_95_low`` / ``ci_95_high`` fields, adding ``ci_95_t_crit``. The point
estimate, t, p and verdict are untouched.

Usage:  python tools/r3_reaggregate_paired_ci.py [paths...]
Default paths: the three committed R3 paired JSONs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import scipy.stats

REPO = Path(__file__).resolve().parent.parent

DEFAULT_PATHS = [
    "verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.json",
    "verification_outputs/gap12-r3-tuned-baseline-nfe500/wave338-p5-r3-n1000-paired.json",
    "verification_outputs/gap12-r3-tuned-baseline-nfe1000/wave338-p5-r3-n1000-paired.json",
]


def _fix(path: Path) -> dict:
    d = json.loads(path.read_text())
    ps = d.get("paired_summary")
    if not ps:
        return {"path": str(path), "status": "no paired_summary"}
    mean = ps["mean_diff"]
    se = ps["se_diff"]
    df = ps["df"]
    old = (ps.get("ci_95_low"), ps.get("ci_95_high"))
    t_crit = float(scipy.stats.t.ppf(0.975, df=df)) if df > 0 else float("nan")
    ps["ci_95_low"] = mean - t_crit * se
    ps["ci_95_high"] = mean + t_crit * se
    ps["ci_95_t_crit"] = t_crit
    ps["ci_95_note"] = (
        "Corrected (GAP-27): t multiplier for df = n_seeds - 1 "
        f"({t_crit:.4f}); the earlier value used a normal 1.96 multiplier."
    )
    path.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(path.relative_to(REPO)),
        "df": df,
        "t_crit": t_crit,
        "ci_old": list(old),
        "ci_new": [ps["ci_95_low"], ps["ci_95_high"]],
    }


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] if argv else [REPO / p for p in DEFAULT_PATHS]
    for p in paths:
        print(json.dumps(_fix(p), indent=1))
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    sys.exit(main(sys.argv[1:]))
