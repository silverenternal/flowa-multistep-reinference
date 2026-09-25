#!/usr/bin/env python3
"""Render the R5b 4-scheduler x 3-n_rounds conditional grid (Wave 350 P4).

Inputs are byte-stable from paper §7.6 mechanism paragraph + the
companion audit trail (Wave 235 P1 rounds1, Wave 225 P7 rounds2,
Wave 206 P6 n_rounds=20 honest-negative-curve). The script emits a
2-panel PNG to docs/drafts/figure_r5b_conditional_grid.png that
visualises the §7.6 n_rounds conditional boundary on CIFAR-10 RF at
matched NFE = 50.

Panel A: heatmap of Delta FID % across 4 schedulers (rows)
         x 3 n_rounds (cols); colour-coded red=baseline_wins,
         green=framework_wins (zero line as boundary).
Panel B: bar chart of Delta FID % vs n_rounds grouped per scheduler
         (3 grouped bars per scheduler).

ADDITIVE only - no numbers are modified. The 12-cell data is
transcribed verbatim from the §7.6 mechanism paragraph + the Wave 235
P1 / Wave 225 P7 / Wave 206 P6 audit material.

Usage:
    python3 tools/render_r5b_conditional_grid.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Byte-stable data points (paper §7.6 mechanism paragraph + audit trail)
#
# Sources:
#   n_rounds=1 : docs/audit/wave235-p1-r5b-fix.{json,csv}
#                 (Wave 235 P1 rounds1, --match-nfe n_rounds=1, baseline_fid
#                 454.3854, n=200 per arm)
#   n_rounds=2 : docs/audit/wave225-p7-r5b-reduced-rounds.{json,csv}
#                 (Wave 225 P7 --match-nfe n_rounds=2, baseline_fid
#                 458.5809, n=200 per arm)
#   n_rounds=20: docs/audit/wave206-p6-cifar-rf-v4-honest-negative-curve.{json,csv}
#                 (Wave 206 P6 --match-nfe n_rounds=20, baseline_fid
#                 83.0866, n=500 per arm; pre-EMA-fix Liu 2022 published
#                 -style inception, the load-bearing Source-A reading)
#
# Each cell is (scheduler, delta_fid_pct). Positive = baseline_wins,
# negative = framework_wins.
# ---------------------------------------------------------------------------

SCHEDULERS = (
    "CosineAnnealScheduler",
    "CodimensionSheetScheduler",
    "EvidenceDrivenScheduler",
    "FreeTrajScheduler",
)
N_ROUNDS = (1, 2, 20)

# 4 schedulers (rows) x 3 n_rounds (cols).
DELTA_FID_PCT = np.array(
    [
        # n_rounds=1  n_rounds=2  n_rounds=20
        [-1.6018,    9.7652,    24.89   ],  # CosineAnnealScheduler
        [-2.5302,    9.7879,    25.13   ],  # CodimensionSheetScheduler
        [-0.1173,    9.8260,    24.46   ],  # EvidenceDrivenScheduler
        [-0.6638,   16.6216,    30.65   ],  # FreeTrajScheduler
    ],
    dtype=float,
)


def _verdict(delta_pct: float) -> str:
    if delta_pct < 0.0:
        return "framework_wins"
    return "baseline_wins"


def _cell_label(delta_pct: float) -> str:
    return f"{delta_pct:+.2f}%"


def render(out_path: str) -> None:
    """Render the 2-panel conditional grid figure to ``out_path``.

    Panel A (heatmap) is a 4x3 grid of Delta FID % cells with
    diverging red/green colour-coding (red = baseline_wins,
    green = framework_wins). Panel B (bar chart) shows the same
    12-cell data grouped by scheduler with 3 coloured bars per
    group (one per n_rounds).
    """
    fig, (ax_hm, ax_bar) = plt.subplots(
        1, 2, figsize=(12.0, 4.8), dpi=150, gridspec_kw={"width_ratios": [1.0, 1.6]}
    )
    fig.patch.set_facecolor("white")
    for ax in (ax_hm, ax_bar):
        ax.set_facecolor("white")

    # -------------------------- Panel A: heatmap --------------------------
    vmax = float(np.max(np.abs(DELTA_FID_PCT)))
    heatmap = ax_hm.imshow(
        DELTA_FID_PCT,
        cmap="RdYlGn_r",  # red = baseline_wins (positive), green = framework_wins
        vmin=-vmax,
        vmax=+vmax,
        aspect="auto",
    )
    ax_hm.set_xticks(range(len(N_ROUNDS)))
    ax_hm.set_xticklabels([f"n_rounds={r}" for r in N_ROUNDS], fontsize=10)
    ax_hm.set_yticks(range(len(SCHEDULERS)))
    ax_hm.set_yticklabels(SCHEDULERS, fontsize=9)
    ax_hm.set_xlabel("n_rounds (restart rounds)", fontsize=10)
    ax_hm.set_title("Panel A: Delta FID % heatmap (4 schedulers x 3 n_rounds)", fontsize=11)
    # Annotate each cell with its byte-stable delta + verdict.
    for i in range(len(SCHEDULERS)):
        for j in range(len(N_ROUNDS)):
            dp = float(DELTA_FID_PCT[i, j])
            colour = "white" if abs(dp) > vmax * 0.55 else "#111111"
            label = f"{dp:+.2f}%\n[{_verdict(dp)}]"
            ax_hm.text(
                j, i, label,
                ha="center", va="center",
                fontsize=7.5,
                color=colour,
            )
    cbar = fig.colorbar(heatmap, ax=ax_hm, fraction=0.046, pad=0.04)
    cbar.set_label(r"$\Delta$ FID %  (positive = baseline_wins)", fontsize=9)

    # -------------------------- Panel B: grouped bars ---------------------
    n_sched = len(SCHEDULERS)
    n_r = len(N_ROUNDS)
    bar_width = 0.25
    x = np.arange(n_sched, dtype=float)
    bar_colors = ["#1b7837", "#7570b3", "#b35806"]  # green, purple, orange
    bar_labels = [f"n_rounds={r}" for r in N_ROUNDS]
    for j in range(n_r):
        offsets = (j - (n_r - 1) / 2.0) * bar_width
        ax_bar.bar(
            x + offsets,
            DELTA_FID_PCT[:, j],
            width=bar_width,
            color=bar_colors[j],
            edgecolor="#222222",
            linewidth=0.6,
            label=bar_labels[j],
            zorder=3,
        )
    ax_bar.axhline(0.0, color="#888888", linewidth=1.0, linestyle="--", zorder=1)
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(
        ["Cosine", "Codim", "Evidence", "FreeTraj"],
        fontsize=9,
    )
    ax_bar.set_xlabel("Scheduler", fontsize=10)
    ax_bar.set_ylabel(r"$\Delta$ FID %  (positive = baseline_wins)", fontsize=10)
    ax_bar.set_title(
        "Panel B: Delta FID % vs n_rounds, grouped per scheduler", fontsize=11, pad=10
    )
    ax_bar.set_ylim(min(-3.5, float(np.min(DELTA_FID_PCT)) - 1.5),
                    float(np.max(DELTA_FID_PCT)) + 4.0)
    ax_bar.legend(
        loc="upper right",
        fontsize=8,
        title="n_rounds",
        title_fontsize=8,
        frameon=True,
        framealpha=0.9,
        edgecolor="#888888",
        ncol=1,
        bbox_to_anchor=(1.0, 1.0),
    )
    # Annotate each bar with its delta + a verdict badge.
    for j in range(n_r):
        offsets = (j - (n_r - 1) / 2.0) * bar_width
        for i in range(n_sched):
            dp = float(DELTA_FID_PCT[i, j])
            ax_bar.text(
                x[i] + offsets,
                dp + (0.45 if dp >= 0 else -0.45),
                f"{dp:+.2f}",
                ha="center",
                va="bottom" if dp >= 0 else "top",
                fontsize=7,
                color="#222222",
            )

    fig.suptitle(
        r"R5b 4-scheduler x 3-n_rounds conditional grid on CIFAR-10 RF "
        r"(matched NFE = 50)",
        fontsize=12,
        y=1.01,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(
        repo_root, "docs", "drafts", "figure_r5b_conditional_grid.png"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    render(out_path)
    size_bytes = os.path.getsize(out_path)
    print(f"wrote {out_path} ({size_bytes} bytes)")


if __name__ == "__main__":
    main()
