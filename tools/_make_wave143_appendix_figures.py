"""Wave 143 Phase 3 appendix figures (A1-A8).

Renders 8 paper appendix figures with matplotlib.
Data sourced from existing verification_outputs/, docs/headline-evidence/,
and the 2D FM model checkpoints in data/.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import json
import os
import sys

sys.path.insert(0, '.')

# Output directory
OUT = "docs/figures"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# Figure A1: Kanzi N=20 RMSD trajectory (line plot)
# ---------------------------------------------------------------------------
print("Building Figure A1...")
ks = json.load(open("verification_outputs/kanzi_inv_proj_n20_20260913_corrected/initial_summary.json"))
seqs = sorted([k for k in ks["per_seq_rmsd_A"].keys()], key=lambda x: int(x.split("_")[1]))
rmsds = [ks["per_seq_rmsd_A"][k] for k in seqs]
mean_rmsd = ks["reconstruction_kabsch_rmsd_A"]["mean_rmsd_A"]
min_rmsd = ks["reconstruction_kabsch_rmsd_A"]["min_rmsd_A"]
max_rmsd = ks["reconstruction_kabsch_rmsd_A"]["max_rmsd_A"]

fig, ax = plt.subplots(figsize=(7, 4))
xs = np.arange(len(seqs))
ax.plot(xs, rmsds, marker="o", color="#357", markersize=5, linewidth=1.2, label="framework_inv_proj RMSD")
ax.axhline(mean_rmsd, color="#888", linestyle="--", linewidth=1, label=f"mean = {mean_rmsd:.3f} Å")
ax.fill_between(xs, [min_rmsd] * len(xs), [max_rmsd] * len(xs), color="#888", alpha=0.15, label="min-max band")
ax.set_xlabel("Record index (0-19)")
ax.set_ylabel("Per-record Kabsch RMSD (Å)")
ax.set_title("Figure A1: Kanzi framework_inv_proj N=20 per-record RMSD trajectory")
ax.legend(loc="upper right", fontsize=8)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f"{OUT}/figA1_kanzi_n20_trajectory.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A1 written")


# ---------------------------------------------------------------------------
# Load 2D FM samples generated earlier
# ---------------------------------------------------------------------------
tm = np.load("/tmp/figdata/two_moons_samples.npz")
eg = np.load("/tmp/figdata/eight_gaussians_samples.npz")

# Generate ground truth
from adaptive_reflow.data.target_distributions import sample_two_moons, sample_eight_gaussians
gt_rng = np.random.default_rng(42)
gt_tm = sample_two_moons(512, gt_rng)
gt_eg = sample_eight_gaussians(512, gt_rng)


# ---------------------------------------------------------------------------
# Figure A2: 2D Two Moons baseline vs framework samples
# ---------------------------------------------------------------------------
print("Building Figure A2...")
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
titles = ["(a) Ground truth target", "(b) Baseline (Euler, NFE=2)", "(c) Framework (RK4, NFE=64)"]
data_sets = [gt_tm, tm["baseline"], tm["framework"]]
colors = ["#222", "#888", "#357"]

for ax, d, t, c in zip(axes, data_sets, titles, colors):
    ax.scatter(d[:, 0], d[:, 1], s=8, alpha=0.55, color=c, edgecolors="none")
    ax.set_xlim(-1.6, 2.6)
    ax.set_ylim(-1.6, 1.6)
    ax.set_aspect("equal")
    ax.set_title(t, fontsize=10)
    ax.grid(True, alpha=0.2)
    ax.set_xlabel("x₁")
    ax.set_ylabel("x₂")

fig.suptitle("Figure A2: 2D Two Moons — framework samples vs baseline (W₂ = 0.4663 vs 0.5029, −7.28%)", fontsize=11, y=1.02)
plt.tight_layout()
plt.savefig(f"{OUT}/figA2_two_moons_samples.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A2 written")


# ---------------------------------------------------------------------------
# Figure A3: 2D Eight Gaussians baseline vs framework samples
# ---------------------------------------------------------------------------
print("Building Figure A3...")
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
titles = ["(a) Ground truth target", "(b) Baseline (Euler, NFE=2)", "(c) Framework (RK4, NFE=64)"]
data_sets = [gt_eg, eg["baseline"], eg["framework"]]
colors = ["#222", "#888", "#357"]

for ax, d, t, c in zip(axes, data_sets, titles, colors):
    ax.scatter(d[:, 0], d[:, 1], s=8, alpha=0.55, color=c, edgecolors="none")
    ax.set_xlim(-2.8, 2.8)
    ax.set_ylim(-2.8, 2.8)
    ax.set_aspect("equal")
    ax.set_title(t, fontsize=10)
    ax.grid(True, alpha=0.2)
    ax.set_xlabel("x₁")
    ax.set_ylabel("x₂")

fig.suptitle("Figure A3: 2D Eight Gaussians — framework samples vs baseline (W₂ = 0.5919 vs 0.6606, −10.40%)", fontsize=11, y=1.02)
plt.tight_layout()
plt.savefig(f"{OUT}/figA3_eight_gaussians_samples.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A3 written")


# ---------------------------------------------------------------------------
# Figure A4: CIFAR-10 v2 vs v4 FID comparison (bar chart)
# ---------------------------------------------------------------------------
print("Building Figure A4...")
fig, ax = plt.subplots(figsize=(7, 4.5))

labels = ["v1 baseline\n(initial)", "v2 framework\n2-NFE→avg 5", "v3 matched\nNFE=2", "v4 framework\n50-NFE→avg 25"]
values = [218.87, 122.18, 222.16, 103.41]  # use v4 mid value for v4
colors_bar = ["#888", "#357", "#bbb", "#bbb"]
bars = ax.bar(labels, values, color=colors_bar, edgecolor="#222", linewidth=0.8)

# Annotate values + verdict
annotations = ["—", "−44.17%\nframework_better", "+1.5%\nparity", "+24 to +31%\nregression"]
for bar, ann in zip(bars, annotations):
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, h + 5, ann, ha="center", va="bottom", fontsize=8, fontweight="bold")

ax.set_ylabel("FID (CIFAR-10, lower is better)")
ax.set_title("Figure A4: CIFAR-10 Rectified Flow — framework FID vs baseline")
ax.axhline(218.87, color="#888", linestyle="--", linewidth=0.8, alpha=0.7, label="v1 baseline (218.87)")
ax.legend(loc="upper left", fontsize=8)
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{OUT}/figA4_cifar_v2_vs_v4_fid.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A4 written")


# ---------------------------------------------------------------------------
# Figure A5: 6 R* bar chart with Bonf-sig p-value labels
# ---------------------------------------------------------------------------
print("Building Figure A5...")
# Data sourced from docs/headline-evidence/*/SOURCE.md + docs/CONSOLIDATED_RESULTS.md §15.34
r_data = [
    {"id": "R1", "model": "LineageFlow", "metric": "hmmscan_total_hits", "baseline": 158, "framework": 342, "delta_pct": +116.46, "p_bonf": 0.0, "verdict": "SUPPORTED", "direction": "higher"},
    {"id": "R2", "model": "FlowMol3",    "metric": "fg_dev",            "baseline": 0.6381, "framework": 0.6146, "delta_pct": -3.69, "p_bonf": 1.0, "verdict": "UNDERPOWERED", "direction": "lower"},
    {"id": "R3", "model": "CIFAR-10 RF",  "metric": "FID",               "baseline": 218.87, "framework": 122.18, "delta_pct": -44.17, "p_bonf": 0.0, "verdict": "framework_better (NFE-averaged)", "direction": "lower"},
    {"id": "R4", "model": "2D Two Moons",  "metric": "W₂",                "baseline": 0.5029, "framework": 0.4663, "delta_pct": -7.28, "p_bonf": 0.0, "verdict": "framework_better", "direction": "lower"},
    {"id": "R5", "model": "2D Eight Gauss","metric": "W₂",                "baseline": 0.6606, "framework": 0.5919, "delta_pct": -10.40, "p_bonf": 0.0, "verdict": "framework_better", "direction": "lower"},
    {"id": "R6", "model": "MNIST FM",     "metric": "FID",               "baseline": 409.18, "framework": 347.75, "delta_pct": -15.01, "p_bonf": 0.0, "verdict": "framework_better", "direction": "lower"},
]

# Normalize to baseline = 1.0 for visual comparison
fig, ax = plt.subplots(figsize=(10, 5.5))
labels_short = [f"{r['id']}\n{r['model']}\n{r['metric']}" for r in r_data]
ratios = [r['framework'] / r['baseline'] for r in r_data]
colors_r = ["#357" if r['verdict'].startswith("framework_better") or r['verdict'] == "SUPPORTED" else "#888" for r in r_data]
bars = ax.bar(labels_short, ratios, color=colors_r, edgecolor="#222", linewidth=0.8)
ax.axhline(1.0, color="#222", linestyle="--", linewidth=0.8, label="baseline (= 1.0)")

for bar, r in zip(bars, r_data):
    h = bar.get_height()
    delta_str = f"{r['delta_pct']:+.2f}%"
    if r['p_bonf'] == 0.0:
        p_str = "p<1e-10"
    elif r['p_bonf'] < 0.001:
        p_str = f"p={r['p_bonf']:.2e}"
    else:
        p_str = f"p={r['p_bonf']:.2f}"
    ax.text(bar.get_x() + bar.get_width()/2, h + 0.02, delta_str,
            ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.text(bar.get_x() + bar.get_width()/2, 0.02, p_str,
            ha="center", va="bottom", fontsize=7, color="#444")

ax.set_ylabel("Framework value / baseline value (lower=framework_better for FID/W₂/fg_dev)")
ax.set_title("Figure A5: 6 R* headline evidence — framework vs baseline\n(n=1000 per cell, Bonferroni-corrected p-values shown)")
ax.set_ylim(0, 1.6)
ax.legend(loc="upper right", fontsize=8)
ax.grid(True, axis="y", alpha=0.3)
plt.xticks(rotation=0, fontsize=8)
plt.tight_layout()
plt.savefig(f"{OUT}/figA5_six_r_star_bars.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A5 written")


# ---------------------------------------------------------------------------
# Figure A6: Per-cell p-value distribution (12 rows)
# ---------------------------------------------------------------------------
print("Building Figure A6...")
import csv
with open("verification_outputs/power_analysis/per_cell.csv") as f:
    rows = list(csv.DictReader(f))

# Sort by p_value_raw
rows_sorted = sorted(rows, key=lambda r: float(r["p_value_raw"]))

fig, ax = plt.subplots(figsize=(8.5, 5.5))
y = np.arange(len(rows_sorted))
pvals = [float(r["p_value_raw"]) for r in rows_sorted]
labels = [f"{r['model'][:6]:6s} | {r['metric'][:22]:22s}" for r in rows_sorted]
colors_p = []
for r in rows_sorted:
    pv = float(r["p_value_raw"])
    vc = r["verdict"]
    if vc == "TIE":
        colors_p.append("#888")
    elif pv < 0.05:
        colors_p.append("#357")
    else:
        colors_p.append("#d57")

ax.barh(y, [-np.log10(max(pv, 1e-10)) for pv in pvals], color=colors_p, edgecolor="#222", linewidth=0.6)
ax.axvline(-np.log10(0.05), color="#222", linestyle="--", linewidth=0.8, alpha=0.7, label="p=0.05 threshold")
ax.axvline(-np.log10(0.05/12), color="#a00", linestyle=":", linewidth=0.8, alpha=0.7, label="Bonf-corrected p=0.05/12")
ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=8, family="monospace")
ax.set_xlabel("−log₁₀(p_value_raw)")
ax.set_title("Figure A6: Per-cell p-value distribution across 12 measurement cells\n(3 models × 4 metrics; UNDERPOWERED=red, significant=blue, TIE=gray)")
ax.legend(loc="lower right", fontsize=8)
ax.invert_yaxis()
ax.grid(True, axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{OUT}/figA6_per_cell_pvalue_distribution.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A6 written")


# ---------------------------------------------------------------------------
# Figure A7: LineageFlow HMMER +116% bar chart
# ---------------------------------------------------------------------------
print("Building Figure A7...")
fig, ax = plt.subplots(figsize=(6, 4.5))

labels_hmmer = ["Baseline\n(Euler, NFE=200)", "Framework\n(multi-round, NFE=200)"]
values_hmmer = [158, 342]
colors_hmmer = ["#888", "#357"]
bars = ax.bar(labels_hmmer, values_hmmer, color=colors_hmmer, edgecolor="#222", linewidth=0.8)

for bar, v in zip(bars, values_hmmer):
    ax.text(bar.get_x() + bar.get_width()/2, v + 6, f"{v}", ha="center", va="bottom", fontsize=10, fontweight="bold")

# Delta annotation
ax.annotate("", xy=(1, 320), xytext=(0, 200),
            arrowprops=dict(arrowstyle="->", color="#357", lw=1.5))
ax.text(0.5, 360, "+116.46%  (p=0, Bonferroni-corrected)", ha="center", va="center", fontsize=10, color="#357", fontweight="bold")

ax.set_ylabel("HMMER total hits (count)")
ax.set_title("Figure A7: LineageFlow HMMER total hits — baseline vs framework\n(N=1000 samples, R1 headline evidence, p<1e-10)")
ax.set_ylim(0, 420)
ax.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{OUT}/figA7_lineageflow_hmmer.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A7 written")


# ---------------------------------------------------------------------------
# Figure A8: 3 composite axis bar plots (3/3 Tier 3 models)
# ---------------------------------------------------------------------------
print("Building Figure A8...")
# Composite values from docs/headline-evidence/composite_axis_byte_stable/SOURCE.md
# and verification_outputs/lineageflow_v2_aggregated_q4_2026.json
composite_data = [
    {"model": "Kanzi",       "composite": +0.1695, "n_cells": 18, "verdict": "framework_improves"},
    {"model": "LineageFlow", "composite": +0.2083, "n_cells": 8,  "verdict": "framework_improves"},
    {"model": "FlowMol3",    "composite": +0.1182, "n_cells": 3,  "verdict": "framework_improves"},
]

fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))
for ax, cd in zip(axes, composite_data):
    label = f"{cd['model']}\n(n={cd['n_cells']} cells)"
    ax.bar(["Framework\ncomposite\n(signed Δ%)"], [cd["composite"]], color="#357", edgecolor="#222", linewidth=0.8)
    ax.text(0, cd["composite"] + 0.01, f"+{cd['composite']*100:.2f}pp", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.text(0, -0.02, f"n={cd['n_cells']}\nbyte-stable", ha="center", va="top", fontsize=8, color="#444")
    ax.set_ylim(-0.05, 0.28)
    ax.set_ylabel("Composite axis Δ (%)")
    ax.set_title(label, fontsize=10)
    ax.axhline(0, color="#222", linewidth=0.8)
    ax.grid(True, axis="y", alpha=0.3)

fig.suptitle("Figure A8: Composite axis byte-stable improvements — 3/3 Tier 3 models framework_improves", fontsize=11, y=1.02)
plt.tight_layout()
plt.savefig(f"{OUT}/figA8_composite_axis_3_models.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A8 written")


# ---------------------------------------------------------------------------
# Figure A1b: 3D trajectory plot (Kanzi record 0, codebook indices over 64 positions)
# ---------------------------------------------------------------------------
print("Building Figure A1b (3D trajectory)...")
ck = json.load(open("verification_outputs/kanzi_inv_proj_n20_20260913_corrected/checkpoint.json"))
rec0 = ck["records"][0]
indices = np.array(rec0["codebook_indices"])

fig = plt.figure(figsize=(8, 5))
ax = fig.add_subplot(111, projection='3d')
t = np.arange(len(indices))
ax.plot(t, indices, rec0["rmsd_A"] * np.ones_like(indices), color="#357", linewidth=1.0, marker="o", markersize=2.5)
ax.set_xlabel("Position index")
ax.set_ylabel("Codebook index (0-999)")
ax.set_zlabel("Per-record RMSD (Å)")
ax.set_title("Figure A1b: Kanzi seq_0 — codebook trajectory over 64 positions\n(framework_inv_proj N=20 sweep, RMSD=1.048 Å)", fontsize=10)
plt.tight_layout()
plt.savefig(f"{OUT}/figA1b_kanzi_codebook_trajectory.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figure A1b written")


print("\nAll appendix figures built.")
print(f"Files written to {OUT}/")
