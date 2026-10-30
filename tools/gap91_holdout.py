"""GAP-91 hold-out — does the contraction law transfer to checkpoints added later?

The six-point fit in ``docs/audit/gap90-optsteps-dose.md`` §10 is validated by
leave-one-out, which is in-sample: every fold still trains on the two GAP-90
checkpoints. This script fits on the four original GAP-84 checkpoints only and
predicts the two added afterwards, so neither touches the coefficients.

    python3 tools/gap91_holdout.py

Reads the frontier artifacts and prints the fit, the two predictions with their
95 % prediction intervals, and the fixed point. Numbers are the ones quoted in
§14 of the GAP-90 audit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

#: checkpoint -> (artifact, is it one of the original four?)
CHECKPOINTS: dict[str, tuple[str, bool]] = {
    "w16e1_5k": (
        "verification_outputs/gap84-cap-frontier/frontier_w16e1_5k.json", True,
    ),
    "w16e1_10k": (
        "verification_outputs/gap84-cap-frontier/frontier_w16e1_10k.json", True,
    ),
    "w16e1_60k": (
        "verification_outputs/gap84-cap-frontier/frontier_w16e1_60k.json", True,
    ),
    "production": (
        "verification_outputs/gap84-cap-frontier/frontier_production.json", True,
    ),
    "epochs2": (
        "verification_outputs/gap90-optsteps-dose/"
        "frontier_epochs2_evidence_driven.json", False,
    ),
    "w8e3": (
        "verification_outputs/gap90-optsteps-dose/"
        "frontier_w8e3_evidence_driven.json", False,
    ),
}

#: t_{0.975} for df = 2, the prediction-interval multiplier at n = 4.
T_975_DF2 = 2.776


def plateaus(rel: str) -> tuple[float, float]:
    """``(baseline plateau, framework plateau)`` from one frontier artifact."""
    art = json.loads((REPO_ROOT / rel).read_text())
    rungs = {r["nfe"]: r for r in art["rungs"]}
    fw = (rungs[100]["framework"] + rungs[200]["framework"]) / 2.0
    return float(art["baseline_plateau"]["value"]), float(fw)


def main() -> int:
    measured = {k: plateaus(rel) for k, (rel, _) in CHECKPOINTS.items()}
    train = [k for k, (_, is_train) in CHECKPOINTS.items() if is_train]
    hold = [k for k, (_, is_train) in CHECKPOINTS.items() if not is_train]

    x = np.array([measured[k][0] for k in train])
    y = np.array([measured[k][1] for k in train])
    slope, intercept = np.polyfit(x, y, 1)
    n = len(x)
    resid = y - (intercept + slope * x)
    ss_res = float((resid ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    resid_sd = float(np.sqrt(ss_res / (n - 2)))
    x_bar = float(x.mean())
    sxx = float(((x - x_bar) ** 2).sum())
    se_slope = resid_sd / np.sqrt(sxx)

    print(f"fit on the {n} original checkpoints ({', '.join(train)}):")
    print(f"  framework = {intercept:.6f} + {slope:.6f} * baseline")
    print(f"  slope 95% CI [{slope - T_975_DF2 * se_slope:.4f}, "
          f"{slope + T_975_DF2 * se_slope:.4f}]  "
          f"R2 = {1 - ss_res / ss_tot:.5f}  residual sd = {resid_sd:.3f}")
    print(f"  fixed point  a / (1 - b) = {intercept / (1 - slope):.3f} FID")
    print()
    print(f"  {'training point':12s} {'baseline':>9s} {'actual':>9s} {'fit':>9s} {'resid':>8s}")
    for k, r in zip(train, resid, strict=True):
        bx, by = measured[k]
        print(f"  {k:12s} {bx:9.4f} {by:9.4f} {intercept + slope * bx:9.4f} {r:+8.4f}")

    print()
    print(f"  {'held out':12s} {'baseline':>9s} {'actual':>9s} {'predicted':>10s} "
          f"{'error':>8s} {'95% PI':>19s}")
    errors = []
    for k in hold:
        bx, by = measured[k]
        pred = intercept + slope * bx
        se = resid_sd * np.sqrt(1 + 1 / n + (bx - x_bar) ** 2 / sxx)
        lo, hi = pred - T_975_DF2 * se, pred + T_975_DF2 * se
        errors.append(pred - by)
        print(f"  {k:12s} {bx:9.4f} {by:9.4f} {pred:10.4f} {pred - by:+8.4f} "
              f"[{lo:6.3f}, {hi:6.3f}]")

    print()
    print(f"  hold-out MAE = {np.mean(np.abs(errors)):.4f} FID   "
          f"max |error| = {max(abs(e) for e in errors):.4f} FID")
    print(f"  training x-range [{x.min():.3f}, {x.max():.3f}]; "
          f"held-out baselines [{min(measured[k][0] for k in hold):.3f}, "
          f"{max(measured[k][0] for k in hold):.3f}] "
          f"-> {'interpolation' if min(measured[k][0] for k in hold) >= x.min() and max(measured[k][0] for k in hold) <= x.max() else 'EXTRAPOLATION'}")
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    raise SystemExit(main())
