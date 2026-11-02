#!/usr/bin/env python3
"""Recompute historical Kanzi summaries; no generation or causal verdict.

Welch inference is conditional on independent records. Four-template baseline
variants and different arm populations prevent a matched-refinement claim.
The index-difference calculation is retained only to reproduce history.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import t


def compare(baseline: dict[str, float], framework: dict[str, float]) -> dict:
    """Validate matching keys and return both explicitly labelled estimands."""
    if set(baseline) != set(framework):
        raise ValueError("record keys must match exactly; no silent intersection")
    if len(baseline) < 2:
        raise ValueError("at least two records per arm required")
    keys = sorted(baseline)
    b = np.array([baseline[k] for k in keys], dtype=float)
    f = np.array([framework[k] for k in keys], dtype=float)
    if not (np.isfinite(b).all() and np.isfinite(f).all()):
        raise ValueError("non-finite RMSD")
    n = len(b)
    vb, vf = b.var(ddof=1), f.var(ddof=1)
    se2 = (vb + vf) / n
    if vb <= 0 or vf <= 0 or (f - b).var(ddof=1) <= 0:
        raise ValueError("positive arm and index-difference variance required")
    df = se2**2 / ((vb / n)**2 / (n - 1) + (vf / n)**2 / (n - 1))
    delta = float(f.mean() - b.mean())

    def interval(se: float, dof: float) -> dict:
        statistic = delta / se
        half = float(t.ppf(0.975, dof)) * se
        return {"difference_A": delta, "se_A": se, "df": dof,
                "t": statistic, "p_two_sided": float(2*t.sf(abs(statistic), dof)),
                "ci95_A": [delta - half, delta + half]}

    welch = interval(float(np.sqrt(se2)), float(df))
    welch["p_bonferroni_7"] = min(1., 7 * welch["p_two_sided"])
    indexed = interval(float((f-b).std(ddof=1) / np.sqrt(n)), float(n-1))
    indexed["d_z"] = float((f-b).mean() / (f-b).std(ddof=1))
    return {"n_per_arm": n, "baseline_mean_A": float(b.mean()),
            "framework_mean_A": float(f.mean()),
            "index_correlation": float(np.corrcoef(b, f)[0, 1]),
            "welch_independent_record_sensitivity": welch,
            "historical_index_difference_not_matched_input": indexed,
            "scope": "Different structure populations; baseline has four PDB templates. "
                     "Record-level Welch does not establish template-generalized inference, "
                     "matched input refinement, biological quality, or multi-round benefit."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--framework", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = [args.baseline, args.framework]
    blobs = [json.loads(p.read_text()) for p in inputs]
    result = compare(*(b["per_seq_rmsd_A"] for b in blobs))
    for blob, name in zip(blobs, ["baseline", "framework"], strict=True):
        if not np.isclose(blob["reconstruction_kabsch_rmsd_A"]["mean_rmsd_A"],
                          result[f"{name}_mean_A"], rtol=0, atol=1e-12):
            raise ValueError(f"{name} aggregate does not match records")
    result["sources"] = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in inputs]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
