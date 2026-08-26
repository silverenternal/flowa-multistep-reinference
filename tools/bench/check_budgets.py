"""Regression gate for the perf budget suite.

This script reads the freshly-emitted ``docs/benchmarks.json`` (written
by :mod:`tools.bench.runner`) and the static ``tools/bench/budgets.json``
file, then fails the process if any tracked metric regressed by more
than ``regression_threshold_pct`` (default ``20``) of its declared
budget.

Per-metric semantics
---------------------

For each ``metric_name`` in :data:`BUDGETS`:

* ``budget = budgets[metric_name]`` — declared upper bound in
  microseconds.
* ``measured = benchmarks.metrics[metric_name + "_p95" OR suffix]`` —
  the observed value from the latest run.

The script treats the budget as an absolute ceiling, not a baseline
to subtract from. A regression is recorded when

    measured > budget * (1 + regression_threshold_pct / 100)

When that happens the script prints a one-line summary for every
regression, exits with a non-zero status, and prints the full report
to stderr. When no metric regresses the script prints a one-line
``ok`` summary to stdout and exits 0.

Mappings
--------

The budgets file uses keys without the ``_p95`` suffix
(``bounded_merge_us_p95``). The benchmarks JSON keys include
``_p95`` as part of the metric name. The script normalises both sides
to a canonical form so the metric names match regardless of trailing
suffixes.

Run from the repo root::

    PYTHONPATH=. python tools/bench/check_budgets.py \\
        --benchmarks docs/benchmarks.json \\
        --budgets tools/bench/budgets.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DEFAULT_REGRESSION_PCT: float = 20.0

#: Canonical metric names that map 1:1 between budgets.json and
#: benchmarks.json. The check uses the budget key as the source of
#: truth and looks up the measured value in :attr:`benchmarks.metrics`.
DEFAULT_TRACKED_METRICS: tuple[str, ...] = (
    "bounded_merge_us_p95",
    "compute_channel_decision_us_p95",
    "evaluate_claim_gate_us_p95",
    "engine_round_loop_us_p95",
)


# ---------------------------------------------------------------------------
# Helpers — pure
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    """Load ``path`` as JSON; raise a friendly error on missing input."""
    if not path.exists():
        raise FileNotFoundError(f"required JSON input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_metric_value(metrics: dict, budget_key: str) -> float | None:
    """Return the measured value for ``budget_key`` from ``metrics``.

    Tries (in order):

    1. The exact budget key (``metrics[budget_key]``).
    2. The same key with the ``_p95`` suffix stripped (``metrics[key]``
       where ``budget_key.endswith("_p95")``).

    Returns ``None`` when neither lookup yields a finite value.
    """
    if budget_key in metrics:
        value = metrics[budget_key]
        if isinstance(value, (int, float)):
            return float(value)
    if budget_key.endswith("_p95"):
        bare = budget_key[: -len("_p95")]
        if bare in metrics:
            value = metrics[bare]
            if isinstance(value, (int, float)):
                return float(value)
    return None


def _classify(
    *,
    measured: float,
    budget: float,
    pct: float,
) -> tuple[str, float]:
    """Return ``(status, allowed_ceiling)`` for one metric.

    ``status`` is one of ``"ok"`` (within budget), ``"warn"`` (over
    budget but under the regression threshold), ``"regressed"``
    (exceeded ``budget * (1 + pct/100)``).
    """
    if budget <= 0:
        # A non-positive budget is malformed; treat any positive
        # measurement as a regression so the script fails loudly.
        return ("regressed" if measured > 0 else "ok", budget)
    ceiling = budget * (1.0 + pct / 100.0)
    if measured <= budget:
        return ("ok", ceiling)
    if measured <= ceiling:
        return ("warn", ceiling)
    return ("regressed", ceiling)


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------


def check_budgets(
    *,
    benchmarks_path: Path,
    budgets_path: Path,
    pct: float = DEFAULT_REGRESSION_PCT,
    metrics: Iterable[str] = DEFAULT_TRACKED_METRICS,
) -> tuple[int, list[dict]]:
    """Run the budget check and return ``(exit_code, report_rows)``.

    The caller can either let the function raise (it never does on the
    happy path) or inspect the returned ``report_rows`` for downstream
    reporting. The ``exit_code`` is ``0`` on success / warn-only and
    ``1`` when at least one metric regressed beyond the threshold.
    """
    benchmarks = _load_json(benchmarks_path)
    budgets_doc = _load_json(budgets_path)

    budgets = budgets_doc.get("budgets", {})
    bench_metrics = benchmarks.get("metrics", {})

    rows: list[dict] = []
    exit_code = 0

    for metric_name in metrics:
        budget_value = budgets.get(metric_name)
        if budget_value is None:
            rows.append(
                {
                    "metric": metric_name,
                    "status": "missing_budget",
                    "measured": None,
                    "budget": None,
                    "ceiling": None,
                }
            )
            continue
        if not isinstance(budget_value, (int, float)) or float(budget_value) <= 0:
            rows.append(
                {
                    "metric": metric_name,
                    "status": "invalid_budget",
                    "measured": None,
                    "budget": float(budget_value) if isinstance(budget_value, (int, float)) else None,
                    "ceiling": None,
                }
            )
            exit_code = 1
            continue

        measured = _resolve_metric_value(bench_metrics, metric_name)
        if measured is None:
            rows.append(
                {
                    "metric": metric_name,
                    "status": "missing_measurement",
                    "measured": None,
                    "budget": float(budget_value),
                    "ceiling": None,
                }
            )
            exit_code = 1
            continue

        status, ceiling = _classify(
            measured=float(measured),
            budget=float(budget_value),
            pct=float(pct),
        )
        rows.append(
            {
                "metric": metric_name,
                "status": status,
                "measured": float(measured),
                "budget": float(budget_value),
                "ceiling": float(ceiling),
            }
        )
        if status == "regressed":
            exit_code = 1

    return exit_code, rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="flowa.bench.check_budgets",
        description="Fail if any perf metric regressed beyond its budget.",
    )
    parser.add_argument(
        "--benchmarks",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "docs" / "benchmarks.json",
        help="path to docs/benchmarks.json (default: %(default)s)",
    )
    parser.add_argument(
        "--budgets",
        type=Path,
        default=Path(__file__).resolve().parent / "budgets.json",
        help="path to tools/bench/budgets.json (default: %(default)s)",
    )
    parser.add_argument(
        "--pct",
        type=float,
        default=DEFAULT_REGRESSION_PCT,
        help=(
            "regression threshold in percent of the budget "
            f"(default: {DEFAULT_REGRESSION_PCT})"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        exit_code, rows = check_budgets(
            benchmarks_path=args.benchmarks,
            budgets_path=args.budgets,
            pct=float(args.pct),
        )
    except FileNotFoundError as exc:
        sys.stderr.write(f"check_budgets: {exc}\n")
        return 2
    except (json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(f"check_budgets: malformed JSON input: {exc}\n")
        return 2

    # Print a compact human-readable summary.
    summary_lines = []
    n_ok = 0
    n_warn = 0
    n_regressed = 0
    n_missing = 0
    for row in rows:
        metric = row["metric"]
        status = row["status"]
        if status == "ok":
            n_ok += 1
            summary_lines.append(
                f"  ok   {metric}: measured={row['measured']:.1f}us "
                f"<= budget={row['budget']:.1f}us"
            )
        elif status == "warn":
            n_warn += 1
            summary_lines.append(
                f"  warn {metric}: measured={row['measured']:.1f}us "
                f"over budget={row['budget']:.1f}us "
                f"(ceiling={row['ceiling']:.1f}us)"
            )
        elif status == "regressed":
            n_regressed += 1
            summary_lines.append(
                f"  FAIL {metric}: measured={row['measured']:.1f}us "
                f"exceeds ceiling={row['ceiling']:.1f}us "
                f"(budget={row['budget']:.1f}us)"
            )
        else:
            n_missing += 1
            summary_lines.append(f"  ---- {metric}: {status}")

    sys.stdout.write("\n".join(summary_lines) + "\n")
    sys.stdout.write(
        f"\nsummary: {n_ok} ok, {n_warn} warn, {n_regressed} regressed, "
        f"{n_missing} missing\n"
    )
    sys.stdout.flush()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
