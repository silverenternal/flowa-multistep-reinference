import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

r = Path("/home/hugo/codes/flowa-multistep-reinference")
data = json.loads(
    (r / "verification_outputs/path-identifiability-20261103/RESULTS.json").read_text()
)
selected = [
    row for row in data["rows"] if row["m"] == 0.5 and row["rho"] == 0 and row["rotation"] == 0.7
]
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.3), layout="constrained")
times = np.linspace(0, 1, 201)
for row, marker, style in zip(selected, ["o", "s", "^"], ["-", "--", "-."], strict=True):
    radii = np.exp(row["amplitude"] * np.sin(np.pi * times))
    axes[0].plot(
        times,
        radii,
        style,
        marker=marker,
        markevery=25,
        label=f"Output std={row['sigma']:g}",
        linewidth=1.5,
        markersize=3,
    )
axes[0].plot(
    times, np.sqrt(times**2 + (1 - times) ** 2), ":", color="black", label="Independent chord std"
)
axes[0].axvline(0.5, color="0.5", linewidth=0.7)
axes[0].set(
    xlabel="Flow time",
    ylabel="True intermediate standard deviation",
    title="Identical endpoint map in all cases",
)
axes[0].legend(fontsize=7)
axes[1].bar(
    ["Shrink", "Preserve", "Expand"],
    [row["output_variance"] for row in selected],
    color=[".75", ".55", ".35"],
)
axes[1].axhline(1, color="black", linestyle="--", linewidth=1, label="Target variance")
axes[1].set(ylabel="Output variance per coordinate", title="Same endpoint refresh at m=0.5")
axes[1].legend(fontsize=7)
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.15)
p = r / "docs/figures/review-path-identifiability-20261103.png"
p.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(p, dpi=240)
plt.close(fig)
