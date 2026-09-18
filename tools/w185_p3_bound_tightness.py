"""Wave 185 P3 — Theorem 1 bound + empirical BL tightness analysis.

Computes the right-hand side of Theorem 1:

    B(NFE) = A_g * exp(-NFE / B_g) + C_g * e_rho

for two regimes:
- framework: (rho=0.1, c=1.0, eta=0.1) — the framework's regime defaults.
- baseline:  (rho=0.25, c=1.0, eta=0.25) — the maximum-allowed
  ungoverned regime (rho < d/4 = 0.25 for d=1).

The (A_g, B_g, C_g, e_rho) constants come from
``PaperQuantitiesSnapshot.for_profile`` with the Wave 11
canonical profile ``g(x) = sin(pi*x)``.

Loads empirical BL (energy distance) from
``verification_outputs/wave185-p2-empirical-bl.csv`` and computes
the **tightness ratio** = empirical_BL / theoretical_bound for
each (model, nfe) cell.

Inputs
------
- ``verification_outputs/wave185-p2-empirical-bl.csv`` (P2 output).

Outputs
-------
- ``verification_outputs/wave185-p3-tightness.csv`` (12 rows).
- stdout JSON for the harness.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from dataclasses import dataclass

# Ensure the framework package is importable when this script is run
# directly from the repo root.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from adaptive_reflow.eval.fid_theorem_aligned import (  # noqa: E402
    PaperQuantitiesSnapshot,
)

MODELS: tuple[str, ...] = ("lineageflow", "kanzi")
NFE_POINTS: tuple[int, ...] = (10, 50, 100, 150, 200, 300)


def _sin_pi(x: float) -> float:
    return math.sin(math.pi * x)


def _build_snapshots() -> tuple[dict[str, float], dict[str, float]]:
    """Return (framework_snap_dict, baseline_snap_dict) of paper quantities."""
    framework = PaperQuantitiesSnapshot.for_profile(
        g=_sin_pi, rho=0.1, c=1.0, eta=0.1, K=8.0, h=0.01,
    )
    baseline = PaperQuantitiesSnapshot.for_profile(
        g=_sin_pi, rho=0.25, c=1.0, eta=0.25, K=8.0, h=0.01,
    )
    return (
        {
            "A_g": framework.A_g,
            "B_g": framework.B_g,
            "C_g": framework.C_g,
            "e_rho": framework.e_rho,
        },
        {
            "A_g": baseline.A_g,
            "B_g": baseline.B_g,
            "C_g": baseline.C_g,
            "e_rho": baseline.e_rho,
        },
    )


def _theorem1_bound(A: float, B: float, C: float, e: float, nfe: int) -> float:
    return A * math.exp(-float(nfe) / B) + C * e


def _load_empirical_bl(csv_path: str) -> dict[tuple[str, int], dict[str, float]]:
    """Load (model, nfe) -> {empirical_BL, ci_low, ci_high} from P2 CSV."""
    out: dict[tuple[str, int], dict[str, float]] = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = row["model"]
            nfe = int(row["nfe"])
            out[(model, nfe)] = {
                "empirical_BL": float(row["empirical_BL_pLDDT_mean"]),
                "ci_low": float(row["empirical_BL_pLDDT_95CI_low"]),
                "ci_high": float(row["empirical_BL_pLDDT_95CI_high"]),
            }
    return out


def main() -> int:
    out_csv = os.path.join(
        _REPO_ROOT, "verification_outputs", "wave185-p3-tightness.csv"
    )
    in_csv = os.path.join(
        _REPO_ROOT, "verification_outputs", "wave185-p2-empirical-bl.csv"
    )
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    framework, baseline = _build_snapshots()
    empirical = _load_empirical_bl(in_csv)

    rows: list[dict[str, object]] = []
    # For JSON output.
    tightness_table: dict[str, dict[str, dict[str, float]]] = {
        m: {} for m in MODELS
    }

    for model in MODELS:
        for nfe in NFE_POINTS:
            emp_bl = empirical[(model, nfe)]["empirical_BL"]
            emp_low = empirical[(model, nfe)]["ci_low"]
            emp_high = empirical[(model, nfe)]["ci_high"]

            # Framework bound uses the framework regime.
            b_fw = _theorem1_bound(
                framework["A_g"], framework["B_g"],
                framework["C_g"], framework["e_rho"], nfe,
            )
            # Baseline bound uses the baseline regime.
            b_bl = _theorem1_bound(
                baseline["A_g"], baseline["B_g"],
                baseline["C_g"], baseline["e_rho"], nfe,
            )

            ratio_fw = emp_bl / b_fw if b_fw > 0 else float("inf")
            ratio_bl = emp_bl / b_bl if b_bl > 0 else float("inf")

            rows.append({
                "model": model,
                "nfe": nfe,
                "A_g": framework["A_g"],
                "B_g": framework["B_g"],
                "C_g": framework["C_g"],
                "e_rho": framework["e_rho"],
                "theoretical_bound": b_fw,
                "empirical_BL": emp_bl,
                "tightness_ratio": ratio_fw,
                "baseline_bound": b_bl,
                "baseline_tightness_ratio": ratio_bl,
                "ci_low": emp_low,
                "ci_high": emp_high,
                "tight_F": emp_high <= b_fw,
                "tight_B": emp_high <= b_bl,
            })
            tightness_table[model][str(nfe)] = {
                "theoretical_bound": b_fw,
                "empirical_BL": emp_bl,
                "tightness_ratio": ratio_fw,
            }

    fieldnames = list(rows[0].keys())
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Find best/worst tightness cells (lowest/highest ratio).
    ratio_pairs = [
        (r["model"], int(r["nfe"]), float(r["tightness_ratio"]))  # type: ignore[arg-type]
        for r in rows
    ]
    best = min(ratio_pairs, key=lambda x: x[2])
    worst = max(ratio_pairs, key=lambda x: x[2])

    print(f"WROTE: {out_csv}")
    print(f"ROWS: {len(rows)}")
    print(
        f"Framework snap: A_g={framework['A_g']:.6f} B_g={framework['B_g']:.6f} "
        f"C_g={framework['C_g']:.6f} e_rho={framework['e_rho']:.6e}"
    )
    print(
        f"Baseline  snap: A_g={baseline['A_g']:.6f} B_g={baseline['B_g']:.6f} "
        f"C_g={baseline['C_g']:.6f} e_rho={baseline['e_rho']:.6e}"
    )
    print("\nTightness table (framework regime):")
    print(
        f"  {'model':12s} {'NFE':>4s} {'B_fw':>12s} {'empirical':>12s} "
        f"{'ratio':>10s} {'tight_F':>8s} {'tight_B':>8s}"
    )
    for r in rows:
        print(
            f"  {r['model']:12s} {r['nfe']:>4d} "
            f"{r['theoretical_bound']:>12.6e} {r['empirical_BL']:>12.4f} "
            f"{r['tightness_ratio']:>10.2f} "
            f"{str(r['tight_F']):>8s} {str(r['tight_B']):>8s}"
        )

    print(f"\nBest tightness: {best[0]} NFE={best[1]} ratio={best[2]:.2f}")
    print(f"Worst tightness: {worst[0]} NFE={worst[1]} ratio={worst[2]:.2f}")

    print("\n__JSON__")
    print(json.dumps(
        {
            "tightness_table": tightness_table,
            "best_tightness_regime": {
                "model": best[0], "nfe": best[1], "tightness_ratio": best[2],
            },
            "worst_tightness_regime": {
                "model": worst[0], "nfe": worst[1], "tightness_ratio": worst[2],
            },
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
