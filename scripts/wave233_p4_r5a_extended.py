"""Wave 233 P4 — R5a Two Moons seed expansion aggregation (n=30).

Aggregates per-seed W2 from the wave209 (n=7) + wave216 (n=3) + wave233
(n=20 new, seeds 10..29) runs into a single CSV+JSON reporting
baseline vs framework per-seed W2 + Welch's t-test verdict at n=30.

Reads existing data from:
- /tmp/wave209_p6_r5a/two_moons_baseline_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_CosineAnnealScheduler_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_CodimensionSheetScheduler_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_EvidenceDrivenScheduler_seed{0}.csv (partial)
- /tmp/wave216_p2_r5a/two_moons_baseline_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_CosineAnnealScheduler_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_CodimensionSheetScheduler_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_EvidenceDrivenScheduler_seed{43,44,45}.csv
- /tmp/wave216_p2_r5a/two_moons_FreeTrajScheduler_seed{43,44,45}.csv

Plus newly produced data:
- docs/r4-survey/two_moons_baseline_seed{10..29}.csv
- docs/r4-survey/two_moons_CosineAnnealScheduler_seed{10..29}.csv
- docs/r4-survey/two_moons_CodimensionSheetScheduler_seed{10..29}.csv
- docs/r4-survey/two_moons_EvidenceDrivenScheduler_seed{10..29}.csv
- docs/r4-survey/two_moons_FreeTrajScheduler_seed{10..29}.csv

Writes:
- /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave233-p4-r5a-expanded.csv
- /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave233-p4-r5a-expanded.json
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
EXISTING_DIR_209 = Path("/tmp/wave209_p6_r5a")
EXISTING_DIR_216 = Path("/tmp/wave216_p2_r5a")
NEW_DIR = REPO_ROOT / "docs" / "r4-survey"
OUT_CSV = REPO_ROOT / "verification_outputs" / "wave233-p4-r5a-expanded.csv"
OUT_JSON = REPO_ROOT / "verification_outputs" / "wave233-p4-r5a-expanded.json"

# Original seeds (wave209 + wave216): n=10
EXISTING_SEEDS = [0, 1, 2, 3, 4, 5, 6, 43, 44, 45]
# New seeds added in wave233 P4 (seeds 10..29): n=20 more
NEW_SEEDS = list(range(10, 30))
ALL_SEEDS = EXISTING_SEEDS + NEW_SEEDS  # n=30

# Bonferroni alpha matches Wave 195 P2 (N=7 R-level cells).
N_CELLS = 7
ALPHA_FAMILY = 0.05
ALPHA_PER_CELL = ALPHA_FAMILY / N_CELLS  # 0.007143

# Min effect size matches the original R5a cell (1pp W2 = 0.01).
MIN_EFFECT_SIZE = 0.01

SUMMARY_TAIL = 5  # match Wave 209 P6 tail

# Source directories to scan (in order). Wave216 only has seeds 43-45, wave209
# has 0-6. New docs/r4-survey/ has seeds 10-29 plus the leftover seed0-6 baselines.
ALL_SOURCE_DIRS = (EXISTING_DIR_209, EXISTING_DIR_216, NEW_DIR)


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


def load_baseline_per_seed(seeds: list[int]) -> tuple[list[float | None], list[Path]]:
    """Load per-seed baseline W2 from first source dir that has it. Returns (vals, src_paths)."""
    out_vals: list[float | None] = []
    out_src: list[Path] = []
    for s in seeds:
        val: float | None = None
        src: Path | None = None
        for d in ALL_SOURCE_DIRS:
            p = d / f"two_moons_baseline_seed{s}.csv"
            if p.exists():
                val = per_seed_baseline_w2(p)
                src = p
                break
        out_vals.append(val)
        out_src.append(src)  # type: ignore[arg-type]
    return out_vals, out_src


def load_scheduler_per_seed(
    scheduler: str, seeds: list[int]
) -> tuple[list[float | None], list[Path]]:
    """Load per-seed framework W2 (mean over last `tail` rounds)."""
    out_vals: list[float | None] = []
    out_src: list[Path] = []
    for s in seeds:
        val: float | None = None
        src: Path | None = None
        for d in ALL_SOURCE_DIRS:
            p = d / f"two_moons_{scheduler}_seed{s}.csv"
            if p.exists():
                val = per_seed_w2_tail(p, tail=SUMMARY_TAIL)
                src = p
                break
        out_vals.append(val)
        out_src.append(src)  # type: ignore[arg-type]
    return out_vals, out_src


def compute_welch(
    baseline: list[float],
    framework: list[float],
    *,
    min_effect_size: float = MIN_EFFECT_SIZE,
    alpha_per_cell: float = ALPHA_PER_CELL,
) -> dict[str, float | str | bool | int]:
    """Welch's t-test on two independent samples (W2 lower-better)."""
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
    delta = f_mean - b_mean  # framework - baseline (W2 lower-better)
    var_b = float(np.var(b_arr, ddof=1))
    var_f = float(np.var(f_arr, ddof=1))
    se = float(math.sqrt(var_b / n_b + var_f / n_f))
    df_num = (var_b / n_b + var_f / n_f) ** 2
    df_den = (var_b / n_b) ** 2 / (n_b - 1) + (var_f / n_f) ** 2 / (n_f - 1)
    df = float(df_num / df_den) if df_den > 0.0 else float("nan")
    t_stat = float(delta / se) if se > 0.0 else float("nan")
    p_raw = float(2.0 * stats.t.sf(abs(t_stat), df=df)) if not math.isnan(t_stat) else float("nan")
    p_bonf = float(min(p_raw * N_CELLS, 1.0))
    pooled = math.sqrt((var_b + var_f) / 2.0)
    d_s = float(delta / pooled) if pooled > 0.0 else float("nan")
    t_crit = float(stats.t.ppf(0.975, df=min(n_b, n_f) - 1))
    ci_lo = float(delta - t_crit * se)
    ci_hi = float(delta + t_crit * se)

    # Verdict precedence (matches Wave 195 P2 + Wave 216 P2):
    # 1. TIE — |delta| < min_effect_size
    # 2. FRAMEWORK_WINS — Bonferroni p < alpha AND delta < 0  (framework is better for W2 lower-better)
    # 3. BASELINE_WINS — Bonferroni p < alpha AND delta > 0  (baseline is better)
    # 4. TIE — fallback (not significant but |delta| >= min_effect_size)
    if abs(delta) < min_effect_size:
        verdict = "TIE"
    elif p_bonf < alpha_per_cell and delta < 0.0:
        verdict = "framework_WINS"
    elif p_bonf < alpha_per_cell and delta > 0.0:
        verdict = "baseline_WINS"
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
    """Aggregate per-seed W2 + run Welch's t-test for n=30."""
    baseline_per_seed, baseline_src = load_baseline_per_seed(ALL_SEEDS)
    cosine_per_seed, cosine_src = load_scheduler_per_seed("CosineAnnealScheduler", ALL_SEEDS)
    codim_per_seed, codim_src = load_scheduler_per_seed("CodimensionSheetScheduler", ALL_SEEDS)
    evd_per_seed, evd_src = load_scheduler_per_seed("EvidenceDrivenScheduler", ALL_SEEDS)
    freetraj_per_seed, freetraj_src = load_scheduler_per_seed("FreeTrajScheduler", ALL_SEEDS)

    def present(seq: list[float | None]) -> list[float]:
        return [float(x) for x in seq if x is not None]

    baseline_present = present(baseline_per_seed)
    cosine_present = present(cosine_per_seed)
    codim_present = present(codim_per_seed)
    evd_present = present(evd_per_seed)
    freetraj_present = present(freetraj_per_seed)

    print("=== Wave 233 P4 R5a Two Moons seed expansion (n=30) ===")
    print(f"n_seeds_baseline:                {len(baseline_present)} (raw {len(baseline_per_seed)})")
    print(f"n_seeds_CosineAnnealScheduler:    {len(cosine_present)} (raw {len(cosine_per_seed)})")
    print(f"n_seeds_CodimensionSheetScheduler: {len(codim_present)} (raw {len(codim_per_seed)})")
    print(f"n_seeds_EvidenceDrivenScheduler:   {len(evd_present)} (raw {len(evd_per_seed)})")
    print(f"n_seeds_FreeTrajScheduler:         {len(freetraj_present)} (raw {len(freetraj_per_seed)})")

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
        b = f"{baseline_per_seed[i]:.5f}" if baseline_per_seed[i] is not None else "—"
        c = f"{cosine_per_seed[i]:.5f}" if cosine_per_seed[i] is not None else "—"
        cd = f"{codim_per_seed[i]:.5f}" if codim_per_seed[i] is not None else "—"
        e = f"{evd_per_seed[i]:.5f}" if evd_per_seed[i] is not None else "—"
        f = f"{freetraj_per_seed[i]:.5f}" if freetraj_per_seed[i] is not None else "—"
        print(f"{s:>4}  {b:>10}  {c:>10}  {cd:>10}  {e:>10}  {f:>10}")

    # Per-arm mean W2 (only n>=3).
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

    # Primary headline: cosine (canonical PaperRatioAdaptiveScheduler surrogate).
    primary_welch = compute_welch(baseline_present, cosine_present)
    print()
    print("=== Welch's t-test (baseline vs CosineAnnealScheduler, primary headline) ===")
    for k, v in primary_welch.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.5f}")
        else:
            print(f"  {k}: {v}")

    best_arm_welch = compute_welch(baseline_present, arms[best_arm_name])
    print()
    print(f"=== Welch's t-test (baseline vs {best_arm_name}, best-by-W2 arm) ===")
    for k, v in best_arm_welch.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.5f}")
        else:
            print(f"  {k}: {v}")

    # Direction-consistency check: per-seed sign of (framework - baseline) W2.
    def direction_consistency(b: list[float | None], f: list[float | None]) -> dict[str, float]:
        paired = [
            (float(bi), float(fi))
            for bi, fi in zip(b, f)
            if bi is not None and fi is not None
        ]
        if not paired:
            return {"n_paired": 0, "frac_positive": float("nan")}
        n_pos = sum(1 for bi, fi in paired if fi - bi > 0)
        n_neg = sum(1 for bi, fi in paired if fi - bi < 0)
        n_zero = sum(1 for bi, fi in paired if fi - bi == 0)
        return {
            "n_paired": len(paired),
            "n_positive": n_pos,
            "n_negative": n_neg,
            "n_zero": n_zero,
            "frac_positive": n_pos / len(paired),
            "frac_negative": n_neg / len(paired),
        }

    dir_cos = direction_consistency(baseline_per_seed, cosine_per_seed)
    print()
    print("Direction-consistency (paired (framework - baseline) sign):")
    for arm_name, f_list in [
        ("CosineAnnealScheduler", cosine_per_seed),
        ("CodimensionSheetScheduler", codim_per_seed),
        ("EvidenceDrivenScheduler", evd_per_seed),
        ("FreeTrajScheduler", freetraj_per_seed),
    ]:
        d = direction_consistency(baseline_per_seed, f_list)
        if d["n_paired"] >= 1:
            print(
                f"  {arm_name:>30}: n_paired={d['n_paired']:>3}, "
                f"frac_positive={d.get('frac_positive', float('nan')):.3f}, "
                f"frac_negative={d.get('frac_negative', float('nan')):.3f}"
            )

    # Write CSV with per-seed + per-arm summary rows.
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["wave", "cell", "scheduler", "seed", "n_samples", "w2", "source_csv"]
        )
        for i, s in enumerate(ALL_SEEDS):
            if baseline_per_seed[i] is not None and baseline_src[i] is not None:
                writer.writerow([
                    "233 P4", "R5a_two_moons", "baseline", s, 1000,
                    f"{baseline_per_seed[i]:.6f}",
                    f"{baseline_src[i].parent.name}/{baseline_src[i].name}",
                ])
            if cosine_per_seed[i] is not None and cosine_src[i] is not None:
                writer.writerow([
                    "233 P4", "R5a_two_moons", "CosineAnnealScheduler", s, 1000,
                    f"{cosine_per_seed[i]:.6f}",
                    f"{cosine_src[i].parent.name}/{cosine_src[i].name}",
                ])
            if codim_per_seed[i] is not None and codim_src[i] is not None:
                writer.writerow([
                    "233 P4", "R5a_two_moons", "CodimensionSheetScheduler", s, 1000,
                    f"{codim_per_seed[i]:.6f}",
                    f"{codim_src[i].parent.name}/{codim_src[i].name}",
                ])
            if evd_per_seed[i] is not None and evd_src[i] is not None:
                writer.writerow([
                    "233 P4", "R5a_two_moons", "EvidenceDrivenScheduler", s, 1000,
                    f"{evd_per_seed[i]:.6f}",
                    f"{evd_src[i].parent.name}/{evd_src[i].name}",
                ])
            if freetraj_per_seed[i] is not None and freetraj_src[i] is not None:
                writer.writerow([
                    "233 P4", "R5a_two_moons", "FreeTrajScheduler", s, 1000,
                    f"{freetraj_per_seed[i]:.6f}",
                    f"{freetraj_src[i].parent.name}/{freetraj_src[i].name}",
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
                "233 P4", "R5a_two_moons_summary", f"{arm_name}_vs_baseline",
                f"{n_b}_vs_{n_f}", 1000, f"{delta:.6f}",
                f"d_s={d_s:.3f}, p={p:.3e}, bonf_sig={bonf_sig}, "
                f"ci=[{ci[0]:.5f}, {ci[1]:.5f}], verdict={verdict}",
            ])

    print(f"Wrote {OUT_CSV}")

    summary = {
        "wave": "233 P4",
        "cell": "R5a_two_moons_W2",
        "n_seeds_baseline": len(baseline_present),
        "n_seeds_per_arm": {k: len(v) for k, v in arms.items()},
        "all_seeds": ALL_SEEDS,
        "existing_seeds_pre": EXISTING_SEEDS,
        "new_seeds_added": NEW_SEEDS,
        "primary_headline": {
            "arm": "CosineAnnealScheduler",
            "welch": primary_welch,
        },
        "best_arm": {
            "name": best_arm_name,
            "mean_w2": arm_means.get(best_arm_name, float("nan")),
            "welch": best_arm_welch,
        },
        "per_arm_welch": {
            name: compute_welch(baseline_present, vals)
            for name, vals in arms.items()
            if vals
        },
        "direction_consistency": {
            name: direction_consistency(baseline_per_seed, f_list)
            for name, f_list in [
                ("CosineAnnealScheduler", cosine_per_seed),
                ("CodimensionSheetScheduler", codim_per_seed),
                ("EvidenceDrivenScheduler", evd_per_seed),
                ("FreeTrajScheduler", freetraj_per_seed),
            ]
        },
        "pre_expansion": {
            "n_seeds": 10,
            "primary_d_s": 1.011,
            "primary_verdict": "TIE",
            "primary_p_value_raw": 3.684e-02,
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())