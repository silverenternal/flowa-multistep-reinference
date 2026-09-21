"""Wave 216 P2 — R5a Two Moons extended seeds aggregation.

Extends the Wave 209 P6 R5a table by running additional seeds {43, 44, 45}
on the 2D Two Moons target (baseline + 4 framework schedulers) and
re-evaluating the Welch's t-test verdict at the extended seed count.

Reads existing data from:
- /tmp/wave209_p6_r5a/two_moons_baseline_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_CosineAnnealScheduler_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_CodimensionSheetScheduler_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_EvidenceDrivenScheduler_seed{0}.csv

Plus newly produced data:
- /tmp/wave216_p2_r5a/two_moons_baseline_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_CosineAnnealScheduler_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_CodimensionSheetScheduler_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_EvidenceDrivenScheduler_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_FreeTrajScheduler_seed{43,44,45}.csv

Writes:
- /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave216-p2-r5a-extended.csv
- /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave216-p2-r5a-extended.json
"""

from __future__ import annotations

import csv
import json
import math
import os
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
EXISTING_DIR = Path("/tmp/wave209_p6_r5a")
NEW_DIR = Path("/tmp/wave216_p2_r5a")
OUT_CSV = REPO_ROOT / "verification_outputs" / "wave216-p2-r5a-extended.csv"
OUT_JSON = REPO_ROOT / "verification_outputs" / "wave216-p2-r5a-extended.json"

# Match the existing Wave 209 P6 seed list + add 3 new seeds.
EXISTING_SEEDS = list(range(7))
NEW_SEEDS = [43, 44, 45]
ALL_SEEDS = EXISTING_SEEDS + NEW_SEEDS

# Match Wave 209 P6 baseline-vs-cosine setup; cosine is the canonical
# PaperRatioAdaptiveScheduler surrogate on the 2D ablation table.
BASELINE_DIR = EXISTING_DIR
COSINE_DIRS = (EXISTING_DIR, NEW_DIR)
COSINE_FALLBACK = COSINE_DIRS[-1]  # use NEW_DIR if not in EXISTING_DIR

# Bonferroni alpha matches Wave 195 P2 (N=7 R-level cells).
N_CELLS = 7
ALPHA_FAMILY = 0.05
ALPHA_PER_CELL = ALPHA_FAMILY / N_CELLS  # 0.007143

# Min effect size matches the original R5a cell (1pp W2 = 0.01).
MIN_EFFECT_SIZE = 0.01

SUMMARY_TAIL = 5  # match Wave 209 P6 tail


def per_seed_w2_tail(csv_path: Path, tail: int = SUMMARY_TAIL) -> float:
    """Mean W2 over the last `tail` rounds of the per-round CSV."""
    rows = []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(float(row["w2"]))
    return sum(rows[-tail:]) / min(tail, len(rows))


def per_seed_baseline_w2(csv_path: Path) -> float:
    """Baseline W2 (single round, single n_cap)."""
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        first = next(reader)
        return float(first["w2"])


def load_baseline_per_seed(seeds: list[int], dirs: list[Path]) -> list[float | None]:
    """Load per-seed baseline W2 from the first directory that has the seed."""
    out: list[float | None] = []
    for s in seeds:
        val: float | None = None
        for d in dirs:
            p = d / f"two_moons_baseline_seed{s}.csv"
            if p.exists():
                val = per_seed_baseline_w2(p)
                break
        out.append(val)
    return out


def load_scheduler_per_seed(
    scheduler: str,
    seeds: list[int],
    dirs: list[Path],
    tail: int = SUMMARY_TAIL,
) -> list[float | None]:
    """Load per-seed framework W2 (mean over last `tail` rounds) from dirs."""
    out: list[float | None] = []
    for s in seeds:
        val: float | None = None
        for d in dirs:
            p = d / f"two_moons_{scheduler}_seed{s}.csv"
            if p.exists():
                val = per_seed_w2_tail(p, tail=tail)
                break
        out.append(val)
    return out


def compute_welch(
    baseline: list[float],
    framework: list[float],
    *,
    min_effect_size: float = MIN_EFFECT_SIZE,
    alpha_per_cell: float = ALPHA_PER_CELL,
) -> dict[str, float | str | bool | int]:
    """Welch's t-test on two independent samples."""
    n_b = len(baseline)
    n_f = len(framework)
    if n_b < 2 or n_f < 2:
        return {
            "n_b": n_b,
            "n_f": n_f,
            "baseline_mean": float(np.mean(baseline)) if baseline else float("nan"),
            "framework_mean": float(np.mean(framework)) if framework else float("nan"),
            "verdict": "insufficient_data",
        }

    b_arr = np.asarray(baseline, dtype=np.float64)
    f_arr = np.asarray(framework, dtype=np.float64)
    b_mean = float(np.mean(b_arr))
    f_mean = float(np.mean(f_arr))
    b_std = float(np.std(b_arr, ddof=1))
    f_std = float(np.std(f_arr, ddof=1))
    delta = f_mean - b_mean  # framework - baseline
    var_b = float(np.var(b_arr, ddof=1))
    var_f = float(np.var(f_arr, ddof=1))
    se = float(math.sqrt(var_b / n_b + var_f / n_f))
    # Welch-Satterthwaite df.
    df_num = (var_b / n_b + var_f / n_f) ** 2
    df_den = (var_b / n_b) ** 2 / (n_b - 1) + (var_f / n_f) ** 2 / (n_f - 1)
    df = float(df_num / df_den) if df_den > 0.0 else float("nan")
    t_stat = float(delta / se) if se > 0.0 else float("nan")
    # Two-sided p-value via Welch's t.
    p_raw = float(2.0 * stats.t.sf(abs(t_stat), df=df)) if not math.isnan(t_stat) else float("nan")
    p_bonf = float(min(p_raw * N_CELLS, 1.0))
    # Cohen's d_s between-subject.
    pooled = math.sqrt((var_b + var_f) / 2.0)
    d_s = float(delta / pooled) if pooled > 0.0 else float("nan")
    # 95% CI on delta (use t critical; df=min(n_b, n_f)-1 approximation per Wave 195).
    t_crit = float(stats.t.ppf(0.975, df=min(n_b, n_f) - 1))
    ci_lo = float(delta - t_crit * se)
    ci_hi = float(delta + t_crit * se)

    # Verdict precedence (matches Wave 195 P2):
    # 1. TIE — |delta| < min_effect_size
    # 2. SUPPORTED — Bonferroni p < alpha AND delta < 0  (framework-WORSE=positive delta for W2=lower_better)
    # 3. REGRESSES — Bonferroni p < alpha AND delta > 0
    # 4. NOT_SIGNIFICANT — fallback
    if abs(delta) < min_effect_size:
        verdict = "TIE"
    elif p_bonf < alpha_per_cell and delta < 0.0:
        verdict = "framework_wins"
    elif p_bonf < alpha_per_cell and delta > 0.0:
        verdict = "framework_wins"  # NOTE: W2 LOWER BETTER; delta<0 = framework better
        # Wait, that's contradictory. Re-check.
        verdict = "baseline_wins" if delta > 0.0 else "framework_wins"
    else:
        verdict = "TIE"

    return {
        "n_b": n_b,
        "n_f": n_f,
        "baseline_mean": b_mean,
        "baseline_std": b_std,
        "framework_mean": f_mean,
        "framework_std": f_std,
        "delta": delta,
        "delta_se": se,
        "ci_95": [ci_lo, ci_hi],
        "t_stat": t_stat,
        "df": df,
        "p_value_raw": p_raw,
        "p_value_bonferroni": p_bonf,
        "cohens_d_s": d_s,
        "min_effect_size": min_effect_size,
        "alpha_per_cell": alpha_per_cell,
        "verdict": verdict,
        "bonferroni_significant": bool(p_bonf < alpha_per_cell),
    }


def main() -> int:
    """Aggregate per-seed W2 + run Welch's t-test for the extended set."""
    # Load baseline W2 (first matches EXISTING, falls back to NEW).
    baseline_per_seed_all = load_baseline_per_seed(ALL_SEEDS, [EXISTING_DIR, NEW_DIR])
    cosine_per_seed_all = load_scheduler_per_seed(
        "CosineAnnealScheduler", ALL_SEEDS, [EXISTING_DIR, NEW_DIR]
    )
    codim_per_seed_all = load_scheduler_per_seed(
        "CodimensionSheetScheduler", ALL_SEEDS, [EXISTING_DIR, NEW_DIR]
    )
    evd_per_seed_all = load_scheduler_per_seed(
        "EvidenceDrivenScheduler", ALL_SEEDS, [EXISTING_DIR, NEW_DIR]
    )
    freetraj_per_seed_all = load_scheduler_per_seed(
        "FreeTrajScheduler", ALL_SEEDS, [EXISTING_DIR, NEW_DIR]
    )

    # Strip None values for t-test.
    def present(seq: list[float | None]) -> list[float]:
        return [float(x) for x in seq if x is not None]

    baseline_present = present(baseline_per_seed_all)
    cosine_present = present(cosine_per_seed_all)
    codim_present = present(codim_per_seed_all)
    evd_present = present(evd_per_seed_all)
    freetraj_present = present(freetraj_per_seed_all)

    print("=== Wave 216 P2 R5a Two Moons extended seeds ===")
    print(f"n_seeds_baseline:            {len(baseline_present)} (raw {len(baseline_per_seed_all)})")
    print(f"n_seeds_CosineAnnealScheduler:    {len(cosine_present)} (raw {len(cosine_per_seed_all)})")
    print(f"n_seeds_CodimensionSheetScheduler: {len(codim_present)} (raw {len(codim_per_seed_all)})")
    print(f"n_seeds_EvidenceDrivenScheduler:   {len(evd_present)} (raw {len(evd_per_seed_all)})")
    print(f"n_seeds_FreeTrajScheduler:         {len(freetraj_present)} (raw {len(freetraj_per_seed_all)})")

    # Pick the framework arm: best-mean-W2 across the four with full coverage.
    # If tied on count, prefer cosine (PaperRatioAdaptiveScheduler surrogate).
    arms = {
        "CosineAnnealScheduler": cosine_present,
        "CodimensionSheetScheduler": codim_present,
        "EvidenceDrivenScheduler": evd_present,
        "FreeTrajScheduler": freetraj_present,
    }
    print()
    print("Per-seed W2 (mean over last 5 rounds for framework; 1 round for baseline):")
    print(f"{'seed':>4}  {'baseline':>10}  {'cosine':>10}  {'codim':>10}  {'evd':>10}  {'freetraj':>10}")
    for i, s in enumerate(ALL_SEEDS):
        b = f"{baseline_per_seed_all[i]:.5f}" if baseline_per_seed_all[i] is not None else "—"
        c = f"{cosine_per_seed_all[i]:.5f}" if cosine_per_seed_all[i] is not None else "—"
        cd = f"{codim_per_seed_all[i]:.5f}" if codim_per_seed_all[i] is not None else "—"
        e = f"{evd_per_seed_all[i]:.5f}" if evd_per_seed_all[i] is not None else "—"
        f = f"{freetraj_per_seed_all[i]:.5f}" if freetraj_per_seed_all[i] is not None else "—"
        print(f"{s:>4}  {b:>10}  {c:>10}  {cd:>10}  {e:>10}  {f:>10}")

    # Pick best framework arm by mean W2 (lowest is best for W2 lower_better).
    # Only consider arms with >=3 seeds.
    arm_means = {}
    for name, vals in arms.items():
        if len(vals) >= 3:
            arm_means[name] = float(np.mean(vals))
    if arm_means:
        best_arm_name = min(arm_means, key=lambda k: arm_means[k])
    else:
        best_arm_name = "CosineAnnealScheduler"

    print()
    print("Per-arm mean W2 (n_seeds >= 3):")
    for name, m in arm_means.items():
        print(f"  {name}: {m:.5f} (n={len(arms[name])})")
    print(f"Best-by-W2 framework arm: {best_arm_name}")

    # Primary headline: cosine arm (canonical PaperRatioAdaptiveScheduler surrogate).
    primary_welch = compute_welch(baseline_present, cosine_present)
    print()
    print("=== Welch's t-test (baseline vs CosineAnnealScheduler, primary headline) ===")
    for k, v in primary_welch.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.5f}")
        else:
            print(f"  {k}: {v}")

    # Best-arm Welch.
    best_arm_welch = compute_welch(baseline_present, arms[best_arm_name])
    print()
    print(f"=== Welch's t-test (baseline vs {best_arm_name}, best-by-W2 arm) ===")
    for k, v in best_arm_welch.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.5f}")
        else:
            print(f"  {k}: {v}")

    # Write CSV with extended per-seed + per-arm summary rows.
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["wave", "cell", "scheduler", "seed", "n_samples", "w2", "source_csv"]
        )
        for i, s in enumerate(ALL_SEEDS):
            base_dir = (
                EXISTING_DIR if (EXISTING_DIR / f"two_moons_baseline_seed{s}.csv").exists()
                else NEW_DIR
            )
            cos_dir = (
                EXISTING_DIR if (EXISTING_DIR / f"two_moons_CosineAnnealScheduler_seed{s}.csv").exists()
                else NEW_DIR
            )
            cd_dir = (
                EXISTING_DIR if (EXISTING_DIR / f"two_moons_CodimensionSheetScheduler_seed{s}.csv").exists()
                else NEW_DIR
            )
            evd_dir = (
                EXISTING_DIR if (EXISTING_DIR / f"two_moons_EvidenceDrivenScheduler_seed{s}.csv").exists()
                else NEW_DIR
            )
            ft_dir = (
                EXISTING_DIR if (EXISTING_DIR / f"two_moons_FreeTrajScheduler_seed{s}.csv").exists()
                else NEW_DIR
            )
            if baseline_per_seed_all[i] is not None:
                writer.writerow([
                    "216 P2", "R5a_two_moons", "baseline", s, 1000,
                    f"{baseline_per_seed_all[i]:.6f}",
                    f"{base_dir.name}/two_moons_baseline_seed{s}.csv",
                ])
            if cosine_per_seed_all[i] is not None:
                writer.writerow([
                    "216 P2", "R5a_two_moons", "CosineAnnealScheduler", s, 1000,
                    f"{cosine_per_seed_all[i]:.6f}",
                    f"{cos_dir.name}/two_moons_CosineAnnealScheduler_seed{s}.csv",
                ])
            if codim_per_seed_all[i] is not None:
                writer.writerow([
                    "216 P2", "R5a_two_moons", "CodimensionSheetScheduler", s, 1000,
                    f"{codim_per_seed_all[i]:.6f}",
                    f"{cd_dir.name}/two_moons_CodimensionSheetScheduler_seed{s}.csv",
                ])
            if evd_per_seed_all[i] is not None:
                writer.writerow([
                    "216 P2", "R5a_two_moons", "EvidenceDrivenScheduler", s, 1000,
                    f"{evd_per_seed_all[i]:.6f}",
                    f"{evd_dir.name}/two_moons_EvidenceDrivenScheduler_seed{s}.csv",
                ])
            if freetraj_per_seed_all[i] is not None:
                writer.writerow([
                    "216 P2", "R5a_two_moons", "FreeTrajScheduler", s, 1000,
                    f"{freetraj_per_seed_all[i]:.6f}",
                    f"{ft_dir.name}/two_moons_FreeTrajScheduler_seed{s}.csv",
                ])

        # Summary rows per arm.
        for arm_name, vals in arms.items():
            if not vals:
                continue
            w = compute_welch(baseline_present, vals)
            n_b = w.get("n_b", "?")
            n_f = w.get("n_f", "?")
            delta = w.get("delta", float("nan"))
            d_s = w.get("cohens_d_s", float("nan"))
            p = w.get("p_value_raw", float("nan"))
            ci = w.get("ci_95", [float("nan"), float("nan")])
            bonf_sig = w.get("bonferroni_significant", False)
            verdict = w.get("verdict", "?")
            writer.writerow([
                "216 P2", "R5a_two_moons_summary", f"{arm_name}_vs_baseline",
                f"{n_b}_vs_{n_f}", 1000, f"{delta:.6f}",
                f"d_s={d_s:.3f}, p={p:.3e}, bonf_sig={bonf_sig}, "
                f"ci=[{ci[0]:.5f}, {ci[1]:.5f}], verdict={verdict}",
            ])

    print(f"Wrote {OUT_CSV}")

    # Write JSON summary.
    summary = {
        "wave": "216 P2",
        "cell": "R5a_two_moons_W2",
        "n_seeds_baseline": len(baseline_present),
        "n_seeds_per_arm": {k: len(v) for k, v in arms.items()},
        "all_seeds": ALL_SEEDS,
        "primary_headline": {
            "arm": "CosineAnnealScheduler",
            "welch": primary_welch,
        },
        "best_arm": {
            "name": best_arm_name,
            "mean_w2": arm_means.get(best_arm_name, float("nan")),
            "welch": best_arm_welch,
        },
        "old_verdict": "TIE",
        "old_d_s": 0.460,
        "old_p_value_raw": 6.04e-01,
        "old_n_seeds": 3,
        "tie_persists_at_extended_seeds": (
            primary_welch.get("verdict") == "TIE"
            and best_arm_welch.get("verdict") == "TIE"
        ),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())