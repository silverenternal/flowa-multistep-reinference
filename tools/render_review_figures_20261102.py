"""Render the reviewed six-checkpoint figures from existing normalized inputs."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    "w16e1_5k": "gap84-cap-frontier/frontier_input_w16e1_5k.json",
    "w16e1_10k": "gap84-cap-frontier/frontier_input_w16e1_10k.json",
    "w16e1_60k": "gap84-cap-frontier/frontier_input_w16e1_60k.json",
    "epochs2": "gap90-optsteps-dose-cap/frontier_input_epochs2.json",
    "production": "gap84-cap-frontier/frontier_input_production.json",
    "w8e3": "gap90-optsteps-dose-cap/frontier_input_w8e3.json",
}


def main() -> None:
    data = {
        key: json.loads((ROOT / "verification_outputs" / path).read_text())
        for key, path in SPECS.items()
    }
    dest = ROOT / "docs/figures"
    dest.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(10, 6), constrained_layout=True)
    for ax, (key, spec) in zip(axes.flat, data.items(), strict=True):
        grid = spec["grid"]
        for arm, label, color, style in [
            ("baseline", "Single pass", "#666666", "o--"),
            ("framework", "FlowA instance", "#2166ac", "s-"),
        ]:
            means = np.array([spec[arm][str(s)]["value"] for s in grid])
            sd = np.array(
                [np.std(spec[arm][str(s)]["units"], ddof=1) for s in grid]
            )
            calls = 4 * np.array(grid)
            ax.plot(calls, means, style, color=color, label=label, markersize=3)
            ax.fill_between(calls, means - sd, means + sd, color=color, alpha=0.15)
        ax.set_xscale("log")
        ax.set_title(key)
        ax.set_xticks([16, 40, 100, 400, 800])
        ax.set_xticklabels(["16", "40", "100", "400", "800"], fontsize=8)
        ax.minorticks_off()
        ax.set_xlabel("Velocity evaluations (C = 4S)", fontsize=8)
        ax.set_ylabel("Projection-FID", fontsize=9)
        ax.grid(alpha=0.15)
        ax.legend(fontsize=7)
    fig.savefig(dest / "review-six-frontiers-2026-11-02.png", dpi=200)
    plt.close(fig)

    def delta(key: str) -> float:
        spec = data[key]
        return float(
            np.mean(
                [
                    spec["framework"][str(s)]["value"]
                    - spec["baseline"][str(s)]["value"]
                    for s in (100, 200)
                ]
            )
        )

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), constrained_layout=True)
    groups = [
        ([5000, 10000, 60000], ["w16e1_5k", "w16e1_10k", "w16e1_60k"],
         "Training images (width 16, epoch 1)"),
        ([1, 2, 3], ["w16e1_60k", "epochs2", "production"],
         "Epochs (width 16, 60k images)"),
        ([8, 16], ["w8e3", "production"],
         "Width (epoch 3, 60k images)"),
    ]
    for ax, (x, keys, label) in zip(axes, groups, strict=True):
        ax.axhspan(-1, 1, color="#dddddd", alpha=0.5, label="Absolute floor band")
        ax.axhline(0, color="black", linewidth=0.7)
        ax.plot(x, [delta(k) for k in keys], "o-", color="#2166ac")
        ax.set_xlabel(label, fontsize=8)
        ax.set_ylabel("Plateau delta (FlowA - baseline)")
        ax.set_xticks(x)
        if len(x) == 3 and x[-1] == 60000:
            ax.set_xticklabels(["5k", "10k", "60k"], fontsize=8)
        ax.set_ylim(-3.6, 1.3)
        ax.grid(alpha=0.15)
    fig.savefig(dest / "review-controlled-axes-2026-11-02.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
