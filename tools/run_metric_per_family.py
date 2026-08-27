"""Run the EvidenceScaleGapMetric per-round for every scheduler family on both targets.

This is an empirical probe that exercises the
:class:`EvidenceScaleGapMetric` (formerly `PosteriorSelectionEvaluator`)
through the same `ReInferenceRunner` plumbing the ablation script uses,
but on **every** (scheduler, target) cell — not just the two paper-
grounded configurations the standard ablation grid runs.

The output is a markdown table that records, for each (scheduler,
target) cell, the round-0 and final-round
`per_round_metrics[r]["selection_ratio"]` value plus the curve's range
and the number of monotone-up rounds (a "convergence" proxy).

The metric is documented as schedule-independent by construction
(`docs/ABLATION.md` §"CosineAnneal vs CodimensionSheet"); the script
verifies that empirically.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter  # noqa: E402
from adaptive_reflow.algorithm import (  # noqa: E402
    ReInferenceConfig,
    ReInferenceRunner,
    SchedulerProtocol,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler import (  # noqa: E402
    CodimensionSheetScheduler,
    ConvergenceAdaptiveScheduler,
    PolynomialScheduler,
    SigmoidScheduler,
)
from adaptive_reflow.eval.posterior_selection_evaluator import (  # noqa: E402
    EvidenceScaleGapMetric,
)

CANONICAL_TARGETS: tuple[str, ...] = ("two_moons", "eight_gaussians")
DEFAULT_ROUNDS: int = 20
DEFAULT_SEED: int = 42
TWODIM_FM_CHANNELS: tuple[str, ...] = ("xy",)


def _build_scheduler(family: str, rounds: int) -> SchedulerProtocol:
    if family == "cosine":
        return default_cosine_scheduler(cycle_length=rounds, n_min=0.0, n_max=1.0)
    if family == "polynomial":
        return PolynomialScheduler(
            cycle_length=rounds, n_min=0.0, n_max=1.0, power=2.0
        )
    if family == "sigmoid":
        return SigmoidScheduler(
            cycle_length=rounds,
            n_min=0.0,
            n_max=1.0,
            steepness=10.0,
            midpoint=0.5,
        )
    if family == "convergence-adaptive":
        return ConvergenceAdaptiveScheduler(
            base=default_cosine_scheduler(cycle_length=rounds, n_min=0.0, n_max=1.0),
            kp=0.10,
            kd=0.05,
            shift_max=0.15,
        )
    if family == "codimension-sheet":
        return CodimensionSheetScheduler(
            cycle_length=rounds, n_min=0.0, n_max=1.0, eps_implicit=0.05
        )
    raise ValueError(f"unknown family: {family}")


def _weights_path(target: str) -> Path:
    return REPO_ROOT / "data" / f"twodim_fm_{target}.npz"


def _run_one(
    family: str,
    target: str,
    weights_path: Path,
    *,
    seed: int,
    rounds: int,
    n_gen: int,
) -> dict[str, object]:
    scheduler = _build_scheduler(family, rounds)
    adapter = TwoDimFMAdapter(weights_path=weights_path, target=target)
    from adaptive_reflow.algorithm import default_policy_driver

    runner = ReInferenceRunner(
        adapter=adapter,
        scheduler=scheduler,
        policy_driver=default_policy_driver(),
    )
    config = ReInferenceConfig(
        n_rounds=rounds,
        outer_cycle_id=0,
        target_round=0,
        seed=int(seed),
        channels=TWODIM_FM_CHANNELS,
        selection_evaluator=EvidenceScaleGapMetric(
            target=target,  # type: ignore[arg-type]
            n_gen=int(n_gen),
            n_ref=int(n_gen),
            seed=int(seed),
            eps_implicit=0.05,
        ),
    )
    result = runner.run(config)
    curve = [
        float(result.per_round_metrics[r]["selection_ratio"])
        for r in sorted(result.per_round_metrics)
        if "selection_ratio" in result.per_round_metrics[r]
    ]
    monotone_up = sum(
        1 for i in range(1, len(curve)) if curve[i] >= curve[i - 1]
    )
    return {
        "family": family,
        "target": target,
        "round_0": float(curve[0]) if curve else float("nan"),
        "final": float(curve[-1]) if curve else float("nan"),
        "min": float(min(curve)) if curve else float("nan"),
        "max": float(max(curve)) if curve else float("nan"),
        "mean_tail5": (
            float(sum(curve[-5:]) / len(curve[-5:])) if len(curve) >= 5 else float("nan")
        ),
        "monotone_up_rounds": int(monotone_up),
        "n_rounds": len(curve),
        "curve": curve,
    }


def _format_md(rows: list[dict[str, object]], *, rounds: int) -> str:
    lines: list[str] = []
    lines.append("# EvidenceScaleGapMetric per-round (empirical probe)")
    lines.append("")
    lines.append(
        f"All cells run with `seed=42`, `rounds={rounds}`, and `n_gen=100` "
        "replays per round. The runner records "
        "`per_round_metrics[r][\"selection_ratio\"]` on every round."
    )
    lines.append("")
    lines.append(
        "| Target | Scheduler family | Round 0 | Round {r-1} | Min | Max | "
        "Mean (last 5) | Monotone-up rounds |"
    )
    # The table header needs the row count baked in
    lines[-1] = (
        "| Target | Scheduler family | Round 0 | "
        f"Round {rounds - 1} | Min | Max | "
        "Mean (last 5) | Monotone-up rounds |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row['target']} | {row['family']} | "
            f"{row['round_0']:.4f} | {row['final']:.4f} | "
            f"{row['min']:.4f} | {row['max']:.4f} | "
            f"{row['mean_tail5']:.4f} | "
            f"{int(row['monotone_up_rounds'])}/{int(row['n_rounds']) - 1} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run EvidenceScaleGapMetric per-round across all families."
    )
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-gen", type=int, default=100)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "docs" / "ABLATION_METRIC_PROBE.md",
    )
    args = parser.parse_args(argv)

    rounds = int(args.rounds)
    families = (
        "cosine",
        "polynomial",
        "sigmoid",
        "convergence-adaptive",
        "codimension-sheet",
    )

    rows: list[dict[str, object]] = []
    started = time.perf_counter()
    for target in CANONICAL_TARGETS:
        weights_path = _weights_path(target)
        if not weights_path.exists():
            print(f"FATAL missing weights for target={target}", file=sys.stderr)
            return 2
        for family in families:
            cell_started = time.perf_counter()
            print(
                f"[metric_probe] target={target} family={family} ...",
                flush=True,
            )
            row = _run_one(
                family,
                target,
                weights_path,
                seed=int(args.seed),
                rounds=rounds,
                n_gen=int(args.n_gen),
            )
            cell_elapsed = time.perf_counter() - cell_started
            rows.append(row)
            print(
                f"[metric_probe]   done in {cell_elapsed:.1f}s "
                f"round_0={row['round_0']:.4f} "
                f"final={row['final']:.4f} "
                f"min={row['min']:.4f} "
                f"max={row['max']:.4f}",
                flush=True,
            )
    elapsed = time.perf_counter() - started

    md = _format_md(rows, rounds=rounds)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(
        f"[metric_probe] wrote {out_path} after {elapsed:.1f}s "
        f"({len(rows)} cells)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
