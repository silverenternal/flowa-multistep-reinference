#!/usr/bin/env python3
"""Render the R5c regime-dependent curve figure (Wave 349 GAP-1).

Inputs are byte-stable from paper §7.8 3-point table (paper-A-final.md
lines 383-389). The script emits a single PNG to docs/figures/
(fig5_r5c_regime_curve.png) that visualises the matched-NFE=50
framework-vs-baseline FID delta across 3 MNIST FM checkpoints at
increasing training intensity.

ADDITIVE only — no numbers are modified. The three (epochs, delta_pct,
verdict) tuples are transcribed verbatim from the paper table.

Usage:
    python3 tools/render_r5c_regime_curve.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt

# Byte-stable data points from paper §7.8 table (lines 383-389).
# Each tuple is (epochs, delta_fid_pct, baseline_fid, framework_fid, verdict).
DATA = (
    (1, -28.43, 29.49, 23.39, "framework_wins"),
    (2, +8.53, 13.45, 15.44, "baseline_wins"),
    (3, +10.37, 11.99, 13.67, "baseline_wins"),
)


def _label_for(epochs: int, delta_pct: float, verdict: str) -> str:
    return f"epochs={epochs}\n({delta_pct:+.2f}%)\n[{verdict}]"


def render(out_path: str) -> None:
    """Render the regime curve as a single-panel PNG.

    The plot uses a horizontal zero-line to mark the framework-wins vs
    baseline-wins boundary, and labels each data point with the
    byte-stable verdict from the §7.8 table.
    """
    epochs = [d[0] for d in DATA]
    delta_pct = [d[1] for d in DATA]
    verdicts = [d[4] for d in DATA]

    fig, ax = plt.subplots(figsize=(5.5, 3.6), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    colors = ["#1b7837" if v == "framework_wins" else "#b35806" for v in verdicts]
    ax.axhline(0, color="#888888", linewidth=1.0, linestyle="--", zorder=1)
    ax.scatter(epochs, delta_pct, s=120, c=colors, zorder=3,
               edgecolors="#222222", linewidths=0.8)
    ax.plot(epochs, delta_pct, color="#444444", linewidth=1.4, zorder=2,
            alpha=0.7)

    for d in DATA:
        ep, dp, _, _, verdict = d
        offset_y = -6.5 if dp > 0 else 6.5
        ax.annotate(
            _label_for(ep, dp, verdict),
            xy=(ep, dp),
            xytext=(0, offset_y),
            textcoords="offset points",
            ha="center",
            va="top" if dp > 0 else "bottom",
            fontsize=8,
            color="#222222",
        )

    ax.set_xlabel("MNIST FM checkpoint training intensity (epochs)", fontsize=10)
    ax.set_ylabel(r"$\Delta$ FID %  (framework vs baseline, matched NFE = 50)",
                  fontsize=10)
    ax.set_xticks([1, 2, 3])
    ax.set_title("R5c regime-dependent curve (smoke vs production ckpt)",
                 fontsize=11, pad=10)
    ax.grid(True, axis="y", alpha=0.25, linestyle=":")
    ax.set_ylim(-36, 18)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__),
                       "..", "docs", "figures",
                       "fig5_r5c_regime_curve.png")
    out = os.path.abspath(out)
    render(out)
    print(f"wrote {out}")
