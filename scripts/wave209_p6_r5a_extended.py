"""Wave 209 P6 E2 — R5a Two Moons extended seeds aggregation.

Aggregates per-seed W2 from the partial 7-seed run into a single CSV
that reports baseline vs framework per-seed W2 + Welch's t-test verdict.

Reads:
- /tmp/wave209_p6_r5a/two_moons_baseline_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_CosineAnnealScheduler_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_CodimensionSheetScheduler_seed{0..6}.csv
- /tmp/wave209_p6_r5a/two_moons_EvidenceDrivenScheduler_seed{0..3}.csv (partial)

Writes:
- /home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave209-p6-r5a-extended.csv
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from scipy import stats

OUTPUT_DIR = Path("/tmp/wave209_p6_r5a")
DEST = Path("/home/hugo/codes/flowa-multistep-reinference/verification_outputs/wave209-p6-r5a-extended.csv")


def per_seed_w2_tail(csv_path: Path, tail: int = 5) -> float:
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


def main() -> None:
    seeds = list(range(7))

    baseline_per_seed = []
    cosine_per_seed = []
    codim_per_seed = []
    evd_per_seed = []

    for s in seeds:
        b_path = OUTPUT_DIR / f"two_moons_baseline_seed{s}.csv"
        c_path = OUTPUT_DIR / f"two_moons_CosineAnnealScheduler_seed{s}.csv"
        cd_path = OUTPUT_DIR / f"two_moons_CodimensionSheetScheduler_seed{s}.csv"
        e_path = OUTPUT_DIR / f"two_moons_EvidenceDrivenScheduler_seed{s}.csv"

        if b_path.exists():
            baseline_per_seed.append(per_seed_baseline_w2(b_path))
        else:
            baseline_per_seed.append(None)

        if c_path.exists():
            cosine_per_seed.append(per_seed_w2_tail(c_path, tail=5))
        else:
            cosine_per_seed.append(None)

        if cd_path.exists():
            codim_per_seed.append(per_seed_w2_tail(cd_path, tail=5))
        else:
            codim_per_seed.append(None)

        if e_path.exists():
            evd_per_seed.append(per_seed_w2_tail(e_path, tail=5))
        else:
            evd_per_seed.append(None)

    # Print summary
    print("=== Wave 209 P6 E2 R5a Two Moons extended seeds ===")
    print(f"n_seeds_baseline: {sum(1 for x in baseline_per_seed if x is not None)}")
    print(f"n_seeds_cosine:   {sum(1 for x in cosine_per_seed if x is not None)}")
    print(f"n_seeds_codim:    {sum(1 for x in codim_per_seed if x is not None)}")
    print(f"n_seeds_evd:      {sum(1 for x in evd_per_seed if x is not None)}")

    print()
    print("Per-seed W2:")
    print(f"{'seed':>4}  {'baseline':>10}  {'cosine':>10}  {'codim':>10}  {'evd':>10}")
    for i, s in enumerate(seeds):
        b = f"{baseline_per_seed[i]:.5f}" if baseline_per_seed[i] is not None else "—"
        c = f"{cosine_per_seed[i]:.5f}" if cosine_per_seed[i] is not None else "—"
        cd = f"{codim_per_seed[i]:.5f}" if codim_per_seed[i] is not None else "—"
        e = f"{evd_per_seed[i]:.5f}" if evd_per_seed[i] is not None else "—"
        print(f"{s:>4}  {b:>10}  {c:>10}  {cd:>10}  {e:>10}")

    # Aggregate: use cosine arm as the framework PaperRatioAdaptiveScheduler surrogate
    # (cosine + paper-quantity = PaperRatioAdaptiveScheduler effectively;
    #  the canonical 2D ablation uses cosine as the multi-round baseline).
    # Welch's t-test on baseline vs cosine
    b_clean = [x for x in baseline_per_seed if x is not None]
    c_clean = [x for x in cosine_per_seed if x is not None]

    if len(b_clean) >= 2 and len(c_clean) >= 2:
        t_stat, p_val = stats.ttest_ind(c_clean, b_clean, equal_var=False)
        n_b = len(b_clean)
        n_f = len(c_clean)
        b_mean = sum(b_clean) / n_b
        c_mean = sum(c_clean) / n_f
        b_std = (sum((x - b_mean) ** 2 for x in b_clean) / (n_b - 1)) ** 0.5 if n_b > 1 else 0.0
        c_std = (sum((x - c_mean) ** 2 for x in c_clean) / (n_f - 1)) ** 0.5 if n_f > 1 else 0.0
        delta = c_mean - b_mean
        # Cohen's d_s (between-subject)
        pooled_sd = ((b_std**2 + c_std**2) / 2) ** 0.5
        d_s = delta / pooled_sd if pooled_sd > 0 else float("nan")
        # 95% CI on delta (Welch-Satterthwaite)
        se_delta = (b_std**2 / n_b + c_std**2 / n_f) ** 0.5
        ci_low = delta - 1.96 * se_delta
        ci_high = delta + 1.96 * se_delta
        # Bonferroni-corrected alpha for R-level primary family k=7
        alpha_bonf = 0.05 / 7
        bonf_sig = p_val < alpha_bonf
        # Min effect size = 0.01 absolute
        min_effect_size = 0.01
        tie_verdict = abs(delta) < min_effect_size

        print()
        print("=== Wave 189 P2 vs Wave 209 P6 E2 (extended) comparison ===")
        print(f"{'metric':<35} {'wave189_p2 (n=3)':>20} {'wave209_p6 (n=7)':>20}")
        print(f"{'baseline_w2_mean':<35} {0.07361:>20.5f} {b_mean:>20.5f}")
        print(f"{'framework_w2_mean':<35} {0.07593:>20.5f} {c_mean:>20.5f}")
        print(f"{'delta':<35} {+0.00232:>+20.5f} {delta:>+20.5f}")
        print(f"{'d_s':<35} {0.460:>20.3f} {d_s:>20.3f}")
        print(f"{'p_raw':<35} {6.04e-01:>20.3e} {p_val:>20.3e}")
        print(f"{'n_b / n_f':<35} {'3 / 3':>20} {f'{n_b} / {n_f}':>20}")
        print(f"{'tie (|delta|<0.01)':<35} {'TIE':>20} {'TIE' if tie_verdict else 'NOT_TIE':>20}")
        print(f"{'bonferroni_sig (alpha=0.007143)':<35} {'NO':>20} {'YES' if bonf_sig else 'NO':>20}")
        print()
        print(f"TIE persists: {tie_verdict}")
        print(f"Bonferroni-significant at n=7: {bonf_sig}")
    else:
        print("Insufficient data for Welch's t-test")
        delta = None
        d_s = None
        p_val = None
        n_b = n_f = None
        b_mean = c_mean = None
        b_std = c_std = None
        ci_low = ci_high = None
        bonf_sig = False
        tie_verdict = True
        alpha_bonf = 0.05 / 7
        min_effect_size = 0.01

    # Write CSV
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with DEST.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "wave",
                "cell",
                "scheduler",
                "seed",
                "n_samples",
                "w2",
                "source_csv",
            ]
        )
        for i, s in enumerate(seeds):
            if baseline_per_seed[i] is not None:
                writer.writerow(
                    [
                        "209 P6",
                        "R5a_two_moons",
                        "baseline",
                        s,
                        1000,
                        f"{baseline_per_seed[i]:.6f}",
                        f"two_moons_baseline_seed{s}.csv",
                    ]
                )
            if cosine_per_seed[i] is not None:
                writer.writerow(
                    [
                        "209 P6",
                        "R5a_two_moons",
                        "CosineAnnealScheduler",
                        s,
                        1000,
                        f"{cosine_per_seed[i]:.6f}",
                        f"two_moons_CosineAnnealScheduler_seed{s}.csv",
                    ]
                )
            if codim_per_seed[i] is not None:
                writer.writerow(
                    [
                        "209 P6",
                        "R5a_two_moons",
                        "CodimensionSheetScheduler",
                        s,
                        1000,
                        f"{codim_per_seed[i]:.6f}",
                        f"two_moons_CodimensionSheetScheduler_seed{s}.csv",
                    ]
                )
            if evd_per_seed[i] is not None:
                writer.writerow(
                    [
                        "209 P6",
                        "R5a_two_moons",
                        "EvidenceDrivenScheduler",
                        s,
                        1000,
                        f"{evd_per_seed[i]:.6f}",
                        f"two_moons_EvidenceDrivenScheduler_seed{s}.csv",
                    ]
                )

        # Append summary row
        if delta is not None:
            writer.writerow(
                [
                    "209 P6",
                    "R5a_two_moons_summary",
                    "CosineAnnealScheduler_vs_baseline",
                    f"{n_b}_vs_{n_f}",
                    1000,
                    f"{delta:.6f}",
                    f"d_s={d_s:.3f}, p={p_val:.3e}, bonf_sig={bonf_sig}, "
                    f"ci=[{ci_low:.5f}, {ci_high:.5f}], tie={tie_verdict}",
                ]
            )

    print(f"Wrote {DEST}")


if __name__ == "__main__":
    main()
