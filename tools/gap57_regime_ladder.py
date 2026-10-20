"""GAP-57: the GAP-35 regime ladder, re-measured under equal total NFE.

GAP-35 (``docs/audit/gap35-cross-domain.md`` §3) found the restart gain is
monotone in the model's optimisation budget: the framework wins by 25-28 % on
under-trained checkpoints and regresses by 3-10 % once the velocity field has
converged. Every framework arm in that table, however, ran at the *legacy*
per-round cap (cosine 25 / codim 48 / evidence 25 total NFE) against a baseline
at 50 NFE, so the magnitude of each win is confounded with compute.

This tool reads the equal-total-NFE re-measurement and prints:

1. a per-checkpoint, per-draw table (baseline FID, each arm's FID, delta %);
2. the three-draw mean / sd per checkpoint;
3. the same quantities for the GAP-35 legacy runs, computed from GAP-35's own
   aggregate with the **same** estimator (``fid_headline`` ratio), so the
   compute confound appears as a column rather than an argument;
4. the least-squares slope of delta % on the baseline FID, i.e. the test of
   "the win tracks the model's residual error".

Estimator note. GAP-35 reports ``delta_pct_mean`` = -25.39 % for ``w16e1_5k``.
That is a *chunk-mean* delta against a 20-image reference, which is
arm-dependently biased (GAP-56 §4.3) and is **not** comparable with the
headline ratio. The headline ratio of the same run is -22.52 %. This tool uses
headline ratios on both sides and says so.

Everything is read from artifacts; nothing is recomputed from samples.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ARMS = ("cosine", "codimension_sheet", "evidence_driven")

DEFAULT_GAP35 = Path("verification_outputs/gap35-mnist-regime/aggregate.json")


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _sd(xs: list[float]) -> float:
    if len(xs) < 2:
        return math.nan
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Return (slope, intercept, r_squared) for y = a + b x."""
    mx, my = _mean(xs), _mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    slope = sxy / sxx if sxx > 0 else math.nan
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else math.nan
    return slope, intercept, r2


def _load(root: Path, tag: str, seed: int) -> dict | None:
    p = root / f"{tag}_s{seed}" / "sweep_summary.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _load_gap35(path: Path) -> dict[str, dict[str, float]]:
    """Per-ckpt legacy headline numbers from GAP-35's aggregate.

    Returns ``{tag: {"baseline": fid, arm: delta_pct, ...}}``. GAP-35's three
    "seeds" are one prior draw with three chunk partitions (its
    ``baseline_fid`` and ``fid_headline`` are identical across seeds), so the
    first entry is the whole draw; no averaging over seeds is meaningful.
    """
    if not path.exists():
        return {}
    agg = json.loads(path.read_text())
    out: dict[str, dict[str, float]] = {}
    for tag, v in agg.get("regime_table", {}).items():
        per_seed = v.get("per_seed") or []
        if not per_seed:
            continue
        row = per_seed[0]
        base = float(row["baseline_fid"])
        rec: dict[str, float] = {"baseline": base}
        for arm in ARMS:
            a = (row.get("all_arms") or {}).get(arm)
            if a is not None:
                rec[arm] = (float(a["fid_headline"]) / base - 1.0) * 100.0
        out[tag] = rec
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path,
                    default=Path("verification_outputs/gap57-equal-nfe-ladder"))
    ap.add_argument("--gap35", type=Path, default=DEFAULT_GAP35)
    ap.add_argument("--seeds", default="42,43,44")
    args = ap.parse_args(argv)

    seeds = [int(s) for s in str(args.seeds).split(",") if s.strip()]
    tags = ["w16e1_5k", "w16e1_10k", "w16e1_60k", "production"]

    print("## Per-draw (equal total NFE = 50 on both sides)\n")
    print("| ckpt | seed | baseline FID | cosine | codim | evidence | "
          "Δ% cos | Δ% codim | Δ% evid |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    per_point: list[tuple[str, int, float, float]] = []  # (tag, seed, base, mean delta%)
    for tag in tags:
        for seed in seeds:
            d = _load(args.root, tag, seed)
            if d is None:
                print(f"| {tag} | {seed} | — | — | — | — | — | — | — |")
                continue
            base = float(d["baseline_fid"])
            fids = {a: float(d["framework_arms"][a]["fid_headline"]) for a in ARMS}
            dpct = {a: (fids[a] / base - 1.0) * 100.0 for a in ARMS}
            per_point.append((tag, seed, base, _mean(list(dpct.values()))))
            print(f"| {tag} | {seed} | {base:.4f} | "
                  f"{fids['cosine']:.4f} | {fids['codimension_sheet']:.4f} | "
                  f"{fids['evidence_driven']:.4f} | "
                  f"{dpct['cosine']:+.2f} | {dpct['codimension_sheet']:+.2f} | "
                  f"{dpct['evidence_driven']:+.2f} |")

    gap35 = _load_gap35(args.gap35)

    print("\n## Three-draw summary, with the GAP-35 legacy protocol beside it\n")
    print("Both columns are headline-ratio deltas. Legacy = framework arms at the "
          "per-round cap (25/48/25 NFE) vs a 50-NFE baseline; equal-NFE = 50 vs 50.\n")
    print("| ckpt | baseline FID (equal-NFE, mean ± sd) | Δ% by arm (equal-NFE) | "
          "best arm (equal-NFE) | Δ% by arm (GAP-35 legacy) | compute cost of the win |")
    print("|---|---:|---|---:|---|---:|")
    for tag in tags:
        pts = [p for p in per_point if p[0] == tag]
        if not pts:
            print(f"| {tag} | — | — | — | — | — |")
            continue
        base_mean = _mean([p[2] for p in pts])
        base_sd = _sd([p[2] for p in pts])
        arm_means: dict[str, float] = {}
        for arm in ARMS:
            vals = []
            for seed in seeds:
                d = _load(args.root, tag, seed)
                if d is None:
                    continue
                b = float(d["baseline_fid"])
                vals.append((float(d["framework_arms"][arm]["fid_headline"]) / b - 1.0) * 100.0)
            arm_means[arm] = _mean(vals) if vals else math.nan
        best_arm = min(arm_means, key=lambda a: arm_means[a])
        eq_txt = " / ".join(f"{a} {arm_means[a]:+.2f}" for a in ARMS)
        g = gap35.get(tag, {})
        if g:
            leg_txt = " / ".join(
                f"{a} {g[a]:+.2f}" for a in ARMS if a in g
            )
            leg_best = min((g[a] for a in ARMS if a in g), default=math.nan)
            shift = arm_means[best_arm] - leg_best
            shift_txt = f"{shift:+.2f} pp"
        else:
            leg_txt, shift_txt = "—", "—"
        print(f"| {tag} | {base_mean:.4f} ± {base_sd:.4f} | {eq_txt} | "
              f"{best_arm} {arm_means[best_arm]:+.2f} | {leg_txt} | {shift_txt} |")

    print("\n## Record-level paired bootstrap (headline FID, B=2000)\n")
    print("The chunk-level test the driver emits uses a 20-image reference and is "
          "arm-dependently biased (GAP-56 §4.3); this is the unbiased estimator with "
          "a sampling distribution. `fav` is the share of bootstrap replicates in "
          "which the framework beats the baseline.\n")
    print("| run | arm | Δ | Δ% | 95% CI | p (Bonf) | fav | verdict |")
    print("|---|---|---:|---:|---|---:|---:|---|")
    wins = ties = losses = 0
    for tag in tags:
        for seed in seeds:
            p = args.root / f"{tag}_s{seed}" / "paired_bootstrap.json"
            if not p.exists():
                continue
            boot = json.loads(p.read_text())
            for arm in ARMS:
                v = boot["arms"][arm]
                ci = f"[{v['delta_ci95'][0]:+.4f}, {v['delta_ci95'][1]:+.4f}]"
                if v["delta_ci95"][1] < 0:
                    verdict = "**framework wins**"
                    wins += 1
                elif v["delta_ci95"][0] > 0:
                    verdict = "baseline wins"
                    losses += 1
                else:
                    verdict = "tie"
                    ties += 1
                print(f"| {tag}_s{seed} | {arm} | {v['delta']:+.4f} | "
                      f"{v['delta_pct']:+.2f} | {ci} | {v['p_bonferroni']:.2e} | "
                      f"{v['frac_boot_favouring_framework']*100:.1f}% | {verdict} |")
    total = wins + ties + losses
    print(f"\nSign census over the {total} record-level cells: "
          f"framework wins **{wins}**, baseline wins **{losses}**, ties **{ties}**.")

    print("\n## Does the gain still track the model's residual error?\n")
    xs = [p[2] for p in per_point]
    ys = [p[3] for p in per_point]
    if len(xs) >= 3:
        slope, intercept, r2 = _ols(xs, ys)
        print(f"Least squares of Δ% on the baseline FID, {len(xs)} points "
              f"(4 checkpoints × {len(seeds)} draws), mean over the three arms:")
        print(f"- slope = **{slope:+.4f}** % per FID unit")
        print(f"- intercept = {intercept:+.4f} %")
        print(f"- R² = {r2:.4f}")
        if not math.isnan(slope) and slope != 0:
            zero = -intercept / slope
            print(f"- zero crossing at baseline FID ≈ **{zero:.2f}**")
            print("- Reading: a negative slope means the restart gain grows as the "
                  "model gets worse. A zero crossing inside the observed FID range "
                  "means the sign flip is a property of the model, not of the "
                  "compute budget.")
    else:
        print("Not enough points for a regression.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
