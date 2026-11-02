#!/usr/bin/env python3
"""Separate fixed-seed holdout report; never pool it with the first study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from tools.cifar_study_metrics_20261103 import kernel_score
from tools.report_cifar_study_20261103 import exact_signflip_three, log_area
from tools.report_component_study_20261103 import holm, seed_summary


def analyze(root: Path, repository: Path) -> dict:
    if (root / "DEFERRED.json").exists():
        return {
            "status": "DEFERRED",
            "reason": json.loads((root / "DEFERRED.json").read_text()),
            "no_candidate_result_claimed": True,
        }
    ledger = json.loads((root / "RUN_LEDGER.json").read_text())
    if not ledger.get("complete"):
        raise ValueError("holdout incomplete; no partial-seed inference")
    protocol = json.loads((root / "PROTOCOL.json").read_text())
    seeds, costs, arms = protocol["seeds"], protocol["cost_grid"], protocol["arms"]
    constant = json.loads((repository / protocol["reference_statistics"]).read_text())[
        "reference_self_kernel"
    ]
    rows = {}
    errors = []
    for seed in seeds:
        for cost in costs:
            path = root / f"s{seed}_c{cost}"
            z = json.loads((path / "results.json").read_text())
            if (
                (z["seed"], z["cost"], z["n"]) != (seed, cost, 1000)
                or z["pilot_only"]
                or set(z["arms"]) != set(arms)
            ):
                raise ValueError("wrong identity")
            with np.load(path / "kid_witness.npz") as w:
                for arm in arms:
                    a = z["arms"][arm]
                    if (
                        a["n_processed"] != 1000
                        or a["n_skipped"]
                        or a["velocity_calls_per_sample"] != cost
                        or set(a["actual_calls_per_batch"]) != {cost}
                    ):
                        raise ValueError("wrong call/N accounting")
                    error = abs(
                        kernel_score(w[f"{arm}_xx"], w[f"{arm}_xy"], constant) - a["kid_unscaled"]
                    )
                    errors.append(error)
                    if error > 1e-12:
                        raise ValueError("kernel witness mismatch")
            rows[seed, cost] = z
    report = {
        "status": "COMPLETE",
        "n_canonical_cells": len(rows),
        "n_metric_witnesses_replayed": len(errors),
        "max_witness_abs_error": max(errors),
        "seeds": seeds,
        "costs": costs,
        "n_per_arm_seed_cost": 1000,
        "primary_family_size": 2,
        "curves": {},
        "primary_contrasts": [],
        "scope": "Separate prospective generation-seed holdout on same checkpoint/reference. Not independent dataset/model confirmation or full frontier. Phase-local multiplicity only. Training/reference uncertainty not covered.",
        "budget_total_conservatively_accounted_s": ledger["conservative_total_gpu_accounted_s"],
    }
    assert report["budget_total_conservatively_accounted_s"] <= 7200
    for arm in arms:
        area = [
            log_area([rows[s, c]["arms"][arm]["kid_unscaled"] for c in costs], costs) for s in seeds
        ]
        report["curves"][arm] = {
            "kid_area": seed_summary(area),
            "per_cost": {
                str(c): {
                    k: seed_summary([rows[s, c]["arms"][arm][k] for s in seeds])
                    for k in ["kid_unscaled", "fid_tfport", "clipped_fraction", "generation_wall_s"]
                }
                for c in costs
            },
        }
    for arm, base in protocol["primary_contrasts"]:
        d = [
            report["curves"][arm]["kid_area"]["values"][i]
            - report["curves"][base]["kid_area"]["values"][i]
            for i in range(3)
        ]
        report["primary_contrasts"].append(
            dict(
                arm=arm,
                baseline=base,
                **seed_summary(d),
                exploratory_exact_signflip_p=exact_signflip_three(d),
            )
        )
    for row, p in zip(
        report["primary_contrasts"],
        holm([x["p_two_sided"] for x in report["primary_contrasts"]]),
        strict=True,
    ):
        row["holm_p"] = p
        row["clears_preregistered_practical_improvement"] = (
            p < 0.05 and row["nominal_ci95"][1] < -0.001
        )
        row["detectable_practical_regression"] = p < 0.05 and row["nominal_ci95"][0] > 0.001
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--repository", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--figure", type=Path)
    args = p.parse_args()
    report = analyze(args.root, args.repository)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    if args.figure and report["status"] == "COMPLETE":
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))
        for ax, row in zip(axes, report["primary_contrasts"], strict=True):
            values = []
            halves = []
            for c in report["costs"]:
                x = report["curves"][row["arm"]]["per_cost"][str(c)]["kid_unscaled"]["values"]
                y = report["curves"][row["baseline"]]["per_cost"][str(c)]["kid_unscaled"]["values"]
                z = seed_summary([a - b for a, b in zip(x, y, strict=True)])
                values.append(z["mean"])
                halves.append((z["nominal_ci95"][1] - z["nominal_ci95"][0]) / 2)
            ax.errorbar(report["costs"], values, yerr=halves, fmt="o-", capsize=4)
            ax.axhline(0, color="black", lw=0.8)
            ax.set_xticks(report["costs"])
            ax.set_xlabel("Actual velocity evaluations per sample")
            ax.set_ylabel("Candidate minus control KID")
            ax.set_title({"baseline_euler": "Euler", "ve_restart": "Restart (RF interface)"}[row["baseline"]])
        fig.suptitle(
            "Separate seeds101/102/103; nominal seed-t 95% CI; two cost points only", fontsize=10
        )
        fig.tight_layout()
        args.figure.parent.mkdir(exist_ok=True, parents=True)
        fig.savefig(args.figure, dpi=200)
        plt.close(fig)
        with np.load(args.root / "s101_c199" / "preselected_images.npz") as samples:
            visual_arms = ["baseline_euler", "consistent_two_round", "ve_restart"]
            labels = ["Euler", "Two-round\nmatched time", "Restart\n(RF bridge)"]
            fig, axes = plt.subplots(3, 8, figsize=(12, 4.8))
            for i, arm in enumerate(visual_arms):
                for j in range(8):
                    ax = axes[i, j]
                    ax.imshow(np.clip((np.moveaxis(samples[arm][j], 0, -1) + 1) / 2, 0, 1))
                    ax.set_xticks([])
                    ax.set_yticks([])
                    if i == 0:
                        ax.set_title(str(j))
                    if j == 0:
                        ax.set_ylabel(labels[i])
            fig.suptitle("CIFAR-10, seed101, C199: first8 prespecified indices; same display transform", fontsize=11)
            fig.tight_layout()
            fig.savefig(args.figure.with_name("review-cifar-candidate-preselected-2026-11-03.png"), dpi=180)
            plt.close(fig)
    print(json.dumps(report.get("primary_contrasts", report), indent=2))


if __name__ == "__main__":
    main()
