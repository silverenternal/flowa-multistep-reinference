#!/usr/bin/env python3
"""Render the R5c matched-rung NFE frontier figure (Figure 1 of the manuscript).

ADDITIVE only -- no number is modified. Every plotted value is read from the
canonical frontier artifacts, never transcribed by hand:

    verification_outputs/gap84-mnist-frontier/frontier_input_<ckpt>_evidence_driven.json

Each file carries, per rung of {4, 5, 10, 25, 50, 100, 200}:
  * `baseline[rung]["value"]`  -- mean over the three seeds (42/43/44)
  * `baseline[rung]["units"]`  -- the per-seed values, used for the +/-1 sd band
  * `framework[rung]["value"]` / `["units"]` -- same, for the framework arm

The plateau is the mean of the last two rungs (100, 200), matching
`tools/frontier_report.py`. The script asserts the four plateau deltas against
the values printed in the manuscript, so a silent artifact drift fails loudly
instead of producing a figure that disagrees with the text.

Layout: 2x2 panels ordered by training completeness (5k, 10k, 60k, production).
Panels carry independent y-ranges because the absolute FID scale spans 24.5 to
10.0 across checkpoints; each panel is annotated with its own plateau delta so
the shrinking gain is read from the annotation rather than from a misleading
shared axis.

The renderer uses matplotlib's `Agg` backend (headless) and is byte-stable
under repeated invocation. It emits a double-column PNG to
`docs/figures/fig_r5c_frontier.png`.

Usage:
    python3 tools/render_r5c_frontier_figure.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedFormatter, FixedLocator, NullLocator

REPO = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO / "verification_outputs" / "gap84-mnist-frontier"
OUT = REPO / "docs" / "figures" / "fig_r5c_frontier.png"

# Checkpoint order = training completeness. Labels are the artifact names.
CHECKPOINTS = (
    ("w16e1_5k", "w16e1_5k (least trained)"),
    ("w16e1_10k", "w16e1_10k"),
    ("w16e1_60k", "w16e1_60k"),
    ("production", "production"),
)

# Manuscript values (paper-A-final.md Sec. 7.9 / Table III). Asserted below.
EXPECTED_PLATEAU_DELTA = {
    "w16e1_5k": -3.1206,
    "w16e1_10k": -1.0036,
    "w16e1_60k": +0.0150,
    "production": -0.0335,
}

BASELINE_COLOR = "#666666"
FRAMEWORK_COLOR = "#2166ac"
HIGHLIGHT_FACE = "#eaf2f8"


def load_checkpoint(ckpt: str) -> dict:
    path = ARTIFACT_DIR / f"frontier_input_{ckpt}_evidence_driven.json"
    with path.open() as handle:
        return json.load(handle)


def series(payload: dict, arm: str, rungs: list[int]) -> tuple[list[float], list[float]]:
    means = [float(payload[arm][str(r)]["value"]) for r in rungs]
    sds = [
        statistics.stdev([float(v) for v in payload[arm][str(r)]["units"]])
        for r in rungs
    ]
    return means, sds


def plateau(means: list[float]) -> float:
    return 0.5 * (means[-1] + means[-2])


def main() -> int:
    plt.rcParams.update(
        {
            "font.size": 8.0,
            "axes.linewidth": 0.6,
            "axes.edgecolor": "#333333",
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "legend.frameon": False,
            "figure.dpi": 300,
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.3))
    axes_flat = axes.ravel()

    for ax, (ckpt, label) in zip(axes_flat, CHECKPOINTS, strict=True):
        payload = load_checkpoint(ckpt)
        rungs = [int(r) for r in payload["grid"]]
        base_mean, base_sd = series(payload, "baseline", rungs)
        fw_mean, fw_sd = series(payload, "framework", rungs)

        delta = plateau(fw_mean) - plateau(base_mean)
        expected = EXPECTED_PLATEAU_DELTA[ckpt]
        if abs(delta - expected) > 5e-4:
            raise SystemExit(
                f"plateau drift for {ckpt}: artifact {delta:+.4f} vs manuscript {expected:+.4f}"
            )
        pct = 100.0 * delta / plateau(base_mean)

        # +/-1 sd band across the three seeds.
        base_lo = [m - s for m, s in zip(base_mean, base_sd, strict=True)]
        base_hi = [m + s for m, s in zip(base_mean, base_sd, strict=True)]
        fw_lo = [m - s for m, s in zip(fw_mean, fw_sd, strict=True)]
        fw_hi = [m + s for m, s in zip(fw_mean, fw_sd, strict=True)]

        ax.fill_between(rungs, base_lo, base_hi, color=BASELINE_COLOR, alpha=0.16, linewidth=0)
        ax.fill_between(rungs, fw_lo, fw_hi, color=FRAMEWORK_COLOR, alpha=0.18, linewidth=0)
        ax.plot(
            rungs,
            base_mean,
            color=BASELINE_COLOR,
            linewidth=1.1,
            linestyle="--",
            marker="o",
            markersize=3.0,
            label="one-shot baseline",
        )
        ax.plot(
            rungs,
            fw_mean,
            color=FRAMEWORK_COLOR,
            linewidth=1.3,
            marker="s",
            markersize=3.0,
            label="re-inference",
        )

        ax.set_xscale("log", base=2)
        ax.set_xticks(rungs)
        ax.xaxis.set_major_formatter(FixedFormatter([str(r) for r in rungs]))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlabel("NFE per sample (matched budget)", labelpad=2)
        ax.set_ylabel("FID", labelpad=2)
        ax.grid(True, which="major", color="#dddddd", linewidth=0.5)
        ax.set_axisbelow(True)

        strong = ckpt == "w16e1_5k"
        if strong:
            ax.set_facecolor(HIGHLIGHT_FACE)
        # Small deltas keep a third decimal so "+0.015" does not print as "+0.01".
        decimals = 3 if abs(delta) < 0.1 else 2
        title = f"{label}\nplateau {delta:+.{decimals}f} FID ({pct:+.2f}%)"
        ax.set_title(title, fontsize=7.6, fontweight="bold" if strong else "normal", pad=3)

        # Headroom for the +/-1 sd band; the low-NFE point can sit well above the
        # plateau on well-trained checkpoints, so the range must cover it.
        low = min(min(base_lo), min(fw_lo))
        high = max(max(base_hi), max(fw_hi))
        span = high - low
        ax.set_ylim(low - 0.10 * span, high + 0.10 * span)

        # Shade the plateau window (last two rungs).
        ax.axvspan(rungs[-2], rungs[-1], color="#000000", alpha=0.05, linewidth=0)

    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=2,
        bbox_to_anchor=(0.5, 0.995),
        handlelength=2.4,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
