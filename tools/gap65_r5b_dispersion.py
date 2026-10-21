"""GAP-65: dispersion of the R5b (CIFAR-10) arms against the Inception reference.

Re-reads the cached InceptionV3 features recorded by the GAP-46 memory-fraction
sweep and reports

    rho_arm = tr(Sigma_arm) / tr(Sigma_reference)

for every (memory fraction, arm) cell, alongside the already-recorded
``mean_delta_pct``. No sampling, no GPU.

Reference: ``data/cifar10_inception_features.npz`` (10 000 x 2048).

This is the out-of-family test of the sign rule established on R5c
(``docs/audit/gap64-r5c-operating-regime.md`` §3.3): the framework's FID cost is
governed by how far it moves the output dispersion away from the data's.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

ARMS = {
    "CodimensionSheetScheduler": "codimension_sheet",
    "CosineAnnealScheduler": "cosine_anneal",
    "EvidenceDrivenScheduler": "evidence_driven",
    "FreeTrajScheduler": "free_traj",
}
SEEDS = (42, 43, 44)
M_VALUES = ("default", "0.25", "0.5", "0.75")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path,
                    default=_REPO_ROOT / "verification_outputs" / "gap46-r5b-memory")
    ap.add_argument("--ref", type=Path,
                    default=_REPO_ROOT / "data" / "cifar10_inception_features.npz")
    args = ap.parse_args(argv)

    ref = np.load(args.ref)["features"].astype(np.float64)
    tr_ref = float(np.trace(np.cov(ref, rowvar=False)))
    print(f"reference: n={ref.shape[0]} d={ref.shape[1]} tr(S_ref)={tr_ref:.4f}")

    deltas: dict[tuple[str, str], float] = {}
    csv_path = args.root / "gap46-memory-fraction.csv"
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            deltas[(row["m"], row["arm"])] = float(row["mean_delta_pct"])

    print()
    print("| m | arm | rho_base | rho_arm | dFID% |")
    print("|---|---|---:|---:|---:|")
    rho_arms: list[float] = []
    d_fids: list[float] = []
    for m in M_VALUES:
        tag = "default" if m == "default" else f"m{m}"
        rho_base_seeds: list[float] = []
        rho_arm_seeds: dict[str, list[float]] = {v: [] for v in ARMS.values()}
        for seed in SEEDS:
            cache = args.root / f"seed{seed}-{tag}" / "inception_feats_cache"
            if not cache.exists():
                continue
            base = np.load(cache / "baseline.npy").astype(np.float64)
            rho_base_seeds.append(
                float(np.trace(np.cov(base, rowvar=False))) / tr_ref)
            for cls, short in ARMS.items():
                p = cache / f"{cls}.npy"
                if p.exists():
                    f = np.load(p).astype(np.float64)
                    rho_arm_seeds[short].append(
                        float(np.trace(np.cov(f, rowvar=False))) / tr_ref)
        if not rho_base_seeds:
            continue
        rho_base = float(np.mean(rho_base_seeds))
        for cls, short in ARMS.items():
            if not rho_arm_seeds[short]:
                continue
            rho_arm = float(np.mean(rho_arm_seeds[short]))
            d = deltas.get((m, cls), float("nan"))
            rho_arms.append(rho_arm)
            d_fids.append(d)
            print(f"| {m} | {short} | {rho_base:.4f} | {rho_arm:.4f} | {d:+.2f} |")

    if len(rho_arms) >= 3:
        r = float(np.corrcoef(np.array(rho_arms), np.array(d_fids))[0, 1])
        print()
        print(f"n cells = {len(rho_arms)}   corr(rho_arm, dFID) = {r:+.4f}")
        print("NOTE: this correlation is dominated by the three arms that the "
              "sweep under-budgeted\n(75-79 NFE vs 150), which collapse to "
              "rho_arm ~ 0.10. It is a statement about\nbudget, not about the "
              "blend. See docs/audit/gap65-dispersion-selector.md section 3.2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
