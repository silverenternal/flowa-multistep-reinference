"""``tools/benchmark_uplifts.measure_internal_uplifts`` contract.

The benchmark harness is the place the framework's quantitative targets
are recorded, so it needs a test of its own: every framework-INTERNAL
uplift must be present, well-formed, and **achieved**. A regression that
silently drops a row (or flips ``achieved`` to ``no``) would otherwise
only surface when someone reads the generated markdown.
"""

from __future__ import annotations

import math

import pytest

from tools.benchmark_uplifts import _format_table, measure_internal_uplifts

REQUIRED_COLUMNS = {
    "algorithm",
    "uplift",
    "metric",
    "baseline",
    "current",
    "delta",
    "pct_change",
    "target",
    "achieved",
}

EXPECTED_UPLIFTS = {
    "P0 #3 projection-free exact W2",
    "P0 #8 vectorised round generation",
    "P0 #9 evidence-driver mode",
    "P1 area-weighted Voronoi coverage",
    "P1 percentile bootstrap CI",
    "P1 bounded-Lipschitz convergence diagnostic",
    "P2 #27 OT displacement mixing",
    "P2 #40 incremental chain verification",
    "sweep-based monotonicity certification",
}


@pytest.fixture(scope="module")
def rows() -> list[dict[str, object]]:
    return measure_internal_uplifts()


def test_every_internal_uplift_is_reported(rows: list[dict[str, object]]) -> None:
    assert {str(row["uplift"]) for row in rows} == EXPECTED_UPLIFTS


def test_rows_carry_the_full_schema(rows: list[dict[str, object]]) -> None:
    for row in rows:
        assert REQUIRED_COLUMNS.issubset(row), row.get("uplift")
        assert isinstance(row["achieved"], bool)
        assert str(row["target"]).strip()


def test_every_target_is_achieved(rows: list[dict[str, object]]) -> None:
    """The headline claim: all framework-INTERNAL targets are met."""
    missed = [str(row["uplift"]) for row in rows if not row["achieved"]]
    assert missed == [], f"unachieved targets: {missed}"


def test_baseline_and_current_are_distinct_where_a_delta_is_claimed(
    rows: list[dict[str, object]],
) -> None:
    for row in rows:
        baseline = float(row["baseline"])  # type: ignore[arg-type]
        current = float(row["current"])  # type: ignore[arg-type]
        if math.isfinite(baseline) and math.isfinite(current):
            assert baseline != current, str(row["uplift"])


def test_w2_row_reports_at_least_the_50_percent_reduction(
    rows: list[dict[str, object]],
) -> None:
    row = next(r for r in rows if r["uplift"] == "P0 #3 projection-free exact W2")
    assert float(row["current"]) <= 0.5 * float(row["baseline"])  # type: ignore[arg-type]
    assert float(row["pct_change"]) <= -50.0  # type: ignore[arg-type]


def test_rows_render_as_a_markdown_table(rows: list[dict[str, object]]) -> None:
    table = _format_table(rows)
    assert table.startswith("| Algorithm |")
    # One header row, one separator row, one row per uplift.
    assert len(table.strip().splitlines()) == len(rows) + 2
    assert " no " not in table


def test_measurement_is_reproducible() -> None:
    """Deterministic seeds: two runs must agree exactly."""
    first = measure_internal_uplifts()
    second = measure_internal_uplifts()
    assert first == second
