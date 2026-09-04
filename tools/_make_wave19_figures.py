"""Generate Wave 19 paper figures (SVG) for the 5-section paper.

Outputs:
  docs/figures/fig5-architecture.svg  - 4-layer framework architecture
  docs/figures/fig6-ablation.svg      - W2 ablation across schedulers
  docs/figures/fig7-conditions.svg    - when framework helps vs doesn't

No matplotlib required: SVG is plain XML and renders cleanly in
mkdocs and most PDF backends.
"""
from __future__ import annotations

import os
import textwrap

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# Brand-neutral palette (matches tools/_make_figures.py)
PALETTE = {
    "ink": "#222831",
    "frame": "#00ADB5",
    "adapter": "#393E46",
    "engine": "#EEEEEE",
    "highlight": "#FFD460",
    "warning": "#E76F51",
    "good": "#0077B6",
    "neutral": "#888888",
    "loops": "#7B2CBF",
    "background": "#FAFAFA",
    "border": "#393E46",
}


def fig5_architecture() -> str:
    """4-layer framework architecture diagram."""
    layers = [
        ("L4", "Adapter Protocol",
         "TwoDimFM · RectifiedFlowCIFAR · LineageFlow\nFlowMol3 · StochasticFM · MnistFM · ToyGaussian",
         PALETTE["adapter"], "#f8f8f8"),
        ("L3", "Algorithm Layer",
         "17 typed state machines · 333 typed transitions\n3 paper-grounded schedulers · 5 derivation rules · DERIV-001",
         PALETTE["frame"], "#e7fafc"),
        ("L2", "Engine + Runner Orchestration",
         "ReInferenceRunner · Ledger (SHA-256 chain)\nHash-chained integrity · Byte-deterministic transition log",
         PALETTE["highlight"], "#fff8e1"),
        ("L1", "Contracts + Metrics",
         "Typed dataclasses · InceptionV3 FID · W2 · selection_ratio\nTheoremAlignedFID · PosteriorSelectionEvaluator",
         PALETTE["loops"], "#f3eafa"),
    ]
    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 640" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="800" height="640" fill="{PALETTE["background"]}"/>',
        f'<text x="400" y="32" text-anchor="middle" font-size="20" font-weight="bold" fill="{PALETTE["ink"]}">FlowA: 4-Layer Architecture</text>',
        f'<text x="400" y="56" text-anchor="middle" font-size="12" fill="{PALETTE["ink"]}">User-supplied pre-trained model plugs into Layer 4; Layers 1-3 are model-agnostic</text>',
    ]
    # Render 4 horizontal layers top to bottom (L4 at top, L1 at bottom)
    y_top = 80
    layer_h = 110
    gap = 14
    for i, (tag, name, sub, color, fill) in enumerate(layers):
        y = y_top + i * (layer_h + gap)
        svg.append(
            f'<rect x="60" y="{y}" width="680" height="{layer_h}" rx="8" ry="8" '
            f'fill="{fill}" stroke="{color}" stroke-width="2.5"/>'
        )
        svg.append(
            f'<rect x="60" y="{y}" width="56" height="{layer_h}" rx="8" ry="8" '
            f'fill="{color}" stroke="{color}" stroke-width="2.5"/>'
        )
        svg.append(
            f'<text x="88" y="{y + layer_h / 2 + 6}" text-anchor="middle" '
            f'font-size="22" font-weight="bold" fill="white">{tag}</text>'
        )
        svg.append(
            f'<text x="138" y="{y + 38}" font-size="16" font-weight="bold" fill="{PALETTE["ink"]}">{name}</text>'
        )
        for j, line in enumerate(sub.split("\n")):
            svg.append(
                f'<text x="138" y="{y + 64 + j * 18}" font-size="11" fill="{PALETTE["ink"]}">{line}</text>'
            )
    # Layer connectors (down arrows)
    for i in range(3):
        y_arrow = y_top + (i + 1) * (layer_h + gap) - gap + 1
        svg.append(
            f'<line x1="400" y1="{y_arrow}" x2="400" y2="{y_arrow + gap - 2}" '
            f'stroke="{PALETTE["ink"]}" stroke-width="2" marker-end="url(#arrow)"/>'
        )
    svg.append(
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">'
        f'<path d="M0,0 L8,4 L0,8 z" fill="{PALETTE["ink"]}"/></marker></defs>'
    )
    # Side annotations
    svg.append(
        f'<text x="20" y="135" font-size="11" font-weight="bold" fill="{PALETTE["adapter"]}">plug-in</text>'
    )
    svg.append(
        f'<text x="20" y="259" font-size="11" font-weight="bold" fill="{PALETTE["frame"]}">paper math</text>'
    )
    svg.append(
        f'<text x="20" y="383" font-size="11" font-weight="bold" fill="{PALETTE["highlight"]}">control flow</text>'
    )
    svg.append(
        f'<text x="20" y="507" font-size="11" font-weight="bold" fill="{PALETTE["loops"]}">metrics</text>'
    )
    svg.append('</svg>')
    out = os.path.join(OUT_DIR, "fig5-architecture.svg")
    with open(out, "w") as f:
        f.write("\n".join(svg))
    return out


def fig6_ablation() -> str:
    """W2 ablation across schedulers - both 2D targets."""
    # Data from docs/CONSOLIDATED_RESULTS.md §4.1-4.2
    two_moons = [
        ("single_pass", 2.8519, PALETTE["neutral"]),
        ("multi_round\ncosine", 0.8691, PALETTE["good"]),
        ("multi_round\ncodim_sheet", 0.8691, PALETTE["frame"]),
        ("multi_round\nevidence_driven", 0.8868, PALETTE["loops"]),
        ("multi_round\nno_restart", 0.6244, PALETTE["highlight"]),
    ]
    eight_gauss = [
        ("single_pass", 2.3095, PALETTE["neutral"]),
        ("multi_round\ncosine", 2.0437, PALETTE["good"]),
        ("multi_round\ncodim_sheet", 2.0437, PALETTE["frame"]),
        ("multi_round\nevidence_driven", 2.0437, PALETTE["loops"]),
        ("multi_round\nno_restart", 0.7591, PALETTE["highlight"]),
    ]
    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 520" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="900" height="520" fill="{PALETTE["background"]}"/>',
        f'<text x="450" y="32" text-anchor="middle" font-size="20" font-weight="bold" fill="{PALETTE["ink"]}">2D Rectified Flow Ablation — Final W₂ by Scheduler</text>',
        f'<text x="450" y="56" text-anchor="middle" font-size="12" fill="{PALETTE["ink"]}">Same checkpoint, same evaluator; only the inference strategy varies. Lower is better.</text>',
    ]
    # Two side-by-side panels
    for panel_idx, (title, data, x0) in enumerate([
        ("two_moons", two_moons, 60),
        ("eight_gaussians", eight_gauss, 490),
    ]):
        x_panel = x0
        y_panel = 90
        panel_w = 360
        panel_h = 380
        svg.append(
            f'<rect x="{x_panel}" y="{y_panel}" width="{panel_w}" height="{panel_h}" '
            f'fill="white" stroke="{PALETTE["ink"]}" stroke-width="1.5"/>'
        )
        svg.append(
            f'<text x="{x_panel + panel_w / 2}" y="{y_panel + 22}" text-anchor="middle" '
            f'font-size="14" font-weight="bold" fill="{PALETTE["ink"]}">{title}</text>'
        )
        # Y axis
        max_y = 3.0
        y_axis_x = x_panel + 80
        y_axis_top = y_panel + 50
        y_axis_bot = y_panel + panel_h - 50
        svg.append(
            f'<line x1="{y_axis_x}" y1="{y_axis_top}" x2="{y_axis_x}" y2="{y_axis_bot}" '
            f'stroke="{PALETTE["ink"]}" stroke-width="1"/>'
        )
        # Bars
        bar_w = 36
        for i, (label, val, color) in enumerate(data):
            bar_h = (val / max_y) * (y_axis_bot - y_axis_top)
            bx = y_axis_x + 30 + i * 50
            by = y_axis_bot - bar_h
            svg.append(
                f'<rect x="{bx}" y="{by}" width="{bar_w}" height="{bar_h}" '
                f'fill="{color}" stroke="{color}" stroke-width="1"/>'
            )
            svg.append(
                f'<text x="{bx + bar_w / 2}" y="{by - 6}" text-anchor="middle" '
                f'font-size="11" font-weight="bold" fill="{PALETTE["ink"]}">{val:.2f}</text>'
            )
            # Label below x axis
            for j, line in enumerate(label.split("\n")):
                svg.append(
                    f'<text x="{bx + bar_w / 2}" y="{y_axis_bot + 14 + j * 11}" '
                    f'text-anchor="middle" font-size="9" fill="{PALETTE["ink"]}">{line}</text>'
                )
        # Y ticks
        for tick in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
            ty = y_axis_bot - (tick / max_y) * (y_axis_bot - y_axis_top)
            svg.append(
                f'<line x1="{y_axis_x - 4}" y1="{ty}" x2="{y_axis_x}" y2="{ty}" '
                f'stroke="{PALETTE["ink"]}" stroke-width="1"/>'
            )
            svg.append(
                f'<text x="{y_axis_x - 8}" y="{ty + 4}" text-anchor="end" '
                f'font-size="10" fill="{PALETTE["ink"]}">{tick:.1f}</text>'
            )
        # Y label
        svg.append(
            f'<text x="{x_panel + 20}" y="{y_panel + panel_h / 2}" '
            f'text-anchor="middle" font-size="11" font-weight="bold" fill="{PALETTE["ink"]}" '
            f'transform="rotate(-90 {x_panel + 20} {y_panel + panel_h / 2})">Final W₂</text>'
        )
    # Legend
    legend_x = 60
    legend_y = 490
    legend_items = [
        ("single_pass baseline", PALETTE["neutral"]),
        ("CosineAnnealScheduler", PALETTE["good"]),
        ("CodimensionSheetScheduler", PALETTE["frame"]),
        ("EvidenceDrivenScheduler", PALETTE["loops"]),
        ("multi_round_no_restart", PALETTE["highlight"]),
    ]
    for i, (label, color) in enumerate(legend_items):
        lx = legend_x + i * 160
        svg.append(
            f'<rect x="{lx}" y="{legend_y - 10}" width="14" height="14" fill="{color}" stroke="{color}"/>'
        )
        svg.append(
            f'<text x="{lx + 20}" y="{legend_y}" font-size="10" fill="{PALETTE["ink"]}">{label}</text>'
        )
    svg.append('</svg>')
    out = os.path.join(OUT_DIR, "fig6-ablation.svg")
    with open(out, "w") as f:
        f.write("\n".join(svg))
    return out


def fig7_conditions() -> str:
    """When does the framework help, and when does it not?"""
    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 540" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="900" height="540" fill="{PALETTE["background"]}"/>',
        f'<text x="450" y="32" text-anchor="middle" font-size="20" font-weight="bold" fill="{PALETTE["ink"]}">FlowA Framework — Conditions for Value-Add</text>',
        f'<text x="450" y="56" text-anchor="middle" font-size="12" fill="{PALETTE["ink"]}">Three measured outcomes on three published flow-matching models</text>',
    ]
    # 3 cards: helps / neutral / hurts
    cards = [
        {
            "x": 60, "color": PALETTE["good"], "fill": "#e7f3fb",
            "header": "HELPS",
            "model": "2D Rectified Flow\n(Liu 2022)",
            "metric": "W₂",
            "result": "−7.28% (two_moons)\n−10.40% (eight_gauss)",
            "condition": "Chained state carries\ninformation across rounds;\nthe ramp is productive.",
            "evidence": "3 seeds, 1965.9 s CPU",
        },
        {
            "x": 320, "color": PALETTE["neutral"], "fill": "#f5f5f5",
            "header": "NEUTRAL (at saturation)",
            "model": "LineageFlow\n(ICML 2026, protein)",
            "metric": "family_validity",
            "result": "1.0000 → 1.0000 (ties)\n+0.23% log-lik; +0.09% div",
            "condition": "Decision metric saturated\nfor both arms; only secondary\nmetrics differentiate.",
            "evidence": "32 samples, 131.24 s CPU",
        },
        {
            "x": 580, "color": PALETTE["warning"], "fill": "#fbeae5",
            "header": "HURTS (matched-NFE)",
            "model": "CIFAR-10 Rectified Flow\n(Liu 2022, 61.8 M params)",
            "metric": "FID",
            "result": "Baseline 83.09\nFramework 103.4–108.6\n(+24 to +31%)",
            "condition": "Harness discards per-round\nstate; cosine ramp degenerates\ninto noise-pool aggregator.",
            "evidence": "500 samples, 2643 s CPU",
        },
    ]
    for c in cards:
        x = c["x"]
        y = 90
        w = 260
        h = 420
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" ry="10" '
            f'fill="{c["fill"]}" stroke="{c["color"]}" stroke-width="2.5"/>'
        )
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="36" rx="10" ry="10" '
            f'fill="{c["color"]}"/>'
        )
        svg.append(
            f'<text x="{x + w / 2}" y="{y + 24}" text-anchor="middle" '
            f'font-size="14" font-weight="bold" fill="white">{c["header"]}</text>'
        )
        # Body
        lines = [
            ("Model:", c["model"]),
            ("Metric:", c["metric"]),
            ("Result:", c["result"]),
            ("Condition:", c["condition"]),
            ("Evidence:", c["evidence"]),
        ]
        ty = y + 70
        for label, val in lines:
            svg.append(
                f'<text x="{x + 16}" y="{ty}" font-size="11" font-weight="bold" fill="{PALETTE["ink"]}">{label}</text>'
            )
            for j, line in enumerate(val.split("\n")):
                svg.append(
                    f'<text x="{x + 16}" y="{ty + 14 + j * 13}" font-size="11" fill="{PALETTE["ink"]}">{line}</text>'
                )
            ty += 16 + 13 * (len(val.split("\n")) + 1) + 6
    # Bottom annotation
    svg.append(
        f'<text x="450" y="525" text-anchor="middle" font-size="11" font-style="italic" '
        f'fill="{PALETTE["ink"]}">Honest framing: framework provides selectable, auditable inference behaviour with a theory-grounded knob — not a universal win.</text>'
    )
    svg.append('</svg>')
    out = os.path.join(OUT_DIR, "fig7-conditions.svg")
    with open(out, "w") as f:
        f.write("\n".join(svg))
    return out


def main() -> None:
    out1 = fig5_architecture()
    out2 = fig6_ablation()
    out3 = fig7_conditions()
    print(f"Wrote {out1}")
    print(f"Wrote {out2}")
    print(f"Wrote {out3}")


if __name__ == "__main__":
    main()
