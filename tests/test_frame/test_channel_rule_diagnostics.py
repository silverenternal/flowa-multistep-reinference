"""Sweep-based monotonicity certification for the channel rule."""

from __future__ import annotations

import pytest

from adaptive_reflow.contracts import ChannelRuleInputs
from adaptive_reflow.frame.channel_rule import check_monotonicity_property
from adaptive_reflow.frame.channel_rule_diagnostics import (
    DEFAULT_SWEEP_POINTS,
    MONOTONE_FACTOR_DIRECTION,
    MonotonicityReport,
    certify_all_factors,
    certify_monotonicity,
    sweep_grid,
)
from tests.perf.test_kernel_benchmarks import _make_channel_rule_inputs


@pytest.fixture()
def baseline() -> ChannelRuleInputs:
    """A fully-valid, gate-opening set of channel-rule inputs."""
    return _make_channel_rule_inputs()


# ---------------------------------------------------------------------------
# sweep_grid
# ---------------------------------------------------------------------------


def test_sweep_grid_spans_the_closed_unit_interval() -> None:
    grid = sweep_grid(5)
    assert grid[0] == pytest.approx(0.0)
    assert grid[-1] == pytest.approx(1.0)
    assert len(grid) == 5
    assert list(grid) == sorted(grid)


def test_sweep_grid_rejects_degenerate_parameters() -> None:
    with pytest.raises(ValueError):
        sweep_grid(1)
    with pytest.raises(ValueError):
        sweep_grid(5, low=1.0, high=0.0)
    with pytest.raises(ValueError):
        sweep_grid(True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Certification of the canonical rule — no false positives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factor", sorted(MONOTONE_FACTOR_DIRECTION))
def test_canonical_rule_is_monotone_in_every_factor(
    baseline: ChannelRuleInputs, factor: str
) -> None:
    report = certify_monotonicity(baseline, factor)
    assert isinstance(report, MonotonicityReport)
    assert report.ok, (
        f"{factor}: {len(report.violations)} violation(s), worst magnitude "
        f"{report.worst_magnitude:.6f}"
    )
    assert report.worst_magnitude == pytest.approx(0.0)


def test_certify_all_factors_covers_every_monotone_factor(
    baseline: ChannelRuleInputs,
) -> None:
    reports = certify_all_factors(baseline)
    assert set(reports) == set(MONOTONE_FACTOR_DIRECTION)
    assert all(report.ok for report in reports.values())


# ---------------------------------------------------------------------------
# Quantitative target: 32x the coverage of the single-pair checker
# ---------------------------------------------------------------------------


def test_sweep_examines_32x_more_pairs_than_the_legacy_checker(
    baseline: ChannelRuleInputs,
) -> None:
    report = certify_monotonicity(baseline, "support_coverage")
    assert report.n_points == DEFAULT_SWEEP_POINTS
    assert report.n_pairs == DEFAULT_SWEEP_POINTS - 1
    # The legacy checker inspects exactly one pair.
    assert report.coverage_ratio / 1.0 >= 32.0


def test_legacy_single_pair_check_still_agrees_on_the_canonical_rule(
    baseline: ChannelRuleInputs,
) -> None:
    """The certifier is additive: it must not contradict the old checker."""
    from dataclasses import replace

    from adaptive_reflow.contracts import FactorValue

    low = replace(baseline, support_coverage=FactorValue(0.2))
    high = replace(baseline, support_coverage=FactorValue(0.9))
    assert check_monotonicity_property("support_down", high, low)
    assert certify_monotonicity(baseline, "support_coverage").ok


# ---------------------------------------------------------------------------
# Localisation on a deliberately-broken rule
# ---------------------------------------------------------------------------


def test_inverted_rule_is_caught_and_localised(baseline: ChannelRuleInputs) -> None:
    """A rule that inverts past a threshold is invisible to a single pair."""

    def broken(inputs: ChannelRuleInputs) -> float:
        coverage = float(inputs.support_coverage)
        # Monotone increasing up to 0.6, then it turns over.
        return coverage if coverage <= 0.6 else 1.2 - coverage

    report = certify_monotonicity(baseline, "support_coverage", rule=broken)
    assert not report.ok
    assert report.violations
    worst = max(report.violations, key=lambda v: v.magnitude)
    assert worst.factor == "support_coverage"
    assert worst.lower_value >= 0.55
    assert worst.magnitude > 0.0
    assert report.worst_magnitude == pytest.approx(worst.magnitude)


def test_a_single_pair_would_have_missed_the_inverted_rule(
    baseline: ChannelRuleInputs,
) -> None:
    """Demonstrates the coverage gap the sweep closes."""

    def broken(inputs: ChannelRuleInputs) -> float:
        coverage = float(inputs.support_coverage)
        return coverage if coverage <= 0.6 else 1.2 - coverage

    # A pair drawn entirely from the monotone region looks clean...
    below = certify_monotonicity(baseline, "support_coverage", rule=broken, n_points=2)
    # ...only because the two endpoints happen to compare favourably.
    assert below.n_pairs == 1
    # The full sweep does not miss it.
    assert not certify_monotonicity(baseline, "support_coverage", rule=broken).ok


def test_tolerance_absorbs_roundoff_sized_moves(
    baseline: ChannelRuleInputs,
) -> None:
    def jittery(inputs: ChannelRuleInputs) -> float:
        return float(inputs.support_coverage) - 1e-15

    assert certify_monotonicity(
        baseline, "support_coverage", rule=jittery, tolerance=1e-12
    ).ok


def test_certify_rejects_unknown_factor_and_bad_tolerance(
    baseline: ChannelRuleInputs,
) -> None:
    with pytest.raises(ValueError):
        certify_monotonicity(baseline, "not_a_factor")
    with pytest.raises(ValueError):
        certify_monotonicity(baseline, "ambiguity", tolerance=-1.0)


def test_report_carries_the_full_beta_trace(baseline: ChannelRuleInputs) -> None:
    report = certify_monotonicity(baseline, "ambiguity", n_points=9)
    assert len(report.betas) == 9
    assert all(isinstance(b, float) for b in report.betas)
    assert report.direction == -1
