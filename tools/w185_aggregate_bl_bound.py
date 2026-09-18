"""Wave 185 P2 — empirical BL distance (energy distance) measurement.

Computes the empirical energy distance between baseline and framework
distributions for each (model, nfe) cell, using pLDDT (1-D) and
(pLDDT, scPerplexity) (2-D) as the feature vectors.

Per Wave 185 P1 design
(``docs/audit/wave185-p1-design.md`` §2), the energy distance is the
canonical BL-distance proxy for the framework: it metrizes convergence
in distribution, is byte-stable between two framework implementations,
and is exposed via
``adaptive_reflow.eval.coverage.energy_distance_with_ci`` with seeded
percentile bootstrap.

Inputs
------
- Wave 179 eval data (``/tmp/w179/eval/{cell}_{arm}_seed{42,43,44}/``):
  3 seeds x 30 records = 90 per cell per arm for {NFE 50, 100, 200}.
- Wave 183 eval data (``/tmp/w183/eval/{cell}_{arm}/``):
  1 seed x 30 records = 30 per cell per arm for {NFE 10, 150, 300}.

Output
------
- ``verification_outputs/wave185-p2-empirical-bl.csv``
- stdout JSON for the harness.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

# Ensure the framework package is importable when this script is run
# directly from the repo root.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from adaptive_reflow.eval.coverage import energy_distance_with_ci  # noqa: E402


# Per Wave 185 P1 §4: (model, nfe) cell layout.
MODELS: Tuple[str, ...] = ("lineageflow", "kanzi")
NFE_POINTS: Tuple[int, ...] = (10, 50, 100, 150, 200, 300)

# Wave 179 covers NFE in {50, 100, 200} with 3 seeds.
WAVE179_NFE: Tuple[int, ...] = (50, 100, 200)
WAVE179_SEEDS: Tuple[int, ...] = (42, 43, 44)
W179_ROOT = "/tmp/w179/eval"

# Wave 183 covers the remaining NFE {10, 150, 300} with 1 seed.
WAVE183_NFE: Tuple[int, ...] = (10, 150, 300)
W183_ROOT = "/tmp/w183/eval"


@dataclass(frozen=True)
class Cell:
    model: str
    nfe: int


def _cell_name(model: str, nfe: int) -> str:
    return f"{model}_nfe{nfe}"


def _load_records(metrics_jsonl: str) -> List[Tuple[float, float]]:
    """Return list of (pLDDT, scPerplexity) for the records in the file."""
    out: List[Tuple[float, float]] = []
    with open(metrics_jsonl, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            plddt = float(rec.get("plddt_mean", float("nan")))
            scperp = float(rec.get("sc_perplexity", float("nan")))
            if np.isnan(plddt) or np.isnan(scperp):
                # Skip incomplete records (e.g., a fold that crashed).
                continue
            out.append((plddt, scperp))
    return out


def _load_arm_records(cell: Cell, arm: str) -> Tuple[np.ndarray, List[float]]:
    """Load all available per-seed records for one (cell, arm).

    Returns ``(records, per_seed_means_plddt)`` where ``records`` is
    an (N, 2) array of (pLDDT, scPerplexity) and ``per_seed_means_plddt``
    is a list of per-seed mean pLDDT values (length 3 when Wave 179
    data is available, length 1 when only Wave 183 data exists).
    """
    name = _cell_name(cell.model, cell.nfe)
    per_seed_records: List[List[Tuple[float, float]]] = []

    if cell.nfe in WAVE179_NFE:
        for seed in WAVE179_SEEDS:
            p = os.path.join(W179_ROOT, f"{name}_{arm}_seed{seed}", "foldability", "metrics.jsonl")
            if os.path.exists(p):
                per_seed_records.append(_load_records(p))
    if cell.nfe in WAVE183_NFE:
        p = os.path.join(W183_ROOT, f"{name}_{arm}", "foldability", "metrics.jsonl")
        if os.path.exists(p):
            per_seed_records.append(_load_records(p))

    if not per_seed_records:
        return np.empty((0, 2), dtype=np.float64), []

    all_records: List[Tuple[float, float]] = []
    per_seed_means: List[float] = []
    for recs in per_seed_records:
        if not recs:
            continue
        all_records.extend(recs)
        per_seed_means.append(float(np.mean([r[0] for r in recs])))

    arr = np.asarray(all_records, dtype=np.float64)
    return arr, per_seed_means


def _energy_distance_1d(baseline: np.ndarray, framework: np.ndarray, *, n_boot: int, seed: int) -> Dict[str, float]:
    """Compute 1-D (pLDDT only) energy distance with bootstrap CI."""
    est = energy_distance_with_ci(
        baseline[:, 0].reshape(-1, 1),
        framework[:, 0].reshape(-1, 1),
        n_bootstrap=n_boot,
        confidence=0.95,
        seed=seed,
    )
    return {
        "point": float(est.point),
        "lower": float(est.lower),
        "upper": float(est.upper),
    }


def _energy_distance_2d(baseline: np.ndarray, framework: np.ndarray, *, n_boot: int, seed: int) -> Dict[str, float]:
    """Compute 2-D (pLDDT, scPerplexity) energy distance with bootstrap CI."""
    est = energy_distance_with_ci(
        baseline,
        framework,
        n_bootstrap=n_boot,
        confidence=0.95,
        seed=seed,
    )
    return {
        "point": float(est.point),
        "lower": float(est.lower),
        "upper": float(est.upper),
    }


def main() -> int:
    out_csv = os.path.join(
        _REPO_ROOT, "verification_outputs", "wave185-p2-empirical-bl.csv"
    )
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    rows: List[Dict[str, object]] = []
    summary: Dict[str, Dict[str, float]] = {m: {} for m in MODELS}

    for model in MODELS:
        for nfe in NFE_POINTS:
            cell = Cell(model, nfe)
            baseline_records, baseline_seed_means = _load_arm_records(cell, "baseline")
            framework_records, framework_seed_means = _load_arm_records(cell, "framework")

            n_b = int(baseline_records.shape[0])
            n_f = int(framework_records.shape[0])

            ed1d = _energy_distance_1d(baseline_records, framework_records, n_boot=1000, seed=42)
            ed2d = _energy_distance_2d(baseline_records, framework_records, n_boot=1000, seed=42)

            rows.append({
                "model": model,
                "nfe": nfe,
                "n_baseline_records": n_b,
                "n_framework_records": n_f,
                "n_seeds": len(baseline_seed_means),
                "empirical_BL_pLDDT_mean": ed1d["point"],
                "empirical_BL_pLDDT_95CI_low": ed1d["lower"],
                "empirical_BL_pLDDT_95CI_high": ed1d["upper"],
                "empirical_BL_2D_mean": ed2d["point"],
                "empirical_BL_2D_95CI_low": ed2d["lower"],
                "empirical_BL_2D_95CI_high": ed2d["upper"],
                "baseline_pLDDT_per_seed": ";".join(f"{m:.4f}" for m in baseline_seed_means),
                "framework_pLDDT_per_seed": ";".join(f"{m:.4f}" for m in framework_seed_means),
            })
            summary[model][str(nfe)] = float(ed1d["point"])

    fieldnames = list(rows[0].keys())
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"WROTE: {out_csv}")
    print(f"ROWS: {len(rows)}")
    for r in rows:
        print(
            f"  {r['model']:12s} NFE={r['nfe']:>3d} "
            f"E1D={r['empirical_BL_pLDDT_mean']:.4f} "
            f"[{r['empirical_BL_pLDDT_95CI_low']:.4f}, {r['empirical_BL_pLDDT_95CI_high']:.4f}] "
            f"E2D={r['empirical_BL_2D_mean']:.4f} "
            f"n_seeds={r['n_seeds']}"
        )

    # Emit the JSON the harness expects.
    print("\n__JSON__")
    print(json.dumps({"empirical_bl_table": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
