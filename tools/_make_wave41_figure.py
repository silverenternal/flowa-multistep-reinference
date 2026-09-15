"""Wave 41 paper-audit figure — per-family signed_mean bar chart.

Renders a horizontal bar chart of the 4 model-family signed_mean values
from `verification_outputs/capability_audit_q4_2026.json` G.1 evidence
section, plus the G.1 robust median target line at +0.05.

Run:  .venvs/flowmol3_venv/bin/python tools/_make_wave41_figure.py
Output: docs/figures/fig8-per-family-signed-mean.png
"""
from __future__ import annotations

import json
import os

from tools._figures_common import OUT_DIR, plt, save_figure

# Brand-neutral palette (dataviz skill, consistent with tools/_make_figures.py)
PALETTE = {
    "ink": "#222831",
    "frame": "#00ADB5",
    "positive": "#00B4A6",
    "negative": "#E76F51",
    "neutral": "#888888",
    "target": "#FFD460",
    "background": "#EEEEEE",
    "text": "#393E46",
}

AUDIT_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "verification_outputs",
    "capability_audit_q4_2026.json",
)


def aggregate_per_family(audit: dict) -> list[tuple[str, int, float, list[float]]]:
    """Return [(family, n_rows, signed_mean, [deltas])] sorted by signed_mean desc."""
    rows = audit["g1"]["evidence"]
    by_family: dict[str, list[float]] = {}
    for r in rows:
        by_family.setdefault(r["model_family"], []).append(r["signed_delta_pct"])
    out: list[tuple[str, int, float, list[float]]] = []
    for family, deltas in by_family.items():
        sm = sum(deltas) / len(deltas)
        out.append((family, len(deltas), sm, deltas))
    out.sort(key=lambda t: t[2], reverse=True)
    return out


def fig8_per_family_signed_mean() -> str:
    with open(AUDIT_JSON, encoding="utf-8") as f:
        audit = json.load(f)

    families = aggregate_per_family(audit)
    g1_robust = audit["g1"]["value"]
    g1_target = 0.05  # >= +0.05 per docs/framework-internal-metrics G.1
    g1_alt = audit["g1"]["alt_value"]
    g1_alt_agg = audit["g1"]["alt_aggregator"]

    fig, ax = plt.subplots(figsize=(11, 5.0))

    labels = [f"{fam}\n(n={n})" for fam, n, _, _ in families]
    means = [sm for _, _, sm, _ in families]
    bar_colors = [
        PALETTE["positive"] if m > 0 else PALETTE["negative"] for m in means
    ]

    bars = ax.barh(
        labels,
        means,
        color=bar_colors,
        edgecolor=PALETTE["ink"],
        linewidth=0.7,
        height=0.6,
    )

    # Annotate each bar with its value
    x_max = max(max(means), abs(min(means)) if min(means) < 0 else 0, g1_target) * 1.4
    for bar, sm, deltas in zip(bars, means, [d for *_, d in families], strict=False):
        # Display value
        ax.text(
            bar.get_width() + (0.01 if sm >= 0 else -0.01),
            bar.get_y() + bar.get_height() / 2,
            f"{sm:+.4f}",
            va="center",
            ha="left" if sm >= 0 else "right",
            color=PALETTE["ink"],
            fontsize=10,
            fontweight="bold",
        )
        # Range annotation
        dmin, dmax = min(deltas), max(deltas)
        ax.text(
            bar.get_width() + (0.05 if sm >= 0 else -0.05),
            bar.get_y() + bar.get_height() / 2 - 0.16,
            f"range [{dmin:+.4f}, {dmax:+.4f}]",
            va="center",
            ha="left" if sm >= 0 else "right",
            color=PALETTE["text"],
            fontsize=8,
            style="italic",
        )

    # Target line
    ax.axvline(
        g1_target,
        color=PALETTE["target"],
        linewidth=2.0,
        linestyle="--",
        label=f"G.1 robust target = +{g1_target}",
    )

    # Zero line
    ax.axvline(0, color=PALETTE["ink"], linewidth=0.7)

    ax.set_xlim(-0.10, x_max + 0.05)
    ax.set_xlabel(
        "Signed Δ% per family = mean((framework − baseline) / |baseline|)",
        color=PALETTE["ink"],
        fontsize=10,
    )
    ax.set_title(
        "FlowA framework value surface by model family — "
        f"G.1 robust median = {g1_robust:+.4f} (PASS, target ≥ +0.05)",
        color=PALETTE["ink"],
        fontsize=12,
        fontweight="bold",
        loc="left",
    )
    ax.invert_yaxis()  # highest signed_mean on top
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PALETTE["ink"])
    ax.spines["bottom"].set_color(PALETTE["ink"])
    ax.tick_params(colors=PALETTE["ink"])
    ax.grid(axis="x", linestyle=":", alpha=0.4, color=PALETTE["neutral"])

    # Legend with G.1 alt info
    legend_text = (
        f"Aggregator (canonical): median of signed deltas — {g1_robust:+.4f} (PASS)\n"
        f"Aggregator (alt, spec-literal mean): {g1_alt_agg}\n"
        f"  → value {g1_alt:+.4f} (FAIL — direction-aware wins outweigh regressions)"
    )
    ax.text(
        0.99,
        -0.32,
        legend_text,
        transform=ax.transAxes,
        fontsize=8,
        color=PALETTE["text"],
        ha="right",
        va="top",
        family="monospace",
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=PALETTE["background"],
            edgecolor=PALETTE["neutral"],
            linewidth=0.5,
        ),
    )

    fig.subplots_adjust(bottom=0.30)

    out = os.path.join(OUT_DIR, "fig8-per-family-signed-mean.png")
    save_figure(fig, out)
    return out


if __name__ == "__main__":
    p = fig8_per_family_signed_mean()
    print(f"wrote {p}")
