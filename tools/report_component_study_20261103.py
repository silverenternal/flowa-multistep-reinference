#!/usr/bin/env python3
"""Recompute the locked eight-contrast component family from saved seed results."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import stats


def holm(pvalues: list[float]) -> list[float]:
    p = np.asarray(pvalues, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("invalid p values")
    order = np.argsort(p, kind="stable")
    result = np.empty(len(p))
    result[order] = np.minimum(1, np.maximum.accumulate(p[order] * np.arange(len(p), 0, -1)))
    return result.tolist()


def seed_summary(values: list[float]) -> dict:
    x = np.asarray(values, dtype=float)
    if x.shape != (3,) or not np.isfinite(x).all():
        raise ValueError("exactly three finite canonical seed values required")
    mean = float(x.mean())
    se = float(x.std(ddof=1) / np.sqrt(3))
    half = float(stats.t.ppf(0.975, 2) * se)
    p = float(2 * stats.t.sf(abs(mean / se), 2)) if se else (0.0 if mean else 1.0)
    return dict(
        values=x.tolist(), mean=mean, nominal_ci95=[mean - half, mean + half], p_two_sided=p, df=2
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    protocol = json.loads((root / "PROTOCOL.json").read_text())
    assert protocol["seeds"] == [42, 43, 44]
    arms = protocol["arms"]
    controls = arms[2:]
    report = {
        "protocol_sha256": hashlib.sha256((root / "PROTOCOL.json").read_bytes()).hexdigest(),
        "comparison_direction": "control minus full; positive favors full",
        "primary_family_size": 8,
        "ci_scope": "nominal seed-t intervals, not simultaneous; df=2, no training-seed replication",
        "checkpoints": {},
        "primary_contrasts": [],
        "covariance_checks": [],
    }
    for ckpt in protocol["checkpoints"]:
        rows = [
            json.loads((root / f"{ckpt}_s{seed}" / "results.json").read_text())
            for seed in protocol["seeds"]
        ]
        for seed, row in zip(protocol["seeds"], rows, strict=False):
            assert row["checkpoint"] == ckpt and row["seed"] == seed and not row["pilot_only"]
            assert set(row["arms"]) == set(arms) and max(row["reproduction_guard"].values()) <= 1e-4
            for arm in row["arms"].values():
                assert (
                    arm["n_processed"] == 1000
                    and arm["n_skipped"] == 0
                    and arm["actual_velocity_calls_per_sample"] == 200
                )
        block = {
            arm: {
                metric: seed_summary([r["arms"][arm][metric] for r in rows])
                for metric in ["projection_fid", "projection_kid"]
            }
            for arm in arms
        }
        block["full_minus_baseline_descriptive"] = {
            metric: seed_summary(
                [r["arms"]["full"][metric] - r["arms"]["baseline"][metric] for r in rows]
            )
            for metric in ["projection_fid", "projection_kid"]
        }
        report["checkpoints"][ckpt] = block
        for control in controls:
            effect = seed_summary(
                [
                    r["arms"][control]["projection_fid"] - r["arms"]["full"]["projection_fid"]
                    for r in rows
                ]
            )
            report["primary_contrasts"].append(dict(checkpoint=ckpt, control=control, **effect))
        for seed in protocol["seeds"]:
            with np.load(root / f"{ckpt}_s{seed}" / "features_and_preselected_images.npz") as z:
                a, b = z["full"], z["no_mean"]
                shift = a - b
                report["covariance_checks"].append(
                    dict(
                        checkpoint=ckpt,
                        seed=seed,
                        max_nonconstant_shift=float(np.abs(shift - shift.mean(0)).max()),
                        max_covariance_difference=float(
                            np.abs(np.cov(a, rowvar=False) - np.cov(b, rowvar=False)).max()
                        ),
                    )
                )
    for row, adjusted in zip(
        report["primary_contrasts"], holm([x["p_two_sided"] for x in report["primary_contrasts"]]), strict=False
    ):
        row["holm_p"] = adjusted
        row["passes_abs_mean_floor_1"] = abs(row["mean"]) >= 1
    (root / "REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    args.figures.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    labels = {
        "no_mean": "No centroid",
        "uniform_budget": "Uniform budget",
        "no_mix_fixed_time": "No mixing (fixed time)",
        "zero_restart_time": "Restart at t=0",
    }
    for j, ckpt in enumerate(protocol["checkpoints"]):
        rows = [x for x in report["primary_contrasts"] if x["checkpoint"] == ckpt]
        y = np.arange(4) + (j - 0.5) * 0.18
        ax.errorbar(
            [x["mean"] for x in rows],
            y,
            xerr=[(x["nominal_ci95"][1] - x["nominal_ci95"][0]) / 2 for x in rows],
            fmt="o",
            capsize=3,
            label=ckpt,
        )
    ax.axvline(0, color="black", lw=0.8)
    ax.axvspan(-1, 1, color="gray", alpha=0.1)
    ax.set_yticks(np.arange(4), [labels[a] for a in controls])
    ax.invert_yaxis()
    ax.set_xlabel("Projection-FID: control minus full (nominal seed-t 95% CI)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.figures / "review-components-2026-11-03.png", dpi=200)
    plt.close(fig)
    fig, axes = plt.subplots(12, 8, figsize=(8, 12))
    for j, ckpt in enumerate(protocol["checkpoints"]):
        with np.load(root / f"{ckpt}_s42" / "features_and_preselected_images.npz") as z:
            for k, arm in enumerate(arms):
                for i in range(8):
                    ax = axes[j * 6 + k, i]
                    ax.imshow(z[f"images_{arm}"][i].reshape(28, 28), cmap="gray", vmin=0, vmax=1)
                    ax.set_xticks([])
                    ax.set_yticks([])
                    if i == 0:
                        ax.set_ylabel(ckpt + "\n" + arm, fontsize=7)
    fig.suptitle("Seed 42, first 8 preselected indices; fixed display range [0,1]", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(args.figures / "review-preselected-samples-2026-11-03.png", dpi=160)
    plt.close(fig)
    print(json.dumps(report["primary_contrasts"], indent=2))


if __name__ == "__main__":
    main()
