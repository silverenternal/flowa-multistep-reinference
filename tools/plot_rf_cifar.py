"""Plot the framework ablation curves for Rectified Flow CIFAR-10.

Reads the JSON summary produced by :mod:`tools.run_rf_cifar_ablation`
and renders two matplotlib figures:

* ``docs/figures/r5_rf_cifar_fid_trajectory.png`` — FID per round for
  each of the 4 scheduler variants, with a horizontal dashed reference
  line at the paper's published FID 2.21.
* ``docs/figures/r5_rf_cifar_selection_ratio.png`` — ``selection_ratio``
  trajectory per round for each scheduler, with reference lines at 0.81
  (round-0 baseline) and 1.0 (paper Theorem 1 limit).

The script is intentionally a single-file utility: it accepts a path
to the ablation JSON (default ``data/rf_ablation/ablation.json``) and
writes the two PNG files under ``--output-dir``. It uses matplotlib
in ``Agg`` (non-interactive) backend so it can run on a headless
machine / CI. No styling beyond a minimal grid + legend so the
output is interpretable in any rendering target.

Usage::

    python -m tools.plot_rf_cifar
    python -m tools.plot_rf_cifar --ablation-json data/rf_ablation/ablation.json \\
        --output-dir docs/figures
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _make_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.plot_rf_cifar",
        description="Plot the RF CIFAR-10 framework ablation figures.",
    )
    p.add_argument(
        "--ablation-json",
        type=str,
        default="data/rf_ablation/ablation.json",
        help="Path to the per-row JSON summary from tools.run_rf_cifar_ablation.",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default="docs/figures",
        help="Where to write the two PNG files.",
    )
    p.add_argument(
        "--published-fid",
        type=float,
        default=2.21,
        help="Published baseline FID (Liu 2022 Table 2).",
    )
    return p


def _load_ablation(path: Path) -> list[dict[str, object]]:
    """Load the ablation JSON. Exits 1 on parse error."""
    import json

    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        print(f"[ERROR] ablation JSON not found at {path}", file=sys.stderr)
        raise SystemExit(1) from exc
    except json.JSONDecodeError as exc:
        print(f"[ERROR] ablation JSON parse failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if not isinstance(data, list):
        print("[ERROR] ablation JSON must be a list of per-scheduler dicts", file=sys.stderr)
        raise SystemExit(1)
    return data


def _plot_fid_trajectory(
    summaries: list[dict[str, object]],
    *,
    output_path: Path,
    published_fid: float,
) -> None:
    """Render the FID-trajectory figure (one line per scheduler)."""
    import matplotlib

    matplotlib.use("Agg")  # headless backend.
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    for summary in summaries:
        fids_raw: Any = summary.get("fid_curve", [])
        fids: list[float] = [float(x) for x in cast(list[float], fids_raw)]
        if not fids:
            continue
        rounds = list(range(len(fids)))
        ax.plot(rounds, fids, marker="o", label=str(summary.get("scheduler", "?")))
    ax.axhline(
        published_fid,
        color="black",
        linestyle="--",
        linewidth=1.0,
        label=f"paper FID {published_fid:.2f}",
    )
    ax.set_xlabel("round index")
    ax.set_ylabel("FID")
    ax.set_title("Rectified Flow CIFAR-10 — FID trajectory across rounds")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_selection_ratio(
    summaries: list[dict[str, object]],
    *,
    output_path: Path,
) -> None:
    """Render the selection-ratio trajectory figure (one line per scheduler)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    for summary in summaries:
        curve_raw: Any = summary.get("selection_curve", [])
        curve: list[float] = [float(x) for x in cast(list[float], curve_raw)]
        if not curve:
            continue
        rounds = list(range(len(curve)))
        ax.plot(rounds, curve, marker="o", label=str(summary.get("scheduler", "?")))
    ax.axhline(0.81, color="grey", linestyle=":", linewidth=1.0, label="baseline 0.81")
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.0, label="paper Theorem 1 limit")
    ax.set_xlabel("round index")
    ax.set_ylabel("selection_ratio")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Rectified Flow CIFAR-10 — selection_ratio across rounds")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    args = _make_argparser().parse_args(argv)
    summaries = _load_ablation(Path(args.ablation_json))
    output_dir = Path(args.output_dir)

    fid_path = output_dir / "r5_rf_cifar_fid_trajectory.png"
    sel_path = output_dir / "r5_rf_cifar_selection_ratio.png"

    _plot_fid_trajectory(summaries, output_path=fid_path, published_fid=float(args.published_fid))
    _plot_selection_ratio(summaries, output_path=sel_path)

    print(f"[DONE] fid_trajectory -> {fid_path}")
    print(f"[DONE] selection_ratio -> {sel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
