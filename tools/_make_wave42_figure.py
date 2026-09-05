"""Wave 42 paper-writeup figure — Tier 3 (Kanzi ICLR 2026 + LineageFlow ICML 2026) real-ckpt
framework advantage shown alongside Tier 1 (toy FM) + Tier 2 (SOTA image RF) values.

Renders a horizontal bar chart of per-family signed_mean for the 5 integrated model families,
colored by tier (Tier 1 toy = blue, Tier 2 SOTA image = green, Tier 3 SOTA 2026 = orange),
with a reference line at y=0.

Inputs:
  - verification_outputs/capability_audit_q4_2026.json (G.1 evidence for Tier 1 + Tier 2 rows)
  - verification_outputs/kanzi_real_ckpt_eval_q4_2026_kanzi.json (Tier 3 Kanzi cells)
  - verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json (Tier 3 LineageFlow forward-smoke)

Output: docs/figures/tier3_real_ckpt_signed_mean.png

Run: .venvs/flowmol3_venv/bin/python tools/_make_wave42_figure.py
"""
from __future__ import annotations

import json
import os

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

# Brand-neutral palette, augmented with tier color mapping
PALETTE = {
    "ink": "#222831",
    "frame": "#00ADB5",
    "positive": "#00B4A6",
    "negative": "#E76F51",
    "neutral": "#888888",
    "target": "#FFD460",
    "background": "#EEEEEE",
    "text": "#393E46",
    # Tier colors per task brief:
    # Tier 1 toy = blue, Tier 2 = green, Tier 3 = orange
    "tier1": "#3F88C5",   # blue
    "tier2": "#27AE60",   # green
    "tier3": "#E67E22",   # orange
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

AUDIT_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "verification_outputs",
    "capability_audit_q4_2026.json",
)
KANZI_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "verification_outputs",
    "kanzi_real_ckpt_eval_q4_2026_kanzi.json",
)
LINEAGEFLOW_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "verification_outputs",
    "lineageflow_real_ckpt_forward_q4_2026.json",
)


def _signed_mean_from_cells(cells: list[dict]) -> float:
    """Return mean signed_delta_pct across cells (0.0 if no cells)."""
    if not cells:
        return 0.0
    deltas = [float(c.get("signed_delta_pct", 0.0)) for c in cells]
    return sum(deltas) / len(deltas)


def _aggregate_tier1_tier2(audit: dict) -> dict[str, tuple[float, list[float]]]:
    """Read G.1 evidence and group rows by model_family. Returns
    {family: (signed_mean, [deltas])}."""
    rows = audit["g1"]["evidence"]
    by_family: dict[str, list[float]] = {}
    for r in rows:
        by_family.setdefault(r["model_family"], []).append(r["signed_delta_pct"])
    out: dict[str, tuple[float, list[float]]] = {}
    for family, deltas in by_family.items():
        out[family] = (sum(deltas) / len(deltas), deltas)
    return out


def _aggregate_tier3_kanzi(kanzi: dict) -> tuple[float, list[float]]:
    """Tier 3 Kanzi real-ckpt eval cells (9 = 3 seeds x 3 NFE budgets)."""
    cells = kanzi.get("cells", [])
    deltas = [float(c.get("signed_delta_pct", 0.0)) for c in cells]
    return _signed_mean_from_cells(cells), deltas


def _aggregate_tier3_lineageflow(lf: dict) -> tuple[float, list[float]]:
    """Tier 3 LineageFlow real-ckpt forward-pass probe.

    The forward JSON has no per-cell comparison cells (Wave 41 Agent B produced
    only the numerical forward smoke); the comparison-vs-baseline number comes
    from the Wave 10 R2 + Wave 19 P1A2 synthetic-shim runs captured in
    capability_audit (lineageflow_avg_log_likelihood row: +0.0024) plus the
    LineageFlow synthetic family_validity saturation tie (0.0).

    We present Tier 3 LineageFlow here as 0.0 because the real-ckpt eval has
    not yet been wrapped through tools/run_real_ckpt_eval.py; the forward probe
    is documented in lineageflow_real_ckpt_forward_q4_2026.json (success status,
    parameter count, output statistics).
    """
    # Forward smoke status is the only binary signal in the JSON; forward-pass
    # round-trip without NaN/Inf is the success criterion (status field).
    # Real-ckpt eval vs baseline not yet captured -> 0.0 honest reading.
    status = lf.get("status", "missing")
    has_nan = lf.get("forward_pass", {}).get("has_nan", True)
    has_inf = lf.get("forward_pass", {}).get("has_inf", True)
    if status == "success" and not has_nan and not has_inf:
        # Forward smoke passes, but the synthetic-shim comparison-vs-baseline
        # number remains 0.0 (synthetic shim saturation tie); we surface that
        # honestly rather than importing the Wave 10 R2 number (synthetic).
        return 0.0, [0.0]
    return 0.0, [0.0]


def main() -> str:
    with open(AUDIT_JSON, "r", encoding="utf-8") as f:
        audit = json.load(f)
    with open(KANZI_JSON, "r", encoding="utf-8") as f:
        kanzi = json.load(f)
    with open(LINEAGEFLOW_JSON, "r", encoding="utf-8") as f:
        lf = json.load(f)

    tier1_tier2 = _aggregate_tier1_tier2(audit)
    tier3_kanzi_sm, tier3_kanzi_deltas = _aggregate_tier3_kanzi(kanzi)
    tier3_lf_sm, tier3_lf_deltas = _aggregate_tier3_lineageflow(lf)

    # Order: x-axis ascending (Tier 1 toy -> Tier 2 -> Tier 3)
    # Brief says X-axis is model families; Y-axis is signed_mean.
    # Tier classification:
    #   Tier 1 toy: twodim_fm (2D analytic + Wang 2022 NFE), mnist_fm (Wave 26/28 toy)
    #   Tier 2: rectified_flow_cifar (Wave 4-7 v3 image RF SOTA comparison)
    #   Tier 3: kanzi (ICLR 2026 protein), lineageflow (ICML 2026 protein)
    family_data: list[tuple[str, int, float, list[float], str]] = [
        # (label, n_rows, signed_mean, deltas, tier)
        ("twodim_fm\n(Tier 1 toy)", tier1_tier2["twodim_fm"][1].__len__(),
         tier1_tier2["twodim_fm"][0], tier1_tier2["twodim_fm"][1], "tier1"),
        ("mnist_fm\n(Tier 1 toy)", tier1_tier2["mnist_fm"][1].__len__(),
         tier1_tier2["mnist_fm"][0], tier1_tier2["mnist_fm"][1], "tier1"),
        ("rectified_flow_cifar\n(Tier 2 SOTA image)", tier1_tier2["rectified_flow_cifar"][1].__len__(),
         tier1_tier2["rectified_flow_cifar"][0], tier1_tier2["rectified_flow_cifar"][1], "tier2"),
        ("kanzi\n(Tier 3 ICLR 2026 protein)",
         len(tier3_kanzi_deltas), tier3_kanzi_sm, tier3_kanzi_deltas, "tier3"),
        ("lineageflow\n(Tier 3 ICML 2026 protein)",
         len(tier3_lf_deltas), tier3_lf_sm, tier3_lf_deltas, "tier3"),
    ]

    labels = [f[0] for f in family_data]
    means = [f[2] for f in family_data]
    deltas_list = [f[3] for f in family_data]
    tiers = [f[4] for f in family_data]
    bar_colors = [PALETTE[t] for t in tiers]

    fig, ax = plt.subplots(figsize=(11, 5.5))

    bars = ax.barh(
        labels,
        means,
        color=bar_colors,
        edgecolor=PALETTE["ink"],
        linewidth=0.7,
        height=0.6,
    )

    # Annotate each bar with its value
    x_max = max(max(means), 0.05) * 1.4
    for bar, sm, deltas, tier in zip(bars, means, deltas_list, tiers):
        ax.text(
            bar.get_width() + 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{sm:+.4f}",
            va="center",
            ha="left",
            color=PALETTE["ink"],
            fontsize=10,
            fontweight="bold",
        )
        if deltas:
            dmin, dmax = min(deltas), max(deltas)
            ax.text(
                bar.get_width() + 0.05,
                bar.get_y() + bar.get_height() / 2 - 0.16,
                f"range [{dmin:+.4f}, {dmax:+.4f}]",
                va="center",
                ha="left",
                color=PALETTE["text"],
                fontsize=8,
                style="italic",
            )

    # Reference line at y=0
    ax.axvline(0, color=PALETTE["ink"], linewidth=1.0, linestyle="-")
    # G.1 robust target line at +0.05 (from capability_audit)
    ax.axvline(
        0.05,
        color=PALETTE["target"],
        linewidth=2.0,
        linestyle="--",
        label="G.1 robust target = +0.05",
    )

    ax.set_xlim(-0.05, x_max + 0.05)
    ax.set_xlabel(
        "Signed Δ% per family = mean((framework - baseline) / |baseline|)",
        color=PALETTE["ink"],
        fontsize=10,
    )
    ax.set_title(
        "FlowA framework value surface by tier — Tier 1 toy + Tier 2 SOTA + Tier 3 2026 real-ckpt",
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

    # Tier color legend (manual swatches)
    from matplotlib.patches import Patch
    legend_patches = [
        Patch(facecolor=PALETTE["tier1"], edgecolor=PALETTE["ink"], label="Tier 1 toy (analytic / MNIST)"),
        Patch(facecolor=PALETTE["tier2"], edgecolor=PALETTE["ink"], label="Tier 2 SOTA image (CIFAR-10 RF)"),
        Patch(facecolor=PALETTE["tier3"], edgecolor=PALETTE["ink"], label="Tier 3 SOTA 2026 protein (Kanzi / LineageFlow)"),
    ]
    legend = ax.legend(
        handles=legend_patches + [
            plt.Line2D([0], [0], color=PALETTE["target"], linestyle="--", linewidth=2.0,
                       label="G.1 robust target = +0.05"),
        ],
        loc="lower right",
        fontsize=8,
        frameon=True,
        facecolor=PALETTE["background"],
        edgecolor=PALETTE["neutral"],
    )

    # Honest reading note (Tier 3 saturation explanation)
    note_text = (
        "Tier 3 honest reading: Kanzi real-ckpt eval (9 cells, adapter_mode=torch) hits the\n"
        "synthetic-mode saturation ceiling for protein_sequence_validity_rate (0.95).\n"
        "LineageFlow forward smoke passes (44.1M params, no NaN/Inf), but the real-ckpt\n"
        "eval-vs-baseline cell has not yet been wrapped; signed_mean = 0.0 by construction.\n"
        "See docs/audit/wave42-paper-writeup.md for the unblock plan."
    )
    ax.text(
        0.01,
        -0.40,
        note_text,
        transform=ax.transAxes,
        fontsize=8,
        color=PALETTE["text"],
        ha="left",
        va="top",
        family="monospace",
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=PALETTE["background"],
            edgecolor=PALETTE["neutral"],
            linewidth=0.5,
        ),
    )

    fig.subplots_adjust(bottom=0.40)

    out = os.path.join(OUT_DIR, "tier3_real_ckpt_signed_mean.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


if __name__ == "__main__":
    p = main()
    print(f"wrote {p}")
