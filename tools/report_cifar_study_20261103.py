#!/usr/bin/env python3
"""Locked seed-level inference and witness replay for the independent CIFAR study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats

from tools.cifar_study_metrics_20261103 import kernel_score
from tools.report_component_study_20261103 import holm, seed_summary


def exact_signflip_three(values):
    from itertools import product

    x = np.asarray(values, dtype=float)
    if x.shape != (3,) or not np.isfinite(x).all():
        raise ValueError("exactly three finite paired differences required")
    observed = abs(float(x.mean()))
    return (
        sum(
            abs(float((x * np.asarray(signs)).mean())) >= observed - 1e-15
            for signs in product([-1.0, 1.0], repeat=3)
        )
        / 8
    )


def log_area(values, costs):
    y = np.asarray(values, dtype=float)
    raw_costs = np.asarray(costs, dtype=float)
    if raw_costs.ndim != 1 or not np.isfinite(raw_costs).all() or np.any(raw_costs <= 0):
        raise ValueError("costs must be finite, positive and one-dimensional")
    x = np.log(raw_costs)
    if y.shape != x.shape or len(x) < 2 or np.any(np.diff(x) <= 0) or not np.isfinite(y).all():
        raise ValueError("need finite values on a strictly increasing cost grid")
    return float(np.trapezoid(y, x) / (x[-1] - x[0]))


def analyze(root: Path) -> dict:
    protocol = json.loads((root / "PROTOCOL.json").read_text())
    ledger = json.loads((root / "RUN_LEDGER.json").read_text())
    if not ledger.get("complete"):
        raise ValueError("canonical study incomplete: do not infer from a subset")
    seeds, costs, arms = protocol["seeds"], protocol["cost_grid"], protocol["arms"]
    ref = json.loads((root / "REFERENCE_STATISTICS.json").read_text())["reference_self_kernel"]
    rows = {}
    errors = []
    for seed in seeds:
        for cost in costs:
            path = root / f"s{seed}_c{cost}"
            z = json.loads((path / "results.json").read_text())
            if (
                z["seed"] != seed
                or z["cost"] != cost
                or z["n"] != 1000
                or z["pilot_only"]
                or set(z["arms"]) != set(arms)
            ):
                raise ValueError("wrong cell identity")
            with np.load(path / "kid_witness.npz") as witness:
                for arm in arms:
                    info = z["arms"][arm]
                    if (
                        info["n_processed"] != 1000
                        or info["n_skipped"] != 0
                        or info["velocity_calls_per_sample"] != cost
                        or set(info["actual_calls_per_batch"]) != {cost}
                    ):
                        raise ValueError("invalid N, skipped records or actual calls")
                    value = kernel_score(witness[f"{arm}_xx"], witness[f"{arm}_xy"], ref)
                    error = abs(value - info["kid_unscaled"])
                    errors.append(error)
                    if error > 1e-12:
                        raise ValueError("saved kernel witness disagrees with score")
            rows[seed, cost] = z
    out = {
        "n_canonical_cells": len(rows),
        "n_arms_per_cell": len(arms),
        "n_metric_witnesses_replayed": len(errors),
        "max_witness_abs_error": max(errors),
        "costs": costs,
        "seeds": seeds,
        "n_per_arm_seed_cost": 1000,
        "primary_metric": "unscaled polynomial KID in fixed TF-port2048 features",
        "primary_family_size": 4,
        "comparison_direction": "first arm minus second arm; negative favors first",
        "ci_scope": "nominal95% paired-seed t df2, not simultaneous; four-rung frontier bounds separately use Bonferroni",
        "curves": {},
        "primary_contrasts": [],
        "frontier_checks": [],
        "gpu_budget": {
            "limit_s": 7200,
            "conservative_used_s": ledger["conservatively_rounded_total_with_prior_and_profiles_s"],
        },
    }
    extra_path = root / "ADDITIONAL_GPU_ACCOUNTING.json"
    extra = (
        json.loads(extra_path.read_text())["conservative_additional_seconds"]
        if extra_path.exists()
        else 0
    )
    out["gpu_budget"]["conservative_used_s"] += extra
    assert out["gpu_budget"]["conservative_used_s"] <= 7200
    for arm in arms:
        area = [
            log_area([rows[s, c]["arms"][arm]["kid_unscaled"] for c in costs], costs) for s in seeds
        ]
        out["curves"][arm] = {"kid_area": seed_summary(area), "per_cost": {}}
        for cost in costs:
            out["curves"][arm]["per_cost"][str(cost)] = {
                metric: seed_summary([rows[s, cost]["arms"][arm][metric] for s in seeds])
                for metric in [
                    "kid_unscaled",
                    "fid_tfport",
                    "clipped_fraction",
                    "generation_wall_s",
                ]
            }
    for arm, base in protocol["primary_contrasts"]:
        effect = seed_summary(
            [
                out["curves"][arm]["kid_area"]["values"][i]
                - out["curves"][base]["kid_area"]["values"][i]
                for i in range(3)
            ]
        )
        out["primary_contrasts"].append(
            dict(
                arm=arm,
                baseline=base,
                **effect,
                exploratory_exact_signflip_p=exact_signflip_three(effect["values"]),
            )
        )
    for row, adjusted in zip(
        out["primary_contrasts"],
        holm([x["p_two_sided"] for x in out["primary_contrasts"]]),
        strict=True,
    ):
        row["holm_p"] = adjusted
        row["clears_preregistered_practical_improvement"] = (
            adjusted < 0.05 and row["nominal_ci95"][1] < -0.001
        )
        row["detectable_practical_regression"] = adjusted < 0.05 and row["nominal_ci95"][0] > 0.001
        row["label_scope"] = (
            "locked seed-level area comparison only; not universal or trained-seed inference"
        )
    for arm, base in protocol["primary_contrasts"]:
        rungs = []
        for cost in costs:
            difference = [
                rows[s, cost]["arms"][arm]["kid_unscaled"]
                - rows[s, cost]["arms"][base]["kid_unscaled"]
                for s in seeds
            ]
            z = seed_summary(difference)
            se = float(np.std(difference, ddof=1) / np.sqrt(3))
            q = float(stats.t.ppf(1 - 0.05 / (2 * 4), 2))
            rungs.append(
                dict(
                    cost=cost,
                    mean=z["mean"],
                    bonferroni_ci95=[z["mean"] - q * se, z["mean"] + q * se],
                )
            )
        high = [
            np.mean(
                [
                    rows[s, c]["arms"][arm]["kid_unscaled"]
                    - rows[s, c]["arms"][base]["kid_unscaled"]
                    for c in costs[-2:]
                ]
            )
            for s in seeds
        ]
        plateau = seed_summary(high)
        levels = out["curves"][base]["per_cost"]
        d_kid = (
            levels[str(costs[-1])]["kid_unscaled"]["mean"]
            - levels[str(costs[-2])]["kid_unscaled"]["mean"]
        )
        d_fid = (
            levels[str(costs[-1])]["fid_tfport"]["mean"]
            - levels[str(costs[-2])]["fid_tfport"]["mean"]
        )
        base_plateau = abs(d_kid) <= 0.001 and abs(d_fid) <= 1
        win = (
            base_plateau
            and all(x["bonferroni_ci95"][1] <= 0 for x in rungs)
            and plateau["nominal_ci95"][1] < -0.001
        )
        out["frontier_checks"].append(
            dict(
                arm=arm,
                baseline=base,
                rungs=rungs,
                high_cost_pair_effect=plateau,
                baseline_high_step_change=dict(kid=d_kid, fid=d_fid),
                baseline_operational_plateau=base_plateau,
                frontier_win=win,
            )
        )
    return out


def figures(root: Path, out: Path, report: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out.mkdir(exist_ok=True, parents=True)
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.8))
    labels = {
        "baseline_euler": "Euler",
        "full_euler": "Full",
        "simple_euler": "Simple t0=0",
        "ve_heun": "VE-Heun",
        "ve_restart": "Restart (RF bridge)",
    }
    for ax, z in zip(axes.flat, report["frontier_checks"], strict=True):
        ax.errorbar(
            [x["cost"] for x in z["rungs"]],
            [x["mean"] for x in z["rungs"]],
            yerr=[(x["bonferroni_ci95"][1] - x["bonferroni_ci95"][0]) / 2 for x in z["rungs"]],
            fmt="o-",
            capsize=3,
        )
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xscale("log")
        from matplotlib.ticker import NullFormatter, NullLocator
        ax.xaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xticks(report["costs"], [str(x) for x in report["costs"]])
        ax.set_xlabel("Actual velocity evaluations per sample")
        ax.set_ylabel("KID difference (unscaled)")
        ax.set_title(labels[z["arm"]] + " minus " + labels[z["baseline"]], fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "review-cifar-matched-2026-11-03.png", dpi=200)
    plt.close(fig)
    arms = list(report["curves"])
    fig, axes = plt.subplots(len(arms), 8, figsize=(10, 6.8))
    with np.load(root / "s42_c199/preselected_images.npz") as z:
        for j, arm in enumerate(arms):
            for i in range(8):
                ax = axes[j, i]
                ax.imshow(np.clip((z[arm][i].transpose(1, 2, 0) + 1) / 2, 0, 1))
                ax.set_xticks([])
                ax.set_yticks([])
                if i == 0:
                    ax.set_ylabel(labels[arm], fontsize=8)
                if j == 0:
                    ax.set_title(str(i), fontsize=8)
    fig.suptitle(
        "CIFAR-10, seed42, C199: first8 prespecified indices; identical display transform",
        fontsize=10,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out / "review-cifar-preselected-2026-11-03.png", dpi=200)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--figures", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = analyze(args.root)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    if args.figures:
        figures(args.root, args.figures, report)
    print(json.dumps(report["primary_contrasts"], indent=2))


if __name__ == "__main__":
    main()
