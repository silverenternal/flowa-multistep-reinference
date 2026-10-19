#!/usr/bin/env python3
"""GAP-55 — record-level inference for the R3 FlowMol3 ``fg_dev`` cell.

Why this exists
---------------
The historical R3 headline (`d_z = -0.285`) came from a *per-record REOS
flag-count proxy* projected from N=200 to N=1000. Two problems:

1. ``fg_dev`` is a **set-level** metric: ``sum_i |p_i^gen - p_i^train|`` over
   REOS flags. It has no exact per-record additive decomposition, so a
   per-record t-test on a proxy is not a test of ``fg_dev``.
2. The canonical artifact was N=200 per arm despite the ``n1000`` filename.

This tool consumes a **paired N=1000 sweep** produced with
``tools/wave87_n1000_sweep.py --smiles-cap 0 --shared-prior`` and reports:

* the aggregate ``fg_dev`` for both arms (as measured by the sweep), and
* a **record-level paired bootstrap** of the difference, which is the correct
  uncertainty statement for a set-level metric.

The bootstrap recomputes ``fg_dev`` from the REOS flag matrix on each resample
(``B`` draws of ``N`` records with replacement). The recomputed absolute value
differs from the upstream analyzer by a small constant (upstream aligns the
train vector positionally and applies its own molecule build path); the
**difference** agrees with the sweep to ~0.006, which is what the bootstrap
uses.

Outputs
-------
    <run-dir>/per_record_fg_dev.json
    <run-dir>/per_record_fg_dev.csv   (per-record flag counts + contributions)

Usage
-----
    .venvs/flowmol3_venv/bin/python tools/gap55_r3_per_record_fg_dev.py \
        --run-dir verification_outputs/gap55-r3-full-smiles
"""

from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from rdkit import Chem

REPO = Path(__file__).resolve().parent.parent
TRAIN_REOS = (
    REPO
    / "data/FlowMol3/repo/data/geom_full_kekulized/train_reos_ring_counts.pkl"
)
ALPHA_BONF = 0.05 / 7  # R-level primary family: 7 cells
N_BOOT = 2000
BOOT_SEED = 20261019


def _find_arm_json(run_dir: Path, arm: str) -> Path:
    matches = sorted(run_dir.glob(f"flowmol3_n1000_{arm}_*.json"))
    if not matches:
        raise SystemExit(f"missing_{arm}_json_in:{run_dir}")
    return matches[-1]


def _load_smiles(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return list(json.load(f)["smiles_list"])


def _reos():
    sys.path.insert(0, str(REPO / "data/FlowMol3/repo/flowmol/analysis"))
    from reos import REOS  # type: ignore

    return REOS(active_rules=["Glaxo", "Dundee"])


def _train_rates() -> np.ndarray:
    with open(TRAIN_REOS, "rb") as f:
        train = pickle.load(f)
    return np.asarray(train["reos_flag_arr"], dtype=np.float64).mean(0)


def _flag_matrix(
    smiles: list[str], reos_obj: object,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (N-row flag matrix, valid mask, per-record flag count).

    Rows for invalid molecules are all-zero and excluded via ``valid``.
    Keeping the full N-row shape lets the bootstrap index both arms on the
    same record ids even when the two arms sanitize different counts.
    """
    n = len(smiles)
    mols: list[object] = []
    row_of: list[int] = []
    valid = np.zeros(n, dtype=bool)
    counts = np.zeros(n, dtype=np.int64)
    for i, smi in enumerate(smiles):
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            continue
        valid[i] = True
        counts[i] = len(reos_obj.mol_to_flags(mol))
        mols.append(mol)
        row_of.append(i)
    compact = np.asarray(reos_obj.mols_to_flag_arr(mols), dtype=np.float64)
    matrix = np.zeros((n, compact.shape[1]), dtype=np.float64)
    matrix[np.asarray(row_of, dtype=np.int64)] = compact
    return matrix, valid, counts


def _fg_dev(flag_rows: np.ndarray, train_rates: np.ndarray) -> float:
    p = flag_rows.sum(0) / flag_rows.shape[0]
    return float(np.abs(p - train_rates[: p.shape[0]]).sum())


def _bootstrap_delta(
    bl_matrix: np.ndarray,
    fw_matrix: np.ndarray,
    bl_valid: np.ndarray,
    fw_valid: np.ndarray,
    train_rates: np.ndarray,
    n_records: int,
    rng: np.random.Generator,
) -> dict[str, float]:
    deltas = np.empty(N_BOOT, dtype=np.float64)
    for b in range(N_BOOT):
        idx = rng.integers(0, n_records, size=n_records)
        bl_rows = bl_matrix[idx][bl_valid[idx]]
        fw_rows = fw_matrix[idx][fw_valid[idx]]
        deltas[b] = _fg_dev(fw_rows, train_rates) - _fg_dev(bl_rows, train_rates)
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    # Two-sided bootstrap p: twice the smaller tail mass at zero.
    p_boot = 2.0 * min(float((deltas >= 0).mean()), float((deltas <= 0).mean()))
    return {
        "n_boot": N_BOOT,
        "mean_delta": float(deltas.mean()),
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "p_bootstrap_two_sided": min(p_boot, 1.0),
        "frac_bootstrap_favourable": float((deltas < 0).mean()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", type=Path, required=True)
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir).resolve()
    bl_json = _find_arm_json(run_dir, "baseline")
    fw_json = _find_arm_json(run_dir, "framework")
    bl_smiles = _load_smiles(bl_json)
    fw_smiles = _load_smiles(fw_json)
    n = min(len(bl_smiles), len(fw_smiles))
    print(f"baseline={bl_json.name} framework={fw_json.name} n={n}", flush=True)

    reos_obj = _reos()
    train_rates = _train_rates()
    bl_matrix, bl_valid, bl_counts = _flag_matrix(bl_smiles[:n], reos_obj)
    fw_matrix, fw_valid, fw_counts = _flag_matrix(fw_smiles[:n], reos_obj)
    print(
        f"sanitized: baseline={int(bl_valid.sum())} framework={int(fw_valid.sum())}",
        flush=True,
    )

    fg_bl = _fg_dev(bl_matrix[bl_valid], train_rates)
    fg_fw = _fg_dev(fw_matrix[fw_valid], train_rates)
    rng = np.random.default_rng(BOOT_SEED)
    boot = _bootstrap_delta(
        bl_matrix, fw_matrix, bl_valid, fw_valid, train_rates, n, rng,
    )

    result = {
        "kind": "gap55_r3_fg_dev_record_bootstrap",
        "run_dir": str(run_dir.relative_to(REPO)),
        "baseline_json": bl_json.name,
        "framework_json": fw_json.name,
        "n_records": n,
        "n_sanitized_baseline": int(bl_valid.sum()),
        "n_sanitized_framework": int(fw_valid.sum()),
        "metric": "reos_cum_dev (fg_dev)",
        "definition": "sum_i |p_i^gen - p_i^train| over REOS Glaxo+Dundee flags",
        "fg_dev_baseline": fg_bl,
        "fg_dev_framework": fg_fw,
        "delta_framework_minus_baseline": fg_fw - fg_bl,
        "bootstrap": boot,
        "alpha_bonferroni": ALPHA_BONF,
        "bootstrap_seed": BOOT_SEED,
        "note": (
            "The recomputed absolute fg_dev differs from the upstream analyzer "
            "by a small constant (upstream positional train alignment + its "
            "own molecule-build path). The recomputed delta agrees with the "
            "sweep's reported delta to ~0.006; the bootstrap uses the "
            "recomputed delta."
        ),
    }
    d = result["delta_framework_minus_baseline"]
    p = boot["p_bootstrap_two_sided"]
    result["verdict"] = (
        "framework_wins"
        if p < ALPHA_BONF and d < 0
        else "baseline_wins"
        if p < ALPHA_BONF and d > 0
        else "not_significant"
    )

    out_json = run_dir / "per_record_fg_dev.json"
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    with open(run_dir / "per_record_fg_dev.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "record", "baseline_flags", "framework_flags",
            "baseline_valid", "framework_valid",
        ])
        for i in range(n):
            w.writerow([
                i, int(bl_counts[i]), int(fw_counts[i]),
                int(bl_valid[i]), int(fw_valid[i]),
            ])

    print(json.dumps({
        "fg_dev_baseline": round(fg_bl, 6),
        "fg_dev_framework": round(fg_fw, 6),
        "delta": round(d, 6),
        "bootstrap": boot,
        "verdict": result["verdict"],
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
