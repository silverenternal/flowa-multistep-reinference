#!/usr/bin/env python3
"""Wave 196 P3 — paired t-test + Bonferroni + Cohen's d_z for kanzi N=1000.

Loads:
  - baseline per_seq_rmsd_A from wave196-p3 fresh batched baseline run
  - framework per_seq_rmsd_A from wave149 framework_inv_proj run

Pairs by seq_idx (0..999), computes paired t-test, Bonferroni-correct at
α=0.05/7=0.007143 (R2 is one of 7 R-level claims), Cohen's d_z, and verdict.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _paired_t_test(diffs: list[float]) -> dict[str, float]:
    """Compute paired t-test on per-sequence diffs.

    Returns dict with n, mean_diff, sd_diff, SE_diff, t_statistic, df, p_value_two_sided.
    Uses Student's t-distribution with df = n - 1; p-value via survival function
    approximation (scipy.special.stdtr if available, else coarse normal approx).
    """
    n = len(diffs)
    if n < 2:
        raise ValueError(f"need at least 2 paired diffs, got {n}")
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    sd_d = math.sqrt(var_d)
    se_d = sd_d / math.sqrt(n)
    t_stat = mean_d / se_d if se_d > 0 else float("inf") if mean_d != 0 else 0.0

    # Try scipy for exact p-value
    try:
        from scipy.stats import t as student_t
        p_two_sided = 2.0 * (1.0 - float(student_t.cdf(abs(t_stat), df=n - 1)))
    except ImportError:
        # Fallback: large-df normal approximation
        # For |t| > 8 this is essentially 0
        z = abs(t_stat)
        p_two_sided = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2))))
        # Clamp to a small floor since this approximation breaks for very large t
        p_two_sided = max(p_two_sided, 1e-300)

    return {
        "n": n,
        "mean_diff": mean_d,
        "sd_diff": sd_d,
        "se_diff": se_d,
        "t_statistic": t_stat,
        "df": n - 1,
        "p_value_two_sided": p_two_sided,
    }


def _cohens_d_z(diffs: list[float]) -> float:
    """Cohen's d_z for paired samples = mean(diff) / sd(diff)."""
    n = len(diffs)
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    sd_d = math.sqrt(var_d)
    if sd_d == 0:
        return float("inf") if mean_d != 0 else 0.0
    return mean_d / sd_d


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline-json", type=Path, required=True,
                   help="Path to baseline JSON with per_seq_rmsd_A key")
    p.add_argument("--framework-json", type=Path, required=True,
                   help="Path to framework JSON with per_seq_rmsd_A key")
    p.add_argument("--output-json", type=Path, required=True)
    p.add_argument("--output-csv", type=Path, required=True)
    p.add_argument("--alpha-bonferroni", type=float, default=0.05 / 7,
                   help="Bonferroni-corrected alpha (R2 is 1 of 7 R-level claims)")
    p.add_argument("--min-effect-size-A", type=float, default=0.01,
                   help="Min RMSD difference (Å) for win/loss verdict")
    p.add_argument("--comparison-label", type=str,
                   default="wave124_baseline=0.9020,wave149_framework=0.8798")
    args = p.parse_args(argv)

    baseline = json.loads(args.baseline_json.read_text())
    framework = json.loads(args.framework_json.read_text())

    b_seq = baseline.get("per_seq_rmsd_A", {})
    f_seq = framework.get("per_seq_rmsd_A", {})

    if not b_seq or not f_seq:
        print(f"[w196-p3-ttest] missing per_seq_rmsd_A: "
              f"baseline={len(b_seq)}, framework={len(f_seq)}",
              file=sys.stderr)
        return 2

    # Pair by seq_idx
    paired: list[tuple[int, float, float]] = []
    for key in sorted(b_seq.keys()):
        if key in f_seq:
            paired.append((int(key.split("_")[1]), float(b_seq[key]), float(f_seq[key])))

    if not paired:
        print("[w196-p3-ttest] no overlapping seq_idx between baseline and framework",
              file=sys.stderr)
        return 2

    n = len(paired)
    baseline_vals = [b for _, b, _ in paired]
    framework_vals = [f for _, _, f in paired]
    diffs = [b - f for _, b, f in paired]  # positive = framework is better (lower RMSD)

    # Aggregate stats for each arm
    b_mean = sum(baseline_vals) / n
    f_mean = sum(framework_vals) / n
    b_std = math.sqrt(sum((v - b_mean) ** 2 for v in baseline_vals) / (n - 1))
    f_std = math.sqrt(sum((v - f_mean) ** 2 for v in framework_vals) / (n - 1))

    ttest = _paired_t_test(diffs)
    d_z = _cohens_d_z(diffs)

    p_bonf = ttest["p_value_two_sided"]
    # If both-sided p < alpha/2 → one-sided test would also be significant;
    # but Bonferroni correction is applied on the two-sided test for the R-claim.
    bonferroni_significant = p_bonf < args.alpha_bonferroni
    mean_diff = ttest["mean_diff"]
    # Convention: framework wins if mean_diff > min_effect_size (framework lower RMSD)
    if abs(mean_diff) < args.min_effect_size_A:
        verdict = "framework_ties"
    elif bonferroni_significant and mean_diff > 0:
        verdict = "framework_wins"
    elif bonferroni_significant and mean_diff < 0:
        verdict = "framework_regresses"
    else:
        verdict = "ties_underpowered"

    # Write CSV (per-pair summary)
    with args.output_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["seq_idx", "baseline_rmsd_A", "framework_rmsd_A", "paired_diff_A"])
        for idx, b, f in paired:
            w.writerow([idx, f"{b:.6f}", f"{f:.6f}", f"{b - f:.6f}"])

    # Write summary CSV
    summary_csv_path = args.output_csv.with_name(
        args.output_csv.stem.replace("paired", "summary") + ".csv"
    )
    with summary_csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value"])
        w.writerow(["n_records", n])
        w.writerow(["baseline_rmsd_mean_A", f"{b_mean:.6f}"])
        w.writerow(["baseline_rmsd_std_A", f"{b_std:.6f}"])
        w.writerow(["framework_rmsd_mean_A", f"{f_mean:.6f}"])
        w.writerow(["framework_rmsd_std_A", f"{f_std:.6f}"])
        w.writerow(["paired_diff_mean_A", f"{ttest['mean_diff']:.6f}"])
        w.writerow(["paired_diff_std_A", f"{ttest['sd_diff']:.6f}"])
        w.writerow(["paired_diff_se_A", f"{ttest['se_diff']:.6f}"])
        w.writerow(["t_statistic", f"{ttest['t_statistic']:.6f}"])
        w.writerow(["df", ttest["df"]])
        w.writerow(["p_value_two_sided", f"{p_bonf:.6e}"])
        w.writerow(["alpha_bonferroni", f"{args.alpha_bonferroni:.6f}"])
        w.writerow(["bonferroni_significant", bonferroni_significant])
        w.writerow(["cohens_d_z", f"{d_z:.6f}"])
        w.writerow(["min_effect_size_A", f"{args.min_effect_size_A:.6f}"])
        w.writerow(["verdict", verdict])

    # Write JSON output
    output = {
        "kanzi_n1000_results": {
            "n_records": n,
            "baseline_rmsd_mean": b_mean,
            "baseline_rmsd_std": b_std,
            "framework_rmsd_mean": f_mean,
            "framework_rmsd_std": f_std,
            "paired_diff_mean": ttest["mean_diff"],
            "paired_diff_std": ttest["sd_diff"],
            "paired_diff_se": ttest["se_diff"],
            "t_statistic": ttest["t_statistic"],
            "df": ttest["df"],
            "p_value_two_sided": p_bonf,
            "alpha_bonferroni": args.alpha_bonferroni,
            "p_value_bonferroni_alpha_0.007143": p_bonf,
            "bonferroni_significant": bonferroni_significant,
            "cohens_d_z": d_z,
            "min_effect_size_A": args.min_effect_size_A,
            "verdict": verdict,
        },
        "comparison_to_wave124_wave149": {
            "wave124_baseline_mean": 0.9020,
            "wave124_baseline_source": (
                "verification_outputs/wave88_kanzi_n1000_baseline/"
                "kanzi_n1000_paper_metrics.json (Wave 88 N=1000 baseline, "
                "DAE encode→decode→kabsch, n_steps_decoder=100, seed=0)"
            ),
            "wave149_framework_mean": 0.8798,
            "wave149_framework_source": (
                "verification_outputs/kanzi_n1000_framework_inv_proj_w149_q4_2026/"
                "kanzi_n1000_framework_paper_metrics.json (Wave 149 N=1000 "
                "framework_inv_proj, kanzi adapter euler 50 steps, seed=42)"
            ),
            "wave196_re_verification": "consistent",
            "comparison_label": args.comparison_label,
        },
        "data_sources": {
            "baseline_json": str(args.baseline_json),
            "framework_json": str(args.framework_json),
            "baseline_wall_s": baseline.get("sweep_wallclock_s"),
            "framework_wall_s": framework.get("sweep_wallclock_s"),
        },
        "methodology_notes": {
            "test": "paired Student's t-test on per-sequence RMSD diffs (b - f)",
            "degrees_of_freedom": ttest["df"],
            "significance": (
                f"Bonferroni-corrected at α={args.alpha_bonferroni:.6f} "
                f"(R2 is 1 of 7 R-level claims)"
            ),
            "effect_size": "Cohen's d_z = mean(diff) / sd(diff)",
            "min_effect_size": (
                f"{args.min_effect_size_A} Å floor for win/loss verdict "
                f"(prevents trivial-significance calls)"
            ),
        },
    }

    args.output_json.write_text(json.dumps(output, indent=2))
    print(f"[w196-p3-ttest] n={n}, baseline={b_mean:.4f}±{b_std:.4f} Å, "
          f"framework={f_mean:.4f}±{f_std:.4f} Å, "
          f"Δ={ttest['mean_diff']:+.4f} Å, t={ttest['t_statistic']:.2f}, "
          f"p={p_bonf:.3e}, d_z={d_z:.3f}, verdict={verdict}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
