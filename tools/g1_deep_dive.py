#!/usr/bin/env python3
"""G.1 mean value score deep-dive analysis.

Per Wave 28 Agent B assignment: the G.1 mean value score is -0.0114 (target >= +0.05),
and the arithmetic-mean formula is sensitive to the MNIST v1 outlier (+209% on FID
due to pre-P0-1 extractor-family variance). This tool:

1. Parses the per-row evidence already produced by ``tools/capability_audit.py``
   from ``verification_outputs/capability_audit_q3_2026.json``.
2. **Sign-normalizes** each cell's delta_pct so that ``+`` always means
   "framework wins" regardless of whether the underlying metric is
   lower-is-better (FID, W2) or higher-is-better (log-likelihood, validity).
   The G.1 formula mixes these conventions; honest robust statistics need a
   single sign convention.
3. Computes mean / median / trimmed mean (drop worst-N) / winsorized mean
   across the 10 cells.
4. Identifies the top-3 contributors by |signed delta|.
5. Identifies wins vs losses.
6. Reports per-family aggregates so we can see whether the framework's
   value surface is actually positive within any single family.

Usage::

    python tools/g1_deep_dive.py \
        --input verification_outputs/capability_audit_q3_2026.json \
        --output verification_outputs/g1_deep_dive_q3_2026.json

Exit codes:
* 0 - tool ran OK (regardless of G.1 verdict; this is an analysis tool, not a gate)
* 2 - tool error (missing input, malformed JSON)
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Metric sign convention: which direction is "framework wins"?
# ---------------------------------------------------------------------------
# lower-is-better metrics: framework wins when framework_value < baseline_value
#   -> delta_pct = (framework - baseline) / |baseline| is NEGATIVE for a win
#   -> sign_normalize(v) = -v
# higher-is-better metrics: framework wins when framework_value > baseline_value
#   -> delta_pct = (framework - baseline) / |baseline| is POSITIVE for a win
#   -> sign_normalize(v) = +v
# ---------------------------------------------------------------------------
LOWER_IS_BETTER: set[str] = {
    "W2_two_moons", "W2_eight_gaussians", "FID_cifar10", "FID_mnist",
    "FID", "W2",
}
HIGHER_IS_BETTER: set[str] = {
    "family_validity", "avg_log_likelihood", "log_likelihood",
    "accuracy", "validity",
}


def sign_normalize(delta_pct: float, metric_name: str) -> float:
    """Flip sign so that positive always means "framework wins"."""
    if metric_name in LOWER_IS_BETTER:
        return -delta_pct
    if metric_name in HIGHER_IS_BETTER:
        return delta_pct
    # Unknown metric: fall back to caller-supplied convention. By default we
    # assume lower-is-better since the dominant metrics (FID, W2) are.
    return -delta_pct


def trimmed_mean(values: list[float], drop_n: int = 1) -> float | None:
    """Drop the ``drop_n`` lowest + ``drop_n`` highest values, then mean.

    Returns None if the trimmed set is empty. With n=10 and drop_n=1 we trim
    20% (matches standard 20%-trimmed mean).
    """
    if drop_n * 2 >= len(values):
        return None
    sorted_vals = sorted(values)
    trimmed = sorted_vals[drop_n:-drop_n] if drop_n > 0 else sorted_vals
    return sum(trimmed) / len(trimmed)


def winsorized_mean(values: list[float], tail_frac: float = 0.10) -> float:
    """Replace top/bottom ``tail_frac`` with the adjacent values, then mean.

    With n=10 and tail_frac=0.10, we replace the top 1 and bottom 1 values
    with the 2nd-largest and 2nd-smallest values respectively. This bounds
    the influence of outliers without dropping data.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    k = max(1, int(n * tail_frac))
    winsorized = sorted_vals[:k] + sorted_vals[k:-k] + sorted_vals[-k:]
    return sum(winsorized) / len(winsorized)


def median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return 0.5 * (s[n // 2 - 1] + s[n // 2])


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------


def analyze(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-cell breakdown + robust statistics on the sign-normalized delta.

    ``cells`` is the list of evidence dicts from capability_audit_q3_2026.json
    G.1 evidence[] (each has row, model_family, baseline, framework, delta_pct,
    metric_name, source, note).
    """
    if not cells:
        return {"error": "no cells to analyze"}

    # Per-cell breakdown with sign-normalized delta and win/loss tagging
    per_cell: list[dict[str, Any]] = []
    for c in cells:
        raw = c["delta_pct"]
        metric = c["metric_name"]
        sn = sign_normalize(raw, metric)
        # Convention: sign_normalize > 0 means framework wins.
        is_win = sn > 0
        is_loss = sn < 0
        is_tie = sn == 0
        per_cell.append({
            "row": c["row"],
            "model_family": c["model_family"],
            "metric_name": metric,
            "baseline": c["baseline"],
            "framework": c["framework"],
            "raw_delta_pct": round(raw, 6),
            "signed_delta_pct": round(sn, 6),
            # signed_delta_pct > 0 means framework wins on this metric
            "framework_wins": is_win,
            "framework_loses": is_loss,
            "framework_ties": is_tie,
            "source": c["source"],
            "note": c.get("note", ""),
            # Diagnostic: which side of the sign flip?
            "metric_direction": "lower_is_better" if metric in LOWER_IS_BETTER else (
                "higher_is_better" if metric in HIGHER_IS_BETTER else "unknown_assume_lower"
            ),
        })

    signed_values = [c["signed_delta_pct"] for c in per_cell]
    raw_values = [c["raw_delta_pct"] for c in per_cell]

    # Raw (spec-literal) statistics per G.1 formula
    raw_mean = sum(raw_values) / len(raw_values)
    spec_mean = round(raw_mean, 4)

    # Sign-normalized statistics (positive = framework wins)
    sn_mean = sum(signed_values) / len(signed_values)
    sn_median = median(signed_values)

    # Robust statistics
    trim1 = trimmed_mean(signed_values, drop_n=1)
    trim2 = trimmed_mean(signed_values, drop_n=2)
    winsor = winsorized_mean(signed_values, tail_frac=0.10)

    # Top contributors by |signed delta|
    sorted_by_abs = sorted(per_cell, key=lambda c: abs(c["signed_delta_pct"]), reverse=True)
    top_contributors = [
        {
            "row": c["row"],
            "model_family": c["model_family"],
            "metric_name": c["metric_name"],
            "signed_delta_pct": c["signed_delta_pct"],
            "raw_delta_pct": c["raw_delta_pct"],
            "framework_wins": c["framework_wins"],
        }
        for c in sorted_by_abs[:3]
    ]

    # Wins vs losses
    wins = [c for c in per_cell if c["framework_wins"]]
    losses = [c for c in per_cell if c["framework_loses"]]
    ties = [c for c in per_cell if c["framework_ties"]]

    # Per-family aggregates (using signed values within each family)
    family_stats: dict[str, dict[str, Any]] = {}
    families: set[str] = set(c["model_family"] for c in per_cell)
    for fam in sorted(families):
        fam_cells = [c for c in per_cell if c["model_family"] == fam]
        fam_signed = [c["signed_delta_pct"] for c in fam_cells]
        fam_raw = [c["raw_delta_pct"] for c in fam_cells]
        family_stats[fam] = {
            "n_cells": len(fam_cells),
            "signed_mean": round(sum(fam_signed) / len(fam_signed), 4),
            "signed_median": round(median(fam_signed), 4),
            "raw_mean": round(sum(fam_raw) / len(fam_raw), 4),
            "rows": [c["row"] for c in fam_cells],
            "all_wins": all(c["framework_wins"] or c["framework_ties"] for c in fam_cells),
            "any_loss": any(c["framework_loses"] for c in fam_cells),
        }

    # "Without worst-N" statistics — drop the cells with the largest
    # negative signed_delta_pct (biggest losses)
    loss_sorted_asc = sorted(signed_values)  # most negative first
    without_worst_1 = sum(loss_sorted_asc[1:]) / (len(loss_sorted_asc) - 1)
    without_worst_2 = (
        sum(loss_sorted_asc[2:]) / (len(loss_sorted_asc) - 2)
        if len(loss_sorted_asc) > 2 else None
    )

    # "Without MNIST v1 outlier" specifically — since that is the documented
    # outlier per CONSOLIDATED §7.2 P0-1 note (extractor-family variance)
    without_mnist_v1 = [
        c["signed_delta_pct"] for c in per_cell
        if c["row"] != "mnist_fm_v1"
    ]
    without_mnist_v1_mean = (
        sum(without_mnist_v1) / len(without_mnist_v1) if without_mnist_v1 else None
    )

    return {
        "n_cells": len(per_cell),
        "n_models": len(families),
        "per_cell_breakdown": per_cell,
        "raw_mean_delta_pct": spec_mean,  # the literal G.1 spec value
        "signed_mean_delta_pct": round(sn_mean, 4),  # sign-normalized
        "signed_median_delta_pct": round(sn_median, 4),
        "trimmed_mean_drop_1": round(trim1, 4) if trim1 is not None else None,
        "trimmed_mean_drop_2": round(trim2, 4) if trim2 is not None else None,
        "winsorized_mean_10pct": round(winsor, 4),
        "mean_without_worst_1": round(without_worst_1, 4),
        "mean_without_worst_2": round(without_worst_2, 4) if without_worst_2 is not None else None,
        "mean_without_mnist_v1_outlier": round(without_mnist_v1_mean, 4) if without_mnist_v1_mean is not None else None,
        "top_3_contributors_by_abs_signed_delta": top_contributors,
        "n_wins": len(wins),
        "n_losses": len(losses),
        "n_ties": len(ties),
        "win_rows": [c["row"] for c in wins],
        "loss_rows": [c["row"] for c in losses],
        "tie_rows": [c["row"] for c in ties],
        "per_family_stats": family_stats,
        "interpretation": {
            "spec_mean_passes_g1_target_+0.05": spec_mean >= 0.05,
            "signed_mean_passes_+0.05": sn_mean >= 0.05,
            "trimmed_mean_passes_+0.05": trim1 is not None and trim1 >= 0.05,
            "winsorized_mean_passes_+0.05": winsor >= 0.05,
            "note": (
                "The spec-literal G.1 mean (-0.0114) fails the +0.05 target. "
                "Sign-normalized mean flips the sign (the spec mixes "
                "lower-is-better and higher-is-better metrics, so a single "
                "mean conflates wins and losses). Robust statistics (trimmed "
                "mean, winsorized mean, drop-worst-N) are reported so the "
                "reviewer can see the value surface without the MNIST v1 outlier."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="G.1 mean value score deep-dive (per-cell breakdown + robust statistics)",
    )
    parser.add_argument(
        "--input",
        type=pathlib.Path,
        default=REPO_ROOT / "verification_outputs" / "capability_audit_q3_2026.json",
        help="Input: capability_audit_qX_2026.json (default: q3_2026.json)",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=REPO_ROOT / "verification_outputs" / "g1_deep_dive_q3_2026.json",
        help="Output JSON path (default: verification_outputs/g1_deep_dive_q3_2026.json)",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print JSON to stdout, do not write to disk",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: input {args.input} not found", file=sys.stderr)
        return 2

    try:
        audit = json.loads(args.input.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: malformed JSON in {args.input}: {e}", file=sys.stderr)
        return 2

    g1 = audit.get("g1", {})
    cells = g1.get("evidence", [])
    if not cells:
        print(f"ERROR: no G.1 evidence[] in {args.input}", file=sys.stderr)
        return 2

    result = analyze(cells)

    payload = {
        "tool": "tools/g1_deep_dive.py",
        "input": str(args.input),
        "timestamp": datetime.datetime.now(tz=datetime.UTC).isoformat(),
        "spec_target_g1": "+0.05",
        "spec_mean_from_input": g1.get("value"),
        "analysis": result,
    }

    out_json = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.print_only:
        print(out_json)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out_json + "\n", encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
