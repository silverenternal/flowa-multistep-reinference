"""GAP-78 observable screen — the separation and ordering logic, on synthetic data.

The screen's verdict is a claim about four real checkpoints, but its arithmetic
is separable and must be testable without them. The two traps it has to avoid:

* a "separation" that is really a tie at the threshold (no strict interval), and
* a Kendall tau that counts a monotone *inversion* as agreement.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.gap78_observable_screen import (
    _kendall_tau,
    observables,
    render,
    screen,
    separates,
)

OUTCOMES = {"a": "WIN", "b": "WIN", "c": "LOSS", "d": "LOSS"}


# --------------------------------------------------------------------------
# separates()
# --------------------------------------------------------------------------


def test_lower_values_win_is_a_separation():
    got = separates(OUTCOMES, {"a": 0.1, "b": 0.2, "c": 0.8, "d": 0.9})
    assert got["separates"] is True
    assert got["direction"] == "lower_wins"
    assert got["threshold_in"] == [0.2, 0.8]


def test_higher_values_win_is_a_separation():
    got = separates(OUTCOMES, {"a": 0.9, "b": 0.8, "c": 0.2, "d": 0.1})
    assert got["separates"] is True
    assert got["direction"] == "higher_wins"


def test_interleaved_values_do_not_separate():
    """The real `rho` pattern: the LOSS 0.782 sits between the two WINs."""
    got = separates(OUTCOMES, {"a": 0.55, "b": 0.75, "c": 0.78, "d": 0.70})
    assert got["separates"] is False
    assert got["direction"] is None


def test_one_outcome_class_is_not_a_separation():
    got = separates({"a": "WIN", "b": "WIN"}, {"a": 0.1, "b": 0.2})
    assert got["separates"] is False
    assert "at least one WIN and one LOSS" in got["reason"]


# --------------------------------------------------------------------------
# _kendall_tau()
# --------------------------------------------------------------------------


def test_tau_is_one_for_a_monotone_agreement():
    assert _kendall_tau([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)


def test_tau_is_minus_one_for_a_reversal():
    assert _kendall_tau([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_tau_counts_a_single_swap_below_one():
    # one discordant pair of six: tau-a = (5 - 1) / 6
    assert _kendall_tau([1, 2, 3, 4], [1, 2, 4, 3]) == pytest.approx(4 / 6)


# --------------------------------------------------------------------------
# observables()
# --------------------------------------------------------------------------


def test_rho_is_the_trace_ratio_by_construction():
    rng = np.random.default_rng(0)
    mu = np.zeros(4)
    feats = rng.standard_normal((500, 4)) * 2.0
    tr_ref = float(np.trace(np.cov(rng.standard_normal((500, 4)), rowvar=False)))
    got = observables(feats, mu, tr_ref, seed=0)
    assert got["rho"] == pytest.approx(
        float(np.trace(np.cov(feats, rowvar=False))) / tr_ref, rel=1e-9
    )


def test_participation_ratio_is_one_for_an_isotropic_cloud_and_lower_for_a_collapsed_one():
    rng = np.random.default_rng(1)
    mu = np.zeros(8)
    iso = rng.standard_normal((400, 8))
    collapsed = iso.copy()
    collapsed[:, 1:] *= 0.01
    tr_ref = 1.0
    a = observables(iso, mu, tr_ref, seed=0)["participation_ratio"]
    b = observables(collapsed, mu, tr_ref, seed=0)["participation_ratio"]
    assert a > 5.0
    assert b < 1.5


def test_mean_shift_is_the_distance_to_the_reference_mean():
    feats = np.zeros((100, 3))
    feats[:, 0] = 3.0
    got = observables(feats + 1e-3 * np.random.default_rng(0).standard_normal((100, 3)),
                      np.zeros(3), 1.0, seed=0)
    assert got["mean_shift"] == pytest.approx(3.0, rel=1e-2)


# --------------------------------------------------------------------------
# screen() wiring and the caveat
# --------------------------------------------------------------------------


def test_render_prints_the_caveat_next_to_the_separation():
    """The confound warning must travel with the number, not live only in prose."""
    rep = {
        "labels": ["a", "b"],
        "outcomes": {"a": "WIN", "b": "LOSS"},
        "per_checkpoint": {"a": {"x": 0.1}, "b": {"x": 0.9}},
        "q1_orders_rho": {"x": {"kendall_tau_vs_rho": 1.0}},
        "q2_separates_outcome": {"x": separates({"a": "WIN", "b": "LOSS"},
                                                {"a": 0.1, "b": 0.9})},
        "caveat": "CONFOUNDED on n=4",
    }
    md = render(rep)
    assert "Q2 sep" in md
    assert "yes (lower_wins)" in md
    assert "CONFOUNDED" in md
