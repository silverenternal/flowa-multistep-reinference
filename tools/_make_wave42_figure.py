"""Wave 42 + Wave 44 + Wave 52 paper-writeup figure — Tier 3 (Kanzi ICLR 2026 + LineageFlow ICML 2026 + FlowMol3 NeurIPS 2024) real-ckpt
framework advantage shown alongside Tier 1 (toy FM) + Tier 2 (SOTA image RF) values.

Wave 52 Agent A update: now reads 3 Tier 3 JSONs (Kanzi, LineageFlow, FlowMol3)
and renders **two readings per Tier 3 model** (decision-metric axis +
composite axis). The Tier 3 bars are paired: decision-metric (light orange)
and composite-axis (dark orange, when available).

Renders a horizontal bar chart of per-family signed_mean for the 7 integrated model rows
(colored by tier: Tier 1 toy = blue, Tier 2 SOTA image = green, Tier 3 SOTA 2026 = orange),
with a reference line at y=0.

Inputs:
  - verification_outputs/capability_audit_q4_2026.json (G.1 evidence for Tier 1 + Tier 2 rows)
  - verification_outputs/kanzi_real_metric_v2_q4_2026.json (Tier 3 Kanzi decision-metric axis, Wave 44 Agent C)
  - verification_outputs/lineageflow_real_metric_v2_q4_2026.json (Tier 3 LineageFlow decision-metric axis, Wave 44 Agent C)
  - verification_outputs/flowmol3_real_composite_q4_2026.json (Tier 3 FlowMol3 composite axis, Wave 50 Agent B)

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
# Wave 44 Agent C JSONs (real metric, real-ckpt forward path):
KANZI_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "verification_outputs",
    "kanzi_real_metric_v2_q4_2026.json",
)
LINEAGEFLOW_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "verification_outputs",
    "lineageflow_real_metric_v2_q4_2026.json",
)
# Wave 50 Agent B JSON (FlowMol3 real-ckpt composite eval):
FLOWMOL3_JSON = os.path.join(
    os.path.dirname(__file__),
    "..",
    "verification_outputs",
    "flowmol3_real_composite_q4_2026.json",
)
# Wave 47 Agent A LineageFlow composite (from /tmp/q4_w47.json smoke test, gitignored):
# Per-cell composite = 0.210937 from Wave 47 Agent A. We hard-code this single
# number for the LineageFlow composite-axis bar; the 9-cell re-sweep is Wave 52
# Agent C (in flight) and will land in verification_outputs/lineageflow_composite_q4_2026.json.
LINEAGEFLOW_COMPOSITE_SINGLE_CELL = 0.210937


def _signed_mean_from_cells(cells: list[dict]) -> float:
    """Return mean signed_delta_pct across cells (0.0 if no cells or all-None)."""
    if not cells:
        return 0.0
    deltas = []
    for c in cells:
        sdp = c.get("signed_delta_pct")
        if sdp is None:
            # RUN_ERROR / BLOCKED cell: skip (do NOT count it as 0).
            continue
        deltas.append(float(sdp))
    if not deltas:
        return 0.0
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


def _aggregate_tier3_kanzi(kanzi: dict) -> tuple[float, list[float], int, int]:
    """Tier 3 Kanzi real-ckpt eval cells (Wave 44 Agent C: 9 = 3 seeds x 3 NFE).

    Returns (signed_mean, [deltas], n_real_computed, n_run_error)."""
    cells = kanzi.get("cells", [])
    agg = kanzi.get("aggregate", {})
    deltas = []
    for c in cells:
        sdp = c.get("signed_delta_pct")
        if sdp is None:
            continue
        deltas.append(float(sdp))
    sm = sum(deltas) / len(deltas) if deltas else 0.0
    n_real = int(agg.get("n_real_computed", 0))
    n_run = int(agg.get("n_run_error", 0))
    return sm, deltas, n_real, n_run


def _aggregate_tier3_lineageflow(lf: dict) -> tuple[float, list[float], int, int]:
    """Tier 3 LineageFlow real-ckpt eval cells (Wave 44 Agent C: 1 RUN_ERROR).

    The single cell is RUN_ERROR (EsmModel dtype bug in
    LineageFlowAdapter._torch_velocity_field), so signed_delta_pct is None.
    We surface 0.0 as the honest reading (no computable cells)."""
    cells = lf.get("cells", [])
    agg = lf.get("aggregate", {})
    deltas = []
    for c in cells:
        sdp = c.get("signed_delta_pct")
        if sdp is None:
            continue
        deltas.append(float(sdp))
    sm = sum(deltas) / len(deltas) if deltas else 0.0
    n_real = int(agg.get("n_real_computed", 0))
    n_run = int(agg.get("n_run_error", 0))
    return sm, deltas, n_real, n_run


def _aggregate_tier3_flowmol3_composite(fm3: dict) -> tuple[float, list[float], int, int]:
    """Tier 3 FlowMol3 composite-axis (Wave 50 Agent B).

    The Wave 50 sweep runs FlowMol3Glue end-to-end on all 9 cells, but
    every phi term is 0.0 (metric layer blocked). composite_median = 0.0,
    composite_verdict = "no_signal". We surface 0.0 as the honest reading.
    """
    cells = fm3.get("cells", [])
    agg = fm3.get("aggregate", {})
    composites = []
    for c in cells:
        comp = c.get("composite")
        if comp is None:
            continue
        composites.append(float(comp))
    sm = sum(composites) / len(composites) if composites else 0.0
    n_composite = int(agg.get("n_composite_computed", 0))
    n_blocked = int(agg.get("n_pending", 0))
    return sm, composites, n_composite, n_blocked


def main() -> str:
    with open(AUDIT_JSON, "r", encoding="utf-8") as f:
        audit = json.load(f)
    with open(KANZI_JSON, "r", encoding="utf-8") as f:
        kanzi = json.load(f)
    with open(LINEAGEFLOW_JSON, "r", encoding="utf-8") as f:
        lf = json.load(f)
    # FlowMol3 may not exist (e.g. fresh checkout); treat as missing data
    fm3 = None
    if os.path.exists(FLOWMOL3_JSON):
        try:
            with open(FLOWMOL3_JSON, "r", encoding="utf-8") as f:
                fm3 = json.load(f)
        except (json.JSONDecodeError, OSError):
            fm3 = None

    tier1_tier2 = _aggregate_tier1_tier2(audit)
    tier3_kanzi_sm, tier3_kanzi_deltas, k_n_real, k_n_run = _aggregate_tier3_kanzi(kanzi)
    tier3_lf_sm, tier3_lf_deltas, l_n_real, l_n_run = _aggregate_tier3_lineageflow(lf)
    if fm3 is not None:
        tier3_fm3_sm, tier3_fm3_comps, fm3_n_comp, fm3_n_blocked = _aggregate_tier3_flowmol3_composite(fm3)
    else:
        tier3_fm3_sm, tier3_fm3_comps, fm3_n_comp, fm3_n_blocked = 0.0, [], 0, 9

    # Order: x-axis ascending (Tier 1 toy -> Tier 2 -> Tier 3 decision -> Tier 3 composite).
    # Brief says X-axis is model families; Y-axis is signed_mean.
    # Tier classification:
    #   Tier 1 toy: twodim_fm (2D analytic + Wang 2022 NFE), mnist_fm (Wave 26/28 toy)
    #   Tier 2: rectified_flow_cifar (Wave 4-7 v3 image RF SOTA comparison)
    #   Tier 3: kanzi (ICLR 2026 protein), lineageflow (ICML 2026 protein), flowmol3 (NeurIPS 2024 mol)
    # Each Tier 3 model gets TWO bars: decision-metric axis (light tier3) and
    # composite axis (dark tier3, when available).
    family_data: list[tuple[str, int, float, list[float], str]] = [
        # (label, n_rows, signed_mean, deltas, tier)
        ("twodim_fm\n(Tier 1 toy)", tier1_tier2["twodim_fm"][1].__len__(),
         tier1_tier2["twodim_fm"][0], tier1_tier2["twodim_fm"][1], "tier1"),
        ("mnist_fm\n(Tier 1 toy)", tier1_tier2["mnist_fm"][1].__len__(),
         tier1_tier2["mnist_fm"][0], tier1_tier2["mnist_fm"][1], "tier1"),
        ("rectified_flow_cifar\n(Tier 2 SOTA image)", tier1_tier2["rectified_flow_cifar"][1].__len__(),
         tier1_tier2["rectified_flow_cifar"][0], tier1_tier2["rectified_flow_cifar"][1], "tier2"),
        # Tier 3 decision-metric axis (light tier3)
        ("kanzi\n(Tier 3 ICLR 2026, decision-metric)",
         len(tier3_kanzi_deltas), tier3_kanzi_sm, tier3_kanzi_deltas, "tier3"),
        ("lineageflow\n(Tier 3 ICML 2026, decision-metric)",
         len(tier3_lf_deltas), tier3_lf_sm, tier3_lf_deltas, "tier3"),
        ("flowmol3\n(Tier 3 NeurIPS 2024, decision-metric)",
         0, 0.0, [], "tier3"),
        # Tier 3 composite axis (dark tier3)
        ("kanzi\n(Tier 3 ICLR 2026, composite-axis, in flight)",
         0, 0.0, [], "tier3_composite"),
        ("lineageflow\n(Tier 3 ICML 2026, composite-axis, +0.211)",
         1, LINEAGEFLOW_COMPOSITE_SINGLE_CELL, [LINEAGEFLOW_COMPOSITE_SINGLE_CELL], "tier3_composite"),
        ("flowmol3\n(Tier 3 NeurIPS 2024, composite-axis, no_signal)",
         len(tier3_fm3_comps), tier3_fm3_sm, tier3_fm3_comps, "tier3_composite"),
    ]

    labels = [f[0] for f in family_data]
    means = [f[2] for f in family_data]
    deltas_list = [f[3] for f in family_data]
    tiers = [f[4] for f in family_data]
    # Tier 3 composite-axis uses a darker shade of orange to distinguish
    # from the decision-metric axis (light orange).
    bar_colors = []
    for t in tiers:
        if t == "tier3_composite":
            bar_colors.append("#B85C00")  # darker orange (composite axis)
        else:
            bar_colors.append(PALETTE[t])

    fig, ax = plt.subplots(figsize=(13, 7.0))

    bars = ax.barh(
        labels,
        means,
        color=bar_colors,
        edgecolor=PALETTE["ink"],
        linewidth=0.7,
        height=0.55,
    )

    # Annotate each bar with its value
    x_max = max(max(means), 0.05, LINEAGEFLOW_COMPOSITE_SINGLE_CELL) * 1.4
    for bar, sm, deltas, tier in zip(bars, means, deltas_list, tiers):
        ax.text(
            bar.get_width() + 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{sm:+.4f}",
            va="center",
            ha="left",
            color=PALETTE["ink"],
            fontsize=9,
            fontweight="bold",
        )
        if deltas:
            dmin, dmax = min(deltas), max(deltas)
            ax.text(
                bar.get_width() + 0.05,
                bar.get_y() + bar.get_height() / 2 - 0.14,
                f"range [{dmin:+.4f}, {dmax:+.4f}]",
                va="center",
                ha="left",
                color=PALETTE["text"],
                fontsize=7,
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
        "Signed Δ% per family = mean((framework - baseline) / |baseline|)  [Tier 3 also shows composite ∈ [-1, +1]]",
        color=PALETTE["ink"],
        fontsize=9,
    )
    ax.set_title(
        "FlowA framework value surface by tier — Tier 1 toy + Tier 2 SOTA + Tier 3 2026 real-ckpt (decision-metric + composite axes)",
        color=PALETTE["ink"],
        fontsize=11,
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
        Patch(facecolor=PALETTE["tier3"], edgecolor=PALETTE["ink"], label="Tier 3 SOTA 2026 (decision-metric axis, light orange)"),
        Patch(facecolor="#B85C00", edgecolor=PALETTE["ink"], label="Tier 3 SOTA 2026 (composite axis, dark orange)"),
    ]
    legend = ax.legend(
        handles=legend_patches + [
            plt.Line2D([0], [0], color=PALETTE["target"], linestyle="--", linewidth=2.0,
                       label="G.1 robust target = +0.05"),
        ],
        loc="lower right",
        fontsize=7,
        frameon=True,
        facecolor=PALETTE["background"],
        edgecolor=PALETTE["neutral"],
    )

    # Honest reading note (Wave 52 Agent A: dual-axis Tier 3 reading)
    note_text = (
        "Tier 3 honest reading (Wave 52 Agent A — dual-axis):\n"
        "  decision-metric axis (light orange): Kanzi 9/9 cells TIE_AT_SATURATION (real metric,\n"
        "    n_real_computed=9, ceiling=1.0); LineageFlow 1/1 cell RUN_ERROR (pre-Wave 47 F-4 fix);\n"
        "    FlowMol3 metric layer missing.\n"
        "  composite axis (dark orange, formula: 0.40*phi1 + 0.35*phi2 + 0.25*phi3 ∈ [-1,+1]):\n"
        f"    Kanzi (in flight, Wave 52 Agent A); LineageFlow +{LINEAGEFLOW_COMPOSITE_SINGLE_CELL:.4f}\n"
        "    (Wave 47 Agent A smoke test: phi3_argmax_turnover=+0.844 across 33 ESM-2 token slots\n"
        "    via LineageFlowClassifierAwareRestart, composite_verdict=framework_improves);\n"
        "    FlowMol3 +0.0000 (Wave 50 Agent B no_signal — FlowMol3Glue ran end-to-end but\n"
        "    metric layer returns None on every cell).\n"
        "  See docs/audit/wave52-paper-tier3-rewrite.md + CONSOLIDATED_RESULTS §16\n"
        "  + docs/audit/wave47-eval-pipeline-integration.md for the full accounting."
    )
    ax.text(
        0.01,
        -0.45,
        note_text,
        transform=ax.transAxes,
        fontsize=7,
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