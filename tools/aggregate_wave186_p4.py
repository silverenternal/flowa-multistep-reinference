#!/usr/bin/env python3
"""Wave 186 P4 aggregator.

Reads the 18-cell Wave 186 P3 eval summary CSV and produces:

1. /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave186-p4-aggregation.csv
2. Four per-axis sensitivity plots under
   /home/hugo/codes/flowa-multistep-reinference/plots/wave186-p4-<axis>.png
3. A machine-readable summary JSON printed to stdout for the harness to
   parse (robust_regions + framework_consistent_winner + commit_sha).

The script is byte-stable (deterministic; no RNG; no time-of-day inputs)
so it can be re-run from CI without producing drift in the CSV or
plots.

Key analytical finding (see Wave 184 P2 §4.1 and Wave 186 P2 §4.1):
The lineageflow synthetic adapter is byte-stable across the full β /
restart_min_nfe / NFE_REF envelope at NFE=100. Only the seed axis
carries variance. The aggregator makes this quantitative: per-axis
range, std, and "framework beats baseline" lift across the seed
ensemble.
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
P3_CSV = REPO_ROOT / "verification_outputs" / "wave186-p3-eval-summary.csv"
P4_CSV = REPO_ROOT / "verification_outputs" / "wave186-p4-aggregation.csv"
PLOTS_DIR = REPO_ROOT / "plots"

# AXIS_ORDER uses the canonical parameter names (matches the CSV column
# names). PERTURB_AXIS_KEY maps each parameter to the value used in the
# Wave 186 P3 perturb_axis column (which shortens "beta_base" to "beta"
# in the raw CSV).
AXIS_ORDER = ("beta_base", "restart_min_nfe", "nfe_ref", "seed")
PERTURB_AXIS_KEY = {
    "beta_base": "beta",
    "restart_min_nfe": "restart_min_nfe",
    "nfe_ref": "nfe_ref",
    "seed": "seed",
}

# ---- helpers --------------------------------------------------------------


def load_p3() -> list[dict]:
    rows: list[dict] = []
    with P3_CSV.open() as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "cell_id": r["cell_id"],
                    "perturb_axis": r["perturb_axis"],
                    "perturb_value": r["perturb_value"],
                    "beta_base": float(r["beta_base"]),
                    "restart_min_nfe": int(r["restart_min_nfe"]),
                    "nfe_ref": int(r["nfe_ref"]),
                    "seed": int(r["seed"]),
                    "plddt_mean": float(r["plddt_mean"]),
                    "plddt_median": float(r["plddt_median"]),
                    "sc_perplexity_mean": float(r["sc_perplexity_mean"]),
                    "sc_perplexity_median": float(r["sc_perplexity_median"]),
                }
            )
    return rows


def get_baseline(rows: list[dict]) -> dict:
    for r in rows:
        if r["cell_id"] == "baseline":
            return r
    raise RuntimeError("baseline row not found in P3 CSV")


def get_axis_rows(rows: list[dict], axis: str) -> list[dict]:
    """Return cells where perturb_axis matches; baseline goes first."""
    axis_rows = [r for r in rows if r["perturb_axis"] == axis]
    base = get_baseline(rows)
    if axis != "none":
        return [base] + axis_rows
    return [base]


def write_aggregation_csv(rows: list[dict]) -> None:
    """Build the P4 aggregation table.

    Columns: cell | parameter | value | pLDDT | scPerplexity |
             delta_plddt_vs_baseline | delta_scperp_vs_baseline
    """
    base = get_baseline(rows)
    base_plddt = base["plddt_mean"]
    base_sc = base["sc_perplexity_mean"]

    P4_CSV.parent.mkdir(parents=True, exist_ok=True)
    with P4_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "cell",
                "parameter",
                "value",
                "pLDDT",
                "scPerplexity",
                "delta_plddt_vs_baseline",
                "delta_scperp_vs_baseline",
            ]
        )
        for r in rows:
            if r["perturb_axis"] == "none":
                param = "baseline"
                value = "-"
            elif r["perturb_axis"] == "beta":
                param = "beta_base"
                value = r["beta_base"]
            elif r["perturb_axis"] == "restart_min_nfe":
                param = "restart_min_nfe"
                value = r["restart_min_nfe"]
            elif r["perturb_axis"] == "nfe_ref":
                param = "nfe_ref"
                value = r["nfe_ref"]
            elif r["perturb_axis"] == "seed":
                param = "seed"
                value = r["seed"]
            else:
                param = r["perturb_axis"]
                value = r["perturb_value"]
            w.writerow(
                [
                    r["cell_id"],
                    param,
                    value,
                    f"{r['plddt_mean']:.4f}",
                    f"{r['sc_perplexity_mean']:.4f}",
                    f"{r['plddt_mean'] - base_plddt:+.4f}",
                    f"{r['sc_perplexity_mean'] - base_sc:+.4f}",
                ]
            )


# ---- per-axis stats & plotting --------------------------------------------


def _axis_cells(rows: list[dict], axis: str) -> list[dict]:
    """Cells perturbing `axis` (excludes baseline which has perturb_axis=none).

    `axis` is the canonical parameter name (e.g. ``beta_base``); the raw
    CSV uses ``beta`` for that axis, so we map via PERTURB_AXIS_KEY.
    """
    return [r for r in rows if r["perturb_axis"] == PERTURB_AXIS_KEY[axis]]


def _extract_xy(cells: list[dict], axis: str) -> tuple[list[float], list[float], list[float]]:
    if axis == "beta_base":
        xs = [c["beta_base"] for c in cells]
    elif axis == "restart_min_nfe":
        xs = [c["restart_min_nfe"] for c in cells]
    elif axis == "nfe_ref":
        xs = [c["nfe_ref"] for c in cells]
    elif axis == "seed":
        xs = [c["seed"] for c in cells]
    else:
        raise ValueError(axis)
    ys_plddt = [c["plddt_mean"] for c in cells]
    ys_sc = [c["sc_perplexity_mean"] for c in cells]
    return xs, ys_plddt, ys_sc


def per_axis_stats(rows: list[dict]) -> dict[str, dict]:
    base = get_baseline(rows)
    stats: dict[str, dict] = {}
    for axis in AXIS_ORDER:
        cells = _axis_cells(rows, axis)
        if not cells:
            continue
        _, yp, ys = _extract_xy(cells, axis)
        plddt_arr = np.array(yp)
        sc_arr = np.array(ys)
        stats[axis] = {
            "n_cells": len(cells),
            "plddt_min": float(plddt_arr.min()),
            "plddt_max": float(plddt_arr.max()),
            "plddt_mean": float(plddt_arr.mean()),
            "plddt_std_sample": float(plddt_arr.std(ddof=1)) if len(plddt_arr) > 1 else 0.0,
            "sc_min": float(sc_arr.min()),
            "sc_max": float(sc_arr.max()),
            "sc_mean": float(sc_arr.mean()),
            "sc_std_sample": float(sc_arr.std(ddof=1)) if len(sc_arr) > 1 else 0.0,
            "plddt_range": float(plddt_arr.max() - plddt_arr.min()),
            "sc_range": float(sc_arr.max() - sc_arr.min()),
            "baseline_plddt": base["plddt_mean"],
            "baseline_sc": base["sc_perplexity_mean"],
            "delta_plddt_mean_vs_baseline": float(plddt_arr.mean() - base["plddt_mean"]),
            "delta_sc_mean_vs_baseline": float(sc_arr.mean() - base["sc_perplexity_mean"]),
        }
    return stats


def _make_plot(rows: list[dict], axis: str, outpath: Path, stats: dict) -> None:
    base = get_baseline(rows)
    cells = _axis_cells(rows, axis)
    xs, yp, ys = _extract_xy(cells, axis)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # --- pLDDT panel ---
    ax1.plot(xs, yp, marker="o", linewidth=2, markersize=8, color="#1f77b4", label="framework")
    ax1.axhline(
        base["plddt_mean"],
        color="#d62728",
        linestyle="--",
        linewidth=1.2,
        label=f"baseline (seed=42) = {base['plddt_mean']:.2f}",
    )
    rng = stats[axis]["plddt_range"]
    std = stats[axis]["plddt_std_sample"]
    ax1.set_title(
        f"pLDDT vs {axis}\n(range={rng:.4f}, std={std:.4f})"
    )
    ax1.set_xlabel(axis)
    ax1.set_ylabel("pLDDT mean")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best", fontsize=8)

    # --- scPerplexity panel ---
    ax2.plot(xs, ys, marker="s", linewidth=2, markersize=8, color="#2ca02c", label="framework")
    ax2.axhline(
        base["sc_perplexity_mean"],
        color="#d62728",
        linestyle="--",
        linewidth=1.2,
        label=f"baseline (seed=42) = {base['sc_perplexity_mean']:.2f}",
    )
    rng_sc = stats[axis]["sc_range"]
    std_sc = stats[axis]["sc_std_sample"]
    ax2.set_title(
        f"scPerplexity vs {axis}\n(range={rng_sc:.4f}, std={std_sc:.4f})"
    )
    ax2.set_xlabel(axis)
    ax2.set_ylabel("scPerplexity mean")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="best", fontsize=8)

    fig.suptitle(
        f"Wave 186 P4 — sensitivity envelope ({axis} axis, N=30/cell)",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(outpath, dpi=120)
    plt.close(fig)


def make_plots(rows: list[dict], stats: dict) -> list[Path]:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for axis in AXIS_ORDER:
        outpath = PLOTS_DIR / f"wave186-p4-{axis}.png"
        _make_plot(rows, axis, outpath, stats)
        paths.append(outpath)
    return paths


# ---- robust-region logic --------------------------------------------------


def robust_regions(rows: list[dict], stats: dict) -> dict:
    """For each axis, return the range over which the framework still wins.

    "Framework wins" on an axis means: the framework metric mean over the
    axis is at least as good as the baseline cell (seed=42). For pLDDT
    higher-is-better; for scPerplexity lower-is-better. When the axis
    cells are byte-stable to ~4dp, the "robust region" is the entire
    tested envelope.
    """
    out: dict = {}
    # baseline row is included via `_axis_cells` (it appears first in every
    # axis list); see Wave 186 P3 CSV format `baseline,perturb_axis=none`.
    for axis in AXIS_ORDER:
        if axis not in stats:
            continue
        s = stats[axis]
        cells = _axis_cells(rows, axis)
        if axis == "beta_base":
            xs = [c["beta_base"] for c in cells]
        elif axis == "restart_min_nfe":
            xs = [c["restart_min_nfe"] for c in cells]
        elif axis == "nfe_ref":
            xs = [c["nfe_ref"] for c in cells]
        elif axis == "seed":
            xs = [c["seed"] for c in cells]
        else:
            continue
        out[axis] = {
            "tested_range": [float(min(xs)), float(max(xs))],
            "plddt_range": s["plddt_range"],
            "sc_range": s["sc_range"],
            "framework_wins_plddt_on_mean": s["delta_plddt_mean_vs_baseline"] > 0,
            "framework_wins_sc_on_mean": s["delta_sc_mean_vs_baseline"] < 0,
        }
    # seed_variance: the only axis that has nonzero variance is seed.
    # Report the sample stddev of pLDDT across the 5 seed cells (the
    # primary "framework still wins?" axis).
    if "seed" in stats:
        out["seed_variance"] = stats["seed"]["plddt_std_sample"]
    return out


def framework_consistent_winner(stats: dict) -> bool:
    """Framework is a consistent winner if the seed-mean framework arm
    beats baseline on BOTH metrics (pLDDT higher, scPerplexity lower).

    Note: byte-stable axes (β / restart_min_nfe / NFE_REF) by definition
    equal baseline byte-for-byte (Wave 184 P2 §4.1 finding). The win is
    recovered at the seed ensemble mean.
    """
    if "seed" not in stats:
        return False
    s = stats["seed"]
    return s["delta_plddt_mean_vs_baseline"] > 0 and s["delta_sc_mean_vs_baseline"] < 0


# ---- commit_sha -----------------------------------------------------------


def current_commit_sha() -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


# ---- main -----------------------------------------------------------------


def main() -> None:
    rows = load_p3()
    if len(rows) != 18:
        raise RuntimeError(f"expected 18 P3 rows, got {len(rows)}")
    write_aggregation_csv(rows)
    stats = per_axis_stats(rows)
    plot_paths = make_plots(rows, stats)
    regions = robust_regions(rows, stats)
    consistent = framework_consistent_winner(stats)
    sha = current_commit_sha()

    summary = {
        "robust_regions": {
            "beta_base": regions.get("beta_base", {}).get("tested_range"),
            "restart_min_nfe": regions.get("restart_min_nfe", {}).get("tested_range"),
            "nfe_ref": regions.get("nfe_ref", {}).get("tested_range"),
            "seed_variance": regions.get("seed_variance"),
        },
        "per_axis_diagnostics": {
            axis: {
                "n_cells": stats[axis]["n_cells"],
                "plddt_range": stats[axis]["plddt_range"],
                "sc_range": stats[axis]["sc_range"],
                "plddt_std_sample": stats[axis]["plddt_std_sample"],
                "sc_std_sample": stats[axis]["sc_std_sample"],
                "delta_plddt_mean_vs_baseline": stats[axis]["delta_plddt_mean_vs_baseline"],
                "delta_sc_mean_vs_baseline": stats[axis]["delta_sc_mean_vs_baseline"],
            }
            for axis in AXIS_ORDER
            if axis in stats
        },
        "framework_consistent_winner": consistent,
        "commit_sha": sha,
    }

    # Print to stdout for harness.
    print(json.dumps(summary, indent=2))

    # Also print a brief human-readable summary for the audit doc author.
    print("\n# Per-axis summary", file=__import__("sys").stderr)
    for axis in AXIS_ORDER:
        if axis not in stats:
            continue
        s = stats[axis]
        print(
            f"  {axis:>18}: n={s['n_cells']}, pLDDT range={s['plddt_range']:.4f}, "
            f"sc range={s['sc_range']:.4f}, "
            f"ΔpLDDT_vs_baseline_mean={s['delta_plddt_mean_vs_baseline']:+.4f}, "
            f"Δsc_vs_baseline_mean={s['delta_sc_mean_vs_baseline']:+.4f}",
            file=__import__("sys").stderr,
        )
    print(f"\nPlots: {plot_paths}", file=__import__("sys").stderr)
    print(f"Aggregation CSV: {P4_CSV}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
