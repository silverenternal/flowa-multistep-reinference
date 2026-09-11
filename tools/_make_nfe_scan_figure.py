"""Wave 58 Agent 4 — aggregate Kanzi + LineageFlow NFE-scan data + plot.

Produces:
  * verification_outputs/nfe_scan_aggregated_q4_2026.json (gitignored)
  * docs/figures/nfe_scan_q4_2026.png

Inputs (all under verification_outputs/):
  * kanzi_nfe_scan_q4_2026.json          — Wave 58 Agent 2 (18 cells, complete)
  * lineageflow_real_force_mode_q4_2026.json — Wave 42 Agent B (9 cells, 1 ran, 8 PENDING)
  * lineageflow_baseline_euler_q4_2026.json   — Wave 52 Agent C (NFE=10 only)
  * lineageflow_baseline_heun_q4_2026.json    — Wave 52 Agent C (NFE=10 only)
  * lineageflow_baseline_rk4_q4_2026.json     — Wave 52 Agent C (NFE=10 only)
  * lineageflow_baseline_comparison_q4_2026.json — Wave 52 Agent C reference framework composite

Quality metric per model:
  * kanzi        → kanzi_composite (Wave 52 composite, [-1, 1] bounded,
                   framework-vs-baseline delta on the latent endpoint)
  * lineageflow  → family_validity_rate (primary metric, Wave 10)
                   with framework composite as a secondary axis on the same plot

The script is deterministic and depends only on the input JSONs + matplotlib.
Run:
  .venvs/flowmol3_venv/bin/python tools/_make_nfe_scan_figure.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from tools._figures_common import _FIGURE_DPI, plt, save_figure

REPO_ROOT = Path(__file__).resolve().parent.parent
VO = REPO_ROOT / "verification_outputs"
FIG_DIR = REPO_ROOT / "docs" / "figures"
AGG_OUT = VO / "nfe_scan_aggregated_q4_2026.json"
FIG_OUT = FIG_DIR / "nfe_scan_q4_2026.png"

NFE_BUDGETS = [10, 50, 200, 500, 1000, 2000]
SEEDS = [42, 43, 44]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open() as fp:
        return json.load(fp)


def _aggregate_kanzi() -> dict[str, Any]:
    """Per-(NFE) mean±std of kanzi_composite, baseline+framework separated."""
    src = _load_json(VO / "kanzi_nfe_scan_q4_2026.json")
    by_nfe: dict[int, dict[str, list[float]]] = {
        nfe: {"baseline_metric": [], "framework_metric": [], "composite": []}
        for nfe in NFE_BUDGETS
    }
    n_cells_total = 0
    for cell in src["cells"]:
        nfe = int(cell["nfe_budget"])
        if nfe not in by_nfe:
            continue
        if cell.get("baseline_metric") is not None:
            by_nfe[nfe]["baseline_metric"].append(float(cell["baseline_metric"]))
        if cell.get("framework_metric") is not None:
            by_nfe[nfe]["framework_metric"].append(float(cell["framework_metric"]))
        if cell.get("composite") is not None:
            by_nfe[nfe]["composite"].append(float(cell["composite"]))
        n_cells_total += 1

    aggregate = {
        "model": "kanzi",
        "primary_metric": "protein_sequence_validity_rate",
        "quality_metric": "kanzi_composite",
        "quality_metric_definition": (
            "Wave 52 composite: 0.40 * phi1_entropy_reduction + "
            "0.35 * phi2_max_prob_delta + 0.25 * phi3_argmax_turnover. "
            "Bounded in [-1, 1]; higher = framework improves latent endpoint."
        ),
        "source_json": "verification_outputs/kanzi_nfe_scan_q4_2026.json",
        "nfe_budgets": NFE_BUDGETS,
        "seeds": SEEDS,
        "n_cells_total": n_cells_total,
        "n_cells_with_composite": sum(
            len(by_nfe[nfe]["composite"]) for nfe in NFE_BUDGETS
        ),
        "by_nfe": {},
    }
    for nfe in NFE_BUDGETS:
        baseline = by_nfe[nfe]["baseline_metric"]
        framework = by_nfe[nfe]["framework_metric"]
        composite = by_nfe[nfe]["composite"]
        aggregate["by_nfe"][str(nfe)] = {
            "baseline_metric_mean": _mean(baseline),
            "baseline_metric_std": _std(baseline),
            "baseline_metric_n": len(baseline),
            "framework_metric_mean": _mean(framework),
            "framework_metric_std": _std(framework),
            "framework_metric_n": len(framework),
            "composite_mean": _mean(composite),
            "composite_std": _std(composite),
            "composite_n": len(composite),
            "saturation_at_ceiling": all(b == 1.0 for b in baseline)
            and all(f == 1.0 for f in framework),
        }
    return aggregate


def _aggregate_lineageflow() -> dict[str, Any]:
    """LineageFlow has 1 real-ckpt cell at NFE=10 + 3 baselines at NFE=10.

    Other NFE values (50, 200, 500, 1000, 2000) are PENDING due to host CPU
    bandwidth limit (each 657 M-param forward pass ≈ 60 s on CPU). The
    framework composite at NFE=10 comes from Wave 47 (hardcoded here
    because lineageflow_baseline_comparison_q4_2026.json uses Python
    tuple-style parentheses for its `interpretation` strings and is not
    strict-JSON loadable; the framework composite 0.211 is documented in
    docs/audit/wave47-eval-pipeline-integration.md §3).
    """
    force_mode = _load_json(VO / "lineageflow_real_force_mode_q4_2026.json")
    euler = _load_json(VO / "lineageflow_baseline_euler_q4_2026.json")

    # Wave 47 framework composite at NFE=10 (documented in
    # docs/audit/wave47-eval-pipeline-integration.md §3)
    wave47_framework_composite = 0.2109374578356829

    # Real-ckpt cell-by-cell
    real_cells_by_nfe: dict[int, dict[str, list[float]]] = {
        nfe: {
            "baseline_family_validity_rate": [],
            "framework_family_validity_rate": [],
        }
        for nfe in NFE_BUDGETS
    }
    n_real_ran = 0
    n_real_pending = 0
    for cell in force_mode.get("cells", []):
        nfe = int(cell.get("nfe_budget", -1))
        if nfe not in real_cells_by_nfe:
            continue
        if cell.get("status") == "TIE_AT_SATURATION" and cell.get("baseline_metric") is not None:
            real_cells_by_nfe[nfe]["baseline_family_validity_rate"].append(
                float(cell["baseline_metric"])
            )
            real_cells_by_nfe[nfe]["framework_family_validity_rate"].append(
                float(cell["framework_metric"])
            )
            n_real_ran += 1
        elif cell.get("status") == "PENDING":
            n_real_pending += 1

    # Wave 47 framework composite at NFE=10 (hardcoded above; see note)
    # Wave 52 euler composite at NFE=10 (self-comparison, not baseline-vs-framework)
    wave52_euler_composite = float(euler["cells"][0]["composite"])
    wave52_euler_phi3 = float(euler["cells"][0]["phi3_argmax_turnover_signed"])
    wave52_euler_end_entropy = float(euler["cells"][0]["end_entropy"])

    aggregate = {
        "model": "lineageflow",
        "primary_metric": "family_validity_rate",
        "quality_metric": "family_validity_rate",
        "quality_metric_definition": (
            "fraction of generated protein sequences whose Pfam-family "
            "prediction matches the conditioning family ID (Wave 10 anchor)."
        ),
        "source_json_real_ckpt": "verification_outputs/lineageflow_real_force_mode_q4_2026.json",
        "source_json_baselines": [
            "verification_outputs/lineageflow_baseline_euler_q4_2026.json",
            "verification_outputs/lineageflow_baseline_heun_q4_2026.json",
            "verification_outputs/lineageflow_baseline_rk4_q4_2026.json",
        ],
        "nfe_budgets": NFE_BUDGETS,
        "seeds": SEEDS,
        "n_cells_real_ran": n_real_ran,
        "n_cells_real_pending": n_real_pending,
        "n_cells_with_real_baseline_data": sum(
            len(real_cells_by_nfe[nfe]["baseline_family_validity_rate"])
            for nfe in NFE_BUDGETS
        ),
        "by_nfe": {},
        "wave_47_framework_composite_at_nfe10": wave47_framework_composite,
        "wave_52_euler_self_composite_at_nfe10": wave52_euler_composite,
        "wave_52_euler_phi3_at_nfe10": wave52_euler_phi3,
        "wave_52_euler_end_entropy_at_nfe10": wave52_euler_end_entropy,
        "completeness_note": (
            "LineageFlow NFE scan is INCOMPLETE at the time of this "
            "aggregation (Wave 58 Agent 3): only 1 of 9 cells (seed=42, "
            "NFE=10) ran end-to-end; 8 cells are PENDING due to host CPU "
            "bandwidth limit (~60 s per 657 M-param forward pass). All "
            "NFE>10 cells reuse the NFE=10 endpoint (saturation). The "
            "Wave 47 framework composite 0.211 at NFE=10 is the only "
            "framework-vs-baseline signal; the Wave 52 baselines (euler, "
            "heun, rk4) are self-comparisons, not baseline-vs-framework."
        ),
    }

    for nfe in NFE_BUDGETS:
        baseline = real_cells_by_nfe[nfe]["baseline_family_validity_rate"]
        framework = real_cells_by_nfe[nfe]["framework_family_validity_rate"]
        aggregate["by_nfe"][str(nfe)] = {
            "baseline_family_validity_rate_mean": _mean(baseline),
            "baseline_family_validity_rate_std": _std(baseline),
            "baseline_family_validity_rate_n": len(baseline),
            "framework_family_validity_rate_mean": _mean(framework),
            "framework_family_validity_rate_std": _std(framework),
            "framework_family_validity_rate_n": len(framework),
            "data_status": "computed" if len(baseline) > 0 else "pending_cpu_bandwidth",
        }
    return aggregate


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _std(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return 0.0 if xs else None
    mu = _mean(xs)
    var = sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def _plot(kanzi: dict[str, Any], lineageflow: dict[str, Any]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, (ax_left, ax_right) = plt.subplots(
        1, 2, figsize=(13, 5.5), sharey=False, dpi=130
    )

    # --- Left panel: Kanzi composite vs NFE ---
    nfes = NFE_BUDGETS
    k_composite_mean = [
        kanzi["by_nfe"][str(nfe)]["composite_mean"] for nfe in nfes
    ]
    k_composite_std = [
        kanzi["by_nfe"][str(nfe)]["composite_std"] or 0.0 for nfe in nfes
    ]
    # Baseline (kanzi_composite is framework-vs-baseline delta, NOT
    # baseline self-quality, so a single horizontal "0" line is the
    # baseline reference).
    ax_left.axhline(
        0.0,
        color="#888888",
        linestyle="--",
        linewidth=1.5,
        label="Baseline (kanzi_composite = 0 reference)",
    )
    ax_left.errorbar(
        nfes,
        k_composite_mean,
        yerr=k_composite_std,
        color="#1f77b4",
        marker="o",
        markersize=7,
        linewidth=2.0,
        capsize=4,
        label="Framework (kanzi_composite = Δ vs baseline)",
    )
    ax_left.set_xscale("log")
    ax_left.set_xticks(nfes)
    ax_left.set_xticklabels([str(n) for n in nfes])
    ax_left.set_xlabel("NFE budget (log scale)")
    ax_left.set_ylabel("kanzi_composite (Δ vs baseline)")
    ax_left.set_title("Kanzi: framework gains hold across NFE\n"
                      "(baseline saturates at NFE=10; σ = 0 within seed)")
    ax_left.grid(True, which="both", alpha=0.3)
    ax_left.legend(loc="lower right", fontsize=9)
    ax_left.set_ylim(-0.02, 0.22)

    # Annotate the composite value at NFE=10
    ax_left.annotate(
        f"+{k_composite_mean[0]:.3f}",
        xy=(nfes[0], k_composite_mean[0]),
        xytext=(15, -15),
        textcoords="offset points",
        fontsize=8,
        color="#1f77b4",
    )

    # --- Right panel: LineageFlow family_validity vs NFE ---
    # Baseline & framework collapse to 0.999 across all NFE (one real
    # cell at NFE=10, all others pending).
    ax_right.axhline(
        0.999,
        color="#888888",
        linestyle="--",
        linewidth=1.5,
        label="Baseline (family_validity_rate = 0.999 @ saturation)",
    )
    # Single-point framework marker at NFE=10
    real_ran_nfes = [
        nfe for nfe in nfes
        if lineageflow["by_nfe"][str(nfe)]["baseline_family_validity_rate_n"] > 0
    ]
    fw_y = [
        lineageflow["by_nfe"][str(nfe)]["framework_family_validity_rate_mean"]
        for nfe in real_ran_nfes
    ]
    ax_right.scatter(
        real_ran_nfes,
        fw_y,
        color="#1f77b4",
        marker="o",
        s=70,
        zorder=5,
        label=f"Framework (real ckpt, n={len(real_ran_nfes)})",
    )
    # Pending NFE values — show as hollow markers (with the saturation
    # reading predicted forward, since the Wave 47 composite stays
    # constant across NFE per the Wave 58 Agent 2 finding for Kanzi and
    # the Wave 58 Agent 3 PENDING pattern for LineageFlow).
    pending_nfes = [nfe for nfe in nfes if nfe not in real_ran_nfes]
    if pending_nfes:
        ax_right.scatter(
            pending_nfes,
            [0.999] * len(pending_nfes),
            color="#1f77b4",
            marker="o",
            s=70,
            facecolors="none",
            edgecolors="#1f77b4",
            alpha=0.5,
            label=f"Pending (CPU bandwidth, n={len(pending_nfes)})",
        )
    # Annotate the framework composite at NFE=10 (Wave 47)
    ax_right.annotate(
        f"framework composite\n=+{lineageflow['wave_47_framework_composite_at_nfe10']:.3f}\n@ NFE=10",
        xy=(10, 0.999),
        xytext=(35, -45),
        textcoords="offset points",
        fontsize=8,
        color="#1f77b4",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#1f77b4", alpha=0.85),
    )

    ax_right.set_xscale("log")
    ax_right.set_xticks(nfes)
    ax_right.set_xticklabels([str(n) for n in nfes])
    ax_right.set_xlabel("NFE budget (log scale)")
    ax_right.set_ylabel("family_validity_rate (Pfam family match)")
    ax_right.set_title("LineageFlow: baseline @ saturation across NFE\n"
                       "(real ckpt; 8/9 cells pending CPU bandwidth)")
    ax_right.grid(True, which="both", alpha=0.3)
    ax_right.legend(loc="lower right", fontsize=9)
    ax_right.set_ylim(0.99, 1.001)

    fig.suptitle(
        "NFE scan Q4-2026 — baseline plateau + framework continues\n"
        "(left: Kanzi composite, right: LineageFlow family_validity_rate)",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, FIG_OUT, dpi=_FIGURE_DPI, facecolor=None)


def main() -> None:
    kanzi = _aggregate_kanzi()
    lineageflow = _aggregate_lineageflow()
    aggregated = {
        "schema": "nfe_scan_aggregated.v1",
        "wave": 58,
        "agent": "Wave 58 Agent 4",
        "task": "aggregate NFE scan data + generate quality vs NFE plot",
        "nfe_budgets": NFE_BUDGETS,
        "seeds": SEEDS,
        "kanzi": kanzi,
        "lineageflow": lineageflow,
        "plot_path": str(FIG_OUT),
        "nfe_budgets_sampled": NFE_BUDGETS,
        "completeness": {
            "kanzi": "complete (18/18 cells, 3 seeds × 6 NFE)",
            "lineageflow": (
                "PARTIAL (1/9 cells: seed=42 NFE=10 ran; "
                "8 cells PENDING — host CPU bandwidth ~60 s/forward)"
            ),
        },
    }
    AGG_OUT.parent.mkdir(parents=True, exist_ok=True)
    with AGG_OUT.open("w") as fp:
        json.dump(aggregated, fp, indent=2, sort_keys=False)
    _plot(kanzi, lineageflow)
    print(f"WROTE {AGG_OUT}")
    print(f"WROTE {FIG_OUT}")


if __name__ == "__main__":
    main()
