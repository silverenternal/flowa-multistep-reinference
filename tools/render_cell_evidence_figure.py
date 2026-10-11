#!/usr/bin/env python3
"""Render the 11-cell evidence-comparison figure (data-comparison diagram).

ADDITIVE only -- no number is modified. Every value transcribed here is
copied verbatim from the canonical manuscript, `docs/drafts/paper-A-final.md`:

  * Panel (a) per-cell standardized effect sizes -- §7.2 per-cell rows:
      R2  Kanzi inv-proj RMSD   d_z = -0.0990  (STRONG,  framework-WINS)
      R1  LineageFlow HMMER     d_z = +0.182   (PARTIAL, framework-WINS)
      R6  Kanzi k6 pLDDT        d_z = +0.2235  (tier-aware counterfactual)
                                d_z = +1.189   (hard tier)
      R3  FlowMol3 REOS         d_z = -0.285   (PARTIAL, framework-WINS)
      R5a 2D Two Moons W_2      d_s = +0.460   (TIE, unpaired)
      R5c MNIST FM FID (smoke)  d_z = -13.18   (STRONG, framework-WINS)
    The vertical reference line at |d| = 0.8 is the paper's STRONG-promotion
    bar (§7.2: "d_z > 0.8 STRONG-promotion bar").
  * Panel (b) the 11-cell verdict distribution -- §7.2 / §7.11:
      4 STRONG + 1 TIE + 2 PARTIAL/single-seed + 4 SUPP-only = 11 cells.
    R5b is CONDITIONAL (protocol-dependent single-round) and the 4 K-cells
    are SUPP-only; neither carries a single standardized effect size, so
    panel (a) plots only the cells with a reported effect.

The renderer uses matplotlib's `Agg` backend (headless) and is byte-stable
under repeated invocation. It emits a single-column, 2-panel PNG to
`docs/figures/fig9_cell_evidence_comparison.png`.

Usage:
    .venvs/flowmol3_venv/bin/python tools/render_cell_evidence_figure.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedFormatter, FixedLocator

# ---------------------------------------------------------------------------
# Verbatim data from paper-A-final.md §7.2 / §7.11 (no number change).
# Each row: (cell_id, metric_short, |effect|, display_str, verdict).
# `display_str` reproduces the paper's exact precision (trailing zeros kept).
# ---------------------------------------------------------------------------
PANEL_A = (
    ("R2", "Kanzi inv-proj RMSD", 0.0990, "$d_z=-0.0990$", "STRONG"),
    ("R1", "LineageFlow HMMER", 0.182, "$d_z=+0.182$", "PARTIAL"),
    ("R6", "Kanzi k6 pLDDT (tier-aware)", 0.2235, "$d_z=+0.2235$", "STRONG"),
    ("R3", "FlowMol3 REOS flags", 0.285, "$d_z=-0.285$", "PARTIAL"),
    ("R5a", "2D Two Moons $W_2$", 0.460, "$d_s=+0.460$", "TIE"),
    ("R6", "Kanzi k6 pLDDT (hard tier)", 1.189, "$d_z=+1.189$", "STRONG"),
    ("R5c", "MNIST FM FID (smoke)", 13.18, "$d_z=-13.18$", "STRONG"),
)

# Verdict distribution from §7.2 aggregate line / §7.11.
PANEL_B = (
    ("STRONG", 4, "#1b7837"),
    ("TIE", 1, "#777777"),
    ("PARTIAL", 2, "#b35806"),
    ("SUPP", 4, "#c9c9c9"),
)

# Verdict -> marker face colour (shared across panels).
_VERDICT_COLOR = {
    "STRONG": "#1b7837",
    "TIE": "#777777",
    "PARTIAL": "#b35806",
    "SUPP": "#c9c9c9",
}
_STRONG_BAR = 0.8  # §7.2 STRONG-promotion bar |d| > 0.8


def _render_panel_a(ax) -> None:
    n = len(PANEL_A)
    ys = list(range(n))[::-1]  # top-to-bottom
    for y, (_cell, _metric, mag, _disp, verdict) in zip(ys, PANEL_A, strict=True):
        color = _VERDICT_COLOR[verdict]
        ax.scatter(mag, y, s=70, c=color, edgecolors="#222222",
                   linewidths=0.8, zorder=3)

    ax.axvline(_STRONG_BAR, color="#b2182b", linewidth=1.1,
               linestyle="--", zorder=1)
    ax.annotate(
        "STRONG bar $|d|=0.8$",
        xy=(_STRONG_BAR, -0.45), xytext=(4, 0),
        textcoords="offset points", ha="left", va="center",
        fontsize=6.5, color="#b2182b",
    )

    ax.set_xscale("log")
    ax.set_xlim(0.06, 40)
    ax.set_ylim(-0.7, n - 0.4)
    ax.set_yticks(ys)
    # Values live in the y-tick labels so the STRONG-bar line never crosses text.
    ax.set_yticklabels(
        [f"{c}  {m}\n({d})" for c, m, _mag, d, _v in PANEL_A], fontsize=6.5
    )
    ax.set_xlabel("standardized effect size $|d|$ (log scale)", fontsize=8)
    ax.set_title("(a) Per-cell effect size", fontsize=9, pad=4)
    ax.grid(True, axis="x", alpha=0.25, linestyle=":")
    ax.tick_params(axis="x", labelsize=7)


def _render_panel_b(ax) -> None:
    labels = [b[0] for b in PANEL_B]
    counts = [b[1] for b in PANEL_B]
    colors = [b[2] for b in PANEL_B]
    ys = list(range(len(PANEL_B)))[::-1]
    ax.barh(ys, counts, color=colors, edgecolor="#222222",
            linewidth=0.7, height=0.62, zorder=3)
    for y, c in zip(ys, counts, strict=True):
        ax.annotate(str(c), xy=(c, y), xytext=(4, 0),
                    textcoords="offset points", ha="left", va="center",
                    fontsize=8, color="#222222")
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 5)
    ax.xaxis.set_major_locator(FixedLocator([0, 1, 2, 3, 4]))
    ax.xaxis.set_major_formatter(FixedFormatter(["0", "1", "2", "3", "4"]))
    ax.set_xlabel("cells", fontsize=8)
    ax.set_title("(b) 11-cell verdict distribution", fontsize=9, pad=4)
    ax.grid(True, axis="x", alpha=0.25, linestyle=":")
    ax.tick_params(axis="x", labelsize=7)


def render(out_path: str) -> None:
    fig, (ax_a, ax_b) = plt.subplots(
        2, 1, figsize=(3.45, 4.6), dpi=300,
        gridspec_kw={"height_ratios": [3.1, 1.0]},
    )
    fig.patch.set_facecolor("white")
    _render_panel_a(ax_a)
    _render_panel_b(ax_b)
    fig.tight_layout(h_pad=1.4)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__),
                       "..", "docs", "figures",
                       "fig9_cell_evidence_comparison.png")
    out = os.path.abspath(out)
    render(out)
    print(f"wrote {out}")
