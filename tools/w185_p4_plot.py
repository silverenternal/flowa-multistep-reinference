"""Wave 185 P4 — Plot empirical vs theoretical BL curves + tightness ratio.

Reads verification_outputs/wave185-p3-tightness.csv and produces:

  - verification_outputs/wave185-p4-figure-bl-tightness.png
    (2 lines per model: empirical point + CI ribbon, theoretical bound)

  - verification_outputs/wave185-p4-figure-tightness-ratio.png
    (1 line per model: empirical / theoretical on log y)

The empirical value is the 1-D pLDDT energy distance (the headline BL
proxy on protein, per Wave 185 P1 §2.1). CIs are the percentile-bootstrap
95% intervals from Wave 185 P2.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
CSV_PATH = REPO / "verification_outputs" / "wave185-p3-tightness.csv"
OUT_FIG1 = REPO / "verification_outputs" / "wave185-p4-figure-bl-tightness.png"
OUT_FIG2 = REPO / "verification_outputs" / "wave185-p4-figure-tightness-ratio.png"

# Model display metadata
MODEL_META = {
    "lineageflow": {"label": "LineageFlow", "color": "#1f77b4", "marker": "o"},
    "kanzi":       {"label": "Kanzi",       "color": "#d62728", "marker": "s"},
}

# Theoretical bound is a single curve (g=sin(πx) snapshot); one style per plot.
THEORY_COLOR = "#2ca02c"
THEORY_LINESTYLE = "--"
THEORY_LABEL = "Theorem 1 bound (B(NFE))"


def load_rows() -> list[dict]:
    with CSV_PATH.open(newline="") as f:
        return list(csv.DictReader(f))


def plot_bl_tightness(rows: list[dict]) -> None:
    """Plot 1: empirical (with CI) vs theoretical bound, per model."""
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=120)

    by_model: dict[str, list[dict]] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)

    # Theoretical bound: profile-only, so identical across models.
    # Use lineageflow rows for the x-axis order, but draw bound once.
    ref = sorted(by_model["lineageflow"], key=lambda r: int(r["nfe"]))
    nfe_ref = np.array([int(r["nfe"]) for r in ref])
    bound_ref = np.array([float(r["theoretical_bound"]) for r in ref])
    ax.plot(
        nfe_ref,
        bound_ref,
        color=THEORY_COLOR,
        linestyle=THEORY_LINESTYLE,
        linewidth=1.8,
        label=THEORY_LABEL,
        zorder=1,
    )

    for model, mrows in by_model.items():
        mrows_sorted = sorted(mrows, key=lambda r: int(r["nfe"]))
        nfe = np.array([int(r["nfe"]) for r in mrows_sorted])
        emp = np.array([float(r["empirical_BL"]) for r in mrows_sorted])
        ci_lo = np.array([float(r["ci_low"]) for r in mrows_sorted])
        ci_hi = np.array([float(r["ci_high"]) for r in mrows_sorted])

        meta = MODEL_META[model]
        ax.fill_between(
            nfe,
            ci_lo,
            ci_hi,
            color=meta["color"],
            alpha=0.15,
            zorder=2,
        )
        ax.errorbar(
            nfe,
            emp,
            yerr=[np.abs(emp - ci_lo), np.abs(ci_hi - emp)],
            color=meta["color"],
            marker=meta["marker"],
            markersize=7,
            linewidth=1.6,
            capsize=4,
            label=f"{meta['label']} (empirical, 95% CI)",
            zorder=3,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("NFE (function evaluations)", fontsize=11)
    ax.set_ylabel("BL distance (1-D pLDDT energy distance)", fontsize=11)
    ax.set_title(
        "Empirical vs Theoretical BL distance\n"
        "Wave 185 P4 — protein axis (lineageflow, kanzi)",
        fontsize=12,
    )
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)

    # Annotate the violation regime: empirical is far above the bound.
    ax.text(
        0.02,
        0.04,
        "Empirical ≫ Theorem 1 bound at every cell\n"
        "(framework-vs-baseline vs framework self-distance)",
        transform=ax.transAxes,
        fontsize=8,
        color="#444444",
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor="#888888", alpha=0.85),
    )

    fig.tight_layout()
    fig.savefig(OUT_FIG1)
    plt.close(fig)
    print(f"wrote {OUT_FIG1}")


def plot_tightness_ratio(rows: list[dict]) -> None:
    """Plot 2: tightness ratio (empirical / theoretical) per model."""
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=120)

    by_model: dict[str, list[dict]] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)

    for model, mrows in by_model.items():
        mrows_sorted = sorted(mrows, key=lambda r: int(r["nfe"]))
        nfe = np.array([int(r["nfe"]) for r in mrows_sorted])
        ratio = np.array([float(r["tightness_ratio"]) for r in mrows_sorted])

        meta = MODEL_META[model]
        ax.plot(
            nfe,
            ratio,
            color=meta["color"],
            marker=meta["marker"],
            markersize=8,
            linewidth=1.8,
            label=f"{meta['label']}",
            zorder=3,
        )
        for x, y in zip(nfe, ratio, strict=False):
            ax.annotate(
                f"{y:.0f}×",
                xy=(x, y),
                xytext=(0, 8),
                textcoords="offset points",
                fontsize=8,
                color=meta["color"],
                ha="center",
            )

    ax.axhline(1.0, color="#888888", linestyle=":", linewidth=1.2,
               label="tightness = 1× (bound honest)", zorder=1)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("NFE (function evaluations)", fontsize=11)
    ax.set_ylabel("Tightness ratio = empirical_BL / B(NFE)", fontsize=11)
    ax.set_title(
        "Tightness ratio per (model, NFE)\n"
        "Wave 185 P4 — empirical / Theorem 1 bound",
        fontsize=12,
    )
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="lower left", fontsize=9, framealpha=0.92)

    # Show the full ratio span.
    ax.text(
        0.98,
        0.04,
        "Ratio ≫ 1 at every cell:\n"
        "theoretical bound is 25×–7,500× tighter than the empirical BL on protein",
        transform=ax.transAxes,
        fontsize=8,
        color="#444444",
        verticalalignment="bottom",
        horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor="#888888", alpha=0.85),
    )

    fig.tight_layout()
    fig.savefig(OUT_FIG2)
    plt.close(fig)
    print(f"wrote {OUT_FIG2}")


def main() -> None:
    rows = load_rows()
    assert rows, "no rows loaded from CSV"
    plot_bl_tightness(rows)
    plot_tightness_ratio(rows)


if __name__ == "__main__":
    main()
