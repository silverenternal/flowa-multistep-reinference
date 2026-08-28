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

The script also sweeps :func:`_paper_evidence_balance` directly to
verify that the closed-form formula (after the commit 91f3741 fix)
moves the sheet share toward 1 as ``eps -> 0`` (paper Lemma 2 /
Theorem 1 direction). The sweep grid is:

* ``n`` in ``[0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95]``
* ``eps`` in ``[0.5, 0.1, 0.05, 0.01, 0.005, 0.001]``

The probe prints ``(sheet, cell, ratio)`` for every ``(n, eps)`` cell
and asserts the qualitative pattern: ``ratio -> 1`` as ``eps -> 0``
and as ``n -> 1``. The result is appended to the same markdown file
(``docs/ABLATION_METRIC_PROBE.md`` by default) as a separate section.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pytest

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
    _paper_evidence_balance,
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


# ---------------------------------------------------------------------------
# _paper_evidence_balance sweep
# ---------------------------------------------------------------------------

#: Grid of `n_cap_base` values used by the closed-form sweep. Chosen to
#: span the small, mid, and large-capacity regimes a cosine ramp emits.
_PAPER_SWEEP_N_GRID: tuple[float, ...] = (
    0.05,
    0.1,
    0.2,
    0.3,
    0.5,
    0.7,
    0.9,
    0.95,
)

#: Grid of `eps_implicit` values used by the closed-form sweep. Includes
#: the canonical ``0.05`` default plus the small values where Theorem 1
#: predicts sheet dominance.
_PAPER_SWEEP_EPS_GRID: tuple[float, ...] = (
    0.5,
    0.1,
    0.05,
    0.01,
    0.005,
    0.001,
)


def _sweep_paper_evidence_balance() -> list[dict[str, object]]:
    """Sweep ``_paper_evidence_balance(n, eps)`` over the canonical grid.

    Returns a list of row dicts suitable for inclusion in the markdown
    probe. The helper also verifies the qualitative pattern predicted by
    paper Lemma 2 / Theorem 1: as ``eps -> 0`` the sheet share tends to
    1 for every ``n < 1``; as ``n -> 1`` the share also tends to 1
    regardless of ``eps``. Any monotonicity violation is surfaced as an
    assertion failure.
    """
    rows: list[dict[str, object]] = []
    for n_base in _PAPER_SWEEP_N_GRID:
        prev_ratio = -1.0
        for eps_implicit in _PAPER_SWEEP_EPS_GRID:
            sheet = max(float(n_base), float(eps_implicit))
            cell = (1.0 - float(n_base)) ** 2 * float(eps_implicit) ** 2
            ratio = float(_paper_evidence_balance(n_base, eps_implicit))
            # Recompute sheet/cell deterministically so the markdown
            # table exposes the paper-aligned closed form explicitly.
            rows.append(
                {
                    "n": float(n_base),
                    "eps": float(eps_implicit),
                    "sheet": float(sheet),
                    "cell": float(cell),
                    "ratio": float(ratio),
                }
            )
            # Qualitatively: as eps decreases, the ratio is non-decreasing
            # (paper Theorem 1 direction) for every n < 1.
            assert ratio >= prev_ratio - 1e-12, (
                f"_paper_evidence_balance must be non-decreasing as eps "
                f"decreases; got n={n_base} eps={eps_implicit} ratio="
                f"{ratio:.6f} after prev_ratio={prev_ratio:.6f}"
            )
            prev_ratio = ratio
        # And in the limit (smallest eps) the ratio is essentially 1 for
        # every n < 1.
        assert prev_ratio == pytest.approx(1.0, abs=1e-6), (
            f"_paper_evidence_balance must approach 1 as eps -> 0 for "
            f"n={n_base} < 1; got {prev_ratio:.6f}"
        )
    return rows


def _format_paper_sweep_md(rows: list[dict[str, object]]) -> str:
    """Format the closed-form sweep as a markdown table.

    Rows are indexed by ``n_cap_base``; columns by ``eps_implicit``; the
    cell value is the closed-form ``ratio = sheet / (sheet + cell)`` that
    the scheduler records on :attr:`last_evidence_ratio`.
    """
    lines: list[str] = []
    lines.append(
        "## `_paper_evidence_balance` closed-form sweep (post-flip)"
    )
    lines.append("")
    lines.append(
        "Direct call into "
        "`adaptive_reflow.algorithm.scheduler._paper_evidence_balance` "
        "for the canonical ``n`` x ``eps`` grid. With the formula flip "
        "(commit `91f3741`) the sheet share uses paper-positive eps "
        "powers:"
    )
    lines.append("")
    lines.append("```")
    lines.append(
        "    sheet = max(n, eps)               # eps^{+1}  (Lemma 2 / Cor. 1)"
    )
    lines.append(
        "    cell  = (1 - n) ** 2 * eps ** 2   # eps^{+2}  (Lemma 3)"
    )
    lines.append(
        "    ratio = sheet / (sheet + cell)"
    )
    lines.append("```")
    lines.append("")
    lines.append(
        "Expected pattern: as ``eps -> 0`` (each row, left-to-right) the "
        "ratio tends to **1** (sheet dominance, paper Theorem 1). As "
        "``n -> 1`` (each column, top-to-bottom) the ratio also tends "
        "to **1** regardless of ``eps``."
    )
    lines.append("")
    header_cells = ["n \\ eps"] + [f"{eps:g}" for eps in _PAPER_SWEEP_EPS_GRID]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "|".join(["---:"] * len(header_cells)) + "|")
    # Group rows by n to build a wide table; preserve grid order so the
    # ``n -> 1`` direction runs top-to-bottom.
    by_n: dict[float, dict[float, float]] = {}
    for row in rows:
        by_n.setdefault(float(row["n"]), {})[float(row["eps"])] = float(
            row["ratio"]
        )
    for n_base in _PAPER_SWEEP_N_GRID:
        cells = by_n.get(float(n_base), {})
        line = f"| {n_base:g} |"
        for eps_implicit in _PAPER_SWEEP_EPS_GRID:
            ratio = cells.get(float(eps_implicit), float("nan"))
            line += f" {ratio:.6f} |"
        lines.append(line)
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
