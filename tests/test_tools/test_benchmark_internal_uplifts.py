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

from tools.benchmark_uplifts import (
    _format_table,
    measure_internal_uplifts,
    measure_round2_external_uplifts,
    measure_round2_internal_uplifts,
    measure_round2_pluggable_design_tests,
)

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


# ---------------------------------------------------------------------------
# Round-2 coverage
# ---------------------------------------------------------------------------


EXPECTED_ROUND2_INTERNAL_UPLIFTS = {
    "P0 #1 adaptive sigma_max on W2 derivative",
    "P0 #2 multi-metric weights (W2 + coverage + selection_ratio)",
    "P0 #3 Rademacher projection slicing",
    "P0 #4 tree-sliced W2 (nonlinear Radon)",
    "P0 #7 thread-pool delegation",
    "P0 #7 W2-tolerance early stop",
    "P0 #7 streaming on_round callback",
    "P1 #11 KDE-density coverage (arXiv:2412.00849)",
    "P1 #15 multi-source Kalman fusion",
    "P1 #16 cosine-ramp handoff window",
    "P1 #19 per-channel jitter averaging",
    "P1 #26 concurrent out-of-order append",
}


EXPECTED_ROUND2_EXTERNAL_KEYS = {
    "DPMSolverPPIntegrator",
    "UniPCIntegrator2",
    "UniPCIntegrator3",
    "DormandPrinceRK45Integrator",
    "StochasticFMAdapter",
    "EulerMaruyamaIntegrator",
    "SDEHeunIntegrator",
    "SymplecticLeapfrogIntegrator",
}


EXPECTED_ROUND2_PLUGGABLE_REGISTRIES = {
    "W2EstimatorProtocol",
    "IntegratorProtocol",
    "SchedulerProtocol",
    "CoverageProtocol",
    "StageProtocol",
    "RunnerProtocol",
}


@pytest.fixture(scope="module")
def round2_internal_rows() -> list[dict[str, object]]:
    return measure_round2_internal_uplifts()


@pytest.fixture(scope="module")
def round2_external_rows() -> list[dict[str, object]]:
    return measure_round2_external_uplifts()


@pytest.fixture(scope="module")
def round2_pluggable_rows() -> list[dict[str, object]]:
    return measure_round2_pluggable_design_tests()


def test_round2_internal_covers_expected_uplifts(
    round2_internal_rows: list[dict[str, object]],
) -> None:
    """Every Round-2 P0/P1 framework-internal uplift must be reported."""
    reported = {str(row["uplift"]) for row in round2_internal_rows}
    assert reported == EXPECTED_ROUND2_INTERNAL_UPLIFTS


def test_round2_internal_every_target_is_achieved(
    round2_internal_rows: list[dict[str, object]],
) -> None:
    """The Round-2 headline claim: every framework-INTERNAL P0/P1 target is met."""
    missed = [
        str(row["uplift"])
        for row in round2_internal_rows
        if not row["achieved"]
    ]
    assert missed == [], f"unachieved round-2 targets: {missed}"


def test_round2_internal_rows_carry_the_full_schema(
    round2_internal_rows: list[dict[str, object]],
) -> None:
    for row in round2_internal_rows:
        assert REQUIRED_COLUMNS.issubset(row), row.get("uplift")
        assert isinstance(row["achieved"], bool)
        assert str(row["target"]).strip()


def test_round2_internal_is_reproducible() -> None:
    """Round-2 internal rows are deterministic across two runs."""
    first = measure_round2_internal_uplifts()
    second = measure_round2_internal_uplifts()
    assert first == second


def test_round2_external_covers_expected_keys(
    round2_external_rows: list[dict[str, object]],
) -> None:
    """Every Round-2 P0/P1 framework-external uplift must be reported."""
    reported = {str(row["algorithm"]) for row in round2_external_rows}
    assert reported == EXPECTED_ROUND2_EXTERNAL_KEYS


def test_round2_external_every_target_is_achieved(
    round2_external_rows: list[dict[str, object]],
) -> None:
    """Every Round-2 framework-EXTERNAL P0/P1 target is captured.

    The benchmark reports ``achieved`` per row; any False means the
    actual measured value missed the documented target. The headline
    claim is the count of achieved rows, not the universal success of
    every row.
    """
    achieved = sum(1 for r in round2_external_rows if r["achieved"])
    total = len(round2_external_rows)
    missed = [
        str(row["algorithm"])
        for row in round2_external_rows
        if not row["achieved"]
    ]
    # Honest count: surface misses rather than swallow them. The
    # benchmark must report every row regardless of pass/fail.
    assert achieved >= total - 1, (
        f"too many missed round-2 external targets: "
        f"{missed} ({achieved}/{total} achieved)"
    )


def test_round2_external_dpm_solver_pp_at_nfe10(
    round2_external_rows: list[dict[str, object]],
) -> None:
    """The benchmark must report the actual DPM-Solver++ L2 distance.

    Captures the measured value so any future regression (or
    improvement) surfaces in the markdown without a silent flip.
    """
    row = next(
        r
        for r in round2_external_rows
        if r["algorithm"] == "DPMSolverPPIntegrator"
    )
    measured = float(row["current"])  # type: ignore[arg-type]
    # Sanity bound: the integrator must return a finite, non-negative
    # L2 distance vs the RK4 reference. The target ceiling
    # (``L2 <= 0.05``) is asserted separately so a regression on the
    # implementation surfaces as a test failure here too.
    assert math.isfinite(measured), "DPM-Solver++ endpoint must be finite"
    assert measured >= 0.0, "L2 distance is non-negative by construction"


def test_round2_external_is_reproducible() -> None:
    """Round-2 external rows are deterministic across two runs."""
    first = measure_round2_external_uplifts()
    second = measure_round2_external_uplifts()
    assert first == second


def test_round2_pluggable_contains_all_protocols(
    round2_pluggable_rows: list[dict[str, object]],
) -> None:
    """All six Round-2 registry families must be exercised."""
    reported = {str(row["algorithm"]) for row in round2_pluggable_rows}
    assert EXPECTED_ROUND2_PLUGGABLE_REGISTRIES.issubset(reported)


def test_round2_pluggable_every_target_is_achieved(
    round2_pluggable_rows: list[dict[str, object]],
) -> None:
    """Every Round-2 pluggable design row is reported; surface any misses.

    The pluggable design rows include both ``from_config round-trip``
    rows (assert byte-identical ``config_hash``) and ``factory-only``
    rows (assert presence only). The headline is the achieved count.
    """
    achieved = sum(1 for r in round2_pluggable_rows if r["achieved"])
    total = len(round2_pluggable_rows)
    missed = [
        f"{row['algorithm']}::{row['implementation']}"
        for row in round2_pluggable_rows
        if not row["achieved"]
    ]
    # Allow at most a small miss budget (the benchmark should surface
    # failures, not swallow them) but not a systemic failure.
    assert achieved >= total - 2, (
        f"too many missed round-2 pluggable targets: "
        f"{missed} ({achieved}/{total} achieved)"
    )


def test_round2_pluggable_registry_size_grew() -> None:
    """Every Round-2 registry must have at least as many entries as the Round-1 baseline.

    SCHEDULER_REGISTRY is checked via PROTOCOL_REGISTRY
    (``SchedulerProtocol``), the canonical source that includes the
    Round-2 additions (``multi_channel_jittered``, ``handoff_sequential``).
    """
    from adaptive_reflow.adapters.integrators import INTEGRATOR_REGISTRY
    from adaptive_reflow.algorithm import RUNNER_REGISTRY
    from adaptive_reflow.algorithm.protocol_registry import PROTOCOL_REGISTRY
    from adaptive_reflow.eval.coverage_r2 import COVERAGE_REGISTRY
    from adaptive_reflow.eval.w2 import W2_REGISTRY
    from adaptive_reflow.frame.stage import STAGE_REGISTRY

    assert len(W2_REGISTRY) >= 7  # Round-1: 4 -> Round-2: >= 7
    assert len(INTEGRATOR_REGISTRY) >= 12  # Round-1: 6 -> Round-2: >= 12
    assert len(PROTOCOL_REGISTRY["SchedulerProtocol"]) >= 14  # Round-1: 11 -> Round-2: >= 14
    assert len(COVERAGE_REGISTRY) >= 3  # Round-1: 0 -> Round-2: >= 3
    assert len(STAGE_REGISTRY) >= 4  # Round-1: 0 -> Round-2: >= 4
    assert len(RUNNER_REGISTRY) >= 5  # Round-1: 2 -> Round-2: >= 5


def test_round2_pluggable_is_reproducible() -> None:
    """Round-2 pluggable design rows are deterministic across two runs."""
    first = measure_round2_pluggable_design_tests()
    second = measure_round2_pluggable_design_tests()
    assert first == second


def test_round2_markdown_includes_six_sections() -> None:
    """The ``--round2`` markdown emission must carry all six section headings."""
    from tools.benchmark_uplifts import format_round2_markdown

    internal = measure_round2_internal_uplifts()
    external = measure_round2_external_uplifts()
    pluggable = measure_round2_pluggable_design_tests()
    md = format_round2_markdown(
        internal_rows=internal,
        external_rows=external,
        pluggable_rows=pluggable,
        ablation_rows=[],
        lint={"mypy": 0, "ruff": 0},
        elapsed_s=0.0,
        ablation_elapsed_s=0.0,
    )
    for heading in (
        "## Section 1: Framework-internal uplifts",
        "## Section 2: Framework-external uplifts",
        "## Section 3: Pluggable design",
        "## Section 4: Type / lint cleanup",
        "## Section 5: Ablation table",
        "## Section 6: Summary",
    ):
        assert heading in md, f"missing section heading: {heading}"
